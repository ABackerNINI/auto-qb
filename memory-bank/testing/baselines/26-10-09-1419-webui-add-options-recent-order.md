# 2850 —— 添加种子三候选「最近使用」排序(含桩数据面 + e2e)

> 摘要: 「WEBUI 添加种子的保存路径/分类/标签按最近使用排序」第二段收尾基线 —— 本段按用户指派改了桩服务数据面(`FakeClient.categories` + `_inject_add_options` + 每对独立 `save_path` + 组键 `(save_path, ())`)并新增真浏览器 e2e; 同轮修掉首版的两个静默失效(路径口径不同径 / 常驻入口直读按视图裁剪的 `state.torrents`)。口径 = 由种子记录派生(非本机存储), 数据面走跨视图取数单点 `_addRecencyRows`。
> 基线时间: 2026-10-09 14:19

**Refs:** memory-bank/pitfalls/web-ui/contract-api.md,memory-bank/modules/webui-static-contract.md,memory-bank/testing/browser-env.md

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2850 passed + 4 skipped + 0 failed, 覆盖率 TOTAL 99%**(16567 语句 / 169 未覆盖 / 5716 分支 / 145 partial; 门槛 98% 达标)
- **耗时**: 单次采样 33.6s(命令墙时 33.6s; 单次数字无意义, 口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **与上一条同专题基线的差**: +1 用例, 来自**本次会话开工同步拉入的远端提交 `35a6ccdc`**(新增 `tests/test_web_shortcuts.py`), 与本专题改动无关。

## dev.e2e 实测

- 命令: `commands run dev.e2e`(桩服务 8137 自动起停, Windows, 单次采样)
- **实测**: **114 passed + 10 skipped + 0 failed**, 耗时 2.6m(命令墙时 ~157s)
- **新增 spec**: `e2e/add-options-recent-order.spec.mjs`(@fast, 双皮肤各 1 条) —— 开添加种子窗口, 断言分类 / 标签候选的**全序**与保存路径候选的**头部 3 条**等于按**桩同源公式现算**的最近使用序; 桩数据面未补前该窗口的三条下拉恒空(分类/标签)或被种子名污染(路径), 该渲染路径从无浏览器断言。
- **红验**: 把 `add_torrent.js::_addRecencyRows` 临时退回 `return this.torrents || []` ⇒ 双皮肤 2 条双双转红(分类候选序退回字母序 `Anime > Movies > TV`), 还原后双绿。
- **零回归**: 桩数据面改动(分类/标签注入、每对独立 save_path、组键归真)未打破既有 spec —— 全量 114 passed 与改动前同档。
- **扩档复核**: 同 spec 在 `E2E_TORRENTS=3000` 档单跑(桩 `种子=3000 组=200`)双皮肤 2 passed —— 期望序由**桩同源公式现算**, 换档自动跟着变(分类/标签/路径候选量随档变化, 断言无需改)。

## 说明

- **代码事实变更**: ①`shared/add_torrent.js` 新增 `_addOrderByRecent`/`_addNormPath`/`_addRecencyRows`/`_addRecencyMaps`, `loadAddOptions` 三候选改走排序单点; ②`scripts/ui_harness.py` 新增 `_inject_add_options` + 合成种子每对独立 `save_path` + 组键改 `(save_path, ())`; ③`tests/helpers.py` `FakeClient` 补 `categories` 字段(默认空, 向后兼容)。零后端端点改动 / 零新增持久化。
- **未验证面**: Linux (WSL) 侧未重测(仅 Windows 单侧采样, 与近期基线同口径)。
