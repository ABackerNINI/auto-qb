"""commit.py 零参数化 + 自动续推守阵(计划 26-09-26-2345 P2/P3) —— 不碰真实 git: 全部 monkeypatch。

## 测试计划
- test_default_paths_full_changed      缺省(零参数) = changed_files() 全量改动
- test_default_rejects_red_lines       缺省模式下红线文件在改动清单 → 拒绝
- test_subset_reports_omitted          传路径 = 子集提交, 返回未纳入清单(治「漏传静默不提交」)
- test_bulk_tokens_refused             -A / . / * 照旧拒绝
- test_message_default_path            缺省消息路径 = <root>/.git/COMMIT_MSG_AI.txt
- test_message_missing_gives_next      消息缺失 → RESULT: FAIL + 指明约定路径的 NEXT, 不碰 preflight
- test_commit_chains_push_and_reports_ok  提交成功后同进程续跑 push(emit_result=False), RESULT: OK
- test_push_failure_is_partial         push 失败 → RESULT: PARTIAL + NEXT 补推, 退出码仍 0(别重提交)
- test_no_push_stops_before_push       --no-push 不碰 push.main, RESULT: OK 标明未推送
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import commit as commit_mod  # noqa: E402
import push as push_mod  # noqa: E402
import verify_ref as verify_ref_mod  # noqa: E402

PKG = Path(__file__).resolve().parent.parent
RED = ["config.yml", "auto-qb-data/"]


def _changed(staged: list[str], unstaged: list[str]):
    return lambda: (staged, unstaged)


def test_default_paths_full_changed(monkeypatch):
    monkeypatch.setattr(commit_mod, "changed_files", _changed(["src/a.py"], ["tests/test_a.py"]))
    to_stage, omitted, refuse = commit_mod.resolve_stage_plan([], RED)
    assert refuse is None
    assert to_stage == ["src/a.py", "tests/test_a.py"]
    assert omitted == []


def test_default_rejects_red_lines(monkeypatch):
    monkeypatch.setattr(commit_mod, "changed_files", _changed(["config.yml"], ["src/a.py"]))
    to_stage, omitted, refuse = commit_mod.resolve_stage_plan([], RED)
    assert to_stage == [] and omitted == []
    assert refuse is not None and "config.yml" in refuse


def test_subset_reports_omitted(monkeypatch):
    monkeypatch.setattr(commit_mod, "changed_files", _changed(["src/a.py", "src/b.py"], []))
    to_stage, omitted, refuse = commit_mod.resolve_stage_plan(["src/a.py"], RED)
    assert refuse is None
    assert to_stage == ["src/a.py"]
    assert omitted == ["src/b.py"]


def test_bulk_tokens_refused(monkeypatch):
    monkeypatch.setattr(commit_mod, "changed_files", _changed(["src/a.py"], []))
    for token in ("-A", ".", "*"):
        _, _, refuse = commit_mod.resolve_stage_plan([token], RED)
        assert refuse is not None and "批量" in refuse


def test_message_default_path(tmp_path):
    assert commit_mod.default_message_path(tmp_path) == tmp_path / ".git" / "COMMIT_MSG_AI.txt"


def test_message_missing_gives_next(monkeypatch, capsys, tmp_path):
    # 引擎跑 test.pkg 时注入的是 **test 包**的 COMMAND_FLOW_PACK_DIR —— 钉回本包,
    # load_config 才能找到 .my-commit-flow.toml(生产路径下引擎给 ship.commit 注入的本来就是本包目录)。
    monkeypatch.setenv("COMMAND_FLOW_PACK_DIR", str(Path(__file__).resolve().parent.parent))
    monkeypatch.setattr(commit_mod, "find_root", lambda: tmp_path)
    monkeypatch.setattr(commit_mod, "changed_files", _changed(["src/a.py"], []))
    rc = commit_mod.main(["--skip-preflight"])
    err = capsys.readouterr().err
    assert rc == 4
    assert "RESULT: FAIL 提交消息文件不存在" in err
    assert ".git" in err and "COMMIT_MSG_AI.txt" in err  # 指明约定路径
    assert "NEXT: 把提交消息" in err
    assert "重跑 commands run ship.commit" in err


def _patch_happy_path(monkeypatch, tmp_path):
    """提交成功路径的全套替身: 改动清单 / git / ref 核对, 消息文件落在 tmp 的 .git 里。"""
    monkeypatch.setenv("COMMAND_FLOW_PACK_DIR", str(PKG))
    monkeypatch.setattr(commit_mod, "find_root", lambda: tmp_path)
    monkeypatch.setattr(commit_mod, "changed_files", _changed(["src/a.py"], []))
    monkeypatch.setattr(commit_mod, "git", lambda *a: subprocess.CompletedProcess(a, 0, "ok\n", ""))
    monkeypatch.setattr(
        commit_mod.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess([], 0, "src/a.py\n", "")
    )
    monkeypatch.setattr(verify_ref_mod, "main", lambda argv=None: 0)
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "COMMIT_MSG_AI.txt").write_text("✨ test", encoding="utf-8")


def test_commit_chains_push_and_reports_ok(monkeypatch, capsys, tmp_path):
    _patch_happy_path(monkeypatch, tmp_path)
    seen = {}

    def fake_push(argv=None, emit_result=True):
        seen["emit_result"] = emit_result
        return 0

    monkeypatch.setattr(push_mod, "main", fake_push)
    rc = commit_mod.main(["--skip-preflight"])
    out = capsys.readouterr()
    assert rc == 0
    assert seen["emit_result"] is False  # 链跑时关掉 push 自己的协议行, 统一结论由 commit 出
    assert "RESULT: OK ok 已提交(1 个文件)并推送" in out.out


def test_push_failure_is_partial(monkeypatch, capsys, tmp_path):
    _patch_happy_path(monkeypatch, tmp_path)
    monkeypatch.setattr(push_mod, "main", lambda argv=None, emit_result=True: 5)
    rc = commit_mod.main(["--skip-preflight"])
    out = capsys.readouterr()
    assert rc == 0  # 提交这个主目标已达成 —— 补推即可, 别重提交
    assert "RESULT: PARTIAL" in out.err
    assert "NEXT: commands run ship.push" in out.err


def test_no_push_stops_before_push(monkeypatch, capsys, tmp_path):
    _patch_happy_path(monkeypatch, tmp_path)

    def _must_not_run(*a, **k):
        raise AssertionError("--no-push 不该续跑推送")

    monkeypatch.setattr(push_mod, "main", _must_not_run)
    rc = commit_mod.main(["--skip-preflight", "--no-push"])
    out = capsys.readouterr()
    assert rc == 0
    assert "RESULT: OK ok 已提交(1 个文件, --no-push 未推送)" in out.out
