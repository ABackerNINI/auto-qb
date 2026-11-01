# 4797 —— flux 精修轮 R3 圆角回退+push 回原版滚动

> 摘要: flux 精修轮 R3 圆角回退+push 回原版滚动
> 基线时间: 2026-11-02 00:05
**Refs:**

## 验收数字

`commands run test.full` 实测(2026-11-02 00:03, 本机):

```
[ok] test.full (114.3s)
  TOTAL                                                22482    182   7708    139    99%
  4797 passed, 10 skipped in 112.15s (0:01:52)
```

- 4797 passed / 10 skipped / 0 failed; 覆盖率 99%(TOTAL 22482, Miss 182)。
- 前置 `commands run test.quick`: 4797 passed, 10 skipped in 31.54s。
- 与上基线(26-11-01-2211, 4797)同数: 本轮零新增用例 —— fx_wiring 6c 判据改写(正向在档钉 → F7c 反向钉, 断言条数持平)。
- test_locking 10 skipped 为存量跳过口径, 无 flaky 重跑。

## 本改动面

- `src/auto_qb/webui/static/flux/style.css`: --radius 三档令牌 16/10/6 → 0px(S5「柔和曲线」形状改写退役, 覆盖共享 CSS 令牌消费面; 头注同步)。
- `src/auto_qb/webui/static/flux/css/components.css`: .site-chip 回 clip-path 3px 切角 / .modal 回 clip-path 14px(blur 保留)/ f-cell 注释回 console 原文。
- `src/auto_qb/webui/static/flux/css/dialogs.css`: .add-drop-box / .speed-pop 回 clip-path 14px 切角。
- `src/auto_qb/webui/static/flux/fx-mount.js`: 415→317 行 —— F7a 滚动干预整体退役(ensureFocusedVisible/focusedRow/scheduleReveal/revealFocusedRow/短窗循环), dock/applyPush 回 S6b 原形, push 纯过渡, 滚动单点交还 shared/shortcuts.js::_kbRevealRow。
- `tests/test_webui_static_skins.py`: fx_wiring 6c 改反向钉(三符号出现即红 + --fx-push-y 在档), 文件头测试计划同步; console 方角守阵 docstring 过时表述(flux 圆角三档)改写。
- `memory-bank/plans/26-10-31-2316-plan-webui-fx-skin.html`: §06 追加「精修轮 R3」实录。
