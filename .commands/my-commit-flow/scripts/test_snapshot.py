"""快照自举守阵 —— `_snapshot.py`(一次调用 = 一个版本)。

取代退役的「配置重取 / 包内模块热刷新」两条治标机制(它们只能在选定的几个点上打补丁): 入口脚本启动时把
整包复制到**仓库之外**的临时目录, 从副本重入 ⇒ 中途 rebase 写进工作区的新版本对本进程不可见。
本文件守住四条不变量: 1) **重入**(未在快照里 → 复制 + 子进程接管); 2) **免疫**(原包被改写, 旧副本输出不变);
3) **采纳**(原包改写后新调用用新版); 4) `import` 不重入(测试不受影响)。另加根注入 / 纯信息入口不复制 /
退出码透传 / 治标机制已退役的静态守卫。

跑法: python <包>/scripts/test_snapshot.py  ·  uv run pytest .commands -q --no-cov (test.pkg 口径)

## 测试计划
- SnapshotUnitTest       `_pack_dir` / `_find_repo_root`(目录须含 HEAD——空壳 `.git` 不算仓库, 26-10-31 事故回归阵; 文件形态 = worktree) / `_sweep_old` 的纯函数行为(自证标记放行 / 外来同前缀豁免 / gettempdir 回落 CWD 整体跳过, issue 0857 P2)
- RespawnGuardTest       已在快照里 / 纯信息入口 → 不复制; 四个入口脚本都装了守卫
- SnapshotEndToEndTest   真子进程: 重入用副本 · 免疫 · 采纳 · 退出码透传 · import 不重入 · 存在性比较限定在用例私有临时根(`-n 8` 并行安全)
- ProbeAnchorTest            探针锚定守卫: 侧信道报告文件优先 / stdout 兜底; 合法放行 / 缺行 / 空值 / 越界就地 fail(fail 先于 cleanup 注册, 26-11-13 CWD 误删事故回归阵, issue 0857 P0+P1a)
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

# 探针入口: 与真入口同款守卫(置于 `__main__` 下 ⇒ import 不触发), 再吐出可断言的字段;
# 字段同时写进 COMMAND_FLOW_PROBE_OUT 指定的文件(侧信道) —— stdout 可能被沙箱/shim 吞改,
# 是 26-11-13 事故的入口面, 测试读报告时侧信道文件优先、stdout 解析只作兜底。
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
    _out = os.environ.get("COMMAND_FLOW_PROBE_OUT", "")
    if _out:
        Path(_out).write_text(
            "PACK_DIR=" + os.environ.get("COMMAND_FLOW_PACK_DIR", "")
            + "\\nREPO_ROOT=" + os.environ.get("COMMAND_FLOW_REPO_ROOT", "")
            + "\\nMARKER={marker}\\n",
            encoding="utf-8",
        )
    raise SystemExit({rc})
'''

_SNAP_VARS = (
    "COMMAND_FLOW_SNAPSHOT", "COMMAND_FLOW_PACK_DIR", "COMMAND_FLOW_REPO_ROOT", "COMMAND_FLOW_ORIGINAL_PACK",
    "COMMAND_FLOW_SNAPSHOT_KEEP", "COMMAND_FLOW_PROBE_OUT"
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


def _probe_text(proc: subprocess.CompletedProcess, report: Path) -> str:
    """探针报告读取单点: 侧信道文件优先, stdout 只作兜底 —— shim 吞改 stdout 是 26-11-13
    事故的入口面, 所有断言面(PACK_DIR / REPO_ROOT / MARKER)一律经本助手取值(评审 R2 #5)。"""
    return report.read_text(encoding="utf-8") if report.is_file() else proc.stdout


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


def _private_tmp(root: Path) -> Path:
    """本用例专属的临时根 —— TMPDIR 指到这里, 前后存在性比较也只看这里。

    为什么隔离(2026-10-16): 旧写法比较**全局** `tempfile.gettempdir()`, 等于假设"只有我在用这个根" ——
    `-n 8` 并行下兄弟用例的临时快照目录会落进同一根, 逐位比较被搅成假红(连续多次复现)。隔离后各
    用例只观察自己的根, 断言意图不变(该操作不得新增 / 遗留快照目录)。
    """
    private = root / "snap-tmp"
    private.mkdir()
    return private


def _snap_dirs(root: Path) -> set[Path]:
    return set(root.glob(_snapshot.SNAPSHOT_PREFIX + "*"))


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
        (repo / ".git" / "HEAD").mkdir(parents=True)  # 真仓库 git init 即建 HEAD
        deep = repo / "a" / "b"
        deep.mkdir(parents=True)
        self.assertEqual(_snapshot._find_repo_root(deep), repo)

    def test_find_repo_root_accepts_worktree_git_file(self) -> None:
        wt = self.root / "wt"
        (wt / "a").mkdir(parents=True)
        (wt / ".git").write_text("gitdir: ../main/.git/worktrees/wt\n", encoding="utf-8")
        self.assertEqual(_snapshot._find_repo_root(wt / "a"), wt)

    def test_find_repo_root_ignores_shell_git_dir_without_head(self) -> None:
        # 26-10-31 事故回归阵: 家目录被塞空壳 `.git` 目录(0 文件无 HEAD) + TMPDIR 回落用户
        # 资料区 ⇒ walk-up 曾误判仓库根。判据加 HEAD 存在性后, 空壳不算仓库, walk 穿过它继续。
        shell = self.root / "shell"
        (shell / ".git").mkdir(parents=True)  # 无 HEAD
        deep = shell / "a" / "b"
        deep.mkdir(parents=True)
        self.assertIsNone(_snapshot._find_repo_root(deep), "空壳 .git 目录不是仓库根")

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
        # 自证标记: 与 make_snapshot 落点同构(pack/scripts/_snapshot.py), 缺了不算本包快照
        for d in (old, fresh):
            (d / "pack" / "scripts").mkdir(parents=True)
            (d / "pack" / "scripts" / "_snapshot.py").write_text("", encoding="utf-8")
        stale = time.time() - _snapshot.SWEEP_AGE - 60
        os.utime(old, (stale, stale))
        _snapshot._sweep_old()
        self.assertFalse(old.exists(), "超过一天的旧快照应被清掉(崩溃 / 强杀时 finally 不跑)")
        self.assertTrue(fresh.exists(), "新快照不该被清掉")

    def test_sweep_old_spares_foreign_prefix_dir(self) -> None:
        # 名字撞 SNAPSHOT_PREFIX 但无自证标记的外来目录 —— 一律不碰(issue 0857 P2)
        base = Path(tempfile.gettempdir())
        foreign = Path(tempfile.mkdtemp(prefix=_snapshot.SNAPSHOT_PREFIX, dir=base))
        self.addCleanup(lambda: shutil.rmtree(foreign, ignore_errors=True))
        stale = time.time() - _snapshot.SWEEP_AGE - 60
        os.utime(foreign, (stale, stale))
        _snapshot._sweep_old()
        self.assertTrue(foreign.exists(), "无自证标记的同前缀目录不得清扫")

    def test_sweep_old_skips_when_tempdir_is_cwd(self) -> None:
        # gettempdir 回落 CWD(沙箱 /tmp 全不可写的典型后果) ⇒ 整体放弃清扫, 宁可不扫不可错删。
        # marked 造进私有根并 chdir 进去: 守卫若被删, _sweep_old 扫的就是这个根、必把 marked 清掉
        # ⇒ 用例真会红(26-11-14 评审 R2 #1: 旧写法 marked 在全局根, 守卫删除后 glob 的是仓库根,
        # 根本碰不到 marked, 断言恒真, 是死用例); 私有根同时让其它 worker 的 _sweep_old 摸不到它,
        # 消除 -n 8 跨 worker 竞态(R2 #2)。
        private = Path(tempfile.mkdtemp(prefix="sweep-cwd-probe-"))
        self.addCleanup(lambda: shutil.rmtree(private, ignore_errors=True))
        marked = private / (_snapshot.SNAPSHOT_PREFIX + "marked")
        (marked / "pack" / "scripts").mkdir(parents=True)
        (marked / "pack" / "scripts" / "_snapshot.py").write_text("", encoding="utf-8")
        stale = time.time() - _snapshot.SWEEP_AGE - 60
        os.utime(marked, (stale, stale))
        old_cwd = os.getcwd()
        os.chdir(private)
        self.addCleanup(lambda: os.chdir(old_cwd))
        with mock.patch.object(_snapshot.tempfile, "gettempdir", return_value=str(private)):
            _snapshot._sweep_old()
        self.assertTrue(marked.exists(), "gettempdir==CWD 时必须整体跳过清扫(守卫删除则本用例红)")


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

    def _snap_from_probe(self, proc: subprocess.CompletedProcess, report: Path) -> Path:
        """解析探针结果, 按快照落点不变量**先验证再锚定** —— 26-11-13 移植事故回归阵。

        侧信道优先: stdout 可能被沙箱 / AppImage shim 吞改(本次事故的入口面), 探针同时把报告写进
        `report`(经 COMMAND_FLOW_PROBE_OUT 注入); 文件缺席才退回 stdout 解析(issue 0857 P1a)。
        解析落空时旧写法 `Path(_field(...))` 会落空成 `Path("")`, 其 `.parent` 恒等 `Path(".")`
        = 测试进程 CWD(= 仓库根), 随后的 `rmtree(snap.parent, ignore_errors=True)` 就把整个仓库
        (含 .git)递归删空(T4 移植报告实证)。守两条: 1) 解析结果必须命中 `make_snapshot` 的唯一落点
        `<gettempdir>/<SNAPSHOT_PREFIX>*/pack`(子进程经 `_run` 继承同一 TMPDIR, 不变量跨进程可判);
        2) 校验不过就地 fail 并附原始输出, **不注册任何 cleanup** —— 校验失败残留的 KEEP=1
        快照目录由 `_sweep_old` 的 24h 龄兜底, 宁可留垃圾不可错删仓库。
        """
        text = _probe_text(proc, report)
        snap = Path(_field(text, "PACK_DIR="))
        anchored = (
            snap.name == "pack" and snap.parent.name.startswith(_snapshot.SNAPSHOT_PREFIX) and
            snap.parent.parent == Path(tempfile.gettempdir())
        )
        if not anchored:
            self.fail(
                f"探针未输出合法快照路径(应落在 <gettempdir>/{_snapshot.SNAPSHOT_PREFIX}*/pack 下), "
                f"拒绝注册 cleanup —— report={report.name} 存在={report.is_file()} "
                f"text={text!r} stdout={proc.stdout!r} stderr={proc.stderr!r}"
            )
        return snap

    def test_respawn_runs_from_snapshot_outside_repo(self) -> None:
        # KEEP=1: 副本在子进程退出时就被删, 要断言它的内容必须先留住
        report = Path(self.tmp.name) / "probe-report.txt"
        proc = _run(
            [str(self.pack / "scripts" / "entry.py")],
            self.repo,
            env={
                "COMMAND_FLOW_SNAPSHOT_KEEP": "1",
                "COMMAND_FLOW_PROBE_OUT": str(report)
            },
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        snap = self._snap_from_probe(proc, report)
        self.addCleanup(lambda: shutil.rmtree(snap.parent, ignore_errors=True))
        self.assertTrue(snap.is_dir(), f"应跑在临时副本上, 实际: {proc.stdout!r}")
        self.assertNotEqual(snap, self.pack, "副本不能就是原包")
        self.assertTrue((snap / "scripts" / "entry.py").is_file(), "副本含包脚本")
        self.assertNotIn(self.repo, snap.parents, "副本必须在仓库之外(否则 rebase 照样碰得到)")
        self.assertEqual(_field(_probe_text(proc, report), "REPO_ROOT="), str(self.repo), "真根经 env 注入(副本向上找不到 .git)")

    def test_snapshot_is_removed_after_run(self) -> None:
        tmp_root = _private_tmp(Path(self.tmp.name))
        before = _snap_dirs(tmp_root)
        proc = _run([str(self.pack / "scripts" / "entry.py")], self.repo, env={"TMPDIR": str(tmp_root)})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(_snap_dirs(tmp_root), before, "正常路径子进程退出即删临时副本(不留垃圾)")

    def test_import_does_not_respawn(self) -> None:
        """守卫在 `__main__` 下 ⇒ `import` 不复制(否则测试 / 复用方每 import 一次就多一份副本)。"""
        tmp_root = _private_tmp(Path(self.tmp.name))
        before = _snap_dirs(tmp_root)
        scripts = self.pack / "scripts"
        code = "import sys; sys.path.insert(0, r'%s'); import entry; print('IMPORTED')" % scripts
        proc = _run(["-c", code], self.repo, env={"TMPDIR": str(tmp_root)})
        self.assertIn("IMPORTED", proc.stdout, proc.stderr)
        self.assertEqual(_snap_dirs(tmp_root), before, "import 不该触发重入")

    def test_snapshot_is_immune_and_new_call_adopts(self) -> None:
        """核心证据: 原包被改写后, **旧副本输出不变**(免疫), **新调用采用新版**(采纳)。"""
        report = Path(self.tmp.name) / "probe-report.txt"
        proc = _run(
            [str(self.pack / "scripts" / "entry.py")],
            self.repo,
            env={
                "COMMAND_FLOW_SNAPSHOT_KEEP": "1",
                "COMMAND_FLOW_PROBE_OUT": str(report)
            },
        )
        snap = self._snap_from_probe(proc, report)
        self.addCleanup(lambda: shutil.rmtree(snap.parent, ignore_errors=True))
        self.assertEqual(_field(_probe_text(proc, report), "MARKER="), "v1")

        _write_entry(self.pack, "v2")  # 模拟内部同步的 rebase 换了本包

        # (a) 跑**旧副本**(SNAPSHOT=1 直入, 不重造) —— 免疫: 仍是 v1
        report_a = Path(self.tmp.name) / "probe-report-a.txt"
        old = _run(
            [str(snap / "scripts" / "entry.py")],
            self.repo,
            env={
                "COMMAND_FLOW_SNAPSHOT": "1",
                "COMMAND_FLOW_PACK_DIR": str(snap),
                "COMMAND_FLOW_REPO_ROOT": str(self.repo),
                "COMMAND_FLOW_PROBE_OUT": str(report_a),
            },
        )
        self.assertEqual(_field(_probe_text(old, report_a), "MARKER="), "v1", f"旧副本必须免疫, 实际: {old.stdout!r}")

        # (b) 原包新调用 → 采纳新版
        report_b = Path(self.tmp.name) / "probe-report-b.txt"
        new = _run([str(self.pack / "scripts" / "entry.py")], self.repo, env={"COMMAND_FLOW_PROBE_OUT": str(report_b)})
        self.assertEqual(_field(_probe_text(new, report_b), "MARKER="), "v2", f"新调用必须采用新版, 实际: {new.stdout!r}")

    def test_exit_code_passthrough(self) -> None:
        _write_entry(self.pack, "x", rc=3)
        proc = _run([str(self.pack / "scripts" / "entry.py")], self.repo)
        self.assertEqual(proc.returncode, 3, f"子进程退出码应原样透传给调用方: {proc.stderr}")


class _ProbeHost:
    """`_snap_from_probe` 的最小宿主桩: 该助手只依赖 `self.fail` —— 直测不必起真 TestCase。"""
    def fail(self, msg: str) -> None:
        raise AssertionError(msg)


class ProbeAnchorTest(unittest.TestCase):
    """探针 PACK_DIR 锚定守卫 —— 26-11-13 移植事故回归阵(T4 报告)。

    沙箱 / AppImage shim 令 respawn 链失败时报告缺席或 stdout 缺 PACK_DIR 行, 旧写法
    `Path(_field(...))` 落空成 `Path("")`, 其 `.parent` 即 `Path(".")` = 测试进程 CWD = 仓库根,
    cleanup 的 `rmtree(snap.parent, ignore_errors=True)` 就把整个仓库(含 .git)递归删空。
    守卫语义(issue 0857 P0+P1a): 侧信道报告文件优先, stdout 解析只作兜底; 解析结果必须命中
    `make_snapshot` 的唯一落点 `<gettempdir>/<SNAPSHOT_PREFIX>*/pack`, 其余一律就地 fail ——
    fail 抛出先于任何 addCleanup 注册(结构保证), 错删路径无从发生。
    """

    # 不存在的报告路径 ⇒ 助手退回 stdout 兜底通道(测纯解析面的用例都用它)
    NO_REPORT = Path(tempfile.gettempdir()) / "probe-anchor-no-such-report"

    @staticmethod
    def _proc(stdout: str) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")

    def _reject(self, stdout: str, report: Path) -> None:
        with self.assertRaises(AssertionError):
            SnapshotEndToEndTest._snap_from_probe(_ProbeHost(), self._proc(stdout), report)

    def test_accepts_only_snapshot_layout(self) -> None:
        good = Path(tempfile.gettempdir()) / (_snapshot.SNAPSHOT_PREFIX + "abc123") / "pack"
        got = SnapshotEndToEndTest._snap_from_probe(
            _ProbeHost(), self._proc(f"PACK_DIR={good}\nMARKER=v1\n"), self.NO_REPORT
        )
        self.assertEqual(got, good)

    def test_side_channel_wins_over_eaten_stdout(self) -> None:
        # stdout 被 shim 吞掉(空)但报告文件在 —— 侧信道必须救回合法路径, 不触发 fail
        good = Path(tempfile.gettempdir()) / (_snapshot.SNAPSHOT_PREFIX + "abc123") / "pack"
        with tempfile.TemporaryDirectory() as td:
            report = Path(td) / "report.txt"
            report.write_text(f"PACK_DIR={good}\nMARKER=v1\n", encoding="utf-8")
            got = SnapshotEndToEndTest._snap_from_probe(_ProbeHost(), self._proc(""), report)
            self.assertEqual(got, good)

    def test_side_channel_garbage_still_fails(self) -> None:
        # 报告文件在但内容坏(如 respawn 链半途死在写文件之前) —— 照样 fail, 不放行
        with tempfile.TemporaryDirectory() as td:
            report = Path(td) / "report.txt"
            report.write_text("PACK_DIR=\n", encoding="utf-8")
            self._reject("", report=report)

    def test_rejects_missing_line(self) -> None:
        self._reject("", self.NO_REPORT)

    def test_rejects_empty_value(self) -> None:
        # `PACK_DIR=` 空值与缺行殊途同归: Path("") 即 Path(".")
        self._reject("PACK_DIR=\nMARKER=v1\n", self.NO_REPORT)

    def test_rejects_path_outside_temp_root(self) -> None:
        self._reject(f"PACK_DIR={Path(tempfile.gettempdir()).parent / 'elsewhere' / 'pack'}\n", self.NO_REPORT)


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
