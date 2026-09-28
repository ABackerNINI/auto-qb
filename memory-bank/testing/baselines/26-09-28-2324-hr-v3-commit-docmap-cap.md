# 1830 passed / 4 skipped —— HR v3 计划文档轮提交: 合流 Gitee 主线 + doc-map 撞 cap 收口

> 摘要: 提交 HR 在线核实 v3 重建计划的文档轮改动。开工 `my-commit-flow.sync` 快进到 d79fb1be
> (合入远端 3 个提交: WEBUI 设置二级页返回优化 / 配置版本升级守卫 / throttle 守阵计时留余量,
> 用例数随之 1828→1830), 随后 `test.full` 报 `_doc-map.md` 12,203 > 12,200 —— 新计划入册撑破
> `index-auto` cap。按 [pitfalls/kb/cap-counting.md](../../pitfalls/kb/cap-counting.md)「两个出口」
> 处置① 收口生成器固定文案: `gen_doc_map` 头部两行并一行(去掉 meta 字段名枚举, 协议仍在
> doc-forms.md) + 单件专题折行 150→400(只影响换行) ⇒ 12,203 → 12,185(余 15)。**未动 cap、
> 未改内容渲染口径** —— 头部固定文案已近榨干, 下轮宜改内容渲染口径或上调 cap。
> 基线时间: 2026-09-28 23:24 (develop @ d79fb1be, 已与 Gitee 主线齐平)
> 档案: plans/26-09-28-1932-plan-hr-verify-rebuild.html (doc-status Open)

- test.full: **1830 passed / 4 skipped**, TOTAL **91%**(12576 语句 / 917 未覆盖 / 4246 分支 / 390 partial),
  耗时 21.61s。较上一基线(26-09-28-1954, 1828/3)**+2 passed / +1 skipped** —— 差异全部来自合入的
  远端提交, 覆盖率 TOTAL 与语句/分支/partial 计数逐位一致。
- 本轮改动: 纯文档 + KB 生成器收口(无业务代码改动) —— 新计划 HTML 入册、activeContext 切片、
  任务档案滚动区与 Refs、docs/hr-online-verify-docs.md 清单、两份审计报告与 1815 计划 doc-refs
  双向认领链补声明、doc-map 生成器收口。
- 中途: 新计划首跑红 1 条(`test_docs_forms::test_doc_map_is_regenerated_and_capped`, 12,203 > 12,200),
  收口后全绿; `kb.check` 全程绿。
- 覆盖率口径见 [baseline.md](../../testing/baseline.md)。
