"""RM09 WebUI 写侧 —— 十条真机用例(端点回执 → 命令线消费 → qB 真作用全链路)。

验证面对准冻结计划 plans/26-10-31-1710-plan-real-RM09.html §03 的十条 spec:
单发命令 pause/resume 全链路(RM09-01)· 删除双态 false 数据还在 / true 数据真删(RM09-02)·
批量合单 hashes+组键混合 + 路由层 400 三连 + skip 计数(RM09-03)· 强制汇报回执三态(RM09-04)·
移动真搬文件 + rename + rename-fs(RM09-05)· 组命令全员真停 + 未知 key 拒收(RM09-06)·
配置保存 WebUI 落盘通道(RM09-07)· keys 写读回 + 非法载荷拒收(RM09-08)· fs mkdir 白名单内建 +
越界拒收(RM09-09)· 种子转移端点未知 target 负向(RM09-10)。

代码实况落刀点(计划给意图, 这里按 src 实况):
- 回执通道: POST 端点 200 只代表「入队」(runtime.post_command 返回 {queued, cmd_id});
  结果轮询 GET /api/cmd/{cmd_id}(system.py:42), pending = 主循环未写。回执 status 三桶
  ok/warn/error, 文案前缀常量单点 commands.py(RC_FAIL/RC_DEFERRED/RC_UNCONFIRMED_PREFIX)。
  pause/resume/delete 等非延迟回执族由 drain 的 defer_receipt 写 ok(RESYNC_COMMANDS 族);
  bulk_torrents 按 action 分流(pause/resume 回执由 drain 写, 错误回执由 handler 写);
  add_torrents/reannounce 由 handler 自写。计划里的「写序号单调」外部不可观测(write_seq 只进
  读缓存键)—— 如实降为可观测面: 回执 ts 单调 + wait_ms/exec_ms 埋点齐全(基线切片记账)。
- bulk 组键模式(DLG-02): keys 收 URL 编码态(base64url(JSON)), 与 /api/groups 行的 key 字段
  同编码(common.group_key_param 解码); 混合模式 = hashes + keys 合并去重, 缺失计数进 error 回执
  文案「N/M 个种子不存在或已被删除」(部分成功也报错口径)。
- 组命令的组 = 辅种组(store.groups, key=(规范化 save_path, 文件列表)): 假种子必须带 announce 且
  测试配置 trackers 有 domains 条目(§2.9), 同内容异 piece_len 两枚同 save_path 才成一个双成员组。
- fs 白名单根 = store 里已知 save_path 派生(fs._browse_roots), mkdir 的 path=父目录 name=单层名;
  越界 403(:116 _within_roots 前缀闸)。
- keys 存储单点 <data_dir>/webui-keys.json(state_dir 口径), 结构校验 fail-fast 422 且不触碰磁盘。
- 配置保存: GET /api/config 掩码树 → PUT {tree} → applied+changes(顶层段名)+restart_required;
  写盘单点 write_tree(非 R 级段立即生效)。热重载机制本身(RM02-04)不复测, 只测落盘通道。
- 转移端点: run/test 都有路由层目标预检(transfer.py:24), 未知 target_id 400 拒收不入队。

跑法: `commands run real.suite -- --slice RM09 --yes`(不要裸 pytest)。真实种子全程非活跃;
假种子一律 real-fake 标签(死端口 announce http://<本机IP>:1/announce, 零外连); 删除/移动/重命名
只对自造种子; 产品非 dry-run 起完整主程序(WEB 命令线挂在主循环命令线上), data_dir 指用例临时
目录, 配置一律 tests-real 派生 + schema_version: 5。
"""
from __future__ import annotations

import base64
import contextlib
import hashlib
import json
import os
import stat
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from auto_qb.webui.commands import (  # noqa: E402  回执文案契约单点(计划 §08: 断言只咬前缀三分类)
    RC_DEFERRED_PREFIX,
    RC_FAIL_PREFIX,
    RC_UNCONFIRMED_PREFIX,
    REANNOUNCE_INACTIVE_SKIP,
)
from lib import app, instances, torrent  # noqa: E402
from lib.bencode import encode  # noqa: E402
from lib.net import local_host  # noqa: E402
from lib.tracker import FakeTracker  # noqa: E402

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="本片断言含 Windows 特有语义(taskkill/盘符路径白名单)"),
]

WORK = Path(__file__).resolve().parents[1] / ".work" / "rm09"
TAG = "real-fake"
SETTLED = {
    "stalledUP", "stalledDL", "pausedUP", "pausedDL", "stoppedUP", "stoppedDL", "missingFiles", "error", "moving"
}
# 假种子 announce 指本机死端口(零外连, §2.9): 产品对「未匹配 tracker 配置」的种子跳过整条
# matched 管线 ⇒ 组命令用例(RM09-03/06)必须配 announce + trackers domains 条目。
FAKE_TRACKER_HOST = local_host()
ANNOUNCE = f"http://{FAKE_TRACKER_HOST}:1/announce"
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 绕 HTTP_PROXY(127.0.0.1 不走代理)

# ---------------------------------------------------------------- 基座


def _is_link(p) -> bool:
    try:
        st = os.lstat(p)
    except OSError:
        return False
    return bool(getattr(st, "st_reparse_tag", 0)) or stat.S_ISLNK(st.st_mode)


def purge_tree(root):
    """删目录树, 绝不递归删穿链接(RM04 同款: os.walk topdown 遇 reparse 点剪枝)。"""
    root = Path(root)
    if _is_link(root):
        os.rmdir(root)
        return
    if not root.exists():
        return
    for dirpath, dirnames, _files in os.walk(root, topdown=True):
        for d in list(dirnames):
            full = Path(dirpath) / d
            if _is_link(full):
                os.rmdir(full)
                dirnames.remove(d)
    import shutil

    shutil.rmtree(root, ignore_errors=True)


def case_dir(name: str) -> Path:
    purge_tree(WORK / name)
    d = WORK / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def norm(path) -> str:
    return str(path or "").replace("\\", "/").rstrip("/")


def wait_until(fn, timeout: float, desc: str, interval: float = 0.4):
    """轮询到 fn() 为真值并返回它; 超时抛 AssertionError 带最后一次观测。"""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = fn()
        if last:
            return last
        time.sleep(interval)
    raise AssertionError(f"等待超时({timeout}s): {desc}; 最后观测: {last}")


CONFIG_TEMPLATE = """\
config:
    schema_version: 5
    qbittorrent:
        host: 127.0.0.1
        port: 36596
        username: ""
        password: ""
    data_dir: "{data_dir}"
    main_tick: 2S
    sync_interval: 1.5S
    state_save_interval: 30S
    interval: 60S
    log:
        level: INFO
    grouping:
        enabled: {grouping}
    trackers:
        rm09fake:
            domains: ["{fake_host}"]
    web:
        enabled: true
        host: 127.0.0.1
        port: {web_port}
        skip_local_verify: true
    notify:
        enabled: false
"""


def write_cfg(case: Path, *, grouping: bool = True) -> tuple[Path, int]:
    """生成临时配置(schema_version: 5, 直连 36596 空库, WEB 必开 —— 命令消费挂在完整主循环上)。"""
    cfg = case / "config.yml"
    web_port = app.free_port()
    cfg.write_text(
        CONFIG_TEMPLATE.format(
            data_dir=(case / "data").as_posix(),
            grouping="true" if grouping else "false",
            web_port=web_port,
            fake_host=FAKE_TRACKER_HOST,
        ),
        encoding="utf-8",
    )
    text = cfg.read_text(encoding="utf-8")
    if "port: 36595" in text:
        raise AssertionError(f"配置指向了 36595(真实种子), 拒跑: {cfg}")
    if "schema_version: 5" not in text:
        raise AssertionError(f"配置缺 schema_version: 5(会触发迁移改写), 拒跑: {cfg}")
    return cfg, web_port


@contextlib.contextmanager
def product_case(name: str, *, grouping: bool = True):
    """起一份完整主程序(非 dry-run, WEB 开)跑单条用例, 收尾必停。"""
    case = case_dir(name)
    cfg, port = write_cfg(case, grouping=grouping)
    proc = app.start(cfg)
    try:
        assert proc.wait_web(), f"产品 WEB 未启动: 日志尾部 {proc.log()[-400:]!r}"
        yield case, port, proc
    finally:
        proc.stop()


def web_req(port: int, method: str, path: str, body: dict | None = None) -> dict:
    """产品 Web API 客户端(GET/POST/PUT; 本机免鉴权 skip_local_verify=true)。"""
    r = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        method=method,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
    )
    if body is not None:
        r.add_header("Content-Type", "application/json")
    with _OPENER.open(r, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def web_err(port: int, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    """非 2xx 探针: 返回 (状态码, 解析后的错误载荷); 拿到 2xx 反而是用例 bug, 直接抛。"""
    try:
        web_req(port, method, path, body)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"raw": raw}
    raise AssertionError(f"期望非 2xx 拒收, 实际成功: {method} {path} {body or ''}")


def post_cmd(port: int, path: str, body: dict | None = None) -> dict:
    """投递写命令: 断言入队回执形状(POST 200 只代表入队 —— 计划 §08 风险 1)。"""
    r = web_req(port, "POST", path, body)
    assert r.get("queued") is True and r.get("cmd_id"), f"入队回执形状不对(缺 queued/cmd_id): {path} -> {r}"
    return r


def wait_cmd(port: int, cmd_id: str, timeout: float = 15.0, desc: str = "命令回执") -> dict:
    """_wait 轮询 /api/cmd/{cmd_id} 到终态(pending = 主循环尚未执行完或仍在确认中)。"""
    def probe():
        r = web_req(port, "GET", f"/api/cmd/{cmd_id}")
        return r if r.get("status") != "pending" else None

    return wait_until(probe, timeout, f"{desc} {cmd_id}")


def flat_hashes(port: int) -> set[str]:
    """产品 store 快照里的种子 hash 集(flat 视图; 命令消费按快照命中, 不在快照=静默跳过)。"""
    return {t["hash"] for t in web_req(port, "GET", "/api/state?view=torrent")["torrents"]}


def wait_in_store(port: int, *hashes: str, timeout: float = 30.0) -> None:
    wait_until(lambda: all(h in flat_hashes(port) for h in hashes), timeout, f"种子未进产品快照: {hashes}")


def wait_in_store_state(port: int, ih: str, state: str, timeout: float = 30.0) -> None:
    """等产品快照把该种子的状态同步到 state(快照滞后 qB 1-2 个同步拍, §2.9)。

    reannounce 的非活跃前置闸读的是快照 state —— 只等 hash 进快照就发命令, 会读到
    checkingUP(检查中 ∈ REANNOUNCE_BLOCKED_STATES)而误落「非活跃忽略」。
    """
    def probe():
        for t in web_req(port, "GET", "/api/state?view=torrent")["torrents"]:
            if t["hash"] == ih and t.get("state") == state:
                return True
        return None

    wait_until(probe, timeout, f"快照状态未到 {state}: {ih[:8]}")


def groups_view(port: int) -> list[dict]:
    return web_req(port, "GET", "/api/groups")["groups"]


def group_row(groups: list[dict], h: str) -> dict | None:
    hits = [g for g in groups if any(m["hash"] == h for m in g["members"])]
    return hits[0] if hits else None


def wait_group(port: int, h: str, members: set[str], timeout: float, desc: str) -> dict:
    """等 h 归进恰含 members 的组, 返回组行(key 字段 = base64url 编码态)。"""
    def probe():
        g = group_row(groups_view(port), h)
        if g and {m["hash"] for m in g["members"]} == members:
            return g
        return None

    return wait_until(probe, timeout, desc)


# ---- qB 侧辅助(36596 副实例; 假种子 real-fake 标签, 幂等清场) ----


def qbfake() -> "object":
    return instances.make(instances.SECONDARY)


def _tags_of(t) -> set[str]:
    """qB 多标签以「, 」连接, 裸 split 对双标签失明(§2.9), 一律 strip。"""
    return {x.strip() for x in (t.get("tags") or "").split(",") if x.strip()}


def _add_retry(qb, raw: bytes, savepath: str, ih: str) -> None:
    """加种子, 409 双义处理(§2.9: 同 infohash 旧副本一律删掉重加, 绝不收养)。"""
    from lib.qb import QbError

    for _attempt in range(4):
        try:
            qb.add_torrent(raw, savepath=savepath, tags=TAG, infohash_hint=ih)
            return
        except QbError as e:
            if "409" not in str(e):
                raise
            stale = qb.torrent(ih)
            if stale is None:
                time.sleep(1.5)
                continue
            qb.delete(stale["hash"], delete_files=True)
            wait_until(lambda: qb.torrent(ih) is None, 15, f"409 旧副本删除未生效: {ih[:8]}")
    raise AssertionError(f"add 持续 409: {ih[:8]} @ {savepath}")


def rm_all_fakes(qb) -> list[str]:
    """删光 36596 里本片自造的种子(连数据), 收尾轮询核净。"""
    gone = []
    for t in qb.torrents():
        if TAG in _tags_of(t):
            qb.delete(t["hash"], delete_files=True)
            try:
                qb.remove_tags(t["hash"], TAG)
            except Exception:  # noqa: BLE001 —— 种子已删时该调用无害失败
                pass
            gone.append(t["name"])
    if gone:
        wait_until(lambda: not [t for t in qb.torrents() if TAG in _tags_of(t)], 15, f"real-fake 残留未删净: {gone}")
    return gone


def settle(qb, ih: str, timeout: float = 60.0) -> dict:
    """等种子走完 check/alloc 拿到稳定态。"""
    deadline = time.time() + timeout
    t: dict = {}
    while time.time() < deadline:
        t = qb.torrent(ih) or {}
        if t.get("state") in SETTLED:
            return t
        time.sleep(0.3)
    return t


def wait_state(qb, ih: str, state: str, timeout: float = 30.0, desc: str = "") -> None:
    wait_until(lambda: (qb.torrent(ih) or {}).get("state") == state, timeout, f"qB 状态未到 {state}: {desc} {ih[:8]}")


def fake_one(
    qb,
    case: Path,
    name: str,
    size: int = 256 * 1024,
    piece_len: int = torrent.PIECE_LEN,
    paused: bool = False,
    sub: str = "src",
    announce: str = ANNOUNCE,
) -> str:
    """单文件假种子(带数据落盘; announce 默认本机死端口, 可传伪 tracker url)。"""
    savepath = case / sub
    os.makedirs(savepath, exist_ok=True)
    torrent.write_file(str(savepath / name), size, "random", name)
    raw, ih = torrent.build_from_path(str(savepath / name), name, announce, piece_len)
    _add_retry(qb, raw, str(savepath), ih)
    if paused:
        qb.pause(ih)
    return ih


def fake_second_member(qb, savepath: Path, name: str, piece_len: int) -> str:
    """同内容第二成员: 沿用已落数据, 换 piece_len 区分 infohash(RM04 口径)。"""
    raw, ih = torrent.build_from_path(str(savepath / name), name, ANNOUNCE, piece_len)
    _add_retry(qb, raw, str(savepath), ih)
    return ih


def fake_multi(
    qb, tname: str, files: list[tuple[str, int]], savepath: Path, salt: str, piece_len: int = torrent.PIECE_LEN
) -> str:
    """多文件种子(子目录布局; RM04 同款造法)。files = [(含 tname 前缀的 posix 相对路径, 字节)]。"""
    blob = bytearray()
    for rel, size in files:
        data = b"".join(torrent.chunks(size, "random", f"{salt}:{rel}"))
        p = savepath / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        blob += data
    pieces = b"".join(hashlib.sha1(bytes(blob[i:i + piece_len])).digest() for i in range(0, len(blob), piece_len))
    info = {
        "name": tname,
        "piece length": piece_len,
        "pieces": pieces,
        "private": 1,
        "files": [{
            "path": rel.split("/")[1:],
            "length": size
        } for rel, size in files],
    }
    ih = hashlib.sha1(encode(info)).hexdigest()
    raw = encode({"info": info, "comment": "auto-qb real-machine test (fake seed)", "announce": ANNOUNCE})
    os.makedirs(savepath, exist_ok=True)
    _add_retry(qb, raw, str(savepath), ih)
    return ih


@pytest.fixture()
def clean_fakes():
    """幂等清场: 开跑先清自造种子, 收尾再清一轮并核净(§09 幂等纪律)。"""
    qb = qbfake()
    rm_all_fakes(qb)
    yield qb
    rm_all_fakes(qb)


# ---------------------------------------------------------------- 用例


def test_rm09_01_pause_resume_roundtrip(clean_fakes):
    """[RM09-01] 单发右键命令真作用: pause/resume 全链路(端点回执 → 命令线消费 → qB 状态真变)

    前置: 基座(非 dry-run 完整主程序连 36596)+ 1 枚带数据假种子(stalledUP), 记录回读前原态。
    副作用: 假种子状态切换两次(做种 → 暂停 → 做种)。
    回滚: real-fake 种子收尾删净(连数据), 产品进程停止, 临时目录随下轮清场。
    失败判据: 回执 ok 但 qB 状态不变(命令线断链/写错实例); 回执永不到达(轮询超时);
              断言咬 pausedUP 旧枚举(qB 5.2 口径错, 用例侧事故); 回执 ts 倒挂。
    """
    with product_case("rm09_01") as (case, port, _proc):
        qb = clean_fakes
        h = fake_one(qb, case, "rm09a.bin")
        settle(qb, h)
        wait_state(qb, h, "stalledUP", desc="加种子后应纯本地做种")
        wait_in_store(port, h)

        r1 = post_cmd(port, f"/api/torrents/{h}/pause")
        rc1 = wait_cmd(port, r1["cmd_id"], desc="pause 回执")
        assert rc1["status"] == "ok", f"pause 回执非 ok: {rc1}"
        wait_state(qb, h, "stoppedUP", desc="pause 后(qB 5.2 暂停语义=stoppedUP)")

        r2 = post_cmd(port, f"/api/torrents/{h}/resume")
        rc2 = wait_cmd(port, r2["cmd_id"], desc="resume 回执")
        assert rc2["status"] == "ok", f"resume 回执非 ok: {rc2}"
        wait_state(qb, h, "stalledUP", desc="resume 后恢复做种")

        # 回执时序(外部可观测面): 回执 ts 单调 + 命令线节拍(wait_ms/exec_ms 埋点齐全)
        assert rc2["ts"] >= rc1["ts"], f"回执 ts 倒挂: {rc1['ts']} -> {rc2['ts']}"
        for rc in (rc1, rc2):
            assert "wait_ms" in rc and "exec_ms" in rc, f"回执缺耗时埋点: {rc}"


def test_rm09_02_delete_two_modes(clean_fakes):
    """[RM09-02] 删除命令双态: delete_files=false 种子消失数据还在 / true 数据真删

    前置: 基座 + 两枚假种子经 POST /api/torrents/add 走 WebUI 通道(独立落点目录, 路径记录)。
    副作用: 两枚自造种子及数据被删(可重建)。
    回滚: 删残留目录; 用例开跑先清同类种子(幂等)。
    失败判据: false 态连数据一起删了(delete_files 透传破, 高优); true 态种子没了文件还在
              (qB delete_files 语义没透传); add 回执 error(qB 拒绝)。
    """
    with product_case("rm09_02") as (case, port, _proc):
        qb = clean_fakes
        dir_a, dir_b = case / "data_a", case / "data_b"
        for d in (dir_a, dir_b):
            os.makedirs(d, exist_ok=True)
        raw_a, ih_a = torrent.build_from_path(
            str(torrent.write_file(str(dir_a / "rm09b_a.bin"), 256 * 1024)), "rm09b_a.bin", ANNOUNCE
        )
        raw_b, ih_b = torrent.build_from_path(
            str(torrent.write_file(str(dir_b / "rm09b_b.bin"), 256 * 1024)), "rm09b_b.bin", ANNOUNCE
        )
        file_a, file_b = dir_a / "rm09b_a.bin", dir_b / "rm09b_b.bin"

        # 经 WebUI add 端点入列(顺带覆盖 add 收据形态; save_path 逐条给 —— 两枚各自独立落点目录)
        for raw, ih, save_path, tag in ((raw_a, ih_a, str(dir_a), "A"), (raw_b, ih_b, str(dir_b), "B")):
            r = post_cmd(
                port, "/api/torrents/add", {
                    "files_b64": [base64.b64encode(raw).decode("ascii")],
                    "save_path": save_path,
                    "tags": [TAG],
                    "paused": False,
                }
            )
            rc = wait_cmd(port, r["cmd_id"], desc=f"add({tag}) 回执")
            assert rc["status"] == "ok", f"add({tag}) 回执非 ok: {rc}"
        settle(qb, ih_a)
        settle(qb, ih_b)
        wait_state(qb, ih_a, "stalledUP", desc="add 后 A 应做种")
        wait_state(qb, ih_b, "stalledUP", desc="add 后 B 应做种")
        wait_in_store(port, ih_a, ih_b)
        assert file_a.is_file() and file_b.is_file(), "加种子后数据文件应已在盘上"

        # ① delete_files=false: 种子消失, 数据还在(防「真删用户数据」语义破的关键红验)
        r1 = post_cmd(port, f"/api/torrents/{ih_a}/delete", {"delete_files": False})
        assert r1["delete_files"] is False, f"delete 回执未回显 delete_files: {r1}"
        rc1 = wait_cmd(port, r1["cmd_id"], desc="delete(false) 回执")
        assert rc1["status"] == "ok", f"delete(false) 回执非 ok: {rc1}"
        wait_until(lambda: qb.torrent(ih_a) is None, 30, "删除后 qB info 仍含该 hash(删除未生效)")
        assert file_a.is_file(), "delete_files=false 连数据一起删了(高危语义破)"

        # ② delete_files=true: 种子消失且数据真被 qB 删
        r2 = post_cmd(port, f"/api/torrents/{ih_b}/delete", {"delete_files": True})
        assert r2["delete_files"] is True, f"delete 回执未回显 delete_files: {r2}"
        rc2 = wait_cmd(port, r2["cmd_id"], desc="delete(true) 回执")
        assert rc2["status"] == "ok", f"delete(true) 回执非 ok: {rc2}"
        wait_until(lambda: qb.torrent(ih_b) is None, 30, "删除后 qB info 仍含该 hash(删除未生效)")
        wait_until(lambda: not file_b.exists(), 15, "delete_files=true 后数据文件仍在盘上")


def test_rm09_03_bulk_mixed_and_gates(clean_fakes):
    """[RM09-03] 批量合单: hashes+组键混合一次入队 → 聚合回执 + 路由层 400 拒收 + skip 计数负向

    前置: 基座 + 2 枚同内容异 piece_len 假种子(announce+domains, 等归组视图出现双成员组)。
    副作用: 2 枚假种子状态切换(暂停 → 恢复 → 暂停)。
    回滚: real-fake 种子删净 + 临时配置目录随用例目录清场。
    失败判据: 混合模式只生效一半(组展开或 hash 合并丢目标); 非法载荷入队而非 400(fail-fast 破);
              不存在 hash 让整批失败(应 skip 不得连坐); 回执 status 与 qB 实际不符。
    """
    with product_case("rm09_03") as (case, port, _proc):
        qb = clean_fakes
        savepath = case / "src"
        os.makedirs(savepath, exist_ok=True)
        h1 = fake_one(qb, case, "rm09c.bin", sub="src")
        h2 = fake_second_member(qb, savepath, "rm09c.bin", piece_len=32768)
        settle(qb, h1)
        settle(qb, h2)
        wait_in_store(port, h1, h2)
        row = wait_group(port, h1, {h1, h2}, 90, "同内容两枚未归成双成员组")
        gkey = row["key"]

        # 正向: hashes=[h1] + keys=[组key] 混合(DLG-02), 一次入队展开合并去重
        r = post_cmd(port, "/api/torrents/bulk", {"action": "pause", "hashes": [h1], "keys": [gkey]})
        rc = wait_cmd(port, r["cmd_id"], desc="bulk pause 回执")
        assert rc["status"] == "ok", f"bulk pause 回执非 ok: {rc}"
        wait_state(qb, h1, "stoppedUP", desc="bulk pause 成员1")
        wait_state(qb, h2, "stoppedUP", desc="bulk pause 成员2(经组键展开)")

        # 负向红验①: action=limits 两方向全空 → 路由层 400 拒收, 不入队(无 cmd_id)
        code1, p1 = web_err(port, "POST", "/api/torrents/bulk", {"action": "limits"})
        assert code1 == 400, f"limits 全空应 400: {code1} {p1}"
        assert "至少提供" in str(p1.get("detail", "")), f"400 detail 文案不对: {p1}"

        # 负向红验②: dl_limit=-1 → 400(「不能为负数」)
        code2, p2 = web_err(port, "POST", "/api/torrents/bulk", {"action": "limits", "dl_limit": -1})
        assert code2 == 400, f"负限速应 400: {code2} {p2}"
        assert "不能为负数" in str(p2.get("detail", "")), f"400 detail 文案不对: {p2}"

        # 负向红验③: 含不存在 hash → 正常入队, 聚合回执带 skip 计数, 其余目标不连坐
        for h in (h1, h2):  # 先用 qB 原生恢复, 让本步的 pause 动作有真状态可断
            qb.resume(h)
        wait_state(qb, h1, "stalledUP", desc="skip 前置恢复1")
        wait_state(qb, h2, "stalledUP", desc="skip 前置恢复2")
        unknown = "f" * 40
        r3 = post_cmd(port, "/api/torrents/bulk", {"action": "pause", "hashes": [h1, unknown], "keys": [gkey]})
        rc3 = wait_cmd(port, r3["cmd_id"], desc="bulk skip 回执")
        assert rc3["status"] == "error", f"含缺失 hash 应回 error 回执(部分成功也报错): {rc3}"
        assert "1/2 个种子不存在或已被删除" in str(rc3.get("error", "")), f"skip 计数文案不对: {rc3}"
        wait_state(qb, h1, "stoppedUP", desc="skip 批里已知目标仍被暂停(不连坐)")
        wait_state(qb, h2, "stoppedUP", desc="skip 批里组员仍被暂停(不连坐)")


def test_rm09_04_reannounce_three_states(clean_fakes):
    """[RM09-04] 强制汇报回执三态: not working / 非活跃忽略 / 成功 ok + 窗内推迟(消解等待模型全链)

    前置: 基座 + 活跃(stalledUP)/暂停(stoppedUP)假种子各 1(死端口) + 伪 tracker 假种子 1
    (interval=1800, 成功后 min 在未来); min 间隔基线由实际 announce 建立。
    副作用: reannounce_pending 账(内存态); 假种子对死端口/本地伪 tracker announce(零外连)。
    回滚: real-fake 种子删净; 伪 tracker 停机; 产品停机清内存账。
    失败判据: 活跃+死端口回了成功语义(检查 announce 是否真死端口); 可达 tracker 强制汇报不落 ok;
              暂停种子也进确认跟踪; 三前缀互串(分档逻辑分叉); 回执永不写(pending 泄漏)。
    注: 旧③「死端口行窗内二次 -> 推迟」在任何诚实判定下不可满足(min_announce 发送时即赋值、
    无响应不改写, 死端口行 min 恒在过去, 推迟分支不可达; 首跑实测落 error=再次被拒的诚实标签),
    推迟与 ok 两态改由伪 tracker 成功行承载(plan 26-10-31-2354 步3)。
    """
    with product_case("rm09_04") as (case, port, _proc):
        qb = clean_fakes
        h_active = fake_one(qb, case, "rm09d_live.bin", paused=False, sub="live")
        h_paused = fake_one(qb, case, "rm09d_stop.bin", paused=True, sub="stop")
        settle(qb, h_active)
        settle(qb, h_paused)
        wait_state(qb, h_active, "stalledUP", desc="活跃对照")
        wait_until(
            lambda: str((qb.torrent(h_paused) or {}).get("state", "")).startswith("stopped"), 30, "暂停对照未进入 stopped 态"
        )
        # 快照状态也要到位(reannounce 非活跃闸读快照 state, 滞后 1-2 拍会误落「非活跃忽略」)
        wait_in_store_state(port, h_active, "stalledUP")
        wait_in_store(port, h_active, h_paused)

        # ① 活跃 + 死端口 announce → tracker 拒绝: 「失败: tracker 未接受汇报(not working)」
        r1 = post_cmd(port, f"/api/torrents/{h_active}/reannounce")
        rc1 = wait_cmd(port, r1["cmd_id"], timeout=50, desc="reannounce(活跃) 回执")  # 确认窗最长 30s + 余量
        assert rc1["status"] == "error", f"活跃+死端口应落失败桶: {rc1}"
        # 聚合回执 error = 三桶计数文案 + 原因拼接, 不以 RC_FAIL_PREFIX 开头; 逐目标原因在 truth.results
        # (§2.14: 断言咬 status 桶 + 前缀, 位置咬对 —— 首跑实测修正, 原 startswith 咬错字段)
        assert RC_FAIL_PREFIX in str(rc1.get("error", "")), f"失败前缀不对: {rc1}"
        reasons1 = [str(r.get("reason", "")) for r in rc1.get("truth", {}).get("results", [])]
        assert any(s.startswith(RC_FAIL_PREFIX) for s in reasons1), f"逐目标原因缺失败前缀: {rc1}"

        # ② 暂停种子 → 非活跃前置闸(不发指令): 「未确认: 种子非活跃…」
        r2 = post_cmd(port, f"/api/torrents/{h_paused}/reannounce")
        rc2 = wait_cmd(port, r2["cmd_id"], timeout=20, desc="reannounce(暂停) 回执")
        assert rc2["status"] == "warn", f"暂停种子应落未确认桶(warn): {rc2}"
        assert rc2.get("error", "") == RC_UNCONFIRMED_PREFIX + REANNOUNCE_INACTIVE_SKIP, f"非活跃文案不对: {rc2}"

        # ③ 成功 ok 回执 + 窗内推迟: 旧期望「死端口行窗内二次 -> 推迟」在任何诚实判定下不可满足
        # (min_announce 发送时即赋值、无响应不改写, 死端口行 min 恒过去, 推迟分支不可达; 首跑实测
        # 落 error=再次被拒的诚实标签)。改用本地伪 tracker 成功行验两条: ok 回执(前跳正证据全链路)
        # 与推迟早回执(D1, min 在未来)。
        with FakeTracker(interval=1800) as tr_ok:
            h_ok = fake_one(qb, case, "rm09d_ok.bin", sub="ok", announce=tr_ok.url)
            settle(qb, h_ok)
            wait_state(qb, h_ok, "stalledUP", desc="伪 tracker 种子应纯本地做种")
            wait_in_store_state(port, h_ok, "stalledUP")
            wait_until(lambda: tr_ok.count(h_ok) >= 1, 60, "伪 tracker 未收到首报")

            def tracker_rows():
                return [
                    t for t in json.loads(qb._call(f"/torrents/trackers?hash={h_ok}").decode("utf-8"))
                    if str(t.get("url", "")).startswith("http")
                ]

            wait_until(lambda: any(t.get("status") == 2 for t in tracker_rows()), 30, "伪 tracker 行未转 working")
            # ③ 前跳幅度 = 本轮强制汇报与上次 announce 的发送间隔, 需 > TOL=3s 才算成功证据
            wait_until(lambda: time.time() - tr_ok.announces[-1]["ts"] > 5, 15, "距上次 announce 间隔不足")
            r_ok = post_cmd(port, f"/api/torrents/{h_ok}/reannounce")
            rc_ok = wait_cmd(port, r_ok["cmd_id"], timeout=50, desc="reannounce(伪 tracker) 回执")
            assert rc_ok["status"] == "ok", f"可达 tracker 强制汇报应落 ok 桶: {rc_ok}"
            assert tr_ok.count(h_ok) >= 2, "ok 回执前强制汇报应真的发起了一次 announce"
            # 窗内二次: min_e = 上次成功响应的 min_interval(1800s) 在未来 -> 「已受理: 推迟至」早回执
            r4 = post_cmd(port, f"/api/torrents/{h_ok}/reannounce")
            rc4 = wait_cmd(port, r4["cmd_id"], timeout=20, desc="reannounce(窗内二次) 回执")
            # 聚合 error = 计数文案开头(同①), 前缀断言咬包含 + truth.results 逐目标 reason
            assert rc4["status"] == "warn" and RC_DEFERRED_PREFIX in str(rc4.get("error", "")
                                                                        ), (f"窗内二次 reannounce 应落「已受理: 推迟至」: {rc4}")
            reasons4 = [str(r.get("reason", "")) for r in rc4.get("truth", {}).get("results", [])]
            assert any(s.startswith(RC_DEFERRED_PREFIX) for s in reasons4), f"逐目标原因缺推迟前缀: {rc4}"


def test_rm09_05_move_rename_renamefs(clean_fakes):
    """[RM09-05] 移动与重命名: location 真搬文件 + rename 改名 + rename-fs 改文件名(qB 回读三连)

    前置: 基座 + 1 枚多文件假种子(子目录布局); 目标目录预建(GATE_SPACE fail-closed, §2.9)。
    副作用: 数据文件被 qB 跨目录搬一次; 名称/文件名改两次。
    回滚: real-fake 种子删净(连数据) + 新旧目录随用例目录清场。
    失败判据: save_path 回读没变(移动链路断, 高优); 旧文件残留新目录为空(qB 没真搬);
              rename-fs 回执 ok 但 files 名单没变; 断言别名/journal(单成员组到不了那支, 口径错)。
    """
    with product_case("rm09_05") as (case, port, _proc):
        qb = clean_fakes
        src = case / "src"
        files = [("rm09epack/a.bin", 128 * 1024), ("rm09epack/b.bin", 64 * 1024)]
        h = fake_multi(qb, "rm09epack", files, src, "rm09e")
        settle(qb, h)
        wait_in_store(port, h)

        # ① location: 目标目录预建 → qB 真搬(单成员恒 FORM_DIRECT, 锚点= save_path 与文件)
        dst = case / "moved"
        dst.mkdir(parents=True, exist_ok=True)
        r1 = post_cmd(port, f"/api/torrents/{h}/location", {"location": str(dst)})
        rc1 = wait_cmd(port, r1["cmd_id"], desc="location 回执")
        assert rc1["status"] == "ok", f"location 回执非 ok: {rc1}"
        wait_until(lambda: norm((qb.torrent(h) or {}).get("save_path", "")) == norm(dst), 30, "qB save_path 未变到新目录")
        assert (dst / "rm09epack" / "a.bin").is_file(), "新目录里没有数据文件(qB 没真搬)"
        wait_until(lambda: not (src / "rm09epack" / "a.bin").exists(), 30, "旧目录数据残留(qB 搬迁未收尾)")

        # ② rename: qB 显示名真变
        r2 = post_cmd(port, f"/api/torrents/{h}/rename", {"name": "rm09e-renamed"})
        rc2 = wait_cmd(port, r2["cmd_id"], desc="rename 回执")
        assert rc2["status"] == "ok", f"rename 回执非 ok: {rc2}"
        wait_until(lambda: (qb.torrent(h) or {}).get("name") == "rm09e-renamed", 30, "qB name 未变")

        # ③ rename-fs: 文件名真变(torrents/files 回读)
        r3 = post_cmd(
            port, f"/api/torrents/{h}/rename-fs", {
                "old_path": "rm09epack/a.bin",
                "new_path": "rm09epack/a2.bin",
                "is_folder": False
            }
        )
        rc3 = wait_cmd(port, r3["cmd_id"], desc="rename-fs 回执")
        assert rc3["status"] == "ok", f"rename-fs 回执非 ok: {rc3}"

        def file_names() -> set[str]:
            return {f["name"] for f in json.loads(qb._call(f"/torrents/files?hash={h}").decode("utf-8"))}

        wait_until(lambda: "rm09epack/a2.bin" in file_names(), 30, "files 名单未出现新文件名")
        assert "rm09epack/a.bin" not in file_names(), "files 名单仍含旧文件名"
        assert (dst / "rm09epack" / "a2.bin").is_file(), "磁盘上新文件名不存在"


def test_rm09_06_group_commands(clean_fakes):
    """[RM09-06] 组命令真作用: 组 pause → 成员全员停 + 未知 key 拒收

    前置: 基座 + 同组假种子 ×2(announce+domains, 等归组视图成员出现再发命令)。
    副作用: 2 枚假种子状态切换(暂停 → 恢复)。
    回滚: real-fake 种子删净。
    失败判据: 命令只作用了部分成员(组展开破, 高优); 未知 key 静默成功(无账);
              回执 ok 但成员状态参差。
    """
    with product_case("rm09_06") as (case, port, _proc):
        qb = clean_fakes
        savepath = case / "src"
        os.makedirs(savepath, exist_ok=True)
        h1 = fake_one(qb, case, "rm09f.bin", sub="src")
        h2 = fake_second_member(qb, savepath, "rm09f.bin", piece_len=32768)
        settle(qb, h1)
        settle(qb, h2)
        wait_in_store(port, h1, h2)
        row = wait_group(port, h1, {h1, h2}, 90, "同内容两枚未归成双成员组")
        gkey = row["key"]

        # 读侧顺带核组视图在线(分组 qB 口径流量端点)
        payload = web_req(port, "GET", f"/api/traffic/qb/group/{urllib.parse.quote(gkey, safe='')}?window=24h")
        assert "totals" in payload, f"组流量视图缺 totals: {list(payload)}"

        # 组 pause → 两名成员全停
        r1 = post_cmd(port, f"/api/groups/{urllib.parse.quote(gkey, safe='')}/pause")
        rc1 = wait_cmd(port, r1["cmd_id"], desc="组 pause 回执")
        assert rc1["status"] == "ok", f"组 pause 回执非 ok: {rc1}"
        wait_state(qb, h1, "stoppedUP", desc="组 pause 成员1")
        wait_state(qb, h2, "stoppedUP", desc="组 pause 成员2")

        # 组 resume → 恢复对照
        r2 = post_cmd(port, f"/api/groups/{urllib.parse.quote(gkey, safe='')}/resume")
        rc2 = wait_cmd(port, r2["cmd_id"], desc="组 resume 回执")
        assert rc2["status"] == "ok", f"组 resume 回执非 ok: {rc2}"
        wait_state(qb, h1, "stalledUP", desc="组 resume 成员1")
        wait_state(qb, h2, "stalledUP", desc="组 resume 成员2")

        # 负向①: 畸形 key(非法 base64) → 路由层 400 拒收
        code1, p1 = web_err(port, "POST", "/api/groups/not-a-valid-key!!/pause")
        assert code1 == 400, f"畸形组 key 应 400: {code1} {p1}"
        assert "分组标识无效" in str(p1.get("detail", "")), f"400 detail 文案不对: {p1}"

        # 负向②: 形状合法但不存在的 key → 按计划「只要不是静默成功」
        bogus = base64.urlsafe_b64encode(json.dumps(["rm09-no-such-group", []]).encode()).decode("ascii")
        r3 = post_cmd(port, f"/api/groups/{bogus}/pause")
        rc3 = wait_cmd(port, r3["cmd_id"], desc="不存在组 pause 回执")
        assert rc3["status"] != "ok", f"不存在的组 key 竟静默 ok(无账): {rc3}"


def test_rm09_07_config_put_persists(clean_fakes):
    """[RM09-07] 配置保存 WebUI 落盘通道: GET → 树编辑 → PUT applied → 磁盘配置文件真变

    前置: 基座(可零种子); 落盘前配置文件字节快照。
    副作用: 运行配置被改一处(临时配置, 非红线 config.yml)。
    回滚: 产品随起停还原(临时 data_dir 删除即净)。
    失败判据: 回执 applied 但磁盘文件没变(落盘通道断, 高优); 改的键丢了(树合并分叉);
              非 R 级键报 restart_required(新事实, 如实记不定性, 引用 RM02-04 R 闸口径)。
    """
    with product_case("rm09_07") as (case, port, _proc):
        cfg_path = case / "config.yml"
        before = cfg_path.read_text(encoding="utf-8")

        got = web_req(port, "GET", "/api/config")
        tree = got["tree"]
        # 树 = 整份 YAML 文档(根键 config), 段在 tree["config"] 之下(RM05-02 同款配方)
        assert got["masked"] is True and tree["config"]["interval"] == "60S", (
            f"配置树原值不对: interval={tree.get('config', {}).get('interval')}"
        )

        tree["config"]["interval"] = "90S"
        resp = web_req(port, "PUT", "/api/config", {"tree": tree})
        assert resp.get("applied") is True, f"PUT 回执 applied 非 true: {resp}"
        assert "interval" in resp.get("changes", []), f"changes 未含改动段: {resp}"
        assert not resp.get("restart_required"), f"非 R 级键竟报 restart_required: {resp}"

        # 磁盘真落盘(字节级: 快照对比 + 键值解析)
        after = cfg_path.read_text(encoding="utf-8")
        assert after != before, "PUT 回执 applied 但配置文件字节未变(落盘通道断)"
        import yaml

        parsed = yaml.safe_load(after)["config"]
        assert parsed["interval"] == "90S", f"落盘内容里 interval 不是 90S: {parsed.get('interval')}"
        assert parsed["web"]["port"] == port, "落盘时无关段被搅动"

        # 回读一致
        tree2 = web_req(port, "GET", "/api/config")["tree"]
        assert tree2["config"]["interval"] == "90S", f"PUT 后 GET 回读不一致: {tree2['config'].get('interval')}"


def test_rm09_08_keys_roundtrip(clean_fakes):
    """[RM09-08] keys 写读回: PUT /api/keys → GET 回读一致 + 非法载荷拒收

    前置: 基座; keys 原值快照(GET)。
    副作用: 产品 keys 存储被写一次(<data_dir>/webui-keys.json)。
    回滚: PUT 回快照原值, 还原后回读比对。
    失败判据: 写后读不一致(写通道断); 非法载荷静默接受(fail-fast 破, 高优);
              还原后与原快照结构不齐。
    """
    with product_case("rm09_08") as (case, port, _proc):
        keys_file = case / "data" / "webui-keys.json"
        orig = web_req(port, "GET", "/api/keys")
        assert orig == {"schema_version": 1, "template": "aqb-default", "overrides": {}}, f"初始 keys 非默认表: {orig}"
        assert not keys_file.exists(), "从未自定义时不应有 keys 落盘文件"

        doc = {
            "schema_version": 1,
            "template": "aqb-default",
            "overrides": {
                "play_pause": "Ctrl+KeyQ",
                "open_settings": ""
            }
        }
        echoed = web_req(port, "PUT", "/api/keys", doc)
        assert echoed == doc, f"PUT 回显与提交不一致: {echoed}"
        back = web_req(port, "GET", "/api/keys")
        assert back == doc, f"写后读不一致: {back}"
        assert keys_file.is_file() and json.loads(keys_file.read_text(encoding="utf-8")) == doc, "keys 文件真值与回读不符"

        # 负向①: 归一化串不符(小写/多段) → 422 且磁盘零触碰
        snap = keys_file.read_bytes()
        code1, p1 = web_err(
            port, "PUT", "/api/keys", {
                "schema_version": 1,
                "template": "aqb-default",
                "overrides": {
                    "x": "ctrl+q"
                }
            }
        )
        assert code1 == 422, f"非法归一化串应 422: {code1} {p1}"
        assert keys_file.read_bytes() == snap, "422 拒收竟触碰了磁盘(高优)"

        # 负向②: schema_version 不识别 → 422
        code2, _p2 = web_err(
            port, "PUT", "/api/keys", {
                "schema_version": 2,
                "template": "aqb-default",
                "overrides": {}
            }
        )
        assert code2 == 422, f"未知 schema_version 应 422: {code2}"

        # 还原快照原值并核齐
        web_req(port, "PUT", "/api/keys", orig)
        assert web_req(port, "GET", "/api/keys") == orig, "还原后与原快照不一致"


def test_rm09_09_fs_mkdir_whitelist(clean_fakes):
    """[RM09-09] fs 写侧: mkdir 白名单根内真建 + 越界根外拒收(负向真红)

    前置: 基座 + 1 枚假种子(其 save_path 构成白名单根); 目标目录不存在(先探空)。
    副作用: 白名单根内新建一个空目录(用例自删)。
    回滚: 删该目录; 越界负向零副作用(拒收验证)。/api/open-path 真弹窗归 RM08, 本用例不调它。
    失败判据: 越界 mkdir 成功(白名单闸破, 安全面高优); 根内 mkdir 回执 ok 但目录没建;
              dirs 回读不含新建目录(读侧装配分叉)。
    """
    with product_case("rm09_09") as (case, port, _proc):
        qb = clean_fakes
        h = fake_one(qb, case, "rm09g.bin", sub="src")
        settle(qb, h)
        wait_in_store(port, h)
        src = case / "src"

        paths = web_req(port, "GET", "/api/paths")["paths"]
        hit = [p for p in paths if norm(p) == norm(src)]
        assert hit, f"/api/paths 未含白名单根(种子 save_path): {paths}"
        parent = hit[0]

        # 白名单根内 mkdir: 真建 + dirs 回读含它
        target = src / "rm09_newdir"
        assert not target.exists(), "前置: 目标目录应不存在"
        resp = web_req(port, "POST", "/api/fs/mkdir", {"path": parent, "name": "rm09_newdir"})
        assert resp.get("existed") is False and norm(resp.get("created", "")) == norm(target), f"mkdir 回执不对: {resp}"
        assert target.is_dir(), "mkdir 回执 ok 但目录没真建"
        dirs = web_req(port, "GET", f"/api/fs/dirs?path={urllib.parse.quote(parent, safe='')}")["dirs"]
        assert any(d["name"] == "rm09_newdir" for d in dirs), f"dirs 回读不含新建目录: {dirs}"
        os.rmdir(target)
        assert not target.exists(), "清理失败"

        # 负向真红: 根外路径 → 403 拒收 + 目录不存在(越界闸门)
        code, p = web_err(port, "POST", "/api/fs/mkdir", {"path": "C:/Windows/Temp", "name": "rm09_escape"})
        assert code == 403, f"根外 mkdir 应 403: {code} {p}"
        assert not (Path("C:/Windows/Temp") / "rm09_escape").exists(), "越界 mkdir 竟真建了(安全闸破, 高优)"


def test_rm09_10_transfer_unknown_target(clean_fakes):
    """[RM09-10] 种子转移端点负向: 未知 target_id 的 run/test 拒收且零状态变化

    前置: 基座 + 1 枚假种子(记录原态); 不配 transfer targets。正向真转移需第二下载器 → 跳过项。
    副作用: 无(两请求都应被路由层预检拦下, 不入队)。
    回滚: 删种子。
    失败判据: 未知 target 竟然入了队或改了种子状态(预检闸破, 高优); test 端点产生写副作用
              (只读语义破); 5xx 泄漏(应为结构化错误回执)。
    """
    with product_case("rm09_10") as (case, port, _proc):
        qb = clean_fakes
        h = fake_one(qb, case, "rm09h.bin", sub="src")
        settle(qb, h)
        wait_state(qb, h, "stalledUP", desc="原态记录")
        before = (qb.torrent(h) or {}).get("state")

        # 未知 target: 路由层预检 400 拒收不入队(run 要求启用 / test 只要求存在 —— 都卡在「不存在」)
        for path, body, tag in (
            ("/api/transfer/test", {
                "target_id": "rm09-nope"
            }, "test"),
            ("/api/transfer/run", {
                "target_id": "rm09-nope",
                "hashes": [h]
            }, "run"),
        ):
            code, p = web_err(port, "POST", path, body)
            assert code == 400, f"transfer/{tag} 未知 target 应 400: {code} {p}"
            assert "转移目标不存在" in str(p.get("detail", "")), f"transfer/{tag} detail 文案不对: {p}"

        # 参数负向: 空 target_id / 空 hashes → 400(非 5xx 泄漏)
        code3, _p3 = web_err(port, "POST", "/api/transfer/test", {"target_id": ""})
        assert code3 == 400, f"空 target_id 应 400: {code3}"
        code4, _p4 = web_err(port, "POST", "/api/transfer/run", {"target_id": "rm09-nope", "hashes": []})
        assert code4 == 400, f"空 hashes 应 400: {code4}"

        # 零状态变化: 种子原态未动(预检闸破则这里会看到转移痕迹)
        after = qb.torrent(h)
        assert after is not None and after.get("state") == before, f"种子状态被未知 target 请求改动: {before} -> {after}"
