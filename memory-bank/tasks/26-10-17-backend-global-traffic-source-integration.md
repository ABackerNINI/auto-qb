# 26-10-17-backend-global-traffic-source-integration — 全局流量来源一键切换 + 工具自动拉起(改版)

**Status:** In Progress
**Added:** 2026-10-17
**Updated:** 2026-10-17 13:52
**Summary:** 用户诉求「全局流量监视器设计不成熟, 特别是与 auto-qb 的联动」: ①auto-qb 一键自动拉起工具(免配端口/密钥) ②工具同时配置 Traffic Monitor 时怎么办 ③两处配置(限速曲线卡的 dat_path 与独立段 global_traffic_monitor)合并为一处 + 来源一键切换。grilling 五轮 36 问收敛(用户四次纠正), 推翻旧计划 26-10-16-0541 的配置落点/发现机制/自启触发/用户可见命名四组拍板, 产出独立计划 26-10-17-0339(Open, doc-topic `global-traffic-source-integration`, 拍板 D1–D19); R1 就地改版(拉起改走工具侧启动器 D19 + D13 收敛为「工具 config 唯一裁决」); 工具侧 S11(目录定位/数据落点/启动器)/S12(发现指针 + 锁锚点)/S13(随机端口 + `endpoint` 子命令)/S14(自启意图布尔开关 + config 回写 + 全称改名 + gitignore)已实施; S15(auto-qb 配置面合并 + v4→v5 升级链)已实施; S16(auto-qb 侧探测-引导拉起-订阅编排: 新增 `core/traffic_source/agent.py` 探测/缺席拉起/状态五态单点 + 可注入启动动作, 订阅方向改从发现指针取端点/密钥 = 删 tool_url/tool_token_path 读路径, 编排挂既有订阅线程每轮先确保可达再注册)已实施; S17(auto-qb 侧设置页合并: 旧过渡 stub 段退休[`GlobalTrafficMonitorConfig` 与 `Config.global_traffic_monitor` 删除, WebUIModule 段认领收缩为 `web`] + 「全局流量来源」单卡[provider 单选 + 选中面展开 + 五态状态区 + 立即拉起/重试/打开工具设置 + 自启开关读指针 + 文件选择器 + 工具参数高级折叠] + 曲线卡删来源字段 + `enabled` 由 provider 派生[修 `conf.enabled` 属性缺失隐患] + 新增 `POST /api/traffic/monitor/relaunch` 与 `WebUIModule.agent`/`request_relaunch`)已实施; S18(守阵补口 4 条[拉起不拼 uv/入口名的静态守阵 · 指针常量跨侧镜像 · 工具运行期目录 gitignore 覆盖 · provider 取数互斥] + 文档四处回写[docs/configuration.md 工具章节整段改版到随机端口/指针/启动器/自启裁决现实 · README · config-reference/keys.md 修 S15 遗留两处口径错 · 三条新坑] + 新基线切片)已实施, S19 待逐项授权。
**Topics:** global-traffic-source-integration

## 原始请求

用户: 「全局流量监视器设计不成熟, 特别是与 auto-qb 的联动」—— ①auto-qb 能一键自动拉起全局流量监视器, 不需过多配置、不需写端口/密钥; ②若同时配置了 Traffic Monitor 怎么办; ③目前「配置全局流量监视器」与「配置 Traffic Monitor」在两个不同地方, 需合并为一处, 全局流量信息来源一键切换。

## 思考过程与决策

全部拍板见计划 §02 的 D1–D19 结论表, 实施不得再自行变更; 确需变更按「计划改版 = 同文件内变更记录 + 抬 doc-updated」处理。要点: 单一来源开关(`traffic_source.provider`, 严格互斥不静默回退) / 配置落点合并(顶层 `global_traffic_monitor` 退休, 曲线段只留 curves) / 迁移走 v4→v5 升级链 / 工具进程形态不削减(独立 + 开机自启 + 多实例共享) / auto-qb 只做「探测 → 缺席一次性引导拉起 → 控制面订阅」不当守护者 / 发现指针 `endpoint.json` 落用户级平台目录且与 `--data-dir` 解耦 / 就绪判据只认探活 / 单实例锁锚指针旁 / 随机端口(`http_port` 默认 0 + `endpoint` 子命令) / 拉起解析(`tool_exe` 显式覆盖 → `tool_dir` 走工具侧启动器, auto-qb 不拼 uv、不认识入口名与子命令 = D19) / 双模目录定位(frozen 用 `sys.executable`, 否则 `__file__`) / 数据默认落「工具安装目录/data」(旧用户目录数据一次性搬迁) / 自启意图恒定写死在启动器、是否注册由工具 config `autostart` 唯一裁决 / 设置页并成一张卡 / 改名只限用户可见面 / 删 `tool_url`/`tool_token_path`/`subscribe`/`autostart`。

**R1 就地改版的判据**: 把「条件计算得到的自启参数」固化成常量, 等于把既有「用户关过不被装回」的防复活闸焊死 —— 判断权应下放给状态持有者(工具 config)。教训入坑档 `pitfalls/kb/discipline.md`。

**与旧计划/旧档案的关系**: 旧计划 26-10-16-0541 的工具本体 S0–S9 全有效、不追改(档案 `26-10-16-backend-global-traffic-monitor.md` 只覆盖那一段); 其旧 S6/S7/S8 被本计划 S15–S17 取代, 旧 S10 并入本计划 S19。本专题用独立 doc-topic 以避 docmap 分叉。

## 实现计划

计划 26-10-17-0339 共 9 步(S11→S19): S11 工具侧目录定位契约 + 数据落点 + 旧数据搬迁 + 启动器 → S12 发现指针与锁锚点 → S13 随机端口与 `endpoint` 子命令 → S14 启动器自启意图/改名/gitignore → S15 auto-qb 配置面与升级链 → S16 探测-拉起-订阅编排(可注入单点) → S17 设置页合并 → S18 守阵/基线/文档 → S19 真机验收(并入旧 S10)。每步需用户**逐项显式授权**, 「继续」不算; 每步独立收尾 + 提交。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S11 | 工具侧目录定位契约 + 数据落点 + 旧数据搬迁 + 启动器 | Done (26-10-17-0534) |
| S12 | 发现指针与锁锚点 | Done (26-10-17-0623) |
| S13 | 随机端口与 `endpoint` 子命令 | Done (26-10-17-0721) |
| S14 | 启动器自启意图/改名/gitignore | Done (26-10-17-0825) |
| S15 | auto-qb 配置面与升级链 | Done (26-10-17-1007) |
| S16 | 探测-拉起-订阅编排(可注入单点) | Done (26-10-17 11:13) |
| S17 | 设置页合并 | Done (26-10-17 13:11) |
| S18 | 守阵/基线/文档 | Done (2026-10-17 13:52) |
| S19 | 真机验收(并入旧 S10) | Open |

## 进度日志

### R1 · S11 实施 (2026-10-17 05:14)

用户指令「实施计划S11: 26-10-17-0339-plan-global-traffic-source-integration.html」= 对 S11 的显式授权(S12–S19 不动), 随后「提交」。开工同步至 ab2e8e30。

**落点**(改 3 文件 + 2 新文件, 纯工具侧、零 auto-qb 触碰): `tools/global-traffic-monitor/src/gtm/storage.py`(新增 `resolve_tool_root()` 单点[D11] + `default_data_dir()` 改判「<工具安装目录>/data」[D12] + env `GTM_DATA_DIR` → `GLOBAL_TRAFFIC_MONITOR_DATA_DIR`[D16] + `migrate_legacy_data_dir()` 旧用户目录一次性搬迁) · `src/gtm/__main__.py`(`_resolve_data_dir()` 接线搬迁, 显式 `--data-dir` 不搬迁; `run`/`autostart` 帮助文案 env 改名) · `tests/test_storage.py`(增改用例: 源码态 + 模拟 frozen 态目录解析、env 覆盖、搬迁四场景、显式目录不搬迁; 头文档测试计划清单同步) · 新增启动器 `tools/global-traffic-monitor/launch.cmd` / `launch.sh`(D19: 恒定 `--autostart`、不传 `--data-dir`、优先自带 venv 解释器、uv 仅兜底、编译态退化为调同目录可执行文件)。

**设计要点**: 「找自己」一律经 `resolve_tool_root()`(frozen 取 `sys.executable` 所在目录, 源码态由 `__file__` 上溯到含 `pyproject.toml` 的工具根), 不散落 `__file__`; 搬迁三闸(旧目录有 `history_traffic.dat` + 目标目录空 + 非同一路径), 幂等可重入、失败只 WARNING 不阻断启动。

**出口判据全过**: ①源码态与模拟 frozen 态下数据目录都解析到「安装目录/data」; ②搬迁幂等测试通过(重复搬迁零副作用)。工具侧全量套件绿 —— 实测数字只记入基线切片 `baselines/26-10-17-0534-global-traffic-source-integration-s11.md`(见 kb.baseline)。

**未动(属计划内后续步骤, 非遗漏)**: `docs/configuration.md` 与工具 README 的旧 env 名 / 平台默认目录文案 → S14 改名面 + S18 文档回写; `data/`、`run/` 的 gitignore 与 `--autostart` 布尔开关 → S14。

**滚动面**: 计划 HTML(本专题计划, 未在本轮改动) · 本档案新建(立档阈值命中: 跨会话 + ≥3 源文件 + 有计划文档) · activeContext 切片 `26-10-17-0339-traffic-source-integration.md`(S11 已实施段 + 待办) · 基线切片新建 · 坑档 `pitfalls/testing/sandbox-tempfile-cwd-fallback.md`(新增) 与 `pitfalls/kb/discipline.md`(R1 改版教训) · kb.index 重建。随本专题「提交」入库。

### R2 · S12 实施 (2026-10-17 06:23)

用户指令「实施计划S12: 26-10-17-0339-plan-global-traffic-source-integration.html」= 对 S12 的显式授权(S13–S19 不动); 开工同步至 e7d89021。

**落点**(改 6 文件, 纯工具侧、零 auto-qb 触碰): `tools/global-traffic-monitor/src/gtm/storage.py`(新增 `_platform_data_home()` 平台用户目录单点 + `pointer_dir()`/`endpoint_path()`/`instance_lock_path()` + `ENDPOINT_SCHEMA=1`[D6] + `write_endpoint()`[原子写] / `remove_endpoint()`[幂等删]; `Storage` 锁锚点从 `data_dir` 迁到 `lock_path` 注入, 默认 = 指针目录 `instance.lock`[D8]) · `src/gtm/server.py`(`ControlServer` 增 `endpoint_file` 注入; `start()` bind 成功后原子写 §05 十字段 + 注册 atexit; `stop()` 删指针; `_autostart_registered()` 探现货态、失败降级 False; 写失败只 WARNING[§09]) · `src/gtm/__main__.py`(标注「锁 acquire 早于 bind/采样」顺序不变式) · `tests/test_storage.py` / `tests/test_server.py` / `tests/test_notifier.py`(装配注入锁路径 + 指针路径 + 自启替身, 新增指针与锁锚点用例 + 「抢输进程不占端口」守阵; 头文档清单同步)。

**设计要点**: 发现指针与单实例锁**都锚在用户级指针目录**(与 `--data-dir` 解耦, 整机一个工具、指针无并发写); 指针写失败不阻断服务(auto-qb 退化为直探默认端口); 协议版本 `schema` 随指针写出(auto-qb 读未知 schema 只告警不猜字段 = S16 消费侧)。

**出口判据全过**: ①第二个实例 fail-fast(锁抢输)、端口零占用(守阵断言 `ControlServer.start` 未被调用 + stderr 含「已持有锁」)、不写指针; ②退出(stop)后指针消失; ③指针 `schema`/`port`/`data_dir`/`token_path` 等十字段齐备且与运行态一致。根 `test.full` 与工具侧套件的实测数字只记入基线切片 `baselines/26-10-17-0623-global-traffic-source-integration-s12.md`(见 kb.baseline; 工具侧较 S11 基线净增 11 条用例)。

**新坑**: `pitfalls/testing/test-lock-path-injection.md`(锁锚点迁出 data_dir 后, 未注入 `lock_path` 的测试会去锁真实用户目录 → 沙箱 `PermissionError` / 沙箱外污染)。

**未动(属计划内后续步骤, 非遗漏)**: `docs/configuration.md` 与工具 README 的旧 env 名 / 平台默认目录 / 锁位置文案 → S14 改名面 + S18 文档回写; `--autostart` 布尔开关与 `data/`、`run/` 的 gitignore → S14; 随机端口与 `endpoint` 子命令 → S13。

**滚动面**: 本档案(S12 段 + 状态表 + Updated 0613) · activeContext 切片(S12 已实施段 + 待办) · 基线切片新建 · 坑档新增 · kb.index 重建。随本专题「提交」入库。

### R3 · S13 实施 (2026-10-17 07:21)

用户指令「实施计划S13: 26-10-17-0339-plan-global-traffic-source-integration.html」= 对 S13 的显式授权(S14–S19 不动), 随后「提交」。开工同步至 2be19e86。

**落点**(改 5 文件, 纯工具侧、零 auto-qb 触碰): `tools/global-traffic-monitor/src/gtm/config.py`(`DEFAULT_HTTP_PORT` 8099 → `0`; `_PORT_RANGE` 从 `(1,65535)` 放开为 `(0,65535)` —— 0 合法 = 内核分配随机端口, `http_port` 不在 `_POSITIVE_FIELDS` 内故不受 >0 约束, 错误文案同步改「期望端口 0-65535」) · `src/gtm/server.py`(`ControlServer` 构造默认端口 `8099` → `0`, 与配置默认对齐; 回填实际端口的绑定逻辑本已就绪, 未动) · `src/gtm/__main__.py`(新增 `endpoint` 子命令 `cmd_endpoint`: 读发现指针打印 `http://<host>:<port>` + `token_path` + `data_dir`; 指针缺失/损坏/schema 未知分别报错或告警——未知 schema 只告警不猜字段 (§05)、已知字段仍打印, 缺失/损坏退出 1) · `tests/test_config.py`(默认值 `http_port == 0` + 端口区间 `0` 由拒改收、负值拒) · `tests/test_server.py`(新增 5 条: 连续两次启动端口不同且各自指针记录一致 · `endpoint` 子命令三字段输出与实际一致 · 指针缺失退出 1 · 指针损坏退出 1 · 未知 schema 告警但仍打印; 头文档测试计划清单同步)。

**设计要点**: 端口默认 `0` 让内核分配随机空闲端口, 随机化后端口对用户不可见 ⇒ `endpoint` 子命令成为手工调试的唯一回告出口(与 D9 呼应, 也是 S16 auto-qb 探测前的自证工具)。`endpoint` 读的是**同一个**发现指针(与 S12 单点一致), 不新增状态。

**出口判据全过**: ①连续启动两次端口不同且均被指针正确记录(守阵); ②`endpoint` 子命令输出与实际一致(URL/`token_path`/`data_dir` 三字段断言); ③工具侧全量套件绿(较 S12 基线 +5 条用例)。根套件无代码改动 ⇒ 回归数字与 S12 基线同量级; 实测数字只记入基线切片 `baselines/26-10-17-0721-global-traffic-source-integration-s13.md`(见 kb.baseline)。

**未动(属计划内后续步骤, 非遗漏)**: CLI 脚本名与 `prog`、env 名、指针/锁文件名、用户级目录名、文案(「另一 … 实例已持有锁」) 的全称改名 + `run --autostart` 布尔开关 + `data/`、`run/` 的 gitignore → S14; 工具 `README.md`/`docs/configuration.md` 旧文案 → S14/S18。

**复发坑**: `pitfalls/testing/sandbox-tempfile-cwd-fallback.md` `复发` **+1** —— 裸跑工具侧套件(未设 TMPDIR)又在工具目录留下 9 个随机名文件 + `pytest-of-11059/`, 提交前手工清理。**为什么没命中: 路由没到** —— 开工只读 `AGENTS.md` 与 memory-bank skill, 未读 `pitfalls/testing/_index.md`。

**滚动面**: 本档案(S13 段 + 状态表 + Updated 0721) · activeContext 切片(S13 已实施段 + 待办) · 工具 README 端口口径两处 + `endpoint` 命令行 · 基线切片新建 · 坑档 `sandbox-tempfile-cwd-fallback.md` 复发+1 · kb.index 重建。随本专题「提交」入库。

### R4 · S14 实施 (2026-10-17 08:25)

用户指令「实施计划S14: 26-10-17-0339-plan-global-traffic-source-integration.html」= 对 S14 的显式授权(S15–S19 不动)。开工同步至 4b418a11。

**落点**(改 15 文件, 纯工具侧、零 auto-qb 触碰 —— 计划 §S14 三条 bullet): `src/gtm/config.py`(新增 `autostart` 布尔键默认 `true`[D13] —— 自启意图唯一裁决权; 增 `_BOOL_FIELDS` 与 `_check_bool_field` 校验器「只收真 bool, 0/1/"true" 一律拒」, 与数值字段 `_reject_bool` 反向对称; `_KNOWN_FIELDS` 并入 bool) · `src/gtm/__main__.py`(`run` 增 `--autostart` **布尔开关** `store_true`[D13/D19] —— 只表示「本次拉起顺带幂等注册」不承载取值; 新增 `_maybe_register_autostart(data_dir, config)`: config.autostart 为假即 no-op, 为真调 `build_installer().register()` 并吞 `AutostartError` 只 WARNING; 调用点在锁 acquire 后、`server.start()` 前[指针现货探测与真值一致]; `prog`/`version`/CLI 文案前缀 `gtm:`→`global-traffic-monitor:`) · `src/gtm/server.py`(`POST /autostart` 成功分支 `replace(self.config_holder.current, autostart=(action=="install"))` + `save_config` + `holder.replace` —— 成功才回写, 失败不落半截状态) · `src/gtm/storage.py`(锁冲突文案改「另一 global-traffic-monitor 实例已持有锁」) · `src/gtm/installer.py`(注册项名改 `global-traffic-monitor-autostart` / `global-traffic-monitor.service` / `com.global-traffic-monitor.autostart`, systemd `Description` 与生成物注释全称化, 提示文案改 `global-traffic-monitor run`; **`python -m gtm run` 模块名不动**[D16 包名不变]) · `pyproject.toml`(`[project.scripts] global-traffic-monitor = "gtm.__main__:main"`) · `launch.cmd`/`launch.sh`(uv 兜底分支改 `global-traffic-monitor run --autostart`; primary 分支保持 `-m gtm run --autostart`) · `README.md`(全称改名面 + `--autostart` 语义段 + 数据目录段 + `POST /autostart` 表格行补回写 + 自启段注册项表) · `.gitignore`(增 `tools/global-traffic-monitor/data/` 与 `run/`) · 测试 `tests/test_smoke.py`(`--version`/`usage` 断言全称) · `tests/test_config.py`(默认值补 `c.autostart is True` + 新增 `test_validate_autostart_bool_field`) · `tests/test_installer.py`(新增 4 条: `--autostart` 布尔开关三态 · config=false no-op · config=true 注册 · 注册失败吞掉) · `tests/test_server.py`(新增 3 条: install 回写 true / uninstall 回写 false / 失败不动 config) · `tests/test_storage.py`(锁文案断言全称)。

**设计要点**: **裁决权单点** —— `--autostart` 只是「意图携带」(`store_true`, `--autostart=false` 直接报错), 真正是否注册由工具 config `autostart` 决定(用户显式关过 = false ⇒ 本次 no-op, 不被装回); `POST /autostart` 是设置页开关的落地口, 成功即把该键回写 config(install→true / uninstall→false), 保证「关过不被装回」的防复活闸有状态支撑。改名**只限用户可见面**(D16): 包名 `gtm`、`from gtm import ...`、`-m gtm`、内部注释/文档照旧。

**出口判据全过**: ①工具侧全量测试绿(较 S13 基线净增 8 条用例, 见基线切片); ②`git status` 在工具跑起来后依然干净(`data/`、`run/` 已被 `.gitignore` 命中, `git check-ignore -v` 实证 `.gitignore:15/16`)。根套件无代码改动 ⇒ 回归数字与 S13 基线同量级; 实测数字只记入基线切片 `baselines/26-10-17-0825-global-traffic-source-integration-s14.md`(见 kb.baseline)。

**复发坑**: `pitfalls/testing/sandbox-tempfile-cwd-fallback.md` `复发` **+1 → 2** —— 裸跑工具侧套件(未设 TMPDIR)又在工具目录留下 `pytest-of-11059/` + 3 个随机名文件, 提交前手工清理。**为什么没命中: 路由没到** —— 开工只读 `AGENTS.md` 与 memory-bank skill, 未先读 `pitfalls/testing/_index.md`。

**未动(属计划内后续步骤, 非遗漏)**: `docs/configuration.md`(新段/新键)与根 `README.md` 回写 → **S18**(计划 §S18 明确列出「回写: docs/configuration.md(新段与新键)、根 README.md、memory-bank 配置参考与踩坑」); auto-qb 侧 `traffic_source`/`provider`/迁移链/探测拉起编排/设置页 → S15–S17; 真机验收 → S19。

**滚动面**: 本档案(S14 段 + 状态表 + Updated 0825) · activeContext 切片(蒸馏压回 cap 内 + S14 段 + 待办) · 基线切片新建 · 坑档 `sandbox-tempfile-cwd-fallback.md` 复发+1 · kb.index 重建。随本专题「提交」入库。

### R5 · S15 实施 (2026-10-17 10:07)

用户指令「实施计划S15: 26-10-17-0339-plan-global-traffic-source-integration.html」= 对 S15 的显式授权(S16–S19 不动), 随后「收尾提交」。开工同步至 66600a25。

**落点**(改 8 源文件, 纯 auto-qb 侧、零行工具侧触碰): `config/models.py`(新增 `TrafficSourceConfig` —— `provider` + `traffic_monitor`/`global_traffic_monitor` 两子对象 + 取数单点 `active_dat_path()`; `GlobalSpeedLimitCurve` 删 `dat_path` 只留 curves/interval/enabled; `GlobalTrafficMonitorConfig` 降为**过渡 stub**; `Config` 增 `traffic_source` 字段) · `config/schema/groups.py`(删 `global_traffic_monitor` 组, 增顶层 `traffic_source` 组[provider enum + 两子块, help「一键切换来源」]; schema_version 抬 5) · `config/validation/{sections,curves,core,rules,__init__}.py`(新增 `_validate_traffic_source` 与 `KNOWN_TRAFFIC_SOURCE_*` 常量; 曲线校验段去内联数据源; `KNOWN_CONFIG_KEYS` 去 `global_traffic_monitor` 加 `traffic_source`; expr 数据源门控改读新段, 与 `active_dat_path()` 同口径) · `config/loaders.py`(新增 `load_traffic_source_config`; 删旧 gtm loader; 曲线 loader 不再读 traffic_source) · `infra/versioning.py`(`CURRENT_VERSIONS["config"]` 4→5) · `config/migrations.py`(注册 v4→v5 `_migrate_config_4_5`) · `core/modules/speed_curve_mod.py`(取数走 `active_dat_path()`; `sections()` 增认领 `traffic_source`) · `rules/expr/env.py`(`_traffic` 走 `active_dat_path()`)。

**迁移口径**(v4→v5, D3): `global_speed_limit_curve.traffic_source[0].traffic_monitor.dat_path` 上移到 `traffic_source.traffic_monitor.dat_path` 后删内联块; 旧 `global_traffic_monitor` 段只迁 `notify_cooldown_s` 到 `traffic_source.global_traffic_monitor.notify_cooldown_s`, `enabled`/`tool_url`/`tool_token_path`/`subscribe`/`autostart` 与整段一并删除; provider 推导 = 旧 gtm 段存在(非空)→ `global_traffic_monitor`, 否则 `traffic_monitor`; 每个被删/被迁的键产出一条 note(经 `migrate_with_notes` 落 WARNING); 对已是 v5 形状的输入幂等无副作用。

**设计要点**: D1 严格互斥落成**取数单点** `TrafficSourceConfig.active_dat_path()` —— provider=traffic_monitor 取 `traffic_source.traffic_monitor.dat_path`; provider=global_traffic_monitor 取「工具数据目录/history_traffic.dat」(data_dir 空则返回空 = 无数据源; 指针来源的细化落 S16); `speed_curve_mod` 与 `rules/expr/env._traffic` 都走它, 不各写一遍。**过渡 stub**: `GlobalTrafficMonitorConfig` 数据类与 `Config.global_traffic_monitor` 字段保留默认值, 好让 S16/S17 才重接的 `webui/tool_client.py` / `routes/traffic_monitor.py` / 前端读旧属性名时不运行期 AttributeError; 但它已从 `KNOWN_CONFIG_KEYS`/schema/loader/校验/键面**全部剔除**(YAML 段交给迁移删)。副作用(已按计划接受): 旧 gtm 段仅含 `enabled:false` 也推成 `global_traffic_monitor`, 迁移 note 有记录。

**出口判据全过**: ①旧形状(v4, 仅 TM dat_path)经 `load_config` 自动升 v5 后取数路径 == 旧行为、provider==traffic_monitor、notes 逐键可读; ②键面基线抬 v5(`commands run test.keys-update` 重生成)且新键全入面; ③`validate_config` 全量聚合新段校验。根 `test.full` 实测数字只记入基线切片 `baselines/26-10-17-1007-global-traffic-source-integration-s15.md`(见 kb.baseline)。

**新坑**: `pitfalls/backend/config-section-retire-across-steps.md` —— 分步退休配置段时直接删数据类/字段会打断「属于后续步骤」的消费者的测试(Python 运行期才 AttributeError); 保留默认值 stub 保绿, 待重接那步再删。**为什么值得记**: 本步开工对「S15 配置面 vs S16 消费侧重接」的边界拿不准, 一度准备越界改 `tool_client`/`routes`; 靠过渡 stub 才把本步收在配置面内且全绿。

**未动(属计划内后续步骤, 非遗漏)**: `webui/tool_client.py` / `routes/traffic_monitor.py` / 前端 JS·设置模板仍读过渡 stub → S16/S17; `docs/configuration.md`(新段/新键)与根 `README.md` 回写 → **S18**; 真机验收 → S19。

**滚动面**: 本档案(S15 段 + 状态表 + Updated 1007) · activeContext 切片(S15 已实施段 + 待办) · 基线切片新建 · 坑档新增 · kb.index 重建。随本专题「提交」入库。

### R6 · S16 实施 (2026-10-17 11:13)

用户指令「实施计划S16: 26-10-17-0339-plan-global-traffic-source-integration.html」= 对 S16 的显式授权(S17–S19 不动)。开工同步至 14bfae19(快进 4434f365→14bfae19)。

**落点**(新 2 文件 + 改 2 文件, 纯 auto-qb 侧、零行工具侧触碰 —— 计划 §S16 四条 bullet):
- 新增 `src/auto_qb/core/traffic_source/__init__.py`(包 docstring: 只放 agent) 与 `agent.py`(**联动单点**): `_platform_data_home()`(Windows `%LOCALAPPDATA%` / macOS `~/Library/Application Support` / 其余 `$XDG_DATA_HOME` 或 `~/.local/share`) → `pointer_dir()`/`endpoint_path()`(镜像工具侧 `global-traffic-monitor/endpoint.json`, **不 import 工具包**) + `default_tool_dir()`(`<仓库根>/tools/global-traffic-monitor`) + `ToolEndpoint`/`LaunchTarget` 数据类 + `read_pointer()`/`parse_pointer()`(schema 未知或缺 host/port/token_path **只告警不猜字段**[D6]) + `discover()` + `probe()`(延迟 import `webui.tool_client`, 读密钥 → `GET /status`, **只认 200**[D7]) + `resolve_launch_target()`(`tool_exe` 存在优先 → `tool_dir` 启动器, 空则兜底默认工具目录[D10/D19]) + `launch_tool()`(模块级**可注入单一动作** —— `is_exe` 直执行; Windows `cmd.exe /c` + `DETACHED_PROCESS`, POSIX `/bin/sh` **新会话**; stdin/out/err=DEVNULL, cwd=脚本目录, **零参数**[D13]) + `TrafficSourceAgent`(状态机: `ensure_running()` 探活成功直返; 缺席按 D10 拉起一次, **首次引导窗口 120s / 常态 10s**, 窗口耗尽记失败 + **固定 30s 退避**[D14]; `status()` 供 UI 读**五态**; `_note_error`/`_clear_error` 同因只首报 WARNING 之后 DEBUG[不刷屏])。
- 改 `src/auto_qb/webui/tool_client.py`(**订阅方向重接指针**): `TrafficMonitorSubscriber` 增 `self._agent`; `_pass()` 重写为四步 —— 期望态为真 → `agent.ensure_running()` 确保可达(探活/缺席拉起) → 注册键未变则心跳、变了/未注册则注销重注册; 工具未就绪时短轮询(`_NOT_READY_POLL_S=3.0`); `_conf()` → `traffic_source.global_traffic_monitor`; `_desired()` 首闸改判 `traffic_source.provider != "global_traffic_monitor"`; `_register/_heartbeat/_unregister` 全改用 `endpoint.base_url`/`endpoint.token_path`、注册键含工具基地址(**端口随机变则重注册**); **删除 `tool_url`/`tool_token_path` 读路径**(`resolve_token_path`/`tool_default_data_dir` 只剩 S17 代理路由在用)。
- 改 `tests/test_traffic_monitor_client.py`(订阅客户端用例改到指针 + provider 契约; `sub_env` 写指针 + 注入假拉起动作) + 新增 `tests/test_traffic_source_agent.py`(agent 单测 11 条: 指针路径/parse schema 闸/探活/拉起解析序/默认工具目录与启动器/拉起+退避/未安装/状态/命令构造; 头文档「测试计划」清单同步)。

**设计要点**: 「拉起工具」做成**模块级可注入单点** `agent.launch_tool` —— 生产走真 `subprocess.Popen`(Windows `DETACHED_PROCESS`), 测试 monkeypatch 成假动作, 以绕开 `tests/sidefx.py` 的 POPEN 白名单(现仅放行 `node` 与临时 wrapper, 判据见 `pitfalls/testing/side-effects.md`)。core→webui 用**函数内延迟 import** 规避循环依赖。auto-qb **不做守护**(D5): `ensure_running()` 是「探测 → 缺席一次性引导拉起」, 别的实例已拉起则不重复拉(D14)。

**出口判据全过**: ①工具未跑时 auto-qb 能自动拉起并订阅成功(探活失败 → 拉起一次 → 播下窗口 → 后续轮探活成功即注册); ②工具在跑时零拉起(探活 200 直返); ③探活失败按固定退避重试且**不刷日志**(同因首报 WARNING 之后 DEBUG)。根 `test.full` 实测数字只记入基线切片 `baselines/26-10-17-1113-global-traffic-source-integration-s16.md`(见 kb.baseline)。

**未动(属计划内后续步骤, 非遗漏)**: 过渡 stub `GlobalTrafficMonitorConfig` 与 `routes/traffic_monitor.py`(设置页代理方向仍读旧属性名, 见 `pitfalls/backend/config-section-retire-across-steps.md`) → **S17** 合并后删; `docs/configuration.md`(新段/新键)与根 `README.md` 回写 → **S18**; 真机验收 → S19。

**滚动面**: 本档案(S16 段 + 状态表 + Updated 1113) · activeContext 切片(最后活动 + R1 行) · 基线切片新建 · kb.index 重建。随本专题「提交」入库。

### R7 · S17 实施 (2026-10-17 13:11)

用户指令「实施计划S17: 26-10-17-0339-plan-global-traffic-source-integration.html」= 对 S17 的显式授权(S18–S19 不动)。开工同步至 38ac4fa6。

**落点**(改 18 文件 / 纯 auto-qb 侧, 零行工具侧触碰 —— 计划 §S17 三条 bullet):

- **后端 · 过渡桩段退休 + provider 派生**: `config/models.py`(删 `GlobalTrafficMonitorConfig` dataclass 与 `Config.global_traffic_monitor` stub 字段) · `webui/module.py`(`sections()` 收缩为 `("web",)` —— 旧段职责已归 speed_curve 的 `traffic_source` 认领; 新增只读 `agent` 属性与 `request_relaunch()` 供路由与订阅客户端同源) · `webui/server/routes/traffic_monitor.py`(`_tm_conf` 改读 `traffic_source.global_traffic_monitor`; 新增 `_webui_module`/`_provider`/`_source_status`/`_ready_endpoint` —— `enabled` 由 `provider == "global_traffic_monitor"` 派生[i.e. 修 `conf.enabled` 属性缺失的生产级隐患], notify 闸门同判; 状态区五态 + ready 时附工具 `/status` 回显; 新增写端点 `POST /api/traffic/monitor/relaunch`[409 = 无订阅线程可促])。
- **schema**: `config/schema/groups.py` 的两个来源子段补 `show_if=("provider", ...)`(选中谁展开谁)。
- **前端 · 新卡「全局流量来源」**: `static/shared/config_hub.js`(HUB_GROUP_META 增 `traffic_source` / 删 `global_traffic_monitor`; HUB_OFF_KEYS 删该行; `hubGo`/`hubReadout` 接线; 重写 `tm*` 方法块 —— `tmProvider`/`tmSetProvider`/`tmProviderItems`[从 schema 树取选中面子段叶子字段]/`tmStateText`/`tmStateClass`/`tmLoad` 读新返回键/`tmRelaunch`+`tmPollSettle`[有界轮询 15×2s + pollGen 代际守卫]/`tmOpenToolSettings`/`tmAutostart`[失败回滚] + 文件选择器 `tmPick*`) · `static/shared/state.js`(tm 数据模型重写: 五态 + pick 子状态) · `static/shared/tpl/settings.html`(新 `v-else-if="hub.view === 'traffic_source'"` 分支, 并压在 400 行分片上限内) · `static/shared/triggers.js`(登记 `POST /relaunch`)。
- **前端 · 曲线卡删来源**: `static/shared/config_editor.js`(`cfgCurveEnable`/`cfgCurveItems` 去掉 `traffic_source` dat_path 项 —— 来源只在设置页一处)。
- **测试**: `tests/test_web_traffic_monitor.py`(路由用例改到指针/provider 契约 + relaunch 三态) · `test_web_traffic_monitor_notify.py`(夹具由 `.enabled=True` 改 `provider="global_traffic_monitor"`; disabled 用例断言新 reason) · `test_traffic_monitor_client.py`(同; e2e 补 `global_traffic_monitor.data_dir` 令 provider=工具面时曲线取到同一 dat) · `test_config_traffic_monitor.py` / `test_web_route_manifest.py` / `webui_helpers.py` / `helpers.py`(键面 / 路由清单 / 段认领基线随退休面更新)。

**设计要点**: 「联动是否启用」不再有独立配置键 —— 单一开关就是 `traffic_source.provider`(D1 严格互斥), 路由的 `enabled` 字段降为**派生展示位**; 设置页开关(`autostart`)状态读指针 `autostart_registered`、拨动走 `POST /autostart`(D13: auto-qb 不持有也不计算该状态); 「立即拉起」只置跨线程标志 + 唤醒订阅线程(拉起仍由订阅线程执行, 黄金法则 5)。

**出口判据全过**: ①「配置来源」只在设置页一处(曲线卡已删来源字段); ②切换(provider 单选 + 选中面展开)/拉起(relaunch 409↔200, 前端五态轮询)/状态展示(五态 + ready 回显)三种交互经路由与模板守阵实测可用; ③根 `test.full` 全绿, 实测数字只记入基线切片 `baselines/26-10-17-1311-global-traffic-source-integration-s17.md`(见 kb.baseline)。

**取舍留痕**: ①「打开工具设置」= 新标签打开工具控制面根地址(`tool_url`), 工具无 HTML 页时浏览器显示 JSON —— 可接受(控制面本就是 JSON API); ②文件选择器受 `/api/fs/dirs` 白名单限制(只列目录、限在允许保存路径内), 范围外只能手填绝对路径, 卡片内已写明。

**未动(属计划内后续步骤, 非遗漏)**: `docs/configuration.md`(新段/新键)与根 `README.md` 回写 → **S18**(S17 无配置键面新增, 只是删过渡 stub); 真机验收 → S19。

**滚动面**: 本档案(S17 段 + 状态表 + Updated 1311) · activeContext 切片(S17 已实施段 + 待办) · 基线切片新建 · kb.index 重建。随本专题「提交」入库。

### R8 · S18 实施 (2026-10-17 13:52)

用户指令「实施计划S18: 26-10-17-0339-plan-global-traffic-source-integration.html」= 对 S18 的显式授权(S19 不动)。开工同步至 `098d98ab`(快进 `14bfae19→098d98ab`, 3 笔)。

**先核缺口再动笔**: S11–S17 已把计划 §S18 列的五类工具侧守阵(指针写删 / 锁前置 / 随机端口 / frozen 分支 / 搬迁幂等)与 auto-qb 侧(新段校验 / 迁移链 / 探测拉起可注入 / 键面基线)**逐条覆盖**, 故本轮只补 §08 验收判据里仍无守阵的三条 + provider 互斥一条, 不重复造用例。

**落点**(改 2 测试文件 + 4 文档 + 3 新坑档 + 1 基线切片, 零源码改动 —— 守阵/文档轮):
- `tests/test_traffic_source_agent.py` —— 3 条新守阵(头「测试计划」同步): ①`test_launch_path_has_no_uv_or_entry_names`(AST 扫 agent.py 非 docstring 字符串, 禁 `uv`/`gtm`/`-m`/`run`/`--autostart`/`--data-dir` —— 「怎么起工具」只许在工具侧启动器里; 运行时命令形状由既有 `test_launch_tool_builds_platform_command` 逐 token 钉住); ②`test_pointer_constants_mirror_tool_side`(AST 读工具 `gtm/storage.py` 的 `POINTER_DIR_NAME`/`ENDPOINT_FILE_NAME`/`ENDPOINT_SCHEMA`, 与 agent 镜像常量同值 —— 工具是独立包, auto-qb 不 import 它, 只能靠守阵钉漂移); ③`test_tool_runtime_dirs_are_gitignored`(读 `.gitignore` 文本断言 `data/` 与 `run/` 在场; **不起 git 进程**, 否则撞 `tests/sidefx.py` 的 POPEN 白名单)。
- `tests/test_config_traffic_monitor.py` —— `test_active_dat_path_provider_is_exclusive`: 两来源参数并存时只有 provider 选中者参与取数; 工具面缺 `data_dir` 返回空而**不回退** TM(§08「来源真正互斥 / 断言取数源唯一」)。
- `docs/configuration.md` —— 全局限速曲线段去内联来源(改指顶层 `traffic_source`); 工具章节整段改版到 S11–S17 现实: 全称 CLI / `<工具安装目录>/data` + 一次性搬迁 / 指针目录与 `instance.lock` / **随机端口**(`http_port` 0, 排障走 `endpoint` 子命令) / 启动器 `launch.cmd·sh` / 自启裁决在工具 `config.autostart`; 新增「auto-qb 侧: 发现与自动拉起」「auto-qb 侧配置(traffic_source)」两节; 迁移检查单重写(切来源 = 改 `provider` + 填 `data_dir`); 双写者禁令改口径。
- `memory-bank/config-reference/keys.md` —— **修 S15 遗留两处口径错**: `tool_dir` 留空 = 仓库内默认目录(原文写「按 PATH 查找」)、`tool_exe` 非空且存在优先于启动器(原文写「默认名」); `data_dir` 注明「取数用, 留空 = 无数据源」。这处漂移是写 S18 文档时对照 `agent.resolve_launch_target()` 才发现的 —— 键面守阵只查「键有没有出处」, 不查「说明对不对」。
- `README.md` —— 限速特性补一条「整机流量来源一键切换」。
- 新坑三条: `pitfalls/backend/traffic-source-discovery-pointer.md`(指针/锁锚用户级目录、就绪只认探活、锁前置、跨包镜像) · `pitfalls/backend/traffic-source-random-port.md`(随机端口后写死端口全失效、订阅注册键须含基地址) · `pitfalls/git/runtime-data-in-repo.md`(运行期数据落仓库内必须同笔补 ignore)。
- 基线切片 `baselines/26-10-17-1352-global-traffic-source-integration-s18.md`(实测数字唯一落点)。

**红绿双验**(4 条新守阵逐条突变判红后 `git checkout` 还原, 字节级一致): agent 加 `_MUT = "uv run gtm run"` → ①红; 工具 `POINTER_DIR_NAME` 改 `gtm` → ②红; `.gitignore` 注释 `data/` 行 → ③红; `active_dat_path()` 工具面缺 `data_dir` 时回退 TM → ④红。

**踩到已记的坑 1 条**: 首次还原 agent.py 用 `Path.write_text` 把 LF 写成了 CRLF(`pitfalls/git/editing-traps.md` 家族) —— 已 `git checkout` 复原; 后续突变一律 byte 级读写。另: 全量测试跑到一半时我还在改 `keys.md`/坑档 ⇒ `test_kb_topic_files_have_metadata` 判红(坑档 `> 触发:` 行被我的 Edit 吃掉了), 属**并发自扰**不是真缺陷 —— 修好三行头后复跑全绿。

**出口判据全过**: ①全量 `test.full` 绿(数字见 kb.baseline 最新切片); ②文档四处无漂移(docs/configuration.md · README · config-reference/keys.md · pitfalls); ③`kb.index` 21 个生成物重建; ④KB 守卫单跑绿、副作用越界 0。数字只记基线切片。

**未动(属计划内后续步骤, 非遗漏)**: S19 真机验收(四条: 未跑→自动拉起→订阅成功 / 自启后重启零拉起 / 双实例共享 / 切回 TM 后工具参数保留不参与取数)。

**滚动面**: 本档案(R8 段 + 状态表 + Updated) · activeContext 切片 · 基线切片 · 三条新坑 · kb.index 重建。
