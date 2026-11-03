# 26-11-03-webui-drawer-window-firstbeat-converge — 修复 e2e 大表既有红: 抽屉窗口化首拍间距未收敛(dt-live #10/#12, dt11 树表批量)

**Status:** Done
**Added:** 2026-11-03
**Updated:** 2026-11-03
**Summary:** 大表既有红已修: 产品窗口引擎三处接线修正(容器 vh/抽屉 gap 收敛/行高实测) + dt11 过时期望改正, 定向 e2e 全绿
**Topics:** webui-drawer-window-firstbeat-converge
**Refs:** memory-bank/issues/26-11-03-0559-test-e2e-big-table-existing-red.html

## 原始请求

1. 认领并修复 e2e 既有红灯 issue `memory-bank/issues/26-11-03-0559-test-e2e-big-table-existing-red.html`（与本轮另一件 ctx-menu issue 同一 harness 面，可合轮，但档案与根因独立留痕）。
2. 先复现红灯再判归属（真缺陷/过时 spec/夹具/环境）；禁止放宽断言、加 skip、改超时；过时 spec 必须用产品侧现状证据支撑；产品缺陷改 `src/` 最小化；计划外缺陷入池不顺手改。
3. 只用测试实例（本机取 `C:\Programs\qBittorrent-testing` 36595/36596），真实种子非活跃，用完清伪造种子与进程，token 不进提交文件。
4. 定向 e2e（红→绿实测）→ `commands run test.full` → 按 `testing/baseline.md` 新建基线切片。
5. 收尾 DoD + `ship.commit`（gitmoji+中文、数字为提交那刻实测）；只在当前 clone 内操作，`config.yml`/`auto-qb-data/` 红线不改不提交。

## 思考过程与决策

- 三处红灯分两类：**真产品缺陷**（dt-live #10/#12）+ **过时 spec**（dt11 树表批量优先级期望）。
- 复现 #12：千文件桩滚到底后末行 `D/f0999 - file.mkv` 不在 DOM。探针实测首拍 `scrollHeight=27309`（真高约 33150），即首拍按 rowGap=0 估总高，少 5~6px × 1000 行；滚动被钳在被压短的总高上，间距随后实测收敛，滚动位置已不在底部 → 末行永远不渲染。
- 两个根因都在窗口引擎接线（`columns_grid.js`）：
  1. 抽屉内容桥首渲时 `.group-table` 未落 DOM，`_winGapFor` 回退 0；**不能借主表缓存** —— 主表挂 `.rl-scope`，`row_lang.css` 把它的 rowGap 清零（抽屉不挂该类，恒为皮肤基值 5/6px），实测借到 0px（错因实证：探针 `_winGap.torrent=0`、`computed rowGap` 主表 0 / 抽屉 6）。
  2. `_rowWindow` 的 end 用文档型 `_winViewH` 而非容器 `vh`，抽屉窗口按主表/文档视口开窗（多渲染约一倍行数），主表几何一变就晚长。
- 决策：不动 `dtRowAfter` 死链（计划外缺陷，入池 `26-11-03-0802-bug-drawer-rowafter-dead-hook`）；收敛逻辑放在 `_winGapFor` 的 null 分支，逐帧探到真间距后 bump `_rowHVer` 重算，上限 12 帧。
- 二次发现：行高首拍在抽屉入场期被 `content-visibility:auto` 报成 `contain-intrinsic-size` 内容盒 27+边框=28，落定后真渲染 27；首拍均值 28 会让「下一次实测」（用户点勾选那拍）才发现差 1px → 再收一窗，正是 #10 变异数 18 的来源。处置：实测只取 `checkVisibility({contentVisibilityAuto:true})` 通过的行；收窗后再补两拍实测，把均值拉回 27（改动仍在窗口引擎，不碰断言）。
- dt11 树表批量：批量「最高」的产品行为已改为**乐观写**（`setFilePriority` 先写本地 priority 再 POST），E01 徽章当帧读 7，`PRIO_CYCLE [0,1,6,7]` 循环 7→0；原 spec 期望 6 基于旧的「批量后 E01 仍为 1」假设 → 过时 spec，改 0 并写明依据。

## 实现计划

1. 复现三处红灯（dt-live #10/#12 两皮肤、drawer-content dt11 树表批量两皮肤）。
2. 修 `columns_grid.js`：end 用容器 `vh`；抽屉间距逐帧收敛（不借主表）；行高实测过滤 content-visibility 跳过行 + 收窗后补拍。
3. 改 `e2e/drawer-content-variant-tables.spec.mjs` 的过时期望 6→0（附产品侧依据注释）。
4. 定向复跑：dt-live 全文件、drawer-content-variant-tables 全文件。
5. 全量 `test.full` + 基线切片 + 收尾回写。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 复现 dt-live #10/#12 与大表 dt11 树表批量 | Done(2026-11-03) |
| 2 | 修 `_rowWindow` end 使用容器 vh | Done(2026-11-03) |
| 3 | `_winGapFor` 抽屉首拍逐帧收敛(不借主表 rowGap) | Done(2026-11-03) |
| 4 | 行高首拍过滤 content-visibility 跳过行 + 收窗后补两拍实测 | Done(2026-11-03) |
| 5 | 过时 spec：dt11 批量后徽章 6→0 | Done(2026-11-03) |
| 6 | 定向 e2e 两套复跑(红→绿) | Done(2026-11-03) |
| 7 | 全量 test.full + 基线切片 | Done(2026-11-03) |

## 进度日志

### R0 · 立档 (2026-11-03)

认领：用户指派修复本 issue；档案与 issue `doc-refs` 双向闭环。

### R1 · 修复与验证 (2026-11-03)

- 复现（修复前）：dt-live #10 变异 10(prism)/11(atlas) 超预算、#12 两皮肤末行不在窗；drawer-content dt11 批量后 E01 徽章实际 POST priority=0，旧 spec 断言 6 → 红。
- 修复后实测：dt-live 全文件 **14 passed**（prism #10 mut 2 / #11 mut 5；atlas #10 mut 2 / #11 mut 5；#12 两皮肤绿）；drawer-content-variant-tables **6 passed**。
- 产品改动唯一文件：`src/auto_qb/webui/static/shared/columns_grid.js`（end 用 vh；抽屉 gap 首拍收敛；行高实测过滤与补拍）。spec 改动唯一文件：`e2e/drawer-content-variant-tables.spec.mjs`（期望 6→0 + 依据注释）。
- 计划外发现入池：`memory-bank/issues/26-11-03-0802-bug-drawer-rowafter-dead-hook.html`（dtRowAfter 参数语义错位，rowAfterFn 永不执行；本轮未改）。

- 2026-11-03 08:21 修复 e2e 大表既有红：窗口引擎三处接线修正(容器 vh/抽屉 gap 首拍收敛/行高实测过滤与补拍) + dt11 过时期望改正；定向 e2e 全绿，全量测试通过
