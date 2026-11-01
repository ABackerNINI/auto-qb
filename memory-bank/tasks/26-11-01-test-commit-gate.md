# 26-11-01-test-commit-gate — 提交闸门无自测包豁免修复: dev/doc/env/kb 补最小自测

**Status:** Done
**Added:** 2026-11-01
**Updated:** 2026-11-01
**Summary:** issue 26-11-01-0921 按方案①修复: dev/doc/env/kb 各落最小自测, dev.port-kill 补 timeout; scoped 四包 / 整跑 test.pkg / test.full 全绿
**Topics:** test-commit-gate
**Refs:** memory-bank/issues/26-11-01-0921-test-commit-gate-no-test-pkg.html, memory-bank/testing/baselines/26-11-01-1926-test-commit-gate.md, memory-bank/pitfalls/testing/importlib-sys-modules-dataclass.md

## 原始请求

1. 「认领并修复 memory-bank/issues/26-11-01-0921-test-commit-gate-no-test-pkg.html」—— 用户显式指派认领(create-issue 认领合规口径)。
2. 「按方案1补最小自测」—— 即 issue 建议①: 按 real 包先例给 dev/doc/env/kb 各补最小自测(config.toml 可解析 + 任务必备键 + 引用脚本存在)。

## 思考过程与决策

- 复验先行(create-issue 防过期原则): 四包清单仍成立(各仅 config.toml、零 test_*.py), 02 节「有自测包」清单一致; pkg_scoped 机制与 real 先例和 issue 记载一致。
- 测试落位与形态沿用 real 先例: `.commands/<包>/scripts/test_<包>_pkg.py`, 自包含 unittest, 不跨包 import —— scoped 闸门按包收窄, 守阵随包走。
- `<skill-dir:NAME>` 展开不抄候选表: doc/kb 守阵就地加载引擎 `_config.find_skill_dir`(单点复用); 加载须先注册 `sys.modules` 再 exec(3.13 + future-annotations + dataclass 会炸 NoneType, 坑档 pitfalls/testing/importlib-sys-modules-dataclass.md)。
- 防空转/防死分支(testing 坑档 guard-dead-branch 教训): .py 引用抽取总数 >0 写进断言; 另做合成坏引用红验, doc/kb/dev 全部抓到才算数。
- env 无 .py 引用, 不设空转 ScriptRef, 改守 env.version 的版本单源声明。
- 守阵首跑即逮到 dev.port-kill 缺 timeout —— 判定为方案①必备键检查的真缺口, 顺带补 `timeout = 60`, 不放宽守阵口径。

## 实现计划

1. 复验 issue 清单与 real 先例(pkg_scoped.py / test_real_pkg.py / 四包 config.toml)。
2. 四包落最小自测(必备键 / .py 引用存在 / 抽取非空; doc·kb 经引擎单点展开 skill-dir; env 守版本单源)。
3. 合成红验 + 逐包 `test.pkg.scoped` + 整跑 `test.pkg` 全绿。
4. issue 状态流转(复验行 / Done / 验证数字) + 收尾回写(基线切片 / 坑档 / 本档案 / 切片)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|

| 1 | 复验四包清单与 real 先例 | Done(2026-11-01) |
| 2 | 四包最小自测落盘 + dev.port-kill 补 timeout | Done(2026-11-01) |
| 3 | 合成红验 + scoped 四包 + 整跑 test.pkg 全绿 | Done(2026-11-01) |
| 4 | issue 置 Done + 收尾回写(基线 / 坑档 / 切片) | Done(2026-11-01) |

## 进度日志

### R0 · 立档 (2026-11-01)

四包 scoped 闸门全绿(rc=0); 整跑 test.pkg 全绿; test.full 全绿(数字见基线切片 testing/baselines/26-11-01-1926-test-commit-gate.md, 或 commands run kb.baseline); issue 26-11-01-0921 已置 Done。改动随本专题入库。

- 2026-11-01 19:29 认领 issue 26-11-01-0921 修复: 四包补最小自测 + dev.port-kill 补 timeout; scoped/test.pkg/test.full 全绿, issue 置 Done
