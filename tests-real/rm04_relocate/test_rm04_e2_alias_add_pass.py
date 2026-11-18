"""

同源声明: _write_cfg_fast_tick/_flush/_await_wrapper_patched 与
test_rm04_e9_selfheal_nomisfire.py / test_rm04_offline_delete_settle.py 同源(函数体逐字一致,
docstring/证据文件名前缀按用例本地化), 单侧改动须同步另两文件(评审 R23 纪律);
_assert_healthy 仅与 test_rm04_e9_selfheal_nomisfire.py 同源(offline 文件无此 helper,
评审 R26 指向面收窄);
_readlink_norm 与 test_rm04_chain_gate_candidates.py 同源。
[RM04-28] [E2] 异名添加放行 + 全链路成立: FILE_LINKS 组迁移 armed 后, 组外异名种子(落旧根)
添加 → 添加预检 ok 零弹窗(误拦1不复现, E1 并入腿); 立即收尾/重启两态 → 改写 → 核验 → 删链门
(豁免生效, 组外异名在场而依赖计数不含它)→ 收尾 done; 新种子照常做种、账面 1.00、零 recheck、
零拒载。

计划 plans/26-11-17-0636-plan-real-rm04-relocate-refactor-verify.html §03.4 RM04-28 用例卡
(E2; E1 误拦1修正面并入: 组外异名添加曾弹 finalize_window confirm, R4 放行扩张修复 ——
relocate_units.evaluate_add 文件级分支 (3)「异名静默放行」单点; 卡面「误拦1」在 E9/docstring
中即异名添加零弹窗)。

「立即收尾/重启两态」口径(卡面 → 盘面落刀): D14「立即收尾」(POST /api/relocate/finalize-now
显式确认 → 产品对配置 qB 即副实例下发 app/shutdown → 回收 daemon 捕窗改写 → 用户手动重启)
与重启后的收尾链是收尾窗的两态; 本用例全链 = armed 异名添加(armed 态预检探针 + 真添加) →
立即收尾(真端点, 不以 qb_down 代打) → 下线窗改写(副实例由产品关闭, 主实例测试侧 real.down
补齐 —— wrapper 实例级名册含双测试镜像, 只关副实例名册不空不开窗, RM04-20/21/27/34 同款
盘面) → rewritten 态预检复探(重启态误拦1腿) → 重启 → 核验(落位 dst/零 recheck/零拒载) →
删链门豁免(X1 在场依赖清零) → 收尾 done。离线窗恰一次(重启态), 与卡面副作用一致。

窗口期纪律(片D 切片 26-11-18-2308 §06 坑点1 对本用例的落点): 收敛链消费别名发生在重启落位
后 1-2 拍, 重启后再布探针必静默扑空 —— 本用例两类探针(armed 态 S3 / rewritten 态 S5)都在
D16 登记存续期内执行; S6 重启后零测试动作只等收敛, 不再布探针。

## 测试计划(单测试函数, 七段)
- G0 开工闸: R: 拓扑在 + 双实例在线(connection_status 非 disconnected) + 副实例无
  real-fake 残留; 产品起(旁路 runner, fast tick, 阈值 8)。
- S1 造现场: 双成员共享文件组(file_links)落 R: → 齐完成 → 归组断言(成员组恰含双成员)。
- S2 搬迁 armed: WEB 迁移(confirm 直投 → started form=file_links + job_id)→ 已武装收尾
  → symlink 现场(指 dst)。
- S3 armed 态异名添加(误拦1探针 + 真添加): precheck-add {save_path=旧根, name=组外异名}
  → cls=ok 零 confirm/零 finalize_window(误拦1不复现)→ 真添加组外异名种子 X1(带数据落旧根)
  → 完成 → 健康(账面 1.00 做种) + 不入成员组 + 实文件在盘 + 零计划外「迁移发起」+ job 仍
  armed(账面零扰动)。
- S4 立即收尾(D14 finalize-now): wrapper patch 在位 → completion_on 基线 + X1 fastresume
  路径键基线 → POST /api/relocate/finalize-now {confirm: true, job_id} → cls=ok(关闭指令
  已下达)→ 副实例端口关闭(产品发起的优雅退出)→ 主实例 real.down 补齐(实例级名册空才开窗)
  → daemon 改写 settled(journal phase=rewritten; mover 面按产品账判定 —— 产品自选 mover 不必
  等于发起 hash, RM04-34 三跑实锤)+ 改写账恰成员两键(daemon 未触组外种子, 账面)+ 开窗观测面
  双押(单断)。
- S5 rewritten 态预检复探(重启态误拦1腿): precheck-add 复探 → cls=ok 零 finalize_window。
- S6 重启 + 核验: 双实例回在线 → 成员落 dst(completion_on 等值 = 零 recheck, 异常态零)→
  X1 在场健康(做种 stalledUP/账面 1.00/落点未动 = 零拒载)+ X1 completion_on 等值(零
  recheck)+ X1 fastresume 路径键改写前后等值(daemon 未触组外种子, 字面)。
- S7 收尾 done + 删链门豁免: S6 后零测试动作 → 「收尾完成」行(删链门依赖清零 + 已在线删除
  别名; X1 在场仍清零 = 豁免生效, 组外异名在场而依赖计数不含它)→ job done/finalized →
  symlink 删除 → 组键归一 dst → 成员/X1 健康。
- Z 收尾: 产品优雅退出 → real-fake 删净(连数据)→ BT_backup 本用例哈希残留清除 + 逐文件
  比对开工快照 → case 树与 R: 子树删净 + 别名 lstat 零残留。

前置: 环境1(R: 在, src=R:/qbt-fake/rm04/rm04_28/src 与 dst=D: 异盘) + 双测试实例在线
      (没起先 `commands run real.up -- --port <白名单端口>`); 副实例无 real-fake 残留;
      wrapper 名册窄化旁路在位(沿 RM04-20/21/27/34 授权, 零新增旁路面); 独占约 3-4 分钟,
      conftest serial 锁串行保护。R: 缺席 => skip 不回退落点(钉死口径)。
副作用: 一次真搬迁(mover 被 qB 原生搬 R:->D:)+ 一次下线窗改写(非 mover fastresume 被
      daemon 改写; 副实例下线由 D14 finalize-now 产品发起, 主实例由测试侧 real.down)+
      双实例优雅下线/重启各一次 + 组外异名种子添加一次(带数据落旧根) + state 账。
回滚: 产品优雅退出(sentinel 通路); 双实例恢复在线; real-fake 种子删净(连数据); BT_backup
      只清本用例哈希残留 + 逐文件比对开工快照(queue 豁免); case 树与 R:/qbt-fake/rm04/rm04_28
      子树删净(purge_tree 不递归删穿链接); 别名 lstat 零残留。
失败判据: 异名添加预检回 confirm/弹窗(误拦1复发, armed 或 rewritten 任一态); finalize-now
      回执非 ok(关闭指令未下达, D14 降级面); 改写未完成或改写账出现组外 hash 或组外种子
      fastresume 被触; 重启后成员未落位/recheck/异常态; X1 被拒载/recheck/落点被扰; 收尾未
      done(删链门把组外异名计入依赖 = 豁免失守,「收尾完成」行缺席)或别名残留; 收尾有残留。

跑法: `commands run real.run -- --case RM04-28 --yes`(不要裸 pytest)。
"""
from __future__ import annotations

import json
import os
import socket
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_rm04_relocate as M  # noqa: E402  (复用 RM04 的造种/清场/断言助手)
import test_rm04_relocate_window as W  # noqa: E402  (RM04-20/21/27/34 同款旁路接线/收尾 helper, 授权见其 docstring)

from lib import app, guard, instances  # noqa: E402
from auto_qb.core.modules import relocate_units as ru  # noqa: E402  (产品码: 相位/原因常量)

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="本片断言含 Windows 特有语义(symlink/优雅退出通路)"),
]

# 拓扑单点(钉死, 见模块 docstring; 与 RM04-20/21/22/23/25/26/27/34 的子树隔离): src 在 R: 内存盘
R_ROOT = Path("R:/qbt-fake/rm04")
SRC = R_ROOT / "rm04_28" / "src"
FILE_NAME = "rm04c28.bin"
OUTSIDER_NAME = "rm04c28x.bin"  # 组外异名 X1: armed 后添加(落旧根), 全程在场贯穿改写/收尾(豁免面对象)
FILE_SIZE = 1024 * 1024
OUTSIDER_SIZE = 256 * 1024
PIECE_LENS = (16384, 32768)  # 同文件异 infohash 的区分面(两颗成员)
SALT = "rm04c28"

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
fr_path_keys = W.fr_path_keys
BT_BACKUP = W.BT_BACKUP

# 片E 证据目录(任务口径: 逐案 evidence 落 tests-real/.work/rm04-sliceE/; 时刻后缀防覆写)
SLICE_EV = HERE.parent / ".work" / "rm04-sliceE"


def _flush(ev: dict, case: Path, tag: str) -> None:
    """证据落盘(gitignored .work/rm04-sliceE): 全量断言现场 + 产品日志副本, 时刻后缀防覆写。"""
    ev["ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
    SLICE_EV.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    (SLICE_EV / f"rm04_28_{tag}_evidence_{stamp}.json"
    ).write_text(json.dumps(ev, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    try:
        log = M.log_text(case)
    except Exception as e:  # noqa: BLE001 —— 取证失败如实带错, 不掩盖主断言
        log = f"<log read failed: {e!r}>"
    (SLICE_EV / f"rm04_28_{tag}_auto-qb_{stamp}.log").write_text(log, encoding="utf-8")


def _write_cfg_fast_tick(case: Path) -> tuple[Path, int]:
    """RM04-28 专用配置: 在 M.write_cfg 基础上把 main_tick 2S -> 1S(片C 沉淀派生)。

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


def _port_open(port: int) -> bool:
    """TCP 端口探针(只测本机白名单端口; finalize-now 产品侧下线的关闭完成观测面)。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", int(port))) == 0


def _readlink_norm(p: Path) -> str:
    """junction/symlink 目标原始读出(归一成 / 形 + 剥设备前缀; RM04-22 同款, 与
    test_rm04_chain_gate_candidates.py 同源)。"""
    s = M.norm(os.readlink(str(p)))
    if s.startswith("//?/UNC/"):
        return "//" + s[len("//?/UNC/"):]
    if s.startswith("//?/"):
        return s[len("//?/"):]
    return s


# ================================================================ RM04-28


def test_rm04_28_e2_alias_add_pass():
    """[RM04-28] E2 异名添加放行 + 全链路成立(七段 S1-S7+Z, 断言明细见模块 docstring)

    前置: R: 在 + 双实例在线 + 副实例无 real-fake 残留; wrapper 收编入库版在位。
    副作用/回滚/失败判据: 见模块 docstring(四行契约)。
    """
    _require_r_topology()
    case = M.case_dir("rm04_28")
    stop_lingering_product(case)
    qb = M.qbfake()
    assert not M.rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
    assert BT_BACKUP.is_dir(), f"副实例 BT_backup 不在(env_registry EXE 派生路径失效?): {BT_BACKUP}"
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
    wl0 = len(wrapper_lines())
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

        # ---- S3 armed 态异名添加(误拦1探针 + 真添加; D16 登记存续期, qB 在线)
        before_issued = M.log_text(case).count("迁移发起")
        pre = M.cmd_post_and_wait(
            web_port, "/api/relocate/precheck-add", {
                "save_path": str(SRC),
                "name": OUTSIDER_NAME
            }
        )
        truth = (pre or {}).get("truth") or pre or {}
        assert truth.get("cls") == "ok", \
            f"误拦1复发(armed 态): 组外异名添加预检非 ok: {json.dumps(pre, ensure_ascii=False)[:500]}"
        reasons = truth.get("reasons") or []
        assert not [r for r in reasons if (r or {}).get("gate") == "finalize_window"], \
            f"误拦1复发(armed 态): finalize_window confirm 命中: {reasons}"
        hx = M.fake_with_data(qb, OUTSIDER_NAME, OUTSIDER_SIZE, SRC, "rm04c28x", piece_len=16384, write=True)
        M.wait_complete(qb, [hx], 120)
        tx = _assert_healthy(qb, hx, "组外异名 X1(添加后)")
        gx = M.group_row(M.groups_view(web_port), hx)
        assert gx is None or set(gx["members"]) == {hx}, f"组外异名 X1 被误归入他组: {gx}"
        assert (SRC / OUTSIDER_NAME).is_file(), "X1 实文件未落盘"
        assert M.norm(tx.get("save_path") or "") == M.norm(SRC), f"X1 落点异常(应为旧根): {tx.get('save_path')}"
        # 账面零扰动观测面 = 成员详情 relocate 相位(产品快照内存值, 实时) —— journal 此刻
        # 尚无文件(它由 daemon 在下线窗写, armed 期 journal_of 恒 None, 首跑实锤的测试侧锚错)
        jrow = M.wait_until(
            lambda: ((M.member_detail(web_port, h1) or {}).get("relocate") or {}).get("phase") == "armed" or None, 30,
            lambda: f"armed 账相位异常/未落: "
            f"{((M.member_detail(web_port, h1) or {}).get('relocate') or {}).get('phase')}"
        )
        assert M.log_text(case).count("迁移发起") == before_issued, "异名添加引发计划外「迁移发起」"
        ev["S3_alias_add_pass"] = {
            "cls": truth.get("cls"),
            "reasons": reasons,
            "outsider": hx[:8],
            "outsider_state": tx.get("state"),
            "job_phase": jrow
        }
        _flush(ev, case, "S3")

        # ---- S4 立即收尾(D14 finalize-now): 产品对配置 qB(副实例)下发 app/shutdown
        wl1 = len(wrapper_lines())
        patched = _await_wrapper_patched(wl0, case)
        comp_before = {h: (qb.torrent(h) or {}).get("completion_on") for h in (h1, h2, hx)}
        assert all(v is not None for v in comp_before.values()), f"completion_on 取不到: {comp_before}"
        M.wait_until(
            lambda: True
            if W.frmod.locate_fastresume(BT_BACKUP, hx) else None, 30, f"X1 fastresume 未落 BT_backup(基线取不到): {BT_BACKUP}"
        )
        frx_before = fr_path_keys(hx)
        result_fn = M.cmd_post_and_wait(web_port, "/api/relocate/finalize-now", {"confirm": True, "job_id": job_id})
        assert (result_fn or {}).get("cls") == "ok", \
            f"finalize-now 回执非 ok(关闭指令未下达): {json.dumps(result_fn, ensure_ascii=False)[:500]}"
        assert "关闭指令" in str((result_fn or {}).get("note") or ""), \
            f"finalize-now note 语义不符: {(result_fn or {}).get('note')}"
        ev["S4_finalize_now"] = {
            "cls": (result_fn or {}).get("cls"),
            "note": (result_fn or {}).get("note"),
            "patched": patched[-1]
        }
        _flush(ev, case, "S4a")
        # 副实例优雅退出(产品发起; qB 自写 fastresume 再退 = real.down 同一优雅语义面);
        # 主实例测试侧 real.down 补齐 —— wrapper 实例级名册含双测试镜像, 只关副实例名册不空不开窗
        M.wait_until(
            lambda: None
            if _port_open(instances.SECONDARY) else True, 60, "finalize-now 后副实例端口未关闭(产品未真正下发 app/shutdown?)"
        )
        qb_down(instances.PRIMARY)
        ev["S4_down"] = {"secondary_down": "by finalize-now(product)", "primary_down": "test-side real.down"}
        _flush(ev, case, "S4b")

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

        # mover 面以产品账为准(产品自选 mover, 不必等于发起 hash —— RM04-34 三跑实锤)
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
        assert set(rws) == {h1, h2}, f"改写账出现组外 hash(daemon 未触组外种子失守): {set(rws)}"
        wnew = wrapper_lines()[wl1:]
        l1_face, obs_owner = window_regime_face(case, wnew)  # 双押单断(细节归 RM04-21 B4, 切分见 docstring)
        ev["S4_rewrite"] = {
            "mover": mover_hash[:8],
            "mover_status": (rws.get(mover_hash) or {}).get("status"),
            "non_mover": non_mover[:8],
            "non_mover_status": (rws.get(non_mover) or {}).get("status"),
            "rewrite_keys": sorted(h[:8] for h in rws),
            "window_regime": {
                "l1_face": l1_face,
                "obs_owner_pid_alive": (obs_owner or {}).get("pid_alive")
            }
        }
        _flush(ev, case, "S4c")

        # ---- S5 rewritten 态预检复探(重启态误拦1腿; precheck_add 纯本地判定零 qB 调用)
        # 相位前置(R26 修复后重跑二分修正): 「rewritten 态」= journal/daemon 改写已落盘 ——
        # 账面镜像在下线窗恒 armed(D13 合并只在主循环 _step_reconcile; qB 离线 = 主循环断连
        # 稳态不跑任务线), 重启后合并与 VERIFY 同拍(毫秒级瞬态), 账面 rewritten 对轮询不可
        # 观测 —— 等账面 rewritten 结构性不可满足, 等待目标改锚 journal 相位(RM04-28 S4
        # rewrite_settled 同一取数面); 账面实况由 probe_phase/journal_phase 双记如实留证
        M.wait_until(
            lambda: (M.journal_of(case, job_id) or {}).get("phase") == "rewritten" or None,
            15, "journal 相位未达 rewritten(daemon 改写未落盘, S5 探针会跑在改写前态)"
        )
        pre2 = M.cmd_post_and_wait(
            web_port, "/api/relocate/precheck-add", {
                "save_path": str(SRC),
                "name": OUTSIDER_NAME
            },
            timeout=90,  # 下线窗主循环被 connect() 阻塞(urllib3 重试预算 ~29s/次), 命令线
            # 只在轮顶跑 —— 回执延迟上界 ≈ 一次在途 connect(~29s)+下一轮, 原 pass1 实测
            # 24.5s 贴着 30s 默认窗险过; 90s = 3x 裕量(二分: pass1b 回执差 ~1s 未落超时红)
        )
        truth2 = (pre2 or {}).get("truth") or pre2 or {}
        assert truth2.get("cls") == "ok", \
            f"误拦1复发(rewritten 态): 异名添加预检非 ok: {json.dumps(pre2, ensure_ascii=False)[:500]}"
        reasons2 = truth2.get("reasons") or []
        assert not [r for r in reasons2 if (r or {}).get("gate") == "finalize_window"], \
            f"误拦1复发(rewritten 态): finalize_window confirm 命中: {reasons2}"
        ev["S5_precheck_rewritten"] = {
            "cls": truth2.get("cls"),
            "reasons": reasons2,
            "probe_phase": ((M.member_detail(web_port, h1) or {}).get("relocate") or {}).get("phase"),
            "journal_phase": (M.journal_of(case, job_id) or {}).get("phase")
        }
        _flush(ev, case, "S5")

        # ---- S6 重启: 成员落 dst(零 recheck 零异常) + X1 在场健康(零拒载/零 recheck)
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
        comp_after = {h: (qb.torrent(h) or {}).get("completion_on") for h in (h1, h2, hx)}
        assert comp_after == comp_before, (
            "completion_on 变化 = qB 载入后做过全量 recheck(改写链不该引发): "
            f"before={comp_before} after={comp_after}"
        )
        tx = _assert_healthy(qb, hx, "组外异名 X1")
        assert M.norm(tx.get("save_path") or "") == M.norm(SRC), f"X1 落点被扰动: {tx.get('save_path')}"
        assert (SRC / OUTSIDER_NAME).is_file(), "X1 实文件被扰动(零拒载面失守)"
        frx_after = fr_path_keys(hx)
        assert frx_after == frx_before, f"组外种子 fastresume 被改写触碰(零拒载面失守): {frx_before} -> {frx_after}"
        ev["S6_restart"] = {
            "save_paths": sps,
            "outsider_state": tx.get("state"),
            "outsider_save_path": tx.get("save_path"),
            "fr_keys_unchanged": True
        }
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
        tx2 = _assert_healthy(qb, hx, "收敛后 X1")
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
            my_hashes = [h for h in (h1, h2, hx) if h]
            for ih in my_hashes:
                for suffix in (".fastresume", ".torrent", ".fastresume.bak", ".torrent.bak"):
                    fp = BT_BACKUP / f"{ih}{suffix}"
                    if fp.is_file():
                        fp.unlink()
                        removed.append(fp.name)
            now = bt_backup_snapshot()
            residue = [k for k in now if k not in snap_before and not any(k.startswith(ih) for ih in my_hashes)]
            before_files = {k: v for k, v in snap_before.items() if (BT_BACKUP / k).is_file() and k != "queue"}
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
