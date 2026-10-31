# 3211 —— webui 局部发布合并骨架抽单点(issue 26-10-11-0309 认领修)执行基线

> 摘要: 用户「认领并修复 memory-bank/issues/26-10-11-0309-refactor-webui-partial-publish-merge-dup.html」→ webui 重复代码修复轮(26-10-11-1610)按拍板留 Open 的热路径项, 本轮认领修完: `runtime._publish_partial_locked` 四段(groups/singles/flat/shows)「重建脏行/保留未脏/追加」合并骨架抽 `_merge_rows` 静态单点(键名传字符串而非 key_of 可调用 —— 核心热路径, 逐行不多付一次函数调用), 行为逐字不变(引用稳定契约不动, 前端 S7 WeakMap 记忆化不受影响); 双保险守阵: S5 镜子 + S6「局部重算 == 全量重跑」单测(既有)全绿, 另新增 2 条(_merge_rows 合并契约直测 + 静态零重复骨架, 均过红验)。数字相对上基线无回归信号(差值现列 `commands run kb.baseline -n 2`)。
> 基线时间: 2026-10-15 04:54

**Refs:** memory-bank/tasks/26-10-11-webui-dup-code-fixes.md

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` -> 已同步 a369c99a; 工作树含本轮改动时实测)
- 命令: `commands run test.full`(Windows)
- **实测 (Windows)**: **3211 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**

| 面 | 语句 | 未覆盖 | 分支 | partial | 覆盖率 |
|---|---|---|---|---|---|
| TOTAL | 16825 | 159 | 5712 | 142 | 99% |

- 耗时: 158.29s(单次采样, 区间口径见 `testing/baseline.md`)
- 新增守阵 2 个测试函数(红验通过): `test_merge_rows_single_point_semantics`(合并契约直测: removed 剔除/脏行换新对象/未脏行同一 dict 原样复用/新增行追加尾部/key_field 参数化)/ `test_publish_partial_merge_skeleton_single_point`(静态: 调用方 4 个 `_merge_rows` 调用点 + 内联骨架 `.pop(k) if k in` 零残留, 单点内恰一份; 红验 = 临时抄回一份内联骨架即判红)
- Linux (WSL 沙箱) 本轮未重测 —— 改动全在 Windows/Linux 同构路径(纯 Python 重构 + 静态守阵), 无平台分支。

## 包内脚本测试

- 本轮未触碰 `.commands/` 与 `.agents/skills/commands/`, 未跑 `test.pkg`; 提交闸门按 match 规则自判。
