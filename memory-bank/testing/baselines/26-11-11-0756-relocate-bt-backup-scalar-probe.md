# 6000 passed, 2 skipped (coverage 99%) —— 全量基线: relocate.bt_backup 标量化+探测后端+端点+编辑器 (计划 26-11-11-0259 S6a)

> 摘要: 全量基线: relocate.bt_backup 标量化+探测后端+端点+编辑器 (计划 26-11-11-0259 S6a)
> 基线时间: 2026-11-11 07:56

## 验收数字

`commands run test.full`(2026-11-11 07:56 实测, HEAD 130ec909):

```text
TOTAL                                                26633     60   9274     64    99%
6000 passed, 2 skipped in 176.58s (0:02:56)
```

## 本改动面

计划 26-11-11-0259 S1-S5 五批(本地分支 relocate-bt-backup-scalar-probe, 批1-批5):

- 批1 c4ee6149: 顶层 bt_backup 表退役 → relocate.bt_backup 标量(models/loaders/validation/schema/groups); v7→v8 迁移链(_migrate_config_7_8 四形态+反证); tests-real 14 文件版本字面量; 键面基线 fixture 重生成; relocate_mod sections() 收单。
- 批2 08b34b54: 新 infra/bt_backup_probe.py(587 行, candidates/qualify/verify/verdict 五态纯函数)+ tests/test_bt_backup_probe.py(653 行 37 用例, tmpdir 合成矩阵)。
- 批3 61363210: POST /api/relocate/bt_backup_probe 端点(断连降级不 503, qB 事实原语化)+ 金清单 91→92 + 7 端点用例。
- 批4 2e6487e1: bt_backup_editor.js/tpl 重写(单路径输入+探测按钮+五态证据区, hash 命中候选优先回填)+ groups.py hidden 接管 + e2e settings-bt-backup 重写(8 用例)。
- 批5 130ec909: 运行面口径收尾(lifecycle 死分支退役 + 注释/文案改标量口径, 零逻辑变化)。

差值参照上一基线切片(memory-bank/testing/baselines/ 目录 kb.baseline 可列)。
