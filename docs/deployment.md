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

示例配置 `docker/config.example.yml` 以 `minimal.yml` 为底, 按容器场景改了**五处**, **这五处不要改回去**:

| 键 | 容器值 | 为什么 |
|---|---|---|
| `data_dir` | `/data` | 对齐 compose 的 named volume 挂载点; 状态/锁/日志/token 全落这里 |
| `qbittorrent.host` | `host.docker.internal` | 容器里 `127.0.0.1` 指容器自己; 宿主机 qB 必须走这个入口 |
| `web.host` | `0.0.0.0` | 默认 127.0.0.1 时端口映射过去谁也连不上(自断访问) |
| `notify.enabled` | `false` | 容器无桌面会话, 平台原生通知预期不可用 |
| `grouping.check_missing_files` | `false` | ❗缺文件扫描读宿主磁盘, 容器里恒判"文件缺失" ⇒ 误暂停整组 + 打 MISSING 标签(真实写 qB)。详见 §11.3; 想保留该功能见 §11.5 |

> 这五处由 `tests/test_config.py::test_example_docker_config_yml_passes_fail_fast` 钉住 —— 示例文件没有守阵会静默漂移。

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

其余功能开关(集数标签 / 标签清理 / 限速曲线 / 站点列表)与容器无关, 语义同
[configuration.md](configuration.md)。**例外: 分组的 `check_missing_files` 与容器强相关** ——
它要读真实磁盘, 容器里不关会误暂停种子并打 `MISSING` 标签, 详见 §11.3 / §11.4。
`trackers:` 留空 = 不匹配任何种子 = 不做任何管理动作
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

## 11. 容器化后的功能变化(失效 / 降级 / 不变)

> 本节是「用 Docker 跑之后, 哪些功能跟宿主直跑不一样」的**单点清单**。
> 除标注外均为 **2026-09-26 在 `auto-qb:latest` 镜像内实测**(python:3.12-slim-bookworm)。
> 踩坑记录见 [memory-bank/pitfalls/ops/docker-host-features.md](../memory-bank/pitfalls/ops/docker-host-features.md)。

### 11.1 四类根因

容器与宿主的差异全部落在下面四类上, 判断任何功能先看它命中哪一类:

| 类 | 根因 | 波及 |
|---|---|---|
| **A 宿主路径不可见** | 程序读的是 **qB 报回来的宿主保存路径**(如 `D:\Downloads\x` / `/volume1/downloads`), 而容器里没有这块盘 ⇒ `os.path.exists` 恒 False、`realpath` 被拼成 `/app/D:/Downloads` | 打开文件夹 · 目录浏览/新建 · 缺文件扫描 · 跳检前置检查 · 规则 `exists()`/`disk_*()` |
| **B 外部程序缺失** | slim 镜像没有 `xdg-open` / `notify-send` / `curl` / `wget`(实测 `command -v` 全 MISSING) | 打开文件夹 · 桌面通知 · 自定义校验程序 |
| **C 无桌面会话** | 容器没有显示器 / 通知中心 / 任务栏 | 桌面通知 · `--tray` 托盘 |
| **D 网络身份与时区** | 容器里 `127.0.0.1` 指容器自己; 本地时间由 `TZ` 决定 | qB 地址 · `web.host` · HR 窗口 / 每日限速曲线 / 日志时间戳 |

### 11.2 可用性矩阵

图例: ❌ 失效 · ⚠️ 降级或行为改变 · ✅ 与宿主直跑一致

| # | 功能 | 状态 | 容器内实际表现 |
|---|---|---|---|
| 1 | 右键「**打开目标文件夹**」(`POST /api/open-path`) | ❌ | 弹 toast「打开目标文件夹失败: 目标目录不存在或不可访问」(**404**) —— 宿主路径在容器内 `isdir` 为 False。即使把下载目录挂成**可见**, 也会变成 **500**: 走 Linux 分支 `xdg-open`(B 类缺失) ⇒ `FileNotFoundError: 'xdg-open'` 未被捕获(实测 `open_path('/tmp')` 直接抛) |
| 2 | 抽屉路径行「打开目录」 | ❌ | 同上, 同一端点 |
| 3 | 添加种子「**浏览目录**」(`GET /api/fs/dirs`) | ❌ | **404/403**。允许根 = qB 报回的宿主保存路径, `realpath` 后不落在任何根内 ⇒ 403「路径不在允许的保存路径范围内」 |
| 4 | 添加种子「**新建文件夹**」(`POST /api/fs/mkdir`) | ❌ | **403**(同上白名单判据) |
| 5 | 添加种子「保存位置」下拉 (`GET /api/paths`) | ⚠️ | **仍返回宿主路径**(纯字符串聚合, 不校验存在性)。手填一个 qB 侧合法路径照常能加种 —— qB 才是路径的裁判; 只是不能"浏览着选" |
| 6 | **缺文件扫描**(`grouping.check_missing_files`, **默认 true**) | ❌ **会误伤** | 见 §11.3 —— 这是唯一会**写坏 qB**的一条 |
| 7 | 跳检前置文件完整性检查(`checking` 动作 / `check_filelist`) | ❌ | 恒返回「文件缺失: xxx」⇒ `ActionResult.skip("全量校验前置检查未通过: ...")` ⇒ **跳检永不执行**。保守降级, 不破坏数据 |
| 8 | 规则表达式 `exists(path)` | ⚠️ **静默** | 恒返回 False ⇒ 依赖它的条件**恒不成立**, 不报错、不告警, 规则看着"没触发" |
| 9 | 规则表达式 `disk_total(path)` / `disk_used(path)` | ❌ | `shutil.disk_usage` 抛 `OSError` ⇒ 表达式报 `ExprError: 磁盘不可用: '<路径>'`(显式报错, 不静默) |
| 10 | `basic_check: custom` 自定义校验程序 | ❌ | 程序不在镜像里 ⇒ `FileNotFoundError` 被 `except Exception` 吞掉 ⇒ 每个候选一条 WARNING「自定义校验程序执行异常」⇒ **全部判为非参考**。日志洪水风险 |
| 11 | 桌面通知(`notify.*`) | ❌ **静默** | Linux 分支调 `notify-send`(缺失) ⇒ `send()` 返回 **False** 且只 DEBUG 一条。示例配置已 `enabled: false` |
| 12 | `--tray` 托盘模式 | ❌ | 无显示环境; 托盘菜单里的 `webbrowser.open` 同样无处可开。**不要在容器里用** |
| 13 | 时区相关(HR 窗口 / 每日限速曲线 / 日志时间戳 / `notify.quiet_hours`) | ⚠️ | 按**容器**本地时间。compose 默认 `TZ: Asia/Shanghai`, 按需改后 `docker compose up -d` 重建生效 |
| 14 | qB 地址 | ⚠️ | 容器内 `127.0.0.1` 是容器自己 ⇒ 宿主 qB 填 `host.docker.internal`(见 §4) |
| 15 | `web.host` | ⚠️ | 必须 `0.0.0.0`, 否则端口映射探不到(见 §4 / §12) |
| 16 | 单实例锁 | ✅ | `filelock` 在容器里走 fcntl, 语义不变 —— 同一 `/data` 卷只能起一个实例。⚠️ **别让宿主实例与容器实例共用一个 data_dir**: 跨 OS 锁机制不同(msvcrt ↔ fcntl), 相互挡不住 |
| 17 | 日志 | ✅ | stdout(`docker logs -f`)+ `/data/logs/auto-qb.log`(默认派生自 `<data_dir>/logs/`), 轮转 10MiB×5 随卷持久化; Web UI 的 `/api/log` 读的就是它 |
| 18 | state / 锁 / `web.token` / `hr/` / 跳检备份 | ✅ | 全落 `/data`, 与平台无关 |
| 19 | 配置读 / 保存 / 热重载 / `.bak` | ✅ | 只要 `/config` 可写(见 §1 表格) |
| 20 | 导出 `.torrent`、上传种子、复制种子信息 | ✅ | 浏览器侧交付。`.torrent` 由前端 base64 后经命令队列**内存直传** qB, 零临时文件、不落容器盘 |
| 21 | 「复制种子信息」剪贴板 | ⚠️ | 经 `http://<局域网IP>:8081` 访问时非安全上下文 ⇒ `navigator.clipboard` 不可用 ⇒ 自动降级 `execCommand`, 功能仍在 |
| 22 | HR 抓取、限速曲线、标签/分类、规则引擎(不碰磁盘的部分)、tracker 限速 | ✅ | 纯 qB API + 字符串匹配, 与文件系统无关 |
| 23 | 优雅停机 / 退出码契约 | ✅ | 见 §10 |
| 24 | GUI 三件(pystray / customtkinter / Pillow) | — | 在镜像里但**只有托盘分支懒加载**, 实测合计 6.9MB, 不值得为它们改依赖布局 |

### 11.3 ❗唯一会写坏 qB 的一条: 缺文件扫描

`core/mixins/grouping.py::_check_missing_files` 拿 qB 报回的 `save_path` 拼上文件名后直接 `os.path.exists`:

```python
full_path = utils.add_long_path_prefix_for_win(os.path.normpath(os.path.join(rep.save_path, fname)))
if not os.path.exists(full_path):   # 容器里恒 False(A 类)
```

命中后是**真实写操作**: `torrents_stop` 暂停整组 + 给每个成员打 `MISSING` 标签。

- **触发时机**: 组内种子被删除 / 上传转暂停 / 进入 errored / `save_path` 变化 —— 事件驱动, **不是每轮全扫**,
  所以表现为"时不时有一批种子被无故暂停 + 打 MISSING", 比必现更难排查。
- **默认开着**: `check_missing_files` 默认 `true` ⇒ **不显式关就会踩**。容器示例 `docker/config.example.yml`
  已自 2026-09-26 起显式写 `false`(§4 表格第五项, 有守阵测试钉住); **自己手搓的容器配置仍要记得关**。
- **处置**: 容器部署**必须**显式写 `grouping.check_missing_files: false`(或按 §11.5 把下载目录挂进去再开)。
- 不关也没有替代告警: 它只写 WARNING 日志, 而容器里通知是哑的(第 11 项) ⇒ 用户只能从 `docker compose logs` 里发现。

### 11.4 必调 / 建议的配置项

| 键 | 容器取值 | 为什么 |
|---|---|---|
| `grouping.check_missing_files` | **`false`** | §11.3, 不关会误暂停 + 误打 MISSING 标签(真实写 qB) |
| `notify.enabled` | `false` | C 类, 示例已写死 |
| `qbittorrent.host` | `host.docker.internal` | D 类 |
| `web.host` | `0.0.0.0` | D 类 |
| `data_dir` | `/data` | 对齐 named volume |
| `basic_check` | 不要用 `custom` | B 类, 自定义程序不在镜像里, 且失败会刷 WARNING |
| 规则里 `exists()` / `disk_*()` | 不要写 | A 类, 一个恒 False、一个直接报错 |

### 11.5 想救回 A 类能力: 把下载目录挂进容器(仅 Linux 宿主可行)

A 类(除 #1 外)全部是"路径看不见"造成的 —— 把下载目录挂到**与 qB 完全相同的绝对路径**即可救回:

```yaml
services:
  auto-qb:
    volumes:
      - ./config:/config
      - auto-qb-data:/data
      - /volume1/downloads:/volume1/downloads:ro   # ← 与 qB 报回的 save_path 逐字一致
```

- **只读 `:ro` 即可**救回: 缺文件扫描(#6)、跳检前置检查(#7)、`exists()`(#8)、`disk_*()`(#9)、目录浏览(#3)。
  要「新建文件夹」(#4)才需要可写。
- **Windows 宿主无解**: qB 报回的是 `D:\Downloads\...` 盘符路径, 在 Linux 容器里无法作为挂载点存在
  (`realpath` 只会把它拼成 `/app/D:/Downloads`)。这类部署**只能**按 §11.4 关掉相关功能。
- **打开文件夹(#1)挂了也没用**: 它是 B 类(缺 `xdg-open`), 不是 A 类 —— 除非把下载目录挂进去
  **并且**在镜像里装 `xdg-open`, 但容器里没有文件管理器可开, 装了也是空转。**结论: 容器内该功能不可用**,
  替代做法是用抽屉里的「复制路径」按钮拿到路径, 再回到宿主资源管理器打开。
- 挂载后 `/api/fs/dirs` 的允许根白名单(派生自 `save_path`)就能命中, 目录浏览与新建自然恢复。

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
| 右键「打开目标文件夹」报「目标目录不存在或不可访问」 | **预期失效(不是故障)**: 宿主保存路径在容器内不可见 ⇒ 404。挂下载目录也救不回来(缺 `xdg-open`), 用「复制路径」代替(§11.2 #1) |
| 添加种子点「浏览目录」报「路径不在允许的保存路径范围内」 | 同上, 允许根是宿主路径。手填路径可用; 想恢复浏览按 §11.5 挂下载目录(§11.2 #3/#4) |
| 一批种子被无故暂停并打上 `MISSING` 标签 | ❗缺文件扫描误判(§11.3): 立刻把 `grouping.check_missing_files` 设为 `false` 并重启; 已打的标签需手工清理 |
| 日志刷「自定义校验程序执行异常」 | `basic_check: custom` 的外部程序不在镜像里 ⇒ 全判非参考。容器里改用 `filelist` / `piecehashes`(§11.2 #10) |
| 规则一直不触发且不报错 | 检查条件里是否用了 `exists()` —— 容器内恒 False(§11.2 #8); `disk_total()` 则会显式报「磁盘不可用」 |
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
