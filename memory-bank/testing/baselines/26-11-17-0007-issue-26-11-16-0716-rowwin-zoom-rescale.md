# 6437 —— 行窗口化 zoom 比例重标修复批全量基线(issue 26-11-16-0716)

> 摘要: 行窗口化 zoom 比例重标修复批全量基线(issue 26-11-16-0716, 终树 = 远端 011e1aeb + 本批, 含评审轮 3 携带x重标共存修复)
> 基线时间: 2026-11-17 00:07

## 验收数字

`commands run test.full` 实测(2026-11-17, Linux 本机; 终树, 1m58s):

```
TOTAL                                                28864    193  10304     80    99%
6437 passed, 23 skipped in 116.48s (0:01:56)
```

说明: 本切片数字**誊自终树**。合流前(2e2ffe1f + 本批)的中间树实测过 6253P/19S(覆盖 99%); rebase 合流远端 011e1aeb(携带 0553 换键携带机制 + HR 迁 aq-table 等新用例)后中间树 6441P/19S; 终树(评审轮 3 携带共存修复 + 电池 11→13 项)为上方最终数字, 是本批的权威基线。

e2e 侧(本批对象, 终树实测): `e2e/row-window-zoom.spec.mjs` **6 passed**(旧用例 3 + 本批新增「运行时 zoom 1→0.9」3 皮肤); `drawer-dock-stability` + `window-invalidation` 回归 **44 passed**(合流树)。红验(临时关 `_measureRowH` 重标块): `row-window-zoom` 新 3 用例在 scrollHeight 断言处红(prism 实测 before 21162 / after 20953, 偏差 1907px ≫ 130px 容差), 旧 3 用例仍绿(基准本来按 0.9 校准); 携带共存修复红验: 摘修复(配对直转记快照)后电池 12/13、恰「携带 x 重标」一项红。绿验: 全部通过。

## 本改动面

- `src/auto_qb/webui/static/shared/columns_grid.js`: 新增 `_rootZoomOf()` 缩放比值实测单点(body gBR 宽/offsetWidth, 量不到返回 null 不回落 1); `_winSigExtra` 改走该单点(令牌回落 "1.0000" 逐位不变); `_measureRowH` 开头加缩放重标块(比对 `_rowHZoom` 基线, 变了全表乘 zNew/zOld 原地平移 `_rowHs`+`_rowH`, 不删键不翻量齐态, `_rowHVer` bump); `_reprobeRenderedRowH` 加过渡拍让路守卫; 0553 换键携带块配对改「优先读 `_rowHs` 旧键现值(已被重标平移), 快照只兜底」(评审轮 3 共存修复, 注释补「其四」)。
- `src/auto_qb/webui/static/shared/lifecycle.js`: created() 初始化非响应式缓存 `_rowHZoom`。
- `tests/test_webui_static_dom_page_layout.py`: 新增 `test_frontend_rowh_zoom_rescale_guard`(剥注释静态守阵 5 面), 文件头测试计划同步。
- `tests/test_webui_static_r4_node_batteries.py`: 新增 `_NODE_ZOOM_RESCALE_PROBE` + `test_r4_rowh_zoom_rescale_follows_root_zoom`(node 电池 13 项, 含携带x重标共存/携带回落两断言; 桩补 `filteredGroups: []` 对接远端 0553 块), 文件头测试计划同步。
- `e2e/row-window-zoom.spec.mjs`: 新增「运行时 zoom 1→0.9: 未量行估高按比例重标」用例 ×3 皮肤(连续 10 采样判稳等待 + scrollHeight ≈ 0.9×before 判据 + 末行可达)。
- 文档回写: `memory-bank/issues/26-11-16-0716-*.html`(复验 + 修复后补充 + 状态 Done) / `memory-bank/pitfalls/web-ui/rowwin-stale-rowh-pad-jump.md`(缩放重标段 + 守阵清单) / `memory-bank/pitfalls/web-ui/css-zoom-coordinate-space.md`(已知权衡段改写: 洞已由比例重标另路补上, 「签名不含 zoom」警告保留)。
- 合流冲突: docstring 测试计划同锚点取并集(远端 HR 条目 + 本批 zoom 条目), 无删改。
