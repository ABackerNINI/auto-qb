"""三层守卫 —— 「只碰白名单实例 / 真实种子全程非活跃」的机检实现。

为什么是代码而不是纪律: 这两条约束一旦靠人记, 迟早会被"这次特殊"绕过; 而绕过的代价是动了生产 qB
或让真实种子跑了一轮流量。所以这里全部 fail-closed: 核不出来就拒跑, 没有 --force 逃生门。

三层:
  1. 静态白名单 —— 端口 ∈ {36595, 36596}, 且占用该端口的进程镜像路径在测试目录下;
  2. 前置快照 + 归零 —— 记下当时所有真实种子, 全部暂停;
  3. 运行期看门狗 —— 每 2s 复核, 真实种子一旦有速率立刻暂停并记违规, 累计 3 次由调用方中止。
"""
from __future__ import annotations

import subprocess
import threading
import time

WHITELIST_PORTS = (36595, 36596)
# testing 与 testing2 都落在这一前缀下; 生产实例(D:\Programs\qBittorrent-2 / Program Files)不在其中
IMAGE_PREFIXES = ("D:\\Programs\\qBittorrent-testing", )
EXE = {
    36595: "D:\\Programs\\qBittorrent-testing\\qbittorrent.exe",
    36596: "D:\\Programs\\qBittorrent-testing2\\qbittorrent.exe",
}
ACTIVE_STATES = {"uploading", "downloading", "forcedUP", "forcedDL", "stalledDL", "metaDL", "checkingUP", "checkingDL"}


class GuardError(RuntimeError):
    """守卫不通过 —— 调用方必须中止, 不许降级继续。"""


def listening_pid(port: int) -> int | None:
    """按端口反查监听进程 PID(Windows netstat; 只用于白名单端口)。

    ⚠ 中文 Windows 的 netstat / powershell 输出是 GBK 代码页 —— 用默认 utf-8 解会
    UnicodeDecodeError 并把守卫打成"崩了", 所以显式按 gbk 解并容错。
    """
    out = subprocess.run(
        ["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True, encoding="gbk", errors="replace", timeout=20
    ).stdout
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[0].upper() == "TCP" and parts[1].endswith(f":{port}"
                                                                              ) and parts[3].upper() == "LISTENING":
            return int(parts[4])
    return None


def image_path(pid: int) -> str | None:
    """进程镜像路径。核不出来返回 None ⇒ 调用方 fail-closed。"""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", f"(Get-Process -Id {pid}).Path"],
            capture_output=True,
            text=True,
            encoding="gbk",
            errors="replace",
            timeout=20,
        )
    except Exception:
        return None
    path = (r.stdout or "").strip().strip("\r\n")
    return path or None


def check_port(port: int) -> dict:
    """第一层: 端口 + 镜像路径。通过返回快照, 不通过抛 GuardError。"""
    if port not in WHITELIST_PORTS:
        raise GuardError(f"端口 {port} 不在白名单 {WHITELIST_PORTS} —— 拒跑")
    pid = listening_pid(port)
    if pid is None:
        raise GuardError(f"端口 {port} 没有监听进程(实例没起? 用 real.up 拉起)")
    path = image_path(pid)
    if not path:
        raise GuardError(f"端口 {port} 的进程 {pid} 镜像路径核不出来 —— 无法确认不是生产实例, 拒跑")
    if not any(path.startswith(p) for p in IMAGE_PREFIXES):
        raise GuardError(f"端口 {port} 被 {path} 占用, 不在测试目录 {IMAGE_PREFIXES} 下 —— 拒跑(可能是生产 qB)")
    return {"port": port, "pid": pid, "image": path}


def check_online(qb) -> str:
    """第 1.5 层: 实例必须真的"在线"(有可用监听 socket)。

    `connection_status == "disconnected"` 不是"网络差", 是**这个实例根本发不出 announce**:
    BT 监听端口被别的进程占着(实测 36596 的 60537 撞上生产实例) ⇒ libtorrent 认定自己离线 ⇒
    tracker 一个请求都不发, 种子照样显示 `stalledUP`/`stalledDL`, 日志里连一条错误都没有。
    这种"看起来全正常、实际零流量"的状态最贵, 所以放在守卫里 fail-closed。
    """
    status = qb.connection_status()
    if status == "disconnected":
        raise GuardError(
            f"端口 {qb.port} connection_status=disconnected —— 没有可用 BT 监听 socket"
            f"(多半是 listen_port 被别的进程占用; 用 socket.bind 探一个空端口再 set_prefs(listen_port=...))"
        )
    return status


def tag_set(t: dict) -> set[str]:
    """qB tags 字段的容错解析: qB 多标签用「, 」(逗号+空格)连接, 裸 split(",") 会把
    第二个标签解析成带前导空格的串(" real-fake")而成员判断失明(issue 26-10-31-1215) ——
    一律 strip 后判成员。所有「按标签认领种子」的判断都走这里, 不许自带裸 split。"""
    return {x.strip() for x in (t.get("tags") or "").split(",") if x.strip()}


def snapshot(qb, skip_tags: tuple[str, ...] = ()) -> dict:
    """第二层: 记录真实种子(哈希 → 名称)并全部暂停。

    `skip_tags`: 带这些标签的种子**既不暂停也不计入保护面** —— 自造种子(real-fake)本来就该由
    用例/命令自己管, 把它们一起暂停会让"我刚加的假种子怎么变成 stoppedUP 了"变成日常困惑。
    """
    def ours(t: dict) -> bool:
        return bool(tag_set(t) & set(skip_tags))

    torrents = [t for t in qb.torrents() if not ours(t)]
    hashes = {t["hash"]: t["name"] for t in torrents}
    if hashes:
        qb.pause("|".join(hashes))
        deadline = time.time() + 15
        while time.time() < deadline:
            still = [t for t in qb.torrents() if t["hash"] in hashes and t["state"] in ACTIVE_STATES]
            if not still:
                break
            time.sleep(0.5)
        else:
            raise GuardError(f"端口 {qb.port}: 暂停后仍有 {len(still)} 个种子处于活跃状态, 拒跑")
    return hashes


def active_torrents(qb, protected: set[str]) -> list[dict]:
    return [
        t for t in qb.torrents()
        if t["hash"] in protected and (t["upspeed"] or t["dlspeed"] or t["state"] in ACTIVE_STATES)
    ]


class Watchdog(threading.Thread):
    """第三层: 运行期复核。违规立刻暂停, 并累计计数交给调用方中止。"""
    def __init__(self, qb, protected: set[str], interval: float = 2.0, limit: int = 3):
        super().__init__(daemon=True)
        self.qb = qb
        self.protected = protected
        self.interval = interval
        self.limit = limit
        self.violations: list[dict] = []
        self.errors: list[dict] = []  # 瞬时不可达等, 不算违规(否则一次抖动就把整片判红)
        self._stop = threading.Event()

    def run(self):
        while not self._stop.wait(self.interval):
            try:
                bad = active_torrents(self.qb, self.protected)
            except Exception as exc:  # 实例暂时不可达不该让看门狗线程炸掉
                self.errors.append({"ts": time.time(), "error": repr(exc)[:120]})
                continue
            if bad:
                self.qb.pause("|".join(t["hash"] for t in bad))
                for t in bad:
                    self.violations.append(
                        {
                            "ts": time.time(),
                            "hash": t["hash"],
                            "name": t["name"],
                            "state": t["state"]
                        }
                    )
            if len(self.violations) >= self.limit:
                return

    def stop(self):
        self._stop.set()
        self.join(timeout=5)
