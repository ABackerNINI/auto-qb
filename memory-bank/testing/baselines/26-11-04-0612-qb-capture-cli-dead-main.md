# 5123 passed, 10 skipped in 267.10s (0:04:27); TOTAL 23933 stmts / 229 miss / 8184 branch / 171 partial / 99% —— qb_capture_cli 死 main 清理全量基线

> 摘要: qb_capture_cli 死 main 清理全量基线
> 基线时间: 2026-11-04 06:12
**Refs:** memory-bank/issues/26-11-03-1145-refactor-qb-capture-cli-dead-main.html

## 验收数字

- 汇总行: `5123 passed, 10 skipped in 267.10s (0:04:27)`(2026-11-04 本机 Windows 实测, `commands run test.full`)
- 覆盖率 TOTAL: `23933 stmts / 229 miss / 8184 branch / 171 partial / 99%`, 闸门绿
- 口径注记: 首轮全量 1 failed(test_gen_all_check_is_green, issue 置 In Progress 后未先重建索引所致的生成物漂移, `kb.index` 重建后重跑一次性绿) —— 不是代码问题
- 对照上一基线 26-11-04-0531: stmts 23896→23933(+37, 同机证明代码轨), 用例 5121→5123, 覆盖率 98.69%(无真机 skip 口径)→99% 闸门绿; 本改动面(scripts/)不在 `--cov=src` 测量面内

## 本改动面

- `scripts/qb_capture_cli.py`: 删除拆分残留的死 `main()`(-22 行, 内含引用未定义 `Capture` 的 :78)与同文件既有未用 `import sys`; docstring 改写为 helper 模块定位并标注「CLI 入口只在 qb_capture.py」防再犯; `build_parser`/`load_from_config`/`_self_test_only` 三 helper 原样保留(qb_capture.py:65 导入面不变)
- `memory-bank/issues/26-11-03-1145-refactor-qb-capture-cli-dead-main.html`: 状态 Open→In Progress→Done, 复验行+修复验证行回写; `issues/_index.md` 与 `attachments/_archive.md` kb.index 重建
