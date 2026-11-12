"""`mutants.py` 的守阵 —— 两块核心: verify 的「KILLED 看新增失败差集」判定 + S4 容器形态面。

背景: 全量套件在 Linux 侧曾有 3 个既有平台失败(`test_alias_fs` ×2 · `test_relocate_paths` ×1,
2026-10-30 已修绿), 老口径「套件里有 failed 就算 KILLED」⇒ 每条候选恒判 KILLED(全杀 = 没杀),
verify 结构性失效。本文件把判据钉在**差集**上: `本次失败 - 基线失败 非空 ⇒ KILLED`。

S4 起脚本后端 wsl.exe -> docker exec(计划 26-11-12-0152 §04 S4 / §06 D6): 容器形态面
(镜像仓路径派生/校验、venv 就绪路线、容器内 bash 脚本)在本文件同步钉面。

跑法: python .commands/mutants/scripts/test_mutants.py  ·  uv run pytest .commands -q --no-cov (test.pkg 口径)

## 测试计划
- FailIdParseTest      short test summary 的 FAILED / ERROR 行解析(含 `- 消息` 尾巴与收集期 ERROR)
- SummaryParseTest     取最后一行 pytest 汇总; 无汇总行时返回空串
- VerdictTest          基线常红 + 无新增失败 ⇒ SURVIVED(本条就是原 bug); 有新增失败 ⇒ KILLED;
                       APPLYFAIL / rc=124 / 无汇总 三种「未判定」不得落进 SURVIVED
- SuiteCmdTest         全套件命令不得带 `-x`(会停在既有失败上), 必须带 `-B` + 禁写字节码 +
                       AUTO_QB_TESTBED=1(容器内挂钟基准按 testbed 档判, 与 test.linux 同口径)
- SuiteCmdDeselectTest 全套件命令自动带 FLAKY_DESELECT 的 --deselect, 且保留既有并行度参数
- SetConfRenderTest    timeout_multiplier 显式写进 [tool.mutmut](默认=mutmut 默认); 覆盖式重写不残留旧值; 非正值拒绝
- RunHeaderTest        结果文件账本头记录 target/池/并行度/timeout_multiplier/镜像HEAD/工具版本, 不与 @@@ 明细格式冲突
- DeselectTableTest     DEFAULT_DESELECT / FLAKY_DESELECT 条目必须指向存在的测试文件与 def; 漂移即判红
- DoneIdsTest           未判定(APPLY_FAIL/TIMEOUT/FLAKY/UNKNOWN)不进 done; KILLED/SURVIVED 进 done
- MirrorPathTest        镜像仓路径派生(--target slug -> /root/auto-qb-tests/mutation/<pkg>)与校验:
                        Windows/MSYS 改写路径与相对路径响亮拒绝; --mirror 显式优先; 都缺时 require 报错
- VenvPrepTest          镜像仓 venv 就绪走 cp 模板 + uv export/pip delta(R4 路线), 不得出现 uv sync; 失败行带 NEXT
- MirrorStateTest       镜像仓三态: 目录不存在才 clone; .git 缺失 ⇒ Fail 且不 clone; refresh 走 fetch
- RegistryPrecheckTest  注册表缺失 ⇒ 拦; 0 字节 ⇒ 按「注册表为空」拦(给同一句 run 提示); 非空不误伤
- CandidateIdsTest      候选清单文件读不到 ⇒ [FAIL] 停手(不裸 traceback); --ids-file 按行修剪丢空行;
                        --from-report 按 @@@ 行解析 + --only-status 过滤
- StatusScriptTest      status 单仓脚本回显旧口径键 + 镜像缺失 [FAIL] 行与 exit 3; 全列脚本根缺失不回非零;
                        mutmut 缺失时 not_killed 标 '?'(工具就位性兜底, 不让 0 假装全杀干净)
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mutants  # noqa: E402
import set_conf  # noqa: E402

#: 历史上 Linux 侧的真实基线(3 条平台失败, 现已修绿) —— 保留当夹具, 代表任意「红基线」
LINUX_BASELINE = {
    "tests/test_alias_fs.py::test_win_interactive_session_station_failures",
    "tests/test_alias_fs.py::test_win_create_junction_kernel_failure_cleans_up",
    "tests/test_relocate_paths.py::test_precheck_empty_file_table_skips_representative_probe",
}

#: S4 容器形态的默认镜像仓根(与 mutants.MUTATION_ROOT 同源断言见 MirrorPathTest)
MUT_ROOT = "/root/auto-qb-tests/mutation"


def _suite_output(failed: list[str], *, passed: int = 4144, extra: str = "") -> str:
    """拼一份像真的 pytest 输出: 进度行 + short test summary + 汇总行。"""
    lines = ["......F...", ""]
    if failed:
        lines += ["=========================== short test summary info ============================"]
        lines += [f"FAILED {node}" for node in failed]
    lines.append("")
    tail = f"{len(failed)} failed, " if failed else ""
    lines.append(f"{tail}{passed} passed, 10 skipped in 25.51s")
    if extra:
        lines.append(extra)
    return "\n".join(lines)


class FailIdParseTest(unittest.TestCase):
    def test_reads_failed_and_error_with_message_tail(self):
        text = "\n".join(
            [
                "FAILED tests/a.py::test_x - AssertionError: boom",
                "ERROR tests/b.py::test_y",
                "PASSED tests/c.py::test_z",
                "3 failed, 1 passed in 1.0s",
            ]
        )
        self.assertEqual(mutants._fail_ids(text), {"tests/a.py::test_x", "tests/b.py::test_y"})

    def test_collection_error_has_no_node_suffix(self):
        self.assertEqual(mutants._fail_ids("ERROR tests/test_broken.py"), {"tests/test_broken.py"})

    def test_progress_lines_are_not_mistaken_for_failures(self):
        self.assertEqual(mutants._fail_ids(_suite_output([])), set())


class SummaryParseTest(unittest.TestCase):
    def test_picks_last_summary_line(self):
        text = "4144 passed in 1s\nnoise\n3 failed, 4144 passed, 10 skipped in 25.51s\n"
        self.assertEqual(mutants._summary_of(text), "3 failed, 4144 passed, 10 skipped in 25.51s")

    def test_empty_when_crashed_without_summary(self):
        self.assertEqual(mutants._summary_of("Traceback (most recent call last):\n  boom"), "")


class VerdictTest(unittest.TestCase):
    def test_red_baseline_without_new_failure_is_survived(self):
        """原 bug: 基线常红 ⇒ 老口径判 KILLED; 正确结论是这条变异没被套件抓到。"""
        text = _suite_output(sorted(LINUX_BASELINE))
        verdict, _ = mutants._verdict(1, text, LINUX_BASELINE)
        self.assertEqual(verdict, "SURVIVED")

    def test_red_baseline_with_new_failure_is_killed(self):
        text = _suite_output(sorted(LINUX_BASELINE) + ["tests/test_rules.py::test_new"])
        verdict, summary = mutants._verdict(1, text, LINUX_BASELINE)
        self.assertEqual(verdict, "KILLED")
        self.assertIn("tests/test_rules.py::test_new", summary)

    def test_green_baseline_failure_is_killed(self):
        verdict, _ = mutants._verdict(1, _suite_output(["tests/a.py::test_x"]), set())
        self.assertEqual(verdict, "KILLED")

    def test_unreproducible_new_failure_is_flaky_not_killed(self):
        """套件里混着 flaky 用例(实测 test_hr_discovery 端口绑定随机红) ⇒ 复现不了就不能记 KILLED。"""
        text = _suite_output(sorted(LINUX_BASELINE) + ["tests/test_hr_discovery.py::test_start_binds_first_free"])
        verdict, summary = mutants._verdict(1, text, LINUX_BASELINE, reconfirmed=False)
        self.assertEqual(verdict, "FLAKY")
        self.assertIn("未复现", summary)

    def test_reproducible_new_failure_stays_killed(self):
        text = _suite_output(sorted(LINUX_BASELINE) + ["tests/a.py::test_x"])
        self.assertEqual(mutants._verdict(1, text, LINUX_BASELINE, reconfirmed=True)[0], "KILLED")

    def test_green_baseline_all_green_is_survived(self):
        verdict, _ = mutants._verdict(0, _suite_output([]), set())
        self.assertEqual(verdict, "SURVIVED")

    def test_partial_baseline_failure_is_not_a_kill(self):
        """变异体让基线里某条失败「少了一条」也不算 KILLED —— 判据只看新增。"""
        text = _suite_output(sorted(LINUX_BASELINE)[:1])
        self.assertEqual(mutants._verdict(1, text, LINUX_BASELINE)[0], "SURVIVED")

    def test_apply_failure_is_not_counted_as_survived(self):
        self.assertEqual(mutants._verdict(9, "APPLYFAIL", LINUX_BASELINE)[0], "APPLY_FAIL")

    def test_apply_failure_keeps_reason_for_triage(self):
        """`apply` 报成功但没落地(缓存与源码对不上)也会走 APPLYFAIL —— 理由要留在结果文件里。"""
        text = "APPLYFAIL 变异未落地(apply 后 src/ 无改动)\n"
        verdict, reason = mutants._verdict(9, text, LINUX_BASELINE)
        self.assertEqual(verdict, "APPLY_FAIL")
        self.assertIn("未落地", reason)

    def test_timeout_is_undetermined_not_survived(self):
        self.assertEqual(mutants._verdict(124, "", LINUX_BASELINE)[0], "TIMEOUT")

    def test_crash_without_summary_is_unknown(self):
        self.assertEqual(mutants._verdict(3, "ImportError: boom", LINUX_BASELINE)[0], "UNKNOWN")


class SuiteCmdTest(unittest.TestCase):
    def test_no_x_flag_and_no_bytecode(self):
        """`-x` 会停在第一条**既有**失败上 ⇒ 变异体根本没被执行; 旧 .pyc 会让判定读到上一条变异体。"""
        cmd = mutants._suite_cmd(8, 1200)
        self.assertNotRegex(cmd, r"(^|\s)-x(\s|$)")
        self.assertIn(" -B ", cmd)
        self.assertIn("PYTHONDONTWRITEBYTECODE=1", cmd)
        self.assertIn("-rfE", cmd)
        self.assertIn("timeout 1200", cmd)
        self.assertIn("tests/", cmd)

    def test_target_can_be_narrowed_to_node_ids(self):
        """复现校验只复跑新增失败的那几条 —— 收集面要能被替换成 node id。"""
        cmd = mutants._suite_cmd(0, 60, "tests/a.py::test_x")
        self.assertIn("pytest tests/a.py::test_x ", cmd)
        self.assertIn("-n 0", cmd)

    def test_testbed_perf_profile_is_exported_in_container(self):
        """容器内全套件必须带 AUTO_QB_TESTBED=1: 挂钟基准按 testbed 档判(与 test.linux 同口径),
        不导出它基线会多一批假红污染「本次失败 - 基线」差集。"""
        cmd = mutants._suite_cmd(8, 1200)
        self.assertIn("AUTO_QB_TESTBED=1", cmd)


class SuiteCmdDeselectTest(unittest.TestCase):
    def test_all_flaky_entries_are_deselected(self):
        cmd = mutants._suite_cmd(8, 1200)
        for node in set_conf.FLAKY_DESELECT:
            self.assertIn(f"--deselect {node}", cmd)
        self.assertIn("-n 8", cmd)
        self.assertNotIn("-n 0", cmd)
        self.assertIn("--no-cov", cmd)


class SetConfRenderTest(unittest.TestCase):
    def test_timeout_multiplier_is_written_explicitly(self):
        """只在镜像里手工加过的值会被覆盖式重写抹掉(W5/W6 实证) ⇒ 必须由渲染器显式产出。"""
        text = set_conf.render("**/core/*.py", ["tests/test_a.py"], ["data"], ["tests/b.py::test_x"], 2)
        self.assertIn("timeout_multiplier = 2\n", text)
        self.assertIn('process_isolation = "forkserver"', text)
        self.assertIn("pytest_add_cli_args_test_selection = [\"tests/test_a.py\"]", text)
        self.assertIn("--deselect\", \"tests/b.py::test_x\"", text)

    def test_default_matches_mutmut_default(self):
        self.assertEqual(set_conf.DEFAULT_TIMEOUT_MULTIPLIER, 15.0)
        self.assertIn("timeout_multiplier = 15\n", set_conf.render("x", [], [], []))

    def test_rewrite_leaves_no_stale_multiplier(self):
        old = '[tool.mutmut]\ntimeout_multiplier = 2\nonly_mutate = ["x"]\n'
        new = set_conf.strip_section(old) + "\n" + set_conf.render("y", [], [], [], 7.5)
        self.assertEqual(new.count("timeout_multiplier"), 1)
        self.assertIn("timeout_multiplier = 7.5\n", new)

    def test_non_positive_multiplier_is_rejected(self):
        self.assertEqual(set_conf.main(["--target", "x", "--timeout-multiplier", "0", "--print"]), 2)


class RunHeaderTest(unittest.TestCase):
    def test_header_records_comparable_parameters(self):
        header = mutants._run_header(
            "**/core/qbapi.py", ["tests/a.py", "tests/b.py"], 4, 2.0, "3275c1d4", "3.8.0", when="2026-11-02 02:30"
        )
        self.assertTrue(header.startswith("# run 2026-11-02 02:30 "))
        self.assertIn("target=**/core/qbapi.py", header)
        self.assertIn("timeout_multiplier=2", header)
        self.assertIn("# pool 2: tests/a.py tests/b.py", header)
        self.assertIn("head=3275c1d4", header)
        self.assertIn("mutmut=3.8.0", header)

    def test_header_lines_do_not_collide_with_detail_format(self):
        """账本头以 `#` 开头; 明细是 `@@@ id :: status` —— 否则下游会把它当候选 id。"""
        header = mutants._run_header("x", [], 4, 15.0, "h", "v", when="2026-11-02 02:30")
        lines = header.splitlines()
        self.assertEqual(len(lines), 3)
        for line in lines:
            self.assertTrue(line.startswith("# "))
            self.assertNotIn("@@@ ", line)


class DeselectTableTest(unittest.TestCase):
    """两张 deselect 表的漂移守阵: 测试文件拆分/改名后条目失效, 必须当场判红并提示改表。"""

    ROOT = Path(__file__).resolve().parents[3]

    def _assert_table(self, table: tuple[str, ...], table_name: str):
        self.assertTrue(table, f"{table_name} 不能为空")
        for node in table:
            with self.subTest(table=table_name, node=node):
                path_s, sep, name = node.partition("::")
                self.assertTrue(sep, f"{node}: 缺 `::<test_name>` 形态")
                self.assertNotIn("::", name, f"{node}: 只允许一层 `::`")
                self.assertTrue(path_s.endswith(".py"), f"{node}: 测试文件后缀不是 .py —— 测试文件拆分后路径漂移, 改 {table_name}")
                fp = self.ROOT / path_s
                self.assertTrue(fp.is_file(), f"{node}: 测试文件不存在 —— 测试文件拆分后路径漂移, 改 {table_name}")
                self.assertIn(
                    f"def {name}", fp.read_text(encoding="utf-8"),
                    f"{node}: 测试函数不存在(可能已改名) —— 测试文件拆分后路径漂移, 改 {table_name}"
                )

    def test_default_deselect_entries_exist(self):
        self._assert_table(set_conf.DEFAULT_DESELECT, "DEFAULT_DESELECT")

    def test_flaky_deselect_entries_exist(self):
        self._assert_table(set_conf.FLAKY_DESELECT, "FLAKY_DESELECT")


class DoneIdsTest(unittest.TestCase):
    def test_undetermined_verdicts_are_retried(self):
        text = "\n".join(
            [
                "# baseline 1 条既有失败 · tests/a.py::test_x",
                "abc123 :: KILLED :: 1 failed, 4144 passed",
                "abc124 :: SURVIVED :: 4144 passed",
                "abc125 :: APPLY_FAIL :: APPLYFAIL 变异未落地",
                "abc126 :: TIMEOUT :: 4144 passed",
                "abc127 :: FLAKY :: 新增失败未复现",
                "abc128 :: UNKNOWN :: ",
                "abc129 :: SURVIVED :: 4144 passed",
            ]
        )
        self.assertEqual(mutants._done_ids(text), {"abc123", "abc124", "abc129"})

    def test_empty_file_has_no_done_ids(self):
        self.assertEqual(mutants._done_ids(""), set())


class MirrorPathTest(unittest.TestCase):
    """镜像仓路径面(S4 容器形态): 派生 / 校验 / 显式优先 —— 错路径不会报错只会跑错地方, 必须响亮拦下。"""
    def _args(self, mirror: str = "", target: str = ""):
        return mock.MagicMock(mirror=mirror, target=target)

    def test_mutation_root_sits_under_tests_root(self):
        """镜像仓收敛在容器测试态单根 /root/auto-qb-tests 下的 mutation/ 子根(计划 §03)。"""
        self.assertEqual(mutants.MUTATION_ROOT, mutants.linux_ci.TESTS_ROOT + "/mutation")

    def test_target_derives_pkg_slug_mirror(self):
        self.assertEqual(mutants.derive_mirror("**/config/*.py"), f"{MUT_ROOT}/config-py")
        self.assertEqual(mutants.derive_mirror("src/auto_qb/infra/utils.py"), f"{MUT_ROOT}/src-auto-qb-infra-utils-py")

    def test_explicit_mirror_wins_over_target(self):
        args = self._args(mirror=f"{MUT_ROOT}/hr", target="**/config/*.py")
        self.assertEqual(mutants.resolve_mirror(args), f"{MUT_ROOT}/hr")

    def test_target_used_when_mirror_empty(self):
        args = self._args(target="**/config/*.py")
        self.assertEqual(mutants.resolve_mirror(args), f"{MUT_ROOT}/config-py")

    def test_both_missing_returns_none(self):
        self.assertIsNone(mutants.resolve_mirror(self._args()))

    def test_require_mirror_fails_when_both_missing(self):
        with self.assertRaises(mutants.Fail) as ctx:
            mutants.require_mirror(self._args())
        self.assertIn("未定镜像路径", str(ctx.exception))

    def test_windows_drive_path_is_rejected(self):
        with self.assertRaises(mutants.Fail) as ctx:
            mutants.check_mirror("C:/Users/x/auto-qb-mut")
        self.assertIn("Windows 路径", str(ctx.exception))

    def test_msys_rewritten_path_is_rejected(self):
        """Git Bash 手工敲 `--mirror /root/...` 会被 MSYS 改写成 D:/Program Files/Git/root/...。"""
        with self.assertRaises(mutants.Fail) as ctx:
            mutants.check_mirror("D:/Program Files/Git/root/auto-qb-tests/mutation/config-py")
        self.assertIn("Windows 路径", str(ctx.exception))

    def test_relative_path_is_rejected(self):
        with self.assertRaises(mutants.Fail) as ctx:
            mutants.check_mirror("auto-qb-mut")
        self.assertIn("绝对路径", str(ctx.exception))

    def test_container_absolute_and_tilde_paths_pass(self):
        mutants.check_mirror("/root/auto-qb-tests/mutation/config-py")
        mutants.check_mirror("~/auto-qb-mut")
        mutants.check_mirror("~")


class VenvPrepTest(unittest.TestCase):
    """镜像仓 venv 就绪面(S4): cp 模板 + export/pip delta —— uv sync 在容器里必死(R4 机制事实)。"""
    def test_uses_template_copy_not_uv_sync(self):
        with mock.patch.object(mutants, "_exec") as ex, mock.patch.object(mutants, "_say"):
            mutants._venv_ready(f"{MUT_ROOT}/config-py")
            script = ex.call_args[0][0]
        self.assertIn(f"cp -a {mutants.linux_ci.VENV_TEMPLATE[mutants.linux_ci.DEFAULT_PYTHON]}/. .venv/", script)
        self.assertIn("uv export", script)
        self.assertIn("uv pip install", script)
        self.assertNotIn("uv sync", script)

    def test_template_path_is_baked_venv_313(self):
        self.assertEqual(mutants.linux_ci.VENV_TEMPLATE[mutants.linux_ci.DEFAULT_PYTHON], "/opt/venv-3.13")

    def test_failure_line_carries_next(self):
        """失败行生产口径: venv 段失败要带 NEXT(核 uv 报错 / R9 换源), 与 linux_ci 口径看齐。"""
        with mock.patch.object(mutants, "_exec", side_effect=mutants.Fail("容器内命令失败(rc=1)")), \
                mock.patch.object(mutants, "_say"), self.assertRaises(mutants.Fail) as ctx:
            mutants._venv_ready(f"{MUT_ROOT}/config-py")
        self.assertIn("NEXT:", str(ctx.exception))
        self.assertIn("R9", str(ctx.exception))


class MirrorStateTest(unittest.TestCase):
    """镜像仓三态: 目录不存在才 clone; .git 缺失 ⇒ Fail 且不 clone; refresh 走 fetch(容器探测)。"""
    def _run(self, *, state: str = "MIRROR_HAVE_GIT", refresh: bool = False):
        calls: list[str] = []

        def fake_exec(script, *, check=True):
            calls.append(script)
            if "MIRROR_" in script:
                return subprocess.CompletedProcess([], 0, state + "\n", "")
            return subprocess.CompletedProcess([], 0, "", "")

        with mock.patch.object(mutants, "_exec", side_effect=fake_exec), \
                mock.patch.object(mutants, "_git_url", return_value="https://example.invalid/repo.git"), \
                mock.patch.object(mutants, "_say"):
            try:
                mutants._ensure_mirror(f"{MUT_ROOT}/config-py", "develop", refresh=refresh, no_sync=True)
            except mutants.Fail as exc:
                return "FAIL", str(exc), calls
        return "OK", "", calls

    def test_missing_dir_triggers_clone(self):
        status, _, calls = self._run(state="MIRROR_NO_DIR")
        self.assertEqual(status, "OK")
        self.assertTrue(any("git clone" in c for c in calls))

    def test_existing_dir_without_git_fails_without_clone(self):
        status, msg, calls = self._run(state="MIRROR_NO_GIT")
        self.assertEqual(status, "FAIL")
        self.assertIn(".git 缺失", msg)
        self.assertFalse(any("git clone" in c for c in calls))

    def test_existing_git_with_refresh_runs_fetch(self):
        status, _, calls = self._run(state="MIRROR_HAVE_GIT", refresh=True)
        self.assertEqual(status, "OK")
        self.assertTrue(any("fetch -q origin" in c for c in calls))
        self.assertFalse(any("git clone" in c for c in calls))

    def test_no_refresh_skips_fetch(self):
        status, _, calls = self._run(state="MIRROR_HAVE_GIT", refresh=False)
        self.assertEqual(status, "OK")
        self.assertFalse(any("fetch -q origin" in c for c in calls))


class RegistryPrecheckTest(unittest.TestCase):
    """空注册表必须与缺失同档拦下: 0 字节 `.meta` 若通过预检, verify 会逐条 APPLYFAIL。"""
    def _run(self, *, rc: int = 0, stdout: str = ""):
        with mock.patch.object(mutants, "_exec", return_value=subprocess.CompletedProcess([], rc, stdout, "")):
            try:
                mutants._check_registry(f"{MUT_ROOT}/config-py")
            except mutants.Fail as exc:
                return "FAIL", str(exc)
        return "OK", ""

    def test_missing_registry_fails_with_run_hint(self):
        status, msg = self._run(stdout="")
        self.assertEqual(status, "FAIL")
        self.assertIn("没有 mutmut 注册表", msg)
        self.assertIn("先跑 mutants.run", msg)

    def test_find_error_is_treated_as_missing(self):
        status, msg = self._run(rc=2, stdout="")
        self.assertEqual(status, "FAIL")
        self.assertIn("没有 mutmut 注册表", msg)

    def test_empty_registry_fails_as_empty_not_missing(self):
        status, msg = self._run(stdout="0 mutants/src/x.py.meta\n")
        self.assertEqual(status, "FAIL")
        self.assertIn("注册表为空(0 字节)", msg)
        self.assertIn("mutants/src/x.py.meta", msg)
        self.assertIn("先跑 mutants.run", msg)
        self.assertNotIn("没有 mutmut 注册表", msg)

    def test_one_empty_meta_among_others_still_fails(self):
        status, msg = self._run(stdout="10 mutants/a.meta\n0 mutants/b.meta\n")
        self.assertEqual(status, "FAIL")
        self.assertIn("mutants/b.meta", msg)
        self.assertNotIn("mutants/a.meta", msg)

    def test_non_empty_registry_passes(self):
        status, _ = self._run(stdout="12345 mutants/src/x.py.meta\n")
        self.assertEqual(status, "OK")


class CandidateIdsTest(unittest.TestCase):
    """候选清单来源面: 文件读不到要 [FAIL] 停手(不能裸 traceback); ids-file 按行修剪;
    --from-report 主线按 @@@ 行解析 + --only-status 过滤。"""
    def test_missing_report_fails_loud_not_traceback(self):
        args = mock.MagicMock(ids_file="", from_report="/nonexistent/x.txt", only_status="survived")
        with self.assertRaises(mutants.Fail) as ctx:
            mutants._candidate_ids(args)
        self.assertIn("候选清单读不到", str(ctx.exception))
        self.assertIn("mutants.report", str(ctx.exception))

    def test_ids_file_lines_are_trimmed_and_blanks_dropped(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh:
            fh.write(" abc123 \n\n  \ndef456\n")
            path = fh.name
        try:
            args = mock.MagicMock(ids_file=path, from_report="", only_status="")
            self.assertEqual(mutants._candidate_ids(args), ["abc123", "def456"])
        finally:
            os.unlink(path)

    def test_from_report_filters_by_only_status(self):
        """主线分支: mutants.report 的产物按 `@@@ <id> :: <status>` 解析, --only-status 只挑对应 id。"""
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh:
            fh.write(
                "# baseline 0 条既有失败\n"
                "@@@ abc001 :: survived\n"
                "@@@ abc002 :: killed\n"
                "@@@ abc003 :: survived\n"
                "@@@ abc004 :: timeout\n"
            )
            path = fh.name
        try:
            args = mock.MagicMock(ids_file="", from_report=path, only_status="survived")
            self.assertEqual(mutants._candidate_ids(args), ["abc001", "abc003"])
            args = mock.MagicMock(ids_file="", from_report=path, only_status="killed,timeout")
            self.assertEqual(mutants._candidate_ids(args), ["abc002", "abc004"])
        finally:
            os.unlink(path)


class StatusScriptTest(unittest.TestCase):
    """status 容器脚本面: 单仓回显旧口径键 + 缺失 [FAIL] 行与退出码; 全列模式根缺失不回非零(假 [FAIL] 防线);
    兜底钉工具就位性(mutmut 缺失标 '?', 不得让 0 假装「全杀干净」)。"""
    def test_detail_script_keeps_legacy_keys(self):
        script = mutants._status_script(f"{MUT_ROOT}/config-py")
        for key in ("mirror=", "head=", "mutmut=", "mutants=", "not_killed=", "only_mutate"):
            self.assertIn(key, script)
        self.assertIn("[FAIL] 镜像不存在", script)
        self.assertIn("exit 3", script)

    def test_all_script_marks_unknown_when_tool_missing(self):
        script = mutants._status_all_script()
        self.assertIn("[ -x \"$d/.venv/bin/mutmut\" ] || nk='?'", script)

    def test_all_script_returns_zero_without_root(self):
        script = mutants._status_all_script()
        self.assertIn(mutants.MUTATION_ROOT, script)
        self.assertIn("exit 0", script)
        self.assertNotIn("exit 3", script)


if __name__ == "__main__":
    unittest.main(verbosity=2)
