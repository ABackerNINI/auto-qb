"""快照自举守阵 —— `_snapshot.py`(一次调用 = 一个版本)。

取代退役的「配置重取 / 包内模块热刷新」两条治标机制(它们只能在选定的几个点上打补丁): 入口脚本启动时把
整包复制到**仓库之外**的临时目录, 从副本重入 ⇒ 中途 rebase 写进工作区的新版本对本进程不可见。
本文件守住四条不变量: ①**重入**(未在快照里 → 复制 + 子进程接管); ②**免疫**(原包被改写, 旧副本输出不变);
③**采纳**(原包改写后新调用用新版); ④`import` 不重入(测试不受影响)。另加根注入 / 纯信息入口不复制 /
退出码透传 / 治标机制已退役的静态守卫。

跑法: python <包>/scripts/test_snapshot.py  ·  uv run pytest .commands -q --no-cov (test.pkg 口径)

## 测试计划
- SnapshotUnitTest       `_pack_dir` / `_find_repo_root` / `_sweep_old` 的纯函数行为
- RespawnGuardTest       已在快照里 / 纯信息入口 → 不复制; 四个入口脚本都装了守卫
- SnapshotEndToEndTest   真子进程: 重入用副本 · 免疫 · 采纳 · 退出码透传 · import 不重入
- RootInjectionTest      `_ship_config.find_root()` 认 `COMMAND_FLOW_REPO_ROOT`
- StopgapRetiredTest     治标机制(热刷新 / 配置重取)已从生产脚本里删净
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _snapshot  # noqa: E402
from _ship_config import REPO_ROOT_ENV, find_root  # noqa: E402

HERE = Path(__file__).resolve().parent
PY = sys.executable

# 探针入口: 与真入口同款守卫(置于 `__main__` 下 ⇒ import 不触发), 再吐出可断言的字段。
ENTRY = '''\
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _snapshot import maybe_respawn  # noqa: E402

if __name__ == "__main__":
    _rc = maybe_respawn(__file__)
    if _rc is not None:
        raise SystemExit(_rc)
    print("PACK_DIR=" + os.environ.get("COMMAND_FLOW_PACK_DIR", ""))
    print("REPO_ROOT=" + os.environ.get("COMMAND_FLOW_REPO_ROOT", ""))
    print("MARKER={marker}")
    raise SystemExit({rc})
'''

_SNAP_VARS = (
    "COMMAND_FLOW_SNAPSHOT", "COMMAND_FLOW_PACK_DIR", "COMMAND_FLOW_REPO_ROOT", "COMMAND_FLOW_ORIGINAL_PACK",
    "COMMAND_FLOW_SNAPSHOT_KEEP"
)


def _git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    assert proc.returncode == 0, f"git {' '.join(args)} 失败: {proc.stderr}"
    return proc.stdout.strip()


def _run(args: list[str], cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    """跑子进程 —— 默认**抹掉**外层可能残留的快照环境变量, 免得测试间互相污染。"""
    base = {k: v for k, v in os.environ.items() if k not in _SNAP_VARS}
    full = {**base, "PYTHONIOENCODING": "utf-8", **(env or {})}
    return subprocess.run(
        [PY, *args], cwd=str(cwd), env=full, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )


def _field(out: str, prefix: str) -> str:
    for line in out.splitlines():
        if line.startswith(prefix):
            return line[len(prefix):].strip()
    return ""


def _make_repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    _git(root, "init", "-b", "develop", str(repo))
    return repo


def _install_pack(repo: Path, marker: str = "v1", rc: int = 0) -> Path:
    """把 `_snapshot.py` + 一个探针入口装进 `<repo>/.commands/my-commit-flow/scripts/`(模拟真包)。"""
    pack = repo / ".commands" / "my-commit-flow"
    (pack / "scripts").mkdir(parents=True)
    shutil.copy2(HERE / "_snapshot.py", pack / "scripts" / "_snapshot.py")
    _write_entry(pack, marker, rc)
    return pack


def _write_entry(pack: Path, marker: str, rc: int = 0) -> None:
    (pack / "scripts" / "entry.py").write_text(ENTRY.format(marker=marker, rc=rc), encoding="utf-8")


def _snap_dirs() -> set[Path]:
    return set(Path(tempfile.gettempdir()).glob(_snapshot.SNAPSHOT_PREFIX + "*"))


class SnapshotUnitTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_pack_dir_is_two_levels_up(self) -> None:
        entry = self.root / "pack" / "scripts" / "commit.py"
        entry.parent.mkdir(parents=True)
        entry.write_text("", encoding="utf-8")
        self.assertEqual(_snapshot._pack_dir(str(entry)), (self.root / "pack").resolve())

    def test_find_repo_root_walks_up_to_git(self) -> None:
        repo = self.root / "repo"
        (repo / ".git").mkdir(parents=True)
        deep = repo / "a" / "b"
        deep.mkdir(parents=True)
        self.assertEqual(_snapshot._find_repo_root(deep), repo)

    def test_find_repo_root_returns_none_outside_repo(self) -> None:
        lonely = self.root / "lonely"
        lonely.mkdir()
        self.assertIsNone(_snapshot._find_repo_root(lonely), "不在仓库里就不注入(让脚本走自己的兜底)")

    def test_sweep_old_removes_only_stale_snapshots(self) -> None:
        base = Path(tempfile.gettempdir())
        old = Path(tempfile.mkdtemp(prefix=_snapshot.SNAPSHOT_PREFIX, dir=base))
        fresh = Path(tempfile.mkdtemp(prefix=_snapshot.SNAPSHOT_PREFIX, dir=base))
        self.addCleanup(lambda: shutil.rmtree(old, ignore_errors=True))
        self.addCleanup(lambda: shutil.rmtree(fresh, ignore_errors=True))
        stale = time.time() - _snapshot.SWEEP_AGE - 60
        os.utime(old, (stale, stale))
        _snapshot._sweep_old()
        self.assertFalse(old.exists(), "超过一天的旧快照应被清掉(崩溃 / 强杀时 finally 不跑)")
        self.assertTrue(fresh.exists(), "新快照不该被清掉")


class RespawnGuardTest(unittest.TestCase):
    """不复制的情形 —— 都在进程内判, 不真起子进程。"""
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.entry = Path(self.tmp.name) / "pack" / "scripts" / "entry.py"
        self.entry.parent.mkdir(parents=True)
        self.entry.write_text("", encoding="utf-8")

    def test_in_snapshot_returns_none(self) -> None:
        """防无限重入: 已在快照里就跑, 不再复制。"""
        with mock.patch.dict(os.environ, {"COMMAND_FLOW_SNAPSHOT": "1"}):
            self.assertIsNone(_snapshot.maybe_respawn(str(self.entry)))

    def test_info_flags_do_not_respawn(self) -> None:
        """纯信息入口直接作用**原包** —— 尤其 `--init` 要把配置写进真包, 不能写进临时副本。"""
        clean = {k: v for k, v in os.environ.items() if k != "COMMAND_FLOW_SNAPSHOT"}
        with mock.patch.dict(os.environ, clean, clear=True):
            for flag in _snapshot.INFO_FLAGS:
                self.assertIsNone(_snapshot.maybe_respawn(str(self.entry), argv=[flag]), flag)

    def test_real_entry_scripts_install_guard(self) -> None:
        """静态守: 四个入口都得装守卫 —— 漏一个, 那条路径就回到"进程手里的快照过期"。"""
        for name in ("commit.py", "sync.py", "push.py", "verify_ref.py"):
            text = (HERE / name).read_text(encoding="utf-8")
            self.assertIn("maybe_respawn(__file__)", text, f"{name} 缺快照自举守卫")


class SnapshotEndToEndTest(unittest.TestCase):
    """真子进程 —— 重入 / 免疫 / 采纳 / 退出码, 都靠"跑一次真的"才测得出来。"""
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = _make_repo(Path(self.tmp.name))
        self.pack = _install_pack(self.repo)

    def test_respawn_runs_from_snapshot_outside_repo(self) -> None:
        # KEEP=1: 副本在子进程退出时就被删, 要断言它的内容必须先留住
        proc = _run([str(self.pack / "scripts" / "entry.py")], self.repo, env={"COMMAND_FLOW_SNAPSHOT_KEEP": "1"})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        snap = Path(_field(proc.stdout, "PACK_DIR="))
        self.addCleanup(lambda: shutil.rmtree(snap.parent, ignore_errors=True))
        self.assertTrue(snap.is_dir(), f"应跑在临时副本上, 实际: {proc.stdout!r}")
        self.assertNotEqual(snap, self.pack, "副本不能就是原包")
        self.assertTrue((snap / "scripts" / "entry.py").is_file(), "副本含包脚本")
        self.assertNotIn(self.repo, snap.parents, "副本必须在仓库之外(否则 rebase 照样碰得到)")
        self.assertEqual(_field(proc.stdout, "REPO_ROOT="), str(self.repo), "真根经 env 注入(副本向上找不到 .git)")

    def test_snapshot_is_removed_after_run(self) -> None:
        before = _snap_dirs()
        proc = _run([str(self.pack / "scripts" / "entry.py")], self.repo)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(_snap_dirs(), before, "正常路径子进程退出即删临时副本(不留垃圾)")

    def test_import_does_not_respawn(self) -> None:
        """守卫在 `__main__` 下 ⇒ `import` 不复制(否则测试 / 复用方每 import 一次就多一份副本)。"""
        before = _snap_dirs()
        scripts = self.pack / "scripts"
        code = "import sys; sys.path.insert(0, r'%s'); import entry; print('IMPORTED')" % scripts
        proc = _run(["-c", code], self.repo)
        self.assertIn("IMPORTED", proc.stdout, proc.stderr)
        self.assertEqual(_snap_dirs(), before, "import 不该触发重入")

    def test_snapshot_is_immune_and_new_call_adopts(self) -> None:
        """核心证据: 原包被改写后, **旧副本输出不变**(免疫), **新调用采用新版**(采纳)。"""
        proc = _run([str(self.pack / "scripts" / "entry.py")], self.repo, env={"COMMAND_FLOW_SNAPSHOT_KEEP": "1"})
        snap = Path(_field(proc.stdout, "PACK_DIR="))
        self.addCleanup(lambda: shutil.rmtree(snap.parent, ignore_errors=True))
        self.assertEqual(_field(proc.stdout, "MARKER="), "v1")

        _write_entry(self.pack, "v2")  # 模拟内部同步的 rebase 换了本包

        # (a) 跑**旧副本**(SNAPSHOT=1 直入, 不重造) —— 免疫: 仍是 v1
        old = _run(
            [str(snap / "scripts" / "entry.py")],
            self.repo,
            env={
                "COMMAND_FLOW_SNAPSHOT": "1",
                "COMMAND_FLOW_PACK_DIR": str(snap),
                "COMMAND_FLOW_REPO_ROOT": str(self.repo),
            },
        )
        self.assertEqual(_field(old.stdout, "MARKER="), "v1", f"旧副本必须免疫, 实际: {old.stdout!r}")

        # (b) 原包新调用 → 采纳新版
        new = _run([str(self.pack / "scripts" / "entry.py")], self.repo)
        self.assertEqual(_field(new.stdout, "MARKER="), "v2", f"新调用必须采用新版, 实际: {new.stdout!r}")

    def test_exit_code_passthrough(self) -> None:
        _write_entry(self.pack, "x", rc=3)
        proc = _run([str(self.pack / "scripts" / "entry.py")], self.repo)
        self.assertEqual(proc.returncode, 3, f"子进程退出码应原样透传给调用方: {proc.stderr}")


class RootInjectionTest(unittest.TestCase):
    """副本在仓库外, `find_root()` 必须认 `COMMAND_FLOW_REPO_ROOT`(否则根解析落到临时目录)。"""
    def test_find_root_honours_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_root = Path(tmp) / "real-repo"
            fake_root.mkdir()
            with mock.patch.dict(os.environ, {REPO_ROOT_ENV: str(fake_root)}):
                self.assertEqual(find_root(), fake_root.resolve())

    def test_blank_env_falls_back_to_walking_up(self) -> None:
        with mock.patch.dict(os.environ, {REPO_ROOT_ENV: "   "}):
            # 空白 = 没注入 → 退回"向上找 .git"的老路径(本包就住在这个仓库里)
            self.assertTrue((find_root() / ".commands" / "my-commit-flow").is_dir())


class StopgapRetiredTest(unittest.TestCase):
    """治标机制(包内模块热刷新 / 配置重取)已随快照语义退役 —— 守住它们不被悄悄带回来。

    快照语义下它们不再有意义: 本进程跑的是**副本**, 中途自我改写本来就不可见, 没有"重载 / 重取"的必要。
    留着就是死代码, 且会让人以为还有一条"跟随新版"的路径。
    """

    RETIRED = ("refresh_package_modules", "reload_config", "_reload_cfg")

    def test_retired_mechanisms_are_gone(self) -> None:
        for name in ("_pipeline.py", "sync.py", "commit.py", "push.py", "verify_ref.py"):
            text = (HERE / name).read_text(encoding="utf-8")
            for dead in self.RETIRED:
                self.assertNotIn(dead, text, f"{name} 仍引用已退役的 {dead}")


if __name__ == "__main__":
    raise SystemExit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
