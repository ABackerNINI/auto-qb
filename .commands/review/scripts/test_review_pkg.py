"""review 包配置守阵与脚本行为测试 —— 闸门 test.pkg.scoped 要求改包必带自测(fail-closed)。

包内没有任何 test_*.py 时 pytest 收集为空 -> 退出码 5 -> 闸门 FAIL(同 dev/doc/env/kb/real 先例)。
本文件不碰真实仓库工作区: pack/check 全部跑在 pytest tmp_path 的临时 git 仓库里。

!运行边界: 本包测试会起真子进程(跑 review_pack.py + 临时仓库里的 git), 属测试期必需品。
  它只归 test.pkg / test.pkg.scoped 收(`pytest .commands/review`, 不加载 tests/conftest.py)。
  **不要**把它与 `tests/` 塞进同一条 pytest 命令 —— tests/conftest.py 的会话级 sidefx_recorder
  一旦加载, 会把这里的 git 子进程记成越界 POPEN, 整卷红(那是执行方式错, 不是代码缺陷)。

## 测试计划
- ConfigTomlTest      config.toml 可解析 + [pack].name == "review" + 十 task(review.pack/check/trace + review.lane 七子命令)必备键 + run 指向对应包内脚本(lane 系含子命令 token, trace 系裸 python) + 带 <args>
- LaneManifestTest    提交在库的 manifest.json 结构守阵: coverage.ok=true + 批次 id 唯一且前缀==route + routes 映射一致 + 文件跨批不重 + 批内不重 + 全部路径在分层范围内(src 代码文件/scripts py, 无 vendor/test_*) + registry 键齐
- LaneScriptTest      review_lane.py 无参 rc=2(无参无动作) + --help rc=0
- LaneStateTest       状态机直驱单测: batch 转换与原子写(无 .tmp 残留)/坏批次 id 拒/重复勾选拒/done 批次未齐拒/产出缺失拒/合法终态/done 需进行中态/schema 校验(status 枚举/批次条目/缺文件)/require_clean lane 边界(lane 内未跟踪与修改放行/lane 外拒/lane 内改名到 lane 外拒)
- PackTest            敏感 fixture: 基线/HEAD 后缀; 敏感面 -> 分面档; 文件清单精确行(重命名只列新路径/[已删除] 同行); 红线命中行含"出现即停"; 警告清单; 敏感面按元素归因(新增行/已跟踪路径标记/未跟踪内容/未跟踪路径/+++ 头归因, 且无幻影键); 仅删除计数; 尾斜杠目录规则; +++ 头不算内容; 空文件 0 行; 默认 root; 大 diff 用独立无敏感仓库证明分面来自行数
- BenignPackTest      无敏感内容的小 diff -> 全能档(纯行数路径); 红线/警告清单仍命中
- CleanPackTest      干净树 -> +0/-0 且全能; 缺/坏闸门配置 -> 可见降级 + 红线预警"无"; 坏 --base / 非 git --root / 非仓库 cwd -> rc=2; 提交后 HEAD!=base 无后缀且已提交改动仍在范围内
- CheckTest           PASS(rc=0); 幻觉引文/超窗/缺字段/坏枚举/过短引文/非字符串字段/缺文件 REFUTE(rc=1); 窗口边界与 --window; stdin; 根外与穿越 REFUTE; 快照 root(无 .git)放行; 非 UTF-8 兜底; 行注入单行化; 非 JSON/非数组/非 UTF-8 输入 rc=2; 空数组 rc=0; 元素非对象 rc=1
- BatchBaseHashTest   基哈希(batch_base_hash, 共享模块 review_content): 同树确定且 12hex; 金值锁规范化格式(固定 fixture 硬编码 12hex, 改钉子必红须显式换金值); 记账类/生成物变更(含未跟踪)不动哈希; 可评已跟踪/未跟踪变更动哈希; 工作树 CRLF 行尾噪音不动哈希(--ignore-cr-at-eol 两侧压掉); 未跟踪文件序无关(按 path 排序); repo 配置逐颗覆写(diff.context/前缀/颜色/算法/orderFile/excludesFile/quotepath/diff.external...)哈希不漂(env 掐 system+global + -c 逐键压 repo 的回归); 工作树改名按删+增展开(name-only 两条路径/无 rename 段); pathspec 逐字精确(f[1].txt 不 glob 误匹配、分块不重复); pack 输出「基哈希:」行与共享实现同值; generated_paths 优先 gen_all --list 清单(反斜杠归一)
- TraceDecideTest     评审留痕纯判定: 实算恒 0 静默; 可评 >0 无 trailer 拦(50 行下限退役 D9, 各量级一律); Review-Skip 恒红(豁免退役 D8, 理由长短不再重要); trailer 行数不符/缺字段(含缺检缺基)/缺行数拦; >400 行只认 派发 ≥ 2(分面降级信息字段); `· 基` 必填+12hex 形状+与重算基哈希比对(不一致红含「重跑 pack 取新基复评」出路, D6); `· 轮` 缺省 1、出现须整数 ≥1(D7), 与 `· 派发` 同现且值合法放行(形状组合); 判定矩阵 11 例(计划 26-11-07-0441 §04: 分面无派发红/派发 2 过/派发 1 红含骨架/缺检红/P>T 红/P<修+入池 红含口径/弃条目不计下界红/自洽数过/全干净 0-0 过/骨架直贴红/无分面超限过); 触安全敏感面无 trailer 拦(含 0 行)/有有效 trailer 放行; Review 优先于 Skip; 正文畸形 Review 段小批也拦(下限豁免已退役); 记账类(含 legacy-review4/)/生成物不计入
- TraceGateTest       端到端(临时仓库真跑脚本): 复跑标记短路先于消息/基比对(带 trailer 错基也 rc=0)且用后即删; 无 trailer 红(10 行小批/60 行, >0 即评, D9); 仅记账类恒 0 静默; trailer 行数相符+基一致 rc=0 / 行数不符 rc=1; 敏感面批(路径标记词)带 trailer 且基一致放行(端到端); 缺基红 / 基不一致(评审后又改一行)红含重跑出路(D6); Review-Skip 新提交红(D8); 历史 Skip 锚点识别回归(Skip 提交照旧推进锚点, 其后无 trailer 提交连坐滚进, 不追溯); 锚点推进(漏评提交被下一批连坐); 评过的提交推进锚点; 冷启动只算工作树; 合并拓扑两例(0903: 侧支带 trailer 不污染/无 trailer 连坐); 提交后复跑不重对行数且 HEAD 回退打「未给消息文件, 实算 N 行」提示(0441 落点 4); 齐平字段弱校验(计划 26-11-07-0201 落点 3): 缺字段/合法 8hex 静默 rc0, 格式异常打 [warn] 一行但 rc0
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
# 基哈希测试 fixture: 14 行含一个空行(第 3 行), 供 config 漂移测试构造对 context / interHunkContext /
# suppressBlankEmpty 敏感的两处分离改动(第 1 与第 11 行: U3 下两块 hunk, interHunk=3 合一)。
HASH_APP_V1 = "l1\nl2\n\nl4\nl5\nl6\nl7\nl8\nl9\nl10\nl11\nl12\nl13\nl14\n"


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
        self.assertEqual(
            set(self.cfg["tasks"]), {
                "review.pack",
                "review.check",
                "review.trace",
                "review.lane.manifest",
                "review.lane.claim",
                "review.lane.start",
                "review.lane.verify",
                "review.lane.batch",
                "review.lane.done",
                "review.lane.smoke",
            }
        )
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
            (ROOT / "memory-bank" / "reports" / "attachments" / "legacy-review4" /
             "manifest.json").read_text(encoding="utf-8")
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
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(proc.returncode, 2, "无参应退出 2(argparse 用法错误), 不得执行任何真动作")
        self.assertEqual(proc.stdout, "", "无参不得有 stdout 输出")

    def test_help_ok(self):
        proc = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("review_lane.py")), "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
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
        self._write_route(
            {
                "route":
                    "R9",
                "owner":
                    "t",
                "claimed_at":
                    "26-11-06-0000",
                "freeze":
                    "f" * 40,
                "snapshot":
                    str(self.root / "snap"),
                "status":
                    "in-progress",
                "batches":
                    [
                        {
                            "id": "R9-1",
                            "title": "批1",
                            "status": "pending",
                            "done_at": None,
                            "findings": 0
                        },
                        {
                            "id": "R9-2",
                            "title": "批2",
                            "status": "pending",
                            "done_at": None,
                            "findings": 0
                        },
                    ],
            }
        )

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

    def test_snapshot_root_without_git_accepted(self):
        """--root 指向 git archive 快照(无 .git)放行(issue 26-11-06-0711): check 只按 root/file
        读文件逐字比对, 与 git 无关; pack 对同一目录仍拒收(两命令区分, 见 CleanPackTest.test_non_repo_root_is_rc2)。"""
        snap = self.tmp / "snap_no_git"
        snap.mkdir()
        (snap / "mod.py").write_text("alpha line\nbeta line\n", encoding="utf-8")
        fpath = self.tmp / "snap_findings.json"
        fpath.write_text(
            json.dumps([self._finding(file="mod.py", line=2, quote="beta line")], ensure_ascii=False),
            encoding="utf-8",
        )
        proc = _run_script("check", "--findings", str(fpath), "--root", str(snap))
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("[PASS]", proc.stdout)
        self.assertIn("通过 1 / 弃 0", proc.stdout)

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


CONTENT_SCRIPT = Path(__file__).with_name("review_content.py")


def _load_content():
    spec = importlib.util.spec_from_file_location("review_content_under_test", CONTENT_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class BatchBaseHashTest(unittest.TestCase):
    """基哈希(batch_base_hash): 确定性与过滤一致(计划 26-11-08-1240 §03 3.3)。

    「可评路径」判定与提交闸门(check_review_trace)共用 review_content 同一份实现 —— 抽模块的
    目的正是让"记账类/生成物不计行"与"记账类/生成物不影响哈希"不分叉。这里在真临时仓库钉住:
    同一树重复调用同值(含 repo 配置逐颗覆写在场, 抗漂移回归) / 单处可评差异必异值 / 改名按
    删+增展开 / pathspec 逐字精确不重复计入。
    """
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.tmp = Path(self._tmpdir.name)
        self.mod = _load_content()
        self.base = self._init_repo()

    def _git(self, *args: str) -> str:
        proc = subprocess.run(
            ["git", *args], cwd=self.tmp, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        assert proc.returncode == 0, f"git {args}: {proc.stderr}"
        return proc.stdout.strip()

    def _init_repo(self) -> str:
        """基线仓库: app.py 多行可评(HASH_APP_V1); 笔记.py 可评(非 ASCII 路径, 钉 quotepath 面);
        tasks/note.md 记账类; pitfalls/_index.md 落 _index 兜底规则(生成物)。
        ! 可评文件一律 write_bytes 写 LF —— write_text 会按平台翻译成 CRLF, 与 blob(入库归一 LF)
        只差行尾, 正好用来测 --ignore-cr-at-eol(见 test_crlf_only_worktree_noise_does_not_move_hash)。"""
        self._git("init")
        self._git("config", "user.email", "t@example.test")
        self._git("config", "user.name", "t")
        (self.tmp / "app.py").write_bytes(HASH_APP_V1.encode("utf-8"))
        (self.tmp / "笔记.py").write_bytes("第一行\n".encode("utf-8"))
        tasks = self.tmp / "memory-bank" / "tasks"
        tasks.mkdir(parents=True)
        (tasks / "note.md").write_text("记账初版\n", encoding="utf-8")
        pitfalls = self.tmp / "memory-bank" / "pitfalls"
        pitfalls.mkdir()
        (pitfalls / "_index.md").write_text("# 索引\n", encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-m", "base")
        return self._git("rev-parse", "HEAD")

    def _hash(self) -> str:
        return self.mod.batch_base_hash(self.tmp, self.base)

    def test_deterministic_and_12_hex(self):
        self.assertEqual(self._hash(), self._hash())
        self.assertRegex(self._hash(), r"^[0-9a-f]{12}$")

    def test_golden_value_pins_normalization_format(self):
        """金值锚定(评审 T2 二轮 minor): 闸门/review.pack/本测试共用 batch_base_hash, 无独立金值时
        规范化格式一变, 三处同步漂移仍全绿, 历史「已申报的 基」全部误红且无处定位 —— 固定 fixture
        (已跟踪改动 + 非 ASCII 路径改动 + 未跟踪可评文件, 全部 write_bytes 写 LF)硬编码期望 12hex。
        金值锁规范化格式: 改任何一颗规范化钉子/整形旗标本用例必红, 须显式换金值才能过。
        """
        (self.tmp / "app.py").write_bytes(b"L1\nl2\n\nl4\n")  # 已跟踪改动(基线是 HASH_APP_V1)
        (self.tmp / "笔记.py").write_bytes("第一行\n改一行\n".encode("utf-8"))  # 非 ASCII 路径进 diff
        (self.tmp / "fresh_mod.py").write_bytes(b"U = 1\n")  # 未跟踪可评
        self.assertEqual(self._hash(), "acddd04d541d")

    def test_bookkeeping_and_generated_changes_do_not_move_hash(self):
        h0 = self._hash()
        note = self.tmp / "memory-bank" / "tasks" / "note.md"
        note.write_text(note.read_text(encoding="utf-8") + "补写记账\n", encoding="utf-8")  # 已跟踪记账类
        index = self.tmp / "memory-bank" / "pitfalls" / "_index.md"
        index.write_text("# 索引\n重排\n", encoding="utf-8")  # 已跟踪生成物(_index 兜底规则)
        (self.tmp / "memory-bank" / "tasks" / "fresh.md").write_text("新记账\n", encoding="utf-8")  # 未跟踪记账类
        self.assertEqual(self._hash(), h0)

    def test_reviewable_tracked_change_moves_hash(self):
        h0 = self._hash()
        (self.tmp / "app.py").write_text("A = 1\nA = 2\n", encoding="utf-8")
        self.assertNotEqual(self._hash(), h0)

    def test_new_untracked_reviewable_file_moves_hash(self):
        h0 = self._hash()
        (self.tmp / "new_mod.py").write_text("B = 1\n", encoding="utf-8")
        h1 = self._hash()
        self.assertNotEqual(h1, h0)
        (self.tmp / "another.py").write_text("C = 1\n", encoding="utf-8")
        self.assertNotEqual(self._hash(), h1)

    def test_untracked_order_does_not_matter(self):
        """两个未跟踪文件创建顺序相反, 哈希必须相同(规范文本按 path 排序, 不依赖目录序)。"""
        (self.tmp / "b_mod.py").write_text("B = 1\n", encoding="utf-8")
        (self.tmp / "a_mod.py").write_text("A = 1\n", encoding="utf-8")
        h_b_first = self._hash()
        (self.tmp / "a_mod.py").unlink()
        (self.tmp / "b_mod.py").unlink()
        (self.tmp / "a_mod.py").write_text("A = 1\n", encoding="utf-8")
        (self.tmp / "b_mod.py").write_text("B = 1\n", encoding="utf-8")
        self.assertEqual(self._hash(), h_b_first)

    def test_rename_diff_expands_to_delete_plus_add(self):
        """工作树改名必须按「删+增」展开进基哈希(--no-renames 口径, 评审二轮 minor)。

        改名与删+增展开的等价树是同一对 tree 对象 —— 纯哈希相等分不出两种表述, 钉的是文本形态
        本身: name-only 列旧+新两个路径(不是只列新路径), diff 文本含旧路径整段删除与新路径整段
        新增、不出现 rename 段。将来丢 --no-renames(name-only 或 diff 任一处)本用例变红。
        """
        h0 = self._hash()
        self._git("mv", "app.py", "renamed_app.py")
        self.assertNotEqual(self._hash(), h0)  # 改名动了可评内容, 哈希必动
        paths = self.mod._reviewable_tracked_paths(self.tmp, self.base, set())
        self.assertEqual(paths, [b"app.py", b"renamed_app.py"])  # 删+增两条路径
        text = self.mod._tracked_diff(self.tmp, self.base, paths)
        self.assertIn(b"-l1\n", text)  # 旧路径整段删除(不是 rename 配对的精简 hunk)
        self.assertIn(b"+l1\n", text)  # 新路径整段新增(同内容搬运)
        self.assertNotIn(b"rename from", text)
        self.assertNotIn(b"similarity index", text)

    def test_crlf_only_worktree_noise_does_not_move_hash(self):
        """工作树与 blob 只差行尾 CR 不算可评改动(评审二轮 major 的衍生面)。

        env 隔离把 core.autocrlf 掐成默认(不归一), CRLF 工作树对 LF blob 会被误报成整文件改动
        —— --ignore-cr-at-eol 在检测与 hunk 两侧压掉: 工作树 CRLF<->LF 互转, 哈希都必须不动。
        """
        h_crlf = self._hash()  # setUp 基线里 笔记.py 的 blob 是 LF
        (self.tmp / "笔记.py").write_bytes("第一行\r\n".encode("utf-8"))  # 工作树转 CRLF: 纯行尾噪音
        self.assertEqual(self._hash(), h_crlf)
        (self.tmp / "笔记.py").write_bytes("第一行\n".encode("utf-8"))  # 转回 LF: 同样不算改动
        self.assertEqual(self._hash(), h_crlf)
        (self.tmp / "笔记.py").write_bytes("第一行\n真内容变了\n".encode("utf-8"))  # 真内容变更照常动哈希
        self.assertNotEqual(self._hash(), h_crlf)

    def test_pathspec_literal_no_glob_duplication(self):
        """pathspec 逐字精确(评审二轮 nit): 文件名里的 [ ] * 不作通配符 —— f[1].txt 只匹配字面名,
        f1.txt 的 diff 段不因 glob 误匹配跨块重复计入(强制小预算分块后, 无 :(literal) 时
        f[1].txt 所在块会把 f1.txt 的段再吐一遍)。"""
        (self.tmp / "f[1].txt").write_bytes(b"bracket\n")
        (self.tmp / "f1.txt").write_bytes(b"plain\n")
        self._git("add", "-A")
        self._git("commit", "-m", "two files")
        base2 = self._git("rev-parse", "HEAD")
        (self.tmp / "f[1].txt").write_bytes(b"bracket changed\n")
        (self.tmp / "f1.txt").write_bytes(b"plain changed\n")
        paths = self.mod._reviewable_tracked_paths(self.tmp, base2, set())
        self.assertEqual(sorted(paths), [b"f1.txt", b"f[1].txt"])
        budget = self.mod.PATHSPEC_CHAR_BUDGET
        self.mod.PATHSPEC_CHAR_BUDGET = 20  # 强制分块: 两个 pathspec 各占一块(glob 重复才可能跨块发生)
        try:
            text = self.mod._tracked_diff(self.tmp, base2, paths)
        finally:
            self.mod.PATHSPEC_CHAR_BUDGET = budget
        self.assertEqual(text.count(b"diff --git"), 2, "glob 误匹配会把同一文件的 diff 段重复计入")
        self.assertIn(b"+bracket changed\n", text)
        self.assertIn(b"+plain changed\n", text)

    def test_hash_stable_under_config_overrides(self):
        """抗配置漂移回归(评审二轮 major): repo 配置(.git/config)逐颗覆写, 基哈希必须不变。

        env 层掐断 system/global, -c 逐键压过 repo —— 漏一颗钉子这里就红。fixture 让每颗钉子
        「漏了就真的会漂」: 两处分离改动(context/interHunk 敏感) + 空行上下文(suppressBlankEmpty
        敏感) + 非 ASCII 路径(quotepath 敏感) + 未跟踪可评文件(excludesFile 敏感) + 排序文件
        (orderFile 敏感) + 属性文件与大文件阈值(attributesFile/bigFileThreshold 敏感)。
        algorithm/indentHeuristic/renames 靠旗标钉本身, 当前无独立回归用例可证其敏感性
        (改名用例整文件删增对算法选择不敏感, 哈希断言用例不覆盖分档)。
        """
        (self.tmp / "app.py").write_bytes("L1\nl2\n\nl4\nl5\nl6\nl7\nl8\nl9\nl10\nL11\nl12\nl13\nl14\n".encode("utf-8"))
        (self.tmp / "笔记.py").write_bytes("第一行\n改过\n".encode("utf-8"))
        (self.tmp / "extra_mod.py").write_bytes(b"U = 1\n")  # 未跟踪可评
        order_path = self.tmp / "diff-order.txt"
        order_path.write_bytes("笔记.py\napp.py\n".encode("utf-8"))  # 逆序: 若被应用会重排 diff 段
        ignore_path = self.tmp / "extra-ignore.txt"
        ignore_path.write_bytes(b"*.py\n")  # 若被应用会隐藏未跟踪 .py
        attr_path = self.tmp / "diff-attr.txt"
        attr_path.write_bytes(b"*.py -diff\n")  # 若被应用会把 app.py 的 hunk 段压成 Binary files 行
        h_stable = self._hash()
        for key, value in (
            ("diff.context", "1"),
            ("diff.mnemonicPrefix", "true"),
            ("diff.srcPrefix", "X/"),
            ("diff.dstPrefix", "Y/"),
            ("color.ui", "always"),
            ("diff.algorithm", "histogram"),
            ("diff.indentHeuristic", "false"),
            ("diff.noprefix", "true"),
            ("diff.interHunkContext", "3"),
            ("diff.suppressBlankEmpty", "true"),
            ("diff.renames", "true"),
            ("diff.orderFile", order_path.as_posix()),
            ("core.quotepath", "true"),
            ("core.excludesFile", ignore_path.as_posix()),
            ("core.attributesFile", attr_path.as_posix()),
            ("core.bigFileThreshold", "1"),
            ("diff.external", "echo hijacked"),
        ):
            self._git("config", key, value)
            try:
                self.assertEqual(self._hash(), h_stable, f"repo 配置 {key}={value} 漂移了基哈希(漏钉子)")
            finally:
                self._git("config", "--unset", key)

    def test_pack_prints_hash_from_shared_impl(self):
        """pack 的「基哈希:」行必须与共享实现同值(输出行不做第二套计算)。"""
        (self.tmp / "app.py").write_text("A = 1\nA = 2\n", encoding="utf-8")
        proc = _run_script("pack", "--base", self.base, "--root", str(self.tmp))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        line = _line_of(proc.stdout, "基哈希: ")
        self.assertRegex(line, r"^基哈希: [0-9a-f]{12}$")
        self.assertEqual(line, f"基哈希: {self._hash()}")

    def test_generated_paths_prefers_gen_all_listing(self):
        """gen_all.py --list 在盘时用它的权威清单, 并把反斜杠归一成 /。"""
        script_dir = self.tmp / ".agents" / "skills" / "memory-bank" / "scripts"
        script_dir.mkdir(parents=True)
        (script_dir / "gen_all.py"
        ).write_text("print('memory-bank/reports/_index.md')\nprint('auto-qb-data\\\\state.json')\n", encoding="utf-8")
        self.assertEqual(
            self.mod.generated_paths(self.tmp), {"memory-bank/reports/_index.md", "auto-qb-data/state.json"}
        )


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
    # !剥掉消息文件 env(POST_MARKER 同款陷阱的 env 变量版): 闸门在 commit.py 里跑 pytest 时
    # 子进程会继承 COMMIT_FLOW_MSG_FILE, 嵌套的 trace 探针误读真实提交消息 → 「按 HEAD 判」
    # 提示与消息来源断言全歪(2026-11-08 pkg.scoped 实测)。探针的消息来源必须只由参数决定。
    env = {k: v for k, v in os.environ.items() if k != "COMMIT_FLOW_MSG_FILE"}
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)


class TraceDecideTest(unittest.TestCase):
    """评审留痕的纯判定面 —— 判据顺序即优先级(见 check_review_trace 模块头)。

    计划 26-11-08-1240 D8/D9 后的口径: 50 行下限退役(可评行数 >0 一律要 trailer)、Review-Skip 恒红、
    trailer 增 `· 基 <12hex>`(必填)与 `· 轮 R`(缺省 1)。base_hash 直调不传 = 跳过基哈希比对(生产面
    main 恒在有 trailer 时传入; 比对逻辑本身由本类 mismatch/match 两例 + TraceGateTest 端到端钉住)。
    """
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_trace()

    def _decide(self, count: int, msg: str, sensitive=(), base_hash: str | None = None):
        return self.mod.decide(count, list(sensitive), msg, base_hash=base_hash)

    def test_no_pending_change_passes(self):
        self.assertTrue(self._decide(0, "")[0])

    def test_reviewable_lines_without_trailer_fail_at_any_size(self):
        """D9: 50 行下限退役 —— 可评行数 >0 即须 trailer, 1 行/12 行/49 行/50 行/800 行一律拦。"""
        for count in (1, 12, 49, 50, 800):
            ok, why = self._decide(count, "✨ 改了点东西\n")
            self.assertFalse(ok, f"{count} 行无 trailer 应判红")
            self.assertIn("未留痕", why)

    def test_trailer_matching_lines_passes(self):
        ok, _ = self._decide(120, "Review: S3 增量 · 120 行 · blocker 0 · 修 3 · 入池 1 · 检 4/4 · 基 a1b2c3d4e5f6\n")
        self.assertTrue(ok)

    def test_trailer_line_mismatch_fails(self):
        ok, why = self._decide(120, "Review: S3 · 100 行 · blocker 0 · 修 3 · 入池 1 · 基 a1b2c3d4e5f6\n")
        self.assertFalse(ok)
        self.assertIn("≠ 实算 120 行", why)

    def test_trailer_missing_fields_fails(self):
        ok, why = self._decide(120, "Review: S3 · 120 行 · blocker 0\n")
        self.assertFalse(ok)
        self.assertIn("缺字段", why)

    def test_trailer_without_line_count_fails(self):
        ok, why = self._decide(120, "Review: S3 · blocker 0 · 修 3 · 入池 1 · 基 a1b2c3d4e5f6\n")
        self.assertFalse(ok)
        self.assertIn("缺 `<N> 行`", why)

    def test_oversize_needs_split_or_facet(self):
        """>400 行只认 `· 派发 ≥ 2`(计划 26-11-07-0441 D1); `· 分面` 降级为信息字段, 不再放行超限(D8)。"""
        base = "Review: S3 · 800 行 · blocker 0 · 修 3 · 入池 0 · 检 3/3 · 基 a1b2c3d4e5f6"
        ok, why = self._decide(800, base)
        self.assertFalse(ok)
        self.assertIn("拆批", why)
        self.assertIn("派发 ≥ 2", why)  # 失败行给出可操作判据
        self.assertIn("检 ?/?", why)  # 尾附可粘贴整行骨架
        self.assertFalse(self._decide(800, base + " · 分面")[0])  # 带分面无派发仍判红
        self.assertTrue(self._decide(800, base + " · 派发 2")[0])  # 派发 ≥ 2 放行
        self.assertTrue(self._decide(800, base + " · 派发 2 · 分面 · 齐平 a7fb3db7")[0])  # 信息字段并存不碍解析

    # ---- 判定矩阵(计划 26-11-07-0441 §04, 编号照抄; trailer 均含必填的 `· 基`) ----

    def test_matrix01_oversize_facet_without_dispatch_red(self):
        """(1) 带 `· 分面` 无 `· 派发`、带 检 3/3, count=800 → 红(D1: 分面不再是超限通路)。"""
        ok, why = self._decide(800, "Review: S3 · 800 行 · blocker 0 · 修 3 · 入池 0 · 检 3/3 · 基 a1b2c3d4e5f6 · 分面\n")
        self.assertFalse(ok)
        self.assertIn("派发 ≥ 2", why)

    def test_matrix02_oversize_dispatch2_without_facet_passes(self):
        """(2) 带 `· 派发 2` 无 `· 分面`、带 检 3/3, count=800 → 过。"""
        ok, _ = self._decide(800, "Review: S3 · 800 行 · blocker 0 · 修 3 · 入池 0 · 检 3/3 · 基 a1b2c3d4e5f6 · 派发 2\n")
        self.assertTrue(ok)

    def test_matrix03_oversize_dispatch1_red_with_skeleton(self):
        """(3) `派发 1`(或两者皆无), count=800 → 红, 失败行含「派发 ≥ 2」与可粘贴骨架。"""
        ok, why = self._decide(800, "Review: S3 · 800 行 · blocker 0 · 修 3 · 入池 0 · 检 3/3 · 基 a1b2c3d4e5f6 · 派发 1\n")
        self.assertFalse(ok)
        self.assertIn("派发 ≥ 2", why)
        self.assertIn("检 ?/?", why)  # 可粘贴骨架在失败行尾
        self.assertIn("派发 ?", why)
        ok, why = self._decide(800, "Review: S3 · 800 行 · blocker 0 · 修 3 · 入池 0 · 检 3/3 · 基 a1b2c3d4e5f6\n")  # 两者皆无
        self.assertFalse(ok)
        self.assertIn("派发 ≥ 2", why)

    def test_matrix04_missing_check_red_under_ceiling(self):
        """(4) count=120 无 `检` → 红(≤400 也要报校验)。"""
        ok, why = self._decide(120, "Review: S3 · 120 行 · blocker 0 · 修 3 · 入池 1 · 基 a1b2c3d4e5f6\n")
        self.assertFalse(ok)
        self.assertIn("缺字段", why)
        self.assertIn("检", why)

    def test_matrix05_check_p_gt_t_red(self):
        """(5) `检 3/2` → 红(P > T)。"""
        ok, why = self._decide(120, "Review: S3 · 120 行 · blocker 0 · 修 0 · 入池 0 · 检 3/2 · 基 a1b2c3d4e5f6\n")
        self.assertFalse(ok)
        self.assertIn("检 3/2", why)
        self.assertIn("T(送检数)", why)

    def test_matrix06_check_p_below_fix_pool_red(self):
        """(6) 修 5 · 入池 2 · 检 6/6 → 红(P < 修+入池)。"""
        ok, why = self._decide(120, "Review: S3 · 120 行 · blocker 0 · 修 5 · 入池 2 · 检 6/6 · 基 a1b2c3d4e5f6\n")
        self.assertFalse(ok)
        self.assertIn("6 < 修 5 + 入池 2 = 7", why)

    def test_matrix07_refuted_entries_dont_count_red(self):
        """(7) 修 5 · 入池 2 · 检 6/12(6 过 6 弃) → 红, 弃掉的条目不计入下界。"""
        ok, why = self._decide(120, "Review: S3 · 120 行 · blocker 0 · 修 5 · 入池 2 · 检 6/12 · 基 a1b2c3d4e5f6\n")
        self.assertFalse(ok)
        self.assertIn("不进这两个数", why)  # 失败行讲清口径: 修/入池 只数过检且未被 REFUTE 的发现

    def test_matrix08_consistent_numbers_with_dispatch_passes(self):
        """(8) 修 5 · 入池 2 · 检 8/9 · 派发 2, count=120 → 过。"""
        ok, _ = self._decide(120, "Review: S3 · 120 行 · blocker 1 · 修 5 · 入池 2 · 检 8/9 · 基 a1b2c3d4e5f6 · 派发 2\n")
        self.assertTrue(ok)

    def test_matrix09_all_clean_batch_passes(self):
        """(9) 检 0/0 · 修 0 · 入池 0(全干净批) → 过(D6: 0≤P≤T 且 0≥0+0)。"""
        ok, _ = self._decide(120, "Review: S3 · 120 行 · blocker 0 · 修 0 · 入池 0 · 检 0/0 · 基 a1b2c3d4e5f6\n")
        self.assertTrue(ok)

    def test_matrix10_skeleton_paste_red(self):
        """(10) 骨架直贴(`?` 未替换) → 红 —— 每个 `?` 位都不匹配数字/hash 形状, 失败方向安全。"""
        ok, why = self._decide(120, "Review: <范围> · 120 行 · blocker ? · 修 ? · 入池 ? · 检 ?/? · 基 ? · 派发 ?\n")
        self.assertFalse(ok)
        self.assertIn("缺字段", why)
        half = "Review: S3 · 120 行 · blocker 0 · 修 0 · 入池 0 · 检 ?/? · 基 a1b2c3d4e5f6 · 派发 2\n"
        ok, why = self._decide(120, half)  # 只留 `检 ?/?`: 形状校验拦住
        self.assertFalse(ok)
        self.assertIn("检(形状不对", why)
        half = "Review: S3 · 120 行 · blocker 0 · 修 0 · 入池 0 · 检 0/0 · 基 a1b2c3d4e5f6 · 派发 ?\n"
        ok, why = self._decide(120, half)  # 只留 `派发 ?`: 形状校验拦住
        self.assertFalse(ok)
        self.assertIn("派发", why)
        self.assertIn("形状不对", why)
        half = "Review: S3 · 120 行 · blocker 0 · 修 0 · 入池 0 · 检 0/0 · 基 ? · 派发 2\n"
        ok, why = self._decide(120, half)  # 只留 `基 ?`: 形状校验拦住
        self.assertFalse(ok)
        self.assertIn("基(形状不对", why)

    def test_matrix11_oversize_dispatch_without_facet_word_passes(self):
        """(11) 检 2/2 · 派发 2(无分面字样), count=800 → 过(无分面字样的正常超限批)。"""
        ok, _ = self._decide(800, "Review: S3 · 800 行 · blocker 0 · 修 1 · 入池 1 · 检 2/2 · 基 a1b2c3d4e5f6 · 派发 2\n")
        self.assertTrue(ok)

    def test_prose_review_mention_on_small_batch_now_blocks(self):
        """D9: 下限豁免退役 —— 正文里随手一句「Review: 见报告」被当 trailer 校验, 缺行数声明照拦。"""
        ok, why = self._decide(5, "动机: 小改\n\nReview: 见报告\n")
        self.assertFalse(ok)
        self.assertIn("缺 `<N> 行`", why)

    def test_review_skip_retired_always_red(self):
        """D8: 新提交写 Review-Skip 一律判红, 理由长短不再看(历史 trailer 只在锚点 walk 识别)。"""
        ok, why = self._decide(120, "Review-Skip: 改\n")
        self.assertFalse(ok)
        self.assertIn("豁免已退役", why)
        ok, why = self._decide(120, "Review-Skip: 只改了一处文档措辞, 无行为变化, 风险为零, 无需评审\n")
        self.assertFalse(ok)  # 理由再充分也红
        self.assertIn("豁免已退役", why)
        self.assertIn("Review:", why)  # 失败行给出路: 写 Review: 走正常评审

    def test_sensitive_small_change_still_needs_review(self):
        ok, why = self._decide(12, "", sensitive=["src/auto_qb/auth_token.py"])
        self.assertFalse(ok)
        self.assertIn("安全敏感面", why)

    def test_zero_lines_with_sensitive_still_blocks(self):
        """敏感面命中不论行数都要评: 0 行(如二进制敏感文件)也不能静默放行。"""
        ok, why = self._decide(0, "", sensitive=["auto-qb-data/state.json"])
        self.assertFalse(ok)
        self.assertIn("安全敏感面", why)

    def test_sensitive_with_valid_trailer_passes(self):
        """敏感面强制的是「必须评」而非「必红」: 有效 trailer = 已评, 放行(下限退役后旧短路随之失效)。"""
        ok, _ = self._decide(
            12,
            "Review: auth · 12 行 · blocker 0 · 修 0 · 入池 0 · 检 0/0 · 基 a1b2c3d4e5f6\n",
            sensitive=["src/auto_qb/auth_token.py"],
        )
        self.assertTrue(ok)

    def test_review_wins_over_skip(self):
        msg = "Review: S3 · 120 行 · blocker 0 · 修 1 · 入池 0 · 检 1/1 · 基 a1b2c3d4e5f6\nReview-Skip: 随便写写\n"
        self.assertTrue(self._decide(120, msg)[0])  # 有真 trailer 时按 trailer 校验, 不被 skip 短路

    # ---- `· 基 <hash>` 机检(计划 26-11-08-1240 D6) ----

    def test_missing_base_field_red(self):
        """`· 基` 必填: 缺了判红(其余字段齐全也不放行)。"""
        ok, why = self._decide(120, "Review: S3 · 120 行 · blocker 0 · 修 0 · 入池 0 · 检 0/0\n")
        self.assertFalse(ok)
        self.assertIn("缺字段", why)
        self.assertIn("基", why)

    def test_base_hash_shape_red(self):
        """`· 基` 值必须 12 位小写 hex: 非 hex / 不足 / 超长(负向 lookahead)都落形状红。"""
        for bad in ("基 xyz", "基 a1b2c3d4e5f", "基 a1b2c3d4e5f60", "基 A1B2C3D4E5F6"):
            ok, why = self._decide(120, f"Review: S3 · 120 行 · blocker 0 · 修 0 · 入池 0 · 检 0/0 · {bad}\n")
            self.assertFalse(ok, bad)
            self.assertIn("基(形状不对", why)

    def test_base_hash_mismatch_red_with_rerun_hint(self):
        """申报的 基 与闸门重算值不一致 → 红, 失败行给出路(重跑 pack 取新基 + 补一轮复评)。"""
        ok, why = self._decide(
            120,
            "Review: S3 · 120 行 · blocker 0 · 修 0 · 入池 0 · 检 0/0 · 基 a1b2c3d4e5f6\n",
            base_hash="0123abcd4567",
        )
        self.assertFalse(ok)
        self.assertIn("a1b2c3d4e5f6", why)
        self.assertIn("0123abcd4567", why)
        self.assertIn("重跑", why)
        self.assertIn("复评", why)

    def test_base_hash_match_passes(self):
        """申报的 基 与闸门重算值一致 → 放行(比对走 main 传入的重算值, 这里同源注入)。"""
        ok, _ = self._decide(
            120,
            "Review: S3 · 120 行 · blocker 0 · 修 0 · 入池 0 · 检 0/0 · 基 a1b2c3d4e5f6\n",
            base_hash="a1b2c3d4e5f6",
        )
        self.assertTrue(ok)

    # ---- `· 轮 R` 字段(计划 26-11-08-1240 D7) ----

    def test_round_field_optional_defaults_and_shape(self):
        """`· 轮` 可缺省(缺省 1); 出现时必须整数 ≥ 1 —— 轮 0 / 非数字 / 骨架 `轮 ?` 都判红。"""
        base = "Review: S3 · 120 行 · blocker 0 · 修 0 · 入池 0 · 检 0/0 · 基 a1b2c3d4e5f6"
        self.assertTrue(self._decide(120, base)[0])  # 缺省 = 1
        self.assertTrue(self._decide(120, base + " · 轮 1\n")[0])
        self.assertTrue(self._decide(120, base + " · 轮 3\n")[0])  # 修复轮数, 与派发无关
        ok, why = self._decide(120, base + " · 轮 0\n")
        self.assertFalse(ok)
        self.assertIn("轮", why)
        for bad in ("轮 x", "轮 ?"):
            ok, why = self._decide(120, base + f" · {bad}\n")
            self.assertFalse(ok, bad)
            self.assertIn("形状不对", why)

    def test_round_and_dispatch_coexist_passes(self):
        """`· 轮` 与 `· 派发` 同现且值均合法 -> 放行(形状组合: 轮=修复轮数与派发=首轮派遣正交, D7/F4)。"""
        ok, _ = self._decide(800, "Review: S3 · 800 行 · blocker 0 · 修 1 · 入池 1 · 检 2/2 · 基 a1b2c3d4e5f6 · 派发 2 · 轮 2\n")
        self.assertTrue(ok)

    def test_generated_and_bookkeeping_are_not_counted(self):
        self.assertFalse(self._counted("memory-bank/pitfalls/_index.md", set()))
        self.assertFalse(self._counted("memory-bank/tasks/26-11-06-x.md", set()))
        self.assertFalse(self._counted("memory-bank/active-context/26-11-06-0000-x.md", set()))
        self.assertFalse(self._counted("memory-bank/testing/baselines/26-11-06-0000-x.md", set()))
        self.assertFalse(self._counted("memory-bank/reports/attachments/legacy-review4/route-R1.json", set()))
        self.assertFalse(self._counted("memory-bank/reports/attachments/legacy-review4/route-R1-notes.md", set()))
        self.assertTrue(self._counted("memory-bank/reports/attachments/26-10-31-fx-research-notes.md", set()))
        self.assertTrue(self._counted("memory-bank/conventions/collaboration.md", set()))
        self.assertTrue(self._counted("src/auto_qb/core/rules.py", set()))

    def _counted(self, path: str, gen: set[str]) -> bool:
        return self.mod._counted(path, gen)


class TraceGateTest(unittest.TestCase):
    """端到端: 临时仓库里真跑脚本 —— 验锚点推进(漏评的提交滚进下一批)与退出码。

    带 `Review:` trailer 的消息文件统一申报与闸门同源现算的 `· 基`(review_content.batch_base_hash,
    锚点=trace.anchor_commit): 一致才放行 —— 计划 26-11-08-1240 D6; 申报行数按 _append 的实算写。
    """
    @classmethod
    def setUpClass(cls):
        cls.trace = _load_trace()
        cls.content = _load_content()

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

    def _batch_hash(self) -> str:
        """当前批(锚点→工作树)的基哈希 —— 与闸门同源实现现算(D6: 申报值必须来自它)。"""
        return self.content.batch_base_hash(self.tmp, self.trace.anchor_commit(self.tmp))

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

    def test_small_batch_without_trailer_blocks(self):
        """D9: 50 行下限退役 —— 10 行的小改没有 trailer 也判红(可评行数 >0 一律要评)。"""
        self._append(10)
        proc = _run_trace(self.tmp, self._msg("小改\n"))
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("未留痕", proc.stdout)

    def test_zero_reviewable_lines_bookkeeping_only_is_silent(self):
        """实算恒 0(仅记账类) → 静默通过(D9 后仅剩的静默面)。"""
        tasks = self.tmp / "memory-bank" / "tasks"
        tasks.mkdir(parents=True)
        (tasks / "note.md").write_text("记账\n", encoding="utf-8")
        proc = _run_trace(self.tmp, self._msg("记账\n"))
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertEqual(proc.stdout.strip(), "")  # v3 契约: 通过即静默

    def test_above_floor_without_trailer_blocks(self):
        self._append(60)
        proc = _run_trace(self.tmp, self._msg("改了一堆\n"))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("未留痕", proc.stdout)

    def test_trailer_with_matching_count_passes(self):
        """行数相符 + `· 基` 与闸门重算一致 → rc=0(D6 一致放行的端到端面)。"""
        self._append(60)
        msg = f"✨ 改\n\nReview: 本批 · 60 行 · blocker 0 · 修 0 · 入池 0 · 检 0/0 · 基 {self._batch_hash()}\n"
        proc = _run_trace(self.tmp, self._msg(msg))
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_trailer_with_wrong_count_blocks(self):
        self._append(60)
        msg = f"✨ 改\n\nReview: 本批 · 30 行 · blocker 0 · 修 0 · 入池 0 · 检 0/0 · 基 {self._batch_hash()}\n"
        proc = _run_trace(self.tmp, self._msg(msg))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("≠ 实算", proc.stdout)

    def test_missing_base_hash_blocks(self):
        """D6: `· 基` 必填 —— 其余字段齐全但缺基, 判红。"""
        self._append(60)
        proc = _run_trace(self.tmp, self._msg("✨ 改\n\nReview: 本批 · 60 行 · blocker 0 · 修 0 · 入池 0 · 检 0/0\n"))
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("基", proc.stdout)

    def test_base_hash_mismatch_blocks_with_rerun_hint(self):
        """D6: 评审后工作树又改一行 → 申报的 基 已过期, 闸门重算必不一致 → 判红并给出路。"""
        self._append(60)
        stale = self._batch_hash()
        path = self.tmp / "app.py"
        path.write_text(path.read_text(encoding="utf-8") + "EXTRA = 1\n", encoding="utf-8")  # 评审后又有新改动
        msg = f"✨ 改\n\nReview: 本批 · 61 行 · blocker 0 · 修 0 · 入池 0 · 检 0/0 · 基 {stale}\n"
        proc = _run_trace(self.tmp, self._msg(msg))
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn(stale, proc.stdout)
        self.assertIn("重跑", proc.stdout)
        self.assertIn("复评", proc.stdout)

    def test_sensitive_batch_with_trailer_and_matching_base_passes(self):
        """敏感面 x 基比对(端到端): 敏感路径在场 + trailer 齐全 + 基与闸门同源现算一致 -> 放行。

        敏感面强制的是「必须评」而非「必红」(decide 纯判定面已有); 这里补闸门真跑面: 敏感检测来自
        numstat/untracked 的文件路径标记词, 基由 main 用 review_content 现算(含未跟踪可评文件)传入
        decide 比对 —— 敏感面批若被跳过基比对或哈希算错, 本用例红。
        """
        (self.tmp / "auth_mod.py").write_text("A = 1\n" * 5, encoding="utf-8")
        msg = f"✨ 改\n\nReview: auth · 5 行 · blocker 0 · 修 0 · 入池 0 · 检 0/0 · 基 {self._batch_hash()}\n"
        proc = _run_trace(self.tmp, self._msg(msg))
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_review_skip_on_new_commit_blocks(self):
        """D8: 新提交写 Review-Skip → 判红, 理由再充分也不放行(豁免已退役)。"""
        self._append(10)
        proc = _run_trace(self.tmp, self._msg("小改\n\nReview-Skip: 仅措辞微调, 无行为变化, 风险为零\n"))
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("豁免已退役", proc.stdout)

    def test_historical_skip_still_anchors_without_retroaction(self):
        """D8 回归: 历史 Review-Skip 提交在锚点 walk 照旧识别(不追溯重判) —— 它之后的无 trailer
        提交照常连坐滚进下一批(5+10=15 行); 申报实算 15 行 + 同源 基 → 放行。若锚点没识别 Skip,
        批会只算工作树 10 行, 行数与哈希都对不上。"""
        self._append(30)
        self._commit("✨ 老豁免批\n\nReview-Skip: 历史豁免, 退役前入库\n")
        skip_sha = self._git("rev-parse", "HEAD")
        self._append(5)
        self._commit("无 trailer 的中间提交\n")
        self._append(10)
        self.assertEqual(self.trace.anchor_commit(self.tmp), skip_sha)  # Skip 照旧推进锚点
        msg = f"✨ 新批\n\nReview: 新批 · 15 行 · blocker 0 · 修 0 · 入池 0 · 检 0/0 · 基 {self._batch_hash()}\n"
        proc = _run_trace(self.tmp, self._msg(msg))
        self.assertEqual(proc.returncode, 0, proc.stdout)

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
        的提交即建立锚点, 此后一律按锚点滚进。申报 20 行 + 同源 基: 若批被错误算成 50(把上一笔
        已提交的 30 行追溯进来), 行数与哈希都会对不上判红。
        """
        self._append(30)
        self._commit("冷启动前的一笔\n")
        self._append(20)
        msg = f"✨ 冷启动后的一笔\n\nReview: 冷启动批 · 20 行 · blocker 0 · 修 0 · 入池 0 · 检 0/0 · 基 {self._batch_hash()}\n"
        proc = _run_trace(self.tmp, self._msg(msg))
        self.assertEqual(proc.returncode, 0, proc.stdout)  # 只算 20 行, 未把前一笔 30 行算进来

    def test_reviewed_commit_moves_the_anchor(self):
        self._append(60)
        self._commit("✨ 第一批\n\nReview: 第一批 · 60 行 · blocker 0 · 修 0 · 入池 0\n")
        self._append(5)  # 新一批只有 5 行 —— 锚点已前进, 不该被上一批的行数拖累
        msg = f"✨ 小补\n\nReview: 小补 · 5 行 · blocker 0 · 修 0 · 入池 0 · 检 0/0 · 基 {self._batch_hash()}\n"
        proc = _run_trace(self.tmp, self._msg(msg))
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_merge_with_stale_branch_tip_does_not_pollute_the_batch(self):
        """合并拓扑(issue 26-11-08-0903): 侧分支 tip 带 trailer 且基线旧时, 锚点不遮蔽主线、
        树差不把分支已评内容算进本批 —— 逐笔计数只算主线新增 + 工作树。

        复刻事故形态: 锚点 b3(60 行已评) → 侧分支从 b3 切出、tip 带自己的 trailer、改**独立文件**
        (干净合并, 与 26-11-08 实证的事故同形态) → 主线继续推进(已评 c4) → 合并分支 → 工作树 20 行
        新批。平铺锚点/树差算法下锚点取到主线 c4(比 c5 新), 树差把分支 c5 的 30 行整支重复计入
        (实算 50, 消息无 Review 判红); 修复后实算 = 20(工作树; 干净合并的 remerge-diff = 0),
        申报 20 行 + 同源 基(锚点=c4)放行 —— 若行数被算成 110, 声明与哈希都会对不上。
        """
        self._append(60)
        self._commit("✨ b3\n\nReview: b3 · 60 行 · blocker 0 · 修 0 · 入池 0\n")
        self._git("checkout", "-b", "side")
        (self.tmp / "side.py").write_text("S = 1\n" * 30, encoding="utf-8")
        self._commit("✨ c5(侧分支)\n\nReview: 侧分支 · 30 行 · blocker 0 · 修 0 · 入池 0\n")
        self._git("checkout", "master")
        self._append(60)
        self._commit("✨ c4(主线)\n\nReview: 主线 · 60 行 · blocker 0 · 修 0 · 入池 0\n")
        self._git("merge", "--no-edit", "-q", "side")  # 分支侧内容已随 c5 trailer 评过(独立文件, 干净合并)
        self._append(20)  # 本批: 只有工作树 20 行
        msg = f"✨ 新批\n\nReview: 新批 · 20 行 · blocker 0 · 修 0 · 入池 0 · 检 0/0 · 基 {self._batch_hash()}\n"
        proc = _run_trace(self.tmp, self._msg(msg))
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertNotIn("110", proc.stdout)

    def test_untrailered_side_commit_rolled_into_next_batch(self):
        """连坐对侧分支同样成立(评审二轮 major): 无 trailer 的侧分支提交被干净合并后,
        其内容必须按自身 diff 计入下一批 —— 不允许「主线+remerge」口径把它整类漏计(假绿)。

        与上一条同拓扑, 唯一差异: 侧分支 c5 不写 trailer。修复后实算 = 30(侧支自身 diff)
        + 20(工作树) = 50 ≥ 下限, 无 trailer 判红。
        """
        self._append(60)
        self._commit("✨ b3\n\nReview: b3 · 60 行 · blocker 0 · 修 0 · 入池 0\n")
        self._git("checkout", "-b", "side")
        (self.tmp / "side.py").write_text("S = 1\n" * 30, encoding="utf-8")
        self._commit("漏评的侧分支提交\n")
        self._git("checkout", "master")
        self._append(60)
        self._commit("✨ c4(主线)\n\nReview: 主线 · 60 行 · blocker 0 · 修 0 · 入池 0\n")
        self._git("merge", "--no-edit", "-q", "side")
        self._append(20)
        proc = _run_trace(self.tmp, self._msg("新批\n"))
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("50 行", proc.stdout)

    def test_post_marker_skips_recheck_and_is_consumed(self):
        """合流复跑(commit.py 写的 `.git/review_trace_post`)不再对行数, 且标记用后即删。

        ! 这个标记**不能走环境变量**: 闸门里会跑 pytest, 子进程继承 env, 会把"跑闸门脚本并断言它
        判红"的自测全部变成 0(2026-11-06 提交复跑轮真实撞到, 三条自测齐红)。
        """
        self._append(200)
        marker = self.tmp / ".git" / "review_trace_post"
        marker.write_text("deadbeef", encoding="utf-8")
        proc = _run_trace(self.tmp)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertFalse(marker.exists(), "标记应被消费掉, 否则下一次提交会静默跳过检查")

    def test_post_marker_short_circuits_before_base_check(self):
        """复跑短路先于基比对(D6 语义确认): 标记在场时直接 rc=0 —— 即使消息带 `Review:` trailer 且
        `· 基` 故意给错, 也走不到 decide 的基哈希比对(合流复跑那次验的是合并后的树, 行数与基都已对过,
        再算只会把 rebase 进来的远端提交算成本批假红)。标记照旧一次性消费。"""
        self._append(60)
        marker = self.tmp / ".git" / "review_trace_post"
        marker.write_text("deadbeef", encoding="utf-8")
        msg = "✨ 改\n\nReview: 本批 · 60 行 · blocker 0 · 修 0 · 入池 0 · 检 0/0 · 基 000000000000\n"
        proc = _run_trace(self.tmp, self._msg(msg))
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertFalse(marker.exists(), "标记应被消费掉, 否则下一次提交会静默跳过检查")

    def test_post_commit_rerun_does_not_recheck(self):
        self._append(60)
        self._commit("✨ 第一批\n\nReview: 第一批 · 60 行 · blocker 0 · 修 0 · 入池 0\n")
        proc = _run_trace(self.tmp)  # 无 --message-file → 退到 HEAD 消息 = 提交后复跑
        self.assertEqual(proc.returncode, 0, proc.stdout)
        # 落点 4(0441): HEAD 回退不再静默 —— 亮出实算行数(已提交 → 锚点==HEAD → 实算 0), 判定不变
        self.assertIn("未给消息文件", proc.stdout)
        self.assertIn("实算 0 行", proc.stdout)

    # ---- 齐平字段弱校验(计划 26-11-07-0201 落点 3): 不强制存在、不验真值, 只查格式; 异常仅 [warn] 不判红

    def test_trailer_without_flush_field_passes_silently(self):
        """缺齐平字段 → 完全静默通过(rc=0 无输出), 现行为不变。"""
        self._append(60)
        msg = f"✨ 改\n\nReview: 本批 · 60 行 · blocker 0 · 修 0 · 入池 0 · 检 0/0 · 基 {self._batch_hash()}\n"
        proc = _run_trace(self.tmp, self._msg(msg))
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertEqual(proc.stdout.strip(), "")

    def test_trailer_flush_field_valid_passes_silently(self):
        """`· 齐平 <8hex>` 格式合法 → 静默通过(rc=0 无输出); 与 `· 分面`/`· 派发` 并存时行数/字段解析不被后缀破坏。"""
        self._append(60)
        msg = f"✨ 改\n\nReview: 本批 · 60 行 · blocker 0 · 修 0 · 入池 0 · 检 0/0 · 基 {self._batch_hash()} · 齐平 a7fb3db7\n"
        proc = _run_trace(self.tmp, self._msg(msg))
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertEqual(proc.stdout.strip(), "")
        self._append(350)  # 凑到 410 行: 超上限必须 派发 ≥ 2(0441 D1) —— 分面/齐平作为信息字段同现不碍解析
        big = (
            f"✨ 改\n\nReview: 本批 · 410 行 · blocker 0 · 修 0 · 入池 0 · 检 0/0 · 基 {self._batch_hash()}"
            " · 派发 2 · 分面 · 齐平 0123abcd\n"
        )
        proc = _run_trace(self.tmp, self._msg(big))
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertEqual(proc.stdout.strip(), "")

    def test_trailer_flush_field_invalid_warns_but_passes(self):
        """格式异常(非 8 位 hex) → 打一行 [warn] 但 rc=0 放行; 绝不因齐平字段判红。"""
        self._append(60)
        msg = f"✨ 改\n\nReview: 本批 · 60 行 · blocker 0 · 修 0 · 入池 0 · 检 0/0 · 基 {self._batch_hash()} · 齐平 xyz\n"
        proc = _run_trace(self.tmp, self._msg(msg))
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("[warn]", proc.stdout)
        self.assertIn("8位", proc.stdout)
        self.assertNotIn("评审留痕: ", proc.stdout)  # 判红失败行的形状, 不该出现
        # 另一形态: 出现了字段但 hash 缺失/超长, 同样只 warn
        msg = f"✨ 改\n\nReview: 本批 · 60 行 · blocker 0 · 修 0 · 入池 0 · 检 0/0 · 基 {self._batch_hash()} · 齐平 a7fb3db71\n"
        proc = _run_trace(self.tmp, self._msg(msg))
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("[warn]", proc.stdout)


if __name__ == "__main__":
    unittest.main()
