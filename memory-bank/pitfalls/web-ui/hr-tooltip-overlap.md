# 做种时长列(HR 弹窗)的原生 :title 与悬停弹窗叠出遮挡

> 摘要: 做种时长列已用 HR 在线核实悬停弹窗(@mouseenter/@mouseleave 触发)承载来源/安全档位结论; 若再在单元格挂原生 `:title="hrDurHint(m)"`, 浏览器原生 title 与自定义弹窗在同一 hover 上叠出, 原生 title 还常被弹窗 DOM 盖住, 表现为「被遮挡的提示」+「来源:未核实」等多余气泡。状态/站点/分类/标签等短文本列本就无需 :title, 挂上只增噪音。处置 = 做种时长列只保留 HR 弹窗触发, 摘掉原生 :title; 短文本列一律不挂 :title。
> 触发: 做种时长, HR 在线核实, hrDurHint, 来源:未核实, 被遮挡的 tooltip, 弹窗叠出, 列 tooltip, 状态列, 站点列, 分类列, 标签列, seeding_time, hrPopEnter, hrSrcClass

## 条目

- **触发**: 做种时长列同时挂了 HR 悬停弹窗(mouseenter 触发, 进度仪表式结论)与原生 `:title`(来自 hrDurHint, 拼「来源: 在线核实/本地兜底/未核实」+「已排除」)。两个提示在同一 hover 上竞争, 原生 title 因 z-index/DOM 顺序常被弹窗盖住, 用户看到的是残缺/被遮挡的提示 + 多出来的「来源:未核实」气泡。另外给状态/站点/分类/标签这类本来就短、不省略的列挂 :title, 纯属噪音。
- **判别**: ①做种时长列 hover 时出现两个提示(一个固定气泡、一个延迟原生 title), 或原生 title 被弹窗遮住只露一角; ②grep `:title="hrDurHint` 或 `:title="stateText` / `:title="mTags` / `:title="m.site"`(短文本列)即命中; ③已退役的同源死代码: hr.js 的 `HR_SRC_TITLES` / `HR_EXCLUDED_TITLE` / `hrDurHint` / `hrSrcText`(2026-09-29 清理)。
- **处置**: ①做种时长列只保留 `@mouseenter="hrPopEnter" / @mouseleave="hrPopLeave"`, 删 `:title="hrDurHint(m)"`; 来源/安全档位结论一律进 HR 弹窗(不再进原生 title), 来源档位由 `hrSrcClass` → CSS 底线编码(在线=整格 / 本地 / 未核实 三档); ②状态/站点/分类/标签列去掉 `:title`(种子页 torrents.html / 辅种组表 groups.html / 追剧成员行 shows.html / 未识别区同构单元格都要清); ③hr.js 里因此变死代码的常量与方法一并删, test_web.py 把钉旧行为的断言改成「应已退役 / 不得再挂原生 :title」的否定断言。
- **守阵**: test_web.py::test_frontend_hr_safety_wiring —— hr.js 不得再有 `HR_SRC_TITLES` / `HR_EXCLUDED_TITLE` / `hrDurHint`; 三套 UI 的 seeding_time 单元格不得再出现 `:title="hrDurHint(m)"`(grep 否定), 且 HR 弹窗触发 `@mouseenter="hrPopEnter"` 必须仍在; 行内文字 chip(`.hr-src`)零残留。
- **复发**: 0
