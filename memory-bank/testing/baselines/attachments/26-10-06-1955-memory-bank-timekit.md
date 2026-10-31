# 2682 —— memory-bank 取时间标准化: timekit 单点 + 三层日期守卫 (@ 开发中, 未提交)

> 摘要: 新增 `timekit.py`(UTC+8 单点取时 + 三层日期守卫) 并接入 `commands run kb.time` /
> `kb.check` / 提交闸门; create-issue 钉 +08; `check_doc_links.py` 迁入 skill; 存量日期清洗 +
> 收口 `gen_active_recent` 静默回退。测试 +4(TZ 无关 / 三层种子 / 代码与路径不误报 / 存量零违规)。
> 基线时间: 2026-10-06 19:55

**Refs:** memory-bank/activeContext/26-09-30-0936-memory-bank-timekit.md

- 分支: develop @ **60071716**(开工 `commands run my-commit-flow.sync` = `已同步 60071716`;
  工作树含本轮 skill / 命令 / 文档改动, **未提交**)
- 命令: `commands run test.full`(Windows)
- **实测 (Windows)**: **2682 passed + 4 skipped, 覆盖率 TOTAL 99%**; pytest 自报 **52.15s**。
  语句 **16021** / 未覆盖 **163** / 分支 **5472** / partial **143**。
- 相对上一条 [26-10-06-1928](26-10-06-1928-ext-shorttime-add-date.md)
  (2678 + 4 / 15823 / 163 / 5472 / 143): passed **+4**(本轮新增 4 条守卫用例); 未覆盖 / 分支 /
  partial **逐位相同**; 语句 **15823 → 16021**(+198) —— 本轮**未碰 `src/`**(改动全在
  `.agents/skills/` / `.commands/` / `memory-bank/` / `tests/`), 覆盖率口径 `--cov=src` 收不到它们,
  该差值来自并行会话已入库的提交(上一条测的 15823 是那轮工作树的瞬时值)。
- 其它机检: `commands run test.pkg` **131 passed**; `commands run kb.check` 绿(日期守卫无违规);
  `commands run doc.drift` / `doc.links` 绿; `commands run doc.caps` 无债务(SKILL.md 8,507/15,000)。
