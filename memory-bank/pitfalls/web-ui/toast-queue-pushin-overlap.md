# toast 队列: 加了 FLIP 反而与让位中的旧条叠画

> 摘要: 给底部锚定的提示条栈补了 FLIP 之后, 新条仍走「原地淡入」, 于是旧条还没让开、新条已经落在同一块地方 —— 重叠是入场形态的锅, 不是 FLIP 的锅
> 触发: toast 重叠, 队列重排, FLIP, 叠画, 新条入场, 顶掉, 提示条重叠, 强制汇报两个窗口, 队列推入, data-fx-queue
**Refs:** memory-bank/conventions/webui.md(提示条队列段) · memory-bank/pitfalls/web-ui/flip-bottom-anchored-stack.md

### 第二条提示条推入时, 与正在上移让位的旧条同帧叠画(最多叠满一整条)

- **触发**: 任何往右下角提示条栈里推**第二条**的路径 —— 强制重新汇报的回执条推入、连点两个操作、
  一条 sticky 等待条还挂着时又来一条回执。单条场景永远踩不到, 所以先自测"推一条"会漏。

- **判别**: 逐帧采样两条的 rect(见下面对话里的 `overlap.mjs` 写法), 算 `上条.bottom - 下条.top`:
  正常应是 **-8**(栈间距 8px), 踩中时会出现若干帧 **+49**(= 旧条整个高度)。
  两个假线索别被骗: ① 稳定态两条间距是对的(动画只持续 ~200ms, 截稳定图看不出来);
  ② `getAnimations()` 里**确实有** translate 关键帧 —— FLIP 播了, 可重叠照旧。

- **根因**: FLIP 的正确姿势是"旧条先定格在旧位置, 再滑向新位置", 所以旧条在动画期间**仍然占着**
  新条要落的那一格; 而新条若走原地入场(`fx-toast-rise` 只下移 10px), 它就落进那一格里。
  几何上看: 旧条 845→779, 新条一入场就是 845, 两者在 t=0 完全重合, 只有等旧条滑走才分开。

- **处置**: 让新条**从下方一整格起步**(自身高度 + 栈间距), 与旧条上移同速, 间距全程恒定:
  ① `flux/fx-mount.js::toastSync` 对"栈里已有其它条"的新节点盖 `data-fx-queue`
  (`if (nodes.length > 1) n.setAttribute("data-fx-queue", "")`; 首条不盖 —— 单条没有让位需求);
  ② `flux/css/fx-mount.css` 给 `[data-fx-queue]` 覆盖入场动画为 `fx-toast-queue-in`
  (`from { opacity:0; transform: translateY(calc(100% + 8px)) }`) + `90ms` 延迟 + `backwards`
  (延迟期保持首帧透明, 不闪出实体);
  ③ danger 队列条要带上 `fx-danger-glow` 双动画, 否则失败回执推入时丢了危险辉光。
  验证口径: 逐帧 `overlap` 全为负(实测 46 帧全部 -8)。

- **守阵**: `tests/test_webui_static_skins.py::_scan_message_surface_parity` 第 20 项 —— 钉
  `@keyframes fx-toast-queue-in` 存在、`[data-fx-queue]` 规则存在、JS 里 `setAttribute("data-fx-queue"` 盖章
  (三条都红验过: 摘掉任一条精确报红, 还原后绿)。静态守阵看不出"动画参数够不够", 改动画幅度时仍要跑一次逐帧采样。

- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
