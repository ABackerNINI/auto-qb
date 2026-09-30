# 26-09-29-webui-chip-click-filter — WEBUI 挂件点击即筛选

**Status:** Done
**Added:** 2026-09-29
**Updated:** 2026-09-29 23:54
**Topics:** webui-chip-click-filter
**Summary:** 表格里点 站点/标签/分类/路径 挂件直接切换对应筛选值(filters.js::filterFromChip 单点复用 toggleFilterValue), 三皮肤 CSS 成对加 f-on/f-cell 交互态; 不挂原生 :title(遵 hr-tooltip-overlap 短文本列口径)。守阵暴露 atlas components.css 顶格 700 行, 规则挪 views.css; 并入远端 58d72e0a(tooltip 扫描同文件相邻 hunk, stash+pop 手工合流)后 test.full 1768 passed / 91%。

## 原始请求

> WEBUI添加功能: 点击站点/标签/分类/路径直接触发筛选, 即点击标签"R", 触发标签筛选器选中"R"

## 思考过程与决策

- **语义选择 = 切换(toggle), 不是置选(set)**: 与顶栏筛选弹层同一多选语义(再点一次取消), 复用现成 `toggleFilterValue`; 用户已有多选时点击追加, 行为可预期且可逆。
- **方法单点**: `filters.js` 新增 `filterFromChip(kind, value)`, kind→field 映射不另抄, 直接查 `filterDefs` computed(单一来源)。空值(未设分类/空路径)直接忽略 —— 筛「(空)」走弹层(那里有空值选项)。
- **stopPropagation 的连带责任**: 行点击是选中语义(组行普通点击=选中), 挂件必须 `@click.stop`; 但 `.stop` 会一并拦掉 lifecycle 里 window 级「点空白收浮层」—— 方法里镜像补 `menu.visible=false; filterMenu=""`。
- **覆盖面(三个视图 × 行层级)**: 组级(共同标签/共同分类、每成员站点 chip、组路径格) + 明细行(站点格 m-site/标签/分类) + 种子页(站点/分类/标签/路径) + 追剧(集行站点 chip、集明细同明细行口径)。Tracker 列虽复用 `.g-save-path` 类但**不是**路径筛选面, 不接。
- **CSS 三皮肤成对**: f-on(inset currentColor 环, 自动跟随状态色/HR 色变体) + f-cell(纯文本格: 明细站点列/路径列, hover 半透明叠加层)。console 皮肤 site-chip 有 `clip-path` 切角, 外环会被裁 ⇒ 一律用 inset 环。
- **守阵现形**: atlas components.css 原本**正好 700 行**(单 CSS 体量上限), 12 行新增直接红 —— 规则整体挪 atlas views.css 的 chip 交互区(该区本就承载 chip 过渡/悬停), components.css 回到 700。prism/console 无行 cap, 块留在原位。
- **不做的**: `+N` 折叠 chip 与 `±/多分类` 差异标记不接点击(筛选弹层锚点在顶栏, 从行内开没有现成定位路径, 收益不抵复杂度); 抽屉/对话框里的同族展示不在表格语义内。(`+N` 折叠已于 2026-09-30 随 [webui-tags-unfold](26-09-30-webui-tags-unfold.md) 整体移除, 该 chip 不复存在; `±` 标记仍在)

## 实现计划

1. `shared/filters.js`: 加 `filterFromChip(kind, value)`(收浮层 + 空值守卫 + filterDefs 查 field + toggleFilterValue)。
2. `shared/tpl/{groups,torrents,shows}.html`: 15 处挂件接 `@click.stop` + `f-on` 态(不挂提示 title —— 同期并入的远端 58d72e0a 立「短文本列一律不挂 :title」口径, 遵之)。
3. 三皮肤 CSS: `.f-cell`/`.f-on` 交互态(atlas→views.css, prism/console→views.css/components.css 原位)。
4. 验证: node --check + git diff 人工核对 + 标签配平 before/after 一致 + test.full 全绿。

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | filters.js 单点方法 | ✅ |
| 2 | groups.html 组级 4 处 + 明细 3 处 | ✅ |
| 3 | torrents.html 种子页 4 处 | ✅ |
| 4 | shows.html 集行 + 集明细 4 处 | ✅ |
| 5 | 三皮肤 CSS 成对 | ✅ |
| 6 | 守阵全绿 + 基线切片 | ✅ |

## 进度日志

- 2026-09-29 23:54: 开工 sync 至 1d711660; 读完 web-ui 坑点索引(frontend-split/columns 等)与 filters.js/tpl 结构后一次性落全部改动。首跑 test.full 红:`test_frontend_template_split_wiring` 判 atlas/css/components.css 712 行超 700 上限(原文件恰好 700)——把新增规则挪到 atlas/css/views.css chip 交互区后全绿。1760 passed + 2 skipped / 91%(test.full 32.3s)。契约回写 modules/webui-static-contract.md + README「批量操作利落」句 + 基线切片。
- 2026-09-30 00:09: 补任务档案 **Topics:** 行(test_doc_topics_complete 红→绿)后闸门复跑全绿(31.1s)。真浏览器冒烟时踩到端口坑: 首轮驱动误打 8127 —— 那是**运行中的生产实例**(桩绑定 EADDRINUSE 静默退出), 幸点击即筛为纯客户端状态、无任何写 API、无副作用; 桩改 8201 后受控重跑 14/14 + 三皮肤 3/3。冒烟工装留在 .openclaw/tmp/(不入仓库)。
- 2026-09-30 00:1x: 「提交」触发。sync 纯落后+树脏(远端 58d72e0a 三提交与本地 3 模板文件级重叠)→ stash → ff → stash pop: 三模板相邻 hunk 冲突, 手工合流取并集(远端 tooltip 清扫 + 本地挂件接线), 并按新落的 pitfalls/web-ui/hr-tooltip-overlap.md 口径**捕掉我加的挂件提示 title**(短文本列一律不挂 :title); 配平复验 OK、test.full 全绿(1768 passed / 12506 语句, 34.4s)、基线切片改记合并后数字。2316 切片的他处未提交改动不入本提交(ship.commit 传路径子集排除)。
