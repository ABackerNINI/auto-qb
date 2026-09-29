"""键盘快捷键守阵 (计划 26-09-28-0354 W1-W4 第一波; 引擎在 shared/shortcuts.js)。

守什么: 注册表是键位**单一事实源**(表外无键位), 而前端无 JS 测试框架 —— 键位冲突、黑名单
越界、危险档键位形态、run 指到不存在的方法, 这些错误全部**静默**(不报错只是键不响/误触),
只能靠静态断言钉住。挂载成对(三份 tpl-manifest + app.mixin)由本文件与 test_web.py 的
_scan_mixin_wiring 双保险。光标滚动跟随禁 scrollIntoView、模态默认焦点/Enter 确认(§08)、
Delete 直连注册表外, 均为本波拍板的口径, 逐条落断言。

## 测试计划

- test_registry_single_source: 注册表 id 唯一 / def 归一化串合法 / scope 合法 / group+label 非空
- test_danger_keys_two_combo_and_pinned: 危险档默认键一律二键组合(修饰键+字母), 且 §08 v4 三条
  逐字钉住(删除 Shift+KeyD / 重新校验 Shift+KeyY / 强制汇报 Shift+KeyA; 超级做种空位)
- test_default_keys_no_conflict_and_no_blacklist: 非 fixed 非空默认键两两不同, 且不碰浏览器黑名单
- test_runs_resolve_to_bundle_methods: 每个 run 里调用的 vm.X 必须在 bundle 方法成员表里存在
- test_mount_pairing_three_shells: shortcuts.js 进三份 tpl-manifest 且排 app.js 前;
  app.mixin(window.AQB_SHORTCUTS) 存在; kbCursor 在 state.js(根选项, 不许进 app.mixin);
  引擎 keydown 注册在 lifecycle.js Esc 退栈链之后且 unmounted 撤除
- test_engine_input_suppression: IME 双保险 / defaultPrevented / repeat / 纯修饰键 /
  输入元素屏蔽 / Escape 早退(引擎永不接 Esc) 六道拦截齐全
- test_delete_direct_outside_registry: 注册表无 def="Delete" 条目; 引擎 Delete 直连 _kbDelete;
  _kbDelete 走 _deleteFlow(与批量浮条同链, 确认框 + HR 点名不可绕过)
- test_danger_kbact_has_confirm: _kbAct 对 recheck / reannounce 先 confirmDialog 再 _actCore
  (键盘路径新增确认框, 鼠标路径不变的 §08 口径)
- test_modal_default_focus_and_enter: 模态确定钮有 ref="modalOk" 且 _openModal 默认焦点落它
  (Enter 即确认 = 按钮原生行为; Esc 取消走退栈链)
- test_cursor_scroll_follow_without_scrollintoview: shortcuts.js 无 scrollIntoView;
  columns.js 留存 _rowPre 前缀和; 光标视觉 .kb-cursor 在共用 CSS 与三张行模板成对
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
BLACKLIST |= {"Ctrl+Tab", "Ctrl+Shift+Tab", "F5", "F11", "F12", "Ctrl+Shift+KeyN",
              "Ctrl+Shift+KeyI", "Ctrl+Shift+KeyJ", "Ctrl+Shift+KeyC"}
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
        assert not it["def"] or re.fullmatch(r"(Ctrl\+)?(Alt\+)?(Shift\+)?(Meta\+)?[A-Z][A-Za-z0-9]*", it["def"]), it["id"]
        if it["def"]:
            assert not it["def"].startswith("Meta"), f"{it['id']} 默认键用 Meta(mac Cmd 全族不可拦)"
        # 本波(W1-W4)只激活 A-D 组: 未激活条目必须 run: null, 防"注册了就活"越波次
        if it["run_null"]:
            assert not it["runs"], f"{it['id']} 声明 run: null 却带 vm 调用"
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
        assert len(parts) == 2 and parts[0] in ("Ctrl", "Alt", "Shift") and parts[1].startswith("Key"), (
            f"危险档 {k} 默认键 {v!r} 不是二键组合(修饰键+字母)"
        )
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
        assert it["def"] not in seen, (
            f"默认键 {it['def']} 被 {it['id']} 与 {seen[it['def']]} 同时占用 —— 后者被静默覆盖"
        )
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
    assert esc_chain_at >= 0 and kb_at > esc_chain_at, (
        "引擎 keydown 必须注册在 Esc 退栈链之后(注册序 = 触发序; 链序不回归是 W1 验收口径)"
    )
    assert 'document.removeEventListener("keydown", this._kbKeyDown)' in life, (
        "unmounted 必须撤掉引擎监听(防热重载句柄堆叠)"
    )


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


def test_delete_direct_outside_registry() -> None:
    for it in _registry():
        assert it["def"] != "Delete", "Delete 键不进注册表(§08 v4: 额外删除操作直连, 不占键表槽位)"
    eng = _read("shortcuts.js")
    m = re.search(r'if \(e\.code === "Delete"(.*?)\n        \}', eng, re.S)
    assert m and "_kbDelete()" in m.group(1), "引擎未直连 Delete -> _kbDelete(§08 决策 v4)"
    body = re.search(r"async _kbDelete\(\) \{(.*?)\n  \},", eng, re.S)
    assert body and "_deleteFlow(" in body.group(1), (
        "_kbDelete 必须走 _deleteFlow(与批量浮条同链: 确认框 + HR 风险点名不可绕过)"
    )


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
    assert open_at >= 0 and fb.find("this.$refs.modalOk", open_at) > open_at, (
        "_openModal 必须在无输入形态时把默认焦点落到 modalOk(Enter 即确认; Esc 取消走退栈链)"
    )


def test_cursor_scroll_follow_without_scrollintoview() -> None:
    eng = _read("shortcuts.js")
    assert ".scrollIntoView(" not in eng, (
        "光标滚动跟随禁用 scrollIntoView(逐层滚动可滚祖先会连带滚整页, "
        "pitfalls web-ui/hover-keynav-fight) —— 用 getBoundingClientRect/前缀和差值"
    )
    assert "this._rowPre" in eng and "_rowPre[kind]" in eng, (
        "窗口化未渲染行必须用 _rowWindow 留存的前缀和换算 y(计划 W2)"
    )
    cols = _read("columns.js")
    assert re.search(r"this\._rowPre\[kind\] = pre;", cols), (
        "columns.js._rowWindow 必须把前缀和留存进 this._rowPre[kind](键盘光标滚动进视口依赖)"
    )
    assert ".kb-cursor" in (SHARED / "console_hub.css").read_text(encoding="utf-8"), (
        "光标行视觉 .kb-cursor 必须在共用层 CSS(三套 UI 同载)"
    )
    for tpl, kind, idexpr in [
        ("groups.html", "group", "g.key"),
        ("torrents.html", "torrent", "m.hash"),
        ("shows.html", "show", "s.key"),
    ]:
        text = (SHARED / "tpl" / tpl).read_text(encoding="utf-8")
        assert f"'kb-cursor': isKbCursor('{kind}'" in text, f"{tpl} 缺 {kind} 行光标绑定"
    shows = (SHARED / "tpl" / "shows.html").read_text(encoding="utf-8")
    assert ':data-key="s.key"' in shows, "剧行缺 data-key(光标定位锚点, W2)"
    assert ':data-key="showEpRowId(' in shows, "集行缺 data-key(光标定位锚点, W2)"
