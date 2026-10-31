# 3165 —— WEBUI dt04 状态卡片栅格卡片填格(width:auto 根治长空隙)基线

> 摘要: 用户报「种子详情页状态卡栅格中真实 tracker 卡片与虚拟卡片之间有很长的空隙, 虚拟卡片后方也有空隙」—— 根因 = 引擎行容器 `.group-row` 被三皮肤经典表 CSS 继承 `width:fit-content`(与 `min-width:100%` 成对, 经典 flex 列容器里靠 min-width 兜底成整行宽); 04 变体把 `.group-table` 覆盖成双列 grid 并用 `min-width:0` 拆掉兜底后, `width:fit-content` 直接生效 —— grid 项宽度非 auto 时不参与默认 `justify-self:stretch`, 卡片收缩到内容宽(真浏览器实测: 1440x900 prism 实体卡 330px / 虚拟卡 378px, 格宽 695px), 两列卡片之间 ~700px 永久空洞且卡宽随内容漂移(违反 2026-10-09「宽度统一」拍板)。修法 = 卡片规则显式 `width:auto`(grid 项 + 默认 stretch 才填格), 不动皮肤经典规则(经典表依赖它横滚)。守阵双扣: 静态守阵 `test_drawer_tpl_trackers_card_uniform_height` 增第 4 节(钉 `.group-row` 行含 `width:auto`) + e2e dt04 用例增几何断言(每卡 = (表宽-gap)/2 ±1px 且全部同宽, fit-content 回潮即红)。新坑入 `pitfalls/web-ui/classic-row-fit-content-grid.md`。真浏览器复核(1440x900, prism/atlas × 3实体+3虚拟 / 6实体+4虚拟): 每卡 = 格宽(prism 686px / atlas 684px), 全部同宽, 虚拟卡与实体卡一致; e2e `drawer-trackers-variant-tables.spec.mjs` 6/6(双皮肤)。
> 基线时间: 2026-10-13 00:08

**Refs:** memory-bank/activeContext/26-10-06-0751-webui-detail-panel-design.md, memory-bank/pitfalls/web-ui/classic-row-fit-content-grid.md

## test.full 实测

- 分支: `develop`(HEAD `cd830692`, 工作树含本轮改动 + 回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **3165 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16718 语句 / 158 未覆盖 / 5688 分支 / 139 partial; 门槛 98% 达标)
- 与上基线的差值: `commands run kb.baseline -n 2` 现列(切片正文只写自己的 TOTAL, 不抄逐位对比)。
- 收集面未变: 静态守阵为原函数增补断言(无新测试函数), e2e 亦为原用例增补断言 ⇒ pytest 收集数不变。
- 耗时: 单次采样 57.60s(本轮三次采样区间 48.5-57.6s)。
- 增量明细(本轮真正新增): 源文件 `src/auto_qb/webui/static/shared/drawer_tpl/04-trackers-status-cards-tall.js`(卡片规则加 `width:auto` + 继承陷阱注释); 测试文件 `tests/test_webui_static_dom_panel.py`(守阵增第 4 节 + docstring/计划行同步); `e2e/drawer-trackers-variant-tables.spec.mjs`(dt04 几何断言 + 头注手势清单); 回写件: 坑档 `pitfalls/web-ui/classic-row-fit-content-grid.md`(新建)、`progress/implemented-webui.md` 新条目、切片 26-10-06-0751 追加; 本基线切片。
- 环境备注: `tests/test_traffic_limits.py` 在 xdist 并行下有既有抖动(本机单跑 13/13 过; 并行轮 failure 集逐轮不同), 与本轮改动无关(仅动静态守阵断言/CSS 字符串/e2e)。
