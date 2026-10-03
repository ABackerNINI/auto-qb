"""commit.py v3 守阵 —— 编排合一 + 一行输出契约。真实临时仓库测 git 路径, 外部依赖(sync/闸门/push)替身。

## 测试计划
- test_stage_plan_*                       暂存计划: 全量 / 子集(omitted 可见) / 拒批量 / 红线 / 空改动
- test_message_default_path               约定消息路径 = <root>/.git/COMMIT_MSG_AI.txt
- test_message_missing_fails_early        消息缺失 → 提交失败一行, 不碰 git 写操作
- test_full_commit_push_one_line          全流程成功 → 恰好一行「提交成功 <hash>」; 消息文件消费即删
- test_staged_delete_skips_add            已暂存的删除: 逐路径 add 不再撞 pathspec 落空(issue 26-09-28-0128)
- test_unstaged_delete_uses_rm_cached     未暂存的删除: 工作区无而索引有 → rm --cached 登记删除(issue 26-09-28-0128)
- test_sync_failure_blocks_commit         未与主线同步 → 提交失败 + sync 失败详情, 不产生提交
- test_dirty_sync_failure_warns_deadlock  树脏类同步失败 → 附死锁护栏行(别再「先跑 sync / 先提交」)
- test_clean_sync_failure_no_deadlock_note 非脏类同步失败(离线) → 不附护栏行, 免误导
- test_gate_failure_blocks_commit         闸门红 → 提交失败 + 闸门名 + 失败输出, 不产生提交
- test_push_failure_is_partial            推送未完成 → 退出码仍 0 + 补推提示; 消息文件照常消费
- test_no_push_stops_before_push          --no-push 不碰 push, 一行注明未推送
- test_warn_lines_note_on_success         warn_lines 命中 → 成功路径附一行 ⚠(唯一例外, D5)
- test_message_kept_on_commit_fail        git commit 失败 → 消息文件保留
- test_message_kept_on_verify_fail        ref 核对失败 → 消息文件保留
- test_check_refs_pass_on_fresh_repo      ref 三处核对在干净仓库通过
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import commit as commit_mod  # noqa: E402
import push as push_mod  # noqa: E402
import sync as sync_mod  # noqa: E402
import verify_ref as verify_ref_mod  # noqa: E402

PKG = Path(__file__).resolve().parent.parent
RED = ["config.yml", "auto-qb-data/"]


def _git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, f"git {' '.join(args)} 失败: {proc.stderr}"
    return proc.stdout.strip()


def _commit_file(repo: Path, name: str, content: str, msg: str) -> None:
    (repo / name).write_text(content, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", msg)


@pytest.fixture()
def repo(tmp_path, monkeypatch):
    """带 bare 远端的工作仓(已推送 base 提交); cwd 钉在仓内, find_root 钉到仓根。"""
    monkeypatch.setenv("COMMAND_FLOW_PACK_DIR", str(PKG))
    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "--bare", "-b", "develop", origin.name)
    a = tmp_path / "a"
    _git(tmp_path, "init", "-b", "develop", "a")
    _git(a, "config", "user.email", "t@t")
    _git(a, "config", "user.name", "t")
    _commit_file(a, "base.txt", "base\n", "base")
    _git(a, "remote", "add", "origin", str(origin))
    _git(a, "push", "-u", "origin", "develop")
    monkeypatch.chdir(a)
    monkeypatch.setattr(commit_mod, "find_root", lambda: a)
    return a


def _patch_ok_flow(monkeypatch):
    """成功路径的外部替身: 同步齐平 / 闸门全过 / ref 一致 / 推送成功(镜像静默在 push 内)。"""
    monkeypatch.setattr(sync_mod, "run_sync", lambda: (True, "已同步 abcdef01"))
    monkeypatch.setattr(commit_mod, "run_gates", lambda hits, ctx: ([], [], 0))
    monkeypatch.setattr(commit_mod, "check_refs", lambda expect="": (True, []))
    monkeypatch.setattr(push_mod, "run_push", lambda: (True, "推送成功 abcdef01"))


def _write_msg(repo: Path, text: str = "✨ test") -> Path:
    msg = repo / ".git" / "COMMIT_MSG_AI.txt"
    msg.write_text(text, encoding="utf-8")
    return msg


# ------------------------------------------------------------------ 暂存计划(纯函数)


def test_stage_plan_full_changed():
    to_stage, omitted, refuse = commit_mod.resolve_stage_plan([], RED, ["src/a.py"], ["tests/t.py"])
    assert refuse is None and to_stage == ["src/a.py", "tests/t.py"] and omitted == []


def test_stage_plan_subset_reports_omitted():
    to_stage, omitted, refuse = commit_mod.resolve_stage_plan(["src/a.py"], RED, ["src/a.py", "src/b.py"], [])
    assert refuse is None and to_stage == ["src/a.py"] and omitted == ["src/b.py"]


def test_stage_plan_bulk_refused():
    for token in ("-A", ".", "*"):
        _, _, refuse = commit_mod.resolve_stage_plan([token], RED, ["src/a.py"], [])
        assert refuse and "批量" in refuse


def test_stage_plan_red_lines_refused():
    _, _, refuse = commit_mod.resolve_stage_plan([], RED, ["config.yml"], ["src/a.py"])
    assert refuse and "config.yml" in refuse


def test_stage_plan_nothing_to_commit():
    _, _, refuse = commit_mod.resolve_stage_plan([], RED, [], [])
    assert refuse and "没有可提交的改动" in refuse


def test_message_default_path(tmp_path):
    assert commit_mod.default_message_path(tmp_path) == tmp_path / ".git" / "COMMIT_MSG_AI.txt"


# ------------------------------------------------------------------ 真实仓库路径


def test_message_missing_fails_early(repo, monkeypatch, capsys):
    monkeypatch.setattr(sync_mod, "run_sync", lambda: (True, "已同步 abcdef01"))
    (repo / "x.txt").write_text("x\n", encoding="utf-8")  # 有改动才走得到消息检查
    rc = commit_mod.main([])
    out = capsys.readouterr().out
    assert rc == 1
    assert "提交失败: 提交消息文件不存在" in out and ".git" in out and "COMMIT_MSG_AI.txt" in out


def test_full_commit_push_one_line(repo, monkeypatch, capsys):
    _patch_ok_flow(monkeypatch)
    msg = _write_msg(repo)
    (repo / "x.txt").write_text("x\n", encoding="utf-8")
    rc = commit_mod.main([])
    out = capsys.readouterr().out
    assert rc == 0
    assert re.fullmatch(r"提交成功 [0-9a-f]{8}\n", out), f"成功必须恰好一行, 实际: {out!r}"
    assert not msg.exists()  # 消费即删: 提交落稳后不残留旧消息


def test_staged_delete_skips_add(repo, monkeypatch, capsys):
    # issue 26-09-28-0128: 删除进暂存区后, 该路径工作区与索引都不复存在 ——
    # 旧实现逐路径 add 撞 "pathspec did not match"; v3 按 (存在? add : (索引里? rm --cached : 跳过)) 分流。
    _patch_ok_flow(monkeypatch)
    _git(repo, "rm", "base.txt")  # 删除已进暂存区
    msg = _write_msg(repo)
    rc = commit_mod.main([])
    out = capsys.readouterr().out
    assert rc == 0 and "提交成功" in out
    assert not msg.exists()
    assert _git(repo, "show", "--stat", "--name-status", "HEAD").count("D") >= 1  # 删除真的进了提交


def test_unstaged_delete_uses_rm_cached(repo, monkeypatch, capsys):
    # issue 26-09-28-0128 方向 A 的另一半: 未暂存删除( D)时工作区已无该文件而索引还有条目 ——
    # 逐路径暂存按存在性分流走 `git rm --cached`, 把删除登记进暂存区后照常提交。
    _patch_ok_flow(monkeypatch)
    (repo / "base.txt").unlink()  # 只删工作区, 不进暂存区(porcelain 形态 ` D`)
    msg = _write_msg(repo)
    rc = commit_mod.main([])
    out = capsys.readouterr().out
    assert rc == 0 and "提交成功" in out
    assert not msg.exists()
    assert _git(repo, "show", "--stat", "--name-status", "HEAD").count("D") >= 1  # 删除经 rm --cached 进了提交


def _dirty_sync_line() -> str:
    """树脏类同步失败行(与 sync.py 真机输出同形态) —— 含解锁配方, 会被 is_dirty_block 认出。"""
    return (f"{sync_mod.DIRTY_BLOCK_MARK} 本地12345678 远端87654321 —— 本地改动与远端新提交重叠; "
            f"解锁: {sync_mod.UNLOCK_STEPS}")


def test_sync_failure_blocks_commit(repo, monkeypatch, capsys):
    monkeypatch.setattr(sync_mod, "run_sync", lambda: (False, _dirty_sync_line()))
    msg = _write_msg(repo)
    (repo / "x.txt").write_text("x\n", encoding="utf-8")
    rc = commit_mod.main([])
    out = capsys.readouterr().out
    assert rc == 1
    assert "提交失败: 未与主线同步" in out
    assert "重叠" in out  # sync 的一行原因透传
    assert msg.exists()  # 未提交, 消息照常保留
    assert _git(repo, "status", "--porcelain").count("x.txt") == 1  # 未产生任何提交/暂存


def test_dirty_sync_failure_warns_deadlock(repo, monkeypatch, capsys):
    """树脏类失败必须点破死锁(2026-10-03): 单独重跑 sync / 「先提交」都进不去, 只能 stash 解锁。"""
    monkeypatch.setattr(sync_mod, "run_sync", lambda: (False, _dirty_sync_line()))
    _write_msg(repo)
    (repo / "x.txt").write_text("x\n", encoding="utf-8")
    rc = commit_mod.main([])
    out = capsys.readouterr().out
    assert rc == 1
    assert "解锁" in out and "git stash push -u" in out and "git stash pop" in out  # 配方完整透传
    assert "本命令内部那一步" in out  # 死锁护栏行: 这条 sync 就是 submit 内部那一步
    assert "先跑 commands run my-commit-flow.sync 后重跑" not in out  # 旧提示会让人原地转圈


def test_clean_sync_failure_no_deadlock_note(repo, monkeypatch, capsys):
    monkeypatch.setattr(sync_mod, "run_sync", lambda: (False, "拿不到远端 origin/develop (离线?) —— 联网后重跑"))
    _write_msg(repo)
    (repo / "x.txt").write_text("x\n", encoding="utf-8")
    rc = commit_mod.main([])
    out = capsys.readouterr().out
    assert rc == 1
    assert "本命令内部那一步" not in out  # 离线不是脏类, 别拿 stash 配方误导


def test_gate_failure_blocks_commit(repo, monkeypatch, capsys):
    monkeypatch.setattr(sync_mod, "run_sync", lambda: (True, "已同步 abcdef01"))
    monkeypatch.setattr(
        commit_mod, "run_gates", lambda hits, ctx: ([("测试闸门", "pytest -q", 1, 0.4, "boom\nE   assert False")], [], 1)
    )
    _write_msg(repo)
    (repo / "x.txt").write_text("x\n", encoding="utf-8")
    rc = commit_mod.main([])
    out = capsys.readouterr().out
    assert rc == 1
    assert "提交失败: 闸门「测试闸门」未过" in out
    assert "boom" in out and "pytest -q" in out  # 命令 + 末 20 行都在
    assert _git(repo, "status", "--porcelain").count("x.txt") == 1  # 未产生提交


def test_push_failure_is_partial(repo, monkeypatch, capsys):
    _patch_ok_flow(monkeypatch)
    monkeypatch.setattr(push_mod, "run_push", lambda: (False, "主线推送未通过 —— rejected"))
    msg = _write_msg(repo)
    (repo / "x.txt").write_text("x\n", encoding="utf-8")
    rc = commit_mod.main([])
    out = capsys.readouterr().out
    assert rc == 0  # 提交这个主目标已达成 —— 补推即可, 别重提交
    assert "提交成功" in out and "未推送" in out
    assert "推送未完成: 主线推送未通过" in out and "commands run ship.push" in out
    assert not msg.exists()  # 提交已落稳(ref 通过), 消息照常消费


def test_no_push_stops_before_push(repo, monkeypatch, capsys):
    _patch_ok_flow(monkeypatch)

    def _must_not_run():
        raise AssertionError("--no-push 不该续跑推送")

    monkeypatch.setattr(push_mod, "run_push", _must_not_run)
    msg = _write_msg(repo)
    (repo / "x.txt").write_text("x\n", encoding="utf-8")
    rc = commit_mod.main(["--no-push"])
    out = capsys.readouterr().out
    assert rc == 0
    assert re.fullmatch(r"提交成功 [0-9a-f]{8}\(未推送 —— 补推: commands run ship\.push\)\n", out)
    assert not msg.exists()  # --no-push 也算提交落稳, 照样消费


def test_warn_lines_note_on_success(repo, monkeypatch, capsys):
    _patch_ok_flow(monkeypatch)
    _write_msg(repo)
    (repo / "想法.md").write_text("在途想法\n", encoding="utf-8")  # 真实配置的 warn_lines 命中
    rc = commit_mod.main([])
    out = capsys.readouterr().out
    assert rc == 0
    assert any(l.startswith("⚠ 已包含: 想法.md") for l in out.splitlines())  # 成功路径唯一例外(D5)


def test_message_kept_on_commit_fail(repo, monkeypatch, capsys):
    _patch_ok_flow(monkeypatch)
    msg = _write_msg(repo)
    (repo / "x.txt").write_text("x\n", encoding="utf-8")
    # 让 commit 必败: 消息指向已被删除的路径之外 —— 用空消息文件让 git 拒绝(无换行的空消息)
    msg.write_text("", encoding="utf-8")
    rc = commit_mod.main([])
    out = capsys.readouterr().out
    assert rc == 1
    assert "提交失败: git commit 未通过" in out
    assert msg.exists()  # 未消费: 修好后重跑还能用同一份消息


def test_message_kept_on_verify_fail(repo, monkeypatch, capsys):
    _patch_ok_flow(monkeypatch)
    monkeypatch.setattr(
        commit_mod, "check_refs", lambda expect="": (False, ["  HEAD         deadbeef", "[STOP] ref 不一致"])
    )
    msg = _write_msg(repo)
    (repo / "x.txt").write_text("x\n", encoding="utf-8")
    rc = commit_mod.main([])
    out = capsys.readouterr().out
    assert rc == 1
    assert "ref 三处不一致" in out
    assert msg.exists()  # 提交可能没落稳: 保留现场不消费


def test_check_refs_pass_on_fresh_repo(repo, monkeypatch):
    monkeypatch.setattr(verify_ref_mod, "REPO", repo)
    ok, detail = verify_ref_mod.check_refs()
    assert ok and detail == []
