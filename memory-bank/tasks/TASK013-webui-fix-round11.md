# TASK013 — WEB UI 第十一轮修复 (7 项 · 图标着色/明细排序/滚动条)

**Status:** In Progress
**Started:** 2026-09-17
**Owner:** 主线 (单会话连续实施)
**Plan doc:** (无 —— 7 项均为单点小修, 不产出计划文档)

## 原始请求

用户在 `想法.md` 的 "TODO → WEBUI" 下列出 7 条:

> * 导航栏追剧/添加种子图标无颜色
> * 状态栏空间剩余/限制速度图标无颜色
> * 移除状态栏"历史"文字, 仅保留图标
> * 辅种页明细表无法点击排序
> * 辅种表加保存路径, 明细表取消保存路径
> * 会出现两个横向滚动条
> * 分类/标签颜色暂无意义, 改为状态色

## 思考过程与决策

- **7 项天然分三类, 决定一次改完一次冒烟**: ①图标/文字层(3 项, 纯 CSS+模板属性, 双 UI 各一处) ②列模型层(2 项, `shared/app.js` 的 `GROUP_COLUMNS`/`DETAIL_COLUMNS` 是两套 UI 的唯一来源 ⇒ 改一处双生效) ③滚动条(1 项, 需定位真因) + 芯片配色(1 项, 语义裁决)。②③有交叉(新增列会改变溢出行为), 故先做列模型再处理滚动条。
- **"两个横向滚动条"必须先复现再改**(实测结论): 真因有两条, 且都会独立出现 ——
  1. **`.group-head` 脱离滚动容器** ⇒ 表头比 `.content` 宽时把整页撑宽, 出现"表格内一条 + 页面级一条"。实测: 把表头宽度写成 3000px, `documentElement.scrollWidth` 从 1872 → 3012(页面级滚动条实锤); 而表体内的行(在 `.group-table` 滚动容器内)不会撑页。
  2. **`.detail` 自带 `overflow-x: auto`** ⇒ 与外层 `.group-table` 各滚各的, 展开明细时出现第二条(注释一直声称"共用同一条滚动", 但属性没删)。
  第三条(本轮踩过弯路, **当日即修正**): 行"列没溢出却常驻横滚条"——
  先误判为"fr 列被逐列取整"并把行/表头改成**定宽 100%**; 用户随即反馈"**滚动后右边无背景条**"(定宽后行盒永远等于容器宽, 内容真溢出时溢出段没有底色/边框)。重测后找到真因: 表格层 `white-space: nowrap` + 单元格 `min-width: auto` ⇒ 自动最小宽 = **文本全长**, 13 列累加把行的 `min-content` 顶到容器之上 ⇒ `fit-content` 恒宽几像素。修法 = **行内单元格统一 `min-width: 0`**(文本排不下由各自 overflow/ellipsis 收尾), 行/表头仍用 `fit-content; min-width: 100%`。实测(星图/棱镜双 UI): 默认态 `scrollWidth == clientWidth`(无假滚动条, 轨道回到小数 260.88px/108.71px), 注入宽模板(如 `420px 300px …`)后行盒与表头**跟着内容长到 1917/2853px**(末格右边界 ≤ 行右边界 ⇒ 底色完整覆盖), 合法滚动条保留。
- **明细排序的落点选择**: 明细表与三个视图**正交**(三视图都有明细), 所以不复用 `sortKey`/`torrentSortKey`/`showSortKey`, 新增独立 `detailSortKey/detailSortDir` + `setSort(key, scope)` 的 `scope="detail"` 分支; 表头右键菜单的排序项也走同一分支(`m.page === "detail"`)。
  - **排序键位补齐**: 明细列模型里原本只有 4 列带 `sortable`(当年"表头暂未接排序"的遗留), 本轮按"可比字段都可排"补齐到 14 列(Hash 不可排 —— 无语义)。
  - **数组字段陷阱**: 标签是数组, 直接相减得 NaN; `sortedMembers` 先把数组 `join(",")` 再比。
- **分类/标签改状态色**: 原配色(分类固定蓝、普通标签固定灰)不带语义, 且蓝色分类 chip 与"下载中"状态色撞色。改为**跟随所在行的状态语义色**(与 `.site-chip` 同口径: 绿/蓝/红, paused/other 保持中性灰), **HR 标签用 `:not(.hr-pending):not(.hr-done)` 排除**, 保住 HR 的橙色/青色语义(这是唯一真带信息的 chip 配色)。
- **列迁移口径**(保存路径): 辅种表取**首位成员**值(与路径筛选器同源, `decoratedGroups.save_path` 早就有), 明细表删除该列 —— 组内成员路径本就一致(组 key 首元即规范化 save_path), 重复展示无信息量; 未归组的虚拟行也已带 `save_path`。列宽/显隐按**列 key** 存, 增删列不需要升 `COLS_STORE_KEY` 版本。

## 实现计划

1. `shared/app.js`: 列模型(辅种表 +保存路径 / 明细表 -保存路径 + 补 `sortable`) → 明细排序状态与 `sortedMembers` → `setSort/_sortKeys/_resetSort/headMenuSort` 加 scope。
2. `atlas/index.html` + `prism/index.html`: 导航与状态栏图标加语义类 / 去"历史"文字 / 辅种行加保存路径格 / 明细表头接排序(两处: 组明细 + 追剧集明细) / 明细行改 `sortedMembers` 并删保存路径格。
3. `atlas/style.css` + `prism/css/*.css`: `.content` 加 `overflow-x: clip`; 行与表头改 `width: 100%`; `.detail` 去 `overflow-x: auto`; 新增 `.ico-tv/.ico-add` 与 `.g-save-path` 省略规则; 状态栏三处图标改语义色; 标签/分类芯片状态色族。
4. 浏览器冒烟(双 UI): 图标色值、历史文字、保存路径列、明细排序三态、滚动条计数(全站 `scrollWidth > clientWidth` 的滚动容器数)、芯片色。

## 子任务状态表

| 项 | 问题 | 落地 | 状态 |
|---|---|---|---|
| 1 | 导航栏追剧/添加种子图标无颜色 | 模板加 `ico-tv`/`ico-add` + 两套 CSS 语义色(violet/green) | ✅ |
| 2 | 状态栏空间剩余/限制速度图标无颜色 | `.sb-item .ico-disk` → indigo; `.sb-limit .ico` → `--limit-hit`(不限速只弱化数值) | ✅ |
| 3 | 状态栏"历史"文字冗余 | 两 UI 去掉 `历史` 文本, 图标改 `--today-up`(原来继承 fg-dim 导致只剩灰点) | ✅ |
| 4 | 辅种页明细表无法点击排序 | `detailSortKey/detailSortDir` + `setSort(key,'detail')` + 14 列表头可排 + 三态循环 | ✅ |
| 5 | 辅种表加保存路径 / 明细表取消 | `GROUP_COLUMNS` 加列(组级首成员值)+ `DETAIL_COLUMNS` 删列 + 两 UI 模板同步 | ✅ |
| 6 | 出现两个横向滚动条 | ①`.content { overflow-x: clip }` ②`.detail` 去 `overflow-x: auto` ③行内单元格 `min-width: 0`(真因: nowrap + `min-width:auto` = 文本全长把行顶宽; 行/表头**保持 fit-content**) | ✅ |
| 7 | 分类/标签颜色无意义 | 芯片改跟随行状态语义色(HR 标签排除) | ✅ |

## 进度日志

- 2026-09-17: 会话开始, 读 `activeContext.md` + 仓库记忆 → 定位前端文件(atlas/prism/shared, 静态文件无构建链)。
- 2026-09-17: 用集成浏览器实测复现"两个横向滚动条"(表头撑页 3000px 实锤 + `.detail` 自带滚动条), 确定三项修复; 期间踩到"集成浏览器页面 hidden → rAF 不触发 → `page.evaluate` 的等待挂起/布局读数失真"两坑, 改用 `bringToFront()` + 不依赖 rAF 的等待。
- 2026-09-17: 代码改完(2 个 JS 模型点 + 2 个模板 + 3 个 CSS), `node --check app.js` 通过。
- 2026-09-17: 冒烟服务 `C:\Temp\aq-smoke\serve.py 38280` 双 UI 逐项实测: 图标色值(星图 rgb(167,139,250)/(52,211,153)、棱镜同族)、保存路径列在辅种表/不在明细表、明细排序三态(降→升→原序, 箭头随键移动)、全站滚动容器数 0、`documentElement` 无横滚、芯片 seeding 行取绿(`rgba(52,211,153,.16)`)/paused 行留中性灰。
- 2026-09-17: 全量测试 `uv run pytest tests -q` → **999 passed**(与基线一致, 前端改动由静态守阵 + 冒烟覆盖)。
- 2026-09-17 (同日追加): 用户反馈"滚动后右边无背景条"—— 定宽 100% 的副作用。重测定位真因(单元格自动最小尺寸), 改 `min-width: 0` 并回退定宽; 双 UI 复测默认态无假滚动条 + 注入宽模板后底色完整覆盖 + 滚动到最右截图确认; 全量测试重跑 999 passed; pitfalls/modules/progress/本档案同步更正。
