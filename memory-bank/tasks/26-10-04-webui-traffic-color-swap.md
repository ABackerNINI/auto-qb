# 26-10-04-webui-traffic-color-swap — WEBUI 上下行流量方向色交换 + 速度组图标统一 + 限速改灰

**Status:** Done
**Added:** 2026-10-04
**Updated:** 2026-10-04
**Summary:** 用户拍板交换上下行流量方向色(原 上行=teal 蓝绿 / 下行=indigo 紫 → 现 上行=indigo 紫 / 下行=teal 蓝绿), 覆盖历史流量图 / qB 流量图(种子·组·全局) / 状态栏今日统计 / 状态栏速度组图标; 速度组方向图标由全局绿/蓝统一到流量语义色(按 `.sb-spd` 作用域覆盖), 状态栏限速值改中性灰 `--fg-dim`(与做种要求值 `.m-pair .req` 同款)。改动 = 7 处令牌定义 + 3 皮肤 i-traffic 内联兜底 + `qb_traffic_chart.js` 兜底链 + 3 皮肤 `.sb-spd` 规则, 共 14 文件; test.full **2508 passed + 4 skipped / 99%**(基线 26-10-04-1722); 真浏览器三皮肤 30 断言全过。改动留在工作树, 等用户显式提交指令。
**Topics:** webui-traffic-color-swap
**Refs:** memory-bank/testing/baselines/26-10-04-1722-webui-traffic-color-swap.md

## 原始请求

> WEBUI 流量色交换, 目前的上行是蓝绿色系, 下行是紫色系, 感觉有些别扭. 包含历史流量图/qb流量图(种子/组/全局)/状态栏上传下载统计/状态栏上传下载速度. 同时状态栏上传下载速度的限速改为灰色系, 与做种要求时长类似.

## 思考过程与决策

- **单一色源**: 上下行流量色是语义令牌 `--today-up` / `--today-down`(7 处声明: `atlas/style.css` · `console/style.css` · `prism/css/themes/*.css` 五主题)。历史流量图(SVG)、qB 流量图(uPlot, 经 `_qbChartTokens()` 现读令牌)、状态栏今日统计(`.sb-item.sb-today .v-up/.v-down`)、i-traffic 组图标(内联 `var(--today-*)`)全部走这两个令牌 —— **交换令牌值即全量生效**, 不逐处改。
- **速度组图标是本轮唯一需要新接线处**: `.sb-spd` 的方向图标此前走**全局** `.ico-up`(绿)/`.ico-down`(蓝), 与流量语义色不同族。用户拍板「统一到流量色系」→ 新增作用域覆盖 `.sb-spd .ico-up/.ico-down`(特异性 0,2,0 压过全局 0,1,0)。**不动全局 `.ico-up/.ico-down`** —— 它们还喂顶栏「种子」入口等非流量位置。
- **限速改灰**: `.sb-spd .lim` 由 `--fg`(亮)改 `--fg-dim`, 与做种要求值 `.m-pair .req` 同款; 字重 600→500, `.off`(不限)态再降为 400 + `opacity .6`, 保留「不限」的弱化层次。
- **兜底链同步**: `qb_traffic_chart.js` 的 `pick("--today-up", "--teal", ...)` 与三皮肤 `index.html` i-traffic 内联 `var(--today-*, var(--xxx))` 的 fallback 色随语义对调 —— 令牌恒有值, 属卫生性一致, 非渲染路径。
- **派生影响(有意保留)**: `.ico-history`(历史流量弹层标题图标)与 i-traffic 双色图标引用 `--today-up`, 随令牌一起交换 —— 同族装饰, 属预期。
- **`--today-ico`(lime)不动**: 今日流量组的入口按钮图标色位, 与 up/down 色刻意不同族(见 `issues/26-09-20-1840`), 本轮不涉及。

## 实现计划

1. 交换 7 处令牌值 → `--today-up: var(--indigo)` / `--today-down: var(--teal)`。
2. 同步 3 皮肤 i-traffic 内联兜底 + `qb_traffic_chart.js` 兜底链。
3. 三皮肤 `.sb-spd`: 新增 `.ico-up/.ico-down` 作用域覆盖; `.lim` 改灰。
4. 验证: `test.full` + 真浏览器三皮肤(令牌解析 / 速度组图标 / 限速灰 / 今日统计 / 历史图 stroke / qB 图 `_qbChartTokens()`)。

## 子任务状态表

| 子任务 | 状态 |
|---|---|
| 交换 7 处 `--today-up/down` 令牌值 | ✅ |
| 同步 i-traffic 内联兜底(3 html) + `qb_traffic_chart.js` 兜底链 | ✅ |
| 三皮肤 `.sb-spd` 图标统一 + 限速改灰 | ✅ |
| 验证: `test.full` 2508 passed + 真浏览器 30 断言 | ✅ |
| 收尾 DoD(切片 / 档案 / 基线 / conventions 回写 / 索引) | ✅ |

## 进度日志

- 2026-10-04 17:2x: 一轮实施完成。14 文件改动; `commands run test.full` **2508 passed + 4 skipped / 41.32s / 99%**; Playwright + `scripts/ui_harness.py` 桩服务三皮肤(atlas/console/prism)实测 30 断言全过(令牌解析 / 速度组图标 / 限速灰 / 今日统计 / 历史图 stroke / qB 图 `_qbChartTokens()`), 零 pageerror。改动留在工作树, 等用户显式提交指令。
