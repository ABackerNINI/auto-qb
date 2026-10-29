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
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mutants  # noqa: E402

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
