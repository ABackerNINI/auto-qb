"""commit.py 守阵 —— 编排合一 + 一行输出契约。真实临时仓库测 git 路径, 外部依赖按需替身:
闸门 / push 一律替身; 同步在编排语义用例里替身, 在真仓场景用例里真跑(见 2026-10-04 提交先行节)。

## 测试计划
- test_stage_plan_*                       暂存计划: 全量 / 子集(omitted 可见) / 拒批量 / 红线 / 空改动
- test_message_default_path               约定消息路径 = <root>/.git/COMMIT_MSG_AI.txt
- test_message_missing_fails_early        消息缺失 → 提交失败一行, 不碰 git 写操作
- test_full_commit_push_one_line          全流程无合流 → 零步骤行, 结果独占一行「提交成功 <hash>」; 消息文件消费即删
- test_staged_delete_skips_add            已暂存的删除: 逐路径 add 不再撞 pathspec 落空(issue 26-09-28-0128)
- test_unstaged_delete_uses_rm_cached     未暂存的删除: 工作区无而索引有 → rm --cached 登记删除(issue 26-09-28-0128)
- test_sync_offline_after_commit_partial  提交先行: 同步失败(离线)在提交落稳之后 → 推送未完成, 退出码 0
- test_sync_conflict_line_passthrough     冲突类失败行原样透传(约定模板无缝拼接), 不再附死锁护栏
- test_remote_moved_rebases_before_push   真仓: 远端前移 → 提交后 rebase 保线性, 结果行报改写后的新 hash(上方留 rebase 步骤行)
- test_head_rewrite_trace_ends_at_result_hash  步骤链不变量: 链尾 == 结果行 hash · 相邻两步首尾相接 · 顺序在结果行上面
- test_remote_conflict_reports_partial    真仓: 同文件冲突 → rebase 自动回滚 → 提交成功(未推送) + 冲突模板
- test_post_rebase_gates_rerun_on_diverge 真仓: rebase 合入远端 → 闸门复跑一轮(共两轮, 同一清单)
- test_post_rebase_gate_red_blocks_push   真仓: 复跑红 → 推送未完成 + 修复指引, 不推送
- test_post_rebase_gate_dirty_amends      真仓: 复跑的 fmt 类闸门又改文件 → amend 折进未推送 tip
- test_post_rebase_pack_changed_leaves_hint 真仓: 合流改动了本包 → 登记一行「仍按启动版本运行, 重跑以采用新版本」
- test_gate_failure_blocks_commit         闸门红 → 提交失败 + 闸门名 + 失败输出, 不产生提交
- test_push_failure_is_partial            推送未完成 → 退出码仍 0 + 补推提示; 消息文件照常消费
- test_no_push_skips_sync_and_push        --no-push 不同步不推送(离线可用), 一行注明未推送
- test_warn_lines_note_on_success         warn_lines 命中 → 成功路径附一行 ⚠(唯一例外, D5)
- test_message_kept_on_commit_fail        git commit 失败 → 消息文件保留
- test_message_kept_on_verify_fail        ref 核对失败且 HEAD 消息与文件不匹配(ref 真丢) → 消息文件保留
- test_message_consumed_on_verify_fail_when_head_matches
                                          ref 核对失败但 HEAD 消息与文件一致( packed-refs 滞后类误报,
                                          2026-10-07 实证) → 提交已落稳, 照常消费不留残骸
- test_stale_message_residue_swept_at_entry
                                          入口残留扫描: 约定消息文件内容 == HEAD 消息(已落库漏删残骸,
                                          树净形态) → 删除 + 拒跑, 不产生新提交
- test_message_kept_when_nothing_to_commit
                                          树净且消息与 HEAD 不匹配(正常待提交消息) → 照旧拒绝, 文件保留
- test_check_refs_pass_on_fresh_repo      ref 三处核对在干净仓库通过
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import commit as commit_mod  # noqa: E402
import push as push_mod  # noqa: E402
import sync as sync_mod  # noqa: E402
import verify_ref as verify_ref_mod  # noqa: E402
from _pipeline import run_capture  # noqa: E402

PKG = Path(__file__).resolve().parent.parent
RED = ["config.yml", "auto-qb-data/"]


def _git(cwd: Path, *args: str) -> str:
    # 走 run_capture: 同批真实临时仓库用例共用防挂死入口(根因见 _pipeline.run_capture 注释)。
    proc = run_capture(["git", *args], cwd=cwd)
    assert proc.returncode == 0, f"git {' '.join(args)} 失败: {proc.stderr}"
    return proc.stdout.strip()


def _commit_file(repo: Path, name: str, content: str, msg: str) -> None:
    (repo / name).write_text(content, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", msg)


@pytest.fixture()
def repo(tmp_path, monkeypatch):
    """带 bare 远端的工作仓(已推送 base 提交); cwd 钉在仓内, find_root / verify_ref 钉到仓根。"""
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
    # 真 check_refs 用例需要: verify_ref 的 REPO / BRANCH 是 import 时定死的模块级值
    monkeypatch.setattr(verify_ref_mod, "REPO", a)
    monkeypatch.setattr(verify_ref_mod, "BRANCH", "develop")
    return a


def _push_remote_commit(repo: Path, tmp: Path, name: str, content: str, msg: str = "remote") -> None:
    """第二个工作仓 b: 模拟"别的 clone 推了新提交"(与 test_sync 同款)。"""
    b = tmp / "b"
    if not b.exists():
        _git(tmp, "clone", "-b", "develop", "origin.git", "b")
        _git(b, "config", "user.email", "t@t")
        _git(b, "config", "user.name", "t")
    target = b / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    _git(b, "add", "-A")
    _git(b, "commit", "-m", msg)
    _git(b, "push", "origin", "develop")


def _must_not_push(steps=None) -> None:
    raise AssertionError("不该走到推送")


def _patch_ok_flow(monkeypatch):
    """成功路径的外部替身: 同步齐平 / 闸门全过 / ref 一致 / 推送成功(镜像静默在 push 内)。"""
    monkeypatch.setattr(sync_mod, "run_sync", lambda steps=None: (True, "已同步 abcdef01"))
    monkeypatch.setattr(commit_mod, "run_gates", lambda hits, ctx: ([], [], 0))
    monkeypatch.setattr(commit_mod, "check_refs", lambda expect="": (True, []))
    monkeypatch.setattr(push_mod, "run_push", lambda steps=None: (True, "推送成功 abcdef01"))


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


def test_message_missing_fails_early(repo, capsys):
    (repo / "x.txt").write_text("x\n", encoding="utf-8")  # 有改动才走得到消息检查
    rc = commit_mod.main([])
    out = capsys.readouterr().out
    assert rc == 1
    assert "提交失败: 提交消息文件不存在" in out and ".git" in out and "COMMIT_MSG_AI.txt" in out


def _result(out: str) -> str:
    """成功/失败的结果行 —— 步骤行在它上面, 断言只看这最后一行(步骤守卫另有专测)。"""
    lines = out.strip().splitlines()
    assert lines, f"没有任何输出: {out!r}"
    return lines[-1]


def test_full_commit_push_one_line(repo, monkeypatch, capsys):
    _patch_ok_flow(monkeypatch)
    msg = _write_msg(repo)
    (repo / "x.txt").write_text("x\n", encoding="utf-8")
    rc = commit_mod.main([])
    out = capsys.readouterr().out
    assert rc == 0
    # 一路无合流 = 没有任何 HEAD 改写 = 零步骤行, 结果独占一行(v3.1 的「没发生的不报」)
    assert re.fullmatch(r"提交成功 [0-9a-f]{8}\n", out), f"无步骤时必须仍是一行, 实际: {out!r}"
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


# ------------------------------------------------------------------ 同步失败 = 推送未完成(2026-10-04 提交先行)


def test_sync_offline_after_commit_partial(repo, monkeypatch, capsys):
    """提交先行(2026-10-04): 同步失败发生在提交落稳之后 —— 按「推送未完成」处理, 不回滚提交。"""
    monkeypatch.setattr(sync_mod, "run_sync", lambda steps=None: (False, "拿不到远端 origin/develop (离线?) —— 联网后重跑"))
    monkeypatch.setattr(commit_mod, "run_gates", lambda hits, ctx: ([], [], 0))
    monkeypatch.setattr(push_mod, "run_push", _must_not_push)
    msg = _write_msg(repo)
    (repo / "x.txt").write_text("x\n", encoding="utf-8")
    rc = commit_mod.main([])
    out = capsys.readouterr().out
    assert rc == 0  # 提交这个主目标已达成 —— 别重新提交
    assert "提交成功" in out and "未推送" in out
    assert "推送未完成: 同步失败: 拿不到远端" in out and "commands run ship.push" in out
    assert not msg.exists()  # ref 核对已过, 消息照常消费
    assert "git stash push -u" not in out  # 离线不是脏类, 别拿 stash 配方误导
    assert "x.txt" in _git(repo, "show", "--name-only", "--format=", "HEAD")  # 提交在, 等补推


def test_sync_conflict_line_passthrough(repo, monkeypatch, capsys):
    """冲突类失败行原样透传, 与 sync.py main() 同一条拼接缝(「同步失败需解决冲突 …」无分隔冒号)。"""
    conflict_line = "需解决冲突 本地12345678 远端87654321 —— rebase 已自动回滚, 手动合流(解冲突)后重跑"
    monkeypatch.setattr(sync_mod, "run_sync", lambda steps=None: (False, conflict_line))
    monkeypatch.setattr(commit_mod, "run_gates", lambda hits, ctx: ([], [], 0))
    monkeypatch.setattr(push_mod, "run_push", _must_not_push)
    _write_msg(repo)
    (repo / "x.txt").write_text("x\n", encoding="utf-8")
    rc = commit_mod.main([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "提交成功" in out and "未推送" in out
    assert "推送未完成: 同步失败需解决冲突 本地12345678 远端87654321" in out  # 模板无缝拼接(v3 约定)
    assert "本命令内部那一步" not in out  # 旧死锁护栏已随提交先行退役


# ------------------------------------------------------------------ 真仓同步场景(rebase / 冲突 / 闸门复跑)


def test_remote_moved_rebases_before_push(repo, tmp_path, monkeypatch, capsys):
    """提交先行主路径: 远端前移 → 提交后 rebase 保线性, 成功行报改写后的新 hash。"""
    pushed = []
    monkeypatch.setattr(commit_mod, "run_gates", lambda hits, ctx: ([], [], 0))
    monkeypatch.setattr(push_mod, "run_push", lambda steps=None: pushed.append(1) or (True, "推送成功 abcdef01"))
    _write_msg(repo)
    (repo / "x.txt").write_text("x\n", encoding="utf-8")
    _push_remote_commit(repo, tmp_path, "b.txt", "b\n")  # 会话中途远端推进
    rc = commit_mod.main([])  # run_sync 不替身 —— 真跑(fetch + 提交后 rebase)
    out = capsys.readouterr().out
    assert rc == 0
    m = re.fullmatch(r"提交成功 ([0-9a-f]{8})", _result(out))
    assert m, f"结果行必须是「提交成功 <hash>」, 实际: {out!r}"
    # rebase 改写了 HEAD: 上面必须有一行把旧 hash 接到新 hash 的痕迹 —— 否则结果行就是黑箱
    assert re.search(rf"→ rebase 重放本地 1 笔 [0-9a-f]{{8}}→{m.group(1)}", out), out
    assert _git(repo, "rev-parse", "HEAD").startswith(m.group(1))  # 成功行报的是 rebase 后的真值
    remote_tip = _git(repo, "ls-remote", "origin", "develop").split()[0]
    assert _git(repo, "rev-list", "--count", f"{remote_tip}..HEAD") == "1"  # 本地提交重放在远端 tip 上
    assert _git(repo, "rev-list", "--merges", "--count", "HEAD") == "0"  # 历史保持线性
    assert (repo / "b.txt").exists() and (repo / "x.txt").exists()  # 两边内容都在
    assert "本次仍按启动版本运行" not in out  # 上游没动本包 → 不留「重跑以采用新版本」那行
    assert pushed == [1]


def test_remote_conflict_reports_partial(repo, tmp_path, monkeypatch, capsys):
    """同文件冲突 → rebase 自动回滚 → 提交成功(未推送) + 约定冲突模板; 退出码 0, 不重新提交。"""
    monkeypatch.setattr(commit_mod, "run_gates", lambda hits, ctx: ([], [], 0))
    monkeypatch.setattr(push_mod, "run_push", _must_not_push)
    msg = _write_msg(repo)
    (repo / "base.txt").write_text("my line\n", encoding="utf-8")
    _push_remote_commit(repo, tmp_path, "base.txt", "remote line\n")  # 同文件不同行 → rebase 必撞
    rc = commit_mod.main([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "提交成功" in out and "未推送" in out
    assert re.search(r"推送未完成: 同步失败需解决冲突 本地[0-9a-f]{8} 远端[0-9a-f]{8}", out)
    assert "commands run ship.push" in out
    assert not msg.exists()  # ref 核对已过 → 消息已消费
    assert not (repo / ".git" / "rebase-merge").exists()  # 回滚无残留
    assert not (repo / ".git" / "rebase-apply").exists()
    assert _git(repo, "log", "--format=%s", "-1") == "✨ test"  # HEAD 仍是本地提交(rebase 已回滚)


def test_post_rebase_gates_rerun_on_diverge(repo, tmp_path, monkeypatch, capsys):
    """rebase 真合入远端(HEAD 改写) → 闸门复跑一轮: 共两轮(提交前 + 合流后), 按同一份本地改动清单。"""
    calls = []

    def _gates(hits, ctx):
        calls.append(list(ctx["changed"]))
        return [], [], 0

    monkeypatch.setattr(commit_mod, "run_gates", _gates)
    monkeypatch.setattr(push_mod, "run_push", lambda steps=None: (True, "推送成功 abcdef01"))
    _write_msg(repo)
    (repo / "x.txt").write_text("x\n", encoding="utf-8")
    _push_remote_commit(repo, tmp_path, "b.txt", "b\n")
    rc = commit_mod.main([])
    out = capsys.readouterr().out
    assert rc == 0 and _result(out).startswith("提交成功 ")
    assert len(calls) == 2  # 提交前一轮 + 合流后复跑一轮
    assert calls[0] == calls[1] == ["x.txt"]


def test_post_rebase_gate_red_blocks_push(repo, tmp_path, monkeypatch, capsys):
    """复跑红 → 推送未完成 + 修复指引(修复重跑将作为新提交入库), 不推送, 退出码 0。"""
    runs = {"n": 0}

    def _gates(hits, ctx):
        runs["n"] += 1
        if runs["n"] == 1:
            return [], [], 0
        return [("测试闸门", "pytest -q", 1, 0.4, "boom\nE   assert False")], [], 1

    monkeypatch.setattr(commit_mod, "run_gates", _gates)
    monkeypatch.setattr(push_mod, "run_push", _must_not_push)
    _write_msg(repo)
    (repo / "x.txt").write_text("x\n", encoding="utf-8")
    _push_remote_commit(repo, tmp_path, "b.txt", "b\n")
    rc = commit_mod.main([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "提交成功" in out and "未推送" in out
    assert "推送未完成: 闸门「测试闸门」未过(合并远端后复跑" in out
    assert "重跑 commands run ship.commit" in out and "boom" in out
    assert runs["n"] == 2


def test_post_rebase_gate_dirty_amends(repo, tmp_path, monkeypatch, capsys):
    """复跑的 fmt 类闸门又改了文件 → 逐路径 add + amend 折进未推送 tip(不产生第二个提交)。"""
    runs = {"n": 0}

    def _gates(hits, ctx):
        runs["n"] += 1
        if runs["n"] == 2:  # 第二轮 = 合流后的复跑: 模拟 fmt 改文件
            (repo / "x.txt").write_text("x\nformatted\n", encoding="utf-8")
        return [], [], 0

    monkeypatch.setattr(commit_mod, "run_gates", _gates)
    monkeypatch.setattr(push_mod, "run_push", lambda steps=None: (True, "推送成功 abcdef01"))
    _write_msg(repo)
    (repo / "x.txt").write_text("x\n", encoding="utf-8")
    _push_remote_commit(repo, tmp_path, "b.txt", "b\n")
    rc = commit_mod.main([])
    out = capsys.readouterr().out
    assert rc == 0 and _result(out).startswith("提交成功 ")
    remote_tip = _git(repo, "ls-remote", "origin", "develop").split()[0]
    assert _git(repo, "rev-list", "--count", f"{remote_tip}..HEAD") == "1"  # 仍只有一个本地提交
    assert "formatted" in _git(repo, "show", "HEAD:x.txt")  # 闸门改动折进了 tip
    # amend 又挪了一次 tip —— 结果行的 hash 与 rebase 那行末端不同, 必须有一条步骤行接上
    assert re.search(r"闸门复跑: 合流后闸门改了 1 个文件 → amend [0-9a-f]{8}→[0-9a-f]{8}", out), out


def test_post_rebase_pack_changed_leaves_hint(repo, tmp_path, monkeypatch, capsys):
    """合流改动了**本包目录** → 登记一行「仍按启动版本运行, 重跑以采用新版本」。

    快照语义(一次调用 = 一个版本)下本进程对自我改写免疫, 但"上游换了本包"对用户是有价值的信号:
    静默会让人以为已经用上新版本。判据 = `git diff <旧> HEAD -- <本包路径>` 非空。
    """
    monkeypatch.setattr(commit_mod, "run_gates", lambda hits, ctx: ([], [], 0))
    monkeypatch.setattr(push_mod, "run_push", lambda steps=None: (True, "推送成功 abcdef01"))
    _write_msg(repo)
    (repo / "x.txt").write_text("x\n", encoding="utf-8")
    # 远端那笔改本包目录(测试里本包不在仓内, 走 pack_rel_path 的引擎约定位置 .commands/my-commit-flow)
    _push_remote_commit(repo, tmp_path, ".commands/my-commit-flow/new_tool.py", "upstream\n")
    assert commit_mod.main([]) == 0
    out = capsys.readouterr().out
    assert "快照: 上游改动了本包 → 本次仍按启动版本运行, 重跑以采用新版本" in out, out


def test_head_rewrite_trace_ends_at_result_hash(repo, tmp_path, monkeypatch, capsys):
    """步骤链不变量: 每一步的箭头右侧 == 下一步箭头左侧, 链尾 == 结果行的 hash(三者必须自洽)。"""
    calls = {"n": 0}

    def _gates(hits, ctx):
        calls["n"] += 1
        if calls["n"] == 2:  # 合流后复跑: fmt 改文件 → 走 amend
            (repo / "x.txt").write_text("x\nformatted\n", encoding="utf-8")
        return [], [], 0

    monkeypatch.setattr(commit_mod, "run_gates", _gates)
    monkeypatch.setattr(push_mod, "run_push", lambda steps=None: (True, "推送成功 abcdef01"))
    _write_msg(repo)
    (repo / "x.txt").write_text("x\n", encoding="utf-8")
    _push_remote_commit(repo, tmp_path, "b.txt", "b\n")
    assert commit_mod.main([]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    res = lines[-1]
    pairs = re.findall(r"([0-9a-f]{8})→([0-9a-f]{8})", "\n".join(lines[:-1]))  # 每个步骤行的「旧hash→新hash」
    assert pairs, f"没有任何 HEAD 改写步骤, 实际: {lines}"
    assert pairs[-1][1] in res, f"结果行的 hash 必须与最后一步箭头右侧一致: {lines}"
    assert [p[1] for p in pairs[:-1]] == [p[0] for p in pairs[1:]], f"步骤链必须首尾相接: {lines}"
    assert lines[0].startswith("同步: ")  # 步骤行按发生顺序排在结果行上面


# ------------------------------------------------------------------ 失败与例外路径


def test_gate_failure_blocks_commit(repo, monkeypatch, capsys):
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
    monkeypatch.setattr(push_mod, "run_push", lambda steps=None: (False, "主线推送未通过 —— rejected"))
    msg = _write_msg(repo)
    (repo / "x.txt").write_text("x\n", encoding="utf-8")
    rc = commit_mod.main([])
    out = capsys.readouterr().out
    assert rc == 0  # 提交这个主目标已达成 —— 补推即可, 别重提交
    assert "提交成功" in out and "未推送" in out
    assert "推送未完成: 主线推送未通过" in out and "commands run ship.push" in out
    assert not msg.exists()  # 提交已落稳(ref 通过), 消息照常消费


def test_no_push_skips_sync_and_push(repo, monkeypatch, capsys):
    _patch_ok_flow(monkeypatch)

    def _must_not_run(steps=None):
        raise AssertionError("--no-push 不该碰同步 / 推送")

    monkeypatch.setattr(sync_mod, "run_sync", _must_not_run)
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
    # ref 真丢的形态: HEAD 仍指旧 tip, 其消息与待提交消息不匹配 —— 钉住判定替身
    monkeypatch.setattr(commit_mod, "message_matches_head", lambda p: False)
    msg = _write_msg(repo)
    (repo / "x.txt").write_text("x\n", encoding="utf-8")
    rc = commit_mod.main([])
    out = capsys.readouterr().out
    assert rc == 1
    assert "ref 三处不一致" in out
    assert msg.exists()  # 提交可能没落稳: 保留现场不消费


def test_message_consumed_on_verify_fail_when_head_matches(repo, monkeypatch, capsys):
    """2026-10-07 实证的残留形态: 提交已落稳(HEAD 消息 == 文件内容), 核对红只是 packed-refs
    滞后一类误报 —— 此时照常消费, 不把「已入库的消息」留在 .git 里当残骸。"""
    _patch_ok_flow(monkeypatch)
    monkeypatch.setattr(
        commit_mod, "check_refs", lambda expect="": (False, ["  HEAD         deadbeef", "[STOP] ref 不一致"])
    )
    msg = _write_msg(repo)  # 不钉判定替身: commit 成功后 HEAD 消息真实等于文件内容
    (repo / "x.txt").write_text("x\n", encoding="utf-8")
    rc = commit_mod.main([])
    out = capsys.readouterr().out
    assert rc == 1
    assert "ref 三处不一致" in out  # 失败行照发(ref 处置指引不变)
    assert "消息文件已消费" in out and "已落稳" in out
    assert not msg.exists()  # 提交已落稳 → 不留残骸


def test_stale_message_residue_swept_at_entry(repo, capsys):
    """入口残留扫描: 约定消息文件内容 == HEAD 消息 = 上次已落库提交漏删的残骸(树净形态,
    2026-10-07 实证) → 删除 + 拒跑; 必须在「没有可提交的改动」之前拦, 否则树净时永不可达。"""
    msg = _write_msg(repo, "base")  # fixture 的 HEAD 提交消息就是 "base"
    before = _git(repo, "rev-list", "--count", "HEAD")
    rc = commit_mod.main([])
    out = capsys.readouterr().out
    assert rc == 1
    assert "已落库提交的残留" in out and "已删除" in out
    assert not msg.exists()  # 残骸自愈
    assert _git(repo, "rev-list", "--count", "HEAD") == before  # 未产生新提交


def test_message_kept_when_nothing_to_commit(repo, capsys):
    """树净且消息与 HEAD 不匹配 = 正常待提交消息(不是残骸) → 照旧拒绝, 文件保留等改动就绪。"""
    msg = _write_msg(repo)  # "✨ test" != HEAD 消息 "base"
    rc = commit_mod.main([])
    out = capsys.readouterr().out
    assert rc == 1
    assert "没有可提交的改动" in out
    assert msg.exists()


def test_check_refs_pass_on_fresh_repo(repo, monkeypatch):
    ok, detail = verify_ref_mod.check_refs()
    assert ok and detail == []
