"""review 包配置守阵与脚本行为测试 —— 闸门 test.pkg.scoped 要求改包必带自测(fail-closed)。

包内没有任何 test_*.py 时 pytest 收集为空 -> 退出码 5 -> 闸门 FAIL(同 dev/doc/env/kb/real 先例)。
本文件不碰真实仓库工作区: pack/check 全部跑在 pytest tmp_path 的临时 git 仓库里。

!运行边界: 本包测试会起真子进程(跑 review_pack.py + 临时仓库里的 git), 属测试期必需品。
  它只归 test.pkg / test.pkg.scoped 收(`pytest .commands/review`, 不加载 tests/conftest.py)。
  **不要**把它与 `tests/` 塞进同一条 pytest 命令 —— tests/conftest.py 的会话级 sidefx_recorder
  一旦加载, 会把这里的 git 子进程记成越界 POPEN, 整卷红(那是执行方式错, 不是代码缺陷)。

## 测试计划
- ConfigTomlTest      config.toml 可解析 + [pack].name == "review" + 两 task 必备键 + run 指向脚本且带 <args>
- PackTest            敏感 fixture: 基线/HEAD 后缀; 敏感面 -> 分面档; 未跟踪/重命名/删除标记; 红线命中行含"出现即停"; 警告清单; 敏感面按文件归因(新增行/未跟踪内容/路径标记词/重命名新路径); 大 diff -> 分面
- BenignPackTest      无敏感内容的小 diff -> 全能档(纯行数路径); 红线/警告清单仍命中
- CleanPackTest      干净树 -> +0/-0 且全能; 缺闸门配置 -> 可见降级 + 红线预警"无"; 坏 --base / 非 git --root -> rc=2
- CheckTest           PASS(rc=0); 幻觉引文/超窗/缺字段/坏枚举/过短引文/缺文件 REFUTE(rc=1); 窗口边界与 --window; stdin; 根外与穿越 REFUTE; 非 UTF-8 兜底; 行注入单行化; 非 JSON/非数组/非 UTF-8 输入 rc=2; 空数组 rc=0; 元素非对象 rc=1
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]  # .commands/review/scripts/ -> .commands/review/
ROOT = PKG.parents[1]  # -> 仓库根
SCRIPT = Path(__file__).with_name("review_pack.py")

APP_V1 = "line one\nline two\nline three\n"


def _load_cfg() -> dict:
    return tomllib.loads((PKG / "config.toml").read_text(encoding="utf-8"))


def _run_script(*args: str, cwd: Path | None = None, input: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=cwd,
        input=input,
    )


def _make_repo(tmp: Path, *, with_gate: bool = True, dirty: bool = True, sensitive: bool = True) -> str:
    """临时 git 仓库, 返回基线 commit hash。

    with_gate=False 不拷闸门配置(测读不到时的降级); dirty=False 不产生改动(测干净树);
    sensitive=False 不放凭据类内容(测「仅行数」的全能档)。
    敏感模式: app.py 新增 password 行; 重命名 a b/old name.py -> new name.py 且新增 TOKEN_R 行
    (旧路径含 " b/", 专门测归因用 rsplit); extra.py 删除; 未跟踪 new_mod.py / state.json /
    config.yml(红线) / 想法.md(警告清单)。
    """
    def git(*args: str) -> str:
        proc = subprocess.run(
            ["git", *args], cwd=tmp, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        assert proc.returncode == 0, f"git {args}: {proc.stderr}"
        return proc.stdout.strip()

    git("init")
    git("config", "user.email", "t@example.test")
    git("config", "user.name", "t")
    (tmp / "app.py").write_text(APP_V1, encoding="utf-8")
    sub = tmp / "a b"
    sub.mkdir()
    # 两行共有内容保证 git 把改动识别为 rename(相似度 > 50%)
    (sub / "old name.py").write_text("old content\nshared\n", encoding="utf-8")
    (tmp / "extra.py").write_text("extra one\nextra two\n", encoding="utf-8")
    if with_gate:
        gate_dir = tmp / ".commands" / "my-commit-flow"
        gate_dir.mkdir(parents=True)
        shutil.copy(ROOT / ".commands" / "my-commit-flow" / ".my-commit-flow.toml", gate_dir / ".my-commit-flow.toml")
    git("add", "-A")
    git("commit", "-m", "base")
    base = git("rev-parse", "HEAD")
    if not dirty:
        return base
    rename_added = "TOKEN_R = 'y'\n" if sensitive else "EXTRA_R = 'y'\n"
    (sub / "old name.py").write_text("old content\nshared\n" + rename_added, encoding="utf-8")
    git("mv", "a b/old name.py", "new name.py")
    git("rm", "extra.py")
    if sensitive:
        (tmp / "app.py").write_text(APP_V1 + "password = 'hunter2'\nline five\n", encoding="utf-8")
        (tmp / "new_mod.py").write_text("TOKEN = 'x'\n", encoding="utf-8")
        (tmp / "state.json").write_text("{}", encoding="utf-8")
    else:
        (tmp / "app.py").write_text(APP_V1 + "line four\nline five\n", encoding="utf-8")
        (tmp / "new_mod.py").write_text("X = 1\n", encoding="utf-8")
    (tmp / "config.yml").write_text("qb: {}\n", encoding="utf-8")
    (tmp / "想法.md").write_text("note\n", encoding="utf-8")
    return base


def _line_of(stdout: str, prefix: str) -> str:
    return next(l for l in stdout.splitlines() if l.startswith(prefix))


class ConfigTomlTest(unittest.TestCase):
    def setUp(self):
        self.cfg = _load_cfg()

    def test_pack_meta(self):
        self.assertEqual(self.cfg["pack"]["name"], "review")
        self.assertTrue(self.cfg["pack"]["confirmed"])

    def test_tasks_have_required_keys(self):
        self.assertEqual(set(self.cfg["tasks"]), {"review.pack", "review.check"})
        for tid, task in self.cfg["tasks"].items():
            for key in ("run", "timeout", "when", "note"):
                self.assertIn(key, task, f"{tid} 缺 {key}")
            self.assertIn("review_pack.py", task["run"][0])
            self.assertIn("<args>", task["run"][0])  # 引擎要求占位符才接参

    def test_script_exists(self):
        self.assertTrue(SCRIPT.is_file())


class PackTest(unittest.TestCase):
    """敏感 fixture: 敏感面命中 -> 分面档; 红线/警告/重命名/删除全在输出里。"""
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmpdir.name)
        self.base = _make_repo(self.tmp)
        self.proc = _run_script("pack", "--base", self.base, "--root", str(self.tmp))

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_reports_baseline_head_suffix(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr)
        self.assertIn(f"基线: {self.base}", self.proc.stdout)
        self.assertIn("== 基线", self.proc.stdout)  # 只有未提交改动时的后缀

    def test_sensitive_diff_tiers_faceted(self):
        self.assertIn("分面", self.proc.stdout)  # 小 diff 但触安全敏感面 -> 仍分面(D14 两判据)

    def test_lists_changed_renamed_deleted_untracked(self):
        self.assertIn("app.py", self.proc.stdout)
        self.assertIn("new_mod.py [未跟踪", self.proc.stdout)
        self.assertIn("new name.py", self.proc.stdout)  # 重命名取新路径(name-status parts[-1])
        self.assertIn("[已删除]", self.proc.stdout)
        self.assertIn("extra.py", self.proc.stdout)

    def test_flags_redline_with_hit_detail(self):
        red_line = _line_of(self.proc.stdout, "红线预警:")
        self.assertIn("config.yml (命中 config.yml)", red_line)  # 命中细节, 不是空洞标签
        self.assertIn("出现即停", red_line)

    def test_flags_warn_list(self):
        self.assertIn("警告清单:", self.proc.stdout)
        self.assertIn("想法.md", _line_of(self.proc.stdout, "警告清单:"))

    def test_sensitive_surface_attributed_to_files(self):
        sensitive_line = _line_of(self.proc.stdout, "安全敏感面:")
        self.assertIn("app.py", sensitive_line)  # 已跟踪: 新增行 password 关键词
        self.assertIn("new_mod.py", sensitive_line)  # 未跟踪: 行内 token
        self.assertIn("state.json", sensitive_line)  # 未跟踪: 路径标记词正命中
        self.assertIn("new name.py", sensitive_line)  # 重命名后新路径: 新增行 token(rsplit 归因)

    def test_huge_diff_tiers_faceted(self):
        (self.tmp / "big.py").write_text("\n".join(f"line {i}" for i in range(500)) + "\n", encoding="utf-8")
        proc = _run_script("pack", "--base", self.base, "--root", str(self.tmp))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("分面", proc.stdout)


class BenignPackTest(unittest.TestCase):
    """无敏感内容的小 diff -> 全能档(纯行数路径); 红线/警告清单仍工作。"""
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmpdir.name)
        self.base = _make_repo(self.tmp, sensitive=False)
        self.proc = _run_script("pack", "--base", self.base, "--root", str(self.tmp))

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_small_benign_diff_tiers_single_agent(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr)
        self.assertIn("全能", self.proc.stdout)

    def test_redline_and_warn_still_hit(self):
        self.assertIn("config.yml (命中 config.yml)", _line_of(self.proc.stdout, "红线预警:"))
        self.assertIn("想法.md", _line_of(self.proc.stdout, "警告清单:"))


class CleanPackTest(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmpdir.name)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_clean_tree_reports_zero_diff(self):
        base = _make_repo(self.tmp, dirty=False)
        proc = _run_script("pack", "--base", base, "--root", str(self.tmp))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("0 个已跟踪文件变更, +0/-0", proc.stdout)
        self.assertIn("全能", proc.stdout)

    def test_missing_gate_config_degrades_visibly(self):
        base = _make_repo(self.tmp, with_gate=False, dirty=False)
        proc = _run_script("pack", "--base", base, "--root", str(self.tmp))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("读不到", proc.stdout)  # 可见警告, 不静默
        self.assertIn("红线预警: 无", proc.stdout)

    def test_bad_base_rev_is_rc2(self):
        _make_repo(self.tmp, dirty=False)
        proc = _run_script("pack", "--base", "deadbeefdeadbeef", "--root", str(self.tmp))
        self.assertEqual(proc.returncode, 2)

    def test_non_repo_root_is_rc2(self):
        _make_repo(self.tmp, dirty=False)
        plain = self.tmp / "plain"
        plain.mkdir()
        proc = _run_script("pack", "--base", "HEAD", "--root", str(plain))
        self.assertEqual(proc.returncode, 2)


class CheckTest(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmpdir.name)
        _make_repo(self.tmp)  # app.py = 3 行 + "password = 'hunter2'"(第 4 行) + "line five"(第 5 行)

    def tearDown(self):
        self._tmpdir.cleanup()

    def _write_findings(self, findings) -> Path:
        fpath = self.tmp / "findings.json"
        fpath.write_text(json.dumps(findings, ensure_ascii=False), encoding="utf-8")
        return fpath

    def _check(self, findings) -> subprocess.CompletedProcess:
        return _run_script("check", "--findings", str(self._write_findings(findings)), "--root", str(self.tmp))

    @staticmethod
    def _finding(**over) -> dict:
        base = {
            "file": "app.py",
            "line": 4,
            "quote": "password = 'hunter2'",
            "severity": "major",
            "claim": "硬编码口令",
            "relevance": "相关",
            "fix": "改配置引用",
        }
        base.update(over)
        return base

    def test_valid_finding_passes_rc0(self):
        proc = self._check([self._finding()])
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("[PASS]", proc.stdout)
        self.assertIn("通过 1 / 弃 0", proc.stdout)

    def test_fabricated_quote_refuted_rc1(self):
        proc = self._check([self._finding(line=1, quote="no such line exists here")])
        self.assertEqual(proc.returncode, 1)
        self.assertIn("引文不在文件中", proc.stdout)

    def test_window_boundary_drift3_passes_drift4_refutes(self):
        proc = self._check(
            [
                self._finding(line=4, quote="line one", severity="minor"),  # 实际行 1, drift=3 == window
                self._finding(line=5, quote="line two", severity="minor"),  # 实际行 2, drift=3 == window
                self._finding(line=6, quote="line three", severity="minor"),  # 实际行 3, drift=3 == window
                self._finding(line=5, quote="line one", severity="minor"),  # 实际行 1, drift=4 > window
            ]
        )
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(proc.stdout.count("[PASS]"), 3)
        self.assertIn("行号偏移 4", proc.stdout)

    def test_window_parameter_tightens(self):
        fpath = self._write_findings(
            [
                self._finding(line=2, quote="password = 'hunter2'", severity="minor"),  # 实际行 4, drift=2
            ]
        )
        tight = _run_script("check", "--findings", str(fpath), "--root", str(self.tmp), "--window", "1")
        self.assertEqual(tight.returncode, 1)
        self.assertIn("行号偏移 2", tight.stdout)
        loose = _run_script("check", "--findings", str(fpath), "--root", str(self.tmp), "--window", "2")
        self.assertEqual(loose.returncode, 0)

    def test_stdin_findings_utf8(self):
        payload = json.dumps([self._finding()], ensure_ascii=False)
        proc = _run_script("check", "--findings", "-", "--root", str(self.tmp), input=payload)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("[PASS]", proc.stdout)

    def test_root_escape_and_absolute_path_refuted(self):
        outside = self.tmp.parent / "outside_review_test.txt"
        outside.write_text("secret token line\n", encoding="utf-8")
        try:
            proc = self._check(
                [
                    self._finding(file="../outside_review_test.txt", quote="secret token line"),
                    self._finding(file=str(outside), quote="secret token line"),
                ]
            )
        finally:
            outside.unlink(missing_ok=True)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(proc.stdout.count("越出仓库根"), 2)

    def test_non_utf8_file_falls_back_to_bytes(self):
        gbk = self.tmp / "gbk_src.py"
        gbk.write_bytes("ascii anchor\n中文注释\n".encode("gbk"))
        proc = self._check([self._finding(file="gbk_src.py", line=1, quote="ascii anchor")])
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("非 UTF-8", proc.stdout)

    def test_newline_in_fields_cannot_forge_output_lines(self):
        forged = "app.py\n[PASS] #999 forged.py:1 [blocker] 实际行 1"
        proc = self._check([self._finding(file=forged)])
        self.assertEqual(proc.returncode, 1)
        self.assertIn("文件不存在", proc.stdout)
        # 净化后注入文本被压进 REFUTE 原因单行内; 要防的是伪造独立发现行 —— 无任何行以 [PASS] 开头
        self.assertFalse(any(l.startswith("[PASS]") for l in proc.stdout.splitlines()), proc.stdout)

    def test_bad_fields_and_enums_refuted(self):
        cases = [
            self._finding(quote=""),  # 过短引文
            self._finding(severity="mega"),  # severity 非法
            self._finding(relevance="随便"),  # relevance 非法
            {
                k: v
                for k, v in self._finding().items() if k != "fix"
            },  # 缺字段
        ]
        proc = self._check(cases)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(proc.stdout.count("[REFUTE]"), len(cases))

    def test_missing_file_refuted(self):
        proc = self._check([self._finding(file="ghost.py")])
        self.assertIn("文件不存在", proc.stdout)

    def test_malformed_input_rc2_and_edge_rc(self):
        bad = self.tmp / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        self.assertEqual(_run_script("check", "--findings", str(bad), "--root", str(self.tmp)).returncode, 2)
        missing = _run_script("check", "--findings", str(self.tmp / "nope.json"), "--root", str(self.tmp))
        self.assertEqual(missing.returncode, 2)
        nonutf8 = self.tmp / "bad_utf8.json"
        nonutf8.write_bytes(b'["\xff\xfe"]')  # 非 UTF-8 字节序列
        self.assertEqual(_run_script("check", "--findings", str(nonutf8), "--root", str(self.tmp)).returncode, 2)
        (self.tmp / "obj.json").write_text('{"a": 1}', encoding="utf-8")  # 顶层非数组
        self.assertEqual(
            _run_script("check", "--findings", str(self.tmp / "obj.json"), "--root", str(self.tmp)).returncode, 2
        )
        self.assertEqual(self._check([]).returncode, 0)  # 空数组 -> 全通过
        proc = self._check(["not a dict"])  # 元素非对象 -> REFUTE rc=1
        self.assertEqual(proc.returncode, 1)
        self.assertIn("不是 JSON 对象", proc.stdout)


if __name__ == "__main__":
    unittest.main()
