# 26-10-17-backend-global-traffic-source-integration — 全局流量来源一键切换 + 工具自动拉起(改版)

**Status:** In Progress
**Added:** 2026-10-17
**Updated:** 2026-10-17 08:25
**Summary:** 用户诉求「全局流量监视器设计不成熟, 特别是与 auto-qb 的联动」: ①auto-qb 一键自动拉起工具(免配端口/密钥) ②工具同时配置 Traffic Monitor 时怎么办 ③两处配置(限速曲线卡的 dat_path 与独立段 global_traffic_monitor)合并为一处 + 来源一键切换。grilling 五轮 36 问收敛(用户四次纠正), 推翻旧计划 26-10-16-0541 的配置落点/发现机制/自启触发/用户可见命名四组拍板, 产出独立计划 26-10-17-0339(Open, doc-topic `global-traffic-source-integration`, 拍板 D1–D19); R1 就地改版(拉起改走工具侧启动器 D19 + D13 收敛为「工具 config 唯一裁决」); 工具侧 S11(目录定位/数据落点/启动器)/S12(发现指针 + 锁锚点)/S13(随机端口 + `endpoint` 子命令)/S14(自启意图布尔开关 + config 回写 + 全称改名 + gitignore)已实施; S15–S19(auto-qb 侧)待逐项授权。
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
| S15 | auto-qb 配置面与升级链 | Open |
| S16 | 探测-拉起-订阅编排(可注入单点) | Open |
| S17 | 设置页合并 | Open |
| S18 | 守阵/基线/文档 | Open |
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
