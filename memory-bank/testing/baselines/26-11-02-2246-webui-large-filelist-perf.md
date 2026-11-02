# 4888 passed + 2 skipped(根) —— 清理 tmp-analysis 残留后全量 + W6 测量先行(建议 W6b Dropped / W6a 做)

> 摘要: 清理 tmp-analysis 残留后全量 + W6 测量先行(建议 W6b Dropped / W6a 做)
> 基线时间: 2026-11-02 22:46
**Refs:** memory-bank/tasks/26-11-02-webui-large-filelist-perf.md, memory-bank/plans/26-11-02-0351-plan-webui-large-filelist-perf.html

## 验收数字

`commands run test.full` 实测(2026-11-02 22:46, 工作区未入库态, 清理 `tmp-analysis/s6_test_discovery.py` 后):

- 汇总行: `4888 passed, 2 skipped, 3 warnings in 182.77s (0:03:02)`
- 覆盖率: TOTAL 22523 stmts / 134 miss, 分支 7728/128 miss, **99%**(门槛 99% 达标)
- 零 failed; 清理前唯一 failed 为 `test_free_port_single_source`(被 gitignored 的 `tmp-analysis/s6_test_discovery.py` 内嵌 `def _free_port` 误报), 删除后 `test.one tests/test_free_port.py` 单独复验通过

e2e / W6 测量(同一树, 均零 failed; W6 数字明细见计划 §06.1):

- `commands run dev.e2e -- drawer-content-perf.spec.mjs window-invalidation.spec.mjs`: 8 passed / 6 skipped(window-invalidation 默认 300 种子档按 `TORRENTS<=500` 跳过; 千级档需 `E2E_TORRENTS=3000`)
- `E2E_TORRENTS=3000 commands run dev.e2e -- perf.spec.mjs`: 20 passed(含 W5 同屏交叉 2 条)
- W6 临时测量 spec(测完删除, 未进守阵): 2 用例 × 3 轮 = 6 passed; 关键数字: W6a 现状徽章可见 142-153ms / 乐观写候选 16.5-19.6ms; W6b payload 127911B / 取数 4.3-4.8ms / parse 0.15-0.18ms / rowsFn 6.0-6.3ms

## 本改动面

- `tmp-analysis/s6_test_discovery.py` — 删除(2026-10-15 一次性生成器残留, gitignored; 其内嵌测试模板含端口实现, 是 `test_free_port_single_source` 的唯一误报源)。`tmp-analysis/` 其余旧草稿未动
- `memory-bank/plans/26-11-02-0351-plan-webui-large-filelist-perf.html` — §06 拍板记录回填 D1/D2/D3 + 新增 §06.1 测量条件/实测数字/代码实况/真机轨待跑清单
- `memory-bank/tasks/26-11-02-webui-large-filelist-perf.md` — Summary/S9-S11/进度日志/Refs 更新, 状态保持 In Progress
- `e2e/w6-measure.spec.mjs` — 临时测量用, 测完已删除; 生产代码零改动
