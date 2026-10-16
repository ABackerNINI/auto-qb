# 26-10-16-ship-commit-omitted-note — ship.commit 子集提示与实际提交面对齐(issue 26-10-16-1523 认领与修复)

**Status:** Done
**Added:** 2026-10-16
**Updated:** 2026-10-16
**Summary:** 用户指令「认领并修复 memory-bank/issues/26-10-16-1523-bug-ship-commit-omitted-note.html」→ 修复后「提交」。子集提交旧提示「另有 N 个改动未纳入」把已暂存的未传改动读成「没进本笔」, 而 `git commit` 提交的是整个索引(入池实测: 10 个 `D ` 撤跟踪项被列成「未纳入」却全在同一笔里)。落盘 = issue §06 方向 A(措辞与语义对齐, 不动提交行为; 方向 B「真正路径限定提交」不做 —— 会推翻坑档 `git/ship-commit-staged-delete.md` 已依赖的「已暂存删除项随整索引落笔」便利): `commit.py` 新增 `omitted_note()` 按索引状态分组(已暂存/未暂存各给计数与示例, 空组不列)、`omitted` 去重(MM 文件不再翻倍); `test_commit.py` 新增 4 条守阵; 红绿双验 3 类突变逐类判红。提交阶段被快照守阵两条既有红挡下(与本次改动无关), 经用户裁决处置: ① 家目录空 `.git` 由机主移除; ② `test_snapshot.py` 两处存在性比较改为「用例私有临时根」内进行(子进程 `TMPDIR` 一并指向它), `-n 8` 跨 worker 假红消除(红绿双验 2 类突变)。测试数字唯一权威在基线切片(见 **Refs:**)。变更集 3 个源文件 ⇒ 命中立档阈值, 建本档。
**Topics:** ship-commit-omitted-note

**Refs:** memory-bank/issues/26-10-16-1523-bug-ship-commit-omitted-note.html,memory-bank/activeContext/26-10-16-1533-ship-commit-omitted-note.md

## 原始请求

> 用户(2026-10-16): 「认领并修复 memory-bank/issues/26-10-16-1523-bug-ship-commit-omitted-note.html」
> 用户(2026-10-16): 「提交」
> 提交被闸门挡下后, 用户裁决: 「我已移除 home 空 .git 目录」; 选「授权我修 ②:并行竞态(最小修)」。

## 思考过程与决策

- **请求边界判定**: 首条 = 执行任务(认领 + 修复, 用户显式指派); 末条「提交」= commit + push 单点授权(触发词口径)。提交受阻后的两项处置各经用户显式裁决。
- **复验先于改动**(防过期原则第 5 条): scratch 探针在临时仓库重放 issue §01 场景(已暂存删除 `D  base.txt` + 未暂存 `?? loose.txt`, 只传 `x.txt`)⇒ **仍复现**: 提示把 base.txt 列进「未纳入」, 而同一笔 `git show --name-status HEAD` = `D base.txt` + `A x.txt`。
- **修法取方向 A, 否掉 B**: 子集模式只限制 `git add` 清单、`git commit` 提交的是整个索引 —— 提示应当描述**提交面**。方向 B(真正路径限定提交)会推翻坑档已依赖的「已暂存删除项随整索引落笔」便利(忽略规则生效后没法再 `git add` 那条路径, 只能靠整索引带走), 且现状不影响正确性; 与 issue §06 的取舍建议一致。
- **顺带 omitted 去重**: MM 文件(staged + unstaged 两份清单都在)旧口径会让计数与示例翻倍 —— 提示要让「计数可信」, 去重(`dict.fromkeys`)属同族修复。
- **提交受阻的两次处置**(均与本次改动无关, 判定依据 = 单跑该文件即复现、不加载改动面):
  - ① 家目录空 `.git`(`C:\Users\11059\.git`)+ 本机 `R:` 盘缺失 ⇒ 约定 `TMPDIR` 回落 `%TEMP%` ⇒ 快照守阵上溯命中家目录 —— 机器侧问题, 用户移除该目录后消失。
  - ② `-n 8` 并行下 `_snap_dirs()` 比较**全局**临时根, 兄弟用例的临时快照目录落进同一根 ⇒ 逐位比较假红(此前闸门侧一过一败、更高频为红)。**最小修 = 把比较窗口收进「本用例私有临时根」**: 新增 `_private_tmp()`, 子进程 `TMPDIR` 一并指向它; 断言意图不变(该操作不得新增/遗留快照目录), 且与并行无关。
- **立档判定**: 变更集源文件 3 个(`commit.py` + `test_commit.py` + `test_snapshot.py`)命中阈值 ≥3 ⇒ 建本档(认领链双向: 本档 ↔ issue; 切片与基线并列引用)。

## 实现计划

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 开工同步(`my-commit-flow.sync`, 已同步 a6b0a784) + 路由(pitfalls/git + issue + skill) | Done |
| S2 | 复验(临时仓库探针重放 §01 场景) | Done |
| S3 | 认领: issue Open → In Progress + 复验小节 + 认领链(切片)+ `kb.index` | Done |
| S4 | `commit.py` 提示分组 `omitted_note()`/`_sample()` + `omitted` 去重 + docstring 同步 | Done |
| S5 | `test_commit.py` 新增 4 条守阵 + 测试计划清单同步 | Done |
| S6 | 红绿双验 3 类突变(旧文案回潮 / 去重回退 / 分组打反)+ 还原哈希比对 | Done |
| S7 | `test.full` + 基线切片 + issue 置 Done + 坑档回写 + `kb.index`/`kb.check` 全绿 | Done |
| S8 | 提交受阻处置: ① 机主移除家目录空 `.git`; ② 经授权修 `test_snapshot.py` 并行竞态(私有临时根)+ 红绿双验 2 类 + `test.pkg` 全绿 | Done |
| S9 | 建档 + 重跑 `ship.commit`(本档随该笔入库) | Done |

## 子任务状态表

| 子任务 | 状态 | 说明 |
|---|---|---|
| 子集提示分组 | Done | 已暂存组 / 未暂存组各给计数与示例, 空组不列; 打印点改调 |
| `omitted` 去重 | Done | MM 文件不再翻倍(`dict.fromkeys`) |
| 守阵(4 条) | Done | 去重 / 分组 / 示例截断 / 真仓「提示=提交面」逐条对齐 |
| 红绿双验 | Done | 3 类(issue 修复)+ 2 类(快照守阵)逐类判红, 还原 SHA256 一致 |
| 基线切片 | Done | `26-10-16-1551-ship-commit-omitted-note.md`(数字唯一权威) |
| 快照守阵并行修复 | Done | 经用户授权; `_private_tmp()` + 两处比较收进私有根; 串行 / 并行多次全绿 |
| 提交入库 | Done | 两轮被既有红挡下 → 处置后重跑 `ship.commit`(结果行见会话回复) |

## 进度日志

- **2026-10-16 15:23 | 入池**(非本轮): issue 由上一会话入池(附取证)。
- **2026-10-16 15:33 开工同步 + 认领 + 复验**: 同步「已同步 a6b0a784」; issue Open → In Progress; 复验 ⇒ 仍复现(探针 `.openclaw/tmp/probe_1523_subset_note.py`, 未入库)。
- **2026-10-16 15:38 落盘 + 红绿双验**: `commit.py` + `test_commit.py` 落盘; 修复后探针输出与提交面逐条一致; 3 类突变逐类判红、还原 SHA256 一致(驱动 `.openclaw/tmp/mutate_1523_driver.py`)。
- **2026-10-16 15:45~15:51 全量与收尾**: 定向守阵全绿; `test.full` 全绿; 基线切片新建; issue 置 Done; 坑档两条回写(git 族「提示已分组」/ testing 族「约定盘缺席 → TMPDIR 静默回落」); `kb.index`/`kb.check` 全绿。
- **2026-10-16 16:32~17:00 提交受阻段**: 首轮 `ship.commit` 被 `test.pkg` 闸门挡下(① 家目录空 `.git` 致快照守阵上溯命中); 用户移除该目录后二轮仍被 ② 挡下(`-n 8` 并行假红, 一条红)。经用户授权按「用例私有临时根」修 `test_snapshot.py` 并红绿双验(泄漏 / import 重入两类突变判红, 还原哈希一致); 定向: 串行全绿、`-n 8` 连续三次全绿(修复前连续红), 全量 `test.pkg` 全绿(数字见基线切片)。
- **2026-10-16 17:04 建档 + 复提交**: 变更集命中立档阈值(3 源文件) ⇒ 建本档; 重跑 `ship.commit`。

## 未做 / 残留(转告)

- 方向 B(真正路径限定提交)不做: 见「思考过程与决策」。
- 快照守阵的 ① 未做代码侧加固(机器已修复; 若将来再现可考虑让「无仓库上溯」断言不依赖机器形态)。
- cap 债务转告(本会话不修): activeContext 切片数超阈值 + `26-10-15-0728-qb-traffic-restart-spike-gap.md` 超切片 cap; `pitfalls/testing/redverify-anchor-lineendings.md` 超 pitfall cap。
