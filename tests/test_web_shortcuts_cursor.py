"""test_web_shortcuts_cursor 测试计划: 键盘快捷键守阵 (计划 26-09-28-0354 W1-W7 全波; 引擎与面板在 shared/shortcuts.js)。

守什么: 注册表是键位**单一事实源**(表外无键位), 而前端无 JS 测试框架 —— 键位冲突、黑名单
越界、危险档键位形态、run 指到不存在的方法, 这些错误全部**静默**(不报错只是键不响/误触),
只能靠静态断言钉住。挂载成对(三份 tpl-manifest + app.mixin)由本文件与 test_webui_static_skins.py 的
_scan_mixin_wiring 双保险。光标滚动跟随禁 scrollIntoView、模态默认焦点/Enter 确认(§08)、
Delete 直连注册表外, 均为已拍板的口径, 逐条落断言。W5 局部作用域(drawer/settings/modal
三档 + 浮层放行焦点局部)与 W6 自定义(适配器 /api/keys / 录制器 / 冲突三选一 / 帮助浮层 /
设置页分区)逐条接线断言见下半部; 后端端点行为测试在 test_web_keys.py / test_web_route_manifest.py(GET 兜底链 / PUT 422 / 金清单)。

## 测试计划

- test_cursor_scroll_follow_without_scrollintoview: shortcuts.js 无 scrollIntoView;
  columns.js 留存 _rowPre 前缀和; 光标视觉 .kb-cursor 在共用 CSS 与五处行模板成对
- test_click_lands_cursor_and_viewport_fallback: 键鼠衔接(报告 26-09-30-1806 方案 B) ——
  selection.js 五点击入口按所在行回写 kbCursor(写在修饰键分支之前, Ctrl/Shift 点击同样落光标);
  _kbMove 无光标回落走 _kbViewportRow(前缀和同源校验 / 渲染行可见性扫描, 解析失败退回旧口径)
- test_shift_anchor_unified: 起点统一(计划 26-10-02-0608 方案 B) —— 五点击入口普通/Ctrl 路径落
  起点且排除 Shift(法则 2); 四处消费者走 _selAnchor 单点解析、无裸 list[0]; _selAnchor 兜底链
  齐全(显式 -> 光标 -> 展开组 -> 首行); _selSetAnchor 不碰选中集合; _kbExtend 先落手势原点
  (_selSeedAnchorFromCursor) 再移动光标, 且已有有效起点不动; 2026-10-19: 五入口 Shift 分支前
  先 _selSeedAnchorFromCursor 再改写 kbCursor(修 Esc 清选择后再次 Shift 连选塌成单行), 落点
  逐 kind(group/member/unit)覆盖
- test_kb_member_range_context_aware: 成员行范围选择随视图取范围(2026-10-09) —— _memberRangeList
  按 viewMode 分流(种子页平铺 / 辅种页展开组 / 追剧页展开集), shiftMemberSel 吃它, _kbExtend 的
  torrent 分支不再一律 shiftTorrentSel(辅种/追剧页成员行 Shift+↑↓ 曾选不中)
- test_kb_collapse_parent_row: 成员行 ← 收起所属单元(2026-10-09) —— _kbCollapseRow 增成员行分支
  (原只认 group/show/ep, 光标按 ↓ 进展开组/展开集后 ← 静默无反应), 父行解析单点 _kbParentRow
  复用 _memberRangeList(与渲染同源, 防错位), 收起后光标带回父行(成员行随收起消失)
- test_sel_group_member_linkage: 组 <-> 成员双向联动(2026-10-09 用户拍板, 取代 FX-11 互斥) ——
  单一写入口 _selAddGroup/_selDropGroup(组选中 = 组 key 与成员 hash 一起写入) + 成员侧回扫
  _selSyncGroups(组内成员全选 => 组入选, 撤到不全 => 组移出); 成员侧五个变更点全部回扫;
  groupSelState 按成员完整度派生 selected(视觉兜底; 2026-10-31 计划 26-10-30-2359 模板C 起
  直通 _selState 多带 ratio 供半选左条按高度量化) / selectedCount 走 selHashSet 去重(组 key
  与其成员 hash 同时在集合里, 直接相加会数两遍) / _bulkTargets 剔除已被选中组覆盖的成员 hash
- test_sel_visual_parity_and_site_cell: 成员行选中视觉与种子页种子行同形(三皮肤 CSS 成对:
  .member-row.selected 与 .group-row.selected 同一 tint 令牌(`--sel-bg`)且同吃左色条规则; 两条规则
  自 2026-10-20 拆分 —— 组行有吸左首格须合成在不透明 `--bg-row` 上(frozen-column ⑩), 成员行无首格
  保持裸柔底) + 成员行「站点」列去掉代表状态的
  方框(groups.html / shows.html 两处模板无 <i class="dot"> + 三皮肤无 .m-site .dot 死规则)
- test_esc_collapse_returns_cursor_to_parent: Esc 收展开兜底档把键盘光标**退回被收起的父行**
  (2026-10-22 用户报「Esc 退出明细表后键盘锚点消失」) —— 三档(expandedKey→group /
  expandedShowEp→ep / expandedShows→show)各自归位, 就地赋值不调 _kbCollapseRow(退栈链不反向
  依赖引擎), 多剧展开选支走 _kbParseEpId 单点; 清选择仍先于收展开(一次按键只退一层)
- test_kb_view_band_single_points: 滚动跟随上下可见边界单点(2026-10-09 用户报: 键盘移到
  第一个/最后一个种子只显示一半) —— 上界 _kbViewTop(顶栏 --head-h + 吸顶列头 .group-head,
  列头吸在顶栏下缘、盖住列表首行; 未吸顶/不在 DOM 回落顶栏高) / 下界 _kbViewBottom 补
  固定状态栏(--statusbar-h, 落点「视口底 - 8px」会停进状态栏背后); _kbViewportRow 与
  _kbScrollRowIntoView(渲染行 + 窗口化两路)三处消费, 上界不得再裸写 _headH
"""

from __future__ import annotations

from webui_helpers import read_shared

import re

from pathlib import Path

from auto_qb.webui.server.routes.keys import _KEYS_SERIAL_RE as KB_DEF_RE

from web_shortcuts_support import (
    SHARED,
    STATIC,
    UIS,
    _read,
)


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
    assert ".kb-cursor" in read_shared("console_hub.css"), ("光标行视觉 .kb-cursor 必须在共用层 CSS(三套 UI 同载)")
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
    键盘 Shift 手势原点先于移动光标(否则区间塌成单行, G2)。
    2026-10-19 收编鼠标路径(用户报障: Shift 连选后 Esc 清选择, 光标在最后选中的种子, 但再次
    Shift 连选不以光标为起点): 五入口在改写 kbCursor 之前先 _selSeedAnchorFromCursor(手势前
    光标落起点), 落点逐 kind(group/member/unit)覆盖 —— 辅种页成员行的光标只解析得出 member
    kind(_selContext 只回当前视图主 kind, 辅种页恒为 group, 单 kind 落点覆盖不到)。"""
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
    # ①b 鼠标 Shift 分支前先落手势原点(2026-10-19 报障: Esc 清选择后再次 Shift 连选塌成单行):
    #    五入口必须先 _selSeedAnchorFromCursor() 再改写 kbCursor —— 顺序反了 _selAnchor 兜底链的
    #    「当前光标」一环读到的是刚点的行, 区间塌成单行(不以光标为起点)
    for fn in ("onGroupClick", "onMemberClick", "onTorrentClick", "onShowClick", "onShowEpClick"):
        m = re.search(rf"{fn}\([^)]*\) \{{(.*?)\n    \}},", sel, re.S)
        assert m, f"selection.js 找不到 {fn}"
        body = m.group(1)
        seed_at = body.find("_selSeedAnchorFromCursor()")
        cursor_at = body.find("this.kbCursor =")
        assert seed_at >= 0, f"{fn} 缺手势前落起点(Shift 分支前必须调 _selSeedAnchorFromCursor)"
        assert 0 <= seed_at < cursor_at, (f"{fn} 必须先落起点再改写光标(顺序反了区间塌成单行: Esc 后 Shift 连选不以光标为起点)")
        seed_line = next(ln for ln in body.splitlines() if "_selSeedAnchorFromCursor" in ln)
        assert "event.shiftKey" in seed_line, (f"{fn} 手势前落起点必须限 Shift(普通/Ctrl 路径由 _selSetAnchor 显式落起点)")
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
    # ④b 手势原点落点必须逐 kind 覆盖(2026-10-19): 辅种页成员行的光标只解析得出 member kind
    #  (_selContext 只回当前视图主 kind, 辅种页恒为 group, 单 kind 落点覆盖不到 => 成员行
    #  Shift 手势取不到原点, 区间塌成单行); 鼠标五入口同样吃本方法(改写 kbCursor 之前)
    assert "_memberRangeList()" in seedb, ("_selSeedAnchorFromCursor 必须覆盖 member kind(辅种页成员行 Shift 手势取不到原点)")
    assert "_kbShowUnits()" in seedb, "_selSeedAnchorFromCursor 必须覆盖 unit kind(追剧页剧/集行)"
    assert 'this.page !== "groups"' in seedb, "手势原点落点仅数据页(设置页无选择上下文)"


def test_kb_member_range_context_aware() -> None:
    """成员行范围选择随视图取范围(2026-10-09): 辅种页/追剧页的成员行(展开组 / 展开集)键盘
    Shift+↑↓ 必须能选中。范围单点 _memberRangeList 按 viewMode 分流(种子页平铺 / 辅种页展开组 /
    追剧页展开集); _kbExtend 的 torrent 分支走它 —— 不再一律 shiftTorrentSel(后者只看种子页
    平铺列表, 在辅种/追剧页该列表为空或无关 ⇒ 范围选不中任何成员)。"""
    sel = _read("selection.js")
    m = re.search(r"_memberRangeList\(\) \{(.*?)\n    \},", sel, re.S)
    assert m, "selection.js 找不到 _memberRangeList(成员行范围单点)"
    body = m.group(1)
    for needle, why in [
        ('this.viewMode === "torrents"', "缺种子页分支(平铺行范围)"),
        ('this.viewMode === "shows"', "缺追剧页分支(展开集版本范围)"),
        ("this.expandedShowEp", "追剧页分支必须按展开的集取成员(否则集明细行范围选不中)"),
        ("this.expandedKey", "辅种页分支必须按展开的组取成员"),
        ("memberHashesOf", "取 hash 必须经 memberHashesOf 单点(裸取对象 hash 会字符串化成 [object Object])"),
        ("sortedMembers", "范围取序必须与 _kbRows / winMembers 同源(屏幕上下 = 选择上下)"),
    ]:
        assert needle in body, f"_memberRangeList {why}"
    # shiftMemberSel 必须吃范围单点(不再自建 filteredGroups.find 分支 —— 追剧页 expandedKey 恒空会落空)
    sm = re.search(r"shiftMemberSel\(m\) \{(.*?)\n    \},", sel, re.S)
    assert sm and "_memberRangeList()" in sm.group(1), "shiftMemberSel 必须走 _memberRangeList 范围单点"
    assert "this.filteredGroups.find" not in sm.group(1), "shiftMemberSel 不得再硬编码辅种页分支"
    # 键盘扩展落点: torrent 分支走 shiftMemberSel(随视图), 不得再一律 shiftTorrentSel
    eng = _read("shortcuts.js")
    ext = re.search(r"_kbExtend\(delta\) \{(.*?)\n    \},", eng, re.S)
    assert ext, "shortcuts.js 找不到 _kbExtend"
    eb = ext.group(1)
    assert "this.shiftMemberSel({ hash: c.id })" in eb, (
        "_kbExtend 的 torrent 分支必须走 shiftMemberSel(随视图取范围) —— 否则辅种/追剧页成员行 Shift+↑↓ 选不中"
    )
    assert "this.shiftTorrentSel({ hash: c.id })" not in eb, ("_kbExtend 不得再一律走 shiftTorrentSel(只看种子页平铺列表, 辅种/追剧页范围落空)")


def test_kb_collapse_parent_row() -> None:
    """成员行 ← 收起所属单元(2026-10-09 用户报: 光标进组后 ← 静默无反应)。

    _kbCollapseRow 原只认 group/show/ep 三种 kind; 成员行(kind=torrent)落空 —— 键盘按 ↓ 进
    展开组/展开集后, ← 收不起任何东西(不报错, 纯"按了没反应")。修法 = 成员行分支收起**所属
    单元**并把光标带回其行; 父行解析单点 _kbParentRow(判据复用 selection.js::_memberRangeList,
    与 _kbRows 渲染同源)。本守阵钉"分支在不在 / 走没走单点 / 光标有没有带回父行"。"""
    eng = _read("shortcuts.js")
    col = re.search(r"_kbCollapseRow\(\) \{(.*?)\n    \},", eng, re.S)
    assert col, "shortcuts.js 找不到 _kbCollapseRow(← 收起当前行的落点)"
    cb = col.group(1)
    at = cb.find('c.kind !== "torrent"')
    assert at >= 0, "缺成员行分支 —— 光标进展开组/展开集后 ← 会静默无反应(用户 2026-10-09 报)"
    tb = cb[at:]
    assert "this._kbParentRow(c)" in tb, "_kbCollapseRow 的成员行分支必须走父行解析单点 _kbParentRow"
    assert "this.expandedKey = null" in tb and "this.expandedShowEp = null" in tb, (
        "成员行 ← 必须真收起所属单元(清 expandedKey / expandedShowEp), 不能只移动光标"
    )
    assert "this._kbApplyCursor(rows, idx)" in tb or "this.kbCursor = p" in tb, ("收起所属单元后必须把光标带回父行(成员行随收起消失, 光标不能留在链外)")
    parent = re.search(r"_kbParentRow\(c\) \{(.*?)\n    \},", eng, re.S)
    assert parent, "shortcuts.js 缺 _kbParentRow(成员行所属行解析单点)"
    pb = parent.group(1)
    for needle, why in [
        ('c.kind !== "torrent"', "必须只对成员行生效(组/剧/集行走各自分支)"),
        ('this.viewMode === "torrents"', "种子页平铺行无父行, 必须返回 null"),
        ("this._memberRangeList()", "父行判据必须复用成员链单点(与渲染同源, 防收起目标错位)"),
        ("this.expandedShowEp", "追剧页父行 = 展开的集行"),
        ("this.expandedKey", "辅种页父行 = 展开的组行"),
    ]:
        assert needle in pb, f"_kbParentRow {why}"


def test_esc_collapse_returns_cursor_to_parent() -> None:
    """Esc 收展开兜底档把键盘光标退回被收起的父行(2026-10-22 用户报「Esc 退出明细表后键盘
    锚点消失」): 明细行随收起一起卸载, 光标却仍指着链外 hash => 虚线框被宿主连坐带走, 下一次
    ↑↓ 还要走无光标回落(_kbViewportRow)重猜落点。三档(group / ep / show)各自归位, 且退栈链
    就地赋值不反向依赖快捷键引擎; 清选择仍先于收展开(一次按键只退一层)"""
    lc = _read("lifecycle.js")
    m = re.search(r'if \(e\.key !== "Escape"\) return;(.*?)\n    \}\);', lc, re.S)
    assert m, "lifecycle.js 找不到 Esc 退栈链(结构变了? 同步本守阵)"
    chain = m.group(1)
    branches = chain.split("else if (")

    def branch(tok: str) -> str:
        hit = [b for b in branches if tok in b]
        assert hit, f"Esc 退栈链缺收起分支: {tok}"
        return hit[0]

    for tok, field, kind in (
        ("this.expandedKey", "expandedKey", "group"),
        ("this.expandedShowEp", "expandedShowEp", "ep"),
        ("this.expandedShows.length", "expandedShows", "show"),
    ):
        b = branch(tok)
        assert f"{field} = null" in b or f"{field} = []" in b, f"{field} 收起分支未复位展开态"
        assert f'this.kbCursor = {{ kind: "{kind}"' in b, (
            f"收起分支必须把光标退回父行({field} -> kind={kind}): 明细行随收起消失, "
            "光标悬空在链外 = 用户看到的「锚点没了」"
        )
    assert "this._kbCollapseRow(" not in chain, (
        "Esc 退栈链不得反向调用快捷键引擎方法(就地赋值 —— 链序由注册序守阵, 不被引擎牵动; "
        "注释里点名 _kbCollapseRow 说明同口径是允许的, 这里只禁真调用)"
    )
    assert chain.index("this.clearSelection()") < chain.index("this.expandedKey"), \
        "清选择必须先于收展开(一次按键只退一层, 有选中时 Esc 不动光标也不收展开)"
    # 剧可多支同时展开: 归位走 _kbParseEpId 单点解析所属剧(不手抄 ep id 形态), 优先光标所在那一支
    assert "_kbParseEpId" in branch("this.expandedShows.length"), \
        "多剧展开归位必须走 _kbParseEpId 单点(光标在哪个剧的集行上就退回哪个剧, 不横跳到首支)"


def test_kb_view_band_single_points() -> None:
    """键盘滚动跟随的上下可见边界单点(2026-10-09 用户报: 键盘移到第一个/最后一个种子只显示一半)。

    这两处此前都把「几何在视口内」当成「看得见」: 上界只算顶栏高 --head-h, 忽略吸在顶栏下缘的
    吸顶列头 .group-head(实测盖住首行 23px / 行高 71px, 矮行过半); 下界只取 window.innerHeight,
    忽略底部固定状态栏(落点「视口底 - 8px」把末行停进状态栏背后, 实测遮 26px / 行高 50px)。
    真机取证: scrollY=40 时首行 rect.top=103 < 列头 bottom=126; 末行 bottom=892 > 状态栏 top=866。
    静态守阵只能钉「单点在且被消费、边界算式不许再裸写」, 几何正确性归 e2e 真浏览器断言
    (tests/test_web_shortcuts.py 的既有口径: 静态全绿而真机必红的教训见 pitfalls/dock-panel)。

    2026-10-09 第三轮(坐标系口径): 单点返回的是**视口坐标**(与 getBoundingClientRect 同源),
    而无光标回落(_kbViewportRow)的渲染行扫描曾把 window.scrollY 混进上/下界, 拿文档坐标去比
    视口坐标的 rect —— 仅 scrollY=0 时成立, 滚过一屏后渲染行全判「出视口」, 回落退化成跳极值行
    (实测 1440x900 追剧页 scrollY=1500: ↓ 期望首可见行实落 row 0)。此处钉死两套坐标的边界:
    vTop/vBot 必须是单点裸值(不加 scrollY), 前缀和分支(文档坐标)比较时加回 sy, 渲染行 rect 与
    vTopM/vBotM(视口坐标)比。几何正确性仍归 e2e kbd-scroll-band.spec.mjs 的新测例。
    """
    eng = _read("shortcuts.js")
    # --- 上界单点: 顶栏 + 吸顶列头 ---
    vt = re.search(r"_kbViewTop\(\) \{(.*?)\n    \},", eng, re.S)
    assert vt, "shortcuts.js 缺 _kbViewTop(行可见上界单点, 与 _kbViewBottom 对称)"
    vtb = vt.group(1)
    assert "_headH" in vtb, "上界必须含顶栏实测高(--head-h 由 columns.js 写入, 值不写死)"
    assert 'document.querySelector(".group-head")' in vtb, "上界必须实测吸顶列头(它吸在顶栏下缘, 盖住列表首行)"
    assert 'getComputedStyle(hd).position !== "sticky"' in vtb, "列头不在 DOM / 未吸顶必须回落顶栏高(无表头列表不无脑加高度)"
    assert "getBoundingClientRect().height" in vtb, "列头高按自身高度复算(吸顶前后 rect 在两态间跳, 只有高度恒定)"
    # --- 下界单点补状态栏(在面板让位之前取更紧者) ---
    vb = re.search(r"_kbViewBottom\(\) \{(.*?)\n    \},", eng, re.S)
    assert vb, "shortcuts.js 缺 _kbViewBottom(行可见下界单点)"
    vbb = vb.group(1)
    assert 'document.querySelector(".statusbar")' in vbb, "下界必须让位底部固定状态栏(末行停进状态栏背后 = 用户报障)"
    assert 'getComputedStyle(sb).position === "fixed"' in vbb, "状态栏让位前必须实测 position:fixed(非固定态不参与让位)"
    assert "Math.min(bot, sbr.top)" in vbb, "下界 = 状态栏顶缘与其它遮蔽(面板)取更紧者"
    assert vbb.index("statusbar") < vbb.index("this.drawer.open"), "状态栏让位在面板让位之前(面板在其上方, 更紧者仍会被 min 取到)"
    # --- 三处消费: 上界走单点, 下界仍是 _kbViewBottom ---
    vp = re.search(r"_kbViewportRow\(rows, delta\) \{(.*?)\n    \},", eng, re.S)
    assert vp, "shortcuts.js 缺 _kbViewportRow"
    vpb = vp.group(1)
    assert "this._kbViewTop()" in vpb, "无光标回落的上界必须走 _kbViewTop(列头盖住首行)"
    assert "this._kbViewBottom()" in vpb, "_kbViewportRow 下界必须走 _kbViewBottom(状态栏 + 面板)"
    # --- 坐标系口径(2026-10-09 修坐标错位): 渲染行 rect 是**视口坐标**, 前缀和 y 是**文档坐标** ---
    # vTop/vBot 必须是单点**裸值**(视口坐标), 不得再叠 window.scrollY —— 旧码 `vTop = scrollY + 单点 + 4`
    # 只在 scrollY=0 时成立, 滚过一屏后所有渲染行都被判「出视口」, 无光标回落退化成跳极值行。
    assert re.search(r"const vTop = this\._kbViewTop\(\);",
                     vpb), ("_kbViewportRow 的 vTop 必须是单点裸值(视口坐标, 与 getBoundingClientRect 同源)")
    assert re.search(r"const vBot = this\._kbViewBottom\(\);", vpb), ("_kbViewportRow 的 vBot 必须是单点裸值(视口坐标)")
    assert vpb.count("window.scrollY") == 1 and "const sy = window.scrollY;" in vpb, (
        "window.scrollY 只经 sy 单点取一次(渲染行 rect 混入 scrollY 即坐标错位)"
    )
    # 前缀和分支(y 文档坐标)比较时加回 sy; 渲染行 rect(视口坐标)直接比 vTopM/vBotM
    assert re.search(r"pre\[i \+ 1\] \+ top > sy \+ vTop \+ 4",
                     vpb) and re.search(r"pre\[i\] \+ top < sy \+ vBot - 4", vpb), "窗口化前缀和(文档坐标)比较必须加回 sy"
    assert "const vTopM = vTop + 4;" in vpb and "const vBotM = vBot - 4;" in vpb, ("渲染行可见带上下界由单点裸值加余量得出(vTopM/vBotM)")
    assert re.search(r"rect\.bottom <= vTopM \|\| rect\.top >= vBotM",
                     vpb), ("渲染行 rect 必须与视口坐标(vTopM / vBotM)比较 —— 与文档坐标比即坐标错位")
    si = re.search(r"_kbScrollRowIntoView\(rows, idx\) \{(.*?)\n    \},", eng, re.S)
    assert si, "shortcuts.js 缺 _kbScrollRowIntoView"
    sib = si.group(1)
    assert sib.count("this._kbViewTop()") == 1 and sib.count("vTop + 4") == 2, (
        "_kbScrollRowIntoView 上界两路(渲染行 rect + 窗口化前缀和 y)都要用 _kbViewTop 的落值"
    )
    assert "this._kbViewBottom()" in sib, "_kbScrollRowIntoView 下界必须走 _kbViewBottom(渲染行与窗口化两路)"
    assert "_headH" not in sib, "_kbScrollRowIntoView 不得再裸写 _headH 当上界(单点外零算式)"
    assert sib.count("window.innerHeight") == 0, "_kbScrollRowIntoView 不得裸用 window.innerHeight 当下界"
    # --- PageUp / PageDown 的「一屏」: 按可见带算, 不得再用整窗高(2026-10-09 收口) ---
    mp = re.search(r"_kbMovePage\(dir\) \{(.*?)\n    \},", eng, re.S)
    assert mp, "shortcuts.js 缺 _kbMovePage"
    mpb = mp.group(1)
    assert "this._kbViewBottom()" in mpb and "this._kbViewTop()" in mpb, (
        "一屏行数必须按**可见带**算(顶栏 + 吸顶列头 … 状态栏 / 停靠面板): 用整窗高会让面板开着时每屏跳过一半行"
    )
    assert re.search(r"const per = Math\.max\(1, Math\.floor\(band / est\)\);",
                     mpb), ("一屏行数算式必须由可见带得出(per = floor(band / est))")
    assert "_winViewH" not in mpb, "_kbMovePage 不得再用 _winViewH(整窗高)当可见带"
    assert "innerHeight" not in mpb, "_kbMovePage 不得再裸用 innerHeight 当可见带"


def test_sel_group_member_linkage() -> None:
    """组 <-> 成员选中双向联动(2026-10-09 用户拍板, 取代 FX-11 的"组/成员互斥")。

    口径: **一个组被选中 <=> 该组全部成员被选中**, 两个方向都要真改写选中数据(不是只改 CSS):
      · 组选中 -> 成员全选: _selAddGroup 把组 key 与全部成员 hash 一起写进选中集合;
      · 成员全选 -> 组入选: _selSyncGroups 按当前 selMembers 回扫, 全在则补组 key、不全则移出。
    落点用同一套写入口; 成员侧五个变更点(toggleMemberSel / shiftMemberSel / shiftTorrentSel /
    _toggleUnit / _extendUnit)都必须回扫。FX-11 时代的"清另一侧"写法必须清干净 —— 它会把联动
    打断(选种子时把已选中的组整段抹掉)。本守阵钉"单点在不在 / 变更点吃没吃 / 消费端去不去重"。"""
    sel = _read("selection.js")

    # ① 单一写入口三件套
    for fn, needle, why in [
        ("_groupHashes", "memberHashesOf", "取 hash 必须经 memberHashesOf 单点(裸取会字符串化)"),
        ("_selAddGroup", "this.selGroups = [...this.selGroups, k]", "组 key 必须写入"),
        ("_selAddGroup", "this.selMembers", "成员 hash 必须一并写入(组选中 => 成员全选)"),
        ("_selDropGroup", "this.selGroups.filter", "组 key 必须撤出"),
        ("_selDropGroup", "this.selMembers.filter", "成员 hash 必须一并撤出(否则残留孤儿选中)"),
        ("_selSyncGroups", "this.decoratedGroups", "回扫必须遍历已知组(groups 按视图回传, 无组数据时自然 no-op)"),
        ("_selSyncGroups", "hashes.every", "成员全在才补组 key(不全 => 组移出)"),
    ]:
        m = re.search(rf"{fn}\([^)]*\) \{{(.*?)\n    \}},", sel, re.S)
        assert m, f"selection.js 找不到 {fn}(双向联动写入口被改名/搬走? 同步本守阵)"
        assert needle in m.group(1), f"{fn} {why}"

    # ② 组侧入口吃单点(toggleGroupSel/shiftGroupSel 不得再手写 selGroups/selMembers)
    for fn in ("toggleGroupSel", "shiftGroupSel"):
        m = re.search(rf"{fn}\([^)]*\) \{{(.*?)\n    \}},", sel, re.S)
        assert m, f"selection.js 找不到 {fn}"
        body = m.group(1)
        assert "this._selAddGroup(" in body, f"{fn} 必须经 _selAddGroup 写入(口径单点)"
        assert "this.selMembers = []" not in body, (f"{fn} 不得再清空 selMembers(FX-11 互斥清理已退役, 会打断组->成员联动)")
    toggle = re.search(r"toggleGroupSel\(g\) \{(.*?)\n    \},", sel, re.S).group(1)
    assert "this._selDropGroup(g.key)" in toggle, "toggleGroupSel 取消侧必须走 _selDropGroup(成员一并撤出)"

    # ③ 成员侧变更点全部回扫(成员全选 => 组入选)
    for fn in ("toggleMemberSel", "shiftMemberSel", "shiftTorrentSel", "_toggleUnit", "_extendUnit"):
        m = re.search(rf"{fn}\([^)]*\) \{{(.*?)\n    \}},", sel, re.S)
        assert m, f"selection.js 找不到 {fn}"
        body = m.group(1)
        assert "this._selSyncGroups()" in body, f"{fn} 缺 _selSyncGroups 回扫(成员全选 => 组入选 断链)"
        assert "this.selGroups = []" not in body, f"{fn} 不得再清空 selGroups(会打断成员->组联动)"

    # ④ 消费端
    gst = re.search(r"groupSelState\(g\) \{(.*?)\n    \},", sel, re.S)
    assert gst, "selection.js 找不到 groupSelState(组行选中态)"
    gb = gst.group(1)
    # 2026-10-31(计划 26-10-30-2359 模板C): groupSelState 直通 _selState(返回多带 ratio,
    # 按成员完整度派生 selected 的口径不变) —— 守阵 needle 跟着搬家, 语义不变
    assert "return this._selState(this._groupHashes(g));" in gb, (
        "groupSelState 必须按成员完整度派生 selected(组内全选 => 组显示选中, 视觉兜底)"
    )
    cnt = re.search(r"selectedCount\(\) \{(.*?)\n    \},", sel, re.S)
    assert cnt and "this.selHashSet.size" in cnt.group(1), (
        "selectedCount 必须走 selHashSet 去重(联动下组 key 与其成员 hash 同时在集合里)"
    )
    bulk = _read("commands.js")
    m = re.search(r"_bulkTargets\(\) \{(.*?)\n    \},", bulk, re.S)
    assert m, "commands.js 找不到 _bulkTargets(批量目标拆解单点)"
    # 2026-10-10(S3): _bulkTargets 退化为 _scopeResolve("sel") 的形状投影, 覆盖剔除逻辑
    # 收进 selection.js::_selExpandGroups 单点 —— 守阵跟着搬家, 语义不变(剔除覆盖成员)
    assert '_scopeResolve("sel")' in m.group(1), "_bulkTargets 必须委托作用域单点 _scopeResolve(口径收敛, 计划 26-10-10-2001 S3)"
    selx = re.search(r"_selExpandGroups\(groupKeys, bag\) \{(.*?)\n    \},", sel, re.S)
    assert selx and "covered" in selx.group(1), (
        "覆盖剔除(已被选中组覆盖的成员 hash 不再发成员命令)必须落在 _selExpandGroups 单点 —— 否则同一目标既发组命令又发成员命令"
    )
    # 组行模板绑定 selected/partial 都吃 groupSelState(两态同源)
    groups_tpl = (SHARED / "tpl" / "groups.html").read_text(encoding="utf-8")
    assert "selected: groupSelState(g).selected" in groups_tpl, "组行模板缺 selected 绑定"


def test_sel_visual_parity_and_site_cell() -> None:
    """成员行选中视觉与种子页同形 + 「站点」列去方框(2026-10-09 用户要求)。

    种子页种子行是 .group-row.torrent-row -> 选中态吃 .group-row.selected(柔底 + 左色条);
    辅种/追剧页成员行是 .member-row -> 此前只有柔底没有左色条, 与种子页选中种子长得不一样。
    本守阵钉: 三皮肤里 .member-row.selected 与 .group-row.selected **用同一个 tint 令牌**
    (`var(--sel-bg, var(--accent-soft))`, 各写一份色值会随主题漂移)且同吃左色条规则;
    两条规则自 2026-10-20 起**拆开写**(组行有吸左首格, 底色要合成在不透明 --bg-row 上;
    成员行没有首格、底由明细面板承光, 保持裸柔底 —— 见 pitfalls/web-ui/frozen-column.md ⑩),
    故这里不再要求“选择器并列同一条规则”。另钉 .member-row 保持 position: relative(左色条 ::before
    的定位前提)。
    「站点」列: 成员行站点格只剩站点名文本(状态由「状态」列表达), 渲染器与三皮肤都不得再挂
    <i class="dot"> / 残留 .m-site .dot 死规则。"""
    for ui in UIS:
        views = (STATIC / ui / "css" / "views.css").read_text(encoding="utf-8")
        # 成员行选中与组行/种子行**同一 tint 令牌**(2026-10-20 起两条规则拆开: 组行/种子行有吸左
        # 首格, 底色必须合成在不透明 --bg-row 上(否则选中行名称列成异色竖带, 见
        # pitfalls/web-ui/frozen-column.md ⑩); 成员行没有首格、承光底是明细面板 .detail
        # (--bg-sunken), 保持裸柔底。钉的是「同一令牌 + 同一形状」, 不是「同一条规则文本」。)
        row_sel = re.search(r"\.group-row\.selected \{([^}]*)\}", views)
        mem_sel = re.search(r"\.member-row\.selected \{([^}]*)\}", views)
        assert row_sel and mem_sel, (
            f"{ui}: 选中底色规则要组行/成员行各一条(.group-row.selected 有吸左首格要合成、"
            ".member-row.selected 保持裸柔底) —— 成员行与种子页选中同视觉靠同一 tint 令牌"
        )
        for body, sel in ((row_sel.group(1), ".group-row.selected"), (mem_sel.group(1), ".member-row.selected")):
            assert "var(--sel-bg, var(--accent-soft))" in body, (
                f"{ui}: {sel} 未用选中态令牌族 --sel-bg —— "
                "两侧各写一份色值会随主题漂移(与种子页选中分家)"
            )
        assert re.search(r"\.group-row\.selected::before, \.member-row\.selected::before \{",
                         views), (f"{ui}: 成员行选中必须同吃左色条规则(与种子页选中种子同形)")
        assert re.search(r"\.member-row \{[^}]*position: relative",
                         views), (f"{ui}: .member-row 缺 position: relative(左色条 ::before 没有定位锚)")
        # .m-site .dot 死规则三皮肤分别落在 views.css / components.css, 两处都不许残留
        # (正则只认"选择器 + 开花括号"的规则行, 注释里提到该选择器不算)
        for css_name in ("views.css", "components.css"):
            cssp = STATIC / ui / "css" / css_name
            if not cssp.exists():
                continue
            css = cssp.read_text(encoding="utf-8")
            assert not re.search(r"^\s*\.m-site[^{\n]*\.dot[^{\n]*\{", css,
                                 re.M), (f"{ui}/{css_name}: 残留 .m-site .dot 死规则(站点列方框已移除, 别再挂回来)")
    # 成员行站点格自计划 26-10-11-1722 P2 起收敛为**单份渲染器** <aq-member-cells>(模板在
    # shared/tpl/xtpl.html#tpl-aq-member-cells) —— 辅种页/追剧页共用, 故站点格只此一处;
    # 两个调用点仍必须走它(退回内联副本 = 站点格又变两份, 改一处漏一处)
    xtpl = (SHARED / "tpl" / "xtpl.html").read_text(encoding="utf-8")
    seg = re.search(r"col\.key === 'site'\"[^>]*>", xtpl)
    assert seg, "shared/tpl/xtpl.html: 找不到成员行站点格模板(列分支被改名? 同步本守阵)"
    assert '<i class="dot">' not in seg.group(0), (
        "shared/tpl/xtpl.html: 成员行站点格不得再挂状态方框 <i class=\"dot\">(2026-10-09 用户要求移除)"
    )
    for name in ("groups.html", "shows.html"):
        tpl = (SHARED / "tpl" / name).read_text(encoding="utf-8")
        assert "<aq-member-cells" in tpl, (f"{name}: 明细成员单元格必须走单份渲染器 <aq-member-cells>(P2 收敛; 退回内联副本 = 站点格两份漂移)")
