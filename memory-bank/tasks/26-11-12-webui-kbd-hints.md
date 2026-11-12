# 26-11-12-webui-kbd-hints — WebUI 快捷键现场提示: 菜单键帽/页签徽标/入口指路

**Status:** Done
**Added:** 2026-11-12
**Updated:** 2026-11-13
**Summary:** WebUI 快捷键现场提示实施完成: 常驻键帽四落点(菜单 key 字段/页签 Alt+1..5 徽标/顶栏 N·K/状态栏 Shift+/ 入口)五笔提交 3df2c3b9..e544bfd2 落地, S1-S6 全 Done, 全量全绿(见 kb.baseline); 领域结论回写 architecture/webui.md「键位现场提示」节; 残余(子菜单溢出/UIS 枚举漂移)入池
**Topics:** webui-kbd-hints
**Refs:** memory-bank/plans/26-11-12-0344-plan-webui-kbd-hints.html, memory-bank/pitfalls/kb/subagent-survey-fact-verify.md, memory-bank/issues/26-11-12-0527-docs-webui-guard-ref-drift.html, memory-bank/issues/26-11-13-0443-bug-webui-ctx-sub-overflow.html, memory-bank/issues/26-11-13-0443-test-webui-uis-enum-drift.html, memory-bank/pitfalls/web-ui/ctx-sub-width-coupling.md, memory-bank/pitfalls/web-ui/css-file-line-cap.md, memory-bank/issues/26-11-12-0318-test-testing-parallel-flaky.html

## 本篇只回答

WebUI 快捷键现场提示专题**执行到哪、验证数字多少** —— 方案与取舍的权威在计划(26-11-12-0344, 只引用不复述); 领域结论(键帽取数链/例外裁定)实施完成后回写 architecture/webui.md 与 conventions/webui.md。

## 原始请求

1. 「WEBUI快捷键缺提示, 比如右键菜单/抽屉/其它等, 调研成熟的解决方案.」
2. 「初步想法是部分快捷键常驻+部分快捷键按某些键显示, 比如右键菜单中的快捷键适合常驻显示」
3. 「grilling然后出一个修改计划」

## 思考过程与决策

- 只读盘点两轮(Explore 子代理): 键面全景(注册表 58 条 = 54 绑键 + 4 空位) + 顶栏/状态栏按钮布局事实核查(34px 锁高/反斜杠三变体/键帽空间判定)。
- 外部调研: NN/g accelerator / golsteyn / saasui 三腿共识 —— 就地显示 + 作弊表浮层 + hold-reveal; 本轮取前两条(浮层已存在只补入口), 第三条与表格 Ctrl/Shift+click 多选冲突不做。
- grilling 两轮八问(Q1-Q8)拍板 **D1-D12**, 结论单点 = 计划 §06 拍板记录; 关键取舍: tooltip 通道整体否决(D10, I4 例外裁定) / 状态栏按钮键帽物理不可行(D7) / 设置 Ctrl+, 不做(D6) / 菜单 `key` 字段引用注册表 id 键位零二次维护(D11) / 四皮肤一步到位(D9)。
- 评审轮 1: 9 发现(blocker 1/major 1/minor 6/nit 1)引文全过检(检 9/9), blocker = §05 limits↔speed-down 误映射(全局限速浮层 vs per-hash 限速弹窗, 界面端点均不同), 全部当场修。

## 实现计划

计划 `memory-bank/plans/26-11-12-0344-plan-webui-kbd-hints.html` §03 波次表(W1 数据单点 → W2 菜单键帽 → W3 顶栏 → W4 页签徽标 → W5 状态栏入口 → W6 测试扩面)与 §04 步骤表(S1-S6, 每步带验收判据), §05 映射审计表 26 行(22 映射 + 4 不映射)为 S2 直抄源。本档案不复述。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| R0 | 调研 + grilling 拍板 + 计划入库 + 分批评审 | Done(2026-11-12) |
| S1 | 键帽取数单点 helper + 共享 CSS 键帽类 | Done(2026-11-12) |
| S2 | 菜单接线(key 字段 + ctxRenderItem + ctx-menus.html + 守阵) | Done(2026-11-12) |
| S3 | 顶栏接线(添加种子 N / 列 K) | Done(2026-11-13) |
| S4 | 抽屉页签 Alt+1..5 徽标(含合并态重排跟随) | Done(2026-11-13) |
| S5 | 状态栏 Shift+/ 入口(triggers 审计同步) | Done(2026-11-13) |
| S6 | 守阵/e2e 扩面 + 全量回归 + 四皮肤真机截图目检 | Done(2026-11-13) |
| W | 收尾回写(§09 三处 + 入池 2 + 坑档 2 + 计划收口 D13/R2) | Done(2026-11-13) |

<!-- 子任务行: 每步一行(步号/内容/状态 Done(日期) 或 Open) -->

## 进度日志

### R0 · 立档 (2026-11-12)

调研(盘点两轮 + 外部方案三腿)与 grilling 两轮八问(Q1-Q8)拍板 D1-D12; 计划 26-11-12-0344 入库(Open, S1-S6 等显式开工; R1 挂链本档案); 分批评审 3 轮: 轮 1 九发现(blocker 1/major 1/minor 6/nit 1)引文全过检全修, 轮 2 复评九条零回退 + 1 新 minor 已修, 轮 3 零新增 actionable 出口(累计检 10/10 · 修 10 · 入池 0); 伴随产出坑档 `pitfalls/kb/subagent-survey-fact-verify.md`(盘点二手事实抽验, 零发现通过); 测试面: 纯文档批零代码变更, test.full 不适用(kb.check 与 ship.gate 各轮全绿), 真机自检不适用(纯记录层制品)。

- 2026-11-12 04:31 快捷键现场提示计划入库: grilling 两轮拍板 D1-D12 + 计划 26-11-12-0344(Open) + 分批评审 3 轮 10 发现全修零 actionable + 坑档 subagent-survey-fact-verify 立档; S1-S6 等显式开工

- 2026-11-12 05:21 漂移直接修复(用户扩围): _scan_keys_serial_re 指称 3 处(shortcuts.js/keys.py/web_shortcuts_support.py 改指 webui_static_scan_js.py 定义点) + ctx_menu.js:93 次级计数 11->10 + 第四处同款 keys.py:32 对照面; 电池补桩 test_r4_move_dialog_partial_disclosure_bar(入库树既有红, e1fbd849 ensureWebFlags 接线 vs 沙箱缺桩); test.full 全绿(见 kb.baseline); 评审 5 轮轮 4/5 零 actionable; 随本专题入库

- 2026-11-12 05:28 漂移族入池 issue 26-11-12-0527-docs-webui-guard-ref-drift(15 处现存指称/11 文件, docs 便签, 不同符号面, 用户拍板入池): L1 三段齐(现象/位置锚点表/建议), 双向链挂任务档案; 随本专题入库

- 2026-11-12 06:31 S1 键帽取数单点(3df2c3b9 入库): shortcuts.js kbShortcutDisplay + 共享 .aq-kbd 键帽类(console_hub_panels.css 尾段, 令牌复用零新增); 评审 T1 分面 2 发检 1/1, 1 nit 顺延; 各批 Review trailer 在对应提交信息(git log --grep webui-kbd-hints 回查)

- 2026-11-12 08:49 S2 菜单键帽接线(8a4b255f 入库): 两条菜单注册表 key 字段(引用注册表 shortcut id, 自定义项无 key 留白) + ctxRenderItem 增产键帽 + ctx-menus.html 键帽列 + _menuFitRefit 二次收口; 评审 T2 派发 2 检 2/2, 2 nit 顺延; 增量拍板「dyn 置灰项键帽随行」

- 2026-11-13 01:21 S3+S4 顶栏页签键帽(cc342b57 入库): shortcuts.js kbKeycapById/kbKeycapOf 适配器 + state.js kbKeysRev 代次响应式; 顶栏 N/K 内联键帽 + 抽屉页签 Alt+1..5 徽标(kbDrawerTabKbd 与键盘 run 同一单点 KB_MERGE_TAB_REMAP, 合并态反查第 4/5 档不显示); 评审 T3 派发 2 轮 2 检 1/1 修 1(flags 桩纪律)

- 2026-11-13 02:38 S5 状态栏「键位」入口(b661be35 入库): 入口钮 + Shift+/ 键帽 + kbToggleHelp 别名中转 _kbToggleKbHelp(与 Shift+/ 同链) + triggers.js 触发点 statusbar.kbd-help; 评审 T4 全能检 1/1, 1 nit 顺延

- 2026-11-13 04:10 S6 外观拍板(e544bfd2 入库): 真机截图目检发现键帽致 .ctx-sub label 折三行(四皮肤一致), 拍板加宽 190→260(四皮肤 min-width + menu.js 估宽 272 五处同步 + scan_css _scan_ctx_sub_width 守阵双向变异自证); 首行右键子菜单底部探出视口的残余拍板入池不入本批; 评审 T5 轮 2 检 1/1 修 1(宽度耦合守阵); 基线切片 26-11-13-0249 全量全绿(见 kb.baseline) + e2e fast 全绿 + 真机四皮肤截图目检过(real-machine.md §06, 测试实例 56589)

- 2026-11-13 04:47 收尾回写完成(§09, 本会话): 顺延三条 nit 勘正(ctx_menu.js:289 括注 / console_hub_panels.css:574 特异性计数 / 文案锚收紧), 随本专题入库; 回写三处 —— architecture/webui.md 新增「键位现场提示」节(key 字段口径/kbShortcutDisplay→kbKeycapById→kbKeycapOf 取数链单点/I4 例外) + conventions/webui.md 悬浮提示例外注记 + 根 README 核对零漂移不动; 入池 2(26-11-13-0443-bug 子菜单溢出残余 / 26-11-13-0443-test UIS 旧枚举漂移, 均挂本档案双向链); 坑档 2(ctx-sub-width-coupling 新立 / css-file-line-cap 复发+1 扩 flux); issue 26-11-12-0318 复发+1(T5 真机截图阶段假红一次, 复跑两轮全绿); 计划收口(doc-status Done + D13 增量拍板行 + R2 变更记录); 状态表 S1-S6 全 Done, 档案结档
