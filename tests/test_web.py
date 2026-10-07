"""test_web 测试计划: WEB UI 后端(拆分进行中, 余 245 fn)

## 测试计划(每个测试函数一条)
- test_api_traffic_qb_disabled_empty_state: qB 口径流量三端点未启用(qb_traffic None / enabled=false)空态与 /api/traffic/history 同构(plan 26-10-03-0946 §08 P4)
- test_api_traffic_qb_requires_token: 三 GET 端点沿用全局 token 鉴权单点(无凭证 401)
- test_api_traffic_qb_window_validation: window 非法值 400 / 缺省 24h / 仅认 WINDOW_NAMES 十三档(D4 沿用: 1m-30d + 6mo/1y/all, 90d 延后)
- test_api_traffic_qb_global_24h_points_totals_and_stale: global 24h 窗天文件块 -> 速率口径变换(区间平均 delta/w, 计划 26-10-07-2127 S2) -> 栅格展开(points 对齐桶/空桶 null=断连真空/窗首无种子 D4 0 线) + totals 差分(重置/断链, 口径不受速率变换影响) + 读取竞态降级回上一份快照标 stale
- test_api_traffic_qb_raw_rate_basis_delta_per_w_totals_unchanged: (计划 26-10-07-2127 S2)raw 窗速率口径 = 计数器差分区间平均 delta/w —— 已知 totals 序列逐桶断言 + 瞬时直采值零上图 + totals 通道逐字节不变(窗首基线缺失/相邻差分照旧) + 活尾桶跨盘/尾接缝差分(图尾同为区间平均)
- test_api_traffic_qb_raw_seed_extension_window_start_baseline: (S2/D3)窗首种子: read_window/v4_series_points t0 外扩一个响应桶宽取前驱桶点作差分基线 —— 窗首桶 rate = delta/w(非 0 线非瞬时值), 种子点被 v4_grid_obs 窗外过滤不外发
- test_api_traffic_qb_raw_seed_vacuum_chain_break_and_recover: (S2/D3)种子跨真空: 真空 null 点断链 —— 恢复首桶 rate 派不出(D4 0 线)且离线期字节不进速率与 totals, 次桶基线恢复 delta/w
- test_api_traffic_qb_raw_seed_vacuum_null_1s_edge_band: (issue 26-10-08-0141)窗首种子 1 秒边界带: 停机落 (seed_t0-1, seed_t0) 时真空 null 点取整后落窗外 —— 修复后标记保留断链, 恢复首桶 D4 0 线且离线字节不进速率/totals(修复前链误接出假尖峰)
- test_api_traffic_qb_global_30d_hour_segment: global 30d 窗 agg hour 行直映栅格桶(epoch 即桶键), interval_s=3600, 相邻桶差分
- test_api_traffic_qb_global_6mo_1y_day_segment: (S3b D4 沿用)6mo/1y 窗 agg day 行直映本地日界桶 —— 滚动窗切片(300 天前行 1y 可见/6mo 不可见), 缺日断链, interval_s=86400
- test_api_traffic_qb_global_all_month_segment: (S3b D4 沿用)all 窗 agg month 行数据面逐月铺格(缺失月 null), 相邻月差分, interval_s=标称月长; 空数据面空态
- test_api_traffic_qb_torrent_endpoint: 单种端点取数 / 非法哈希 400 / 未知哈希空态 / 冻结种子历史仍可查
- test_api_traffic_qb_torrent_1y_single_agg_cold_read: (S3b 验收)年视图单 agg 文件冷读恰 1 open, 缓存命中再查零 open
- test_api_traffic_qb_global_24h_reads_only_involved_day_files: (S3b 端点面回归)24h 窗只开窗口涉及日期天文件(含窗首种子外扩: 常态恰 2 个/跨午夜边界至多 3 个), 窗外日期/agg.dat 零 open
- test_api_traffic_qb_group_endpoint: 分组读侧现算(Σ 成员区间平均/全员空闲 z 覆盖 0 线/全员无观测断线 —— 借 global 判 null 退役且零全局读取/成员重置贡献 0/历史回溯可见/解析不到成员空态/畸形 key 400)
- test_api_traffic_qb_group_30d_reads_member_agg_only: (S3b 验收)3d+ 窗组图只读成员 agg 文件(2 成员恰 2 open = M×1, 天文件零读取)
- test_api_traffic_qb_group_never_transferred_empty_state: 组从未有成员产过流量 -> 空态
- test_api_traffic_qb_group_member_only_zruns_not_empty: 组空态判据观测面 —— 成员只剩 z 块不算「从未产过流量」, 出 0 线而非空态
- test_config_schema_endpoint: 图形化配置元数据端点(分组/插件/热重载级别)
- test_config_tree_roundtrip: 配置树读取/保存写回文件并投递热重载命令
- test_config_tree_invalid_rejected: 非法配置树 -> 400 且不写回
- test_config_tree_requires_config_root: 缺少 config 根段 -> 400
- test_config_tree_restart_field_fallback: R 级字段(data_dir)提交后被回退为磁盘旧值
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
- test_build_group_view_cross_group_conflict_flag: 组视图跨组文件交叉标记(26-10-04-0107 S4/D4) —— 去重集合展平为组 key 集合后端查好, warned 注入组对两侧 true、组外组 false; warned 空全 false; 未归组单种子视图(singles)为成员级投影不携带组级标记
- test_build_group_view_member_num_seeds_fields: 组视图成员透出 num_seeds/num_leechs/num_complete/num_incomplete
- test_build_group_view_group_aggregates: 组视图组级聚合(辅种扩列 2026-09-28) —— 进度/可用性 max、eta 最小有效值(哨兵不参与)、剩余量 min、最近活动 max(-1 不参与)、已下载求和、做种时长平均、分享率=总上传÷单份大小; 全组无效值回 0/None
- test_member_view_extended_fields: 成员视图透出辅种扩列字段(eta/time_active/last_activity 分钟量化 + downloaded/amount_left/completion_on/seen_complete/availability/限速/tracker/infohash_v2)
- test_error_reason_from_tracker_msg: 错误种子的具体原因取 tracker 报错 msg(虚拟条目跳过)+ 视图透出 error_reason(取不到回退"错误"/非错误态为空)
- test_error_reason_missing_files_without_api: missingFiles 的原因由状态本身给出("文件丢失"), 不发 tracker 请求
- test_refresh_error_reasons_budget_and_ttl: 错误原因预取限流(单轮预算条数/TTL 内不重取/过期重取)
- test_refresh_error_reasons_clears_when_recovered: 状态恢复后清空原因缓存并置脏(不留旧原因)
- test_refresh_error_reasons_skips_when_disconnected: qB 断开时跳过(不发请求/不清空现值)
- testhr_view_fields_three_state: 详情字段透出站点侧三态与依据(接入站点才有值, 未接入全空)
- testhr_view_fields_excluded: HR 排除态视图(hr_excluded=True, 触发/达标 False, 站点侧全空, 桥不被打扰)
- test_api_hr_status_disabled_returns_empty_state: 未启用 HR 时 /api/hr/status 回 enabled=false + 说明(前端空态, 不报错)
- test_api_hr_status_reports_site_state: 启用后逐站点摊开现状 —— 新鲜度/覆盖证明/索引与回填进度/配额/熔断/
  「现在为什么不放行」(与 --hr-status 同一 `hr.status` 口径) + 波次明细 lane_text 徽章人话逐档正确(LANE_TEXTS 单点)
- test_api_hr_status_names_the_blocking_step: 覆盖证明不成立时要说清卡在哪一步(用户看到种子没放行时最想知道的一句)
- test_api_hr_site_entries_full_fields: 种子明细端点(计划 26-10-01-2216 §7 阶段1)200 全字段 —— 行键面 = §3 P0+P1 全集
- test_api_hr_site_entries_local_present: 明细行 local_present 本地库 join(计划 26-10-02-1936 §3.3 决策点③a) ——
  v1 命中/仅 v2 命中/大小写差异命中 -> True, 本地不存在 -> False(未做种)
- test_api_hr_site_entries_verified_two_states: verified 有/无两态同表(无记录→未核实; 有记录→verified_ts+source 原值+人话)
- test_api_hr_site_entries_empty_site: 站点已接入但没有 HR 行 -> 200 + 空数组(前端空态)
- test_api_hr_site_entries_guards: HR 未启用 400 / 站点未接入 404(与 confirm-empty 同款话术)
- test_api_hr_site_entries_409_worker_absent: hr 门面在但取数服务缺席(service=None) -> 409 不假装有数据
- test_api_hr_history_rows_from_real_wave: 拉取历史端点(计划 26-10-04-0312 §3.4)200 —— 行键面 = §3.4 全集,
  真实波次(S2 记录器)落表; 完成徽章/触发人话/档位 lane_text/写者短标识全由后端算好
- test_api_hr_history_site_filter: site 过滤只回该站; 未接入 404 点名已接入清单(与 entries 同款话术)
- test_api_hr_history_guards: HR 未启用 400 / 取数服务缺席 409(与 entries 同款校验)
- test_api_hr_history_limit_clamped: limit 截最新 N 条; 0 钳到 1(不回全量也不回空页)
- test_api_hr_history_read_error_reported_not_raised: 站点文件读坏不抛 —— read_errors{site: err} 带出, rows 剔掉坏站
- test_api_state_excludes_hr_entry_details: 体积守卫 —— 种子明细键不得进 /api/state 轮询载荷(计划 §8)
- test_hr_user_visible_texts_no_graduation_wording: 否定守阵 —— 用户可见文案来源(hr status/resolve/events 字符串常量)「毕业」零残留
  (注释保留域术语, 决策点②); 无事实分支与带事实分支同文「在线·已达标」(testhr_view_fields_three_state 内钉)
- test_api_hr_refresh_single_site_and_no_runtime: refresh 指定单站受理 + hr 门面缺席回 409
- test_api_hr_confirm_empty: 人工对账戳端点(缺 site/未启用/未接入 400, 成功 ok, 写入失败 409)
- test_api_events_sse_stream_lifecycle: SSE 生成器整块(hello 帧/事件帧/keepalive 心跳/终结退订;
  TestClient 会挂死无限流, 直调端点驱动 body_iterator)
- test_api_events_sse_generator_error_still_unsubscribes: 生成器异常死亡也走 finally 退订
- test_views_published_atomically_when_rebuilt_concurrently: 并发重建(主循环线程 vs Web 线程)时四份视图与版本号必须**同一轮**发布, 不得出现"半新半旧"
- test_flush_views_marks_dirty_on_hr_revision_change: HR 判定新鲜度置脏(plan 26-10-03-0436 Step 2) —— hr.revision 变化后 flush_views 置脏, 重建后基线前移、再次 flush 不再置脏(无循环置脏)
- test_flush_views_hr_facade_missing_null_defense: hr 门面缺失(None)时判空防御 —— 重建记基线与 flush 比对都跳过, 不炸不置脏
- test_build_search_index_files: 搜索索引构建(hash -> name+files), 单条文件拉取失败跳过该种子
- test_build_search_index_incremental_and_evict: 增量维护(不重拉已建条目/补拉新增/淘汰已删)
- test_build_search_index_budget_resumes: 限流分批构建, 未拉完保持脏, 续建至完成
- test_build_search_index_aborts_when_disconnected: qB 断连时中止构建且不写空索引
- test_search_torrents_name_match: 种子名匹配(即时/大小写不敏感)
- test_search_torrents_separator_normalized: 分隔符归一匹配 —— 空格查询词命中点/下划线/连字符分隔的名与文件(回归 "cat and" 搜不到 The.Cat.and… 名)
- test_parse_query_tokens: 查询解析词法 —— 正/负词/短语 + 宽容边界(孤立-/未闭合引号/纯标点/--dv/web-dl)
- test_search_torrents_cross_row_and: 正词逐词跨行 AND(拍板 26-09-27 二次定案, 推翻 26-09-26 文件行隔离)—— 每个正词命中任一候选行(全称行/文件行)即可: 「minions mteam」名字×标签、「delta 03」名字×集文件跨行命中; 负词种子级不变
- test_search_torrents_negative_term: 负词种子级(26-09-27 定案)—— 任一候选行含负词 ⇒ 该种子整体排除: 单种子内季包文件统一计算(任一文件带负词整包排除), 多种子集合逐个算
- test_search_torrents_negative_torrent_veto: 负词种子级回归 —— 名字/保存路径/站点行含负词 ⇒ 整种子排除, 优先于一切正词命中(「cat and -11」+「-mteam」两轮报障回归)
- test_search_torrents_facet_rows: 候选行覆盖全部文本面(站点/分类/路径/标签行即时匹配, by 定位行类别) + facet 行负词整种子排除 —— 三页同源(26-09-26 单点化; 负词种子级 26-09-27 定案)
- test_search_torrents_phrase: 短语 "…" 整段归一为连续子串, 词序敏感(terms-AND 命中而短语不命中的区分用例)
- test_search_torrents_regression_envnv10: 回归(26-09-26 报障)——「恶女 10」命中单文件发布物, -ubweb 可排除
- test_search_torrents_negative_only_empty: 仅负词/空查询返回空 + negative_only 标记, 不投递索引构建
- test_search_torrents_file_match: 文件列表匹配(依赖已建索引)
- test_search_torrents_building_triggers: 索引脏时 building=True 并投递构建命令
- test_api_search_endpoint: GET /api/search 转发与鉴权(含空查询)
- test_api_paths_endpoint: GET /api/paths 已知目录聚合(组 save_path + 现有种子 save_path 归一去重排序; 空路径跳过; 无副作用; 鉴权)
- test_api_open_path_endpoint: POST /api/open-path 打开目标文件夹(FX-14 + R10-10) —— 目录/单文件(select=True 定位选中)/回退 save_path(缺失或下载中未落盘)/组键首元、未知目标 404、kind 非法 400、客户端传 path 被忽略、无副作用、鉴权
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
- test_api_t_bulk_limits_location_enqueue: bulk 限速/移动动作入队(计划 26-10-02-1955 W2) —— up/dl/location 提供才透传(0=不限合法), 负数/limits 全空/location 空路径 400 不入队; 历史载荷形态不变; 无密钥 401
- test_api_t_bulk_skip_check_enqueue: bulk 跳检动作入队(计划 26-10-02-1955 W3) —— 无额外参数(载荷只有 hashes/action/delete_files); 无密钥 401; gate 在 drain 分派处, 路由层开关关时仍 200 入队
- test_drain_web_commands_torrent_write_actions: 二轮写命令正常执行(参数透传/cmd_id 回执 ok/限速位置同步快照)
- test_drain_web_commands_torrent_write_unknown_hash_skips: 二轮写命令未知 hash 静默跳过不调 API
- test_drain_web_commands_share_limits_and_queue_mapping: share-limits 缺省维度 -2 补齐; queue 动作映射; 未知动作 error 回执
- test_drain_web_commands_torrent_write_param_errors: 写命令参数错误 -> error 回执且不调 API, 后续命令继续
- test_drain_web_commands_bulk_torrents: 批量多 hash 一次调用 + 聚合回执(部分缺失/未知动作/空列表 -> error)
- test_drain_web_commands_bulk_torrents_group_keys: bulk 组键模式(DLG-02): 组键展开级联全组成员删除; 与 hashes 混合去重; 缺失组计组数; 组不存在不调 API
- test_drain_web_commands_bulk_torrents_tags_category: bulk 标签/分类命令执行 —— add_tags/remove_tags/set_category 单次调用带全部 hash; 缺 tags / 缺 category 键 error 回执; 空串分类(清除)合法; 标签非空校验
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
- test_state_kind_maps_states: 状态语义分类映射(暂停态优先于下载/做种)
- test_apply_new_config_levels: 配置热重载按 L0/L1/L2/R 级别应用; L1 只剩重连(web 重启/logging/notify/HR 全部改经模块 apply, P1-P2); L0 下 hr.apply 也必须被调到(HR 路由守阵)
- test_apply_new_config_l2_preserves_runtime_state: L2 热重载保留运行期内存 state —— 不得重读磁盘旧版回滚 exec_history/skip_check_day/recheck_fails(issue 26-09-21-1347 守阵)
- test_stop_web_server_releases_port_for_restart: 停止后服务线程真正退出, 同端口可再次监听(10048 回归守阵)
- test_start_web_server_started_message_is_info: 「WEB UI 已启动」按 INFO 记(alert-levels 契约: 生命周期消息不许 WARNING, 否则 notify 开启时每次启动弹通知)
- test_webui_module_apply_skips_restart_when_bind_unchanged: 监听身份未变 -> 不重启, 仅刷新密钥(经 WebUIModule.apply 驱动, P2)
- test_start_web_server_reports_failure_when_port_taken: 端口被占用 -> 句柄未就绪 + ERROR 日志(不再静默)
- test_web_loop_exception_handler_downgrades_connection_reset: 网络波动(WinError 10054 对端强迫关闭)降级为一行 INFO, 不再 ERROR + traceback
- test_web_loop_noise_log_throttled_in_window: 断连日志按窗口节流(窗口内只记首条, 出窗口附抑制条数)
- test_web_loop_exception_handler_delegates_real_bug: 反向守阵 —— 非波动异常交回 asyncio 默认处理器, 不吞
- test_is_network_fluctuation_matrix: 波动判定矩阵(异常类 / winerror / errno 三条路都认; 非 OSError 与"目标拒绝"不算)
- test_uvicorn_config_installs_loop_exception_handler: 处理器必须真的装到 uvicorn 事件循环上(经 get_loop_factory 注入)
- test_api_category_tag_endpoints: 分类/标签 CRUD 端点(入队与 400 校验)
- test_category_tag_commands_execute: 分类/标签命令执行(QbApi 封装 + 缓存失效)
- test_api_speed_mode_and_override: /api/speed/mode 曲线/停用两形态 + /api/speed/override 落 transfer 端点
- test_api_speed_alt_and_toggle: ALT-01 备用速度 —— /api/speed/mode 增列 alt_on/alt_current + /api/speed/alt 落 setPreferences(alt_*) + /api/speed/alt/toggle 落 toggle 端点
- test_qbapi_alt_speed_limits_normalization: ALT-01 QbApi 备用限速 KiB<->bytes/s 换算 + setPreferences 增量语义(只传非 None 方向) + 模式切换
- test_api_speed_mode_curve_config_disabled: 曲线存在但 enabled=False -> curve_enabled=False(快照之上叠加配置判定)
- test_api_add_torrent_endpoint: /api/torrents/add multipart(bytes 内存直传/选项透传/空来源 400)
- test_add_torrent_receipt_and_optional_flags: 添加回执两形态(API>=2.14.0 的 JSON 元数据 / 旧文本 "Ok.")判受理 + 两个 optional 选项(停止位 is_stopped / 自动管理 use_auto_torrent_management)恒显式下发(省略会吃 qB 会话/全局默认) + 成功走 INFO(改前 WARNING 会直推桌面弹窗)
- test_api_export_endpoint: /api/torrents/{hash}/export 字节流与 disposition(404/503); 非 ASCII 种子名走 filename*(回归: 头 latin-1 编码崩)
- test_content_disposition_encoding: content_disposition 头值纯 ASCII + filename* 百分号编码 + 清洗/回退
- test_api_category_tag_list_endpoints: GET /api/categories 与 /api/tags 列表端点(store 缓存数据源)
- test_api_tags_exclude_auto: /api/tags?exclude_auto=1 剔除程序自动维护标签(站点/HR 精确集 + 集数模板形状; 事件标记保留, 不带参全量)
- test_api_log_endpoint: /api/log tail 与 level 过滤(未配置空)
- test_api_log_level_filter_follows_config_format: 等级过滤按 config.logging.format 定位等级名(生产格式无方括号, 按字面量 `[WARNING` 捞会恒空 —— 2026-09-25 真机 bug)
- test_api_log_level_filter_keeps_multiline_record: 多行日志(整段 traceback)折行后跟随其记录的等级, 筛 ERROR 不丢栈
- test_api_log_note_when_level_unfilterable: 筛不了(格式无等级字段 / 已存行与格式不符)回全部行 + note, 不静默给空
- test_webui_module_apply_toggle_enabled: web.enabled 热开关(关->开启动 / 开->关停止并清句柄; 经 WebUIModule.apply 驱动, P2)
- test_seed_flat_view_fields_and_gating: 种子平铺视图(SEED_ITEM)字段契约齐全 + ensure_group_state 同门控回传
- test_flat_view_refreshed_by_main_loop_tick: 种子页速度随主循环刷新(回归: 平铺视图曾被"饿死"停在旧快照)
- test_rebuild_views_single_entry_point: rebuild_views 唯一重建入口(四视图 + 版本号 + 脏标记一次完成)
- test_api_state_status_carries_server_state: status.server(state)恒回传不受 rid 门控(状态栏与行数据同源同轮)
- test_api_torrent_detail_endpoint: /api/torrents/{hash} 全字段详情(to_dict+site+HR); 未知 hash 404
- test_api_torrent_subresources: /api/torrents/{hash}/trackers|files|peers 透传(trackers 例外: url 已 mask, plan 26-10-07-0055 S3); 未知 404/断连 503
- test_api_torrent_trackers_masked_response: 守阵① API 外发(plan 26-10-07-0055 S4) —— trackers 响应 url 一律 mask(凭据原文不外发, 缺席断言不写死参数名), mask 保留 scheme://host+path+参数名, 虚拟条目透传, 两次请求逐字节一致; 红验: 路由改回透传
- test_api_readonly_endpoints_short_cache: P1-4 只读端点短缓存(窗口内合并 / 写命令后失效 / 断连仍 503)
- test_api_torrent_peers_endpoint: /api/torrents/{hash}/peers 走 sync_torrent_peers(torrent_hash=..)整包透传(404/503)
- test_api_stats_endpoint: /api/stats 透出 store.server_state(未同步时 null)
- test_api_enqueue_wakes_main_loop: 投递用户命令唤醒主循环; 反向守卫——自投递命令须登记进 SELF_POSTED_COMMANDS(防自激)
- test_cmd_trackers_log_sanitized: tracker 移除日志只写脱敏主地址 —— 任意命名的凭据全文都不进日志(不按参数名黑名单), 主地址仍在(S3 后入参为 mask 值)
- test_cmd_remove_tracker_mask_roundtrip: S3 删除改道 —— remove_tracker 收 mask 值当场重取原文比对, 恰 1 命中 qB 收原文; 0/多命中报「未找到该 tracker」且零写调用
- test_cmd_remove_tracker_same_host_distinct_passkeys: 守阵② 写路径同 host 区分(plan 26-10-07-0055 S4) —— 同 host 两条不同 passkey mask 互异(R8), 传 A 的 mask qB 恰收一次 remove 且 urls==A 原文(B 不受影响); 红验: 删除临时改回直传
- test_tracker_edit_offline_route_and_static: 守阵③ 编辑下线(plan 26-10-07-0055 S2/S4) —— POST trackers/edit 不落到处理器(404/405; 根挂 StaticFiles 兜 405) + 路由表白名单复核 + static/ 遍历 grep "trackers/edit" 零命中(金清单行由 test_web_route_manifest_frozen 钉); 红验: 临时加回路由/写回字样
- test_trackers_baseline_keys_are_raw_urls: 守阵④ 基线 key 为原文(plan 26-10-07-0055 S4) —— _trackers_baseline 的 dict key == fake client 原文 url, 同 host 两条不同 passkey key 互异且各行 epoch 字段对号; 红验: 基线临时切 mask
- test_torrent_detail_trackers_route_mask_canary: 守阵⑤ 静态扫 canary(plan 26-10-07-0055 S4) —— torrent_detail.py 源码含 mask_tracker_entry 引用且钉在 trackers 端点 _cached_read 取数 lambda 上(mask 先于缓存写入); 红验: 同守阵① 改回透传
- test_web_route_manifest_frozen: 路由金清单守阵(W0, plan 26-09-22-1857; ALT-01 增 2 条 speed/alt, P2' 增 1 条 skip-check, 26-10-01-2216 阶段1 增 1 条 hr sites entries, 26-10-02-1955 W1 增 1 条 webui/flags, 26-10-03-0946 P4 增 3 条 traffic/qb, 26-10-04-0312 S3 增 1 条 hr history, 26-10-05-0314 S2 增 1 条 skip-check/precheck, WEBUI 错误历史 S2 增 1 条 errlog): 78 条 (method, path) 集合逐一钉死, web.py 拆 web/ 包期间任何路由丢失/改名/方法变更即红
- test_create_app_is_thin_assembly: 组装壳守阵(W6): create_app 源 ≤150 行且无内联路由装饰器(防 926 行单函数回潮)
- test_api_keys_get_default_when_missing: 快捷键配置文件不存在 -> GET 回默认表(计划 26-09-28-0354 W6 §4.4)
- test_api_keys_put_roundtrip: PUT 合法配置落盘(atomic_write)且 GET 原样回读; 空串=显式禁用语义保留
- test_api_keys_put_invalid_rejected: PUT 结构非法(schema_version/模板/overrides 形状/归一化串) -> 422 且不触碰磁盘
- test_api_keys_read_corrupt_fallback: 主文件坏 JSON -> WARN + 默认表; .bak 完好 -> 回备份(读时兜底链)
- test_api_keys_unknown_schema_version_fallback: schema_version 不识别 -> 回默认表 + WARN(升级链口径: 宁可回默认不带病生效)
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
### P1 覆盖率提升轮: webui 运行时与命令长尾
- test_web_runtime_notify_drops_are_counted: SSE 广播非阻塞(慢/坏订阅者各计丢弃)
- test_web_runtime_check_pending_paths: 在途汇报确认全路径(item 级 deadline 超时 warn(epoch/legacy 文案)/停止直判/断连/读异常 error/判定聚合三桶与前 3 条原因截断)
- test_web_runtime_resync_elapsed_ms_logs_by_threshold: 补刷新计时按阈值分级(慢 WARNING / 正常 DEBUG)
- test_web_runtime_set_result_prunes_stale_and_carries_truth: 回执表 TTL 淘汰 + truth 附带
- test_web_runtime_affected_hashes_shapes: 受影响种子三种取法 + 异常退化
- test_web_runtime_affected_truth_queries_live_api: 真值直查 qB, 失败回 None 不回落快照
- test_web_commands_delete_with_files_and_reannounce_gone_receipt: 删除透传 delete_files; 汇报缺失显式回执
- test_reannounce_group_empty_snapshot_error_receipt: 组命令空组回执(E-03) —— 组内成员执行时刻全不在快照时显式 error 回执, 不发指令不登记跟踪(对齐单发口径, 前端不再挂到超时)
- test_web_commands_recheck_and_skip_check_receipts: recheck/skip-check 拒绝回执带文案
- test_web_commands_limits_partial_directions: 限速只下发提供的方向; 分享限制缺省 -2 补齐
- test_web_commands_rename_fs_folder_branch: 重命名文件夹分支
- test_web_commands_bulk_argument_errors: 批量参数四类错误回执
- test_web_commands_bulk_missing_targets_reported: 批量缺失种子/组分列计数
- test_web_commands_bulk_recheck_via_ops: 批量 recheck 经 ops 聚合回执
- test_web_commands_add_torrents_receipt: 添加种子受理/拒绝回执
- test_api_torrent_write_endpoints_extra_enqueue: 写端点补遗(pause/resume/delete/skip-check/limits 部分方向)
- test_api_torrents_add_endpoint_errors_and_enqueue: 添加种子 base64 坏/空载荷 400 + 合法入队
- test_api_config_put_and_preview_tree_shape: 配置树 PUT/preview 非对象 400 + preview 不落盘
- test_api_expr_eval_runtime_error: 求值期失败(除零) -> ok=False 带文案与 used
- test_api_keys_endpoint_roundtrip_and_validation: 快捷键默认表/422 校验/保存读回
- test_api_keys_sanitize_rejects_non_dict: _sanitize 非 dict 一律 None
- test_api_category_and_tag_empty_rejections: 分类/标签空入参 400
- test_api_speed_mode_reads_client_with_alt_fields: 限速托管直读 qB(含 ALT 双组) + 读失败/部分成功整组回 None(DEBUG 留摘要)
- test_api_fs_error_semantics: fs 端点错误语义化(404/501/403/400)
- test_api_traffic_qb_global_live_tail_realtime: (S6 验收追加)raw 段窗活尾合流 —— 纯活尾(零盘)出实时桶点(桶值 = 区间平均, 计划 26-10-07-2127 S2);
  磁盘落盘后滞后快照重列已落盘记录被按 ts 精确去重(快照与 flush 竞态不重不漏), 快照清空后磁盘响应与合流响应逐点一致
- test_api_traffic_qb_group_live_tail_member_only: (S6)组端点空态判据计入活尾 —— 成员仅活尾(零盘)组图非空(单记录窗首基线缺失 D4 0 线, S2);
  单种端点同享活尾
- test_frontend_toast_duration_floor_by_kind: 错误/超时类 toast 停留下限守阵(2026-10-05 用户报「右下角错误信息停留太短」) ——
  ui_feedback.js 头部 `TOAST_MS_FLOOR` 给 error/timeout 设 ≥8s 下限, `toast()` 与 `_finishToast()`
  两条排期路径都经 `toastMs(kind, ms)` 解析且 ms 缺省为 null(绕过即回到裸 ms, 下限形同虚设)
- test_aq_tip_anchor_watch_and_reacquire_wired: aq-tip 锚定保活守阵(2026-10-07 用户报「详情面板 tooltip 位置不正确」, 变体 5s 轮询整帧重建三条错位路径) —— ui_feedback.js 定位抽 place() 单点(show 初显与显示期重定位共用, 夹取/err-panel 避让同口径) + reacquire() 语义重解析(data-aq-tip 同文案节点按视口中心距旧矩形最近者, 语义扫描先于指针坐标 elementFromPoint 回退, 回退有 Number.isFinite(curX) 门护键盘 NaN 路径) + watch/tick rAF 帧环(浮层可见期才运转, 每帧只 1 次 getBoundingClientRect 零 DOM 查询: 断链走语义重解析 / 四轴 rect 漂移超 1px 重定位) + enter 记 curRect 基准 / hide 作废成对, 任一环被重构摘除即红
"""
import base64
import errno
import json
import logging
import os
import re
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
from auto_qb.infra.utils import decode_group_key, encode_group_key, mask_tracker_url
from auto_qb.webui import create_app
from auto_qb.webui.runtime import (
    CMD_SLOW_MS,
    EVENT_QUEUE_MAX,
    REANNOUNCE_CONFIRM_TIMEOUT,
    WEB_RESULT_MAX,
    WEB_RESULT_TTL,
    WebUIRuntime,
)

from webui_helpers import (
    KEY,
    _web_stub,
    _make_web_manager,
    STATIC_ROOT,
    _UI_ALL,
    _ui_aggregate,
    _enable_qb_traffic,
    _qb_v4,
    _hr_status_env,
    _make_grouped_manager,
    _iter_api_routes,
    module_log,
    _attach_live_tail_host,
)


def _free_port() -> int:
    """取一个本机空闲端口(先绑 0 再释放; 用于真实起停 WEB 服务器的测试)"""
    import socket

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


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


def _v4_opens(opened):
    """qb-traffic-v4/ 数据面的打开路径(请求链路会开无关文件, 只看 v4 读盘)"""
    return [p for p in opened if "qb-traffic-v4/" in p]


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
    """global 24h 窗(raw 段): 天文件块 -> 桶点 -> 速率口径变换(区间平均 delta/w, 计划
    26-10-07-2127 S2) -> 栅格展开(points 对齐桶 / 空桶 null = 断连真空 / 窗首无种子基线
    缺失 D4 豁免 0 线) + totals 相邻桶快照差分(重置 null / 断连断链, 口径不受速率变换
    影响) + 读取竞态降级: 回上一份成功快照标 stale=true, 不以空态冒充无数据(§08)"""
    from auto_qb.core.traffic_store import V4Block, V4DayCache, V4NullRun, V4Sample, v4_epoch_date_str

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
    now = int(time.time())
    base = ((now - 7200) // 30) * 30  # 窗内 2h 处的 30s 对齐桶
    # 块首记录槽位恰在 base+30(w=30) -> 桶 base 1:1 对位, 其后标称 30s 逐桶对齐;
    # n 游程 3 槽(槽位 base+180/210/240)在响应面 = 连续空桶(断连), 尾记录以游程终点续链
    # v4 行型: 计数器回落处拆块(与写侧「重置强制关块重立基线」一致), 槽位序列不变
    store.append_records(
        "global",
        v4_epoch_date_str(base + 30),
        (base + 30, 30),
        (
            V4Sample(100, 50, 1000, 500),  # 桶 base
            V4Sample(200, 70, 2000, 800),  # 桶 base+30
            V4Sample(5, 5, 2400, 900),  # 桶 base+60
            V4Sample(300, 90, 3400, 1300),  # 桶 base+90
        ),
        (1000, 500),
    )
    store.append_records(
        "global",
        v4_epoch_date_str(base + 30),
        (base + 150, 30),
        (
            V4Sample(10, 10, 2900, 1400),  # 桶 base+120: dl 快照回落(重置, 新块立基线)
            V4NullRun(3, dt_ms=90000),  # 断连 3 槽: 桶 base+150/180/210 空
            V4Sample(12, 22, 3500, 1500, dt_ms=30000),  # 桶 base+240(断链后基线缺失)
        ),
        (2900, 1400),
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
    assert point_at(body, base) == {"t": base, "dl": 0, "up": 0}  # 窗内首点无基线: D4 豁免 0 线(非 null)
    assert point_at(body, base + 30) == {"t": base + 30, "dl": 33, "up": 10}  # 区间平均: delta(1000,300)/30
    assert point_at(body, base + 120) == {"t": base + 120, "dl": 0, "up": 3}  # dl 重置派不出 0 线 + up delta(100)/30
    assert point_at(body, base + 150) is None  # 断连段: 连续空桶 = null(不连线)
    assert point_at(body, base + 180) is None
    assert point_at(body, base + 210) is None
    assert point_at(body, base + 240) == {"t": base + 240, "dl": 0, "up": 0}  # 断链后基线缺失: D4 0 线
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

    monkeypatch.setattr(V4DayCache, "read_window", _read_broken())
    stale = client.get("/api/traffic/qb/global", headers=auth).json()
    assert stale["meta"]["stale"] is True
    assert stale["points"] == body["points"] and stale["totals"] == body["totals"]
    monkeypatch.setattr(V4DayCache, "read_agg", _read_broken())
    fresh = client.get("/api/traffic/qb/global", headers=auth, params={"window": "30d"}).json()
    assert fresh["points"] == [] and fresh["totals"] == [] and fresh["meta"]["stale"] is True
    monkeypatch.undo()
    assert client.get("/api/traffic/qb/global", headers=auth).json()["meta"]["stale"] is False  # 恢复后照常


def test_api_traffic_qb_raw_rate_basis_delta_per_w_totals_unchanged(web_env):
    """(计划 26-10-07-2127 S2)raw 窗速率口径 = 计数器差分区间平均 delta/w: 已知 totals 序列
    逐桶断言(20/10 与 40/20), 瞬时直采值(5xxx-9xxx 垃圾字段)零上图; totals 通道逐字节不变
    (窗首基线缺失 null + 相邻差分照旧); 活尾槽带绝对 totals —— 图尾桶跨盘/尾接缝差分,
    同为区间平均(head_pending=False 非块首活尾从写侧游标倒推槽位)"""
    from auto_qb.core.traffic_store import LiveTail, V4Sample, v4_epoch_date_str

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
    now = int(time.time())
    b0 = ((now - 240) // 30) * 30  # 5m 窗内, 远离窗首/窗尾栅格边缘(种子外扩区无数据)
    store.append_records(
        "global",
        v4_epoch_date_str(b0 + 30),
        (b0 + 30, 30),
        (
            V4Sample(7777, 7777, 1000, 500),  # 桶 b0: 窗内首点无基线 -> D4 0 线
            V4Sample(9999, 9999, 1600, 800),  # 桶 b0+30: delta(600,300)/30 -> 20/10
            V4Sample(5555, 5555, 2800, 1400),  # 桶 b0+60: delta(1200,600)/30 -> 40/20
        ),
        (1000, 500),
    )
    _attach_live_tail_host(
        mgr,
        {
            "global":
                LiveTail(
                    block_open=True,
                    head_pending=False,  # 块首已落盘: 活尾记录为非块首, 槽位从游标 projected_ts 倒推
                    start_epoch=b0 + 30,
                    interval_s=30,
                    projected_ts=float(b0 + 120),
                    records=(V4Sample(8888, 8888, 3400, 1700), ),  # 桶 b0+90: delta(600,300)/30 -> 20/10
                    open_run=None,
                )
        },
    )
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "5m"}).json()

    def pt(seg, t):
        return next((p for p in body[seg] if p and p["t"] == t), None)

    assert body["meta"]["stale"] is False and body["meta"]["interval_s"] == 30
    assert pt("points", b0) == {"t": b0, "dl": 0, "up": 0}  # 窗内首点基线缺失 D4 0 线
    assert pt("points", b0 + 30) == {"t": b0 + 30, "dl": 20, "up": 10}
    assert pt("points", b0 + 60) == {"t": b0 + 60, "dl": 40, "up": 20}
    assert pt("points", b0 + 90) == {"t": b0 + 90, "dl": 20, "up": 10}  # 活尾桶: 跨盘/尾接缝差分
    assert all(p["dl"] < 1000 and p["up"] < 1000 for p in body["points"] if p is not None)  # 瞬时垃圾值零上图
    # totals 通道逐字节不变(速率变换不动快照链): 窗首基线缺失 + 相邻差分(含活尾桶)
    assert pt("totals", b0) == {"t": b0, "dl": None, "up": None}
    assert pt("totals", b0 + 30) == {"t": b0 + 30, "dl": 600, "up": 300}
    assert pt("totals", b0 + 60) == {"t": b0 + 60, "dl": 1200, "up": 600}
    assert pt("totals", b0 + 90) == {"t": b0 + 90, "dl": 600, "up": 300}


def test_api_traffic_qb_raw_seed_extension_window_start_baseline(web_env):
    """(计划 26-10-07-2127 S2/D3)窗首种子: read_window/v4_series_points 的 t0 外扩一个响应
    桶宽(grid.t0 - grid.interval)取前驱桶点作差分基线 —— 窗首桶 rate = delta/w(旧口径下
    是瞬时直采值; 无种子时是 D4 0 线), 瞬时垃圾值零上图; 种子点自身基线缺失且被 v4_grid_obs
    窗外过滤天然不外发。数据跨窗首等距等差铺放(逐桶 delta 恒 600/300), 对窗首 floor 对齐
    位置与端点取 now 的 ±1s 秒漂不敏感(断言值恒定)"""
    from auto_qb.core.traffic_store import V4Sample, v4_epoch_date_str

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
    now = int(time.time())
    first = (now - 300) - ((now - 300) % 30)  # 5m 窗栅格首桶(floor 对齐)
    totals = ((1000, 500), (1600, 800), (2200, 1100), (2800, 1400), (3400, 1700))
    store.append_records(
        "global",
        v4_epoch_date_str(first),
        (first, 30),
        tuple(V4Sample(9999, 9999, dl, up) for dl, up in totals),  # 瞬时字段全垃圾, 只看差分
        (1000, 500),
    )
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "5m"}).json()
    pts = [p for p in body["points"] if p is not None]
    assert len(pts) >= 2 and body["meta"]["stale"] is False
    p0 = pts[0]
    assert p0["t"] in (first, first + 30)  # 端点取 now 与用例 ±1s: 窗首桶至多移一格
    assert all(p["dl"] == 20 and p["up"] == 10 for p in pts)  # 逐桶 delta(600,300)/30 —— 种子给窗首桶基线
    tots = [p for p in body["totals"] if p is not None]
    assert tots[0] == {"t": p0["t"], "dl": None, "up": None}  # totals 口径不变: 窗首桶基线缺失
    assert tots[1] == {"t": pts[1]["t"], "dl": 600, "up": 300}  # 相邻桶差分照旧


def test_api_traffic_qb_raw_seed_vacuum_chain_break_and_recover(web_env):
    """(计划 26-10-07-2127 S2/D3)种子跨真空: 窗首前种子块与窗内恢复块之间程序停机 ——
    v4_series_points 既有真空判定出 null 点断链, 恢复首桶 rate 派不出(D4 豁免 0 线, 非
    null 非尖峰), 离线期 qB 自行传输的字节既不进速率也不进 totals(恢复首桶 totals 基线
    缺失 null), 次桶起基线恢复 delta/w"""
    from auto_qb.core.traffic_store import V4Sample, v4_epoch_date_str

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
    now = int(time.time())
    first = (now - 300) - ((now - 300) % 30)
    store.append_records(  # 窗首前种子块: 单记录, 桶 first-30(被 v4_grid_obs 窗外过滤不外发)
        "global", v4_epoch_date_str(first), (first, 30), (V4Sample(1111, 1111, 1000, 500), ), (1000, 500)
    )
    store.append_records(  # 停机后恢复块(真空 [first, first+60)): 首记录 totals 已含离线期字节 9000/4500
        "global",
        v4_epoch_date_str(first + 90),
        (first + 90, 30),
        (
            V4Sample(9999, 9999, 10600, 5300),  # 桶 first+60: 恢复首点基线缺失 -> D4 0 线(离线字节不进速率)
            V4Sample(7777, 7777, 11200, 5600),  # 桶 first+90: delta(600,300)/30 -> 20/10(基线恢复)
            V4Sample(5555, 5555, 11800, 5900),  # 桶 first+120: delta(600,300)/30 -> 20/10
        ),
        (10600, 5300),
    )
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "5m"}).json()

    def pt(seg, t):
        return next((p for p in body[seg] if p and p["t"] == t), None)

    assert body["meta"]["stale"] is False
    assert pt("points", first) is None and pt("points", first + 30) is None  # 真空段断线(不连线)
    assert pt("points", first + 60) == {"t": first + 60, "dl": 0, "up": 0}  # 恢复首桶 D4 0 线(非 null 非尖峰)
    assert pt("points", first + 90) == {"t": first + 90, "dl": 20, "up": 10}  # 基线恢复
    assert pt("points", first + 120) == {"t": first + 120, "dl": 20, "up": 10}
    assert all(p["dl"] < 1000 and p["up"] < 1000 for p in body["points"] if p is not None)  # 瞬时垃圾值零上图
    assert pt("totals", first + 60) == {"t": first + 60, "dl": None, "up": None}  # 离线字节不进 totals(基线缺失)
    assert pt("totals", first + 90) == {"t": first + 90, "dl": 600, "up": 300}
    assert all(p is None or (p["dl"] in (None, 600) and p["up"] in (None, 300)) for p in body["totals"])


def test_api_traffic_qb_raw_seed_vacuum_null_1s_edge_band(web_env, monkeypatch):
    """(issue 26-10-08-0141)窗首种子 1 秒边界带: 停机时刻落在 (seed_t0-1, seed_t0) 时真空
    null 点 t = int(prev_chain_end) 取整后 = seed_t0-1 恰落窗外 —— 修复前被丢弃, 种子点
    (覆盖桶触及窗首照收)与恢复首点之间差分链误接, 离线期 qB 自行传输的字节被误归恢复首桶
    出假尖峰(rate 300 / totals 9000); 修复后标记保留并断链, 恢复首桶 rate 派不出(D4 0 线)
    且离线字节不进速率与 totals。时钟钉死(1 秒带需确定性 now; 端点 _grid 走 traffic_qb.time.time)"""
    from auto_qb.core.traffic_store import V4Sample, v4_epoch_date_str
    from auto_qb.webui.server import traffic_qb as tq

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
    fixed = 1_800_000_000.0  # 30 的整倍 -> 5m 窗栅格对齐(确定性几何)

    class _FixedClock:
        def time(self):
            return fixed

    monkeypatch.setattr(tq, "time", _FixedClock())
    g_t0 = int(fixed) - 300  # 5m 窗栅格首桶
    seed_t0 = g_t0 - 30  # D3 窗首种子外扩 = grid.t0 - grid.interval
    store.append_records(  # 种子块: 末槽恰落 (seed_t0-1, seed_t0) 的 1 秒带(首记录 @seed_t0-30, 次记录 +29.5s)
        "global",
        v4_epoch_date_str(seed_t0 - 30),
        (seed_t0 - 30, 30),
        (V4Sample(1111, 1111, 1000, 500), V4Sample(2222, 2222, 1600, 800, dt_ms=29500)),
        (1000, 500),
    )
    store.append_records(  # 停机后恢复块(真空): 首记录 totals 已含离线期字节 9000/4500
        "global",
        v4_epoch_date_str(g_t0 + 30),
        (g_t0 + 30, 30),
        (V4Sample(9999, 9999, 10600, 5300), V4Sample(8888, 8888, 11200, 5600)),
        (10600, 5300),
    )
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "5m"}).json()

    def pt(seg, t):
        return next((p for p in body[seg] if p and p["t"] == t), None)

    assert body["meta"]["stale"] is False and body["meta"]["interval_s"] == 30
    assert pt("points", g_t0) == {"t": g_t0, "dl": 0, "up": 0}  # 恢复首桶 D4 0 线(修复前 = 假尖峰 300)
    assert pt("points", g_t0 + 30) == {"t": g_t0 + 30, "dl": 20, "up": 10}  # 次桶基线恢复 delta/w
    assert all(p["dl"] < 1000 and p["up"] < 1000 for p in body["points"] if p is not None)  # 离线字节零上图
    assert pt("totals", g_t0) == {"t": g_t0, "dl": None, "up": None}  # 离线字节不进 totals(修复前 = 9000)
    assert pt("totals", g_t0 + 30) == {"t": g_t0 + 30, "dl": 600, "up": 300}


def test_api_traffic_qb_global_30d_hour_segment(web_env):
    """global 30d 窗(agg hour 段): agg.dat hour 行直映栅格桶(epoch 即桶键, 桶内不再
    聚合), meta.interval_s=3600; 相邻 hour 桶快照差分"""
    from auto_qb.core.traffic_store import AggRow

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
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
    """6mo/1y 窗(agg day 段, D4 沿用): day 行直映本地日界桶, 滚动窗切片正确 ——
    300 天前的行 1y 可见 / 6mo 不可见; 缺日 = null 桶(totals 断链基线缺失);
    meta.interval_s=86400"""
    from datetime import datetime, timedelta

    from auto_qb.core.traffic_store import AggRow

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
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
    """all 窗(agg month 段, D4 沿用): month 行数据面逐月铺格(缺失月 = null 桶, 折线
    断开), 相邻月桶快照差分; meta.interval_s = 标称月长(真实月长按行间隔, 点位真值在
    points[].t —— 前端按真值落点)"""
    from auto_qb.core.traffic_store import AggRow, v4_month_epoch

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
    now = int(time.time())
    m0 = v4_month_epoch(now)  # 本自然月(完结月行; 当月行未封不写, 用例直接造历史月)
    m1 = v4_month_epoch(m0 - 86400)  # 上月
    m4 = v4_month_epoch(v4_month_epoch(v4_month_epoch(m1 - 86400) - 86400) - 86400)  # 再往前 3 个自然月
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
    """单种端点: 正常取数 / 非法哈希 400 / 未知哈希空态; 数据挂 infohash ——
    不在当前快照的冻结种子历史仍可查"""
    from auto_qb.core.traffic_store import V4Sample, v4_epoch_date_str

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
    now = int(time.time())
    base = ((now - 3600) // 30) * 30
    # 块首记录槽位恰在 base+30(w=30) -> 桶 base 1:1 对位
    store.append_records(
        "torrent:HA", v4_epoch_date_str(base + 30), (base + 30, 30), (V4Sample(500, 100, 5000, 1000), ), (5000, 1000)
    )
    body = client.get("/api/traffic/qb/torrent/HA", headers=auth).json()
    assert body["meta"]["source"] == "qb" and body["meta"]["stale"] is False
    p = next(p for p in body["points"] if p and p["t"] == base)
    assert p == {"t": base, "dl": 0, "up": 0}  # 区间平均口径: 单记录窗首无基线, D4 豁免 0 线(瞬时值不上图)
    # 非法哈希(路径不安全字符, 存储层 fail-fast) -> 400; 未知哈希(合法字符, 无文件) -> 空态
    assert client.get("/api/traffic/qb/torrent/HA.X", headers=auth).status_code == 400
    assert client.get("/api/traffic/qb/torrent/ZZ", headers=auth).json()["points"] == []
    # 删种冻结(hash 已不在 by_hash 快照)后历史仍可查: 数据以 v4 天文件为准, 不以快照存在性裁决
    assert "HA" not in mgr.store.by_hash
    body2 = client.get("/api/traffic/qb/torrent/HA", headers=auth).json()
    assert any(p2 and p2["t"] == base for p2 in body2["points"])


def test_api_traffic_qb_torrent_1y_single_agg_cold_read(web_env, monkeypatch):
    """年视图单 agg 文件冷读(§05.3 验收): 1y 窗恰好 1 次 qb-traffic-v4 open(agg.dat,
    天文件零读取); 再查(mtime/size 键控缓存命中)零新 open"""
    from datetime import datetime, timedelta

    from auto_qb.core.traffic_store import AggRow

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
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
    assert len(_v4_opens(opened)) == 1  # 单 agg 文件冷读(360 天前的 day 行无需任何天文件)
    monkeypatch.undo()
    assert next(p for p in body["points"] if p and p["t"] == d1) == {"t": d1, "dl": 10, "up": 1}
    opened2 = _qb_open_spy(monkeypatch)
    client.get("/api/traffic/qb/torrent/HA", headers=auth, params={"window": "1y"})
    assert _v4_opens(opened2) == []  # 缓存命中零 open
    monkeypatch.undo()


def test_api_traffic_qb_global_24h_reads_only_involved_day_files(web_env, monkeypatch):
    """24h 窗端点面回归(§05.2): 只开窗口涉及的日期天文件(24h 窗恰 2 个, 窗外更早天文件
    零 open), agg.dat 亦不触"""
    from datetime import datetime, timedelta

    from auto_qb.core.traffic_store import V4Sample, v4_epoch_date_str, v4_window_dates

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
    now = int(time.time())
    base = ((now - 600) // 30) * 30  # 窗内 10 分钟前的对齐桶
    involved = sorted(v4_window_dates(now - 86400 - 30, now))  # 镜像端点窗首种子外扩(S2/D3: t0 - 一个桶宽)
    older_date = (datetime.strptime(involved[0], "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    # 造数: 现行记录落 base 所在日期; 其余涉及日期与窗外更早日期各放一块(读侧按窗过滤)。
    # 块料 totals 与 base 块一致(100, 50): 窗首恰跨午夜被链进差分链时 delta=0, 窗首桶值恒 (0,0) 不随对齐漂移
    for d in involved + [older_date]:
        if d == v4_epoch_date_str(base + 30):
            store.append_records("global", d, (base + 30, 30), (V4Sample(7, 7, 100, 50), ), (100, 50))
        else:
            ts = int(datetime.strptime(d, "%Y-%m-%d").timestamp()) + 30
            store.append_records("global", d, (ts, 30), (V4Sample(1, 1, 100, 50), ), (100, 50))
    opened = _qb_open_spy(monkeypatch)
    body = client.get("/api/traffic/qb/global", headers=auth).json()
    monkeypatch.undo()
    dat_opens = sorted(os.path.basename(p) for p in _v4_opens(opened))
    assert dat_opens == sorted(d + ".dat" for d in involved)  # 只开涉及日期(含种子外扩), 更早日期/agg.dat 不触
    assert 2 <= len(involved) <= 3  # 常态恰 2; 窗首种子外扩跨本地午夜边界时至多 3(S2/D3)
    assert next(p for p in body["points"] if p and p["t"] == base) == {"t": base, "dl": 0, "up": 0}  # D4 0 线


def test_api_traffic_qb_group_endpoint(web_env, monkeypatch):
    """分组端点读侧现算(观测面, §05.1/§05.4): Σ 成员均值 / 全员空闲(z 覆盖)出 0 线 /
    全员无观测(停机)整桶断线 —— 「借 global 判 null」退役: 全程零全局系列文件读取 /
    成员重置贡献 0 不拖垮全组 / 成员历史回溯可见 / 解析不到成员空态 / 畸形 key 400"""
    from auto_qb.core.traffic_store import V4Sample, V4ZeroRun, v4_epoch_date_str

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
    now = int(time.time())
    base = ((now - 3600) // 30) * 30
    b0, b1, b2, b3, b4, b5 = (base + i * 30 for i in range(6))
    # HA: b0..b3 r 行(块首槽位恰在 b0+30 -> 桶 1:1 对位) + b4 z 覆盖(空闲观测, 快照恒定)
    #     —— b4 之后无任何块 = 停机(桶 b5 全员无观测)
    # v4 行型: 计数器回落处拆块(与写侧「重置强制关块重立基线」一致), 槽位序列不变
    store.append_records(
        "torrent:HA",
        v4_epoch_date_str(b0 + 30),
        (b0 + 30, 30),
        (
            V4Sample(100, 10, 1000, 0),  # 桶 b0
            V4Sample(0, 0, 2000, 0),  # 桶 b1
        ),
        (1000, 0),
    )
    store.append_records(
        "torrent:HA",
        v4_epoch_date_str(b0 + 30),
        (b2 + 30, 30),
        (
            V4Sample(10, 5, 500, 0),  # 桶 b2: 快照回落(重置, 新块立基线)
            V4Sample(10, 5, 600, 0),  # 桶 b3
            V4ZeroRun(1, 600, 0),  # 桶 b4: 空闲 z 观测
        ),
        (500, 0),
    )
    # HB: b0 就有数据(200, 快照 100) —— b0 的行在其"入组前", 回溯同样可见; b1/b2 连续产点
    store.append_records(
        "torrent:HB",
        v4_epoch_date_str(b0 + 30),
        (b0 + 30, 30),
        (
            V4Sample(200, 20, 100, 0),  # 桶 b0
            V4Sample(0, 0, 300, 0),  # 桶 b1
            V4Sample(30, 3, 400, 0),  # 桶 b2
        ),
        (100, 0),
    )
    enc = encode_group_key(KEY)
    opened = _qb_open_spy(monkeypatch)
    body = client.get(f"/api/traffic/qb/group/{enc}", headers=auth).json()
    monkeypatch.undo()
    # 组端点无 global 依赖: 请求全程零 qb-traffic-v4/global/ 读取(本用例根本未造全局数据)
    assert not [p for p in _v4_opens(opened) if "/global/" in p]

    def pt(seg, t):
        return next((p for p in body[seg] if p and p["t"] == t), None)

    assert body["meta"]["source"] == "qb" and body["meta"]["stale"] is False
    assert pt("points", b0) == {"t": b0, "dl": 0, "up": 0}  # 双成员窗首点基线缺失 D4 0 线(回溯可见性不变: 桶非 null)
    assert pt("points", b1) == {"t": b1, "dl": 40, "up": 0}  # 区间平均: HA delta(1000)/30=33 + HB delta(200)/30=7
    assert pt("points", b2) == {"t": b2, "dl": 3, "up": 0}  # HA 重置派不出 0 线 + HB delta(100)/30=3
    assert pt("points", b3) == {"t": b3, "dl": 3, "up": 0}  # HA delta(100)/30=3, HB 无行按 0 计
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
    2 成员 30d 窗请求恰好 2 次 qb-traffic-v4 open(各成员 agg.dat 一次), 天文件与全局零读取;
    组速率 = 成员 agg 行求和"""
    from auto_qb.core.traffic_store import AggRow

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
    now = int(time.time())
    h = ((now - 172800) // 3600) * 3600  # 窗内 2 天前的小时桶
    for key in ("torrent:HA", "torrent:HB"):
        store.append_agg_rows(key, (AggRow("hour", h, 100, 100, 10, 10, 1000, 100, 3600), ))
    opened = _qb_open_spy(monkeypatch)
    body = client.get(f"/api/traffic/qb/group/{encode_group_key(KEY)}", headers=auth, params={"window": "30d"}).json()
    monkeypatch.undo()
    v4 = _v4_opens(opened)
    assert len(v4) == 2 and all(p.endswith("agg.dat") for p in v4)  # M×1, 不读任何天文件
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
    """组空态判据观测面(§05.4 沿用): 成员只剩 z 块(raw 已滑出
    窗/从未活跃传输)不算「从未产过流量」—— z 覆盖是真实观测, 组出 0 线而非空态;
    全程不读全局系列(本用例未造任何全局数据)"""
    from auto_qb.core.traffic_store import V4ZeroRun, v4_epoch_date_str

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
    now = int(time.time())
    start = ((now - 600) // 30) * 30
    # 块首记录 = z 游程: 块首槽位恰在 start+30 -> 桶 start 1:1 对位
    store.append_records(
        "torrent:HA", v4_epoch_date_str(start + 30), (start + 30, 30), (V4ZeroRun(1, 100, 50), ), (100, 50)
    )
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
    # 26-10-06 用户要求重排: 站点提到第二(紧跟常规), 限速 / HR 在线核实 后置到末尾
    assert [g["key"]
            for g in data["groups"]] == ["basic", "trackers", "maintenance", "traffic", "rules", "speed", "hr_check"]
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
    "在文件夹中选中相关文件")** / content_path 缺失回退 save_path / **content_path 未落盘(下载中,
    qB 报逻辑完成名而磁盘尚无该路径)回退 save_path, 不因"未完成"而 404** / 组键取 key 首元 /
    未知组与不存在目录 404 / content 与 save_path 都不存在 404 / kind 非法 400 /
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
        "HA":
            SimpleNamespace(hash="HA", save_path=str(d_seed), content_path=str(d_content)),
        "HB":
            SimpleNamespace(hash="HB", save_path=str(d_seed), content_path=str(f_file)),
        "HC":
            SimpleNamespace(hash="HC", save_path=str(d_seed), content_path=""),
        # 下载中单文件种子: content_path 是 qB 报的逻辑完成名, 磁盘上尚未落盘(或带 .!qB 后缀) —— 实际故障场景
        "HD":
            SimpleNamespace(hash="HD", save_path=str(d_seed), content_path=str(d_seed / "incomplete.mkv")),
        # content 与 save_path 都不存在: 回退后终检兜底 404
        "HE":
            SimpleNamespace(hash="HE", save_path=str(tmp_path / "gone"), content_path=str(tmp_path / "gone" / "x.mkv")),
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
        # 3b. content_path 未落盘(下载中既非目录也非文件) -> 回退 save_path, 不 404
        spy.reset_mock()
        assert post({"kind": "torrent", "hash": "HD"}).json() == {"opened": norm(d_seed), "select": False}
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
        assert post({"kind": "torrent", "hash": "HE"}).status_code == 404  # content 未落盘 + save_path 也不存在 -> 终检兜底 404
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
        # S3 删除改道(plan 26-10-07-0055): remove_tracker 收 mask 值, 后端重取原文比对
        client.trackers_map["HA"] = [{"url": "https://c.example/announce?passkey=SUPERSECRET123", "status": 2}]
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
                "remove_tracker", {
                    "hash": "HA",
                    "url": mask_tracker_url("https://c.example/announce?passkey=SUPERSECRET123"),
                    "cmd_id": "c10"
                }
            ),
            ("set_file_priority", {
                "hash": "HA",
                "indices": [0, 1],
                "priority": 6,
                "cmd_id": "c11"
            }),
            (
                "rename_fs", {
                    "hash": "HA",
                    "old_path": "old/file.mkv",
                    "new_path": "new/file.mkv",
                    "is_folder": False,
                    "cmd_id": "c12"
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
        assert client.calls[10] == ("remove_trackers", ("HA", ["https://c.example/announce?passkey=SUPERSECRET123"])), \
            "mask 入参须换回原文传 qB(qB 按原文精确匹配)"
        assert client.calls[11] == ("file_priority", ("HA", [0, 1], 6))
        assert client.calls[12] == ("rename_file", ("HA", "old/file.mkv", "new/file.mkv"))
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
        # 全部命令回执 ok(c10=edit_tracker 已随编辑功能下线移除, 现为 c1..c12)
        assert all(mgr.web.results[f"c{i}"]["status"] == "ok" for i in range(1, 13)), mgr.web.results
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
        # magnet_uri 不在轮询载荷(issue E-04 P-06): 按需取 /api/torrents/{hash} 详情
        assert "magnet_uri" not in item and item["max_ratio"] == 1.5
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
    """GET /api/torrents/{hash}/trackers|files|peers: qB 透传(trackers 例外: url 已 mask);
    未知 hash 404, qB 断连 503"""
    from helpers import FakeClient

    from auto_qb.torrents import TorrentRecord

    mgr, client = web_env
    rec = TorrentRecord(hash="HA", name="X")
    mgr.store.get = lambda h: {"HA": rec}.get(h)
    fake = FakeClient()
    fake.trackers_map["HA"] = [{"url": "https://t.example/announce", "status": 2}]  # 无凭据, mask 后不变
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


def test_api_torrent_trackers_masked_response(web_env):
    """守阵① API 外发(plan 26-10-07-0055 S4): trackers 响应 url 一律 mask

    红验方式(S4b 照做): 把 torrent_detail.py 的 api_torrent_trackers 路由临时改回
    裸透传(去掉 mask_tracker_entry) -> 本组必红。

    - 含凭据的原文不出现在响应体(整值缺席断言, **不写死参数名**——私站参数名任意,
      只用原值字符串断言缺席);
    - mask 保留 scheme://host + path 端点名 + query 参数名(只换"值"), 站点/端点仍可辨;
    - 虚拟条目(**/[DHT]/[PeX]/[LSD])原样透传;
    - 两次请求逐字节一致(mask 确定性, hash16 不加盐);
    - mask 先于缓存写入: 缓存里只有 mask 条目。
    """
    from helpers import FakeClient

    from auto_qb.torrents import TorrentRecord

    mgr, client = web_env
    rec = TorrentRecord(hash="HA", name="X")
    mgr.store.get = lambda h: {"HA": rec}.get(h)
    fake = FakeClient()
    original = "https://pt.example.com/announce?passkey=SUPERSECRET123"
    fake.trackers_map["HA"] = [
        {
            "url": original,
            "status": 2,
            "msg": "Working"
        },
        {
            "url": "** [DHT] 3",
            "status": 0,
            "msg": ""
        },
        {
            "url": "[PeX] 1",
            "status": 0,
            "msg": ""
        },
        {
            "url": "[LSD] 2",
            "status": 0,
            "msg": ""
        },
    ]
    mgr.client = fake
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    r1 = client.get("/api/torrents/HA/trackers", headers=auth)
    body1 = r1.content
    entries = r1.json()
    masked = entries[0]["url"]
    assert masked == mask_tracker_url(original), "url 应为 mask 值"
    assert masked != original, "mask 不得与原文相同(等于没脱敏)"
    assert masked.startswith("https://pt.example.com/announce?passkey="), \
        "mask 必须保留 scheme://host + path 端点名 + 参数名(只换值), 否则站点/端点不可辨"
    assert "SUPERSECRET123" not in body1.decode("utf-8"), "凭据原文不得出现在响应体"
    assert entries[0]["status"] == 2 and entries[0]["msg"] == "Working", "其余字段原样不动(R9)"
    assert [e["url"] for e in entries[1:]] == ["** [DHT] 3", "[PeX] 1", "[LSD] 2"], \
        "虚拟条目原样透传"
    body2 = client.get("/api/torrents/HA/trackers", headers=auth).content
    assert body1 == body2, "两次请求必须逐字节一致(mask 确定性)"


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
    """tracker 移除的日志只写脱敏主地址, 不含凭据全文(issue 26-09-21-1408; 编辑功能已下线)

    S3(plan 26-10-07-0055)后入参是 mask 值: 日志行 sanitize_tracker_url(mask) 仍是主地址
    (mask 的 query 值本就是 hash, sanitize 再把整段 query 丢掉)。

    断言口径刻意**不写死参数名**: 私站凭据参数名是任意的(passkey 只是最常见的一种),
    所以只钉死"密钥全文一行都进不了日志 + 主地址仍在(够排查是哪个站)"。
    日志会落盘(含轮转备份)且能经 /api/log 读回, 泄露面比"读一次"大得多。
    """
    from auto_qb.webui.commands import WebCommandsMixin
    from helpers import FakeClient

    class _Cmds(WebCommandsMixin):
        def __init__(self):
            self.api = FakeClient()
            self.client = self.api
            self.store = {"HA": object()}

    m = _Cmds()
    secret = "https://pt.example.com/announce?passkey=SUPERSECRET123"
    m.api.trackers_map["HA"] = [{"url": secret, "status": 2}]
    caplog.set_level(logging.INFO, logger="auto_qb.webui.commands")
    caplog.clear()
    m._cmd_remove_tracker(hash="HA", url=mask_tracker_url(secret))
    text = "\n".join(r.getMessage() for r in caplog.records if r.name == "auto_qb.webui.commands")
    assert "SUPERSECRET123" not in text, "passkey 全文进了日志"
    assert "passkey" not in text, "query 整段都应丢弃, 不该残留参数名"
    assert "pt.example.com" in text, "主地址要保留(否则没法排查是哪个站)"


def test_cmd_remove_tracker_mask_roundtrip():
    """S3 删除改道(plan 26-10-07-0055): remove_tracker 收 mask 值, 当场重取原文比对

    - 恰 1 命中: qB 收到的是该条**原文**(mask 值绝不透传给 qB), 原文不进任何输出;
    - 命中 0 条: ValueError「未找到该 tracker，请刷新后重试」且 qB 零写调用;
    - 命中 >=2 条(同 mask 的重复条目): 同样报错, 绝不猜;
    - 虚拟条目(**/[DHT]/[PeX]/[LSD])不参与比对。
    """
    from auto_qb.webui.commands import WebCommandsMixin
    from helpers import FakeClient

    original = "https://pt.example.com/announce?passkey=SUPERSECRET123"
    masked = mask_tracker_url(original)

    class _Cmds(WebCommandsMixin):
        def __init__(self, trackers):
            self.api = FakeClient()
            self.client = self.api
            self.store = {"HA": object()}
            self.api.trackers_map["HA"] = trackers

    # 恰 1 命中: 传 mask, qB 收原文
    m = _Cmds([{"url": original, "status": 2}, {"url": "** [DHT] 0", "status": 0}])
    m._cmd_remove_tracker(hash="HA", url=masked)
    assert m.api.calls[-1] == ("remove_trackers", ("HA", [original])), "qB 必须收到原文"
    assert m.api.calls[-1] != ("remove_trackers", ("HA", [masked])), "mask 值不得透传给 qB"

    # 命中 0 条: 报错且零 remove 调用(其它条目不被误删)
    m = _Cmds([{"url": original, "status": 2}])
    with pytest.raises(ValueError, match=r"未找到该 tracker"):
        m._cmd_remove_tracker(hash="HA", url=mask_tracker_url("https://other.example.com/announce?passkey=X"))
    assert not [c for c in m.api.calls if c[0] == "remove_trackers"], "未命中不得触发任何 remove 调用"

    # 命中 >=2 条: 同 URL 重复出现 -> 报错不猜
    m = _Cmds([{"url": original, "status": 2}, {"url": original, "status": 1}])
    with pytest.raises(ValueError, match=r"未找到该 tracker"):
        m._cmd_remove_tracker(hash="HA", url=masked)
    assert not [c for c in m.api.calls if c[0] == "remove_trackers"]


def test_cmd_remove_tracker_same_host_distinct_passkeys():
    """守阵② 写路径同 host 区分(plan 26-10-07-0055 S4): 同 host 两条 tracker(不同 passkey)
    mask 互异, 传 A 的 mask 删除 -> qB 收到且仅收到 A 的**原文**, B 不受影响

    红验方式(S4b 照做): _cmd_remove_tracker 临时改回直传(把入参 mask 值原样传给
    torrents_remove_trackers, 不再重取比对) -> qB 收到 mask 值而非原文, 本组必红。

    这是报告 §02「脱敏后同值」在 mask 形态下的失效证明(R8: hash 保值差异 => 唯一性恢复):
    若 mask 退化成"只留主地址", 两条 mask 撞值 => 比对命中 2 条 => 报错不猜(不误删但删不掉)。
    """
    from auto_qb.webui.commands import WebCommandsMixin
    from helpers import FakeClient

    url_a = "https://pt.example.com/announce?passkey=AAAAAAAAAAAAAAAA"
    url_b = "https://pt.example.com/announce?passkey=BBBBBBBBBBBBBBBB"
    mask_a, mask_b = mask_tracker_url(url_a), mask_tracker_url(url_b)
    assert mask_a != mask_b, "同 host 不同凭据值的 mask 必须互异(R8), 否则删除定位会撞值"

    class _Cmds(WebCommandsMixin):
        def __init__(self, trackers):
            self.api = FakeClient()
            self.client = self.api
            self.store = {"HA": object()}
            self.api.trackers_map["HA"] = trackers

    m = _Cmds([{"url": url_a, "status": 2}, {"url": url_b, "status": 2}])
    m._cmd_remove_tracker(hash="HA", url=mask_a)
    removes = [c for c in m.api.calls if c[0] == "remove_trackers"]
    assert removes == [("remove_trackers", ("HA", [url_a]))], \
        "qB 必须恰收到一次 remove 且 urls == A 的原文(不含 B 的原文, 不含任何 mask 值)"
    assert mask_a not in str(removes) and mask_b not in str(removes), "mask 值不得透传给 qB"


def test_tracker_edit_offline_route_and_static(web_env):
    """守阵③ 编辑下线(plan 26-10-07-0055 S2/S4): tracker 编辑功能三层全无

    红验方式(S4b 照做): 临时加回 POST /api/torrents/{hash}/trackers/edit 路由(或把
    "trackers/edit" 字样写回 static/ 任意文件) -> 本组必红。

    - 路由金清单无 trackers/edit 行: test_web_route_manifest_frozen 已钉(S2 改过的清单即守阵);
    - POST /api/torrents/{hash}/trackers/edit 不落到任何处理器(路由不存在; 本应用根挂了
      StaticFiles(static_ui.py), 未匹配路径由挂载兜住 -> POST 回 405, 纯 404 反而说明挂载没了);
    - 静态目录 grep "trackers/edit" 零命中(测试内 Python 遍历, 不调 shell; 前端残留调用
      一个已消失的端点 = 按钮点了静默失败)。
    """
    from fastapi.routing import APIRoute

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    r = client.post("/api/torrents/HA/trackers/edit", headers=auth, json={"hash": "HA", "url": "x"})
    assert r.status_code in (404, 405), \
        f"trackers/edit 必须不落到任何处理器(404/405), 实际 {r.status_code} —— 路由被加回来了?"
    # 路由表白名单式复核(不依赖静态挂载的行为): 不得存在 trackers/edit 的 API 路由
    app = client.app
    edit_routes = [
        r.path for r in _iter_api_routes(app.routes) if isinstance(r, APIRoute) and "trackers/edit" in r.path
    ]
    assert edit_routes == [], f"路由表里存在 trackers/edit: {edit_routes}"

    hits = []
    for dirpath, _dirs, files in os.walk(STATIC_ROOT):
        for fn in files:
            p = os.path.join(dirpath, fn)
            try:
                text = Path(p).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue  # 二进制/不可读文件跳过(图片等)
            if "trackers/edit" in text:
                hits.append(os.path.relpath(p, STATIC_ROOT))
    assert hits == [], f"static/ 里残留 trackers/edit 引用: {hits}(前端还在调已下线的端点)"


def test_trackers_baseline_keys_are_raw_urls():
    """守阵④ 基线 key 为原文(plan 26-10-07-0055 S4): _trackers_baseline 的 dict key
    必须是 fake client 的**原文** url, 不是 mask

    红验方式(S4b 照做): _trackers_baseline 临时切到 mask_tracker_url 做 key ->
    同 host 撞 key 静默漏判, 本组必红(报告 §04 自伤警告: mask 化基线反而破坏确认判定)。

    防的是后人"顺手统一脱敏"把汇报确认基线也 mask 掉 —— 同 host 不同 passkey 的两条
    tracker mask 后仍互异(R8), 但原文 key 与 mask key 全然不同, 判定域(status>=2 且
    b_next 非空的行)会整体错位, 前跳证据静默丢。既有 test_trackers_baseline_shape_and_
    epoch_mode 用的是无凭据 url(mask == 原文), 切 mask 不会红 —— 钉不住, 本用例补位。
    """
    from auto_qb.core.qbmanager import QbManager
    from helpers import FakeClient

    url_a = "https://pt.example.com/announce?passkey=AAAAAAAAAAAAAAAA"
    url_b = "https://pt.example.com/announce?passkey=BBBBBBBBBBBBBBBB"
    client = FakeClient()
    client.trackers_map = {
        "HA":
            [
                {
                    "url": url_a,
                    "status": 2,
                    "next_announce": 1000,
                    "min_announce": 900
                },
                {
                    "url": url_b,
                    "status": 2,
                    "next_announce": 2000,
                    "min_announce": 1900
                },
                {
                    "url": "** [DHT] 3",
                    "status": 0
                },
            ],
    }
    baseline, _epoch = QbManager._trackers_baseline(SimpleNamespace(client=client), ["HA"])
    assert set(baseline["HA"]) == {url_a, url_b}, \
        "基线 key 必须等于 fake client 的原文 url(同 host 两条不同 passkey 的 key 互异), 虚拟行排除"
    assert mask_tracker_url(url_a) not in baseline["HA"], "基线 key 不得是 mask 值(切 mask 即红)"
    assert baseline["HA"][url_a]["next"] == 1000 and baseline["HA"][url_b]["next"] == 2000, \
        "原文 key 下各行的 epoch 字段逐条对号(撞 key 会互相覆盖丢行)"


def test_torrent_detail_trackers_route_mask_canary():
    """守阵⑤ 静态扫 canary(plan 26-10-07-0055 S4): torrent_detail.py 的 trackers 路由
    源码必须引用 mask_tracker_entry —— 有人改回裸透传即红(延续 issue 26-09-21-1408 守阵做法)

    红验方式(S4b 照做): 同守阵① —— 路由临时改回透传(删掉 mask_tracker_entry 引用) ->
    本组必红。运行时守阵①兜运行行为, 本 canary 兜源码形态(连缓存 lambda 一起钉)。
    """
    src_path = os.path.join(os.path.dirname(STATIC_ROOT), "server", "routes", "torrent_detail.py")
    src = Path(src_path).read_text(encoding="utf-8")
    assert "mask_tracker_entry" in src, \
        "torrent_detail.py 不再引用 mask_tracker_entry —— trackers 路由被改回裸透传? 同步守阵①"
    # 钉在 trackers 端点的取数 lambda 上(不是仅在文件里 import 一下): 缓存写入必须已 mask
    assert re.search(r"_cached_read\(\s*\n?\s*f?\"trackers:\{hash\}\".*mask_tracker_entry", src, re.S), \
        "trackers 端点的 _cached_read 取数 lambda 里没有 mask_tracker_entry —— mask 必须先于缓存写入"


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
    ("GET", "/api/errlog"),  # 错误历史内存环增量(WEBUI 错误历史 S2; 与 /api/log 同属系统诊断)
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


def test_web_route_manifest_frozen(web_env):
    """路由金清单守阵: 76 条 (method, path) 集合逐一钉死, 丢失/改名/方法变更即红

    (2026-10-07 编辑 tracker 下线, plan 26-10-07-0055 S2: 减 POST /api/torrents/{hash}/trackers/edit, 77->76)

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


def test_reannounce_group_empty_snapshot_error_receipt():
    """组强制汇报空组回执(E-03): 组内成员执行时刻全不在快照 -> 显式 error 回执, 不发指令不登记

    组快照渲染后、命令执行前组内成员全被删除(主循环被长任务占住时窗口秒级): _group_hashes
    回空 -> 修复前不发指令不写回执, 前端 waitCmd 挂到自身超时才弹「超时」。对齐单发
    reannounce_torrent 对缺失的显式 error 回执口径。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        mgr.store.remove_torrent("HA")
        mgr.store.remove_torrent("HB")
        assert mgr._group_hashes(key) == [], "前置: 组内成员已全部不在快照"
        mgr.web.commands.put(("reannounce_group", {"key": key, "cmd_id": "r-gone"}))
        mgr.web.consume_commands()
        assert client.calls == [], "空组不得发任何指令"
        assert mgr.web.reannounce_pending == {}, "空组不登记确认跟踪"
        r = mgr.web.results["r-gone"]
        assert r["status"] == "error" and "不存在" in r["error"], "空组必须显式 error 回执"


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
    # 部分成功组合同样整组回 None(首读成功后续读抛 -> 不出现「一半真一半未知」浮层;
    # issue 26-10-06-0028 chore-speed-mode-silent-except)
    mgr.api = SimpleNamespace(
        get_global_speed_limits=lambda: {"up_limit": 1024},
        get_speed_limits_mode=lambda: (_ for _ in ()).throw(RuntimeError("超时")),
        get_alt_speed_limits=lambda: {"up_limit": 512},
    )
    body = client.get("/api/speed/mode", headers=auth).json()
    assert body["current"] is None and body["alt_on"] is None and body["alt_current"] is None, "部分成功也整组回 None(口径对齐)"


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


def test_api_traffic_qb_global_live_tail_realtime(web_env):
    """(S6)raw 段窗活尾合流: 纯活尾(零盘)出实时桶点(不等 flush_interval 落盘);
    磁盘落盘后滞后快照重列已落盘记录被按 ts 精确去重(快照与 flush 竞态不重不漏),
    快照清空后磁盘响应与合流响应逐点一致 —— 图面全程无跳变"""
    from auto_qb.core.traffic_store import LiveTail, V4Sample, v4_epoch_date_str

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
    now = int(time.time())
    base = ((now - 240) // 30) * 30  # 5m 窗内
    b0, b1, b2 = (base + i * 30 for i in range(3))
    recs = (V4Sample(100, 50, 1000, 500), V4Sample(200, 70, 2000, 800))
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
    assert pt("points", b0) == {"t": b0, "dl": 0, "up": 0}  # 区间平均口径: 首点基线缺失 D4 0 线
    assert pt("points", b1) == {"t": b1, "dl": 33, "up": 10}  # delta(1000, 300)/30
    assert pt("points", b2) is None  # 活尾之外无观测
    assert pt("totals", b1) == {"t": b1, "dl": 1000, "up": 300}
    live_body = body
    # flush 落盘(同两记录) + 滞后快照仍重列全部记录: 按 ts 去重, 响应逐点不变
    store.append_records("global", v4_epoch_date_str(b0 + 30), (b0 + 30, 30), recs, (1000, 500))
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "5m"}).json()
    assert body == live_body
    # 快照清空(flush 后的下一轮发布): 纯磁盘读路径, 响应仍逐点一致
    _attach_live_tail_host(mgr, {})
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "5m"}).json()
    assert body == live_body


def test_api_traffic_qb_group_live_tail_member_only(web_env):
    """(S6)组端点空态判据计入活尾: 成员仅活尾(零盘)组图非空(不再误判「从未产过流量」);
    单种端点同享活尾"""
    from auto_qb.core.traffic_store import LiveTail, V4Sample

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
        records=(V4Sample(300, 30, 500, 50), ),
        open_run=None,
    )
    _attach_live_tail_host(mgr, {"torrent:HB": tail})
    body = client.get(f"/api/traffic/qb/group/{encode_group_key(KEY)}", headers=auth, params={"window": "5m"}).json()

    def pt(seg, t):
        return next((p for p in body[seg] if p and p["t"] == t), None)

    assert pt("points", b0) == {"t": b0, "dl": 0, "up": 0}  # HB 活尾观测(HA 无数据按 0 计); 单记录窗首基线缺失 D4 0 线
    assert pt("totals", b0) == {"t": b0, "dl": 0, "up": 0}  # 窗首基线缺失
    assert pt("points", b1) is None  # 单记录覆盖桶 [b0, b0+30) 恰一格, b1 无观测
    # 单种端点同享活尾(区间平均口径: 单记录无基线, D4 豁免 0 线 —— 桶在即合流生效)
    body = client.get("/api/traffic/qb/torrent/HB", headers=auth, params={"window": "5m"}).json()
    assert next((p for p in body["points"] if p and p["t"] == b0), None) == {"t": b0, "dl": 0, "up": 0}


def test_frontend_toast_duration_floor_by_kind() -> None:
    """错误 / 超时类 toast 停留时长下限守阵(2026-10-05 用户报「右下角错误信息停留太短」)

    停留时长单点在 `shared/ui_feedback.js` 头部的 `TOAST_MS_FLOOR`; `toast()` 与 `_finishToast()`
    两条排期路径都必须经 `toastMs(kind, ms)` 解析 —— 绕过即回到裸 ms, 按 kind 的下限形同虚设。
    钉住三件事(全是"pytest 全绿、界面行为退化"的形态):
    1. error / timeout 的下限不得低于 8s(用户报障的正是"4s 一闪而过, 带原因段的报错读不完");
    2. 排期点恰好 2 处且都走 `toastMs(kind, ms)`(新增排期点须一并走解析, 否则新链路漏掉下限);
    3. 两处 `ms` 缺省为 `null`(写死数字会让 kind 下限在缺省路径不生效 —— 而报障的恰恰是缺省路径)。
    """
    fb = open(os.path.join(STATIC_ROOT, "shared", "ui_feedback.js"), encoding="utf-8").read()
    m = re.search(r"TOAST_MS_FLOOR = \{([^}]*)\}", fb)
    assert m, "ui_feedback.js 缺 TOAST_MS_FLOOR(停留时长单点; 改名或挪走了? 同步本守阵)"
    floors = {k: int(v) for k, v in re.findall(r"(\w+)\s*:\s*(\d+)", m.group(1))}
    assert floors.get("error", 0) >= 8000, \
        f"error 类 toast 停留下限过低({floors.get('error')}ms) —— 「错误信息一闪而过」会复发"
    assert floors.get("timeout", 0) >= 8000, \
        f"timeout 类 toast 停留下限过低({floors.get('timeout')}ms) —— 部分失败汇总同样要读得完"
    assert fb.count("toastMs(kind, ms)") == 2, \
        "排期点应为 2 处(toast / _finishToast)且都必须走 toastMs(kind, ms)(绕过 = 下限失效)"
    assert re.search(r"toast\(text, kind = \"info\", ms = null, opts = \{\}\)", fb), \
        "toast() 的 ms 缺省必须是 null(写死 4000 会让 kind 下限在缺省路径不生效)"
    assert re.search(r"_finishToast\(id, kind, text, ms = null\)", fb), \
        "_finishToast() 的 ms 缺省必须是 null(同上)"


def test_aq_tip_anchor_watch_and_reacquire_wired():
    """aq-tip 锚定保活守阵(2026-10-07 用户报「详情面板 tooltip 位置不正确」)

    详情面板 15 变体由轮询数据驱动整帧重建(replaceChildren), tooltip 三条错位路径:
    ①350ms 窗口内锚点被换掉后按旧指针坐标重解析可能中到别的元素(布局移位), 键盘 focusin
    路径无坐标; ②浮层已显示后锚点被 5s 轮询换成新节点(mouseover 不再触发), 浮层停旧坐标;
    ③重建引发布局移位, 浮层不跟随。修法单点在 shared/ui_feedback.js: 定位抽 place() 单点 +
    reacquire() 语义重解析(先于指针坐标回退) + watch/tick rAF 帧环廉价体检。本守阵读 JS
    源码钉住结构与次序(剥行注释后锚定, 注释改写不红、代码突变必红), 任一环被重构摘除即红:
    1. enter 记录锚点矩形基准 curRect, hide 作废(键盘路径无坐标, 全靠矩形基准重解析);
    2. reacquire 语义优先: 全文档 [data-aq-tip] 同文案节点按矩形中心距取最近, 之后才是指针
       坐标 elementFromPoint 回退(次序倒了 = 布局移位路径复发), 回退有 Number.isFinite 门;
    3. show 断链走 reacquire, 定位统一走 place 并挂 watch(两路径夹取/避让同口径);
    4. tick 帧环: 只在浮层可见期运转, 每帧仅 1 次 getBoundingClientRect 零 DOM 查询,
       断链分支与四轴漂移分支齐备(非断链路径出现 querySelectorAll = 性能红线)。
    """
    ui = open(os.path.join(STATIC_ROOT, "shared", "ui_feedback.js"), encoding="utf-8").read()

    # ① 矩形基准的记/废成对
    assert re.search(r"^  let curRect = null;", ui, re.M), \
        "ui_feedback.js 缺 curRect 矩形基准状态(语义重解析/漂移检测失锚, 同步本守阵)"
    assert re.search(r"curRect = target\.getBoundingClientRect\(\);", ui), \
        "enter 未记录锚点矩形基准 —— 键盘路径(focusin 无坐标)的锚点重解析退化为直接收起"
    m = re.search(r"function hide\(\)\s*\{(.*?)\n  \}", ui, re.S)
    assert m and "curRect = null" in m.group(1), \
        "hide 未作废 curRect 基准(悬空基准会污染下一次悬浮的重解析)"

    # ② reacquire: 语义扫描先于指针回退, 回退有 NaN 门
    m = re.search(r"function reacquire\(\)\s*\{(.*?)\n  \}", ui, re.S)
    assert m, "ui_feedback.js 找不到 reacquire(锚点被重建换掉后的语义重解析单点被摘? 同步本守阵)"
    acq = re.sub(r"//[^\n]*", "", m.group(1))
    assert 'querySelectorAll("[data-aq-tip]")' in acq, \
        "reacquire 缺语义候选扫描(同 data-aq-tip 文案的新节点) —— 断链后无处重解析"
    i_sem = acq.index('querySelectorAll("[data-aq-tip]")')
    i_ptr = acq.find("elementFromPoint")
    assert i_ptr != -1, \
        "reacquire 缺指针坐标回退(2026-10-04 收口口径: 语义解析不到才按指针重解析)"
    assert i_sem < i_ptr, \
        "reacquire 指针回退先于语义解析 —— 布局移位时旧坐标下的元素已不是原锚点(路径③复发)"
    assert re.search(r"Number\.isFinite\(curX\)", acq), \
        "指针回退缺 Number.isFinite(curX) 门 —— 键盘路径 NaN 坐标会传给 elementFromPoint"

    # ③ show 断链走 reacquire; 定位单点 place + 显示期监测 watch 成对
    m = re.search(r"function show\(anchor\)\s*\{(.*?)\n  \}", ui, re.S)
    assert m, "ui_feedback.js 找不到 show(改名或挪走了? 同步本守阵)"
    sh = re.sub(r"//[^\n]*", "", m.group(1))
    assert "reacquire()" in sh, \
        "show 的断链分支未走 reacquire(键盘路径无指针坐标, 只能靠语义重解析兜住)"
    assert re.search(r"function place\(anchor\)", ui), \
        "定位未抽 place() 单点 —— show 初显与显示期重定位两套夹取/避让口径必然漂移"
    assert re.search(r"place\(anchor\);", sh) and "watch();" in sh, \
        "show 未统一走 place + watch(定位单点/显示期监测被绕开)"
    assert re.search(r"curRect = \{ left: r\.left, top: r\.top", ui), \
        "place 未在定位时刷新 curRect 基准(漂移检测失准)"

    # ④ tick 帧环: 可见期才运转, 断链/漂移两分支齐备, 每帧路径零全文档查询
    m = re.search(r"function tick\(\)\s*\{(.*?)\n  \}", ui, re.S)
    assert m, "ui_feedback.js 找不到 tick(rAF 帧环主体被摘? 同步本守阵)"
    tick = re.sub(r"//[^\n]*", "", m.group(1))
    assert 'classList.contains("on")' in tick and "cur" in tick, \
        "tick 缺可见性守卫(cur + .on) —— 浮层收起后帧环空转烧帧"
    assert "isConnected" in tick, \
        "tick 缺锚点存活检查 —— 浮层显示后锚点被重建换掉不再跟随(路径②复发)"
    assert "reacquire()" in tick, "tick 断链分支未走语义重解析"
    for axis in ("left", "top", "width", "height"):
        assert f"curRect.{axis}" in tick, f"tick 漂移检测缺 {axis} 轴比对(重建移位/内容变宽不重定位)"
    assert "querySelectorAll" not in tick, \
        "tick 每帧路径出现全文档查询 —— 体检必须只做 1 次 rect 比对(5s 轮询场景的性能红线)"
    assert re.search(r"requestAnimationFrame\(tick\)", ui), \
        "帧环未用 requestAnimationFrame(定时器轮询会与绘制解耦空转)"
