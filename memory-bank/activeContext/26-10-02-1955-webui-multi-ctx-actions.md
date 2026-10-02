# WEBUI 多选右键菜单(限速/移动/跳检/导出)— 计划已出, 待拍板

> 摘要: 用户指派出计划。计划 plans/26-10-02-1955-plan-webui-multi-ctx-actions.html(doc-status Open): R1 多选右键加 限速/移动/跳检/导出.torrent 四项, R2 跳检项(单选+多选)加配置开关 web.skip_check_menu 默认关。五波: W1 开关全链路(models/loaders/validate/GUI schema/minimal.yml/keys.md + 新 GET /api/webui/flags + skip-check 端点 403 fail-closed + 前端 flags 显隐) / W2 bulk 扩 limits+location(qbapi 原生收 hash 列表, 单次调用) / W3 bulk skip_check 走 ops 逐 hash 串行聚合回执(样板 _bulk_recheck_via_ops) / W4 新 POST /api/torrents/export-archive zip 归档(前端用 selHashSet 全量展开含组选中) / W5 冒烟+收尾。三决策点待拍板: D1 批量导出形态(推荐后端 zip) D2 服务端同步封禁(推荐是, rule 源不动) D3 批量限速留空不改(推荐); 不拍板按推荐走。关键取证: bulk 通道 RESYNC/DEFERRED 两表已含 bulk_torrents(扩动作零表改), 路由金清单 +2, 键面 fixture 要重生成。本轮只出计划, 零代码改动, 未提交。
> 最后活动: 2026-10-02 19:55
