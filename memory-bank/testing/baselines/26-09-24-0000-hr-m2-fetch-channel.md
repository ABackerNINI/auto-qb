# 1375 → 1466 (+91) —— HR 在线核实 M2: 取数通道

> 摘要: 端点+队列+fetcher+worker+runtime+MV3 扩展; channel.extension_id / channel.request_timeout 两新键; 测出真缺陷「关停白等扩展回传」已修; 时分不可考; 当日序位第 2 (09-24)
> 基线时间: 2026-09-24 00:00
> 档案: 26-09-22-backend-partial-hr-verify

- ↑ 收集数 **1375 → 1466**(+91; 2026-09-24 **HR 在线核实 M2: 取数通道**):
  用户令「提交…然后继续 M2」。本轮落地计划的 **M2**(后端端点 + 取数线程 + 共享站点数据 + MV3 扩展):
  新增 `hr/channel.py`(协议 `HrTask`/`HrResult` + 密钥落 `<data_dir>/hr.token` + origin 白名单 +
  URL 白名单(SSRF)) / `hr/queue.py`(派发式队列 = 端点线程与取数线程的**唯一**交接面; 只接受
  「确实派发过且未作废」的回传, 且回传域名须与任务一致) / `hr/server.py`(stdlib
  `ThreadingHTTPServer`, 仅听回环, `allow_reuse_address=False`) / `hr/fetcher.py::ChannelFetcher`
  (把请求变任务并阻塞等回传) / `hr/worker.py`(取数线程按 `poll_interval` 自唤醒 + 只读视图
  **原子发布**(单元组赋值, 读方零等待) + 告警节流) / `hr/runtime.py`(`QbManager.hr` 门面:
  按配置启停、热重载重挂、自检快照); 扩展在 `extensions/hr-fetch-proxy/`(MV3 哑取数器 + 实例端点列表)。
  配置侧: `channel`/`shared_dir` 改 **L1** 并接上 `HrRuntime.apply`(监听身份变了才重绑端口);
  新增两个键 `channel.extension_id`(§6 要求「优先固定扩展 id」, 没有它无从固定)与
  `channel.request_timeout`(**必须有**: 否则扩展中途被杀会让持锁的取数线程永久挂住)。
  新增 6 个测试文件; 覆盖端点鉴权三道 + 真 HTTP 往返 + 端口冲突 fail-fast + 任务伪造注入 +
  视图「只在数据变化时抬 revision」+ 关停叫停 + 热重载重挂。
  **本轮测出一个真缺陷并修掉**: 取数线程正阻塞等扩展回传时, `stop()` 会白等到
  `request_timeout`(默认 180s)且**一直持着站点锁** ⇒ 改「先 `cancel_all` 叫醒等待方, 再 join」
  (`HrWorker.stop()` 内建, 调用方不可能忘); 这也是本轮 7 条用例各慢 10.5s 的根因。
  红验方式: 首跑 4 条真红(队列未派发即回传 / `path_of` 尾斜杠 / `silent_for` 伪时钟 / publish 空视图),
  逐条定位后全绿。
  全量 **1465 passed + 1 skipped** / TOTAL 91%(10217 语句 / 763 未覆盖 / 3382 分支 / 304 partial) /
  sidefx 台账 2353 / 越界 0(**合流后为 1467 passed + 1 skipped = 1468 collected**, 见上一条 ——
  本轮实测时还未并入那 +2)。⚠ 余下 **M3(判定联动四消费点) / M4(多站点)** 未落地 ——
  本档案「子任务状态表」逐项记状态。耗时升到 17.1–17.2s(真 socket + 线程用例, 见 [baseline.md](../baseline.md))。
