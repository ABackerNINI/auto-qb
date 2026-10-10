# 变异镜像工作树残留上一轮 apply 的变异体，而 `git status` 看不出来

> 摘要: `mutants.run` / `mutants.verify` 是**就地改源码**的(`mutmut apply` 把变异体写进镜像 `src/`), 正常路径跑完会还原。但上一轮被**中断**(超时被杀 / `TaskStop` / 崩)时, 变异体可能**留在镜像工作树里**, 而 `git status` / `git diff` / `git update-index --really-refresh` **全判净**(替换前后**字节数相同**时 git 的 stat 缓存直接跳过内容比对)。后果: 下一次 `--no-refresh` 轮**带着一个已被变异的源码**开跑, 该文件的变异体集合与基线都不再是 develop, 结果不可信 —— 而且**没有任何报错**。判别: 跑 `--no-refresh` 前, 别信 `git status`, 直接 `grep` 目标文件的关键行(或 `git checkout -f -- src/` 无条件还原)。实测残留: hr 专用镜像 `~/auto-qb-mut-hr` 的 `queue.py` 留着 `left = deadline + time.monotonic()`(= `wait__mutmut_19`)。
> 触发: 变异测试, mutmut, 镜像残留, 工作树脏, apply 未还原, 中断, TaskStop, 超时被杀, --no-refresh, git status 判净, stat 缓存, 同长度替换, git diff 看不出, git checkout -f, 基线污染

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md, memory-bank/testing/baselines/26-10-10-1458-mutants-hr-serialization.md

### 现象与处置 (2026-10-10, hr serialization 轮)

- **触发**: 本轮用 `--no-refresh` 在专用镜像 `~/auto-qb-mut-hr` 上跑 `**/hr/queue.py`。开跑前惯例核对镜像 src 与主仓一致(sha1sum) —— `model.py` / `store.py` 相符, **`queue.py` 不符**。

- **判别**: 逐行 diff 后发现镜像 `queue.py` 的 `wait()` 里是 `left = deadline + time.monotonic()`(源码应为 `-`), 即 **R14 整包轮某个被中断的 `mutmut apply` 残留**。诡异之处:
  - `git status --short src/auto_qb/hr/queue.py` → **空**(判净);
  - `git diff src/auto_qb/hr/queue.py` → **空**;
  - `git update-index --really-refresh` 之后再 `git status --porcelain src/` → **仍空**;
  - 但 `git show HEAD:src/auto_qb/hr/queue.py` 里是**正确**的 `-`。
  - **根因**: 该变异是**同长度替换**(`+` ↔ `-`), 且 mutmut 的写回使文件的 stat(mtime/size)与索引记录**一致** ⇒ git 的 stat 缓存**直接跳过内容比对**, 不读文件内容就判「未修改」。`--really-refresh` 只是刷新 stat 缓存, **不强制读内容**, 所以也看不见。
  - **判别口诀**: 判「镜像干净」**不能只看 `git status`** —— 必须直接读内容(`grep` 目标函数的关键行, 或与主仓逐行 diff)。

- **处置**:
  1. 跑 `--no-refresh` 轮**之前**, 无条件 `git -C <mirror> checkout -f -- src/` 把工作树强制还原到 HEAD(`-f` 会真的重写文件, 不受 stat 缓存影响)。**不要**用 `git status` 当放行判据。
  2. 验证镜像与主仓一致时, **别只看 sha1** —— 镜像与主仓的行尾可能不同(实测镜像 LF / 主仓 CRLF), 同名文件 hash 天然不等; 要核**内容**(`grep` 关键行 / 归一化行尾后比对)。
  3. 更稳的做法: 该轮跑完(或任何中断后)**主动** `git checkout -f -- src/` 复位一次, 不把「工作树干净」当作默认前提。

- **同源风险面**: 任何「就地改源码再还原」的工具(`mutants.verify` 逐条 `apply` → 跑 → 还原; 红验脚本)在**中断**时都会留残留; 中断途径包括 `mutants.run` 撞 timeout、`TaskStop`、shell 崩。红验脚本宜把「原字节还原」放进 `try/finally`(本轮实测: 被 `TaskStop` 硬杀时 `finally` **没跑**, 主仓 `src/` 留了变异体 —— 只能事后 `git checkout -- src/` 复位)。

**复发**: 1 —— 2026-10-10 hr serialization 轮(未造成实际错数: 开跑前 sha1 核对时发现并复位)。
