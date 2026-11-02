#!/usr/bin/env python3
"""HTML 结构守卫: 拦「闭合标签缺 `>` 」这类静默吞正文的坏标签 + v.Nu 规范级巡检。

━━ 背景 (2026-11-01 两起实测事故) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
手编生成物 HTML 时把闭合标签写成 `</code)` / `</code下` (少 `>`):
    issues/26-11-01-0334-bug-torrent-transfer-duplicate-409.html:113 (s2-s7/footer 全嵌进未闭合
    code, 掉进 200px 左栏) · reports/26-10-14-1110-...html:320 (同型)。
HTML5 容错设计下这是**静默**的: 分词器把 `</code): 目标 …。</p` 连同下一个 `>` 整段吃进一个
非法尾标签, `<code>` 永不闭合, 其后全部内容嵌进它 (浏览器实测 DOM 复核) —— 页面能打开、
无任何报错, 只有排版错乱。规范级证据 (W3C v.Nu 实测): `Stray end tag "code)"` /
`Unclosed element "code"` / `Element "section" not allowed as child of element "code"`。
机检依据 (stdlib html.parser 实测): 坏尾标签以残缺名 `code):` 到达 handle_endtag —— 永不
匹配栈上的 `code`, 与浏览器同款行为, 故进程内解析即可复现病灶, 无需起子进程。

━━ 两层常驻判据 (零依赖, 全库 645 件 <2s) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
L1 正则 (行级, file:line): 尾标签名后紧跟非空白/`/`/`>` 的字符 —— 直接命中
    `</code)` 与 `</code下` 两种笔误形态。
L2 解析 (stdlib html.parser): start/end 标签名必须匹配 `^[a-zA-Z][a-zA-Z0-9-]*$` ——
    拦任意分隔符形态的残缺标签 (含开标签 `<code)…>`), 与 L1 互为独立第二网。
更广的规范级伤害 (嵌套违规 / 未转义 `<` / 属性烂在标签里) 归 `--vnu` 巡检, 不在此重复造。

━━ v.Nu 巡检 (--vnu, 规范级, 需 java) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
W3C 官方校验器 v.Nu (vnu.jar, ~32MB, 不进仓库): 落点 `<root>/.tools/vnu.jar` (gitignored),
缺失时自动从 GitHub 下载。两种跑法:
    --vnu <files...>   只查给定文件 —— 提交闸门用 `<changed:**/*.html>` 增量 (2026-11-01 起
                       全仓改动 HTML, 不限 memory-bank), 配 `--strict` 有 error 即 rc=1
                       (改谁谁达标, 存量文件不进检查面)。
    --vnu --all        全库巡检 (实测 645 件 ~9s) —— 默认**只报告不拦** (存量 320 条 error
                       属债务, 清理走专门会话), `--strict` 才 rc=1。

⚠ Vue 模板分片不送 v.Nu (2026-11-02): `src/auto_qb/webui/static/shared/tpl/*.html` 是 Vue
模板片段 (由 boot.js 按 tpl-manifest 聚合成页面), 里面的 `v-if` / `@click` / `:class` 是指令
不是 HTML 属性 —— v.Nu 按 HTML 文档语义校验, 必然逐条报 `Attribute "…" not allowed`。
实测首次提交改分片时 22 条 error 全属此类 (同批 showcase.html 零 error)。故 run_vnu 先按
路径判据摘掉这些分片并在输出里写明 (摘掉要可见, 不静默), 全被摘掉时不下载 jar、不依赖 JDK。
L1+L2 对分片照常跑 —— 结构判据 (闭合标签/标签名) 对模板片段同样成立。

用法 (从仓库根; `<skill-dir>` = memory-bank skill 实际所在目录):
    python <skill-dir>/scripts/check_html.py --check          全库 L1+L2 守卫, 有命中 rc=1
    python <skill-dir>/scripts/check_html.py <files...>       只查给定文件 (闸门 <changed:> 用)
    python <skill-dir>/scripts/check_html.py --vnu --strict <files...>   增量规范级 (闸门)
    python <skill-dir>/scripts/check_html.py --vnu --all      全库巡检报告 (kb.html-audit)
    python <skill-dir>/scripts/check_html.py --safety         冒烟探针 (无参是否真动作)
"""

from __future__ import annotations

import re
import subprocess
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import find_root, rel_posix, resolve_mb_dir  # noqa: E402

# --------------------------------------------------------------------------- 判据

# L1: 尾标签名后紧跟非法字符 (非标签名字符且非空白 / `/` / `>`)。两个 lookahead 缺一不可:
# 只留后者的会让引擎把 `</title>` 回溯成 `</titl`+`e` 穿过否定前瞻而全库误报 (2026-11-01 首跑实测)。
END_TAG_BAD_RE = re.compile(r"</([A-Za-z][A-Za-z0-9-]*)(?![A-Za-z0-9-])(?![\s/>])")

# L2: 合法标签名 (start 与 end 同判)。残缺名 (如 `code):` / `code下`) 一律判红。
TAG_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9-]*$")

# script/style 内容遮蔽: 分词器在 script data 态不把 `</g,` 当标签 (JS 字面量 `replace(/</g, …)`
# 的存量实况: plans/26-09-25-2043:502, html.parser 同判不报)。L1 在遮蔽后的文本上跑, 位置不变
# (等长替换保行号); L2 走 html.parser 自身的 CDATA 态, 天然无此误报。
CDATA_BLOCK_RE = re.compile(r"(<(script|style)\b[^>]*>).*?(</\2\s*>)", re.DOTALL | re.IGNORECASE)


def mask_cdata(text: str) -> str:
    """把 <script>/<style> 内容替换成等长空白 (保行号); 标签对本身保留。"""
    def _blank(m: re.Match) -> str:
        body = m.group(0)[len(m.group(1)):-len(m.group(3))]
        return m.group(1) + re.sub(r"[^\n]", " ", body) + m.group(3)

    return CDATA_BLOCK_RE.sub(_blank, text)


# v.Nu 发行单点 (latest 跟随上游; jar 本体不进仓库, 落 gitignored 的 .tools/)
VNU_URL = "https://github.com/validator/validator/releases/download/latest/vnu.jar"
TOOLS_DIRNAME = ".tools"


class _TagValidator(HTMLParser):
    """L2: 校验全部 start/end 标签名; 记录 (行, 列, 残缺名)。"""
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.bad: list[tuple[int, str]] = []

    def _check(self, tag: str) -> None:
        if not TAG_NAME_RE.match(tag):
            line, col = self.getpos()
            self.bad.append((line, tag))

    def handle_starttag(self, tag: str, attrs: dict) -> None:
        self._check(tag)

    def handle_startendtag(self, tag: str, attrs: dict) -> None:
        self._check(tag)

    def handle_endtag(self, tag: str) -> None:
        self._check(tag)


def check_text(text: str) -> list[str]:
    """单文件两层判据 → 问题列表 (行内描述, 无路径前缀)。"""
    problems: list[str] = []
    for m in END_TAG_BAD_RE.finditer(mask_cdata(text)):
        line = text.count("\n", 0, m.start()) + 1
        snippet = text[m.start():m.start() + 40].replace("\n", "\\n")
        problems.append(f"行 {line}: 闭合标签缺 '>': {snippet!r}")
    parser = _TagValidator()
    parser.feed(text)
    parser.close()
    for line, tag in parser.bad[:20]:
        problems.append(f"行 {line}: 残缺标签名 {tag!r} (解析器收到, 永不匹配真实元素)")
    return problems


def collect_files(mb: Path, paths: list[Path] | None) -> list[Path]:
    """检查面: 显式文件参数优先 (闸门 <changed:> 形态); 否则全库 *.html。"""
    if paths:
        return sorted(p for p in paths if p.is_file() and p.suffix == ".html")
    return sorted(mb.rglob("*.html"))


# x-template 碎片: 全文件只由 <script type="text/x-template"> 块(夹注释/空白)组成,
# 被前端 fetch 后内联进宿主文档, 自己不是独立 HTML 文档 —— v.Nu 的 document 级规则
# (doctype / title)对它无意义 (2026-11-02 ship.commit 实测: xtpl.html 被误报 2 条)。
# 这类文件仍过 L1+L2 常驻判据 (标签配平面), 此处只豁免 --vnu 的文档级检查。
_XTPL_FRAG_RE = re.compile(
    r"^(?:\s|<!--.*?-->|<script\b[^>]*\btype=[\"']text/x-template[\"'][^>]*>.*?</script>)+$",
    re.S,
)


def is_xtemplate_fragment(path: Path) -> bool:
    try:
        text = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        return False
    return bool(_XTPL_FRAG_RE.fullmatch(text.strip()))


def run_l1l2(files: list[Path], root: Path) -> int:
    """L1+L2 逐文件检查; 命中打印 file:问题 并 rc=1。"""
    bad_total = 0
    for path in files:
        try:
            text = path.read_bytes().decode("utf-8")
        except UnicodeDecodeError as exc:
            print(f"{rel_posix(path, root)}: 非 UTF-8, 跳过结构判据 ({exc})")
            continue
        for problem in check_text(text):
            print(f"{rel_posix(path, root)}:{problem}")
            bad_total += 1
    if bad_total:
        print(f"[红] check_html: {bad_total} 处坏标签 / {len(files)} 个文件 —— 修复形态见模块 docstring")
        return 1
    print(f"[ok] check_html: {len(files)} 个 HTML, L1+L2 零命中")
    return 0


# --------------------------------------------------------------------------- v.Nu 巡检


def ensure_vnu_jar(root: Path) -> Path:
    """vnu.jar 落点 `<root>/.tools/vnu.jar`; 缺失时下载 (32MB, 一次性)。"""
    jar = root / TOOLS_DIRNAME / "vnu.jar"
    if jar.is_file():
        return jar
    jar.parent.mkdir(parents=True, exist_ok=True)
    print(f"[..] check_html: vnu.jar 缺失, 下载到 {rel_posix(jar, root)} (~32MB, 一次性) …")
    urllib.request.urlretrieve(VNU_URL, jar)
    print(f"[ok] check_html: vnu.jar 就绪 ({jar.stat().st_size} 字节)")
    return jar


# Vue 模板分片的家 (单点 = tpl-manifest 的目录约定): 这些 .html 是模板**片段**, 由 boot.js
# 按清单聚合成页面再注入。v-if / @click / :prop 是 Vue 指令而非 HTML 属性, v.Nu 必报
# `Attribute "…" not allowed` —— 那是范畴错误, 不是缺陷 (2026-11-02 首次提交改分片实测
# 22 条, 同批 showcase.html 零 error)。判据只认路径: 兜底成"内容含 v- 就跳过"会把真正
# 写坏属性名的页面一起放过, 得不偿失。
VUE_TPL_SEGMENTS = ("shared", "tpl")


def is_vue_template_fragment(path: Path, root: Path) -> bool:
    """该文件是否为 `shared/tpl/` 下的 Vue 模板分片 (v.Nu 不适用)。"""
    try:
        parts = path.resolve().relative_to(root.resolve()).parts
    except (ValueError, OSError):
        return False
    n = len(VUE_TPL_SEGMENTS)
    return any(tuple(parts[i:i + n]) == VUE_TPL_SEGMENTS for i in range(len(parts) - n + 1))


def run_vnu(files: list[Path], root: Path, strict: bool, java: str) -> int:
    """跑 v.Nu; 输出归一为 `仓库相对路径:行: error: 文案`; --strict 有 error 即 rc=1。"""
    if not files:
        print("[ok] check_html --vnu: 本次无 HTML 改动, 跳过")
        return 0
    fragments = [p for p in files if is_xtemplate_fragment(p)]
    if fragments:
        files = [p for p in files if p not in fragments]
        print(
            f"[ok] check_html --vnu: 跳过 {len(fragments)} 个 x-template 碎片 (非独立文档, 仍过 L1+L2): " +
            ", ".join(rel_posix(p, root) for p in fragments)
        )
        if not files:
            return 0
    skipped = [p for p in files if is_vue_template_fragment(p, root)]
    if skipped:
        files = [p for p in files if p not in skipped]
        print(
            "[--] check_html --vnu: 跳过 Vue 模板分片 (v-if/@click/:prop 属模板语法, v.Nu 不适用): " +
            ", ".join(rel_posix(p, root) for p in skipped)
        )
        if not files:
            print("[ok] check_html --vnu: 本次改动全是 Vue 模板分片, 无需 v.Nu")
            return 0
    jar = ensure_vnu_jar(root)
    cmd = [java, "-jar", str(jar), "--asciiquotes", "--errors-only", "--exit-zero-always", *[str(p) for p in files]]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    except FileNotFoundError:
        print(f"[红] check_html --vnu: java 不可用 ({java!r} 未找到) —— 装 JDK 后重跑, 或只依赖 L1+L2 常驻判据")
        return 1
    errors = [ln for ln in (proc.stdout + proc.stderr).splitlines() if ": error:" in ln]
    for ln in errors:
        print(ln.replace("file:/", "").replace(f"file:{root.as_posix()}/", ""))
    if not errors:
        print(f"[ok] check_html --vnu: {len(files)} 个文件, 零 error")
        return 0
    print(
        f"[{'红' if strict else '债'}] check_html --vnu: {len(errors)} 条 error / {len(files)} 个文件" +
        ("" if strict else " —— 巡检报告, 不拦; 清理走专门会话")
    )
    return 1 if strict else 0


# --------------------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    root = find_root()
    mb = resolve_mb_dir(root)

    if "--safety" in args:
        print("read-only: 纯校验不写文件 (--vnu 首跑会下载 vnu.jar 到 gitignored 的 .tools/)")
        return 0

    # 提交闸门冒烟探针 (<each:|--with-safety>) 会逐脚本跑 --help: 必须友好退出 rc=0,
    # 陌生参数 rc=2 会让整个提交闸门红 (2026-11-01 首次 ship.commit 实测)。
    if "--help" in args or "-h" in args:
        print(__doc__.splitlines()[0].strip("\""))
        print("用法: check_html.py --check | <files...> | --vnu [--all|--strict] <files...> | --safety")
        return 0

    vnu = "--vnu" in args
    strict = "--strict" in args
    check_all = "--check" in args or "--all" in args
    paths = [Path(a) for a in args if not a.startswith("--")]

    if vnu:
        files = sorted(mb.rglob("*.html")) if "--all" in args else [p if p.is_absolute() else root / p for p in paths]
        return run_vnu(files, root, strict, "java")
    if check_all:
        return run_l1l2(collect_files(mb, None), root)
    if paths:
        return run_l1l2(collect_files(mb, [p if p.is_absolute() else root / p for p in paths]), root)
    print("用法: check_html.py --check | <files...> | --vnu [--all|--strict] <files...> | --safety")
    return 2


if __name__ == "__main__":
    sys.exit(main())
