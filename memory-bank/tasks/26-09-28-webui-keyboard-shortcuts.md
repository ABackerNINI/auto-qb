# 26-09-28-webui-keyboard-shortcuts — WEBUI 键盘快捷键(可自定义): 成熟方案调研 + 存储定案

**Status:** Done
**Added:** 2026-09-28
**Updated:** 2026-10-09
**Summary:** 前案 26-09-26-0822 (localStorage 预选) 经成熟方案调研与存储对比后被 26-09-28-0354 取代(0822 置 Superseded): 定案后端独立文件 auto-qb-data/webui-keys.json + GET/PUT /api/keys(金清单+2); 引擎不引库自写 ~200 行(tinykeys 为参照), 沿 0822 注册表/e.code/作用域/三段屏蔽设计; 自定义面板进设置页「快捷键」分区 + ? 浮层。§08 六决策点已全部拍板(2026-09-30, ① 五轮收敛至 v4 终版): ①危险档一律二键组合(修饰键+字母, 非裸键非三键)+确认框兜底(默认确定/Enter 确认)—— 删除=Shift+D(另有 Delete 键作为额外删除操作无需绑定, 直连 _deleteFlow, 即删除双快捷键入口), 重新校验=Shift+Y, 强制汇报=Shift+A; 裸键 D/C/F 释放空位; ②光标只走组行; ③Shift 族保留; ④不加顶栏按钮; ⑤取消一次做完, W1-W4 第一波先行、W5-W7 第二波; ⑥后端文件。注册表 58 条(52 默认+6 空位)。存储 schema 预埋 {template, overrides}, 绑定模板机制确认缓议仅预埋(§4.7)。2026-09-30 追加: 用户报键鼠割裂(鼠标顶部按键跳底), 调研报告 26-09-30-1806 落地(根因=点击不回写 kbCursor + 无光标↑落末行的极值回落; 推荐方案 B); 同日用户拍板按方案 B 实施, 已落地(五入口回写 kbCursor / 回落改视口就近 _kbViewportRow / 明细成员行补光标视觉 / 守阵 17 条), 随本提交入库。2026-10-09 追加: 快捷键「改为切换语义」适配性分析报告 26-10-09-1731 落地 —— 注册表 59 条判定 **6 适合**(流量图 Ctrl+\ / 统计 \ / 历史 Shift+\ / 详情面板 I / 帮助 Shift+/ / 列选择器 K) / **4 有条件**(详情页签 Alt+1~5 / Enter / 限速 L / 设置 Ctrl+,) / **49 不适合**; 判定 5 准则(C1 界面显隐 / C2 关闭无副作用 / C3 键位语义单一 / C4 重复按下期望明确 / C5 有开关基础); 关键实现约束 = 浮层屏蔽闸门 `_kbOverlayBusy` 吞第二次按键, 抽屉类零障碍、浮层类需放行。
**Topics:** webui-keyboard-shortcuts
**Refs:** memory-bank/plans/26-09-28-0354-plan-webui-keyboard-shortcuts.html, memory-bank/plans/26-09-26-0822-plan-webui-keyboard-shortcuts.html, memory-bank/tasks/26-09-28-webui-settings-back-nav.md, memory-bank/reports/26-09-30-1806-report-webui-keymouse-cohesion.html, memory-bank/reports/26-10-09-1731-report-webui-shortcuts-toggle-suitability.html, memory-bank/activeContext/26-10-09-1759-webui-shortcuts-toggle-suitability.md

## 原始请求

为 WEBUI 添加键盘快捷键, 调研成熟的设计方案; 需要支持自定义, 自定义在设置里; 存储在后端单独文件还是前端 localStorage 需要对比分析优劣; 写一份计划(只计划不改代码)。

## 思考过程与决策

- **调研(外部, 2026-09-28 实测)**: 支持逐条重映射的成熟产品只有 Gmail(服务端账号)/VS Code(keybindings.json 本地文件+可选按 OS 同步)/JupyterLab(服务端 $HOME/.jupyter 用户文件 JSON5) 三家, **无一用 localStorage 作正式存储**(vscode.dev 未登录只是兜底); 库横评: tinykeys 4.0.1 最活跃且 key+code 双匹配(UMD 1.1KB gzip), hotkeys-js/keyCode 系与 e.code 设计相抵, @github/hotkey 仅 ESM, Mousetrap/keymaster 停更, react-hotkeys-hook 需构建。
- **不引库自写**: 「可自定义」完整栈(录制器/冲突/黑名单/作用域接线/存储)没有库覆盖, 库只解决派发 ~40 行; tinykeys ~6.4KB 源码作实现细节参照(isComposing/repeat/AltGraph/defaultPrevented/$mod)。
- **存储定案(建议)**: 后端独立文件。0822 把「服务端持久化」等同「写 config.yml 红线」是假二分 —— 独立文件既不碰 config.yml 也不碰 state.json(黄金法则 5 主循环单写线程, web 线程本就不能写 state); localStorage 的失效通道(浏览器「关闭窗口时清除站点数据」)在本项目列偏好上已实际发生(pitfalls/web-ui/columns-persist.md), 且快捷键是「用户逐条录制的配置」, 信息价值高于列宽/主题这类可低成本重派生的偏好 —— 两范式并存各安其位, 不是破坏一致性。
- **沿袭 0822**: 注册表单一事实源 AQB_KEYS(58 条=52 默认+6 空位)/e.code 归一化/scope 五值/输入态三段屏蔽/Esc 唯一 fixed 接 lifecycle 退栈链尾/kbCursor 光标/_actCore 唯一重构点。
- **新增修订**: 字符语义键与 code 的权衡按 MDN 口径落注; 黑名单以 Chromium reserved accelerators + Firefox bug 1052569 为准(Ctrl+W/T/N/Q 不可拦); 录制器走 VS Code ⌘K⌘K 模式; 跨标签语义明示为「刷新后生效」(与 config 保存语义一致, 混合镜像方案缓议)。

## 实现计划

波次(可拆口 W1-W4 先行交付默认键位, W5-W6 第二波): W1 引擎+注册表+适配器桩 → W2 光标模型+滚动进视口 → W3 目标解析+commands._actCore 抽取 → W4 绑定 A-D 组 → W5 绑定 E-H+局部作用域 → W6 后端 webui-keys.json + GET/PUT /api/keys + 金清单 + 面板录制器 → W7 静态守阵 + 真机走查 + 文档回写。可拆口: W1-W4 先行交付默认键位, W5-W6 第二波。

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | 前案 0822 可行性分析 | Done (26-09-26) |
| 2 | 成熟方案调研(产品/库/坑/上游) + 存储对比分析 → 计划 26-09-28-0354 | Done |
| 3 | §08 六个决策点拍板(核心: 存储定案) | Done (2026-09-30 全部拍板, ①③改向见进度日志) |
| 4 | W1-W7 实施 | Done (W1-W4 2026-09-30 第一波; W5-W7 2026-09-30 第二波, 未提交) |
| 5 | 收尾回写(基线/progress/pitfalls) | Done (两波基线切片 26-09-30-0555 / 26-09-30-0702; 新坑 js-comment-terminator) |
| 6 | 键鼠割裂调研(用户报障) → 报告 + 方案推荐 | Done (26-09-30, 报告 [26-09-30-1806](../reports/26-09-30-1806-report-webui-keymouse-cohesion.html), 方案 B 待拍板) |
| 7 | 方案 B 实施(点击落光标 + 回落视口就近) | Done (2026-09-30) |
| 8 | Shift 连选起点统一(计划 26-10-02-0608 方案 B) | Done (2026-10-02, W1-W5 全落地, 已入库 `fa79d526`) |
| 9 | 快捷键「改为切换语义」适配性分析(用户命题) → 报告 | Done (26-10-09, 报告 [26-10-09-1731](../reports/26-10-09-1731-report-webui-shortcuts-toggle-suitability.html), 判定 6 适合 / 4 有条件 / 49 不适合; 待拍板是否实施) |

## 进度日志

- 2026-09-28 03:54 调研与计划落地(未动代码): 计划 26-09-28-0354 立档, 0822 置 Superseded 并回链; 6 决策点建议案就绪, 等拍板。
- 2026-09-30 决策点①拍板: 用户点出无修饰单键的误触风险(如单键触发重新校验), 定案「无修饰单键为主 + 快捷键触发的危险操作一律加确认框, 确认框默认『确定』/ Enter 即确认」; 已回写计划 §08 与 W4 验收行。余 ②-⑥ 待拍板(②用户已问语义, 待解释后定)。
- 2026-09-30 六项全部拍板: ①升级 v2 —— 无修饰单键一律不绑危险操作, 危险清单逐条盘点(0822 键表 A-H 组 52 默认键): 删除 D8 `D`→Ctrl+Alt+D / 重新校验 D4 `C`→Ctrl+Alt+C / 强制汇报 D3 `F`→Ctrl+Alt+F(均确认框), 强制开始 Shift+F 与超级做种(空位)/放弃改动(不绑)评审后保持; 裸键 D/C/F 释放为空位, danger 禁绑裸键默认表与面板双侧执行。③改向: Shift 族保留(E 组 7 条 + F5/F6)。②④⑤⑥按建议案(组行线性链 / 不加顶栏 / W1-W7 一次 / 后端文件)。存储 schema 预埋 {template, overrides}; 绑定模板机制(切换/派生/导入导出)预研可行(+150-250 行)记入计划 §4.7 缓议, 用户未拍板做。计划状态改「拍板齐, 待实施」。
- 2026-09-30 ①⑤再改向 (v3): ①取消 Ctrl+Alt 三键, 以单手操作为主 —— 危险操作回到单键默认 + 确认框兜底: 删除=Delete 键(上游对齐, 字母 D 释放为空位), 重新校验还原 C, 强制汇报还原 F; 面板 danger 条目改回 0822 §06 口径「⚠ 单键触发 (有确认框)」标注, 不再拒绑裸键。⑤取消「W1-W7 一次做完」, 按原拆口: W1-W4 第一波(默认键位), W5-W7 第二波。模板机制确认缓议·仅预埋(schema {template, overrides} 不变)。
- 2026-09-30 ① v3 修正: 危险档选键仅两条(重新校验 C / 强制汇报 F); Delete 键算额外的删除操作, 无需绑定 —— 不占键表槽位、不进注册表与面板改键列表, 引擎里直连 _deleteFlow; 字母 D 释放为空位。注册表 58→57 条(51 默认+6 空位)。计划 §08/§5.1/W4/§07 已联动修正。
- 2026-09-30 ① 终版 v4: 危险操作一律二键组合(一个修饰键+字母; 非裸键、非三键), Delete 也算危险操作且保留额外操作身份 —— 删除绑定两个快捷键: Shift+D(注册表默认) + Delete(额外操作, 无需绑定直连 _deleteFlow); 重新校验=Shift+Y(验), 强制汇报=Shift+A(reAnnounce); 均确认框兜底(默认确定/Enter)。裸键 D/C/F 释放空位; 注册表回到 58 条(52 默认+6 空位); 面板 danger 条目标「⚠ 危险操作 (有确认框)」, 自绑裸键提示但允许。计划 §08/§5.1/§5.2/W4/§07 已联动修正。
- 2026-09-30 05:55 **W1-W4 第一波实施完成, 未提交**(等用户「提交」指令): shared/shortcuts.js 新增(引擎 e.code 归一化 + 六道拦截 + 黑名单 + 注册表 + 适配器桩 window.AQB_KEYS 内存实现 + 光标/目标解析/键位动作); 光标滚动进视口走 getBoundingClientRect 差值 + columns._rowWindow 留存 _rowPre(禁 scrollIntoView, hover-keynav-fight 坑档); commands._actCore 抽取, act/actTorrent/bulkAct/actEpisode 四入口收敛(端点按目标形态路由, recheck 恒 bulk/单种子种子级); Delete 直连 _kbDelete->_deleteFlow(注册表外, §08 v4); 模态确认框默认焦点落「确定」(ref=modalOk, Enter 即确认)。当波守阵 tests/test_web_shortcuts.py 10 条; test.full **1802 passed + 3 skipped / 91%**(基线 [26-09-30-0555](../testing/baselines/26-09-30-0555-webui-keyboard-w1w4.md)); Playwright 探针 30 项功能验证全过(光标/选择/危险档确认框/输入态屏蔽/设置页不串扰)。
  - 与计划文字偏差两处: ①注册表落地 55 条(51 默认+4 空位)而非 58 —— H2(面板 Esc)归 W6 面板自身不进注册表; I 组文件优先级 x4 / 按列排序未注册(0822 自评「需二层光标, 复杂度不划算」/「绑键不现实」), W6 面板动工时再议补齐。②危险档确认框无逐条接线 —— 模态原语统一实现默认焦点+Enter 确认(§08 对确认框的要求由 _openModal 单点满足, 删除类既有确认框同样受益)。
  - 实施前既有红 3 条(计划会话遗留, 已修): 任务档案 Status「Ready」与计划 doc-status「拍板齐, 待实施」不在守阵词表 → 改 In Progress + kb.index 重建。
  - 冒烟既有失败 3 项(dev.harness, stash 前后对照确认先在、与本波无关): 追剧集行 CTX-03 多选右键(确定性)、辅种组行 CTX-03(抖动)、列设置隐藏列宽保留(确定性) —— 未修(范围守恒), 已入池 issues/26-09-30-0602-test-ui-smoke-ctx03-multiselect 与 26-09-30-0602-test-ui-smoke-colwidth-hidden-preserve(2026-09-30)。
- 2026-09-30 06:00 W1-W4 第一波提交入库(38ffec5, 用户「提交」指令)。
- 2026-09-30 07:02 **W5-W7 第二波实施完成, 未提交**(等用户「提交」指令; 基线 [26-09-30-0702](../testing/baselines/26-09-30-0702-webui-keyboard-w5w7.md), test.full **1813 passed + 3 skipped / 91%**, 较第一波 +11 条):
  - **W5 绑定+局部作用域**: E/F/I 组 run 全量接线(单目标动作目标解析要求恰一 hash —— `_kbSingleHash`, 多选/整组/剧集单元一律提示不猜第一个; 复用 editMove/editRename/copyTorrentInfo/exportTorrent/torrentCmd 既有单种链, 不另写实现); `_kbScope` 三档全量生效(设置页/抽屉/列表), 抽屉 Alt+1-4 切页, 设置页 Ctrl+S inputSafe, 引擎模态白名单分流(模态内只响应模态键位, 本期注册表无 modal 条目, 预留分支由静态守阵钉住); 浮层打开只放行焦点局部(drawer/settings)键位, 列表键位在浮层下仍失效; Delete 直连分支随引擎重构并入无条目路径并补浮层+作用域守卫。
  - **W6 后端持久化+面板**: 新 routes/keys.py —— GET/PUT /api/keys, 存储 auto-qb-data/webui-keys.json(与 web.token 同寻址), 读时兜底链 主文件→.bak→默认表(逐级 WARN), PUT 结构校验 422 不触碰磁盘 + atomic_write keep_backup, 金清单 +2; 适配器接通(AQB_KEYS.reload/save, **load 保持同步快照**——引擎 keydown 内现取不 await; startPolling 作为两条登录路径唯一汇合点拉真值, 失败静默回默认表); 设置页「快捷键」分区(首页卡+hubNow+hubRestore 认 keys, 客户端块同「运行日志」先例): VS Code 按下即录录制器(捕获段监听+stopPropagation, 引擎/退栈链/hubOnKey 都收不到), 纯修饰键拒收 / Esc 取消 / 黑名单当场拒绑 / 冲突三选一(交换/覆盖对方置空/取消) / 单条与全部重置 / 空串=显式禁用 / danger 裸键提示但允许 / 保存 PUT 失败本地回滚 / 离开未保存先确认(hubGo+hubBack 双挂 kbGuardLeave); 帮助浮层 Shift+Slash(只读速查 + 前往设置自定义; Esc 归退栈链, 名单三处同步: 退栈链/escBusy/_kbOverlayBusy)。
  - **W7 守阵+验证**: test_web_shortcuts.py 10→16(+6), test_web.py 金清单+2 与 keys 后端 +5; Playwright 探针 28 项全过(面板/录制器/冲突/保存刷新生效/抽屉 Alt 切页/E-F 组/设置页 Ctrl+S), dev.harness 96 项 prism 无新增失败(同败 2 项既有, 抖动项本轮未复现); 新坑入档 pitfalls/web-ui/js-comment-terminator.md(块注释内 `*/` 提前终止, node --check 仍绿运行时才炸 —— 实测踩中, 探针 pageerror 抓到)。
- 2026-09-30 18:06 **键鼠割裂调研落地(纯调研, 未动代码)**: 用户报「上下键与鼠标点击割裂感很强, 鼠标在顶部操作按一下键盘跳到最下方」。代码取证三场景: S1 无光标回落口径( `_kbMove` cur<0 时 ↓→首行/**↑→末行**, shortcuts.js:465-469, 注释自称「就近」实为极值回落) → 跳底直接来源; S2 五个鼠标点击入口(selection.js)从不回写 kbCursor(全仓写点仅 state.js:176 + shortcuts.js), 键盘从旧位置出发; S3 残留光标(身份重定位让旧光标跨轮询存活, 按键跳回)。业界调研(WAI-ARIA APG 初始焦点=选中项 / VS Code focus·selection·anchor 三 trait + reveal 最小滚动 no-op / Gmail 点击落光标 / Win32 LVM_SETSELECTIONMARK / Downshift·react-aria·AG Grid 默认行为)收敛三法则: 光标三分独立建模 / **点击是键鼠衔接点** / 视口最小跟随+刷新不滚动。对照六项达标四项(身份光标/最小滚动/刷新不动/hover 纯 CSS), 缺「点击衔接」与「回落口径」两处。报告 [26-09-30-1806](../reports/26-09-30-1806-report-webui-keymouse-cohesion.html): 推荐方案 B(回落改视口就近 + 点击入口回写 kbCursor; 落光标≠选中, 不违反 2026-09-17 普通点击不选中口径; 唯一口径决策点=普通点击出现 kb-cursor 视觉反馈), 方案 C(roving tabindex/aria-activedescendant)缓议。**待用户拍板后另出计划文档实施**(范围守恒: 本轮只出报告)。
- 2026-09-30 19:53 **方案 B 实施完成, 未提交**(用户指令「实施计划…按推荐方案」直接拍板实施, 未另出计划 HTML —— 以报告 §06/§07 为实施口径; 决策细节在本条)。改动 6 文件:
  - **回落口径(S1)**: `_kbMove` cur<0 分支改走新 `_kbViewportRow(rows, delta)` —— ↓ 落视口内首行、↑ 落视口内末行(视口就近, 修「一按 ↑ 跳到底」)。两条解析路: ①group/torrent 窗口化视图用 `_rowPre` 前缀和换算文档 y(与 `_kbScrollRowIntoView` 同源, `pre.length === rows.length + 1` 同源校验, 不符放弃 —— P1-2 退避口径); ②其余(追剧页全量渲染 / 小列表 <ROW_WIN_MIN=200 不开窗 / 前缀失效)扫渲染行可见性(`querySelectorAll("[data-key], [data-hash]")` + getBoundingClientRect, v-if 保证 DOM 只有当前视图)。都解析不出 → 退回旧口径 ↓首行/↑末行。只读几何, 滚动仍只归 `_kbApplyCursor`(键盘路径), 点击路径不滚动(点击行必在视口内)。
  - **点击落光标(S2/S3)**: selection.js 五入口(onGroupClick/onMemberClick/onTorrentClick/onShowClick/onShowEpClick)首行按所在行回写 kbCursor, 写在修饰键分支之前 —— Ctrl/Shift+点击在选中语义之外同样落光标; 落光标≠选中(只写 focus 语义, 不动 selGroups/selMembers/selAnchor*)。明细成员行点击落 `{kind:"torrent", id:hash}`: 该身份不在组行线性链(决策② 成员行 vNext), 下一次 ↑↓ 经视口就近回落落到链行, 而动作键目标解析(`_kbTargets` kind=torrent 分支)立即生效。
  - **视觉补齐**: 报告「视觉双轨已就位」对明细成员行不成立 —— groups.html / shows.html 两处 member-row 缺 kb-cursor 绑定(光标链不含成员行故键盘路径到不了, 报告口径偏差), 按方案 B「点击行出现光标环」补齐(`'kb-cursor': isKbCursor('torrent', m.hash)`; `.kb-cursor` 是共用层通用类, 无需改 CSS)。
  - **文案与注释**: `_kbHint` 改「先点选一行, 或用 ↑↓ / Home / End 定位目标」(不再教「先用 ↑↓ 移到一行」—— 点过就行); shortcuts.js 头注 + state.js kbCursor 注释同步方案 B 口径。
  - **守阵**: test_web_shortcuts.py 16→17 —— 新增 test_click_lands_cursor_and_viewport_fallback(五入口回写断言+必须写在修饰键分支之前 / `_kbMove` 不得直写极值回落 / `_kbViewportRow` 前缀和同源校验+渲染行扫描+保守退路+禁 scrollIntoView); test_cursor_scroll_follow_without_scrollintoview 模板断言 3→5 行(补两处成员行)。
  - 实测: test.full **1851 passed + 3 skipped / 90%**(基线 [26-09-30-1953](../testing/baselines/26-09-30-1953-webui-keymouse-planb.md); 19:53 初测 01e47169+本轮 1844+3, 提交前合流内核 P1(2174a568, 与本轮无关的后端模块化)后复核 20:10, P1 带 +7)。node --check 三 JS 全绿。方案 C(roving tabindex)仍缓议 —— B 的状态模型与 C 兼容。
- 2026-10-02 06:08 **Shift 连选起点计划入库(纯计划, 未动代码)**: 用户报「Shift 连选起点与键鼠联动脱节 —— 鼠标点过第 5 行按 Shift+↓ 却从列表第一行起选」。出计划 [plans/26-10-02-0608](../plans/26-10-02-0608-plan-webui-shift-anchor.html)(Open, 待拍板): 根因=方案 B 统一了**光标**(focus)却没统一**起点**(anchor) —— 点击落 kbCursor, 但 Shift 区间起点仍走另一套 `selAnchor*` 状态机(仅由 Ctrl/⌘ 点击与展开写入), 为空时四处消费者一律兜底 `list[0]`。取证 G1-G5 / 复现矩阵 M1-M8 / 方案 A(只改兜底)/B(推荐)/C(起点与光标合并, 不可行)比选 / 实施波次 W1-W5 / 4 个口径决策点。代码事实核对截至 2359a3d1。
- 2026-10-02 06:35 **Shift 连选起点实施完成, 未提交**(用户指令「按推荐实施计划 26-10-02-0608」= 拍板方案 B + 4 决策点建议案; 基线 [26-10-02-0635](../testing/baselines/26-10-02-0635-webui-shift-anchor.md), test.full **2290 passed + 3 skipped / 99%**, 守阵 18→19)。改动 4 文件(纯前端):
  - **W1 起点解析单点化(selection.js)**: 新增 `_selAnchorField(kind)` / `_selCursorId(kind)` / `_selAnchor(kind, list)` / `_selSetAnchor(kind, id)` / `_selContext()`; 兜底链收敛为 **显式锚点(有效) → 当前光标(有效) → [group: `expandedKey`] → 列表首行**(`_selAnchor` 内唯一一处 `ids[0]`)。四处消费者改调用: `shiftGroupSel`(`_selAnchor("group", list)`) / `shiftMemberSel` / `shiftTorrentSel`(均 `"member"`) / `_extendUnit`(`"unit", units`) —— 消掉「四处各写一遍 `list[0]`」的口径漂移源。
  - **W2 点击落起点(selection.js 五入口)**: `onGroupClick`/`onMemberClick`/`onTorrentClick`/`onShowClick`/`onShowEpClick` 在修饰键分支**之前**补 `if (!event.shiftKey) this._selSetAnchor(...)`。**关键口径修正**: 计划文字说「不写 Shift 分支」又要求「写在修饰键分支之前」—— 两者只能靠 `!event.shiftKey` 守卫同时满足(无条件早写会让 Shift+点击把起点重置到目标行, M1 退化成只选一行; 已按验收表 §7.1 的 M1=5–20 定夺)。Ctrl/⌘ 路径值与 `toggle*Sel` 写入相同, 幂等无害。
  - **W3 键盘手势原点(shortcuts.js)**: 新增 `_selSeedAnchorFromCursor()`(走 `_selContext()` 取当前视图 {kind, ids}, 已有有效起点则**不动** —— 法则 2), `_kbExtend` 开头在 `this._kbMove(delta)` **之前**调用(顺序反了光标已移动 ⇒ 区间塌成单行, 即 G2)。
  - **W4 追剧页区间化(selection.js)**: `_extendUnit` 的起点解析改走 `_selAnchor("unit", units)`; 只有 units 为空或目标不在 units 时才保留 `_toggleUnit` 兜底(修 M7/M8 首拍退化为单单元切换)。
  - **W5 守阵+回写**: `tests/test_web_shortcuts.py` 新增 `test_shift_anchor_unified`(五入口落起点+排除 Shift+写在 ctrlKey 前 / 四消费者无裸 `list[0]` / `_selAnchor` 兜底链三环 / `_selSetAnchor` 不碰选中集合 / `_kbExtend` 落起点先于 `_kbMove`), docstring 测试计划清单 +1; `state.js` 三锚点字段注释、`selection.js`/`shortcuts.js` 头注同步。
  - **行为口径未变**: 普通点击仍不选中(落起点只写 `selAnchor*`) / Shift 不重置起点 / 滚动仍只在键盘路径(`_kbApplyCursor`, 点击路径不滚) / 禁 `scrollIntoView` / FX-11 组-成员互斥清理不变 / 无 Python src / 配置键 / 后端改动。
  - 冒烟: dev.harness + ui_smoke.cjs(3000 种子)80 PASS + 2 FAIL, 失败项 = 既有的吸顶遮挡间歇失败(**stash 前后对照同行号同项数**确认先在, 与本笔无关, 范围守恒未修); 提交前并入 `eae2aede`(改 console_hub.css / xtpl.html)后重测仍同 80 PASS + 同 2 项同行号; 无 pageerror / console.error。
  - 未做: 真机实弹走查(计划 §07.1 的 M1-M8 行为验收)留给用户。



- 2026-10-04 18:41 — 状态 In Progress → Done：计划 26-09-28-0354 全部落地: 后端 auto-qb-data/webui-keys.json + GET/PUT /api/keys, 自写引擎, 注册表 58 条; 后续键鼠割裂修复由 26-10-02-webui-nav-focus / webui-esc-clear-filters(均 Done)接走。
- 2026-10-09 17:59 **快捷键「改为切换语义」适配性分析落地(纯调研, 未动代码)**: 用户命题「分析快捷键中哪些适合改为切换类型(如 qB 流量图 —— 按一下打开、再按一下关闭), 写报告含适合/不适合表格」。对注册表 59 条(另 Delete 注册表外)逐条判定, 先立 5 准则(C1 界面显隐 / C2 关闭无副作用 / C3 键位语义单一 / C4 重复按下期望明确 / C5 有开关基础)。**判定**: 6 适合 —— 流量图 `Ctrl+\`(用户点名; 入口 `openQbHistory→openDrawerTraffic` 同目标**幂等短路**是「再按无反应」根因, 改短路为 `closeDrawer()` 即可)、统计 `\`、历史 `Shift+\`、详情面板 `I`、帮助 `Shift+/`、列选择器 `K`(`toggleColMenu` 本身即切换函数, 仅被浮层屏蔽挡住); 4 有条件 —— 详情页签 `Alt+1~5`(已双态, 可补「同页签再按 ⇒ 关」)、`Enter`(组行已开关/种子行不建议兼关)、限速 `L`(含输入框, 关闭丢输入)、设置 `Ctrl+,`(页面导航, 无关闭语义); 49 不适合 —— 导航 / 表单对话框 / 后端命令与危险动作 / 队列 / qB 状态开关(本身即 toggle 但切的是状态非显隐)/ 光标移动 / 已成对的展开收起 / 选择 / 多档循环 `[`/`]`。**关键实现约束**: 浮层屏蔽闸门 `_kbOverlayBusy` 会吞掉第二次按键 —— 抽屉类(流量图/详情)已不在名单、第二按直达(零障碍), 浮层类(统计/历史/帮助/列选择器)需给「自切换放行白名单」; 切换是 `run` 内分支, 不改注册表结构、不动键表, `Esc` 仍是统一关闭出口。报告 [26-10-09-1731](../reports/26-10-09-1731-report-webui-shortcuts-toggle-suitability.html)(§03 总判定表 / §04-06 详解 / §07 约束 / §08 全量清单)。**范围守恒: 本轮只出报告, 是否实施待用户拍板。**