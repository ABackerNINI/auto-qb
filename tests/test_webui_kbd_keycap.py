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
