# 并行会话共用同一份变异镜像仓: 对方的 `rm -rf mutants` 会删掉你正在跑的结果

> 摘要: (2026-11-12 起容器口径) 镜像仓默认**按目标派生** `/root/auto-qb-tests/mutation/<pkg>`(`mutants.py` 的 `derive_mirror`, 每目标一份), **换目标互不冲**; 但容器 `auto-qb-testbed` 是**全宿主共享**的(多 clone 的会话都 exec 进同一个容器), **同 target 的并行会话仍互冲** —— `mutants.run` 的 `[4/6]` 步 `rm -rf mutants mutmut-cache.db` 会把正在跑的 `mutants/**/*.meta` 一起删掉, 下一次结果落盘时崩在 `FileNotFoundError: mutants/.../<file>.meta`(WSL 时代实测 hr 首轮在 5125/8027 处崩, 85% 作废)。**同目标并行**时: `--mirror <容器内绝对路径>` 各占一份(`report` / `verify` 带**同一个** `--mirror`), 并存时把 `--children` 降到 2(对方 3); **不同目标**用默认派生仓即天然隔离。
> 触发: 并行会话, 共享镜像, rm -rf mutants, FileNotFoundError, .meta 被删, mutmut 崩, only_mutate 被改, 专用镜像, --mirror, --children, 同 target 并行, 容器共享, 按目标派生, derive_mirror

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

### 容器形态(2026-11-12 起): 冲突面按目标收窄, 同目标并行未消失

- **冲突面收窄**: 镜像仓不再共用一份(WSL 时代默认 `~/auto-qb-mut` 全目标共用), 而是按 `--target` 的 slug 派生 `<MUTATION_ROOT>/<pkg>` —— 目标 A 的 `rm -rf mutants` 不再碰目标 B 的注册表/缓存。
- **未消失的部分**: 容器全宿主共享 → **同 target** 的两个并行会话(哪怕来自不同 clone)落在**同一个**镜像仓里, 互冲机制与 WSL 时代完全相同。同目标并行时 `--mirror` 显式各占一份, 注意:
  - `--mirror` 必须是**容器内绝对路径**(`/...` 或 `~/...`)—— 收到 Windows 路径或被 Git Bash/MSYS 改写的路径会在 `check_mirror` 停手(手工调用时 `~` 加引号、容器绝对路径加 `MSYS_NO_PATHCONV=1`; 走 `commands run mutants.*` 则参数经 python argv 直传, 不受影响);
  - `report` / `verify` 要带**同一个** `--mirror`, 否则读的不是同一份注册表。
- **判别**(容器内, 三条同时成立即可确认):
  1. `docker exec auto-qb-testbed ps -eo pid,etime,cmd | grep "[m]utmut run"` → **两份** `mutmut run`, 其中一份的 `--max-children` 与你给的不同;
  2. `grep -m1 only_mutate <镜像仓>/pyproject.toml` → **不是你设的目标**(实测被对方改成 `["**/config/*.py"]`);
  3. `find <镜像仓>/mutants -name '*.meta'` → 出现**别人目标**的 `.meta`(如 config), 而**你自己的目标一条都没有**。
  另: 崩点前最后一次成功落盘的 `.meta` 时间戳会**早于**对方的开跑时间。

- **处置**:
  1. **同目标并行 = 每会话一份镜像**: `commands run mutants.run -- --mirror '/root/auto-qb-tests/mutation/<pkg>-<会话标记>' ...`(后续 `report` / `verify` 带同一个 `--mirror`)。首次会 `git clone`(容器内直连 Gitee, 实测 ≈13.5s)+ venv(cp 模板 + delta, 实测秒级), 成本低。
  2. **并存时降并发**: 对方用 3 时本会话用 `--children 2`(容器 8 vCPU / 12G 内存, 纪律同 WSL 时代, 4+4 会互相拖慢甚至 OOM)。
  3. **已被冲掉的轮次**: 若崩前已跑过大半, 可在容器里续跑补齐(见 skill 硬约束 15, 配方在包 note), 不必从零重跑 —— 但续跑点若也被删就只能重跑。

### 历史留痕(WSL 形态, 2026-10-10, hr 首轮踩到; 2026-11-12 随 S4 容器迁移, 共用默认改为按目标派生)

- **触发**: 本工作区在默认镜像 `~/auto-qb-mut` 上跑 hr 包变异审计时, 另一份 clone 的会话在同一镜像上跑 config 轮。触发条件: **两个会话共用同一个镜像路径**(默认值), 且**时间上重叠**。

- **现象**: 本会话的 `mutants.run` 跑到 `5125/8027`(≈64%)时崩:
  ```
  File ".../mutmut/mutation/data.py", line 122, in save
      with open(self.meta_path, "w") as f:
  FileNotFoundError: [Errno 2] No such file or directory: 'mutants/src/auto_qb/hr/runtime.py.meta'
  ```
  目录明明在、文件却打不开 —— 因为对方会话的 `mutants.run` 在 `[4/6]` 步执行了 `rm -rf mutants`, 把本会话**已跑 85% 的 `mutants/src/auto_qb/hr/*.meta` 整目录删了**。

- **处置**(WSL 形态): ①每会话一份镜像 `--mirror '~/auto-qb-mut-<pkg>'`(WSL 路径形态, 已随容器迁移退役); ②并存时降并发; ③可续跑补齐。

**复发**: 1 —— 2026-10-10 hr 首轮(直接损失: 已跑的 ≈60 min / 85% 作废; 改用专用镜像后整包 96 min 跑完)。容器形态(2026-11-12 起)未复发 —— 冲突面按目标收窄, 预防靠「同目标并行才各占一份镜像」的纪律。
