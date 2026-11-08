"""test_rule_trace 测试计划: per-run trace(W4, plan 26-11-01-0106 D5/D4)

per-run trace 是规则排障辅助: 维度 = (规则 x 种子 hash), 键面 state["rule_traces"]["{规则名}:{hash}"],
回答「这条规则这次为什么没跑/跑了什么」。体积两层合围:
- 写入侧(rules/base.py): 条件明细叶子条数 <= _TRACE_COND_MAX_ITEMS(超出留头部 + clip 标记),
  错误/消息串 <= _TRACE_MSG_MAX_CHARS 字符;
- state 层(core/state.py): 每维度环形 _TRACE_KEEP_PER_DIM 条 + 保留期 _TRACE_KEEP_DAYS 天 +
  全键面总条目 _TRACE_MAX_ENTRIES + 单条序列化 <= _TRACE_ENTRY_MAX_BYTES 字节(超限降级截断存根)
—— 相乘给出体积硬上界 300 x 2KiB = 600KiB, 1MiB 红线压测见 test_trace_size_redline_stress。
trace 无去重语义, 与 exec_history(去重依据)同键口径互不迁移; prune 复用 _prune_exec_history
同款机制(_evict_oldest / prune_day_keys 单点, 差异仅 keep_today=False)。

## 测试计划(每个测试函数一条)
- test_trace_condition_no_match_end_to_end: 条件不命中端到端例 —— 一次运行后从 state 读 trace
  能回答「这条规则这次为什么没跑」(verdict=no_match + 逐叶子求值明细 + 空动作表)
- test_trace_condition_error_end_to_end: 条件异常端到端例 —— trace 带异常叶子明细(e 字段截断,
  无 name 哑条件回退类名)与顶层 error, verdict=error
- test_trace_action_failure_end_to_end: 动作失败端到端例 —— 每步状态/处置/消息(截断)落 trace,
  失败步 disp=stop, verdict=executed(失败动作计已执行)
- test_trace_retry_and_resume_signals: retry/断点信号 —— retry 档 trace 记 {attempt, delay} 与
  resume 断点索引; 续跑成功轮断点已消费不残留 resume 键
- test_trace_ring_keep_recent_per_dim: 环形 —— 每维度只留最近 _TRACE_KEEP_PER_DIM 条, 最旧先出
- test_trace_entry_byte_cap_stub: 单条体积兜底 —— 超 _TRACE_ENTRY_MAX_BYTES 的条目降级为截断
  存根(保留 verdict/ts/date 与 truncated 标记, 丢明细)
- test_trace_prune_keep_days_and_total_cap: prune 复用同款机制 —— 维度按最新条目日期过保留期淘汰;
  总条目超上限逐出最旧(trace 无去重语义, 当日也参与, keep_today=False)
- test_trace_size_redline_stress: 体积红线压测 —— 近深度上限条件树(40 叶 x 15 层嵌套) x 40 种子
  x 3 轮高频运行, 断言 trace 键面总体积 <= 1MiB(环形/总量逐出/单条字节上限全部生效)
- test_trace_old_state_keys_unaffected: 旧 state 载入回归 —— 既有 exec_history 去重判定不变,
  rule_traces 新键面零干扰(旧文件无该键照常 setdefault), 落盘重读两键面共存
- test_trace_dry_run_flagged: dry-run 运行在 trace 里带 dry 标记(据 trace 分辨真实/演练运行)

覆盖率第三轮 T2b 补测(26-11-05):
- test_trace_prune_ring_fallback_trims_oversized_dim: 环形兜底 —— 外部种入超限维度被 prune 裁回 KEEP_PER_DIM(351->352)
"""
import json
import os
import tempfile
from datetime import datetime, timedelta
from types import SimpleNamespace

from auto_qb.config.compat import CONDITION_TREE_MAX_DEPTH
from auto_qb.core import state as state_mod
from auto_qb.core.state import StateService
from auto_qb.rules.base import (
    VERDICT_ERROR,
    VERDICT_EXECUTED,
    VERDICT_NO_MATCH,
    VERDICT_RETRY,
    ActionResult,
    BaseAction,
    Rule,
)
from auto_qb.rules.actions import AddTagsAction
from helpers import FakeClient, FakeTorrent, make_ctx, make_manager


def _latest_trace(mgr, rule_name: str, hash_: str) -> dict:
    """从 state 读某维度最新一条 trace(排障端到端例的读法口径: mgr.state["rule_traces"])"""
    dim = mgr.state["rule_traces"][f"{rule_name}:{hash_}"]
    assert dim, "维度至少一条"
    return dim[-1]


def test_trace_condition_no_match_end_to_end():
    """条件不命中端到端例: 从 state 读 trace 回答「为什么没跑」—— verdict + 哪个叶子 False"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags="", size=1), client)  # 1 字节, 远小于 1MiB
        rule = Rule(
            "g.test",
            {
                "conditions": [{
                    "size": ">=1MiB"
                }],
                "actions": [{
                    "add_tags": ["DONE"]
                }],
            },
            mgr,
        )
        assert rule.process(ctx) == VERDICT_NO_MATCH
        assert client.calls == [], "未执行动作"
        entry = _latest_trace(mgr, "g.test", "HASH123")
        assert entry["verdict"] == "no_match", "结论: 条件不满足"
        assert entry["conditions"] == [{"c": "size", "r": False}], "求值明细: size 叶子 False"
        assert entry["actions"] == [], "没跑到任何动作"
        assert "ts" in entry and "date" in entry, "排序字段由 state 层补齐"


def test_trace_condition_error_end_to_end():
    """条件异常端到端例: trace 带异常叶子明细 + 顶层 error, verdict=error(本条本轮不命中)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags=""), client)

        class Boom:
            def match(self, ctx):
                raise RuntimeError("boom-" + "x" * 300)

        rule = Rule("g.test", {"actions": [{"add_tags": ["X"]}]}, mgr)
        rule.condition_tree = ("all", [("leaf", Boom())])
        assert rule.process(ctx) == VERDICT_ERROR
        assert client.calls == []
        entry = _latest_trace(mgr, "g.test", "HASH123")
        assert entry["verdict"] == "error"
        # 无 name 的哑条件: 明细回退类名(求值明细是辅助, 不能因取名失败反弄错 verdict)
        rec = entry["conditions"][0]
        assert rec["c"] == "Boom"
        assert rec["e"].startswith("RuntimeError: boom-") and len(rec["e"]) <= 200, "异常串截断留头"
        assert "boom" in entry["error"], "顶层 error 可读"


def test_trace_action_failure_end_to_end():
    """动作失败端到端例: 每步 st/disp/msg 落 trace, 失败步 disp=stop, verdict=executed"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags=""), client)

        class FailAction(BaseAction):
            name = "fail"

            def execute(self, ctx):
                return ActionResult.fail("qB 请求 500: " + "d" * 500)

        rule = Rule("g.test", {"actions": [{"add_tags": ["X"]}]}, mgr)
        rule.steps = [("action", FailAction(None), Rule._resolve_on_error(None))]
        assert rule.process(ctx) == VERDICT_EXECUTED, "失败动作本身计已执行(W2 前语义不变)"
        assert client.calls == []
        entry = _latest_trace(mgr, "g.test", "HASH123")
        assert entry["verdict"] == "executed"
        assert entry["conditions"] == [], "无条件规则零求值明细"
        (step, ) = entry["actions"]
        assert step["name"] == "fail" and step["st"] == "failed" and step["disp"] == "stop"
        assert step["msg"].startswith("qB 请求 500:") and len(step["msg"]) <= 200, "消息截断留头"


def test_trace_retry_and_resume_signals():
    """retry/断点信号: retry 档 trace 记 {attempt, delay} + resume 断点; 成功续跑轮不残留"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()

        class FailAction(BaseAction):
            name = "fail"

            def execute(self, ctx):
                return ActionResult.fail("boom")

        rule = Rule("g.test", {"actions": [{"add_tags": ["X"]}]}, mgr)
        on_error = {"policy": "retry", "retries": 3, "backoff": 45}
        rule.steps = [("action", FailAction(None), on_error)]
        task = SimpleNamespace(resume_index=None, attempt=0, retry_delay=None)
        ctx = make_ctx(mgr, FakeTorrent(tags=""), client)
        ctx.task = task
        assert rule.process(ctx) == VERDICT_RETRY
        entry = _latest_trace(mgr, "g.test", "HASH123")
        assert entry["verdict"] == "retry"
        assert entry["retry"] == {"attempt": 0, "delay": 45}, "attempt 计数挂 Task, delay = backoff"
        assert entry["resume"] == 0, "断点挂失败动作(续跑轮从本动作重试)"
        # 续跑轮: 换成功动作从断点继续 —— 断点消费后 resume 信号不残留
        rule.steps = [("action", AddTagsAction(["X"]), Rule._resolve_on_error(None))]
        task.resume_index = 0
        task.attempt = 1
        assert rule.process(ctx) == VERDICT_EXECUTED
        entry2 = _latest_trace(mgr, "g.test", "HASH123")
        assert "resume" not in entry2 and "retry" not in entry2, "断点/重试信号只在挂起轮存在"


def test_trace_ring_keep_recent_per_dim():
    """环形: 每维度只留最近 _TRACE_KEEP_PER_DIM 条, 最旧先出"""
    with tempfile.TemporaryDirectory() as td:
        svc = StateService(os.path.join(td, "state.json"))
        for i in range(8):
            svc.record_rule_trace("r", "H", {"verdict": "executed", "n": i})
        dim = svc.data["rule_traces"]["r:H"]
        assert len(dim) == state_mod._TRACE_KEEP_PER_DIM
        assert [e["n"] for e in dim] == [3, 4, 5, 6, 7], "最旧 3 条被环形逐出, 新条目在尾"


def test_trace_entry_byte_cap_stub():
    """单条体积兜底: 超 _TRACE_ENTRY_MAX_BYTES 的条目降级截断存根(保留 verdict 与排序字段)"""
    with tempfile.TemporaryDirectory() as td:
        svc = StateService(os.path.join(td, "state.json"))
        big = {"verdict": "executed", "conditions": [{"c": "x", "r": True}], "msg": "y" * 5000}
        svc.record_rule_trace("r", "H", big)
        (entry, ) = svc.data["rule_traces"]["r:H"]
        raw = json.dumps(entry, ensure_ascii=False, default=str).encode("utf-8")
        assert len(raw) <= state_mod._TRACE_ENTRY_MAX_BYTES, "落库条目不超单条字节上限"
        assert entry["verdict"] == "executed" and entry["truncated"] is True
        assert "ts" in entry and "date" in entry, "排序字段保留"
        assert "conditions" not in entry and "msg" not in entry, "明细让位于体积红线"
        # 正常条目原样保留(不误伤)
        svc.record_rule_trace("r", "H2", {"verdict": "no_match", "conditions": [{"c": "size", "r": False}]})
        (normal, ) = svc.data["rule_traces"]["r:H2"]
        assert normal["conditions"] == [{"c": "size", "r": False}] and "truncated" not in normal


def test_trace_prune_keep_days_and_total_cap():
    """prune 复用 _prune_exec_history 同款机制: 保留期(维度最新条目定维龄) + 总量上限逐出"""
    from auto_qb.core import state as state_mod

    with tempfile.TemporaryDirectory() as td:
        svc = StateService(os.path.join(td, "state.json"))
        today = datetime.now().date()
        expired = (today - timedelta(days=state_mod._TRACE_KEEP_DAYS + 1)).isoformat()
        recent = (today - timedelta(days=1)).isoformat()
        svc.data["rule_traces"] = {
            "r_old:H": [{
                "verdict": "executed",
                "date": expired,
                "ts": 0.0
            }],
            "r_recent:H": [{
                "verdict": "executed",
                "date": recent,
                "ts": 1.0
            }],
            "r_today:H": [{
                "verdict": "executed",
                "date": today.isoformat(),
                "ts": 2.0
            }],
        }
        svc.record_rule_trace("r_new", "H", {"verdict": "no_match"})
        traces = svc.data["rule_traces"]
        assert "r_old:H" not in traces, "维度最新条目超保留期整维淘汰"
        assert "r_recent:H" in traces and "r_today:H" in traces and "r_new:H" in traces

        # 总量上限: 塞满上限条目(当日)再写一条 —— trace 无去重语义, 当日也参与逐出
        svc.data["rule_traces"] = {
            f"r{i}:H{j}": [{
                "verdict": "executed",
                "date": today.isoformat(),
                "ts": float(i * 10 + j)
            }]
            for i in range(50)
            for j in range(state_mod._TRACE_MAX_ENTRIES // 50)
        }
        before = sum(len(v) for v in svc.data["rule_traces"].values())
        assert before == state_mod._TRACE_MAX_ENTRIES
        svc.record_rule_trace("r_new", "H", {"verdict": "no_match"})
        traces = svc.data["rule_traces"]
        total = sum(len(v) for v in traces.values())
        assert total <= state_mod._TRACE_MAX_ENTRIES, "总条目不超上限(当日记录也逐出, keep_today=False)"
        assert "r_new:H" in traces, "新写入条目在"


def test_trace_size_redline_stress():
    """体积红线压测(验收判据2): 近深度上限条件树 x 高频种子, trace 键面总体积 <= 1 MiB

    极端构造: 40 个 size 叶子(全命中) 嵌 15 层 all(叶子恰在深度上限 16), 3 条规则 x
    40 种子 = 120 维度各跑 3 轮(共 360 条写入 > 总量上限 300, 逐出生效)。断言:
    总体积 / 总条目 / 每维度环形条数 / 单条字节量 四层全部在界内。
    """
    leaves = [{"size": f">={i}MiB"} for i in range(1, 41)]  # 种子 100MiB: 40 叶全命中
    tree = {"all": leaves}
    # 内层 all + 40 叶: 叶子深度 = 嵌套层数 + 2, 14 层包装 -> 叶子恰在深度上限 16
    for _ in range(CONDITION_TREE_MAX_DEPTH - 2):
        tree = {"all": [tree]}

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        # conditions 直接给树形 dict(给列表会被 normalize 包隐式 all 再添一层深度)
        rules = [Rule(f"g.r{i}", {"conditions": tree, "actions": [{"add_tags": [f"T{i}"]}]}, mgr) for i in range(3)]
        ctxs = [make_ctx(mgr, FakeTorrent(tags="", hash=f"H{i:03d}"), client) for i in range(40)]
        for _round in range(3):
            for rule in rules:
                for ctx in ctxs:
                    verdict = rule.process(ctx)
                    assert verdict in (VERDICT_EXECUTED, "no_op"), f"非预期 verdict: {verdict}"

        traces = mgr.state["rule_traces"]
        blob = json.dumps(traces, ensure_ascii=False, default=str).encode("utf-8")
        assert len(blob) <= 1024 * 1024, f"trace 键面总体积超 1MiB 红线: {len(blob)} bytes"
        total = sum(len(v) for v in traces.values())
        assert total <= state_mod._TRACE_MAX_ENTRIES, f"总条目超上限: {total}"
        assert total > 0 and len(traces) == 120, "全维度都有现场(高频种子逐出后仍覆盖)"
        for dim in traces.values():
            assert len(dim) <= state_mod._TRACE_KEEP_PER_DIM
            for entry in dim:
                raw = json.dumps(entry, ensure_ascii=False, default=str).encode("utf-8")
                assert len(raw) <= state_mod._TRACE_ENTRY_MAX_BYTES, "单条不超字节上限"
        # 条件明细条数截断生效: 40 叶 -> 31 条保留 + 1 条 clip 标记
        latest = traces[f"g.r0:H000"][-1]
        assert len(latest["conditions"]) == 32
        assert latest["conditions"][-1] == {"clip": 9}, "头部保留 + 丢弃计数标记"


def test_trace_old_state_keys_unaffected():
    """旧 state 载入回归: 既有 exec_history 去重判定不变, rule_traces 新键面零干扰"""
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "state.json")
        legacy = {
            "exec_history":
                {
                    "hhan_checking_rules.rule:ABCDEF123456": {
                        "ts": 1750000000.0,
                        "date": "2026-10-01",
                        "hour": 3
                    }
                }
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(legacy, f, ensure_ascii=False)
        svc = StateService(path)
        svc.data = svc.load()
        # 去重判定不变(旧键照常命中, 陌生键照常放行)
        assert svc.get_exec_record("hhan_checking_rules.rule", "ABCDEF123456") is not None
        assert svc.get_exec_record("hhan_checking_rules.rule", "OTHERHASH0000") is None
        # 旧文件无 rule_traces 键: setdefault 建新键面, 不触碰既有键
        svc.record_rule_trace("hhan_checking_rules.rule", "ABCDEF123456", {"verdict": "no_match"})
        assert svc.data["exec_history"]["hhan_checking_rules.rule:ABCDEF123456"]["date"] == "2026-10-01"
        (entry, ) = svc.data["rule_traces"]["hhan_checking_rules.rule:ABCDEF123456"]
        assert entry["verdict"] == "no_match"
        # 落盘重读: 两键面共存(exec_history 去重依据不因 trace 新键面丢失)
        svc.save()
        svc2 = StateService(path)
        svc2.data = svc2.load()
        assert svc2.get_exec_record("hhan_checking_rules.rule", "ABCDEF123456") is not None
        assert svc2.data["rule_traces"]["hhan_checking_rules.rule:ABCDEF123456"][0]["verdict"] == "no_match"


def test_trace_dry_run_flagged():
    """dry-run 运行在 trace 里带 dry 标记: 排障时能分辨演练与真实运行"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags=""), client, dry_run=True)
        rule = Rule("g.test", {"actions": [{"add_tags": ["X"]}]}, mgr)
        assert rule.process(ctx) == VERDICT_EXECUTED
        entry = _latest_trace(mgr, "g.test", "HASH123")
        assert entry["dry"] is True
        ctx2 = make_ctx(mgr, FakeTorrent(tags=""), client)
        rule.process(ctx2)
        assert "dry" not in _latest_trace(mgr, "g.test", "HASH123"), "真实运行无 dry 标记"


# ---------- 覆盖率第三轮 T2b 补测(26-11-05): 环形兜底裁维度 ----------


def test_trace_prune_ring_fallback_trims_oversized_dim():
    """(T2b)环形兜底(351->352): 写入侧已裁, 但外部种入超限维度(旧版本 state 文件)后
    任一次写入触发的 prune 都会把维度裁回 _TRACE_KEEP_PER_DIM, 最旧先出"""
    with tempfile.TemporaryDirectory() as td:
        svc = StateService(os.path.join(td, "state.json"))
        today = datetime.now().date().isoformat()
        svc.data["rule_traces"] = {
            "r:H":
                [
                    {
                        "verdict": "executed",
                        "date": today,
                        "ts": float(i)
                    } for i in range(state_mod._TRACE_KEEP_PER_DIM + 2)
                ],
        }
        svc.record_rule_trace("r2", "H2", {"verdict": "no_match"})
        dim = svc.data["rule_traces"]["r:H"]
        assert len(dim) == state_mod._TRACE_KEEP_PER_DIM, len(dim)
        assert [e["ts"] for e in dim] == [2.0, 3.0, 4.0, 5.0, 6.0], "最旧两条先出"
