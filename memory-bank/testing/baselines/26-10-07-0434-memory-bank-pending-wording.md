# 2693 —— memory-bank 回写措辞守卫: 禁「待提交」类时点相对断言 (develop @ d2b2abf8 + 本轮改动)

> 摘要: 新增回写措辞守卫 `check_wording.py`(扫 `tasks/` + `activeContext/`, 判「待提交 / 未提交(状态) /
> 等…指令 / 粗体未 commit」; 豁免带日期的流水条目与树态描述「未提交改动」)+ 口径单点进 skill「回写措辞」节 +
> 存量清洗 88 处 / 64 文件(84 改 + 4 整行删)。本轮无 src/ 改动(纯 skill / 命令配置 / 测试 / 知识库)。
> 基线时间: 2026-10-07 04:34

**Refs:** memory-bank/tasks/26-10-07-memory-bank-pending-wording.md

- 分支: develop @ **d2b2abf8**(开工 `commands run my-commit-flow.sync` 未跑, 本轮问答起手; 改动全在工作树)
- 命令: `commands run test.full`(Windows)
- **实测 (Windows)**: **2693 passed + 4 skipped, 覆盖率 TOTAL 99%(16021 语句 / 163 未覆盖 /
  5472 分支 / 143 partial)**; pytest 自报 **49.02s**。
- 相对上一条 [26-10-07-0346](26-10-07-0346-webui-drawer-search-jump.md)(2690 + 4 / 16021 / 163 / 5472 / 143):
  passed **+3**(`tests/test_memory_bank.py` 新增 3 条措辞守卫用例 —— 存量零违规 / 四条边界 / 已挂 `kb.check`),
  覆盖四指标**逐位相同**(本轮无 `src/` 改动, 不进 `--cov=src` 统计面)。
- 旁证: `commands run kb.check` 6 步全绿, 其中新守卫自报「回写措辞守卫: 无违规」; 存量清洗前后
  守卫命中数 88 → 0(`tmp-analysis/migrate_pending_wording.py`, 判据 `import` 守卫的 `scan_text`)。
