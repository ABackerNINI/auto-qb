# 26-10-16-0144-hr-registry-isolation — 扩展「发现产生很多无关条目」修复(注册表路径隔离 + 写路径剪枝)

> 摘要: 用户实报 HR 扩展「立即发现」产生很多无关条目、且连不上正确后端(主实例 `Failed to fetch`)。分析定位到**测试污染真实注册表**: `hr.runtime._build_discovery()` 把实例心跳登记进 `%LOCALAPPDATA%/auto-qb-hr/instances.json`, 条目 id = `sha1(data_dir)[:12]` 而测试的 data_dir 是每例唯一的 `tmp_path` ⇒ 每个用例都算「一个全新实例」, 只增不减(跑一次 test_hr_runtime.py 净增 24 条; 现场累积 684 条, 26 簇几乎每簇 24 条); 旧形态只有 `test_hr_discovery` 一个文件做了路径隔离。叠加两个设计缺口: ①`InstanceRegistry` 只读时过滤 TTL、写时不剪 ⇒ 文件无界增长; ②后端按文件序(最后心跳升序)返回 ⇒ `instances[0]` 恒为最旧的死实例。修法 = 会话夹具隔离路径 + 写路径剪枝; 扩展侧排序与 TTL 两项**有意不做**(理由见下)。
> 最后活动: 2026-10-16 01:44
> 状态: Done

## 本轮落点(代码事实)

- `tests/conftest.py`: 新增会话级 autouse 夹具 `_isolated_hr_registry` —— 把 `auto_qb.hr.runtime` **命名空间里**的 `default_registry_path` 指向 tmp 目录(**只 patch runtime 的引用**, 不动 `hr.discovery.default_registry_path` 本身, 否则 `test_default_registry_path_platform_shape` 断言的真实平台形态会被改掉); 模块 docstring 由「三件事」扩为「四件事」+ 新增第 4 节(背景 / 处置 / 不拦什么)。
- `src/auto_qb/hr/discovery.py`: 抽出 `_entry_fresh`(读路径 `alive` 与写路径 `upsert` **共用**同一判据, 防「读时看不见、写时不剪」漂移); `InstanceRegistry.upsert` 新增 `ttl` 参数并顺手剪掉超龄条目 —— 写路径是唯一写入口, 有活实例心跳就一定有剪枝; 全死时文件留着也无害(没人读)。
- `tests/test_hr_discovery.py`: 新增 `test_registry_prunes_expired_on_upsert`(剪枝行为 + 边界与 `alive` 同判据, 不许差一)与 `test_hr_registry_path_is_isolated_from_real_file`(守阵: runtime 用的路径必须 ≠ 真实 app-data 路径); 头部 docstring「测试计划」第 1 层同步。
- **红验**(两条都真打到行为, 不是只改写法): 撤掉 `upsert` 的剪枝 ⇒ 剪枝用例红(`['old…','new…'] != ['new…']`); 撤掉夹具的 patch ⇒ 隔离守阵红, 实测报出真实路径 `C:\Users\...\instances.json`。
- **独立取证**: 跑测试前后注册表条数不变(修复前同规模两次运行净增 24 条)。全量数字见 `commands run kb.baseline` 最新切片。

## 有意不做的两项(及理由)

- **扩展侧排序**(把 `instances[0]` 换成本最新心跳的活实例): 后端按 `ts` 降序排会让 `instances[0]` 随 30s 心跳在多个实例间**来回翻** —— 把「陈旧但稳定」换成「不稳定」; 而路径隔离 + 剪枝之后列表里本就不该有死条目, 收益不抵抖动。
- **收紧 `INSTANCE_TTL_S`(120s)**: 同 data_dir 重启复用同一条目 id(`upsert` 覆盖), 所以**真实例不会**留下陈旧条目; 缩短 TTL 只影响「不同 data_dir 的实例死后 2 分钟」这一窄窗, 而计划 §C1 已定「发现失败有手动退路, 不需要更激进的 TTL」。

## 下一步 / 移交

- 待用户真机确认: 扩展「立即发现」列表应只剩真实例。存量 684 条死条目**已全部超 TTL**(对发现不可见), 下一个活实例心跳会由剪枝清掉 —— **无需手工清理**。
- 立档阈值判定: 本轮改动 = 1 个源文件 + 2 个测试文件、单会话指令 <5 轮 ⇒ **未命中阈值**, 按 memory-bank skill 只写本切片, 不建 tasks 档案。若后续要接扩展侧排序 / TTL 收紧, 那时再立档。

## 同族补记(2026-10-16 04:10, issue 26-10-16-0348 已修)

同一测试隔离族的**第二个面**——固定端口碰撞(上一个面是写文件): `test_hr_runtime.make_config` 曾沿用模型默认 `discovery_port=18788`(**固定**), 候选 18788/18789/18790 连号三个也是固定的 ⇒ `-n 8` 并行下多 worker + 用户真实实例(netstat 实测常驻占 18788)占满候选 ⇒ `HrDiscoveryServer.start()` 记 WARNING「全部被占」⇒ 污染「生命周期消息只记 INFO」断言(两条用例偶发判红, 曾误拦 ship.commit 闸门; 单跑/重跑皆绿所以一度被疑为 `_free_port` TOCTOU)。修法 = `make_config` 默认 `discovery_port=0`(本文件无一条测发现) + 守卫用例 `test_channel_runtime_leaves_discovery_unbound`; 连带 `test_hr_discovery.py::test_runtime_non_loopback_pairing_full_flow` 显式自选端口。教训与两个既有面的关系: **测试只要 start() 真实服务, 固定端口/共享路径/写用户数据三件事都别留模型默认**。报告: `memory-bank/issues/26-10-16-0348-test-hr-runtime-channel-port-race.html`(Done)。
