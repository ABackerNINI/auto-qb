---
summary: 全局流量来源改版(一键切换 + 自动拉起) — grilling 五轮收敛, 产出独立计划 26-10-17-0339(Open); 推翻旧计划 26-10-16-0541 的配置落点/发现机制/自启触发/用户可见命名四组拍板; R1 就地改版(26-10-17-0429): 拉起改走工具侧启动器(D19) + D13 收敛为工具侧唯一裁决; 工具侧 S11–S14 已实施(目录定位/数据落点/启动器 · 发现指针与锁锚点 · 随机端口与 endpoint · 自启意图/全称改名/gitignore); S15–S19(auto-qb 侧)待逐项授权
---

> 摘要: 用户诉求「全局流量监视器设计不成熟, 特别是与 auto-qb 的联动」: ①auto-qb 一键自动拉起工具(免配端口/密钥) ②工具同时配置 Traffic Monitor 时怎么办 ③两处配置(限速曲线卡的 dat_path 与独立段 global_traffic_monitor)合并为一处, 来源一键切换。经 grilling 五轮 36 问收敛(用户四次纠正), 产出独立计划 `memory-bank/plans/26-10-17-0339-plan-global-traffic-source-integration.html`(doc-status Open, doc-topic `global-traffic-source-integration`)。**R1 就地改版**(26-10-17-0429): 用户指出「把 `--autostart` 固化进启动器」与 D13 冲突 ⇒ 启动器契约(D10 改写 + 新增 D19) + D13 收敛为「启动器恒定携带意图, 工具 config 唯一裁决」。
> 最后活动: 2026-10-17 08:25

# activeContext · traffic-source-integration(26-10-17-0339)

**用户诉求(原话要点)**: 全局流量监视器目前设计不成熟, 特别是与 auto-qb 的联动; 设想是 auto-qb 能**一键自动拉起**全局流量监视器, 不需要过多配置、不需要写端口/密钥; 同时要考虑**如果同时配置了 Traffic Monitor 怎么办**; 目前配置全局流量监视器与 Traffic Monitor 在**两个不同的地方**, 需要改为一处, 设想是**全局流量信息来源一键切换**。

**关键事实(实施前须复核漂移)**:
- 现联动只经工具控制面 HTTP, 端口来自 `tool_url`、密钥来自 `tool_token_path`(或镜像平台默认数据目录); **工具没在跑时 auto-qb 什么都做不了** —— 连 `autostart` 开关本身都要 `POST /autostart` 打到控制面(鸡生蛋), 故「一键拉起」在旧设计下逻辑上不可能。
- 工具 = 独立 venv 的包(psutil/filelock), auto-qb venv **刻意不装 psutil** ⇒ auto-qb 只能起子进程, 解释器须指向工具环境; 工具 CLI 旧只有 `run [--data-dir]`。
- auto-qb **已有 config schema 迁移链**(`MIGRATIONS["config"][n]` + 启动物化原子写回/备份), 「配置升级路线」落在它上面(现到 v4)。
- `tests/sidefx.py` 的 POPEN 白名单只放行 `node` 与临时 wrapper ⇒ auto-qb 侧「拉起工具」必须做成**可注入单点**。
- 生产 `config.yml` 目前**只用 TM**, **未配** `global_traffic_monitor` 段 ⇒ 迁移痛点小。

**产出计划拍板 19 条(D1–D19, 见计划 §02)**: 单一来源开关(`traffic_source.provider`, 严格互斥不静默回退) / 配置落点合并(顶层 `global_traffic_monitor` 退休, 曲线段只留 curves; 不含 auto-qb 侧 `autostart` 键) / 迁移走 v4→v5 升级链 / 工具进程形态不削减(独立 + 开机自启 + 多实例共享) / auto-qb 只做「探测 → 缺席一次性引导拉起 → 控制面订阅」**不当守护者** / 发现指针 `endpoint.json` 落**用户级平台目录**且与 `--data-dir` 解耦 / **就绪判据只认探活** / 单实例锁锚指针旁且抢输不占端口 / **随机端口**(`http_port` 默认 0 + `endpoint` 子命令) / 拉起解析(`tool_exe` 显式覆盖 → `tool_dir` 走**工具侧启动器**, auto-qb 不拼 uv、不认识入口名与子命令 = D19) / 双模目录定位(frozen 用 `sys.executable`, 否则 `__file__`) / 数据默认落「工具安装目录/data」(旧用户目录数据一次性搬迁) / **自启意图恒定写死在启动器, 是否注册由工具 config `autostart` 唯一裁决**(用户关过不被装回), 设置页开关走 `POST /autostart` / 多实例竞争靠锁前置 + 退避 / 设置页并成一张卡 / **改名只限用户可见面**(包名与内部文档继续用 gtm = D16) / 删 `tool_url`/`tool_token_path`/`subscribe`/`autostart`。

**计划步骤**: S11 工具侧目录定位 + 数据落点 + 启动器 → S12 发现指针与锁锚点 → S13 随机端口与 `endpoint` 子命令 → S14 启动器自启意图/改名/gitignore → S15 auto-qb 配置面与升级链 → S16 探测-拉起(零参执行启动器)-订阅编排(可注入单点) → S17 设置页合并 → S18 守阵/基线/文档 → S19 真机验收(并入旧 S10)。每步需用户**逐项显式授权**, 「继续」不算。

**与旧计划的关系**: 旧计划 26-10-16-0541 的**工具本体 S0–S9 全有效、不追改**; 其旧 S6/S7/S8 被本计划 S15–S17 取代, 旧 S10 并入本计划 S19。本计划用**独立 doc-topic** 以避 docmap 分叉, 未改动旧计划文件。

**工具侧已实施(S11–S14; 每步详解见 `tasks/26-10-17-backend-global-traffic-source-integration.md` 进度日志)**:
- **S11**(26-10-17-0534): `storage.resolve_tool_root()` 单点(frozen 取 `sys.executable` 所在目录, 源码态由 `__file__` 上溯到含 pyproject.toml 的工具根) + `default_data_dir()` 改判「<工具安装目录>/data」+ env 改名 `GLOBAL_TRAFFIC_MONITOR_DATA_DIR` + 旧用户目录一次性搬迁(幂等; 显式 `--data-dir` 不搬迁) + 启动器 `launch.cmd`/`launch.sh`(恒定 `--autostart`、不传 `--data-dir`、优先自带 venv 解释器、uv 兜底)。
- **S12**(26-10-17-0623): 发现指针 `endpoint.json`(`_platform_data_home()` 单点 + 十字段 schema + 原子写/幂等删) + 锁锚点从 `data_dir` 迁到指针目录 `instance.lock`(与 `--data-dir` 解耦); `ControlServer.start()` bind 后写指针、`stop()` 删; 写失败只 WARNING 不阻断。
- **S13**(26-10-17-0721): `http_port` 默认 8099 → `0`(内核分配随机空闲端口, `_PORT_RANGE` 下限放开到 0) + `endpoint` 子命令读**同一**指针打印 host:port/token_path/data_dir(端口随机后手工调试唯一出口)。
- **S14**(26-10-17-0825): ①`config` 新增 `autostart` **布尔键**(默认 `true`, 只收真 bool, 进 `_BOOL_FIELDS` 全量校验) + `run --autostart` **布尔开关**(`store_true`, 不承载取值) 顺带幂等注册 —— 裁决权在 config `autostart`(false → 本次 no-op, 用户关过不被装回), 注册排在锁 acquire 后、`server.start()` 前(指针现货探测与真值一致), 失败只 WARNING 不阻断; ②`POST /autostart` 成功回写 config `autostart`(= install/卸载); ③**用户可见面全称改名**(CLI 脚本名/`prog`/`version`/CLI 文案前缀/锁冲突文案/注册项 task·unit·label/systemd Description/启动器兜底命令/工具 README; **包名 `gtm` 与 `-m gtm` 模块名不动**); ④`.gitignore` 增 `tools/global-traffic-monitor/data/` 与 `run/`。

**待办**: ①S15–S19 **逐步骤显式授权**后实施(每步独立收尾+提交); ②旧计划 26-10-16-0541 的 S10 与本计划 S19 归并方式待拍板; ③`docs/configuration.md`(新段/新键)与根 README 回写 → **S18**(计划 §S18 明确), 本轮不动; ④复发坑 `pitfalls/testing/sandbox-tempfile-cwd-fallback.md` 本轮再 **+1**(裸跑工具侧套件未设 TMPDIR 落临时垃圾)。
