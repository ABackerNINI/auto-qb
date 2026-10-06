"""my-commit-flow 的自测(v3) —— 闸门引擎 / 占位符展开 / 静态检查 / 配置体检。stdlib `unittest`, 零依赖。

为什么放在包目录而不是项目的 `tests/`: 这份包是**跨项目资产**, 绑进某个仓库的 `tests/`
会把两边耦合起来; 它依赖的是包自己的脚本, 不是那个仓库的 `src/`。
(本项目 `pytest.ini` 的 `testpaths = tests` 也不会收集到它 —— 正合预期; 提交闸门 test.pkg 会跑。)

跑法:
    python <包>/scripts/test_pipeline.py
    uv run pytest .commands -q --no-cov   (test.pkg 的口径)

v3(计划 26-09-28-0157)收掉的旧面: 检查表分类(classify_sync / sync_recipe / behind_rows /
classify_merge_probe)随检查表一起删除 —— 同步行分类改由 test_sync.py 用**真实临时仓库**测。

## 测试计划
- GlobMatchTest                <changed:>/<each:> 的 GLOB 语义(**/ 跨目录)
- ExpandTest                   占位符四类 + 展开失败 + each_limit + 空格引号
- RunGatesTest                 闸门执行: 全过静默 / 失败留末 20 行 / 超时 / 人工闸门不执行 /
                               展开失败不降级 / 无匹配**静默**跳过(v2 的那条 WARN 已废)
- GitRetryTest                 git 命令: 单次 20s 超时 + 有界重试(网络子命令失败即重试 / 非幂等本地写
                               不重试 / 只读命令仅超时与瞬时签名重试 / attempts=1 关重试 / retry_note)
- MirrorNoRetryTest            GitHub 镜像只给超时不给重试 —— 静态守住 push.py 那一行(attempts=1)
- PackageRefreshTest / ReloadConfigTest  (已退役: 快照自举取代了「热刷新 / 配置重取」两条治标机制,
                              守阵迁到 test_snapshot.py —— 机制没了, 测机制的用例留着就是测不到现实的死守阵)
- SmokeSafetyTest              冒烟安全: 配置里两条 `--help` 闸门必须带 `|--with-safety`;
                               <each:> 接受该后缀; 探针摘掉「无参即真动作」脚本(超时按不安全)
- ShortTest                    失败明细里的根路径压缩
- NoTrackingRefTest            判落后一律 ls-remote 真值 —— 静态扫描禁止 refs/remotes 快照与 status -sb
- StaticNameTest               AST 找未定义名(冷门分支 NameError, push.py 曾潜伏过一例)
- ConfigProblemsTest           未知键 / timeout 非法 / 生成物自动化解键类型 → STOP
"""

from __future__ import annotations

import ast
import builtins
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _pipeline  # noqa: E402
from _ship_config import config_problems, find_root, load_config  # noqa: E402

PY = sys.executable


def ctx(root: Path, changed: list[str], each_limit: int = 99) -> dict:
    return {"root": root, "changed": changed, "each_limit": each_limit}


class GlobMatchTest(unittest.TestCase):
    def test_star_matches_across_dirs(self) -> None:
        self.assertTrue(_pipeline._glob_match("src/auto_qb/a.py", "*.py"))
        self.assertFalse(_pipeline._glob_match("src/auto_qb/a.py", "*.md"))

    def test_double_star_with_prefix(self) -> None:
        pat = ".agents/skills/**/scripts/*.py"
        self.assertTrue(_pipeline._glob_match(".agents/skills/my-commit-flow/scripts/sync.py", pat))
        self.assertTrue(_pipeline._glob_match(".agents/skills/a/b/scripts/x.py", pat))
        self.assertFalse(_pipeline._glob_match(".agents/skills/a/b/x.py", pat))


class ExpandTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".agents" / "skills" / "create-issue").mkdir(parents=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_root_placeholder(self) -> None:
        cmds, skip = _pipeline.expand_run("python <root>/scripts/x.py", ctx(self.root, []))
        self.assertIsNone(skip)
        self.assertEqual(cmds, [f"python {self.root}/scripts/x.py"])

    def test_changed_placeholder(self) -> None:
        cmds, skip = _pipeline.expand_run("yapf -i <changed:*.py>", ctx(self.root, ["src/b.py", "src/a.py", "a.md"]))
        self.assertIsNone(skip)
        self.assertEqual(cmds, ["yapf -i src/a.py src/b.py"])  # 排序后拼接

    def test_changed_no_match_is_skipped(self) -> None:
        cmds, skip = _pipeline.expand_run("yapf -i <changed:*.py>", ctx(self.root, ["a.md"]))
        self.assertEqual(cmds, [])
        self.assertIn("无匹配文件", skip or "")

    def test_each_placeholder_fan_out(self) -> None:
        cmds, skip = _pipeline.expand_run(
            "python <each:.agents/skills/**/scripts/*.py> --help",
            ctx(self.root, [".agents/skills/a/scripts/x.py", ".agents/skills/b/scripts/y.py"])
        )
        self.assertIsNone(skip)
        self.assertEqual(len(cmds), 2)
        self.assertTrue(all(c.endswith("--help") for c in cmds))

    def test_each_limit_exceeded(self) -> None:
        files = [f".agents/skills/s{i}/scripts/x.py" for i in range(3)]
        with self.assertRaises(_pipeline.ExpandError) as raised:
            _pipeline.expand_run("python <each:*.py> --help", ctx(self.root, files, each_limit=2))
        self.assertIn("each_limit", str(raised.exception))

    def test_skill_dir_placeholder(self) -> None:
        cmds, skip = _pipeline.expand_run("python <skill-dir:create-issue>/scripts/gen.py --check", ctx(self.root, []))
        self.assertIsNone(skip)
        found = _pipeline.find_skill_dir("create-issue", self.root)
        self.assertEqual(cmds, [f"python {found}/scripts/gen.py --check"])

    def test_skill_dir_missing_is_error(self) -> None:
        with self.assertRaises(_pipeline.ExpandError) as raised:
            _pipeline.expand_run("python <skill-dir:create-issues>/x.py", ctx(self.root, []))
        self.assertIn("找不到 skill 目录", str(raised.exception))

    def test_unknown_placeholder_is_error(self) -> None:
        with self.assertRaises(_pipeline.ExpandError) as raised:
            _pipeline.expand_run("yapf -i <改过的 py 文件>", ctx(self.root, []))
        self.assertIn("无法展开", str(raised.exception))

    def test_quotes_paths_with_spaces(self) -> None:
        cmds, _ = _pipeline.expand_run("yapf -i <changed:*.py>", ctx(self.root, ["src/a b.py"]))
        self.assertEqual(cmds, ['yapf -i "src/a b.py"'])


class RunGatesTest(unittest.TestCase):
    """v3 契约: 闸门全过**静默**(没有 PASS 行), 失败才说话; 无匹配文件是按设计跳过, 不是 WARN。"""
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _gate(self, cmd: str, auto: bool = True, timeout: int = 60) -> dict:
        return {"match": [""], "run": [cmd], "auto": auto, "timeout": timeout, "note": "测试闸门"}

    def test_passing_gate_is_silent(self) -> None:
        failures, manual, ran = _pipeline.run_gates([self._gate(f'"{PY}" -c "pass"')], ctx(self.root, []))
        self.assertEqual(failures, [])
        self.assertEqual(manual, [])
        self.assertEqual(ran, 1)

    def test_failing_gate_reports_note_rc_tail(self) -> None:
        failures, _, ran = _pipeline.run_gates(
            [self._gate(f'"{PY}" -c "import sys; print(\'boom\'); sys.exit(3)"')], ctx(self.root, [])
        )
        self.assertEqual(len(failures), 1)
        note, cmd, rc, secs, tail = failures[0]
        self.assertEqual((note, rc), ("测试闸门", 3))
        self.assertIn("boom", tail)  # 失败输出要留末 20 行供定位
        self.assertGreater(secs, 0)
        self.assertEqual(ran, 1)

    def test_timeout_is_failure(self) -> None:
        failures, _, _ = _pipeline.run_gates(
            [self._gate(f'"{PY}" -c "import time; time.sleep(5)"', timeout=1)], ctx(self.root, [])
        )
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0][2], -1)
        self.assertIn("超时", failures[0][4])

    def test_manual_gate_is_not_executed(self) -> None:
        cmd = f'"{PY}" -c "import sys; sys.exit(3)"'
        failures, manual, ran = _pipeline.run_gates([self._gate(cmd, auto=False)], ctx(self.root, []))
        self.assertEqual((failures, ran), ([], 0))
        self.assertEqual(manual, [cmd])

    def test_expand_failure_of_auto_gate_is_failure(self) -> None:
        failures, manual, _ = _pipeline.run_gates([self._gate("python <nope:x>")], ctx(self.root, []))
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0][2], -2)  # 展开失败: 不是 git 的码, 但必须停
        self.assertEqual(manual, [])  # 不降级成打印

    def test_no_match_skip_is_silent(self) -> None:
        gate = {"match": [""], "run": ["python <each:src/**/*.py> --help"], "auto": True, "note": "t"}
        failures, _, ran = _pipeline.run_gates([gate], ctx(self.root, ["docs/a.md"]))
        self.assertEqual((failures, ran), ([], 0))  # 按设计跳过, 连 WARN 都没有

    def test_gates_for_empty_match_hits_everything(self) -> None:
        gates = [{"match": [""], "run": ["x"], "auto": True}]
        self.assertEqual(len(_pipeline.gates_for(["src/a.py"], gates)), 1)
        self.assertEqual(_pipeline.gates_for(["src/a.py"], [{"match": ["docs/"], "run": ["x"]}]), [])


class GitRetryTest(unittest.TestCase):
    """git 命令的**单次超时 + 有界重试**(2026-10-06 用户口径: Gitee 间歇性卡住 → 提交常被拆成
    「未推送 + 手工补推」)。判据单点在 `_pipeline._retryable`, 机制在 `run_git`。

    run_capture 用替身: 真起进程测不出「重试了几次」, 也没必要为一条用例真等 20s 超时。
    退避改成 0 —— 否则每条用例白等三个 1s。
    """
    def setUp(self) -> None:
        self.calls: list[list[str]] = []
        self.timeouts: list[float] = []
        self.script: list[tuple[int, str]] = []  # 第 N 次调用的 (rc, stderr); 用尽后沿用最后一个
        orig_capture, orig_backoff = _pipeline.run_capture, _pipeline.GIT_RETRY_BACKOFF

        def _fake(args, cwd=None, timeout=None, shell=False, env=None):
            self.calls.append(list(args))
            self.timeouts.append(timeout)
            rc, err = self.script[min(len(self.calls), len(self.script)) - 1]
            return subprocess.CompletedProcess(args, rc, "", err)

        _pipeline.run_capture = _fake
        _pipeline.GIT_RETRY_BACKOFF = 0.0
        self.addCleanup(lambda: setattr(_pipeline, "run_capture", orig_capture))
        self.addCleanup(lambda: setattr(_pipeline, "GIT_RETRY_BACKOFF", orig_backoff))

    def _run(self, *args, **kwargs):
        return _pipeline.run_git(["git", *args], **kwargs)

    def test_network_subcommand_retries_until_success(self) -> None:
        """网络子命令失败即重试 —— Gitee 的失败签名靠不住(网关 502 / 代理重置 / TLS 抖动), 白名单必漏。"""
        self.script = [(128, "Recv failure"), (128, "Recv failure"), (0, "")]
        proc = self._run("push", "gitee", "develop")
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.attempts_used, 3)
        self.assertEqual(len(self.calls), 3)

    def test_all_attempts_failed_is_failure(self) -> None:
        """全部尝试都失败才判失败 —— 3 次用尽后把最后一次的结果交出去。"""
        self.script = [(128, "Recv failure")]
        proc = self._run("push", "gitee", "develop")
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual((proc.attempts_used, len(self.calls)), (3, 3))

    def test_attempts_one_disables_retry(self) -> None:
        """GitHub 镜像: 只给超时, 不给重试 —— attempts=1 时连网络子命令也只跑一次。"""
        self.script = [(128, "Recv failure")]
        proc = self._run("push", "github", "develop", attempts=1)
        self.assertEqual((proc.attempts_used, len(self.calls)), (1, 1))

    def test_timeout_is_passed_through(self) -> None:
        self.script = [(0, "")]
        self._run("fetch", "gitee", "develop")
        self.assertEqual(self.timeouts, [_pipeline.GIT_TIMEOUT])

    def test_non_idempotent_local_command_is_not_retried(self) -> None:
        """非幂等本地写只给超时、不给重试: 超时被杀 ≠ 没执行完 —— 再跑一次轻则把
        "nothing to commit" 当成失败, 重则 amend 又挪一次 hash 把步骤链写坏。"""
        for sub in ("commit", "rebase", "merge", "reset", "checkout", "rm"):
            self.calls.clear()
            self.script = [(-1, "卡死")]
            proc = self._run(sub, "x")
            self.assertEqual(len(self.calls), 1, f"{sub} 不该被重试")
            self.assertEqual(proc.attempts_used, 1, sub)

    def test_readonly_command_retries_on_timeout(self) -> None:
        self.script = [(-1, "卡死 (20s, 进程树已杀)"), (0, "")]
        proc = self._run("status", "--porcelain")
        self.assertEqual((proc.returncode, proc.attempts_used), (0, 2))

    def test_nonzero_is_a_normal_answer_and_is_not_retried(self) -> None:
        """`cat-file -e` 判路径在不在 HEAD —— 非 0 是**正常答案**, 盲重试会把每次查询拖成 3 倍耗时。"""
        self.script = [(1, "")]
        proc = self._run("cat-file", "-e", "HEAD:x")
        self.assertEqual((proc.returncode, proc.attempts_used, len(self.calls)), (1, 1, 1))

    def test_readonly_command_retries_on_transient_signature(self) -> None:
        self.script = [(1, "fatal: unable to access 'https://…': SSL_ERROR_SYSCALL"), (0, "")]
        proc = self._run("config", "--get-regexp", r"^http")
        self.assertEqual((proc.returncode, proc.attempts_used), (0, 2))

    def test_subcommand_skips_dash_c_prefix(self) -> None:
        """`-c k=v` 是**两个** argv 元素 —— 镜像推送带 `-c http.x.proxy=` 前缀, 判错就漏掉重试档位。"""
        self.assertEqual(_pipeline._subcommand(["-c", "http.x.proxy=", "push", "gitee", "develop"]), "push")
        self.assertEqual(_pipeline._subcommand(["-c", "a=b", "-c", "c=d", "ls-remote", "o", "dev"]), "ls-remote")
        self.assertEqual(_pipeline._subcommand(["--no-pager", "status"]), "status")
        self.assertEqual(_pipeline._subcommand(["-c", "a=b"]), "")

    def test_subcommand_skips_git_executable(self) -> None:
        """❗`run_git` 传的是**完整 argv**(首元素是 `git`) —— 不跳它就把子命令读成 "git",
        三档判据全部失效、重试静默失效(2026-10-06 实写时踩到)。"""
        self.assertEqual(_pipeline._subcommand(["git", "push", "gitee", "develop"]), "push")
        self.assertEqual(_pipeline._subcommand(["git.exe", "commit", "-F", "m"]), "commit")
        self.assertEqual(_pipeline._subcommand([r"C:\Program Files\Git\bin\git.exe", "fetch", "o"]), "fetch")

    def test_retry_note_only_when_retried(self) -> None:
        """失败行里的备注: 没重试就不啰嗦, 重试了才写次数(否则读的人以为命令没试过就报错)。"""
        self.script = [(0, "")]
        self.assertEqual(_pipeline.retry_note(self._run("fetch", "gitee", "develop")), "")
        self.script = [(128, "Recv failure")]
        self.assertEqual(_pipeline.retry_note(self._run("fetch", "gitee", "develop")), "(已重试 2 次)")

    def test_git_check_raises_with_retry_note(self) -> None:
        """`git(check=True)` 的 RuntimeError 也要带重试次数 —— 排障时看得出命令自己试过几次。"""
        self.script = [(128, "Recv failure")]
        with self.assertRaises(RuntimeError) as raised:
            _pipeline.git("push", "gitee", "develop")
        self.assertIn("已重试 2 次", str(raised.exception))

    def test_defaults_are_20s_and_3_attempts(self) -> None:
        """用户口径的默认值: 单次 20s, 重试 3 次(可用环境变量覆盖, 覆盖时不判)。"""
        if "COMMAND_FLOW_GIT_TIMEOUT" not in os.environ:
            self.assertEqual(_pipeline.GIT_TIMEOUT, 20)
        if "COMMAND_FLOW_GIT_ATTEMPTS" not in os.environ:
            self.assertEqual(_pipeline.GIT_ATTEMPTS, 3)


class MirrorNoRetryTest(unittest.TestCase):
    """GitHub 镜像**只给超时, 不给重试**(用户口径 2026-10-06) —— 静态守住 push.py 那一行。

    为什么静态守: 这条口径没有行为出口(镜像成功失败都不提), 只能靠源码形态守 —— 删掉
    `attempts=1` 会让镜像也跟着重试 3 次, 而输出里**一点痕迹都没有**。
    """

    PUSH = Path(__file__).resolve().parent / "push.py"

    def test_mirror_push_passes_attempts_1(self) -> None:
        code = [l for l in self.PUSH.read_text(encoding="utf-8").splitlines() if l.lstrip().startswith("git_run(")]
        mirror = [l for l in code if "mirror" in l]
        self.assertEqual(len(mirror), 1, f"镜像推送的调用行数变了(应恰 1 条): {mirror}")
        self.assertIn("attempts=1", mirror[0], "镜像必须 attempts=1(只给超时不给重试): " + mirror[0])

    def test_main_push_keeps_default_retry(self) -> None:
        """主线推送走默认重试 —— 别在 push.py 里又套一层(两层各重试 = 最多 6 次尝试)。"""
        text = self.PUSH.read_text(encoding="utf-8")
        self.assertIn('git_run("push", main, branch)', text)
        self.assertNotIn('git_run("push", main, branch, attempts=1)', text)


class SmokeSafetyTest(unittest.TestCase):
    """闸门冒烟只给脚本加 `--help` —— 而 `--help` 未必被脚本认。

    2026-10-03 实测: `sync.py --help` 把陌生参数当无参, **真的同步了一次**; `push.py --help`
    同款, 那会真的推。修复两头: ①展开支持 `|--with-safety` 过滤; ②本用例机检**配置里那两条
    冒烟闸门确实带了过滤** —— 少了它, 下一个写"无参即真动作"的人会再踩一次(且是静默的)。
    """
    CONFIG = Path(__file__).resolve().parent.parent / ".my-commit-flow.toml"

    def test_smoke_gates_use_safety_filter(self) -> None:
        text = self.CONFIG.read_text(encoding="utf-8")
        # 只看真正会执行的 `run = [...]` 行 —— 注释里会提到 --help(sync.py / push.py 的教训),
        # 拿注释当判据会误报(写这条守卫时确实踩了一次)。
        smoke = [
            line
            for line in text.splitlines() if line.lstrip().startswith("run") and "<each:" in line and "--help" in line
        ]
        self.assertTrue(smoke, "配置里找不到脚本冒烟闸门(删了? 那本条守卫该跟着改)")
        for line in smoke:
            self.assertIn(
                "--with-safety>",
                line,
                "冒烟闸门没带 |--with-safety —— `--help` 会被未知参数当无参, 对 sync.py/push.py "
                "就是真的同步 / 真的推送:\n  " + line.strip(),
            )

    def test_each_re_accepts_safety_suffix(self) -> None:
        m = _pipeline.EACH_RE.search("<each:.commands/**/scripts/*.py|--with-safety> --help")
        self.assertIsNotNone(m)
        self.assertEqual((m.group(1), m.group(2)), (".commands/**/scripts/*.py", "--with-safety"))
        # 不带后缀仍是老语义(现有闸门逐字不变)
        m = _pipeline.EACH_RE.search("<each:src/**/*.py> --help")
        self.assertEqual((m.group(1), m.group(2)), ("src/**/*.py", None))

    def test_safety_filter_drops_parameterless_action_scripts(self) -> None:
        """探针判据是**问脚本自己**(`--safety` 吐 `action-without-args`), 不是文件名规则。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts = root / ".commands" / "p" / "scripts"
            scripts.mkdir(parents=True)
            (scripts / "doit.py").write_text(
                "import sys\nprint('action-without-args') if '--safety' in sys.argv else sys.exit(0)\n",
                encoding="utf-8",
            )
            (scripts / "check.py").write_text(
                "import sys\nprint('read-only-default') if '--safety' in sys.argv else sys.exit(0)\n",
                encoding="utf-8",
            )
            (scripts / "hang.py").write_text(
                "import time\ntime.sleep(60)\n", encoding="utf-8"
            )  # 探针会超时 —— 按不安全处理, 不拿 --help 去赌
            changed = [".commands/p/scripts/doit.py", ".commands/p/scripts/check.py", ".commands/p/scripts/hang.py"]
            ctx = {"root": root, "changed": changed, "each_limit": 99}
            cmds, skip = _pipeline.expand_run("python <each:.commands/**/scripts/*.py|--with-safety> --help", ctx)
            self.assertIsNone(skip)
            self.assertEqual(len(cmds), 1)  # 只有 check.py 留下
            self.assertIn("check.py", cmds[0])
            self.assertNotIn("doit.py", cmds[0])

    def test_safety_filter_all_dropped_is_skip_not_silent_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts = root / "s"
            scripts.mkdir(parents=True)
            (scripts / "doit.py").write_text("print('action-without-args')\n", encoding="utf-8")
            ctx = {"root": root, "changed": ["s/doit.py"], "each_limit": 99}
            cmds, skip = _pipeline.expand_run("python <each:s/*.py|--with-safety> --help", ctx)
            self.assertEqual(cmds, [])
            self.assertIn("安全过滤", skip or "")


class ShortTest(unittest.TestCase):
    def test_short_strips_root_prefix(self):
        root = Path("C:/repo")
        self.assertEqual(_pipeline._short("python C:/repo/a.py", root), "python a.py")
        self.assertEqual(_pipeline._short(r"python C:\repo\a.py", root), "python a.py")


class NoTrackingRefTest(unittest.TestCase):
    """落后/领先判据一律走 ls-remote 现查的远端真值 —— 本工具 shell 里 refs/remotes/* 的
    写入会被静默丢弃, 跟踪 ref 是陈年快照, 曾据此报出假"落后 5"; status -sb 同理。"""

    SCRIPTS = ("sync.py", "push.py", "commit.py")

    def test_ahead_behind_never_reads_tracking_ref(self) -> None:
        here = Path(__file__).resolve().parent
        for name in self.SCRIPTS:
            for i, line in enumerate((here / name).read_text(encoding="utf-8").splitlines(), 1):
                if "--left-right" in line:
                    self.assertNotIn(
                        "{MAIN}/{BRANCH}",
                        line,
                        f"{name}:{i} 在用 refs/remotes 快照算 ahead/behind —— 该写入会被静默丢弃, "
                        "判据必须是 ls-remote 拿到的远端 tip 对比本地 HEAD",
                    )
                self.assertNotIn('"-sb"', line, f"{name}:{i} 在用 status -sb 的快照判据")


SPECIALS = {"__name__", "__file__", "__doc__", "__package__", "__spec__", "__loader__", "__builtins__", "__debug__"}


def _bound(node: ast.AST) -> set[str]:
    """某个作用域里**被绑定**的名字 —— 赋值 / 参数 / for / with / except / 推导 / 嵌套定义 / import。"""
    names: set[str] = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            names.add(n.id)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(n.name)
        elif isinstance(n, ast.arg):
            names.add(n.arg)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for alias in n.names:
                names.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(n, ast.ExceptHandler) and n.name:
            names.add(n.name)
        elif isinstance(n, ast.Global):
            names.update(n.names)
        elif isinstance(n, ast.alias):
            names.add((n.asname or n.name).split(".")[0])
    return names


def _loaded(node: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}


def undefined_names(path: Path) -> set[str]:
    """静态找出"用了但从未定义"的名字 —— 冷门分支里的 NameError 只有靠这个才抓得到。

    push.py 曾把 `MIRROR_URL_NOW` 写成 `MIRROR_URL`: 那个分支只有"没找到镜像远端"时才走,
    平时主线推送失败会提前 return, 于是这个未定义名在真机上潜伏到被人踩到为止。
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    module_bound = _bound(tree) | set(dir(builtins)) | SPECIALS
    bad: set[str] = set()

    def walk(node: ast.AST, inherited: set[str]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                own = _bound(child)
                scope = inherited | own
                bad.update(_loaded(child) - scope)
                walk(child, scope)  # 闭包: 外层绑定的名字对内层可见
            else:
                walk(child, inherited)

    bad.update(_loaded(tree) - module_bound)
    walk(tree, module_bound)
    return bad


class StaticNameTest(unittest.TestCase):
    SCRIPTS = ["_ship_config.py", "_pipeline.py", "_snapshot.py", "sync.py", "push.py", "commit.py", "verify_ref.py"]
    # memory-bank skill 的脚本同属"改了就可能留下未定义名"的资产, 一并纳入
    # (2026-09-22 目录化重构新增了 4 个; 之前只扫本包自己那 5 个)。
    OTHER_SCRIPTS = (
        ".agents/skills/memory-bank/scripts/_common.py",
        ".agents/skills/memory-bank/scripts/gen_tasks_index.py",
        ".agents/skills/memory-bank/scripts/gen_kb_index.py",
        ".agents/skills/memory-bank/scripts/check_kb_structure.py",
    )

    def test_no_undefined_names_in_other_skill_scripts(self) -> None:
        root = find_root()
        missing = [rel for rel in self.OTHER_SCRIPTS if not (root / rel).is_file()]
        self.assertFalse(missing, f"清单里的脚本不存在(改名了? 同步本清单): {missing}")
        bad = [f"{rel}: {', '.join(sorted(undefined_names(root / rel)))}" for rel in self.OTHER_SCRIPTS]
        bad = [b for b in bad if not b.endswith(": ")]
        self.assertFalse(bad, "memory-bank skill 脚本里有未定义名:\n" + "\n".join(bad))

    def test_no_undefined_names_in_scripts(self) -> None:
        bad = [
            f"{name}: {', '.join(sorted(undefined_names(Path(__file__).resolve().parent / name)))}"
            for name in self.SCRIPTS
        ]
        bad = [line for line in bad if not line.endswith(": ")]
        self.assertEqual(bad, [], "存在未定义的名字(拼写错 / 改名漏改), 会在冷门分支上 NameError")

    def test_checker_actually_catches_undefined_names(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as fh:
            fh.write("def f():\n    return MIRROR_URL\n")
            tmp = Path(fh.name)
        try:
            self.assertEqual(undefined_names(tmp), {"MIRROR_URL"})
        finally:
            tmp.unlink()

    def test_checker_is_not_fooled_by_closure(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as fh:
            fh.write("def outer():\n    x = 1\n    def inner():\n        return x\n    return inner\n")
            tmp = Path(fh.name)
        try:
            self.assertEqual(undefined_names(tmp), set())  # 闭包变量不算未定义
        finally:
            tmp.unlink()


class ConfigProblemsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / ".my-commit-flow.toml"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _problems(self, text: str) -> list[tuple[str, str]]:
        self.path.write_text(text, encoding="utf-8")
        cfg, _ = load_config(explicit=str(self.path))
        return config_problems(cfg, self.path)

    BASE = 'confirmed = true\nred_lines = ["a"]\n'

    def test_unknown_gate_key_is_stop(self) -> None:
        problems = self._problems(self.BASE + '[[gates]]\nmatch = ["src/"]\nrun = ["x"]\nauto_run = true\n')
        self.assertTrue(any(lvl == "STOP" and "auto_run" in msg for lvl, msg in problems))

    def test_unknown_top_key_is_stop(self) -> None:
        problems = self._problems(self.BASE + "staged_panicc = 5\n")
        self.assertTrue(any(lvl == "STOP" and "staged_panicc" in msg for lvl, msg in problems))

    def test_bad_timeout_is_stop(self) -> None:
        problems = self._problems(self.BASE + '[[gates]]\nmatch = ["src/"]\nrun = ["x"]\ntimeout = 0\n')
        self.assertTrue(any(lvl == "STOP" and "timeout" in msg for lvl, msg in problems))

    def test_bad_auto_resolve_type_is_stop(self) -> None:
        # 1 不是 bool —— 按错类型动作会让化解路径静默失效, 必须 STOP
        problems = self._problems(self.BASE + "auto_resolve_generated = 1\n")
        self.assertTrue(any(lvl == "STOP" and "auto_resolve_generated" in msg for lvl, msg in problems))

    def test_bad_generated_cmd_type_is_stop(self) -> None:
        problems = self._problems(self.BASE + "generated_list_cmd = 5\n")
        self.assertTrue(any(lvl == "STOP" and "generated_list_cmd" in msg for lvl, msg in problems))

    def test_valid_generated_keys_have_no_stop(self) -> None:
        problems = self._problems(
            self.BASE + "auto_resolve_generated = true\ngenerated_list_cmd = \"x\"\ngenerated_regen_cmd = \"y\"\n"
        )
        self.assertFalse([p for p in problems if p[0] == "STOP"])

    def test_valid_config_has_no_stop(self) -> None:
        problems = self._problems(self.BASE + '[[gates]]\nmatch = ["src/"]\nrun = ["x"]\nauto = true\ntimeout = 60\n')
        self.assertFalse([p for p in problems if p[0] == "STOP"])

    def test_unconfirmed_draft_is_warn(self) -> None:
        problems = self._problems('confirmed = false\nred_lines = ["a"]\n')
        self.assertTrue(any(lvl == "WARN" and "初稿" in msg for lvl, msg in problems))


if __name__ == "__main__":
    raise SystemExit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
