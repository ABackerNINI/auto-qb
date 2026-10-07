# 基线切片 26-10-07-0940 — 详情面板变体骨架去重(reg.helpers 单点收口)

> 摘要: 认领 issue 26-10-07-0845(P3-8)实施收尾 —— 核心层 reg.helpers 骨架单点 + 变体 01-12
> 消费去重 + 两个守阵口径同步(test_web.py), Python 产品代码零改动。净 -111 行。
> 基线时间: 2026-10-07 09:40
**Refs:** memory-bank/issues/26-10-07-0845-refactor-webui-drawer-tpl-dedup.html · memory-bank/activeContext/26-10-07-0940-webui-drawer-tpl-dedup.md

- 分支: develop @ `732c20c6`(工作树含本轮未提交改动)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2712 passed + 4 skipped, 49.84s, 覆盖率 TOTAL 99%**
  (16061 语句 / 163 未覆盖 / 5496 分支 / 143 partial; 门槛 98% 达标)
- 相对上基线 (26-10-07-0836: 2712 passed + 4 skipped / 99% / 52.13s): passed/语句/分支全同
  (重构轮零新增测试函数, 两个既有守阵原地改口径), 未覆盖与 partial 数字一致, 无回归信号。
- 耗时 52.13s→49.84s 为单次采样波动(同机历史采样区间内), 按口径不更新区间结论。
