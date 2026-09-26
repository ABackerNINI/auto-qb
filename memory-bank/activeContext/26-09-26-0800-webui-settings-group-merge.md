# 设置页分组合并: 日志/界面(WebUI)/通知/运行日志 并入「常规」

> 摘要: schema groups.py 单点合并(log/web/notify 并进 basic, 三个独立分组删除, 首页 10 卡 → 6 卡), 两套 UI 派生跟随 + `__logs` 特制卡/分支删除(运行日志块随常规分区页尾), 存量浏览器偏好映射兼容; 守阵同步。已立档 `26-09-26-webui-settings-group-merge`, 事实回写 progress/core-domain 完成, 随主提交入库。
> 触发: 设置页, 分组, 常规, WebUI, 运行日志, 通知, schema groups, hub 卡片
> 最后活动: 2026-09-26 08:00

## 状态

- **已完成(代码)**: groups.py 合并 + __init__.py 文档行; config_hub.js(META/HELP rel/OFF_KEYS/hubCards/hubNow/hubGo/hubRestore/hubLedOf/hubReadout); atlas/prism 模板成对改; dialogs.js 注释; test_config_schema_endpoint 守阵更新。
- **已完成(收尾)**: 事实回写(progress/implemented-webui.md 新条目 + core-domain.md 专段描述; README 无设置页分组描述不用动); 基线切片 `26-09-26-0802-webui-settings-group-merge`; tmpdir 坑复发 +1; 档案立档 + 本切片。
- **验证**: 合并工作树(含并行 versioning/button 测试)test.quick 1665 passed + 1 skipped; test.full 数字见 kb.baseline 最新切片。
- **遗留**: 真机浏览器走查待用户重启进程后自查(schema 是模块级常量, 重启才见新分组); GitHub 镜像允许失败只报一次。
