# 3405 —— HR 实例注册表隔离与写路径剪枝(扩展「发现产生很多无关条目」修复)

> 摘要: 修「扩展立即发现把整批死条目当存活实例采纳、主实例指向死端口报 Failed to fetch」——
> 根因是**测试污染真实注册表**: `hr.runtime._build_discovery()` 把实例心跳登记进用户
> `%LOCALAPPDATA%/auto-qb-hr/instances.json`, 条目 id = `sha1(data_dir)[:12]` 而测试的 data_dir
> 是每例唯一的 `tmp_path` ⇒ 每个用例都算「一个全新实例」, 只增不减(跑一次 `test_hr_runtime.py`
> 净增 24 条, 现场累积 684 条 / 26 簇几乎每簇 24 条); 叠加两个设计缺口 —— `InstanceRegistry`
> 只读时过滤 TTL 而写时不剪(文件无界增长)、后端按文件序(最后心跳升序)返回(`instances[0]` 恒为
> 最旧的死实例)。修法两处: ①`tests/conftest.py` 会话级 autouse 夹具把 runtime 的
> `default_registry_path` 指向 tmp 目录; ②`InstanceRegistry.upsert` 顺手剪掉超 TTL 条目(与 `alive`
> 共用 `_entry_fresh` 判据)。新增 2 条守阵(路径隔离 + 写路径剪枝), 均已红验。
> 坑档: memory-bank/pitfalls/testing/hr-registry-pollution.md
> 基线时间: 2026-10-16 01:44

## TOTAL

```
TOTAL                                               17334    182   5842    158    99%
3405 passed, 4 skipped in 124.76s (0:02:04)
```

- 语句 17334 / 未覆盖 182; 分支 5842 / partial 158; 覆盖率 **99%**(`commands run test.full` 实测, Windows 侧)。
- 耗时区间口径见 testing/baseline.md(单次采样); 本次全量一次采样 124.76s。
- **独立取证**: 跑测试前后 `%LOCALAPPDATA%/auto-qb-hr/instances.json` 条数 **710 → 710**
  (修复前同规模两次运行净增 24 条); 全量跑完同样 710 → 710 ⇒ 隔离生效。
- Linux(WSL) 侧未重测 —— 本轮无平台分支新代码(纯逻辑 + 会话夹具), 存量平台守阵未动。
