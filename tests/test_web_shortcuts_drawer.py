"""test_web_shortcuts_drawer 测试计划: 键盘快捷键守阵 (计划 26-09-28-0354 W1-W7 全波; 引擎与面板在 shared/shortcuts.js)。

守什么: 注册表是键位**单一事实源**(表外无键位), 而前端无 JS 测试框架 —— 键位冲突、黑名单
越界、危险档键位形态、run 指到不存在的方法, 这些错误全部**静默**(不报错只是键不响/误触),
只能靠静态断言钉住。挂载成对(全部皮肤(webui_helpers._UI_ALL)的 tpl-manifest + app.mixin)由本文件与 tests/webui_static_scan_js.py 的
_scan_mixin_wiring 双保险。光标滚动跟随禁 scrollIntoView、模态默认焦点/Enter 确认(§08)、
Delete 直连注册表外, 均为已拍板的口径, 逐条落断言。W5 局部作用域(drawer/settings/modal
三档 + 浮层放行焦点局部)与 W6 自定义(适配器 /api/keys / 录制器 / 冲突三选一 / 帮助浮层 /
设置页分区)逐条接线断言见下半部; 后端端点行为测试在 test_web_keys.py / test_web_route_manifest.py(GET 兜底链 / PUT 422 / 金清单)。

## 测试计划

- test_modal_default_focus_and_enter: 模态确定钮有 ref="modalOk" 且 _openModal 默认焦点落它
  (Enter 即确认 = 按钮原生行为; Esc 取消走退栈链)
- test_local_scope_wiring: settings-save inputSafe + Ctrl+KeyS + cfgSave; 引擎 _kbScope
  settings/list 档齐全(方案A W2 起停靠面板不再是作用域, drawer 值机制留位);
  浮层打开只放行焦点局部(settings)键位; 非 inputSafe 条目不得标 inputSafe
- test_drawer_dock_keyboard_w2: 方案A W2(计划 26-10-03-0917 §2.2/§2.3/§3.2/§3.4) ——
  _kbOverlayBusy 摘 drawer.open 而 escBusy 保留(两名单职责分叉: 面板≠浮层 vs Esc 关面板);
  drawer-tab 四条 group=详情面板 / scope=list / run=_kbDrawerTab 双态(非种子页 toast 忽略 /
  开态切页只对种子形态 kind=seed 成立, 流量形态开态视同关态走 openTorrentDrawer 换形打开 ——
  流量形态 hash 恒空, 切页签会打出 /api/torrents//trackers 空 hash 404 / 关态开面板定位该页签,
  目标解析 kbCursor(torrent) 优先 + 单选种子兜底);
  跟随单点 _kbFollowDrawer 挂 _kbApplyCursor 尾部, page+kind 守卫 + 200ms 防抖 + hash 短路 +
  停稳复核; _loadDrawerTab bump 请求代际 seq 且四 fetcher 带 _drawerStale 旧响应丢弃
  (W1 计划 26-10-11-2106 起这层剥在 drawer_store.js, 守阵读该文件);
  _switchDrawerTarget 换目标走 FX-29 软切换(不清空旧数据, switching 遮罩防串显 + 按 tab 的
  待到集合全到手才落定); open/close 作废在途跟随定时器; 头部标题走 drawerTitle(memberByHash
  名优先, 不等详情); 详情加载空态只归常规页签; 四皮肤 CSS 成对(switching 遮罩 + 加载胶囊)
- test_drawer_follow_mouse_click: 鼠标路径接 §1.3 预留的同一跟随挂点 —— 种子行**普通单击**走
  _kbFollowDrawer(面板开则换目标, 200ms 防抖与 page/kind 守卫全在挂点内); Ctrl/Shift 是选择
  手势不跟随(圈选 N 行不该让面板逐行翻); 单击**不得开面板**(开面板仍归双击 / Enter / 右键
  「详情」—— 点一下就弹出 42vh 面板压掉列表, 与「列表当前行必须看得清」冲突)
- test_drawer_height_w3: 方案A W3(计划 26-10-03-0917 §2.1/§3.5/D1) —— 顶缘 grip 拖拽调高
  (pointer capture + preventDefault + 夹取 [240px, 70vh] 收口 _drawerClampHeight 纯逻辑单点,
  松手才落盘); 持久化 autoqb.ui.drawerHeight / autoqb.ui.drawerOpen 与 drawerTab 同族(try/catch);
  D1 首屏默认关闭 = drawer.open 初值 false + drawerOpen 键全 bundle 只写不回读(逐文件断言) +
  drawerHeightPx 高度记忆仍生效; 模板 grip 四 pointer 事件 / aside 内联高度绑定;
  四皮肤 CSS 成对(grip touch-action / 拖拽期禁选中 / .drawer relative)
- test_qb_traffic_shortcuts: 流量图三入口(2026-10-05) —— open-qb-traffic(Ctrl+Backslash, run
  _kbToggleQbTraffic 含切换分支; 未开走 openQbHistory 含 qbTrafficOn 门 + 未启用提示) /
  drawer-tab-traffic(Alt+Digit5, run
  _kbDrawerTab("traffic") 且方法内补流量门控: 未启用提示后忽略, 不许切到无按钮隐形页签) /
  traffic-win-prev-next(新「流量图」组, [ ], **when 条件绑定 qbTrafficActive** + run qbCycleWindow);
  引擎在 preventDefault 之前分流 when(假则不消费键位, 留给浏览器)
- test_drawer_tab_shortcuts_merge_remap: 详情面板合并页签态快捷键重排(2026-10-10 用户报
  「标签合并后没有同步修改快捷键」) —— KB_MERGE_TAB_REMAP 位次表(1=常规&内容 / 2=Tracker&用户 /
  3=流量, 4/5 停用) + _kbDrawerTab 内重排**先于**流量门控(第 3 档 remap 成 traffic 后仍过
  qbTrafficOn 门) + _kbMergeTabsOn 读 dtMergeTabsOn(与页签栏 v-if 同一判据) + 帮助浮层/设置页
  文案经 kbLabel 随态改写(静态 label 未合并时不变)
- test_shortcut_toggle_semantics: 切换语义(2026-10-09, 报告 26-10-09-1731 §03/§04) —— 6 条「适合」
  条目开/关双态: open-stats/open-history/open-qb-traffic/help-panel 的 run 指向 _kbToggle*
  (已开 ⇒ closeX, 未开 ⇒ openX); 详情面板 I 仍走 _kbOpenDrawer 但方法含「已开同目标 ⇒
  closeDrawer」; 列选择器 K 仍走 toggleColMenu(本身即切换); 引擎 KB_SELF_TOGGLE_OVERLAY
  自切换白名单(四条浮层 id -> 状态字段, 浮层开着时放行第二次按键); 切换只改键盘 run 路径,
  鼠标入口保持原语义
- test_modal_whitelist_branch: 引擎含模态白名单分流(modal 条目仅模态内响应, 模态内非模态键位一律失效)
- test_recorder_and_panel_wiring: 录制器按下即录(捕获段监听+stopPropagation) / 纯修饰键拒收 /
  Esc 取消 / 黑名单当场拒绑 / 冲突三选一(交换/覆盖对方置空/取消) / 单条与全部重置 /
  空串=显式禁用语义保留 / danger 裸键提示但允许 / 面板保存 PUT 失败本地回滚 /
  离开守卫挂 hubGo+hubBack 且未保存先确认
- test_adapter_and_backend_endpoints: AQB_KEYS.load 同步快照 / save PUT /api/keys / reload GET /
  脏数据 sanitize 兜底; keys.py 落 routes 注册表; 存储路径与 web.token 同寻址(state_file 同目录)
- test_help_overlay_wiring: help-panel run -> _kbToggleKbHelp(已开 ⇒ closeKbHelp, 未开仍走 kbOpenHelp);
  kbHelpOpen 在 state.js 根选项;
  Esc 退栈链 / escBusy / _kbOverlayBusy 三处名单同步; 帮助浮层模板(只读速查 + 前往设置链接)
- test_settings_panel_section: settings-detail 独立 'keys' 分支已删除(2026-11-03 改版并入 WebUI 卡):
  aqb:kb-full-modal 扫描锚内录制/禁用/重置/冲突三选一/保存放弃全套钮 + 覆盖层三件套(遮罩/面板/
  v-show=kbFullOpen, 默认折叠) + 折叠块头展开钮与读数(键帽串经 kbDisplayOf 走 kbShortcutDisplay
  取数单点, 计划 26-11-12-0344 S1); config_hub 只认 "webui"(旧 keys 存量值经
  HUB_VIEW_ALIAS 映射), 独立首页卡不复活; console_hub.css 有 .kb-row 样式
- test_kb_full_overlay_wiring: 键位编辑全屏覆盖层(2026-11-03 改版)接线 —— Esc 退栈链有 kbFullOpen
  分支(对话层级先于清筛选兜底), escBusy/_kbOverlayBusy 两名单同步, state.js 默认折叠不持久化;
  刷新兜底 U1-b 双脏源(cfgGuardActive = cfgDirty || kbDirtyView) + 双 watcher 传 true 重算
- test_drawer_narrow_fullscreen_w4: 方案A W4(计划 26-10-03-0917 D3 + 前波移交观察项) ——
  D3 窄屏降级四皮肤成对(≤900px 面板 fixed 全屏覆盖主区 / !important 压内联高度记忆 /
  statusbar 让位 / grip 隐藏 / 停靠基线 relative 不删 / 关闭钮保留); W4 几何走查产出
  _kbViewBottom 行可见下界单点(实测面板顶缘, fixed 全屏态回落, _kbViewportRow 与
  _kbScrollRowIntoView 两处消费且不再裸用 window.innerHeight 当下界); 轮询停靠化收口
  (5s tick 挡非种子视图, 面板不可见即不拉)
- test_drawer_open_reveal_row: 显式打开路径行让位(2026-10-03 报障: 双击列表末尾几行,
  停靠面板一开把被点行盖住; W4 下界单点只接了键盘跟随; 2026-10-04 回归: 开场量的
  是 loading 态几何且文档底 scrollBy 被钳制) —— openTorrentDrawer 调 _kbRevealRow(hash)
  补让位 + 开场按 FX-29 待到集合登记数据源、全到手在 _drawerDone 兑现挂单补发
  (_drawerOpenReveal 带 open/hash 双守卫); 槽位落定 drawerAfterEnterHook 再补一发
  (流量形态不发); nextTick 等面板挂载再量, 下界走 _kbViewBottom 单点(不裸用
  innerHeight), 行不在 DOM 静默放弃, 不用逐层滚动 API(文件头禁令); S-C 判据收紧
  (2026-11-13 用户拍板「未被覆盖的行绝对不动」, 修订计划 26-11-12-1048 D3/D7 的
  「判据零改动」仅此一处): 触发界 = vBot + 补差, 补差按界源分支取值(单点
  _kbViewBottomPad: 面板分支 +8 呼吸距补偿 = 面板顶实缘, 越过带(行底落在(面板顶-12,
  面板顶])的未覆盖行不触发; 状态栏/整窗分支 +0 精确边, 关闭路径让位行为不变), 位移公式
  不动(真覆盖仍让位到 vBot - 8 终值); 同带语义第二实现点 _kbScrollRowIntoView 两路
  (flux 开门落定回执经 state.js drawerVisible 重入)一并收紧
- test_flux_door_window_scroll_transport: S-A flux 首开遮挡竞速修复(2026-11-13 用户报「种子先被面板
  遮挡、之后才上移」) —— flux 入场 translateY(100%) 300ms 整幅上滑 x html.fx-glide{scroll-behavior:
  smooth} x 四个让位/重入写入者(openTorrentDrawer 开场 / _drawerDone 兑现 / afterEnter 补发 / 落定
  回执重入)互相重启平滑爬行(实测 490ms+), 面板 300ms 就升完而行还在半路。修复 = fx-glide 挂点从
  开门挪到落定回执后(setTimeout 宏任务延迟): 开门窗口(enter 起拍到面板升完)内四写者走瞬时(与
  抽屉上升同步, 对齐 prism「种子跟着上升」手感), 回执后恢复平滑(800ms 窗口罩开门结束后的短暂
  键盘滚动); 四写者职责/挂点/判据/公式零改动, 只动传输方式; 宏任务延迟的依据(评审勘误如实口径):
  fireSettle 在 transitionend 捕获阶段、同一派发的目标阶段还有 Vue onAfterEnter(#3 入口), 两发
  重入的 scrollBy 都在本任务收尾后的微任务落地 —— 同步挂会赶上 afterEnter 那发, 包装本身必要;
  dock(true)/dock(false) 各撤挂类(glideAddTimer)/摘除(glideTimer)两个句柄 + 开门分支防御性摘类
  (重复触发幂等); e2e 红验在 e2e/drawer-dock-stability.spec.mjs S-A 用例(三皮肤,
  flux 红->绿, prism/atlas 对照恒绿)
- test_drawer_transition_dock_anim: 出入过渡动画(2026-10-03 用户报: 抽屉出现/消失生硬) ——
  停靠面板占文档流, 开/关时列表底部一帧撑开/收回是生硬根源, 面板本体滑淡治不了布局跳变:
  JS 钩子驱动 .drawer-dock 槽位高度插值(enter 追面板实时高 / leave 收面板自身高, 槽位整段
  冻结末帧一次收拢 —— W2 改写, 正面断言见 test_drawer_leave_slot_freeze_w2),
  模板 @enter/@leave 接线(before-enter 同帧量不到面板); 动画期几何登记 _drawerAnimTop
  (_kbViewBottom 优先读它, 让位量测不读中间插值; 2026-10-04 回归: 详情中途长高后起拍
  登记值失效, 追赶循环逐帧重登记落定顶缘 = dock 底缘 - 面板自然高); 重开打断收场时
  清面板内联高再量自然高; after 钩子挡被打断的迟到清场; reduced-motion 与 D3 全屏态
  双豁免; 四皮肤 CSS 成对(dock 动画期裁剪 + 退场 absolute 底缘锚定); T6 如实口径
  (2026-11-13): enter 起拍只写 height, margin-top 呼吸距恒在 CSS、JS 全程零写入
- test_drawer_leave_slot_freeze_w2: W2 收场高度传导修复(计划 26-11-12-1048 §02/§04 S3, D9/D11) ——
  旧机制逐帧写 dock 高度/呼吸距跟缴面板 = 文档逐帧变矮 = scrollY 逐帧钳制, 背景列表逐帧回弹
  (修复前真机逐帧取证: 收场位移事件 8~11 次, e2e W2 文档底用例判据 <=1)。新机制: 槽位高度
  写一次整段冻结, 逐帧循环只收已出流面板自身高, 末帧一次性收拢(文档底至多一次钳制,
  「钳制属预期」口径不动)。T6 边距生命周期改版如实改写(2026-11-13, 缺陷甲+乙): margin-top
  呼吸距整体退出 JS, margin 写点在 drawer + shortcuts 两域聚合面零出现(marginTop 字面全量禁
  + setProperty 钉, 关系断言, 甲的结构性保证 —— 旧口径 enter 起拍清边距 = 文档凹陷 -8px/Gecko 钳制永久, leave 末帧缴 0 + afterLeave
  缴回 = 两段式 -8 行位残差); 槽位总占位 = margin(CSS 恒 8) + height, leave 冻结/末帧收拢
  只写 height 各 1 次(计数钉 2), 闭合稳态一步落回 8px; 四皮肤 CSS 成对(sticky 槽位 +
  margin-top 8px(呼吸距唯一持有者) + 动画期裁剪 + 退场 absolute 底缘锚定 + 160ms 同拍;
  flux 差异只在入场 translateY(100%) 与 RM 降级块)
- test_kb_reveal_clamp_complete_a: T6 让位截断续缴(A 路线, 2026-11-14 用户拍板, 破
  shortcuts_engine.js 零改动的显式授权) —— 让位 scrollBy 请求超过当下文档下滚余量时被
  maxScroll 截断(enter 起拍槽位塌着/文档底 gap=0, 头寸要等槽位长高才出现), 行停在 (公式落点,
  请求落点) 之间, S-C 收紧后的触发界(行底>面板顶)对残位不再触发、后续发不补(S-A prism 前置红
  实证: 残位 面板顶-2, 差 14px; 改前靠「起拍凹陷多钳 8px 把残位留在带内」的巧合补齐)。续缴 =
  「同一公式落点的续缴」不是新公式(_kbViewBottom 单点逐帧复读, 差额现算幂等收口); **已发起
  限定** = 登记只在触发分支内 scrollBy 之后且带截断判定(y0+wanted 越过 maxScroll, 与传输无关)
  —— 静态触发带一字不动, 从未发起的行(含带内未覆盖行)绝不进本机制(S-C 不破); 守卫: open
  周期界(drawer.open/hash 逐帧 + closeDrawer 显式 _kbRevealCompleteStop, 无跨周期残留)、
  余量不足只等不发(盲发 = 再被钳 = 白发位移事件)、600ms 退避、平滑在途停稳才缴(开门窗口
  瞬时/fx-glide 平滑按现行传输, fx-mount 零改动)
"""

from __future__ import annotations

from webui_helpers import read_shared, _UI_ALL

import re

from pathlib import Path

from auto_qb.webui.server.routes.keys import _KEYS_SERIAL_RE as KB_DEF_RE

from web_shortcuts_support import (
    ROOT,
    SHARED,
    STATIC,
    _pick,
    _read,
    _registry,
)


def test_modal_default_focus_and_enter() -> None:
    pop = (SHARED / "tpl" / "popovers.html").read_text(encoding="utf-8")
    m = re.search(r'<button ref="modalOk"[^>]*@click="resolveModal\(true\)"', pop)
    assert m, "模态确定钮缺 ref=modalOk(计划 §08: 默认焦点在确定, Enter 即确认)"
    fb = _read("ui_feedback.js")
    open_at = fb.find("_openModal(cfg)")
    assert open_at >= 0 and fb.find("this.$refs.modalOk",
                                    open_at) > open_at, ("_openModal 必须在无输入形态时把默认焦点落到 modalOk(Enter 即确认; Esc 取消走退栈链)")


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
    store_js = _read("drawer_store.js")  # W1: 取数/竞态/等待集合/软切换已剥出 drawer.js
    # --- §3.2 名单分叉: _kbOverlayBusy 摘 drawer.open(面板≠浮层), escBusy 保留(Esc 关面板) ---
    busy = re.search(r"_kbOverlayBusy\(\) \{(.*?)\n    \},", eng, re.S)
    assert busy, "shortcuts.js 找不到 _kbOverlayBusy"
    assert "this.drawer.open" not in busy.group(1), "_kbOverlayBusy 必须摘除 drawer.open(停靠面板不是浮层, Delete 等列表键面板开着要保持可用)"
    assert "this.filePrio.visible || this.historyOpen" in busy.group(1), "_kbOverlayBusy 名单书写序漂移, 同步本守阵解析"
    dialogs_js = _read("dialogs.js")
    esc_busy = re.search(r"escBusy\(\) \{(.*?)\n    \},", dialogs_js, re.S)
    # Esc 关面板这一项两处(dialogs.escBusy / lifecycle 退栈链)都写 drawerVisible —— 面板随
    # drawerVisible 退场(不在主内容页)时不吃 Esc: 那条 Esc 属于当前页面(设置页退回首页)
    assert esc_busy and "this.drawerVisible" in esc_busy.group(1), \
        "escBusy 必须保留抽屉项(2026-10-06 起写 drawerVisible, 同 lifecycle 退栈链)"
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
    # 2026-10-08(计划 26-10-08-1217): 守卫收为主内容页级 —— 三视图共用面板, 不再挡视图
    assert 'this.page !== "groups"' in tb, "_kbDrawerTab 缺主内容页守卫(设置页没有停靠落点)"
    assert 'this.viewMode !== "torrents"' not in tb, \
        "_kbDrawerTab 不得再挡视图(三视图共用面板: 辅种/追剧页 Alt+1~5 必须可用)"
    assert tb.index('this.page !== "groups"') < tb.index("this.drawerTab(tab)"), \
        "主内容页守卫必须先于双态分流"
    assert "this.toast(" in tb, "非种子页必须 toast 提示后忽略, 不许静默"
    assert tb.index('if (this.drawer.open && this.drawerIsSeed)'
                   ) < tb.index("this.drawerTab(tab)"), "开态切页签只对种子形态成立(流量形态页签按钮不渲染, 切不得)"
    # 流量形态开态(全局/分组流量图, hash 恒空)必须视同关态换目标打开: 直接切页签会把空 hash
    # 打进 /api/torrents//trackers 等端点(404 toast), Alt+1 因流量形态 tab 恒 general 早退(按了没反应)
    # 形态判据收口(W3): 字面量比较改走 drawerIsSeed 单点(见 test_frontend_drawer_form_judge_single_point)
    assert tb.index('this.drawerIsSeed') < tb.index("openTorrentDrawer(hash)"), \
        "流量形态开态必须落到 openTorrentDrawer 换形打开, 不许走 drawerTab(空 hash 404)"
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
    assert 'if (this.page !== "groups") return;' in fb, \
        "跟随挂点必须带主内容页守卫(三视图共用面板: 只挡非主内容页, 不再挡视图)"
    assert "}, 200)" in fb, "跟随必须 200ms 防抖(连发上下键不逐行拉详情)"
    assert "this.drawer.hash === c.id" in fb, "hash 未变必须短路(光标落回同一行不重拉)"
    assert "cur.id === this.drawer.hash" in fb and "cur.kind !== \"torrent\"" in fb, "停稳复核必须再验目标(面板关/切页/目标已换/落回原行放弃)"
    # --- §3.4 数据面: _loadDrawerTab 代际 seq + fetcher 旧响应丢弃 + 换目标清数据 ---
    load = re.search(r"_loadDrawerTab\(tab\) \{(.*?)\n    \},", store_js, re.S)
    assert load and "this._drawerLoadSeq = (this._drawerLoadSeq || 0) + 1" in load.group(
        1
    ), "_loadDrawerTab 必须 bump 请求代际 seq(换目标/换页签后旧响应丢弃)"
    for fn in ("_fetchDrawerDetail", "_fetchDrawerTrackers", "_fetchDrawerFiles", "_fetchDrawerPeers"):
        sig = re.search(rf"async {fn}\((.*?)\) \{{", store_js)
        assert sig and "seq = 0" in sig.group(1), f"{fn} 必须带可选 seq(代际守卫)"
    # R21-A-01(2026-10-21): 四 fetcher 的落地次序收敛为唯一骨架 _fetchDrawerSource —— stale 判点
    # 从「四份 × 3 路 = 12」降到骨架内 3 路 + _drawerDone 1 处; 具名入口只许是薄壳(自带请求 = 又一份次序)。
    skel = re.search(r"async _fetchDrawerSource\(src, silent = false, seq = 0\) \{(.*?)\n    \},", store_js, re.S)
    assert skel, "drawer_store.js 找不到四 fetcher 的唯一骨架 _fetchDrawerSource(改名或挪走了? 同步本守阵)"
    assert skel.group(1).count("this._drawerStale(hash, seq)") == 3, \
        "骨架必须成功/异常/finally 三路都过 _drawerStale 旧响应丢弃(任一路缺失 = 慢响应覆盖新目标)"
    assert store_js.count("this._drawerStale(hash, seq)") == 4, \
        "stale 判点只该在骨架 3 路 + _drawerDone 1 处(多出来的 = 又有一份落地次序)"
    for fn in ("_fetchDrawerDetail", "_fetchDrawerTrackers", "_fetchDrawerFiles", "_fetchDrawerPeers"):
        thin = re.search(rf"async {fn}\(.*?\) \{{(.*?)\n    \}},", store_js, re.S)
        assert thin, f"{fn} 形态漂移(守阵正则失配, 同步本守阵)"
        assert "this._fetchDrawerSource(" in thin.group(1), f"{fn} 必须委派唯一骨架(次序不得有第二份)"
        assert "await this.api(" not in thin.group(1), f"{fn} 不许自带请求(次序只此一份)"
    stale = re.search(r"_drawerStale\(hash, seq\) \{\n      return (.*?);\n    \},", store_js, re.S)
    assert stale and "this.drawer.hash !== hash" in stale.group(1) and "seq !== this._drawerLoadSeq" in stale.group(
        1
    ), "_drawerStale 必须 hash 戳 + 代际双守卫(hash 戳兜 5s 轮询竞态)"
    switch = re.search(r"_switchDrawerTarget\(hash\) \{(.*?)\n    \},", store_js, re.S)
    assert switch, "drawer_store.js 找不到 _switchDrawerTarget(跟随换目标落点; W1 起在数据层)"
    sb = switch.group(1)
    # --- FX-29 软切换: 不清空旧数据(保留几何) + 遮罩防串显 + 早到请求不提前掀罩 ---
    for line in (
        "this.drawer.detail = null;", "this.drawer.trackers = [];", "this.drawer.files = [];",
        "this.drawer.peers = { peers: [] };"
    ):
        assert line not in sb, (
            f"换目标不得再{line[:-1].strip()} —— FX-29: 清空 = body 落加载空态 + 未拖过高的面板"
            "抽成一条再撑回, 连按上下键就是持续闪烁 + 列表/停靠面板连锁跳动"
        )
    assert "this._drawerWait = new Set(this._drawerWaitSources(this.drawer.tab));" in sb, (
        "换目标须按 tab 登记本次要等的数据源集合(详情恒等 + 该 tab 列表)"
    )
    assert "this._drawerBusyArm();" in sb, "换目标须延迟点亮遮罩(快响应时零中间态, 只有慢下来才淡出旧值)"
    assert "this._loadDrawerTab(this.drawer.tab)" in sb, "换目标后必须按当前页签重拉(跟随保留页签, 不回 drawerLastTab)"
    assert 'if (this.drawer.tab !== "general") this._fetchDrawerDetail();' in sb, (
        "换目标必须恒拉详情(头部标题依赖; _loadDrawerTab 只在 general 页签拉, 走查发现的串显 hash 缺口)"
    )
    # 落定只认「本 tab 的全套数据源」, 且过期响应不登记(否则另一个源还是上个种子的值就掀了罩)
    done = re.search(r"_drawerDone\(src, hash, seq\) \{(.*?)\n    \},", store_js, re.S)
    assert done, "drawer_store.js 找不到 _drawerDone(FX-29 单个数据源到手登记; W1 起在数据层)"
    db = done.group(1)
    assert db.index("this._drawerStale(hash, seq)") < db.index("w.delete(src)"), "过期响应不得登记到手(stale 先判)"
    assert "if (w.size) return;" in db, "兄弟源仍在飞时必须继续罩着(防半新半旧的中间帧)"
    assert 'switching: false' in _read("state.js"), "drawer 初值须显式建 switching 字段(vue-reactivity 静默坑)"
    assert re.search(r"drawerTitle\(\) \{\n.*?this\.memberByHash\.get\(this\.drawer\.hash\)", drawer_js,
                     re.S), ("drawerTitle 必须优先取 memberByHash 的名字(FX-29: 原实现等详情, 中间一帧标题是 40 字符 hash)")
    # --- 模板: 标题走 drawerTitle / 遮罩挂 body / 详情空态只归常规页签 ---
    # W3: 标题插值随两形态共用头部壳上移到 aq-drawer-head 片段(面板模板改为把 drawerTitle()
    # 经 :text 入参交给组件), 故「取成员名优先」这条要在两处各钉一半: 入参面(面板) + 渲染面(片段)
    tpl = (SHARED / "tpl" / "drawer.html").read_text(encoding="utf-8")
    head_tpl = (SHARED / "tpl" / "drawer-head.html").read_text(encoding="utf-8")
    assert ':text="drawerTitle()"' in tpl and "drawer.detail ? drawer.detail.name : drawer.hash" not in tpl, (
        "头部标题必须走 drawerTitle()(成员名优先, 不再是 hash; W3 起经 aq-drawer-head 的 :text 入参)"
    )
    assert "{{ text }}" in head_tpl, "头部壳片段必须渲染 text 入参(标题渲染面单点)"
    assert ':class="{ switching: drawer.switching,' in tpl and 'class="drawer-busy"' in tpl, (
        "body 必须挂 switching 遮罩类与加载胶囊(FX-29)"
    )
    assert "drawer.tab === 'general' && drawer.loading && !drawer.detail" in tpl, (
        "详情加载空态只归常规页签(压到 Tracker/用户/内容会把整幅表格换成一行空态)"
    )
    # --- 四皮肤 CSS 成对: switching 遮罩 + 加载胶囊 ---
    for ui in _UI_ALL:
        cssp = STATIC / ui / "css" / "dialogs.css"  # issue 26-10-20-2231: prism 也有了弹窗层, 四皮肤同路径
        css = cssp.read_text(encoding="utf-8")
        assert ".drawer-body.switching > *:not(.drawer-busy)" in css, f"{ui}: 缺 FX-29 软切换遮罩规则(四皮肤成对)"
        assert ".drawer-busy {" in css, f"{ui}: 缺加载胶囊样式"
    # open/close 作废在途跟随(显式操作优先于防抖中的跟随)
    assert drawer_js.count("this._stopDrawerFollow();") >= 2, "openTorrentDrawer 与 closeDrawer 都必须作废在途跟随定时器"
    # Delete 直连的 list 作用域守卫仍成立(停靠面板下 scope=list, Delete 可用 —— §2.2 矩阵)
    assert 'this._kbScope() === "list"' in eng, "Delete 直连必须保留 list 作用域守卫(面板开着 scope 仍为 list)"


def test_drawer_follow_mouse_click() -> None:
    """鼠标路径接跟随挂点(计划 26-10-03-0917 §1.3 相邻预留): 种子行普通单击与键盘共用
    _kbFollowDrawer 同一挂点 —— 面板开着点哪行换哪行; 面板关着不打开; 修饰键点击不跟随"""
    sel = _read("selection.js")
    m = re.search(r"onTorrentClick\(m, event\) \{(.*?)\n    \},", sel, re.S)
    assert m, "selection.js 找不到 onTorrentClick(单击入口被改名/搬走? 同步本守阵)"
    body = m.group(1)
    assert "this._kbFollowDrawer();" in body, ("种子行单击未接跟随挂点 —— 面板开着点另一行不换目标(键盘 ↑↓ 跟随、鼠标不跟随 = 两条输入没接同一行状态)")
    at = body.index("this._kbFollowDrawer()")
    assert at > body.index("event.ctrlKey") and at > body.index("this.shiftTorrentSel(m)"), (
        "跟随必须写在两个修饰键分支之后(Ctrl/Shift 是选择手势, 圈选 N 行不该让面板逐行翻)"
    )
    assert "openTorrentDrawer" not in body, (
        "单击不得开面板 —— 点一下就弹出 42vh 面板压掉列表, 与「列表当前行必须看得清」硬约束冲突; 开面板仍归双击 / Enter / 右键「详情」"
    )
    # 挂点自带守卫: 面板关着单击零副作用(不拉数据, 也不偷偷把面板打开)
    follow = re.search(r"_kbFollowDrawer\(\) \{(.*?)\n    \},", _read("drawer.js"), re.S)
    assert follow and "if (!this.drawer.open) return;" in follow.group(1), ("_kbFollowDrawer 首守卫必须挡面板关闭态(单击只在面板已开时换目标)")
    tpl = (SHARED / "tpl" / "torrents.html").read_text(encoding="utf-8")
    assert '@dblclick="openTorrentDrawer(m.hash)"' in tpl, "双击开面板入口掉了(单击只跟随, 开面板仍归双击)"


def test_drawer_height_w3() -> None:
    """方案A W3(计划 26-10-03-0917 §2.1 布局参数 / §3.5 持久化 / D1 首屏默认关闭)"""
    drawer_js = _read("drawer.js")
    state_js = _read("state.js")
    app_js = _read("app.js")
    tpl = (SHARED / "tpl" / "drawer.html").read_text(encoding="utf-8")
    # --- §2.1 拖拽调高: 顶缘 grip pointer 事件 + 夹取 [240px, 70vh](纯逻辑单点) ---
    clamp = re.search(r"_drawerClampHeight\(px, viewportH\) \{(.*?)\n    \},", drawer_js, re.S)
    assert clamp, "drawer.js 找不到 _drawerClampHeight(夹取必须收口在纯逻辑单点)"
    cb = clamp.group(1)
    assert "0.7" in cb and "240" in cb, "夹取区间必须是 [240px, 70vh](§2.1 布局参数)"
    assert "Math.min(Math.max(px" in cb, "夹取必须 min/max 双向(下界 240 / 上界 70vh)"
    grip = re.search(r"drawerGripDown\(e\) \{(.*?)\n    \},", drawer_js, re.S)
    assert grip, "drawer.js 找不到 drawerGripDown(顶缘拖拽入口)"
    gb = grip.group(1)
    assert "setPointerCapture" in gb and "preventDefault" in gb, "拖拽必须 pointer capture + preventDefault(出窗不丢事件/不起手选中)"
    move = re.search(r"drawerGripMove\(e\) \{(.*?)\n    \},", drawer_js, re.S)
    assert move and "_drawerClampHeight(" in move.group(1), "move 实时改高必须过夹取函数"
    up = re.search(r"drawerGripUp\(e\) \{(.*?)\n    \},", drawer_js, re.S)
    assert up and "persistDrawerHeight()" in up.group(1), "松手才落盘(拖拽过程不写 localStorage)"
    # 面板内联样式: 高度只在开态生效, height 与 max-height 同锁(CSS 默认 42vh 上限要能被拖拽突破);
    # 2026-10-18 用户硬约束(报障「五区分组握手中组进出场导致详情面板高度跳动」): **展开恒锁确定
    # 高度** —— 未拖拽过也回落默认 42vh, 不得返回 {} 走 CSS 内容自适应(任何元素进出场都会改实高)
    style = re.search(r"drawerPanelStyle\(\) \{(.*?)\n    \},", drawer_js, re.S)
    assert style, "drawer.js 找不到 drawerPanelStyle(面板高度应用单点)"
    stb = style.group(1)
    assert stb.index("this.drawer.open") < stb.index("this.drawerHeightPx"
                                                    ), ("内联高度必须守卫 开态(dashboardPanelStyle 高度不该挂在关闭态)")
    assert '"maxHeight"' in stb or "maxHeight" in stb, "内联样式必须同时锁 max-height(拖过 42vh 后 CSS 默认上限要被覆盖)"
    assert "|| Math.round(window.innerHeight * 0.42)" in stb and "return {};" not in stb.replace(
        "if (!this.drawer.open) return {};", ""
    ), ("未拖拽过也必须回落确定高度(默认 42vh) —— 返回 {} 走 CSS 内容自适应即「面板高度自己跳」复发")
    # --- §3.5 持久化: 两键与 drawerTab 同族 try/catch; D1 = drawerOpen 只写不回读 ---
    for fn, key in (("persistDrawerHeight", "autoqb.ui.drawerHeight"), ("persistDrawerOpen", "autoqb.ui.drawerOpen")):
        body = re.search(rf"{fn}\(\) \{{(.*?)\n    \}},", drawer_js, re.S)
        assert body, f"drawer.js 找不到 {fn}"
        assert f'localStorage.setItem("{key}"' in body.group(1), f"{fn} 必须写 {key}(§3.5 键族)"
        assert "catch" in body.group(1), f"{fn} 必须吞写入异常(与 persistDrawerTab 同纪律)"
    all_shared = {n: _read(n) for n in ("app.js", "state.js", "drawer.js", "shortcuts.js", "dialogs.js", "selection.js")}
    for n, s in all_shared.items():
        assert 'getItem("autoqb.ui.drawerOpen")' not in s, (
            f"{n} 回读了 autoqb.ui.drawerOpen —— D1 硬约束: 首屏恒默认关闭, 该键只作记录(写不回读)"
        )
    assert 'localStorage.getItem("autoqb.ui.drawerHeight")' in app_js, "高度记忆必须回读(initialDrawerHeight)"
    assert "n >= 240" in app_js, "initialDrawerHeight 读侧必须挡出界脏值(视口夹取在应用时做)"
    # --- D1: 首屏默认关闭 —— drawer.open 初值 false ---
    assert "open: false," in state_js, "state.js drawer 初值必须 open=false(D1 首屏默认关闭)"
    assert "drawerHeightPx: initialDrawerHeight()" in state_js, "state.js 必须挂高度记忆初值"
    close_fn = re.search(r"closeDrawer\(\) \{(.*?)\n    \},", drawer_js, re.S)
    assert close_fn and "persistDrawerOpen()" in close_fn.group(1), "关闭必须记开合态"
    # --- 模板接线: grip pointer 四事件 / aside 内联高度绑定 ---
    assert '@pointerdown="drawerGripDown($event)"' in tpl and '@pointermove="drawerGripMove($event)"' in tpl, (
        "grip 必须接 pointerdown/move(拖拽调高入口)"
    )
    assert '@pointerup="drawerGripUp($event)"' in tpl and '@pointercancel="drawerGripUp($event)"' in tpl, (
        "grip 必须接 pointerup + pointercancel(取消路径也要落盘收尾)"
    )
    # Vue 3.5 运行时编译模板解析不了 `_` 前缀裸标识符(ReferenceError, W3 目检实证) ——
    # grip 三个内联处理器必须非下划线命名(精确匹配已隐含); 既有 _copyText 模板调用是历史缺陷, 单独报告不在此钉
    assert ':style="drawerPanelStyle()"' in tpl, "aside 必须绑定内联高度"
    # --- 四皮肤 CSS 成对: grip / 拖拽期禁选中 / 面板 relative(absolute grip 定位参照) ---
    for ui in _UI_ALL:
        cssp = STATIC / ui / "css" / "dialogs.css"  # issue 26-10-20-2231: prism 也有了弹窗层, 四皮肤同路径
        css = cssp.read_text(encoding="utf-8")
        assert ".drawer-grip" in css and "touch-action: none" in css, f"{ui}: grip 样式缺失(触摸端拖拽会滚动页面)"
        assert "body.drawer-resizing" in css and "user-select: none" in css, f"{ui}: 拖拽期禁选中文本缺失"
        assert re.search(r"\.drawer \{ position: relative;", css), f"{ui}: .drawer 必须 relative(grip absolute 定位参照)"


def test_qb_traffic_shortcuts() -> None:
    """流量图三入口快捷键(2026-10-05): 打开全局图 / 流量页签 Alt+5 / 窗口前后切换 [ ]

    注册表是键位单一事实源, 前端无 JS 测试框架 —— 漏接线只表现为"按了没反应"(静默)。逐条钉:
    1. open-qb-traffic: 视图与导航 / global / Ctrl+Backslash / run _kbToggleQbTraffic(切换语义:
       已开同目标 ⇒ closeDrawer; 未开走 openQbHistory 内含 qbTrafficOn 门 + 未启用提示, 键盘入口
       不许静默无反应);
    2. drawer-tab-traffic: 详情面板组 / list / Alt+Digit5 / run _kbDrawerTab("traffic"), 且
       _kbDrawerTab 内补流量门控(qbTrafficOn false 提示后忽略, 不许切到无按钮的隐形页签 ——
       页签按钮 v-if=qbTrafficOn 不渲染);
    3. traffic-win-prev/next: 新「流量图」组 / global / [ ] / **when 条件绑定 qbTrafficActive**
       (仅流量图可见时消费键位) / run qbCycleWindow(±1); 引擎必须在 preventDefault **之前**
       分流 when(假则不消费, 键位留给浏览器 —— 否则无流量图时 [ / ] 被无谓吞掉)。"""
    items = {it["id"]: it for it in _registry()}
    eng = _read("shortcuts.js")
    chart = _read("qb_traffic_chart.js")

    # 1. 打开全局流量图(状态栏入口的键盘对应; 2026-10-09 起为切换语义, 见 test_shortcut_toggle_semantics)
    it = items["open-qb-traffic"]
    assert it["group"] == "视图与导航" and it["scope"] == "global", "open-qb-traffic 应 视图与导航 / global"
    assert it["def"] == "Ctrl+Backslash", "open-qb-traffic 默认键必须是 Ctrl+Backslash"
    assert it["runs"] == ["_kbToggleQbTraffic"], "open-qb-traffic 必须走 _kbToggleQbTraffic(切换语义)"
    assert "if (!this.qbTrafficOn) {" in chart and "功能未启用: qB 口径流量图" in chart, \
        "openQbHistory 必须补未启用提示(键盘入口不能静默无反应)"

    # 2. 详情面板流量页签(Alt+1-4 的第五档)
    it = items["drawer-tab-traffic"]
    assert it["group"] == "详情面板" and it["scope"] == "list", "drawer-tab-traffic 应 详情面板 / list"
    assert it["def"] == "Alt+Digit5", "drawer-tab-traffic 默认键必须是 Alt+Digit5"
    assert 'run: (vm) => vm._kbDrawerTab("traffic")' in eng, "drawer-tab-traffic run 未走 _kbDrawerTab"
    dtab = re.search(r"_kbDrawerTab\(tab\) \{(.*?)\n    \},", eng, re.S)
    assert dtab, "shortcuts.js 找不到 _kbDrawerTab"
    tb = dtab.group(1)
    gate = tb.index('if (tab === "traffic")')
    assert gate > tb.index('this.page !== "groups"'), "流量门控必须在页面守卫之后(守卫序: 页面 -> 功能门 -> 双态)"
    assert gate < tb.index('if (this.drawer.open && this.drawerIsSeed)'), "流量门控必须先于开态切页(未启用不得切到隐形页签)"
    # boot 韧性(issue 26-11-11-0633): flags 未取到(boot 期偶发失败)先补拉一次再判, 不把"没取到"当"没启用"
    assert "await this.ensureWebFlags()" in tb and "flagsLoaded" in tb, "流量页签门控缺'未取到先 await 补拉一次再判'"
    assert "功能未启用: qB 口径流量图" in tb, "流量页签未启用必须 toast 提示后忽略, 不许静默"

    # 3. 窗口前后切换(when 条件绑定 + 端点夹取, 见 test_webui_static_dom_page.py 的持久化守阵)
    for tid, key, delta in (("traffic-win-prev", "BracketLeft", "-1"), ("traffic-win-next", "BracketRight", "1")):
        it = items[tid]
        assert it["group"] == "流量图" and it["scope"] == "global", f"{tid} 应 流量图 / global"
        assert it["def"] == key, f"{tid} 默认键必须是 {key}"
        assert it["when"] == "qbTrafficActive", f"{tid} 必须 when 条件绑定 qbTrafficActive(无流量图不消费键位)"
        assert f"run: (vm) => vm.qbCycleWindow({delta})" in eng, f"{tid} run 未走 qbCycleWindow({delta})"
    assert "qbCycleWindow(delta) {" in chart, "qb_traffic_chart.js 缺 qbCycleWindow 落点"
    # 引擎: when 必须在 preventDefault 之前分流(假 = 不消费, 键位留给浏览器/其它 handler)
    eng_disp = re.search(r"_kbOnKeyDown\(e\) \{(.*?)\n    \},", eng, re.S)
    assert eng_disp, "shortcuts.js 找不到 _kbOnKeyDown"
    body = eng_disp.group(1)
    assert "if (item.when && !item.when(this)) return;" in body, \
        "引擎缺 when 条件绑定分流(条件项无流量图时也会吞掉 [ / ])"
    assert body.index("item.when && !item.when(this)") < body.index("e.preventDefault();\n      item.run(this);"), \
        "when 分流必须在 preventDefault 之前(否则键位已被消费, 「留给浏览器」成空话)"


def test_drawer_tab_shortcuts_merge_remap() -> None:
    """详情面板合并页签态页签快捷键重排(2026-10-10 用户报「标签合并后没有同步修改快捷键」)。

    病根: R3 把页签栏收敛成 [常规&内容][Tracker&用户](+流量) 后, 注册表五档(Alt+1..5)未随动,
    按 Alt+3 名义上是「用户页」却落在收起的页签上。修法 = 合并态按**位次**重排到三张可见页签,
    未合并(dtMergeTabsOn false)保持五档原样。逐条钉住不变量:
    1. 位次表 KB_MERGE_TAB_REMAP: 1->general / 2->trackers / 3->traffic, 4/5 停用(null);
    2. _kbDrawerTab 消费该表且重排在流量门控**之前**(第 3 档 remap 成 traffic 后仍要过 qbTrafficOn 门);
    3. 判据单点 _kbMergeTabsOn 读 dtMergeTabsOn computed(与页签栏 v-if 同一判据, 不自造第二套);
    4. 帮助浮层 / 设置页快捷键文案经 kbLabel 随态改写, 未合并回落注册表静态 label。"""
    eng = _read("shortcuts.js")

    # 1. 位次表: 前 3 档落三张可见页签, 4/5 停用(null)
    remap = re.search(r"const KB_MERGE_TAB_REMAP = \{(.*?)\};", eng, re.S)
    assert remap, "shortcuts.js 找不到 KB_MERGE_TAB_REMAP(合并态位次重排表)"
    body = remap.group(1)
    for frag in ('general: "general"', 'trackers: "trackers"', 'peers: "traffic"', "content: null", "traffic: null"):
        assert frag in body, f"KB_MERGE_TAB_REMAP 缺位次映射片段: {frag}"

    # 2. _kbDrawerTab 消费重排表, 且先于流量门控
    dtab = re.search(r"_kbDrawerTab\(tab\) \{(.*?)\n    \},", eng, re.S)
    assert dtab, "shortcuts.js 找不到 _kbDrawerTab"
    tb = dtab.group(1)
    assert "this._kbMergeTabsOn()" in tb, "_kbDrawerTab 未接合并态判据(_kbMergeTabsOn)"
    assert "KB_MERGE_TAB_REMAP[tab]" in tb, "_kbDrawerTab 未消费 KB_MERGE_TAB_REMAP"
    assert tb.index("KB_MERGE_TAB_REMAP[tab]") < tb.index('if (tab === "traffic")'), \
        "合并态重排必须先于流量门控(第 3 档 remap 成 traffic 后仍要过 qbTrafficOn 门)"

    # 3. 判据单点
    helper = re.search(r"_kbMergeTabsOn\(\) \{(.*?)\n    \},", eng, re.S)
    assert helper and "this.dtMergeTabsOn" in helper.group(1), \
        "_kbMergeTabsOn 必须读 dtMergeTabsOn(与页签栏 v-if 同一判据, 不许自造第二套)"

    # 4. 文案随态: 两处模板改用 kbLabel; kbLabel 只改写详情面板组 + 随合并态
    for rel in ("tpl/popovers.html", "tpl/settings-detail.html"):
        assert "{{ kbLabel(it) }}" in _read(rel), f"{rel} 快捷键文案未走 kbLabel(合并态与页签栏对不上)"
    kb_label = re.search(r"kbLabel\(item\) \{(.*?)\n    \},", eng, re.S)
    assert kb_label, "shortcuts.js 找不到 kbLabel(随态文案单点)"
    lb = kb_label.group(1)
    assert 'item.group !== "详情面板"' in lb, "kbLabel 只应改写「详情面板」组(其余回落静态 label)"
    assert "this._kbMergeTabsOn()" in lb, "kbLabel 必须随合并态(未合并不改写)"
    for frag in ("常规&内容", "Tracker&用户", "打开/切到 流量", "合并态停用"):
        assert frag in lb, f"kbLabel 合并态文案缺: {frag}"


def test_shortcut_toggle_semantics() -> None:
    """切换语义(2026-10-09, 报告 26-10-09-1731 §03/§04): 6 条「适合」条目开/关双态

    注册表是键位单一事实源, 前端无 JS 测试框架 —— 切换逻辑只表现为"再按没反应"(静默)。逐条钉:
    1. 四条浮层/抽屉条目 run 指向 _kbToggle*(不再是只打开): open-stats -> _kbToggleStats /
       open-history -> _kbToggleHistory / open-qb-traffic -> _kbToggleQbTraffic /
       help-panel -> _kbToggleKbHelp;
    2. 详情面板 I 的 run 仍是 _kbOpenDrawer, 但方法体含「已开同目标 ⇒ closeDrawer」切换分支;
    3. 列选择器 K 的 run 仍是 toggleColMenu(本身即切换);
    4. 引擎自切换白名单 KB_SELF_TOGGLE_OVERLAY: 四条浮层 id -> 状态字段, 浮层开着时放行第二次
       按键(否则被 _kbOverlayBusy 闸门吞掉);
    5. 切换只改键盘 run 路径, 鼠标入口(状态栏按钮 / 右键菜单 / 双击)保持原语义。"""
    items = {it["id"]: it for it in _registry()}
    eng = _read("shortcuts.js")

    # 1. 四条 run 改指切换分支
    assert items["open-stats"]["runs"] == ["_kbToggleStats"], "open-stats 必须走切换分支(已开⇒关)"
    assert items["open-history"]["runs"] == ["_kbToggleHistory"], "open-history 必须走切换分支"
    assert items["open-qb-traffic"]["runs"] == ["_kbToggleQbTraffic"], "open-qb-traffic 必须走切换分支"
    assert items["help-panel"]["runs"] == ["_kbToggleKbHelp"], "help-panel 必须走切换分支"

    # 2./3. 详情面板 / 列选择器 run 不变(前者方法内含切换, 后者本身即切换)
    assert items["act-detail"]["runs"] == ["_kbOpenDrawer"], "详情面板 I 仍走 _kbOpenDrawer(方法内含切换分支)"
    assert items["col-picker"]["runs"] == ["toggleColMenu"], "列选择器 K 仍走 toggleColMenu(本身即切换)"

    # 三条纯浮层切换: 已开走 closeX, 未开走 openX(关闭复用既有方法, 不新造状态)
    for meth, close_call, open_call in (
        ("_kbToggleStats", "this.closeStats()", "this.openStats()"),
        ("_kbToggleHistory", "this.closeHistory()", "this.openHistory()"),
        ("_kbToggleKbHelp", "this.closeKbHelp()", "this.kbOpenHelp()"),
    ):
        body = re.search(re.escape(meth) + r"\(\) \{(.*?)\n    \},", eng, re.S)
        assert body, f"shortcuts.js 找不到 {meth}"
        assert close_call in body.group(1) and open_call in body.group(1), f"{meth} 缺 开/关 双分支"

    # 流量图切换: 同目标(全局流量形态) ⇒ closeDrawer, 否则 openQbHistory(门控/提示在后者)
    qt = re.search(r"_kbToggleQbTraffic\(\) \{(.*?)\n    \},", eng, re.S)
    assert qt, "shortcuts.js 找不到 _kbToggleQbTraffic"
    assert "this.closeDrawer()" in qt.group(1) and "this.openQbHistory()" in qt.group(1), "流量图切换缺 关/开 双分支"
    assert 'this.drawer.scope === "global"' in qt.group(1), "流量图切换只在同目标(全局流量形态)时关"

    # 详情面板 I: 已开同目标 ⇒ closeDrawer(切换), 换目标仍 openTorrentDrawer
    od = re.search(r"_kbOpenDrawer\(\) \{(.*?)\n    \},", eng, re.S)
    assert od, "shortcuts.js 找不到 _kbOpenDrawer"
    assert "this.closeDrawer()" in od.group(1) and "this.openTorrentDrawer(hash)" in od.group(1), \
        "详情面板 I 缺 已开同目标⇒关 / 否则打开 双分支"
    assert 'this.drawerIsSeed && this.drawer.hash === hash' in od.group(1), \
        "详情面板 I 只在种子形态同目标时关(流量形态/换目标仍打开; 形态判据走 drawerIsSeed 单点)"

    # 4. 引擎自切换白名单: 四条浮层 id -> 状态字段; 浮层打开时放行第二次按键
    assert "const KB_SELF_TOGGLE_OVERLAY = {" in eng, "缺自切换白名单(报告 §07.1)"
    for iid, field in (
        ("open-stats", "statsOpen"), ("open-history", "historyOpen"), ("help-panel", "kbHelpOpen"),
        ("col-picker", "colMenuOpen")
    ):
        assert f'"{iid}": "{field}"' in eng, f"自切换白名单缺 {iid} -> {field}"
    assert "const own = KB_SELF_TOGGLE_OVERLAY[item.id];" in eng, "引擎未消费自切换白名单"
    assert "if (!(own && this[own])) {" in eng, "自切换白名单放行分支缺失(第二次按键仍被闸门吞)"


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
    body = re.search(r"kbConflictResolve\(mode\) \{(.*?)\n    \},", eng, re.S)
    assert body, "缺 kbConflictResolve(冲突三选一落点)"
    text = body.group(1)
    assert 'mode === "swap"' in text and 'mode === "steal"' in text, "冲突必须含交换/覆盖两支"
    assert 'ov[other.id] = ""' in text, "覆盖语义 = 对方置空(空串=显式禁用, 不能丢)"
    # 重置单条/全部 + 空串禁用
    assert "kbResetAll" in eng and "kbResetRow" in eng and "kbDisableRow" in eng, "缺重置/禁用入口"
    # 保存语义: PUT 失败本地回滚; 成功提示跨浏览器刷新生效
    save = re.search(r"async kbSaveKeys\(\) \{(.*?)\n    \},", eng, re.S)
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
    assert "kbGuardLeave(target)" in eng and 'this.hub.view !== "webui"' in eng, \
        "缺离开守卫实现(2026-11-03 改版: 面板并入 webui 分区, 守卫口径随迁)"


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
    # 寻址走 webui 旁挂目录单点(同寻址口径不变: state_file 同目录; 见 common.state_dir)
    assert "state_dir(manager)" in keys_py, "存储路径必须走 state_dir 单点(与 web.token 同寻址)"
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
    assert "_kbToggleKbHelp()" in eng, "help-panel run 未接切换分支(2026-10-09 切换语义)"
    assert "kbOpenHelp()" in eng, "help-panel 切换分支未开态仍走 kbOpenHelp"
    assert "kbGoSettings()" in eng, "帮助浮层缺「前往设置自定义」链路"
    life = _read("lifecycle.js")
    chain_at = life.find('e.key !== "Escape"')
    kb_at = life.find("this.kbHelpOpen = false")
    assert chain_at >= 0 and kb_at > chain_at, "帮助浮层必须进 lifecycle Esc 退栈链"
    assert "this.kbHelpOpen" in _read("dialogs.js"), "escBusy 必须同步 kbHelpOpen(新增浮层两处同步守则)"
    assert "this.kbHelpOpen" in eng, "_kbOverlayBusy 必须同步 kbHelpOpen(浮层打开时列表键位失效)"
    pop = (SHARED / "tpl" / "popovers.html").read_text(encoding="utf-8")
    for needle in (':open="kbHelpOpen"', "kbGroups()", "kbEntriesOf(grp)", "kbGoSettings()"):
        assert needle in pop, f"帮助浮层模板缺 {needle}"


def test_settings_panel_section() -> None:
    """W6 设置页「快捷键」: WebUI 卡内折叠块 + 全屏覆盖层(2026-11-03 改版; 2026-11-11 行布局重排) + CSS

    独立「keys」分区/首页卡已删除, 面板并入「WebUI」卡: 折叠块(读数) ⇄ 全屏覆盖层
    (HR 站点状态同款骨架, 复用 .hr-full-mask/.hr-full-modal), 覆盖层盖住配置树 actbar
    (任一时刻视野里只有一个保存按钮)。"""
    detail = (SHARED / "tpl" / "settings-detail.html").read_text(encoding="utf-8")
    assert "hub.view === 'keys'" not in detail, "独立 keys 分区应已删除(并入 WebUI 卡)"
    m = re.search(r"<!-- aqb:kb-full-modal:begin.*?-->(.*?)<!-- aqb:kb-full-modal:end.*?-->", detail, re.S)
    assert m, "settings-detail 缺 aqb:kb-full-modal 扫描锚 —— 覆盖层被移走或锚被删? 同步本守阵"
    frag = m.group(1)
    for needle in (
        "kbRecord(it.id)", "kbDisableRow(it)", "kbResetRow(it)", "kbResetAll()", "kbSaveKeys()", "kbDraftRevert()",
        "kbConflictResolve(", "kbDisplayOf(it)"
    ):
        assert needle in frag, f"快捷键面板缺交互 {needle}"
    # 覆盖层三件套 + 默认折叠(HR 覆盖层同款判据, test_frontend_hr_full_modal_wiring 同口径)
    for needle, what in (
        ('class="hr-full-mask"', "遮罩(点遮罩关闭路径)"),
        ('class="hr-full-modal kb-full"', "全屏面板(kb-full: 限宽 1120 居中, 2026-11-11 行布局重排)"),
        ('class="kb-table"', "三列网格容器(行布局重排, 全列表跨行对齐)"),
        ("kbFullClose()", "关闭动作(x 与遮罩两路复用)"),
        ('aria-label="关闭"', "x 关闭钮可访问名"),
        ('v-show="kbFullOpen"', "显隐挂 kbFullOpen(折叠 ⇄ 全屏覆盖层)"),
    ):
        assert needle in frag, f"键位覆盖层缺 {what}(应有 `{needle}`)"
    assert not re.search(r'class="hr-full-modal[^"]*\bopen\b', frag), "全屏面板不得带预展开属性(默认折叠是拍板交互)"
    # 折叠块头: 展开钮 + 读数
    assert ':aria-expanded="kbFullOpen"' in detail and "kbFullOpenPanel()" in detail, "折叠块头缺展开钮接线"
    assert "kbReadout()" in detail, "折叠块头缺键位读数"
    hub = _read("config_hub.js")
    for needle in ('key: "webui"', 'keys: "webui"', 'v === "webui"'):
        assert needle in hub, f"config_hub 缺 webui 分区接线(旧 keys 存量值经 HUB_VIEW_ALIAS 映射): {needle}"
    assert 'key: "keys"' not in hub, "独立「快捷键」首页卡应已删除(读数并入 WebUI 卡)"
    css = read_shared("console_hub.css")
    for cls in (
        ".kb-row", ".kb-grp-t", ".kb-help", ".kb-conflict", ".kb-danger", ".kb-table", ".hr-full-modal.kb-full"
    ):
        assert cls in css, f"console_hub.css 缺 {cls}(挂件类名必须有对应规则)"


def test_kb_full_overlay_wiring() -> None:
    """键位编辑全屏覆盖层接线(2026-11-03 改版): 关闭三路 + 名单三处同步 + 刷新兜底双脏源"""
    life = _read("lifecycle.js")
    chain_at = life.find('e.key !== "Escape"')
    kb_at = life.find("this.kbFullOpen) this.kbFullClose()")
    assert chain_at >= 0 and kb_at > chain_at, "键位覆盖层必须进 lifecycle Esc 退栈链(对话层级, 先于清筛选兜底)"
    assert "this.kbFullOpen" in _read("dialogs.js"), "escBusy 必须同步 kbFullOpen(否则覆盖层开着时 Esc 顺带退回设置首页)"
    assert "this.kbFullOpen" in _read("shortcuts.js"), "_kbOverlayBusy 必须同步 kbFullOpen(覆盖层开着时列表键位失效)"
    state = _read("state.js")
    assert "kbFullOpen: false" in state, "state.js 缺 kbFullOpen: false(默认折叠, hrsOpen 同款先例)"
    # 刷新兜底(U1-b)双脏源: 配置树 || 键位草稿 —— watcher 必须传 true 让 cfgGuardActive 重算,
    # 传各自新值会在「一源变净另一源仍脏」时把还需要的 beforeunload 摘掉
    assert "this.cfgDirty || this.kbDirtyView" in _read("config_editor.js"), \
        "刷新兜底判据必须含键位草稿第二脏源(否则键位脏时 F5 静默丢失; 计算属性=属性访问)"
    assert "kbDirtyView() {" in _read("config_hub.js"), "config_hub 缺 kbDirtyView 计算属性(watcher 的可观察信号)"
    assert "kbDirtyView() {" in state and "cfgGuardSync(true)" in state, \
        "state.js 双 watcher(cfgDirty/kbDirtyView)必须传 true 让 cfgGuardActive 重算"


def test_drawer_narrow_fullscreen_w4() -> None:
    """方案A W4(计划 26-10-03-0917 W4/D3 + 前波移交观察项): D3 窄屏降级四皮肤成对;
    行可见下界 _kbViewBottom(停靠面板盖住列表视口底部, 走查实证后收口); 轮询停靠化语义收口"""
    # --- D3: ≤900px 面板转全屏覆盖主区(四皮肤成对; 关闭钮在模板, 断言不被降级样式移除) ---
    # W3: 关闭钮随两形态共用头部壳一并上移到 aq-drawer-head 片段(单一实现, 面板模板不再各写一份)
    head_tpl = (SHARED / "tpl" / "drawer-head.html").read_text(encoding="utf-8")
    assert head_tpl.count('class="drawer-close"') == 1, ("关闭钮必须在头部壳片段(drawer-head.html, D3 全屏态唯一的关面板入口; 两形态共用一处)")
    assert 'class="drawer-close"' not in (SHARED / "tpl" / "drawer.html").read_text(encoding="utf-8"), \
        "关闭钮不得在面板模板再写一份(两形态各一份头部的复写正是问题 4 根因, W3 收口)"
    for ui in _UI_ALL:
        cssp = STATIC / ui / "css" / "dialogs.css"  # issue 26-10-20-2231: prism 也有了弹窗层, 四皮肤同路径
        css = cssp.read_text(encoding="utf-8")
        # prism 等文件在 D3 之前已有同断点的窄屏块(topbar 折行族), 必须认含 .drawer 的那块
        blocks = [m.group(1) for m in re.finditer(r"@media \(max-width: 900px\) \{(.*?)\n\}", css, re.S)]
        blk = next((b for b in blocks if ".drawer" in b), None)
        assert blk is not None, f"{ui}: 缺 D3 窄屏降级 @media(max-width:900px) 块"
        assert re.search(r"\.drawer \{ position: fixed;", blk), f"{ui}: 窄屏下面板必须 fixed 全屏覆盖主区(D3)"
        assert "max-height: none !important" in blk and "height: auto !important" in blk, (
            f"{ui}: 全屏态必须 !important 压过 drawerPanelStyle 内联高度(高度记忆/拖拽值失效)"
        )
        assert "bottom: var(--statusbar-h" in blk, f"{ui}: 全屏态要给底部状态栏让位(不整体盖屏)"
        assert ".drawer-grip { display: none; }" in blk, f"{ui}: 全屏态拖拽调高无意义, grip 必须隐藏"
        # 停靠基线规则仍在前(窄屏块只是覆盖): .drawer relative 是 W3 grip 定位参照, 不得被改掉
        assert re.search(r"\.drawer \{ position: relative;", css), f"{ui}: 停靠基线 .drawer relative 不得删(窄屏块只做覆盖)"
    # --- W4 几何走查产出: 行可见下界让位停靠面板 ---
    eng = _read("shortcuts.js")
    vb = re.search(r"_kbViewBottom\(\) \{(.*?)\n    \},", eng, re.S)
    assert vb, "shortcuts.js 缺 _kbViewBottom(行可见下界单点)"
    vbb = vb.group(1)
    assert "this.drawer.open" in vbb, "_kbViewBottom 必须守 drawer.open(关面板回落整窗高)"
    assert 'document.querySelector(".drawer-dock > .drawer")' in vbb, "下界必须实测面板顶缘(滚到文档底自然落回文档流)"
    assert 'getComputedStyle(panel).position !== "fixed"' in vbb, (
        "窄屏全屏态(position:fixed, 断点单点在 CSS)必须回落整窗高, JS 不复制 900px 断点数"
    )
    # 两处消费: 无光标回落(_kbViewportRow)与滚动进视口(_kbScrollRowIntoView)都不得再裸用 window.innerHeight 当下界
    vp = re.search(r"_kbViewportRow\(rows, delta\) \{(.*?)\n    \},", eng, re.S)
    assert vp and "this._kbViewBottom()" in vp.group(1), "_kbViewportRow 下界必须走 _kbViewBottom(面板盖住列表底部, W4 走查实证)"
    si = re.search(r"_kbScrollRowIntoView\(rows, idx\) \{(.*?)\n    \},", eng, re.S)
    assert si, "shortcuts.js 缺 _kbScrollRowIntoView"
    sib = si.group(1)
    assert "this._kbViewBottom()" in sib, "_kbScrollRowIntoView 下界必须走 _kbViewBottom(渲染行与窗口化两路)"
    assert sib.count("window.innerHeight") == 0, "_kbScrollRowIntoView 不得再裸用 window.innerHeight 当下界"
    # --- 前波移交观察项收口: 面板不可见(切走页面/视图)即停轮询拉取(定时器不拆, 回页自恢复) ---
    drawer_js = _read("drawer.js")
    store_js = _read("drawer_store.js")  # W1: 页签轮询收口在数据层
    # 2026-10-22: 轮询生命周期收敛进 polling.js 骨架(startPoll), 这里改为按**守卫声明**钉 ——
    # 守卫序(面板开 -> 主内容页)由 guard 表达式的书写序承载, 页面隐藏由骨架恒等守卫兜。
    poll = re.search(r"_startDrawerPoll\(\) \{\n(.*?)\n    \},", store_js, re.S)
    assert poll, "drawer_store.js 找不到 trackers/peers 主节拍轮询(W1 起轮询收口在数据层)"
    pb = poll.group(1)
    guard = re.search(r"guard: \(\) => (.*?),", pb, re.S)
    assert guard, "主节拍轮询缺 guard 声明(守卫要交给骨架, 不得再裸写在 tick 里)"
    gb = guard.group(1)
    assert gb.index("this.drawer.open") < gb.index('this.page === "groups"'), "轮询守卫序: 面板开 -> 页面可见"
    # 2026-10-08(计划 26-10-08-1217): 面板三视图共用, 轮询只挡非主内容页 —— 在辅种页/追剧页展开的
    # 面板同样要续拉 trackers/peers(此前「换视图即不拉」会让这两页的页签数据停在打开那一刻)。
    assert 'this.page === "groups"' in gb, "轮询必须带主内容页守卫(非主内容页面板不在 DOM)"
    assert "viewMode" not in pb, "轮询不得再挡视图(三视图共用面板)"


def test_drawer_open_reveal_row() -> None:
    """显式打开路径行让位(2026-10-03 报障: 双击列表末尾几行, 停靠面板一开把被点行盖住) ——
    W4 下界单点只接了键盘跟随, 显式打开 openTorrentDrawer 必须补一次被点行让位;
    2026-10-04 回归: 开场那发量的是 loading 态几何(面板随后长到 42vh), 且文档底打开时
    scrollBy 被钳制成 0(下滚余量是停靠槽位长高才创造的) —— 数据落定与槽位落定各补一发。
    2026-11-13 S-C(用户拍板「未被覆盖的行绝对不动」, 修订计划 26-11-12-1048 D3/D7 的
    「判据零改动」仅此一处): 触发界从 vBot - 4 收紧到 vBot + 补差, 补差按 _kbViewBottom 的
    界源分支取值(单点 _kbViewBottomPad) —— 面板分支 +8 呼吸距补偿(界 = 面板顶实缘, 行底落在
    (面板顶-12, 面板顶] 越过带内的未覆盖行不再被抬 4~16px, e2e 红验实测 prism/atlas ~10px) /
    状态栏·整窗分支 +0 精确边(关闭路径遮 1~8px 的行照旧让位到状态栏上 8px 净空, 统一 +8 不
    分支会过紧外溢 —— 同日评审发现); 位移公式不动, 真覆盖行的让位量与落点终值(vBot - 8)全程
    逐位一致。同带语义第二实现点 _kbScrollRowIntoView 两路(flux 开门落定回执经 state.js
    drawerVisible 重入)一并收紧; _kbViewportRow/_kbMovePage 不在让位链(只选行/算一屏,
    不因开门滚动), 不动。"""
    drawer_js = _read("drawer.js")
    store_js = _read("drawer_store.js")  # W1: _drawerDone 在数据层
    open_fn = re.search(r"async openTorrentDrawer\(hash\) \{(.*?)\n    \},", drawer_js, re.S)
    assert open_fn, "drawer.js 找不到 openTorrentDrawer"
    body = open_fn.group(1)
    assert "this._kbRevealRow(hash)" in body, ("显式打开必须调 _kbRevealRow 让位(停靠面板一开就压住列表底部, 双击末尾几行被挡)")
    assert 'this._drawerWait = new Set(initialTab === "traffic" ? ["detail"] : this._drawerWaitSources(initialTab))' in body, (
        "开场必须按 FX-29 待到集合登记数据源(详情+初值页签), 全到手才是面板几何落定(页签数据中途长高也覆盖); "
        "流量页签定高不进集合"
    )
    assert "this._drawerOpenReveal = hash" in body, "开场必须挂落定补让位挂单(数据源全到手后兑现)"
    done_fn = re.search(r"_drawerDone\(src, hash, seq\) \{(.*?)\n    \},", store_js, re.S)
    assert done_fn and "_drawerOpenReveal" in done_fn.group(1), (
        "待到集合清空(_drawerDone)必须兑现开场挂单补发让位 —— 那是数据落定时刻, 页签数据晚到也覆盖"
    )
    assert "this.drawer.hash === h" in done_fn.group(1), ("挂单兑现必须带 hash 守卫(挂单后被打断/换目标, 迟到兑现不得按旧种子几何抢滚动)")
    after_enter = re.search(r"drawerAfterEnterHook\(\) \{(.*?)\n    \},", drawer_js, re.S)
    assert after_enter and "this._kbRevealRow(this.drawer.hash)" in after_enter.group(1), (
        "槽位落定(afterEnter)必须补一发让位: 文档底打开时开场 scrollBy 被钳制成 0, "
        "下滚余量是停靠槽位长高才创造的, 落定后才有足额余量(2026-10-04 取证)"
    )
    assert 'this.drawerIsSeed' in after_enter.group(1), "流量形态无种子行可让, afterEnter 补发必须按形态门控(走 drawerIsSeed 单点)"
    eng = _read("shortcuts.js")
    rv = re.search(r"_kbRevealRow\(hash\) \{(.*?)\n    \},", eng, re.S)
    assert rv, "shortcuts.js 缺 _kbRevealRow(显式打开路径的行让位单点)"
    rb = rv.group(1)
    assert "$nextTick" in rb, "面板 DOM 随 open v-if 挂载, 必须等 nextTick 再量几何(同帧量不到面板)"
    assert "this._kbViewBottom()" in rb, "让位下界必须走 _kbViewBottom 单点(dock-panel 坑档: 不许现写 innerHeight)"
    assert rb.count("window.innerHeight") == 0, "_kbRevealRow 不得裸用 window.innerHeight 当下界"
    assert "data-hash" in rb and "CSS.escape" in rb, "目标行按 data-hash 定位且转义(与滚动跟随同源)"
    assert "scrollBy" in rb, "让位走 getBoundingClientRect + scrollBy 差值(与 _kbScrollRowIntoView 同口径)"
    assert "scrollIntoView" not in rb, "_kbRevealRow 不得用逐层滚动 API(shortcuts.js 文件头禁令)"
    assert "if (!el) return;" in rb, "行不在 DOM(窗口化折叠)必须静默放弃, 滚动位置宁可不动也不猜"
    # --- S-C 判据收紧(2026-11-13 用户拍板「未被覆盖的行绝对不动」; 同日评审收口: 补差按界源分支
    # 取值): 触发界 = 单点 + 补差, 补差与 _kbViewBottom 的分支语义配对 —— 面板分支 +8(界自带
    # -8 呼吸距, 补回后界 = 面板顶实缘, 行底 <= 面板顶的未覆盖行在让位三发上都不动) / 状态栏·
    # 整窗分支 +0(返回值就是遮蔽实缘, 精确边 —— 关闭路径遮 1~8px 的行照旧让位到状态栏上 8px
    # 净空, 不因面板分支补差外溢而漏让)。位移公式不动(真覆盖行让位量与落点终值修复前后逐位
    # 一致)。钉法 = 补差单点与面板分支呼吸距的**关系** + 三处判据点一致化, 不是裸字符串:
    # 单点呼吸距若调整, 补差必须跟随才算仍指面板顶实缘; 旧口径 vBot - 4 的越过带会把未覆盖行
    # 抬 4~16px; 统一 +8 不分支则关闭路径过紧外溢(评审发现)。
    vb2 = re.search(r"_kbViewBottom\(\) \{(.*?)\n    \},", eng, re.S)
    assert vb2, "shortcuts.js 缺 _kbViewBottom(行可见下界单点, S-C 触发界从它派生)"
    breathe = re.search(r"panel\.getBoundingClientRect\(\)\.top - (\d+)", vb2.group(1))
    assert breathe, "_kbViewBottom 面板分支应带呼吸距(面板顶缘 - N), 补差单点与其同值才等于面板顶实缘"
    pad = re.search(r"_kbViewBottomPad\(\) \{(.*?)\n    \},", eng, re.S)
    assert pad, "shortcuts.js 缺 _kbViewBottomPad(触发界补差单点: 补差按界源分支取值)"
    pdb = pad.group(1)
    assert pdb.count("window.innerHeight") == 0 and "getBoundingClientRect().top" not in pdb, (
        "补差单点只读分支条件不读矩形(几何仍归 _kbViewBottom 单点, 不许第二几何源)"
    )
    assert "this.drawer.open" in pdb, "补差单点必须先挡面板开合(关闭 = 界源状态栏/整窗, 补差 0 精确边)"
    assert 'document.querySelector(".drawer-dock > .drawer")' in pdb, ("补差单点必须实测面板 DOM(面板不在 DOM = 界源非面板分支, 补差 0)")
    assert 'getComputedStyle(panel).position === "fixed"' in pdb, ("D3 窄屏全屏态面板出流, 界源回落状态栏/整窗, 补差必须为 0(精确边)")
    assert f"return {breathe.group(1)}" in pdb, (
        f"面板分支补差必须与 _kbViewBottom 面板分支呼吸距同值(实测补差单点 return 值, 呼吸距 {breathe.group(1)}): "
        "补回呼吸距触发界才等于面板顶实缘(未覆盖行绝对不动)"
    )
    assert re.search(r"if \(rect\.bottom > vBot \+ this\._kbViewBottomPad\(\)\) \{", rb), (
        "_kbRevealRow 触发界必须是 vBot + _kbViewBottomPad()(补差按界源分支取值): 面板开 = 面板顶实缘"
        "(未覆盖行绝对不动; 旧口径 vBot - 4 的越过带会把未覆盖行抬 4~16px, e2e S-C 红验实测) / "
        "面板关·D3 = 精确边(关闭路径遮 1~8px 的行照旧让位, 统一 +8 不分支会过紧外溢 —— 评审发现)。"
        "T6(A 路线)如实改写: 触发体从单行改块状(截断续缴登记进分支), 判据表达式逐字不动"
    )
    assert re.search(r"const wanted = rect\.bottom - vBot \+ 8;",
                     rb) and re.search(r"window\.scrollBy\(0, wanted\)", rb), (
                         "位移公式 rect.bottom - vBot + 8 不得随判据收紧改动(真覆盖行的让位量与落点终值 vBot - 8 修复前后逐位一致; "
                         "T6(A 路线)如实改写: 公式落值进 wanted 变量(scrollBy 与截断判定共用一次计算), 数式逐字不动)"
                     )
    # --- 同带语义第二实现点(让位链普查): _kbScrollRowIntoView 下界两路 —— flux 开门落定回执
    # (state.js drawerVisible -> AQB_FX_MOUNT.dock 回执)重入本方法把 drawer.hash 行算回可见带,
    # 不一并收紧则 flux 上越过带行在开门路径仍被抬; 键盘跟随共用同一下界(真覆盖仍让位, 口径一致)。
    si2 = re.search(r"_kbScrollRowIntoView\(rows, idx\) \{(.*?)\n    \},", eng, re.S)
    assert si2, "shortcuts.js 缺 _kbScrollRowIntoView(S-C 同带语义第二实现点)"
    sib2 = si2.group(1)
    assert re.search(r"const vPad = this\._kbViewBottomPad\(\);",
                     sib2), ("补差必须与 _kbViewBottom 同帧单次落值复用(单点纪律: 边界落值只取一次)")
    assert re.search(r"else if \(rect\.bottom > vBot \+ vPad\) window\.scrollBy", sib2), (
        "_kbScrollRowIntoView 渲染行路下界触发界必须是 vBot + vPad(补差单点落值; flux 开门回执经此重入, "
        "同带语义必须一并收紧 —— 旧口径 vBot - 4 在 flux 开门路径仍会抬越过带行)"
    )
    assert re.search(r"else if \(y \+ h > window\.scrollY \+ vBot \+ vPad\) window\.scrollTo",
                     sib2), ("_kbScrollRowIntoView 窗口化前缀和路下界触发界必须与渲染行路同收紧(vBot + vPad, 两路同带语义)")
    assert re.search(r"window\.scrollBy\(0, rect\.bottom - vBot \+ 8\)", sib2) and re.search(
        r"window\.scrollTo\(0, y \+ h - vBot \+ 8\)", sib2
    ), "_kbScrollRowIntoView 两路位移公式不动(只收紧触发界, 让位量口径不变)"


def test_flux_door_window_scroll_transport() -> None:
    """S-A flux 首开遮挡竞速修复(2026-11-13 用户报「种子先被面板遮挡、之后才上移」):
    fx-glide 挂点从开门挪到落定回执后, 开门窗口内让位/重入滚动走瞬时。

    病根(flux 独有): 入场 translateY(100%) 300ms 整幅上滑(dialogs.css, 令牌 --fx-dur-panel)
    x html.fx-glide { scroll-behavior: smooth }(fx-mount.css) x 四个让位/重入写入者
    (openTorrentDrawer 开场 / _drawerDone 集合落定兑现 / drawerAfterEnterHook 补发 /
    state.js 落定回执重入) —— 开门即挂的 fx-glide 让四次 scrollBy 互相重启/累加平滑爬行
    (真机取证 490ms+, 且互相累加会越过公式落点再被回执修正), 面板 300ms 就升完而行还在
    半路 = 先被盖后探出。修复只动传输方式: 挂点挪到落定回执后 —— 开门窗口(enter 起拍到
    面板升完)内四写者瞬时(与抽屉上升同步, 对齐 prism 手感), 回执后恢复平滑(800ms 窗口)。
    四写者职责/挂点/判据/公式零改动(三发挂点与 state.js 重入由 test_drawer_open_reveal_row
    与 test_frontend_fx_wiring 钉住, 本守阵只钉传输机制不变量)。钉法:
    1. dock(true) 分支不得挂 fx-glide(开门窗口传输 = 瞬时)且保留 armSettle() 武装(R5#179);
    2. fireSettle 挂点必须在 settleArmed 单发守卫与 settleCb() 之后, 且经 setTimeout 宏任务
       延迟。依据(2026-11-13 评审勘误, 如实口径): fireSettle 跑在 transitionend 派发的捕获
       阶段, 同一次派发的目标阶段还有 Vue Transition 的 onAfterEnter(#3 补发入口);
       回执重入(#4)在回执回调内同步进入 _kbScrollRowIntoView —— 两发重入的入口(监听器/
       同步调用)都在**本任务内**, 只有它们的 scrollBy 在本任务收尾后的微任务里落地。
       若在 fireSettle 内同步挂类, 类会先于 afterEnter 监听器挂上(同步挂会赶上 afterEnter
       那发), 两发全被平滑重启爬行, S-A 症状复发 —— 宏任务包装把挂类推到本任务(含全部
       微任务)跑完之后, 本身必要, 不是可选优化; 按「微任务先于宏任务」把挂点改回同步恰是复发路径;
    3. 挂/摘两个定时器都留句柄(glideAddTimer 回执后挂类的 setTimeout(0) / glideTimer 挂上后
       800ms 的摘除), dock(true)/dock(false) 各撤两个句柄(重复触发幂等): 只撤摘除句柄撤不掉
       「回执→宏任务」间隙里的挂类定时器 —— 关面板落在间隙则 fx-glide 在面板已关后被挂上并
       存续 800ms, 期间再开被 dock(true) 带进新开门窗口(S-A 复发); 上一轮摘除句柄还挂着则会
       砍短这一轮的平滑窗口。类本身的残局(定时器已 fire、类还在)由 dock(true) 防御性摘类兜底,
       关面板立即摘。"""
    mount_js = (STATIC / "flux" / "fx-mount.js").read_text(encoding="utf-8")
    # --- 1. dock: 开门分支不挂 fx-glide + 撤两个句柄 + 防御性摘类; 关面板分支立即摘 + 撤两个句柄 ---
    dock_blk = re.search(r"function dock\(open, onSettled\) \{(.*?)\n  \}", mount_js, re.S)
    assert dock_blk, "fx-mount.js 找不到 dock(open, onSettled)(签名漂移? 同步本守阵)"
    db = dock_blk.group(1)
    assert 'classList.add("fx-glide")' not in db, (
        "dock(true) 分支不得挂 fx-glide(S-A): 开门窗口内的让位/重入滚动必须瞬时(与抽屉上升同步; "
        "开门即挂 = 四写者互相重启/累加平滑爬行 490ms+, 面板 300ms 升完而行在半路, 「先遮挡后上移」复发)"
    )
    assert "armSettle()" in db, (
        "dock(true) 分支必须保留 armSettle() 武装(R5#179 兜底定时器; test_frontend_fx_wiring 同钉, "
        "回执丢失场景 fx-glide 恒挂 = 键盘滚动一直平滑)"
    )
    # 句柄清理(幂等面, 两分支各撤两个): glideAddTimer(回执后挂类的 setTimeout(0))与
    # glideTimer(挂上后的 800ms 摘除) —— 只撤摘除句柄的旧口径撤不掉「回执→宏任务」间隙里
    # 的挂类定时器(关面板落在间隙 = fx-glide 在面板已关后被挂上并存续 800ms, 期间再开被
    # 带进新开门窗口); 上一轮摘除句柄挂着则砍短这一轮的平滑窗口。
    assert db.count("clearTimeout(glideAddTimer)") == 2 and db.count("clearTimeout(glideTimer)") == 2, (
        "dock 两分支必须各撤两个句柄(glideAddTimer 挂类 / glideTimer 摘除) —— 只撤摘除句柄撤不掉"
        "「回执→宏任务」间隙里的挂类定时器: 关面板落在间隙则 fx-glide 在面板已关后被挂上并存续 "
        "800ms, 期间再开被带进新开门窗口, S-A 复发(各恰 2 处 = open 分支 1 + close 分支 1)"
    )
    open_blk = re.search(r"if \(open\) \{(.*?)\n    \} else \{", db, re.S)
    assert open_blk and 'classList.remove("fx-glide")' in open_blk.group(1), (
        "dock(true) 必须防御性摘 fx-glide(上一轮类已挂上的残局: 定时器已 fire 后句柄撤无可撤, "
        "不摘类则平滑仍被带进本次开门窗口)"
    )
    close_blk = re.search(r"\} else \{\n(.*?)\n    \}", db, re.S)
    assert close_blk, "fx-mount.js dock 缺 else 分支(关面板路径)? 同步本守阵解析"
    cb = close_blk.group(1)
    assert 'classList.remove("fx-glide")' in cb, "dock(false) 必须立即摘 fx-glide(关面板不留平滑窗口)"
    assert "clearTimeout(glideAddTimer)" in cb and "clearTimeout(glideTimer)" in cb, (
        "dock(false) 必须连同挂类/摘除两个定时器一并撤(关面板后不得再有定时器写 html 类)"
    )
    # --- 2. fireSettle: 挂点在单发守卫与回执之后、经宏任务延迟; 两个句柄都写回 ---
    fs = re.search(r"function fireSettle\(\) \{(.*?)\n  \}", mount_js, re.S)
    assert fs, "fx-mount.js 找不到 fireSettle"
    fb = fs.group(1)
    at_armed = fb.index("settleArmed = false")
    at_cb = fb.index("settleCb()")
    at_add = fb.find('classList.add("fx-glide")')
    assert at_add > at_cb > at_armed >= 0, (
        "fx-glide 挂点必须在 settleArmed 单发守卫与 settleCb() 之后(S-A: 先回执后挂平滑 —— 回执重入"
        "与 afterEnter 补发都属开门窗口, 挂早了会被平滑重启爬行)"
    )
    assert re.search(
        r"setTimeout\(function \(\) \{[^}]*?document\.documentElement\.classList\.add\(\"fx-glide\"\)", fb
    ), (
        "fx-glide 挂点必须经 setTimeout 宏任务延迟(S-A 关键顺序): fireSettle 在 transitionend 捕获阶段"
        "运行, 同一派发的目标阶段还有 Vue Transition 的 onAfterEnter(#3 入口), 两发重入的 scrollBy 都"
        "在本任务收尾后的微任务落地 —— 同步挂会赶上 afterEnter 那发, 两发全被平滑, 症状复发; "
        "宏任务包装本身必要, 不是可选优化"
    )
    assert re.search(r"glideAddTimer\s*=\s*setTimeout", fb) and re.search(r"glideTimer\s*=\s*setTimeout", fb) \
        and 'classList.remove("fx-glide")' in fb, (
        "挂类与摘除都必须写回句柄(glideAddTimer/glideTimer, dock 两分支要撤它们, 幂等面)且 fireSettle "
        "保留 800ms 后摘(平滑窗口只罩回执后的短暂键盘滚动, 不能恒驻留)"
    )
    # --- 3. CSS 落点仍在(正面钉在 test_frontend_fx_wiring; 这里防 JS/CSS 两半漂移的另一半) ---
    assert 'classList.add("fx-glide")' in mount_js and 'classList.remove("fx-glide")' in mount_js, (
        "fx-mount.js 必须保留 fx-glide 的挂/摘(S-A 只挪挂点, 类与 CSS 规则两半都在: 缺任一半 = "
        "回执后键盘滚动窗口失效或平滑恒驻留)"
    )


def test_drawer_transition_dock_anim() -> None:
    """出入过渡动画(2026-10-03 用户报: 抽屉出现/消失很生硬)

    停靠面板占据文档流, open 翻转时列表底部一帧被面板撑开/收回 —— 这是生硬根源; 面板本体的
    transform/opacity 滑淡(既有 CSS)治不了布局跳变。修法 = JS 钩子驱动: enter 追面板实时高
    插值 / leave 槽位整段冻结只收面板自身高、末帧一次收拢(W2, 计划 26-11-12-1048, 正面断言见
    test_drawer_leave_slot_freeze_w2), 并把动画期的几何登记进 _drawerAnimTop 供下界单点消费。
    T6(2026-11-13)如实口径: enter 起拍只写 height(margin-top 呼吸距恒在 CSS, JS 全程零写入 ——
    dock.style.marginTop 聚合面零出现的关系断言钉在 test_drawer_leave_slot_freeze_w2), 槽位
    总占位 = margin(恒 8) + height, 起拍帧文档零变化(旧口径清边距 = 凹陷 -8px)。
    """
    drawer_js = _read("drawer.js")
    tpl = (SHARED / "tpl" / "drawer.html").read_text(encoding="utf-8")
    # --- 模板接线: 必须用 @enter(before-enter 同帧元素未插入 DOM, 量不到父容器槽位) ---
    assert '@enter="drawerEnterHook"' in tpl and '@leave="drawerLeaveHook"' in tpl, "<transition> 必须接 enter/leave 钩子"
    assert "@before-enter" not in tpl, "不得用 before-enter(同帧元素未插入 DOM, parentElement 为 null, 动画整体失效)"
    assert '@after-enter="drawerAfterEnterHook"' in tpl and '@after-leave="drawerAfterLeaveHook"' in tpl, "after 钩子必须接线(收敛兜底/残局回收)"
    # --- 钩子机制: 槽位插值驱动的是 .drawer-dock 高度, 不碰面板 :style 绑定 ---
    enter = re.search(r"drawerEnterHook\(el\) \{(.*?)\n    \},", drawer_js, re.S)
    assert enter, "drawer.js 找不到 drawerEnterHook"
    eb = enter.group(1)
    assert 'el.parentElement' in eb, "enter 钩子必须经面板父节点定位 .drawer-dock(tpl-manifest 注入落点)"
    assert 'classList.add("drawer-anim")' in eb and 'dock.style.height' in eb, "enter 必须挂动画类并写 dock 槽位高度(治布局一帧跳变)"
    assert "requestAnimationFrame" in eb, "槽位展开必须走 rAF(同帧直写终值会被合成一帧吞成无过渡)"
    assert 'getBoundingClientRect().height' in eb, "槽位目标高必须每帧量面板实时高(详情中途到达长高也跟)"
    assert 'prefers-reduced-motion' in eb, "reduced-motion 必须豁免插值(全局降级口径)"
    assert 'drawer-leave-active' in eb and 'old.style.height = ""' in eb, (
        "重开打断收场时必须清被打断面板的内联高再量自然高(压成 0 会把自然高量成 0, 整段动画失效)"
    )
    leave = re.search(r"drawerLeaveHook\(el\) \{(.*?)\n    \},", drawer_js, re.S)
    assert leave, "drawer.js 找不到 drawerLeaveHook"
    lb = leave.group(1)
    assert 'drawer-dock.drawer-anim' in lb and "frozenH" in lb, "收场必须先取 closeDrawer 冻结的槽位高再清理(面板出流后自然高已塌)"
    assert 'position === "fixed"' in lb, "D3 窄屏全屏态必须豁免(面板出流, 无布局可插值)"
    # W2(计划 26-11-12-1048)如实改写: 旧断言钉「dock.style.height = el.style.height 逐帧跟缴」,
    # 该机制正是 W2 根因(dock 流内 sticky, 逐帧缩它 = 文档逐帧变矮 = scrollY 逐帧钳制) ——
    # 收场只收面板自身高; 槽位冻结/末帧收拢的正面断言在 test_drawer_leave_slot_freeze_w2
    assert "el.style.height" in lb, "收场必须收面板自身高度(面板出流后不收自身高会顶住槽位, 插值失效)"
    assert "dock.style.height = el.style.height" not in lb, ("收场不得逐帧跟缴 dock 槽位高(W2 根因机制已废: 槽位整段冻结, 逐帧写它文档逐帧变矮)")
    # --- 几何登记: 动画期下界单点优先读登记值, 让位量测不读中间插值 ---
    assert "_drawerAnimTop = this._drawerFinalTop(dock)" in drawer_js or "_drawerAnimTop = _drawerFinalTop(dock)" in drawer_js, (
        "钩子必须把自然高帧的 dock 顶缘登记进 _drawerAnimTop(插值期顶缘是中间值, 不可让让位量测读到)"
    )
    assert "_drawerAnimTop = Math.round(dock.getBoundingClientRect().bottom - target)" in eb, (
        "追赶循环必须逐帧重登记落定顶缘(dock 底缘 - 面板自然高; sticky 吸底期底缘恒定): "
        "详情中途长高后起拍登记的 loading 态顶缘不再是落定几何, 让位量测会按旧几何漏让(2026-10-04 回归)"
    )
    # --- 代际闸: 快速开关往返时旧循环立即让位新拍(seq 不符的 rAF 回调自弃) ---
    assert lb.count("seq !== this._drawerAnimSeq") >= 1 and eb.count("seq !== this._drawerAnimSeq") >= 1, (
        "enter/leave 循环必须带 seq 代际闸(重开/重关打断时旧循环不得再写 dock)"
    )
    # 动画期句柄(_drawerAnimTop/_drawerAnimSeq/_drawerAnimRaf/_drawerAnimDock)与 _drawerTimer 同族:
    # 实例级非响应式, 惰性初始化, 不进 state.js 的 data(见 state.js drawer 注释口径)
    eng = _read("shortcuts.js")
    vb = re.search(r"_kbViewBottom\(\) \{(.*?)\n    \},", eng, re.S)
    assert vb and "_drawerAnimTop" in vb.group(1), "_kbViewBottom 必须在动画期优先读登记的落定顶缘(dock-panel 坑档: 单点消费)"
    assert vb.group(1).count("panel") >= 1 and vb.group(1).index("panel") < vb.group(1).index("_drawerAnimTop"), (
        "_kbViewBottom 必须先取面板 DOM 再作登记值的有效性判定(动画中切走视图时登记值悬空, 不得消费)"
    )
    # --- closeDrawer 槽位冻结(leave 期面板转 absolute 出流, dock 会瞬间塌 0) ---
    close_fn = re.search(r"closeDrawer\(\) \{(.*?)\n    \},", drawer_js, re.S)
    assert close_fn and 'classList.add("drawer-anim")' in close_fn.group(1), (
        "closeDrawer 必须冻结当前用户可见高到 dock(同帧无跳变帧, 收场从捕获帧起步)"
    )
    # --- after 钩子挡被打断的迟到清场(快速开关往返) ---
    ae = re.search(r"drawerAfterEnterHook\(\) \{(.*?)\n    \},", drawer_js, re.S)
    al = re.search(r"drawerAfterLeaveHook\(\) \{(.*?)\n    \},", drawer_js, re.S)
    assert ae and "if (!this.drawer.open) return;" in ae.group(1), "afterEnter 必须挡入场被打断的迟到清场(不杀 leave 拍循环)"
    assert al and "if (this.drawer.open) return;" in al.group(1), "afterLeave 必须挡收场被打断的迟到清场(不杀 enter 拍循环)"
    # --- 四皮肤 CSS 成对: 动画期裁剪 + 退场 absolute 底缘锚定(顶锚定会随槽位塌缩把面板顶跑) ---
    for ui in _UI_ALL:
        cssp = STATIC / ui / "css" / "dialogs.css"  # issue 26-10-20-2231: prism 也有了弹窗层, 四皮肤同路径
        css = cssp.read_text(encoding="utf-8")
        assert ".drawer-dock.drawer-anim { overflow: hidden; }" in css, f"{ui}: 缺 dock 动画期裁剪规则(四皮肤成对)"
        assert re.search(r"\.drawer-leave-active \{ position: absolute; left: 0; right: 0; bottom: 0;",
                         css), (f"{ui}: 退场必须 absolute 底缘锚定(bottom: 0, 面板沉下去而不是被顶跑)")
        # 判据只落在 .drawer-leave-active **自己的声明体**上: issue 26-10-20-2231 起 prism 的
        # 弹窗层文件里 .modal-mask(合法地用 inset: 0)排在抽屉段之前, 按"文件前段不得出现 inset: 0"
        # 判会把遮罩的合法写法当违规 —— 改成逐条抽该选择器的声明体来判(意图不变, 判据更窄)。
        for body in re.findall(r"\.drawer-leave-active[^{]*\{([^}]*)\}", css):
            assert "inset" not in body, f"{ui}: 退场不得用 inset: 0(顶锚定随槽位塌缩把面板顶跑)"


def test_drawer_leave_slot_freeze_w2() -> None:
    """W2 收场高度传导修复(计划 26-11-12-1048 §02/§04 S3, D9/D11): leave 期槽位整段冻结。

    旧机制逐帧写 dock.style.height/marginTop 跟缴面板 —— dock 是流内 sticky 元素, 文档随之
    逐帧变矮, 浏览器逐帧钳制 scrollY, 背景列表逐帧回弹(修复前真机逐帧取证: 收场位移事件
    8~11 次; e2e drawer-dock-stability W2 文档底用例判据 <=1)。新机制: 高度插值约束在已出流的
    面板层(leave-active absolute 底缘锚定), 槽位高度写一次整段冻结, 末帧一次性收拢 —— 文档底
    至多一次钳制(「钳制属预期」口径不动, D4), 非文档底零位移。判据/位移公式/三发
    挂点/_kbViewBottom 零改动(D3/D7), 本守阵只钉新机制接线与四皮肤 CSS 成对(R4/S3)。

    T6 边距生命周期改版(2026-11-13, 缺陷甲+乙, 本守阵按新口径如实改写): margin-top 呼吸距
    整体退出 JS —— 旧口径 enter 起拍清边距使文档凹陷 -8px(贴文档底 scrollY 被钳, Gecko 无
    Chromium 的同帧恢复, 钳制永久 -> 重开误发 reveal)、leave 末帧缴 0 + afterLeave 缴回 CSS =
    文档两段式(->0 再 ->8), 首段多钳的 -8 残差永久落在闭合行位上(实测行底 +8)。新口径: 槽位
    总占位 = margin(CSS 恒 8, JS 零写入) + height(JS 唯一写面), enter 全程单调不减、leave 单调
    降到关闭态总占位 8px, 文档两段式与起拍凹陷结构性消失(红验见 e2e T6 两用例)。"""
    drawer_js = _read("drawer.js")
    # --- T6 关系断言(缺陷甲的结构性保证): margin 写点在 drawer + shortcuts 两域聚合面零出现 ---
    # 写点与清点都不许有 —— 呼吸距恒在 CSS(8px, 四皮肤成对钉在下方), JS 一旦写 margin(不论
    # 写 0、写值还是 = "" 清点)都是旧两段式机制的复发面: enter 起拍写 0 = 文档凹陷 -8px
    # (Gecko 钳制永久), leave 末帧缴 0 + afterLeave 缴回 = 闭合行位 -8 残差。负向扫描按字面
    # "marginTop" 全量(覆盖 dock.style.marginTop / dock.style["marginTop"] / 任意接收者的
    # .style.marginTop 写法) + setProperty("margin-top") 单独钉(css 属性名写法不含 camelCase 字面)
    eng_margin = _read("shortcuts.js")  # T6 A 路线授权改动的另一半域(让位链), 同入负向扫描
    both_domains = drawer_js + eng_margin
    assert "marginTop" not in both_domains, (
        "marginTop 不得在 drawer + shortcuts 两域聚合面任何写法出现(dock.style.marginTop / "
        "style[\"marginTop\"] / 任意接收者同判 —— T6: margin-top 呼吸距恒在 CSS, 槽位总占位 = "
        "margin(恒 8) + height, JS 参与 margin 生命周期 = 起拍凹陷/两段式残差复发)"
    )
    assert not re.search(r"setProperty\([\"']margin-top", both_domains), (
        "setProperty(\"margin-top\") 是 margin 写入的第二语法面(css 属性名写法, 不含 camelCase "
        "字面), 必须与 marginTop 字面一并负向钉死(评审 minor: 只扫 dock.style.marginTop 一种写法"
        "且只扫 drawer 域时, 变体/另一域回归恒绿)"
    )
    leave = re.search(r"drawerLeaveHook\(el\) \{(.*?)\n    \},", drawer_js, re.S)
    assert leave, "drawer.js 聚合面找不到 drawerLeaveHook(拆分漂移? 同步本守阵)"
    lb = leave.group(1)
    # --- 槽位冻结: 高度写一次(动画期逐帧不动; margin 恒在 CSS 本就不冻结自不动), 逐帧循环里
    # 只准写面板自身高 ---
    assert 'dock.style.height = h0 + "px"' in lb, (
        "收场必须把 dock 槽位高一次性冻结(W2: dock 进文档高, 逐帧收回 = 逐帧钳制 scrollY; "
        "T6 口径下冻结态总占位 = margin(CSS 恒 8) + height, 文档高全程恒定)"
    )
    assert 'dock.style.height = "";' in lb, (
        "末帧必须把槽位高一次性收拢: 槽位总占位一步落回关闭态 margin 8 + height 0 = 8px"
        "(文档底至多一次钳制, D11 位移事件 <=1; margin 不缴 —— T6 两段式 ->0 再 ->8 的 -8 "
        "行位残差正是旧口径末帧缴边距所致)"
    )
    # 计数钉(评审加固, 取代旧的精确串负向钉): leave 函数体内 dock 高度写点恰 2 处
    # = 起拍冻结 1 + 末帧收拢 1 —— 逐帧跟缴旧机制不论 RHS 换成什么写法都会引入第 3 处写点
    # 破此计数, 比精确串匹配更能挡「机制语法变体回退」(旧断言只认旧写法, 变体回退两测全绿)
    assert lb.count("dock.style.height") == 2, (
        "leave 函数体内 dock.style.height 只许出现 2 次(冻结 1 + 末帧收拢 1): "
        "新增任何逐帧 dock 写(不论写法)= 文档逐帧变矮 = scrollY 逐帧钳制(旧机制复发)"
    )
    # afterLeave 兜底钉: 末帧已收拢, afterLeave 清 height 内联只服务打断路径; margin 无内联
    # 可清(T6 关系断言已钉全聚合面零出现), 不再有「缴回 CSS 8px」的第二段文档变化
    al = re.search(r"drawerAfterLeaveHook\(\) \{(.*?)\n    \},", drawer_js, re.S)
    assert al and 'dock.style.height = "";' in al.group(1), (
        "drawerAfterLeaveHook 必须清 dock 内联 height(打断路径兜底; T6: margin 无内联, 无第二段"
        "文档变化可兜)"
    )
    # --- 四皮肤 CSS 成对(R4/S3): 冻结机制依赖的几何契约逐皮肤钉住, 不出现只改一皮肤的漂移 ---
    # flux 与另三皮肤的差异只在入场(translateY(100%) 整幅上滑 + fx 骨令牌)与 RM 降级块,
    # 收场几何四皮肤同构 —— 本循环逐字钉收场面, flux 入场差异不进判据
    for ui in ("console", "flux", "prism", "atlas"):
        css = (STATIC / ui / "css" / "dialogs.css").read_text(encoding="utf-8")
        assert re.search(r"\.drawer-dock \{ position: sticky;",
                         css), (f"{ui}: .drawer-dock 必须流内 sticky(W2 前提: 槽位在文档流里, 冻结它文档高才恒定)")
        assert "margin-top: 8px" in css, f"{ui}: 缺呼吸距 margin-top 8px(四皮肤成对设计常量; T6 起它是呼吸距唯一持有者, JS 零写入)"
        assert ".drawer-dock.drawer-anim { overflow: hidden; }" in css, f"{ui}: 缺 dock 动画期裁剪规则(四皮肤成对)"
        assert ".drawer-leave-active { position: absolute; left: 0; right: 0; bottom: 0; pointer-events: none; }" in css, (
            f"{ui}: 退场必须 absolute 底缘锚定出流(W2 载体: 高度插值约束在不出流的层, 面板底边钉死向下收)"
        )
        assert ".drawer-leave-active { transition: transform .16s ease-in" in css, (
            f"{ui}: 退场 CSS 时长必须 160ms(与 JS 收场曲线同拍, 收场视觉时序保持)"
        )


def test_kb_reveal_clamp_complete_a() -> None:
    """T6 让位截断续缴(A 路线, 2026-11-14 用户拍板, 破 shortcuts_engine.js 零改动的显式授权)。

    缺陷面(S-A prism 前置红实证): 让位 scrollBy 的请求超过当下文档下滚余量时被 maxScroll 截断
    (enter 起拍槽位还塌着/文档底 gap=0, 让位头寸要等停靠槽位长高才出现), 行停在 (公式落点,
    请求落点) 之间 —— S-C 收紧后的触发界(行底>面板顶)对这种残位不再触发, 后续发不补
    (实测残位 面板顶-2, 差 14px; 改前靠「起拍凹陷多钳 8px 把残位留在带内」的巧合由后续发补齐)。

    续缴 = 「同一公式落点的续缴」, 不是新公式: 落点/判据走 _kbViewBottom/_kbViewBottomPad 单点
    逐帧复读, 差额按公式落点与当前位之差现算(重复触发不叠加, 幂等)。**已发起限定**(本机制不
    复活 S-C 杀掉的行为的关键): 登记只许出现在 _kbRevealRow 触发分支内、且须带「确被截断」判定
    —— 从未发起让位的行(含带内未覆盖行)绝不进本机制, 静态触发带一字不动。守卫: open 周期界
    (drawer.open/hash 逐帧守卫 + closeDrawer 显式 stop, 无跨周期残留 —— 旧 W1 教训)、delta<=0
    幂等收口、余量不足只等不发(盲发 = 再被钳 = 白发位移事件, D11 口径)、600ms 退避(槽位长高
    最长 400ms)、平滑在途停稳才缴(开门窗口瞬时/fx-glide 平滑按现行传输, fx-mount 零改动)。"""
    eng = _read("shortcuts.js")
    # --- 已发起限定: 续缴登记只许在触发分支内 scrollBy 之后, 且带截断判定 ---
    rv = re.search(r"_kbRevealRow\(hash\) \{(.*?)\n    \},", eng, re.S)
    assert rv, "shortcuts.js 缺 _kbRevealRow(让位单点被改名/搬走? 同步本守阵)"
    rb = rv.group(1)
    assert rb.count("_kbRevealCompleteStart") == 1, (
        "_kbRevealCompleteStart 只许在 _kbRevealRow 触发分支内登记一次(已发起限定): 分支外的登记"
        "= 静态触发带被放宽, 从未发起的行(含带内未覆盖行)会被主动抬起 —— S-C「未覆盖绝对不动」复发"
    )
    assert eng.count("this._kbRevealCompleteStart(") == 1, (
        "登记调用点必须 shortcuts.js 聚合面全文件唯一(文件级计数钉, 评审 minor): 只钉 _kbRevealRow "
        "函数体内的次数/顺序时, 未来其它方法对未发起行新增登记调用全部钉不红 —— 「从未发起的行绝不"
        "被机制抬起」在文件级失守"
    )
    idx_trigger = rb.index("rect.bottom > vBot + this._kbViewBottomPad()")
    idx_scrollby = rb.index("window.scrollBy(0, wanted)")
    idx_reg = rb.index("this._kbRevealCompleteStart(hash)")
    assert idx_trigger < idx_scrollby < idx_reg, ("续缴登记必须落在「触发判定 -> 发起 scrollBy 之后」: 未发起/未实际让位不得登记(已发起限定)")
    assert "document.documentElement.scrollHeight - document.documentElement.clientHeight" in rb, (
        "登记必须带截断判定(y0 + wanted 越过 maxScroll): 未截断的让位已足额落地, 登记续缴 = 白挂状态"
    )
    assert re.search(r"y0 \+ wanted > maxScroll \+ 0\.5", rb), (
        "截断判定按请求终点越界算(y0 + wanted > maxScroll), 与传输方式无关(瞬时和平滑的终点都受"
        "同一 maxScroll 钳制) —— 读发起后的 scrollY 判截断在平滑传输下恒假(动画未落地)"
    )
    # --- 续缴循环四守卫 + 传输/公式口径 ---
    start = re.search(r"_kbRevealCompleteStart\(hash\) \{(.*?)\n    \},", eng, re.S)
    assert start, "shortcuts.js 缺 _kbRevealCompleteStart(截断续缴单点)"
    sb = start.group(1)
    assert "!this.drawer.open" in sb and "this.drawer.hash !== hash" in sb, (
        "续缴循环必须带 open 周期守卫(drawer.open + hash 双查): 关面板/换目标 = 状态随周期作废, "
        "不得跨周期残留(旧 W1 跨周期登记量教训)"
    )
    assert "delta < 0.5" in sb, (
        "续缴必须幂等: 已到/越过公式落点(delta < 0.5 亚像素容差收口, 与:384 截断判定/:407 在途判定"
        "同一 0.5 口径)即收口, 重复触发不叠加不回修; 严格 delta<=0 在 DSF!=1 滚动像素吸附下恒 +ε"
        "残差过守卫, 回排循环每帧空转重发 no-op(评审 minor)"
    )
    assert "delta > headroom" in sb and "requestAnimationFrame(step)" in sb, (
        "余量不足(delta > headroom)只等不发: 盲发会被 maxScroll 再钳, 白发位移事件(D11 口径)且"
        "把截断固化为逐帧爬行"
    )
    assert "performance.now() - t0 > 600" in sb, (
        "续缴必须带 600ms 退避: 槽位长高最长 400ms(drawerEnterHook 强制收敛), 到点仍无余量说明"
        "截断与让位无关(后续文档变化), 放弃 —— 不许无限排队"
    )
    assert "Math.abs(y - lastY) > 0.5" in sb, ("平滑滚动在途(scrollY 仍在变)不得叠加发: 停稳才续缴, 否则逐帧抢发与平滑动画互相打架")
    assert "const landing = this._kbViewBottom() - 8" in sb, (
        "续缴落点必须走 _kbViewBottom 单点逐帧复读(同一公式落点的续缴, 不是新公式; vBot - 8 与"
        "_kbRevealRow 发起拍同式), 判据/补差分支语义不得在续缴里复制第二份"
    )
    assert sb.count("window.scrollBy") == 1 and "scrollIntoView" not in sb and "window.scrollTo" not in sb, (
        "续缴只许 window.scrollBy 一把(传输按现行窗口语义: 开门窗口瞬时/fx-glide 平滑, fx-mount "
        "零改动); 逐层滚动 API 是文件头禁令, scrollTo 会绕开增量口径"
    )
    send_idx = sb.index("window.scrollBy(0, delta)")
    step_tail = sb[send_idx:].split("\n      };")[0]  # send 到 step 体内收拢(方法末尾的初始排帧不在窗内)
    assert "this._kbRevealCompleteTimer = requestAnimationFrame(step);" in step_tail, (
        "发送后必须在 step 体内回排验证帧(发到收口为止, 评审 minor): 单发语义下平滑窗(fx-glide)里"
        "该发为平滑滚动, 被用户中途滚动打断/文档中途收缩再钳后行停在残位, 静态触发带对残位不触发,"
        "无人再补 —— 回排后次轮按既有守卫自然处置(delta<=0 收口/在途只等/再被钳只等, 600ms 退避兜底)"
    )
    assert "getBoundingClientRect" in sb and "data-hash" in sb, "续缴按行实测矩形现算差额(不按请求历史累加)"
    # --- 状态句柄与清理时机: 实例级非响应式 + closeDrawer 显式作废 ---
    assert "_kbRevealCompleteTimer" in sb and "cancelAnimationFrame" in sb, (
        "续缴必须走可取消的 rAF 句柄(_kbRevealCompleteTimer, 与 _drawerAnimRaf 同族: 实例级"
        "非响应式, 惰性初始化, 不进 state.js 的 data)"
    )
    stop = re.search(r"_kbRevealCompleteStop\(\) \{(.*?)\n    \},", eng, re.S)
    assert stop and "cancelAnimationFrame" in stop.group(1) and "_kbRevealCompleteTimer = 0" in stop.group(1), (
        "必须有 _kbRevealCompleteStop 单点(取消在途 rAF + 句柄归零)供 closeDrawer 显式清状态"
    )
    drawer_js = _read("drawer.js")
    close_fn = re.search(r"closeDrawer\(\) \{(.*?)\n    \},", drawer_js, re.S)
    assert close_fn and "this._kbRevealCompleteStop()" in close_fn.group(1), (
        "closeDrawer 必须显式 _kbRevealCompleteStop(状态清理时机 = open 周期终点): 只靠循环内的 "
        "open 守卫有一帧窗口, 快速关->重开同 hash 时旧拍续缴会跨周期复活(旧 W1 机理)"
    )
