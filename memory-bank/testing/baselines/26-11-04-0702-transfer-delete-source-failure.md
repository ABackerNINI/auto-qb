# 5146 —— transfer 删源失败不翻盘修复全量基线

> 摘要: transfer 删源失败不翻盘修复全量基线
> 基线时间: 2026-11-04 07:02
**Refs:**

## 验收数字

- 汇总行: `5146 passed, 2 skipped in 197.01s (0:03:17)`(2026-11-04 本机 Windows 实测, `commands run test.full` 一次性绿)
- 覆盖率 TOTAL: `23943 stmts / 210 miss / 8186 branch / 164 partial / 99%`(终端默认整数精度)
- 口径注记: 等价 test.full 展开(`-n 8 --cov=src --cov-report=term-missing --cov-branch`); 相对上基线逐位对比看 `commands run kb.baseline -n 2`

## 本改动面

- `src/auto_qb/transfer/orchestrator.py`: `_delete_source` 改签名 `-> bool`, 内部捕获删源异常(WARNING 日志)不外抛; `_transfer_one` 删源失败时往 note 追加「源删除失败, 源已保留」, 结果恒 SUCCESS(issue 26-11-03-0824)
- `tests/test_transfer_orchestrator.py`: `_FakeQbApi` 加 `delete_error` 注入位; 新增 `test_delete_source_failure_keeps_success`(删源抛 RuntimeError -> 仍 SUCCESS/code=None/reason 注记/调用确已发起); 头部测试计划清单同步
- `memory-bank/issues/26-11-03-0824-bug-transfer-source-delete-misreport.html`: 状态 Open→Done, 复验行/修复后补充/状态变更日志回写; `memory-bank/issues/_index.md` kb.index 重建
