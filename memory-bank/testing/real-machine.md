# 真机实测(连真实 qBittorrent 的实测轨)

> 摘要: 第四条测试轨规程 —— 分工与准入、硬约束、环境守卫与假红陷阱、种子层 L0/L1/L2、切片与漂移治理、用例写法。状态与进度不在本文件, 在常驻锚 issue。
> 触发: 真机实测, 真机测试, 连真机, 实测排期, 测试 qB, 36595, 36596, 56589, 56590, 测试环境, QBT_REAL_ENV, 双环境, 假种子, 伪 tracker, 切片, 用例成熟度, 漂移判定, tests-real, real 包, 不走闸门, 免token, 免鉴权, 跳过本地验证, 功能完工, 常用验收
**Refs:** memory-bank/plans/26-11-01-2033-plan-real-machine-rm04-drift-plan.html, memory-bank/plans/26-11-01-2123-plan-real-rm08-drift.html, memory-bank/plans/26-11-04-0140-plan-real-rm08-addendum-missing-merge.html, memory-bank/issues/26-10-31-0641-test-real-machine-test-standing.html

## 00 定位: 四条测试轨的分工

| 轨 | 载体 | 挂闸门 |
|---|---|---|
| 单测 | `tests/`(全 Fake) | ✅ `test.quick` 在 ship 链上 |
| 浏览器 | `e2e/` + 桩服务 | ✅ 改前端门禁 |
| 语料回放 | `sim_qb.py --source=corpus` | ❌ |
| **真机** | `tests-real/` + 测试 qB 双环境 | ❌ **永不** |

**准入判据(反膨胀)**: 能用桩/语料验的**不进真机**。只收: ① qB 真执行才成立(命令回执/真状态变化/限速真下发); ② 必须碰真文件系统/进程/注册表。观感交互归 e2e 轨, 仅「桩数据失真足以改变结论」才进, agent 自跑(`dev.webui`+浏览器自动化)。

**触发时机(2026-11-04 起)**: 本轨转**功能完工驱动** —— 落入上述两类即当轮自跑验收(§06); 没做必须明示理由或记 `BLOCKED`。仍不挂自动闸门; 排期锚降为兜底巡检。同一件事三条轨都测 = 三份断言各自漂移, 选一条其余引用。

## 01 硬约束(违反即事故, 没有"这次特殊")

| # | 约束 | 机检 |
|---|---|---|
| 1 | **只碰白名单实例**: 双环境主/副端口+镜像路径前缀(单点 `tests-real/lib/env_registry.py`, `real.env` 可查) | `real.guard` 越界退出码非 0, 无 `--force` |
| 2 | **只允许 `real-fake` 假种子, 真实 PT 种子禁入**(2026-11-04 已清退真实种子, 不得代造) | guard 前置 pause-all + 2s 看门狗, 违规≥3 中止本轮 |
| 3 | **生产配置零触碰**: 只用 `tests-real/config/*.yml` 派生配置 | guard 撞仓库根 `config.yml` 拒跑 |
| 4 | **不动其它 qB**: 杀/起前核镜像路径 | guard 前后进程比对, 新增/消失即报告 |
| 5 | **不挂闸门**: `ship.*` 链上出现 `real.*` 即缺陷, 立即回滚 | 人 |

> 约束 2 与"测做种"冲突: 该用例标 `[需活跃种子]` 本轮跳过并记账, **不允许**临时放宽; L1/L2 假种子不受此限。

## 02 环境与守卫

### 2.1 守卫(`tests-real/lib/guard.py`, 任何用例先过)

静态白名单(端口/镜像路径/配置路径) → 在线核验(`connection_status` 非 `disconnected`) → 前置快照+归零(记进程与种子, pause 全部) → 运行期看门狗(2s 轮询, 违规暂停+记账) → 收尾恢复快照、删净自造物、重跑进程比对。

### 2.2 起停与进程红线

- 起/停一律 `real.up`/`real.down`(白名单内), **不手工双击 exe**; 端口残留占用走 `dev.port-kill`(只传白名单端口)。
- `real.down` 走 WebAPI `app/shutdown` **优雅退出**(2026-11-06 issue 26-11-06-0448 修复): qB 自己写回 fastresume/state 再退, 退出前等端口释放(60s); 端口没起打印 skip, 镜像路径核验不过 / API 失败 / 超时一律 rc=1 报红留人工核查, **不降级强杀**。非优雅退出会跳过 fastresume 写回, 与 relocate 下线窗口机制相抵触。**2026-11-06 06:37-06:39 真机实测背书(环境2 / qB 5.2.3)**: 6/6 PASS —— 端口释放 / 目标 pid 消失 / 对照实例 56589 全程未动 / `.fastresume` 在 shutdown 窗口内被重写(优雅写回硬证据) / 重启后假种子状态逐字读回; 逐字证据与三态见 `testing/real-baselines/26-11-06-0639-real-RM00.md`。
- 🔴 **禁止一切 `taskkill` 及任何形态的外部进程强制终止**(任何形态/目标, python subprocess 同禁): 生产 qB(26586)与测试实例同名映像, `/IM` 全杀=误杀生产(实际发生)。详见 pitfalls/ops/taskkill-image-name-ban。
- 双实例均 portable(自带 `profile/`), 干净环境换 profile 不删 `%APPDATA%`。
- **多 clone 单实例**: 测试实例全机一套, 同一时刻只允许一个 clone 跑 `real.*`; guard 报端口占用先确认是否别的 clone 在测。

### 2.3 环境·鉴权·读侧

- 选环境: `QBT_REAL_ENV=1|2`, 缺省按 EXE 存在性探测; `real.env` 打印当前环境。环境1 = `36595/36596` + `D:\Programs\qBittorrent-testing`; 环境2 = `56589/56590` + `C:\Programs\qBittorrent-testing`(BT 监听端口单点 = `env_registry.py`)。
- **四实例一律免鉴权**(WebUI 已勾「跳过本地验证」, **永不需要 token**, 旧机制已退役)。**收 401/403 = 设置被重置, fail-closed 修环境**: 去 qB WebUI 重勾后重跑, 不加绕行(绕行触发 IP 封禁 3600s 连环假红)。
- 读侧切片首选 `dev.webui`(关掉自动任务连真机); 它**仍会真写**, 约束 1/2 照适用。

### 2.4 环境级假红陷阱(每片开工先核)

| 陷阱 | 处置 |
|---|---|
| **`connection_status=disconnected`**(端口撞车/网卡残留 ⇒ libtorrent 离线, 整片假红) | `real.up` 后必核, 只接受 `connected`/`firewalled`; disconnected 换端口或清网卡(`set_prefs(current_network_interface="")`, 换机抄 profile 必查, 见 pitfalls/testing/qb-profile-nic) |
| 限速原值 1 KiB/s(环境1)奇数; `/torrents/trackers` 带 `**[DHT]**` 等伪条目 | 曲线用例预置偶数 KiB 收尾还原; trackers 断言按 url 以 `http` 开头过滤(private 种子 msg=「私有 torrent」非错误) |
| `uploaded` 计数与 store 快照滞后(慢 1-2 拍) | 临界断言先 `_wait`/`wait_in_store_state` 追平, 只等 hash 存在不够 |

qB 5.2 API 差异已封装在 `lib/qb.py`; 诊断入口 `tests-real/tools/diag_l2.py` / `diag_log.py <port>`, 卡住先跑别靠猜。

### 2.5 假种子 CLI(`real.seed*`; 参数见 `--help`)

- 默认 256K 够看状态; **>2G 停下等授权**(`--allow-huge --reason` 双写), 只要"大"用 `--no-data`(零落盘; 停 `stalledDL` 不进 `missingFiles`, 测"文件被删"要真删)。
- ≥32M 落 `R:/qbt-fake/`(重启即清; 环境2 无 R: 退回 `.work` 真写盘); 默认无 announce=纯本地做种, 要 announce 用例里用 `FakeTracker`; 自造种子一律打 **`real-fake`** 标签, list/rm/clean 与守卫只认它; 收尾 `real.seed.clean`。

### 2.6 产品进程(`tests-real/lib/app.py`)

- `--dry-run` **不启 WEB**(WEB 类用例不带 dry-run); Windows 外部 SIGTERM=强杀, 优雅退出只能进程内 `signal.raise_signal` 或 `start(graceful_after=N)`; 配置必写 `schema_version: 5`(否则走迁移改写配置); 断言真 pid 用 `real_pid()`, 杀产品进程照 §2.2。
- GUI 依赖解释器带 Tk(`tkinter` 不在 `uv.lock`, `env.sync` 全绿≠能跑界面): 判据 `python -c "import customtkinter"`。

### 2.7 分片陷阱速查(造法细节看用例 docstring 与切片计划)

→ RM02-RM09 与跨卷小容量前置的逐条速查已外迁: [attachments/26-11-08-real-machine-slice-traps.md](attachments/26-11-08-real-machine-slice-traps.md)(26-11-08 cap 清零)。

## 03 种子层: L0/L1/L2

| 层 | 怎么造 | 种子状态 | 能测什么 |
|---|---|---|---|
| L0 | `real.seed` 假种子, 无 announce | paused/stalledUP | 只读数据面 |
| L1 | 构造种子+伪 tracker announce(零 peer) | 零外网流量 | 标签/限速/规则/HR 数据面 |
| L2 | 主做种+副下载, 伪 tracker 回对端 | 真上传下载 | 速率/进度/完成事件 |

L1/L2 已验证解锁(环境1 RM00; 环境2 2026-11-01 实证), 各片直接引用; 大库量级归**语料回放轨**。写 L1/L2 两条铁律: ① announce 用局域网 IP(`lib/net.py: local_host()`), 写 `127.0.0.1` → `WSAEADDRNOTAVAIL`(qB 出站 socket 绑物理网卡); ② 伪 tracker 回包必须排除请求者自己(同 IP 单连接限制会挤掉真 leech; `lib/tracker.py` 已按 port 排除)。

## 04 切片表

片表唯一权威 = 常驻锚 issue §03(RM00-RM10: 基建/启动/主循环/规则/归组迁移/tracker标签/HR/限速/WebUI 读写/通知), 排期序 RM00→01→02→04→03→05→06→07→09→08→10。更新规则见 §05。

## 05 切片更新规则(切/并/拆/下线)

1. 新功能先看是否落既有片 glob: 落得进**并入**, 不开新片。
2. 开新片三门槛**同时满足**: 独立副作用面/前置 + 并入单轮超半天 + 有完成判据。
3. 编号不复用(新片=最大号+1); 功能删除/被取代 ⇒ 片置 `Dropped`, 行保留指向取代者。
4. 拆片: ≥3 个互不依赖副作用面, 或单轮新增用例 >12 条。并片: 连续两轮纯回归且 glob 命中 <3 文件。
5. 改片表必须记账(issue §08 + §07)。
6. **每轮开工 glob 自检**: 命中 0 文件=片已失效(下线); 命中出现不属于该片的大件=边界糊了(拆)。

## 06 一轮的标准动作

**功能完工触发(常用)**: 收尾自检功能落入 §00 两类 ⇒ 当轮自跑: `real.guard` 自检 → 能写成断言的补 `tests-real` 用例走 `real.run --yes`; 观感走 `dev.webui`+浏览器自动化; 主程序走 `dev.run`(派生配置)。结论记 `testing/real-baselines/` 与档案一行验收结论。**没做必须明示理由(环境不可用/纯桩可验/BLOCKED), 不写理由=收尾未完成**。

**定期排期触发(兜底)**: 收到「对〈片名〉做真机实测, 先写分步实施计划」后按序, 不许跳步:
1. 定片(映射不到先按 §05 处置); 2. 漂移体检(§07, 结论进计划开头); 3. 环境自检 `real.guard`; 4. 写分步计划(`plans/` HTML: 用例清单+档位+期望值 / 本轮哪条升档(§08) / `[需活跃种子]` 跳过项+解锁条件 / 验收判据); 5. 执行: 每条 `PASS`/`FAIL`(⇒ scope-guard 入池 bug)/`BLOCKED`(写明原因), **当轮不修缺陷**; 6. 记录: `testing/real-baselines/<stamp>-real-<片>.md`(三态/基线 commit/环境指纹)+更新锚 issue §07; 7. 收尾: 用例代码 `ship.commit`, **不立 task 档案**(常驻锚即档案)。

## 07 漂移处理(判据机械, 不是印象)

每片在锚 issue §07 记**基线 commit**; 开工第一步 `git log <base>..HEAD -- <globs>`: **零命中** ⇒ 只跑回归档(L2/L3 全跑), 不重做人工目视; **有命中** ⇒ 逐条读 diff: 判据变⇒降一档重测, 路径/接口变⇒改锚点重测, 纯重构⇒仍跑标「重构后复验」; **glob 命中 0** ⇒ §05 规则 6; **无人认领新目录** ⇒ §05 规则 1。纪律: 重构不算零命中(行为等价是假设); 基线 commit 必须是真 HEAD, 写不出就从「首轮」重来。

## 08 用例成熟度 L0–L3

| 档 | 判据 | 谁判 |
|---|---|---|
| L0 | 人工目视(**过渡形态非终态**) | 人 |
| L1 | 脚本采集+人判读 | 半自动 |
| L2 | 脚本自动断言 | 机器 |
| L3 | L2+负向对照(故意造错必须红) | 机器 |

**硬要求: 每轮至少 1 条升一档, 写进计划验收条件**(做不到明写「本轮纯回归」+原因); 判据被改过 ⇒ 降一档下轮重爬; 锚 issue 记各片 L0-L3 分布。观感类同爬档(agent 截图判定)。

## 09 用例怎么写

- 位置 `tests-real/<rmNN>_<slug>/`, id 写 docstring 首行 `[RMxx-nn] <一句话>`; 可 pytest 单跑但 **pytest.ini testpaths 不改**(基线零扰动)。
- 每条必写四行: 前置 / 副作用 / 回滚 / 失败判据; 只断言外部可观测事实(内部实现归单测); 幂等(开跑清场收尾删净); L3 红验与单测同口径。
- 禁止: 非白名单端口、读仓库根 `config.yml`、依赖人工点击(除非标 L0)、`try/except: pass` 吞异常。

## 10 产物落位

规程=本文件; 排期锚+片表+进度=常驻锚 issue; 每轮计划=`plans/<stamp>-plan-real-<片>.html`(拍板即冻结); 实测数字=`testing/real-baselines/`(全量基线单点见 kb.baseline); 用例=`tests-real/`; 诊断工具=`tests-real/tools/`; 命令=`.commands/real/`(`real.guard/run/env/up/down/seed*/list/suite`); 缺陷=各自 bug/perf issue。
