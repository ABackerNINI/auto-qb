# Docker 部署方案 (调研完成, 待拍板)

> 摘要: 调研了 auto-qb 的 Docker 部署方式并产出计划 `memory-bank/plans/26-09-25-2241-plan-docker-deploy.html` (doc-topic: docker-deploy, 状态 Open)。核心结论: 仓库无容器化资产属绿地; 程序对容器天然友好 (stdout 日志 / data_dir 收口全部持久化 / 不碰 torrent 文件 / GUI 懒加载), 唯一代码缺口是未注册 SIGTERM。方案为 uv 多阶段镜像 + compose 单服务 + docker/config.example.yml, 分 P1 镜像 → P2 编排文档 → P3 SIGTERM 优雅退出 → P4 可选。任务档案 `memory-bank/tasks/26-09-25-deps-docker-deploy.md`。
> 最后活动: 2026-09-25 22:41
> 下一步: 用户拍板决策点 D1–D7 (尤其 D2 GUI 依赖不瘦身、D5 P3 补 SIGTERM) → 授权后按 P1 开工
