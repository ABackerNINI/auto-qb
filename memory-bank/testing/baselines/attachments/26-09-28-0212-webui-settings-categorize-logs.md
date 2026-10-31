# 1815 passed / 3 skipped —— webui 设置页分类回归修复(「常规/日志」成块 + 运行日志默认折叠)

> 摘要: 26-09-26 分组合并(1905d6d)的回归修复 —— log/web/notify 三段去掉 open=True 恢复成块展示(「常规/日志」而非并入「常规/常规」), label 恢复 日志/WebUI/通知; 运行日志块默认折叠 + 首次展开才拉 /api/log; hubHits/hubFieldCount 递归适配块内字段。
> 基线时间: 2026-09-28 02:12
> 档案: 26-09-28-webui-settings-categorize-logs

- **本线守阵就地加强 1 条**(test_web.py): `test_config_schema_endpoint` 新增断言 basic 尾三段
  kind=object 且不声明 open(open 段被 cfgFlatten 平铺成无标题同级字段, 正是本次回归根因)。
  本线零新增用例; 用例总数较上条基线(1814+3)的 +1 来自其间已入库的并行线。
- 三套 UI(atlas/prism/console)设置页同吃 shared 模板与 config_hub.js, 本线只改共享层一处即全生效;
  shell tpl-manifest 一致性守阵(test_web.py `_UI_ALL`)钉住 console 不漂移。

TOTAL **91.39%**(12504 语句 / 914 未覆盖 / 4204 分支 / 388 partial), 耗时 18.66s(单次采样)。
