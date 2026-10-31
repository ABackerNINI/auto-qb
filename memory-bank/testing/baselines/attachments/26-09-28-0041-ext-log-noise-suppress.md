# 基线 · 1813 passed + 3 skipped —— 扩展日志连不上降噪轮(故障期只打头尾)

> 摘要: 扩展(hr-fetch-proxy)连不上端点时每轮一条全量排查清单 ERROR + 状态栏同文复读, 日志环被灌满
> (用户 26-09-27 实报)。改「故障期只打头尾」: 首报全量 ERROR; 连败降 debug(默认级别不落盘), 每 30 轮
> 重提一次全量; 恢复补 INFO 并清计数(落 storage.local 防 SW 回收); 状态栏同文复读降 debug。
> 新增守阵 1 条(node VM 真跑 pollAll 五步), README ④区同步。
> 数字取自实施完成实测(`commands run test.full`, 合并远端 aef2462 后新基线上复跑)。
> 基线时间: 2026-09-28 00:41
> 档案: memory-bank/tasks/26-09-28-ext-log-noise-suppress.md

- **测试增量**: 本轮净 +1 —— `test_connection_failure_logs_head_tail_only`(五步场景 + 状态栏降级 +
  计数落盘断言)。远端 26-09-28-0014(sites-page-search)增量已并入。

TOTAL 1813 passed + 3 skipped / 91%(12355 语句 / 914 未覆盖 / 4198 分支 / 387 partial, test.full 16.3s)
对比前基线(26-09-28-0014): 1812 passed + 3 skipped / 91% —— passed +1(本轮新守阵), 覆盖率持平 91%, 零回归。
覆盖率口径见 [baseline.md](../../testing/baseline.md)。

## node 守阵披露(已于 2026-09-28 01:1x 处置完毕)

本机原本**无 node**, node VM 守阵在标准口径下静默跳过(假绿)。用便携 node v22.14.0 真跑
`tests/test_extension_proxy.py`: 新守阵过, 但暴露 **3 条既有守阵漂移**(与降噪改动无关, 09d4109
「配额双桶」把扩展硬上限提至 page 60/时·600/日、torrent 50/时·200/日, 守阵仍按旧值 10/50 断言):
`test_extension_quota_caps_and_refuses` / `test_extension_quota_windows_roll_over` /
`test_background_events_ring_dual_write`。

**处置(2026-09-28, 用户指令)**: ①node 装机 `C:\Program Files\nodejs` + 系统 PATH, 守阵回到「真绿」;
②三条守阵阈值改为**从 site-caps.js 现值动态取**(不再硬编码), 根治漂移。带 node test.full
**1813 passed + 3 skipped / 91% 零失败**。教训入坑 [pitfalls/testing/node-guards-silent-skip.md](../../pitfalls/testing/node-guards-silent-skip.md)。
