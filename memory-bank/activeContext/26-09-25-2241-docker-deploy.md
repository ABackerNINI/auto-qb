# Docker 部署 (P1–P3 已实施并入库, 待真机验收)

> 摘要: 计划 `memory-bank/plans/26-09-25-2241-plan-docker-deploy.html` 拍板后实施完毕 (状态 In Progress)。落地 5 交付物: Dockerfile + .dockerignore (uv 多阶段, builder/runtime 都钉 bookworm, README/LICENSE 必须留 —— pyproject readme 元数据), compose.yaml + docker/config.example.yml (过 load_config 实测 ✓; data_dir=/data / web.host=0.0.0.0 / notify 关), docs/deployment.md + README 指针; P3 唯一代码改动: cli.py 注册 SIGTERM→KeyboardInterrupt 复用优雅关闭路径 (test_cli.py +4 条)。追加: ①minimal.yml 漂移修复(add_episode_tags 字典形态); ②示例守阵 test_config.py +2 条(minimal 开箱语义 + docker 容器契约字段), 红验过; 全量 1614 collected: 1613 passed + 1 skipped。任务档案 `memory-bank/tasks/26-09-25-deps-docker-deploy.md`。**已提交**(2026-09-26, gitee/develop)。
> 最后活动: 2026-09-26
> 下一步: 有 Docker 的机器上跑真机验收 (docker build / compose up / docker stop 三组验收标准在计划 §5, 体积耗时数字回填计划与档案)

