"""journal 双写者合并语义表驱动钉扎(S2b, 计划 26-11-15-2340 §03.6 钉扎表「journal 双写者族」)

journal 是收尾账的**跨进程投影**(I3), 权威账只有 state.json 的 job 账 —— 但 journal 实际
有两个写者(daemon 写改写账/rewritten 相位, 主循环写终态/回滚), 无跨进程锁、整包
last-writer-wins, 唯一必须守住的序: **非终态不得覆盖终态**。合并语义的单点 =
write_journal 的前向合并 + record_rewrites/reset_rewrites 两个合并口。本文件按三个历史
实锤形态表驱动钉扎(相位派生后合并点唯一):
- 心跳覆盖终态: 主循环已收口(done/cancelled/failed/superseded)后 daemon 的任何非终态写
  (心跳式记账/arm/翻相)一律拒写且文件原样 —— 否则退休指令被回退, 已终结 job 的改写账
  被继续重放(D12);
- arm 不重置: daemon 记账不带 phase 不得把 rewritten 打回 armed(否则收尾窗来回摆,
  pending 永不清);
- 同盘永卡: 相位回摆(rewritten -> armed 重放 -> rewritten)是合法双写序, 但合并必须
  **保键** —— verify_replays 计数/rewrites 明细被整包覆盖丢键 = 重放节奏闸失效 = 永卡。

## 测试计划(每个测试函数一条)
- test_stop_phases_mirror_terminal_phases: journal.STOP_PHASES 与 units.TERMINAL_PHASES
  同值配对(infra 不反向 import core, 字面量镜像由本测试钉住 —— 单活模型扩相位时两处必须同步)
- test_daemon_writes_never_overwrite_terminal: 表驱动 —— 终态账(journal 相位 ∈ STOP_PHASES)
  遇 daemon 全部写入口(record_rewrites 带/不带 phase、write_journal 非终态相位)一律拒写
  (心跳覆盖终态三写入口面)
- test_record_rewrites_phase_none_preserves_rewritten: arm 不重置 —— rewritten 账上
  record_rewrites(phase=None) 只并改写账, 相位保持 rewritten
- test_phase_flip_flop_keeps_counters: rewritten -> armed(reset_rewrites 重放)-> rewritten
  (daemon 翻相)回摆合法, verify_replays 计数与重置账(prev_status)跨 daemon 合并不丢键
  (同盘永卡根因面: 丢计数 = 重放节奏闸失效)
- test_main_loop_terminal_writes_always_win: 主循环写终态于非终态之上恒成功; 终态互覆
  last-writer-wins(契约既有面, 与拒写面同表钉住)
- test_reset_rewrites_refused_on_terminal: 终态账不得重放(reset_rewrites -> -1, 不动盘)
"""
import pytest

from auto_qb.core.modules import relocate_units as ru
from auto_qb.infra import relocate_journal as rj


def _read(data_dir, jid):
    return rj.read_journal(data_dir, jid)


def _mk(data_dir, jid, phase, **extra):
    body = {"phase": phase, "ts": 100.0}
    body.update(extra)
    assert rj.write_journal(data_dir, jid, body)


def test_stop_phases_mirror_terminal_phases():
    """STOP_PHASES(journal 侧字面量)与 TERMINAL_PHASES(units 权威)同值配对"""
    assert rj.STOP_PHASES == ru.TERMINAL_PHASES


@pytest.mark.parametrize("terminal_phase", ["done", "cancelled", "failed", "superseded"])
def test_daemon_writes_never_overwrite_terminal(tmp_path, terminal_phase):
    """表驱动: 终态账遇 daemon 三个写入口一律拒写且文件原样(心跳覆盖终态)"""
    data_dir, jid = str(tmp_path / "data"), "jr-1"
    _mk(data_dir, jid, terminal_phase, rewrites={"HA": {"status": "rewritten", "ts": 1.0}})
    before = _read(data_dir, jid)

    # daemon 写入口其一: record_rewrites 不带 phase(心跳式记账)
    assert rj.record_rewrites(data_dir, jid, {"HA": {"status": "rewritten"}}) is False
    # 其二: record_rewrites 带非终态相位(arm/翻相)
    assert rj.record_rewrites(data_dir, jid, {}, phase="rewritten") is False
    assert rj.record_rewrites(data_dir, jid, {}, phase="armed") is False
    # 其三: write_journal 直写非终态相位
    assert rj.write_journal(data_dir, jid, {"phase": "armed", "ts": 200.0}) is False

    assert _read(data_dir, jid) == before, "终态账逐键原样(拒写不落盘)"


def test_record_rewrites_phase_none_preserves_rewritten(tmp_path):
    """arm 不重置: rewritten 账上记账不带 phase, 相位保持 rewritten 不被打回 armed"""
    data_dir, jid = str(tmp_path / "data"), "jr-2"
    _mk(data_dir, jid, "rewritten", rewrites={})

    ok = rj.record_rewrites(data_dir, jid, {"HB": {"status": "rewritten"}}, pid=4321)

    assert ok is True
    body = _read(data_dir, jid)
    assert body["phase"] == "rewritten", "phase=None 只并账不重置相位(arm 不重置)"
    assert body["rewrites"]["HB"]["status"] == "rewritten"
    assert body["pid"] == 4321


def test_phase_flip_flop_keeps_counters(tmp_path):
    """回摆合法且保键: rewritten -> armed(重放)-> rewritten(daemon 翻相), verify_replays
    与重置明细跨 daemon 整包合并不丢(丢键 = 重放节奏闸失效 = 同盘永卡根因)"""
    data_dir, jid = str(tmp_path / "data"), "jr-3"
    _mk(data_dir, jid, "rewritten", rewrites={"HA": {"status": "rewritten", "ts": 1.0}})

    # 主循环核验不过: 重放入口把 settled 清回 pending + 相位回 armed + 计数 +1
    assert rj.reset_rewrites(data_dir, jid, ts=200.0) == 1
    body = _read(data_dir, jid)
    assert body["phase"] == "armed"
    assert body["rewrites"]["HA"]["status"] == "pending"
    assert body["rewrites"]["HA"]["prev_status"] == "rewritten"
    assert body[rj.VERIFY_REPLAYS_KEY] == 1

    # daemon 下一窗口重放改写并翻相 rewritten: 整包合并必须带上主循环写的计数键
    assert rj.record_rewrites(data_dir, jid, {"HA": {"status": "rewritten"}}, phase="rewritten") is True
    body = _read(data_dir, jid)
    assert body["phase"] == "rewritten"
    assert body[rj.VERIFY_REPLAYS_KEY] == 1, "daemon 合并不丢 verify_replays(重放节奏闸)"
    assert body["rewrites"]["HA"]["status"] == "rewritten"

    # 再一轮核验不过: 计数累加(节奏闸读得到历史)
    assert rj.reset_rewrites(data_dir, jid, ts=300.0) == 1
    assert _read(data_dir, jid)[rj.VERIFY_REPLAYS_KEY] == 2


def test_main_loop_terminal_writes_always_win(tmp_path):
    """主循环写终态于非终态之上恒成功; 终态互覆 last-writer-wins(契约既有面)"""
    data_dir, jid = str(tmp_path / "data"), "jr-4"
    _mk(data_dir, jid, "armed")
    assert rj.write_journal(data_dir, jid, {"phase": "done", "ts": 110.0}) is True
    assert _read(data_dir, jid)["phase"] == "done"
    assert rj.write_journal(data_dir, jid, {"phase": "failed", "ts": 120.0}) is True
    assert _read(data_dir, jid)["phase"] == "failed"


def test_reset_rewrites_refused_on_terminal(tmp_path):
    """终态账不得重放: reset_rewrites 返回 -1, 账面与盘面零触碰"""
    data_dir, jid = str(tmp_path / "data"), "jr-5"
    _mk(data_dir, jid, "done", rewrites={"HA": {"status": "rewritten", "ts": 1.0}})
    before = _read(data_dir, jid)

    assert rj.reset_rewrites(data_dir, jid) == -1
    assert _read(data_dir, jid) == before

    # 无 settled 记录的非终态账: 0(不动盘, 幂等) —— 与拒写面区分
    _mk(data_dir, "jr-6", "armed", rewrites={"HA": {"status": "pending"}})
    assert rj.reset_rewrites(data_dir, "jr-6") == 0
    assert _read(data_dir, "jr-6") == {"phase": "armed", "ts": 100.0, "rewrites": {"HA": {"status": "pending"}}}
