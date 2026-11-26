"""

同源声明: _write_cfg_fast_tick/_await_wrapper_patched/_flush 三件 helper 与 test_rm04_offline_delete_settle.py 同源(函数体逐字一致, docstring/证据文件名前缀按用例本地化), 单侧改动须同步另一文件(评审 R23)。[RM04-34] [E9] 自愈全链·误拦消失: 生产等价态(R6 场景: 组外异名种子在场 + armed 组 +
离线窗)→ 零人工干预收敛 done; 窗口期内两单误拦均消失(异名添加零弹窗 = 误拦1, 组外异名
带文件删除放行 = 误拦2)双证。

计划 plans/26-11-17-0636-plan-real-rm04-relocate-refactor-verify.html §03.4 RM04-34 用例卡
(E9; E1 两误拦修正面并入: 误拦1 = 异名添加曾弹 finalize_window confirm(R4 放行扩张修复),
误拦2 = 组外异名带文件删除曾被 D16 拒(qbapi._relocate_delete_blocked R3 文件级交集精判
修复, 不相交 = 放行))。

切分(不测三遍, 计划 §03.2 E9 行): 自愈主链 B1-B7 深断言归 RM04-21(test_rm04_reconcile_
reenter.py)已入库断言 —— 本用例不复写 B 链(启动对账重入/改写账逐键/fastresume 字面/
qb_side_check_failed 假阴性面均不在断言面), 只断 **E 专属面**: 1) 零人工干预收敛 done
(收敛行/相位链可观测); 2) 窗口期内两单误拦均消失(双证); 3) 组外异名种子在场态的健康面
(其状态不受 armed 组/离线窗/收敛链扰动, 且收敛链对在场组外异名正确豁免)。流程驱动面
(改写 settled/落位 dst)只取让流程可推进的最小断, 引用 RM04-21。

窗口期口径与探针布点(首跑实锤修正): 收尾窗 = armed→done 全程(下线窗是其中改写子窗)。
误拦2探针必须在 **D16 登记存续期**(armed, 别名在账)内、qB 在线时执行(删除真落 qB),
而收敛链在全员落位后 1-2 拍内即消费别名(done)—— 重启后再探针必然撞上已收尾(三跑实锤:
S6 到场时别名已被收尾删除, D16 登记已随终态撤销, 探针失去被测面)⇒ 误拦2固定在 armed
下线窗之前执行。误拦1探针在下线窗内执行(qB 已下线、产品在位 —— precheck_add 纯本地
判定: 活跃 job 作用域登记 + 落点链接实况 + 目标卷剩余, 零 qB 调用, relocate_plan.
precheck_add docstring 单点)。组外异名种子两颗分工: X1 全程在场(贯穿下线窗与收敛链,
R6 在场面 + 收敛豁免面对象), X2 为误拦2探针专用(armed 期带文件删除)。

## 测试计划(单测试函数, 七段)
- G0 开工闸: R: 拓扑在 + 双实例在线(connection_status 非 disconnected) + 副实例无
  real-fake 残留; 产品起(旁路 runner, fast tick, 阈值 8)。
- S1 造现场: 双成员共享文件组(file_links)落 R: + 组外异名 X1/X2(异名实文件, 同旧根,
  与成员零文件交集)→ 四颗齐完成 → 归组断言(成员组恰含双成员; X1/X2 不入组)。
- S2 搬迁 armed: WEB 迁移(confirm 直投 → started form=file_links + job_id)→ 已武装收尾
  → symlink 现场(指 dst)。
- S3 误拦2探针(armed, qB 在线, D16 登记存续): 产品 WEB 删除 X2(delete_files=true)→
  回执 ok 非 error(D16 不拒; 误拦2不复现)→ qB 无 X2 + 磁盘 X2 实文件清净 + 成员/别名
  零扰动 + 零计划外「迁移发起」。
- S4 下线窗: 双实例优雅下线 → daemon 改写非 mover settled(journal; mover 面按产品账
  判定 —— 产品自选 mover 不必等于发起 hash, 三跑实锤)→ 开窗观测面双押(单断)。
- S5 误拦1探针(下线窗内, qB 下线、产品在位): precheck-add {save_path=旧根, name=X1 名}
  → cls=ok 零 confirm(误拦1不复现; finalize_window 门零命中)。
- S6 重启: 双实例回在线 → 双成员落 dst(completion_on 锚零 recheck, 异常态零)→ X1 在场
  且健康(progress 1.0 / 无 error/missing / 文件在盘 / 落点未动)。
- S7 零人工干预收敛: S6 后**零测试动作** → 「收尾完成」行(删链门依赖清零 + 已在线删除
  别名; X1 在场仍清零 = 收敛豁免面对象)→ job done/finalized → symlink 删除 → 组键归一
  dst → 成员健康。
- Z 收尾: 产品优雅退出 → real-fake 删净(连数据)→ BT_backup 本用例哈希残留清除 + 逐文件
  比对开工快照 → case 树与 R: 子树删净 + 别名 lstat 零残留。

前置: 环境1(R: 在, src=R:/qbt-fake/rm04/rm04_34/src 与 dst=D: 异盘) + 双测试实例在线
      (没起先 `commands run real.up -- --port <白名单端口>`); 副实例无 real-fake 残留;
      wrapper 名册窄化旁路在位(沿 RM04-20/21/27 授权, 零新增旁路面); 独占约 3-4 分钟,
      conftest serial 锁串行保护。R: 缺席 => skip 不回退落点(钉死口径)。
副作用: 一次真搬迁(mover 被 qB 原生搬 R:->D:)+ 一次下线窗改写(非 mover fastresume 被
      daemon 改写)+ 双实例优雅下线/重启各一次 + 组外异名 X2 带文件删除一次 + state 账。
回滚: 产品优雅退出(sentinel 通路); 双实例恢复在线; real-fake 种子删净(连数据, X2 已在
      S3 删除); BT_backup 只清本用例哈希残留 + 逐文件比对开工快照(queue 豁免); case 树
      与 R:/qbt-fake/rm04/rm04_34 子树删净(purge_tree 不递归删穿链接); 别名 lstat 零残留。
失败判据: 需人工干预才收敛(收尾完成行缺失/job 非 done); 窗口期内出现任一误拦(误拦1
      precheck 回 confirm 或 finalize_window 命中; 误拦2 删除回 error 或文件残留);
      收敛 done 但组外异名种子状态受扰(X1 删除前 error/missing/recheck/落点被扰);
      成员落位失败或异常态; 收尾有残留。

跑法: `commands run real.run -- --case RM04-34 --yes`(不要裸 pytest)。
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_rm04_relocate as M  # noqa: E402  (复用 RM04 的造种/清场/断言助手)
import test_rm04_relocate_window as W  # noqa: E402  (RM04-20/21/27 同款旁路接线/收尾 helper, 授权见其 docstring)

from lib import app, guard, instances  # noqa: E402
from auto_qb.core.modules import relocate_units as ru  # noqa: E402  (产品码: 相位/原因常量)

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="本片断言含 Windows 特有语义(symlink/优雅退出通路)"),
]

# 拓扑单点(钉死, 见模块 docstring; 与 RM04-20/21/22/23/25/26/27 的子树隔离): src 在 R: 内存盘
R_ROOT = Path("R:/qbt-fake/rm04")
SRC = R_ROOT / "rm04_34" / "src"
FILE_NAME = "rm04c34.bin"
OUTSIDER1_NAME = "rm04c34x.bin"  # 组外异名 X1: 全程在场(R6 在场面 + 收敛豁免面对象)
OUTSIDER2_NAME = "rm04c34y.bin"  # 组外异名 X2: 误拦2探针专用(armed 期带文件删除)
FILE_SIZE = 1024 * 1024
OUTSIDER_SIZE = 256 * 1024
PIECE_LENS = (16384, 32768)  # 同文件异 infohash 的区分面(两颗成员)
SALT = "rm04c34"

# 复用 RM04-21 的旁路面(单一实现, 不另抄一份)
_require_r_topology = W._require_r_topology
start_bypass_app = W.start_bypass_app
stop_lingering_product = W.stop_lingering_product
qb_up = W.qb_up
qb_down = W.qb_down
bt_backup_snapshot = W.bt_backup_snapshot
wrapper_lines = W.wrapper_lines
live_daemon_pid = W.live_daemon_pid
window_regime_face = W.window_regime_face
# 副实例 BT_backup 路径单点在 W, 函数内按需取(收集期不探测 EXE)

# 片D 证据目录(任务口径: 逐案 evidence 落 tests/real/.work/rm04-sliceD/; 时刻后缀防覆写)
SLICE_EV = HERE.parent / ".work" / "rm04-sliceD"


def _flush(ev: dict, case: Path, tag: str) -> None:
    """证据落盘(gitignored .work/rm04-sliceD): 全量断言现场 + 产品日志副本, 时刻后缀防覆写。"""
    ev["ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
    SLICE_EV.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    (SLICE_EV / f"rm04_34_{tag}_evidence_{stamp}.json"
    ).write_text(json.dumps(ev, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    try:
        log = M.log_text(case)
    except Exception as e:  # noqa: BLE001 —— 取证失败如实带错, 不掩盖主断言
        log = f"<log read failed: {e!r}>"
    (SLICE_EV / f"rm04_34_{tag}_auto-qb_{stamp}.log").write_text(log, encoding="utf-8")


def _write_cfg_fast_tick(case: Path) -> tuple[Path, int]:
    """RM04-34 专用配置: 在 M.write_cfg 基础上把 main_tick 2S -> 1S(片C 沉淀派生)。

    收尾核验/删链门/收敛链按主循环拍推进, 1S 拍让零人工干预收敛在落位后秒级发生;
    sync_interval 1.5S 不变。"""
    cfg, web_port = M.write_cfg(case, relocate=True, alias_threshold=8)
    text = cfg.read_text(encoding="utf-8")
    assert "main_tick: 2S" in text
    cfg.write_text(text.replace("main_tick: 2S", "main_tick: 1S"), encoding="utf-8")
    return cfg, web_port


def _assert_healthy(qb, ih: str, what: str) -> dict:
    """种子健康面: progress 1.0 + 无 error/missing/checking 异常态。返回 torrent 快照。"""
    t = qb.torrent(ih) or {}
    assert t.get("progress") == 1.0, f"{what} {ih[:8]} progress != 1.0: {t.get('progress')}"
    st = str(t.get("state") or "").lower()
    assert "error" not in st and "missing" not in st and "checking" not in st, f"{what} {ih[:8]} 异常态: {t.get('state')}"
    return t


def _await_wrapper_patched(wl0: int, case: Path, timeout: float = 15.0) -> list[str]:
    """等 wrapper patch 行或在位健康 daemon(daemon 刚拉起时 patch 行/心跳落盘有 ~1s 竞态窗,
    首跑实锤: wrapper start 行已见而 patched 行未落, 立即断言假红)。"""
    def probe():
        patched = [ln for ln in wrapper_lines()[wl0:] if "patched rd._proc_absent" in ln]
        if patched:
            return patched
        pid = live_daemon_pid(case)
        if pid:
            return [f"reused live patched daemon pid={pid}(前轮宽限窗内在位, 产品按健康 watcher 复用)"]
        return None

    return M.wait_until(probe, timeout, "wrapper patch 行与在位健康 daemon 均未出现(旁路没装上?)")


# ================================================================ RM04-34


def test_rm04_34_e9_selfheal_no_misfire():
    """[RM04-34] E9 自愈全链·误拦消失(七段 S1-S7+Z, 断言明细见模块 docstring)

    前置: R: 在 + 双实例在线 + 副实例无 real-fake 残留; wrapper 收编入库版在位。
    副作用/回滚/失败判据: 见模块 docstring(四行契约)。
    """
    _require_r_topology()
    case = M.case_dir("rm04_34")
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
    hx1 = None
    hx2 = None
    link = SRC / FILE_NAME  # finally 的别名零残留检查用(早退时按"建没建"如实判)
    dst = case / "dst"
    snap_before = bt_backup_snapshot()
    wl0 = len(wrapper_lines())
    try:
        # ---- S1 造现场: 双成员共享文件组 + 组外异名 X1(全程在场)/X2(探针专用)
        M.purge_tree(SRC.parent)
        cfg, web_port = _write_cfg_fast_tick(case)
        p = start_bypass_app(case, cfg)
        assert p.wait_web(45), f"WEB 没起来:\n{p.log()[-800:]}"
        assert p.wait_log("整组迁移已启用", 20), f"relocate 启动日志缺失:\n{p.log()[-600:]}"
        h1 = M.fake_with_data(qb, FILE_NAME, FILE_SIZE, SRC, SALT, piece_len=PIECE_LENS[0], write=True)
        h2 = M.fake_with_data(qb, FILE_NAME, FILE_SIZE, SRC, SALT, piece_len=PIECE_LENS[1], write=False)
        assert h1 != h2, "两颗 infohash 撞车(必须同文件异 infohash)"
        hx1 = M.fake_with_data(qb, OUTSIDER1_NAME, OUTSIDER_SIZE, SRC, "rm04c34x1", piece_len=16384, write=True)
        hx2 = M.fake_with_data(qb, OUTSIDER2_NAME, OUTSIDER_SIZE, SRC, "rm04c34x2", piece_len=32768, write=True)
        assert len({h1, h2, hx1, hx2}) == 4, "infohash 撞车"
        M.wait_complete(qb, [h1, h2, hx1, hx2], 120)
        M.wait_group(web_port, h1, {h1, h2}, 30, "双成员组未归组(X 不该入组)")
        for hx, nm in ((hx1, "X1"), (hx2, "X2")):
            gx = M.group_row(M.groups_view(web_port), hx)
            assert gx is None or set(gx["members"]) == {hx}, f"组外异名 {nm} 被误归入他组: {gx}"
        M.wait_store_progress(web_port, [h1, h2], 60)
        src_str = (qb.torrent(h1) or {}).get("save_path") or ""
        assert M.norm(src_str) == M.norm(SRC), f"成员 save_path 异常: {src_str}"
        assert (SRC / OUTSIDER1_NAME).is_file() and (SRC / OUTSIDER2_NAME).is_file(), "X 实文件未落盘"
        ev["S1_scene"] = {"members": [h1[:8], h2[:8]], "outsider1": hx1[:8], "outsider2": hx2[:8], "src": src_str}
        _flush(ev, case, "S1")

        # ---- S2 搬迁 armed(file_links)
        result = M.cmd_post_and_wait(web_port, f"/api/torrents/{h1}/location", {"location": str(dst), "confirm": True})
        item = M.one_started_item(result)
        assert item.get("form") == "file_links", f"形态非 file_links: {json.dumps(item, ensure_ascii=False)[:400]}"
        job_id = item.get("job_id")
        assert job_id, f"started 项缺 job_id: {json.dumps(item, ensure_ascii=False)[:400]}"
        assert p.wait_log("已武装收尾", 60), "未武装(日志锚缺失)"
        M.wait_until(lambda: M.reparse_kind(link) == "symlink" or None, 60, lambda: f"链接形态异常: {M.reparse_kind(link)}")
        ev["S2_armed"] = {"job": job_id, "form": "file_links", "link": str(link)}
        _flush(ev, case, "S2")

        # ---- S3 误拦2探针(armed, qB 在线, D16 登记存续期): 组外异名带文件删除放行
        before_issued = M.log_text(case).count("迁移发起")
        result_d = M.cmd_post_and_wait(web_port, f"/api/torrents/{hx2}/delete", {"delete_files": True})
        assert (result_d or {}).get("status") == "ok", \
            f"误拦2复发: 组外异名带文件删除被拒: {json.dumps(result_d, ensure_ascii=False)[:500]}"
        M.wait_until(lambda: qb.torrent(hx2) is None, 30, "删除回执 ok 但 qB 仍有 X2")
        M.wait_until(lambda: not (SRC / OUTSIDER2_NAME).exists() or None, 30, "删除后 X2 实文件残留(磁盘清净失守)")
        for h in (h1, h2):
            _assert_healthy(qb, h, "成员(删除扰动面)")
        assert M.reparse_kind(link) == "symlink", f"删除探针扰动别名: {link}"
        assert (SRC / OUTSIDER1_NAME).is_file(), "删除探针扰动 X1 实文件"
        assert M.log_text(case).count("迁移发起") == before_issued, "删除探针引发计划外「迁移发起」"
        ev["S3_misfire2_gone"] = {"status": (result_d or {}).get("status"), "file_gone": True, "alias_kept": True}
        _flush(ev, case, "S3")

        # ---- S4 下线窗: 双实例优雅下线 -> daemon 改写非 mover settled -> 开窗观测面双押(单断)
        wl1 = len(wrapper_lines())
        patched = _await_wrapper_patched(wl0, case)
        comp_before = {h: (qb.torrent(h) or {}).get("completion_on") for h in (h1, h2)}
        assert all(v is not None for v in comp_before.values()), f"completion_on 取不到: {comp_before}"
        qb_down(instances.SECONDARY)
        qb_down(instances.PRIMARY)
        ev["S4_down"] = {"wl1": wl1, "patched": patched[-1]}
        _flush(ev, case, "S4a")

        def rewrite_settled():
            jr = M.journal_of(case, job_id) or {}
            rws = jr.get("rewrites") or {}
            if rws and all(
                ((rws.get(h) or {}).get("status")) in ("rewritten", "already", "unmatched") for h in (h1, h2)
            ) and jr.get("phase") == "rewritten":
                return jr
            return None

        jr = M.wait_until(rewrite_settled, 300, f"daemon 未在下线窗完成改写(job={job_id})")
        rws = jr.get("rewrites") or {}
        ev["S4_rewrites_raw"] = json.dumps(rws, ensure_ascii=False, default=str)[:2000]  # 先落全量账再断言(FAIL 二分留现场)
        _flush(ev, case, "S4raw")

        # mover 面以产品账为准(产品自选 mover, 不必等于发起 hash —— 首跑实锤: 发起 7b550963
        # 而产品选 4ae6adba 做 mover; mover 的 fastresume 在 qB 优雅下线时已写 dst = already 合法)。
        # 取数走产品详情端点(state.json 30S 落盘周期追不上, 二跑实锤: jobs_on_disk 此刻无账)
        def mover_of():
            d1 = ((M.member_detail(web_port, h1) or {}).get("relocate") or {})
            if d1.get("job_id") == job_id and d1.get("mover") is not None:
                return h1 if d1.get("mover") is True else h2
            return None

        mover_hash = M.wait_until(mover_of, 30, "产品详情端点未回 relocate 面(mover 判定不可得)")
        assert mover_hash in (h1, h2), f"账面 mover 不在本组: {mover_hash[:8]}"
        non_mover = h2 if mover_hash == h1 else h1
        assert (rws.get(non_mover) or {}).get("status") == "rewritten", \
            f"非 mover({non_mover[:8]})改写账 status={(rws.get(non_mover) or {}).get('status')} != rewritten"
        assert (rws.get(mover_hash) or {}).get("status") in ("already", "rewritten"), \
            f"mover({mover_hash[:8]})改写账异常: {(rws.get(mover_hash) or {}).get('status')}"
        wnew = wrapper_lines()[wl1:]
        l1_face, obs_owner = window_regime_face(case, wnew)  # 双押单断(细节归 RM04-21 B4, 切分见 docstring)
        ev["S4_rewrite"] = {
            "mover": mover_hash[:8],
            "mover_status": (rws.get(mover_hash) or {}).get("status"),
            "non_mover": non_mover[:8],
            "non_mover_status": (rws.get(non_mover) or {}).get("status"),
            "window_regime": {
                "l1_face": l1_face,
                "obs_owner_pid_alive": (obs_owner or {}).get("pid_alive")
            }
        }
        _flush(ev, case, "S4b")

        # ---- S5 误拦1探针(下线窗内: qB 下线、产品在位; precheck_add 纯本地判定零 qB 调用)
        pre = M.cmd_post_and_wait(
            web_port, "/api/relocate/precheck-add", {
                "save_path": str(SRC),
                "name": OUTSIDER1_NAME
            }
        )
        truth = (pre or {}).get("truth") or pre or {}
        assert truth.get("cls") == "ok", \
            f"误拦1复发: 异名添加预检非 ok: {json.dumps(pre, ensure_ascii=False)[:500]}"
        reasons = truth.get("reasons") or []
        assert not [r for r in reasons if (r or {}).get("gate") == "finalize_window"], \
            f"误拦1复发: finalize_window confirm 命中: {reasons}"
        ev["S5_misfire1_gone"] = {"cls": truth.get("cls"), "reasons": reasons}
        _flush(ev, case, "S5")

        # ---- S6 重启: 双成员落 dst(零 recheck 零异常) + X1 在场且健康
        qb_up(instances.SECONDARY)
        qb_up(instances.PRIMARY)

        def all_at_dst():
            cur = {t["hash"]: t for t in qb.torrents()}
            if all(M.norm((cur.get(h) or {}).get("save_path") or "") == M.norm(str(dst)) for h in (h1, h2)):
                return {h: cur[h]["save_path"] for h in (h1, h2)}
            return None

        sps = M.wait_until(
            all_at_dst, 120, lambda: f"重启后未全员落位 dst: "
            f"{ {h: (qb.torrent(h) or {}).get('save_path') for h in (h1, h2)} }"
        )
        for h in (h1, h2):
            _assert_healthy(qb, h, "成员")
        comp_after = {h: (qb.torrent(h) or {}).get("completion_on") for h in (h1, h2)}
        assert comp_after == comp_before, (
            "completion_on 变化 = qB 载入后对成员做过全量 recheck(改写链不该引发): "
            f"before={comp_before} after={comp_after}"
        )
        tx = _assert_healthy(qb, hx1, "组外异名 X1")
        assert M.norm(tx.get("save_path") or "") == M.norm(SRC), f"X1 落点被扰动: {tx.get('save_path')}"
        assert (SRC / OUTSIDER1_NAME).is_file(), "X1 实文件被扰动(在场健康面失守)"
        ev["S6_restart"] = {"save_paths": sps, "outsider_state": tx.get("state")}
        _flush(ev, case, "S6")

        # ---- S7 零人工干预收敛: S6 后零测试动作 -> 收尾完成 -> done/finalized -> 别名删净 -> 组归一
        M.wait_until(lambda: True if "收尾完成" in M.log_text(case) else None, 180, "收尾完成行未出现(需人工干预才收敛?)")
        fin_line = [ln for ln in M.log_text(case).splitlines() if "收尾完成" in ln][-1]
        assert "删链门依赖清零" in fin_line and "已在线删除别名" in fin_line, f"收尾行语义不符: {fin_line}"
        fjob = M.wait_job_phase(case, job_id, {"done", "failed"}, 180, "job 未收敛")
        assert fjob.get("phase") == ru.PHASE_DONE and fjob.get("reason") == ru.REASON_FINALIZED, \
            f"job 终态非 done/finalized: {fjob.get('phase')}/{fjob.get('reason')}"
        M.wait_until(lambda: True if not os.path.lexists(str(link)) else None, 60, "收尾后 symlink 未删除")
        g2 = M.wait_group(web_port, h1, {h1, h2}, 60, "组未归一(两颗不同组 = 裂组)")
        k2 = M.decode_key(g2["key"])
        assert M.norm(k2[0]) == M.norm(str(dst)), f"终态组键首元不是 dst: {k2[0]}"
        for h in (h1, h2):
            _assert_healthy(qb, h, "收敛后成员")
        tx2 = _assert_healthy(qb, hx1, "收敛后 X1")
        assert M.norm(tx2.get("save_path") or "") == M.norm(SRC), f"收敛后 X1 落点被扰: {tx2.get('save_path')}"
        ev["S7_converged"] = {"phase": fjob.get("phase"), "reason": fjob.get("reason"), "log": fin_line}
        _flush(ev, case, "S7")

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
            my_hashes = [h for h in (h1, h2, hx1, hx2) if h]
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
