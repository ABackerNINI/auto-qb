# 基线 · 1756 passed + 3 skipped —— config 迁移写回事故修复轮(writer 写盘前先迁移提交树)

> 摘要: 生产事故修复: WebUI 保存把浏览器往返的 v1 旧键树**带 v2 章直接落盘**(校验走的是
> 临时副本上的迁移结果), 磁盘落成「v2 章 + 未迁移旧键」, 写完的 reload 当场撞废除校验、
> 下次启动也进不来。修复: `writer._prepare` 在盖章/校验前对提交树跑与加载侧同一的
> `migrate_config_schema`(写什么校验什么), loaders 侧迁移分派函数相应转公共。新增 writer
> 迁移回归测试 4 条(事故锚点 / 二次保存幂等 / v2+旧键拒写 / 预览同口径)。
> 数字取自修复完成实测(`commands run test.full`, 基线 origin/develop @ 5809bddd)。
> 基线时间: 2026-09-27 22:01
> 档案: memory-bank/activeContext/26-09-27-2022-hr-binding-tracker-mapping.md

- **测试增量**: tests/test_config_writer.py +4(LEGACY_V1 生产形态夹具, 与 test_hr_config
  的 test_legacy_equivalent_migration 生产锚点同构); 前基线 26-09-27-2022 的 +10 全保留。

TOTAL 1756 passed + 3 skipped / 92%(11731 语句 / 848 未覆盖 / 3940 分支 / 349 partial, test.full 18.9s)
对比前基线(26-09-27-2022): 1752 passed + 3 skipped / 91%(11730 语句 / 849 未覆盖) —— passed +4,
语句 +1, 未覆盖 -1, 覆盖率 91%→92%, 零回归。
覆盖率口径见 [baseline.md](../../testing/baseline.md)。
