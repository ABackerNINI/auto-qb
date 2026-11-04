# TOTAL 24427 / 227 miss / 99%; 5198 passed, 10 skipped in 136.05s (test.full) —— 收口评审修复轮全量基线: 计划 26-11-03-0456 六项修复

> 摘要: 收口评审修复轮全量基线: 计划 26-11-03-0456 六项修复
> 基线时间: 2026-11-05 00:24
**Refs:**

## 验收数字

- `commands run test.full` 实测(2026-11-05 00:24, Windows 本机):
  - 覆盖率 TOTAL 表: **TOTAL 24427 / 227 miss / 99%**(statements 24427, missed 227, branch 8370, brMiss 167)
  - 汇总行: **5198 passed, 10 skipped in 136.05s (0:02:16)**
  - 口径: 全量 pytest 含覆盖率报表; 10 skipped 为平台条件跳过; 数字为该次运行实测, 非均化

## 本改动面

计划 26-11-03-0456(已完成种子下载保险丝)收口评审(分面 3 代理)6 条发现的修复轮:

- `src/auto_qb/core/modules/fuse_mod.py`: armed 条目 dl_limit==0 补齐加连续计数(`_REARM_YIELD=3`), 超限让位转 released 不再与外部清零互写; `_new_entry` 增 `rearm` 字段
- `src/auto_qb/config/validation/sections.py`: `fuse_tag` 校验加严 —— 拒含逗号(qB 标签分隔符)与首尾空白(qB 会裁剪)
- `src/auto_qb/cli.py`: `--fuse-release` 入参加 40 位十六进制校验(parser.error); `fuse_release` 显式列表 0 命中打 WARNING 并返回 False(退出码 1)
- `tests/test_fuse_mod.py`: 新增 armed 补齐让位/瞬时失败回流 2 用例 + release dry-run 零写用例; 批量触发用例补汇总 WARNING 恰一条断言; CLI 用例补落盘/dry-run 不落盘/0 命中 False 断言; 头部测试计划同步
- `tests/test_config_schema.py`: fuse_tag 逗号/首尾空白负例并入聚合报错用例
- `memory-bank/config-reference/keys.md`: fuse_tag 约束与行为段回写
