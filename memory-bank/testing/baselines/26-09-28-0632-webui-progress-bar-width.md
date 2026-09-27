# 1818 passed / 3 skipped —— 进度条数值盒定宽(条长与百分比文本解耦)

> 摘要: 用户报「种子页进度条长度不一致, 似受进度文本长度影响」。根因 = `.m-progress` flex 行里条吃剩余空间、`.val` 占自然宽, 文本愈宽条愈短; 处置 = 三套皮肤数值盒 `min-width: 4em` + `text-align: right`, 守阵 `_scan_progress_val_parity` 成对兜底。真浏览器量测: 种子页 19 行文本 10.0%–100.0% 七种长度下条宽逐行恒定(atlas/prism 29px、console 31px)。纯静态 CSS + 测试守阵改动, 无 Python 源改动。
> 基线时间: 2026-09-28 06:32
> 档案: tasks/26-09-28-webui-progress-bar-width.md

- test.full: **1818 passed / 3 skipped**, 20.12s, TOTAL **91%**(12512 语句 / 914 未覆盖 / 4204 分支 / 387 partial), 与前基线(26-09-28-0546)持平; 首轮曾 1 红(见下), 终轮全绿。
- 插曲: 新增 activeContext 切片使切片数 57 > 上限 56, `test_kb_active_context_slices_are_valid` 红 —— 按归档口径删除已完全沉淀进 tasks/26-09-27-webui-curve-chart.md 的冗余切片 26-09-28-0553-webui-curve-collapse-ask-tone 后归绿。
