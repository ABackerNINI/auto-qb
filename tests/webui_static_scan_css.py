"""`webui_static_scan_css` 支撑: 从 `test_webui_static_skins.py` 拆出的模块级辅助/常量(move-only 搬迁, 未改语义)."""

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

from webui_static_scan_common import (
    _CSS_CONTAINER_AT,
    _FLUX_BACKDROP_BUDGET,
    _PERF_BACKDROP_BANNED,
    _STATE_TOKEN_EXPECT,
    _extract_column_keys,
)


def _scan_css_blocks(path, rel, problems):
    """CSS 规则块守阵: 顶层规则开了块却没闭合, 而下一非空行又开了新规则 -> 漏写 `; }`

    (2026-09-17 实测: prism/css/views.css 曾有一条 `.ce-subcard .ce-field { … padding: 7px 0` 漏了
    `; }`, 浏览器把其后约 200 条规则整段当作"未结束的声明块"丢弃 —— 棱镜大半样式静默消失而
    pytest 全绿。注意**全文件花括号计数是配平的**(别处有多余 `}`), 只数括号查不出来。
    该规则本身已随经典设置页的死代码清理删除, 此处只作判据来源留档。)
    """
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    depth = 0
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        opens, closes = line.count("{"), line.count("}")
        if depth == 0 and opens > closes and not stripped.startswith(_CSS_CONTAINER_AT):
            nxt = next((l.strip() for l in lines[i:] if l.strip()), "")
            if "{" in nxt:  # 本块还没闭合, 下一行又开了新规则 -> 语法已坏
                problems.append(f"{rel}:{i} 规则块未闭合(下一非空行又开了新规则)")
        depth += opens - closes
        if depth < 0:
            problems.append(f"{rel}:{i} 多余的 `}}`")
            depth = 0
    if depth != 0:
        problems.append(f"{rel} 花括号未配平(差 {depth})")


def _scan_css_comments(path, rel, problems):
    """CSS 注释提前终止守阵: 注释体内的 `*/` 会把注释砍断, 尾巴落成代码态的孤立垃圾 ——
    浏览器按错误恢复丢弃到下一个 `}` 为止, **紧跟的那条规则整条静默消失**(无任何报错)。

    (2026-09-28 实测: console/css/components.css 进度条注释写了 `(s-*/member-row 族)`,
    `s-*` 后的 `*/` 提前闭合注释, 紧随其后的 `.m-progress { display: flex; … }` 被整条吞掉
    —— 三处表格(辅种/种子/追剧明细)进度条只剩百分比没有条。判据 = 浏览器同款注释语义
    (字符串感知)扫一遍: 正常文件的所有 `*/` 都应消费在注释态里, 代码态出现孤立 `*/` 即中招。)
    """
    with open(path, encoding="utf-8") as f:
        text = f.read()
    i, n = 0, len(text)
    in_comment = False
    str_ch = None
    while i < n:
        c = text[i]
        if in_comment:
            if c == "*" and i + 1 < n and text[i + 1] == "/":
                in_comment = False
                i += 2
                continue
            i += 1
            continue
        if str_ch:
            if c == "\\":
                i += 2
                continue
            if c == str_ch:
                str_ch = None
            i += 1
            continue
        if c in "\"'":
            str_ch = c
            i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            in_comment = True
            i += 2
            continue
        if c == "*" and i + 1 < n and text[i + 1] == "/":
            line = text.count("\n", 0, i) + 1
            problems.append(f"{rel}:{line} 注释被体内 `*/` 提前终止(其后规则被浏览器整条丢弃)")
            i += 2
            continue
        i += 1


def _scan_backdrop_filter(problems):
    """毛玻璃守阵: 全屏遮罩 / 吸顶吸底条不得带 backdrop-filter, 三旧皮肤声明数对齐, flux 显式档

    现象(2026-09-24, 用户报"星图卡顿, 点状态栏历史流量尤其明显; 棱镜无此问题"):
    星图 atlas/style.css 一度挂了 5 处 backdrop-filter —— 顶栏 blur(12px) / 状态分布条 blur(10px) /
    弹层遮罩 blur(3px) / 配置页吸底条 blur(10px) / 抽屉遮罩 blur(2px); 棱镜侧只有抽屉遮罩一处。
    点开"历史流量"时, .modal-mask(全屏 fixed + blur)的 backdrop 里正压着顶栏与状态分布条这两块
    毛玻璃 —— **嵌套毛玻璃**迫使每帧回读 + 重复模糊整个视口, 而弹层内的 hist-draw 描边动画
    还在主线程逐帧重绘, 两者叠成肉眼可见的卡顿。棱镜 .modal-mask 从来没加过 backdrop-filter,
    所以无此症状。

    两层断言(缺一不可):
    1.**位置**: 上述六类元素一律不许出现 backdrop-filter(不论哪套 UI、哪份 CSS) --
      flux 例外四类(topbar/status-strip/statusbar/ce-actions)按 R2 显式档放开, modal-mask 对
      flux 也仍禁(遮罩级全屏 blur 是 PERF-01 根因本体, 任何皮肤不回来);
    2.**数量**: 三旧皮肤(atlas/prism/console)逻辑处数必须相等且为 0 —— 防"只在某一侧加回来"
      这类单边改动(shared/console_hub.css 是共用层, 各边同担, 不计入各自计数); flux 走显式档,
      逻辑处数必须恰等于 _FLUX_BACKDROP_BUDGET(加/摘毛玻璃 = 显式改预算 + 红绿双验)。
      计数按规则体归并: `-webkit-backdrop-filter` 前缀别名与同一体的无前缀声明只算一处。
    扫描前先剥 `/* ... */`, 否则本文件里解释这段历史的注释会被当成真实声明(实测会误报)。
    """
    counts = {ui: 0 for ui in _UI_ALL}
    for dirpath, _dirs, files in os.walk(STATIC_ROOT):
        for name in sorted(files):
            if not name.endswith(".css") or "/vendor/" in f"/{dirpath}/{name}":
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, STATIC_ROOT).replace(os.sep, "/")
            text = re.sub(r"/\*.*?\*/", "", open(path, encoding="utf-8").read(), flags=re.S)
            sel = ""
            counted = False  # 当前规则体已计过一条逻辑毛玻璃声明(前缀别名不重复计数)
            for line in text.splitlines():
                if "{" in line:
                    sel = (sel + " " + line.split("{", 1)[0]).strip()
                    counted = False
                if re.search(r"(?:-webkit-)?backdrop-filter\s*:", line):
                    if not counted:
                        for ui in _UI_ALL:
                            if rel.startswith(ui + "/"):
                                counts[ui] += 1
                        counted = True
                    for bad in _PERF_BACKDROP_BANNED:
                        if re.search(r"\.%s\b" % re.escape(bad), sel):
                            if rel.startswith("flux/") and bad != "modal-mask":
                                continue  # R2 显式档: flux 四类常驻浮层面明示放开(静态 blur), 遮罩仍禁
                            problems.append(
                                f"{rel} `{sel or '(未识别选择器)'}` 上出现 backdrop-filter —— "
                                f"{bad} 是全屏遮罩或常驻吸顶/吸底条, 加毛玻璃会与弹层遮罩叠成嵌套模糊"
                                f"(每帧回读 + 重复模糊整个视口; 星图 2026-09-24 卡顿根因, 见 PERF-01)"
                            )
                if "}" in line:
                    sel = ""
    non_flux = {ui: n for ui, n in counts.items() if ui != "flux"}
    if len(set(non_flux.values())) != 1:
        problems.append(
            f"三旧皮肤的 backdrop-filter 声明数不对齐: "
            f"{' / '.join(f'{ui} {n} 处' for ui, n in non_flux.items())} —— "
            f"单边加毛玻璃会重新引入嵌套模糊卡顿(遮罩类从不带 backdrop-filter, 见 PERF-01)"
        )
    if counts["flux"] != _FLUX_BACKDROP_BUDGET:
        problems.append(
            f"flux 的 backdrop-filter 逻辑处数 = {counts['flux']}(显式档恰 {_FLUX_BACKDROP_BUDGET} 处: "
            f"顶栏/状态栏/详情面板/弹窗面板各一) —— R2 精修 V2 口径: flux 加/摘毛玻璃必须显式改本预算"
            f"并红绿双验, 防『顺手再挂一块』重演嵌套模糊(遮罩级全屏 blur 任何皮肤不回来, 见 PERF-01)"
        )


def _scan_column_cells_paired(problems):
    """列模型每个列 key 必须在对应行模型渲染器里有值单元格分支(辅种扩列 2026-09-28 守阵; P2/P3 改扫渲染器)

    列模型(TABLE_COLUMNS)是表头/grid 模板/列选择器的单一来源 —— 但**值单元格**是渲染器里的
    v-if/v-else-if 分支, 漏写某列的分支时没有任何报错: 表头照常渲染、列选择器照常可勾,
    值格却永远空白, 且无法从"pytest 全绿"察觉。

    !值单元格自计划 26-10-11-1722 P2/P3 起**不再是页面模板里的内联副本**:
      · group / torrent / show-ep 三类收敛为**每行模型单份**渲染器
        (<aq-group-cells> / <aq-torrent-cells> / <aq-show-cells> / <aq-ep-cells>,
         模板在 shared/tpl/xtpl-cells.html);
      · 明细成员单元格(member)在 P2 已收敛为 <aq-member-cells>(模板在 shared/tpl/xtpl.html)。
    故改为扫渲染器所在分片, 并额外钉住"注册为全局组件 + 页面调用点都走它"—— 漏一处即退回内联副本
    (静默回潮)。"删一个渲染器分支必须报红"的语义不变, 只是红点从页面模板挪到渲染器。
    另钉住默认隐藏策略单点(2026-10-12 issue 26-10-12-1911 收口): loadColState 必须消费
    DEFAULT_HIDDEN_KEYS(漏消费 = 默认隐藏列全部默认可见), 且列定义不得再写 hide:true
    (回潮即三表口径再漂移)。
    """
    app_js = open(os.path.join(STATIC_ROOT, "shared", "app.js"), encoding="utf-8").read()
    plans = (
        ("GROUP_COLUMNS", "tpl/xtpl-cells.html"),  # 单份渲染器 <aq-group-cells>(P3)
        ("DETAIL_COLUMNS", "tpl/xtpl.html"),  # 单份渲染器 <aq-member-cells>(P2)
        ("TORRENT_COLUMNS", "tpl/xtpl-cells.html"),  # 单份渲染器 <aq-torrent-cells>(P3)
        ("SHOW_COLUMNS", "tpl/xtpl-cells.html"),  # 单份渲染器 <aq-show-cells>/<aq-ep-cells>(P3)
    )
    for const, tpl in plans:
        keys = _extract_column_keys(app_js, const)
        if keys is None:
            problems.append(f"app.js 缺少列模型 {const}(列模型单一来源被改名/搬走?)")
            continue
        text = open(os.path.join(STATIC_ROOT, "shared", tpl), encoding="utf-8").read()
        for k in keys:
            if f"col.key === '{k}'" not in text:
                problems.append(f"{const} 列 {k} 在 shared/{tpl} 没有值单元格分支(col.key === '{k}') —— 表头在、值永远空白")
    # 行模型渲染器的接线单点(注册 + 页面调用点): 漏注册 = 该页整块渲染不出来; 漏调用 = 退回内联副本
    renderers = (
        ("aq-member-cells", "AQ_MEMBER_CELLS_COMPONENT", ("tpl/groups.html", "tpl/shows.html")),
        ("aq-group-cells", "AQ_GROUP_CELLS_COMPONENT", ("tpl/groups.html", )),
        ("aq-torrent-cells", "AQ_TORRENT_CELLS_COMPONENT", ("tpl/torrents.html", )),
        ("aq-show-cells", "AQ_SHOW_CELLS_COMPONENT", ("tpl/shows.html", )),
        ("aq-ep-cells", "AQ_EP_CELLS_COMPONENT", ("tpl/shows.html", )),
    )
    for name, glob, tpls in renderers:
        if not re.search(r'app\.component\(\s*"%s"\s*,\s*window\.%s\s*\)' % (name, glob), app_js):
            problems.append(f"app.js 未注册 {name}(window.{glob}) —— 行模型渲染器没接线, 该页值格全空")
        for tpl in tpls:
            text = open(os.path.join(STATIC_ROOT, "shared", tpl), encoding="utf-8").read()
            if f"<{name}" not in text:
                problems.append(f"shared/{tpl} 未使用 <{name}> —— 行模型渲染器收敛回潮"
                                "(该页退回内联副本, 改一处漏一处)")
    if "DEFAULT_HIDDEN_KEYS" not in app_js or "DEFAULT_HIDDEN_KEYS.has(c.key)" not in app_js:
        problems.append("app.js loadColState 未消费默认隐藏单点 DEFAULT_HIDDEN_KEYS(默认隐藏列全部可见)")
    if "hide: true" in app_js:
        problems.append("app.js 列定义又见 hide:true —— 默认隐藏策略只应写在 DEFAULT_HIDDEN_KEYS 单点(issue 26-10-12-1911)")


def _scan_progress_val_parity(problems):
    """进度条数值盒守阵: 三套皮肤的 `.m-progress .val` 都必须恰 1 条且带 min-width 定宽(2026-09-28)

    现象(用户报"种子页进度条长度不一致, 似乎受后面的进度文本长度影响"): `.m-progress` 是
    flex 行, `.bar { flex: 1 1 auto }` 吃剩余空间, `.val` 只占自身文本宽 —— 「100.0%」比
    「5.2%」宽, 同一列各行条的起点/长度随百分比文本宽度逐行漂移。处置 = 数值盒
    `min-width: 4em`(容纳最宽的「100.0%」, 三套皮肤字号 11.5-12px 下实测文本 ≈3.5em 以内)
    + `text-align: right`, 条长即与文本解耦; 本守阵防"只在某一侧加 / 新皮肤漏带"。
    """
    hits = {ui: 0 for ui in _UI_ALL}
    for dirpath, _dirs, files in os.walk(STATIC_ROOT):
        for name in sorted(files):
            if not name.endswith(".css") or "/vendor/" in f"/{dirpath}/{name}":
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, STATIC_ROOT).replace(os.sep, "/")
            ui = next((u for u in _UI_ALL if rel.startswith(u + "/")), None)
            if ui is None:
                continue
            text = re.sub(r"/\*.*?\*/", "", open(path, encoding="utf-8").read(), flags=re.S)
            lines = text.splitlines()
            for idx, line in enumerate(lines):
                if not re.match(r"^\s*\.m-progress \.val\s*\{", line):
                    continue
                hits[ui] += 1
                body = line.split("{", 1)[1]
                j = idx
                while "}" not in body and j + 1 < len(lines):
                    j += 1
                    body += lines[j]
                if not re.search(r"min-width\s*:", body):
                    problems.append(f"{rel} `.m-progress .val` 缺 min-width 定宽 —— 条吃剩余空间, "
                                    "数值盒不定宽时条长随百分比文本宽度逐行漂移")
    for ui, n in hits.items():
        if n != 1:
            problems.append(f"{ui} 皮肤的 `.m-progress .val` 基础规则数 = {n}(应恰 1 条且带 min-width 定宽)")


def _scan_state_color_tokens(problems):
    """状态色令牌守阵(2026-11-02): 每皮肤的 7 个 kind 都必须有 --st/--st-soft, 进度条必须读 --st

    背景: 进度条填充原先各皮肤写死(atlas 蓝渐变 / console+flux 绿 LED / prism --accent), 与
    种子状态无关 —— 星图/棱镜下"做种"的条是蓝的、控制台/流影下"下载"的条是绿的, 颜色把状态
    读反; 且 downloading/checking/moving 三支同 --blue, 校验中与下载中肉眼分不出。
    处置 = 行元素上声明 --st/--st-soft(7 kind), 图例/芯片/行文字/进度条统一消费变量。

    钉四件事(缺一条都是静默故障):
    ① 每个 kind 都要有 --st 声明, 且取值 = 期望表(防漏一个状态 → 回落写死色);
    ② --st-soft 同条声明(芯片底用); ③进度条 `.bar > i` 每皮肤恰 1 条且体内含 var(--st;
    ④ 值漂移即红(checking 被人改回 --blue → 校验中又和下载中同色, 用户报障原样复发)。
    """
    found = {ui: {} for ui in _UI_ALL}
    bar = {ui: [] for ui in _UI_ALL}
    for dirpath, _dirs, files in os.walk(STATIC_ROOT):
        for name in sorted(files):
            if not name.endswith(".css") or "/vendor/" in f"/{dirpath}/{name}":
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, STATIC_ROOT).replace(os.sep, "/")
            ui = next((u for u in _UI_ALL if rel.startswith(u + "/")), None)
            if ui is None:
                continue
            text = re.sub(r"/\*.*?\*/", "", open(path, encoding="utf-8").read(), flags=re.S)
            for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", text):
                if "--st" in body:
                    m = re.search(r"--st\s*:\s*([^;]+);", body)
                    if m:
                        val = m.group(1).strip()
                        soft = "--st-soft" in body
                        for kind in re.findall(r"\.k-([a-z]+)", sel):
                            if kind in _STATE_TOKEN_EXPECT:
                                found[ui].setdefault(kind, set()).add((val, soft))
                if re.search(r"\.m-progress\s+\.bar\s*>\s*i", sel) and "background" in body:
                    bar[ui].append((rel, body))
    for ui in _UI_ALL:
        for kind, want in _STATE_TOKEN_EXPECT.items():
            vals = found[ui].get(kind)
            if not vals:
                problems.append(f"{ui} 皮肤缺状态色令牌 `.k-{kind}` 的 --st 声明"
                                " —— 该状态的前景色与进度条会回落写死色")
                continue
            for val, soft in sorted(vals):
                if val != want:
                    problems.append(f"{ui} 皮肤 `.k-{kind}` 的 --st = {val}(应为 {want})"
                                    " —— 校验中/下载中同色会复发")
                if not soft:
                    problems.append(f"{ui} 皮肤 `.k-{kind}` 缺 --st-soft 同条声明(芯片底会回落写死色)")
        if len(bar[ui]) != 1:
            problems.append(f"{ui} 皮肤的 `.m-progress .bar > i` 规则数 = {len(bar[ui])}(应恰 1 条)")
        for rel, body in bar[ui]:
            if "var(--st" not in body:
                problems.append(f"{rel} 进度条填充未取状态色 var(--st) —— 各状态一条色, 读不出种子状态")


def _scan_flux_modal_frost(problems):
    """flux 弹窗毛玻璃与浮层不透明底对照守阵(2026-11-03 回归, 用户报「flux 弹窗毛玻璃弄丢了」)

    现象与根因: `backdrop-filter` 声明从未被删(仍在 `.modal` 上), 但 26-11-02 的消息面统一把
    弹窗底从 `--bg-card`(82%) 换成 `--bg-elev`(92%) —— 只剩 8% 透视, blur 形同不存在, 肉眼
    读成"毛玻璃被上一次透明修复弄丢了"。故本守阵**同时钉两侧**, 只钉其一都会让修复来回翻烧饼:
    ① 弹窗侧: `.modal` 必须保留无前缀 + `-webkit-`(Safari < 18)两份 blur 声明, 且底必须是
       半透明角色面(`--msg-base`), 不允许再回到 `--bg-elev` 近不透明底;
    ② 透明修复侧(26-11-02 R7): flux `--bg-pop` 必须仍是不透明色, 且八类**不挂 blur** 的浮层
       (列选择器/筛选器/右键菜单/次级菜单/限速浮层/HR 悬停卡/拖放落点/HR 全屏面板)仍消费它 ——
       把毛玻璃找回来只许动弹窗底, 不许把这批浮层重新调透明(用户报障原症状: 下层正文透出);
    ③ 提示条不得被 `--msg-base` 波及: `--msg-base` 只许在 `.modal-mask` 作用域声明(挂 :root
       会让无 blur 的 `.toast` 一起变透明, 即透明修复倒退), 且 --bg-card 的 alpha 必须低于
       --bg-elev, 保证 blur 有可见透视。
    WARN: 只钉 flux —— 三旧皮肤没有毛玻璃(见 _scan_backdrop_filter 恒 0), 不随本守阵放开。
    """
    flux_dir = os.path.join(STATIC_ROOT, "flux")
    rules = {}  # 选择器 -> [(rel, body)]; 逗号分组已拆成单个选择器
    rule_bodies = []  # (rel, body) 每条规则一份(未拆逗号) —— 声明单点计数必须按规则, 否则共享规则会被计两次
    style_path = os.path.join(flux_dir, "style.css")
    for dirpath, _dirs, files in os.walk(flux_dir):
        for name in sorted(files):
            if not name.endswith(".css"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, name), STATIC_ROOT).replace(os.sep, "/")
            text = re.sub(r"/\*.*?\*/", "", open(os.path.join(dirpath, name), encoding="utf-8").read(), flags=re.S)
            for sel_block, body in re.findall(r"([^{}]+)\{([^{}]*)\}", text):
                rule_bodies.append((rel, body))
                for sel in (s.strip() for s in sel_block.split(",")):
                    if sel:
                        rules.setdefault(sel, []).append((rel, body))

    # ① 弹窗本体: 两份 blur + 半透明角色底
    modal = rules.get(".modal", [])
    if not modal:
        problems.append("flux 缺 `.modal` 规则 —— 弹窗基线无处落(毛玻璃/描边/材质全失效)")
    else:
        rel, body = modal[0][0], "\n".join(b for _r, b in modal)
        for token, why in (
            ("backdrop-filter: blur(", "无前缀毛玻璃(Chrome/Edge/Firefox 主链路)"),
            ("-webkit-backdrop-filter: blur(", "Safari < 18 的前缀别名"),
        ):
            if token not in body:
                problems.append(f"{rel} `.modal` 缺 {token} —— {why}丢失; 弹窗是 R2 显式档最后一处毛玻璃,"
                                "删掉等于用户报的「弹窗毛玻璃弄丢了」原症状")
        if "var(--msg-surface" not in body:
            problems.append(f"{rel} `.modal` 底未消费 --msg-surface —— 消息面材质与提示条分家")

    # ② 角色底单点: --msg-surface 恰一处, 且用 --msg-base 分流(提示条近不透明 / 弹窗半透明)
    surface_decls = [(rel, body) for rel, body in rule_bodies if re.search(r"--msg-surface\s*:", body)]
    if len(surface_decls) != 1:
        problems.append(f"flux 的 --msg-surface 声明数 = {len(surface_decls)} —— 消息面供给面必须恰一处单点"
                        "(提示条/弹窗各写一份渐变表达式就会漂移)")
    elif "var(--msg-base" not in surface_decls[0][1]:
        problems.append(
            f"{surface_decls[0][0]} 的 --msg-surface 未走 --msg-base 角色底 —— 弹窗与无 blur 的"
            "提示条被迫共用一个 alpha: 要么弹窗 blur 被不透明底压成不可见, 要么提示条重新透出正文"
        )
    base_decls = [
        (rel, sel, body) for sel, bodies in rules.items() for rel, body in bodies if re.search(r"--msg-base\s*:", body)
    ]
    mask_ok = any(
        sel == ".modal-mask" and re.search(r"--msg-base\s*:\s*var\(--bg-card\)", body) for _r, sel, body in base_decls
    )
    if not mask_ok:
        problems.append(
            "flux 的 `.modal-mask` 未声明 `--msg-base: var(--bg-card)` —— 弹窗底退回 92% 不透明,"
            "blur 只剩 8% 透视, 毛玻璃名存实亡(2026-11-03 回归根因)"
        )

    # ③ 提示条不得被半透明角色底波及(无 blur 的小条透出正文 = 透明修复倒退)
    for rel, sel, _body in base_decls:
        if sel != ".modal-mask":
            problems.append(
                f"{rel} `{sel}` 声明了 --msg-base —— 只许在 `.modal-mask` 作用域分流; 挂 :root/.toast"
                "会让无 blur 的提示条一起变透明(下层正文透出, 用户报障原症状)"
            )

    # ④ 透明修复侧: --bg-pop 不透明 + 八类无 blur 浮层仍消费它
    style = open(style_path, encoding="utf-8").read() if os.path.isfile(style_path) else ""
    m = re.search(r"--bg-pop\s*:\s*([^;]+);", style)
    if not m:
        problems.append("flux/style.css 缺 --bg-pop —— 无 blur 浮层的不透明底单点被删")
    else:
        val = m.group(1).strip()
        if any(t in val for t in ("rgba(", "rgb(", "hsla(", "transparent")):
            problems.append(f"flux `--bg-pop` = {val} —— 必须是不透明色; 无 blur 浮层用半透明底会把下层正文"
                            "透出来(26-11-02 透明修复倒退)")
    for sel in (
        ".col-menu", ".pop-menu", ".ctx-menu", ".ctx-sub", ".speed-pop", ".hr-pop", ".add-drop-box", ".hr-full-modal"
    ):
        bodies = rules.get(sel)
        if not bodies:
            problems.append(f"flux 缺 `{sel}` 规则 —— 无 blur 浮层的不透明底无处落")
        elif not any("var(--bg-pop" in body for _r, body in bodies):
            problems.append(f"flux `{sel}` 未消费 var(--bg-pop) —— 无 blur 浮层重新变半透明会把下层正文透出"
                            "(26-11-02 透明修复倒退)")

    # ⑤ blur 要有可见透视: --bg-card alpha 必须低于 --bg-elev 且明显低于 1
    def _alpha(name):
        mm = re.search(rf"{re.escape(name)}\s*:\s*rgba\([^)]*,\s*([0-9.]+)\s*\)", style)
        return float(mm.group(1)) if mm else None

    a_card, a_elev = _alpha("--bg-card"), _alpha("--bg-elev")
    if a_card is None or a_elev is None:
        problems.append("flux/style.css 的 --bg-card/--bg-elev 不是 rgba 令牌 —— 弹窗底的透视度无从判定")
    elif a_card >= a_elev or a_card >= .95:
        problems.append(
            f"flux --bg-card alpha = {a_card}(--bg-elev = {a_elev}) —— 弹窗底的透视度不足,"
            "backdrop blur 会被不透明底压成不可见(毛玻璃形同虚设)"
        )


