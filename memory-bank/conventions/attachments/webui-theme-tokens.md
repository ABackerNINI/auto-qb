# WEB UI 令牌分工与 HTML dark 主题

> 摘要: `conventions/webui.md` 的令牌分工与 HTML 文档 dark 主题规范 —— 整段逐字外迁, 本节是该主题的现行权威。
> 触发: 令牌, token, 状态色, 选中态, 流量色, 三皮肤, 主题, dark, color-scheme, HTML 产出

## WEB UI 令牌分工 (2026-09-17 第十轮)

同名语义只允许有一个令牌族, 新增值先找族再考虑加令牌:

- **令牌名集三皮肤必须相等**(issue 26-10-20-2231, 守阵 `test_frontend_skin_css_token_parity`): 取值按各自设计语言各写各的
  (如 `--font-display` 星图 = 单一无衬线族、控制台/棱镜 = Bahnschrift), 但**名字一个都不能少** —— 少声明一个,
  该皮肤下 `var(--x)` 的那条声明会在计算值阶段**整条作废且无任何报错**(星图此前少 3 个字体令牌, 自己 4 处
  `var(--font-mono)` 裸引用全程失效、共用层只能按"该皮肤没有令牌"各写兜底链)。新增令牌 = 三皮肤同轮补名。
- **浮层底色 `--bg-pop` 与玻璃化**(2026-11-02 立, 2026-11-04 反转, 见下): flux 是唯一把
  `--bg-card: rgba(...,.82)` / `--bg-elev: rgba(...,.92)` 写成半透明的皮肤(另三皮肤两 token 均为不透明 hex)。
  `--bg-pop` = `--bg-elev(.92)` 覆在页底 `--bg` 上的**不透明等效色**(flux `#1c2a3f`), **只给无毛玻璃的浮层**,
  另三皮肤 `--bg-pop: var(--bg-elev)` 惰性别名(名集守阵要求)。
  **2026-11-04 口径反转(全浮层玻璃化, 用户报「添加种子/右键菜单等弹窗毛玻璃近乎没有」)**: 26-11-02
  「透正文」的根因是半透明底**无 blur**; 挂上 blur 后半透明即毛玻璃, 不再透可读正文。故 flux 菜单/浮层族
  (下拉/右键菜单/次级菜单/悬停卡/限速浮层/拖放落点/HR 全屏面板/图表与历史 tip/共用层覆盖组含
  `.relc-pop`)一律 `--bg-card` 半透明底 + backdrop-filter, 预算 4→16(见 flux 段); **`--bg-pop` 消费面收窄到
  `.col-ghost` 一处**(列头拖动虚影 —— 每帧移动的 fixed 元素挂 blur = 逐帧回读采样, 唯一不玻璃化的浮层)。
  ⚠ **挂 blur 的浮层不能吃近不透明底**(2026-11-03 回归): `.modal` 的底必须走 `--msg-base: var(--bg-card)`
  (alpha .82), 换成 `--bg-elev`(.92)/`--bg-pop` 会把 blur 只剩 8% 透视, 肉眼读作「毛玻璃被透明修复弄丢了」。
  ⚠ **玻璃可见度 = 面板底 alpha × 遮罩 alpha 的叠乘**(2026-11-04 第二根因): `.modal-mask` 遮罩 alpha
  ≤ .6(现 .5) —— 11-03 轮只修了弹窗底(.92→.82), .72 遮罩仍把实际透视压到 ~5%, blur 依旧不可见。
  判据与双向钉 = 守阵 `_scan_flux_modal_frost`(含遮罩浓度钉、玻璃化浮层族钉、.col-ghost 反向钉)。
  shared 层浮层(`console_hub.css` 的 `.hb-pop`/`.hb-tr-drop`/`.search-help-pop`/`.aq-tip`/`.err-panel`、
  `row_lang.css` 的 `.rowlang-menu`/`.relc-pop`)本体**不动**(shared 基线仍不透明 --bg-pop, 三旧皮肤无毛玻璃),
  只在 flux 侧用 `html[data-fx-preset]` 前缀覆盖为半透明底+blur(见 flux 段)。
- **CSS 分层三皮肤同构**(2026-10-21): 星图/控制台 = `style.css → css/components → css/views → css/dialogs`;
  棱镜 = `css/tokens → css/themes/*(五主题) → css/base → css/components → css/views → css/dialogs`;
  三皮肤最后都接共用层 `shared/console_hub.css` + `shared/dt_table.css`。**弹窗层恒排最后**(抽屉/确认框/对话框/
  全屏覆盖层/悬停弹窗/抽屉内表), 排在页面级规则之前会被反压 —— 棱镜此前正是这种变形结构(issue 26-10-20-2231)。
  链接序由 `test_frontend_template_split_wiring` 钉死, 别按"就近贴语义最近的文件"改。
- **状态色族**(`--green/--blue/--error/--warn` + `--paused-*`): 表达**种子/行状态**。只染有语义的状态; 0 值/
  "—"占位不染; 芯片(站点/标签/分类)保持自身语义色不跟随行色(决策 D6-A —— 芯片表达**成员级**语义, 跟随行色会抹平这层信息)。
  `--paused` 是唯一"无色相"的成员, 取值 = `--fg-muted`(中性中间调), 配 `--paused-soft: transparent` + `--paused-line: var(--border-strong)`
  —— **暂停/其它一律"不铺底 + 中性描边"**, 不许落回 `--surface-2`(暗底 = 白 6%, 读作"太白/没颜色")。该族**各套 UI 各声明一处**(atlas/prism/console/flux)
  (星图 `:root` / 棱镜 `themes/*.css` 五主题), 改值必须全处同改。
- **状态色 → kind 映射与 `--st` 单点**(2026-11-02): 七个 kind 各绑一支令牌 —— 做种 `--green` / 下载 `--blue` /
  **校验 `--warn`(琥珀)** / **移动中 `--violet`(紫, 与 `views.py::state_kind` docstring 的原口径对齐)** /
  错误 `--error` / 暂停与其它 `--paused`。消费面不再各写令牌值: 行元素(`.k-*` 图例项 / `.site-chip.<kind>` /
  `.group-row.s-<kind>` / `.member-row.<kind>`)声明 `--st`(前景) 与 `--st-soft`(柔和底) 一次, 图例色、芯片底、
  行文字(名称/数值/state-text/.val)、**进度条填充**统一读变量。声明在**行元素**上靠继承下发 ——
  内层成员行自带 kind 类即覆盖, 不用后代选择器给子行连带染组行色。校验与下载原先同 `--blue` 肉眼分不出
  (用户报障原症状), 拆开后由 `test_frontend_static_bundle_health` 第 19 项钉死值。
- **选中态族**(`--sel-bg/--sel-line/--sel-bar`, 五主题均取**非绿**的靖蓝族): 只用于"用户选中"语义; **不得**再引用
  `--accent`/`--accent-soft` —— 品牌主题(orbit)下 `--accent` 与做种 `--green` 同族且明度接近, 用户分不出"选中"与"做种"。
- **流量方向色族**(`--today-up/--today-down`, 星图 `:root` 一处 + 棱镜五主题各一处, 改值必须全处同改):
  表达**上下行流量方向**, 消费面 = 历史流量图 SVG / qB 流量图(uPlot 经 `_qbChartTokens()` 现读令牌;
  2026-10-08 起同源还喂**画布注解层**: 限速虚线随方向取 `up/down`, 缺口斜纹取 `grid` 令牌) /
  状态栏今日统计(`.sb-item.sb-today .v-up/.v-down`) / 状态栏速度组方向图标(`.sb-spd .ico-up/.ico-down`) /
  i-traffic 组图标(内联 `var(--today-*)`) / **设置页限速曲线预览图**(`.ce-chart-up`/`.ce-chart-down`
  五处: 曲线线色 / 面积填充 / 悬停标记点 / 图例方向标 `.ce-lg-dir` / 档位组方向条 `.ce-dir-dot`;
  2026-10-11 归族, 此前误借状态色族 `--warn`/`--blue`)。取值 **上行 = `--indigo`(紫) / 下行 = `--teal`(蓝绿)**
  (2026-10-04 用户拍板交换)。⚠ 该族是**间接令牌**(指向 `--indigo`/`--teal`), 需要"同色软底"时**不能**借
  `--indigo-soft`/`--teal-soft`(主题换指向即脱族) —— 用 `color-mix(in srgb, var(--today-up) 16%, transparent)`
  从同一令牌现算, 或照直方图 `.hist-area.up|down` 的 `fill: var(--today-*)` + `opacity` 写法。
  ⚠ 速度组图标**不要**改全局 `.ico-up/.ico-down`(绿/蓝, 还喂顶栏「种子」等
  非流量位置), 只能按 `.sb-spd` 作用域覆盖。状态栏限速值(`.sb-spd .lim`)是**参考值**, 用中性灰 `--fg-dim`
  (与做种要求值 `.m-pair .req` 同款), 不随方向染色。
- **画布注解层限速线(plan 26-10-12-0535)**: qB 流量图的限速虚线自 2026-10-12 起按**当时值分段**——
  后端主循环采样点把 qB 全局限速生效值(上/下行分开, 0 = 不限速)按「有变化才记」落
  `<data_dir>/qb-traffic-v4/limits/<日期>.dat`(分天, 00:00 硬切 + 新天首行基线 carry, 不淘汰对齐
  day/month 全保留; 记录器在 `core/traffic_limits.py`, 挂点 `traffic_sample_mod._sample_global`),
  三端点 payload 统一附 `limits: [[ts,up,down],...]`(首元素 = 窗口起点合成事件, 记录起点前无值);
  前端 `_qbDrawLimits` 从图记录 `u._qbLimits` 走 `_qbLimitSegs` 纯函数构段(每段画各自区间, 末段到
  图右沿; 逐段可见性 0 < v < ymax; 快路 setData 同步换 limits), 悬停 tooltip 增补「当时限速」行
  (`_qbLimitAt` 二分, 记录起点前不给)。变体 13 无注解层照旧不显示; 14/15 走共享钩子自动生效。
- **表面/底色族**: 状态栏用专用 `--statusbar-bg`(与页底形成可见层级); **不要改 `--glass`** —— 它同时管顶栏,
  改它会连带改顶栏。
- **尺寸族**: 弹窗宽度取 `--modal-w-narrow/base/form/add`/`--modal-wide-w`(各套 UI 同值同族); 新增弹窗只选档,
  不写新数字(这正是此前"第 N 次调大"的成因)。
- **单点口径原则(通用)**: 同一数据/口径在两个以上地方出现时, 收成 computed/method 单点(如 `speedLimitBytes`
  限速取数、`cellSeedingTime/cellRatio/cellPeers/cellAvailability/cellTime` 单元格口径、`_deleteDetails` 删除详情行、
  `selSizeSummaryOf` 选中摘要大小、`colAlignCss` 列对齐), 模板里只引用不重算。新增展示口径时先问"它是否已被别处实现"。

## HTML 文档一律 dark 主题 (2026-09-20 用户指定)

- **适用**: 所有产出的单文件 HTML —— 计划文档 / issue 报告 / 交付物 / 演示页。**一律深色底 + 浅色字, 禁止浅底黑字**。
- **配色口径**: `--bg` / `--paper` 亮度 ≈ `#0f…`~`#18…`, `--ink` 亮度 ≥ `#d8…`; 样式里**必须**写 `color-scheme: dark` —— 缺这条, 浏览器原生滚动条与表单控件不会跟着变深。
- **制品模板正文区**(2026-10-17): skill `templates/{plan,report}.html` 的 `.sheet` = `max-width: 1280px; padding: 48px clamp(18px, 3.2vw, 44px) 80px` —— **版面自适应**: sheet 随视口流动、侧距随宽度伸缩, 正文/列表/表格/代码块同宽 (prose 不设 ch 上限, 右缘对齐); 窄视口 (≤1180px) 表格内代码允许断行防页面横向溢出。规格单点在模板自身(带注释); 存量自带内联 CSS 的件按冻结线(2026-10-17 模板正文区定型日)豁免, 不逐一计数 —— 存量数字随产出持续漂移, 以冻结线日期为界。
- **存量**: `memory-bank/plans/`、`memory-bank/issues/`、`memory-bank/reports/` 的全部主题件已全量核查为深色(最近一次全量实测 2026-10-31, 此后不再回填计数 —— 计数随产出漂移, 违规与否只看「新产出是不是深色」); 新产出若不是深色即为违规。
- **例外**: `resources/`(ui-component-libraries 设计观摩稿 + settings-page-templates 候选稿)**不套用** —— 那批白底极简(kenya-hara / pentagram / muller-brockmann)是设计本体。⚠ 遇到"统一主题"类要求, 先分清**交付物 vs 参考素材**, 别一把梭。
- **命名**: 放 `memory-bank/plans/` 时命名 `YY-MM-DD-HHMM-<slug>.html`, 日期时间**用 `commands run kb.time stamp` 取当前值**, 不靠记忆。
