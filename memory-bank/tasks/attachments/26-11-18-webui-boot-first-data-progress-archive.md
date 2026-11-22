# 26-11-18-webui-boot-first-data — 进度日志早期轮次归档 (R0/R1/R2)
> 摘要: 重启后 WebUI 首份数据任务档案进度日志的早期三轮全文外迁（立档 / S0 真机取证 / S1 启动首轮提前发布），供追溯与守恒核对
> 触发: 外迁, 追溯, 守恒核对

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

- 2026-11-18 06:13 S1 提前发布落地: apply_sync 落库后插启动首轮发布点(落库前 rounds_applied==0 判据), 经 on_sync_line hook 复用发布单点, 4 单测钉核心语义, 相关子集全绿

