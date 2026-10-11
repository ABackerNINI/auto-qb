# WEBUI 限速曲线预览图 · 配色并入流量方向色族

> 摘要: 用户令「WEBUI 设置限速曲线预览图颜色改为上传/下载色, 与其它地方统一」。落点 = 三套皮肤(console / atlas / prism)的 `.ce-chart-up` / `.ce-chart-down` —— 曲线线色 / 面积填充 / 悬停标记点 / 图例方向标 `.ce-lg-dir.up|down` / 档位组方向条 `.ce-dir-dot.up|down` 五处, 由旧的自证配色(上传 `--warn` 橙 / 下载 `--blue` 浅蓝, 2026-09-28 引入)换成流量方向色族 `--today-up` / `--today-down`(星图 `:root` + 棱镜五主题各一处声明, 取值 上行 `--indigo` / 下行 `--teal`), 与状态栏速度组 · 今日流量卡 · 历史流量图 · qB 流量图同源。面积填充用 `color-mix(in srgb, <令牌> 16%, transparent)` 保持原软色浓度并随主题自动同族; 令牌缺失回退同族原色链(`--indigo` / `--teal`), 不落回 `--accent`。纯 CSS 令牌改动(3 文件) + `conventions/webui.md` 消费面补记, 无 Python 测试增删。
> 最后活动: 2026-10-11 18:43

**Refs:** memory-bank/tasks/26-09-27-webui-curve-chart.md

## 正在进行

- 本专题已收口(改动随本专题入库)。真机设置页肉眼走查仍挂 Open(见档案子任务表末行): 用户下次开设置页顺眼一扫即可。

## 关键结论

- **曲线预览图没有自证配色的理由**: 它的两色表达的就是「上传 / 下载」方向, 与状态栏速度组、今日流量卡、历史流量图、qB 流量图是同一语义 ⇒ 必须走**同一个令牌族**。旧配色 `--warn` / `--blue` 属状态色族(表达种子/行状态), 借来表达方向是**跨族误用**; conventions/webui.md 的「令牌分工: 同名语义只允许有一个令牌族」正是这条判据 —— 再遇到"某处颜色与别处不一致", 先判它表达的是哪个族, 而不是就地调色值。
- **消费面清单是这类改动的检查表**: `conventions/webui.md`「流量方向色族」段原本列了四个消费面(历史流量图 / qB 流量图 / 状态栏今日统计 / 速度组图标 / i-traffic 图标), 本次补上第五个(限速曲线预览图)。**改该族令牌或新增消费面, 都要同步这一行**。
- **`--today-*` 是**间接**令牌**(`--today-up: var(--indigo)`), 所以面积软色不能写 `--indigo-soft`(主题换 up/down 指向就脱族) —— 用 `color-mix(... 16%, transparent)` 从**同一令牌**现算, 与直方图 `.hist-area.up/.down` 用 `fill: var(--today-up); opacity: .08` 是同一思路的两种写法。`color-mix` 在本仓库已有先例(`console/css/components.css` / `shared/console_hub.css`)。
- **悬停标记点一起改是刻意的**: 原 `.ce-chart-dot` 固定 `--fg` 中性灰, 与「线是方向色、点是中性色」的半吊子观感冲突; 历史流量图的 `.hist-dot.up/.down` 本就随方向色 ⇒ 按既有惯例一并归族。若用户不喜欢, 摘掉这三行即可(`.ce-chart-up .ce-chart-dot` / `.ce-chart-down .ce-chart-dot`)。
- **守阵空白**: 仓库没有针对这几条配色规则的机检(与历史流量图同理 —— 颜色属"看图验收"), 故本轮**零测试改动**; 验证 = 全量 `test.full` 无回归 + 三皮肤令牌存在性核对(逐个确认 `--today-up` / `--today-down` / `--indigo` / `--teal` 在星图 `:root`、棱镜五主题均已声明)。
