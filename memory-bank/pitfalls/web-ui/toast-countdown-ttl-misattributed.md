# toast 倒计时: 进度条走完了, 窗口还要再挂一会儿

> 摘要: 同一条提示条的进度条时长与退场定时器不同源 —— stamp 时用的是"整栈共用"的 ttl, 同一 tick 里先发出的归档条(4000)把 TTL 贴到了后推入的结果条(12000)上
> 触发: 进度条到了不消失, 倒计时条走完窗口还在, 时间指示条停在末尾, 强制重新汇报失败窗口不消失, --fx-life, data-fx-cd, toastSync ttl, 归档条 TTL 串条
**Refs:** memory-bank/conventions/webui.md(提示条队列 ⑤) · memory-bank/pitfalls/web-ui/toast-queue-pushin-overlap.md

### 失败回执条的进度条 4s 走完, 条却要等 12s 才消失

- **触发**: 任何**两段式**链路(归档条 + 结果条同一 tick 推入)且两条 TTL 不同: 强制重新汇报失败
  (归档 4000 / 结果 error floor 12000)、导出部分失败、删除前置汇报失败、转移失败。成功路径两条
  TTL 通常相同(4000/4000 或 3000/4000), 差得少, 肉眼看不出来 —— 所以只在**失败**分支暴露,
  报障原话「强制重新汇报失败的窗口时间指示条到了但没消失」。

- **判别**: 在页面里读失败回执条的 `style.getPropertyValue('--fx-life')` 与 `getAnimations()`
  里 `scaleX` 那条的 `duration` —— 踩中时两者都是 **4000ms**, 而该条的 `kind=error`
  (实际退场定时器 12000ms)。用 MutationObserver 记录节点移除时刻, 实测: 动画 `finished` 在
  t=5106ms, 节点消失 t=13013ms —— **中间 8 秒条挂在屏上, 进度条早已归零**。正常应是
  `--fx-life` 与退场同时刻(差 ~100ms = View Transitions 退场)。

- **根因**: `flux/fx-mount.js::toastSync(ttl, settleId)` 的 stamp 分支写的是
  `if (ttl > 0) 给**这个新节点**挂 data-fx-cd` —— ttl 是**整栈共用**的一个值, 谁先 stamp 谁拿。
  而 `_settleRunningToast` 是: `_finishToast(归档条, info, 4000)` → `toast(结果条, error, 12000)`,
  两处 `$nextTick(() => toastSync(...))` 按注册序执行 ⇒ 归档条那次调用(ttl=4000)先跑, 此时结果条
  已经渲染出来但还没 stamp, 于是 4000 落到它头上; 随后结果条自己那次调用(12000)看到
  `_fxToast` 已置位, 走"补挂"分支, 而补挂分支只认 settleId(本次没传) ⇒ 不再改。结果: 条 12s
  才移除, 进度条 4s 走完。
  九轮加 settleId 时只修了"补挂"一侧, **stamp 一侧的整栈 ttl 是同一类错的另一半**, 当时没报障
  是因为九轮只看了单条与同 TTL 的成功路径。

- **处置**: 让 ttl 与"这一条"绑死 ——
  ① `toastSync(ttl, id)`: 循环里先算 `own = data-id === id`(缺 id 时退化为栈尾, 只是兜底),
  stamp 分支**不再**按 `ttl > 0` 挂条, 与补挂分支合并成唯一一处 `if (own && ttl > 0) { … }`;
  ② 两个消费点都传本条 id: `toast()` → `toastSync(ttl, id)`(它本来就有 id, 此前漏传),
  `_finishToast()` → `toastSync(wait, id)`(已有);
  ③ sticky 条(ttl=0)照旧不挂 —— 归档成终态/「已投递」时才由 `_finishToast` 补上, 语义不变。
  修后实测: 归档条 4000 / 结果条 12000, 结果条在 11916/12000 时节点消失, 进度条终点 = 退场时刻。

- **守阵**: `tests/test_webui_static_skins_*.py::_scan_message_surface_parity` 第 20 项 —— 三条
  判据(都红验过): ① `var own = id != null` 与 `own && ttl > 0` 同时在档; ② `setAttribute("data-fx-cd"`
  **全文件唯一一处**(旁路 = 绕过归属判定); ③ `shared/ui_feedback.js` 里每个 `toastSync(...)`
  都必须两参且第二参是 `id`。静态守阵钉不住"两处时序谁先执行", 改这块仍需浏览器里看一次
  `--fx-life` 与节点移除时刻。

- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
