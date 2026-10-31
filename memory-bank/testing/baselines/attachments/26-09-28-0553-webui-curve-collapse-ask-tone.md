# 1816 passed / 2 failed(1 偶发 + 1 索引滞回) —— 曲线标题栏整栏折叠 + 「?」语调色

> 摘要: 用户两条 WEBUI 反馈: ①曲线标题栏整栏可点折叠(删「收起/展开」钮, `#i-chevron` 旋转指示, 周期输入框/删除钮 `@click.stop`), 「添加档位」→「下载档位」间距 6px → 18px; ②设置页行内「?」按钮挂 `hubToneOf` 语调类, danger/important 行静息描边走 `--tone-line`、hover/打开整组转语义色。纯静态资源改动(shared/tpl 两模板 + console_hub.css), 无 Python 源改动。验证: dev.harness 桩 + 真浏览器逐项量测(折叠/图标/键盘/间距像素/「?」on 态全红)。
> 基线时间: 2026-09-28 05:53
> 档案: tasks/26-09-27-webui-curve-chart.md(追加)

- test.full: 1816 passed / 2 failed / 3 skipped —— 两条失败均与本次无关且已定性:
  - `test_memory_bank.py::test_index_is_regenerated`: 本轮改 tasks 档案后索引未重建的滞回, `kb.index` 后复跑即绿(见下)。
  - `test_qbmanager.py::test_run_loop_throttles_without_stop_event`: 时序偶发, 单独复跑 passed。
- TOTAL **91%**(12512 语句 / 914 未覆盖 / 4204 分支 / 388 partial), 耗时 20.57s, 与前基线(26-09-28-0546)持平。
