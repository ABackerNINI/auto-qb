"""一次性拆分工具(已归档, 保留供复用): tests/test_web.py -> 16 个平铺测试模块 + webui_helpers.py。

状态: **已归档的一次性工具**。2026-10-08 完成 5 批迁移后按用户拍板保留(原计划 S7 默认删除), 供以后
拆其它大文件复用(计划 26-10-07-2336 §P-03: test_hr_service / test_traffic_sample / test_grouping)。
机制与逐批实测见任务档案 [../tasks/26-10-08-backend-test-web-split.md] §S2–§S7。

背景: 计划 [../plans/26-10-07-2336-plan-test-web-split.html] S2。test_web.py 是当时全仓最大单一
文件(14,556 行 / 329 个被收集测试函数), 按注释分节机械拆成 16 个平铺模块, **零逻辑改动、集合恒等**。
手工搬 1.4 万行必然产生漏迁/重迁/夹具落错文件, 且**测试照样全绿**(bulk-rename 坑档的「静默漏迁」形态);
脚本化后漏迁由校验器钉住, 机械面零判断。

机制(见计划 §5):
1. AST 解析源文件, 顶层语句按「gap 归属」(上一语句 end+1 .. 本语句 end)切成块 —— 每条源行恰属一块,
   前置注释(节标记)随其后第一个函数走。
2. 映射表(函数名 -> 目标文件)从任务档案读取; 辅助函数/常量按「定义 -> 使用」传递闭包定归属:
   跨多文件 -> webui_helpers.py; 恰一个文件 -> 随该文件; 跨文件 fixture(web_env) -> conftest。
3. 每文件 import 头按 used-names 收集裁剪; docstring「## 测试计划」条目按函数名逐条重分布(一行不改写)。
4. 校验 4 条(见 validate): 1 集合恒等 2 计数各恰一次 3 docstring 反幽灵 + 条目守恒 4 可编译。

用法(本脚本已移入 memory-bank/archive/, 从仓库根跑):
    # 演练(不触生产): 全量拆到 testpaths 之外的临时目录, 校验 4 条 + 报表
    uv run python memory-bank/archive/split_test_web.py --out-dir R:/Temp/aqb-split-drill --report
    # 批次(生产): 只迁一批并改写源文件(余量为空则删除)
    uv run python memory-bank/archive/split_test_web.py --out-dir tests --rewrite-source --files <逗号分隔文件名>

红线: 本脚本只做「行在文件间移动」, 不改任何断言/夹具/逻辑。相邻缺陷一律入池 issues, 不顺手修。
"""

import argparse
import ast
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path


def _find_repo() -> Path:
    """仓库根: 从本文件向上找 `.git` —— 本脚本已移入 memory-bank/archive/, 不能再用 `parent.parent`。"""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".git").exists():
            return parent
    return here.parents[2]


REPO = _find_repo()
DEFAULT_SOURCE = REPO / "tests" / "test_web.py"
DEFAULT_MAP = REPO / "memory-bank" / "tasks" / "26-10-08-backend-test-web-split.md"
HELPERS_MODULE = "webui_helpers.py"
HELPERS_STEM = "webui_helpers"
BUCKET_HELPERS = "__helpers__"
BUCKET_CONFTEST = "__conftest__"
BUCKET_REMAINDER = "__remainder__"
DELETE_SOURCE = "__delete_source__"

# 每份新文件的 docstring 标题(第一行)。域描述取自计划 §3.1 总账。
TITLES = {
    "test_web_auth.py": "WEB UI 后端鉴权 / token / SSE 票据 / 跨站闸",
    "test_web_api_core.py": "WEB UI 核心 API 读写",
    "test_webui_static_skins.py": "webui 前端资产静态守阵: 皮肤清单 / CSS / 挂件类名",
    "test_webui_static_dom_panel.py": "webui 前端静态守阵: 详情面板 / 弹窗 / 浮层",
    "test_webui_static_dom_page.py": "webui 前端静态守阵: 页面 / 列模型 / 视图",
    "test_web_traffic_qb.py": "qB 口径流量图三 GET 端点",
    "test_web_backend_misc.py": "WEB 后端杂项: config / token / sites / 分组视图 / 错误原因 / HR 状态",
    "test_web_hr.py": "HR web 端点与搜索 / 文件系统端点",
    "test_web_commands.py": "Web 命令执行 (_drain_web_commands) 与强制汇报确认",
    "test_web_views_reload.py": "Web 视图与配置热重载",
    "test_web_admin.py": "管理端点 (分类 / 标签 / 限速 / 添加 / 导出 / 日志)",
    "test_web_seed_center.py": "种子中心视图 (种子页 / 详情抽屉 / 全局统计)",
    "test_web_route_manifest.py": "W0 结构守阵 + 路由金清单",
    "test_web_keys.py": "键盘快捷键 /api/keys (W6)",
    "test_web_skip_check.py": "跳检三分流预检 + force 透传",
    "test_web_longtail.py": "P1 覆盖率提升轮 + v3 活尾 (运行时 / 命令 / 路由长尾)",
}

PLAN_HEADER = "## 测试计划(每个测试函数一条)"
ENTRY_RE = re.compile(r"^- ([A-Za-z_]\w*):")
FILE_HDR_RE = re.compile(r"^#### (\S+\.py)")
BULLET_RE = re.compile(r"^- ([A-Za-z_]\w*)$")


class SplitError(RuntimeError):
    """拆分或校验失败(命中即中止)。"""


# ---------------------------------------------------------------------------
# 1. 输入: 映射表 + 源文件
# ---------------------------------------------------------------------------


def load_mapping(map_file: Path) -> "dict[str, str]":
    """从任务档案「### 目标文件映射」节读取 函数名 -> 目标文件。

    段界: 「### 目标文件映射」到「**合计 ...」(不含)。条目 = `#### <file>.py` 头下的一串 `- <name>`。
    """
    text = map_file.read_text(encoding="utf-8")
    if "### 目标文件映射" not in text:
        raise SplitError(f"映射表节未找到: {map_file}")
    body = text.split("### 目标文件映射", 1)[1].split("**合计", 1)[0]
    mapping: "dict[str, str]" = {}
    cur = None
    for ln in body.splitlines():
        m = FILE_HDR_RE.match(ln)
        if m:
            cur = m.group(1)
            continue
        b = BULLET_RE.match(ln)
        if cur and b:
            name = b.group(1)
            if name in mapping:
                raise SplitError(f"映射表重复条目: {name} ({mapping[name]} 与 {cur})")
            mapping[name] = cur
    if not mapping:
        raise SplitError("映射表为空")
    return mapping


def parse_source(source: Path):
    """返回 (text, lines(keepends), tree)。"""
    text = source.read_text(encoding="utf-8")
    return text, text.splitlines(keepends=True), ast.parse(text)


def raw_module_docstring(source_lines, doc_node) -> str:
    """从源行**逐字**取模块 docstring 内容(不用 ast.get_docstring —— 它会求值转义, 把 `\\\\p` 吃成 `\\p`)。"""
    if doc_node is None:
        return ""
    s, e = doc_node.lineno, doc_node.end_lineno
    first = source_lines[s - 1]
    q = '"""' if '"""' in first else "'''"
    head = first[first.index(q) + 3:]
    tail = source_lines[e - 1]
    tail = tail[:tail.rindex(q)] if e != s else ""
    mid = "".join(source_lines[s:e - 1])
    return head + mid + tail


def parse_docstring_entries(doc: str) -> "list[tuple[str, list[str]]]":
    """把模块 docstring 的「## 测试计划」节解析成 (函数名, 条目行块) 列表。

    首个条目之前的前言(标题 / 空行 / `## 测试计划` 头)丢弃; 条目区内的 `###` 小标题挂到其后一条。
    """
    doc_lines = doc.splitlines()
    first = None
    for i, ln in enumerate(doc_lines):
        if ENTRY_RE.match(ln):
            first = i
            break
    if first is None:
        return []
    entries = []
    pending = []
    for ln in doc_lines[first:]:
        m = ENTRY_RE.match(ln)
        if m:
            entries.append((m.group(1), pending + [ln]))
            pending = []
        elif ln.startswith("#"):
            pending.append(ln)
        elif entries:
            entries[-1][1].append(ln)
        else:
            pending.append(ln)
    return entries


# ---------------------------------------------------------------------------
# 2. 顶层块划分 + 归属裁决
# ---------------------------------------------------------------------------


def owned_span(node, prev_end: int):
    """gap 归属: 本语句从「上一语句末行 + 1」起, 到自身末行止(前置注释/空行随本块)。"""
    start = node.lineno
    for dec in getattr(node, "decorator_list", None) or []:
        start = min(start, dec.lineno)
    return prev_end + 1, node.end_lineno


def used_names(node) -> "set[str]":
    """节点内出现的全部 Load 名字(递归含装饰器/默认值/注解/嵌套函数体)。"""
    out = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
            out.add(sub.id)
    return out


def top_name(node) -> "str | None":
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return node.name
    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id
    return None


class Model:
    """源文件的顶层结构与归属裁决。"""
    def __init__(self, tree, mapping):
        self.tree = tree
        self.mapping = mapping
        self.file_order = []
        for fn in mapping.values():
            if fn not in self.file_order:
                self.file_order.append(fn)

        self.imports = []
        self.doc_node = None
        self.blocks = []  # (node, start, end)
        prev_end = 0
        for i, node in enumerate(tree.body):
            start, end = owned_span(node, prev_end)
            prev_end = end
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                self.imports.append(node)
            elif i == 0 and isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) \
                    and isinstance(node.value.value, str):
                self.doc_node = node
            else:
                self.blocks.append((node, start, end))

        self.defs = {}  # 顶层函数 / 类
        self.consts = {}
        for node, _s, _e in self.blocks:
            nm = top_name(node)
            if nm is None:
                continue
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                self.defs[nm] = node
            else:
                self.consts[nm] = node

        self.test_names = [n for n in self.defs if n.startswith("test")]
        self.unmapped = [n for n in self.test_names if n not in mapping]  # 源有函数但映射表未列(漏迁)
        self.refs = {name: used_names(node) for name, node in self.defs.items()}
        self.test_to_file = {n: mapping[n] for n in self.test_names if n in mapping}
        self._files_cache = {}
        self.owner = {}
        self._assign()

    def _files_for(self, name, seen=None) -> "set[str]":
        """名字被哪些目标文件(传递)使用。"""
        if name in self._files_cache:
            return self._files_cache[name]
        if seen is None:
            seen = set()
        if name in seen:
            return set()
        seen.add(name)
        out = set()
        for tn, tf in self.test_to_file.items():
            if name in self.refs[tn]:
                out.add(tf)
        for hn in self.defs:
            if hn == name or hn in self.test_to_file:
                continue
            if name in self.refs[hn]:
                out |= self._files_for(hn, seen)
        self._files_cache[name] = out
        return out

    def _assign(self):
        for name, node in list(self.defs.items()) + list(self.consts.items()):
            if name in self.test_to_file:
                self.owner[name] = self.test_to_file[name]
                continue
            if name in self.unmapped:
                continue  # 映射表未列的测试函数: 留给「漏迁」校验报, 不在这里当孤儿炸
            files = self._files_for(name)
            if self._is_fixture(node) and len(files) > 1:
                self.owner[name] = BUCKET_CONFTEST
            elif len(files) > 1:
                self.owner[name] = BUCKET_HELPERS
            elif len(files) == 1:
                self.owner[name] = next(iter(files))
            else:
                raise SplitError(f"顶层 {name} 无任何目标文件引用(孤儿), 归属无法裁决")

    @staticmethod
    def _is_fixture(node) -> bool:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return False
        for dec in node.decorator_list:
            target = dec.func if isinstance(dec, ast.Call) else dec
            if isinstance(target, ast.Attribute) and target.attr == "fixture":
                return True
        return False

    # -- 每 bucket 的节点与引用 --
    def nodes_of(self, bucket):
        return [(n, s, e) for n, s, e in self.blocks if self.owner.get(top_name(n)) == bucket]

    def lineno_of(self, name) -> int:
        node = self.defs.get(name) or self.consts.get(name)
        return node.lineno

    def shared_set(self) -> "set[str]":
        return {n for n, b in self.owner.items() if b == BUCKET_HELPERS}

    def shared_names_used_by(self, nodes) -> "list[str]":
        """nodes 直接引用的跨文件共享名(需 from webui_helpers import ...), 按定义行序。

        扣掉 nodes 自身定义的名(webui_helpers.py 内部互相引用不得自 import)。
        """
        local = {top_name(n) for n, _s, _e in nodes}
        need = set()
        for node, _s, _e in nodes:
            need |= used_names(node)
        return sorted((need & self.shared_set()) - local, key=self.lineno_of)

    @staticmethod
    def used_import_names(nodes) -> "set[str]":
        out = set()
        for node, _s, _e in nodes:
            out |= used_names(node)
        return out


# ---------------------------------------------------------------------------
# 3. 渲染
# ---------------------------------------------------------------------------


def render_imports(model: Model, keep: "set[str]", shared: "list[str]") -> "list[str]":
    """按 used-names 裁剪 import 头; 组间空行按原样保留; 末尾接 from webui_helpers import ...。

    返回的每项都是**带换行**的整行(与源行同构), 供 render_file 直接拼接。
    """
    out = []
    groups = _import_groups(model.imports)
    prev_group = None
    for i, stmt in enumerate(model.imports):
        kept = []
        for a in stmt.names:
            bound = a.asname or (a.name.split(".")[0] if isinstance(stmt, ast.Import) else a.name)
            if bound in keep:
                kept.append(a)
        if not kept:
            continue
        if prev_group is not None and groups[i] != prev_group:
            out.append("\n")
        out.append(_one_import(stmt, kept) + "\n")
        prev_group = groups[i]
    if shared:
        out.append("\n")
        out.append(_render_from_import(HELPERS_STEM, shared) + "\n")
    return out


def _import_groups(imports) -> "list[int]":
    """原 import 块的分组号(源里以空行分隔的组), 用于裁剪后保留原有组结构。"""
    groups = []
    g = 0
    for i, stmt in enumerate(imports):
        if i > 0 and stmt.lineno - imports[i - 1].end_lineno > 1:
            g += 1
        groups.append(g)
    return groups


def _one_import(stmt, kept) -> str:
    parts = [a.name + (f" as {a.asname}" if a.asname else "") for a in kept]
    if isinstance(stmt, ast.Import):
        return "import " + ", ".join(parts)
    mod = ("." * stmt.level) + (stmt.module or "")
    return _render_from_import(mod, parts)


def _render_from_import(mod: str, parts) -> str:
    one = f"from {mod} import " + ", ".join(parts)
    if len(one) <= 100:
        return one
    body = "".join("    " + p + ",\n" for p in parts)
    return f"from {mod} import (\n{body})"


def render_docstring(title: str, entry_blocks) -> str:
    head = f'"""{title}'
    if not entry_blocks:
        return head + '\n"""\n'
    body = "\n".join(ln for blk in entry_blocks for ln in blk)
    return f'{head}\n\n{PLAN_HEADER}\n{body}\n"""\n'


def render_file(model: Model, title: str, nodes, entries, source_lines) -> "tuple[str, str, str]":
    """返回 (整文件文本, 生成的头(新 docstring + 裁剪 import), 原样搬来的块体)。

    头/体分开返回, 供「行守恒」校验按体做逐行比对。
    """
    header = render_docstring(title, entries)
    header += "".join(render_imports(model, Model.used_import_names(nodes), model.shared_names_used_by(nodes)))
    header += "\n"
    body = "".join("".join(source_lines[s - 1:e]) for _node, s, e in nodes)
    return header + body, header, body


# ---------------------------------------------------------------------------
# 4. 主流程
# ---------------------------------------------------------------------------


def build(args):
    """执行拆分; 返回 (outputs, bodies, model, doc_entries, lines, selected)。"""
    mapping = load_mapping(Path(args.map_file))
    _text, lines, tree = parse_source(Path(args.source))
    model = Model(tree, mapping)

    selected = args.files or model.file_order
    for f in selected:
        if f not in model.file_order:
            raise SplitError(f"--files 指定了未知目标文件: {f}")

    doc_entries = parse_docstring_entries(raw_module_docstring(lines, model.doc_node))
    entry_by_name = defaultdict(list)
    for name, blk in doc_entries:
        entry_by_name[name].append(blk)

    outputs = {}
    bodies = {}

    # 共享模块「全量一次性写出」(S3 口径): 共享件在**首个**持有它们的批次随源一起搬出, 之后各批的源里
    # 已无这些块 ⇒ 闭包为空。若此时仍按空 nodes 渲染并写盘, 会把既有 webui_helpers.py 清成只剩头(实测
    # 437→3 行, 直接打爆 conftest 与已迁文件的 import)。故仅当本批确有共享块时才产出该文件, 否则沿用既有。
    helper_nodes = model.nodes_of(BUCKET_HELPERS)
    if helper_nodes:
        outputs[HELPERS_MODULE], _h, bodies[HELPERS_MODULE] = render_file(
            model, "webui_helpers 共享件: test_web 拆分后的跨文件辅助与常量(原 tests/test_web.py)", helper_nodes, [], lines
        )

    for fname in selected:
        nodes = model.nodes_of(fname)
        entries = [blk for node, _s, _e in nodes for blk in entry_by_name.get(top_name(node), [])]
        outputs[fname], _h, bodies[fname] = render_file(
            model, f"{fname[:-3]} 测试计划: {TITLES.get(fname, '')}", nodes, entries, lines
        )

    if args.rewrite_source:
        # 余量 = 未被本次「搬走」的块。搬走面 = 选中文件 + 共享模块(总是写) + conftest(仅当上收)。
        # 否则共享件/夹具会同时留在余量与独立文件里 → 行守恒「多出行」。
        moved = set(selected) | {BUCKET_HELPERS}
        if args.emit_conftest:
            moved |= {BUCKET_CONFTEST}
        remain = [b for b in model.blocks if model.owner.get(top_name(b[0])) not in moved]
        remain_tests = [top_name(b[0]) for b in remain if top_name(b[0]) in model.test_to_file]
        if not remain_tests:
            outputs[DELETE_SOURCE] = ""
        else:
            entries = [blk for node, _s, _e in remain for blk in entry_by_name.get(top_name(node), [])]
            title = f"{Path(args.source).stem} 测试计划: WEB UI 后端(拆分进行中, 余 {len(remain_tests)} fn)"
            src_name = Path(args.source).name
            outputs[src_name], _h, bodies[src_name] = render_file(model, title, remain, entries, lines)

    return outputs, bodies, model, doc_entries, lines, selected


# ---------------------------------------------------------------------------
# 5. 校验 4 条
# ---------------------------------------------------------------------------


def _test_names_of(path: Path) -> "list[str]":
    t = ast.parse(path.read_text(encoding="utf-8"))
    return [
        n.name for n in t.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test")
    ]


def _all_top_names(path: Path) -> "set[str]":
    t = ast.parse(path.read_text(encoding="utf-8"))
    return {nm for nm in (top_name(n) for n in t.body) if nm}


def validate(
    out_dir: Path,
    model: Model,
    doc_entries,
    selected,
    rewritten_source: Path | None,
    emit_conftest: bool,
    source_lines,
    bodies: "dict[str, str] | None" = None,
    expect_fn: int = 329,
    expect_entries: int = 312
):
    problems = []
    stats = {}

    # 源侧计数钉死(计划 §9 收口口径): 函数 329 / 条目 312 —— 与「按源自身计数」比会漏掉「整行删掉」
    if len(model.test_to_file) != expect_fn:
        problems.append(f"[校验1] 源被收集测试函数 {len(model.test_to_file)} != 应 {expect_fn}")
    if len(doc_entries) != expect_entries:
        problems.append(f"[校验3] 源 docstring 条目 {len(doc_entries)} != 应 {expect_entries}(漏登/多登)")
    stats["src_fn"] = len(model.test_to_file)
    stats["src_entries"] = len(doc_entries)

    # 源侧反幽灵: 条目名必须都是源里的真实函数
    ghosts = sorted({n for n, _blk in doc_entries} - set(model.test_to_file))
    if ghosts:
        problems.append(f"[校验3] 源 docstring 幽灵条目(无对应函数): {ghosts}")

    # 源侧漏迁: 被收集测试函数必须在映射表里
    if model.unmapped:
        problems.append(f"[校验1] 源有测试函数但映射表未列(漏迁) {len(model.unmapped)} 个: {model.unmapped[:8]}")

    emitted = [out_dir / f for f in selected] + [out_dir / HELPERS_MODULE]
    if rewritten_source is not None:
        emitted.append(rewritten_source)

    # 校验 1 + 2: 集合恒等 + 各恰一次
    seen = defaultdict(list)
    for p in emitted:
        if p.exists():
            for n in _test_names_of(p):
                seen[n].append(p.name)
    dup = {n: ps for n, ps in seen.items() if len(ps) > 1}
    if dup:
        problems.append(f"[校验2] 测试函数重迁(同名多处): {dup}")
    # 批内(rewrite): 迁走的函数落 selected 文件, 余量留在改写后的源文件 —— 并集仍是全量, 故恒比全量。
    expect = set(model.test_to_file)
    got = set(seen)
    if expect - got:
        problems.append(f"[校验1] 漏迁(应迁未迁) {len(expect - got)} 个: {sorted(expect - got)[:8]}")
    if got - expect:
        problems.append(f"[校验1] 多出(源中不存在) {len(got - expect)} 个: {sorted(got - expect)[:8]}")
    stats["emitted_fn"] = len(got)

    # 校验 3: 反幽灵 + 条目守恒
    total_entries = 0
    for fname in selected:
        p = out_dir / fname
        if not p.exists():
            continue
        doc = ast.get_docstring(ast.parse(p.read_text(encoding="utf-8")), clean=False) or ""
        names = _all_top_names(p)
        for name, _blk in parse_docstring_entries(doc):
            total_entries += 1
            if name not in names:
                problems.append(f"[校验3] {fname} docstring 幽灵条目: {name}(本文件无此函数)")
    expect_entries = sum(1 for n, _blk in doc_entries if model.test_to_file.get(n) in selected)
    if total_entries != expect_entries:
        problems.append(f"[校验3] 条目总数不守恒: 实 {total_entries} != 应 {expect_entries}")
    stats["entries"] = total_entries

    # 内容守恒: 所有块必须落到某个被写出的 bucket(conftest 桶在演练/未上收时可延后)
    # 批内: 选中文件 + 余量(源文件) + 共享模块; conftest 未上收时随余量留在源文件里。
    written = set(selected) | {BUCKET_HELPERS}
    if rewritten_source is not None:
        written |= set(model.file_order)
        if not emit_conftest:
            written |= {BUCKET_CONFTEST}
    if emit_conftest:
        written |= {BUCKET_CONFTEST}
    deferred = []
    lost = []
    for b in model.blocks:
        bucket = model.owner.get(top_name(b[0]))
        if bucket in written:
            continue
        if bucket == BUCKET_CONFTEST:
            deferred.append(top_name(b[0]))
        else:
            lost.append(top_name(b[0]))
    if lost:
        problems.append(f"[内容守恒] {len(lost)} 个块未落任何输出文件: {lost[:8]}")
    stats["deferred_conftest"] = deferred

    # 行守恒: 被写出文件的「块体」逐行 == 源里这些块的源行(逐行搬移, 零改写/零丢失)
    # conftest 夹具由 _append_conftest 直接写、不进 bodies, 故从比对面排除。
    if bodies is not None:
        # conftest 夹具若已上收则由 _append_conftest 直接写、不进 bodies ⇒ 从比对面排除;
        # 未上收时它留在源文件余量里, 属 bodies, 故保留。
        body_written = written - ({BUCKET_CONFTEST} if emit_conftest else set())
        exp_counter = Counter()
        for node, s, e in model.blocks:
            if model.owner.get(top_name(node)) in body_written:
                exp_counter.update(source_lines[s - 1:e])
        got_counter = Counter()
        for fname in list(selected) + [HELPERS_MODULE]:
            if fname in bodies:
                got_counter.update(bodies[fname].splitlines(keepends=True))
        if rewritten_source is not None and rewritten_source.name in bodies:
            got_counter.update(bodies[rewritten_source.name].splitlines(keepends=True))
        if exp_counter != got_counter:
            miss = sum((exp_counter - got_counter).values())
            extra = sum((got_counter - exp_counter).values())
            problems.append(f"[行守恒] 块体逐行不守恒: 少 {miss} 行 / 多 {extra} 行")
        stats["body_lines"] = sum(got_counter.values())

    # 校验 4: 可编译(内存编译, 不落 .pyc)
    for p in emitted:
        if p.exists():
            try:
                compile(p.read_text(encoding="utf-8"), str(p), "exec")
            except SyntaxError as exc:
                problems.append(f"[校验4] {p.name} 编译失败: {exc}")
    return problems, stats


def collect_only(paths, expected_fns: "set[str]") -> bool:
    """校验 4 的收集面: pytest --collect-only 计数恒等(项数 + 函数名集合)。

    走 -o addopts= 清掉 -n 4/覆盖率, 只做收集(不跑用例, 故 fixture 缺失无妨)。
    paths 为**显式文件列表** —— 演练给输出目录, 批内给「选中文件 + 共享模块 + 改写后源文件」,
    避免在批内收集整个 tests/ 目录(那会把仓里其余测试一并算进来)。
    """
    cmd = [sys.executable, "-m", "pytest", "--collect-only", "-q", "-o", "addopts=", "-p", "no:cacheprovider"
          ] + [str(p) for p in paths]
    try:
        proc = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        print("  [FAIL] [校验4] collect-only 超时")
        return False
    out = proc.stdout + proc.stderr
    items = [ln for ln in out.splitlines() if "::" in ln]
    fns = {ln.split("::")[-1].split("[", 1)[0].strip() for ln in items}
    ok = proc.returncode == 0 and len(items) > 0 and fns == expected_fns
    print(
        f"  [校验4] collect-only: {len(items)} 项 / {len(fns)} 函数名 (rc={proc.returncode}) "
        f"{'== 源' if fns == expected_fns else '!= 源: ' + str(sorted(expected_fns ^ fns)[:8])}"
    )
    if not items:
        print("     提示: 需在带 pytest 的解释器下跑本脚本(如 `uv run python scripts/split_test_web.py ...`)")
    return ok


# ---------------------------------------------------------------------------
# 6. CLI
# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="test_web.py 拆分工具(计划 26-10-07-2336 S2)")
    ap.add_argument("--out-dir", required=True, help="输出目录(演练给 testpaths 之外的临时目录)")
    ap.add_argument("--source", default=str(DEFAULT_SOURCE), help="源测试文件")
    ap.add_argument("--map-file", default=str(DEFAULT_MAP), help="映射表(任务档案)")
    ap.add_argument("--files", default="", help="逗号分隔的目标文件名子集(默认全部)")
    ap.add_argument("--rewrite-source", action="store_true", help="批次模式: 改写源文件(余量为空则删除)")
    ap.add_argument("--emit-conftest", default="", help="把跨文件 fixture(web_env) 追加到该 conftest 路径")
    ap.add_argument("--collect", action="store_true", help="额外跑 pytest --collect-only 计数恒等校验")
    ap.add_argument("--expect-fn", type=int, default=329, help="被收集测试函数总数(计划收口口径)")
    ap.add_argument("--expect-entries", type=int, default=312, help="docstring 计划条目总数(计划收口口径)")
    ap.add_argument("--report", action="store_true", help="打印归属/条目报表")
    args = ap.parse_args(argv)
    args.files = [s.strip() for s in args.files.split(",") if s.strip()]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        outputs, bodies, model, doc_entries, source_lines, selected = build(args)
    except SplitError as exc:
        print(f"[FAIL] 拆分中止: {exc}")
        return 2

    deleted = False
    for fname, content in outputs.items():
        if fname == DELETE_SOURCE:
            deleted = True
            continue
        (out_dir / fname).write_text(content, encoding="utf-8", newline="")

    rewritten = None
    if args.rewrite_source:
        src = Path(args.source)
        if deleted:
            if src.exists():
                src.unlink()
            print(f"[删除] 源文件余量为空, 已删除 {src}")
        else:
            src.write_text(outputs[src.name], encoding="utf-8", newline="")
            rewritten = src

    if args.emit_conftest:
        _append_conftest(Path(args.emit_conftest), model, source_lines)

    if args.report:
        _report(model, selected, outputs)

    problems, stats = validate(
        out_dir, model, doc_entries, selected, rewritten, bool(args.emit_conftest), source_lines, bodies,
        args.expect_fn, args.expect_entries
    )
    print("\n=== 校验 ===")
    print(
        f"  源: 函数 {stats.get('src_fn')} / 条目 {stats.get('src_entries')}; "
        f"输出: 函数 {stats.get('emitted_fn')} / 条目 {stats.get('entries')} / 块体行 {stats.get('body_lines')}"
    )
    if stats.get("deferred_conftest"):
        print(f"  [defer] conftest 桶(演练未写出): {stats['deferred_conftest']}")
    if args.collect:
        # 收集面 = 本次被写出的全部文件; 恒比全量函数名集。
        # - 演练/全量模式(未改写源): 整个 out_dir;
        # - 批模式: 选中文件 + 共享模块 (+ 改写后的源文件, 仅当余量非空未被删)。
        # 判据必须看 args.rewrite_source, 不能看 rewritten —— 末批余量为空会删源, 此时 rewritten 仍为 None,
        # 若按 None 走「整个 out_dir」分支, 会去收集整个 tests/ 目录(实测 2,689 项), 校验4 假红。
        if args.rewrite_source:
            targets = [out_dir / f for f in selected] + [out_dir / HELPERS_MODULE]
            if rewritten:
                targets.append(Path(args.source))
        else:
            targets = [out_dir]
        if not collect_only(targets, set(model.test_to_file)):
            problems.append("[校验4] collect-only 计数不恒等")
    if problems:
        for p in problems:
            print("  [FAIL] " + p)
        return 1
    print("  [OK] 校验 1-4 + 内容守恒 全绿")
    return 0


def _append_conftest(conftest: Path, model: Model, source_lines):
    """把跨文件 fixture(web_env) 追加到 conftest; 幂等(已存在即跳过), 并补 from webui_helpers 导入。"""
    text = conftest.read_text(encoding="utf-8")
    fixtures = model.nodes_of(BUCKET_CONFTEST)
    if not fixtures:
        return
    added = [source_lines[s - 1:e] for _n, s, e in fixtures]
    names = [top_name(n) for n, _s, _e in fixtures]
    for nm in names:
        if f"def {nm}(" in text:
            print(f"[conftest] 已存在 {nm}, 跳过")
            return
    need = set()
    for node, _s, _e in fixtures:
        need |= used_names(node)
    shared = sorted(need & model.shared_set(), key=model.lineno_of)
    block = "\n\n"
    if shared:
        block += _render_from_import(HELPERS_STEM, shared) + "\n\n\n"
    for chunk in added:
        block += "".join(chunk) + "\n\n"
    conftest.write_text(text.rstrip("\n") + "\n" + block.rstrip("\n") + "\n", encoding="utf-8", newline="")
    print(f"[conftest] 追加 {names} 到 {conftest}")


def _report(model: Model, selected, outputs):
    print("=== 归属裁决 ===")
    for fname in selected:
        nodes = model.nodes_of(fname)
        tests = [top_name(n) for n, _s, _e in nodes if top_name(n) in model.test_to_file]
        local = [top_name(n) for n, _s, _e in nodes if top_name(n) not in model.test_to_file]
        shared = model.shared_names_used_by(nodes)
        print(
            f"  {fname:34s} fn={len(tests):3d} 本地件={len(local):2d} 共享件={len(shared):2d} "
            f"行={outputs[fname].count(chr(10))}"
        )
    helpers = model.nodes_of(BUCKET_HELPERS)
    if HELPERS_MODULE in outputs:
        print(f"  {HELPERS_MODULE:34s} 件={len(helpers)} 行={outputs[HELPERS_MODULE].count(chr(10))}")
    else:
        print(f"  {HELPERS_MODULE:34s} 件=0 (本批无共享块, 沿用既有文件)")
    conftest = [n for n, b in model.owner.items() if b == BUCKET_CONFTEST]
    print(f"  conftest 件={len(conftest)}: {conftest}")
    print(f"  共享辅助/常量({len(model.shared_set())}): " + ", ".join(sorted(model.shared_set())))
    single = {
        n: b
        for n, b in model.owner.items() if b not in (BUCKET_HELPERS, BUCKET_CONFTEST) and n not in model.test_to_file
    }
    print(f"  随唯一使用域的辅助/常量: {len(single)}")


if __name__ == "__main__":
    sys.exit(main())
