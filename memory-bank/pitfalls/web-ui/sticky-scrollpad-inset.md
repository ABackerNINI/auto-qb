# 滚动容器 padding 内缩 sticky 视矩形 (吸顶/吸底条贴边缝漏字)

> 摘要: sticky 的视矩形被**滚动容器自身的 padding 内缩** —— top:0 实际停在 padding-top 之下、bottom:0 实际停在 padding-bottom 之上, 中途滚动时数据行文字从这两条缝里漏出来; 行级 grid 表格的吸顶列头与吸底汇总条会同时中招(两档极端不露缝, 只有中途露)。修法 = 负 inset 抵消 padding(top:-14px / bottom:-20px), 或把 padding 移出滚动容器(结构性大改, 一般不值)。守阵量「吸顶条顶缘 == 滚动容器可视顶缘」的几何齐平。
> 触发: 吸顶, 吸底, sticky, 滚动容器 padding, drawer-body, 表头吸顶, 统计条吸底, 漏出文字, 行文字漏出, 顶部漏字, 底部漏字, 中途滚动, 未到顶, 没到底, dt11, 树表批量, drawer_tpl, 负 inset, sticky 缝隙

### 吸顶/吸底 sticky 条与滚动容器 padding 之间的缝

- **触发**: 给滚动容器(如 `.drawer-body { padding: 14px … 20px }`)里的元素写 `position:sticky; top:0`(或 `bottom:0`), 且中途滚动时有内容从它下面滚过。
- **判别**: 吸顶态量吸顶条 `getBoundingClientRect().top` 与滚动容器 rect top 之差 —— 实测**恒等于 padding-top**(14px), 吸底态之差恒等于 padding-bottom(20px); 缝隙带里 `elementFromPoint` 采到的是数据行元素(`.dt11-n` 名字格)。两档极端(scrollTop=0 与滚到底)不露缝, 只有**中途**露 —— 用户报障口径「上滑时未到顶导致顶部漏出文字 / 统计栏没到底也会在底部漏出文字」。注意半透明背景不背锅: 各皮肤 `--bg-card` 全是不透明色, 缝在条**外**不在条内。
- **处置**: 负 inset 抵消: `top:-14px` / `bottom:-20px` —— 数值 = 三皮肤 `.drawer-body` 的 padding-top/bottom(atlas|console: 14px 18px 20px / prism: 14px 16px 20px); dt11 变体既有 `margin:8px -16px -20px` 盖缝设计本就写死同一假设, **改皮肤 drawer-body padding 必须连负 inset 一起核**。吸底条负 inset 后贴到可视底缘, 与自身 margin-bottom:-20px 的「滚到底盖过 padding」口径自然衔接(滚到底 = 自然位 = 贴底, 量得 0.2px 子像素差属正常)。结构性替代方案(把 padding 移出滚动容器)牵动全部页签与三皮肤, 除非大重构否则不取。**吸底条自身 8px margin-top 静置间隙**吸底态会露出所滚过行的底部留白(几何上最多扫到约 0.5px 字降部), 实测目检不可辨, 不动。
- **守阵**: `e2e/drawer-content-dt11-sticky.spec.mjs` + `e2e/drawer-peers-sticky-flush.spec.mjs`(dt07/09) —— 分别桩掉 `/api/torrents/*/files` 与 `*/peers`(FakeClient 默认文件列表为空 / peer 每种子仅 1~7 个滚不起来, 必须喂数据才能滚), 中途滚动(+dt11 含滚到底)断言吸顶头顶缘 == `.drawer-body` 顶缘、吸底条底缘 == 底缘(±1px, 双皮肤); 两个守阵均已红验(还原 top:0/bottom:0 即红)。
- **同族清偿 (2026-10-10)**: dt07(`.dt07-head`)/dt09(`.dt09-head`) 同缝确认并同法修复(top:-14px), 探针实测中途滚动 gap 归零; 守阵为 `drawer-peers-sticky-flush.spec.mjs`(2 变体 × 2 皮肤, 红验 4/4 红)。dt10 的 `.dt10-right` 也是 sticky top:0 但它是**侧栏卡**(兄弟列, 无内容从其下滚过), 内缩只是停低 14px 的观感偏移、非漏字, 不修。
