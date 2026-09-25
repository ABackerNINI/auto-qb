# WEB UI 添加种子: 回执误报失败 + optional 选项不生效

> 摘要: 用户报"添加种子显示失败 + 桌面弹 WARNING, 但实际添加成功, 且「添加后开始」不生效"。三条根因全部实证: ①回执只认旧版文本 `"Ok."`, 而 qB 5.2.3(Web API 2.14.0 起)`/torrents/add` 已改回 JSON 元数据 ⇒ 判定恒假; ②停止位被"False 就不传"吞掉 ⇒ qB 回落会话默认; ③成功路径记 WARNING ⇒ 经通知联动直推桌面弹窗。同轮按用户要求把同类的「自动种子管理」一并修成恒显式。**已修复 + 已回写, 已入库 `434e019`**。
> 触发: 添加种子, 添加失败, 添加后开始, 自动种子管理, torrents/add, 添加回执, stopped, autoTMM, 桌面弹窗 WARNING
> 最后活动: 2026-09-24 20:36

## 状态

**已完成**(本 clone, 已随本次提交入库):

- 取证链: monkeypatch `QbittorrentSession.request` 实测真实返回类型与请求体;
  对 qB 源码(`addtorrentparams.h` / `sessionimpl.cpp` / `webui/api/torrentscontroller.cpp`)与自家 WebUI
  (`addtorrent.js` 恒传 `stopped` / `<select name="autoTMM">`)逐条对照。
- 修复: `webui/commands.py` 新增 `_add_outcome`(两形态都认, `pending_count>0` 算受理)
  + `is_stopped` / `use_auto_torrent_management` 恒显式下发 + 成功 INFO / 未受理才 WARNING。
- 守阵: `test_web.py::test_add_torrent_receipt_and_optional_flags` —— 四条断言**各自反向对照红验**
  (还原旧实现分别报 `'error'=='ok'` / `None is False` / WARNING 断言);
  替身 `FakeClient` 补 `is_stopped` 与 `is_stopped_raw`(区分"显式 False"与"没传")。
- 回写: `pitfalls/backend/qb-api.md`(响应形态 + optional 字段判据两条)· `pitfalls/testing/stubs-sim.md`
  (仿真保真度 + `make_manager` 清 root handlers 致 caplog 恒空)· `testing/baseline.md` +
  `baseline-history.md` · 专题档案 `tasks/26-09-15-webui-qb-replacement.md`(子任务 2.11)。

**实测**(提交时刻): 全量 **1232 passed + 1 skipped** / TOTAL 91%
(7782 语句 / 622 未覆盖 / 2648 分支) / sidefx 台账 2067 条 · 越界 0; `doc.caps` PASS。

**同步插曲**: 开工时与主线齐平, 提交前发现主线已前进 2 个提交(`9d7a3eb` / `2e2e2b5`)⇒ 按
「移出改动 → `merge --ff-only` → 施回改动」同步(重叠仅 3 个文件: 两个基线文档 + 生成物
`tasks/_index.md`; 已先 `git diff --output` 出补丁 + 另存 4 文件)。合流后 1232 = 主线 1231 + 本任务 1。
⚠ 合流带进来的两条 GBK 码页断言在本工具 shell 里**恒红**(注入 `PYTHONUTF8=1` 所致, 非缺陷)——
判据已记进 [../pitfalls/testing/patching.md](../pitfalls/testing/patching.md), 测真值用
`env -u PYTHONUTF8 -u PYTHONIOENCODING`。

## 待用户处置

1. **一处行为变化需知情**: 勾选框变权威后, "未勾自动种子管理 + 未填保存路径"的添加从
   "由 qB 全局模式决定"变成**确定性 Manual**(落 qB 默认保存路径)。若其实想要"默认走 qB 全局自动管理",
   正确改法是把前端勾选框默认改成勾选(`app.js` 的 `addTmm: true` + 两套 HTML 初始态), 而不是回到省略参数 —— 等用户拍板。
2. 真机复验: 用户实例跑在别的 clone 上, 需同步代码后再验一次(跨 clone 写操作按红线未动)。

## 单点指针

- 判据全文 → [../pitfalls/backend/qb-api.md](../pitfalls/backend/qb-api.md)(响应形态 / optional 字段两节)
- 测试替身与日志采集陷阱 → [../pitfalls/testing/stubs-sim.md](../pitfalls/testing/stubs-sim.md)
- 专题档案 → [../tasks/26-09-15-webui-qb-replacement.md](../tasks/26-09-15-webui-qb-replacement.md)
- 测试数字单点 → [../testing/baseline.md](../testing/baseline.md)
