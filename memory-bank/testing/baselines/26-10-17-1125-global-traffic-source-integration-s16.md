# 3524 passed + 4 skipped(根) —— 全局流量来源集成 S16(auto-qb 探测-拉起-订阅编排: agent 联动单点 + 订阅方向改读发现指针)

> 摘要: 全局流量来源集成 S16(auto-qb 探测-拉起-订阅编排: agent 联动单点 + 订阅方向改读发现指针)
> 基线时间: 2026-10-17 11:25

## 验收数字

- 根 `test.full`(契约: 覆盖率门槛 98% + 包内 TMPDIR): **3524 passed + 4 skipped in 299.56s**; TOTAL **18158 255 6094 188 98%**(语句/未覆盖/分支/partial/覆盖率)。本切片由 `commands run kb.new baseline` 从实测输出誊写(裁定 A4)。
- 本轮知识库回写后守卫单跑 `test.one`(`tests/test_memory_bank.py` + `tests/test_docs_forms.py`): **77 passed**, 副作用台账越界 0 条(覆盖新基线切片格式、档案/切片结构与认领链守阵)。

## 本改动面

- `src/auto_qb/core/traffic_source/__init__.py`(新增) · `agent.py`(新增, **联动单点**) —— 发现指针定位(`_platform_data_home`/`pointer_dir`/`endpoint_path`) + `default_tool_dir()` + `ToolEndpoint`/`LaunchTarget` + `read_pointer`/`parse_pointer`(schema 闸, 不猜字段)/`discover`/`probe`(只认 200) + `resolve_launch_target`(`tool_exe` → `tool_dir` 启动器) + `launch_tool`(**模块级可注入单点**: detached, Windows `cmd.exe /c`+`DETACHED_PROCESS` / POSIX `/bin/sh` 新会话, 零参数) + `TrafficSourceAgent`(探活/缺席拉起/首引 120s·常态 10s 窗口/失败 30s 退避/`status()` 五态/同因不刷屏)
- `src/auto_qb/webui/tool_client.py` —— 订阅方向重接指针: `TrafficMonitorSubscriber` 增 `_agent`; `_pass()` 四步(确保可达 → 注册键未变则心跳 → 变则注销重注册); `_NOT_READY_POLL_S=3.0`; `_conf()` 改读 `traffic_source.global_traffic_monitor`; `_desired()` 首闸改判 `traffic_source.provider`; 注册/心跳/注销全走 `endpoint.base_url`/`token_path`, 注册键含工具基地址; **删 `tool_url`/`tool_token_path` 读路径**
- `tests/test_traffic_source_agent.py`(新增, agent 单测) · `tests/test_traffic_monitor_client.py`(改写: `sub_env` 写指针 + 注入假拉起动作, 用例改到指针/provider 契约; 头文档测试计划清单同步)
- `memory-bank/tasks/26-10-17-backend-global-traffic-source-integration.md`(R6 段 + 状态表 S16 Done + Updated) · `memory-bank/activeContext/26-10-17-0339-global-traffic-source-integration.md`(S16 已实施段 + 待办 + 摘要) · 本基线切片 —— 本专题滚动面
- 未动(属计划内后续步骤, 非遗漏): 过渡 stub `GlobalTrafficMonitorConfig` 与 `routes/traffic_monitor.py`(代理方向) → **S17**; `docs/configuration.md` 与根 `README.md` → **S18**; 真机验收 → S19
