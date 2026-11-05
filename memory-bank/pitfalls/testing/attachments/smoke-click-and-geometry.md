# 浏览器冒烟 · 点击落点被吞与行高于视口(外迁)

> 摘要: `pitfalls/testing/smoke.md` 两条行点击落点坑的原文整体外迁(2026-11-05 压缩): 行内可交互后代吞掉点击、行高于视口时 scrollIntoView(center) 把落点推出视口。正文原样照搬, 标题降一级以避开坑档条目扫描。
> 触发: Ctrl+click, 修饰键点击, site-chip, 点击落点, elementFromPoint, scrollIntoView, 行高于视口, sticky-head, 3000 种子, member-row, ep-name

## 行内可交互后代会吞修饰键点击, 冒烟点行必须避开交互后代落点

- **触发**: 冒烟用例对行做 Ctrl+click 多选(或任何要点到"行本体"的动作), 落点用行几何中心(2026-10-01 实测, issue 26-09-30-0602 清偿)。
- **判别**: 行中部被行内可交互后代占据 —— 追剧集/辅种组行都有 `.site-chip`(`@click.stop="filterFromChip(...)"`, tpl/shows.html / tpl/groups.html), 点击落在芯片上时事件被 `.stop` 吞掉, 行 handler(selection.js `_toggleUnit`/`toggleGroupSel`)**根本不触发**, 症状是"修饰键点击不生效/选中 0 项", 极易误判成轮询重渲染竞态或真实 UI 缺陷。定案用仪器化探针: document **捕获级**记录 mousedown/mouseup/click 落点 + 覆写行 vm 方法看是否被调 + 行 DOM expando 查脱挂 —— 落点全在芯片、行 handler 未被调、节点未脱挂 ⇒ 是落点被吞, 不是竞态也不是产品缺陷。**间歇性**的来源: 芯片布局随前序冒烟步骤(状态文案/筛选态)漂移, 行几何中心有时被盖住有时不被 ⇒ 同一用例忽红忽绿。
- **处置**: 修饰键点击落点避开交互后代 —— `position: { x: 8, y: 8 }` 落**行左缘名称列**(`.g-name`/`.g-name-text` 无任何 `.stop` 后代); 右键不受影响(chip 无 `contextmenu.stop`, 事件冒泡到行)。修法已随 0602 清偿落码(旧冒烟脚本 commit `59725443`, 现由 `e2e/multiselect-shows.spec.mjs` 承载); 新写用例点行时照此选落点, 别默认几何中心安全。
- **不止 Ctrl+click: 普通点击与双击同样被吞, `force: true` 也救不了(2026-10-09 实测)**: 展开行用的
  普通 `click()`、开详情面板用的 `dblclick()` 落几何中心时一样打在 `.site-chip` 上 —— `force` 只跳过
  actionability 检查(可见/稳定/可点), **不改变落点坐标**, 事件照旧被 `.stop` 吞掉 ⇒ 表现为「行没展开 /
  后续 `.member-row` 找不到」, 极易误判成"该功能没实现"。第二处反直觉点: **集行**的名称格类名是
  `.ep-name`(不是 `.g-name`), 追剧页两层展开(剧→集→成员)各自的名称格不同名。
- **最省事的写法**: 直接点**名称格元素**而不是算坐标 —— `row.locator('.g-name').click({ force: true })`
  / `epRow.locator('.ep-name').click({ force: true })`; 成员行(`.member-row`)无名称列, 只能点它自身
  —— 但**几何中心与行左缘 8,8 不是一回事**(2026-10-19 实测, 见下条)。
- **成员行的第一格就是 `.m-site` 筛选格 —— clickRow 行左缘 8,8 必踩(2026-10-19 实测)**: 辅种页
  成员行是 `display:grid` 且**从行盒 0 起排**(不像组行有名称格占首列), 首格即 `tpl-aq-member-cells`
  的 `site` 列(`@click.stop="filterFromChip('site', ...)"`) ⇒ `clickRow` 默认落点 `{x:8,y:8}` 落在
  `.m-site` 上 ⇒ 事件被 `.stop` 吞、`onMemberClick` 不触发, 且 `filterFromChip` 把列表过滤成别的
  形态 ⇒ 症状是**点击后 `.member-row` 归零**(极易误判成"组被收起/功能没实现")。此前本节"成员行点
  它自身即可"的说法只对**几何中心**成立, 对 clickRow 的 8,8 是错的。修法 = `e2e/lib/gestures.mjs`
  `clickRow` 加 `opts.point`(相对行盒偏移, 默认 8,8 不变), 成员行调用方传**第二格**(`.m-state`,
  无交互后代)偏移, 且偏移从 DOM 现算(`el.children[1]`), 不硬编码列宽。用例:
  `e2e/shift-select-anchor.spec.mjs` 的 `memberPoint`。
- **复发**: 4 —— 后三次都是判据盲点复发: 「知道要点名称列, 但没意识到 force 不改落点 + 集行名称格
  叫 .ep-name」; 最后一次是**纪律本身的漏洞**——"成员行点自身即可"没区分几何中心与行左缘, 而 clickRow
  恰恰用后者(三条判据已在上文两条实测里)。

## 行高于视口时 scrollIntoView(center) 把落点推出视口: elementFromPoint 恒回 (null), 5 拍空转

- **触发**: e2e 的 `clickRow` 报 `落点验证 5 拍未过(行左缘 8,8 被拦截, 最后拦截者 (null))`, 且
  **只在大规模档必现**(300 种子全绿 / `E2E_TORRENTS=3000` 恒红), 双皮肤 × 2 条(追剧集行)。
- **判别**: `(null)` 与上一条「被 `sticky-head`/`html` 拦截」**不是一回事** —— 后者有拦截者元素名,
  前者是**落点在视口之外**(elementFromPoint 只在坐标落在视口内时才有元素可回)。真身: 大库下
  聚合行会被行内 chip 撑爆 —— 3000 种子实测整库塌成 **1 剧 × 24 集**, 每集 ~142 个版本 ⇒ 集行的
  `.g-sites` 格堆了 142 个 site-chip, **行高 1220px > 900px 视口**; 而 clickRow 的对冲一律
  `scrollIntoView({block:'center'})` ⇒ 行居中后**行顶落到 -160px** ⇒ 落点 `y = top+8 = -152`(负
  值) ⇒ 恒 null, 5 拍量到的都是同一个负坐标, 重排无效 ⇒ 确定性红(不是时序抖动)。
- **处置**(测试侧 arrange, 不碰产品): ①拦截面取**所有** `.sticky-head` 下沿的**最大值** —— 文档里
  不止一个(顶栏条 + 表头各一), 只取 `querySelector` 的头一个会**低估**拦截面, 落点被表头吃掉而
  5 拍都不自愈; ②行高 > 可用视口(`vh - guard - 16`)时改 `block:'start'`(行顶贴滚动口顶), 不居中;
  ③落点钳进「行盒 ∩ (视口 − 拦截面)」: `lo = max(top+8, guard+8)`、`hi = min(bottom-8, vh-8)`,
  `lo > hi` 即本拍作废交给下一拍重排。取证仪器: 元素几何探针(行高 / 容器滚动态 / elementFromPoint
  多落点), 一眼看出"行比视口还高" —— 别靠读代码推。
- **产品侧另案**: 一集 142 个版本 chip 把行撑到 1220px 属渲染与信息密度问题, 不在测试基建修复范围
  (issue 26-10-18-2226 里已备注, 未入池)。
- **复发**: 0
