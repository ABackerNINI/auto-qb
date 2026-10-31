# 基线 · 1811 passed + 3 skipped —— config 迁移物化重构轮(启动物化 + 版本号备份 + 写回版本闸门)

> 摘要: 计划 26-09-27-2252 落地: 推翻延迟物化 —— ①`writer.materialize_schema_migration`
> 启动物化单点(`QbManager.run()` 开头): 磁盘落后则「版本号备份 `<名>.v<m>.bak` → 迁移 →
> 校验复核 → 原子写回」, 幂等常态零 IO, dry-run 只探测; ②写回**版本闸门** `_reject_stale_version`
> (用户裁决): 提交树版本低于当前(含缺失)直接 400 指路刷新, 不做迁移修补 —— 第一版「迁移后
> 写回」补丁被取代移除; ③`migrate_config_schema` 改返回 desc、迁移日志降 DEBUG(启动日志黑洞
> 随物化 INFO 关闭)。测试改写 7 条(闸门 2 + 预览拦截 1 + 物化 4), 移除第一版用例 3 条,
> 夹具补版本章 4 处。重构档案并入 tasks/26-09-27-config-hr-binding-mapping.md(D9-D13)。
> 数字取自实施完成实测(`commands run test.full`; 提交前已按「先同步后提交」合并远端两笔
> (HR v2 落地 + 限速曲线预览图, 5809bdd→09d4109), 在合并基线上复跑, 基线 origin/develop @ 09d4109)。
> 基线时间: 2026-09-27 23:26 (23:5x 合并远端后刷新)
> 档案: memory-bank/tasks/26-09-27-config-hr-binding-mapping.md

- **测试增量**: 本轮净 +3 —— 移除第一版「迁移后写回」3 条(migrates_before_stamping /
  stale_resave_heals / preview_migrates), 新增闸门 2 + 预览拦截 1 + 物化 4, 保留 v2+旧键拒写 1;
  test_web 夹具 2 处 + web_env 2 处补 schema_version 章。合并远端(HR v2)另带来其增量。

TOTAL 1811 passed + 3 skipped / 91%(12355 语句 / 914 未覆盖 / 4198 分支 / 387 partial, test.full 15.8s)
对比前基线(26-09-27-2138): 1752 passed + 3 skipped / 91%(11730 语句 / 849 未覆盖) —— passed +59
(远端 HR v2 大批新增 + 本轮净 +3), 语句 +625, 未覆盖 +65, 覆盖率持平 91%, 零回归。
覆盖率口径见 [baseline.md](../../testing/baseline.md)。
