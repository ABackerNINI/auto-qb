"""
[RM04-33] [E8] 不可判定保守回归: 注入清单取数失败 -> 删链门计依赖 + D16 照旧拦(宁拦勿漏), 负向对照内建。

同源声明: _write_cfg_fast_tick/_assert_healthy/_readlink_norm 复用
test_rm04_e2_alias_add_pass.py(E2 单侧实现, 本文件 import 复用零拷贝);
qb_up/bt_backup_snapshot/BT_BACKUP/BypassApp/_require_r_topology/stop_lingering_product 复用
test_rm04_relocate_window.py(W 单点); 造种/清场/断言助手复用 test_rm04_relocate.py(M 单点)。
_runners 同源声明: _RUNNER_BYPASS_E8 = W._RUNNER_BYPASS 逐字派生(旁路授权先例沿
test_rm04_e4_outsider_delete.py 模块 docstring: RM04-20/21/27/34), 单侧差异三处且仅三处 ——
a) 增加对 auto_qb.torrents.record.TorrentRecord.files 的进程内注入包装(对 TRIGGER 文件指名的
   hash raise, 其余 hash 与无 trigger 时逐字走原实现; raise 落在门级消费方 relocate_plan.
   PlanMixin._file_map / qbapi._relocate_file_names 各自 try/except 之内, 产品「清单不可得 ->
   保守」分支原码消费 —— 用例卡 P4 定稿形态);
b) patch 装配后写 MARKER 文件(用例侧断言注入面在位的确定性证据);
c) runner 文件名/占位符本地化(__WRAP__/__TRIGGER__/__MARKER__, 原 {wrap} 同款 replace 装配)。
daemon 旁路与 sentinel 优雅退出通路与 W 逐字一致, 零新增旁路面。

计划 plans/26-11-17-0636-plan-real-rm04-relocate-refactor-verify.html §03.4 RM04-33 用例卡
(L3, 新建即 L3: 保守两门 = 负向对照内建): armed 组在场, 进程内对注入 hash 的
TorrentRecord.files raise -> 断言: (1) 删链门计依赖(宁拦勿漏, 不豁免不误删); (2) D16 删种
拦截照旧拦; (3) 产品不崩、日志有保守留痕。负向对照内建 = 取数成功时正常放行: X0(取数成功)
带文件删除当场放行 vs X1(注入)同位置删除被拒 —— 同拓扑同判据只差取数可得性, 保守分支因果
钉死; X2(取数成功)在删链门悬挂期同位置在场而不被计依赖(依赖计数恰 1 不膨胀)。

切分: 与 RM04-25 C 腿(同名真依赖)机制不同(清单不可得 vs 依赖存在); 与 RM04-28/29(异名豁免)
互补(豁免要求清单可得)。

## 测试计划(单测试函数, S1-S5+Z 六段)
- S1 造现场 + 注入面在位: 产品起(E8 旁路 runner, fast tick 1S, MARKER 落盘即注入面装配证据)
  -> FILE_LINKS 双成员共享文件组(R:/qbt-fake/rm04/rm04_33/src)完成/归组 -> 搬迁 armed
  (form=file_links + job_id) -> 已武装收尾 + symlink 指 dst + 成员详情 relocate 相位 armed。
- S2 组外异名三枚(带数据落旧根, 与成员零文件交集): X0/D16 负向对照、X1/注入目标、
  X2/删链门负向对照 -> 各自健康(1.0 做种)+ 不入成员组 + 实文件在盘 + 落点=旧根。
- S3 D16 两门对照(注入激活: TRIGGER 写入 X1 hash):
  负向对照 X0 带文件删除回执 ok(取数成功 -> 交集不相交 -> 豁免放行, qB 无 X0 + 实文件清净);
  正向 X1 带文件删除回执 error(D16 照旧拦, 清单不可得 -> 不豁免) + qB 仍有 X1 + 实文件原样
  + 日志增「D16 交集判据取文件清单失败」WARNING(带 X1 hash)+ 产品存活 + WEB 可响应。
- S4 删链门保守(注入保持): 删光成员(仅删种子, qB 直删不经产品)-> 收缩(R4, 1S 拍)-> 空集
  核验顺 VERIFY -> 删链门: X1 取数失败 -> file_alias_intersects None -> 保守计依赖, 日志
  「删链门依赖未清(1 个)」(恰 1: X2 同位置取数成功不被计, 负向对照内建)+ 磁盘账
  reason=chain_deps + last_error 带 X1 样例 + symlink 原样指 dst + X1 文件/种子原样(不误删)
  + 日志增「读取文件列表失败」WARNING(带 X1 hash 前缀)+ 产品存活。
- S5 注入解除 -> 依赖清零收敛(负向对照完成): 删 TRIGGER -> X1 带文件删除回执 ok(取数成功
  -> 豁免放行, X1 实文件清净)-> 「收尾完成(删链门依赖清零, 已在线删除别名)」-> 磁盘账
  done/finalized + symlink 删除 + X2 存活到终态零扰动(健康 + 实文件在盘 + 落点=旧根)。
- Z 收尾: 产品优雅退出 -> real-fake 删净(连数据)-> BT_backup 本用例哈希残留清除 + 开工快照
  逐文件比对 -> case 树与 R: 子树删净 + symlink lstat 零残留。

前置: 环境1(R: 在, src=R:/qbt-fake/rm04/rm04_33/src 与 dst=D: 异盘) + 双测试实例在线
      (没起先 `commands run real.up -- --port <白名单端口>`); 副实例无 real-fake 残留;
      进程内旁路启动(E8 注入沿用例卡 P4 定稿形态 + RM04-20/21 start_bypass_app 先例,
      零新增旁路面); 独占约 3-4 分钟, conftest serial 锁串行保护。R: 缺席 => skip 不回退。
副作用: armed 组 + 注入 hash 的 raise(用例进程内, 不落盘; TRIGGER/MARKER 在 case 树随清理)
      + 组外种子带文件删除三次(S3 X0/S4 无/S5 X1)+ state 账。
回滚: 产品优雅退出(sentinel 通路); 双实例保持在线; real-fake 种子删净(连数据, X0/X1 已在
      S3/S5 删除, X2 由 rm_all_fakes 删); BT_backup 只清本用例哈希残留 + 逐文件比对开工快照
      (queue 豁免); case 树与 R:/qbt-fake/rm04/rm04_33 子树删净(purge_tree 不递归删穿链接);
      symlink lstat 零残留。
失败判据: 取数失败被当「无依赖」豁免(删链门放行/误删链接 = 宁拦勿漏失守); D16 失守放行;
      产品崩或 raise 逃逸到顶层(无保守留痕/进程死); X2 同位置被误计依赖(负向对照红);
      收敛需人工干预; 收尾有残留。

跑法: `commands run real.run -- --case RM04-33 --yes`(不要裸 pytest)。
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
import test_rm04_relocate_window as W  # noqa: E402  (旁路接线/收尾 helper, 授权见其 docstring)
import test_rm04_e2_alias_add_pass as E2  # noqa: E402  (同源 helper 复用, 见模块 docstring)

from lib import guard, instances  # noqa: E402
from auto_qb.core.modules import relocate_units as ru  # noqa: E402  (产品码: 相位/原因常量)

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="本片断言含 Windows 特有语义(symlink/优雅退出通路)"),
]

# 拓扑单点(钉死, 与 E2 同构; 子树隔离): src 在 R: 内存盘
R_ROOT = Path("R:/qbt-fake/rm04")
SRC = R_ROOT / "rm04_33" / "src"
FILE_NAME = "rm04c33.bin"
FILE_SIZE = 1024 * 1024
PIECE_LENS = (16384, 32768)  # 同文件异 infohash 的区分面(两颗成员)
SALT = "rm04c33"
# 组外异名三枚(带数据落旧根; 名/量各异 -> 各自单例组, 与成员零文件交集)
X0_NAME, X0_SIZE = "rm04c33x0.bin", 128 * 1024  # S3 D16 负向对照(取数成功放行, 删)
X1_NAME, X1_SIZE = "rm04c33x1.bin", 192 * 1024  # S3/S4 注入目标(清单不可得 -> 保守), S5 解除后删
X2_NAME, X2_SIZE = "rm04c33x2.bin", 160 * 1024  # S4/S5 删链门负向对照(取数成功不计依赖, 存活到终态)

# 保守留痕锚(产品「清单不可得 -> 保守」分支的日志面, 单点见源码 docstring)
WARN_D16 = "D16 交集判据取文件清单失败"  # qbapi._relocate_file_names except(带完整 hash)
WARN_FILEMAP = "读取文件列表失败"  # relocate_plan._file_map except(log_repr 带 hash 前 8 位)
GATE_LINE = "删链门依赖未清"  # relocate_exec._step_verify logger.info
FIN_LINE = "收尾完成"  # relocate_exec._finalize_verified logger.info

# 复用单点(不另抄一份)
_require_r_topology = W._require_r_topology
stop_lingering_product = W.stop_lingering_product
qb_up = W.qb_up
bt_backup_snapshot = W.bt_backup_snapshot
_write_cfg_fast_tick = E2._write_cfg_fast_tick
_assert_healthy = E2._assert_healthy
_readlink_norm = E2._readlink_norm
BypassApp = W.BypassApp
BT_BACKUP = W.BT_BACKUP

# 片G 证据目录(任务口径: 逐案 evidence 落 tests-real/.work/rm04-sliceG/; 时刻+遍次后缀防覆写)
SLICE_EV = HERE.parent / ".work" / "rm04-sliceG"


def _pass() -> str:
    return os.environ.get("RM04G_PASS", "0")


def _flush(ev: dict, case: Path, tag: str) -> None:
    """证据落盘(gitignored .work/rm04-sliceG): 全量断言现场 + 产品日志副本, 时刻+遍次后缀防覆写。"""
    ev["pass"] = _pass()
    ev["ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
    SLICE_EV.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    (SLICE_EV / f"rm04_33_{tag}_evidence_{stamp}.json"
    ).write_text(json.dumps(ev, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    try:
        log = M.log_text(case)
    except Exception as e:  # noqa: BLE001 —— 取证失败如实带错, 不掩盖主断言
        log = f"<log read failed: {e!r}>"
    (SLICE_EV / f"rm04_33_{tag}_auto-qb_{stamp}.log").write_text(log, encoding="utf-8")


def _warn_lines(case: Path, anchor: str, needle: str) -> list[str]:
    """带锚与 needle(如注入 hash)的产品日志行(保守留痕断言面)。"""
    return [ln for ln in M.log_text(case).splitlines() if anchor in ln and needle in ln]


# ---------------------------------------------------------------- E8 旁路 runner(W._RUNNER_BYPASS 逐字派生, 差异三处见模块 docstring 同源声明)

_RUNNER_BYPASS_E8 = '''import signal, sys, threading, time, os
WRAP = r"__WRAP__"
TRIGGER = r"__TRIGGER__"
MARKER = r"__MARKER__"
import auto_qb.core.modules.relocate_exec as rex
import auto_qb.torrents.record as _trec
_orig_popen = rex.ExecMixin._popen_detached
_orig_files = _trec.TorrentRecord.files

def _spawn_daemon_bypass(self, data_dir, host, port):
    args = [sys.executable, WRAP, "--data-dir", data_dir, "--host", str(host or ""),
            "--port", str(int(port or 0))]
    _orig_popen(args)  # detached 单点照旧(never taskkill 口径不变)

rex.ExecMixin._spawn_daemon = _spawn_daemon_bypass

def _files_e8(self, client):
    # E8 注入(RM04-33 用例卡 P4 定稿形态): 对 TRIGGER 指名 hash 的 TorrentRecord.files raise
    # —— raise 落在门级消费方(_file_map/_relocate_file_names)各自 try/except 之内, 产品
    # 「清单不可得 -> 保守」分支原码消费; 其余 hash 与无 trigger 时逐字走原实现(负向对照面)。
    try:
        with open(TRIGGER, "r", encoding="utf-8") as _f:
            _h = (_f.read() or "").strip()
    except OSError:
        _h = ""
    if _h and str(getattr(self, "hash", "")) == _h:
        raise RuntimeError("E8 inject(RM04-33): file list unavailable")
    return _orig_files(self, client)

_trec.TorrentRecord.files = _files_e8
try:
    with open(MARKER, "w", encoding="utf-8") as _mf:
        _mf.write("e8-inject-patched")
except OSError:
    pass
from auto_qb import cli
sentinel = sys.argv.pop(2)
def _watch():
    while not os.path.exists(sentinel):
        time.sleep(0.2)
    try:
        os.remove(sentinel)
    except OSError:
        pass
    signal.raise_signal(signal.SIGTERM)
threading.Thread(target=_watch, daemon=True).start()
raise SystemExit(cli.main() or 0)
'''.replace("__WRAP__", str(W.WRAP))


def start_e8_app(case: Path, cfg: Path, trigger: Path, marker: Path) -> BypassApp:
    """E8 旁路启动(W.start_bypass_app 同款进程面 + 注入 patch; 观测面/收尾全继承 BypassApp)。"""
    runner = case / "runner_sigterm_e8.py"
    runner.write_text(
        _RUNNER_BYPASS_E8.replace("__TRIGGER__", str(trigger)).replace("__MARKER__", str(marker)),
        encoding="utf-8",
    )
    sentinel = case / "stop.sentinel"
    if sentinel.exists():
        sentinel.unlink()
    import subprocess
    popen = subprocess.Popen(
        [str(W.app.PY), str(runner), str(cfg), str(sentinel)],
        cwd=str(W.REPO),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={
            **os.environ, "PYTHONIOENCODING": "utf-8"
        },
    )
    return BypassApp(popen, case, cfg, sentinel)


def _add_outsider(qb, name: str, size: int, salt: str, piece_len: int = 16384) -> str:
    """组外异名种子(带数据落旧根; 独立名/量 -> 单例组, 与成员零文件交集)。"""
    return M.fake_with_data(qb, name, size, SRC, salt, piece_len=piece_len, write=True)


def _assert_outsider_scene(qb, web_port: int, h: str, name: str, what: str) -> dict:
    """组外异名在场面: 健康 1.0 + 不入成员组 + 实文件在盘 + 落点=旧根。返回证据行。"""
    t = _assert_healthy(qb, h, what)
    gx = M.group_row(M.groups_view(web_port), h)
    assert gx is None or set(gx["members"]) == {h}, f"{what} 被误归入他组: {gx}"
    assert (SRC / name).is_file(), f"{what} 实文件未落盘: {SRC / name}"
    assert M.norm(t.get("save_path") or "") == M.norm(SRC), f"{what} 落点异常(应为旧根): {t.get('save_path')}"
    return {"hash": h, "name": name, "state": t.get("state"), "save_path": t.get("save_path")}


# ================================================================ RM04-33


def test_rm04_33_e8_undecidable_conservative():
    """[RM04-33] E8 不可判定保守回归(S1-S5+Z, 断言明细见模块 docstring 测试计划)

    前置: R: 在 + 双实例在线 + 副实例无 real-fake 残留; E8 旁路 runner 在位。
    副作用/回滚/失败判据: 见模块 docstring(四行契约)。
    """
    _require_r_topology()
    case = M.case_dir("rm04_33")
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

    trigger = case / "e8_inject.trigger"
    marker = case / "e8_inject_armed.txt"
    ev: dict = {"case": str(case), "topology": {"src": str(SRC), "dst": "case/dst", "trigger": str(trigger)}}
    p = None
    h1 = None
    h2 = None
    hx0 = None
    hx1 = None
    hx2 = None
    link = SRC / FILE_NAME  # finally 的别名零残留检查用(早退时按"建没建"如实判)
    dst = case / "dst"
    snap_before = bt_backup_snapshot()
    try:
        # ---- S1 造现场 + 注入面在位: FILE_LINKS 双成员组 armed
        M.purge_tree(SRC.parent)
        cfg, web_port = _write_cfg_fast_tick(case)
        p = start_e8_app(case, cfg, trigger, marker)
        assert p.wait_web(45), f"WEB 没起来:\n{p.log()[-800:]}"
        assert p.wait_log("整组迁移已启用", 20), f"relocate 启动日志缺失:\n{p.log()[-600:]}"
        M.wait_until(lambda: True if marker.is_file() else None, 30, f"E8 注入面装配证据(MARKER)未落盘: {marker}")
        h1 = M.fake_with_data(qb, FILE_NAME, FILE_SIZE, SRC, SALT, piece_len=PIECE_LENS[0], write=True)
        h2 = M.fake_with_data(qb, FILE_NAME, FILE_SIZE, SRC, SALT, piece_len=PIECE_LENS[1], write=False)
        assert h1 != h2, "两颗 infohash 撞车(必须同文件异 infohash)"
        M.wait_complete(qb, [h1, h2], 120)
        M.wait_group(web_port, h1, {h1, h2}, 30, "双成员组未归组")
        M.wait_store_progress(web_port, [h1, h2], 60)
        src_str = (qb.torrent(h1) or {}).get("save_path") or ""
        assert M.norm(src_str) == M.norm(SRC), f"成员 save_path 异常: {src_str}"
        result = M.cmd_post_and_wait(web_port, f"/api/torrents/{h1}/location", {"location": str(dst), "confirm": True})
        item = M.one_started_item(result)
        assert item.get("form") == "file_links", f"形态非 file_links: {json.dumps(item, ensure_ascii=False)[:400]}"
        job_id = item.get("job_id")
        assert job_id, f"started 项缺 job_id: {json.dumps(item, ensure_ascii=False)[:400]}"
        assert p.wait_log(f"job {job_id}: 已武装收尾", 60), "未武装(日志锚缺失)"
        M.wait_until(lambda: M.reparse_kind(link) == "symlink" or None, 60, lambda: f"链接形态异常: {M.reparse_kind(link)}")
        assert M.norm(_readlink_norm(link)).startswith(M.norm(dst)), f"symlink 未指 dst: {_readlink_norm(link)}"
        M.wait_until(
            lambda: ((M.member_detail(web_port, h1) or {}).get("relocate") or {}).get("phase") == "armed" or None, 30,
            lambda: f"armed 账相位未落: "
            f"{((M.member_detail(web_port, h1) or {}).get('relocate') or {}).get('phase')}"
        )
        ev["S1_armed"] = {"job": job_id, "form": "file_links", "link": str(link), "target": _readlink_norm(link)}
        _flush(ev, case, "S1")

        # ---- S2 组外异名三枚(带数据落旧根; 注入未激活, 取数全成功)
        hx0 = _add_outsider(qb, X0_NAME, X0_SIZE, "rm04c33x0")
        hx1 = _add_outsider(qb, X1_NAME, X1_SIZE, "rm04c33x1")
        hx2 = _add_outsider(qb, X2_NAME, X2_SIZE, "rm04c33x2")
        assert len({hx0, hx1, hx2}) == 3, "组外种子 infohash 撞车"
        M.wait_complete(qb, [hx0, hx1, hx2], 120)
        scene = {
            "x0": _assert_outsider_scene(qb, web_port, hx0, X0_NAME, "X0(D16 负向对照)"),
            "x1": _assert_outsider_scene(qb, web_port, hx1, X1_NAME, "X1(注入目标)"),
            "x2": _assert_outsider_scene(qb, web_port, hx2, X2_NAME, "X2(删链门负向对照)"),
        }
        ev["S2_outsiders"] = scene
        _flush(ev, case, "S2")

        # ---- S3 D16 两门对照(注入激活: TRIGGER 写入 X1 hash)
        assert p.alive(), "S3 前 product 进程已死"
        trigger.write_text(hx1, encoding="utf-8")
        d16_c0 = len(_warn_lines(case, WARN_D16, hx1))
        # 负向对照: X0 取数成功 -> 交集不相交 -> 豁免放行(误拦2修正面, 取数成功对照)
        result_x0 = M.cmd_post_and_wait(web_port, f"/api/torrents/{hx0}/delete", {"delete_files": True})
        assert (result_x0 or {}).get("status") == "ok", \
            f"负向对照失守: 取数成功的 X0 带文件删除被拒: {json.dumps(result_x0, ensure_ascii=False)[:500]}"
        M.wait_until(lambda: qb.torrent(hx0) is None, 30, "X0 删除回执 ok 但 qB 仍有 X0")
        M.wait_until(lambda: True if not (SRC / X0_NAME).exists() else None, 30, "X0 实文件残留(磁盘清净失守)")
        # 正向: X1 注入(清单不可得) -> D16 照旧拦(宁拦勿漏, 不豁免)
        result_x1 = M.cmd_post_and_wait(web_port, f"/api/torrents/{hx1}/delete", {"delete_files": True})
        receipt_txt = json.dumps(result_x1, ensure_ascii=False)
        assert (result_x1 or {}).get("status") == "error", \
            f"D16 失守: 清单不可得的 X1 带文件删除被放行: {receipt_txt[:500]}"
        assert "别名" in receipt_txt, f"D16 拦截文案缺失(活动别名面): {receipt_txt[:500]}"
        assert qb.torrent(hx1) is not None, "D16 拦截回执 error 但 qB 侧 X1 被删(整批不发失守)"
        assert (SRC / X1_NAME).is_file(), "D16 拦截后 X1 实文件被删(不误删失守)"
        d16_lines = _warn_lines(case, WARN_D16, hx1)
        assert len(d16_lines) > d16_c0, \
            f"保守留痕缺失: 「{WARN_D16}」WARNING 未增长(注入面未生效?): {d16_lines[-1:] or '(无)'}"
        assert p.alive(), "D16 拦截后产品进程死亡(raise 逃逸/崩溃)"
        M.wait_until(
            lambda: ((M.member_detail(web_port, h1) or {}).get("relocate") or {}).get("phase") == "armed" or None, 15,
            lambda: f"拦截后产品 WEB 不可响应/相位受扰: "
            f"{((M.member_detail(web_port, h1) or {}).get('relocate') or {}).get('phase')}"
        )
        ev["S3_d16"] = {
            "trigger": hx1,
            "x0_negative": {
                "status": (result_x0 or {}).get("status"),
                "file_gone": True
            },
            "x1_positive": {
                "status": (result_x1 or {}).get("status"),
                "kept": True
            },
            "warn_d16_lines": len(d16_lines),
            "product_alive": True,
        }
        _flush(ev, case, "S3")

        # ---- S4 删链门保守(注入保持): 删光成员 -> 收缩 -> 空集核验顺 VERIFY -> 保守计依赖
        gate_c0 = M.log_text(case).count(GATE_LINE)
        fm_c0 = len(_warn_lines(case, WARN_FILEMAP, hx1[:8]))
        qb.delete(h1, delete_files=False)
        qb.delete(h2, delete_files=False)
        M.wait_until(
            lambda: True
            if M.log_text(case).count(GATE_LINE) > gate_c0 else None, 120, "删链门依赖未清行未出现(清单不可得未被保守计依赖 = 宁拦勿漏失守)"
        )
        dep_line = [ln for ln in M.log_text(case).splitlines() if GATE_LINE in ln][-1]
        assert "(1 个)" in dep_line, \
            f"依赖计数非 1(恰 1 = X2 同位置取数成功不被计的负向对照面): {dep_line}"
        fm_lines = _warn_lines(case, WARN_FILEMAP, hx1[:8])
        assert len(fm_lines) > fm_c0, \
            f"保守留痕缺失: 「{WARN_FILEMAP}」WARNING 未增长(删链门未消费注入面?): {fm_lines[-1:] or '(无)'}"

        def chain_deps_on_disk():
            job = M.jobs_on_disk(case).get(job_id) or {}
            return job if job.get("reason") == ru.REASON_CHAIN_DEPS else None

        jobrow = M.wait_until(
            chain_deps_on_disk, 100,
            lambda: f"磁盘账未落 chain_deps: {(M.jobs_on_disk(case).get(job_id) or {}).get('reason')}"
        )
        assert hx1[:8] in str(jobrow.get("last_error") or ""), \
            f"依赖账样例缺 X1: {jobrow.get('last_error')}"
        # 宁拦勿漏面: 别名原样 + X1 原样(不豁免不误删) + X2 零扰动
        assert M.reparse_kind(link) == "symlink", f"删链门悬挂期别名被删(误删链接): {link}"
        assert M.norm(_readlink_norm(link)).startswith(M.norm(dst)), f"悬挂期 symlink 指向被改: {_readlink_norm(link)}"
        assert qb.torrent(hx1) is not None, "删链门悬挂期 X1 被删"
        assert (SRC / X1_NAME).is_file(), "删链门悬挂期 X1 实文件被删(不误删失守)"
        x2row = _assert_outsider_scene(qb, web_port, hx2, X2_NAME, "X2(悬挂期负向对照)")
        assert p.alive(), "删链门悬挂期产品进程死亡"
        ev["S4_chain_gate"] = {
            "dep_line": dep_line,
            "warn_filemap_lines": len(fm_lines),
            "disk_reason": jobrow.get("reason"),
            "disk_last_error": jobrow.get("last_error"),
            "alias_kept": True,
            "x1_kept": True,
            "x2": x2row,
            "product_alive": True,
        }
        _flush(ev, case, "S4")

        # ---- S5 注入解除 -> 依赖清零收敛(负向对照完成: 取数成功 -> 豁免 -> 放行 -> 收尾)
        trigger.unlink(missing_ok=True)
        result_x1b = M.cmd_post_and_wait(web_port, f"/api/torrents/{hx1}/delete", {"delete_files": True})
        assert (result_x1b or {}).get("status") == "ok", \
            f"负向对照失守: 注入解除后 X1 带文件删除仍被拒: {json.dumps(result_x1b, ensure_ascii=False)[:500]}"
        M.wait_until(lambda: qb.torrent(hx1) is None, 30, "X1 删除回执 ok 但 qB 仍有 X1")
        M.wait_until(lambda: True if not (SRC / X1_NAME).exists() else None, 30, "X1 实文件残留(磁盘清净失守)")
        M.wait_until(lambda: True if FIN_LINE in M.log_text(case) else None, 180, "收尾完成行未出现(依赖清零后收尾未恢复)")
        fin = [ln for ln in M.log_text(case).splitlines() if FIN_LINE in ln][-1]
        assert "删链门依赖清零" in fin and "已在线删除别名" in fin, f"收尾行语义不符: {fin}"
        M.wait_until(lambda: True if not os.path.lexists(str(link)) else None, 60, "收尾后 symlink 未删除")

        def done_on_disk():
            job = M.jobs_on_disk(case).get(job_id) or {}
            return job if job.get("phase") == ru.PHASE_DONE and job.get("reason") == ru.REASON_FINALIZED else None

        fjob = M.wait_until(done_on_disk, 100, lambda: f"磁盘账未落 done/finalized: {M.jobs_on_disk(case).get(job_id)}")
        x2row2 = _assert_outsider_scene(qb, web_port, hx2, X2_NAME, "X2(终态对照)")
        assert p.alive(), "收敛后产品进程死亡"
        ev["S5_converged"] = {
            "x1_negative_after_unsettle": {
                "status": (result_x1b or {}).get("status"),
                "file_gone": True
            },
            "fin_line": fin,
            "phase": fjob.get("phase"),
            "reason": fjob.get("reason"),
            "alias_removed": True,
            "x2_survives": x2row2,
            "product_alive": True,
        }
        _flush(ev, case, "S5")

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
            my_hashes = [h for h in (h1, h2, hx0, hx1, hx2) if h]
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
        if link is not None and os.path.lexists(str(link)) and M._is_link(str(link)):
            errs.append(f"别名零残留失守: {link}")
        if errs:
            raise AssertionError(f"收尾未净(Z): {'; '.join(errs)}")
