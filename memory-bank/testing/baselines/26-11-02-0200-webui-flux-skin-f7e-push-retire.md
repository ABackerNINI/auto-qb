# 4798 —— flux 精修轮 R5(F7e) push 位移弃用+面板上滑+上推过渡

> 摘要: flux 精修轮 R5(F7e) push 位移弃用+面板上滑+上推过渡
> 基线时间: 2026-11-02 02:00
**Refs:**

## 验收数字

`commands run test.full` 实测(2026-11-02 02:00, 本机):

```
[ok] test.full (153.2s)
  TOTAL                                                22482    182   7708    139    99%
  4798 passed, 10 skipped in 151.11s (0:02:31)
```

- 4798 passed / 10 skipped / 0 failed; 覆盖率 99%(TOTAL 22482, Miss 182)。
- 前置 `commands run test.quick`: 4798 passed, 10 skipped in 33.67s。
- 与上基线(26-11-02-0005, 4797)差 +1: fx_wiring 6b/6c 重写为 F7e 形态(push 退役反向钉 + 两段动效落点正向钉, 断言条数净 +1)。
- test_locking 10 skipped 为存量跳过口径, 无 flaky 重跑。

## 本改动面

- `src/auto_qb/webui/static/flux/fx-mount.js`: push 位移本体退役(dock 不再 stamp data-fx="push"/data-fx-pushed/--fx-push-y, RO/top 过渡 transitionend 拆除); 落定回执换锚到面板入场 transform 过渡(transitionend 主路 + PANEL_ENTER_MS+100ms 兜底, settleArmed 单发); dock(true) 挂 html.fx-glide(上推过渡窗口), fireSettle 后 800ms 摘。354→约 300 行内。
- `src/auto_qb/webui/static/flux/css/fx-mount.css`: push 载体两段(relative-top 覆盖 + top 过渡)删除, 改退役段注; no-preference 媒体块内新增 html.fx-glide { scroll-behavior: smooth }(F7e 动效② 上推过渡)。
- `src/auto_qb/webui/static/flux/css/dialogs.css`: 面板入场 translateY(-16px) 微移 → translateY(100%) 底部上滑, 时长/缓动消费 fx 令牌 var(--fx-dur-panel)/var(--fx-ease-out); 新增 prefers-reduced-motion 降级块(过渡归零)。
- `src/auto_qb/webui/static/shared/state.js`: drawerVisible watch 的 dock 回执注释改写(F7e 语义: 落定回执换锚 + 行目标 = drawer.hash); 代码本体零改动。
- `tests/test_webui_static_skins.py`: fx_wiring 6b(B4 载体正向钉)改 F7e 反向钉(mount_css/js 零 push 载体/stamp 代码形态); 6c 追加 settleArmed 单发守卫钉 + 两段动效落点钉(dialogs.css 上滑 + fx-glide); 文件头测试计划同步。
- `memory-bank/plans/26-10-31-2316-plan-webui-fx-skin.html`: §06 追加「精修轮 R5(F7e)」实录 + §10 变更记录 R11。
