# 基线 · 1752 passed + 3 skipped —— HR 站点绑定改映射制轮(26-09-27-1930 计划落地)

> 摘要: 计划 26-09-27-1930 实施: 站点绑定从「域名交集比对」整体改为**映射制**(web 域与
> announce 域两命名空间永不互相比对), 档案双域硬编码(web_domain/tracker_domain) +
> 默认映射零配置查表 + 显式键 `hr_check.sites.<id>.tracker` 兜底; 旧键
> `trackers.<名>.hr_check` 不设常驻兼容层, 走 schema 迁移链 **config v1→v2**(26-09-26-0506
> 机制首个 config 生产落地, 新增 config/migrations.py)。新增测试 +10, 改写若干;
> 生产 config.yml 全程零改动, 只读加载实测: BTSchool 旧键被迁移链自动改写且派生 URL 与旧值一致。
> 数字取自实施完成实测(`commands run test.full`, 基线 origin/develop @ 045ea27)。
> 基线时间: 2026-09-27 20:22
> 档案: memory-bank/activeContext/26-09-27-2022-hr-binding-tracker-mapping.md

- **测试增量**: tests/test_hr_config.py 域名交集类用例删除/改写为映射类, 新增迁移单测 5 条
  (搬移/off 删除/新位置获胜/定位不到保留/幂等无盖章) + 显式映射 2 条 + 歧义与唯一性各 1 条 +
  CarPT 回归锚 1 条; 钉死 config 版本号=1 的断言(test_config / test_config_writer /
  test_exporter)随 v2 抬号更新, test_config_schema 档案常量守卫改双域键。

TOTAL 1752 passed + 3 skipped / 91%(11730 语句 / 849 未覆盖 / 3940 分支 / 351 partial, test.full 18.9s)
对比前基线(26-09-27-1812): 1742 passed + 3 skipped / 91%(11691 语句) —— passed +10, 语句 +39,
覆盖率持平 91%, 零回归。
覆盖率口径见 [baseline.md](../../testing/baseline.md)。
