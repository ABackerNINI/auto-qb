"""test_recycle_daemon 测试计划: fastresume 回收 daemon 竞态矩阵(计划 26-11-05-0808 §3.4 S3)

覆盖面: journal 协议扩展(rewritten 相位/成员改写账/daemon 心跳账/pending 口径单点,
relocate_journal S3 扩展段)+ 回收 daemon 主体(D12 简化形制)的竞态矩阵。全部替身:
「qB 在不在」桩在 socket.create_connection(端口证)+ 进程名册(证一)上, 不起真进程、
不回连真端口; fastresume 用 tmp 目录真实构造(test_core_fastresume 同款造法, 不 mock
编辑器 —— 改写落盘/幂等/坏样本语义全走真实代码); spec/journal/daemon.json 落 tmp_path;
时钟/睡眠注入, 无真实等待。

## 测试计划(每个测试函数一条; 竞态矩阵五项加注)

协议面(relocate_journal S3 扩展):
- test_instance_key_sanitizes_for_filename: 实例键文件名安全形制(冒号/IPv6/保留字折叠)
- test_daemon_state_write_touch_read_roundtrip: daemon.json 写-touch-读; touch 保诊断字段/
  更 ts; 外来 pid touch 拒写不落盘(退位互斥写侧闸)
- test_daemon_heartbeat_age_and_missing_is_inf: 无记录/无 ts => 无穷大
- test_daemon_stale_matrix: 挂死重拉判定 —— 无记录/pid 死/心跳过期 => stale; 健康在位 =>
  不 stale(alive 替身注入)
- test_release_daemon_state_owner_only: 按归属释放; 外来者删不掉新主记录
- test_release_daemon_state_remove_failure_is_false: 删除 OSError => False 不抛
- test_list_spec_jobs_missing_dir_is_empty: relocate 目录缺失 => 空清单
- test_spec_members_non_dict_entries_fall_back_to_hashes: members 形不符 => 退 hashes 派生
- test_clear_journal_removes_stale_life_journal: 主循环专属清理口 —— 真删/幂等(已不在
  => False)/上一世 failed 残留清掉后 daemon 认领面恢复
- test_record_rewrites_merges_members_and_refuses_terminal: 成员账合并(不丢前账)/fresh 建账
  相位 armed/翻相 rewritten 保账/终态拒收(取消收口即时生效的协议级闸)/终态相位参数 fail-fast
- test_failed_phase_is_stop_phase_daemon_side: failed 相位纳入停止语义(issue 26-11-07-0527
  #3)—— 记账/翻相/心跳式整包写拒收(失败证据不被覆盖)/scan 剔除/重放入口拒写/成员级
  failed 状态不回归(仍不视为收口)
- test_pending_members_settled_semantics: pending 口径 —— rewritten/already/unmatched 出账,
  failed/not_found/无账留守; members 字段优先于 hashes 派生

daemon 主体:
- test_rewrite_member_status_mapping: retarget 三态 + not_found/异常到记账 status 的映射表;
  fails 承前累计(失败 +1, 成功保值)
- test_rewrite_member_relative_keys_resolved_via_profile_base: 相对形态键经 spec.bt_backup
  推导 base 解析改写(E2c/issue 26-11-07-2336)—— rewritten 出账 + 产物落盘 + 重放 already
- test_scan_jobs_filters_instance_optin_and_terminal: 实例字面过滤/bt_backup opt-in(旧链
  spec 不碰)/终态剔除/残缺 spec 剔除/翻相 flag
- test_owner_beat_throttles_touch: 心跳 10s 节流(D12); 被退位自检在 touch 之前; 记录消失
  重新认主; touch 间隙被拒不炸
- test_run_flips_settled_phase_without_window: 全员已收口(账在相位未翻)+ qB 在线 => 只补翻
  相位, 零改写零进窗(journal 写不限窗口, D13)
- test_run_waits_for_stable_window_before_window: 进窗第三证(稳定窗)—— 下线未持续满
  stable 不动手(关机风暴形态: 窗口短于稳定窗 => 错过无害), 零落盘
- test_run_grace_exit_after_idle_period: pending 空 => 宽限计时, 计满才 idle 退出
  (grace < max_wait 时宽限先到, 非 timeout)
- test_cli_main_idle_exit_zero: CLI 入口空载 idle 退出码 0

竞态矩阵:
- [抢先回升/零写入] test_qb_revives_before_first_write_zero_member_writes: 进窗后第一次
  落盘前 qB 回升(名册第二次现读时翻 state)=> 本轮放弃, 零成员改写, 账面零 records
- [抢先回升/中途] test_qb_revives_mid_sequence_abandons_rest: A 改写落账后 qB 回升(retarget
  钩子翻 state)=> B 不再尝试不落账不落盘; A 已写部分留存(N4 自愈面)
- [半途崩溃] test_crash_mid_window_journal_consistent_and_next_round_replays: A 收口后 daemon
  终止(B 持续失败至 max_wait => timeout 模拟进程死亡) => 账面一致(A rewritten/B failed 计数
  在账); 修好 B 后新 daemon 重放: 只试 B(A 零重试), B 收口, 相位翻 rewritten
- [重复重放] test_replay_after_journal_loss_records_already: fastresume 已在目标值而账本清零
  (账丢失/新 daemon) => retarget unchanged+already => 记 already 出账, 文件字节零改动, 无
  .bak 产生(黄金法则 1)
- [窗口内重试] test_window_retry_until_success_counts_failures: 瞬态故障(坏样本第一拍修复)
  => 窗口内第二拍改写成功(D8 重试至成功), 失败计数 1 进账不丢
- [取消即时生效] test_main_loop_cancel_mid_window_skips_rest: A 落账的同一间隙对账落终态
  => B 写前现读见终态即弃, 不落盘; 终态相位不被 daemon 回退(前向合并)
- test_record_refused_when_terminal_lands_in_gap: 收口落在写前检查与落账间隙 => 落账拒收
  (False) => job 立即放弃(协议级终态闸门在 daemon 侧的出口)
- [退位互斥] test_deposed_old_daemon_self_checks_and_exits: 新主 pid 抢占(纯文件写, 无
  taskkill) => 旧 daemon 下一拍自检见外来 pid 即 deposed 退出, 退出前零覆盖(新主 ts 原样),
  release 不误删新主记录
- [退位互斥/窗口内] test_deposed_at_window_pass_top_aborts_round: 会话中抢占 => 拍顶自检
  即整轮 deposed, 已落账部分留存
- [退位互斥/成员拍] test_deposed_mid_window_member_beat_aborts: 成员 A 处理中途抢占 =>
  成员 B 拍级自检放弃, B 零触碰
- test_run_already_running_healthy_watcher_untouched: 健康 watcher(心跳新鲜 + pid 活)=>
  already_running 让路, daemon.json 零触碰
- test_run_preempts_dead_pid_record: 记录 pid 已死 => pid 抢占接管, 后续正常空载 idle
- test_run_timeout_keeps_pending: max_wait 到点 => timeout, pending 原样(账面零 records),
  daemon.json 按归属释放
- test_cli_main_timeout_exit_one: CLI timeout 档退出码 1
- test_module_main_entry_exits_with_result_code: python -m 入口结论码经 sys.exit 上抛 + 零 sys.modules 抢先加载告警

覆盖率缺口清偿(26-11-07, test.full 99.31% -> 99.5% 闸):
- test_write_journal_refuses_nonterminal_over_terminal: 终态闸门(非终态拒/终态互覆)
- test_alive_posix_fallback_paths: _alive POSIX 支(kill 探活/进程不在/信号不支持)
- test_verify_replays_of_bad_shape_is_zero: verify_replays 坏形 => 0
- test_reset_rewrites_terminal_refused_and_keeps_unsettled: 重放入口终态拒(-1)/非 settled 原样保留
- test_tasklist_ignores_non_quoted_lines: tasklist CSV 非引号行跳过
- test_names_from_proc_tolerates_unreadable_comm: /proc 名册逐项容错(comm 打不开跳过;
  pid 1 comm 重定向真实文件 => 可读支两平台非空可断, 修 Windows 主平台空转断言)
- test_qb_process_names_dispatches_non_windows: 进程名册分派(ps 支/proc 支)

收口评审修复轮(26-11-07):
- test_spec_retarget_mid_window_rewrites_remaining_to_new_dst: 窗口中段 spec.dst 被改道
  (supersede 账面段不需 qB 在线)=> 剩余成员按新 dst 改写(评审 #4: 旧实现用窗口 scan
  快照, 剩余成员写旧 dst)/ spec 现读失败 => 本 job 本拍放弃不拿旧快照改写
- test_spec_unreadable_mid_window_skips_job_without_stale_rewrite: spec 现读失败(撕态/被删)
  => 本 job 本拍放弃, 零改写零落账不拿旧快照(评审 #4 容错支)
- test_proc_absent_dual_evidence_and_roster_fallback: 证一判定(评审 #6)—— 名册可用时
  「进程不在 AND 端口拒连」合取(名册见 qB + 端口拒连 = 不进窗, WebUI 不可达 != 进程
  不在)/ 名册无 qB + 拒连成立 / 名册不可用退端口单证但告警降级 / 无端口退名册单证

观测面(W1a, 计划 26-11-10-0318 §03.1/§03.4; obs 账 helper + 观测通道函数族, 全桩化):
- test_obs_write_read_roundtrip_and_full_replace: obs 账写读回环(schema_version 写侧强制钉上/
  ts 缺省挂钟); 新写入即全量替换 —— host/port 换实例后旧 owner/absorbed 零继承
- test_obs_read_missing_or_bad_shape_is_none: 缺文件/schema_version 不符(含 bool 冒充 1)/
  host 非空 str 闸/port 正 int 闸/owner 或 absorbed 形不符(混型反例 pid="4242"/pid=True/
  ct="1e3")/absorbed 缺失/ts 非正数值/整文件非 dict/ct=1e999(inf)与 ct=10**400(巨 int
  溢出, T2 评审)非有限值反例 => None(半残记录不冒充证据, 保守退全机口径)
- test_obs_write_failure_is_false: 盘故障(OSError)=> False 不抛(daemon 节拍不因观测账中断)
- test_filetime_to_epoch_known_value: FILETIME(1601 起 100ns ticks)-> epoch 秒与 datetime 锚点互证
- test_owner_pid_from_netstat_zh_en_and_wildcard: netstat 解析中英文样例各一; 0.0.0.0 通配/
  具体地址同算, [::] IPv6 行独立 pid+端口断言(解析回归可判红); 非 LISTENING/UDP 行/表头/
  端口不合跳过; encoding=utf-8+errors=replace+timeout=10 钉法断言
- test_owner_pid_from_netstat_ambiguous_or_garbage_is_none: 归属不唯一 => None+warning(不猜);
  乱码输出(解码失败等效形态)=> 无匹配行 => None
- test_owner_pid_from_procnet_fake_tree: Linux LISTENING 归属(假 /proc): st==0A 端口->inode->
  fd socket 链接归属; tcp6 缺失只当该表无监听; 非监听行/端口不合跳过; 归属不唯一 => None
- test_listening_owner_pid_dispatch_and_exception_is_none: 分派(nt->netstat/posix->procnet)+
  归属不成功(None 支)与通道异常 => None+warning(证据语义: None=观测不可用, 绝不当 owner 死证)
- test_qb_processes_from_powershell_parse_and_conservative_drops: PowerShell 解析(pid|name|
  filetime -> ct 换算, 映像名小写); StartTime 不可读/pid 非数值/映像名空条目剔除且聚合判 None
  (部分清单不冒充全量); 形制外行/缺健康标记 => None; 标记+零数据 => {}(健康零观测); 钉法断言
- test_qb_processes_from_proc_fake_tree: Linux O2(假 /proc 树): comm 含 qbittorrent 收录 +
  btime/starttime/SC_CLK_TCK 换算; 读时已消失的 pid(FileNotFoundError)整体忽略; comm/stat 身份
  不可得 => 聚合判 None
- test_qb_processes_from_proc_broken_btime_or_hz_is_none: 病树变体 —— /proc/stat OSError/
  btime 行缺失/sysconf 桩抛/HZ<=0 => None + warning「枚举不可用」(绝不产假 ct)
- test_qb_processes_dispatch_timeout_and_healthy_empty: O2 分派: 子进程超时/命令缺失 => None+
  warning(观测不可用退 L2); posix 分派透传; 健康零观测({})不判不可用
- test_observe_owner_cross_check_and_channel_none: O1 交叉校验: 归属 pid 映像名含 qbittorrent
  才记 {pid, ct, ts}; 非 qB 占端口/映像名漂移/枚举通道 None/归属不成功 => None+warning(不记录)

判据面(W1b, 计划 26-11-10-0318 §03.2/§03.3; 全机 LISTENING 映射底座 + _Observation 状态机,
全替身/时钟显式注入/零 I/O; T2 评审修正: 行一同域阈值/gap 带走 settle/缺 ct 面真挡/健康
标记收紧/T2 nit 5-7):
- test_listening_map_netstat_groups_pid_ports: 全机映射解析 —— pid 归组(通配/具体/[::] 同算,
  同 pid 多端口合并); ESTABLISHED/TIME_WAIT/UDP 行与表头不进映射; 健康标记(零条 LISTENING
  解析成功 => None+warning, T2 收紧)—— 空输出/表头孤行/整包乱码/TCP 前缀行在而状态字或
  列数全不合都在此列(防「乱码 => 人人空集 => 假 settle 吸收」)
- test_listening_map_windows_and_dispatch: Windows 映射通道子进程钉法(encoding/errors/
  timeout/creationflags)+ dispatch(nt/posix)+ 通道异常 => None+warning(观测不可用)
- test_listening_map_proc_fake_tree: Linux 全机映射(假 /proc): inode->pid 归组/同 pid 多监听
  合并/tcp6 缺失只当该表无监听/tcp 主表不可读 => None+warning/表在而零条 LISTENING 解析
  (st 全非 0A)=> None+warning 且不扫 fd(T2 收紧, 不再 {})/
  REUSEPORT 两 pid 同端口 => 都进映射且归属判不唯一
- test_owner_pid_from_map_consistent_with_single_port_fns: 同源一致性 —— 同一份输出下, 映射
  派生归属与 W1a 单端口归属函数逐端口结论一致(netstat/procnet 各一, 含不唯一两边同 None)
- test_listening_owner_pid_injected_map_no_subprocess: 注入映射的归属面不起子进程(subprocess
  下毒); 端口无主/归属不唯一 => None+warning(与自取路径同语义)
- test_observe_owner_injected_map_matches_self_fetch: 注入映射的候选面不起子进程且与自取路径
  结论一致(自取路径两平台分派任一平台都跑, 两支各 os.name 桩钉住: nt 桩 netstat 输出 /
  proc 桩 /proc 表+fd, 各让 8081 归 pid 100) —— W2a 每 poll 一次读取喂「归属+指纹」两
  消费面的接线契约
- test_observation_zero_bet_absorb_row1: §03.2 行一 零赌注吸收(同域阈值, T2 major 修正)——
  ct < owner.ct 的非 owner 面直接进 absorbed(OS create_time 同域比消钟差, 持久面变更,
  不需要指纹通道); owner 本尊/已吸收面不重复; 名册 None 整拍不动
- test_observation_gap_band_goes_settle_and_order_invariant: 行一 gap 带 [owner.ct, ts_last)
  走未决 settle 管道(T2 major 修正: 旧混域零赌注即时吸收已废); 行序钉死 —— 行二在位续证
  刷 ts 不移动锚(owner.ct), gap 面两序最终一致走 settle 绝不即时吸收; 指纹通道断只滞留未决
- test_observation_unreadable_ct_face_parks_pending: 名册条目 ct 读不出的面进未决真挡(T2
  minor/nit)—— 不自动 settle 吸收(写不进合法 absorbed 条目)/absorbed 保留/l1 挡窗/身份
  恢复重走分类/绑端口升格出队/从名册消失出队
- test_observation_port_bind_becomes_owner_row2: §03.2 行二 绑端口转 owner —— 复活/换身/PID
  复用三向都更新 owner 记录(未决出队/误吸面出 absorbed); 在位续证只刷内存 ts 不触发落盘
- test_observation_owner_record_survives_death: owner 死亡(pid 从名册消失)时记录保留(它就是
  死证), 只有复活/换身才覆盖; 名册 {} 零持久面变更
- test_observation_settle_absorb_row3_and_reset: §03.2 行三 settle 吸收 —— 指纹稳定 30s 且不含
  我们端口才吸收; 指纹变了/通道不可用 => settle 重算; 空指纹(已创建未绑端口)受同一有界赌注
  (R3); 指纹含我们端口永不 settle
- test_observation_pending_blocks_and_leaves_on_disappear_row4: §03.2 行四 未决挡 L1(死证+
  拒连已齐也不开); 从名册消失即出队(重现全新计时); PID 复用(同 pid 异 ct)出队重算
- test_observation_absorbed_release_and_pid_reuse: absorbed 消失移出(持久面变更 => 落盘时机,
  payload 不含死者); PID 复用不继承吸收身份(旧条目清出 + 新面孔重走未决/settle)
- test_observation_l1_open_truth_table: §03.3 真值表 —— owner 死三形态 × 端口拒连 × 未决成员;
  无 owner 记录 => False(L1 不适用); 名册 None => None(本拍不可判, 与「不成立」可区分);
  名册 {} + owner 记录 => 死证成立(立即进窗)
- test_observation_payload_roundtrip_and_bad_shape_is_none: to_payload->from_payload 回环幂等;
  owner/absorbed 恢复、未决清空(settle 重算); 坏 payload(host/port 不符或混型/owner 或
  absorbed 形不符/absorbed 缺键/非 dict)=> None 保守弃不抛

接线面(W2a, 计划 26-11-10-0318 §04 W2 的 1-3 项): run/_process_window 三层判据接线 + 观测维护
tick 契约 + 复验升级 + warning 节流; _stub_qb 并桩观测通道(恒 None)把既有用例钉在 L2 等价
面。接线级单测; 场景级全链端到端(场景 X/Y、PID 复用两端向、obs 跨重启端到端链)留 W2b
—— 本波的 test_run_restarts_restore_owner_evidence_from_obs_file 是接线级重启恢复
(from_payload 恢复面), 不是端到端全链(T3 评审 B3 措辞区分):
- test_run_l1_dead_owner_enters_window_without_stable_wait: L1 verdict True 立即进窗(拍板
  D2, 无 down_since 计时)—— obs 死证(owner pid 已从名册消失)+ 拒连 + 无未决 => stable
  远超 max_wait 仍完成改写(时钟注入证明无 30s 等待)
- test_run_no_owner_record_walks_l2_stable_window_equivalent: 等价面 —— 无 owner 记录 =>
  verdict False 走 L2 现状 30s(与 test_run_waits_for_stable_window_before_window 同形态:
  stable 未满 timeout 零落盘); verdict False 不告警(正常路径, 区别于通道故障); obs 文件零写
- test_run_l1_roster_channel_broken_falls_back_l2_throttled: 名册通道故障 => l1_open None
  即便有有效死证也不进窗(通道故障不冒充通过)⇒ 退 L2 + 节流 warning(60s 内多拍只首拍一条;
  跨 60s 边界的窗口期再计一条); roster None => tick 整拍不动, obs 文件零写
- test_run_l1_window_reverify_owner_revive_aborts: 复验升级(§03.3)—— 进窗判据与窗内复验
  之间 owner 复活(名册重现 + 端口回绑)=> L1 窗复验不过 => qb_back 中止零落盘(现状中止
  语义原样); 复活在位续证只在内存, obs 持久面零变更
- test_run_obs_tick_persists_changed_state_only: 观测维护 tick 契约 —— 持久面变更(True)
  才 write_obs: 新面孔零赌注吸收首拍落盘一次, 同 roster 后续拍零变更不重写(多拍写次数
  钉死 = 1, 在位续证只在内存); 文件内容对齐 obs schema
- test_run_obs_write_failure_throttled_warning_no_crash: obs 落盘失败 => 节流 warning 不崩,
  内存态继续(重启丢观测退 L2 安全向); 每 poll 新面孔都触发写尝试, 60s 内只首拍一条
- test_run_restarts_restore_owner_evidence_from_obs_file: daemon 重启恢复(§03.4 覆盖
  「停机期间目标死亡」)—— 前世经真实 tick 通道归档在位 owner, 新世 from_payload 恢复
  死证 => 立即进窗改写; obs 记录跨重启保留
- test_run_corrupt_obs_file_starts_empty_and_stays_l2: obs 文件坏形(非 JSON)=> 新建空
  _Observation 走 L2(D3 冷启动形态): 不崩溃、不覆盖坏文件、窗口时序按现状
- test_run_observation_channels_not_polled_without_pending: §03.1 口径 —— 无 pending job
  时观测通道零调用(子进程预算只花在有活的拍上)

复验现判补强(W2a 编排方裁决, §03.3 第 3 条件「现判」化: unclassified_faces 纯分类读并入
_l1_window_open —— 条件 3 不只看进窗时 pending 快照, 现读名册里状态机不能立即出具「无害」
结论的面一律复验不过):
- test_run_l1_window_reverify_unclassified_face_blocks: 窗顶复验现读名册冒出全新未分类面
  => l1_open 三条件全齐也复验不过 qb_back 零落盘; 指纹通道断 => 面永滞未决, 窗不再开
- test_run_l1_window_reopens_after_settle_absorb: 同面被 tick 正规吸收(settle 30s 行三,
  持久面落盘)后窗重开改写收口 —— 挡是暂态不是死锁, 与状态机设计自洽
- test_run_l1_window_reverify_absorbed_face_does_not_block: absorbed 命中面是状态机已出具
  「无害」结论的面 => 复验放行改写(分类读不把已吸收面当未分类)
- test_run_l1_window_reverify_unreadable_ct_face_blocks: ct 读不出的面 => 未分类挡(与 tick
  缺 ct 面停未决真挡同向), l1_open 三条件全齐也不放行
- test_observation_unclassified_faces_classification_table: unclassified_faces 分类表(纯
  分类读)—— owner 身份命中/absorbed 命中/pending 在册不进清单; ct 读不出/ct<owner.ct 未及
  吸收/owner pid 复用面/absorbed pid 复用面(B2)/全新面一律未分类; roster 字面量乱序插入
  钉 sorted(B5); 纯读状态机零变动

通道告警节流(T3 评审 A1: 通道函数族加 keyword-only warn 形参, 缺省 logger.warning 直落
—— 直接调用方/既有测试零感知; 接线面 _observe_poll 按(实例, 类)传 _warn_sink 节流绑定,
sink 类键 obs_listen/obs_roster/obs_owner + 接线点处置类 listen 补齐, 持续故障每类
1 条/60s 不刷屏):
- test_run_observe_channel_warnings_throttled_per_class: 持续故障形态(netstat 空输出格式
  漂移 + PowerShell 缺健康标记 + 接线点指纹/verdict 处置)—— 四类各 60s 只首拍一条, 跨
  60s 边界的窗口期再计一条(拍点 5s 步进, 140s 窗各 3 条)
- test_run_observe_owner_warning_throttled: 占用者告警(端口可达 + 归属唯一 + 占用者非名册
  qB)每 poll 触发同类节流; 占用者永不建档(obs owner 恒 None), 无关名册 qB 面 30s settle 吸收
  照常(观测维护不因占用者告警阻断)
- test_run_owner_attribution_and_occupier_warnings_independent_throttled: 归属/占用者告警
  分键(评审轮 2 N1)—— 归属层告警(映射无我们端口 => 「未归属成功」)走 obs_listen 类、
  占用者告警走 obs_owner 类, 交替故障形态下两类各自 60s 节流互不顶掉(旧共键实现首拍即把
  对方顶掉): 60s 窗两类各 1 条, 140s 窗各 3 条; 占用者/归属失败都永不建档(obs owner 恒
  None)
- test_run_l1_reverify_channel_failure_throttled: L1 复验拍通道故障节流(评审轮 2 N2)——
  复验现读名册通道异常经 obs_roster 类 sink 节流(与主循环读同一条 qB 名册通道, 同根因
  共键不刷屏)+ verdict None 处置留痕走独立 reverify 键(qb_back 中止事件不被主循环处置
  留痕顶掉): poll 拍通道健康进窗/复验拍通道异常的交替形态下, 60s 窗两类各只首拍一条,
  跨 60s 边界各 3 条; 复验不过 => qb_back 零落盘

场景级(W2b, 计划 26-11-10-0318 §04 W2 第 4 项; 六场景全链端到端。与接线级 W2a 分工:
接线级钉分层语义(三层判据分派/tick 契约/复验现判/节流计数), 场景级钉全链行为 ——
观测通道 -> 状态机 -> 进窗 -> 逐成员改写 -> journal 落账 -> obs 持久化的完整驱动序列,
时序断言用注入时钟 + 落账时刻捕获证明, 无真实等待; 世界桩 _stub_world 单桩四通道,
翻面点显式(参考 _flip_to_face_at_reverify 做法)):
- test_scenario_x_owner_death_gap_rewrites_immediately: [场景X] 目标重启死亡间隙立即落盘
  (§03.3 callout, 拍板 D2 安全性根基)—— poll1 真实观测通道建档 owner -> poll2 目标死亡
  新身完全未起 => 同拍 L1 立即进窗复验照过, 两成员逐个改写落盘 + journal 逐成员记账
  (双键明细在账, 相位翻 rewritten); 落账时刻 - owner 建档时刻 < NEW_FACE_SETTLE(stable=1000
  注入时钟证明无 30s 等待, 且早于 L2 等价路径的「死亡 + 30s 稳定期」最早开窗点)
- test_scenario_y_daily_restart_settle_absorb_then_rewrite: [场景Y] 日常实例重启 settle
  吸收(P7 形态, §03.2 行三, §07 R3 有界赌注定价 ~33s)—— 目标死(owner 记录在 obs)+
  日常库重启新面孔(ct >= owner.ts, 不绑我们端口)=> 未决挡窗 -> NEW_FACE_SETTLE 指纹
  稳定吸收落盘 -> 窗开改写; 吸收前零改写(落账时刻 >= absorbed ts)/吸收后改写落盘/
  首见到吸收 >= 30s 且 < 40s(满界下一拍, 不拖)/obs absorbed 条目持久化/owner 死证原样
- test_scenario_pid_reuse_non_qb_dead_evidence_form1: [PID复用向一] 死 owner 的 pid 被非
  qB 程序复用(qB 身份名册无该 pid)=> 死证形态一成立照常进窗, 首拍即改写(同场日常库旧
  实例 ct < owner.ct 行一零赌注吸收不挡窗); 全机映像名册见 qB(L2 等价路径被阻断)——
  窗是 L1 开的, 实例级证据相对全机口径的增量; obs absorbed 收录日常库、owner 死证原样
- test_scenario_pid_reuse_qb_instance_blocks_until_disposed: [PID复用向二] 死 owner 的 pid
  被另一 qB 实例复用(名册有 pid 但 ct 不等)=> 判原实例已死(形态二)+ 复用者按全新面孔
  分类(PID 复用不继承 owner/absorbed 身份)=> 未决挡窗直至 settle 吸收后窗开改写;
  owner 死证记录不被复用者覆盖(未绑我们端口不升格); 吸收前零改写
- test_scenario_pending_face_at_window_criterion_blocks: [未决挡窗] 窗开判据现场冒未决新面
  (与场景 Y 呼应、驱动源不同: 目标死亡同拍现身的全新面, ct >= ts_last)=> 判据现场未决
  在册不进窗(窗从未开过, 区别于窗开后复验挡)零改写, settle 后窗开改写; owner 建档 ts
  钉在首见拍(真实通道建档), absorbed 持久化
- test_scenario_obs_reload_across_restart_rewrites_from_dead_evidence: [obs重启重载]
  第一世 daemon 经真实观测通道建档 owner(目标在跑, 零改写 timeout 收束)-> 停机期间
  目标死亡 -> 第二世 from_payload 恢复死证 => 首拍 L1 进窗改写(stable=1000 无 30s 等待);
  obs owner 记录跨重启逐字段一致(死证不被触碰), 与接线级重启恢复专测分工: 本测建档走
  全链通道非预播种
- test_scenario_channel_outage_falls_to_l2_then_l1_on_recovery: [通道失败退L2] 名册通道
  恒故障 => 全程退 L2 现状判据(黄金法则 2 保守退化): 30s 稳定期内零改写(max_wait=25 <
  stable=30 截停; 通道故障若被冒充成健康零观测或稳定期被丢, 改写会在首拍出现; 分派层
  None=>True 由接线级复验闸专测兜, 本测断言面 = 端到端往返)+ 节流
  warning 留痕 60s 一条 + obs 死证种子原样(roster None => tick 整拍不动); 第二世通道
  恢复(健康零观测)=> 回 L1 死证立即改写(零「退 L2」留痕, 无稳定期)—— 行为与接线前
  等价的端到端往返
"""
import builtins
import io
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pytest

from auto_qb.core import fastresume as frmod
from auto_qb.hr.bencode import compute_infohashes
from auto_qb.infra import relocate_journal as rj
from auto_qb.tools import recycle_daemon as rd

HOST = "127.0.0.1"
PORT = 36596

# ---------------------------------------------------------------------------
# 造法(test_core_fastresume 同款: 真实 bencode/fastresume, 不 mock 编辑器)
# ---------------------------------------------------------------------------


def _member_fixture(backup: Path, tag: bytes, old_root: str, *, rewritten_to: str = "") -> str:
    """BT_backup 落一对 <v1>.torrent + <v1>.fastresume, 返回 v1 hash。
    save_path 反斜杠风味(lt 键, N1 实测字节), qBt 键正斜杠风味; rewritten_to 非空时
    直接落"已在目标值"形态(重复重放测试用)。"""
    info = {b"name": tag, b"piece length": 16384, b"pieces": b"\x00" * 20, b"length": 1}
    torrent = frmod.bencode({b"announce": b"http://tracker.example/ann", b"info": info})
    v1, _, _ = compute_infohashes(torrent)
    name = tag.decode()
    root = rewritten_to or old_root
    val = {
        b"save_path": (root + "\\" + name).encode("utf-8"),
        b"qBt-savePath": (root.replace("\\", "/") + "/" + name).encode("utf-8"),
        b"qBt-name": tag,
        b"completed": 1,
    }
    backup.mkdir(parents=True, exist_ok=True)
    (backup / f"{v1}.torrent").write_bytes(torrent)
    (backup / f"{v1}.fastresume").write_bytes(frmod.bencode(val))
    return v1


def _write_job(
    tmp_path: Path,
    data_dir: str,
    job_id: str,
    hashes,
    *,
    host=HOST,
    port=PORT,
    bt_backup=True,
    members=None,
    src=None,
    dst=None,
    journal_phase=None
) -> dict:
    src = str(tmp_path / "src") if src is None else src
    dst = str(tmp_path / "dst") if dst is None else dst
    spec = {
        "job_id": job_id,
        "src": src,
        "dst": dst,
        "scope": dst,
        "hashes": list(hashes),
        "host": host,
        "port": port,
        "alias_paths": [],
        "files": [],
    }
    if bt_backup:
        spec["bt_backup"] = str(tmp_path / "BT_backup")
    if members is not None:
        spec["members"] = members
    rj.write_spec(data_dir, job_id, spec)
    if journal_phase:
        rj.write_journal(data_dir, job_id, {"phase": journal_phase})
    return spec


def _stub_qb(monkeypatch, state):
    """三证桩: 端口证桩在 socket.create_connection(连得上=在/拒连=不在, rd 内三证判据
    消费同一 socket 模块对象); 进程名册与 state 联动 —— qB 在 = 名册含 qbittorrent,
    不在 = 名册可用但只有无关进程(评审 #6 起 _proc_absent 双判合取, 名册参与判定;
    单实例机器语义: qB 真死时名册自然无 qB 进程, 合取不损窗口可用性)。state["up"]=True
    即「qB 在」。

    W2a 并桩观测通道(计划 26-11-10-0318 接线面): _qb_processes/_listening_map 恒 None
    (观测通道不可用)—— 接线面每拍观测维护拿到 l1_open None => 既有用例一律退 L2 现状
    路径(等价面锚死: 无 owner 记录/通道故障都不改既有窗口时序), 且不起真子进程
    (PowerShell/netstat); L1 路径由接线面专测用 _stub_obs 自桩可控 roster/映射。"""
    def _connect(addr, timeout=None):
        if state["up"]:
            return mock.MagicMock()
        raise OSError(10061, "refused")

    monkeypatch.setattr(rd.socket, "create_connection", _connect)
    monkeypatch.setattr(
        rd, "_qb_process_names", lambda: ("qbittorrent.exe", ) if state["up"] else ("explorer.exe", "svchost.exe")
    )
    # *a/**k 接参: 接线面 _observe_poll 以 warn= 关键字调用通道函数(T3 评审 A1), 桩签名须兼容
    monkeypatch.setattr(rd, "_qb_processes", lambda *a, **k: None)
    monkeypatch.setattr(rd, "_listening_map", lambda *a, **k: None)


def _clock_gen(start=1000.0, step=5.0):
    state = {"t": start}

    def _clock():
        state["t"] += step
        return state["t"]

    return _clock


def _run(
    data_dir,
    *,
    host=HOST,
    port=PORT,
    stable=0.0,
    poll=0.0,
    grace=0.0,
    heartbeat=10.0,
    max_wait=0.0,
    clock=None,
    sleep=None
):
    return rd.run(
        data_dir,
        host,
        port,
        stable=stable,
        poll=poll,
        grace=grace,
        heartbeat=heartbeat,
        max_wait=max_wait,
        clock=clock or _clock_gen(),
        sleep=sleep or (lambda s: None),
    )


def _fr_path(tmp_path: Path, h1: str) -> Path:
    return tmp_path / "BT_backup" / f"{h1}.fastresume"


# ---------------------------------------------------------------------------
# 协议面: instance_key / daemon.json / 心跳 / stale 判定
# ---------------------------------------------------------------------------


def test_instance_key_sanitizes_for_filename():
    k = rj.instance_key("127.0.0.1", 8080)
    assert k == "127.0.0.1_8080"
    # IPv6/怪字符一律折叠(Windows 文件名禁冒号); 折叠不可逆, 身份判定以 (host, port) 原值
    for host in ("::1", "fe80::1%eth0", "a b"):
        key = rj.instance_key(host, 8080)
        assert not (set(key) & set(":\\/*?\"<>|")), key
    assert rj.instance_key("h", 1) == rj.instance_key("h", 1)


def test_daemon_state_write_touch_read_roundtrip(tmp_path):
    d = str(tmp_path)
    rj.write_daemon_state(d, "k", 7, host="h1", port=9, ts=100.0)
    st = rj.read_daemon_state(d, "k")
    assert st["pid"] == 7 and st["host"] == "h1" and st["port"] == 9 and st["ts"] == 100.0
    # touch: 归属核验通过 => 更 ts, 诊断字段保留
    assert rj.touch_daemon_state(d, "k", 7, ts=150.0) is True
    st = rj.read_daemon_state(d, "k")
    assert st["ts"] == 150.0 and st["host"] == "h1" and st["port"] == 9
    # 被退位(记录 pid 非我): 拒 touch 且不落盘(不得用心跳覆盖新主 pid)
    assert rj.touch_daemon_state(d, "k", 8, ts=200.0) is False
    assert rj.read_daemon_state(d, "k")["ts"] == 150.0


def test_daemon_heartbeat_age_and_missing_is_inf(tmp_path):
    d = str(tmp_path)
    assert rj.daemon_heartbeat_age(d, "none") == float("inf")
    rj.write_daemon_state(d, "k", 7, ts=1000.0)
    assert rj.daemon_heartbeat_age(d, "k", now=1005.0) == 5.0
    rj._write_json(rj.daemon_state_path(d, "bad"), {"pid": 7})  # 无 ts(坏记录)
    assert rj.daemon_heartbeat_age(d, "bad") == float("inf")


def test_daemon_stale_matrix(tmp_path):
    """挂死重拉判定(对账 ACT_ENSURE_DAEMON 的判据单点, 本期提供函数、接线下一任务)"""
    d = str(tmp_path)
    assert rj.daemon_stale(d, "none", max_age=60.0, now=1000.0) is True, "无记录 => 可重拉"
    rj.write_daemon_state(d, "k", 4242, ts=1000.0)
    assert rj.daemon_stale(d, "k", max_age=60.0, now=1050.0, alive=True) is False, "健康在位"
    assert rj.daemon_stale(d, "k", max_age=60.0, now=1061.0, alive=True) is True, "心跳过期"
    assert rj.daemon_stale(d, "k", max_age=60.0, now=1001.0, alive=False) is True, "pid 已死"
    rj._write_json(rj.daemon_state_path(d, "bad"), {"pid": 0, "ts": 1000.0})
    assert rj.daemon_stale(d, "bad", max_age=60.0, now=1001.0, alive=True) is True, "坏记录"


def test_release_daemon_state_owner_only(tmp_path):
    d = str(tmp_path)
    rj.write_daemon_state(d, "k", 7, ts=1.0)
    assert rj.release_daemon_state(d, "k", 8) is False, "外来者不得删"
    assert rj.read_daemon_state(d, "k") is not None
    assert rj.release_daemon_state(d, "k", 7) is True
    assert rj.read_daemon_state(d, "k") is None
    assert rj.release_daemon_state(d, "k", 7) is False


def test_release_daemon_state_remove_failure_is_false(tmp_path, monkeypatch):
    """删除失败(OSError)⇒ False 不抛(调用方在 finally 里, 退出路径不得炸)"""
    d = str(tmp_path)
    rj.write_daemon_state(d, "k", 7, ts=1.0)

    def _raise(p):
        raise OSError("busy")

    monkeypatch.setattr(rj.os, "remove", _raise)
    assert rj.release_daemon_state(d, "k", 7) is False


def test_list_spec_jobs_missing_dir_is_empty(tmp_path):
    assert rj.list_spec_jobs(str(tmp_path / "no-such-dir")) == []


def test_spec_members_non_dict_entries_fall_back_to_hashes():
    """members 字段全非 dict(形不符)⇒ 退回 hashes 派生(不空转不炸)"""
    spec = {"members": ["not-a-dict", 42], "hashes": ["h1"]}
    pend = rj.pending_members(spec, {})
    assert [rj.member_key(m) for m in pend] == ["h1"]


# ---------------------------------------------------------------------------
# 协议面: 成员改写账与 pending 口径
# ---------------------------------------------------------------------------


def test_record_rewrites_merges_members_and_refuses_terminal(tmp_path):
    d = str(tmp_path)
    # fresh 建账: 无 journal 时相位落 armed(相位模型主干), 账随写随在
    assert rj.record_rewrites(d, "j", {"h1": {"status": "rewritten"}}, ts=1.0, pid=9) is True
    j = rj.read_journal(d, "j")
    assert j["phase"] == "armed" and j["rewrites"]["h1"]["status"] == "rewritten" and j["pid"] == 9
    # 合并: 后写不丢前账; 记录缺省补 ts
    assert rj.record_rewrites(d, "j", {"h2": {"status": "failed"}}, ts=2.0) is True
    rw = rj.read_rewrites(d, "j")
    assert rw["h1"]["status"] == "rewritten" and rw["h2"]["status"] == "failed"
    assert rw["h2"]["ts"] == 2.0
    # 翻相: rewritten 相位落账且账保全
    assert rj.record_rewrites(d, "j", {}, phase=rj.PHASE_REWRITTEN, ts=3.0) is True
    j = rj.read_journal(d, "j")
    assert j["phase"] == "rewritten" and j["rewrites"]["h1"]["status"] == "rewritten"
    # 终态拒收: 对账已收口 => 拒写(取消/完成对 daemon 即时生效的协议级闸门)
    rj.write_journal(d, "j", {"phase": "done"})
    assert rj.record_rewrites(d, "j", {"h3": {"status": "rewritten"}}) is False
    assert rj.read_journal(d, "j")["phase"] == "done"
    # 终态相位参数 fail-fast(终态是主循环专属写权)
    try:
        rj.record_rewrites(d, "j2", {}, phase="done")
        raise AssertionError("终态相位参数必须 ValueError")
    except ValueError:
        pass


def test_failed_phase_is_stop_phase_daemon_side(tmp_path):
    """failed 相位纳入停止语义(issue 26-11-07-0527 #3): daemon/写侧协议对 failed 与
    done/cancelled 同退休 —— 记账/翻相/心跳式整包写一律拒收(失败证据不被重拉后的
    daemon 抹掉), scan 剔除, 重放入口拒写; 成员级 failed 状态不回归(仍不视为收口)"""
    d = str(tmp_path)
    rj.write_journal(d, "jf", {"phase": "failed", "reason": "verify_mismatch", "ts": 1.0})
    assert "failed" in rj.STOP_PHASES
    # daemon 记账拒收: journal 原样(证据不被整包覆盖)
    assert rj.record_rewrites(d, "jf", {"h1": {"status": "rewritten"}}, ts=2.0) is False
    j = rj.read_journal(d, "jf")
    assert j["phase"] == "failed" and j["reason"] == "verify_mismatch" and "rewrites" not in j, j
    # 心跳式/翻相的非终态整包写同样拒收(前向合并: 非终态不得覆盖终态)
    assert rj.write_journal(d, "jf", {"phase": "armed", "pid": 9}) is False
    assert rj.write_journal(d, "jf", {"phase": rj.PHASE_REWRITTEN}) is False
    assert rj.read_journal(d, "jf")["phase"] == "failed"
    # 终态相位参数 fail-fast 与重放入口拒写
    try:
        rj.record_rewrites(d, "jf2", {}, phase="failed")
        raise AssertionError("failed 相位参数必须 ValueError")
    except ValueError:
        pass
    assert rj.reset_rewrites(d, "jf") == -1
    # scan 剔除: 失败终态的 job 不再被 daemon 认领(退休)
    data_dir = str(tmp_path / "data2")
    backup = tmp_path / "BT_backup2"
    h1 = _member_fixture(backup, b"m-f", str(tmp_path / "src"))
    _write_job(tmp_path, data_dir, "job-failed", [h1])
    rj.write_journal(data_dir, "job-failed", {"phase": "failed", "reason": "verify_mismatch", "ts": 1.0})
    assert [x["job_id"] for x in rd._scan_jobs(data_dir, HOST, PORT)] == []
    # 成员级 failed 状态不回归: 仍不在收口集(pending 留守, 窗口内重试/下一窗口重放)
    assert rj.record_rewrites(d, "j-ok", {"h1": {"status": "failed", rj.REWRITE_FAILS_KEY: 1}}, ts=3.0) is True
    spec = {"members": [{"hash_v1": "h1", "hash_v2": ""}]}
    assert [rj.member_key(m) for m in rj.pending_members(spec, rj.read_rewrites(d, "j-ok"))] == ["h1"]


def test_clear_journal_removes_stale_life_journal(tmp_path):
    """主循环专属清理口(issue 26-11-07-0527 #3 评审 finding 1): 真删/幂等(已不在 => False
    不抛); 清掉上一世 failed 残留后 daemon 认领面自然恢复(退休随新生命周期解除)"""
    d = str(tmp_path)
    rj.write_journal(d, "jc", {"phase": "failed", "reason": "verify_mismatch", "ts": 1.0})
    assert rj.clear_journal(d, "jc") is True
    assert rj.read_journal(d, "jc") is None
    assert rj.clear_journal(d, "jc") is False, "幂等: 已不在 => False 不抛"
    assert rj.clear_journal(d, "never-existed") is False


def test_pending_members_settled_semantics():
    spec = {"hashes": ["h1", "h2", "h3", "h4", "h5"]}
    rewrites = {
        "h1": {
            "status": "rewritten"
        },
        "h2": {
            "status": "already"
        },
        "h3": {
            "status": "unmatched"
        },
        "h4": {
            "status": "failed",
            "fails": 2
        },
    }
    pend = rj.pending_members(spec, rewrites)
    # rewritten/already/unmatched 出账(REWRITE_SETTLED); failed 与无账留守
    assert [rj.member_key(m) for m in pend] == ["h4", "h5"]
    assert rj.pending_members(spec, {}) and len(rj.pending_members(spec, {})) == 5
    # members 字段优先于 hashes 派生(v2/hybrid 显式双 hash 形态)
    spec2 = {"hashes": ["hA"], "members": [{"hash_v1": "", "hash_v2": "v2id"}]}
    pend2 = rj.pending_members(spec2, {})
    assert len(pend2) == 1 and rj.member_key(pend2[0]) == "v2id"


# ---------------------------------------------------------------------------
# daemon 主体: 记账映射 / 扫描 / 心跳节流 / 翻相 / CLI
# ---------------------------------------------------------------------------


def test_rewrite_member_status_mapping(tmp_path):
    old_root = str(tmp_path / "src")
    new_root = str(tmp_path / "dst")
    backup = tmp_path / "BT_backup"
    spec = {"bt_backup": str(backup), "src": old_root, "dst": new_root}
    h_ok = _member_fixture(backup, b"m-ok", old_root)
    h_already = _member_fixture(backup, b"m-already", old_root, rewritten_to=new_root)
    h_elsewhere = _member_fixture(backup, b"m-elsewhere", old_root)
    h_missing = "0" * 40
    h_bad = _member_fixture(backup, b"m-bad", old_root)
    (_fr_path(tmp_path, h_bad)).write_bytes(b"garbage-not-bencode")
    # elsewhere: 路径键全不命中旧根 => unmatched(确定性无操作)
    p = _fr_path(tmp_path, h_elsewhere)
    val = frmod.load_fastresume(p)
    val[b"save_path"] = rb"Q:\elsewhere\x"
    val[b"qBt-savePath"] = b"Q:/elsewhere/x"
    p.write_bytes(frmod.bencode(val))

    assert rd._rewrite_member(spec, {"hash_v1": h_ok}, None)["status"] == "rewritten"
    rec = rd._rewrite_member(spec, {"hash_v1": h_already}, None)
    assert rec["status"] == "already" and "save_path" in rec["keys"]
    assert rd._rewrite_member(spec, {"hash_v1": h_elsewhere}, None)["status"] == "unmatched"
    assert rd._rewrite_member(spec, {"hash_v1": h_missing}, None)["status"] == "not_found"
    bad = rd._rewrite_member(spec, {"hash_v1": h_bad}, None)
    assert bad["status"] == "failed" and bad["error"] and bad[rj.REWRITE_FAILS_KEY] == 1
    # fails 承前累计: 失败 +1, 成功保值(失败计数进账, D8); ok 已被上面真改写过, 用新成员
    bad2 = rd._rewrite_member(spec, {"hash_v1": h_bad}, {"status": "failed", "fails": 3})
    assert bad2["status"] == "failed" and bad2[rj.REWRITE_FAILS_KEY] == 4
    h_ok2 = _member_fixture(backup, b"m-ok2", old_root)
    ok2 = rd._rewrite_member(spec, {"hash_v1": h_ok2}, {"status": "failed", "fails": 2})
    assert ok2["status"] == "rewritten" and ok2[rj.REWRITE_FAILS_KEY] == 2
    # 契约错(old==new, 调用方责任) => failed 记账, daemon 不崩(fail-fast 面收进账里)
    h_same = _member_fixture(backup, b"m-same", old_root)
    same = rd._rewrite_member({"bt_backup": str(backup), "src": old_root, "dst": old_root}, {"hash_v1": h_same}, None)
    assert same["status"] == "failed" and "无改写差异" in same["error"]


def test_rewrite_member_relative_keys_resolved_via_profile_base(tmp_path):
    # E2c 接线(issue 26-11-07-2336): spec.bt_backup 嵌套布局自动推导 profile base,
    # 相对形态键改写出账 rewritten(同盘部署收尾链恢复收敛)
    backup = tmp_path / "prof" / "qB" / "data" / "BT_backup"
    backup.mkdir(parents=True)
    old_root = str(tmp_path / "prof" / "src")
    new_root = str(tmp_path / "prof" / "dst")
    spec = {"bt_backup": str(backup), "src": old_root, "dst": new_root}
    info = {b"name": b"m-rel", b"piece length": 16384, b"pieces": b"\x00" * 20, b"length": 1}
    torrent = frmod.bencode({b"announce": b"http://tracker.example/ann", b"info": info})
    v1, _, _ = compute_infohashes(torrent)
    val = {
        b"save_path": rb"..\src",  # base = <tmp>\prof\qB -> 上弹一段即旧根
        b"qBt-savePath": b"../src/member",
        b"qBt-name": b"m-rel",
        b"completed": 1,
    }
    (backup / f"{v1}.torrent").write_bytes(torrent)
    fp = backup / f"{v1}.fastresume"
    fp.write_bytes(frmod.bencode(val))

    rec = rd._rewrite_member(spec, {"hash_v1": v1}, None)
    assert rec["status"] == "rewritten" and set(rec["keys"]) == {"save_path", "qBt-savePath"}
    back = frmod.load_fastresume(fp)
    assert back[b"save_path"] == new_root.encode("utf-8")
    # 产物后缀分隔符 = base 根分隔符(随宿主 tmp_path 风味, Linux CI 下为正斜杠)
    sep = "\\" if not new_root.startswith("/") else "/"
    assert back[b"qBt-savePath"] == (new_root + sep + "member").encode("utf-8")
    # 重放: 改写产物(绝对新根)重跑 => already 出账, 字节零变化(黄金法则 1)
    fp_bytes = fp.read_bytes()
    rec2 = rd._rewrite_member(spec, {"hash_v1": v1}, None)
    assert rec2["status"] == "already" and "save_path" in rec2["keys"]
    assert fp.read_bytes() == fp_bytes


def test_scan_jobs_filters_instance_optin_and_terminal(tmp_path):
    data_dir = str(tmp_path / "data")
    backup = tmp_path / "BT_backup"
    h1 = _member_fixture(backup, b"m-1", str(tmp_path / "src"))
    _write_job(tmp_path, data_dir, "job-mine", [h1])  # 本实例 + opt-in
    _write_job(tmp_path, data_dir, "job-other-host", [h1], host="10.0.0.9")  # 别实例
    _write_job(tmp_path, data_dir, "job-other-port", [h1], port=1)  # 别实例
    _write_job(tmp_path, data_dir, "job-oldchain", [h1], bt_backup=False)  # 旧链 spec(无 opt-in)
    _write_job(tmp_path, data_dir, "job-terminal", [h1], journal_phase="cancelled")  # 已收口
    _write_job(tmp_path, data_dir, "job-broken", [h1], src="", dst="")  # 残缺 spec
    (Path(data_dir) / "relocate" / "job-corrupt.spec.json").write_bytes(b"{not-json")  # 坏 spec
    _write_job(tmp_path, data_dir, "job-badport", [h1], port="abc")  # port 非数值
    # 翻相 flag: 全员收口 + 账在 + 相位未翻
    _write_job(tmp_path, data_dir, "job-settled", [h1])
    rj.record_rewrites(data_dir, "job-settled", {h1: {"status": "rewritten"}}, ts=1.0)

    jobs = {j["job_id"]: j for j in rd._scan_jobs(data_dir, HOST, PORT)}
    assert set(jobs) == {"job-mine", "job-settled"}
    assert [rj.member_key(m) for m in jobs["job-mine"]["pending"]] == [h1]
    assert jobs["job-settled"]["pending"] == [] and jobs["job-settled"]["flip"] is True


def test_owner_beat_throttles_touch(tmp_path, monkeypatch):
    d = str(tmp_path)
    owner = rd._Owner(d, "k", 7, heartbeat=10.0)
    assert owner.claim(1000.0, max_age=60.0) == "claimed"
    assert rj.read_daemon_state(d, "k")["ts"] == 1000.0
    assert owner.beat(1005.0) is True, "间隔未到: 自检过但不写"
    assert rj.read_daemon_state(d, "k")["ts"] == 1000.0
    assert owner.beat(1010.5) is True, "到点 touch"
    assert rj.read_daemon_state(d, "k")["ts"] == 1010.5
    # 被退位: 自检先于 touch => False 且新主记录原样
    rj.write_daemon_state(d, "k", 99, ts=1.0)
    assert owner.beat(1020.0) is False
    assert rj.read_daemon_state(d, "k")["pid"] == 99
    # 记录异常消失: 重新落盘认主(daemon 不因账文件消失而白死)
    os.remove(rj.daemon_state_path(d, "k"))
    assert owner.beat(1030.0) is True
    assert rj.read_daemon_state(d, "k")["pid"] == 7
    # touch 被拒(退位落在自检读与落账写的微秒间隙)⇒ beat False(写侧闸兜底)
    monkeypatch.setattr(rd.rj, "touch_daemon_state", lambda *a, **k: False)
    assert owner.beat(1040.0) is False


def test_run_flips_settled_phase_without_window(tmp_path, monkeypatch):
    """全员已收口而相位未翻(窗口中崩溃错过翻相)+ qB 在线 => 只补翻 rewritten, 零进窗零改写
    (journal 写不限窗口, D13; fastresume 落盘才限窗口, N1)"""
    tmp_path.joinpath("src").mkdir()
    tmp_path.joinpath("dst").mkdir()
    backup = tmp_path / "BT_backup"
    old_root = str(tmp_path / "src")
    h1 = _member_fixture(backup, b"m-1", old_root, rewritten_to=str(tmp_path / "dst"))
    data_dir = str(tmp_path / "data")
    _write_job(tmp_path, data_dir, "job-1", [h1], src=old_root, dst=str(tmp_path / "dst"))
    rj.record_rewrites(data_dir, "job-1", {h1: {"status": "rewritten"}}, ts=1.0)
    state = {"up": True}
    _stub_qb(monkeypatch, state)
    calls = {"n": 0}
    real = rd.fastresume.retarget

    def _count(*a, **k):
        calls["n"] += 1
        return real(*a, **k)

    monkeypatch.setattr(rd.fastresume, "retarget", _count)
    assert _run(data_dir) == "idle"
    assert calls["n"] == 0, "零进窗零改写"
    assert rj.read_journal(data_dir, "job-1")["phase"] == rj.PHASE_REWRITTEN
    assert rj.read_daemon_state(data_dir, rj.instance_key(HOST, PORT)) is None, "空闲退出按归属释放"


def test_run_waits_for_stable_window_before_window(tmp_path, monkeypatch):
    """进窗第三证(稳定窗): 下线须持续满 stable 才动手(语义照搬 guardian)——窗口短于稳定窗
    (关机风暴形态)错过无害, 零落盘(N9 断言「窗口 < 稳定窗 => 错过、下一窗口收敛」的单元面)"""
    tmp_path.joinpath("src").mkdir()
    tmp_path.joinpath("dst").mkdir()
    backup = tmp_path / "BT_backup"
    old_root = str(tmp_path / "src")
    h1 = _member_fixture(backup, b"m-1", old_root)
    before = _fr_path(tmp_path, h1).read_bytes()
    data_dir = str(tmp_path / "data")
    _write_job(tmp_path, data_dir, "job-1", [h1], src=old_root, dst=str(tmp_path / "dst"))
    state = {"up": False}  # 全程「下线」, 但从未持续满 stable
    _stub_qb(monkeypatch, state)
    assert _run(data_dir, stable=100.0, max_wait=25.0) == "timeout", "稳定窗未满不进窗"
    assert rj.read_rewrites(data_dir, "job-1") == {}
    assert _fr_path(tmp_path, h1).read_bytes() == before


def test_run_grace_exit_after_idle_period(tmp_path, monkeypatch):
    data_dir = str(tmp_path / "data")
    state = {"up": True}
    _stub_qb(monkeypatch, state)
    # 无任何 job: 宽限 30s 计满才退(grace=30 < max_wait=100 => idle 先到, 非 timeout)
    assert _run(data_dir, grace=30.0, max_wait=100.0, clock=_clock_gen(step=10.0)) == "idle"
    assert rj.read_daemon_state(data_dir, rj.instance_key(HOST, PORT)) is None


def test_cli_main_idle_exit_zero(tmp_path, capsys):
    data_dir = str(tmp_path / "data")
    code = rd.main(["--data-dir", data_dir, "--host", HOST, "--port", str(PORT), "--grace", "0", "--poll", "0"])
    assert code == 0
    out = capsys.readouterr().out
    assert "idle" in out and HOST in out


def test_cli_main_timeout_exit_one(tmp_path, monkeypatch, capsys):
    tmp_path.joinpath("src").mkdir()
    tmp_path.joinpath("dst").mkdir()
    backup = tmp_path / "BT_backup"
    old_root = str(tmp_path / "src")
    h1 = _member_fixture(backup, b"m-1", old_root)
    data_dir = str(tmp_path / "data")
    _write_job(tmp_path, data_dir, "job-1", [h1], src=old_root, dst=str(tmp_path / "dst"))
    state = {"up": True}  # qB 在线无窗可进
    _stub_qb(monkeypatch, state)
    code = rd.main(["--data-dir", data_dir, "--host", HOST, "--port", str(PORT), "--poll", "0", "--max-wait", "20"])
    assert code == 1, "timeout 档退出码 1"
    assert "timeout" in capsys.readouterr().out


def test_module_main_entry_exits_with_result_code(tmp_path, monkeypatch, recwarn):
    """python -m 入口: main() 结论码经 sys.exit 上抛(空载 idle 档退出码 0)

    文件级 `from auto_qb.tools import recycle_daemon as rd` 已让目标模块先入 sys.modules,
    runpy.run_module(3.12+) 会据此抛 RuntimeWarning('found in sys.modules ... unpredictable
    behaviour')。按 `python -m` 的首次执行语义, 运行前摘掉该条目(monkeypatch 在 teardown
    自动还原), warning 根因消除且入口仍真跑一遍; 包属性仍指向原模块, 其余用例的 rd 不受影响。
    recwarn 断言把「零告警」钉成守阵 —— 删掉 delitem 即回归判红(红验已验)。
    """
    import runpy
    import sys

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "recycle_daemon", "--data-dir",
            str(tmp_path / "none"), "--host", HOST, "--port",
            str(PORT), "--grace", "0", "--poll", "0"
        ],
    )
    monkeypatch.delitem(sys.modules, "auto_qb.tools.recycle_daemon", raising=False)
    with pytest.raises(SystemExit) as ei:
        runpy.run_module("auto_qb.tools.recycle_daemon", run_name="__main__")
    assert ei.value.code == 0
    assert not [
        w for w in recwarn if issubclass(w.category, RuntimeWarning) and "found in sys.modules" in str(w.message)
    ], "python -m 入口执行期不得再出现 sys.modules 抢先加载告警(delitem 修复回潮)"


# ---------------------------------------------------------------------------
# 竞态矩阵
# ---------------------------------------------------------------------------


def test_qb_revives_before_first_write_zero_member_writes(tmp_path, monkeypatch):
    """[抢先回升/零写入] 进窗后第一次落盘之前 qB 回升 => 本轮放弃, 零成员改写, 账面零 records

    回升时机桩: 进程名册第 2 次现读(第一次=主循环下线判定, 第二次=窗口拍级复验)时把
    state 翻成「在」—— 名册现读正是 N1 铁律的守门点, 翻转落在两次现读之间即「写前复验
    拦住回升」。流程确定性由桩保证, 不依赖真实时序。"""
    tmp_path.joinpath("src").mkdir()
    tmp_path.joinpath("dst").mkdir()
    backup = tmp_path / "BT_backup"
    old_root = str(tmp_path / "src")
    h1 = _member_fixture(backup, b"m-1", old_root)
    before = _fr_path(tmp_path, h1).read_bytes()
    data_dir = str(tmp_path / "data")
    _write_job(tmp_path, data_dir, "job-1", [h1], src=old_root, dst=str(tmp_path / "dst"))

    state = {"up": False}
    _stub_qb(monkeypatch, state)
    roster = {"n": 0}

    def _roster():
        roster["n"] += 1
        if roster["n"] >= 2:
            state["up"] = True  # 第二次名册现读时 qB 已回升
        # 评审 #6 合取语义: 名册与 state 联动(down = 名册可用但无 qB, up = 名册见 qB) ——
        # 旧桩恒含 qbittorrent, 在合取判定下窗永不开, 进窗/回升路径覆盖不到
        return ("qbittorrent.exe", ) if state["up"] else ("explorer.exe", )

    monkeypatch.setattr(rd, "_qb_process_names", _roster)
    assert _run(data_dir, max_wait=60.0) == "timeout", "回升后无窗可进, max_wait 收束"
    assert rj.read_rewrites(data_dir, "job-1") == {}, "零成员记账"
    assert _fr_path(tmp_path, h1).read_bytes() == before, "零落盘"


def test_qb_revives_mid_sequence_abandons_rest(tmp_path, monkeypatch):
    """[抢先回升/中途] A 改写落账后 qB 回升 => B 不再尝试(不落账不落盘); A 留存(N4 自愈面)"""
    tmp_path.joinpath("src").mkdir()
    tmp_path.joinpath("dst").mkdir()
    backup = tmp_path / "BT_backup"
    old_root = str(tmp_path / "src")
    new_root = str(tmp_path / "dst")
    h_a = _member_fixture(backup, b"m-a", old_root)
    h_b = _member_fixture(backup, b"m-b", old_root)
    b_before = _fr_path(tmp_path, h_b).read_bytes()
    data_dir = str(tmp_path / "data")
    _write_job(tmp_path, data_dir, "job-1", [h_a, h_b], src=old_root, dst=new_root)

    state = {"up": False}
    _stub_qb(monkeypatch, state)
    real = rd.fastresume.retarget

    def _retarget_then_revive(backup_dir, h1, h2, old, new):
        rep = real(backup_dir, h1, h2, old, new)
        if h1 == h_a:
            state["up"] = True  # A 刚落盘 qB 即回升
        return rep

    monkeypatch.setattr(rd.fastresume, "retarget", _retarget_then_revive)
    assert _run(data_dir, max_wait=60.0) == "timeout"
    rw = rj.read_rewrites(data_dir, "job-1")
    assert set(rw) == {h_a} and rw[h_a]["status"] == "rewritten", "只 A 记账"
    d = frmod.load_fastresume(_fr_path(tmp_path, h_a))
    assert d[b"save_path"] == (new_root + "\\m-a").encode("utf-8")
    assert d[b"qBt-savePath"] == (new_root.replace("\\", "/") + "/m-a").encode("utf-8")
    assert _fr_path(tmp_path, h_b).read_bytes() == b_before, "B 零落盘"
    assert rj.read_journal(data_dir, "job-1")["phase"] == "armed", "未收口不翻相"


def test_crash_mid_window_journal_consistent_and_next_round_replays(tmp_path, monkeypatch):
    """[半途崩溃] A 收口后 daemon 终止(B 持续失败至 max_wait => timeout 模拟进程死亡)
    => 账面一致(A rewritten / B failed 且计数在账); 修好 B 后新 daemon 重放: 只试 B
    (A 零重试), B 收口, 相位翻 rewritten"""
    tmp_path.joinpath("src").mkdir()
    tmp_path.joinpath("dst").mkdir()
    backup = tmp_path / "BT_backup"
    old_root = str(tmp_path / "src")
    h_a = _member_fixture(backup, b"m-a", old_root)
    h_b = _member_fixture(backup, b"m-b", old_root)
    (_fr_path(tmp_path, h_b)).write_bytes(b"garbage-not-bencode")  # B 坏样本: 持续失败
    data_dir = str(tmp_path / "data")
    _write_job(tmp_path, data_dir, "job-1", [h_a, h_b], src=old_root, dst=str(tmp_path / "dst"))

    state = {"up": False}
    _stub_qb(monkeypatch, state)
    calls = {"a": 0, "b": 0}
    real = rd.fastresume.retarget

    def _count(backup_dir, h1, h2, old, new):
        calls["a" if h1 == h_a else "b"] += 1
        return real(backup_dir, h1, h2, old, new)

    monkeypatch.setattr(rd.fastresume, "retarget", _count)
    assert _run(data_dir, max_wait=200.0) == "timeout", "daemon 终止(崩溃替身)"
    rw = rj.read_rewrites(data_dir, "job-1")
    assert rw[h_a]["status"] == "rewritten", "A 的账已落(崩溃前)"
    assert rw[h_b]["status"] == "failed" and rw[h_b][rj.REWRITE_FAILS_KEY] >= 2, "B 失败计数进账"
    assert rj.read_journal(data_dir, "job-1")["phase"] == "armed", "未收口不翻相"
    a_calls_after_crash = calls["a"]

    # 新 daemon 起来(账在, 崩溃无痕): 修好 B, 重放只试 B
    good = {
        b"save_path": (old_root + "\\m-b").encode("utf-8"),
        b"qBt-savePath": (old_root.replace("\\", "/") + "/m-b").encode("utf-8"),
        b"completed": 1,
    }
    (_fr_path(tmp_path, h_b)).write_bytes(frmod.bencode(good))
    assert _run(data_dir) == "idle"
    assert calls["a"] == a_calls_after_crash, "A 已收口, 零重试"
    assert calls["b"] >= 2, "B 被重放"
    rw = rj.read_rewrites(data_dir, "job-1")
    assert rw[h_b]["status"] == "rewritten" and rw[h_b][rj.REWRITE_FAILS_KEY] >= 2, "计数承前不丢"
    assert rj.read_journal(data_dir, "job-1")["phase"] == rj.PHASE_REWRITTEN, "全收口翻相"


def test_replay_after_journal_loss_records_already(tmp_path, monkeypatch):
    """[重复重放] fastresume 已在目标值而账本清零 => retarget unchanged+already => 记 already
    出账, 文件字节零改动, 无 .bak 产生(黄金法则 1: 幂等重放零副作用)"""
    tmp_path.joinpath("src").mkdir()
    tmp_path.joinpath("dst").mkdir()
    backup = tmp_path / "BT_backup"
    old_root = str(tmp_path / "src")
    h1 = _member_fixture(backup, b"m-1", old_root, rewritten_to=str(tmp_path / "dst"))
    fr = _fr_path(tmp_path, h1)
    before = fr.read_bytes()
    data_dir = str(tmp_path / "data")
    _write_job(tmp_path, data_dir, "job-1", [h1], src=old_root, dst=str(tmp_path / "dst"))
    state = {"up": False}
    _stub_qb(monkeypatch, state)
    assert _run(data_dir) == "idle"
    rw = rj.read_rewrites(data_dir, "job-1")
    assert rw[h1]["status"] == "already", "已在目标值记 already(出账)"
    assert "save_path" in rw[h1]["keys"]
    assert fr.read_bytes() == before, "文件字节零改动"
    assert not fr.with_name(fr.name + ".bak").exists(), "未落盘即无 .bak"
    assert rj.read_journal(data_dir, "job-1")["phase"] == rj.PHASE_REWRITTEN


def test_window_retry_until_success_counts_failures(tmp_path, monkeypatch):
    """[窗口内重试] 瞬态故障(坏样本第一拍后自愈) => 窗口内第二拍改写成功(D8: 重试至成功),
    失败计数 1 进账不丢"""
    tmp_path.joinpath("src").mkdir()
    tmp_path.joinpath("dst").mkdir()
    backup = tmp_path / "BT_backup"
    old_root = str(tmp_path / "src")
    h1 = _member_fixture(backup, b"m-1", old_root)
    good_again = {
        b"save_path": (old_root + "\\m-1").encode("utf-8"),
        b"qBt-savePath": (old_root.replace("\\", "/") + "/m-1").encode("utf-8"),
        b"completed": 1,
    }
    (_fr_path(tmp_path, h1)).write_bytes(b"garbage-not-bencode")  # 先坏
    data_dir = str(tmp_path / "data")
    _write_job(tmp_path, data_dir, "job-1", [h1], src=old_root, dst=str(tmp_path / "dst"))
    state = {"up": False}
    _stub_qb(monkeypatch, state)
    calls = {"n": 0}
    real = rd.fastresume.retarget

    def _flaky(backup_dir, h1_, h2_, old, new):
        calls["n"] += 1
        try:
            return real(backup_dir, h1_, h2_, old, new)
        finally:
            if calls["n"] == 1:
                (_fr_path(tmp_path, h1)).write_bytes(frmod.bencode(good_again))  # 第一拍后自愈

    monkeypatch.setattr(rd.fastresume, "retarget", _flaky)
    assert _run(data_dir) == "idle"
    rw = rj.read_rewrites(data_dir, "job-1")
    assert rw[h1]["status"] == "rewritten"
    assert rw[h1][rj.REWRITE_FAILS_KEY] == 1, "失败计数进账且不丢"
    assert calls["n"] >= 2, "窗口内重试确有发生"
    assert rj.read_journal(data_dir, "job-1")["phase"] == rj.PHASE_REWRITTEN


def test_main_loop_cancel_mid_window_skips_rest(tmp_path, monkeypatch):
    """[取消即时生效] A 落账的同一间隙对账落终态 => B 写前现读见终态即弃(不落盘),
    终态相位不被 daemon 回退(前向合并)"""
    tmp_path.joinpath("src").mkdir()
    tmp_path.joinpath("dst").mkdir()
    backup = tmp_path / "BT_backup"
    old_root = str(tmp_path / "src")
    h_a = _member_fixture(backup, b"m-a", old_root)
    h_b = _member_fixture(backup, b"m-b", old_root)
    b_before = _fr_path(tmp_path, h_b).read_bytes()
    data_dir = str(tmp_path / "data")
    _write_job(tmp_path, data_dir, "job-1", [h_a, h_b], src=old_root, dst=str(tmp_path / "dst"))
    state = {"up": False}
    _stub_qb(monkeypatch, state)
    real_rec = rd.rj.record_rewrites

    def _rec_then_cancel(data_dir_, job_id, records, **kw):
        ok = real_rec(data_dir_, job_id, records, **kw)
        if ok and h_a in records:
            rj.write_journal(data_dir_, job_id, {"phase": "cancelled"})  # 对账同间隙收口
        return ok

    monkeypatch.setattr(rd.rj, "record_rewrites", _rec_then_cancel)
    assert _run(data_dir) == "idle"
    assert rj.read_journal(data_dir, "job-1")["phase"] == "cancelled", "终态不被回退"
    assert _fr_path(tmp_path, h_b).read_bytes() == b_before, "取消后 B 零落盘"


def test_deposed_old_daemon_self_checks_and_exits(tmp_path, monkeypatch):
    """[退位互斥] 新主 pid 抢占(纯文件写, 绝不 taskkill) => 旧 daemon 下一拍自检见外来
    pid 即 deposed 退出; 退出前零覆盖(新主记录原样), release 不误删新主记录"""
    data_dir = str(tmp_path / "data")
    foreign_pid = os.getpid() + 100000  # 外来 pid(只在文件里, 不探测不杀)
    foreign_ts = 123.0
    scan = {"n": 0}
    real_scan = rd._scan_jobs

    def _scan_then_preempt(data_dir_, host, port):
        n = scan["n"] + 1
        scan["n"] = n
        if n == 1:
            # "新 daemon" 在旧主第一拍扫描时抢占: 纯 pid 抢占(写文件)
            rj.write_daemon_state(data_dir_, rj.instance_key(HOST, PORT), foreign_pid, ts=foreign_ts)
        return real_scan(data_dir_, host, port)

    monkeypatch.setattr(rd, "_scan_jobs", _scan_then_preempt)
    assert _run(data_dir, grace=10.0**9) == "deposed", "旧主自检自杀"
    st = rj.read_daemon_state(data_dir, rj.instance_key(HOST, PORT))
    assert st["pid"] == foreign_pid and st["ts"] == foreign_ts, "旧主退出前零覆盖"
    assert scan["n"] >= 1


def test_deposed_at_window_pass_top_aborts_round(tmp_path, monkeypatch):
    """[退位互斥/窗口内] 新主在窗口会话中抢占(记账后落外来 pid) => 下一拍顶部自检即弃,
    整轮 deposed 收束, 不再碰任何成员"""
    tmp_path.joinpath("src").mkdir()
    tmp_path.joinpath("dst").mkdir()
    backup = tmp_path / "BT_backup"
    old_root = str(tmp_path / "src")
    h1 = _member_fixture(backup, b"m-1", old_root)
    data_dir = str(tmp_path / "data")
    key = rj.instance_key(HOST, PORT)
    _write_job(tmp_path, data_dir, "job-1", [h1], src=old_root, dst=str(tmp_path / "dst"))
    state = {"up": False}
    _stub_qb(monkeypatch, state)
    foreign_pid = os.getpid() + 200000
    real_rec = rd.rj.record_rewrites

    def _rec_then_preempt(data_dir_, job_id, records, **kw):
        ok = real_rec(data_dir_, job_id, records, **kw)
        if ok:
            rj.write_daemon_state(data_dir_, key, foreign_pid, ts=999.0)  # 新主抢占(纯文件写)
        return ok

    monkeypatch.setattr(rd.rj, "record_rewrites", _rec_then_preempt)
    assert _run(data_dir, grace=10.0**9) == "deposed", "拍顶自检自杀"
    rw = rj.read_rewrites(data_dir, "job-1")
    assert rw[h1]["status"] == "rewritten", "已落账部分留存"
    st = rj.read_daemon_state(data_dir, key)
    assert st["pid"] == foreign_pid and st["ts"] == 999.0, "退位者零覆盖"


def test_deposed_mid_window_member_beat_aborts(tmp_path, monkeypatch):
    """[退位互斥/成员拍] 抢占落在成员 A 检查与记账之间 => 成员 B 的拍级自检见外来 pid
    即整轮放弃, B 零触碰"""
    tmp_path.joinpath("src").mkdir()
    tmp_path.joinpath("dst").mkdir()
    backup = tmp_path / "BT_backup"
    old_root = str(tmp_path / "src")
    h_a = _member_fixture(backup, b"m-a", old_root)
    h_b = _member_fixture(backup, b"m-b", old_root)
    b_before = _fr_path(tmp_path, h_b).read_bytes()
    data_dir = str(tmp_path / "data")
    key = rj.instance_key(HOST, PORT)
    _write_job(tmp_path, data_dir, "job-1", [h_a, h_b], src=old_root, dst=str(tmp_path / "dst"))
    state = {"up": False}
    _stub_qb(monkeypatch, state)
    foreign_pid = os.getpid() + 300000
    real_wo = rd._window_open
    wo = {"n": 0}

    def _wo_then_preempt(host, port):
        wo["n"] += 1
        if wo["n"] == 2:  # 拍级(1)之后的成员级复验点: A 处理中途新主抢占
            rj.write_daemon_state(data_dir, key, foreign_pid, ts=999.0)
        return real_wo(host, port)

    monkeypatch.setattr(rd, "_window_open", _wo_then_preempt)
    assert _run(data_dir, grace=10.0**9) == "deposed"
    rw = rj.read_rewrites(data_dir, "job-1")
    assert set(rw) == {h_a}, "只 A 记账"
    assert _fr_path(tmp_path, h_b).read_bytes() == b_before, "B 零触碰"


def test_record_refused_when_terminal_lands_in_gap(tmp_path, monkeypatch):
    """收口落在写前检查与落账的间隙 => record_rewrites 拒收(False) => 该 job 立即放弃
    (协议级终态闸门在 daemon 侧的出口)"""
    tmp_path.joinpath("src").mkdir()
    tmp_path.joinpath("dst").mkdir()
    backup = tmp_path / "BT_backup"
    old_root = str(tmp_path / "src")
    h1 = _member_fixture(backup, b"m-1", old_root)
    data_dir = str(tmp_path / "data")
    _write_job(tmp_path, data_dir, "job-1", [h1], src=old_root, dst=str(tmp_path / "dst"))
    state = {"up": False}
    _stub_qb(monkeypatch, state)
    real_rec = rd.rj.record_rewrites

    def _rec_after_terminal(data_dir_, job_id, records, **kw):
        rj.write_journal(data_dir_, job_id, {"phase": "cancelled"})  # 主循环恰在间隙收口
        return real_rec(data_dir_, job_id, records, **kw)  # => False(终态拒收)

    monkeypatch.setattr(rd.rj, "record_rewrites", _rec_after_terminal)
    assert _run(data_dir) == "idle"
    assert rj.read_journal(data_dir, "job-1")["phase"] == "cancelled", "终态不被回退"


def test_run_already_running_healthy_watcher_untouched(tmp_path):
    data_dir = str(tmp_path / "data")
    key = rj.instance_key(HOST, PORT)
    rj.write_daemon_state(data_dir, key, os.getpid(), ts=1000.0)  # 健康 watcher(本进程必活)
    assert _run(data_dir) == "already_running"
    st = rj.read_daemon_state(data_dir, key)
    assert st["pid"] == os.getpid() and st["ts"] == 1000.0, "让路者零触碰"


def test_run_preempts_dead_pid_record(tmp_path, monkeypatch):
    data_dir = str(tmp_path / "data")
    key = rj.instance_key(HOST, PORT)
    rj.write_daemon_state(data_dir, key, 424242, ts=1000.0)  # 记录 pid 已死
    monkeypatch.setattr(rj, "_alive", lambda pid: pid == os.getpid())
    seen = {}
    real_scan = rd._scan_jobs

    def _snap(data_dir_, host, port):
        seen.setdefault("st", rj.read_daemon_state(data_dir_, key))  # 抢占落定后的记录
        return real_scan(data_dir_, host, port)

    monkeypatch.setattr(rd, "_scan_jobs", _snap)
    assert _run(data_dir) == "idle", "抢占后正常接管(空载宽限退出)"
    assert seen["st"]["pid"] == os.getpid(), "pid 抢占已落账"


def test_run_timeout_keeps_pending(tmp_path, monkeypatch):
    tmp_path.joinpath("src").mkdir()
    tmp_path.joinpath("dst").mkdir()
    backup = tmp_path / "BT_backup"
    old_root = str(tmp_path / "src")
    h1 = _member_fixture(backup, b"m-1", old_root)
    before = _fr_path(tmp_path, h1).read_bytes()
    data_dir = str(tmp_path / "data")
    _write_job(tmp_path, data_dir, "job-1", [h1], src=old_root, dst=str(tmp_path / "dst"))
    state = {"up": True}  # qB 在线: 无窗可进
    _stub_qb(monkeypatch, state)
    assert _run(data_dir, max_wait=40.0) == "timeout"
    assert rj.read_rewrites(data_dir, "job-1") == {}, "pending 原样"
    assert _fr_path(tmp_path, h1).read_bytes() == before
    assert rj.read_daemon_state(data_dir, rj.instance_key(HOST, PORT)) is None, "按归属释放"


# ---------------------------------------------------------------------------
# 覆盖率缺口清偿(26-11-07): journal 协议边角 / 进程名册跨平台支
# ---------------------------------------------------------------------------


def test_write_journal_refuses_nonterminal_over_terminal(tmp_path):
    """终态闸门: journal 已收口(done/cancelled)时非终态写被拒(False), 终态互覆仍放行"""
    assert rj.write_journal(str(tmp_path), "j1", {"phase": "done"}) is True
    assert rj.write_journal(str(tmp_path), "j1", {"phase": "armed"}) is False, "终态不被非终态回退"
    assert rj.write_journal(str(tmp_path), "j1", {"phase": "cancelled"}) is True, "终态互覆 last-writer-wins"


def test_alive_posix_fallback_paths(monkeypatch):
    """_alive POSIX 支: os.kill 探活 / 进程不在 / 信号不支持, 三路都有归宿(Windows 桩 os.name)"""
    monkeypatch.setattr(rj.os, "name", "posix")
    monkeypatch.setattr(rj.os, "kill", lambda pid, sig: None)
    assert rj._alive(os.getpid()) is True

    def _no_proc(pid, sig):
        raise OSError(3, "no such process")

    monkeypatch.setattr(rj.os, "kill", _no_proc)
    assert rj._alive(999999) is False

    def _unsupported(pid, sig):
        raise AttributeError("kill unsupported")

    monkeypatch.setattr(rj.os, "kill", _unsupported)
    assert rj._alive(1) is False


def test_verify_replays_of_bad_shape_is_zero(tmp_path):
    """verify_replays 坏形(非数字) => 0(从未重放), 不抛"""
    rj.write_journal(str(tmp_path), "j1", {"phase": "armed", "verify_replays": "not-a-number"})
    assert rj.verify_replays_of(str(tmp_path), "j1") == 0


def test_reset_rewrites_terminal_refused_and_keeps_unsettled(tmp_path):
    """重放入口: 终态拒(-1); settled 清回 pending 时非 settled 记录原样保留"""
    assert rj.reset_rewrites(str(tmp_path), "gone", ts=1.0) == 0, "无 journal: 无 settled 可重置(幂等 0)"
    rj.write_journal(str(tmp_path), "j1", {"phase": "done"})
    assert rj.reset_rewrites(str(tmp_path), "j1", ts=1.0) == -1, "终态拒重放"
    rj.write_journal(
        str(tmp_path),
        "j2",
        {
            "phase": "rewritten",
            "rewrites": {
                "HA": {
                    "status": "rewritten"
                },
                "HB": {
                    "status": "failed",
                    "error": "x"
                },
            },
        },
    )
    n = rj.reset_rewrites(str(tmp_path), "j2", ts=2.0)
    assert n == 1, "只有 settled(rewritten)被清"
    rewrites = rj.read_rewrites(str(tmp_path), "j2")
    assert rewrites["HA"]["status"] == rj.REWRITE_RESET_STATUS and rewrites["HA"]["prev_status"] == "rewritten"
    assert rewrites["HB"] == {"status": "failed", "error": "x"}, "非 settled 记录原样保留"


def test_tasklist_ignores_non_quoted_lines(monkeypatch):
    """tasklist CSV 解析: 非引号开头行(表头/空行)跳过, 只收引号内映像名"""
    class _Out:
        stdout = '"qbittorrent.exe","1234","Console","1"\nheader-without-quotes\n'

    monkeypatch.setattr(rd.subprocess, "run", lambda *a, **kw: _Out())
    assert rd._names_from_tasklist() == ("qbittorrent.exe", )


def test_names_from_proc_tolerates_unreadable_comm(monkeypatch, tmp_path):
    """/proc 名册: 非数字项跳过; comm 打不开(权限/消失)逐项跳过不炸, 可读项照常收"""
    monkeypatch.setattr(rd.os, "listdir", lambda p: ["1", "self", "2"])
    # pid 1 的 comm 重定向到已知内容的真实文件: Windows 无 /proc, 不重定向则可读支在
    # 主平台空转(名册空 tuple, all(()) 恒真断言失效), 重定向后两平台都断到非空名册
    comm1 = tmp_path / "comm1"
    comm1.write_text("systemd\n", encoding="utf-8")
    real_open = open

    def _open(path, *a, **kw):
        p = str(path).replace("\\", "/")
        if p.endswith("/comm"):
            if "/2/" in p:
                raise OSError(13, "permission")
            if "/1/" in p:
                return real_open(str(comm1), *a, **kw)
        return real_open(path, *a, **kw)

    import builtins

    monkeypatch.setattr(builtins, "open", _open)
    names = rd._names_from_proc()
    assert isinstance(names, tuple)
    # 真断言(评审 #7: 原行 "X or True" 恒真): 可读项(pid 1 重定向文件)收进名册, 不可读
    # 项(拒读的 pid 2)跳过, 不产空串垃圾项 —— 两平台名册均非空, 断言不再空转
    assert names == ("systemd", )


def test_qb_process_names_dispatches_non_windows(monkeypatch):
    """进程名册分派: 非 Windows 且无 /proc -> ps 支; 非 Windows 且有 /proc -> proc 支"""
    monkeypatch.setattr(rd.os, "name", "posix")
    monkeypatch.setattr(rd.os.path, "isdir", lambda p: False)
    monkeypatch.setattr(rd, "_names_from_ps", lambda: ("ps-qbittorrent-nox", ))
    assert rd._qb_process_names() == ("ps-qbittorrent-nox", )
    monkeypatch.setattr(rd.os.path, "isdir", lambda p: True)
    monkeypatch.setattr(rd, "_names_from_proc", lambda: ("proc-qbittorrent", ))
    assert rd._qb_process_names() == ("proc-qbittorrent", )


def test_proc_absent_dual_evidence_and_roster_fallback(monkeypatch, caplog):
    """证一判定(评审 #6): 名册可用时「进程不在 AND 端口拒连」双判合取 —— 端口拒连只证明
    WebUI 不可达, 不证明进程不在; 旧实现端口短路恒 True, qB 存活但 WebUI 不可达时假阳性
    进窗, daemon 在 qB 运行期改写 fastresume(N1 零写入被破)"""
    port_state = {"refused": True}
    monkeypatch.setattr(rd, "_port_refused", lambda host, port, timeout=1.0: port_state["refused"])
    # 名册见 qB + 端口拒连 => False(评审 #6 核心支: 不进窗)
    assert rd._proc_absent(("qbittorrent.exe", ), "127.0.0.1", 8080) is False
    # 名册见 qB + 端口可连 => False
    port_state["refused"] = False
    assert rd._proc_absent(("qbittorrent.exe", ), "127.0.0.1", 8080) is False
    # 名册无 qB + 端口可连 => False(端口证不成立)
    assert rd._proc_absent(("chrome.exe", ), "127.0.0.1", 8080) is False
    # 名册无 qB + 端口拒连 => True(合取成立; qB 真死两证自然同向, 窗口可用性不受损)
    port_state["refused"] = True
    assert rd._proc_absent(("chrome.exe", ), "127.0.0.1", 8080) is True
    # 名册不可用(空)+ 端口拒连 => 端口单证 True, 但告警降级留痕(证据链弱化不许静默)
    with caplog.at_level(logging.WARNING, logger="auto_qb.tools.recycle_daemon"):
        assert rd._proc_absent((), "127.0.0.1", 8080) is True
    assert any("名册不可用" in r.message for r in caplog.records), caplog.text
    # 名册不可用 + 端口可连 => False(端口在服务, 不告警)
    caplog.clear()
    port_state["refused"] = False
    assert rd._proc_absent((), "127.0.0.1", 8080) is False
    assert not any("名册不可用" in r.message for r in caplog.records)
    # 无端口可判(port=0): 退回名册单证(旧行为, 兼容无端口场景)
    assert rd._proc_absent(("chrome.exe", ), "", 0) is True
    assert rd._proc_absent(("qbittorrent.exe", ), "", 0) is False
    # 无端口且无名册 => 未证明(保守 False, 旧口径「判不出不算已退出」不变)
    assert rd._proc_absent((), "", 0) is False


def test_spec_retarget_mid_window_rewrites_remaining_to_new_dst(tmp_path, monkeypatch):
    """[supersede 即时生效/评审 #4] 窗口中段 spec.dst 被改道(retarget_spec 不需 qB 在线)
    => 剩余成员按新 dst 改写; 旧实现沿用窗口 scan 快照会把剩余成员写旧 dst(改写方向错)。
    另: spec 现读失败(被并发重写撕态) => 本 job 本拍放弃, 绝不拿旧快照改写。"""
    tmp_path.joinpath("src").mkdir()
    tmp_path.joinpath("dst1").mkdir()
    tmp_path.joinpath("dst2").mkdir()
    backup = tmp_path / "BT_backup"
    old_root = str(tmp_path / "src")
    dst1, dst2 = str(tmp_path / "dst1"), str(tmp_path / "dst2")
    h_a = _member_fixture(backup, b"m-a", old_root)
    h_b = _member_fixture(backup, b"m-b", old_root)
    data_dir = str(tmp_path / "data")
    _write_job(tmp_path, data_dir, "job-1", [h_a, h_b], src=old_root, dst=dst1)
    state = {"up": False}
    _stub_qb(monkeypatch, state)
    real = rd.fastresume.retarget

    def _retarget_then_redirect(backup_dir, h1, h2, old, new):
        # A 改写落盘的同一间隙, supersede 改道 spec.dst(dst1 -> dst2; 账面段不需 qB 在线)
        assert new == dst1, "前置: 改道发生在窗口 scan 之后, 本拍仍按 scan 快照的目标"
        out = real(backup_dir, h1, h2, old, new)
        assert rj.retarget_spec(data_dir, "job-1", dst2)
        return out

    calls = {"n": 0}

    def _hook(backup_dir, h1, h2, old, new):
        calls["n"] += 1
        if calls["n"] == 1:
            return _retarget_then_redirect(backup_dir, h1, h2, old, new)
        return real(backup_dir, h1, h2, old, new)

    monkeypatch.setattr(rd.fastresume, "retarget", _hook)
    assert _run(data_dir) == "idle"
    assert rj.read_spec(data_dir, "job-1")["dst"] == dst2, "改道已落盘"
    rw = rj.read_rewrites(data_dir, "job-1")
    assert rw[h_a]["status"] == "rewritten", "A: 改道前按当时账面 dst1 改写(时序正确)"
    assert rw[h_b]["status"] == "rewritten", "B: 改道后必须按新 dst 改写"
    fr_b = _fr_path(tmp_path, h_b)
    val, _pos = frmod.bdecode(fr_b.read_bytes())
    assert val[b"save_path"] == (dst2 + "\\m-b").encode("utf-8"), "B 落到新 dst(旧实现会写 dst1)"
    assert val[b"qBt-savePath"] == (dst2.replace("\\", "/") + "/m-b").encode("utf-8")
    fr_a = _fr_path(tmp_path, h_a)
    val_a, _pos = frmod.bdecode(fr_a.read_bytes())
    assert val_a[b"save_path"] == (dst1 + "\\m-a").encode("utf-8"), "A 维持改道前的 dst1(已写部分不追改)"


def test_spec_unreadable_mid_window_skips_job_without_stale_rewrite(tmp_path, monkeypatch):
    """spec 现读失败(撕态/被删) => 本 job 本拍放弃, 不拿窗口 scan 快照改写(评审 #4 容错支)"""
    tmp_path.joinpath("src").mkdir()
    tmp_path.joinpath("dst").mkdir()
    backup = tmp_path / "BT_backup"
    old_root = str(tmp_path / "src")
    h1 = _member_fixture(backup, b"m-1", old_root)
    data_dir = str(tmp_path / "data")
    _write_job(tmp_path, data_dir, "job-1", [h1], src=old_root, dst=str(tmp_path / "dst"))
    state = {"up": False}
    _stub_qb(monkeypatch, state)
    real_read_spec = rj.read_spec
    spec_calls = {"n": 0}

    def _flaky_spec(dd, job_id):
        spec_calls["n"] += 1
        if spec_calls["n"] <= 1:
            return real_read_spec(dd, job_id)  # 窗口 scan 时 spec 还在
        return None  # 窗口内逐成员现读: 撕态/被删

    monkeypatch.setattr(rd.rj, "read_spec", _flaky_spec)
    assert _run(data_dir, max_wait=200.0) == "timeout", "spec 恒读不到 => 放弃本 job(pending 留守), max_wait 兜底"
    assert spec_calls["n"] >= 2, "窗口内确有逐成员现读(非只用 scan 快照)"
    rw = rj.read_rewrites(data_dir, "job-1")
    assert not rw, "零改写零落账: 绝不拿旧快照改写(下一窗口按新账重放)"
    assert not (rj.read_journal(data_dir, "job-1") or {}), "零建账(从未落过改写记录)"


# ---------------------------------------------------------------------------
# 观测面(W1a, 计划 26-11-10-0318 §03.1/§03.4): obs 账 helper + 观测通道函数族
# 全桩化: 不起真进程、不回连真端口; netstat/PowerShell 用样例输出桩, /proc 用假树
# ---------------------------------------------------------------------------

LOG_RD = "auto_qb.tools.recycle_daemon"

# 中文 Windows netstat 实测样例(数据行恒 ASCII, 表头本地化; 04:07 本机探针逐列核对;
# [::] IPv6 行给独立端口+pid —— 同端口同 pid 会与 v4 行合并, IPv6 行解析破坏不可判红)
NETSTAT_ZH = (
    "\n"
    "活动连接\n"
    "\n"
    "  协议  本地地址          外部地址        状态           PID\n"
    "  TCP    0.0.0.0:36596         0.0.0.0:0              LISTENING       12345\n"
    "  TCP    127.0.0.1:36596       127.0.0.1:52341        ESTABLISHED     12345\n"
    "  TCP    [::]:36597            [::]:0                 LISTENING       7777\n"
    "  TCP    0.0.0.0:135           0.0.0.0:0              LISTENING       9876\n"
)
NETSTAT_EN = (
    "\n"
    "Active Connections\n"
    "\n"
    "  Proto  Local Address          Foreign Address        State           PID\n"
    "  TCP    192.168.1.5:36596      0.0.0.0:0              LISTENING       12345\n"
    "  TCP    192.168.1.5:36598      192.168.1.5:443        TIME_WAIT       0\n"
    "  UDP    0.0.0.0:5353           *:*                                    5678\n"
)


def _stub_stdout(monkeypatch, stdout):
    """subprocess.run 桩: 只回给定 stdout(returncode=0), 不起真进程; 返回记录最近一次
    调用 kwargs 的 dict, 供断言编码/超时钉法(encoding/errors/timeout 回归防线)"""
    calls = {}

    def _run(*args, **kwargs):
        calls.clear()
        calls.update(kwargs)
        return mock.MagicMock(returncode=0, stderr="", stdout=stdout)

    monkeypatch.setattr(rd.subprocess, "run", _run)
    return calls


def _stub_proc_open(monkeypatch, mapping):
    """builtins.open 桩: 命中 mapping 的路径回 StringIO(或抛 mapping 里的异常实例),
    其余走真 open(仿 test_names_from_proc_tolerates_unreadable_comm 的重定向造法)"""
    real_open = open

    def _open(path, *a, **kw):
        p = str(path).replace("\\", "/")
        if p in mapping:
            v = mapping[p]
            if isinstance(v, BaseException):
                raise v
            return io.StringIO(v)
        return real_open(path, *a, **kw)

    monkeypatch.setattr(builtins, "open", _open)


def test_obs_write_read_roundtrip_and_full_replace(tmp_path):
    d = str(tmp_path)
    payload = {
        "host": "127.0.0.1",
        "port": 8080,
        "owner": {
            "pid": 4242,
            "ct": 100.0,
            "ts": 110.0
        },
        "absorbed": [{
            "pid": 7,
            "ct": 90.0,
            "ts": 105.0
        }],
        "ts": 120.0,
    }
    assert rj.write_obs(d, "k", payload) is True
    st = rj.read_obs(d, "k")
    assert st["schema_version"] == rj.OBS_SCHEMA_VERSION == 1, "schema_version 写侧强制钉上"
    assert st["host"] == "127.0.0.1" and st["port"] == 8080 and st["ts"] == 120.0
    assert st["owner"] == {"pid": 4242, "ct": 100.0, "ts": 110.0}
    assert st["absorbed"] == [{"pid": 7, "ct": 90.0, "ts": 105.0}]
    # ts 缺省取挂钟(SYSTEM_CLOCK 单点); 路径与 daemon.json 同家族(实例键复用)
    assert rj.write_obs(d, "k2", {"host": "h", "port": 2, "owner": None, "absorbed": []}) is True
    st2 = rj.read_obs(d, "k2")
    assert isinstance(st2["ts"], float) and st2["ts"] > 0
    assert rj.obs_path(d, rj.instance_key("127.0.0.1", 8080)).endswith("obs-127.0.0.1_8080.json")
    # 新写入即全量替换: host/port 换实例 => 旧 owner/absorbed 零继承(注释语义, 这里钉行为)
    assert rj.write_obs(d, "k", {"host": "10.0.0.9", "port": 9999, "owner": None, "absorbed": [], "ts": 200.0}) is True
    st = rj.read_obs(d, "k")
    assert st["host"] == "10.0.0.9" and st["port"] == 9999 and st["ts"] == 200.0
    assert st["owner"] is None and st["absorbed"] == []


def test_obs_read_missing_or_bad_shape_is_none(tmp_path):
    """缺文件/schema_version 不符(含 bool 冒充 1)/host 非空 str 闸/port 正 int 闸/owner 或
    absorbed 形不符(混型反例: pid="4242"/pid=True/ct="1e3"/ts=True)/absorbed 键缺失/ts 非正
    数值/整文件非 dict => None(半残记录不冒充证据, 保守退全机口径)"""
    d = str(tmp_path)
    assert rj.read_obs(d, "none") is None, "缺文件 => None"
    rj.write_obs(d, "ok", {"host": "h", "port": 1, "owner": None, "absorbed": [], "ts": 1.0})
    assert rj.read_obs(d, "ok") is not None
    # int 形 ct/ts 与 float 形同收(严格判型排的是混型, 不是 int)
    rj.write_obs(
        d, "ok2", {
            "host": "h",
            "port": 1,
            "owner": {
                "pid": 4,
                "ct": 1,
                "ts": 2
            },
            "absorbed": [{
                "pid": 5,
                "ct": 1.5,
                "ts": 2.5
            }],
            "ts": 3
        }
    )
    assert rj.read_obs(d, "ok2") is not None
    bad_bodies = [
        {
            "schema_version": 99,
            "host": "h",
            "port": 1,
            "owner": None,
            "absorbed": [],
            "ts": 1.0
        },  # 版本不符
        {
            "schema_version": True,
            "host": "h",
            "port": 1,
            "owner": None,
            "absorbed": [],
            "ts": 1.0
        },  # 版本 bool 冒充 1
        {
            "host": "h",
            "port": 1,
            "owner": None,
            "absorbed": [],
            "ts": 1.0
        },  # 版本缺失
        {
            "schema_version": 1,
            "port": 1,
            "owner": None,
            "absorbed": [],
            "ts": 1.0
        },  # host 缺失
        {
            "schema_version": 1,
            "host": "",
            "port": 1,
            "owner": None,
            "absorbed": [],
            "ts": 1.0
        },  # host 空串
        {
            "schema_version": 1,
            "host": 5,
            "port": 1,
            "owner": None,
            "absorbed": [],
            "ts": 1.0
        },  # host 非str
        {
            "schema_version": 1,
            "host": "h",
            "owner": None,
            "absorbed": [],
            "ts": 1.0
        },  # port 缺失
        {
            "schema_version": 1,
            "host": "h",
            "port": 0,
            "owner": None,
            "absorbed": [],
            "ts": 1.0
        },  # port 非正
        {
            "schema_version": 1,
            "host": "h",
            "port": "8080",
            "owner": None,
            "absorbed": [],
            "ts": 1.0
        },  # port 数值串混型
        {
            "schema_version": 1,
            "host": "h",
            "port": 1,
            "owner": {
                "pid": "4242",
                "ct": 1.0,
                "ts": 1.0
            },
            "absorbed": [],
            "ts": 1.0
        },  # pid 数值串
        {
            "schema_version": 1,
            "host": "h",
            "port": 1,
            "owner": {
                "pid": True,
                "ct": 1.0,
                "ts": 1.0
            },
            "absorbed": [],
            "ts": 1.0
        },  # pid bool 冒充 1
        {
            "schema_version": 1,
            "host": "h",
            "port": 1,
            "owner": {
                "pid": 4242,
                "ct": "1e3",
                "ts": 1.0
            },
            "absorbed": [],
            "ts": 1.0
        },  # ct 数值串
        {
            "schema_version": 1,
            "host": "h",
            "port": 1,
            "owner": {
                "pid": 4242,
                "ct": 1e999,
                "ts": 1.0
            },
            "absorbed": [],
            "ts": 1.0
        },  # ct = 1e999 => inf(JSON Infinity 往返): 非有限值拒收(T1 复评遗留, W1b 补)
        {
            "schema_version": 1,
            "host": "h",
            "port": 1,
            "owner": {
                "pid": 4242,
                "ct": 10**400,
                "ts": 1.0
            },
            "absorbed": [],
            "ts": 1.0
        },  # ct 巨 int(转 float 溢出): 与 inf 同判废(T2 评审 minor)
        {
            "schema_version": 1,
            "host": "h",
            "port": 1,
            "owner": {
                "pid": 4242,
                "ct": 1.0,
                "ts": True
            },
            "absorbed": [],
            "ts": 1.0
        },  # entry ts bool
        {
            "schema_version": 1,
            "host": "h",
            "port": 1,
            "owner": {
                "pid": 0,
                "ct": 1.0,
                "ts": 1.0
            },
            "absorbed": [],
            "ts": 1.0
        },  # pid 非正
        {
            "schema_version": 1,
            "host": "h",
            "port": 1,
            "owner": "junk",
            "absorbed": [],
            "ts": 1.0
        },  # owner 非dict
        {
            "schema_version": 1,
            "host": "h",
            "port": 1,
            "owner": None,
            "absorbed": ["junk"],
            "ts": 1.0
        },  # absorbed 成员形不符
        {
            "schema_version": 1,
            "host": "h",
            "port": 1,
            "owner": None,
            "absorbed": [],
            "ts": "x"
        },  # ts 非数值
        {
            "schema_version": 1,
            "host": "h",
            "port": 1,
            "owner": None,
            "absorbed": [],
            "ts": "120.0"
        },  # 顶层 ts 数值串混型
        {
            "schema_version": 1,
            "host": "h",
            "port": 1,
            "owner": None,
            "absorbed": [],
            "ts": True
        },  # 顶层 ts bool
        {
            "schema_version": 1,
            "host": "h",
            "port": 1,
            "owner": None,
            "ts": 1.0
        },  # absorbed 键缺失(非本链产物)
    ]
    for i, body in enumerate(bad_bodies):
        rj._write_json(rj.obs_path(d, f"bad{i}"), body)
        assert rj.read_obs(d, f"bad{i}") is None, body
    rj._write_json(rj.obs_path(d, "lst"), [1, 2])  # 整文件非 dict
    assert rj.read_obs(d, "lst") is None


def test_obs_write_failure_is_false(tmp_path, monkeypatch):
    """盘故障 => False 不抛(观测持久化 best-effort, 调用方告警留痕后继续)"""
    def _boom(path, fn):
        raise OSError("disk full")

    monkeypatch.setattr(rj, "_write_json", _boom)
    assert rj.write_obs(str(tmp_path), "k", {"owner": None, "absorbed": [], "ts": 1.0}) is False


def test_filetime_to_epoch_known_value():
    dt = datetime(2022, 6, 18, 5, 6, 40, tzinfo=timezone.utc)
    ft = int((dt - datetime(1601, 1, 1, tzinfo=timezone.utc)).total_seconds() * 10**7)
    assert rd._filetime_to_epoch(ft) == dt.timestamp() == (ft - rd._FILETIME_1601_TO_EPOCH_TICKS) / 10**7


def test_owner_pid_from_netstat_zh_en_and_wildcard(monkeypatch):
    """netstat 解析中英文样例各一: LISTENING 行本地端口归属(0.0.0.0 通配/具体地址同算),
    [::] IPv6 行独立 pid+端口断言(解析回归可判红); ESTABLISHED/TIME_WAIT/UDP 行/表头/
    端口不合一律跳过; 子进程钉法(encoding=utf-8 + errors=replace + timeout=10)钉死"""
    calls = _stub_stdout(monkeypatch, NETSTAT_ZH)
    assert rd._owner_pid_from_netstat(36596) == 12345, "通配行归属; 同端口 ESTABLISHED 行跳过"
    assert calls["encoding"] == "utf-8" and calls["errors"] == "replace" and calls["timeout"] == 10, "钉法回归防线"
    assert rd._owner_pid_from_netstat(36597) == 7777, "[::] IPv6 行独立归属(端口按最后一个 ':' 取)"
    assert rd._owner_pid_from_netstat(135) == 9876
    assert rd._owner_pid_from_netstat(9999) is None
    calls_en = _stub_stdout(monkeypatch, NETSTAT_EN)
    assert rd._owner_pid_from_netstat(36596) == 12345
    assert calls_en["encoding"] == "utf-8" and calls_en["errors"] == "replace" and calls_en["timeout"] == 10
    assert rd._owner_pid_from_netstat(36598) is None, "TIME_WAIT 不算监听"
    assert rd._owner_pid_from_netstat(5353) is None, "UDP 行(4 列)跳过"


def test_owner_pid_from_netstat_ambiguous_or_garbage_is_none(monkeypatch, caplog):
    # 归属不唯一(同端口两个 LISTENING pid)=> None + warning(不猜)
    _stub_stdout(
        monkeypatch,
        "  TCP    0.0.0.0:8080    0.0.0.0:0    LISTENING    100\n"
        "  TCP    10.0.0.2:8080    0.0.0.0:0    LISTENING    200\n",
    )
    with caplog.at_level(logging.WARNING, logger=LOG_RD):
        assert rd._owner_pid_from_netstat(8080) is None
    assert any("归属不唯一" in r.message for r in caplog.records), caplog.text
    # 乱码输出(解码失败的等效形态: 数据行全部不成形)=> 无匹配行 => None, 不产假证据
    _stub_stdout(monkeypatch, "\ufffd\ufffd\ufffd \ufffd\ufffd\nrandom garbage line\n")
    assert rd._owner_pid_from_netstat(8080) is None


def test_owner_pid_from_procnet_fake_tree(monkeypatch, caplog):
    """Linux LISTENING 归属(假 /proc): st==0A 行端口->inode, /proc/<pid>/fd socket 链接归属;
    tcp6 缺失只当该表无监听; st==01(非监听)行不贡献 inode; 归属不唯一 => None + warning"""
    tcp = (
        "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n"
        "   0: 00000000:1F90 00000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 12345 1 0\n"
        "   1: 00000000:1F91 00000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 12346 1 0\n"
        "   2: 0100007F:1F90 0200007F:CEAA 01 00000000:00000000 00:00000000 00000000     0        0 12347 1 0\n"
    )
    _stub_proc_open(monkeypatch, {"/proc/net/tcp": tcp, "/proc/net/tcp6": OSError(2, "no tcp6")})
    # 单一归属: 8080 -> inode 12345 -> pid 42; 8081 -> inode 12346 -> pid 44; fd 目录打不开的
    # pid 无从归属(逐项跳过); 非 socket fd 与已消失 fd 不贡献归属; /proc 根清单含非数字项
    links = {"/proc/42/fd/5": "socket:[12345]", "/proc/42/fd/6": "pipe:[999]", "/proc/44/fd/9": "socket:[12346]"}

    def _listdir(p):
        if p == "/proc":
            return ["1", "self", "42", "43", "44"]
        try:
            return {"/proc/42/fd": ["5", "6"], "/proc/44/fd": ["9", "gone"]}[p.replace("\\", "/")]
        except KeyError:
            raise OSError(2, f"no fd dir {p}")

    def _readlink(p):
        p = p.replace("\\", "/")
        if p.endswith("/gone"):
            raise OSError(2, f"fd vanished {p}")
        try:
            return links[p]
        except KeyError:
            raise OSError(2, f"no link {p}")

    monkeypatch.setattr(rd.os, "listdir", _listdir)
    monkeypatch.setattr(rd.os, "readlink", _readlink)
    assert rd._owner_pid_from_procnet(8080) == 42
    assert rd._owner_pid_from_procnet(8081) == 44
    assert rd._owner_pid_from_procnet(8082) is None, "表中无该端口监听"
    # 归属不唯一: 两个 pid 链到同一 inode => None + warning(不猜)
    monkeypatch.setattr(rd.os, "readlink", lambda p: "socket:[12345]")
    with caplog.at_level(logging.WARNING, logger=LOG_RD):
        assert rd._owner_pid_from_procnet(8080) is None
    assert any("归属不唯一" in r.message for r in caplog.records), caplog.text


def test_listening_owner_pid_dispatch_and_exception_is_none(monkeypatch, caplog):
    """LISTENING 归属分派(nt -> netstat 支 / 非 nt -> procnet 支); 归属不成功(无监听行/
    归属不唯一)与通道异常 => None + warning(证据语义: None = 观测不可用, 调用方退 L2,
    绝不当 owner 死证)"""
    monkeypatch.setattr(rd.os, "name", "nt")
    monkeypatch.setattr(rd, "_owner_pid_from_netstat", lambda port: 5555)
    assert rd._listening_owner_pid(8080) == 5555
    monkeypatch.setattr(rd.os, "name", "posix")
    monkeypatch.setattr(rd, "_owner_pid_from_procnet", lambda port: 6666)
    assert rd._listening_owner_pid(8080) == 6666
    # 归属不成功(解析侧无监听行/归属不唯一)=> None + warning「未归属成功」
    monkeypatch.setattr(rd, "_owner_pid_from_procnet", lambda port: None)
    with caplog.at_level(logging.WARNING, logger=LOG_RD):
        assert rd._listening_owner_pid(8080) is None
    assert any("未归属成功" in r.message for r in caplog.records), caplog.text
    # 通道异常 => None + warning(观测不可用)
    caplog.clear()

    def _boom(port):
        raise RuntimeError("boom")

    monkeypatch.setattr(rd, "_owner_pid_from_procnet", _boom)
    with caplog.at_level(logging.WARNING, logger=LOG_RD):
        assert rd._listening_owner_pid(8080) is None
    assert any("观测不可用" in r.message for r in caplog.records), caplog.text


def test_qb_processes_from_powershell_parse_and_conservative_drops(monkeypatch, caplog):
    """PowerShell 枚举解析: 数据行 pid|name|filetime -> {pid: {name, ct}}(映像名小写);
    StartTime 不可读/pid 非数值/映像名空条目剔除且聚合判 None(部分清单不冒充全量); 形制外
    的行/缺健康标记 => None; 标记+零数据 => {}(健康零观测, 非 None); 钉法钉死"""
    calls = _stub_stdout(
        monkeypatch,
        "4212|qbittorrent|133000000000000000\r\n8804|qBittorrentEnhanced|133000000100000000\r\nqb-obs-end\r\n"
    )
    assert rd._qb_processes_from_powershell() == {
        4212: {
            "name": "qbittorrent",
            "ct": 1655526400.0
        },
        8804: {
            "name": "qbittorrentenhanced",
            "ct": 1655526410.0
        },
    }
    assert calls["encoding"] == "utf-8" and calls["errors"] == "replace" and calls["timeout"] == 10, "钉法回归防线"
    # StartTime 不可读(空 filetime): 该条目剔除, 聚合判不可用
    _stub_stdout(monkeypatch, "4212|qbittorrent|\r\n8804|qbittorrent|133000000100000000\r\nqb-obs-end\r\n")
    with caplog.at_level(logging.WARNING, logger=LOG_RD):
        assert rd._qb_processes_from_powershell() is None
    assert any("StartTime" in r.message for r in caplog.records), caplog.text
    # 形制外的行混入(解析器不硬赌输出格式)=> 聚合判不可用
    caplog.clear()
    _stub_stdout(monkeypatch, "Get-Process : error text\r\n4212|qbittorrent|133000000000000000\r\nqb-obs-end\r\n")
    assert rd._qb_processes_from_powershell() is None
    # 第二剔除支: pid 非数值 / 映像名空 —— 条目剔除 + 聚合判不可用
    caplog.clear()
    _stub_stdout(monkeypatch, "abc|qbittorrent|133000000000000000\r\nqb-obs-end\r\n")
    assert rd._qb_processes_from_powershell() is None
    assert any("pid/映像名" in r.message for r in caplog.records), caplog.text
    caplog.clear()
    _stub_stdout(monkeypatch, "4212||133000000000000000\r\nqb-obs-end\r\n")
    assert rd._qb_processes_from_powershell() is None
    assert any("pid/映像名" in r.message for r in caplog.records), caplog.text
    # 缺健康标记(管线半途而废)=> None(区分「通道故障」与「健康零观测」)
    caplog.clear()
    _stub_stdout(monkeypatch, "4212|qbittorrent|133000000000000000\r\n")
    assert rd._qb_processes_from_powershell() is None
    assert any("健康标记" in r.message for r in caplog.records), caplog.text
    # 通道健康且全机无 qB => {}(有效观测, 不是 None)
    _stub_stdout(monkeypatch, "\r\nqb-obs-end\r\n")
    assert rd._qb_processes_from_powershell() == {}


def test_qb_processes_from_proc_fake_tree(monkeypatch, caplog):
    """Linux O2(假 /proc 树): comm 含 qbittorrent 收录, ct = btime + starttime/SC_CLK_TCK;
    读时已消失的 pid(FileNotFoundError)整体忽略不算枚举不完整; comm/stat 身份不可得 =>
    聚合判 None(部分清单不冒充全量)"""
    healthy_stat = "100 (qbittorrent) S " + " ".join(["0"] * 18) + " 2000000 0 0"

    def _fake(monkeypatch, comm, stat):
        mapping = {"/proc/stat": "cpu 1 2 3\nbtime 1000000000\nintr 1\n"}
        for pid, c in comm.items():
            mapping[f"/proc/{pid}/comm"] = c
        for pid, s in stat.items():
            mapping[f"/proc/{pid}/stat"] = s
        monkeypatch.setattr(rd.os, "listdir", lambda p: ["1", "self", "100", "200", "300"])
        _stub_proc_open(monkeypatch, mapping)
        monkeypatch.setattr(rd.os, "sysconf", lambda name: 100, raising=False)

    # 健康树: qbittorrent 收录 + ct 换算; 无关 comm(systemd/self)与非数字项跳过
    _fake(monkeypatch, {1: "systemd\n", "self": "python\n", 100: "qbittorrent\n"}, {100: healthy_stat})
    assert rd._qb_processes_from_proc() == {100: {"name": "qbittorrent", "ct": 1000020000.0}}
    # 读时已消失(pid 300 stat FileNotFoundError): 死进程无威胁, 条目整体忽略, 聚合仍可用
    _fake(
        monkeypatch, {
            100: "qbittorrent\n",
            300: "qbittorrent\n"
        }, {
            100: healthy_stat,
            300: FileNotFoundError(2, "gone")
        }
    )
    assert rd._qb_processes_from_proc() == {100: {"name": "qbittorrent", "ct": 1000020000.0}}
    # stat 身份不可得(pid 200 PermissionError): 剔除 + 聚合判不可用
    _fake(
        monkeypatch, {
            100: "qbittorrent\n",
            200: "qbittorrent\n"
        }, {
            100: healthy_stat,
            200: PermissionError(13, "denied")
        }
    )
    with caplog.at_level(logging.WARNING, logger=LOG_RD):
        assert rd._qb_processes_from_proc() is None
    assert any("starttime" in r.message.lower() for r in caplog.records), caplog.text
    # comm 不可读(pid 200 PermissionError): 无法判是否 qB => 同款聚合不可用
    caplog.clear()
    _fake(monkeypatch, {100: "qbittorrent\n", 200: PermissionError(13, "denied")}, {100: healthy_stat})
    assert rd._qb_processes_from_proc() is None
    assert any("comm" in r.message for r in caplog.records), caplog.text


def test_qb_processes_from_proc_broken_btime_or_hz_is_none(monkeypatch, caplog):
    """病树变体: /proc/stat 读不到(btime OSError)/ btime 行缺失(sysconf 桩抛/返 0 同款)
    => None + warning「枚举不可用」(基线量缺失时 (pid, ct) 换算无从谈起, 观测不可用,
    绝不产假 ct)"""
    monkeypatch.setattr(rd.os, "listdir", lambda p: ["100"])
    # btime 文件 OSError
    _stub_proc_open(monkeypatch, {"/proc/stat": OSError(13, "denied")})
    with caplog.at_level(logging.WARNING, logger=LOG_RD):
        assert rd._qb_processes_from_proc() is None
    assert any("枚举不可用" in r.message for r in caplog.records), caplog.text
    # btime 行缺失(StopIteration)
    caplog.clear()
    _stub_proc_open(monkeypatch, {"/proc/stat": "cpu 1 2 3\n"})
    with caplog.at_level(logging.WARNING, logger=LOG_RD):
        assert rd._qb_processes_from_proc() is None
    assert any("枚举不可用" in r.message for r in caplog.records), caplog.text
    # sysconf 桩抛(平台无 SC_CLK_TCK 等价物)
    caplog.clear()
    _stub_proc_open(monkeypatch, {"/proc/stat": "btime 1000000000\n"})

    def _no_sysconf(name):
        raise AttributeError("no sysconf")

    monkeypatch.setattr(rd.os, "sysconf", _no_sysconf, raising=False)
    with caplog.at_level(logging.WARNING, logger=LOG_RD):
        assert rd._qb_processes_from_proc() is None
    assert any("枚举不可用" in r.message for r in caplog.records), caplog.text
    # HZ <= 0
    caplog.clear()
    monkeypatch.setattr(rd.os, "sysconf", lambda name: 0, raising=False)
    with caplog.at_level(logging.WARNING, logger=LOG_RD):
        assert rd._qb_processes_from_proc() is None
    assert any("枚举不可用" in r.message for r in caplog.records), caplog.text


def test_qb_processes_dispatch_timeout_and_healthy_empty(monkeypatch, caplog):
    """O2 分派: 子进程超时/命令缺失 => None + warning(观测不可用, 调用方退 L2, 绝不产假
    证据); posix 分派透传 proc 支; 健康零观测({})不判不可用"""
    monkeypatch.setattr(rd.os, "name", "nt")

    def _raise(exc):
        def _run(*a, **kw):
            raise exc

        return _run

    with caplog.at_level(logging.WARNING, logger=LOG_RD):
        monkeypatch.setattr(rd.subprocess, "run", _raise(rd.subprocess.TimeoutExpired(cmd="powershell", timeout=10)))
        assert rd._qb_processes() is None, "超时 => 观测不可用"
        monkeypatch.setattr(rd.subprocess, "run", _raise(FileNotFoundError(2, "no powershell")))
        assert rd._qb_processes() is None, "命令缺失 => 观测不可用"
    assert caplog.text.count("观测不可用") >= 2, caplog.text
    monkeypatch.setattr(rd.os, "name", "posix")
    monkeypatch.setattr(rd, "_qb_processes_from_proc", lambda: {})
    assert rd._qb_processes() == {}, "健康零观测透传(不判不可用)"


def test_observe_owner_cross_check_and_channel_none(monkeypatch, caplog):
    """O1 交叉校验: 归属 pid 的映像名含 qbittorrent(大小写不敏感)才记录 {pid, ct, ts};
    非 qB 服务占端口/名册映像名漂移/枚举通道故障/归属不成功 => None + 不记录(保守面)。
    桩签名带 listen_map 形参(W1b 给 _listening_owner_pid 扩了共用映射注入面, 缺省 None)"""
    monkeypatch.setattr(rd, "_listening_owner_pid", lambda port, listen_map=None: 4242)
    qb = {4242: {"name": "qBittorrent", "ct": 100.0}}
    assert rd._observe_owner(8080, qb, 500.0) == {"pid": 4242, "ct": 100.0, "ts": 500.0}
    # 非 qB 占端口(全机 qB 名册无此 pid)=> 不记录 + warning
    monkeypatch.setattr(rd, "_listening_owner_pid", lambda port, listen_map=None: 7)
    with caplog.at_level(logging.WARNING, logger=LOG_RD):
        assert rd._observe_owner(8080, qb, 500.0) is None
    assert any("不记录 owner" in r.message for r in caplog.records), caplog.text
    # 名册成员映像名漂移(不含 qbittorrent)=> 不记录(带与保守)
    monkeypatch.setattr(rd, "_listening_owner_pid", lambda port, listen_map=None: 4242)
    assert rd._observe_owner(8080, {4242: {"name": "chrome", "ct": 100.0}}, 500.0) is None
    # 枚举通道故障(None)=> 直接 None(没有名册就没有证据)
    assert rd._observe_owner(8080, None, 500.0) is None
    # 归属不成功 => None
    monkeypatch.setattr(rd, "_listening_owner_pid", lambda port, listen_map=None: None)
    assert rd._observe_owner(8080, qb, 500.0) is None


# ---------------------------------------------------------------------------
# 判据面(W1b, 计划 26-11-10-0318 §03.2/§03.3): 全机 LISTENING 映射底座 + _Observation
# 状态机。全替身、时钟显式注入: 不起真进程、不回连真端口、零 I/O —— 状态机输入(名册/
# owner 候选/指纹映射)直接喂构造值, 落盘时机契约靠 tick 返回值钉住
# ---------------------------------------------------------------------------

# 全机映射解析样例(W1a 单端口样例之外的扩展形制): pid 100 双端口监听(通配+具体),
# pid 200 IPv6 行与 pid 100 同端口(归属不唯一样态), pid 300 只出现在 ESTABLISHED/
# TIME_WAIT 行(不得混进监听集), UDP 行与表头不贡献
NETSTAT_MAP_EN = (
    "\n"
    "Active Connections\n"
    "\n"
    "  Proto  Local Address          Foreign Address        State           PID\n"
    "  TCP    0.0.0.0:8080           0.0.0.0:0              LISTENING       100\n"
    "  TCP    10.0.0.2:8081          0.0.0.0:0              LISTENING       100\n"
    "  TCP    [::]:8080              [::]:0                 LISTENING       200\n"
    "  TCP    10.0.0.2:8080          10.0.0.2:443           ESTABLISHED     300\n"
    "  TCP    10.0.0.2:9000          10.0.0.9:443           TIME_WAIT       300\n"
    "  UDP    0.0.0.0:5353           *:*                                    400\n"
)
NETSTAT_MAP_ZH = (
    "\n"
    "活动连接\n"
    "\n"
    "  协议  本地地址          外部地址        状态           PID\n"
    "  TCP    0.0.0.0:8080          0.0.0.0:0              LISTENING       100\n"
)


def _ident(ct: float, name: str = "qbittorrent") -> dict:
    """名册条目构造(_qb_processes 契约形 {name, ct})"""
    return {"name": name, "ct": float(ct)}


def _owner_record(pid: int, ct: float, ts: float) -> dict:
    """owner 记录构造({pid, ct, ts}, 与 obs schema 对齐)"""
    return {"pid": int(pid), "ct": float(ct), "ts": float(ts)}


def _seed_owner(obs, now: float = 500.0, pid: int = 100, ct: float = 100.0):
    """经候选命中给状态机建档 owner(契约路径, 不直改字段)"""
    obs.tick({pid: _ident(ct)}, {"pid": pid, "ct": ct}, None, now)


def test_listening_map_netstat_groups_pid_ports(caplog):
    """全机 LISTENING 映射解析: pid 归组(通配/具体/[::] 同算, 同 pid 多端口合并);
    ESTABLISHED/TIME_WAIT/UDP 行与表头不进映射; 健康标记(T2 评审收紧): 零条 LISTENING
    解析成功 —— 空输出/表头孤行/整包乱码/TCP 前缀行在而状态字或列数全不合 => None +
    warning(格式漂移嫌疑, §07 R2「解析不出就退」), 防「乱码 => 人人空监听集 => 假 settle 吸收」"""
    assert rd._listening_map_netstat(NETSTAT_MAP_EN) == {100: frozenset({8080, 8081}), 200: frozenset({8080})}
    assert rd._listening_map_netstat(NETSTAT_MAP_ZH) == {100: frozenset({8080})}, "中文表头样例同解析"
    with caplog.at_level(logging.WARNING, logger=LOG_RD):
        assert rd._listening_map_netstat("") is None
        assert rd._listening_map_netstat("Active Connections\n\n") is None, "表头孤行 => 通道不可用"
        assert rd._listening_map_netstat("\ufffd\ufffd\ufffd \ufffd\ufffd\nrandom garbage\n") is None, "乱码不产假映射"
        # TCP 前缀行在而状态字/列数全不合(T2 评审新增输入类): 零 LISTENING 解析成功 => None
        assert rd._listening_map_netstat(
            "  TCP    0.0.0.0:8080    0.0.0.0:0    SYN_SENT    100\n"
            "  TCP    only-three-cols\n"
        ) is None, "TCP 行在而零 LISTENING 解析 => 格式漂移嫌疑"
    assert any("格式漂移" in r.message for r in caplog.records), caplog.text


def test_listening_map_windows_and_dispatch(monkeypatch, caplog):
    """Windows 映射通道: 子进程钉法(encoding=utf-8 + errors=replace + timeout=10 +
    creationflags=CREATE_NO_WINDOW)钉死; dispatch(nt -> windows / posix -> proc);
    通道异常 => None + warning(观测不可用)"""
    calls = _stub_stdout(monkeypatch, NETSTAT_MAP_EN)
    assert rd._listening_map_windows() == {100: frozenset({8080, 8081}), 200: frozenset({8080})}
    assert calls["encoding"] == "utf-8" and calls["errors"] == "replace" and calls["timeout"] == 10, "钉法回归防线"
    assert calls["creationflags"] == getattr(rd.subprocess, "CREATE_NO_WINDOW", 0), "钉法第 4 项(T2 评审 nit 6)"
    monkeypatch.setattr(rd.os, "name", "nt")
    assert rd._listening_map() == {100: frozenset({8080, 8081}), 200: frozenset({8080})}
    monkeypatch.setattr(rd.os, "name", "posix")
    monkeypatch.setattr(rd, "_listening_map_proc", lambda: {7: frozenset({80})})
    assert rd._listening_map() == {7: frozenset({80})}, "posix 分派透传"

    def _boom():
        raise RuntimeError("boom")

    monkeypatch.setattr(rd, "_listening_map_proc", _boom)
    with caplog.at_level(logging.WARNING, logger=LOG_RD):
        assert rd._listening_map() is None
    assert any("观测不可用" in r.message for r in caplog.records), caplog.text


def test_listening_map_proc_fake_tree(monkeypatch, caplog):
    """Linux 全机映射(假 /proc): 表 st==0A 行端口->inode, /proc/<pid>/fd socket 链接归组
    (同 pid 多监听合并); tcp6 缺失只当该表无监听; tcp 主表不可读 => None + warning(v4
    主表缺席不许把全员判成空集); 表在而零条 LISTENING 解析成功(st 全非 0A)=> None +
    warning(格式漂移嫌疑, T2 评审收紧)且不再扫 fd; REUSEPORT 两 pid 同端口 => 两 pid
    都进映射、归属判不唯一"""
    tcp = (
        "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n"
        "   0: 00000000:1F90 00000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 111 1 0\n"
        "   1: 00000000:1F91 00000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 222 1 0\n"
        "   2: 00000000:1F90 00000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 333 1 0\n"
        "   3: 0100007F:1F90 0200007F:CEAA 01 00000000:00000000 00:00000000 00000000     0        0 444 1 0\n"
    )
    links = {"/proc/5/fd/3": "socket:[111]", "/proc/6/fd/7": "socket:[222]", "/proc/6/fd/9": "socket:[333]"}

    def _listdir(p):
        if p == "/proc":
            return ["1", "self", "5", "6", "9"]
        try:
            return {"/proc/5/fd": ["3"], "/proc/6/fd": ["7", "9"]}[p.replace("\\", "/")]
        except KeyError:
            raise OSError(2, f"no fd dir {p}")

    def _readlink(p):
        try:
            return links[p.replace("\\", "/")]
        except KeyError:
            raise OSError(2, f"no link {p}")

    monkeypatch.setattr(rd.os, "listdir", _listdir)
    monkeypatch.setattr(rd.os, "readlink", _readlink)
    _stub_proc_open(monkeypatch, {"/proc/net/tcp": tcp, "/proc/net/tcp6": OSError(2, "no tcp6")})
    assert rd._listening_map_proc() == {5: frozenset({8080}), 6: frozenset({8080, 8081})}, \
        "inode 111/333 同端口(8080)归到两 pid; 444 非 0A 行不贡献; pid 9 无 fd 目录跳过"
    assert rd._owner_pid_from_map(rd._listening_map_proc(), 8080) is None, "REUSEPORT 两 pid => 归属不唯一不猜"
    assert rd._owner_pid_from_map(rd._listening_map_proc(), 8081) == 6
    # tcp 主表不可读 => None + warning(假证据方向防守)
    _stub_proc_open(monkeypatch, {"/proc/net/tcp": OSError(13, "denied")})
    with caplog.at_level(logging.WARNING, logger=LOG_RD):
        assert rd._listening_map_proc() is None
    assert any("映射不可用" in r.message for r in caplog.records), caplog.text
    # 表在而零条 LISTENING 解析成功(行在而 st 全非 0A) => None + warning(格式漂移嫌疑)且不再扫 fd
    _stub_proc_open(
        monkeypatch, {
            "/proc/net/tcp":
                "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n"
                "   0: 00000000:1F90 0200007F:CEAA 01 00000000:00000000 00:00000000 00000000     0        0 444 1 0\n"
        }
    )

    def _no_scan(p):
        raise AssertionError("零 LISTENING 解析成功时不得扫 /proc/<pid>/fd")

    monkeypatch.setattr(rd.os, "listdir", _no_scan)
    with caplog.at_level(logging.WARNING, logger=LOG_RD):
        assert rd._listening_map_proc() is None, "零 LISTENING 解析成功 => 格式漂移嫌疑(T2 评审收紧)"
    assert any("格式漂移" in r.message for r in caplog.records), caplog.text


def test_owner_pid_from_map_consistent_with_single_port_fns(monkeypatch):
    """同源一致性: 同一份输出下, 全机映射派生的归属与 W1a 单端口归属函数逐端口结论一致
    (含不唯一 => 两边同 None + 不猜); netstat/procnet 各验一遍"""
    calls = _stub_stdout(monkeypatch, NETSTAT_MAP_EN)
    m = rd._listening_map_netstat(NETSTAT_MAP_EN)
    for port in (8080, 8081, 9000, 5353, 9999):
        assert rd._owner_pid_from_netstat(port) == rd._owner_pid_from_map(m, port), f"netstat port {port}"
    assert rd._owner_pid_from_netstat(8080) is None and rd._owner_pid_from_netstat(8081) == 100
    assert calls["timeout"] == 10, "单端口函数内部复用映射读取, 钉法不变"
    # procnet 同源
    tcp = (
        "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n"
        "   0: 00000000:1F90 00000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 111 1 0\n"
        "   1: 00000000:1F91 00000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 222 1 0\n"
    )
    links = {"/proc/5/fd/3": "socket:[111]", "/proc/6/fd/7": "socket:[222]"}

    def _listdir(p):
        if p == "/proc":
            return ["5", "6"]
        try:
            return {"/proc/5/fd": ["3"], "/proc/6/fd": ["7"]}[p.replace("\\", "/")]
        except KeyError:
            raise OSError(2, f"no fd dir {p}")

    monkeypatch.setattr(rd.os, "listdir", _listdir)
    monkeypatch.setattr(rd.os, "readlink", lambda p: links.get(p.replace("\\", "/"), "pipe:[1]"))
    _stub_proc_open(monkeypatch, {"/proc/net/tcp": tcp, "/proc/net/tcp6": OSError(2, "no tcp6")})
    m2 = rd._listening_map_proc()
    assert m2 == {5: frozenset({8080}), 6: frozenset({8081})}
    for port in (8080, 8081, 8082):
        assert rd._owner_pid_from_procnet(port) == rd._owner_pid_from_map(m2, port), f"procnet port {port}"


def test_listening_owner_pid_injected_map_no_subprocess(monkeypatch, caplog):
    """注入映射的归属面: 不起子进程(subprocess.run 下毒也不炸); 端口无主/归属不唯一 =>
    None + warning(与自取路径同语义)"""
    def _poison(*a, **kw):
        raise AssertionError("注入映射后不得再起子进程")

    monkeypatch.setattr(rd.subprocess, "run", _poison)
    m = {100: frozenset({8080}), 200: frozenset({8081})}
    assert rd._listening_owner_pid(8080, m) == 100
    assert rd._listening_owner_pid(8081, m) == 200
    with caplog.at_level(logging.WARNING, logger=LOG_RD):
        assert rd._listening_owner_pid(8082, m) is None, "端口无主 => 观测不可用"
        assert rd._listening_owner_pid(8080, {100: frozenset({8080}), 200: frozenset({8080})}) is None
    assert any("未归属成功" in r.message for r in caplog.records), caplog.text
    assert any("归属不唯一" in r.message for r in caplog.records), caplog.text


def test_observe_owner_injected_map_matches_self_fetch(monkeypatch):
    """候选面同源一致性: 注入映射的 _observe_owner 不起子进程, 且与自取路径结论一致 ——
    W2a 每 poll 一次读取喂「归属 + 指纹」两消费面的接线契约。自取路径的两平台分派在任一
    平台都跑(两支各 os.name 桩钉住): nt 支桩 netstat 输出, proc 支桩 /proc 表+fd, 两支
    各让 8081 归 pid 100 —— 修 CI Linux 红: 分派不钉时 Linux 上 netstat 桩落空/proc 支
    真读 /proc(8081 无监听 => None)(坑: 平台分派的测试每支都必须钉住自己的分派)。"""
    def _poison(*a, **kw):
        raise AssertionError("注入映射后不得再起子进程")

    qb = {100: {"name": "qBittorrent", "ct": 100.0}}
    monkeypatch.setattr(rd.subprocess, "run", _poison)
    assert rd._observe_owner(8081, qb, 500.0, listen_map={100: frozenset({8081})}) == _owner_record(100, 100.0, 500.0)
    # 自取路径 nt 分派(os.name 桩钉住分派 —— Linux 上不钉则走 proc 分派, netstat 桩落空,
    # 即本批修的 CI 红同根因): 桩 netstat 输出(编码/超时钉法回归防线), 与注入路径结论一致
    monkeypatch.setattr(rd.os, "name", "nt")
    calls = _stub_stdout(monkeypatch, NETSTAT_MAP_EN)
    assert rd._observe_owner(8081, qb, 500.0) == _owner_record(100, 100.0, 500.0)
    assert calls["timeout"] == 10
    # 自取路径 proc 分派(os.name 桩, 两平台都跑): /proc/net/tcp 8081(LISTENING, inode 111)
    # 归 pid 100, 与 NETSTAT_MAP_EN 同一结论; proc 分派同样不起子进程(回毒)
    monkeypatch.setattr(rd.subprocess, "run", _poison)
    monkeypatch.setattr(rd.os, "name", "posix")
    tcp = (
        "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n"
        "   0: 00000000:1F91 00000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 111 1 0\n"
    )
    links = {"/proc/100/fd/3": "socket:[111]"}

    def _listdir(p):
        if p == "/proc":
            return ["100"]
        try:
            return {"/proc/100/fd": ["3"]}[p.replace("\\", "/")]
        except KeyError:
            raise OSError(2, f"no fd dir {p}")

    monkeypatch.setattr(rd.os, "listdir", _listdir)
    monkeypatch.setattr(rd.os, "readlink", lambda p: links.get(p.replace("\\", "/"), "pipe:[1]"))
    _stub_proc_open(monkeypatch, {"/proc/net/tcp": tcp, "/proc/net/tcp6": OSError(2, "no tcp6")})
    assert rd._observe_owner(8081, qb, 500.0) == _owner_record(100, 100.0, 500.0)


def test_observation_zero_bet_absorb_row1():
    """§03.2 行一(同域阈值, T2 评审 major 修正): ct < owner.ct 的非 owner 面直接进
    absorbed(即时吸收, 不需要指纹通道)—— ct 与 owner.ct 同为 OS create_time 域, 同域
    比较消钟差; owner 本尊与已吸收面不重复处理; 名册 None 整拍不可判、持久面不动"""
    obs = rd._Observation(HOST, PORT)
    _seed_owner(obs, now=500.0, pid=100, ct=100.0)
    roster = {100: _ident(100.0), 200: _ident(50.0), 300: _ident(90.0)}
    assert obs.tick(roster, None, None, 505.0) is True, "50/90 早于 owner 实例本身 => 零赌注吸收"
    assert obs.owner == _owner_record(100, 100.0, 500.0), "owner 记录不动"
    assert obs.absorbed == [{"pid": 200, "ct": 50.0, "ts": 505.0}, {"pid": 300, "ct": 90.0, "ts": 505.0}]
    assert obs.pending == {}, "零赌注面不经未决"
    assert obs.tick(roster, None, None, 510.0) is False, "已吸收(同 pid 同 ct)不重复, 持久面零变更"
    assert obs.tick(None, None, None, 520.0) is False, "名册 None => 整拍不动"
    assert len(obs.absorbed) == 2 and obs.owner is not None


def test_observation_gap_band_goes_settle_and_order_invariant():
    """行一 gap 带 [owner.ct, ts_last)(T2 评审 major 修正): 旧实现被混域零赌注即时吸收,
    现改走未决 settle 管道(30s 指纹稳定后吸收, 场景 Y 代价 ~33s 计划已定价)。行序钉死:
    行二在位续证把 ts 刷到 now 后, gap 面仍走 settle —— 即时吸收阈值锚在 owner.ct(不被
    ts 刷新移动), 无论行一/行二谁先判, gap 面最终一致走 settle, 绝不即时吸收"""
    obs = rd._Observation(HOST, PORT)
    _seed_owner(obs, now=500.0, pid=100, ct=100.0)
    # 行二在位续证: ts 500 -> 590(阈值若锚 ts 会被刷走, 锚 owner.ct 不动)
    assert obs.tick({100: _ident(100.0)}, {"pid": 100, "ct": 100.0}, None, 590.0) is False
    roster = {100: _ident(100.0), 200: _ident(300.0)}  # ct 300 落在 [owner.ct=100, ts_last=590) gap 带
    assert obs.tick(roster, None, {200: frozenset({8081})}, 600.0) is False, "gap 面: 进未决, 不即时吸收"
    assert obs.absorbed == [] and obs.pending[200]["ct"] == 300.0
    assert obs.tick(roster, None, {200: frozenset({8081})}, 625.0) is False, "未满 30s 挡窗"
    assert obs.tick(roster, None, {200: frozenset({8081})}, 631.0) is True, "稳定 31s => settle 吸收"
    assert obs.absorbed == [{"pid": 200, "ct": 300.0, "ts": 631.0}] and obs.pending == {}
    # 指纹通道不可用时 gap 面同样只滞留未决(更保守, 从不开安全口子)
    obs2 = rd._Observation(HOST, PORT)
    _seed_owner(obs2, now=500.0, pid=100, ct=100.0)
    assert obs2.tick({100: _ident(100.0), 200: _ident(300.0)}, None, None, 600.0) is False
    assert obs2.absorbed == [] and 200 in obs2.pending, "gap 面 + 无指纹证据 => 滞留未决挡窗"


def test_observation_unreadable_ct_face_parks_pending():
    """名册条目 ct 读不出的面(T2 评审 minor 3/nit 7): 进未决真挡 —— 无有效 ct 写不进
    合法 absorbed 条目, 绝不自动 settle 吸收; absorbed 保留不被扰动; 挡 L1; 直到从名册
    消失(出队)、身份恢复(重走分类)或绑端口转 owner(升格出队)"""
    obs = rd._Observation(HOST, PORT)
    _seed_owner(obs, now=500.0, pid=100, ct=100.0)
    obs.tick({100: _ident(100.0), 300: _ident(50.0)}, None, None, 505.0)  # 300 零赌注吸收(ct < owner.ct)
    roster = {100: _ident(100.0), 200: {"name": "qbittorrent"}, 300: _ident(50.0)}  # 200 缺 ct 键
    assert obs.tick(roster, None, None, 600.0) is False, "缺 ct 面进未决(内存面), 持久面不变"
    assert obs.absorbed == [{"pid": 300, "ct": 50.0, "ts": 505.0}], "absorbed 保留"
    assert obs.pending[200] == {"ct": None, "first_seen": 600.0, "fp": None}, "缺 ct 面: 真挡不吸收"
    assert obs.l1_open(roster, True) is False, "缺 ct 面挡窗"
    # 身份恢复(补回可读 ct): 旧未决出队, 按真实身份重走分类
    assert obs.tick(
        {
            100: _ident(100.0),
            200: _ident(600.0),
            300: _ident(50.0)
        }, None, {200: frozenset({8081})}, 610.0
    ) is False
    assert obs.pending[200]["ct"] == 600.0, "身份恢复 => 重走分类"
    # 绑端口转 owner: 升格出队(旧 owner 面按零赌注吸收 —— 早于新 owner 实例存在)
    roster_ok = {100: _ident(100.0), 200: _ident(600.0), 300: _ident(50.0)}
    assert obs.tick(roster_ok, {"pid": 200, "ct": 600.0}, None, 620.0) is True
    assert obs.owner == _owner_record(200, 600.0, 620.0) and obs.pending == {}
    assert {e["pid"] for e in obs.absorbed} == {100, 300}, "旧 owner 面 + 早于新 owner 的面都归零赌注"
    # 从名册消失: 出队
    obs2 = rd._Observation(HOST, PORT)
    _seed_owner(obs2)
    obs2.tick({200: {"name": "qbittorrent"}}, None, None, 600.0)
    assert 200 in obs2.pending
    assert obs2.tick({}, None, None, 610.0) is False and obs2.pending == {}


def test_observation_port_bind_becomes_owner_row2():
    """§03.2 行二: ct >= ts 且绑我们端口(= owner 候选命中)=> 复活/换身/PID 复用三向都转
    owner(持久面变更、未决出队、误吸面出 absorbed); 同 pid 同 ct = 在位续证: 只刷内存
    ts, 不触发落盘(§03.4 写时机 = 变更即写, 频率低)"""
    obs = rd._Observation(HOST, PORT)
    _seed_owner(obs)
    # 复活/换身: 新 pid 绑端口 => owner 记录覆盖(旧死证被新身接替)
    assert obs.tick({200: _ident(600.0)}, {"pid": 200, "ct": 600.0}, None, 600.0) is True
    assert obs.owner == _owner_record(200, 600.0, 600.0)
    # 换身前在未决集的面, 升格即出队
    obs2 = rd._Observation(HOST, PORT)
    _seed_owner(obs2)
    assert obs2.tick({200: _ident(600.0)}, None, {200: frozenset({9999})}, 590.0) is False, "先进未决"
    assert 200 in obs2.pending
    assert obs2.tick({200: _ident(600.0)}, {"pid": 200, "ct": 600.0}, {200: frozenset({9999})}, 600.0) is True
    assert obs2.owner == _owner_record(200, 600.0, 600.0) and obs2.pending == {}
    # PID 复用: 同 pid 异 ct 绑端口 => owner 的 ct 换新(死证基线跟着换)
    obs3 = rd._Observation(HOST, PORT)
    _seed_owner(obs3)
    assert obs3.tick({100: _ident(700.0)}, {"pid": 100, "ct": 700.0}, None, 600.0) is True
    assert obs3.owner == _owner_record(100, 700.0, 600.0)
    # 在位续证: 同 pid 同 ct 候选命中 => ts 内存刷新但不触发落盘
    obs4 = rd._Observation(HOST, PORT)
    _seed_owner(obs4)
    assert obs4.tick({100: _ident(100.0)}, {"pid": 100, "ct": 100.0}, None, 590.0) is False
    assert obs4.owner == _owner_record(100, 100.0, 590.0), "ts 刷新在内存"
    # 早于 owner 实例的面(ct < owner.ct)被零赌注吸收后绑回端口(R3/R4 角落): 出 absorbed 转 owner
    obs5 = rd._Observation(HOST, PORT)
    _seed_owner(obs5, now=500.0, pid=100, ct=100.0)
    assert obs5.tick({200: _ident(50.0)}, None, None, 505.0) is True, "零赌注吸收(ct < owner.ct)"
    assert obs5.tick({200: _ident(50.0)}, {"pid": 200, "ct": 50.0}, None, 600.0) is True
    assert obs5.owner == _owner_record(200, 50.0, 600.0) and obs5.absorbed == []


def test_observation_owner_record_survives_death():
    """owner 死亡(owner pid 从名册消失)时 owner 记录保留 —— 它就是死证, 只有复活/换身
    才覆盖; 名册 {} 时零持久面变更(不吸收不清出)"""
    obs = rd._Observation(HOST, PORT)
    _seed_owner(obs)
    assert obs.tick({}, None, None, 600.0) is False, "名册空: 零持久面变更"
    assert obs.owner == _owner_record(100, 100.0, 500.0), "死证保留"
    assert obs.tick({200: _ident(600.0)}, {"pid": 200, "ct": 600.0}, None, 610.0) is True
    assert obs.owner == _owner_record(200, 600.0, 610.0), "只有复活/换身才覆盖"


def test_observation_settle_absorb_row3_and_reset():
    """§03.2 行三: 监听集指纹稳定 NEW_FACE_SETTLE 且不含我们端口 => 吸收(持久面变更);
    指纹变了/通道不可用 => settle 重算(不把观察间隙当稳定); 空指纹(已创建未绑端口)受
    同一有界赌注(R3); 指纹含我们端口永不 settle(绑定证据已在, 行二未命中 = 归属没跟上,
    保守挡)"""
    assert rd.NEW_FACE_SETTLE == 30.0, "常量数值与 §03.2/§07 R3 一致"
    obs = rd._Observation(HOST, PORT)
    _seed_owner(obs)
    roster = {100: _ident(100.0), 200: _ident(600.0)}
    fp = frozenset({8081, 9090})
    assert obs.tick(roster, None, {200: fp}, 600.0) is False, "新面孔进未决(内存面, 非落盘时机)"
    assert obs.pending[200]["first_seen"] == 600.0
    assert obs.tick(roster, None, {200: fp}, 620.0) is False, "未满 30s 仍未决(挡窗)"
    assert obs.tick(roster, None, {200: fp}, 631.0) is True, "稳定 31s => settle 吸收"
    assert obs.absorbed == [{"pid": 200, "ct": 600.0, "ts": 631.0}] and obs.pending == {}
    # 指纹变了重算: 变更拍重置 first_seen
    obs2 = rd._Observation(HOST, PORT)
    _seed_owner(obs2)
    roster2 = {100: _ident(100.0), 200: _ident(600.0)}
    assert obs2.tick(roster2, None, {200: frozenset({8081})}, 600.0) is False
    assert obs2.tick(roster2, None, {200: frozenset({8081, 9090})}, 620.0) is False, "指纹变了 => 重算"
    assert obs2.pending[200]["first_seen"] == 620.0
    assert obs2.tick(roster2, None, {200: frozenset({8081, 9090})}, 645.0) is False, "重算后 25s 仍未决"
    assert obs2.tick(roster2, None, {200: frozenset({8081, 9090})}, 651.0) is True, "重算后满 31s => 吸收"
    # 空指纹(已创建未绑端口)按同一有界赌注 settle —— §03.2 尾部赌注的本体
    obs3 = rd._Observation(HOST, PORT)
    _seed_owner(obs3)
    roster3 = {100: _ident(100.0), 200: _ident(600.0)}
    assert obs3.tick(roster3, None, {200: frozenset()}, 600.0) is False
    assert obs3.tick(roster3, None, {200: frozenset()}, 631.0) is True, "空集稳定 31s => 吸收(R3)"
    # 指纹含我们端口: 永不 settle
    obs4 = rd._Observation(HOST, PORT)
    _seed_owner(obs4)
    roster4 = {100: _ident(100.0), 200: _ident(600.0)}
    ours = frozenset({PORT, 8081})
    for t in (600.0, 700.0, 800.0):
        assert obs4.tick(roster4, None, {200: ours}, t) is False
    assert 200 in obs4.pending and obs4.absorbed == []
    # 指纹通道不可用(None): 计时重置, 无证据不吸收
    obs5 = rd._Observation(HOST, PORT)
    _seed_owner(obs5)
    roster5 = {100: _ident(100.0), 200: _ident(600.0)}
    assert obs5.tick(roster5, None, {200: frozenset({8081})}, 600.0) is False
    assert obs5.tick(roster5, None, None, 610.0) is False, "通道断 => 计时重置"
    assert obs5.pending[200]["first_seen"] == 610.0
    assert obs5.tick(roster5, None, {200: frozenset({8081})}, 620.0) is False, "证据恢复 => 从头计时"
    assert obs5.pending[200]["first_seen"] == 620.0
    assert obs5.tick(roster5, None, {200: frozenset({8081})}, 651.0) is True, "稳定 31s => 吸收"


def test_observation_pending_blocks_and_leaves_on_disappear_row4():
    """§03.2 行四: 未决成员挡 L1(owner 死证 + 端口拒连已齐也不开); 从名册消失即出队
    (重现按新面孔重算, settle 重来); PID 复用(同 pid 异 ct)同样出队重算"""
    obs = rd._Observation(HOST, PORT)
    _seed_owner(obs)
    roster = {100: _ident(100.0), 200: _ident(600.0)}
    assert obs.tick(roster, None, {200: frozenset({8081})}, 600.0) is False
    assert obs.l1_open(roster, True) is False, "未决挡窗(死证/拒连已齐)"
    assert obs.l1_open(roster, False) is False
    assert obs.tick({100: _ident(100.0)}, None, None, 610.0) is False, "面 200 消失 => 出队(内存面)"
    assert obs.pending == {}
    assert obs.l1_open({100: _ident(100.0)}, True) is False, "owner 在位, L1 仍不开"
    assert obs.l1_open({}, True) is True, "owner 死 + 拒连 + 无未决 => 立即进窗"
    assert obs.tick(roster, None, {200: frozenset({8081})}, 700.0) is False, "重现: 全新计时"
    assert obs.pending[200]["first_seen"] == 700.0
    # PID 复用: 同 pid 异 ct => 旧未决出队, 新面孔重进
    obs2 = rd._Observation(HOST, PORT)
    _seed_owner(obs2)
    obs2.tick({100: _ident(100.0), 200: _ident(600.0)}, None, {200: frozenset({8081})}, 600.0)
    obs2.tick({100: _ident(100.0), 200: _ident(999.0)}, None, {200: frozenset({8081})}, 610.0)
    assert obs2.pending[200] == {"ct": 999.0, "first_seen": 610.0, "fp": frozenset({8081})}


def test_observation_absorbed_release_and_pid_reuse():
    """absorbed 成员从名册消失即移出(持久面变更 => 落盘时机, payload 不含死者); pid 被
    复用(ct 不等)时旧条目同样清出、新面孔重新分类(N1 关键面: 复用者不得继承吸收身份)"""
    obs = rd._Observation(HOST, PORT)
    _seed_owner(obs, now=500.0, pid=100, ct=100.0)
    obs.tick({100: _ident(100.0), 200: _ident(50.0)}, None, None, 505.0)  # 零赌注吸收(ct < owner.ct)
    assert obs.absorbed == [{"pid": 200, "ct": 50.0, "ts": 505.0}]
    assert obs.tick({100: _ident(100.0)}, None, None, 600.0) is True, "死者清出 = 持久面变更"
    assert obs.absorbed == []
    restored = rd._Observation.from_payload(obs.to_payload(600.0), HOST, PORT)
    assert restored is not None and restored.absorbed == [], "payload 不含死者"
    # PID 复用: 吸收身份不得继承
    obs2 = rd._Observation(HOST, PORT)
    _seed_owner(obs2, now=500.0, pid=100, ct=100.0)
    obs2.tick({100: _ident(100.0), 200: _ident(50.0)}, None, None, 505.0)
    assert obs2.tick({100: _ident(100.0), 200: _ident(900.0)}, None, {200: frozenset({8081})}, 600.0) is True
    assert obs2.absorbed == [], "复用者不继承吸收身份"
    assert obs2.pending[200]["ct"] == 900.0, "复用者按新面孔走未决/settle"


def test_observation_l1_open_truth_table():
    """§03.3 真值表: owner 死三形态(pid 无进程 / ct 不等 / 映像名非 qB)× 端口拒连 ×
    未决成员; 无 owner 记录 => False(L1 不适用); 名册 None => None(本拍不可判, 与
    「不成立」可区分); 名册 {} + owner 记录 => 死证成立(立即进窗, 无稳定期)"""
    obs = rd._Observation(HOST, PORT)
    assert obs.l1_open({}, True) is False, "无 owner 记录: L1 不适用"
    assert obs.l1_open(None, True) is None, "名册 None => 本拍不可判"
    _seed_owner(obs)
    alive = {100: _ident(100.0)}
    dead_absent = {200: _ident(600.0)}
    dead_ct = {100: _ident(999.0)}
    dead_name = {100: {"name": "chrome", "ct": 100.0}}
    assert obs.l1_open(alive, True) is False, "owner 在位: 死证不成立"
    assert obs.l1_open(alive, False) is False
    for roster, tag in ((dead_absent, "pid无进程"), (dead_ct, "ct不等"), (dead_name, "映像非qB")):
        assert obs.l1_open(roster, True) is True, f"死证[{tag}] + 拒连 + 无未决 => 立即进窗"
        assert obs.l1_open(roster, False) is False, f"死证[{tag}] + 端口在服 => 不成立"
    # 未决成员一票挡窗(l1_open 纯读, 不清未决)
    assert obs.tick(dead_absent, None, {200: frozenset({8081})}, 600.0) is False
    assert obs.l1_open(dead_absent, True) is False, "未决挡窗"
    assert obs.l1_open({}, True) is False, "名册 {} 也不清未决(纯读)"
    assert obs.tick({}, None, None, 700.0) is False, "面 200 消失 => 未决出队(内存面, 非落盘变更)"
    assert obs.pending == {}
    assert obs.l1_open({}, True) is True, "名册 {} + owner 记录 => 死证成立 => 立即进窗"
    assert obs.l1_open({}, False) is False
    assert obs.l1_open(None, True) is None


def test_observation_payload_roundtrip_and_bad_shape_is_none():
    """序列化: to_payload -> from_payload 回环幂等; owner/absorbed 恢复、未决清空(settle
    重算, §03.2 hint); 坏 payload(非 dict/host 不符或非 str/port 不符或 bool 或数值串/
    owner 或 absorbed 形不符/absorbed 缺键)=> None 保守弃, 不抛"""
    obs = rd._Observation(HOST, PORT)
    _seed_owner(obs, now=500.0, pid=100, ct=100.0)
    obs.tick({100: _ident(100.0), 200: _ident(50.0)}, None, None, 505.0)  # absorbed(零赌注: ct < owner.ct)
    obs.tick(
        {
            100: _ident(100.0),
            200: _ident(50.0),
            300: _ident(600.0)
        }, None, {300: frozenset({8081})}, 600.0
    )  # pending(200 仍在名册, 不清出)
    payload = obs.to_payload(610.0)
    assert payload == {
        "host": HOST,
        "port": PORT,
        "owner": _owner_record(100, 100.0, 500.0),
        "absorbed": [{
            "pid": 200,
            "ct": 50.0,
            "ts": 505.0
        }],
        "ts": 610.0,
    }
    obs2 = rd._Observation.from_payload(payload, HOST, PORT)
    assert obs2 is not None
    assert obs2.owner == obs.owner and obs2.absorbed == obs.absorbed
    assert obs2.pending == {}, "未决不持久: 重启 settle 重算"
    assert rd._Observation.from_payload(obs2.to_payload(610.0), HOST, PORT).to_payload(610.0) == payload, "回环幂等"
    bads = [
        None,
        [1, 2],
        {},
        {
            "host": "10.0.0.9",
            "port": PORT,
            "owner": None,
            "absorbed": []
        },  # host 不符(跨实例拒载)
        {
            "host": HOST,
            "port": PORT + 1,
            "owner": None,
            "absorbed": []
        },  # port 不符
        {
            "host": HOST,
            "port": True,
            "owner": None,
            "absorbed": []
        },  # port bool 冒充 1
        {
            "host": HOST,
            "port": str(PORT),
            "owner": None,
            "absorbed": []
        },  # port 数值串
        {
            "host": "",
            "port": PORT,
            "owner": None,
            "absorbed": []
        },  # host 空串
        {
            "host": 5,
            "port": PORT,
            "owner": None,
            "absorbed": []
        },  # host 非 str
        {
            "host": HOST,
            "port": PORT,
            "owner": "junk",
            "absorbed": []
        },  # owner 非 dict
        {
            "host": HOST,
            "port": PORT,
            "owner": {
                "pid": "1",
                "ct": 1.0,
                "ts": 1.0
            },
            "absorbed": []
        },  # owner 混型
        {
            "host": HOST,
            "port": PORT,
            "owner": None,
            "absorbed": "junk"
        },  # absorbed 非 list
        {
            "host": HOST,
            "port": PORT,
            "owner": None,
            "absorbed": ["junk"]
        },  # absorbed 成员形不符
        {
            "host": HOST,
            "port": PORT,
            "owner": None
        },  # absorbed 缺键(非本链产物)
    ]
    for body in bads:
        assert rd._Observation.from_payload(body, HOST, PORT) is None, body
    ok = rd._Observation.from_payload(
        {
            "host": HOST,
            "port": PORT,
            "owner": None,
            "absorbed": [],
            "ts": 1.0
        }, HOST, PORT
    )
    assert ok is not None and ok.owner is None and ok.absorbed == [] and ok.pending == {}, "合法冷态载荷可载"


# ---------------------------------------------------------------------------
# 接线面(W2a, 计划 26-11-10-0318 §04 W2 的 1-3 项): run/_process_window 三层判据接线 + 观测
# 维护 tick 契约 + 复验升级 + warning 节流。既有桩全沿用(_stub_qb 的观测通道并桩把既有
# 用例钉在 L2 等价面); L1 路径用可控 roster/监听映射桩(_stub_obs); 场景级全链端到端
# (场景 X/Y、PID 复用两端向、obs 跨重启端到端)留 W2b —— 本波的重启恢复是接线级单测
# (from_payload 恢复面), 本波只做接线级单测
# ---------------------------------------------------------------------------


def _pending_job(tmp_path: Path, data_dir: str, tag: bytes = b"m-1") -> str:
    """标准待收尾 job 造法(单成员, src/dst/BT_backup 就位), 返回 v1 hash —— 接线面专测
    共用的最小 pending 形态(既有 _member_fixture/_write_job 的封装)"""
    tmp_path.joinpath("src").mkdir(exist_ok=True)
    tmp_path.joinpath("dst").mkdir(exist_ok=True)
    h1 = _member_fixture(tmp_path / "BT_backup", tag, str(tmp_path / "src"))
    _write_job(tmp_path, data_dir, "job-1", [h1], src=str(tmp_path / "src"), dst=str(tmp_path / "dst"))
    return h1


def _seed_obs(data_dir: str, owner, absorbed=None, ts: float = 500.0) -> None:
    """obs 文件播种(模拟前世 daemon 的归档; 走 write_obs 真实路径, schema_version 由写侧
    钉上)—— owner 非 None = 前世见过该实例(pid/ct 为 OS 身份), ts = 归档时刻"""
    assert rj.write_obs(
        data_dir, rj.instance_key(HOST, PORT), {
            "host": HOST,
            "port": PORT,
            "owner": owner,
            "absorbed": [] if absorbed is None else absorbed,
            "ts": ts
        }
    )


def _stub_obs(monkeypatch, st):
    """观测通道注入(W2a 接线面): roster(_qb_processes)/全机监听映射(_listening_map)按 st
    现值返回(可变 dict, 桩每拍读现值 => 测试可中途翻面)—— 与 _stub_qb 的联动风格同款;
    roster=None 模拟通道不可用(None), {} 模拟健康零观测"""
    monkeypatch.setattr(rd, "_qb_processes", lambda *a, **k: st.get("roster"))
    monkeypatch.setattr(rd, "_listening_map", lambda *a, **k: st.get("listen_map"))


def test_run_l1_dead_owner_enters_window_without_stable_wait(tmp_path, monkeypatch):
    """L1 verdict True 立即进窗(拍板 D2, 无 down_since 计时): obs 死证(owner pid 已从
    名册消失)+ 端口拒连 + 无未决 => 首拍即进窗改写 —— stable(1000s)远超 max_wait 仍完成
    (时钟注入证明无 30s 等待; 同形态无死证走 L2 则 timeout 零落盘, 见等价面专测)"""
    data_dir = str(tmp_path / "data")
    h1 = _pending_job(tmp_path, data_dir)
    _seed_obs(data_dir, {"pid": 4242, "ct": 100.0, "ts": 500.0})  # 前世归档: owner 曾在, 现已死
    _stub_qb(monkeypatch, {"up": False})
    _stub_obs(monkeypatch, {"roster": {}, "listen_map": None})  # 名册健康零观测: 4242 不在 => 死证成立
    assert _run(data_dir, stable=1000.0, max_wait=60.0) == "idle"
    rw = rj.read_rewrites(data_dir, "job-1")
    assert rw[h1]["status"] == "rewritten", "L1 首拍进窗改写(stable=1000 未阻)"
    assert rj.read_journal(data_dir, "job-1")["phase"] == rj.PHASE_REWRITTEN
    d = frmod.load_fastresume(_fr_path(tmp_path, h1))
    assert d[b"qBt-savePath"] == (str(tmp_path / "dst").replace("\\", "/") + "/m-1").encode("utf-8")


def test_run_no_owner_record_walks_l2_stable_window_equivalent(tmp_path, monkeypatch, caplog):
    """等价面(硬要求): 无 owner 记录(obs 缺失)=> verdict False 走 L2 现状三证原样 ——
    30s 稳定期保留, 窗口时序不早于接线前(与 test_run_waits_for_stable_window_before_window
    同形态:
    stable 未满 timeout 零落盘); verdict False 是正常路径不告警(区别于通道故障);
    目标未上线不建档, obs 文件零写"""
    data_dir = str(tmp_path / "data")
    h1 = _pending_job(tmp_path, data_dir)
    before = _fr_path(tmp_path, h1).read_bytes()
    _stub_qb(monkeypatch, {"up": False})
    _stub_obs(monkeypatch, {"roster": {}, "listen_map": None})  # 名册健康但无 owner 记录 => L1 不适用
    with caplog.at_level(logging.WARNING, logger=LOG_RD):
        assert _run(data_dir, stable=100.0, max_wait=25.0) == "timeout", "L2 30s 稳定期保留(等价面)"
    assert not [r for r in caplog.records if "退 L2" in r.message], "verdict False 不告警"
    assert rj.read_rewrites(data_dir, "job-1") == {} and _fr_path(tmp_path, h1).read_bytes() == before, "零落盘"
    assert rj.read_obs(data_dir, rj.instance_key(HOST, PORT)) is None, "obs 零写(目标未上线不建档)"


def test_run_l1_roster_channel_broken_falls_back_l2_throttled(tmp_path, monkeypatch, caplog):
    """名册通道故障(qB 身份枚举不可用)=> l1_open None 即便有有效死证也不进窗(通道故障
    绝不冒充通过)⇒ 退 L2 现状判据 + 节流 warning(§03.1 通道纪律): 60s 内多拍只首拍一条;
    跨过 60s 边界的窗口期再计一条(拍点 5s 步进: 140s 窗 28 拍恰 3 条 —— 1015/1075/1135);
    roster None => tick 整拍不动, obs 文件零写(死证播种原样)"""
    data_dir = str(tmp_path / "data")
    _pending_job(tmp_path, data_dir)
    _seed_obs(data_dir, {"pid": 4242, "ct": 100.0, "ts": 500.0})
    _stub_qb(monkeypatch, {"up": False})  # S1 并桩: roster/listen_map 恒 None(通道不可用)
    seeded = rj.read_obs(data_dir, rj.instance_key(HOST, PORT))
    with caplog.at_level(logging.WARNING, logger=LOG_RD):
        assert _run(data_dir, stable=1000.0, max_wait=50.0) == "timeout", "有死证但通道故障: 不进窗"
        n1 = len([r for r in caplog.records if "不可判" in r.message])
        assert n1 == 1, f"60s 内多拍只首拍一条, 实得 {n1}"
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger=LOG_RD):
        assert _run(data_dir, stable=1000.0, max_wait=140.0) == "timeout"
        n2 = len([r for r in caplog.records if "不可判" in r.message])
        assert n2 == 3, f"跨 60s 边界再计(不刷屏), 实得 {n2}"
    assert rj.read_obs(data_dir, rj.instance_key(HOST, PORT)) == seeded, "roster None => tick 整拍不动, obs 零写"
    assert rj.read_rewrites(data_dir, "job-1") == {}, "通道故障零改写"


def test_run_l1_window_reverify_owner_revive_aborts(tmp_path, monkeypatch):
    """复验升级(§03.3 硬要求): L1 窗的窗内复验 = 全套现读现判 —— 进窗判据与窗内复验之间
    owner 复活(名册重现同 pid 同 ct + 端口回绑)=> 复验不过 => qb_back 中止, 零成员落盘
    (现状中止/重试语义原样, 不新增行为); 复活在位续证只刷内存 ts, obs 持久面零变更"""
    data_dir = str(tmp_path / "data")
    h1 = _pending_job(tmp_path, data_dir)
    before = _fr_path(tmp_path, h1).read_bytes()
    _seed_obs(data_dir, {"pid": 100, "ct": 100.0, "ts": 500.0})
    st = {"phase": "dead"}  # dead => revived: 翻面点 = L1 窗内复验首次现读名册(第 2 次 _qb_processes 调用)

    def _connect(addr, timeout=None):
        if st["phase"] == "revived":
            return mock.MagicMock()
        raise OSError(10061, "refused")

    def _roster(*a, **k):
        st["calls"] = st.get("calls", 0) + 1
        if st["calls"] >= 2:
            st["phase"] = "revived"
        return {} if st["phase"] == "dead" else {100: _ident(100.0)}

    monkeypatch.setattr(rd.socket, "create_connection", _connect)
    monkeypatch.setattr(rd, "_qb_processes", _roster)
    monkeypatch.setattr(
        rd, "_listening_map", lambda *a, **k: None if st["phase"] == "dead" else {100: frozenset({PORT})}
    )
    monkeypatch.setattr(
        rd, "_qb_process_names", lambda: ("explorer.exe", ) if st["phase"] == "dead" else ("qbittorrent.exe", )
    )
    assert _run(data_dir, stable=1000.0, max_wait=60.0) == "timeout", "复验不过 => qb_back, 无窗可再进"
    assert rj.read_rewrites(data_dir, "job-1") == {} and _fr_path(tmp_path, h1).read_bytes() == before, "零落盘"
    st2 = rj.read_obs(data_dir, rj.instance_key(HOST, PORT))
    assert st2["owner"] == {"pid": 100, "ct": 100.0, "ts": 500.0}, "在位续证只在内存, obs 持久面零变更"


def test_run_obs_tick_persists_changed_state_only(tmp_path, monkeypatch):
    """观测维护 tick 契约: 持久面变更(tick True)才 write_obs —— 新面孔零赌注吸收(ct <
    owner.ct)首拍落盘一次; 同一 roster 的后续拍零持久面变更不重写(owner 在位续证只在
    内存)—— 多拍写次数钉死 = 1; 文件内容对齐 obs schema(owner 原样 + absorbed 新条目)"""
    data_dir = str(tmp_path / "data")
    _pending_job(tmp_path, data_dir)
    _seed_obs(data_dir, {"pid": 100, "ct": 100.0, "ts": 500.0})  # owner 在位: 不进窗, 纯观测维护
    _stub_qb(monkeypatch, {"up": True})
    _stub_obs(monkeypatch, {"roster": {100: _ident(100.0), 200: _ident(50.0)}, "listen_map": {100: frozenset({PORT})}})
    calls = {"n": 0}
    real_write = rj.write_obs

    def _count_write(*a, **k):
        calls["n"] += 1
        return real_write(*a, **k)

    monkeypatch.setattr(rj, "write_obs", _count_write)
    assert _run(data_dir, stable=1000.0, max_wait=50.0) == "timeout", "owner 在位: 无窗, 多拍观测维护"
    assert calls["n"] == 1, f"变更拍写一次, 后续拍零变更不重写, 实得 {calls['n']}"
    st = rj.read_obs(data_dir, rj.instance_key(HOST, PORT))
    # owner 身份原样; ts = 变更拍(吸收同拍)的观测时刻 —— 续证单独不触发落盘, 但同拍有
    # 其它变更时落的是内存已刷新的 ts(契约口径: 刷新只在内存「不单独触发写」, 非隔离快照)
    assert st["owner"]["pid"] == 100 and st["owner"]["ct"] == 100.0 and st["owner"]["ts"] > 500.0, "owner 身份原样"
    assert len(st["absorbed"]) == 1, "零赌注吸收进 absorbed"
    assert st["absorbed"][0]["pid"] == 200 and st["absorbed"][0]["ct"] == 50.0 and st["absorbed"][0]["ts"] > 500.0
    assert rj.read_rewrites(data_dir, "job-1") == {}, "零改写(未进窗)"


def test_run_obs_write_failure_throttled_warning_no_crash(tmp_path, monkeypatch, caplog):
    """obs 落盘失败(盘故障)=> 节流 warning 留痕不崩, 内存态继续跑(重启丢观测退 L2, 安全
    向): 每 poll 新面孔吸收都触发写尝试, 60s 内多拍只首拍一条; daemon 结论正常产出
    (timeout 收束), obs 文件保持种子原样(无一次覆盖)"""
    data_dir = str(tmp_path / "data")
    _pending_job(tmp_path, data_dir)
    _seed_obs(data_dir, {"pid": 100, "ct": 100.0, "ts": 500.0})  # owner 在位: 持续观测, 不进窗
    seeded = rj.read_obs(data_dir, rj.instance_key(HOST, PORT))
    _stub_qb(monkeypatch, {"up": True})
    seq = {"k": 0}

    def _roster(*a, **k):
        seq["k"] += 1
        faces = {p: _ident(50.0) for p in range(200, 200 + seq["k"])}  # 每 poll 一个新面孔(全部早于 owner)
        faces[100] = _ident(100.0)
        return faces

    monkeypatch.setattr(rd, "_qb_processes", _roster)
    monkeypatch.setattr(rd, "_listening_map", lambda *a, **k: {100: frozenset({PORT})})
    monkeypatch.setattr(rj, "write_obs", lambda *a, **k: False)  # 盘故障: 恒失败
    with caplog.at_level(logging.WARNING, logger=LOG_RD):
        assert _run(data_dir, stable=1000.0, max_wait=50.0) == "timeout", "写失败不崩, daemon 照常收束"
        n = len([r for r in caplog.records if "落盘失败" in r.message])
        assert n == 1, f"60s 内多拍写失败只首拍一条, 实得 {n}"
    assert rj.read_obs(data_dir, rj.instance_key(HOST, PORT)) == seeded, "写恒失败: 种子原样, 无一次覆盖"


def test_run_restarts_restore_owner_evidence_from_obs_file(tmp_path, monkeypatch):
    """daemon 重启恢复(§03.4, 覆盖「停机期间目标死亡」): 前世 daemon 经真实观测通道归档
    在位 owner(tick 建档落盘)=> 停机期间目标死亡 => 新世 from_payload 恢复死证 => 立即
    进窗改写(无 30s 等待); obs 记录跨重启保留(新世 tick 无变更不重写)"""
    data_dir = str(tmp_path / "data")
    h1 = _pending_job(tmp_path, data_dir)
    # 前世: 目标在线(owner 绑端口), 只做观测维护(owner 活着不进窗), timeout 收束
    _stub_qb(monkeypatch, {"up": True})
    _stub_obs(monkeypatch, {"roster": {100: _ident(100.0)}, "listen_map": {100: frozenset({PORT})}})
    assert _run(data_dir, stable=1000.0, max_wait=20.0) == "timeout"
    seeded = rj.read_obs(data_dir, rj.instance_key(HOST, PORT))
    assert seeded["owner"]["pid"] == 100 and seeded["owner"]["ct"] == 100.0, "前世已归档在位 owner"
    # 新世: 停机期间目标死亡(名册零观测 + 端口拒连)—— obs 文件里的 owner 记录 = 有效死证
    _stub_qb(monkeypatch, {"up": False})
    _stub_obs(monkeypatch, {"roster": {}, "listen_map": None})
    assert _run(data_dir, stable=1000.0, max_wait=60.0) == "idle"
    rw = rj.read_rewrites(data_dir, "job-1")
    assert rw[h1]["status"] == "rewritten", "恢复的死证驱动 L1 立即进窗"
    assert rj.read_obs(data_dir, rj.instance_key(HOST, PORT)) == seeded, "死证记录跨重启保留"


def test_run_corrupt_obs_file_starts_empty_and_stays_l2(tmp_path, monkeypatch):
    """obs 文件坏形(非 JSON 半残文件)=> read_obs None => 新建空 _Observation 走 L2(D3
    冷启动形态: 等目标下次上线建档): 不崩溃、不覆盖坏文件(tick 无变更不落盘)、窗口时序
    按 L2 现状(30s 保留)"""
    data_dir = str(tmp_path / "data")
    _pending_job(tmp_path, data_dir)
    _stub_qb(monkeypatch, {"up": False})
    _stub_obs(monkeypatch, {"roster": {}, "listen_map": None})
    obs_file = Path(rj.obs_path(data_dir, rj.instance_key(HOST, PORT)))
    obs_file.parent.mkdir(parents=True, exist_ok=True)
    obs_file.write_bytes(b"not-json-at-all")
    assert _run(data_dir, stable=100.0, max_wait=25.0) == "timeout", "坏记录不冒充证据 => L2 30s 保留"
    assert rj.read_rewrites(data_dir, "job-1") == {}
    assert obs_file.read_bytes() == b"not-json-at-all", "坏文件不覆盖(零变更不落盘)"


def test_run_observation_channels_not_polled_without_pending(tmp_path, monkeypatch):
    """§03.1 口径: 观测维护仅 pending 非空时跑 —— 空载拍(无 job)观测通道零调用(§07 R1
    子进程预算只花在有活的拍上)"""
    data_dir = str(tmp_path / "data")
    calls = {"roster": 0, "lmap": 0}
    monkeypatch.setattr(rd, "_qb_processes", lambda *a, **k: calls.__setitem__("roster", calls["roster"] + 1))
    monkeypatch.setattr(rd, "_listening_map", lambda *a, **k: calls.__setitem__("lmap", calls["lmap"] + 1))
    assert _run(data_dir) == "idle"
    assert calls == {"roster": 0, "lmap": 0}, "空载零通道调用"


# ---------------------------------------------------------------------------
# 复验现判补强(W2a 编排方裁决, 计划 §03.3 第 3 条件「现判」化): _Observation.unclassified_faces
# 纯分类读并入 _l1_window_open —— 窗内复验不再只看进窗时的 pending 快照, 现读名册里状态机
# 不能立即出具「无害」结论的面一律复验不过(qb_back); 新面由下一拍 tick 正规分类后窗可重开
# ---------------------------------------------------------------------------


def _flip_to_face_at_reverify(monkeypatch, st, face):
    """复验翻面桩: 第 2 次 _qb_processes 调用(L1 窗顶复验的现读点)起名册现值翻出 face ——
    翻面点即「进窗判据与窗内复验之间」的世界变化; socket 全程拒连(目标已死, 新面不绑端口),
    _qb_process_names 与名册联动(face 在场 = 全机名册见 qB, L2 亦不得开窗)"""
    def _connect(addr, timeout=None):
        raise OSError(10061, "refused")

    def _roster(*a, **k):
        st["calls"] = st.get("calls", 0) + 1
        if st["calls"] >= 2:
            st["phase"] = "face"
        return {} if st["phase"] == "dead" else dict(face)

    monkeypatch.setattr(rd.socket, "create_connection", _connect)
    monkeypatch.setattr(rd, "_qb_processes", _roster)
    monkeypatch.setattr(
        rd, "_qb_process_names", lambda: ("explorer.exe", ) if st["phase"] == "dead" else ("qbittorrent.exe", )
    )


def test_run_l1_window_reverify_unclassified_face_blocks(tmp_path, monkeypatch):
    """复验现判补强(裁决项一): L1 窗开启后、窗顶复验现读名册冒出全新未分类面(pid/ct 状态机从未
    见过)=> l1_open 三条件全齐也复验不过 => qb_back 零落盘 —— 条件 3 的「无未决」不能只看
    进窗时 pending 快照; 面进未决后指纹通道不可用 => 永滞未决, 窗不再开, timeout 收束"""
    data_dir = str(tmp_path / "data")
    h1 = _pending_job(tmp_path, data_dir)
    before = _fr_path(tmp_path, h1).read_bytes()
    _seed_obs(data_dir, {"pid": 4242, "ct": 100.0, "ts": 500.0})
    st = {"phase": "dead"}
    _flip_to_face_at_reverify(monkeypatch, st, {200: _ident(600.0)})
    monkeypatch.setattr(rd, "_listening_map", lambda *a, **k: None)  # 指纹通道断: 未决面不 settle
    assert _run(data_dir, stable=1000.0, max_wait=60.0) == "timeout", "未分类面挡复验 => qb_back, 无窗可再进"
    assert rj.read_rewrites(data_dir, "job-1") == {} and _fr_path(tmp_path, h1).read_bytes() == before, "零落盘"
    assert rj.read_obs(data_dir, rj.instance_key(HOST, PORT))["absorbed"] == [], "面滞未决(内存面), 无吸收落盘"


def test_run_l1_window_reopens_after_settle_absorb(tmp_path, monkeypatch):
    """同面被 tick 正规吸收后窗重开: 未分类面进未决后, 指纹稳定 NEW_FACE_SETTLE 且不含
    我们端口 => settle 吸收(§03.2 行三, 持久面落盘)—— 下一拍 L1 verdict 复为 True 且复验
    分类读见 absorbed 命中 => 窗重开改写收口(挡是暂态不是死锁, 与状态机设计自洽)"""
    data_dir = str(tmp_path / "data")
    h1 = _pending_job(tmp_path, data_dir)
    _seed_obs(data_dir, {"pid": 4242, "ct": 100.0, "ts": 500.0})
    st = {"phase": "dead"}
    _flip_to_face_at_reverify(monkeypatch, st, {200: _ident(600.0)})
    monkeypatch.setattr(rd, "_listening_map", lambda *a, **k: {200: frozenset({8081})})  # 指纹稳定且不含我们端口
    assert _run(data_dir, stable=1000.0, max_wait=120.0) == "idle", "settle 吸收后窗重开并收口"
    rw = rj.read_rewrites(data_dir, "job-1")
    assert rw[h1]["status"] == "rewritten", "吸收后 L1 重开改写"
    st2 = rj.read_obs(data_dir, rj.instance_key(HOST, PORT))
    assert len(st2["absorbed"]) == 1 and st2["absorbed"][0]["pid"] == 200 and st2["absorbed"][0]["ct"] == 600.0
    assert st2["absorbed"][0]["ts"] > 500.0, "面已正规吸收落盘"


def test_run_l1_window_reverify_absorbed_face_does_not_block(tmp_path, monkeypatch):
    """absorbed 命中面复验不挡: 名册现读里命中 absorbed(pid,ct)的面是状态机已出具
    「无害」结论的面 —— 复验放行, 窗开启改写(分类读不把已吸收面当未分类)"""
    data_dir = str(tmp_path / "data")
    h1 = _pending_job(tmp_path, data_dir)
    _seed_obs(
        data_dir,
        {
            "pid": 4242,
            "ct": 100.0,
            "ts": 500.0
        },
        absorbed=[{
            "pid": 200,
            "ct": 50.0,
            "ts": 505.0
        }],  # 前世已零赌注吸收的面(早于 owner 实例)
    )
    _stub_qb(monkeypatch, {"up": False})
    _stub_obs(monkeypatch, {"roster": {200: _ident(50.0)}, "listen_map": None})
    assert _run(data_dir, stable=1000.0, max_wait=60.0) == "idle"
    assert rj.read_rewrites(data_dir, "job-1")[h1]["status"] == "rewritten", "absorbed 命中面不挡复验"


def test_run_l1_window_reverify_unreadable_ct_face_blocks(tmp_path, monkeypatch):
    """ct 读不出面复验挡: 名册条目身份不完整(无 ct)的状态机结论只能是「未分类」——
    无法证明它是已吸收/在位/已决的哪一类, 保守挡(与 tick 缺 ct 面停未决真挡同向);
    l1_open 三条件全齐也不放行"""
    data_dir = str(tmp_path / "data")
    h1 = _pending_job(tmp_path, data_dir)
    before = _fr_path(tmp_path, h1).read_bytes()
    _seed_obs(data_dir, {"pid": 4242, "ct": 100.0, "ts": 500.0})
    st = {"phase": "dead"}
    _flip_to_face_at_reverify(monkeypatch, st, {200: {"name": "qbittorrent"}})  # 缺 ct 键
    monkeypatch.setattr(rd, "_listening_map", lambda *a, **k: None)
    assert _run(data_dir, stable=1000.0, max_wait=60.0) == "timeout", "缺 ct 面挡复验 => qb_back"
    assert rj.read_rewrites(data_dir, "job-1") == {} and _fr_path(tmp_path, h1).read_bytes() == before, "零落盘"
    assert rj.read_obs(data_dir, rj.instance_key(HOST, PORT))["absorbed"] == [], "缺 ct 面写不进合法 absorbed"


def test_observation_unclassified_faces_classification_table():
    """unclassified_faces 分类表(纯分类读): owner 身份命中/absorbed 命中/pending 在册不进
    清单(三者在 l1_open 各有等价挡); ct 读不出/ct<owner.ct 未及吸收/owner pid 复用面/absorbed
    pid 复用面/全新面一律未分类; 纯读 —— 状态机零变动; 名册空 => 清单空"""
    obs = rd._Observation(HOST, PORT)
    _seed_owner(obs, now=500.0, pid=100, ct=100.0)
    obs.tick({100: _ident(100.0), 200: _ident(50.0)}, None, None, 505.0)  # 200 零赌注吸收
    obs.tick(
        {
            100: _ident(100.0),
            200: _ident(50.0),
            300: _ident(600.0)
        }, None, {300: frozenset({8081})}, 510.0
    )  # 300 进未决(200 须在场, 否则 absorbed 消失清出)
    # roster 字面量 600 放 400 前(插入序与 pid 数值序不同): 钉住返回值 sorted(out) 排序
    roster = {
        100: _ident(100.0),  # owner 本尊(pid+ct 命中)
        200: _ident(50.0),  # absorbed 命中
        300: _ident(600.0),  # pending 在册
        600: {
            "name": "qbittorrent"
        },  # ct 读不出
        400: _ident(700.0),  # 全新面(ct > owner.ct)
        500: _ident(40.0),  # ct < owner.ct 尚未吸收(tick 会零赌注吸收, 此刻未及)
    }
    before = (dict(obs.owner), [dict(e) for e in obs.absorbed], {p: dict(v) for p, v in obs.pending.items()})
    assert obs.unclassified_faces(roster) == [400, 500, 600]
    after = (dict(obs.owner), [dict(e) for e in obs.absorbed], {p: dict(v) for p, v in obs.pending.items()})
    assert before == after, "纯读: 状态机零变动"
    # owner pid 被复用(ct 不等): 不算 owner 身份命中 => 未分类(l1_open 形态二判死的同时,
    # 复用者本体是未分类新面, 不因「原实例已死」放行)
    assert obs.unclassified_faces({100: _ident(999.0)}) == [100]
    # absorbed pid 被复用(ct 不等): absorbed 命中要求 pid+ct 均等, 复用者不继承吸收身份
    # => 未分类(T3 评审 B2, 与 owner 复用向对称; tick 侧旧 absorbed 条目走消失清出重分类)
    assert obs.unclassified_faces({200: _ident(600.0)}) == [200]
    assert obs.unclassified_faces({}) == [], "名册空 => 无未分类面"


def test_run_observe_channel_warnings_throttled_per_class(tmp_path, monkeypatch, caplog):
    """[持续故障节流/通道格式漂移+名册通道故障] 通道函数经接线面节流 sink 告警(T3 评审 A1,
    §03.1 通道纪律「每(实例, 类)1 条/60s」): netstat 空输出零 LISTENING 解析成功(格式漂移
    => obs_listen 类)+ PowerShell 名册缺健康标记(obs_roster 类)+ 接线点处置留痕(listen
    指纹不可用/roster verdict 不可判两类)—— daemon 主循环每 poll 触发, 每类 60s 只首拍
    一条, 跨 60s 边界的窗口期再计一条(拍点 5s 步进, 140s 窗各 3 条); 通道函数缺省直落
    路径(warn=None => logger.warning)由既有通道单测钉住, 零改动仍绿"""
    data_dir = str(tmp_path / "data")
    _pending_job(tmp_path, data_dir)

    def _connect(addr, timeout=None):
        raise OSError(10061, "refused")

    monkeypatch.setattr(rd.socket, "create_connection", _connect)
    monkeypatch.setattr(rd, "_qb_process_names", lambda: ("explorer.exe", "svchost.exe"))
    monkeypatch.setattr(rd.os, "name", "nt")  # 钉 Windows 分派: 双通道都走子进程桩(平台无关)
    _stub_stdout(monkeypatch, "")  # 双通道故障: netstat 空输出(格式漂移)+ PS 缺健康标记
    tags = ("格式漂移", "缺健康标记", "本拍不可判", "未决面本拍不 settle")
    with caplog.at_level(logging.WARNING, logger=LOG_RD):
        assert _run(data_dir, stable=1000.0, max_wait=50.0) == "timeout", "L2 现状收束(通道故障不进窗)"
        counts = {tag: len([r for r in caplog.records if tag in r.message]) for tag in tags}
        assert counts == {"格式漂移": 1, "缺健康标记": 1, "本拍不可判": 1, "未决面本拍不 settle": 1}, counts
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger=LOG_RD):
        assert _run(data_dir, stable=1000.0, max_wait=140.0) == "timeout"
        counts = {tag: len([r for r in caplog.records if tag in r.message]) for tag in tags}
        assert counts == {"格式漂移": 3, "缺健康标记": 3, "本拍不可判": 3, "未决面本拍不 settle": 3}, counts


def test_run_observe_owner_warning_throttled(tmp_path, monkeypatch, caplog):
    """[持续故障节流/占用者告警] 端口可达 + LISTENING 归属唯一 + 占用者非名册 qB =>
    _observe_owner 的占用者告警(非 qB 服务占端口不记录 owner)每 poll 触发, 经 sink
    obs_owner 类节流: 60s 只首拍一条, 跨 60s 边界的窗口期再计一条; 占用者永不建档
    (obs owner 恒 None), 无关名册 qB 面 30s settle 吸收照常(观测维护不因占用者告警阻断)"""
    data_dir = str(tmp_path / "data")
    _pending_job(tmp_path, data_dir)

    def _connect(addr, timeout=None):
        return mock.MagicMock()

    monkeypatch.setattr(rd.socket, "create_connection", _connect)
    monkeypatch.setattr(rd, "_qb_process_names", lambda: ("qbittorrent.exe", ))
    monkeypatch.setattr(rd, "_listening_map", lambda *a, **k: {7777: frozenset({PORT})})  # 非 qB 占用者绑我们端口
    monkeypatch.setattr(rd, "_qb_processes", lambda *a, **k: {100: _ident(100.0)})  # 名册只有无关 qB 实例
    with caplog.at_level(logging.WARNING, logger=LOG_RD):
        assert _run(data_dir, stable=1000.0, max_wait=50.0) == "timeout"
        n1 = len([r for r in caplog.records if "非全机 qB 名册成员" in r.message])
        assert n1 == 1, f"占用者告警 60s 内只首拍一条, 实得 {n1}"
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger=LOG_RD):
        assert _run(data_dir, stable=1000.0, max_wait=140.0) == "timeout"
        n2 = len([r for r in caplog.records if "非全机 qB 名册成员" in r.message])
        assert n2 == 3, f"跨 60s 边界再计, 实得 {n2}"
    st = rj.read_obs(data_dir, rj.instance_key(HOST, PORT))
    assert st["owner"] is None, "占用者永不建档"
    assert len(st["absorbed"]) == 1 and st["absorbed"][0]["pid"] == 100 and st["absorbed"][0]["ct"] == 100.0, \
        "无关 qB 面 settle 吸收照常"


def test_run_owner_attribution_and_occupier_warnings_independent_throttled(tmp_path, monkeypatch, caplog):
    """[持续故障节流/归属与占用者分键] 归属层告警(端口可达 + LISTENING 映射无我们端口 =>
    「未归属成功」)走 obs_listen 类、占用者告警(归属唯一 + 占用者非名册 qB)走 obs_owner
    类 —— 两类 sink 分键后各自 60s 节流互不顶掉(评审轮 2 N1: 交替故障形态下旧共键实现
    第一拍就把对方顶掉): 60s 窗两类各 1 条, 140s 窗各 3 条; 占用者/归属失败都永不建档
    (obs owner 恒 None), 无 owner 记录恒走 L2 等价面(不进窗)"""
    data_dir = str(tmp_path / "data")
    _pending_job(tmp_path, data_dir)

    def _connect(addr, timeout=None):
        return mock.MagicMock()

    monkeypatch.setattr(rd.socket, "create_connection", _connect)
    monkeypatch.setattr(rd, "_qb_process_names", lambda: ("qbittorrent.exe", ))  # 名册见 qB: L2 不开窗, 每 poll 纯观测维护
    monkeypatch.setattr(rd, "_qb_processes", lambda *a, **k: {100: _ident(100.0)})  # 名册只有无关 qB 实例
    st = {"n": 0}

    def _lmap(*a, **k):
        st["n"] += 1
        if st["n"] % 2:
            return {7777: frozenset({PORT})}  # 占用者形态: 非 qB 服务绑我们端口(归属成功 => 占用者告警)
        return {300: frozenset({8081})}  # 归属失败形态: 映射无我们端口 => 「未归属成功」告警

    monkeypatch.setattr(rd, "_listening_map", _lmap)
    with caplog.at_level(logging.WARNING, logger=LOG_RD):
        assert _run(data_dir, stable=1000.0, max_wait=50.0) == "timeout"
        occ = len([r for r in caplog.records if "非全机 qB 名册成员" in r.message])
        att = len([r for r in caplog.records if "未归属成功" in r.message])
        assert occ == 1 and att == 1, f"两类分键: 60s 窗内各自首拍一条互不顶掉, occ={occ} att={att}"
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger=LOG_RD):
        assert _run(data_dir, stable=1000.0, max_wait=140.0) == "timeout"
        occ = len([r for r in caplog.records if "非全机 qB 名册成员" in r.message])
        att = len([r for r in caplog.records if "未归属成功" in r.message])
        assert occ == 3 and att == 3, f"跨 60s 边界再计(每类独立 60s 节流), occ={occ} att={att}"
    assert rj.read_obs(data_dir, rj.instance_key(HOST, PORT))["owner"] is None, "占用者/归属失败都永不建档"


def test_run_l1_reverify_channel_failure_throttled(tmp_path, monkeypatch, caplog):
    """[复验拍通道故障节流] L1 窗内复验(_l1_window_open)现读名册通道故障: 通道告警经
    warn sink 节流(复用 obs_roster 类 —— 与主循环读同一条 qB 名册通道, 同根因不刷屏)、
    verdict None 处置留痕走独立 reverify 键(复验不过 = qb_back 中止本轮, 处置事件不被
    主循环处置留痕顶掉): poll 拍通道健康(verdict True 进窗)/复验拍通道异常的交替形态下,
    60s 窗内多拍复验两类各只首拍一条, 跨 60s 边界再计(140s 窗各 3 条); 复验不过 =>
    qb_back 零落盘(通道故障不冒充通过, 中止语义原样)"""
    data_dir = str(tmp_path / "data")
    _pending_job(tmp_path, data_dir)
    _seed_obs(data_dir, {"pid": 4242, "ct": 100.0, "ts": 500.0})  # 有效死证: poll 拍 verdict True 进窗
    st = {"n": 0}

    def _ps(*, warn=None):
        st["n"] += 1
        if st["n"] % 2:
            return {}  # poll 拍: 通道健康零观测(4242 死证成立 => 立即进窗)
        raise OSError("reverify channel down")  # 复验拍: 通道异常(经真实 _qb_processes dispatch => sink 节流)

    monkeypatch.setattr(rd.os, "name", "nt")  # 钉 Windows 分派: _qb_processes 真实 dispatch(异常经 warn sink 下发)
    monkeypatch.setattr(rd, "_qb_processes_from_powershell", _ps)
    monkeypatch.setattr(rd, "_listening_map", lambda *a, **k: None)  # 指纹通道断(listen 类, 与本测两类互不干扰)
    monkeypatch.setattr(rd, "_qb_process_names", lambda: ("explorer.exe", ))

    def _connect(addr, timeout=None):
        raise OSError(10061, "refused")

    monkeypatch.setattr(rd.socket, "create_connection", _connect)
    with caplog.at_level(logging.WARNING, logger=LOG_RD):
        assert _run(data_dir, stable=1000.0, max_wait=50.0) == "timeout", "复验不过 => qb_back, 无窗可再进"
        ch = len([r for r in caplog.records if "枚举通道异常" in r.message])
        rv = len([r for r in caplog.records if "复验" in r.message])
        assert ch == 1 and rv == 1, f"60s 窗内多拍复验只首拍各一条(通道/处置分键), ch={ch} rv={rv}"
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger=LOG_RD):
        assert _run(data_dir, stable=1000.0, max_wait=140.0) == "timeout"
        ch = len([r for r in caplog.records if "枚举通道异常" in r.message])
        rv = len([r for r in caplog.records if "复验" in r.message])
        assert ch == 3 and rv == 3, f"跨 60s 边界再计(两类独立节流), ch={ch} rv={rv}"
    assert rj.read_rewrites(data_dir, "job-1") == {}, "复验中止零改写(通道故障不冒充通过)"


# ---------------------------------------------------------------------------
# 场景级(W2b, 计划 26-11-10-0318 §04 W2 第 4 项): 六场景全链端到端 —— 与接线级(W2a)
# 分工: 接线级钉分层语义(三层判据分派/tick 契约/复验现判/节流计数), 场景级钉全链行为:
# 观测通道 -> 状态机 -> 进窗 -> 逐成员改写 -> journal 落账 -> obs 持久化的完整驱动序列,
# 一律经 _run 主循环驱动(不单调函数), 时序断言用注入时钟 + 落账时刻捕获证明, 无真实等待。
# 世界桩 _stub_world 单桩四通道(roster/lmap/up/names), 翻面点显式(参考 _flip_to_face_at_
# reverify 的做法); 全部替身, 不起真进程/不回连真端口
# ---------------------------------------------------------------------------


def _scenario_job(tmp_path: Path, data_dir: str, tags) -> list:
    """多成员待收尾 job 造法(场景级用: 逐成员记账断言需要 >= 2 个成员), 返回 v1 hash 清单
    (_member_fixture/_write_job 的多成员封装, 造法与 _pending_job 同源)"""
    tmp_path.joinpath("src").mkdir(exist_ok=True)
    tmp_path.joinpath("dst").mkdir(exist_ok=True)
    hashes = [_member_fixture(tmp_path / "BT_backup", tag, str(tmp_path / "src")) for tag in tags]
    _write_job(tmp_path, data_dir, "job-1", hashes, src=str(tmp_path / "src"), dst=str(tmp_path / "dst"))
    return hashes


def _stub_world(monkeypatch, st):
    """场景级世界桩(W2b): 单一 st dict 驱动四条替身面 —— roster(全机 qB 身份名册, O2)/
    lmap(全机 LISTENING 映射, O3)/up(端口可达性, 证二)/names(全机映像名册, L2 证一消费)。
    st["phases"][st["phase"]] 供数, 桩每拍读现值(与 _stub_obs/_stub_qb 联动风格同款);
    st["next"] + st["flip_at"] = 翻面点: 第 flip_at 次 _listening_map 调用起 phase 推进到
    next —— 翻面点即「世界变化时刻」, 测试显式。翻面钉在 _listening_map 调用序数上而非
    _qb_processes: 每 poll 恰调用一次且是每拍首个读取(_observe_poll 数据流序), 翻面落在
    拍边界, 同一拍的三路读取(lmap/refused/roster)看到同一世界(区别于 _flip_to_face_at_
    reverify 的「窗内复验现读翻面」形态 —— 那是世界变化刻意落在拍内两读之间, 复验现判的
    被测面); 窗内复验不调 _listening_map, 故其调用数 = poll 拍数。静态世界不设 next。
    phase 缺省键: roster={}/lmap=None/up=False/names=("explorer.exe",)。"""
    st.setdefault("calls", 0)
    st.setdefault("phase", "p0")

    def _cur():
        return st["phases"][st["phase"]]

    def _connect(addr, timeout=None):
        if _cur().get("up"):
            return mock.MagicMock()
        raise OSError(10061, "refused")

    def _lmap(*a, **k):
        st["calls"] += 1
        if st.get("next") and st["calls"] >= st.get("flip_at", 2):
            st["phase"] = st["next"]
            st["next"] = None
        return _cur().get("lmap")

    monkeypatch.setattr(rd.socket, "create_connection", _connect)
    monkeypatch.setattr(rd, "_qb_processes", lambda *a, **k: _cur().get("roster", {}))
    monkeypatch.setattr(rd, "_listening_map", _lmap)
    monkeypatch.setattr(rd, "_qb_process_names", lambda: _cur().get("names", ("explorer.exe", )))


def _capture_record_ts(monkeypatch, log):
    """改写落账时刻捕获(场景级时序测量, 时刻全部来自注入时钟 —— 无真实等待的证明面):
    包装 rj.record_rewrites, 只记成员记账调用(非空 records)的 ts; 相位补翻(空 records)
    不计。log 由测试持有。"""
    orig = rj.record_rewrites

    def _cap(*a, **k):
        records = a[2] if len(a) > 2 else k.get("records")
        if records:
            log.append(k.get("ts"))
        return orig(*a, **k)

    monkeypatch.setattr(rj, "record_rewrites", _cap)


def _spy_obs_tick(monkeypatch, log):
    """观测 tick 间谍(场景级时序测量): 包装 _Observation.tick 透传原行为, 记录每拍
    (now, roster 键升序或 None)—— 用于钉「面孔首见时刻/通道恢复时刻/owner 建档拍」。
    log 由测试持有。"""
    orig = rd._Observation.tick

    def _spy(self, roster, owner_cand, listen_map, now):
        log.append((now, sorted(roster) if roster is not None else None))
        return orig(self, roster, owner_cand, listen_map, now)

    monkeypatch.setattr(rd._Observation, "tick", _spy)


def test_scenario_x_owner_death_gap_rewrites_immediately(tmp_path, monkeypatch):
    """场景 X(计划 26-11-10-0318 §03.3 callout, 拍板 D2 安全性根基): 目标重启死亡间隙
    立即落盘 —— owner 死、新身完全未起, L1 立即进窗完成多成员改写收口。驱动序列: poll1
    目标在跑(观测通道经真实 _observe_owner -> tick 建档 owner 并落盘 obs)-> poll2 目标
    死亡(名册健康零观测 + 端口拒连, 新身未起)=> 同拍 L1 verdict True 立即进窗, 窗内
    复验现读仍零观测照过 -> 两成员逐个改写落账 -> settled -> idle。
    断言: 改写落盘(fastresume 双键)+ journal 逐成员记账 + 相位翻 rewritten; 无 30s 等待
    (stable=1000 仍完成, 落账时刻早于「死亡发现拍 + NEW_FACE_SETTLE」—— 那是 L2 等价
    路径的最早开窗点, 细步注入时钟证明, 界对成员数与拍内 clock 调用数不敏感)。"""
    data_dir = str(tmp_path / "data")
    h1, h2 = _scenario_job(tmp_path, data_dir, (b"m-1", b"m-2"))
    st = {
        "phases":
            {
                "alive":
                    {
                        "roster": {
                            100: _ident(100.0)
                        },
                        "lmap": {
                            100: frozenset({PORT})
                        },
                        "up": True,
                        "names": ("qbittorrent.exe", )
                    },
                "dead": {
                    "roster": {},
                    "lmap": {},
                    "up": False,
                    "names": ("explorer.exe", )
                },
            },
        "phase": "alive",
        "next": "dead",
        "flip_at": 2,  # 翻面点: poll2 的名册观测起世界进入「owner 死 + 新身未起」
    }
    _stub_world(monkeypatch, st)
    rec_ts = []
    _capture_record_ts(monkeypatch, rec_ts)
    tick_log = []
    _spy_obs_tick(monkeypatch, tick_log)
    # 细步时钟(step=1): 时序界对成员数与拍内 clock 调用数不敏感(每成员 2 次拍内调用也只
    # 吃掉个位秒), 界 30 的语义不变 —— 早于 L2 等价路径的「死亡 + NEW_FACE_SETTLE」最早开窗点
    assert _run(data_dir, stable=1000.0, max_wait=200.0, clock=_clock_gen(step=1.0)) == "idle"
    rw = rj.read_rewrites(data_dir, "job-1")
    assert rw[h1]["status"] == "rewritten" and rw[h2]["status"] == "rewritten", "两成员都改写落账"
    assert "qBt-savePath" in rw[h1]["keys"] and "qBt-savePath" in rw[h2]["keys"], "journal 逐成员双键明细在账"
    assert rj.read_journal(data_dir, "job-1")["phase"] == rj.PHASE_REWRITTEN
    for h, tag in zip((h1, h2), ("m-1", "m-2")):
        d = frmod.load_fastresume(_fr_path(tmp_path, h))
        assert d[b"qBt-savePath"] == (str(tmp_path / "dst").replace("\\", "/") + "/" + tag).encode("utf-8")
    owner_ts = tick_log[0][0]  # owner 建档拍 = 首拍(真实通道建档, tick 与建档同刻)
    st_obs = rj.read_obs(data_dir, rj.instance_key(HOST, PORT))
    assert st_obs["owner"]["ts"] == owner_ts and st_obs["owner"]["pid"] == 100, "建档 ts 与首见拍一致, 死证记录原样"
    assert tick_log[1][1] == [], "死亡拍名册零观测(新身完全未起 —— 场景 X 的世界前提)"
    assert rec_ts, "改写已落账"
    death_poll = tick_log[1][0]  # 死亡发现拍 = poll2(翻面后首拍; L2 口径的 down_since 也从这拍起算)
    assert max(rec_ts) - death_poll < rd.NEW_FACE_SETTLE, \
        "无 30s 等待: 落账早于「死亡发现拍 + NEW_FACE_SETTLE」—— 那是 L2 等价路径的最早开窗点(注入时钟证明)"


def test_scenario_y_daily_restart_settle_absorb_then_rewrite(tmp_path, monkeypatch):
    """场景 Y(计划 26-11-10-0318 §03.2 行三, P7 形态, §07 R3 有界赌注定价 ~33s): 日常
    实例重启 settle 吸收 —— 目标死(owner 记录在 obs)+ 日常库重启新面孔(pid=200, ct=600
    >= owner.ts, 不绑我们端口)=> 未决挡窗 -> NEW_FACE_SETTLE 30s 指纹稳定后吸收落盘 ->
    窗开完成改写。驱动序列: 静态世界(无翻面)—— 每拍观测同一名册, 面孔首拍进未决, 满界
    拍 settle 吸收(持久面落盘), 同拍 L1 verdict True 进窗改写收口。
    断言: 吸收前零改写(落账时刻 >= absorbed ts)/吸收后改写落盘/首见到吸收 >= 30s 且
    < 40s(满界下一拍, 不拖)/obs absorbed 条目持久化/owner 死证记录原样。"""
    data_dir = str(tmp_path / "data")
    h1 = _pending_job(tmp_path, data_dir)
    _seed_obs(data_dir, {"pid": 100, "ct": 100.0, "ts": 500.0})
    _stub_world(
        monkeypatch,
        {
            "phases":
                {
                    "p0":
                        {
                            "roster": {
                                200: _ident(600.0)
                            },
                            "lmap": {
                                200: frozenset({8081})
                            },
                            "up": False,
                            "names": ("qbittorrent.exe", )  # 日常库在跑: L2 全机口径同样挡窗
                        }
                }
        }
    )
    rec_ts = []
    _capture_record_ts(monkeypatch, rec_ts)
    tick_log = []
    _spy_obs_tick(monkeypatch, tick_log)
    assert _run(data_dir, stable=1000.0, max_wait=200.0) == "idle"
    assert rj.read_rewrites(data_dir, "job-1")[h1]["status"] == "rewritten", "吸收后窗开改写收口"
    first_seen = tick_log[0][0]
    st_obs = rj.read_obs(data_dir, rj.instance_key(HOST, PORT))
    assert st_obs["owner"] == {"pid": 100, "ct": 100.0, "ts": 500.0}, "owner 死证记录原样"
    assert len(st_obs["absorbed"]) == 1 and st_obs["absorbed"][0]["pid"] == 200 \
        and st_obs["absorbed"][0]["ct"] == 600.0, "absorbed 条目持久化(日常库新面孔)"
    absorbed_ts = st_obs["absorbed"][0]["ts"]
    # settle 界下沿钉绝对字面量 30.0(计划 §07 R3 定价): NEW_FACE_SETTLE 被调小(有界赌注
    # 收窄)时此处必须红; 界上沿引常量 —— 调大(更保守)不红, 由常量断言容忍
    assert absorbed_ts - first_seen >= 30.0, "settle 界(计划定价 30s)尊重: 提前吸收即赌注破界"
    assert absorbed_ts - first_seen < rd.NEW_FACE_SETTLE + 10.0, "满界下一拍即吸收(不拖)"
    assert rec_ts and min(rec_ts) >= absorbed_ts, "吸收前零改写(未决挡窗)"
    assert max(rec_ts) - first_seen < rd.NEW_FACE_SETTLE + 20.0, "全程 ~33s 时序(计划定价形态)"
    d = frmod.load_fastresume(_fr_path(tmp_path, h1))
    assert d[b"qBt-savePath"] == (str(tmp_path / "dst").replace("\\", "/") + "/m-1").encode("utf-8")


def test_scenario_pid_reuse_non_qb_dead_evidence_form1(tmp_path, monkeypatch):
    """PID 复用方向一(计划 26-11-10-0318 §03.3 死证形态一): 死 owner 的 pid 被非 qB 程序
    复用 —— qB 身份名册(只收映像含 qbittorrent 的进程)里该 pid 消失(名册无此 pid), 原实例
    死证形态一成立 => 照常进窗。驱动序列: 前世归档 owner(pid=100)-> 本世名册只有日常库实例
    pid=300(ct=50 早于 owner 实例 => 行一零赌注吸收, 不挡窗); pid 100 现属 chrome.exe
    (qB 名册不可见, 全机映像名册只见 chrome + 日常库)。
    断言: 首拍即进窗(死证 + 零赌注吸收同拍成立, 落账时刻 < NEW_FACE_SETTLE, stable=1000
    无稳定期); 改写落盘; obs absorbed 收录日常库、owner 死证记录原样(复用者不触碰);
    全机名册见 qB(L2 等价路径被阻断)—— 窗是 L1 开的, 实例级证据相对全机口径的增量。"""
    data_dir = str(tmp_path / "data")
    h1 = _pending_job(tmp_path, data_dir)
    _seed_obs(data_dir, {"pid": 100, "ct": 100.0, "ts": 500.0})
    _stub_world(
        monkeypatch,
        {
            "phases":
                {
                    "p0":
                        {
                            "roster": {
                                300: _ident(50.0)
                            },
                            "lmap": {},
                            "up": False,
                            "names": ("chrome.exe", "qbittorrent.exe")  # pid 100 现属 chrome; 日常库在跑
                        }
                }
        }
    )
    rec_ts = []
    _capture_record_ts(monkeypatch, rec_ts)
    tick_log = []
    _spy_obs_tick(monkeypatch, tick_log)
    assert _run(data_dir, stable=1000.0, max_wait=200.0) == "idle"
    assert rj.read_rewrites(data_dir, "job-1")[h1]["status"] == "rewritten", "死证形态一照常进窗改写"
    first_seen = tick_log[0][0]
    assert rec_ts and min(rec_ts) - first_seen < rd.NEW_FACE_SETTLE, "首拍即进窗(无稳定期)"
    st_obs = rj.read_obs(data_dir, rj.instance_key(HOST, PORT))
    assert st_obs["owner"] == {"pid": 100, "ct": 100.0, "ts": 500.0}, "复用者不触碰 owner 死证记录"
    assert [e["pid"] for e in st_obs["absorbed"]] == [300], "日常库实例零赌注吸收落盘(不挡窗)"
    d = frmod.load_fastresume(_fr_path(tmp_path, h1))
    assert d[b"qBt-savePath"] == (str(tmp_path / "dst").replace("\\", "/") + "/m-1").encode("utf-8")


def test_scenario_pid_reuse_qb_instance_blocks_until_disposed(tmp_path, monkeypatch):
    """PID 复用方向二(计划 26-11-10-0318 §03.3 死证形态二 + §03.2 身份不继承): 死 owner
    的 pid 被另一 qB 实例复用(名册有 pid=100 但 ct 不等)=> 判原实例已死(形态二), 复用者
    按全新面孔分类(PID 复用不继承 owner 身份, 也不继承 absorbed)=> 未决挡窗直至状态机
    处置(settle 吸收)后窗开改写。驱动序列: 前世归档 owner(pid=100, ct=100)-> 本世名册
    {100: ct=999}(复用者不绑我们端口)-> 首拍起未决挡窗(死证成立但未决一票挡)-> 30s
    settle 吸收落盘 -> 同拍进窗, 复验分类读见 absorbed 命中放行 -> 改写收口。
    断言: 吸收前零改写; absorbed 条目按复用者新身份落盘(pid=100, ct=999); owner 死证
    记录原样(未被复用者覆盖 —— 未绑我们端口不升格 owner); 吸收后改写落盘。"""
    data_dir = str(tmp_path / "data")
    h1 = _pending_job(tmp_path, data_dir)
    _seed_obs(data_dir, {"pid": 100, "ct": 100.0, "ts": 500.0})
    _stub_world(
        monkeypatch,
        {
            "phases":
                {
                    "p0":
                        {
                            "roster": {
                                100: _ident(999.0)
                            },  # 复用者: 同 pid 异 ct 的另一 qB 实例
                            "lmap": {
                                100: frozenset({8081})
                            },
                            "up": False,
                            "names": ("qbittorrent.exe", )
                        }
                }
        }
    )
    rec_ts = []
    _capture_record_ts(monkeypatch, rec_ts)
    tick_log = []
    _spy_obs_tick(monkeypatch, tick_log)
    assert _run(data_dir, stable=1000.0, max_wait=200.0) == "idle"
    assert rj.read_rewrites(data_dir, "job-1")[h1]["status"] == "rewritten", "复用者被处置后窗开改写"
    first_seen = tick_log[0][0]
    st_obs = rj.read_obs(data_dir, rj.instance_key(HOST, PORT))
    assert st_obs["owner"] == {"pid": 100, "ct": 100.0, "ts": 500.0}, "owner 死证记录不被复用者覆盖"
    assert len(st_obs["absorbed"]) == 1 and st_obs["absorbed"][0]["pid"] == 100 \
        and st_obs["absorbed"][0]["ct"] == 999.0, "复用者按新身份吸收(不继承 owner 旧 ct)"
    absorbed_ts = st_obs["absorbed"][0]["ts"]
    # settle 界下沿钉绝对字面量 30.0(计划 §07 R3 定价): NEW_FACE_SETTLE 被调小(有界赌注
    # 收窄)时此处必须红; 界上沿引常量 —— 调大(更保守)不红, 由常量断言容忍
    assert absorbed_ts - first_seen >= 30.0, "复用者走全新面孔 settle 管道(计划定价 30s)"
    assert absorbed_ts - first_seen < rd.NEW_FACE_SETTLE + 10.0, "满界下一拍即吸收"
    assert rec_ts and min(rec_ts) >= absorbed_ts, "复验/分类读挡直至该面被状态机处置(吸收前零改写)"
    d = frmod.load_fastresume(_fr_path(tmp_path, h1))
    assert d[b"qBt-savePath"] == (str(tmp_path / "dst").replace("\\", "/") + "/m-1").encode("utf-8")


def test_scenario_pending_face_at_window_criterion_blocks(tmp_path, monkeypatch):
    """未决挡窗(计划 26-11-10-0318 §03.2 行四; 与场景 Y 呼应、驱动源不同: 目标死亡同拍
    现身的全新面, ct >= ts_last): 窗开判据现场冒未决新面 => 不进窗, settle 后进窗。
    驱动序列: poll1 目标在跑(观测通道建档 owner)-> poll2 目标死亡且全新 qB 面(pid=300,
    ct=600)同拍现身(不绑我们端口)—— 判据现场未决成员在册 => 不进窗(L1 未决挡 + L2
    全机名册见 qB 双向挡), 零改写; settle 30s 吸收 => 窗开改写收口。
    断言: 吸收前零改写(现场冒面即挡 —— 窗从未开过, 区别于窗开后复验挡的接线级形态);
    吸收后改写; obs absorbed 持久化; owner 建档 ts 钉在首见拍(真实通道建档)。"""
    data_dir = str(tmp_path / "data")
    h1 = _pending_job(tmp_path, data_dir)
    st = {
        "phases":
            {
                "alive":
                    {
                        "roster": {
                            100: _ident(100.0)
                        },
                        "lmap": {
                            100: frozenset({PORT})
                        },
                        "up": True,
                        "names": ("qbittorrent.exe", )
                    },
                "deadface":
                    {
                        "roster": {
                            300: _ident(600.0)
                        },
                        "lmap": {
                            300: frozenset({8081})
                        },
                        "up": False,
                        "names": ("qbittorrent.exe", )  # 新面孔在跑: L2 全机口径同样挡窗
                    },
            },
        "phase": "alive",
        "next": "deadface",
        "flip_at": 2,  # 翻面点: poll2 起「目标死亡 + 全新面同拍现身」(判据现场形态)
    }
    _stub_world(monkeypatch, st)
    rec_ts = []
    _capture_record_ts(monkeypatch, rec_ts)
    tick_log = []
    _spy_obs_tick(monkeypatch, tick_log)
    assert _run(data_dir, stable=1000.0, max_wait=200.0) == "idle"
    assert rj.read_rewrites(data_dir, "job-1")[h1]["status"] == "rewritten", "settle 后窗开改写收口"
    st_obs = rj.read_obs(data_dir, rj.instance_key(HOST, PORT))
    assert st_obs["owner"]["ts"] == tick_log[0][0] and st_obs["owner"]["pid"] == 100, \
        "owner 建档 ts 钉在首见拍(真实通道建档)"
    assert len(st_obs["absorbed"]) == 1 and st_obs["absorbed"][0]["pid"] == 300 \
        and st_obs["absorbed"][0]["ct"] == 600.0, "全新面被正规吸收落盘"
    face_first = tick_log[1][0]  # 面孔首见拍 = poll2(与死亡同拍现身)
    absorbed_ts = st_obs["absorbed"][0]["ts"]
    # settle 界下沿钉绝对字面量 30.0(计划 §07 R3 定价): NEW_FACE_SETTLE 被调小(有界赌注
    # 收窄)时此处必须红; 界上沿引常量 —— 调大(更保守)不红, 由常量断言容忍
    assert absorbed_ts - face_first >= 30.0, "未决期 settle 界(计划定价 30s)尊重"
    assert absorbed_ts - face_first < rd.NEW_FACE_SETTLE + 10.0, "满界下一拍即吸收"
    assert rec_ts and min(rec_ts) >= absorbed_ts, "吸收前零改写(判据现场未决在册, 窗从未开过)"
    d = frmod.load_fastresume(_fr_path(tmp_path, h1))
    assert d[b"qBt-savePath"] == (str(tmp_path / "dst").replace("\\", "/") + "/m-1").encode("utf-8")


def test_scenario_obs_reload_across_restart_rewrites_from_dead_evidence(tmp_path, monkeypatch):
    """obs 重启重载端到端(计划 26-11-10-0318 §03.3/§03.4「停机期间目标死亡」全链):
    第一世 daemon 经真实观测通道建档 owner(目标在跑)-> daemon 停机(timeout 收束, obs
    归档留存)-> 停机期间目标死亡 -> 第二世 daemon from_payload 恢复死证 -> 直接 L1 进窗
    改写(无 30s 等待)。与接线级 test_run_restarts_restore_owner_evidence_from_obs_file
    分工: 本测第一世 owner 建档走全链通道(桩四通道 -> _observe_owner -> tick -> write_obs),
    非预播种; 第一世零改写也入断言。
    断言: 第一世建档成功且零改写; 第二世首拍即改写(落账时刻 - 第二世首拍 < NEW_FACE_SETTLE,
    stable=1000); obs owner 记录跨重启逐字段一致(死证不被第二世触碰)。"""
    data_dir = str(tmp_path / "data")
    h1 = _pending_job(tmp_path, data_dir)
    # 第一世: 目标在跑, 真实通道建档, owner 活着不进窗, timeout 收束
    _stub_world(
        monkeypatch, {
            "phases":
                {
                    "p0":
                        {
                            "roster": {
                                100: _ident(100.0)
                            },
                            "lmap": {
                                100: frozenset({PORT})
                            },
                            "up": True,
                            "names": ("qbittorrent.exe", )
                        }
                }
        }
    )
    assert _run(data_dir, stable=1000.0, max_wait=20.0) == "timeout"
    life1_obs = rj.read_obs(data_dir, rj.instance_key(HOST, PORT))
    assert life1_obs["owner"]["pid"] == 100 and life1_obs["owner"]["ct"] == 100.0, "第一世真实通道建档"
    assert rj.read_rewrites(data_dir, "job-1") == {}, "owner 在位: 第一世零改写"
    # 停机期间目标死亡(名册零观测 + 端口拒连)-> 第二世 from_payload 恢复死证
    _stub_world(monkeypatch, {"phases": {"p0": {"roster": {}, "lmap": {}, "up": False, "names": ("explorer.exe", )}}})
    rec_ts = []
    _capture_record_ts(monkeypatch, rec_ts)
    tick_log = []
    _spy_obs_tick(monkeypatch, tick_log)
    assert _run(data_dir, stable=1000.0, max_wait=200.0) == "idle"
    assert rj.read_rewrites(data_dir, "job-1")[h1]["status"] == "rewritten", "恢复死证驱动 L1 立即进窗改写"
    assert rj.read_obs(data_dir, rj.instance_key(HOST, PORT))["owner"] == life1_obs["owner"], \
        "obs owner 记录跨重启逐字段一致(死证不被触碰)"
    assert rec_ts and min(rec_ts) - tick_log[0][0] < rd.NEW_FACE_SETTLE, "第二世首拍即进窗(无 30s 等待)"


def test_scenario_channel_outage_falls_to_l2_then_l1_on_recovery(tmp_path, monkeypatch, caplog):
    """通道失败退 L2(计划 26-11-10-0318 §03.1 通道纪律 + §07 R5 等价面, 黄金法则 2 保守
    退化): L1 观测通道(名册枚举)持续故障 => 全程退 L2 现状判据(30s 稳定期), warning
    节流留痕, 行为与接线前等价; 恢复后回到 L1。同一 data_dir 连续两世:
    第一世名册通道恒 None —— 30s 稳定期内零改写(max_wait=25 < stable=30 截停; 通道故障若
    被冒充成健康零观测(None 冒充 {})或稳定期被丢, 改写会在首拍出现; 分派层 None=>True
    的冒充由接线级复验闸专测兜, 本测断言面 = 端到端往返)+ 节流 warning 60s 一条 + obs
    死证种子原样(roster None => tick 整拍不动); 第二世通道恢复(健康零观测)=> 回 L1,
    死证立即进窗改写(stable=1000 无稳定期), 全程零「退 L2」留痕。"""
    data_dir = str(tmp_path / "data")
    h1 = _pending_job(tmp_path, data_dir)
    _seed_obs(data_dir, {"pid": 4242, "ct": 100.0, "ts": 500.0})
    seeded = rj.read_obs(data_dir, rj.instance_key(HOST, PORT))
    _stub_world(
        monkeypatch,
        {
            "phases": {
                "p0": {
                    "roster": None,  # 名册通道恒故障(观测不可用)
                    "lmap": None,
                    "up": False,
                    "names": ("explorer.exe", )
                }
            }
        }
    )
    with caplog.at_level(logging.WARNING, logger=LOG_RD):
        assert _run(data_dir, stable=30.0, max_wait=25.0) == "timeout", "通道故障: 30s 稳定期内不进窗(L2 现状)"
        n = len([r for r in caplog.records if "退 L2 全机口径" in r.message])
        assert n == 1, f"节流留痕 60s 一条, 实得 {n}"
    assert rj.read_rewrites(data_dir, "job-1") == {}, "零改写(通道故障不冒充通过, 等价面)"
    assert rj.read_obs(data_dir, rj.instance_key(HOST, PORT)) == seeded, "roster None => tick 整拍不动, obs 种子原样"
    caplog.clear()  # 第一世留痕不漏进第二世断言
    # 第二世: 通道恢复(健康零观测)=> 回 L1
    _stub_world(monkeypatch, {"phases": {"p0": {"roster": {}, "lmap": {}, "up": False, "names": ("explorer.exe", )}}})
    rec_ts = []
    _capture_record_ts(monkeypatch, rec_ts)
    tick_log = []
    _spy_obs_tick(monkeypatch, tick_log)
    with caplog.at_level(logging.WARNING, logger=LOG_RD):
        assert _run(data_dir, stable=1000.0, max_wait=200.0) == "idle"
        assert not [r for r in caplog.records if "退 L2 全机口径" in r.message], "通道恢复零退 L2 留痕"
    assert rj.read_rewrites(data_dir, "job-1")[h1]["status"] == "rewritten", "恢复后回到 L1 立即改写"
    assert rec_ts and min(rec_ts) - tick_log[0][0] < rd.NEW_FACE_SETTLE, "恢复后无稳定期(L1 强证据)"
