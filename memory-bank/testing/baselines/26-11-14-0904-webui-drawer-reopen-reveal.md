# 6077 passed + 2 skipped, TOTAL 27110/65/9478/68 —— 抽屉让位误补偿与下降抖动修复专题(S6 收尾)全绿基线

> 摘要: 抽屉让位误补偿与下降抖动修复专题(S6 收尾)全绿基线
> 基线时间: 2026-11-14 09:04

## 验收数字

- `commands run test.full`: **6077 passed, 2 skipped** (185.98s), 覆盖率 TOTAL **27110 语句 / 65 miss / 9478 分支 / 68 br-partial (99%)**, Required 99.5% 达标(99.63%)。
- 当轮共跑三笔 `test.full`: 第 1 笔 1 failed(`test_docs_forms.py::test_claim_chain_is_bidirectional`) —— 档案 `**Refs:**` 新增 issue 后 issue 未反向声明本档案, 属回写操作自身引入的单向链, 补 issue `doc-refs` 后修复(非代码缺陷); 第 2 笔 1 failed(`test_trigger_events.py::test_event_checking_resume_fail`) —— 8 worker 并行下的挂钟冷却窗口偶红, 隔离单跑通过, 与本分支零关涉(本分支零后端改动); 第 3 笔(本切片)全绿。

## 本改动面

- 分支 `feat/webui-drawer-reopen-reveal` 7 笔提交(`ffcf0346`..`5c04d0e7`), 全部 webui 静态面: ①S0 红验基线 e2e(`ffcf0346`); ②W2 收场抖动修复 leave 期槽位冻结+末帧一次收拢(`0aeba884`); ③S-C 让位判据越过带收紧+补差单点 `_kbViewBottomPad()`(`03bc1a72`); ④S-A flux 首开竞速修复(`37957914`); ⑤T6 边距生命周期重构+让位截断续缴 `_kbRevealCompleteStart`(`fbf5dc26`); ⑥T7 顶界触发带收紧 `_kbViewTopPad()`(`93a378f7`); ⑦T8 四皮肤根滚动器禁 CSS scroll anchoring(`5c04d0e7`)
- 本轮(S6 收尾)仅 memory-bank 文档回写(档案续作/计划翻 Done/坑档/本切片), 零代码改动
- 树态: 本片测在含本轮未提交 S6 文档回写改动的工作树上
