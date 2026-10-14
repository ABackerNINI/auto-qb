# 3205 —— 抽屉页签轮询节拍: 5s 固定改主节拍 currentPollMs()(守阵两处正则同轮同步)

**Refs:** memory-bank/tasks/26-10-14-webui-drawer-cadence-main-beat.md

> 摘要: 用户报「种子详情面板用户页实时速度刷新率太低, 改成与 webui 主节拍一致, 即种子页的刷新间隔」—— 不是 bug 但节拍拍: 抽屉 peers/trackers 页签续拉走 `_startDrawerPoll` 固定 5000ms(P1-4 的 5s, 省 qB 直连成本), 种子行走 `currentPollMs()`(分档 1.5/2/3s)⇒ 实时速度滞后行数据三倍。修法 = setInterval 尾部改 `this.currentPollMs()`(主节拍单点, 吃方法不手抄档位); 服务端不动(peers ttl 1s 仍窗口外, trackers 2s 缓存吸收 1.5s 档白拉)。守阵两处里钉 `}, 5000);` 正则改钉新形态同轮(判据不放宽, 旧形态即时红 = 钉随改有牙)。验证 = pytest 全量 + e2e 全量(e2e 首轮一条 flaky 红属 delta-sync 时序竞态与本轮面 disjoint, 单 spec 重绿 + 全量重跑绿)。
> 基线时间: 2026-10-14 15:13
> 档案: memory-bank/tasks/26-10-14-webui-drawer-cadence-main-beat.md

## 验收数字

- test.full: 3205 passed + 4 skipped / TOTAL 16824 158 5724 140 99%(98.65%, 过 98% 闸门).
- 耗时: 110.40s(单次采样, 口径见 baseline.md).
- e2e 全量(本机 8137 起桩串行): 240 passed + 10 skipped(跳检菜单矩阵行随默认 env 跳过, 既定口径)/ 413.9s —— 首轮一条 flaky 红: delta-sync「lastRid 置空后下一轮为全量」8s 谓超时(踢 refresh 与轮询循环竞, 与本轮改动面 disjoint), 单 spec 重跑全绿 + 全量重跑全绿; 端口 8137 残留进程走 `dev.port-kill` 再重跑(playwright-teardown 已知本机形态)。
- 包内脚本测试(commands run test.pkg): 本轮未触 .commands/ 与 .agents/skills/commands/, 闸门 match 不命中, 未跑.
- Linux(WSL)侧未重测 —— 改动纯前端静态 JS 尾部 + 服务端注释一行, 无平台分支; 本条 Windows 侧数字为事实源.

## 本改动面

- 源(3 文件): drawer_store.js(`_startDrawerPoll` setInterval 尾部 5000 改 `this.currentPollMs()`, P1-4 注释改写两侧历史; 两处「5s 轮询」注释改「抽屉轮询」) · drawer.js(两处头部注释「5s 轮询」改「主节拍轮询」) · torrent_detail.py(peers 缓存注释「抽屉 5s 轮询本就在窗口外」改「抽屉主节拍轮询(>=1.5s)仍窗口外」).
- 测试(2 文件): test_webui_static_dom_panel.py / test_web_shortcuts.py —— 两处 setInterval 尾部正则钉改钉 `this.currentPollMs());` 形态 + 断文案「5s 轮询」改「主节拍轮询」; dom_panel 另一处 drawer_tpl 失败文案注释口径改.
- 红验: 守阵正则钉新形态 —— 旧形态(5000)对新钉即时失配红, 改形态绿即钉随改有牙(改完跑全绿确认钉命中非失配).
- 文档: 本切片 · 任务档案 tasks/26-10-14-webui-drawer-cadence-main-beat.md · activeContext 切片 26-10-14-1513 · 契约附件 webui-static-contract-details.md 两处改 · kb.index 重建.

## 已知偏差 / 移交

- setInterval 尾部吃 `currentPollMs()` 一次求值起轮: 档位跨分档(种子量过 1000/3000 断点)或失败退背变化时抽屉定时器不重求值(主轮走 setTimeout 链现求值每轮)—— 抽屉定时器重启(切页签/换目标/关面板)现求值新值, 稳态种子量跨档漂移属观察面板接受, 若日后要现求值改 setTimeout 链与主轮同口径.
- e2e 全量首轮 flaky(delta-sync)复见: 时序竞态型量具 8s 谓窗口, 与节拍改动无关 —— 若复频再问, 先分账两轮 kick 与轮询循环同页抢.
