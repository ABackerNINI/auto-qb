# 26-09-29-webui-tracker-focus-layer — 站点搜索改聚焦搜索层(方案C)

**Status:** Done
**Added:** 2026-09-29
**Updated:** 2026-09-29 22:10
**Topics:** webui-sites-page-search
**Summary:** 按 plans/26-09-29-0323 三方案拍板(用户选 C · 聚焦搜索层)重做 trackers 二级页搜索呈现层: 聚焦或有词即开层(暗幕 + 列表详情退隐 + 搜索行升面板), 命中面板三段式(头 = 命中数搬出输入框 + 键位 / 列表 = ↑↓ 活动高亮 / 尾 = 「新增站点「词」」快捷新增 + Esc 提示); 新增/导入收进 pill 行尾动作区与站点 pill 分形。收层路径四条(点命中/Esc/点暗幕/点外)一律走 hubTrackerStageClose 清词单点。纯前端零后端。26-09-29 深夜追加: 修上下键选中项闪烁(hover/act 同源打架 → mousemove+3px 位移门限接管 + CSS 摘 :hover 单路高亮, 子任务 6); 同族弹窗隐患与滚动跟随缺口入池 issues。22:10 认领滚动跟随缺口并修完(hubTrackerScrollActIntoView 手动 scrollTop 差值, 子任务 7)。

## 原始请求

用户报四痛点(搜索下拉覆盖站点设置不和谐 / 不支持 ↑↓ 与 Enter / 命中数挤占搜索框 / 新增与导入按钮和站点 pill 同形难分), 要求出三套模板选择; 拍板记录: plans/26-09-29-0323-plan-webui-sites-search-3-proposals.html(2026-09-29 选 C)。

## 思考过程与决策

- **跳转器拍板延续**: 「收层一律清词」(2026-09-28 拍板)在方案C下升级为收层单点 `hubTrackerStageClose(blurInput)` —— 四条收层路径全部过它, 不再各自清词; hubGo/hubBack 的离开分区清词也改走单点(聚焦态一并复位, 治「离开再回来层还开着」)。
- **开层语义**: `hubTrackerStageOpen = hub.trackerSearchFocus || hubTrackerActive`。因为所有收层都清词, 「有词但层收着」不存在, 开与 hubTrackerActive 同域; 空词聚焦时面板出语法引导(教学成本压进交互)。
- **IME 守卫是通则**: hubOnKey 顶部统一 `isComposing || keyCode===229` 早退(组词中 Esc 归输入法, 不再误清搜索词/关浮层); hubTrackerKeydown 同守卫护 ↑↓/Enter。
- **键盘活动项**: `hub.trackerHitIdx` 随命中集合重建重置为 0(Enter 即开第一命中, 对齐拍板样机); hover 与 ↑↓ 共写同一状态, 键鼠不打架。⚠ **此判断 26-09-29 深夜被用户实测证伪**: 共写正是闪烁根源(静止光标钉住悬停旧高亮 + 浏览器补发合成 hover 事件), 已修为 mousemove+3px 位移门限接管 + CSS 单路高亮(子任务 6 / pitfalls/web-ui/hover-keynav-fight)。
- **暗幕用字面黑**: `rgba(0,0,0,.45)` 与 `--shadow-*` 家族同口径(阴影/暗幕与皮肤无关), 不占用皮肤令牌; 刻意不用 backdrop-filter(性能坑 pitfalls/web-ui/css-perf-parity)。
- **pill 行不再 v-if 隐藏**: 搜索态整行退隐变暗(.3)留在背景里, 视觉上是「舞台让位」而非内容消失; 行尾动作区(新增 = `.hb-btn.dashed` 虚线 / 导入 = `.hb-btn.ghost` 幽灵)与实底站点 pill 分形(P4 拍板)。
- **快捷新增闭环**: 面板尾「新增站点「词」」调 `hubAddTracker(prefill)`, 搜索词直接进命名框 —— 搜不到就当场建。
- **3 方案模板与实现的关系**: 拍板样机(memory-bank/plans/26-09-29-0323)是交互口径的单点, 实现按其样机状态机逐条落地, CSS 类名回归 hb-tr-* 命名空间(hb-tr-stage/veil/drop-hd/drop-list/drop-ft/cur)。

## 实现计划

见 [plans/26-09-29-0323-plan-webui-sites-search-3-proposals.html](../plans/26-09-29-0323-plan-webui-sites-search-3-proposals.html) 方案C节(设计要点 / 实现落点 / 风险), 本档案不复制。

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | config_hub.js: hub.trackerSearchFocus/trackerHitIdx state + hubTrackerStageOpen computed + hubTrackerStageClose/hubTrackerKeydown 单点 + hubOnKey IME 守卫与 Esc 分支重写 + hubOnDocClick 点外(.hb-tr-stage) + hubAddTracker(prefill) | Done |
| 2 | settings.html: trackers 分支改聚焦层结构(stage/veil/面板三段式/命中行 act+当前标记/行尾动作区), 删 hb-tr-count 徽标 | Done |
| 3 | console_hub.css: hb-tr-stage/veil + 搜索行升层 + drop 三段式 + hit.act/cur + hb-btn.dashed + hb-pill-tail, 三皮肤令牌共用(暗幕字面黑除外) | Done |
| 4 | 守阵 test_frontend_tracker_search_wiring 重写(聚焦层结构/键盘/IME/收层单点四路径/CSS 成对) | Done |
| 5 | 真实 CSS 视觉快照三态目检(闲置/开层有命中/开层空态) + test.full 全绿基线 | Done |
| 6 | 上下键选中项闪烁修复: hubTrackerHoverIdx(mousemove+3px 位移门限) + CSS 摘 :hover 单路高亮 + 收层复位门限坐标 + 守阵 4 断言 | Done |
| 7 | 命中列表滚动跟随(26-09-29-2142): hubTrackerScrollActIntoView(getBoundingClientRect 差值调 scrollTop, 禁 scrollIntoView) + keydown $nextTick 挂接 + 守阵扩 4 断言 | Done |

## 进度日志

- **2026-09-29 04:15 (Done)**: 实施完成。真实 CSS 快照目检三态全过(控制台皮肤令牌真值); 守阵重写 1 条(收层四路径改断言 hubTrackerStageClose 单点 + 聚焦层结构 + IME); hb-tr-count 类随模板删除连带清 CSS。中间产物: plans/26-09-29-0323 三方案可交互模板(真浏览器冒烟过, harness 键盘事件管道不派发, ↑↓Enter 用页面内合成事件验证 —— 样机与实现共用同一条处理语义)。
- **2026-09-29 04:35 (Done)**: 提交流程合并远端 3 笔(HR v3 重建 be83d61 配置 40→14 键 + 两笔修复, da09e20→05a8415), stash 腾挪零冲突; 在合并后新基线上重测: test.full **1736 passed + 3 skipped / 90%**(26.26s; 数字较本轮首测 1831/91% 的差全部来自远端 HR v3 的守阵增删, 非本轮改动; 基线切片 [26-09-29-0415](../testing/baselines/26-09-29-0415-webui-tracker-focus-layer.md) 已按新基线回写)。待「提交」指令由 ship.commit 入库。
- **2026-09-29 21:45 (Done)**: 用户报「搜索框结果上下键选中项偶尔异常闪烁」。取证: ↑↓ 只切 class 不重建列表, 纯键盘路径不可能闪 —— 闪源是悬停/键盘两路同源高亮打架(mouseenter + CSS :hover 与 act 同源) + 浏览器对静止光标补发合成 hover 事件(入场动画/滚动/DOM 变更后)。修: hubTrackerHoverIdx(mousemove+3px 位移门限)接管悬停 + CSS 摘 :hover(.act 单路) + box-shadow 补 transition + 收层复位 trackerMouseAt; 守阵 4 断言(禁止 @mouseenter 回潮等)。同轮入池 2 bug(命中列表滚动跟随缺口 / 弹窗分类·标签下拉同族隐患, 26-09-29-2142) + 新坑 pitfalls/web-ui/hover-keynav-fight。test.full **1751 passed + 2 skipped / 91%**(12442 语句 / 999 未覆盖, 31.32s, rc=0), 基线切片 [26-09-29-2145](../testing/baselines/26-09-29-2145-webui-tracker-focus-layer.md)。
- **2026-09-29 22:10 (Done)**: 认领 issue 26-09-29-2142-bug-tracker-hit-keynav-scroll(命中列表 300px 超屏后 ↑↓ 无滚动跟随)。修: config_hub.js 新增 hubTrackerScrollActIntoView(getBoundingClientRect 差值手动调 scrollTop, block:"nearest" 语义; 禁 scrollIntoView —— 逐层滚祖先会连带滚暗幕后面的整页), keydown ↑↓ 分支改 idx 后 $nextTick 挂接(等 .act 类挪到新行再量); 合成 mousemove 由子任务 6 的 3px 门限挡掉(pitfalls/web-ui/hover-keynav-fight 处置④依赖兑现)。守阵 test_frontend_tracker_search_wiring 扩 4 断言(②b: 必须挂接/实现存在/差值法/禁 scrollIntoView)。test.full **1751 passed + 2 skipped / 91%**(30.35s, rc=0), 基线切片 [26-09-29-2210](../testing/baselines/26-09-29-2210-webui-tracker-keynav-scroll.md)。待「提交」指令由 ship.commit 入库。
