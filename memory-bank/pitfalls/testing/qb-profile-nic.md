# 换机抄 qB profile 残留原机网卡标识 ⇒ connection_status=disconnected 假红

> 摘要: 换机抄 qB profile 残留原机网卡标识 ⇒ connection_status=disconnected 假红
> 触发: disconnected, 网卡, ethernet_, profile, 换机, firewalled, real.up, connection_status
**Refs:** memory-bank/testing/real-machine.md

### 换机部署测试 qB(抄 profile)后实例双双 disconnected

- **触发**: 把测试 qB 的 `profile/` 目录从一台机器抄到另一台机器(双环境化、换机重建)后 `real.up` 拉起 —— 原机 prefs 里的 `current_network_interface`(形如 `ethernet_32769`)是**按机器**的网卡标识, 新机网卡对不上。
- **判别**: WebUI API 全通(token 正常、种子清单正常), 但 `GET /api/v2/transfer/info` 的 `connection_status == "disconnected"`; `prefs()["current_network_interface"]` 是一个非本机网卡的 `ethernet_*` 串。与「BT 监听端口被生产实例抢占」(real-machine §2.5.1)症状相同, 差别在本条用 `socket.bind` 探 BT 端口是**空闲**的 —— 占用不在端口, 在接口绑定。
- **处置**: `set_prefs(current_network_interface="")`(任意接口)后等几秒, `connection_status` 转 `connected`/`firewalled` 即愈(2026-11-01 环境2 双实例实测)。同时核对 `listen_port` 是否撞本机其它进程(§2.5.1 口径)。长期口径: 换机抄 profile 后必核这条, 已写进 real-machine §2.5.2。
- **守阵**: `real.guard` 第 1.5 层 `check_online` 已 fail-closed 拦 disconnected(本轮实测正是它拦住的, 无需新增机检)。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
