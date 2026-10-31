# 键盘光标首行虚线贴住吸顶列头: 行间有 gap 但首行与列头 0 间隙

> 摘要: 键盘光标首行虚线贴住吸顶列头: 行间有 gap 但首行与列头 0 间隙
> 等级: L0
> 触发: 光标虚线上边缘被遮挡, 第一个种子虚线, kb-cursor 上边被压, 首行贴着列头, 虚线缺一半, 键盘光标上边看不见, 三主表首行, torrents-dock group-table, padding-top
**Refs:** memory-bank/tasks/26-10-20-webui-kbd-cursor-first-row.md

### 首行光标虚线的上边缘被吸顶列头"吃掉": 行距只做在行与行之间

- **触发**: 键盘锚点(`.kb-cursor`)落到三主表(辅种/种子/追剧)的**第一行**时, 虚线上边缘看起来被吸顶列头压掉一半, 第二行起四边完整。改 `.group-table` 的 gap、列头 padding 或行高时最容易复发。
- **判别**: 量 `首行.getBoundingClientRect().top - .group-head.getBoundingClientRect().bottom` —— 为 0 即踩中。虚线是 `outline: 1px dashed; outline-offset: -1px`, 按规范画在 **border box 最外 1px**(行顶 0~1px), 而列头的 `border-bottom` + `--shadow-1`(向下 1px / 2px 模糊)正好落在这道边缘上; 行与行之间有 gap 衬底, 唯独首行上边没有。!**不能靠肉眼或开关光标的差分截图判定** —— 像素上虚线四边都在(差分实测上边 ~394 点、下边 411 点), 缺的是"呼吸位"不是笔画。
- **处置**: 主表容器顶端让出与行距等宽的空隙, 三皮肤各一条 `.torrents-dock > .group-table { padding-top: <行距>px }`(prism 5 / atlas 6 / console 6)。落地位置: prism `css/views.css`、atlas `css/views.css`(components.css 的 700 行 cap 已满, 与首列吸左条同因)、console `css/components.css`。**不要**改用行 `margin-top`: 行窗口化的 `_rowPre` 前缀和按行高累加, margin 会让未渲染行的落点偏; 也**不要**给 `.group-head` 加 margin(吸顶落位是 `top: calc(--head-h - 1px)`, 与 margin 无关但会改变自然位与吸顶位的差值)。抽屉内的 `.group-table` 挂在 `.drawer` 下, 天然不受影响。
- **守阵**: `e2e/kbd-scroll-band.spec.mjs` 的「Home / End …」用例内追加三视图循环: Home 后 `首行 top - 列头 bottom >= 4`(双皮肤)。红验: 把三条 padding 置 0 → 三视图间隙全归 0, 双皮肤双双转红。
- **复发**: 0
