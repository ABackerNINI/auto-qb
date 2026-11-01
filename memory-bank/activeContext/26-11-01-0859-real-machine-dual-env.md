# real-machine-dual-env

> 摘要: 真机轨双环境化: 新增 tests-real/lib/env_registry.py 单点(环境1 D盘机 36595/36596 与环境2 C盘机 56589/56590, QBT_REAL_ENV 显式 > EXE 探测 > fail-closed), guard/instances/runner/rm00-rm10 全部端口字面量改派生 + docstring 角色化; 新增 real.env 命令; token 口径改不落盘(用户每轮会话给 QBT_TEST_加端口号环境变量); 环境2 首轮基建实测: real.up 拉起双实例 + guard 全绿(firewalled), 踩坑 profile 残留环境1 网卡标识 ethernet_32769 → 双实例 disconnected 假红, 已置空修复入坑档; BT 端口 27049/32719 等环境2 事实回填规程 §2.5.2; 基线切片 26-11-01-0858(数字见 kb.baseline; src/ 零改动零扰动)
> 最后活动: 2026-11-01 08:59
**Refs:**

**R0(2026-11-01 08:59):** 真机轨双环境化: 新增 tests-real/lib/env_registry.py 单点(环境1 D盘机 36595/36596 与环境2 C盘机 56589/56590, QBT_REAL_ENV 显式 > EXE 探测 > fail-closed), guard/instances/runner/rm00-rm10 全部端口字面量改派生 + docstring 角色化; 新增 real.env 命令; token 口径改不落盘(用户每轮会话给 QBT_TEST_加端口号环境变量); 环境2 首轮基建实测: real.up 拉起双实例 + guard 全绿(firewalled), 踩坑 profile 残留环境1 网卡标识 ethernet_32769 → 双实例 disconnected 假红, 已置空修复入坑档; BT 端口 27049/32719 等环境2 事实回填规程 §2.5.2; 基线切片 26-11-01-0858(数字见 kb.baseline; src/ 零改动零扰动)

**R1(2026-11-01 08:59):** 真机轨双环境化: 新增 tests-real/lib/env_registry.py 单点(环境1 D盘机 36595/36596 与环境2 C盘机 56589/56590, QBT_REAL_ENV 显式 > EXE 探测 > fail-closed), guard/instances/runner/rm00-rm10 全部端口字面量改派生 + docstring 角色化; 新增 real.env 命令; token 口径改不落盘(用户每轮会话给 QBT_TEST_加端口号环境变量); 环境2 首轮基建实测: real.up 拉起双实例 + guard 全绿(firewalled), 踩坑 profile 残留环境1 网卡标识 ethernet_32769 → 双实例 disconnected 假红, 已置空修复入坑档; BT 端口 27049/32719 等环境2 事实回填规程 §2.5.2; 基线切片 26-11-01-0858(数字见 kb.baseline; src/ 零改动零扰动)
