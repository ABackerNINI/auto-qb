# auto-qb Linux 测试端 testbed 镜像(S1 基建, 计划单点:
# memory-bank/plans/26-11-12-0152-plan-linux-testbed-docker.html §03「镜像分层」/ §06 D1-D8)。
#
# 形态: 常驻容器 auto-qb-testbed(--restart unless-stopped)的环境底座 —— 环境一次烘焙, 代码由
# test.linux / test.linux-e2e / mutants 按会话经 docker exec 推送; 容器内不留必须手工抢救的状态,
# 容器重建即净室。tag 由构建脚本打: auto-qb-testbed:<uv.lock sha256 前 8 位> + latest
# (hash 未变 = 依赖层整体命中缓存, 重建秒级)。
#
# 网络策略(D8, 2026-11-12 拍板): 镜像与依赖一律国内镜像站优先; github 系直连; 连不上 ->
# 停手请用户手动开代理后重跑 —— 本镜像不内置代理、不自动重试、代理地址不进代码。
#
# 镜像源候选与切换方式(R9: 国内站时效性强, 实跑后把实测钉值回写任务档案 task note, 漂移即换下一家):
# - Docker Hub 基底: 不在本文件写死 —— 构建脚本 .commands/test/scripts/linux_env.py 按候选清单
#   逐家试拉后经 --build-arg BASE_IMAGE 传入; 候选可用环境变量 AUTO_QB_TESTBED_HUB_MIRRORS 覆盖
#   (逗号/空白分隔, 值 direct = 跳过镜像源直连)。
#   默认候选: docker.m.daocloud.io / docker.1ms.run / docker.xuanyuan.me / docker.mirrors.tuna.tsinghua.edu.cn
#   *实跑实测(2026-11-12): 首跑 docker.m.daocloud.io 拉取瞬断(anonymous token EOF), 候选链按序
#   顶上 —— docker.1ms.run 拉成同一 digest fe81560990fa; 重试跑 daocloud 恢复, 成功构建的基底
#   终局来自 docker.m.daocloud.io(两家均通; 按序试拉机制已实证, 漂移即换下一家)。
# - apt(下方 ARG APT_MIRROR): 清华默认, 备选 mirrors.aliyun.com / mirrors.ustc.edu.cn
#   *实跑实测(2026-11-12): TUNA 走 http 11MB/s; WARN: 必须 http 不能 https —— 极简基底无 CA 包,
#   详见层 1 注。
# - PyPI(下方 ARG UV_INDEX): 清华 simple 默认, 备选 https://mirrors.aliyun.com/pypi/simple/
#   注意: uv sync --frozen 不吃 index(机制事实见层 4 注与计划 §10 R4)—— PyPI 面实走
#   uv export + uv pip install --index-url(层 5); S2 运行期 delta 走同款 pip 路线
# - npm / playwright 二进制(下方 ARG NPM_REGISTRY / ARG PLAYWRIGHT_DOWNLOAD_HOST): npmmirror
#   *实跑实测(2026-11-12): npm ci 859ms; chromium 114.3MiB 走 cdn.npmmirror.com 成功
#   (playwright 1.63.0 / chromium-1243 / Chrome Headless Shell 153.0.8010.12)。
# - github 系(uv 托管 CPython 3.13, 源在 github releases): 直连; 失败即构建中断, 停手请用户
#   手动开代理后重跑。备选路线(计划已记, 未实装): deadsnakes PPA(launchpad 直连)
#   *实跑实测(2026-11-12): 直连成功, 未开代理 —— CPython 3.13.18 下载 6.9s 落地。
# - NodeSource(层 2): 直连成功, 未触发 apt 18.x 降级 —— node v22.23.5 / npm 10.9.9。
# - PyPI(层 3/5): TUNA simple; pip 装到 uv 0.13.7; export+pip 双 venv 各 63 包约 335ms。
#
# 整体实测: 全量构建(buildkit 步骤 1-13 一次走通; 注意步号不是本文件的 6 分层编号)约 161s,
# 镜像 2.95GB; 幂等复跑 0.5s no-op。
#
# 分层(贪心缓存序, 改代码不触发重装): 系统层 -> node 层 -> uv 层 -> ENV 层 -> 依赖烘焙层 -> e2e 层。

# ---------------------------------------------------------------------------
# 层 1 系统层: ubuntu:24.04(基底对齐 CI ubuntu-latest)+ apt 换国内源 + 基础工具
# 3.13 不走 apt: noble 官方源无 python3.13(计划评审轮 1 实测), 走下方烘焙层 uv 托管 CPython
# WARN: apt 源必须走 http 不能 https(2026-11-12 首跑实测): 极简基底 ubuntu:24.04 连 /etc/ssl/certs
# 都没有(无 ca-certificates), https 面 apt 握手必死("No system certificates available"); http 面
# 完整性靠 apt 的 GPG 签名校验, 安全语义不降 —— 本层会装上 ca-certificates, 后续层的 https 面
# (nodesource curl / playwright install-deps)不受影响。TUNA http 实测 11MB/s。
ARG BASE_IMAGE=ubuntu:24.04
FROM ${BASE_IMAGE}
ARG APT_MIRROR=mirrors.tuna.tsinghua.edu.cn
RUN set -eux; \
    if [ -f /etc/apt/sources.list.d/ubuntu.sources ]; then \
      sed -ri "s#http://archive\.ubuntu\.com#http://${APT_MIRROR}#g; s#http://security\.ubuntu\.com#http://${APT_MIRROR}#g" \
        /etc/apt/sources.list.d/ubuntu.sources; \
    fi; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      python3.12 python3.12-venv python3-pip \
      git tar rsync curl ca-certificates; \
    rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# 层 2 node 层: NodeSource LTS(与 CI lts/* 同源)。
# R2: nodesource.com 非 github 系, 直连; 不可达时降级 apt nodejs(Ubuntu 24.04 = 18.x,
# playwright 1.63 兼容 >=18)—— npm 与 playwright 二进制本就走 npmmirror, 不受此降级影响。
ARG NODE_MAJOR=22
RUN set -eux; \
    if curl -fsSL --connect-timeout 20 --max-time 60 -o /tmp/nodesource_setup.sh "https://deb.nodesource.com/setup_${NODE_MAJOR}.x" \
       && bash /tmp/nodesource_setup.sh; then \
      apt-get install -y --no-install-recommends nodejs; \
    else \
      echo "[WARN] NodeSource 不可达, 降级 apt nodejs(R2: Ubuntu 24.04 = 18.x, playwright 1.63 兼容 >=18)"; \
      apt-get install -y --no-install-recommends nodejs npm; \
    fi; \
    rm -rf /var/lib/apt/lists/*; \
    node --version; npm --version

# ---------------------------------------------------------------------------
# 层 3 uv 层: pip 走国内 PyPI 镜像装 uv(计划 R1: ghcr COPY --from 降为备选, 主线不碰 github)。
# --break-system-packages: noble 系统 python 是 PEP 668 externally-managed; 这里只往系统装
# uv 二进制本体(项目环境一律是 uv 管理的 venv), 无污染面。
ARG UV_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple
RUN python3 -m pip install --no-cache-dir --break-system-packages -i "${UV_INDEX}" uv

# 层 4 环境变量层: 运行期零下载(两个解释器都已进镜像, 发现即用)。
# UV_DEFAULT_INDEX / UV_INDEX_URL 两个等价变量同指国内源, 都只覆盖解析/下载面 —— export
# --frozen 与 uv sync 不吃 index(机制事实, 计划 §10 R4: uv.lock 记录 787 个
# files.pythonhosted.org 绝对 URL, sync --frozen 跳过 index 校验, 故 PyPI 面一律走 uv pip
# 路线显式 --index-url, 层 5; S2 运行期 delta 同款, 交接注记见 linux_env.py 头注)。
# UV_INDEX_URL 是 pip 兼容旧别名, UV_DEFAULT_INDEX 优先 —— 双写兜住两代 uv 的读法。
ARG PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright
ENV UV_PYTHON_DOWNLOADS=never \
    UV_DEFAULT_INDEX="${UV_INDEX}" \
    UV_INDEX_URL="${UV_INDEX}" \
    UV_LINK_MODE=copy \
    PLAYWRIGHT_DOWNLOAD_HOST="${PLAYWRIGHT_DOWNLOAD_HOST}" \
    LANG=C.UTF-8

# ---------------------------------------------------------------------------
# 层 5 依赖烘焙层: 双 venv 模板(D3: 3.12 = apt 系统 + 3.13 = uv 托管, CI 矩阵全对齐,
# 缺一即留「本地绿 CI 红」盲区)。plan/lock 四份清单由构建脚本拷进临时 context(不整棵工作树)。
# R3(uv#7340): ENV UV_PYTHON_DOWNLOADS=never 连显式 uv python install 也拦 —— install 必须
# RUN 级 manual override, 否则构建自锁; venv/导出/安装不给 override(继承 never: 发现不了解释器
# 就 fail-fast, 不许偷偷补下载)。
# R4(评审轮 3 用户拍板): 下载源不用 uv sync --frozen(它跳过 index 校验、按 uv.lock 记录的
# files.pythonhosted.org 绝对 URL 直连, 镜像索引无效)—— 改导出+pip 路线:
# uv export 从锁文件出钉版清单, uv pip install -r --index-url 显式指国内镜像。S2 运行期 delta
# 走同款(见 linux_env.py 头注交接注记)。
# WARN: uv export 不写 --generate-hashes(2026-11-12 首跑实测): 新版 uv(0.13.7 实测; 0.12.14 该
# 旗标同已移除)export 默认带 hash —— 写了直接 "unexpected
# argument" 构建自断。若未来 hash 默认行为再变, 以 `uv export --help` 实测为准。
COPY pyproject.toml uv.lock /root/env-template/
WORKDIR /root/env-template
RUN set -eux; \
    UV_PYTHON_DOWNLOADS=manual uv python install 3.13; \
    uv venv --python 3.13 /opt/venv-3.13; \
    uv venv --python 3.12 /opt/venv-3.12; \
    uv export --frozen --format requirements-txt --no-emit-project \
      -o requirements.txt; \
    uv pip install --python /opt/venv-3.13/bin/python --index-url "${UV_INDEX}" \
      -r requirements.txt; \
    uv pip install --python /opt/venv-3.12/bin/python --index-url "${UV_INDEX}" \
      -r requirements.txt

# ---------------------------------------------------------------------------
# 层 6 e2e 层: node_modules 模板(/opt/e2e-node)+ playwright chromium(D2: e2e 进环境)。
# playwright 系统依赖用官方 install-deps(依赖清单单点归 playwright, 不手抄防漂移;
# apt 源已在层 1 换国内); 浏览器二进制走 PLAYWRIGHT_DOWNLOAD_HOST(npmmirror)。
COPY package.json package-lock.json /opt/e2e-node/
WORKDIR /opt/e2e-node
ARG NPM_REGISTRY=https://registry.npmmirror.com
RUN npm ci --registry="${NPM_REGISTRY}" --no-fund --no-audit
RUN npx playwright install-deps chromium && rm -rf /var/lib/apt/lists/*
RUN npx playwright install chromium

# 常驻容器: 无服务面, 睡眠保活, 干活全走 docker exec(test.linux / e2e / mutants)
WORKDIR /root
CMD ["sleep", "infinity"]
