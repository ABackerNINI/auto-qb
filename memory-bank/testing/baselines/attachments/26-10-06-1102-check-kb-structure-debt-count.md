# 2677 —— 修 check_kb_structure CLI 把「下限提示」也算成「cap 债务」的口径缺陷

> 摘要: `check_kb_structure.py` 的汇总行原用 `len(warns)` 计「cap 债务 N 项」, 而 `warns` 里混着
> `CAP_MIN_WARN` 的「过小」提示(不带 `DEBT_MARK`)⇒ 该行**恒报 ~40 项、永不清零**(实测 40 项 vs 真实 0),
> 与 `pitfalls/kb/cap-debt.md` 第 1 条「债务数必须能清零」相悖。修法 = 分类收成单点
> `split_warns(warns) -> (债务, 提示)`, CLI 只数债务侧 + 两类**分开贴标签**; 顺带订正两处把 warns 当
> 「债务清单」的注释。新增守卫 1 条(**红验已过**)。**提交闸门从来不受影响**(`check_context_caps.py`
> 一直按 `DEBT_MARK` 过滤, 实测 0)。
> 基线时间: 2026-10-06 11:02

**Refs:** memory-bank/activeContext/26-09-30-2112-memory-bank-cap-debt.md

- 分支: develop @ **e0601315**(工作树含本轮改动未提交)
- 命令: `commands run test.full`(Windows —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **2677 passed + 4 skipped, 覆盖率 TOTAL 99%**
  - 语句 **16021** / 未覆盖 **163** / 分支 **5472** / partial **143**。
  - 耗时: 单次 **46.08s**(wall 47.5s) ⇒ 区间约 **45~48s**。
- 相对上一条基线 [26-10-06-1053](26-10-06-1053-memory-bank-cap-cleanup.md)(2676 + 4 / 16021 / 163 / 5472 / 143):
  passed **+1** —— 新增守卫 `test_kb_debt_count_excludes_min_size_hints`; 语句 / 未覆盖 / 分支 / partial 逐位相同。
- **红验**: 把 `debts, hints = split_warns(warns)` 退回 `debts, hints = warns, []`, 守卫立刻转红
  (CLI 报 `cap 债务 1 项` —— 那个 1 就是「过小」提示), 还原后转绿 ⇒ 它不是恒绿断言。
- 守卫: `tests/test_memory_bank.py` **33 passed** · `commands run doc.caps` 债务 0 项 ·
  `kb.check` 绿(459 文档 · 250 专题, 主键 + 认领链 OK) · `doc.links` 绿 · `kb.active --check` 绿 · `doc.drift` 0 处。
- 改动面:
  - `.agents/skills/memory-bank/scripts/check_kb_structure.py` —— 新增 `split_warns()` 单点; CLI 汇总行只数
    带 `DEBT_MARK` 的行, 无债务时明写「cap 债务 0 项」; 「过小」提示改贴 `[提示]`(原与债务同贴 `[WARN]`,
    几十条建议看着像几十笔欠债); 订正 `check_caps` docstring 与 `run_all` 内注释(原写「warns 就是 cap 债务清单」)。
  - `tests/test_memory_bank.py` —— 新增 `test_kb_debt_count_excludes_min_size_hints`(造「只有过小文件」的
    tmp 库 → 必须报 `cap 债务 0 项`; 再加一个超限文件 → 报 `1 项`) + 头部「## 测试计划」清单同步。
  - `memory-bank/pitfalls/git/editing-traps.md` —— 新条目「Git Bash 里 `sed -i` 会把整份文件的行尾改成 CRLF」:
    本轮做红验时踩到 —— `sed -i` 把 HEAD 为 LF 的脚本整份写成 CRLF, `git diff` **看不见**, 而
    `_common.char_count()` 在 CRLF 上每行多算 1 ⇒ cap 检查会凭空多出一笔债。
    与上一轮新记的「拿 KB 字节比字符数 cap」**同族**: 口径不一致 ⇒ 报出根本不存在的债务。
  - `memory-bank/activeContext/26-09-30-2112-memory-bank-cap-debt.md` —— 原「未修·待用户决定是否入池」的
    条目改记为**已修**(用户点名「修 check_kb_structure.py」)。
  - 生成物 `_index.md` 族(20 个重建)。
- 行尾: 改动面全为 **LF**; `26-09-30-2112` 切片与 `pitfalls/kb/cap-counting.md` 是本 clone 的**存量 CRLF**
  (HEAD blob 是 LF, 归一层3 未做), 未做一次性转换(与仓库既定处置一致), 且都不是 MIXED。
- **已入库**: `4236975c`(与清三项 cap 债务的 `26-10-06-1053` 同笔; ship.commit 内部同步 rebase 重放 `0a78d64e→4236975c`)。
