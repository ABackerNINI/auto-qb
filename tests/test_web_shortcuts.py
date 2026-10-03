"""键盘快捷键守阵 (计划 26-09-28-0354 W1-W7 全波; 引擎与面板在 shared/shortcuts.js)。

守什么: 注册表是键位**单一事实源**(表外无键位), 而前端无 JS 测试框架 —— 键位冲突、黑名单
越界、危险档键位形态、run 指到不存在的方法, 这些错误全部**静默**(不报错只是键不响/误触),
只能靠静态断言钉住。挂载成对(三份 tpl-manifest + app.mixin)由本文件与 test_web.py 的
_scan_mixin_wiring 双保险。光标滚动跟随禁 scrollIntoView、模态默认焦点/Enter 确认(§08)、
Delete 直连注册表外, 均为已拍板的口径, 逐条落断言。W5 局部作用域(drawer/settings/modal
三档 + 浮层放行焦点局部)与 W6 自定义(适配器 /api/keys / 录制器 / 冲突三选一 / 帮助浮层 /
设置页分区)逐条接线断言见下半部; 后端端点行为测试在 test_web.py(GET 兜底链 / PUT 422 / 金清单)。

## 测试计划

- test_registry_single_source: 注册表 id 唯一 / def 归一化串合法 / scope 合法 / group+label 非空;
  全波激活: 非 fixed 条目必须带 run(run: null 仅允许 fixed 的 Esc 展示条目)
- test_danger_keys_two_combo_and_pinned: 危险档默认键一律二键组合(修饰键+字母), 且 §08 v4 三条
  逐字钉住(删除 Shift+KeyD / 重新校验 Shift+KeyY / 强制汇报 Shift+KeyA; 超级做种空位)
- test_default_keys_no_conflict_and_no_blacklist: 非 fixed 非空默认键两两不同, 且不碰浏览器黑名单
- test_runs_resolve_to_bundle_methods: 每个 run 里调用的 vm.X 必须在 bundle 方法成员表里存在
- test_mount_pairing_three_shells: shortcuts.js 进三份 tpl-manifest 且排 app.js 前;
  app.mixin(window.AQB_SHORTCUTS) 存在; kbCursor 在 state.js(根选项, 不许进 app.mixin);
  引擎 keydown 注册在 lifecycle.js Esc 退栈链之后且 unmounted 撤除
- test_engine_input_suppression: IME 双保险 / defaultPrevented / repeat / 纯修饰键 /
  输入元素屏蔽 / Escape 早退(引擎永不接 Esc) 六道拦截齐全
- test_arrow_repeat_continuous: 长按连发只给上下键族 —— 引擎 repeat 拦截放行标记条目,
  注册表 repeat 标记恰为 cursor-up/down + extend-up/down 且 scope=list
- test_delete_direct_outside_registry: 注册表无 def="Delete" 条目; 引擎 Delete 直连 _kbDelete;
  _kbDelete 走 _deleteFlow(与批量浮条同链, 确认框 + HR 点名不可绕过)
- test_danger_kbact_has_confirm: _kbAct 对 recheck / reannounce 先 confirmDialog 再 _actCore
  (键盘路径新增确认框, 鼠标路径不变的 §08 口径)
- test_modal_default_focus_and_enter: 模态确定钮有 ref="modalOk" 且 _openModal 默认焦点落它
  (Enter 即确认 = 按钮原生行为; Esc 取消走退栈链)
- test_cursor_scroll_follow_without_scrollintoview: shortcuts.js 无 scrollIntoView;
  columns.js 留存 _rowPre 前缀和; 光标视觉 .kb-cursor 在共用 CSS 与五处行模板成对
- test_click_lands_cursor_and_viewport_fallback: 键鼠衔接(报告 26-09-30-1806 方案 B) ——
  selection.js 五点击入口按所在行回写 kbCursor(写在修饰键分支之前, Ctrl/Shift 点击同样落光标);
  _kbMove 无光标回落走 _kbViewportRow(前缀和同源校验 / 渲染行可见性扫描, 解析失败退回旧口径)
- test_shift_anchor_unified: 起点统一(计划 26-10-02-0608 方案 B) —— 五点击入口普通/Ctrl 路径落
  起点且排除 Shift(法则 2); 四处消费者走 _selAnchor 单点解析、无裸 list[0]; _selAnchor 兜底链
  齐全(显式 -> 光标 -> 展开组 -> 首行); _selSetAnchor 不碰选中集合; _kbExtend 先落手势原点
  (_selSeedAnchorFromCursor) 再移动光标, 且已有有效起点不动
- test_local_scope_wiring: settings-save inputSafe + Ctrl+KeyS + cfgSave; 引擎 _kbScope
  settings/list 档齐全(方案A W2 起停靠面板不再是作用域, drawer 值机制留位);
  浮层打开只放行焦点局部(settings)键位; 非 inputSafe 条目不得标 inputSafe
- test_drawer_dock_keyboard_w2: 方案A W2(计划 26-10-03-0917 §2.2/§2.3/§3.2/§3.4) ——
  _kbOverlayBusy 摘 drawer.open 而 escBusy 保留(两名单职责分叉: 面板≠浮层 vs Esc 关面板);
  drawer-tab 四条 group=详情面板 / scope=list / run=_kbDrawerTab 双态(非种子页 toast 忽略 /
  开态切页 / 关态开面板定位该页签, 目标解析 kbCursor(torrent) 优先 + 单选种子兜底);
  跟随单点 _kbFollowDrawer 挂 _kbApplyCursor 尾部, page+kind 守卫 + 200ms 防抖 + hash 短路 +
  停稳复核; _loadDrawerTab bump 请求代际 seq 且四 fetcher 带 _drawerStale 旧响应丢弃;
  _switchDrawerTarget 清旧页签数据防串显; open/close 作废在途跟随定时器
- test_modal_whitelist_branch: 引擎含模态白名单分流(modal 条目仅模态内响应, 模态内非模态键位一律失效)
- test_recorder_and_panel_wiring: 录制器按下即录(捕获段监听+stopPropagation) / 纯修饰键拒收 /
  Esc 取消 / 黑名单当场拒绑 / 冲突三选一(交换/覆盖对方置空/取消) / 单条与全部重置 /
  空串=显式禁用语义保留 / danger 裸键提示但允许 / 面板保存 PUT 失败本地回滚 /
  离开守卫挂 hubGo+hubBack 且未保存先确认
- test_adapter_and_backend_endpoints: AQB_KEYS.load 同步快照 / save PUT /api/keys / reload GET /
  脏数据 sanitize 兜底; keys.py 落 routes 注册表; 存储路径与 web.token 同寻址(state_file 同目录)
- test_help_overlay_wiring: help-panel run -> kbOpenHelp; kbHelpOpen 在 state.js 根选项;
  Esc 退栈链 / escBusy / _kbOverlayBusy 三处名单同步; 帮助浮层模板(只读速查 + 前往设置链接)
- test_settings_panel_section: settings-detail 有 hub.view === 'keys' 分支(录制/禁用/重置/
  冲突三选一/保存放弃全套钮); config_hub 首页卡+hubNow+hubRestore 认 "keys";
  console_hub.css 有 .kb-row 样式
- test_esc_chain_clear_filters_fallback: ESC 接退栈链终端兜底清面筛(计划 26-10-02-1632 方案 A) ——
  兜底在收剧展开之后(链序即退栈序, LIFO 不可倒) / 门条件五件套(authOk / page=groups /
  !hrPop.open / !inInput / facetsActive) / toast 点名不静默; Escape 仅 clear-esc 一个默认绑定
  且面板 label 点名清筛选; facetsActive 不含 searchQuery(搜索词归 clearSearch)
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src" / "auto_qb" / "webui" / "static"
SHARED = STATIC / "shared"
UIS = ("atlas", "prism", "console")

# 归一化串合法形态(与 shortcuts.js KB_DEF_RE 同一正则, 改一边必须改另一边)
KB_DEF_RE = re.compile(r"^(Ctrl\+)?(Alt\+)?(Shift\+)?(Meta\+)?[A-Z][A-Za-z0-9]*$")
KB_SCOPES = {"global", "list", "drawer", "settings", "modal"}


def _read(rel: str) -> str:
    return (SHARED / rel).read_text(encoding="utf-8")


def _registry() -> list[dict]:
    """解析 shortcuts.js 的 AQB_SHORTCUT_DEFS(条目字段按固定书写序, 逐条正则提取)"""
    text = _read("shortcuts.js")
    m = re.search(r"const AQB_SHORTCUT_DEFS = \[(.*?)\n\];", text, re.S)
    assert m, "shortcuts.js 找不到 AQB_SHORTCUT_DEFS 注册表(单一事实源被改名/搬走?)"
    out = []
    for chunk in re.split(r'\{ id: "', m.group(1))[1:]:
        item = {
            "id": chunk.split('"', 1)[0],
            "group": _pick(chunk, r'group: "([^"]*)"'),
            "label": _pick(chunk, r'label: "([^"]*)"'),
            "def": _pick(chunk, r'def: "([^"]*)"'),
            "scope": _pick(chunk, r'scope: "(\w+)"'),
            "danger": 'danger: true' in chunk,
            "fixed": 'fixed: true' in chunk,
            "inputSafe": 'inputSafe: true' in chunk,
            "repeat": 'repeat: true' in chunk,
            "run_null": "run: null" in chunk,
            "runs": re.findall(r"run: \(vm\) => vm\.(\w+)\(", chunk),
        }
        out.append(item)
    assert out, "注册表解析出 0 条(书写格式漂移? 同步本守阵的解析)"
    return out


def _pick(chunk: str, pattern: str) -> str:
    m = re.search(pattern, chunk)
    return m.group(1) if m else ""


def _manifest_scripts(ui: str) -> list[str]:
    shell = (STATIC / ui / "index.html").read_text(encoding="utf-8")
    m = re.search(r'<script type="application/json" id="tpl-manifest">(.*?)</script>', shell, re.S)
    assert m, f"{ui}/index.html 缺 tpl-manifest 清单"
    return re.findall(r'"(/shared/[^"]+\.js)"', m.group(1))


def _bundle_method_names() -> set[str]:
    """bundle(shared/*.js 清单序)里 methods/computed 块的成员名(与 test_web._section_members 同口径)"""
    names: set[str] = set()
    for src in _manifest_scripts("prism"):
        rel = src.lstrip("/")
        if rel.endswith("vendor/vue.global.prod.js"):
            continue
        text = (STATIC / rel).read_text(encoding="utf-8")
        in_block = False
        for line in text.splitlines():
            if not in_block:
                if line.strip() in ("methods: {", "computed: {"):
                    in_block = True
                continue
            if line in ("  },", "  }"):  # 与 test_web._section_members 同口径: 只认块级收口, 不被嵌套函数骗
                in_block = False
                continue
            m = re.match(r"^    (?:async )?([A-Za-z_$][\w$]*)\s*[(:]", line)
            if m:
                names.add(m.group(1))
    return names


# 浏览器保留键黑名单(与 shortcuts.js KB_BLACKLIST 语义一致, 此处按计划 §3.3 边界独立抄录:
# 默认键表绝不允许出现这些 —— 面板(W6)拒绑是运行时防线, 本断言是默认表的事前防线)
BLACKLIST = set()
for _c in ("KeyW", "KeyT", "KeyN", "KeyQ"):
    BLACKLIST |= {f"Ctrl+{_c}", f"Ctrl+Shift+{_c}"}
BLACKLIST |= {
    "Ctrl+Tab", "Ctrl+Shift+Tab", "F5", "F11", "F12", "Ctrl+Shift+KeyN", "Ctrl+Shift+KeyI", "Ctrl+Shift+KeyJ",
    "Ctrl+Shift+KeyC"
}
BLACKLIST |= {f"Ctrl+Digit{i}" for i in range(1, 9)}


def test_registry_single_source() -> None:
    items = _registry()
    ids = [it["id"] for it in items]
    assert len(ids) == len(set(ids)), f"注册表 id 重复: {[i for i in ids if ids.count(i) > 1]}"
    for it in items:
        assert it["group"] and it["label"], f"{it['id']} 缺 group/label"
        assert it["scope"] in KB_SCOPES, f"{it['id']} scope 非法: {it['scope']}"
        assert not it["def"] or KB_DEF_RE.match(it["def"]), f"{it['id']} def 归一化串非法: {it['def']!r}"
        # 修饰键必须按固定序出现(Ctrl,Alt,Shift,Meta), 否则同一键位有两种写法, 冲突检测失明
        assert not it["def"] or re.fullmatch(r"(Ctrl\+)?(Alt\+)?(Shift\+)?(Meta\+)?[A-Z][A-Za-z0-9]*",
                                             it["def"]), it["id"]
        if it["def"]:
            assert not it["def"].startswith("Meta"), f"{it['id']} 默认键用 Meta(mac Cmd 全族不可拦)"
        # 全波激活(W1-W7): 非 fixed 条目必须带 run; run: null 仅允许 fixed 的 Esc 展示条目
        if it["run_null"]:
            assert it["fixed"], f"{it['id']} 未激活(run: null)却不是 fixed —— 波次收尾后表外无空条目"
        else:
            assert it["runs"], f"{it['id']} 激活条目必须有 run"


def test_danger_keys_two_combo_and_pinned() -> None:
    items = _registry()
    danger = {it["id"]: it["def"] for it in items if it["danger"]}
    # §08 v4: 危险档一律二键组合(一个修饰键 + 字母; 非裸键、非三键), 确认框兜底
    for k, v in danger.items():
        if not v:
            continue
        parts = v.split("+")
        assert len(parts) == 2 and parts[0] in ("Ctrl", "Alt", "Shift"
                                               ) and parts[1].startswith("Key"), (f"危险档 {k} 默认键 {v!r} 不是二键组合(修饰键+字母)")
    # 逐字钉住 §08 v4 终版(改键必须先改拍板, 再改这里与计划)
    assert danger.get("act-delete") == "Shift+KeyD", "删除默认键必须是 Shift+KeyD(另有 Delete 直连)"
    assert danger.get("act-recheck") == "Shift+KeyY", "重新校验默认键必须是 Shift+KeyY"
    assert danger.get("act-reannounce") == "Shift+KeyA", "强制汇报默认键必须是 Shift+KeyA"
    assert danger.get("super-seeding") == "", "超级做种为空位(面板标危险, 不默认绑定)"


def test_default_keys_no_conflict_and_no_blacklist() -> None:
    items = _registry()
    seen: dict[str, str] = {}
    for it in items:
        if not it["def"] or it["fixed"]:
            continue
        assert it["def"] not in BLACKLIST, f"{it['id']} 默认键 {it['def']} 撞浏览器黑名单(preventDefault 无效)"
        assert it["def"] not in seen, (f"默认键 {it['def']} 被 {it['id']} 与 {seen[it['def']]} 同时占用 —— 后者被静默覆盖")
        seen[it["def"]] = it["id"]


def test_runs_resolve_to_bundle_methods() -> None:
    members = _bundle_method_names()
    for it in _registry():
        for name in it["runs"]:
            assert name in members, (
                f"注册表 {it['id']} 的 run 调用 vm.{name}(), 但 bundle 方法成员表里没有 {name} "
                "—— 方法被改名后键位会静默失效"
            )


def test_mount_pairing_three_shells() -> None:
    for ui in UIS:
        scripts = _manifest_scripts(ui)
        assert "/shared/shortcuts.js" in scripts, f"{ui} 的 tpl-manifest 未挂 shortcuts.js(整块功能静默消失)"
        assert scripts.index("/shared/shortcuts.js") < scripts.index("/shared/app.js"), (
            f"{ui}: shortcuts.js 必须排在 app.js 之前(app.js 要读 window.AQB_SHORTCUTS)"
        )
    app_js = _read("app.js")
    assert "app.mixin(window.AQB_SHORTCUTS);" in app_js, "app.js 未注入 AQB_SHORTCUTS mixin"
    state_js = _read("state.js")
    assert "kbCursor: null" in state_js, "kbCursor 必须在 state.js 根选项 data(不许进 app.mixin)"
    life = _read("lifecycle.js")
    esc_chain_at = life.find('e.key !== "Escape"')
    kb_at = life.find('document.addEventListener("keydown", this._kbKeyDown)')
    assert esc_chain_at >= 0 and kb_at > esc_chain_at, ("引擎 keydown 必须注册在 Esc 退栈链之后(注册序 = 触发序; 链序不回归是 W1 验收口径)")
    assert 'document.removeEventListener("keydown", this._kbKeyDown)' in life, ("unmounted 必须撤掉引擎监听(防热重载句柄堆叠)")


def test_engine_input_suppression() -> None:
    eng = _read("shortcuts.js")
    for needle, why in [
        ('e.key === "Escape"', "引擎必须对 Escape 早退(Esc 归退栈链, 引擎永不接)"),
        ("e.defaultPrevented", "必须尊重 defaultPrevented(多 handler 礼仪)"),
        ("e.isComposing || e.keyCode === 229", "IME 组合期双保险(isComposing + 229)"),
        ("KB_MODIFIER_CODES.has(e.code)", "纯修饰键不判定"),
        ("e.repeat", "长按自动重复一律不吃"),
        ('"input, textarea, select, [contenteditable]"', "输入元素屏蔽(输入态三段之二)"),
        ("_kbOverlayBusy()", "模态层屏蔽(输入态三段之三; 列表键位在浮层下必须失效)"),
        ("inputSafe", "输入元素内只放行显式标记 inputSafe 的绑定"),
        ("_kbScope()", "作用域判定(非焦点页不串扰, W1 验收口径)"),
    ]:
        assert needle in eng, f"shortcuts.js 缺引擎拦截: {why}"


def test_arrow_repeat_continuous() -> None:
    """长按连发(2026-09-30): 上下键族按住不动连续触发, 其余键位自动重复仍一律丢弃"""
    eng = _read("shortcuts.js")
    assert "e.repeat && !(item && item.repeat)" in eng, ("引擎必须保留 repeat 拦截且只放行标记条目(逐键查询后判定)")
    items = {it["id"]: it for it in _registry()}
    expected = {"cursor-up", "cursor-down", "extend-up", "extend-down"}
    marked = {tid for tid, it in items.items() if it["repeat"]}
    assert marked == expected, f"repeat 标记漂移: 多出 {marked - expected} / 缺 {expected - marked}(每按一次发一条后端命令的键位不许开连发)"
    for tid in sorted(expected):
        assert items[tid]["scope"] == "list", f"{tid} repeat 条目必须 list 作用域(连发不该越过输入态/浮层屏蔽)"


def test_delete_direct_outside_registry() -> None:
    for it in _registry():
        assert it["def"] != "Delete", "Delete 键不进注册表(§08 v4: 额外删除操作直连, 不占键表槽位)"
    eng = _read("shortcuts.js")
    m = re.search(r'if \(!inInput && e\.code === "Delete"(.*?)\n        \}', eng, re.S)
    assert m and "_kbDelete()" in m.group(1), "引擎未直连 Delete -> _kbDelete(§08 决策 v4)"
    assert "_kbOverlayBusy()" in m.group(1) and '"list"' in m.group(1), ("Delete 直连必须带浮层屏蔽与 list 作用域守卫(输入态/浮层下不得误删)")
    body = re.search(r"async _kbDelete\(\) \{(.*?)\n  \},", eng, re.S)
    assert body and "_deleteFlow(" in body.group(1), ("_kbDelete 必须走 _deleteFlow(与批量浮条同链: 确认框 + HR 风险点名不可绕过)")


def test_danger_kbact_has_confirm() -> None:
    eng = _read("shortcuts.js")
    body = re.search(r"async _kbAct\(action\) \{(.*?)\n  \},", eng, re.S)
    assert body, "shortcuts.js 找不到 _kbAct(危险档键盘路径确认框的落点)"
    text = body.group(1)
    # §08: 重新校验/强制汇报键盘路径新增确认框(默认确定/Enter 确认); 鼠标路径不变
    for action in ("recheck", "reannounce"):
        confirm_at = text.find(f'if (action === "{action}")')
        core_at = text.find("this._actCore(")
        assert 0 <= confirm_at < core_at, f"{action} 必须先 confirmDialog 再进 _actCore(§08 危险档口径)"
        assert "confirmDialog(" in text, "确认框走站内 confirmDialog(默认焦点在确定, Enter 确认)"


def test_modal_default_focus_and_enter() -> None:
    pop = (SHARED / "tpl" / "popovers.html").read_text(encoding="utf-8")
    m = re.search(r'<button ref="modalOk"[^>]*@click="resolveModal\(true\)"', pop)
    assert m, "模态确定钮缺 ref=modalOk(计划 §08: 默认焦点在确定, Enter 即确认)"
    fb = _read("ui_feedback.js")
    open_at = fb.find("_openModal(cfg)")
    assert open_at >= 0 and fb.find("this.$refs.modalOk",
                                    open_at) > open_at, ("_openModal 必须在无输入形态时把默认焦点落到 modalOk(Enter 即确认; Esc 取消走退栈链)")


def test_cursor_scroll_follow_without_scrollintoview() -> None:
    eng = _read("shortcuts.js")
    assert ".scrollIntoView(" not in eng, (
        "光标滚动跟随禁用 scrollIntoView(逐层滚动可滚祖先会连带滚整页, "
        "pitfalls web-ui/hover-keynav-fight) —— 用 getBoundingClientRect/前缀和差值"
    )
    assert "this._rowPre" in eng and "_rowPre[kind]" in eng, ("窗口化未渲染行必须用 _rowWindow 留存的前缀和换算 y(计划 W2)")
    cols = _read("columns.js")
    assert re.search(r"this\._rowPre\[kind\] = pre;",
                     cols), ("columns.js._rowWindow 必须把前缀和留存进 this._rowPre[kind](键盘光标滚动进视口依赖)")
    assert ".kb-cursor" in (SHARED / "console_hub.css").read_text(encoding="utf-8"
                                                                 ), ("光标行视觉 .kb-cursor 必须在共用层 CSS(三套 UI 同载)")
    for tpl, kind, idexpr in [
        ("groups.html", "group", "g.key"),
        ("torrents.html", "torrent", "m.hash"),
        ("shows.html", "show", "s.key"),
        ("groups.html", "torrent", "m.hash"),  # 明细成员行(点击落光标的视觉落点, 方案 B)
        ("shows.html", "torrent", "m.hash"),  # 集明细成员行(同上)
    ]:
        text = (SHARED / "tpl" / tpl).read_text(encoding="utf-8")
        assert f"'kb-cursor': isKbCursor('{kind}'" in text, f"{tpl} 缺 {kind} 行光标绑定"
    shows = (SHARED / "tpl" / "shows.html").read_text(encoding="utf-8")
    assert ':data-key="s.key"' in shows, "剧行缺 data-key(光标定位锚点, W2)"
    assert ':data-key="showEpRowId(' in shows, "集行缺 data-key(光标定位锚点, W2)"


def test_click_lands_cursor_and_viewport_fallback() -> None:
    """键鼠衔接(报告 26-09-30-1806 方案 B): 五个点击入口回写 kbCursor(落光标 ≠ 选中);
    无光标/光标失效回落 = 视口就近行(修「鼠标在列表顶部按一下 ↑ 视口跳到底」的 S1 根因)"""
    sel = _read("selection.js")
    for fn, write in [
        ("onGroupClick", 'this.kbCursor = { kind: "group", id: g.key };'),
        ("onMemberClick", 'this.kbCursor = { kind: "torrent", id: m.hash };'),
        ("onTorrentClick", 'this.kbCursor = { kind: "torrent", id: m.hash };'),
        ("onShowClick", 'this.kbCursor = { kind: "show", id: s.key };'),
        ("onShowEpClick", 'this.kbCursor = { kind: "ep", id };'),
    ]:
        m = re.search(rf"{fn}\([^)]*\) \{{(.*?)\n    \}},", sel, re.S)
        assert m, f"selection.js 找不到 {fn}(五点击入口被改名/搬走? 同步本守阵)"
        body = m.group(1)
        assert write in body, f"{fn} 缺点击落光标回写(键鼠衔接被静默丢掉: {write})"
        at = body.find("this.kbCursor")
        ctrl_at = body.find("event.ctrlKey")
        assert 0 <= at < ctrl_at, f"{fn} 落光标必须写在修饰键分支之前(Ctrl/Shift+点击同样落光标)"
    eng = _read("shortcuts.js")
    move = re.search(r"_kbMove\(delta\) \{(.*?)\n    \},", eng, re.S)
    assert move, "shortcuts.js 找不到 _kbMove(回落口径落点)"
    assert "_kbViewportRow(rows, delta)" in move.group(1), "无光标回落必须走视口就近解析(方案 B)"
    assert "(delta > 0 ? 0 : rows.length - 1)" not in move.group(1), "_kbMove 不得直写极值回落(必须经 _kbViewportRow)"
    vp = re.search(r"_kbViewportRow\(rows, delta\) \{(.*?)\n    \},", eng, re.S)
    assert vp, "缺 _kbViewportRow(视口就近回落解析单点)"
    vb = vp.group(1)
    assert "_rowPre" in vb and "rows.length + 1" in vb, "窗口化视图必须用 _rowPre 前缀和换算且做长度同源校验(不符放弃, P1-2 口径)"
    assert "getBoundingClientRect" in vb, "非窗口化/前缀失效时必须扫渲染行可见性(v-if 保证 DOM 只有当前视图)"
    assert ".scrollIntoView(" not in vb, "回落解析只读几何, 禁 scrollIntoView(pitfalls web-ui/hover-keynav-fight)"
    assert "rows.length - 1" in vb, "解析失败的保守退路 = 旧口径(↓ 首行 / ↑ 末行)"


def test_shift_anchor_unified() -> None:
    """起点统一(计划 26-10-02-0608 方案 B): 区间起点(anchor)与光标一样纳入键鼠统一模型 ——
    点击落起点(Shift 不重置, 法则 2) / 四处消费者走单点解析(不再各写一遍 list[0]) /
    键盘 Shift 手势原点先于移动光标(否则区间塌成单行, G2)。"""
    sel = _read("selection.js")
    # ① 五入口普通/Ctrl 路径落起点, 写在修饰键分支之前, 且排除 Shift 分支(法则 2)
    for fn, write in [
        ("onGroupClick", 'this._selSetAnchor("group", g.key)'),
        ("onMemberClick", 'this._selSetAnchor("member", m.hash)'),
        ("onTorrentClick", 'this._selSetAnchor("member", m.hash)'),
        ("onShowClick", 'this._selSetAnchor("unit", "show|" + s.key)'),
        ("onShowEpClick", 'this._selSetAnchor("unit", id)'),
    ]:
        m = re.search(rf"{fn}\([^)]*\) \{{(.*?)\n    \}},", sel, re.S)
        assert m, f"selection.js 找不到 {fn}(五点击入口被改名/搬走? 同步本守阵)"
        body = m.group(1)
        at = body.find("_selSetAnchor")
        ctrl_at = body.find("event.ctrlKey")
        assert at >= 0, f"{fn} 缺点击落起点(起点与光标脱节: 点第 5 行 Shift 选却从表头起)"
        assert 0 <= at < ctrl_at, f"{fn} 落起点必须写在修饰键分支之前"
        line = next(ln for ln in body.splitlines() if "_selSetAnchor" in ln)
        assert "event.shiftKey" in line and "!" in line, (f"{fn} 落起点必须排除 Shift 分支(法则 2: 否则 Shift+点击只选目标单行, M1 回归)")
        assert write in body, f"{fn} 落起点值不对(起点 id 形态漂移: {write})"
    # ② 四处消费者统一走单点解析, 不再出现裸 list[0] 兜底
    for fn, call in [
        ("shiftGroupSel", 'this._selAnchor("group", list)'),
        ("shiftMemberSel", 'this._selAnchor("member", list)'),
        ("shiftTorrentSel", 'this._selAnchor("member", list)'),
        ("_extendUnit", 'this._selAnchor("unit", units)'),
    ]:
        m = re.search(rf"{fn}\([^)]*\) \{{(.*?)\n    \}},", sel, re.S)
        assert m, f"selection.js 找不到 {fn}(起点消费者被改名/搬走? 同步本守阵)"
        body = m.group(1)
        assert call in body, f"{fn} 未走起点单点解析 {call}(四处各写兜底 = 口径漂移源)"
        assert "list[0]" not in body, f"{fn} 仍残留裸 list[0] 兜底(起点脱节根因)"
    # ③ 起点解析单点: 兜底链齐全 + 落起点不碰选中集合
    anchor = re.search(r"_selAnchor\(kind, list\) \{(.*?)\n    \},", sel, re.S)
    assert anchor, "缺 _selAnchor(起点解析单点)"
    ab = anchor.group(1)
    for needle, why in [
        ("_selCursorId(kind)", "兜底链缺「当前光标」一环(键盘走到第 20 行 Shift 选却从表头起)"),
        ("this.expandedKey", "辅种页缺「展开的组」次选兜底(既有产品规则 menu.js/toggleExpand)"),
        ("ids[0]", "缺最后兜底(列表首行)"),
    ]:
        assert needle in ab, f"_selAnchor {why}"
    setter = re.search(r"_selSetAnchor\(kind, id\) \{(.*?)\n    \},", sel, re.S)
    assert setter and "this[this._selAnchorField(kind)] = id;" in setter.group(1), (
        "_selSetAnchor 必须只写 selAnchor* 字段(落起点 != 选中)"
    )
    sb = setter.group(1)
    assert "selGroups" not in sb and "selMembers" not in sb, ("_selSetAnchor 不得触碰选中集合(与 2026-09-17「普通点击不选中」冲突)")
    # ④ 键盘手势原点: 先落起点再移动光标, 且已有有效起点不动(法则 2)
    eng = _read("shortcuts.js")
    ext = re.search(r"_kbExtend\(delta\) \{(.*?)\n    \},", eng, re.S)
    assert ext, "shortcuts.js 找不到 _kbExtend(键盘 Shift 扩展落点)"
    eb = ext.group(1)
    seed_at = eb.find("_selSeedAnchorFromCursor()")
    move_at = eb.find("this._kbMove(delta)")
    assert seed_at >= 0, "_kbExtend 缺手势原点落起点(首次 Shift 扩展从列表首行起算的根因)"
    assert 0 <= seed_at < move_at, "_kbExtend 必须先落起点再移动光标(顺序反了区间塌成单行)"
    seed = re.search(r"_selSeedAnchorFromCursor\(\) \{(.*?)\n    \},", eng, re.S)
    assert seed, "缺 _selSeedAnchorFromCursor(键盘手势原点)"
    seedb = seed.group(1)
    assert "ctx.ids.includes(this[field])" in seedb, ("已有有效起点必须不动(法则 2: 同一起点多次 Shift 扩展)")
    assert "this[field] = fromCursor" in seedb, "无有效起点时必须以当前光标落起点"


def test_local_scope_wiring() -> None:
    """W5 局部作用域: settings-save 接线 + 引擎 scope 档齐全 + 浮层放行焦点局部(方案A W2 后口径)"""
    items = {it["id"]: it for it in _registry()}
    save = items["settings-save"]
    assert save["scope"] == "settings" and save["inputSafe"], "settings-save 必须 settings 作用域 + inputSafe"
    assert save["def"] == "Ctrl+KeyS", "settings-save 默认键必须是 Ctrl+KeyS"
    eng = _read("shortcuts.js")
    # scope 档(设置页/列表; modal 在派发处分流)。方案A W2: 停靠面板不再是作用域 ——
    # drawer.open 不进 _kbScope(否则面板开着 list 条目全被 item.scope !== scope 拦死),
    # "drawer" 值由 KB_SCOPES 与浮层放行分支机制留位
    scope_body = re.search(r"_kbScope\(\) \{(.*?)\n    \},", eng, re.S)
    assert scope_body, "shortcuts.js 找不到 _kbScope"
    assert 'this.page === "settings"' in scope_body.group(1) and 'return "list";' in scope_body.group(
        1
    ), "_kbScope 缺 settings/list 档"
    assert "drawer.open" not in scope_body.group(1), "_kbScope 不得再判 drawer.open(停靠面板=list 作用域, W2 §3.2)"
    # 浮层打开只放行焦点局部自身的键位, 其余一律失效(drawer 放行判定机制留位, 现不可达)
    assert 'scope !== "drawer" && scope !== "settings"' in eng, ("浮层放行分支必须只认局部键位(列表键位在浮层下仍失效)")
    # inputSafe 只允许 settings 作用域(输入框内放行的键位不该作用于列表页)
    for it in _registry():
        if it["inputSafe"]:
            assert it["scope"] == "settings", f"{it['id']} inputSafe 条目必须 settings 作用域"


def test_drawer_dock_keyboard_w2() -> None:
    """方案A W2(计划 26-10-03-0917 §2.2 矩阵 / §2.3 跟随纪律 / §3.2 scope 派发 / §3.4 数据面)"""
    eng = _read("shortcuts.js")
    drawer_js = _read("drawer.js")
    # --- §3.2 名单分叉: _kbOverlayBusy 摘 drawer.open(面板≠浮层), escBusy 保留(Esc 关面板) ---
    busy = re.search(r"_kbOverlayBusy\(\) \{(.*?)\n    \},", eng, re.S)
    assert busy, "shortcuts.js 找不到 _kbOverlayBusy"
    assert "this.drawer.open" not in busy.group(1), "_kbOverlayBusy 必须摘除 drawer.open(停靠面板不是浮层, Delete 等列表键面板开着要保持可用)"
    assert "this.filePrio.visible || this.historyOpen" in busy.group(1), "_kbOverlayBusy 名单书写序漂移, 同步本守阵解析"
    dialogs_js = _read("dialogs.js")
    esc_busy = re.search(r"escBusy\(\) \{(.*?)\n    \},", dialogs_js, re.S)
    assert esc_busy and "this.drawer.open" in esc_busy.group(1), "escBusy 必须保留 drawer.open(面板开 Esc=关面板, 退栈链零改动)"
    # --- §3.2 drawer-tab 四条: 详情面板组 / list 作用域 / run=_kbDrawerTab 双态 ---
    items = {it["id"]: it for it in _registry()}
    for tid in ("drawer-tab-general", "drawer-tab-trackers", "drawer-tab-peers", "drawer-tab-content"):
        it = items[tid]
        assert it["group"] == "详情面板", f"{tid} 应独立成「详情面板」组(帮助面板语义变化可见)"
        assert it["scope"] == "list", f"{tid} 必须 list 作用域(W2 双态; drawer 作用域条目清空)"
        assert it["def"].startswith("Alt+Digit"), f"{tid} 默认键应为 Alt+1-4"
    assert 'run: (vm) => vm._kbDrawerTab("general")' in eng, "drawer-tab-general run 未走 _kbDrawerTab 双态入口"
    # 双态实现: 非种子页 toast 忽略 -> 开态切页 -> 关态开面板定位该页签
    dtab = re.search(r"_kbDrawerTab\(tab\) \{(.*?)\n    \},", eng, re.S)
    assert dtab, "shortcuts.js 找不到 _kbDrawerTab(Alt+1-4 双态入口)"
    tb = dtab.group(1)
    assert tb.index('this.page !== "groups" || this.viewMode !== "torrents"'
                   ) < tb.index("this.drawerTab(tab)"), "非种子页守卫必须先于双态分流(停靠落点只在种子视图)"
    assert "this.toast(" in tb, "非种子页必须 toast 提示后忽略, 不许静默"
    assert tb.index("if (this.drawer.open)") < tb.index("openTorrentDrawer(hash)"), "双态序: 开态切页 / 关态开面板"
    assert "this.drawerLastTab = tab;" in tb and "this.persistDrawerTab()" in tb, "关态开面板必须经 drawerLastTab 定位该页签(openTorrentDrawer 的初始页签口径)"
    # 目标解析: kbCursor(kind=torrent) 优先, 单选种子兜底, 无目标 _kbHint
    assert 'c.kind === "torrent" ? c.id : this._kbSingleHash()' in tb, "目标解析须 kbCursor(torrent) 优先 + _kbSingleHash 兜底"
    assert "this._kbHint()" in tb, "无目标必须 _kbHint 提示后忽略"
    # --- §2.3 跟随单点: 挂 _kbApplyCursor 尾部, page+kind 守卫 + 防抖 + hash 短路 + 停稳复核 ---
    apply_cur = re.search(r"_kbApplyCursor\(rows, idx\) \{(.*?)\n    \},", eng, re.S)
    assert apply_cur and "_kbFollowDrawer()" in apply_cur.group(1), "跟随单点必须挂 _kbApplyCursor 尾部(§2.3 触发单点)"
    follow = re.search(r"_kbFollowDrawer\(\) \{(.*?)\n    \},", drawer_js, re.S)
    assert follow, "drawer.js 找不到 _kbFollowDrawer(跟随单点应在数据面)"
    fb = follow.group(1)
    assert fb.index("this.drawer.open") < fb.index('c.kind !== "torrent"'), "跟随守卫序: 面板开 -> 种子页 -> kind=torrent"
    assert 'this.page !== "groups" || this.viewMode !== "torrents"' in fb, "挂点必须带种子页守卫(追剧/组行视图共用 _kbApplyCursor 不波及)"
    assert "}, 200)" in fb, "跟随必须 200ms 防抖(连发上下键不逐行拉详情)"
    assert "this.drawer.hash === c.id" in fb, "hash 未变必须短路(光标落回同一行不重拉)"
    assert "cur.id === this.drawer.hash" in fb and "cur.kind !== \"torrent\"" in fb, "停稳复核必须再验目标(面板关/切页/目标已换/落回原行放弃)"
    # --- §3.4 数据面: _loadDrawerTab 代际 seq + fetcher 旧响应丢弃 + 换目标清数据 ---
    load = re.search(r"_loadDrawerTab\(tab\) \{(.*?)\n    \},", drawer_js, re.S)
    assert load and "this._drawerLoadSeq = (this._drawerLoadSeq || 0) + 1" in load.group(
        1
    ), "_loadDrawerTab 必须 bump 请求代际 seq(换目标/换页签后旧响应丢弃)"
    for fn in ("_fetchDrawerDetail", "_fetchDrawerTrackers", "_fetchDrawerFiles", "_fetchDrawerPeers"):
        sig = re.search(rf"async {fn}\((.*?)\) \{{", drawer_js)
        assert sig and "seq = 0" in sig.group(1), f"{fn} 必须带可选 seq(代际守卫)"
    assert drawer_js.count("this._drawerStale(hash, seq)") >= 8, "四个 fetcher 的成功/异常/finally 三路都必须过 _drawerStale 旧响应丢弃"
    stale = re.search(r"_drawerStale\(hash, seq\) \{\n      return (.*?);\n    \},", drawer_js, re.S)
    assert stale and "this.drawer.hash !== hash" in stale.group(1) and "seq !== this._drawerLoadSeq" in stale.group(
        1
    ), "_drawerStale 必须 hash 戳 + 代际双守卫(hash 戳兜 5s 轮询竞态)"
    switch = re.search(r"_switchDrawerTarget\(hash\) \{(.*?)\n    \},", drawer_js, re.S)
    assert switch, "drawer.js 找不到 _switchDrawerTarget(跟随换目标落点)"
    sb = switch.group(1)
    assert "this.drawer.trackers = [];" in sb and "this.drawer.files = [];" in sb and "this.drawer.peers = { peers: [] };" in sb, "换目标必须清旧页签数据(防止串显上个种子的 trackers/files/peers)"
    assert "this._loadDrawerTab(this.drawer.tab)" in sb, "换目标后必须按当前页签重拉(跟随保留页签, 不回 drawerLastTab)"
    assert 'if (this.drawer.tab !== "general") this._fetchDrawerDetail();' in sb, (
        "换目标必须恒拉详情(头部标题依赖; _loadDrawerTab 只在 general 页签拉, 走查发现的串显 hash 缺口)"
    )
    # open/close 作废在途跟随(显式操作优先于防抖中的跟随)
    assert drawer_js.count("this._stopDrawerFollow();") >= 2, "openTorrentDrawer 与 closeDrawer 都必须作废在途跟随定时器"
    # Delete 直连的 list 作用域守卫仍成立(停靠面板下 scope=list, Delete 可用 —— §2.2 矩阵)
    assert 'this._kbScope() === "list"' in eng, "Delete 直连必须保留 list 作用域守卫(面板开着 scope 仍为 list)"


def test_modal_whitelist_branch() -> None:
    """W5: 模态层白名单 —— 模态内只响应模态键位(计划 §5.1 输入态三段之三)"""
    eng = _read("shortcuts.js")
    assert 'item.scope === "modal"' in eng and "!this.modal.visible" in eng, ("引擎必须含 modal 白名单分流: modal 条目仅模态层内响应")
    assert "} else if (this.modal.visible) {" in eng, ("模态打开时非模态条目必须一律失效(列表/全局键位不得穿透模态)")


def test_recorder_and_panel_wiring() -> None:
    """W6 面板与录制器(§5.2): 录制/取消/黑名单/冲突三选一/重置/禁用/保存/离开守卫"""
    eng = _read("shortcuts.js")
    # 录制器: 捕获段监听 + stopPropagation(录制态按键不进引擎/退栈链/hubOnKey)
    for needle, why in [
        ('document.addEventListener("keydown", this._kbRecHandler, true)', "录制走捕获段监听(先于引擎)"),
        ("e.stopPropagation()", "录制态按键必须截断, 引擎与退栈链收不到"),
        ("KB_MODIFIER_CODES.has(e.code)", "纯修饰键拒收(§3.3)"),
        ('e.key === "Escape"', "Esc 取消录制"),
        ("kbInBlacklist(serial)", "黑名单当场拒绑(§3.3 边界)"),
        ("kbSerializeEvent(e)", "按下即录走归一化序列(与引擎同一序列化单点)"),
    ]:
        assert needle in eng, f"录制器缺实现: {why}"
    # 冲突三选一: 交换 / 覆盖(对方置空) / 取消
    body = re.search(r"kbConflictResolve\(mode\) \{(.*?)\n  \},", eng, re.S)
    assert body, "缺 kbConflictResolve(冲突三选一落点)"
    text = body.group(1)
    assert 'mode === "swap"' in text and 'mode === "steal"' in text, "冲突必须含交换/覆盖两支"
    assert 'ov[other.id] = ""' in text, "覆盖语义 = 对方置空(空串=显式禁用, 不能丢)"
    # 重置单条/全部 + 空串禁用
    assert "kbResetAll" in eng and "kbResetRow" in eng and "kbDisableRow" in eng, "缺重置/禁用入口"
    # 保存语义: PUT 失败本地回滚; 成功提示跨浏览器刷新生效
    save = re.search(r"async kbSaveKeys\(\) \{(.*?)\n  \},", eng, re.S)
    assert save and "kbDraftRevert()" in save.group(1), "保存失败必须本地回滚(§4.4)"
    # 危险档: danger 裸键提示但允许(§08 v4)
    assert 'item.danger && serial && !serial.includes("+"' in eng, "danger 绑裸键必须提示(允许)"
    # 面板离开守卫: 未保存先确认, 且同时挂在 hubGo 与 hubBack
    hub = _read("config_hub.js")
    for fn in ("hubGo(key) {", "hubBack() {"):
        at = hub.find(fn)
        assert at >= 0 and hub.find("kbGuardLeave",
                                    at) < hub.find("this.hub.view",
                                                   at), (f"{fn.split('(')[0]} 必须先过 kbGuardLeave 离开守卫(未保存提示, §5.2)")
    assert "kbGuardLeave(target)" in eng and 'this.hub.view !== "keys"' in eng, "缺离开守卫实现"


def test_adapter_and_backend_endpoints() -> None:
    """W6 存储链: 适配器三口(load 同步/save PUT/reload GET) + 后端单点路由"""
    eng = _read("shortcuts.js")
    assert "/api/keys" in eng, "适配器未指向 /api/keys"
    for needle, why in [
        ("async reload(token)", "reload: GET 服务端真值(启动/开面板时拉)"),
        ("async save(doc, token)", "save: PUT 整份替换(§4.4)"),
        ("load() {", "load 必须保持同步快照(引擎 keydown 内现取, 不 await)"),
        ("_sanitize(doc)", "服务端脏数据第二道兜底(版本不识别/结构不符回默认)"),
    ]:
        assert needle in eng, f"适配器缺口: {why}"
    keys_py = (ROOT / "src" / "auto_qb" / "webui" / "server" / "routes" / "keys.py").read_text(encoding="utf-8")
    assert "webui-keys.json" in keys_py, "后端存储文件名必须是 webui-keys.json(计划 §4.4)"
    assert "manager.state_file" in keys_py, "存储路径必须与 web.token 同寻址(state_file 同目录)"
    assert "atomic_write(" in keys_py and "keep_backup=True" in keys_py, "写盘必须走 atomic_write + .bak"
    init = (ROOT / "src" / "auto_qb" / "webui" / "server" / "routes" / "__init__.py").read_text(encoding="utf-8")
    assert "_keys.build_router" in init, "keys 路由未注册进 ROUTE_BUILDERS"
    # state.js 根选项: 面板/浮层状态不许进 app.mixin(pitfalls web-ui/frontend-split)
    state_js = _read("state.js")
    for field in ("kbHelpOpen: false", "kbDraft: null", "kbSaved: null", "kbRecId:", "kbConflict: null"):
        assert field in state_js, f"state.js 缺根选项字段 {field.split(':')[0]}"
    polling = _read("polling.js")
    assert "_kbReloadKeys(true)" in polling, "startPolling(两条登录路径唯一汇合点)必须拉一次键位真值"


def test_help_overlay_wiring() -> None:
    """W6 H 组: 帮助浮层(只读速查 + 前往设置自定义)"""
    eng = _read("shortcuts.js")
    assert "kbOpenHelp()" in eng, "help-panel run 未接 kbOpenHelp"
    assert "kbGoSettings()" in eng, "帮助浮层缺「前往设置自定义」链路"
    life = _read("lifecycle.js")
    chain_at = life.find('e.key !== "Escape"')
    kb_at = life.find("this.kbHelpOpen = false")
    assert chain_at >= 0 and kb_at > chain_at, "帮助浮层必须进 lifecycle Esc 退栈链"
    assert "this.kbHelpOpen" in _read("dialogs.js"), "escBusy 必须同步 kbHelpOpen(新增浮层两处同步守则)"
    assert "this.kbHelpOpen" in eng, "_kbOverlayBusy 必须同步 kbHelpOpen(浮层打开时列表键位失效)"
    pop = (SHARED / "tpl" / "popovers.html").read_text(encoding="utf-8")
    for needle in ('v-if="kbHelpOpen"', "kbGroups()", "kbEntriesOf(grp)", "kbGoSettings()"):
        assert needle in pop, f"帮助浮层模板缺 {needle}"


def test_settings_panel_section() -> None:
    """W6 设置页「快捷键」分区: 模板分支 + 首页卡/元信息/恢复 + CSS"""
    detail = (SHARED / "tpl" / "settings-detail.html").read_text(encoding="utf-8")
    assert "hub.view === 'keys'" in detail, "settings-detail 缺快捷键分区分支"
    for needle in (
        "kbRecord(it.id)", "kbDisableRow(it)", "kbResetRow(it)", "kbResetAll()", "kbSaveKeys()", "kbDraftRevert()",
        "kbConflictResolve(", "kbDisplayName(kbSerialOf(it))"
    ):
        assert needle in detail, f"快捷键面板缺交互 {needle}"
    hub = _read("config_hub.js")
    for needle in ('key: "keys"', 'hub.view === "keys"', 'v === "keys"'):
        assert needle in hub, f"config_hub 缺 keys 分区接线: {needle}"
    css = (SHARED / "console_hub.css").read_text(encoding="utf-8")
    for cls in (".kb-row", ".kb-grp-t", ".kb-help", ".kb-conflict", ".kb-danger"):
        assert cls in css, f"console_hub.css 缺 {cls}(挂件类名必须有对应规则)"


def test_esc_chain_clear_filters_fallback() -> None:
    """ESC 接退栈链终端兜底清面筛(计划 26-10-02-1632 方案 A): 链序 / 门条件五件套 /
    toast 点名 / Escape 唯一默认绑定 / facetsActive 不含搜索词"""
    lc = _read("lifecycle.js")
    assert lc.index("expandedShows = []") < lc.index("this.clearFilters()"), \
        "清筛选兜底必须在收剧展开之后(链序即退栈序, LIFO 不可倒)"
    for frag in ("this.authOk", 'this.page === "groups"', "!this.hrPop.open", "!inInput", "this.facetsActive"):
        assert frag in lc, f"清筛选兜底缺门条件: {frag}"
    assert "已清除全部筛选" in lc, "清筛选兜底必须 toast 点名, 不许静默"
    sc = _read("shortcuts.js")
    assert sc.count('def: "Escape"') == 1, "Escape 只许固定键 clear-esc 一个默认绑定"
    assert "清筛选" in sc, "clear-esc 面板 label 必须反映清筛选兜底"
    fj = _read("filters.js")
    block = fj[fj.index("facetsActive()"):]
    block = block[:block.index("},")]
    assert "searchQuery" not in block, "facetsActive 不得含 searchQuery(搜索词归 clearSearch)"
