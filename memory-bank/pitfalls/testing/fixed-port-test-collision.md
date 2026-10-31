# 测试夹具留模型默认固定端口 —— 并行撞端口污染「无 WARNING」断言

> 摘要: 测试夹具不覆盖「固定端口 + 连号候选表」的服务端口(`HrChannelConfig.discovery_port` 模型默认 **18788**, 候选表 18788/18789/18790 也是写死的), `-n 8` 并行下多个 worker 同时绑、再叠加本机**真实实例常驻**(2026-10-16 netstat 实测 PID 19168 占着 18788)⇒ 三个候选全被占 ⇒ `HrDiscoveryServer.start()` 记一条 WARNING「候选端口全部被占」⇒ 污染「生命周期消息只记 INFO」类断言, 表现为**偶发判红**(取决于真实实例在不在 + worker 调度)。修法: 夹具显式 `discovery_port=0`(0 = 关闭发现, `_build_discovery` 直接返回 None), 没有候选表就没有碰撞面。
> 等级: L0
> 触发: 加 hr runtime 测试, 发现端口, discovery_port, 固定端口, 18788, 并行偶发红, WARNING 污染 INFO 断言, caplog 断言偶发, 端口被占, 真实实例占端口, xdist 端口冲突, make_config

### 测试夹具不得沿用模型默认的固定端口

- **触发**: 写 / 改用任何构造 `HrRuntime`(或其它带「固定端口 + 候选表」服务)的测试夹具; 排查「并行跑才偶发红、且红在日志级别断言上」。
- **判别**:
  - `make_config(tmp_path, channel=True)` 不传 `discovery_port` 时沿用模型默认 **18788** —— 名字叫「默认值」, 实际是**写死的固定端口**; 候选表 `discovery_candidates()` = base +0/+1/+2 连号三个, 同样固定(`hr/discovery.py:64`)。
  - 症状: 断言「start/stop 生命周期只记 INFO 不记 WARNING」的用例**偶发判红**, 失败信息却是
    `HR 发现端点候选端口 18788/18789/18790 全部被占 —— 发现不可用` —— 与端点(`channel.port`)
    半点关系没有, 极容易查错方向。
  - **现场放大因子是本机真实实例**: 用户真跑的实例(另一个 clone)常驻 18788 ⇒ 第一个候选
    **从来就不属于测试**; 剩下两个候选被 8 个并行 worker 抢, 占满是常态而非巧合。
  - **⚠ 入池时的猜测是错的, 记下来别再犯**: 曾猜是 `_free_port()` 的 TOCTOU(端点端口竞态)。
    **决定性反证**: 同样中招的 `test_start_stop_messages_are_info_not_warning` 用的是 `port=0`
    (内核分配), **全程不调 `_free_port()`** —— 它能吐 WARNING 的唯一路径就是发现端点。
    ⇒ 偶发并行失败先**枚举所有能产生该日志的路径**, 别顺着「最像竞态」的那个猜。
- **处置**:
  - `tests/test_hr_runtime.py` 的 `make_config` 加 `discovery_port=0` 默认参数 —— 该文件几十条
    用例**没有一条测发现服务**, 不该碰共享固定端口。新增守卫用例
    `test_channel_runtime_leaves_discovery_unbound` 钉住「channel 开着也不绑发现端口」, 防默认值回流。
  - `port=0` 对数据端点(`channel.port`)够用(内核分配); 但发现服务是「固定候选表顺序尝试」形态,
    换端口只是换个固定值去撞 —— **默认关掉**(`discovery_port=0`)比换端口更稳。
  - 依赖旧默认值的用例(`test_hr_discovery.py::test_runtime_non_loopback_pairing_full_flow`)
    显式自选端口(`_free_port()`), 不许沿用默认。
- **确定性复验**(不靠并行运气): 占光 18788/18789/18790 三个候选端口后**串跑**目标用例 ——
  修复前必红、修复后转绿。探针留在 gitignored 的 `tmp-analysis/`, 不入库。
- **同族**: [hr-registry-pollution.md](hr-registry-pollution.md)(HR 发现/运行时的另一半测试隔离面:
  注册表写用户真实文件); 并行面共性见 [parallel-run.md](parallel-run.md)。
