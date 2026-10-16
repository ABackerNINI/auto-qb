# 26-10-17-backend-global-traffic-source-integration — 全局流量来源一键切换 + 工具自动拉起(改版)

**Status:** In Progress
**Added:** 2026-10-17
**Updated:** 2026-10-17 05:34
**Summary:** 用户诉求「全局流量监视器设计不成熟, 特别是与 auto-qb 的联动」: ①auto-qb 一键自动拉起工具(免配端口/密钥) ②工具同时配置 Traffic Monitor 时怎么办 ③两处配置(限速曲线卡的 dat_path 与独立段 global_traffic_monitor)合并为一处 + 来源一键切换。grilling 五轮 36 问收敛(用户四次纠正), 推翻旧计划 26-10-16-0541 的配置落点/发现机制/自启触发/用户可见命名四组拍板, 产出独立计划 26-10-17-0339(Open, doc-topic `global-traffic-source-integration`, 拍板 D1–D19); R1 就地改版(拉起改走工具侧启动器 D19 + D13 收敛为「工具 config 唯一裁决」); S11(工具侧目录定位/数据落点/旧数据搬迁/启动器)已实施。
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
| S12 | 发现指针与锁锚点 | Open |
| S13 | 随机端口与 `endpoint` 子命令 | Open |
| S14 | 启动器自启意图/改名/gitignore | Open |
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
