# 26-09-25-deps-docker-deploy — Docker 部署方案 (调研 + 计划)

**Status:** In Progress
**Added:** 2026-09-25
**Updated:** 2026-09-25
**Summary:** 调研 auto-qb 的 Docker 部署方式并出方案。调研结论: 仓库无任何容器化资产 (绿地); 运行形态对容器友好 (stdout 恒有日志、运行态全收口 data_dir、只经 qB API 不碰 torrent 文件、GUI 三件仅托盘懒加载), 唯一代码缺口是**未注册 SIGTERM** (docker stop 即杀, 丢最多一个 state_save_interval 周期的运行态)。方案: uv 多阶段构建 (python:3.12-slim + uv sync --frozen --no-dev) + compose 单服务 (config 可写目录 + /data named volume + TZ) + 容器示例配置 (minimal.yml 底, data_dir=/data, web.host=0.0.0.0), P1 镜像 → P2 编排文档 → P3 SIGTERM 优雅退出 (唯一代码改动) → P4 可选 (CI build / GHCR / GUI 依赖分组 / 非 root)。决策点 D1–D7 与验收标准单点在计划文档。**P1–P3 已实施**: 5 交付物全部落地, cli.py 注册 SIGTERM→KeyboardInterrupt (4 条单测), 全量无回归; **本机无 Docker, docker build / compose up / docker stop 真机验收待用户机器执行**; 示例配置因 minimal.yml 本身过时改用 add_episode_tags 字典形态。追加: minimal.yml 漂移修复 + 示例守阵 2 条(test_config.py)。**已提交**(2026-09-26, gitee/develop)。
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
| 方案与取舍 (D1–D7) | Done | 计划文档 §3; 用户令实施即拍板, 计划状态已改 In Progress |
| P1 镜像化 (Dockerfile + .dockerignore) | Done | 两文件落地 + 对 plan 样例的两处修正(见进度日志); ❗docker build 本机未跑(无 Docker Desktop), 镜像体积/构建耗时/GUI 三件占用**未实测** |
| P2 编排与文档 (compose + 示例配置 + 部署文档) | Done | compose.yaml + docker/config.example.yml + docs/deployment.md 落地; 示例配置过 load_config 实测 ✓, compose YAML 解析实测 ✓; ❗compose up / WebUI 登录 / 写回+bak / 状态续接 / 双开拒锁等真机验收**未做** |
| P3 SIGTERM 优雅退出 (唯一代码改动) | Done | cli.py: `_install_sigterm_handler` + `_sigterm_to_keyboardinterrupt`(转 KeyboardInterrupt 复用既有路径 + 首信号后 SIG_IGN 保护清理窗口); test_cli.py +4 条单测; 全量 1612 collected: 1611 passed + 1 skipped 无回归; ❗容器内真实 docker stop 实测(Shutting down... / state mtime / 退出码 0)**待 Docker 环境** |
| P4 可选 (CI build / GHCR / GUI 瘦身 / 非 root) | Pending | 全部可延后, 不阻塞交付 |

## 进度日志

- **2026-09-25 22:41 (调研 + 计划产出)** — 用户令调研 docker 部署方式并写计划。开工同步齐平 (9d09f1f8); 十条运行形态事实核对完毕, 关键发现: ①程序与容器契约面小 (不需要挂载下载目录, 不需要 X/GTK 系统库); ②SIGTERM 缺口是唯一代码改动点; ③config 挂载必须可写 (Web UI 写回); ④时区必须可配 (HR 窗口/每日曲线按本地时间)。计划文档 `26-09-25-2241-plan-docker-deploy.html` 立档, 状态 Open 待拍板。未动任何代码, 未提交 —— 等用户拍板方案与显式提交指令。
- **2026-09-25 (P1–P3 实施)** — 用户令"实施计划"。开工同步齐平 (origin 远端名, 237b5ee == gitee/develop; `my-commit-flow.sync` 机检内部拿不到远端真值告警, 以 ls-remote 实证替代)。落地:
  - **P1**: `Dockerfile` + `.dockerignore`。对计划样例的三处修正: ①builder/runtime 都钉 **bookworm**(uv 的 python3.12-bookworm-slim 与 python:3.12-slim-bookworm), 避免样例里 bookworm builder + 浮动 slim runtime 跨 Debian 拷 venv; ②builder 需 **COPY README.md + LICENSE** —— pyproject `readme` 是显式文件引用, hatchling 缺文件直接构建失败(计划样例没覆盖); ③依赖层缓存改为 `uv sync --no-install-project` + 补装项目两步(plan §4 注释想要的"改源码不触发重装"靠这个才能成立), 加 `PYTHONUNBUFFERED=1`。
  - **P2**: `compose.yaml` + `docker/config.example.yml` + `docs/deployment.md`(README 加一节指针)。示例配置以 minimal.yml 为底改四处: data_dir=/data / qb.host=host.docker.internal / web.host=0.0.0.0 / notify.enabled=false 显式; qB 凭据用占位符(不携带真实密码)。healthcheck 探 `GET /`(307→/atlas/, 非 /api 路径免 token, auth.py 实证)。**示例配置过 load_config 实测 ✓** (state_file 正确派生 /data/state.json)。
  - **P3**: cli.py 加 `import signal` + `_sigterm_to_keyboardinterrupt`(首信号后 SIG_IGN) + `_install_sigterm_handler`(注册失败静默), main() 参数校验后统一调用 —— handler 在主线程抛 KeyboardInterrupt, 关闭路径仍全在主循环线程, 不破单一写线程红线。test_cli.py 头部测试计划同步 +4 条。
  - **验证**: 全量 **1612 collected: 1611 passed + 1 skipped**(+4), 91% 覆盖率, 17.5s —— 无回归; dev.fmt 已跑。
  - **坑**: ①minimal.yml 本身已过不了当前 fail-fast 校验(`add_episode_tags: true` 旧形态, 现要求字典) —— 抄它当底子直接翻车, 已记 `pitfalls/docs/drift.md`; minimal.yml 的修复属计划外, **未动, 报告交用户决定**。②计划外发现: `.dockerignore` 不能排除 README.md/LICENSE(同上 hatchling 元数据)。
  - **未做/待办**: 本机无 Docker Desktop, P1/P2/P3 的真机验收(build / compose up / docker stop)全部待用户在有 Docker 的机器执行; 体积/耗时数字未实测不回填计划文档; **未提交** —— 等显式提交指令。
- **2026-09-26 (minimal.yml 修复 + 示例守阵 + 提交)** — 用户令修复 minimal.yml: `add_episode_tags` 改字典形态(`enabled: true`), 过 load_config ✓ —— 注意旧布尔写法在 schema 改版后被静默解析成**关**(enabled 默认 false), 不只是校验红。用户令补示例守阵: test_config.py +2 条(minimal 开箱语义 + docker 示例容器契约字段), minimal 守阵红验过(HEAD 旧形态 → 红)。全量 **1614 collected: 1613 passed + 1 skipped**, 91% 覆盖率, 17.0s。用户令提交: ✨ 一笔入库(gitee/develop), 知识库旗标随主提交更新。剩余待办不变: Docker 真机验收。
