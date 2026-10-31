# qB API 耗时的真机标定口径

> 摘要: 标定 qB API 耗时(如 tracker 取数预算)时, 三个坑会把数字或结论带偏: 路径式 `/torrents/{hash}/trackers` 不存在(404)、该实例对带 SID cookie 的请求回 404、每次新建连接会把 TCP 建连算进单次耗时(实测 27 倍差)。
> 等级: L0
> 触发: 真机标定, 耗时测量, tracker 取数预算, qB API, 404, 连接复用, keep-alive, P95
**Refs:** memory-bank/plans/26-10-19-2007-plan-webui-site-alerts.html

### 「裸 GET 能通、登录后全 404」与「每次新建连接」两件事会把标定数字带偏

- **触发**: 拿生产 qB 的连接参数跑一次性测量脚本(如 S0 标定 `torrents/trackers` 单次耗时), 决定预算/线程化取舍。
- **判别**: 三条症状, 逐条都能冒充"业务结论":
  ① `GET /api/v2/torrents/{hash}/trackers` 恒 **404** —— qB 的 trackers 端点是**查询参数式**
     `/api/v2/torrents/trackers?hash=<40位>`; 路径式不存在, 404 文本是 `Not Found`(会被误读成"该种子不存在")。
  ② 用 `requests.Session()` **登录成功后**带着 `QBT_SID_*` cookie 继续请求, 该实例(qB 5.2.3 + 本机白名单)
     对**后续所有** API 请求回 404; 而**裸 `requests.get`**(不带 cookie)恒 200。即"鉴权越完整越不通"。
  ③ 用 `requests.get` 每调一次新建连接: 均值 **10.76ms**; 同一批种子换成**单连接 keep-alive**
     (`http.client.HTTPConnection` 复用)后均值 **0.38ms** —— **27 倍差**, 足以把"20 条/轮"从
     "占 tick 14%" 误判成"占 0.5%"。
- **处置**: 标定脚本三件套 —— ① 端点用 `?hash=` 查询参数; ② 不登录、不存 cookie(本机白名单场景),
  或至少确认带 cookie 时端点仍 200; ③ 用 `http.client` **单连接**连发(生产 `qbittorrentapi` 客户端
  同样是 keep-alive, 新建连接的数字不代表它)。报数一律给 **均值 / P95 / 每轮预算总占用 / 占 tick 比例**,
  别只报均值。S0 实测样例见计划 R1 行。
- **复发**: 0
