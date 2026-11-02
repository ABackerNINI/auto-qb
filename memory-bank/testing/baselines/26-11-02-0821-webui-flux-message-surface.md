# 4823 —— 提示条上移状态栏 + 队列重排 FLIP + 强制汇报两态统一后全量

> 摘要: 提示条上移状态栏 + 队列重排 FLIP + 强制汇报两态统一后全量
> 基线时间: 2026-11-02 08:21
**Refs:** memory-bank/testing/baselines/26-11-02-0750-webui-flux-message-surface.md

## 验收数字

`commands run test.full` 实测(2026-11-02 08:18, 八轮: 状态栏让位 + 队列 FLIP + 两态同高):

```text
TOTAL                                                22521    152   7726    135    99%
4823 passed, 10 skipped in 235.37s (0:03:55)
```

- 口径注记: 10 skipped 为既有跳过面(平台条件跳过, 与本轮改动无关); 覆盖率 99%。
- 守阵 `tests/test_webui_static_skins.py` 26 passed: 第 20 项新增两条 —— `.toast-wrap` 的 `bottom`
  必须含 `var(--statusbar-h`(压回状态栏即红)、`fx-mount.js` 里 `flipStack();` 至少两处
  (插入/退场各一, 少一处 = 有一侧回到瞬移)。红验两条各精确报红、还原后绿。
- 布局面实测(桩服务 + Playwright, 1440×950): 状态栏顶 916 / 高 34; 单条提示条 bottom = 904
  (12px 呼吸位, 不进状态栏); 两条同时在场时 gap = 8、最低边仍 904; 等待态与回执态**同为 59px**。
- 动效面实测: 插入第二条时, 现存条 `getAnimations()` 拿到 `translate` 关键帧且当帧仍在旧位置
  (FLIP 生效, 不是瞬移); 结算换文案时拿到 `height` 关键帧(高度形变)。
- e2e 同步验证: `commands run dev.e2e -- e2e/site-alerts.spec.mjs -g "命令结果图标"` → 2 passed
  (prism/atlas, 该用例断言回执文案 `强制重新汇报: 成功 2, 失败 1, 未确认 0`, 本轮未改这句)。

## 本改动面

- `flux/css/components.css`(维持 700 行): `.toast-wrap` 的 `bottom: 20px` → `calc(var(--statusbar-h,
  34px) + 12px)` —— 提示条坐在状态栏之上(用户八轮「通知挡住了状态栏, 上移」), 与 `.err-panel`(+8)同族。
- `flux/fx-mount.js`: 新增 `flipStack()`(D6-3 队列重排 FLIP), 在 `toastSync`(插入/结算)与
  `toastDrop`(退场, 非 VT 分支的 rAF 里)各调一次。量位置用**视口坐标**并先 cancel 自己上一轮的
  WAAPI 动画(底部锚定栈里 `offsetTop` 恒 0, 用它 FLIP 会静默不播 —— 见
  pitfalls/web-ui/flip-bottom-anchored-stack.md); 自身高度变化补 `height` 关键帧, 邻居进出补
  `transform: translateY(dy) → 0`; RM/无 WAAPI 只记位不动画。
- `shared/commands.js`: 强制汇报两态(等待/已投递 → 成功)文案压成「标题 + 一行说明」并统一措辞到
  菜单名「强制重新汇报」(此前等待态叫「强制汇报」、回执态叫「强制重新汇报」, 措辞与盒子高度都不一致):
  等待态 76px(说明折两行) → 59px, 与回执态同高, 结算不再"两个窗口叠一下"。
  `plan.skipped` 分支同样一行:「强制重新汇报已投递: N 个活跃目标, 跳过 M 个非活跃」。
- `shared/delete_flow.js`: 删除前置汇报的等待/完成文案同步成「强制重新汇报进行中 / 完成」(同一动作
  同一套措辞)。
- `fx/showcase.html`: D6-3 卡片补 `adopted` 字段并在卡面渲染「生产」行(与生产的差别写明: 不走 VT
  快照, 改为挂载层 FLIP)。
- `tests/test_webui_static_skins.py`: 第 20 项补位置与队列两条断言; `.toast-wrap` 纳入规则收集。
- `memory-bank`: 新增坑档 `pitfalls/web-ui/flip-bottom-anchored-stack.md`(底部锚定栈不能用 offsetTop,
  含判别方法), `conventions/webui.md` 增「提示条栈: 状态栏之上 + 队列重排 FLIP + 两态同高」段。
