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
            f"顶栏/状态栏/详情面板/弹窗面板 + 2026-11-04 全浮层玻璃化的 12 处菜单/浮层族) —— "
            f"flux 加/摘毛玻璃必须显式改本预算并红绿双验, 防『顺手再挂一块』重演嵌套模糊"
            f"(遮罩级全屏 blur 任何皮肤不回来, 见 PERF-01)"
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


def _scan_ctx_sub_width(problems):
    """右键菜单次级子面板宽度守阵: 四皮肤 `.ctx-sub` min-width 互证同值 260px + menu.js 首帧估宽算术绑定(2026-11-13)

    五处数字耦合(四皮肤 components.css 的 min-width 各一份 + menu.js::_subOverflowsRight 首帧估宽)此前
    零守阵, 单边改动即静默复发两种故障:
    - 某皮肤 min-width 回退(260 -> 190): 该皮肤子菜单 label+键帽放不下折行(260 = 最长项
      「开启自动种子管理」104px + 键帽「Shift + T」约 75px, 单行实需约 246 取整留余);
    - 估宽与 min-width 脱钩: _subOverflowsRight 按估宽先判子面板翻不翻, 估宽 < min-width 时首帧按
      窄面板判向, 实测复核(_subFitViewport)前面板已探出视口右缘(用户报"二级菜单部分出现在屏幕外")。
    钉两件事(缺一即红):
    1. 四皮肤 `<ui>/css/components.css` 基础 `.ctx-sub` 规则各恰 1 条, 体内 min-width 四值互证同值
       且 == 260px(单皮肤回退 = 四皮肤静默分叉, 该皮肤折行);
    2. `_subOverflowsRight` 的 probeRight 第二参 == min-width 260 + 内边距 12(=272; JS 写字面量 272
       或表达式 260 + 12 均认) —— 与 CSS 侧算术绑定, 改宽度漏同步 JS(或反之)即红。
    """
    want, pad = 260, 12
    vals = {}
    for ui in _UI_ALL:
        path = os.path.join(STATIC_ROOT, ui, "css", "components.css")
        rel = f"{ui}/css/components.css"
        if not os.path.isfile(path):
            problems.append(f"{rel} 不存在 —— `.ctx-sub` min-width 守阵无处落")
            continue
        text = re.sub(r"/\*.*?\*/", "", open(path, encoding="utf-8").read(), flags=re.S)
        rules = re.findall(r"(?m)^\.ctx-sub\s*\{([^{}]*)\}", text)
        if len(rules) != 1:
            problems.append(f"{rel} 基础 `.ctx-sub` 规则数 = {len(rules)}(应恰 1 条) —— 规则被改名/拆并, 宽度守阵无处落")
            continue
        m = re.search(r"min-width\s*:\s*([0-9.]+)px", rules[0])
        if not m:
            problems.append(f"{rel} `.ctx-sub` 缺 min-width 定宽 —— label+键帽宽度失去下限, 子菜单项随文本折行")
            continue
        vals[ui] = float(m.group(1))
    if len(set(vals.values())) > 1:
        problems.append(
            "四皮肤 `.ctx-sub` min-width 不齐: " + ", ".join(f"{u} {v:g}px" for u, v in sorted(vals.items())) +
            " —— 单皮肤回退该皮肤子菜单 label+键帽折行(四皮肤同值, 改宽度四处 components.css 同步)"
        )
    drifted = sorted(u for u, v in vals.items() if v != want)
    if drifted:
        problems.append(
            f"{'+'.join(drifted)} 皮肤 `.ctx-sub` min-width = {vals[drifted[0]]:g}px(应 {want}px) —— "
            "260 = 最长项「开启自动种子管理」+ 键帽「Shift + T」单行实需约 246 取整留余, 回退即折行复发"
        )
    menu_path = os.path.join(STATIC_ROOT, "shared", "menu.js")
    menu = open(menu_path, encoding="utf-8").read()
    m = re.search(r"(?m)^\s*_subOverflowsRight\s*\(\s*anchor\s*\)\s*\{", menu)
    if not m:
        problems.append("shared/menu.js 缺 `_subOverflowsRight(anchor)` 方法定义 —— 子面板首帧方向估宽无处落")
        return
    end = menu.find("_subFitViewport", m.end())
    if end == -1:
        problems.append("shared/menu.js `_subOverflowsRight` 之后找不到 `_subFitViewport` —— 方法结构漂移, 估宽守阵不再可靠")
        return
    body = re.sub(r"/\*.*?\*/", "", menu[m.end():end], flags=re.S)
    probe = re.search(r"probeRight\s*\(([^{}]*)\)", body)
    if not probe:
        problems.append("shared/menu.js `_subOverflowsRight` 缺 probeRight 估宽调用 —— 首帧方向判据丢失")
        return
    args = [a.strip() for a in probe.group(1).split(",")]
    if len(args) < 2:
        problems.append(f"shared/menu.js `_subOverflowsRight` probeRight 参数不足({probe.group(1).strip()}) —— 估宽实参无从判定")
        return
    est = args[1]
    if est != str(want + pad) and not re.fullmatch(rf"{want}\s*\+\s*{pad}", est):
        problems.append(
            f"shared/menu.js `_subOverflowsRight` 首帧估宽 = {est}(应 {want + pad} = min-width {want} + 内边距 {pad}, "
            f"写字面量 {want + pad} 或表达式 {want} + {pad} 均可) —— 估宽与 min-width 脱钩时首帧按窄面板判向, "
            "子面板实测复核前已探出视口右缘(改 min-width 四处 components.css + 本处同步)"
        )


def _scan_ctx_kbd_slot(problems):
    """W4 恒渲染固定预留键位列守阵(计划 26-11-14-0041 S3): 四皮肤同值 + 钉值 + 共享结构单点

    恒渲染键位槽(ctx-menus.html 一级/次级 .ctx-kbd-slot)把「键位列几何」从键帽文本宽度解耦:
    无论该项有无键位, 每行都占同一固定列宽(min-width), 显影(按住反引号)只切键帽
    opacity/visibility, 文字位置永不位移(I3); 无键位项槽内留白(不渲染 kbd)。数字是外观定案
    B 档(槽宽 88 / 槽距 0, 2026-11-14 用户拍板; 子面板回 260 / 菜单 259), 落皮肤专属布局层
    四皮肤同值, 守阵钉住防止单皮肤静默回退。
    钉四件事(缺一即红):
    1. 四皮肤 components.css 基础 `.ctx-item .ctx-kbd-slot` 规则各恰 1 条, 体内 min-width
       与 margin-left 四值互证同值且 == 88 / 0(0 允许无单位写法; 单皮肤回退 = 该皮肤各行
       label 右缘不对齐);
    2. 四皮肤 `.ctx-item` 基础规则 gap 四值互证 == 9px(W4 五处连锁之一, 与 .ctx-sub 260 /
       menu.js 272 / _scan_ctx_sub_width want,pad 同口径);
    3. 共享 console_hub_panels.css 有 `.ctx-item .ctx-kbd-slot { flex: none; text-align: right; }`
       结构单点(四皮肤 index.html 全 link => 同构), 且共享侧不带 min-width/margin-left
       (外观数字只在皮肤专属层, 共享结构侧不分裂第二份宽度口径);
    4. 前后端正则一致: 守阵用同一条 `\\.ctx-item \\.ctx-kbd-slot\\s*\\{...\\}` 解析四皮肤 CSS
       与共享 CSS(同一份前端产物), 规则写法(单行块, 允许接在既有规则行尾以守住 700 行体量
       上限)与正则同款 —— 前端漏写/拆块即红, 不会静默漏检(与 _scan_ctx_sub_width 解析
       .ctx-sub 同款口径)。
    """
    want_min, want_margin, want_gap = 88, 0, 9
    slot_re = r"\.ctx-item \.ctx-kbd-slot\s*\{([^{}]*)\}"
    item_re = r"(?m)^\.ctx-item\s*\{([^{}]*)\}"
    vals_min, vals_margin, vals_gap = {}, {}, {}
    for ui in _UI_ALL:
        path = os.path.join(STATIC_ROOT, ui, "css", "components.css")
        rel = f"{ui}/css/components.css"
        if not os.path.isfile(path):
            problems.append(f"{rel} 不存在 —— 恒渲染键位槽守阵无处落")
            continue
        text = re.sub(r"/\*.*?\*/", "", open(path, encoding="utf-8").read(), flags=re.S)
        slots = re.findall(slot_re, text)
        if len(slots) != 1:
            problems.append(f"{rel} `.ctx-item .ctx-kbd-slot` 规则数 = {len(slots)}(应恰 1 条) —— 恒渲染键位槽宽度守阵无处落")
            continue
        m = re.search(r"min-width\s*:\s*([0-9.]+)px", slots[0])
        ml = re.search(r"margin-left\s*:\s*([0-9.]+)(?:px)?", slots[0])
        if not m or not ml:
            problems.append(f"{rel} `.ctx-item .ctx-kbd-slot` 缺 min-width/margin-left —— 键位列不固定或间距丢失")
            continue
        vals_min[ui], vals_margin[ui] = float(m.group(1)), float(ml.group(1))
        items = re.findall(item_re, text)
        if len(items) != 1:
            problems.append(f"{rel} 基础 `.ctx-item` 规则数 = {len(items)}(应恰 1 条) —— gap 连锁守阵无处落")
            continue
        g = re.search(r"gap\s*:\s*([0-9.]+)px", items[0])
        if not g:
            problems.append(f"{rel} `.ctx-item` 缺 gap —— W4 五处连锁之一失锚")
            continue
        vals_gap[ui] = float(g.group(1))
    for label, vals, want in (
        ("min-width", vals_min, want_min), ("margin-left", vals_margin, want_margin), ("gap", vals_gap, want_gap)
    ):
        if len(vals) < len(_UI_ALL):
            continue  # 缺口已在上面逐皮肤报出
        if len(set(vals.values())) > 1:
            problems.append(
                f"四皮肤 {label} 不齐: " + ", ".join(f"{u} {v:g}" for u, v in sorted(vals.items())) +
                " —— 单皮肤回退该皮肤键位列不对齐(W4 四皮肤同步, 改数字四处 components.css 同步)"
            )
        drifted = sorted(u for u, v in vals.items() if v != want)
        if drifted:
            problems.append(
                f"{'+'.join(drifted)} 皮肤 {label} = {vals[drifted[0]]:g}(应 {want}) —— "
                "改数字须四皮肤 components.css + 守阵锚值同步(§08 菜单加宽连锁)"
            )
    shared = os.path.join(STATIC_ROOT, "shared", "console_hub_panels.css")
    shared_text = re.sub(r"/\*.*?\*/", "", open(shared, encoding="utf-8").read(), flags=re.S)
    shared_slots = re.findall(slot_re, shared_text)
    if len(shared_slots) != 1:
        problems.append(
            f"shared/console_hub_panels.css `.ctx-item .ctx-kbd-slot` 结构规则数 = {len(shared_slots)}(应恰 1 条) —— 四皮肤同构的结构单点丢失"
        )
    elif "flex: none" not in shared_slots[0] or "text-align: right" not in shared_slots[0]:
        problems.append(
            "shared/console_hub_panels.css `.ctx-item .ctx-kbd-slot` 缺 flex:none/text-align:right —— 键位槽右对齐结构丢失"
        )
    elif re.search(r"min-width|margin-left", shared_slots[0]):
        problems.append(
            "shared/console_hub_panels.css `.ctx-item .ctx-kbd-slot` 混入 min-width/margin-left 数字 —— 外观数字只在皮肤专属层, 共享结构侧不许分裂第二份宽度口径"
        )


def _scan_state_color_tokens(problems):
    """状态色令牌守阵(2026-11-02): 每皮肤的 7 个 kind 都必须有 --st/--st-soft, 进度条必须读 --st

    背景: 进度条填充原先各皮肤写死(atlas 蓝渐变 / console+flux 绿 LED / prism --accent), 与
    种子状态无关 —— 星图/棱镜下"做种"的条是蓝的、控制台/流影下"下载"的条是绿的, 颜色把状态
    读反; 且 downloading/checking/moving 三支同 --blue, 校验中与下载中肉眼分不出。
    处置 = 行元素上声明 --st/--st-soft(7 kind), 图例/芯片/行文字/进度条统一消费变量。

    钉四件事(缺一条都是静默故障):
    1. 每个 kind 都要有 --st 声明, 且取值 = 期望表(防漏一个状态 → 回落写死色);
    2. --st-soft 同条声明(芯片底用); 3. 进度条 `.bar > i` 每皮肤恰 1 条且体内含 var(--st;
    4. 值漂移即红(checking 被人改回 --blue → 校验中又和下载中同色, 用户报障原样复发)。
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
    1. 弹窗侧: `.modal` 必须保留无前缀 + `-webkit-`(Safari < 18)两份 blur 声明, 且底必须是
       半透明角色面(`--msg-base`), 不允许再回到 `--bg-elev` 近不透明底;
    2. 透明修复侧(26-11-02 R7, 2026-11-04 反转): flux `--bg-pop` 必须仍是不透明色 —— 但 26-11-02
       「八类无 blur 浮层一律 --bg-pop」的口径已被 2026-11-04「全浮层玻璃化」取代(用户报「添加
       种子/右键菜单等弹窗毛玻璃近乎没有」): 26-11-02 透正文的根因是半透明底**无 blur**, 挂上
       blur 后半透明即毛玻璃。现钉菜单/浮层族 = 半透明 --bg-card + blur(见 4); --bg-pop 消费面
       收窄到 .col-ghost(拖动虚影不玻璃化);
    3. 提示条不得被 `--msg-base` 波及: `--msg-base` 只许在 `.modal-mask` 作用域声明(挂 :root
       会让无 blur 的 `.toast` 一起变透明, 即透明修复倒退), 且 --bg-card 的 alpha 必须低于
       --bg-elev, 保证 blur 有可见透视;
    6. 遮罩浓度钉(2026-11-04 第二根因): `.modal-mask` alpha ≤ .6 —— 玻璃可见度 = 弹窗底 alpha ×
       遮罩 alpha, 11-03 轮修了弹窗底但 .72 遮罩仍把实际透视压到 ~5%。
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

    # 1. 弹窗本体: 两份 blur + 半透明角色底
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

    # 2. 角色底单点: --msg-surface 恰一处, 且用 --msg-base 分流(提示条近不透明 / 弹窗半透明)
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

    # 3. 提示条不得被半透明角色底波及(无 blur 的小条透出正文 = 透明修复倒退)
    for rel, sel, _body in base_decls:
        if sel != ".modal-mask":
            problems.append(
                f"{rel} `{sel}` 声明了 --msg-base —— 只许在 `.modal-mask` 作用域分流; 挂 :root/.toast"
                "会让无 blur 的提示条一起变透明(下层正文透出, 用户报障原症状)"
            )

    # 4. 2026-11-04 全浮层玻璃化(用户复报「添加种子/右键菜单等弹窗毛玻璃近乎没有」): 26-11-02
    #   「透正文」的根因是半透明底**无 blur**; 挂上 blur 后半透明即毛玻璃, 不再透可读正文。
    #   - --bg-pop 仍必须不透明, 消费面收窄到 .col-ghost(列头拖动虚影 —— 每帧移动的 fixed 元素
    #     挂 blur = 逐帧回读采样, 唯一不玻璃化的浮层);
    #   - 菜单/浮层族必须「半透明底(--bg-card) + blur」, 反向钉住防整族退回不透明平底;
    #   - 共用层覆盖(html[data-fx-preset] 前缀)同口径; :is() 组在 rules 字典里被逗号拆散, 按原文正则钉。
    style = open(style_path, encoding="utf-8").read() if os.path.isfile(style_path) else ""
    m = re.search(r"--bg-pop\s*:\s*([^;]+);", style)
    if not m:
        problems.append("flux/style.css 缺 --bg-pop —— 拖动虚影(.col-ghost)的不透明底单点被删")
    else:
        val = m.group(1).strip()
        if any(t in val for t in ("rgba(", "rgb(", "hsla(", "transparent")):
            problems.append(f"flux `--bg-pop` = {val} —— 必须是不透明色(消费面 = .col-ghost)")
    ghost = rules.get(".col-ghost")
    if not ghost:
        problems.append("flux 缺 `.col-ghost` 规则 —— 唯一保留不透明底的浮层无处落")
    elif not any("var(--bg-pop" in body for _r, body in ghost):
        problems.append("flux `.col-ghost` 未消费 var(--bg-pop) —— 拖动虚影每帧移动, 挂 blur = 逐帧回读采样, 保留不透明底")
    for sel in (
        ".col-menu",
        ".pop-menu",
        ".ctx-menu",
        ".ctx-sub",
        ".ce-chart-tip",
        ".hist-tip",
        ".hr-full-modal",
        ".add-drop-box",
        ".speed-pop",
        ".hr-pop",
        ".hp-arrow",
    ):
        bodies = rules.get(sel)
        if not bodies:
            problems.append(f"flux 缺 `{sel}` 规则 —— 玻璃化浮层族断档")
        else:
            body = "\n".join(b for _r, b in bodies)
            # 两份声明各钉各的: "backdrop-filter: blur(" 是 "-webkit-backdrop-filter: blur(" 的
            # 子串, 纯子串判断挡不住「只删无前缀(Chrome/Edge/Firefox 主链路)留前缀别名」的回归
            # (评审面2内存探针实测全绿) —— 无前缀侧用负向环视排除前缀别名。
            if not re.search(r"(?<!-webkit-)backdrop-filter: blur\(", body):
                problems.append(
                    f"flux `{sel}` 缺无前缀 backdrop-filter —— 2026-11-04 全浮层玻璃化档位缺失"
                    "(主链路 blur 丢失 = 用户报障的「毛玻璃没有」原状)"
                )
            if "-webkit-backdrop-filter: blur(" not in body:
                problems.append(f"flux `{sel}` 缺 -webkit-backdrop-filter —— Safari < 18 的前缀别名缺失")
            if "var(--bg-card" not in body:
                problems.append(f"flux `{sel}` 底未走半透明 --bg-card —— 不透明底吃掉 blur, 毛玻璃形同虚设")
    dialogs_path = os.path.join(flux_dir, "css", "dialogs.css")
    dialogs_text = re.sub(r"/\*.*?\*/", "", open(dialogs_path, encoding="utf-8").read(),
                          flags=re.S) if os.path.isfile(dialogs_path) else ""
    if not re.search(r"html\[data-fx-preset\] \.hb-pop\s*\{[^}]*backdrop-filter: blur\(", dialogs_text):
        problems.append("flux/css/dialogs.css 的 `html[data-fx-preset] .hb-pop` 覆盖未挂 blur —— 共用层浮层玻璃化缺角")
    grp = re.search(r"html\[data-fx-preset\] :is\(([^)]*)\)\s*\{[^}]*var\(--bg-card\)[^}]*blur\(", dialogs_text)
    if not grp:
        problems.append(
            "flux/css/dialogs.css 的共用层 :is() 覆盖组未玻璃化 —— 需半透明 --bg-card + blur"
            "(shared 本体仍钉不透明 --bg-pop, flux 侧覆盖反转)"
        )
    else:
        # 逐成员锚定: 组正则只看整体时, 任一成员被删出组会静默回落 shared 不透明基线
        # (评审面2探针实测: 只锚 .relc-pop 时删 .aq-tip 全绿)
        for member in (
            ".hb-pop-arrow", ".hb-tr-drop", ".search-help-pop", ".aq-tip", ".err-panel", ".rowlang-menu", ".relc-pop"
        ):
            if member not in [m.strip() for m in grp.group(1).split(",")]:
                problems.append(f"flux 共用层 :is() 玻璃化覆盖组缺 `{member}` —— 该面回落不透明基线, 玻璃静默丢失")

    # 5. blur 要有可见透视: --bg-card alpha 必须低于 --bg-elev 且明显低于 1
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

    # 6. 遮罩浓度: 玻璃可见度 = 弹窗底 alpha × 遮罩 alpha 的叠乘 —— 2026-11-03 轮只修了弹窗底
    #   (.92→.82), 但遮罩 .72 使对下层内容的实际透视仅 ~5%, blur 依旧肉眼不可见(2026-11-04
    #   用户复报「近乎没有」的第二根因)。本轮同批降浓的三块遮罩统一钉 alpha ≤ .6, 防
    #   「调深遮罩提对比」把玻璃再次压死(评审面2探针实测只钉 .modal-mask 时另两块回拨不红)。
    for mask_sel in (".modal-mask", ".hr-full-mask", ".add-drop-mask"):
        mask_bodies = rules.get(mask_sel, [])
        if not mask_bodies:
            problems.append(f"flux 缺 `{mask_sel}` 规则 —— 遮罩浓度钉无处落")
            continue
        mm = re.search(r"rgba\([^)]*,\s*([0-9.]+)\s*\)", "\n".join(b for _r, b in mask_bodies))
        if not mm:
            problems.append(f"flux `{mask_sel}` 底不是 rgba() —— 遮罩浓度无从判定"
                            "(玻璃可见度 = 弹窗底 alpha × 遮罩 alpha)")
        elif float(mm.group(1)) > .6:
            problems.append(
                f"flux `{mask_sel}` 遮罩 alpha = {mm.group(1)} —— 超 .6 上限; 遮罩过浓会把其上玻璃面的 blur 压成"
                "肉眼不可见(2026-11-04 第二根因: .72 遮罩 × .82 弹窗底 = 实际透视仅 ~5%)"
            )
