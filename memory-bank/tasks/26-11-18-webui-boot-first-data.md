# 26-11-18-webui-boot-first-data — 重启后 WebUI 首份数据 5-15s: 立项分析(根因链取证 + grilling 拍板 + 提前发布计划)

**Status:** Open
**Added:** 2026-11-18
**Updated:** 2026-11-18
**Summary:** 重启后 WebUI 首份数据 5-15s: 立项分析 + S0 真机取证(根因链两形态实测坐实) + S1 提前发布 + S2 守阵补齐落地(S3 真机验收待做)
**Topics:** webui-boot-first-data
**Refs:** memory-bank/plans/26-11-18-0259-plan-webui-boot-first-data.html, memory-bank/issues/26-11-18-0259-perf-first-round-grouping-files-serial.html, memory-bank/issues/26-11-18-0259-perf-first-round-pathmap-selfcheck-critical-path.html

## 本篇只回答

「重启后 WebUI 首份数据 5-15s(约 210 种子)」的根因是什么、修法怎么拍板、计划推进到哪 —— 根因结论与拍板细节归档在此; 方案正文单点在计划 26-11-18-0259。

## 原始请求

1. 「auto-qb重启后WEBUI刷新后主界面要5-15秒才出现, 种子约210. 之前修过一次.分析原因」(问答/只读轮)
2. 「立项分析, grilling and then create a plan」(执行授权: 立项 + grilling + 计划/档案产出)

## 思考过程与决策

- 根因(取证 2026-11-18, 详见计划 §02): 排除面桩实测(真 create_app + 210 合成种子): /api/state 冷 52ms / 资产串行链 ≈0.4s / CLI 导入 368ms / 渲染面百毫秒级 —— 都不是瓶颈。真正的链: store 不持久化种子记录 → 重启后首个同步必为全量轮(210 全走 added) → `_refresh_torrents`(qbmanager.py:939)整条管线(apply_sync :956 + path_map_selfcheck :966 + full_round :970 + 归组每种子 files 单发 grouping_mod.py:401 ≈210 次往返 + post 冲突检查)跑完才有首次发布(qbmanager.py:851), 窗口期 group_view_dirty 初始 True(runtime.py:112), 首请求抢先发布空代并把 dirty 压住, 含落库数据的代要等管线跑完 flush_views → 5-15s ≈ 管线时长。
- 与上次修复的关系: 26-11-02-0902(首访行高量齐)是前端渲染段, 不覆盖本次根因; 渲染面健康(210 行走估算开窗)。
- 两轮 grilling 11 问拍板 D1-D11(全记录见计划 §06), 用户改判两处: D5 = ②归组 files 串行 / ③path_map 自检关键路径不入主修、入池两条 issue 独立排期; D10 = S0 取证只用 real-machine 轨道环境, 不取生产数字。
- 关键物理事实: qB WebAPI `/torrents/files` 单 hash 专用(qbittorrentapi 源码取证), files 拉取无法批量合并 → groups 页第二跳时刻由②的 issue 承接, 本计划 North Star 按 D9 分视图口径。

## 实现计划

计划单点: `memory-bank/plans/26-11-18-0259-plan-webui-boot-first-data.html`(Open)。
- S0 真机取证: real-machine 轨道环境1/2 + ≈210 假种子受控重启, 量各视图首份数据出现时刻 + 首轮管线日志时间窗, 坐实根因并喂两条 issue 基线数字。
- S1 提前发布: `_refresh_torrents` 在 apply_sync 后插入启动首轮发布点(store 空 + 首个全量同步判据, 不依赖种子数), 复用既有发布单点, 不新增锁/线程/配置键。
- S2 守阵: 单测(两代发布语义/rid 序列/delta 兼容/首代形状) + e2e(桩冷启动两跳) + test.full 全绿。
- S3 真机验收: 同 S0 口径修复前/后对比, flat/singles/shows ≤2s 硬判据, groups 第二跳记录并回写②。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 立项 | 根因分析 + grilling D1-D11 + 计划入库 + ②③入池 | Done(2026-11-18) |
| S0 | real-machine 环境重启取证(各视图首份数据时刻 + 管线时间窗) | Done(2026-11-18, 基线 `testing/real-baselines/26-11-18-0445-webui-boot-first-data-S0.md`) |
| S1 | 启动首轮提前发布(apply_sync 后插发布点) | Done(2026-11-18) |
| S2 | 守阵(单测/e2e/test.full) | Done(2026-11-18, 数字见 kb.baseline 本切片) |
| S3 | 真机验收(修复前后对比, 数字回写 issue②) | Open |

## 进度日志

### R0 · 立档 (2026-11-18)

- 问答轮完成根因分析(排除面桩实测 + 根因链代码取证, 本地桩 210 种子端口 8391 实测后经 dev.port-kill 核身份清理)。
- 分批评审: 三轮(首轮分面×2 + 修复轮×2)累计 11 发现(1 blocker=机制反写: dirty 初始 True 而非 False, 已按真实机制改写 / 1 major=S1 判据竞态失效, 已改「落库后最后一代不含落库数据」判据 / 9 minor=锚点与口径面)全修零 actionable, 引文检 11/11; 评审期间远端锚点前移两次(a5d3175e/9c8824dc 各带 Review:), 批次内容未变。
- grilling 两轮 11 问拍板(D5/D10 用户改判, 余全按推荐); 产出: 计划 26-11-18-0259(Open) + issue ②③(Open) + 本档案; 零代码改动, 基线切片不适用(测试面零改动); 本轮产出件随本专题入库。

- 2026-11-18 03:03 立项轮: 根因链闭环(排除面桩实测: /api/state 冷52ms/资产链0.4s/渲染面百毫秒级均非瓶颈; 真根因=重启首轮全量管线挡首次发布: apply_sync+path_map自检+归组files逐种子单发210次+冲突检查, 窗口期group_view_dirty=False返回空视图) + grilling 两轮11问拍板D1-D11(D5改判②③入池issue两件 / D10改判S0只走real-machine轨道不取生产数字) + 计划26-11-18-0259入库Open(S0-S3待显式开工) + 档案立档; 零代码改动

### R1 · S0 真机取证 (2026-11-18)

- S0 完成: 环境2副实例56590 + 210枚real-fake假种子(256K, 105剧×2集, 死端口announce命中trackers段), 派生配置(schema_version 8/grouping on/WEB 39000免鉴权/非dry-run)受控重启标准2轮(interval 0.25/fetch_timeout 10)+空代竞态探测1轮(0.03/0.1)。**分视图首份数据(t0=spawn): run1 flat/singles/shows=1.113s·groups=1.893s; run2 flat/singles/shows=1.101s·groups=1.639s; 探测轮首响应=0行空代(web bind+0.07s早于落库)·flat/shows/groups=2.421s·singles恒0(全归组库正当稳态)**; 代际两种形态都观测到(标准轮: gen1请求触发flat满/singles全量超集/groups空→gen2管线结束flush收缩; 探测轮: §02.2第3点原样0行空代→空窗到gen2), 零新代窗口=管线期。管线窗(WEB up→检测到新增种子210个)=0.489s(apply_sync+自检no-op+full_round 210 tracker单发); [检测到新增(日志锚点)→gen2(HTTP观测±轮询粒度)]=0.506/0.596/0.734s(files单发+post+flush); 微基准(已落盘, 产品同款客户端keep-alive): files×210=0.445s(2.12ms/次)·trackers×210=0.467s(2.22ms/次)。**根因链判定: 吻合且两形态都直接观测到**(groups首份数据=gen2=管线完成时刻逐点相等; 首请求落点早/晚于落库完成⇒空代/flat满两形态), S1全覆盖。计划外观察项: run2优雅停SIGTERM→退出38.75s(rc=0路径齐全, 疑似主线程阻塞C调用, 挂点未定位)——只报告未入池。证据`testing/real-baselines/26-11-18-0445-webui-boot-first-data-S0.md`; 工具`tests-real/tools/{seed_bulk_boot,measure_boot_first_data,run_s0_boot}.py`(S3复测须显式传`--interval 0.25 --fetch-timeout 10`对齐标准轮); 种子留存56590待S3复测后清。

- 2026-11-18 04:57 S0 真机取证完成: 环境2副实例56590+210枚假种子受控重启2轮+竞态探测1轮, 分视图首份数据实测(标准轮flat/singles/shows≈spawn+1.1s首响应, groups=gen2≈spawn+1.6~1.9s; 探测轮命中0行空代), 管线时间窗与微基准回填两条issue基线, 证据real-baselines/26-11-18-0445

### R2 · S1 启动首轮提前发布 (2026-11-18)

- S1 完成: `qbmanager._refresh_torrents` 在 `apply_sync` 落库后、`need_validate` 分支前插入启动首轮提前发布点 —— 判据 = **落库前 capture `store.rounds_applied == 0`**(纯内存计数: `__init__` 置 0 / `_apply` 每轮自增单点 / 不落盘 / `reset_runtime` 不清 ⇒ 热重载 L2 / qB 重启补 / 重连全量轮均 >0 零行为变化; 不依赖种子数)。发布复用同一 **on_sync_line hook**(`host.run_sync_line(False)` → webui `flush_views` → `_publish_locked`, P2 守阵禁直驱表现层), 不新增锁/线程/配置键; `force=False`(首个主循环发布前不存在未取走版本, "已取走"门控恒可过); 提前发布失败吞异常记 WARNING 不打断首轮管线(权威发布在管线结束既有路径 —— 归组经 `group_key_migrations` 登记 → full 理由触发第二跳; grouping 关闭且无 HR/规则写标签的形态第二跳无迁移理由、靠下一变更轮自愈, site 列可能滞留至该轮, 已知代价面)。单测: 新文件 `tests/test_webui_boot_first_publish.py` 4 用例(管线中即有含落库数据的基础代+site=Unknown 证早于 full_round / 竞态空代不跳过 / 非启动轮零行为变化 / 失败不打断管线) + 既有守阵 `test_p2a_sync_line_flush_propagates_to_host` 按新契约更新(启动首轮恰两次 [False, True]); 相关子集 6 批 38 文件全绿(qbmanager/webui-delta/store/views/grouping/sync/episodes/modules_p5/ui/checking/local_qb/ascii/config/actions/hr), 全量 test.full 留 S2(数字见 kb.baseline)。dry-run 语义核实: flush 路径无 dry_run 门, 提前 fire 与现状同机制(web 未启/无请求 → is_active False → 不发布); 计划外观察(只报告): dry-run/首轮提前 fire 会让 OpsModule 跳检备份对账提前约 1 拍触发(对账自身按进程幂等, 重加路径无 dry_run 门系既有面)。

- 2026-11-18 06:13 R2

### R3 · S2 守阵补齐 (2026-11-18)

- S2 完成(产品代码零改动)。**单测补齐**(盘点 S1 已钉面后只补缺, `tests/test_webui_boot_first_publish.py` 增至 6 用例): `test_base_generation_lacks_site_derived_fields_completion_fills_them` —— 基础代 site 派生面全空(site=Unknown/hr_tag=""/hr_triggered=False/hr_req_time=0, 错误种子只有笼统回退「错误」) + 补全代 HR 派生字段落位(tracker_conf 匹配后现算) + **错误原因补齐面实测口径**: 取数器在任务线(`module.on_task_line` = advance_error_reasons -> flush_views), 同步线两代都不含具体原因, 任务线一代补齐、ver 逐代 +1 —— 计划 §03「第二跳补齐 tracker 错误原因」的表述与实现有差(第二跳只补 site/HR 派生面, 具体原因晚一代), 按实现钉; `test_delta_client_two_generation_sequence_compatibility` —— 时间线恰两代 ver 严格连续(不跳不重)/rid==ver 零回传/补全代经组键迁移降级 full(R10/R11 协议回退, 「多吃一代」实际代价 = 补全代一次全量载荷)/未协商客户端历史形状逐键兼容/真实增量轮(delta_fields 速度)回增量。S1 已显式钉过「groups 首代空、flat 首代满」(test 1 断言原样), 未重复。**e2e 桩冷启动两跳**(可观测性方案): 桩管线毫秒级跑完且 uvicorn 起在管线后, 两跳窗口 HTTP 天然不可观测 —— 加 `--boot-first on` 模式(E2E_BOOT_FIRST 第五维, 默认 off 桩行为逐字不变): store 不预灌、启动首轮经真实 `_sync_line` 在主线程跑(空 store -> rounds_applied==0 判据自然成立)、归组 files 单发在 `_BootGate` 闸口挂起、`/__harness__/boot_go|boot_gate` 两跳放行; 新 spec `e2e/boot-first-two-hop.spec.mjs` 断言 空代(S0 §02.2 第 3 点形态) -> 基础代(flat 满/groups 空/singles 超集/shows 解析 + UI 种子行先出/分组页空) -> 补全代(groups 落位/singles 收缩/flat 恒满 + UI 分组行落位), rid 严格 +1(两跳间零中间代); 观察端轮询/SSE 全程跨两代 = R2 回归面, 同轮 delta-sync 双皮肤全绿。桩配套两处: `_FileEntry`(dict 子类 + 属性访问 —— files 端点可序列化与真归组 `f.name` 两面交集, 纯 dict 会让归组全数落待归组补偿、纯 SimpleNamespace 会让 files 端点 500); boot-first 模式跳过站点健康两态注入(首轮 full_round 重匹配会覆写 tracker_conf)。**静态守阵**: ascii/port-zero/legacy 脚本守阵全绿(踩 1: `ui_harness.py` docstring ①② circled 类符号被 ASCII 闸拦, 改 (a)/(b))。**全量验证**: test.full 全绿(数字见 kb.baseline 本切片); 默认模式抽查 delta-sync + views 全绿(桩默认路径行为逐字不变)。计划 HTML 与两条 issue 未动(收口统一处理)。R1 单写线程守阵以「提前发布同步完成恰一次」断言落实(发布走主循环线程内既有 hook, 无异步形态); 显式 get_ident 断言评审裁量不采。

- 2026-11-18 07:40 R3: 单测 6 用例(S1 面 + S2 补缺: 两代派生字段/错误原因任务线补齐/delta 两代兼容) + e2e 冷启动两跳 spec(--boot-first 模式可观测方案) + 静态守阵全绿 + test.full 全绿(数字见 kb.baseline 本切片), 产品代码零改动

- 2026-11-18 07:26 S2 守阵补齐: 单测补缺(6 用例) + e2e 冷启动两跳(--boot-first 模式) + 静态守阵全绿 + test.full 全绿(数字见 kb.baseline 本切片)
