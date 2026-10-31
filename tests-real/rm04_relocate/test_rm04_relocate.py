"""RM04 辅种与分组 —— 八条真机用例(归组 key / 组内一致性 / 跨组冲突 / 缺失文件 / 跨盘移动 / journal)。

验证面对准冻结计划 plans/26-10-31-1042-plan-real-RM04.html §02 的六行代码映射:
归组 key(group_key_of, 断言走产品 WEB 只读端点 GET /api/groups)· 组内大小一致性(警告+整组暂停)·
跨组文件冲突(暂停下载方 + MISSING 豁免对照)· 缺失文件标记(带数据真删; --no-data 不是缺文件态)·
跨盘移动主链(R:→D: 真跨卷, 目录别名 + 穿透 + journal phase=done)· journal 恢复与坏账兜底。

代码实况落刀点(计划给意图, 这里按 src 实况):
- 单成员组恒走 FORM_DIRECT(qB 自搬, 无别名无 journal)—— 目录别名链必须多成员组 + 子目录布局
  (alias_file_threshold: 1 压低阈值 + POST body confirm=true 过二次确认);
- 正常发起的搬迁锚点是「迁移发起」;「已下发 qB 搬迁」只出现在重启补发路径(_step_move);
- 同一物理文件挂两枚同组种子(辅种本质)时, 两枚的 info 必须不同 ⇒ 用**不同 piece_len** 造
  (同内容不同分块 → 不同 infohash, 双双校验通过); 盐不同会让先写的成员校验失败;
- 同卷证明闸门: qB 36596 默认保存路径在 R: 盘(实测), 与 src 同卷 ⇒ 多成员跨卷可过 GATE_SAME_FS;
- journal 恢复的权威账在 state.json 的 relocate.jobs(job_to_dict 形), journal/spec/pid 是 guardian 侧账;
  相位落盘走 state_save_interval(30S)周期, 断言等待窗按 30s+ 裕量给。

跑法: `commands run real.suite -- --slice RM04 --yes`(不要裸 pytest)。真实种子全程非活跃;
八条全部 L1 假种子(零外连); 假种子一律 real-fake 标签; 落点只认 tests-real/.work/ 与 R:/qbt-fake/。
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

import pytest

from lib import app, torrent
from lib.bencode import encode
from lib.net import local_host

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="本片断言含 Windows 特有语义(junction/taskkill)"),
]

WORK = Path(__file__).resolve().parents[1] / ".work" / "rm04"
RAM = Path("R:/qbt-fake/rm04")  # 内存盘: 搬迁 src/大种子落点(重启即清空)
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
    from lib import instances
    return instances.make(36596)


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
    """删光 36596 里本片自造的种子(连数据), 返回删掉的名字(证据用)。

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
    """生成临时配置(schema_version: 5, 直连 36596, WEB 必开 —— 本片断言全走产品 WEB 只读端点)。

    product data_dir 指用例临时目录: journal/spec/pid/state 随目录清理, 不碰仓库根 auto-qb-data/。
    返回 (配置路径, web端口)。"""
    cfg = case / "config.yml"
    web_port = app.free_port()
    cfg.write_text(
        CONFIG_TEMPLATE.format(
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
    if "port: 36595" in text:
        raise AssertionError(f"配置指向了 36595(真实种子), 拒跑: {cfg}")
    if "schema_version: 5" not in text:
        raise AssertionError(f"配置缺 schema_version: 5(会触发迁移改写), 拒跑: {cfg}")
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

    前置: 产品非 dry-run 连 36596, grouping.enabled=true(默认); 3 枚 --no-data 假种子
          (A/B 同名同 save_path 异 salt, C 异名同 save_path), 停在 stalledDL。
    副作用: 36596 加 3 假种子(real-fake); 零文件系统写(仅 savepath 目录壳)。
    回滚: 删光 real-fake 种子 + 删用例目录。
    失败判据: A/B 未归同组; 或 C 与 A/B 归成一组(对照红验失效); 或出现
              「文件大小不一致」日志(3 枚同尺寸, 归组触发的一致性检查不得误报)。
    """
    case = case_dir("rm04_01")
    p = None
    try:
        qb = qbfake()
        assert not rm_all_fakes(qb), "开跑前 36596 有 real-fake 残留, 先清场"
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
    副作用: 36596 加 3 假种子; A/B 整组被产品暂停(假种子, 允许)。
    回滚: 删光 real-fake 种子 + 删用例目录。
    失败判据: 日志无「文件大小不一致, 暂停整组」; 或 A/B 未变 stopped; 或单成员 C
              也被判不一致而暂停(误报)。
    """
    case = case_dir("rm04_02")
    p = None
    try:
        qb = qbfake()
        assert not rm_all_fakes(qb), "开跑前 36596 有 real-fake 残留, 先清场"
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
        assert not rm_all_fakes(qb), "开跑前 36596 有 real-fake 残留, 先清场"
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
    副作用: 36596 加 2 假种子; B(下载方)被暂停两次(初次 + 复发红验)。
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
        assert not rm_all_fakes(qb), "开跑前 36596 有 real-fake 残留, 先清场"
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


def test_rm04_05_cross_volume_relocate_dir_alias():
    """[RM04-05] 跨盘移动主链: R:→D: 真跨卷 relocate → 目录别名 + 穿透 + journal phase=done

    前置: relocate.enabled=true + alias_file_threshold: 1; 两枚带数据多文件假种子(子目录
          布局, 同文件列表同内容异 piece_len)在 R:/qbt-fake/rm04/rm04_05/src 成组;
          dst = 用例目录 dst(D: 真磁盘, 真跨卷)。触发 = 产品 WEB
          POST /api/torrents/{hash}/location (confirm=true, 目录别名提议需二次确认)。
    副作用: qB 真搬数据(R:→D:); src 内容根变 junction 指向 dst; <data_dir>/relocate/ 落账。
    回滚: 删 junction 只 os.rmdir 本体(禁递归删穿); 删光 real-fake 种子; 删用例目录 + RAM 树。
    失败判据: 回执无 started; save_path 未变 dst(归一后比); dst 侧 size 不齐; src 内容根
              未成 junction; 经原路径穿透读不到同 size; journal 未落 phase=done;
              日志缺「迁移发起」/「已武装收尾」。
    """
    case = case_dir("rm04_05")
    p = None
    try:
        qb = qbfake()
        assert not rm_all_fakes(qb), "开跑前 36596 有 real-fake 残留, 先清场"
        src = RAM / "rm04_05" / "src"
        dst = case / "dst"
        purge_tree(src.parent)
        cfg, web_port = write_cfg(case, relocate=True, alias_threshold=1)
        p = app.start(cfg, case)
        assert p.wait_web(40), f"WEB 没起来:\n{p.log()[-800:]}"
        assert p.wait_log("整组迁移已启用", 20), \
            f"relocate 启动日志缺失(开关没生效?):\n{p.log()[-600:]}"

        files = [("rm04c5/sub/a.bin", 128 * 1024), ("rm04c5/sub/b.bin", 128 * 1024)]
        h1 = fake_multi(qb, "rm04c5", files, src, "rm04c5", write=True)  # 数据只写这一份
        h2 = fake_multi(qb, "rm04c5", files, src, "rm04c5", piece_len=32768, write=False)
        wait_complete(qb, [h1, h2])
        assert wait_group(web_port, h1, {h1, h2}, 20, "两成员未成组(前提不成立)")
        wait_store_progress(web_port, [h1, h2])  # 闸门读产品快照, 等 1-2 个同步拍追平
        dst.mkdir(parents=True, exist_ok=True)  # 目标卷空间闸门要读 dst(不存在 = 不可判定 = 拒)

        # ---- 触发: 产品 WEB 命令线(目录别名提议 → confirm=true 过二次确认)
        result = cmd_post_and_wait(web_port, f"/api/torrents/{h1}/location", {"location": str(dst), "confirm": True})
        item = one_started_item(result)
        job_id = item.get("job_id")
        assert job_id, f"回执 started 项缺 job_id: {json.dumps(item, ensure_ascii=False)[:400]}"
        assert "迁移发起" in log_text(case), "日志缺「迁移发起」(搬迁没有真正下发)"

        # ---- qB 侧: save_path 变 dst + dst 数据 size 对齐
        wait_until(
            lambda: norm((qb.torrent(h1) or {}).get("save_path")) == norm(dst), 60,
            f"mover save_path 未变 dst: {(qb.torrent(h1) or {}).get('save_path')}"
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
    finally:
        if p is not None:
            p.stop()
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
        assert not rm_all_fakes(qb), "开跑前 36596 有 real-fake 残留, 先清场"
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
        assert not rm_all_fakes(qb), "开跑前 36596 有 real-fake 残留, 先清场"
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
        assert not rm_all_fakes(qb), "开跑前 36596 有 real-fake 残留, 先清场"
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
