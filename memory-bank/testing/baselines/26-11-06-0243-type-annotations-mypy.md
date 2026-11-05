# 5348 passed, 10 skipped, 1 warning in 154.67s —— 类型注解清偿与 mypy 渐进接入 S5 收尾: test.full 全量绿 + mypy 面数字

> 摘要: 类型注解清偿与 mypy 渐进接入 S5 收尾: test.full 全量绿 + mypy 面数字
> 基线时间: 2026-11-06 02:43
**Refs:** memory-bank/plans/26-11-05-0635-plan-type-annotations-mypy.html, memory-bank/issues/26-09-21-1408-refactor-type-annotations-mypy.html

## 验收数字

`commands run test.full` 汇总行(测于本轮工作树, 分支 feature/type-annotations-mypy, 基线 4c4102f8):

- 5348 passed, 10 skipped, 1 warning in 154.67s
- coverage: 99%(TOTAL 24498 stmts / 74 miss / 8396 branch / 40 partial; 覆盖率闸 99.0 未动)

**mypy 面**(`commands run dev.typecheck`, 计划 26-11-05-0635 S1-S4 落地后的终态):

- dev.typecheck 退出码 0: `Success: no issues found in 194 source files`(豁免面外全绿)
- 豁免面(ignore_errors): 2 模式 —— `auto_qb.tray.*`(GUI 三方回调)、`auto_qb.rules.expr.env`(闭包工厂)
- 豁免面(disable_error_code): 16 个 override 块共 55 个错误码条目, 按模块×错误码展开 157 对
- 收紧面(disallow_untyped_defs): 8 模式 —— `config.*`/`torrents.*`/`core.*` + rules 5 模式(base/conditions/registry/checking_meta/actions.*)
- 守阵: `tests/test_mypy_allowlist_guard.py` 冻结豁免清单(只减不增)

**AST 注解 full 率复测**(脚本 annotation_stats.py, 口径同计划 §02: 实参注解+返回值齐全 = full; 括号内为 §02 改前数字):

- config 160/160 = 100%(改前 84/160)
- core 751/751 = 100%(改前 503/751)
- torrents 65/65 = 100%(§03 记 94%, 查漏后归零)
- rules 非 expr 面 114/114 = 100%(改前 49/186); rules 全包 126/186 = 67.7% —— expr/ 闭包工厂 72 个 def 留 allowlist, 是递减面
- 未在 S3 范围的面(webui 47.7% / hr 88.4% / tray 26.7%)维持递减目标, 见 issue 26-09-21-1408 Done 备注

## 本改动面

- S1-S4 代码落地(分支 feature/type-annotations-mypy, 基线 4c4102f8): 2b6e9d6c mypy 接入(mypy==2.4.1 + [tool.mypy] + dev.typecheck task)→ 5bf0e93b/16d002df RUF013 隐式 Optional 全库归零 → 13ba10c2/9c4dc138/27d3b24e S3 三批注解补全(config/torrents/core/rules 非 expr)→ 4c4102f8 allowlist 分级 + 守阵。
- S5 收尾: 零代码改动 —— 本基线切片 + issue 26-09-21-1408 置 Done + 坑档沉淀(annotations-lazy-eval 新形态 / sandbox-tool-cache mypy 缓存实测 / 新档 mypy-config-cwd、uv-trampoline) + 计划外缺陷入池 + 计划档案 R1 回写。
