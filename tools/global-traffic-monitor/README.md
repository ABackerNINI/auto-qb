# global-traffic-monitor (gtm)

整机流量历史记录小工具 —— TrafficMonitor 替代。

独立于 auto-qb 主进程、开机自启: 以 psutil 采样整机全适配器流量 (排除回环与
down 网卡), 以 TrafficMonitor 兼容格式 (`history_traffic.dat`: 每行
"YYYY/MM/DD 上传KB/下载KB") 原子落盘; 当日累计上下行合计变化超过阈值
(默认 100 MiB) 时, 向所有存活订阅的 auto-qb 实例推送通知 (带单调事件号),
后者即时重读历史文件并刷新 WebUI 历史流量图。

## 定位与边界

- 工具是 `history_traffic.dat` 的**唯一写者**; 落盘用「临时文件 + os.replace」
  原子替换, 任意数量读者在任意时刻见到完整一致的文件。
- 工具**不参与**限速联动, 仅记录整机流量历史 (与 TrafficMonitor 同口径)。
- 多个 auto-qb 实例可同时订阅 (各自端点 + token + 心跳租约), 互不干扰。
- 通知推送与文件落盘解耦: 推送失败不影响落盘, 订阅者丢失通知可靠慢轮询兜底,
  两条通道互为冗余。

## 依赖与隔离

- 运行时依赖 psutil (采集) + filelock (单实例锁) + pyyaml (config.yml 解析, 与
  auto-qb 同族); HTTP 控制面与客户端全部 stdlib (`http.server` /
  `urllib.request`) —— 三平台 pip install 即装。
- 自带独立 venv (uv 管理, 落在本目录 `.venv/`), 与 auto-qb 主项目环境互不污染。

## 目录结构

```
src/gtm/
  __init__.py   版本与包说明
  __main__.py   CLI 入口 (global-traffic-monitor): run 主循环 (S2/S4) + claim (§03) + install/uninstall-autostart (S5) + endpoint (S13)
  config.py     工具配置加载/校验/热重载 (S3)
  sampler.py    psutil 采样 + 日界累计 + 重置/恢复 (S1)
  storage.py    TM 兼容落盘 + state.json 原子写 + 单实例锁 (S2)
  server.py     本地控制面 127.0.0.1:<随机端口> (S3/S13)
  notifier.py   阈值事件推送订阅者 (S4)
  installer.py  三平台自启幂等注册/卸载 (S5)
  identity.py   正主注册与让位判定(三处 ID + 启动矩阵 + 注记 + 代拉, §03)
tests/          模块守阵 (test_smoke.py S0; test_sampler.py S1; test_storage.py S2; test_config.py + test_server.py S3; test_notifier.py S4; test_installer.py S5; test_identity.py §03; manual_e2e_relay.py 为手动 e2e 复算脚本, 不入套件)
```

安装目录内另有第二启动器 `claim.cmd` / `claim.sh`(人工易主入口, 与 `launch.*` 同族)。

## 运行 (S2-S4)

```bash
global-traffic-monitor run [--data-dir DIR] [--autostart]   # 前台采样-落盘主循环 + 控制面
global-traffic-monitor claim [--data-dir DIR]               # 人工易主: 重登记本安装为正主 (§03/D5)
global-traffic-monitor endpoint                             # 读发现指针打印当前端点 host:port / token_path / data_dir (S13)
```

`run` 启动先过**正主注册判定**(见下节): 非正主安装启动即让位(代拉正主后立即退出),
自身不写任何数据。`claim` 是唯一人工易主通道, 入口零参数启动器 `claim.cmd` /
`claim.sh`(与 `launch.*` 同族, D19; auto-qb 设置页「以本安装重登记」按钮经二次确认后
有界前台执行它)。

`--autostart` 是布尔开关 (S14/D13): 只表示「本次拉起顺带幂等注册开机自启」, 不承载
取值; **是否真注册由工具 config `autostart` 唯一裁决** (用户关过 = `false` ⇒ 本次
`no-op`, 不被自动装回)。不带该开关的拉起 (如自启项自己那条 `run --data-dir`) 不做任何
注册尝试。

数据目录默认落在**工具安装目录下的 `data/`** (环境变量 `GLOBAL_TRAFFIC_MONITOR_DATA_DIR`
优先; 旧用户级目录 `%LOCALAPPDATA%/gtm` 等首启**一次性搬迁**), 落 `history_traffic.dat`
(TM 兼容) + `state.json`(每次采样原子写, 含订阅注册表, kill -9 丢失窗口 ≤ 采样间隔) +
`config.yml`(配置, PUT /config 热重载 last-writer-wins) + `monitor.token`(控制面密钥,
首启原子生成)。单实例锁与发现指针锚在**用户级指针目录** (`%LOCALAPPDATA%/global-traffic-monitor/`
· `~/Library/Application Support/global-traffic-monitor/` · `~/.local/share/global-traffic-monitor/`)
的 `instance.lock` / `endpoint.json` (S12/D6/D8)。单轮落盘失败记 ERROR 并在下一轮重试,
不杀守护进程; Ctrl+C 优雅退出(最终落盘 + 释放锁 + 停控制面)。

## 正主注册与让位 (计划 26-10-20-1316 §03)

同机可能并存**多份安装**(多个 auto-qb clone 各带一份 gtm) 与**多个 auto-qb 实例**,
而数据落点默认跟随安装(`<安装>/data`)。若不加约束: 工具死亡后**先启动的一方**会按
对称逻辑拉起自己那份安装、占领指针与数据落点 —— 两份数据互不相通(A/data 历史成孤儿)。
正主注册把「谁是唯一写者」变成机器级显式事实: **整机只有一个安装写数据**(注册正主),
非正主安装启动即让位, 恢复/移动/易主/归并全部是显式人工动作。

### 三处 ID(文件名同为 `tool-id`, uuid, 不跨机有意义)

| 位置 | 文件 | 角色 | 写者 |
|---|---|---|---|
| 安装目录 | `<安装>/tool-id` | 我是谁(先于数据可读, 定引导顺序) | 工具首启生成 |
| 指针目录 | `primary.json` | 机器注册的正主 `{schema, id, install_path, data_dir, version}` | 认领(O_EXCL 原子建)/ `claim` |
| 数据目录 | `<data>/tool-id` | 这份数据归谁写(版本血统防线) | 正主认领时写入 |

指针目录 = `%LOCALAPPDATA%/global-traffic-monitor/` · `~/Library/Application
Support/global-traffic-monitor/` · `~/.local/share/global-traffic-monitor/`(与
`endpoint.json` / `instance.lock` 同址, S12)。

### 启动判定矩阵(在取单实例锁 / 绑端口 / 解析数据目录**之前**完成; 让位方全程不持锁、不写数据)

| 分支 | 判据 | 动作 |
|---|---|---|
| ① 认领 | 无 `primary.json` | O_EXCL 原子建记录(自己三项) -> 正主路径 |
| ② 正主 | `id` 同且 `install_path` 同 | 正主路径 |
| ③ 拒绝 | `id` 同但 `install_path` 异(拷贝件 / 安装被移动) | 拒绝启动 + 写注记, 人工改记录或删记录重认 |
| ④ 让位 | `id` 异 | 记录自洽校验 -> 自洽: **代拉正主后立即退出**(不等待); 矛盾(目标安装 `tool-id` 与记录 id 不符 / 目标即自身): 写注记退出 |

正主路径续查数据归属: `<data>/tool-id` 缺失 -> 写入认领; 相同 -> 过; **不同 ->
fail-fast**(「该数据属于其它安装」, 拒绝跨版本接管)。记录**只认领时写一次**, 此后
**零自动刷新**; 唯一例外 = 正主启动时补写为空的 `data_dir` 信息位。记录/注记损坏或
schema 未知一律按缺失或矛盾降级(WARNING), 不死锁、不静默、不猜字段。

### claim —— 唯一人工易主通道

入口是安装目录内第二启动器 `claim.cmd` / `claim.sh`(**零参数**, D19 同族; auto-qb
设置页「以本安装重登记」按钮经**二次确认**后有界前台执行, timeout 30s, 退出码与人读
输出原样展示)。护栏顺序(D5):

1. **非阻塞试单实例锁** —— 工具正在跑 -> 拒绝(「请先停止再重登记」);
2. **数据归属校验** —— `<data>/tool-id` 属于其它安装 -> 拒绝(与启动矩阵同一判据);
3. 通过 -> **原子重写 `primary.json`**(id / install_path / data_dir 三项全用本安装
   事实)+ 清让位注记 -> 释放锁, 退出 0。

标准流程(易主到本安装): **停止工具 -> 以本安装重登记 -> 立即拉起**。缺 claim 启动器
= 旧安装, 按钮点击时提示升级。

### 状态注记 `deferred.json`(工具侧书写, auto-qb 只读展示)

让位(④)与被拒(③)时工具书写(谁让位 / 代拉目标 / 结论 / 时间戳); **正主成功启动或
claim 成功时由权威方清除**。auto-qb 设置页状态区据此展示「主工具注册于 X, 当前未在
运行」类文案 —— 判定在工具侧, 展示在 auto-qb 侧, 永不来反(auto-qb 零记录读写)。

### 纪律(给人)

- **禁止拷贝安装目录**: 同 id 异 path 会被 ③ 拒绝(放行拷贝件会让两份同 id 数据静默
  分叉)。要迁移就整目录移动, 或删记录重新认领。
- **新机 / 重装先启想当正主的那份(A)**: 先启动的一方认领; 启反了用 claim 显式矫正
  (先停工具)。
- **移动安装目录**: `realpath` 归一对不上即 ③; 确认本人后编辑 `primary.json` 的
  `install_path`, 或删除该记录让本安装重新认领。
- **存量已分裂数据(两份 dat)**: 工具**不自动选举、不自动归并**。人工步骤: 选定保留
  目录 -> 把另一份的 `history_traffic.dat` 历史行按需合并进去(或直接选定保留哪份)
  -> 保证 `<data>/tool-id` 与正主一致 -> 启动或 claim。删 `<data>/tool-id` 是显式
  人工动作, 工具不提供绕过开关。
- **记录损坏**: 按缺失或矛盾降级(WARNING); 处置 = 人工修复 `primary.json` 或删除它
  后重启重新认领。

### 手动 e2e 复算(双安装 + 真进程)

```bash
# 在仓库根, 用仓库 venv 的 python(它没装 gtm, PYTHONPATH 才指得动拷贝件):
.venv/Scripts/python.exe tools/global-traffic-monitor/tests/manual_e2e_relay.py
```

复算「A 起 -> A 崩溃 -> B 先起 -> B 代拉 A -> A 指针回来 -> 同一 dat -> claim 两态
护栏」全链路(真起子进程, 不入 pytest 套件 —— sidefx 的 POPEN 白名单不放行)。

## 控制面 (S3)

`http://127.0.0.1:<随机端口>` (默认 `http_port: 0` = 内核分配随机端口, S13/D9; 占用即
fail-fast), 全部端点需 `Authorization:
Bearer <monitor.token>` (`secrets.compare_digest` 比对, 缺/错 401):

| 端点 | 说明 |
|---|---|
| `GET /status` | 采样状态 (当日累计/末事件号/订阅者数/文件路径/配置回显/uptime) |
| `PUT /config` | 全量校验 (聚合报错) -> 原子写 config.yml -> 热重载 |
| `POST /subscribe` | `{endpoint, token}` 注册订阅, 返回 id + 租约参数 |
| `POST /heartbeat` | `{id}` 心跳续租 (订阅方每 60s; 未知 id 404) |
| `POST /unsubscribe` | `{id}` 注销 (幂等, 未知 id 404) |
| `POST /autostart` | `{action: install\|uninstall}` 幂等注册/卸载开机自启 (S6 设置页开关; 在工具进程内跑 installer, `sys.executable` 即自启项要指向的解释器; 成功**回写工具 config `autostart`** —— 自启意图的唯一裁决权, S14/D13; 平台不支持 501 / 命令失败 500 / 载荷非法 400) |
| `POST /shutdown` | 优雅退出 (1737 S3 设置页「关闭工具」代理): **先回 200 再置停止信号**, 退出走 `run` 的 finally (最终落盘 + 释放锁 + 停控制面 + 删指针); 未绑定 stop_event 时只 200 + WARNING |

租约: `last_heartbeat + lease_ttl` (默认 3M = 180s) 过期剔除 (懒剔除, 每个已鉴权
请求入口先 prune)。注册表落 state.json, 重启续存。配置键与默认值见计划 §05;
非法键/类型/范围/正则一次性聚合拒绝 (黄金法则 4), 拒绝不落盘不换配置。

**时间/大小是复合串** (S7/D13): `config.yml` 与 `PUT /config` / `GET /status` 的 `config`
回显里, 时间写 `5S`/`30S`/`3M`/`2H`/`1D`, 大小写 `1MiB`/`500KiB`/`100GiB` (只认二进制单位
B/KiB/MiB/GiB/TiB)。解析与回显单点在 `gtm/units.py` (文法镜像 auto-qb 的 `parse_time` /
`parse_fsize`), 内存里的 `Config` 仍是秒/字节, 采样循环不认识单位。**读侧兼容 D13 之前的
裸数值** (`sample_interval: 5.0` 按秒、`flush_delta_bytes: 1048576` 按字节), 启动时由
`migrate_legacy_config` 一次性改写成复合串; 写侧只会写复合串。

⚠ `PUT /config` 是**全量覆盖** (last-writer-wins): 载荷必须带全部键, 只发要改的键
会把其余键静默打回默认值 (冒烟实测: 只发 `notify_threshold_bytes` 会让
`sample_interval` 从 0.05 变回 5)。设置页须「读后写」(先 GET /status 取 `config`
回显, 改字段后整体 PUT)。

## 通知 (S4)

采样循环内累计「距上次事件的当日上下行合计变化」, >= `notify_threshold_bytes`
(默认 100 MiB) 时向所有存活订阅者推送一个事件 (事件体六键, 计划 §04 S4):

```json
{"event_id": 7, "day": "2026-10-16", "up_bytes": 123, "down_bytes": 456, "total_bytes": 579, "ts": 1760587200.123}
```

- 顺序: **先落盘** (dat 节流窗口内的活尾即时封口 —— 订阅者收到事件时文件必已含新值)
  -> 事件号 +1 且落 state.json (**重启接续**, 订阅方按事件号单调去重) -> 派发。
- **不占采样循环**: 派发在独立守护线程里做, 且**每订阅者一线程** —— 假死端点只占满
  自己的 `notify_timeout_s` 超时窗口, 既不拖慢采样节拍也不拖慢其它订阅者; 推送失败
  只记 WARNING 不重试 (订阅者靠慢轮询兜底); 在途线程达上限 (32) 则跳过本轮派发并告警。
- **启动/崩溃恢复后首帧补发一次** (`catch_up`, 不看阈值): 让重启后仍持旧视图的订阅者
  立即刷新; 事件号接续 (不是从 1 重来)。
- 阈值累计基数 = **上次事件时刻**的当日合计, 只在事件派发成功后推进 (随样本推进会
  把「累计变化」退化成单样本 delta); 跨天/累计回退只重置基数, 不产伪事件。
- 推送以 `Authorization: Bearer <订阅时登记的 token>` POST JSON 到订阅端点
  (auto-qb 侧 `/api/traffic/monitor/notify`, S7); 订阅方按事件号单调去重, 且 **26-10-21 起
  事件直达补丁** —— auto-qb 收到事件后用六键自带权威累计直接改快照「今日流量」(零读盘,
  用户拍板「读盘本身就是副作用」), 每个新事件号立即生效; 旧订阅方侧冷却 `notify_cooldown_s`
  (曾默认 600s) 已退役(键保留仅为兼容)。

## 开发

```bash
uv sync                              # 在本目录建独立 venv 并安装依赖
uv run global-traffic-monitor --version   # 验证安装与入口
```

### 测试与覆盖率门槛

```bash
uv run pytest                                  # 全量 + 覆盖率门槛: 一条命令出 TOTAL 与判定
uv run pytest tests/test_units.py --no-cov     # 排障单个测试档: 必须加 --no-cov
```

- **门槛口径独立, 不与主仓合算**: 覆盖率分母只含 `gtm` 包(语句 + 分支出口), 阈值写在
  `pyproject.toml` 的 `[tool.pytest.ini_options] addopts` 里
  (`--cov=gtm --cov-branch --cov-report=term-missing --cov-fail-under=<N>`)。主仓
  `pytest.ini` 的 `--cov=src --cov-fail-under=99` **一个字不动** —— 两套分母混算会互相稀释,
  两套数字也不可互比。
- **阈值阶梯**: 88 → 91 → 93.5 → **98.5(定档 = Windows 侧实测 − 0.8, 向下取 0.5 的整数倍)**。阈值恒低于当期实测 0.8–1.0 点, 且取**双平台
  较低者**; 抬阈值是阶段验收动作的一部分, 与基线切片同轮落地。
- **单档必加 `--no-cov`**: addopts 里的门槛是对**全量收集面**设的, 只收集一个测试档时分母
  塌缩, 覆盖率必然远低于门槛 → **假红**(用例其实全绿)。覆盖率闸只归全量跑(本地 `uv run
  pytest` 与 CI)。
- **两侧覆盖率天然不等**: `installer` 的平台后端(winreg 只在 Windows 可执行、`os.getuid`
  只在 POSIX 可执行)与真机探测面决定了 ubuntu / windows 不可能相等, 所以定档取低者,
  也不追主仓的 99%(硬追只能靠 `pragma: no cover`, 与「豁免只减不增」冲突)。
- **豁免只减不增**: 现存 `pragma: no cover` 1 行(`units.py`), 新增豁免须逐块写理由;
  平台分支优先走注入替身(`runner` / `registry` / `home` / `uid` 注入点)而不是豁免。
- **CI 同一份 addopts**: `.github/workflows/ci.yml` 的 `test-gtm` job 在 ubuntu + windows
  各跑一次, 本地 `uv run pytest` 与 CI 不靠人记参数。

### 跨进程契约: 与主仓同轮跑(M6)

本工具与 auto-qb 主仓是**同一份跨进程契约的两端**: 主仓 `webui/tool_client.py` 消费本工具的
`GET /status`、`PUT /config`、`POST /subscribe|heartbeat|unsubscribe|autostart|shutdown`。
主仓侧有 99% 门槛守着, 工具侧现在也有 98.5 门槛 —— 但两边各自绿**不等于契约没漂**。

改任一侧的**端点路径 / 请求或响应字段 / 状态码**时, 两侧测试必须**同轮跑**:

```bash
commands run test.one -- tests/test_traffic_monitor_client.py   # 主仓契约端
commands run test.gtm                                           # 工具侧契约端
```

任一侧红即阻断合并。只改实现细节(不动端点/字段/状态码)时按各自门槛正常跑即可。

## 自启 (S5)

```bash
global-traffic-monitor install-autostart [--data-dir DIR]   # 注册开机自启 (幂等)
global-traffic-monitor uninstall-autostart                  # 卸载开机自启 (幂等)
```

也可由启动器 `launch.cmd` / `launch.sh` (工具侧唯一知道「怎么起」的地方, D19) 拉起并
顺带幂等注册: `run --autostart` 只表达这种「顺带注册」意图, 是否真注册看 config
`autostart` (默认 `true`; 经 `POST /autostart` 关过后为 `false`, 再被拉起也不装回)。

| 平台 | 机制 | 注册项 |
|---|---|---|
| Windows | `HKCU\...\Run` 注册表值(当前用户, 登录时触发, **零提权**) | `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` 值 `global-traffic-monitor` |
| Linux | `systemctl --user enable --now` | `~/.config/systemd/user/global-traffic-monitor.service` |
| macOS | `launchctl bootstrap gui/<uid>` | `~/Library/LaunchAgents/com.global-traffic-monitor.autostart.plist` |

- **注册什么**: 一条 `python -m gtm run --data-dir <DIR>` 守护命令 (包名 gtm 不变, D16);
  解释器取**调用本命令的那个 python** (`sys.executable`) —— 它按定义就是装了本工具的 venv。
  `data_dir` 解析成绝对路径 **写死进注册项**(自启拉起时是登录会话,
  `GLOBAL_TRAFFIC_MONITOR_DATA_DIR` 不可控), 故 `--data-dir` 要与 `run` 用的同一个。
- **幂等**: 重复注册/重复卸载都是成功 no-op。判据是**期望态是否已达成** —— Windows 看 Run 值
  是否存在(开关语义就是「有没有自启项」), 内容与当前参数不一致时**覆盖写**收敛; Linux/macOS 看
  单元/plist 文件内容是否一致**且**已启用/已加载, 未达成则收敛(文件漂移就重写, 服务被 disable
  就重新启用)。只查「文件存在」会把「文件在但服务被停」误判成已注册。
- **退出码** (供 auto-qb 设置页开关判成败): `0` = 达成期望态(含 skipped/absent) ·
  `1` = 平台命令失败/前置条件缺失(如解释器不存在) · `2` = 平台不支持。
- **不解析平台命令输出**: systemctl / launchctl 的输出随系统语言本地化, 本模块**只信退出码**;
  输出仅作失败时的附注(解码走 UTF-8 -> 本地码页兜底链)。Windows 侧已无平台命令, 注册表值按
  原样读回比对。
- **Windows 为什么不用计划任务**: `schtasks /SC ONLOGON` 是「任何用户登录」级系统触发器, 普通
  权限进程创建会被 Task Scheduler 拒(rc=1 拒绝访问), 只有提权才能注册 —— 而本工具由 auto-qb
  以普通权限拉起, 无人值守路径上没人点 UAC。HKCU Run 零提权、语义正好是「当前用户登录」。
- **Windows 注意**: ①Run 值长度上限 **260 字符**(解释器路径 + `-m gtm run --data-dir <DIR>`),
  超了注册会 fail-fast 报错而不是截断成一条跑不起来的命令 —— 目录太深就把工具或数据目录挪短;
  ②升级前若曾用**管理员**权限注册过旧计划任务, 它会残留在系统里, 用一条命令清掉(管理员 cmd):
  `schtasks /Delete /TN global-traffic-monitor-autostart /F`(不存在会报「找不到」, 属正常)。
- 由 auto-qb WebUI 设置页开关调用 (S6), 也可命令行直接跑。Linux `systemctl --user` 需登录
  会话 (SSH 裸连需 `loginctl enable-linger`)。

## 设计单点

实施计划: [memory-bank/plans/26-10-16-0541-plan-global-traffic-monitor.html](../../memory-bank/plans/26-10-16-0541-plan-global-traffic-monitor.html)
可行性报告: [memory-bank/reports/26-10-13-1034-report-global-traffic-source-lag.html](../../memory-bank/reports/26-10-13-1034-report-global-traffic-source-lag.html)
正主注册与让位: [memory-bank/plans/26-10-20-1316-plan-gtm-primary-registration.html](../../memory-bank/plans/26-10-20-1316-plan-gtm-primary-registration.html)
坑档(指针/锁锚用户级目录): [memory-bank/pitfalls/backend/traffic-source-discovery-pointer.md](../../memory-bank/pitfalls/backend/traffic-source-discovery-pointer.md)
