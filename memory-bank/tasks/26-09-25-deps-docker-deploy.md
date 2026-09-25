# 26-09-25-deps-docker-deploy — Docker 部署方案 (调研 + 计划)

**Status:** Open
**Added:** 2026-09-25
**Updated:** 2026-09-25
**Summary:** 调研 auto-qb 的 Docker 部署方式并出方案。调研结论: 仓库无任何容器化资产 (绿地); 运行形态对容器友好 (stdout 恒有日志、运行态全收口 data_dir、只经 qB API 不碰 torrent 文件、GUI 三件仅托盘懒加载), 唯一代码缺口是**未注册 SIGTERM** (docker stop 即杀, 丢最多一个 state_save_interval 周期的运行态)。方案: uv 多阶段构建 (python:3.12-slim + uv sync --frozen --no-dev) + compose 单服务 (config 可写目录 + /data named volume + TZ) + 容器示例配置 (minimal.yml 底, data_dir=/data, web.host=0.0.0.0), P1 镜像 → P2 编排文档 → P3 SIGTERM 优雅退出 (唯一代码改动) → P4 可选 (CI build / GHCR / GUI 依赖分组 / 非 root)。决策点 D1–D7 与验收标准单点在计划文档。**未提交**。
**Topics:** docker-deploy
**Refs:** memory-bank/plans/26-09-25-2241-plan-docker-deploy.html

## 原始请求

> 调研本项目docker部署方式, 写一个计划

## 思考过程与决策

- **绿地确认**: 根目录与知识库均无 Docker 相关资产 (grep 命中的全是 HTML「容器」元素等无关词); 多 clone 工作区 tasks/ 查重无同名 slug。
- **契约面很小是最大利好**: 程序只经 qB WebUI API 操作种子, 不直接读写 torrent 文件 ⇒ 不需要挂载下载目录; 日志恒有 stdout handler ⇒ `docker logs` 开箱可用; 运行态 (state.json/锁/日志/web.token/hr/) 全在 data_dir ⇒ 一个 named volume 收口全部持久化。
- **D1 构建方式选 uv 多阶段**: 与 CI/本机同一把 uv.lock, 复现性最强; `uv export` + pip 备选因多一道导出物被否。
- **D2 GUI 依赖第一期不瘦身**: 瘦身要动 pyproject + uv.lock + env.sync 口径, 换来的只有十几 MB 级体积 (预估), 收益配不上代价, 列 P4。
- **D3 配置必须可写挂载**: Web UI 保存配置会写回 config.yml + 自动 .bak, 只读挂载会废掉核心能力; `web.host` 默认 127.0.0.1 在容器里等于自断, 示例配置必须改 0.0.0.0 并保留安全提示。
- **D5 SIGTERM 是唯一代码缺口**: cli.py 只捕 KeyboardInterrupt; docker stop 的 SIGTERM 直接终止, finally 落盘不走, 默认配置下丢窗最多 120s > docker stop 默认宽限 10s。补 handler 复用既有优雅退出路径, 改动小、直接兑现黄金法则 3。
- **红线贯彻**: 仓库根 config.yml / auto-qb-data/ 不进镜像 (.dockerignore 显式排除)、不进 compose 示例; 容器示例配置是新文件 docker/config.example.yml, 不动 minimal.yml。

## 实现计划

单点在 [计划文档](../plans/26-09-25-2241-plan-docker-deploy.html) (§1 调研事实表 / §3 决策点 D1–D7 / §4 交付物 5 文件 / §5 分阶段 P1–P4 / §6 风险)。拍板后按 P1 → P2 → P3 顺序实施, P4 可选延后。

## 子任务状态表

| 子任务 | 状态 | 说明 |
|---|---|---|
| 调研 (代码实况 + 部署约束) | Done | 十条事实全核对自代码 (cli.py / infra/logging.py / config/models.py / webui/server/lifecycle.py / docs/configuration.md / pyproject.toml); 详计划文档 §1 表 1 |
| 方案与取舍 (D1–D7) | Done | 计划文档 §3; 状态 Open 待拍板 |
| P1 镜像化 (Dockerfile + .dockerignore) | Pending | 验收: build 成功 / --help 正常 / 假 qB 配置干净退出码 1; 实测体积与耗时回填 |
| P2 编排与文档 (compose + 示例配置 + 部署文档) | Pending | 验收: compose up 后 WebUI 可登录 / logs 有流 / 配置写回+bak / 状态续接 / 双开被锁拒 |
| P3 SIGTERM 优雅退出 (唯一代码改动) | Pending | 复用 KeyboardInterrupt 路径; 验收: docker stop 后 "Shutting down..." + state 落盘 + 退出码 0 + 全量测试无回归 |
| P4 可选 (CI build / GHCR / GUI 瘦身 / 非 root) | Pending | 全部可延后, 不阻塞交付 |

## 进度日志

- **2026-09-25 22:41 (调研 + 计划产出)** — 用户令调研 docker 部署方式并写计划。开工同步齐平 (9d09f1f8); 十条运行形态事实核对完毕, 关键发现: ①程序与容器契约面小 (不需要挂载下载目录, 不需要 X/GTK 系统库); ②SIGTERM 缺口是唯一代码改动点; ③config 挂载必须可写 (Web UI 写回); ④时区必须可配 (HR 窗口/每日曲线按本地时间)。计划文档 `26-09-25-2241-plan-docker-deploy.html` 立档, 状态 Open 待拍板。未动任何代码, 未提交 —— 等用户拍板方案与显式提交指令。
