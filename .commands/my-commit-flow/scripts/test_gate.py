"""gate.py(ship.gate 提交闸门预跑)守阵 —— 计划 26-11-11-0408。

预跑主体(run_gate_prerun)全部走替身: changed_files / load_config / run_gates 都是 monkeypatch
钉在 gate 模块命名空间上 —— 预跑的语义(树净 / 红线只提示 / when_message 过滤 / 全量失败明细 /
成功一行)与引擎(run_gates 本体)解耦, 引擎自有 test_pipeline 覆盖。真实包装载自检一条
(when_message 新键必须过 config_problems, 否则一写就挡提交)。

## 测试计划
- test_safety_probe_declares_action_without_args   --safety 探针自认「无参即真动作」(fmt 真改文件)
                                                   → 冒烟闸门摘除本脚本; rc 0
- test_explicit_empty_argv_enters_prerun           显式空表([]) = 测试裸调动作入口(sync.py 同款判据):
                                                   main([]) 不吃 pytest 的 sys.argv, 真跑预跑主体
- test_clean_tree_reports_nothing_to_run           树净 → rc 0 + 一行「树净, 无闸门可跑」, 不碰闸门
- test_config_stop_fails_fast                      配置体检 STOP(未知键) → 失败一行 rc 1, 不跑闸门
- test_red_lines_warn_only_gates_still_run         红线命中 → 只打 WARN 行, 闸门照跑(拍板 D6)
- test_warn_lines_note_only_gates_still_run        warn_lines 半边独立钉住: 「人工确认项」打行分支
                                                   回归(循环被删/键名改错)时红线用例救不了(分面 2)
- test_present_filters_vanished_paths              工作区已不存在的路径不进 present(与 commit 同口径);
                                                   空串 match 闸门在纯删除面上仍命中
- test_when_message_skipped_without_msg            消息文件不存在 → when_message 闸门打略过行后摘除,
                                                   其余闸门照跑, 不设 COMMIT_FLOW_MSG_FILE(拍板 D6)
- test_when_message_runs_with_msg                  消息文件存在 → when_message 闸门原样保留(提前发现
                                                   忘写 trailer) + 照 commit.py:515 注入消息路径
- test_no_hits_reports_no_gate                     闸门全被摘除/零命中 → 「无闸门命中」rc 0
- test_success_one_line                            全绿 → 恰一行结果(命中 G / 执行 C / 耗时), rc 0
- test_manual_gates_reported                       manual 兜底提示照打(本仓库配置恒空, 纯守阵)
- test_failures_list_all_after_result_line         失败 → 结果行先行(「N 条未过」), 全量明细垫底逐条
                                                   带闸门名/rc/耗时/$命令/输出尾; rc 1(预跑是诊断面,
                                                   不像 commit 只取 failures[0] —— 计划 §03 行为表)
- test_main_returns_1_on_gate_failure              rc 映射半边: main([]) 实测失败 → rc 1(恒 0 回归
                                                   时结果行用例救不了退出码)(分面 2)
- test_pack_config_passes_config_problems          真实 .my-commit-flow.toml 装载自检: when_message
                                                   新键在 GATE_KEYS 白名单 + bool 校验零 STOP
- test_when_message_type_invalid_stops             bool 校验半边独立钉住: when_message 写成字符串
                                                   → config_problems STOP(删 isinstance 检查即红)(分面 2)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gate as gate_mod  # noqa: E402
from _ship_config import config_problems, load_config  # noqa: E402

PKG = Path(__file__).resolve().parent.parent


class _GateSpy:
    """run_gates 替身: 记下 (hits, ctx) 供断言, 返回预置结果。"""
    def __init__(self, failures=(), manual=(), ran=0):
        self.failures = list(failures)
        self.manual = list(manual)
        self.ran = ran
        self.calls: list[tuple[list, dict]] = []

    def __call__(self, hits, ctx):
        self.calls.append((list(hits), dict(ctx)))
        return list(self.failures), list(self.manual), self.ran


@pytest.fixture()
def repo(tmp_path, monkeypatch):
    """最小工作仓(只要 .git 目录在 —— changed_files / run_gates 全替身, 不跑真 git)。"""
    monkeypatch.setenv("COMMAND_FLOW_PACK_DIR", str(PKG))
    r = tmp_path / "r"
    (r / ".git").mkdir(parents=True)
    monkeypatch.chdir(r)
    monkeypatch.setattr(gate_mod, "find_root", lambda: r)
    return r


def _patch_changed(monkeypatch, staged=(), unstaged=()):
    monkeypatch.setattr(gate_mod, "changed_files", lambda: (list(staged), list(unstaged)))


def _patch_cfg(monkeypatch, **overrides):
    """装载真实包配置再按需改 gates —— 保证 config_stops 对真实键集放行, 只钉住被测语义。"""
    cfg, src = load_config()
    for key, value in overrides.items():
        cfg[key] = value
    monkeypatch.setattr(gate_mod, "load_config", lambda: (cfg, src))
    return cfg


def _gate(name: str, when_message=False):
    g = {"match": [""], "run": ["echo hi"], "auto": True, "timeout": 60, "note": name}
    if when_message:
        g["when_message"] = True
    return g


def _write_msg(repo: Path) -> Path:
    # 内容 gate.py 不读(它只判 exists 并把路径递给 review.trace)—— 不用 gitmoji, 免 ASCII 守卫摩擦
    # (test_commit.py 的 gitmoji 走的是「功能性数据」整文件豁免, 这里没有断言它的必要)。
    msg = repo / ".git" / "COMMIT_MSG_AI.txt"
    msg.write_text("中文测试消息\n", encoding="utf-8")
    return msg


# ------------------------------------------------------------------ 入口契约


def test_safety_probe_declares_action_without_args(capsys):
    rc = gate_mod.main(["--safety"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "action-without-args" in out  # 冒烟闸门据此摘除: 无参跑 fmt 真改文件


def test_explicit_empty_argv_enters_prerun(repo, monkeypatch, capsys):
    # 显式空表 = 测试裸调动作入口: 不吃调用方 sys.argv, 真的下沉到预跑主体(sync.py 2026-10-03 判据)。
    _patch_changed(monkeypatch)  # 树净
    _patch_cfg(monkeypatch)
    rc = gate_mod.main([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "树净" in out


# ------------------------------------------------------------------ 预跑主体语义


def test_clean_tree_reports_nothing_to_run(repo, monkeypatch, capsys):
    _patch_changed(monkeypatch)
    _patch_cfg(monkeypatch)
    spy = _GateSpy()
    monkeypatch.setattr(gate_mod, "run_gates", spy)
    ok, line, detail = gate_mod.run_gate_prerun([])
    assert ok and not detail
    assert "树净" in line and "ship.commit" in line
    assert spy.calls == []  # 树净不碰闸门


def test_config_stop_fails_fast(repo, monkeypatch, capsys):
    _patch_changed(monkeypatch, staged=["src/a.py"])
    cfg, src = load_config()
    bad = dict(cfg, gates=[{**cfg["gates"][0], "unknown_key": True}])
    monkeypatch.setattr(gate_mod, "load_config", lambda: (bad, src))
    spy = _GateSpy()
    monkeypatch.setattr(gate_mod, "run_gates", spy)
    ok, line, detail = gate_mod.run_gate_prerun([])
    assert not ok and not detail
    assert "配置错误" in line and "unknown_key" in line
    assert spy.calls == []


def test_red_lines_warn_only_gates_still_run(repo, monkeypatch, capsys):
    (repo / "config.yml").write_text("x\n", encoding="utf-8")
    (repo / "src").mkdir()
    (repo / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
    _patch_changed(monkeypatch, staged=["config.yml", "src/a.py"])
    _patch_cfg(monkeypatch)
    spy = _GateSpy(ran=1)
    monkeypatch.setattr(gate_mod, "run_gates", spy)
    ok, line, _ = gate_mod.run_gate_prerun([])
    out = capsys.readouterr().out
    assert ok and "闸门全绿" in line
    assert "WARN: 红线命中" in out and "config.yml" in out  # 只提示(拍板 D6)
    assert spy.calls and "src/a.py" in spy.calls[0][1]["changed"]  # 闸门照跑


def test_warn_lines_note_only_gates_still_run(repo, monkeypatch, capsys):
    # warn_lines 半边(分面 2 发现 1): 「人工确认项」打行分支独立于红线, 回归(循环被删/键名改错)时
    # 红线用例救不了它 —— 预跑会静默丢人工确认项提示。
    (repo / "src").mkdir()
    (repo / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
    _patch_changed(monkeypatch, staged=["src/a.py"])
    _patch_cfg(monkeypatch, warn_lines=["src/"])
    spy = _GateSpy(ran=1)
    monkeypatch.setattr(gate_mod, "run_gates", spy)
    ok, line, _ = gate_mod.run_gate_prerun([])
    out = capsys.readouterr().out
    assert ok and "闸门全绿" in line
    assert "WARN: 人工确认项" in out and "src/a.py" in out  # 只提示不拦
    assert spy.calls and "src/a.py" in spy.calls[0][1]["changed"]  # 闸门照跑


def test_present_filters_vanished_paths(repo, monkeypatch, capsys):
    # 纯删除提交的典型面: 工作区已不存在的路径不进 present(与 commit 同口径)。
    (repo / "kept.txt").write_text("x\n", encoding="utf-8")  # 在世文件; gone.txt 刻意不存在
    _patch_changed(monkeypatch, staged=["gone.txt", "kept.txt"])
    _patch_cfg(
        monkeypatch, gates=[{
            "match": ["src/"],
            "run": ["echo hi"],
            "auto": True,
            "timeout": 60,
            "note": "路径闸门"
        }]
    )
    spy = _GateSpy(ran=0)
    monkeypatch.setattr(gate_mod, "run_gates", spy)
    ok, line, _ = gate_mod.run_gate_prerun([])
    assert ok and "无闸门命中" in line  # gone.txt 不算数, kept.txt 不命中 src/ → 零命中
    assert spy.calls == []
    # 空串 match 闸门在纯删除面上仍命中(与 commit 的 gates_for 语义一致), ctx 只带在世路径。
    _patch_cfg(monkeypatch, gates=[_gate("全局闸门")])
    spy2 = _GateSpy(ran=0)
    monkeypatch.setattr(gate_mod, "run_gates", spy2)
    ok2, line2, _ = gate_mod.run_gate_prerun([])
    assert ok2 and "无闸门命中" not in line2
    assert spy2.calls and spy2.calls[0][1]["changed"] == ["kept.txt"]


def test_when_message_skipped_without_msg(repo, monkeypatch, capsys):
    monkeypatch.delenv("COMMIT_FLOW_MSG_FILE", raising=False)  # 防 ambient 残留干扰断言
    _patch_changed(monkeypatch, staged=["memory-bank/x.md"])
    _patch_cfg(monkeypatch, gates=[_gate("评审留痕", when_message=True), _gate("其他闸门")])
    spy = _GateSpy(ran=1)
    monkeypatch.setattr(gate_mod, "run_gates", spy)
    ok, line, _ = gate_mod.run_gate_prerun([])
    out = capsys.readouterr().out
    assert ok and "闸门全绿" in line
    assert "(略过 1 条)" in line  # 成行口径: 略过条数进结果行(计划 §03)
    assert "[预跑] 略过 1 条消息依赖闸门" in out and "评审留痕" in out
    assert "COMMIT_FLOW_MSG_FILE" not in os.environ  # 消息不在, 不设环境变量
    assert [g["note"] for g in spy.calls[0][0]] == ["其他闸门"]  # when_message 被摘除, 其余照跑


def test_when_message_runs_with_msg(repo, monkeypatch, capsys):
    msg = _write_msg(repo)
    monkeypatch.delenv("COMMIT_FLOW_MSG_FILE", raising=False)
    _patch_changed(monkeypatch, staged=["memory-bank/x.md"])
    _patch_cfg(monkeypatch, gates=[_gate("评审留痕", when_message=True)])
    spy = _GateSpy(ran=1)
    monkeypatch.setattr(gate_mod, "run_gates", spy)
    ok, line, _ = gate_mod.run_gate_prerun([])
    out = capsys.readouterr().out
    assert ok and "闸门全绿" in line
    assert "略过" not in out  # 消息在, 不打略过行
    assert os.environ.get("COMMIT_FLOW_MSG_FILE") == str(msg)  # 照 commit.py:515 注入生效路径
    assert spy.calls[0][0][0]["note"] == "评审留痕"  # 原样保留(提前发现忘写 trailer)


def test_no_hits_reports_no_gate(repo, monkeypatch, capsys):
    _patch_changed(monkeypatch, staged=["memory-bank/x.md"])
    _patch_cfg(monkeypatch, gates=[_gate("评审留痕", when_message=True)])
    spy = _GateSpy()
    monkeypatch.setattr(gate_mod, "run_gates", spy)
    ok, line, _ = gate_mod.run_gate_prerun([])  # 消息缺失 → 唯一闸门被摘 → 零命中
    assert ok
    assert "无闸门命中" in line
    assert spy.calls == []


def test_success_one_line(repo, monkeypatch, capsys):
    _patch_changed(monkeypatch, staged=["src/a.py"])
    _patch_cfg(monkeypatch, gates=[_gate("甲"), _gate("乙")])
    spy = _GateSpy(ran=3)
    monkeypatch.setattr(gate_mod, "run_gates", spy)
    ok, line, detail = gate_mod.run_gate_prerun([])
    assert ok and not detail
    assert line.startswith("闸门全绿: 命中 2 条, 执行 3 条命令")
    assert "(略过 0 条)" in line  # 成行口径恒带略过位(计划 §03, 零略过也如实显示)
    assert "贴进评审记录" in line  # 结果行就是要贴进评审记录的那个值


def test_manual_gates_reported(repo, monkeypatch, capsys):
    _patch_changed(monkeypatch, staged=["src/a.py"])
    _patch_cfg(monkeypatch, gates=[_gate("甲")])
    spy = _GateSpy(manual=["cmd-a", "cmd-b"], ran=0)
    monkeypatch.setattr(gate_mod, "run_gates", spy)
    ok, _line, _ = gate_mod.run_gate_prerun([])
    out = capsys.readouterr().out
    assert ok and "人工闸门" in out and "cmd-a" in out


def test_failures_list_all_after_result_line(repo, monkeypatch, capsys):
    _patch_changed(monkeypatch, staged=["src/a.py"])
    _patch_cfg(monkeypatch, gates=[_gate("甲"), _gate("乙")])
    fails = [("甲", "cmd-a", 1, 1.5, "boom-a"), ("乙", "cmd-b", -2, 0.0, "boom-b")]
    spy = _GateSpy(failures=fails)
    monkeypatch.setattr(gate_mod, "run_gates", spy)
    ok, line, detail = gate_mod.run_gate_prerun([])
    assert not ok and detail
    assert "2 条未过" in line and "ship.gate" in line
    text = "\n".join(detail)
    # 全量明细(不像 commit 只取 failures[0]): 两条都在, 各带闸门名/rc/命令
    assert "「甲」" in text and "「乙」" in text
    assert "(rc=1, 1.5s)" in text and "(rc=-2, 0.0s)" in text
    assert "$ cmd-a" in text and "$ cmd-b" in text and "boom-a" in text


def test_main_returns_1_on_gate_failure(repo, monkeypatch, capsys):
    # rc 映射半边(分面 2 发现 2): main 的 `0 if ok else 1` 回归成恒 0 时, 闸门红会被当成功 ——
    # 结果行/明细用例救不了退出码, 必须 main([]) 实测。
    _patch_changed(monkeypatch, staged=["src/a.py"])
    _patch_cfg(monkeypatch, gates=[_gate("甲")])
    spy = _GateSpy(failures=[("甲", "cmd-a", 1, 1.0, "boom-a")])
    monkeypatch.setattr(gate_mod, "run_gates", spy)
    rc = gate_mod.main([])
    out = capsys.readouterr().out
    assert rc == 1
    assert "闸门预跑失败" in out and "boom-a" in out


# ------------------------------------------------------------------ 真实包装载自检


def test_pack_config_passes_config_problems(monkeypatch):
    # when_message 新键守阵: 真实 .my-commit-flow.toml 装载后 config_problems 零 STOP ——
    # 缺 GATE_KEYS 白名单/bool 校验时, 这条会在提交闸门撞墙之前先红(闸门键 STOP 会挡一切提交)。
    # ! 必须钉 PKG: commands 引擎调 task 时注入的 COMMAND_FLOW_PACK_DIR 是 **task 所在包**
    #   (pkg_scoped 上下文 = .commands/test), 不钉就会把配置源指到别家包(test_commit 夹具同款处置)。
    monkeypatch.setenv("COMMAND_FLOW_PACK_DIR", str(PKG))
    cfg, src = load_config()
    stops = [msg for lvl, msg in config_problems(cfg, src) if lvl == "STOP"]
    assert stops == []
    review_trace = [g for g in cfg["gates"] if "review.trace" in "".join(g.get("run", []))]
    assert review_trace and review_trace[0].get("when_message") is True


def test_when_message_type_invalid_stops(repo, monkeypatch):
    # bool 校验半边(分面 2 发现 3): isinstance 检查整个删掉这条仍要红 —— 字符串 "false" 是真值,
    # meant-false 的闸门会被预跑**错误略过**(注释与实现靠这条对齐)。
    monkeypatch.setenv("COMMAND_FLOW_PACK_DIR", str(PKG))
    cfg, src = load_config()
    bad = dict(cfg, gates=[{**cfg["gates"][0], "when_message": "false"}])
    stops = [msg for lvl, msg in config_problems(bad, src) if lvl == "STOP"]
    assert any("when_message" in m and "false" in m for m in stops)
