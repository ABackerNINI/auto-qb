"""sync.py 的场景测试 —— **真实临时仓库**(本地 bare 远端), 覆盖 v3 同步行分类与线性历史承诺。

同步是写状态的操作, mock 测不出 git 的真实拒绝/回滚行为 —— 全部场景跑真 git, 仓库建在
pytest 的 tmp_path 下(不碰任何真实 clone); 判据引用 pitfalls/git/refs.md 的环境约束。

## 测试计划
- test_in_sync_reports_same_hash        齐平 → 已同步 <hash>(HEAD 不变)
- test_ahead_only_is_noop               本地领先(未推送) → 已同步, 推送即快进
- test_behind_clean_fast_forwards       纯落后+树净 → 同步成功, HEAD == 远端 tip
- test_behind_dirty_without_overlap_ok  落后+树脏无重叠 → 同步成功, 本地改动原样保留
- test_behind_dirty_overlap_refuses     落后+脏重叠 → 失败(重叠), HEAD 与脏文件原样; 失败行自带解锁配方
- test_diverged_rebases_linear          分叉(不同文件) → rebase 保线性: 零 merge commit, 提交内容不变
- test_diverged_conflict_rolls_back     分叉同文件冲突 → 「同步失败需解决冲突 本地<x> 远端<y>」,
                                        rebase 已回滚(无残留状态, HEAD 不变)
- test_diverged_dirty_refuses           分叉+树脏 → 失败(自带解锁配方, 不再给「先提交」这条死锁指引)
- test_dirty_block_flag_recognized      脏类失败行被 is_dirty_block 认出; 冲突/离线类不被认成脏类
- test_offline_reports_unreachable      远端不可达 → 拿不到远端
- test_staged_overflow_refuses          staged 暴增 → 拒绝(ref 回退信号)
- test_main_prints_one_line_contract    main() 输出形态: 成功一行 / 冲突行恰为约定模板
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sync as sync_mod  # noqa: E402
from _ship_config import find_root  # noqa: E402

PKG = Path(__file__).resolve().parent.parent
HASH_RE = re.compile(r"^[0-9a-f]{8}$")


def _git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, f"git {' '.join(args)} 失败: {proc.stderr}"
    return proc.stdout.strip()


def _commit_file(repo: Path, name: str, content: str, msg: str) -> None:
    (repo / name).write_text(content, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", msg)


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """bare 远端 origin.git + 工作仓 a(已推送 base 提交); cwd 钉在 a, 配置指向本包。"""
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
    return SimpleNamespace(tmp=tmp_path, origin=origin, a=a)


def _push_remote_commit(env: dict, name: str, content: str, msg: str = "remote") -> Path:
    """第二个工作仓 b: 模拟"别的 clone 推了新提交"。"""
    b = env.tmp / "b"
    if not b.exists():
        _git(env.tmp, "clone", "-b", "develop", env.origin.name, "b")
        _git(b, "config", "user.email", "t@t")
        _git(b, "config", "user.name", "t")
    _commit_file(b, name, content, msg)
    _git(b, "push", "origin", "develop")
    return b


def test_in_sync_reports_same_hash(env, monkeypatch):
    monkeypatch.chdir(env.a)
    before = _git(env.a, "rev-parse", "HEAD")
    ok, line = sync_mod.run_sync()
    assert ok
    m = re.match(r"^已同步 ([0-9a-f]{8})$", line)
    assert m and _git(env.a, "rev-parse", "HEAD").startswith(m.group(1))
    assert _git(env.a, "rev-parse", "HEAD") == before


def test_ahead_only_is_noop(env, monkeypatch):
    monkeypatch.chdir(env.a)
    _commit_file(env.a, "local.txt", "local\n", "local work")
    before = _git(env.a, "rev-parse", "HEAD")
    ok, line = sync_mod.run_sync()
    assert ok and line.startswith("已同步 ")
    assert _git(env.a, "rev-parse", "HEAD") == before


def test_behind_clean_fast_forwards(env, monkeypatch):
    monkeypatch.chdir(env.a)
    _push_remote_commit(env, "b.txt", "b\n")
    remote_tip = _git(env.a, "ls-remote", "origin", "develop").split()[0]
    ok, line = sync_mod.run_sync()
    assert ok and re.match(r"^同步成功 [0-9a-f]{8}$", line)
    assert _git(env.a, "rev-parse", "HEAD") == remote_tip


def test_behind_dirty_without_overlap_ok(env, monkeypatch):
    monkeypatch.chdir(env.a)
    (env.a / "local.txt").write_text("dirty\n", encoding="utf-8")  # 未跟踪 = 树脏
    _push_remote_commit(env, "b.txt", "b\n")
    ok, line = sync_mod.run_sync()
    assert ok and line.startswith("同步成功 ")
    assert (env.a / "local.txt").read_text(encoding="utf-8") == "dirty\n"  # 本地改动原样


def test_behind_dirty_overlap_refuses(env, monkeypatch):
    monkeypatch.chdir(env.a)
    (env.a / "base.txt").write_text("my edit\n", encoding="utf-8")  # 与远端将改的文件重叠
    _push_remote_commit(env, "base.txt", "remote edit\n")
    before = _git(env.a, "rev-parse", "HEAD")
    ok, line = sync_mod.run_sync()
    assert not ok
    assert "重叠" in line
    # 死锁护栏(2026-10-03): 失败行必须自带解锁配方, 且**不能**再给「先提交」这条死锁指引
    assert sync_mod.is_dirty_block(line)
    assert "git stash push -u" in line and "git stash pop" in line
    assert "先提交或移出" not in line
    assert _git(env.a, "rev-parse", "HEAD") == before  # 仓库状态不变
    assert (env.a / "base.txt").read_text(encoding="utf-8") == "my edit\n"


def test_diverged_rebases_linear(env, monkeypatch):
    monkeypatch.chdir(env.a)
    _commit_file(env.a, "a-only.txt", "a\n", "local work")  # 本地独有(未推送)
    _push_remote_commit(env, "b.txt", "b\n")  # 远端新提交
    old_local = _git(env.a, "rev-parse", "HEAD")
    ok, line = sync_mod.run_sync()
    assert ok and re.match(r"^同步成功 [0-9a-f]{8}$", line)
    assert _git(env.a, "rev-parse", "HEAD") != old_local  # rebase 改写 hash
    assert _git(env.a, "rev-list", "--merges", "--count", "HEAD") == "0"  # 历史保持线性
    assert (env.a / "a-only.txt").exists()  # 提交内容不变
    remote_tip = _git(env.a, "ls-remote", "origin", "develop").split()[0]
    assert _git(env.a, "rev-list", "--count", f"{remote_tip}..HEAD") == "1"  # 本地提交重放在远端 tip 上


def test_diverged_conflict_rolls_back(env, monkeypatch):
    monkeypatch.chdir(env.a)
    _commit_file(env.a, "base.txt", "my line\n", "local edit")
    before = _git(env.a, "rev-parse", "HEAD")
    _push_remote_commit(env, "base.txt", "remote line\n")  # 同文件不同行 → rebase 必撞
    ok, line = sync_mod.run_sync()
    assert not ok
    assert re.search(r"需解决冲突 本地[0-9a-f]{8} 远端[0-9a-f]{8}", line)
    assert "已自动回滚" in line
    assert _git(env.a, "rev-parse", "HEAD") == before  # 回滚后 HEAD 不变
    assert not (env.a / ".git" / "rebase-merge").exists()  # 无残留 rebase 状态
    assert not (env.a / ".git" / "rebase-apply").exists()


def test_diverged_dirty_refuses(env, monkeypatch):
    monkeypatch.chdir(env.a)
    _commit_file(env.a, "a-only.txt", "a\n", "local work")
    (env.a / "base.txt").write_text("dirty\n", encoding="utf-8")
    _push_remote_commit(env, "b.txt", "b\n")
    ok, line = sync_mod.run_sync()
    assert not ok
    assert "已分叉且工作区脏" in line
    assert sync_mod.is_dirty_block(line) and "git stash push -u" in line and "git stash pop" in line
    assert "先提交或 stash 后重跑" not in line  # 旧指引会把执行者推进死锁


def test_dirty_block_flag_recognized(env, monkeypatch):
    """is_dirty_block 的分流: 只有「本地改动挡路」这一类算脏类 —— commit.py 靠它决定补不补死锁护栏。"""
    monkeypatch.chdir(env.a)
    (env.a / "base.txt").write_text("my edit\n", encoding="utf-8")
    _push_remote_commit(env, "base.txt", "remote edit\n")
    _, dirty = sync_mod.run_sync()
    assert sync_mod.is_dirty_block(dirty)
    # 冲突(已提交后分叉)与离线都不是脏类 —— 各自的处置不含 stash 配方
    _git(env.a, "checkout", "--", "base.txt")
    _commit_file(env.a, "base.txt", "my line\n", "local edit")
    _push_remote_commit(env, "base.txt", "remote line\n")
    _, conflict = sync_mod.run_sync()
    assert not sync_mod.is_dirty_block(conflict)
    _git(env.a, "remote", "set-url", "origin", str(env.tmp / "nonexistent.git"))
    _, offline = sync_mod.run_sync()
    assert not sync_mod.is_dirty_block(offline)


def test_offline_reports_unreachable(env, monkeypatch):
    monkeypatch.chdir(env.a)
    _git(env.a, "remote", "set-url", "origin", str(env.tmp / "nonexistent.git"))
    ok, line = sync_mod.run_sync()
    assert not ok
    assert "拿不到远端 origin/develop" in line and "联网后重跑" in line


def test_staged_overflow_refuses(env, monkeypatch):
    monkeypatch.chdir(env.a)
    bulk = env.a / "bulk"
    bulk.mkdir()
    for i in range(201):
        (bulk / f"f{i}.txt").write_text("x\n", encoding="utf-8")
    _git(env.a, "add", "-A")
    ok, line = sync_mod.run_sync()
    assert not ok
    assert "staged 201" in line and "add -A" in line  # ref 回退信号, 拒绝继续


def test_main_prints_one_line_contract(env, monkeypatch, capsys):
    monkeypatch.chdir(env.a)
    assert sync_mod.main() == 0
    assert capsys.readouterr().out.count("\n") == 1  # 成功恰好一行
    _push_remote_commit(env, "base.txt", "remote line\n")
    _commit_file(env.a, "base.txt", "my line\n", "local edit")
    assert sync_mod.main() == 1
    out = capsys.readouterr().out
    assert re.search(r"^同步失败需解决冲突 本地[0-9a-f]{8} 远端[0-9a-f]{8}", out)  # 约定模板
    assert len(out.strip().splitlines()) == 1  # 失败也是一行(原因 + 步骤都在行内)
