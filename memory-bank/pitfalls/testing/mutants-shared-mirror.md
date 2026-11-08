# 多 clone 并行共用 WSL 镜像: 对方的 `rm -rf mutants` 会删掉你正在跑的结果

> 摘要: 变异测试镜像默认是 `~/auto-qb-mut`, **多会话共用**; 而 `mutants.run` 每次都 `rm -rf mutants mutmut-cache.db`。并行会话一开跑, 就会把你**正在跑**的 `mutants/<pkg>/*.meta` 一起删掉 —— 你在下一次结果落盘时崩在 `FileNotFoundError: mutants/.../<file>.meta`(实测: hr 首轮在 5125/8027 处崩, 已跑的 85% 作废)。判别特征: `ps` 里有两份 `mutmut run`; 镜像 `pyproject.toml` 的 `only_mutate` 不是你设的目标; `mutants/` 下出现**别人目标**的 `.meta`。处置: 每会话用专用镜像 `--mirror '~/auto-qb-mut-<pkg>'`, 并存时把 `--children` 降到 3。
> 触发: 多 clone 并行, 共享镜像, 并行会话, rm -rf mutants, FileNotFoundError, .meta 被删, mutmut 崩, only_mutate 被改, 专用镜像, --mirror, --children

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

### 现象与判别 (2026-10-10, hr 首轮踩到)

- **触发**: 本工作区在默认镜像 `~/auto-qb-mut` 上跑 hr 包变异审计时, 另一份 clone 的会话在同一镜像上跑 config 轮。触发条件: **两个会话共用同一个镜像路径**(默认值), 且**时间上重叠**。

- **现象**: 本会话的 `mutants.run` 跑到 `5125/8027`(≈64%)时崩:
  ```
  File ".../mutmut/mutation/data.py", line 122, in save
      with open(self.meta_path, "w") as f:
  FileNotFoundError: [Errno 2] No such file or directory: 'mutants/src/auto_qb/hr/runtime.py.meta'
  ```
  目录明明在、文件却打不开 —— 因为对方会话的 `mutants.run` 在 `[4/6]` 步执行了 `rm -rf mutants`, 把本会话**已跑 85% 的 `mutants/src/auto_qb/hr/*.meta` 整目录删了**。

- **判别**(三条同时成立即可确认):
  1. `ps -eo pid,etime,cmd | grep "[m]utmut run"` → **两份** `mutmut run`, 其中一份的 `--max-children` 与你给的不同;
  2. `grep -m1 only_mutate <mirror>/pyproject.toml` → **不是你设的目标**(实测被对方改成 `["**/config/*.py"]`);
  3. `find <mirror>/mutants -name '*.meta'` → 出现**别人目标**的 `.meta`(如 config), 而**你自己的目标一条都没有**。
  另: 崩点前最后一次成功落盘的 `.meta` 时间戳会**早于**对方的开跑时间。

- **处置**:
  1. **每会话一份镜像**: `commands run mutants.run -- --mirror '~/auto-qb-mut-<pkg>' ...`(后续 `mutants.report` / `mutants.verify` 也要带**同一个** `--mirror`)。首次会 `git clone`(≈12s) + `uv sync` + 装 mutmut, 成本低。
  2. **并存时降并发**: 对方用 4 时本会话用 `--children 3`(WSL 只有 8 核, 4+4 会互相拖慢甚至打挂)。
  3. **已被冲掉的轮次**: 若崩前已跑过大半, 可用 mutmut 续跑补齐(见 skill 硬约束 15), 不必从零重跑 —— 但续跑点若也被删就只能重跑。

**复发**: 1 —— 2026-10-10 hr 首轮(直接损失: 已跑的 ≈60 min / 85% 作废; 改用专用镜像后整包 96 min 跑完)。
