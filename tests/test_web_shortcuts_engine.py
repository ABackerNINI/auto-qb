"""test_web_shortcuts_engine 测试计划: 键盘快捷键守阵 (计划 26-09-28-0354 W1-W7 全波; 引擎与面板在 shared/shortcuts.js)。

守什么: 注册表是键位**单一事实源**(表外无键位), 而前端无 JS 测试框架 —— 键位冲突、黑名单
越界、危险档键位形态、run 指到不存在的方法, 这些错误全部**静默**(不报错只是键不响/误触),
只能靠静态断言钉住。挂载成对(全部皮肤(webui_helpers._UI_ALL)的 tpl-manifest + app.mixin)由本文件与 tests/webui_static_scan_js.py 的
_scan_mixin_wiring 双保险。光标滚动跟随禁 scrollIntoView、模态默认焦点/Enter 确认(§08)、
Delete 直连注册表外, 均为已拍板的口径, 逐条落断言。W5 局部作用域(drawer/settings/modal
三档 + 浮层放行焦点局部)与 W6 自定义(适配器 /api/keys / 录制器 / 冲突三选一 / 帮助浮层 /
设置页分区)逐条接线断言见下半部; 后端端点行为测试在 test_web_keys.py / test_web_route_manifest.py(GET 兜底链 / PUT 422 / 金清单)。

## 测试计划

- test_engine_input_suppression: IME 双保险 / defaultPrevented / repeat / 纯修饰键 /
  输入元素屏蔽 / Escape 早退(引擎永不接 Esc) 六道拦截齐全
- test_arrow_repeat_continuous: 长按连发只给上下键族 —— 引擎 repeat 拦截放行标记条目,
  注册表 repeat 标记恰为 cursor-up/down + extend-up/down 且 scope=list
- test_esc_chain_clear_filters_fallback: ESC 接退栈链终端兜底清面筛(计划 26-10-02-1632 方案 A) ——
  兜底在收剧展开之后(链序即退栈序, LIFO 不可倒) / 门条件五件套(authOk / page=groups /
  !hrPop.open / !inInput / facetsActive) / toast 点名不静默; Escape 仅 clear-esc 一个默认绑定
  且面板 label 点名清筛选; facetsActive 不含 searchQuery(搜索词归 clearSearch)
- test_esc_chain_search_input_blur: ESC 退出搜索框聚焦(2026-11-13 报障) —— 退焦档排在清选择
  兜底之前(输入语境优先, 第二次 Esc 才轮到列表状态) / 仅钉死 $refs.searchInput(设置页输入
  不接, 站点搜索层归 hubOnKey) / IME 双保险(组词中 Esc 只取消组词不退焦) / 档内无 clearSearch
  (搜索词归 clearSearch, Esc 只退焦) / 面板 label 点名退出搜索框
"""

from __future__ import annotations

import re

from pathlib import Path

from auto_qb.webui.server.routes.keys import _KEYS_SERIAL_RE as KB_DEF_RE

from web_shortcuts_support import (
    SHARED,
    _pick,
    _read,
    _registry,
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


def test_esc_chain_search_input_blur() -> None:
    """ESC 退出搜索框聚焦(2026-11-13 报障): 浮层名单走空后焦点在顶栏搜索框 -> blur 退焦。

    钉四件事: 分支序(退焦档必须在清选择兜底之前 —— 打字中按 Esc 是"离开输入框", 不许先动
    列表状态) / 仅钉死顶栏搜索框(设置页输入框不接) / IME 双保险(组词中 Esc 归输入法) /
    档内不清词(搜索词归 clearSearch)。"""
    lc = _read("lifecycle.js")
    blur_at = lc.index("inputEl.blur()")
    assert lc.count("inputEl.blur()") == 1, "退焦档只许一个调用位(其余输入面各有自己的 Esc 路径)"
    assert blur_at < lc.index("this.selGroups.length || this.selMembers.length) this.clearSelection()"), \
        "退出搜索框档必须排在清选择兜底之前(链序即优先序, 输入语境优先)"
    assert "inputEl === this.$refs.searchInput" in lc, "退焦档必须钉死顶栏搜索框, 不得泛化到全部输入"
    branch_start = lc.rindex("else if", 0, blur_at)
    branch = lc[branch_start:blur_at + len("inputEl.blur()")]
    assert "e.isComposing || e.keyCode === 229" in branch, "退焦档必须带 IME 双保险(组词中 Esc 只取消组词)"
    assert "clearSearch" not in branch, "退焦档不得清搜索词(词归 clearSearch, Esc 只退焦)"
    sc = _read("shortcuts.js")
    assert "退出搜索框" in sc, "clear-esc 面板 label 必须点名退出搜索框(行为新增要进面板文案)"
