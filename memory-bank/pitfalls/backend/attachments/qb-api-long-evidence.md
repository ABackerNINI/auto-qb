## torrents/add 回执: 三值受理态与聚合

- **处置**: 判定统一走 `webui/commands.py::_add_outcome`(两形态都认, 且把计数写进回执详情);
  别在别处再写一遍子串判定。⚠ 它返回的是**三值受理态**(`ok`/`partial`/`fail`, 2026-10-18
  由布尔扩为三值): `failure_count>0 ∧ success+pending>0` = `partial`(qB 整批里挑着拒) ——
  由 `_cmd_add_torrents` 跨文件/链接两次调用聚合成三态回执(部分受理 = `warn`, 前端据此
  **关窗**; 全拒才 `error` **留窗**)。把 partial 当布尔 False 压回 error, 「部分成功」就与
  「全部失败」混为一谈 —— 用户报障形态 = 部分种子添加失败(已存在)时添加窗口不消失
  (2026-10-18, 见 pitfalls/web-ui/add-partial-receipt.md)。


## torrentPeers 速度字段: 落袋适配与守阵

- **处置**: 在**落袋单点**做一次键名适配(2026-10-10 落地: `webui/static/shared/drawer.js::_drawerNormPeers`
  在 `_fetchDrawerPeers` 落袋处补 `dlspeed`/`upspeed`, peers 为 dict/数组双形态同归一), 全部消费点
  (经典表经 `drawerPeerRows`、变体 07/08/09 各自的 `peerList` 直读原始对端对象)**一处修好**;
  别在各消费点各写一遍。**配套**: 桩服务 / 合成数据必须用**真 qB 键名**(`dl_speed`/`up_speed`) ——
  本 bug 正是因 `scripts/ui_harness.py` 自造数据用了 `dlspeed`/`upspeed`, 冒烟「看得见速度」而真机恒 0,
  一路逃过全部 e2e(见 [../testing/stubs-sim.md](../../testing/stubs-sim.md) 同名复发条)。
- **守阵**: `tests/test_webui_static_dom_panel_drawer.py::test_drawer_peers_speed_keys_normalized`(适配单点在 +
  落袋走单点 + 桩键名与真 qB 同形); e2e `e2e/drawer-peers.spec.mjs`「上下行至少一格含数字」守卫。



## 库透传参数与 setShareLimits: 原始处置与守阵

- **处置**: 透传新参数一律 camelCase 直发 kwarg(两版库同 wire, 见 ops_mod `_skip_add_call` 的
  `shareLimitsMode=` 用法)并配请求体级守阵; 版本可选的 qB 新字段进 `_EXTENSION_FIELDS`
  (+ record slot, 缺省 None = 不发), 不动 `RE_ADD_FIELDS`。
- **setShareLimits 双必填参**(issue 26-11-01-2102, 2026-11-02 修): qB 5.0/Web API 2.10.4 起
  该端点还必填 `shareLimitAction`(库具名参缺省 None 被丢弃 → 请求体缺参恒 400), facade 与
  `shareLimitsMode` 同一手法缺省显式 `"Default"`(到限执行 qB 全局默认动作; 5.2 无该参数,
  忽略未知参无副作用); 守阵含 **facade 出口** wire 用例 —— 直调裸库传显式参的用例钉不住
  facade 漏参形态。
- **守阵**: `tests/test_qbapi_wire.py`(真库 + 真 requests 栈经 FakeQbServer 按线上原文断言三件事;
  含 facade(QbApi)出口双必填参守阵); `tests/test_torrents_*.py` 的 _SNAPSHOT_FIELDS↔record slots 同步守卫。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)

## 添加选项: 本项目下发口径与守阵

- **处置**: 本项目暴露的两个 optional 选项**恒显式下发** ——
  `kwargs["is_stopped"] = bool(paused)`、`kwargs["use_auto_torrent_management"] = bool(auto_tmm)`
  (且不能被"False 就不传"的过滤器吞掉, 它们要写在过滤器**之后**)。
  qB 自家 WebUI 同此口径: `addtorrent.js` 恒传 `stopped=true/false`,
  `autoTMM` 是 `<select name="autoTMM">`(Manual=false 默认 / Automatic=true)随表单恒提交。
  守阵: `tests/test_web_admin.py::test_add_torrent_receipt_and_optional_flags`(两个方向都钉)。

