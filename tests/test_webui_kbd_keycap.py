"""test_webui_kbd_keycap 测试计划: WebUI 键帽取数单点 + 共享键帽类守阵(计划 26-11-12-0344 S1)。

守什么: 「注册表 shortcut 条目 -> 键位显示串」helper(kbShortcutDisplay, shared/shortcuts.js)是
键帽取数唯一入口(不变量 I1: kbSerialWithDraft 模板基准 def ⊕ 用户草稿 overrides 空串判定 ->
kbDisplayName), 设置键位面板(tpl/settings-detail.html)/ Shift+/ 帮助浮层(tpl/popovers.html)/
后续键帽消费方(计划 S2-S5: 右键菜单/顶栏/页签徽标/状态栏入口)一律经它取数 —— 不许第二套取数
逻辑, 更不许在模板/JS 里写死键位串; 改绑即时生效与空串即隐藏由同一条链保证。共享 CSS 键帽类
.aq-kbd 在 console_hub_panels.css 尾段单点, 四皮肤同构; 令牌纪律 I3: 只引用既有令牌
(--surface-2/--border/--fg/--font-mono), 零新增令牌, 四皮肤令牌名集不动(parity 守阵继续兜住)。

## 测试计划

- test_kb_shortcut_display_helper: node 电池真跑 shortcuts.js(无 node 静默跳过) —— 未绑定条目
  (def 空位, 无 override)返回空串 / 绑定条目 -> kbDisplayName 人类键名(含 code 映射箭头) /
  改绑草稿即时生效(override 胜出, 与 kbSerialWithDraft 同链) / 草稿显式置空(禁用)返回空串 /
  无关草稿回落模板基准 / 条目缺失防御性空串 / 注册表 def:"" 空位四条经单点全空串 /
  AQB_SHORTCUTS.methods.kbDisplayOf 委托单点(草稿经 this.kbDraft 生效)
- test_kbd_display_single_source_static: 取数链单点静态锚 —— kbShortcutDisplay 定义在
  shortcuts.js 且由 kbSerialWithDraft + kbDisplayName 组成; shortcuts_panel.js kbDisplayOf 委托
  kbShortcutDisplay 并传 this.kbDraft; settings-detail / popovers 两处模板键帽 v-if 与文本均走
  kbDisplayOf; 全模板零 kbDisplayName(kbSerialOf(...)) 二套取数残留
- test_aq_kbd_css_four_skin_isomorphic: 共享 CSS 键帽类 .aq-kbd 在 console_hub_panels.css 单点
  (形状沿用 .kb-row-keys kbd 先例口径), var() 引用只落在 I3 允许集
  {--surface-2, --border, --fg, --font-mono} 且无字面色值; 四皮肤 index.html 全部 link
  console_hub_panels.css(共享单文件 => 四皮肤同构, 静态断言不做截图); 置灰行键帽随行 needle
  (.ctx-menu .ctx-item.is-gated .aq-kbd -> var(--fg-dim), S2 增量: dyn gate 置灰行走各皮肤
  components.css 既有置灰链, 键帽不随行会原地亮 --fg)
- test_keycap_static_mounts_topbar_and_drawer_tabs(计划 S3/S4): 顶栏键帽(添加种子/列选择两钮
  <kbd class="aq-kbd"> 常驻 DOM, 串走 AQB_SHORTCUTS.methods.kbKeycapOf -> kbKeycapById ->
  kbShortcutDisplay 单点, id 引用注册表 add-torrent/col-picker; D6 口径 = 顶栏恰两处键帽,
  设置 Ctrl+, 不做)+ 抽屉页签徽标(两态 <aq-seg> 挂 :kbd-of 回调 + 流量页签按钮内联 kbd,
  drawer.js dtTabKbdOf/dtMergeTabKbdOf/dtTrafficKbd 三入口统一经 _dtTabKbd ->
  kbDrawerTabKbd 单点) + kbDrawerTabKbd 合并态必须读 KB_MERGE_TAB_REMAP(与键盘 run 同表,
  脱钩即 S4 单点破口) + 改绑即时跟随的响应式链(草稿源 AQB_KEYS 快照非响应式: state.js
  kbKeysRev 显式建字段 + 适配器四变更点 _kbReloadKeys/_kbApplyOverrides/kbSaveKeys/
  kbDraftRevert 各 +1 + 取数方法渲染期 void 读, 断一环 = 常驻键帽面改绑后钉死)
  + 被接线模板零手抄键位串(禁 "Alt + " 字面量与无 v-if 的静态 kbd)
- test_keycap_static_mount_statusbar_entry(计划 S5): 状态栏「键位」入口钮(<kbd class="aq-kbd">
  常驻 DOM, 串走 AQB_SHORTCUTS.methods.kbKeycapOf -> kbKeycapById -> kbShortcutDisplay 单点,
  id 引用注册表 help-panel —— 与 Shift+/ 键盘条目同一条目, I1 不手抄)+ 分派链 = @click.stop
  调 kbToggleHelp 模板别名(shortcuts_engine.js 一比一中转 _kbToggleKbHelp = 注册表
  help-panel run 同一 toggle 方法, 开/关行为与 Shift+/ 完全一致; 模板别名因 Vue 解析不到
  _ 前缀成员, issue 26-10-03-1412; 纯显示层: 引擎/浮层本体零改动)+ statusbar.html 恰一处
  kbd(S5 = 恰一处入口, 反漂移)+ 反手抄锚扩 statusbar.html(kbd 必带 v-if, 键位串字面量禁入)
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess

from webui_helpers import STATIC_ROOT, _UI_ALL, read_shared

SHARED = os.path.join(STATIC_ROOT, "shared")
PANELS_CSS = os.path.join(SHARED, "console_hub_panels.css")

# I3 令牌纪律: .aq-kbd 的 var() 引用只允许这个集合(四皮肤 :root 既有令牌, parity 守阵兜住)
AQ_KBD_TOKENS = {"--surface-2", "--border", "--fg", "--font-mono"}

# node 电池: 加载真实 shortcuts.js + shortcuts_panel.js(kbDisplayOf 在面板片段), 对键帽取数单点
# 跑行为面(空串判定/改绑草稿即时生效)。注册表 AQB_SHORTCUT_DEFS 是 new Function 体内 const,
# 顶层取不到 —— 用体尾挂电池 IIFE(test_frontend_qb_traffic_scope_stale_polarity 取 _QB_SCOPES
# 同款手法)。无 node 静默跳过(与 _scan_js_syntax_with_node 同口径, 不引入 pytest skip)。
_NODE_KBD_DISPLAY_PROBE = r"""
const fs = require("fs");
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8") + "\n" + fs.readFileSync(process.argv[2], "utf8");
const report = new Function(src + "\n;return (function battery() {" + `
const J = JSON.stringify;
const checks = [];
const A = (name, cond) => checks.push([name, !!cond]);
const unbound = { id: "super-seeding", def: "" };
const bound = { id: "act-reannounce", def: "Shift+KeyA" };
A("未绑定条目(def 空位, 无 override)返回空串", kbShortcutDisplay(unbound, null) === "");
A("绑定条目 -> kbDisplayName(Shift + A)", kbShortcutDisplay(bound, null) === "Shift + A");
A("code 映射(队列上移 Ctrl + 箭头)", kbShortcutDisplay({ id: "queue-up", def: "Ctrl+ArrowUp" }, null) === "Ctrl + " + KB_CODE_NAMES.ArrowUp);
A("改绑草稿即时生效(override 胜出, 与 kbSerialWithDraft 同链)",
  kbShortcutDisplay(bound, { overrides: { "act-reannounce": "KeyZ" } }) === "Z");
A("草稿显式置空(禁用)返回空串", kbShortcutDisplay(bound, { overrides: { "act-reannounce": "" } }) === "");
A("无关草稿回落模板基准", kbShortcutDisplay(bound, { overrides: { "act-pause": "KeyZ" } }) === "Shift + A");
A("条目缺失防御性空串(不抛)", kbShortcutDisplay(null, null) === "");
const holes = AQB_SHORTCUT_DEFS.filter((it) => it.def === "").map((it) => it.id);
A("注册表 def 空位四条 id 如期", J(holes) === J(["super-seeding", "share-limits", "clear-filters", "invert-select"]));
A("注册表空位经单点全返回空串", holes.every((id) => kbShortcutDisplay(AQB_SHORTCUT_DEFS.find((it) => it.id === id), null) === ""));
const M = window.AQB_SHORTCUTS.methods;
A("kbDisplayOf 委托单点(草稿经 this.kbDraft 生效)",
  typeof M.kbDisplayOf === "function"
  && M.kbDisplayOf.call({ kbDraft: { overrides: { "act-reannounce": "KeyZ" } } }, bound) === "Z"
  && M.kbDisplayOf.call({ kbDraft: null }, unbound) === "");
/* S3: 顶栏静态挂点按 shortcut id 直查(kbKeycapById -> kbShortcutDisplay 单点链) */
A("kbKeycapById: 顶栏两钮 id 现算(N/K)", kbKeycapById("add-torrent", null) === "N" && kbKeycapById("col-picker", null) === "K");
A("kbKeycapById: 未知 id 防御性空串(不抛)", kbKeycapById("no-such-entry", null) === "");
/* S5: 状态栏「键位」入口钮按 shortcut id 现算(id 引用注册表 help-panel, 与 Shift+/ 键盘条目同一条目) */
A("kbKeycapById: help-panel 状态栏入口现算(Shift + /)", kbKeycapById("help-panel", null) === "Shift + /");
A("kbKeycapOf 方法委托单点(沙箱无适配器回默认表)",
  typeof M.kbKeycapOf === "function" && M.kbKeycapOf.call({}, "add-torrent") === "N");
/* S4: 页签徽标单点 —— 非合并五档直映 / 合并态与 KB_MERGE_TAB_REMAP 同表反查(位次重排) */
const T = (pages, merged) => kbDrawerTabKbd(pages, merged, null);
A("非合并页签徽标五档直映(Alt+1..5, 含 traffic Alt+5)",
  T(["general"], false) === "Alt + 1" && T(["trackers"], false) === "Alt + 2"
  && T(["peers"], false) === "Alt + 3" && T(["content"], false) === "Alt + 4"
  && T(["traffic"], false) === "Alt + 5");
A("合并态对页签徽标反查(gc=Alt+1 / tp=Alt+2)", T(["general", "content"], true) === "Alt + 1" && T(["trackers", "peers"], true) === "Alt + 2");
A("合并态流量页签徽标随位次变 Alt+5 -> Alt+3", T(["traffic"], true) === "Alt + 3");
A("合并态第 4/5 档(null)停用不显示", T(["content"], true) === "" && T(["nope"], true) === "" && T([], true) === "");
A("页签徽标改绑草稿即时跟随(override 胜出)", kbDrawerTabKbd(["general"], false, { overrides: { "drawer-tab-general": "KeyZ" } }) === "Z");
A("合并态徽标与键盘重排表逐档同值(单点同表证明)",
  Object.keys(KB_MERGE_TAB_REMAP).every((k) => {
    const dst = KB_MERGE_TAB_REMAP[k];
    return !dst || T([dst], true) === kbKeycapById("drawer-tab-" + k, null);
  }));
return { ok: checks.filter((c) => c[1]).length, total: checks.length, failed: checks.filter((c) => !c[1]).map((c) => c[0]) };
` + "})();")();
console.log(JSON.stringify(report));
"""


def test_kb_shortcut_display_helper() -> None:
    """键帽取数单点 kbShortcutDisplay 行为电池(node 真跑, 无 node 静默跳过)"""
    node = shutil.which("node")
    if not node:
        return
    proc = subprocess.run(
        [
            node, "-e", _NODE_KBD_DISPLAY_PROBE,
            os.path.join(SHARED, "shortcuts.js"),
            os.path.join(SHARED, "shortcuts_panel.js")
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, f"kbShortcutDisplay node 电池跑挂: {proc.stderr.strip()}"
    report = json.loads(proc.stdout.strip().splitlines()[-1])
    assert report["failed"] == [], f"键帽取数电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


def test_kbd_display_single_source_static() -> None:
    """取数链单点静态锚: helper 组成 / kbDisplayOf 委托 / 两模板走单点 / 二套取数零残留"""
    shortcuts = read_shared("shortcuts.js")
    m = re.search(r"function kbShortcutDisplay\(item, draft\) \{(.*?)\n\}", shortcuts, re.S)
    assert m, "shortcuts.js 缺 kbShortcutDisplay(键帽取数单点被改名/搬走? 同步本守阵)"
    body = m.group(1)
    assert "kbSerialWithDraft(item, draft)" in body and "kbDisplayName(serial)" in body, (
        "kbShortcutDisplay 必须由 kbSerialWithDraft 空串判定 + kbDisplayName 组成(不许第二套取数逻辑)"
    )
    panel = read_shared("shortcuts_panel.js")
    m2 = re.search(r"kbDisplayOf\(item\) \{(.*?)\n    \},", panel, re.S)
    assert m2, "shortcuts_panel.js 缺 kbDisplayOf(模板键帽取数入口被改名/搬走?)"
    assert "kbShortcutDisplay(item, this.kbDraft)" in m2.group(1
                                                              ), ("kbDisplayOf 必须委托单点并传 this.kbDraft(面板即时试用稿, 改绑即时生效)")
    # 两处既有键帽消费面: v-if 与文本同走单点(空串判定和显示名内含在单点里, 模板不自己拼)
    for tpl in ("tpl/settings-detail.html", "tpl/popovers.html"):
        text = open(os.path.join(SHARED, tpl), encoding="utf-8").read()
        assert 'v-if="kbDisplayOf(it)">{{ kbDisplayOf(it) }}</kbd>' in text, (
            f"{tpl} 键帽 v-if 与文本须同走 kbDisplayOf 单点(计划 26-11-12-0344 S1)"
        )
    # 二套取数残留反锚: 全模板不许再有 kbSerialOf + kbDisplayName 手拼
    tpl_dir = os.path.join(SHARED, "tpl")
    for name in os.listdir(tpl_dir):
        text = open(os.path.join(tpl_dir, name), encoding="utf-8").read()
        assert "kbDisplayName(kbSerialOf(" not in text, (
            f"tpl/{name} 出现 kbDisplayName(kbSerialOf(...)) 手拼 —— 键位显示串一律走 kbShortcutDisplay 单点(I1)"
        )


def test_aq_kbd_css_four_skin_isomorphic() -> None:
    """共享键帽类 .aq-kbd: 令牌纪律 I3 + 四皮肤同构(共享单文件 + 四 shell 全 link, 静态断言)"""
    css = open(PANELS_CSS, encoding="utf-8").read()
    m = re.search(r"\.aq-kbd \{(.*?)\n\}", css, re.S)
    assert m, "console_hub_panels.css 缺共享键帽类 .aq-kbd(S1 单点被搬走? 同步本守阵)"
    body = m.group(1)
    vars_used = set(re.findall(r"var\((--[\w-]+)", body))
    assert vars_used, ".aq-kbd 须引用既有令牌(四皮肤同构靠令牌, 不许字面色值)"
    assert vars_used <= AQ_KBD_TOKENS, (f".aq-kbd 引用了 I3 允许集之外的令牌(疑似新增令牌): {sorted(vars_used - AQ_KBD_TOKENS)}")
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", body), ".aq-kbd 不许字面色值(令牌纪律 I3)"
    # 四皮肤同构: 键帽类是共享单文件单点, 四份 shell 全 link 同一文件 => 同一规则四皮肤生效
    for ui in _UI_ALL:
        shell = open(os.path.join(STATIC_ROOT, ui, "index.html"), encoding="utf-8").read()
        assert 'href="/shared/console_hub_panels.css"' in shell, (
            f"{ui} shell 未 link console_hub_panels.css(键帽类四皮肤同构破口)"
        )
    # 置灰行键帽随行(S2 增量): dyn gate 置灰(.is-gated, 各皮肤 components.css 的置灰链
    # label -> var(--fg-dim))行内键帽颜色必须随行, 规则被删/改名 = 置灰行键帽原地亮 --fg
    assert ".ctx-menu .ctx-item.is-gated .aq-kbd { color: var(--fg-dim); }" in css, (
        "console_hub_panels.css 缺置灰行键帽随行规则 .ctx-menu .ctx-item.is-gated .aq-kbd"
        "(S2 增量被删? 同步本守阵与 e2e menus.spec 置灰键帽色断言)"
    )
    # 页签键帽徽标版式(S4): .drawer-tabs button 内联流下键帽居中 + 左距 —— 必须在 .aq-kbd
    # 基形之后(守阵以「文件里首个 .aq-kbd { 即共享基形」定位, 本测试自己的正则同此假设)
    assert ".drawer-tabs button .aq-kbd { vertical-align: middle; margin-left: 3px; }" in css, (
        "console_hub_panels.css 缺抽屉页签键帽徽标版式规则(S4 被删?)"
    )


def test_keycap_static_mounts_topbar_and_drawer_tabs() -> None:
    """S3 顶栏键帽 + S4 页签徽标接线静态锚(计划 26-11-12-0344)

    顶栏: 添加种子/列选择两钮内联 <kbd class="aq-kbd"> 常驻 DOM(I4/D10: 键位提示不走
    title/.aq-tip 通道), 串走 kbKeycapOf(id 引用注册表, I1 不手抄); D6 口径 = 顶栏恰两处,
    设置 Ctrl+, 不做。页签: 两态 <aq-seg> 挂 :kbd-of 回调 + 流量页签按钮内联 kbd, drawer.js
    三个投影方法统一经 _dtTabKbd -> kbDrawerTabKbd 单点(合并态与键盘 run 同表
    KB_MERGE_TAB_REMAP); 被接线模板零手抄键位串。
    """
    topbar = open(os.path.join(SHARED, "tpl", "topbar.html"), encoding="utf-8").read()
    for sid in ("add-torrent", "col-picker"):
        needle = "<kbd v-if=\"kbKeycapOf('%s')\" class=\"aq-kbd\">{{ kbKeycapOf('%s') }}</kbd>" % (sid, sid)
        assert needle in topbar, (f"topbar.html 缺 {sid} 键帽节点(S3)或未走 kbKeycapOf 单点(I1 改绑即时跟随/空串即隐藏)")
    assert topbar.count("<kbd") == 2, (
        f"topbar.html 键帽数量漂移(D6 拍板: 恰 add-torrent/col-picker 两处, 设置 Ctrl+, 不做; "
        f"实测 {topbar.count('<kbd')} 处)"
    )

    drawer_tpl = open(os.path.join(SHARED, "tpl", "drawer.html"), encoding="utf-8").read()
    assert ':kbd-of="(it) => dtMergeTabKbdOf(it)"' in drawer_tpl \
        and ':kbd-of="(it) => dtTabKbdOf(it)"' in drawer_tpl, (
        "drawer.html 两态 <aq-seg> 缺 :kbd-of 键帽回调(S4 徽标被删? 同步本守阵)"
    )
    assert '流量 <kbd v-if="dtTrafficKbd()" class="aq-kbd">{{ dtTrafficKbd() }}</kbd>' in drawer_tpl, (
        "drawer.html 流量页签缺内联键帽节点(S4: 非合并 Alt+5 / 合并态位次重排 Alt+3)"
    )

    drawer_js = open(os.path.join(SHARED, "drawer.js"), encoding="utf-8").read()
    for m in ("dtTabKbdOf", "dtMergeTabKbdOf", "dtTrafficKbd"):
        assert re.search(rf"{m}\((?:it)?\) \{{", drawer_js), f"drawer.js 缺页签徽标投影方法 {m}(S4)"
    assert drawer_js.count("this._dtTabKbd(") == 3, ("drawer.js 页签徽标三入口必须统一走 _dtTabKbd 单点(就地取数 = 第二套键位链)")
    assert "kbDrawerTabKbd(pages, merged, draft)" in drawer_js, (
        "_dtTabKbd 必须把页集合/合并态透传 shortcuts.js kbDrawerTabKbd 单点"
    )

    # 改绑即时跟随的响应式链(S3/S4): 草稿源 AQB_KEYS 快照非响应式, 常驻键帽面(顶栏/页签, 不像
    # 右键菜单逐次开层重渲)靠 kbKeysRev 代次注册渲染依赖 —— state 显式建字段 + 适配器四个变更点
    # 各 +1 + 两处取数方法渲染期 void 读。断任何一环 = 改绑后键帽钉死(e2e drawer-merge 改绑
    # 跟随用例行为面同证)。
    shortcuts = read_shared("shortcuts.js")
    state_js = open(os.path.join(SHARED, "state.js"), encoding="utf-8").read()
    assert "kbKeysRev: 0," in state_js, "state.js 缺 kbKeysRev 显式建字段(vue-reactivity 坑)"
    engine = open(os.path.join(SHARED, "shortcuts_engine.js"), encoding="utf-8").read()
    panel = open(os.path.join(SHARED, "shortcuts_panel.js"), encoding="utf-8").read()
    for src, fn in (
        (engine, "_kbReloadKeys"), (panel, "_kbApplyOverrides"), (panel, "kbSaveKeys"), (panel, "kbDraftRevert")
    ):
        m4 = re.search(rf"{fn}\((?:quiet = false|overrides)?\) \{{(.*?)\n    \}},", src, re.S)
        assert m4 and "this.kbKeysRev++" in m4.group(1), (f"{fn} 缺 kbKeysRev++(适配器变更点必须通知常驻键帽面重渲染, S3/S4)")
    assert "void this.kbKeysRev;" in drawer_js and "void this.kbKeysRev;" in shortcuts, (
        "键帽取数方法(_dtTabKbd/kbKeycapOf)渲染期必须 void 读 kbKeysRev 注册依赖(改绑即时跟随)"
    )

    m = re.search(r"function kbDrawerTabKbd\(pages, merged, draft\) \{(.*?)\n\}", shortcuts, re.S)
    assert m, "shortcuts.js 缺 kbDrawerTabKbd(页签徽标取数单点被改名/搬走? 同步本守阵)"
    body = m.group(1)
    assert "KB_MERGE_TAB_REMAP" in body and "kbKeycapById" in body, (
        "kbDrawerTabKbd 合并态必须读 KB_MERGE_TAB_REMAP(与键盘 run 同一重排表, 脱钩 = 徽标错位)"
        "且经 kbKeycapById -> kbShortcutDisplay 取数(I1)"
    )
    m2 = re.search(r"function kbKeycapById\(id, draft\) \{(.*?)\n\}", shortcuts, re.S)
    assert m2 and "kbShortcutDisplay" in m2.group(1), ("kbKeycapById 必须经 kbShortcutDisplay 单点(不许第二套取数逻辑)")

    # aq-seg 可选键帽: prop + 模板渲染(其余三套分段钮不传 kbdOf, DOM 零变化)
    bits = open(os.path.join(SHARED, "tpl", "ctl-bits.html"), encoding="utf-8").read()
    m3 = re.search(r'<script type="text/x-template" id="tpl-aq-seg">(.*?)</script>', bits, re.S)
    assert m3 and 'v-if="kbdOf && kbdOf(it)"' in m3.group(1) and 'class="aq-kbd"' in m3.group(1), (
        "tpl-aq-seg 缺可选键帽渲染(S4)"
    )
    ctl = open(os.path.join(SHARED, "ctl_bits.js"), encoding="utf-8").read()
    assert "kbdOf: { type: Function, default: null }" in ctl, "aq-seg 缺 kbdOf 可选 prop(S4)"

    # 反手抄锚: 被接线模板零手抄键位串 —— kbd 一律带 v-if(现算空串判定), 键位显示串字面量
    # (「Alt + 」带空格形态即 kbDisplayName 输出)不得出现在模板里
    for name in ("topbar.html", "drawer.html", "ctl-bits.html", "statusbar.html"):
        text = open(os.path.join(SHARED, "tpl", name), encoding="utf-8").read()
        assert re.search(r"<kbd(?![^>]*v-if=)", text) is None, (f"tpl/{name} 出现无 v-if 的静态 <kbd>(键位串必须现算, 禁手抄)")
        assert "Alt + " not in text, (f"tpl/{name} 出现手抄键位显示串字面量「Alt + …」 —— 一律走 kbShortcutDisplay 单点(I1)")


def test_keycap_static_mount_statusbar_entry() -> None:
    """S5 状态栏「键位」入口接线静态锚(计划 26-11-12-0344)

    状态栏: 「键位」文字钮(.sb-btn, 与「完整统计」同款四皮肤既有样式零新增)内联
    <kbd class="aq-kbd"> 常驻 DOM, 串走 kbKeycapOf(id 引用注册表 help-panel —— 与 Shift+/
    键盘条目同一条目, I1 不手抄); 分派 = @click.stop 调 kbToggleHelp 模板别名 —— 该别名必须
    一比一中转 _kbToggleKbHelp(注册表 help-panel run 的同一 toggle 方法, 开/关行为与 Shift+/
    完全一致; 别名存在的唯一理由是 Vue 模板解析不到 _ 前缀成员, issue 26-10-03-1412;
    _kbToggleKbHelp 方法体的开/关双分支由 test_web_shortcuts_drawer 切换语义守阵钉住)。
    纯显示层: 引擎/浮层本体零改动, S5 = 恰一处入口(kbd 数量反漂移)。
    """
    sb = open(os.path.join(SHARED, "tpl", "statusbar.html"), encoding="utf-8").read()
    # 键帽节点: v-if 与文本同走 kbKeycapOf 单点(空串判定内含在单点里, 模板不自己拼)
    needle = "<kbd v-if=\"kbKeycapOf('help-panel')\" class=\"aq-kbd\">{{ kbKeycapOf('help-panel') }}</kbd>"
    assert needle in sb, ("statusbar.html 缺键位帮助入口键帽节点(S5)或未走 kbKeycapOf 单点"
                          "(I1 改绑即时跟随/空串即隐藏与顶栏键帽同链)")
    assert sb.count("<kbd") == 1, (f"statusbar.html 键帽数量漂移(S5 拍板: 恰 help-panel 入口一处; 实测 {sb.count('<kbd')} 处)")
    # 分派链: click 调 kbToggleHelp(模板可触达的无前缀别名, issue 26-10-03-1412); 别名必须
    # 一比一中转 _kbToggleKbHelp —— 与注册表 help-panel run 同一 toggle 方法(不得另写实现),
    # 中转体断言单点在下方 engine 块。
    assert '@click.stop="kbToggleHelp()"' in sb, (
        "statusbar.html 键位入口缺 @click.stop=kbToggleHelp 分派(help-panel 同链 toggle 方法)"
    )
    engine = open(os.path.join(SHARED, "shortcuts_engine.js"), encoding="utf-8").read()
    m_alias = re.search(r"kbToggleHelp\(\) \{(.*?)\n    \},", engine, re.S)
    assert m_alias and "this._kbToggleKbHelp()" in m_alias.group(1), (
        "shortcuts_engine.js 缺 kbToggleHelp 模板别名或别名不再中转 _kbToggleKbHelp"
        "(分派必须与 Shift+/ 同链, 不得另写 toggle 实现)"
    )
    # 入口钮文案锚: 「键位」二字已最短(计划 §07 状态栏溢出对策 —— 超限只许缩文案不许加宽)
    assert "键位" in sb, "statusbar.html 缺「键位」入口文案(S5)"
    # 版式锚: 复用 .sb-btn(与「完整统计」同款) —— 不另起样式类(零新增 CSS, I3 令牌纪律)
    entry = re.search(r'<button class="sb-btn" @click\.stop="kbToggleHelp\(\)">', sb)
    assert entry, "statusbar.html 键位入口钮未用 .sb-btn 既有样式类(四皮肤零新增 CSS 的落点)"
