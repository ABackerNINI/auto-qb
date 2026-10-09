# 2849 —— 添加种子三候选「最近使用」排序

> 摘要: 「WEBUI 添加种子的保存路径/分类/标签按最近使用排序」的收尾基线。口径 = **由种子记录派生**(非本机存储): 「最近使用」= 该值下种子 `added_on` 的最大值, 数据取 `state.torrents`(SEED_ITEM 全量平铺)。纯前端 1 文件: `add_torrent.js` 新增模块级纯函数 `_addOrderByRecent`/`_addNormPath` + 方法 `_addRecencyMaps`, `loadAddOptions` 三候选在落袋处统一过排序单点(未用过落末尾按字母序)。守阵新增 `test_frontend_add_options_recent_order`(node 电池真跑两纯函数 + 静态接线, 已红验)。
> 基线时间: 2026-10-09 14:00

**Refs:** memory-bank/pitfalls/web-ui/contract-api.md,memory-bank/modules/webui-static-contract.md

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2849 passed + 4 skipped + 0 failed, 覆盖率 TOTAL 99%**(16567 语句 / 169 未覆盖 / 5716 分支 / 145 partial; 门槛 98% 达标)
- **耗时**: 单次采样 33.5s(命令墙时 33.5s; 单次数字无意义, 口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **新增用例**: 静态守阵 **1 个新测试函数** —— `tests/test_webui_static_dom_panel.py::test_frontend_add_options_recent_order`(node 电池 12 项真跑 `_addOrderByRecent`/`_addNormPath` + 静态钉三候选接线与时间表单点; 同文件头部「## 测试计划」同步清单)

## 说明

- **代码事实变更**: 有 —— `shared/add_torrent.js` 新增模块级 `_addOrderByRecent`(最近使用降序 → 未用过按字母序, `slice()` 不改入参)与 `_addNormPath`(与后端 `infra/utils.path_normalize` 同口径), 方法 `_addRecencyMaps`(遍历 `state.torrents` 现算三时间表), `loadAddOptions` 三候选改走排序单点。零后端改动 / 零新请求 / 零新增持久化。
- **红验**: 在副本上把 `_addOrderByRecent` 的比较方向变异(`tb - ta` → `ta - tb`)跑同一 node 电池 → 12 项中 4 项转红(降序 / 未用过落末尾 / 部分命中 / 大时间戳), 还原后全绿。
- **未验证面**: ①**e2e 轨未加断言** —— 桩服 `FakeClient.torrents_categories()` 恒回 `{}`(harness 合成种子的分类字段不透传), 添加窗口的分类候选在桩下恒空, 加排序 e2e 只会得「空候选」假绿; 未动桩(改动面 / 范围守恒)。②Linux (WSL) 侧未重测(仅 Windows 单侧采样, 与近期基线同口径)。
