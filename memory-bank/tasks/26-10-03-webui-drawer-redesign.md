# 26-10-03-webui-drawer-redesign — WEBUI 种子详情抽屉重设计

**Status:** Done
**Added:** 2026-10-03
**Updated:** 2026-10-03
**Summary:** 方案A四波实施+收尾全部完成: W1 停靠骨架(`f994ce20` 浮层→底部停靠面板, 摘遮罩与blur=PERF-01归零收尾) → W2 键盘跟随流(`9c594e1e` scope存活+Alt+1~4双态+详情防抖跟随) → W3 高度治理(`b81a1ee4` 拖拽调高+收起钮+高度持久化+D1首屏默认收起) → W4 回归验证(`a0b5d73f` ≤900px全屏降级D3+停靠几何修复_kbViewBottom+轮询可见性守卫+基线切片26-10-03-1335) → W5 收尾回写(三issue置Done+本档案收口+计划doc-status→Done+坑档复发1条)。拍板 D1默认收起/D2 Enter仅跟随不关/D3 ≤900px全屏覆盖/D4 C波次废弃, 全按计划推荐项落地。测试: test.quick 2326→2328, test.full **2329 passed + 3 skipped / 99%**; 冒烟走查单24项×三皮肤全过。
**Topics:** webui-drawer-redesign
**Refs:** memory-bank/reports/26-10-03-0759-report-webui-drawer-redesign.html,memory-bank/plans/26-10-03-0917-plan-webui-drawer-redesign.html

## 原始请求

用户指派 (2026-10-03): 解决 3 个池内 issue —— 26-10-01-2108-feat-webui-shortcuts-drawer-nav (抽屉打开时上下键切种子) / 26-10-01-2108-feat-webui-shortcuts-drawer-open (Alt+1~4 列表侧直接开抽屉定位页签) / 26-10-01-2119-feat-webui-drawer-redesign (抽屉整体重做); 追加关键约束: 目前抽屉显示时模糊种子列表, 键盘切换时看不清当前选中行, 重设计必须解决; 要求调研成熟方案, 做 3 个简单模板供选择, 写一份报告。流程要求: 主会话只委派总结不实施, 串行派单防超并发, 代码任务每阶段单独提交, 非代码交付物等提交指令。

## 思考过程与决策

- 拆解为 4 阶段串行: ①调研(报告+3模板, 不提交) → ②拍板选型 → ③实施(按选型分波, 每波单独提交) → ④收尾(测试/issue关闭/回写)。
- 阶段1调研一次成功, 关键取证 (2026-10-03 @ develop 112baefc, 报告内含全行号): blur 病灶为三皮肤各一处 `.drawer-mask` 的 `backdrop-filter: blur(2px)` (atlas/console 的 css/dialogs.css L3-4/L6-7, prism 的 css/views.css L546-547), 是 PERF-01 后全站仅存 blur; 抽屉模板单点 `shared/tpl/drawer.html` 三皮肤共用; 快捷键注册表 `shortcuts.js` L266-279 (Alt+Digit1-4, scope drawer), 派发浮层分支 L433-438 是「列表侧 Alt+1~4 无效」的实现层原因; 既有列表光标模型 `_kbMove/_kbApplyCursor/_kbScrollRowIntoView` 可直接复用。
- 三方案: A 底部停靠面板 (qBt 式, 改造面 M-L) / B 主从分栏 (L, 宽表压缩+行窗口化几何回归面最大, 不推荐) / C 非模态浮层 (摘 blur+遮罩降档~0.15+高亮行跟随自动滚动, 改造面 S-M, 模板不动, 页签记忆/长文本截断/FX-22 全保留)。调研推荐: C 先行落地三个 issue, A 列为 issue 2119 的终态演进另立计划。
- **拍板 D1: 用户改判「只写报告」** —— 阶段②③④ (选型/实施/收尾实施) 全部取消; 报告与模板留在工作区不提交, 等用户提交指令; 实施波次仅在报告中备查, 需要时须用户再授权。

## 实现计划

方案A已单独立计划: **plans/26-10-03-0917-plan-webui-drawer-redesign.html**(五波 W1-W5 + 拍板点 D1-D4; **已实施完结, doc-status Done**, 波次权威在计划侧)。下方 C 路线波次仅存档备查:

1. 波1 (S): 抽屉内上下键切种子 —— shortcuts.js 注册 2 动作 + drawer.js `drawerNav(delta)` + 防抖 → 关 issue drawer-nav
2. 波2 (S): Alt+1~4 列表侧开抽屉定位页签 —— scope 调整/拆双条目 + 无选中兜底 → 关 issue drawer-open
3. 波3 (S-M): 去 blur + 遮罩降档 + kb-cursor 增强 + 抽屉收窄 (三皮肤各 1-2 行, 完成 PERF-01 全站归零) → issue drawer-redesign 轻量部分
4. 波4 (M, 可选): 常规页信息密度微调 → issue drawer-redesign
5. 波5 (L, 长期): 方案 A 底部停靠终态, 单独立计划

## 子任务状态表

| 子任务 | 状态 | 产出 |
|---|---|---|
| 阶段1 调研 (现状取证+成熟方案+报告+3模板) | Done | reports/26-10-03-0759-report-webui-drawer-redesign.html + reports/26-10-03-drawer-redesign-templates/ 三模板 |
| 阶段2 拍板选型 | Dropped | 用户改判「只写报告」, 不选型 |
| 阶段3 实施 (波1-3 按选型) | Dropped | 未排期, 待用户再授权 |
| 方案A 实施计划编制 (后续轮) | Done | plans/26-10-03-0917-plan-webui-drawer-redesign.html (五波 W1-W5 + 拍板点 D1-D4) |
| W1 停靠骨架 (浮层→底部面板, 摘遮罩与blur) | Done | 提交 `f994ce20` |
| W2 键盘跟随流 (scope存活 + Alt+1~4双态 + 详情跟随) | Done | 提交 `9c594e1e`; 核销 issue drawer-nav / drawer-open |
| W3 高度治理 (拖拽调高 + 收起钮 + 持久化) | Done | 提交 `b81a1ee4` |
| W4 回归验证 (窄屏降级 + 几何修复 + 基线切片) | Done | 提交 `a0b5d73f`; 基线 testing/baselines/26-10-03-1335-webui-drawer-redesign-w4-done.md |
| W5 收尾回写 (三issue置Done + 档案收口 + 计划→Done + 坑档) | Done | 本档案 + progress/implemented-webui.md + pitfalls/web-ui/ |

## 实施记录 (方案A四波, 2026-10-03)

- **提交链**: `f994ce20` (W1) → `9c594e1e` (W2) → `b81a1ee4` (W3) → `a0b5d73f` (W4), W5 纯文档回写随收尾提交入库。
- **关键取舍落地口径 (D1-D4 全按计划 §05 推荐项)**:
  - **D1 首屏默认收起**: `drawerOpen` 只写不回读, 首屏满高硬约束; 高度记忆 `autoqb.ui.drawerHeight` 仍生效。
  - **D2 Enter 已开仅跟随不关**: 关面板只走 Esc 与关闭钮。
  - **D3 ≤900px 转全屏覆盖**: 纯 CSS 媒体查询, 面板 body 零改动。
  - **D4 C 路线波次废弃**: C 波1 光标动作被 scope 存活语义取代, C 波3 遮罩降档被 W1 结构性取代 (blur 摘除顺带完成 PERF-01 全站归零)。
- **计划内修复两处** (W4 几何走查发现, 非计划外缺陷): ①停靠面板 sticky 吸底遮蔽以 `window.innerHeight` 为下界的滚动几何 → `shortcuts.js` `_kbViewBottom()` 单点下界, 面板开着时可见性下界让位面板顶缘; ②隐藏面板 5s 轮询收口 → 种子视图可见性守卫 (面板不在 DOM 即停轮询)。
- **kb-cursor 复检后未增强**: 三皮肤均可辨认, 增强与既有拍板 (shared 层单点配方) 打架, 维持现状。
- **tracker/peers 宽表**: 全宽利用 ~97%, 方案A全宽收益兑现。
- **测试**: test.quick 2326→2327→2328 (三波各 +1), test.full **2329 passed + 3 skipped / 99%**; 冒烟走查单 24 项 × 三皮肤 (atlas/prism/console) 全过; 基线切片 [testing/baselines/26-10-03-1335-webui-drawer-redesign-w4-done.md](../testing/baselines/26-10-03-1335-webui-drawer-redesign-w4-done.md)。
- **坑**: 模板里 `_` 前缀裸标识符 ReferenceError 为**已记坑复发** (pitfalls/web-ui/vue-reactivity.md「模板里不允许下划线前缀标识符」, 波及 shared/tpl/drawer.html 与 popovers.html 复制钮, drawer.js L667 注释钉原因) —— 未命中原因: 该条目判别只有模板插值 `{{ _x() }}` 形态, 实际踩的是事件绑定 `@click="_copyText(...)"` 同族形态, 路由到了但形态对不上没认出来。已把复发与本例形态回写进该条目。新增坑档: 停靠面板滚动几何下界、boot.js 嵌套 template 落点 (见 pitfalls/web-ui/)。

## 进度日志

- 2026-10-03 08:27 — 建档。开工 sync 成功 112baefc; 阶段1调研子智能体一次成功 (55 次工具调用, 零异常), 产出 4 个新文件 (报告 + 3 模板, 均过 HTML 标签配平与 node --check 静态校验; 子代理环境无浏览器, 可视化冒烟未做); 相邻 issue selection-follow-mouse (用户未点名) 只在报告 04 节提关联未纳入。拍板 D1 = 用户选「只写报告」→ 阶段2-4 实施面取消, 本档案转 Open 备查。零代码改动, 测试基线沿用 26-10-03-0542 (2309 passed + 3 skipped / 99%), 未跑新基线; 3 个 issue 保持 Open 未认领; 交付物 untracked 等提交指令。
- 2026-10-03 09:17 — 用户指派「按报告的方案A写一个分步实施计划」: 计划 26-10-03-0917 落盘 (方案A 底部停靠, 五波 W1 骨架/W2 键盘跟随/W3 高度治理/W4 回归/W5 收尾 + 拍板点 D1-D4, Open 待拍板; 报告 C 波1 废弃、C 波3 并入 W1 由 D4 拍板)。认领链回写: 3 个 issue doc-refs 与本档案 Refs 加计划双向声明。零代码改动, 交付物 untracked 等提交指令。
- 2026-10-03 13:4x — **W1-W5 全部完成, 本档案转 Done**。四波代码提交链 `f994ce20`→`9c594e1e`→`b81a1ee4`→`a0b5d73f` (明细见上方「实施记录」段), D1-D4 全按计划推荐项落地; W4 发现并修复两处计划内缺陷 (停靠几何 `_kbViewBottom` / 隐藏面板轮询收口); 下划线前缀坑复发 1 条已闭环 (复发 +1 + 未命中原因, 见实施记录末条)。W5 收尾回写: 三 issue (drawer-nav / drawer-open / drawer-redesign) 置 Done 并补修复回执; 计划 doc-status → Done; 已完成条目迁出 [progress/implemented-webui.md](../progress/implemented-webui.md); activeContext 切片收口。测试基线 26-10-03-1335 (test.full 2329 + 3 skipped / 99%)。
