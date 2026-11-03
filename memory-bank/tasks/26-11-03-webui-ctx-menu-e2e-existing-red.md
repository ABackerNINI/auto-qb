# 26-11-03-webui-ctx-menu-e2e-existing-red — 修复 e2e 右键菜单既有红: 定制块行数漂移与 CTX 选择器/子面板 fit

**Status:** Done
**Added:** 2026-11-03
**Updated:** 2026-11-03
**Summary:** 右键菜单既有红已修: 三条 spec 按产品注册表现状改正(一级 20 行/两个 has-sub/静态更多操作), 产品零改动
**Topics:** webui-ctx-menu-e2e-existing-red
**Refs:** memory-bank/issues/26-11-03-0559-test-e2e-ctx-menu-existing-red.html

## 原始请求

1. 认领并修复 e2e 既有红灯 issue `memory-bank/issues/26-11-03-0559-test-e2e-ctx-menu-existing-red.html`（与大表 issue 同一 harness 面，可合轮，但档案与根因独立留痕）。
2. 先复现红灯再判归属；禁止放宽断言、加 skip、改超时；过时 spec 必须用产品侧现状证据支撑；产品缺陷改 `src/` 最小化；计划外缺陷入池不顺手改。
3. 定向 e2e 给红→绿实测数 → `test.full` → 基线切片；收尾 DoD + `ship.commit`；只在当前 clone，红线文件不碰。

## 思考过程与决策

- 三支用例全部判为**过时 spec**（产品侧有意变更），本轮不改产品代码，只修选择器/期望值：
  1. `ctx-custom`：设置页定制块「四支 tab」一级行数 19→**20**。依据产品注册表 `shared/ctx_menu.js` 的 `order.member`：15 项 + 5 线 = 20（"转移到" 为 26-10-28 加入的第二个父项，与"更多操作"并列；提交 d839a417）。只改次数与注释，次级 13 不动。
  2. `menus` CTX-04/05/06：一级 `.ctx-item.has-sub` 由 1 变 2（动态「转移到」+ 静态「更多操作」），旧断言 `count()==1` + `subs.first()` 触发 strict mode violation。改为按 `data-item` 锁定身份：`has-sub` 恒 2、断言 `[data-item="transfer"]` 在座、hover `[data-item="sub-more"]`（复制族子面板仍在静态入口下，内容断言保持）。
  3. `menus` CTX-sub fit：hover 选择器 `.ctx-menu > .ctx-item.has-sub` 命中 2 → 改 `[data-item="sub-more"]`，量具仍是复制族子面板尺寸。
- 为什么原断言失效：三条都隐含"一级只有一个次级入口 / 一级 19 行"的旧产品口径；当前产品为 26-10-28 起新增动态转移父项后的现状（注册表与 DOM 均 20 行 / 2 个 has-sub），断言口径落后于产品，不是布局或夹具缺陷。
- 附带发现（计划外，入池不改）：`dtRowAfter` 参数语义错位死链 `26-11-03-0802-bug-drawer-rowafter-dead-hook`（属大表轮次发现，与本件根因无关）。

## 实现计划

1. 复现：`ctx-custom` 定制块、`menus` CTX-04、`menus` CTX-sub fit（两皮肤）。
2. 只改 spec：`e2e/ctx-custom.spec.mjs`（19→20 + 注释）、`e2e/menus.spec.mjs`（CTX-04/05/06 与 CTX-sub fit 选择器/计数）。
3. 定向复跑两个文件 + `menus` 全文件，防回归。
4. 全量 `test.full` + 基线切片 + 收尾回写。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 复现 ctx-custom / CTX-04 / CTX-sub fit 红灯 | Done(2026-11-03) |
| 2 | 修 ctx-custom 一级 19→20（含 order 长度） | Done(2026-11-03) |
| 3 | 修 menus CTX-04/05/06 选择器与计数 | Done(2026-11-03) |
| 4 | 修 menus CTX-sub fit hover 选择器 | Done(2026-11-03) |
| 5 | 定向复跑（红→绿）+ menus 全文件回归 | Done(2026-11-03) |
| 6 | 全量 test.full + 基线切片 | Done(2026-11-03) |

## 进度日志

### R0 · 立档 (2026-11-03)

认领：用户指派修复本 issue；档案与 issue `doc-refs` 双向闭环。

### R1 · 修复与验证 (2026-11-03)

- 复现（修复前）：`ctx-custom` 2 failed（prism/atlas，19 vs 20）；`menus` CTX-04 2 failed（has-sub 计数 1 vs 2 + strict mode）；`menus` CTX-sub fit 2 failed（hover 选择器命中 2）。
- 修复后实测：`ctx-custom` **2 passed**；`menus` CTX-04/CTX-sub 定向各绿；`menus` 全文件 **30 passed / 6 skipped**（skip 为既有 W5-off 条件组）。
- 改动文件：仅 `e2e/ctx-custom.spec.mjs`、`e2e/menus.spec.mjs`；产品 `src/` 零改动。

- 2026-11-03 08:21 修复 e2e 右键菜单既有红：按产品注册表与 data-item 改正三条过时 spec(定制块 20 行/两个 has-sub/hover 锁定静态更多操作)；产品零改动，定向 e2e 全绿
