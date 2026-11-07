# 代码风格长示例: 凭据脱敏

> 摘要: `conventions/code-style.md` 的凭据脱敏规格(越界即脱敏 / R1 / R6 铁律 / 守阵) —— 整段逐字外迁, 本节是该主题的现行权威。
> 触发: 凭据脱敏, tracker URL, sanitize_tracker_url, mask_tracker_url, mask_tracker_entry, passkey, 日志泄露

- **凭据脱敏 = 越界即脱敏** (2026-09-22, issue 26-09-21-1408; 2026-10-07 升级, plan 26-10-07-0055): 任何**可能内嵌凭据的 URL**(首当其冲是 tracker announce URL)**一旦越出进程内使用边界——API 响应体/前端 DOM/日志/落盘——必须先脱敏**; 进程内(内存比对/基线 key)不脱敏。两个越界面各有一个单点函数:
  - **日志**进日志前过 `utils.sanitize_tracker_url()`, 只留主地址 `scheme://host[:port]`, path/query/fragment 整段丢弃 —— 日志会落盘(含轮转备份)、可经 `/api/log` 读回, 且经通知联动(下条)直推系统通知, 泄露面远不止"读一次"。
  - **外发(响应体/前端 DOM)**过 `utils.mask_tracker_url()` / `mask_tracker_entry()`: 保留 `scheme://host` + path 端点名 + query 参数名(站点/端点仍可辨, 站点匹配/域名告警无感), 只把"值"换成确定性 hash16(不加盐, 两次逐字节一致, 删除改道靠它当场比对重取原文); mask 规格单点 R1–R9 在 `infra/utils.py` 与 plan 26-10-07-0055。(2026-11-08 起执行点前移: `torrents/record.py` 的 tracker 槽位在**入库单点** apply_delta 先掩码 —— 外发面拿到即 mask 值, 26-11-07-0536 批B; `/torrents/trackers` 端点的响应面掩码照旧。)
  - **铁律 R1**: 虚拟条目(`**`/`[DHT]`/`[PeX]`/`[LSD]`)原样透传, 不过 mask —— 它们不是 announce URL, 没有凭据。
  - **铁律 R6**: **不按参数名挑, query 全值 hash** —— 私站凭据参数名是任意的(passkey 只是最常见的一种, 还有 authkey/token/uid 等), 按名挑每漏一个名字就漏一个站; 旧日志口径因此整段丢弃, mask 口径因此全值 hash。
  - 守阵: `tests/test_web_seed_center.py` 守阵①~⑦钉住(① API 外发 / ② 删除改道 / ③ 编辑下线 / ④ 基线 key 原文 / ⑤ 静态 canary / ⑥ 详情响应外发 / ⑦ 行视图外发 —— ⑥⑦ 为 26-11-07-0536 批B 新增), 打回旧实现 CI 立刻红; 另有入库泄敏单点 `test_tracker_snapshot_masked_at_ingestion`(26-11-07-0536 批B); 红验方式见各守阵 docstring。
