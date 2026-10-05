# WEBUI 错误历史计划: 认领 issue 26-10-05-2013 + 分步实施计划(含 3 可交互模板)

> 摘要: 用户指派认领 issue 26-10-05-2013(feat: 右下角 toast 退场即销毁, 错过后无处可查),
> 出分步实施计划 [26-10-05-2026](../plans/26-10-05-2026-plan-webui-toast-error-history.html)(Open 待拍板)。
> 口径按 issue §06 完整方案 + 用户本轮「收 error」拍板: toast()/_finishToast() 双钩子收 error+timeout
> 进会话内环形缓冲(cap 50, upsert by id), auth.js 零改动(历史跨重连存活), 前端零持久化/零新配置键;
> 入口+面板全走 shared 层(overlays.html + console_hub.css, 三皮肤零清单改动自动生效)。
> 计划同时交付 3 个**完全可交互**入口模板(T1 toast 同域浮空钮 / T2 状态栏徽标+上拉面板 / T3 顶栏铃铛下拉,
> 演示含触发错误→toast 退场入历史→未读徽标→面板复制/清空/模拟重连)供 D1 拍板, 推荐 T2;
> D2 = SSE 断线沿发 error toast 作事件源(推荐采纳, 可跳)。
> **21:43 范围修订**(用户复审拍板「按推荐更新文档」): 挂机场景「浏览器关闭才是常态」, 纯前端缓冲对关闭期
> 零覆盖 → 增补后端 WARNING+ 内存错误环(tray UiLogHandler 同款范式) + /api/errlog 增量端点 + 前端
> boot 合并(不计未读)/60s 补拉(计未读)/游标回退检测, 条目加 source 字段; 步骤重排 S1-S8(新增 S2 后端环
> +端点 / S3 boot 合并), 守阵 5+4 条 + 红验; 不做清单拆分重写(持久化/通用日志查看器维持不做)。
> 用户报「演示控制点击无反应」已修: mount 以 .demo-app 为根找控制钮, 但 .demo-ctl 是卡片级兄弟不在其子树,
> 按钮从未绑上事件 —— 改回 .tpl-card 根上查找; 真浏览器(内置 IAB + 临时 HTTP 服务)全链走查通过
> (触发/徽标/面板/复制/清空/连发/模拟重连/T3/拍板标记)。
> 最后活动: 2026-10-05 21:43

**Refs:** memory-bank/issues/26-10-05-2013-feat-webui-toast-error-history.html, memory-bank/plans/26-10-05-2026-plan-webui-toast-error-history.html

## 现状

- **计划已交付, 待拍板 D1(模板三选一)/D2(断线事件源)**, 未动任何生产代码。
- 复验(20:26, HEAD 2130450c): issue 六锚点全部复现; 认领面新增 9 条实施事实已写进计划 §02 ——
  关键三条: ①sticky 结算链(`_finishToast`, 3 文件 8 调用点)是第二收集必经点, 只钩 toast() 会漏
  强制汇报超时/批量删除未完全成功; ②overlays.html 已在三皮肤 tpl-manifest(`into: app`) → 面板零清单改动;
  ③复制直接复用 commands.js:660 `copyText`(模板安全封装)。
- 口径要点(计划 §03): timeout kind 在本库实际语义 = 「超时/未完全成功终态」, 与 error 同收
  (issue §06 倾向句「busy 结算出的超时/失败终态」); 严格 error-only 则删 KINDS 一个键。
  收集时机 = **发出即收**而非 issue 原建议的「退场时追加」—— auth.js:68 `this.toasts = []` 绕过
  _dropToast, 挂退场会漏重连前最后一批错误(挂机型最需要追溯的一批)。
- issue 侧已同步: 状态 Open → In Progress(meta+徽标两处) + doc-refs 双向声明 + 状态日志 + 复验行。
- **21:43 范围修订回写**(同轮提交): §02 修正 issue「无处可查」证据 —— /api/log(system.py:19)与
  FE-2C 日志弹窗(dialogs.js:411)/设置页运行日志块(config_hub.js:402)早已存在, 原取证漏扫
  server/routes/; 浏览器关闭期错误主体 = core 自治日志点 102 处/10 文件(实测 grep) + 命令回执
  WEB_RESULT_TTL=120s/64 条(runtime.py:56)随 JS 丢失无补取。issue §02 修正条 + §07 状态日志同步,
  plans/_index.md 标题同步; 两份 HTML 标签配平复核通过(li 56/56, tr 53/53)。
- 下一步: 用户回复 D1/D2 拍板 → 按 §05 S1-S8 实施(每步一笔提交, S4 按 D1 选定模板落挂点)。
