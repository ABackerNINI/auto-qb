# Docker 部署

> 方案与决策单点: [memory-bank/plans/26-09-25-2241-plan-docker-deploy.html](../memory-bank/plans/26-09-25-2241-plan-docker-deploy.html)。
> 本文是操作手册: 构建 / 配置 / 升级 / 排障, 以及与宿主直跑的差异。

auto-qb 是单进程长驻 Python 程序, 与容器的契约面很小: **配置文件、数据目录、Web 端口**三条边界。
一容器 = 一实例(单实例锁在 data_dir, 同数据卷双开会被拒绝 —— 是预期保护, 不是故障)。

## 前置条件

- Docker 20.10+ 与 Docker Compose v2(`docker compose version` 可查)。
- 一台可达的 qBittorrent(WebUI 已开启)—— 它跑在哪都不影响本方案, 只要容器网络能连上。
- Linux 宿主机上 qB 跑在宿主时, compose 已内置 `extra_hosts: host.docker.internal:host-gateway`,
  无需额外配置; Docker Desktop(Windows/macOS)自带该入口。

## 快速开始

```bash
# 1. 准备配置目录(必须在仓库根执行: compose 挂载 ./config)
mkdir config
cp docker/config.example.yml config/config.yml

# 2. 编辑 config/config.yml: 填 qbittorrent 的 host / port / username / password
#    容器示例默认 host: host.docker.internal(qB 在宿主机), NAS/远程填 IP

# 3. 构建并启动
docker compose up -d --build

# 4. 取 Web UI 密钥(首次启动随机生成, 持久化在数据卷)
docker exec auto-qb cat /data/web.token

# 5. 浏览器打开 http://localhost:8081 (宿主 8081 -> 容器 web.port 8080), 输入密钥登录
```

## 三条边界(挂载与端口)

| 边界 | 容器内路径 | 挂载方式 | 说明 |
|---|---|---|---|
| 配置 | `/config` | bind mount `./config` | **必须可写**: Web UI 保存配置会写回 config.yml 并自动留 .bak, 挂只读会废掉配置能力 |
| 数据 | `/data` | named volume `auto-qb-data` | `data_dir`: state.json / 单实例锁 / 日志 / web.token / hr/ / 跳检备份全在此; 换容器不丢状态 |
| 端口 | `8080` | 映射宿主 `8081` | 宿主 qB WebUI 若占 8080, 映射侧避开; 改 `web.port` 需同步 compose 的 `ports` 与 `healthcheck` |

配置文件内**不要写宿主路径**: 程序在容器里看到的文件系统就是挂载后的样子。

## 与宿主直跑的差异

- **时区**: HR 窗口、每日限速曲线、日志时间戳按容器本地时间。compose 默认 `TZ: Asia/Shanghai`, 按需改。
- **托盘 / 桌面通知不可用**: 无桌面环境属预期。`notify.enabled` 在示例配置里已显式关闭;
  `--tray` 模式不要在容器里用。
- **qB 种子文件不经手**: 程序只经 qB WebUI API 操作, **不需要挂载下载目录** —— 下载目录
  归 qB 管, qB 在哪文件就在哪。
- **日志双轨不变**: stdout(`docker logs -f` 开箱可用) + `/data/logs/auto-qb.log`(随数据卷持久化)。
- **单实例锁**: 同一个 `/data` 卷只能起一个实例; 想多开就换一个数据卷 + 换一套配置。

## 日常运维

```bash
docker compose logs -f              # 看日志(stdout, INFO 起)
docker compose stop                 # 优雅停止: SIGTERM -> 落盘后退出码 0(宽限 30s)
docker compose start                # 再起: 标签历史/规则账本/限速状态接着上次继续
docker compose up -d --build        # 升级: 拉新代码后重建镜像, 数据卷与配置不动
docker compose down                 # 停止并删容器(named volume 保留; 加 -v 才会删数据, 慎用)
docker compose exec auto-qb sh      # 进容器排障
```

健康检查: `docker ps` 里 `healthy/unhealthy` 探的是 Web UI 端口(`GET /` → 307 → 静态页, 免 token)。
`unhealthy` 先看 `docker compose logs`, 多为 Web 端口被改而 healthcheck 未同步。

## 排障速查

| 现象 | 原因与处置 |
|---|---|
| 启动即退出, 日志报「无法连接 qBittorrent」 | fail-fast 路径(干净退出码 1, 无堆栈): 查 qbittorrent.host/port/凭据; 宿主 qB 用 `host.docker.internal`, 别写 127.0.0.1(那指容器自己) |
| 日志报「另一实例已持有锁」 | 同一 `/data` 卷已有实例在跑(或宿主直跑的实例共用了数据目录): 停掉另一个, 或换数据卷 |
| 浏览器打不开 8081 | `web.host` 必须是 `0.0.0.0`(示例配置已改); 查 compose `ports` 与 `web.port` 是否一致 |
| Web UI 保存配置报错 | `/config` 被挂成只读了: 去掉 `:ro`, Web UI 要写回 config.yml + .bak |
| HR 窗口/每日曲线时间不对 | `TZ` 与宿主不一致: 改 compose environment 后 `docker compose up -d` 重建容器 |
| 配置校验失败(列 N 处) | fail-fast 聚合报错, 按日志逐条改 config.yml; 示例配置可直接对照 |

## 安全提示

容器场景 `web.host` 必须开 `0.0.0.0`, 这会把**可删除种子、可改配置**的管理界面暴露到端口映射上:

- `web.token` 保持强制鉴权(示例配置 `skip_local_verify: false`);
- 端口映射只绑本机可写 `"127.0.0.1:8081:8080"`, 或置于反向代理之后再加一层认证;
- 公网/局域网直接暴露务必配合防火墙(与 README「安全提示」同口径)。
