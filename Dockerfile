# auto-qb 容器镜像 (plan 26-09-25-2241 · D1: uv 多阶段构建)
# builder 与 runtime 都钉 bookworm: 拷贝 venv 跨 Debian 版本时解释器 patch 级与
# glibc 环境完全一致, 不冒 python:3.12-slim 浮动到新 Debian 的险
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
WORKDIR /app

# 依赖缓存层: 只拷锁文件装全量依赖(--no-install-project 时还没有源码可装项目本体)。
# 依赖不变时改源码不触发重装 —— 层缓存命中
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 项目本体以普通 wheel 形态装入(--no-editable): 镜像内代码随 venv 走, 不依赖挂载。
# README.md 是 pyproject 的 readme 元数据, hatchling 构建期要读, 缺了直接构建失败
COPY README.md LICENSE ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.12-slim-bookworm
# slim 无 tzdata; HR 窗口/每日限速曲线按本地时间计算(plan D7), TZ 经 compose environment 可覆盖
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" \
    TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1
# 配置路径是 CLI 位置参数(cli.py: 默认 config.yml), 容器里指向挂载的配置目录
ENTRYPOINT ["auto-qb"]
CMD ["/config/config.yml"]
