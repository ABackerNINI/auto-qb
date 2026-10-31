# 部分受理被回执成 error: 按回执二态驱动 UI 行为必然错一头

> 摘要: 部分受理被回执成 error: 按回执二态驱动 UI 行为必然错一头
> 等级: L0
> 触发: 部分成功, 部分受理, 添加种子回执, 命令回执三态, warn 回执, 添加窗口不消失, 关窗判据, 批量添加
**Refs:** memory-bank/tasks/26-10-18-webui-add-partial-receipt.md

### qB 对重复种子是「整批里挑着拒」—— 部分受理被回执成 error, 按回执二态设计的 UI 行为必然错一头

- **触发**: 判 `torrents_add` 结果 / 写命令回执 / 任何**按回执 ok/error 二态驱动 UI 行为**(关窗 vs 留窗、放行 vs 拦截)的消费端。本仓实例: WEBUI 添加种子批量提交时一部分"已存在"被拒。
- **判别**: qB 的 `/torrents/add` 对重复种子**不是整批 409**, 而是 HTTP 200 + `failure_count>0`(其余成功) —— 部分成功是常态路径。旧口径 `_add_outcome` 只回布尔(无被拒才算受理), `_cmd_add_torrents` 把"部分受理"与"全拒"一起写成 `error` 回执; 前端 `submitAddTorrent` 只认 `r.ok` 关窗 ⇒ 用户报「部分种子添加失败(已存在)时添加窗口不消失」(2026-10-18): 种子明明加进去几个, 窗口赖着不动还报"添加种子失败"。反向的过度修复(把 error 也一起关窗)同样错 —— 全拒时那一份文件/链接原样没进 qB, 关窗用户就没法改完重提。
- **处置**: 回执侧出**三态**(与 reannounce 的 ok/error/warn 同词汇表, 不造第四态): `_add_outcome` 返回 `ok`/`partial`/`fail` 三值受理态, `_cmd_add_torrents` 跨文件/链接两次调用聚合 —— 加进去了 ∧ 无被拒 = `ok`; 加进去了 ∧ 有被拒 = `warn`(文案带"成功 N / 失败 M / 待定 K"计数); 全拒 = `error`。消费端按 `r.status` 分流而不是只判 `r.ok`: warn = 已受理但有保留 ⇒ 关窗 + warn toast(想补提再开窗); error = 原样没进 ⇒ 留窗等用户改。判据口诀: **"成功没有"与"有被拒的没有"是两个独立问题, 别压进同一个布尔**。
- **守阵**: 后端三态聚合 `tests/test_web_admin.py::test_add_torrent_receipt_and_optional_flags`(元数据形态 partial→warn)+ `tests/test_web_longtail.py::test_web_commands_add_torrents_receipt`(元数据单调用 + 旧文本混合两调用两种 partial 形态); 前端分流接线 `tests/test_webui_static_dom_panel.py::test_frontend_add_torrent_partial_receipt_wiring`(warn 分支在且关窗 / ok 保持关窗 / error 不得关窗, 已红验); 行为面 `e2e/add-partial-receipt.spec.mjs`(page.route 注入 warn/error 回执, 双皮肤 × 两方向, 已红验)。
- **复发**: 0 (2026-10-18 首记)
