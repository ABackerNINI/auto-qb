# 已实现 · WEB UI — 2026-10-04~10-07 六条实施记录 (外迁存档)

> 摘要: `progress/implemented-webui.md` 的六条胖条目(drawer followups / tracker URL 脱敏 / 列对齐几何 / 错误信息历史 / 强制汇报确认 / 危险动作防护)原样外迁 —— 主档 23,251 撞 `evergreen` cap 20,000, 按「触顶切最老一半到 `attachments/`」处置。
> 触发: WEB UI 2026-10 实施记录, cap 外迁, 危险动作防护, 强制汇报确认, 列对齐几何

> 本文件是**外迁存档**: 主档该段原文, **一字未改**搬来(仅相对链接整体上移一层 —— 本文件在 `progress/attachments/`)。
> 本目录在 `EXCLUDED_DIRS`, 不计 cap; 主档原位留指针。

- **tracker URL 源头脱敏 方案 B: 拉取即脱敏 + mask 形态 + 编辑下线**(2026-10-07, 计划
  [plans/26-10-07-0055](../../plans/26-10-07-0055-plan-tracker-url-sanitize-planb.html) S1–S4 全落地, 分支
  feat/tracker-url-sanitize-planb 六提交 `589c91ff`…`ff97e7cf` 待并回; 档案
  [tasks/26-10-07-webui-tracker-url-sanitize](../../tasks/26-10-07-webui-tracker-url-sanitize.md) Done): 把凭据脱敏从
  「日志出口」上提到 **qbapi 拉取即脱敏**—— S1 源头归一化(`mask_tracker_url`/entry 按 R1–R9 规格: 保形状 +
  值全 hash 不按参数名挑 + 不加盐 + path 末段高熵 ≥16 位才整段 hash; 槽/Facade 归一拉取即 mask, 单轨边界 =
  仅删除路径瞬时取原文)+ 6 组单测; S2 编辑下线(前端/路由/命令表/处理器/QbApi 包装/测试全链路删除, 端点清单
  77→76); S3 收口切换原子批(详情 API mask 前置于缓存 + `_cmd_remove_tracker` 改道 mask 比对/原文传 qB/
  0·2+ 命中报错); S4 守阵 5 组(详情 mask/删除 roundtrip/编辑端点 404/405/汇报基线原文/缓存源头 canary)
  逐组红验全过(全红→还原复绿); code-style「凭据脱敏」条升级越界即脱敏。test.full 2698 passed + 4 skipped /
  98.54%(基线 [26-10-07-0337](../../testing/baselines/attachments/26-10-07-0337-tracker-url-sanitize-planb-s4b.md));
  真机走查未做(无 qB 环境待用户验证), 计划外发现(commands.py:257 虚拟前缀第三处 / static_ui.py:46 POST
  恒 405)未修, 明细见档案进度日志。
- **WEBUI 列对齐几何缺陷修复: 把手槽与列头文字排版解耦**(2026-10-06, 计划
  [plans/26-10-06-1009](../../plans/26-10-06-1009-plan-webui-column-alignment.html) PHASE 0-7 全落地; 专题档案
  [tasks/26-09-29-webui-column-alignment](../../tasks/26-09-29-webui-column-alignment.md) Done): 用户报「右对齐列
  没有真正对齐标题文字」—— 取证报告 [reports/26-10-06-0945](../../reports/26-10-06-0945-report-webui-column-alignment.html)
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
  [26-10-06-1037](../../testing/baselines/attachments/26-10-06-1037-webui-column-alignment-fix.md))。坑档
  [pitfalls/web-ui/header-cell-gutter](../../pitfalls/web-ui/header-cell-gutter.md); 范围外: 设置页 HR 表① 的
  14px(机制不同, `<table>`+`hrsCols()` 无列模型, 待单独排期)。

- **WEB UI 错误信息历史: toast 环形缓冲 + 后端错误环 + 状态栏入口面板**(2026-10-05~06, 计划
  [plans/26-10-05-2026](../../plans/26-10-05-2026-plan-webui-toast-error-history.html) S1-S8 全落地, 分支
  feat/webui-error-history 六笔提交 `9e70b0bd`…`ae94311e` 待并回; 认领 issue
  [26-10-05-2013](../../issues/26-10-05-2013-feat-webui-toast-error-history.html), Done): `toast()` /
  `_finishToast()` 双钩子**发出即收**(auth 清 toasts 绕过退场钩, 退场收会漏重连前最后一批错误),
  error/timeout 条目 upsert by id 进会话内环形缓冲(cap 50, 零持久化 / 零新配置键, warn 不收);
  后端 `auto_qb` logger 挂 WARNING+ 内存错误环(cap 200, msg 截断, emit 零 IO)+ 只读增量端点
  `GET /api/errlog`(after 游标), 前端 boot 拉全量合并(不计未读)+ 60s 补拉(计未读)+ 游标回退重拉
  —— 补「浏览器关闭期」盲区; 入口按 D1 拍板 **T2 状态栏右段徽标 + 上拉面板**(单条 copyText 复制 /
  一键清空 / 点外关 / Esc 关); D2 采纳: SSE 断线沿发一条 error toast 自动落历史, 重试期不重复。
  守阵: 前端静态 6 条(tests/test_webui_error_history.py)+ 后端行为 7 条(tests/test_webui_backend_errlog.py)
  + 路由金清单 `/api/errlog`(77→78); test.full 2649 passed + 4 skipped / 98%(基线
  [26-10-06-0413](../../testing/baselines/attachments/26-10-06-0413-webui-toast-error-history-done.md)); 三皮肤真机
  走查未做(CLI 会话, 无真机浏览器 + 真实 qB), 待用户真机验证。
  **2026-10-09 面板改名「通知」+ 陈述型通知出口**(用户报「列偏好空存储提示会遮挡测试截图, 每次测试都
  触发; 并把『错误历史』改为『通知』」): 该提示原先是 `columns.js` 运行时往 `body` 插的 fixed 横幅
  (测试用全新浏览器上下文 ⇒ 去重标记恒空 ⇒ 每次都弹、每张截图被盖一截), 改走新增的陈述型通知单点
  `shared/ui_feedback.js::_recordNotice`(kind `info` / source `notice` / id `n`+seq, 与 toast、后端
  errlog 同列同 cap, 只入面板不计浮层); 面板可见文案(入口 title / 标题 / 空态 / 复制 label)统一为
  「通知」, **内部标识符与后端错误环 `/api/errlog` 保持旧名**(守阵与后端语义钉在它们上)。见
  [任务档案](../../tasks/26-10-09-webui-notice-panel-exit.md)、档案
  [tasks/26-10-09-webui-notice-panel-exit](../../tasks/26-10-09-webui-notice-panel-exit.md)、坑档
  [pitfalls/web-ui/floating-hint-vs-notice-panel](../../pitfalls/web-ui/floating-hint-vs-notice-panel.md)。

- **WEB UI 强制汇报确认机制重构: epoch 前跳证据门控 + warn 第三态**(2026-10-05, 计划
  [plans/26-10-05-0923](../../plans/26-10-05-0923-plan-reannounce-confirm-rework.html) S0-S5 全落地, 提交链
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
  [pitfalls/backend/announce-epoch-semantics](../../pitfalls/backend/announce-epoch-semantics.md);
  test.full 2610 passed + 4 skipped / 98%(基线
  [26-10-05-1202](../../testing/baselines/attachments/26-10-05-1202-reannounce-confirm-rework.md)); 档案
  [tasks/26-10-05-backend-reannounce-confirm-rework](../../tasks/26-10-05-backend-reannounce-confirm-rework.md)(Done)。

- **WEB UI 危险动作防护: 重新校验确认框 + 跳检前置条件三分流预检**(2026-10-05, 计划
  [plans/26-10-05-0314](../../plans/26-10-05-0314-plan-webui-danger-guards.html) S0-S5 全落地, 提交链
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
  [pitfalls/testing/static-guard-mutation](../../pitfalls/testing/static-guard-mutation.md));
  test.full 2576 passed + 4 skipped / 99%(基线
  [26-10-05-0737](../../testing/baselines/attachments/26-10-05-0737-webui-danger-guards.md)); 档案
  [tasks/26-10-05-webui-danger-guards](../../tasks/26-10-05-webui-danger-guards.md)(Done)。

- **WEB UI 复述型 tooltip 全量移除 67 处 + 不复活守卫**(2026-10-04, 判定报告
  [reports/26-10-04-0815](../../reports/26-10-04-0815-report-webui-tooltip-declutter.html) 全量实施, 提交链
  `72a7d274`(报告)→`80220a82`(A 组状态栏 7 处 + A5 sbStats 精简)→`5c0412ff`(B 组顶栏 12)→`ae919a39`
  (追剧/详情抽屉 12)→`728f92ab`(对话框族 19)→`a33db037`(设置页/配置编辑器 16)→`e8203a3c`
  (H1 columns.js + 守卫), 分支 webui-tooltip-declutter 待并回): 133 处全量清点按 R1 复述 / R2 自明+无害 /
  R3 截断兜底 / R4 信息增量 / R5 不可发现交互+后果预告 五类判据判定, 移除 67 / 保留 66; 悬浮提示唯一
  通道仍是 shared/ui_feedback.js `.aq-tip` 拦截层, 移除 = 纯删 title 属性, 三皮肤零成对改; dialogs.js
  A5(statusbar 统计项)按报告「精简」只去复述半句。守阵: test_removed_redundant_tooltips_stay_removed
  (tests/test_web.py)断言代表性已删文案不写回。全量基线 [testing/baselines/26-10-04-0900](../../testing/baselines/attachments/26-10-04-0900-webui-tooltip-declutter.md);
  档案 [tasks/26-10-04-webui-tooltip-declutter](../../tasks/26-10-04-webui-tooltip-declutter.md)(Done)。

