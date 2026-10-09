# 已实现 · 客户端 / 主循环 / 状态 / 内置功能

> 摘要: 后端主干与内置功能的落地记录 —— 客户端 / 主循环 / 数据层 / 任务队列 / 托盘 / 通知 / 标签 / HR / 分组。
> 触发: 做过没有, 主循环, 数据层, 任务队列, 托盘, 通知, 标签, HR, 分组, 单实例锁

## 已实现 (✅, 有单测覆盖)

- **🆕 qB 口径流量 v4 格式换代: 块头基线 delta + 按落盘切块 + 自然推算结算 (2026-10-05~06, 计划
  [plans/26-10-05-2200](../plans/26-10-05-2200-plan-qb-traffic-v4-delta.html) 全段, 报告
  [26-10-05-1946](../reports/26-10-05-1946-report-qb-traffic-v4-delta.html) Done)**:
  v3 天文件逐行绝对 totals 的行宽随 all-time 计数无界增长, 换代打包四件事: 块头 B 行携带
  totals 基线(5 列; 块首 n 游程前缀拆 3 列无基线块, 块内 r/z 判坏行) + r/z 行存相对块基线的
  delta(内存结构恒绝对, delta 只存在于线格式 —— parse 以基线 cumsum 复原、format 减法序列化,
  读侧/agg/catch-up/WebUI 语义零改动) + 关块状态机「flush ∧ 块内有 r 行才关, 空闲块跨 flush
  开放」(空闲段盘上恰 1 条长 z 行, 空闲期写盘归零、解析缓存全天有效; ZRUN 保险闸退役为天级;
  计数器重置强制关块重立基线) + 覆盖结算判定函数单点 `v4_block_gap_continuous`(gap ≤ interval +
  DRIFT_TOL → 连续, 在线 _agg_feed 与离线 _agg_credit_day_file 两路同源复用)。v3 格式函数与旧写
  路径随翻转退役, 全仓 V3→V4 符号代际改名; 目录 `qb-traffic-v4/` 全新落点, 旧 v3 原样留存不读
  不迁移(删留决定权在用户)。B1 纯函数区并存(6a98c504, 2628 passed + 4 skipped / 99% / 25.7s) →
  B2 原子翻转(B2-1..B2-3 合并前 squash, 2632 passed + 4 skipped / 98.50% / 28.1s, 机检零残留) →
  B3 收尾(配置配比口径 N2 入 models/loaders 注释; v3 计划 §02.1 条款级取代; dry-run 真机零 ERROR)。
  字节对照三档全落报告 §07 推演区间: 满速活跃天 -12.5% / 低速 -22.3% / 空闲天 -98.9%(基线
  [26-10-06-0132](../testing/baselines/26-10-06-0132-qb-traffic-v4-delta-b3.md), test.full 2632
  passed + 4 skipped / 98% / 27.8s)。格式契约单点 = traffic_store.py 模块 docstring。档案
  [tasks/26-10-05-backend-qb-traffic-v4-delta](../tasks/26-10-05-backend-qb-traffic-v4-delta.md)。

- **recheck 轮询生效确认整体重设计: 证据门控判定 (2026-10-04, 计划
  [plans/26-10-04-1824](../plans/26-10-04-1824-plan-ops-recheck-effect-confirmation.html) 全段, issue
  [26-10-03-1140](../issues/26-10-03-1140-bug-ops-recheck-false-success.html) Done)**:
  recheck 轮询原成功分支 `if rec.progress >= 1.0` 直接对陈旧快照下结论 —— 已完成种子提交后首跳
  (入队即到期)读到 qB 异步应用前旧快照误判「校验成功」(生产事故 2026-10-03: 4 条 40GB 同毫秒假成功)。
  重设计四件: ①`rules/checking_meta.py` 判定纯函数 `poll_verdict` + 证据谓词 `is_piece_checking`
  ({checkingDL, checkingUP}, 排除 qB 启动期 checkingResumeData 伪证据) —— SUCCESS 仅 seen_checking
  可达, 「无证据成功」签名层面不可表达, 160 组合穷举钉死; ②ops_mod poll 闭包重构为证据门控状态机
  (证据闩收窄 / 未见证据 progress 回落提前判「校验未通过」/ START_TIMEOUT 判败前一次性仲裁直查
  D5 ≤1 次, 超时日志报真实时长); ③R1 提交点实时复核 (快照→冷却→live 单 hash 直查→登记→发送,
  跳检 R2 同款: live 空 skip / live checking 拒绝 / 异常 fail-closed), baseline_progress 改取 live
  真值; ④模式固化: 坑档 [pitfalls/backend/effect-confirmation.md](../pitfalls/backend/effect-confirmation.md)
  + ops_mod 模块头判定纪律 (新异步操作接入 = 新 source, 判定必须走证据门控)。等价性红线不破:
  周期观测纯快照读零 API, 直查只在决定性时刻。新增用例 15 条 (A3/B3/C3/D4/E2) + 既有适配 27 处;
  test.full 2530 passed + 4 skipped / 99% (基线
  [26-10-04-2256](../testing/baselines/26-10-04-2256-ops-recheck-effect-confirmation.md))。
  五棒串行子智能体实施 (S1-S4, 编排者核验提交), 档案
  [tasks/26-10-04-backend-ops-recheck-effect-confirmation](../tasks/26-10-04-backend-ops-recheck-effect-confirmation.md)。

- **跨组文件交叉检测与紧急处置 (2026-10-04, 计划
  [plans/26-10-04-0107](../plans/26-10-04-0107-plan-cross-group-file-conflict.html) S0-S5 全段, issue
  [26-09-22-2221](../issues/26-09-22-2221-feat-cross-group-file-conflict.html) Done)**:
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
  4 skipped / 99% / 36.16s(基线 [26-10-04-0412](../testing/baselines/26-10-04-0412-cross-group-conflict-detection.md));
  真机走查留待用户。档案 [tasks/26-10-04-backend-cross-group-conflict](../tasks/26-10-04-backend-cross-group-conflict.md)

- **热重载 L2 重建后种子级任务补建: RulesModule 订阅 full_round (2026-10-04, issue
  [26-10-01-2147](../issues/26-10-01-2147-bug-webui-hotreload-newsite-maintenance.html) 认领修复)**:
  `rebuild_runtime` 换新 TaskQueue 后只有全局任务自注册重入队, 种子级任务(内置 maintenance + interval
  规则任务)随旧队列丢弃且唯一触发源 torrents_added 相位对存量记录不触发(`_apply` 只对 prev 没有的
  hash 判 added)⇒ 所有 L2 级热重载后存量种子维护面停摆直到重启。修法三件: ①`TaskQueue.has_task(kind,
  name, hash)` 查重助手(`has_named` 委托归一); ②RulesModule 订阅 `full_round`(装配序在 TrackerModule
  重匹配之后), conf 已就位且任务面缺失的存量记录补建, conf 仍 None(未匹配站点)留待下轮; ③
  `_create_torrent_tasks` 入口幂等(maintenance 任务在队即整面跳过, 首轮全量轮「补建先于 added 管线」
  双入口互斥) + `immediate=True`(补建任务立即到期, 下一 tick 兑现一次维护消费 `external_tag_changes`
  —— on_change「首轮全量收敛」契约成立)。红验先行 3 用例(test_modules_p5.py)。坑档
  [pitfalls/backend/hot-reload-stale-bindings-derived-views.md](../pitfalls/backend/hot-reload-stale-bindings-derived-views.md);
  档案 [tasks/26-10-04-backend-hotreload-torrent-task-restore](../tasks/26-10-04-backend-hotreload-torrent-task-restore.md)

- **HR 热重载存量绑定陈旧修复: `TrackerModule.apply` 重绑存量记录 (2026-10-03, 计划
  [plans/26-10-03-0436](../plans/26-10-03-0436-plan-hr-hotreload-webui-stale-display.html) P1, `2a5d07a2`)**:
  热重载只换 `manager.config` 对象, 存量 `rec.tracker_conf` 仍指旧 `TrackerConfig`(其 `hr_check` 派生视图为
  None; 重绑两条旧路 —— L2 判据只比绑定三元组 / full_round 只补 None —— 都不覆盖配置值类变更) ⇒ HR 判定 /
  `HrRuntime._anchors()` 锚点收集 / `hr` 规则段三个消费面全瘫, WebUI 恒显「本地·达标」。
  修法 = 认领模块 `apply(old,new)`: `old.trackers != new.trackers`(整段按值比较)即遍历
  `store.by_hash` 中 `tracker_conf is not None` 的记录执行 `rec.tracker_conf = self.match(rec)`
  (回执 `tracker:rebound N`), 相等短路零动作, `ctx.api.client is None` 防御跳过不抛 ——
  一处修复覆盖三个消费面, 不动 L2 结构判据。守阵 test_tracker.py 三用例(存量重绑+回执 / client=None /
  相等短路, 红验过)。坑档 [pitfalls/backend/hot-reload-stale-bindings-derived-views.md](../pitfalls/backend/hot-reload-stale-bindings-derived-views.md);
  档案 [tasks/26-10-03-backend-hr-hotreload-stale-display](../tasks/26-10-03-backend-hr-hotreload-stale-display.md)

- **缺文件扫描过渡态容忍: .!qB 孪生存在不判缺失 (2026-10-01, 清偿 issue
  [26-09-21-0219-bug-qb-move-dot-qb-suffix-recheck](../issues/26-09-21-0219-bug-qb-move-dot-qb-suffix-recheck.html),
  按计划 [26-09-22-2038](../plans/26-09-22-2038-qb-move-dot-qb-suffix-fix-plan.html) 修法 1 主体)**:
  qB 移动种子搬运窗口内文件被临时改名 .!qB, 缺文件扫描把过渡态读成永久缺失 ⇒ 误停整组 + MISSING 标签。
  修法 = grouping_mod.py 汇聚点单点容忍(.!qB 孪生存在不判缺失) + 连续 3 次上限兜底残留; 计数为会话级
  内存态(store.transitional_missing_skips)**不落盘**; 孪生探测经 fa.exists() 三态语义适配文件访问层
  (docker 逻辑路径直探 syscall 恒 False, 否则容忍静默失效)。测试 +8(grouping 5 / utils 2 / file_access 1,
  红验 5 failed → 落码 7 passed); 计划 doc-status 完档 Done。**已入库 `c353e899`**(W2 清偿 3/3);
  档案 [tasks/26-09-22-backend-qb-move-missing-tolerance.md](../tasks/26-09-22-backend-qb-move-missing-tolerance.md)。

- **托盘退出 join 超时 5s→10s + 超时 WARNING (2026-10-01, 清偿 issue
  [26-09-21-1347-bug-tray-join-timeout-abandons-save](../issues/26-09-21-1347-bug-tray-join-timeout-abandons-save.html))**:
  主循环 daemon 线程 join(5s) 超时即放弃 ⇒ 优雅退出撞上长任务时本次运行期 state 不落盘(黄金法则 3 收口)。
  修法 = issue 候选 A: 落盘收尾预算 5→10s + 超时 is_alive 判定后 WARNING 明示未落盘; 否决候选 B
  (UI 线程补写 state 违反 state_file 唯一写者纪律)。守阵 +1(test_ui: 预算 10s / 超时 WARNING /
  退出码 0 / IPC 仍清理; GUI 栈不可实例化, object.__new__ + 直挂 handler)。**已入库 `9f73b6d8`**(W2 清偿 2/3)。

- **HR 在线核实 v3 波次模型重建 (2026-09-29, 计划 26-09-28-1932 M1–M5)**: 判定=四行判定表
  (考察中管束/终态放行/无证据本地兜底硬编码, 12 格矩阵单测); 取数=单波型波次引擎(全量对账 +
  A/B/C 轮流 + 三停翻条件 + 档位级截断有效性 + 失踪观察期 + 流转守恒/骤降/零行戳三道防伪 +
  身份登记一次下载); 频控=单模型三键(熔断/停用/退避全删); 配置 40→14 键(config v2→v3 +
  hr_site v1→v2 迁移, 档案 listing 字段); `--hr-resume` 删 / `--hr-confirm-empty` 增(含 WebUI
  按钮)。HR 测试按新模型重写约 200 条; 全量 1743 passed + 3 skipped; 基线切片 26-09-29;
  档案 [tasks/26-09-22-backend-partial-hr-verify.md](../tasks/26-09-22-backend-partial-hr-verify.md)。
  **追记(2026-09-29)**: 粗配判据收紧(剔技术噪声整词后再算 ≥K 重合, K 仍 12) —— 真实数据 159 → 31 对、
  新增 0; 坑档 [pitfalls/backend/fuzzy-match-noise.md](../pitfalls/backend/fuzzy-match-noise.md)。

- **HR 状态模型重新梳理 + D 档已免罪来源单列 (2026-09-26, 计划 v3.4)**: 用户指令钉死「优先级
  在线信息.考察中 > 在线信息.已达标 > 在线信息.未达标 > 本地信息(= v3.0 已落码), 最终态
  已达标 | 未达标 | 已免罪, 三个状态都代表结束状态」—— 终态语义收口进主计划 §9 新「状态模型」节
  (A 考察中 = 唯一进行中; 终态展示落点: safe 绿可删 / failed 红考核未通过 / 安全放行)。修复展示缺口:
  WebUI 曾把 D 档已免罪折进「在线·已核实」(与「完整刷新未列出」缺席证据共用 `SRC_SITE_RELEASED`) ⇒
  新增 `SRC_SITE_EXEMPT`「在线·已免罪」, `HrResolution.released_src` / `HrJudgement.verified_source`
  透传 D 档放行出处, `safety_display` 分流(缺席式放行原样 site_released); 前端 `shared/hr.js`
  两张映射表 +1 键(徽标「在线」/ 来源桶「在线核实」, 无新 CSS)。测试 +2 + test_web 字段级 D 档
  断言块, 守阵 SRC_* 常量 8→9, ★红验 3 条全红; 全量 **1637 passed + 1 skipped**(TOTAL 92%);
  计划 [plans/26-09-22-2204-partial-hr-site-verify-plan.html](../plans/26-09-22-2204-partial-hr-site-verify-plan.html)
  §9/§14 v3.4; 档案 [tasks/26-09-22-backend-partial-hr-verify.md](../tasks/26-09-22-backend-partial-hr-verify.md);
  **已入库 `a497fba`**(合并远端 4 笔[docker 部署/种子级标签分类编辑/分享率列对齐]后经合并提交 `d72a538` 推送,
  合并树重测 1641 collected: 1640 passed + 1 skipped / TOTAL 92%)
- **浏览器扩展运行日志(分级 + 环形上限 + 选项页④区) (2026-09-25)**: `extensions/hr-fetch-proxy` 加日志 ——
  条数 10–10000 可设(默认 1000, 环形丢最旧), 四级 debug/info/warn/error(记录阈值默认 info + 选项页分级过滤),
  明细含毫秒时间 / 收到的命令(kind·id·站点) / 请求类型(拉清单/页面直取/页面渲染/种子下载)与 HTTP 结果 /
  耗时 / 字节数 / 回传后端响应体快照 / 扩展侧硬上限拒发。MV3 SW 随时被回收 ⇒ 唯一事实源
  `chrome.storage.local`(内存环形缓冲 + 防抖 300ms 整份写回; 外部清空经 onChanged 采纳, 免得被内存缓冲盖回);
  选项页④区设置即时生效 + 清空走 `clear-logs` 协议 + 渲染 esc 转义 + 限渲染 3000 行。守阵真跑当场抓到
  flush 链**自引用死锁**(首刷即死锁且无报错, 已修并入坑 `pitfalls/web-ui/extension-bridge.md`); 顺带修选项页
  轮询周期文案漂移(5 分钟→1 分钟)+ 文案↔`POLL_MINUTES` 防漂守阵。新增守阵 3 条, 基线 1576 →
  **1579 collected**(TOTAL 91% 不变); 档案 [tasks/26-09-25-webui-ext-hr-logging.md](../tasks/26-09-25-webui-ext-hr-logging.md)
- **HR 在线核实(部分种子 HR 站点) —— M1 核心管道 + M2 取数通道 + 告警分档/现状报告 (2026-09-24)**: 站点侧核实「哪些种子受 HR 管束」并给出**三态**判定(受管束 / 已核实不受管束 / 未核实)。M1 = `src/auto_qb/hr/` 离线管道(bencode 取 info **原始字节切片**算 infohash · NexusPHP `myhr.php` 解析 · 站点分文件 + **每站点一把锁** · 频控「只向上抖动 + 两级配额 + 熔断 + 时间窗」 · 三态判定与不可变视图 · 刷新管道 · `--hr-once` 只读走查) + 配置全链路(两条配置期 fail-fast: `mode != off` 必配 `hr` 段 / `hr_page_scopes` 必含 A+B+C); M2 = **取数通道**: 后端零 cookie、零直连站点 —— 本地端点(`127.0.0.1` + token + origin/URL 白名单, 只入队) + **取数线程**(按 `poll_interval` 自唤醒、不随主循环 tick、持锁抓取、不碰 state_file/队列/store) + 只读视图**原子发布**(主循环零等待, 只在数据变化时抬 `revision`) + MV3 扩展 `extensions/hr-fetch-proxy/`(哑取数器: 页面**默认无界面直取**、必要时离屏 popup 窗口渲染 / service worker 取 .torrent, 不碰 cookie API); **告警分档与现状可见性**(M2 上线后按用户实报补): 结果对象带 `reason_kind`(budget = 被自己频控拦下 / parse = 页面字段翻页问题), 日志按此分级 —— 节流态只记一条 INFO(按被拦根因去重), 页面改版与取数失败才 WARNING; 新增 `--hr-status [--hr-status-rows N]` 只读现状报告; 生命周期/节流只记 INFO, 同一事件只由产生处告警一次(`alerted`); 站点数据文件两层保护(`.bak` + `.bad-<ts>`); 只读口径在**成功与失败两条写盘分支**上都拦得住。**M3 判定联动 (2026-09-25)**: 三态判定接进 `TorrentRecord`(记录持 `QbManager.hr` 门面稳定引用 `hr_link`, 读取时现算), `check_hr_condition` / `check_hr_satisfied` **站点侧优先、站点没给再回落本地** ⇒ 打标 / WebUI 视图 / `hr` 规则条件 / `tor.hr_*` 表达式四个消费点一行未动; `mode: all` 升为「站点侧驱动 + 未核实恒受管束」; WebUI 透出三态/依据/达标来源供对账; **零静默变更**两道门。余 M4(多站点)未落地 —— 明细见 [tasks/26-09-22-backend-partial-hr-verify.md](../tasks/26-09-22-backend-partial-hr-verify.md)。
- **state.json 损坏静默清空 / .bak 从不用于恢复 · issue 26-09-21-1347 (2026-09-22, 已置 `Fixed`, 已入库 `e11df80`)**: `_load_state` 的 `except (FileNotFoundError, json.JSONDecodeError): pass` 把「文件损坏」与「首启」同等对待 ⇒ 损坏时静默返回 `{}`(exec_history / skip_check_day / recheck_fails / 上传基线全丢且无线索), 而 `atomic_write(keep_backup=True)` 每次写盘前复制的 `state.json.bak` **全库零读取方**。**修法 = 拆三态 + 回退 + 自愈**: ①新增 `_read_state_file` 返回 `dict`(可用) / `None`(不存在=首启, 静默) / 哨兵 `_CORRUPT`(存在但非法 JSON、非 dict、非法 UTF-8; `OSError` 故意不吞 —— 那是环境问题不是内容问题) ②见 `_CORRUPT` 记 WARNING(损坏文件**原样保留不删**)并回退 `<state_file>.bak`, 读到合法 dict 即用以 INFO 记「用了备份」; 备份也不可用才 `{}` 并再告警说清后果 ③**自愈写回** `_write_back_recovered` —— 把恢复出的内容写回主文件且**刻意不带 `keep_backup`**, 否则下次 `save_state` 会把损坏内容复制成新的 `.bak`, 把唯一一份好备份盖掉(等于这次恢复白做) ④备份后缀单点化 `utils.BACKUP_SUFFIX`(写侧 `atomic_write` 与读侧共用, 防命名漂移)。**守阵 4 条**(回退+自愈 / 无备份时两条 WARNING / 首启不得告警 / 自愈写回失败只告警不抛)+ `test_utils` 备份路径断言改按常量; 红验: 运行期把 `_load_state` 打回旧实现 ⇒ 新守阵必红。全量 **1152 → 1160 passed + 1 skipped**。附带发现(报告里标「可选低优先」的孤儿 `state.json.*.tmp` 启动清理)
**也已一并修完**: 新增 `_cleanup_orphan_tmp`, 挂在 `QbManager.__init__` **持锁之后**(没锁说明有别的实例在写,
删它的临时文件会让那次写盘 `os.replace` 失败 ⇒ 状态白丢一次更新), 只认 `<state_file>.<随机>.tmp` 这一个形状
(`.bak` 是恢复凭据、别人的 `*.tmp` 与空随机段一概不碰), 只读模式 `no_lock=True` 不做这次磁盘副作用; 守阵 4 条
含一条**接线守阵**(源码里必须出现在 `acquire()` 之后且落在 `if not no_lock` 内)+ 幂等断言。
报告 [issues/26-09-21-1347-bug-state-load-corrupt-silent-reset.html](../issues/26-09-21-1347-bug-state-load-corrupt-silent-reset.html)。
- 跳检备份时机修复 · issue 26-09-21-1347 (2026-09-22, 已置 `Fixed`): `.torrent` 备份原先只在**重加的两条失败分支**上落盘, 而删除是跳检链上第一个不可逆步骤 ⇒ 「删除已生效 → 重加未被 qB 接受」这个约 0.5~5.5s 的缝隙内崩溃/强杀, 种子从客户端消失、`data` 只在内存、state 无在途标记, 重启后无任何恢复凭据(需人工回站点重下 .torrent)。**修法 = 只挪调用时机**: 阶段 2 导出成功后立刻走现成的 `_backup_torrent`(落盘 + 元数据 + 立即 `save_state`), 并新增配对的 `_clear_backup` —— 重加确认成功后清理(文件 + 元数据)、删除未生效(种子仍在)也清理, 只有重加失败/崩溃才留下备份; 备份写不进去则**不删除**直接 fail(无损失)。**守阵 3 条**: ①在客户端的 `torrents_delete` 里快照备份文件是否存在(只查最终结果无法区分"之前写的"还是"之后补的") ②删除未生效 → 备份必须被清掉 ③备份失败 → 不得发出 delete。⚠ 顺带把 `test_checking.py::make_mgr` 改成**未指定 state_file 时自动发一份临时 state 文件** —— 跳检现在每次都真实落盘/删除备份, 留空会写到 CWD=仓库根(污染仓库 + 被 `tests/sidefx.py` 判成越界删除)。全量 **1142 → 1145 passed**; 知识库: `rule-system.md` / `config-reference.md` / `systemPatterns.md` / `docs/configuration.md` 已回写"备份先于删除"。报告 [issues/26-09-21-1347-bug-skip-checking-readd-no-backup-window.html](../issues/26-09-21-1347-bug-skip-checking-readd-no-backup-window.html)。
- 导出 .torrent 中文名 500 已修 (2026-09-17, 已入库 `4de0953`): `/api/torrents/{hash}/export` 把种子名直拼进 `Content-Disposition`, 而 HTTP 头只能 latin-1 ⇒ 中文名触发 `UnicodeEncodeError` 500。修法: 新增 `web.content_disposition(filename, fallback, ext)` 双段头(`filename=` ASCII 回退 + `filename*=UTF-8''<百分号编码>`)并清洗控制字符; 测试 `test_content_disposition_encoding` + 导出端点非 ASCII 用例。
- TorrentRecord 全字段缓存 (2026-09-15): 快照 21 → 70 字段(必需 21 + 重加升格 6 + 可选扩展 43, 字段定稿参照用户提供的真机 TorrentDictionary 样例 + 真机冒烟补 4 字段), 为 WebUI 后续功能供数; D1-D5 决策见 [memory-bank/plans/26-09-15-1302-record-full-fields-plan.html](../plans/26-09-15-1302-record-full-fields-plan.html): slots 全量声明(_raw 降为前向兼容兜底)/RE_ADD_FIELDS 升格进快照(变化开始计入变化集)/新字段全可选(默认值取 qB 哨兵 -1/-2/8640000, REQUIRED 校验面不变)/缓存≠展示(新字段不进 _VIEW_FIELDS, 视图重建成本零变化, 测试锁死)/哨兵原样透传; 新增 `to_dict()` 全字段导出; 真机只读冒烟(119 种子)响应字段全声明 _raw 无残留; 测试 +9 净 +7, 基线 879 passed; 视图/规则/HR/分组消费字段全在旧集合内零行为变化
- 标签/分类管理: 站点标签加/删、相似标签清理、`delete_tags`/`delete_tags_if_has_no_torrents` 全局清理、集数标签
- HR 管理: 触发标签/分类 + satisfied 标签/分类, 站点覆盖全局
- 辅种分组: 增量归组、大小一致性、缺文件事件驱动扫描 (删除/上传转暂停/路径变化)、下载冲突检查
- 托盘常驻 UI (2026-09-12, --tray): `ui.py` —— CustomTkinter 深色窗口(状态卡片/最近日志/暂停恢复/通知热切换/开机自启)+ pystray 托盘(6 项菜单, 勾选态实时); 运行时暂停/恢复 = pause_event 完全旁观, 恢复后增量 diff 补上; 双开唤起 = 单实例锁 + localhost IPC(ui.port, 第二实例静默退出 0); 托管模式主循环移入后台线程(单一写线程约束保持), 首连失败重试常驻; GUI 栈仅 tray 分支加载; 通知开关支持从未配置状态热挂载(setup_notify force, 会话级); toast 点击激活唤起窗口(launch_arguments 经 AUMID 快捷方式 Arguments); 窗口图标 CTk iconbitmap 防 CTk 默认覆盖(assets/icon.ico); 打开日志目录前绝对化路径并确保目录存在, 托盘事件单点失败不中断 UI 轮询链; 新依赖 pystray/Pillow/customtkinter
- 主动通知 (2026-09-12): `notify.py` 零第三方依赖 —— NotifyHandler 挂 `auto_qb` logger 复用日志规范, PlatformChannel 按平台分派(win32=PowerShell WinRT toast / linux=notify-send / darwin=osascript), quiet_hours 免打扰(与 date_time 共用 utils.time_in_range) + 每小时上限 + 同键去重窗(内存态); CLI 致命退出补发 notify_fatal; dry-run 不挂载; toast 来源显示 "AutoQB" —— 首次运行幂等注册开始菜单快捷方式 AutoQB.lnk(%APPDATA% Programs 目录, 隐式 AppUserModelID), 注册失败回退 PowerShell 来源
- 任务队列: 单 heapq 队列 + `add_task(keep_progress=...)` 断点语义 + check 轮询在途去重 (12f3b46 重构完成)
- 数据层: TorrentStore 快照+惰性缓存+分组索引; QbApi Facade写后同步
- YAML 导出 (`--export-yaml`, `--only-missing`), qB 5.0 API 适配
- 单实例锁 (2026-09-05): 基于第三方 `filelock`, 锁文件 `<state_file 去扩展名>.lock` + 伴生 `.meta.json`; 仅正常 `run()` 模式持锁, `--export-yaml` 等只读模式通过 `no_lock=True` 跳过; 失败抛 `SingleInstanceLockError(AutoQbError)`, CLI 单点捕获 AutoQbError 体系干净退出 (退出码 1, stderr 无堆栈); 陈旧锁不接管 (OS 句柄随进程退出自动释放, 必要时手动删除)
- **🆕 state.json 损坏静默清空 + .bak 从不用于恢复 —— 已修并验证, 已入库 `e11df80`(见本文件顶部「最后更新」首条)**: issue
  [26-09-21-1347-bug-state-load-corrupt-silent-reset.html](../issues/26-09-21-1347-bug-state-load-corrupt-silent-reset.html)
  已置 `Fixed`(索引已重建)。**附带发现(孤儿 `state.json.*.tmp` 启动清理)也已一并修完** —— 新增
  `_cleanup_orphan_tmp()`, 挂在 `QbManager.__init__` **持锁之后**(没锁说明有别的实例在写, 删它的临时文件
  会让那次 `os.replace` 失败 ⇒ 状态白丢一次更新), 只认 `<state_file>.<随机>.tmp` 这一个形状(`.bak` 是恢复
  凭据、别人的 `*.tmp` 与空随机段一概不碰), `no_lock=True` 的只读模式不调用; 守阵 4 条(含**接线守阵**:
  源码里必须出现在 `acquire()` 之后且落在 `if not no_lock` 内 + 幂等断言)。全量 **1160 passed + 1 skipped**。
  ✅ **本批改动(源码 3 文件 + 测试 1 文件 + 知识库 5 文件)已入库 `f261de7`**(Gitee + GitHub 均推上)。
  🧪 端到端复核(真实 `QbManager(..., no_lock=False)` 构造路径): 损坏 → 内存 state == `.bak` / 主文件被自愈
  写回 / 孤儿 tmp 被清理 / `.bak` 未被损坏内容盖掉 —— 四件事全成立(脚本在 `H:/Temp/e2e_state_recovery_check.py`,
  未进仓库)。

## HR 故障归属分层 (2026-10-09, 计划 26-10-09-0821)

用户实报: 关浏览器过夜, WebUI 错误历史里出现 4 条 `[HR 页面改版] 页面取数失败(等待浏览器扩展取数超时 180s)`
与 2 条 `[HR 通道静默]`。根因是**分类模型上的一个洞**: 「等扩展回传超时」在 `hr/fetcher.py` 抛的是**裸的**
`HrFetchError`, 于是掉进 service 的 `except HrFetchError` ⇒ 被当「页面取数失败」: 套 `[HR 页面改版]` 标签、
写 `wave.notes`、推进 `fail_streak`(连关几晚就升成「疑似改版」ERROR)。即**环境态被伪装成站点结论**。

- **归位**: 新增 `HrChannelTimeout(HrChannelUnavailable)` 并于超时处抛出 ⇒ 落进既有的通道层出口
  (`ACTION_NO_CHANNEL`、`_warn_no_channel` 每站一次), 上面三处污染一并消失。
- **层贯穿出口**: `events.DOMAINS`(事件→层, 单点)+ 新增 `hr/log.py`(生产点挂 `hr_domain`/`hr_silent`)
  + `infra/logging.is_record_suppressed`; 出口 `WebErrLogHandler` / `NotifyHandler` 按「层 × 档位」收放 ——
  **通道层的静默子类只进后端 log**, 不进前端错误历史、不弹通知。
- **可分辨边界**: `ChannelStatus` 增「被拒接触」面(401/403; 不污染 `last_contact_ts`); 401 日志由每分钟 ERROR
  改为状态变化 + 6h 的 WARNING; 通道静默文案按 `rejected` / `web_active` / `none` 三档分叉, 不再用一句问句让用户猜。
- **WebUI 活跃信号**: 判据取「WebUI 是否活跃」单信号(不判断同机/同源) —— 活跃 ⇒ 可见告警, 不活跃 ⇒ 静默。
- 基线: [testing/baselines/26-10-09-0931-hr-fault-domain.md](../testing/baselines/26-10-09-0931-hr-fault-domain.md)(2836 passed)。
