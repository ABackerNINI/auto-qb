"""
[RM04-32] [E7] 交集判据取数核验: files API 对 FILE_LINKS 与 NoSubfolder 两形态取清单(与门级取数数据源同源), 清单与磁盘实况一致。

同源声明: _write_cfg_fast_tick/_assert_healthy/_readlink_norm 复用
test_rm04_e2_alias_add_pass.py(E2 单侧实现, 本文件 import 复用零拷贝);
start_bypass_app/_require_r_topology/stop_lingering_product/qb_up/bt_backup_snapshot/W.BT_BACKUP
复用 test_rm04_relocate_window.py(W 单点); 造种/清场/断言助手复用 test_rm04_relocate.py(M 单点)。
_tree_snap 与 test_rm04_e4_outsider_delete.py 同源(函数体逐字一致, 单侧改动须同步)。
_build_nsf_raw 为本用例本地新增: 多文件剥根种子构造, info/pieces 口径逐字对齐 M.fake_multi
(同盐同文件表算 blob -> 逐 piece sha1), 差异仅在不入库直返 raw(加库走 _add_with_layout);
_add_with_layout 配方誊写自报告 26-11-13-0617 实验(tests/real/.work/relocate-form-gates/
run_exp.py add_retry), 差异仅在 409 清场改用 M.wait_until 轮询 —— M._add_retry 不支持
contentLayout 表单域, 故不直接复用。

计划 plans/26-11-17-0636-plan-real-rm04-relocate-refactor-verify.html §03.4 RM04-32 用例卡(L2):
FILE_LINKS 与 NoSubfolder 两形态组, 经产品 WEB 只读端点 GET /api/torrents/{hash}/files 取成员
文件清单, 与磁盘实况逐文件对照(size/rel 路径双一致, FILE_LINKS 形态经 junction 视图同证)。
该端点与门级取数**数据源同源**(client.torrents_files = qB /torrents/files 透传), 但缓存层
各自独立: WEB 路由走 ctx.cached_read(torrent_detail.py), 门级走 TorrentRecord._files 惰性
持久缓存(relocate_plan.PlanMixin._file_map / qbapi._relocate_file_names 消费) —— WEB 端点
不经门级惰性缓存单点; TorrentRecord.files 面由 RM04-33 注入/放行双腿覆盖(评审 R34 纠偏)。

切分(不测三遍, 卡面钉死): 闸门面交集行为已由 RM04-28/29(异名豁免)/RM04-25 C 腿(同名计依赖)
外部可观测地钉住, 本条只核「清单取数 <-> 磁盘实况」一致性独立面; _norm 归一后交集判定正确性
引用不复断(单测 tests/test_relocate_units.py 谓词单点钉扎), 本 docstring 即切分声明。

E7b 形态说明(qB 5.2.3 实证, 报告 26-11-13-0617): 多文件种子以 contentLayout=NoSubfolder 加库
(剥根平铺)时, files API 名单不带 info 根前缀(报告 ['a.bin','b.bin'] 形)且与磁盘平铺逐项一致 ——
交集谓词 file_alias_intersects 对该形态 _join(save_path, rel) 绝对化无需剥根校正的取数前提。

## 测试计划(单测试函数, S1-S3+Z 四段)
- S1 造现场: 产品起(旁路 runner)→ FILE_LINKS 组(双成员共享 1MiB 单文件,
  R:/qbt-fake/rm04/rm04_32a/src)与 NoSubfolder 组(双成员多文件剥根平铺 256KiB+128KiB,
  R:/qbt-fake/rm04/rm04_32b/nsf, info 根 nsfb, contentLayout=NoSubfolder 加库, 数据手工平铺
  实写)各自完成/归组, 两组组键互不串(独立根独立文件表)。
- S2 两形态各搬迁 armed: WEB 迁移 confirm 直投 → form 均为 file_links(组 A 1 文件 / 组 B 2
  文件均小于阈值 8; 组 B 平铺布局整目录别名不提供)→ 已武装收尾 + symlink 现场指各自 dst +
  成员详情 relocate 相位双组 armed(两枚 armed 组账)。
- S3 取数对照(断言面): 逐成员经 GET /api/torrents/{h}/files 取清单 →
  a) 行面: 与磁盘实况逐文件双一致 —— rel 名逐字一致(缺行/多行即红)、size 与磁盘字节数全等;
  b) 形态面: 名单 posix 相对形(无反斜杠/无盘符/无绝对前缀); NoSubfolder 组名单不带 info 根
     前缀(剥根形态回归面);
  c) 链接视图同证(FILE_LINKS): 非 mover 成员 save_path 下文件为 symlink 指向 dst, 穿链读出
     size == 清单 size == dst 实体 size; mover 成员 save_path 即 dst, 实体 size == 清单 size;
  d) 非空面: 两形态任一成员取空清单而磁盘有货即红。
- Z 收尾: 产品优雅退出 → real-fake 删净(连数据)→ BT_backup 本用例哈希残留清除 + 开工快照
  逐文件比对 → case 树与 R: 子树删净 + 链接 lstat 零残留。

前置: 环境1(R: 在, src 在 R:/qbt-fake/rm04 与 dst=D: case 异盘) + 双测试实例在线
      (没起先 `commands run real.up -- --port <白名单端口>`); 副实例无 real-fake 残留;
      独占约 2-3 分钟, conftest serial 锁串行保护。R: 缺席 => skip 不回退落点(钉死口径)。
副作用: 只读为主 + 两枚 armed 组账(state.json 随 case 树清理)+ 两次真搬迁(R: → D: case)。
回滚: 产品优雅退出(sentinel 通路); 双实例保持在线; real-fake 种子删净(连数据); BT_backup
      只清本用例哈希残留 + 逐文件比对开工快照(queue 豁免); case 树与 R:/qbt-fake/rm04/
      rm04_32a|32b 子树删净(purge_tree 不递归删穿链接); 链接 lstat 零残留。
失败判据: 清单与磁盘实况不一致(缺行/多行/size 错); 名单形态错(反斜杠/盘符/绝对路径);
      NoSubfolder 名单带 info 根前缀(剥根形态回归); 两形态任一取空却磁盘有货; 链接形态或
      指向漂移; 收尾有残留。

跑法: `commands run real.run -- --case RM04-32 --yes`(不要裸 pytest)。
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_rm04_relocate as M  # noqa: E402  (复用 RM04 的造种/清场/断言助手)
import test_rm04_relocate_window as W  # noqa: E402  (旁路接线/收尾 helper, 授权见其 docstring)
import test_rm04_e2_alias_add_pass as E2  # noqa: E402  (同源 helper 复用, 见模块 docstring)

from lib import guard, instances, torrent  # noqa: E402
from lib.bencode import encode  # noqa: E402  (剥根多文件种子手工构造)

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="本片断言含 Windows 特有语义(symlink/优雅退出通路)"),
]

# 拓扑单点(钉死; 两形态组子树隔离): src 在 R: 内存盘, dst 在 case(D: 异盘)
R_ROOT = Path("R:/qbt-fake/rm04")
SRC_A = R_ROOT / "rm04_32a" / "src"  # 组 A(FILE_LINKS): 单文件平铺双成员
SRC_B = R_ROOT / "rm04_32b" / "nsf"  # 组 B(NoSubfolder): 多文件剥根平铺双成员
FILE_A = "rm04c32a.bin"
FILE_A_SIZE = 1024 * 1024
NSF_A, NSF_B = "nsf_a.bin", "nsf_b.bin"
NSF_A_SIZE = 256 * 1024
NSF_B_SIZE = 128 * 1024
NSF_ROOT_NAME = "nsfb"  # 组 B info 根(NoSubfolder 加库后磁盘平铺, 名单不带此前缀)
PIECE_LENS = (16384, 32768)  # 同内容异 infohash 的区分面(两颗成员)
SALT_A = "rm04c32a"
SALT_B = "rm04c32b"

# 复用单点(不另抄一份)
_require_r_topology = W._require_r_topology
start_bypass_app = W.start_bypass_app
stop_lingering_product = W.stop_lingering_product
qb_up = W.qb_up
bt_backup_snapshot = W.bt_backup_snapshot
_write_cfg_fast_tick = E2._write_cfg_fast_tick
_assert_healthy = E2._assert_healthy
_readlink_norm = E2._readlink_norm
# 副实例 BT_backup 路径单点在 W, 函数内按需取(收集期不探测 EXE)

# 片G 证据目录(任务口径: 逐案 evidence 落 tests/real/.work/rm04-sliceG/; 时刻+遍次后缀防覆写)
SLICE_EV = HERE.parent / ".work" / "rm04-sliceG"


def _pass() -> str:
    return os.environ.get("RM04G_PASS", "0")


def _flush(ev: dict, case: Path, tag: str) -> None:
    """证据落盘(gitignored .work/rm04-sliceG): 全量断言现场 + 产品日志副本, 时刻+遍次后缀防覆写。"""
    ev["pass"] = _pass()
    ev["ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
    SLICE_EV.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    (SLICE_EV / f"rm04_32_{tag}_evidence_{stamp}.json"
    ).write_text(json.dumps(ev, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    try:
        log = M.log_text(case)
    except Exception as e:  # noqa: BLE001 —— 取证失败如实带错, 不掩盖主断言
        log = f"<log read failed: {e!r}>"
    (SLICE_EV / f"rm04_32_{tag}_auto-qb_{stamp}.log").write_text(log, encoding="utf-8")


def _tree_snap(root: Path) -> dict:
    """磁盘逐文件快照(lstat 不跟随链接): rel 路径 -> {kind, size}。链接/目录 size=None。

    与 test_rm04_e4_outsider_delete.py _tree_snap 同源(函数体逐字一致, 单侧改动须同步)。"""
    out: dict = {}
    if not root.exists():
        return out
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        for nm in sorted(dirnames) + sorted(filenames):
            p = Path(dirpath) / nm
            rel = p.relative_to(root).as_posix()
            kind = M.reparse_kind(p)
            if kind:
                out[rel] = {"kind": kind, "size": None}
                continue
            st = os.lstat(p)
            if stat.S_ISDIR(st.st_mode):
                out[rel] = {"kind": "dir", "size": None}
            else:
                out[rel] = {"kind": "file", "size": st.st_size}
    return out


def _build_nsf_raw(salt: str, piece_len: int) -> tuple[bytes, str]:
    """组 B 剥根多文件种子构造(不入库直返 raw+infohash)。

    info/pieces 口径逐字对齐 M.fake_multi: blob = 逐文件 chunks(salt:rel) 拼接, pieces =
    逐 piece_len sha1 摘要拼接; info.files path = 单段相对名(剥根形态, 与实验 build_multi
    的 rel='a.bin' 同形)。两成员同盐异 piece_len -> 异 infohash 同内容, 双双校验通过。"""
    blob = bytearray()
    for rel, size in ((NSF_A, NSF_A_SIZE), (NSF_B, NSF_B_SIZE)):
        blob += b"".join(torrent.chunks(size, "random", f"{salt}:{rel}"))
    pieces = b"".join(hashlib.sha1(bytes(blob[i:i + piece_len])).digest() for i in range(0, len(blob), piece_len))
    info = {
        "name": NSF_ROOT_NAME,
        "piece length": piece_len,
        "pieces": pieces,
        "private": 1,
        "files": [{
            "path": [rel],
            "length": size
        } for rel, size in ((NSF_A, NSF_A_SIZE), (NSF_B, NSF_B_SIZE))],
    }
    ih = hashlib.sha1(encode(info)).hexdigest()
    raw = encode({"info": info, "comment": "auto-qb real-machine test (fake seed)", "announce": M.ANNOUNCE})
    return raw, ih


def _add_with_layout(qb, raw: bytes, savepath: str, ih: str, content_layout: str) -> None:
    """带 contentLayout 加种(NoSubfolder 剥根平铺; 配方见模块 docstring 同源声明)。

    同 infohash 旧副本在场一律删掉重加(绝不收养, M._add_retry 同口径); 加完补一次 start
    (qB 5.2 paused=false 仍可能落 stoppedUP, lib.qb.add_torrent 同款)。"""
    stale = qb.torrent(ih)
    if stale is not None:
        qb.delete(ih, delete_files=False)
        M.wait_until(lambda: True if qb.torrent(ih) is None else None, 30, f"{ih[:8]} 旧副本未删净")
    fields = {
        "savepath": savepath,
        "paused": "false",
        "stopped": "false",
        "tags": M.TAG,
        "contentLayout": content_layout,
    }
    boundary = "----rm04e7boundary"
    parts = []
    for k, v in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="torrents"; filename="rm04e7.torrent"\r\n'
        f"Content-Type: application/x-bittorrent\r\n\r\n".encode() + raw + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    qb._call("/torrents/add", b"".join(parts), f"multipart/form-data; boundary={boundary}")
    M.wait_until(lambda: True if qb.torrent(ih) is not None else None, 40, f"{ih[:8]} 加种子后未出现在实例")
    cur = qb.torrent(ih)
    if cur and str(cur.get("state", "")).startswith("stopped"):
        qb.resume(ih)


def _fetch_files(web_port: int, h: str) -> list[dict]:
    """产品 WEB 只读端点取成员文件清单(GET /api/torrents/{h}/files; qB 透传列表)。"""
    data = M.web_req(web_port, "GET", f"/api/torrents/{h}/files")
    assert isinstance(data, list), f"files 端点回执非列表: {type(data).__name__}"
    return data


def _assert_member_list(web_port: int, qb, h: str, expect_names: set[str], dst: Path, group: str) -> dict:
    """单成员取数对照(断言面 a/b/c/d): 清单 x 磁盘逐文件双一致 + 形态面 + 链接视图同证。

    返回证据行(进 ev)。sp 判 mover/非 mover: save_path 等值 dst = mover(实体文件面),
    否则 = 非 mover(armed 链接视图面, 穿链 size == 清单 size == dst 实体 size)。"""
    flist = _fetch_files(web_port, h)
    assert flist, f"[{group}] {h[:8]} 清单取空而磁盘有货(取数面失守)"
    names = [str(f.get("name")) for f in flist]
    sizes = {str(f.get("name")): int(f.get("size")) for f in flist}
    assert len(sizes) == len(flist), f"[{group}] {h[:8]} 清单行重名: {names}"
    assert set(names) == expect_names, f"[{group}] {h[:8]} 行面失守(缺行/多行): {sorted(names)} != {sorted(expect_names)}"
    for n in names:
        # 形态面: posix 相对形(反斜杠/盘符/绝对前缀任一出现即红)
        assert "\\" not in n, f"[{group}] 清单名带反斜杠(归一形态错): {n!r}"
        assert ":" not in n, f"[{group}] 清单名带盘符(绝对路径形态错): {n!r}"
        assert not n.startswith("/"), f"[{group}] 清单名是绝对路径: {n!r}"
    if group == "B":
        for n in names:
            assert not n.startswith(NSF_ROOT_NAME + "/"), \
                f"[{group}] NoSubfolder 名单带 info 根前缀(剥根形态回归): {n!r}"
    t = qb.torrent(h) or {}
    sp = M.norm(t.get("save_path") or "")
    assert sp, f"[{group}] {h[:8]} save_path 取不到: {t}"
    is_mover = sp == M.norm(str(dst))
    rows = []
    for n in sorted(names):
        p_disk = Path(sp) / n
        assert p_disk.is_file(), f"[{group}] {h[:8]} 清单行磁盘缺失: {p_disk}"
        through = os.path.getsize(p_disk)  # 穿链读(非 mover 的 save_path 文件是 symlink)
        assert through == sizes[n], \
            f"[{group}] {h[:8]} size 双一致失守: 清单 {sizes[n]} != 磁盘穿链 {through} ({p_disk})"
        kind = M.reparse_kind(p_disk)
        row = {"name": n, "api_size": sizes[n], "disk_through_size": through, "kind": kind or "file"}
        if kind == "symlink":
            # 链接视图同证: symlink 指向 dst 且 dst 实体 size == 清单 size
            tgt = _readlink_norm(p_disk)
            assert M.norm(tgt).startswith(M.norm(str(dst))), f"[{group}] 链接未指 dst: {tgt}"
            assert os.path.getsize(Path(tgt)) == sizes[n], \
                f"[{group}] dst 实体 size 失守: {tgt} {os.path.getsize(Path(tgt))} != 清单 {sizes[n]}"
            row["target"] = tgt
        elif kind is not None:
            raise AssertionError(f"[{group}] 链接形态异常(预期 symlink 或实体文件): {p_disk} kind={kind}")
        rows.append(row)
    face = "mover(dst 实体)" if is_mover else "非 mover(链接视图)"
    return {"hash": h, "save_path": sp, "face": face, "rows": rows}


# ================================================================ RM04-32


def test_rm04_32_e7_filemap_consistency():
    """[RM04-32] E7 交集判据取数核验(S1-S3+Z, 断言明细见模块 docstring 测试计划)

    前置: R: 在 + 双实例在线 + 副实例无 real-fake 残留。
    副作用/回滚/失败判据: 见模块 docstring(四行契约)。
    """
    _require_r_topology()
    case = M.case_dir("rm04_32")
    stop_lingering_product(case)
    qb = M.qbfake()
    assert not M.rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
    assert W.BT_BACKUP.is_dir(), f"副实例 BT_backup 不在(env_registry EXE 派生路径失效?): {W.BT_BACKUP}"
    for port in (instances.PRIMARY, instances.SECONDARY):
        guard.check_port(port)
        status = guard.check_online(instances.make(port))
        assert status != "disconnected", f"{port} connection_status=disconnected(假红陷阱), 拒跑"
    qb_up(instances.SECONDARY)
    qb_up(instances.PRIMARY)

    ev: dict = {
        "case": str(case),
        "topology": {
            "src_a": str(SRC_A),
            "src_b": str(SRC_B),
            "dst_a": "case/dst_a",
            "dst_b": "case/dst_b",
        },
    }
    p = None
    ha1 = None
    ha2 = None
    hb1 = None
    hb2 = None
    link_a = SRC_A / FILE_A
    links_b = (SRC_B / NSF_A, SRC_B / NSF_B)
    dst_a = case / "dst_a"
    dst_b = case / "dst_b"
    snap_before = bt_backup_snapshot()
    try:
        # ---- S1 造现场: 两形态组各一(FILE_LINKS 单文件平铺 / NoSubfolder 多文件剥根平铺)
        M.purge_tree(SRC_A.parent)
        M.purge_tree(SRC_B.parent)
        cfg, web_port = _write_cfg_fast_tick(case)
        p = start_bypass_app(case, cfg)
        assert p.wait_web(45), f"WEB 没起来:\n{p.log()[-800:]}"
        assert p.wait_log("整组迁移已启用", 20), f"relocate 启动日志缺失:\n{p.log()[-600:]}"
        # 组 A(FILE_LINKS): 双成员共享 1MiB 单文件(E2 同款造法)
        ha1 = M.fake_with_data(qb, FILE_A, FILE_A_SIZE, SRC_A, SALT_A, piece_len=PIECE_LENS[0], write=True)
        ha2 = M.fake_with_data(qb, FILE_A, FILE_A_SIZE, SRC_A, SALT_A, piece_len=PIECE_LENS[1], write=False)
        assert ha1 != ha2, "组 A 两颗 infohash 撞车(必须同文件异 infohash)"
        # 组 B(NoSubfolder): 数据手工平铺实写(剥根形态), 两成员同盐异 piece_len 经
        # contentLayout=NoSubfolder 加库(qB 5.2.3 剥根: 磁盘平铺 + files API 名单不带根前缀)。
        # 盐口径与 _build_nsf_raw 逐字一致: 每文件 salt = f"{SALT_B}:{rel}"(M.fake_multi 同款
        # 逐文件盐; 首跑实锤: 整体盐写盘 -> pieces 失配 -> qB 视为缺数据 stalledDL -> 产品
        # 「同时下载, 暂停整组」误停组 B, wait_complete 超时假红)
        torrent.write_file(str(SRC_B / NSF_A), NSF_A_SIZE, "random", f"{SALT_B}:{NSF_A}")
        torrent.write_file(str(SRC_B / NSF_B), NSF_B_SIZE, "random", f"{SALT_B}:{NSF_B}")
        assert (SRC_B / NSF_A).is_file() and (SRC_B / NSF_B).is_file(), "组 B 平铺数据未实写"
        raw_b1, ihb1 = _build_nsf_raw(SALT_B, PIECE_LENS[0])
        raw_b2, ihb2 = _build_nsf_raw(SALT_B, PIECE_LENS[1])
        assert ihb1 != ihb2, "组 B 两颗 infohash 撞车(必须同内容异 piece_len)"
        hb1, hb2 = ihb1, ihb2
        _add_with_layout(qb, raw_b1, str(SRC_B), ihb1, "NoSubfolder")
        _add_with_layout(qb, raw_b2, str(SRC_B), ihb2, "NoSubfolder")
        M.wait_complete(qb, [ha1, ha2, ihb1, ihb2], 120)
        ga = M.wait_group(web_port, ha1, {ha1, ha2}, 30, "组 A 未归组")
        gb = M.wait_group(web_port, ihb1, {ihb1, ihb2}, 30, "组 B 未归组")
        assert ga["key"] != gb["key"], "两组组键撞车(独立根独立文件表失守)"
        M.wait_store_progress(web_port, [ha1, ha2, ihb1, ihb2], 60)
        ev["S1_scene"] = {
            "group_a": [ha1[:8], ha2[:8]],
            "group_b": [ihb1[:8], ihb2[:8]],
            "nsf_disk_flat": all((SRC_B / n).is_file() for n in (NSF_A, NSF_B)),
        }
        _flush(ev, case, "S1")

        # ---- S2 两形态各搬迁 armed(均 file_links: 组 B 2 文件 < 阈值 8 且平铺不提供目录别名)
        result_a = M.cmd_post_and_wait(
            web_port, f"/api/torrents/{ha1}/location", {
                "location": str(dst_a),
                "confirm": True
            }
        )
        item_a = M.one_started_item(result_a)
        assert item_a.get("form") == "file_links", f"组 A 形态非 file_links: {json.dumps(item_a, ensure_ascii=False)[:400]}"
        job_a = item_a.get("job_id")
        assert job_a, f"组 A started 项缺 job_id: {json.dumps(item_a, ensure_ascii=False)[:400]}"
        assert p.wait_log(f"job {job_a}: 已武装收尾", 60), "组 A 未武装(日志锚缺失)"
        M.wait_until(
            lambda: M.reparse_kind(link_a) == "symlink" or None, 60, lambda: f"组 A 链接形态异常: {M.reparse_kind(link_a)}"
        )
        assert M.norm(_readlink_norm(link_a)).startswith(
            M.norm(dst_a)
        ), f"组 A symlink 未指 dst_a: {_readlink_norm(link_a)}"

        result_b = M.cmd_post_and_wait(
            web_port, f"/api/torrents/{ihb1}/location", {
                "location": str(dst_b),
                "confirm": True
            }
        )
        item_b = M.one_started_item(result_b)
        assert item_b.get("form") == "file_links", f"组 B 形态非 file_links: {json.dumps(item_b, ensure_ascii=False)[:400]}"
        job_b = item_b.get("job_id")
        assert job_b, f"组 B started 项缺 job_id: {json.dumps(item_b, ensure_ascii=False)[:400]}"
        assert p.wait_log(f"job {job_b}: 已武装收尾", 60), "组 B 未武装(日志锚缺失)"
        for n in (NSF_A, NSF_B):
            link = SRC_B / n
            M.wait_until(
                lambda link=link: M.reparse_kind(link) == "symlink" or None,
                60,
                lambda link=link: f"组 B 链接形态异常: {link} {M.reparse_kind(link)}"
            )
            assert M.norm(_readlink_norm(link)).startswith(M.norm(dst_b)), \
                f"组 B symlink 未指 dst_b: {link} -> {_readlink_norm(link)}"
        # 两枚 armed 组账(成员详情 relocate 相位 = 产品快照实时面)
        for h in (ha1, ihb1):
            M.wait_until(
                lambda h=h:
                ((M.member_detail(web_port, h) or {}).get("relocate") or {}).get("phase") == "armed" or None,
                30,
                lambda: f"armed 账相位未落(h={h[:8]})"
            )
        ev["S2_armed"] = {
            "job_a": job_a,
            "job_b": job_b,
            "form_a": item_a.get("form"),
            "form_b": item_b.get("form"),
            "link_a_target": _readlink_norm(link_a),
            "links_b_targets": [_readlink_norm(SRC_B / n) for n in (NSF_A, NSF_B)],
        }
        _flush(ev, case, "S2")

        # ---- S3 取数对照: 逐成员经产品 WEB 只读端点取清单 x 磁盘实况逐文件双一致
        checks = []
        checks.append(_assert_member_list(web_port, qb, ha1, {FILE_A}, dst_a, "A"))
        checks.append(_assert_member_list(web_port, qb, ha2, {FILE_A}, dst_a, "A"))
        checks.append(_assert_member_list(web_port, qb, ihb1, {NSF_A, NSF_B}, dst_b, "B"))
        checks.append(_assert_member_list(web_port, qb, ihb2, {NSF_A, NSF_B}, dst_b, "B"))
        # 双组各恰一枚 mover(实体面)/一枚非 mover(链接视图面) —— armed 拓扑钉扎
        # (评审 R26/R34 口径: 「自证」必须落断言, 双 mover 回归会让穿链 size 同证整面静默失效)
        for group, members in (("A", (ha1, ha2)), ("B", (ihb1, ihb2))):
            sps = {M.norm((qb.torrent(h) or {}).get("save_path") or "") for h in members}
            assert len(sps) == 2 and M.norm(str(dst_a if group == "A" else dst_b)) in sps, \
                f"[{group}] 非「恰一枚 mover 落 dst + 恰一枚留 src」拓扑: {sps}"
        ev["S3_filemap"] = {"members": checks}
        _flush(ev, case, "S3")

    finally:
        # ---- Z 收尾: 产品退出 -> 实例恢复 -> 删种子(连数据) -> BT_backup 核净 -> 目录删净
        ev["Z_cleanup"] = {}
        errs: list[str] = []
        if p is not None:
            try:
                ev["Z_cleanup"]["product_stop_rc"] = p.stop(40)
            except Exception as e:  # noqa: BLE001
                errs.append(f"产品停止失败: {e!r}")
        _flush(ev, case, "Z1")
        for port in (instances.SECONDARY, instances.PRIMARY):
            try:
                qb_up(port)  # 环境还原: 双实例回在线
            except Exception as e:  # noqa: BLE001
                errs.append(f"real.up {port} 恢复失败: {e!r}")
        try:
            ev["Z_cleanup"]["seeds_removed"] = M.rm_all_fakes(M.qbfake())
        except Exception as e:  # noqa: BLE001
            errs.append(f"real-fake 种子清理失败: {e!r}")
        try:
            removed = []
            my_hashes = [h for h in (ha1, ha2, hb1, hb2) if h]
            for ih in my_hashes:
                for suffix in (".fastresume", ".torrent", ".fastresume.bak", ".torrent.bak"):
                    fp = W.BT_BACKUP / f"{ih}{suffix}"
                    if fp.is_file():
                        fp.unlink()
                        removed.append(fp.name)
            now = bt_backup_snapshot()
            residue = [k for k in now if k not in snap_before and not any(k.startswith(ih) for ih in my_hashes)]
            before_files = {k: v for k, v in snap_before.items() if (W.BT_BACKUP / k).is_file() and k != "queue"}
            changed = [k for k, v in before_files.items() if now.get(k) != v]
            ev["Z_cleanup"].update({"bt_backup_removed": removed, "residue": residue, "changed": changed})
            if residue:
                errs.append(f"BT_backup 出现非本用例的未知残留: {residue}")
            if changed:
                errs.append(f"开工前已有 BT_backup 逐种子文件被改动: {changed}")
        except Exception as e:  # noqa: BLE001
            errs.append(f"BT_backup 核净失败: {e!r}")
        _flush(ev, case, "Z2")
        try:
            M.purge_tree(SRC_A.parent)
            M.purge_tree(SRC_B.parent)
            M.purge_tree(case)
        except Exception as e:  # noqa: BLE001
            errs.append(f"目录清理失败: {e!r}")
        for link in (link_a, *links_b):
            if link is not None and M._is_link(str(link)):
                errs.append(f"链接零残留失守: {link}")
        if errs:
            raise AssertionError(f"收尾未净(Z): {'; '.join(errs)}")
