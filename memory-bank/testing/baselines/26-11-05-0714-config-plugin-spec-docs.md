# 5341 passed + 10 skipped —— issue 26-09-28-1946 清偿(插件 spec 键面豁免删除)后全量基线

> 摘要: 5341 passed + 10 skipped —— issue 26-09-28-1946 清偿(插件 spec 键面豁免删除)后全量基线
> 基线时间: 2026-11-05 07:14
**Refs:** memory-bank/issues/26-09-28-1946-docs-config-plugin-spec-docs.html

## 验收数字

`commands run test.full` 实测(2026-11-05 07:14, Windows, 本机):

- 汇总行: `5341 passed, 10 skipped, 1 warning in 161.69s (0:02:41)` —— 0 failed
- 覆盖率 TOTAL 表末行: `TOTAL 24464 69 8390 38 99%`(语句 24464 / 缺 69 / 分支 8390 / 部分覆盖 38); 闸门判定通过(退出码 0)
- 口径注记: 副作用台账越界 0。相对上基线 26-11-05-0620: 测试数/语句/缺口净额逐位一致(本轮只改文档与测试守卫的豁免段, 不新增用例不动产品码)。

## 本改动面

- `memory-bank/rule-system/conditions-and-actions.md`: 新增独立 `##` 节「`checking` 动作详解」——顶层 4 键(`basic_check`/`custom_basic_check_program_path`/`with_reference`/`without_reference`)+ 分支段 3 键(`enabled`/`mode`/`auto_start`)逐键表, 口径对齐 schema 插件表(`CHECKING_SECTION_FIELDS`)与 `_validate_checking_action_spec`; 修动作表 checking 行悬空「见下节」引用; 摘要/触发词同步。
- `tests/test_config_key_surface.py`: 删除 `_DOC_EXEMPT`(定义+使用), 键面出处检查对插件 spec 内部键全面生效(模拟删豁免实测真缺口 = checking 6 叶键); 头部 docstring「键面口径」段同步改写。
- `memory-bank/issues/26-09-28-1946-docs-config-plugin-spec-docs.html`: 认领清偿, 状态翻 Done(复验/修法/验证进状态日志), 索引重建。
