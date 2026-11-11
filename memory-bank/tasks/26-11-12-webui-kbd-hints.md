# 26-11-12-webui-kbd-hints — WebUI 快捷键现场提示: 菜单键帽/页签徽标/入口指路

**Status:** Open
**Added:** 2026-11-12
**Updated:** 2026-11-12
**Summary:** WebUI 快捷键现场提示(常驻: 菜单键帽/页签徽标/顶栏 N·K/状态栏 Shift+/ 入口; 按需: 既有 Shift+/ 浮层只补入口) —— 方案权威在计划 26-11-12-0344, 本档案管执行与验证
**Topics:** webui-kbd-hints
**Refs:** memory-bank/plans/26-11-12-0344-plan-webui-kbd-hints.html, memory-bank/pitfalls/kb/subagent-survey-fact-verify.md, memory-bank/issues/26-11-12-0527-docs-webui-guard-ref-drift.html

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
| S1 | 键帽取数单点 helper + 共享 CSS 键帽类 | Open |
| S2 | 菜单接线(key 字段 + ctxRenderItem + ctx-menus.html + 守阵) | Open |
| S3 | 顶栏接线(添加种子 N / 列 K) | Open |
| S4 | 抽屉页签 Alt+1..5 徽标(含合并态重排跟随) | Open |
| S5 | 状态栏 Shift+/ 入口(triggers 审计同步) | Open |
| S6 | 守阵/e2e 扩面 + 全量回归 + 四皮肤真机截图目检 | Open |

<!-- 子任务行: 每步一行(步号/内容/状态 Done(日期) 或 Open) -->

## 进度日志

### R0 · 立档 (2026-11-12)

调研(盘点两轮 + 外部方案三腿)与 grilling 两轮八问(Q1-Q8)拍板 D1-D12; 计划 26-11-12-0344 入库(Open, S1-S6 等显式开工; R1 挂链本档案); 分批评审 3 轮: 轮 1 九发现(blocker 1/major 1/minor 6/nit 1)引文全过检全修, 轮 2 复评九条零回退 + 1 新 minor 已修, 轮 3 零新增 actionable 出口(累计检 10/10 · 修 10 · 入池 0); 伴随产出坑档 `pitfalls/kb/subagent-survey-fact-verify.md`(盘点二手事实抽验, 零发现通过); 测试面: 纯文档批零代码变更, test.full 不适用(kb.check 与 ship.gate 各轮全绿), 真机自检不适用(纯记录层制品)。

- 2026-11-12 04:31 快捷键现场提示计划入库: grilling 两轮拍板 D1-D12 + 计划 26-11-12-0344(Open) + 分批评审 3 轮 10 发现全修零 actionable + 坑档 subagent-survey-fact-verify 立档; S1-S6 等显式开工

- 2026-11-12 05:21 漂移直接修复(用户扩围): _scan_keys_serial_re 指称 3 处(shortcuts.js/keys.py/web_shortcuts_support.py 改指 webui_static_scan_js.py 定义点) + ctx_menu.js:93 次级计数 11->10 + 第四处同款 keys.py:32 对照面; 电池补桩 test_r4_move_dialog_partial_disclosure_bar(入库树既有红, e1fbd849 ensureWebFlags 接线 vs 沙箱缺桩); test.full 全绿(见 kb.baseline); 评审 5 轮轮 4/5 零 actionable; 随本专题入库

- 2026-11-12 05:28 漂移族入池 issue 26-11-12-0527-docs-webui-guard-ref-drift(15 处现存指称/11 文件, docs 便签, 不同符号面, 用户拍板入池): L1 三段齐(现象/位置锚点表/建议), 双向链挂任务档案; 随本专题入库
