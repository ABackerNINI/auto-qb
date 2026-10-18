# webui-add-partial-receipt

> 摘要: 三态回执修复落地并全量验证: 后端 _add_outcome 三值受理态 + _cmd_add_torrents 聚合(ok/warn/error), 前端 submitAddTorrent 按 r.status 分流(warn 关窗+toast / error 留窗), 单测/静态守阵/e2e 双方向均红验; test.full 与 e2e fast 全过(数字见基线切片)
> 最后活动: 2026-10-18 22:27

**R0(2026-10-18 22:27):** 三态回执修复落地并全量验证: 后端 _add_outcome 三值受理态 + _cmd_add_torrents 聚合(ok/warn/error), 前端 submitAddTorrent 按 r.status 分流(warn 关窗+toast / error 留窗), 单测/静态守阵/e2e 双方向均红验; test.full 与 e2e fast 全过(数字见基线切片)
