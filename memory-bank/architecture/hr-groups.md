# HR 合规与辅种分组

> 摘要: HR 达标判定状态机(判定单点在 TorrentRecord)与打标分流、HR 在线核实运行时、跳检对 HR 的代价边界、辅种分组归组不变量与缺文件/冲突处置、整组迁移边界、外部旧路径种子处置(foreign 面)。
> 触发: HR, H&R, 达标, 放行, 管束, 考察中, 在线核实, hr_check, 打标, 跳检保护, 辅种分组, 分组, 缺文件, MISSING, 下载冲突, 迁移, relocate, 外部旧路径种子, foreign, IYUU, 辅种冲突

## HR 判定状态机 (单点 `torrents/record.py`)

判定入口族, 全部先过公共守卫(站点未配 hr 或命中排除表恒短路):

- `hr_judgement()`: 站点侧三态判定 —— 只有站点配了 `hr_check` 且总开关开才走站点侧语义(**零静默变更**: 未接入的站点行为一字不变); 未接入/被排除返回 None → 本地字段逻辑。
- `hr_managed()`: **管束语义单点**(打标分流/规则条件/表达式 `hr_condition_met` 的管理判据都消费它): 考察中恒管束(网站绝对权威, 含超额被动命中); 终态放行恒不管束(**本地未做够也不许推翻** —— 故不能写成 not satisfied); 无站点证据按本地判据兜底(未达标即管束, 含 downloaded=0 的转移种)。
- `check_hr_satisfied()`: 义务已了单点 —— 站点结论优先且**命中即停**(本地值不得越级推翻站点清单结论); 免罪/未列出/无证据才回落本地时长(要求+额外)或分享率; **无触发门**: 达标只看做种事实, 转移种做种满也算达标。
- `check_hr_condition()`: 本机下载触发, **纯展示辅助**(前端区分「本机下载 vs 疑似辅种」), 管理语义不得消费 —— 「不触发」不代表无义务。

判定表(站点数据是权威, 计划 plans/26-09-28-1932-plan-hr-verify-rebuild.html): 行 1 命中考察中 → 管束(绝对权威); 行 2/3 终态档与移出未列出 → 放行(**一经签发永续有效**, 反转必然伴随重新下载); 行 4 无有效站点证据 → 本地判据兜底(达标放行/未达标管束, 硬编码无配置)。「本机下载触发」与「管束」语义分离(plans/26-09-30-0559-plan-hr-trigger-semantics.html): 触发只是展示口径, 管束只看义务是否了结。**排除表优先**(hr.exclude_tags/exclude_categories, plans/26-09-28-1805-plan-hr-exclude-tag-category.html): 命中即排除, 压过一切管束; 在 qB 加/删排除标签下一轮即生效, 已打标记残留不回撤。

## HR 触发落地: 打标分流 (core/modules/maintenance_mod.py)

`add_hr_tag_or_category` 门禁三段: 放行短路(终态结论不受本地做种影响) → 超额跳过(做种 ≥ 3× 基准, 义务早已了结; 被动命中考察中仍打 HR 标签) → satisfied 分流(达标打 satisfied 标签/分类, 否则打 HR 标签/分类)。**全量纳入**: 达标前含 downloaded=0 的转移种/纯辅种都打 HR 标签。标签文本经 `replace_vars` 展开 `${required_seeding_time}`, WebUI 视图透出的展示字段与真写入 qB 的标签逐字相等。

## HR 在线核实 (hr/ 包, 波次引擎 v3)

浏览器扩展通道 + 取数线程抓站点清单, 判定账号在各站点的 H&R 状态:

- **账号级状态不进 state_file**(多实例/多客户端是常态): 一站点一个 JSON 文件 + 一把锁, 取数线程**持锁完成「读→判效→抓→写→释放」全程** —— 即使有 bug 也不可能两实例同抓同写; 拿不到锁直接等下一轮(不排队不轰炸)。
- **单波型**: 每波都从第 1 页开始、以覆盖全部对象为目标并**自证覆盖**(结论只来自本波抓到的页面) —— 清单是动的, 「断点续抓/凭上波跳过」在赌覆盖假设成立。波的大小随对账与转终态单调变浅。
- **档位独立**: 某档失败只影响该档新证据(截断式: 失效点之前数据全部有效), 处置 = 档位截断 + 下周期自然重试, **无熔断/停用/退避**; 证据无时效只有真伪。
- 模型主键 = (站点, tid), infohash 下载后回填; 三种运行口径: 正常 / dry-run(**零请求也零写入**) / `hr.once` 只读走查。
- **能力即角色**: `hr_check.enabled` 即建取数线程, 再满足 `channel.enabled` 才起端点 —— 没装扩展的实例只读共享站点文件照样发布视图(多实例分工: 谁有浏览器谁抓; 跨机实例经通道同样可驱动)。
- **发现通道按 clone 物理隔离**(plans/26-11-10-0515, 起 issue 26-11-03-0315): 登记簿每 clone 一份 `<sha1(data_dir)[:12]>.json`(entry_id 同源, runtime 算), 发现响应只含本 clone 实例; 旧用户级 `instances.json` 遗留不读不删不迁移。发现候选口 18788-18795 连号 8(`DISCOVERY_CANDIDATES`), 扩展并行探测; 展示名走 `hr_check.channel.name`(空回落 data_dir 目录名); 扩展六态显式裁决(auto/selected/ambiguous/needsSelection/selectedMissing/noAnswer, 快照键 `servedVerdict` + 选择集 `activeNames`, 三条外呼路径只打服务集 —— 手动添加恒在)。测试带 28788: 桩默认与 dev.run 注入(`--hr-discovery-port`)一律测试带, 显式豁免 `--hr-prod-discovery`; 生产默认 18788 一字不动。
- 事件四类按层单点(login 登录失效 / parse 页面改版 / silence 通道静默 / channel 通道不可用; plans/26-10-09-0821-plan-hr-fault-domain.html): 层是单点表, 「通道事件贴站点标签」在代码上不可表达。站点现状快照(`hr/status.py`)纯数据单层, `--hr-status` 报告/WebUI/运维脚本三消费者同一套数值口径。

## 跳检与 HR: 代价边界

跳检删种重加清零 qB 每种统计 → HR 锚点 seeding_time 倒退、超额线推迟(损失真实但数据不坏)。WEB 右键跳检对 HR 在管种子**只做警示文案**(硬闸涉及 HR 状态机语义, 另立单独裁决, plans/26-10-05-0314-plan-webui-danger-guards.html); 保护单点在 ops 层, 规则/WEB 同一入口按 source 区分(见 rule-engine.md checking 节)。

## 辅种分组 (core/modules/grouping_mod.py)

辅种 = 同一份数据在多站做种, 分组让组内共享物理文件的事实驱动保护动作。**设计不变量**:

- **归组键单点 `group_key_of`** = (规范化 save_path, 排序后的文件相对路径元组) —— 相同文件归组, 纯函数单一事实源; 组索引(groups/member_to_key/group_sizes)在 store, O(1) 定位, 增量维护。
- **组键首元走物理解析**(三层: 迁移 job 登记表 → 目录级链接 → 代表文件识别): 别名在场时仍指旧路径的成员与已搬走的 mover 并成同组不裂组; 文件级第三方链接只打标记不并组(语义表达不进组键形态)。
- 四相位订阅(transitions/torrents_added/removed_scan/post), 全部增量: 归组只对新种子拉文件列表, 冲突重算只对 `dirty_groups`(变化集驱动)。单条归组失败**逐条隔离**(消费点 `_try_assign` 包裹, issue 26-11-14-0745): 失败条入 `_pending_assign` 待归组补偿清单, post 相位每轮重试(种子已删出清单), 批内其余归组不中断; 清单纯内存不进 state_file —— rid 语义下失败轮种子下轮不再判 added, 产品进程重启(首轮全量重放)即最外层补偿路径, 与 by_hash/groups 内存态语义一致。
- **缺文件整组暂停**: 触发源(组内删除 / 上传转暂停 / 进入 errored / 保存路径变化)同组同轮只扫一次; 代表种允许 errored 成员(缺文件第一现场)—— 与跳检参考种「仅 is_complete」是**两口径**, 各自单点不混。命中 → **整组暂停 + MISSING 标签**(组内共享物理文件, 单点补救无意义)。安全边界: 存在性不可判定(UNDETERMINED)**跳过本组不判定**(配错映射宁可功能退化, 不能静默误暂停); qB 搬运过渡态(原名缺失 + `.!qB` 孪生)整轮放弃, 连续多次未消除才按真实缺失兜底; 搬迁在途的组让路。
- **下载冲突**: 同组 ≥2 同时下载, 或已完成与下载中并存 → 警告 + 整组暂停(两份下载写同一物理文件); 带 MISSING 标签的完成成员不计入「已完成」—— 用户重下是合法补救, 不被拦停。归组时文件大小不一致 → 警告 + 整组暂停。跨组交叉检测用物路径键(目录别名解析 + 大小写折叠)与归组键分层 —— 归组键保持词法形态。

## 整组迁移 (core/modules/relocate_*, 缺省关闭)

`relocate.enabled=false` 行为零(路由 fail-closed + 模块自查双拦)。迁移 = **别名单元**(junction/symlink)而非搬数据: 建链后旧路径数据不动, `regroup_scope` 强制作用域内重归组让 mover 与留守成员同组。预检零副作用(`relocate_precheck` 三分流 ok/confirm/blocked, 不写 state 不调写 API); 迁移在途的种子让缺文件扫描让路(此刻判「缺失」必是误判, 而误暂停代价不可逆)。设计与分期见 plans/26-10-18-1604-plan-group-relocate-restart-free.html。

**已定案口径**(2026-11-08 拍板, 自 issues-26-11-08-batch-fix):

- **撤终态拒撤**: `relocate_cancel` 对终态 job(FAILED/DONE/CANCELLED)恒 blocked(gate=`cancel_terminal`), 失败账不被覆盖、已收尾数据不再被搬回; 回迁走反向再迁移。
- **撤销回搬 fire-and-forget 豁免**: 对放行相位(MOVED/ARMED)的回搬在 `setLocation(src)` 下发后立即落 CANCELLED 并 `_resume_members`, 回搬过程脱离 job 跟踪 —— 回搬中断则数据分居 src/dst 无账可对。残余风险**拍板接受**(B9 已在拒撤守卫注释注明不取对账轮询方案, 不为此引入对账状态机); 边界: 仅撤销回搬, 迁移本体不豁免。
- **建链幂等**: `_build_links` 对盘上已存在且恰指向目标的别名/链接跳过入账(崩溃窗口孤儿可续建), 失败回滚 `_rollback_links` 按 plan 全量清单清理孤儿; 真冲突(指向别处)保守报错不删。
- **裂组口径**: 终态(failed/done/cancelled)job 退出 `resolve_physical` 登记表(TERMINAL_PHASES)→ 组键物理解析第 1 层断供; file_links 形态不改目录 realpath(第 2/3 层不并组)→ 真失败期间组视图可能按 save_path 分行(设计内, 现场保留语义的一部分; 「qB 列目录不解析文件级 symlink」类假阴性已修, 见 plans/26-11-10-0230-plan-relocate-listing-false-negative.html)。运行时F自检对「qB 列目录返回链接对象元数据」判 skipped(2026-11-10, `relocate_proof._link_object_hit`), file_links+symlink 假阴性消除。
- **失败账对账重推**: 上条的「终态退出登记表」对 failed 账不是永久静止 —— 每次启动按物理现状对账重推一次(armed_at==0(重入配额未用)且 mover 已到 dst 且 dst 数据全量在位 → 翻案重入既有收尾链, 组随重入经第 1 层活跃 job 登记表归一; 真失败/配额已用保守保留), 见 plans/26-11-10-0721-plan-relocate-startup-reconcile.html。

### 外部旧路径种子处置 (core/modules/relocate_foreign.py ForeignMixin, 计划 plans/26-11-20-0434-plan-backend-relocate-foreign-torrent.html)

IYUU 等外部工具按旧路径加种的两类坏法各一条处置线(场景 A 收尾窗内到达 = 零破坏纳入收尾; 场景 B 收尾后到达 = 只通知), 底线全程零破坏(不删种/不重加/不跳检/绝不静默全量校验 D8/D9), 文件清单不一致只告警不处置(D4)。配置键 `relocate.foreign_torrent`(bool 默认 true, D5; 权威在 config schema 代码单点)与 relocate.enabled 共同构成侦测闸门, 挂点 on_task_line 在 enabled 早退**之前**(关闸也观测跳变)。

- **侦测(D12)**: 每拍消费 store.last_added_diff(同步层原始 first-seen 差集, 在 qbmanager tracker 匹配门**之前**现算 —— 与 IYUU 具体添加形态无关 D6), 成本 O(本拍新增)与库容无关; 启动基线轮豁免, 断连重连只计断连期真新到, 每拍覆盖只读不排空。全量兜底扫只挂**四时机**: 启动首轮与 foreign_torrent 翻 true 共用「闸门激活」假→真跳变 / 收尾窗 job 集合比对触发 arm / store.sync_epoch 重连锚; 无周期兜底(D13, 漏消费等下次时机自愈)。
- **分类与预算**: save_path 归一恰等活跃 job 旧根(含 inherited)= 场景 A, 恰等终态账 done 的 src = 场景 B, failed/cancelled/superseded 不产自身边(接管旧根经后继 inherited 移交边仍可达, 语义不变), 子目录落点不在射程; 清单比对复用 _file_map/_plan_files 单点, 不一致只告警 + mismatch 账。单拍至多 10 次文件表比对 + 候选池上限 1000 有界 FIFO, 先处理后出队、逐候选异常隔离; 队列只存内存(丢失走 D13 边界)。
- **场景 A 纳入**: 追加 job.hashes + 读-改-写 spec["members"](hash_v1/v2 双查重、arm_members_of 同形追加、原子落盘; journal 零写 —— 改写账唯一写者是 daemon, 清单每窗现算); pre-armed 到达 torrents_pause + 并入 resume_hashes(dict.fromkeys 去重, 不覆盖原按住账), armed/收尾窗到达不暂停、纳入照做(D10); pending_tag 增量补打(was_add 门控)。核验覆盖/删链门豁免/缺文件扫描让路/跳检让路/删种拦截/absence_shrink 全部真自动(实时派生自 job.hashes, 零额外接线)。
- **收尾守卫**: `_rewrite_cover_of` 四分流 —— journal.rewrites 有账走既有语义零变更 / 无账在 spec = 改写在途 WAIT / 无账不在 spec = orphan WAIT + `_warn_orphan_rewrites` 告警带人工出路(接线 _step_reconcile, 只读视图不 materialize state) / spec 不可读保守 WAIT; `_verify_hang` 同加 WAIT 支(纳入成员改写未回流不再触发重放与永久悬挂)。
- **闭包解析** `_foreign_resolve_old_root`: done 直连边 + plan.inherited 移交边的传递闭包, 同根多条按 owner (updated_at, job_id, 自身边优先) 取新; visited 环保护 + 深度上限 20(= DONE_HISTORY_KEEP); 首跳无边 = None = R7「映射已过期」语义, 继承条目 job_id 悬空回落 owner。
- **场景 B 通知(D8/D14)**: WARNING 含旧路径/闭包解析现位置/产出 job/手动处置指引, 零自动动作。notified 账 state `relocate.foreign.notified`(hash → {root, kind, job_id, phase, location, first_seen}), 种子消失清条目; 重解析失败且账有 kind=B 条目 → 降级「映射已过期」(`_foreign_notify_expired`, 带重加路径守卫防误报), location 置空兼任呈现 expired 位与持久去重位, 新边重建 `_foreign_restore_location` 静默回填。
- **呈现**: 只读发布视图 foreign_notified_view(仿 jobs_snapshot: 整表重建/不变不换代/mark_dirty(full)), Web 线程不碰活账; WebUI relocate 面板 foreign 行标注(恒单排自成档, 筛选档「旧路径外部种子 (N)」空态不显示)+ 浮窗专属块 + 抽屉迁移段 + popovers 强调; 降级文案单点 decorate.RELOCATE_FOREIGN_EXPIRED; views_relocate foreign_member 投影与 member_relocate 同形, 组级豁免放宽 {foreign, superseded}(通知态不套「多任务」混态)。
- **内容根预筛(B1, 计划 plans/26-11-21-1600-plan-relocate-foreign-gate.html)**: 候选经 save_path 恰等门后、D4 清单比对前, `foreign_gate_passes`(relocate_units 纯函数)现算候选内容根 × scope 归一恰等, 不等 = 静默 DEBUG 丢弃(不入 notified 不呈现无持久负缓存, D2/D6); 退化形态(平铺/混合 scope=save_path)与不可判定形态(空文件表/空 scope/异常)保守恒过回落 D4; 文件表复用 _file_map 记录级惰性缓存零附加 API; 只丢「通知/纳入候选」, 收尾链与成员面零触碰, `_foreign_on_scenario_a` 接缝零改动 —— 兄弟目录种子不再涌入 mismatch(issue 1500)。
- **通知账终态清理(B2)**: job「非终态→终态」翻转边沿单点清 notified 内该 job 的 kind=A/mismatch(kind=B 留到种子消失), 三接线: `_set_job` 边沿 / `_handover_predecessors` superseded 直写点 / `_load_jobs` 启动对账采纳支(journal 即时落盘先于 state 周期刷盘, 崩溃窗恢复的终态不经 _set_job, 漏挂 = 在账 hash 被全量扫跳过致场景 B 通知永不发生); 清理面走只读视图判存在(合法关闭配置零 materialize, 黄金法则 2); 被清真同根种子交时机扫自然重判。mismatch 重判语义钉档单点在 relocate_foreign docstring(done/superseded 旧根在闭包边集 → 重落+恰重发一次 WARNING; failed/cancelled 无自身边 → classify 不命中 → 静默消失; 拍板 a 接受现状不改行为)。mismatch 文案改口径「同内容根目录下内容不一致, 疑似外部工具重加了不同版本」(后端 WARNING + decorate.RELOCATE_FOREIGN_MISMATCH 单点, 浮窗/抽屉共用; 呈现档位词表不扩面, D3)。(1326 收口)
- **收尾窗可观测性(B3 后端)**: daemon 日志分文件 `<data_dir>/logs/recycle_daemon.log`(INFO/append/无轮转/路径硬编码零新配置键, 只挂 daemon 进程与模块 logger, 建目录/开文件失败静默降级), 流程 INFO 行: 进窗路径(L1 实例级证据/L2 全机稳定窗标注)+ 逐成员改写结果(窗会话级边沿账去重, 事件恰一次); 对账 ACT_WAIT 提示(rt 键 = qB 态×相位×pending 数翻转去重 INFO, 只落 auto-qb.log 不接 errlog 环/推送); journal armed→rewritten 合并 INFO(相位条件自去重)。
- **行状态细化(B3 前端)**: `views_relocate.finalize_state(phase + qB 连接态)` 纯派生投影零新 state 键: rewritten → 「已改写待回连核验」(qB 三态恒定, 词面不抖动) / armed 且 qB 恰离线 → 「qB 下线等改写窗」(在线/未知回落 coarse) / done → 「收尾完成(新保存路径 dst)」; qB 连接态只读既有 status_snapshot().connected(替身/异常按 None 收口); 行状态词单点 decorate.relocateRowStateText, 浮窗 verdict 与抽屉迁移段共用; 呈现词表与「迁移状态」筛选档不扩面(细分档是收尾窗瞬时子态, 筛选仍按 coarse 取数); 快照延迟按「最后已知」呈现。
