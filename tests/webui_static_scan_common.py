"""`webui_static_scan_common` 支撑: 从 `test_webui_static_skins.py` 拆出的模块级辅助/常量(move-only 搬迁, 未改语义)."""

import json

import os

import re

import shutil

import subprocess

from webui_helpers import (
    STATIC_ROOT,
    _UI_ALL,
    _ui_manifest,
    _ui_aggregate,
    _ui_css_files,
    _ui_css_aggregate,
    _ui_css_effective,
    _app_bundle_files,
    _app_bundle_text,
    _tpl_path,
)


def _assert_tags_balanced(text, label):
    """HTML 标签配平(HTMLParser 视角): 分片切割边界错位(把半个元素切进相邻分片)在聚合上现形

    分片本身因 wrapper 跨片(template v-else / .layout / .hb-wrap)**允许不配平**,
    配平只对「按清单序拼接后的聚合」成立 —— 它必须与拆分前的整页等价。
    void 元素与自闭合不参与; script/style 内容是 CDATA(内部尖括号不参与)。
    """
    from html.parser import HTMLParser

    void = {
        "meta", "link", "img", "input", "br", "hr", "source", "col", "area", "base", "wbr", "embed", "track", "param"
    }

    class _Balance(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=False)
            self.stack, self.bad = [], []

        def handle_starttag(self, tag, attrs):
            if tag not in void:
                self.stack.append((tag, self.getpos()[0]))

        def handle_startendtag(self, tag, attrs):
            pass

        def handle_endtag(self, tag):
            if tag in void:
                return
            if not self.stack:
                self.bad.append(f"多余的 </{tag}> @行{self.getpos()[0]}")
                return
            open_tag, open_line = self.stack.pop()
            if open_tag != tag:
                self.bad.append(f"</{tag}> @行{self.getpos()[0]} 与未闭合的 <{open_tag}> @行{open_line} 交错")

    p = _Balance()
    p.feed(text)
    p.close()
    leftovers = [f"<{t}> @行{l}" for t, l in p.stack]
    problems = p.bad + [f"未闭合的 {x}" for x in leftovers]
    assert not problems, f"{label} 标签不配平(分片切割边界错位?): " + "; ".join(problems[:8])


# CSS 容器型 at-rule: "开块后下一行是嵌套规则"属正常写法, 不参与"漏闭合"判定
# (@starting-style: Chrome 117+, 扁平写法 = 块内包选择器规则, 语义同容器型 —— fx 库入场原语用, 计划 26-10-31-2316 S2)
_CSS_CONTAINER_AT = ("@media", "@supports", "@keyframes", "@container", "@layer", "@scope", "@starting-style")

# 追剧视图的"集成员"两种写法(e.members / ep.members) —— 取 hash 必须经 memberHashesOf 归一
_EP_MEMBERS_RE = re.compile(r"\b(?:ep|e)\.members\b")

# `node -e` 批量校验脚本(不落盘): 逐文件按 **CommonJS 包装**编译 —— 与 `node --check` 同语义, 但只起一个进程。
# WARN: 必须经 `Module.wrap`: 裸 `new vm.Script(src)` 按**经典脚本**解析, 会把顶层 `return`(CommonJS 下合法)
#   判成语法错误 ⇒ 比原判据凭空变严(2026-09-23 实测: 同一批样本里只有该边界项判定不同)。
_NODE_SYNTAX_CHECK = (
    "const fs=require('fs'),vm=require('vm'),M=require('module');let bad=0;"
    "for(const f of process.argv.slice(1)){"
    "try{new vm.Script(M.wrap(fs.readFileSync(f,'utf8')),{filename:f});}"
    "catch(e){bad++;console.error(f+'\\t'+e.message);}}"
    "process.exit(bad?1:0);"
)


def _section_members(text, section):
    """取片段文件 / app.js 里 `methods: {` 或 `computed: {` 块的成员名(4 空格缩进的 `name(` / `name:`)

    块结束判据 = **缩进不深于段起始行**的 `}` 或 `},`(2026-10-20 修, 计划 26-10-20-0024 W4):
    原判据写死 `line in ("  },", "  }")`, 只认 2 空格收尾 —— 对 `window.X = {` 缩进在 IIFE 内
    (2 空格对象 / 4 空格段 / 6 空格成员)的片段, 段的收尾是 4 空格, 判据不触发 ⇒ 扫描一路吃到
    下一个 `methods: {` 并把 "methods" 记成上一个段的**幻影成员**, 于是任意两个这种写法的片段
    互相"重名"(实测: drawer_templates.js 给 ctx_menu_custom.js 报 computed.methods 重名)。
    成员名仍只认 4 空格缩进(本仓库 col-0 对象约定下的成员位置) —— 深缩进片段的成员不在此扫描,
    与修改前一致, 不放宽也不收紧。
    """
    names, in_block, base = [], False, 0
    for line in text.splitlines():
        if not in_block:
            if line.strip() == section + ": {":
                in_block, base = True, len(line) - len(line.lstrip())
            continue
        indent = len(line) - len(line.lstrip())
        if line.strip() in ("},", "}") and indent <= base:
            break
        m = re.match(r"^    (?:async )?([A-Za-z_$][\w$]*)\s*[(:]", line)
        if m:
            names.append(m.group(1))
    return names


def _computed_body(text, name):
    """取 computed 成员 `<name>() { ... }` 的函数体(按缩进配平到同缩进或更浅的 `},`/`}`)

    只做"这段实现里有没有出现某个调用"这类**存在性**判定(见 _scan_filter_facets),
    故不需要真解析: 从定义行开始收集, 遇到缩进不大于定义行的 `}` 即停。
    """
    m = re.search(rf"^\s*{name}\(\)\s*\{{", text, re.M)
    if not m:
        return None
    indent = len(m.group(0)) - len(m.group(0).lstrip())
    out = []
    for line in text[m.end():].splitlines():
        if line.strip() in ("}", "},") and len(line) - len(line.lstrip()) <= indent:
            break
        out.append(line)
    return "\n".join(out)


def _strip_js_comments(text):
    """去掉 JS 的块注释与行注释 —— 供**存在性**守阵使用, 避免被注释骗过

    !这是本项目踩过的坑(memory-bank/testing.md 列偏好守阵那条): 只查"字符串出现了没有",
    注释里正写着那个名字 ⇒ 真被注释掉的代码照样判过。故存在性判定一律先剥注释。
    行注释只认"前面不是冒号"的 `//`(避开 `https://` 这类字面量), 不做完整词法分析 ——
    本函数只服务"某标识符在这段实现里有没有被调用", 不需要精确到字符串内部。
    """
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    out = []
    for line in text.splitlines():
        m = re.search(r"(?<!:)//", line)
        out.append(line[:m.start()] if m else line)
    return "\n".join(out)


# 挂件级类名白名单 —— 只盯这些; 组件层类名(`.ico` / `.row` / `.cell` 等)不进, 否则满屏误报。
# 添加新挂件类时请同步这里。
_PAGE_HOOK_CLASSES = ("hub-page", "ce-page", "layout")

# PERF-01(2026-09-24): 这两类元素**不许**再挂 backdrop-filter —— 它们要么是全屏遮罩, 要么是
# 常驻吸顶/吸底条, 都处在别的遮罩的 backdrop 里; 一旦两块毛玻璃叠在一起, Chromium 每帧都要
# 回读并重复模糊整个视口(星图"点状态栏历史流量卡顿"的实测根因)。
# 注: 抽屉遮罩 `.drawer-mask` 不在此列 —— 它是**当时唯一在用的**遮罩, 底下已无第二块毛玻璃,
# 两套 UI 同款且棱镜侧实测无卡顿; 一并摘掉会单边改动棱镜外观, 超出本次范围(见 scope-guard)。
_PERF_BACKDROP_BANNED = ("modal-mask", "topbar", "status-strip", "statusbar", "ce-actions")

# R2 精修(计划 26-10-31-2316 §06, 2026-11-01): flux 显式档 —— 用户报"浮层半透明, 下层文字透出
# 影响阅读", flux 的常驻大型浮层面(顶栏/状态栏/详情面板/弹窗面板)挂**静态** backdrop-filter
# 真毛玻璃(无过渡; 弹窗遮罩与列表行仍不带)。四类旧禁类对 flux 放开, 但声明数钉死显式预算:
# 多一处少一处都红, 防"顺手再挂一块"重演嵌套模糊(弹窗面板 blur 会叠在顶栏/状态栏 blur 之上,
# 这是**有意接受的小面积嵌套** —— 遮罩级全屏 blur 不回来, 帧率实测背书, 见计划档案 R2 实录)。
# 计数口径 = **逻辑处**(按规则体): `-webkit-backdrop-filter` 是 Safari 前缀别名, 与同体的无前缀
# 声明只计一处 —— 否则加一条兼容声明就把预算顶红, 迫使 agent 去改预算而不是改样式。
# 2026-11-04 全浮层玻璃化(用户报"添加种子/右键菜单等弹窗毛玻璃近乎没有", 显式改预算 + 红绿双验):
# 预算 4 → 16, 新增 12 处 = 下拉(.col-menu/.pop-menu)/右键菜单(.ctx-menu/.ctx-sub)/图表与历史
# 悬停卡(.ce-chart-tip/.hist-tip)/HR 全屏面板(.hr-full-modal)/拖放落点(.add-drop-box)/
# 限速浮层(.speed-pop)/HR 悬停弹窗(.hr-pop/.hp-arrow)/共用层覆盖(.hb-pop 与 :is 组含 .relc-pop)。
# 26-11-02「透正文」的根因是半透明底**无 blur**; 挂上 blur 后半透明即毛玻璃, 不再透可读正文。
# 唯一保留不透明 --bg-pop 的浮层 = .col-ghost(列头拖动虚影, 每帧移动的 fixed 元素挂 blur = 逐帧
# 回读采样, 不玻璃化)。遮罩级全屏 blur 仍任何皮肤不回来。
_FLUX_BACKDROP_BUDGET = 16


def _extract_column_keys(app_js: str, const_name: str):
    """从 app.js 提取列模型数组的 key 清单(缺该数组返回 None —— 列模型被改名/搬走的信号)"""
    m = re.search(r"const %s = \[(.*?)\n\];" % const_name, app_js, re.S)
    if not m:
        return None
    return re.findall(r'key: "(\w+)"', m.group(1))


_STATE_TOKEN_EXPECT = {
    "seeding": "var(--green)",
    "downloading": "var(--blue)",
    "checking": "var(--warn)",
    "moving": "var(--violet)",
    "error": "var(--error)",
    "paused": "var(--paused)",
    "other": "var(--paused)",
}


def _toast_literal_texts(src):
    """产出 (行号, 典型渲染文本): 提示条文案的两个入口都扫。

    - `toast(text, kind, ms, opts)` → 第 1 个实参;
    - `_finishToast(id, kind, text, ms)`(常驻条原位结算成终态, 如「等待中…」→「成功/超时」)
      → 第 3 个实参。只扫 toast 会漏掉一批终态文案(「已导出 N 个 .torrent」「强制汇报成功…」
      都在这里)。

    实现口径: 先用正则定位调用点, 再用 `_args_texts` 按顶层逗号切实参(字符串/模板/嵌套括号
    都在切分里处理)。注释行(以 `//` 或 `*` 开头)里的提及不算调用。
    典型文本 = 字面量原样 + `${...}`/裸表达式折成占位(模拟 err.message / 名称 / 计数);
    首段就是表达式的调用跳过(主标题由运行时拼接, 静态判不了)。
    """
    for m in re.finditer(r"(?<![\w$])(_finishToast|toast)\s*\(", src):
        name = m.group(1)
        line_start = src.rfind("\n", 0, m.start()) + 1
        prefix = src[line_start:m.start()].lstrip()
        if prefix.startswith("//") or prefix.startswith("*"):
            continue  # 注释里的提及, 不是调用
        arg_idx = 2 if name == "_finishToast" else 0
        texts, _end = _args_texts(src, m.end())
        if len(texts) <= arg_idx or texts[arg_idx] is None:
            continue
        yield src[:m.start()].count("\n") + 1, texts[arg_idx]


def _args_texts(src, start):
    """按顶层逗号切开实参, 逐个折成典型文本(非字面量实参 = None); 返回 (列表, 收尾下标)。"""
    texts, i = [], start
    while True:
        text, i = _first_arg_text(src, i)
        texts.append(text)
        if i >= len(src) or src[i] != ",":
            return texts, i
        i += 1


def _skip_string(src, start):
    """跳过一段字符串/模板字面量, 返回闭合引号之后的下标。"""
    quote = src[start]
    i = start + 1
    while i < len(src):
        if src[i] == "\\":
            i += 2
            continue
        if src[i] == quote:
            return i + 1
        if quote == "`" and src.startswith("${", i):
            i = _skip_braces(src, i + 2)
            continue
        i += 1
    return len(src)


def _skip_braces(src, start):
    """从 `${` 的内容起点跳到配对的 `}` 之后(模板里嵌表达式的花括号计数)。"""
    depth, i = 1, start
    while i < len(src):
        if src[i] in "\"'`":
            i = _skip_string(src, i)
            continue
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return len(src)


def _first_arg_text(src, start):
    """取 toast( 的第一个实参: 是字面量/字面量拼接则返回典型文本, 否则返回 (None, 收尾下标)。"""
    parts = []
    literal_seen = False
    head_from_expr = False  # 首段来自 `${head}...` / 三元 / 变量 = 标题由运行时决定, 静态判不了
    i = start
    depth = 0
    while i < len(src):
        ch = src[i]
        if ch in "\"'`":
            end = _skip_string(src, i)
            raw = src[i + 1:end - 1]
            if not parts and raw.startswith("${"):
                head_from_expr = True
            lit = re.sub(r"\$\{[^}]*\}", "示例值x", raw)
            parts.append(lit)
            literal_seen = True
            i = end
            continue
        if ch in "([{":
            depth += 1
            i += 1
            continue
        if ch in ")]}":
            if depth == 0:
                break
            depth -= 1
            i += 1
            continue
        if ch == "," and depth == 0:
            break
        if ch in "+" or ch.isspace():
            i += 1
            continue
        # 裸表达式(三元/变量/调用): 表达式本身折成一个占位; 同层后面的字面量照常拼回去
        if not parts:
            head_from_expr = True
        parts.append("示例值x")
        j, d = i, 0
        while j < len(src):
            c = src[j]
            if c in "\"'`":
                end = _skip_string(src, j)
                lit = re.sub(r"\$\{[^}]*\}", "示例值x", src[j + 1:end - 1])
                parts.append(lit)
                j = end
                continue
            if c in "([{":
                d += 1
            elif c in ")]}":
                if d == 0:
                    break
                d -= 1
            elif c == "," and d == 0:
                break
            j += 1
        i = j if j > i else i + 1  # 保证前进(否则 "-" 之类的单字符会死循环)
    # 首段是表达式(如 `${head}...` / `cond ? ... : ...`)时跳过: 主标题由运行时拼接,
    # 静态无从判定(拿占位当标题会误报)。首段是字面量的才判 —— 这类占绝大多数。
    if not literal_seen or head_from_expr:
        return None, i
    return "".join(parts).strip(), i


def _toast_kinds_in_use():
    """模板图标映射 + JS 调用点里出现的 toast kind 全集(守阵判据, 不含中性 info 的取舍在调用方)

    两个来源缺一不可: 模板图标映射(`{ ok: '#i-check', error: '#i-warn', … }`)决定**渲染**分支,
    JS 调用点决定**谁在用**。只看模板会漏"新加 kind 但模板没给图标"(照样渲染, 只是图标走 info);
    只看 JS 会漏"模板里有却暂时没人用的档"(留着也别删)。
    """
    kinds = set()
    tpl = os.path.join(STATIC_ROOT, "shared", "tpl", "overlays.html")
    if os.path.isfile(tpl):
        text = open(tpl, encoding="utf-8").read()
        m = re.search(r"\{([^}]*)\}\[t\.kind\]", text)
        if m:
            kinds |= set(re.findall(r"(\w+)\s*:", m.group(1)))
    for name in sorted(os.listdir(os.path.join(STATIC_ROOT, "shared"))):
        if not name.endswith(".js"):
            continue
        text = open(os.path.join(STATIC_ROOT, "shared", name), encoding="utf-8").read()
        kinds |= set(re.findall(r"toast\([^;]{0,80}?\"(ok|warn|error|info|busy|timeout)\"", text))
    return kinds


# message surface 语义档期望表(值 = 消费的色令牌名): timeout 与 warn 同取琥珀 ——
# 两者都是「已受理但未落定」, 靠图标区分(clock vs info), 与 TOAST_MS_FLOOR 的停留下限同族。
_MSG_TONE_EXPECT = {"ok": "--green", "warn": "--warn", "error": "--error", "busy": "--accent", "timeout": "--warn"}

# 中性档: info 就是基线本身(中性描边 + accent 图标), 不单列规则 —— 列了反而与"无等级"的语义自相矛盾
_MSG_NEUTRAL_KINDS = ("info", )

# node 单测探针(不落盘): 加载真实 hr_status.js, 对模块级纯函数 hrsCompareRows 跑排序语义电池
# (计划 26-10-02-1936 §3.4: 空值恒末位两方向不反转 / verified_ts·last_seen 0 哨兵 / 档位固定秩 /
#  字符串·数值分型 / 同值稳定性)。无 node 静默跳过(与 _scan_js_syntax_with_node 同口径)。
_NODE_HRS_SORT_PROBE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));
const rows = [
  { tid: 10, name: "kb", uploaded_bytes: 200, ratio: 2.0, need_seed_seconds: 3600,
    done_iso: "2026-09-01T10:00:00", verified_ts: 100, last_seen: 200, lane: "B" },
  { tid: 20, name: "ka", uploaded_bytes: null, ratio: null, need_seed_seconds: null,
    done_iso: null, verified_ts: 0, last_seen: 0, lane: "A" },
  { tid: 30, name: "kc", uploaded_bytes: 300, ratio: 30.0, need_seed_seconds: 60,
    done_iso: "2026-09-02T10:00:00", verified_ts: 300, last_seen: 100, lane: "C" },
  { tid: 40, name: "kd", uploaded_bytes: 300, ratio: 15.0, need_seed_seconds: 60,
    done_iso: null, verified_ts: 200, last_seen: 300, lane: "D" },
];
const seq = (key, dir) => [...rows].sort((a, b) => hrsCompareRows(a, b, key, dir)).map((r) => r.tid);
const checks = [
  ["bytes 降序 null 末位", JSON.stringify(seq("uploaded_bytes", -1)) === "[30,40,10,20]"],
  ["bytes 升序 null 仍末位", JSON.stringify(seq("uploaded_bytes", 1)) === "[10,30,40,20]"],
  ["同值稳定性(两方向 30 在 40 前)", seq("uploaded_bytes", -1).indexOf(30) < seq("uploaded_bytes", -1).indexOf(40)
    && seq("uploaded_bytes", 1).indexOf(30) < seq("uploaded_bytes", 1).indexOf(40)],
  ["verified_ts 0 哨兵降序末位", JSON.stringify(seq("verified_ts", -1)) === "[30,40,10,20]"],
  ["verified_ts 0 哨兵升序仍末位", JSON.stringify(seq("verified_ts", 1)) === "[10,40,30,20]"],
  ["last_seen 两方向空恒末位", JSON.stringify(seq("last_seen", -1)) === "[40,10,30,20]"
    && JSON.stringify(seq("last_seen", 1)) === "[30,10,40,20]"],
  ["档位固定秩降序 D>C>B>A", JSON.stringify(seq("lane", -1)) === "[40,30,10,20]"],
  ["档位固定秩升序 A<B<C<D", JSON.stringify(seq("lane", 1)) === "[20,10,30,40]"],
  ["名称字符串升序", JSON.stringify(seq("name", 1)) === "[20,10,30,40]"],
  ["名称字符串降序", JSON.stringify(seq("name", -1)) === "[40,30,10,20]"],
  ["need_seed_seconds null 两方向末位", JSON.stringify(seq("need_seed_seconds", -1)) === "[10,30,40,20]"
    && JSON.stringify(seq("need_seed_seconds", 1)) === "[30,40,10,20]"],
  ["done_iso 空串两方向末位", JSON.stringify(seq("done_iso", 1)) === "[10,30,20,40]"
    && JSON.stringify(seq("done_iso", -1)) === "[30,10,20,40]"],
];
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""


def _css_rules(text):
    """(选择器列表, 规则体) 序列。先剥注释 —— 注释落在选择器捕获里会污染逐字比较。"""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    out = []
    for mo in re.finditer(r"([^{}]*)\{([^}]*)\}", text):
        sels = [s.strip() for s in mo.group(1).split(",") if s.strip()]
        out.append((sels, mo.group(2)))
    return out


def _css_body(rules, sel, where):
    """按**完整选择器**取规则体(不用子串 —— 子串会被 `... > :first-child` 那条先撞上)。"""
    for sels, body in rules:
        if sel in sels:
            return body
    raise AssertionError(f"{where} 缺规则 `{sel}` —— 底色契约的落点被删或被改名?")


def _css_bg(body):
    """取 background 声明值(空白归一); 缺声明即红。"""
    mo = re.search(r"background:\s*([^;]*);", body)
    assert mo, f"规则体内找不到 background 声明: {body.strip()[:80]}"
    return " ".join(mo.group(1).split())


_RADIUS_RE = re.compile(r"(?<![-\w])border-(?:\w+-)*radius\s*:\s*([^;}]+)")

# console 方角白名单(R1 精修 B1, 26-10-31-2316 §06): 现存值全量盘点后冻结 —— 0(方角)/
# 999px(胶囊)/小值(发丝件/微圆角)/50%(圆点)/var(--radius*)三档(console 令牌 0px, 判据 1 钉)/
# inherit(随父)。flux 意图的 16/10/6 档不在列, 出现即红。
_CONSOLE_RADIUS_ALLOW = {
    "0",
    "999px",
    "inherit",
    "50%",
    "2px",
    "3px",
    "4px",
    "6px",
    "0 2px 2px 0",
    "0 3px 3px 0",
    "var(--radius)",
    "var(--radius-sm)",
    "var(--radius-sm, 4px)",
}
