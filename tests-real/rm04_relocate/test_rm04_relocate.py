"""RM04 辅种与分组 —— 十一条真机用例(归组 key / 组内一致性 / 跨组冲突 / 缺失文件 / 跨盘移动 / journal / facade share_limits / .!qB 窄域)。

验证面对准冻结计划 plans/26-10-31-1042-plan-real-RM04.html §02 的六行代码映射(漂移复测轮
plans/26-11-01-2033 追加 RM04-09: qbapi facade share_limits_mode):
归组 key(group_key_of, 断言走产品 WEB 只读端点 GET /api/groups)· 组内大小一致性(警告+整组暂停)·
跨组文件冲突(暂停下载方 + MISSING 豁免对照)· 缺失文件标记(带数据真删; --no-data 不是缺文件态)·
跨盘移动主链(同卷口径 C:→C:, 目录别名 + 穿透 + journal phase=done; 真跨卷半边 BLOCKED)·
journal 恢复与坏账兜底 · facade share_limits_mode 5.2.3 端到端(RM04-09)·
.!qB 窄域(S1/S2/R1/R2)真机复验(RM04-10: 组外 .!qB 不拦且原地不动 / 组内 .!qB 硬拦 /
目标叶子未建可上溯 + 同卷 note / 目标为文件 target_type)·
Web UI 整组迁移 confirm 回路真机化(RM04-14: 浏览器点击 -> 确认框 7 要素 -> confirm=true 重发
-> dst 落地 + job/journal done; 取消路径原框带路径重开且 B 组零位移)。

代码实况落刀点(计划给意图, 这里按 src 实况):
- 单成员组恒走 FORM_DIRECT(qB 自搬, 无别名无 journal)—— 目录别名链必须多成员组 + 子目录布局
  (alias_file_threshold: 1 压低阈值 + POST body confirm=true 过二次确认);
- 正常发起的搬迁锚点是「迁移发起」;「已下发 qB 搬迁」只出现在重启补发路径(_step_move);
- 同一物理文件挂两枚同组种子(辅种本质)时, 两枚的 info 必须不同 ⇒ 用**不同 piece_len** 造
  (同内容不同分块 → 不同 infohash, 双双校验通过); 盐不同会让先写的成员校验失败;
- 同卷证明闸门(same_volume_proof): qB 副实例 free_space_on_disk 报的是它**默认 save_path** 那块卷。
  环境1(36596 默认路径在 R: 盘)天然可证; 环境2 的 56590 默认 save_path 指向不存在的 R: 盘 ⇒
  free_space_on_disk 恒 -1 ⇒ 证明必败 ⇒ 多成员组被 GATE_SAME_FS 拒(RM04-05 探针实测)。
  解锁(造法校准, 测毕还原): 用例临时把 56590 save_path 改指 C: 现存目录, qB 立即报出 C: 真值;
- journal 恢复的权威账在 state.json 的 relocate.jobs(job_to_dict 形), journal/spec/pid 是 guardian 侧账;
  相位落盘走 state_save_interval(30S)周期, 断言等待窗按 30s+ 裕量给。

跑法: `commands run real.suite -- --slice RM04 --yes`(不要裸 pytest)。真实种子全程非活跃;
十一条全部 L1 假种子(零外连); 假种子一律 real-fake 标签; 落点只认 tests-real/.work/ 与 R:/qbt-fake/。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Callable

import pytest

from lib import app, instances, small_target, torrent
from lib.bencode import encode
from lib.net import local_host

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="本片断言含 Windows 特有语义(junction/taskkill)"),
]

WORK = Path(__file__).resolve().parents[1] / ".work" / "rm04"


def _ram_root() -> Path:
    """搬迁 src/大种子落点: R: 盘在用 R:/qbt-fake/rm04(内存盘, 重启即清空);
    R: 缺席(环境2 C盘机)退 .work/rm04/ram/ 真写盘(漂移复测计划 §04 S2 的盘探测回退)。"""
    r = Path("R:/qbt-fake/rm04")
    try:
        r.mkdir(parents=True, exist_ok=True)
        probe = r / ".probe"
        probe.write_bytes(b"x")
        probe.unlink()
        return r
    except OSError:
        return WORK / "ram"


RAM = _ram_root()
TAG = "real-fake"
MISSING_TAG = "MISSING"
SETTLED = {
    "stalledUP", "stalledDL", "pausedUP", "pausedDL", "stoppedUP", "stoppedDL", "missingFiles", "error", "moving"
}
IO_REPARSE_TAG_MOUNT_POINT = 0xA0000003

# 假种子 announce 指本机死端口(零外连): 产品对「未匹配 tracker 配置」的种子跳过整条
# torrents_added 管线(qbmanager.matched_added 判据, 实测: 无 announce ⇒ 归组永不发生),
# 所以种子必须带 announce 且测试配置里有对应 domains 条目。选本机死端口而非假域名 ——
# 假域名要走 DNS 解析(出外网), 本机 IP 死端口连接即被 RST(实测 §2.5 口径的变体)。
FAKE_TRACKER_HOST = local_host()
ANNOUNCE = f"http://{FAKE_TRACKER_HOST}:1/announce"

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 绕 HTTP_PROXY(127.0.0.1 不走代理)

# ---------------------------------------------------------------- 基座


def qbfake():
    return instances.make(instances.SECONDARY)


def _tags_of(t) -> set[str]:
    """qB tags 字段的容错解析: qB 多标签用「, 」(逗号+空格)连接, 裸 split(",") 会把
    " real-fake" 留下前导空格 → 双标签种子(MISSING, real-fake)对 real-fake 失明
    (实测: 清理漏网 → 同 infohash 残留被下一轮收养 → 假 FAIL 自续)。"""
    return {x.strip() for x in (t.get("tags") or "").split(",") if x.strip()}


def _add_retry(qb, raw: bytes, savepath: str, ih: str) -> None:
    """加种子, 409 双义处理(实测 qB 5.2: 重复 infohash 返回 409 Conflict)。

    同 infohash 旧副本在场时**一律删掉重加**, 绝不收养 —— 收养会把上轮的预打标/预暂停
    状态带进本跑(触发源永不触发 → 假 FAIL 自续, 实测踩中)。"""
    from lib.qb import QbError
    for attempt in range(4):
        try:
            qb.add_torrent(raw, savepath=savepath, tags=TAG, infohash_hint=ih)
            return
        except QbError as e:
            if "409" not in str(e):
                raise
            stale = qb.torrent(ih)
            if stale is None:
                time.sleep(1.5)  # 409 竞态落空型(未见副本): 稍候重试
                continue
            qb.delete(stale["hash"], delete_files=True)
            wait_until(lambda: qb.torrent(ih) is None, 15, f"409 同 infohash 旧副本删除未生效: {ih[:8]}")
    raise AssertionError(f"add 持续 409: {ih[:8]} @ {savepath}")


def rm_all_fakes(qb) -> list[str]:
    """删光 副实例 里本片自造的种子(连数据), 返回删掉的名字(证据用)。

    顺序 = **先删后摘标签**(删失败时保留 real-fake 标记, 让下一次清场还能看见它;
    先摘后删会在删除漏网时把种子变成无主残留 —— 实测踩中)。收尾轮询核净, 不净即抛。"""
    gone = []
    for t in qb.torrents():
        if TAG in _tags_of(t):
            qb.delete(t["hash"], delete_files=True)
            try:  # 标签摘除尽力而为(qB 空 tag 列表残留由 guard 收尾兜底)
                qb.remove_tags(t["hash"], f"{TAG},{MISSING_TAG}")
            except Exception:  # noqa: BLE001 —— 种子已删时该调用无害失败, 不影响清理
                pass
            gone.append(t["name"])
    if gone:
        wait_until(
            lambda: not [t for t in qb.torrents() if TAG in _tags_of(t)], 15, f"清理后仍有 real-fake 残留(删除未生效): {gone}"
        )
    return gone


def _is_link(p) -> bool:
    """junction / 任意 reparse 点 / symlink 探测(不跟随)。"""
    try:
        st = os.lstat(p)
    except OSError:
        return False
    return bool(getattr(st, "st_reparse_tag", 0)) or stat.S_ISLNK(st.st_mode)


def reparse_kind(p) -> str | None:
    """链接形态判定(与产品 alias_fs.alias_kind_of 同口径的本地探针)。"""
    try:
        st = os.lstat(p)
    except OSError:
        return None
    tag = getattr(st, "st_reparse_tag", 0)
    if tag == IO_REPARSE_TAG_MOUNT_POINT:
        return "junction"
    if stat.S_ISLNK(st.st_mode):
        return "symlink"
    if st.st_nlink > 1:
        return "hardlink"
    return None


def make_junction(link: Path, target: Path) -> None:
    """建一条目录 junction(mklink /J, 与产品 create_dir_alias 同产物)。"""
    r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True, text=True)
    assert r.returncode == 0, f"mklink /J 失败({link} -> {target}): {r.stdout} {r.stderr}"


def _space_negative_control(web_port: int, ih: str, files: list[tuple[str, int]], case: Path) -> None:
    """L490 负向对照: 跨卷 + 目标剩余严格小于 needed, 断言拒绝且零副作用。

    前置**只认显式入口** `QBT_REAL_SMALL_TARGET`(见 lib/small_target.py): 用户手动挂载
    ImDisk 内存盘(96M)并在其下建空目录; 守卫硬拒无盘符/系统卷/Recovery-System-EFI 卷标/
    hidden-system 属性/junction 跨卷路径。前置缺失或剩余不小于 needed 时**显式断言失败并
    给出挂载命令**, 不 skip。
    目标叶子故意不存在, 产品上溯到用户目录读卷剩余; L490 在一切搬运之前拒绝, 目标卷零写入。"""
    needed = sum(s for _n, s in files)
    target, free = small_target.require_small_target(needed)
    dst_neg = target / f"rm04_05_space_dst_{os.getpid()}"
    try:
        assert not dst_neg.exists(), f"目标叶子必须不存在(产品会上溯到 {target}): {dst_neg}"
        before = log_text(case).count("迁移发起")
        result = cmd_post_and_wait(
            web_port, f"/api/torrents/{ih}/location", {
                "location": str(dst_neg),
                "confirm": True
            }
        )
        assert result.get("status") == "error", \
            f"空间不足应被闸门 error 拒绝, 实际: {json.dumps(result, ensure_ascii=False)[:500]}"
        items = ((result or {}).get("truth") or {}).get("results") or []
        gates = [r for it in items for r in (it.get("reasons") or []) if r.get("gate") == "space"]
        assert gates, f"拒绝原因缺 gate=space: {json.dumps(items, ensure_ascii=False)[:400]}"
        assert any("空间不足" in str(r.get("text")) for r in gates), \
            f"L490 分支未命中(文案应为「空间不足」, 实际: {gates})"
        assert not [it for it in items if it.get("cls") == "started"], "空间不足却有 started 项(闸门失守)"
        assert log_text(case).count("迁移发起") == before, "空间不足却新增「迁移发起」(负向对照零副作用失守)"
        assert not dst_neg.exists(), f"空间不足却创建了目标叶子(目标卷被写入): {dst_neg}"
        assert free < needed, f"前置自证失败: free={free} needed={needed}"
    finally:
        # 只在闸门失守意外建了唯一 pid 叶子时清掉它; 不触碰用户目录内既有数据
        if dst_neg.exists():
            purge_tree(dst_neg)


def purge_tree(root) -> None:
    """删目录树, **绝不递归删穿链接**(计划 §08 红线 1): junction/symlink 只 os.rmdir 本体。

    rglob/glob 会跟随 junction 展开, 所以用 os.walk(topdown) 遇链接剪枝 + 根单独判;
    悬空 junction 的 lstat/rmdir 均可用(lstat 不跟随)。"""
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
    shutil.rmtree(root, ignore_errors=True)


def case_dir(name: str) -> Path:
    purge_tree(WORK / name)
    d = WORK / name
    d.mkdir(parents=True, exist_ok=True)
    return d


CONFIG_TEMPLATE = """\
config:
    schema_version: 8
    qbittorrent:
        host: 127.0.0.1
        port: {qb_port}
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
        enabled: true
        cross_group_conflict_check: {cross_group}
    trackers:
        rm04fake:
            domains: ["{fake_host}"]
    relocate:
        enabled: {relocate}
        alias_file_threshold: {alias_threshold}
    web:
        enabled: true
        host: 127.0.0.1
        port: {web_port}
        skip_local_verify: true
    notify:
        enabled: false
"""


def write_cfg(case: Path,
              *,
              cross_group: bool = False,
              relocate: bool = False,
              alias_threshold: int = 8) -> tuple[Path, int]:
    """生成临时配置(schema_version: 8, 直连副实例(SECONDARY), WEB 必开 —— 本片断言全走产品 WEB 只读端点)。

    product data_dir 指用例临时目录: journal/spec/pid/state 随目录清理, 不碰仓库根 auto-qb-data/。
    返回 (配置路径, web端口)。"""
    cfg = case / "config.yml"
    web_port = app.free_port()
    cfg.write_text(
        CONFIG_TEMPLATE.format(
            qb_port=instances.SECONDARY,
            data_dir=(case / "data").as_posix(),
            cross_group="true" if cross_group else "false",
            relocate="true" if relocate else "false",
            alias_threshold=alias_threshold,
            web_port=web_port,
            fake_host=FAKE_TRACKER_HOST,
        ),
        encoding="utf-8",
    )
    text = cfg.read_text(encoding="utf-8")
    if f"port: {instances.PRIMARY}" in text:
        raise AssertionError(f"配置指向了 {instances.PRIMARY}(真实种子), 拒跑: {cfg}")
    if "schema_version: 8" not in text:
        raise AssertionError(f"配置缺 schema_version: 8(会触发迁移改写), 拒跑: {cfg}")
    return cfg, web_port


def web_req(port: int, method: str, path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        method=method,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
    )
    if body is not None:
        req.add_header("Content-Type", "application/json")
    with _OPENER.open(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def wait_until(fn, timeout: float, desc: str | Callable[[], str], interval: float = 0.4):
    """轮询到 fn() 为真值并返回它; 超时抛 AssertionError 带最后一次观测。

    desc 支持 str 或惰性 callable(超时构造报错时才求值): 调用点拼带「最后观测值」的
    f-string desc 必须传 lambda —— str 在调用期求值, 超时报错里显示的是等待前的旧值
    而非超时时刻实况(issue 26-11-08-0044, RM07-11 首版踩过)。
    """
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = fn()
        if last:
            return last
        time.sleep(interval)
    raise AssertionError(f"等待超时({timeout}s): {desc() if callable(desc) else desc}; 最后观测: {last}")


def settle(qb, ih: str, timeout: float = 30.0) -> dict:
    """等种子走完 check/alloc 拿到稳定态。"""
    deadline = time.time() + timeout
    t: dict = {}
    while time.time() < deadline:
        t = qb.torrent(ih) or {}
        if t.get("state") in SETTLED:
            return t
        time.sleep(0.3)
    return t


def wait_complete(qb, ihs: list[str], timeout: float = 90.0) -> None:
    wait_until(
        lambda: all((qb.torrent(h) or {}).get("progress") == 1.0 for h in ihs),
        timeout,
        f"种子未完成校验: {ihs}",
    )


def norm(path) -> str:
    return str(path or "").replace("\\", "/").rstrip("/")


# ---- 假种子构造(带 real-fake 标签; --no-data 的文件表来自元数据, 与磁盘无关) ----


def fake_no_data(qb, name: str, size: int, savepath, salt: str, piece_len: int = torrent.PIECE_LEN) -> str:
    os.makedirs(savepath, exist_ok=True)  # savepath 得存在; 文件不写 ⇒ 永远 progress 0
    raw, ih = torrent.build_stream(name, size, "random", salt, ANNOUNCE, piece_len)
    _add_retry(qb, raw, str(savepath), ih)
    return ih


def fake_with_data(
    qb, name: str, size: int, savepath: Path, salt: str, piece_len: int = torrent.PIECE_LEN, write: bool = True
) -> str:
    """带数据单文件种子。write=False 时不落盘(同物理文件挂第二枚同组成员用:
    内容沿用先写成员的那份, 靠 piece_len 区分 infohash —— 见模块 docstring)。"""
    if write:
        torrent.write_file(str(savepath / name), size, "random", salt)
    raw, ih = torrent.build_from_path(str(savepath / name), name, ANNOUNCE, piece_len)
    _add_retry(qb, raw, str(savepath), ih)
    return ih


def fake_multi(
    qb,
    tname: str,
    files: list[tuple[str, int]],
    savepath: Path,
    salt: str,
    piece_len: int = torrent.PIECE_LEN,
    write: bool = True
) -> str:
    """多文件种子(子目录布局): files = [(含 tname 前缀的 posix 相对路径, 字节)]。

    目录别名的确定性成立条件(计划 §08 风险 7): 内容根 = save_path/<tname> 且目录专属。
    write=False 时数据不落盘(--no-data 形态)或沿用已落数据(同内容第二成员, 换 piece_len)。"""
    blob = bytearray()
    for rel, size in files:
        data = b"".join(torrent.chunks(size, "random", f"{salt}:{rel}"))
        if write:
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
    os.makedirs(savepath, exist_ok=True)  # savepath 得存在(qB 落内容根在其下)
    _add_retry(qb, raw, str(savepath), ih)
    return ih


# ---- groups 只读视图断言(GET /api/groups; 归组本身无日志, 数据源单点) ----


def groups_view(web_port: int) -> list[dict]:
    return web_req(web_port, "GET", "/api/groups")["groups"]


def group_row(groups: list[dict], h: str) -> dict | None:
    hits = [g for g in groups if any(m["hash"] == h for m in g["members"])]
    return hits[0] if hits else None


def decode_key(encoded: str) -> tuple:
    import base64
    arr = json.loads(base64.urlsafe_b64decode(encoded.encode("ascii")))
    return arr[0], tuple(arr[1])


def wait_group(web_port: int, h: str, members: set[str], timeout: float, desc: str) -> dict:
    """等 h 归进恰含 members 的组, 返回组行(供 key 解码断言)。"""
    def probe():
        g = group_row(groups_view(web_port), h)
        if g and {m["hash"] for m in g["members"]} == members:
            return g
        return None

    return wait_until(probe, timeout, desc)


def wait_store_progress(web_port: int, ihs: list[str], timeout: float = 40.0) -> None:
    """等产品 store 快照反映种子校验完成(progress==1.0)。

    relocate 闸门读的是**产品快照**的 progress, 与 qB 实际进度有 1-2 个同步拍滞后
    (实测: qB 侧已 1.0 而命令立刻下发 → 被 GATE_INCOMPLETE 拒)。组视图随进度变化
    置脏重建, 视图反映 1.0 ⇒ store 已 1.0, 且 store 只会单向前进, 无回退竞态。"""
    def probe():
        rows = {m["hash"]: m for g in groups_view(web_port) for m in g["members"]}
        if all(rows.get(h, {}).get("progress") == 1.0 for h in ihs):
            return True
        return None

    wait_until(probe, timeout, f"产品快照未反映种子完成: {[h[:8] for h in ihs]}")


def log_text(case: Path) -> str:
    return app.read_log(case)


def count_anchor(case: Path, anchor: str) -> int:
    return log_text(case).count(anchor)


def jobs_on_disk(case: Path) -> dict:
    """state.json 里的 relocate.jobs(权威 job 账; journal 只是 guardian 侧自述)。"""
    p = case / "data" / "state.json"
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    box = data.get("relocate") or {}
    return box.get("jobs") or {}


def journal_of(case: Path, job_id: str) -> dict | None:
    p = case / "data" / "relocate" / f"{job_id}.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def cmd_post_and_wait(web_port: int, path: str, body: dict, timeout: float = 30.0) -> dict:
    """投产品 WEB 命令并轮询回执到非 pending。"""
    receipt = web_req(web_port, "POST", path, body)
    cmd_id = receipt.get("cmd_id")
    if not cmd_id:
        return receipt  # 自投递命令无回执

    def probe():
        r = web_req(web_port, "GET", f"/api/cmd/{cmd_id}")
        return r if r.get("status") != "pending" else None

    return wait_until(probe, timeout, f"命令回执未落: {path}")


def one_started_item(result: dict) -> dict:
    """回执 truth.results 里挑 cls=started 的项(断言失败给全量现场)。"""
    items = ((result or {}).get("truth") or {}).get("results") or []
    started = [it for it in items if it.get("cls") == "started"]
    assert started, f"回执无 started 项: {json.dumps(result, ensure_ascii=False)[:600]}"
    return started[0]


def wait_job_phase(case: Path, job_id: str, phases: set[str], timeout: float, desc: str) -> dict:
    """等 state.json 落盘的 job 相位进入 phases(落盘周期 30S, 窗口按 30s+裕量给)。"""
    def probe():
        job = jobs_on_disk(case).get(job_id) or {}
        return job if job.get("phase") in phases else None

    return wait_until(probe, timeout, desc)


# ================================================================ RM04-01


def test_rm04_01_group_key_same_and_contrast():
    """[RM04-01] 归组 key: 同 save_path 同文件列表归同组, 异文件列表不同组(对照红验内建)

    前置: 产品非 dry-run 连 副实例, grouping.enabled=true(默认); 3 枚 --no-data 假种子
          (A/B 同名同 save_path 异 salt, C 异名同 save_path), 停在 stalledDL。
    副作用: 副实例 加 3 假种子(real-fake); 零文件系统写(仅 savepath 目录壳)。
    回滚: 删光 real-fake 种子 + 删用例目录。
    失败判据: A/B 未归同组; 或 C 与 A/B 归成一组(对照红验失效); 或出现
              「文件大小不一致」日志(3 枚同尺寸, 归组触发的一致性检查不得误报)。
    """
    case = case_dir("rm04_01")
    p = None
    try:
        qb = qbfake()
        assert not rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
        cfg, web_port = write_cfg(case)
        p = app.start(cfg, case)
        assert p.wait_web(40), f"WEB 没起来:\n{p.log()[-800:]}"

        savepath = WORK / "rm04_01"
        ha = fake_no_data(qb, "rm04c1.bin", 256 * 1024, savepath, "rm04c1-a")
        hb = fake_no_data(qb, "rm04c1.bin", 256 * 1024, savepath, "rm04c1-b")
        hc = fake_no_data(qb, "rm04c1other.bin", 256 * 1024, savepath, "rm04c1-c")
        settle(qb, ha)
        settle(qb, hb)
        settle(qb, hc)

        g = wait_group(web_port, ha, {ha, hb}, 25, "A/B(同名同表)未归同组")
        # 对照红验: 异文件列表必须不同组 —— 否则主断言恒绿(计划 §03 失败判据)
        gc = wait_group(web_port, hc, {hc}, 15, "C(异文件列表)未独立成组")
        assert hc not in {m["hash"] for m in g["members"]}, \
            f"对照失效: C 也归进了 A/B 的组, 归组 key 的文件列表维度丢失: {g['key']}"
        kpath, kfiles = decode_key(g["key"])
        assert norm(kpath) == norm(savepath), f"组键首元不是规范化 save_path: {kpath}"
        assert tuple(sorted(kfiles)) == ("rm04c1.bin", ), f"组键文件列表不符: {kfiles}"
        assert decode_key(gc["key"])[1] == ("rm04c1other.bin", ), "C 组键文件列表不符"
        assert "文件大小不一致" not in log_text(case), \
            "同尺寸成员归组出现「文件大小不一致」—— 组内一致性检查误报"
    finally:
        if p is not None:
            p.stop()
        rm_all_fakes(qbfake())
        purge_tree(case)


# ================================================================ RM04-02


def test_rm04_02_size_consistency_pauses_group():
    """[RM04-02] 组内大小一致性: 同文件列表不同声明大小 → 警告 + 整组暂停; 单成员组不误报

    前置: 同 RM04-01 基座; A/B --no-data 同名同 save_path、声明 256K/512K(相对路径同、
          大小不同); C --no-data 异名单成员组作对照。
    副作用: 副实例 加 3 假种子; A/B 整组被产品暂停(假种子, 允许)。
    回滚: 删光 real-fake 种子 + 删用例目录。
    失败判据: 日志无「文件大小不一致, 暂停整组」; 或 A/B 未变 stopped; 或单成员 C
              也被判不一致而暂停(误报)。
    """
    case = case_dir("rm04_02")
    p = None
    try:
        qb = qbfake()
        assert not rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
        cfg, web_port = write_cfg(case)
        p = app.start(cfg, case)
        assert p.wait_web(40), f"WEB 没起来:\n{p.log()[-800:]}"

        savepath = WORK / "rm04_02"
        ha = fake_no_data(qb, "rm04c2.bin", 256 * 1024, savepath, "rm04c2-a")
        hb = fake_no_data(qb, "rm04c2.bin", 512 * 1024, savepath, "rm04c2-b")
        hc = fake_no_data(qb, "rm04c2solo.bin", 256 * 1024, savepath, "rm04c2-c")
        settle(qb, ha)
        settle(qb, hb)
        settle(qb, hc)

        wait_until(lambda: "文件大小不一致, 暂停整组" in log_text(case), 25, "日志无「文件大小不一致, 暂停整组」(一致性检查没触发)")
        for h in (ha, hb):
            wait_until(
                lambda h=h: (qb.torrent(h) or {}).get("state", "").startswith("stopped"), 20, f"成员 {h[:8]} 未被整组暂停"
            )
        assert wait_group(web_port, ha, {ha, hb}, 15, "A/B 未归同组(前提不成立)")
        # 对照: 单成员组不得误报(C 保持下载态, 不被一致性检查误停)
        time.sleep(6)
        cst = (qb.torrent(hc) or {}).get("state", "")
        assert not cst.startswith("stopped"), f"对照失败: 单成员组 {hc[:8]} 被误判不一致而暂停({cst})"
    finally:
        if p is not None:
            p.stop()
        rm_all_fakes(qbfake())
        purge_tree(case)


# ================================================================ RM04-03


def test_rm04_03_missing_files_tag_and_contrast():
    """[RM04-03] 缺失文件标记: 真删文件 → MISSING 标签 + 整组暂停; 不删文件的对照组不打标

    前置: 两组各 2 枚带数据假种子(256K, 落 .work/rm04/rm04_03)成组; 完成后(上传态)
          组1 真删数据文件再 stop, 组2 只 stop 不删 —— 两条组都命中「上传转暂停」触发源。
    副作用: 真删用例目录下数据文件; 组1 两成员被加 MISSING 标签并暂停。
    回滚: 删光 real-fake 种子(连数据)+ 摘 MISSING 标签 + 删用例目录。
    失败判据: 组1 成员 tags 不含 MISSING; 或只有一枚被标(整组面丢失); 或未删文件的
              对照组也被打标(对照红验失效); 或「文件丢失」日志缺失。
    """
    case = case_dir("rm04_03")
    p = None
    try:
        qb = qbfake()
        assert not rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
        cfg, web_port = write_cfg(case)
        p = app.start(cfg, case)
        assert p.wait_web(40), f"WEB 没起来:\n{p.log()[-800:]}"

        savepath = WORK / "rm04_03"
        # 同组两枚共享同一物理文件: 先写的一份是唯一数据, 第二枚 write=False 换 piece_len
        h1a = fake_with_data(qb, "rm04c3.bin", 256 * 1024, savepath, "rm04c3-a1")
        h1b = fake_with_data(qb, "rm04c3.bin", 256 * 1024, savepath, "x", piece_len=32768, write=False)
        h2a = fake_with_data(qb, "rm04c3b.bin", 256 * 1024, savepath, "rm04c3-b1")
        h2b = fake_with_data(qb, "rm04c3b.bin", 256 * 1024, savepath, "x", piece_len=32768, write=False)
        wait_complete(qb, [h1a, h1b, h2a, h2b])
        assert wait_group(web_port, h1a, {h1a, h1b}, 20, "组1 未成组(前提不成立)")
        assert wait_group(web_port, h2a, {h2a, h2b}, 20, "组2 未成组(前提不成立)")

        # 触发源 = 种子由上传转暂停: 组1 真删数据文件, 两组全部 stop
        datafile = savepath / "rm04c3.bin"
        assert datafile.is_file()
        datafile.unlink()
        qb.pause(f"{h1a}|{h1b}|{h2a}|{h2b}")
        for h in (h1a, h1b, h2a, h2b):
            wait_until(
                lambda h=h: (qb.torrent(h) or {}).get("state", "").startswith("stopped"), 25, f"{h[:8]} 未进入暂停态(触发源没成立)"
            )

        # 组1: 整组 MISSING + 暂停; 组2(对照, 未删文件): 必须不打标 —— 否则主断言恒绿
        wait_until(
            lambda: all(MISSING_TAG in _tags_of(qb.torrent(h) or {}) for h in (h1a, h1b)),
            30,
            "组1 成员未全部打上 MISSING 标签(整组面丢失)",
        )
        assert "文件丢失, 暂停整组并添加标签" in log_text(case), "日志缺「文件丢失, 暂停整组并添加标签」"
        time.sleep(6)  # 再给两个 tick: 对照组若会被误标, 这里必然显形
        for h in (h2a, h2b):
            tags = sorted(_tags_of(qb.torrent(h) or {}))
            assert MISSING_TAG not in tags, \
                f"对照红验失效: 未删文件的组2 成员 {h[:8]} 也被打上 MISSING(tags={tags})"
    finally:
        if p is not None:
            p.stop()
        rm_all_fakes(qbfake())
        purge_tree(case)


# ================================================================ RM04-04


def test_rm04_04_cross_group_conflict_and_missing_exempt():
    """[RM04-04] 跨组文件冲突: 交叉 + 下载中参与者 → 警告 + 暂停下载方; MISSING 豁免对照; 开关关零警告

    前置: cross_group_conflict_check: true; 组 A 带数据完整(2 文件, stalledUP), 组 B
          --no-data(同内容根同名文件物理重叠, stalledDL 满足下载中谓词, 零外连)。
    副作用: 副实例 加 2 假种子; B(下载方)被暂停两次(初次 + 复发红验)。
    回滚: 删光 real-fake 种子(连数据)+ 摘标签 + 删两个用例目录。
    失败判据: 无「跨组文件交叉」警告; 或下载方未被暂停; 或完成侧被误暂停; 复发红验
              (resume 后再次警告+暂停)不成立; MISSING 豁免对照不豁免(resume 后仍被打断);
              开关关(false)时出现警告或暂停。
    """
    case = case_dir("rm04_04")
    p = None
    p2 = None
    try:
        qb = qbfake()
        assert not rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
        cfg, web_port = write_cfg(case, cross_group=True)
        p = app.start(cfg, case)
        assert p.wait_web(40), f"WEB 没起来:\n{p.log()[-800:]}"

        savepath = WORK / "rm04_04"
        # A/B 同内容根(rm04c4pack)同名文件物理重叠, 文件列表不同 ⇒ 两组; A 带数据完整,
        # B --no-data 停 stalledDL(实测满足 _is_active_download 谓词, 零外连; B 不校验数据,
        # 盐/分块随意 ⇒ 不与 A 共享内容约束)
        ha = fake_multi(
            qb,
            "rm04c4pack", [("rm04c4pack/shared4.bin", 128 * 1024), ("rm04c4pack/a2.bin", 64 * 1024)],
            savepath,
            "rm04c4-a",
            write=True
        )
        hb = fake_multi(
            qb,
            "rm04c4pack", [("rm04c4pack/shared4.bin", 128 * 1024), ("rm04c4pack/b2.bin", 64 * 1024)],
            savepath,
            "rm04c4-b",
            write=False
        )
        wait_complete(qb, [ha])
        settle(qb, hb)
        assert (qb.torrent(hb) or {}).get("state") == "stalledDL", "B 不是 stalledDL, 下载方前提不成立"

        # ---- 主断言: 警告 + 下载方被停 + 完成侧不误停
        wait_until(lambda: "跨组文件交叉" in log_text(case), 30, "无「跨组文件交叉」警告")
        wait_until(lambda: (qb.torrent(hb) or {}).get("state", "").startswith("stopped"), 20, "下载方 B 未被暂停")
        ast = (qb.torrent(ha) or {}).get("state", "")
        assert not ast.startswith("stopped"), f"完成侧 A 被误暂停(D2: 只停下载中成员): {ast}"
        n_warn_1 = count_anchor(case, "跨组文件交叉")

        # ---- 复发红验: B 恢复后必须再次警告+暂停(消除段把过期去重记录清掉才可能复发)
        qb.resume(hb)
        wait_until(lambda: count_anchor(case, "跨组文件交叉") > n_warn_1, 30, "B resume 后没有第二次警告(消除/复发链断了)")
        wait_until(lambda: (qb.torrent(hb) or {}).get("state", "").startswith("stopped"), 20, "复发红验: B 第二次未被暂停")

        # ---- MISSING 豁免对照: A 侧带 missing_tag 后事件必须被豁免(resume 不再被打断)
        qb.add_tags(ha, MISSING_TAG)
        time.sleep(3)  # 让产品先看到 tags 变化(脏组重算)
        qb.resume(hb)
        time.sleep(10)  # 4-5 个 tick: 若豁免分支失效, 这里必然再次警告+暂停
        n_warn_2 = count_anchor(case, "跨组文件交叉")
        assert n_warn_2 == n_warn_1 + 1, \
            f"豁免对照失效: A 带 MISSING 后 resume B 仍触发了新警告({n_warn_1 + 1} -> {n_warn_2})"
        bst = (qb.torrent(hb) or {}).get("state", "")
        assert not bst.startswith("stopped"), f"豁免对照失效: B 被再次暂停({bst})"

        # ---- 开关关(false)校验(并入收尾): 同现场零警告零暂停
        qb.pause(hb)
        p.stop()
        p = None
        case2 = case_dir("rm04_04_off")
        cfg2, _web_port2 = write_cfg(case2, cross_group=False)
        p2 = app.start(cfg2, case2)
        assert p2.wait_web(40), f"默认关校验进程没起来:\n{p2.log()[-600:]}"
        qb.resume(hb)
        time.sleep(10)
        assert "跨组文件交叉" not in log_text(case2), "开关关闭时仍出现「跨组文件交叉」警告(默认关失守)"
        assert not (qb.torrent(hb) or {}).get("state", "").startswith("stopped"), \
            "开关关闭时 B 仍被暂停(处置段没挂到开关上)"
    finally:
        if p is not None:
            p.stop()
        if p2 is not None:
            p2.stop()
        rm_all_fakes(qbfake())
        purge_tree(case)
        purge_tree(WORK / "rm04_04_off")


# ================================================================ RM04-05


def test_rm04_05_same_volume_relocate_dir_alias():
    """[RM04-05] 跨盘移动主链(同卷口径): C:→C: relocate → 目录别名 + 穿透 + journal phase=done
                  + GATE_SPACE 拒绝负向对照(L3)

    前置: relocate.enabled=true + alias_file_threshold: 1; 两枚带数据多文件假种子(子目录
          布局, 同文件列表同内容异 piece_len)在 RAM 落点(R: 盘缺席时退 .work/rm04/ram/)成组;
          dst = 用例目录 dst(与本机唯一可写卷 C: 同卷 —— 真跨卷半边 BLOCKED, 计划 §04 第 3 项)。
    同卷证明解锁(造法校准, 探针实测): qB 副实例默认 save_path 指向不存在的 R: 盘 ⇒
          free_space_on_disk 恒 -1 ⇒ same_volume_proof 必败 ⇒ 多成员组被 GATE_SAME_FS 拒;
          用例临时把 56590 的 save_path 改指 C: 现存目录(qB 立即报出 C: 真值), 测毕逐字还原。
    触发 = 产品 WEB POST /api/torrents/{hash}/location (confirm=true, 目录别名提议需二次确认)。
    负向对照(先于主链, 红验 = 给足 dst 即过): dst_neg = Z:/rm04_05_neg_ctl/dst(Z: 不存在盘,
          上溯整链不可判定) → GATE_SPACE「剩余空间不可判定」拒绝 —— 回执 error + reasons 含
          gate=space + 零 started 零「迁移发起」(零副作用)。
    L490 空间不足负向对照(2026-11-02 issue 26-11-02-1208, 复验改为显式入口): 组数据
          2×64MiB=128MiB; 前置只认 QBT_REAL_SMALL_TARGET 指向的小容量卷空目录(lib/small_target.py
          硬守卫: 带盘符/非系统卷/非 Recovery-System-EFI 卷标/无 hidden-system/reparse point/
          st_dev 与盘符根一致), 前置缺失或剩余不小于 needed 时显式失败并给准备指引, 不 skip。
          **已废弃并移除**: 上一轮曾用无盘符隐藏 Recovery 卷经 junction 造前置(见同函数 docstring
          与 issue 更正记录), 该做法不许可再引入; tests/test_real_machine_safety.py 源码扫描守卫
          保证一旦复发即红。
          本段置于主链之后: 主链仍全跑; 前置缺失时只本段显式失败, 不掩盖主链结果。
    副作用: qB 真搬数据(R:/qbt-fake/rm04 → D: case/dst); src 内容根变 junction 指向 dst;
          <data_dir>/relocate/ 落账; 副实例 save_path 临时改写(finally 还原并核验)。
    回滚: 副实例 save_path 还原; 删 junction 只 os.rmdir 本体(禁递归删穿); 删光 real-fake 种子;
          删用例目录 + RAM 树。用户小容量目录只读剩余/不建叶子, 无需清理; 若闸门失守意外建了
          叶子, finally 只删该唯一 pid 叶子(不触碰目录内既有数据)。
    失败判据: dst 缺席却 started/「迁移发起」(闸门失守); L490 对照未以「空间不足」拒绝或出现
              started/「迁移发起」/目标叶子被创建; 主链回执无 started; save_path 未变 dst(归一后比);
              dst 侧 size 不齐; src 内容根未成 junction; 经原路径穿透读不到同 size; journal 未落
              phase=done; 日志缺「迁移发起」/「已武装收尾」; save_path 未还原。
    """
    case = case_dir("rm04_05")
    p = None
    qb = qbfake()
    orig_save_path = qb.prefs().get("save_path")
    assert orig_save_path, "副实例 save_path 读取失败(鉴权/连不通?), 拒跑"
    try:
        assert not rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
        # ---- 同卷证明解锁: save_path 临时改指 C: 现存目录(探针实测 free_space_on_disk 立即跟真值)
        probe_dir = case / "qbsave"
        probe_dir.mkdir(parents=True, exist_ok=True)
        qb.set_prefs(save_path=str(probe_dir))
        time.sleep(0.5)
        assert qb.prefs().get("save_path") == str(probe_dir), \
            "save_path 临时改写未生效(同卷证明解锁不成立, 多成员组会被 GATE_SAME_FS 拒)"

        src = RAM / "rm04_05" / "src"
        dst = case / "dst"
        # 负向对照专用路径: Z: 不存在盘, 上溯整链不可判定 → GATE_SPACE target_free=None + same_volume=None
        # 真实命中(方案A, 2026-11-02 issue 26-11-02-1144): 原 dst=case/"dst" 在环境2 C盘充足时
        # 上溯父目录即命中 73GB free + same_volume=True → 闸门放行(设计正确, 红验前提写窄)
        dst_neg = Path("Z:/rm04_05_neg_ctl/dst")
        purge_tree(src.parent)
        cfg, web_port = write_cfg(case, relocate=True, alias_threshold=1)
        p = app.start(cfg, case)
        assert p.wait_web(40), f"WEB 没起来:\n{p.log()[-800:]}"
        assert p.wait_log("整组迁移已启用", 20), \
            f"relocate 启动日志缺失(开关没生效?):\n{p.log()[-600:]}"

        # 组数据 128MiB: 超过 ImDisk 96M 盘格式化后的剩余(~80MiB), 让 L490「空间不足」前置成立
        files = [("rm04c5/sub/a.bin", 64 * 1024 * 1024), ("rm04c5/sub/b.bin", 64 * 1024 * 1024)]
        h1 = fake_multi(qb, "rm04c5", files, src, "rm04c5", write=True)  # 数据只写这一份
        h2 = fake_multi(qb, "rm04c5", files, src, "rm04c5", piece_len=32768, write=False)
        wait_complete(qb, [h1, h2])
        assert wait_group(web_port, h1, {h1, h2}, 20, "两成员未成组(前提不成立)")
        wait_store_progress(web_port, [h1, h2])  # 闸门读产品快照, 等 1-2 个同步拍追平

        # ---- 负向对照(L3 兑现): 不存在盘 Z: dst_neg → GATE_SPACE 上溯整链不可判定拒绝(零副作用)
        #      原 dst=case/"dst" 在 C盘充足时上溯父目录即命中 free_space + same_volume → 闸门放行,
        #      红灯失守(issue 26-11-02-1144)。改用 Z:/... 让 _volume_free_resolved 上溯整链失败 → None
        #      + _same_volume_resolved 上溯整链失败 → None → GATE_SPACE 条件真实命中。
        result = cmd_post_and_wait(
            web_port, f"/api/torrents/{h1}/location", {
                "location": str(dst_neg),
                "confirm": True
            }
        )
        assert result.get("status") == "error", \
            f"dst 缺席应被闸门 error 拒绝, 实际: {json.dumps(result, ensure_ascii=False)[:500]}"
        neg_items = ((result or {}).get("truth") or {}).get("results") or []
        neg_gates = [r.get("gate") for it in neg_items for r in (it.get("reasons") or [])]
        assert "space" in neg_gates, f"拒绝原因缺 gate=space: {neg_gates}; items={json.dumps(neg_items, ensure_ascii=False)[:400]}"
        assert not [it for it in neg_items if it.get("cls") == "started"], "dst 缺席却有 started 项(闸门失守)"
        assert "迁移发起" not in log_text(case), "dst 缺席却出现「迁移发起」(负向对照零副作用失守)"

        # ---- 主链: 预建 dst → 目录别名搬迁(confirm=true 过二次确认)
        dst.mkdir(parents=True, exist_ok=True)
        result = cmd_post_and_wait(web_port, f"/api/torrents/{h1}/location", {"location": str(dst), "confirm": True})
        item = one_started_item(result)
        job_id = item.get("job_id")
        assert job_id, f"回执 started 项缺 job_id: {json.dumps(item, ensure_ascii=False)[:400]}"
        assert "迁移发起" in log_text(case), "日志缺「迁移发起」(搬迁没有真正下发)"

        # ---- qB 侧: save_path 变 dst + dst 数据 size 对齐
        wait_until(
            lambda: norm((qb.torrent(h1) or {}).get("save_path")) == norm(dst), 60, lambda:
            (f"mover save_path 未变 dst: {(qb.torrent(h1) or {}).get('save_path')}")
        )
        for rel, size in files:
            f = dst / rel
            wait_until(lambda f=f, size=size: f.is_file() and f.stat().st_size == size, 30, f"dst 侧文件未对齐: {f}")
        # ---- 别名面: src 内容根 = junction → dst; 穿透 = 经原路径 stat 读到同 size
        content_root = src / "rm04c5"
        wait_until(lambda: _is_link(content_root), 30, f"src 内容根未成链接: {content_root}")
        assert reparse_kind(content_root) == "junction", \
            f"src 内容根链接形态非 junction: {reparse_kind(content_root)}"
        for rel, size in files:
            via_src = src / rel
            wait_until(
                lambda via_src=via_src, size=size: via_src.is_file() and via_src.stat().st_size == size,
                15,
                f"穿透校验失败(经原路径读不到同 size): {via_src}"
            )
        wait_until(lambda: "已武装收尾" in log_text(case), 30, "日志缺「已武装收尾」(arm 段没走)")

        # ---- 收口: 成员2 仍指 src(经别名读得到数据), 经 qB 原生 setLocation 跟进 dst
        #      (ACT_DONE_EXTERNAL 的「已被外部完成」判据: 全员 save_path==dst + 链接在 + qB 在)
        qb.set_location(h2, str(dst))
        wait_until(lambda: norm((qb.torrent(h2) or {}).get("save_path")) == norm(dst), 30, "成员2 的 qB setLocation 未生效")
        job = wait_job_phase(case, job_id, {"done"}, 90, "job 未推进到 done(reason=external 预期)")
        assert job.get("reason") == "external", f"job done 但 reason={job.get('reason')}: {job}"
        jr = journal_of(case, job_id)
        assert jr and jr.get("phase") == "done", f"journal 未落 phase=done: {jr}"

        # ---- 负向对照2(L490 空间不足分支): 放在主链之后, 前置缺失只红本段, 不掩盖主链结果
        #      显式入口 QBT_REAL_SMALL_TARGET; 守卫见 lib/small_target.py; 不再自动枚举/挂接隐藏卷
        _space_negative_control(web_port, h1, files, case)
    finally:
        if p is not None:
            p.stop()
        qb.set_prefs(save_path=orig_save_path)
        time.sleep(0.3)
        restored = qb.prefs().get("save_path")
        assert restored == orig_save_path, f"副实例 save_path 未还原: {restored!r} != {orig_save_path!r}"
        rm_all_fakes(qbfake())
        purge_tree(case)
        purge_tree(RAM / "rm04_05")


# ================================================================ RM04-06


def test_rm04_06_journal_recovery_after_crash():
    """[RM04-06] journal 恢复: 搬迁中强杀产品 → 重启恢复在途 job → 推进到 done(真杀优先, 注入兜底)

    前置: relocate.enabled=true; 单成员带数据假种子 64M 落 R:(拉长 qB 搬运窗口);
          命中「迁移发起」日志即 taskkill /F /T。state 未及落盘时(30S 周期)走计划批准的
          注入退路: 停机态把 phase=moving/move_issued=true 的 job 账写进 state.json
          (job_to_dict 形)+ journal/spec, 重启后走 _recover 的 RESUME 分支。
    副作用: 产品进程被强杀; 重启后继续推进到 done; 注入分支改写 state.json。
    回滚: 删光 real-fake 种子(连数据)+ 删用例目录 + RAM 树。
    失败判据: state 里有非终态 job 而重启日志「恢复在途 job」计 0 条(恢复面失效, 红验即此);
              job 卡在 moving 不推进; 已搬好的数据被再搬一遍(dst size 变化); 带崩进程/堆栈。
    """
    case = case_dir("rm04_06")
    p = None
    try:
        qb = qbfake()
        assert not rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
        src = RAM / "rm04_06" / "src"
        dst = case / "dst"
        purge_tree(src.parent)
        cfg, web_port = write_cfg(case, relocate=True)
        name = "rm04c6.bin"
        size = 64 * 1024 * 1024
        h = fake_with_data(qb, name, size, src, "rm04c6")
        # 预热起停: 生成合法 state.json(强杀发生在 30S 落盘周期内时, 注入退路才有底座可写)
        p = app.start(cfg, case, graceful_after=6.0)
        rc = p.wait(90)
        assert rc == 0, f"预热起停退出码 {rc}:\n{p.log()[-600:]}"
        p = None
        assert (case / "data" / "state.json").is_file(), "预热退出后 state.json 没落盘"

        p = app.start(cfg, case)
        assert p.wait_web(40), f"WEB 没起来:\n{p.log()[-800:]}"
        assert p.wait_log("整组迁移已启用", 20), f"relocate 启动日志缺失:\n{p.log()[-600:]}"
        wait_complete(qb, [h])
        wait_store_progress(web_port, [h])  # 闸门读产品快照, 等 1-2 个同步拍追平
        dst.mkdir(parents=True, exist_ok=True)  # 目标卷空间闸门要读 dst(不存在 = 不可判定 = 拒)

        # ---- 真杀窗口: 「迁移发起」一落日志即强杀(taskkill /F /T 整树)
        result = cmd_post_and_wait(web_port, f"/api/torrents/{h}/location", {"location": str(dst)})
        one_started_item(result)
        killed = False
        deadline = time.time() + 20.0
        while time.time() < deadline:
            if "迁移发起" in app.read_log(case):
                p.kill()
                killed = True
                break
            time.sleep(0.05)
        assert killed, "20s 内没观测到「迁移发起」日志, 强杀窗口没抓住"
        assert not p.alive(), "taskkill 后进程仍活着"
        p = None

        # qB 的搬运不随产品死(独立进程): 等它搬完, 现场定为「数据已在 dst」
        wait_until(
            lambda: norm((qb.torrent(h) or {}).get("save_path")) == norm(dst), 90,
            "强杀后 qB 未把数据搬到 dst(64M 跨卷搬运 90s 未完成, 环境异常)"
        )
        dst_size_before = (dst / name).stat().st_size

        disk_jobs = jobs_on_disk(case)
        # 恢复路径留痕(落 .work, 随 clean 清; 基线切片引用): 真杀赶没赶上 30S 落盘窗口
        marker = WORK / "rm04_06_recovery_path.txt"
        marker.parent.mkdir(parents=True, exist_ok=True)
        if not disk_jobs:
            # ---- 注入退路(计划 §03 RM04-06 明文批准): 停机态按 job_to_dict 形造 phase=moving 账
            sp = case / "data" / "state.json"
            assert sp.is_file(), "state.json 不存在, 注入底座不成立"
            injected = {
                "job_id": "rm04c6recovery",
                "hashes": [h],
                "mover": h,
                "src": src.as_posix(),
                "dst": dst.as_posix(),
                "scope": src.as_posix(),
                "alias_kind": "",
                "alias_paths": [],
                "phase": "moving",
                "reason": "",
                "armed_at": 0.0,
                "updated_at": time.time(),
                "resume_hashes": [],
                "attempts": 0,
                "last_error": "",
                "plan": {
                    "form": "direct",
                    "link_kind": None,
                    "scope": src.as_posix(),
                    "files": [[name, size]]
                },
                "move_issued": True,
            }
            data = json.loads(sp.read_text(encoding="utf-8"))
            data.setdefault("relocate", {}).setdefault("jobs", {})["rm04c6recovery"] = injected
            sp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            rdir = case / "data" / "relocate"
            rdir.mkdir(parents=True, exist_ok=True)
            (rdir / "rm04c6recovery.json"
            ).write_text(json.dumps({
                "phase": "moving",
                "ts": time.time()
            }, ensure_ascii=False), encoding="utf-8")
            (rdir / "rm04c6recovery.spec.json").write_text("{}", encoding="utf-8")
            marker.write_text("journal-injection(state 未及落盘, 计划 §03 批准的退路)", encoding="utf-8")
            expect_job_id = "rm04c6recovery"
        else:
            expect_job_id = next(iter(disk_jobs))  # 真杀路径: 30S 落盘赶上了搬迁窗口
            marker.write_text("real-kill", encoding="utf-8")

        # ---- 重启: 恢复在途 job → 推进到终态
        # 日志是追加式: 全文里已有预热轮/强杀前轮的多条「整组迁移已启用」行 —— wait_log 会
        # 撞上旧行立刻返回, 必须等**新行**出现再取计数(实测: 直接 findall 恒取到旧轮的 0)
        n_start_lines = len(re.findall(r"整组迁移已启用\(恢复在途 job (\d+) 条\)", log_text(case)))
        p = app.start(cfg, case)
        try:
            wait_until(
                lambda: len(re.findall(r"整组迁移已启用\(恢复在途 job (\d+) 条\)", log_text(case))) > n_start_lines, 40,
                "重启后没有新的 relocate 启动日志行(进程没起来?)"
            )
            counts = re.findall(r"整组迁移已启用\(恢复在途 job (\d+) 条\)", log_text(case))
            recovered = int(counts[-1]) if counts else 0
            assert recovered >= 1, \
                f"红验失败: state 里有非终态 job({expect_job_id}), 重启却计 {recovered} 条 —— 恢复面失效"
            assert expect_job_id in jobs_on_disk(case), "恢复计数对不上 state 里的 job"
            # 恢复判据日志(_recover 三分流至少留一行; 补发路径另有「已下发 qB 搬迁」)
            wait_until(
                lambda: any(a in app.read_log(case) for a in ("恢复: ", "补发", "已下发 qB 搬迁")), 30, "恢复判据日志缺失(_recover 未跑)"
            )
            wait_job_phase(case, expect_job_id, {"done", "cancelled"}, 150, "恢复后 job 卡在 moving 不推进(恢复面失效)")
            assert (dst / name).stat().st_size == dst_size_before, \
                "恢复过程把已搬好的数据又搬了一遍(对账判据应幂等)"
            assert (dst / name).stat().st_size == size, "dst 数据 size 与种子声明不符"
            assert p.alive(), "恢复过程把进程带崩了"
            assert "Traceback" not in p.log(), "恢复路径出现未捕获异常堆栈"
        finally:
            if p is not None:
                p.stop()
                p = None
    finally:
        if p is not None:
            p.stop()
        rm_all_fakes(qbfake())
        purge_tree(case)
        purge_tree(RAM / "rm04_06")


# ================================================================ RM04-07


def test_rm04_07_corrupt_journal_and_orphan_pid():
    """[RM04-07] journal 异常形态兜底: 损坏 journal / 孤儿 pid 不崩 + 走到终态

    前置: 先优雅起停一次生成合法 state.json; 停机态注入 armed job(job_to_dict 形)+
          真建 junction(src 内容根 → dst)+ 写坏 journal(非 JSON)+ 留孤儿 .pid(指向
          已死进程); 种子 save_path 已在 dst(数据齐)。
    副作用: journal 被产品按现场定夺重写(phase=done); job 对账收口。
    回滚: 删 junction 只 os.rmdir 本体 + 删光 real-fake 种子 + 删用例目录 + RAM 树。
    失败判据: 产品启动崩溃/退出; job 永不终态(坏账/孤儿 pid 把对账挡死在 WAIT);
              日志出现未捕获异常堆栈; journal 没有被现场定夺重写。
    """
    case = case_dir("rm04_07")
    p = None
    try:
        qb = qbfake()
        assert not rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
        src = RAM / "rm04_07" / "src"
        dst = case / "dst"
        purge_tree(src.parent)
        cfg, _web_port = write_cfg(case, relocate=True)
        job_id = "rm04c7armed"
        files = [("rm04c7/a.bin", 256 * 1024)]
        # 种子直接落 dst(armed 现场 = 数据已在目标位置); src 侧只放 junction
        h = fake_multi(qb, "rm04c7", files, dst, "rm04c7", write=True)
        wait_complete(qb, [h])

        # 优雅起停一次: 生成合法 state.json(带 schema_version 章), 注入才有干净底座
        p = app.start(cfg, case, graceful_after=6.0)
        rc = p.wait(90)
        assert rc == 0, f"预热起停退出码 {rc}:\n{p.log()[-600:]}"
        p = None
        sp = case / "data" / "state.json"
        assert sp.is_file(), "预热退出后 state.json 没落盘, 注入底座不成立"

        src_content_root = src / "rm04c7"
        src.mkdir(parents=True, exist_ok=True)
        make_junction(src_content_root, dst / "rm04c7")
        assert reparse_kind(src_content_root) == "junction", "junction 没建出来, 注入现场不成立"

        job = {
            "job_id": job_id,
            "hashes": [h],
            "mover": h,
            "src": src.as_posix(),
            "dst": dst.as_posix(),
            "scope": src_content_root.as_posix(),
            "alias_kind": "dir",
            "alias_paths": [src_content_root.as_posix()],
            "phase": "armed",
            "reason": "",
            "armed_at": time.time(),
            "updated_at": time.time(),
            "resume_hashes": [],
            "attempts": 0,
            "last_error": "",
            "plan":
                {
                    "form": "dir_alias",
                    "link_kind": "junction",
                    "scope": src_content_root.as_posix(),
                    "files": [[rel, s] for rel, s in files]
                },
            "move_issued": True,
        }
        data = json.loads(sp.read_text(encoding="utf-8"))
        data.setdefault("relocate", {}).setdefault("jobs", {})[job_id] = job
        sp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

        rdir = case / "data" / "relocate"
        rdir.mkdir(parents=True, exist_ok=True)
        (rdir / f"{job_id}.json").write_bytes(b"\xff\xfe NOT-JSON {{{ nope")  # 坏账: _read_json 应回 None
        # 孤儿 pid: 指向一个确实已死的进程(起一个睡着的 python 再杀掉, 拿真死 pid)
        victim = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
        victim_pid = victim.pid
        victim.kill()
        victim.wait(10)
        (rdir / f"{job_id}.pid").write_text(json.dumps({"pid": victim_pid, "ts": time.time()}), encoding="utf-8")

        # 带伤启动: 坏 journal 按 None 回退现场定夺; 孤儿 pid 判死不挡对账; 收口 done(external)
        p = app.start(cfg, case)
        try:
            assert p.wait_log("整组迁移已启用(恢复在途 job 1 条)", 40), \
                f"启动日志缺恢复行(注入 job 没被读到):\n{p.log()[-800:]}"
            wait_job_phase(case, job_id, {"done", "cancelled"}, 90, "job 永不终态(坏账/孤儿 pid 把对账挡死在 WAIT)")
            jr = journal_of(case, job_id)
            assert jr and jr.get("phase") == "done", \
                f"journal 没有被现场定夺重写为 done(仍是坏账或旧相位): {jr}"
            assert p.alive(), "带伤启动把进程带崩了"
            assert "Traceback" not in p.log(), "对账路径出现未捕获异常堆栈"
        finally:
            if p is not None:
                p.stop()
                p = None
    finally:
        if p is not None:
            p.stop()
        rm_all_fakes(qbfake())
        purge_tree(case)
        purge_tree(RAM / "rm04_07")


# ================================================================ RM04-08


def test_rm04_08_save_path_change_regroup():
    """[RM04-08] 保存路径变化 → 重归组(组 key 路径变化面)+ 缺文件扫描被触发且文件齐全零动作

    前置: 两枚带数据假种子成组落 .work/rm04/rm04_08/src; 绕过 relocate 闸门, 用
          lib/qb.py 对 qB 直发 setLocation 到 .work/rm04/rm04_08/moved(qB 原生搬)。
    副作用: qB 真搬数据(用例目录内); 组 key 变化(旧键解散/新键建立)。
    回滚: 删光 real-fake 种子(连数据)+ 删 .work/rm04/rm04_08 整树。
    失败判据: groups 视图无新 key/仍持旧 key; 成员从组里丢失(重归组丢成员);
              文件齐全却被打 MISSING(重归组触发扫描误报); 出现「路径不可判定」警告。
    """
    case = case_dir("rm04_08")
    p = None
    try:
        qb = qbfake()
        assert not rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
        src = WORK / "rm04_08" / "src"
        moved = WORK / "rm04_08" / "moved"
        cfg, web_port = write_cfg(case)
        p = app.start(cfg, case)
        assert p.wait_web(40), f"WEB 没起来:\n{p.log()[-800:]}"

        # 同组两枚共享同一物理文件: 数据只写一份, 第二枚换 piece_len(同内容异 infohash)
        h1 = fake_with_data(qb, "rm04c8.bin", 256 * 1024, src, "rm04c8")
        h2 = fake_with_data(qb, "rm04c8.bin", 256 * 1024, src, "x", piece_len=32768, write=False)
        wait_complete(qb, [h1, h2])
        g_old = wait_group(web_port, h1, {h1, h2}, 20, "两成员未成组(前提不成立)")
        old_key = g_old["key"]
        assert norm(decode_key(old_key)[0]) == norm(src), f"旧组键路径不符: {decode_key(old_key)[0]}"

        # ---- qB 直改位置(绕开 relocate 闸门正是本意: 验产品的路径变化检测)
        qb.set_location(f"{h1}|{h2}", str(moved))
        wait_until(
            lambda: all(norm((qb.torrent(h) or {}).get("save_path")) == norm(moved) for h in (h1, h2)), 60,
            "qB setLocation 后 save_path 未变 moved"
        )

        # ---- 重归组: 新键建立(路径=moved, 成员不丢), 旧键消失
        def new_group():
            g = group_row(groups_view(web_port), h1)
            if g and {m["hash"] for m in g["members"]} == {h1, h2} and g["key"] != old_key:
                return g
            return None

        g_new = wait_until(new_group, 30, "重归组没有发生(新组键未出现或成员丢失)")
        kpath, kfiles = decode_key(g_new["key"])
        assert norm(kpath) == norm(moved), f"新组键首元不是 moved: {kpath}"
        assert tuple(sorted(kfiles)) == ("rm04c8.bin", ), f"新组键文件列表不符: {kfiles}"
        assert all(g["key"] != old_key for g in groups_view(web_port)), "旧键仍挂在视图上(未解散)"

        # ---- 重归组即触发缺文件扫描, 文件齐全 ⇒ 零动作(不误标不误停)
        time.sleep(8)  # 4-5 个 tick: 误报若在, 必然显形
        for h in (h1, h2):
            t = qb.torrent(h) or {}
            tags = sorted(_tags_of(t))
            assert MISSING_TAG not in tags, f"文件齐全却被打 MISSING(扫描误报): {h[:8]} tags={tags}"
            assert not t.get("state", "").startswith("stopped"), \
                f"文件齐全却被整组暂停: {h[:8]} state={t.get('state')}"
        log = log_text(case)
        assert "文件丢失" not in log, "文件齐全却出现「文件丢失」日志"
        assert "路径不可判定" not in log, "踩中 fs.path_map「路径不可判定」分支(计划 §05: 记 BLOCKED 口径)"
    finally:
        if p is not None:
            p.stop()
        rm_all_fakes(qbfake())
        purge_tree(case)


# ================================================================ RM04-09


def test_rm04_09_facade_share_limits_end_to_end():
    """[RM04-09] facade share_limits_mode 5.2.3 端到端: WebUI set_share_limits → 恒发
                  shareLimitsMode="Default" → qB 回读命中 + 不存在 hash 静默零副作用负向(L3)

    前置: 副实例 1 枚带数据假种子(显式落点 .work/rm04/rm04_09)+ 产品进程连副实例
          (写侧面基座同 RM04-01; 56590 localhost 免鉴权 = 环境2 标准配置)。
    动作: WebUI 命令线 POST /api/torrents/{h}/share-limits(ratio_limit=3.5 / seeding_time_limit=90)。
    断言: 入队回执形状(queued+cmd_id) + 终态回执 status=ok(5.2 忽略未知参 shareLimitsMode
          —— facade 恒发 "Default", 库对 5.2 无副作用) + qB 侧 ratio_limit/seeding_time_limit
          直接回读命中(不经产品快照) + 产品日志「分享限制更新」恰 1 行。
    负向(L3, 回执形态开工探针已核实): 不存在 hash → store.get None 静默 return
          (commands.py _cmd_set_share_limits 入口守卫), drain 仍补写 ok 回执 —— 断言 = 回执
          ok 且「分享限制更新」日志行数零新增(该行只在 api 调用成功后打)且真实种子限值原样
          (零副作用)。守卫若失守: qB 对不存在 hash 返回 404 → 回执 error 或日志出现行 → 红。
    副作用: 副实例 1 枚假种子(带数据, 收尾连数据删); 假种子 ratio/seeding_time 限值被改。
    回滚: 删光 real-fake 种子(连数据)+ 删用例目录。
    失败判据: 回执非 ok; qB 回读值不符(facade 传参失真/库丢参); 日志缺「分享限制更新」;
              不存在 hash 触发 qB 调用(404/回执 error)或改动了任何种子限值(静默 return 失守)。
    """
    case = case_dir("rm04_09")
    p = None
    try:
        qb = qbfake()
        assert not rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
        cfg, web_port = write_cfg(case)
        p = app.start(cfg, case)
        assert p.wait_web(40), f"WEB 没起来:\n{p.log()[-800:]}"

        savepath = WORK / "rm04_09"
        h = fake_with_data(qb, "rm04c9.bin", 256 * 1024, savepath, "rm04c9")
        wait_complete(qb, [h])
        wait_store_progress(web_port, [h])  # 等 store 快照收录该 hash(store.get 是命令入口守卫)

        ratio, seed_minutes = 3.5, 90
        base = log_text(case).count("分享限制更新")

        # ---- 负向对照(L3): 不存在 hash → 静默 return 零 qB 调用零副作用
        unknown = "0" * 40
        result = cmd_post_and_wait(
            web_port, f"/api/torrents/{unknown}/share-limits", {
                "ratio_limit": ratio,
                "seeding_time_limit": seed_minutes
            }
        )
        assert result.get("status") == "ok", \
            f"不存在 hash 应回执 ok(静默 return), 实际: {json.dumps(result, ensure_ascii=False)[:500]}"
        assert log_text(case).count("分享限制更新") == base, \
            "不存在 hash 却出现「分享限制更新」日志行(入口守卫失守, api 调用发生了)"
        before = qb.torrent(h) or {}
        assert float(before.get("ratio_limit") or 0) != ratio, "负向对照前提不成立: 主种子限值碰巧已是目标值"

        # ---- 主链: WebUI 命令线 set_share_limits → facade 恒发 shareLimitsMode="Default" → 5.2 生效
        result = cmd_post_and_wait(
            web_port, f"/api/torrents/{h}/share-limits", {
                "ratio_limit": ratio,
                "seeding_time_limit": seed_minutes
            }
        )
        assert result.get("status") == "ok", f"回执非 ok: {json.dumps(result, ensure_ascii=False)[:500]}"
        wait_until(lambda: log_text(case).count("分享限制更新") == base + 1, 15, "日志缺「分享限制更新」行(命令没走到 api 调用)")

        # qB 直接回读(不经产品快照): 5.2 忽略未知参 shareLimitsMode, 两维限值必须落上
        def _readback():
            t = qb.torrent(h) or {}
            try:
                return (float(t.get("ratio_limit")), int(t.get("seeding_time_limit"))) \
                    if t.get("ratio_limit") is not None and t.get("seeding_time_limit") is not None else None
            except (TypeError, ValueError):
                return None

        got = wait_until(_readback, 20, "qB 侧 ratio_limit/seeding_time_limit 回读超时(快照缺字段)")
        gr, gs = got
        assert abs(gr - ratio) < 1e-6, f"ratio_limit 回读不符: 期望 {ratio}, 实得 {gr}(facade 传参失真?)"
        assert gs == seed_minutes, f"seeding_time_limit 回读不符: 期望 {seed_minutes}, 实得 {gs}(facade 传参失真?)"
    finally:
        if p is not None:
            p.stop()
        rm_all_fakes(qbfake())
        purge_tree(case)


# ================================================================ RM04-10


def _file_state(p: Path) -> dict:
    return {"size": p.stat().st_size, "sha1": hashlib.sha1(p.read_bytes()).hexdigest()}


def _assert_unchanged(p: Path, before: dict, what: str) -> None:
    """断言磁盘条目仍在原路径且内容逐字节未变(被迁移/删除/顺手改写都会红)。"""
    assert p.is_file(), f"{what} 不在了(被迁移/删除): {p}"
    now = _file_state(p)
    assert now["size"] == before["size"], f"{what} 大小被改: {before['size']} -> {now['size']}: {p}"
    assert now["sha1"] == before["sha1"], f"{what} 内容被改(sha1 不符): {p}"


def _gates_of(result: dict) -> list[str]:
    items = ((result or {}).get("truth") or {}).get("results") or []
    return [r.get("gate") for it in items for r in (it.get("reasons") or [])]


def _has_started(result: dict) -> bool:
    items = ((result or {}).get("truth") or {}).get("results") or []
    return bool([it for it in items if it.get("cls") == "started"])


def test_rm04_10_qbtemp_narrow_foreign_allowed_own_blocked():
    """[RM04-10] .!qB 窄域(S1/S2/R1/R2)真机复验: 组外 .!qB 不拦迁移且原地不动; 组内 .!qB 仍硬拦;
    目标叶子未建(上溯) + 同卷 note; 目标为文件 target_type; 普通条目不受影响。

    对应: plans/26-11-02-0134-plan-relocate-qbtemp-narrow.html §07 风险对策 +
          tasks/26-11-02-backend-relocate-qbtemp-narrow.md S5 真机复验。
    前置: 副实例; grouping+relocate 开; G1 单成员已完成(迁移主体); G2 --no-data 未完成(外部组,
          手造 g2.!qB); G3 单成员已完成(手造 g3.!qB 作本组未落定对照); keep.txt 无主杂项;
          目标 dst 叶子不存在、与 src 同卷、父目录存在(命中 R1 上溯 + R2 #1 同卷)。
    副作用: 副实例加 3 枚 real-fake; 1 次真迁移(G1 单成员 direct) + 3 次闸门拒绝; 用例目录清理。
    回滚: 删光 real-fake(连数据) + purge case/RAM 树。
    失败判据: 组外 .!qB 被拦/被搬/被删; 组内 .!qB 未拦; G2 未同时命中 incomplete+qb_temp;
              目标叶子未建却 GATE_SPACE; 目标为文件未 target_type; 迁移后源/目标结构不符;
              普通条目被改动。
    """
    case = case_dir("rm04_10")
    p = None
    ev: dict = {"case": "RM04-10", "env": "环境1(D盘机)"}
    try:
        qb = qbfake()
        ev["qb_version"] = qb.version()
        assert not rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
        src = RAM / "rm04_10" / "src"
        dst = RAM / "rm04_10" / "dst"
        purge_tree(src.parent)
        src.mkdir(parents=True, exist_ok=True)
        assert not dst.exists(), f"目标叶子必须不存在(测 R1 上溯): {dst}"
        cfg, web_port = write_cfg(case, relocate=True)
        p = app.start(cfg, case)
        assert p.wait_web(40), f"WEB 没起来:\n{p.log()[-800:]}"
        assert p.wait_log("整组迁移已启用", 20), f"relocate 启动日志缺失:\n{p.log()[-600:]}"

        size = 256 * 1024
        h1 = fake_with_data(qb, "rm04c10_g1.bin", size, src, "rm04c10-g1")
        h2 = fake_no_data(qb, "rm04c10_g2.bin", size, src, "rm04c10-g2")
        h3 = fake_with_data(qb, "rm04c10_g3.bin", size, src, "rm04c10-g3")
        for h in (h1, h2, h3):
            settle(qb, h)
        wait_complete(qb, [h1, h3])
        for h in (h1, h2, h3):
            qb.pause(h)
            settle(qb, h)

        g2_temp = src / "rm04c10_g2.bin.!qB"
        g2_temp.write_bytes(bytes(range(256)) * 4)
        g3_temp = src / "rm04c10_g3.bin.!qB"
        g3_temp.write_bytes(b"g3-temp" * 128)
        keep = src / "keep_rm04c10.txt"
        keep.write_bytes(b"ordinary unowned entry" * 16)
        g1_src = src / "rm04c10_g1.bin"
        g3_file = src / "rm04c10_g3.bin"
        ev.update(
            {
                "src": norm(src),
                "dst": norm(dst) + "(leaf absent)",
                "hashes": {
                    "g1": h1,
                    "g2": h2,
                    "g3": h3
                },
                "foreign_qbtemp": _file_state(g2_temp),
                "own_qbtemp": _file_state(g3_temp),
                "keep": _file_state(keep),
                "g3_file": _file_state(g3_file)
            }
        )

        assert wait_group(web_port, h1, {h1}, 25, "G1 未独立成组")
        assert wait_group(web_port, h2, {h2}, 25, "G2 未独立成组")
        assert wait_group(web_port, h3, {h3}, 25, "G3 未独立成组")
        wait_store_progress(web_port, [h1, h3])
        wait_until(
            lambda: next(
                (
                    m.get("progress") for m in (group_row(groups_view(web_port), h2) or {}).get("members", [])
                    if m.get("hash") == h2
                ), None
            ) == 0, 20, "G2 未以 progress=0 进入产品快照"
        )

        # ---- 负向1: 组内 .!qB(已完成 G3) → qb_temp 硬拦, 零副作用
        before = count_anchor(case, "迁移发起")
        dst3 = RAM / "rm04_10" / "dst3"
        r3 = cmd_post_and_wait(web_port, f"/api/torrents/{h3}/location", {"location": str(dst3), "confirm": True})
        assert r3.get("status") == "error", f"组内 .!qB 应被拒, 实际: {json.dumps(r3, ensure_ascii=False)[:500]}"
        gates3 = _gates_of(r3)
        assert "qb_temp" in gates3, f"组内 .!qB 拒绝原因缺 qb_temp: {gates3}"
        assert "incomplete" not in gates3, f"G3 已完成却命中 incomplete(对照失效): {gates3}"
        assert not _has_started(r3), "组内 .!qB 被拦却出现 started 项"
        assert count_anchor(case, "迁移发起") == before, "组内 .!qB 拒绝却新增「迁移发起」(零副作用失守)"
        _assert_unchanged(g3_temp, ev["own_qbtemp"], "组内 .!qB")
        assert norm((qb.torrent(h3) or {}).get("save_path")) == norm(src), "组内 .!qB 拒绝却改了 G3 save_path"
        ev["g3_blocked_gates"] = gates3

        # ---- 负向2: 外部组 G2(未完成)自身 .!qB → incomplete + qb_temp 双拦, 外组 .!qB 原地不动
        before = count_anchor(case, "迁移发起")
        dst2 = RAM / "rm04_10" / "dst2"
        r2 = cmd_post_and_wait(web_port, f"/api/torrents/{h2}/location", {"location": str(dst2), "confirm": True})
        assert r2.get("status") == "error", f"外部组未完成应被拒, 实际: {json.dumps(r2, ensure_ascii=False)[:500]}"
        gates2 = _gates_of(r2)
        assert "incomplete" in gates2 and "qb_temp" in gates2, f"G2 拒绝原因缺 incomplete/qb_temp: {gates2}"
        assert not _has_started(r2), "G2 被拦却出现 started 项"
        assert count_anchor(case, "迁移发起") == before, "G2 拒绝却新增「迁移发起」(零副作用失守)"
        _assert_unchanged(g2_temp, ev["foreign_qbtemp"], "外组 .!qB")
        ev["g2_blocked_gates"] = gates2

        # ---- 负向3: 目标路径为文件 → target_type 硬拦(R2 #3), 零副作用
        not_a_dir = case / "target_is_file"
        not_a_dir.write_bytes(b"not-a-dir")
        before = count_anchor(case, "迁移发起")
        rf = cmd_post_and_wait(web_port, f"/api/torrents/{h1}/location", {"location": str(not_a_dir), "confirm": True})
        assert rf.get("status") == "error", f"目标为文件应被拒, 实际: {json.dumps(rf, ensure_ascii=False)[:500]}"
        gates_f = _gates_of(rf)
        assert "target_type" in gates_f, f"目标为文件拒绝原因缺 target_type: {gates_f}"
        assert not _has_started(rf), "目标为文件却出现 started 项"
        assert count_anchor(case, "迁移发起") == before, "目标为文件拒绝却新增「迁移发起」(零副作用失守)"
        assert norm((qb.torrent(h1) or {}).get("save_path")) == norm(src), "目标为文件拒绝却改了 G1 save_path"
        ev["target_type_gates"] = gates_f

        # ---- 主链: 外组 .!qB 在内容根 → G1 单成员迁移放行(目标叶子未建, 同卷上溯)
        before = count_anchor(case, "迁移发起")
        result = cmd_post_and_wait(web_port, f"/api/torrents/{h1}/location", {"location": str(dst), "confirm": True})
        item = one_started_item(result)
        job_id = item.get("job_id")
        assert job_id, f"回执 started 项缺 job_id: {json.dumps(item, ensure_ascii=False)[:400]}"
        assert item.get("form") == "direct", f"单成员组形态应为 direct, 实际: {item.get('form')}"
        assert item.get("target_free") is not None and item["target_free"] > 0, \
            f"目标叶子未建时未上溯到有效剩余: target_free={item.get('target_free')}"
        assert item.get("same_volume") is True, f"src/dst 应同卷, 实际: {item.get('same_volume')}"
        notes = " | ".join(item.get("notes") or [])
        assert "源与目标同卷" in notes, f"同卷 note 缺失: {notes}"
        assert "内容根含组外种子的文件" in notes and "rm04c10_g2.bin.!qB" in notes, \
            f"组外 .!qB 未进入外组条目 note: {notes}"
        assert "内容根含非种子杂项" in notes and "keep_rm04c10.txt" in notes, f"杂项 note 缺失: {notes}"
        assert not [g for g in (r.get("gate") for r in (item.get("reasons") or []))
                    if g in {"qb_temp", "space", "target_type", "incomplete"}], \
            f"放行项仍带硬闸门: {item.get('reasons')}"
        ev.update(
            {
                "started": True,
                "job_id": job_id,
                "form": item.get("form"),
                "target_free": item.get("target_free"),
                "same_volume": item.get("same_volume"),
                "notes": item.get("notes")
            }
        )

        wait_until(
            lambda: norm((qb.torrent(h1) or {}).get("save_path")) == norm(dst), 90, lambda:
            (f"qB 侧 G1 save_path 未变 dst: {(qb.torrent(h1) or {}).get('save_path')}")
        )
        dst_g1 = dst / "rm04c10_g1.bin"
        wait_until(lambda: dst_g1.is_file() and dst_g1.stat().st_size == size, 30, f"dst 侧 G1 数据未对齐: {dst_g1}")
        assert sorted(x.name for x in dst.iterdir()) == ["rm04c10_g1.bin"], \
            f"dst 目录结构不符(只应有 G1 文件): {sorted(x.name for x in dst.iterdir())}"
        assert not (dst / "rm04c10_g2.bin.!qB").exists(), "外组 .!qB 被顺手带到 dst"
        assert not (dst / "keep_rm04c10.txt").exists(), "无主杂项被带到 dst"
        assert not (dst / "rm04c10_g3.bin").exists(), "外部组普通条目被带到 dst"
        wait_until(lambda: not g1_src.exists(), 30, f"源侧 G1 文件未消失(direct 应搬走): {g1_src}")
        assert src.is_dir(), "源内容根被整体删除(应保留其余条目)"
        _assert_unchanged(g2_temp, ev["foreign_qbtemp"], "外组 .!qB")
        _assert_unchanged(g3_temp, ev["own_qbtemp"], "组内 .!qB")
        _assert_unchanged(keep, ev["keep"], "无主杂项")
        _assert_unchanged(g3_file, ev["g3_file"], "外部组普通条目")
        wait_until(lambda: count_anchor(case, "迁移发起") > before, 30, "日志缺「迁移发起」(搬迁没有真正下发)")
        job = wait_job_phase(case, job_id, {"done"}, 90, "job 未推进到 done")
        assert job.get("phase") == "done", f"job 未 done: {job}"
        wait_until(
            lambda: norm((lambda g: decode_key(g["key"])[0] if g else "")
                         (group_row(groups_view(web_port), h1)) or "") == norm(dst), 30, "G1 迁移后未在 dst 重归组"
        )
        ev.update(
            {
                "job_phase": job.get("phase"),
                "dst_entries": sorted(x.name for x in dst.iterdir()),
                "src_g1_gone": not g1_src.exists(),
                "result": "PASS"
            }
        )
    finally:
        if p is not None:
            p.stop()
        try:
            WORK.mkdir(parents=True, exist_ok=True)
            (WORK / "rm04_10_evidence.json").write_text(json.dumps(ev, ensure_ascii=False, indent=2), encoding="utf-8")
            (WORK / "rm04_10_auto-qb.log").write_text(app.read_log(case), encoding="utf-8")
        except Exception:  # noqa: BLE001 - 取证失败不得掩盖主断言结果
            pass
        rm_all_fakes(qbfake())
        purge_tree(case)
        purge_tree(RAM / "rm04_10")


# ================================================================ RM04-14

ROOT = Path(__file__).resolve().parents[2]


def _sha1_file(p: Path) -> str:
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _head_sha() -> str:
    """取证用构建版本(不参与闸门): HEAD 短 hash + 工作树是否带未提交改动。"""
    try:
        head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True)
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True)
        sha = (head.stdout or "").strip() or "unknown"
        return f"{sha}{'-dirty' if (dirty.stdout or '').strip() else ''}"
    except Exception:  # noqa: BLE001 - 取证失败不得阻塞用例
        return "unknown"


def _run_ui_script(web_port: int, mode: str, group: str, dst: Path, skin: str = "prism") -> dict:
    """调 Node/Playwright 侧脚本点真实 Web UI; 返回 UI_RESULT JSON(失败即断言失败带现场)。"""
    node = shutil.which("node")
    assert node, "node 不在 PATH(浏览器验收入口需要 Node + playwright)"
    script = Path(__file__).resolve().parents[1] / "lib" / "relocate_confirm_ui.mjs"
    assert script.is_file(), f"UI 脚本缺失: {script}"
    env = dict(os.environ)
    env.update(
        {
            "RM_UI_BASE": f"http://127.0.0.1:{web_port}",
            "RM_UI_GROUP": group,
            "RM_UI_DST": str(dst),
            "RM_UI_MODE": mode,
            "RM_UI_SKIN": skin,
        }
    )
    r = subprocess.run(
        [node, str(script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=300,
        env=env,
    )
    line = next((ln for ln in reversed((r.stdout or "").splitlines()) if ln.startswith("UI_RESULT ")), None)
    assert line, f"UI 脚本无 UI_RESULT 输出(rc={r.returncode}):\nstdout={(r.stdout or '')[-1500:]}\nstderr={(r.stderr or '')[-1500:]}"
    data = json.loads(line[len("UI_RESULT "):])
    assert r.returncode == 0 and data.get("ok") is True, \
        f"浏览器验收失败(mode={mode}): {data.get('error')}\n" \
        f"steps={json.dumps(data.get('steps'), ensure_ascii=False)}\n" \
        f"requests={json.dumps(data.get('requests'), ensure_ascii=False)[:800]}\n" \
        f"stderr={(r.stderr or '')[-800:]}"
    return data


def test_rm04_14_webui_confirm_loop_ui():
    """[RM04-14] Web UI 整组迁移 confirm 回路真机化: 浏览器点击 -> 确认框 7 要素 ->
                 带 confirm=true 重发 -> dst 落地 + job/journal done; 取消路径原框带路径重开且零副作用

    前置: relocate.enabled=true + alias_file_threshold: 8(默认); A/B 各 2 枚带数据多文件假种子
          (9 个子目录文件 = 9MiB, 同文件列表同内容异 piece_len) 落 RAM(R: 缺席退 .work/rm04/ram/);
          内容根 save_path/<name> 目录专属 ⇒ 多成员 + 文件数 ≥ 阈值 ⇒ FORM_DIR_ALIAS + needs_confirm。
          dst_a/dst_b 预建且与 src 同卷; 同卷证明解锁同 RM04-05(qB 副实例 save_path 临时改指 C: 现存目录)。
    动作: tests-real/lib/relocate_confirm_ui.mjs(Node + playwright) 真点 Web UI:
          B 组「右键组行 -> 设定位置 -> 填 dst -> 设定位置」走取消; A 组同手势走确认。
    副作用: A 组真实搬迁(qB 真移 9MiB; src 内容根成 junction); B 组零副作用(仅一次被拦截的首投)。
          副实例 save_path 临时改写(finally 还原); 副实例新增 4 枚 real-fake 种子(收尾删净)。
    回滚: 副实例 save_path 还原; 删 junction 只 rmdir 本体; 删光 real-fake 种子; 删用例目录 + RAM 树。
    失败判据: 首投后出现「已执行」(把等确认误报成功); 确认框缺 7 要素任一; 取消后原框未带原路径
              重开或发生第二次请求; 确认后无带 confirm=true 的第二次 POST; 成功 toast 未按回执计数;
              dst 无落地/大小/哈希不符; src 内容根未成 junction; 缺「迁移发起」/「已武装收尾」;
              job/journal 未 phase=done; B 组出现任何位移。
    """
    case = case_dir("rm04_14")
    p = None
    qb = qbfake()
    orig_save_path = qb.prefs().get("save_path")
    ev: dict = {"case": "RM04-14", "head": _head_sha()}
    try:
        assert orig_save_path, "副实例 save_path 读取失败(鉴权/连不通?), 拒跑"
        assert not rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
        probe_dir = case / "qbsave"
        probe_dir.mkdir(parents=True, exist_ok=True)
        qb.set_prefs(save_path=str(probe_dir))
        time.sleep(0.5)
        assert qb.prefs().get("save_path") == str(probe_dir), \
            "save_path 临时改写未生效(同卷证明解锁不成立, 多成员组会被 GATE_SAME_FS 拒)"

        src_a = RAM / "rm04_14" / "src_a"
        src_b = RAM / "rm04_14" / "src_b"
        dst_a = case / "dst_a"
        dst_b = case / "dst_b"
        purge_tree(RAM / "rm04_14")
        dst_a.mkdir(parents=True, exist_ok=True)
        dst_b.mkdir(parents=True, exist_ok=True)
        cfg, web_port = write_cfg(case, relocate=True)
        p = app.start(cfg, case)
        assert p.wait_web(40), f"WEB 没起来:\n{p.log()[-800:]}"
        assert p.wait_log("整组迁移已启用", 20), f"relocate 启动日志缺失:\n{p.log()[-600:]}"
        ev["web_port"] = web_port

        files_a = [(f"rm04c11a/sub/f{i:02d}.bin", 1024 * 1024) for i in range(9)]
        files_b = [(f"rm04c11b/sub/g{i:02d}.bin", 1024 * 1024) for i in range(9)]
        h1a = fake_multi(qb, "rm04c11a", files_a, src_a, "rm04c11a")
        h2a = fake_multi(qb, "rm04c11a", files_a, src_a, "rm04c11a", piece_len=32768, write=False)
        h1b = fake_multi(qb, "rm04c11b", files_b, src_b, "rm04c11b")
        h2b = fake_multi(qb, "rm04c11b", files_b, src_b, "rm04c11b", piece_len=32768, write=False)
        wait_complete(qb, [h1a, h2a, h1b, h2b], timeout=120)
        assert wait_group(web_port, h1a, {h1a, h2a}, 25, "A 组两成员未成组(前提不成立)")
        assert wait_group(web_port, h1b, {h1b, h2b}, 25, "B 组两成员未成组(前提不成立)")
        wait_store_progress(web_port, [h1a, h2a, h1b, h2b], timeout=60)

        src_hashes = {rel: _sha1_file(src_a / rel) for rel, _size in files_a}
        ev.update(
            {
                "src_a": str(src_a),
                "dst_a": str(dst_a),
                "src_b": str(src_b),
                "dst_b": str(dst_b),
                "hashes": src_hashes,
                "hashes_before": len(src_hashes)
            }
        )

        # ---- 取消路径(B 组): 首投被拦截 -> 确认框 -> 取消 -> 原框带路径重开 -> 零副作用
        anchor0 = count_anchor(case, "迁移发起")
        cancel = _run_ui_script(web_port, "cancel", "rm04c11b", dst_b)
        ev["cancel"] = cancel
        assert len(cancel["requests"]) == 1, f"取消路径首投请求数应为 1: {cancel['requests']}"
        assert not cancel["requests"][0]["body"].get("confirm"), "取消路径首投不应带 confirm"
        assert cancel["cancelPath"] == str(dst_b), f"取消后原框未带原路径重开: {cancel['cancelPath']}"
        assert len(cancel["receipts"]) == 1, f"取消路径回执数应为 1: {cancel['receipts']}"
        crec = cancel["receipts"][0]
        assert crec.get("status") == "ok", f"confirm 回执契约应为 ok: {crec}"
        csum = (crec.get("truth") or {}).get("summary") or {}
        assert csum.get("confirm") == 1, f"回执 summary.confirm 应为 1: {csum}"
        assert csum.get("started") == 0, f"等确认不得 started: {csum}"
        citems = [it for it in ((crec.get("truth") or {}).get("results") or []) if it.get("cls") == "confirm"]
        assert citems, f"回执缺 cls=confirm 项: {json.dumps(crec, ensure_ascii=False)[:600]}"
        assert citems[0].get("form") == "dir_alias", f"确认项形态应为目录别名: {citems[0].get('form')}"
        assert citems[0].get("needs_confirm") is True, "确认项 needs_confirm 不为 True"
        assert norm(citems[0].get("target")) == norm(dst_b), f"确认项目标不符: {citems[0].get('target')}"
        assert count_anchor(case, "迁移发起") == anchor0, "取消路径出现「迁移发起」(零副作用失守)"
        assert not (dst_b / "rm04c11b").exists(), f"取消路径 dst 被写入: {dst_b / 'rm04c11b'}"
        for rel, size in files_b:
            f = src_b / rel
            assert f.is_file() and f.stat().st_size == size, f"取消路径源文件位移: {f}"
        for h in (h1b, h2b):
            assert norm((qb.torrent(h) or {}).get("save_path")) == norm(src_b), \
                f"取消路径 qB save_path 被改: {h[:8]} -> {(qb.torrent(h) or {}).get('save_path')}"
        ev["cancel_side_effect_free"] = True

        # ---- 确认路径(A 组): 首投被拦截 -> 确认框 -> 确认 -> 带 confirm=true 重发 -> 真实落地
        anchor1 = count_anchor(case, "迁移发起")
        conf = _run_ui_script(web_port, "confirm", "rm04c11a", dst_a)
        ev["confirm"] = conf
        assert len(conf["requests"]) == 2, f"确认路径应有两次 POST: {conf['requests']}"
        assert conf["requests"][0]["body"].get("confirm") in (None, False), "首投不应带 confirm"
        assert conf["requests"][1]["body"].get("confirm") is True, \
            f"重发未带 confirm=true: {json.dumps(conf['requests'][1], ensure_ascii=False)}"
        assert str(conf["requests"][1]["body"].get("location")) == str(dst_a), "重发目标与实际不一致"
        assert len(conf["receipts"]) == 2, f"确认路径回执数应为 2: {conf['receipts']}"
        rec1, rec2 = conf["receipts"]
        assert rec1.get("status") == "ok", f"首投回执契约应为 ok: {rec1}"
        r1sum = (rec1.get("truth") or {}).get("summary") or {}
        assert r1sum.get("confirm") == 1 and r1sum.get("started") == 0, f"首投回执不符: {r1sum}"
        r1items = [it for it in ((rec1.get("truth") or {}).get("results") or []) if it.get("cls") == "confirm"]
        assert r1items and r1items[0].get("form") == "dir_alias", "首投确认项形态不符"
        assert norm(r1items[0].get("target")) == norm(dst_a), "首投确认项目标不符"
        assert rec2.get("status") == "ok", f"确认后回执 status 应为 ok: {rec2}"
        r2sum = (rec2.get("truth") or {}).get("summary") or {}
        assert r2sum.get("started") == 1 and r2sum.get("confirm") == 0, f"确认后回执不符: {r2sum}"
        item = one_started_item(rec2)
        job_id = item.get("job_id")
        assert job_id, f"started 项缺 job_id: {json.dumps(item, ensure_ascii=False)[:500]}"
        assert item.get("form") == "dir_alias", f"实际形态不是目录别名: {item.get('form')}"
        assert item.get("same_volume") is True, f"同卷证明未通过: {item.get('same_volume')}"
        assert "源与目标同卷" in " | ".join(item.get("notes") or []), \
            f"同卷 note 缺失: {item.get('notes')}"
        assert "已执行" in "".join(conf.get("toasts") or []), "确认后未出现「已执行」成功提示"
        ev.update({"job_id": job_id, "started_item": item})

        # ---- 文件系统双向取证: qB 侧漂移 + dst 落地 + src 内容根 junction + 穿透可读
        moved = wait_until(
            lambda: next((h for h in (h1a, h2a) if norm((qb.torrent(h) or {}).get("save_path")) == norm(dst_a)), None),
            90, lambda:
            (f"qB 侧无成员 save_path 变 dst: "
             f"{[(h[:8], (qb.torrent(h) or {}).get('save_path')) for h in (h1a, h2a)]}")
        )
        other = h2a if moved == h1a else h1a
        for rel, size in files_a:
            f = dst_a / rel
            wait_until(lambda f=f, size=size: f.is_file() and f.stat().st_size == size, 45, f"dst 侧文件未落地: {f}")
            assert _sha1_file(f) == src_hashes[rel], f"dst 侧内容哈希不符(不是真搬移): {f}"
        ev["dst_files"] = [
            {
                "path": str(dst_a / rel),
                "size": (dst_a / rel).stat().st_size,
                "sha1": src_hashes[rel]
            } for rel, _size in files_a
        ]
        ev["mover"] = moved

        content_root = src_a / "rm04c11a"
        wait_until(lambda: _is_link(content_root), 45, f"src 内容根未成链接: {content_root}")
        assert reparse_kind(content_root) == "junction", f"src 内容根链接形态非 junction: {reparse_kind(content_root)}"
        ev["src_content_root_kind"] = reparse_kind(content_root)
        for rel, size in files_a:
            via_src = src_a / rel
            wait_until(
                lambda via_src=via_src, size=size: via_src.is_file() and via_src.stat().st_size == size,
                20,
                f"穿透校验失败(经原路径读不到同 size): {via_src}"
            )
        ev["src_through_alias_ok"] = True
        wait_until(lambda: count_anchor(case, "迁移发起") > anchor1, 45, "日志缺「迁移发起」(搬迁没有真正下发)")
        wait_until(lambda: "已武装收尾" in log_text(case), 45, "日志缺「已武装收尾」(arm 段没走)")
        ev["log_anchors"] = {"迁移发起": count_anchor(case, "迁移发起"), "已武装收尾": count_anchor(case, "已武装收尾")}

        # ---- 收口: 未移动成员经 qB 原生 setLocation 跟进 -> job/journal phase=done
        qb.set_location(other, str(dst_a))
        wait_until(
            lambda: all(norm((qb.torrent(h) or {}).get("save_path")) == norm(dst_a) for h in (h1a, h2a)), 60,
            "成员 save_path 未全部变 dst"
        )
        job = wait_job_phase(case, job_id, {"done"}, 120, "job 未推进到 done(reason=external 预期)")
        assert job.get("reason") == "external", f"job done 但 reason={job.get('reason')}: {job}"
        jr = journal_of(case, job_id)
        assert jr and jr.get("phase") == "done", f"journal 未落 phase=done: {jr}"
        ev.update({"job": job, "journal_phase": jr.get("phase"), "result": "PASS"})
    finally:
        if p is not None:
            p.stop()
        try:
            qb.set_prefs(save_path=orig_save_path)
            time.sleep(0.3)
            ev["save_path_restored"] = qb.prefs().get("save_path") == orig_save_path
        except Exception:  # noqa: BLE001 - 还原失败不得掩盖主断言结果
            ev["save_path_restored"] = False
        try:
            rm_all_fakes(qbfake())
        finally:
            try:
                WORK.mkdir(parents=True, exist_ok=True)
                (WORK /
                 "rm04_14_evidence.json").write_text(json.dumps(ev, ensure_ascii=False, indent=2), encoding="utf-8")
                (WORK / "rm04_14_auto-qb.log").write_text(app.read_log(case), encoding="utf-8")
            except Exception:  # noqa: BLE001 - 取证失败不得掩盖主断言结果
                pass
            purge_tree(case)
            purge_tree(RAM / "rm04_14")
