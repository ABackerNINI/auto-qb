"""test_actions_on_error 测试计划: rules/actions 动作插件执行语义

## 测试计划(每个测试函数一条)
- test_on_error_stop_default_fail: on_error=stop(缺省)动作失败 -> 中止动作链, 后续动作不执行
- test_on_error_stop_default_raise: on_error=stop 动作内异常 -> 同失败径中止动作链
- test_on_error_continue_fail: on_error=continue 失败 -> 记账后继续后续动作, 链不中断
- test_on_error_continue_raise: on_error=continue 异常 -> 同 continue 径继续后续动作
- test_on_error_retry_requeues_with_backoff: on_error=retry 失败 -> VERDICT_RETRY + 断点挂
  失败动作 + retry_delay=backoff(引擎 requeue 推迟到期, 无 run 内 sleep)
- test_on_error_retry_exhausted_stops_chain: on_error=retry 重试耗尽(attempt>=retries) ->
  按 stop 收场中止链, 不再返回 RETRY
- test_on_error_retry_recovers_after_success: on_error=retry 续跑轮动作成功 -> 正常完成,
  断点消费、attempt 归零、执行历史照记
- test_on_error_retry_without_task_is_stop: 无任务上下文(外部入口)配 retry -> 按 stop 收场
  (requeue 无处安放, 保守退化不静默重试)
- test_on_error_retry_raise_with_task: on_error=retry 动作内异常 -> 与失败径同语义
  (RETRY / 耗尽 stop)
- test_on_error_malformed_rejected_at_rule_construction: on_error 取值非法 -> Rule 构造期
  ConfigError(绕过 config 校验直构造的 fail-fast 兜底层)
"""

import os

import tempfile

from unittest.mock import patch

from auto_qb.rules.base import ActionResult, Rule, VERDICT_EXECUTED, VERDICT_RETRY

from auto_qb.rules.actions import (
    AddCategoryAction,
    AddTagsAction,
    CheckAction,
    DownloadSpeedLimitAction,
    MoveToAction,
    ReannounceAction,
    RemoveCategoryAction,
    RemoveTagsAction,
    StartAction,
    StopAction,
    UploadSpeedLimitAction,
)

from helpers import capture_logs, drive_skip, FakeClient, FakeTorrent, make_ctx, make_manager, seed_store


class _StubAction:
    """动作桩: behavior = fail(返回失败) / raise(抛异常) / ok(成功)"""

    name = "stub"

    def __init__(self, label, behavior, calls):
        self._label = label
        self._behavior = behavior
        self._calls = calls

    def execute(self, ctx):
        self._calls.append(self._label)
        if self._behavior == "raise":
            raise RuntimeError("stub boom")
        if self._behavior == "fail":
            return ActionResult.fail("stub fail")
        return ActionResult.ok("stub ok")


def _on_error_rule(mgr, first_on_error=None, first_behavior="fail"):
    """动作[0]带指定 on_error 的两动作规则; 两个动作都换测试桩, 返回 (rule, calls)"""
    act_spec = {"type": "add_tags", "params": ["X"]}
    if first_on_error is not None:
        act_spec["on_error"] = first_on_error
    rule = Rule("g.oe", {"actions": [act_spec, {"type": "add_tags", "params": ["Y"]}]}, mgr)
    calls = []
    # W3-B 起 process 迭代 self.steps(choose 块与普通动作同占一步): 换桩时 steps/actions 同步替换
    rule.steps[0] = ("action", _StubAction("first", first_behavior, calls), rule.steps[0][2])
    rule.steps[1] = ("action", _StubAction("second", "ok", calls), rule.steps[1][2])
    rule.actions = [rule.steps[0][1], rule.steps[1][1]]
    return rule, calls


def _retry_task(mgr, tor):
    """带断点语义的任务替身(与引擎 _handle_rule 消费的 Task 同型)"""
    from auto_qb.core.taskqueue import Task

    return Task("rule", "g.oe", hash=tor.hash, store=mgr.store, interval=60)


def _run_with_task(mgr, rule, tor, client, task):
    ctx = make_ctx(mgr, tor, client)
    ctx.task = task
    return ctx, rule.process(ctx)


def test_on_error_malformed_rejected_at_rule_construction():
    """on_error 取值非法(retries/backoff 不可解析) -> Rule 构造期 ConfigError(fail-fast 兜底层)

    config 校验是第一道闸; 绕过校验直接构造 Rule(测试/内存 Config)时构造期按同口径拒绝,
    不留「运行期每轮解析失败」的悬空面。
    """
    import pytest

    from auto_qb.config import ConfigError

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        with pytest.raises(ConfigError, match="on_error 取值非法"):
            Rule("g.oe", {"actions": [{"type": "add_tags", "params": ["X"], "on_error": {"retries": "abc"}}]}, mgr)


def test_on_error_stop_default_fail():
    """on_error=stop(缺省)动作失败 -> 中止动作链, 后续动作不执行(现行语义零变化)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client, tor = FakeClient(), FakeTorrent(tags="")
        rule, calls = _on_error_rule(mgr)  # 缺省 on_error(normalize 注入 stop)
        ctx = make_ctx(mgr, tor, client)
        assert rule.process(ctx) == VERDICT_EXECUTED
        assert calls == ["first"], f"stop 档失败必须中止链: {calls}"
        assert mgr.ctx.state.get_exec_record(rule.name, tor.hash) is None, "链未走通不计执行历史"


def test_on_error_stop_default_raise():
    """on_error=stop 动作内异常 -> 与失败径同语义: 中止动作链, 异常转 fail 不外抛"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client, tor = FakeClient(), FakeTorrent(tags="")
        rule, calls = _on_error_rule(mgr, first_behavior="raise")
        ctx = make_ctx(mgr, tor, client)
        assert rule.process(ctx) == VERDICT_EXECUTED
        assert calls == ["first"], f"stop 档异常必须中止链: {calls}"


def test_on_error_continue_fail():
    """on_error=continue 失败 -> 记账后继续后续动作(替代退役布尔 ignore_next_action_error)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client, tor = FakeClient(), FakeTorrent(tags="")
        rule, calls = _on_error_rule(mgr, first_on_error={"policy": "continue"})
        ctx = make_ctx(mgr, tor, client)
        assert rule.process(ctx) == VERDICT_EXECUTED
        assert calls == ["first", "second"], f"continue 档失败不得中断链: {calls}"
        assert mgr.ctx.state.get_exec_record(rule.name, tor.hash) is not None, "后续动作成功照记执行历史"


def test_on_error_continue_raise():
    """on_error=continue 异常 -> 同 continue 径: 异常转 fail, 继续后续动作"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client, tor = FakeClient(), FakeTorrent(tags="")
        rule, calls = _on_error_rule(mgr, first_on_error={"policy": "continue"}, first_behavior="raise")
        ctx = make_ctx(mgr, tor, client)
        assert rule.process(ctx) == VERDICT_EXECUTED
        assert calls == ["first", "second"], f"continue 档异常不得中断链: {calls}"


def test_on_error_retry_requeues_with_backoff():
    """on_error=retry 失败 -> VERDICT_RETRY + 断点挂失败动作 + retry_delay=backoff; 无 run 内 sleep"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client, tor = FakeClient(), FakeTorrent(tags="")
        rule, calls = _on_error_rule(mgr, first_on_error={"policy": "retry", "retries": 2, "backoff": 30})
        task = _retry_task(mgr, tor)
        with patch("time.sleep", side_effect=AssertionError("run 内 sleep 禁止(黄金法则 3/5)")):
            ctx, verdict = _run_with_task(mgr, rule, tor, client, task)
        assert verdict == VERDICT_RETRY, f"retry 档失败应返回 VERDICT_RETRY: {verdict}"
        assert task.resume_index == 0, f"断点必须挂失败动作索引: {task.resume_index}"
        assert task.retry_delay == 30.0, f"requeue 推迟秒数须为 backoff: {task.retry_delay}"
        assert calls == ["first"], "RETRY 轮不得继续后续动作"
        # 引擎消费面(attempt +1)后重试再失败: 第二次仍 RETRY(上限 retries=2)
        task.attempt += 1
        with patch("time.sleep", side_effect=AssertionError("run 内 sleep 禁止(黄金法则 3/5)")):
            ctx, verdict = _run_with_task(mgr, rule, tor, client, task)
        assert verdict == VERDICT_RETRY and task.attempt < 2


def test_on_error_retry_exhausted_stops_chain():
    """on_error=retry 重试耗尽(attempt>=retries) -> 按 stop 收场中止链, 不再返回 RETRY"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client, tor = FakeClient(), FakeTorrent(tags="")
        rule, calls = _on_error_rule(mgr, first_on_error={"policy": "retry", "retries": 2, "backoff": 30})
        task = _retry_task(mgr, tor)
        task.attempt = 2  # 已重试 2 次 = 上限
        ctx = make_ctx(mgr, tor, client)
        ctx.task = task
        assert rule.process(ctx) == VERDICT_EXECUTED, "耗尽后按 stop 收场"
        assert calls == ["first"], f"耗尽后中止链: {calls}"
        assert task.resume_index is None and task.attempt == 0, "正常收尾消费断点并归零 attempt"


def test_on_error_retry_recovers_after_success():
    """on_error=retry 续跑轮动作成功 -> 正常完成: 断点消费、attempt 归零、执行历史照记"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client, tor = FakeClient(), FakeTorrent(tags="")
        rule, calls = _on_error_rule(mgr, first_on_error={"policy": "retry", "retries": 2, "backoff": 30})
        task = _retry_task(mgr, tor)
        # 脚本化桩: 首跑失败, 续跑轮成功(_scripted 按调用次数取 behavior)
        results = ["fail", "ok"]

        class _Scripted:
            name = "stub"

            def execute(self, ctx):
                calls.append("first")
                behavior = results.pop(0) if results else "ok"
                if behavior == "raise":
                    raise RuntimeError("stub boom")
                return ActionResult.fail("stub fail") if behavior == "fail" else ActionResult.ok("stub ok")

        rule.steps[0] = ("action", _Scripted(), rule.steps[0][2])  # W3-B: steps 是执行单点
        rule.actions[0] = rule.steps[0][1]
        ctx = make_ctx(mgr, tor, client)
        ctx.task = task
        assert rule.process(ctx) == VERDICT_RETRY, "首跑失败返回 RETRY"
        task.attempt += 1  # 引擎 _handle_rule 消费
        assert rule.process(ctx) == VERDICT_EXECUTED, "续跑轮成功正常完成"
        assert task.resume_index is None and task.attempt == 0, "断点消费 + attempt 归零"
        assert calls == ["first", "first", "second"], f"续跑轮从失败动作重跑并继续后续动作: {calls}"
        assert mgr.ctx.state.get_exec_record(rule.name, tor.hash) is not None, "执行历史照记"


def test_on_error_retry_without_task_is_stop():
    """无任务上下文(外部入口)配 retry -> 按 stop 收场(requeue 无处安放, 保守退化)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client, tor = FakeClient(), FakeTorrent(tags="")
        rule, calls = _on_error_rule(mgr, first_on_error={"policy": "retry", "retries": 2, "backoff": 30})
        ctx = make_ctx(mgr, tor, client)
        assert ctx.task is None
        assert rule.process(ctx) == VERDICT_EXECUTED
        assert calls == ["first"], f"无任务时 retry 退化为 stop 中止链: {calls}"


def test_on_error_retry_raise_with_task():
    """on_error=retry 动作内异常 -> 与失败径同语义: RETRY 信号 / 耗尽按 stop"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client, tor = FakeClient(), FakeTorrent(tags="")
        rule, calls = _on_error_rule(
            mgr, first_on_error={
                "policy": "retry",
                "retries": 1,
                "backoff": 5
            }, first_behavior="raise"
        )
        task = _retry_task(mgr, tor)
        ctx = make_ctx(mgr, tor, client)
        ctx.task = task
        assert rule.process(ctx) == VERDICT_RETRY
        assert task.resume_index == 0 and task.retry_delay == 5.0
        task.attempt += 1
        assert rule.process(ctx) == VERDICT_EXECUTED, "异常径耗尽同按 stop 收场"
        assert calls == ["first", "first"]
