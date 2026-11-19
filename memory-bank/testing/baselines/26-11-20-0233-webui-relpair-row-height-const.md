# 6472 —— 行高恒等修正批: relpair负margin锁行高

> 摘要: 行高恒等修正批: relpair负margin锁行高
> 基线时间: 2026-11-20 02:33

## 验收数字

TOTAL                                                28929    195  10326     81    99%
6472 passed, 23 skipped, 7 warnings in 103.79s (0:01:43)

`commands run test.full` 实测(2026-11-20 02:33, 本机 Linux, 覆盖率 99% 达标)。e2e 面(同批实测): 新守阵 relocate-pair-row-height.spec 四皮肤 4 passed(SKINS_ALL, ~30s), relocate 族回归 pair-filter/pop-terminal 4 passed + key-change-pad(E2E_TORRENTS=400 抬档)1 passed, 红验(摘修正)四皮肤全红判别力在案。

## 本改动面

- `src/auto_qb/webui/static/shared/row_lang.css`: `.has-relpair` 加 `margin: -5px 0`(负 margin 吃上下 padding 锁行高, pair 块 margin-box 20.59px ≤ 内容盒) + 双排段注释行高恒等口径改写
- `e2e/relocate-pair-row-height.spec.mjs`: 新增(+154 行), 四皮肤 SKINS_ALL @fast, vm 注入 A/B 两腿逐行行高差分(组行+种子行), 桩增量轮询不回传行 → route 翻腿不可行的取证在案
- `tests/test_webui_relocate_visibility.py`: 新增静态守阵 test_p1_pair_cell_margin_keeps_row_height_constant(margin 被摘/改值/拆写均红) + 文件头测试计划同步
- `memory-bank/conventions/webui.md`: 「迁移状态展示口径」节新增「行高恒等」条
- `memory-bank/pitfalls/testing/route-leg-flip-incremental-polling.md`: 新坑档(见 pitfalls 索引)
