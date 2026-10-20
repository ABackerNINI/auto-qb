# 首列吸左固定(冻结列)在本仓表格上的九处非显然约束

> 摘要: 给 `.group-row` 加「首列 `position: sticky; left: 0`」时, 八件事不显然 —— ①**表头 `.group-head` 在滚动容器之外**(纵向 sticky 的前提), 首格拿不到 sticky 锚, 必须用反向 `translateX` 抵消, 且要减掉表头 `padding-left`(三皮肤均 14px), 否则比行首格恒右偏 14px; ②sticky 首格必须**不透明**才挡得住滑过的兄弟列, 而行的状态底(下沉/选中)是 rgba 令牌 —— 直接取令牌会**双重上色**(atlas 选中态实测逐通道差 17/18/33, 超可辨阈 20), 须用「同色 `linear-gradient` 叠不透明 `--bg-row`」做合成(差 ≤8); ③行的左侧色条 `.group-row.selected::before` 挂在**行**上, 横滚后随行滚出, 且**不能**顺手改成 sticky(行是 grid 容器, 绝对定位伪元素一变 sticky 就进流成为网格项, 破坏行布局); ④**吸左边界要有视觉提示** —— 横滚时滑入首格下方的列会留一段未盖满的尾字紧贴首格右缘, 无边界线索时被读成渲染 bug(2026-10-11 用户报「状态列被名称列盖住」), 须在横滚非零时画右缘**发丝线**; ④b**这条提示别用带负 `spread` 的 `box-shadow` 落影** —— 落影可见度是**首格高度的函数**(常态行首格 22px 时被内缩成 2px 近乎不可见, 高行 46px+ 才完整显形), 逐行深浅差 7 倍, 只在"刚好被撑高的那几行"冒黑块(2026-10-12 用户报「名称列后随机出现阴影」, 已删落影); ⑤**首格必须 `align-self: stretch`** —— 行是 `align-items: center`, 网格项默认不拉伸, 首格只有单行内容高, 站点/标签等多 chip 格换行把行撑高时(小窗常态)滑入的 chip 从首格上下两段漏出(2026-10-11 用户复报「小窗时站点的徽标不会被名称列挡住」); ⑥**首格底色规则是「主列表行语言」, 会被复用 `.group-row` 的抽屉面带进去** —— 抽屉各引擎面行板语言各不相同(族面 `--tbl-face-bg`→`--bg` / 04 卡 `--bg-card` / 05·10 透明 / 08 引擎 `--bg-row`), 首格一律 `--bg-row` 就行内一条异色竖带(ocean 主题 Δ 16/255), 须**按面重锚**, 半透明 tint(err/bad/is-chk/sel)合成在**该面的承光底**上(抽屉是 `--bg-card`, 不是主表的 `--bg-row`); ⑦**search-hit 行底是方向渐层**(`90deg accent-soft→transparent 46%` over `--bg-row`), 首格镜像必须**同款渐层** —— 只给平铺基色会**丢整条渐层**(实测首格 `backgroundImage=none`, 追剧表命中行名称列读作异色竖带); ⑧**变体家族是「外层 `.dtNN-wrap` 外壳 + 内层 `.dtNN-list` 行容器」两层, 行必须活在 `.dtNN-list` 里** —— 变体 CSS 前缀以 `.dtNN-list .group-row` 为作用域, 05 修前只有单层 `dt05-wrap`、行直接挂下面 ⇒ 前缀不匹配, 六条 `.group-row` 规则全程空转, 行一直带主表卡底, 肉眼只看到「必现列和别的列不一样」(2026-10-14 用户报障, 逐面量计算样式才发现 `inList=false`); ⚠ 修它别把外层直接改名(会打破 e2e 通用助手 `.dt${variantId}-wrap` 与家族约定), 要补内层 list。 ⑨ 首格只镜像静态色值、不镜像行板过渡 ⇒ 悬停/移出 160ms 内闪一条硬边竖带(补同源 background-color 过渡)。 ⑩**半透明状态底必须「叠加」在行底上, 不能用 `background` 简写「替换」行底** —— 行板一旦把底换掉, 承光层就变成页底 `--bg`, 而首格仍按 `--bg-row` 合成 ⇒ 选中/半选行名称列整列一条异色竖带(实测 Δ9/255 atlas、5/255 prism, 三主表全中, 未选中行 Δ0; 展开行的 `--bg-sunken` 同族 Δ5/2, 同轮一并收)。
> 触发: 首列吸左, 名称列后阴影, 随机出现阴影, 黑块, box-shadow spread 负值, 落影随行高变, 冻结列, frozen column, sticky 首格, 横向滚动, 表头横向同步, transform 桥接, 首格不透明, 半透明状态底, 双重上色, 左侧色条消失, 过渡中间值, 皮肤 CSS 700 行上限, 残根, 尾字粘连, 状态列被盖住, 吸左边界, is-hscrolled, 边界落影, 徽标漏出, chip 换行, align-items center, align-self stretch, 首格高度, 必现列背景不一致, 异色竖带, 按面重锚, 承光底, dt05-list, 行容器, 外壳类名空转, search-hit 渐层丢失, dtNN-wrap, 动态拼接选择器, 必显列悬停闪竖带, 滑过闪一下又恢复一致, 悬停时首格与其它列不同色, 首格无过渡, transition 不同源, 行板 160ms 首格瞬切, 过渡窗口逐帧采样, 选中行必显列异色竖带, 选中的行名称列与其它列不同色, 半透明状态底替换行底, background 简写换掉行底, 行板承光层变页底, 行底丢失, 合成基准分家

**Refs:** memory-bank/tasks/26-10-06-webui-frozen-first-column.md,memory-bank/tasks/26-10-11-webui-frozen-col-boundary.md,memory-bank/reports/26-10-14-0136-report-webui-detail-table-rebuild-review.html

### 首列吸左固定(冻结列)的九处非显然约束

- **触发**: 给行宽 `fit-content` > 容器的这些表(辅种 / 种子 / 追剧)加「首列常驻滚动容器左缘」。
- **判别**: 一行 `position: sticky` 完不了事 —— 表头、底色、左色条三处各有独立成因(见处置);
  另有一条量测陷阱: 点击后立刻读 `backgroundColor` 会拿到**过渡中间值**。
- **处置**:
  - **① 表头不在滚动容器里, 首格只能用反向位移**: `.group-head` 为做纵向 sticky 被移出 `.group-table`,
    横向靠 `sync*HeadScroll` 写 `transform: translateX(-scrollLeft)` 桥接 ⇒ 它**没有滚动祖先**,
    `position: sticky` 对它无效。首格改 `transform: translateX(max(0px, calc(var(--head-pin-x, 0px) - 14px)))`,
    位移量由三个 `sync*HeadScroll` 写进 `--head-pin-x`。**减 14px 是必须的** —— 表头 `padding: 7px 14px`,
    不减的话表头首格恒比行首格右偏 14px; 行内首格用原生 sticky, 语义是 `max(0, 自然位 - scrollLeft)`,
    两者同形才对得上(实测: 横滚后两格 `left` 同为容器左缘)。
  - **② 首格必须不透明, 半透明状态底要自己做合成**: 兄弟列从首格下面滑过, 半透明底挡不住。
    基础 / 悬浮态行底是不透明 hex, 直接取即可; 但 `.expanded`(`--bg-sunken`)/`.selected`/`.partial`
    (`--sel-bg`)是 **rgba** —— 把令牌直接给首格会叠在行底之上**双重上色**: atlas 选中态实测
    首格 `#333a61` vs 行 `#232840`(差 17/18/33 > 20, 肉眼可辨)。修法 =
    `linear-gradient(<tint>, <tint>), var(--bg-row)`(同色渐变当纯色层 + 一层不透明基色)
    ⇒ 首格 = tint over `--bg-row`、行 = tint over 页底 `--bg`, 实测差 ≤8。
  - **③ 左侧色条不跟着吸, 且不能顺手改 sticky**: `.group-row.selected::before` 挂在**行**上
    (`left: 0` = 滚动内容左缘), 横滚后随行滚出视野 ⇒ 选中行横滚时只剩底色、丢色条(已知残留)。
    **别把它改成 `position: sticky`** —— `.group-row` 是 grid 容器, 绝对定位的伪元素一旦变 sticky
    就**进流成为网格项**被自动摆进单元格, 直接破坏行布局。要保住它得换承载物(如首格 `box-shadow: inset`),
    但那样未横滚时会与行上那条并出双线。
  - **④ 吸左边界要有视觉提示, 否则滑入列的残根被读成渲染 bug**: 兄弟列滑进首格下方是**逐步**的
    —— 未盖满的尾字("做种"的"种")会紧贴首格右缘露出, 与名称省略号之间没有任何分隔,
    读成"名称后面多了个坏字"(2026-10-11 用户报「向右滚动时状态列被名称列盖住」)。
    盖住本身是冻结列的正确行为, 缺的是**边界线索**: CSS 感知不了 scrollLeft, 由三个
    `sync*HeadScroll` 在横滚非零时给 `.group-table` 与吸顶表头打 `.is-hscrolled`(回 0 摘标),
    CSS 据此给吸左首格(行 + 表头**成对**, 漏表头 = 列名残根仍裸露)画右缘**发丝线**
    (`inset -1px 0 0 var(--border)`), 尾字被一条列分隔线切开、读成 pane 边界; 未滚动不画
    (无物可盖, 视觉保持安静)。
  - **④b 边界提示别用 `box-shadow` 落影 —— 它的可见度随首格高度变, 会读成"随机黑块"**:
    2026-10-11 首版提示是"发丝线 + 右缘渐隐落影"两条叠写
    (`inset -1px 0 0 var(--border), 16px 0 14px -10px rgba(0,0,0,.55)`)。2026-10-12 用户报
    「WEBUI 名称列后随机出现阴影」—— 取证(截图逐行测像素 + 桩服务真浏览器复现)确认**不是接线错、
    也不是新表格引擎引起**, 而是落影的几何自带"逐行不一致":
    box-shadow 的 `spread: -10px` 先从首格四周**内缩 10px**, 再用 `blur: 14px` 模糊 ——
    - 常态行首格只有 **22px** 高(见 ⑤: 行 44px − padding 20px − border 2px) ⇒ 落影矩形被内缩成
      **2px**, 只剩模糊尾巴, 肉眼近乎不可见(实测该列最暗处只比行底低 Δ≈2.0/255);
    - 站点/标签多 chip 格换行把行撑高时, 首格 46px+ ⇒ 落影矩形 26px+, 完整显形(实测 Δ≈13.7/255)。
    ⇒ 同一个"横滚"状态在逐行之间深浅差 **7 倍**, 只在"刚好被撑高的那几行"冒出黑块 —— 这正是用户
    描述的"随机"。发丝线(`inset` 阴影**铺满**首格, 与高度无关)无此问题, 故 2026-10-12 **只留发丝线、
    删掉落影**(三皮肤 views.css 同改; 守阵 `test_frontend_frozen_column_boundary_wiring` 由"必须有
    落影成分"翻成"**不得**有 `rgba(0, 0, 0`", 回潮即红)。
    **推广**: 给"行高不齐的列表"画**贴边提示**(落影/渐隐/内发光)时, 别用带负 `spread` 的 box-shadow
    —— 它的可见度是**元素高度的函数**; 要跨行一致就用与高度无关的画法(`inset` 线 / 伪元素渐变 /
    与行高解耦的 `::after`)。
  - **⑤ 首格必须 `align-self: stretch`, 否则高行时盖不住**: `.group-row { align-items: center }`
    —— grid 项默认不拉伸, 吸左首格只有**单行内容高**(实测 22px), 且垂直居中。站点(`.g-sites`
    flex-wrap)/标签(`.g-tags`)等多 chip 格在窄轨(小窗常态)换行把行撑高(实测 71px)后, 横滚时
    滑入首格下方的 chip 从首格**上下两段**成排漏出(2026-10-11 用户复报「小窗时站点的徽标不会
    被名称列挡住」)。修 = 首格 `align-self: stretch`(撑满行内容高; `.g-name` 自身
    `align-items:center` 内容仍居中不改观感)。方角疑虑不成立: 行 `padding: 10px 14px` ≥
    圆角半径, 拉伸后的首格方角落不到行圆角曲线区, 不戳行缘。
  - ⚠ **量底色别在点击后立刻读**: `.group-row` 有 `transition: background`, `getComputedStyle().backgroundColor`
    会拿到**过渡中间值**(实测读到 `rgba(64,72,124,.345)`, 既非旧值也非 `--sel-bg`), 极易误判成「规则没生效」。
  - ⚠ **落点选文件**: 皮肤 CSS 有**单文件 700 行**上限(守阵 `test_frontend_template_split_wiring`,
    只查 atlas / console)。atlas 的 `css/components.css` 已顶满 ⇒ 新增规则一律放该皮肤的 `css/views.css`
    (prism 的表格规则本就在 `views.css`, 且不受该上限约束)。
  - **⑥ 首格底色是「主列表行语言」, 抽屉面复用 `.group-row` 时会被带进去(2026-10-14 修「必现列背景与其他列不一致」)**:
    皮肤 views.css 的 `.group-row > :first-child { background: var(--bg-row) }` 描述的是**主列表**三页
    (种子/辅种/追剧)的行语言(不透明卡底)。抽屉各引擎表面复用 `.group-row`(外壳/桥零特判, D5 口径)
    ⇒ 首格规则跟着漏进抽屉, 而各面**行板语言**各不相同: 族面 06/07/09/11 行板 `--tbl-face-bg`(→`--bg`)、
    04 卡片行 `--bg-card`、05 健康分组与 10 内容树行板透明(承光底 = 抽屉卡底 `--bg-card`)、
    08 行板本就是引擎 `--bg-row`。三样各算 ⇒ 行内画出一条异色竖带(实测 prism/frost 行板
    rgb(242,246,251) vs 首格 rgb(247,250,253); ocean 主题 `--bg #0d1724` vs `--bg-row #112034`,
    Δ 16/255, 用户默认暗色主题下肉眼可辨)。**判据 = 首格可见底 == 行板可见底**(半透明层逐层
    alpha 合成后同 rgb; 裸计算样式相等覆盖不到摘底/透明行的面), 处置 = `shared/dt_table.css`
    **按面重锚**: 族面首格同行板 Token(`--tbl-face-bg`)且悬停同 `--bg-hover`、err(06)/bad(07·09)/
    is-chk(11)/sel(10) 的半透明 tint 用「同色 `linear-gradient` 叠**不透明 `--bg-card`**」合成
    (**不是** `--bg-row` —— 抽屉的承光底是卡底, 见 ② 同法); 04/05 的首格不是「列」而是内容根
    (卡头/`.dt05-rowin`, 单列或卡片栅格无兄弟列可挡) ⇒ 摘底 + `position: static`; 10 多列可横滚
    ⇒ 保留吸左、取 `--bg-card`; 08 基础态同语言不重锚, 只补 bad 合成; 族表头首格显式同
    `--tbl-head-bg`(皮肤规则给 `--bg` 只是回退值相同而侥幸对齐)。
  - **⑦ search-hit 行底是方向渐层, 首格镜像别只给平铺基色**: 主表搜索命中行底是
    `linear-gradient(90deg, var(--accent-soft), transparent 46%) over var(--bg-row)`(components.css),
    而首格规则只有平铺 `--bg-row` ⇒ **整条渐层丢失**(实测追剧表命中行首格 `backgroundImage=none`,
    左缘渐层最强处 Δ≈18/14/9, 名称列读作一条异色竖带)。修 = 三皮肤 views.css 补
    `.group-row.search-hit > :first-child` 同款合成(停靠点同行 46%; 首格宽 << 行宽 ⇒ 格内衰减
    更快, 残余差只落在渐层尾部, 远小于异色竖带)。**推广**: 行底一旦用**空间渐层**, 首格镜像
    必须同款渐层 —— 「同色不同画法」在格/行宽度差巨大时就是可见竖带。
  - **⑧ 变体外壳类名 ↔ CSS 前缀是运行时接线, 不匹配 = 整段规则空转(05 变体行容器坑)**:
    drawer_tpl 变体的 CSS 以 `.drawer .dtNN-list .group-row` 为作用域前缀(U3 引擎化时写入),
    家族结构 = **两层**: 外层 `.dtNN-wrap`(外壳, e2e 通用助手 `openTrackersVariant` 按它等)
    + 内层 `.dtNN-list`(行容器, 锚槽/行活着里面)。05 修前只有单层 `dt05-wrap`、行直接
    挂在它下面 ⇒ 前缀全程不匹配, 六条 `.group-row` 版式规则(摘引擎卡底/行观感归
    `.dt05-rowin`/失败区与 chips 合成行)**全程不生效**, 行一直带着主表卡底(`--bg-row`
    + 描边 + 圆角 + padding)。用户报障面是「必现列背景与其他列不一致」, 但逐面量计算样式时
    05 的真实病症是 `inList=false/inWrap=true`(整面规则空转), 与首格底色是两件事。
    **处置**: 补内层 `.dt05-list` 包住分区(`<div class="dt05-wrap"><div class="dt05-list">`)
    —— ⚠ 首版修法是把外层直接改名 `dt05-list`, 当时"全仓搜 dt05-wrap 无引用"的判据**漏了
    e2e 里动态拼的 `.dt${variantId}-wrap`**, 跑全量 @fast 才被抓到(2 例红); 家族两层结构
    是硬约定, 新变体照抄, 守阵 `test_frontend_pinned_first_cell_bg_per_face` 钉 05 的
    两层相邻结构与 CSS 前缀对齐。**推广**: "全仓搜旧类名无引用"对**动态拼接的选择器**
    无效, 判据要连 `dt${`/模板字符串一起搜; 家族结构约定优先于单点改名。
- **⑨ 首格「镜像行板底色」必须连**过渡**一起镜像, 只镜像静态色值 = 悬停闪一条竖带(2026-10-20 用户
  报「必显列鼠标滑过时背景与其它列不一致, 短暂时间后恢复一致」)**: 三主表(种子/辅种/追剧)行板
  `.group-row` 带 `transition: background var(--dur)`(160ms), 而吸左首格只有静态 `background` 声明、
  **没有 transition** ⇒ `:hover` 一到, 首格同一帧 snap 到 `--bg-hover`, 其余列还在从 `--bg-row` 渐入;
  160ms 内行内是一条硬边竖带, 过渡结束后"恢复一致"。真浏览器逐帧采样(rAF 循环两边读
  backgroundColor, 双皮肤 × 三表全中): prism/frost 首帧首格 rgb(233,241,249) vs 行板 rgb(247,250,253)
  = Δ14; atlas/ocean 首帧 rgb(28,37,52) vs rgb(17,23,34) = Δ18 —— 已过可辨阈, 且**硬边竖带**比
  同色差的面状更刺眼。移出方向同理反号(首格先回基色、其余列还在渐出)。
  **处置**: 三皮肤 views.css 的 `.group-row > :first-child` 补
  `transition: background-color var(--dur) var(--ease)` —— 与行板**同源用同一对令牌**, 禁写字面毫秒
  (行板调时长时两处会静默错拍)。只过渡 `background-color`: 悬停只换颜色, 而 expanded/selected/
  search-hit 走 `background-image` 渐层(见 ⑥⑦, 浏览器不可插值), 声明 `background` 简写等于把不可
  动画的层也纳进来, 无益。
  **判据(推广)**: ①任何"首格跟行板同色"的规则集都要多问一句「行板在动的时候它跟不跟得上」——
  静态色值一致只覆盖静止态; ②量它别量稳态(`waitForTimeout(400)` 之后当然一致, 先前 e2e 的
  「量底色」注释就是这么写的), 要在过渡窗口内**逐帧**采样: 修复前 14/18, 修复后逐帧 0;
  ③静态守阵只能钉声明, "两边真的逐帧同步"必须真浏览器采(与 ⑧ 的静态/行为分工同形)。
  **残留(机制层, 本轮未量)**: expanded/selected/search-hit 的渐层状态两侧承载物不同(行板是纯色
  token, 首格是渐层) —— 渐层不可插值 ⇒ 点展开/选中时理论仍有同帧错位; 用户未报, 要彻底消除须
  把 tint 换成可插值的承载物(伪元素 opacity / inset shadow), 但那会撞 ②③ 的合成与发丝线约束。
  **覆盖面审计(2026-10-20, 用户问「其它位置的表格有没有此问题」)**: 首格镜像规则全仓只有一条
  (三皮肤 `.group-row > :first-child`), 所以一次性覆盖 —— 主表三页、经典抽屉表(tracker/peer/file,
  行在 `.drawer-body` 下)与 04–11 全部引擎变体面共用它; 按面重锚(`shared/dt_table.css`)、变体注入
  CSS 都只改**色值/版式**, 不声明 transition ⇒ 全部继承同一条过渡。真浏览器逐帧复测(双皮肤):
  06/07/09/10/11 与经典抽屉面滑入/移出逐帧差 **0**(10 有 0.5 的取整项)。其余非 `.group-row`
  的表(设置页 HR 明细/波次/拉取历史、统计面板、设置 hub 行、`.drawer-table` 真表)悬停是
  `.hr-hist-row:hover td` 这类**整行所有格同时换色**、且全链无 transition ⇒ 结构性不可能错拍
  (要错拍必须「行有过渡而某格自己画色」两个条件同时成立)。
  **同次审计的另一个发现(2026-10-20 当日已修)**: 08 面的 `.bad` 行静息态首格与相邻列差
  **5.3(prism)/3.4(atlas)** —— 根因不是「没合成」而是**合成基色选错**: 行级 tint
  `--error-soft` 叠在**分组段底 `section.dt08-grp`(实测计算底 = `--bg-row`)**上, 而首格按
  ⑥ 的族面惯例取了抽屉卡底 `--bg-card`。两令牌差: frost `#f7fafd` vs `#fdfeff` ⇒ 经 12%
  透明 tint 合成后逐通道差 5/4/2。**处置**: `shared/dt_table.css` 该条合成基色改
  `var(--bg-row)`(承光底跟随实际承载者, 不跟随族面惯例); 量具新增到
  `e2e/dt-table-face-bg.spec.mjs` 的 `STATE_CASES['08']`(补测位), 静态守阵
  `test_frontend_pinned_first_cell_bg_per_face` 的 08 条改为「必含 --bg-row / 禁 --bg-card」
  —— 两侧都红绿双验过(修前首格 rgb(245,232,231) vs 行板 rgb(240,228,229))。
  **推广**: 合成基色必须按**实际承光层**定(逐层量: 自元素向上第一个不透明层), 不能按
  「这面属于哪一族」推 —— 08 的行表面是卡底语言, 但承光层是分组段底, 两个都“看起来对”。
- **⑩ 半透明状态底是「叠加」不是「替换」—— 行板把底换掉, 首格的合成基准就与它分家
  (2026-10-20 用户报「选中的行必显列背景与其它列不一致」)**: 选中/半选行原本写
  `.group-row.selected { background: var(--sel-bg) }`(裸半透明 tint) —— `background` 简写把行底
  `--bg-row` 一并**替换**掉, 行板实际承光层变成**页底** `--bg`; 而首格按 ②⑥ 的口径合成在
  `--bg-row` 上。两边基准分家 ⇒ 选中行名称列整列一条异色竖带。真浏览器逐像素(1440×900, 选中行
  首格与相邻格同相对位置取色): atlas 首格 rgb(38,45,73) vs 相邻列 rgb(34,39,64) = **Δ9**、prism
  rgb(229,234,249) vs rgb(224,230,246) = Δ5, 三主表(种子/辅种/追剧) × 双皮肤全中; 未选中行 Δ0
  (行底本就是 `--bg-row`)。承光层可反解验证: 相邻列可见底 = (tint 透明度回拆) ≈ `--bg`
  (#0e1218 / #f2f6fb), 而不是 `--bg-row`。
  **处置**: 行板改成**层叠**(与首格同一表达式) ——
  `background: linear-gradient(var(--sel-bg, var(--accent-soft)), var(--sel-bg, var(--accent-soft))), var(--bg-row)`;
  `.member-row` 没有吸左首格、也不承 row 底色 ⇒ 拆出来保持原裸柔底不动。修后行板与首格计算背景
  **逐字相等**, 逐像素 Δ0(prism) / ≤1 取整(atlas)。顺带收掉 ⑨ 残留里 selected/partial 那一半
  (渐层不可插值): 两侧基色都不再变, 只有 image 层同帧出现。
  **判据(推广)**: 「首格 == 行板」不能只量首格自己的合成式, 要问**行板自己的底还在不在** ——
  状态规则用 `background` 简写写半透明令牌时, 底就被静默换掉了。修法不是「把首格改成猜页底」——
  那会把正确性绑在「这张表刚好放在哪种底上」(撞 ⑥ 的按面重锚); 而是让行板恢复「状态叠在行底上」
  的结构, 与承载面无关。
  **同族拓展(2026-10-20 用户「group 一同修」同轮收)**: `.group-row.expanded { background: var(--bg-sunken) }`
  是同一个缺陷 —— 下沉底也是半透明、也是**替换**行底。实测展开行(辅种页)atlas 首格 rgb(9,15,25) vs
  相邻列 rgb(9,13,20) = Δ5/255、prism Δ2/255(上一条只报选中态时它低于可辨阈, 故首轮按范围守恒未动);
  处置同一口径: 三皮肤改 `linear-gradient(var(--bg-sunken), var(--bg-sunken)), var(--bg-row)`(prism
  在 views.css, atlas/console 在 components.css), 修后 Δ0。⚠ console 另有
  `.group-row.expanded:hover { background: var(--bg-sunken) }`(压过行板悬停) —— 不一起改则**悬停
  展开行**那一下又跌回半透明, 首格与行板重新分家; 判据是「凡自带 background 的展开态变体都要同款叠底」。
- **守阵**: `test_frontend_frozen_column_boundary_wiring`(静态钉 is-hscrolled 打标、三皮肤成对
  规则与首格 `align-self: stretch`);
  `test_frontend_pinned_first_cell_bg_per_face`(静态钉 search-hit 首格镜像、dt_table.css 八面
  按面重锚规则与合成基色 `--bg-card`、05 外壳 dt05-list 接线);
  `test_frontend_pinned_first_cell_hover_transition_parity`(静态钉三皮肤首格
  `transition: background-color var(--dur)` 与行板时长同源、悬停镜像规则在位) 与
  `e2e/main-table-pinned-hover.spec.mjs`(三主表 × 双皮肤, 滑入/移出各逐帧采样 —— 首格 vs 行板差
  ≤ 2 + 稳态同色且确实变过色; **在过渡窗口内测**, 不是等 400ms 后测稳态 —— 后者正是这个缺陷
  能活到今天的原因);
  `test_frontend_pinned_first_cell_selected_row_keeps_base`(静态钉三皮肤 `.group-row.selected` /
  `.partial` 的 background 末层是 `var(--bg-row)`(裸半透明令牌即红)、行板与首格 tint 同字面、
  `.member-row.selected` 拆分后仍在) 与 `e2e/main-table-pinned-selected.spec.mjs`(三主表 × 双皮肤,
  真手势 Ctrl+click 选中后 —— 行板 backgroundColor 不透明 + 行板与首格 backgroundColor/
  backgroundImage **逐字相等**, 含选中行被指针压住时; 修复前首格 rgb(17,23,34) vs 行板
  rgba(129,140,248,.18));
  `test_frontend_pinned_first_cell_expanded_row_keeps_base`(静态钉三皮肤 `.group-row.expanded` 末层
  `var(--bg-row)`、首格镜像同基色、console 的 `.group-row.expanded:hover` 不得跌回裸 `--bg-sunken`)
  与同一 spec 里的展开行用例(辅种表/追剧表 × 双皮肤: 展开行板不透明 + 与首格逐字相等, 含悬停);
  几何/可见底色静态判不出, 验证 = 桩服务真浏览器量具 `e2e/dt-table-face-bg.spec.mjs`
  (首格可见底 == 行板可见底, 含悬停与 err/bad/is-chk/sel 状态行; 主表 search-hit 首格渐层镜像)。
  ⚠ 多 clone  workspace 下先确认 8137 没有**别 clone 的残留桩**(本例撞上 auto-qb-clone5 的),
  撞上宁可失败也不要静默验错对象 —— 换干净端口 `E2E_PORT=<n>` 复跑(见 pitfalls/testing/smoke.md)。
