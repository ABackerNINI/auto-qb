""".commands/conftest.py 临时目录防呆闸的回归阵 —— issue 26-11-14-0857 P1b(2026-11-14 评审 R2 #3)。

闸本体是「TMPDIR 落在仓库根之内 ⇒ rc=4 响亮拒收」: 比较写反 / HEAD 判据被简化 / SystemExit
被删都无红灯, 会让包测试在仓库内起跑出混乱假红。这里用**真子进程**把 conftest 装进假仓库直接跑
`pytest --collect-only`, 负例断 rc=4 + stderr 含 FATAL 文案, 正例断放行 —— 闸的行为以裸 pytest
实测口径钉死(2026-11-14 实测: 仓库内 TMPDIR rc=4, 仓库外 rc=0)。

## 测试计划
- ConftestGuardTest  假仓库真子进程: .git 目录形态 仓库内 TMPDIR → rc=4 且 stderr 含 FATAL; 仓库外 → rc=0; worktree 文件形态(.git=FILE) 仓库内 → rc=4; 无 .git 裸目录 仓库内 → rc=0(判据不误伤); 空壳 .git(无 HEAD) 仓库内 → rc=0(26-10-31 判据同口径)
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SMOKE = "def test_ok():\n    assert True\n"


class ConftestGuardTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def _plant(self, repo: Path) -> Path:
        """把 conftest 副本 + 冒烟用例装进 <repo>/.commands/(conftest 以自身位置向上找 .git)。"""
        (repo / ".commands").mkdir(parents=True)
        shutil.copy2(HERE / "conftest.py", repo / ".commands" / "conftest.py")
        (repo / ".commands" / "test_smoke.py").write_text(SMOKE, encoding="utf-8")
        return repo

    def _git_marker(self, repo: Path) -> None:
        (repo / ".git").mkdir()
        (repo / ".git" / "HEAD").write_text("ref: refs/heads/develop\n", encoding="utf-8")

    def _run_collect(self, repo: Path, tmpdir: Path) -> subprocess.CompletedProcess:
        env = dict(os.environ, TMPDIR=str(tmpdir))
        return subprocess.run(
            [sys.executable, "-m", "pytest", ".commands", "--collect-only", "-q"],
            cwd=str(repo),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def test_rejects_tmpdir_inside_repo(self) -> None:
        repo = self._plant(self.root / "repo")
        self._git_marker(repo)
        inside = repo / "inrepo"
        inside.mkdir()
        proc = self._run_collect(repo, inside)
        self.assertEqual(proc.returncode, 4, f"仓库内 TMPDIR 必须 rc=4 拒收: {proc.stderr}")
        self.assertIn("FATAL", proc.stderr, "拒收必须带响亮文案, 否则静默退码无法排障")

    def test_rejects_tmpdir_inside_worktree_checkout(self) -> None:
        # worktree 文件形态: .git 是 FILE(指针)也算仓库根 —— conftest 判据与 _snapshot 同口径,
        # 删掉该分支本例必红(评审 R2 轮 2 #1: 目录形态单钉漏掉 worktree 向)
        repo = self._plant(self.root / "wt")
        (repo / ".git").write_text("gitdir: ../main/.git/worktrees/wt\n", encoding="utf-8")
        inside = repo / "inrepo"
        inside.mkdir()
        proc = self._run_collect(repo, inside)
        self.assertEqual(proc.returncode, 4, f"worktree 检出内 TMPDIR 必须 rc=4 拒收: {proc.stderr}")

    def test_allows_tmpdir_outside_repo(self) -> None:
        repo = self._plant(self.root / "repo")
        self._git_marker(repo)
        outside = self.root / "outside"
        outside.mkdir()
        proc = self._run_collect(repo, outside)
        self.assertEqual(proc.returncode, 0, f"仓库外 TMPDIR 必须放行: {proc.stderr}")

    def test_bare_dir_without_git_passes_through(self) -> None:
        # 判据不误伤: 无 .git 的裸目录不算仓库根, conftest 让路 —— TMPDIR 指进裸目录**内**也要放行
        # (判据弱化为「无 .git 也返回目录」的变异下本例必红, 评审 R2 轮 2 #2: 旧写法 TMPDIR 在外,
        # 判据没被真行使)
        bare = self._plant(self.root / "bare")
        inside = bare / "inrepo"
        inside.mkdir()
        proc = self._run_collect(bare, inside)
        self.assertEqual(proc.returncode, 0, f"裸目录(无 .git)内 TMPDIR 不应触发拒收: {proc.stderr}")

    def test_shell_git_dir_without_head_passes_through(self) -> None:
        # 26-10-31 事故判据同口径: 空壳 .git 目录(无 HEAD)不算仓库根 —— TMPDIR 在内也要放行
        shell = self._plant(self.root / "shell")
        (shell / ".git").mkdir()
        inside = shell / "inrepo"
        inside.mkdir()
        proc = self._run_collect(shell, inside)
        self.assertEqual(proc.returncode, 0, f"空壳 .git(无 HEAD)不是仓库根, 不应拒收: {proc.stderr}")


if __name__ == "__main__":
    raise SystemExit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
