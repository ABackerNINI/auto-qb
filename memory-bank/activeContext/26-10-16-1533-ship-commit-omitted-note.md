# 26-10-16-1533-ship-commit-omitted-note — ship.commit 子集提示与实际提交面对齐(issue 26-10-16-1523 认领与修复)

> 摘要: 用户「认领并修复 memory-bank/issues/26-10-16-1523-bug-ship-commit-omitted-note.html」。问题: 子集模式只限制 `git add` 清单, 而 `git commit` 提交的是**整个索引** —— 旧提示「未纳入」把已暂存的未传改动也读成"没进本笔", 与实际相反(入池实测: 10 个 `D ` 撤跟踪项被列成「未纳入」却全在同一笔里)。落盘(issue §06 方向 A; B「真正路径限定提交」不做 —— 会推翻坑档 `git/ship-commit-staged-delete.md` 已依赖的「已暂存删除项随整索引落笔」便利): `commit.py` 新增 `omitted_note()` 按索引状态分组(已暂存/未暂存各给计数与示例, 空组不列)、`omitted` 去重(MM 文件不再翻倍); 打印点改调它。守阵 4 条 + 红绿双验 3 类突变逐类判红(还原 SHA256 一致); 复验先于改动(探针临时仓库重放: 修复前仍复现 → 修复后与提交面逐条一致)。数字见基线切片与档案。另: 提交阶段被快照守阵两条既有红挡下(与本次改动无关), 已处置 —— ① 家目录空 `.git` 由机主移除; ② `-n 8` 并行竞态经用户授权按「用例私有临时根」修复(红绿双验 2 类; 见落点)。新坑已记 `pitfalls/testing/tmpdir.md`; 基线切片「包内脚本测试」节留有当时的失败记录。
> 最后活动: 2026-10-16 17:04
> 状态: Done

**Refs:** memory-bank/issues/26-10-16-1523-bug-ship-commit-omitted-note.html,memory-bank/tasks/26-10-16-ship-commit-omitted-note.md,memory-bank/testing/baselines/26-10-16-1551-ship-commit-omitted-note.md

## 本轮落点(代码事实)

- `.commands/my-commit-flow/scripts/commit.py`: 新增 `_sample(files, limit=3)` 与 `omitted_note(omitted, staged)` —— 打印前按索引状态把「未参与 add」的改动分两组: `已暂存 N 个(仍会随整索引进本笔: …)`(在 staged 清单里, 照样随整索引进本笔)与 `未暂存 N 个(不会进本笔: …)`(只在 unstaged 清单里), 空组不列; 打印点由平铺旧文案改调它。`resolve_stage_plan` 的 `omitted` 去重(`dict.fromkeys`, MM 文件同时在两份清单里、旧口径计数翻倍)。模块 docstring 流程第 3 步 + 函数 docstring 同步(记 issue 26-10-16-1523)。
- `.commands/my-commit-flow/scripts/test_commit.py`: 新增 4 条守阵(去重 / 分组与计数示例 / 示例截断且空组不列 / 真仓「提示与提交面逐条对齐」); 头部「测试计划」清单同步。
- `.commands/my-commit-flow/scripts/test_snapshot.py`(授权修, 为放行闸门): 两条存在性比较(`_snap_dirs`)改为在**本用例私有临时根**内进行 —— 新增 `_private_tmp()`(根 + 子进程 TMPDIR 一并指向它), `-n 8` 并行下不再因兄弟用例落进同一全局临时根而假红; 断言意图不变(import 不重入 / 不留临时副本)。红绿双验(泄漏 / import 重入两类突变判红, 还原 SHA256 一致)。
- `memory-bank/pitfalls/git/ship-commit-staged-delete.md`: 变体二补一行「提示已按索引状态分组, 不再混称『未纳入』」(含与本变体实测的对照)。
- `memory-bank/pitfalls/testing/tmpdir.md`: 新条目「约定盘缺席/不可见 → TMPDIR 静默回落」(识别口径 + 同日收口注)。
- `memory-bank/issues/26-10-16-1523-bug-ship-commit-omitted-note.html`: Open → In Progress(15:33, 复验后)→ Done(15:51); 认领链双向(本切片/档案 Refs ↔ issue doc-refs)。
- `memory-bank/testing/baselines/26-10-16-1551-ship-commit-omitted-note.md`: 本专题基线(test.full / 定向 / 红绿双验 / 既有失败记录)。

## 未做(有意, 范围守恒)

- 方向 B(真正路径限定提交)不做: 属行为面改动, 且会推翻「已暂存删除项随整索引落笔」的既有依赖(坑档 `git/ship-commit-staged-delete.md` 变体二的处方依赖于它)。
- 快照守阵的 ①(家目录 `.git` 形态)未做代码侧加固: 机器已修复; 若将来再现, 可考虑让「无仓库上溯」断言不依赖机器上溯形态。

## 下一步 / 移交

- 立档: 变更集 3 个源文件(`commit.py` + `test_commit.py` + `test_snapshot.py`)命中阈值 ⇒ 见 `memory-bank/tasks/26-10-16-ship-commit-omitted-note.md`(认领链双向)。
- 快照守阵既有红已解除(① 机主修复; ② 经授权修复); `.commands/` 提交闸门不再被挡(提交前 `test.pkg` 实测全绿, 数字见基线切片)。
- 转告(本会话不修): cap 债务 —— activeContext 切片数超阈值 + `26-10-15-0728-qb-traffic-restart-spike-gap.md` 超切片 cap; `pitfalls/testing/redverify-anchor-lineendings.md` 超 pitfall cap —— 另开会话清理。
