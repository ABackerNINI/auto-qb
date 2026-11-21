# 26-11-20-backend-relocate-foreign-torrent — 整组移动外部旧路径种子零破坏处置 (IYUU 辅种冲突)

**Status:** Done
**Added:** 2026-11-20
**Updated:** 2026-11-21
**Summary:** 完结: 外部旧路径种子零破坏处置落地 (S1-S5 五批 T1-T5) —— 配置键 relocate.foreign_torrent (默认 true) + 侦测面 (added 差集 + 四时机全量兜底) + 场景 A 零破坏纳入 (spec 双写 journal 零写) + 收尾守卫 WAIT 分流与终态账闭包解析 + 场景 B 只通知 (WARNING + WebUI relocate 面板); 五批双评审 23 发现全修; 全量数字见基线切片; 计划 26-11-20-0434 已翻 Done
**Topics:** backend-relocate-foreign-torrent
**Refs:** memory-bank/plans/26-11-20-0434-plan-backend-relocate-foreign-torrent.html, memory-bank/issues/26-11-21-1326-feat-relocate-foreign-orphan-self-heal.html, memory-bank/issues/26-11-21-1326-docs-relocate-replay-note-drift.html, memory-bank/issues/26-11-21-1326-refactor-relocate-foreign-notified-cleanup.html, memory-bank/issues/26-11-21-1326-feat-relocate-foreign-view-stale-gate-off.html, memory-bank/testing/baselines/26-11-21-1341-backend-relocate-foreign-torrent.md

## 本篇只回答

本专项「整组移动 × 外部旧路径种子处置」做到哪了、怎么分步落地; 机制细节与逐条决策依据单点在计划 HTML (见 Refs), 本档案不复述。

## 原始请求

1. 整组移动功能与 IYUU 辅种冲突: IYUU (PT 界最常用辅种工具) 按本机已有种子到服务器匹配其它站相同种子, 匹配上就下载种子经 qB WEBUI 直接添加, 保存路径设为已有种子的路径; 可能选中整组移动的旧路径。
2. 新种子未被纳入收尾, 收尾阶段链接被删后种子找不到文件, 变「文件丢失」态; 初步想法: 删种+跳检重加指向新位置, 或自动纳入收尾。
3. 关注点: 新种子可能以跳检/非跳检方式添加, 添加后可能被用户规则跳检/完整校验等——需要安全且不冲突的方式。
4. grilling 然后出一个修改计划。

轮中补充指令 (逐条拍板见计划 §06): 场景 A 为主但 A/B/链式全管; 默认开启; 不绑定 IYUU 具体配置形态; 场景 B 只通知, 全程不做删种跳检重加; 全量校验绝不静默自动跑; 侦测不做周期兜底。

## 思考过程与决策

- 三轮只读子代理取证: ① relocate 全机制 (相位机/别名/收尾/删链门/让路面/state 账); ② 跳检相位机与外部种子发现 (store 全量镜像/事件管线 tracker 门/无来源标记/missing 只暂停告警无修复); ③ 「纳入收尾」可行性核查——结论条件可行: state job.hashes 与 spec.members 双面同步追加即全覆盖, journal 零写入; 四个实现坑 (核验悬挂放大/pending_tag 一次性/事件 tracker 门/终态账滚动 20 条)。
- grilling 四轮 14 问 → 拍板 D1-D14 (计划 §06); 两次用户改判: 默认开启 (原推荐关)、场景 B 只通知 (原方案删种重加+分片哈希门作废)。
- 侦测设计一轮修正: 「每 tick 全量扫」被否 (5000 种子场景形状错误) → 改为同步层原始 added 差集 + 时机触发全量兜底 (D12), 周期兜底被否 (D13)。
- 关键事实纠正 (D11): qB 对 skip_checking 添加也做基础文件检查 (用户实证), 「无数据假种」担忧撤回; 场景 B 到达呈 missingFiles。

## 实现计划

S1-S6 六步 (配置面/侦测面/纳入/收尾守卫+链式映射/通知面/收尾), 每步内容与验收判据单点在计划 §04; 本档案只留步号与状态。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 配置面 relocate.foreign_torrent + schema/validate | Done |
| S2 | 侦测面: added 差集消费 + 时机兜底全量扫 | Done |
| S3 | 场景 A 零破坏纳入 (state+spec 双写/暂停恢复/标签补打) | Done |
| S4 | 收尾守卫 (核验悬挂放宽) + 链式映射解析器 | Done |
| S5 | 场景 B 通知面 (日志 + WebUI relocate 面板) | Done |
| S6 | 全量绿 + 评审 + 文档回写 | Done |

## 进度日志

### R0 · 立档 (2026-11-20)

立项轮: 同步 7bd4e7f4 → 三轮只读子代理取证 → grilling: 轮1 Q1-Q7 → 轮2 Q8-Q11 (用户中途改判: 场景 B 只通知/全程无删种重加, Q8-Q10 作废) → 轮3 Q12-Q13 (改判: 全量校验绝不静默) → 落盘前侦测修正轮 Q14 (差集替代逐拍全量扫; 无周期兜底) → 全拍板 D1-D14 → 计划 26-11-20-0434 入库 (Open, S1-S6 待显式开工, --refs 双向补链本档案) → 本档案立档。零代码改动。

- 2026-11-20 04:48 立项轮: 三轮取证 + grilling 四轮 14 问拍板 D1-D14 (改判: 默认开启/场景B只通知/无周期兜底; 侦测改同步层 added 差集) + 计划 26-11-20-0434 入库 Open(S1-S6 待显式开工) + 档案立档; 零代码改动
- 2026-11-20 04:59 评审: 2 轮 (轮1 2 minor 引文过检当场修——建链时序句/D16 跨计划来源标注; 轮2 复评零发现, 修复确认未回退), 检 2/2 修 2 入池 0, 零 actionable 出口; pack 前置 sync 齐平 + ship.gate 预跑全绿

### R1 · 实施收口 (2026-11-21)

S1-S5 五批落地 (分支 feat/relocate-foreign-torrent, 基线 b3c4c3b7), S6 文档回写收口 (架构 hr-groups.md 增补 foreign 面小节 / 计划翻 Done + §10 R1 / 坑档新增 / README 与 conventions 核查):

- T1 (S1+S2a, df63f10a): 配置键 relocate.foreign_torrent (bool 默认 true, D5) 进 schema/models/validation/loaders + store.last_added_diff 每拍原始 first-seen 差集 (不过 tracker 门, 启动基线轮豁免, 断连重连只计断连期真新到); 评审 0 发现。
- T2 (S2b, 7b3e1baa): relocate_foreign.py 侦测面 —— 差集 O(新增) + 四时机全量兜底 (启动首轮与开关翻转共用闸门激活跳变信号 / 收尾窗 job 集合比对触发 arm / store.sync_epoch 重连锚) + 候选判定与清单比对复用单点 + notified 账 + 单拍预算 10 次比对 / 候选池 1000 有界 FIFO; 评审 5 发现 (1 major 3 minor 1 nit) 2 轮全修。
- T3 (S3, d8082739): 场景 A 零破坏纳入 —— job.hashes + 读-改-写 spec["members"] (hash_v1/v2 双查重, journal 零写) + pre-armed 暂停入 resume_hashes + pending_tag 增量补打; 核验/删链门豁免/缺文件扫描让路/跳检让路/删种拦截/absence_shrink 全真自动; 附带修 T2 引入的测试写红线目录缺陷 (autouse 夹具钉 data_dir=tmp_path, 坑档 pitfalls/testing/); 评审 5 发现 (1 blocker 1 minor 3 nit) 2 轮全修。
- T4 (S4, 787eb46a): 收尾守卫 —— _rewrite_cover_of 四分流 (recorded 既有语义 / spec=改写在途 WAIT / orphan WAIT+告警带人工出路 / spec 不可读保守 WAIT) + _verify_hang WAIT 支 + orphan 告警接线 _step_reconcile; _foreign_resolve_old_root 传递闭包 (done 直连边 + inherited 移交边, 深度上限 20, 首跳无边=None=R7 过期语义); 评审 4 发现 (2 minor 2 nit) 2 轮全修。
- T5 (S5, b3c4c3b7): 场景 B 只通知 —— WARNING (旧路径/闭包现位置/产出 job/手动指引) + _foreign_notify_expired (R7 降级, location 置空兼任呈现位与去重位) + 发布视图 foreign_notified_view + WebUI relocate 面板 foreign 行标注/浮窗专属块/抽屉迁移段/popovers + 降级文案单点 decorate.RELOCATE_FOREIGN_EXPIRED + e2e 双皮肤; 评审 9 发现 (2 major 4 minor 3 nit) 3 轮全修。
- 评审台账: 五批双评审合计 23 发现 (1 blocker / 3 major / 10 minor / 9 nit) 全部修复收口; 收口批: 接缝终审 1 minor (词表单点) + 文档批评审 2 (坑档类名/枚举补) 已修, 合计 26 (23+3); 另覆盖率闸门收敛 20 新测 (99.48%→99.60%); 引文过检台账 0/0、2/5 (3 条随修复失效不计数)、5/5、4/4、9/9。
- 全量测试: test.quick 6666 → 6732 passed 递进 (2 skipped 恒定, 0 failed); 权威数字以主会话 test.full 基线切片为准 (memory-bank/testing/baselines/), 本档案不手抄。

- 2026-11-21 13:48 实施轮收口: T1-T5 五批落地(df63f10a/7b3e1baa/d8082739/787eb46a/b3c4c3b7: 配置键+store差集/侦测面/场景A纳入/收尾守卫+链式闭包/场景B通知面) + 收口批(接缝终审词表修复/覆盖率99.48%→99.60%收敛20测/S6文档回写+4issue入池/残留清理); 分批评审 26 发现全修零 actionable 出口; test.full 6748P/6S 覆盖率闸门过见基线切片 26-11-21-1341
