# 2845 —— 06 变体逐行汇报倒计时真 per-tracker 口径 (计划 26-10-09-1243 / issue 26-10-07-0149)

> 摘要: 06 变体逐行汇报倒计时从「种子级 `detail.reannounce_in` 全局近似」升级为「行级 `next_announce`(qB 5.2+ 随 /trackers 透传, epoch 秒)减 nowSec」后的收尾基线。改动 1 个前端变体(`06-trackers-table-collapsed.js`: `nextHtml` 读行级 `next_announce` + 减 `nowSec` / 去「全局」标 / 去微条; 缺字段回退旧全局近似; `nowSec` 计入 sig) + 1 桩(`scripts/ui_harness.py::_make_trackers_response`) + 新增静态守阵 1 条(红验确认) + e2e 1 条(双皮肤)。后端零改动。
> 档案: memory-bank/tasks/26-10-09-webui-per-tracker-reannounce.md
> 基线时间: 2026-10-09 13:00

**Refs:** memory-bank/tasks/26-10-09-webui-per-tracker-reannounce.md

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2845 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**(16553 语句 / 169 未覆盖 / 5708 分支 / 145 partial; 门槛 98% 达标)
- **耗时**: 42.37s(命令墙时 44.4s)
- **新增用例 1 条**: `tests/test_webui_static_dom_panel.py::test_drawer_tpl_trackers_per_tracker_reannounce`(6 断言: 读行级 next_announce / epoch 减 nowSec / 「全局」标只在回退分支 / 回退分支仍在 / nowSec 计入 sig / 真口径不画微条 / 调用点传参)。
- **红验**: 临时把 sig 里的 `nowSec` 改坏(`nowSec` → `nowSecX`)后该守阵转红(断言「06 未把 nowSec 计入 sig」), 还原复绿 —— 证守卫非恒真。
- **e2e**: `e2e/drawer-trackers-reannounce.spec.mjs` 双皮肤(prism / atlas)@fast 实测 2 passed(逐行倒计时 ≥2 行且互不相同 + 无「全局」标)。

## 说明

- **相对上基线的参考**: 要看差值跑 `commands run kb.baseline -n 2`。
- **代码事实变更**: 有 —— `06-trackers-table-collapsed.js::nextHtml(ctx)` → `nextHtml(ctx, t, nowSec)`; 真口径分支读行级 `t.next_announce` 减 `nowSec`、去「全局」标(`dt06-gb`)、去微条(`dt06-tbar`); 缺字段回退种子级 `detail.reannounce_in` 全局近似(旧路径保留); `render()` 的 sig 追加 `nowSec`。后端 `/api/torrents/{hash}/trackers` 与 `mask_tracker_entry` 零改动。
- **正确性依据**: `next_announce` 是 qB 5.2+(WebAPI 2.13.0)随 `/trackers` 透传的 **Unix epoch 绝对秒**(出处 reports/26-10-05-0854 §4.1), 必须先减 `now` 再格式化(epoch 当倒计时是已记录事故根因); per-tracker interval 不可得故不画微条(不造假)。见计划 26-10-09-1243 §03。
