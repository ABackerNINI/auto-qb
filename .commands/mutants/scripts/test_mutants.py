"""`mutants.py verify` 的判定守阵 —— 核心是「KILLED 看新增失败, 不看套件有没有失败」。

背景: 本机 WSL Linux 侧全量套件曾有 3 个既有平台失败(`test_alias_fs` ×2 · `test_relocate_paths` ×1,
2026-10-30 已修绿),
老口径「套件里有 failed 就算 KILLED」⇒ 每条候选恒判 KILLED(全杀 = 没杀), verify 结构性失效。
本文件把判据钉在**差集**上: `本次失败 - 基线失败 非空 ⇒ KILLED`。

跑法: python .commands/mutants/scripts/test_mutants.py  ·  uv run pytest .commands -q --no-cov (test.pkg 口径)

## 测试计划
- FailIdParseTest      short test summary 的 FAILED / ERROR 行解析(含 `- 消息` 尾巴与收集期 ERROR)
- SummaryParseTest     取最后一行 pytest 汇总; 无汇总行时返回空串
- VerdictTest          基线常红 + 无新增失败 ⇒ SURVIVED(本条就是原 bug); 有新增失败 ⇒ KILLED;
                       APPLYFAIL / rc=124 / 无汇总 三种「未判定」不得落进 SURVIVED
- SuiteCmdTest         全套件命令不得带 `-x`(会停在既有失败上), 且必须带 `-B` + 禁写字节码
- SetConfRenderTest    timeout_multiplier 显式写进 [tool.mutmut](默认=mutmut 默认); 覆盖式重写不残留旧值; 非正值拒绝
- RunHeaderTest        结果文件账本头记录 target/池/并行度/timeout_multiplier/镜像HEAD/工具版本, 不与 @@@ 明细格式冲突
- DeselectTableTest     DEFAULT_DESELECT / FLAKY_DESELECT 条目必须指向存在的测试文件与 def; 漂移即判红
- DoneIdsTest           未判定(APPLY_FAIL/TIMEOUT/FLAKY/UNKNOWN)不进 done; KILLED/SURVIVED 进 done
- SuiteCmdDeselectTest  全套件命令自动带 FLAKY_DESELECT 的 --deselect, 且保留既有并行度参数
- EnsureMirrorTest      WSL 不可达 / .git 缺失 ⇒ Fail 且不 clone; 目录不存在才 clone; refresh 走 fetch
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mutants  # noqa: E402
import set_conf  # noqa: E402

#: 历史上本机 Linux 侧的真实基线(3 条平台失败, 现已修绿) —— 保留当夹具, 代表任意「红基线」
LINUX_BASELINE = {
    "tests/test_alias_fs.py::test_win_interactive_session_station_failures",
    "tests/test_alias_fs.py::test_win_create_junction_kernel_failure_cleans_up",
    "tests/test_relocate_paths.py::test_precheck_empty_file_table_skips_representative_probe",
}


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
                self.assertTrue(
                    path_s.endswith(".py"),
                    f"{node}: 测试文件后缀不是 .py —— 测试文件拆分后路径漂移, 改 {table_name}"
                )
                fp = self.ROOT / path_s
                self.assertTrue(
                    fp.is_file(), f"{node}: 测试文件不存在 —— 测试文件拆分后路径漂移, 改 {table_name}"
                )
                self.assertIn(
                    f"def {name}",
                    fp.read_text(encoding="utf-8"),
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


class SuiteCmdDeselectTest(unittest.TestCase):
    def test_all_flaky_entries_are_deselected(self):
        cmd = mutants._suite_cmd(8, 1200)
        for node in set_conf.FLAKY_DESELECT:
            self.assertIn(f"--deselect {node}", cmd)
        self.assertIn("-n 8", cmd)
        self.assertNotIn("-n 0", cmd)
        self.assertIn("--no-cov", cmd)


class EnsureMirrorTest(unittest.TestCase):
    """探测三态: WSL 不可达 / 目录不存在 / 目录在但 .git 缺失 —— 后两者绝不 clone 覆盖。"""

    def _run(self, *, probe_rc: int = 0, state: str = "MIRROR_HAVE_GIT", refresh: bool = False):
        calls: list[str] = []

        def fake_wsl(distro, script, *, check=True):
            calls.append(script)
            if "echo ok" in script:
                return subprocess.CompletedProcess([], probe_rc, "", "")
            if "MIRROR_" in script:
                return subprocess.CompletedProcess([], 0, state + "\n", "")
            return subprocess.CompletedProcess([], 0, "", "")

        with mock.patch.object(mutants, "_wsl", side_effect=fake_wsl), \
                mock.patch.object(mutants, "_git_url", return_value="https://example.invalid/repo.git"), \
                mock.patch.object(mutants, "_say"):
            try:
                mutants._ensure_mirror(
                    "Ubuntu-26.04", "~/auto-qb-mut", "develop", refresh=refresh, no_sync=True
                )
            except mutants.Fail as exc:
                return "FAIL", str(exc), calls
        return "OK", "", calls

    def test_wsl_unreachable_fails_without_clone(self):
        status, msg, calls = self._run(probe_rc=1)
        self.assertEqual(status, "FAIL")
        self.assertIn("WSL 不可达", msg)
        self.assertFalse(any("git clone" in c for c in calls))

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
