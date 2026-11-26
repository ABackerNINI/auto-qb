"""

同源声明: _write_cfg_fast_tick 复用 test_rm04_e2_alias_add_pass.py(与其
test_rm04_e9_selfheal_nomisfire.py / test_rm04_offline_delete_settle.py 同源, 函数体逐字一致,
单侧改动须同步); _assert_healthy 复用 E2(仅与 test_rm04_e9_selfheal_nomisfire.py 同源,
offline 文件无此 helper); _flush 同源(前缀按用例本地化)。拓扑与 RM04-28(E2) 同构共用(卡面「前置:
同 RM04-28 拓扑(同片先后跑, 共用组外异名拓扑)」): FILE_LINKS 双成员组 + 组外异名种子 armed
后带数据落旧根, 常量按用例本地化(rm04_29 子树隔离, 不共享运行态 —— 遍间真清场重造)。
[RM04-29] [E4] 组外异名带文件删除放行: armed 态删除组外异名种子(带文件, 与成员无文件交集)
→ 当场删除成功(误拦2不复现, E1 并入腿: 修复前被 D16 拒); 真实文件清干净(磁盘逐文件对照);
别名与成员做种无损(账面/状态零扰动)。

计划 plans/26-11-17-0636-plan-real-rm04-relocate-refactor-verify.html §03.4 RM04-29 用例卡
(E4; 误拦2修正面 = qbapi._relocate_delete_blocked R3 文件级交集精判修复 —— X 与成员/别名
零文件交集 = 放行, 不相交不拒)。

切分(不测三遍, 计划 §03.2 E4 行): 与 RM04-28(E2) 共用组外异名拓扑但断言面互补 —— 异名
「添加」放行+全链归 RM04-28, 本用例只断异名「带文件删除」放行面(armed 态 D16 精判)+ 删除
后的磁盘/账面无损面; RM04-34(E9) S3 已同证误拦2消失(它以「两误拦双证」为面), 本用例把该
面独立耐久化并加深磁盘逐文件对照(卡面新增深度), 不复写 E9 其余段。

窗口期纪律(片D 切片 26-11-18-2308 §06 坑点1 对本用例的落点): 误拦2探针必须在 D16 登记
存续期(armed, 别名在账)内、qB 在线时执行 —— 本用例无下线窗/无重启(卡面副作用无离线窗),
armed 态全程存续, 探针固定在 S4(armed 稳态)执行; 收敛链消费别名只发生在重启落位后 1-2 拍,
本用例不重启, 无「重启后探针扑空」面。

## 测试计划(单测试函数, 五段)
- G0 开工闸: R: 拓扑在 + 双实例在线(connection_status 非 disconnected) + 副实例无
  real-fake 残留; 产品起(旁路 runner, fast tick, 阈值 8)。
- S1 造现场: 双成员共享文件组(file_links)落 R: → 齐完成 → 归组断言(成员组恰含双成员)。
- S2 搬迁 armed: WEB 迁移(confirm 直投 → started form=file_links + job_id)→ 已武装收尾
  → symlink 现场(指 dst)。
- S3 armed 态添加组外异名种子(共用 E2 拓扑腿): 带数据落旧根 → 完成 → 健康(1.0 做种)
  + 不入成员组 + 实文件在盘。
- S4 误拦2探针(armed, qB 在线, D16 登记存续期): SRC/dst 磁盘逐文件快照(lstat 不跟随链接)
  → 产品 WEB 删除 X(delete_files=true)→ 回执 ok 非 error(误拦2不复现, 修复前被 D16 拒)
  → qB 无 X → X 实文件清净 → 逐文件对照(消失集恰 = {X 实文件}; SRC 零计划外新条目; dst 树
  逐文件不变 = 新位置数据零波及)→ 别名 symlink 原样(形态+指向)→ 成员健康(做种无损)
  → job 仍 armed(账面零扰动)+ 零计划外「迁移发起」+ 组行原样。
- Z 收尾: 产品优雅退出 → real-fake 删净(连数据)→ BT_backup 本用例哈希残留清除 + 逐文件
  比对开工快照 → case 树与 R: 子树删净 + 别名 lstat 零残留。

前置: 环境1(R: 在, src=R:/qbt-fake/rm04/rm04_29/src 与 dst=D: 异盘) + 双测试实例在线
      (没起先 `commands run real.up -- --port <白名单端口>`); 副实例无 real-fake 残留;
      wrapper 名册窄化旁路在位(沿 RM04-20/21/27/34 授权, 零新增旁路面); 独占约 2-3 分钟,
      conftest serial 锁串行保护。R: 缺席 => skip 不回退落点(钉死口径)。
副作用: armed 组在场 + 组外异名种子带文件删除一次(其带数据落旧根的添加属拓扑搭建)+
      state 账。
回滚: 产品优雅退出(sentinel 通路); 双实例保持在线; real-fake 种子删净(连数据, X 已在
      S4 删除); BT_backup 只清本用例哈希残留 + 逐文件比对开工快照(queue 豁免); case 树与
      R:/qbt-fake/rm04/rm04_29 子树删净(purge_tree 不递归删穿链接); 别名 lstat 零残留。
失败判据: 删除回 error/confirm(D16 拒 = 误拦2复发); qB 仍有 X 或 X 实文件残留(磁盘清净
      失守); 逐文件对照失守(波及他文件/dst 树被扰); 别名形态或指向变化/成员异常态或
      progress 失守/组行扰动/计划外「迁移发起」(做种无损面失守); 收尾有残留。

跑法: `commands run real.run -- --case RM04-29 --yes`(不要裸 pytest)。
"""
from __future__ import annotations

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
import test_rm04_relocate_window as W  # noqa: E402  (RM04-20/21/27/34 同款旁路接线/收尾 helper, 授权见其 docstring)
import test_rm04_e2_alias_add_pass as E2  # noqa: E402  (同源 helper 复用 + 共用组外异名拓扑声明, 见模块 docstring)

from lib import guard, instances  # noqa: E402

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="本片断言含 Windows 特有语义(symlink/优雅退出通路)"),
]

# 拓扑单点(钉死, 与 E2 同构; 子树隔离): src 在 R: 内存盘
R_ROOT = Path("R:/qbt-fake/rm04")
SRC = R_ROOT / "rm04_29" / "src"
FILE_NAME = "rm04c29.bin"
OUTSIDER_NAME = "rm04c29x.bin"  # 组外异名 X: armed 后添加(落旧根), S4 带文件删除(探针对象)
FILE_SIZE = 1024 * 1024
OUTSIDER_SIZE = 256 * 1024
PIECE_LENS = (16384, 32768)  # 同文件异 infohash 的区分面(两颗成员)
SALT = "rm04c29"

# 复用 RM04-21 的旁路面 + E2 同源 helper(单一实现, 不另抄一份)
_require_r_topology = W._require_r_topology
start_bypass_app = W.start_bypass_app
stop_lingering_product = W.stop_lingering_product
qb_up = W.qb_up
bt_backup_snapshot = W.bt_backup_snapshot
_write_cfg_fast_tick = E2._write_cfg_fast_tick
_assert_healthy = E2._assert_healthy
_readlink_norm = E2._readlink_norm
# 副实例 BT_backup 路径单点在 W, 函数内按需取(收集期不探测 EXE)

# 片E 证据目录(任务口径: 逐案 evidence 落 tests/real/.work/rm04-sliceE/; 时刻后缀防覆写)
SLICE_EV = HERE.parent / ".work" / "rm04-sliceE"


def _flush(ev: dict, case: Path, tag: str) -> None:
    """证据落盘(gitignored .work/rm04-sliceE): 全量断言现场 + 产品日志副本, 时刻后缀防覆写。"""
    ev["ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
    SLICE_EV.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    (SLICE_EV / f"rm04_29_{tag}_evidence_{stamp}.json"
    ).write_text(json.dumps(ev, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    try:
        log = M.log_text(case)
    except Exception as e:  # noqa: BLE001 —— 取证失败如实带错, 不掩盖主断言
        log = f"<log read failed: {e!r}>"
    (SLICE_EV / f"rm04_29_{tag}_auto-qb_{stamp}.log").write_text(log, encoding="utf-8")


def _tree_snap(root: Path) -> dict:
    """磁盘逐文件快照(lstat 不跟随链接): rel 路径 -> {kind, size}。链接/目录 size=None。

    kind 判定: reparse 点(junction/symlink, M.reparse_kind 单点口径)优先, 其次目录/普通
    文件 —— 逐文件对照的「消失集恰 = X 实文件」断言面。"""
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
        # 不跟随链接目录(walk 默认 followlinks=False, 链接目录留在 dirnames 但不下钻;
        # 链接目录本身已在上面的循环里按 kind 记账)
    return out


# ================================================================ RM04-29


def test_rm04_29_e4_outsider_delete():
    """[RM04-29] E4 组外异名带文件删除放行(五段 S1-S4+Z, 断言明细见模块 docstring)

    前置: R: 在 + 双实例在线 + 副实例无 real-fake 残留; wrapper 收编入库版在位。
    副作用/回滚/失败判据: 见模块 docstring(四行契约)。
    """
    _require_r_topology()
    case = M.case_dir("rm04_29")
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

    ev: dict = {"case": str(case), "topology": {"src": str(SRC), "dst": "case/dst"}}
    p = None
    h1 = None
    h2 = None
    hx = None
    link = SRC / FILE_NAME  # finally 的别名零残留检查用(早退时按"建没建"如实判)
    dst = case / "dst"
    snap_before = bt_backup_snapshot()
    try:
        # ---- S1 造现场: 双成员共享文件组(file_links)
        M.purge_tree(SRC.parent)
        cfg, web_port = _write_cfg_fast_tick(case)
        p = start_bypass_app(case, cfg)
        assert p.wait_web(45), f"WEB 没起来:\n{p.log()[-800:]}"
        assert p.wait_log("整组迁移已启用", 20), f"relocate 启动日志缺失:\n{p.log()[-600:]}"
        h1 = M.fake_with_data(qb, FILE_NAME, FILE_SIZE, SRC, SALT, piece_len=PIECE_LENS[0], write=True)
        h2 = M.fake_with_data(qb, FILE_NAME, FILE_SIZE, SRC, SALT, piece_len=PIECE_LENS[1], write=False)
        assert h1 != h2, "两颗 infohash 撞车(必须同文件异 infohash)"
        M.wait_complete(qb, [h1, h2], 120)
        M.wait_group(web_port, h1, {h1, h2}, 30, "双成员组未归组")
        M.wait_store_progress(web_port, [h1, h2], 60)
        src_str = (qb.torrent(h1) or {}).get("save_path") or ""
        assert M.norm(src_str) == M.norm(SRC), f"成员 save_path 异常: {src_str}"
        ev["S1_scene"] = {"members": [h1[:8], h2[:8]], "src": src_str}
        _flush(ev, case, "S1")

        # ---- S2 搬迁 armed(file_links)
        result = M.cmd_post_and_wait(web_port, f"/api/torrents/{h1}/location", {"location": str(dst), "confirm": True})
        item = M.one_started_item(result)
        assert item.get("form") == "file_links", f"形态非 file_links: {json.dumps(item, ensure_ascii=False)[:400]}"
        job_id = item.get("job_id")
        assert job_id, f"started 项缺 job_id: {json.dumps(item, ensure_ascii=False)[:400]}"
        assert p.wait_log("已武装收尾", 60), "未武装(日志锚缺失)"
        M.wait_until(lambda: M.reparse_kind(link) == "symlink" or None, 60, lambda: f"链接形态异常: {M.reparse_kind(link)}")
        assert M.norm(_readlink_norm(link)).startswith(M.norm(dst)), f"symlink 未指 dst: {_readlink_norm(link)}"
        ev["S2_armed"] = {"job": job_id, "form": "file_links", "link": str(link), "target": _readlink_norm(link)}
        _flush(ev, case, "S2")

        # ---- S3 armed 态添加组外异名种子(共用 E2 拓扑腿: 带数据落旧根)
        hx = M.fake_with_data(qb, OUTSIDER_NAME, OUTSIDER_SIZE, SRC, "rm04c29x", piece_len=16384, write=True)
        M.wait_complete(qb, [hx], 120)
        tx = _assert_healthy(qb, hx, "组外异名 X(添加后)")
        gx = M.group_row(M.groups_view(web_port), hx)
        assert gx is None or set(gx["members"]) == {hx}, f"组外异名 X 被误归入他组: {gx}"
        assert (SRC / OUTSIDER_NAME).is_file(), "X 实文件未落盘"
        assert M.norm(tx.get("save_path") or "") == M.norm(SRC), f"X 落点异常(应为旧根): {tx.get('save_path')}"
        ev["S3_outsider_added"] = {"outsider": hx[:8], "outsider_state": tx.get("state")}
        _flush(ev, case, "S3")

        # ---- S4 误拦2探针(armed, qB 在线, D16 登记存续期): 组外异名带文件删除放行
        snap_src_before = _tree_snap(SRC)
        snap_dst_before = _tree_snap(dst)
        assert OUTSIDER_NAME in snap_src_before, f"快照缺 X 实文件: {snap_src_before}"
        before_issued = M.log_text(case).count("迁移发起")
        result_d = M.cmd_post_and_wait(web_port, f"/api/torrents/{hx}/delete", {"delete_files": True})
        assert (result_d or {}).get("status") == "ok", \
            f"误拦2复发: 组外异名带文件删除被拒: {json.dumps(result_d, ensure_ascii=False)[:500]}"
        M.wait_until(lambda: qb.torrent(hx) is None, 30, "删除回执 ok 但 qB 仍有 X")
        M.wait_until(lambda: not (SRC / OUTSIDER_NAME).exists() or None, 30, "删除后 X 实文件残留(磁盘清净失守)")
        # 磁盘逐文件对照: 消失集恰 = {X 实文件}; SRC 零计划外新条目; dst 树零波及
        snap_src_after = _tree_snap(SRC)
        snap_dst_after = _tree_snap(dst)
        gone = {k: v for k, v in snap_src_before.items() if k not in snap_src_after}
        assert set(gone) == {OUTSIDER_NAME}, \
            f"逐文件对照失守: SRC 消失集 {sorted(gone)} != {{X 实文件}}(波及他文件)"
        added = [k for k in snap_src_after if k not in snap_src_before]
        assert not added, f"SRC 出现计划外新条目: {added}"
        assert snap_dst_after == snap_dst_before, \
            f"dst 树被删除波及(新位置数据失守): before={snap_dst_before} after={snap_dst_after}"
        # 别名与成员做种无损(账面/状态零扰动)
        assert M.reparse_kind(link) == "symlink", f"删除探针扰动别名形态: {link}"
        assert M.norm(_readlink_norm(link)).startswith(M.norm(dst)), \
            f"删除探针扰动别名指向: {_readlink_norm(link)}"
        for h in (h1, h2):
            _assert_healthy(qb, h, "成员(删除扰动面)")
        # 账面零扰动观测面 = 成员详情 relocate 相位(产品快照内存值, 实时) —— journal 此刻
        # 尚无文件(它由 daemon 在下线窗写, armed 期 journal_of 恒 None; E2 首跑实锤同锚错)
        jrow = M.wait_until(
            lambda: ((M.member_detail(web_port, h1) or {}).get("relocate") or {}).get("phase") == "armed" or None, 15,
            lambda: f"job 相位受扰: "
            f"{((M.member_detail(web_port, h1) or {}).get('relocate') or {}).get('phase')}"
        )
        assert M.log_text(case).count("迁移发起") == before_issued, "删除探针引发计划外「迁移发起」"
        g_after = M.group_row(M.groups_view(web_port), h1)
        assert g_after is not None and set(g_after["members"]) == {h1, h2}, f"组行受扰: {g_after}"
        ev["S4_misfire2_gone"] = {
            "status": (result_d or {}).get("status"),
            "file_gone": True,
            "gone_set": sorted(gone),
            "src_no_new": True,
            "dst_unchanged": True,
            "alias_kept": True,
            "job_phase": jrow,
            "group_intact": True
        }
        _flush(ev, case, "S4")

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
            my_hashes = [h for h in (h1, h2, hx) if h]
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
            M.purge_tree(SRC.parent)
            M.purge_tree(case)
        except Exception as e:  # noqa: BLE001
            errs.append(f"目录清理失败: {e!r}")
        if h1 and M._is_link(str(link)):
            errs.append(f"别名零残留失守: {link}")
        if errs:
            raise AssertionError(f"收尾未净(Z): {'; '.join(errs)}")
