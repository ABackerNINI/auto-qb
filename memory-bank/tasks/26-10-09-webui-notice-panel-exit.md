# 26-10-09-webui-notice-panel-exit — 空存储提示改道通知面板 + 面板改名「通知」

**Status:** Done
**Added:** 2026-10-09
**Updated:** 2026-10-09 11:37
**Topics:** webui-error-history
**Summary:** 用户报「WEBUI 把『本地址还没有列偏好记录』放入错误历史 —— 它会遮挡测试截图, 每次测试时都会触发; 同时把『错误历史』改为『通知』」。两件事一并做: ①该提示原先是 `columns.js::_showColsOriginHint` 运行时插进 `body` 的 **fixed 横幅**(可点关 / 15s 自灭), 出口改为**通知面板**内的陈述型条目(新单点 `ui_feedback.js::_recordNotice`, kind=`info` / source=`notice` / id 前缀 `n`, 与 toast、后端 errlog 两条来源同列、同 cap); 测试用全新浏览器上下文 ⇒ 无"已提示"去重标记, 于是**每次跑测试都弹**, 每张截图都被盖一截 —— 改道后面板默认收起, 只在状态栏入口留未读徽标。②面板用户可见文案一律「通知」(入口 title / 面板标题 / 空态 / 复制钮 label)——面板不只装错误(陈述型告知也进它), 再叫"错误历史"会把告知读成故障。内部标识符(`err-panel`/`_errHistory`/`errPanelOpen` 等)与后端错误环(`/api/errlog`)**不动** —— 守阵与后端语义都钉在它们上面, 改名收益为负。实测数字见基线切片 [26-10-09-1137](../testing/baselines/26-10-09-1137-webui-notice-panel-exit.md); 真浏览器三皮肤验证: 页面无浮层横幅 / 徽标 =1 / 面板标题「通知」/ 条目中性灰点 / 零 pageerror。
**Refs:** memory-bank/testing/baselines/26-10-09-1137-webui-notice-panel-exit.md,memory-bank/pitfalls/web-ui/floating-hint-vs-notice-panel.md,memory-bank/pitfalls/web-ui/columns-persist.md

## 原始请求

用户原文: 「WEBUI将"本地址还没有列偏好记录"放入"错误历史", 因为其会遮挡测试截图, 每次测试时都会触发. 同时将"错误历史"改为"通知"」

读法(本档案据以实施): 提示**已经**在"错误历史"里可查(它本就是一条告知), 用户真正要的是**它别再以浮层形态压在页面上、别再进截图** —— 括号里给的两个理由("遮挡测试截图" "每次测试都会触发")都只在说"浮层"这一形态; 后半句的面板改名正是把"面板 = 收通知的地方"定调。

## 思考过程与决策

- **形态才是病根, 不是文案**: 提示内容(事实 + 两条成因 + 自查路径)是 2026-09-24 取证后的定稿, 一字不改; 改的是**出口形态** —— fixed 横幅 ⇒ 面板条目。判据: 用户给的两个理由都指向"占了版面/进了截图", 与文案无关。
- **为什么不直接删提示**: 该提示承载"偏好为什么回默认"的排查入口(origin 隔离 / 浏览器站点级清站点数据, 前者客户端无法消除、后者客户端无法自检), 删掉等于把用户重新推回"这又是应用 bug"的老路([columns-persist](../pitfalls/web-ui/columns-persist.md) 是那条弯路的事故档案)。面板形态下信息量不变、成本归零。
- **新单点而非复用 toast**: 走 `toast()` 需要放宽 `ERR_HISTORY_KINDS`(否则 info 不入缓冲), 而放宽会把**全站 30+ 处 info toast** 一并灌进面板(量级灾难)。故新增 `_recordNotice(text)`: 只入缓冲、不弹条, kind 固定 `info`(中性灰点; 红点留给真故障), `source: 'notice'` 与 toast / backend 区分。
- **id 命名空间**: 条目 id 三方共存 —— 数字(toast)/ `b`+后端 seq / 新 `n`+前端 seq。`_recordErrorToast` 按 id upsert, 撞号会把两条无关条目并成一条, 故前缀必须错开。
- **改名只改可见文案 + 注释, 不动标识符**: `err-panel` / `.sb-err` / `_errHistory` / `errPanelOpen` / `ERR_HISTORY_CAP` 被静态守阵、e2e 与后端 `/api/errlog` 语义钉住; 改名的收益是"读起来对", 代价是全线返工与守阵重钉 —— 判为负收益。改名后**刻意留一处对照**(overlays.html / statusbar.html 注释里的「原『错误历史』」), 让后来者 grep 旧名能找到新位置。
- **后端不跟改**: `runtime.py` 的错误环 / `GET /api/errlog` 是**真错误日志**(WARNING+), 它喂给面板与本改名无关; 把它也叫"通知"反而错。前端面板 = 通知(多来源), 后端环 = 错误环(单来源)。
- **守阵补两条**: ①`test_frontend_notice_push_wired`(新单点三处接线: 写缓冲 / 计未读 / 不建 DOM); ②`test_frontend_cols_empty_hint_is_not_a_floating_banner`(提示里不得再出现 `document.createElement`/`appendChild`/`position:fixed`/`z-index:9999`), 并在既有入口守阵里钉住三处「通知」文案。
- **范围守恒**: 未动收集时机(emit 即收 + settle upsert)/ cap / 后端环 / 补拉定时器 / tooltip 让位 / Esc 退栈; 未动"清空"与未读清零语义; 未给面板加筛选或分级。

## 实现计划

单会话单步闭环: ① 读码定位提示的出口与面板结构 → ② `ui_feedback.js` 加 `_recordNotice` 单点 → ③ `columns.js` 提示改走它(去 DOM 注入) → ④ 面板可见文案改名(overlays/statusbar)+ 静态注释统一 → ⑤ 守阵新增/改写 → ⑥ 定向测试 → ⑦ 真浏览器验证(无浮层 / 徽标 / 面板 / 零 pageerror)+ e2e fast → ⑧ `test.full` → ⑨ 回写(档案 / 基线切片 / activeContext 切片 / progress / 坑档)+ `kb.index`。

## 子任务状态表

| # | 子任务 | 状态 | 产出 |
|---|---|---|---|
| S1 | 定位出口与形态 | ✅ | 提示在 `columns.js::_showColsOriginHint` 里自建 fixed 横幅(整条可点关 / 15s 自灭); 面板 `err-panel` 已是"多来源条目列表", 天然是陈述型通知的落点 |
| S2 | 通知收集单点 | ✅ | `ui_feedback.js::_recordNotice(text)` —— unshift + cap 裁剪 + 计未读, kind `info` / source `notice` / id `n`+seq |
| S3 | 提示改道 | ✅ | `_showColsOriginHint` 去 `createElement`/`style.cssText`/`appendChild`/`setTimeout`, 改 `this._recordNotice(<原文案>)`; sessionStorage + localStorage 两层去重标记原样保留 |
| S4 | 改名「通知」 | ✅ | overlays.html(aria-label / 面板标题 / 空态 / 复制 label)+ statusbar.html(入口 title); 前端 8 个 static 文件的注释一并统一(仅注释) |
| S5 | 守阵 | ✅ | 新增 `test_frontend_notice_push_wired`、`test_frontend_cols_empty_hint_is_not_a_floating_banner`; 既有入口守阵补三处「通知」文案断言 |
| S6 | 定向 + 全量 | ✅ | `test.one` 定向 36 passed; `test.full` 全绿 / 0 failed / TOTAL 99%(精确数字见基线切片 26-10-09-1137) |
| S7 | 真浏览器 + e2e | ✅ | 桩服务单皮肤: 浮层横幅计数 0 / 徽标 1 / 面板标题「通知」/ 行 `err-row info` / 文案逐字一致 / 零 pageerror; 面板开启后徽标清零; `dev.e2e` fast 子集 18 passed(含"无运行时错误"断言) |
| S8 | 收尾回写 | ✅ | 本档案 / 基线切片 / activeContext 切片 / progress / 坑档 / `columns-persist` 口径行; `kb.index` |

## 进度日志

- **2026-10-09 11:2x** 会话开工: 同步 `同步成功 812be13d`(620ec75b→812be13d)。读 `kb.active` + `pitfalls/web-ui/columns-persist.md` + 前端收集链(`ui_feedback.js` / `columns.js` / `overlays.html` / `statusbar.html` / `lifecycle.js`), 判定用户的病根是**浮层形态**而非文案, 且面板已是多来源列表 ⇒ 只需换出口 + 改名。
- **2026-10-09 11:3x** 落码 S2–S4: 新增 `_recordNotice`; `_showColsOriginHint` 改走它(去 DOM 注入, 去重标记与文案原样); 可见文案改「通知」, 前端 static 注释统一(仅注释、零逻辑); 后端错误环命名**不动**。
- **2026-10-09 11:3x** 守阵 S5: 新增 2 条 + 既有入口守阵补 3 条文案断言 + 两文件「测试计划」docstring 同步; `commands run test.one -- tests/test_webui_error_history.py tests/test_webui_static_dom_page.py` **36 passed**。
- **2026-10-09 11:3x** 真浏览器 S7(临时桩 `scripts/ui_harness.py --port 8138`, 脚本与截图在 `tmp-analysis/` 已删): `floatingBanner=0` / `badge="1"` / 面板开前 `err-panel` 计数 0 / 标题「通知」/ `err-row info` / 条目文案与源码逐字一致 / `pageErrors=[]`; 入口 title 经 `.aq-tip` 拦截层迁为 `data-aq-tip="通知"`(既有机制, 非本次改动); 截图目检确认页面无遮挡。`dev.e2e` fast 子集 **18 passed**(含 Vue 挂载与"无运行时错误"断言)。
- **2026-10-09 11:37** `commands run test.full` 全绿 / 0 failed / TOTAL 99%(精确数字见基线切片 [26-10-09-1137](../testing/baselines/26-10-09-1137-webui-notice-panel-exit.md)); 新坑写进 [floating-hint-vs-notice-panel](../pitfalls/web-ui/floating-hint-vs-notice-panel.md), [columns-persist](../pitfalls/web-ui/columns-persist.md) 的处置行同步(提示落通知面板); 本档案 + activeContext 切片 + `progress/implemented-webui.md` 回写; `kb.index` 重建。
