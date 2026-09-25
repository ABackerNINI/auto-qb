# 1468 → 1476 (+8) —— 扩展侧两条实报报错修掉 + 守阵

> 摘要: origin pattern 缺 scheme 未捕获拒绝 + hr_check 段缺失端点从未启动 ⇒ 输入先归一化(normalize.js 一份共用) + 排障表; 时分不可考; 当日序位第 4 (09-24)
> 基线时间: 2026-09-24 00:00

- ↑ 收集数 **1468 → 1476**(**+8**; 2026-09-24 **扩展侧两条实报报错修掉 + 守阵**):
  用户装上 M2 交付的扩展后实报两条: ① `Invalid value for origin pattern pt.btschool.club:
  Missing scheme separator.` ② `TypeError: Failed to fetch`。根因: ①选项页把**原始输入**直喂
  `chrome.permissions.request`(它只吃带 scheme 的匹配模式, 报错还是**未捕获的 Promise 拒绝**);
  ② 后端 `config.yml` 里**根本没有 `hr_check` 段** ⇒ 端点从未启动(端点要三个开关同时满足:
  `hr_check.enabled` + 站点 `mode != off` + `channel.enabled`), 而浏览器对网络层失败只给一句
  `Failed to fetch` ⇒ 用户无从下手。修法: 输入**先归一化再交给浏览器 API**(裸域名→`https://host/*`;
  端点补 scheme / `localhost` 折 `127.0.0.1` / 协议固定 http), 非法输入**逐条**报错; 归一化抽成
  `normalize.js` **一份**(选项页 `<script>` + 后台 `importScripts` 共用, 防止两条路径漂移);
  选项页新增**自测端点连通**(把"连不上 / 401 / 403"分开)+ `unhandledrejection` 兜底;
  扩展 README 补「端点何时才会启动」三开关与排障表; `host_permissions` 补 localhost /[::1] 别名。
  新增 `tests/test_extension_proxy.py` **8 条**(manifest 作用域 / **真跑** normalize.js / 归一化只有一份 /
  与后端协议常量对照 / 调用顺序 / 不得留裸拒绝) —— ★红验过(去掉补 scheme 那行即当场变红);
  过程中真被 `node --check` 漏挡一次(删了本地副本、引用还在的 `ReferenceError`), 故守阵坚持"执行"而非"查语法"。
  全量 **1475 passed + 1 skipped** / TOTAL 91%(10217 / 763 / 3382 / 304) / sidefx 2357 / 越界 0。
