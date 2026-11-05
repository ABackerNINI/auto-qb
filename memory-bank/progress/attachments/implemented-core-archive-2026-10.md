# 已实现 · 客户端 / 主循环 / 状态 · 2026-10 上旬段 (外迁存档)

> 摘要: 2026-10-01~10-05 段原文逐字外迁 —— recheck 证据门控 / 跨组文件冲突 / 热重载任务补建 / HR 绑定重绑 / .!qB 容忍 / 托盘 join / 主循环退避等 7 条。
> 触发: 已实现, recheck, 跨组冲突, 热重载, 外迁存档

> 本文件是外迁存档: 主档 `memory-bank/progress/implemented-core.md` 的 2026-10-01~10-05 段 原文逐字搬来(仅相对链接整体下移一层 —— 本文件在 `progress/attachments/`); 主档原位留指针。

- **主循环异常路径退避 (2026-10-05, issue [26-10-02-0728](../../issues/26-10-02-0728-bug-mainloop-first-tick-exception-no-backoff.html))**: 时间线推进写在动作之后, 异常时 next_*_at 恒过期 ⇒ wait_for=0 快速重试; 异常分支把两条时间线推到 max(原值, now+main_tick), 守阵 `test_run_exception_backs_off_next_tick`。

- **recheck 轮询生效确认整体重设计: 证据门控判定 (2026-10-04, 计划
  [plans/26-10-04-1824](../../plans/26-10-04-1824-plan-ops-recheck-effect-confirmation.html) 全段, issue
  [26-10-03-1140](../../issues/26-10-03-1140-bug-ops-recheck-false-success.html) Done)**:
  recheck 轮询原成功分支 `if rec.progress >= 1.0` 直接对陈旧快照下结论 —— 已完成种子提交后首跳
  (入队即到期)读到 qB 异步应用前旧快照误判「校验成功」(生产事故 2026-10-03: 4 条 40GB 同毫秒假成功)。
  重设计四件: ①`rules/checking_meta.py` 判定纯函数 `poll_verdict` + 证据谓词 `is_piece_checking`
  ({checkingDL, checkingUP}, 排除 qB 启动期 checkingResumeData 伪证据) —— SUCCESS 仅 seen_checking
  可达, 「无证据成功」签名层面不可表达, 160 组合穷举钉死; ②ops_mod poll 闭包重构为证据门控状态机
  (证据闩收窄 / 未见证据 progress 回落提前判「校验未通过」/ START_TIMEOUT 判败前一次性仲裁直查
  D5 ≤1 次, 超时日志报真实时长); ③R1 提交点实时复核 (快照→冷却→live 单 hash 直查→登记→发送,
  跳检 R2 同款: live 空 skip / live checking 拒绝 / 异常 fail-closed), baseline_progress 改取 live
  真值; ④模式固化: 坑档 [pitfalls/backend/effect-confirmation.md](../../pitfalls/backend/effect-confirmation.md)
  + ops_mod 模块头判定纪律 (新异步操作接入 = 新 source, 判定必须走证据门控)。等价性红线不破:
  周期观测纯快照读零 API, 直查只在决定性时刻。新增用例 15 条 (A3/B3/C3/D4/E2) + 既有适配 27 处;
  test.full 2530 passed + 4 skipped / 99% (基线
  [26-10-04-2256](../../testing/baselines/attachments/26-10-04-2256-ops-recheck-effect-confirmation.md))。
  五棒串行子智能体实施 (S1-S4, 编排者核验提交), 档案
  [tasks/26-10-04-backend-ops-recheck-effect-confirmation](../../tasks/26-10-04-backend-ops-recheck-effect-confirmation.md)。

- **跨组文件交叉检测与紧急处置 (2026-10-04, 计划
  [plans/26-10-04-0107](../../plans/26-10-04-0107-plan-cross-group-file-conflict.html) S0-S5 全段, issue
  [26-09-22-2221](../../issues/26-09-22-2221-feat-cross-group-file-conflict.html) Done)**:
  组边界不等于文件不交叉(部分重叠文件列表 / 大小写不同 / junction·symlink 别名同目录), 新种子下载会
  静默覆盖另一组已下载数据且不可逆 —— 既有三条防线都以「同组」为边界够不到跨组。落地四件: ①独立开关
  `grouping.cross_group_conflict_check` 默认关(全链贯通, 键面基线 154→155); ②grouping_mod
  `_check_cross_group_file_conflicts` 四步判定 —— store.groups×group_sizes 物理路径全量展开(目录级
  `realpath_lexical` 别名解析 + 检测私有 `_cross_physical_key` normcase 归一, **不动 path_normalize**)
  → 交叉事件 → MISSING 豁免(任一侧带标签 = 重下补救合法) → 按组对聚合激活警告; 纯内存零触盘、零新增
  qB 请求, 增量轮 dirty 空短路; ③处置 = `store.cross_group_conflict_warned` 组对去重 + 仅暂停涉事
  下载方 `torrents_stop(dl_hashes)`(绝不传整组) + 消除循环(discard 过期组对, 下次重现再触发);
  ④Web 组视图组名旁 cross_group_conflict `#i-warn` 标记(warned 集合派生 + view_changed 显式置脏兜底)。
  新增用例 19 条(config_schema 3 / grouping 15[平台 skipif 拆分] / web 1); test.full 2441 passed +
  4 skipped / 99% / 36.16s(基线 [26-10-04-0412](../../testing/baselines/attachments/26-10-04-0412-cross-group-conflict-detection.md));
  真机走查留待用户。档案 [tasks/26-10-04-backend-cross-group-conflict](../../tasks/26-10-04-backend-cross-group-conflict.md)

- **热重载 L2 重建后种子级任务补建: RulesModule 订阅 full_round (2026-10-04, issue
  [26-10-01-2147](../../issues/26-10-01-2147-bug-webui-hotreload-newsite-maintenance.html) 认领修复)**:
  `rebuild_runtime` 换新 TaskQueue 后只有全局任务自注册重入队, 种子级任务(内置 maintenance + interval
  规则任务)随旧队列丢弃且唯一触发源 torrents_added 相位对存量记录不触发(`_apply` 只对 prev 没有的
  hash 判 added)⇒ 所有 L2 级热重载后存量种子维护面停摆直到重启。修法三件: ①`TaskQueue.has_task(kind,
  name, hash)` 查重助手(`has_named` 委托归一); ②RulesModule 订阅 `full_round`(装配序在 TrackerModule
  重匹配之后), conf 已就位且任务面缺失的存量记录补建, conf 仍 None(未匹配站点)留待下轮; ③
  `_create_torrent_tasks` 入口幂等(maintenance 任务在队即整面跳过, 首轮全量轮「补建先于 added 管线」
  双入口互斥) + `immediate=True`(补建任务立即到期, 下一 tick 兑现一次维护消费 `external_tag_changes`
  —— on_change「首轮全量收敛」契约成立)。红验先行 3 用例(test_modules_p5.py)。坑档
  [pitfalls/backend/hot-reload-stale-bindings-derived-views.md](../../pitfalls/backend/hot-reload-stale-bindings-derived-views.md);
  档案 [tasks/26-10-04-backend-hotreload-torrent-task-restore](../../tasks/26-10-04-backend-hotreload-torrent-task-restore.md)

- **HR 热重载存量绑定陈旧修复: `TrackerModule.apply` 重绑存量记录 (2026-10-03, 计划
  [plans/26-10-03-0436](../../plans/26-10-03-0436-plan-hr-hotreload-webui-stale-display.html) P1, `2a5d07a2`)**:
  热重载只换 `manager.config` 对象, 存量 `rec.tracker_conf` 仍指旧 `TrackerConfig`(其 `hr_check` 派生视图为
  None; 重绑两条旧路 —— L2 判据只比绑定三元组 / full_round 只补 None —— 都不覆盖配置值类变更) ⇒ HR 判定 /
  `HrRuntime._anchors()` 锚点收集 / `hr` 规则段三个消费面全瘫, WebUI 恒显「本地·达标」。
  修法 = 认领模块 `apply(old,new)`: `old.trackers != new.trackers`(整段按值比较)即遍历
  `store.by_hash` 中 `tracker_conf is not None` 的记录执行 `rec.tracker_conf = self.match(rec)`
  (回执 `tracker:rebound N`), 相等短路零动作, `ctx.api.client is None` 防御跳过不抛 ——
  一处修复覆盖三个消费面, 不动 L2 结构判据。守阵 test_tracker.py 三用例(存量重绑+回执 / client=None /
  相等短路, 红验过)。坑档 [pitfalls/backend/hot-reload-stale-bindings-derived-views.md](../../pitfalls/backend/hot-reload-stale-bindings-derived-views.md);
  档案 [tasks/26-10-03-backend-hr-hotreload-stale-display](../../tasks/26-10-03-backend-hr-hotreload-stale-display.md)

- **缺文件扫描过渡态容忍: .!qB 孪生存在不判缺失 (2026-10-01, 清偿 issue
  [26-09-21-0219-bug-qb-move-dot-qb-suffix-recheck](../../issues/26-09-21-0219-bug-qb-move-dot-qb-suffix-recheck.html),
  按计划 [26-09-22-2038](../../plans/26-09-22-2038-qb-move-dot-qb-suffix-fix-plan.html) 修法 1 主体)**:
  qB 移动种子搬运窗口内文件被临时改名 .!qB, 缺文件扫描把过渡态读成永久缺失 ⇒ 误停整组 + MISSING 标签。
  修法 = grouping_mod.py 汇聚点单点容忍(.!qB 孪生存在不判缺失) + 连续 3 次上限兜底残留; 计数为会话级
  内存态(store.transitional_missing_skips)**不落盘**; 孪生探测经 fa.exists() 三态语义适配文件访问层
  (docker 逻辑路径直探 syscall 恒 False, 否则容忍静默失效)。测试 +8(grouping 5 / utils 2 / file_access 1,
  红验 5 failed → 落码 7 passed); 计划 doc-status 完档 Done。**已入库 `c353e899`**(W2 清偿 3/3);
  档案 [tasks/26-09-22-backend-qb-move-missing-tolerance.md](../../tasks/26-09-22-backend-qb-move-missing-tolerance.md)。

- **托盘退出 join 超时 5s→10s + 超时 WARNING (2026-10-01, 清偿 issue
  [26-09-21-1347-bug-tray-join-timeout-abandons-save](../../issues/26-09-21-1347-bug-tray-join-timeout-abandons-save.html))**:
  主循环 daemon 线程 join(5s) 超时即放弃 ⇒ 优雅退出撞上长任务时本次运行期 state 不落盘(黄金法则 3 收口)。
  修法 = issue 候选 A: 落盘收尾预算 5→10s + 超时 is_alive 判定后 WARNING 明示未落盘; 否决候选 B
  (UI 线程补写 state 违反 state_file 唯一写者纪律)。守阵 +1(test_ui: 预算 10s / 超时 WARNING /
  退出码 0 / IPC 仍清理; GUI 栈不可实例化, object.__new__ + 直挂 handler)。**已入库 `9f73b6d8`**(W2 清偿 2/3)。
