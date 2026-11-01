# 4795 passed + 10 skipped(根) —— webui 单种子移动失败 toast 文案

> 摘要: webui 单种子移动失败 toast 文案
> 基线时间: 2026-11-02 00:43
**Refs:**

## 验收数字

`commands run test.full` (2026-11-02 00:43 实测, 本机 Windows):

- 汇总行: `4795 passed, 10 skipped in 190.77s (0:03:10)`
- TOTAL 表: `TOTAL 22482 182 7708 140 99%` (语句 / 未达 / 分支 / 部分分支 / 覆盖率)
- 逐条口径: 主仓一套账 (全量含覆盖率报表); 本轮未动 tools/, 无工具侧独立账面

## 本改动面

### 代码 (webui 前端静态件)

- `src/auto_qb/webui/static/shared/drawer.js:768`: 单种子移动 `_editPost` 的 okText
  「已移动」→「移动」—— 失败 toast 由 `${okText}失败` 派生, 随之从「已移动失败: <原因>」
  变「移动失败: <原因>」(用户口径); 成功 toast「已执行: 移动」与发送失败前缀同步变化。
  该 okText 全库唯一出现点, 无守阵钉字。

### 测试 / 知识库

- 无新增无改动: 纯前端静态文案一行, Python 侧零改动。
- 诊断结论(未改码): 单种子移动在 `relocate.enabled=true` 时走整组迁移闸门(计划 26-10-18-1604
  P5 三入口接线, 现行决策); `qb_temp` 闸门把内容根里**别的种子**的 `.!qB` 文件也计入拦截
  (`relocate_mod.py` 事实收集 + `relocate_units.py` GATE_QB_TEMP), 对 direct/file_links
  形态属误报 —— 待用户拍板是否收窄闸门, 未入池。
