# 基线切片 26-10-07-1003 — content 组行级键盘 roving tabindex(issue 26-10-07-0846)

> 摘要: 认领 issue 26-10-07-0846 实施收尾 —— 核心层 reg.helpers 增行级键盘四件套
> (roving/rowFocusKey/rowRestore/rowMove), content 组 dt10/11/12 行/块容器键盘化
> (tabindex=-1 + 锚点/回焦/方向键移焦/Enter-Space 激活), 新增守阵
> test_drawer_tpl_content_row_keyboard_roving(test_web.py)。
> 基线时间: 2026-10-07 10:03
**Refs:** memory-bank/issues/26-10-07-0846-feat-webui-content-row-keyboard.html,memory-bank/tasks/26-10-07-webui-content-row-keyboard.md,memory-bank/activeContext/26-10-07-1003-webui-content-row-keyboard.md

- 分支: develop @ `cc30fc76`(工作树含本轮未提交改动)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2713 passed + 4 skipped, 56.24s, 覆盖率 TOTAL 99%**
  (16061 语句 / 163 未覆盖 / 5496 分支 / 143 partial; 门槛 98% 达标)
- 相对上基线 (26-10-07-0940: 2712 passed + 4 skipped / 99% / 49.84s): passed 2712→2713
  (+1 = 新守阵 content_row_keyboard_roving), 语句/分支/未覆盖/partial 全同(纯前端 JS 改动,
  不进 Python 覆盖率面), 无回归信号; 耗时 49.84s→56.24s 为单次采样波动(同机历史采样区间内),
  按口径不更新区间结论。
