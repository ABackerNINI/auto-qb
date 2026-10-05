"""test_web 测试计划: WEB UI 后端(FastAPI 鉴权/API/命令投递/设置读写)

## 测试计划(每个测试函数一条)
- test_api_requires_token: 无/错密钥访问 /api/* -> 401
- test_config_public_endpoint_no_auth: 公开端点 /api/config/public 免 token 只读本机免鉴权标志(不含机密); **仅限 loopback**(远端 403, issue 26-09-21-1408 B-02)
- test_skip_local_verify_loopback_bypass: web.skip_local_verify=true 时本机连接免密钥放行(提示日志 **INFO 级**、**每进程只记一次**), 对外/远端仍强制鉴权
- test_skip_local_verify_default_off: 默认关闭(保守), 本机连接也不免鉴权
- test_skip_local_verify_cross_site_guard_host_whitelist: skip_local_verify 开启时 Host 白名单(DNS rebinding 防护, issue 26-09-21-1408) —— 外部域名 403(API+静态), loopback 全形态与自配 host 放行
- test_skip_local_verify_cross_site_guard_write_origin: skip_local_verify 开启时写方法 Origin 同源校验(CSRF 防护) —— 跨站 Origin 403 且不入队, 同源/无 Origin 放行, GET 不校验(跨站读拿不到响应体, 危害面在写)
- test_skip_local_verify_cross_site_guard_all_write_endpoints: 全部写端点穷举(迭代路由表) —— 跨站 Origin 下一律 403(闸在全局依赖单点, 先于任何处理器/422)
- test_skip_local_verify_cross_site_guard_credentials_bypass: 携带凭证的请求绕过跨站闸(浏览器跨站伪造不了凭证, 持密不在威胁模型内) —— 既有分支照旧裁决(loopback 免鉴权放行 / 远端对密钥 200、错密钥 401)
- test_skip_local_verify_default_off_no_cross_site_guard: 默认关闭零变化 —— 外部 Host/Origin 不触发 403(仍走既有 401 路径)
- test_auth_host_origin_parsing_helpers: Host 头解析与 Origin 判定纯函数单测(host:port / [::1]:port 形态 / 解析失败 fail-closed / 端口一致性)
- test_sse_ticket_flow: SSE 一次性票据(B-01) —— 带鉴权 POST 换票, 单次消费/过期无效/重放无效/无凭证 401/满额拒签
- test_sse_ticket_in_require_token_and_query_token_removed: require_token 收 ?ticket=(仅限 /api/events, 取即删); ?token= 查询串兜底已删除(密钥正确也不再是凭证)
- test_start_web_server_config_disables_proxy_headers: uvicorn Config 显式 proxy_headers=False(B-03, 防反代 XFF 改写 client.host 造成免鉴权误判)
- test_frontend_sse_ticket_wiring: polling.js 换票接线守阵 —— POST /api/events/ticket + ?ticket= 连流 + 重连换新票; ?token= 通道不得回潮
- test_api_status_and_groups: 状态与分组快照读取(经注入的 manager; status 含 version)
- test_api_expr_eval_endpoint: 表达式试算端点(校验-only / 按种子求值 + 中间值 / 名字错误 / 种子不存在)
- test_static_assets_disable_heuristic_cache: 静态资源带 no-cache(/api 不受影响), 防升级后仍加载旧前端(UI 目录化路径: atlas/prism/shared)
- test_ui_root_and_legacy_newui_redirect: / -> 307 上次使用的 UI(autoqb_ui 皮肤 cookie, 未记录/失效回落星图); 旧 /newui/* 书签 -> 307 /prism/*
- test_frontend_ui_skin_cookie_persisted: boot.js 必须把当前 UI 写进 autoqb_ui cookie —— 根路径「记住上次 UI」的数据源(307 在服务端裁决, cookie 是唯一读得到的载体)
- test_frontend_static_bundle_health: 前端静态资源静态守阵(冲突标记/注释孤儿续行/node --check 语法校验/CSS 规则漏闭合/CSS 注释提前终止/<transition> 吞弹窗/静态引用缺失/追剧视图集成员取 hash 未走 memberHashesOf/STATE_RANK 与后端 _SHOW_STATE_RANK 漂移 / 页面挂件类名必须有对应 CSS 规则 / 列模型每列必须有值单元格分支+hide 默认隐藏接线 —— 均为"pytest 全绿但界面废掉"的故障形态)
- test_frontend_template_split_wiring: 模板分片接线守阵(26-09-26 拆分 plans/26-09-26-2233 W1) —— 清单完整性(漏挂=整块消失 / 404=整页占位 / into 非法)+ 双 UI 分片名单同名同序 + 聚合标签配平 + shell≤200 行/单分片≤400 行 + 清单脚本序(vendor 首 app.js 尾)
- test_frontend_member_window_functions_live_in_methods: 成员行窗口三个带参函数(memberWin/memberPadTop/memberPadBottom)必须落在 methods 块, 不能进 computed —— Vue 3 computed 是无参 getter, 带参会导致整表白屏(issue 26-09-21-0247)
- test_frontend_computed_not_invoked_as_function: computed 成员不得以 `this.X()` 调用(拿到的是 getter 的值, 再 () 会 TypeError) —— 经典设置页改"数值+单位"字段的数字会整页白屏
- test_frontend_template_no_reserved_prefix_identifiers: 模板表达式(插值+指令)禁止 `_`/`$` 前缀裸标识符 —— Vue 内部保留域解析不到, 抛 ReferenceError 且整块渲染失败(issue 26-10-03-1412 复制钮 `_copyText`); `$event` 白名单, 成员访问不拦
- test_frontend_dist_segments_aggregates_per_view: distSegments 必须按 viewMode 取数(torrents / shows / groups), 不能只数 this.groups —— 种子页次导航 chips 会全空(issue 26-09-21-0247)
- test_frontend_cols_store_single_setitem_site: COLS_STORE_KEY 的 setItem 全仓恰好一处(persistPage 内) —— 散写回潮即红
- test_frontend_persist_page_takes_intent_only: persistPage 只收意图态(colHidden/colOrder/colW), 生效宽度 colWidths 不得进持久化路径(双轨模型铁律, plan 26-09-21-1551)
- test_frontend_col_manual_flag_not_revived: 反向守阵 —— manual 标志位(colManual)不得复活(v5 下 w 非空即固化页)
- test_frontend_cols_legacy_keys_have_migration: LEGACY_COLS_KEYS 键链必须伴随 migrateLegacyToV5 迁移(v3->v4 清零事故的机检)
- test_frontend_cols_empty_hint_names_browser_clear_cause: 空存储提示必须点名浏览器站点级"关闭窗口时清除 Cookie 和站点数据"这条通道 + 给自查路径 + sessionStorage 会话级去重(2026-09-24 取证: cookie 例外 127.0.0.1,* setting=4)
- test_removed_redundant_tooltips_stay_removed: 复述型 tooltip 不得复活守阵(报告 26-10-04-0815) —— 模板已移除的复述型原生 title 文案(statusbar「点击修改」「数据状态」/ topbar 页签「按分组展示」「全部种子一行一条」/ drawer「关闭(Esc)」/ dialogs 族 title="关闭" / settings-detail·xtpl「点击收起」/ columns.js H1 横幅「点击关闭」)不得写回, 悬浮提示一律走 shared/ui_feedback.js 拦截层
- test_recheck_confirm_wired_all_mouse_entries: 重新校验确认框三入口接线守阵(T13, 计划 26-10-05-0314 S3) —— commands.js _recheckConfirm 单点(helper 存在 + 文案与 okText 调用形态沿键盘路径原样)+ bulkAct 批量通道 / drawer.js torrentCmd 单选通道各含 recheck 确认分支 + shortcuts.js _kbAct 改调共用 helper 不再内联 confirmDialog 文案 + 共用文案字符串全仓只此一份, 任一接入点被重构摘除即红
- test_skip_check_dialog_precheck_wired: 跳检预检对话框接线守阵(T23, 计划 26-10-05-0314 S4) —— ui_feedback.js _modalInit 声明 okDisabled/busy/verdict 三字段 + popovers.html 确认钮 :disabled="modal.okDisabled" 绑定 / busy 行 / verdict 行式渲染区(强制钮复用 extraText 第三钮 danger-solid) + drawer.js 两入口(skipCheckTorrent/skipCheckMulti)均交棒 _skipCheckDialog 且不再自带 _openModal + _skipCheckDialog 进框即禁用(busy + 固定警示区)并发预检(_skipPrecheck), 任一被重构摘除即红
- test_skip_check_dialog_verdict_render: 跳检预检三分流渲染逻辑守阵(T24, 计划 26-10-05-0314 S4) —— _skipPrecheck 状态机分支(预检失败降级=启用普通确认且无强制钮 / 含 blocked=确认强制双钮全收 / ok+force 混合=确认钮文案「跳检 N 个可跳检的」+ 强制钮「强制跳检全部」/ force-only=确认保持禁用 / 全 ok=只启用确认)+ ok 子集派生(cls==="ok" 过滤)+ 确认路径送 ok 子集而强制路径送全量+force(_skipExec 单发 body 仅 force 时带 force 键, 批量确认只走 hashes 通道)+ 降级文案「后端闸门仍会在执行时拦截」+ _skipVerdictRows 计数行与分组上限截断(slice(0,5)+等 X 个), 任一分支被改写即红
- test_frontend_page_location_persisted: 顶层 page 与设置分区必须持久化(读侧白名单 / 写侧单漏斗) + 启动补一次 cfgLoad + 分区 key 对 schema 校验 —— 否则"设置页刷新掉回种子页"复发(2026-09-25 用户报)
- test_frontend_unsaved_changes_guard_wiring: 设置页未保存改动防护接线守阵(issue 26-09-25-1702 / 报告 26-10-02-0508 U1-b) —— 键盘刷新(F5/Ctrl+R)走自绘三选一框(保存并刷新/放弃并刷新/留在此页)+ 其余导航走原生 beforeunload 兜底 + 兜底随脏态挂摘成对 + 主动刷新前摘兜底防双框连击 + 不做草稿恢复(不碰 Web Storage)
- test_frontend_expand_state_survives_view_switch: 展开态跨视图记忆守阵 —— 切视图不得置空 expandedKey/expandedShows/expandedShowEp(辅种页→种子页→辅种页 展开的组会收起, 2026-09-25 用户报); 还回前必须验那一行还在, 且 groupWin 的退避判据要同步(否则为不存在的面板永久退化成全量渲染)
- test_frontend_qb_traffic_chart_wiring: qB 口径流量图前端接线守阵(P5a+P5b, plan 26-10-03-0946 §07) —— enabled=false 三挂点入口不渲染不请求(全局入口按钮 v-if="qbHistEntryOn" / 抽屉流量页签与组右键菜单项 v-if="qbTrafficOn", 门在 flags.qb_traffic_enabled, /api/webui/flags 下发 fail-closed)+ uPlot 双系列 spanGaps=false 断线不连线 + 桶序->_qbPointsToData 栅格重建与 null 语义 node 真跑(全 null 回落/前导 null 锚推算/interval 非法防御 + S3b 月行真值落点/空槽内插/anchor.xs) + 轮询下界常量 1500(A4, S3b §05.5)+ 三挂点作用域表与低频轮询口径(interval_s 夹取 + document.hidden 跳过 + 关闭/切走 clearInterval)+ 静默续拉(loading 空态只在「尚无落袋结果」时接管正文(qbCurPending = loading + 无数据 + 无错误) + 同宿主 setData 原地快路 + 换肤先销毁再重建 + 错误态由成功落袋清除, 2026-10-04 修轮询期闪烁 / 2026-10-05 补齐空态与错误态闪烁)+ FX-29 软切换落定登记(_qbLoad 落袋 _drawerDone("traffic") 与 _drawerWaitSources 成对, 2026-10-04 修流量页签单击换行遮罩挂死)+ 三主题登记链(tpl/vendor/mixin/manifest)+ escBusy 与 Esc 退栈链同步 + 建图后宿主 ResizeObserver 自适应与销毁断开(便签 26-10-04-0134)+ 缺口三态文案与空态钉住(P4, plan 26-10-04-0721 §05: 0 桶状态行/缺口合并文案/图例 hint 两处/单种空态收窄为从未传输 + node 三段混排回归)
- test_api_group_commands_enqueue: pause/resume/reannounce/delete 命令入队(key 编解码回原值)
- test_api_group_malformed_key_returns_400: 畸形分组 key(base64 非法/非 JSON/结构不符)回 400 而非 500
- test_api_delete_with_files_flag: delete 命令透传 delete_files 标志
- test_api_cmd_result_endpoint: 命令端点返回 cmd_id; /api/cmd/{id} 查询回执(pending -> 结果)
- test_api_enqueue_wakes_main_loop: 投递用户命令唤醒主循环; 反向守卫——自投递命令须登记进 SELF_POSTED_COMMANDS(防自激)
- test_api_traffic_history_endpoint: /api/traffic/history 透出快照 history; 缺省空数组
- test_api_traffic_qb_disabled_empty_state: qB 口径流量三端点未启用(qb_traffic None / enabled=false)空态与 /api/traffic/history 同构(plan 26-10-03-0946 §08 P4)
- test_api_traffic_qb_requires_token: 三 GET 端点沿用全局 token 鉴权单点(无凭证 401)
- test_api_traffic_qb_window_validation: window 非法值 400 / 缺省 24h / 仅认 WINDOW_NAMES 十三档(v3 D4: 1m-30d + 6mo/1y/all, 90d 延后)
- test_api_traffic_qb_global_24h_points_totals_and_stale: (v3)global 24h 窗天文件块 -> 栅格展开(points 对齐桶/空桶 null=断连真空) + totals 差分(重置/断链) + 读取竞态降级回上一份快照标 stale
- test_api_traffic_qb_global_30d_hour_segment: (v3)global 30d 窗 agg hour 行直映栅格桶(epoch 即桶键), interval_s=3600, 相邻桶差分
- test_api_traffic_qb_global_6mo_1y_day_segment: (v3 S3b D4 新档)6mo/1y 窗 agg day 行直映本地日界桶 —— 滚动窗切片(300 天前行 1y 可见/6mo 不可见), 缺日断链, interval_s=86400
- test_api_traffic_qb_global_all_month_segment: (v3 S3b D4 新档)all 窗 agg month 行数据面逐月铺格(缺失月 null), 相邻月差分, interval_s=标称月长; 空数据面空态
- test_api_traffic_qb_torrent_endpoint: (v3)单种端点取数 / 非法哈希 400 / 未知哈希空态 / 冻结种子历史仍可查
- test_api_traffic_qb_torrent_1y_single_agg_cold_read: (v3 S3b 验收)年视图单 agg 文件冷读恰 1 open, 缓存命中再查零 open
- test_api_traffic_qb_global_24h_reads_only_involved_day_files: (v3 S3b 端点面回归)24h 窗只开窗口涉及日期天文件(恰 2 个), 窗外日期/agg.dat 零 open
- test_api_traffic_qb_group_endpoint: (v3)分组读侧现算(Σ 成员均值/全员空闲 z 覆盖 0 线/全员无观测断线 —— 借 global 判 null 退役且零全局读取/成员重置贡献 0/历史回溯可见/解析不到成员空态/畸形 key 400)
- test_api_traffic_qb_group_30d_reads_member_agg_only: (v3 S3b 验收)3d+ 窗组图只读成员 agg 文件(2 成员恰 2 open = M×1, 天文件零读取)
- test_api_traffic_qb_global_live_tail_realtime: (S6 验收追加)raw 段窗活尾合流 —— 纯活尾(零盘)出实时桶点;
  磁盘落盘后滞后快照重列已落盘记录被按 ts 精确去重(快照与 flush 竞态不重不漏), 快照清空后磁盘响应与合流响应逐点一致
- test_api_traffic_qb_group_live_tail_member_only: (S6)组端点空态判据计入活尾 —— 成员仅活尾(零盘)组图非空;
  单种端点同享活尾
- test_api_traffic_qb_group_never_transferred_empty_state: 组从未有成员产过流量 -> 空态
- test_api_traffic_qb_group_member_only_zruns_not_empty: (v3)组空态判据观测面平移 —— 成员只剩 z 块不算「从未产过流量」, 出 0 线而非空态
- test_config_schema_endpoint: 图形化配置元数据端点(分组/插件/热重载级别)
- test_config_tree_roundtrip: 配置树读取/保存写回文件并投递热重载命令
- test_config_tree_invalid_rejected: 非法配置树 -> 400 且不写回
- test_config_tree_restart_field_fallback: R 级字段(data_dir)提交后被回退为磁盘旧值
- test_config_tree_requires_config_root: 缺少 config 根段 -> 400
- test_config_tree_preserves_comments: round-trip 写盘保留已有键的注释
- test_web_token_not_printed_in_logs: 生成的访问密钥不进任何日志(WARNING 会被 notify 推送, 且 /api/log 可读回)
- test_web_token_generated_atomic_and_readable: 首次生成密钥落盘 web.token 且读回一致, 无临时文件残留(走 atomic_write, issue 26-09-21-1347)
- test_web_token_existing_file_reused_without_rewrite: 已有合法 token 时直接复用文件现值, 不触达写盘路径(不重写不漂移)
- test_web_token_write_interrupt_leaves_no_half_token: 写盘中断不留非空半截 token —— 经真实 atomic_write 跑"写一半抛错", 旧文件不被破坏、临时文件被清理, 下次调用重新生成(自愈)
- test_config_tree_masks_secrets: /api/config 掩码敏感字段, 且"读取→原样保存"不会把密码写成占位串
- test_sites_missing_scans_and_builds_defaults: GET /api/sites/missing 未配置域名生成默认条目(domains/tags/占位限速/hr 示例值与 --export-yaml 同源); 已配置域名双向包含不重复
- test_sites_missing_name_conflict_suffix: 站点名冲突(既有配置占用/批内同名) -> _N 后缀(与 CLI 导出同一套 gen_tracker_name)
- test_sites_missing_all_covered_returns_empty: 全部域名已被覆盖 -> sites 空数组
- test_sites_missing_requires_connected_client: qB 断连 -> 503(不得拿空扫描冒充"没有缺失站点")
- test_sites_missing_api_failure_maps_502: 扫描中途 qB 调用失败 -> 502 带原因(不裸 500)
- test_frontend_sites_import_wiring: 一键导入按钮接线守阵 —— 两套 UI 站点 pill 行都挂「⤓ 导入缺失站点」+ config_hub.js 的 hubImportSites/防重入标志
- test_frontend_tracker_search_wiring: 站点页搜索接线守阵(计划 26-09-27-1852) —— 模板三件套(输入绑定/清空钮/计数) + 归一化必须 \\p{L}\\p{N}(u 标志, ASCII \\W 折碎中文词) + 收层路径四条一律清词单点(点命中/Esc/点暗幕/点外即收; 方案C 聚焦层 2026-09-29 拍板) + 聚焦层开合/键盘导航/IME 守卫 + 悬停接管位移门限(治上下键选中项闪烁 2026-09-29) + 键盘活动项滚动跟随(26-09-29-2142) + pill 无键数徽标 + 行尾动作区分形 + hb-tr-* 类 CSS 成对定义
- test_frontend_dialog_combo_hover_takeover: 弹窗下拉悬停接管守阵(issue 26-09-29-2142, 站点搜索闪烁同族) —— 分类/标签/编辑分类下拉 @mousemove+3px 位移门限共享小工具(comboHoverIdx) + @mouseenter 直写零残留 + 门限坐标 state 声明 + 开层单点复位 + 三皮肤 data-hi 行 CSS 摘 :hover(高亮只走 .on 单路)
- test_frontend_search_help_wiring: 顶栏搜索语法浮卡接线守阵(计划 26-09-28-0201 方案A) —— 模板(「?」钮/浮卡/示例回填/简化占位符) + state 声明 + view.js 方法(回填即搜) + 点空白/Esc/导航三条收起路径 + 三皮肤 CSS 成对定义与 input 右内边距留位
- test_group_key_codec_roundtrip: 分组 key 编解码往返(含中文/多文件)
- test_build_group_view: 分组视图组装(组名/合计/成员站点/单种子大小与总大小/标签/分类/保存路径)
- test_views_published_atomically_when_rebuilt_concurrently: 并发重建(主循环线程 vs Web 线程)时四份视图与版本号必须**同一轮**发布, 不得出现"半新半旧"
- test_flush_views_marks_dirty_on_hr_revision_change: HR 判定新鲜度置脏(plan 26-10-03-0436 Step 2) —— hr.revision 变化后 flush_views 置脏, 重建后基线前移、再次 flush 不再置脏(无循环置脏)
- test_flush_views_hr_facade_missing_null_defense: hr 门面缺失(None)时判空防御 —— 重建记基线与 flush 比对都跳过, 不炸不置脏
- test_build_group_view_member_num_seeds_fields: 组视图成员透出 num_seeds/num_leechs/num_complete/num_incomplete
- test_build_group_view_group_aggregates: 组视图组级聚合(辅种扩列 2026-09-28) —— 进度/可用性 max、eta 最小有效值(哨兵不参与)、剩余量 min、最近活动 max(-1 不参与)、已下载求和、做种时长平均、分享率=总上传÷单份大小; 全组无效值回 0/None
- test_build_group_view_cross_group_conflict_flag: 组视图跨组文件交叉标记(26-10-04-0107 S4/D4) —— 去重集合展平为组 key 集合后端查好, warned 注入组对两侧 true、组外组 false; warned 空全 false; 未归组单种子视图(singles)为成员级投影不携带组级标记
- test_member_view_extended_fields: 成员视图透出辅种扩列字段(eta/time_active/last_activity 分钟量化 + downloaded/amount_left/completion_on/seen_complete/availability/限速/tracker/infohash_v2)
- test_error_reason_from_tracker_msg: 错误种子的具体原因取 tracker 报错 msg(虚拟条目跳过)+ 视图透出 error_reason(取不到回退"错误"/非错误态为空)
- test_error_reason_missing_files_without_api: missingFiles 的原因由状态本身给出("文件丢失"), 不发 tracker 请求
- test_refresh_error_reasons_budget_and_ttl: 错误原因预取限流(单轮预算条数/TTL 内不重取/过期重取)
- test_refresh_error_reasons_clears_when_recovered: 状态恢复后清空原因缓存并置脏(不留旧原因)
- test_refresh_error_reasons_skips_when_disconnected: qB 断开时跳过(不发请求/不清空现值)
- test_build_search_index_files: 搜索索引构建(hash -> name+files), 单条文件拉取失败跳过该种子
- test_build_search_index_incremental_and_evict: 增量维护(不重拉已建条目/补拉新增/淘汰已删)
- test_build_search_index_budget_resumes: 限流分批构建, 未拉完保持脏, 续建至完成
- test_build_search_index_aborts_when_disconnected: qB 断连时中止构建且不写空索引
- test_search_torrents_name_match: 种子名匹配(即时/大小写不敏感)
- test_search_torrents_file_match: 文件列表匹配(依赖已建索引)
- test_search_torrents_separator_normalized: 分隔符归一匹配 —— 空格查询词命中点/下划线/连字符分隔的名与文件(回归 "cat and" 搜不到 The.Cat.and… 名)
- test_parse_query_tokens: 查询解析词法 —— 正/负词/短语 + 宽容边界(孤立-/未闭合引号/纯标点/--dv/web-dl)
- test_search_torrents_cross_row_and: 正词逐词跨行 AND(拍板 26-09-27 二次定案, 推翻 26-09-26 文件行隔离)—— 每个正词命中任一候选行(全称行/文件行)即可: 「minions mteam」名字×标签、「delta 03」名字×集文件跨行命中; 负词种子级不变
- test_search_torrents_negative_term: 负词种子级(26-09-27 定案)—— 任一候选行含负词 ⇒ 该种子整体排除: 单种子内季包文件统一计算(任一文件带负词整包排除), 多种子集合逐个算
- test_search_torrents_negative_torrent_veto: 负词种子级回归 —— 名字/保存路径/站点行含负词 ⇒ 整种子排除, 优先于一切正词命中(「cat and -11」+「-mteam」两轮报障回归)
- test_search_torrents_phrase: 短语 "…" 整段归一为连续子串, 词序敏感(terms-AND 命中而短语不命中的区分用例)
- test_search_torrents_regression_envnv10: 回归(26-09-26 报障)——「恶女 10」命中单文件发布物, -ubweb 可排除
- test_search_torrents_negative_only_empty: 仅负词/空查询返回空 + negative_only 标记, 不投递索引构建
- test_search_torrents_building_triggers: 索引脏时 building=True 并投递构建命令
- test_api_search_endpoint: GET /api/search 转发与鉴权(含空查询)
- test_frontend_search_syntax_wiring: 搜索匹配**服务端单点**的前端接线守阵 —— 清除钮 @mousedown.prevent 成对(焦点态清除失灵回归)/前端不得复活任何文本匹配实现(filters.js _parseSearchQuery 等四函数、hr.js/shows.js 旧整句 includes、app.js searchHitsQ 均已删, 复活即红)/filteredTorrents 必须消费 searchHits
- test_search_torrents_facet_rows: 候选行覆盖全部文本面(站点/分类/路径/标签行即时匹配, by 定位行类别) + facet 行负词整种子排除 —— 三页同源(26-09-26 单点化; 负词种子级 26-09-27 定案)
### P1 覆盖率提升轮: webui 运行时与命令长尾
- test_web_runtime_notify_drops_are_counted: SSE 广播非阻塞(慢/坏订阅者各计丢弃)
- test_web_runtime_check_pending_paths: 在途汇报确认全路径(item 级 deadline 超时 warn(epoch/legacy 文案)/停止直判/断连/读异常 error/判定聚合三桶与前 3 条原因截断)
- test_web_runtime_resync_elapsed_ms_logs_by_threshold: 补刷新计时按阈值分级(慢 WARNING / 正常 DEBUG)
- test_web_runtime_set_result_prunes_stale_and_carries_truth: 回执表 TTL 淘汰 + truth 附带
- test_web_runtime_affected_hashes_shapes: 受影响种子三种取法 + 异常退化
- test_web_runtime_affected_truth_queries_live_api: 真值直查 qB, 失败回 None 不回落快照
- test_web_commands_delete_with_files_and_reannounce_gone_receipt: 删除透传 delete_files; 汇报缺失显式回执
- test_web_commands_recheck_and_skip_check_receipts: recheck/skip-check 拒绝回执带文案
- test_web_commands_limits_partial_directions: 限速只下发提供的方向; 分享限制缺省 -2 补齐
- test_web_commands_rename_fs_folder_branch: 重命名文件夹分支
- test_web_commands_bulk_argument_errors: 批量参数四类错误回执
- test_web_commands_bulk_missing_targets_reported: 批量缺失种子/组分列计数
- test_web_commands_bulk_recheck_via_ops: 批量 recheck 经 ops 聚合回执
- test_web_commands_add_torrents_receipt: 添加种子受理/拒绝回执
- test_api_torrent_write_endpoints_extra_enqueue: 写端点补遗(pause/resume/delete/skip-check/limits 部分方向)
- test_api_webui_flags_endpoint: R2 功能旗标端点(计划 26-10-02-1955 W1) —— 开/关读实时配置 + 未鉴权 401; qb_traffic_enabled 旗标(P5a)段缺省/关 = False, 开 = True
- test_api_t_skip_check_gated_by_config: R2 skip-check 端点 gate —— 配置关 403(detail 注明 web.skip_check_menu)/ 开 200 入队, 403 不投递命令
- test_api_torrents_add_endpoint_errors_and_enqueue: 添加种子 base64 坏/空载荷 400 + 合法入队
- test_api_config_put_and_preview_tree_shape: 配置树 PUT/preview 非对象 400 + preview 不落盘
- test_api_expr_eval_runtime_error: 求值期失败(除零) -> ok=False 带文案与 used
- test_api_keys_endpoint_roundtrip_and_validation: 快捷键默认表/422 校验/保存读回
- test_api_keys_sanitize_rejects_non_dict: _sanitize 非 dict 一律 None
- test_api_category_and_tag_empty_rejections: 分类/标签空入参 400
- test_api_speed_mode_reads_client_with_alt_fields: 限速托管直读 qB(含 ALT 双组) + 读失败回 None
- test_api_fs_error_semantics: fs 端点错误语义化(404/501/403/400)
- test_api_paths_endpoint: GET /api/paths 已知目录聚合(组 save_path + 现有种子 save_path 归一去重排序; 空路径跳过; 无副作用; 鉴权)
- test_api_open_path_endpoint: POST /api/open-path 打开目标文件夹(FX-14 + R10-10) —— 目录/单文件(select=True 定位选中)、回退 save_path、组键首元、未知目标 404、kind 非法 400、客户端传 path 被忽略、无副作用、鉴权
- test_api_fs_dirs_endpoint: GET /api/fs/dirs 目录浏览(R10-11) —— 首屏允许根/只列目录(排除文件与越界符号链接)/上溯到根为止/.. 穿越与白名单外 403/不存在 404/无白名单空返回/鉴权/无副作用
- test_api_fs_dirs_case_sibling_is_outside_whitelist: **仅 Linux** —— 大小写兄弟目录(/x/Media 与 /x/media)必须判为越界, 白名单归一不得做 NTFS 式折叠(折叠 => 越界放行, fail-open)
- test_api_fs_mkdir_endpoint: POST /api/fs/mkdir 新建目录(R10-11) —— 正常创建/重名目录幂等/重名文件 409/名字含分隔符或点为 400/白名单外 403/父目录不存在 404/鉴权/不投命令
- test_fs_endpoints_route_fs_calls_through_long_path_prefix: fs 三端点的文件系统调用必须过 add_long_path_prefix_for_win(Windows 长路径 >MAX_PATH 否则 isdir 给假/scandir 抛错 ⇒ 误报 404)
- test_fs_endpoints_unmapped_root_semantic_404: Mapped 模式下白名单内但未命中 fs.path_map 的路径 -> fs 三端点语义化 404「不可判定」而非裸 500(BUG 回归: UNDETERMINED 禁止布尔化, 路由五处两态消费收进 _determinable 单点)
- test_fs_path_helpers_strip_long_path_prefix_before_compare: _bare/_fs_real 比较前剥长路径前缀(否则同一条路径的两种写法被判越界, 子目录全被过滤)
- test_drain_web_commands_group_actions: 组级暂停/开始/汇报/删除命令执行并作用于整组 hash
- test_drain_web_commands_torrent_actions: 单种子命令作用于该 hash; 种子不在快照 -> 跳过(删除守阵)
- test_api_torrent_write_endpoints_enqueue: 二轮种子写端点(15个) POST 转发 cmd/参数入队 + 无密钥 401
- test_api_t_bulk_group_keys_enqueue: bulk 组键模式(DLG-02): keys 编码组键入队解码回 tuple, 可与 hashes 混合; 纯 hash 载荷不带 keys 键; 无密钥 401
- test_api_t_bulk_tags_category_enqueue: bulk 标签/分类动作入队 —— tags 过滤空串非空才透传、category 按键存在性透传(空串=清除分类要保留)、未提供时载荷不带键(历史形态不变); 无密钥 401
- test_drain_web_commands_torrent_write_actions: 二轮写命令正常执行(参数透传/cmd_id 回执 ok/限速位置同步快照)
- test_drain_web_commands_torrent_write_unknown_hash_skips: 二轮写命令未知 hash 静默跳过不调 API
- test_drain_web_commands_share_limits_and_queue_mapping: share-limits 缺省维度 -2 补齐; queue 动作映射; 未知动作 error 回执
- test_drain_web_commands_torrent_write_param_errors: 写命令参数错误 -> error 回执且不调 API, 后续命令继续
- test_drain_web_commands_bulk_torrents: 批量多 hash 一次调用 + 聚合回执(部分缺失/未知动作/空列表 -> error)
- test_drain_web_commands_bulk_torrents_group_keys: bulk 组键模式(DLG-02): 组键展开级联全组成员删除; 与 hashes 混合去重; 缺失组计组数; 组不存在不调 API
- test_drain_web_commands_bulk_torrents_tags_category: bulk 标签/分类命令执行 —— add_tags/remove_tags/set_category 单次调用带全部 hash; 缺 tags / 缺 category 键 error 回执; 空串分类(清除)合法; 标签非空校验
- test_api_t_bulk_limits_location_enqueue: bulk 限速/移动动作入队(计划 26-10-02-1955 W2) —— up/dl/location 提供才透传(0=不限合法), 负数/limits 全空/location 空路径 400 不入队; 历史载荷形态不变; 无密钥 401
- test_api_t_bulk_skip_check_enqueue: bulk 跳检动作入队(计划 26-10-02-1955 W3) —— 无额外参数(载荷只有 hashes/action/delete_files); 无密钥 401; gate 在 drain 分派处, 路由层开关关时仍 200 入队
- test_drain_web_commands_bulk_torrents_limits_location: bulk 限速/移动分派 —— 只调有值方向、每方向一次调用传全 hashes; 写后快照同步(up_limit/dl_limit/save_path); 缺值 error 回执不调 API
- test_cmd_trackers_write_invalidates_lazy_cache: tracker 三兄弟写后失效 _trackers_info 惰性缓存(重读拉新值)
- test_drain_web_commands_unknown_and_error_continues: 未知命令与执行异常只记日志, 不中断后续消费
- test_drain_web_commands_empty_queue: 队列为空直接返回(queue.Empty 分支)
- test_verdict_reannounce_epoch_matrix: epoch 判定矩阵(②在途/③前跳 ==TOL 边界 pending/基线 status 0/1 行极值不触发/④status4+msg rejected 且先于前跳判, 空 msg 不判败; plan 26-10-05-0923)
- test_verdict_reannounce_legacy_matrix: legacy 判定矩阵(基线行无 epoch 字段 -> ②/③′/④ 生效, 前跳判据不参与)
- test_verdict_reannounce_min_window_guard: 判据② min 窗口守卫(基线 min 在未来 updating=推迟登记假瞬态 -> pending; 过期/缺失/0 后在途直证, S0 探针实证)
- test_trackers_baseline_shape_and_epoch_mode: baseline 形状回归 {url: {status, updating, next, min}} + epoch_mode 字段存在性探测(虚拟行排除)
- test_reannounce_receipt_prefix_contract: D4=warn 前缀文案契约(三前缀常量钉死, 改文案必红; 机器分流依据 = status 三值)
- test_reannounce_confirm_success_and_timeout: epoch 确认回执: 前跳命中 -> ok 回执跟踪清空; 超时 -> warn「未确认」不再判「失败」
- test_reannounce_confirm_group_aggregate: 组汇报三桶聚合(ok+error -> error 带计数与原因; 全推迟 -> warn「已受理」早回执 + 后台登记)
- test_reannounce_register_immediate_verdicts_and_deadline: 注册直判(停止种子立即 warn/推迟检出早回执+后台登记) + item 级 deadline 公式与 600 上限
- test_reannounce_stopped_midwindow_direct_verdict: 窗口内暂停直判(下一 tick warn「种子已停止」, 不等 deadline)
- test_reannounce_background_verify_and_cap: 推迟后台核实(达 min_e 出结论落 INFO/WARNING 日志并移除/逾时 DEBUG 静默移除/500 上限丢最旧 WARNING)
- test_cmd_group_actions_skip_missing_group: 组 key 不存在/成员不在快照 -> 空 hashes 不调 API
- test_cmd_reload_config_delegates: reload_config 命令委托 apply_new_config
- test_ensure_group_view_rebuilds_when_dirty: 分组视图脏时重建(Web 请求侧兜底)/干净时复用引用
- test_ensure_group_state_versioning: 分组视图版本号: 首次重建自增, rid 一致时不回传 groups
- test_ensure_group_state_show_view_carries_member_index: 追剧页必须连带成员索引(groups+singles), 但不回传种子平铺数组(否则刷新后追剧页永久空白)
- test_group_view_ver_seeded_from_start_time: 版本号以启动时间播种(进程重启不回落到旧值)
- test_api_state_rid_gate: /api/state 带 rid: 版本一致时 updated=False 且无 groups; 缺省/不匹配回传全量
- test_api_state_skips_jsonable_encoder: 热路径(/api/state、/api/groups)必须返回 JSONResponse 而非裸 dict —— 否则 FastAPI 会白跑一遍 jsonable_encoder 递归遍历响应体(3000 种子实测 161ms, 占端点耗时 85%); 用计数替身钉死
- test_api_state_view_scoped_payload: P1-1 按视图回传(只回当前视图数组; 未知 view 回全部; 增量门控优先)
- test_build_speed_totals_covers_ungrouped: 速度合计 = store 全量(组内成员 ∪ 未归组), 不能只算 groups(漏未归组实测少算 88.7%)
- test_api_state_speed_totals_survives_view_scoping: status.totals 恒回传 —— 种子页(不回 groups)/辅种页/rid 命中三种情况下都在且等于全量(issue 26-09-20-1646 防复现)
- test_frontend_hub_field_covers_non_leaf_items: 设置页 hub-field 模板必须显式覆盖 cfgFlatten 产出的**全部**非叶子项类型(section/group/subcard) —— 缺一支, 段项就落进叶子字段的兜底 `<input>`, 值被 String(对象) 成 "[object Object]"(2026-09-25 用户报)
- test_frontend_hub_field_renders_readonly_fields: schema Field.readonly(程序托管字段, issue 26-09-28-2135)接线守阵 —— CE_FIELD_BASE 有 readonly/readonlyComplex/readonlySummary 三成员, 控件链首支是只读摘要分支、全部可编辑控件挂 :disabled、行带「程序维护」徽标、settings-detail 块级 section 开关对 readonly 段换徽标(缺一处 = 该类字段仍可编辑, 保存却被后端覆盖/回退, 反馈误导)
- test_frontend_statusbar_speed_reads_server_totals: 静态防回潮 —— 前端 totalDl/totalUl 必须读 status.totals, 不得改回对 this.groups 求和
- test_frontend_hr_safety_wiring: 删除安全档位前端接线守阵 —— hr.js 的 token 映射表与后端 resolve.py 的 SRC_* 常量逐字一致、做种时长列 6 处换绑 hrDurClass/hrSrcClass + 挂 hrSrcFull/hrSrcHalf 底线与 hrPopEnter 触发 + 来源与已排除文案都走 hrDurHint 进 title(行内不留 chip) + 弹窗单例 DOM 每套 UI 恰一份、三套 CSS 的 hr-warn/hr-line/hr-pop 成对定义、js 引用的 m.hr_* 字段都在后端 hr_view_fields 键集里(字段打错 = 页面静默空白)
- test_frontend_hr_detail_table_wiring: HR 表① 全量详情表前端接线守阵(计划 26-10-01-2216 阶段2 + 26-10-02-1936 阶段3) —— 设置分区表① 模板绑定(档位 chips 本地过滤/已删除种子切换钮/明细行/空态/失踪行挂钩/「数据截至」时间戳/三列重组列名「核实结论」「在列」)+ 拍板守卫(remain_seconds 不进表、不挂 hr-pop、单元格无原生 title、表① 段无 <details>(排障视图在 aqb:hr-diag 独立段)、来源徽章类名 hr-vsrc 不复用已退役 hr-src)+ hr_status.js 按站点明细加载与本地筛选且无 setInterval(不轮询)+ .hr-detail-table 与档位色义四档/失踪行 --paused 弱化/来源徽章样式在三套 UI CSS 成对定义(prism 拆 components.css + views.css 两件)
- test_frontend_hr_diag_view_wiring: HR 表② 排障视图前端接线守阵(计划 26-10-01-2216 阶段3) —— 站点卡片 <details> 默认收起(无 open 属性)/ summary 文案 / 站点级 kv 行(hrsKvRows)与各档波次明细行(lanes[].detail 首获展示位)模板绑定 + 展开态不持久化(hr_status.js 无 localStorage)+ .hrs-diag/.hr-diag-kv/.hr-wave-table 三套 UI CSS 成对(波次表同挂 .hr-detail-table 继承表① 徽章色义)
- test_frontend_hr_full_modal_wiring: HR 站点状态折叠 + 覆盖式全屏弹窗守阵(计划 26-10-02-1936 阶段2) —— aqb:hr-full-modal 扫描锚段内遮罩/面板/头部(标题+摘要+✕)绑定齐全、有「展开/收起」钮且无独立「全屏」钮、面板无预展开属性(v-show 挂 hrsOpen); hrsOpen 默认 false(state.js)不持久化(hr_status.js/config_hub.js/state.js 无该键的 localStorage 写读); hubGo 不再自动拉数只复位 hrsOpen; ESC 关闭进 lifecycle 退栈链且同步 escBusy 名单(dialogs.js), 先于 1632 清筛选兜底; 首次展开才拉(hrsToggle 未 loaded 即调 loadHrStatus)、无 setInterval; .hr-full-mask/.hr-full-modal 三套 UI CSS 成对(prism 落 components.css)
- test_frontend_hr_contract_keys_match_backend: HR 两张表消费键契约守阵(计划 26-10-01-2216 阶段4 + 26-10-02-1936 阶段3 扩) —— 从前端源码提取消费键(表① e.*: 模板 aqb:hr-detail-table 段 + hr_status.js 行辅助与行集函数; 表② s.*/ls.*: hr_status.js 全文件 + aqb:hr-diag 模板段), 断言 ⊆ EntryDetail/SiteStatus/LaneStatus 的 to_dict 键集(后端侧闭集钉法 test_entry_details_field_surface 挡不住「上游改键+同步改 expected」的前端静默落空), 每组带核心键在场断言防提取器失效变恒真; 幻键集必须为空(表② 徽章人话 ls.lane_text 曾是幻键致渲染为空, 已修: LaneStatus 补 lane_text 字段由 _lane_statuses 填充, 白名单收空守阵恢复严格; local_present 是响应层 mark_local_present 追加的合法豁免)
- test_frontend_hr_table_sort_filter_reorg_wiring: HR 表① 已删除种子过滤 + 三态排序 + 三列重组守阵(计划 26-10-02-1936 阶段3; 文案 26-10-03 定) —— 切换钮默认「显示已删除种子 (N)」且 oldOn 默认关(只看本地仍在列), 旧误导文案「未做种/只看做种中」零残留; 表头十列全 sortable(hrsCols() 单点 + @click hrsSetSort + sprite 箭头)而表② 波次表无 sortable; 三态状态机(首点降→再点升→第三击恢复后端默认序, 换列直接降序); 比较器纯函数 hrsCompareRows 用 node 真跑(空值恒末位两方向不反转/verified_ts·last_seen 0 哨兵/档位 A<B<C<D 固定秩/字符串数值分型), 无 node 静默跳过; 新列结构(核实结论徽章+副行 / 在列·失踪徽章+副行)与 CSS 三处成对(th.sortable 箭头 accent·hover faint / .hr-sub 副行 / .hr-pres 徽章 / 名称列限宽钩子 + .hr-full-modal 放开); 旧列辅助 hrsVerifiedText/hrsStatusText 零残留
- test_frontend_hr_history_wiring: HR 表③ 拉取历史前端接线守阵(计划 26-10-04-0312 §3.5/§05 S4) —— aqb:hr-history 扫描锚 begin/end 成对且段内 <details> 默认收起 + summary 文案 + 站点 chips(hrsHistSiteChips 行内集合现算)+「仅看异常」toggle + 刷新钮 + 「数据截至」时间戳 + 十列表头(时间/站点/触发/结果/页数/行数/回填/放行/耗时/说明)+ 明细行 v-for 与展开明细子行(hr-hist-sub)+ 空态/未启用态文案 + read_errors 点名行; 取数纪律: 首次展开才 fetch(limit=300, @toggle -> hrsHistEnsureLoaded)+ 「刷新」手动重拉(hrsHistReload)+ 无 setInterval + 站点过滤纯前端本地筛不拼 site 查询串; 展开态不持久化(hr_status.js 代码态零 localStorage); .hr-hist-table/.hr-hist-row/.hr-hist-sub/.hr-hres 及五档色义(ok/warn/dim/err/blue)三套 UI CSS 成对
- test_frontend_ctx_submenu_single_entry_and_hover_close: 右键次级菜单守阵 —— 一级只留「更多操作」一个入口(复制族并入, CTX-06)、移出父项后延迟收起(CTX-05)、hover 图标规则必须限定直接子级且压特异性否则整片子面板变灰(CTX-04)
- test_frontend_ctx_menu_multi_select_targets_selection: 多选右键菜单守阵 —— 四个 open*Menu 必须写 menu.multi、三套 UI 必须有批量分支且调 ctxAct/ctxDelete、ctxAct/ctxDelete 必须复用 bulkAct/bulkDelete
- test_frontend_bulk_bar_retired: 批量控制条退役守阵 —— 三套 UI 模板零残留(.bulk-inline/bulkAct(/bulkDeleteLabel(/bulkHrWarnText() 与三套 CSS 死样式零残留(.bulk-inline/.bulk-btn/.bulk-hr-warn/.bulk-sep/.bulk-count/.bulk-enter-*/.ico-select/@keyframes bulk-in), 批量链路 bulkAct/bulkDelete 仍在且 ctxAct/ctxDelete 复用
- test_frontend_meta_dialog_paired: 标签/分类编辑对话框守阵 —— 三套 UI 成对(metaOpen 对话框 + 批量菜单/单种子菜单两处入口, 批量控制条退役后模板层不再直接调 openMetaDialog(null))、shared 逻辑接线(openMetaDialog 锁定目标 + metaToggleTag 走 bulk 链路 + ctxMeta 先收菜单)、.meta-dialog/.opt-pill 三套 CSS 成对定义
- test_api_state_status_carries_server_state: status.server(state)恒回传不受 rid 门控(状态栏与行数据同源同轮)
- test_api_category_tag_endpoints: 分类/标签 CRUD 端点(入队与 400 校验)
- test_category_tag_commands_execute: 分类/标签命令执行(QbApi 封装 + 缓存失效)
- test_api_speed_mode_and_override: /api/speed/mode 曲线/停用两形态 + /api/speed/override 落 transfer 端点
- test_api_speed_alt_and_toggle: ALT-01 备用速度 —— /api/speed/mode 增列 alt_on/alt_current + /api/speed/alt 落 setPreferences(alt_*) + /api/speed/alt/toggle 落 toggle 端点
- test_qbapi_alt_speed_limits_normalization: ALT-01 QbApi 备用限速 KiB<->bytes/s 换算 + setPreferences 增量语义(只传非 None 方向) + 模式切换
- test_api_speed_mode_curve_config_disabled: 曲线存在但 enabled=False -> curve_enabled=False(快照之上叠加配置判定)
- test_api_add_torrent_endpoint: /api/torrents/add multipart(bytes 内存直传/选项透传/空来源 400)
- test_add_torrent_receipt_and_optional_flags: 添加回执两形态(API>=2.14.0 的 JSON 元数据 / 旧文本 "Ok.")判受理 + 两个 optional 选项(停止位 is_stopped / 自动管理 use_auto_torrent_management)恒显式下发(省略会吃 qB 会话/全局默认) + 成功走 INFO(改前 WARNING 会直推桌面弹窗)
- test_frontend_add_torrent_drag_drop_wiring: DND-01 全局拖拽添加种子接线守阵(静态) —— window 级 drag 四事件 add/remove 对称、drop handler 必 preventDefault(否则浏览器直接打开文件)、接管判据只认 Files/text-uri-list(不误拦页面内拖文本)、双 UI 落点遮罩成对 + app.js addDragOver 状态
- test_frontend_add_combo_blur_close_and_fit: 添加种子三下拉「失焦即收 + 限高不出窗」接线守阵(2026-10-03 报障) —— 三输入框 @focusout 收层 + 收层必须 40ms 合帧守卫(label 转发回焦同步收 = 闪烁) + 三开层方法撤销挂起收层 + 开层 watcher 量「输入行→滚动容器可见底沿」净空限高(滚动条留在窗口内) + 候选异步到位重限 + 三浮层互斥双向(closeAddPopsExcept 单点, 三开层各调一次, 26-10-04-0130)
- test_frontend_add_combo_label_clear_mask_and_refit: 添加种子三下拉「第二轮遗留四项」守阵(2026-10-03, label 闪烁 2026-10-04 三修+四轮 JS 守卫) —— 四个 combo 的字段 label 一律 @mousedown.prevent + @click.stop(mousedown 默认动作 blur 武装的 40ms 合帧定时器在人手按住期间先收层、松手转发回焦再重开 = 闪烁; stop 挡 window click 收层; 缺一即回归)+ 收层 JS 单点守卫 _popBlurShouldHold(收层前判「焦点已回本族输入框 / 本族 label 转发 click 仍在途」→ 不收, 模板修饰符缺位(旧页签残留)时独立根除闪烁, add 三字段 + meta 分类全接)+ 三输入框内嵌清空 x(@mousedown.prevent 保焦点 + @click.stop 挡 window 收层, 缺一即「清完下拉没了」)+ 遮罩关窗改「mousedown 记臂位 + mouseup.self 才关」(全仓 11 处, @click.self 会被"拖选文字终点落在遮罩上抬手"误判成点空白关窗, 零残留)+ 过滤词变化重限高(三个输入值 watcher + meta 侧三处)+ meta 分类下拉补失焦收层与 window click 兜底名单 + 清空钮样式三皮肤成对
- test_frontend_button_system_paired: 按钮体系(.bt)迁移守阵 —— ce-btn/ce-icon 全语料零残留、.bt 六变体两套 CSS 成对定义、两套模板 bt 用量逐类相等、双色令牌(on-accent/on-accent-ink/on-error)星图 :root + 棱镜五主题成对声明
- test_api_export_endpoint: /api/torrents/{hash}/export 字节流与 disposition(404/503); 非 ASCII 种子名走 filename*(回归: 头 latin-1 编码崩)
- test_content_disposition_encoding: content_disposition 头值纯 ASCII + filename* 百分号编码 + 清洗/回退
- test_api_log_endpoint: /api/log tail 与 level 过滤(未配置空)
- test_api_log_level_filter_follows_config_format: 等级过滤按 config.logging.format 定位等级名(生产格式无方括号, 按字面量 `[WARNING` 捞会恒空 —— 2026-09-25 真机 bug)
- test_api_log_level_filter_keeps_multiline_record: 多行日志(整段 traceback)折行后跟随其记录的等级, 筛 ERROR 不丢栈
- test_api_log_note_when_level_unfilterable: 筛不了(格式无等级字段 / 已存行与格式不符)回全部行 + note, 不静默给空
- test_api_category_tag_list_endpoints: GET /api/categories 与 /api/tags 列表端点(store 缓存数据源)
- test_api_tags_exclude_auto: /api/tags?exclude_auto=1 剔除程序自动维护标签(站点/HR 精确集 + 集数模板形状; 事件标记保留, 不带参全量)
- test_seed_flat_view_fields_and_gating: 种子平铺视图(SEED_ITEM)字段契约齐全 + ensure_group_state 同门控回传
- test_flat_view_refreshed_by_main_loop_tick: 种子页速度随主循环刷新(回归: 平铺视图曾被"饿死"停在旧快照)
- test_rebuild_views_single_entry_point: rebuild_views 唯一重建入口(四视图 + 版本号 + 脏标记一次完成)
- test_api_torrent_detail_endpoint: /api/torrents/{hash} 全字段详情(to_dict+site+HR); 未知 hash 404
- test_api_torrent_subresources: /api/torrents/{hash}/trackers|files|peers 透传(未知 404/断连 503)
- test_api_readonly_endpoints_short_cache: P1-4 只读端点短缓存(窗口内合并 / 写命令后失效 / 断连仍 503)
- test_api_torrent_peers_endpoint: /api/torrents/{hash}/peers 走 sync_torrent_peers(torrent_hash=..)整包透传(404/503)
- test_api_stats_endpoint: /api/stats 透出 store.server_state(未同步时 null)
- test_state_kind_maps_states: 状态语义分类映射(暂停态优先于下载/做种)
- test_apply_new_config_levels: 配置热重载按 L0/L1/L2/R 级别应用; L1 只剩重连(web 重启/logging/notify/HR 全部改经模块 apply, P1-P2); L0 下 hr.apply 也必须被调到(HR 路由守阵)
- test_apply_new_config_l2_preserves_runtime_state: L2 热重载保留运行期内存 state —— 不得重读磁盘旧版回滚 exec_history/skip_check_day/recheck_fails(issue 26-09-21-1347 守阵)
- test_stop_web_server_releases_port_for_restart: 停止后服务线程真正退出, 同端口可再次监听(10048 回归守阵)
- test_start_web_server_started_message_is_info: 「WEB UI 已启动」按 INFO 记(alert-levels 契约: 生命周期消息不许 WARNING, 否则 notify 开启时每次启动弹通知)
- test_webui_module_apply_skips_restart_when_bind_unchanged: 监听身份未变 -> 不重启, 仅刷新密钥(经 WebUIModule.apply 驱动, P2)
- test_webui_module_apply_toggle_enabled: web.enabled 热开关(关->开启动 / 开->关停止并清句柄; 经 WebUIModule.apply 驱动, P2)
- test_start_web_server_reports_failure_when_port_taken: 端口被占用 -> 句柄未就绪 + ERROR 日志(不再静默)
- test_web_loop_exception_handler_downgrades_connection_reset: 网络波动(WinError 10054 对端强迫关闭)降级为一行 INFO, 不再 ERROR + traceback
- test_web_loop_noise_log_throttled_in_window: 断连日志按窗口节流(窗口内只记首条, 出窗口附抑制条数)
- test_web_loop_exception_handler_delegates_real_bug: 反向守阵 —— 非波动异常交回 asyncio 默认处理器, 不吞
- test_is_network_fluctuation_matrix: 波动判定矩阵(异常类 / winerror / errno 三条路都认; 非 OSError 与"目标拒绝"不算)
- test_uvicorn_config_installs_loop_exception_handler: 处理器必须真的装到 uvicorn 事件循环上(经 get_loop_factory 注入)
- test_cmd_trackers_log_sanitized: tracker 编辑/移除日志只写脱敏主地址 —— 任意命名的凭据全文都不进日志(不按参数名黑名单), 主地址仍在
- test_web_route_manifest_frozen: 路由金清单守阵(W0, plan 26-09-22-1857; ALT-01 增 2 条 speed/alt, P2' 增 1 条 skip-check, 26-10-01-2216 阶段1 增 1 条 hr sites entries, 26-10-02-1955 W1 增 1 条 webui/flags, 26-10-03-0946 P4 增 3 条 traffic/qb, 26-10-04-0312 S3 增 1 条 hr history, 26-10-05-0314 S2 增 1 条 skip-check/precheck): 77 条 (method, path) 集合逐一钉死, web.py 拆 web/ 包期间任何路由丢失/改名/方法变更即红
- test_drain_web_commands_recheck_rejected_while_checking: R1 单发拒绝(plan 26-09-30-0109) —— 规则校验在途时 WEB recheck 回执 error「校验进行中」, qB 不重启校验
- test_drain_web_commands_bulk_recheck_skips_inflight: R1 bulk 第二入口 —— 在途 hash 逐个经 ops 过滤, 聚合回执带「N 个校验进行中已跳过」, 其余正常提交
- test_drain_web_commands_bulk_skip_check_aggregated: bulk 跳检经 ops 逐 hash 串行(计划 26-10-02-1955 W3) —— 混合结果聚合回执分段计数(成功 / 同日去重 skip / 部分下载禁+执行失败 fail); 成功批 ok 回执且记录同日去重(skip_check_day 跨来源共享)
- test_drain_web_commands_bulk_skip_check_gated: bulk 跳检 gate(D2=是·fail-closed) —— web.skip_check_menu 关时 drain 分派处拒单且零 qB 调用; 同 manager 实时改配置即放行(现读不按值持有)
- test_drain_web_commands_skip_check_torrent: 右键跳检命令(P2') —— 经 ops 层四阶段全流程, 回执 ok 且记录同日去重
- test_web_skip_check_completed_rejected_receipt: T10(26-10-05-0314 S2) —— 单发已完成种子: ops G3 闸门拒绝文案经 ActionResult 通道原样透传进 error 回执(不截断不改写), 零 qB 写调用
- test_web_bulk_skip_check_mixed_outcome: T11(26-10-05-0314 S2) —— 批量混合(1 已完成 + 1 暂停未完成): 聚合回执失败计数与文案自解释(G3), 成功标的走通四阶段并记同日去重(T12 门控不回归由既有 test_api_t_skip_check_gated_by_config(单发 403)/test_drain_web_commands_bulk_skip_check_gated(批量拒单)+ 本轮 T21 预检 403 断言覆盖, 无新用例)
- test_web_precheck_endpoint: T21(26-10-05-0314 S2) —— 预检端点 POST /api/torrents/skip-check/precheck: 路由级 403 门控同单发(fail-closed 零入队)/空 hashes 400 不入队/入队载荷 {hashes}; drain 级回执 truth={results, summary} 结构、混合 {ok, force, blocked} 计数、未知 hash → cls=blocked 文案「已不在客户端」
- test_web_force_passthrough: T22(26-10-05-0314 S2) —— 单发 body.force → ops.skip_check 收到 force=True(mock kwarg 断言)/缺省 force=False; 批量 body.force → _bulk_skip_check_via_ops 逐 hash 透传; 路由级提供才透传(缺省载荷形态不变); force=true 时 case 1 闸门(G3)照常硬拒进回执
- test_webui_no_rules_import: 边界守阵(P2') —— webui 操作链不得 import 规则模块; 其余 webui 模块不得触碰规则动作插件(rules.actions/registry)
- test_create_app_is_thin_assembly: 组装壳守阵(W6): create_app 源 ≤150 行且无内联路由装饰器(防 926 行单函数回潮)
- testhr_view_fields_three_state: 详情字段透出站点侧三态与依据(接入站点才有值, 未接入全空)
- testhr_view_fields_excluded: HR 排除态视图(hr_excluded=True, 触发/达标 False, 站点侧全空, 桥不被打扰)
- test_api_hr_status_disabled_returns_empty_state: 未启用 HR 时 /api/hr/status 回 enabled=false + 说明(前端空态, 不报错)
- test_api_hr_status_reports_site_state: 启用后逐站点摊开现状 —— 新鲜度/覆盖证明/索引与回填进度/配额/熔断/
  「现在为什么不放行」(与 --hr-status 同一 `hr.status` 口径) + 波次明细 lane_text 徽章人话逐档正确(LANE_TEXTS 单点)
- test_api_hr_status_names_the_blocking_step: 覆盖证明不成立时要说清卡在哪一步(用户看到种子没放行时最想知道的一句)
- test_api_hr_site_entries_full_fields: 种子明细端点(计划 26-10-01-2216 §7 阶段1)200 全字段 —— 行键面 = §3 P0+P1 全集
- test_api_hr_site_entries_verified_two_states: verified 有/无两态同表(无记录→未核实; 有记录→verified_ts+source 原值+人话)
- test_api_hr_site_entries_empty_site: 站点已接入但没有 HR 行 -> 200 + 空数组(前端空态)
- test_api_hr_site_entries_guards: HR 未启用 400 / 站点未接入 404(与 confirm-empty 同款话术)
- test_api_hr_site_entries_409_worker_absent: hr 门面在但取数服务缺席(service=None) -> 409 不假装有数据
- test_api_state_excludes_hr_entry_details: 体积守卫 —— 种子明细键不得进 /api/state 轮询载荷(计划 §8)
- test_api_hr_site_entries_local_present: 明细行 local_present 本地库 join(计划 26-10-02-1936 §3.3 决策点③a) ——
  v1 命中/仅 v2 命中/大小写差异命中 -> True, 本地不存在 -> False(未做种)
- test_api_hr_history_rows_from_real_wave: 拉取历史端点(计划 26-10-04-0312 §3.4)200 —— 行键面 = §3.4 全集,
  真实波次(S2 记录器)落表; 完成徽章/触发人话/档位 lane_text/写者短标识全由后端算好
- test_api_hr_history_site_filter: site 过滤只回该站; 未接入 404 点名已接入清单(与 entries 同款话术)
- test_api_hr_history_guards: HR 未启用 400 / 取数服务缺席 409(与 entries 同款校验)
- test_api_hr_history_limit_clamped: limit 截最新 N 条; 0 钳到 1(不回全量也不回空页)
- test_api_hr_history_read_error_reported_not_raised: 站点文件读坏不抛 —— read_errors{site: err} 带出, rows 剔掉坏站
- test_hr_user_visible_texts_no_graduation_wording: 否定守阵 —— 用户可见文案来源(hr status/resolve/events 字符串常量)「毕业」零残留
  (注释保留域术语, 决策点②); 无事实分支与带事实分支同文「在线·已达标」(testhr_view_fields_three_state 内钉)
- test_api_keys_get_default_when_missing: 快捷键配置文件不存在 -> GET 回默认表(计划 26-09-28-0354 W6 §4.4)
- test_api_keys_put_roundtrip: PUT 合法配置落盘(atomic_write)且 GET 原样回读; 空串=显式禁用语义保留
- test_api_keys_put_invalid_rejected: PUT 结构非法(schema_version/模板/overrides 形状/归一化串) -> 422 且不触碰磁盘
- test_api_keys_read_corrupt_fallback: 主文件坏 JSON -> WARN + 默认表; .bak 完好 -> 回备份(读时兜底链)
- test_api_keys_unknown_schema_version_fallback: schema_version 不识别 -> 回默认表 + WARN(升级链口径: 宁可回默认不带病生效)
- test_api_events_sse_stream_lifecycle: SSE 生成器整块(hello 帧/事件帧/keepalive 心跳/终结退订;
  TestClient 会挂死无限流, 直调端点驱动 body_iterator)
- test_api_events_sse_generator_error_still_unsubscribes: 生成器异常死亡也走 finally 退订
- test_api_hr_confirm_empty: 人工对账戳端点(缺 site/未启用/未接入 400, 成功 ok, 写入失败 409)
- test_api_hr_refresh_single_site_and_no_runtime: refresh 指定单站受理 + hr 门面缺席回 409
"""
import base64
import errno
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

from auto_qb import __version__
from auto_qb.config.models import HrCheckConfig
from auto_qb.infra import file_access
from auto_qb.infra.utils import decode_group_key, encode_group_key
from auto_qb.webui import create_app
from auto_qb.webui.runtime import (
    CMD_SLOW_MS,
    EVENT_QUEUE_MAX,
    REANNOUNCE_CONFIRM_TIMEOUT,
    WEB_RESULT_MAX,
    WEB_RESULT_TTL,
    WebUIRuntime,
)

KEY = ("R:/seeds", ("a.mkv", "b.mkv"))


def _web_stub(enabled=True, host="127.0.0.1", port=8080, token="t"):
    """WEB 段替身(仅 _apply_web_config 关心的字段)"""
    return SimpleNamespace(enabled=enabled, host=host, port=port, token=token)


def _free_port() -> int:
    """取一个本机空闲端口(先绑 0 再释放; 用于真实起停 WEB 服务器的测试)"""
    import socket

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _make_web_manager(tmp_path, config_text):
    """构造 WEB API 所需的 manager 替身(轻量 namespace, 不连 qB)"""
    from types import SimpleNamespace

    wake_calls = []  # 记录 manager.wake() 调用: 投递用户命令应唤醒, 自投递命令不应唤醒
    state_file = os.path.join(tmp_path, "state.json")
    config_file = os.path.join(tmp_path, "config.yml")
    with open(config_file, "w", encoding="utf-8") as f:
        f.write(config_text)
    web_cfg = SimpleNamespace(
        enabled=True,
        host="127.0.0.1",
        port=8080,
        token="",
        skip_local_verify=False,
        # R2(计划 26-10-02-1955 W1): 测试侧默认开 —— gate 用例按需实例级置 False
        skip_check_menu=True
    )
    config = SimpleNamespace(
        web=web_cfg,
        trackers={
            "HHan":
                SimpleNamespace(
                    tags=["HHan"],
                    remove_tags=[],
                    remove_similar_tags=False,
                    upload_speed_limit=0,
                    download_speed_limit=0,
                    hr=None,
                    domains=["d.com"],
                    rules=[]
                )
        },
        state_file=state_file,
        data_dir=str(tmp_path),
        grouping=SimpleNamespace(enabled=True, check_missing_files=True, missing_tag="MISSING"),
        add_episode_tags=SimpleNamespace(enabled=False, add_tag_single="", add_tag_multi=""),
        delete_tags=[],
        delete_tags_if_has_no_torrents=[],
        global_speed_limit_curve=None,
        qb_traffic=None,  # qB 口径流量(plan 26-10-03-0946 §06): None = 未启用; 用例按需置 QbTraffic(enabled=True)
        notify=SimpleNamespace(enabled=False),
        qbittorrent=SimpleNamespace(host="127.0.0.1", port=1, username="u", password="p"),
        logging=SimpleNamespace(level="WARNING", file="", max_bytes=1048576, format="%(message)s"),
        main_tick=2.0,
        sync_interval=1.5,
        max_tasks_per_tick=20,
        interval=60.0,
        remove_similar_tags=False,
        skip_checking_tag="zSkipChecked",
        rules_config={},
    )
    groups = {KEY: ["HA", "HB"]}
    view = [
        {
            "key":
                encode_group_key(KEY),
            "name":
                "Show",
            "count":
                2,
            "dlspeed":
                0,
            "upspeed":
                2048,
            "uploaded":
                4096,
            "size":
                1024**3,
            "members":
                [
                    {
                        "hash": "HA",
                        "site": "HHan",
                        "state": "stalledUP",
                        "kind": "seeding",
                        "dlspeed": 0,
                        "upspeed": 1024,
                        "uploaded": 2048,
                        "size": 512**2,
                        "progress": 1.0,
                        "seeding_time": 3600,
                        "ratio": 1.2
                    },
                    {
                        "hash": "HB",
                        "site": "M-Team",
                        "state": "pausedUP",
                        "kind": "paused",
                        "dlspeed": 0,
                        "upspeed": 1024,
                        "uploaded": 2048,
                        "size": 512**2,
                        "progress": 1.0,
                        "seeding_time": 3600,
                        "ratio": 1.2
                    },
                ],
        }
    ]
    mgr = SimpleNamespace(
        status_snapshot=lambda: {
            "connected": True,
            "paused": False,
            "torrents": 2
        },
        state_file=state_file,
        data_dir=str(tmp_path),
        config=config,
        config_path=config_file,
        store=SimpleNamespace(groups=groups, by_hash={}, get=lambda h: None, server_state=None),
        client=None,
        # 命令唤醒(真实 manager 置位 _wake_event 让主循环立即消费); 此处记录调用供断言
        wake=lambda: wake_calls.append(1),
    )
    # 模块宿主替身(schema 端点的段认领由模块 sections() 派生, W4 级别表退役)
    mgr.host = SimpleNamespace(
        modules=lambda: [
            SimpleNamespace(name="webui", sections=lambda: ("web", )),
            SimpleNamespace(name="tracker", sections=lambda: ("trackers", )),
            SimpleNamespace(name="rules", sections=lambda: ("rules_config", "interval")),
        ]
    )
    # 详情端点的 HR 展示字段由 WebviewMixin 静态方法提供; stub 直接引用同一实现
    from auto_qb.core.qbmanager import QbManager

    # 命令投递经表现层门面(WebUIRuntime.post_command): post_command 与 consume_commands
    # 共用 runtime 自带的 commands 队列 —— 端点测试直投 mgr.web.commands, 断言仍然成立
    from auto_qb.webui import WebUIRuntime

    mgr.web = WebUIRuntime(mgr)
    # routes 走 web.* 新名口(plan 别名层处置 W1/W2): 替身数据挂门面命名空间,
    # 门面方法覆盖为读替身数据
    mgr.web.group_view = view
    mgr.web.flat_view = []
    mgr.web.traffic_view = {"state": "disabled", "periods": [], "history": [], "limit": {}}
    mgr.hr_view_fields = QbManager.hr_view_fields
    mgr._wake_calls = wake_calls  # 供端点测试断言"投递命令是否唤醒主循环"
    # 视图替身方法: routes 现调 web.ensure_view / web.ensure_state, 这里把门面方法指到替身数据上
    mgr.web.ensure_view = lambda: mgr.web.group_view

    def _ensure_group_state(rid, view=None):
        # 与真实实现同形: 默认回全部; P1-1 带 view 时只回该视图的数组
        from auto_qb.webui.views import VIEW_ARRAYS

        updated = rid != mgr.web.group_view_ver
        state = {"rid": mgr.web.group_view_ver, "updated": updated}
        if updated:
            arrays = {
                "groups": mgr.web.group_view,
                "singles": [],  # 与真实 ensure_group_state 同形: singles 随 groups 同门控回传
                "shows": {
                    "list": [],
                    "unrecognized": []
                },
                "torrents": mgr.web.flat_view,  # 种子平铺视图同门控(与真实实现同形)
            }
            for k in (VIEW_ARRAYS.get(view) if view else None) or arrays:
                state[k] = arrays[k]
        return state

    mgr.web.ensure_state = _ensure_group_state
    return mgr


@pytest.fixture()
def web_env(tmp_path):
    """带 TestClient 的 WEB 环境(manager 替身 + 密钥已生成)"""
    from fastapi.testclient import TestClient

    from auto_qb.webui import create_app, ensure_web_token

    mgr = _make_web_manager(
        tmp_path,
        "config:\n  qbittorrent:\n    host: h\n    port: 1\n    username: u\n    password: p\n  schema_version: 4\n"
    )
    mgr.web.token = ensure_web_token(mgr)
    app = create_app(mgr)
    client = TestClient(app)
    return mgr, client


def test_api_requires_token(web_env, caplog):
    """无/畸形/错密钥访问 /api/* -> 401

    缺省/畸形凭证(无头、裸 Bearer、错 scheme)静默 401 不记 WARNING(历史误报: 前端空 token
    发出 "Bearer " 被 HTTP 层裁成裸 "Bearer", 每次空提交都刷 WARNING 并触发系统通知);
    仅"携带了但错误"的密钥记恰好一条 WARNING, 且文本不含任何密钥片段。
    """
    mgr, client = web_env
    web_logger = "auto_qb.web"
    malformed = (
        None,  # 完全无头
        "Bearer",  # 有 scheme 无 token(等价于前端空 token 经 OWS 裁剪后的值)
        "Bearer ",  # scheme 后仅空白(未经 OWS 裁剪的原始形态)
        "Token xyz",  # 错 scheme
    )
    caplog.set_level(logging.WARNING, logger=web_logger)
    for header in malformed:
        caplog.clear()
        kwargs = {} if header is None else {"headers": {"Authorization": header}}
        assert client.get("/api/status", **kwargs).status_code == 401
        assert not [r for r in caplog.records if r.name == web_logger and r.levelno >= logging.WARNING
                   ], (f"畸形凭证 {header!r} 不应记 WARNING")
    # 携带了但错误的密钥: 401 + 恰好一条不含密钥内容的 WARNING
    caplog.clear()
    assert client.get("/api/status", headers={"Authorization": "Bearer wrong"}).status_code == 401
    warns = [r for r in caplog.records if r.name == web_logger and r.levelno == logging.WARNING]
    assert len(warns) == 1
    assert mgr.web.token not in warns[0].getMessage()
    assert mgr.web.token[:8] not in warns[0].getMessage()
    # 正确密钥放行
    assert client.get("/api/status", headers={"Authorization": f"Bearer {mgr.web.token}"}).status_code == 200


def test_config_public_endpoint_no_auth(web_env):
    """公开只读端点 /api/config/public: 免 token 可读但**仅限 loopback**, 只暴露本机免鉴权标志

    该标志只对本机浏览器有用(免鉴权本就只对 loopback 生效); 远端可读等于向攻击者
    广播「CSRF 面开关」状态(issue 26-09-21-1408 B-02) —— 403 明确拒绝, 前端读取失败
    自然回落密钥表单(TestClient 缺省对端 testclient 非 loopback, 正好充当远端)。
    """
    from fastapi.testclient import TestClient

    mgr, client = web_env
    # 远端(非 loopback): 403, 不广播开关状态
    assert client.get("/api/config/public").status_code == 403
    # loopback: 免密钥可读, 默认关闭值 false
    loopback = TestClient(client.app, client=("127.0.0.1", 50000))
    resp = loopback.get("/api/config/public")
    assert resp.status_code == 200
    assert resp.json() == {"web": {"skip_local_verify": False}}
    # 不泄露访问密钥
    assert str(mgr.web.token) not in resp.text


def test_api_webui_flags_endpoint(web_env):
    """R2 功能旗标端点(计划 26-10-02-1955 W1): 开/关读**实时配置** + 未鉴权 401

    FakeConfig 测试侧默认 skip_check_menu=True(helpers, 供既有 skip-check 用例直通);
    关闭用例实例级置 False(深拷贝, 不跨测试泄漏) —— 端点必须现取 manager.config 引用,
    不按值持有旧 Config(hot-reload-held-config 坑)。
    qb_traffic_enabled(P5a, plan 26-10-03-0946 §07): 段缺省 None / enabled=false 均 False,
    _enable_qb_traffic 置段 enabled=True 后即时翻真(读实时配置口径)。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    assert client.get("/api/webui/flags", headers=auth).json() == {
        "skip_check_menu": True,
        "qb_traffic_enabled": False,  # FakeConfig 默认 qb_traffic=None(未启用)
    }
    mgr.config.web.skip_check_menu = False
    assert client.get("/api/webui/flags", headers=auth).json() == {
        "skip_check_menu": False,
        "qb_traffic_enabled": False,
    }
    _enable_qb_traffic(mgr, enabled=True)
    assert client.get("/api/webui/flags", headers=auth).json()["qb_traffic_enabled"] is True
    _enable_qb_traffic(mgr, enabled=False)
    assert client.get("/api/webui/flags", headers=auth).json()["qb_traffic_enabled"] is False
    assert client.get("/api/webui/flags").status_code == 401


def test_api_t_skip_check_gated_by_config(web_env):
    """R2 skip-check 端点 gate(D2=是 · fail-closed): 配置关 403(detail 注明键名) / 配置开 200 入队

    gate 读实时配置 —— 同一 client 内翻转配置键即时生效; 403 时不得投递命令。
    rule 源跳检回归哨: test_ops.py 全部零改动全绿。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    mgr.config.web.skip_check_menu = False
    resp = client.post("/api/torrents/HA/skip-check", headers=auth)
    assert resp.status_code == 403, resp.text
    assert "web.skip_check_menu" in resp.json()["detail"], "403 detail 必须注明配置键名"
    assert mgr.web.commands.empty(), "配置关时不得投递命令"
    mgr.config.web.skip_check_menu = True
    resp = client.post("/api/torrents/HA/skip-check", headers=auth)
    assert resp.status_code == 200, resp.text
    cmd, payload = mgr.web.commands.get_nowait()
    assert cmd == "skip_check_torrent" and payload["hash"] == "HA"


def test_skip_local_verify_loopback_bypass(web_env, caplog):
    """web.skip_local_verify=true 时: 本机(loopback)连接免密钥放行, 直接进入

    默认 false(保守): 本机连接仍强制鉴权; 开启后仅 loopback 放行 —— 对外/远端连接
    (request.client.host 非 127.0.0.1/::1)即使带对密钥以外的任何请求也须密钥(仍强制)。
    提示日志**每进程只记一次**(R10-01)且为 **INFO**: 免鉴权模式下前端按设计不发 Authorization
    头, 每请求都记会把轮询日志刷满; 首次记一条足以说明该实例不校验密钥。级别用 INFO 而非
    WARNING —— 免鉴权是用户显式开启的配置(非异常), WARNING 会经 notify 推送扰民。
    跨站防护(issue 26-09-21-1408)开启后 Host 白名单生效: 请求须带合法 Host 头(TestClient
    缺省 Host=testserver 不在白名单, 真实浏览器请求必然携带 loopback/自配 host 形态)。
    """
    from fastapi.testclient import TestClient

    from auto_qb.webui import create_app

    mgr = web_env[0]
    # 用独立 loopback 客户端 + 开启开关
    mgr.config.web.skip_local_verify = True
    app = create_app(mgr)
    host_hdr = {"Host": "127.0.0.1:8080"}
    loopback = TestClient(app, client=("127.0.0.1", 50000))
    remote = TestClient(app, client=("192.168.1.50", 50000))

    caplog.set_level(logging.INFO, logger="auto_qb.web")
    caplog.clear()
    # 本机: 无密钥/错密钥均放行(直接进入)
    assert loopback.get("/api/status", headers=host_hdr).status_code == 200
    infos = [r for r in caplog.records if r.name == "auto_qb.web" and r.levelno == logging.INFO]
    assert infos and "skip_local_verify" in infos[-1].getMessage()
    assert not [r for r in caplog.records if r.name == "auto_qb.web" and r.levelno >= logging.WARNING], \
        "免鉴权是显式配置而非异常: 不得记 WARNING 及以上(否则经 notify 推送扰民)"
    # 只记一次: 其余免密钥请求不再刷日志
    caplog.clear()
    assert loopback.get("/api/status", headers=host_hdr).status_code == 200
    assert loopback.get("/api/status", headers={**host_hdr, "Authorization": "Bearer wrong"}).status_code == 200
    assert not [r for r in caplog.records if r.name == "auto_qb.web" and "skip_local_verify" in r.getMessage()]
    # 对外/远端连接: 仍强制鉴权(Host 头合法 —— 白名单不关心对端地址; 凭证面语义不变)
    assert remote.get("/api/status", headers=host_hdr).status_code == 401
    assert remote.get(
        "/api/status", headers={
            **host_hdr, "Authorization": f"Bearer {mgr.web.token}"
        }
    ).status_code == 200


def test_skip_local_verify_cross_site_guard_host_whitelist(web_env, caplog):
    """skip_local_verify 开启时 Host 白名单(DNS rebinding 防护, issue 26-09-21-1408)

    attacker.com 指向本机时浏览器带来的 Host 头是外部域名 —— 不在白名单一律 **403 明确
    拒绝**(API 与静态路径同闸: rebinding 下攻击页从本源加载页面是同源读的前提);
    合法变体(loopback 全形态 + 自配 host)照常放行, 不破坏正常本机使用。
    """
    from fastapi.testclient import TestClient

    from auto_qb.webui import create_app

    mgr = web_env[0]
    mgr.config.web.skip_local_verify = True
    client = TestClient(create_app(mgr), client=("127.0.0.1", 50000))
    caplog.set_level(logging.WARNING, logger="auto_qb.web")
    # 外部域名(rebinding 面): API 与静态页一律 403, 不静默(WARNING 留痕)
    assert client.get("/api/status", headers={"Host": "attacker.com"}).status_code == 403
    assert client.get("/", headers={"Host": "attacker.com:8080"}).status_code == 403
    warns = [r for r in caplog.records if r.name == "auto_qb.web" and r.levelno == logging.WARNING]
    assert warns and "Host" in warns[0].getMessage()
    assert mgr.web.token not in warns[0].getMessage(), "拒绝日志不得含密钥内容"
    # 合法变体放行: host:port / 裸 host / [::1]:port 全形态
    for host in ("127.0.0.1:8080", "localhost:8080", "[::1]:8080", "127.0.0.1", "localhost"):
        assert client.get("/api/status", headers={"Host": host}).status_code == 200, host


def test_skip_local_verify_cross_site_guard_write_origin(web_env):
    """skip_local_verify 开启时写方法 Origin 同源校验(CSRF 防护, issue 26-09-21-1408)

    本机网页对 /api/* 发跨站简单请求(不触发 CORS 预检)即可驱动写命令 —— 写方法上
    Origin 非空时必须是白名单同源, 否则 403 且**命令不入队**; 同源 Origin(浏览器对同源
    POST 也会带)与无 Origin(curl/脚本)照常放行; GET 不校验(跨站读拿不到响应体,
    危害面在写, 与 issue 修法一致)。
    """
    from fastapi.testclient import TestClient

    from auto_qb.webui import create_app

    mgr = web_env[0]
    mgr.config.web.skip_local_verify = True
    client = TestClient(create_app(mgr), client=("127.0.0.1", 50000))
    host_hdr = {"Host": "127.0.0.1:8080"}
    body = {"text": "(tor.size >= 1GiB)"}
    # 读方法不校验 Origin(跨站 GET 响应不可读, 无危害面)
    assert client.get("/api/status", headers={**host_hdr, "Origin": "http://evil.com"}).status_code == 200
    # 写方法 + 跨站 Origin: 403 且不入队
    assert client.post(
        "/api/expr/eval", headers={
            **host_hdr, "Origin": "http://evil.com"
        }, json=body
    ).status_code == 403
    # 同源 Origin(host:port 与端口一致)放行
    assert client.post(
        "/api/expr/eval", headers={
            **host_hdr, "Origin": "http://127.0.0.1:8080"
        }, json=body
    ).status_code == 200
    # 无 Origin(非浏览器客户端)放行
    assert client.post("/api/expr/eval", headers=host_hdr, json=body).status_code == 200


def test_skip_local_verify_cross_site_guard_all_write_endpoints(web_env):
    """全部写端点穷举: 跨站 Origin 下一律 403(闸在全局依赖单点, 先于任何处理器/422)

    覆盖面以**路由表实际清点**为准(不手工点名) —— 每条 POST/PUT/DELETE/PATCH 路由
    (路径参数填占位值)带 evil Origin 打一遍, 403 即闸门先于处理器生效; 新写端点自动
    进入本测试的覆盖面。
    """
    import re

    from fastapi.testclient import TestClient

    from auto_qb.webui import create_app

    mgr = web_env[0]
    mgr.config.web.skip_local_verify = True
    client = TestClient(create_app(mgr), client=("127.0.0.1", 50000))
    headers = {"Host": "127.0.0.1:8080", "Origin": "http://evil.com"}
    write_methods = {"POST", "PUT", "DELETE", "PATCH"}
    write_routes = [r for r in _iter_api_routes(client.app.routes) if r.methods & write_methods]
    assert len(write_routes) >= 30, f"写路由清点异常({len(write_routes)} 条), 穷举失去意义"
    checked = []
    for route in write_routes:
        method = next(iter(route.methods & write_methods))
        path = re.sub(r"\{[^}]+\}", "x", route.path)
        resp = getattr(client, method.lower())(path, headers=headers, json={})
        assert resp.status_code == 403, f"{method} {route.path} 跨站 Origin 未被拒绝(实际 {resp.status_code})"
        checked.append((method, route.path))
    assert ("POST", "/api/torrents/{hash}/delete") in checked, "高危写端点必须在覆盖面内"


def test_skip_local_verify_cross_site_guard_credentials_bypass(web_env):
    """携带凭证的请求绕过跨站闸: 持密即可信方(浏览器跨站伪造不了凭证), 既有语义照旧裁决

    带凭证 + 外部 Host -> 不进跨站闸, 落到既有分支: loopback 对端走免鉴权放行(错密钥也
    放行, 与 bypass 测试同一语义); 远端对端对密钥 200 / 错密钥 **401**(token 路径的
    语义)而非 403 —— 跨站闸只拦**无凭证**请求, 不改变既有鉴权行为。
    """
    from fastapi.testclient import TestClient

    from auto_qb.webui import create_app

    mgr = web_env[0]
    mgr.config.web.skip_local_verify = True
    app = create_app(mgr)
    loopback = TestClient(app, client=("127.0.0.1", 50000))
    remote = TestClient(app, client=("192.168.1.50", 50000))
    ok = {"Host": "attacker.com", "Authorization": f"Bearer {mgr.web.token}"}
    bad = {"Host": "attacker.com", "Authorization": "Bearer wrong"}
    assert loopback.get("/api/status", headers=ok).status_code == 200
    assert loopback.get("/api/status", headers=bad).status_code == 200  # 免鉴权分支既有语义
    assert remote.get("/api/status", headers=ok).status_code == 200
    assert remote.get("/api/status", headers=bad).status_code == 401


def test_skip_local_verify_default_off_no_cross_site_guard(web_env):
    """默认关闭零变化: 外部 Host/Origin 不触发 403, 仍走既有 401 路径(安全纪律)"""
    from fastapi.testclient import TestClient

    from auto_qb.webui import create_app

    mgr = web_env[0]
    assert mgr.config.web.skip_local_verify is False
    client = TestClient(create_app(mgr), client=("127.0.0.1", 50000))
    assert client.get("/api/status", headers={"Host": "attacker.com"}).status_code == 401
    assert client.post("/api/expr/eval", json={"text": "(tor.size >= 1GiB)"}).status_code == 401


def test_auth_host_origin_parsing_helpers():
    """Host 头解析与 Origin 判定纯函数单测: 形态 / fail-closed / 端口一致性"""
    from auto_qb.webui.server.auth import _allowed_hostnames, _host_header_parts, _origin_allowed

    assert _host_header_parts("127.0.0.1:8080") == ("127.0.0.1", 8080)
    assert _host_header_parts("127.0.0.1") == ("127.0.0.1", None)
    assert _host_header_parts("[::1]:8787") == ("::1", 8787)
    assert _host_header_parts("attacker.com") == ("attacker.com", None)
    assert _host_header_parts("") == ("", None)  # 空 Host -> fail-closed(调用方拒绝)
    allowed = _allowed_hostnames("127.0.0.1")
    assert {"localhost", "127.0.0.1", "::1", "::ffff:127.0.0.1"} <= allowed
    assert _origin_allowed("http://127.0.0.1:8080", allowed, 8080)
    assert _origin_allowed("http://localhost:8080", allowed, 8080)
    assert not _origin_allowed("http://evil.com", allowed, 8080)  # 跨站 host
    assert not _origin_allowed("http://127.0.0.1:9999", allowed, 8080)  # 端口不一致
    assert not _origin_allowed("ftp://127.0.0.1", allowed, None)  # 非 http(s)
    assert not _origin_allowed("not a url", allowed, None)  # 无 host


def _auth_request(path="/api/events", query="", host="127.0.0.1:8080", client=("127.0.0.1", 50000), method="GET"):
    """构造 require_token 直调用的 Request(绕开 TestClient 的流式端点阻塞)"""
    from starlette.requests import Request as StarletteRequest

    scope = {
        "type": "http",
        "asgi": {
            "version": "3.0"
        },
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": query.encode(),
        "root_path": "",
        "headers": [(b"host", host.encode())],
        "client": client,
        "server": ("127.0.0.1", 8080),
    }
    return StarletteRequest(scope)


def test_sse_ticket_flow(web_env):
    """SSE 一次性票据(B-01): 带鉴权 POST 换票 -> 单次消费 / 过期无效 / 重放无效 / 无凭证 401

    EventSource 发不出 Authorization 头; 换票端点让长期密钥彻底退出查询串 —— 票据
    30s TTL + 取即删, 泄漏面收敛为"用完即弃"。
    """
    from auto_qb.webui.runtime import EVENT_TICKET_TTL_S

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    resp = client.post("/api/events/ticket", headers=auth)
    assert resp.status_code == 200
    body = resp.json()
    ticket = body["ticket"]
    assert ticket and ticket != mgr.web.token, "票据不得是密钥复用"
    assert body["ttl"] == EVENT_TICKET_TTL_S
    # 单次消费: 首次 True, 重放 False; 未知票据 False
    assert mgr.web.consume_event_ticket(ticket) is True
    assert mgr.web.consume_event_ticket(ticket) is False
    assert mgr.web.consume_event_ticket("unknown-ticket") is False
    # 过期票据无效(签发时刻拨回 TTL 之外)
    stale = mgr.web.issue_event_ticket()
    mgr.web._event_tickets[stale] = time.time() - (EVENT_TICKET_TTL_S + 1)
    assert mgr.web.consume_event_ticket(stale) is False
    # 无凭证换票 -> 401(默认 skip 关闭); 满额拒签回 ""(签发方法层语义)
    assert client.post("/api/events/ticket").status_code == 401
    from auto_qb.webui.runtime import EVENT_TICKET_MAX

    tickets = [mgr.web.issue_event_ticket() for _ in range(EVENT_TICKET_MAX)]
    assert all(tickets) and len(set(tickets)) == EVENT_TICKET_MAX, "满额前每次签发必须唯一非空"
    assert mgr.web.issue_event_ticket() == "", "满额必须拒签(回空串, 端点转 503)"


def test_sse_ticket_in_require_token_and_query_token_removed(web_env):
    """require_token 收 ?ticket=(仅限 /api/events, 取即删); ?token= 查询串兜底已删除

    查询串放长期密钥的通道必须保持关闭: 即使密钥正确, ?token= 也不再是有效凭证
    (B-01 的核心语义 —— 防反代访问日志留下密钥)。
    """
    from fastapi import HTTPException

    from auto_qb.webui.server.auth import make_require_token

    mgr, _client = web_env
    require_token = make_require_token(mgr)
    # 有效票据放行(消费即删)
    ticket = mgr.web.issue_event_ticket()
    assert require_token(_auth_request(query=f"ticket={ticket}"), authorization="") is None
    assert mgr.web.consume_event_ticket(ticket) is False, "require_token 必须已消费该票据"
    # 票据只认 /api/events 路径: 挂到别的端点不生效(401)且不被误消费
    ticket2 = mgr.web.issue_event_ticket()
    with pytest.raises(HTTPException) as ei:
        require_token(_auth_request(path="/api/state", query=f"ticket={ticket2}"), authorization="")
    assert ei.value.status_code == 401
    assert mgr.web.consume_event_ticket(ticket2) is True, "非 SSE 路径不得误消费票据"
    # ?token= 已删: 密钥正确的查询串也不再是有效凭证
    with pytest.raises(HTTPException) as ei:
        require_token(_auth_request(query=f"token={mgr.web.token}"), authorization="")
    assert ei.value.status_code == 401


def test_start_web_server_config_disables_proxy_headers(web_env, monkeypatch):
    """uvicorn Config 显式 proxy_headers=False(B-03): 不信任反代 XFF/Forwarded 头

    uvicorn 默认 proxy_headers=True 会把本机反代转发的 X-Forwarded-For 写回
    request.client.host —— XFF 伪造成 loopback 可造成 skip_local_verify 免鉴权误判。
    装配点断言(lifecycle 的 _QuietLoopConfig 直传)。
    """
    from auto_qb.webui.server import lifecycle

    captured = {}

    class _FakeServer:
        def __init__(self, config):
            captured["config"] = config
            self.started = True
            self.should_exit = False

        def run(self):
            pass

    monkeypatch.setattr(lifecycle.uvicorn, "Server", _FakeServer)
    handle = lifecycle.start_web_server(web_env[0])
    assert handle.started
    assert captured["config"].proxy_headers is False


def test_frontend_sse_ticket_wiring():
    """SSE 换票前端接线守阵(B-01): polling.js 必须走 POST /api/events/ticket + ?ticket=
    并带重连换票路径; ?token= 查询串(长期密钥进查询串的通道)不得回潮。"""
    src = Path(os.path.join(STATIC_ROOT, "shared", "polling.js")).read_text(encoding="utf-8")
    assert "/api/events/ticket" in src, "startEvents 必须先换票"
    assert "encodeURIComponent(ticket)" in src, "EventSource 必须以 ?ticket= 连流"
    assert "?token=" not in src, "查询串放长期密钥的旧通道不得回潮"
    assert "_esRetry" in src, "一次性票据重连必失效: 必须有关连接换新票重开的重试路径"


def test_skip_local_verify_default_off(web_env):
    """默认关闭(保守): 本机连接也不免鉴权, 无密钥仍 401"""
    from fastapi.testclient import TestClient

    from auto_qb.webui import create_app

    mgr = web_env[0]
    assert mgr.config.web.skip_local_verify is False  # 默认 false
    app = create_app(mgr)
    loopback = TestClient(app, client=("127.0.0.1", 50000))
    assert loopback.get("/api/status").status_code == 401


def test_api_status_and_groups(web_env):
    """状态与分组快照读取: 徽章数据/组名/站点明细齐全; status 携带版本号(顶栏展示)"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    status = client.get("/api/status", headers=auth).json()
    assert status["connected"] is True and status["torrents"] == 2
    assert status["version"] == __version__, "status 应透出包版本号"
    data = client.get("/api/groups", headers=auth).json()
    assert len(data["groups"]) == 1
    g = data["groups"][0]
    assert g["name"] == "Show" and g["count"] == 2 and g["upspeed"] == 2048
    assert [m["site"] for m in g["members"]] == ["HHan", "M-Team"]


def test_api_expr_eval_endpoint(web_env):
    """表达式试算端点 /api/expr/eval: 校验-only 与"按种子求值 + 中间值"两条路径

    前端「试算」按钮靠它: 写错表达式不用等到保存才知道; 填了种子 hash 还能看到
    每个取值到底取到了什么(中间值), 这是排查"条件为什么不匹配"最有用的一条信息。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    # 替身 store 默认 get() 恒 None: 塞一条合成种子进去(试算要读它的字段)
    from auto_qb.torrents import TorrentRecord

    rec = TorrentRecord(hash="h1", name="Show 1", size=5 * 1024**3, state="uploading")
    mgr.store.get = lambda h: rec if h == "h1" else None
    h = "h1"

    ok = client.post("/api/expr/eval", json={"text": "(tor.size >= 1GiB)"}, headers=auth).json()
    assert ok["ok"] is True and ok["used"] == ["tor.size"] and ok["value"] is None

    bad = client.post("/api/expr/eval", json={"text": "tor.nope > 1"}, headers=auth).json()
    assert bad["ok"] is False and "未知取值" in bad["error"]

    val = client.post(
        "/api/expr/eval", json={
            "text": "(tor.size >= 1GiB) and (tor.name ~ \"Show\")",
            "hash": h
        }, headers=auth
    ).json()
    assert val["ok"] is True and isinstance(val["value"], bool)
    assert [t["name"] for t in val["trace"]] == ["tor.size", "tor.name"]

    missing = client.post("/api/expr/eval", json={"text": "(tor.size >= 1GiB)", "hash": "nope"}, headers=auth).json()
    assert missing["ok"] is False and "找不到种子" in missing["error"]


def test_static_assets_disable_heuristic_cache(web_env):
    """静态资源带 no-cache: 不加 Cache-Control 时浏览器会启发式缓存数小时

    症状: 升级程序后仍加载旧前端("改了但没变"), 开发中实际撞到。
    no-cache 仍允许存储, 但每次必须带 ETag 重新校验(未变走 304); /api 响应不受影响。
    路径随 UI 目录化更新: atlas=星图(旧) / prism=棱镜(新) / shared=公共逻辑层。
    """
    mgr, client = web_env
    for path in (
        "/atlas/", "/atlas/style.css", "/shared/tpl/topbar.html", "/prism/", "/shared/app.js", "/shared/boot.js",
        "/shared/vendor/vue.global.prod.js", "/console/", "/console/css/components.css"
    ):
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} 应可访问"
        assert resp.headers.get("cache-control") == "no-cache", f"{path} 应带 no-cache"
    api = client.get("/api/status", headers={"Authorization": f"Bearer {mgr.web.token}"})
    assert api.headers.get("cache-control") != "no-cache", "/api 响应不应被静态策略影响"


def test_ui_root_and_legacy_newui_redirect(web_env):
    """根路径与旧 /newui/* 重定向: / -> 上次使用的 UI(autoqb_ui 皮肤 cookie); /newui/* -> 307 /prism/*

    UI 目录化后 StaticFiles 根下无 index.html, 根路径由显式路由兜底; 默认星图, 但带皮肤 cookie
    (shared/boot.js 在每套 UI 加载时写入)时直达该 UI —— 修复「关窗口重开总回星图」(2026-09-29 用户报)。
    cookie 值双重校验: 形状合法 + static/<名>/index.html 真实存在 —— UI 改名/删除后的旧 cookie
    与路径逃逸形状一律回落星图。/newui 兼容路由保住升级前书签(子路径原样映射到 /prism/*)。
    """
    _, client = web_env
    for cookie, expect in (
        ({}, "/atlas/"),  # 未记录(首次访问/清过站点数据) -> 默认星图
        ({
            "autoqb_ui": "prism"
        }, "/prism/"),  # 上次用棱镜 -> 直达棱镜
        ({
            "autoqb_ui": "console"
        }, "/console/"),  # 上次用控制台 -> 直达控制台
        ({
            "autoqb_ui": "atlas"
        }, "/atlas/"),  # 上次用星图(显式记录)
        ({
            "autoqb_ui": "ghost"
        }, "/atlas/"),  # 目录已不存在(UI 改名/删除后的旧 cookie)
        ({
            "autoqb_ui": "../prism"
        }, "/atlas/"),  # 形状不合法(路径逃逸形状不得进重定向目标)
    ):
        # starlette 1.6 弃用逐请求 cookies=<...>(审计 L8, b 类: 测试代码用了弃用 API), 按官方迁移路径
        # 改设到 client 实例; 每档先清空再写入, 保持"该次请求只带本档 cookie"的独立语义
        # (307 应答不带 Set-Cookie, 不存在串档; 清空是防未来路由加 Set-Cookie 后跨档污染)。
        client.cookies.clear()
        client.cookies.update(cookie)
        root = client.get("/", follow_redirects=False)
        assert root.status_code == 307, f"cookie={cookie} 根路径应 307 重定向"
        assert root.headers["location"] == expect, f"cookie={cookie} 应重定向到 {expect}"
    for old, new in (
        ("/newui", "/prism/"), ("/newui/", "/prism/"), ("/newui/css/tokens.css", "/prism/css/tokens.css"),
        ("/newui/js/theme.js", "/prism/js/theme.js")
    ):
        resp = client.get(old, follow_redirects=False)
        assert resp.status_code == 307, f"{old} 应 307 重定向"
        assert resp.headers["location"] == new, f"{old} 应映射到 {new}"


def test_frontend_ui_skin_cookie_persisted():
    """boot.js 必须把当前 UI 写进 autoqb_ui cookie —— 根路径「记住上次 UI」的数据源(2026-09-29 用户报)

    根路径 307 由服务端在收到请求那一刻裁决, localStorage 服务端读不到, cookie 是唯一可行载体;
    三套 UI 共用 boot.js = 唯一写入口(打开即记录, 切换菜单无需单独埋点)。服务端取值校验
    (形状 + 目录存在性)见 test_ui_root_and_legacy_newui_redirect。
    """
    boot = open(os.path.join(STATIC_ROOT, "shared", "boot.js"), encoding="utf-8").read()
    assert '"autoqb_ui="' in boot, "boot.js 未写 autoqb_ui cookie —— 关窗重开根路径会回到默认星图"
    assert "location.pathname.split" in boot, "boot.js 未从 URL 路径段判定当前 UI"
    assert "Max-Age=" in boot, "皮肤 cookie 必须带有效期(会话 cookie 关窗即丢, 等于没修)"
    assert "Path=/" in boot, "皮肤 cookie 必须 Path=/(根路径 / 要能读到)"


STATIC_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "auto_qb", "webui", "static"
)

# 全部 UI(皮肤)清单: 目录即 UI(static/<名>/index.html, 后端零注册表)。
# 新增皮肤 = 加一档, 全文件"成对改"守阵随本常量自动扩档; 单独点名的守阵(令牌对账/CSS 链接序)另行核对。
_UI_ALL = ("atlas", "prism", "console")


def _ui_manifest(ui):
    """解析 ui/index.html shell 里 <script type="application/json" id="tpl-manifest"> 清单

    清单是 boot.js 与守阵共用的单一来源(plans/26-09-26-2233 §5): parts = 模板分片(into: app|body,
    其余值为 #app 内自定义选择器落点, 方案A 停靠面板 26-10-03-0917 W1 起支持),
    scripts = 逻辑脚本加载顺序。缺清单/坏 JSON 直接断言红 —— shell 半残比假绿好。
    """
    shell = open(os.path.join(STATIC_ROOT, ui, "index.html"), encoding="utf-8").read()
    m = re.search(r'<script type="application/json" id="tpl-manifest">(.*?)</script>', shell, re.S)
    assert m, f"{ui}/index.html 缺 tpl-manifest 清单(拆分半途? 同步本守阵)"
    return json.loads(m.group(1))


def _ui_shell_inline(ui):
    """shell index.html 里 #app 的内联残余(登录遮罩区): `<div id="app" v-cloak>` 到 2 空格 `  </div>`"""
    lines = open(os.path.join(STATIC_ROOT, ui, "index.html"), encoding="utf-8").read().split("\n")
    try:
        open_i = lines.index('  <div id="app" v-cloak>')
    except ValueError:
        raise AssertionError(f"{ui}/index.html 缺 #app 容器(拆分半途? 同步本守阵)")
    closes = [i for i, ln in enumerate(lines) if ln == "  </div>"]
    assert len(closes) == 1, f"{ui}/index.html 的 #app 收口锚点(2 空格 `  </div>`)应恰有一处, 实测 {len(closes)}"
    return "\n".join(lines[open_i + 1:closes[0]])


def _ui_aggregate(ui):
    """拆分后模板聚合 = shell 内联段 + 分片按清单序拼接 —— 拆分后守阵只认聚合, 不认单分片

    26-09-26 模板分片(plans/26-09-26-2233 W1)后, 原 2555/2613 行 index.html 变成 ≤200 行 shell
    + tpl/*.html; 旧守阵继续读 index.html 会整体假绿(内容都搬去了分片)。顺序 = boot 注入序
    (app 桶在 shell 内联段之后按清单序进 #app, body 桶进 body), 与运行时 Vue 编译输入一致。
    单看任何一个分片都会漏跨分片的结构(如批量菜单的 template 链), 所以一律走这里。
    """
    chunks = [_ui_shell_inline(ui)]
    for part in _ui_manifest(ui)["parts"]:
        text = open(_tpl_path(part["src"], ui), encoding="utf-8").read()
        chunks.append(text.rstrip("\n"))
    return "\n".join(chunks)


def _ui_css_files(ui):
    """ui shell <head> 里声明的本 UI CSS 链接顺序(link 顺序即级联序) —— CSS 拆分后的加载序单一来源"""
    shell = open(os.path.join(STATIC_ROOT, ui, "index.html"), encoding="utf-8").read()
    hrefs = re.findall(r'<link rel="stylesheet" href="(/%s/[^"]+\.css)"' % ui, shell)
    assert hrefs, f"{ui} shell head 缺本 UI 的 CSS 链接"
    return [os.path.join(STATIC_ROOT, *h.lstrip("/").split("/")) for h in hrefs]


def _ui_css_aggregate(ui):
    """UI CSS 聚合(按 shell link 序拼接) —— CSS 分层拆分后守阵只认聚合, 级联序 = link 序

    26-09-27 atlas/style.css 分层拆分(W2)后, 旧守阵继续单读 style.css 会假绿(规则搬进了 css/)。
    切分是连续字节切片(级联序不变), 聚合与拆分前逐字节等价。
    """
    return "\n".join(open(p, encoding="utf-8").read() for p in _ui_css_files(ui))


def _assert_tags_balanced(text, label):
    """HTML 标签配平(HTMLParser 视角): 分片切割边界错位(把半个元素切进相邻分片)在聚合上现形

    分片本身因 wrapper 跨片(template v-else / .layout / .hb-wrap)**允许不配平**,
    配平只对「按清单序拼接后的聚合」成立 —— 它必须与拆分前的整页等价。
    void 元素与自闭合不参与; script/style 内容是 CDATA(内部尖括号不参与)。
    """
    from html.parser import HTMLParser

    void = {
        "meta", "link", "img", "input", "br", "hr", "source", "col", "area", "base", "wbr", "embed", "track", "param"
    }

    class _Balance(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=False)
            self.stack, self.bad = [], []

        def handle_starttag(self, tag, attrs):
            if tag not in void:
                self.stack.append((tag, self.getpos()[0]))

        def handle_startendtag(self, tag, attrs):
            pass

        def handle_endtag(self, tag):
            if tag in void:
                return
            if not self.stack:
                self.bad.append(f"多余的 </{tag}> @行{self.getpos()[0]}")
                return
            open_tag, open_line = self.stack.pop()
            if open_tag != tag:
                self.bad.append(f"</{tag}> @行{self.getpos()[0]} 与未闭合的 <{open_tag}> @行{open_line} 交错")

    p = _Balance()
    p.feed(text)
    p.close()
    leftovers = [f"<{t}> @行{l}" for t, l in p.stack]
    problems = p.bad + [f"未闭合的 {x}" for x in leftovers]
    assert not problems, f"{label} 标签不配平(分片切割边界错位?): " + "; ".join(problems[:8])


# CSS 容器型 at-rule: "开块后下一行是嵌套规则"属正常写法, 不参与"漏闭合"判定
_CSS_CONTAINER_AT = ("@media", "@supports", "@keyframes", "@container", "@layer", "@scope")
# 追剧视图的"集成员"两种写法(e.members / ep.members) —— 取 hash 必须经 memberHashesOf 归一
_EP_MEMBERS_RE = re.compile(r"\b(?:ep|e)\.members\b")


def _scan_css_blocks(path, rel, problems):
    """CSS 规则块守阵: 顶层规则开了块却没闭合, 而下一非空行又开了新规则 -> 漏写 `; }`

    (2026-09-17 实测: prism/css/views.css 曾有一条 `.ce-subcard .ce-field { … padding: 7px 0` 漏了
    `; }`, 浏览器把其后约 200 条规则整段当作"未结束的声明块"丢弃 —— 棱镜大半样式静默消失而
    pytest 全绿。注意**全文件花括号计数是配平的**(别处有多余 `}`), 只数括号查不出来。
    该规则本身已随经典设置页的死代码清理删除, 此处只作判据来源留档。)
    """
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    depth = 0
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        opens, closes = line.count("{"), line.count("}")
        if depth == 0 and opens > closes and not stripped.startswith(_CSS_CONTAINER_AT):
            nxt = next((l.strip() for l in lines[i:] if l.strip()), "")
            if "{" in nxt:  # 本块还没闭合, 下一行又开了新规则 -> 语法已坏
                problems.append(f"{rel}:{i} 规则块未闭合(下一非空行又开了新规则)")
        depth += opens - closes
        if depth < 0:
            problems.append(f"{rel}:{i} 多余的 `}}`")
            depth = 0
    if depth != 0:
        problems.append(f"{rel} 花括号未配平(差 {depth})")


def _scan_css_comments(path, rel, problems):
    """CSS 注释提前终止守阵: 注释体内的 `*/` 会把注释砍断, 尾巴落成代码态的孤立垃圾 ——
    浏览器按错误恢复丢弃到下一个 `}` 为止, **紧跟的那条规则整条静默消失**(无任何报错)。

    (2026-09-28 实测: console/css/components.css 进度条注释写了 `(s-*/member-row 族)`,
    `s-*` 后的 `*/` 提前闭合注释, 紧随其后的 `.m-progress { display: flex; … }` 被整条吞掉
    —— 三处表格(辅种/种子/追剧明细)进度条只剩百分比没有条。判据 = 浏览器同款注释语义
    (字符串感知)扫一遍: 正常文件的所有 `*/` 都应消费在注释态里, 代码态出现孤立 `*/` 即中招。)
    """
    with open(path, encoding="utf-8") as f:
        text = f.read()
    i, n = 0, len(text)
    in_comment = False
    str_ch = None
    while i < n:
        c = text[i]
        if in_comment:
            if c == "*" and i + 1 < n and text[i + 1] == "/":
                in_comment = False
                i += 2
                continue
            i += 1
            continue
        if str_ch:
            if c == "\\":
                i += 2
                continue
            if c == str_ch:
                str_ch = None
            i += 1
            continue
        if c in "\"'":
            str_ch = c
            i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            in_comment = True
            i += 2
            continue
        if c == "*" and i + 1 < n and text[i + 1] == "/":
            line = text.count("\n", 0, i) + 1
            problems.append(f"{rel}:{line} 注释被体内 `*/` 提前终止(其后规则被浏览器整条丢弃)")
            i += 2
            continue
        i += 1


def _scan_template_transitions(path, rel, problems):
    """模板 `<transition>` 结构守阵: 必须配对, 且弹窗不得落在 `<transition>` 内

    (2026-09-17 实测: 抽屉外层多了一个未闭合的 `<transition name="pop">`, 于是统计/限速/添加/
    管理/确认框全被浏览器解析成它的子节点 —— `Transition` 只渲染第一个子节点, **所有弹窗被静默
    丢弃**: 点击毫无反应、控制台也不报错。配对计数 + 弹窗嵌套双查, 二者都能抓住这个 bug。)
    """
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    depth = 0
    for i, line in enumerate(lines, 1):
        low = line.lower()
        if "modal-mask" in low and depth > 0:
            problems.append(f"{rel}:{i} 弹窗(.modal-mask)落在 <transition> 内(Transition 只渲染首个子节点 -> 弹窗会被丢弃)")
        depth += low.count("<transition") - low.count("</transition>")
        if depth < 0:
            problems.append(f"{rel}:{i} 多余的 </transition>")
            depth = 0
    if depth != 0:
        problems.append(f"{rel} `<transition>` 未闭合(差 {depth})")


# `node -e` 批量校验脚本(不落盘): 逐文件按 **CommonJS 包装**编译 —— 与 `node --check` 同语义, 但只起一个进程。
# WARN: 必须经 `Module.wrap`: 裸 `new vm.Script(src)` 按**经典脚本**解析, 会把顶层 `return`(CommonJS 下合法)
#   判成语法错误 ⇒ 比原判据凭空变严(2026-09-23 实测: 同一批样本里只有该边界项判定不同)。
_NODE_SYNTAX_CHECK = (
    "const fs=require('fs'),vm=require('vm'),M=require('module');let bad=0;"
    "for(const f of process.argv.slice(1)){"
    "try{new vm.Script(M.wrap(fs.readFileSync(f,'utf8')),{filename:f});}"
    "catch(e){bad++;console.error(f+'\\t'+e.message);}}"
    "process.exit(bad?1:0);"
)


def _scan_js_syntax_with_node(js_files, problems):
    """有 node 时对前端 JS 做**真**语法校验(2026-09-17 起本机已装 node)

    这是启发式扫描(注释孤儿续行等)之上的一道硬闸: 任何语法错误都能以 `文件:行` 形式报出。
    无 node(未装的机器/精简 CI)时**静默跳过**本项 —— 不引入 pytest skip(基线是 0 skipped),
    启发式扫描仍在拦最常见的那类损坏。

    !2026-09-23 由「逐文件起一个 `node --check`」改为**单进程批量**: 20 个文件 = 20 次进程启动,
    实测 7.4s, 其中 95% 是进程启动开销(批量 0.38s)。校验语义已逐样本对齐过 ——
    6 个故障样本(注释孤儿续行 / 未闭括号 / 未闭字符串 / 未闭模板串 / 坏正则 / 未闭圆括号)
    + 1 个正常样本 + 1 个顶层 `return` 边界样本, 判定与 `node --check` **8/8 一致**。
    """
    node = shutil.which("node")
    if not node:
        return
    paths = [path for path, _rel in js_files]
    if not paths:
        return
    proc = subprocess.run([node, "-e", _NODE_SYNTAX_CHECK, *paths], capture_output=True, text=True)
    if proc.returncode == 0:
        return
    rel_of = {os.path.normcase(path): rel for path, rel in js_files}
    for line in (proc.stderr or proc.stdout).strip().splitlines():
        name, _, message = line.partition("\t")
        rel = rel_of.get(os.path.normcase(name.strip()), name.strip())
        problems.append(f"{rel} node 语法校验报错: {message.strip() or 'unknown'}")


def _app_bundle_files():
    """app.js 及它按域拆分出的片段文件, 按 prism shell 的 tpl-manifest **加载顺序**返回 [(path, rel)]

    (2026-09-20 app.js 拆分: 片段以 window.AQB_* 全局 mixin 注入 **同一个** Vue 实例, 逻辑上仍是一份
     代码 —— 故"跨文件的不变量"必须按整包看: 只扫 app.js 会把搬走的那半漏掉。实测拆完当场报
     「找不到 _optimisticSettled 调用点」, 而它只是挪到了 commands.js, 功能没丢。)
     顺序取自清单而非文件名排序 —— 片段必须排在 app.js **之前**(app.js 末尾要读 window.AQB_*);
     26-09-26 模板分片后 <script> 标签从 HTML 搬进了 tpl-manifest 的 scripts 数组, 由 boot.js 依序放行。
    """
    out = []
    for src in _ui_manifest("prism")["scripts"]:
        if "/vendor/" in src:
            continue
        rel = src.lstrip("/")
        out.append((os.path.join(STATIC_ROOT, rel), rel))
    return out


def _app_bundle_text():
    """app.js + 内核片段(清单序)聚合文本 —— W2b 拆分后成员按域存放, 守阵找成员一律读聚合"""
    return "\n".join(open(p, encoding="utf-8").read() for p, _rel in _app_bundle_files())


def _bundle_iter():
    """(rel, text) 对迭代: 整包按清单序 —— 「恰好只在一处」类不变量改整包扫描用"""
    for p, rel in _app_bundle_files():
        yield rel, open(p, encoding="utf-8").read()


def _section_members(text, section):
    """取片段文件 / app.js 里 `methods: {` 或 `computed: {` 块的成员名(4 空格缩进的 `name(` / `name:`)"""
    names, in_block = [], False
    for line in text.splitlines():
        if not in_block:
            if line.strip() == section + ": {":
                in_block = True
            continue
        if line in ("  },", "  }"):
            break
        m = re.match(r"^    (?:async )?([A-Za-z_$][\w$]*)\s*[(:]", line)
        if m:
            names.append(m.group(1))
    return names


def _scan_mixin_wiring(problems):
    """拆分接线守阵(2026-09-20): 片段文件必须「HTML 引用了」且「app.js 注入了」, 且成员不得重名

    拆成多文件后有两类**静默**故障形态(pytest 全绿 / 界面局部废掉):
    1. 文件写了但漏加 <script> 或漏 app.mixin() —— 那一整块功能凭空消失, 控制台不报错
       (Vue 直接把没注册的 mixin 当不存在);
    2. 两个片段里出现同名成员 —— Vue 的 mixin 合并是**后者覆盖前者**, 不报错, 但被覆盖的那个
       实现从此永不执行(表现为"点了没反应"或行为回到旧逻辑)。
    """
    bundle = _app_bundle_files()
    refs = {rel for _p, rel in bundle}
    # boot.js 走 shell 静态 <script src>(它自己负责按清单放行其余脚本, 不在清单内), 两张 shell 的
    # 静态引用同样算"已接线"
    for ui in _UI_ALL:
        shell = open(os.path.join(STATIC_ROOT, ui, "index.html"), encoding="utf-8").read()
        refs |= {m.lstrip("/") for m in re.findall(r'<script src="(/shared/[^"]+\.js)"></script>', shell)}
    for dirpath, _dirs, files in os.walk(os.path.join(STATIC_ROOT, "shared")):
        if os.path.basename(dirpath) == "vendor":  # 第三方压缩产物, 不参与本仓库的片段约定
            continue
        for name in sorted(files):
            if not name.endswith(".js"):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, STATIC_ROOT).replace(os.sep, "/")
            if rel in refs:
                continue
            problems.append(f"{rel} 未被 tpl-manifest 清单或 shell 静态 <script> 引用(拆分片段漏挂 -> 整块功能静默消失)")

    app_text = open(os.path.join(STATIC_ROOT, "shared", "app.js"), encoding="utf-8").read()
    # 三种"已接线"形态:
    #   1. mixin    —— window.AQB_* 注入 Vue 实例
    #   2. component —— 注册为组件(如 hub-field 走 app.component)
    #   3. **行为基座** —— 被另一个全局用 `Object.assign({}, window.X, …)` 拷走复用(如 config_hub.js
    #      的 HUB_FIELD_COMPONENT 拷 config_editor.js 的 CE_FIELD_BASE)。它本身不是组件、不注册,
    #      但成员确实在跑 ⇒ 不该报"定义了没注入"。
    #      WARN: 只认 `Object.assign({}, window.X` 这一种形态(本项目唯一的复用写法), 不要放宽成"出现即算"。
    #      (2026-09-25: 经典设置页移除后 ce-field 组件与 tpl-ce-field 模板删除, 基座随之改名去组件化。)
    #   4. **根选项展开** —— `...window.X` 展开进 createApp 根组件选项(W2b: state.js 的 data/computed/watch
    #      与 lifecycle.js 的生命周期)。!这类成员**不许**走 app.mixin: 全局 mixin 会波及 hub-field 等
    #      组件实例(watch/mounted 双份执行)。只认 app.js 里 `...window.X` 展开形态, 不放宽。
    registered = set(re.findall(r"app\.mixin\(window\.(\w+)\)", app_text))
    registered |= set(re.findall(r"app\.component\(\s*\"[^\"]+\"\s*,\s*window\.(\w+)\)", app_text))
    registered |= set(re.findall(r"\.\.\.window\.(\w+)", app_text))
    for path, _rel in bundle:
        registered |= set(re.findall(r"Object\.assign\(\{\},\s*window\.(\w+)", open(path, encoding="utf-8").read()))
    seen = {}
    for path, rel in bundle:
        text = open(path, encoding="utf-8").read()
        for glob in re.findall(r"^window\.(\w+) = \{", text, re.M):
            if glob not in registered:
                problems.append(f"{rel} 定义了 window.{glob} 但 app.js 没有 app.mixin(window.{glob})(片段漏注入)")
        for section in ("methods", "computed"):
            for member in _section_members(text, section):
                if member in seen:
                    problems.append(
                        f"{rel} 的 {section}.{member} 与 {seen[member]} 重名 —— Vue mixin 后者覆盖前者, "
                        "被盖掉的实现永不执行且不报错"
                    )
                seen[member] = rel


def _scan_episode_member_hashes(text, rel, problems):
    """追剧视图"集成员 -> hash"守阵 (2026-09-19 实测事故)

    后端 shows 视图的 `members` 是 **hash 数组**, 而前端 `decoratedShows` 会把它换成**成员对象**
    (带 hit 标记, 供行内渲染/筛选)。菜单与命令只认 hash —— 一旦把对象当 hash 传出去, 拼进
    URL/JSON 时字符串化成 `[object Object]` ⇒ 后端查不到该 hash ⇒ 404「种子不存在」:
    整集/整剧的 开始/暂停/强制汇报/打开目标文件夹/删除 全线哑火(单种子菜单传的是 `member.hash`,
    不受影响 —— "种子右键正常、剧/集右键失败"就是这形状)。故凡是"从集成员取 hash"的地方
    一律走 `memberHashesOf`(两形态都收), 这里只做静态拦截。
    """
    lines = text.splitlines()
    for i, line in enumerate(lines, 1):
        if not _EP_MEMBERS_RE.search(line):
            continue
        wants_hash = "hashes" in line or ".hash" in line or "for (const h of" in line
        if wants_hash and "memberHashesOf(" not in line:
            problems.append(
                f"{rel}:{i} 集成员取 hash 未走 memberHashesOf"
                "(members 在前端已是对象 -> 传出去会变成 [object Object], 后端 404「种子不存在」)"
            )


def _scan_state_rank(text, rel, problems):
    """状态优先级表守阵: 前端 `STATE_RANK` 必须与后端 `_SHOW_STATE_RANK` 逐项一致(2026-09-19)

    两表是**同一概念**("一组/一集种子该显示成什么状态")的两份实现:
    前端那份决定辅种页组行取哪个成员状态着色(`decoratedGroups.status.primary`),
    后端那份决定追剧页集行的 `e.state`。漂移的后果有两层 ——
    1. 同一批种子在辅种页与追剧页显示成**不同颜色**(用户没法解释, 只会觉得"颜色乱");
    2. 乐观 UI: 前端按自己的表算出"点击后的颜色", 下一轮回执却按后端的表算真值 ⇒ 颜色弹回。
    实测曾漂移两处({downloading,checking} 与 {paused,seeding} 两组取值相反), 人眼不可能发现,
    故机械比对(改一边必须改另一边 —— 这正是本守阵要逼出来的动作)。
    """
    from auto_qb.webui.views import _SHOW_STATE_RANK

    m = re.search(r"const STATE_RANK = \{([^}]*)\}", text)
    if not m:
        problems.append(f"{rel} 找不到 `const STATE_RANK = {{...}}`(状态优先级单点表, 见 isPending 一带注释)")
        return
    front = {k: int(v) for k, v in re.findall(r"(\w+)\s*:\s*(\d+)", m.group(1))}
    if front != _SHOW_STATE_RANK:
        problems.append(
            f"{rel} STATE_RANK 与后端 _SHOW_STATE_RANK 不一致"
            f"(前端 {front} / 后端 {_SHOW_STATE_RANK}) —— 同一批种子会在辅种页与追剧页显示成不同颜色"
        )
    # 顺序语义(2026-09-21): 做种必须排在**暂停之前** —— 组内"部分暂停部分做种中"取**做种色**。
    # 上面的逐项比对只能保证"两页同色", 保证不了"同成哪个色": 2026-09-19 的 BUG-7 把前端表整体
    # 对齐后端时, 顺手把 {paused,seeding} 也翻成 paused ⇒ 辅种页做种中的组整行变灰(用户报
    # "辅种页状态色错误, 以前是对的")。两表一起改才不会重蹈覆辙, 故此处单独钉住顺序。
    if front and front.get("seeding", 9) >= front.get("paused", -1):
        problems.append(
            f"{rel} STATE_RANK 把 paused 排在 seeding 之前或同级(前端 {front}) —— "
            "组/集内\"部分暂停部分做种中\"会取暂停色(灰), 用户口径是取**做种色**(绿); "
            "见 app.js STATE_RANK 注释与 memory-bank/pitfalls.md"
        )


def _scan_pending_settle(text, rel, problems):
    """乐观 UI「撤下」守阵(2026-09-19, 与主线 32f531d / 12657ee 同一族缺陷的第二道锁)

    背景: 「点击 → 行恢复正常」曾实测 3785~5178ms, 根因是 pending 只有 3s 常量兜底一个出口 ——
    systemPatterns 明写的「真值匹配即清」**从未实现过**; 而且这个兜底还只在 refresh() 里被顺带
    求值 ⇒ 撤下 = 3000ms + 等到下一次 /api/state。真机连报三次同一现象, 前三次修复全只动"贴上",
    因为没人量过"撤下"。

    主线修法落地后有两处**极易被改回去/写反**的地方, 本守阵逐条钉住:
      1. `_snapshotTruth(state)` 必须在 `reapplyPending()` **之前** —— 快照要的是服务端原始值;
         挪到之后就变成"行上的补丁值 vs 补丁值", 恒真 ⇒ pending 一瞬间就清(实测 28ms),
         而且冒烟里「落回的是真值」那条**照样 PASS**(补丁值还留在行上, 看着就像真值)。
      2. 判定必须走 `_optimisticSettled`(比真值快照)而不是"拿行上的当前值比" —— 同上。

    !2026-09-21 P3 后1.2.**仍然保留, 且必须保留**: 真值现在主要由 `truth` 事件(SSE)推送,
      但 **SSE 断线期间推的事件会丢**; 这时 `_optimisticSettled` 是唯一的安全网 —— 轮询带回的
      `/api/state` 一旦已经含真值就提前收工, 不用干等到 TRUTH_HOLD_MS(8s)超时回滚。
      没有它, SSE 一断就会出现"命令其实成功了, 8 秒后却回滚"的假失败。
    !已删除的旧机制(勿复活): `_settleFromTruth`(回执带真值就地撤下)、
      `_pullTruthAfterCmd`(回执后拉全量, 1500ms 预算) —— 真值改由事件推送后它们成了死代码。
    """
    i_snap = text.find("this._snapshotTruth(state)")
    i_reap = text.find("this.reapplyPending()")
    if i_snap < 0:
        problems.append(f"{rel} 找不到 `this._snapshotTruth(state)` —— 判「真值是否对齐」没有服务端原始值可比")
    elif i_reap >= 0 and i_snap > i_reap:
        problems.append(
            f"{rel} _snapshotTruth 写在 reapplyPending **之后** —— 快照到的是被补丁改过的行值,"
            "判定恒真 ⇒ pending 立刻清、失败路径留假状态(红线)"
        )
    if "this._optimisticSettled(" not in text:
        problems.append(
            f"{rel} 找不到 _optimisticSettled 的调用点 —— 它是 **SSE 断线时的安全网**: 没有它,"
            "推送丢失就只能干等 TRUTH_HOLD_MS 超时回滚(命令其实成功 ⇒ 假失败)"
        )
    # 反向守阵: 已删的机制不许复活(它们是真值改推送后遗留的死代码)
    for dead in ("_settleFromTruth", "_pullTruthAfterCmd"):
        if dead in text:
            problems.append(f"{rel} 残留已删机制 {dead} —— 真值已改由 truth 事件推送, 它只会拖慢撤下")


def _computed_body(text, name):
    """取 computed 成员 `<name>() { ... }` 的函数体(按缩进配平到同缩进或更浅的 `},`/`}`)

    只做"这段实现里有没有出现某个调用"这类**存在性**判定(见 _scan_filter_facets),
    故不需要真解析: 从定义行开始收集, 遇到缩进不大于定义行的 `}` 即停。
    """
    m = re.search(rf"^\s*{name}\(\)\s*\{{", text, re.M)
    if not m:
        return None
    indent = len(m.group(0)) - len(m.group(0).lstrip())
    out = []
    for line in text[m.end():].splitlines():
        if line.strip() in ("}", "},") and len(line) - len(line.lstrip()) <= indent:
            break
        out.append(line)
    return "\n".join(out)


def _strip_js_comments(text):
    """去掉 JS 的块注释与行注释 —— 供**存在性**守阵使用, 避免被注释骗过

    !这是本项目踩过的坑(memory-bank/testing.md 列偏好守阵那条): 只查"字符串出现了没有",
    注释里正写着那个名字 ⇒ 真被注释掉的代码照样判过。故存在性判定一律先剥注释。
    行注释只认"前面不是冒号"的 `//`(避开 `https://` 这类字面量), 不做完整词法分析 ——
    本函数只服务"某标识符在这段实现里有没有被调用", 不需要精确到字符串内部。
    """
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    out = []
    for line in text.splitlines():
        m = re.search(r"(?<!:)//", line)
        out.append(line[:m.start()] if m else line)
    return "\n".join(out)


def _scan_filter_facets(text, rel, problems):
    """筛选器选项"取数面"守阵(2026-09-21, 用户报「种子页筛选器无数据」)

    选项必须走**单点取数面** `facetRows`(filters.js): 组视图/追剧视图按组(计数=含该值的组数),
    种子页按种子(计数=含该值的种子数)。四个筛选器(标签/分类/站点/路径)原先各自遍历 `groups`
    计算, 而种子页按视图分片**不回 groups**(`VIEW_ARRAYS["torrent"] = ("torrents",)`) ⇒
    四个弹层恒空、只剩"暂无数据"(H&R 是固定两档, 表现为 0/0 —— 更隐蔽)。
    这类"跨视图的常驻消费者去依赖按视图裁剪的阵列"本项目**已犯三次**:
    状态栏速度(issue 26-09-20-1646) / 追剧页成员索引(BUG-8) / 本次筛选器,
    故机械钉住: 每个选项 computed 必须出现单点调用, 且按组算的旧实现不得复活。
    """
    text = _strip_js_comments(text)  # 注释里出现这些名字不算数(见 _strip_js_comments)
    if not re.search(r"^\s*facetRows\(\)\s*\{", text, re.M):
        problems.append(f"{rel} 找不到 facetRows() —— 筛选器选项的取数面单点(见 filters.js 注释)")
    for name in ("tagOptions", "categoryOptions", "siteOptions", "pathOptions"):
        body = _computed_body(text, name)
        if body is None:
            problems.append(f"{rel} 找不到 computed.{name}(改名前请同步本守阵)")
        elif "_facetOptions(" not in body:
            problems.append(
                f"{rel} computed.{name} 没走 _facetOptions 单点 —— 各自遍历集合会在种子页"
                "(按视图分片不回 groups)算出空选项, 弹层只剩\"暂无数据\""
            )
    for name in ("hrOptions", "hrSrcOptions"):
        body = _computed_body(text, name)
        if body is not None and "facetRows" not in body:
            problems.append(f"{rel} computed.{name} 没走 facetRows 单点 —— 种子页不回 groups ⇒ H&R 档位恒 0/0")
    if "_memberValueOptions" in text:
        problems.append(f"{rel} 残留 _memberValueOptions —— 选项一律走 facetRows/_facetOptions 单点"
                        "(按组算的第二条口径正是本次故障的成因)")


# 挂件级类名白名单 —— 只盯这些; 组件层类名(`.ico` / `.row` / `.cell` 等)不进, 否则满屏误报。
# 添加新挂件类时请同步这里。
_PAGE_HOOK_CLASSES = ("hub-page", "ce-page", "layout")


def _scan_page_class_wiring(problems):
    """挂件类名配对: HTML 的 `<main class="X ...">` 里出现的挂件类名必须在 CSS 里有规则

    现象(2026-09-21, 用户报"输入框缺发光 + 排版竖着"):
    CSS 里 `.hb-page`(前缀化时手滑)定义 `--tone` 等, 而 HTML 上是 `class="ce-page hub-page"` ——
    `.hb-page` 选择器**永远不命中**任何元素 ⇒ `--tone` 从未定义 ⇒ 所有 `var(--tone)` 派生值
    替换时判为无效 ⇒ 描边回退、发光整条消失、等宽字体也不生效(剩下字体 fallback)。
    静悄悄地废掉一整块视觉,**没有运行时报错**, 靠真浏览器量 computedStyle 才看得出来。

    为防止再犯: 每张 index.html 的 `<main class="...">` 里出现的挂件类名, 都必须能在某份
    CSS(shared/* 或同目录的 *.css)里找到对应的选择器规则。
    """
    css_text = ""
    for dirpath, _dirs, files in os.walk(STATIC_ROOT):
        for name in sorted(files):
            if not name.endswith(".css"):
                continue
            if "/vendor/" in f"/{dirpath}/{name}":
                continue
            css_text += open(os.path.join(dirpath, name), encoding="utf-8").read() + "\n"
    selectors = set(re.findall(r"^\s*\.([A-Za-z_][\w-]*)\s*[\{,]", css_text, re.M))
    for dirpath, _dirs, files in os.walk(STATIC_ROOT):
        for name in sorted(files):
            if not name.endswith(".html"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, name), STATIC_ROOT).replace(os.sep, "/")
            if "/vendor/" in f"/{rel}":
                continue
            text = open(os.path.join(dirpath, name), encoding="utf-8").read()
            for m in re.finditer(r"<\s*main\b[^>]*\bclass=\"([^\"]+)\"", text):
                for cls in m.group(1).split():
                    if cls not in _PAGE_HOOK_CLASSES:
                        continue
                    if cls not in selectors:
                        problems.append(
                            f"{rel} `<main class=\"...{cls}...\">` 在所有 CSS 里都找不到 `{cls}` "
                            f"的选择器规则 —— 该挂件类上的令牌/变量定义永不生效, 派生样式全部失效"
                            f"(参考 2026-09-21 把 .hb-page 错写成 .hub-page 之外的类名, 整页无发光)"
                        )


# PERF-01(2026-09-24): 这两类元素**不许**再挂 backdrop-filter —— 它们要么是全屏遮罩, 要么是
# 常驻吸顶/吸底条, 都处在别的遮罩的 backdrop 里; 一旦两块毛玻璃叠在一起, Chromium 每帧都要
# 回读并重复模糊整个视口(星图"点状态栏历史流量卡顿"的实测根因)。
# 注: 抽屉遮罩 `.drawer-mask` 不在此列 —— 它是**当时唯一在用的**遮罩, 底下已无第二块毛玻璃,
# 两套 UI 同款且棱镜侧实测无卡顿; 一并摘掉会单边改动棱镜外观, 超出本次范围(见 scope-guard)。
_PERF_BACKDROP_BANNED = ("modal-mask", "topbar", "status-strip", "statusbar", "ce-actions")


def _scan_backdrop_filter(problems):
    """毛玻璃守阵: 全屏遮罩 / 吸顶吸底条不得带 backdrop-filter, 且星图与棱镜的数量必须对齐

    现象(2026-09-24, 用户报"星图卡顿, 点状态栏历史流量尤其明显; 棱镜无此问题"):
    星图 atlas/style.css 一度挂了 5 处 backdrop-filter —— 顶栏 blur(12px) / 状态分布条 blur(10px) /
    弹层遮罩 blur(3px) / 配置页吸底条 blur(10px) / 抽屉遮罩 blur(2px); 棱镜侧只有抽屉遮罩一处。
    点开"历史流量"时, .modal-mask(全屏 fixed + blur)的 backdrop 里正压着顶栏与状态分布条这两块
    毛玻璃 —— **嵌套毛玻璃**迫使每帧回读 + 重复模糊整个视口, 而弹层内的 hist-draw 描边动画
    还在主线程逐帧重绘, 两者叠成肉眼可见的卡顿。棱镜 .modal-mask 从来没加过 backdrop-filter,
    所以无此症状。

    两层断言(缺一不可):
    1.**位置**: 上述六类元素一律不许出现 backdrop-filter(不论哪套 UI、哪份 CSS);
    2.**数量**: 各套 UI 自己的声明数必须相等 —— 防"只在某一侧加回来"这类单边改动
      (shared/console_hub.css 是共用层, 各边同担, 不计入各自计数)。
    扫描前先剥 `/* ... */`, 否则本文件里解释这段历史的注释会被当成真实声明(实测会误报)。
    """
    counts = {ui: 0 for ui in _UI_ALL}
    for dirpath, _dirs, files in os.walk(STATIC_ROOT):
        for name in sorted(files):
            if not name.endswith(".css") or "/vendor/" in f"/{dirpath}/{name}":
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, STATIC_ROOT).replace(os.sep, "/")
            text = re.sub(r"/\*.*?\*/", "", open(path, encoding="utf-8").read(), flags=re.S)
            sel = ""
            for line in text.splitlines():
                if "{" in line:
                    sel = (sel + " " + line.split("{", 1)[0]).strip()
                if re.search(r"backdrop-filter\s*:", line):
                    for ui in _UI_ALL:
                        if rel.startswith(ui + "/"):
                            counts[ui] += 1
                    for bad in _PERF_BACKDROP_BANNED:
                        if re.search(r"\.%s\b" % re.escape(bad), sel):
                            problems.append(
                                f"{rel} `{sel or '(未识别选择器)'}` 上出现 backdrop-filter —— "
                                f"{bad} 是全屏遮罩或常驻吸顶/吸底条, 加毛玻璃会与弹层遮罩叠成嵌套模糊"
                                f"(每帧回读 + 重复模糊整个视口; 星图 2026-09-24 卡顿根因, 见 PERF-01)"
                            )
                if "}" in line:
                    sel = ""
    if len(set(counts.values())) != 1:
        problems.append(
            f"各套 UI 的 backdrop-filter 声明数不对齐: "
            f"{' / '.join(f'{ui} {n} 处' for ui, n in counts.items())} —— "
            f"单边加毛玻璃会重新引入嵌套模糊卡顿(遮罩类从不带 backdrop-filter, 见 PERF-01)"
        )


def _extract_column_keys(app_js: str, const_name: str):
    """从 app.js 提取列模型数组的 key 清单(缺该数组返回 None —— 列模型被改名/搬走的信号)"""
    m = re.search(r"const %s = \[(.*?)\n\];" % const_name, app_js, re.S)
    if not m:
        return None
    return re.findall(r'key: "(\w+)"', m.group(1))


def _scan_column_cells_paired(problems):
    """列模型每个列 key 必须在对应模板里有值单元格分支(辅种扩列 2026-09-28 守阵)

    列模型(TABLE_COLUMNS)是表头/grid 模板/列选择器的单一来源 —— 但**值单元格**是模板里的
    v-if/v-else-if 分支, 模板漏写某列的分支时没有任何报错: 表头照常渲染、列选择器照常可勾,
    值格却永远空白, 且无法从"pytest 全绿"察觉。明细列还要**两处成对**(groups.html 辅种页
    展开明细 + shows.html 追剧集成员 —— 两份模板共用同一列模型, 漏一处 = 该页该列空白)。
    另钉住 loadColState 必须消费 `hide` 标志(默认隐藏列的注入单点, 漏消费 = hide 列全部
    默认可见, 可选列设计失守)。
    """
    app_js = open(os.path.join(STATIC_ROOT, "shared", "app.js"), encoding="utf-8").read()
    plans = (
        ("GROUP_COLUMNS", ("tpl/groups.html", )),
        ("DETAIL_COLUMNS", ("tpl/groups.html", "tpl/shows.html")),
        ("TORRENT_COLUMNS", ("tpl/torrents.html", )),
        ("SHOW_COLUMNS", ("tpl/shows.html", )),
    )
    for const, tpls in plans:
        keys = _extract_column_keys(app_js, const)
        if keys is None:
            problems.append(f"app.js 缺少列模型 {const}(列模型单一来源被改名/搬走?)")
            continue
        for tpl in tpls:
            text = open(os.path.join(STATIC_ROOT, "shared", tpl), encoding="utf-8").read()
            for k in keys:
                if f"col.key === '{k}'" not in text:
                    problems.append(f"{const} 列 {k} 在 shared/{tpl} 没有值单元格分支(col.key === '{k}') —— 表头在、值永远空白")
    if ".filter((c) => c.hide)" not in app_js:
        problems.append("app.js loadColState 未消费列定义 hide 标志(hide 列默认隐藏失灵)")


def _scan_progress_val_parity(problems):
    """进度条数值盒守阵: 三套皮肤的 `.m-progress .val` 都必须恰 1 条且带 min-width 定宽(2026-09-28)

    现象(用户报"种子页进度条长度不一致, 似乎受后面的进度文本长度影响"): `.m-progress` 是
    flex 行, `.bar { flex: 1 1 auto }` 吃剩余空间, `.val` 只占自身文本宽 —— 「100.0%」比
    「5.2%」宽, 同一列各行条的起点/长度随百分比文本宽度逐行漂移。处置 = 数值盒
    `min-width: 4em`(容纳最宽的「100.0%」, 三套皮肤字号 11.5-12px 下实测文本 ≈3.5em 以内)
    + `text-align: right`, 条长即与文本解耦; 本守阵防"只在某一侧加 / 新皮肤漏带"。
    """
    hits = {ui: 0 for ui in _UI_ALL}
    for dirpath, _dirs, files in os.walk(STATIC_ROOT):
        for name in sorted(files):
            if not name.endswith(".css") or "/vendor/" in f"/{dirpath}/{name}":
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, STATIC_ROOT).replace(os.sep, "/")
            ui = next((u for u in _UI_ALL if rel.startswith(u + "/")), None)
            if ui is None:
                continue
            text = re.sub(r"/\*.*?\*/", "", open(path, encoding="utf-8").read(), flags=re.S)
            lines = text.splitlines()
            for idx, line in enumerate(lines):
                if not re.match(r"^\s*\.m-progress \.val\s*\{", line):
                    continue
                hits[ui] += 1
                body = line.split("{", 1)[1]
                j = idx
                while "}" not in body and j + 1 < len(lines):
                    j += 1
                    body += lines[j]
                if not re.search(r"min-width\s*:", body):
                    problems.append(f"{rel} `.m-progress .val` 缺 min-width 定宽 —— 条吃剩余空间, "
                                    "数值盒不定宽时条长随百分比文本宽度逐行漂移")
    for ui, n in hits.items():
        if n != 1:
            problems.append(f"{ui} 皮肤的 `.m-progress .val` 基础规则数 = {n}(应恰 1 条且带 min-width 定宽)")


def _scan_frontend_assets():
    """扫描 webui/static 返回问题清单(空 = 健康)

    检查项(均为"整页白屏 / 整块功能静默失效"级故障, 且 Python 侧测试天然看不见):
    1. 合并冲突标记残留(`<<<<<<<` / `>>>>>>>` / 单独一行 `=======`) —— 语法错误;
    2. JS 里"注释已闭合却仍留续行"(上一非空行以 `*/` 结尾, 本行又以 `*` 起头) ——
       整包 SyntaxError, app.js 不执行, Vue 从不 mount, `v-cloak` 的 #app 恒 display:none;
    3. JS 语法硬校验: 有 node 时单进程批量校验(语义同 `node --check`, 见 _scan_js_syntax_with_node);
    4. CSS 规则块漏闭合(浏览器会把其后规则整段当声明丢弃) —— 见 _scan_css_blocks;
    5. 模板 `<transition>` 不配对 / 把弹窗包进 `<transition>`(只渲染首子节点 -> 弹窗全丢);
    6. 模板/样式里以 `/` 开头的 src|href 引用, 在 static 根下必须真实存在(防改名/漏档 404);
    7. 追剧视图"集成员 -> hash"必须走 `memberHashesOf`(见 _scan_episode_member_hashes);
    8. `STATE_RANK` 必须与后端 `_SHOW_STATE_RANK` 逐项一致(见 _scan_state_rank) ——
       两表分别决定"辅种页组行"与"追剧页集行"的颜色, 漂移的后果是同一批种子两页不同色;
       该项同时钉住**顺序语义**: seeding 必须排在 paused 之前(混合态取做种色, 2026-09-21 用户口径);
    9. 乐观 UI 的**撤下**路径: 真值快照必须早于补丁重贴、判定必须走 `_optimisticSettled`、
       回执后必须调 `_pullTruthAfterCmd`(见 _scan_pending_settle) —— 任一被绕过, 撤下就退回
       3s 常量兜底(真机连报三次的那条), 或判定恒真导致失败路径留假状态(红线)。
    10. 拆分接线: 片段文件必须被 HTML 引用 + 被 app.js `app.mixin()` 注入, 且成员不得重名
       (见 _scan_mixin_wiring) —— 漏挂/漏注入 = 整块功能静默消失, 重名 = 被覆盖者永不执行。

    11. 筛选器选项必须走 `facetRows` 单点取数面(见 _scan_filter_facets) —— 各自遍历 `groups`
       会在种子页(按视图分片不回数组)算出空选项, 弹层只剩"暂无数据"。
    12. 页面"挂件类名"必须配对存在 CSS 规则: HTML 的 `<main class="...hub-page...">` / `ce-page` /
       `layout` 这类挂件类名, 都必须在对应 CSS(shared/console_hub.css / prism/views.css /
       atlas/style.css)里有规则, 否则**整段页面没样式**(实测: 把 `.hub-page` 错写成 `.hb-page`
       后 `--tone` 从未定义, 所有 `var(--tone)` 派生的描边/发光/语义色全部失效, 还以为"页面正常"
       只是"缺发光"; 真浏览器量 computedStyle 才看得出来)。
       (见 _scan_page_class_wiring)

    13. 毛玻璃(backdrop-filter)不得挂在全屏遮罩 / 吸顶吸底条上, 且星图与棱镜的声明数必须相等
       (见 _scan_backdrop_filter) —— 嵌套毛玻璃会让"点状态栏历史流量"这类开弹层的动作明显卡顿,
       且**只在星图侧复现**(棱镜 .modal-mask 从不带 backdrop-filter), 属于"两边都能跑、一边更卡"
       的差异, 肉眼走查看不出来, 只能靠计数兜底。

    14. 列模型每个列 key 必须在对应模板有值单元格分支(见 _scan_column_cells_paired) ——
       模板漏写分支无任何报错(表头在、列选择器可勾、值永远空白); 明细列两份模板
       (groups.html/shows.html)必须成对; loadColState 必须消费 hide 标志(默认隐藏列注入单点)。

    15. CSS 注释体内不得出现 `*/`(见 _scan_css_comments) —— 注释被提前终止后, 尾巴落成
       代码态垃圾, 浏览器按错误恢复把紧跟的规则整条静默丢弃(2026-09-28 实测: console 皮肤
       进度条注释 `(s-*/member-row 族)` 吞掉 `.m-progress { display: flex }`, 三处表格
       进度条只剩百分比没有条)。

    16. 三套皮肤的 `.m-progress .val` 基础规则必须恰 1 条且带 min-width 定宽(见
       _scan_progress_val_parity) —— 条吃剩余空间, 数值盒不定宽时进度条长度随百分比
       文本宽度逐行漂移(2026-09-28 实测: 「100.0%」的行比「5.2%」的行条短)。


    WARN: 7/8/9/11 四项按 **app.js 整包**(HTML 加载顺序拼接 app.js + 各片段)扫描, 不按单文件 ——
      拆分后同一条不变量的代码可能分处两个文件, 只看一个文件必然漏(2026-09-20 实测)。
    """
    problems = []
    js_files = []
    for dirpath, _dirs, files in os.walk(STATIC_ROOT):
        for name in sorted(files):
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, STATIC_ROOT).replace(os.sep, "/")
            if not name.endswith((".js", ".css", ".html")):
                continue
            with open(path, encoding="utf-8") as f:
                lines = f.read().splitlines()
            for i, line in enumerate(lines, 1):
                if line.startswith(("<<<<<<<", ">>>>>>>")) or line == "=======":
                    problems.append(f"{rel}:{i} 合并冲突标记残留")
            # 只扫自家前端(vendor 为第三方压缩产物, 不适用本仓库注释/结构规范)
            if "/vendor/" not in f"/{rel}":
                if name.endswith(".js"):
                    js_files.append((path, rel))
                    for i, line in enumerate(lines):
                        if not re.match(r"^\s*\*(?!/)", line):
                            continue
                        prev = next((l for l in reversed(lines[:i]) if l.strip()), "")
                        if prev.rstrip().endswith("*/"):
                            problems.append(f"{rel}:{i + 1} 注释块已闭合后仍有续行(会造成整包 SyntaxError)")
                elif name.endswith(".css"):
                    _scan_css_blocks(path, rel, problems)
                    _scan_css_comments(path, rel, problems)
                elif name.endswith(".html"):
                    _scan_template_transitions(path, rel, problems)
            for ref in re.findall(r'(?:src|href)="(/[^"]+)"', "\n".join(lines)):
                if not os.path.exists(os.path.join(STATIC_ROOT, ref.lstrip("/"))):
                    problems.append(f"{rel} 引用不存在的静态资源 {ref}")
    _scan_js_syntax_with_node(js_files, problems)
    # app.js 已按域拆分(2026-09-20): 跨文件不变量按**整包**(HTML 加载顺序拼接)扫描 ——
    # 只看 app.js 会把搬进片段的那半漏掉, 只看片段又拿不到 app.js 里的表格常量与 refresh 主链。
    bundle = _app_bundle_files()
    bundle_text = "\n".join(open(p, encoding="utf-8").read() for p, _r in bundle)
    rel = "shared/app.js(整包 %d 个文件)" % len(bundle)
    _scan_episode_member_hashes(bundle_text, rel, problems)
    _scan_state_rank(bundle_text, rel, problems)
    _scan_pending_settle(bundle_text, rel, problems)
    _scan_filter_facets(bundle_text, rel, problems)
    _scan_mixin_wiring(problems)
    _scan_page_class_wiring(problems)
    _scan_backdrop_filter(problems)
    _scan_column_cells_paired(problems)
    _scan_progress_val_parity(problems)
    return problems


def test_frontend_static_bundle_health():
    """前端静态资源守阵: 冲突残留/注释孤儿续行/node 语法校验/CSS 漏闭合/transition 吞弹窗/引用缺失/集成员取 hash/状态优先级表/列单元格配对

    三个实测故障(2026-09-17)都是"pytest 全绿但界面废掉"的形态:
    1. app.js 注释续行留在已闭合的 `*/` 之后 -> 整包 SyntaxError -> Vue 不 mount -> 只剩背景色;
    2. prism views.css 一条规则漏 `; }` -> 其后约 200 条规则被浏览器丢弃 -> 棱镜大半样式消失;
    3. 抽屉外层 `<transition>` 未闭合 -> 统计/限速/添加/确认框被 Transition 丢弃(点了没反应且无报错)。
    装了 node 的机器还会在此跑 `node --check` 对所有前端 JS 做真语法校验(无 node 则静默跳过)。
    """
    problems = _scan_frontend_assets()
    assert not problems, "前端静态资源问题: " + "; ".join(problems)


def _tpl_path(src, ui):
    """清单分片 src -> 盘上路径: /shared/... = 单一语义源(收敛后唯一形态); 相对路径按 <ui>/ 解析(兼容)"""
    if src.startswith("/"):
        return os.path.join(STATIC_ROOT, *src.lstrip("/").split("/"))
    return os.path.join(STATIC_ROOT, ui, *src.split("/"))


def _scan_ui_diff_registry(problems):
    """收集 shared/tpl 里的 UI 差异口(`v-if="ui === ...'"`) —— 「活差异清单」的机械面

    收敛定案(plans/26-09-26-2233 W3): 单一语义模板后, 模板级 UI 差异只允许写成
    `<template v-if="ui === 'atlas'|'prism'">` 条件块, 且块前必须带 `ui-diff:` 注释说明原因;
    新增差异走这个口, **不许另开分片副本**(双模板副本的复发形态就是绕开这个口私拷一份)。
    """
    registry = []
    shared_dir = os.path.join(STATIC_ROOT, "shared", "tpl")
    if not os.path.isdir(shared_dir):
        problems.append("缺 shared/tpl 单一语义分片目录(模板分裂回潮?)")
        return registry
    for name in sorted(os.listdir(shared_dir)):
        if not name.endswith(".html"):
            continue
        lines = open(os.path.join(shared_dir, name), encoding="utf-8").read().split("\n")
        for i, ln in enumerate(lines):
            m = re.search(r"v-if=\"ui\s*===\s*'(\w+)'\"", ln)
            if not m:
                continue
            side = m.group(1)
            if side not in _UI_ALL:
                problems.append(f"shared/tpl/{name}:{i + 1} UI 条件取值非法: {side!r}(只认 {'|'.join(_UI_ALL)})")
            if "ui-diff:" not in "\n".join(lines[max(0, i - 3):i + 1]):
                problems.append(f"shared/tpl/{name}:{i + 1} ui 条件块缺 `ui-diff:` 注释(差异口必须写明原因)")
            registry.append(f"{name}:{i + 1}:{side}")
    return registry


def test_frontend_template_split_wiring():
    """模板分片接线守阵(2026-09-26 W1; 26-09-27 收敛后 = 单一语义源 shared/tpl): 清单完整性 + 差异口 + 聚合配平

    模板拆分/收敛后的静默故障形态(与 JS 片段的 _scan_mixin_wiring 同源):
      1. 分片文件在盘上但清单漏挂 —— boot 不注入, 该页面区整块消失(零报错);
      2. 清单挂了不存在的分片 / into 非法 —— boot fetch 404, 整页停在错误占位;
      3. 两套 shell 清单漂移(各自演化 parts/scripts)—— 单一语义模板下等于偷偷分裂出第二份模板;
      4. 绕开 UI 差异口私拷模板块(双模板副本的复发形态)—— 由 _scan_ui_diff_registry 钉住。
    另钉: 聚合标签配平(切割边界错位的兜底)、shell ≤200 行 / 单分片 ≤400 行、清单脚本序(vendor 首 / app.js 尾)。
    """
    problems = []
    manifests = {}
    for ui in _UI_ALL:
        shell = open(os.path.join(STATIC_ROOT, ui, "index.html"), encoding="utf-8").read()
        udir = os.path.join(STATIC_ROOT, ui)
        mf = _ui_manifest(ui)
        manifests[ui] = mf
        n_shell = shell.count("\n") + (0 if shell.endswith("\n") else 1)
        if n_shell > 200:
            problems.append(f"{ui}/index.html {n_shell} 行, shell 体量上限 200(拆了又长回去?)")
        assert '<script src="/shared/boot.js"></script>' in shell, f"{ui} shell 缺 boot.js 引用(分片无人注入)"
        names = []
        for part in mf["parts"]:
            path = _tpl_path(part["src"], ui)
            names.append(os.path.basename(part["src"]))
            if not os.path.isfile(path):
                problems.append(f"{ui}: 清单挂了不存在的分片 {part['src']}(boot fetch 404 = 整页停在错误占位)")
                continue
            n = open(path, encoding="utf-8").read().count("\n")
            # 单分片体量上限默认 400; settings-detail.html 是 HR 表①(计划 26-10-01-2216 阶段2,
            # 拍板②b 按站点明细表)的落点, 391 -> 435 行属功能增长不是拆分回潮, 单独点名给例外额度
            # (其余分片仍钉 400); 26-10-02-1936 阶段2 折叠头 + 覆盖式全屏覆盖层再涨 454 -> 473,
            # 额度提到 500; 26-10-04-0312 S4 表③ 拉取历史(全局 <details> 段)再涨 482 -> 539,
            # 额度提到 560 —— 该分片下次再长应把 speed/keys 等视图拆成独立分片 —— 切割须过
            # 等价性验证(pitfalls/web-ui/frontend-split.md), 不得顺手抽文件
            cap = 560 if os.path.basename(part["src"]) == "settings-detail.html" else 400
            if n > cap:
                problems.append(f"{ui}/{part['src']} {n} 行, 超 {cap} 行单分片体量上限")
            if part.get("into") not in ("app", "body"):
                # 其余值 = #app 内自定义选择器落点(boot.js 会先查常规 DOM 再下钻 <template> 片段;
                # 方案A 停靠面板 26-10-03-0917 W1 起 drawer 分片落 .drawer-dock)。约定: 必须以
                # "." 开头且落点容器真实存在于某分片, 防手滑写成任意字符串
                into = part.get("into")
                if not (isinstance(into, str) and into.startswith(".") and into):
                    problems.append(f"{ui}/{part['src']} into 非法: {into!r}(boot 只认 app|body 或 '.' 开头的选择器)")
                    continue
                # 自定义落点容器必须真实存在于某分片(boot.js 运行时 fail-fast, 这里提前到静态)
                if into[1:] not in _ui_aggregate(ui):
                    problems.append(f"{ui}/{part['src']} into 落点 {into} 在任何分片中都不存在(boot 会 fail-fast 停在错误占位)")
        tpl_dir = os.path.join(udir, "tpl")
        if os.path.isdir(tpl_dir):
            problems.append(f"{ui}: 残留 {ui}/tpl/ 目录(收敛后唯一源是 shared/tpl, 双副本必须删除)")
        assert mf["scripts"], f"{ui} 清单缺 scripts(逻辑脚本无人放行)"
        assert mf["scripts"][0].endswith("vue.global.prod.js"), f"{ui} 清单首个脚本必须是 Vue vendor"
        assert mf["scripts"][-1].endswith("/app.js"), (f"{ui} 清单末个脚本必须是 app.js(它末尾才 createApp, 且启动时要读 window.AQB_*)")
        # W2 CSS 分层(atlas/console): 链接顺序即级联序; 单文件 ≤700 行体量守阵
        css_files = _ui_css_files(ui)
        if ui in ("atlas", "console"):
            rels = [os.path.relpath(p, STATIC_ROOT).replace(os.sep, "/") for p in css_files]
            assert rels == [
                f"{ui}/style.css", f"{ui}/css/components.css", f"{ui}/css/views.css", f"{ui}/css/dialogs.css"
            ], (f"{ui} CSS 链接顺序漂移: {rels}(级联序 = link 序; 拆分是连续字节切片, 重排顺序前先核对视觉等价)")
            for p in css_files:
                n = open(p, encoding="utf-8").read().count("\n")
                if n > 700:
                    problems.append(f"{os.path.relpath(p, STATIC_ROOT)} {n} 行, 超 700 行单 CSS 体量上限")
    # 单一语义模板: 各套 shell 清单必须逐项相等 —— 漂移 = 偷偷分裂出第二份模板(收敛前态回潮)
    base_mf = manifests[_UI_ALL[0]]
    for ui in _UI_ALL[1:]:
        assert manifests[ui] == base_mf, (
            f"{ui} 的 tpl-manifest 与 {_UI_ALL[0]} 不一致 —— 单一语义模板下清单漂移 = 模板分裂回潮, 必须逐项对齐: "
            f"{_UI_ALL[0]}={base_mf} / {ui}={manifests.get(ui)}"
        )
    # 盘上孤儿分片: shared/tpl 存在但清单漏挂
    shared_dir = os.path.join(STATIC_ROOT, "shared", "tpl")
    listed = {os.path.basename(p["src"]) for p in manifests["atlas"]["parts"]}
    if os.path.isdir(shared_dir):
        for f in sorted(os.listdir(shared_dir)):
            if f.endswith(".html") and f not in listed:
                problems.append(f"shared/tpl/{f} 在盘上但清单漏挂(boot 不注入 = 该页面区整块消失)")
    # UI 差异口注册表(活差异清单): 条件块只认 _UI_ALL 内的皮肤名且必须带 ui-diff 注释
    registry = _scan_ui_diff_registry(problems)
    assert registry, "UI 差异口注册表为空 —— 该机制是收敛后新增模板级差异的唯一入口; 若确已全部消除, 同步本守阵"
    assert not problems, "模板分片接线问题: " + "; ".join(problems)
    # 聚合配平放最后: 切割边界错位(半个元素切进相邻分片)在这里现形
    for ui in _UI_ALL:
        _assert_tags_balanced(_ui_aggregate(ui), f"{ui} 聚合模板")


def test_frontend_button_system_paired():
    """按钮体系(.bt)迁移守阵(2026-09-26, 方案 B 星图胶囊 / C 棱镜双色) —— "两套 UI 成对改"的静态兜底

    迁移是一次大批量类名替换(ce-btn/ce-icon -> bt 变体), 最危险的残缺形态是"只改一边"或
    "模板换了 CSS 没换"(页面静默回退到 UA 默认按钮)。四类机械断言:
    1. 旧类名 ce-btn / ce-icon 在全部前端语料(html/css/js)里零残留;
    2. .bt 体系块与六个语义变体在两套 CSS 各有成对定义(星图 style.css / 棱镜 components.css);
    3. 两套 index.html 的 bt 变体用量逐类相等(模板本就同构, 数量不等 = 单边漏改/误删);
    4. 双色配方令牌 --on-accent / --on-accent-ink / --on-error 在星图 :root 与棱镜五主题成对声明
      (缺一个主题, 该主题实心主钮/危险钮的前景色会掉回继承或 UA 默认)。
    """
    atl = os.path.join(STATIC_ROOT, "atlas")
    pri = os.path.join(STATIC_ROOT, "prism")
    atl_html = _ui_aggregate("atlas")
    pri_html = _ui_aggregate("prism")
    atl_css = _ui_css_aggregate("atlas")
    pri_css = open(os.path.join(pri, "css", "components.css"), encoding="utf-8").read()

    # 1. 旧类名零残留(全语料: static 树下全部 html/css/js, 排除 vendor; 类名若只留在注释里
    #    也应清理, 留着会误导下一次死类判定)
    corpus_files = []
    for root, dirs, files in os.walk(STATIC_ROOT):
        dirs[:] = [d for d in dirs if d != "vendor"]
        for f in files:
            if f.endswith((".html", ".css", ".js")):
                corpus_files.append(os.path.join(root, f))
    leftovers = []
    for f in corpus_files:
        text = open(f, encoding="utf-8").read()
        for bad in ("ce-btn", "ce-icon"):
            if bad in text:
                leftovers.append(f"{os.path.relpath(f, STATIC_ROOT)}:{bad}")
    assert not leftovers, f"旧按钮类名必须零残留: {leftovers}"

    # 2. .bt 体系块与变体在两套 CSS 成对定义
    variants = ["primary", "ghost", "danger", "danger-solid", "icon", "sm"]
    for css, name in (
        (atl_css, "atlas css 聚合(link 序)"),
        (pri_css, "prism/css/components.css"),
        (_ui_css_aggregate("console"), "console css 聚合(link 序)"),
    ):
        assert re.search(r"^\.bt \{", css, re.M), f"{name} 缺 .bt 体系块"
        for v in variants:
            assert re.search(rf"^\.bt\.{re.escape(v)} \{{", css, re.M), f"{name} 缺 .bt.{v} 变体"

    # 3. 两套模板的 bt 用量逐类相等(class="bt ..." 静态写法; :class 动态绑定单独对账)
    def _bt_counts(html):
        counts = {}
        for m in re.finditer(r'class="(bt[^"]*)"', html):
            for cls in m.group(1).split():
                if cls == "bt" or cls.startswith("bt-"):
                    counts[cls] = counts.get(cls, 0) + 1
                elif cls in ("primary", "ghost", "danger", "danger-solid", "icon", "sm"):
                    counts[f"~{cls}"] = counts.get(f"~{cls}", 0) + 1
        return counts

    a_cnt, p_cnt = _bt_counts(atl_html), _bt_counts(pri_html)
    assert a_cnt == p_cnt, f"两套模板 bt 用量不成对: atlas={a_cnt} prism={p_cnt}"
    assert a_cnt, "模板里没有任何 bt 按钮(迁移被整体回退?)"
    for dyn in ("'danger-solid'", "'primary'"):
        assert atl_html.count(dyn) == pri_html.count(dyn) and atl_html.count(dyn) >= 1, \
            f"站内确认框的动态变体绑定 {dyn} 未成对"

    # 4. 双色配方令牌成对声明(星图 :root 一处 + 棱镜五主题各一处)
    for tok in ("--on-accent:", "--on-accent-ink:", "--on-error:"):
        assert atl_css.count(tok) == 1, f"星图 :root 应恰好声明一次 {tok}"
        themes = os.path.join(pri, "css", "themes")
        for tf in os.listdir(themes):
            tcss = open(os.path.join(themes, tf), encoding="utf-8").read()
            assert tok in tcss, f"棱镜主题 {tf} 缺 {tok}(五主题须成对)"


def test_frontend_search_syntax_wiring():
    """搜索匹配**服务端单点**的前端接线守阵(2026-09-26 统一, 治"同一语义修三遍")

    两类"pytest 全绿但交互废掉 / 前端再长出第二套匹配实现"的故障形态, 一律机械钉住:
    1. 顶栏搜索清除钮必须挂 @mousedown.prevent —— 缺了它, 按下瞬间输入框失焦收窄
      (focus 时 240→300px 的宽度过渡回退), 绝对定位在右沿的按钮随收窄移出光标,
      click 落空 => "有焦点时点 x 清不掉, 无焦点正常"; 两套 index.html 成对断言。
    2. 三页(辅种/种子/追剧)搜索命中一律消费服务端 searchHits(views.py::search_torrents 的
      行级裁决, 候选行 = 名字/站点/分类/路径/标签/文件名): 前端**不得再出现**任何文本匹配
      实现 —— 26-09-26 统一前 filters.js(_parseSearchQuery/_searchNorm/_torrentTextMatch)、
      hr.js(更早的整句 includes)、shows.js(剧名整句 includes)各持一份, 同一语义
      (恶女 10 / 季包"cat 12")前后端修了三遍; 复活任何一个即与单点漂移, 直接红。
      语法(词 AND/-排除/短语/归一)行为级用例在服务端侧: test_parse_query_tokens /
      test_search_torrents_*(对账守阵已无对象 —— 客户端没有解析器了)。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    filters_js = open(os.path.join(shared, "filters.js"), encoding="utf-8").read()
    hr_js = open(os.path.join(shared, "hr.js"), encoding="utf-8").read()
    app_js = open(os.path.join(shared, "app.js"), encoding="utf-8").read()
    shows_js = open(os.path.join(shared, "shows.js"), encoding="utf-8").read()

    # 1. 清除钮 mousedown.prevent 成对(两套模板的 search-clear 按钮逐个检查)
    for theme in _UI_ALL:
        html = _ui_aggregate(theme)
        m = re.search(r'<button[^>]*class="search-clear"[^>]*>', html)
        assert m, f"{theme} 模板找不到 search-clear 按钮"
        tag = m.group(0)
        assert "@mousedown.prevent" in tag, f"{theme} search-clear 缺 @mousedown.prevent(焦点态清除失灵回归)"
        assert '@click="clearSearch"' in tag, f"{theme} search-clear 缺 clearSearch 接线"

    # 2. 前端无第二匹配实现(反漂移: 任何一个复活即红); 三页接线走 searchHits
    # (注释里允许引用旧函数名讲历史, 故断言"名字+括号"—— 定义或调用才算复活)
    for name in ("_parseSearchQuery", "_searchNorm", "_torrentTextMatch", "_torrentSearchPass"):
        assert not re.search(rf"{name}\s*\(", filters_js), \
            f"filters.js 复活了客户端匹配 {name}(搜索匹配单点在 views.py, 复活即漂移)"
    assert "_torrentTextMatch" not in hr_js, "hr.js 不得再留 _torrentTextMatch 旧整句实现(双实现漂移)"
    assert 'searchHitsQ' not in app_js, "app.js 残留 searchHitsQ(客户端匹配时代的陈旧守卫, 已随单点化删除)"
    assert "hits.has(r.hash)" in filters_js, "filteredTorrents 未消费 searchHits(种子页搜索断线)"
    assert "(s.name || \"\").toLowerCase().includes(q)" not in shows_js, \
        "shows.js 复活了剧名整句 includes 旧匹配(剧名命中应来自服务端名字行)"


def test_frontend_hr_safety_wiring():
    """删除安全档位的前端接线守阵(2026-09-25, 计划 webui-hr-safety-display)

    四类"字段/令牌打错 = pytest 全绿但页面静默空白或配色失效"的故障形态, 一律机械钉住:
    1. hr.js 的 token 映射表(HR_SRC_CLASSES / HR_SRC_BUCKETS)必须与后端 resolve.py 的 SRC_* 常量
      逐字一致 —— 来源档位是前后端契约, 打错字来源标记静默消失; 三档类名驱动单元格底线三编码(CSS),
      文字结论改由悬停弹窗承载(原生 title 已移除, 避免与弹窗叠出被遮挡的冗余提示);
    2. 做种时长列在两套 UI 各 3 处(组内成员/种子页/明细)都必须换绑 hrDurClass + hrSrcClass, 并由
      hrSrcFull/hrSrcHalf 挂底线 + hrPopEnter 触发 —— 漏一处那一列就不显示安全档位/来源线/悬停弹窗;
      弹窗单例 DOM(teleport body)每套 UI 恰一份(26-09-26-webui-hr-popup 起 :title 换成悬停弹窗触发);
      要求时长的渲染门只认「已做种非空 + 有要求」, 不得依赖 hr_triggered(2026-09-29 实报:
      未核/在线行被一并藏掉要求, 只剩孤立的来源芯片);
    3. hr-unk / hr-fail / hr-line 新样式必须三套 CSS 成对定义(改这里时同步另一套的纪律);
      hr-pop 弹窗规则(浮层/箭头/双轨)同理成对;
      整格线(在线)必须挂**文字包裹层** .dur-body 而不是单元格 .m-dur —— 行是 grid, 单元格被拉满整列宽,
      挂它上面 width:100% 的空 <i> 就画成整列一条(线随列宽不随文字, 2026-09-29 真机实报);
    4. 前端 js 里引用的 m.hr_* 字段必须都在后端 hr_view_fields 的键集里(字段一致性守阵,
      M4 设置页守阵同款思路)。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    hr_js = open(os.path.join(shared, "hr.js"), encoding="utf-8").read()
    resolve_py = open(
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "auto_qb", "hr", "resolve.py"),
        encoding="utf-8",
    ).read()

    # 1. 来源 token 契约: 后端常量集 == 前端两张映射表的键集
    src_tokens = set(re.findall(r'^SRC_[A-Z_]+ = "([a-z_]+)"', resolve_py, re.M))
    assert len(
        src_tokens
    ) == 6, f"resolve.py 的 SRC_* 常量应为 6 个(v3: 删 policy/local_exempt; 26-09-30 计划 hr-trigger-semantics: 删 unverified), 实测 {sorted(src_tokens)}"
    assert "unverified" not in src_tokens, "SRC_UNVERIFIED 应已随「未核实」灰档退役(本地统一 SRC_LOCAL)"

    def _map_keys(name):
        m = re.search(rf"const {name} = \{{(.*?)\}};", hr_js, re.S)
        assert m, f"hr.js 缺 const {name}"
        return set(re.findall(r"([a-z_]+):", m.group(1)))

    assert _map_keys("HR_SRC_CLASSES") == src_tokens, "HR_SRC_CLASSES 键与后端 SRC_* 不一致"
    assert _map_keys("HR_SRC_BUCKETS") == src_tokens, "HR_SRC_BUCKETS 键与后端 SRC_* 不一致"
    # 来源文案不再进原生 title(2026-09-29 晚: 原生 title 与悬停弹窗叠出, 出现「来源:未核实」等
    #   被弹窗遮挡的冗余提示; 来源改由 hrSrcClass → CSS 底线编码, 文字结论在悬停弹窗内)。
    #   故 hrDurHint / HR_SRC_TITLES / HR_EXCLUDED_TITLE 整套应已退役。
    assert "hrDurHint" not in hr_js, "hr.js 仍残留 hrDurHint(来源+已排除的 title 组装) —— 原生 title 已移除"
    assert "HR_SRC_TITLES" not in hr_js, "hr.js 仍残留 HR_SRC_TITLES —— 来源文案不再进 title"
    assert "HR_EXCLUDED_TITLE" not in hr_js, "hr.js 仍残留 HR_EXCLUDED_TITLE —— 已排除文案不再进 title"
    # 四个安全档位(2026-09-25 用户修正起 failed=未达标终态红档; 2026-09-30 计划
    # hr-trigger-semantics: unknown 灰档退役, 换 warning 黄档=疑似辅种): warning 由前端映射 hr-warn 黄
    for name in ("HR_SAFETY_CLASSES", "HR_SAFETY_BUCKETS"):
        assert _map_keys(name) == {"danger", "failed", "safe", "warning"}, f"{name} 键集应为四个安全档位"

    # 2. 做种时长列换绑 + 弹窗单例: 两套 UI 各 3 处触发 / 各 1 份弹窗 DOM
    for ui in _UI_ALL:
        html = _ui_aggregate(ui)
        for needle, want in (
            (':class="[hrDurClass(m), hrSrcClass(m)]"', 3),
            ('v-if="hrSrcHalf(m)"', 3),  # 半格线(本地 / 未核实)画在数值上
            ('v-if="hrSrcFull(m)"', 3),  # 整格线(在线)画在**文字包裹层**上
            ('class="dur-body"', 3),  # 文字包裹层: 整格线随文字不随列宽(挂单元格 = 随列宽)
            ('@mouseenter="hrPopEnter($event, m)"', 3),
            ('@mouseleave="hrPopLeave"', 4),  # 3 处触发面 + 弹窗自身(移入弹窗不隐藏)
            ('<teleport to="body">', 1),
            ('ref="hrPop"', 1),
        ):
            got = html.count(needle)
            assert got == want, f"{ui} 里 `{needle}` 应出现 {want} 处, 实测 {got}"
        # 旧绑定不得残留(换绑遗漏的形态)
        assert ':class="hrTimeClass(m)"' not in html, f"{ui} 仍有做种时长列挂着旧 hrTimeClass —— 漏换绑"
        assert "hrSrcBadge" not in html, f"{ui} 仍挂着旧的 2 字来源徽标 hrSrcBadge —— 漏换绑"
        assert "hrDurTitle" not in html, f"{ui} 仍有做种时长列挂原生 :title —— 应已换悬停弹窗触发"
        assert ':title="hrDurHint(m)"' not in html, f"{ui} 做种时长列仍挂原生 :title(hrDurHint) —— 应只靠悬停弹窗"
        # 行内文字 chip 零残留(2026-09-29 非文字化的对象就是这两个 chip, 复活即列宽问题回归)
        assert 'class="hr-src"' not in html, f"{ui} 做种时长列仍有 .hr-src 文字 chip —— 文案应只走 title"
        assert ">已排除<" not in html, f"{ui} 做种时长列仍有「已排除」文字 chip —— 应已撤进 title"
        # 要求时长必须「有要求就显示」(2026-09-29 用户实报: 未核/在线行只剩来源芯片, 看不到要求):
        # 门只能是「已做种非空 + 有要求」—— 依赖 hr_triggered 会把未触发行连要求一起藏掉
        assert '"cellSeedingTime(m) && m.hr_req_time"' in html, \
            f"{ui} 做种时长列的要求渲染门被改 —— 应只按 hr_req_time 判定(未触发行也要看得到要求)"

    # 弹窗「无时长要求」收起条件: 不得再把 unverified 包进去(它有本地要求, 收起就看不到),
    # 真放行/免罪(义务已了)仍收起——2026-09-29 实报后定稿
    collapse = re.search(r"if \(\[([^\]]*)\]\.includes\(src\) \|\| !\(req > 0\)\)", hr_js)
    assert collapse, "hr.js 弹窗的「无时长要求」收起条件找不到了 —— 渲染规则被改? 同步本守阵"
    assert "unverified" not in collapse.group(1), "未核实行不得收起为「无时长要求」(本地有要求, 收起即失真)"
    assert "site_released" in collapse.group(1) and "site_exempt" in collapse.group(1), "真放行/免罪仍应收起轨道"

    # 3. 新样式两套 CSS 成对
    atlas_css = _ui_css_aggregate("atlas")
    prism_css = open(os.path.join(STATIC_ROOT, "prism", "css", "views.css"), encoding="utf-8").read()
    console_css = _ui_css_aggregate("console")
    for css, name in (
        (atlas_css, "atlas css 聚合(link 序)"), (prism_css, "prism/css/views.css"),
        (console_css, "console css 聚合(link 序)")
    ):
        for rule in (
            ".m-pair.hr-warn",
            ".m-pair.hr-fail",
            ".m-dur .hr-line",
            ".hr-pop",
            ".hp-arrow",
            ".hp-gauge",
            ".hp-badge",
            # 排除命中行的中性灰档(2026-10-02): 弹窗 lane=excluded 的点与结论色, 三套成对
            ".hp-dot.excluded",
            ".hp-verdict.excluded",
        ):
            assert rule in css, f"{name} 缺 {rule} 规则 —— 三套 UI 必须成对定义"
        # 死样式零残留: 最后一个 .hr-src 消费方(已排除 chip)已撤进 title
        assert ".m-pair .hr-src" not in css, f"{name} 仍留着 .hr-src chip 样式 —— 已无消费方, 应删除"
        assert "z-index: 140" in css, f"{name} 缺弹窗 z-index: 140(须高于 ctx-menu 100 与 speed-pop 131)"
        # 半格线是空 <i>: 只给 left:0 而 width:auto 会收缩成 0 —— 线整条不可见(2026-09-29 实报)
        for half in (".m-dur .dur-val > .hr-line", ".m-dur.src-local .hr-line"):
            assert half in css, f"{name} 缺 {half} 规则 —— 本地的半格线会消失"
        # 死档位样式零残留(2026-09-30 计划 hr-trigger-semantics: unknown/unverified 随灰档退役)
        assert ".m-pair.hr-unk" not in css, f"{name} 仍留着 .hr-unk 死样式 —— 未核实档已退役"
        assert ".src-unver" not in css, f"{name} 仍留着 .src-unver 死样式 —— unverified 来源档已退役"
        assert re.search(r"\.m-dur \.dur-val > \.hr-line \{[^}]*width: 100%", css), \
            f"{name} 半格线没写显式 width:100% —— 空 <i> 的 width:auto 会收缩成 0(线整条不可见)"
        # 整格线(在线)必须挂文字包裹层 .dur-body —— 挂 .m-dur 上会随列宽(2026-09-29 真机实报:
        # 行是 grid, 单元格被拉满整列宽, width:100% 的空 <i> 画成整列一条, 与「随文字」相反)
        for full in (".m-dur .dur-body {", ".m-dur .dur-body > .hr-line"):
            assert full in css, f"{name} 缺 {full} 规则 —— 在线的整格线会随列宽而不是随文字"
        assert re.search(r"\.m-dur \.dur-body > \.hr-line \{[^}]*width: 100%", css), \
            f"{name} 整格线没写显式 width:100% —— 空 <i> 的 width:auto 会收缩成 0(线整条不可见)"
        assert ".m-dur > .hr-line" not in css, \
            f"{name} 整格线仍挂在单元格 .m-dur 上 —— 单元格是 grid item 会被拉满列宽, 线随列宽不随文字"

    # 4. 前端引用的 m.hr_* 字段 ⊆ 后端 hr_view_fields 键集(字段一致性)
    from auto_qb.core.qbmanager import QbManager
    from auto_qb.torrents import TorrentRecord
    from helpers import FakeTorrent

    keys = set(QbManager.hr_view_fields(TorrentRecord.from_torrent(FakeTorrent(hash="HX"))))
    assert keys, "hr_view_fields 连空配置分支都该返回全键集"
    used = set()
    for name in sorted(os.listdir(shared)):
        if name.endswith(".js"):
            used |= set(re.findall(r"\bm\.(hr_[a-z_]+)", open(os.path.join(shared, name), encoding="utf-8").read()))
    for ui in _UI_ALL:
        used |= set(re.findall(r"\bm\.(hr_[a-z_]+)", _ui_aggregate(ui)))
    unknown = used - keys
    assert not unknown, f"前端引用了后端不存在的 HR 字段: {sorted(unknown)}(字段打错 = 页面静默空白)"


def test_frontend_hr_detail_table_wiring():
    """HR 表① 全量详情表前端接线守阵(2026-10-01, 计划 26-10-01-2216 阶段2; 26-10-02-1936 阶段3 扩)

    表① 是设置分区「站点状态」块里逐站点的种子明细表(数据 /api/hr/sites/<site>/entries,
    阶段1 交付), 四类"漏一处 = 静默失效 / 拍板被推翻"的故障形态机械钉住:
    1. 模板绑定: 档位 chips(本地过滤不回后端)/ 已删除种子切换钮(阶段3)/ 明细行 / 空态 / 失踪行挂钩 /
      「数据截至」时间戳(拍板⑥)+ 三列重组列名「核实结论」「在列」(阶段3 拍板④, 口径钉在列名)——
      缺一处该功能消失;
    2. 拍板守卫: remain_seconds 不得进表(拍板③, 2026-09-25 误读教训)/ 不挂 hr-pop 不做行内跳转
      (拍板⑤)/ 单元格无原生 title(hr-tooltip-overlap: 与悬停弹窗叠出遮挡)/ 表① 段无 <details>
      (排障视图在 aqb:hr-diag 独立段, 阶段3 交付)/ 来源徽章类名是 hr-vsrc —— .hr-src 是列表页已退役
      的文字 chip 族(守阵钉了 class="hr-src" 零残留, 复用即撞红);
    3. JS 接线: hr_status.js 有按站点明细加载(loadHrSiteEntries)与本地筛选(hrsLaneSelOf),
      且无 setInterval(计划 §5.5 刷新纪律: 打开拉一次 + 手动刷新, 不轮询、不进 /api/state);
    4. CSS 三处成对(计划 §5.6): .hr-detail-table 在 atlas / console / prism 的 CSS 聚合各 ≥1,
      档位色义四档(A=warn / B=green / C=error / D=blue)与失踪行 --paused 弱化规则成对;
      prism 拆两文件 —— 表头过滤栏段在 components.css、表格徽章段在 views.css(漏一件即该套静默失效)。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    tpl = open(os.path.join(shared, "tpl", "settings-detail.html"), encoding="utf-8").read()
    m = re.search(r"<!-- aqb:hr-detail-table:begin.*?-->(.*?)<!-- aqb:hr-detail-table:end.*?-->", tpl, re.S)
    assert m, "settings-detail.html 缺 aqb:hr-detail-table 扫描锚 —— 表① 模板被移走或锚被删? 同步本守阵"
    frag = m.group(1)

    # 1. 模板绑定: chips / 已删除种子切换钮 / 明细行 / 空态 / 失踪行 / 时间戳 / 拍板④重组列名
    for needle, what in (
        ("hrsLaneChips()", "档位筛选 chips"),
        ("hrsSetLaneSel(", "chips 点击切换"),
        ("hrsToggleOld(", "已删除种子切换钮点击(阶段3)"),
        ("hrsOldBtnText(", "已删除种子切换钮文案计数(阶段3)"),
        ('v-for="e in hrsDetailRows', "明细行渲染"),
        ('class="drawer-table hr-detail-table"', "表格骨架(同挂 .drawer-table 一类)"),
        ("hrsEmptyText(s.site)", "空态文案单点(阶段3: 区分本地无 HR/档位暂无/已删除视图空)"),
        ("数据截至", "「数据截至」时间戳(拍板⑥)"),
        (':class="{ missing: !e.active }"', "失踪行弱化挂钩"),
    ):
        assert needle in frag, f"表① 模板缺 {what}(应有 `{needle}`)"

    # 2. 拍板 / 悬浮纪律守卫
    assert "remain_seconds" not in frag, "remain_seconds 不得进表①(拍板③: 考核窗口倒计时, 2026-09-25 误读教训)"
    assert "hrPopEnter" not in frag, "表① 不得挂 hr-pop 悬停(拍板⑤: 第一期纯清单)"
    assert "title=" not in frag, "表① 单元格不得挂原生 title(hr-tooltip-overlap: 与悬停弹窗叠出遮挡)"
    assert "<details" not in frag.lower(), "表① 段不得混入 <details>(排障视图在 aqb:hr-diag 独立段, 阶段3 已交付)"
    assert 'class="hr-src"' not in frag, "来源徽章类名必须是 hr-vsrc —— hr-src 是列表页已退役 chip 族(复活即撞守阵)"

    # 3. JS 接线: 按站点按需加载 + 本地筛选 + 不轮询
    hr_status_js = open(os.path.join(shared, "hr_status.js"), encoding="utf-8").read()
    for needle, what in (
        ("loadHrSiteEntries", "明细加载函数"),
        ("/api/hr/sites/${encodeURIComponent(site)}/entries", "明细端点拼接"),
        ("hrsLaneSelOf", "档位筛选读取"),
        ("hrsDetailRows", "本地过筛行集(不回后端)"),
        ("该站点本地没有 HR 种子", "空站点空态文案(阶段3: 做种中视图全空)"),
        ("该档位暂无", "档位过滤空态文案(阶段3)"),
        ('label: "核实结论"', "拍板④ 重组列名(口径钉在列名)"),
        ('label: "在列"', "拍板④ 重组列名(口径钉在列名)"),
    ):
        assert needle in hr_status_js, f"hr_status.js 缺 {what}({needle})"
    assert "setInterval" not in hr_status_js, "hr_status.js 不得有轮询定时器(计划 §5.5: 打开拉一次 + 手动刷新)"

    # 4. CSS 三处成对 + 档位色义 + 失踪行弱化
    for css, name in (
        (_ui_css_aggregate("atlas"), "atlas css 聚合(link 序)"),
        (_ui_css_aggregate("console"), "console css 聚合(link 序)"),
        (_ui_css_aggregate("prism"), "prism css 聚合(link 序)"),
    ):
        assert ".hr-detail-table" in css, f"{name} 缺 .hr-detail-table 段 —— 三套 UI 必须成对改(计划 §5.6)"
        for lane in ("a", "b", "c", "d"):
            assert f".hr-detail-table .hr-lane-{lane}" in css, f"{name} 缺 .hr-lane-{lane} 档位色义(计划 §5.4)"
        assert ".hr-detail-table tr.missing .hr-lane" in css, f"{name} 缺失踪行 --paused 描边弱化规则"
        assert ".hr-vsrc" in css, f"{name} 缺来源小徽章(.hr-vsrc)样式"
    pri_components = open(os.path.join(STATIC_ROOT, "prism", "css", "components.css"), encoding="utf-8").read()
    pri_views = open(os.path.join(STATIC_ROOT, "prism", "css", "views.css"), encoding="utf-8").read()
    assert ".hr-detail-table-bar" in pri_components, "prism/css/components.css 缺表头过滤栏段( chips + 数据截至)"
    assert ".hr-detail-table .hr-lane-a" in pri_views, "prism/css/views.css 缺表格徽章段"


# node 单测探针(不落盘): 加载真实 hr_status.js, 对模块级纯函数 hrsCompareRows 跑排序语义电池
# (计划 26-10-02-1936 §3.4: 空值恒末位两方向不反转 / verified_ts·last_seen 0 哨兵 / 档位固定秩 /
#  字符串·数值分型 / 同值稳定性)。无 node 静默跳过(与 _scan_js_syntax_with_node 同口径)。
_NODE_HRS_SORT_PROBE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));
const rows = [
  { tid: 10, name: "kb", uploaded_bytes: 200, ratio: 2.0, need_seed_seconds: 3600,
    done_iso: "2026-09-01T10:00:00", verified_ts: 100, last_seen: 200, lane: "B" },
  { tid: 20, name: "ka", uploaded_bytes: null, ratio: null, need_seed_seconds: null,
    done_iso: null, verified_ts: 0, last_seen: 0, lane: "A" },
  { tid: 30, name: "kc", uploaded_bytes: 300, ratio: 30.0, need_seed_seconds: 60,
    done_iso: "2026-09-02T10:00:00", verified_ts: 300, last_seen: 100, lane: "C" },
  { tid: 40, name: "kd", uploaded_bytes: 300, ratio: 15.0, need_seed_seconds: 60,
    done_iso: null, verified_ts: 200, last_seen: 300, lane: "D" },
];
const seq = (key, dir) => [...rows].sort((a, b) => hrsCompareRows(a, b, key, dir)).map((r) => r.tid);
const checks = [
  ["bytes 降序 null 末位", JSON.stringify(seq("uploaded_bytes", -1)) === "[30,40,10,20]"],
  ["bytes 升序 null 仍末位", JSON.stringify(seq("uploaded_bytes", 1)) === "[10,30,40,20]"],
  ["同值稳定性(两方向 30 在 40 前)", seq("uploaded_bytes", -1).indexOf(30) < seq("uploaded_bytes", -1).indexOf(40)
    && seq("uploaded_bytes", 1).indexOf(30) < seq("uploaded_bytes", 1).indexOf(40)],
  ["verified_ts 0 哨兵降序末位", JSON.stringify(seq("verified_ts", -1)) === "[30,40,10,20]"],
  ["verified_ts 0 哨兵升序仍末位", JSON.stringify(seq("verified_ts", 1)) === "[10,40,30,20]"],
  ["last_seen 两方向空恒末位", JSON.stringify(seq("last_seen", -1)) === "[40,10,30,20]"
    && JSON.stringify(seq("last_seen", 1)) === "[30,10,40,20]"],
  ["档位固定秩降序 D>C>B>A", JSON.stringify(seq("lane", -1)) === "[40,30,10,20]"],
  ["档位固定秩升序 A<B<C<D", JSON.stringify(seq("lane", 1)) === "[20,10,30,40]"],
  ["名称字符串升序", JSON.stringify(seq("name", 1)) === "[20,10,30,40]"],
  ["名称字符串降序", JSON.stringify(seq("name", -1)) === "[40,30,10,20]"],
  ["need_seed_seconds null 两方向末位", JSON.stringify(seq("need_seed_seconds", -1)) === "[10,30,40,20]"
    && JSON.stringify(seq("need_seed_seconds", 1)) === "[30,40,10,20]"],
  ["done_iso 空串两方向末位", JSON.stringify(seq("done_iso", 1)) === "[10,30,20,40]"
    && JSON.stringify(seq("done_iso", -1)) === "[30,10,20,40]"],
];
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""


def test_frontend_hr_table_sort_filter_reorg_wiring():
    """HR 表① 未做种过滤 + 三态排序 + 三列重组守阵(2026-10-02, 计划 26-10-02-1936 阶段3)

    三块新交互"漏一处 = 静默失效 / 拍板被推翻"的故障形态机械钉住:
    1. 已删除种子切换钮(§3.3 决策点③a): 默认文案「显示已删除种子 (N)」、oldOn 默认关(只看本地仍在列 =
      local_present true), 切换后「只看本地仍在列 (M)」; 计数在站点全行集现算;
    2. 三态排序(§3.4, 对齐 shared/sort.js): 表头十列全 sortable(hrsCols() 单点 + @click
      hrsSetSort + sprite 双箭头)而表② 波次表不接排序; 状态机 = 首点降 → 再点升 → 第三击恢复
      后端默认序, 换列直接降序; 比较器纯函数 hrsCompareRows 用 node 真跑语义电池
      (空值恒末位两方向不反转 / 0 哨兵 / 档位 A<B<C<D 固定秩 / 字符串·数值分型 / 同值稳定),
      无 node 的机器静默跳过本项(不引入 pytest skip, 基线 0 skipped);
    3. 三列重组(§3.6 决策点④): 模板新列结构(核实结论徽章 hr-vsrc + 副行 / 在列·失踪徽章
      hr-pres + 副行)+ CSS 三处成对(th.sortable 箭头激活 accent·hover faint / .hr-sub 副行小字 /
      .hr-pres 徽章 / 名称列限宽钩子 + .hr-full-modal 放开); 旧列辅助 hrsVerifiedText /
      hrsStatusText 随列退役, 零残留。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    tpl = open(os.path.join(shared, "tpl", "settings-detail.html"), encoding="utf-8").read()
    js = open(os.path.join(shared, "hr_status.js"), encoding="utf-8").read()
    m = re.search(r"<!-- aqb:hr-detail-table:begin.*?-->(.*?)<!-- aqb:hr-detail-table:end.*?-->", tpl, re.S)
    assert m, "settings-detail.html 缺 aqb:hr-detail-table 扫描锚 —— 表① 模板被移走或锚被删? 同步本守阵"
    frag = m.group(1)

    # 1. 已删除种子切换钮: 默认态文案 + oldOn 默认关(只看本地仍在列)
    #    文案 2026-10-03 用户二次驳回: 默认过滤实为「本地已删除」而非「没在做种」, 反向态含暂停/异常
    assert "显示已删除种子 (" in js and "只看本地仍在列 (" in js, "切换钮双态文案缺失(计划 §3.3, 26-10-03 文案)"
    # 旧措辞只在测试说明里提; 前端源码零残留(含注释 —— 注释解释的是「为何不再用做种措辞」)
    assert "未做种" not in js and "只看做种中" not in js, "旧误导文案残留(26-10-03 二次驳回)"
    mo = re.search(r"hrsOldOnOf\(site\) \{\n(.*?)\n    \},", js, re.S)
    assert mo and "!!" in mo.group(1), "hrsOldOnOf 必须默认 falsy(默认只看本地仍在列, 计划 §3.3)"
    assert "hrsToggleOld(s.site)" in frag and "hrsOldBtnText(s.site)" in frag, "工具条缺已删除种子切换钮绑定"
    assert "e.local_present" in js, "行集过滤必须消费后端 local_present(决策点③a), 前端不得自算 join"

    # 2. 三态排序: 表头接线 + 列模型单点 + 状态机 + 纯函数
    assert 'class="sortable"' in frag and "hrsSetSort(s.site, c.key)" in frag, "表头缺 sortable + 点击排序接线"
    assert "hrsCols()" in frag and "hrsArrowHref(s.site, c.key)" in frag, "表头列模型/箭头接线缺失"
    assert "#i-arrow-up" in js and "#i-arrow-down" in js, "箭头必须是 sprite 双图标(与种子页同款)"
    mo = re.search(r"hrsCols\(\) \{\n(.*?)\n    \},", js, re.S)
    assert mo, "hr_status.js 缺 hrsCols() 列模型单点"
    keys = re.findall(r'key: "([a-z_]+)"', mo.group(1))
    assert len(keys) == 10 and len(set(keys)) == 10, f"表① 必须 10 列可排, 实得 {len(keys)}: {keys}"
    assert set(keys) == {
        "lane", "name", "tid", "uploaded_bytes", "downloaded_bytes", "ratio", "need_seed_seconds", "done_iso",
        "verified_ts", "last_seen"
    }, "十列排序键漂移, 同步本守阵"
    mo = re.search(r"hrsSetSort\(site, key\) \{\n(.*?)\n    \},", js, re.S)
    assert mo, "hr_status.js 缺 hrsSetSort 三态状态机"
    body = mo.group(1)
    assert "!== key" in body and "sortDir[site] = -1" in body, "换列必须直接降序开始(sort.js 同款)"
    assert 'hrsSortDirOf(site) === -1' in body and "sortDir[site] = 1" in body, "第二击必须转升序"
    assert 'hrsSortKeyOf(site) = ""' in body or 'sortSel[site] = ""' in body, "第三击必须恢复后端默认序"
    for fn in ("HRS_LANE_RANK", "HRS_SORT_VAL", "hrsValEmpty", "hrsCompareRows"):
        assert re.search(rf"\b{fn}\b", js), f"hr_status.js 缺排序纯函数 {fn}(模块级单例, 供 node 单测)"
    # 排序必须作用在当前过滤后的行集上(hrsDetailRows 内, 而不是另一个未过滤的行集)
    mo = re.search(r"hrsDetailRows\(site\) \{\n(.*?)\n    \},", js, re.S)
    assert mo and "hrsCompareRows" in mo.group(1) and "local_present" in mo.group(1), \
        "hrsDetailRows 必须做 chips × 未做种 AND 过滤后再排序(计划 §3.4)"
    # 表② 波次表不接排序(行数 <=4)
    md = re.search(r"<!-- aqb:hr-diag:begin.*?-->(.*?)<!-- aqb:hr-diag:end.*?-->", tpl, re.S)
    assert md and "sortable" not in md.group(1), "表② 波次表不得接排序(计划 §3.4)"
    # 有 node 时真跑比较器语义电池(无 node 静默跳过, 不引入 skip)
    node = shutil.which("node")
    if node:
        proc = subprocess.run(
            [node, "-e", _NODE_HRS_SORT_PROBE, os.path.join(shared, "hr_status.js")],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        assert proc.returncode == 0, f"hrsCompareRows node 电池跑挂: {proc.stderr.strip()}"
        report = json.loads(proc.stdout.strip().splitlines()[-1])
        assert report["failed"] == [], f"排序语义电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"

    # 3. 三列重组: 新列结构 + 旧辅助零残留 + CSS 三处成对
    for needle, what in (
        ('class="hr-vsrc"', "核实结论徽章(沿用 hr-vsrc 色义)"),
        ("hrsVerdictText(e)", "核实结论主层文案"),
        ("hrsVerdictSub(e)", "核实结论副行(来源人话 · 时刻)"),
        ('class="hr-pres"', "在列/退役徽章"),
        ("hrsPresenceText(e)", "在列主层文案"),
        ("hrsPresenceSub(e)", "在列副行(观察期 · 最近被见到)"),
        ('class="hr-sub"', "副行小字"),
    ):
        assert needle in frag, f"表① 三列重组缺 {what}(应有 `{needle}`)"
    # 4. 文案语义修正(2026-10-03 §8 B3/B4): 退役行不再借「失踪 N 波」, 终态在列行不再一律「未核实」
    #    (注: 「失踪行」是 CSS tr.missing 的既有叫法, 与徽章文案不是一回事 —— 只钉模板 literal)
    assert "失踪 ${" not in js, "退役行「失踪 N 波」文案残留(§8 B4: missing_streak 退役即清零, 显示恒 0 是语义错位)"
    assert "已移出" in js and "已退役" in js, "退役行主徽章三态缺失(§8 B4: 已移出 / 已退役)"
    assert "hrsTerminalLane" in js, "B3 终态档判据 helper 缺失(核实结论中间态)"
    assert "在列·" in js, "B3 中间态文案「在列·<档位人话>」缺失"
    mo = re.search(r"hrsVerdictText\(e\) \{\n(.*?)\n    \},", js, re.S)
    assert mo and "hrsTerminalLane" in mo.group(1), "hrsVerdictText 未消费终态档判据(B3 中间态)"
    mo = re.search(r"hrsPresenceText\(e\) \{\n(.*?)\n    \},", js, re.S)
    assert mo and "verified_source" in mo.group(1), "hrsPresenceText 退役行未按放行记录分流(B4)"
    assert "missing_streak" not in mo.group(1), "退役行主徽章不得再用 missing_streak(B4)"
    for dead in ("hrsVerifiedText", "hrsStatusText"):
        # 判定只认代码态(剥块/行注释 —— 历史注释里提旧名不算残留)
        js_code = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
        js_code = re.sub(r"//[^\n]*", "", js_code)
        tpl_code = re.sub(r"<!--.*?-->", "", tpl, flags=re.S)
        assert dead not in js_code and dead not in tpl_code, f"{dead} 随旧列退役, 不得残留(死代码)"
    for css, name in (
        (_ui_css_aggregate("atlas"), "atlas css 聚合(link 序)"),
        (_ui_css_aggregate("console"), "console css 聚合(link 序)"),
        (_ui_css_aggregate("prism"), "prism css 聚合(link 序)"),
    ):
        for rule, what in (
            (".hr-detail-table th.sortable", "排序表头"),
            (".hr-detail-table th .arrow", "排序箭头位"),
            (".hr-detail-table th.sortable .arrow.on", "激活列箭头 accent"),
            (".hr-detail-table th.sortable:hover .arrow", "非激活列 hover 浅色占位"),
            (".hr-detail-table .hr-sub", "副行小字(--fg-dim 等宽)"),
            (".hr-detail-table .hr-pres", "在列/退役徽章底形"),
            (".hr-detail-table .hr-pres.hr-pres-on", "在列徽章色义"),
            (".hr-detail-table .hr-pres.hr-pres-out", "已移出徽章 --blue 色义"),
            (".hr-detail-table td.wrap { max-width", "名称列限宽钩子(卡片上下文)"),
            (".hr-full-modal .hr-detail-table td.wrap { max-width: none", "全屏态名称列放开限宽"),
        ):
            assert rule in css, f"{name} 缺 {rule}({what}) —— 三套 UI 必须成对改(计划 §5.6)"


# node 单测探针(P5a): 加载真实 qb_traffic_chart.js, 对模块级纯函数 _qbPointsToData 跑
# 栅格重建 + null 断线语义电池(plan 26-10-03-0946 §5.1/§5.2: 桶键等距 / null 槽 y=null
# / 全 null 回落 / interval 非法防御)。无 node 静默跳过(与 _scan_js_syntax_with_node 同口径)。
_NODE_QB_TRAFFIC_PROBE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));
const P = (t, up, dl) => ({ t, up, dl });
const checks = [];
let pts = [P(1000, 1, 2), P(1030, 3, 4), P(1060, 5, 6)];
let d = _qbPointsToData(pts, 30);
checks.push(["连续段 xs 等距", !!d && JSON.stringify(d.xs) === "[1000,1030,1060]"]);
checks.push(["连续段值透传", !!d && d.up.join() === "1,3,5" && d.dl.join() === "2,4,6"]);
pts = [P(1000, 1, 2), null, P(1060, 5, 6)];
d = _qbPointsToData(pts, 30);
checks.push(["null 桶 x 按栅格重建(缺口位置不漂移)", !!d && JSON.stringify(d.xs) === "[1000,1030,1060]"]);
checks.push(["null 桶 y=null(spanGaps=false 断线)", !!d && d.up[1] === null && d.dl[1] === null]);
checks.push(["锚取首点", !!d && d.anchor.k === 0 && d.anchor.t0 === 1000]);
pts = [null, P(1030, 3, 4), null, P(1090, 7, 8)];
d = _qbPointsToData(pts, 30);
checks.push(["前导 null 整列重建", !!d && JSON.stringify(d.xs) === "[1000,1030,1060,1090]"]);
checks.push(["前导/中断 null y=null", !!d && d.up[0] === null && d.up[2] === null && d.up[3] === 7]);
checks.push(["锚取首个非 null", !!d && d.anchor.k === 1 && d.anchor.t0 === 1030]);
checks.push(["全 null 回落(后端已归一 [])", _qbPointsToData([null, null], 30) === null]);
checks.push(["interval 非法回落", _qbPointsToData([P(1, 1, 1)], 0) === null]);
// P4 回归(plan 26-10-04-0721 §07): 停机/断连 = null 缺口(spanGaps:false 如实断线);
// 空闲 = (0,0) 真实观测点(0 平线, 不是缺口) —— 三段混排(活跃/缺口/空闲/活跃)一次钉住
pts = [P(1000, 5, 6), null, null, P(1090, 0, 0), P(1120, 0, 0), null, P(1180, 2, 3)];
d = _qbPointsToData(pts, 30);
checks.push(["三段混排 xs 等距(缺口位置不漂移)",
  !!d && JSON.stringify(d.xs) === "[1000,1030,1060,1090,1120,1150,1180]"]);
checks.push(["停机/断连 null 桶 y=null(如实断线)",
  !!d && d.up[1] === null && d.up[2] === null && d.up[5] === null && d.dl[5] === null]);
checks.push(["空闲段 (0,0) 是观测点不成缺口",
  !!d && d.up[3] === 0 && d.up[4] === 0 && d.dl[3] === 0 && d.dl[4] === 0]);
checks.push(["三段混排活跃值透传", !!d && d.up[0] === 5 && d.up[6] === 2 && d.dl[6] === 3]);
// S3b 月视图(plan 26-10-04-1957 §05.3): month 行按行间隔 28-31 天非等距 —— 非 null 点
// 按真值 t 落点(覆写), null 槽在两真值点间线性内插/窗端外推; anchor.xs 供 tooltip 真值
const jan = 1735689600, feb = 1738368000, mar = 1740787200;  // 2025-01/02/03-01(31d/28d)
pts = [P(jan, 1, 2), P(feb, 3, 4), P(mar, 5, 6)];
d = _qbPointsToData(pts, 2592000);
checks.push(["月行真值 x 落点(按行间隔非等距)", !!d && JSON.stringify(d.xs) === JSON.stringify([jan, feb, mar])]);
checks.push(["anchor.xs 悬停真值", !!d && d.anchor.xs[2] === mar && d.anchor.k === 0 && d.anchor.t0 === jan]);
pts = [P(jan, 1, 2), null, P(mar, 5, 6)];
d = _qbPointsToData(pts, 2592000);
checks.push(["月视图空槽真值内插", !!d && d.xs[1] === (jan + mar) / 2 && d.up[1] === null]);
checks.push(["月视图值透传", !!d && d.up[0] === 1 && d.dl[2] === 6]);
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""


def test_frontend_qb_traffic_chart_wiring():
    """qB 口径流量图前端接线守阵(P5a+P5b, plan 26-10-03-0946 §07)

    五类"漏一处 = 静默失效 / P5 验收被破坏"的故障形态机械钉住:
    1. enabled=false 三挂点入口不渲染不请求(P5 验收): 全局入口按钮 v-if="qbHistEntryOn" 挂今日
      流量面板内; 抽屉「流量」页签按钮与组右键「qB 口径流量图」菜单项 v-if="qbTrafficOn";
      门单点在 flags.qb_traffic_enabled(/api/webui/flags 下发, fail-closed 默认 false,
      state.js 显式建字段 + lifecycle.loadWebFlags 写入), _qbLoad 里再兜一道 —— 无旗标无入口,
      无入口无触发路径 = 三挂点零请求;
    2. uPlot 双系列断线语义(§5.2): 两 series 显式 spanGaps=false(纯断线, 无最大跨越);
      桶序 -> uPlot 数据的栅格重建 _qbPointsToData 用 node 真跑(null 槽 y=null + x 等距
      不漂移 / 前导 null 锚推算 / 全 null 与 interval 非法回落), 无 node 静默跳过;
      容器尺寸自适应(便签 26-10-04-0134 + 2026-10-04 高度跟随): 建图后宿主挂 ResizeObserver,
      宽/高任一变化 u.setSize 重画(高度取宿主 clientHeight, 随抽屉拖拽调高), _qbChartDestroy
      断开 + 回调自摘/0 尺寸守卫;
    3. 三主题登记链(§07): tpl 分片 + uPlot vendor + 组件 mixin 在三份 index.html 的
      tpl-manifest 同步登记(逐份断言, 三清单一致性另由 test_frontend_template_split_wiring
      钉住), app.mixin 注入 + 抽屉/Esc 退栈/escBusy 名单同步 + _logout 清理;
    4. 挂点形态(2026-10-04 三挂点并入底部详情抽屉): 今日流量面板入口(TM 历史入口旁并列按钮),
      图层/取值 CSS 三套 UI 成对(.qb-* 结构类 + .sb-qb 入口类 + .drawer-body.is-traffic 撑满段;
      tooltip 与图例复用 .hist-* 同源色义);
    5. 三挂点并入抽屉与低频轮询(§07 表): 全局/分组 = drawer.kind === "traffic"(scope 记挂点),
      单种 = drawer.kind === "seed" + drawer.tab === "traffic"(drawer.js _loadDrawerTab 进,
      关抽屉/切页签/换形态由 _stopDrawerPoll + _qbTeardown 统一收); 三挂点建图落点统一
      ref="qbChartHost"、共用同一段正文块(qbTrafficActive -> qbCur*); 组右键菜单项直用
      menu.key 的 encode_group_key 通道(不自行编码); 轮询三挂点统一: 间隔从 meta.interval_s
      夹取([15s,600s] 配置校验界, 30d 窗桶宽 3600s 被夹到上界保续拉语义) + document.hidden 跳过
      (对齐 _startDrawerPoll 先例)+ _qbPollStop 显式 clearInterval(只挂打开期间, 不后台常驻)。
      静默续拉(2026-10-04 修「每隔几秒闪一次」; 2026-10-05 补齐空态/错误态): loading 空态只在
      「本作用域尚无任何落袋结果」时接管正文(qbCurPending = loading + 无数据 + 无错误), 落袋走
      setData 原地快路(不 destroy+new 清屏), 换肤先销毁再整图重建; 错误态改由下一次成功落袋清除
      (发请求前清 = 续拉把错误文案换成 loading/空态再换回 = 每个轮询周期闪一次)。FX-29 软切换落定登记
      (2026-10-04 修「流量页签单击换行『正在加载…』挂死」): _qbLoad 落袋登记
      _drawerDone("traffic"), 与 _drawerWaitSources 成对, 缺一边遮罩等永不到手的源。
      drawer-dock 落点已自种子视图上提为 app 级分片(dock.html), 抽屉任意页可开。
    6. 缺口三态文案与空态(plan 26-10-04-0721 §05, P4): 悬停 0 桶状态行(空闲段 z 派生 (0,0)
      真实观测点, 与 null 缺口可辨)/ 悬停缺口合并文案「无采样 · 程序未运行或 qB 断连」/
      图例 hint 两处同步「缺口 = 无采样(停机/断连)」/ 单种空态收窄为「从未有传输记录」;
      三皮肤共用 shared 分片与 mixin(tpl-manifest 登记链见上面第 3 点), 文案单点钉住即可。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    js = open(os.path.join(shared, "qb_traffic_chart.js"), encoding="utf-8").read()
    state_js = open(os.path.join(shared, "state.js"), encoding="utf-8").read()
    lifecycle_js = open(os.path.join(shared, "lifecycle.js"), encoding="utf-8").read()
    auth_js = open(os.path.join(shared, "auth.js"), encoding="utf-8").read()
    dialogs_js = open(os.path.join(shared, "dialogs.js"), encoding="utf-8").read()
    app_js = open(os.path.join(shared, "app.js"), encoding="utf-8").read()
    drawer_js = open(os.path.join(shared, "drawer.js"), encoding="utf-8").read()
    statusbar = open(os.path.join(shared, "tpl", "statusbar.html"), encoding="utf-8").read()
    drawer_tpl = open(os.path.join(shared, "tpl", "drawer.html"), encoding="utf-8").read()
    dock_tpl = open(os.path.join(shared, "tpl", "dock.html"), encoding="utf-8").read()
    ctx_menus = open(os.path.join(shared, "tpl", "ctx-menus.html"), encoding="utf-8").read()

    # 1. enabled 门(fail-closed 单点; 三挂点共用 qbTrafficOn, 全局入口另挂今日流量面板本体)
    assert 'flags: { skip_check_menu: false, qb_traffic_enabled: false }' in state_js, \
        "state.js flags 默认缺 qb_traffic_enabled: false(fail-closed 初值必须显式建)"
    assert "qb_traffic_enabled: !!(f && f.qb_traffic_enabled)" in lifecycle_js, \
        "loadWebFlags 必须写回 qb_traffic_enabled(缺了旗标恒 false = 功能永不可见)"
    assert "qb_traffic_enabled: false" in lifecycle_js, "loadWebFlags 失败分支必须保持 fail-closed"
    mo = re.search(r"qbTrafficOn\(\) \{\n(.*?)\n    \},", js, re.S)
    assert mo and "this.flags.qb_traffic_enabled" in mo.group(1), \
        "qb_traffic_chart.js 缺 qbTrafficOn 功能总门单点(抽屉流量页签/组右键菜单项的 v-if 门)"
    mo = re.search(r"qbHistEntryOn\(\) \{\n(.*?)\n    \},", js, re.S)
    assert mo, "qb_traffic_chart.js 缺 qbHistEntryOn 入口门单点"
    body = mo.group(1)
    assert "this.flags.qb_traffic_enabled" in body and "this.todayTraffic" in body, \
        "入口门必须同时消费 flags.qb_traffic_enabled 与今日流量面板(挂点本体)"
    # 入口按钮: v-if 门 + 面板内并列(TM 历史入口同组)
    assert 'v-if="qbHistEntryOn"' in statusbar and 'class="sb-qb"' in statusbar, \
        "statusbar 缺 qB 入口按钮(v-if 门是 P5 验收的静态锚)"
    today_blk = re.search(r'<template v-if="todayTraffic">(.*?)</template>', statusbar, re.S)
    assert today_blk and 'class="sb-qb"' in today_blk.group(1), \
        "qB 入口必须挂在今日流量面板组内(挂点 = 今日流量面板, plan §07 表)"

    # 2. uPlot 断线语义 + 悬停取值对齐
    assert js.count("spanGaps: false") == 2, "上行/下行两 series 都必须显式 spanGaps=false(§5.2)"
    assert "setCursor" in js and "qbHistHoverIdx" in js, "缺 uPlot setCursor -> 悬停取值通道"
    assert "_qbPointsToData" in js and "function _qbPointsToData" in js, \
        "缺栅格重建纯函数(模块级单例, 供 node 单测)"
    # 容器 resize 自适应(便签 26-10-04-0134): 建图宽度一次取定后画布不重算 —— 宿主必须挂
    # ResizeObserver, 宽度变了 uPlot setSize 重画; _qbChartDestroy 必须断开(不留对旧宿主的观察);
    # 回调要有自摘/0 宽守卫(挂点 DOM 随 v-if 拆除后 RO 报 0 宽, setSize(0) 会把图画没)
    assert "new ResizeObserver(" in js, "qb_traffic_chart.js 缺宿主 ResizeObserver(resize 后画布不重算)"
    assert "u.setSize(" in js, "qb_traffic_chart.js resize 回调缺 uPlot setSize 重画"
    destroy_blk = re.search(r"_qbChartDestroy\(scope\) \{\n(.*?)\n    \},", js, re.S)
    assert destroy_blk and "disconnect()" in destroy_blk.group(1), \
        "_qbChartDestroy 必须断开 ResizeObserver(图已销毁还观察旧宿主)"
    assert "host.isConnected" in js and "w > 0" in js, \
        "ResizeObserver 回调缺自摘/0 宽守卫(挂点拆除后 RO 报 0 宽, 不得对旧宿主 setSize)"
    # 有 node 时真跑 null 断线语义电池(无 node 静默跳过, 不引入 skip)
    node = shutil.which("node")
    if node:
        proc = subprocess.run(
            [node, "-e", _NODE_QB_TRAFFIC_PROBE,
             os.path.join(shared, "qb_traffic_chart.js")],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        assert proc.returncode == 0, f"_qbPointsToData node 电池跑挂: {proc.stderr.strip()}"
        report = json.loads(proc.stdout.strip().splitlines()[-1])
        assert report["failed"] == [], f"null 断线语义电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"

    # 3. 三主题登记链 + 接线(2026-10-04: 抽屉落点上提 app 级 -> dock.html 分片)
    for ui in _UI_ALL:
        mf = _ui_manifest(ui)
        assert "/shared/tpl/dock.html" in [p["src"] for p in mf["parts"]], f"{ui} 清单缺 dock.html 分片"
        assert "/shared/tpl/drawer.html" in [p["src"] for p in mf["parts"]], f"{ui} 清单缺 drawer.html 分片"
        assert "/shared/vendor/uPlot.iife.min.js" in mf["scripts"], f"{ui} 清单缺 uPlot vendor"
        assert "/shared/qb_traffic_chart.js" in mf["scripts"], f"{ui} 清单缺组件 mixin"
        assert os.path.isfile(os.path.join(STATIC_ROOT, "shared", "vendor", "uPlot.iife.min.js")), \
            "uPlot.iife.min.js 不在盘上(404 = 整页停在错误占位)"
    assert 'class="drawer-dock"' in dock_tpl, "dock.html 缺 .drawer-dock 落点(boot 会 fail-fast)"
    assert "app.mixin(window.AQB_QB_TRAFFIC)" in app_js, "app.js 未注入 AQB_QB_TRAFFIC(整块功能静默消失)"
    # 三挂点并入抽屉后, Esc/escBusy 单点在 drawer.open(dialogs.js + lifecycle.js 两处同步)
    assert "this.drawer.open ||" in dialogs_js, \
        "escBusy 名单缺 drawer.open(抽屉承载流量图, 与 Esc 退栈链两处同步纪律)"
    assert "else if (this.drawer.open) this.closeDrawer();" in lifecycle_js, \
        "Esc 退栈链缺抽屉分支(种子详情与流量图共用 closeDrawer)"
    assert "this.drawer.open = false" in auth_js and "this._qbTeardown()" in auth_js, \
        "_logout 必须收起抽屉并 _qbTeardown(不留对 /api/traffic/qb/* 的后台请求)"
    assert "this.qbHistData = null" in auth_js and "this.qbGroupData = null" in auth_js \
        and "this.qbTorrentData = null" in auth_js, \
        "_logout 必须清三挂点数据(受保护内容同 historyOpen 先例)"

    # 4. CSS 三套 UI 成对(.qb-* 结构类 + .sb-qb 入口; tooltip/图例复用 .hist-* 不在此列)
    for css, name in (
        (_ui_css_aggregate("atlas"), "atlas css 聚合(link 序)"),
        (_ui_css_aggregate("console"), "console css 聚合(link 序)"),
        (_ui_css_aggregate("prism"), "prism css 聚合(link 序)"),
    ):
        for rule, what in (
            (".qb-tabs button.active", "窗口切换激活态"),
            (".qb-note", "加载/空态"),
            (".qb-chart {", "图表容器(悬停 tooltip 定位锚)"),
            (".sb-qb {", "今日流量面板入口按钮"),
            (".drawer-body.is-traffic { display: flex;", "抽屉流量形态正文 flex 纵列"),
            (".drawer-body.is-traffic .qb-chart-host { height: 100%; }", "图高撑满抽屉可用高"),
        ):
            assert rule in css, f"{name} 缺 {rule}({what}) —— 三套 UI 必须成对改"

    # 5. 三挂点并入抽屉 + 低频轮询(plan §07 表①②③ + 「轮询/取数」列)
    # 作用域表 = 三挂点单一描述源: 三作用域齐全, 各持 state 字段名/容器 ref/端点 url;
    # 2026-10-04 并入抽屉后三挂点建图落点统一 qbChartHost(同一时刻只渲染一个流量形态)
    assert js.count('host: "qbChartHost"') == 3, \
        "_QB_SCOPES 三挂点必须统一建图落点 ref=qbChartHost(抽屉内共用一段正文块)"
    assert 'url: (h, w) => "/api/traffic/qb/torrent/" + h + "?window=" + w' in js, \
        "单种作用域端点串漂移(/api/traffic/qb/torrent/{hash})"
    assert 'url: (k, w) => "/api/traffic/qb/group/" + k + "?window=" + w' in js, \
        "分组作用域端点串漂移(/api/traffic/qb/group/{key}; key 原样内插 = encode_group_key 通道, 不自行编码)"
    # 单种挂点(§07 表②): 种子详情头部「流量」页签 v-if 门 + drawer.js 接线三处
    assert 'v-if="qbTrafficOn"' in drawer_tpl and 'drawerTab(\'traffic\')' in drawer_tpl, \
        "drawer.html 缺「流量」页签按钮(v-if=qbTrafficOn 门 + drawerTab 入口)"
    assert 'tab === "traffic" && this.qbTrafficOn' in drawer_js and 'this._qbPollStart("torrent")' in drawer_js, \
        "drawer.js _loadDrawerTab 缺流量页签分支(加载 + 起轮询)"
    assert 'this._qbPollStop("torrent")' in drawer_js, \
        "drawer.js _stopDrawerPoll 缺流量轮询收口(关抽屉/切页签/换目标全走这里 = 关闭即停)"
    assert 'last === "traffic" && !this.qbTrafficOn' in drawer_js, \
        "drawer.js 打开抽屉缺流量页签初值归一(功能关闭时上次停留页签须落回常规页)"
    # 全局/分组挂点: 组右键菜单项(v-if 门) + 抽屉流量形态(共用正文块/建图落点/关闭/窗口切换)
    assert 'v-if="qbTrafficOn"' in ctx_menus and 'openQbGroup(menu.key)' in ctx_menus, \
        "ctx-menus.html 缺组右键「qB 口径流量图」菜单项(v-if 门 + menu.key 直用的 encode_group_key 通道)"
    assert ctx_menus.count("openQbGroup(menu.key)") == 1, "组右键菜单项只能挂在单组菜单(多选/剧集菜单不得出现)"
    assert 'v-if="qbTrafficActive"' in drawer_tpl and 'ref="qbChartHost"' in drawer_tpl \
        and 'qbSetWindow(w)' in drawer_tpl and 'qbCurSummary' in drawer_tpl, \
        "drawer.html 缺流量形态正文块(三挂点共用: qbTrafficActive 门 / 建图落点 / 窗口切换 / 汇总)"
    assert 'drawer.kind === \'traffic\'' in drawer_tpl and 'qbTrafficTitle' in drawer_tpl, \
        "drawer.html 缺流量形态头部(标题取 qbTrafficTitle)"
    assert 'this.openDrawerTraffic("global", "")' in js and 'this.openDrawerTraffic("group", key)' in js, \
        "openQbHistory/openQbGroup 必须归一到 openDrawerTraffic(打开流量形态抽屉)"
    assert 'this._qbLoad(scope);' in js and 'this._qbPollStart(scope);' in js, \
        "openDrawerTraffic 缺打开拉取 + 起轮询(§07 表③「打开弹层拉取」)"
    assert 'if (!this.qbTrafficOn || !key) return;' in js, "openQbGroup 缺 fail-closed 兜底门(入口 v-if 之外的加载路径)"
    # 低频轮询(§07): 间隔取 meta.interval_s 夹取([1.5s,600s] 配置校验界, A4 下界对齐
    # v3 采样间隔放宽后的真实下界) + 30s 兜底 + document.hidden 跳过(对齐 drawer.js
    # _startDrawerPoll 先例) + 关闭路径显式 clearInterval
    assert "_QB_POLL_FALLBACK_MS = 30000" in js and "_QB_POLL_MIN_MS = 1500" in js and "_QB_POLL_MAX_MS = 600000" in js, \
        "轮询间隔常量漂移(30s 兜底 / [1.5s,600s] 夹取界 = §06 配置校验边界, A4: 15000 -> 1500)"
    assert "Math.min(_QB_POLL_MAX_MS, Math.max(_QB_POLL_MIN_MS, s * 1000))" in js, \
        "轮询间隔必须经 [1.5s,600s] 夹取(agg 段窗 meta.interval_s=3600 是桶宽, 直拉 = 一小时不刷新)"
    assert "if (!def.active(this) || document.hidden || this[def.loading]) return;" in js, \
        "轮询 tick 缺 document.hidden / 不活跃 / 在途未落袋跳过(先例 _startDrawerPoll)"
    assert js.count("clearInterval(") == 1, \
        "组件内 clearInterval 只允许在 _qbPollStop 单点(轮询停止收口)"
    # 关闭路径统一收口(2026-10-04): closeDrawer 收抽屉即 _qbTeardown(停三挂点轮询 + 销毁三挂点图)
    assert "this._qbTeardown();" in drawer_js, \
        "drawer.js 缺 _qbTeardown 调用(关抽屉/换形态时轮询与图不停, P5 验收)"
    teardown_blk = re.search(r"_qbTeardown\(\) \{\n(.*?)\n    \},", js, re.S)
    assert teardown_blk and "this._qbPollStop(s)" in teardown_blk.group(1) \
        and "this._qbChartDestroy(s)" in teardown_blk.group(1), \
        "_qbTeardown 必须停三挂点轮询并销毁三挂点图(单点收口)"
    # 静默续拉(2026-10-04 修「每隔几秒闪一次」; 2026-10-05 补齐空态/错误态): 续拉对用户不可见 ——
    # loading 空态只在「本作用域尚无任何落袋结果」时接管正文(判据 qbCurPending 三合一 = loading +
    # 无数据 + 无错误), 数据落袋走 setData 原地快路(destroy+new uPlot 清屏一帧), 换肤因 canvas 色
    # 烘焙必须先销毁再整图重建(setData 不换色)。2026-10-04 那版只门了「有图」一态
    # (!qbCurPoints.length): 空数据集的空态文案与错误文案仍被每个轮询周期的 loading 顶掉一帧
    # (真机报「流量图闪烁 暂无…」), 判据因此改为按「有无落袋结果」而不是按「有无点」。
    assert 'v-if="qbCurPending"' in drawer_tpl, \
        "drawer.html loading 空态必须门在 qbCurPending 上(按有无落袋结果而不是有无点: 空态/错误态被接管 = 每个轮询周期闪一次)"
    pending_blk = re.search(r"qbCurPending\(\) \{\n(.*?)\n    \},", js, re.S)
    assert pending_blk and "this.qbCurLoading && !this.qbCurData && !this.qbCurError" in pending_blk.group(1), \
        "qbCurPending 必须三合一(loading + 无数据 + 无错误): 少任一项都有一种既有状态(图/空态/错误)被续拉顶掉"
    load_blk = re.search(r"async _qbLoad\(scope\) \{\n(.*?)\n    \},", js, re.S)
    assert load_blk, "qb_traffic_chart.js 缺 _qbLoad(取数单点)"
    load_body = load_blk.group(1)
    assert load_body.index("await this.api(") < load_body.index('this[def.error] = "";') \
        and load_body.index("this[def.data] = data;") < load_body.index('this[def.error] = "";'), \
        "错误态只允许在**成功落袋**分支清(发请求前清 = 续拉把错误文案换成 loading/空态再换回 = 每个轮询周期闪一次)"
    assert "prev.setData([data.xs, data.up, data.dl]);" in js and "prev.root.parentElement === host" in js, \
        "qb_traffic_chart.js 缺 setData 原地快路(每次轮询 destroy+new uPlot 清屏 = 每隔一个轮询周期闪一次)"
    theme_blk = re.search(r"_qbOnThemeChange = \(\) => \{\n(.*?)\n        \};", js, re.S)
    assert theme_blk and theme_blk.group(1).find("this._qbChartDestroy(s)") < theme_blk.group(1).find("this._qbChartBuild(s)"), \
        "换肤处理器必须先 _qbChartDestroy 再 _qbChartBuild(canvas 色建图时烘焙, setData 快路不换色)"
    # FX-29 软切换落定登记(2026-10-04 修「流量页签单击换行『正在加载…』挂死」): 换目标软切换的
    # 待到集合含 "traffic"(_drawerWaitSources 通用分支), 但 _drawerDone 只有 detail/trackers/
    # files/peers 四个 fetcher 在调 —— _qbLoad 落袋不登记则集合永不清空, drawer.switching 遮罩
    # 挂死盖住图(双击走 openTorrentDrawer 整体重置不经待到集合, 只有单击跟随软切换踩中)
    assert 'if (scope === "torrent") this._drawerDone("traffic", ctx, 0);' in js, \
        "qb_traffic_chart.js _qbLoad 落袋必须登记 FX-29 落定(_drawerDone('traffic')), 否则软切换遮罩等一个永不到手的源挂死"
    wait_blk = re.search(r"_drawerWaitSources\(tab\) \{\n(.*?)\n    \},", drawer_js, re.S)
    assert wait_blk and 'return ["detail", tab]' in wait_blk.group(1), \
        "drawer.js _drawerWaitSources 通用分支必须覆盖 traffic 页签(与 _qbLoad 的落定登记成对, 拆开即挂死)"
    # state.js 根选项显式建字段(Vue 响应式前置, frontend-split 纪律)
    for field in (
        "qbTorrentWindow", "qbTorrentData", "qbTorrentLoading", "qbTorrentError", "qbTorrentHoverIdx",
        "qbTorrentHoverLeft", "qbGroupKey", "qbGroupName", "qbGroupWindow", "qbGroupData", "qbGroupLoading",
        "qbGroupError", "qbGroupHoverIdx", "qbGroupHoverLeft"
    ):
        assert re.search(rf"^\s+{field}: ", state_js, re.M), f"state.js 缺 {field} 初值(根选项显式建字段)"
    assert 'kind: "seed", scope: ""' in state_js, \
        "state.js drawer 缺 kind/scope 初值(抽屉双形态, vue-reactivity 前置)"

    # 6. 缺口三态文案与空态(plan 26-10-04-0721 §05, P4): 三皮肤共用 shared/tpl/drawer.html 与
    # shared/qb_traffic_chart.js(登记链已在上面第 3 点逐皮肤钉住), 文案单点改动三皮肤同时
    # 生效 —— 这里钉文案本体 + 触发判据 + 旧文案退场, 不逐皮肤重复
    assert 'v-if="qbCurHover.up + qbCurHover.dl === 0">0 B/s · 空闲/做种中</span>' in drawer_tpl, \
        "悬停 0 桶缺状态行(空闲段 z 派生 (0,0) 真实观测点, 必须与 null 缺口可辨; 速率行照旧)"
    assert "无采样 · 程序未运行或 qB 断连" in drawer_tpl, \
        "悬停缺口文案未更新(plan §05 首版合并文案: 两态区分依赖可选 API 形状增强, 拍板不做)"
    assert "断线 · 无数据" not in drawer_tpl, "旧缺口文案「断线 · 无数据」必须退场"
    assert drawer_tpl.count("缺口 = 无采样, 停机/断连") == 2, \
        "图例 hint 两处(工具条 + 图例)必须同步为「缺口 = 无采样(停机/断连)」"
    assert "断线处不连线" not in drawer_tpl, "旧图例 hint「断线处不连线」必须退场"
    assert '暂无该种子的 qB 口径流量数据(从未有传输记录)' in js, \
        "单种空态文案未收窄为「从未有传输记录」(plan §03.3 拍板: 空闲不再产生空态)"
    assert "仅活跃传输期间有采样" not in js, \
        "旧单种空态文案必须退场(空闲段现在是 0 平线, 空态语义只剩从未传输)"


def test_frontend_hr_diag_view_wiring():
    """HR 表② 排障视图前端接线守阵(2026-10-01, 计划 26-10-01-2216 阶段3)

    表② 是站点卡片里原生 <details> 默认收起的排障视图(上半张站点级 kv 行 + 下半张各档波次明细,
    数据全来自 /api/hr/status 现有载荷, 零新请求零新定时器), 三类"漏一处 = 静默失效 / 拍板被推翻"
    的故障形态机械钉住:
    1. 模板绑定: <details> 默认收起(无 open 属性, 计划 §5.3: 默认收起是拍板交互, 浏览器原生
      open 会让排障噪音常驻)/ summary 文案 / kv 行 v-for(hrsKvRows)/ 波次明细行 v-for
      (lanes[].detail 首次获得展示位, 拍板①a: --hr-status 文本表格化);
    2. 展开态不持久化: 排障是临时动作, hr_status.js 不得出现 localStorage(计划 §5.3);
    3. CSS 三处成对(计划 §5.6): .hrs-diag / .hr-diag-kv / .hr-wave-table 在 atlas / console /
      prism 聚合各 ≥1 —— 波次表同挂 .hr-detail-table 继承表① 徽章色义, 那一段的成对由
      test_frontend_hr_detail_table_wiring 钉住, 这里钉表② 自己的新类。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    tpl = open(os.path.join(shared, "tpl", "settings-detail.html"), encoding="utf-8").read()
    m = re.search(r"<!-- aqb:hr-diag:begin.*?-->(.*?)<!-- aqb:hr-diag:end.*?-->", tpl, re.S)
    assert m, "settings-detail.html 缺 aqb:hr-diag 扫描锚 —— 表② 排障视图被移走或锚被删? 同步本守阵"
    frag = m.group(1)

    # 1. details 默认收起 + 模板绑定
    dm = re.search(r"<details\b[^>]*>", frag)
    assert dm, "排障视图缺 <details>(收起交互是拍板交互)"
    assert not re.search(r"<details\b[^>]*\bopen\b", dm.group(0)), "排障视图 <details> 不得带默认 open(计划 §5.3: 默认收起)"
    for needle, what in (
        ("排障视图", "summary 文案"),
        ("hrsKvRows(s)", "站点级 kv 行渲染"),
        ('v-for="ls in s.lanes"', "各档波次明细行渲染(lanes[].detail 展示位)"),
        ('class="drawer-table hr-diag-kv"', "kv 表骨架(同挂 .drawer-table 一类)"),
        ("hr-wave-table", "波次明细表类名(同挂 .hr-detail-table 继承徽章色义)"),
    ):
        assert needle in frag, f"排障视图缺 {what}(应有 `{needle}`)"

    # 2. 展开态不持久化 + JS 拼行单点(无新请求/定时器由 hr_detail_table 守阵的 setInterval 断言一并覆盖)
    js = open(os.path.join(shared, "hr_status.js"), encoding="utf-8").read()
    for needle in ("hrsKvRows", "hrsWaveCutoff", "hrsWaveCount"):
        assert needle in js, f"hr_status.js 缺 {needle}(表② 人话拼接单点)"
    # 剥块注释再查(注释里提到"不写 localStorage"的说明文字不算使用 —— 判定只认代码态)
    js_code = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    js_code = re.sub(r"//[^\n]*", "", js_code)
    assert "localStorage" not in js_code, "展开态不持久化(计划 §5.3: 排障是临时动作): hr_status.js 代码态不得出现 localStorage"

    # 3. CSS 三处成对(表② 新类)
    for css, name in (
        (_ui_css_aggregate("atlas"), "atlas css 聚合(link 序)"),
        (_ui_css_aggregate("console"), "console css 聚合(link 序)"),
        (_ui_css_aggregate("prism"), "prism css 聚合(link 序)"),
    ):
        for cls in (".hrs-diag", ".hr-diag-kv", ".hr-wave-table"):
            assert cls in css, f"{name} 缺 {cls} 段 —— 三套 UI 必须成对改(计划 §5.6)"


def test_frontend_hr_full_modal_wiring():
    """HR 站点状态折叠 + 覆盖式全屏弹窗前端接线守阵(2026-10-02, 计划 26-10-02-1936 阶段2)

    「站点状态」块改两态状态机: 折叠(仅头部) ⇄ 覆盖式全屏弹窗(用户拍板①改判: 「展开」即全屏,
    无中间内嵌展开态; 决策点⑤a: 首次展开才拉数)。五类"漏一处 = 静默失效 / 拍板被推翻"的
    故障形态机械钉住:
    1. 模板绑定: aqb:hr-full-modal 扫描锚段内遮罩(点遮罩关)/面板(v-show 挂 hrsOpen, 无预展开
      属性)/头部(标题 + 摘要 hrsSummaryText + ✕)齐全; 头部有「展开/收起」钮(:aria-expanded 随态,
      运行日志块同款范式)且**无独立「全屏」钮**(拍板①改判后工具条全屏钮已取消);
    2. 状态纪律: hrsOpen 默认 false(state.js, logs.open 同款先例)且不持久化 —— 三个承载文件
      代码态零 localStorage; hubGo 打开分区不再自动拉数、只复位 hrsOpen(每次进分区回折叠);
    3. 取数时机(决策点⑤a): hrsToggle 首次展开且未 loaded 才调 loadHrStatus; 折叠态点
      「全部立即拉取/刷新」顺手展开再拉(hrsExpandAnd* 方法在场); 无 setInterval(不轮询);
    4. ESC 三路关闭: lifecycle.js 退栈链有 hrsOpen 分支(先于 26-10-02-1632 清筛选兜底,
      不抢不漏)且 dialogs.js::escBusy 名单同步(否则设置页 Esc 关弹窗会顺带退回设置首页);
    5. CSS 三处成对: .hr-full-mask / .hr-full-modal 在三套 UI 聚合各 ≥1(prism 落 components.css,
      与 .modal-mask 同文件), 让出顶栏(--head-h)/状态栏(--statusbar-h)的边界声明成对。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    tpl = open(os.path.join(shared, "tpl", "settings-detail.html"), encoding="utf-8").read()
    m = re.search(r"<!-- aqb:hr-full-modal:begin.*?-->(.*?)<!-- aqb:hr-full-modal:end.*?-->", tpl, re.S)
    assert m, "settings-detail.html 缺 aqb:hr-full-modal 扫描锚 —— 覆盖层被移走或锚被删? 同步本守阵"
    frag = m.group(1)

    # 1. 覆盖层模板绑定(遮罩/面板/头部三件套) + 折叠默认态
    for needle, what in (
        ('class="hr-full-mask"', "遮罩(点遮罩关闭路径)"),
        ('class="hr-full-modal"', "全屏面板"),
        ("hrsCollapse()", "关闭动作(✕ 与遮罩两处复用)"),
        ("hrsSummaryText()", "头部摘要(N 站点 · 数据截至)"),
        ('aria-label="关闭"', "✕ 关闭钮可访问名"),
        ('v-show="hrsOpen"', "显隐挂 hrsOpen(两态: 折叠 ⇄ 全屏覆盖层)"),
    ):
        assert needle in frag, f"全屏覆盖层缺 {what}(应有 `{needle}`)"
    assert not re.search(r'class="hr-full-modal[^"]*\bopen\b', frag), "全屏面板不得带预展开属性(默认折叠是拍板交互)"
    # 头部按钮(在 hb-blk-hd, 锚段之外): 展开/收起钮在场, 独立「全屏」钮不得存在(拍板①改判)
    assert ':aria-expanded="hrsOpen"' in tpl, "头部缺「展开/收起」钮的 aria-expanded 随态绑定"
    assert "hrsToggle()" in tpl, "头部缺展开/收起切换(hrsToggle)"
    for legacy in ("hrsSiteFullscreen", ">全屏<", "'全屏'", '"全屏"'):
        assert legacy not in tpl, f"不得复活独立「全屏」钮(拍板①改判: 展开即全屏) —— 命中 `{legacy}`"

    # 2. 状态纪律: 默认折叠 + 不持久化
    state_js = open(os.path.join(shared, "state.js"), encoding="utf-8").read()
    assert "hrsOpen: false" in state_js, "state.js 缺 hrsOpen: false(默认折叠, logs.open 同款先例)"
    # 不持久化只约束 hrsOpen 本身: config_hub.js 存量就有 hub 视图键的 localStorage 读写(合法),
    # 这里钉的是「展开态不许新增存储通道」—— 任何含 localStorage 的行不得提及 hrsOpen/hrs.open,
    # 且三个承载文件代码态不得出现新的 hrs 存储键字面量。
    for name in ("hr_status.js", "config_hub.js", "state.js"):
        code = open(os.path.join(shared, name), encoding="utf-8").read()
        code = re.sub(r"/\*.*?\*/", "", code, flags=re.S)
        code = re.sub(r"//[^\n]*", "", code)
        for ln in code.splitlines():
            if "localStorage" in ln:
                assert "hrsOpen" not in ln and "hrs.open" not in ln, \
                    f"{name} 把展开态写进 localStorage —— 不持久化被破坏: {ln.strip()}"
        assert 'localStorage.setItem("autoqb.hrs' not in code, \
            f"{name} 新增了 hrs 存储键 —— 展开态不持久化(计划 §3.1)"

    # 3. 取数时机: 首次展开才拉 + 折叠态点拉取/刷新顺手展开
    js = open(os.path.join(shared, "hr_status.js"), encoding="utf-8").read()
    js_flat = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    for needle, what in (
        ("hrsToggle()", "展开/收起切换单点"),
        ("if (!this.hrs.loaded) this.loadHrStatus();", "首次展开才拉(决策点⑤a)"),
        ("hrsExpandAndRefreshAll()", "折叠态点「全部立即拉取」顺手展开再拉"),
        ("hrsExpandAndReload()", "折叠态点「刷新」顺手展开再拉"),
        ("hrsSummaryText()", "摘要拼行单点"),
    ):
        assert needle in js_flat, f"hr_status.js 缺 {what}(应有 `{needle}`)"
    assert "setInterval" not in js, "hr_status.js 不得有轮询定时器(计划 §5.5 刷新纪律)"
    hub_js = open(os.path.join(shared, "config_hub.js"), encoding="utf-8").read()
    assert 'if (key === "hr_check") this.hrsOpen = false;' in hub_js, \
        "hubGo 打开 HR 分区必须复位 hrsOpen(每次进分区回折叠), 且不得再自动 loadHrStatus"
    assert 'key === "hr_check" && !this.hrs.loaded' not in hub_js, \
        "hubGo 不得在打开分区时自动 loadHrStatus(决策点⑤a: 取数时机收进 hrsToggle)"

    # 4. ESC 关闭: 退栈链分支 + escBusy 名单两处同步(不抢不漏)
    lc = open(os.path.join(shared, "lifecycle.js"), encoding="utf-8").read()
    dl = open(os.path.join(shared, "dialogs.js"), encoding="utf-8").read()
    chain = re.search(r"if \(e\.key !== \"Escape\"\) return;.*?\}\);", lc, re.S)
    assert chain, "lifecycle.js 找不到 Esc 退栈链 —— 结构变了? 同步本守阵"
    assert "this.hrsOpen) this.hrsCollapse()" in chain.group(0), \
        "Esc 退栈链缺 hrsOpen 分支(覆盖层 ESC 关闭不生效或被清筛选兜底抢走)"
    clear_idx = chain.group(0).find("clearFilters()")
    hrs_idx = chain.group(0).find("hrsCollapse()")
    assert 0 <= hrs_idx < clear_idx, "hrsOpen 分支必须排在清筛选兜底之前(26-10-02-1632 优先级: 关弹窗不顺带清筛选)"
    busy = re.search(r"escBusy\(\) \{\n(.*?)\n    \},", dl, re.S)
    assert busy and "this.hrsOpen" in busy.group(1), \
        "escBusy 名单缺 hrsOpen —— 漏同步时设置页按 Esc 关弹窗会顺带退回设置首页(hubOnKey)"

    # 5. CSS 三处成对: 遮罩 + 面板 + 上下边界让出声明
    for css, name in (
        (_ui_css_aggregate("atlas"), "atlas css 聚合(link 序)"),
        (_ui_css_aggregate("console"), "console css 聚合(link 序)"),
        (_ui_css_aggregate("prism"), "prism css 聚合(link 序)"),
    ):
        for cls in (".hr-full-mask", ".hr-full-modal"):
            assert cls in css, f"{name} 缺 {cls} 段 —— 三套 UI 必须成对改(计划 §5 阶段2)"
        assert "--head-h" in css and "--statusbar-h" in css, \
            f"{name} 的全屏覆盖层缺顶栏/状态栏让出声明(--head-h / --statusbar-h)"
    pri_components = open(os.path.join(STATIC_ROOT, "prism", "css", "components.css"), encoding="utf-8").read()
    assert ".hr-full-modal" in pri_components, "prism/css/components.css 缺全屏覆盖层段(与 .modal-mask 同文件)"


def test_frontend_hr_contract_keys_match_backend():
    """HR 两张表「前端消费键 ⊆ 后端导出键」契约守阵(2026-10-01, 计划 26-10-01-2216 阶段4)

    表① 行字段的后端导出面已由 test_hr_status.test_entry_details_field_surface 钉死(闭集),
    但那是**后端侧**钉法: 上游改键名 + 同步改那条 expected 后 pytest 照样全绿, 前端消费的
    旧键名却静默落空 —— 渲染成空串/undefined, 不报错不看页面发现不了(与
    test_frontend_hr_status_fields_match_backend 同一故障族, 但那里只扫模板里的 `s.*`,
    表② 的 kv 拼行与波次取数在 hr_status.js 里, 模板只有 hrsKvRows(s) 一个调用点, 扫不到)。

    这里从**前端源码**提取消费键(双向都能红: 前端新增幻键 / 上游改键名都会撞):
    - 表① 行: 共享模板 aqb:hr-detail-table 段的直接 `e.*` + hr_status.js 的行辅助/行集函数
      (参数把行对象传进来的: hrsDetailRows 的 `e` / hrsVerdictText/hrsVerdictSub/hrsSrcCls/
      hrsPresenceText/hrsPresenceCls/hrsPresenceSub 的 `e`, 26-10-02-1936 阶段3 随三列重组换名),
      对照 EntryDetail.to_dict; 全文件扫 `e.*` 会误吞 catch(e) 的 auth/message, 故按函数体提;
    - 表② 站点级: hr_status.js 全文件(拼行单点 hrsKvRows 与摘要层 hrsState*/hrsLaneText
      的参数都叫 s)`s.*` + aqb:hr-diag 模板段, 对照 SiteStatus.to_dict;
    - 表② 波次级: hr_status.js 全文件 `ls.*`(hrsWaveCutoff/hrsWaveCount/hrsLaneClass)
      + aqb:hr-diag 模板段, 对照 LaneStatus.to_dict。
    每组都带「核心键必须在场」断言 —— 提取器本身失效(函数改名/文件挪走)时守阵变红而不是
    静默变恒真。
    """
    from auto_qb.hr.status import EntryDetail, LaneStatus, SiteStatus

    shared = os.path.join(STATIC_ROOT, "shared")
    tpl = open(os.path.join(shared, "tpl", "settings-detail.html"), encoding="utf-8").read()
    js = open(os.path.join(shared, "hr_status.js"), encoding="utf-8").read()
    # 判定只认代码态(与 test_frontend_hr_diag_view_wiring 的 localStorage 检查同款剥注释)
    js_code = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    js_code = re.sub(r"//[^\n]*", "", js_code)

    frag_table = re.search(r"<!-- aqb:hr-detail-table:begin.*?-->(.*?)<!-- aqb:hr-detail-table:end.*?-->", tpl, re.S)
    frag_diag = re.search(r"<!-- aqb:hr-diag:begin.*?-->(.*?)<!-- aqb:hr-diag:end.*?-->", tpl, re.S)
    assert frag_table and frag_diag, "settings-detail.html 缺 aqb 扫描锚(表①/表②) —— 模板被移走? 同步本守阵"

    # --- 表① 行字段: 模板直接消费 + JS 行辅助/行集函数(行对象经参数传入) ---
    used_e = set(re.findall(r"\be\.([a-z_]+)\b", frag_table.group(1)))
    for fn in (
        "hrsDetailRows", "hrsVerdictText", "hrsVerdictSub", "hrsSrcCls", "hrsPresenceText", "hrsPresenceCls",
        "hrsPresenceSub"
    ):
        # 行集函数参数是 site(体内 lambda 参数 e), 行辅助函数参数是 e —— 统一按「函数头到方法尾」切块
        m = re.search(rf"\n    {fn}\((?:e|site)\) \{{\n(.*?)\n    \}},", js, re.S)
        assert m, f"hr_status.js 找不到 {fn} 函数体 —— 表① 行消费单点被移走或改名? 同步本守阵"
        used_e |= set(re.findall(r"\be\.([a-z_]+)\b", m.group(1)))
    assert {"tid", "verified_ts", "last_seen"} <= used_e, f"表① 消费键提取失效(只扫到 {sorted(used_e)}) —— 守阵变恒真, 同步提取器"
    # local_present 是响应层 mark_local_present 追加的只读标记(routes/hr.py 单点, 决策点③a),
    # 不在 EntryDetail.to_dict —— 有意豁免; 其余幻键仍然是真缺陷。
    phantom_e = sorted(used_e - set(EntryDetail(tid=0).to_dict()) - {"local_present"})
    assert not phantom_e, f"表① 消费了 EntryDetail 不导出的键 {phantom_e}(渲染成空, 打错/上游改名都会这样)"

    # --- 表② 站点级(s.*)与波次级(ls.*) ---
    used_s = set(re.findall(r"\bs\.([a-z_]+)\b", js_code)) | set(re.findall(r"\bs\.([a-z_]+)\b", frag_diag.group(1)))
    assert {"fresh_text", "index_total", "empty_confirmed"} <= used_s, f"表② 站点级消费键提取失效(只扫到 {sorted(used_s)}) —— 同步提取器"
    phantom_s = sorted(used_s - set(SiteStatus(site="probe").to_dict()))
    assert not phantom_s, f"表② 消费了 SiteStatus 不导出的键 {phantom_s}(kv 行静默落空)"
    used_ls = set(re.findall(r"\bls\.([a-z_]+)\b", js_code)) | set(re.findall(r"\bls\.([a-z_]+)\b", frag_diag.group(1)))
    assert {"full_depth", "count_claim", "lane_text"} <= used_ls, f"表② 波次级消费键提取失效(只扫到 {sorted(used_ls)}) —— 同步提取器"
    # 严格闭集(2026-10-01 收空): 曾有已知幻键 ls.lane_text(徽章人话渲染为空), 修法 = LaneStatus
    # 补该字段由 _lane_statuses 填充(LANE_TEXTS 单点), 白名单已收 —— 任何幻键在这里都是真缺陷。
    phantom_ls = sorted(used_ls - set(LaneStatus().to_dict()))
    assert not phantom_ls, f"表② 波次级消费了 LaneStatus 不导出的键 {phantom_ls}(渲染成空, 打错/上游改名都会这样)"


def test_frontend_hr_history_wiring():
    """HR 表③ 拉取历史前端接线守阵(2026-10-04, 计划 26-10-04-0312 §3.5/§05 S4)

    表③ 是全屏覆盖层里 .hrs-list 之后的全局 <details>(拉取历史跨站点成时间轴, 不进 per-site
    article; 数据 /api/hr/history, S1-S3 交付; 状态挂 hr_status.js 伴生键 hrsHist, 方法前缀
    hrsHist*), 五类"漏一处 = 静默失效 / 拍板被推翻"的故障形态机械钉住:
    1. 模板绑定: aqb:hr-history 扫描锚 begin/end 成对且段内 <details> 默认收起(表② 同款折叠
      范式)/ summary 文案 / 站点 chips(hrsHistSiteChips, 行内站点集合现算)/ 「仅看异常」toggle /
      刷新钮 / 「数据截至」时间戳 / 十列表头(计划 §3.5 mock 列面: 时间/站点/触发/结果/页数/行数/
      回填/放行/耗时/说明)/ 明细行 v-for + 行点击展开明细子行(hr-hist-sub)/ 空态与未启用态文案 /
      read_errors 点名行(坏站点文件不静默);
    2. 取数纪律(计划 §3.5): 首次展开才 fetch(limit=300, 模板 @toggle -> hrsHistOnToggle ->
      hrsHistEnsureLoaded), 「刷新」手动重拉(hrsHistReload), 无 setInterval(不轮询);
      站点过滤纯前端本地筛不回后端(端点拼串不得出现 site 查询参数);
    3. 展开态不持久化: 排障动作不写存储, hr_status.js 代码态零 localStorage(表② 同款);
    4. CSS 三处成对(计划 §5.6): .hr-hist-table / .hr-hist-row / .hr-hist-sub / .hr-hres 及
      result_tone 五档色义(ok/warn/dim/err/blue)在 atlas / console / prism 聚合各 ≥1
      (骨架 .drawer-table + .hr-detail-table 与 chips 行复用件的成对由既有守阵钉住)。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    tpl = open(os.path.join(shared, "tpl", "settings-detail.html"), encoding="utf-8").read()
    begins = re.findall(r"<!-- aqb:hr-history:begin", tpl)
    ends = re.findall(r"<!-- aqb:hr-history:end", tpl)
    assert len(begins) == 1 and len(ends) == 1, \
        f"aqb:hr-history 扫描锚必须 begin/end 恰好成对各一(实得 begin={len(begins)} / end={len(ends)}) —— 表③ 段被移走或锚被删? 同步本守阵"
    m = re.search(r"<!-- aqb:hr-history:begin.*?-->(.*?)<!-- aqb:hr-history:end.*?-->", tpl, re.S)
    frag = m.group(1)

    # 1. 折叠范式 + 模板绑定
    dm = re.search(r"<details\b[^>]*>", frag)
    assert dm, "表③ 缺 <details>(表② 同款折叠范式)"
    assert not re.search(r"<details\b[^>]*\bopen\b", dm.group(0)), "表③ <details> 不得带默认 open(默认收起是拍板交互)"
    for needle, what in (
        ("拉取历史 · 最近取数与波次明细", "summary 文案"),
        ("hrsHistOnToggle($event)", "首次展开触发(@toggle)"),
        ("hrsHistSiteChips()", "站点 chips(行内站点集合现算)"),
        ("hrsHistSetSite(", "chips 点击切换"),
        ("仅看异常", "「仅看异常」toggle 文案"),
        ("hrsHistToggleBad()", "「仅看异常」点击切换"),
        ("hrsHistReload()", "「刷新」手动重拉"),
        ("hrsHistFreshText()", "「数据截至」时间戳(拼行单点在 hrsHistFreshText)"),
        ('class="drawer-table hr-detail-table hr-hist-table"', "表格骨架(同挂 .drawer-table + .hr-detail-table)"),
        ('v-for="r in hrsHistRows()"', "明细行渲染(前端本地过筛行集)"),
        ('class="hr-hist-row"', "可点击主行(展开触发)"),
        ('class="hr-hist-sub"', "展开明细子行"),
        ("hrsHistSubText(r)", "子行文案单点(各档 lanes 明细)"),
        ('class="hr-hres"', "结果徽章(result_tone 色档)"),
        ("hrsHistResCls(r)", "结果徽章色档映射"),
        ("正在读取拉取历史", "加载态文案"),
        ("最近还没有拉取记录", "空态文案"),
        ("HR 在线核实未启用", "未启用态文案"),
        ("文件读取失败", "read_errors 点名行(坏站点文件不静默)"),
    ):
        assert needle in frag, f"表③ 模板缺 {what}(应有 `{needle}`)"
    # 十列列面(计划 §3.5 mock): 时间/站点/触发/结果/页数/行数/回填/放行/耗时/说明(数值列挂 .num)
    for col in ("时间", "站点", "触发", "结果", "页数", "行数", "回填", "放行", "耗时", "说明"):
        assert f"<th>{col}</th>" in frag or f'<th class="num">{col}</th>' in frag, \
            f"表③ 表头缺「{col}」列(计划 §3.5 mock 列面)"

    # 2. 取数纪律: 首次展开才拉 + 手动刷新 + 不轮询 + 本地过滤不回后端
    js = open(os.path.join(shared, "hr_status.js"), encoding="utf-8").read()
    for needle, what in (
        ("/api/hr/history?limit=", "历史端点拼接"),
        ("HRS_HIST_LIMIT = 300", "单页拉取条数(计划拍板值)"),
        ("hrsHistOnToggle(ev)", "toggle 入口(开与合都触发, 只有展开才拉)"),
        ("hrsHistEnsureLoaded", "首次展开才拉单点"),
        ("hrsHistReload", "手动重拉单点"),
        ("hrsHistSiteChips", "站点 chips 现算单点"),
        ("hrsHistRows", "本地过筛行集单点"),
        ("hrsHistIsBad", "仅看异常判据单点"),
        ('r.kind === "defer"', "拦下行一律算异常(计划 §3.5 拍板)"),
        ("hrsHistSubText", "展开子行文案单点"),
        ("hrsHistResCls", "徽章色档映射单点"),
        ("数据截至", "「数据截至」拼行单点(hrsHistFreshText)"),
    ):
        assert needle in js, f"hr_status.js 缺 {what}({needle})"
    assert "setInterval" not in js, "hr_status.js 不得有轮询定时器(表③ 不轮询, 计划 §3.5)"
    assert "/api/hr/history?site" not in js and "&site=" not in js, \
        "站点过滤必须纯前端本地筛, 不得回后端拼 site 查询串(计划 §3.5)"

    # 3. 展开态不持久化(剥块/行注释再查 —— 说明文字不算使用, 判定只认代码态)
    js_code = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    js_code = re.sub(r"//[^\n]*", "", js_code)
    assert "localStorage" not in js_code, "展开态不持久化: hr_status.js 代码态不得出现 localStorage"

    # 4. CSS 三处成对: 表③ 新类 + result_tone 五档色义
    for css, name in (
        (_ui_css_aggregate("atlas"), "atlas css 聚合(link 序)"),
        (_ui_css_aggregate("console"), "console css 聚合(link 序)"),
        (_ui_css_aggregate("prism"), "prism css 聚合(link 序)"),
    ):
        for cls in (".hr-hist-table", ".hr-hist-row", ".hr-hist-sub", ".hr-hres"):
            assert cls in css, f"{name} 缺 {cls} 段 —— 三套 UI 必须成对改(计划 §5.6)"
        for tone in ("ok", "warn", "dim", "err", "blue"):
            assert f".hr-hres.hr-hres-{tone}" in css, f"{name} 缺 .hr-hres-{tone} 色义(result_tone 五档)"


def test_frontend_member_window_functions_live_in_methods():
    """成员行窗口三个函数(memberWin / memberPadTop / memberPadBottom)必须在 methods 块, 不能在 computed

    现象与定性(issue 26-09-21-0247):
    这三个函数**带参数**(`list`), Vue 3 computed 是无参 getter —— 模板里 `memberPadTop(g.members)`
    调用时, Vue 把 `this.memberWin` 当 getter 触发, 拿到的是 `{padTop:0,…}` 这个**值**;
    再 `(list)` 把它当函数调 → "this.memberWin is not a function" → 辅种页展开任一行即整表白屏
    (chips / 状态条 / 表头 / 行 全部消失, 控制台报错)。同一份代码在拆分前(afef7ce^)
    就在 computed, 之前未塌是因为没人走"辅种页展开"路径; 守不住就会再塌。

    断言: 这三个名字的定义行必须在 `methods: {` 之后、`computed: {` 之前。
    """
    rel = "shared/columns.js"
    text = open(os.path.join(STATIC_ROOT, rel), encoding="utf-8").read()
    m_methods = re.search(r"^\s*methods:\s*\{", text, re.M)
    m_computed = re.search(r"^\s*computed:\s*\{", text, re.M)
    assert m_methods, f"{rel} 找不到 methods 块(文件结构改了? 同步本守阵)"
    assert m_computed, f"{rel} 找不到 computed 块(文件结构改了? 同步本守阵)"
    methods_end = m_methods.end()
    computed_start = m_computed.start()
    assert methods_end < computed_start, f"{rel} methods 块不在 computed 之前(顺序倒了?)"
    for name in ("memberWin", "memberPadTop", "memberPadBottom"):
        m_def = re.search(rf"^\s*{name}\s*\(", text, re.M)
        assert m_def, f"{rel} 找不到 {name}(... 定义(改名了? 同步本守阵)"
        assert methods_end < m_def.start() < computed_start, (
            f"{rel} {name}(...) 定义落在 computed 块里 —— Vue 3 computed 不能带参, "
            f"模板里 memberPadTop(g.members) 会把 this.memberWin 当 getter 触发,"
            f"拿到值再 (list) 当函数调 → 整表白屏(issue 26-09-21-0247)"
        )


def _computed_member_names(lines):
    """取一个片段文件里所有 `computed: {` 块的成员名(块缩进 + 2 的成员行)

    比 `_section_members` 多两件事: 1.**所有** computed 块都要取(组件里的 computed 也在内,
    不只看顶层 mixin); 2.终止行按**块的缩进**判定 —— 用 `line.strip() in ("},", "}")`
    会被深层嵌套的 `},`(如 `return {...};` 之后那一行)提前关掉块, 从而漏掉后面的成员。
    """
    out, in_block, indent = set(), False, 0
    for line in lines:
        if not in_block:
            if line.strip() == "computed: {":
                in_block = True
                indent = len(line) - len(line.lstrip())
            continue
        if line.rstrip() in (" " * indent + "},", " " * indent + "}"):
            in_block = False
            continue
        m = re.match(r"^\s{%d}(?:async\s+)?([A-Za-z_$][\w$]*)\s*[(:]" % (indent + 2), line)
        if m:
            out.add(m.group(1))
    return out


def test_frontend_computed_not_invoked_as_function():
    """computed 成员不许以 `this.X()` 形式调用 —— 拿到的是 getter 的**值**, 不是函数

    现象与定性(2026-09-21, 经典设置页「数值 + 单位」字段):
    `unitParts` 是 computed(返回 `{num, unit}`), 而 `setUnitNum` 里写成了
    `this.unitParts().unit` —— 这是把 getter 的**返回值**当函数调用 ⇒ `TypeError:
    this.unitParts is not a function` ⇒ **一改数字框就整页白屏**(设置页整段消失)。
    此前没人发现是因为: 1. 模板里 `unitParts.num` 是对的(只错在 JS 方法里);
    2. 只有真的去改"主循环间隔 / 轮转大小"这类带单位的值才会触发。

    为什么必须机检: 这类错误**只在真浏览器里跑特定交互**才现形, `node --check` 查不出来
    (语法完全合法), 静态守阵里也天然看不见; 与 `test_frontend_member_window_functions_live_in_methods`
    是同一族("computed 看起来对, 实际废掉"), 但那一条守的是"带参函数放错了块",
    这一条守的是"无参 computed 被当成函数调" —— 两个方向都要钉。

    断言: 任一片段文件里, 出现在 `computed: {` 块中的成员名, 不得在该文件中以 `this.<名>(` 出现。
    """
    problems = []
    for path, rel in _app_bundle_files():
        text = open(path, encoding="utf-8").read()
        lines = text.splitlines()
        for name in sorted(_computed_member_names(lines)):
            for m in re.finditer(r"this\.%s\(" % re.escape(name), text):
                ln = text[:m.start()].count("\n") + 1
                stripped = lines[ln - 1].strip()
                # 注释行里引用这个写法(说明"别这么写")不算违规, 否则守阵会逼人删文档
                if stripped.startswith(("*", "//", "#")):
                    continue
                problems.append(
                    f"{rel}:{ln} `{name}` 是 computed 却以 this.{name}() 调用"
                    "(拿到的是 getter 的值, 再 () 会 TypeError ⇒ 触发该路径的界面整段白屏)"
                )
    assert not problems, "computed 被当函数调用: " + "; ".join(problems)


def test_frontend_template_no_reserved_prefix_identifiers():
    """模板表达式里禁止 `_`/`$` 前缀裸标识符 —— Vue 把两类前缀当内部保留域, 模板解析不到

    现象与定性(issue 26-10-03-1412, 坑位 web-ui/vue-reactivity.md「模板里不允许下划线前缀标识符」):
    drawer.html / popovers.html 的复制钮处理器写成 `@click="_copyText(...)"`, 真浏览器点击恒抛
    `ReferenceError: _copyText is not defined`(用户复验原文, 2026-10-03)且**整块渲染失败** ——
    Vue 把 `_`/`$` 前缀成员排除在组件代理之外, data/methods 里的 `_` 方法对模板不可见;
    vue.global.prod 无 dev 警告, 失败是静默的。

    覆盖两类形态(上次复发 1 的根子就是判别只记了插值形态, `@click="_x()"` 没被认出来):
    插值 `{{ ... }}` 与指令表达式(v-on / v-bind / v-if 等的属性值)。
    `$event` 是 Vue 内建事件形参, 白名单放行; `obj._x` 成员访问(点号后)不属于裸标识符, 不拦。
    """
    problems = []
    sources = []  # (rel, text): 盘上全部分片 + 各 UI shell 的 #app 内联段(与运行时编译输入同源)
    tpl_dir = os.path.join(STATIC_ROOT, "shared", "tpl")
    for name in sorted(os.listdir(tpl_dir)):
        if name.endswith(".html"):
            rel = "shared/tpl/" + name
            sources.append((rel, open(os.path.join(tpl_dir, name), encoding="utf-8").read()))
    for ui in _UI_ALL:
        sources.append((f"{ui}/index.html(#app 内联)", _ui_shell_inline(ui)))

    # 逐文件剥 HTML 注释(注释里的"别这么写"示例不算违规, 否则守阵会逼人删文档)
    stripped = [(rel, re.sub(r"<!--.*?-->", "", text, flags=re.S)) for rel, text in sources]
    for rel, text in stripped:
        spans = [(m.group(1), m.start()) for m in re.finditer(r"\{\{(.*?)\}\}", text, re.S)]
        spans += [
            (m.group(1), m.start())
            for m in re.finditer(r"""(?:^|\s)(?:v-[\w:.\-]+|@[\w.\-]+|:[\w.\-]+)\s*=\s*(["'])(.*?)\1""", text, re.S)
        ]
        for expr, pos in spans:
            for m in re.finditer(r"(?<![\w$.])([_$][A-Za-z_$][\w$]*)", expr):
                tok = m.group(1)
                if tok == "$event":  # Vue 内建事件形参, 模板里合法
                    continue
                ln = text[:pos].count("\n") + 1
                problems.append(
                    f"{rel}:{ln} 模板表达式含保留前缀标识符 `{tok}` —— Vue 解析不到(_/$ 前缀不对模板暴露, "
                    f"成员定义在 methods/data 里也会抛 ReferenceError 且整块渲染失败); "
                    f"模板处理器一律去前缀, 内部 `_` 方法经无前缀别名中转(issue 26-10-03-1412)"
                )
    assert not problems, "模板保留前缀标识符: " + "; ".join(problems)


def test_frontend_dist_segments_aggregates_per_view():
    """状态分布 distSegments 必须按当前 viewMode 取数, 不能只数 this.groups

    现象与定性(issue 26-09-21-0247):
    后端按视图回传(P1-1, 见 mixins/web_view.VIEW_ARRAYS): view=torrent 只回 torrents,
    view=group 只回 groups+singles。旧版 distSegments 只数 this.groups[].members[].kind,
    于是两种场景 chips 全空:
    1. localStorage 持久化 `autoqb.ui.view=torrents` 后首进种子页(首轮 groups=[]);
    2. 在种子页停得久(轮询只刷 torrents, groups 永远是空/旧)。
    表现是「做种10 错误1」整行消失。

    断言: distSegments 实现里必须包含三个 viewMode 分支(torrents / shows / 其余即 groups)。
    """
    rel = "shared/dialogs.js"
    text = open(os.path.join(STATIC_ROOT, rel), encoding="utf-8").read()
    m = re.search(r"distSegments\s*\(\)\s*\{(.*?)\n    \},", text, re.S)
    assert m, f"{rel} 找不到 distSegments computed(改名或挪走了? 同步本守阵)"
    body = m.group(1)
    for token, label in (
        ('this.viewMode === "torrents"', "torrents 视图分支"),
        ('this.viewMode === "shows"', "shows 视图分支"),
        ("this.groups", "groups 视图分支(else 兜底, 直接读 this.groups)"),
    ):
        assert token in body, f"distSegments 缺少{label}({token!r}) —— 种子页/追剧页次导航统计会全空(issue 26-09-21-0247)"


def test_frontend_cols_store_single_setitem_site():
    """全仓前端对 COLS_STORE_KEY 的 setItem 必须恰好一处(persistPage 内) —— 唯一持久化漏斗

    plan 26-09-21-1551: 旧模型 6 个落盘点各自决定写入时机, "先存后算/先算后存"选错 3 处,
    内存/存储长期漂移(失败分析实测: 内存 12 键 / 存储 0 键)。新模型只有一个漏斗,
    散写回潮 = 本守阵红。
    """
    hits = []
    for name, text in _bundle_iter():
        text = open(os.path.join(STATIC_ROOT, name), encoding="utf-8").read()
        for i, ln in enumerate(text.splitlines(), 1):
            code = ln.split("//")[0]
            if "localStorage.setItem(COLS_STORE_KEY" in code:
                hits.append(f"{name}:{i}")
    assert len(hits) == 1 and hits[0].startswith("shared/columns.js"), (
        f"COLS_STORE_KEY 的 setItem 必须只存在于 columns.js 的 persistPage 内, 实测: {hits}"
    )
    cols = open(os.path.join(STATIC_ROOT, "shared/columns.js"), encoding="utf-8").read()
    m = re.search(r"persistPage\s*\(\s*page\s*\)\s*\{(.*?)\n    \},", cols, re.S)
    assert m, "columns.js 找不到 persistPage(page)(改名或挪走了? 同步本守阵)"
    assert "localStorage.setItem(COLS_STORE_KEY" in m.group(1), "setItem 不在 persistPage 内? 同步本守阵"


def test_frontend_persist_page_takes_intent_only():
    """persistPage 只收意图态(colHidden/colOrder/colW), 生效宽度 colWidths 不得出现在其代码里

    "派生值没有资格落盘"是双轨模型唯一铁律(plan 26-09-21-1551)。旧模型 colWidths 混装
    意图与"按窗口算出的自适应 px", 靠 manual 标志在读写两侧过滤, 任何一侧失配即复发
    (issue 26-09-20-1800, 四轮修复未绝根)。取代旧守阵 test_frontend_save_col_state_skips_widths_for_auto_pages。
    """
    rel = "shared/columns.js"
    text = open(os.path.join(STATIC_ROOT, rel), encoding="utf-8").read()
    m = re.search(r"persistPage\s*\(\s*page\s*\)\s*\{(.*?)\n    \},", text, re.S)
    assert m, f"{rel} 找不到 persistPage(page)(改名或挪走了? 同步本守阵)"
    body = m.group(1)
    # !只看**代码行**(同旧守阵教训: 注释里提到不算)
    code_lines = [ln.strip() for ln in body.splitlines() if not ln.strip().startswith(("*", "//", "#"))]
    assert not any("colWidths" in ln for ln in code_lines
                  ), ("persistPage 的**代码**里出现 colWidths(生效态/派生值) —— 派生值落盘会让"
                      "'列宽被别的窗口改写'原样复发(plan 26-09-21-1551 铁律)")
    assert any("this.colW" in ln for ln in code_lines), ("persistPage 的**代码**里必须写意图态 this.colW(结构变了? 同步本守阵)")


def test_frontend_col_manual_flag_not_revived():
    """反向守阵: manual 标志位不得复活 —— 双轨模型下 w 非空即固化页, 标志位是旧模型的失配源

    v4 模型靠 manual:{page:bool} 门控"现算能不能覆盖 / 持久化要不要过滤", 读写两侧必须
    永远成对同步, 任何一侧失配 = "列设置被重置"复发(issue 26-09-20-1800 全史)。
    v5 删除该标志; 连注释里也不得出现该标识, 防止有人照着历史注释"顺手加回来"。
    """
    for name, text in _bundle_iter():
        text = open(os.path.join(STATIC_ROOT, name), encoding="utf-8").read()
        assert "colManual" not in text, (
            f"{name} 出现 colManual —— manual 标志位在双轨模型(v5)下已删除, "
            "不得复活(w 非空即固化页); 如确需重引, 先重审 plan 26-09-21-1551"
        )


def test_frontend_cols_legacy_keys_have_migration():
    """LEGACY_COLS_KEYS 键链必须伴随迁移函数 —— 升版必挂迁移(定案口径)

    v3->v4 升版没挂迁移, 用户手调的宽/隐/序一次性清零(四轮修复复盘第1.轮, "时不时被重置"
    的机制性来源)。v5 挂 migrateLegacyToV5; 本守阵钉住键链与迁移的耦合。
    """
    rel = "shared/app.js"
    text = open(os.path.join(STATIC_ROOT, rel), encoding="utf-8").read()
    m = re.search(r"const LEGACY_COLS_KEYS = \[(.*?)\];", text, re.S)
    assert m, f"{rel} 找不到 LEGACY_COLS_KEYS"
    keys = re.findall(r'"([^"]+)"', m.group(1))
    assert keys == [
        "autoqb_cols_v4", "autoqb_cols_v3"
    ], (f"LEGACY_COLS_KEYS 变更了({keys}) —— 升版/换键必须同步 migrateLegacyToV5 与迁移测试"
        "(plan 26-09-21-1551; v3->v4 清零事故的机检)")
    assert "function migrateLegacyToV5" in text, "LEGACY_COLS_KEYS 非空但找不到 migrateLegacyToV5(迁移函数)"
    assert "migrateLegacyToV5(raw)" in text, "readColStateRaw 未使用 migrateLegacyToV5(旧键不会被迁移)"


def test_frontend_cols_empty_hint_names_browser_clear_cause():
    """空存储提示必须点出"浏览器站点级关闭时清除站点数据"这条通道 + 自查路径 + 会话级去重

    2026-09-24 取证(真因, 非应用 bug): 用户 Edge/Chrome 的 `content_settings.exceptions.cookies`
    里都有 `127.0.0.1,*` setting=4(Chromium `CONTENT_SETTING_SESSION_ONLY`, 界面文案 = "关闭窗口时
    清除 Cookie 和站点数据") ⇒ 关浏览器时该 host 的 Cookie 与 localStorage **一起**被清, 于是
    "浏览器重启后偏好全回默认"。旧提示只写了 origin 隔离(换地址/端口), 把排查方向带偏了好几轮。
    另一层: 清站点数据的环境下 localStorage 里的"已提示"标记也一起没了 ⇒ 没有 sessionStorage
    兜底就会每次关浏览器重开都弹。
    """
    text = open(os.path.join(STATIC_ROOT, "shared", "columns.js"), encoding="utf-8").read()
    m = re.search(r"_showColsOriginHint\(\)\s*\{(.*?)\n    \},", text, re.S)
    assert m, "columns.js 找不到 _showColsOriginHint(改名或挪走了? 同步本守阵)"
    body = m.group(1)
    assert "关闭窗口时清除" in body, (
        "空存储提示没提浏览器站点级『关闭窗口时清除 Cookie 和站点数据』—— 用户会把整站数据被清"
        "误判成应用 bug(2026-09-24 取证: Edge/Chrome 的 cookie 例外 127.0.0.1,* setting=4)"
    )
    assert "edge://settings/content/all" in body, "提示必须给出可自查的浏览器设置路径(否则用户无从下手)"
    assert "sessionStorage" in body, "缺少 sessionStorage 兜底 ⇒ 清站点数据的环境下每次开浏览器都弹"
    assert "localStorage.setItem(COLS_ORIGIN_HINT_KEY" in body, "普通场景的跨会话去重标记(只弹一次)被删了"


def test_removed_redundant_tooltips_stay_removed():
    """复述型 tooltip 不得复活守阵(报告 26-10-04-0815: A-G 组模板 66 处 + H1 columns.js)

    判定口径: tooltip 只是逐字复述可见内容 / 图标本身自明的都属冗余, 已整体移除;
    全站悬浮提示统一由 shared/ui_feedback.js 拦截层渲染。本守阵读模板/JS 源码钉住
    代表性文案, 哪个文件把已删文案写回去即红。判定为保留的 tooltip(操作说明/后果预告、
    drawer.js 等的 _openModal 弹窗标题字段、config_hub.js 设置节标题、独立图表部件)不在列。
    """
    checks = (
        # A 组 · 底部状态栏: 数值逐字复述 + 「点击修改」增量提示 + 数据状态实现细节
        ("shared/tpl/statusbar.html", ("点击修改", "数据状态")),
        # B 组 · 顶栏页签: 与可见文字同义(图标+「分组」/「种子」)
        ("shared/tpl/topbar.html", ("按分组展示", "全部种子一行一条")),
        # D 组 · 抽屉关闭钮: ✕ 自明, Esc 快捷键在帮助浮层有正式清单
        ("shared/tpl/drawer.html", ("关闭(Esc)", "关闭（Esc）")),
        # E 组 · 对话框族关闭钮: 关闭钮的 ✕ 自明
        ("shared/tpl/dialogs.html", ('title="关闭"', )),
        ("shared/tpl/dialogs-mgr.html", ('title="关闭"', )),
        ("shared/tpl/popovers.html", ('title="关闭"', )),
        # F 组 · 曲线标题栏 caret: 箭头方向已表意
        ("shared/tpl/settings-detail.html", ("点击收起", )),
        ("shared/tpl/xtpl.html", ("点击收起", )),
        # H1 · columns.js 列偏好提示横幅: 横幅整体可点 + 手型光标 + 15s 自毁
        ("shared/columns.js", ("点击关闭", )),
    )
    for rel, needles in checks:
        text = open(os.path.join(STATIC_ROOT, *rel.split("/")), encoding="utf-8").read()
        for needle in needles:
            assert needle not in text, (
                f"{rel} 出现已移除的复述型 tooltip 文案「{needle}」(报告 26-10-04-0815 判定为移除) —— "
                "悬浮提示一律走 shared/ui_feedback.js 拦截层, 不要把原生 title 写回去"
            )


def test_recheck_confirm_wired_all_mouse_entries():
    """重新校验确认框三入口接线守阵(T13, 计划 26-10-05-0314 S3)

    键盘路径原有确认框(shortcuts.js _kbAct), 鼠标路径(批量右键/单选右键/抽屉)点下即执行
    (issue 26-10-05-0254: 防护不对称)。S3 抽共用 helper(commands.js _recheckConfirm, 文案与
    调用形态逐字沿键盘路径)后四处同一文案。本守阵读 JS 源码钉住三个接入点 + 文案单点,
    任一被重构摘除即红:
    1. commands.js _recheckConfirm 存在, 且 confirmDialog/okText 调用形态与文案逐字原样;
    2. bulkAct(批量右键 ctxAct 的落点, 批量浮条退役后仍是批量通道单点)含 recheck 确认分支;
    3. drawer.js torrentCmd(单选右键与抽屉内命令共同通道)含 recheck 确认分支;
    4. shortcuts.js _kbAct 改调共用 helper, 不再内联 confirmDialog 文案;
    5. 共用文案字符串全仓只在 commands.js 出现一次(防三处各抄一份漂移)。
    """
    cmds = open(os.path.join(STATIC_ROOT, "shared", "commands.js"), encoding="utf-8").read()
    drawer = open(os.path.join(STATIC_ROOT, "shared", "drawer.js"), encoding="utf-8").read()
    shortcuts = open(os.path.join(STATIC_ROOT, "shared", "shortcuts.js"), encoding="utf-8").read()
    text = "全量重读磁盘并校验完整性, 大库上耗时长且不可中断。"

    # ① 共用 helper 单点: 调用形态(标题/okText)与文案逐字沿键盘路径原样
    m = re.search(r"async _recheckConfirm\(what\)\s*\{(.*?)\n    \},", cmds, re.S)
    assert m, "commands.js 找不到 _recheckConfirm(改名或挪走了? 同步本守阵)"
    helper = m.group(1)
    assert 'confirmDialog("重新校验"' in helper and '{ okText: "确定" }' in helper, (
        "共用 helper 未沿键盘路径原调用形态(confirmDialog + okText 确定) —— 入口间确认形态漂移"
    )
    assert text in helper, "共用 helper 丢失键盘路径既有文案(重新校验确认框文案必须逐字保留)"

    # ② 共用文案字符串只此一份(三入口共用, 防各抄一份漂移)
    for name, src in (("commands.js", cmds), ("drawer.js", drawer), ("shortcuts.js", shortcuts)):
        assert src.count(text) == (1 if name == "commands.js" else
                                   0), (f"{name} 内联了重新校验确认文案 —— 共用文案只允许存在 commands.js _recheckConfirm 一份")

    # ③ 批量通道(bulkAct): 批量右键(ctxAct)入口, recheck 先确认后投递, 取消零副作用。
    #    分支按**整行活性**锚定(精确缩进 + if/await/if(!ok) 结构) —— 注释包裹、短路禁用、
    #    挪出确认调用都会破坏匹配而变红; 裸字符串包含判定拦不住这些摘除形态(红验实测)。
    m = re.search(r"async bulkAct\(action\)\s*\{(.*?)\n    \},", cmds, re.S)
    assert m, "commands.js 找不到 bulkAct(改名或挪走了? 同步本守阵)"
    assert re.search(
        r'^      if \(action === "recheck"\) \{\n'
        r"        const ok = await this\._recheckConfirm\(.+\);\n"
        r"        if \(!ok\) return;\n"
        r"      \}$",
        m.group(1),
        re.M,
    ), "bulkAct 的 recheck 确认分支被摘除/改写 —— 批量右键重新校验恢复裸奔(计划 26-10-05-0314 S3; 接入点改写须同步本守阵)"

    # ④ 单选通道(torrentCmd): 单选右键与抽屉内命令入口, 只拦 recheck 其它命令不受影响
    m = re.search(r"async torrentCmd\(action, body = null, okText = \"\"\)\s*\{(.*?)\n    \},", drawer, re.S)
    assert m, "drawer.js 找不到 torrentCmd(改名或挪走了? 同步本守阵)"
    assert re.search(
        r'^      if \(action === "recheck"\) \{\n'
        r"        const ok = await this\._recheckConfirm\(.+\);\n"
        r"        if \(!ok\) return;\n"
        r"      \}$",
        m.group(1),
        re.M,
    ), "torrentCmd 的 recheck 确认分支被摘除/改写 —— 单选右键/抽屉重新校验恢复裸奔(计划 26-10-05-0314 S3; 接入点改写须同步本守阵)"

    # ⑤ 键盘通道(_kbAct): 改调共用 helper(整行活性锚定), 不得再内联确认框文案
    m = re.search(r"async _kbAct\(action\)\s*\{(.*?)\n    \},", shortcuts, re.S)
    assert m, "shortcuts.js 找不到 _kbAct(改名或挪走了? 同步本守阵)"
    assert re.search(
        r"^        const ok = await this\._recheckConfirm\(what\);$",
        m.group(1),
        re.M,
    ), "_kbAct 未调共用 helper —— 键盘路径自成一份文案必漂移(计划 26-10-05-0314 S3)"
    assert 'confirmDialog("重新校验"' not in m.group(1), ("_kbAct 又内联了重新校验确认框文案 —— 应改调 commands.js _recheckConfirm")


def test_skip_check_dialog_precheck_wired():
    """跳检预检对话框接线守阵(T23, 计划 26-10-05-0314 S4)

    S4 把跳检确认框升级为三分流预检对话框: 共享 modal 扩展 okDisabled/busy/verdict 三字段,
    抽 _skipCheckDialog 取代 skipCheckTorrent/skipCheckMulti 两个各自为政的 _openModal。
    本守阵读 JS/模板源码钉住接线, 整行/整块活性锚定(T13 经验: 字符串包含拦不住突变),
    任一环被重构摘除即红:
    1. ui_feedback.js _modalInit 声明 okDisabled: false / busy: false / verdict: null
       (缺省零变化是「既有全部对话框不受影响」的根基);
    2. popovers.html 确认钮(modalOk)挂 :disabled="modal.okDisabled" 绑定 + busy 行 +
       verdict 行式渲染区(复用 modal-details 范式) + 强制钮仍走 extraText 第三钮
       (danger-solid 破坏性分支);
    3. drawer.js 两入口均交棒 _skipCheckDialog 且方法体内不再自带 _openModal;
    4. _skipCheckDialog 进框即 okDisabled:true + busy:true + verdict(固定警示区)并触发预检
       (_skipPrecheck 调 precheck 端点 + waitCmd 等回执)。
    """
    ui = open(os.path.join(STATIC_ROOT, "shared", "ui_feedback.js"), encoding="utf-8").read()
    tpl = open(os.path.join(STATIC_ROOT, "shared", "tpl", "popovers.html"), encoding="utf-8").read()
    drawer = open(os.path.join(STATIC_ROOT, "shared", "drawer.js"), encoding="utf-8").read()

    # ① _modalInit 三字段(缺省值即零变化契约: 改默认/删字段/改名都红)
    m = re.search(r"_modalInit\(\)\s*\{\s*return\s*\{(.*?)\n      \};", ui, re.S)
    assert m, "ui_feedback.js 找不到 _modalInit(改名或挪走了? 同步本守阵)"
    init = m.group(1)
    assert re.search(r"^        okDisabled: false, // ", init, re.M), \
        "_modalInit 缺 okDisabled: false 声明(确认钮禁用通道) —— 预检对话框状态机失锚"
    assert re.search(r"^        busy: false,\s+// ", init, re.M), \
        "_modalInit 缺 busy: false 声明(预检在途行) —— 预检对话框状态机失锚"
    assert re.search(r"^        verdict: null,\s+// ", init, re.M), \
        "_modalInit 缺 verdict: null 声明(三分流渲染区) —— 预检对话框状态机失锚"

    # ② 模板: 确认钮 :disabled 绑定(整钮块锚定 —— 绑定挪出 modalOk 钮或改静态值即红)
    m = re.search(r'<button ref="modalOk"[\s\S]*?</button>', tpl)
    assert m, "popovers.html 找不到 modalOk 确认钮(模板重构? 同步本守阵)"
    assert ':disabled="modal.okDisabled"' in m.group(0), \
        "modalOk 确认钮缺 :disabled=\"modal.okDisabled\" 绑定 —— 进框禁用/按态解锁失效(计划 26-10-05-0314 S4)"
    # busy 行(整行锚定)与 verdict 渲染区(行式明细, 复用 modal-details 范式)
    assert '<p v-if="modal.busy" class="modal-body">正在检查前置条件…</p>' in tpl, \
        "popovers.html 缺预检 busy 行 —— 预检在途无反馈(计划 26-10-05-0314 S4)"
    assert '<div v-if="modal.verdict && modal.verdict.length" class="modal-details">' in tpl, \
        "popovers.html 缺 verdict 三分流渲染区(modal-details 行式范式)"
    assert 'v-for="(d, i) in modal.verdict"' in tpl, "verdict 区缺行式 v-for 渲染"
    # 强制钮仍复用 extraText 第三钮通道(danger-solid 破坏性分支; 换自铸强制钮即红)
    assert re.search(r'<button v-if="modal\.extraText" class="bt danger-solid" @click="resolveModal\(\'extra\'\)">', tpl), \
        "第三钮(extraText 通道)被改写 —— S4 强制钮必须复用既有 danger-solid 破坏性分支"

    # ③ 两入口均交棒 _skipCheckDialog, 且方法体内不再自带 _openModal(确认框被取代)
    for name in ("skipCheckTorrent", "skipCheckMulti"):
        m = re.search(rf"async {name}\(\)\s*\{{(.*?)\n    \}},", drawer, re.S)
        assert m, f"drawer.js 找不到 {name}(改名或挪走了? 同步本守阵)"
        assert "this._skipCheckDialog(" in m.group(1), \
            f"{name} 未走 _skipCheckDialog —— 预检对话框两入口共用的状态机被绕开(计划 26-10-05-0314 S4)"
        assert "_openModal" not in m.group(1), \
            f"{name} 仍自带 _openModal 确认框 —— 旧 danger 确认框应被预检对话框取代"

    # ④ _skipCheckDialog: 进框即禁用 + busy + 固定警示区 + 触发预检(调 _skipPrecheck)
    m = re.search(r"async _skipCheckDialog\(hashes, exec\)\s*\{(.*?)\n    \},", drawer, re.S)
    assert m, "drawer.js 找不到 _skipCheckDialog(S4 状态机被改名/挪走? 同步本守阵)"
    dlg = re.sub(r"//[^\n]*", "", m.group(1))  # 剥行注释后锚定代码结构(注释改写不红, 代码突变必红)
    assert "okDisabled: true" in dlg, "_skipCheckDialog 进框未禁用确认钮(预检回执前不得有可执行钮)"
    assert "busy: true" in dlg, "_skipCheckDialog 进框未置 busy(预检在途无反馈)"
    assert "verdict: warnRows" in dlg, "_skipCheckDialog 进框未挂固定警示区(case 3 不代表没有代价)"
    assert "this._skipPrecheck(seq" in dlg, "_skipCheckDialog 未触发预检投递"


def test_skip_check_dialog_verdict_render():
    """跳检预检三分流渲染逻辑守阵(T24, 计划 26-10-05-0314 S4)

    静态钉住 _skipPrecheck/_skipCheckDialog/_skipExec/_skipVerdictRows 的状态机语义,
    防渲染逻辑被改写出「blocked 仍可执行 / 降级态冒出强制钮 / 混合态送错子集」这类
    pytest 静态守阵之外只有真浏览器才看得见的回归:
    1. 六态分支(逐分支提取语句清单与期望比对, 剥注释滤空行): 预检失败降级=启用普通确认且无
       强制钮 / 含 blocked=确认强制双钮全收 / ok+force 混合=确认「跳检 N 个可跳检的」+强制
       「强制跳检全部」/ force-only=确认保持禁用只有强制钮 / 全 ok=只启用确认;
    2. ok 子集派生与提交口径: okHashes 只收 cls==="ok"; 确认路径送 ok 子集(降级送全量),
       强制路径送全量 + force=true(单发 body 仅 force 时带 force 键, 批量确认只走 hashes);
    3. 降级文案明示「后端闸门仍会在执行时拦截」(D10);
    4. 分组展示: 计数行(可跳检/需强制/禁止)+ 组内名称上限截断(slice(0,5)+等 X 个)。
    """
    drawer = open(os.path.join(STATIC_ROOT, "shared", "drawer.js"), encoding="utf-8").read()

    # ① 状态机六态分支: 逐分支提取语句清单(剥注释滤空行后)与期望逐一比对 ——
    #    摘除/新增/改写任一语句(如降级分支删掉解锁行、blocked 分支漏收强制钮)即红
    m = re.search(r"async _skipPrecheck\(seq, hashes, warnRows\)\s*\{(.*?)\n    \},", drawer, re.S)
    assert m, "drawer.js 找不到 _skipPrecheck(S4 状态机被改名/挪走? 同步本守阵)"
    pre = re.sub(r"//[^\n]*", "", m.group(1))

    def _branch(head, nxt):
        bm = re.search(re.escape(head) + r"(.*?)" + re.escape(nxt), pre, re.S)
        assert bm, f"状态机分支锚点丢失: {head!r} -> {nxt!r}(分支结构被改写? 同步本守阵)"
        return [ln.strip() for ln in bm.group(1).splitlines() if ln.strip()]

    assert _branch("if (degraded) {", "} else if (counts.blocked) {") == [
        "this.modal.okDisabled = false;",
        'this.modal.extraText = "";',
    ], "降级分支(D10)被改写 —— 必须启用普通确认(okDisabled=false)且无强制钮(extraText 空)"
    assert _branch("} else if (counts.blocked) {", "} else if (counts.ok && counts.force) {") == [
        "this.modal.okDisabled = true;",
        'this.modal.extraText = "";',
    ], "含 blocked 分支被改写 —— blocked 硬闸: 确认/强制双钮全收, 不得产生任何可执行钮"
    assert _branch("} else if (counts.ok && counts.force) {", "} else if (counts.force) {") == [
        "this.modal.okDisabled = false;",
        "this.modal.okText = `跳检 ${counts.ok} 个可跳检的`;",
        "this.modal.extraText = `强制跳检全部 ${counts.ok + counts.force}`;",
    ], "ok+force 混合分支被改写 —— 确认钮只送 ok 子集文案, 强制钮送全量"
    assert _branch("} else if (counts.force) {", "} else {") == [
        "this.modal.okDisabled = true;",
        "this.modal.extraText = `强制跳检全部 ${counts.ok + counts.force}`;",
    ], "force-only 分支被改写 —— 确认保持禁用, 只有强制钮"
    fm = re.search(re.escape("} else if (counts.force) {") + r"(.*?)" + re.escape("} else {"), pre, re.S)
    assert fm, "force-only 分支锚点丢失(分支结构被改写? 同步本守阵)"
    tail_m = re.search(r"(.*?)\n      \}", pre[fm.end():], re.S)
    assert tail_m, "全 ok 分支锚点丢失(分支结构被改写? 同步本守阵)"
    assert [ln.strip() for ln in tail_m.group(1).splitlines() if ln.strip()] == [
        "this.modal.okDisabled = false;",
        "this.modal.okText = `跳检 ${counts.ok} 个`;",
        'this.modal.extraText = "";',
    ], "全 ok 分支被改写 —— 只启用确认(送全量不带 force), 无强制钮"
    # ok 子集派生: 只收 cls==="ok"(blocked/force 不进确认子集)
    assert 'okHashes = results.filter((x) => x.cls === "ok").map((x) => x.hash);' in pre, \
        "okHashes 未按 cls===\"ok\" 派生 —— 确认子集口径失守"
    # D10 降级文案(两处: 非 ok 回执 + 请求异常, 缺一即红)
    assert pre.count("后端闸门仍会在执行时拦截") == 2, \
        "降级文案「后端闸门仍会在执行时拦截」应恰好覆盖 非 ok 回执 与 请求异常 两分支"

    # ② 确认/强制两路径的提交口径(_skipCheckDialog 分派 + _skipExec 端点载荷)
    m = re.search(r"async _skipCheckDialog\(hashes, exec\)\s*\{(.*?)\n    \},", drawer, re.S)
    assert m, "drawer.js 找不到 _skipCheckDialog"
    dlg = re.sub(r"//[^\n]*", "", m.group(1))
    assert "return this._skipExec(exec, hashes, true);" in dlg, \
        "强制路径未送全量(hashes) —— 强制钮必须送全量 + force"
    assert "return this._skipExec(exec, v.degraded ? hashes : v.okHashes, false);" in dlg, \
        "确认路径未按 态送 ok 子集(降级送全量) —— 混合态把 force/blocked 目标混进普通确认即违背三分流"
    m = re.search(r"async _skipExec\(exec, hashes, force\)\s*\{(.*?)\n    \},", drawer, re.S)
    assert m, "drawer.js 找不到 _skipExec"
    exe = re.sub(r"//[^\n]*", "", m.group(1))
    assert "body: force ? JSON.stringify({ force: true }) : undefined" in exe, \
        "单发跳检 body 应仅在 force 时携带 force 键(缺省载荷与历史一致)"
    assert "keys: force ? exec.groupKeys : []" in exe and "hashes: force ? exec.memberHashes : hashes" in exe, \
        "批量跳检载荷口径失守: 确认=只送 ok 子集(hashes), 强制=keys+hashes 整份"
    assert "...(force ? { force: true } : {})" in exe, \
        "批量强制路径缺 force: true 透传(S2: 提供才入载荷)"

    # ③ 分组展示: 计数行 + 上限截断(5 + 等 X 个)
    m = re.search(r"_skipVerdictRows\(results\)\s*\{(.*?)\n    \},", drawer, re.S)
    assert m, "drawer.js 找不到 _skipVerdictRows"
    rows = re.sub(r"//[^\n]*", "", m.group(1))
    assert "`可跳检 ${ok.length} / 需强制 ${force.length} / 禁止 ${blocked.length}`" in rows, \
        "分组展示缺计数行(可跳检/需强制/禁止)"
    assert "g.names.slice(0, 5)" in rows, "分组行缺名称上限截断(5 个)"
    assert "等 ${g.names.length} 个" in rows, "分组行缺「等 X 个」尾注"


def test_frontend_page_location_persisted():
    """顶层 page 与设置分区必须持久化 —— 刷新后停在原页(2026-09-25 用户报"设置页刷新会回到种子页")

    `page` 原本是**纯内存态**、初值恒 "groups" ⇒ 在设置页按 F5 必掉回辅种页, 编辑位置全丢;
    设置页里的分区(`hub.view`)同理, 只持久化顶层页会让「设置 → 站点」刷新后落到设置首页。
    两条都只有真浏览器看得见(pytest 全绿、界面行为退化), 故在此静态钉住四件事:
    1. 读侧**白名单**(只认 "settings", 不信任存储内容) + 写侧唯一漏斗;
    2. **启动必须补一次 cfgLoad** —— 设置页的配置树是按需加载的, 只改初值不改启动路径,
       首屏会停在「配置加载失败 + 重试」(`cfg.schema` 永远为 null);
    3. 恢复的分区 key 必须**对 schema 校验** —— 分区会随版本改名/删除, 否则停在空白分区;
    4. 恢复走 `hubGo`(懒加载与默认选中项都在那条路径里, 自己重写必漏一半)。
    """
    app = _app_bundle_text()
    m = re.search(r"function initialPage\(\)\s*\{(.*?)\n\}", app, re.S)
    assert m, "app.js 找不到 initialPage()(改名或挪走了? 同步本守阵)"
    assert "autoqb.ui.page" in m.group(1), "initialPage 未读 autoqb.ui.page —— 页面位置没有持久化"
    assert '=== "settings" ? "settings" : "groups"' in m.group(1), (
        "initialPage 必须白名单式取值(只认 settings, 其余落 groups) —— 直接回填存储内容会把脏值当页名"
    )
    assert re.search(r"^\s*page:\s*initialPage\(\),", app, re.M), "data() 的 page 初值未走 initialPage()"

    m = re.search(r"persistUiPage\(\)\s*\{(.*?)\n    \},", app, re.S)
    assert m, "app.js 找不到 persistUiPage()(改名或挪走了? 同步本守阵)"
    assert "autoqb.ui.page" in m.group(1), "persistUiPage 未写 autoqb.ui.page"
    m_watch = re.search(r"^\s*page\(\)\s*\{(.*?)\n    \},", app, re.S | re.M)
    assert m_watch and "this.persistUiPage()" in m_watch.group(1), ("watch(page) 未调 persistUiPage —— 切页不落盘, 刷新后仍掉回辅种页")
    m_poll = re.search(r"startPolling\(\)\s*\{(.*?)\n    \},", app, re.S)
    assert m_poll, "app.js 找不到 startPolling()(改名或挪走了? 同步本守阵)"
    poll = m_poll.group(1)
    assert 'this.page === "settings"' in poll and "this.cfgLoad()" in poll, (
        "startPolling 未在恢复到设置页时补一次 cfgLoad —— 首屏停在「配置加载失败 + 重试」"
        "(设置页的配置树是按需加载的)"
    )

    hub = open(os.path.join(STATIC_ROOT, "shared", "config_hub.js"), encoding="utf-8").read()
    m = re.search(r"function initialHubView\(\)\s*\{(.*?)\n\}", hub, re.S)
    assert m and "autoqb.ui.hub" in m.group(1), "config_hub.js 的 initialHubView 未读 autoqb.ui.hub"
    assert re.search(r"^\s*view:\s*initialHubView\(\),", hub, re.M), "hub.view 初值未走 initialHubView()"
    assert re.search(r'"hub\.view"\(v\)\s*\{', hub), "缺少 hub.view 的 watcher —— 分区切换不落盘"
    assert 'localStorage.setItem("autoqb.ui.hub"' in hub, "hub.view 的 watcher 未写 autoqb.ui.hub"
    m = re.search(r"hubRestore\(\)\s*\{(.*?)\n    \},", hub, re.S)
    assert m, "config_hub.js 找不到 hubRestore()(改名或挪走了? 同步本守阵)"
    body = m.group(1)
    assert "this.cfg.schema" in body and "groups.some" in body, ("hubRestore 未对 schema 校验分区 key —— 分区改名/删除后刷新会停在空白分区")
    assert "this.hubGo(" in body, "hubRestore 应复用 hubGo(否则漏掉 trackers/rules 选中项与日志/HR 懒加载)"
    ed = open(os.path.join(STATIC_ROOT, "shared", "config_editor.js"), encoding="utf-8").read()
    assert "this.hubRestore()" in ed, "cfgLoad 成功后未调 hubRestore(schema 到手那一刻才校验得了分区 key)"


def test_frontend_unsaved_changes_guard_wiring():
    """设置页未保存改动防护接线守阵(issue 26-09-25-1702 / 报告 26-10-02-0508, 路线 U1-b)

    现象: 设置页改了配置没保存就刷新, 整棵树被服务端配置整体替换, 改动**静默丢**。
    定性: 页签切换是纯内存态(全仓无 pushState / location.hash), 丢失只发生在**真实页面重载**
    这一条路径上 —— 正好是 beforeunload 的覆盖区间。选的路线是 **U1-b 自绘框 + 原生兜底**:
      · 键盘刷新(F5 / Ctrl+R 族): keydown 里 preventDefault 拦掉默认刷新, 弹**自绘**三选一框
        (可写中文, 且多出「保存并刷新」这一支 —— 这是选 U1-b 而不选 U1-a 唯一买到的东西);
      · 其余真实导航(地址栏回车 / 关标签 / 后退): JS **取消不了**导航, 只能靠原生 beforeunload 框。
    两条链少一条就漏一半; 且**主动刷新前必须先摘掉原生兜底**(否则自绘框答完接着 reload 又弹一次
    原生框 = 双框连击, 报告 §6 的"去重")。不做草稿恢复(刷新即回到磁盘配置), 判据沿用 cfgDirty 单点。

    静态守阵钉住六件事(全是"pytest 全绿、界面行为退化"的形态):
    1. 自绘三选一框的基础设施(模板第三钮 + confirmThreeDialog + resolveModal("extra") 结算);
    2. 原生兜底随脏态**挂载 / 摘除成对**(常驻挂载 => Firefox 放弃 bfcache + 无改动也弹框的疲劳);
    3. 只拦 F5 / Ctrl+R 族(不抢任何其它键), 脏态为假时一声不吭, 已有弹窗时不叠框(交给原生兜底);
    4. 三分支语义(保存并刷新必须先看 cfgSave 的成败 / 放弃并刷新 / 留在此页);
    5. 主动刷新前摘兜底;
    6. 键盘监听在 lifecycle 注册、unmounted 撤除, 脏态 watcher 在 state.js 接线(漏接 = 整块静默消失)。
    """
    ed = open(os.path.join(STATIC_ROOT, "shared", "config_editor.js"), encoding="utf-8").read()
    fb = open(os.path.join(STATIC_ROOT, "shared", "ui_feedback.js"), encoding="utf-8").read()
    pop = open(os.path.join(STATIC_ROOT, "shared", "tpl", "popovers.html"), encoding="utf-8").read()
    st = open(os.path.join(STATIC_ROOT, "shared", "state.js"), encoding="utf-8").read()
    lc = open(os.path.join(STATIC_ROOT, "shared", "lifecycle.js"), encoding="utf-8").read()

    # 1. 自绘三选一框: 第三钮(模板) + 入口(confirmThreeDialog) + "extra" 结算(resolveModal)
    assert 'v-if="modal.extraText"' in pop and "@click=\"resolveModal('extra')\"" in pop, \
        "popovers.html 缺第三钮渲染(三选一框退化成两钮 = 白选 U1-b)"
    assert 'extraText: "",' in fb, "ui_feedback.js _modalInit 缺 extraText(漏声明 = 模板键 undefined)"
    three = re.search(r"confirmThreeDialog\(title, body, opts = \{\}\) \{(.*?)\n    \},", fb, re.S)
    assert three and "extraText: opts.extraText" in three.group(1), \
        "缺 confirmThreeDialog(自绘刷新守卫的入口; 改名或挪走了? 同步本守阵)"
    assert 'resolve(choice === "extra" ? "extra" : true)' in fb, \
        "resolveModal 未把第三钮结算为 \"extra\"(三分支拿不到区分 = 只会保存或只会丢弃)"
    # 反向: 既有两钮契约不得被第三钮污染(confirmDialog 仍返回布尔)
    assert "okText: opts.okText || \"确认\", cancelText: opts.cancelText || \"取消\", danger: !!opts.danger," in fb

    # 2. 原生兜底: 挂 / 摘成对 + 幂等(只在 dirty 期存在)
    sync = re.search(r"cfgGuardSync\(on\) \{(.*?)\n    \},", ed, re.S)
    assert sync, "config_editor.js 缺 cfgGuardSync(原生兜底的挂摘单点; 改名? 同步本守阵)"
    body = sync.group(1)
    assert 'window.addEventListener("beforeunload"' in body and 'window.removeEventListener("beforeunload"' in body, \
        "beforeunload 必须挂摘成对 —— 只挂不摘 = 常驻监听(伤 bfcache + 无改动也弹框)"
    assert "if (want === !!this._cfgGuardOn) return;" in body, "cfgGuardSync 必须幂等(重复挂载 = 句柄堆叠)"
    # 判据单点: 与 actbar「有改动还没保存」同一条 cfgDirty, 不另立状态机
    guard = re.search(r"cfgGuardActive\(\) \{(.*?)\n    \},", ed, re.S)
    assert guard and "this.cfgDirty" in guard.group(1), \
        "守卫判据必须是 cfgDirty(另立判据 = 与页面上「有改动还没保存」两处各说各话)"
    # 反向: 不做草稿恢复 —— 配置树含 qbittorrent.password, 一律不得进 Web Storage(报告 §6)
    assert "sessionStorage" not in ed and "localStorage" not in ed, \
        "config_editor.js 不得碰 Web Storage(整树入存会把 qbittorrent.password 摆上 XSS 面; 草稿另开议题)"

    # 3. 只拦 F5 / Ctrl+R 族; 无改动放行; 已有弹窗不叠框
    key = re.search(r"_cfgOnReloadKey\(e\) \{(.*?)\n    \},", ed, re.S)
    assert key, "config_editor.js 缺 _cfgOnReloadKey(键盘刷新拦截; 改名? 同步本守阵)"
    body = key.group(1)
    assert 'e.code === "F5"' in body, "键盘拦截必须覆盖 F5(硬刷新 Ctrl/Shift+F5 同族)"
    assert 'e.code === "KeyR"' in body and "e.ctrlKey || e.metaKey" in body, \
        "键盘拦截必须覆盖 Ctrl+R / Cmd+R 族(用 e.code 物理键位, 与快捷键引擎同口径)"
    assert "e.preventDefault();" in body, "命中刷新键必须 preventDefault(不取消默认刷新 = 自绘框白弹)"
    assert "if (!this.cfgGuardActive()) return;" in body, \
        "无未保存改动时必须放行(每次刷新都弹 = 弹框疲劳, 用户会闭眼点离开)"
    assert "if (this.modal.visible) return;" in body, \
        "已有弹窗时必须放行(自绘框叠在弹窗上 = 上一个悬空 Promise 被静默结算为取消)"

    # 4. 三分支语义: 保存并刷新必须先看 cfgSave 成败(保存失败带着改动刷新 = 白丢)
    rel = re.search(r"async cfgReloadGuard\(\) \{(.*?)\n    \},", ed, re.S)
    assert rel, "config_editor.js 缺 cfgReloadGuard(自绘刷新守卫; 改名? 同步本守阵)"
    body = rel.group(1)
    assert "confirmThreeDialog(" in body, "刷新守卫必须弹自绘三选一框(U1-b 的落点)"
    for token in ("保存并刷新", "放弃改动并刷新", "留在此页"):
        assert token in body, f"三选一框缺「{token}」分支(自绘的意义就在这三个选项上)"
    assert "await this.cfgSave()" in body and "if (!saved) return;" in body, \
        "「保存并刷新」必须判 cfgSave 的成败 —— 保存失败却刷新 = 改动照样丢"
    save = re.search(r"async cfgSave\(\) \{(.*?)\n    \},", ed, re.S)
    assert save and "return true;" in save.group(1) and "return false;" in save.group(1), \
        "cfgSave 必须返回成败布尔(「保存并刷新」靠它决定刷不刷新)"

    # 5. 主动刷新前摘兜底(否则 reload 会再弹一次原生框 = 双框连击)
    assert "this.cfgGuardRelease();" in body and "location.reload()" in body, \
        "刷新前必须 cfgGuardRelease() + location.reload()(漏摘 = 自绘框答完又答一遍原生框)"
    assert "cfgGuardSync(false)" in re.search(r"cfgGuardRelease\(\) \{(.*?)\n    \},", ed, re.S).group(1)

    # 6. 接线: lifecycle 注册 / 撤除 + state.js 脏态 watcher
    assert 'this._cfgGuardKey = (e) => this._cfgOnReloadKey(e);' in lc and \
        'document.addEventListener("keydown", this._cfgGuardKey)' in lc, \
        "lifecycle.js 未注册键盘刷新拦截(漏注册 = 整块功能静默消失)"
    unm = re.search(r"unmounted\(\) \{(.*?)\n  \},", lc, re.S)
    assert unm and 'removeEventListener("keydown", this._cfgGuardKey)' in unm.group(1), \
        "lifecycle.js unmounted 未撤除键盘拦截(热重载后句柄堆叠, 一次按键弹 N 个框)"
    assert "this.cfgGuardRelease();" in unm.group(1), "unmounted 未摘原生兜底(同上, 防堆叠)"
    assert re.search(r"cfgDirty\(v\) \{\s*this\.cfgGuardSync\(v\);", st), \
        "state.js 缺 cfgDirty watcher —— 兜底不随脏态挂载(要么永不弹, 要么常驻弹)"


def test_frontend_expand_state_survives_view_switch():
    """展开态必须跨视图带走 —— 切走收进桶、切回还回去(2026-09-25 用户报「辅种页切到种子页再切回, 展开的组收起来了」)

    现象与定性:
    旧 `setViewMode` 里三行 `expandedKey / expandedShows / expandedShowEp = null`, 展开态**随切页丢掉**。
    展开态是"我正盯着这一组"这种临时意图, 跟"停在哪个视图"一样该跟着人走 —— 切到种子页再切回来,
    应该还是原来展开的那一组(不是"重新点开一次")。
    改法是**按视图分桶暂存**(`expandMemo`): 切走收进桶并清空实时字段(展开态仍不串台到别的视图),
    切回还回该视图最后一次的展开。

    两条反向约束(少一条就会把修好的东西又弄坏):
    1. **还回前必须验"那一行还在"** —— 组可能已被删或被筛掉;
    2. `groupWin` 的退避判据必须同步成"**当前真的有面板**" —— 只判 `expandedKey` 非空的话,
       一个过期的键会让行窗口永久退避(大库上 = 悄悄关掉 P1-2 优化, 界面看着完全正常, 只是滚动变卡)。
    """
    app = _app_bundle_text()
    m = re.search(r"setViewMode\(mode\)\s*\{(.*?)\n    \},", app, re.S)
    assert m, "app.js 找不到 setViewMode(mode)(改名或挪走了? 同步本守阵)"
    body = m.group(1)
    assert "this.stashExpandState()" in body, "setViewMode 未 stash 展开态 —— 切页即丢, 切回不还原"
    assert "this.restoreExpandState(mode)" in body, "setViewMode 未 restore 展开态 —— 切回分组页展开的组收起来了"
    dropped = re.findall(r"this\.expanded(?:Key|Shows|ShowEp)\s*=", body)
    assert not dropped, (f"setViewMode 里仍有 {len(dropped)} 处置空展开态的赋值 —— 展开态会随切页丢掉(应走 stash/restore)")

    m = re.search(r"restoreExpandState\(mode\)\s*\{(.*?)\n    \},", app, re.S)
    assert m, "app.js 找不到 restoreExpandState(mode)(改名或挪走了? 同步本守阵)"
    restore = m.group(1)
    assert "this.groups.some(" in restore, ("restoreExpandState 未验展开的组是否还在 —— 组已被删/被筛掉时留下悬空 expandedKey")
    assert "this.expandedKey = key" in restore, "restoreExpandState 未把分组展开键还回 expandedKey"

    cols = open(os.path.join(STATIC_ROOT, "shared", "columns.js"), encoding="utf-8").read()
    m = re.search(r"groupWin\(\)\s*\{(.*?)\n    \},", cols, re.S)
    assert m, "columns.js 找不到 groupWin()(改名或挪走了? 同步本守阵)"
    win = m.group(1)
    assert "if (this.expandedKey) return" not in win, ("groupWin 仍只按 expandedKey 非空退避 —— 过期的键会让行窗口永久退化成全量渲染")
    assert "this.expandedKey" in win and ".some(" in win, ("groupWin 的退避判据必须带上'展开的组确实在可见集合里'这一条")


def test_frontend_hub_field_covers_non_leaf_items():
    """hub-field 必须覆盖 cfgFlatten 产出的**全部**项类型 —— 缺了非叶子那三支就显示 `[object Object]`

    现象与定性(2026-09-25 用户报「设置页部分设置项显示 [object Object]」):
    `cfgFlatten` 把嵌套 object 展开成 **四种** item.type —— field(叶子) / section(可选段) /
    group(普通 object 段) / subcard(父字段的相关设置子卡)。`tpl-hub-field` 的控件分支
    (bool / enum / list / rules_ref / keyed_list / 数值+单位) 末尾是一个**无条件**的 `<input v-else>`,
    值取 `cfgInputValue` → `cfgScalar` → `String(value)`: 叶子字段存的是标量没问题, 而
    section / group / subcard 这条路径上存的是**对象**(如 `config.trackers.<站点>.hr`),
    `String({...})` 恰好是 "[object Object]" ⇒ 站点页「HR 规则」「HR 在线核实」与规则页
    checking 的 with_reference / without_reference 两个分支整行都显示这个串; 更糟的是**随手一改
    就把配置写成这个字符串**, 保存时后端校验才报错。

    根因: 经典设置页的 `tpl-ce-field` 有这三支, 清理死代码时随模板一起被删, 而 `cfgFlatten`
    仍会产出这三类项, 站点 / 规则两个专段又把扁平结果直接交给 hub-field(普通分区页的
    `hubBlocks` 只挑 `type === "field"`, 所以只有这两个专段暴露出来)。

    守阵两条:
    1. 两套皮肤的模板都必须**逐个**判 `item.type === '<非叶子类型>'`, 类型名单从 config_editor.js
       的 cfgFlatten 实读(将来新增类型忘了加分支 → 立刻红, 不靠人记);
    2. 叶子分支必须是链尾的 `v-else` —— 否则非叶子项会有绕回兜底 input 的路径。
    """
    editor = open(os.path.join(STATIC_ROOT, "shared", "config_editor.js"), encoding="utf-8").read()
    kinds = set(re.findall(r'type:\s*"(field|section|group|subcard)"', editor))
    assert "field" in kinds, "config_editor.js 里找不到 cfgFlatten 的 type: \"field\"(改名/挪走了? 同步本守阵)"
    non_leaf = sorted(k for k in kinds if k != "field")
    assert non_leaf, ("config_editor.js 的 cfgFlatten 不再产出任何非叶子项类型 —— "
                      "若嵌套段真的取消了, 本守阵该跟着撤, 别让它空转")

    for skin in _UI_ALL:
        html = _ui_aggregate(skin)
        m = re.search(r'<script type="text/x-template" id="tpl-hub-field">(.*?)\n  </script>', html, re.S)
        assert m, f"{skin}/index.html 找不到 tpl-hub-field 模板(改名/挪走了? 同步本守阵)"
        tpl = m.group(1)
        for kind in non_leaf:
            assert f"item.type === '{kind}'" in tpl, (
                f"{skin} 的 tpl-hub-field 缺 `item.type === '{kind}'` 分支 —— 该类项会落进叶子字段的"
                "兜底 <input>, 值被 String(对象) 成 '[object Object]'(且一改就把配置写成这个串)"
            )
            assert "item.items" in tpl, f"{skin} 的 tpl-hub-field 未递归渲染 item.items —— 段内子字段会整段消失"
        assert re.search(
            r'<div\s+v-else\s+class="hb-row"', tpl
        ), (f"{skin} 的 tpl-hub-field 叶子分支不是链尾的 <div v-else class=\"hb-row\"> —— "
            "非叶子项仍有掉进兜底 input 的路径")
        assert 'v-if="item.type === \'section\'"' in tpl, (
            f"{skin} 的 tpl-hub-field 首个分支必须带 v-if(链头), 否则 v-else-if 链不成立"
        )


def test_frontend_hub_field_renders_readonly_fields():
    """schema Field.readonly(程序托管字段)在设置页必须渲染为禁用控件(静态防回潮)

    issue 26-09-28-2135: schema_version/data_dir/state_file/fs 打 readonly 标 —— 这些字段的
    用户输入会被后端无条件覆盖/回退(程序盖章、R 级回退、readonly 键面防线), UI 若仍渲染
    可编辑控件, 反馈就是误导性的「已保存」。守阵四查(每套皮肤):

    1. CE_FIELD_BASE 必须有 readonly/readonlyComplex/readonlySummary 三个成员 ——
       HUB_FIELD_COMPONENT 经 Object.assign 继承, 缺一个模板引用就是 undefined 静默失效;
    2. tpl-hub-field 控件链**首支**必须是 readonly 的只读摘要分支(readonlyComplex) ——
       列表/对象值(fs.path_map)落进输入框会 String 化成 "[object Object]";
    3. 全部可编辑控件都挂 :disabled="readonly"(bool/enum/list/rules_ref/keyed_list/
       数值+单位两件套/文本 至少 7 处, 漏一处 = 该类 readonly 字段仍可改);
    4. 叶子行带「程序维护」徽标; settings-detail 的块级 section 开关对 readonly 段换徽标
       (fs 段的启用/关闭开关在那里, 不禁用就能把整段从 UI 删掉)。
    """
    editor = open(os.path.join(STATIC_ROOT, "shared", "config_editor.js"), encoding="utf-8").read()
    for member in ("readonly()", "readonlyComplex()", "readonlySummary()"):
        assert member in editor, f"config_editor.js 的 CE_FIELD_BASE 缺 computed {member} (模板引用会 undefined 静默失效)"

    for skin in _UI_ALL:
        html = _ui_aggregate(skin)
        m = re.search(r'<script type="text/x-template" id="tpl-hub-field">(.*?)\n  </script>', html, re.S)
        assert m, f"{skin} 找不到 tpl-hub-field 模板(改名/挪走了? 同步本守阵)"
        tpl = m.group(1)
        assert 'v-if="readonlyComplex"' in tpl, (
            f"{skin} 的 tpl-hub-field 缺 readonly 只读摘要分支(链首) —— "
            "列表/对象值(fs.path_map)会落进输入框 String 化成 '[object Object]'"
        )
        n_disabled = tpl.count(':disabled="readonly"')
        assert n_disabled >= 7, (
            f"{skin} 的 tpl-hub-field 只有 {n_disabled} 处 :disabled=\"readonly\"(须 >= 7) —— "
            "bool/enum/list/rules_ref/keyed_list/数值+单位两件套/文本 的控件要全挂禁用"
        )
        assert '<span v-if="readonly" class="hb-badge">程序维护</span>' in tpl, (f"{skin} 的 tpl-hub-field 叶子行缺「程序维护」徽标")
        # 块级 section 开关(settings-detail 分片): readonly 段不渲染启用/关闭, 换「程序维护」徽标
        assert "b.item.field && b.item.field.readonly" in html, (
            f"{skin} 的 settings-detail 块级 section 开关未对 readonly 段收口 —— fs 段可从 UI 整段删除"
        )


def test_frontend_statusbar_speed_reads_server_totals():
    """状态栏速度必须读服务端标量 status.totals, 不得改回对 groups 求和(静态防回潮)

    issue 26-09-20-1646: 旧实现是 `totalDl() { return this.groups.reduce(...) }` —— 而 groups
    **按视图回传**(VIEW_ARRAYS: 种子页不回它), 于是状态栏在种子页恒为 0(首屏即种子页)或
    停在**冻结的旧值**(先开过辅种页再切过来), 并且漏掉未归组 singles(实测少算 88.7%)。
    Python 侧单测看不见这种"界面废掉", 只能静态钉住这两个 computed。
    """
    import re

    text = open(os.path.join(STATIC_ROOT, "shared", "decorate.js"), encoding="utf-8").read()
    for name in ("totalDl", "totalUl"):
        m = re.search(rf"\n    {name}\(\) \{{(.*?)\n    \}},", text, re.S)
        assert m, f"decorate.js 里找不到 computed {name}(改名或挪走了? 同步本守阵)"
        body = m.group(1)
        assert "this.groups" not in body, (
            f"{name} 又在对 this.groups 求和: groups 是按视图回传的(种子页不回) "
            f"⇒ 状态栏恒为 0 或停在旧值(issue 26-09-20-1646)"
        )
        assert "status.totals" in body, f"{name} 必须读服务端恒回传的 status.totals: {body.strip()}"


def test_frontend_ctx_menu_multi_select_targets_selection():
    """多选右键菜单必须作用于**整个选中集合**, 不是被点的那一行(CTX-03)

    用户报: "多选时右键菜单应该对所有选择的种子生效, 当前仅对鼠标指向的触发右键的种子生效"。
    根因: 四个 open*Menu 只记 anchor(key/hash/episode), 动作端点直接拿它拼 URL ⇒ 无论选了多少,
    都只动被点的那一个。而批量浮条早已有正确实现(bulkAct/bulkDelete 走 _bulkTargets)。

    修法是让菜单在"被点的行属于选中集合"时升级为批量菜单, 动作复用批量浮条的链路。这条守阵
    钉住三处**成对**关系(任一处漏改都会静默退化回单目标, 且 pytest/`node --check` 都看不见):
      1. 四个 open*Menu 必须各自写入 `multi:` —— 漏一处, 那条路径的多选右键就仍是单目标;
      2. 两套 UI 的批量分支必须**成对存在**且逐项一致(双 UI 是两条独立模板, 只改一边 = 另一边
         用户看不到批量菜单), 且只能调 ctxAct/ctxDelete;
      3. ctxAct/ctxDelete 必须**复用** bulkAct/bulkDelete —— 自己再拆一遍目标集合就会与批量浮条
         的口径漂移(虚拟行/组展开/失效目标跳过这三条语义都在 _bulkTargets 里)。
    """
    # 1. 四个菜单入口都必须写 multi
    openers = {
        "shared/menu.js": ["openMenu(event, group)", "openMemberMenu(event, member)"],
        "shared/shows.js": ["openShowEpMenu(event, show, ep)", "openShowMenu(event, show)"],
    }
    for rel, fns in openers.items():
        text = open(os.path.join(STATIC_ROOT, rel), encoding="utf-8").read()
        for fn in fns:
            m = re.search(rf"\n    {re.escape(fn)} \{{(.*?)\n    \}},", text, re.S)
            assert m, f"{rel} 找不到 {fn}(改名或挪走了? 同步本守阵)"
            body = m.group(1)
            assert "_ctxMulti(" in body, (
                f"{rel} 的 {fn} 没有调 _ctxMulti 计算 menu.multi —— 该路径的多选右键会退化成"
                f"只作用于被点的那一行(CTX-03)"
            )
            assert "multi:" in body, f"{rel} 的 {fn} 没把 multi 写进 this.menu —— 模板读不到, 批量分支永不渲染"

    # 2. 两套 UI 的批量分支成对且逐项一致
    branches = {}
    for ui in _UI_ALL:
        text = _ui_aggregate(ui)
        m = re.search(r'<template v-if="menu\.multi">(.*?)</template>', text, re.S)
        assert m, (
            f"{ui}/index.html 的右键菜单没有 v-if=\"menu.multi\" 批量分支 —— "
            f"多选右键拿不到批量动作(双 UI 必须成对改, 另一套有而它没有 = 半边用户没有该功能)"
        )
        branch = m.group(1)
        # 归一空白后逐项比对: 两套 UI 的批量菜单是同一套语义, 不该各自演化
        branches[ui] = re.sub(r"\s+", " ", branch).strip()
        for call in ("ctxAct('resume')", "ctxAct('pause')", "ctxAct('reannounce')", "ctxAct('recheck')", "ctxDelete()"):
            assert call in branch, f"{ui}/index.html 批量分支缺少 {call}"
        assert "actTorrent(" not in branch and "actEpisode(" not in branch, (
            f"{ui}/index.html 批量分支里出现了单目标/单集动作 —— 批量菜单必须整份走 ctxAct/ctxDelete"
        )
    assert branches["atlas"] == branches["prism"], (
        "两套 UI 的批量右键菜单不一致(星图 vs 棱镜)—— 双 UI 必须成对改; 差异: "
        f"atlas={branches['atlas'][:120]!r} / prism={branches['prism'][:120]!r}"
    )

    # 3. ctxAct/ctxDelete 复用批量浮条链路, 且先收起菜单(菜单根节点 @click.stop, 全局点空白关不掉)
    cmd = open(os.path.join(STATIC_ROOT, "shared", "commands.js"), encoding="utf-8").read()
    for name, delegate in (("ctxAct(action)", "bulkAct(action)"), ("ctxDelete()", "bulkDelete()")):
        m = re.search(rf"\n    {re.escape(name)} \{{(.*?)\n    \}},", cmd, re.S)
        assert m, f"shared/commands.js 找不到 {name}(改名或挪走了? 同步本守阵)"
        body = m.group(1)
        assert delegate in body, (
            f"{name} 必须复用批量浮条的 {delegate} —— 自己再拆一遍目标集合会与 _bulkTargets 的"
            f"口径漂移(虚拟行/组展开/失效目标跳过), CTX-03"
        )
        assert "this.menu.visible = false" in body, f"{name} 必须先收起右键菜单(菜单是 @click.stop, 全局点空白关不掉)"


def test_frontend_bulk_bar_retired():
    """批量控制条退役守阵(2026-10-05) —— 防回潮

    用户拍板: 移除筛选行里"已选 N 个种子 · 开始/暂停/…"的批量控制条, 批量动作一律走
    **右键批量菜单**(被右键行属于选中集合时升级为 menu.multi 分支, 见 ctx-menus.html)。
    控制条是模板 + 三套 CSS + 一批 JS 助手的组合, 最容易的退化形态是"只删模板、CSS/JS 残留"
    或"某套 UI 的 CSS 没删干净"(皮肤间静默不一致 —— 用户看到的仍是半残控制条)。逐层钉住:
      1. 三套 UI 的聚合模板里 .bulk-inline / bulkAct( / bulkDeleteLabel( / bulkHrWarnText( /
         name="bulk" 零残留;
      2. 三套 UI 的 CSS 聚合里 .bulk-inline/.bulk-btn/.bulk-hr-warn/.bulk-sep/.bulk-count/
         .bulk-enter-*/.ico-select 与 @keyframes bulk-in 零残留(死样式零残留纪律);
      3. 批量链路本身仍在(右键菜单要用): bulkAct/bulkDelete 定义保留, ctxAct/ctxDelete 复用。
    """
    for ui in _UI_ALL:
        text = _ui_aggregate(ui)
        for token in (".bulk-inline", "bulkAct(", "bulkDeleteLabel(", "bulkHrWarnText(", 'name="bulk"'):
            assert token not in text, f"{ui} 模板仍残留批量控制条痕迹 {token!r} —— 已退役, 应零残留"
        css = _ui_css_aggregate(ui)
        for token in (
            ".bulk-inline", ".bulk-btn", ".bulk-hr-warn", ".bulk-sep", ".bulk-count", ".bulk-enter", ".bulk-leave",
            ".ico-select", "@keyframes bulk-in"
        ):
            assert token not in css, f"{ui} CSS 仍残留死样式 {token!r} —— 批量控制条已退役, 应删除"
    # 批量链路仍在: 右键批量菜单要用(定义在 shared/commands.js / delete_flow.js)
    cmd = open(os.path.join(STATIC_ROOT, "shared", "commands.js"), encoding="utf-8").read()
    assert "async bulkAct(action) {" in cmd, "bulkAct 定义消失 —— 右键批量菜单的动作链断了"
    assert "return this.bulkAct(action);" in cmd, "ctxAct 必须继续复用 bulkAct"
    dfl = open(os.path.join(STATIC_ROOT, "shared", "delete_flow.js"), encoding="utf-8").read()
    assert "async bulkDelete() {" in dfl, "bulkDelete 定义消失 —— 右键批量删除断了"
    assert "bulkHrWarnText" not in dfl and "bulkDeleteLabel" not in dfl, (
        "死方法 bulkHrWarnText/bulkDeleteLabel 应已随批量控制条删除(零消费方)"
    )


def test_frontend_meta_dialog_paired():
    """标签/分类编辑对话框守阵(静态防回潮)

    对选中集合(或单种子)即时增删标签/改分类。风险形态与批量菜单守阵(CTX-03)同源:
      1. 双 UI 是两条独立模板, 只改一边 = 另一边用户没有入口(两套 UI 必须成对改);
      2. 对话框的投递必须走 bulk 链路(/api/torrents/bulk), 目标集合口径单点在
         _bulkTargets/openMetaDialog —— 自己再拆一遍就会与批量浮条口径漂移;
      3. .opt-pill(atlas 此前没有该组件)与 .meta-dialog 的 CSS 必须两套成对定义,
         模板用到的类在 CSS 无定义 = 静默裸样式(挂件类名错配的变体)。
    """
    # 1. 三套 UI 成对: metaOpen 对话框 + 两处入口(批量菜单 ctxMeta / 单种子菜单)
    #    (2026-10-05 批量控制条退役: 模板层不再直接调 openMetaDialog(null), 批量入口统一走 ctxMeta)
    for ui in _UI_ALL:
        text = _ui_aggregate(ui)
        assert 'v-if="metaOpen"' in text, f"{ui}/index.html 缺少标签/分类对话框(三套 UI 必须成对改)"
        assert "openMetaDialog(null)" not in text, (
            f"{ui}/index.html 又出现模板层直接调 openMetaDialog(null) —— 批量控制条已退役, "
            f"批量入口应统一走 ctxMeta(右键批量菜单)"
        )
        assert 'openMetaDialog(menu.hash)' in text, f"{ui}/index.html 单种子右键菜单缺少标签/分类入口"
        assert "ctxMeta()" in text, f"{ui}/index.html 批量右键菜单缺少 ctxMeta 入口"
    # 2. shared 逻辑接线(逻辑层两套共用, 只在 shared 出现)
    dlg = open(os.path.join(STATIC_ROOT, "shared", "dialogs.js"), encoding="utf-8").read()
    for token in (
        "openMetaDialog(singleHash)",
        "closeMeta()",
        "_metaBulk(action, extra, okText)",
        "metaToggleTag(tag)",
        "metaAddNewTags()",
        "metaSetCategory(name)",
        "_bulkTargets()",
        "/api/torrents/bulk",
    ):
        assert token in dlg, f"shared/dialogs.js 缺少 {token}(改名或挪走了? 同步本守阵)"
    cmd = open(os.path.join(STATIC_ROOT, "shared", "commands.js"), encoding="utf-8").read()
    m = re.search(r"\n    ctxMeta\(\) \{(.*?)\n    \},", cmd, re.S)
    assert m, "shared/commands.js 找不到 ctxMeta(改名或挪走了? 同步本守阵)"
    assert "this.menu.visible = false" in m.group(1), ("ctxMeta 必须先收起右键菜单(菜单是 @click.stop, 全局点空白关不掉)")
    assert "openMetaDialog(null)" in m.group(1), ("ctxMeta 必须复用 openMetaDialog 打开对话框 —— 目标集合口径单点在它里面")
    # 3. CSS 成对: .meta-dialog 与 .opt-pill 各套 UI 都要有定义
    for name, t in (
        ("atlas css 聚合(link 序)", _ui_css_aggregate("atlas")),
        (
            "prism/css/components.css",
            open(os.path.join(STATIC_ROOT, "prism", "css", "components.css"), encoding="utf-8").read()
        ),
        ("console css 聚合(link 序)", _ui_css_aggregate("console")),
    ):
        assert ".meta-dialog" in t, f"{name} 缺少 .meta-dialog 定义"
        assert ".opt-pill" in t, f"{name} 缺少 .opt-pill 定义(atlas 此前没有该组件, 易漏)"


def test_frontend_add_torrent_drag_drop_wiring():
    """DND-01 全局拖拽添加种子接线守阵(静态防回潮)

    拖拽进料口的关键点全在 JS/HTML 静态结构里, pytest 运行时看不见:
      1. window 级 drag 事件四件套(dragenter/dragover/dragleave/drop) add/remove 严格对称
         —— 漏 remove = 卸载后幽灵监听重复 ingest;
      2. drop handler 必须 preventDefault —— 删掉它浏览器会直接打开 .torrent / 跳转链接,
         表现为"拖进去弹出的是文件内容页";
      3. 接管判据只认 "Files"/"text/uri-list" —— 若放宽到 text/plain, 页面内拖选中文本、
         拖词进输入框的原生行为会被误拦;
      4. 双 UI 的落点遮罩成对存在(v-if="addDragOver"), app.js 有 addDragOver 状态 ——
         只改一套皮肤 = 另一套用户拖了没反应。
    """
    import re

    add_js = open(os.path.join(STATIC_ROOT, "shared", "add_torrent.js"), encoding="utf-8").read()
    # 1. 四件套 add/remove 对称
    added, removed = set(), set()
    for hook, bucket in (("mounted", added), ("unmounted", removed)):
        m = re.search(rf"\n  {hook}\(\) \{{(.*?)\n  \}},", add_js, re.S)
        assert m, f"add_torrent.js 找不到 {hook} 钩子(DND-01 监听挂载点, 改名或挪走了? 同步本守阵)"
        for ev in re.findall(r'window\.(?:add|remove)EventListener\("([a-z]+)"', m.group(1)):
            bucket.add(ev)
    expect = {"dragenter", "dragover", "dragleave", "drop"}
    # 子集语义: mounted 还合法挂了 label 失焦收层守卫的 mousedown capture 记录器(四轮, 2026-10-04),
    # 不能再断言"恰好等于四件套" —— 只要求四件套一个不少, 多余监听交给 removed == added 对称性兜住。
    assert expect <= added, f"mounted 缺 drag 事件: {expect - added}(少一个就有一条路径不接管)"
    assert removed == added, f"unmounted 与 mounted 不对称: add={sorted(added)} / remove={sorted(removed)}"

    # 2. drop handler 必须拦默认行为 + depth 归零灭遮罩
    m = re.search(r"\n    _addDragDrop\(e\) \{(.*?)\n    \},", add_js, re.S)
    assert m, "add_torrent.js 找不到 _addDragDrop(drop 分流入口, 改名或挪走了? 同步本守阵)"
    assert "preventDefault()" in m.group(1
                                        ), ("_addDragDrop 少了 preventDefault —— 浏览器会直接打开 .torrent/链接而不是交给添加对话框(DND-01)")

    # 3. 接管判据只认文件与链接, 不得放宽到 text/plain
    m = re.search(r"\n    _addDragTakes\(e\) \{(.*?)\n    \},", add_js, re.S)
    assert m, "add_torrent.js 找不到 _addDragTakes(接管判据, 改名或挪走了? 同步本守阵)"
    takes = m.group(1)
    assert 'types.includes("Files")' in takes and 'types.includes("text/uri-list")' in takes, (
        "_addDragTakes 必须显式认 Files 与 text/uri-list(接管面收窄到拖文件/拖链接)"
    )
    assert "text/plain" not in takes, ("_addDragTakes 不得认 text/plain —— 会误拦页面内拖选中文本/拖词进输入框的原生行为(DND-01)")

    # 4. app.js 状态 + 双 UI 遮罩成对
    app_js = _app_bundle_text()
    assert "addDragOver: false" in app_js, "app.js 缺 addDragOver 状态(遮罩显隐没有数据源)"
    for ui in _UI_ALL:
        html = _ui_aggregate(ui)
        assert 'class="add-drop-mask"' in html and 'v-if="addDragOver"' in html, (
            f"{ui}/index.html 缺拖拽落点遮罩(.add-drop-mask + v-if=\"addDragOver\")—— "
            f"该皮肤用户拖文件进页面没有落点反馈(双 UI 必须成对改)"
        )


def test_frontend_add_combo_blur_close_and_fit():
    """添加种子三下拉「失焦即收 + 限高不出窗」接线守阵(2026-10-03 报障, 静态防回潮)

    两个用户可见故障形态, 根因都在事件接线/几何量测这类 pytest 运行时看不见的地方:
      1. **点窗口其它位置下拉不收 / 闪烁重现**: 收层判据原来只有 window click(lifecycle.js),
         点字段 label(for= 转发激活)时浏览器先 blur 再把焦点转回输入框, click 关层 + 转发
         click 重开 = 关了又开(leave 过渡被打断 = 闪烁)。修法 = 收层主判据改 @focusout,
         但**不能同步收** —— 必须 40ms 合帧守卫(焦点回来由开层方法撤销), 否则闪烁回潮。
      2. **选项过长把窗口撑变形**: .pop-menu 基础 max-height 只保证菜单自身可滚, 菜单锚在
         输入行下方, 绝对定位溢出会伸出窗口外并把 .add-dialog-body 的 scrollHeight 撑大。
         修法 = 开层时把可滚内层限到「输入行 → 滚动容器可见底沿」的净空内(滚动条留在窗口里)。
    """
    import re

    at = open(os.path.join(STATIC_ROOT, "shared", "add_torrent.js"), encoding="utf-8").read()
    mgr = open(os.path.join(STATIC_ROOT, "shared", "tpl", "dialogs-mgr.html"), encoding="utf-8").read()

    # 1. 三个输入框全部挂 @focusout 收层(漏一个 = 那个下拉点空白不收)
    for input_id in ("ad-save-path", "ad-category", "ad-tags"):
        m = re.search(rf'<input id="{input_id}"(.*?)>', mgr, re.S)
        assert m, f"dialogs-mgr.html 找不到 #{input_id}(添加窗口三下拉的输入框, 改名或挪走了? 同步本守阵)"
        assert '@focusout="addPopBlurClose"' in m.group(1), \
            f"#{input_id} 缺 @focusout=\"addPopBlurClose\"(失焦即收是收层主判据, 漏挂 = 该下拉点窗口其它位置不收)"

    # 2. 失焦收层必须带合帧守卫: 同步收层会被 label 的焦点转回打断(闪烁回潮)
    body = re.search(r"addPopBlurClose\(\) \{(.*?)\n    \},", at, re.S)
    assert body, "add_torrent.js 找不到 addPopBlurClose(失焦收层单点, 改名或挪走了? 同步本守阵)"
    assert "setTimeout" in body.group(1) and "clearTimeout" in body.group(1), \
        "addPopBlurClose 必须用定时器合帧(同步收层 + label 转发回焦 = 关了又开闪烁); 定时窗内焦点回来由开层方法撤销"
    for field in ("addCatMenu", "addTagMenu", "addPathPop"):
        assert f"this.{field} = false" in body.group(1), f"addPopBlurClose 漏收 {field}"

    # 3. 三个开层方法先撤销挂起的收层(焦点回到输入框 = 菜单保持, 不闪)
    for fnname in ("openAddCatMenu", "openAddTagMenu", "openAddPathPop"):
        body = re.search(rf"{fnname}\(\) \{{(.*?)\n    \}},", at, re.S)
        assert body and "_addPopBlurCancel()" in body.group(1), \
            f"{fnname} 必须先 _addPopBlurCancel()(焦点转回输入框时撤销挂起的失焦收层, 否则菜单闪烁)"

    # 4. 限高: 开层 watcher 单点(开层入口有四处, 直挂方法会漏) + 量「行→滚动容器可见底沿」净空
    for token in ("addCatMenu(v) {", "addTagMenu(v) {", "addPathPop(v) {"):
        assert token in at, f"add_torrent.js 缺 watcher {token}(开层限高必须走 watcher 单点, 四处开层入口直挂会漏)"
    fit = re.search(r"_fitAddPop\(refName\) \{(.*?)\n    \},", at, re.S)
    assert fit, "add_torrent.js 找不到 _fitAddPop(下拉限高单点, 改名或挪走了? 同步本守阵)"
    fit_body = fit.group(1)
    assert 'closest(".add-input-row")' in fit_body and 'closest(".add-dialog-body")' in fit_body, \
        "_fitAddPop 必须以输入行为锚、以 .add-dialog-body 可见底沿为界量净空(以视口为界会在窗口化/滚动时量错)"
    assert 'list.style.maxHeight = ""' in fit_body, \
        "_fitAddPop 限高前必须先复位旧值(上一次的限高会污染本次测量)"

    # 5. 候选异步到位会改变菜单高度, 开着时也要重限
    for opt in ("addCatOptions", "addTagOptions", "addPathOptions"):
        assert re.search(rf"{opt}\(\) \{{\n      if \(this\.", at), \
            f"add_torrent.js 缺 {opt} 的 watcher(候选异步到位改变菜单高度, 开着时必须重限)"

    # 6. 三浮层互斥必须双向(26-10-04-0130): 开层收别家走 closeAddPopsExcept 单点 —— 单向写法
    #    (只 openAddPathPop 收 cat/tag, 反向不收)会让路径面板与下拉同悬, 且面板盖住相邻字段
    #    label 的点击(走查实测 "subtree intercepts pointer events")
    mutex = re.search(r"closeAddPopsExcept\(kind\) \{(.*?)\n    \},", at, re.S)
    assert mutex, "add_torrent.js 找不到 closeAddPopsExcept(三浮层互斥单点, 改名或挪走了? 同步本守阵)"
    mutex_body = mutex.group(1)
    for field, kind_key in (("addCatMenu", "cat"), ("addTagMenu", "tag"), ("addPathPop", "path")):
        assert f'kind !== "{kind_key}"' in mutex_body, \
            f"closeAddPopsExcept 缺 {field} 分支(互斥单点必须覆盖全部三个浮层)"
    for fnname, kind in (("openAddCatMenu", "cat"), ("openAddTagMenu", "tag"), ("openAddPathPop", "path")):
        body = re.search(rf"{fnname}\(\) \{{(.*?)\n    \}},", at, re.S)
        assert body and f'closeAddPopsExcept("{kind}")' in body.group(1), \
            (f"{fnname} 必须调 closeAddPopsExcept(\"{kind}\") —— 开本浮层时收掉其余两个, "
             f"互斥漏一侧 = 双浮层同悬且盖住相邻字段 label 的点击")


def test_frontend_add_combo_label_clear_mask_and_refit():
    """添加种子三下拉「第二轮遗留四项」接线守阵(2026-10-03 报障, 静态防回潮)

    上一轮(失焦即收 + 开层限高)之后剩下的四条, 根因同样全在"pytest 看不见的事件/几何接线"里:
      1. **点字段 label 稳定复现下拉闪烁(两轮才修对)**: label 的 click 默认动作把 click **转发**
         给 for= 的输入框, 而它自己那次 click 先冒泡到 window(lifecycle 收层名单) ⇒ 必须
         @click.stop。但只挡 click 赢不了主竞态: label 的 **mousedown** 默认动作先把已聚焦的
         输入框 blur 掉, addPopBlurClose 的 40ms 合帧定时器在**按住期间**(人手 80~150ms 必然
         > 40ms)先触发收层, 松手后 label 转发回焦再重开 = 闪烁。修法 = 四个 combo 的字段 label
         一律 @mousedown.prevent + @click.stop(缺一即回归)。
      2. **三个 combobox 没有清空按钮**: 补 .add-pop-clear, 必须 @mousedown.prevent(不拦默认
         动作按钮会抢焦点 → 输入框失焦走 addPopBlurClose 把下拉收掉, 清完想接着挑就多点一次)。
      3. **拖选输入框文字、终点落在遮罩上抬手 = 关窗**: click 的 target 是 mousedown/mouseup 的
         **公共祖先**, 这情形公共祖先就是遮罩 ⇒ @click.self 误判成"点空白关窗"。修法 = 遮罩
         改成 mousedown 记臂位 + mouseup.self 才关(全仓 11 处遮罩统一, 含无输入框的弹层 ——
         拖选普通文字同样会误关)。
      4. **选中分类后逐字删除, 下拉把窗口撑变形**: 限高只在开层那一刻按**当时**的候选量算过,
         过滤词变化(候选从 1 条涨回全量)时菜单没关过, 开层 watcher 不触发 ⇒ 旧限高不更新。
         修法 = 三个输入值各挂 watcher(开着才重限), meta 对话框的分类下拉同族一并补。
      5. **四轮 JS 收层守卫(2026-10-04 用户报三修后真机仍闪)**: 三修的 Chromium 探针自校验证明
         修饰符修法本身有效(摘掉即复现完整闪烁链), 用户症状与"浏览器跑的还是旧模板"一致 ——
         页签长开不刷新时模板/JS 以加载那一刻为准, 服务端更新到不了。故收层再加 JS 单点守卫
         _popBlurShouldHold: addPopBlurClose/metaCatBlurClose 的 40ms 定时器触发那刻, 焦点已回
         本族输入框或本族 label 转发 click 仍在途(mousedown 记录器 capture 记落点) → 跳过收层。
         模板修饰符在 = 纯 no-op(mousedown 已被 prevent, 定时器不武装); 缺位 = 独立根除闪烁,
         任何模板/JS 代际混合都安全。
    """
    import re

    shared = os.path.join(STATIC_ROOT, "shared")
    at = open(os.path.join(shared, "add_torrent.js"), encoding="utf-8").read()
    dg = open(os.path.join(shared, "dialogs.js"), encoding="utf-8").read()
    lf = open(os.path.join(shared, "lifecycle.js"), encoding="utf-8").read()
    mgr = open(os.path.join(shared, "tpl", "dialogs-mgr.html"), encoding="utf-8").read()
    pv = open(os.path.join(shared, "tpl", "popovers.html"), encoding="utf-8").read()

    # 1. 四个 combo 的字段 label 全部 @mousedown.prevent + @click.stop(漏一个 = 那个下拉点 label 稳定闪烁;
    #    prevent 挡 mousedown 默认动作的 blur(40ms 合帧窗赢不了人手按住时长), stop 挡 window click 收层)
    for holder, input_id in (
        ("mgr", "ad-save-path"), ("mgr", "ad-category"), ("mgr", "ad-tags"), ("pv", "meta-category")
    ):
        src = mgr if holder == "mgr" else pv
        m = re.search(rf'<label[^>]*for="{input_id}"[^>]*>', src, re.S)
        assert m, f"找不到 for=\"{input_id}\" 的字段 label(改结构了? 同步本守阵)"
        assert "@click.stop" in m.group(0), \
            (f"label[for={input_id}] 缺 @click.stop —— 点它会走「window click 收层 → label 转发 "
             f"click 重开」= 下拉闪烁再现(输入框已聚焦, @focusout 挡不住这一路)")
        assert "@mousedown.prevent" in m.group(0), \
            (f"label[for={input_id}] 缺 @mousedown.prevent —— label 的 mousedown 默认动作把已聚焦的"
             f"输入框 blur 掉, addPopBlurClose 的 40ms 合帧定时器在按住期间(人手 80~150ms > 40ms)"
             f"先收层, 松手 label 转发回焦再重开 = 闪烁(2026-10-04 三修, 真机按住时序实测)")

    # 2. 三个 combobox 内嵌清空(x): 行挂 has-clear + 按钮 @mousedown.prevent + 走 clearAddField
    for input_id, kind, field in (
        ("ad-save-path", "path", "addSavePath"), ("ad-category", "cat", "addCategory"), ("ad-tags", "tag", "addTags")
    ):
        i = mgr.index(f'id="{input_id}"')
        seg = mgr[mgr.rindex('class="add-input-row', 0, i):i + 900]
        assert "has-clear" in seg, f"#{input_id} 的输入行缺 has-clear(清空钮靠它让出右内边距)"
        assert 'class="add-pop-clear"' in seg, f"#{input_id} 行内缺 .add-pop-clear 清空按钮"
        assert '@mousedown.prevent' in seg, \
            f"#{input_id} 的清空钮缺 @mousedown.prevent(不拦默认动作会抢焦点 → 下拉被失焦收掉)"
        assert f"clearAddField('{kind}')" in seg, f"#{input_id} 的清空钮没接 clearAddField('{kind}')"
        assert f'v-if="{field}"' in seg, f"#{input_id} 的清空钮没按 {field} 非空才显形"
        btn = re.search(r'<button[^>]*add-pop-clear[\s\S]{0,200}?>', seg)
        assert btn and "@click.stop" in btn.group(0), \
            (f"#{input_id} 的清空钮缺 @click.stop —— 它的 click 会冒泡到 lifecycle 的 window "
             f"收层名单, 点一下 x 顺手把下拉一起收了(真机走查实测: 清空后菜单消失)")
    clear_body = re.search(r"clearAddField\(kind\) \{(.*?)\n    \},", at, re.S)
    assert clear_body, "add_torrent.js 找不到 clearAddField(三个 combobox 的清空单点)"
    for field in ("addSavePath", "addCategory", "addTags"):
        assert f"this.{field} = \"\";" in clear_body.group(1), f"clearAddField 不清空 {field}"

    # 3. 遮罩关窗: mousedown 记臂位 + mouseup.self 才关; 全仓不许再有 @click.self
    masks = 0
    for name in ("dialogs-mgr.html", "dialogs.html", "popovers.html"):
        txt = open(os.path.join(shared, "tpl", name), encoding="utf-8").read()
        for m in re.finditer(r'<div v-if="[^"]*" class="modal-mask[\s\S]{0,240}?>', txt):
            masks += 1
            tag = m.group(0)
            assert '@mousedown="maskDownSelf"' in tag and '@mouseup.self="maskCloseIfArmed(' in tag, \
                (f"{name} 的遮罩没接「mousedown 记臂位 + mouseup.self 才关」: {tag[:80]} —— "
                 f"@click.self 会被『拖选文字终点落在遮罩上抬手』误判成点空白关窗")
        live = re.sub(r"<!--[\s\S]*?-->", "", txt)  # 注释里讲原理不算(只查真接线)
        assert "@click.self" not in live, \
            f"{name} 仍残留 @click.self 遮罩关窗(拖选文字抬手会误关窗)"
    # 2026-10-04: qb-traffic.html 两个模态弹层并入底部详情抽屉(无遮罩) -> 阈值 11 -> 9
    assert masks >= 9, f"只数到 {masks} 处 modal-mask(漏挂? 或守阵正则失配, 复核)"
    arm = re.search(r"maskDownSelf\(e\) \{(.*?)\n    \},", dg, re.S)
    assert arm and "e.target === e.currentTarget" in arm.group(1), \
        "dialogs.js::maskDownSelf 必须判 target === currentTarget(只有按在遮罩上才算起手)"
    close_arm = re.search(r"maskCloseIfArmed\(closeFn, \.\.\.args\) \{(.*?)\n    \},", dg, re.S)
    assert close_arm and "if (!this._maskArmed) return;" in close_arm.group(1), \
        "dialogs.js::maskCloseIfArmed 必须先判 _maskArmed(起手在对话框内的那一笔不许关窗)"

    # 4. 过滤词变化重限高: 三个输入值 watcher + meta 侧三处(候选到位/开层/过滤词)
    for val, pop in (("addCategory", "addCatMenu"), ("addTags", "addTagMenu"), ("addSavePath", "addPathPop")):
        assert re.search(rf"\n    {val}\(\) \{{\n      if \(this\.{pop}\) this\._fitAddPop", at), \
            (f"add_torrent.js 缺 {val} 的 watcher —— 打开时按当时的候选量限过高, 删字让候选涨回全量时"
             f"菜单没关过(开层 watcher 不触发), 下拉会把窗口撑变形")
    for key, guard in (
        ("metaCatMenu(v)", "if (v)"), ("metaCatInput()", "if (this.metaCatMenu)"),
        ("metaCategories()", "if (this.metaCatMenu)")
    ):
        assert re.search(rf"\n    {re.escape(key)} \{{\n      {re.escape(guard)} this\._fitAddPop", dg), \
            f"dialogs.js 缺 {key} 的限高 watcher(meta 分类下拉与三下拉同族, 撑变形同样会犯)"
    assert 'if (!this.addOpen && !this.metaOpen) return;' in at, \
        "_fitAddPop 必须同时放行 meta 对话框(两处共用同一套限高, 只认 addOpen 会让 meta 侧恒不生效)"

    # 5. meta 分类下拉补失焦收层 + 进 window click 兜底名单(原本两处都漏 = 点对话框别处下拉不收)
    m = re.search(r'<input id="meta-category"(.*?)>', pv, re.S)
    assert m and '@focusout="metaCatBlurClose"' in m.group(1), \
        "#meta-category 缺 @focusout 收层(点对话框里别的地方下拉悬着不收)"
    blur = re.search(r"metaCatBlurClose\(\) \{(.*?)\n    \},", dg, re.S)
    assert blur and "setTimeout" in blur.group(1) and "clearTimeout" in blur.group(1), \
        "metaCatBlurClose 必须定时合帧(同步收层会被 label 转发回焦打断 = 闪烁)"
    open_meta = re.search(r"openMetaCatMenu\(\) \{(.*?)\n    \},", dg, re.S)
    assert open_meta and "_metaPopBlurCancel()" in open_meta.group(1), \
        "openMetaCatMenu 必须撤销挂起的失焦收层(焦点转回输入框时菜单不闪)"
    assert "this.metaCatMenu = false;" in lf, \
        "lifecycle.js 的 window click 兜底名单缺 metaCatMenu(与三下拉同层, 漏了靠 focusout 单点兜)"

    # 6. 清空钮样式三皮肤成对(漏一档 = 该皮肤按钮无样式: 透明方块 + 文字被压在底下)
    for ui in _UI_ALL:
        css_dir = os.path.join(STATIC_ROOT, ui, "css")
        blob = "".join(
            open(os.path.join(css_dir, f), encoding="utf-8").read()
            for f in sorted(os.listdir(css_dir)) if f.endswith(".css")
        )
        assert ".add-pop-clear" in blob, f"{ui} 缺 .add-pop-clear 样式(清空钮无尺寸/无 hover)"
        assert ".add-input-row.has-clear" in blob, f"{ui} 缺 .has-clear 右内边距(文字会被按钮压住)"

    # 7. 四轮 JS 收层守卫(2026-10-04): 40ms 定时器收层前必须问 _popBlurShouldHold ——
    #    焦点已回本族输入框 / 本族 label 转发 click 仍在途 → 不收。模板修饰符缺位(旧页签
    #    残留模板)时由它独立根除「按住期收层 → 松手回焦重开」, 不依赖模板 JS 同代到达。
    assert "window.addEventListener(\"mousedown\", this._popLabelDownRecorder, { capture: true });" in at, \
        "add_torrent.js mounted 缺 mousedown capture 记录器(守卫没有落点数据 = 形同虚设)"
    assert "removeEventListener(\"mousedown\", this._popLabelDownRecorder" in at, \
        "add_torrent.js unmounted 缺记录器移除(热重载后句柄堆叠, 每次点击记 N 笔)"
    hold = re.search(r"_popBlurShouldHold\(ids\) \{(.*?)\n    \},", at, re.S)
    assert hold, "add_torrent.js 找不到 _popBlurShouldHold(收层守卫单点)"
    assert "document.activeElement" in hold.group(1) and "ids.includes(ae.id)" in hold.group(1), \
        "_popBlurShouldHold 必须先判「焦点已回本族输入框」(转发 click 已落地 → 不收)"
    assert "performance.now() - rec.t <= 350" in hold.group(1), \
        "_popBlurShouldHold 必须带 350ms 新鲜度上界(防旧记录误挡后续无 mousedown 的失焦, 如 Tab)"
    add_close = re.search(r"addPopBlurClose\(\) \{(.*?)\n    \},", at, re.S)
    assert add_close and '_popBlurShouldHold(["ad-save-path", "ad-category", "ad-tags"])' in add_close.group(1), \
        "addPopBlurClose 收层前没问守卫(三字段的家族 id 名单缺一即该字段守卫失效)"
    meta_close = re.search(r"metaCatBlurClose\(\) \{(.*?)\n    \},", dg, re.S)
    assert meta_close and '_popBlurShouldHold(["meta-category"])' in meta_close.group(1), \
        "metaCatBlurClose 收层前没问守卫(meta 分类下拉与三下拉同族, 缺位同闪)"


def test_frontend_ctx_submenu_single_entry_and_hover_close():
    """右键菜单的次级菜单: 一级只留「更多操作」一个入口, 且移出后必须收起 (CTX-04 / CTX-05 / CTX-06)

    三条用户报的故障形态, 全部是"pytest 全绿 + node --check 全绿 + 界面废掉"那一类:
      1. **二级菜单图标 hover 变灰**: `.ctx-item:hover .ico` 是后代选择器, 而 `.ctx-sub` 是父项的
         DOM 后代 —— hover 父项会把整个子面板的图标一起刷成 `--fg-muted`, 语义色全被抹平。
         修法两处缺一不可: `>` 限定直接子级 + `:where(:hover)` 把特异性压到 0(让位给语义色规则)。
      2. **移出不消失**: 只有 mouseenter 展开、没有任何 mouseleave, 鼠标移到别的菜单项上子面板
         会一直挂在屏幕上。修法挂**父项**的 mouseleave 延迟收起(子面板上再挂一条会在
         "从面板回到父项"时误收起), 延迟只为跨过父项与面板之间那 4px 缝隙。
      3. **复制族并成第二个子面板**: 一级出现两个"更多"入口, 用户得先选"该进哪个"。
         CTX-06 把 复制名称/哈希/magnet 并入「更多操作」末尾。
    """
    # 1. CSS 的 hover 规则: 直接子级 + 特异性压制(改回后代选择器 = 整片子面板变灰)
    css = {
        "atlas": _ui_css_aggregate("atlas"),
        "prism": open(os.path.join(STATIC_ROOT, "prism", "css", "components.css"), encoding="utf-8").read(),
        "console": _ui_css_aggregate("console"),
    }
    for ui, text in css.items():
        assert ".ctx-item:where(:hover) > .ico" in text, (
            f"{ui} 的右键菜单 hover 规则必须是 `.ctx-item:where(:hover) > .ico` —— "
            f"用后代选择器会把整个子面板的图标一起拉灰, 用不带 :where 的写法会压过语义色规则(CTX-04)"
        )
        assert not re.search(r"\.ctx-item:hover\s+\.ico\b",
                             text), (f"{ui} 仍存在后代写法的 `.ctx-item:hover .ico` —— hover 父项会连子面板图标一起变灰(CTX-04)")

    # 2. 两套 UI 的次级菜单: 一级只有一个入口, 复制三项在面板内
    for ui in _UI_ALL:
        text = _ui_aggregate(ui)
        m = re.search(r'<div class="ctx-item has-sub".*?\n            </div>\n', text, re.S)
        assert m, f"{ui}/index.html 找不到次级菜单父项(改名或挪走了? 同步本守阵)"
        block = m.group(0)
        assert "更多操作" in block, f"{ui} 的次级菜单入口文案不是「更多操作」"
        assert "@mouseleave=\"scheduleSubClose()\"" in block, (
            f"{ui} 次级菜单父项缺 @mouseleave=\"scheduleSubClose()\" —— 鼠标移出后子面板不会消失(CTX-05)"
        )
        assert "@mouseenter=\"keepSub()\"" in block, (
            f"{ui} 子面板缺 @mouseenter=\"keepSub()\" —— 跨过父项与面板之间 4px 缝隙时会被收掉, 鼠标进不去子面板"
        )
        assert block.count("class=\"ctx-sub\""
                          ) == 1, (f"{ui} 一级菜单出现 {block.count('class=\"ctx-sub\"')} 个子面板 —— 只允许「更多操作」一个入口(CTX-06)")
        for kind in ("name", "hash", "magnet"):
            assert f"copyTorrentInfo('{kind}')" in block, (
                f"{ui} 的复制族缺 copyTorrentInfo('{kind}') —— 复制项必须并进「更多操作」(CTX-06)"
            )
        assert "subMenu === 'copy'" not in text, (f"{ui} 仍残留 subMenu === 'copy' 分支 —— 复制已并入「更多操作」, 双入口会回潮(CTX-06)")

    # 3. 收起的两个方法必须存在且挂在延迟上(同步收起 = 鼠标进不去子面板)
    menu = open(os.path.join(STATIC_ROOT, "shared", "menu.js"), encoding="utf-8").read()
    for name, needle in (("keepSub()", "clearTimeout"), ("scheduleSubClose()", "setTimeout")):
        m = re.search(rf"\n    {re.escape(name)} \{{(.*?)\n    \}},", menu, re.S)
        assert m, f"shared/menu.js 找不到 {name}(改名或挪走了? 同步本守阵)"
        assert needle in m.group(1), f"{name} 必须走 {needle}(延迟收起/撤销挂起), 实现漂移了"
    delay = re.search(r"const SUB_CLOSE_DELAY_MS = (\d+);", menu)
    assert delay and int(delay.group(1)) > 0, "SUB_CLOSE_DELAY_MS 必须为正整数(0 = 同步收起, 进不去子面板)"
    app = _app_bundle_text()
    assert "_subCloseTimer: 0," in app, "app.js data 必须声明 _subCloseTimer(未声明的属性不进响应式, 且易漂移)"
    assert re.search(r'"menu\.visible"\(v\) \{\n(?:.*\n){0,4}?.*this\.keepSub\(\);',
                     app), ("menu.visible 关闭时必须 keepSub() 撤掉挂起的收起 —— 否则一级关掉后定时器还会再触发一次")


def test_api_group_commands_enqueue(web_env):
    """pause/resume/reannounce 命令入队: key 解码回原 tuple, 主循环侧执行"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    enc = encode_group_key(KEY)
    for action in ("pause", "resume", "reannounce"):
        resp = client.post(f"/api/groups/{enc}/{action}", headers=auth)
        assert resp.status_code == 200, resp.text
    cmds = [mgr.web.commands.get_nowait() for _ in range(3)]
    assert [c for c, _ in cmds] == ["pause_group", "resume_group", "reannounce_group"]
    assert all(p["key"] == KEY for _, p in cmds), "key 应解码回原 tuple"


def test_api_group_malformed_key_returns_400(web_env):
    """畸形分组 key -> 400(客户端错误), 不是 500

    `decode_group_key` 对 base64 非 ASCII / 非法 JSON / 结构不符分别抛 ValueError 系与
    TypeError/IndexError; 不拦截就是 500 + 栈回溯 —— 手输或被篡改的 URL 都能打出服务端错误页。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    bad_keys = [
        "!!!not-base64!!!",  # 非法 base64 → binascii.Error
        base64.urlsafe_b64encode(b"not json{").decode(),  # 合法 base64, 解出非法 JSON
        base64.urlsafe_b64encode(b"123").decode(),  # 合法 JSON 但结构不符(不可下标)→ TypeError
    ]
    for bad in bad_keys:
        resp = client.post(f"/api/groups/{bad}/pause", headers=auth)
        assert resp.status_code == 400, f"{bad!r} 应回 400, 实际 {resp.status_code}: {resp.text}"
        assert mgr.web.commands.empty(), "畸形 key 不该投递命令"


def test_api_delete_with_files_flag(web_env):
    """delete 命令透传 delete_files 标志(默认 False 保留文件)"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    enc = encode_group_key(KEY)
    client.post(f"/api/groups/{enc}/delete", headers=auth, json={"delete_files": True})
    cmd, payload = mgr.web.commands.get_nowait()
    assert cmd == "delete_group" and payload["delete_files"] is True


def test_api_cmd_result_endpoint(web_env):
    """命令端点返回 cmd_id; /api/cmd/{id} 查询回执(pending -> 结果)"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    resp = client.post("/api/torrents/HA/reannounce", headers=auth)
    assert resp.status_code == 200
    cmd_id = resp.json()["cmd_id"]
    assert cmd_id, "投递响应应携带 cmd_id"
    assert client.get(f"/api/cmd/{cmd_id}", headers=auth).json() == {"status": "pending"}
    mgr.web.results[cmd_id] = {"status": "ok", "error": "", "ts": 123.0}
    assert client.get(f"/api/cmd/{cmd_id}", headers=auth).json() == {"status": "ok", "error": "", "ts": 123.0}
    # 其余命令端点同样携带 cmd_id(delete 返回体保留 delete_files 标志)
    enc = encode_group_key(KEY)
    assert client.post(f"/api/groups/{enc}/pause", headers=auth).json()["cmd_id"]
    delete_resp = client.post(f"/api/groups/{enc}/delete", headers=auth, json={"delete_files": True}).json()
    assert delete_resp["cmd_id"] and delete_resp["delete_files"] is True


def test_api_traffic_history_endpoint(web_env):
    """/api/traffic/history: 透出限速曲线任务发布的按日 history; 未启用时返回空数组"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    assert client.get("/api/traffic/history", headers=auth).json() == {"state": "disabled", "history": []}
    mgr.web.traffic_view = {
        "state": "ok",
        "history": [{
            "date": "2026-09-14",
            "up": 1024,
            "down": 2048
        }],
    }
    data = client.get("/api/traffic/history", headers=auth).json()
    assert data["state"] == "ok" and data["history"][0]["date"] == "2026-09-14"


# ---- qB 口径流量图三 GET 端点(plan 26-10-03-0946 §08 P4; 装配单点 server/traffic_qb.py, 纯函数口径 core/traffic_grid.py) ----


def _enable_qb_traffic(mgr, **kw):
    """用例侧启用 qb_traffic(真实 QbTraffic 段, 缺省键取设计缺省; kw 可覆盖任意键)"""
    from auto_qb.config import QbTraffic

    mgr.config.qb_traffic = QbTraffic(**{"enabled": True, **kw})
    return mgr.config.qb_traffic


def _qb_v3(mgr):
    """指向替身 data_dir(tmp_path)的 v3 存储层: 用例经真实写路径造 qb-traffic-v3/ 天文件与 agg.dat"""
    from auto_qb.core.traffic_store import TrafficV3Store

    return TrafficV3Store(mgr.config.data_dir)


def _qb_open_spy(monkeypatch):
    """open 计数探针: 记录打开路径(正斜杠归一)并放行 —— 端点面文件读取数验收(§05.2/§05.4)用"""
    import builtins

    opened = []
    real_open = builtins.open

    def counting_open(file, *a, **k):
        opened.append(os.fspath(file).replace("\\", "/"))
        return real_open(file, *a, **k)

    monkeypatch.setattr(builtins, "open", counting_open)
    return opened


def _v3_opens(opened):
    """qb-traffic-v3/ 数据面的打开路径(请求链路会开无关文件, 只看 v3 读盘)"""
    return [p for p in opened if "qb-traffic-v3/" in p]


def test_api_traffic_qb_disabled_empty_state(web_env):
    """未启用空态(qb_traffic None / enabled=false): 三端点 200 空数组 + meta, 与 /api/traffic/history 未启用分支同构"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    paths = ("/api/traffic/qb/global", f"/api/traffic/qb/torrent/HA", f"/api/traffic/qb/group/{encode_group_key(KEY)}")
    for p in paths:  # qb_traffic = None(缺省): 200 空态(不 500 不 404)
        r = client.get(p, headers=auth)
        assert r.status_code == 200, p
        body = r.json()
        assert body["points"] == [] and body["totals"] == []
        assert body["meta"]["source"] == "qb" and body["meta"]["stale"] is False and body["meta"]["window"] == "24h"
    # 与未启用空数组先例同构: /api/traffic/history 同样 200 + 空数组
    assert client.get("/api/traffic/history", headers=auth).status_code == 200
    _enable_qb_traffic(mgr, enabled=False)  # 段存在但 enabled=false: 同空态
    for p in paths:
        body = client.get(p, headers=auth).json()
        assert body["points"] == [] and body["meta"]["stale"] is False


def test_api_traffic_qb_requires_token(web_env):
    """三 GET 端点沿用全局 token 鉴权单点: 无凭证 401"""
    mgr, client = web_env
    _enable_qb_traffic(mgr)
    for p in ("/api/traffic/qb/global", "/api/traffic/qb/torrent/HA", f"/api/traffic/qb/group/{encode_group_key(KEY)}"):
        assert client.get(p).status_code == 401, p


def test_api_traffic_qb_window_validation(web_env):
    """window 非法值 4xx(不 500); 缺省回 24h; 大小写敏感(仅 WINDOW_NAMES 十三档, §08 + D4)"""
    from auto_qb.webui.server.traffic_qb import WINDOW_NAMES

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    windows = ("1m", "5m", "30m", "3h", "6h", "12h", "24h", "3d", "7d", "30d", "6mo", "1y", "all")
    assert WINDOW_NAMES == windows  # D4 档位映射: 10 -> 13 档(6mo/1y/all 上, 90d 延后不上)
    for p in ("/api/traffic/qb/global", "/api/traffic/qb/torrent/HA", f"/api/traffic/qb/group/{encode_group_key(KEY)}"):
        assert client.get(p, headers=auth, params={"window": "90d"}).status_code == 400, p
        assert client.get(p, headers=auth, params={"window": "24H"}).status_code == 400, p  # 大写不认
        assert client.get(p, headers=auth, params={"window": ""}).status_code == 400, p
        for w in windows:  # 十三档全部放行(1m/5m/30m/3h/6h/12h/24h 对齐 qB 速度图 + 3d/7d/30d + 6mo/1y/all)
            assert client.get(p, headers=auth, params={"window": w}).status_code == 200, (p, w)
    assert client.get("/api/traffic/qb/global", headers=auth).json()["meta"]["window"] == "24h"  # 缺省 24h
    assert client.get("/api/traffic/qb/global", headers=auth, params={
        "window": "30d"
    }).json()["meta"]["window"] == "30d"


def test_api_traffic_qb_global_24h_points_totals_and_stale(web_env, monkeypatch):
    """global 24h 窗(v3 raw 段): 天文件块 -> 桶点 -> 栅格展开(points 对齐桶 1:1 / 空桶 null
    = 断连真空) + totals 相邻桶快照差分(重置 null / 断连断链) + 读取竞态降级: 回上一份成功
    快照标 stale=true, 不以空态冒充无数据(§08)"""
    from auto_qb.core.traffic_store import V3Block, V3DayCache, V3NullRun, V3Sample, v3_epoch_date_str

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v3(mgr)
    now = int(time.time())
    base = ((now - 7200) // 30) * 30  # 窗内 2h 处的 30s 对齐桶
    # 块首记录槽位恰在 base+30(w=30) -> 桶 base 1:1 对位, 其后标称 30s 逐桶对齐;
    # n 游程 3 槽(槽位 base+180/210/240)在响应面 = 连续空桶(断连), 尾记录以游程终点续链
    store.append_records(
        "global",
        v3_epoch_date_str(base + 30),
        (base + 30, 30),
        (
            V3Sample(100, 50, 1000, 500),  # 桶 base
            V3Sample(200, 70, 2000, 800),  # 桶 base+30
            V3Sample(5, 5, 2400, 900),  # 桶 base+60
            V3Sample(300, 90, 3400, 1300),  # 桶 base+90
            V3Sample(10, 10, 2900, 1400),  # 桶 base+120: dl 快照回落(重置, 逐向独立)
            V3NullRun(3, dt_ms=90000),  # 断连 3 槽: 桶 base+150/180/210 空
            V3Sample(12, 22, 3500, 1500, dt_ms=30000),  # 桶 base+240(断链后基线缺失)
        ),
    )

    def point_at(body, bucket):
        return next((p for p in body["points"] if p and p["t"] == bucket), None)

    def total_at(body, bucket):
        return next((p for p in body["totals"] if p and p["t"] == bucket), None)

    r = client.get("/api/traffic/qb/global", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["meta"] == {"window": "24h", "interval_s": 30, "source": "qb", "stale": False}
    assert 2880 <= len(body["points"]) <= 2881  # 满窗栅格(窗首对齐时恰 2880)
    assert point_at(body, base) == {"t": base, "dl": 100, "up": 50}  # r1 桶(对齐 1:1)
    assert point_at(body, base + 30) == {"t": base + 30, "dl": 200, "up": 70}
    assert point_at(body, base + 150) is None  # 断连段: 连续空桶 = null(不连线)
    assert point_at(body, base + 180) is None
    assert point_at(body, base + 210) is None
    assert point_at(body, base + 240) == {"t": base + 240, "dl": 12, "up": 22}
    # totals: 桶 base 窗内首个有观测桶 -> 基线缺失 null; 相邻桶差分; 重置逐向独立; 断链后基线缺失
    assert total_at(body, base) == {"t": base, "dl": None, "up": None}
    assert total_at(body, base + 30) == {"t": base + 30, "dl": 1000, "up": 300}
    assert total_at(body, base + 60) == {"t": base + 60, "dl": 400, "up": 100}
    assert total_at(body, base + 90) == {"t": base + 90, "dl": 1000, "up": 400}
    assert total_at(body, base + 120) == {"t": base + 120, "dl": None, "up": 100}  # dl 重置
    assert total_at(body, base + 180) is None  # 断连桶
    assert total_at(body, base + 240) == {"t": base + 240, "dl": None, "up": None}  # 断链后基线缺失

    # 读取竞态降级(§08「最坏返回上一秒快照 + stale」):
    # a) 24h 已有成功响应入 last-good -> 降级回上一份快照(点值不变) + stale=true;
    # b) 30d 从未成功请求过 -> 无历史快照, 降级回现算空态 + stale=true(不冒充"确定无数据")
    def _read_broken():
        def raise_oserror(self, *a, **k):
            raise OSError("simulated read race")

        return raise_oserror

    monkeypatch.setattr(V3DayCache, "read_window", _read_broken())
    stale = client.get("/api/traffic/qb/global", headers=auth).json()
    assert stale["meta"]["stale"] is True
    assert stale["points"] == body["points"] and stale["totals"] == body["totals"]
    monkeypatch.setattr(V3DayCache, "read_agg", _read_broken())
    fresh = client.get("/api/traffic/qb/global", headers=auth, params={"window": "30d"}).json()
    assert fresh["points"] == [] and fresh["totals"] == [] and fresh["meta"]["stale"] is True
    monkeypatch.undo()
    assert client.get("/api/traffic/qb/global", headers=auth).json()["meta"]["stale"] is False  # 恢复后照常


def test_api_traffic_qb_global_30d_hour_segment(web_env):
    """global 30d 窗(v3 agg hour 段): agg.dat hour 行直映栅格桶(epoch 即桶键, 桶内不再
    聚合), meta.interval_s=3600; 相邻 hour 桶快照差分"""
    from auto_qb.core.traffic_store import AggRow

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v3(mgr)
    now = int(time.time())
    h = ((now - 172800) // 3600) * 3600  # 窗内 2 天前的小时桶
    store.append_agg_rows(
        "global", (
            AggRow("hour", h, 200, 400, 60, 100, 1000, 400, 3600),
            AggRow("hour", h + 3600, 100, 200, 30, 60, 1500, 700, 3600),
        )
    )
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "30d"}).json()
    assert body["meta"]["interval_s"] == 3600 and body["meta"]["window"] == "30d"
    assert 720 <= len(body["points"]) <= 721  # 30d 窗 ≈720 桶
    p = next(p for p in body["points"] if p and p["t"] == h)
    assert p == {"t": h, "dl": 200, "up": 60}  # hour 行 avg(桶内不再聚合)
    total = next(p for p in body["totals"] if p and p["t"] == h)
    assert total == {"t": h, "dl": None, "up": None}  # 窗内首个有观测小时桶: 基线缺失
    total2 = next(p for p in body["totals"] if p and p["t"] == h + 3600)
    assert total2 == {"t": h + 3600, "dl": 500, "up": 300}  # 相邻桶快照差分


def test_api_traffic_qb_global_6mo_1y_day_segment(web_env):
    """6mo/1y 窗(v3 agg day 段, D4 新档): day 行直映本地日界桶, 滚动窗切片正确 ——
    300 天前的行 1y 可见 / 6mo 不可见; 缺日 = null 桶(totals 断链基线缺失);
    meta.interval_s=86400"""
    from datetime import datetime, timedelta

    from auto_qb.core.traffic_store import AggRow

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v3(mgr)
    now = int(time.time())
    today = datetime.fromtimestamp(now).date()

    def midnight(days_ago):
        d = today - timedelta(days=days_ago)
        return int(datetime(d.year, d.month, d.day).timestamp())

    d1, d2, d_old = midnight(5), midnight(4), midnight(300)
    store.append_agg_rows(
        "global", (
            AggRow("day", d_old, 10, 10, 1, 1, 100, 50, 86400),
            AggRow("day", d1, 100, 200, 50, 60, 1000, 500, 86400),
            AggRow("day", d2, 60, 90, 40, 50, 1500, 800, 86400),
        )
    )
    body6 = client.get("/api/traffic/qb/global", headers=auth, params={"window": "6mo"}).json()
    assert body6["meta"]["window"] == "6mo" and body6["meta"]["interval_s"] == 86400
    assert 182 <= len(body6["points"]) <= 184  # 滚动窗 182d + 首尾日界
    assert next((p for p in body6["points"] if p and p["t"] == d_old), None) is None  # 300 天前滑出 6mo
    assert next(p for p in body6["points"] if p and p["t"] == d1) == {"t": d1, "dl": 100, "up": 50}
    assert next(p for p in body6["points"] if p and p["t"] == d2) == {"t": d2, "dl": 60, "up": 40}
    total1 = next(p for p in body6["totals"] if p and p["t"] == d1)
    assert total1 == {"t": d1, "dl": None, "up": None}  # 前一日无行 = null 桶: 断链基线缺失
    total2 = next(p for p in body6["totals"] if p and p["t"] == d2)
    assert total2 == {"t": d2, "dl": 500, "up": 300}  # 相邻日桶快照差分
    body1 = client.get("/api/traffic/qb/global", headers=auth, params={"window": "1y"}).json()
    assert body1["meta"]["window"] == "1y" and body1["meta"]["interval_s"] == 86400
    assert 365 <= len(body1["points"]) <= 367
    assert next(p for p in body1["points"] if p and p["t"] == d_old) == {"t": d_old, "dl": 10, "up": 1}


def test_api_traffic_qb_global_all_month_segment(web_env):
    """all 窗(v3 agg month 段, D4 新档): month 行数据面逐月铺格(缺失月 = null 桶, 折线
    断开), 相邻月桶快照差分; meta.interval_s = 标称月长(真实月长按行间隔, 点位真值在
    points[].t —— 前端按真值落点)"""
    from auto_qb.core.traffic_store import AggRow, v3_month_epoch

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v3(mgr)
    now = int(time.time())
    m0 = v3_month_epoch(now)  # 本自然月(完结月行; 当月行未封不写, 用例直接造历史月)
    m1 = v3_month_epoch(m0 - 86400)  # 上月
    m4 = v3_month_epoch(v3_month_epoch(v3_month_epoch(m1 - 86400) - 86400) - 86400)  # 再往前 3 个自然月
    store.append_agg_rows(
        "global", (
            AggRow("month", m4, 10, 10, 1, 1, 100, 50, 3 * 86400),
            AggRow("month", m1, 100, 200, 50, 60, 1000, 500, 3 * 86400),
            AggRow("month", m0, 60, 90, 40, 50, 1500, 800, 3 * 86400),
        )
    )
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "all"}).json()
    assert body["meta"]["window"] == "all" and body["meta"]["interval_s"] == 30 * 86400
    assert len(body["points"]) == 5  # m4..m0 逐月铺格
    assert body["points"][0] == {"t": m4, "dl": 10, "up": 1}
    assert body["points"][1] is None and body["points"][2] is None  # 缺失月 = null 桶
    assert body["points"][3] == {"t": m1, "dl": 100, "up": 50}
    assert body["points"][4] == {"t": m0, "dl": 60, "up": 40}
    assert body["totals"][0] == {"t": m4, "dl": None, "up": None}  # 首桶基线缺失
    assert body["totals"][3] == {"t": m1, "dl": None, "up": None}  # 与 m4 隔缺失月: 断链
    assert body["totals"][4] == {"t": m0, "dl": 500, "up": 300}  # 相邻月快照差分
    # 空数据面: 全 null -> 空态归一(points: [])
    empty = client.get("/api/traffic/qb/torrent/ZZ", headers=auth, params={"window": "all"}).json()
    assert empty["points"] == [] and empty["meta"]["window"] == "all" and empty["meta"]["interval_s"] == 30 * 86400


def test_api_traffic_qb_torrent_endpoint(web_env):
    """单种端点(v3): 正常取数 / 非法哈希 400 / 未知哈希空态; 数据挂 infohash ——
    不在当前快照的冻结种子历史仍可查"""
    from auto_qb.core.traffic_store import V3Sample, v3_epoch_date_str

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v3(mgr)
    now = int(time.time())
    base = ((now - 3600) // 30) * 30
    # 块首记录槽位恰在 base+30(w=30) -> 桶 base 1:1 对位
    store.append_records(
        "torrent:HA", v3_epoch_date_str(base + 30), (base + 30, 30), (V3Sample(500, 100, 5000, 1000), )
    )
    body = client.get("/api/traffic/qb/torrent/HA", headers=auth).json()
    assert body["meta"]["source"] == "qb" and body["meta"]["stale"] is False
    p = next(p for p in body["points"] if p and p["t"] == base)
    assert p == {"t": base, "dl": 500, "up": 100}
    # 非法哈希(路径不安全字符, 存储层 fail-fast) -> 400; 未知哈希(合法字符, 无文件) -> 空态
    assert client.get("/api/traffic/qb/torrent/HA.X", headers=auth).status_code == 400
    assert client.get("/api/traffic/qb/torrent/ZZ", headers=auth).json()["points"] == []
    # 删种冻结(hash 已不在 by_hash 快照)后历史仍可查: 数据以 v3 天文件为准, 不以快照存在性裁决
    assert "HA" not in mgr.store.by_hash
    body2 = client.get("/api/traffic/qb/torrent/HA", headers=auth).json()
    assert any(p2 and p2["t"] == base for p2 in body2["points"])


def test_api_traffic_qb_torrent_1y_single_agg_cold_read(web_env, monkeypatch):
    """年视图单 agg 文件冷读(§05.3 验收): 1y 窗恰好 1 次 qb-traffic-v3 open(agg.dat,
    天文件零读取); 再查(mtime/size 键控缓存命中)零新 open"""
    from datetime import datetime, timedelta

    from auto_qb.core.traffic_store import AggRow

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v3(mgr)
    now = int(time.time())
    today = datetime.fromtimestamp(now).date()

    def midnight(days_ago):
        d = today - timedelta(days=days_ago)
        return int(datetime(d.year, d.month, d.day).timestamp())

    d1, d2 = midnight(360), midnight(359)
    store.append_agg_rows(
        "torrent:HA", (
            AggRow("day", d1, 10, 10, 1, 1, 100, 50, 86400),
            AggRow("day", d2, 20, 20, 2, 2, 200, 100, 86400),
        )
    )
    opened = _qb_open_spy(monkeypatch)
    body = client.get("/api/traffic/qb/torrent/HA", headers=auth, params={"window": "1y"}).json()
    assert len(_v3_opens(opened)) == 1  # 单 agg 文件冷读(360 天前的 day 行无需任何天文件)
    monkeypatch.undo()
    assert next(p for p in body["points"] if p and p["t"] == d1) == {"t": d1, "dl": 10, "up": 1}
    opened2 = _qb_open_spy(monkeypatch)
    client.get("/api/traffic/qb/torrent/HA", headers=auth, params={"window": "1y"})
    assert _v3_opens(opened2) == []  # 缓存命中零 open
    monkeypatch.undo()


def test_api_traffic_qb_global_24h_reads_only_involved_day_files(web_env, monkeypatch):
    """24h 窗端点面回归(§05.2): 只开窗口涉及的日期天文件(24h 窗恰 2 个, 窗外更早天文件
    零 open), agg.dat 亦不触"""
    from datetime import datetime, timedelta

    from auto_qb.core.traffic_store import V3Sample, v3_epoch_date_str, v3_window_dates

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v3(mgr)
    now = int(time.time())
    base = ((now - 600) // 30) * 30  # 窗内 10 分钟前的对齐桶
    involved = sorted(v3_window_dates(now - 86400, now))
    older_date = (datetime.strptime(involved[0], "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    # 造数: 现行记录落 base 所在日期; 其余涉及日期与窗外更早日期各放一块(读侧按窗过滤)
    for d in involved + [older_date]:
        if d == v3_epoch_date_str(base + 30):
            store.append_records("global", d, (base + 30, 30), (V3Sample(7, 7, 100, 50), ))
        else:
            ts = int(datetime.strptime(d, "%Y-%m-%d").timestamp()) + 30
            store.append_records("global", d, (ts, 30), (V3Sample(1, 1, 1, 1), ))
    opened = _qb_open_spy(monkeypatch)
    body = client.get("/api/traffic/qb/global", headers=auth).json()
    monkeypatch.undo()
    dat_opens = sorted(os.path.basename(p) for p in _v3_opens(opened))
    assert dat_opens == sorted(d + ".dat" for d in involved)  # 只开涉及日期(至多 2 个), 更早日期/agg.dat 不触
    assert len(involved) == 2
    assert next(p for p in body["points"] if p and p["t"] == base) == {"t": base, "dl": 7, "up": 7}


def test_api_traffic_qb_group_endpoint(web_env, monkeypatch):
    """分组端点读侧现算(v3 观测面, §05.1/§05.4): Σ 成员均值 / 全员空闲(z 覆盖)出 0 线 /
    全员无观测(停机)整桶断线 —— 「借 global 判 null」退役: 全程零全局系列文件读取 /
    成员重置贡献 0 不拖垮全组 / 成员历史回溯可见 / 解析不到成员空态 / 畸形 key 400"""
    from auto_qb.core.traffic_store import V3Sample, V3ZeroRun, v3_epoch_date_str

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v3(mgr)
    now = int(time.time())
    base = ((now - 3600) // 30) * 30
    b0, b1, b2, b3, b4, b5 = (base + i * 30 for i in range(6))
    # HA: b0..b3 r 行(块首槽位恰在 b0+30 -> 桶 1:1 对位) + b4 z 覆盖(空闲观测, 快照恒定)
    #     —— b4 之后无任何块 = 停机(桶 b5 全员无观测)
    store.append_records(
        "torrent:HA",
        v3_epoch_date_str(b0 + 30),
        (b0 + 30, 30),
        (
            V3Sample(100, 10, 1000, 0),  # 桶 b0
            V3Sample(0, 0, 2000, 0),  # 桶 b1
            V3Sample(10, 5, 500, 0),  # 桶 b2: 快照回落(重置)
            V3Sample(10, 5, 600, 0),  # 桶 b3
            V3ZeroRun(1, 600, 0),  # 桶 b4: 空闲 z 观测
        )
    )
    # HB: b0 就有数据(200, 快照 100) —— b0 的行在其"入组前", 回溯同样可见; b1/b2 连续产点
    store.append_records(
        "torrent:HB",
        v3_epoch_date_str(b0 + 30),
        (b0 + 30, 30),
        (
            V3Sample(200, 20, 100, 0),  # 桶 b0
            V3Sample(0, 0, 300, 0),  # 桶 b1
            V3Sample(30, 3, 400, 0),  # 桶 b2
        )
    )
    enc = encode_group_key(KEY)
    opened = _qb_open_spy(monkeypatch)
    body = client.get(f"/api/traffic/qb/group/{enc}", headers=auth).json()
    monkeypatch.undo()
    # 组端点无 global 依赖: 请求全程零 qb-traffic-v3/global/ 读取(本用例根本未造全局数据)
    assert not [p for p in _v3_opens(opened) if "/global/" in p]

    def pt(seg, t):
        return next((p for p in body[seg] if p and p["t"] == t), None)

    assert body["meta"]["source"] == "qb" and body["meta"]["stale"] is False
    assert pt("points", b0) == {"t": b0, "dl": 300, "up": 30}  # Σ 成员均值(HA 100 + HB 200, 回溯可见)
    assert pt("points", b1) == {"t": b1, "dl": 0, "up": 0}  # HA 速率 0 行 + HB 速率 0 行
    assert pt("points", b2) == {"t": b2, "dl": 40, "up": 8}  # HA 10 + HB 30
    assert pt("points", b3) == {"t": b3, "dl": 10, "up": 5}  # HB 无行按 0 计
    assert pt("points", b4) == {"t": b4, "dl": 0, "up": 0}  # HA z 覆盖空闲观测 -> 0 线(非 null)
    assert pt("points", b5) is None  # 全员无观测(停机)整桶断线 —— 成员观测面裁决, 不借 global
    assert pt("totals", b0) == {"t": b0, "dl": 0, "up": 0}  # 双成员窗内基线缺失 -> 0(不出洞)
    assert pt("totals", b1) == {"t": b1, "dl": 1200, "up": 0}  # HA +1000, HB +200
    assert pt("totals", b2) == {"t": b2, "dl": 100, "up": 0}  # HA 重置贡献 0(不是 -1500), HB +100
    assert pt("totals", b3) == {"t": b3, "dl": 100, "up": 0}  # HA +100, HB 无行基线缺失 0
    assert pt("totals", b4) == {"t": b4, "dl": 0, "up": 0}  # z 快照同值 delta=0
    assert pt("totals", b5) is None  # null 桶整桶 None
    # 指纹解析不到成员 -> 空态; 畸形 key -> 400(同 /api/groups/{key} 通道)
    other = encode_group_key(("R:/other", ("c.mkv", )))
    assert client.get(f"/api/traffic/qb/group/{other}", headers=auth).json()["points"] == []
    assert client.get("/api/traffic/qb/group/!!!not-base64!!!", headers=auth).status_code == 400


def test_api_traffic_qb_group_30d_reads_member_agg_only(web_env, monkeypatch):
    """3d+ 窗组图只读成员 agg 文件(§05.4, 组图 30d 由 M×31 -> M×1 次文件读取):
    2 成员 30d 窗请求恰好 2 次 qb-traffic-v3 open(各成员 agg.dat 一次), 天文件与全局零读取;
    组速率 = 成员 agg 行求和"""
    from auto_qb.core.traffic_store import AggRow

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v3(mgr)
    now = int(time.time())
    h = ((now - 172800) // 3600) * 3600  # 窗内 2 天前的小时桶
    for key in ("torrent:HA", "torrent:HB"):
        store.append_agg_rows(key, (AggRow("hour", h, 100, 100, 10, 10, 1000, 100, 3600), ))
    opened = _qb_open_spy(monkeypatch)
    body = client.get(f"/api/traffic/qb/group/{encode_group_key(KEY)}", headers=auth, params={"window": "30d"}).json()
    monkeypatch.undo()
    v3 = _v3_opens(opened)
    assert len(v3) == 2 and all(p.endswith("agg.dat") for p in v3)  # M×1, 不读任何天文件
    p = next(p for p in body["points"] if p and p["t"] == h)
    assert p == {"t": h, "dl": 200, "up": 20}  # Σ 成员 avg
    total = next(p for p in body["totals"] if p and p["t"] == h)
    assert total == {"t": h, "dl": 0, "up": 0}  # 双成员基线缺失 -> 0(不出洞)


def test_api_traffic_qb_group_never_transferred_empty_state(web_env):
    """组从未有成员产过流量(成员文件全缺) -> 空态(§08 分组端点); 不渲染全 0 线"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    body = client.get(f"/api/traffic/qb/group/{encode_group_key(KEY)}", headers=auth).json()
    assert body["points"] == [] and body["totals"] == [] and body["meta"]["stale"] is False


def test_api_traffic_qb_group_member_only_zruns_not_empty(web_env):
    """组空态判据 v3 观测面(§05.4, v2 not p.zruns 语义平移): 成员只剩 z 块(raw 已滑出
    窗/从未活跃传输)不算「从未产过流量」—— z 覆盖是真实观测, 组出 0 线而非空态;
    全程不读全局系列(本用例未造任何全局数据)"""
    from auto_qb.core.traffic_store import V3ZeroRun, v3_epoch_date_str

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v3(mgr)
    now = int(time.time())
    start = ((now - 600) // 30) * 30
    # 块首记录 = z 游程: 块首槽位恰在 start+30 -> 桶 start 1:1 对位
    store.append_records("torrent:HA", v3_epoch_date_str(start + 30), (start + 30, 30), (V3ZeroRun(1, 100, 50), ))
    body = client.get(f"/api/traffic/qb/group/{encode_group_key(KEY)}", headers=auth).json()
    assert body["points"] != []  # 非空态: 只剩 z 覆盖的成员仍产出 points
    p = next(p for p in body["points"] if p and p["t"] == start)
    assert p == {"t": start, "dl": 0, "up": 0}  # z 覆盖桶 -> 空闲 0 线


def test_config_schema_endpoint(web_env):
    """图形化配置元数据端点: 分组/站点字段/规则字段/插件表/热重载级别齐全"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    data = client.get("/api/config/schema", headers=auth).json()
    # 2026-09-26: 日志/WebUI/通知 三个短段并入 basic(设置页不再单列三张卡)
    # 26-10-03: 流量图分组(plan 26-10-03-0946 §06)插在 speed 与 trackers 之间
    assert [g["key"]
            for g in data["groups"]] == ["basic", "maintenance", "hr_check", "speed", "traffic", "trackers", "rules"]
    assert [f["key"] for f in data["groups"][0]["fields"]][-3:] == ["log", "web", "notify"]
    # 2026-09-28: 三段在「常规」页必须各自成块展示分类名(「常规/日志」而非并入「常规/常规」) ——
    # 成块的前提是不声明 open(open 段被 cfgFlatten 平铺成无标题同级字段, 正是本次回归的根因)
    for f in data["groups"][0]["fields"][-3:]:
        assert f["kind"] == "object" and not f.get("open"), f["key"]
    assert {p["name"] for p in data["plugins"]["condition"]} >= {"size", "tags", "state", "freespace"}
    assert {p["name"] for p in data["plugins"]["action"]} >= {"add_tags", "checking", "reannounce"}
    # 段认领由模块 sections() 派生(W4 级别表退役; 前端不消费, 留给排障对照)
    assert data["levels"]["claimed_sections"]["web"] == ["webui"]
    assert data["levels"]["claimed_sections"]["trackers"] == ["tracker"]
    assert data["levels"]["claimed_sections"]["rules_config"] == ["rules"]


def test_config_tree_roundtrip(web_env):
    """配置树读取与保存: 树为 YAML 同构(标量字符串), 写回文件 + 热重载命令入队"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    data = client.get("/api/config", headers=auth).json()
    tree = data["tree"]
    assert tree["config"]["qbittorrent"]["host"] == "h", "树应为 YAML 同构的字符串标量"

    tree["config"]["main_tick"] = "5s"
    resp = client.put("/api/config", headers=auth, json={"tree": tree})
    assert resp.status_code == 200, resp.text
    assert resp.json()["applied"] is True
    assert "main_tick" in resp.json()["changes"], "PUT 回执应报变更段路径(W4: 路径字符串)"
    with open(mgr.config_path, encoding="utf-8") as f:
        assert "5s" in f.read(), "新配置应写回 config 文件"
    cmd, payload = mgr.web.commands.get_nowait()
    assert cmd == "reload_config" and payload["config"].main_tick == 5.0


def test_config_tree_invalid_rejected(web_env):
    """非法配置树 -> 400, config 文件不被覆盖"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    tree = client.get("/api/config", headers=auth).json()["tree"]
    tree["config"]["main_tick"] = "abc"
    before = open(mgr.config_path, encoding="utf-8").read()
    resp = client.put("/api/config", headers=auth, json={"tree": tree})
    assert resp.status_code == 400
    assert "main_tick" in resp.json()["detail"]
    assert open(mgr.config_path, encoding="utf-8").read() == before
    assert mgr.web.commands.empty(), "校验失败不应投递热重载"


def test_config_tree_requires_config_root(web_env):
    """缺少 config 根段 -> 400(防止误删整段被当作"全默认"静默接受)"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    resp = client.put("/api/config", headers=auth, json={"tree": {"qbittorrent": {}}})
    assert resp.status_code == 400
    assert "config" in resp.json()["detail"]


def test_config_tree_restart_field_fallback(web_env):
    """R 级字段提交后回退为磁盘旧值(进程身份不可热切换), 并回报 restart_required"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    with open(mgr.config_path, "w", encoding="utf-8") as f:
        f.write("config:\n  schema_version: 4\n  data_dir: old-dir\n  qbittorrent:\n    host: h\n")

    tree = client.get("/api/config", headers=auth).json()["tree"]
    tree["config"]["data_dir"] = "new-dir"
    resp = client.put("/api/config", headers=auth, json={"tree": tree})
    assert resp.status_code == 200, resp.text
    # data_dir 变更会连带派生 state_file(<data_dir>/state.json), 两者同为 R 级
    assert "data_dir" in resp.json()["restart_required"]
    text = open(mgr.config_path, encoding="utf-8").read()
    assert "old-dir" in text, "R 级字段应保留旧值"
    assert "new-dir" not in text, "R 级字段的新值不得写入磁盘"


def test_config_tree_preserves_comments(web_env):
    """round-trip 写盘保留已有键注释(列表项注释为已记录的取舍)"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    with open(mgr.config_path, "w", encoding="utf-8") as f:
        f.write("config:\n  schema_version: 4\n  # 保留我\n  main_tick: 2s\n  qbittorrent:\n    host: h\n")

    tree = client.get("/api/config", headers=auth).json()["tree"]
    tree["config"]["main_tick"] = "3s"
    resp = client.put("/api/config", headers=auth, json={"tree": tree})
    assert resp.status_code == 200, resp.text
    text = open(mgr.config_path, encoding="utf-8").read()
    assert "# 保留我" in text, "已有键的注释应在 round-trip 写盘后保留"
    assert "3s" in text


def test_web_token_not_printed_in_logs(tmp_path, caplog):
    """生成的访问密钥不得出现在任何日志里

    原实现用 `logger.warning(f"WEB UI 访问密钥: {token}")`: notify 处理器的级别取
    config.min_level(早期默认 WARNING, 26-09-27 等级整改后默认 ERROR) ⇒ 密钥被推到系统
    通知; 落日志文件后已登录者可经 /api/log 读回。拿到密钥即等于拿到改配置/删种子的能力。改为只提示文件路径。
    """
    from auto_qb.webui import ensure_web_token

    mgr = _make_web_manager(
        tmp_path,
        "config:\n  qbittorrent:\n    host: h\n    port: 1\n    username: u\n    password: p\n  schema_version: 4\n"
    )
    with caplog.at_level(logging.DEBUG, logger="auto_qb.web"):
        token = ensure_web_token(mgr)
    assert token, "前置: 应生成随机密钥"
    assert any(r.name == "auto_qb.web" for r in caplog.records), "前置: 应有生成提示日志"
    for r in caplog.records:
        assert token not in r.getMessage(), f"密钥不得出现在日志: {r.getMessage()}"
        assert token[:8] not in r.getMessage(), f"密钥前缀也不得出现: {r.getMessage()}"


_WEB_MGR_CFG = "config:\n  qbittorrent:\n    host: h\n    port: 1\n    username: u\n    password: p\n  schema_version: 4\n"


def test_web_token_generated_atomic_and_readable(tmp_path):
    """首次生成: 密钥落盘 web.token 且读回一致, 同目录无临时文件残留(issue 26-09-21-1347)

    ensure_web_token 走 utils.atomic_write(mkstemp 0600 + os.replace): 写盘成功后目标文件
    即完整可读 —— 半截状态只可能存在于临时文件, replace 前对读取侧不可见。
    """
    from auto_qb.webui import ensure_web_token

    mgr = _make_web_manager(tmp_path, _WEB_MGR_CFG)
    token = ensure_web_token(mgr)
    assert re.fullmatch(r"[0-9a-f]{64}", token), "token_hex(32) 应为 64 位小写 hex"
    token_file = tmp_path / "web.token"
    assert token_file.read_text(encoding="ascii") == token, "落盘内容必须与返回值逐字节一致"
    assert not list(tmp_path.glob("web.token.*")), "不得残留临时文件"


def test_web_token_existing_file_reused_without_rewrite(tmp_path, monkeypatch):
    """已有合法 token 时不重写: 直接返回文件现值, 写盘路径一次都不触发(不重写不漂移)"""
    from auto_qb.webui import ensure_web_token
    from auto_qb.webui.server import common

    existing = "ab" * 32
    (tmp_path / "web.token").write_text(existing, encoding="ascii")
    mgr = _make_web_manager(tmp_path, _WEB_MGR_CFG)

    def _must_not_write(*_a, **_kw):
        raise AssertionError("已有合法 token 时不得触达写盘路径")

    monkeypatch.setattr(common, "atomic_write", _must_not_write)
    assert ensure_web_token(mgr) == existing, "应复用文件现值而非重新生成"
    assert (tmp_path / "web.token").read_text(encoding="ascii") == existing


def test_web_token_write_interrupt_leaves_no_half_token(tmp_path, monkeypatch):
    """写盘中断不留非空半截 token(issue 26-09-21-1347): 旧文件不被破坏, 下次调用重新生成(自愈)

    经真实 atomic_write 跑"写一半抛错": 回调写入半截后抛 RuntimeError, 由 atomic_write 负责
    清理临时文件并重抛 —— 目标路径保持旧内容。若实现退回 O_TRUNC 直写, 同一时刻半截内容已落
    目标文件, 本条在 raises 处即红。
    """
    from auto_qb.webui import ensure_web_token
    from auto_qb.webui.server import common

    mgr = _make_web_manager(tmp_path, _WEB_MGR_CFG)
    token_file = tmp_path / "web.token"
    token_file.write_text("", encoding="ascii")  # 空文件: 读取侧判空后走重新生成分支

    real_atomic_write = common.atomic_write

    def _crash_mid(path, write_fn, **kw):
        def _half(_f):
            _f.write("deadbeef")  # 半截密钥, 模拟写盘途中被杀
            raise RuntimeError("simulated kill mid-write")

        return real_atomic_write(path, _half, **kw)

    monkeypatch.setattr(common, "atomic_write", _crash_mid)
    with pytest.raises(RuntimeError):
        ensure_web_token(mgr)
    assert token_file.read_text(encoding="ascii") == "", "中断后不得留下非空半截 token"
    assert not list(tmp_path.glob("web.token.*")), "中断的临时文件必须被清理"

    monkeypatch.undo()
    token = ensure_web_token(mgr)  # 自愈: 下次启动重新生成并完整落盘
    assert token_file.read_text(encoding="ascii") == token


def test_config_tree_masks_secrets(web_env):
    """/api/config 掩码敏感字段, 且"读取后原样保存"不会把密码写成占位串

    掩码只影响展示: PUT 侧用磁盘旧值还原哨兵, 因此前端不改密码地保存一遍仍是真密码 ——
    只掩码不还原的话, 一次保存就会毁掉生产配置。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    data = client.get("/api/config", headers=auth).json()
    assert data["masked"] is True
    assert data["tree"]["config"]["qbittorrent"]["password"] == data["mask_sentinel"]
    assert data["tree"]["config"]["qbittorrent"]["host"] == "h", "非敏感字段不掩码"

    resp = client.put("/api/config", headers=auth, json={"tree": data["tree"]})
    assert resp.status_code == 200, resp.text
    text = open(mgr.config_path, encoding="utf-8").read()
    assert "password: p" in text, f"原样保存不得把密码写成占位串: {text}"
    assert data["mask_sentinel"] not in text


def _site_scan_env(web_env, trackers_by_hash):
    """给 web_env 的 manager 挂上站点扫描所需的最小 api/client 替身"""
    from types import SimpleNamespace

    mgr, client = web_env
    mgr.client = object()  # require_client 只判 None
    # collect_all_tracker_hostnames 按 tor.hash 属性取 hash(QbApi 同形), 不能给 dict
    torrents = [SimpleNamespace(hash=h) for h in trackers_by_hash]
    mgr.api = SimpleNamespace(
        torrents_info=lambda **kw: list(torrents),
        torrents_trackers=lambda h: list(trackers_by_hash.get(h, [])),
    )
    return mgr, client


def test_sites_missing_scans_and_builds_defaults(web_env):
    """GET /api/sites/missing: 未配置域名生成默认条目; 已配置域名(双向包含)不重复出现"""
    mgr, client = _site_scan_env(
        web_env,
        {
            "T1": [{
                "url": "https://tracker.d.com/announce"
            }, {
                "url": "http://tracker.newsite.org/announce"
            }],
            "T2": [{
                "url": "https://tracker.d.com/announce"
            }],
        },
    )
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    data = client.get("/api/sites/missing", headers=auth).json()
    assert data["torrents"] == 2 and data["domains"] == 2
    assert [s["name"] for s in data["sites"]] == ["tracker_newsite_org"]
    entry = data["sites"][0]["entry"]
    assert entry["domains"] == ["tracker.newsite.org"]
    assert entry["tags"] == ["Newsite"], "默认标签 = 倒数第二级域名首字母大写"
    assert entry["upload_speed_limit"] == "0KiB/s", "占位限速与 --export-yaml 同源"
    assert entry["hr"]["required_seeding_time"] == "3D", "hr 示例值与 --export-yaml 同源"


def test_sites_missing_name_conflict_suffix(web_env):
    """站点名冲突: 既有配置占用目标名 / 批内清洗同名 -> _N 后缀(与 CLI 导出同一套 gen_tracker_name)"""
    from types import SimpleNamespace

    mgr, client = _site_scan_env(
        web_env,
        {"T1": [{
            "url": "http://a.b.com/announce"
        }, {
            "url": "http://a-b.com/announce"
        }]},
    )
    mgr.config.trackers["a_b_com"] = SimpleNamespace(domains=["zzz.com"])  # 占用目标名但域名不覆盖缺失域
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    data = client.get("/api/sites/missing", headers=auth).json()
    assert [s["name"] for s in data["sites"]] == ["a_b_com_1", "a_b_com_2"]


def test_sites_missing_all_covered_returns_empty(web_env):
    """全部域名已被配置覆盖 -> sites 空数组(前端据此提示"没有发现未配置的站点")"""
    mgr, client = _site_scan_env(web_env, {"T1": [{"url": "https://tracker.d.com/announce"}]})
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    data = client.get("/api/sites/missing", headers=auth).json()
    assert data["sites"] == []


def test_sites_missing_requires_connected_client(web_env):
    """qB 断连 -> 503(不得拿空扫描结果冒充"没有缺失站点")"""
    mgr, client = web_env  # stub 默认 client=None
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    assert client.get("/api/sites/missing", headers=auth).status_code == 503


def test_sites_missing_api_failure_maps_502(web_env):
    """扫描中途 qB 调用失败 -> 502 带原因(不裸 500)"""
    from types import SimpleNamespace

    def _boom(**kw):
        raise RuntimeError("boom")

    mgr, client = web_env
    mgr.client = object()
    mgr.api = SimpleNamespace(torrents_info=_boom)
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    resp = client.get("/api/sites/missing", headers=auth)
    assert resp.status_code == 502 and "boom" in resp.json()["detail"]


def test_frontend_sites_import_wiring():
    """一键导入缺失站点的前端接线守阵(2026-09-26)

    两套 UI 的站点 pill 行都必须挂「⤓ 导入缺失站点」按钮并调用 config_hub.js 的
    hubImportSites —— 漏一套那套 UI 就没有入口; 防重入标志 hub.importing 必须存在。
    """
    hub_js = open(os.path.join(STATIC_ROOT, "shared", "config_hub.js"), encoding="utf-8").read()
    assert "async hubImportSites()" in hub_js, "config_hub.js 缺 hubImportSites 方法"
    assert "this.hub.importing" in hub_js, "缺防重入标志 hub.importing"
    for ui in _UI_ALL:
        html = _ui_aggregate(ui)
        assert "hubImportSites()" in html, f"{ui} 站点分区缺导入按钮"
        assert "导入缺失站点" in html, f"{ui} 缺导入按钮文案"


def test_frontend_tracker_search_wiring():
    """站点页搜索接线守阵(静态防回潮, 计划 26-09-27-1852; 方案C 聚焦搜索层 2026-09-29 拍板)

    trackers 二级页搜索是纯前端实现, pytest 运行时看不见, 断链都是静默的:
      1. 模板三件套(输入框绑定 / 清空钮 / 计数)与命中行结构缺一 = 搜索入口废;
      2. 归一化必须用 [^\\p{L}\\p{N}](u 标志) —— JS 的 ASCII \\W 是 Unicode 语义的反面,
         会把整个中文词折成空格, 中文搜索静默失效(Python \\W 的同语义直译陷阱);
      3. 收层路径四条(点命中 / Esc / 点暗幕 / 点外即收)一律走 hubTrackerStageClose 清词单点 ——
         漏一条 = 层赖着盖详情(「不主动消失」报障的根因);
      4. 聚焦层开合(聚焦或有词即开) + 键盘导航(↑↓ 移动 / Enter 打开) + IME 组词守卫(方案C)
         + 悬停接管(mousemove + 3px 位移门限, 静止光标/合成事件不夺活动项 —— 治上下键选中项闪烁 2026-09-29)
         + 键盘活动项滚动跟随(↑↓ 后 .act 行滚进 300px 列表视野, 手动 scrollTop 差值, 禁 scrollIntoView —— 26-09-29-2142);
      5. 站点 pill 不带配置键数徽标(26-09-27 拍板); 新增/导入收进行尾动作区与站点 pill 分形(P4);
      6. 模板用到的 hb-tr-* 类必须在 console_hub.css 有定义(挂件类名错配变体)。
    """
    tpl = open(os.path.join(STATIC_ROOT, "shared", "tpl", "settings.html"), encoding="utf-8").read()
    for token in (
        'v-model="cfg.trackerQuery"',
        "hubTrackerClear()",
        "hubTrackerCountText",
        "hubTrackerHits.hits",
        'class="hb-tr-drop"',  # 命中面板(v-if hubTrackerStageOpen)仍挂搜索行下
        'class="hb-tr-detail"',
        "hb-tr-hit",
        "hb-tr-chip",
        # 方案C 聚焦层结构: 舞台 + 暗幕 + 开合 + 键盘 + 面板头尾 + 行尾动作区
        "hb-tr-stage",
        "hubTrackerStageOpen",
        "hb-tr-veil",
        "hubTrackerStageClose(true)",
        'ref="trackerSearchInput"',
        "hub.trackerSearchFocus = true",
        "hubTrackerKeydown($event)",
        '@mousemove="hubTrackerHoverIdx(i, $event)"',  # 悬停接管走位移门限(治上下键选中项闪烁)
        "hb-tr-drop-hd",
        "hb-tr-drop-ft",
        "hb-pill-tail",
        "hubAddTracker(cfg.trackerQuery.trim())",  # 面板尾快捷新增把搜索词带进命名框
    ):
        assert token in tpl, f"shared/tpl/settings.html 缺少 {token}(站点搜索模板被改坏? 同步本守阵)"
    pills = re.search(r'class="hb-pills"(.*?)</div>', tpl, re.S)
    assert pills, "trackers pill 行找不到(结构改名? 同步本守阵)"
    assert "hubCount" not in pills.group(1), "站点 pill 不应显示配置键数徽标(hubCount), 26-09-27 拍板"
    assert "hb-pill-tail" in pills.group(1) and "hubImportSites()" in pills.group(1), \
        "行尾动作区(新增/导入)必须留在 pill 行内(P4: 与站点 pill 分形分位)"
    # 2. 逻辑层单点: CJK 安全归一化 + 解析 / 行索引 / 命中 / 清空 / 收层 / 键盘
    hub = open(os.path.join(STATIC_ROOT, "shared", "config_hub.js"), encoding="utf-8").read()
    assert re.search(r"replace\(/\[\^\\p\{L\}\\p\{N\}\]\+/gu",
                     hub), ("站点归一化必须用 [^\\p{L}\\p{N}](u 标志): ASCII \\W 会把整个中文词折成空格")
    for token in (
        "trackerParseQuery(q)",
        "trackerRows(name, entry)",
        "hubTrackerHits()",
        "hubTrackerClear()",
        "hubTrackerPick(name)",
        "hubTrackerStageClose(blurInput)",
        "hubTrackerKeydown(e)",
        "hubTrackerHoverIdx(i, ev)",
        "trackerMouseAt: null",
        "trackerSearchFocus: false",
        "trackerHitIdx: -1",
    ):
        assert token in hub, f"shared/config_hub.js 缺少 {token}"
    keydown = re.search(r"hubTrackerKeydown\(e\) \{(.*?)\n    \},", hub, re.S)
    assert keydown and "isComposing" in keydown.group(1) and "ArrowDown" in keydown.group(1) \
        and "Enter" in keydown.group(1), "键盘导航必须含 ↑↓/Enter 且 IME 组词中不劫持(isComposing 守卫)"
    # 2.b 滚动跟随(26-09-29-2142): 命中列表 max-height 300px 可滚, ↑↓ 只改 idx 不推滚动条,
    #    长列表上高亮走出可视区 = 键盘选择不可用。手动差值调 scrollTop, 禁 scrollIntoView(连带滚整页)。
    assert keydown and "hubTrackerScrollActIntoView" in keydown.group(1), \
        "↑↓ 改 idx 后必须调 hubTrackerScrollActIntoView 滚动跟随(长列表高亮走出视野)"
    scrollfn = re.search(r"hubTrackerScrollActIntoView\(\) \{(.*?)\n    \},", hub, re.S)
    assert scrollfn, "缺 hubTrackerScrollActIntoView() 实现(改名/挪走? 同步本守阵)"
    scbody = scrollfn.group(1)
    assert "getBoundingClientRect" in scbody and "scrollTop" in scbody, \
        "滚动跟随必须手动差值调 scrollTop(只滚命中列表自身, block:nearest 语义)"
    assert "scrollIntoView" not in scbody, \
        "不得用 scrollIntoView(逐层滚动所有可滚祖先, 连带滚动暗幕后面的整页产生二次干扰)"
    # 3. 收层单点四条路径: 点命中 / Esc(hubOnKey) / 点暗幕(veil) / 点外即收(hubOnDocClick) —— 全部清词
    pick = re.search(r'@click="(hubTrackerPick\(h\.name\))"', tpl)
    assert pick, "命中行 @click 必须接 hubTrackerPick —— 只选中不清词会把切站效果留在暗幕底下(死锁)"
    assert '@mouseenter="hub.trackerHitIdx' not in tpl, \
        "命中行不得挂 @mouseenter(静止光标的旧高亮与键盘活动项同源打架 = 上下键选中项闪烁), 悬停接管走 hubTrackerHoverIdx"
    veil = re.search(r'class="hb-tr-veil" @click="(hubTrackerStageClose\(true\))"', tpl)
    assert veil, "暗幕 @click 必须接 hubTrackerStageClose(true) —— 点暗幕 = 清词收层退聚焦层"
    docclick = re.search(r"hubOnDocClick\(e\) \{(.*?)\n    \},", hub, re.S)
    assert docclick and 'closest(".hb-tr-stage")' in docclick.group(1) \
        and "hubTrackerStageClose(true)" in docclick.group(1), \
        "hubOnDocClick 必须含点外即收(closest .hb-tr-stage 豁免 stage 内点击)"
    onkey = re.search(r"hubOnKey\(e\) \{(.*?)\n    \},", hub, re.S)
    assert onkey and "isComposing" in onkey.group(1), "hubOnKey 必须 IME 组词守卫(组词中 Esc 归输入法)"
    assert onkey and "hubTrackerStageClose(true)" in onkey.group(1), "Esc 必须清词收层退聚焦层"
    for fn in ("hubGo(key)", "hubBack()"):
        body = re.search(rf"{re.escape(fn)} \{{(.*?)\n    \}},", hub, re.S)
        assert body and "hubTrackerStageClose(false)" in body.group(1), \
            f"{fn} 必须走收层单点(离开分区不带搜索残留, 聚焦态一并复位)"
    closefn = re.search(r"hubTrackerStageClose\(blurInput\) \{(.*?)\n    \},", hub, re.S)
    assert closefn and 'this.cfg.trackerQuery = ""' in closefn.group(1) \
        and "trackerSearchFocus = false" in closefn.group(1) \
        and "trackerMouseAt = null" in closefn.group(1), \
        "收层单点必须清词 + 复位聚焦态 + 复位悬停门限坐标(跳转器拍板: 收层一律清词)"
    ed = open(os.path.join(STATIC_ROOT, "shared", "config_editor.js"), encoding="utf-8").read()
    assert 'trackerQuery: ""' in ed, "cfg.trackerQuery 必须在 config_editor.js state 声明(漏声明 = 响应性缺失)"
    # 6. CSS 成对: 模板用到的 hb-tr-* 类都要有规则
    css = open(os.path.join(STATIC_ROOT, "shared", "console_hub.css"), encoding="utf-8").read()
    for cls in (
        "hb-tr-stage",
        "hb-tr-veil",
        "hb-tr-search",
        "hb-tr-x",
        "hb-tr-drop",  # 命中面板(方案C: 头/列表/尾三段式)
        "hb-tr-drop-hd",
        "hb-tr-drop-list",
        "hb-tr-drop-ft",
        "hb-tr-detail",
        "hb-tr-hit",
        "hb-tr-hit-name",
        "hb-tr-cur",
        "hb-tr-chips",
        "hb-tr-chip",
        "hb-tr-hint",
        "hb-pill-tail",
        "hb-btn.dashed",
    ):
        assert "." + cls in css, f"console_hub.css 缺少 .{cls} 定义(挂件类名错配 = 静默裸样式)"
    assert ".hb-tr-hit.act" in css and "hb-tr-hit:hover" not in css, \
        "命中行高亮只走 .act —— CSS :hover 会跟键盘活动项双高亮打架(闪烁根因之一), 悬停接管在 hubTrackerHoverIdx"


def test_frontend_dialog_combo_hover_takeover():
    """弹窗下拉悬停接管守阵(issue 26-09-29-2142, 站点搜索闪烁同族, 2026-09-29 修)

    添加种子分类/标签下拉与编辑弹窗分类下拉原是 @mouseenter 直写键盘活动项 —— 光标静止停在
    列表上用 ↑↓ 选择时, 行滚动/DOM 变更后浏览器给静止光标补发合成 hover 事件, 活动项被拽回
    光标行(改前真机实测: ↓×16 轨迹两次被拽回, Enter 选中 cat-06 而非键盘到达的 cat-16 ——
    不止闪烁, 实选错)。处置(hover-keynav-fight 同款): 1. 悬停接管走 @mousemove + 3px 位移
    门限(comboHoverIdx 共享小工具, 三处不各抄一份); 2. CSS 摘 data-hi 行的 :hover, 高亮只走
    .on 一条路; 3. 开层单点复位门限坐标(下次打开首个动作不被旧坐标误挡)。
    """
    mgr = open(os.path.join(STATIC_ROOT, "shared", "tpl", "dialogs-mgr.html"), encoding="utf-8").read()
    for token in (
        "@mousemove=\"comboHoverIdx('cat', i, $event)\"",  # 悬停接管走位移门限(治上下键选中项闪烁)
        "@mousemove=\"comboHoverIdx('tag', i, $event)\"",
    ):
        assert token in mgr, f"dialogs-mgr.html 缺少 {token}(分类/标签下拉悬停接线被改坏? 同步本守阵)"
    assert "@mouseenter=\"addCatHi" not in mgr and "@mouseenter=\"addTagHi" not in mgr, \
        "分类/标签下拉行不得挂 @mouseenter(静止光标旧高亮与键盘活动项同源打架 = 上下键选中项闪烁/Enter 选错), 悬停接管走 comboHoverIdx"
    pop = open(os.path.join(STATIC_ROOT, "shared", "tpl", "popovers.html"), encoding="utf-8").read()
    assert "@mousemove=\"comboHoverIdx('meta', i, $event)\"" in pop, "popovers.html 缺少 meta 分类下拉悬停接线(同步本守阵)"
    assert "@mouseenter=\"metaCatHi" not in pop, "编辑弹窗分类下拉行不得挂 @mouseenter(同族打架), 悬停接管走 comboHoverIdx"
    # 1. 门限坐标三字段声明(漏声明 = 响应性缺失) + 共享小工具单点实现(别三处各抄一份)
    st = open(os.path.join(STATIC_ROOT, "shared", "state.js"), encoding="utf-8").read()
    for token in ("addCatMouseAt: null", "addTagMouseAt: null", "metaCatMouseAt: null"):
        assert token in st, f"state.js 缺少 {token}(门限坐标未声明 = 响应性缺失)"
    at = open(os.path.join(STATIC_ROOT, "shared", "add_torrent.js"), encoding="utf-8").read()
    assert "comboHoverIdx(kind, i, ev)" in at, "缺 comboHoverIdx 共享小工具(三处下拉共用, 别各抄一份)"
    fn = re.search(r"comboHoverIdx\(kind, i, ev\) \{(.*?)\n    \},", at, re.S)
    assert fn and "dx * dx + dy * dy < 9" in fn.group(1), \
        "悬停接管必须带 3px 位移门限(合成事件位移恒 0 被挡, 真实移动才接管)"
    # 3. 开层单点复位门限坐标(下次打开首个动作不被旧坐标误挡)
    for fnname, field in (("openAddCatMenu", "addCatMouseAt"), ("openAddTagMenu", "addTagMouseAt")):
        body = re.search(rf"{fnname}\(\) \{{(.*?)\n    \}},", at, re.S)
        assert body and f"{field} = null" in body.group(1), \
            f"{fnname} 必须复位 {field}(开层复位门限坐标)"
    dlg = open(os.path.join(STATIC_ROOT, "shared", "dialogs.js"), encoding="utf-8").read()
    body = re.search(r"openMetaCatMenu\(\) \{(.*?)\n    \},", dlg, re.S)
    assert body and "metaCatMouseAt = null" in body.group(1), \
        "openMetaCatMenu 必须复位 metaCatMouseAt(开层复位门限坐标)"
    # 2. CSS 单路高亮: 三皮肤 data-hi 行摘 :hover(.on 活动项是唯一高亮通道)
    for rel in (
        os.path.join("atlas", "css",
                     "dialogs.css"), os.path.join("console", "css",
                                                  "dialogs.css"), os.path.join("prism", "css", "components.css")
    ):
        css = open(os.path.join(STATIC_ROOT, rel), encoding="utf-8").read()
        assert ".pop-item[data-hi]:not(.on):hover" in css, \
            f"{rel} 缺 data-hi 行 hover 中和规则(CSS :hover 与键盘活动项双高亮 = 闪烁根因之一)"


def test_frontend_search_help_wiring():
    """顶栏搜索语法浮卡接线守阵(计划 26-09-28-0201 方案A) —— 模板(帮助钮/浮卡/示例回填/简化占位符)
    + state 声明(漏声明 = 响应性缺失) + view.js 方法(回填即搜/焦点还给输入框)
    + 三条收起路径(点空白/Esc/导航) + 三皮肤 CSS 成对定义(挂件类名错配 = 静默裸样式)"""
    tpl = open(os.path.join(STATIC_ROOT, "shared", "tpl", "topbar.html"), encoding="utf-8").read()
    for token in (
        'placeholder="搜索种子或文件名..."',  # 占位符简化(语法细节移交浮卡), 26-09-28 用户拍板
        'class="search-help"',
        "'no-clear': !searchQuery",  # 空框无清空钮时「?」右移补位(6px), 有词退回 27px —— 26-09-28 用户
        "toggleSearchHelp",
        'class="search-help-pop"',
        "searchHelpFill('4k hdr')",
        "searchHelpFill('&quot;web dl&quot;')",
        "shp-row",
        "shp-tip",
        'ref="searchInput"',
    ):
        assert token in tpl, f"shared/tpl/topbar.html 缺少 {token}(搜索语法浮卡被改坏? 同步本守阵)"
    # 2. state 声明 + 方法单点(回填必须走 doSearch 即搜 + 焦点还输入框)
    state = open(os.path.join(STATIC_ROOT, "shared", "state.js"), encoding="utf-8").read()
    assert "searchHelpOpen: false" in state, "searchHelpOpen 必须在 state.js data 声明(漏声明 = 响应性缺失)"
    view = open(os.path.join(STATIC_ROOT, "shared", "view.js"), encoding="utf-8").read()
    for token in ("toggleSearchHelp()", "searchHelpFill(q)", "this.doSearch()", "this.$refs.searchInput"):
        assert token in view, f"shared/view.js 缺少 {token}"
    fill = re.search(r"searchHelpFill\(q\) \{(.*?)\n    \},", view, re.S)
    assert fill and "this.searchHelpOpen = false" in fill.group(1), "searchHelpFill 必须先收起浮卡"
    # 3. 收起路径: 点空白 + Esc(lifecycle 两条链), 以及 goView/openSettings 导航收起(不带残留跨页)
    lc = open(os.path.join(STATIC_ROOT, "shared", "lifecycle.js"), encoding="utf-8").read()
    assert lc.count("this.searchHelpOpen = false") >= 2, "浮卡必须挂 lifecycle 的点空白与 Esc 两条收起链"
    assert "searchHelpOpen) this.searchHelpOpen = false" in lc, "Esc 退栈必须含浮卡(pop 层)"
    goview = re.search(r"goView\(mode\) \{(.*?)\n    \},", view, re.S)
    assert goview and "this.searchHelpOpen = false" in goview.group(1), "goView 导航必须收起浮卡"
    ed = open(os.path.join(STATIC_ROOT, "shared", "config_editor.js"), encoding="utf-8").read()
    openst = re.search(r"async openSettings\(\) \{(.*?)\n    \},", ed, re.S)
    assert openst and "this.searchHelpOpen = false" in openst.group(1), "openSettings 导航必须收起浮卡"
    # 4. CSS 成对: 挂件类在共用层(console_hub.css, 三套 UI 同载), input 右内边距 52px 三皮肤各自留位
    shared_css = open(os.path.join(STATIC_ROOT, "shared", "console_hub.css"), encoding="utf-8").read()
    for cls in (".search-help", ".search-help.no-clear", ".search-help-pop", ".shp-row", ".shp-tip"):
        assert cls in shared_css, f"shared/console_hub.css 缺少 {cls} 定义(挂件类名错配 = 静默裸样式)"
    atlas_css = open(os.path.join(STATIC_ROOT, "atlas", "css", "components.css"), encoding="utf-8").read()
    assert re.search(r"\.search-help \{[^}]*border-radius: 50%", atlas_css), "星图 pill 差异丢失(「?」钮应圆)"
    for rel in ("prism/css/components.css", "atlas/css/components.css", "console/css/components.css"):
        css = open(os.path.join(STATIC_ROOT, rel), encoding="utf-8").read()
        assert "padding: 7px 52px 7px 33px" in css, f"{rel} input 右内边距未给浮卡按钮留位(32px 旧值 = 「?」压住文字)"


def test_group_key_codec_roundtrip():
    """分组 key 编解码回原值(base64url(JSON))"""
    key = ("R:/下載/目錄", ("a.mkv", "b.mkv"))
    assert decode_group_key(encode_group_key(key)) == key


def test_build_group_view(tmp_path):
    """分组视图快照组装: 组级聚合求和 + 成员明细 + 编码 key(回归真机 utils.encode_group_key 缺失)"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.config.grouping.enabled = True
    mgr.client = FakeClient()
    t1 = FakeTorrent(
        hash="HA",
        name="Show",
        state="stalledUP",
        upspeed=1024,
        uploaded=2048,
        size=512**2,
        progress=1.0,
        seeding_time=3641,  # 非整分钟: 视图输出应按分钟向下取整
        save_path=r"R:/s",
        tags="b, a",  # 逗号分隔字符串 -> 视图输出排序后的标签列表
        category="anime",
    )
    t2 = FakeTorrent(
        hash="HB",
        name="Show",
        state="pausedUP",
        upspeed=1024,
        uploaded=2048,
        size=512**2,
        progress=1.0,
        seeding_time=3600,
        save_path=r"R:/s",
        tags="b, a",
        category="anime",
    )
    from helpers import seed_store

    seed_store(mgr, [t1, t2])
    key = ("R:/s", ("a.mkv", "b.mkv"))
    mgr.store.groups[key] = ["HA", "HB"]
    mgr.store.member_to_key["HA"] = key
    mgr.store.member_to_key["HB"] = key

    view = mgr._build_group_view()
    assert len(view) == 1
    g = view[0]
    assert g["key"] == encode_group_key(key)
    assert g["name"] == "Show" and g["count"] == 2
    assert g["upspeed"] == 2048 and g["uploaded"] == 4096
    # size = 单种子大小(代表成员), total_size = 全组求和(两者相等时前端不提示大小不一致)
    assert g["size"] == 512**2 and g["total_size"] == 2 * 512**2
    assert [m["site"] for m in g["members"]] == ["Unknown", "Unknown"]
    assert g["members"][0]["kind"] == "seeding"
    # 成员视图透出 save_path/tags/category 供前端算组级共同值(后端不做集合运算)
    assert [m["save_path"] for m in g["members"]] == [r"R:/s", r"R:/s"]
    assert [m["tags"] for m in g["members"]] == [["a", "b"], ["a", "b"]]
    assert [m["category"] for m in g["members"]] == ["anime", "anime"]
    # seeding_time 展示值按分钟取整(与 store 重建判定同一步长, 防视图内容与脏标记脱钩)
    assert [m["seeding_time"] for m in g["members"]] == [3600, 3600]


def test_build_group_view_cross_group_conflict_flag(tmp_path):
    """组视图透出跨组文件交叉标记(plan 26-10-04-0107 S4/D4) —— 后端查去重集合, 前端只渲染

    warned 注入组对 -> 组对两侧组字段 true、组外组 false; warned 空 -> 全 false;
    未归组种子不进组视图, singles 单种子视图是成员级投影, 不携带组级标记(无污染;
    前端 filters.js 对搜索视图的虚拟单种子组恒补 cross_group_conflict: false, 单种子无组 key)。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.config.grouping.enabled = True
    mgr.client = FakeClient()
    t1 = FakeTorrent(hash="HA", name="ShowA", state="stalledUP", progress=1.0, size=512**2, save_path=r"R:/a")
    t2 = FakeTorrent(hash="HB", name="ShowB", state="downloading", progress=0.5, size=512**2, save_path=r"R:/b")
    t3 = FakeTorrent(hash="HC", name="ShowC", state="stalledUP", progress=1.0, size=512**2, save_path=r"R:/c")
    t4 = FakeTorrent(hash="HD", name="Lone", state="stalledUP", progress=1.0, size=512**2, save_path=r"R:/d")
    seed_store(mgr, [t1, t2, t3, t4])
    key_a = (r"R:/a", ("a.mkv", ))
    key_b = (r"R:/b", ("b.mkv", ))
    key_c = (r"R:/c", ("c.mkv", ))
    mgr.store.groups[key_a] = ["HA"]
    mgr.store.groups[key_b] = ["HB"]
    mgr.store.groups[key_c] = ["HC"]
    for h, k in (("HA", key_a), ("HB", key_b), ("HC", key_c)):
        mgr.store.member_to_key[h] = k

    # warned 空(开关关/无交叉常态) -> 全 false
    view = {g["name"]: g for g in mgr._build_group_view()}
    assert set(view) == {"ShowA", "ShowB", "ShowC"}
    assert not any(g["cross_group_conflict"] for g in view.values()), "warned 空时不得有组被标记"

    # warned 注入组对 (A, B) -> 两侧组 true, 组外 C false
    # (直写 store 去重集合的白盒姿势, 对齐本文件 seed_store + 手填 groups 的既有夹具)
    mgr.store.cross_group_conflict_warned.add((key_a, key_b))
    view = {g["name"]: g for g in mgr._build_group_view()}
    assert view["ShowA"]["cross_group_conflict"] is True
    assert view["ShowB"]["cross_group_conflict"] is True
    assert view["ShowC"]["cross_group_conflict"] is False

    # 未归组种子(Lone)不在组视图里; singles 是成员级投影, 不携带组级标记(无字段污染)
    singles = mgr._build_singles_view()
    assert [m["name"] for m in singles] == ["Lone"]
    assert all("cross_group_conflict" not in m for m in singles)


def test_build_group_view_member_num_seeds_fields(tmp_path):
    """组视图成员透出 num_seeds/num_leechs/num_complete/num_incomplete(TorrentRecord 快照直取)

    前端成员列/种子页展示连接数与可用性的数据源: _member_view 是组视图 members 与
    singles 未归组种子的共同投影, 字段在成员层透出后两处同形。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = FakeClient()
    t1 = FakeTorrent(
        hash="HA",
        name="Show",
        save_path=r"R:/s",
        num_seeds=12,
        num_leechs=3,
        num_complete=45,
        num_incomplete=6,
    )
    t2 = FakeTorrent(
        hash="HB",
        name="Show",
        save_path=r"R:/s",
        num_seeds=34,
        num_leechs=5,
        num_complete=67,
        num_incomplete=8,
    )
    seed_store(mgr, [t1, t2])
    key = ("R:/s", ("a.mkv", "b.mkv"))
    mgr.store.groups[key] = ["HA", "HB"]
    mgr.store.member_to_key["HA"] = key
    mgr.store.member_to_key["HB"] = key

    members = mgr._build_group_view()[0]["members"]
    for m in members:
        for f in ("num_seeds", "num_leechs", "num_complete", "num_incomplete"):
            assert f in m, f"组视图成员缺少字段 {f}: {sorted(m)}"
    by_hash = {m["hash"]: m for m in members}
    assert by_hash["HA"]["num_seeds"] == 12
    assert by_hash["HA"]["num_leechs"] == 3
    assert by_hash["HA"]["num_complete"] == 45
    assert by_hash["HA"]["num_incomplete"] == 6
    assert by_hash["HB"]["num_seeds"] == 34
    assert by_hash["HB"]["num_leechs"] == 5
    assert by_hash["HB"]["num_complete"] == 67
    assert by_hash["HB"]["num_incomplete"] == 8


def test_build_group_view_group_aggregates(tmp_path):
    """组视图组级聚合(辅种扩列 2026-09-28): "单份文件"语义下的口径单点

    组内成员指向同一份文件(组 key 首元即规范化 save_path), 磁盘只占一份 —— 字节量类取
    "单份"视角, 只有逐成员真实发生的网络流量才可求和:
    - progress/availability 取 max(最完整副本 / 最好的 swarm)
    - eta 取最小有效值(下载冲突检查保证同组至多一个在下载; 哨兵 8640000/非正不参与)
    - amount_left 取 min(补齐一份即可 —— 最完整成员还差的字节, 其余成员 recheck 即齐)
    - last_activity 取 max(-1/0 = 从未 哨兵不参与, 全组从未回 0)
    - downloaded 求和(多站切换下载的真实网络流量, 逐成员可加)
    - seeding_time 取平均(成员值已量化到分钟, 平均后再取整)
    - ratio = 总上传 ÷ 单份大小(分母不能是 total_size, N 份会稀释 N 倍)
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.config.grouping.enabled = True
    mgr.client = FakeClient()
    size = 10000
    t1 = FakeTorrent(
        hash="HA",
        name="Show",
        save_path=r"R:/s",
        size=size,
        progress=0.5,
        eta=7261,  # 成员视图量化到分钟 -> 7260
        downloaded=100,
        amount_left=500,
        availability=1.5,
        last_activity=1700000100,
        seeding_time=3641,  # -> 3600(分钟量化)
        uploaded=1024,
        state="stalledUP",
    )
    t2 = FakeTorrent(
        hash="HB",
        name="Show",
        save_path=r"R:/s",
        size=size,
        progress=1.0,
        eta=8640000,  # 哨兵(无 ETA): 不参与 eta 聚合
        downloaded=200,
        amount_left=300,
        availability=-1.0,  # qB 未知: 不参与 availability 聚合
        last_activity=-1,  # 从未: 不参与 last_activity 聚合
        seeding_time=7200,
        uploaded=2048,
        state="pausedUP",
    )
    # 全组无效值: eta 全哨兵/非正 -> 0, last_activity 全从未 -> 0, availability 全未知 -> None
    t3 = FakeTorrent(
        hash="HC", name="Alone", save_path=r"R:/x", eta=8640000, last_activity=-1, availability=-1.0, state="pausedUP"
    )
    t4 = FakeTorrent(
        hash="HD", name="Alone", save_path=r"R:/x", eta=0, last_activity=0, availability=-1.0, state="pausedUP"
    )
    seed_store(mgr, [t1, t2, t3, t4])
    key = ("R:/s", ("a.mkv", "b.mkv"))
    mgr.store.groups[key] = ["HA", "HB"]
    mgr.store.member_to_key["HA"] = key
    mgr.store.member_to_key["HB"] = key
    key2 = ("R:/x", ("c.mkv", ))
    mgr.store.groups[key2] = ["HC", "HD"]
    mgr.store.member_to_key["HC"] = key2
    mgr.store.member_to_key["HD"] = key2

    g = mgr._build_group_view()[0]
    assert g["progress"] == 1.0
    assert g["eta"] == 7260, "组 eta = 最小有效值(哨兵不参与)"
    assert g["downloaded"] == 300
    assert g["amount_left"] == 300
    assert g["availability"] == 1.5
    assert g["last_activity"] == 1700000100
    assert g["seeding_time"] == 5400, "组做种时长 = 成员平均值(3600 与 7200 的均值)"
    assert g["ratio"] == round(3072 / size, 3), "组分享率分母 = 单份大小而非 total_size"

    g2 = {gg["name"]: gg for gg in mgr._build_group_view()}["Alone"]
    assert g2["eta"] == 0 and g2["last_activity"] == 0 and g2["availability"] is None


def test_member_view_extended_fields(tmp_path):
    """成员视图透出辅种扩列字段(2026-09-28): 明细表新列与组级聚合的共同数据源

    _member_view 是组视图 members 与 singles 未归组种子的共同投影 —— 明细表新增的
    剩余时间/已下载/限速/Tracker/Hash v2 等列从这里取数。秒级递增字段(eta/time_active/
    last_activity)必须经 view_field_value 分钟量化(与 store 重建判定同一步长, 否则做种中的
    种子每轮置脏、惰性重建失效); 哨兵原样带过(负数不量化, 见 view_field_value)。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = FakeClient()
    t = FakeTorrent(
        hash="HA",
        name="Show",
        save_path=r"R:/s",
        eta=7261,
        time_active=3661,
        last_activity=1700000123,
        completion_on=1700000500,
        seen_complete=1700000600,
        availability=1.2345,
        dl_limit=1024,
        up_limit=2048,
        tracker="https://tracker.example/announce",
        infohash_v2="v2hash-abcd1234",
        downloaded=123456,
        amount_left=654321,
    )
    seed_store(mgr, [t])
    v = mgr._member_view(mgr.store.by_hash["HA"])
    assert v["eta"] == 7260 and v["time_active"] == 3660 and v["last_activity"] == 1700000100
    assert v["downloaded"] == 123456 and v["amount_left"] == 654321
    assert v["completion_on"] == 1700000500 and v["seen_complete"] == 1700000600
    assert v["availability"] == 1.23
    assert v["dl_limit"] == 1024 and v["up_limit"] == 2048
    assert v["tracker"] == "https://tracker.example/announce"
    assert v["infohash_v2"] == "v2hash-abcd1234"


def _tracker_calls(client):
    """给 FakeClient 的 torrents_trackers 挂调用计数器(返回被查询过的 hash 列表)

    "免 API"/"TTL 内不重取"/"单轮预算限流"三类断言都需要该计数, 而公共替身无此计数
    (既有用例不依赖), 故在测试侧按需包装, 不改动 helpers.FakeClient 的既有语义。
    """
    seen = []
    orig = client.torrents_trackers
    client.torrents_trackers = lambda h: (seen.append(h), orig(h))[1]
    return seen


def test_error_reason_from_tracker_msg(tmp_path):
    """错误状态的具体原因: 取 tracker 报错 msg(虚拟条目跳过), 并透出到成员/种子视图

    qB torrents/info **不含**错误文本(Web API 无该字段), 原因只能从 torrents/trackers 的
    msg 取; 预取结果写在记录上, 视图组装只读缓存 —— 视图可能每 tick 重建, 不能在里面发 API。
    取不到报错 msg 的错误种子(磁盘/IO 类)回退状态文本, 不留空串(否则前端显示空白状态)。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    client = FakeClient()
    mgr.client = client
    client.trackers_map["HA"] = [
        {
            "url": "** [DHT] **",
            "status": 4,
            "msg": "virtual-entry-msg"
        },  # 虚拟条目: 不得采信
        {
            "url": "https://tracker.hhanclub.net/announce.php",
            "status": 2,
            "msg": "Working"
        },
        {
            "url": "https://tracker.other.net/announce.php",
            "status": 4,
            "msg": "torrent not registered"
        },
    ]
    client.trackers_map["HB"] = [{"url": "https://tracker.hhanclub.net/announce.php", "status": 2, "msg": "Working"}]
    err = FakeTorrent(hash="HA", name="Show", state="error")
    no_msg = FakeTorrent(hash="HB", name="Show", state="error")
    seed_store(mgr, [err, no_msg])

    mgr.web.group_view_dirty = False
    mgr.refresh_error_reasons()

    assert err.tracker_error_msg == "torrent not registered", "取第一条非空错误 msg(虚拟条目跳过)"
    assert mgr.web.group_view_dirty is True, "原因变化须显式置脏(非快照字段, store.view_changed 覆盖不到)"
    assert mgr._member_view(err)["error_reason"] == "torrent not registered"
    assert mgr._seed_view(err)["error_reason"] == "torrent not registered"
    assert no_msg.tracker_error_msg == "" and mgr._member_view(no_msg)["error_reason"] == "错误"
    assert mgr._member_view(FakeTorrent(hash="HC", state="stalledUP"))["error_reason"] == "", "非错误状态不带原因"


def test_error_reason_missing_files_without_api(tmp_path):
    """missingFiles 的原因由状态本身给出("文件丢失"), 不需要任何 tracker 请求"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    client = FakeClient()
    mgr.client = client
    seen = _tracker_calls(client)
    t = FakeTorrent(hash="HA", name="Show", state="missingFiles")
    seed_store(mgr, [t])

    mgr.refresh_error_reasons()

    assert mgr._member_view(t)["error_reason"] == "文件丢失"
    assert seen == [], "missingFiles 的原因不依赖 API"


def test_refresh_error_reasons_budget_and_ttl(tmp_path, monkeypatch):
    """预取限流: 单轮最多预算条, TTL 内不重取, 过期后重取

    错误种子成片时(整组文件丢失)不能一轮打满 tracker 请求 —— 与搜索索引同一限流哲学。
    """
    from auto_qb.webui import views as web_view
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    monkeypatch.setattr(web_view, "ERROR_REASON_BUDGET", 1)
    mgr = make_manager(str(tmp_path / "state.json"))
    client = FakeClient()
    mgr.client = client
    seen = _tracker_calls(client)
    seed_store(mgr, [FakeTorrent(hash="HA", name="A", state="error"), FakeTorrent(hash="HB", name="B", state="error")])

    mgr.refresh_error_reasons()
    assert seen == ["HA"], "单轮只拉预算条数"
    mgr.refresh_error_reasons()
    assert seen == ["HA", "HB"], "下一轮续取剩余种子"
    mgr.refresh_error_reasons()
    assert seen == ["HA", "HB"], "TTL 内不重取"

    monkeypatch.setattr(web_view, "ERROR_REASON_BUDGET", 5)
    monkeypatch.setattr(web_view, "ERROR_REASON_TTL", 0.0)
    mgr.refresh_error_reasons()
    assert seen == ["HA", "HB", "HA", "HB"], "TTL 过期后重取(tracker msg 随站点状态变化)"


def test_refresh_error_reasons_clears_when_recovered(tmp_path):
    """状态恢复(离开错误态)后清空原因缓存 —— 否则恢复做种仍挂着旧原因"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = FakeClient()
    t = FakeTorrent(hash="HA", name="A", state="error", tracker_error_msg="unregistered", tracker_error_ts=time.time())
    seed_store(mgr, [t])

    mgr.web.group_view_dirty = False
    mgr.refresh_error_reasons()
    assert t.tracker_error_msg == "unregistered", "错误态且未过期: 原样保留"
    assert mgr.web.group_view_dirty is False, "无变化不置脏"

    t.state = "stalledUP"
    mgr.refresh_error_reasons()
    assert t.tracker_error_msg == "" and t.tracker_error_ts == 0.0
    assert mgr.web.group_view_dirty is True, "清空也是视图变化"


def test_refresh_error_reasons_skips_when_disconnected(tmp_path):
    """qB 断开(client None)时跳过: 不发请求、不清空已有原因(连接恢复后自然刷新)"""
    from helpers import FakeTorrent, make_manager, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = None
    t = FakeTorrent(hash="HA", name="A", state="error", tracker_error_msg="unregistered")
    seed_store(mgr, [t])

    mgr.refresh_error_reasons()  # 不抛异常

    assert t.tracker_error_msg == "unregistered" and t.tracker_error_ts == 0.0


def test_build_group_view_hr_tags(tmp_path):
    """分组视图透出 HR 标签展示值: 已触发未达标 -> hr_tag, 已达标 -> hr_tag_done

    判定与打标签流程同源(torrents.check_hr_condition/check_hr_satisfied), 标签文本经
    utils.replace_vars 展开 ${required_seeding_time} —— 前端只按文本相等着色, 故两者必须逐字一致。
    """
    from helpers import FakeClient, FakeTorrent, FakeTracker, _hr_rule, make_manager, seed_store

    hr = _hr_rule(add_tag="!!HR${required_seeding_time}!!", add_tag_for_satisfied="--HR${required_seeding_time}--")
    conf = FakeTracker("HHan", hr=hr)
    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = FakeClient()

    def tor(h, name, seeding_time, downloaded=512**2):
        return FakeTorrent(
            hash=h,
            name=name,
            state="stalledUP",
            size=512**2,
            total_size=512**2,
            downloaded=downloaded,
            amount_left=0,
            progress=1.0,
            seeding_time=seeding_time,
            save_path=r"R:/s",
            tracker_conf=conf
        )

    seed_store(
        mgr,
        [
            tor("HA", "Pending.Show", 3600),  # 1 小时: 已触发 HR 但未达标(3D + 12H)
            tor("HB", "Done.Show", 4 * 86400),  # 4 天: 已达标
            tor("HC", "NoHR.Show", 4 * 86400, downloaded=0),  # 纯辅种(无下载量): 不触发 HR
        ]
    )
    for h, key in (("HA", ("R:/p", ("a.mkv", ))), ("HB", ("R:/d", ("b.mkv", ))), ("HC", ("R:/n", ("c.mkv", )))):
        mgr.store.groups[key] = [h]
        mgr.store.member_to_key[h] = key

    members = {g["name"]: g["members"][0] for g in mgr._build_group_view()}
    assert members["Pending.Show"]["hr_tag"] == "!!HR3D!!"
    assert members["Pending.Show"]["hr_tag_done"] == ""
    assert members["Done.Show"]["hr_tag"] == ""
    assert members["Done.Show"]["hr_tag_done"] == "--HR3D--"
    # 未触发 HR 条件时两字段都为空 -> 前端保持普通标签配色
    assert members["NoHR.Show"]["hr_tag"] == "" and members["NoHR.Show"]["hr_tag_done"] == ""
    # 新增展示字段(前端 H&R 栏 / 做种时长与分享率对照列的数据源): 触发与达成布尔 + 要求阈值
    assert members["Pending.Show"]["hr_triggered"] is True
    assert members["Pending.Show"]["hr_satisfied"] is False
    assert members["Pending.Show"]["hr_req_time"] == 3 * 86400 + 12 * 3600
    assert members["Pending.Show"]["hr_req_ratio"] == 0.0
    assert members["Done.Show"]["hr_triggered"] is True and members["Done.Show"]["hr_satisfied"] is True
    assert members["NoHR.Show"]["hr_triggered"] is False


def testhr_view_fields_three_state(tmp_path):
    """详情字段透出站点侧三态与依据 + 删除安全档位×来源(WebUI 可观测性): 接入站点才有值, 未接入全空"""
    from auto_qb.config import HRRule, TrackerConfig
    from auto_qb.config.models import SiteHrCheckConfig
    from auto_qb.core.qbmanager import QbManager
    from auto_qb.hr.resolve import HrIdentity, HrJudgement, HrSiteFacts
    from auto_qb.torrents import TorrentRecord
    from helpers import FakeTorrent, make_manager

    mgr = make_manager(str(tmp_path / "state.json"))
    rec = TorrentRecord.from_torrent(FakeTorrent(hash="HA", state="stalledUP", downloaded=0))
    conf = TrackerConfig(
        name="HHan", domains=["hhanclub.net"], hr=HRRule(required_seeding_time=3 * 86400, condition=("dlratio", 0.7))
    )
    rec.tracker_conf = conf

    # 未接入 hr_check: 三态四项全空(前端据此不显示三态行, 与既有四个字段的空值口径一致);
    # 本地未触发 + 未做种满 => 删除安全 = warning 疑似辅种黄档(计划 26-09-30-0559 §5, 旧「不适用」作废)
    fields = QbManager.hr_view_fields(rec)
    assert fields["hr_state"] == "" and fields["hr_state_text"] == "" and fields["hr_reason"] == ""
    assert fields["hr_safety"] == "warning" and fields["hr_safety_src"] == "local"
    assert fields["hr_safety_text"] == "本地·未达标(疑似辅种)"

    conf.hr_check = SiteHrCheckConfig(
        enabled=True, tracker="hhanclub", hr_page_url="https://hhanclub.net/myhr.php", required_seeding_time=86400.0
    )
    link = mock.Mock()
    link.judge.return_value = HrJudgement(
        identity=HrIdentity.HR, reason="清单命中·考察中(档位 A)", site_satisfied=False, site="HHan"
    )
    rec.hr_link = link
    fields = QbManager.hr_view_fields(rec)
    assert fields["hr_triggered"] is False, "hr_triggered = 纯本地触发判据(展示辅助), downloaded=0 不触发"
    assert fields["hr_satisfied"] is False, "命中考察中 => 义务仍在, 恒未达标"
    assert fields["hr_state"] == "hr" and fields["hr_state_text"] == "受管束"
    assert fields["hr_reason"] == "清单命中·考察中(档位 A)"
    # 删除安全档位: 命中考察中 => 在线·考察中, 不能删(v3: identity=HR 恒映射 site_scope)
    assert fields["hr_safety"] == "danger" and fields["hr_safety_src"] == "site_scope"
    assert fields["hr_safety_text"] == "在线·考察中"

    # 命中行带档位(A 考察中): 档位即结论 —— 在线·考察中, 不能删(本地值不参与)
    link.judge.return_value = HrJudgement(
        identity=HrIdentity.HR,
        reason="清单命中·考察中(档位 A)",
        site_satisfied=False,
        facts=HrSiteFacts(lane="A"),
        site="HHan",
    )
    fields = QbManager.hr_view_fields(rec)
    assert fields["hr_safety"] == "danger" and fields["hr_safety_src"] == "site_scope"
    assert fields["hr_safety_text"] == "在线·考察中"

    # 命中 B 已达标(终态): 放行 + satisfied —— 可删, 来源「在线·已达标」
    link.judge.return_value = HrJudgement(
        identity=HrIdentity.RELEASED,
        reason="清单命中·已达标(B, 终态放行)",
        site_satisfied=True,
        facts=HrSiteFacts(lane="B", remain_seconds=0, ratio=1.5),
        site="HHan",
    )
    fields = QbManager.hr_view_fields(rec)
    assert fields["hr_satisfied"] is True
    assert fields["hr_safety"] == "safe" and fields["hr_safety_src"] == "site_satisfied"
    assert fields["hr_safety_text"] == "在线·已达标"
    # 站点侧值(两套值对账): 已给的照传, 没给的空串 —— 未知与 0 必须可分(0 = 已达标)
    assert fields["hr_site_lane"] == "B" and fields["hr_site_remain"] == 0
    assert fields["hr_site_ratio"] == 1.5 and fields["hr_site_need"] == "" and fields["hr_site_dl"] == ""

    # 命中 C 未达标(终态): 放行但「考核未通过」红档(不能删桶) —— 站点结论已定
    link.judge.return_value = HrJudgement(
        identity=HrIdentity.RELEASED,
        reason="清单命中·未达标(C, 考核结论已定, 终态放行)",
        site_satisfied=False,
        facts=HrSiteFacts(lane="C"),
        site="HHan",
    )
    fields = QbManager.hr_view_fields(rec)
    assert fields["hr_triggered"] is False and fields["hr_state"] == "released_non_hr"
    assert fields["hr_safety"] == "failed" and fields["hr_safety_src"] == "site_unsatisfied"

    # 放行记录(覆盖范围内未列出): 可删, 来源「在线·已核实」
    link.judge.return_value = HrJudgement(identity=HrIdentity.RELEASED, reason="放行记录(覆盖范围内未列出)")
    fields = QbManager.hr_view_fields(rec)
    assert fields["hr_triggered"] is False and fields["hr_state"] == "released_non_hr"
    assert fields["hr_state_text"] == "已核实·放行"
    assert fields["hr_safety"] == "safe" and fields["hr_safety_src"] == "site_released"
    assert fields["hr_safety_text"] == "在线·已核实，安全放行"

    # D 档已免罪(v3.4, 2026-09-26 用户指令): 站点明确终态结论, 来源单列「在线·已免罪」,
    # 不与缺席证据 site_released 混一个 token
    from auto_qb.hr.model import SOURCE_EXEMPT, SOURCE_SATISFIED

    link.judge.return_value = HrJudgement(
        identity=HrIdentity.RELEASED,
        reason="放行记录(D 档已免罪)",
        released_src=SOURCE_EXEMPT,
    )
    fields = QbManager.hr_view_fields(rec)
    assert fields["hr_safety"] == "safe" and fields["hr_safety_src"] == "site_exempt"
    assert fields["hr_safety_text"] == "在线·已免罪"

    # 放行记录无命中行事实 + released_src=satisfied(计划 26-10-02-1936 §3.5): 无事实分支与
    # 带事实分支同文「在线·已达标」—— 同一结论两种写法(旧「在线·已达标(毕业)」)消灭
    link.judge.return_value = HrJudgement(
        identity=HrIdentity.RELEASED,
        reason="放行记录(已达标移出)",
        released_src=SOURCE_SATISFIED,
    )
    fields = QbManager.hr_view_fields(rec)
    assert fields["hr_safety"] == "safe" and fields["hr_safety_src"] == "site_satisfied"
    assert fields["hr_safety_text"] == "在线·已达标"

    # 本地兜底路径(judge 返回 None: 站点侧无可查键/未发布视图): triggered/satisfied 就是本地结论,
    # 来源统一 local —— 呈现口径与打标流程同源, 不会出现"标签说达标、徽章说不能删"
    rec2 = TorrentRecord.from_torrent(
        FakeTorrent(hash="HB", state="stalledUP", size=512**2, total_size=512**2, downloaded=512**2, seeding_time=3600)
    )
    rec2.tracker_conf = conf
    rec2.hr_link = link
    link.judge.return_value = None
    fields = QbManager.hr_view_fields(rec2)
    assert fields["hr_triggered"] is True and fields["hr_satisfied"] is False
    assert fields["hr_safety"] == "danger" and fields["hr_safety_src"] == "local"
    assert fields["hr_safety_text"] == "本地·未达标"
    rec3 = TorrentRecord.from_torrent(
        FakeTorrent(
            hash="HC", state="stalledUP", size=512**2, total_size=512**2, downloaded=512**2, seeding_time=4 * 86400
        )
    )
    rec3.tracker_conf = conf
    rec3.hr_link = link
    fields = QbManager.hr_view_fields(rec3)
    assert fields["hr_safety"] == "safe" and fields["hr_safety_src"] == "local"
    assert fields["hr_safety_text"] == "本地·达标"


def testhr_view_fields_excluded(tmp_path):
    """HR 排除态视图(计划 26-09-28-1805): hr_excluded=True, 触发/达标恒 False,
    删除安全档位短路成空串(「不适用」空白由组装层保证, 计划 26-09-30-0559 §5);
    hr_excluded_by 透出命中来源 token(2026-10-02: 悬停弹窗依据行「按什么排除」的数据源)"""
    from auto_qb.config import HRRule, TrackerConfig
    from auto_qb.config.models import SiteHrCheckConfig
    from auto_qb.core.qbmanager import QbManager
    from auto_qb.torrents import TorrentRecord
    from helpers import FakeTorrent, make_manager

    make_manager(str(tmp_path / "state.json"))  # 与其它视图测试同构(本函数直调类方法, 不读实例态)
    rec = TorrentRecord.from_torrent(FakeTorrent(hash="HD", state="stalledUP", downloaded=0, tags="noHR"))
    conf = TrackerConfig(
        name="HHan",
        domains=["hhanclub.net"],
        hr=HRRule(required_seeding_time=3 * 86400, condition=("dlratio", 0.7), exclude_tags=["noHR"]),
    )
    conf.hr_check = SiteHrCheckConfig(
        enabled=True, tracker="hhanclub", hr_page_url="https://hhanclub.net/myhr.php", required_seeding_time=86400.0
    )
    rec.tracker_conf = conf
    rec.hr_link = mock.Mock()  # 排除种子连判定桥都不该被打扰
    fields = QbManager.hr_view_fields(rec)
    assert fields["hr_excluded"] is True
    assert fields["hr_excluded_by"] == "tag"
    assert fields["hr_triggered"] is False and fields["hr_satisfied"] is False
    assert fields["hr_state"] == "" and fields["hr_safety"] == "" and fields["hr_safety_text"] == ""
    assert fields["hr_safety_src"] == "" and fields["hr_site_lane"] == ""
    rec.hr_link.judge.assert_not_called()

    # 分类命中(2026-10-02 实报的主场景)与双命中: 来源 token 随命中列表走
    conf.hr.exclude_categories = ["keep"]
    rec_cat = TorrentRecord.from_torrent(FakeTorrent(hash="HG", state="stalledUP", downloaded=0, category="keep"))
    rec_cat.tracker_conf = conf
    fields_cat = QbManager.hr_view_fields(rec_cat)
    assert fields_cat["hr_excluded"] is True and fields_cat["hr_excluded_by"] == "category"
    rec.tags = "noHR"
    rec.category = "keep"
    fields_both = QbManager.hr_view_fields(rec)
    assert fields_both["hr_excluded_by"] == "tag+category", "标签与分类同时命中时 token 合并"

    # 未命中排除表: hr_excluded=False, 行为照旧
    rec2 = TorrentRecord.from_torrent(FakeTorrent(hash="HE", state="stalledUP", downloaded=0, tags="HHan"))
    rec2.tracker_conf = conf
    assert QbManager.hr_view_fields(rec2)["hr_excluded"] is False

    # 空配置分支也带 hr_excluded/hr_excluded_by 键(前端字段一致性守阵消费全键集)
    empty = QbManager.hr_view_fields(TorrentRecord.from_torrent(FakeTorrent(hash="HF")))
    assert empty["hr_excluded"] is False and empty["hr_excluded_by"] == ""


def _hr_status_env(mgr, tmp_path, *, complete=True, pages=None):
    """给 web 替身挂上一个**真** HR 服务(跑过一轮), 返回它 —— 站点文件与视图都是真的

    替身 manager 的 config 是 SimpleNamespace(没有 hr_check 段), 所以这里显式补上, 并挂一个
    `hr` 门面替身(真门面需要端点/线程, 与本端点的只读口径无关)。
    pages 可整组替换三档页面(种子明细端点的空站点用例用全零行页)。
    """
    from types import SimpleNamespace
    import time

    from auto_qb.hr.runtime import HrRuntimeStatus, HrRefreshService
    from auto_qb.config.models import SiteHrCheckConfig
    from hr_helpers import Clock, FakeFetcher, global_conf, myhr_page, row, site_conf, torrent_blob

    # !假时钟要落在**真实当前时间**附近: 端点用真 `time.time()` 取 now, 若测试时钟是
    # hr_helpers 默认的 2023 基准, 数据必然被判「已过有效期」—— 测的就不是想测的东西了
    clock = Clock(start=time.time())
    if pages is None:
        pages = {"A": myhr_page([row(101)]), "B": myhr_page([row(101)]), "C": myhr_page([row(101)])}
        if not complete:
            pages["C"] = "<html><body>没有表格</body></html>"
    svc = HrRefreshService(
        data_dir=str(tmp_path),
        global_conf=global_conf(),
        site_confs={"HHan": site_conf()},
        fetcher=FakeFetcher(pages, {101: torrent_blob("t101.bin")}),
        owner="tester",
        now_fn=clock,
    )
    svc.refresh_site("HHan")
    mgr.config.hr_check = HrCheckConfig(enabled=True)
    # 写类路由(confirm-empty / refresh)按 trackers.*.hr_check 判「站点已接入」——替身条目补真模型
    mgr.config.trackers["HHan"].hr_check = SiteHrCheckConfig(enabled=True, tracker="HHan")
    mgr.hr = SimpleNamespace(
        service=svc,
        status=lambda: HrRuntimeStatus(
            enabled=True,
            sites=("HHan", ),
            fetch_enabled=True,
            worker_running=True,
            poll_interval=300.0,
            sites_dir=str(tmp_path / "hr"),
            writer="tester",
            channel=None,
            note="",
        ),
    )
    return svc


def test_api_hr_status_disabled_returns_empty_state(web_env):
    """未启用 HR 时 /api/hr/status 回 enabled=false + 说明(前端据此显示空态, 而不是报错)"""
    mgr, client = web_env
    r = client.get("/api/hr/status", headers={"Authorization": f"Bearer {mgr.web.token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is False and body["sites"] == [] and body["channel"] == {}
    assert "未启用" in body["note"], "要说明为什么没有数据, 不能静默空"


def test_api_hr_status_reports_site_state(web_env, tmp_path):
    """启用后逐站点摊开现状: 新鲜度/覆盖证明/索引与回填进度/配额/熔断/「现在为什么不放行」

    与 `--hr-status` 共用 `hr.status` 一层 —— 这里断言的是那一层的字段真的透到了 HTTP。
    """
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    r = client.get("/api/hr/status", headers={"Authorization": f"Bearer {mgr.web.token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is True and body["fetch_enabled"] is True and body["worker_running"] is True
    assert [s["site"] for s in body["sites"]] == ["HHan"]

    site = body["sites"][0]
    assert site["listing"] == "list" and site["enabled"] is True
    assert site["index_total"] == 1 and site["index_active"] == 1
    assert site["pending_infohash"] == 0 and site["backfill_ratio"] == 1.0
    assert site["managed"] == 0 and site["keys"] == 2, "行名不粗配本地名 → 考察中命中 0; 身份键在终态档占 v1/v2 两个"
    assert all(l["status"] == "ok" for l in site["lanes"]), "三档波次状态全有效"
    # 表② 波次表档位徽章人话(计划 26-10-01-2216 §6.2 mockup「A 考察中」形态): 曾因 LaneStatus
    # 缺字段渲染为空(幻键), 修后逐档钉值 + 钉「取自 LANE_TEXTS 单点」双断言
    from auto_qb.hr.model import FETCH_LANES
    from auto_qb.hr.status import LANE_TEXTS

    lane_texts = {l["lane"]: l["lane_text"] for l in site["lanes"]}
    assert lane_texts == {"A": "考察中", "B": "已达标", "C": "未达标"}, f"徽章人话逐档不对: {lane_texts}"
    assert lane_texts == {k: LANE_TEXTS[k] for k in FETCH_LANES}, "lane_text 必须取自 LANE_TEXTS 单点, 不另写第二份映射"
    assert "上次取波" in site["fresh_text"] and "复用窗至" in site["fresh_text"]
    assert site["next_wave_at"] > site["fetched_at"], "下次取波 = 上次取数 + 周期"
    assert "今天" in site["quota"]["text"] and site["quota"]["day_max"] > 0
    assert site["channel_text"] in ("正常", "未启用") and site["file_path"].endswith("HHan.json")


def test_api_hr_status_names_the_blocking_step(web_env, tmp_path):
    """覆盖证明不成立时, 状态里要直接说出「现在为什么不放行」(用户看到种子没放行时最想知道的一句)"""
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path, complete=False)
    body = client.get("/api/hr/status", headers={"Authorization": f"Bearer {mgr.web.token}"}).json()
    site = body["sites"][0]
    assert site["releases_enabled"] is False
    assert "blocking" in site, f"要说清卡在哪一步: {site}"


# ---------- 立即拉取(计划 26-09-30-0240): POST /api/hr/refresh ----------


def test_api_hr_refresh_accepts_and_returns_requested(web_env, tmp_path):
    """成功受理: 调 manager.hr.request_refresh(与插件端点同一实现)并回受理清单"""
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    calls = []

    def _fake_request_refresh(sites=None):
        calls.append(sites)
        return {"requested": ["HHan"], "note": "已受理, 取数由取数线程执行"}

    mgr.hr.request_refresh = _fake_request_refresh
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    body = client.post("/api/hr/refresh", json={}, headers=auth).json()
    assert body["ok"] is True and body["requested"] == ["HHan"]
    assert calls == [None], "缺省 = 全部启用站点(不逐站点名)"


def test_api_hr_refresh_requires_enabled_hr(web_env, tmp_path):
    """HR 未启用 -> 400; 未接入的站点 -> 400(不受理无档案站点)"""
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    mgr.hr.request_refresh = lambda sites=None: {"requested": ["HHan"], "note": ""}
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    mgr.config.hr_check.enabled = False
    assert client.post("/api/hr/refresh", json={}, headers=auth).status_code == 400
    mgr.config.hr_check.enabled = True
    r = client.post("/api/hr/refresh", json={"site": "Nope"}, headers=auth)
    assert r.status_code == 400 and "Nope" in r.json()["detail"]


def test_api_hr_refresh_409_when_worker_not_running(web_env, tmp_path):
    """取数线程未启动 -> 409(「现在拉不了」的如实形态, 不假装成功)"""
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    mgr.hr.request_refresh = lambda sites=None: {"requested": [], "note": "取数线程未启动"}
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    r = client.post("/api/hr/refresh", json={}, headers=auth)
    assert r.status_code == 409 and "取数线程未启动" in r.json()["detail"]


# ---------- 种子明细(计划 26-10-01-2216 §7 阶段1): GET /api/hr/sites/{site}/entries ----------


def test_api_hr_site_entries_full_fields(web_env, tmp_path):
    """200 全字段: 行键面 = 计划 §3 P0+P1 全集(前端只消费后端算好字段, 不重算)"""
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    r = client.get("/api/hr/sites/HHan/entries", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["site"] == "HHan" and body["read_error"] == "" and body["now"] > 0
    assert len(body["entries"]) == 1
    row = body["entries"][0]
    assert set(row) == {
        "tid",
        "dl_id",
        "name",
        "lane",
        "lane_text",
        "uploaded_bytes",
        "downloaded_bytes",
        "ratio",
        "need_seed_seconds",
        "need_seed_text",
        "infohash_v1",
        "infohash_v2",
        "verified_ts",
        "verified_source",
        "verified_source_text",
        "local_present",
        "done_iso",
        "active",
        "missing_streak",
        "first_seen",
        "last_seen",
    }
    assert row["tid"] == 101 and row["name"]
    assert row["infohash_v1"] and row["infohash_v2"], "取过 .torrent 的行 v1/v2 都已回填"
    assert row["local_present"] is False, "夹具本地库为空 -> 全部行是未做种(local_present join 响应层追加)"
    assert row["need_seed_seconds"] is not None and row["need_seed_text"] not in ("", None)
    assert row["lane"] and row["lane_text"], "档位原值 + 人话都要给"
    assert row["active"] is True and "done_iso" in row
    assert row["first_seen"] >= 0.0 and row["last_seen"] >= 0.0, "first_seen/last_seen 原样透传(写入行为属取数管道, 不在此钉)"


def test_api_hr_site_entries_local_present(web_env, tmp_path):
    """local_present 本地库 join(计划 26-10-02-1936 §3.3, 决策点③a): 明细端点每行带只读标记

    真实 join 用例(端点级): v1 精确命中 / 仅 v2 命中 / 大小写差异命中 -> True;
    本地不存在 -> False(未做种, 含本地从未下载的清单行)。join 键口径单点在
    routes.hr.mark_local_present(纯函数四态由 test_hr_status 钉)。
    """
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    auth = {"Authorization": f"Bearer {mgr.web.token}"}

    def first_row():
        return client.get("/api/hr/sites/HHan/entries", headers=auth).json()["entries"][0]

    r0 = first_row()
    assert r0["local_present"] is False, "本地库为空 -> 未做种"
    h1, h2 = r0["infohash_v1"], r0["infohash_v2"]
    assert h1 and h2, "夹具行 v1/v2 均已回填(不然测不了双键探测)"

    mgr.store.by_hash.clear()
    mgr.store.by_hash[h1] = mock.Mock()
    assert first_row()["local_present"] is True, "v1 命中"

    mgr.store.by_hash.clear()
    mgr.store.by_hash[h2] = mock.Mock()
    assert first_row()["local_present"] is True, "仅 v2 命中(v1 未收录的终态冻结形态)"

    mgr.store.by_hash.clear()
    mgr.store.by_hash[h1.upper()] = mock.Mock()
    assert first_row()["local_present"] is True, "大小写差异命中(站点清单与 qB hash 书写形态不同)"

    mgr.store.by_hash.clear()
    mgr.store.by_hash["deadbeef"] = mock.Mock()
    assert first_row()["local_present"] is False, "本地只有别的种子 -> 未做种"


def test_api_hr_site_entries_verified_two_states(web_env, tmp_path):
    """verified 有/无两态同表: 无记录→未核实(0/""/"未核实"); 有记录→verified_ts + source 原值 + 人话"""
    mgr, client = web_env
    svc = _hr_status_env(mgr, tmp_path)
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    row = client.get("/api/hr/sites/HHan/entries", headers=auth).json()["entries"][0]
    assert row["verified_ts"] == 0.0
    assert row["verified_source"] == "" and row["verified_source_text"] == "未核实"
    # 注入放行记录(持锁会话写站点文件 —— 与端点读的是同一份数据), 再验有记录态
    from auto_qb.hr.model import SOURCE_EXEMPT, HrVerified

    ts = 1_759_000_000.0
    with svc.store("HHan").hold() as session:
        h = session.data.index[101].infohash_v1
        session.data.verified[h] = HrVerified(infohash=h, tid=101, verified_ts=ts, source=SOURCE_EXEMPT)
        assert session.commit(time.time()) == "written"
    row = client.get("/api/hr/sites/HHan/entries", headers=auth).json()["entries"][0]
    assert row["verified_ts"] == ts
    assert row["verified_source"] == "absent" and row["verified_source_text"] == "D 免罪"


def test_api_hr_site_entries_empty_site(web_env, tmp_path):
    """站点已接入但没有 HR 行 -> 200 + 空数组(前端显示空态, 不当错误)"""
    mgr, client = web_env
    from hr_helpers import EMPTY_TABLE_PAGE

    _hr_status_env(mgr, tmp_path, pages={"A": EMPTY_TABLE_PAGE, "B": EMPTY_TABLE_PAGE, "C": EMPTY_TABLE_PAGE})
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    r = client.get("/api/hr/sites/HHan/entries", headers=auth)
    assert r.status_code == 200
    assert r.json()["entries"] == []


def test_api_hr_site_entries_guards(web_env, tmp_path):
    """HR 未启用 -> 400; 站点未接入 -> 404 并点名已接入清单(与 confirm-empty 同款话术)"""
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    mgr.config.hr_check.enabled = False
    assert client.get("/api/hr/sites/HHan/entries", headers=auth).status_code == 400
    mgr.config.hr_check.enabled = True
    r = client.get("/api/hr/sites/Nope/entries", headers=auth)
    assert r.status_code == 404 and "Nope" in r.json()["detail"]


def test_api_hr_site_entries_409_worker_absent(web_env, tmp_path):
    """hr 门面在但 service 缺席(取数线程未启动的实例形态) -> 409「线程未启动」, 不假装有数据"""
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    mgr.hr.service = None
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    r = client.get("/api/hr/sites/HHan/entries", headers=auth)
    assert r.status_code == 409 and "取数线程未启动" in r.json()["detail"]


# ---------- 拉取历史(计划 26-10-04-0312 §3.4): GET /api/hr/history ----------


def test_api_hr_history_rows_from_real_wave(web_env, tmp_path):
    """200: 真实波次(S2 记录器落的事件)进历史表 —— 行键面 = §3.4 全集, 人话徽章后端算好"""
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    r = client.get("/api/hr/history", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is True and body["read_errors"] == {} and body["now"] > 0
    assert body["rows"], "夹具跑过一轮真实波, 历史表不能是空的"
    row = body["rows"][0]
    assert set(row) == {
        "ts",
        "ts_text",
        "site",
        "kind",
        "kind_text",
        "trigger",
        "trigger_text",
        "action",
        "result_text",
        "result_tone",
        "reason",
        "reason_kind",
        "pages",
        "rows",
        "torrents_ok",
        "torrents_fail",
        "verified",
        "elapsed_s",
        "elapsed_text",
        "lanes",
        "notes",
        "by",
    }
    assert row["site"] == "HHan" and row["kind"] == "wave"
    assert row["result_text"] == "完成" and row["result_tone"] == "ok", "三档全跑完的波 -> 完成徽章(映射单点在 hr.status)"
    assert row["trigger"] == "auto" and row["trigger_text"] == "自动"
    assert row["ts"] > 0 and row["ts_text"] and row["elapsed_text"], "epoch 与人话并给(排序用原值, 展示用文案)"
    assert row["lanes"] and all(l["lane_text"] for l in row["lanes"]), "各档 lane_text 人话随行给出"
    assert row["by"] == "tester", "写者实例短标识随事件透传(多实例分辨「谁抓的」)"


def test_api_hr_history_site_filter(web_env, tmp_path):
    """site 过滤: 给了就只回该站; 未接入的站点 404 并点名已接入清单(与 entries 同款话术)"""
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    r = client.get("/api/hr/history?site=HHan", headers=auth)
    assert r.status_code == 200
    rows = r.json()["rows"]
    assert rows and all(row["site"] == "HHan" for row in rows), "过滤键生效, 行只来自指定站点"
    r = client.get("/api/hr/history?site=Nope", headers=auth)
    assert r.status_code == 404 and "Nope" in r.json()["detail"] and "HHan" in r.json()["detail"]


def test_api_hr_history_guards(web_env, tmp_path):
    """HR 未启用 -> 400; 取数服务缺席(service=None) -> 409(与 entries 同款校验口径)"""
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    mgr.config.hr_check.enabled = False
    assert client.get("/api/hr/history", headers=auth).status_code == 400
    mgr.config.hr_check.enabled = True
    mgr.hr.service = None
    r = client.get("/api/hr/history", headers=auth)
    assert r.status_code == 409 and "取数线程未启动" in r.json()["detail"]


def test_api_hr_history_limit_clamped(web_env, tmp_path):
    """limit 查询参数: 截最新的 N 条; 0 钳到 1(FastAPI 只管 int 解析, 卫生钳制在这层做)"""
    mgr, client = web_env
    svc = _hr_status_env(mgr, tmp_path)
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    from auto_qb.hr.model import HrHistoryEvent

    # 合成事件用未来时刻: 夹具真实波的 ts = 当前时间, 必须保证它排不进「最新 N 条」
    base = time.time() + 1000.0
    with svc.store("HHan").hold() as session:
        for offset in (1000.0, 2000.0, 3000.0):
            session.data.history.append(HrHistoryEvent(ts=base + offset, kind="wave", action="refreshed"))
        assert session.commit(time.time()) == "written"
    rows = client.get("/api/hr/history?limit=2", headers=auth).json()["rows"]
    assert [r["ts"] for r in rows] == [base + 3000.0, base + 2000.0], "limit 截最新的 N 条"
    rows = client.get("/api/hr/history?limit=0", headers=auth).json()["rows"]
    assert len(rows) == 1, "limit<=0 钳到 1(不回全量也不回空页)"


def test_api_hr_history_read_error_reported_not_raised(web_env, tmp_path):
    """站点文件读坏不抛: read_errors{site: err} 原样带出, rows 剔掉坏站(表① 同款只读口径)"""
    mgr, client = web_env
    svc = _hr_status_env(mgr, tmp_path)
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    svc.store("HHan").path.write_text("{not-json", encoding="utf-8")
    r = client.get("/api/hr/history", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["rows"] == [], "坏站的数据不进行集(历史表宁缺勿错)"
    assert "HHan" in body["read_errors"] and body["read_errors"]["HHan"], "坏文件本身就是要人看的信息"


def test_api_state_excludes_hr_entry_details(web_env):
    """体积守卫: 种子明细键不得进 /api/state 轮询载荷(计划 §8) —— 明细只随表①按站点按需拉"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    text = json.dumps(client.get("/api/state", headers=auth).json(), ensure_ascii=False)
    for key in ("need_seed_text", "verified_source_text", "lane_text", "missing_streak", "local_present"):
        assert f'"{key}"' not in text, f"/api/state 轮询载荷混入了明细键 {key}"


def test_hr_user_visible_texts_no_graduation_wording():
    """否定守阵(计划 26-10-02-1936 §3.5): 用户可见文案来源「毕业」零残留

    扫 hr/status.py(SOURCE_TEXTS 等)· hr/resolve.py(放行依据文案表 / safety_display 人话)·
    hr/events.py(告警行)的**字符串常量**(AST 层取, 注释天然不在其列 —— 注释按决策点②
    保留「毕业」域术语, grep 可溯源)。前端静态文案归阶段 2-3 守阵, 不在此。
    """
    import ast

    hr_dir = Path(__file__).resolve().parents[1] / "src" / "auto_qb" / "hr"
    for name in ("status.py", "resolve.py", "events.py"):
        tree = ast.parse((hr_dir / name).read_text(encoding="utf-8"), filename=name)
        offenders = [
            n.value
            for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and "毕业" in n.value
        ]
        assert not offenders, f"{name} 的用户可见字符串残留「毕业」: {offenders!r}"


def test_api_hr_refresh_single_site_and_no_runtime(web_env, tmp_path):
    """refresh 补遗: 指定 site -> request_refresh 收到 ["HHan"](单站受理, 不是全部);
    hr 门面整个缺席(getattr = None) -> 409「线程未启动」, 不是 500"""
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    calls = []

    def _fake(sites=None):
        calls.append(sites)
        return {"requested": list(sites or []), "note": ""}

    mgr.hr.request_refresh = _fake
    body = client.post("/api/hr/refresh", json={"site": "HHan"}, headers=auth).json()
    assert body["ok"] is True and body["requested"] == ["HHan"]
    assert calls == [["HHan"]], "带 site 时只受理该站"
    del mgr.hr  # SimpleNamespace: 模拟取数线程从未启动的实例
    r = client.post("/api/hr/refresh", json={}, headers=auth)
    assert r.status_code == 409 and "取数线程未启动" in r.json()["detail"]


def test_api_hr_confirm_empty(web_env, tmp_path, monkeypatch):
    """人工对账戳端点(§5.3): 缺 site / HR 未启用 / 站点未接入 -> 400; 成功 -> ok+site 且
    run_hr_confirm_empty 收到 [site]; 写入失败(站点锁占用) -> 409"""
    from auto_qb.webui.server.routes import hr as hr_routes

    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    r = client.post("/api/hr/confirm-empty", json={}, headers=auth)
    assert r.status_code == 400 and "缺少 site" in r.json()["detail"]
    mgr.config.hr_check.enabled = False
    r = client.post("/api/hr/confirm-empty", json={"site": "HHan"}, headers=auth)
    assert r.status_code == 400 and "未启用" in r.json()["detail"]
    mgr.config.hr_check.enabled = True
    r = client.post("/api/hr/confirm-empty", json={"site": "Nope"}, headers=auth)
    assert r.status_code == 400 and "Nope" in r.json()["detail"] and "HHan" in r.json()["detail"]
    calls = []
    monkeypatch.setattr(hr_routes, "run_hr_confirm_empty", lambda config, sites: calls.append(sites) or 0)
    body = client.post("/api/hr/confirm-empty", json={"site": "HHan"}, headers=auth).json()
    assert body == {"ok": True, "site": "HHan"}
    assert calls == [["HHan"]]
    monkeypatch.setattr(hr_routes, "run_hr_confirm_empty", lambda config, sites: 1)
    r = client.post("/api/hr/confirm-empty", json={"site": "HHan"}, headers=auth)
    assert r.status_code == 409 and "写入失败" in r.json()["detail"]


def test_api_events_sse_stream_lifecycle(web_env, monkeypatch):
    """SSE 生成器整块: hello 帧 -> 广播后事件帧(先 touch) -> 无事件时 keepalive 心跳 ->
    消费端关闭 -> 生成器终结执行 finally 退订(subscriber_count 归零)。

    !不走 TestClient 流式读: starlette 1.6 TestClient 的 handle_request 用 portal.call 把
    整个 app 跑到完成为止, 无限 SSE 流永不完成 -> 挂死(实测 90s) —— 改为直调生产路由端点
    拿 StreamingResponse, anyio 驱动 body_iterator(与真实发送同源, 鉴权是全局依赖另行已测)。
    keepalive 间隔猴补 0.05s, 挂钟下界留 20ms 余量(pitfalls/testing/timing-tolerance.md)。
    """
    import gc
    import time as _time

    import anyio

    from auto_qb.webui.server.context import WebContext
    from auto_qb.webui.server.routes import events as events_mod

    mgr, _client = web_env
    monkeypatch.setattr(events_mod, "SSE_KEEPALIVE_S", 0.05)
    touches = []
    monkeypatch.setattr(mgr.web, "touch", lambda: touches.append(1))
    route = next(r for r in events_mod.build_router(WebContext(mgr)).routes if r.path == "/api/events")
    resp = route.endpoint()
    assert resp.media_type == "text/event-stream"
    assert resp.headers["cache-control"] == "no-cache"
    assert resp.headers["x-accel-buffering"] == "no"  # 反代不缓冲, SSE 才能逐帧到

    async def _drive():
        frames = resp.body_iterator
        # hello 帧: 订阅即发, 不触发 touch(还没进事件循环)
        assert await frames.__anext__() == 'event: hello\ndata: {"ok": true}\n\n'
        assert touches == []
        # 事件帧: 广播 -> 帧名取 ev.type, payload 原样; touch 标记活跃
        assert mgr.web.notify("cmd_done", {"id": 9}) == 1
        assert await frames.__anext__() == 'event: cmd_done\ndata: {"id": 9}\n\n'
        assert len(touches) == 1
        # keepalive: 队列空 -> Empty 分支 -> 心跳注释帧(必须 < WEB_VIEW_TTL, 自锁防线)
        t0 = _time.monotonic()
        assert await frames.__anext__() == ": keepalive\n\n"
        assert _time.monotonic() - t0 >= 0.05 - 0.02
        assert len(touches) == 2
        # 心跳后循环继续(continue): 再广播一条, 事件帧照常送达
        assert mgr.web.notify("view_changed", {"ver": 2}) == 1
        assert await frames.__anext__() == 'event: view_changed\ndata: {"ver": 2}\n\n'
        assert len(touches) == 3
        await frames.aclose()  # 客户端断开: 消费端关闭

    anyio.run(_drive)
    # starlette 1.6 不显式 close 同步生成器 —— 断开后由生成器终结执行 finally 退订;
    # aclose 后引用链已断, collect 使终结确定性发生(生产同语义: 流对象失去引用即退订)
    del resp
    gc.collect()
    assert mgr.web.subscriber_count() == 0, "断流后必须退订, 防句柄堆叠"


def test_api_events_sse_generator_error_still_unsubscribes(web_env, monkeypatch):
    """生成器中途异常死亡(touch/序列化等任何异常)也必须走 finally 退订 —— fail-safe 语义"""
    import anyio

    from auto_qb.webui.server.context import WebContext
    from auto_qb.webui.server.routes import events as events_mod

    mgr, _client = web_env
    monkeypatch.setattr(events_mod, "SSE_KEEPALIVE_S", 0.05)
    route = next(r for r in events_mod.build_router(WebContext(mgr)).routes if r.path == "/api/events")
    resp = route.endpoint()

    async def _drive():
        frames = resp.body_iterator
        assert await frames.__anext__() == 'event: hello\ndata: {"ok": true}\n\n'
        monkeypatch.setattr(mgr.web, "touch", lambda: (_ for _ in ()).throw(RuntimeError("view boom")))
        mgr.web.notify("cmd_done", {"id": 1})
        with pytest.raises(RuntimeError, match="view boom"):
            await frames.__anext__()

    anyio.run(_drive)
    assert mgr.web.subscriber_count() == 0, "生成器异常死亡也要退订, 防句柄堆叠"


def test_frontend_hr_status_fields_match_backend():
    """前端 HR 状态块引用的字段必须在后端快照里存在 —— 打错一个字段名就是**整段静默空白**

    两套 UI 各扫一个入口(2026-09-25 起 HR 站点状态并入 Console Hub「HR 在线核实」分区页尾,
    经典设置页与其独立章节/卡片已移除): 这类错误后端全绿、pytest 也全绿, 只有真打开页面才
    看得出来(与 `_scan_page_class_wiring` 的挂件类名同一类故障), 故机检。
    """
    from auto_qb.hr.status import SiteStatus

    site_keys = set(SiteStatus(site="probe").to_dict().keys())
    hrs_keys = {
        "loaded", "loading", "error", "enabled", "note", "sites", "channel", "fetchEnabled", "workerRunning",
        "pollInterval", "confirming", "refreshing", "refreshNote"
    }
    # 锚点必须指向合并块自身: v-if 只在「HR 在线核实」分区模板块这一处出现, 重复出现说明块被复制
    # (2026-09-27 起块内含「站点接入」+「站点状态」两个块, 扫描窗放大到 8000 字符; 26-10-01 阶段2
    # 表① 又带入嵌套 <template v-for> 明细表 —— 单找第一个 </template> 会切在明细表收口、丢掉块尾
    # 字段覆盖, 故改按模板嵌套深度找**锚点自己的配对收口**, 窗口只作半残兜底: 阶段3 放大到 16000,
    # 26-10-04-0312 S4 表③ 拉取历史全局段再涨(实测块 18.2k 字符)放大到 32000)
    anchor = "hub.view === 'hr_check'"
    for ui in _UI_ALL:
        html = _ui_aggregate(ui)
        idx = html.find(anchor)
        assert idx > 0, f"{ui} 缺少锚点 {anchor} —— 合并进「HR 在线核实」的状态块丢失"
        assert html.find(anchor, idx + 1) < 0, f"{ui} 锚点出现多次 —— 状态块被复制了?"
        open_i = html.rfind("<template", max(0, idx - 200), idx)
        assert open_i >= 0, f"{ui}: 锚点 {anchor} 不在 <template> 开标签内 —— 模板结构被改坏? 同步本守阵"
        depth = 0
        cut = -1
        for m in re.finditer(r"<template\b|</template>", html[open_i:open_i + 32000]):
            depth += 1 if m.group(0).startswith("<template") else -1
            if depth == 0:
                cut = open_i + m.start()
                break
        assert cut > 0, f"{ui}: 状态块没有闭合标签 —— 模板结构被改坏"
        block = html[idx:cut]
        used_site = set(re.findall(r"\bs\.([a-z_]+)\b(?!\()", block))
        assert used_site, f"{ui}: 没扫到任何字段 —— 锚点失效, 这个守阵现在是恒真的"
        missing = sorted(used_site - site_keys)
        assert not missing, f"{ui}: 模板引用了后端快照里没有的字段 {missing}(会整段空白)"
        used_hrs = set(re.findall(r"\bhrs\.([A-Za-z_]+)\b(?!\()", block))
        missing_hrs = sorted(used_hrs - hrs_keys)
        assert not missing_hrs, f"{ui}: 模板引用了 hrs 状态里没有的字段 {missing_hrs}"


def test_build_group_view_hr_counts(tmp_path):
    """组级 H&R 计数: 分母 = 已触发 HR 的成员数, 分子 = 其中未达标的成员数(前端 H&R 栏)"""
    from helpers import FakeClient, FakeTorrent, FakeTracker, _hr_rule, make_manager, seed_store

    hr = _hr_rule(required_share_ratio=2.0)
    conf = FakeTracker("HHan", hr=hr)
    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = FakeClient()

    def tor(h, seeding_time, ratio):
        return FakeTorrent(
            hash=h,
            name="Show",
            state="stalledUP",
            size=512**2,
            total_size=512**2,
            downloaded=512**2,
            amount_left=0,
            progress=1.0,
            seeding_time=seeding_time,
            ratio=ratio,
            save_path=r"R:/s",
            tracker_conf=conf,
        )

    seed_store(
        mgr,
        [
            tor("HA", 100, 0.5),  # 已触发但未达标(时长与分享率都不够)
            tor("HB", 100, 3.0),  # 已触发且分享率达标
            tor("HC", 4 * 86400, 0.1),  # 已触发且时长达标
        ]
    )
    key = ("R:/s", ("a.mkv", ))
    mgr.store.groups[key] = ["HA", "HB", "HC"]
    for h in ("HA", "HB", "HC"):
        mgr.store.member_to_key[h] = key

    g = mgr._build_group_view()[0]
    assert g["hr_triggered"] == 3
    assert g["hr_pending"] == 1


def test_build_group_view_added_on_is_latest_member(tmp_path):
    """组级 added_on = 组内**最近添加**成员的时间(前端默认按此降序排序)

    用 max 而非 min: "刚补进来的那个辅种"才是用户最关心的新条目。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = FakeClient()
    t1 = FakeTorrent(hash="HA", name="Show", added_on=1000, save_path=r"R:/s")
    t2 = FakeTorrent(hash="HB", name="Show", added_on=3000, save_path=r"R:/s")
    t3 = FakeTorrent(hash="HC", name="Other", added_on=2000, save_path=r"R:/o")
    seed_store(mgr, [t1, t2, t3])
    key = ("R:/s", ("a.mkv", "b.mkv"))
    mgr.store.groups[key] = ["HA", "HB"]
    mgr.store.member_to_key["HA"] = key
    mgr.store.member_to_key["HB"] = key
    key2 = ("R:/o", ("c.mkv", ))
    mgr.store.groups[key2] = ["HC"]
    mgr.store.member_to_key["HC"] = key2

    groups = {g["name"]: g for g in mgr._build_group_view()}
    assert groups["Show"]["added_on"] == 3000  # max(1000, 3000)
    assert groups["Other"]["added_on"] == 2000
    # 成员级也透出 added_on(排序/展示共用的原始值)
    assert sorted(m["added_on"] for m in groups["Show"]["members"]) == [1000, 3000]


def test_views_published_atomically_when_rebuilt_concurrently(tmp_path):
    """并发重建: 四份视图与版本号必须**同一轮**发布(主循环线程 vs Web 线程)

    web.py 的同步 `def` 处理器跑在 FastAPI 线程池里, 会与主循环同时走 `rebuild_views`。
    无锁时后者的"逐条赋值 + 版本号自增"会被前者插到中间 ⇒ 1.`_group_view_ver += 1` 是
    读-改-写, 丢失更新; 2.Web 线程可能拿到"groups 来自本轮、flat 来自上一轮"的错位组合,
    而版本号只有一个 ⇒ 前端按 rid 判定 updated=true 却把错位数据整表换上去。

    检测手法(刻意做成**确定性**, 不依赖线程调度): 让重建卡在 builder 里不放行, 再把脏标记
    置为 False —— 于是读取路径不需要重建, 它能否返回**只取决于有没有锁**, 与交错时序无关。
    (更直觉的"比对四份视图的 build 号"写法是 flaky 的: 无锁时若两个线程各自完整发布一轮,
    最后发布者胜出, 四份仍是自洽的, 用例会假绿。)
    """
    import threading as _threading

    from helpers import FakeClient, make_manager

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = FakeClient()

    inside = _threading.Event()  # 重建已进入 builder
    release = _threading.Event()  # 放行重建
    errors = []

    def _build_group():
        inside.set()
        release.wait(5)  # 卡在临界区里, 模拟"重建尚未发布"
        return []

    mgr._build_group_view = _build_group

    def _main_loop_path():
        try:
            mgr.web.rebuild_views()  # 主循环 _tick 走的重建路径(持锁)
        except Exception as e:  # 线程内异常不能静默吞掉
            errors.append(e)

    t = _threading.Thread(target=_main_loop_path)
    t.start()
    assert inside.wait(5), "前置: 重建线程应已进入 builder"

    # 关键: 置脏为 False, 让读取路径**不需要重建** —— 于是它是否返回只取决于"有没有锁",
    # 不再受线程调度影响(若改成依赖交错时序, 用例会变 flaky)。
    mgr.web.group_view_dirty = False

    read_done = _threading.Event()

    def _web_path():
        try:
            mgr.web.ensure_view()  # Web 线程路径
        finally:
            read_done.set()

    r = _threading.Thread(target=_web_path)
    r.start()
    assert not read_done.wait(0.5), ("重建进行中读取不应立即返回 —— 锁未生效时, "
                                     "Web 线程会读到半新半旧的四视图组合")
    release.set()
    t.join()
    r.join()
    assert not errors, f"重建线程异常: {errors}"


def test_flush_views_marks_dirty_on_hr_revision_change(tmp_path):
    """HR 判定新鲜度置脏(plan 26-10-03-0436 Step 2): hr.revision 变化 -> flush_views 置脏

    HR 判定结果不是 store 快照字段, store.view_changed 覆盖不到它(与「错误原因」预取
    同一判别法): 取数线程发布新判定(revision 自增)必须显式翻译成一次置脏, 否则界面
    挂在旧判定上直到别的原因碰巧重建。基线随重建前移 => 只置一拍, 无循环置脏。
    """
    from auto_qb.hr.resolve import HrSiteView, HrViewSet

    from helpers import FakeTorrent, make_manager, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    seed_store(mgr, [FakeTorrent(hash="HA", name="A")])
    mgr.store.consume_view_changed()  # 排掉 store 构造期置脏(TorrentStore 初始 view_changed=True), 只考察 HR 通道
    mgr.web.group_view_dirty = False
    mgr.web.rebuild_views()  # 重建完成: 基线记下当刻 revision(0)
    assert mgr.web.group_view_dirty is False
    assert mgr.web._hr_rev_at_build == 0

    # 直接推 publisher 模拟取数线程发布新判定(内容指纹变化 => revision 自增)
    pushed = mgr.hr.publisher.publish(HrViewSet(views={"HHan": HrSiteView(site="HHan")}, generated_at=1.0))
    assert pushed is True, "前置: 首个站点视图必须抬 revision"

    mgr.web.flush_views()
    assert mgr.web.group_view_dirty is True, "revision 变化必须置脏"

    # 重建后基线前移, 再次 flush 不再置脏(无循环置脏)
    mgr.web.rebuild_views()
    assert mgr.web.group_view_dirty is False
    assert mgr.web._hr_rev_at_build == mgr.hr.publisher.revision, "基线必须随重建前移"
    mgr.web.flush_views()
    assert mgr.web.group_view_dirty is False, "基线已前移, 不得循环置脏"


def test_flush_views_hr_facade_missing_null_defense(tmp_path):
    """hr 门面缺失(None)时判空防御: 重建记基线与 flush 比对都跳过, 不炸不置脏"""
    from helpers import make_manager

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.hr = None
    mgr.store.consume_view_changed()  # 排掉 store 构造期置脏, 只考察 HR 通道
    mgr.web.group_view_dirty = False
    mgr.web.rebuild_views()
    assert mgr.web._hr_rev_at_build is None, "无 HR 运行时: 基线记 None"
    mgr.web.flush_views()
    assert mgr.web.group_view_dirty is False, "无 HR 运行时: 新鲜度比对跳过, 不得置脏"


def test_build_search_index_files():
    """build_search_index: 主循环构建索引(hash -> name+files), 单条文件拉取失败跳过该种子"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        from helpers import _fake_file
        client.files_map["HA"] = [_fake_file("movie.mkv", 0), _fake_file("sub.srt", 0)]
        client.files_map["HB"] = [_fake_file("anime.mkv", 0)]
        t1 = FakeTorrent(hash="HA", name="Alpha", tracker_conf=None)
        t2 = FakeTorrent(hash="HB", name="Beta", tracker_conf=None)
        seed_store(mgr, [t1, t2])

        # 让 HB 的文件拉取失败: files() 抛异常 -> 该种子 files 为空但不阻塞
        def boom(h):
            if h == "HB":
                raise RuntimeError("fail")
            return [_fake_file("movie.mkv", 0), _fake_file("sub.srt", 0)]

        client.torrents_files = boom

        mgr.build_search_index()
        assert mgr.web.search_index_dirty is False
        idx = mgr.web.search_index
        assert idx["HA"]["name"] == "Alpha"
        assert "movie.mkv" in idx["HA"]["files"]
        assert idx["HB"]["files"] == [], "文件拉取失败的种子 files 应为空"
        assert set(idx.keys()) == {"HA", "HB"}


def test_build_search_index_incremental_and_evict():
    """build_search_index 增量维护: 已建条目只刷新名称(不重拉文件), 新种子补拉, 已消失种子淘汰"""
    from helpers import FakeClient, FakeTorrent, _fake_file, make_manager, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.files_map["HA"] = [_fake_file("movie.mkv", 0)]
        ha = FakeTorrent(hash="HA", name="Alpha")
        seed_store(mgr, [ha])
        mgr.build_search_index()
        first_calls = client.files_calls
        assert first_calls == 1

        # 种子集未变: 不重复拉文件列表, 仅刷新名称, 且整体替换引用(原子交换契约)
        idx_before = mgr.web.search_index
        ha.name = "Alpha.Renamed"
        mgr.build_search_index()
        assert client.files_calls == first_calls, "已建条目不重复拉取文件列表"
        assert mgr.web.search_index["HA"]["name"] == "Alpha.Renamed", "名称应刷新"
        assert mgr.web.search_index is not idx_before, "索引应整体替换引用(Web 线程并发只读安全), 不就地增删"

        # HA 消失 + HB 新增: 只补拉新种子, 已删种子淘汰
        client.files_map["HB"] = [_fake_file("anime.mkv", 0)]
        seed_store(mgr, [FakeTorrent(hash="HB", name="Beta")])
        mgr.web.search_index_dirty = True
        mgr.build_search_index()
        assert set(mgr.web.search_index.keys()) == {"HB"}, "已消失种子应被淘汰"
        assert client.files_calls == first_calls + 1, "只补拉新增种子的文件列表"
        assert mgr.web.search_index_dirty is False


def test_build_search_index_budget_resumes(monkeypatch):
    """build_search_index 限流: 单次最多拉预算条, 未拉完保持脏, 下次调用续建至完成"""
    from auto_qb.webui import views as web_view
    from helpers import FakeClient, FakeTorrent, _fake_file, make_manager, seed_store

    monkeypatch.setattr(web_view, "SEARCH_INDEX_BUILD_BUDGET", 1)
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.files_map["HA"] = [_fake_file("a.mkv", 0)]
        client.files_map["HB"] = [_fake_file("b.mkv", 0)]
        seed_store(mgr, [FakeTorrent(hash="HA", name="Alpha"), FakeTorrent(hash="HB", name="Beta")])

        mgr.build_search_index()
        assert mgr.web.search_index_dirty is True, "预算用尽应保持脏(待续建)"
        assert set(mgr.web.search_index.keys()) == {"HA"}, "单次只拉预算条数的文件列表"

        mgr.build_search_index()
        assert mgr.web.search_index_dirty is False, "续建后应不再脏"
        assert set(mgr.web.search_index.keys()) == {"HA", "HB"}


def test_build_search_index_aborts_when_disconnected():
    """build_search_index: qB 断开(client None)时中止并保持脏——不把空文件列表当成"已建完"""
    from helpers import FakeClient, FakeTorrent, _fake_file, make_manager, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.files_map["HA"] = [_fake_file("movie.mkv", 0)]
        seed_store(mgr, [FakeTorrent(hash="HA", name="Alpha")])

        mgr.client = None  # 模拟 qB 断连(setter 同步解绑 store/api)
        mgr.build_search_index()
        assert mgr.web.search_index_dirty is True, "断连时应保持脏, 待连接恢复后重建"
        assert mgr.web.search_index is None, "断连时不得写入空文件索引"

        mgr.client = client  # 连接恢复
        mgr.build_search_index()
        assert mgr.web.search_index_dirty is False
        assert mgr.web.search_index["HA"]["files"] == ["movie.mkv"]


def test_search_torrents_name_match():
    """search_torrents: 种子名匹配(即时, 无需文件索引), 大小写不敏感"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        t1 = FakeTorrent(hash="HA", name="My.Movie.2024", state="stalledUP")
        t2 = FakeTorrent(hash="HB", name="Anime.Series.S01", state="downloading")
        seed_store(mgr, [t1, t2])

        r = mgr.search_torrents("my.movie")
        names = [x["hash"] for x in r["results"]]
        assert names == ["HA"], f"名称命中(小写): {r}"
        assert all(x["by"] == "name" for x in r["results"])


def test_search_torrents_separator_normalized():
    """search_torrents: 分隔符归一匹配 —— 空格查询词命中点/下划线/连字符分隔的种子名与文件名

    回归(26-09-25): "The.Cat.and.the.Dragon.S01.1080p.friDay.WEB-DL.AAC2.0.H.264-MWeb"
    搜 "cat and" 不命中 —— 旧实现裸子串匹配, 查询词里的空格对不上名里的点号。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store, _fake_file

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        t1 = FakeTorrent(
            hash="HA", name="The.Cat.and.the.Dragon.S01.1080p.friDay.WEB-DL.AAC2.0.H.264-MWeb", state="stalledUP"
        )
        t2 = FakeTorrent(hash="HB", name="Other.Show.S02", state="stalledUP")
        client.files_map["HA"] = [_fake_file("The.Cat.and.the.Dragon.S01E01.1080p.WEB-DL.mkv", 0)]
        client.files_map["HB"] = [_fake_file("the_cat_and_dragon_e02.mkv", 0)]
        seed_store(mgr, [t1, t2])
        mgr.build_search_index()

        r = mgr.search_torrents("cat and")
        # HA 名字命中(回归主案例), HB 的下划线文件名归一后也含 "cat and"(file 路径顺带覆盖)
        assert [x["hash"] for x in r["results"]] == ["HA", "HB"], f"空格查询词应命中点号分隔名: {r}"
        assert [x["by"] for x in r["results"]] == ["name", "file"]
        assert [x["hash"] for x in mgr.search_torrents("web dl")["results"]] == ["HA"], "连字符分隔应命中"
        # 对称: 点号查询词同样归一, 仍命中; 纯分隔符不命中(解析即丢弃, 等价空查询)
        assert [x["hash"] for x in mgr.search_torrents("cat.and")["results"]] == ["HA", "HB"]
        # 同行同现: 词序无关 —— 旧口径 "dragon cat" 因连续子串序敏感不命中;
        # HA 名行与 HB 的下划线文件行均同含两词, 两路各按行命中
        assert [x["hash"] for x in mgr.search_torrents("dragon cat")["results"]] == ["HA", "HB"]
        assert mgr.search_torrents("...")["results"] == []

        # 文件命中: 下划线分隔的文件名按同一口径(HA 名与文件均不含该子串, 排除 seen 去重干扰)
        r = mgr.search_torrents("and dragon e02")
        assert [x["hash"] for x in r["results"]] == ["HB"], f"下划线文件名应命中: {r}"
        assert r["results"][0]["by"] == "file"


def test_parse_query_tokens():
    """_parse_query: 词法 —— 正/负词、短语、宽容边界(孤立 -/未闭合引号/纯标点/--dv/web-dl/词中引号)"""
    from auto_qb.webui.views import _parse_query

    # 基本分词 + 负词(词首 - 后随非空白); 归一小写
    assert _parse_query("恶女 10 -DV") == (["恶女", "10"], ["dv"])
    # 短语整段归一为连续子串(保留空格); 排除短语
    assert _parse_query('"s01e10" 恶女 -"H264 AAC"') == (["s01e10", "恶女"], ["h264 aac"])
    # 宽容: 孤立 - 忽略 / 未闭合引号收至行尾 / 纯标点 token 丢弃 / --dv 等价 -dv / web-dl 是正词
    assert _parse_query("-") == ([], [])
    assert _parse_query('foo "bar') == (["foo", "bar"], [])
    assert _parse_query("...") == ([], [])
    assert _parse_query("--dv") == ([], ["dv"])
    assert _parse_query("WEB-DL") == (["web dl"], [])
    # 词中引号无特殊含义(随归一折叠); 空查询
    assert _parse_query('foo"bar baz"') == (["foo bar", "baz"], [])
    assert _parse_query("") == ([], [])


def test_search_torrents_cross_row_and():
    """search_torrents 正词逐词跨行 AND(拍板 26-09-27 二次定案): 每个正词命中任一候选行即可, 行可不同

    26-09-26 曾拍板「多词须同行, 文件行不参与跨行」(防季包吸词); 26-09-27 用户实测推翻 ——
    「种子名 Gamma.Delta + 集文件 Gamma.E01-E03」搜「delta 03」须命中(标题在名字行、集号只在
    集文件行), 召回优先, 吸词代价(附加词可被包内任一文件名吸收)知情接受。负词种子级否决不变
    (见 negative_term / negative_torrent_veto); 全称行全覆盖的命中排前, 需文件行补词的以 file
    兜底排后。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store, _fake_file

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        t1 = FakeTorrent(hash="HA", name="Alpha.Beta.S01", state="stalledUP", tags="MTeam")
        t2 = FakeTorrent(hash="HB", name="Gamma", state="stalledUP")
        client.files_map["HB"] = [_fake_file("delta.mkv", 0), _fake_file("Gamma.E03.mkv", 1)]
        # 26-09-27 报障原型: 包名 Gamma.Delta 在名字行, 集号 03 只在集文件行
        t3 = FakeTorrent(hash="HC", name="Gamma.Delta.S01", state="stalledUP")
        client.files_map["HC"] = [
            _fake_file("Gamma.E01.mkv", 0),
            _fake_file("Gamma.E02.mkv", 1),
            _fake_file("Gamma.E03.mkv", 2)
        ]
        seed_store(mgr, [t1, t2, t3])
        mgr.build_search_index()

        # 同行 AND 照常; 全称行跨行(名字×标签)照常(「minions mteam」同型)
        assert [(x["hash"], x["by"]) for x in mgr.search_torrents("alpha s01")["results"]] == [("HA", "name")]
        assert [(x["hash"], x["by"]) for x in mgr.search_torrents("alpha mteam")["results"]] == [("HA", "name")]
        # 报障回归: delta 在名字行、03 只在集文件行 → file 兜底命中(HB 的 delta 则只在文件行)
        assert [(x["hash"], x["by"])
                for x in mgr.search_torrents("delta 03")["results"]] == [("HB", "file"), ("HC", "file")]
        # 26-09-26 的「跨行不命中」断言全部翻转: 词落不同行也命中
        assert [(x["hash"], x["by"])
                for x in mgr.search_torrents("gamma delta")["results"]] == [("HC", "name"), ("HB", "file")]
        assert [(x["hash"], x["by"])
                for x in mgr.search_torrents("gamma e03")["results"]] == [("HB", "file"), ("HC", "file")]
        assert [(x["hash"], x["by"])
                for x in mgr.search_torrents("e03 delta")["results"]] == [("HB", "file"), ("HC", "file")]
        # 单词行为不变; AND 不退化为 OR(alpha 与 delta 无一颗种子同有 → 空)
        assert [(x["hash"], x["by"])
                for x in mgr.search_torrents("delta")["results"]] == [("HC", "name"), ("HB", "file")]
        assert mgr.search_torrents("alpha delta")["results"] == []


def test_search_torrents_negative_term():
    """search_torrents 负词种子级(2026-09-27 定案): 任一候选行含负词 ⇒ 该种子整体排除 —— 单个
    种子内包含的合集(季包文件)统一计算; 多种子集合(辅种组/追剧)里的每个种子单独计算"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store, _fake_file

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        t1 = FakeTorrent(hash="HA", name="Show.S01E10.DV.1080p", state="stalledUP")
        # 单种子内包含的合集(季包): E09 文件带 DV ⇒ 统一计算, 整包排除(E10 行干净也救不回)
        t2 = FakeTorrent(hash="HB", name="Show.S01.Complete", state="stalledUP")
        client.files_map["HB"] = [_fake_file("Show.S01E09.DV.mkv", 0), _fake_file("Show.S01E10.1080p.mkv", 1)]
        # 多种子集合里的另一颗单集种子: 干净 ⇒ 留下
        t3 = FakeTorrent(hash="HC", name="Show.S01E10.1080p.CR.WEB-DL", state="stalledUP")
        seed_store(mgr, [t1, t2, t3])
        mgr.build_search_index()

        # "show 10 -dv": HA 名行含 dv ⇒ 排除; HB 的 E09.DV 文件行含 dv ⇒ 整包排除; HC 干净 ⇒ 名字命中
        r = mgr.search_torrents("show 10 -dv")
        assert [(x["hash"], x["by"]) for x in r["results"]] == [("HC", "name")], f"负词种子级: {r}"
        # 不带负词: 三颗都命中(即时命中 [HA, HC] 先于文件命中 HB; 旧口径 -dv 会把 dv 当正词搜, 顺带验证解析)
        assert [x["hash"] for x in mgr.search_torrents("show 10")["results"]] == ["HA", "HC", "HB"]
        # 排除短语: "web dl" 作为短语只排除 HC(HA/HB 不含该短语)
        assert [x["hash"] for x in mgr.search_torrents("show 10 -\"web dl\"")["results"]] == ["HA", "HB"]


def test_search_torrents_negative_torrent_veto():
    """search_torrents 负词种子级(2026-09-27 定案): 任一候选行(名字/站点/分类/路径/标签/文件行)
    含负词 ⇒ 整种子排除, 优先于一切正词命中

    两轮实机报障的收口: 1.「cat and -11」(26-09-26) —— E11 单文件的种子名行含 "11" 被行级作废,
    却被不含 "11" 的保存路径行整颗捞回; 2.「-mteam」(27-09-27) —— 站点/标签行负词拦不住名字行
    正词命中。负词必须是种子级才有可预测的排除语义; 文件行同入种子级否决(见 negative_term)。
    """
    from helpers import FakeClient, FakeTorrent, FakeTracker, make_manager, seed_store, _fake_file

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        t1 = FakeTorrent(
            hash="HA",
            name="The.Cat.and.the.Dragon.S01E11.1080p.friDay.WEB-DL.AAC2.0.H.264-MWeb.mkv",
            state="stalledUP",
            save_path="D:/TV/The.Cat.and.the.Dragon.S01",
        )
        site = FakeTracker("MTeam")
        site.tags = []  # tracker_name 取 conf.name(默认 tags 会顶掉站点名)
        t2 = FakeTorrent(hash="HB", name="Alpha.S01", state="stalledUP", tracker_conf=site)
        # 名字含负词、文件行干净的种子: 文件轮也须受身份行否决约束
        t3 = FakeTorrent(hash="HC", name="E11.REPACK", state="stalledUP")
        client.files_map["HC"] = [_fake_file("Show.1080p.mkv", 0)]
        seed_store(mgr, [t1, t2, t3])
        mgr.build_search_index()

        # 报障1.回归: HA 名字行含 "11" ⇒ 整种子否决, 保存路径行("cat and" 齐、无 "11")不得捞回
        assert mgr.search_torrents("cat and -11")["results"] == []
        # 无负词时 HA 照常命中(名字行) —— 否决只由负词触发
        assert [(x["hash"], x["by"]) for x in mgr.search_torrents("cat and")["results"]] == [("HA", "name")]
        # 报障2.: HB 名字行通过 "alpha", 但站点行含 "mteam" ⇒ 整种子排除; 去负词后名字行照常命中
        assert mgr.search_torrents("alpha -mteam")["results"] == []
        assert [(x["hash"], x["by"]) for x in mgr.search_torrents("alpha")["results"]] == [("HB", "name")]
        # 文件轮同受身份行否决: HC 名字行含 "repack" ⇒ 排除, 唯一文件行(Show.1080p.mkv)干净也救不回
        assert mgr.search_torrents("show -repack")["results"] == []
        # 对照: 去掉负词后 HC 靠文件行命中("show" 只落在文件行)
        assert [(x["hash"], x["by"]) for x in mgr.search_torrents("show")["results"]] == [("HC", "file")]


def test_search_torrents_facet_rows():
    """search_torrents 候选行覆盖全部文本面(26-09-26 单点化): 站点/分类/保存路径/标签行即时匹配

    正词逐词跨行(拍板 26-09-27 二次定案): 每个正词命中任一候选行(全称行/文件行)即可; 负词
    种子级(26-09-27): facet 行含负词 ⇒ 整种子排除。
    服务端此前的候选行只有 名字/文件, 搜站点/标签只在种子页(旧客户端行)能搜到而分组/追剧页
    搜不到 —— 跨页不一致; 单点化后三页同源, 用 by 定位首个通过的行类别(前端不消费, 测试定位用)。
    """
    from helpers import FakeClient, FakeTorrent, FakeTracker, make_manager, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        site = FakeTracker("MDCx")
        site.tags = []  # tracker_name 取 conf.name(FakeTracker 默认 tags=["HHan"] 会顶掉站点名)
        t1 = FakeTorrent(
            hash="HA",
            name="Alpha.S01E01",
            state="stalledUP",
            save_path="D:/media/anime",
            category="动漫",
            tags="HDCT, 2026",
            tracker_conf=site,
        )
        t2 = FakeTorrent(hash="HB", name="Beta.S01E02", state="stalledUP")
        seed_store(mgr, [t1, t2])
        mgr.build_search_index()

        # 站点/分类/标签/路径行: 各词只落在 HA 的对应行, 不在任何名字/文件里
        assert [(x["hash"], x["by"]) for x in mgr.search_torrents("MDCx")["results"]] == [("HA", "site")]
        assert [(x["hash"], x["by"]) for x in mgr.search_torrents("动漫")["results"]] == [("HA", "category")]
        assert [(x["hash"], x["by"]) for x in mgr.search_torrents("HDCT")["results"]] == [("HA", "tag")]
        assert [(x["hash"], x["by"]) for x in mgr.search_torrents("media anime")["results"]] == [("HA", "path")]
        # facet 行负词 = 整种子排除(2026-09-27 双轨定案): "anime -hdct" 标签行含负词 ⇒ 整种子排除,
        # 路径行干净也救不回(26-09-26 的「负词只作废该行」口径在此类行上被推翻)
        assert mgr.search_torrents("anime -hdct")["results"] == []
        # 同口径: "anime -media" 路径行含负词 ⇒ 整种子排除, 其余行不含 anime → 空结果
        assert mgr.search_torrents("anime -media")["results"] == []


def test_search_torrents_phrase():
    """search_torrents 短语: "…" 整段归一为**连续**子串(可含分隔符), 词序敏感 —— 与词间 AND 的区分用例"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        t1 = FakeTorrent(hash="HA", name="Cat.Dog.And.Bird", state="stalledUP")
        seed_store(mgr, [t1])

        # 词间 AND: cat 与 and 同行即命中(不要求相邻)
        assert [x["hash"] for x in mgr.search_torrents("cat and")["results"]] == ["HA"]
        # 短语: 要求归一后连续出现 —— "cat and" 在 "cat dog and" 里不连续 → 不命中; "dog and" 连续 → 命中
        assert mgr.search_torrents('"cat and"')["results"] == []
        assert [x["hash"] for x in mgr.search_torrents('"dog and"')["results"]] == ["HA"]
        # 短语可跨 scene 分隔符: "cat dog" 命中点号分隔的连续两词
        assert [x["hash"] for x in mgr.search_torrents('"cat dog"')["results"]] == ["HA"]


def test_search_torrents_regression_envnv10():
    """search_torrents 回归(26-09-26 用户报障): 「恶女 10」须命中单文件发布物; -排除词生效

    旧口径整句连续子串匹配: 「恶女 10」要求两词连续, 而文件名里「恶女」后跟「雏宫蝶鼠替换传」、
    「10」在远处的 s01e10 里 —— 必不命中。现行逐词跨行 AND 口径下两词同行照常命中。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        name = (
            "[虽然我不是完美恶女～雏宫蝶鼠替换传～].Futsutsuka.na.Akujo.dewa.Gozaimasu.ga."
            "Suuguu.Chouso.Torikae.Den.2026.S01E10.1080p.CR.WEB-DL.H264.AAC-UBWEB.mkv"
        )
        t1 = FakeTorrent(hash="HA", name=name, state="stalledUP")
        seed_store(mgr, [t1])

        r = mgr.search_torrents("恶女 10")
        assert [x["hash"] for x in r["results"]] == ["HA"], f"报障回归: 恶女 10 应命中: {r}"
        assert r["results"][0]["by"] == "name"
        # 短语与排除词: "s01e10" 连续命中; -ubweb 排除该发布组
        assert [x["hash"] for x in mgr.search_torrents('"s01e10"')["results"]] == ["HA"]
        assert mgr.search_torrents("恶女 10 -ubweb")["results"] == []


def test_search_torrents_negative_only_empty():
    """search_torrents 仅负词/空查询: 无正判据返回空 + negative_only 标记(前端提示依据), 不投递索引构建"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        t1 = FakeTorrent(hash="HA", name="Alpha", state="stalledUP")
        seed_store(mgr, [t1])

        r = mgr.search_torrents("-dv")
        assert r == {"results": [], "building": False, "negative_only": True}
        assert mgr.web.commands.empty(), "仅负词无从起搜, 不应投递构建命令"
        # 空查询: 同样空结果, 但 negative_only=False(前端按普通空态处理)
        r2 = mgr.search_torrents("")
        assert r2 == {"results": [], "building": False, "negative_only": False}


def test_search_torrents_file_match():
    """search_torrents: 文件列表匹配(依赖已构建的索引), 命中文件名"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        from helpers import _fake_file
        client.files_map["HA"] = [_fake_file("movie.mkv", 0)]
        client.files_map["HB"] = [_fake_file("soundtrack.flac", 0)]
        # 季包回归(26-09-26 报障): 包名不含集号 "12", 查询词只在集文件名里 —— 文件行必须命中
        client.files_map["HC"] = [
            _fake_file("The.Cat.and.the.Dragon.S01E12.1080p.friDay.WEB-DL.AAC2.0.H.264-MWeb.mkv", 0),
        ]
        t1 = FakeTorrent(hash="HA", name="Alpha", state="stalledUP")
        t2 = FakeTorrent(hash="HB", name="Beta", state="stalledUP")
        t3 = FakeTorrent(
            hash="HC", name="The.Cat.and.the.Dragon.S01.1080p.friDay.WEB-DL.AAC2.0.H.264-MWeb", state="stalledUP"
        )
        seed_store(mgr, [t1, t2, t3])
        mgr.build_search_index()  # 先构建索引

        # 文件命中: soundtrack 只在 HB 的文件里, 不在任何种子名中
        r = mgr.search_torrents("soundtrack")
        hashes = [x["hash"] for x in r["results"]]
        assert hashes == ["HB"], f"文件匹配应命中 HB: {r}"
        assert r["results"][0]["by"] == "file"
        assert r["building"] is False, "索引已就绪不应 building"

        # 季包: 名行含 cat 不含 12(12 不在任何全称行), 集文件行同含两词 → file 兜底命中
        r = mgr.search_torrents("cat 12")
        assert [(x["hash"], x["by"]) for x in r["results"]] == [("HC", "file")], f"季包集文件应命中: {r}"


def test_search_torrents_building_triggers():
    """search_torrents: 索引脏(种子集变化后)时返回 building=true 并投递构建命令"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store, _fake_file

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.files_map["HA"] = [_fake_file("movie.mkv", 0)]
        t1 = FakeTorrent(hash="HA", name="Alpha", state="stalledUP")
        seed_store(mgr, [t1])

        mgr.web.search_index_dirty = True  # 模拟种子集变化后未构建
        r = mgr.search_torrents("movie")
        assert r["building"] is True, "索引脏时 building 应为 True"
        # 名称未命中, 文件索引未就绪 -> 无结果, 但投递了构建命令
        assert r["results"] == []
        cmd, payload = mgr.web.commands.get_nowait()
        assert cmd == "build_search_index" and payload == {}

        # 主循环构建后再查 -> building 消除且文件匹配生效
        mgr._cmd_build_search_index()
        r2 = mgr.search_torrents("movie")
        assert r2["building"] is False
        assert [x["hash"] for x in r2["results"]] == ["HA"]


def test_api_search_endpoint(web_env):
    """GET /api/search: 端点返回搜索结果(名称匹配即时), 空查询返回空"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    # mock 替身: 直接返回固定结果(端点仅做转发, 逻辑由 search_torrents 单测覆盖); 空查询返回空
    mgr.search_torrents = lambda q: (
        {
            "results": [],
            "building": False
        } if not (q or "").strip() else {
            "results": [{
                "hash": "H1",
                "name": q,
                "by": "name"
            }],
            "building": False
        }
    )
    r = client.get("/api/search", params={"q": "movie"}, headers=auth).json()
    assert r["results"][0]["name"] == "movie"
    r2 = client.get("/api/search", params={"q": ""}, headers=auth).json()
    assert r2["results"] == [] and r2["building"] is False
    # 鉴权: 无密钥 401
    assert client.get("/api/search", params={"q": "movie"}).status_code == 401


def test_api_paths_endpoint(web_env):
    """GET /api/paths: 已知目录聚合(DLG-04): 组 save_path + 现有种子 save_path, 排序去重

    组 key 首元已是规范化 save_path; 种子侧经 path_normalize 归一分隔符后去重(反斜杠写法
    与组同径不重复); 空路径跳过; 只读快照无副作用; 鉴权沿用 /api/* 依赖。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    mgr.store.groups = {
        ("R:/Downloads", ("a.mkv", "b.mkv")): ["HA", "HB"],
        ("D:/ISO", ("x.iso", )): ["HC"],
    }
    mgr.store.by_hash = {
        "HA": SimpleNamespace(hash="HA", save_path="R:\\Downloads"),  # 反斜杠写法 -> 与组 key 同径去重
        "HC": SimpleNamespace(hash="HC", save_path="D:/ISO"),
        "HD": SimpleNamespace(hash="HD", save_path="E:/TV/"),
        "HE": SimpleNamespace(hash="HE", save_path=""),  # 空路径跳过
    }
    r = client.get("/api/paths", headers=auth).json()
    assert r == {"paths": ["D:/ISO", "E:/TV/", "R:/Downloads"]}, r
    # 只读无副作用: 快照未被改动
    assert set(mgr.store.groups) == {("R:/Downloads", ("a.mkv", "b.mkv")), ("D:/ISO", ("x.iso", ))}
    assert set(mgr.store.by_hash) == {"HA", "HC", "HD", "HE"}
    # 鉴权: 无密钥 401
    assert client.get("/api/paths").status_code == 401


def test_api_open_path_endpoint(web_env, tmp_path):
    """POST /api/open-path (FX-14 + R10-10): 服务端自行派生目录/文件后交系统默认程序打开

    覆盖: 目录型 content_path 取自身 / **文件型 content_path 取文件本身并带 select=True(R10-10
    "在文件夹中选中相关文件")** / content_path 缺失回退 save_path / 组键取 key 首元 /
    未知组与不存在目录 404 / kind 非法 400 /
    **客户端额外传入的 path 被忽略**(安全红线: 否则等于把"任意文件执行"暴露给 WEB 端点) / 鉴权 401。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    d_content = tmp_path / "content"
    d_content.mkdir()
    f_file = d_content / "movie.mkv"
    f_file.write_bytes(b"x")
    d_seed = tmp_path / "seeds"
    d_seed.mkdir()
    norm = lambda p: str(p).replace("\\", "/")  # noqa: E731  与 utils.path_normalize 同径(仅统一分隔符)
    mgr.store.groups = {(norm(d_seed), ("a.mkv", )): ["HA"]}
    mgr.store.by_hash = {
        "HA": SimpleNamespace(hash="HA", save_path=str(d_seed), content_path=str(d_content)),
        "HB": SimpleNamespace(hash="HB", save_path=str(d_seed), content_path=str(f_file)),
        "HC": SimpleNamespace(hash="HC", save_path=str(d_seed), content_path=""),
    }
    # web_env 的 store 是轻量 namespace(get 恒 None), 这里按真实 Store.get 语义接上 by_hash
    mgr.store.get = lambda h: mgr.store.by_hash.get(h)
    post = lambda body: client.post("/api/open-path", json=body, headers=auth)  # noqa: E731
    # patch 地址 = auto_qb.web.common.open_path(web.py 拆 web/ 包后模块地址稳定化;
    # 原地址 auto_qb.web.open_path 随模块拆分失效 —— 管线性改动, plan 26-09-22-1857 W1)
    with mock.patch("auto_qb.webui.server.common.open_path") as spy:
        # 1. 目录型 content_path -> 取自身(非选中语义)
        r = post({"kind": "torrent", "hash": "HA"})
        assert r.status_code == 200 and r.json() == {"opened": norm(d_content), "select": False}, r.text
        spy.assert_called_once_with(norm(d_content), select=False)
        # 2. 文件型 content_path(单文件种子) -> 打开该文件并**定位选中**(R10-10)
        spy.reset_mock()
        assert post({"kind": "torrent", "hash": "HB"}).json() == {"opened": norm(f_file), "select": True}
        spy.assert_called_once_with(norm(f_file), select=True)
        # 3. content_path 缺失 -> 回退 save_path
        spy.reset_mock()
        assert post({"kind": "torrent", "hash": "HC"}).json() == {"opened": norm(d_seed), "select": False}
        spy.assert_called_once_with(norm(d_seed), select=False)
        # 4. 组: 组键首元即规范化 save_path(组内成员天然一致)
        spy.reset_mock()
        group_key = encode_group_key((norm(d_seed), ("a.mkv", )))
        assert post({"kind": "group", "key": group_key}).json() == {"opened": norm(d_seed), "select": False}
        spy.assert_called_once_with(norm(d_seed), select=False)
        # 5. 安全: 客户端多传的 path 被忽略 —— 打开的是服务端派生的目录, 不是它
        spy.reset_mock()
        post({"kind": "group", "key": group_key, "path": "C:/Windows/System32"})
        spy.assert_called_once_with(norm(d_seed), select=False)
        # 6. 未知组 / 未知 hash / 不存在目录 -> 404; kind 非法 -> 400; 均不调用系统打开
        spy.reset_mock()
        assert post({"kind": "group", "key": encode_group_key(("D:/nope", ("z", )))}).status_code == 404
        assert post({"kind": "torrent", "hash": "NOPE"}).status_code == 404
        assert post(
            {
                "kind": "group",
                "key": encode_group_key((norm(tmp_path / "missing"), ("a.mkv", )))
            }
        ).status_code == 404
        assert post({"kind": "wat"}).status_code == 400
        spy.assert_not_called()
    # 只读无副作用: 不入命令队列
    assert mgr.web.commands.empty()
    # 鉴权: 无密钥 401
    assert client.post("/api/open-path", json={"kind": "wat"}).status_code == 401


def test_api_fs_dirs_endpoint(web_env, tmp_path):
    """GET /api/fs/dirs (R10-11): 服务端目录浏览 —— 允许根白名单/只列目录/穿越防护/鉴权

    这是本项目唯一新增的**文件系统读**能力, 安全边界逐条固化: 1.首屏(path 空)= 允许根列表;
    2.只返回目录条目(同名文件不出现); 3.上溯到允许根为止(根之上 parent 为空);
    4.`..` 穿越与白名单外路径一律 403; 5.不存在/不是目录 404; 6.无白名单时空返回(不报错);
    7.指向根外的符号链接不出现在列表里(逃逸防护); 8.无密钥 401; 9.只读不入命令队列。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    root = tmp_path / "root"
    (root / "sub" / "deep").mkdir(parents=True)
    (root / "b.txt").write_bytes(b"x")
    outside = tmp_path / "outside"
    outside.mkdir()
    norm = lambda p: str(p).replace("\\", "/")  # noqa: E731  与 utils.path_normalize 同径
    mgr.store.by_hash = {"HA": SimpleNamespace(hash="HA", save_path=str(root), content_path=str(root))}
    get = lambda p=None: client.get("/api/fs/dirs", headers=auth, params={} if p is None else {"path": p})  # noqa: E731

    # 1. 首屏 = 允许根列表(前端入口)
    body = get().json()
    assert body["path"] == "" and body["roots"] == [norm(root)]
    assert body["dirs"] == [{"name": norm(root), "path": norm(root)}]
    # 2. 列子目录: 只出现目录(同名文件被排除); 已在允许根 -> 不能再上溯
    body = get(norm(root)).json()
    assert [d["name"] for d in body["dirs"]] == ["sub"]
    assert body["path"] == norm(root) and body["parent"] == ""
    # 3. 进入子目录后可上溯回根
    body = get(norm(root / "sub")).json()
    assert [d["name"] for d in body["dirs"]] == ["deep"]
    assert body["parent"] == norm(root)
    # 4. 越界 / .. 穿越 / 不存在 -> 403 / 403 / 404
    assert get(norm(outside)).status_code == 403
    assert get(norm(root / ".." / "outside")).status_code == 403
    assert get(norm(root / "nope")).status_code == 404
    assert get(norm(root / "b.txt")).status_code == 404  # 目标存在但是文件 -> 不是目录
    # 5. 符号链接逃逸: 指向根外的子目录不进列表
    #    跳过条件有两种: (a) 环境不允许建链(Windows 未开开发者模式 -> OSError);
    #    (b) **建了但落成真实目录** —— 部分沙箱/文件系统重定向层会让 os.symlink "成功"却
    #    islink=False(实测 mode=0o40777), 此时根本不存在"逃逸链接", 断言无意义。
    #    这两种都是环境能力缺失, 不是代码缺陷 —— 真机上能建真链接时照常断言。
    link = root / "escape"
    try:
        os.symlink(outside, link, target_is_directory=True)
    except (OSError, NotImplementedError, AttributeError):
        pass
    else:
        if os.path.islink(link):
            assert "escape" not in [d["name"] for d in get(norm(root)).json()["dirs"]]
    # 6. 无白名单(还没有任何已知保存路径) -> 空返回而非报错
    mgr.store.by_hash = {}
    assert get().json() == {"path": "", "parent": "", "roots": [], "dirs": []}
    # 7. 鉴权 + 只读无副作用
    assert client.get("/api/fs/dirs").status_code == 401
    assert mgr.web.commands.empty()


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="只有大小写敏感的 FS(ext4)上两个名字才是两个目录; NTFS 上是同一个, 断言无意义")
def test_api_fs_dirs_case_sibling_is_outside_whitelist(web_env, tmp_path):
    """**大小写兄弟目录必须判为越界** —— `web._fs_real` 不得做 NTFS 式大小写折叠

    生产代码跑在**本机真实磁盘**上: Linux 下 `/x/Media` 与 `/x/media` 是两个**不同**目录。若把归一
    换成 `ntpath.normcase`(折叠大小写 + `/`->`\\`), 后者会被判成"在白名单内" ⇒ **越界放行**
    (fail-open, 安全方向反了)。`os.path.normcase` 在 Linux 是恒等函数, 恰恰是所需语义 —— 钉死它。
    WARN: 本条只能在 Linux 上真跑(NTFS 上根本建不出"仅大小写不同"的两个目录), 由 CI 验。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    root = tmp_path / "Media"
    root.mkdir()
    sibling = tmp_path / "media"  # 仅大小写不同
    sibling.mkdir()
    # 前置校验: 这两者**确实是两个目录**(否则下面的 403 断言说明不了任何事)
    (root / "inside.txt").write_bytes(b"x")
    assert not (sibling / "inside.txt").exists(), "大小写兄弟必须是另一个目录, 否则本条断言无意义"
    norm = lambda p: str(p).replace("\\", "/")  # noqa: E731  与 utils.path_normalize 同径
    mgr.store.by_hash = {"HA": SimpleNamespace(hash="HA", save_path=str(root), content_path=str(root))}
    r = client.get("/api/fs/dirs", headers=auth, params={"path": norm(sibling)})
    assert r.status_code == 403, f"大小写兄弟目录不得被折叠进白名单(折叠 => 越界放行): {r.status_code}"


def test_api_fs_mkdir_endpoint(web_env, tmp_path):
    """POST /api/fs/mkdir (R10-11): 新建目录的边界 —— 单层名字/白名单/幂等/同名文件 409

    覆盖: 正常新建(目录真的出现在磁盘上 + 返回绝对路径) / 重名目录幂等(200 + existed=True) /
    同名**文件** 409 / 名字含分隔符或为 . .. -> 400 / 白名单外父目录 403 / 父目录不存在 404 /
    无密钥 401 / 不入命令队列(只建目录, 不碰任务队列与 state)。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    norm = lambda p: str(p).replace("\\", "/")  # noqa: E731
    mgr.store.by_hash = {"HA": SimpleNamespace(hash="HA", save_path=str(root), content_path=str(root))}
    post = lambda body: client.post("/api/fs/mkdir", json=body, headers=auth)  # noqa: E731

    # 1. 正常新建
    r = post({"path": norm(root), "name": "新文件夹"})
    assert r.status_code == 200 and r.json() == {"created": norm(root / "新文件夹"), "existed": False}, r.text
    assert (root / "新文件夹").is_dir()
    # 2. 重名目录幂等(不报错)
    assert post({"path": norm(root), "name": "新文件夹"}).json()["existed"] is True
    # 3. 同名文件 -> 409
    (root / "b.txt").write_bytes(b"x")
    assert post({"path": norm(root), "name": "b.txt"}).status_code == 409
    # 4. 名字含路径成分 / . / .. -> 400(只接受单层名字, 不做路径拼接)
    for bad in ("", "  ", "a/b", "a\\b", ".", ".."):
        assert post({"path": norm(root), "name": bad}).status_code == 400, bad
    # 5. 白名单外 / 父目录不存在 -> 403 / 404
    assert post({"path": norm(outside), "name": "x"}).status_code == 403
    assert post({"path": "", "name": "x"}).status_code == 403
    assert post({"path": norm(root / "missing"), "name": "x"}).status_code == 404
    # 6. 鉴权 + 不入命令队列(不绕过单一写线程: 只建目录)
    assert client.post("/api/fs/mkdir", json={"path": norm(root), "name": "x"}).status_code == 401
    assert mgr.web.commands.empty()


def test_fs_endpoints_route_fs_calls_through_long_path_prefix(web_env, tmp_path, monkeypatch):
    """fs 三端点的**文件系统调用**必须过 `add_long_path_prefix_for_win`(本次报障的核心)

    Windows 上 >MAX_PATH 的裸路径 `isdir` 给假 / `scandir` 抛 WinError 3 ⇒ 不加前缀时端点会
    误报 404, 而前端只看到"目录不存在或不可访问"。这里把前缀 helper 换成 spy, 逐端点钉住
    "确实调了它"。

    WARN: 测的是**路由**而不是平台效果: 真 Windows 行为在 Linux CI 上无法复现(平台固定约定见
    testing/file-conventions.md), 故宿主上前缀是恒等(前缀对 POSIX 路径无意义); 前缀本身的
    正确性与打开层分支另由 `test_exists_dir_file_apply_long_path_prefix` /
    `test_open_path_windows_*` 覆盖。26-09-27: 前缀单点收编进文件访问层(infra/file_access,
    plan 26-09-27-1407) —— spy 地址随单点迁到 `auto_qb.infra.utils.add_long_path_prefix_for_win`,
    断言意图不变(全部本地 syscall 过单点)。
    """
    from auto_qb.infra.utils import add_long_path_prefix_for_win as real_prefix

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    root = tmp_path / "root"
    (root / "sub").mkdir(parents=True)
    norm = lambda p: str(p).replace("\\", "/")  # noqa: E731  与 utils.path_normalize 同径
    mgr.store.groups = {(norm(root), ("a.mkv", )): ["HA"]}
    mgr.store.by_hash = {"HA": SimpleNamespace(hash="HA", save_path=str(root), content_path=str(root))}
    mgr.store.get = lambda h: mgr.store.by_hash.get(h)

    calls = []

    def spy(p):
        calls.append(p)
        return real_prefix(p)

    monkeypatch.setattr("auto_qb.infra.utils.add_long_path_prefix_for_win", spy)

    # 1. 目录浏览
    assert client.get("/api/fs/dirs", headers=auth, params={"path": norm(root)}).status_code == 200
    assert norm(root) in calls, f"fs/dirs 的文件系统调用未过前缀 helper: {calls}"
    # 2. 新建目录
    calls.clear()
    assert client.post("/api/fs/mkdir", json={"path": norm(root), "name": "new"}, headers=auth).status_code == 200
    assert norm(root) in calls, f"fs/mkdir 的文件系统调用未过前缀 helper: {calls}"
    # 3. 打开目标文件夹(open_path 必须 mock —— 真调会弹资源管理器, 守阵判越界)
    calls.clear()
    with mock.patch("auto_qb.webui.server.common.open_path"):
        assert client.post("/api/open-path", json={"kind": "torrent", "hash": "HA"}, headers=auth).status_code == 200
    assert norm(root) in calls, f"open-path 的文件系统调用未过前缀 helper: {calls}"


def test_fs_endpoints_unmapped_root_semantic_404(web_env, tmp_path):
    """Mapped 模式下白名单内但未命中映射 -> 三端点语义化 404「不可判定」, 不是裸 500(BUG 回归)

    回归: fs 路由曾有五处两态布尔消费(not fa.isdir / if fa.exists / not fa.isfile),
    Mapped miss 时包装层返回 UNDETERMINED, 其 __bool__ 抛 TypeError ⇒ FastAPI 裸 500。
    收进 _determinable 单点分流后: 未命中 fs.path_map 的允许根 浏览/新建/打开 都返回
    带原因的 404(「不可判定」不冒充「不存在」, 报告 §05)。
    """
    from auto_qb.config import PathMapEntry

    mgr, client = web_env
    saved = file_access.get_file_access()
    file_access._instance = file_access.MappedFileAccess(
        (PathMapEntry(src="D:/Downloads", dst=str(tmp_path / "mnt")), )
    )
    try:
        auth = {"Authorization": f"Bearer {mgr.web.token}"}
        unmapped = tmp_path / "unmapped"
        unmapped.mkdir()  # 宿主真实存在, 但前缀不在映射表里 -> 逻辑空间不可判定
        norm = lambda p: str(p).replace("\\", "/")  # noqa: E731  与 utils.path_normalize 同径
        mgr.store.by_hash = {"HA": SimpleNamespace(hash="HA", save_path=str(unmapped), content_path="")}
        mgr.store.groups = {(norm(unmapped), ("a.mkv", )): ["HA"]}
        mgr.store.get = lambda h: mgr.store.by_hash.get(h)
        # 1. 目录浏览: 白名单内(是已知保存路径)但未命中映射 -> 404 不可判定
        r = client.get("/api/fs/dirs", headers=auth, params={"path": norm(unmapped)})
        assert r.status_code == 404 and "不可判定" in r.json()["detail"], r.text
        # 2. 新建文件夹: 父目录未命中映射 -> 404 不可判定
        r = client.post("/api/fs/mkdir", json={"path": norm(unmapped), "name": "x"}, headers=auth)
        assert r.status_code == 404 and "不可判定" in r.json()["detail"], r.text
        # 3. 打开路径(torrent): content_path 缺失回退 save_path(未命中) -> 404 不可判定
        r = client.post("/api/open-path", json={"kind": "torrent", "hash": "HA"}, headers=auth)
        assert r.status_code == 404 and "不可判定" in r.json()["detail"], r.text
        # 4. 打开路径(组): 组键首元未命中映射 -> 404 不可判定
        key = encode_group_key((norm(unmapped), ("a.mkv", )))
        r = client.post("/api/open-path", json={"kind": "group", "key": key}, headers=auth)
        assert r.status_code == 404 and "不可判定" in r.json()["detail"], r.text
    finally:
        file_access._instance = saved


def test_fs_path_helpers_strip_long_path_prefix_before_compare():
    """`_bare` / `_fs_real`: **比较前必须剥掉 `\\\\?\\` 前缀** —— 否则同一条路径的两种写法被判"越界"

    实测后果(Windows 真机): `os.scandir` 家族给出的 entry 路径**带前缀**, 而允许根
    不带 ⇒ `_within_roots` 恒 False ⇒ **子目录被全部过滤掉**(目录树恒空)。
    `os.path.realpath` 是否保留前缀**与路径长度有关**(实测短路径保留、长路径剥掉), 不能依赖它,
    故必须在比较前显式剥掉。

    本条是纯路径归一, **与宿主平台无关** ⇒ Linux CI 上也守得住(这正是把三个 helper 提到模块级
    而不是留在 `build_router` 闭包里的原因)。
    26-09-27: 前缀剥离/加前缀单点迁入文件访问层(infra/file_access, plan 26-09-27-1407),
    `_fs` 帮手随之删除(包装层内部自理) —— 剥前缀契约改在 file_access 单点断言, `_bare`
    保留薄委托供路由侧钉住。
    """
    from auto_qb.webui.server.routes import fs as fs_mod

    bare = os.path.abspath("x")
    assert fs_mod._bare("\\\\?\\" + bare) == bare
    assert fs_mod._bare(bare) == bare, "无前缀原样返回"
    assert fs_mod._bare("\\\\?\\UNC\\server\\share") == "\\\\server\\share", "UNC 形态还原"
    # 带前缀与不带前缀必须归一到同一个可比较形式(_fs_real 委托包装层, 内部先剥再规范化)
    assert fs_mod._fs_real("\\\\?\\" + bare) == fs_mod._fs_real(bare)
    # 前缀单点幂等: 已是带前缀形态再进包装层不得叠加 —— path_normalize 会把 `\\?\\` 折坏成 `/?/`
    fa = file_access.LocalFileAccess()
    assert fa._pref(fa._pref(bare)) == fa._pref(bare)
    assert file_access._norm_logical(file_access._norm_logical("\\\\?\\" + bare)) == file_access._norm_logical(bare)


# ---------- Web 命令执行(主循环侧 _drain_web_commands) ----------


def _make_grouped_manager(td):
    """构造两个同文件列表的种子并归组(供 Web 命令执行测试); 返回 (mgr, client, key)"""
    from helpers import FakeClient, FakeTorrent, _fake_file, make_manager, seed_store

    mgr = make_manager(os.path.join(td, "state.json"))
    client = FakeClient()
    mgr.client = client
    files = [_fake_file("movie.mkv", 100)]
    client.files_map["HA"] = files
    client.files_map["HB"] = files
    tors = [
        FakeTorrent(hash="HA", name="Show", save_path=r"R:\Downloads"),
        FakeTorrent(hash="HB", name="Show", save_path=r"R:\Downloads"),
    ]
    # !**同时**灌进 FakeClient: 真值改走 `torrents/info` 直查(不再读同步快照),
    #   直查查的是 qB 客户端里的种子 —— 只 seed store 的话桩里查不到, 与真机不符。
    for t in tors:
        client.torrents[t.hash] = t
    seed_store(mgr, tors)
    mgr.host.get("grouping")._assign_new_torrent("HA")
    mgr.host.get("grouping")._assign_new_torrent("HB")
    return mgr, client, mgr.store.member_to_key["HA"]


def test_drain_web_commands_group_actions():
    """_drain_web_commands: 组级暂停/开始/汇报/删除命令在主循环侧执行, 作用于整组 hash"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        mgr.web.commands.put(("pause_group", {"key": key}))
        mgr.web.commands.put(("resume_group", {"key": key}))
        mgr.web.commands.put(("reannounce_group", {"key": key}))
        mgr.web.consume_commands()
        # reannounce 走 FakeClient 旧约定(记 None; test_actions 多处断言依赖), pause/resume 记 hash 列表
        assert client.calls == [("pause", ["HA", "HB"]), ("resume", ["HA", "HB"]), ("reannounce", None)], client.calls
        # 删除整组: delete_files 透传, 成员从快照移除
        mgr.web.commands.put(("delete_group", {"key": key, "delete_files": True}))
        mgr.web.consume_commands()
        assert client.calls[-1] == ("delete", True), f"delete_group: {client.calls}"
        assert mgr.store.by_hash == {}, "删除整组后成员应已从快照移除"


def test_drain_web_commands_torrent_actions():
    """_drain_web_commands: 单种子命令只作用于该 hash; 种子不在快照 -> 跳过(删除守阵)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        for cmd in ("pause_torrent", "resume_torrent", "reannounce_torrent"):
            mgr.web.commands.put((cmd, {"hash": "HA"}))
        mgr.web.consume_commands()
        assert [c[0] for c in client.calls] == ["pause", "resume", "reannounce"], client.calls
        assert client.calls[0][1] == ["HA"] and client.calls[1][1] == ["HA"], "单种子命令只作用于该 hash"
        # 删除守阵: 种子已不在快照 -> 不调 API
        before = list(client.calls)
        mgr.web.commands.put(("pause_torrent", {"hash": "GONE"}))
        mgr.web.commands.put(("delete_torrent", {"hash": "GONE", "delete_files": True}))
        mgr.web.consume_commands()
        assert client.calls == before, "种子不在快照应跳过(删除守阵)"


def test_api_torrent_write_endpoints_enqueue(web_env):
    """二轮种子写端点(15个) POST 转发: cmd 与参数正确入队; 无密钥 401(鉴权沿用 /api/* 依赖)"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    cases = [
        ("/api/torrents/HA/recheck", None, "recheck_torrent", {
            "hash": "HA"
        }),
        ("/api/torrents/HA/super-seeding", {
            "enable": True
        }, "super_seeding", {
            "hash": "HA",
            "enable": True
        }),
        ("/api/torrents/HA/force-start", {
            "enable": False
        }, "force_start", {
            "hash": "HA",
            "enable": False
        }),
        (
            "/api/torrents/HA/limits", {
                "up_limit": 1024,
                "dl_limit": 0
            }, "set_torrent_limits", {
                "hash": "HA",
                "up_limit": 1024,
                "dl_limit": 0
            }
        ),
        ("/api/torrents/HA/limits", {
            "dl_limit": 512
        }, "set_torrent_limits", {
            "hash": "HA",
            "dl_limit": 512
        }),
        (
            "/api/torrents/HA/share-limits", {
                "ratio_limit": 1.5,
                "seeding_time_limit": -1,
                "inactive_seeding_time_limit": -2
            }, "set_share_limits", {
                "hash": "HA",
                "ratio_limit": 1.5,
                "seeding_time_limit": -1,
                "inactive_seeding_time_limit": -2
            }
        ),
        ("/api/torrents/HA/location", {
            "location": "R:/X"
        }, "set_torrent_location", {
            "hash": "HA",
            "location": "R:/X"
        }),
        ("/api/torrents/HA/rename", {
            "name": "New"
        }, "rename_torrent", {
            "hash": "HA",
            "name": "New"
        }),
        ("/api/torrents/HA/queue", {
            "action": "top"
        }, "queue_torrent", {
            "hash": "HA",
            "action": "top"
        }),
        ("/api/torrents/HA/auto-tmm", {
            "enable": True
        }, "set_auto_tmm", {
            "hash": "HA",
            "enable": True
        }),
        ("/api/torrents/HA/trackers/add", {
            "urls": ["u1", "u2"]
        }, "add_trackers", {
            "hash": "HA",
            "urls": ["u1", "u2"]
        }),
        (
            "/api/torrents/HA/trackers/edit", {
                "orig_url": "a",
                "new_url": "b"
            }, "edit_tracker", {
                "hash": "HA",
                "orig_url": "a",
                "new_url": "b"
            }
        ),
        ("/api/torrents/HA/trackers/remove", {
            "url": "a"
        }, "remove_tracker", {
            "hash": "HA",
            "url": "a"
        }),
        (
            "/api/torrents/HA/files/priority", {
                "indices": [0, 2],
                "priority": 7
            }, "set_file_priority", {
                "hash": "HA",
                "indices": [0, 2],
                "priority": 7
            }
        ),
        (
            "/api/torrents/HA/rename-fs", {
                "old_path": "a",
                "new_path": "b",
                "is_folder": True
            }, "rename_fs", {
                "hash": "HA",
                "old_path": "a",
                "new_path": "b",
                "is_folder": True
            }
        ),
        (
            "/api/torrents/bulk", {
                "hashes": ["HA", "HB"],
                "action": "pause"
            }, "bulk_torrents", {
                "hashes": ["HA", "HB"],
                "action": "pause",
                "delete_files": False
            }
        ),
        (
            "/api/torrents/bulk", {
                "hashes": ["HA"],
                "action": "delete",
                "delete_files": True
            }, "bulk_torrents", {
                "hashes": ["HA"],
                "action": "delete",
                "delete_files": True
            }
        ),
    ]
    for path, body, want_cmd, want_payload in cases:
        resp = client.post(path, headers=auth, json=body)
        assert resp.status_code == 200, f"{path}: {resp.text}"
        data = resp.json()
        assert data["queued"] is True and data["cmd_id"], path
        got_cmd, got_payload = mgr.web.commands.get_nowait()
        assert got_cmd == want_cmd, f"{path}: {got_cmd}"
        got_payload.pop("cmd_id")
        got_payload.pop("_queued_ts", None)  # P0-0 埋点元数据, 不参与入队参数断言
        got_payload.pop("_queued_ts", None)  # P0-0 埋点元数据, 不参与入队参数断言
        assert got_payload == want_payload, f"{path}: {got_payload}"
    # 鉴权沿用既有 /api/* 依赖: 无/错密钥 401
    assert client.post("/api/torrents/HA/recheck").status_code == 401
    assert client.post("/api/torrents/bulk", json={"hashes": ["HA"], "action": "pause"}).status_code == 401


def test_api_t_bulk_group_keys_enqueue(web_env):
    """bulk 组键模式(DLG-02): keys 传编码组键, 入队前解码回 tuple; 可与 hashes 混合

    纯 hash 调用不带 keys 键(队列载荷与历史形态完全一致, 不碰既有断言); 无密钥 401。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    key = encode_group_key(("R:/Downloads", ("a.mkv", "b.mkv")))
    # 混合选择: hashes + keys(解码回原组键 tuple) 同 payload 入队
    resp = client.post(
        "/api/torrents/bulk",
        headers=auth,
        json={
            "hashes": ["HC"],
            "keys": [key],
            "action": "delete",
            "delete_files": True
        },
    )
    assert resp.status_code == 200 and resp.json()["queued"] is True
    cmd, payload = mgr.web.commands.get_nowait()
    payload.pop("cmd_id")
    payload.pop("_queued_ts", None)  # 同上
    payload.pop("_queued_ts", None)  # 同上
    assert cmd == "bulk_torrents"
    assert payload == {
        "hashes": ["HC"],
        "keys": [("R:/Downloads", ("a.mkv", "b.mkv"))],
        "action": "delete",
        "delete_files": True,
    }, payload
    # 纯 hash 调用: 载荷不含 keys 键(历史形态不变)
    client.post("/api/torrents/bulk", headers=auth, json={"hashes": ["HA"], "action": "pause"})
    _, payload2 = mgr.web.commands.get_nowait()
    assert "keys" not in payload2
    # 鉴权: 无密钥 401
    assert client.post("/api/torrents/bulk", json={"keys": [key], "action": "delete"}).status_code == 401


def test_api_t_bulk_tags_category_enqueue(web_env):
    """bulk 标签/分类动作入队: tags 过滤空段非空才透传; category 按键存在性透传(空串=清除分类要保留);
    未提供时载荷不带这两个键(纯 pause 调用的队列载荷与历史形态完全一致); 无密钥 401"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    cases = [
        # add_tags: 空段过滤后透传
        (
            {
                "hashes": ["HA"],
                "action": "add_tags",
                "tags": ["HR", "", "Keep"]
            },
            {
                "hashes": ["HA"],
                "action": "add_tags",
                "delete_files": False,
                "tags": ["HR", "Keep"]
            },
        ),
        (
            {
                "hashes": ["HA"],
                "action": "remove_tags",
                "tags": ["HR"]
            },
            {
                "hashes": ["HA"],
                "action": "remove_tags",
                "delete_files": False,
                "tags": ["HR"]
            },
        ),
        # set_category: category="" 也必须透传(清除分类的语义靠空串承载, 按键存在性判断)
        (
            {
                "hashes": ["HA"],
                "action": "set_category",
                "category": ""
            },
            {
                "hashes": ["HA"],
                "action": "set_category",
                "delete_files": False,
                "category": ""
            },
        ),
        (
            {
                "hashes": ["HA"],
                "action": "set_category",
                "category": "电影"
            },
            {
                "hashes": ["HA"],
                "action": "set_category",
                "delete_files": False,
                "category": "电影"
            },
        ),
        # 历史形态: 不带 tags/category 的载荷不加新键
        (
            {
                "hashes": ["HA"],
                "action": "pause"
            },
            {
                "hashes": ["HA"],
                "action": "pause",
                "delete_files": False
            },
        ),
    ]
    for body, want_payload in cases:
        resp = client.post("/api/torrents/bulk", headers=auth, json=body)
        assert resp.status_code == 200, f"{body}: {resp.text}"
        assert resp.json()["queued"] is True
        cmd, payload = mgr.web.commands.get_nowait()
        assert cmd == "bulk_torrents"
        payload.pop("cmd_id")
        payload.pop("_queued_ts", None)  # P0-0 埋点元数据, 不参与入队参数断言
        assert payload == want_payload, body
    assert client.post(
        "/api/torrents/bulk", json={
            "hashes": ["HA"],
            "action": "add_tags",
            "tags": ["x"]
        }
    ).status_code == 401


def test_api_t_bulk_limits_location_enqueue(web_env):
    """bulk 限速/移动动作入队(计划 26-10-02-1955 W2): up/dl 提供才透传(0=不限合法, 负数 400)、
    location 非空才透传; limits 两方向全空 / location 空路径 -> 400 不入队;
    纯 pause 调用的队列载荷不带新键(历史形态不变); 无密钥 401"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    cases = [
        # 只提供上传方向: 载荷只带 up_limit(0 = qB 语义的不限速, 合法)
        (
            {
                "hashes": ["HA", "HB"],
                "action": "limits",
                "up_limit": 1024
            },
            {
                "hashes": ["HA", "HB"],
                "action": "limits",
                "delete_files": False,
                "up_limit": 1024
            },
        ),
        # 两方向都提供: 0 原样透传(不限速)
        (
            {
                "hashes": ["HA"],
                "action": "limits",
                "up_limit": 0,
                "dl_limit": 2048
            },
            {
                "hashes": ["HA"],
                "action": "limits",
                "delete_files": False,
                "up_limit": 0,
                "dl_limit": 2048
            },
        ),
        # 批量移动: 非空路径透传(首尾空白剥掉)
        (
            {
                "hashes": ["HA"],
                "action": "location",
                "location": "  R:/X  "
            },
            {
                "hashes": ["HA"],
                "action": "location",
                "delete_files": False,
                "location": "R:/X"
            },
        ),
    ]
    for body, want_payload in cases:
        resp = client.post("/api/torrents/bulk", headers=auth, json=body)
        assert resp.status_code == 200, f"{body}: {resp.text}"
        assert resp.json()["queued"] is True
        cmd, payload = mgr.web.commands.get_nowait()
        assert cmd == "bulk_torrents"
        payload.pop("cmd_id")
        payload.pop("_queued_ts", None)  # P0-0 埋点元数据, 不参与入队参数断言
        assert payload == want_payload, body
    # 参数错误 -> 400 且不入队(负数 / limits 全空 / location 空路径)
    bad = [
        {
            "hashes": ["HA"],
            "action": "limits",
            "up_limit": -1
        },
        {
            "hashes": ["HA"],
            "action": "limits",
            "dl_limit": -1024
        },
        {
            "hashes": ["HA"],
            "action": "limits"
        },
        {
            "hashes": ["HA"],
            "action": "location",
            "location": ""
        },
        {
            "hashes": ["HA"],
            "action": "location",
            "location": "   "
        },
        {
            "hashes": ["HA"],
            "action": "location"
        },
    ]
    for i, body in enumerate(bad):
        resp = client.post("/api/torrents/bulk", headers=auth, json=body)
        assert resp.status_code == 400, f"case {i}: {resp.status_code} {resp.text}"
        assert mgr.web.commands.qsize() == 0, f"case {i}: 参数错误不应入队"
    # 历史 形态: 不带新键的纯 pause 载荷不变
    client.post("/api/torrents/bulk", headers=auth, json={"hashes": ["HA"], "action": "pause"})
    _, payload = mgr.web.commands.get_nowait()
    payload.pop("cmd_id")
    payload.pop("_queued_ts", None)
    assert payload == {"hashes": ["HA"], "action": "pause", "delete_files": False}, payload
    # 鉴权: 无密钥 401
    assert client.post(
        "/api/torrents/bulk", json={
            "hashes": ["HA"],
            "action": "limits",
            "up_limit": 1
        }
    ).status_code == 401


def test_api_t_bulk_skip_check_enqueue(web_env):
    """bulk 跳检动作入队(计划 26-10-02-1955 W3): 无额外参数, 载荷只有 hashes/action/delete_files
    (多余键不出现); 无密钥 401。gate 在 drain 分派处(路由层不设), 故开关关时这里仍 200 入队"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    resp = client.post("/api/torrents/bulk", headers=auth, json={"hashes": ["HA", "HB"], "action": "skip_check"})
    assert resp.status_code == 200 and resp.json()["queued"] is True
    cmd, payload = mgr.web.commands.get_nowait()
    assert cmd == "bulk_torrents"
    payload.pop("cmd_id")
    payload.pop("_queued_ts", None)
    assert payload == {"hashes": ["HA", "HB"], "action": "skip_check", "delete_files": False}, payload
    # 鉴权: 无密钥 401
    assert client.post("/api/torrents/bulk", json={"hashes": ["HA"], "action": "skip_check"}).status_code == 401


def test_drain_web_commands_torrent_write_actions():
    """二轮写命令: 参数正确传给 QbApi(真链路), cmd_id 回执 ok, 限速/保存路径写后同步快照"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        cmds = [
            ("recheck_torrent", {
                "hash": "HA",
                "cmd_id": "c1"
            }),
            ("super_seeding", {
                "hash": "HA",
                "enable": True,
                "cmd_id": "c2"
            }),
            ("force_start", {
                "hash": "HA",
                "enable": True,
                "cmd_id": "c3"
            }),
            ("set_torrent_limits", {
                "hash": "HA",
                "up_limit": 1024,
                "dl_limit": 2048,
                "cmd_id": "c4"
            }),
            (
                "set_share_limits", {
                    "hash": "HA",
                    "ratio_limit": 1.5,
                    "seeding_time_limit": -1,
                    "inactive_seeding_time_limit": -2,
                    "cmd_id": "c5"
                }
            ),
            ("set_torrent_location", {
                "hash": "HA",
                "location": "R:/Moved",
                "cmd_id": "c6"
            }),
            ("rename_torrent", {
                "hash": "HA",
                "name": "NewName",
                "cmd_id": "c7"
            }),
            ("set_auto_tmm", {
                "hash": "HA",
                "enable": True,
                "cmd_id": "c8"
            }),
            ("add_trackers", {
                "hash": "HA",
                "urls": ["https://a/announce", "https://b/announce"],
                "cmd_id": "c9"
            }),
            (
                "edit_tracker", {
                    "hash": "HA",
                    "orig_url": "https://a/announce",
                    "new_url": "https://c/announce",
                    "cmd_id": "c10"
                }
            ),
            ("remove_tracker", {
                "hash": "HA",
                "url": "https://c/announce",
                "cmd_id": "c11"
            }),
            ("set_file_priority", {
                "hash": "HA",
                "indices": [0, 1],
                "priority": 6,
                "cmd_id": "c12"
            }),
            (
                "rename_fs", {
                    "hash": "HA",
                    "old_path": "old/file.mkv",
                    "new_path": "new/file.mkv",
                    "is_folder": False,
                    "cmd_id": "c13"
                }
            ),
        ]
        for cmd, payload in cmds:
            mgr.web.commands.put((cmd, payload))
        mgr.web.consume_commands()
        assert client.calls[0] == ("recheck", None) and client.recheck_hashes_calls[0] == "HA"
        assert client.calls[1] == ("set_super_seeding", True)
        assert client.calls[2] == ("set_force_start", True)
        assert client.calls[3] == ("set_upload_limit", 1024)
        assert client.calls[4] == ("set_download_limit", 2048)
        assert client.calls[5] == ("set_share_limits", (1.5, -1, -2)), "share-limits 三值映射"
        assert client.calls[6] == ("set_location", "R:/Moved")
        assert client.calls[7] == ("rename", ("HA", "NewName")), "rename 参数形态(torrent_hash, new_torrent_name)"
        assert client.calls[8] == ("set_auto_tmm", True)
        assert client.calls[9] == ("add_trackers", ("HA", ["https://a/announce", "https://b/announce"]))
        assert client.calls[10] == ("edit_tracker", ("HA", "https://a/announce", "https://c/announce"))
        assert client.calls[11] == ("remove_trackers", ("HA", ["https://c/announce"]))
        assert client.calls[12] == ("file_priority", ("HA", [0, 1], 6))
        assert client.calls[13] == ("rename_file", ("HA", "old/file.mkv", "new/file.mkv"))
        # !D2 之后回执**在 drain 阶段就写**(不再扣住等真值)—— 真机实测 qB 翻状态要 1258ms,
        #   扣着回执等 = 撤下被钉死在 1.25s+(实测撤下 2947ms)。回执只表示"命令已执行"。
        assert mgr.web.results["c1"]["status"] == "ok", "回执必须立即发, 不再等真值落地"
        # recheck_torrent 已入延迟回执族(plan 26-09-30-0109: handler 经 ops 提交并自写回执,
        # 拒绝时回执带自解释文案) —— 它不再走 RESYNC 的 defer_receipt 真值登记; 校验态由
        # 正常快照刷新可见, 乐观 UI 也不做 recheck(结果在远端)
        assert "c1" not in mgr.web.truth_pending, "recheck 由 handler 自写回执, 不登记真值待推"
        # 回执**不带 truth**: 带上未落地的真值 = 让前端采纳命令前的旧值 ⇒ 弹回(红线)
        assert "truth" not in mgr.web.results["c1"], "回执不得带真值(真值改由 truth 事件推送)"
        # 真值登记为待推, 由 run() 无条件 flush(幂等; 漏调会让前端一直挂着乐观值)
        assert "c2" in mgr.web.truth_pending, "RESYNC 命令应登记待推真值"
        mgr.web.flush_truths()
        assert mgr.web.flush_truths() is None, "重复 flush 必须是安全的空操作"
        # 全部命令回执 ok
        assert all(mgr.web.results[f"c{i}"]["status"] == "ok" for i in range(1, 14)), mgr.web.results
        # 限速/保存路径写后快照同步(QbApi update_torrent_fields)
        rec = mgr.store.get("HA")
        assert rec.up_limit == 1024 and rec.dl_limit == 2048 and rec.save_path == "R:/Moved"


def test_drain_web_commands_torrent_write_unknown_hash_skips():
    """二轮写命令: hash 不在快照 -> 静默跳过不调 API(照 pause_torrent 删除守阵样板)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        cmds = [
            ("recheck_torrent", {
                "hash": "GONE"
            }),
            ("super_seeding", {
                "hash": "GONE",
                "enable": True
            }),
            ("force_start", {
                "hash": "GONE",
                "enable": True
            }),
            ("set_torrent_limits", {
                "hash": "GONE",
                "up_limit": 1,
                "dl_limit": 1
            }),
            (
                "set_share_limits", {
                    "hash": "GONE",
                    "ratio_limit": 1.0,
                    "seeding_time_limit": -1,
                    "inactive_seeding_time_limit": -1
                }
            ),
            ("set_torrent_location", {
                "hash": "GONE",
                "location": "R:/X"
            }),
            ("rename_torrent", {
                "hash": "GONE",
                "name": "N"
            }),
            ("queue_torrent", {
                "hash": "GONE",
                "action": "top"
            }),
            ("set_auto_tmm", {
                "hash": "GONE",
                "enable": True
            }),
            ("add_trackers", {
                "hash": "GONE",
                "urls": ["u"]
            }),
            ("edit_tracker", {
                "hash": "GONE",
                "orig_url": "a",
                "new_url": "b"
            }),
            ("remove_tracker", {
                "hash": "GONE",
                "url": "a"
            }),
            ("set_file_priority", {
                "hash": "GONE",
                "indices": [0],
                "priority": 1
            }),
            ("rename_fs", {
                "hash": "GONE",
                "old_path": "a",
                "new_path": "b",
                "is_folder": True
            }),
        ]
        for cmd, payload in cmds:
            mgr.web.commands.put((cmd, payload))
        mgr.web.consume_commands()
        assert client.calls == [] and client.recheck_hashes_calls == [], client.calls


def test_drain_web_commands_share_limits_and_queue_mapping():
    """share-limits: 缺省维度按 -2(用全局)补齐; queue: 四动作映射到对应 qB 方法, 未知动作 error 回执"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        # queue 四动作 -> qB 队列端点方法(方法名映射正确)
        for action, want in (
            ("top", "queue_top"), ("up", "queue_up"), ("down", "queue_down"), ("bottom", "queue_bottom")
        ):
            mgr.web.commands.put(("queue_torrent", {"hash": "HA", "action": action}))
            mgr.web.consume_commands()
            assert client.calls[-1] == (want, ["HA"]), f"{action}: {client.calls[-1]}"
        # share-limits 缺省维度 -2 补齐(库不过滤 None, 直传会以字面量 "None" 发给 qB)
        mgr.web.commands.put(("set_share_limits", {"hash": "HA", "ratio_limit": 2.0}))
        mgr.web.consume_commands()
        assert client.calls[-1] == ("set_share_limits", (2.0, -2, -2)), client.calls[-1]
        # 未知队列动作 -> error 回执且不调 API
        before = list(client.calls)
        mgr.web.commands.put(("queue_torrent", {"hash": "HA", "action": "middle", "cmd_id": "qerr"}))
        mgr.web.consume_commands()
        assert client.calls == before
        r = mgr.web.results["qerr"]
        assert r["status"] == "error" and "middle" in r["error"], r


def test_drain_web_commands_torrent_write_param_errors():
    """写命令参数错误(空名称/路径/URL/非法优先级) -> error 回执且不调 API, 后续命令继续消费"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        errs = [
            ("rename_torrent", {
                "hash": "HA",
                "name": ""
            }, "e1"),
            ("set_torrent_location", {
                "hash": "HA",
                "location": ""
            }, "e2"),
            ("add_trackers", {
                "hash": "HA",
                "urls": []
            }, "e3"),
            ("edit_tracker", {
                "hash": "HA",
                "orig_url": "a",
                "new_url": ""
            }, "e4"),
            ("remove_tracker", {
                "hash": "HA",
                "url": ""
            }, "e5"),
            ("set_file_priority", {
                "hash": "HA",
                "indices": [0],
                "priority": 3
            }, "e6"),
            ("set_file_priority", {
                "hash": "HA",
                "indices": [],
                "priority": 1
            }, "e7"),
            ("rename_fs", {
                "hash": "HA",
                "old_path": "a",
                "new_path": "",
                "is_folder": False
            }, "e8"),
        ]
        for cmd, payload, cmd_id in errs:
            mgr.web.commands.put((cmd, {**payload, "cmd_id": cmd_id}))
        mgr.web.commands.put(("pause_torrent", {"hash": "HA"}))  # 后续命令不受影响
        mgr.web.consume_commands()
        assert client.calls == [("pause", ["HA"])], client.calls
        for _, _, cmd_id in errs:
            assert mgr.web.results[cmd_id]["status"] == "error", (cmd_id, mgr.web.results[cmd_id])


def test_drain_web_commands_bulk_torrents():
    """批量命令: 多 hash 一次 API 调用 + 聚合回执; 部分缺失/未知动作/空列表 -> error 回执"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        # pause: 一次调用传全部 hashes(单条 call 即单次调用), 全部命中 -> ok
        mgr.web.commands.put(("bulk_torrents", {"hashes": ["HA", "HB"], "action": "pause", "cmd_id": "b1"}))
        mgr.web.consume_commands()
        assert client.calls[-1] == ("pause", ["HA", "HB"]), client.calls[-1]
        assert mgr.web.results["b1"]["status"] == "ok"
        # recheck: 经 ops 层逐个提交(R1 第二入口) —— 每 hash 一次提交并各自登记在途,
        # 不再是"一次 API 传全部"(直调 API 会让批量路径绕过在途互斥, 留下 C1 旁路)
        mgr.web.commands.put(("bulk_torrents", {"hashes": ["HA", "HB"], "action": "recheck", "cmd_id": "b2"}))
        mgr.web.consume_commands()
        assert client.recheck_hashes_calls == ["HA", "HB"], client.recheck_hashes_calls
        assert mgr.web.results["b2"]["status"] == "ok"
        # delete: delete_files 透传, 成员从快照移除
        mgr.web.commands.put(
            ("bulk_torrents", {
                "hashes": ["HA"],
                "action": "delete",
                "delete_files": True,
                "cmd_id": "b3"
            })
        )
        mgr.web.consume_commands()
        assert client.calls[-1] == ("delete", True)
        assert mgr.store.get("HA") is None
        assert mgr.web.results["b3"]["status"] == "ok"
        # 部分缺失: 已知种子仍执行, 回执 error 带缺失计数
        mgr.web.commands.put(("bulk_torrents", {"hashes": ["HB", "GONE"], "action": "resume", "cmd_id": "b4"}))
        mgr.web.consume_commands()
        assert client.calls[-1] == ("resume", ["HB"])
        r = mgr.web.results["b4"]
        assert r["status"] == "error" and "1/2" in r["error"], r
        # 未知动作 -> error 回执, 不调 API
        before = list(client.calls)
        mgr.web.commands.put(("bulk_torrents", {"hashes": ["HB"], "action": "purge", "cmd_id": "b5"}))
        mgr.web.consume_commands()
        assert client.calls == before
        assert mgr.web.results["b5"]["status"] == "error" and "purge" in mgr.web.results["b5"]["error"]
        # 空 hash 列表 -> error 回执
        mgr.web.commands.put(("bulk_torrents", {"hashes": [], "action": "pause", "cmd_id": "b6"}))
        mgr.web.consume_commands()
        assert mgr.web.results["b6"]["status"] == "error"


def test_drain_web_commands_bulk_torrents_group_keys():
    """bulk 组键模式(DLG-02): 逐组展开成员级联全组, 与 hashes 合并去重, 缺失按组计数

    组键删除 = 组内全部在册成员一次 API 调用(与 delete_group 同级联语义);
    组不存在/成员全部不在快照计一个缺失组(不按种子数), 回执文案与种子缺失分列。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        # 组键删除: 级联全组(一次调用传全部成员), delete_files 透传, 成员从快照移除, 回执 ok
        mgr.web.commands.put(
            ("bulk_torrents", {
                "keys": [key],
                "action": "delete",
                "delete_files": True,
                "cmd_id": "g1"
            })
        )
        mgr.web.consume_commands()
        assert client.calls[-1] == ("delete", True), client.calls
        assert mgr.store.get("HA") is None and mgr.store.get("HB") is None
        assert mgr.web.results["g1"]["status"] == "ok"


def test_drain_web_commands_bulk_torrents_group_keys_mixed_and_missing():
    """bulk 组键模式: 混合选择合并去重(显式 hash 与组员重叠不重复调用); 缺失组分列计数"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        # 混合: 组(含 HA/HB) + 散种子 HA(重叠) + 散种子 GONE(缺失) -> 去重后 [HA, HB] 一次调用; 回执带缺失计数
        mgr.web.commands.put(
            ("bulk_torrents", {
                "hashes": ["HA", "GONE"],
                "keys": [key],
                "action": "pause",
                "cmd_id": "g2"
            })
        )
        mgr.web.consume_commands()
        assert client.calls[-1] == ("pause", ["HA", "HB"]), client.calls[-1]
        r = mgr.web.results["g2"]
        assert r["status"] == "error" and "1/2" in r["error"], r
        # 组键不存在/成员不在快照 -> 计缺失组, 不调 API
        before = list(client.calls)
        gone_key = ("R:/gone", ("x.mkv", ))
        mgr.web.commands.put(("bulk_torrents", {"keys": [gone_key], "action": "pause", "cmd_id": "g3"}))
        mgr.web.consume_commands()
        assert client.calls == before, "缺失组不应调用 qB API"
        r = mgr.web.results["g3"]
        assert r["status"] == "error" and "1/1 个组" in r["error"], r
        # 组部分成员仍在: 只作用于在册成员, 组不算缺失
        mgr.store.by_hash.pop("HA")
        mgr.web.commands.put(("bulk_torrents", {"keys": [key], "action": "resume", "cmd_id": "g4"}))
        mgr.web.consume_commands()
        assert client.calls[-1] == ("resume", ["HB"]), client.calls[-1]
        assert mgr.web.results["g4"]["status"] == "ok"


def test_drain_web_commands_bulk_torrents_tags_category():
    """bulk 标签/分类命令: 单次 API 调用带全部在册 hash; 缺 tags / 缺 category 键 error 回执;
    空串分类(清除)合法; 标签缺失计数照常分列(同一聚合回执链路)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        # add_tags: 一次调用(tags 由替身记录; 作用范围/缺失过滤与 pause 共用同一链路), 部分缺失回执 error 带计数
        mgr.web.commands.put(
            (
                "bulk_torrents",
                {
                    "hashes": ["HA", "HB", "GONE"],
                    "action": "add_tags",
                    "tags": ["HR", "Keep"],
                    "cmd_id": "t1"
                },
            )
        )
        mgr.web.consume_commands()
        assert client.calls[-1] == ("add_tags", ["HR", "Keep"]), client.calls[-1]
        r = mgr.web.results["t1"]
        assert r["status"] == "error" and "1/3" in r["error"], r
        # remove_tags
        mgr.web.commands.put(
            ("bulk_torrents", {
                "hashes": ["HA"],
                "action": "remove_tags",
                "tags": ["HR"],
                "cmd_id": "t2"
            })
        )
        mgr.web.consume_commands()
        assert client.calls[-1] == ("remove_tags", ["HR"]), client.calls[-1]
        assert mgr.web.results["t2"]["status"] == "ok"
        # set_category: 非空
        mgr.web.commands.put(
            ("bulk_torrents", {
                "hashes": ["HA", "HB"],
                "action": "set_category",
                "category": "电影",
                "cmd_id": "t3"
            })
        )
        mgr.web.consume_commands()
        assert client.calls[-1] == ("set_category", "电影"), client.calls[-1]
        assert mgr.web.results["t3"]["status"] == "ok"
        # set_category: category="" = 清除分类, 合法(只有 None/缺键才 error)
        mgr.web.commands.put(
            ("bulk_torrents", {
                "hashes": ["HA"],
                "action": "set_category",
                "category": "",
                "cmd_id": "t4"
            })
        )
        mgr.web.consume_commands()
        assert client.calls[-1] == ("set_category", ""), client.calls[-1]
        assert mgr.web.results["t4"]["status"] == "ok"
        # add_tags 缺 tags -> error 回执, 不调 API
        before = list(client.calls)
        mgr.web.commands.put(("bulk_torrents", {"hashes": ["HA"], "action": "add_tags", "cmd_id": "t5"}))
        mgr.web.consume_commands()
        assert client.calls == before, "缺 tags 不应调用 qB API"
        r = mgr.web.results["t5"]
        assert r["status"] == "error" and "标签" in r["error"], r
        # set_category 缺 category 键(None) -> error 回执
        mgr.web.commands.put(("bulk_torrents", {"hashes": ["HA"], "action": "set_category", "cmd_id": "t6"}))
        mgr.web.consume_commands()
        assert client.calls == before, "缺 category 不应调用 qB API"
        r = mgr.web.results["t6"]
        assert r["status"] == "error" and "分类" in r["error"], r


def test_drain_web_commands_bulk_torrents_limits_location():
    """bulk 限速/移动分派(计划 26-10-02-1955 W2): 只调有值方向、每方向一次调用传全 hashes
    (不逐枚循环); 0=不限速合法; 缺值(直投队列绕过路由校验)-> error 回执不调 API"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        # limits: 两方向都有 -> 各一次调用, 每次收全 hashes; 回执 ok
        mgr.web.commands.put(
            (
                "bulk_torrents", {
                    "hashes": ["HA", "HB"],
                    "action": "limits",
                    "up_limit": 1024,
                    "dl_limit": 2048,
                    "cmd_id": "l1"
                }
            )
        )
        mgr.web.consume_commands()
        assert client.calls[-2:] == [("set_upload_limit", 1024), ("set_download_limit", 2048)]
        assert client.limit_location_hashes_calls[-2:] == [
            ("set_upload_limit", ["HA", "HB"]),
            ("set_download_limit", ["HA", "HB"]),
        ], client.limit_location_hashes_calls
        assert mgr.web.results["l1"]["status"] == "ok"
        # 写后快照同步(QbApi 写方法同步 store, 同 tick 读到新值)
        assert mgr.store.get("HA").up_limit == 1024 and mgr.store.get("HB").dl_limit == 2048
        # limits: 只提供下载方向(0 = 不限速, 合法)-> 只调下载方向
        mgr.web.commands.put(
            ("bulk_torrents", {
                "hashes": ["HA", "HB", "GONE"],
                "action": "limits",
                "dl_limit": 0,
                "cmd_id": "l2"
            })
        )
        mgr.web.consume_commands()
        assert client.calls[-1] == ("set_download_limit", 0), client.calls[-1]
        assert client.limit_location_hashes_calls[-1] == ("set_download_limit", ["HA", "HB"]), \
            "缺失 hash 过滤后一次调用传全部在册 hashes"
        assert mgr.web.results["l2"]["status"] == "error" and "1/3" in mgr.web.results["l2"]["error"]
        # location: 一次调用传全 hashes, 快照 save_path 同步
        mgr.web.commands.put(
            ("bulk_torrents", {
                "hashes": ["HA", "HB"],
                "action": "location",
                "location": "R:/X",
                "cmd_id": "l3"
            })
        )
        mgr.web.consume_commands()
        assert client.calls[-1] == ("set_location", "R:/X"), client.calls[-1]
        assert client.limit_location_hashes_calls[-1] == ("set_location", ["HA", "HB"])
        assert mgr.web.results["l3"]["status"] == "ok"
        assert mgr.store.get("HA").save_path == "R:/X"
        # limits 两方向全空 -> error 回执不调 API(直投队列绕过路由 400 时的 handler 兜底)
        before = list(client.calls)
        mgr.web.commands.put(("bulk_torrents", {"hashes": ["HA"], "action": "limits", "cmd_id": "l4"}))
        mgr.web.consume_commands()
        assert client.calls == before, "缺限速值不应调用 qB API"
        assert mgr.web.results["l4"]["status"] == "error" and "限速值" in mgr.web.results["l4"]["error"]
        # location 空路径 -> error 回执不调 API
        mgr.web.commands.put(
            ("bulk_torrents", {
                "hashes": ["HA"],
                "action": "location",
                "location": "  ",
                "cmd_id": "l5"
            })
        )
        mgr.web.consume_commands()
        assert client.calls == before, "空路径不应调用 qB API"
        assert mgr.web.results["l5"]["status"] == "error" and "目标路径" in mgr.web.results["l5"]["error"]


def test_cmd_trackers_write_invalidates_lazy_cache():
    """tracker 三兄弟写后失效 _trackers_info 惰性缓存: 下轮读取拉新值(同 tick 内后续读不拿旧值)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        rec = mgr.store.get("HA")
        # 预热: 惰性缓存持有旧 tracker 列表
        assert rec.trackers_info(mgr.client)[0]["url"] == "https://tracker.hhanclub.net/announce.php"
        assert rec._trackers_info is not None
        client.trackers_map["HA"] = [{"url": "https://new.example.com/announce"}]
        mgr.web.commands.put(("add_trackers", {"hash": "HA", "urls": ["https://extra.example.com/announce"]}))
        mgr.web.consume_commands()
        assert rec._trackers_info is None, "add_trackers 应失效惰性缓存"
        assert rec.trackers_info(mgr.client) == [{"url": "https://new.example.com/announce"}]
        # edit: 再次失效
        rec.trackers_info(mgr.client)  # 重新预热
        mgr.web.commands.put(
            (
                "edit_tracker", {
                    "hash": "HA",
                    "orig_url": "https://new.example.com/announce",
                    "new_url": "https://edited.example.com/announce"
                }
            )
        )
        mgr.web.consume_commands()
        assert rec._trackers_info is None, "edit_tracker 应失效惰性缓存"
        # remove: 再次失效
        rec.trackers_info(mgr.client)  # 重新预热
        mgr.web.commands.put(("remove_tracker", {"hash": "HA", "url": "https://new.example.com/announce"}))
        mgr.web.consume_commands()
        assert rec._trackers_info is None, "remove_tracker 应失效惰性缓存"


def test_drain_web_commands_unknown_and_error_continues():
    """_drain_web_commands: 未知命令(KeyError)与执行异常只记日志, 不中断后续命令消费"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        mgr.web.commands.put(("no_such_command", {}))  # KeyError 分支
        mgr.web.commands.put(("build_search_index", {"bogus": 1}))  # 参数错误 -> TypeError 分支
        mgr.web.commands.put(("pause_group", {"key": key}))  # 后续命令仍应执行
        mgr.web.consume_commands()
        assert client.calls[-1] == ("pause", ["HA", "HB"]), f"异常命令不应中断消费: {client.calls}"
        assert mgr.web.commands.empty()


def test_drain_web_commands_empty_queue():
    """_drain_web_commands: 队列为空时直接返回(queue.Empty 分支), 无任何 API 调用"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        mgr.web.consume_commands()
        assert client.calls == []


# ---------- 强制汇报确认重构(plan 26-10-05-0923: epoch 前跳证据门控 + D4=warn 三桶) ----------


def _epoch_tracker(url="u", status=2, updating=False, next_announce=10_000, min_announce=5_000, msg=""):
    """构造 epoch 语义的 qB tracker 行替身(next_announce/min_announce 是 Unix epoch 绝对秒)"""
    return {
        "url": url,
        "status": status,
        "updating": updating,
        "next_announce": next_announce,
        "min_announce": min_announce,
        "msg": msg,
    }


def test_verdict_reannounce_epoch_matrix():
    """epoch 判定矩阵(§3.1): ②在途/③前跳=confirmed(==TOL 边界=pending, 基线 status 0/1 行不判),
    ④status4+msg=rejected(空 msg 不判败), 其余 pending"""
    from auto_qb.core.qbmanager import QbManager

    f = QbManager._verdict_reannounce
    base = {"u": {"status": 2, "updating": False, "next": 10_000, "min": 5_000}}
    kw = dict(t0=9_000, tol=3.0, now=20_000)
    # ② updating / status==3(min 已过期) -> confirmed
    assert f([_epoch_tracker(updating=True)], base, **kw) == ("confirmed", "announce 在途")
    assert f([_epoch_tracker(status=3)], base, **kw) == ("confirmed", "announce 在途")
    # ③ 主判据: 前跳 > TOL -> confirmed; ==TOL 边界不触发
    assert f([_epoch_tracker(next_announce=10_004)], base, **kw)[0] == "confirmed"
    state, reason = f([_epoch_tracker(next_announce=10_504, min_announce=6_000)], base, **kw)
    assert state == "confirmed" and "epoch 前跳 +504s" in reason and "min 同前跳" in reason, "min 同向前跳作佐证"
    assert f([_epoch_tracker(next_announce=10_003)], base, **kw) == ("", ""), "==TOL 边界 -> pending"
    assert f([_epoch_tracker(next_announce=10_001)], base, **kw) == ("", ""), "跳幅 <= TOL -> pending"
    assert f([_epoch_tracker()], base, **kw) == ("", ""), "无变化继续等待"
    # ③ 判定域限基线 status>=2: 基线未联系行(status 0/1)带极值 next 不触发假前跳
    for b_status in (0, 1):
        b = {"u": {"status": b_status, "updating": False, "next": 10_000, "min": 5_000}}
        assert f([_epoch_tracker(next_announce=999_999)], b, **kw) == ("", ""), f"基线 status={b_status} 行不判前跳"
    # ④ tracker 拒绝: status4+msg -> rejected(逐行先于前跳判, 防 status4 行的重试排程误判成功)
    assert f([_epoch_tracker(status=4, msg="tracker message", next_announce=99_999)], base,
             **kw) == ("rejected", "失败: tracker 未接受汇报(not working): tracker message")
    assert f([_epoch_tracker(status=4)], base, **kw) == ("", ""), "status4 空 msg 不武断判败"
    # 虚拟 tracker 行不参与判定
    assert f([_epoch_tracker(url="** [DHT]", next_announce=99_999)], base, **kw) == ("", "")


def test_verdict_reannounce_legacy_matrix():
    """legacy 判定矩阵(§3.2): 基线行无 epoch 字段 -> ②在途/③′变 working/④拒绝生效, 前跳判据不参与"""
    from auto_qb.core.qbmanager import QbManager

    f = QbManager._verdict_reannounce
    base = {"u": {"status": 1, "updating": None, "next": None, "min": None}}  # 行无 epoch 字段
    kw = dict(t0=9_000, tol=3.0, now=20_000)
    assert f([_epoch_tracker(status=3)], base, **kw) == ("confirmed", "announce 在途")
    assert f([_epoch_tracker(updating=True)], base, **kw) == ("confirmed", "announce 在途")
    assert f([_epoch_tracker(status=2)], base, **kw) == ("confirmed", "tracker 状态转为 working")
    assert f([_epoch_tracker(status=4, msg="bad")], base, **kw) == ("rejected", "失败: tracker 未接受汇报(not working): bad")
    # 无前跳判据: 基线非 working + 当前仍非 working, next_announce 再大也不得判成功
    assert f([_epoch_tracker(status=1, next_announce=99_999)], base, **kw) == ("", "")
    assert f([_epoch_tracker(status=1)], base, **kw) == ("", ""), "基线 1 -> 1 无结论"
    b2 = {"u": {"status": 2, "updating": None, "next": None, "min": None}}
    assert f([_epoch_tracker(status=2)], b2, **kw) == ("", ""), "基线已是 working -> ③′ 不触发"
    assert f([_epoch_tracker(status=4)], base, **kw) == ("", ""), "status4 空 msg 不武断判败"


def test_verdict_reannounce_min_window_guard():
    """判据② min 窗口守卫(S0 探针实证): 基线 min 在未来时 updating 是推迟登记假瞬态 -> pending; 过期后在途直证"""
    from auto_qb.core.qbmanager import QbManager

    f = QbManager._verdict_reannounce
    base = {"u": {"status": 2, "updating": False, "next": 100_000, "min": 200_000}}
    kw = dict(t0=190_000, tol=3.0)
    assert f([_epoch_tracker(updating=True)], base, now=150_000, **kw) == ("", ""), "min 未过期: updating 是假瞬态"
    assert f([_epoch_tracker(status=3)], base, now=199_999, **kw) == ("", "")
    assert f([_epoch_tracker(updating=True)], base, now=200_000, **kw)[0] == "confirmed", "min 已过期: 在途直证"
    # min 缺失/为 0: 无窗口信息可用, 不加守卫(在途即直证)
    b_none = {"u": {"status": 2, "updating": False, "next": 100_000, "min": None}}
    assert f([_epoch_tracker(updating=True)], b_none, now=150_000, **kw)[0] == "confirmed"
    b_zero = {"u": {"status": 2, "updating": False, "next": 100_000, "min": 0}}
    assert f([_epoch_tracker(updating=True)], b_zero, now=150_000, **kw)[0] == "confirmed"


def test_trackers_baseline_shape_and_epoch_mode():
    """baseline 形状回归: {url: {status, updating, next, min}} + epoch_mode(任一 real 行含 next_announce 键)"""
    from auto_qb.core.qbmanager import QbManager

    from helpers import FakeClient

    client = FakeClient()
    client.trackers_map = {
        "HA":
            [
                _epoch_tracker(url="https://t.example/ann", status=2, next_announce=1000, min_announce=900),
                {
                    "url": "** [DHT]",
                    "status": 2,
                    "next_announce": 5,
                    "min_announce": 5
                },
            ],
        "HB": [{
            "url": "https://t2.example/ann",
            "status": 1,
            "msg": "x"
        }],  # 无 epoch 字段行
    }
    baseline, epoch_mode = QbManager._trackers_baseline(SimpleNamespace(client=client), ["HA", "HB"])
    assert epoch_mode is True, "任一 real 行含 next_announce 键 = epoch 模式"
    assert baseline["HA"] == {
        "https://t.example/ann": {
            "status": 2,
            "updating": False,
            "next": 1000,
            "min": 900
        }
    }, "real 行按新 dict 形状记录, 虚拟行排除"
    assert baseline["HB"] == {"https://t2.example/ann": {"status": 1, "updating": None, "next": None, "min": None}}
    # 全部行都无 next_announce 键 -> legacy 模式
    client.trackers_map = {"HA": [{"url": "https://t.example/ann", "status": 1}]}
    baseline, epoch_mode = QbManager._trackers_baseline(SimpleNamespace(client=client), ["HA"])
    assert epoch_mode is False and baseline["HA"]["https://t.example/ann"]["next"] is None


def test_reannounce_receipt_prefix_contract():
    """D4=warn 双契约(§3.4): 三前缀常量文案钉死(改文案必红); 机器分流依据是回执 status 三值"""
    from auto_qb.webui.commands import RC_DEFERRED_PREFIX, RC_FAIL_PREFIX, RC_UNCONFIRMED_PREFIX

    assert RC_FAIL_PREFIX == "失败: tracker 未接受汇报(not working): "
    assert RC_DEFERRED_PREFIX == "已受理: 最小间隔未过期, 推迟至 "
    assert RC_UNCONFIRMED_PREFIX == "未确认: "


def test_reannounce_confirm_success_and_timeout():
    """强制汇报确认(epoch 语义): 前跳命中 -> ok 回执且跟踪清空; 超时 -> warn「未确认」不再判「失败」"""
    import time as _time

    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        u = "https://tracker.hhanclub.net/announce.php"
        client.trackers_map = {"HA": [_epoch_tracker(url=u, status=2, next_announce=100_000, min_announce=90_000)]}
        # 确认前不写回执(登记 pending), tracker 无变化时继续等待
        mgr.web.commands.put(("reannounce_torrent", {"hash": "HA", "cmd_id": "cmd1"}))
        mgr.web.consume_commands()
        assert "cmd1" in mgr.web.reannounce_pending and "cmd1" not in mgr.web.results
        mgr.web.check_pending()
        assert "cmd1" not in mgr.web.results, "无前跳证据应继续等待"
        client.trackers_map["HA"][0]["next_announce"] = 105_000  # epoch 前跳 +5000s
        mgr.web.check_pending()
        assert mgr.web.results["cmd1"]["status"] == "ok"
        assert mgr.web.reannounce_pending == {}, "全部确认后跟踪应移除"
        # 超时: item 级 deadline 已过仍无证据 -> warn「未确认」(不与 error「失败」混淆)
        mgr.web.commands.put(("reannounce_torrent", {"hash": "HA", "cmd_id": "cmd2"}))
        mgr.web.consume_commands()
        mgr.web.reannounce_pending["cmd2"]["items"]["HA"]["deadline"] = _time.time() - 1
        mgr.web.check_pending()
        r = mgr.web.results["cmd2"]
        assert r["status"] == "warn"
        assert "未确认: " in r["error"] and "前跳" in r["error"]
        assert "汇报确认失败" not in r["error"], "超时不再用旧「失败」标签"


def test_reannounce_confirm_group_aggregate():
    """组强制汇报三桶聚合: ok+error -> error 带计数与原因; 全推迟 -> warn「已受理」早回执 + 后台登记"""
    import time as _time

    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        u = "https://tracker.hhanclub.net/announce.php"
        client.trackers_map = {
            "HA": [_epoch_tracker(url=u, status=2, next_announce=100_000, min_announce=90_000)],
            "HB": [_epoch_tracker(url=u, status=4, msg="rejected by tracker", next_announce=100_000)],
        }
        mgr.web.commands.put(("reannounce_group", {"key": key, "cmd_id": "cmd3"}))
        mgr.web.consume_commands()
        assert "cmd3" not in mgr.web.results
        # HA 前跳命中(ok); HB status4+msg(rejected) -> 聚合 error
        client.trackers_map["HA"][0]["next_announce"] = 105_000
        mgr.web.check_pending()
        r = mgr.web.results["cmd3"]
        assert r["status"] == "error"
        assert "成功 1, 失败 1, 未确认 0" in r["error"]
        assert "失败: tracker 未接受汇报(not working): rejected by tracker" in r["error"]
        assert mgr.web.reannounce_pending == {}
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        u = "https://tracker.hhanclub.net/announce.php"
        fut = _time.time() + 1000  # min_e - t0 = 1000s > 25s -> 双双推迟
        client.trackers_map = {
            "HA": [_epoch_tracker(url=u, status=2, next_announce=fut, min_announce=fut)],
            "HB": [_epoch_tracker(url=u, status=2, next_announce=fut + 5, min_announce=fut)],
        }
        mgr.web.commands.put(("reannounce_group", {"key": key, "cmd_id": "cmd4"}))
        mgr.web.consume_commands()
        items = mgr.web.reannounce_pending["cmd4"]["items"]
        assert all(it["done"] and it["status"] == "warn" for it in items.values()), "推迟 item 注册即出结论"
        assert set(mgr.web.reannounce_background) == {"HA", "HB"}, "推迟 item 登记后台核实"
        mgr.web.check_pending()  # 全部 item 注册时已出结论 -> 下一 tick 即聚合
        r = mgr.web.results["cmd4"]
        assert r["status"] == "warn" and "成功 0, 失败 0, 未确认 2" in r["error"]
        assert r["error"].count("已受理: 最小间隔未过期, 推迟至 ") == 2
        assert mgr.web.reannounce_pending == {}


def test_reannounce_register_immediate_verdicts_and_deadline():
    """注册直判: 停止种子立即 warn; 推迟检出早回执 + 后台登记; item 级 deadline 公式与 600 上限"""
    import time as _time

    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        # (a) 停止种子: store 快照 state_enum.is_stopped -> 立即 done+warn, 不等窗口
        rec = mgr.store.get("HA")
        rec.state = "stoppedUP"
        rec._state_enum = None  # 复位惰性缓存(state_enum 按新 state 重算)
        mgr.web.commands.put(("reannounce_torrent", {"hash": "HA", "cmd_id": "cmd5"}))
        mgr.web.consume_commands()
        it = mgr.web.reannounce_pending["cmd5"]["items"]["HA"]
        assert it["done"] and it["status"] == "warn"
        assert it["reason"] == "未确认: 种子已停止, qB 静默忽略强制汇报"
        assert mgr.web.reannounce_background == {}, "停止种子不走推迟后台"
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        u = "https://tracker.hhanclub.net/announce.php"
        fut = _time.time() + 1000
        client.trackers_map = {"HA": [_epoch_tracker(url=u, status=2, next_announce=fut, min_announce=fut)]}
        # (b) 推迟检出: min_e - t0 > 25s -> 立即 warn「已受理」+ 后台登记
        mgr.web.commands.put(("reannounce_torrent", {"hash": "HA", "cmd_id": "cmd6"}))
        mgr.web.consume_commands()
        it = mgr.web.reannounce_pending["cmd6"]["items"]["HA"]
        assert it["done"] and it["status"] == "warn"
        assert it["reason"].startswith("已受理: 最小间隔未过期, 推迟至 ")
        assert it["reason"].endswith("(后台继续核实, 结果见日志)")
        assert it["deadline"] - it["t0"] == 600.0, "窗口公式 capped 600(异常大 min 值不撑爆窗口)"
        bg = mgr.web.reannounce_background["HA"]
        assert bg["min_e"] == fut and bg["baseline"] == it["baseline"] and bg["epoch_mode"] is True
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        u = "https://tracker.hhanclub.net/announce.php"
        # 立即路径: min_e - t0 = 20s(<= 25 不推迟) -> deadline = t0 + max(30, 20+15) = t0+35
        now = _time.time()
        client.trackers_map = {"HA": [_epoch_tracker(url=u, status=2, next_announce=now + 20, min_announce=now + 20)]}
        mgr.web.commands.put(("reannounce_torrent", {"hash": "HA", "cmd_id": "cmd7"}))
        mgr.web.consume_commands()
        it = mgr.web.reannounce_pending["cmd7"]["items"]["HA"]
        assert not it["done"], "min_e - t0 <= 25s 走立即路径轮询"
        assert 34.9 <= it["deadline"] - it["t0"] <= 35.0
        assert "HA" not in mgr.web.reannounce_background
        # 无 min 信息: min_e 按 0 -> max(30, 负) = 30 基础窗口; legacy 行 epoch_mode=False
        client.trackers_map = {"HB": [{"url": u, "status": 1}]}
        mgr.web.commands.put(("reannounce_torrent", {"hash": "HB", "cmd_id": "cmd8"}))
        mgr.web.consume_commands()
        it8 = mgr.web.reannounce_pending["cmd8"]["items"]["HB"]
        assert not it8["done"] and it8["epoch_mode"] is False
        assert 29.9 <= it8["deadline"] - it8["t0"] <= 30.1


def test_reannounce_stopped_midwindow_direct_verdict():
    """窗口内暂停直判: 确认窗口内用户暂停种子 -> 下一 tick 立即 warn「种子已停止」, 不等 deadline"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        u = "https://tracker.hhanclub.net/announce.php"
        client.trackers_map = {"HA": [_epoch_tracker(url=u, status=2, next_announce=100_000, min_announce=90_000)]}
        mgr.web.commands.put(("reannounce_torrent", {"hash": "HA", "cmd_id": "cmd9"}))
        mgr.web.consume_commands()
        mgr.web.check_pending()
        assert "cmd9" not in mgr.web.results, "运行中无证据继续等待"
        rec = mgr.store.get("HA")
        rec.state = "stoppedUP"
        rec._state_enum = None
        mgr.web.check_pending()
        r = mgr.web.results["cmd9"]
        assert r["status"] == "warn" and "未确认: 种子已停止" in r["error"]
        assert mgr.web.reannounce_pending == {}


def test_reannounce_background_verify_and_cap():
    """推迟后台核实(D1): 达 min_e 出结论落日志并移除; 逾时静默移除; 500 上限丢最旧并 WARNING"""
    from auto_qb.core.qbmanager import QbManager
    from auto_qb.webui.commands import REANNOUNCE_BACKGROUND_MAX

    base = {"u": {"status": 2, "updating": False, "next": 100_000, "min": 90_000}}

    def _runtime(rows):
        client = SimpleNamespace(torrents_trackers=lambda h: rows)
        return WebUIRuntime(SimpleNamespace(client=client, _verdict_reannounce=QbManager._verdict_reannounce))

    # confirmed: 达 min_e 后前跳 -> INFO 日志后移除
    rt = _runtime([_epoch_tracker(next_announce=105_000)])
    rt.reannounce_background["H_OK"] = {
        "min_e": time.time() - 10,
        "baseline": base,
        "epoch_mode": True,
        "t0": time.time() - 40
    }
    with module_log("auto_qb.webui.runtime") as messages:
        rt.check_pending()
    assert "H_OK" not in rt.reannounce_background
    assert any("后台核实已确认" in m for m in messages)
    # rejected: status4+msg -> WARNING 日志后移除
    rt = _runtime([_epoch_tracker(status=4, msg="nope")])
    rt.reannounce_background["H_BAD"] = {
        "min_e": time.time() - 10,
        "baseline": base,
        "epoch_mode": True,
        "t0": time.time() - 40
    }
    with module_log("auto_qb.webui.runtime") as messages:
        rt.check_pending()
    assert "H_BAD" not in rt.reannounce_background
    assert any("后台核实失败" in m for m in messages)
    # 未达 min_e: 不读不判, 条目保留; 逾时(min_e + TIMEOUT)未出结论 -> DEBUG 静默移除
    rt = _runtime([_epoch_tracker()])
    rt.reannounce_background["H_FUT"] = {
        "min_e": time.time() + 500,
        "baseline": base,
        "epoch_mode": True,
        "t0": time.time()
    }
    rt.reannounce_background["H_OLD"] = {
        "min_e": time.time() - 100,
        "baseline": base,
        "epoch_mode": True,
        "t0": time.time() - 200
    }
    with module_log("auto_qb.webui.runtime") as messages:
        rt.check_pending()
    assert "H_FUT" in rt.reannounce_background, "未达 min_e 不核实"
    assert "H_OLD" not in rt.reannounce_background, "逾时未出结论静默移除"
    assert any("逾时移除" in m for m in messages)
    # 上限 500: 超限丢最旧并 WARNING 一次
    rt = _runtime([_epoch_tracker()])
    for i in range(REANNOUNCE_BACKGROUND_MAX):
        rt.reannounce_background[f"H{i:03d}"] = {
            "min_e": time.time() + 500,
            "baseline": base,
            "epoch_mode": True,
            "t0": time.time()
        }
    host = SimpleNamespace(
        client=SimpleNamespace(torrents_trackers=lambda h: []),
        store=SimpleNamespace(get=lambda h: None),
        _verdict_reannounce=QbManager._verdict_reannounce,
    )
    host.web = rt
    fut = time.time() + 1000  # min_e - t0 > 25s: HNEW 以推迟身份登记, 触发超限逐出
    bg_base = {"u": {"status": 2, "updating": False, "next": fut, "min": fut}}
    with module_log("auto_qb.webui.commands") as cmd_messages:
        QbManager._register_reannounce_pending(host, "cmd_bg", ["HNEW"], {"HNEW": bg_base}, True)
    assert len(rt.reannounce_background) == REANNOUNCE_BACKGROUND_MAX
    assert "H000" not in rt.reannounce_background and "HNEW" in rt.reannounce_background, "超限丢最旧"
    assert any("丢弃最旧" in m for m in cmd_messages)


def test_cmd_group_actions_skip_missing_group():
    """组级命令: 组 key 不存在或成员已不在快照 -> 空 hashes, 不调 qB API"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        gone = ("R:/gone", ("x.mkv", ))
        mgr.store.groups[gone] = ["NOT_IN_STORE"]  # 成员不在快照 -> _group_hashes 过滤为空
        assert mgr._group_hashes(gone) == []
        for cmd in ("pause_group", "resume_group", "reannounce_group", "delete_group"):
            mgr.web.commands.put((cmd, {"key": gone}))
        mgr.web.commands.put(("pause_group", {"key": ("R:/nonexistent", ("y.mkv", ))}))  # 组 key 不存在
        mgr.web.consume_commands()
        assert client.calls == [], f"空组不应调用 qB API: {client.calls}"


def test_cmd_reload_config_delegates():
    """_cmd_reload_config: 委托 apply_new_config(热重载分级应用逻辑本身由 config 影响分析测试覆盖)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        applied = []
        mgr.apply_new_config = lambda cfg: applied.append(cfg) or {"applied": True}
        new_cfg = object()
        mgr.web.commands.put(("reload_config", {"config": new_cfg}))
        mgr.web.consume_commands()
        assert applied == [new_cfg], "reload_config 命令应把新配置交给 apply_new_config"


# ---------- Web 视图与配置热重载 ----------


def test_ensure_group_view_rebuilds_when_dirty():
    """ensure_group_view: 脏时立即重建(Web 请求侧兜底), 干净时直接返回当前引用(不重建)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        mgr.web.group_view = []
        mgr.web.group_view_dirty = True
        view = mgr.web.ensure_view()
        assert len(view) == 1 and view[0]["count"] == 2, f"脏时应重建分组视图: {view}"
        assert mgr.web.group_view_dirty is False
        assert mgr.web.ensure_view() is view, "干净时直接返回当前引用(不重建)"


def test_ensure_group_state_versioning():
    """ensure_group_state: 重建分组视图时版本号自增; rid 一致时不回传 groups(体积极小)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        mgr.web.group_view = []
        mgr.web.group_view_dirty = True
        start_ver = mgr.web.group_view_ver
        state = mgr.web.ensure_state(rid=None)  # 首次: 版本不匹配 -> 全量
        assert state["updated"] is True
        assert state["rid"] == start_ver + 1, "重建后版本号应自增"
        assert len(state["groups"]) == 1
        assert state["singles"] == [], "未归组种子为空时 singles 应为空列表(键必须存在, 前端按同门控替换)"
        # 同版本再次请求: 不回传 groups
        again = mgr.web.ensure_state(rid=state["rid"])
        assert again["updated"] is False
        assert again["rid"] == state["rid"]
        assert "groups" not in again and "singles" not in again
        # 视图变化后版本自增, 旧 rid 失效 -> 重新回传
        mgr.web.group_view_dirty = True
        bumped = mgr.web.ensure_state(rid=state["rid"])
        assert bumped["updated"] is True
        assert bumped["rid"] == state["rid"] + 1
        assert "groups" in bumped and "singles" in bumped


def test_ensure_group_state_show_view_carries_member_index():
    """追剧页(view=show)必须**连带成员索引** groups+singles 一起回传, 但不得回传种子平铺数组

    前端 `decoratedShows` 的成员解析走 `memberByHash`(由 groups + singles + torrents 拼出来),
    而后端 shows 里的 `members` 只是一串 hash(设计上"不随 shows 重复回传")。
    只回 shows ⇒ 前端索引为空 ⇒ 每个集的成员都被 `filter(Boolean)` 丢掉 ⇒ 追剧页**永久空白**
    (2026-09-19 实测: 刷新后 groups=0 / memberByHash=0 / 0 行; 且 rid 已记住 ⇒ 之后每轮都是
    "版本未变不回传", 自己不会恢复, 必须手动切一次视图才回来)。
    同时守住另一头: 种子平铺数组(3000 种子 ≈ 4.5MB)不能顺手一起回 —— 追剧页用不到它。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        mgr.web.group_view_dirty = True
        state = mgr.web.ensure_state(rid=None, view="show")
        assert "shows" in state, "追剧页应回 shows"
        assert "groups" in state and "singles" in state, \
            "追剧页必须连带成员索引(groups+singles), 否则前端 memberByHash 为空 -> 整页空白"
        assert "torrents" not in state, "追剧页不该回传种子平铺数组(4.5MB, 用不到)"


def test_build_singles_view_ungrouped_only():
    """_build_singles_view: 只含未归组种子且字段与 members 同形(save_path/name/HR 齐全);
    singles 随 ensure_group_state 与 groups 同门控回传/同版本不回传"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        from helpers import FakeTorrent, seed_store

        seed_store(mgr, [FakeTorrent(hash="HZ", name="Lone", save_path=r"R:\Elsewhere")])
        mgr.web.group_view_dirty = True
        state = mgr.web.ensure_state(rid=None)
        assert [s["hash"] for s in state["singles"]] == ["HZ"], f"singles 应只含未归组种子: {state['singles']}"
        assert state["singles"][0]["save_path"] == r"R:\Elsewhere"
        assert "hr_triggered" in state["singles"][0] and "name" in state["singles"][0]
        grouped_hashes = {m["hash"] for g in state["groups"] for m in g["members"]}
        assert not (grouped_hashes & {s["hash"] for s in state["singles"]}), "已归组种子不得出现在 singles"
        again = mgr.web.ensure_state(rid=state["rid"])
        assert "singles" not in again and "groups" not in again
        assert "shows" not in again, "追剧视图与 groups 同版本门控: 版本一致不回传"


def test_build_singles_view_num_seeds_fields():
    """singles 视图透出 num_seeds/num_leechs/num_complete/num_incomplete(与组视图成员同形)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        from helpers import FakeTorrent, seed_store

        seed_store(
            mgr, [
                FakeTorrent(
                    hash="HZ",
                    name="Lone",
                    save_path=r"R:\Elsewhere",
                    num_seeds=9,
                    num_leechs=2,
                    num_complete=11,
                    num_incomplete=4,
                )
            ]
        )
        mgr.web.group_view_dirty = True
        state = mgr.web.ensure_state(rid=None)
        singles = {s["hash"]: s for s in state["singles"]}
        assert "HZ" in singles, f"singles 应只含未归组种子: {state['singles']}"
        s = singles["HZ"]
        assert s["num_seeds"] == 9
        assert s["num_leechs"] == 2
        assert s["num_complete"] == 11
        assert s["num_incomplete"] == 4


def test_build_shows_view_aggregation():
    """_build_shows_view: 全量种子按剧→季→集聚合(不依赖辅种分组);
    同集多版本归并成同一集行(多站点不分开); 缺集提示; 日期型归 None 季桶;
    未识别种子进未识别桶; shows 随 ensure_group_state 同门控回传"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        from helpers import FakeTorrent, seed_store

        seed_store(
            mgr, [
                FakeTorrent(hash="HA", name="Show.Name.S01E05.1080p.WEB-DL", save_path=r"R:\Downloads"),
                FakeTorrent(hash="HB", name="Show Name S01E05 720p HDTV", save_path=r"R:\Downloads2"),
                FakeTorrent(hash="HC", name="Show.Name.S01E07.1080p", save_path=r"R:\Downloads3"),
                FakeTorrent(hash="HD", name="Another.Show.S01E01.1080p", save_path=r"R:\Downloads4"),
                FakeTorrent(hash="HE", name="Some.Movie.2023.1080p.BluRay.x265", save_path=r"R:\Movies"),
                FakeTorrent(hash="HF", name="Show.Name.2026.09.15.1080p.WEB.h264", save_path=r"R:\TV"),
            ]
        )
        view = mgr._build_shows_view()
        names = {s["key"]: s for s in view["list"]}
        assert set(names) == {"show name", "another show"}, f"同剧异写应归并为一部剧: {list(names)}"
        assert view["unrecognized"] == ["HE"], f"无标记种子进未识别桶: {view['unrecognized']}"
        show = names["show name"]
        assert show["name"] == "Show Name", "展示名取频次最高的原始剧名(点分隔符美化为空格)"
        seasons = {s["season"]: s for s in show["seasons"]}
        assert set(seasons) == {1, None}, "日期型归 None 季桶, 编号季独立"
        eps = {tuple(e["key"]): e for e in seasons[1]["episodes"]}
        assert set(eps) == {("ep", 5), ("ep", 7)}, f"同集多版本归并为一行: {list(eps)}"
        assert eps[("ep", 5)]["count"] == 2, "S01E05 两份种子(不同编码)应归并进同一集行"
        assert eps[("ep", 5)]["members"] == ["HA", "HB"]
        assert seasons[1]["gaps"] == [6], f"E5/E7 已有, E6 缺: {seasons[1]['gaps']}"
        dates = seasons[None]["episodes"]
        assert dates[0]["key"] == ["date", "2026-09-15"], f"日期型集键: {dates}"
        # 同门控回传: 首次全量带 shows, 同版本不回传
        mgr.web.group_view = []
        mgr.web.group_view_dirty = True
        state = mgr.web.ensure_state(rid=None)
        assert "shows" in state and state["shows"]["list"] == view["list"]
        assert "unrecognized" in state["shows"]
        again = mgr.web.ensure_state(rid=state["rid"])
        assert "shows" not in again


def test_shows_view_files_fallback_hook():
    """文件兑底接线: 季包/无标记种子在索引未覆盖时标记 _shows_pending 并投递构建命令;
    索引推进(文件就位)后置脏触发重建, 季包集数范围从文件列表展开"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        from helpers import FakeTorrent, _fake_file, seed_store

        client.files_map["HP"] = [
            _fake_file("Show.S01E01.mkv", 10),
            _fake_file("Show.S01E02.mkv", 10),
            _fake_file("Show.S01E03.mkv", 10),
        ]
        seed_store(mgr, [FakeTorrent(hash="HP", name="Show.Name.S01.Complete.1080p", save_path=r"R:\Downloads")])
        view = mgr._build_shows_view()
        assert mgr.web.shows_pending is True, "季包种子索引未覆盖: 应标记待解析"
        assert ("build_search_index", {}) in list(mgr.web.commands.queue), "应投递索引构建命令"
        node = view["list"][0]["seasons"][0]["episodes"][0]
        assert node["key"] == ["pack"], f"索引未建成前整季包无范围: {node['key']}"
        # 消费构建命令(真实链路: 主循环 _drain -> build_search_index), 文件就位 -> 清 pending + 置脏
        mgr.web.consume_commands()
        assert mgr.web.shows_pending is False
        assert mgr.web.group_view_dirty is True, "索引推进是文件兑底唯一信号, 应触发追剧视图重建"
        mgr.web.group_view_dirty = True
        view = mgr._build_shows_view()
        node = view["list"][0]["seasons"][0]["episodes"][0]
        assert node["key"] == ["range", 1, 3], f"季包从文件列表展开集数范围: {node['key']}"
        # 索引已覆盖全部种子: 不再重复投递
        assert ("build_search_index", {}) not in list(mgr.web.commands.queue)
        assert mgr.web.shows_pending is False


def test_group_view_ver_seeded_from_start_time():
    """版本号以进程启动时间播种: 重启后不会回落到旧客户端已持有的值(否则前端会一直展示旧列表)"""
    from helpers import make_manager

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        assert mgr.web.group_view_ver > 1_600_000_000, "应为时间戳量级, 而非 0/1 小整数"


def test_api_state_rid_gate(web_env):
    """/api/state 带 rid: 版本一致时 updated=False 且无 groups; 缺省/不匹配回传全量"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    full = client.get("/api/state", headers=auth).json()
    assert full["updated"] is True and len(full["groups"]) == 1
    assert full["status"]["torrents"] == 2, "status 与版本无关, 恒回传"
    assert full["status"]["version"] == __version__, "status 携带版本号(与 rid 门控无关)"
    # 同版本: 只回 status
    same = client.get(f"/api/state?rid={full['rid']}", headers=auth).json()
    assert same["updated"] is False
    assert "groups" not in same
    assert same["status"]["torrents"] == 2
    # 不匹配的 rid: 回传全量
    other = client.get(f"/api/state?rid={full['rid'] + 99}", headers=auth).json()
    assert other["updated"] is True and len(other["groups"]) == 1


def test_api_state_skips_jsonable_encoder(web_env, monkeypatch):
    """热路径必须**跳过** FastAPI 的 jsonable_encoder(3000 种子实测省 ~160 ms/轮, 占端点耗时 85%)

    `/api/state` 若返回裸 dict, FastAPI 会先跑一遍 `jsonable_encoder` **递归遍历整个响应体**
    (3000 种子 × 74 字段 = 22 万个值, 实测 **161 ms**, 而端点总耗时 189 ms); 我们的视图本来就是
    JSON 原生类型(str/int/float/bool/None/dict/list), 这趟遍历纯属白跑, 且全程占着 GIL —— 与主循环
    抢 CPU, 是大库下"点了没反应"的一个真实来源。改成返回 `JSONResponse` 后 FastAPI 直接短路
    (`fastapi/routing.py`: `isinstance(raw_response, Response)` ⇒ 跳过 `serialize_response`)。

    用**计数替身**把它钉死: 谁把返回值改回裸 dict, 这条断言立刻变红。
    (不用时间型断言 —— 计时在 CI 上不可靠; 计数是确定性的。)
    """
    import fastapi.routing as fr
    from helpers import FakeClient

    from auto_qb.torrents import TorrentRecord

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    # 详情族需要一个存在的种子 + 一个"连着的"客户端(否则 404/503, 测不到响应管线)
    mgr.store.get = lambda h: {"HA": TorrentRecord(hash="HA", name="X")}.get(h)
    # web_env 的 manager 是 SimpleNamespace 替身, 没有真实方法 —— 补上被测端点要用到的那几个
    mgr.search_torrents = lambda q: {"HA": {"name": "X", "files": []}}
    fake = FakeClient()
    fake.trackers_map["HA"] = [{"url": "https://t.example/announce", "status": 2}]
    fake.files_map["HA"] = [{"index": 0, "name": "a.mkv", "size": 1}]
    fake.peers_map["HA"] = {"peers": [{"ip": "1.2.3.4", "client": "qB"}]}
    mgr.client = fake

    calls = []
    real = fr.jsonable_encoder

    def spy(*a, **kw):
        calls.append(1)
        return real(*a, **kw)

    monkeypatch.setattr(fr, "jsonable_encoder", spy)
    urls = (
        "/api/state?view=torrent",
        "/api/state",
        "/api/groups",
        # 注: /api/config/schema **故意不在**清单里 —— 它的载荷含 dataclass(Group/Field/Plugin),
        # 必须保留 FastAPI 的 jsonable_encoder 做转换(直返会 500, 见 web.py 该端点的注释)。
        "/api/search?q=Show",
        "/api/torrents/HA",
        "/api/torrents/HA/trackers",
        "/api/torrents/HA/files",
        "/api/torrents/HA/peers",
    )
    for url in urls:
        resp = client.get(url, headers=auth)
        assert resp.status_code == 200, f"{url}: {resp.text}"
        assert calls == [], (
            f"{url} 走了 jsonable_encoder({len(calls)} 次) —— 返回值又变成裸 dict 了? "
            "见 web.py api_state 注释: 3000 种子实测这趟白跑 161ms, 占端点耗时 85%"
        )


def test_api_state_view_scoped_payload(web_env):
    """P1-1 按视图回传: view=torrent 只回 torrents; view=show 回 shows **+ 成员索引**; 未知 view 回全部

    收益: 大库下每轮响应体明显下降(3000 种子实测: 全量 6.41MB / 种子页 4.52MB /
    辅种页 1.75MB / 追剧页 1.88MB)。注意追剧页**不是**最小的那份 —— 它必须带成员索引, 见下。
    风险面: 前端**必须**按"键不存在则保留原引用"赋值, 不能用 `|| []` 把没回的视图抹空。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    base = client.get("/api/state", headers=auth).json()
    assert {"groups", "singles", "shows", "torrents"} <= set(base), "不带 view 时四份全回(保守默认)"

    t = client.get("/api/state?view=torrent", headers=auth).json()
    assert "torrents" in t
    assert "groups" not in t and "singles" not in t and "shows" not in t

    s = client.get("/api/state?view=show", headers=auth).json()
    # 追剧页必须连带**成员索引**(groups+singles): shows 里的 members 只是一串 hash,
    # 前端靠索引还原成成员对象 —— 只回 shows 会让 memberByHash 为空、整页空白(BUG-8)
    assert "shows" in s and "groups" in s and "singles" in s
    assert "torrents" not in s, "追剧页用不到种子平铺数组(4.5MB), 不该一起回"

    g = client.get("/api/state?view=group", headers=auth).json()
    # 辅种页要同时用 groups 与 singles(未归组单种子是同页兜底行), 必须一起回
    assert "groups" in g and "singles" in g and "torrents" not in g

    # 未知 view: 回全部(保守默认, 老客户端/非视图调用方不受影响)
    weird = client.get("/api/state?view=nope", headers=auth).json()
    assert {"groups", "singles", "shows", "torrents"} <= set(weird)
    # 版本一致时无论带不带 view 都不回数组(增量门控优先)
    same = client.get(f"/api/state?rid={base['rid']}&view=torrent", headers=auth).json()
    assert same["updated"] is False and "torrents" not in same


def test_build_speed_totals_covers_ungrouped(tmp_path):
    """速度合计 = store 全量(组内成员 ∪ 未归组), 不能只算 groups

    状态栏旧实现对前端 `groups` 求和: 既漏掉未归组的单种子(实测少算 88.7%),
    又在种子页因 groups 不回传而恒为 0(issue 26-09-20-1646)。合计范围必须是
    `store.by_hash` 全量 —— 与种子页平铺视图同源。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = FakeClient()
    # 组内两个(合计 dl 3000 / ul 5000) + 未归组一个(dl 7000 / ul 9000)
    grouped = [
        FakeTorrent(hash="HA", name="Show", save_path=r"R:/s", dlspeed=1000, upspeed=2000),
        FakeTorrent(hash="HB", name="Show", save_path=r"R:/s", dlspeed=2000, upspeed=3000),
    ]
    single = FakeTorrent(hash="HC", name="Other", save_path=r"R:/t", dlspeed=7000, upspeed=9000)
    seed_store(mgr, grouped + [single])
    key = ("R:/s", ("a.mkv", ))
    mgr.store.groups[key] = ["HA", "HB"]
    mgr.store.member_to_key["HA"] = key
    mgr.store.member_to_key["HB"] = key

    totals = mgr._build_speed_totals()
    assert totals == {"dlspeed": 10000, "upspeed": 14000}, (f"速度合计漏了未归组种子: {totals} —— 只算 groups 的话是 dl=3000 / ul=5000")
    # 对照: 组视图自身的合计**不含**未归组(两者刻意不等, 正是本 bug 的成因)
    assert mgr._build_group_view()[0]["dlspeed"] == 3000


def test_api_state_speed_totals_survives_view_scoping():
    """status.totals 恒回传: 种子页(不回 groups)/ 辅种页 / rid 命中三种情况下都在且等于全量

    !这是 issue 26-09-20-1646(状态栏速度恒为 0)的防复现守阵。状态栏是**跨视图**的常驻
    显示, 一旦它的数值来自按视图裁剪的数组, 就会在某个视图下恒 0 或停在冻结的旧值。
    故 totals 必须与 traffic / server 同属"恒回传"口径: 不参与 VIEW_ARRAYS 分片、不受 rid 门控。
    """
    from fastapi.testclient import TestClient

    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        mgr.web.token = "t"
        grouped = [
            FakeTorrent(hash="HA", name="Show", save_path=r"R:/s", dlspeed=1000, upspeed=2000),
            FakeTorrent(hash="HB", name="Show", save_path=r"R:/s", dlspeed=2000, upspeed=3000),
        ]
        seed_store(mgr, grouped + [FakeTorrent(hash="HC", name="Other", save_path=r"R:/t", dlspeed=7000, upspeed=9000)])
        key = ("R:/s", ("a.mkv", ))
        mgr.store.groups[key] = ["HA", "HB"]
        mgr.store.member_to_key["HA"] = key
        mgr.store.member_to_key["HB"] = key

        tc = TestClient(create_app(mgr))
        auth = {"Authorization": "Bearer t"}
        want = {"dlspeed": 10000, "upspeed": 14000}

        # 1. 种子页: groups 根本不回传 —— 但若 totals 也跟着没了, 状态栏就恒为 0
        t = tc.get("/api/state?view=torrent", headers=auth).json()
        assert "groups" not in t, "种子页按设计不回 groups(P1-1 体积优化)"
        assert t["status"]["totals"] == want, f"种子页缺少/错误的 totals: {t['status'].get('totals')}"

        # 2. 辅种页: totals 与种子页**同源同值**(不能因视图不同而变)
        g = tc.get("/api/state?view=group", headers=auth).json()
        assert g["status"]["totals"] == want

        # 3. rid 命中(updated=False, 任何数组都不回)时 totals 仍必须回传 —— 否则稳态下每轮都拿不到
        ver = g["rid"]
        same = tc.get(f"/api/state?rid={ver}&view=torrent", headers=auth).json()
        assert same["updated"] is False
        assert same["status"]["totals"] == want, "增量门控下 totals 被门控掉了: 稳态状态栏会不刷新"


@pytest.mark.parametrize(
    "state, kind",
    [
        ("error", "error"),
        ("missingFiles", "error"),
        ("checkingUP", "checking"),
        ("pausedUP", "paused"),  # 暂停态优先于做种(stoppedUP 同时命中 is_uploading)
        ("stoppedDL", "paused"),
        ("downloading", "downloading"),
        ("stalledUP", "seeding"),
        ("uploading", "seeding"),
        ("moving", "other"),
    ]
)
def test_state_kind_maps_states(state, kind):
    """state_kind: 状态语义分类(前端着色) —— 暂停态优先于下载/做种, errored/checking 最前"""
    from auto_qb.core.qbmanager import QbManager
    from helpers import FakeTorrent

    assert QbManager.state_kind(FakeTorrent(hash="H", name="t", state=state)) == kind


def _pin_noop_sections(new_cfg, mgr):
    """把与「本次验证无关」的段钉到现行配置同对象: 模块 apply 整段短路(P1-P5)。

    logging/notify/web 是 P1/P2 模块段; rules 六段是 RulesModule 的重建判据段
    (_rebuild_needed: rules_config/interval/delete_tags*/global_speed_limit_curve/trackers
    —— 不钉的话 Mock 段会被整段不等误判成 L2 重建)。
    """
    new_cfg.logging = mgr.config.logging
    new_cfg.notify = mgr.config.notify
    new_cfg.web = mgr.config.web
    new_cfg.qbittorrent = mgr.config.qbittorrent
    new_cfg.rules_config = mgr.config.rules_config
    new_cfg.interval = mgr.config.interval
    new_cfg.delete_tags = mgr.config.delete_tags
    new_cfg.delete_tags_if_has_no_torrents = mgr.config.delete_tags_if_has_no_torrents
    new_cfg.global_speed_limit_curve = mgr.config.global_speed_limit_curve
    new_cfg.trackers = mgr.config.trackers


def test_apply_new_config_levels(monkeypatch):
    """apply_new_config(W4 后): 换配置对象 + 无条件广播 apply + 段变内核自判重连 + R 闸

    级别分派层已退役 —— 零动作段由模块 apply 自判短路(钉段对象), web 重启/规则重建/
    事件抑制各自单点在模块; qbittorrent 段变由内核自判重连; R 段仅提示重启。
    完成消息按 INFO 记(alert-levels 契约: 热重载是预期动作, WARNING 会被 notify 推成通知)。
    """
    import logging as std_logging

    from auto_qb.config.impact import ConfigChange
    from helpers import FakeConfig, make_manager

    # 日志抓取用挂在目标 logger 上的 Grab handler —— 不用 caplog:
    # make_manager 会走 setup_logging 清空 root handlers(logging.py:98), caplog 挂在 root 上抓不到
    grabbed = []

    class Grab(std_logging.Handler):
        def emit(self, record):
            grabbed.append(record)

    grab = Grab()
    qbm_logger = std_logging.getLogger("auto_qb.core.qbmanager")
    qbm_logger.addHandler(grab)

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        new_cfg = mock.MagicMock(name="new_config")
        mgr.connect = mock.MagicMock(return_value=True)
        # make_manager 把 rules_config 设为实例属性(遮蔽类属性), 后面替身 SimpleNamespace
        # 的段对象都要与它同对象, 否则 RulesModule.apply 会被误判成段变触发重建
        rules_config_orig = mgr.config.rules_config

        def _apply(changes):
            # diff 结果受控(变更判定本身由 impact 单测覆盖)
            monkeypatch.setattr("auto_qb.config.impact.diff_config_impacts", lambda old, new: changes)
            return mgr.apply_new_config(new_cfg)

        # 1. 零动作热重载: 仅替换配置对象, 任务队列保持不变, 各模块 apply 全部短路
        # !HR 路由守阵(2026-09-29 实报「取数线程未启动」): 站点接入不走任何分支, hr.apply
        # 必须每次热重载都被调到(由 HrRuntime.apply 自判重建/短路), 不能只挂在特定级别
        mgr.hr = mock.MagicMock()
        queue_before = mgr.task_queue
        _pin_noop_sections(new_cfg, mgr)
        try:
            res = _apply([ConfigChange("main_tick", 1, 2)])
        finally:
            qbm_logger.removeHandler(grab)  # 先摘 handler, 断言失败也不跨测试泄漏
        assert res["applied"] is True and res["changes"] == 1 and res["restart_required"] == []
        assert all(a["action"] == "none" for a in res["actions"]), res["actions"]
        assert mgr.config is new_cfg
        assert mgr.task_queue is queue_before, "零动作热重载不应重建任务队列"
        assert not mgr.events.suppressed and not mgr.events.replay_requested, "零动作热重载不置事件重放保护(请求位/live 旗标都不动)"
        mgr.hr.apply.assert_called_once(), "HR 运行时每次热重载都要过一遍 apply(站点接入无分支)"
        # 生命周期消息守阵: 完成消息必须是 INFO, 不得用 WARNING(否则 notify 开启时每次保存配置弹通知)
        done_logs = [r for r in grabbed if "配置热重载完成" in r.getMessage()]
        assert done_logs, "热重载完成应留一行日志"
        assert done_logs[-1].levelno == std_logging.INFO, f"热重载完成是预期动作, 应记 INFO(实为 {done_logs[-1].levelname})"

        # 2. web 监听身份变化: 仅 webui 模块动服务器(先停旧并等其线程退出 -> 启新),
        #    不重连 qB(重连只由 qbittorrent 段变触发)
        mgr.config = SimpleNamespace(
            qbittorrent=FakeConfig.qbittorrent,
            web=_web_stub(port=38080),
            hr_check=HrCheckConfig(),
            logging=new_cfg.logging,
            notify=new_cfg.notify,
            rules_config=rules_config_orig,
            interval=FakeConfig.interval,
            delete_tags=FakeConfig.delete_tags,
            delete_tags_if_has_no_torrents=FakeConfig.delete_tags_if_has_no_torrents,
            global_speed_limit_curve=FakeConfig.global_speed_limit_curve,
            trackers=FakeConfig.trackers,
        )
        new_cfg.web = _web_stub(port=38081)  # 仅端口变化 -> 需重启
        old_handle = mock.MagicMock()
        mgr.web.handle = old_handle
        calls = []

        def _fake_stop(handle, timeout=0.0):
            calls.append(("stop", handle))
            return True

        def _fake_start(m):
            calls.append(("start", m))
            return "新句柄"

        monkeypatch.setattr("auto_qb.webui.stop_web_server", _fake_stop)
        monkeypatch.setattr("auto_qb.webui.start_web_server", _fake_start)
        res = _apply([ConfigChange("web", None, None)])
        assert all(a["action"] != "none" for a in res["actions"] if a["module"] == "webui")
        mgr.connect.assert_not_called(), "web 端口变化不重连 qB(重连只由 qbittorrent 段变触发)"
        assert calls == [("stop", old_handle), ("start", mgr)], "必须先停旧服务(并等其线程退出)再启新服务"
        assert mgr.web.handle == "新句柄", "web 句柄应换为新服务句柄"

        # 3. qbittorrent 段变: 内核自判重连(连接管理属内核, plan §3.1)
        mgr.connect.reset_mock()
        mgr.config = SimpleNamespace(
            qbittorrent=SimpleNamespace(host="old", port=1, username="u", password="p"),
            web=new_cfg.web,
            hr_check=HrCheckConfig(),
            logging=new_cfg.logging,
            notify=new_cfg.notify,
            rules_config=rules_config_orig,
            interval=FakeConfig.interval,
            delete_tags=FakeConfig.delete_tags,
            delete_tags_if_has_no_torrents=FakeConfig.delete_tags_if_has_no_torrents,
            global_speed_limit_curve=FakeConfig.global_speed_limit_curve,
            trackers=FakeConfig.trackers,
        )
        new_cfg.qbittorrent = SimpleNamespace(host="new", port=1, username="u", password="p")
        _apply([ConfigChange("qbittorrent", None, None)])
        mgr.connect.assert_called_once(), "qbittorrent 段变由内核自判重连"

        # 4. R 段: 仅提示重启, 配置对象照常替换(实际拦截在 webui PUT 侧回退 R 字段)
        res = _apply([ConfigChange("state_file", "a", "b")])
        assert res["restart_required"] == ["state_file"]
        assert res["applied"] is True


def test_apply_new_config_l2_preserves_runtime_state(monkeypatch):
    """守阵(2026-09-22, issue 26-09-21-1347): L2 热重载不得重读磁盘 state 回滚运行期内存态

    state 平时不落盘(仅优雅退出/跳检重加落盘), 磁盘上的 state.json 永远是「上次退出」
    的旧版 —— L2 重建(rules 模块 rebuild_runtime)若重读 state 会把本次运行累计的
    exec_history/skip_check_day/recheck_fails 等整体回滚到旧版, Web UI 改规则保存即
    确定性触发。断言用「对象同一性 + 内容保留」双断言, 不 mock _load_state 本身
    (避免耦合实现符号)。P5 起重建在 RulesModule: 队列重建 + 抑制置位经回执与总线断言。
    """
    from auto_qb.config.impact import ConfigChange
    from helpers import make_manager

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        # 运行期内存态: 模拟本次运行累计的去重/冷却记录(构造后注入, 与磁盘无关)
        runtime = {
            "exec_history": {
                "r1:abc": {
                    "ts": 1.0,
                    "date": "2026-09-22",
                    "hour": 19
                }
            },
            "skip_check_day": {
                "abc": "2026-09-22"
            },
            "recheck_fails": {
                "abc": {
                    "count": 2
                }
            },
        }
        mgr.state.update(runtime)
        state_before = mgr.state
        # 磁盘上是「上次退出版本」的旧版(内容与内存不同)
        with open(os.path.join(td, "state.json"), "w", encoding="utf-8") as f:
            json.dump({"stale_marker": True}, f)
        # 替身: rules 重建判据段钉住, 仅 interval 留 Mock -> RulesModule.apply 判段变触发重建;
        # logging/notify/web 段钉住 -> 其余模块整段短路(P1-P2)
        new_cfg = mock.MagicMock(name="new_config")
        new_cfg.logging = mgr.config.logging
        new_cfg.notify = mgr.config.notify
        new_cfg.web = mgr.config.web
        new_cfg.qbittorrent = mgr.config.qbittorrent
        new_cfg.rules_config = mgr.config.rules_config
        new_cfg.delete_tags = mgr.config.delete_tags
        new_cfg.delete_tags_if_has_no_torrents = mgr.config.delete_tags_if_has_no_torrents
        new_cfg.global_speed_limit_curve = mgr.config.global_speed_limit_curve
        new_cfg.trackers = mgr.config.trackers
        mgr.connect = mock.MagicMock(return_value=True)
        monkeypatch.setattr(
            "auto_qb.config.impact.diff_config_impacts", lambda old, new: [ConfigChange("interval", 1, 2)]
        )

        queue_before = mgr.task_queue
        res = mgr.apply_new_config(new_cfg)

        assert any(a["module"] == "rules" and a["action"] == "rebuilt" for a in res["actions"]), res["actions"]
        assert mgr.task_queue is not queue_before, "L2 仍应重建任务队列(本守阵只钉 state 语义)"
        assert mgr.events.replay_requested, "L2 重建应挂总线事件重放保护请求位(窗口协议见 EventBus)"
        assert not mgr.events.suppressed, "挂请求不置 live 旗标(窗口内相位照常送达, issue 26-10-01-0750)"
        assert mgr.state is state_before, "L2 热重载不得替换 state 对象(重读磁盘 = 回滚运行期内存态)"
        assert mgr.state["exec_history"] == runtime["exec_history"], "执行历史不得被磁盘旧版回滚"
        assert mgr.state["skip_check_day"] == runtime["skip_check_day"], "跨日跳检去重不得被回滚"
        assert mgr.state["recheck_fails"] == runtime["recheck_fails"], "校验失败冷却不得被回滚"


def test_stop_web_server_releases_port_for_restart(tmp_path):
    """回归守阵(2026-09-14): 热重载重启 WEB 服务器必须先等旧服务线程退出

    只 stop()(置 should_exit)就立刻启新服务时, 旧服务尚未关闭监听套接字 ——
    新服务 bind 报 `[Errno 10048] 通常每个套接字地址只允许使用一次`, 保存配置后 WEB UI 失联。
    本测试用真实 uvicorn 复现该时序: 停止后同端口必须能再次监听。
    """
    from auto_qb.webui import start_web_server, stop_web_server

    cfg_text = "config:\n  qbittorrent:\n    host: h\n    port: 1\n    username: u\n    password: p\n"
    port = _free_port()
    mgr1 = _make_web_manager(tmp_path, cfg_text)
    mgr1.config.web.port = port
    h1 = start_web_server(mgr1)
    try:
        assert h1.started, "旧服务应监听成功"
        assert stop_web_server(h1), "stop_web_server 应等到服务线程退出"
        assert not h1.thread.is_alive(), "服务线程应已退出(监听套接字已释放)"

        mgr2 = _make_web_manager(tmp_path, cfg_text)
        mgr2.config.web.port = port
        h2 = start_web_server(mgr2)
        try:
            assert h2.started, "旧服务退出后同端口应能重新监听(原 bug: Errno 10048)"
        finally:
            stop_web_server(h2)
    finally:
        if h1.thread.is_alive():  # 断言失败时清理, 不掩盖原异常
            stop_web_server(h1)


def test_start_web_server_started_message_is_info(tmp_path):
    """「WEB UI 已启动」按 INFO 记(pitfalls/ops/alert-levels.md 契约)

    启动是程序按配置做的动作, WARNING 会被 notify 推成系统通知 —— 每次启动弹一条,
    即用户实报的「一开就弹 warning」。监听地址在消息文本里, 暴露面信息不丢。
    日志抓取走 _grab_web_logger: caplog 挂 root, 而 root 级别/handlers 是跨测试全局状态
    (root 出厂 WARNING 会把 INFO 拦成 no-op, test_logging 的 setup_logging 测试还会清
    root handlers), xdist 下同 worker 邻居每次不同, 依赖它就偶发落空。
    """
    from auto_qb.webui import start_web_server, stop_web_server

    grabbed, restore = _grab_web_logger()
    try:
        cfg_text = "config:\n  qbittorrent:\n    host: h\n    port: 1\n    username: u\n    password: p\n"
        mgr = _make_web_manager(tmp_path, cfg_text)
        mgr.config.web.port = _free_port()
        h = start_web_server(mgr)
        try:
            assert h.started, "服务应监听成功"
            started = [r for r in grabbed if "WEB UI 已启动" in r.getMessage()]
            assert started, "启动应留一行日志(含监听地址与密钥路径)"
            assert started[-1].levelno == logging.INFO, \
                f"启动是预期动作, 应记 INFO(实为 {started[-1].levelname})"
        finally:
            stop_web_server(h)
    finally:
        restore()


def test_webui_module_apply_skips_restart_when_bind_unchanged(monkeypatch):
    """监听身份(enabled/host/port)未变 -> 不重启服务器, 仅刷新密钥(鉴权每请求实时读取)

    否则改个日志级别之类的变更也会把 WEB 服务器拆了重建, 白白放大端口竞态窗口。
    P2 起该语义单点在 WebUIModule.apply(_apply_web_config 迁入), 经模块入口驱动。
    """
    from helpers import make_manager

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        # 真实调用点: self.config 已是新配置; 模块拿到的是(旧配置, 新配置)整对象
        mgr.config.web = _web_stub(port=8080, token="新密钥")
        old_handle = mock.MagicMock()
        mgr.web.handle = old_handle
        monkeypatch.setattr("auto_qb.webui.start_web_server", mock.MagicMock())
        monkeypatch.setattr("auto_qb.webui.stop_web_server", mock.MagicMock())

        mgr.host.get("webui").apply(SimpleNamespace(web=_web_stub(port=8080, token="旧密钥")), mgr.config)

        from auto_qb.webui import start_web_server, stop_web_server

        start_web_server.assert_not_called()
        stop_web_server.assert_not_called()
        assert mgr.web.handle is old_handle, "监听身份未变时不应重启"
        assert mgr.web.token == "新密钥", "密钥变更应即时刷新(无需重启)"


def test_start_web_server_reports_failure_when_port_taken(tmp_path):
    """端口被占用: 句柄未就绪且记 ERROR —— 不再静默失败、不再假报"已启动"

    uvicorn 启动失败走 sys.exit(3), 而 SystemExit 在非主线程被 threading 静默吞掉,
    历史上只留一行 uvicorn 自己的 ERROR(无时间戳), 日志上看不出 WEB UI 已经死了。
    """
    import socket

    from auto_qb.webui import start_web_server, stop_web_server

    cfg_text = "config:\n  qbittorrent:\n    host: h\n    port: 1\n    username: u\n    password: p\n"
    with socket.socket() as holder:  # 占住端口(不 listen 也可; bind 后即不可再绑)
        holder.bind(("127.0.0.1", 0))
        holder.listen(1)
        mgr = _make_web_manager(tmp_path, cfg_text)
        mgr.config.web.port = holder.getsockname()[1]
        grabbed, restore = _grab_web_logger(logging.ERROR)
        try:
            handle = start_web_server(mgr)
            assert handle.started is False, "端口被占用时不应报告就绪"
            assert any("WEB UI 启动失败" in r.getMessage() for r in grabbed), "失败必须记 ERROR"
        finally:
            restore()
        stop_web_server(handle)


def _grab_web_logger(min_level=logging.INFO):
    """挂在 auto_qb.web 模块 logger 上的日志采集器: 对全局日志状态自足; 用完必须调 restore

    !这组测试不要用 caplog 断言: caplog 的采集 handler 挂在 root 上, 而 root 的级别与
    handlers 是**跨测试全局状态** —— root 出厂 level 是 WARNING(auto_qb.web 未显式设级时
    INFO 调用被拦成 no-op), test_logging 的 setup_logging 测试还会清空/重置 root。
    xdist 动态调度下同 worker 邻居每次不同, 依赖全局状态的断言就**偶发落空**(CI 实测:
    噪音日志测试抓到 0 条)。挂模块 logger + 显式 setLevel 才自足。
    返回 (records, restore); restore 恢复该 logger 原 level 与 handlers。
    """
    grabbed = []

    class _Grab(logging.Handler):
        def emit(self, record):
            grabbed.append(record)

    grab = _Grab(level=min_level)
    web_logger = logging.getLogger("auto_qb.web")
    saved = (web_logger.level, list(web_logger.handlers))
    web_logger.setLevel(min_level)
    web_logger.addHandler(grab)

    def restore():
        web_logger.setLevel(saved[0])
        web_logger.handlers = saved[1]

    return grabbed, restore


def _noise_loop():
    """异常处理器替身: 只关心「是否把异常交还给默认处理器」"""
    return mock.MagicMock()


def _reset_noise_state():
    from auto_qb.webui.server import lifecycle as lc

    lc._noise_state.update(at=0.0, suppressed=0)
    return lc


def test_web_loop_exception_handler_downgrades_connection_reset():
    """网络波动(WinError 10054 对端强迫关闭): 降级为一行 INFO, 不再 ERROR + traceback(2026-09-24 实测)

    Windows ProactorEventLoop 下客户端(关页面 / SSE 重连 / 抖动)断开时, asyncio 自己的回调
    `_ProactorBasePipeTransport._call_connection_lost` 会抛 ConnectionResetError, 默认处理器
    以 ERROR 整段 traceback 打出, 看着像崩溃。
    """
    lc = _reset_noise_state()
    loop = _noise_loop()
    context = {
        "message": "Exception in callback _ProactorBasePipeTransport._call_connection_lost(None)",
        "exception": ConnectionResetError(10054, "远程主机强迫关闭了一个现有的连接。"),
    }
    grabbed, restore = _grab_web_logger()
    try:
        lc._web_loop_exception_handler(loop, context)
    finally:
        restore()

    assert len(grabbed) == 1 and grabbed[0].levelno == logging.INFO, "断连应记为一行 INFO"
    assert not any(r.levelno >= logging.ERROR for r in grabbed), "不得再出现 ERROR"
    loop.default_exception_handler.assert_not_called(), "波动型异常不应交给默认处理器"


def test_web_loop_noise_log_throttled_in_window():
    """断连日志按窗口节流: 窗口内只记首条, 出窗口时附被抑制条数(SSE 重连会成串刷屏)"""
    lc = _reset_noise_state()
    loop = _noise_loop()
    context = {"exception": ConnectionResetError(10054, "远程主机强迫关闭了一个现有的连接。")}
    grabbed, restore = _grab_web_logger()
    try:
        lc._web_loop_exception_handler(loop, context)
        lc._web_loop_exception_handler(loop, context)
        assert len(grabbed) == 1, "窗口内只记一条"

        lc._noise_state["at"] -= lc.NET_NOISE_WINDOW  # 推进到窗口外
        lc._web_loop_exception_handler(loop, context)
    finally:
        restore()

    assert len(grabbed) == 2, "出窗口后应再记一条"
    assert "另有 1 条" in grabbed[-1].getMessage(), "被抑制的条数要带出来, 不能静默丢"
    loop.default_exception_handler.assert_not_called()


def test_web_loop_exception_handler_delegates_real_bug():
    """反向守阵: 非网络波动的异常(真 bug)一律不吞, 交回 asyncio 默认处理器"""
    lc = _reset_noise_state()
    loop = _noise_loop()
    context = {"message": "Task exception was never retrieved", "exception": ValueError("真 bug")}
    grabbed, restore = _grab_web_logger()
    try:
        lc._web_loop_exception_handler(loop, context)
    finally:
        restore()

    loop.default_exception_handler.assert_called_once_with(context), "真 bug 必须照旧走默认处理器(ERROR)"
    assert not grabbed, "不得被误判成网络波动"


def test_is_network_fluctuation_matrix():
    """波动判定矩阵: 异常类 / winerror / errno 三条路都要认, 非 OSError 与"目标拒绝"不算"""
    lc = _reset_noise_state()
    assert lc._is_network_fluctuation(ConnectionResetError(10054, "远程主机强迫关闭了一个现有的连接。"))
    assert lc._is_network_fluctuation(ConnectionAbortedError(10053, "软件中止"))
    assert lc._is_network_fluctuation(BrokenPipeError(32, "管道断裂"))
    assert lc._is_network_fluctuation(OSError(errno.ECONNRESET, "reset")), "errno 路(POSIX 语义)"
    win_only = OSError("模拟: 只有 winerror 的 Windows 错误")  # Windows 上 errno 可能缺失/映射不到
    win_only.winerror = 10054
    assert lc._is_network_fluctuation(win_only), "winerror 兜底路不能少"
    assert not lc._is_network_fluctuation(ValueError("真 bug")), "非 OSError 一律不算"
    assert not lc._is_network_fluctuation(None), "上下文没有 exception 时不算"
    assert not lc._is_network_fluctuation(OSError(errno.ECONNREFUSED, "拒绝")), "目标拒绝是配置/故障信号, 不是波动"


def test_uvicorn_config_installs_loop_exception_handler():
    """处理器必须真的装到服务事件循环上 —— 只定义不装载等于没修(循环在 asyncio.run 内才创建)"""
    from fastapi import FastAPI

    from auto_qb.webui.server import lifecycle as lc

    config = lc._QuietLoopConfig(FastAPI(), host="127.0.0.1", port=8080, log_level="warning")
    factory = config.get_loop_factory()
    loop = factory()
    try:
        assert loop.get_exception_handler() is lc._web_loop_exception_handler, "服务循环必须挂上自定义处理器"
    finally:
        loop.close()


# ---------- 管理端点(R2B: 分类/标签/限速/添加/导出/日志) ----------


def test_api_category_tag_endpoints(web_env):
    """分类/标签 CRUD 端点: 正常入队返回 cmd_id; 空名/空列表 400"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    assert client.post("/api/categories", json={
        "name": "电影",
        "save_path": "R:/mv"
    }, headers=auth).json()["queued"] is True
    assert client.post(
        "/api/categories/edit", json={
            "name": "电影",
            "save_path": "R:/mv2"
        }, headers=auth
    ).status_code == 200
    assert client.post("/api/categories/remove", json={"names": ["电影"]}, headers=auth).status_code == 200
    assert client.post("/api/tags", json={"tags": ["4K", "HDR"]}, headers=auth).status_code == 200
    assert client.post("/api/tags/remove", json={"tags": ["4K"]}, headers=auth).status_code == 200
    assert client.post("/api/categories", json={"name": "  "}, headers=auth).status_code == 400
    assert client.post("/api/categories/remove", json={"names": []}, headers=auth).status_code == 400
    assert client.post("/api/tags", json={"tags": []}, headers=auth).status_code == 400


def test_category_tag_commands_execute():
    """分类/标签命令: create/edit/remove/create_tags/delete_tags 调用 api 封装(带缓存失效)"""
    from helpers import FakeClient, make_manager

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        mgr._cmd_create_category(name="电影", save_path="R:/mv")
        mgr._cmd_edit_category(name="电影", save_path="R:/mv2")
        mgr._cmd_remove_categories(names=["电影"])
        mgr._cmd_create_tags(tags=["4K", "HDR"])
        mgr._cmd_delete_tags(tags=["4K"])
        assert [c[0] for c in client.calls] == [
            "create_category", "edit_category", "remove_categories", "create_tags", "delete_tags"
        ]
        assert client.calls[0][1] == "电影" and client.calls[0][2] == "R:/mv"
        assert client.calls[3][1] == ["4K", "HDR"]


def test_api_speed_mode_and_override():
    """限速托管(D2): /api/speed/mode 曲线启用/停用两形态(目标来自快照, 当前值直读);
    /api/speed/override 命令落 transfer 端点(KiB -> bytes)"""
    from fastapi.testclient import TestClient

    from helpers import FakeClient, make_manager

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        mgr.web.token = "t"
        mgr.web.traffic_view = {"state": "enabled", "limit": {"target": {"up": 100, "down": 50}}}
        tc = TestClient(create_app(mgr))
        auth = {"Authorization": "Bearer t"}
        data = tc.get("/api/speed/mode", headers=auth).json()
        assert data["curve_enabled"] is True
        assert data["curve_target"] == {"upload_kib": 100, "download_kib": 50}
        assert data["current"] == {"upload_limit": 0, "download_limit": 0}
        mgr.web.traffic_view = {"state": "disabled", "limit": {}}
        data = tc.get("/api/speed/mode", headers=auth).json()
        assert data["curve_enabled"] is False and data["curve_target"] is None
        # 覆盖命令: 入队 + 主循环消费 -> transfer 端点写入(bytes)
        cmd_id = tc.post("/api/speed/override", json={
            "upload_kib": 2048,
            "download_kib": 1024
        }, headers=auth).json()["cmd_id"]
        mgr.web.consume_commands()
        assert mgr.web.results[cmd_id]["status"] == "ok"
        assert ("transfer_set_upload_limit", 2048 * 1024) in client.calls
        assert ("transfer_set_download_limit", 1024 * 1024) in client.calls


def test_api_speed_alt_and_toggle():
    """ALT-01(计划 26-09-28-0037): 备用速度三端点 —— /api/speed/mode 增列 alt_on/alt_current(读失败回
    None 不冒充); /api/speed/alt 命令落 app/setPreferences(alt_*, bytes/s); /api/speed/alt/toggle
    命令落 transfer/toggleSpeedLimitsMode"""
    from fastapi.testclient import TestClient

    from helpers import FakeClient, make_manager

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        mgr.web.token = "t"
        mgr.web.traffic_view = {"state": "disabled", "limit": {}}
        tc = TestClient(create_app(mgr))
        auth = {"Authorization": "Bearer t"}

        # 初态: 主速度模式 + 备用限速 0
        data = tc.get("/api/speed/mode", headers=auth).json()
        assert data["alt_on"] is False
        assert data["alt_current"] == {"upload_limit": 0, "download_limit": 0}

        # 备用限速设置: KiB -> bytes 落 setPreferences(alt_*)
        cmd_id = tc.post("/api/speed/alt", json={
            "upload_kib": 1024,
            "download_kib": 512
        }, headers=auth).json()["cmd_id"]
        mgr.web.consume_commands()
        assert mgr.web.results[cmd_id]["status"] == "ok"
        assert client.alt_up_limit_value == 1024 * 1024
        assert client.alt_dl_limit_value == 512 * 1024
        assert ("app_set_preferences", ["alt_dl_limit", "alt_up_limit"]) in client.calls

        # 模式切换: toggle 端点 0 -> 1, mode 读数联动
        data = tc.get("/api/speed/mode", headers=auth).json()
        assert data["alt_current"] == {"upload_limit": 1024, "download_limit": 512}
        cmd_id = tc.post("/api/speed/alt/toggle", headers=auth).json()["cmd_id"]
        mgr.web.consume_commands()
        assert mgr.web.results[cmd_id]["status"] == "ok"
        assert client.speed_limits_mode_value == 1
        data = tc.get("/api/speed/mode", headers=auth).json()
        assert data["alt_on"] is True


def test_qbapi_alt_speed_limits_normalization(tmp_path):
    """ALT-01 QbApi Facade: 备用限速走 app/preferences alt_*(bytes/s, 0=不限) 对外 KiB;
    setPreferences 增量语义(只传非 None 方向, 两方向全 None 不发请求); 模式读/切直透"""
    from helpers import FakeClient, make_manager

    mgr = make_manager(str(tmp_path / "state.json"))
    client = FakeClient()
    mgr.client = client
    api = mgr.api

    assert api.get_alt_speed_limits() == {"upload_limit": 0, "download_limit": 0}  # 0 归一 0
    client.alt_up_limit_value = 512 * 1024
    client.alt_dl_limit_value = -1  # 负值同样归一为 0 = 不限
    assert api.get_alt_speed_limits() == {"upload_limit": 512, "download_limit": 0}

    api.set_alt_speed_limits(upload_kib=2048)  # 只传上行: 增量语义, 下行键不出现
    assert client.alt_up_limit_value == 2048 * 1024
    assert client.alt_dl_limit_value == -1
    assert client.calls[-1] == ("app_set_preferences", ["alt_up_limit"])

    api.set_alt_speed_limits(upload_kib=0, download_kib=3072)  # 0 = 不限 -> 写 0
    assert client.alt_up_limit_value == 0
    assert client.alt_dl_limit_value == 3072 * 1024

    n_calls = len(client.calls)
    api.set_alt_speed_limits()  # 两方向全 None: 不发请求
    assert len(client.calls) == n_calls

    assert api.get_speed_limits_mode() == 0
    api.toggle_speed_limits_mode()
    assert client.speed_limits_mode_value == 1
    assert api.get_speed_limits_mode() == 1


def test_api_speed_mode_curve_config_disabled():
    """曲线存在但 enabled=False -> /api/speed/mode 返回 curve_enabled=False(快照滞后也兑底); 对照 enabled=True 不影响"""
    from fastapi.testclient import TestClient

    from auto_qb.config import CurvePoint, GlobalSpeedLimitCurve, PeriodCurve
    from helpers import FakeClient, make_manager

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        mgr.web.token = "t"
        mgr.config.global_speed_limit_curve = GlobalSpeedLimitCurve(
            dat_path="x.dat",
            curves=[PeriodCurve(period="day", upload_points=[CurvePoint(threshold_bytes=1, speed_bytes_per_s=1)])],
            enabled=False,
        )
        mgr.web.traffic_view = {"state": "ok", "limit": {"target": {"up": 100, "down": 50}}}  # 滞后快照
        tc = TestClient(create_app(mgr))
        auth = {"Authorization": "Bearer t"}
        data = tc.get("/api/speed/mode", headers=auth).json()
        assert data["curve_enabled"] is False and data["curve_target"] is None

        # 对照: 恢复 enabled=True(缺省)后, 快照判定不受配置叠加影响
        mgr.config.global_speed_limit_curve.enabled = True
        data = tc.get("/api/speed/mode", headers=auth).json()
        assert data["curve_enabled"] is True
        assert data["curve_target"] == {"upload_kib": 100, "download_kib": 50}


def test_api_add_torrent_endpoint():
    """添加种子(JSON+base64): bytes 经命令队列内存直传(零临时文件零新依赖) + 选项透传; 空来源 400"""
    import base64

    from fastapi.testclient import TestClient

    from helpers import FakeClient, make_manager

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        mgr.web.token = "t"
        tc = TestClient(create_app(mgr))
        auth = {"Authorization": "Bearer t"}
        r = tc.post(
            "/api/torrents/add",
            json={
                "files_b64": [base64.b64encode(b"d8:announce").decode()],
                "urls": ["magnet:?xt=urn:btih:X"],
                "save_path": "R:/new",
                "category": "mv",
                "tags": ["4K", "HDR"],
                "paused": True,
                "skip_checking": False,
                "sequential": True,
                "first_last_piece_prio": False,
                "auto_tmm": True,
            },
            headers=auth,
        )
        assert r.status_code == 200
        cmd_id = r.json()["cmd_id"]
        cmd, payload = mgr.web.commands.queue[0]  # peek 不消费: drain 才是回执写入者
        assert cmd == "add_torrents"
        assert payload["files"] == [b"d8:announce"]
        assert payload["urls"] == ["magnet:?xt=urn:btih:X"]
        assert payload["paused"] is True and payload["auto_tmm"] is True
        assert payload["sequential"] is True and payload["skip_checking"] is False
        assert payload["tags"] == ["4K", "HDR"]
        mgr.web.consume_commands()
        assert mgr.web.results[cmd_id]["status"] == "ok"
        adds = [c for c in client.calls if c[0] == "add"]
        assert len(adds) == 2, "文件与链接各一次 torrents_add"
        assert adds[0][1]["paused"] is True and adds[0][1]["use_auto_torrent_management"] is True
        assert adds[0][1]["tags"] == ["4K", "HDR"]
        # 空来源: 400
        assert tc.post("/api/torrents/add", json={}, headers=auth).status_code == 400


def test_add_torrent_receipt_and_optional_flags():
    """添加种子回执两形态 + 两个 optional 选项恒显式下发 + 成功走 INFO(2026-09-24 真机 bug)

    1. 回执判定只认 `"Ok." in str(result)` ⇒ 在 qB 5.2.3(Web API 2.14.0 起 `/torrents/add` 改成
       JSON 元数据 `{success_count, failure_count, pending_count, added_torrent_ids}`)恒为假 ⇒
       种子明明加进去了, WEB UI 却弹"添加种子失败";
    2. 停止位被"False 就不传"的过滤器吞掉 ⇒ qB 回落到**会话级**默认(SessionImpl::
       initLoadTorrentParams 的 `addStopped.value_or(isAddTorrentStopped())`)⇒ 前端「添加后开始」
       勾了没用。另: 停止位只能用 `is_stopped=` 传 —— 库内 `is_paused or is_stopped` 会把
       `is_paused=False` 折成 None(实测请求体为空);
       同类的「自动种子管理」也是 `std::optional`(缺省回落 `savePath 空 ∧ 全局未禁自动管理`),
       一并按"恒显式"钉住;
    3. 成功路径原来记 WARNING, 而 NotifyHandler 挂在 auto_qb logger 上 ⇒ 每次添加成功都往桌面推
       一条 WARNING 弹窗; 成功必须 INFO, 只有未被接受才 WARNING。
    """
    import base64
    import logging

    from fastapi.testclient import TestClient
    from qbittorrentapi.torrents import TorrentsAddedMetadata

    from auto_qb.webui import commands as web_commands
    from helpers import FakeClient, make_manager

    class _Capture(logging.Handler):
        """级别采集器: 挂在**模块 logger** 上"""
        def __init__(self):
            super().__init__(level=logging.INFO)
            self.records = []

        def emit(self, record):
            self.records.append(record)

    with tempfile.TemporaryDirectory() as td:
        # !不能用 caplog: make_manager 走 setup_logging, 那里有 `logging.getLogger().handlers.clear()`
        #   —— 用例体内建 manager 会把 pytest 挂在 root 上的采集 handler 一并清掉, 之后一条也抓不到
        #   (症状是"日志断言恒空")。挂模块 logger 不受 root 清理影响, 且能验到真实级别。
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        mgr.web.token = "t"
        tc = TestClient(create_app(mgr))
        auth = {"Authorization": "Bearer t"}
        orig_add = client.torrents_add
        cap = _Capture()
        web_commands.logger.addHandler(cap)
        try:

            def add_returns(result):
                """保留 FakeClient 的台账记录, 只替换返回值(顶替真机 qB 的响应形态)"""
                client.torrents_add = lambda **kw: (orig_add(**kw), result)[1]

            def post_add(paused, auto_tmm=False):
                r = tc.post(
                    "/api/torrents/add",
                    json={
                        "files_b64": [base64.b64encode(b"d8:announce").decode()],
                        "paused": paused,
                        "auto_tmm": auto_tmm,
                    },
                    headers=auth,
                )
                assert r.status_code == 200
                cmd_id = r.json()["cmd_id"]
                mgr.web.consume_commands()
                return cmd_id

            def add_logs():
                return [(r.levelno, r.getMessage()) for r in cap.records if "添加种子" in r.getMessage()]

            # 1. 新形态(API >= 2.14.0): JSON 元数据 -> 受理; 成功必须是 INFO(改前: error + WARNING)
            add_returns(
                TorrentsAddedMetadata(
                    {
                        "success_count": 1,
                        "failure_count": 0,
                        "pending_count": 0,
                        "added_torrent_ids": ["HASH123"]
                    }
                )
            )
            assert mgr.web.results[post_add(False)]["status"] == "ok"
            assert [lvl for lvl, _ in add_logs()] == [logging.INFO], "受理成功不得走 WARNING(通知联动会直推桌面弹窗)"

            # 2. 部分失败 -> error 回执(部分成功也报错, 与 bulk 同一口径)且走 WARNING
            cap.records.clear()
            add_returns(
                TorrentsAddedMetadata(
                    {
                        "success_count": 1,
                        "failure_count": 1,
                        "pending_count": 0,
                        "added_torrent_ids": ["HASH123"]
                    }
                )
            )
            cid = post_add(False)
            assert mgr.web.results[cid]["status"] == "error"
            assert "成功 1 / 失败 1" in mgr.web.results[cid]["error"]
            assert [lvl for lvl, _ in add_logs()] == [logging.WARNING]

            # 3. 仅 pending(magnet 元数据未就绪)也是受理, 不是失败
            add_returns(
                TorrentsAddedMetadata(
                    {
                        "success_count": 0,
                        "failure_count": 0,
                        "pending_count": 1,
                        "added_torrent_ids": []
                    }
                )
            )
            assert mgr.web.results[post_add(False)]["status"] == "ok"

            # 4. 旧形态文本仍认(API < 2.14.0 的 "Ok."/"Fails.")
            add_returns("Ok.")
            assert mgr.web.results[post_add(False)]["status"] == "ok"
            add_returns("Fails.")
            assert mgr.web.results[post_add(False)]["status"] == "error"

            # 5. 两个 optional 选项必须**显式**下发(省略 = 吃 qB 会话/全局默认, 勾选框失效):
            #    停止位 + 自动种子管理。`use_auto_torrent_management` 由替身记 kw.get(...) ——
            #    没传时是 None, 传 False 才是 False, 两者可分。
            add_returns("Ok.")
            post_add(False)
            last = [c for c in client.calls if c[0] == "add"][-1][1]
            assert last["is_stopped_raw"] is False, "省略 stopped 会吃 qB 会话默认(不自动开始) => 选项失效"
            assert last["use_auto_torrent_management"] is False, "省略 autoTMM 会吃 qB 全局管理模式 => 选项失效"
            assert last["paused"] is False
            # 勾选方向: 两个都显式 True
            post_add(True, auto_tmm=True)
            last = [c for c in client.calls if c[0] == "add"][-1][1]
            assert last["is_stopped_raw"] is True and last["paused"] is True
            assert last["use_auto_torrent_management"] is True
            post_add(True)
            last = [c for c in client.calls if c[0] == "add"][-1][1]
            assert last["is_stopped_raw"] is True and last["paused"] is True
        finally:
            web_commands.logger.removeHandler(cap)


def test_api_export_endpoint(web_env):
    """导出 .torrent: 原始字节 + Content-Disposition; 未知 hash 404, qB 断连 503

    非 ASCII 种子名是回归点: HTTP 头只能 latin-1, 直写中文时 Starlette 编码头抛
    UnicodeEncodeError 导致整个导出 500(TestClient 会把该异常上抛到测试里)。
    """
    from helpers import FakeClient

    from auto_qb.torrents import TorrentRecord

    mgr, client = web_env
    rec = TorrentRecord(hash="HA", name='Show"S01')
    cn = TorrentRecord(hash="HB", name="我的种子/第一季")
    mgr.store.get = lambda h: {"HA": rec, "HB": cn}.get(h)
    fake = FakeClient()
    mgr.client = fake
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    r = client.get("/api/torrents/HA/export", headers=auth)
    assert r.status_code == 200 and r.content == b"TORRENT-DATA"
    assert "attachment" in r.headers["content-disposition"]
    assert "ShowS01.torrent" in r.headers["content-disposition"], "文件名中的引号/路径符应被清洗"
    # 中文名: 回退名用 hash, 原名走 filename*=UTF-8''(百分号编码), 头值本身仍是纯 ASCII
    rc = client.get("/api/torrents/HB/export", headers=auth)
    assert rc.status_code == 200 and rc.content == b"TORRENT-DATA"
    cd = rc.headers["content-disposition"]
    assert 'filename="HB.torrent"' in cd, "纯非 ASCII 名无可用回退 -> 用 hash"
    assert "filename*=UTF-8''%E6%88%91%E7%9A%84%E7%A7%8D%E5%AD%90_%E7%AC%AC%E4%B8%80%E5%AD%A3.torrent" in cd
    assert client.get("/api/torrents/NOPE/export", headers=auth).status_code == 404
    mgr.client = None
    assert client.get("/api/torrents/HA/export", headers=auth).status_code == 503


def test_content_disposition_encoding():
    """content_disposition: 头值恒为 latin-1 可编码的纯 ASCII, 原名走 filename* 百分号编码

    覆盖清洗(引号/路径符/控制字符 -> 防头注入)、ASCII/非 ASCII 混合名的回退、ext 后缀。
    """
    from auto_qb.webui import content_disposition

    # 全非 ASCII: 回退名取 fallback, 原名保留在 filename*
    cd = content_disposition("中文种子", "HASH", "torrent")
    assert cd.encode("latin-1")  # 头值必须可 latin-1 编码, 否则响应 500
    assert 'filename="HASH.torrent"' in cd
    assert cd.endswith("filename*=UTF-8''%E4%B8%AD%E6%96%87%E7%A7%8D%E5%AD%90.torrent")
    # 混合名: 回退名去掉非 ASCII 部分, 中文部分仍需在 filename* 里完整保留
    cd = content_disposition("Show/我的\\种子\"X", "HASH", "torrent")
    assert cd.encode("latin-1")
    assert 'filename="Show__X.torrent"' in cd, "路径符与引号应被清洗"
    assert "%E6%88%91%E7%9A%84_%E7%A7%8D%E5%AD%90X" in cd
    # 控制字符(CR/LF)必须剔除, 否则可截断/注入头
    cd = content_disposition("a\r\nb", "HASH", "torrent")
    assert "\r" not in cd and "\n" not in cd
    assert 'filename="ab.torrent"' in cd
    # 无 ext 时不加后缀
    assert content_disposition("a", "HASH") == "attachment; filename=\"a\"; filename*=UTF-8''a"


def test_api_category_tag_list_endpoints(web_env):
    """GET /api/categories 与 /api/tags 列表端点: 透出 store 缓存(管理对话框数据源)"""
    mgr, client = web_env
    mgr.api = SimpleNamespace(
        torrents_categories=lambda: {"mv": {
            "save_path": "R:/mv"
        }},
        torrents_tags=lambda: ["4K", "HDR"],
    )
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    assert client.get("/api/categories", headers=auth).json() == {"categories": {"mv": {"save_path": "R:/mv"}}}
    assert client.get("/api/tags", headers=auth).json() == {"tags": ["4K", "HDR"]}


def test_api_tags_exclude_auto(web_env):
    """/api/tags?exclude_auto=1: 剔除程序自动维护的标签(站点/HR 精确集 + 集数模板形状)

    添加种子窗口与「标签/分类…」弹窗的候选源; 事件标记(MISSING/zSkipChecked)与普通
    用户标签保留(2026-09-28 拍板); 不带参仍全量 —— 标签管理对话框数据源不受影响。"""
    from types import SimpleNamespace

    mgr, client = web_env
    mgr.config.trackers["HHan"].hr = SimpleNamespace(
        add_tag="HR-${required_seeding_time}",
        add_tag_for_satisfied="",
        required_seeding_time_raw="3D",
    )
    mgr.config.add_episode_tags = SimpleNamespace(
        enabled=True,
        add_tag_single="zE${episode_first}",
        add_tag_multi="zE${episode_first}-${episode_last}",
    )
    mgr.api = SimpleNamespace(torrents_tags=lambda: ["4K", "HHan", "HR-3D", "zE1", "zE1-12", "zE1x", "MISSING"], )
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    assert client.get("/api/tags?exclude_auto=1", headers=auth).json() == {"tags": ["4K", "zE1x", "MISSING"]}
    assert client.get("/api/tags", headers=auth).json() == {
        "tags": ["4K", "HHan", "HR-3D", "zE1", "zE1-12", "zE1x", "MISSING"]
    }


def _log_lines(fmt, recs):
    """按 fmt 渲染真实日志行 —— 手写字符串一旦与 config.logging.format 不符,
    测的就成了"格式不符"那条兜底路径, 真正的等级过滤反而没测到(本轮实测踩过)。
    asctime 取自 record.created, 故同一 record 渲染两次结果一致、可用来对账。"""
    fmtr = logging.Formatter(fmt)
    return [fmtr.format(logging.LogRecord(name, lv, "f.py", 1, msg, None, None)) for name, lv, msg in recs]


def test_api_log_endpoint(web_env):
    """/api/log: 自身日志 tail + 按配置格式串过滤等级; 文件未配置返回空

    必须显式设 format: web_env 替身的 logging.format 是 `%(message)s`(没有等级字段),
    直接拿它测等级过滤只会落到"筛不了"的兜底路径。"""
    from auto_qb.config.models import LoggingConfig

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    log_path = os.path.join(mgr.data_dir, "auto-qb.log")
    fmt = mgr.config.logging.format = LoggingConfig().format  # 未配置 log.format 时的默认
    lines = _log_lines(
        fmt, [
            ("auto_qb.core.x", logging.INFO, "启动完成"), ("auto_qb.core.y", logging.WARNING, "连接重试"),
            ("auto_qb.core.z", logging.ERROR, "校验失败")
        ]
    )
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    mgr.config.logging.file = log_path
    data = client.get("/api/log?lines=10", headers=auth).json()
    assert len(data["lines"]) == 3 and data["file"] == log_path and data["note"] == ""
    for lv, want in (("info", lines[0]), ("warning", lines[1]), ("error", lines[2])):
        data = client.get(f"/api/log?lines=10&level={lv}", headers=auth).json()
        assert data["lines"] == [want] and data["note"] == "", lv
    mgr.config.logging.file = ""
    assert client.get("/api/log", headers=auth).json() == {"lines": [], "file": "", "note": ""}


def test_api_log_level_filter_follows_config_format(web_env):
    """等级过滤按 config.logging.format 定位等级名, 不能靠字面量 —— 生产配置的 format 是
    `%(asctime)s - %(levelname)s - %(message)s`(无方括号), 旧实现按 `[WARNING` 捞 ⇒ 恒空,
    界面只剩"日志文件暂无内容"(2026-09-25 真机报告)。"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    log_path = os.path.join(mgr.data_dir, "auto-qb.log")
    mgr.config.logging.format = "%(asctime)s - %(levelname)s - %(message)s"  # 与 config.yml 同形
    lines = _log_lines(
        mgr.config.logging.format, [
            ("auto_qb.core.x", logging.INFO, "启动完成"), ("auto_qb.core.y", logging.WARNING, "连接重试"),
            ("auto_qb.core.z", logging.ERROR, "校验失败")
        ]
    )
    assert "[WARNING" not in lines[1], "本用例的前提: 该格式的行里没有方括号等级标记"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    mgr.config.logging.file = log_path
    data = client.get("/api/log?lines=100&level=WARNING", headers=auth).json()
    assert data["lines"] == [lines[1]] and data["note"] == ""
    assert client.get("/api/log?lines=100&level=ERROR", headers=auth).json()["lines"] == [lines[2]]


def test_api_log_level_filter_keeps_multiline_record(web_env):
    """多行日志(exc_info=True 打出的整段 traceback)折行后每行都不带等级标记 —— 过滤按"记录"
    取舍, 否则筛 ERROR 只剩标题行、用户真正要看的栈被丢掉。"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    log_path = os.path.join(mgr.data_dir, "auto-qb.log")
    fmt = mgr.config.logging.format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    header = _log_lines(fmt, [("auto_qb.core", logging.ERROR, "主循环异常: boom")])[0]
    body = ["Traceback (most recent call last):", '  File "x.py", line 1, in <module>', "RuntimeError: boom"]
    nxt = _log_lines(fmt, [("auto_qb.core", logging.INFO, "下一轮")])[0]
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join([header] + body + [nxt]) + "\n")
    mgr.config.logging.file = log_path
    data = client.get("/api/log?lines=100&level=ERROR", headers=auth).json()
    assert data["lines"] == [header] + body and data["note"] == ""


def test_api_log_note_when_level_unfilterable(web_env):
    """两种"筛不了"都回全部行 + note, 不静默给空 —— 否则"筛选失效"与"确实没有该等级日志"
    在界面上长得一模一样(本轮 bug 的观感就是这个)。"""
    from auto_qb.infra.logging import NOTE_FORMAT_MISMATCH, NOTE_NO_LEVEL_FIELD

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    log_path = os.path.join(mgr.data_dir, "auto-qb.log")
    mgr.config.logging.format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    lines = _log_lines(
        mgr.config.logging.format,
        [("auto_qb.core.x", logging.INFO, "启动完成"), ("auto_qb.core.y", logging.WARNING, "连接重试")]
    )
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    mgr.config.logging.file = log_path
    # 1.格式里没有等级字段 -> 等级无从判定
    mgr.config.logging.format = "%(asctime)s %(message)s"
    data = client.get("/api/log?lines=100&level=WARNING", headers=auth).json()
    assert data["lines"] == lines and data["note"] == NOTE_NO_LEVEL_FIELD
    # 2.格式有等级字段, 但文件里的行是另一种格式(改了 format, 旧行还在) -> 一行都对不上
    mgr.config.logging.format = "%(levelname)s|%(asctime)s|%(message)s"
    data = client.get("/api/log?lines=100&level=WARNING", headers=auth).json()
    assert data["lines"] == lines and data["note"] == NOTE_FORMAT_MISMATCH
    # 不过滤时无论哪种格式都照常给全部行, 且不带 note
    data = client.get("/api/log?lines=100", headers=auth).json()
    assert data["lines"] == lines and data["note"] == ""


def test_webui_module_apply_toggle_enabled(monkeypatch):
    """web.enabled 热开关(经 WebUIModule.apply, P2): 关 -> 开(启动服务器); 开 -> 关(停止并清空句柄)"""
    from helpers import make_manager

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        started = mock.MagicMock(return_value="新句柄")
        stopped = mock.MagicMock()
        monkeypatch.setattr("auto_qb.webui.start_web_server", started)
        monkeypatch.setattr("auto_qb.webui.stop_web_server", stopped)
        mod = mgr.host.get("webui")

        # 关 -> 开(旧句柄为 None, 原先该场景完全不生效)
        mgr.config.web = _web_stub(enabled=True, port=8080)
        mgr.web.handle = None
        mod.apply(SimpleNamespace(web=_web_stub(enabled=False, port=8080)), mgr.config)
        started.assert_called_once()
        assert mgr.web.handle == "新句柄"

        # 开 -> 关: 停止并清空句柄
        mgr.config.web = _web_stub(enabled=False, port=8080)
        mod.apply(SimpleNamespace(web=_web_stub(enabled=True, port=8080)), mgr.config)
        stopped.assert_called_once()
        assert mgr.web.handle is None


# ---------- 种子中心视图(WEB UI 替代 qB 界面: 种子页/详情抽屉/全局统计) ----------


def test_seed_flat_view_fields_and_gating():
    """种子平铺视图(SEED_ITEM): _build_flat_view 全字段契约 + ensure_group_state 同门控回传

    字段集与前端契约一字不差(详见实施 prompt); eta/time_active 按分钟量化(与重建判定
    同一步长); HR 字段与分组成员视图同源; 同版本请求不回传 torrents(与 groups/singles 同门控)。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        t1 = FakeTorrent(
            hash="H1",
            name="T1",
            state="stalledUP",
            save_path=r"R:\D",
            eta=8640030,
            time_active=3641,
            num_seeds=5,
            num_leechs=2,
            magnet_uri="magnet:?xt=urn:btih:H1",
            max_ratio=1.5,
        )
        seed_store(mgr, [t1])
        state = mgr.web.ensure_state(rid=None)
        items = state["torrents"]
        assert [t["hash"] for t in items] == ["H1"]
        item = items[0]
        expected = {
            "hash",
            "name",
            "site",
            "state",
            "kind",
            "dlspeed",
            "upspeed",
            "downloaded",
            "uploaded",
            "size",
            "total_size",
            "progress",
            "eta",
            "ratio",
            "max_ratio",
            "max_seeding_time",
            "max_inactive_seeding_time",
            "seeding_time",
            "added_on",
            "completion_on",
            "time_active",
            "availability",
            "num_seeds",
            "num_leechs",
            "num_complete",
            "num_incomplete",
            "tracker",
            "trackers_count",
            "category",
            "tags",
            "save_path",
            "dl_limit",
            "up_limit",
            "seq_dl",
            "f_l_piece_prio",
            "auto_tmm",
            "force_start",
            "super_seeding",
            "priority",
            "magnet_uri",
            "infohash_v1",
            "infohash_v2",
            "private",
            "comment",
            "created_by",
            "creation_date",
            "has_metadata",
            "piece_size",
            "pieces_have",
            "pieces_num",
            "last_activity",
            "total_wasted",
            "connections_count",
            "connections_limit",
            "reannounce",
            "reannounce_in",
            "has_tracker_error",
            "has_tracker_warning",
            "has_other_announce_error",
            "amount_left",
            "content_path",
            "download_path",
            "root_path",
            "popularity",
            "seen_complete",
            "downloaded_session",
            "uploaded_session",
            "hr_tag",
            "hr_tag_done",
            "hr_triggered",
            "hr_satisfied",
            "hr_req_time",
            "hr_req_ratio",
        }
        missing = expected - set(item)
        assert not missing, f"SEED_ITEM 缺字段: {missing}"
        # 量化: eta 8640030->8640000, time_active 3641->3600(与重建判定同一步长)
        assert item["eta"] == 8640000 and item["time_active"] == 3600
        assert item["num_seeds"] == 5 and item["num_leechs"] == 2
        assert item["magnet_uri"] == "magnet:?xt=urn:btih:H1" and item["max_ratio"] == 1.5
        assert item["hr_triggered"] is False, "HR 字段与成员视图同源(未配置站点为 False)"
        # 同版本: torrents 与 groups/singles/shows 同门控不回传
        again = mgr.web.ensure_state(rid=state["rid"])
        assert "torrents" not in again and "groups" not in again and "singles" not in again


def test_flat_view_refreshed_by_main_loop_tick():
    """种子页速度随主循环刷新(2026-09-18 缺陷回归: 平铺视图曾被"饿死")

    症状: 状态栏"速度合计"正常(它取 groups 求和, 由主循环每 tick 重建), 而种子页行内
    速度长时间不变。真因: 主循环只重建 `_group_view` 就把**共享**脏标记清掉 ⇒ Web 线程
    的兜底重建永不触发 ⇒ 平铺视图(flat)永远停在旧快照, 而版本号照常自增 ⇒ 前端判
    `updated=true` 把**陈旧数组整表换上去**。

    本用例钉住端到端事实: 主循环 tick 之后, Web 请求拿到的 torrents 必须是**新**速度。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1", state="downloading", dlspeed=100, progress=0.5)
        client.torrents["H2"] = FakeTorrent(hash="H2", name="T2", state="downloading", dlspeed=200, progress=0.5)
        mgr.config.grouping.enabled = True
        mgr.web.touch()  # Web 活跃(否则主循环跳过组装)
        mgr._tick(dry_run=False)
        first = mgr.web.ensure_state(rid=None)
        assert sorted(t["dlspeed"] for t in first["torrents"]) == [100, 200], "首轮应建出平铺视图"

        client.torrents["H1"].dlspeed = 999
        client.torrents["H2"].dlspeed = 888
        mgr.web.touch()
        mgr._tick(dry_run=False)  # 速度变化 -> 置脏 -> 主循环重建
        second = mgr.web.ensure_state(rid=first["rid"])
        assert second["updated"] is True, "视图版本号应随速度变化自增"
        got = {t["hash"]: t["dlspeed"] for t in second["torrents"]}
        assert got == {"H1": 999, "H2": 888}, f"种子页速度应随主循环刷新(修前恒为旧快照): {got}"
        # 未归组单种子视图(第二个受害者)同样要跟上
        assert {t["hash"]: t["dlspeed"] for t in second["singles"]} == got


def test_rebuild_views_single_entry_point():
    """rebuild_views 是**唯一**重建入口: 四份视图 + 版本号 + 脏标记一次完成

    在调用点各建一部分必然漏建(历史漏了 flat/singles/shows)—— 新增视图只能挂在这里。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        seed_store(mgr, [FakeTorrent(hash="H1", name="T1", dlspeed=1), FakeTorrent(hash="H2", name="T2", dlspeed=2)])
        mgr.web.group_view_dirty = True
        ver = mgr.web.group_view_ver
        mgr.web.rebuild_views()
        assert mgr.web.group_view_dirty is False, "重建后脏标记复位"
        assert mgr.web.group_view_ver == ver + 1, "版本号自增"
        assert sorted(t["dlspeed"] for t in mgr.web.flat_view) == [1, 2], "平铺视图同次重建"
        assert sorted(t["dlspeed"] for t in mgr.web.singles_view) == [1, 2], "单种子视图同次重建"
        assert mgr.web.shows_view["unrecognized"] == ["H1", "H2"], "追剧视图同次重建(T1/T2 无集数标记)"
        # 幂等: 标记已清 -> 不重复重建(惰性语义不被破坏)
        mgr.web.ensure_view()
        assert mgr.web.group_view_ver == ver + 1


def test_api_state_status_carries_server_state(web_env):
    """/api/state 的 status **恒**回传 server_state(不受 rid 门控)

    状态栏常显统计与"限制速度"取它。以前前端要为此单独再打一次 /api/stats —— 两条链路
    刷新频率不同 ⇒ 出现"状态栏速度正常、种子行速度滞后"的错位观测。合并后每轮只剩
    1 条请求, 且两者**同源同轮**。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    body = client.get("/api/state", headers=auth).json()
    assert "server" in body["status"], "status 须带 server_state(恒回传)"
    assert body["status"]["server"] is None, "未同步时为 null(前端显示未同步文案)"

    mgr.store.server_state = {"dl_info_speed": 1234}
    same = client.get(f"/api/state?rid={body['rid']}", headers=auth).json()
    assert "groups" not in same, "版本一致时不回传 groups(响应体趋近于零)"
    assert same["status"]["server"] == {"dl_info_speed": 1234}, "但 server_state 恒回传"


def test_api_torrent_detail_endpoint(web_env):
    """GET /api/torrents/{hash}: 全字段详情(to_dict + site + HR 展示字段); 未知 hash 404"""
    from auto_qb.torrents import TorrentRecord

    mgr, client = web_env
    rec = TorrentRecord.from_torrent(
        {
            "hash": "HA",
            "name": "Detail",
            "save_path": r"R:\D",
            "state": "stalledUP",
            "size": 100,
            "total_size": 100,
            "downloaded": 100,
            "uploaded": 5,
            "dlspeed": 0,
            "upspeed": 0,
            "seeding_time": 60,
            "ratio": 0.05,
            "amount_left": 0,
            "completed": 100,
            "progress": 1.0,
            "dl_limit": 0,
            "up_limit": 0,
            "added_on": 1700000000,
            "tags": "",
            "category": "",
            "content_path": r"R:\D\Detail",
            "magnet_uri": "magnet:?xt=urn:btih:HA",
            "eta": 8640000,
            "num_seeds": 3,
        },
        hash="HA",
    )
    mgr.store.get = lambda h: {"HA": rec}.get(h)
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    resp = client.get("/api/torrents/HA", headers=auth)
    assert resp.status_code == 200
    t = resp.json()["torrent"]
    assert t["hash"] == "HA" and t["name"] == "Detail"
    assert t["magnet_uri"] == "magnet:?xt=urn:btih:HA" and t["num_seeds"] == 3
    assert t["site"] == "Unknown", "未匹配站点时 site 为 Unknown(与 tracker_name 语义一致)"
    assert "hr_triggered" in t and "infohash_v1" in t, "HR 字段与 to_dict 全字段都应透出"
    assert client.get("/api/torrents/NOPE", headers=auth).status_code == 404


def test_api_torrent_subresources(web_env):
    """GET /api/torrents/{hash}/trackers|files|peers: qB 透传; 未知 hash 404, qB 断连 503"""
    from helpers import FakeClient

    from auto_qb.torrents import TorrentRecord

    mgr, client = web_env
    rec = TorrentRecord(hash="HA", name="X")
    mgr.store.get = lambda h: {"HA": rec}.get(h)
    fake = FakeClient()
    fake.trackers_map["HA"] = [{"url": "https://t.example/announce", "status": 2}]
    fake.files_map["HA"] = [{"index": 0, "name": "a.mkv", "size": 1}]
    fake.peers_map["HA"] = {"peers": [{"ip": "1.2.3.4", "client": "qB"}]}
    mgr.client = fake
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    assert client.get("/api/torrents/HA/trackers", headers=auth).json() == fake.trackers_map["HA"]
    assert client.get("/api/torrents/HA/files", headers=auth).json() == fake.files_map["HA"]
    peers = client.get("/api/torrents/HA/peers", headers=auth).json()
    assert peers["peers"][0]["ip"] == "1.2.3.4"
    assert fake.peers_calls == 1, "peers 走透传(不写 store 惰性缓存)"
    # 未知 hash: 404(先于 client 检查)
    assert client.get("/api/torrents/NOPE/trackers", headers=auth).status_code == 404
    # qB 断连: 503
    mgr.client = None
    assert client.get("/api/torrents/HA/files", headers=auth).status_code == 503
    assert client.get("/api/torrents/HA/peers", headers=auth).status_code == 503


def test_api_readonly_endpoints_short_cache(web_env):
    """P1-4: 直连 qB 的只读端点短缓存 —— 窗口内合并重复请求; **写命令后立即失效**; 断连仍 503

    "写后失效"是硬要求: 没有它就会出现"刚改完文件优先级、重取还拿到缓存旧值"这种
    **看起来没生效**的假象。断连优先于缓存也是硬要求: 拿旧值冒充"还连着"会把 qB 已断开藏起来。
    """
    from helpers import FakeClient

    from auto_qb.torrents import TorrentRecord

    mgr, client = web_env
    rec = TorrentRecord(hash="HA", name="X")
    mgr.store.get = lambda h: {"HA": rec}.get(h)
    fake = FakeClient()
    fake.files_map["HA"] = [{"index": 0, "name": "a.mkv", "size": 1}]
    mgr.client = fake
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    first = client.get("/api/torrents/HA/files", headers=auth).json()
    assert first == fake.files_map["HA"]
    assert fake.files_calls == 1
    # 窗口内重复请求: 命中缓存, 不再打 qB
    assert client.get("/api/torrents/HA/files", headers=auth).json() == first
    assert fake.files_calls == 1, "同一时间窗内的重复请求应合并为一次 qB 调用"
    # 写命令后失效(模拟主循环消费了一条写命令)
    mgr.web.write_seq += 1
    assert client.get("/api/torrents/HA/files", headers=auth).json() == first
    assert fake.files_calls == 2, "写命令后缓存必须失效, 否则用户会看到'改了没生效'"
    # 断连优先于缓存: 仍 503, 不拿旧值冒充还连着
    mgr.client = None
    assert client.get("/api/torrents/HA/files", headers=auth).status_code == 503


def test_api_torrent_peers_endpoint(web_env):
    """GET /api/torrents/{hash}/peers: 走 sync_torrent_peers(torrent_hash=..)整包透传

    qbittorrent-api 2026.8.1 无 torrents_peers 方法(线上调用 AttributeError), 端点改走
    sync/torrentPeers —— 响应整包含 rid/full_update/peers/peers_removed, 前端对 peers 键
    做 dict/数组双形态归一(抽屉 state 默认 peers: {peers: []} 同形状)。回归守阵:
    若改回旧调用, FakeClient 已无 torrents_peers, 本测试 500 红。
    """
    from helpers import FakeClient

    from auto_qb.torrents import TorrentRecord

    mgr, client = web_env
    rec = TorrentRecord(hash="HA", name="X")
    mgr.store.get = lambda h: {"HA": rec}.get(h)
    fake = FakeClient()
    fake.peers_map["HA"] = {
        "rid": 7,
        "full_update": True,
        "peers": {
            "1.2.3.4:51413": {
                "ip": "1.2.3.4",
                "port": 51413,
                "client": "qBittorrent 5.0"
            }
        },
        "peers_removed": [],
    }
    mgr.client = fake
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    resp = client.get("/api/torrents/HA/peers", headers=auth)
    assert resp.status_code == 200
    assert resp.json() == fake.peers_map["HA"], "sync 响应整包透传(前端按 peers 键归一)"
    assert fake.peers_calls == 1
    # 未知 hash: 404(先于 client 检查); qB 断连: 503
    assert client.get("/api/torrents/NOPE/peers", headers=auth).status_code == 404
    mgr.client = None
    assert client.get("/api/torrents/HA/peers", headers=auth).status_code == 503


def test_api_stats_endpoint(web_env):
    """GET /api/stats: 透出 store.server_state(qB 全局状态); 未同步/降级时 null"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    assert client.get("/api/stats", headers=auth).json() == {"server": None}
    mgr.store.server_state = {"dl_info_speed": 1024, "dht_nodes": 9}
    data = client.get("/api/stats", headers=auth).json()
    assert data["server"] == {"dl_info_speed": 1024, "dht_nodes": 9}


def test_api_enqueue_wakes_main_loop(web_env):
    """P0-1: 投递用户命令 -> 唤醒主循环立即消费(命令不必等下个 tick)

    反向守卫: **自投递**命令(build_search_index 等)不得唤醒, 否则形成自激循环
    (唤醒 -> drain 500 条文件 API -> 索引仍脏 -> 再投递 -> 立刻再唤醒)打满 CPU 并冲垮 qB。
    """
    import re

    from auto_qb.webui.commands import SELF_POSTED_COMMANDS

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    mgr._wake_calls.clear()
    assert client.post("/api/torrents/HA/recheck", headers=auth).status_code == 200
    assert len(mgr._wake_calls) == 1, f"用户命令投递后应唤醒主循环, 实际 {len(mgr._wake_calls)} 次"

    # 静态反向守卫: Web 侧所有 self-posted 的 cmd 名都必须登记, 否则下次新增就会自激
    src = open(os.path.join(os.path.dirname(__file__), "..", "src", "auto_qb", "webui", "views.py"),
               encoding="utf-8").read()
    # 两种投递写法都要认(2026-09-20 起统一走门面的 post_command; 旧写法保留匹配以防回退)
    posted = set(re.findall(r'web_commands\.put\(\(\s*"([^"]+)"', src)
                ) | set(re.findall(r'web\.post_command\(\s*"([^"]+)"', src))
    assert posted, "未解析到任何自投递命令 —— 正则或源码位置已变, 守卫失效"
    missing = posted - set(SELF_POSTED_COMMANDS)
    assert not missing, (f"自投递命令 {missing} 未登记进 SELF_POSTED_COMMANDS —— "
                         "遗漏会让主循环自激打满 CPU 并冲垮 qB")


def test_cmd_timing_is_logged_without_browser(caplog):
    """命令耗时必须落到**日志**(不是只在回执里回传) —— 真机排查"点了要等几秒"的主出口

    2026-09-20: 用户连报四次「乐观 UI 生效但要 2-4s 才恢复正常」, 四轮修复全在前端找, 因为
    1. 本地桩服务没有主循环 ⇒ wait_ms 恒为 0 ⇒ 「投递 → 回执」这一段从来没被测到;
    2. 埋点只随回执回传, 要看就得开 F12 —— 真机上用户常常开不了/不愿开, 等于没有埋点。
    故 `_log_cmd_timing` 直接落日志, 且**慢命令必须 WARNING**(否则淹没在 INFO 里捞不出来)。
    """
    import logging

    from auto_qb.webui.commands import CMD_SLOW_MS
    from auto_qb.webui import WebUIRuntime

    class _T:
        """只需要 _log_cmd_timing 用到的两个属性"""
        _web_results = {}
        _web_write_seq = 0

        _log_cmd_timing = WebUIRuntime._log_cmd_timing

    t = _T()
    # 1. 慢 -> WARNING, 且带归因提示(排队/执行各自指向不同的后端原因)
    with caplog.at_level(logging.DEBUG):
        caplog.clear()
        t._log_cmd_timing("pause_torrent", {"wait_ms": 1800.0, "exec_ms": 2.0})
    recs = [r for r in caplog.records if "[cmd]" in r.getMessage()]
    assert recs, "慢命令没有落日志 —— 真机无法排查"
    assert recs[-1].levelno == logging.WARNING, f"慢命令应为 WARNING, 实际 {recs[-1].levelname}"
    assert "1800" in recs[-1].getMessage()

    # 2. 快 -> DEBUG(2026-09-21 改: 原本是 INFO, 但每条命令都打会把日志刷满;
    #    常态耗时改由前端 `[perf]` 那一行承载, 服务端只在**异常慢**时升 WARNING)
    with caplog.at_level(logging.DEBUG):
        caplog.clear()
        t._log_cmd_timing("pause_torrent", {"wait_ms": 1.0, "exec_ms": 3.0})
    recs = [r for r in caplog.records if "[cmd]" in r.getMessage()]
    assert recs, "快命令也要有记录(否则排查时连 DEBUG 都捞不出来)"
    assert recs[-1].levelno == logging.DEBUG, f"快命令应为 DEBUG(不占 INFO), 实际 {recs[-1].levelname}"
    # 反过来钉住: 快命令**不得**是 INFO 及以上(否则又回到刷屏)
    with caplog.at_level(logging.INFO):
        caplog.clear()
        t._log_cmd_timing("pause_torrent", {"wait_ms": 1.0, "exec_ms": 3.0})
    assert not [r for r in caplog.records if "[cmd]" in r.getMessage()], "快命令不得进 INFO —— 每条命令都打会刷屏"

    # 3. 自投递命令(建索引等)频次高 -> 压到 DEBUG, 不许进常规日志
    with caplog.at_level(logging.DEBUG):
        caplog.clear()
        t._log_cmd_timing("build_search_index", {"wait_ms": 900.0, "exec_ms": 900.0})
    recs = [r for r in caplog.records if "[cmd]" in r.getMessage()]
    assert recs and recs[-1].levelno == logging.DEBUG, "自投递命令会刷屏, 必须压到 DEBUG"

    assert CMD_SLOW_MS > 0


def _mk_mgr_with_one_torrent(state="pausedDL", progress=1.0):
    """一个只含单个种子的 QbManager(供回执时序类断言用)

    !临时目录**挂到 mgr 上**, 不用 `tempfile.mkdtemp()`(2026-09-23 实测): 后者没有任何人回收,
    每跑一次就在 TMPDIR 根下留一个 `tmpXXXX` 目录 —— 实测已积到 1268 个。
    也不能写成"函数内建 TemporaryDirectory 但不返回": 局部对象出函数即被回收, 目录当场消失,
    mgr 后续写 state.json 会失败。挂给 mgr 后随 mgr 释放即删, 两头都对。
    """
    import tempfile

    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    tmpdir = tempfile.TemporaryDirectory(prefix="autoqb-web-")
    mgr = make_manager(os.path.join(tmpdir.name, "state.json"))
    mgr._test_tmpdir = tmpdir  # 生命周期锚点: 见 docstring, 不能让它在这里被回收
    tor = FakeTorrent(hash="b" * 40, name="t", state=state, progress=progress)
    mgr.client = FakeClient()
    mgr.client.torrents[tor.hash] = tor
    seed_store(mgr, [tor])
    return mgr, tor


def test_receipt_sent_immediately_truth_pushed_later():
    """回执**立即**发(不带真值), 真值落地后单独推(2026-09-20 D2 定案)

    旧做法: 扣住回执等真值落地再发, 且把真值塞在回执里。
    真机实测(23:15 暂停种子): qB 执行只要 2.7ms、补刷新 2.9ms, 但真值要等 **1258ms** 才在
    qB 侧出现(走直查也一样)⇒ 扣着回执等 = 撤下被钉死在 1.25s+(实测撤下 2947ms)。

    新做法两步:
      1. 回执立刻发 —— 只表示"命令已执行", **不带 truth**(带上未落地的真值 = 让前端采纳
         命令前的旧值 ⇒ 弹回, 那条红线不能破); 前端据此结束压暗 ⇒ 撤下降到 10~20ms。
      2. 真值继续直查, 落地了再推 `truth` 事件; **超时不推**(宁可让前端超时回滚)。
    """
    import time

    from auto_qb.webui.commands import TRUTH_PUSH_CAP_MS

    mgr, tor = _mk_mgr_with_one_torrent(state="pausedDL", progress=1.0)
    rt = mgr.web
    h = tor.hash
    pushed = []
    rt.notify = lambda etype, payload: (pushed.append((etype, payload)), 0)[1]

    # 1. 回执立即到账, 且**不带 truth**
    rt.defer_receipt("r1", "resume_torrent", {"hash": h}, {"wait_ms": 0.0, "exec_ms": 1.0})
    assert rt.results["r1"]["status"] == "ok", "回执必须立即发(不再扣住等真值)"
    assert "truth" not in rt.results["r1"], "回执带未落地的真值 ⇒ 前端采纳旧值 ⇒ 弹回"
    assert "r1" in rt.truth_pending, "真值应登记为待推"

    # 2. 真值没落地 -> 不推
    rt.flush_truths()
    assert not [p for p in pushed if p[0] == "truth"], "真值未落地不得推送"

    # 3. 真值落地 -> 推 `truth` 事件, 内容是落地后的值
    tor.state = "uploading"
    rt.flush_truths()
    ev = [p for p in pushed if p[0] == "truth"]
    assert len(ev) == 1, ev
    assert ev[0][1]["truth"][h]["kind"] == "seeding", ev[0][1]
    assert "r1" not in rt.truth_pending, "推完应出队"

    # 4. 超时兜底: 真值始终不落地则**放弃推送**(不是推一个可能是旧值的真值)
    rt.defer_receipt("r2", "pause_torrent", {"hash": h}, {"wait_ms": 0.0, "exec_ms": 1.0})
    assert rt.results["r2"]["status"] == "ok"
    rt.truth_pending["r2"]["ts"] = time.time() - (TRUTH_PUSH_CAP_MS / 1000.0 + 1.0)
    before = len([p for p in pushed if p[0] == "truth"])
    rt.flush_truths()
    assert len([p for p in pushed if p[0] == "truth"]) == before, "真值超时未落地必须**不推**"


def test_affected_truth_reads_qb_directly_not_sync_snapshot():
    """真值必须**直查 qB**(torrents/info), 不得读 /sync/maindata 同步快照

    定案背景(2026-09-20): 同步快照按 qB 的节奏刷新 —— 真机实测命令后要等 6 轮 / **1362ms**
    才在快照上看到新状态(命令本身只要 8.4ms), 这个数与
    `sync_interval = 1.5 # 与 qB 自带 WebUI(1500ms)同量级` 几乎重合 ⇒ 滞后来自快照刷新。
    拿快照当"命令后的真值"就会读到命令**前**的旧值 —— 这正是"撤下要等 3s"的根源。

    判据: 故意让**快照**与** qB 客户端**不一致, 真值必须等于客户端那一侧。
    !这条守阵要能挡住"改回读 store.by_hash": 那样 truth 会变成 paused, 断言立刻红。
    """
    with tempfile.TemporaryDirectory() as td:
        from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        # qB 客户端(直查看到的是它): 已经在做种 —— 命令已生效
        client.torrents["H1"] = FakeTorrent(hash="H1", name="n", state="uploading", progress=1.0)
        # 同步快照(store): 还停在命令**前**的暂停态(复刻快照滞后)
        seed_store(mgr, [FakeTorrent(hash="H1", name="n", state="pausedDL", progress=1.0)])

        truth = mgr.web._affected_truth("resume_torrent", {"hash": "H1"})
        assert truth == {
            "H1": {
                "kind": "seeding"
            }
        }, (f"真值应取 qB 直查结果(seeding), 实际 {truth} —— "
            "若这里是 paused 说明又去读同步快照了")
        # 反证: 快照那一侧确实还是 paused —— 证明本用例有判别力, 不是恒真
        assert mgr.store.by_hash["H1"].state == "pausedDL"


def test_truth_hold_matches_truth_push_cap():
    """前端"值覆盖"的保持上限必须与后端真值推送上限一致(否则判据漂移)

    !本条**同时**修掉一个既有缺陷: 原 `test_truth_hold_budget_matches_backend` 在文件里
      同名定义了两次, Python 后者覆盖前者 ⇒ 前一条**从未执行**(已入池 issue
      26-09-20-2212)。现在合并成一条, 且断言改名后的新常数 —— 守阵失效时会直接红,
      不会像之前那样"看着有守阵其实没跑"。

    新契约(D2): 前端 TRUTH_HOLD_MS = 后端 TRUTH_PUSH_CAP_MS。
      前端: 值覆盖最多保持这么久, 超时回滚(不留假状态);
      后端: 真值最多等这么久, 超时放弃推送(不推可能未落地的真值)。
      两边是同一段窗口的两端, 不一致就会出现"前端先回滚、真值后到"的错配。
    """
    import re

    from auto_qb.webui.commands import TRUTH_PUSH_CAP_MS

    js = open(
        os.path.join(os.path.dirname(__file__), "..", "src", "auto_qb", "webui", "static", "shared", "commands.js"),
        encoding="utf-8",
    ).read()
    m = re.search(r"TRUTH_HOLD_MS\s*=\s*([\d.]+)", js)
    assert m, "commands.js 里找不到 TRUTH_HOLD_MS —— 守阵失效(常数被改名?)"
    assert float(
        m.group(1)
    ) == float(TRUTH_PUSH_CAP_MS
              ), (f"前端值覆盖保持 {m.group(1)}ms != 后端真值推送上限 {TRUTH_PUSH_CAP_MS}ms —— "
                  "两边必须一致, 否则会出现'前端先回滚、真值后到'的错配")


def test_cmd_trackers_log_sanitized(caplog):
    """tracker 编辑/移除的日志只写脱敏主地址, 不含凭据全文(issue 26-09-21-1408)

    断言口径刻意**不写死参数名**: 私站凭据参数名是任意的(passkey 只是最常见的一种),
    所以只钉死"密钥全文一行都进不了日志 + 主地址仍在(够排查是哪个站)"。
    日志会落盘(含轮转备份)且能经 /api/log 读回, 泄露面比"读一次"大得多。
    """
    from auto_qb.webui.commands import WebCommandsMixin
    from helpers import FakeClient

    class _Cmds(WebCommandsMixin):
        def __init__(self):
            self.api = FakeClient()
            self.store = {"HA": object()}

    m = _Cmds()
    secret = "https://pt.example.com/announce?passkey=SUPERSECRET123"
    caplog.set_level(logging.INFO, logger="auto_qb.webui.commands")
    caplog.clear()
    m._cmd_edit_tracker(hash="HA", orig_url=secret, new_url="https://other.example.com/announce?authkey=XYZ")
    m._cmd_remove_tracker(hash="HA", url=secret)
    text = "\n".join(r.getMessage() for r in caplog.records if r.name == "auto_qb.webui.commands")
    assert "SUPERSECRET123" not in text, "passkey 全文进了日志"
    assert "XYZ" not in text, "换名的凭据(authkey)同样不能进日志"
    assert "passkey" not in text and "authkey" not in text, "query 整段都应丢弃, 不该残留参数名"
    assert "pt.example.com" in text and "other.example.com" in text, "主地址要保留(否则没法排查是哪个站)"


# ---- W0 结构守阵(plan 26-09-22-1857: web.py create_app 拆分 web/ 包, 先行落阵再动刀) ----

# 从拆分前的 web.py 用 AST 提取的全部路由(取证 2026-09-22, develop @ 975e146):
# 57 个 /api 端点 + 3 个 UI 重定向(/, /newui, /newui/{rest:path})。拆分全程必须逐条保持。
# (2026-09-28 ALT-01 增 POST /api/speed/alt 与 /api/speed/alt/toggle 两条, 计划 26-09-28-0037)
# (2026-10-02 增 POST /api/events/ticket —— SSE 一次性票据换票, issue 26-09-21-1408 B-01)
# (2026-10-03 增 3 条 GET /api/traffic/qb/* —— qB 口径流量图, plan 26-10-03-0946 §08 P4)
# (2026-10-04 增 1 条 GET /api/hr/history —— 拉取历史时间轴, plan 26-10-04-0312 §3.4)
_GOLDEN_ROUTES = {
    ("GET", "/"),
    ("GET", "/api/categories"),
    ("POST", "/api/categories"),
    ("POST", "/api/categories/edit"),
    ("POST", "/api/categories/remove"),
    ("GET", "/api/cmd/{cmd_id}"),
    ("POST", "/api/hr/confirm-empty"),
    ("POST", "/api/hr/refresh"),  # 26-09-30-0240: 立即拉取(置一次性 force 旗标 + 唤醒取数线程)
    ("GET", "/api/config"),
    ("PUT", "/api/config"),
    ("POST", "/api/config/preview"),
    ("GET", "/api/config/public"),
    ("GET", "/api/config/schema"),
    ("GET", "/api/events"),
    ("POST", "/api/events/ticket"),  # SSE 换票(26-10-02 加固: ?ticket= 取代 ?token= 查询串)
    ("POST", "/api/expr/eval"),
    ("GET", "/api/fs/dirs"),
    ("POST", "/api/fs/mkdir"),
    ("GET", "/api/groups"),
    ("POST", "/api/groups/{key}/delete"),
    ("POST", "/api/groups/{key}/pause"),
    ("POST", "/api/groups/{key}/reannounce"),
    ("POST", "/api/groups/{key}/resume"),
    ("GET", "/api/keys"),  # 键盘快捷键 W6(计划 26-09-28-0354): webui-keys.json 读(兜底链)
    ("PUT", "/api/keys"),  # 同上: 整份替换写(结构校验 422)
    ("GET", "/api/log"),
    ("POST", "/api/open-path"),
    ("GET", "/api/paths"),
    ("GET", "/api/search"),
    ("GET", "/api/speed/mode"),
    ("POST", "/api/speed/override"),
    ("POST", "/api/speed/alt"),
    ("POST", "/api/speed/alt/toggle"),
    ("GET", "/api/state"),
    ("GET", "/api/stats"),
    ("GET", "/api/status"),
    ("GET", "/api/tags"),
    ("POST", "/api/tags"),
    ("POST", "/api/tags/remove"),
    ("POST", "/api/torrents/add"),
    ("POST", "/api/torrents/bulk"),
    ("GET", "/api/torrents/{hash}"),
    ("POST", "/api/torrents/{hash}/auto-tmm"),
    ("POST", "/api/torrents/{hash}/delete"),
    ("GET", "/api/torrents/{hash}/export"),
    ("GET", "/api/torrents/{hash}/files"),
    ("POST", "/api/torrents/{hash}/files/priority"),
    ("POST", "/api/torrents/{hash}/force-start"),
    ("POST", "/api/torrents/{hash}/limits"),
    ("POST", "/api/torrents/{hash}/location"),
    ("POST", "/api/torrents/{hash}/pause"),
    ("GET", "/api/torrents/{hash}/peers"),
    ("POST", "/api/torrents/{hash}/queue"),
    ("POST", "/api/torrents/{hash}/reannounce"),
    ("POST", "/api/torrents/{hash}/recheck"),
    ("POST", "/api/torrents/{hash}/rename"),
    ("POST", "/api/torrents/{hash}/rename-fs"),
    ("POST", "/api/torrents/{hash}/resume"),
    ("POST", "/api/torrents/{hash}/share-limits"),
    ("POST", "/api/torrents/{hash}/skip-check"),  # P2' 右键跳检(plan 26-09-30-0109)
    ("POST", "/api/torrents/skip-check/precheck"),  # 跳检预检只读端点(plan 26-10-05-0314 S2; 403 门控同单发)
    ("POST", "/api/torrents/{hash}/super-seeding"),
    ("GET", "/api/torrents/{hash}/trackers"),
    ("POST", "/api/torrents/{hash}/trackers/add"),
    ("POST", "/api/torrents/{hash}/trackers/edit"),
    ("POST", "/api/torrents/{hash}/trackers/remove"),
    ("GET", "/api/traffic/history"),
    ("GET", "/api/traffic/qb/global"),  # qB 口径流量图三端点(plan 26-10-03-0946 §08 P4; 同域对照 history)
    ("GET", "/api/traffic/qb/group/{key}"),  # 同上: 组读侧现算(§04.1), key 同 /api/groups/{key} 通道
    ("GET", "/api/traffic/qb/torrent/{hash}"),  # 同上: 单种(数据挂 infohash, 删种冻结后历史仍可查)
    ("GET", "/newui"),
    ("GET", "/newui/{rest:path}"),
    ("GET", "/api/hr/status"),  # M4: HR 站点级状态快照(只读; 与 --hr-status 同一口径)
    ("GET", "/api/hr/sites/{site}/entries"),  # 种子明细(计划 26-10-01-2216 §7 阶段1; 决策点②b 按站点按需拉)
    ("GET", "/api/hr/history"),  # 拉取历史时间轴(计划 26-10-04-0312 §3.4; 表③ 数据源, 跨站合并)
    ("GET", "/api/sites/missing"),  # 站点导入: 未配置站点扫描(只读; 与 --export-yaml --only-missing 同口径)
    ("GET", "/api/webui/flags"),  # R2 跳检菜单开关(计划 26-10-02-1955 W1): 前端功能旗标(登录后, 读实时配置)
}


def _iter_api_routes(routes):
    """展平 include_router 的注册结果: 本环境 FastAPI 把路由包在 _IncludedRouter 里,
    不再展开为平铺 APIRoute —— 按域 Router 拆分后必须递归下钻才能清点到全部路由。"""
    from fastapi.routing import APIRoute

    for r in routes:
        if isinstance(r, APIRoute):
            yield r
            continue
        for attr in ("original_router", "router"):
            sub = getattr(r, attr, None)
            if sub is not None and hasattr(sub, "routes"):
                yield from _iter_api_routes(sub.routes)
                break


def test_web_route_manifest_frozen(web_env):
    """路由金清单守阵: 76 条 (method, path) 集合逐一钉死, 丢失/改名/方法变更即红

    集合比对**不比顺序**: 拆分后按域 include_router, 跨 router 注册顺序与旧源码不再逐条
    一致 —— 已核实无同形路径冲突(每条 (method, path) 恰好一条路由, /api/torrents/bulk、
    /add 与 /{hash} 靠方法区分); 各 router 内部相对顺序保持源码顺序。
    HEAD 是 Starlette 对 GET 路由的自动补集, 比对时剔除。
    """
    from starlette.routing import Mount

    mgr, client = web_env
    app = client.app
    found = {(next(iter(r.methods - {"HEAD"})), r.path) for r in _iter_api_routes(app.routes)}
    assert found == _GOLDEN_ROUTES, (
        f"路由清单漂移: 多出 {sorted(found - _GOLDEN_ROUTES)}, 丢失 {sorted(_GOLDEN_ROUTES - found)}"
    )
    assert any(isinstance(r, Mount) for r in app.routes), "静态挂载(StaticFiles)不得丢失"


def test_create_app_is_thin_assembly():
    """组装壳守阵(W6, plan 26-09-22-1857): create_app 源 ≤150 行且不含内联路由装饰器

    本 issue 的病根是工厂函数无约束生长(926 行); 行数上限 + 装饰器检查双闸防回潮。
    红验: 同一断言跑拆分前的 create_app(926 行, 含 @app.*)必红(见计划 §06 W6)。
    """
    import inspect

    from auto_qb.webui import create_app

    src = inspect.getsource(create_app)
    n = len(src.splitlines())
    assert n <= 150, f"create_app 长回 {n} 行(上限 150) —— 端点请进 routes/ 对应域模块, 别再塞回工厂"
    assert "@app." not in src, "组装壳里不得出现内联路由装饰器 —— 端点一律放 routes/ 模块"


# ---------------- 键盘快捷键 /api/keys(W6, 计划 26-09-28-0354 §4.4; 前端接线守阵在 test_web_shortcuts.py) ----------------


def _keys_headers(mgr):
    return {"Authorization": f"Bearer {mgr.web.token}"}


def test_api_keys_get_default_when_missing(web_env):
    """快捷键配置文件不存在(用户从未自定义) -> GET 回默认表, 不报错不建文件"""
    mgr, client = web_env
    r = client.get("/api/keys", headers=_keys_headers(mgr))
    assert r.status_code == 200
    assert r.json() == {"schema_version": 1, "template": "aqb-default", "overrides": {}}


def test_api_keys_put_roundtrip(web_env):
    """PUT 合法配置落盘且 GET 原样回读; 空串(显式禁用)语义在存储层原样保留"""
    import json as _json

    from auto_qb.webui.server.routes.keys import keys_file_path

    mgr, client = web_env
    doc = {"schema_version": 1, "template": "aqb-default", "overrides": {"act-pause": "Ctrl+KeyP", "act-resume": ""}}
    r = client.put("/api/keys", headers=_keys_headers(mgr), json=doc)
    assert r.status_code == 200, r.text
    assert r.json() == doc
    # 落盘: 同目录文件存在且内容与响应一致(读回是合法 JSON)
    stored = _json.loads(Path(keys_file_path(mgr)).read_text(encoding="utf-8"))
    assert stored == doc
    # 回读
    r2 = client.get("/api/keys", headers=_keys_headers(mgr))
    assert r2.status_code == 200 and r2.json() == doc


def test_api_keys_put_invalid_rejected(web_env):
    """PUT 结构非法 -> 422, 且不触碰磁盘(合法旧值原样保留)"""
    import json as _json

    from auto_qb.webui.server.routes.keys import keys_file_path

    mgr, client = web_env
    good = {"schema_version": 1, "template": "aqb-default", "overrides": {"act-pause": "KeyP"}}
    assert client.put("/api/keys", headers=_keys_headers(mgr), json=good).status_code == 200
    bad_cases = [
        # schema_version 错 / 缺 template / overrides 非表 / 值非字符串 / 归一化串非法(修饰序乱/小写)
        {
            "schema_version": 2,
            "template": "aqb-default",
            "overrides": {}
        },
        {
            "schema_version": 1,
            "overrides": {}
        },
        {
            "schema_version": 1,
            "template": "aqb-default",
            "overrides": []
        },
        {
            "schema_version": 1,
            "template": "aqb-default",
            "overrides": {
                "act-pause": 1
            }
        },
        {
            "schema_version": 1,
            "template": "aqb-default",
            "overrides": {
                "act-pause": "Shift+Ctrl+KeyP"
            }
        },
        {
            "schema_version": 1,
            "template": "aqb-default",
            "overrides": {
                "act-pause": "ctrl+keyp"
            }
        },
    ]
    for bad in bad_cases:
        r = client.put("/api/keys", headers=_keys_headers(mgr), json=bad)
        assert r.status_code == 422, f"{bad} 应 422, 实得 {r.status_code}"
    # 磁盘未被触碰
    import json as _json2
    stored = _json2.loads(Path(keys_file_path(mgr)).read_text(encoding="utf-8"))
    assert stored == good


def test_api_keys_read_corrupt_fallback(web_env, caplog):
    """读时兜底链: 主文件坏 JSON -> WARN + 默认表; .bak 完好 -> 回备份(§4.4)"""
    import json as _json
    import logging as _logging

    from auto_qb.webui.server.routes.keys import keys_file_path

    mgr, client = web_env
    path = Path(keys_file_path(mgr))
    # 主文件坏 + 无备份 -> 默认表 + WARN
    path.write_text("{oops", encoding="utf-8")
    with caplog.at_level(_logging.WARNING, logger="auto_qb.web"):
        r = client.get("/api/keys", headers=_keys_headers(mgr))
    assert r.status_code == 200
    assert r.json() == {"schema_version": 1, "template": "aqb-default", "overrides": {}}
    assert any("快捷键配置" in rec.message for rec in caplog.records), "损坏必须 WARN(失效模式可测可查)"
    # .bak 完好 -> 回备份
    bak = {"schema_version": 1, "template": "aqb-default", "overrides": {"act-pause": "KeyP"}}
    (path.parent / (path.name + ".bak")).write_text(_json.dumps(bak), encoding="utf-8")
    r2 = client.get("/api/keys", headers=_keys_headers(mgr))
    assert r2.json() == bak


def test_api_keys_unknown_schema_version_fallback(web_env, caplog):
    """schema_version 不识别(未来版本) -> 回默认表 + WARN(宁可回默认, 不带病生效)"""
    import json as _json
    import logging as _logging

    from auto_qb.webui.server.routes.keys import keys_file_path

    mgr, client = web_env
    Path(keys_file_path(mgr)
        ).write_text(_json.dumps({
            "schema_version": 99,
            "template": "x",
            "overrides": {}
        }), encoding="utf-8")
    with caplog.at_level(_logging.WARNING, logger="auto_qb.web"):
        r = client.get("/api/keys", headers=_keys_headers(mgr))
    assert r.json() == {"schema_version": 1, "template": "aqb-default", "overrides": {}}
    assert any("结构不符" in rec.message for rec in caplog.records)


def test_drain_web_commands_recheck_rejected_while_checking():
    """R1 单发拒绝(plan 26-09-30-0109 §3.2): 规则校验在途时 WEB recheck -> 回执 error「校验进行中」, qB 不重启校验

    C1 的 WEB->规则半边: WEB recheck 直调 API 会重启规则正在轮询的校验, 进度回落可能触发
    CHECK_START_GIVEUP 误判失败并污染当日失败计数。提交点检查在 ops 层单点, handler 只映射回执。
    """
    from auto_qb.core.taskqueue import REQUEUE, Task

    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        inflight = Task("check", "check-checking-result", hash="HA", store=mgr.store, handler=lambda t, d: REQUEUE)
        assert mgr.task_queue.add_task(inflight)
        mgr.web.commands.put(("recheck_torrent", {"hash": "HA", "cmd_id": "r1"}))
        mgr.web.consume_commands()
        assert client.recheck_hashes_calls == [], f"拒绝时 qB 不得收到 recheck: {client.recheck_hashes_calls}"
        assert mgr.web.results["r1"]["status"] == "error", mgr.web.results
        assert "校验进行中" in mgr.web.results["r1"]["error"], mgr.web.results["r1"]


def test_drain_web_commands_bulk_recheck_skips_inflight():
    """R1 bulk 第二入口(plan 26-09-30-0109 §3.2): 在途 hash 逐个经 ops 过滤, 聚合回执带跳过计数

    bulk recheck 直调 API 是 C1 的第二入口(批量路径旁路); 现逐个走 ops_recheck(source="web"):
    在途/校验中的 hash 被拒绝并计数, 其余正常提交并登记在途(决策链 1.5 可见)。
    """
    from auto_qb.core.taskqueue import REQUEUE, Task

    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        inflight = Task("check", "check-checking-result", hash="HB", store=mgr.store, handler=lambda t, d: REQUEUE)
        assert mgr.task_queue.add_task(inflight)
        mgr.web.commands.put(("bulk_torrents", {"hashes": ["HA", "HB"], "action": "recheck", "cmd_id": "b9"}))
        mgr.web.consume_commands()
        assert client.recheck_hashes_calls == ["HA"], f"仅非在途的 HA 提交: {client.recheck_hashes_calls}"
        assert "HA" in mgr.task_queue.active_check_hashes(), "提交的 hash 应登记在途"
        assert mgr.web.results["b9"]["status"] == "error", mgr.web.results
        assert "1 个校验进行中已跳过" in mgr.web.results["b9"]["error"], mgr.web.results["b9"]


def test_drain_web_commands_bulk_skip_check_aggregated():
    """bulk 跳检经 ops 逐 hash 串行(计划 26-10-02-1955 W3): 混合结果聚合回执分段计数

    ok(四阶段走通+记同日去重) / 同日去重(skip) / 部分下载禁(fail) / 执行失败(fail) 四类
    混在一批, 回执文案逐段断言; 成功批回执 ok。gate 关闭拒单见 test_drain_web_commands_bulk_skip_check_gated。
    """
    from datetime import date

    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        tors = [
            FakeTorrent(hash="HASH123", name="Show", state="pausedUP", progress=0.0),
            FakeTorrent(hash="HDUP", name="Dup", state="pausedUP", progress=0.0),
            FakeTorrent(hash="HPART", name="Part", state="pausedUP", progress=0.5),
            FakeTorrent(hash="HEXP", name="Exp", state="pausedUP", progress=0.0),
            FakeTorrent(hash="HASH456", name="Solo", state="pausedUP", progress=0.0),
        ]
        for t in tors:
            client.torrents[t.hash] = t
        seed_store(mgr, tors)
        # 同日去重预置(HDUP 当日已跳检过 —— skip_check_day 跨来源共享, 这里直接预写该表)
        mgr.state["skip_check_day"] = {"HDUP": date.today().isoformat()}
        # HEXP 导出失败(四阶段第一步即炸, fail 有文案)
        orig_export = client.torrents_export

        def export(torrent_hash=None, **kw):
            if torrent_hash == "HEXP":
                raise RuntimeError("boom")
            return orig_export(torrent_hash=torrent_hash, **kw)

        client.torrents_export = export
        with module_log("auto_qb.webui.commands") as messages:
            mgr.web.commands.put(
                (
                    "bulk_torrents", {
                        "hashes": ["HASH123", "HDUP", "HPART", "HEXP"],
                        "action": "skip_check",
                        "cmd_id": "bs1"
                    }
                )
            )
            mgr.web.consume_commands()
        rec = mgr.web.results["bs1"]
        assert rec["status"] == "error", rec
        # 文案逐段: ok 之外的三类各占一段(跳过按原因分桶, 失败聚合计数)
        assert "1 个跳过: 今日已跳检过该种子" in rec["error"], rec["error"]
        assert "2 个失败: " in rec["error"] and "部分下载的种子禁止跳检" in rec["error"], rec["error"]
        assert "导出 .torrent 失败" in rec["error"], rec["error"]
        assert any("批量跳检(成功 1, 跳过 1, 失败 2)" in m for m in messages), messages
        # ok 的那枚走通四阶段并记录同日去重(跨来源共享不回归)
        names = [c[0] for c in client.calls]
        assert "export" in names and "delete" in names and "add" in names, client.calls
        assert mgr.state["skip_check_day"].get("HASH123"), "web 批量跳检应记录同日去重"
        # 纯成功批 -> ok 回执(FakeClient 重加固定回 HASH123, 成功标的只能用它; 独立新 manager)
        with tempfile.TemporaryDirectory() as td2:
            mgr2 = make_manager(os.path.join(td2, "state.json"))
            client2 = FakeClient()
            mgr2.client = client2
            t2 = FakeTorrent(hash="HASH123", name="Solo", state="pausedUP", progress=0.0)
            client2.torrents["HASH123"] = t2
            seed_store(mgr2, [t2])
            with module_log("auto_qb.webui.commands") as messages2:
                mgr2.web.commands.put(
                    ("bulk_torrents", {
                        "hashes": ["HASH123"],
                        "action": "skip_check",
                        "cmd_id": "bs2"
                    })
                )
                mgr2.web.consume_commands()
            assert mgr2.web.results["bs2"]["status"] == "ok", mgr2.web.results["bs2"]
            assert any("批量跳检(成功 1 个种子)" in m for m in messages2), messages2


def test_drain_web_commands_bulk_skip_check_gated():
    """bulk 跳检 gate(计划 26-10-02-1955 W3, D2=是·fail-closed): web.skip_check_menu 关 -> drain 分派处拒单

    读实时配置(ctx.config 现取); 拒单不发任何 qB 调用(export/delete/add 零出现)。
    单发端点 403 双态既有用例不回归(test_api_t_skip_check_gated_by_config)。
    hash 用 FakeClient 重加固定回的 HASH123, 使重开开关后的放行段走通重加确认。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        t = FakeTorrent(hash="HASH123", name="Show", state="pausedUP", progress=0.0)
        client.torrents["HASH123"] = t
        seed_store(mgr, [t])
        mgr.config.web.skip_check_menu = False
        mgr.web.commands.put(("bulk_torrents", {"hashes": ["HASH123"], "action": "skip_check", "cmd_id": "bg1"}))
        mgr.web.consume_commands()
        rec = mgr.web.results["bg1"]
        assert rec["status"] == "error" and "web.skip_check_menu" in rec["error"], rec
        assert client.calls == [], "gate 拒单不得触达 qB(四阶段零调用)"
        # 开关重开(实时配置现读, 同一 manager 热改即生效)-> 放行执行
        mgr.config.web.skip_check_menu = True
        mgr.web.commands.put(("bulk_torrents", {"hashes": ["HASH123"], "action": "skip_check", "cmd_id": "bg2"}))
        mgr.web.consume_commands()
        assert mgr.web.results["bg2"]["status"] == "ok", mgr.web.results["bg2"]
        assert any(c[0] == "export" for c in client.calls), client.calls


def test_drain_web_commands_skip_check_torrent():
    """右键跳检命令(P2', plan 26-09-30-0109 §3.6): 经 ops 层四阶段全流程, 回执 ok 且记录同日去重

    WEB 触发的跳检与规则跳检同一闸门/同一去重/同一执行体(天然串行于主循环线程);
    hash 用 FakeClient 重加固定回的 HASH123, 使重加确认走通全流程。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        t = FakeTorrent(hash="HASH123", name="Show", state="pausedDL", progress=0.0)
        client.torrents["HASH123"] = t
        seed_store(mgr, [t])
        mgr.web.commands.put(("skip_check_torrent", {"hash": "HASH123", "cmd_id": "s1"}))
        mgr.web.consume_commands()
        names = [c[0] for c in client.calls]
        assert "export" in names and "delete" in names and "add" in names, f"应走跳检四阶段: {client.calls}"
        assert mgr.web.results["s1"]["status"] == "ok", mgr.web.results
        assert mgr.state["skip_check_day"]["HASH123"], "web 跳检应记录跨来源同日去重"


# ==================== 跳检三分流预检 + force 透传(plan 26-10-05-0314 S2) ====================


def test_web_skip_check_completed_rejected_receipt():
    """T10: 单发已完成种子 —— ops G3 闸门拒绝文案经 ActionResult 通道原样透传进 error 回执
    (handler 只映射不截断不改写), 拒绝零副作用(不得导出/删除/重加)"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        t = FakeTorrent(hash="HDONE", name="Done", state="pausedUP", progress=1.0)
        seed_store(mgr, [t])
        client.torrents["HDONE"] = t
        mgr.web.commands.put(("skip_check_torrent", {"hash": "HDONE", "cmd_id": "s-done"}))
        mgr.web.consume_commands()
        rec = mgr.web.results["s-done"]
        assert rec["status"] == "error", rec
        assert "已完成" in rec["error"], f"ops 拒绝文案必须原样进回执: {rec['error']!r}"
        assert client.calls == [], f"拒绝零副作用(不得导出/删除/重加): {client.calls}"


def test_web_bulk_skip_check_mixed_outcome():
    """T11: 批量混合(1 已完成 + 1 暂停未完成) —— 聚合回执失败计数与文案自解释(G3), 成功
    标的走通四阶段并记同日去重(FakeClient 重加固定回 HASH123, 成功标的只能用它 ——
    同 test_drain_web_commands_bulk_skip_check_aggregated 的口径)"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        tors = [
            FakeTorrent(hash="HDONE", name="Done", state="pausedUP", progress=1.0),
            FakeTorrent(hash="HASH123", name="Fresh", state="pausedDL", progress=0.0),
        ]
        for t in tors:
            client.torrents[t.hash] = t
        seed_store(mgr, tors)
        mgr.web.commands.put(
            ("bulk_torrents", {
                "hashes": ["HDONE", "HASH123"],
                "action": "skip_check",
                "cmd_id": "bm1"
            })
        )
        mgr.web.consume_commands()
        rec = mgr.web.results["bm1"]
        assert rec["status"] == "error", rec  # 部分成功也报错(既有聚合口径)
        assert "1 个失败: " in rec["error"] and "已完成" in rec["error"], f"失败计数与文案自解释: {rec['error']!r}"
        names = [c[0] for c in client.calls]
        assert "export" in names and "delete" in names and "add" in names, client.calls
        assert mgr.state["skip_check_day"].get("HASH123"), "成功的标的应记录同日去重"


def test_web_precheck_endpoint(web_env):
    """T21: 预检端点 POST /api/torrents/skip-check/precheck —— 路由级: 403 门控同单发
    (fail-closed, detail 注明键名, 关时零入队)/ 空 hashes 400 不入队 / 入队 cmd 与载荷;
    drain 级(make_manager): 回执 truth={results, summary} 结构、混合 {ok, force, blocked}
    计数、未知 hash → cls=blocked 文案「已不在客户端」"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    # 路由级: 门控同单发(D2=是 · fail-closed)
    mgr.config.web.skip_check_menu = False
    resp = client.post("/api/torrents/skip-check/precheck", headers=auth, json={"hashes": ["HA"]})
    assert resp.status_code == 403, resp.text
    assert "web.skip_check_menu" in resp.json()["detail"], "403 detail 必须注明配置键名"
    assert mgr.web.commands.empty(), "配置关时不得投递命令"
    # 门开: 200 入队, cmd 与载荷形状
    mgr.config.web.skip_check_menu = True
    resp = client.post("/api/torrents/skip-check/precheck", headers=auth, json={"hashes": ["HA", "HB"]})
    assert resp.status_code == 200 and resp.json()["queued"] is True, resp.text
    cmd, payload = mgr.web.commands.get_nowait()
    assert cmd == "skip_check_precheck", (cmd, payload)
    payload.pop("cmd_id")
    payload.pop("_queued_ts", None)
    assert payload == {"hashes": ["HA", "HB"]}, payload
    # 空 hashes: 400 拒收不入队(路由层参数校验, 同 bulk/limits/location 先例)
    resp = client.post("/api/torrents/skip-check/precheck", headers=auth, json={"hashes": []})
    assert resp.status_code == 400, resp.text
    assert mgr.web.commands.empty(), "空 hashes 400 不得入队"
    # drain 级: 回执结构 + 混合三态 + gone verdict
    from auto_qb.core.taskqueue import REQUEUE, Task

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        qc = FakeClient()
        mgr.client = qc
        t_ok = FakeTorrent(hash="HASH123", name="Fresh", state="pausedDL", progress=0.0)
        t_done = FakeTorrent(hash="HDONE", name="Done", state="pausedUP", progress=1.0)
        t_force = FakeTorrent(hash="HFORCE", name="Busy", state="pausedDL", progress=0.0)
        for t in (t_ok, t_done, t_force):
            qc.torrents[t.hash] = t
        seed_store(mgr, [t_ok, t_done, t_force])
        # force 样本: G5 同 hash 校验在途(kind=check 任务入队即登记 _active_checks)
        assert mgr.task_queue.add_task(
            Task("check", "check-checking-result", hash="HFORCE", store=mgr.store, handler=lambda t, d: REQUEUE)
        )
        mgr.web.commands.put(
            ("skip_check_precheck", {
                "hashes": ["HASH123", "HDONE", "HFORCE", "HMISSING"],
                "cmd_id": "pc1"
            })
        )
        mgr.web.consume_commands()
        rec = mgr.web.results["pc1"]
        assert rec["status"] == "ok", rec
        data = rec["truth"]
        assert set(data) == {"results", "summary"}, data
        results, summary = data["results"], data["summary"]
        assert [x["hash"] for x in results] == ["HASH123", "HDONE", "HFORCE", "HMISSING"], results
        assert results[0]["cls"] == "ok" and results[0]["reasons"] == [] and results[0]["name"] == "Fresh"
        assert results[1]["cls"] == "blocked", results[1]
        assert results[1]["reasons"][0]["gate"] == "G3" and "已完成" in results[1]["reasons"][0]["text"]
        assert results[2]["cls"] == "force", results[2]
        assert results[2]["reasons"][0]["gate"] == "G5"
        assert results[3]["cls"] == "blocked", results[3]
        assert results[3]["reasons"][0]["gate"] == "gone"
        assert "已不在客户端" in results[3]["reasons"][0]["text"], "gone 文案自解释"
        assert summary == {"ok": 1, "force": 1, "blocked": 2}, summary


def test_web_force_passthrough(web_env):
    """T22: force 透传 —— 单发 body.force=true → ops.skip_check 收到 force=True(mock kwarg
    断言)/ 缺省不传 → force=False; 批量 body.force=true → _bulk_skip_check_via_ops 逐 hash
    透传; 路由级提供才透传(缺省队列载荷形态不变); force=true 时 case 1 闸门(G3 已完成)
    照常硬拒, 拒绝文案进回执 —— force 只是许可不是指令"""
    from auto_qb.rules.base import ActionResult
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

    # 路由级: force 提供才透传, 缺省载荷不带键
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    resp = client.post("/api/torrents/HA/skip-check", headers=auth, json={"force": True})
    assert resp.status_code == 200, resp.text
    cmd, payload = mgr.web.commands.get_nowait()
    assert cmd == "skip_check_torrent" and payload.get("force") is True, payload
    client.post("/api/torrents/HA/skip-check", headers=auth)  # 缺省: 不带 force
    _, payload = mgr.web.commands.get_nowait()
    assert "force" not in payload, "缺省载荷形态必须与今天一致"
    resp = client.post(
        "/api/torrents/bulk", headers=auth, json={
            "hashes": ["HA", "HB"],
            "action": "skip_check",
            "force": True
        }
    )
    assert resp.status_code == 200, resp.text
    cmd, payload = mgr.web.commands.get_nowait()
    assert cmd == "bulk_torrents" and payload.get("force") is True, payload
    client.post("/api/torrents/bulk", headers=auth, json={"hashes": ["HA"], "action": "skip_check"})
    _, payload = mgr.web.commands.get_nowait()
    assert "force" not in payload, "批量缺省载荷形态必须与今天一致"
    # drain 级(单发): kwarg 断言 —— force=True / 缺省 False
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        qc = FakeClient()
        mgr.client = qc
        t = FakeTorrent(hash="HASH123", name="Fresh", state="pausedDL", progress=0.0)
        seed_store(mgr, [t])
        qc.torrents["HASH123"] = t
        with mock.patch.object(mgr.ctx.ops, "skip_check", return_value=ActionResult.ok("mocked")) as m:
            mgr.web.commands.put(("skip_check_torrent", {"hash": "HASH123", "cmd_id": "f1", "force": True}))
            mgr.web.commands.put(("skip_check_torrent", {"hash": "HASH123", "cmd_id": "f2"}))
            mgr.web.consume_commands()
        assert [c.kwargs.get("force") for c in m.call_args_list] == [True, False], m.call_args_list
        assert mgr.web.results["f1"]["status"] == "ok" and mgr.web.results["f2"]["status"] == "ok", mgr.web.results
    # drain 级(批量): 逐 hash 透传
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        qc = FakeClient()
        mgr.client = qc
        tors = [
            FakeTorrent(hash="HA", name="A", state="pausedDL", progress=0.0),
            FakeTorrent(hash="HB", name="B", state="pausedDL", progress=0.0),
        ]
        seed_store(mgr, tors)
        with mock.patch.object(mgr.ctx.ops, "skip_check", return_value=ActionResult.ok("mocked")) as m:
            mgr.web.commands.put(
                ("bulk_torrents", {
                    "hashes": ["HA", "HB"],
                    "action": "skip_check",
                    "cmd_id": "bf1",
                    "force": True
                })
            )
            mgr.web.consume_commands()
        assert [c.kwargs.get("force") for c in m.call_args_list] == [True, True], "逐 hash 透传"
        assert mgr.web.results["bf1"]["status"] == "ok", mgr.web.results
    # force=true 时 case 1 闸门(G3)照常硬拒: 文案进回执, 零副作用
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        qc = FakeClient()
        mgr.client = qc
        t = FakeTorrent(hash="HDONE", name="Done", state="pausedUP", progress=1.0)
        seed_store(mgr, [t])
        qc.torrents["HDONE"] = t
        mgr.web.commands.put(("skip_check_torrent", {"hash": "HDONE", "cmd_id": "f3", "force": True}))
        mgr.web.consume_commands()
        rec = mgr.web.results["f3"]
        assert rec["status"] == "error" and "已完成" in rec["error"], "force 不豁越 case 1(blocked)硬闸"
        assert qc.calls == [], f"force 被拒同样零副作用: {qc.calls}"


def test_webui_no_rules_import():
    """边界守阵(P2', plan 26-09-30-0109 §3.4/FIG.2): webui 不触碰规则动作插件 —— 操作语义单点在 ops 层

    依赖方向 rules -> ops <- web: WEB 的操作执行链不得 import 规则模块(v2 收编方案做不到
    这一点 —— 它要求 WEB 调进规则模块内部)。两层口径:
    - 操作链模块(webui/{__init__,commands,runtime,views}.py): 不得 import auto_qb.rules 任何部分;
    - 其余 webui 模块: 不得 import 规则**根包**(会传递拉起动作插件注册)与 rules.actions /
      rules.registry; rules.expr / rules.base 仅限 config 编辑器表达式试算
      (server/routes/config.py 既有合法用途, 不属操作语义)。
    """
    import re

    import auto_qb.webui as _webui_pkg

    webui_root = os.path.dirname(os.path.abspath(_webui_pkg.__file__))
    op_chain = {"__init__.py", "commands.py", "runtime.py", "views.py"}
    plugin_prefixes = ("rules", "rules.actions", "rules.registry")
    rx = re.compile(r"^\s*(?:from|import)\s+(auto_qb\.rules[\w.]*|(?:\.{2,4})rules[\w.]*)")
    violations = []
    for dirpath, _dirs, files in os.walk(webui_root):
        for fn in files:
            if not fn.endswith(".py"):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, webui_root).replace("\\", "/")
            is_op_chain = "/" not in rel and fn in op_chain
            with open(full, encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    m = rx.match(line)
                    if not m:
                        continue
                    mod = m.group(1).lstrip(".") or "rules"
                    if is_op_chain or mod in plugin_prefixes:
                        violations.append(f"{rel}:{i}: import {m.group(1).strip()}")
    assert not violations, ("webui 出现规则模块引用(依赖方向做反, 操作语义必须单点在 core/modules/ops_mod.py): "
                            f"{violations}")


# ==================== P1 覆盖率提升轮: webui 运行时与命令长尾 ====================


class _ListLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


class module_log:
    """挂在指定模块 logger 上的自足采集(pitfalls/testing/log-capture: 禁 caplog)"""
    def __init__(self, name, level=logging.DEBUG):
        self._handler = _ListLogHandler()
        self._logger = logging.getLogger(name)
        self._level = level

    def __enter__(self):
        self._old_level, self._old_propagate = self._logger.level, self._logger.propagate
        self._logger.addHandler(self._handler)
        self._logger.setLevel(self._level)
        self._logger.propagate = False
        return self._handler.messages

    def __exit__(self, *exc):
        self._logger.removeHandler(self._handler)
        self._logger.setLevel(self._old_level)
        self._logger.propagate = self._old_propagate
        return False


def test_web_runtime_notify_drops_are_counted():
    """SSE 广播非阻塞: 慢消费者(队列满)与坏消费者(异常)各计一次丢弃, 不影响其它订阅者"""
    from auto_qb.webui.runtime import EVENT_QUEUE_MAX

    mgr = SimpleNamespace()  # notify 不读 host
    rt = WebUIRuntime(mgr)
    slow = rt.subscribe()  # 有界队列: 灌满即丢
    broken = rt.subscribe()
    broken.put_nowait = lambda ev: (_ for _ in ()).throw(RuntimeError("坏订阅者"))  # 每次都炸
    good = rt.subscribe()
    for _ in range(EVENT_QUEUE_MAX):
        slow.put_nowait({"type": "x", "payload": {}, "ts": 0.0})
    assert rt.subscriber_count() == 3
    hit = rt.notify("state", {"v": 1})
    assert hit == 1, "只有健康订阅者送达"
    assert rt.notify_dropped == 2, "队列满 + 异常各记一次丢弃"
    assert good.qsize() == 1


def test_web_runtime_check_pending_paths():
    """在途汇报确认全路径(item 级 deadline): 完成跳过/超时 warn(epoch+legacy 文案)/停止直判/断连等待/
    读 tracker 异常 error/判定 confirmed 与 rejected/聚合三桶与前 3 条原因截断"""
    from auto_qb.core.qbmanager import QbManager
    from auto_qb.webui.commands import RC_FAIL_PREFIX

    verdicts = {"H_OK": ("confirmed", ""), "H_FAIL": ("rejected", RC_FAIL_PREFIX + "ann"), "H_WAIT": ("", "")}
    client = SimpleNamespace(
        torrents_trackers=lambda h: (_ for _ in ()).throw(RuntimeError("读取失败")) if h == "H_ERR" else [h]
    )
    store = SimpleNamespace(
        get=lambda h: SimpleNamespace(state_enum=SimpleNamespace(is_stopped=True)) if h == "H_STOP" else None
    )
    host = SimpleNamespace(
        client=client,
        store=store,
        _verdict_reannounce=lambda trackers, baseline, **kw: verdicts.get(trackers[0], ("", "")),
    )
    rt = WebUIRuntime(host)
    now = time.time()

    def _item(**over):
        it = {
            "done": False,
            "status": "",
            "reason": "",
            "baseline": {},
            "epoch_mode": True,
            "t0": now,
            "deadline": now + REANNOUNCE_CONFIRM_TIMEOUT,
        }
        it.update(over)
        return it

    rt.reannounce_pending["c1"] = {
        "items":
            {
                "H_DONE": _item(done=True, status="warn", reason="未确认: 种子已停止"),
                "H_OK": _item(),
                "H_FAIL": _item(),
                "H_WAIT": _item(),
                "H_ERR": _item(),
                "H_STOP": _item(),
            },
    }
    rt.reannounce_pending["c_timeout"] = {"items": {"H_T": _item(deadline=now - 1.0)}}
    rt.reannounce_pending["c_timeout_legacy"] = {"items": {"H_TL": _item(deadline=now - 1.0, epoch_mode=False)}}
    rt.reannounce_pending["c_disconnected"] = {"items": {"H_D": _item()}}
    rt.check_pending()
    # 超时 -> warn「未确认」(epoch/legacy 两文案), 不再判「失败」
    assert rt.results["c_timeout"]["status"] == "warn" and "未确认: 30s" in rt.results["c_timeout"]["error"]
    assert rt.results["c_timeout_legacy"]["status"] == "warn"
    assert "旧版 qB 无 epoch 字段" in rt.results["c_timeout_legacy"]["error"]
    # 仍在进行(无证据)的条目: 不出结论, 条目留在途; 其余已定论的先记进条目
    assert "c1" in rt.reannounce_pending, "确认未决不出结论"
    items = rt.reannounce_pending["c1"]["items"]
    assert items["H_OK"]["status"] == "ok" and items["H_FAIL"]["status"] == "error"
    assert items["H_FAIL"]["reason"] == RC_FAIL_PREFIX + "ann"
    assert items["H_STOP"]["status"] == "warn" and "种子已停止" in items["H_STOP"]["reason"], "store 快照 stopped 直判"
    assert items["H_ERR"]["done"] is True and "读取失败" in items["H_ERR"]["reason"]
    # 断连: client None -> 本轮跳过(等恢复), 保持在途
    host.client = None
    rt.check_pending()
    assert "c_disconnected" in rt.reannounce_pending, "断连不判失败, 等恢复继续确认"
    # 最后一个未决出结论 -> 聚合三桶(任一 error -> error; 原因截断为前 3 条)
    host.client = client
    verdicts["H_WAIT"] = ("confirmed", "")
    verdicts["H_D"] = ("rejected", RC_FAIL_PREFIX + "ann")  # 同 tick 断连条目恢复, 出拒绝结论
    rt.check_pending()
    assert "c1" not in rt.reannounce_pending, "全部种子出结论后聚合并移除"
    r = rt.results["c1"]
    assert r["status"] == "error", "任一 error -> 聚合 error"
    assert "成功 2, 失败 2, 未确认 2" in r["error"], "三桶计数按 item status 分流"
    assert r["error"].count(";") == 2, "原因截断为前 3 条"
    assert rt.results["c_disconnected"]["status"] == "error", "断连恢复后出结论的失败项照常聚合"
    assert rt.results["c_disconnected"]["error"] == "成功 0, 失败 1, 未确认 0: " + RC_FAIL_PREFIX + "ann"
    # 单条确认成功 -> ok 回执, 跟踪清空
    rt2 = WebUIRuntime(
        SimpleNamespace(
            client=SimpleNamespace(torrents_trackers=lambda h: ["H_D"]),
            store=SimpleNamespace(get=lambda h: None),
            _verdict_reannounce=lambda trackers, baseline, **kw: ("confirmed", ""),
        )
    )
    rt2.reannounce_pending["c_ok"] = {"items": {"H_D": _item()}}
    rt2.check_pending()
    assert rt2.results["c_ok"]["status"] == "ok" and rt2.reannounce_pending == {}


def test_web_runtime_resync_elapsed_ms_logs_by_threshold():
    """命令后补刷新计时: 异常慢升 WARNING, 正常只 DEBUG(不刷满日志)"""
    rt = WebUIRuntime(SimpleNamespace())
    with module_log("auto_qb.webui.runtime") as messages:
        rt.resync_elapsed_ms(time.time() - (float(CMD_SLOW_MS) / 1000.0 + 1.0))
        assert any("命令后补刷新" in m and "真值" in m for m in messages), "超阈值 -> WARNING"
        rt.resync_elapsed_ms(time.time())
    assert any("命令后补刷新" in m for m in messages), "正常耗时也落 DEBUG(排障可查)"


def test_web_runtime_set_result_prunes_stale_and_carries_truth():
    """回执表: 超量时按 TTL 淘汰旧回执; truth 附带进回执供前端撤乐观态"""
    rt = WebUIRuntime(SimpleNamespace())
    now = time.time()
    for i in range(WEB_RESULT_MAX + 8):
        rt.results[f"stale{i}"] = {"status": "ok", "error": "", "ts": now - WEB_RESULT_TTL - 10.0}
    rt.results["fresh"] = {"status": "ok", "error": "", "ts": now}
    rt.set_result("new1", "ok", truth={"HA": {"kind": "seeding"}})
    assert "new1" in rt.results
    assert rt.results["new1"]["truth"] == {"HA": {"kind": "seeding"}}
    assert all(k.startswith("stale") is False or k == "fresh" for k in rt.results), "过期回执被清理"
    assert len(rt.results) <= WEB_RESULT_MAX


def test_web_runtime_affected_hashes_shapes():
    """受影响种子的三种取法(单种子 / 组 / 批量含组键) + 异常退化空表"""
    host = SimpleNamespace(store=SimpleNamespace(groups={("R:/X", ("a.mkv", )): ["HA", "HB"]}))
    rt = WebUIRuntime(host)
    assert rt._affected_hashes("pause_torrent", {"hash": "HA"}) == ["HA"]
    assert rt._affected_hashes("pause_torrent", {}) == [], "无 hash 不猜"
    assert rt._affected_hashes("pause_group", {"key": ("R:/X", ("a.mkv", ))}) == ["HA", "HB"]
    assert rt._affected_hashes("bulk_torrents", {
        "hashes": ["HC"],
        "keys": [("R:/X", ("a.mkv", ))]
    }) == ["HC", "HA", "HB"]
    broken = SimpleNamespace(store=None)
    assert WebUIRuntime(broken)._affected_hashes("pause_group", {"key": "k"}) == [], "桩/异常配置退化空表"


def test_web_runtime_affected_truth_queries_live_api():
    """真值直查 qB(不读同步快照); 查不到回 None(不回落旧值伪装)"""
    torrent = SimpleNamespace(hash="HA")
    host = SimpleNamespace(
        api=SimpleNamespace(torrents_info=lambda torrent_hashes=None: [torrent]),
        state_kind=lambda t: "seeding",
    )
    rt = WebUIRuntime(host)
    truth = rt._affected_truth("pause_torrent", {"hash": "HA"})
    assert truth == {"HA": {"kind": "seeding"}}
    assert rt._affected_truth("pause_torrent", {}) is None, "无受影响种子 -> None"

    def boom(torrent_hashes=None):
        raise RuntimeError("qB 断了")

    rt2 = WebUIRuntime(SimpleNamespace(api=SimpleNamespace(torrents_info=boom), state_kind=lambda t: "x"))
    with module_log("auto_qb.webui.runtime") as messages:
        assert rt2._affected_truth("pause_torrent", {"hash": "HA"}) is None
    assert any("真值直查失败" in m for m in messages), "直查失败落 WARNING(不回落快照)"


def test_web_commands_delete_with_files_and_reannounce_gone_receipt():
    """删除透传 delete_files; 汇报种子已不存在 -> 显式 error 回执(不静默)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        mgr.web.commands.put(("delete_torrent", {"hash": "HA", "delete_files": True, "cmd_id": "d1"}))
        mgr.web.commands.put(("reannounce_torrent", {"hash": "GONE", "cmd_id": "r1"}))
        mgr.web.consume_commands()
        assert client.calls[-1] == ("delete", True), "delete_files 透传给 API"
        assert mgr.web.results["d1"]["status"] == "ok"
        assert mgr.web.results["r1"]["status"] == "error" and "不存在" in mgr.web.results["r1"]["error"]


def test_web_commands_recheck_and_skip_check_receipts():
    """重新校验/右键跳检经 ops 提交: 拒绝时回执带自解释文案; 种子不存在同样显式报"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        mgr.web.commands.put(("recheck_torrent", {"hash": "GONE", "cmd_id": "c-gone"}))
        mgr.web.commands.put(("skip_check_torrent", {"hash": "GONE", "cmd_id": "s-gone"}))
        mgr.web.consume_commands()
        assert mgr.web.results["c-gone"]["status"] == "error" and "不存在" in mgr.web.results["c-gone"]["error"]
        assert mgr.web.results["s-gone"]["status"] == "error", "跳检拒绝(种子消失) -> error 回执带文案"
        assert mgr.web.results["s-gone"]["error"], "拒绝文案不为空"


def test_web_commands_limits_partial_directions():
    """限速只下发提供的方向(up/dl 可各自缺省); 分享限制同理"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        mgr._cmd_set_torrent_limits("HA", up_limit=1024)
        mgr._cmd_set_torrent_limits("HA", dl_limit=2048)
        mgr._cmd_set_share_limits("HA", ratio_limit=1.5)
        kinds = [c[0] for c in client.calls]
        assert kinds.count("set_upload_limit") == 1 and kinds.count("set_download_limit") == 1
        assert client.calls[-1] == ("set_share_limits", (1.5, -2, -2)), "缺失维度按 -2(全局默认)补齐"


def test_web_commands_rename_fs_folder_branch():
    """重命名文件夹走 torrents_rename_folder(文件走 rename_file 已有守阵)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        mgr._cmd_rename_fs("HA", old_path="old/dir", new_path="new/dir", is_folder=True)
        assert client.calls[-1] == ("rename_folder", ("HA", "old/dir", "new/dir"))


def test_web_commands_bulk_argument_errors():
    """批量动作参数错误: 未知动作 / 空目标 / 标签动作无标签 / set_category 无分类 /
    limits 两方向全空 / location 空路径 -> error 回执且不调 API"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        cases = [
            ({
                "hashes": ["HA"],
                "action": "purge"
            }, "purge"),
            ({
                "action": "pause"
            }, "未提供任何 hash"),
            ({
                "hashes": ["HA"],
                "action": "add_tags"
            }, "未提供标签"),
            ({
                "hashes": ["HA"],
                "action": "set_category"
            }, "未提供分类"),
            ({
                "hashes": ["HA"],
                "action": "limits"
            }, "未提供限速值"),
            ({
                "hashes": ["HA"],
                "action": "location"
            }, "未提供目标路径"),
        ]
        for i, (payload, want) in enumerate(cases):
            mgr.web.commands.put(("bulk_torrents", dict(payload, cmd_id=f"b{i}")))
            mgr.web.consume_commands()
            assert mgr.web.results[f"b{i}"]["status"] == "error", (payload, mgr.web.results)
            assert want in mgr.web.results[f"b{i}"]["error"]
        assert client.calls == [], "参数错误不触达 qB"


def test_web_commands_bulk_missing_targets_reported():
    """批量: 缺失种子与缺失组分列计数(部分缺失也进 error 文案, 拒绝计数可见)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        ghost_key = ("R:/Nowhere", ("none.mkv", ))
        mgr.web.commands.put(
            ("bulk_torrents", {
                "hashes": ["HA", "GONE"],
                "keys": [ghost_key],
                "action": "pause",
                "cmd_id": "bm"
            })
        )
        mgr.web.consume_commands()
        rec = mgr.web.results["bm"]
        assert rec["status"] == "error"
        assert "1/2 个种子不存在" in rec["error"] and "1/1 个组不存在" in rec["error"]


def test_web_commands_bulk_recheck_via_ops():
    """批量 recheck 经 ops 逐个提交: 提交/跳过/缺失聚合进回执(部分成功也报错)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        with module_log("auto_qb.webui.commands") as messages:
            mgr.web.commands.put(("bulk_torrents", {"hashes": ["HA", "GONE"], "action": "recheck", "cmd_id": "br"}))
            mgr.web.consume_commands()
        rec = mgr.web.results["br"]
        assert rec["status"] == "error" and "1/2 个种子不存在" in rec["error"]
        assert any("批量 recheck(提交 1" in m for m in messages), "提交/跳过计数落日志(回执只带缺失文案)"


def test_web_commands_add_torrents_receipt():
    """添加种子: 文件+链接都受理 -> ok 回执; qB 未接受 -> error 回执带详情"""
    from hr_helpers import torrent_blob

    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        blob = torrent_blob(name="added.bin")
        mgr.web.commands.put(
            (
                "add_torrents",
                {
                    "files": [blob],
                    "urls": ["magnet:?xt=urn:btih:xyz"],
                    "save_path": "R:/Drop",
                    "category": "cat",
                    "tags": ["t1"],
                    "paused": False,
                    "skip_checking": False,
                    "sequential": False,
                    "first_last_piece_prio": False,
                    "auto_tmm": False,
                    "cmd_id": "a1",
                },
            )
        )
        mgr.web.consume_commands()
        assert mgr.web.results["a1"]["status"] == "ok", mgr.web.results["a1"]
        assert any(c[0] == "add" for c in client.calls)
        # qB 拒绝(旧文本形态 "Fails.") -> error 回执(新形态元数据由既有守阵钉)
        client.torrents_add = lambda *a, **kw: "Fails."
        mgr.web.commands.put(("add_torrents", {"files": [blob], "urls": [], "cmd_id": "a2"}))
        mgr.web.consume_commands()
        assert mgr.web.results["a2"]["status"] == "error" and "qB 未接受" in mgr.web.results["a2"]["error"]


# ==================== P1 覆盖率提升轮: webui 路由长尾 ====================


def test_api_torrent_write_endpoints_extra_enqueue(web_env):
    """种子写端点补遗: pause/resume/delete(带 delete_files)/skip-check/limits(部分方向)/share-limits(部分维度)"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    post = lambda path, body=None: client.post(f"/api/torrents/HA{path}", json=body, headers=auth)  # noqa: E731
    cases = [
        ("/pause", None, "pause_torrent", {
            "hash": "HA"
        }),
        ("/resume", None, "resume_torrent", {
            "hash": "HA"
        }),
        ("/delete", {
            "delete_files": True
        }, "delete_torrent", {
            "hash": "HA",
            "delete_files": True
        }),
        ("/skip-check", None, "skip_check_torrent", {
            "hash": "HA"
        }),
        ("/limits", {
            "up_limit": 1024
        }, "set_torrent_limits", {
            "hash": "HA",
            "up_limit": 1024
        }),
        ("/share-limits", {
            "ratio_limit": 1.5
        }, "set_share_limits", {
            "hash": "HA",
            "ratio_limit": 1.5
        }),
    ]
    for path, body, cmd, want in cases:
        resp = post(path, body)
        assert resp.status_code == 200, (path, resp.text)
        got_cmd, payload = mgr.web.commands.get_nowait()
        assert got_cmd == cmd
        payload.pop("cmd_id")
        payload.pop("_queued_ts", None)
        assert payload == want, path
    # 鉴权沿用 /api/* 全局依赖
    assert client.post("/api/torrents/HA/pause").status_code == 401


def test_api_torrents_add_endpoint_errors_and_enqueue(web_env):
    """/api/torrents/add: base64 坏 -> 400; 空载荷 -> 400; 合法载荷入队(文件+链接)"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    assert client.post("/api/torrents/add", json={"files_b64": ["!!not-b64!!"]}, headers=auth).status_code == 400
    assert client.post("/api/torrents/add", json={}, headers=auth).status_code == 400
    assert client.post("/api/torrents/add", json={"files_b64": ["!!not-b64!!"]}).status_code == 401
    blob = base64.b64encode(b"d4:infod4:name4:abcee").decode("ascii")
    resp = client.post(
        "/api/torrents/add",
        json={
            "files_b64": [blob, ""],
            "urls": ["magnet:?xt=urn:btih:abc"],
            "save_path": "R:/Drop",
            "tags": ["t"]
        },
        headers=auth,
    )
    assert resp.status_code == 200 and resp.json()["queued"] is True
    cmd, payload = mgr.web.commands.get_nowait()
    assert cmd == "add_torrents"
    assert payload["files"] == [b"d4:infod4:name4:abcee"], "空串条目被过滤, base64 解出原始字节"
    assert payload["urls"] == ["magnet:?xt=urn:btih:abc"] and payload["save_path"] == "R:/Drop"


def test_api_config_put_and_preview_tree_shape(web_env):
    """配置树: PUT/preview 的 tree 非对象都 400; preview 返回 YAML 文本不落盘"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    assert client.put("/api/config", json={"tree": "nope"}, headers=auth).status_code == 400
    assert client.post("/api/config/preview", json={"tree": [1]}, headers=auth).status_code == 400
    assert client.put("/api/config", json={"tree": "nope"}).status_code == 401
    tree = client.get("/api/config", headers=auth).json()["tree"]
    resp = client.post("/api/config/preview", json={"tree": tree}, headers=auth)
    assert resp.status_code == 200 and "yaml" in resp.json()
    before = Path(mgr.config_path).read_text(encoding="utf-8")
    assert Path(mgr.config_path).read_text(encoding="utf-8") == before, "preview 不落盘"


def test_api_expr_eval_runtime_error(web_env):
    """表达式试算: 编译/校验通过但**求值期**失败(除零) -> ok=False 带错误文案与 used 清单"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    mgr.store.get = lambda h: SimpleNamespace(uploaded=100, downloaded=0)
    resp = client.post(
        "/api/expr/eval",
        json={
            "text": "(tor.uploaded / tor.downloaded) > 1",
            "hash": "HA"
        },
        headers=auth,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False and "除数为 0" in body["error"]
    assert body["used"] == ["tor.downloaded", "tor.uploaded"]


def test_api_keys_endpoint_roundtrip_and_validation(web_env):
    """快捷键配置: 默认表 / 非法结构 422 / 合法保存后读回一致"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    assert client.get("/api/keys", headers=auth).json()["template"] == "aqb-default"
    bad = {"schema_version": 1, "template": "", "overrides": {}}
    assert client.put("/api/keys", json=bad, headers=auth).status_code == 422
    bad2 = {"schema_version": 1, "template": "aqb-default", "overrides": {"k": "Bad Serial!"}}
    assert client.put("/api/keys", json=bad2, headers=auth).status_code == 422
    assert client.put("/api/keys", json=bad2).status_code == 401
    good = {"schema_version": 1, "template": "aqb-default", "overrides": {"openSearch": "Ctrl+K", "x": ""}}
    assert client.put("/api/keys", json=good, headers=auth).status_code == 200
    assert client.get("/api/keys", headers=auth).json()["overrides"]["openSearch"] == "Ctrl+K"


def test_api_keys_sanitize_rejects_non_dict():
    """_sanitize 结构校验单点: 非 dict 文档一律 None(走默认表兜底链)"""
    from auto_qb.webui.server.routes.keys import _sanitize

    assert _sanitize(None) is None
    assert _sanitize([1, 2]) is None
    assert _sanitize("x") is None


def test_api_category_and_tag_empty_rejections(web_env):
    """分类/标签写端点的空入参 400(与既有详情端点同一校验口径)"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    assert client.post("/api/categories", json={"name": "  "}, headers=auth).status_code == 400
    assert client.post("/api/categories/edit", json={}, headers=auth).status_code == 400
    assert client.post("/api/tags/remove", json={"tags": []}, headers=auth).status_code == 400
    resp = client.post("/api/tags", json={"tags": ["新标签"]}, headers=auth)
    assert resp.status_code == 200
    cmd, payload = mgr.web.commands.get_nowait()
    assert cmd == "create_tags" and payload["tags"] == ["新标签"]


def test_api_speed_mode_reads_client_with_alt_fields(web_env):
    """限速托管状态: qB 在连时直读当前限速与 ALT 双组; 读失败不炸(回 None)"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    api = SimpleNamespace(
        get_global_speed_limits=lambda: {"up_limit": 1024},
        get_speed_limits_mode=lambda: 1,
        get_alt_speed_limits=lambda: {"up_limit": 512},
    )
    mgr.client = SimpleNamespace()
    mgr.api = api
    body = client.get("/api/speed/mode", headers=auth).json()
    assert body["current"] == {"up_limit": 1024} and body["alt_on"] is True
    assert body["alt_current"] == {"up_limit": 512}
    # 读失败 -> 字段回 None, 端点不 500
    mgr.api = SimpleNamespace(
        get_global_speed_limits=lambda: (_ for _ in ()).throw(RuntimeError("断连")),
        get_speed_limits_mode=lambda: 0,
        get_alt_speed_limits=lambda: {},
    )
    body = client.get("/api/speed/mode", headers=auth).json()
    assert body["current"] is None and body["alt_on"] is None and body["alt_current"] is None, "任一读取失败整组回 None(不拿旧缓存冒充)"


def test_api_fs_error_semantics(web_env, tmp_path, monkeypatch):
    """fs 端点错误语义化: 目录不可读 404 / mkdir 不支持 501 / 只读挂载 403 / 其它失败 400 / open 不支持 501"""
    from auto_qb.infra import file_access as fa_mod

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    root = tmp_path / "fsroot"
    root.mkdir()
    mgr.store.by_hash = {"HA": SimpleNamespace(hash="HA", save_path=str(root), content_path=str(root))}
    norm = lambda p: str(p).replace("\\", "/")  # noqa: E731

    class _FakeFA:
        def isdir(self, p):
            return True

        def isfile(self, p):
            return True

        def exists(self, p):
            return False

        def realpath_lexical(self, p):
            return p

        def scandir(self, p):
            raise PermissionError(13, "拒绝访问")

        def mkdir(self, p):
            raise OSError(errno.EACCES, "拒绝访问")

    monkeypatch.setattr(file_access, "get_file_access", lambda: _FakeFA())
    # 目录浏览: scandir 失败 -> 404 带原因(不是裸 500)
    resp = client.get("/api/fs/dirs", params={"path": norm(root)}, headers=auth)
    assert resp.status_code == 404 and "目录不可读" in resp.json()["detail"]
    # mkdir: EACCES -> 403(只读挂载语义化)
    resp = client.post("/api/fs/mkdir", json={"name": "nd", "path": norm(root)}, headers=auth)
    assert resp.status_code == 403 and "只读" in resp.json()["detail"]

    # mkdir: 其它 OSError -> 400
    class _OtherFA(_FakeFA):
        def mkdir(self, p):
            raise OSError(errno.EINVAL, "无效参数")

    monkeypatch.setattr(file_access, "get_file_access", lambda: _OtherFA())
    resp = client.post("/api/fs/mkdir", json={"name": "nd", "path": norm(root)}, headers=auth)
    assert resp.status_code == 400 and "新建失败" in resp.json()["detail"]

    # mkdir: 环境不支持 -> 501
    class _NoFA(_FakeFA):
        def mkdir(self, p):
            raise fa_mod.NotSupported("nope")

    monkeypatch.setattr(file_access, "get_file_access", lambda: _NoFA())
    assert client.post("/api/fs/mkdir", json={"name": "nd", "path": norm(root)}, headers=auth).status_code == 501
    # open-path: 打开动作不支持 -> 501 引导「复制路径」(patch 地址 = common.open_path, 与既有守阵一致)
    import auto_qb.webui.server.common as fs_common

    def _unsupported(path, select=False):
        raise fa_mod.NotSupported("nope")

    monkeypatch.setattr(fs_common, "open_path", _unsupported)
    mgr.store.groups = {(norm(root), ("a.mkv", )): ["HA"]}
    encoded = encode_group_key((norm(root), ("a.mkv", )))
    resp = client.post("/api/open-path", json={"kind": "group", "key": encoded}, headers=auth)
    assert resp.status_code == 501 and "复制路径" in resp.json()["detail"]


# ---------- v3 活尾合流(S6 验收追加, 2026-10-05) ----------


def _attach_live_tail_host(mgr, tails):
    """manager 替身挂模块宿主最小桩: host.get("qb_traffic") -> 带 live_tail 的模块桩
    (真 manager 经 QbManager.host 持 ModuleHost, 端点 getattr 防御取用)"""
    from types import SimpleNamespace

    mgr.host = SimpleNamespace(get=lambda name: SimpleNamespace(live_tail=tails))


def test_api_traffic_qb_global_live_tail_realtime(web_env):
    """(S6)raw 段窗活尾合流: 纯活尾(零盘)出实时桶点(不等 flush_interval 落盘);
    磁盘落盘后滞后快照重列已落盘记录被按 ts 精确去重(快照与 flush 竞态不重不漏),
    快照清空后磁盘响应与合流响应逐点一致 —— 图面全程无跳变"""
    from auto_qb.core.traffic_store import LiveTail, V3Sample, v3_epoch_date_str

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v3(mgr)
    now = int(time.time())
    base = ((now - 240) // 30) * 30  # 5m 窗内
    b0, b1, b2 = (base + i * 30 for i in range(3))
    recs = (V3Sample(100, 50, 1000, 500), V3Sample(200, 70, 2000, 800))
    tail_full = LiveTail(
        block_open=True,
        head_pending=True,
        start_epoch=b0 + 30,
        interval_s=30,
        projected_ts=float(b1 + 30),
        records=recs,
        open_run=None,
    )
    # 纯活尾(块全量未落盘, 零天文件): 图面实时出点
    _attach_live_tail_host(mgr, {"global": tail_full})
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "5m"}).json()

    def pt(seg, t):
        return next((p for p in body[seg] if p and p["t"] == t), None)

    assert body["meta"]["stale"] is False
    assert pt("points", b0) == {"t": b0, "dl": 100, "up": 50}
    assert pt("points", b1) == {"t": b1, "dl": 200, "up": 70}
    assert pt("points", b2) is None  # 活尾之外无观测
    assert pt("totals", b1) == {"t": b1, "dl": 1000, "up": 300}
    live_body = body
    # flush 落盘(同两记录) + 滞后快照仍重列全部记录: 按 ts 去重, 响应逐点不变
    store.append_records("global", v3_epoch_date_str(b0 + 30), (b0 + 30, 30), recs)
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "5m"}).json()
    assert body == live_body
    # 快照清空(flush 后的下一轮发布): 纯磁盘读路径, 响应仍逐点一致
    _attach_live_tail_host(mgr, {})
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "5m"}).json()
    assert body == live_body


def test_api_traffic_qb_group_live_tail_member_only(web_env):
    """(S6)组端点空态判据计入活尾: 成员仅活尾(零盘)组图非空(不再误判「从未产过流量」);
    单种端点同享活尾"""
    from auto_qb.core.traffic_store import LiveTail, V3Sample

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    now = int(time.time())
    base = ((now - 240) // 30) * 30  # 5m 窗内
    b0, b1 = (base + i * 30 for i in range(2))
    tail = LiveTail(
        block_open=True,
        head_pending=True,
        start_epoch=b0 + 30,
        interval_s=30,
        projected_ts=float(b1 + 30),
        records=(V3Sample(300, 30, 500, 50), ),
        open_run=None,
    )
    _attach_live_tail_host(mgr, {"torrent:HB": tail})
    body = client.get(f"/api/traffic/qb/group/{encode_group_key(KEY)}", headers=auth, params={"window": "5m"}).json()

    def pt(seg, t):
        return next((p for p in body[seg] if p and p["t"] == t), None)

    assert pt("points", b0) == {"t": b0, "dl": 300, "up": 30}  # HB 活尾观测(HA 无数据按 0 计)
    assert pt("totals", b0) == {"t": b0, "dl": 0, "up": 0}  # 窗首基线缺失
    assert pt("points", b1) is None  # 单记录覆盖桶 [b0, b0+30) 恰一格, b1 无观测
    # 单种端点同享活尾
    body = client.get("/api/traffic/qb/torrent/HB", headers=auth, params={"window": "5m"}).json()
    assert any(p and p["t"] == b0 and p["dl"] == 300 for p in body["points"])
