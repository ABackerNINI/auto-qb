# 4455 —— flux 精修轮 R1 四回归修复

> 摘要: flux 精修轮 R1 四回归修复
> 基线时间: 2026-11-01 21:09
**Refs:**

## 验收数字

`commands run test.full` 实测(2026-11-01 21:07, 本机):

```
[ok] test.full (112.7s)
  TOTAL                                                22482    197   7708   155    99%
  4455 passed, 10 skipped in 110.62s (0:01:50)
```

- 4455 passed / 10 skipped / 0 failed; 覆盖率 99%(TOTAL 22482, Miss 197)。
- 前置 `commands run test.quick`: 4455 passed, 10 skipped in 29.07s。
- 比上基线(4454)多 1 条 = 新增守阵 `test_frontend_console_square_radius`(B1 console 方角口径); fx_wiring 扩 6a/6b/6c 三判据(R1 四 bug 回归钉)。
- test_locking 10 skipped 为存量跳过口径, 无 flaky 重跑。

## 本改动面

- `src/auto_qb/webui/static/flux/css/fx-mount.css`: B2(D4-1 行板 hover gradient 让位 row_lang 单点, 换墓碑注释)/ B4(push 载体 relative-top 覆盖三件: 媒体块外静态几何 `position:relative; top:0` + `[data-fx-pushed]` `transform:none; top:calc(-1*--fx-push-y)`, 媒体块内 top 过渡)。
- `src/auto_qb/webui/static/flux/fx-mount.js`: B3(选中/聚焦行可视区回拉 `ensureFocusedVisible`: 终态几何解算, 滚动可行域优先、滚动救不回时裁剪 push 量; `scheduleReveal` 短窗 rAF 循环覆盖 top 过渡全程; 挂 `applyPush`/`dock(false)` 两路径; `AQB_FX_MOUNT.revealFocusedRow` 暴露单点)。
- `tests/test_webui_static_skins.py`: 新增 `test_frontend_console_square_radius`(B1: console --radius 三令牌 0px + console 自有 CSS 与四件共享面 border-radius 声明值白名单, 红绿双验); `test_frontend_fx_wiring` 扩判据 6a/6b/6c(B2 墓碑/B4 载体三件/B3 回拉机构); 头部测试计划同步。
- 三旧皮肤(atlas/prism)/console/shared(除上述零涉及)/showcase/config.yml/auto-qb-data 零改动(git status 证实: 仅 flux 两文件 + 本测试文件)。
