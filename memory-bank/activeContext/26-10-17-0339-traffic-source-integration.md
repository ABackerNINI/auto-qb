---
summary: 全局流量来源改版(一键切换 + 自动拉起) — grilling 五轮收敛, 产出独立计划 26-10-17-0339(Open); 推翻旧计划 26-10-16-0541 的配置落点/发现机制/自启触发/用户可见命名四组拍板; R1 就地改版(26-10-17-0429): 拉起改走工具侧启动器(D19) + D13 收敛为工具侧唯一裁决
---

> 摘要: 用户诉求「全局流量监视器设计不成熟, 特别是与 auto-qb 的联动」: ①auto-qb 一键自动拉起工具(免配端口/密钥) ②工具同时配置 Traffic Monitor 时怎么办 ③两处配置(限速曲线卡的 dat_path 与独立段 global_traffic_monitor)合并为一处, 来源一键切换。经 grilling 五轮 36 问收敛(用户四次纠正: 自启与多实例共享不可削减 → 发现机制找不到非 8099/自定义 data-dir 的工具 → 数据不写用户目录 + 编译态定位 → 改问答细节), 产出**独立计划** `memory-bank/plans/26-10-17-0339-plan-global-traffic-source-integration.html`(doc-status Open, doc-topic `global-traffic-source-integration`)。**R1 就地改版**(26-10-17-0429): 用户指出「把 `--autostart` 固化进启动器」与 D13(取值可变)冲突 ⇒ 启动器契约(D10 改写 + 新增 D19) + D13 收敛为「启动器恒定携带意图, 工具 config 唯一裁决」, auto-qb 侧 `autostart` 键退休。
> 最后活动: 2026-10-17 04:29

# activeContext · traffic-source-integration(26-10-17-0339)

**用户诉求(原话要点)**: 全局流量监视器目前设计不成熟, 特别是与 auto-qb 的联动; 设想是 auto-qb 能**一键自动拉起**全局流量监视器, 不需要过多配置、不需要写端口/密钥; 同时要考虑**如果同时配置了 Traffic Monitor 怎么办**; 目前配置全局流量监视器与 Traffic Monitor 在**两个不同的地方**, 需要改为一处, 设想是**全局流量信息来源一键切换**。

**过程**: `commands run my-commit-flow.sync` 开工同步 → 读旧计划 26-10-16-0541 + 工具的 storage/server/__main__/config/tests + auto-qb 的 models/schema/validation/migrations/loaders/tool_client/config_editor/sidefx 取事实 → grilling 五轮(第一轮 7 问 / 第二轮 9 问 / 第三轮 6 问 / 第四轮 8 问 / 第五轮 6 问; 第四轮误重复问第三轮已定的「随机端口」被用户指出)。

**关键事实(实施前须复核漂移, 行号基准 clone @ 88e7e4ee)**:
- 现联动**只经工具控制面 HTTP**, 端口来自 `tool_url` 键、密钥来自 `tool_token_path` 键(或镜像平台默认数据目录); **工具没在跑时 auto-qb 什么都做不了** —— 连 `autostart` 开关本身都要 `POST /autostart` 打到控制面(鸡生蛋), 故「一键拉起」在现设计下逻辑上不可能。
- 工具 = 独立 venv 的包(psutil/filelock), auto-qb venv **刻意不装 psutil**(S0 隔离判据) ⇒ auto-qb 只能起**子进程**, 解释器须指向工具环境; 工具 CLI 只有 `run [--data-dir]`, **端口只能写工具 config(`http_port` 默认 8099)**。
- `server.py` **已支持随机端口**(`port=0` 回填真实绑定端口), 只有配置校验把 0 判非法; 锁 `SingleInstanceLock` 在 `__main__` 早段 acquire、服务其后 start。
- auto-qb **已有 config schema 迁移链**(`MIGRATIONS["config"][n]` + 启动物化单点原子写回/备份), 「配置升级路线」正落在它上面(现到 v4)。
- `tests/sidefx.py` 的 POPEN 白名单只放行 `node` 与临时 wrapper ⇒ auto-qb 侧「拉起工具」必须做成**可注入单点**。
- 缩写 `gtm` 散布面: 包目录 `src/gtm`、CLI 脚本名、`prog`、env `GTM_DATA_DIR`、锁/默认数据目录名、文案、测试与工具侧 S0–S9 记录。
- 生产 `config.yml` 目前**只用 TM**(`global_speed_limit_curve.traffic_source[0].traffic_monitor.dat_path`), **未配** `global_traffic_monitor` 段 ⇒ 迁移痛点小。

**产出计划拍板 19 条(D1–D19, 见计划 §02)**: 单一来源开关(`traffic_source.provider`, 严格互斥不静默回退) / 配置落点合并(顶层 `global_traffic_monitor` 退休, 曲线段只留 curves; **不含 autostart 键**) / 迁移走 v4→v5 升级链 / 工具进程形态不削减(独立 + 开机自启 + 多实例共享) / auto-qb 只做「探测 → 缺席一次性引导拉起 → 控制面订阅」**不当守护者** / 发现指针 `endpoint.json` 落**用户级平台目录**且与 `--data-dir` 解耦 / **就绪判据只认探活**(`GET /status` 200, 残留文件不算) / 单实例锁锚指针旁(整机一个工具)且抢输不占端口 / **随机端口**(`http_port` 默认 0 + `endpoint` 子命令) / 拉起解析(`tool_exe` 显式覆盖 → `tool_dir` 走**工具侧启动器** `launch.cmd`/`launch.sh`; **auto-qb 不拼 uv / 不认识入口名与子命令** = D19) / 双模目录定位(frozen 用 `sys.executable`, 否则 `__file__`; **源码位置定位不了编译后的 exe**) / 数据默认落 `工具安装目录/data`(非 PWD; 旧用户目录数据一次性搬迁; 启动器不传 `--data-dir`) / 自启意图**恒定写死在启动器**, **是否注册由工具 config `autostart` 唯一裁决**(用户关过不被装回), 设置页开关走 `POST /autostart` / 多实例竞争靠锁前置 + 退避, 不做实例间通信 / 设置页并成一张卡 / **改名只限用户可见面**(包名与内部文档继续用 gtm) / 删 `tool_url`/`tool_token_path`/`subscribe`/`autostart` / `qb_traffic` 不进菜单。

**计划步骤**: S11 工具侧目录定位 + 数据落点 + **启动器** → S12 发现指针与锁锚点 → S13 随机端口与 endpoint 子命令 → S14 启动器自启意图/改名/gitignore → S15 auto-qb 配置面与升级链 → S16 探测-拉起(执行启动器, 零参数)-订阅编排(可注入单点) → S17 设置页合并 → S18 守阵/基线/文档 → S19 真机验收(并入旧 S10)。

**与旧计划的关系**: 旧计划 26-10-16-0541 的**工具本体 S0–S9 全有效、不追改**; 其旧 S6/S7/S8 被本计划 S15–S17 取代, 旧 S10 并入本计划 S19。用户拍板「新写计划」(仓库约定本为「改版 = 同文件内变更记录」), 为免 docmap 分叉, 本计划用**独立 doc-topic**; 未改动旧计划文件(单向链接只在正文, 未声明 doc-refs, 故不触发认领链机检)。

**R1 · 计划就地改版(2026-10-17-0429, 纯文档轮, 无代码事实变更)**: 用户令「更新文档」。起因: 用户指出我上一轮提议的「把拉起命令写在工具侧启动器、auto-qb 无参执行」**与 D13 冲突** —— 原 D13 让 auto-qb 条件计算 `--autostart true|false`(provider=工具来源 且 用户未关过 ⇒ 真), 取值**可变**, 而 `false` 那支正是「用户显式关过不被装回」的防复活闸, 固化成常量等于把闸门焊死(实质冲突, 非措辞冲突)。改判: **判断权下放给状态持有者**。落地(同文件内改版 + 抬 doc-updated, 遵 doc-forms.md 第 33 行): ①**D19 新增**「启动器契约」—— 工具根 `launch.cmd`/`launch.sh`, 优先工具自带 venv 解释器、`uv` 仅兜底、恒定携带自启意图、不传 `--data-dir`、编译态内容退化为调同目录可执行文件; auto-qb 只做 resolve_tool_root → 找启动器 → `cmd.exe /c` 或 `/bin/sh` detached 执行; ②**D10 改写**(去掉 auto-qb 拼 `uv run --project … gtm run`, `tool_exe` 降为显式覆盖逃生门); ③**D13 收敛**(auto-qb 不传任何自启参数; 工具 config `autostart` 默认 true 为唯一裁决点; 设置页开关仍走 `POST /autostart`); ④**连带删键**: auto-qb 侧 `autostart` 键退休(D2/D17/S17/§05 同步) —— 否则「工具 config 唯一裁决」又会退化成两处配置; ⑤S11(启动器产物)/S14(布尔开关)/S16(零参执行)/§03(布局+图)/§08(两条新验收: 拉起不依赖 auto-qb 侧 uv · 自启不被装回)/§09(启动器被挡/无 exec 位的对策)/§10(启动器两文件) 同步。**计划文件已改**(doc-updated 26-10-17-0339 → 26-10-17-0429, §01 记 R0/R1 变更记录)。

**待办**: ①S11–S19 **逐步骤显式授权**后实施(每步独立收尾+提交); ②是否为本专题在 `tasks/` 立档(旧专题档案 `26-10-16-backend-global-traffic-monitor.md` 只覆盖到旧 S9); ③旧计划 26-10-16-0541 的 S10 与本计划 S19 归并方式待拍板; ④R0/R1 均为纯文档轮, 未跑 test.full 新建基线切片(无代码事实变更); ⑤「可变意图被固化成常量 ⇒ 与既有拍板冲突」这一轮教训是否要入 `pitfalls/`(kb 类)—— 新建文件需用户显式确认。
