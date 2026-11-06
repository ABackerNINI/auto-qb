"""review 包配置守阵与脚本行为测试 —— 闸门 test.pkg.scoped 要求改包必带自测(fail-closed)。

包内没有任何 test_*.py 时 pytest 收集为空 -> 退出码 5 -> 闸门 FAIL(同 dev/doc/env/kb/real 先例)。
本文件不碰真实仓库工作区: pack/check 全部跑在 pytest tmp_path 的临时 git 仓库里。

!运行边界: 本包测试会起真子进程(跑 review_pack.py + 临时仓库里的 git), 属测试期必需品。
  它只归 test.pkg / test.pkg.scoped 收(`pytest .commands/review`, 不加载 tests/conftest.py)。
  **不要**把它与 `tests/` 塞进同一条 pytest 命令 —— tests/conftest.py 的会话级 sidefx_recorder
  一旦加载, 会把这里的 git 子进程记成越界 POPEN, 整卷红(那是执行方式错, 不是代码缺陷)。

## 测试计划
- ConfigTomlTest      config.toml 可解析 + [pack].name == "review" + 九 task(review.pack/check + review.lane 七子命令)必备键 + run 指向对应包内脚本且 lane 系含子命令 token + 带 <args>
- LaneManifestTest    提交在库的 manifest.json 结构守阵: coverage.ok=true + 批次 id 唯一且前缀==route + routes 映射一致 + 文件跨批不重 + 批内不重 + 全部路径在分层范围内(src 代码文件/scripts py, 无 vendor/test_*) + registry 键齐
- LaneScriptTest      review_lane.py 无参 rc=2(无参无动作) + --help rc=0
- LaneStateTest       状态机直驱单测: batch 转换与原子写(无 .tmp 残留)/坏批次 id 拒/重复勾选拒/done 批次未齐拒/产出缺失拒/合法终态/schema 校验(status 枚举/批次条目/缺文件)
- PackTest            敏感 fixture: 基线/HEAD 后缀; 敏感面 -> 分面档; 文件清单精确行(重命名只列新路径/[已删除] 同行); 红线命中行含"出现即停"; 警告清单; 敏感面按元素归因(新增行/已跟踪路径标记/未跟踪内容/未跟踪路径/+++ 头归因, 且无幻影键); 仅删除计数; 尾斜杠目录规则; +++ 头不算内容; 空文件 0 行; 默认 root; 大 diff 用独立无敏感仓库证明分面来自行数
- BenignPackTest      无敏感内容的小 diff -> 全能档(纯行数路径); 红线/警告清单仍命中
- CleanPackTest      干净树 -> +0/-0 且全能; 缺/坏闸门配置 -> 可见降级 + 红线预警"无"; 坏 --base / 非 git --root / 非仓库 cwd -> rc=2; 提交后 HEAD!=base 无后缀且已提交改动仍在范围内
- CheckTest           PASS(rc=0); 幻觉引文/超窗/缺字段/坏枚举/过短引文/非字符串字段/缺文件 REFUTE(rc=1); 窗口边界与 --window; stdin; 根外与穿越 REFUTE; 非 UTF-8 兜底; 行注入单行化; 非 JSON/非数组/非 UTF-8 输入 rc=2; 空数组 rc=0; 元素非对象 rc=1
- TraceDecideTest     评审留痕纯判定: 无待评/低于下限放行; 超限无 trailer 拦; trailer 行数不符/缺字段/缺行数拦; >400 行须拆批或记分面; Review-Skip 理由过短拦; 触安全敏感面小改仍要评; Review 优先于 Skip; 记账类/生成物不计入
- TraceDecideTest(续) 低于下限时正文里的畸形 Review 段不硬拦
- TraceGateTest       端到端(临时仓库真跑脚本): 复跑阶段标记跳过; 低于下限静默; 超限无 trailer rc=1; trailer 行数相符 rc=0 / 不符 rc=1; 锚点推进(漏评提交被下一批连坐); 评过的提交推进锚点; 提交后复跑不重对行数
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
import importlib.util
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]  # .commands/review/scripts/ -> .commands/review/
ROOT = PKG.parents[1]  # -> 仓库根
SCRIPT = Path(__file__).with_name("review_pack.py")
LANE_SCRIPT = Path(__file__).with_name("review_lane.py")

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
    (旧路径在目录 a b/ 下、新路径含空格, 测 +++ 头归因不被 " b/" 截断也不带尾随 TAB); extra.py 删除; 未跟踪 new_mod.py / state.json /
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
    if sensitive:
        (tmp / "auth_store.py").write_text("AUTH_MODE = 'off'\n", encoding="utf-8")
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
        (tmp / "auth_store.py").write_text("AUTH_MODE = 'on'\n", encoding="utf-8")
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
        self.assertEqual(set(self.cfg["tasks"]), {
            "review.pack", "review.check", "review.trace",
            "review.lane.manifest", "review.lane.claim", "review.lane.start",
            "review.lane.verify", "review.lane.batch", "review.lane.done", "review.lane.smoke",
        })
        for tid, task in self.cfg["tasks"].items():
            for key in ("run", "timeout", "when", "note"):
                self.assertIn(key, task, f"{tid} 缺 {key}")
            run_cmd = task["run"][0]
            if tid.startswith("review.lane."):
                self.assertIn("review_lane.py", run_cmd, f"{tid} 应指向 review_lane.py: {run_cmd}")
                seg = tid.rsplit(".", 1)[-1]
                self.assertIn(seg, run_cmd.split(), f"{tid} 的 run 应含子命令 {seg}: {run_cmd}")
            elif tid == "review.trace":
                # 提交闸门上的命令: 纯 stdlib, 必须用裸 python(uv/console-script 有 trampoline 坏掉的先例)
                self.assertIn("check_review_trace.py", run_cmd, f"{tid} 应指向 check_review_trace.py: {run_cmd}")
                self.assertTrue(run_cmd.startswith("python "), f"{tid} 应用裸 python: {run_cmd}")
            else:
                self.assertIn("review_pack.py", run_cmd, f"{tid} 应指向 review_pack.py: {run_cmd}")
            self.assertIn("<args>", run_cmd)  # 引擎要求占位符才接参


class LaneManifestTest(unittest.TestCase):
    """提交在库的 manifest.json 结构守阵(数据不变式, 不碰工作树/不依赖树漂移)。"""

    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(
            (ROOT / "memory-bank" / "reports" / "attachments" / "legacy-review4" / "manifest.json")
            .read_text(encoding="utf-8")
        )

    def test_coverage_ok(self):
        self.assertTrue(self.manifest["coverage"]["ok"], "manifest 覆盖守卫未通过, claim 会被拒")

    def test_batches_shape(self):
        batches = self.manifest["batches"]
        self.assertEqual(len(batches), 34)
        ids = [b["id"] for b in batches]
        self.assertEqual(len(ids), len(set(ids)), "批次 id 重复")
        for b in batches:
            self.assertEqual(b["id"].split("-")[0], b["route"], f"{b['id']} 前缀与 route 不一致")
            self.assertGreater(len(b["files"]), 0, f"{b['id']} 无文件")
            self.assertIn(b["depth"], ("full", "contract", "mechanism", "scan"))
            for key in ("r2_ids", "r2_index", "issues"):
                self.assertIn(key, b["registry"], f"{b['id']} registry 缺 {key}")

    def test_routes_mapping(self):
        for route, ids in self.manifest["routes"].items():
            self.assertEqual(route, ids[0].split("-")[0], f"{route} 映射里混入别的路线批次")
        mapped = [i for ids in self.manifest["routes"].values() for i in ids]
        self.assertEqual(sorted(mapped), sorted(b["id"] for b in self.manifest["batches"]))

    def test_files_disjoint_and_in_scope(self):
        seen: set[str] = set()
        for b in self.manifest["batches"]:
            for f in b["files"]:
                p = f["path"]
                self.assertNotIn(p, seen, f"{p} 同时出现在多个批次(重叠守卫失效)")
                seen.add(p)
                self.assertTrue(p.startswith("src/") or p.startswith("scripts/"), f"{p} 越出分层范围")
                self.assertNotIn("vendor/", p, f"{p} vendor 第三方库不应进范围")
                self.assertFalse(fnmatch.fnmatchcase(p.rsplit("/", 1)[-1], "test_*.py"), p)


class LaneScriptTest(unittest.TestCase):
    """review_lane.py 的无参安全面: 无参必须 rc=2 纯用法错误(无参无动作)。"""

    def test_no_args_is_usage_error(self):
        proc = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("review_lane.py"))],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        self.assertEqual(proc.returncode, 2, "无参应退出 2(argparse 用法错误), 不得执行任何真动作")
        self.assertEqual(proc.stdout, "", "无参不得有 stdout 输出")

    def test_help_ok(self):
        proc = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("review_lane.py")), "--help"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("smoke", proc.stdout + proc.stderr)


class LaneStateTest(unittest.TestCase):
    """review_lane 状态机单测: 临时目录直驱 cmd_batch/cmd_done/_load_route(不依赖 git 网络面)。

    claim/start/verify 需真仓+远端(ls-remote/sync), 归 smoke 全环管; 这里把 route JSON 的
    状态转换与守卫语义(非法跳转/产出缺失/schema 校验/原子写)钉进守阵。
    """

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("review_lane_under_test", LANE_SCRIPT)
        cls.lane = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.lane)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / ".git").mkdir()  # _resolve_root 只验 .git 存在
        self.lane_dir = self.root / "memory-bank" / "reports" / "attachments" / "legacy-review4"
        self.lane_dir.mkdir(parents=True)
        self._write_route({
            "route": "R9", "owner": "t", "claimed_at": "26-11-06-0000", "freeze": "f" * 40,
            "snapshot": str(self.root / "snap"), "status": "in-progress",
            "batches": [
                {"id": "R9-1", "title": "批1", "status": "pending", "done_at": None, "findings": 0},
                {"id": "R9-2", "title": "批2", "status": "pending", "done_at": None, "findings": 0},
            ],
        })

    def _write_route(self, data):
        (self.lane_dir / "route-R9.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def _read_route(self):
        return json.loads((self.lane_dir / "route-R9.json").read_text(encoding="utf-8"))

    def _ns(self, **kw):
        base = {"root": str(self.root), "route": "R9"}
        base.update(kw)
        return argparse.Namespace(**base)

    def _expect_rc(self, fn, *args, code=1):
        with self.assertRaises(SystemExit) as cm:
            fn(*args)
        self.assertEqual(cm.exception.code, code)

    def test_batch_transitions_and_atomic_write(self):
        self.lane.cmd_batch(self._ns(id="R9-1", findings=3))
        data = self._read_route()
        self.assertEqual(data["batches"][0]["status"], "done")
        self.assertEqual(data["batches"][0]["findings"], 3)
        self.assertEqual(data["batches"][1]["status"], "pending")
        self.assertFalse(list(self.lane_dir.glob("*.tmp")), "原子写不应残留临时文件")

    def test_batch_rejects_bad_id_and_double_done(self):
        self._expect_rc(self.lane.cmd_batch, self._ns(id="R9-X", findings=0))
        self.lane.cmd_batch(self._ns(id="R9-1", findings=0))
        self._expect_rc(self.lane.cmd_batch, self._ns(id="R9-1", findings=0))

    def test_done_blocked_until_all_batches_and_outputs(self):
        self._expect_rc(self.lane.cmd_done, self._ns())  # 批次未齐
        for b in ("R9-1", "R9-2"):
            self.lane.cmd_batch(self._ns(id=b, findings=0))
        self._expect_rc(self.lane.cmd_done, self._ns())  # findings/notes 缺失
        (self.lane_dir / "route-R9-findings.json").write_text("[]", encoding="utf-8")
        (self.lane_dir / "route-R9-notes.md").write_text("# t\n", encoding="utf-8")
        self.lane.cmd_done(self._ns())
        self.assertEqual(self._read_route()["status"], "done")

    def test_load_route_schema_guards(self):
        good = self._read_route()
        self._write_route(dict(good, status="weird"))
        self._expect_rc(self.lane._load_route, self.root, "R9")
        self._write_route(dict(good, batches=[{"id": "R9-1", "status": "half"}]))
        self._expect_rc(self.lane._load_route, self.root, "R9")
        (self.lane_dir / "route-R9.json").unlink()
        self._expect_rc(self.lane._load_route, self.root, "R9")

    def test_done_requires_in_progress(self):
        self._write_route(dict(self._read_route(), status="claimed"))
        self._expect_rc(self.lane.cmd_done, self._ns())

    def test_require_clean_allow_lane(self):
        """allow_lane 放行 lane 内未跟踪/修改; lane 外拒; 「lane 内 -> lane 外」重命名拒(评审实证绕过面)。

        前置: lane 目录先提交 .keep 哨兵 —— 未跟踪目录在 porcelain 会折叠成「?? memory-bank/」,
        真实 clone 里 lane 内有已跟踪的 manifest.json 故不折叠, 测试环境须同构。
        """
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "t@example.test"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=self.root, check=True)
        (self.root / "base.txt").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "add", "base.txt"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=self.root, check=True)
        rf = self.root / "memory-bank" / "reports" / "attachments" / "legacy-review4"
        rf.mkdir(parents=True, exist_ok=True)
        (rf / ".keep").write_text("\n", encoding="utf-8")
        subprocess.run(["git", "add", ".keep"], cwd=str(rf), check=True)
        subprocess.run(["git", "commit", "-q", "-m", "lane keep"], cwd=self.root, check=True)
        # 仅 lane 内未跟踪: 放行
        (rf / "route-R9.json").write_text("{}", encoding="utf-8")
        self.lane._require_clean(self.root, allow_lane=True)
        # lane 外未跟踪: 拒
        (self.root / "outside.txt").write_text("x\n", encoding="utf-8")
        self._expect_rc(self.lane._require_clean, self.root, True)
        (self.root / "outside.txt").unlink()
        # 已提交的 lane 文件 rename 到 lane 外: 拒(porcelain「old -> new」两侧都必须在 lane 内)
        subprocess.run(["git", "add", "route-R9.json"], cwd=str(rf), check=True)
        subprocess.run(["git", "commit", "-q", "-m", "route"], cwd=self.root, check=True)
        subprocess.run(["git", "mv", str(rf / "route-R9.json"), "moved.txt"], cwd=self.root, check=True)
        self._expect_rc(self.lane._require_clean, self.root, True)

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
        listing = self.proc.stdout.split("文件清单:", 1)[1]
        lines = [l.strip() for l in listing.splitlines() if l.strip()]
        self.assertIn("app.py", lines)
        self.assertIn("new name.py", lines)  # 重命名只列新路径(name-status parts[-1])
        self.assertIn("extra.py [已删除]", lines)  # 删除标记与文件同一行
        self.assertNotIn("old name.py", " ".join(lines))  # 旧路径不应出现
        self.assertTrue(any(l.startswith("new_mod.py [未跟踪") for l in lines))

    def test_flags_redline_with_hit_detail(self):
        red_line = _line_of(self.proc.stdout, "红线预警:")
        self.assertIn("config.yml (命中 config.yml)", red_line)  # 命中细节, 不是空洞标签
        self.assertIn("出现即停", red_line)

    def test_flags_warn_list(self):
        self.assertIn("警告清单:", self.proc.stdout)
        self.assertIn("想法.md", _line_of(self.proc.stdout, "警告清单:"))

    def test_sensitive_surface_attributed_to_files(self):
        sensitive_line = _line_of(self.proc.stdout, "安全敏感面:")
        items = [p.lstrip(" ") for p in sensitive_line.split(":", 1)[1].split("; ") if p]  # 只去前导空格: 尾随 TAB 必须暴露
        self.assertNotIn("\t", sensitive_line)  # 含空格路径的 +++ 头 TAB 不能漏进归因键
        self.assertIn("app.py", items)  # 已跟踪: 新增行 password 关键词
        self.assertIn("auth_store.py", items)  # 已跟踪: 路径标记词 auth
        self.assertIn("new_mod.py", items)  # 未跟踪: 行内 token
        self.assertIn("state.json", items)  # 未跟踪: 路径标记词正命中
        self.assertIn("new name.py", items)  # 重命名后新路径(含空格): 新增行 token(+++ 头归因)
        self.assertNotIn("old name.py b/new name.py", sensitive_line)  # split 误实现的幻影键

    def test_huge_diff_tiers_faceted_by_line_count(self):
        # 独立仓库且无敏感面: 分面只能来自 400 行判据(沿用敏感 fixture 会让本用例恒真)
        other = self.tmp / "big_repo"
        other.mkdir()
        base = _make_repo(other, sensitive=False)
        (other / "big.py").write_text("\n".join(f"line {i}" for i in range(500)) + "\n", encoding="utf-8")
        proc = _run_script("pack", "--base", base, "--root", str(other))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("分档: 分面", proc.stdout)
        self.assertIn("安全敏感面: 无", proc.stdout)  # 分面来自行数, 不是敏感面

    def test_deletion_counts_are_parsed(self):
        # extra.py 删两行 + auth_store.py 改写一行 → -3; 钉住 shortstat 的 deletions 解析
        self.assertIn("-3", _line_of(self.proc.stdout, "diff 统计:"))

    def test_directory_rule_matches_nested_path(self):
        d = self.tmp / "auto-qb-data"
        d.mkdir()
        (d / "state.json").write_text("{}", encoding="utf-8")
        proc = _run_script("pack", "--base", self.base, "--root", str(self.tmp))
        self.assertIn("auto-qb-data/state.json (命中 auto-qb-data/)", proc.stdout)  # 尾斜杠规则

    def test_pplus_header_not_treated_as_sensitive_content(self):
        # 文件名含 api_key 但不在路径标记词内、内容普通; 必须 git add 才进 +++ 头(否则用例恒真)
        (self.tmp / "api_key_notes.py").write_text("notes only\n", encoding="utf-8")
        subprocess.run(["git", "add", "api_key_notes.py"], cwd=self.tmp, check=True, capture_output=True)
        proc = _run_script("pack", "--base", self.base, "--root", str(self.tmp))
        self.assertIn("api_key_notes.py", proc.stdout)  # 确实经过 +++ 头进了变更面
        self.assertNotIn("api_key_notes.py", _line_of(proc.stdout, "安全敏感面:"))

    def test_empty_untracked_file_counts_zero_lines(self):
        (self.tmp / "empty.txt").write_text("", encoding="utf-8")
        proc = _run_script("pack", "--base", self.base, "--root", str(self.tmp))
        self.assertIn("empty.txt [未跟踪 +0 行]", proc.stdout)

    def test_default_root_from_cwd(self):
        proc = _run_script("pack", "--base", self.base, cwd=self.tmp)  # 不带 --root
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(f"基线: {self.base}", proc.stdout)


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

    def test_non_repo_cwd_is_rc2(self):
        plain = self.tmp / "plain_cwd"
        plain.mkdir()
        self.assertEqual(_run_script("pack", "--base", "HEAD", cwd=plain).returncode, 2)

    def test_bad_toml_gate_config_degrades_visibly(self):
        base = _make_repo(self.tmp, dirty=False)
        gate = self.tmp / ".commands" / "my-commit-flow" / ".my-commit-flow.toml"
        gate.write_text("red_lines = [unclosed\n", encoding="utf-8")
        proc = _run_script("pack", "--base", base, "--root", str(self.tmp))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("解析失败", proc.stdout)  # 坏 TOML 也要可见降级
        self.assertIn("红线预警: 无", proc.stdout)

    def test_pack_after_commit_has_no_suffix(self):
        base = _make_repo(self.tmp, sensitive=False)
        for args in (("add", "-A"), ("commit", "-m", "wip")):
            subprocess.run(["git", *args], cwd=self.tmp, capture_output=True, text=True, check=True)
        proc = _run_script("pack", "--base", base, "--root", str(self.tmp))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("== 基线", proc.stdout)  # HEAD != base 时后缀消失
        self.assertIn("new_mod.py", proc.stdout)  # 已提交改动仍在 diff 范围内


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
            self._finding(line="4"),  # line 非 int
            self._finding(line=0),  # line < 1
            self._finding(file=""),  # file 空串
            self._finding(quote=123),  # quote 非字符串
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


TRACE_SCRIPT = Path(__file__).with_name("check_review_trace.py")


def _load_trace():
    spec = importlib.util.spec_from_file_location("check_review_trace", TRACE_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_trace(root: Path, msg_file: Path | None = None) -> subprocess.CompletedProcess:
    args = [sys.executable, str(TRACE_SCRIPT), "--root", str(root)]
    if msg_file is not None:
        args += ["--message-file", str(msg_file)]
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")


class TraceDecideTest(unittest.TestCase):
    """评审留痕的纯判定面 —— 判据顺序即优先级(见 check_review_trace 模块头)。"""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load_trace()

    def _decide(self, count: int, msg: str, sensitive=()):
        return self.mod.decide(count, list(sensitive), msg)

    def test_no_pending_change_passes(self):
        self.assertTrue(self._decide(0, "")[0])

    def test_below_floor_passes(self):
        ok, why = self._decide(49, "")
        self.assertTrue(ok)
        self.assertIn("低于下限", why)

    def test_above_floor_without_trailer_fails(self):
        ok, why = self._decide(50, "✨ 改了点东西\n")
        self.assertFalse(ok)
        self.assertIn("未留痕", why)

    def test_trailer_matching_lines_passes(self):
        ok, _ = self._decide(120, "Review: S3 增量 · 120 行 · blocker 0 · 修 3 · 入池 1\n")
        self.assertTrue(ok)

    def test_trailer_line_mismatch_fails(self):
        ok, why = self._decide(120, "Review: S3 · 100 行 · blocker 0 · 修 3 · 入池 1\n")
        self.assertFalse(ok)
        self.assertIn("≠ 实算 120 行", why)

    def test_trailer_missing_fields_fails(self):
        ok, why = self._decide(120, "Review: S3 · 120 行 · blocker 0\n")
        self.assertFalse(ok)
        self.assertIn("缺字段", why)

    def test_trailer_without_line_count_fails(self):
        ok, why = self._decide(120, "Review: S3 · blocker 0 · 修 3 · 入池 1\n")
        self.assertFalse(ok)
        self.assertIn("缺 `<N> 行`", why)

    def test_oversize_needs_split_or_facet(self):
        body = "Review: S3 · 800 行 · blocker 0 · 修 3 · 入池 1\n"
        ok, why = self._decide(800, body)
        self.assertFalse(ok)
        self.assertIn("拆批", why)
        self.assertTrue(self._decide(800, body.replace("入池 1", "入池 1 · 分面"))[0])

    def test_below_floor_ignores_malformed_trailer(self):
        """低于下限的批没有 trailer 义务 —— 正文里随手写一句「Review: 见报告」不该被硬拦。"""
        ok, _ = self._decide(5, "动机: 小改\n\nReview: 见报告\n")
        self.assertTrue(ok)

    def test_skip_needs_real_reason(self):
        self.assertFalse(self._decide(120, "Review-Skip: 改\n")[0])
        ok, why = self._decide(120, "Review-Skip: 只改了一处文档措辞, 无行为变化\n")
        self.assertTrue(ok)
        self.assertIn("豁免", why)

    def test_sensitive_small_change_still_needs_review(self):
        ok, why = self._decide(12, "", sensitive=["src/auto_qb/auth_token.py"])
        self.assertFalse(ok)
        self.assertIn("安全敏感面", why)

    def test_review_wins_over_skip(self):
        msg = "Review: S3 · 120 行 · blocker 0 · 修 1 · 入池 0\nReview-Skip: 随便写写\n"
        self.assertTrue(self._decide(120, msg)[0])  # 有真 trailer 时按 trailer 校验, 不被 skip 短路

    def test_generated_and_bookkeeping_are_not_counted(self):
        self.assertFalse(self._counted("memory-bank/pitfalls/_index.md", set()))
        self.assertFalse(self._counted("memory-bank/tasks/26-11-06-x.md", set()))
        self.assertFalse(self._counted("memory-bank/activeContext/26-11-06-0000-x.md", set()))
        self.assertFalse(self._counted("memory-bank/testing/baselines/26-11-06-0000-x.md", set()))
        self.assertTrue(self._counted("memory-bank/conventions/collaboration.md", set()))
        self.assertTrue(self._counted("src/auto_qb/core/rules.py", set()))

    def _counted(self, path: str, gen: set[str]) -> bool:
        return self.mod._counted(path, gen)


class TraceGateTest(unittest.TestCase):
    """端到端: 临时仓库里真跑脚本 —— 验锚点推进(漏评的提交滚进下一批)与退出码。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="trace_gate_"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self._git("init")
        self._git("config", "user.email", "t@example.test")
        self._git("config", "user.name", "t")
        (self.tmp / "app.py").write_text("A = 1\n", encoding="utf-8")
        self._commit("base")

    def _git(self, *args: str) -> str:
        proc = subprocess.run(["git", *args], cwd=self.tmp, capture_output=True, text=True, encoding="utf-8")
        assert proc.returncode == 0, f"git {args}: {proc.stderr}"
        return proc.stdout.strip()

    def _commit(self, msg: str) -> None:
        self._git("add", "-A")
        self._git("commit", "-m", msg)

    def _msg(self, text: str) -> Path:
        """消息文件放 `.git/` 下 —— 与真实约定路径同款(git 不把 .git 内容算进改动清单)。"""
        path = self.tmp / ".git" / "MSG.txt"
        path.write_text(text, encoding="utf-8")
        return path

    def _append(self, lines: int) -> None:
        """增量追加(不是重写): 重写会让"本批"变成删+增, 把行数算成两倍。"""
        path = self.tmp / "app.py"
        start = getattr(self, "_n", 0)
        add = "".join(f"X{start + i} = {i}\n" for i in range(lines))
        path.write_text(path.read_text(encoding="utf-8") + add, encoding="utf-8")
        self._n = start + lines

    def test_below_floor_is_silent(self):
        self._append(10)
        proc = _run_trace(self.tmp, self._msg("小改\n"))
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertEqual(proc.stdout.strip(), "")  # v3 契约: 通过即静默

    def test_above_floor_without_trailer_blocks(self):
        self._append(60)
        proc = _run_trace(self.tmp, self._msg("改了一堆\n"))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("未留痕", proc.stdout)

    def test_trailer_with_matching_count_passes(self):
        self._append(60)
        proc = _run_trace(self.tmp, self._msg("✨ 改\n\nReview: 本批 · 60 行 · blocker 0 · 修 0 · 入池 0\n"))
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_trailer_with_wrong_count_blocks(self):
        self._append(60)
        proc = _run_trace(self.tmp, self._msg("✨ 改\n\nReview: 本批 · 30 行 · blocker 0 · 修 0 · 入池 0\n"))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("≠ 实算", proc.stdout)

    def test_anchor_advances_so_skipped_commits_roll_forward(self):
        self._append(30)
        self._commit("✨ 第一批\n\nReview: 第一批 · 30 行 · blocker 0 · 修 0 · 入池 0\n")
        self._append(20)
        self._commit("漏评的一笔\n")  # 20 行, 没写 trailer: 锚点停在第一批
        self._append(40)
        proc = _run_trace(self.tmp, self._msg("第三笔\n"))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("60 行", proc.stdout)  # 20 + 40: 漏评的那笔被下一批连坐

    def test_cold_start_counts_worktree_only(self):
        """冷启动(历史里一条 Review: 都没有)时锚点退化为 HEAD —— 只算工作树, 不追溯全历史。

        这是有意接受的边界: 追溯全历史会让"第一次提交"要求评审整棵仓库。落地后第一笔带 trailer
        的提交即建立锚点, 此后一律按锚点滚进。
        """
        self._append(30)
        self._commit("冷启动前的一笔\n")
        self._append(20)
        proc = _run_trace(self.tmp, self._msg("冷启动后的一笔\n"))
        self.assertEqual(proc.returncode, 0, proc.stdout)  # 只算 20 行, 未把前一笔 30 行算进来

    def test_reviewed_commit_moves_the_anchor(self):
        self._append(60)
        self._commit("✨ 第一批\n\nReview: 第一批 · 60 行 · blocker 0 · 修 0 · 入池 0\n")
        self._append(5)  # 新一批只有 5 行 —— 锚点已前进, 不该被上一批的行数拖累
        proc = _run_trace(self.tmp, self._msg("小补\n"))
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_post_phase_env_skips_recheck(self):
        """合流复跑(commit.py 注入 COMMIT_FLOW_GATE_PHASE=post)不再对行数。

        不跳过的话, rebase 进来的远端提交会被算进本批 → 假红「未留痕」。
        """
        self._append(200)
        env = dict(os.environ, COMMIT_FLOW_GATE_PHASE="post")
        proc = subprocess.run([sys.executable, str(TRACE_SCRIPT), "--root", str(self.tmp)],
                              capture_output=True, text=True, encoding="utf-8", env=env)
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_post_commit_rerun_does_not_recheck(self):
        self._append(60)
        self._commit("✨ 第一批\n\nReview: 第一批 · 60 行 · blocker 0 · 修 0 · 入池 0\n")
        proc = _run_trace(self.tmp)  # 无 --message-file → 退到 HEAD 消息 = 提交后复跑
        self.assertEqual(proc.returncode, 0, proc.stdout)


if __name__ == "__main__":
    unittest.main()
