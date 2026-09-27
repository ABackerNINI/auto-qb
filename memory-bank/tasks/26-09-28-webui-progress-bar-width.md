# 26-09-28-webui-progress-bar-width — WEBUI 进度条条长随百分比文本漂移(数值盒定宽)

**Status:** Done
**Added:** 2026-09-28
**Updated:** 2026-09-28
**Summary:** 种子/辅种/追剧三处表格共用的 `.m-progress` 进度条, 条长随右侧百分比文本宽逐行漂移(「100.0%」行比「5.2%」行条短)。三套皮肤数值盒统一 `min-width: 4em` + `text-align: right` 解耦; 守阵 `_scan_progress_val_parity` 成对兜底; 真浏览器量测三套皮肤条宽逐行恒定(atlas/prism 29px、console 31px)。test.full 1818 passed(基线 26-09-28-0632)。
**Topics:** webui-progress-bar-width

## 原始请求

用户报: 「WEBUI种子页进度条长度不一致, 似乎受后面的进度文本长度影响」。

## 思考过程与决策

- 根因即用户猜测: `.m-progress { display:flex }` 里 `.bar { flex: 1 1 auto }` 吃剩余空间, `.val { flex: 0 0 auto }` 占自身自然宽 —— 百分比文本愈宽条愈短, 同列逐行漂移; `m-progress` 在 torrents/groups/shows 三模板 5 处共用, 组件级 CSS 一处修全覆盖。
- 修数值盒不修条: 把条定死宽度会与"列宽可拖"冲突(窄列溢出/宽列留白); 数值盒 `min-width: 4em` 容纳最宽的「100.0%」(11.5-12px 字号下实测文本 ≤3.6em), 右对齐使数字列齐(tabular-nums/mono 早已就位)。
- 三套皮肤成对改(atlas/console 的 components.css + prism 的 views.css); 说明文字并入各文件既有的进度段注释行 —— atlas components.css 已贴 700 行单文件体量上限, 不得加行(test.quick 首轮即被该守阵拦下)。
- 守阵按「两套 UI 成对改加静态计数断言」纪律落 `_scan_progress_val_parity`; 布局正确性另行真浏览器量测(静态断言兜不住计算宽)。

## 实现计划

1. 三套皮肤 `.m-progress .val` +`min-width: 4em; text-align: right`。
2. `tests/test_web.py` +第 16 项扫描器 `_scan_progress_val_parity`(每套恰 1 条 `.m-progress .val` 基础规则且带 min-width)。
3. 验证: test.quick → test.full; dev.harness 桩(默认端口 8099 被一周前孤儿进程占用, 改 `--port 8101`) + 真浏览器三套皮肤量 `.bar`/`.val` 宽与 computed 值。

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | 三套皮肤 CSS 数值盒定宽右对齐 | Done |
| 2 | 守阵 _scan_progress_val_parity + 守阵 docstring 第 16 项 | Done |
| 3 | test.quick/full + 真浏览器三皮肤量测 | Done |
| 4 | 收尾回写(档案/切片/基线/坑条/索引) | Done |

## 进度日志

- 2026-09-28 06:00 定位根因并实施; test.quick 首轮 1 红: atlas components.css 701 行超「单 CSS ≤700 行」体量守阵(新增注释行所致) —— 说明并入既有注释行后归绿(1818 passed / 3 skipped)。
- 2026-09-28 06:25 真浏览器量测(dev.harness 桩 8101): 三套皮肤种子页 19 行, 文本 10.0%–100.0% 七种长度下 `.bar` 宽逐行恒定(atlas/prism 29px、console 31px), `.val` 恒 48/46px, computed min-width 48px/46px(=4em)生效、text-align right 生效。
- 2026-09-28 06:30 test.full 终轮 1818 passed / 3 skipped, TOTAL 91%; 基线切片 26-09-28-0632; 坑条入 pitfalls/web-ui/progress-bar.md(独立新主题文件 —— layout-css.md 已 7,995 字符超 pitfall cap 6,000, 不再喂大)。
- 2026-09-28 06:32 新切片使 activeContext 目录数 57>56 触红守阵 —— 按归档口径删除已完全沉淀的冗余切片 26-09-28-0553-webui-curve-collapse-ask-tone(其内容自称详见 tasks/26-09-27-webui-curve-chart.md 09-28 追加段)后归绿。
- 2026-09-28 06:40 用户问「辅种/追剧页是否同样覆盖」—— 真浏览器补量测确认: 三皮肤 × 辅种(组行+展开明细, prism/console 各 202 行, 文本 100.0%/90.0%)/追剧(展开 24 行, 文本 0.0%/10.0%/100.0%)条宽逐行恒定, 组件级修复天然覆盖三页; 按用户「直接提交」指令入库。
