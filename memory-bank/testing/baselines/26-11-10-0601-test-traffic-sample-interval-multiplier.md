# 5900 passed, 2 skipped —— 流量采样间隔倍数键 v6→v7 全量测试基线

> 摘要: 流量采样间隔倍数键(v6→v7) 全量测试基线: 5900 passed, 2 skipped (209.90s), 覆盖率 99% (26238 stmts / 48 miss)
> 基线时间: 2026-11-10 06:01

## 验收数字

```text
TOTAL                                                26238     48    9144     58    99%
5900 passed, 2 skipped in 209.90s (0:03:29)
```

(实测时点: 本分支 P1–P7 工作树, `commands run test.full` 2026-11-10 06:00; 较上一基线 26-11-10-0132 的 5883: +17 = 本计划新增用例(生效间隔单点 6 + 迁移链 v6→v7 节点 7)与改写面净增)

## 本改动面

- **配置模型与加载器**(src/auto_qb/config/models.py + loaders.py): `qb_traffic.sample_interval_multiplier` (int >= 1, 默认 1) 替代旧秒值键 `sample_interval`。
- **校验层与 schema**(src/auto_qb/config/validators.py + schema): 倍数 `int >= 1` 且有效秒数 `multiplier × main_tick <= 600`; 旧键不在白名单, 残留即 fail-fast。
- **升级链 v6→v7**(src/auto_qb/config/migrations.py + infra/versioning.py): 旧秒值按同一 config 树 `main_tick`(缺省 2.0) 换算为整数倍数并钳进 v7 硬校验, 逐键 note(精确还原/向上取整/贴上限钳制/main_tick>600 兜底 1)。
- **运行时单点**(src/auto_qb/core/traffic_sampler.py): 抽纯函数 `effective_sample_interval`, 采样器与 webui 栅格同调; 删失配取整 + 告警语义。
- **测试面**: tests/ 与 tests-real/ 旧键 kwarg 与 `schema_version: 6` 清零; 迁移链 v6→v7 节点用例 7 条(精确还原/钳制/取整/幂等/D9 不补写/不可解析/上限不可满足) + 生效间隔单点用例 6 条; 新增新键登记守卫; tests-real 基座 schema_version 同步 7; P7 修 `tests/test_relocate_config.py` 迁移幂等断言(已清洗树改按当前版本 v7 断言) + 清 `tests/test_traffic_sample_config.py` 死导入。
