# 首列吸左固定(冻结列)在本仓表格上的十处非显然约束

> 摘要: 首列吸左(冻结列)在本仓 `.group-row` 表格上的十处非显然约束 —— 表头反向位移、首格不透明合成、边界发丝线、stretch、按面重锚、search-hit 渐层镜像、变体两层结构、过渡同源、状态底叠加; 完整处置步骤与实测证据见 [attachments/frozen-column-constraints.md](attachments/frozen-column-constraints.md)。
> 等级: L0
> 触发: 首列吸左, 名称列后阴影, 随机出现阴影, 黑块, box-shadow spread 负值, 落影随行高变, 冻结列, frozen column, sticky 首格, 横向滚动, 表头横向同步, transform 桥接, 首格不透明, 半透明状态底, 双重上色, 左侧色条消失, 过渡中间值, 皮肤 CSS 700 行上限, 残根, 尾字粘连, 状态列被盖住, 吸左边界, is-hscrolled, 边界落影, 徽标漏出, chip 换行, align-items center, align-self stretch, 首格高度, 必现列背景不一致, 异色竖带, 按面重锚, 承光底, dt05-list, 行容器, 外壳类名空转, search-hit 渐层丢失, dtNN-wrap, 动态拼接选择器, 必显列悬停闪竖带, 滑过闪一下又恢复一致, 悬停时首格与其它列不同色, 首格无过渡, transition 不同源, 行板 160ms 首格瞬切, 过渡窗口逐帧采样, 选中行必显列异色竖带, 选中的行名称列与其它列不同色, 半透明状态底替换行底, background 简写换掉行底, 行板承光层变页底, 行底丢失, 合成基准分家

**Refs:** memory-bank/tasks/26-10-06-webui-frozen-first-column.md,memory-bank/tasks/26-10-11-webui-frozen-col-boundary.md,memory-bank/reports/26-10-14-0136-report-webui-detail-table-rebuild-review.html

### 首列吸左固定(冻结列)的十处非显然约束

- **触发**: 给行宽 `fit-content` > 容器的这些表(辅种 / 种子 / 追剧)加「首列常驻滚动容器左缘」。
- **判别**: 一行 `position: sticky` 完不了事 —— 表头、底色、左色条三处各有独立成因(见处置);
  另有一条量测陷阱: 点击后立刻读 `backgroundColor` 会拿到**过渡中间值**。
- **处置**: 详细步骤与实测证据见 [attachments/frozen-column-constraints.md](attachments/frozen-column-constraints.md)

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
  **同族拓展(2026-10-30, issue 26-10-30-0818)**: 行语言 flat(ba2a91be)把「同一表达式」弱化成
  「视觉恒等」—— 行板取半透明 tint 叠页底、首格取 color-mix 不透明等价色, 肉眼逐帧一致
  (premultiplied 恒等), 但 e2e 守阵按**计算值**比较(逐帧通道/稳态逐字)即红(atlas 6 例)。
  判据再加一条: **行板与首格要逐字同一个表达式, 「数学上恒等」的另一种写法不算同** —— 恒等
  推导对人不透明, 守阵读的是计算样式。另: prism 例全绿是无头亮主题假象
  (testing/headless-prefers-light-theme-gate), 双皮肤绿≠两面都真正吃到待测规则。
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
  现状(2026-11-03, 计划 26-11-03-0316): e2e 端口由脚本取号(`ui_harness --port 0` + `webServer.wait`
  捕获回传), `E2E_PORT` 已取消(设置即报错); 复跑直接起新桩即可。
