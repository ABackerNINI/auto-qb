# 26-10-20-webui-kbd-cursor-first-row — WEBUI 三主表首行键盘光标虚线贴住吸顶列头

**Status:** Done
**Added:** 2026-10-20
**Updated:** 2026-10-20
**Summary:** 三主表首行让出与行距同宽的 padding-top(prism 5 / atlas 6 / console 6), 首行键盘光标虚线上边缘不再贴住吸顶列头; e2e 三视图断言 + 红验, 全量全绿
**Topics:** webui-kbd-cursor-first-row
**Refs:** memory-bank/pitfalls/web-ui/kbd-cursor-first-row-gap.md

## 原始请求

1. 「修复：WEBUI 3个主表的第一个种子键盘锚点虚线上边缘被遮挡」(2026-10-19 23:34)。

## 思考过程与决策

- **三个主表** = 辅种(`viewMode=groups`) / 种子(`torrents`) / 追剧(`shows`), 三视图共用同一个列表容器
  `.content.torrents-dock > .group-table`; 光标视觉是共用层 `.kb-cursor`(`outline: 1px dashed`,
  `outline-offset: -1px`, 三皮肤同源)。
- **取证**(桩 300 种子 / 1440x900 / 三皮肤 × 三视图, `Home` 后量几何): 首行 `top` 与 `.group-head`
  `bottom` **恒等(间隙 0)**, 而第二行起有 5px(prism) / 6px(atlas、console) 的行距。开关光标的差分截图
  显示虚线四边笔画**都在**(上边约七成像素是 dash 图案), 缺的不是笔画而是**首行上边的呼吸位** ——
  虚线的 1px 按规范画在行盒最外 1px, 列头的 `border-bottom` 连同 `--shadow-1`(向下 1px / 2px 模糊)
  正压在这道边缘上, 行与行之间则有 gap 衬底。故判为「贴着列头 ⇒ 读成上边缘被削」, 而非元素遮挡。
- **拍板**: 不动行/列头几何, 只在主表容器顶端让出与行距同宽的空隙
  `.torrents-dock > .group-table { padding-top: <行距> }` —— 这样窗口化 `_rowPre`(按行高累加)与
  `.group-head` 的吸顶落位(`top: calc(--head-h - 1px)`)都不受影响; 抽屉里的 `.group-table` 挂在
  `.drawer` 下, 天然不命中该选择器。
- **取舍**: atlas `css/components.css` 已顶满 700 行体量 cap(首版写在那里被
  `test_frontend_template_split_wiring` 拦下), 规则改落 `css/views.css` —— 与既有「首列吸左固定」
  同因; console 的 components.css 尚有余量, 就地放。

## 实现计划

1. 三皮肤各一条首行让位规则(值 = 各自 `.group-table` 行距)。
2. `e2e/kbd-scroll-band.spec.mjs` 的 Home/End 用例内补三视图循环: Home 后首行顶与列头底至少 4px。
3. 红验: 三条 padding 归 0 → 三视图间隙归 0, 双皮肤断言转红, 还原复绿。
4. 全量 e2e + `test.full`, 数字记基线切片(`commands run kb.baseline`)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 三皮肤 `.torrents-dock > .group-table { padding-top }`(prism views 5px / atlas views 6px / console components 6px) | Done(2026-10-20) |
| 2 | `e2e/kbd-scroll-band.spec.mjs` 补三视图首行间隙断言(4px 下限, 双皮肤) | Done(2026-10-20) |
| 3 | 红验: padding 置 0 → 三视图间隙 0、双皮肤转红(已还原并复绿) | Done(2026-10-20) |
| 4 | 全量 e2e 与 `test.full`; 数字见 `commands run kb.baseline` 最新切片 | Done(2026-10-20) |

## 进度日志

### R0 · 立档 (2026-10-20)

首行让位落地并红验; 全量 e2e 与 `test.full` 已跑(数字见 kb.baseline)。附注: 首跑时
`test_api_traffic_qb_global_24h_reads_only_involved_day_files` 曾红一次 —— 该用例取真实时钟,
只在本地 00:00~00:10 的「10 分钟桶 / 窗尾跨午夜」缝上判 0 而非 null, 00:10 后复跑即绿, 与本轮
前端改动无关(纯 dat 读侧); 未在本轮范围内动, 是否入池待用户决定。

- 2026-10-20 00:05 三主表首行让位: .torrents-dock > .group-table 加 padding-top(prism 5/atlas 6/console 6), 光标虚线上边缘不再贴吸顶列头; e2e 补三视图首行间隙断言并红验, 全量 e2e 与 test.full 已跑
