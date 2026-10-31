# 红验逐条 apply 时 `.pyc` 缓存未失效，读到上一条变异体 ⇒ 假 SURVIVED（等长替换 + 秒级 mtime 碰撞）

> 摘要: 红验/`mutants.verify` 这类「逐条 apply 变异体 → 跑 pytest → 还原」的循环里，同一条源码行若被**等长替换**（如 `get(None, view.channel_state)` ↔ `get(view.channel_state, None)`），且相邻两条的 apply/跑/还原在**同一秒内**完成，则 Python 的 `.pyc` 缓存判据 `(源文件 mtime, size)` **两条都相同**（mtime 秒级精度 + size 因为等长也相同）⇒ 子进程 import 时**直接复用上一条变异体编译出的字节码**，实际跑的还是上一轮的代码。后果：本该被守阵杀掉的变异报 **SURVIVED**（假存活），且**没有任何报错**；在同一份 dump 上重复跑还会**稳定复现**同一批假存活（不是偶发抖动）。与 [mutants-mirror-dirty-worktree](mutants-mirror-dirty-worktree.md) 同族（同是「等长替换让缓存比对失效」，那档是 git stat 缓存判净，本条是 Python 字节码缓存判新）。判别: 同一条变异**单跑 KILLED、全量跑 SURVIVED**（或反之）就要怀疑缓存；实测 hr display 轮 `_print_site m23/m24`（`CHANNEL_TEXTS.get` 的两个实参互换，等长）稳定假 SURVIVED。处置: 跑测试的子进程加 `-B` / `PYTHONDONTWRITEBYTECODE=1` **并**开工前清 `__pycache__`（`PYTHONDONTWRITEBYTECODE` 只禁写新缓存，**已有的旧 `.pyc` 仍会被读**）；`.pytest_cache` 由 `-p no:cacheprovider` 另管，与本条无关。
> 等级: L0
> 触发: 红验, 变异测试, mutmut, apply, 同构变异, 假存活, 假 SURVIVED, pyc, pycache, __pycache__, 字节码缓存, 缓存未失效, mtime 秒级, size 相同, 等长替换, 同长度替换, PYTHONDONTWRITEBYTECODE, python -B, importlib 缓存, 单跑 KILLED 全量 SURVIVED

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md, memory-bank/pitfalls/testing/mutants-mirror-dirty-worktree.md, memory-bank/testing/baselines/26-10-15-1200-mutants-hr-display.md

### 现象与处置 (2026-10-15, hr display 轮)

- **触发**: 本轮红验脚本（dump 驱动同构变异逐条 apply → 跑定向池 → 原字节还原）跑全量 540 条，`_print_site m23/m24` 报 SURVIVED。但这两条的语义差异**肉眼可辨**（m24 把未知通道态的回落值从原文改成 `None`，池内 `test_print_site_lines_exact` 明写 `assert "通道=zzz" in lines[3]`）。手工 apply 该变异 → 跑测试 → **FAILED（KILLED）**，与脚本判定矛盾。

- **根因（两层同时成立才触发）**:
  1. **等长替换**：`CHANNEL_TEXTS.get(None, view.channel_state)`（m23）与 `get(view.channel_state, None)`（m24）**字符数相同** ⇒ 两次 apply 后**文件 size 相同**，还原到原文件时 size 也相同（原式 `get(view.channel_state, view.channel_state)` 恰好同长）。
  2. **秒级 mtime 碰撞**：逐条跑一条约 0.5s（`.venv/bin/python -m pytest` 直跑），相邻两条的「apply → 跑 → 还原 → 再 apply」落在**同一秒**内 ⇒ `(mtime, size)` 与上一条编译时记录的**完全一致** ⇒ CPython 认为 `.pyc` 有效，**不重编译**。
  - 于是 m24 的子进程实际 import 了 m23 变异体编译的字节码（m23 行为与本条等价 ⇒ 池全绿 ⇒ 假 SURVIVED）。
  - **与「守阵真的挡不住」在输出上无法区分**：两次全量跑给出**逐条一致**的 149/106 假数（稳定性反而更像真结论，危害更大）。

- **判别**:
  - **单条 vs 全量判定不一致**（同一条变异单跑 KILLED、落在长链里 SURVIVED）⇒ 先怀疑缓存，不要改守阵。
  - **相邻条同长**这一特征可作辅助线索（dump diff 里 `-`/`+` 行字符数相同）。
  - 交叉验证：只跑该文件段（同一条在别的位置/别的顺序下判定是否翻转）。

- **处置**:
  1. 子进程一律加 `-B`（`python -B -m pytest`）**并且** `env["PYTHONDONTWRITEBYTECODE"]="1"`。**只设环境变量不够** —— 已存在的旧 `.pyc` 仍会被 import 读取，必须配合下一步。
  2. 开工清缓存：`for d in src/**/__pycache__ tests/**/__pycache__: rmtree(d)`（放在红验脚本的 `check_clean()` 里，与 `git checkout -- src/` 同处）。
  3. **红验数字须与 S6（mutmut 权威工具）对差**：mutmut 逐条 apply 也会踩同源缓存吗？mutmut 每条变异**重写整个文件并换 mtime**，且其内部按 hook 记录状态，本机未观测到同类偏差；但**红验自建的 applier 必须自证** —— 单条复跑抽查是廉价的自证手段（本轮正是这样抓到）。

- **为什么脚本里 `ast.parse` 自检挡不住**: 语法自检只看「变异体本身是否合法」，而本条的问题是**跑的根本不是这个变异体**，两者正交。

**复发**: 1 —— 2026-10-15 hr display 轮（假 SURVIVED 已污染前两次全量读数，第三次修好后 `_print_site m24` 翻为 KILLED；同批还发现 `m23` 是真等价，两回事要分开判）。
