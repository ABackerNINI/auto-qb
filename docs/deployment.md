# Docker 部署

> 方案与决策单点: [memory-bank/plans/26-09-25-2241-plan-docker-deploy.html](../memory-bank/plans/26-09-25-2241-plan-docker-deploy.html)。
> 本文是操作手册: 架构 / 部署步骤 / 运维 / 升级回滚 / 备份迁移 / 排障。
> 文中数字除特别标注外均为 **2026-09-26 真机实测** (Docker Desktop 4.84 · Windows, 全功能关闭冒烟配置连真实 qB)。

auto-qb 是单进程长驻 Python 程序, 与容器的契约面很小: **配置文件、数据目录、Web 端口**三条边界。
一容器 = 一实例(单实例锁在 data_dir, 同数据卷双开会被拒绝 —— 是预期保护, 不是故障)。

## 1. 架构总览

```text
宿主机 (Windows / macOS / Linux)
├── qBittorrent WebUI  :16585 (哪都行, 只要容器网络可达)
└── Docker
    └── 容器 auto-qb:latest
        ├── auto-qb 进程 (ENTRYPOINT auto-qb, CMD /config/config.yml)
        │     └── 经 qB WebUI API 操作种子 —— 不经手种子文件, 无需挂载下载目录
        ├── /config  ← bind mount ./config        (config.yml, 必须可写)
        ├── /data    ← named volume auto-qb-data  (state.json / 锁 / 日志 / web.token)
        └── 8080     ← 宿主 8081                   (Web UI; 健康检查探的就是它)
```

| 边界 | 容器内路径 | 挂载方式 | 说明 |
|---|---|---|---|
| 配置 | `/config` | bind mount `./config` | **必须可写**: Web UI 保存配置会写回 config.yml 并留 `.bak`, 挂只读会废掉配置能力 |
| 数据 | `/data` | named volume `auto-qb-data` | `data_dir`: state.json / 单实例锁 / 日志 / web.token / hr/ / 跳检备份全在此; 换容器不丢状态 |
| 端口 | `8080` | 映射宿主 `8081` | 宿主 qB WebUI 若占 8080, 映射侧避开; 改 `web.port` 需同步 compose 的 `ports` 与 `healthcheck` |

配置文件内**不要写宿主路径**: 程序在容器里看到的文件系统就是挂载后的样子。

## 2. 前置条件

- Docker 20.10+ 与 Docker Compose v2 (`docker compose version` 可查)。
- 一台可达的 qBittorrent (WebUI 已开启) —— 跑在哪都不影响本方案, 只要容器网络能连上。
- Linux 宿主机上 qB 跑在宿主时, compose 已内置 `extra_hosts: host.docker.internal:host-gateway`,
  无需额外配置; Docker Desktop (Windows/macOS) 自带该入口。

## 3. 快速开始

```bash
# 0. (可选但建议) 预跑一遍校验, 免得容器反复重启才发现配置写错
uv run python -c "from auto_qb.config import load_config; load_config('config/config.yml'); print('OK')"

# 1. 准备配置目录(必须在仓库根执行: compose 挂载 ./config)
mkdir config
cp docker/config.example.yml config/config.yml

# 2. 编辑 config/config.yml: 填 qbittorrent 的 host / port / username / password
#    容器示例默认 host: host.docker.internal(qB 在宿主机), NAS/远程填 IP

# 3. 构建并启动(首次构建约 3.7 分钟; 依赖不变时只重建源码层, 约 9 秒)
docker compose up -d --build

# 4. 取 Web UI 密钥(首次启动随机生成, 持久化在数据卷; 重启不变)
docker exec auto-qb cat /data/web.token

# 5. 浏览器打开 http://localhost:8081 (宿主 8081 -> 容器 web.port 8080), 输入密钥登录
```

> ⚠ `config/` 已在 `.gitignore` 里(2026-09-26 起) —— 部署配置含真实 qB 凭据, 与根 `config.yml` 同一红线口径, 不会也不应进仓库。

## 4. 配置详解(容器场景)

示例配置 `docker/config.example.yml` 以 `minimal.yml` 为底, 按容器场景改了四处, **这四处不要改回去**:

| 键 | 容器值 | 为什么 |
|---|---|---|
| `data_dir` | `/data` | 对齐 compose 的 named volume 挂载点; 状态/锁/日志/token 全落这里 |
| `qbittorrent.host` | `host.docker.internal` | 容器里 `127.0.0.1` 指容器自己; 宿主机 qB 必须走这个入口 |
| `web.host` | `0.0.0.0` | 默认 127.0.0.1 时端口映射过去谁也连不上(自断访问) |
| `notify.enabled` | `false` | 容器无桌面会话, 平台原生通知预期不可用 |

### qB 地址怎么填(三案)

| qB 在哪 | `qbittorrent.host` 填什么 | 备注 |
|---|---|---|
| 宿主机(最常见) | `host.docker.internal` | Linux 宿主由 compose `extra_hosts` 补, Windows/macOS 开箱即用 |
| 同一个 compose 里 | qB 服务的服务名 | 走 compose 内部网络 |
| NAS / 远程 | 直接填 IP | 与容器化无关 |

### 功能开关与健康检查的耦合(❗最容易踩的坑)

`web.enabled: true` 在容器示例里**恒为 true** —— compose 的健康检查探的就是 Web 端口
(plan D6 的刻意设计)。**容器里关掉 Web UI (`web.enabled: false`), 程序照常跑, 但容器会
在约 1 分钟后永远显示 `unhealthy`**(实测) —— 不是故障, 是健康检查探测目标不存在。
想在容器里关 Web UI, 就必须同时删掉 compose 的 `healthcheck` 段, 否则监控会一直误报。

其余功能开关(分组 / 集数标签 / 标签清理 / 限速曲线 / 站点列表)与容器无关, 语义同
[configuration.md](configuration.md)。`trackers:` 留空 = 不匹配任何种子 = 不做任何管理动作
(全功能关闭的冒烟配置即以此保证对 qB 零写入)。

## 5. 启动验证清单

```bash
docker compose ps                        # ① STATUS 应为 Up (healthy), 约 12~21 秒内转 healthy
docker compose logs --tail=50            # ② 应有「启动 qB 管理器」「WEB UI 已启动」(均为 INFO), 无 ERROR
curl http://127.0.0.1:8081/ -i           # ③ 307 -> /atlas/ 静态页(免 token); 无 token 访问 /api/* 应 401
docker exec auto-qb cat /data/web.token  # ④ 64 位密钥; 浏览器输入它登录
```

登录后 `状态` 页种子数应与 qB 一致(接口口径: `GET /api/status` 的 `connected` / `torrents`)。

## 6. 日常运维

```bash
docker compose logs -f              # 看日志(stdout, INFO 起; 另有一份轮转文件在 /data/logs/auto-qb.log)
docker compose stop                 # 优雅停止: SIGTERM -> 落盘后退出码 0(实测约 1 秒, 宽限 30s)
docker compose start                # 再起: 标签历史/规则账本/限速状态接着上次继续
docker compose restart              # 重启(读的是同一份挂载配置)
docker compose up -d --build        # 升级: 拉新代码后重建镜像, 数据卷与配置不动
docker compose down                 # 停止并删容器(named volume 保留; 加 -v 才会删数据, 慎用)
docker compose exec auto-qb sh      # 进容器排障
docker stats auto-qb                # 资源占用
```

## 7. 升级与回滚

```bash
git fetch && git checkout <目标版本/commit>   # 或 git pull
docker compose up -d --build                 # 重建镜像并滚动替换容器; 数据卷/配置原样保留
```

- 依赖没变时重建只走源码层, 实测约 9 秒; 依赖变了走 `uv.lock` 全量重装(约 3.7 分钟)。
- 镜像内依赖由 `uv sync --frozen --no-dev` 逐字节复现, 不存在"锁外漂浮"的包。
- **回滚** = checkout 旧版本后 `docker compose up -d --build`。注意 state.json 只保证**向后兼容**:
  新版本写过的高版本 state 被旧版本读到时行为未定义 —— 回滚跨了写 state 的版本请先备份卷(见 §8)。
- 升级后看一眼 `docker compose logs --tail=50`: 启动序列应无 ERROR; 若报 qB 字段不兼容
  (`QbCompatError`)属 fail-fast 保护, 按提示处理, 不会静默带病运行。

## 8. 数据备份与迁移

named volume `auto-qb-data` 里有全部运行态(state.json / 日志 / web.token / hr/ / 跳检备份):

```bash
# 备份(停机更稳: docker compose stop 先优雅落盘)
docker run --rm -v auto-qb-clone4_auto-qb-data:/data -v "$(pwd)":/backup alpine \
    tar czf /backup/auto-qb-data-$(date +%F).tar.gz -C /data .

# 恢复到新机器/新卷
docker volume create auto-qb-clone4_auto-qb-data
docker run --rm -v auto-qb-clone4_auto-qb-data:/data -v "$(pwd)":/backup alpine \
    tar xzf /backup/auto-qb-data-$(date +%F).tar.gz -C /data
```

> 卷名前缀是 compose 项目名(目录名), 不同目录部署时以 `docker volume ls` 实际输出为准。
> 配置侧备份就是 `config/config.yml` 本身; Web UI 每次保存都会把上一版留到 `<data_dir>/config.yml.bak`
> (❗在**数据卷**里, 不在 config/ 旁边 —— 设计如此, 见 [webui/server/common.py](../src/auto_qb/webui/server/common.py))。

## 9. 健康检查语义

```yaml
test: ["CMD", "python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8080/', timeout=3)"]
interval: 30s / timeout: 5s / retries: 3 / start_period: 15s
```

- 探的是 **Web UI 端口**(slim 镜像没有 curl/wget, 用 python 内联探活); `GET /` 307 → `/atlas/`
  静态页, 非 `/api` 路径免 token —— 所以 healthy ≠ 已登录, 只代表"服务在听、前端资产在"。
- 实测启动后 **12~21 秒**转 healthy (start_period 15s 内的失败不计数, 之后每 30s 一次、连败 3 次判 unhealthy, 约 1 分钟)。
- `unhealthy` 的两种已知成因: ① `web.port` 改了而 compose 的 healthcheck/ports 没同步; ② `web.enabled: false`
  (见 §4)。容器**不会**因 unhealthy 被重启(健康状态 ≠ 存活), 程序照常运行。
- healthy 只证明 Web 层活着, 不证明 qB 连通 —— qB 连通看 `GET /api/status` 的 `connected`
  或日志里的连接错误。

## 10. 退出码与重启行为(2026-09-26 实测)

| 场景 | 退出码 | 日志特征 | 容器表现 |
|---|---|---|---|
| `docker stop` / SIGTERM | **0** | `[INFO] ... 停止`; state.json mtime = 停止瞬间 | exited, 不再重启(优雅停机) |
| 配置错误(校验失败/YAML 坏) | **1** | stderr `配置错误: ...` 聚合报错, 无堆栈 | 按 restart 策略重启 |
| 单实例锁被占 | **1** | stderr `另一实例已持有锁 ...`, 无堆栈 | 同上 |
| **连不上 qB** | **1** | stderr `无法连接 qBittorrent <host>:<port>: 请检查...` + 上一行 `连接 qBittorrent 失败` 的详细原因 | 同上 |

- `restart: unless-stopped` 对**任何**退出码都会拉起容器, 但 Docker 自带**指数退避**
  (100ms 起翻倍, 上限 1 分钟): 实测 qB 不可达时首轮 40 秒内约 9 次, 随后自动降到最多每分钟一次;
  qB 恢复可达后某次重启即转正常(`Up (healthy)`), **无需人工干预**。这就是宿主机重启后
  "qB 比 auto-qb 晚起来"场景的自愈方式。
- 连不上 qB 之所以退出码 1 而不是带病常驻: 非托管(CLI)模式走 fail-fast 契约
  (`QbConnectError` → stderr 干净消息), 托管模式(--tray)才按 main_tick 重试常驻。
- qB 在运行中途宕机**不需要**容器重启: 主循环内有重连退避(2s→2×→…→上限 30s), 恢复即自动接上。

## 11. 与宿主直跑的差异

- **时区**: HR 窗口、每日限速曲线、日志时间戳按容器本地时间。compose 默认 `TZ: Asia/Shanghai`, 按需改;
  改完 `docker compose up -d` 重建容器生效。
- **托盘 / 桌面通知不可用**: 无桌面环境属预期。`notify.enabled` 示例已显式关闭; `--tray` 模式不要在容器里用。
- **qB 种子文件不经手**: 程序只经 qB WebUI API 操作, **不需要挂载下载目录** —— 下载目录归 qB 管, qB 在哪文件就在哪。
- **日志双轨不变**: stdout (`docker logs -f` 开箱可用) + `/data/logs/auto-qb.log`(轮转 10MiB×5, 随数据卷持久化)。
- **单实例锁**: 同一个 `/data` 卷只能起一个实例; 想多开就换一个数据卷 + 换一套配置。
- **GUI 三件(pystray/customtkinter/Pillow)在镜像里但用不到**: 仅托盘分支懒加载, 实测合计 6.9MB, 不值得为它们改依赖布局。

## 12. 安全提示

容器场景 `web.host` 必须开 `0.0.0.0`, 这会把**可删除种子、可改配置**的管理界面暴露到端口映射上:

- `web.token` 保持强制鉴权(示例配置 `skip_local_verify: false`; `web.token: ""` = 首次启动随机生成 64 位密钥, 密钥内容不进日志);
- 端口映射只绑本机可写 `"127.0.0.1:8081:8080"`, 或置于反向代理之后再加一层认证;
- 公网/局域网直接暴露务必配合防火墙(与 README「安全提示」同口径);
- 配置树接口对敏感字段按掩码返回, 浏览器侧不会明文回显 qB 密码; 保存时用磁盘旧值还原哨兵, 密码不会被占位串写坏。

## 13. 排障速查

| 现象 | 原因与处置 |
|---|---|
| 反复重启, 日志报 `无法连接 qBittorrent <host>:<port>` | fail-fast(退出码 1, 无堆栈): 查 qbittorrent.host/port/凭据; 宿主 qB 用 `host.docker.internal`, 别写 127.0.0.1(那指容器自己)。qB 短暂不可达(如宿主刚重启)不用管, Docker 退避重启会自愈(§10) |
| 容器一直 `unhealthy` | ① `web.port` 与 compose healthcheck/ports 不同步; ② `web.enabled: false`(健康检查没有探测目标, §4); ③ 想 Web/健康检查都不要就删 compose 的 `healthcheck` 段 |
| 日志报「另一实例已持有锁」 | 同一 `/data` 卷已有实例在跑(或宿主直跑的实例共用了数据目录): 停掉另一个, 或换数据卷 |
| 浏览器打不开 8081 | `web.host` 必须是 `0.0.0.0`(示例配置已改); 查 compose `ports` 与 `web.port` 是否一致; 密钥看 `docker exec auto-qb cat /data/web.token` |
| Web UI 保存配置报错 | `/config` 被挂成只读了: 去掉 `:ro`, Web UI 要写回 config.yml + `.bak` |
| 改了 `web.port` 没生效 | 要同步**三处**: config 的 `web.port`、compose 的 `ports`、compose 的 `healthcheck` |
| HR 窗口/每日曲线时间不对 | `TZ` 与宿主不一致: 改 compose environment 后 `docker compose up -d` 重建容器 |
| 配置校验失败(列 N 处) | fail-fast 聚合报错, 按日志逐条改 config.yml; 示例配置可直接对照 |
| 想验证配置又不想起容器 | 见 §3 第 0 步的本地校验一行 |
| Git Bash 里 `docker exec auto-qb cat /data/web.token` 报找不到文件 | Git Bash 把**容器内路径**也按 POSIX→Windows 转换了(`/data/...` → `D:/Program Files/Git/data/...`); 前缀 `MSYS_NO_PATHCONV=1` 即可 |
| `docker compose run` 传配置路径报「配置文件读取失败: D:/Program Files/Git/...」 | 同上, `MSYS_NO_PATHCONV=1 docker compose run --rm auto-qb /config/xxx.yml` |

## 14. 实测基线(2026-09-26)

| 项 | 实测 |
|---|---|
| 镜像体积 / 构建耗时 | 252MB; 冷构建 223s, 依赖不变时重建 9s |
| 启动 → healthy | 12~21s (healthcheck start_period 15s) |
| 优雅停止 | 约 1s, 退出码 0, state.json 落盘于停止瞬间 |
| 连不上 qB 时 | 退出码 1, 约 1s; Docker 退避重启上限 1 次/分钟 |
| Web UI 密钥 | 64 位, 持久化 `/data/web.token`, 跨重启复用 |
| 配置写回 | round-trip 保留注释; `.bak` 落 `<data_dir>/<配置名>.bak`; L0/L1/L2 热重载即时生效, R 级(data_dir/state_file)需重启 |
| 全功能关闭时 state.json | 仅 `upload_snapshots`(~16KB); 91 种子库全程零写入实测通过 |
