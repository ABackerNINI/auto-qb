# 已实现 · WEB UI(界面 / 视图 / 状态色)

> 摘要: 摘要: 前端界面与视图的落地记录 —— 设置页 / 追剧视图 / 双界面 / 错误原因 / 各轮修复。
> 触发: WEB UI 做过没有, 前端功能, 设置页, 视图, 状态色, 修复轮次, 双界面

## 已实现 (✅, 有单测覆盖)

- **WEBUI 种子详情面板折叠状态整体移除**(2026-10-09; 档案 [26-10-09-webui-drawer-collapse-removal](../tasks/26-10-09-webui-drawer-collapse-removal.md)): 用户动议「WEBUI移除种子详情面板的折叠状态」—— `drawer.collapsed` 字段、收起/展开钮、44px 收起态头部摘要条(dt-summary)、收起态鼠标换目标 peek(`_drawerPeekTarget`/`_drawerPeekApply`/`__peek` 戳)、`toggleDrawerCollapse`、收起态守卫(qb_traffic_chart 三挂点 active / 拖拽 / 跟随 / Alt+页签)与三皮肤 CSS 全部摘除; 核心层 `dtSummaryHtml`/`_dtDefaultSummary` 与 7 个变体(03/06/09/10/11/12/15)的 `summary()` 供数链同撤(收起档专供, 全成死代码); 面板行为回归纯「开/关 + 拖拽调高」; 守阵同步(删 peek 守阵整函数、D1/W3 守阵改写); 基线见 kb.baseline 最新一条。

> 本文件只留近期条目; 2026-09-26~10-04 二十九条及更早的条目已按 cap 轮转**原文外迁** → [implemented-webui-history.md](implemented-webui-history.md)(下方各条留一行指针, 事实不变)。

- **WEBUI Tracker 状态卡片栅格宽度统一: 虚拟合并卡去 sp2**(2026-10-09; 同专题续作无独立档案, 切片 26-10-06-0751): 用户报「变体 04 状态卡片栅格: 启用 tracker 卡片半宽, 未启用的虚拟条目全宽, 需统一」—— 根因 = 虚拟合并卡沿用设计稿 `sp2` 类跨双列全宽, 与实体卡(各占一格半宽)不一致; 拍板「虚拟卡改半宽」: 删 `.dt04-card.sp2` CSS 规则与类引用, 虚拟卡与实体卡同占一格, 与设计稿的差异点在 `virtualCardHtml` 注释标明; 基线见 [26-10-09-2012](../testing/baselines/26-10-09-2012-webui-dt04-tracker-card-width.md)。
- **WEBUI 详情面板模板选择框收窄: 定宽 240 -> 150px**(2026-10-09; 同专题续作无独立档案, 切片 26-10-06-0751): 用户报「模板选择框太长, 长度需保持固定防切页签其它元素移位」—— 只改定宽值不回退内容驱动宽(原生 select 自动最小宽=最宽 option 的病根与守阵口径不变), `.dt-summary` 维持 240px 独立定宽(各按内容域取值, 不必等宽); 守阵 `test_drawer_tpl_select_fixed_width_tab_independent` / `test_drawer_tpl_cross_seed_fold_and_select_width` 同步 150 并加「240 不得残留」反向断言; 真浏览器双皮肤取证: 四页签 offsetWidth 恒 150(置 auto 探针后还原仍 150), 最长 label(英雄行·键值栅格)自然宽 117px 不截断; 基线见 [26-10-09-1939](../testing/baselines/26-10-09-1939-webui-detail-panel-dt-select-narrow.md)。
- **WEBUI tooltip 二轮去冗 + 锚定下放**(2026-10-07, 分支 webui-tooltip-fix2 两提交 `94013201`/`99fa6eef`; 档案
  [tasks/26-10-04-webui-tooltip-declutter](../tasks/26-10-04-webui-tooltip-declutter.md) Done): 详情面板机械+拍板移除 45 处
  复述/开发者口径 title(守阵 I 组 37 needle); 容器级 title 下放实际悬浮元素 6 组(04 色族胶囊 / 01 横幅 chips / 12 画布删
  / 14 栏头 / 收起摘要条族 5 变体 / 04 虚拟卡), 修用户报 tracker 状态卡片栅格错位; 真浏览器悬浮实测 12/12 PASS;
  计划外发现 ui_harness peers 数据缺失入池 [issue 26-10-07-2309](../issues/26-10-07-2309-test-webui-peers-harness.html)。

- **WEBUI 详情面板 followups 四修: 模板选择器定宽 / 切页返回变体重挂 / 换种子软切换 / tooltip 锚定保活**(2026-10-07, 分支
  fix/webui-detail-panel-followups 四提交 `039ea285`…`8677a415`; 档案
  [tasks/26-10-07-webui-detail-panel-followups](../tasks/26-10-07-webui-detail-panel-followups.md) Done): 用户点名 4 缺陷
  —— ①`.dt-select` 定宽 240px(`.dt-summary` flex-basis 同步): 原生 select 自动最小宽=最宽 option, `dtTplOptions` 按页签
  变化导致宽度跳动带动同排元素; ②切设置页返回详情面板空白: aside 被 v-if 拆建后变体宿主换节点而 `_dtMounted` 持旧宿主,
  watch(drawerVisible) 种子支路进场补 `$nextTick(_dtSync)` 重挂; ③显式换种子闪"空态→加载态→数据"三连: 已开换目标改交棒
  `_switchDrawerTarget` 软切换单点(旧数据撑几何+160ms 延迟遮罩), 同目标重入短路零副作用, 冷启动 loading 按 initialTab
  同帧置位; ④tooltip 锚定保活: place() 定位单点 + reacquire() 语义重解析 + watch()/tick() rAF 帧环(漂移>1px 重定位,
  可见期每帧仅 1 次 getBoundingClientRect), 键盘 NaN 坐标由矩形基准兜住。每项红验守阵 1 个测试函数; 真机 qB 116 种子
  浏览器实测四项全 PASS、零 console 错误; test.full 2717 passed + 4 skipped / 99%(基线
  [26-10-07-1142](../testing/baselines/26-10-07-1142-webui-detail-panel-followups.md))。坑档
  [drawer-switch-flicker](../pitfalls/web-ui/drawer-switch-flicker.md) /
  [aq-tip-position-clamp](../pitfalls/web-ui/aq-tip-position-clamp.md) /
  [vif-host-node-stale](../pitfalls/web-ui/vif-host-node-stale.md)。
- **tracker URL 源头脱敏 方案 B: 拉取即脱敏 + mask 形态 + 编辑下线**(2026-10-07, 计划
  [plans/26-10-07-0055](../plans/26-10-07-0055-plan-tracker-url-sanitize-planb.html) S1–S4 全落地, 分支
  feat/tracker-url-sanitize-planb 六提交 `589c91ff`…`ff97e7cf` 待并回; 档案
  [tasks/26-10-07-webui-tracker-url-sanitize](../tasks/26-10-07-webui-tracker-url-sanitize.md) Done): 把凭据脱敏从
  「日志出口」上提到 **qbapi 拉取即脱敏**—— S1 源头归一化(`mask_tracker_url`/entry 按 R1–R9 规格: 保形状 +
  值全 hash 不按参数名挑 + 不加盐 + path 末段高熵 ≥16 位才整段 hash; 槽/Facade 归一拉取即 mask, 单轨边界 =
  仅删除路径瞬时取原文)+ 6 组单测; S2 编辑下线(前端/路由/命令表/处理器/QbApi 包装/测试全链路删除, 端点清单
  77→76); S3 收口切换原子批(详情 API mask 前置于缓存 + `_cmd_remove_tracker` 改道 mask 比对/原文传 qB/
  0·2+ 命中报错); S4 守阵 5 组(详情 mask/删除 roundtrip/编辑端点 404/405/汇报基线原文/缓存源头 canary)
  逐组红验全过(全红→还原复绿); code-style「凭据脱敏」条升级越界即脱敏。test.full 2698 passed + 4 skipped /
  98.54%(基线 [26-10-07-0337](../testing/baselines/26-10-07-0337-tracker-url-sanitize-planb-s4b.md));
  真机走查未做(无 qB 环境待用户验证), 计划外发现(commands.py:257 虚拟前缀第三处 / static_ui.py:46 POST
  恒 405)未修, 明细见档案进度日志。
- **WEBUI 列对齐几何缺陷修复: 把手槽与列头文字排版解耦**(2026-10-06, 计划
  [plans/26-10-06-1009](../plans/26-10-06-1009-plan-webui-column-alignment.html) PHASE 0-7 全落地; 专题档案
  [tasks/26-09-29-webui-column-alignment](../tasks/26-09-29-webui-column-alignment.md) Done): 用户报「右对齐列
  没有真正对齐标题文字」—— 取证报告 [reports/26-10-06-0945](../reports/26-10-06-0945-report-webui-column-alignment.html)
  实测主视图 4 表右对齐列偏 11px(明细 10px), 根因 `.h-cell{padding-right:10px}`(给拖拽把手留的命中区, 因
  `.h-cell` 有 `overflow:hidden` 不能外伸), 值格 `padding-right:0`。修法取「彻底方案」(报告 §5 P0/C1):
  省略号下移到内层 `<span class="h-label">` → `.h-cell` 改 `display:flex; overflow:visible; padding-right:0`
  → 把手 `.resizer` 以 `right:-5px` 跨进 grid 的 10px 列间距(半进半出, 不新增宽度开销); 右对齐列箭头
  由 `columns.js::colAlignCss()` 追加 `.arrow{order:-1}` 排到标签左侧(消排序时标题跳动 +11px); 三主题同步
  (atlas 新增规则落 `views.css` 避 components.css 700 行 cap)。一并归正「0 值居中」旧口径(第九轮 D4 已裁决
  取消、代码却留): 删三主题 `.g-stat.zero,.m-stat.zero{text-align:center}`。新增常驻守卫
  `e2e/smoke.spec.mjs`「右对齐列表头↔值盒模型差 ≤1px 且值格不居中」(红绿双验)。实测盒模型差
  group/torrent 1px、detail 0px(改前 11/10), 排序后 ≤1(改前 21~22), 三主题一致; `dev.e2e` 6 passed;
  test.full 2676 passed + 4 skipped / 99%(基线
  [26-10-06-1037](../testing/baselines/26-10-06-1037-webui-column-alignment-fix.md))。坑档
  [pitfalls/web-ui/header-cell-gutter](../pitfalls/web-ui/header-cell-gutter.md); 范围外: 设置页 HR 表① 的
  14px(机制不同, `<table>`+`hrsCols()` 无列模型, 待单独排期)。

- **WEB UI 错误信息历史: toast 环形缓冲 + 后端错误环 + 状态栏入口面板**(2026-10-05~06, 计划
  [plans/26-10-05-2026](../plans/26-10-05-2026-plan-webui-toast-error-history.html) S1-S8 全落地, 分支
  feat/webui-error-history 六笔提交 `9e70b0bd`…`ae94311e` 待并回; 认领 issue
  [26-10-05-2013](../issues/26-10-05-2013-feat-webui-toast-error-history.html), Done): `toast()` /
  `_finishToast()` 双钩子**发出即收**(auth 清 toasts 绕过退场钩, 退场收会漏重连前最后一批错误),
  error/timeout 条目 upsert by id 进会话内环形缓冲(cap 50, 零持久化 / 零新配置键, warn 不收);
  后端 `auto_qb` logger 挂 WARNING+ 内存错误环(cap 200, msg 截断, emit 零 IO)+ 只读增量端点
  `GET /api/errlog`(after 游标), 前端 boot 拉全量合并(不计未读)+ 60s 补拉(计未读)+ 游标回退重拉
  —— 补「浏览器关闭期」盲区; 入口按 D1 拍板 **T2 状态栏右段徽标 + 上拉面板**(单条 copyText 复制 /
  一键清空 / 点外关 / Esc 关); D2 采纳: SSE 断线沿发一条 error toast 自动落历史, 重试期不重复。
  守阵: 前端静态 6 条(tests/test_webui_error_history.py)+ 后端行为 7 条(tests/test_webui_backend_errlog.py)
  + 路由金清单 `/api/errlog`(77→78); test.full 2649 passed + 4 skipped / 98%(基线
  [26-10-06-0413](../testing/baselines/26-10-06-0413-webui-toast-error-history-done.md)); 三皮肤真机
  走查未做(CLI 会话, 无真机浏览器 + 真实 qB), 待用户真机验证。
  **2026-10-09 面板改名「通知」+ 陈述型通知出口**(用户报「列偏好空存储提示会遮挡测试截图, 每次测试都
  触发; 并把『错误历史』改为『通知』」): 该提示原先是 `columns.js` 运行时往 `body` 插的 fixed 横幅
  (测试用全新浏览器上下文 ⇒ 去重标记恒空 ⇒ 每次都弹、每张截图被盖一截), 改走新增的陈述型通知单点
  `shared/ui_feedback.js::_recordNotice`(kind `info` / source `notice` / id `n`+seq, 与 toast、后端
  errlog 同列同 cap, 只入面板不计浮层); 面板可见文案(入口 title / 标题 / 空态 / 复制 label)统一为
  「通知」, **内部标识符与后端错误环 `/api/errlog` 保持旧名**(守阵与后端语义钉在它们上)。见
  [activeContext 26-10-09-1137](../activeContext/26-10-09-1137-webui-notice-panel-exit.md)、档案
  [tasks/26-10-09-webui-notice-panel-exit](../tasks/26-10-09-webui-notice-panel-exit.md)、坑档
  [pitfalls/web-ui/floating-hint-vs-notice-panel](../pitfalls/web-ui/floating-hint-vs-notice-panel.md)。

- **WEB UI 强制汇报确认机制重构: epoch 前跳证据门控 + warn 第三态**(2026-10-05, 计划
  [plans/26-10-05-0923](../plans/26-10-05-0923-plan-reannounce-confirm-rework.html) S0-S5 全落地, 提交链
  `bf12a487`(S0 真机探针三点实证: 前跳 +5466s / TOL=3.0 维持 / 推迟路径 min_e+1 冻结)→`89840a3c`
  (S1+S2 webui/commands.py 判定提为纯函数 `_verdict_reannounce` 五分支: ②updating 直证 / ③
  `next > b_next+TOL` 前跳主判据 —— 方向反转, 旧判据 `na < b_na-60` 把 epoch 绝对秒当倒计时恒不触发是
  失效根因, 限基线 status≥2 行 + min 窗口假瞬态守卫 / ④status4+msg 判败先于②③防重试排程假前跳误判 /
  legacy 回退; runtime.py check_pending 三桶聚合 + item 级窗口 + `reannounce_background` 后台核实上限 500)
  →`554bf03e`(S3 static/shared/commands.js: `_pollCmd` 终结纳入 warn 第三态 / SSE 与轮询共用 status 透传 /
  三桶按 r.status 分流 / sticky 文案补推迟子句 / delete_flow 保守口径 warn 不放行删除), 分支
  feat/reannounce-confirm-rework 待并回): 推迟路径(min_interval 未过期)早回执「已受理: 推迟至 HH:MM」+
  后台日志核实, 停止种子直判「未确认」, 超时落 warn 诚实标签不再恒误报「失败」; 机器分流依据从「前缀」
  改为「status」(ok/error/warn)。§05 十一组用例全落地净增 +7; 新坑档
  [pitfalls/backend/announce-epoch-semantics](../pitfalls/backend/announce-epoch-semantics.md);
  test.full 2610 passed + 4 skipped / 98%(基线
  [26-10-05-1202](../testing/baselines/26-10-05-1202-reannounce-confirm-rework.md)); 档案
  [tasks/26-10-05-backend-reannounce-confirm-rework](../tasks/26-10-05-backend-reannounce-confirm-rework.md)(Done)。

- **WEB UI 危险动作防护: 重新校验确认框 + 跳检前置条件三分流预检**(2026-10-05, 计划
  [plans/26-10-05-0314](../plans/26-10-05-0314-plan-webui-danger-guards.html) S0-S5 全落地, 提交链
  `ae2982d9`(S1a store 组级判定上移单点, grouping_mod 委托保签名)→`372f197c`(S1b-1 ops
  `_skip_gates_detail` 三分流判定单点只读变体 + G3-G6 新闸门 + force 语义 + precheck dry-run +
  filelist 并入执行链, R2 live 复核前移到闸门之前)→`64479a28`(S1b-2 G7/G8 组内镜像闸门: 校验在途
  =force 可豁越 / 校验失败推断=blocked 硬拒)→`0d2ff943`(S2 预检端点
  `POST /api/torrents/skip-check/precheck` + 单发/批量 force 透传)→`005dd20a`(S3
  `_recheckConfirm` 共用确认框接入全部鼠标入口, 与键盘路径同文案)→`b87ed2e1`(S4 跳检预检对话框
  三分流状态机: 进框禁用→预检→按态渲染, force 钮必须先见赌注), 分支 webui-danger-guards 待并回):
  跳检「该不该允许」判定下沉 ops 单点与规则侧同谓词(规则侧零变化, test_checking 69 条全程绿),
  WEB 确认框升级「进框禁用→预检→按态渲染」三分流(case 1 禁止无逃生 / case 2 可显式强制 /
  case 3 放行), force 服务端裁决只豁越 G5/G7; 重新校验鼠标三通道补齐确认框。新守阵 22 条(每闸门
  一测 + 红验探针先红后恢复; T13/T24 首版经红验暴露突变盲区升级, 坑档
  [pitfalls/testing/static-guard-mutation](../pitfalls/testing/static-guard-mutation.md));
  test.full 2576 passed + 4 skipped / 99%(基线
  [26-10-05-0737](../testing/baselines/26-10-05-0737-webui-danger-guards.md)); 档案
  [tasks/26-10-05-webui-danger-guards](../tasks/26-10-05-webui-danger-guards.md)(Done)。

- **WEB UI 复述型 tooltip 全量移除 67 处 + 不复活守卫**(2026-10-04, 判定报告
  [reports/26-10-04-0815](../reports/26-10-04-0815-report-webui-tooltip-declutter.html) 全量实施, 提交链
  `72a7d274`(报告)→`80220a82`(A 组状态栏 7 处 + A5 sbStats 精简)→`5c0412ff`(B 组顶栏 12)→`ae919a39`
  (追剧/详情抽屉 12)→`728f92ab`(对话框族 19)→`a33db037`(设置页/配置编辑器 16)→`e8203a3c`
  (H1 columns.js + 守卫), 分支 webui-tooltip-declutter 待并回): 133 处全量清点按 R1 复述 / R2 自明+无害 /
  R3 截断兜底 / R4 信息增量 / R5 不可发现交互+后果预告 五类判据判定, 移除 67 / 保留 66; 悬浮提示唯一
  通道仍是 shared/ui_feedback.js `.aq-tip` 拦截层, 移除 = 纯删 title 属性, 三皮肤零成对改; dialogs.js
  A5(statusbar 统计项)按报告「精简」只去复述半句。守阵: test_removed_redundant_tooltips_stay_removed
  (tests/test_web.py)断言代表性已删文案不写回。全量基线 [testing/baselines/26-10-04-0900](../testing/baselines/26-10-04-0900-webui-tooltip-declutter.md);
  档案 [tasks/26-10-04-webui-tooltip-declutter](../tasks/26-10-04-webui-tooltip-declutter.md)(Done)。

- WEB UI **WEB UI HR 拉取历史详情表(2026-10-04)**: 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **WEB UI 添加种子三下拉 label 闪烁「第四轮」(JS 收层守卫单点加固)(2026-10-04)**: 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **WEB UI qB 口径流量图三图(2026-10-04)**: 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **WEB UI 添加种子三浮层互斥补双向(closeAddPopsExcept 单点)(2026-10-04)**: 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **WEB UI 添加种子三下拉 label 闪烁「第三轮」(上轮修法未修住)(2026-10-04)**: 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **WEB UI 抽屉出入过渡动画(2026-10-04)**: 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **WEB UI 添加种子三下拉「第二轮遗留四项」(2026-10-03)**: 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **WEB UI 添加种子三下拉「失焦即收 + 限高不出窗」(2026-10-03)**: 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **WEB UI 种子详情抽屉重设计: 浮层 → 底部停靠属性面板 (方案A)(2026-10-03)**: 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **WEB UI 站点级「显式空 = 覆盖为空」三态 + 「跟随全局」删键: 删除类标签全局/站点作用域混淆修复(2026-10-03)**: 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI ****WEB UI HR 判定新鲜度置脏 (2026-10-03, 计划(2026-10-03)**: 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **多选右键菜单四项(限速/移动/跳检/导出 .torrent)+ 跳检菜单开关 `web.skip_check_menu`**: 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **HR 站点状态区展示二轮改造(2026-10-02)**: 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **HR 排除辅种补悬停弹窗**(2026-10-02): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **ESC 兜底清全部面筛**(2026-10-02): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **Shift 连选起点与键鼠联动统一**(2026-10-02): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **HR 在线核实详情两张表**(2026-10-01): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **设置页只读字段(程序托管/R 级)**(2026-10-01): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **web.token 生成改走 atomic_write**(2026-10-01): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **标签列全量展开, 移除「+1/+2」折叠**(2026-09-30): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **键盘快捷键全量落地(可自定义)**(2026-09-30, plans/26-09-28-0354 W1-W7 两波): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **做种时长列/弹窗的「要求」显示修复**(2026-09-29): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **前端大文件拆分 + 单一语义模板收敛 + 内核续拆**(2026-09-27, plans/26-09-26-2233 五波全落地): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **自绘悬浮提示 .aq-tip**(2026-09-28): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **设置页分类回归修复: 「常规/日志」成块 + 运行日志默认折叠**(2026-09-28): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **搜索框语法帮助入口: 框内幽灵「?」+ 锚定浮卡(方案A)**(2026-09-28): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **多选右键菜单作用于整个选中集合**(2026-09-24, 已入库 `907890b`): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **右键次级菜单三修**(2026-09-25, 已入库 `3a8dabd`): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **搜索负词种子级定案: 任一候选行含负词 ⇒ 整种子排除**(2026-09-26/27): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **搜索匹配收敛服务端单点: 三页(辅种/种子/追剧)统一消费 searchHits**(2026-09-26 晚): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **搜索查询语法强化: 词 AND + `-排除` + `"短语"`(行级语义)**(2026-09-26): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **做种时长悬停弹窗(T3 进度仪表)**(2026-09-26): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **设置页分组合并: 日志/界面(WebUI)/通知/运行日志 并入「常规」**(2026-09-26): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **种子级标签/分类即时编辑**(2026-09-26): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **一键导入缺失站点**(2026-09-26): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **站点接入数据白屏修复**(2026-09-25): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **HR 删除安全档位呈现**(2026-09-25): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **设置页控件两处打磨**(2026-09-25): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **设置页合一: 移除经典设置页**(2026-09-25): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

> 注意区分: 下表部分功能作者在 README 中标注 🚧 = "已实现但未严格测试(实盘验证)", 如规则引擎的条件/动作/checking/去重语义等 — 有单测但作者尚不认为经过严格验证; 此类 🚧 ≠ 未实现, 勿移除 (语义详见 pitfalls.md)。
- **2026-09-21 设置页新版(Console Hub)落地**(含版式硬知识: 派生变量声明在使用层 / 发光负 spread / 切角与发光互斥; 无浏览器验证手段)与计划外发现(setUnitNum computed 误用, 已随经典页移除)**: 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- **2026-09-19 打开目标文件夹修复 / 2026-09-18 视图重建收口·错误原因显示 / 2026-09-15 追剧视图 / 2026-09-17 第 9/10/11 轮修复 / 2026-09-15 三条(双界面命名目录化/旧版第八轮优化/新版界面与多主题)**: 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
