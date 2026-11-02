# 4823 —— toast 队列: 强制汇报两段消息 + 推入不叠画后全量

> 摘要: toast 队列: 强制汇报两段消息 + 推入不叠画后全量
> 基线时间: 2026-11-02 09:11
**Refs:** memory-bank/testing/baselines/26-11-02-0821-webui-flux-message-surface.md

## 验收数字

`commands run test.full` 实测(2026-11-02 09:11, 九轮: 强制汇报拆两段 + 队列推入不叠画):

```text
TOTAL                                                22521    152   7726    135    99%
4823 passed, 10 skipped in 271.83s (0:04:31)
```

- 口径注记: 10 skipped 为既有跳过面(平台条件跳过, 与本轮改动无关); 覆盖率 99%。
- 守阵 `tests/test_webui_static_skins.py` 26 passed: 第 20 项追加五条 —— `fx-toast-queue-in`
  关键帧存在、`[data-fx-queue]` 规则存在、JS 给栈内新条盖 `data-fx-queue`、投递条不许自称
  「等待中」(`强制重新汇报等待中` 出现即红)、`_settleDeliveredToast(reToast)` 至少两处调用。
  红验五种破坏形态各精确报红、还原后绿(摘关键帧 / 摘规则 / JS 不盖章 / 改回等待中 / 回执退回原位改字)。

## 实测(桩服务 + Playwright, 1440×950, 真实右键手势)

- **修前时间线**: 投递条 t=1077ms 出现 → t=1608ms **同一节点**被改成回执文案 —— 只活 531ms,
  队列里始终 n=1。这就是用户报的「第一个窗口被第二个顶掉, 仅显示不到 1 秒, 没有做到队列重排」。
- **修后时间线**: 投递条 1126ms 出现 → 2021ms 归档成 `info`(895ms, 命中 900ms 最短展示保护) →
  2027ms 回执条推入, **n=2**。
- **重叠帧**: 逐帧采样 `上条.bottom - 下条.top`, 改前 5 帧为正(最大 49px = 旧条整个高度),
  改后 **46 帧全为 -8**(栈间距恒定)。
- **稳定态**: 投递条 `info` / `--fx-life: 4000ms` / 倒计时条已挂; 回执条 `ok` / `3000ms`;
  gap = 8; 最低边 904(状态栏顶 916, 不遮挡)。
- **退场**: 回执条 3s 到期退出后, 投递条回落到底锚位; 4s 后清空(剩余 0 条)。

## 本改动面

- `shared/commands.js`: 强制汇报的「已投递」与「回执」拆成**两条消息** —— 投递条 `busy` 起步,
  回执到来时经 `_settleDeliveredToast(ref, minShow=900, ttl=4000)` 归档成中性 `info` 并**留在队列里**,
  回执**另起** `toast()`。`reToast` 句柄提到 `try` 外, `catch` 里也收口(sticky 条不结账会永远挂屏)。
  投递文案统一成「强制重新汇报已投递: N 个目标, tracker 确认中」(归档后仍成立, 不写「等待中」);
  回执文案去掉重复的跳过数、补目标数(「强制重新汇报成功: tracker 已确认 N 个目标」)。
- `flux/fx-mount.js`: `toastSync(ttl, settleId)` 增加第二参 —— 按 `data-id` 把结算后的 TTL 精确补到
  被结算的那一条(`--fx-life` + `data-fx-cd`, 变时长要摘标记 + 强制回流重播)。栈内新条盖 `data-fx-queue`。
- `flux/css/fx-mount.css`: 新增 `fx-toast-queue-in` 关键帧(`translateY(calc(100% + 8px))` 起步)与
  `[data-fx-queue]` 规则(90ms 延迟 + `backwards`), 含 danger 双动画变体。
- `shared/tpl/overlays.html`: `.toast` 加 `:data-id="t.id"`(纯属性, 四皮肤同模板, 无视觉影响)。
- `shared/ui_feedback.js`: `_finishToast` 调 `toastSync(wait, id)`。
- `fx/showcase.html`: D6-3 卡片 `adopted` 补九轮两处口径(推入侧 + 消息侧)。
- `e2e/site-alerts.spec.mjs`: 聚合回执断言前加 `expect.poll` 等回执条落定(行图标在回执处理中途就落,
  900ms 最短展示让"读 toasts 那一刻它已在数组里"不再成立)。
- `tests/test_webui_static_skins.py`: 第 20 项补五条队列口径。
- `memory-bank`: 新增坑档 `pitfalls/web-ui/toast-queue-pushin-overlap.md`(FLIP 反而制造重叠, 含逐帧判别),
  `conventions/webui.md` 的「提示条栈」段整段改写(八轮的"同一条两个状态"是被否方案, 不能留)。

## e2e 同步

- `commands run dev.e2e -- e2e/site-alerts.spec.mjs -g "命令结果图标"` → **2 passed**(prism/atlas)。
- `commands run dev.e2e -- e2e/menus.spec.mjs -g "块E"` → **8 passed**(prism/atlas: 非活跃置灰 / 混选放行 /
  删除确认框两例)。
- `commands run dev.e2e -- e2e/menus.spec.mjs -g "W4 多选导出|W2 批量限速"` → **4 passed**。
