# qB 字段口径混杂: alltime 对是全部流量而速率字段是 payload EMA

> 摘要: qB sync/maindata 三个流量字段口径不同源 —— `dl_info_speed/up_info_speed` = libtorrent payload 通道 5s EMA(1Hz 整数截断), `alltime_dl/up` = **recvBytes(全部 peer 流量: payload+协议)+IP overhead** 的持久单调累计(qB sessionimpl.cpp:6571-6572/6615+6625-6626), `dl_info_data/up_info_data` = payload 会话累计。把不同口径的字段当同一基使用(分类用一个、差分用另一个)会产生「字段读 0 但 totals 每 tick 都动」的持续形态, 任何「字段==0 即空闲」的单条件判据都会吞字节。
> 触发: dl_info_speed, alltime_dl, payload, 全部流量, 字段口径, 空闲判据, z 游程, 采样分类, 差分链, counter 口径, 二手调研笔记, 流量图翻面
> 判别: 到 qB/libtorrent 源码逐字核对该字段的赋值链(qB SessionStatus 字段 ← calcRate/session_stats metric ← libtorrent stat 通道), 认准 `recvBytes`(全部流量) vs `recvPayloadBytes`(payload) vs per-torrent `all_time_download`(payload-only, torrent.cpp:10909 累加 last_payload_downloaded)三个不同 counter; 实测形态: payload EMA 读 0 ⟺ ≥25-37s 无 payload(stat.cpp:15-21 的 floor(EMA*4/5) 衰减链), 而全部流量 totals 每 tick 都可能动(协议握手/keepalive/DHT 不进 payload 通道)。本轮实例: 2026-10-07 调研笔记写「底层累计源是 recvPayloadBytes 等」—— 一个「等」字把 `totalDownload = recvBytes + ipOverhead` 埋掉, 导致两轮分析先误判「totals 每 tick 动」为不物理、后又误收修复方案(见档案「思考过程与决策」两次翻转节)。
> 处置: 空闲/分类判据必须与速率差分基**同源**(totals 持平才判空闲, 不看速率字段); 跨 base 组合前先写一个最小探针(模拟「字段 0 + totals 动」)验证物理性, 再下「不物理」结论 —— 本轮两次分析翻转都源于跳过这一步。qB 流量图自身语义 = DOWN/UP 默认曲线画全部流量 calcRate 差分(payload 是默认关的可选叠层, speedwidget.cpp:134-139 + preferences.cpp:2147), 对齐它 = 每 tick 恒出样本、协议噪底常驻。
> 守阵: tests/test_traffic_sample_core.py 空闲判据双条件三用例(协议流量逐 tick r / 真静默仍 z / 断连重连重分类 r 封 n)+ tests/test_web_traffic_qb.py 端到端一致性钉面(GET 与 SSE 全量帧逐点同值, 修前整窗全 0)。
> 复发: 1(2026-11-21: 二手笔记「recvPayloadBytes 等」被当 payload 单一口径引用, 推出「字段 0 ⟺ totals 冻结」的错误物理性结论, 修复方案先错后返 —— 本坑条目即该轮立档)。
**Refs:** memory-bank/tasks/26-11-21-webui-traffic-idle-dual-condition.md
