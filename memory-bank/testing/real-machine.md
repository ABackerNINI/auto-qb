# 真机实测(连真实 qBittorrent 的实测轨)

> 摘要: 第四条测试轨的**全部规程** —— 硬约束与环境守卫、种子层 L0/L1/L2、切片表与切片更新规则、一轮的标准动作、两次排期之间的漂移判定、用例成熟度 L0–L3 与用例写法。状态与进度**不在本文件**, 在常驻锚 issue。
> 触发: 真机实测, 真机测试, 连真机, 实测排期, 测试 qB, 36595, 36596, 假种子, 伪 tracker, 切片, 用例成熟度, 漂移判定, tests-real, real 包, 不走闸门

## 00 定位: 四条测试轨的分工

| 轨 | 载体 | 代价 | 覆盖什么 | 挂闸门 |
|---|---|---|---|---|
| 单测 | `tests/`(全 Fake) | 全量 ~8s | 纯逻辑 / 判据 / 状态机 | ✅ `test.quick` 在 `ship.commit` 链上 |
| 浏览器 | `e2e/` + 桩服务 | 全量 ~11min | 前端渲染 / 交互 / 乐观 UI | ✅ 改前端时的门禁 |
| 语料回放 | `scripts/qb_capture.py` → `sim_qb.py --source=corpus` | 分钟级 | 真机**数据面形态**(字段/分布/时间轴) | ❌ |
| **真机** | `tests-real/` + 两个测试 qB 实例 | **半天 / 片** | **写侧真作用 / qB 真行为 / 文件系统 / 进程生命周期 / 观感** | ❌ **永不** |

**准入判据(反膨胀)**: 能用桩或语料验的, **不进真机轨**。真机轨只收三类 ——
① 必须由 qB 真执行才成立(命令回执、种子真状态变化、限速真下发);
② 必须碰真文件系统 / 真进程 / 真注册表(移动、硬链接、重启、托盘、开机自启);
③ 只有人眼能判(观感、配色、跟手性)。

同一件事在三条轨都测 = 维护三份会各自漂移的断言 —— 选一条, 其余只引用。

## 01 硬约束(违反即事故, 没有"这次特殊")

| # | 约束 | 谁执行 | 怎么机检 |
|---|---|---|---|
| 1 | **只碰白名单实例**: `127.0.0.1:36595` / `127.0.0.1:36596`, 且进程镜像路径前缀 `D:\Programs\qBittorrent-testing` | `real.guard` 静态核验 | 端口或镜像路径不在白名单 → **退出码非 0, 无 `--force`** |
| 2 | **真实种子全程非活跃** | guard 前置 `pause-all` + 运行期看门狗 | 每 2s 轮询目标 qB, 任一**真实**种子进入 `uploading`/`downloading` → 立即暂停并记违规; 违规 ≥3 次中止本轮 |
| 3 | **生产配置零触碰**: 只用 `tests-real/config/*.yml` 派生配置 | guard 校验配置路径 | 配置路径 == 仓库根 `config.yml` → 拒跑(红线文件, 见 pitfalls/ops/prod-files) |
| 4 | **不动其它 qB**: 杀进程/重启前先核镜像路径 | `real.up` / `real.down` | guard 记录运行前全部 qB 进程 (PID+镜像路径), 收尾比对; 出现新增/消失即报告 |
| 5 | **不挂闸门** | 人 | `.commands/my-commit-flow` 或 `ship.*` 里出现 `real.*` 调用 = 缺陷, 立即回滚 |

> 约束 2 与功能测试天然冲突(要测"做种/上传"就得让种子活跃)。处置: 该条用例在计划里标 **`[需活跃种子]`** 并写解锁条件, 本轮跳过并记账 —— **不允许**为了跑通用例临时放宽约束。L1/L2 解锁后(§03), 假种子不受此约束, 冲突面大幅收窄。

## 02 环境与守卫

### 2.1 守卫(全在 `tests-real/guard.py`, 入口 `real.guard`; 任何用例先过它)

1. **静态白名单** —— 端口 ∈ {36595, 36596}; 进程镜像路径前缀匹配; 配置路径不是 `config.yml`。
2. **在线核验** —— `connection_status` 必须不是 `disconnected`(`connected` / `firewalled` 都算通过)。
   见 §2.5: 掉线时 qB 一个 announce 都不发, 而种子状态看起来完全正常 —— 不拦在门口, 整片结论都是假的。
3. **前置快照 + 归零** —— 记录当时所有 qB 进程与目标实例的种子清单; 对目标实例 `pause` 全部种子, 校验 `start_paused_enabled`。
4. **运行期看门狗** —— 后台线程按 2s 轮询目标实例; 违规即暂停 + 记账; 超阈值中止并让本轮结论记 `ABORTED`(不是 PASS)。

收尾:**恢复快照**(把本轮 pause 过的种子恢复原状态; 本轮自造的种子/标签/分类**删干净**), 并重跑一次进程比对。

### 2.2 启动 / 重启

- 一律走 `real.up` / `real.down`(白名单内), **不要手工双击 exe** —— 手工启动的进程 guard 认不出归属。
- 端口被残留占用 → `dev.port-kill`(**只传白名单端口**), 它按端口查真 PID, 不会误杀包装进程。
- 两个实例都是 **portable 模式**(各自带 `profile/`), 配置与 `qBittorrent-data` 互不影响; 需要"干净环境"时换 `profile` 目录而不是删 `%APPDATA%`。

### 2.3 RM00 之前的手工版(三条, 缺一不开跑)

`real` 包由 RM00 建立; 在那之前守卫是手工 checklist —— 跑 `dev.webui` / `dev.run` 前逐条核:

1. 目标端口是 `36595` / `36596`, 且该端口对应的进程镜像路径在 `D:\Programs\qBittorrent-testing*` 下(用端口反查 PID 再核路径, 别只看端口);
2. 目标实例**全部种子处于 `paused`**(`GET /api/v2/torrents/info` 逐条看 `state`), 有活跃的先暂停;
3. 要跑的配置是 `tests-real/config/*.yml` 派生的那份, **不是**仓库根 `config.yml`。

三条核完在回复里贴一行"guard 手工: 端口 ok / 种子 paused ok / 配置 ok" —— 事后追责靠这一行。

### 2.4 安全模式: 读侧切片优先用 `dev.webui`

`dev.webui` 起一份**关掉全部自动任务**的最小配置(只留同步快照 + WEB UI, 数据目录独立), 连真机 qB 看界面/试交互 —— 读侧切片(RM08)首选它, 不必跑完整主循环。注意它**仍会真写**: WebUI 上点"暂停"就是真暂停(这是测乐观 UI 的前提), 所以约束 1/2 一样适用。

### 2.5 实例的硬事实(RM00 实测; 环境有变先改这里)

**两个测试实例的 BT 监听端口**: 36595 = `26803`, 36596 = `60539`, 都绑在局域网 IP `192.168.1.122` 上。

> 🔴 **36596 原本配的是 60537, 而生产实例 `D:\Programs\qBittorrent-2` 占着 60537**。撞车后果不是"慢", 是**该实例一个 announce 都不发**: 抢不到监听 socket ⇒ `/api/v2/transfer/info` 的 `connection_status` 变成 `disconnected` ⇒ libtorrent 认定自己离线, 连 tracker 都不联系, 所有种子永远停在 `stalledUP`/`stalledDL` 且 `status=1`(未联系)。
> **所以 `real.up` 之后必须核一句 `connection_status`**: 只接受 `connected` / `firewalled`; 见到 `disconnected` 立刻换端口(`set_prefs(listen_port=...)`, 用 `socket.bind` 先探空), 不要往下测 —— 否则整片结论全是假红。

**其它会让人白跑半小时的实测事实**:

| 事实 | 影响 | 处置 |
|---|---|---|
| 两实例 `dl_limit = 1024`(1 KiB/s) | L2 互传 2MB 要半小时 | 用 `transfer_limits` fixture 临时钉 256 KiB/s, 结束还原 |
| `/torrents/trackers` 会返回 `** [DHT] **` / `** [PeX] **` / `** [LSD] **` 伪条目 | 直接 `is_local_url` 会误报"非本机地址" | 断言前按 `url` 以 `http` 开头过滤 |
| 种子是 private 时, 上述三条的 `msg` = 「这是私有 torrent」 | 正常现象, 不是错误 | 不要断言它们 status==0 |
| `uploaded` 计数比 `progress` 慢一拍(实测差 ~20KB) | 临界断言会假红 | 用 `_wait` 等它追平, 或断言 `>= payload` 前先轮询 |
| 36596 的 WebUI 是 `LocalHostAuth=false` | 带 token 反而 403 | `lib/qb.py` 已做一次鉴权降级, 不要"修"成报错 |
| qB 5.2 字段名 | `upspeed`/`dlspeed`(不是 `up_speed`); 暂停用 `/torrents/stop` 与 `/torrents/start`; `/torrents/add` 返回 JSON 收据 | 已在 `lib/qb.py` 封装 |
| 工具 shell 里 `Start-Process` / `cmd start` 起的 GUI 进程会随命令结束被杀 | 实例"启动成功"后消失 | 一律经 `explorer.exe`(`real.up` 已这么做) |
| `--portable` **不是**合法命令行参数(传了会 0xc0000005 崩) | 实例崩溃, 看着像环境坏了 | 无参启动即可: 目录里有 `profile/` 就是 portable |

**诊断入口(卡住时先跑它们, 别靠猜)**: `uv run python tests-real/tools/diag_l2.py [秒]`(双实例互传全过程: announce 计数 / tracker 视图 / TCP 连接表) 与 `tests-real/tools/diag_log.py <port> [行数]`(qB 日志尾部)。

### 2.6 手工探索: 假种子命令(`real.seed*`)

需要"随手造个种子看看界面 / 状态 / 标签 / 限速"时用它, 不必先写一条用例:

| 命令 | 干什么 |
|---|---|
| `real.seed` | 造数据 + 造 `.torrent` + 加入实例(`add`) |
| `real.seed.list` | 列出自造种子(hash / 名字 / 大小 / 进度 / 状态 / 落点) |
| `real.seed.rm` | 删自造种子(`--all` / `--name` / `--hash` 前缀; 默认连数据) |
| `real.seed.clean` | 清 `tests-real/.work/` 与 `R:/qbt-fake/` 下的残留(不碰 qB 里的条目) |

参数: `--size 256K|8M|1.5G|512k`(**默认 256K**, KB 级就够看状态) · `--pattern random|zeros|text` ·
`--dir <落点>`(只认 `tests-real/.work/` 与 `R:/qbt-fake/`) · `--from <现成文件>`(大小自动取文件, 不动原文件) ·
`--no-data` · `--paused` · `--piece-len` · `--port 36595|36596`(默认 36596, 空库当草稿本) ·
`--allow-huge --reason "<原因>"`(> 2G 才用得上) · `--yes`(不加就只打印计划)。

五条口径:

- **默认 KB 级, 不要造大种子**: 造种子的目的是"看状态/走分支", 256K 已经够(16 个 piece, 校验瞬完)。
  真正需要大小时(测进度条、测分块、测限速曲线)再显式给 `--size`。
- **> 2G 原则上不造**: 命令会**停下来等授权** —— 必须 `--allow-huge --reason "<原因>"` 双写才放行,
  只给 `--allow-huge` 会被拒(授权要留痕, 否则等于默认允许), 放行后打印 `[warn]` 留痕。理由是三个代价叠加:
  占盘/占内存盘、qB 校验要**读满一遍**、清理最容易漏(尤其落到真磁盘的)。想清楚了再分两条路走:
  只要"大尺寸"这个属性看状态 ⇒ `--no-data`(不落盘, 零代价, 不受限); 要真数据 ⇒ 先问自己 1G 行不行。
  `--from <现成文件>` 不创建文件、只造种子, 源文件超 2G 只告警不拦。
- **≥ 32M 自动落 `R:/qbt-fake/`**: R 盘是**内存盘**(约 52 GB 可用), 写多少都不心疼; 但**重启即清空**,
  所以大种子只当次会话有效。要长期留着就显式 `--dir` 指到磁盘(仍在允许的落点内)。R: 不可用时自动退回 `.work` 并提示会真写盘。
- **默认不带 announce** ⇒ 纯本地做种(`stalledUP`、progress 100%、零外连)。要 announce 请在用例里用
  `FakeTracker` —— CLI 是短命进程, 起不了活到你看完的 tracker。
- **自造种子一律打 `real-fake` 标签** ⇒ list / rm / clean 只认这个标签, 碰不到真实种子; 守卫的归零
  (`guard.snapshot(skip_tags=("real-fake",))`)也会跳过它们 —— 否则"刚加的假种子怎么变成 `stoppedUP` 了"
  会变成日常困惑。

`clean` 默认把 `tests-real/.work/` 与 `R:/qbt-fake/` **两处都扫**(含空目录壳子), 越界拒跑。

> ⚠️ **`--no-data` 不是"缺文件态"**: 实测 qB 停在 `stalledDL` / progress 0, 不会进 `missingFiles`(`recheck` 也不进)。
> 要测"文件被删"这条路径, 请在用例里加完种子再删文件。

### 2.7 产品进程的硬事实(`tests-real/lib/app.py`, RM01 实测)

要测产品自身(而不是 qB)时, 起停一律走 `lib/app.py`。四条语义与直觉不同, 不记住会白烧一轮:

| 事实 | 现场表现 | 正确做法 |
|---|---|---|
| **`--dry-run` 不启 WEB 服务** | `webui/module.py:66` 是 `if dry_run or not web.enabled: return` —— 等 40s 也不会有"WEB UI 已启动" | WEB 类用例(启动日志/端口/token)**不带** dry-run; 只验进程边界才带 |
| **Windows 上外部 SIGTERM 等于强杀** | `Popen.send_signal(SIGTERM)` 走 `TerminateProcess`: 退出码 1、`finally` 一行不跑、日志无收尾。`CTRL_C_EVENT` 也投递不到(子进程无控制台) | 优雅退出只能**进程内** `signal.raise_signal(SIGTERM)` 触发(`start(graceful_after=N)`); 或到 Linux 上从外部发 |
| **配置必须写 `schema_version: 5`** | 否则每次启动走 v1→v5 迁移; 非 dry-run 时还会**改写**配置文件并留备份, 把临时目录搅浑 | `write_config()` 已带; 手写配置时别忘 |
| **`Popen.pid` ≠ 进程实际 pid** | uv 给 venv 的 `Scripts/python.exe` 是 47KB **启动器**(基解释器 91KB), 真解释器是它的子进程 ⇒ 锁 meta / 日志里的 pid 与 `Popen.pid` 对不上 | 按 pid 断言用 `real_pid()`(读锁 meta); 杀进程用 `taskkill /F /T` —— 不带 `/T` 只杀启动器, 孤儿进程继续持锁, 用例就"测了个寂寞" |

**GUI 栈依赖解释器带 Tk**(RM01 实测, 一次踩透): `tkinter` 是 CPython 标准库的一部分(Tcl/Tk 编译产物), **不是 PyPI 包, 不可能出现在 `uv.lock` 里** —— 所以 `env.sync` 全绿也不代表能跑界面。`customtkinter` / `pystray` 装得上, 但前者在 `__init__.py:6` 就 `from tkinter import ...`。
判据一句话: `python -c "import customtkinter"` 过不了 ⇒ 这个 venv 的 GUI 面整体不可用, 任何"界面看起来对"的结论都只来自单测打桩。
本机曾因此踩坑: `.venv` 建在宿主自带的裁剪版 Python(`H:\Programs\AutoClaw\resources\python`, 无 `_tkinter.pyd`/`tcl/`)上, 已改为 uv 管理的 CPython 3.13.15(带 Tk 8.6)重建。换机器/重建 venv 时先跑这一句。

两个探针口径(踩过才写的):

- **`port_free()` 不许用 `SO_REUSEADDR`**: Windows 上它的语义是"允许抢占别人正在监听的端口", `bind` 成功 ≠ 端口空闲。实测因此谎报"已释放", 紧接着重启撞 `Errno 10048`。裸 `bind` 才是可信探针。
- **端口别复用**: 上一条用例刚停的进程, 监听套接字要过一小会儿才真正消失 —— 整片连跑时后一条抢到前一条刚释放的端口就 10048, 单跑不复现。`free_port()` 记会话内已用端口, 段(39000–39999)够大, 比 sleep 等它可靠。该段 39099 常被 WorkBuddy 自己的 `editor_sdk.exe` 占着, 探空会自动跳过。

### 2.8 进程间网络与断连事实(RM02 实测, 2026-10-31)

| 事实 | 现场表现 | 处置 |
|---|---|---|
| qB WebUI 校验 Host 头 | 经本地代理转发时保留原 Host(`127.0.0.1:<代理端口>`) → `/auth/login` 401(直连同 body 204) | `lib/proxy.py` 统一把 Host 改写成实例的 host:port 再转发 |
| 本机 loopback 连接失败单次 ~2s | 连无监听端口的 connect 不是瞬时 RST; 托管模式首个 connect() 周期(detect_scheme http/https + login 三连)约 20-40s 才落第一条 ERROR | 断连类用例的等待窗按此放宽; 慢不是挂死 |
| 热重载命令线 = `PUT /api/config` | 回执带 `changes`(顶层段名)与 `restart_required`; R 级段(data_dir/state_file/fs)提交即被回退旧值并报 restart_required | 触发 L2 重建的最小改动 = 改 `interval`(rules 模块认领段) |
| 托盘模式 SIGTERM 无效 | graceful 跑壳(进程内 raise_signal)对 CLI rc=0 有效, 对 `--tray` 3/3 不退出(45s+ 仍存活; issue 26-10-31-1030) | 托盘进程收尾只能 `taskkill /F /T`; 托盘用例不验优雅退出 |
| 断连后不自动重连(缺陷在池) | 运行期 qB 断开一次后, 每 main_tick 一条「主循环异常」ERROR(75s 内 39-45 条)且恢复后不回连 —— issue 26-10-31-1029 | RM02-07 记 FAIL; 修复后须真机回归 |
| `.bak` 只在写盘前已有旧文件时生成 | fresh 目录首次优雅退出只有 state.json, 没有 `.bak`(atomic_write keep_backup 语义) | 要造 `.bak` 需先正常起停**两次** |

> 并行陷阱: `pytest.ini` 的 addopts 是 `-n 8`, 默认 `--dist load` 下 `xdist_group` **不生效**。官方入口 `real.suite` 传 `-n 0` 没问题, 直跑 `pytest tests-real/...` 会互相抢端口 —— `rm01_startup/conftest.py` 用一把文件锁兜住, 后续片照抄。

### 2.9 归组/迁移面与假种子进管线的事实(RM04 实测, 2026-10-31)

| 事实 | 现场表现 | 处置 |
|---|---|---|
| **「未匹配 tracker 配置」的种子跳过整条 torrents_added 管线** | 无 announce 的假种子不进 `matched_added`(qbmanager 实况: tracker_conf 匹配失败即 `continue`) ⇒ **归组/维护/限速全不发生**, groups 视图恒空 | 假种子必须带 announce 且测试配置 trackers 段有对应 domains 条目。announce 用 `http://<本机IP>:1/announce`(本机死端口, 连接即 RST 零外连); 别用假域名 —— 那要走 DNS 出外网 |
| **qB 5.2 `/torrents/add` 对重复 infohash 返回 409 Conflict** | 复跑同 infohash 的用例收到 409 | 409 时删旧副本重加, **绝不收养** —— 收养会把上轮的预打标/预暂停状态带进本跑, 触发源(上传转暂停/新增)永不触发, 假 FAIL 自续(RM04 实测毒化两轮) |
| **产品 store 快照滞后 qB 实际进度 1-2 个同步拍** | qB 侧 progress 已 1.0, 立刻触发 relocate 会被 GATE_INCOMPLETE 拒 | 等 groups 视图成员 progress==1.0 再触发(视图随进度置脏重建, 单向前进无回退竞态) |
| **qB 多标签以「, 」(逗号+空格)连接** | 产品打上 MISSING 后 tags = `MISSING, real-fake` | 标签成员判断必须 strip(`{x.strip() for x in tags.split(",")}`); 裸 split 对双标签失明 —— 已入池 26-10-31-1215(seed.py/guard.py), 用例侧各自防御 |
| **relocate 目标目录不存在 ⇒ GATE_SPACE 不可判定拒绝** | disk_usage 打不存在的路径 → fail-closed blocked | 用例预建 dst 即可, 合法闸门非缺陷 |
| **单成员组恒走 FORM_DIRECT(qB 自搬, 无别名无 journal)** | ×1 假种子的 relocate 不产生别名/ journal, 锚点是「迁移发起」非「已下发 qB 搬迁」(后者只在重启补发路径出现) | 要验目录别名主链: 多成员组(≥2 枚同表种子, 同内容异 piece_len 区分 infohash)+ 子目录布局 + `alias_file_threshold: 1` + 命令线 POST body `confirm: true` |
| **armed job 可不经 qB 退出收口** | 对账表 `link_present + qb_up + 全员 at_dst → ACT_DONE_EXTERNAL`: phase=done(reason=external) + journal phase=done | 用例可用 qB 原生 setLocation 让其余成员跟进 dst 即时收口; guardian「qB 退出删链接」路径归 RM10 |
| **搬迁窗口基本抓不住 state 30S 落盘周期** | 64M 跨卷搬迁数秒, 强杀后 state.json 常无在途 job(「恢复在途 job 0 条」≠ 恢复面失效) | journal 注入退路(RM04 计划 §03 批准): 停机态按 job_to_dict 形造 phase=moving/move_issued=true 账 + journal/spec, 重启走 `_recover` RESUME 分支; 另注意产品日志是**追加式**, 断言「最后一次启动」的日志行要等新行出现再取 |
| **删 junction 绝不递归(重申 §08)** | `rm -r`/`shutil.rmtree` 对 junction 的行为按平台而异, 穿透即删真实数据 | 用 `os.walk(topdown)` 遇 reparse 点 `os.rmdir` 剪枝的 purge 形态(RM04 用例 `purge_tree` 可照抄) |

### 2.10 规则引擎面的事实(RM03 实测, 2026-10-31)

| 事实 | 现场表现 | 处置 |
|---|---|---|
| **规则绑定名 = `@规则集.规则名` 全名** | 日志行「规则[rm03_rules.xxx]」与 state.json 的 `exec_history` 键、去重记账全部用**带规则集前缀的全名**, 裸规则名不出现 | 咬规则日志/记账的断言按全名写锚点(RM03 首轮 7 条假红全挂在这) |
| **规则 `interval` 键留空才是每轮语义** | `interval: 0S` 被配置校验拒绝(「必须为正时间」); 留空 = 每 tick 级别(队列归一化 1s) | 每轮检查的规则**省略 interval 键**, 不要写 0S |
| **`execute_once` 合法枚举 = never/once/daily/hourly** | 「always」不是合法值, 校验即拒 | 「窗口内只执行一次」落 `once` |
| **dry-run 管线照常分派规则** | --dry-run 下种子同步照常执行、interval/事件规则照常命中(日志有「规则[…] 动作[…] 成功」行), 动作经 ctx.dry_run 跳过 qB 写, 实测 ≥10 节拍零 qB 写(tags/category/限速全等) | dry-run 可作规则面的**零副作用观测窗**(RM03-09 实测); 注意它仍会读 qB 并跑完整主循环 |
| **规则层去重的权威账在 state.json `exec_history`** | `record_execution` 只写内存, 优雅退出/周期落盘(≥30S)才刷盘; 动作级幂等(add_tags skip)是 DEBUG 级, INFO 日志不可见 —— 只数成功行分不出"去重失效" | 去重断言走 exec_history 的 ts(用 `graceful_after` 起产品拿落盘账), 不咬动作日志 |
| **stop_following_rules_if 当前不生效(缺陷在池 26-10-31-1304)** | `Rule.process` 的 (handled, stop) 在唯一调用点被丢弃; 条件出错日志「停止后续规则」的措辞与实际行为不符 | 规则链止损语义别当已验事实引用; 修复后须真机回归 RM03-05 |
| **hr 配置不牵动假种子(RM03-04 实测)** | tracker 条目带 `hr: {required_seeding_time: 3D}` 时, 假种子(零下载量)不触发 HR 在线核实/打标(触发条件是下载比例), `${required_seeding_time}` 变量替换照常工作 | RM03-04 口径可复用: 变量替换面用 hr 段驱动, 不需要 hr_check 站点接入 |

### 2.11 tracker·标签面的事实(RM05 实测, 2026-10-31)

| 事实 | 现场表现 | 处置 |
|---|---|---|
| **qB 全局标签定义独立于种子存活** | 种子删除/逐种子摘标都不带走定义; `GET /torrents/tags` 列定义, `createTags`/`deleteTags` 表单逗号分隔多值可用(v5.2.3) | 清场必须显式删定义层; RM05-06 前提「add→remove 后定义残留」实测成立, 可作无种子对照的造法 |
| **delete_tags 与站点标签「互相打架」是同节拍振荡** | 种子级维护每 interval 重打 tracker tags(qB addTags **隐式重建已删定义**), 与全局删除成对发生(先删后打), 干净窗亚秒级, 外部轮询采样不可稳定观测 —— schema delete_tags 的 risk 文案明载此预期, 非缺陷 | 这类组合的断言走: 删除日志命中集 == 展开期望 + **不被重打的孤儿标签永久消失**(定义级删除的存在性证明) + 对照标签全采样恒在; 不做「任意时刻定义不在」的快照断言 |
| **多匹配「第一个」= 配置书写序** | `match_tracker_confs` 按 config dict 顺序返回 `confs[0]`(不排序), WARNING「种子匹配到多个 tracker 配置, 使用第一个」一行同时点出全部命中条目名 | 要防「按名字序假绿」, 条目键故意让字母序与书写序相反(RM05-01 的 zz/aa 手法); `write_cfg` 必须 `sort_keys=False` |
| **热重载 trackers 段实测(RM05-02)** | PUT /api/config 回执 applied 且**无 restart_required**; 日志「rebound N」; 新 tags 下一维护节拍兑现; 旧标签不回撤(重绑只换 conf 不摘旧标) | 断言「rebound」+ 新标签兑现即可, 别咬「旧标被清」; tags 变更经树编辑 `tree["config"]["trackers"]["<条目>"]["tags"]` |
| **hr_check.enabled=false 下站点派生零取数** | 站点条目 `hr_check.sites.<id>.enabled: true` 只走装载期派生, HR 线程不启动, 正向启动日志零「在线核实」痕迹 | 站点派生面可零外连实测(在线核实面归 RM06); 绑定校验要求被绑条目带 `hr` 段, 否则「已绑定站点…未配置 hr 段」ConfigError; 负向(绑0/绑2/未登记 id)走 `run_cli --dry-run` 退出码 + 「配置错误」文案(RM03-05 同款观测法) |

## 03 种子层: L0 / L1 / L2

| 层 | 怎么造 | 种子状态 | 能测什么 | 风险 | 现状 |
|---|---|---|---|---|---|
| **L0** | 用实例里现成的真实种子 | 全程 `paused` | 只读数据面、观感、配置读写 | 零(不动真实种子) | ✅ 现在可用 |
| **L1** | 构造种子, announce 指向本地伪 tracker(bencode, **零 peer**) | `stalledUP` / `paused`, **零外网流量** | 标签/分类/状态/限速下发/规则命中/HR 判定数据面 | 零(流量不出本机) | ✅ RM00 已验证 |
| **L2** | 36595 做种 + 36596 下载, 伪 tracker 回对端地址 | 真 `uploading`/`downloading` | 真实速率/进度/完成事件/做种时间/汇报 | 零(两端都打本地 tracker) | ✅ RM00 已验证 |

**L1 设计要点**: 伪 tracker 只需实现 `GET /announce` 返回 `d8:intervali1800e5:peers0:e`(零 peer)即够; 种子用 bencode 现造(`announce` = `http://<本机局域网IP>:<port>/announce`), 不要拿真实种子的 infohash 改 announce —— 那会让真实 tracker 仍被联系。
**L2 设计要点**: 伪 tracker 对 36596 的 announce 返回 36595 的 peer(`ip` + `port` 取自 qB 的监听端口), 两端都在本机 ⇒ 流量不出网卡。

> ⚠️ **announce 不能写 `127.0.0.1`**: qB 的出站 socket 绑在以太网接口上(`current_network_interface`), 打 127.0.0.1 会 `WSAEADDRNOTAVAIL`, tracker 状态 4「该请求的地址无效」。一律用 `lib/net.py: local_host()` 取的局域网 IP —— 仍是本机, 流量仍不出网卡。
> ⚠️ **伪 tracker 回包必须排除请求者自己**: 两实例同 IP 只差端口, 若把"自己"也回给它, 种子会去连自己, 而 qB 默认 `enable_multi_connections_from_same_ip=false`(同一 IP 只允许一条连接), 真正的 leech 会被挤掉 —— 现场表现是 `connections_count` 1→0 且零字节, 极易误判成加密/防火墙问题。`lib/tracker.py` 已按 announce 里的 `port` 排除。

**RM00 验收三条**(全绿才解锁 L1/L2, 之后各片才允许引用):

1. **L1 正向** —— 构造种子加入 36595 后, `GET /api/v2/torrents/info` 里该种子 `upspeed == 0 && dlspeed == 0` 持续 ≥60s, 且伪 tracker 收到 ≥1 次 announce。
2. **L1 反向** —— 关掉伪 tracker 后种子进入 `error`/`stalledUP`, 且**无任何外网连接**(用连接表或域名黑名单断言), 证明流量物理上出不去。
3. **L2** —— 36596 从 36595 拉取同一构造种子, `progress` 单调升至 1.0, 期间 `upspeed > 0` 持续 ≥10s, 完成后 36595 侧 `seeding_time` 增长; 全程两端 announce 只打本地伪 tracker。

**退路(必须写进 RM00 计划)**: 若 qB 拒绝自定义 announce / 拒绝非标准端口 / 双实例拒绝互连 ⇒ L1 降级为"真实种子 + 全局暂停 + 只读断言", L2 直接置 `Dropped` 并写明原因 —— 不允许"再试试"把 RM00 撑成三次排期。

## 04 切片表

**切片的定义不是"文件清单", 是"一个能独立排期、独立验收的验证面"**。片表本身在常驻锚 issue 的 §03(唯一权威), 本节只给切分口径与更新规则。

| 片 | 名称 | 主要验证面 | 预算 |
|---|---|---|---|
| RM00 | 基建: guard / 伪 tracker / 双实例互传 | 基建(解锁 L1/L2) | 1 次 |
| RM01 | 连接·认证·启动 | 副作用 + 观感(启停/注册表/托盘/token) | 0.5 次 |
| RM02 | 主循环·调度·持久化 | 副作用(节拍/落盘/热重载/优雅退出) | 0.5 次 |
| RM03 | 规则引擎 | 副作用(动作真作用于 qB) | 1 次 |
| RM04 | 辅种与分组 | 副作用(文件系统: 归组/移动/journal) | 1 次 |
| RM05 | tracker·标签与分类清理 | 副作用(批量打标/删标/站点档案) | 0.5 次 |
| RM06 | HR 在线核实 | 数据面 + 副作用(取数通道/三态/频控) | 1 次 |
| RM07 | 限速·流量曲线·全局流量 | 副作用 + 数据面(限速下发/采样/流量源) | 1 次 |
| RM08 | WebUI 读侧 | 数据面 + 观感(轮询/增量/大库/抽屉) | 0.5 次 |
| RM09 | WebUI 写侧 | 副作用(命令/批量/乐观 UI/移动重命名) | 1 次 |
| RM10 | 通知·外部集成 | 观感 + 副作用(通知通道/导出/扩展) | 0.5 次 |

**排期顺序**(按"风险 × 副作用"): `RM00 → RM01 → RM02 → RM04 → RM03 → RM05 → RM06 → RM07 → RM09 → RM08 → RM10`。

## 05 切片更新规则(后续 agent 按这套切/并/拆/下线)

功能会变, 片表必须跟着变 —— 但**不能每轮重排**, 否则"上次测过哪片"失去意义。规则:

1. **归属优先**: 新功能先看路径是否落在既有片 glob 内。落得进去 ⇒ **并入该片**(更新 issue §03 该行 glob), **不开新片**。
2. **开新片的门槛(三条同时满足)**: ① 有独立的副作用面或独立的前置状态; ② 并进既有片会让那片单轮超过半天; ③ 有明确的"这片做完了"判据。缺一条就并入。
3. **编号不复用**: 新片取当前最大号 +1; 下线的片号永久留空, 不许回收。
4. **拆片阈值**: 一片内出现 ≥3 个互不依赖的副作用面, 或单轮新增用例 >12 条 ⇒ 拆。
5. **并片阈值**: 连续两轮只跑回归、零新增用例、glob 命中文件 <3 个 ⇒ 并入相邻片。
6. **下线**: 功能被删或被取代 ⇒ 片置 `Dropped`, 行保留(划掉 + 指向取代者), 不删行。
7. **改片表必须记账**: issue §08 记一行 + §07 对应行同步(新片插一行, 状态 `待做`)。
8. **glob 自检(每轮开工必做)**: 跑一次该片 glob 的命中文件清单, 与"该片应覆盖的功能面"人工对一眼。**命中 0 文件 = 片已失效**, 按规则 6 处理; 命中里出现**明显不属于该片的大件** = 片边界糊了, 按规则 4 拆。
9. **存量清单随片迁出**: `checklists/manual-walkthrough.md` 处于**冻结**状态(不批量迁移)。每片第一次排期时, 把属于该片的条目迁进该片用例集, 原文件对应行标 `已迁出 → RMxx`; 全部迁完再把那份清单置 `Superseded` 并指向常驻锚。理由: 片表还在长, 现在迁完还得返工; 而两份清单长期并存, 结局一定是"哪份都不全"。

> 规则 8 是防"假阴性"的唯一手段: 功能搬了目录而 glob 没跟上时, 漂移体检(§07)会报"零命中", 于是"没变、不用测"—— 而事实是"测不到"。

## 06 一轮的标准动作

排期指令的形态是固定的一句:

```text
对「<片名>」做真机实测, 先写分步实施计划, 参考 memory-bank/issues/<常驻锚>.html 与 memory-bank/testing/real-machine.md
```

收到后按序执行, **不许跳步**:

1. **定片**: 把 `<片名>` 映射到片号。映射不到 ⇒ 先按 §05 规则 1/2 处置(改片表 + 记 §08), 再开工。
2. **漂移体检**: 按 §07 用 `git log <基线commit>..HEAD -- <globs>` 分类, 结论写进计划开头。**没有基线 commit 的首轮写"首轮, 无漂移面"**。
3. **环境自检**: `real.guard`(P0 之前手工核: 端口、进程镜像路径、种子是否全 paused、配置不是 `config.yml`)。
4. **写分步计划**(`plans/` HTML, 拍板后冻结), 必须含四块: ① 本片用例清单(逐条 id + 当前档位 + 期望值); ② **本轮哪条要从 L(n) 升到 L(n+1)**(§08 硬要求); ③ 受约束 2 影响标 `[需活跃种子]` 而跳过的条目 + 解锁条件; ④ 验收判据(什么算这片做完)。
5. **执行**: 逐条跑; 每条结果三态 —— `PASS` / `FAIL`(⇒ 按 scope-guard 入池 `bug` issue) / `BLOCKED`(环境或约束所致, 写明原因与解锁条件)。**当轮不修**缺陷(一律入池, 下轮再修)。
6. **记录**: 新建 `testing/real-baselines/<stamp>-real-<片>.md`(用例数 / 各档分布 / PASS-FAIL-BLOCKED / 基线 commit / 环境指纹); 更新 issue §07 该行。
7. **收尾**: 用例代码照常 `ship.commit`(可复用性靠这个); 缺陷已入池; **不立 `task` 档案**(常驻锚 issue 即档案); 改过片表则 §08 已记。

## 07 漂移处理: 两次排期之间功能变了怎么办

**判据是机械的, 不是印象。** 每片在 issue §07 记一个**基线 commit**(实测时刻的 HEAD)。下次开工第一步:

| `git log <base>..HEAD -- <globs>` | 含义 | 处置 |
|---|---|---|
| **零命中** | 该片代码没动过 | 只跑**回归档**: 已 L2/L3 的用例全跑一遍; 结论写"无漂移回归"; **不重做人工目视** |
| **有命中** | 动过 | 逐条读 diff 分类: ①判据变(期望值/阈值/分支)⇒ 该条**降一档重测**; ②路径/接口变 ⇒ 改用例锚点后重测; ③纯重构(行为等价)⇒ 仍跑, 但结论标"重构后复验" |
| **glob 命中 0 文件** | 片可能失效或 glob 落后 | 按 §05 规则 8 处置 |
| **出现无人认领的新目录** | 新功能没归属 | 按 §05 规则 1/2 提名并入或开新片 |

三条纪律:

- **"上次测过"不等于"这次不用测"** —— 零命中才免人工目视, 有命中一律重测。
- **重构不算零命中**: 纯重构也要跑一遍(行为等价是假设, 不是事实)。
- **基线 commit 必须是真的 HEAD**, 不许写"大概上周"; 写不出 commit 的片, 下一轮从"首轮"重来。

## 08 用例成熟度 L0–L3(未更改部分怎么加强)

| 档 | 判据 | 谁判 | 例 |
|---|---|---|---|
| **L0** | 人工目视, 只写"看到了什么" | 人 | 五主题下输入框有没有过曝 |
| **L1** | 脚本采集 + 人判读(输出结构化快照, 人看数字) | 半自动 | 脚本打印 `up_speed` 序列, 人判断曲线是否合理 |
| **L2** | 脚本自动断言(有期望值, 不满足即红) | 机器 | 断言 `up_speed > 0` 持续 ≥10s |
| **L3** | L2 + **负向对照**(故意造错/造边界, 断言必须红) | 机器 | 摘掉限速下发 → 断言必须失败(红绿双验) |

**硬要求: 每轮至少把 1 条用例升一档, 并写进该轮计划的验收条件。** 做不到就在计划里明写"本轮纯回归, 不加强" + 原因 —— 否则"加强"永远排在"测完"后面, 永远不发生。

- **降级规则**: 用例对应的判据被改过(§07 "判据变") ⇒ 该条**降一档**, 下轮重新爬。
- **记录**: issue §07 每片记 `L0/L1/L2/L3 = 4/6/2/0` 这种分布, 一眼看出"这片还有多少靠人眼"。
- **为什么必须有这条**: 没有它, 每轮排期都是"把上次的人工目视再做一遍", 工作量恒定、覆盖不增 —— 这正是 `manual-walkthrough.md` 那 15 条挂了两个月的机制。

## 09 用例怎么写

- **位置**: `tests-real/<rmNN>_<slug>/`, 用例 id `RM06-01`(写在 docstring 首行 `[RM06-01] <一句话>`, `real.list` 从这里抽)。
- **兼容 pytest**: 可以 `uv run pytest tests-real/... --no-cov` 单跑, 但 `pytest.ini` 的 `testpaths` **不改** —— `test.full` 永远看不到这个目录, 基线数字零扰动。
- **每条必写四行**: `前置`(需要 L0/L1/L2 哪层 + 哪些种子) / `副作用`(会改什么) / `回滚`(怎么恢复) / `失败判据`。
- **只断言外部可观测事实**: qB API 返回、文件系统、进程表、HTTP 响应。内部实现细节归单测, 不在这里断言(否则一次重构让整片变红)。
- **幂等**: 用例必须能重跑 —— 开跑先清自己造的种子/标签/分类, 收尾删干净。
- **禁止**: 连非白名单端口; 读仓库根 `config.yml`; 依赖人工点击(除非明确标 L0); `try/except: pass` 吞异常。
- **L3 的红验**: 与单测同口径 —— 故意破坏后必须看到红, 否则这条不算 L3。

## 10 产物落位

| 产物 | 落点 | 权威 |
|---|---|---|
| 规程(怎么做) | 本文件 | 硬约束 / 守卫 / 切片规则 / 漂移 / 成熟度 |
| 排期锚 + 片表 + 进度 | `issues/<stamp>-test-real-machine-test-standing.html` | 要不要做 / 什么时候做 / 覆盖到哪 |
| 每轮计划 | `plans/<stamp>-plan-real-<片>.html` | 这一轮怎么测、为什么这么测(拍板即冻结) |
| 每轮实测数字 | `testing/real-baselines/<stamp>-real-<片>.md` | 用例数 / 档位分布 / PASS-FAIL-BLOCKED / 基线 commit |
| 用例 | `tests-real/` | 可复用的断言本体 |
| 产品进程起停 | `tests-real/lib/app.py` | 临时配置生成 / 起停 / 抓日志 / 端口探空 / 注册表备份还原(见 §2.7) |
| 手工造种子 | `tests-real/seed.py`(`real.seed*`) | 造/加/看/删假种子, 只服务手工探索, 不参与验收 |
| 诊断工具(非用例) | `tests-real/tools/` | 卡住时的现场采集, 不参与验收 |
| 命令 | `.commands/real/` | 守卫与运行入口 |
| 缺陷 | 各自的 `bug` / `perf` issue | 每条独立排期 |

## 11 反模式

- ❌ 为了跑通用例临时放宽"种子非活跃" —— 一次放宽, 之后所有结论都不可信。
- ❌ 把真机用例塞进 `tests/` 或挂上闸门 —— 需要活 qB 的断言会让提交变成运气。
- ❌ 用印象代替 `git log` 判漂移 —— 结论不可复核, 且必然漏掉"重构后行为变了"。
- ❌ 每轮都从 L0 重做人工目视 —— 工作量恒定, 覆盖不增。
- ❌ 一片撑成三次排期 —— 超预算就按 §05 规则 4 拆, 别硬扛。
- ❌ 把实测发现的缺陷当轮顺手修 —— 会把"测一片"变成"修一片", 下轮排期重新估。
- ❌ 手工双击 exe 起 qB —— 进程归属不明, guard 无法保证"不动其它 qB"。
