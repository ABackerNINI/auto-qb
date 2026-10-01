# 基线 · 1929 passed + 3 skipped / 91% —— 兼容 Transmission 可行性分析(纯知识库轮)

> 摘要: issue 26-10-01-2212 认领轮的可行性报告收官基线。**零代码变更** —— 本轮只产出
> reports/26-10-01-2347 与立档, 故测试计数与上一基线完全相同(这是事实, 不是漏测)。
> 档案: [tasks/26-10-01-backend-transmission-compat.md](../../tasks/26-10-01-backend-transmission-compat.md)。
> 基线时间: 2026-10-01 23:55 起测, 2026-10-02 00:05 **在与远端合流后的新基线 16eb223b 上复测**(远端
> 并入 16eb223b/964a55ba/f5ce07bd 三笔, 含 HR 明细导出 API 与新增测试, 故计数高于首测)。

TOTAL **1940 passed + 3 skipped / 91%**(13377 语句 / 1033 未覆盖 / 4444 分支 / 436 partial,
test.full 33.5s @ 16eb223b, rc=0)。首测(826f25e6, 合流前)为 **1929+3 / 91%**(13326 / 1033 / 4432 / 436,
32.0s) —— **+11 全部来自远端合流的三笔提交**, 本轮**零代码变更、不贡献计数增量**; 记这一条只为留存
「纯知识库轮闸门同样要过」的口径, 以及合流后必须在新基线上复测(计数会变)这一事实。

## 本轮验证面

- `tests/test_docs_forms.py` 全绿: 新报告 doc-* meta 齐 / 状态词 Done 在 5 词表 / 命名带 type token /
  `color-scheme: dark` / `reports/_index.md` == 生成结果 / 认领链双向(issue ↔ 报告 ↔ 档案三方互链)。
- 索引重建: `gen_issues_index.py`(issue 移入 In Progress 区) + `commands run kb.index`(16 个索引,
  含 reports/_index.md 新登记与 tasks/_index.md 新档案)。

## 无改动声明

本轮严守范围守恒: **未改任何 src/ 代码、未入池新 issue、未改 TODO.md**。报告结论「暂不做」待用户拍板,
拍「做」才转计划文档。

## 合流备注(生成物索引冲突的正解是重跑, 不是手工合并)

远端 16eb223b 与本地同改 `issues/_index.md` / `tasks/_index.md`(全体 clone 最热写点), `my-commit-flow.sync`
判定「本地改动与远端新提交重叠」而拒绝合流。处置: `git checkout --` 回退**这三份生成物索引**(可再生的,
丢了不损失) → 重跑 sync 快进到 16eb223b → 在新基线上重跑 `gen_issues_index.py` 与 `kb.index` 重新生成。
新文件(报告/档案/切片)与 issue HTML 未被远端触碰, 不受影响。
