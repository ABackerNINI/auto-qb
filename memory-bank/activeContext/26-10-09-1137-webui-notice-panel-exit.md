# 空存储提示改道通知面板 + 面板改名「通知」 · 已闭环

> 摘要: 用户报「WEBUI 把『本地址还没有列偏好记录』放入错误历史 —— 它会遮挡测试截图, 每次测试时都会触发; 同时把『错误历史』改为『通知』」。判为**形态**病根而非文案: 该提示原是 `columns.js::_showColsOriginHint` 往 `body` 插的 fixed 横幅(可点关 / 15s 自灭), 测试用全新浏览器上下文 ⇒ 无"已提示"去重标记 ⇒ 每次跑测试都弹、每张截图都被盖一截。修法 = 新增陈述型通知单点 `ui_feedback.js::_recordNotice`(kind `info` / source `notice` / id `n`+seq, 与 toast、后端 errlog 同列同 cap), 提示改走它 —— 面板默认收起, 只在状态栏入口留未读徽标; 文案与两层去重标记一字未动。面板可见文案统一改「通知」(入口 title / 面板标题 / 空态 / 复制 label), 理由 = 面板不只装错误(陈述型告知也进它)。**内部标识符与后端错误环(`/api/errlog`)不动** —— 守阵与后端语义钉在旧名上, 改名收益为负。
>
> 最后活动: 2026-10-09 11:37

**Refs:** memory-bank/tasks/26-10-09-webui-notice-panel-exit.md,memory-bank/pitfalls/web-ui/floating-hint-vs-notice-panel.md,memory-bank/testing/baselines/26-10-09-1137-webui-notice-panel-exit.md

## 本轮完成

- **`shared/ui_feedback.js`**: 新增 `_recordNotice(text)` 收集单点(unshift + `ERR_HISTORY_CAP` 裁剪 + 计未读); kind 固定 `info`(中性灰点, 红点留给真故障), `source: "notice"`, id 前缀 `n` 与数字 toast id、`b`+后端 seq 三方错开(upsert 按 id 去重)。**未放宽 `ERR_HISTORY_KINDS`** —— 放宽会把全站 info toast 一并灌进面板。
- **`shared/columns.js`**: `_showColsOriginHint` 去掉 `document.createElement` / `style.cssText` / `appendChild` / `setTimeout`, 改 `this._recordNotice(<原文案>)`; sessionStorage + localStorage 两层去重标记保留。
- **模板改名**: `tpl/overlays.html`(aria-label / `.err-hd-t` 标题 / 空态 / 复制钮 label)+ `tpl/statusbar.html`(入口 title)改「通知」; 改名理由写进两处注释并留「原『错误历史』」对照, 让 grep 旧名能找到新位置。
- **注释统一**: 前端 `static/shared/` 8 个文件里的 `错误历史` → `通知`(纯注释, 零逻辑); 后端 `runtime.py` / `routes/system.py` 的**错误环**命名保留(它是真错误日志 WARNING+, 与本改名无关)。
- **守阵**: 新增 `tests/test_webui_error_history.py::test_frontend_notice_push_wired`(单点三处接线 + 不得建 DOM)与 `tests/test_webui_static_dom_page.py::test_frontend_cols_empty_hint_is_not_a_floating_banner`(提示里禁 `createElement`/`appendChild`/`position:fixed`/`z-index:9999`); 既有入口守阵补三处「通知」文案断言; 两文件「测试计划」docstring 同步。
- **验证**: 定向 36 passed(见 [档案](../tasks/26-10-09-webui-notice-panel-exit.md) 子任务表); 真浏览器(桩服务)浮层横幅计数 0 / 徽标 1 / 面板标题「通知」/ 行 `err-row info` / 文案逐字一致 / 零 pageerror, 截图目检页面无遮挡; `dev.e2e` fast 子集全绿(含"无运行时错误"断言)。实测数字见 `commands run kb.baseline`。

## 待办 / 移交

- **面板内条目暂不分级/不筛选**: 通知面板现在混装 error/timeout toast、后端错误环、陈述型通知三类, 靠色点区分(error 红 / warn 黄 / info 灰)。若日后条目量上来, 再议分级或过滤。
- **`_recordNotice` 是"陈述型提示"的唯一出口**: 今后凡"告知类"前端提示一律走它, 不要再自建页面浮层(理由见坑档 [floating-hint-vs-notice-panel](../pitfalls/web-ui/floating-hint-vs-notice-panel.md))。
- 无代码遗留。
