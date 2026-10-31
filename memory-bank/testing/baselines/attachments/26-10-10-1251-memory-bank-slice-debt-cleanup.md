# 2886 —— memory-bank 切片条数债务清偿(125 → 46)基线

> 摘要: 清理会话清偿 `activeContext/` 条数债务(125 > 70)—— 删 79 片(53 片档案 Done + 26 片无档案蒸馏后删), 留 46 片(5 片真实 md-link 入链 + 9 活跃专题 + cap-debt 专题片 + 近 5 天滚动状态)。无档案旧片按域蒸馏 28 条进 `progress/` 五个 implemented-*.md; 可编辑面 44 处链接改指(11 处 md 链接 + 33 处认领链 Refs token), 冻结件零改动。`SLICE_COUNT_LIMIT` 未抬。
> 专题: memory-bank-cap-debt
> 基线时间: 2026-10-10 12:51

**Refs:** memory-bank/activeContext/26-09-30-2112-memory-bank-cap-debt.md

## test.full 实测

- 分支: `develop`(开工 `my-commit-flow.sync` 快进 5b68b877→cebfdcc4; 工作树含本轮 ~120 文件改动时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2886 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16568 语句 / 166 未覆盖 / 5716 分支 / 143 partial; 门槛 98% 达标; 40.85s)
- 与上基线的差值: `commands run kb.baseline -n 2` 现列(切片正文只写自己的 TOTAL)。
- 增量明细: passed +13 = 开工快进并入的远端区间(快捷键切换 6 条实施等), **本轮零 `src/` 零 `tests/` 改动** —— 改动面全在知识库(memory-bank/ + docs/), 不进 `--cov=src` 统计, 也不在 `testpaths(tests/)` 里。

## 本轮改动面(全部为知识库维护)

- `memory-bank/activeContext/` —— **删 79 片**(判据与逐类数字见 cap-debt 切片), 留 46 片。
- `memory-bank/progress/implemented-{core,webui,webui-perf,testing,tooling}.md` —— 蒸馏条目 +1/+1/+2/+9/+3(旧切片事实压缩, 指针指向档案/计划/坑档单点), 全部仍在 cap 内。
- 认领链修复 33 件(tasks 26 / issues 3 / reports 4): Refs 与 doc-refs 里的 `memory-bank/activeContext/<已删片>` token 移除(双向链另一端已随文件删除, 不产生单向链)。
- `docs/hr-online-verify-docs.md` 8 条链接改指档案/报告/progress(docs 不在 `doc.links` 默认扫描面, 属人读文档修复)。
- `memory-bank/activeContext/26-09-30-2112-memory-bank-cap-debt.md` —— 本轮处置记录 + 最后活动; 生成物 `_index.md` 族 20 个重建。

## 守卫收口

- `kb.check` 全绿(主键 552 文档 · 290 专题 / 认领链闭环 / 回写措辞 / 日期)。
- `doc.links` 绿 / `doc.caps -- --strict` 债务 0 项 / `kb.active` **共 46 个切片**(债务线 70 以下) / `test.one -- tests/test_memory_bank.py` 43 passed。
