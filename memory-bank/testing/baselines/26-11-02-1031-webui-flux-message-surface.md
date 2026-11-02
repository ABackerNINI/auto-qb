# 4823 —— toast 倒计时按 id 归属(失败回执条进度条走完却不消失)后全量

> 摘要: toast 倒计时按 id 归属(失败回执条进度条走完却不消失)后全量
> 基线时间: 2026-11-02 10:31
**Refs:** memory-bank/testing/baselines/26-11-02-0947-webui-flux-message-surface.md

## 验收数字

`commands run test.full` 实测(2026-11-02 10:31, 十一轮: 倒计时条按 id 挂载):

```text
TOTAL                                                22521    152   7726    135    99%
4823 passed, 10 skipped in 174.95s (0:02:54)
```

- 口径注记: 10 skipped 与覆盖率 99% 均与十轮相同(无新增用例, 只加判据)。
- 守阵 `tests/test_webui_static_skins.py` 26 passed: 第 20 项在十轮三判据之后追加倒计时归属三条 ——
  ① `var own = id != null` + `own && ttl > 0` 同时在档; ② `setAttribute("data-fx-cd"` 全文件**唯一一处**;
  ③ `shared/ui_feedback.js` 每个 `toastSync(...)` 都两参且第二参是 `id`。
  红验: 把 `own && ttl > 0` 改成 `ttl > 0`、`var own = id != null` 改成 `var own = true` →
  精确报红(「倒计时没按 data-id 命中本条…用户看到「时间指示条到了但窗口不消失」」), 还原后绿。

## 报障与根因

- 报障(用户): 「强制重新汇报失败的窗口时间指示条到了但没消失」。
- 时间线取证(桩服务 + Playwright 1440×900, 触发 `_runningToast` + `_settleRunningToast(error)`):

```text
t=1003ms  id1[4000ms cd] 强制重新汇报已投递: 2 个目标
          id2[4000ms cd] 强制重新汇报: 成功 0, 失败 2, 未确认 0 (…)   <-- 应是 12000ms
t=5106ms  id1 已退场; id2 的 scaleX 动画 playState=finished, currentTime=4000/4000
t=13013ms id2 才被移除(12s = error 档 floor)
```

- 根因: `flux/fx-mount.js::toastSync` 的 **stamp 分支**用「整栈共用」的 ttl 给所有未挂载的新节点挂
  `data-fx-cd`。`_settleRunningToast` 在同一 tick 里先 `_finishToast(归档条, info, 4000)`、再
  `toast(结果条, error, 12000)` —— 两份 `$nextTick` 按注册序执行 ⇒ 4000 先落到已渲染但未 stamp 的
  结果条上; 结果条自己那次调用(12000)看到 `_fxToast` 已置位 ⇒ 只走补挂分支, 而补挂只认 settleId
  (本次没传) ⇒ 不再改。九轮加 settleId 时只修了「补挂」一侧, stamp 一侧是同一类错的另一半;
  九轮只验了单条与同 TTL 的成功路径, 失败分支(4000 vs 12000)才暴露。

## 本改动面

- `flux/fx-mount.js`: `toastSync(ttl, id)` —— 循环内先算 `own = data-id === id`(缺 id 退化为栈尾,
  仅兜底); stamp 分支不再按 `ttl > 0` 挂条, 与补挂分支合并成唯一一处 `if (own && ttl > 0) { … }`
  (含 `--fx-life` 覆写 + 摘标记 + 强制回流重播)。注释记录十一轮报障、实测时刻与"为什么只修补挂不够"。
- `shared/ui_feedback.js`: `toast()` 的 `toastSync(ttl)` → `toastSync(ttl, id)`(此前漏传第二参);
  `_finishToast` 注释同步(settleId → 本条 id 语义)。
- `tests/test_webui_static_skins.py`: 第 20 项追加倒计时归属三条判据 + 注释(含实测数字)。
- `memory-bank`: `conventions/webui.md` 提示条队列 ⑤ 整条改写(两入口都传 id / own 守卫 / 十一轮根因)、
  新增 `pitfalls/web-ui/toast-countdown-ttl-misattributed.md` 与 `_index.md` 索引行。

## 渲染面复验(浏览器实测, 桩服务 8137)

| 场景 | 归档条 | 结果条 | 结果 |
| --- | --- | --- | --- |
| 两段式 error(报障路径) | 4000 → t=5.0s 退场 | **12000** → t=13.0s 退场, 动画 11916/12000 时节点消失 | 进度条终点 = 退场时刻 |
| 两段式 ok(3000) | 4000 → t=5.0s | 3000 → t=4.0s | 各归各位 |
| 单条 error(6000 传参) | — | 12000 → t=12.1s | floor 生效 |
| sticky 进行中条 | 无 `data-fx-cd` | — | 按设计不给倒计时 |
| 真实链路 `_actCore('reannounce')`(桩 ok) | id1 投递条 t=18ms 入 / t=5.0s 退 | id2 回执 t=915ms 入 / t=4.0s 退 | 两条并存, TTL 各自正确 |

View Transitions 退场额外占 ~100ms(实测 vt-start 3012 / removed 3114 / vt-finished 3442),
是"进度条归零到节点消失"的固定余量, 非错位。
