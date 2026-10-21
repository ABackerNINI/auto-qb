# 3972 passed + 10 skipped —— 抽屉四 fetcher 收敛为唯一取数骨架(issue 26-10-20-2231)

> 摘要: 抽屉四 fetcher 收敛为唯一取数骨架(issue 26-10-20-2231)
> 基线时间: 2026-10-21 05:45
**Refs:** memory-bank/issues/26-10-20-2231-refactor-fe-drawer-fetcher-boilerplate-dup.html

## 验收数字

`commands run test.full`(本机 Windows, 仓库自带 TMPDIR 前缀), 连跑两次数字一致:

```text
TOTAL                                                20471     91   7012     93    99%
3972 passed, 10 skipped in 35.47s
```

与上一切片 `26-10-21-0426-dup-code-audit.md`(3968 passed / 20467 语句 / 93·93 缺口)相比:
**passed +4** —— 本轮新增 1 条守阵(`test_drawer_fetcher_skeleton_single_point`), 另 3 条是上一笔
提交(6ad07b6a「模板层三件套」)在该切片之后落入树的用例; 语句分母 +4 / 缺口 -2 **与本轮无因果**
(本轮 `src/` 只改一个前端 JS, 零 Python 语句增删), 近三条切片的分母本身在 20467–20470 间浮动,
记作切片口径浮动。覆盖率闸(`--cov-fail-under 99`)照过(99%)。

口径注记:

- 0 failed / 0 error; 10 skipped 与上一切片同集合。
- 本轮新增 1 条用例: `tests/test_webui_static_dom_panel.py::test_drawer_fetcher_skeleton_single_point`
  (静态单点 + 形态 + **37 项 node 行为电池**); 单跑 1 passed。
- **等价性对照**: 同一份 37 项电池对**收敛前**的四份实现(`git show HEAD:…drawer_store.js`)同样
  37/37 全过 —— 电池证明的是「行为不变」, 不是「形态变成这样」。
- 守阵同步四处(形态正则失配, 按「同步本守阵」纪律改在断言面, 语义只收紧不放松):
  `test_web_shortcuts.py::test_drawer_dock_keyboard_w2`(stale 判点 8+ → 骨架三路 + `_drawerDone` 恰 4)、
  `test_drawer_tpl_registry_wiring`(`_dtNotify` 四类 → 骨架按 src 通知 + 差异表四源齐全)、
  `test_drawer_tpl_a11y_and_fetch_error_states`(三失败标记 → 表声明 errKey + 骨架通用落/清)、
  `test_drawer_peers_speed_keys_normalized` / `test_drawer_list_switch_no_loading_flash_wiring`
  (peers 归一与 loading 门 → 表条目 + 骨架各钉一半)。
- 红验(守阵活性, **七类突变全部判红**, 均以精确反向编辑还原, 还原后 md5 逐字节比对原文件):
  ①薄壳里加第二行逻辑 ⇒ 红(「不再是单行薄壳」); ②列表源 `_dtNotify` 提到清 loading 之前 ⇒ 红;
  ③骨架 finally 漏 `_drawerDone` ⇒ 红(遮罩会挂死 + stale 判点数≠4); ④peers 空值形状改裸数组 ⇒ 红;
  ⑤peers 归一绕过 `_drawerNormPeers` ⇒ 红(电池报「peers 归一键名适配」);
  ⑥抹平通知时机分化(detail 也改成清门后通知)⇒ 红; ⑦四份次序回潮(peers 薄壳自带 `await this.api`)
  ⇒ 红(两条守阵同时红)。
- **浏览器层**: 抽屉域 11 份 e2e 全绿 —— `drawer-peers` / `drawer-switch-no-flash` / `drawer-merge`
  三份 20 passed, `drawer-tables` / `drawer-{trackers,peers,content}-variant-tables` /
  `drawer-dock-stability` / `dt-live-update` / `drawer-groups-shows` / `drawer-trackers-reannounce`
  八份 44 passed(双皮肤 prism + atlas, 共 64 passed)。端口注: 8137 被 clone1 残留桩、8337 被 clone2
  残留桩占用(跨仓库不动), 本轮用 `E2E_PORT=8437` 跑, 收尾兜底自动清理。

## 本改动面

| 文件 | 改动 |
|---|---|
| `src/auto_qb/webui/static/shared/drawer_store.js` | 新增顶层差异表 `_DT_FETCH`(4 源 × 端点/归一/目标状态键/空值形状 + loading 门/失败标记/通知时机)与唯一骨架 `_fetchDrawerSource(src, silent, seq)`; 四份 ~22 行 fetcher 退化为单行薄壳; 文件头「本层拥有」补骨架与表 |
| `tests/test_webui_static_dom_panel.py` | 新增 `_drawer_fetch_parts` 助手 + 守阵 `test_drawer_fetcher_skeleton_single_point`(含 `_NODE_DRAWER_FETCH_PROBE` 37 项电池) + 头部 docstring 测试计划补一行; 四处既有守阵改为钉骨架/差异表 |
| `tests/test_web_shortcuts.py` | stale 判点断言改为「骨架三路 + `_drawerDone` 一处」+ 四入口薄壳委派断言 |
| `memory-bank/issues/26-10-20-2231-refactor-fe-drawer-fetcher-boilerplate-dup.html` | 状态 Open → In Progress → Done; §04 改「修复与验证」, 状态日志下沉 §05; head `doc-refs` 并链本切片 |
| `memory-bank/issues/_index.md` · `memory-bank/issues/attachments/_archive.md` | 索引重建生成物(`commands run kb.index`) |
| `memory-bank/testing/baselines/26-10-21-0545-fe-drawer-fetcher-skeleton.md` | 本切片 |

净行数: `drawer_store.js` 359 → 423(**+64**, 全部来自差异表与两段头注); 其中的**次序逻辑**从四份
86 行降到骨架 48 行 + 4 行薄壳, `this._drawerStale(hash, seq)` 判点 **13 → 4**(骨架三路 + `_drawerDone`)。
未触及: 后端代码、`config.yml`、`drawer.js`、各变体模板、三皮肤 CSS。
上一轮的改动与数字见 `memory-bank/testing/baselines/26-10-21-0426-dup-code-audit.md`。
