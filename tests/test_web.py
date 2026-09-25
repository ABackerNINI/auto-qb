"""test_web 测试计划: WEB UI 后端(FastAPI 鉴权/API/命令投递/设置读写)

## 测试计划(每个测试函数一条)
- test_api_requires_token: 无/错密钥访问 /api/* -> 401
- test_config_public_endpoint_no_auth: 公开端点 /api/config/public 免 token 只读本机免鉴权标志(不含机密)
- test_skip_local_verify_loopback_bypass: web.skip_local_verify=true 时本机连接免密钥放行(提示日志 **INFO 级**、**每进程只记一次**), 对外/远端仍强制鉴权
- test_skip_local_verify_default_off: 默认关闭(保守), 本机连接也不免鉴权
- test_api_status_and_groups: 状态与分组快照读取(经注入的 manager; status 含 version)
- test_api_expr_eval_endpoint: 表达式试算端点(校验-only / 按种子求值 + 中间值 / 名字错误 / 种子不存在)
- test_static_assets_disable_heuristic_cache: 静态资源带 no-cache(/api 不受影响), 防升级后仍加载旧前端(UI 目录化路径: atlas/prism/shared)
- test_ui_root_and_legacy_newui_redirect: / -> 307 /atlas/; 旧 /newui/* 书签 -> 307 /prism/*
- test_frontend_static_bundle_health: 前端静态资源静态守阵(冲突标记/注释孤儿续行/node --check 语法校验/CSS 规则漏闭合/<transition> 吞弹窗/静态引用缺失/追剧视图集成员取 hash 未走 memberHashesOf/STATE_RANK 与后端 _SHOW_STATE_RANK 漂移 / 页面挂件类名必须有对应 CSS 规则 —— 均为"pytest 全绿但界面废掉"的故障形态)
- test_frontend_member_window_functions_live_in_methods: 成员行窗口三个带参函数(memberWin/memberPadTop/memberPadBottom)必须落在 methods 块, 不能进 computed —— Vue 3 computed 是无参 getter, 带参会导致整表白屏(issue 26-09-21-0247)
- test_frontend_computed_not_invoked_as_function: computed 成员不得以 `this.X()` 调用(拿到的是 getter 的值, 再 () 会 TypeError) —— 经典设置页改"数值+单位"字段的数字会整页白屏
- test_frontend_dist_segments_aggregates_per_view: distSegments 必须按 viewMode 取数(torrents / shows / groups), 不能只数 this.groups —— 种子页次导航 chips 会全空(issue 26-09-21-0247)
- test_frontend_cols_store_single_setitem_site: COLS_STORE_KEY 的 setItem 全仓恰好一处(persistPage 内) —— 散写回潮即红
- test_frontend_persist_page_takes_intent_only: persistPage 只收意图态(colHidden/colOrder/colW), 生效宽度 colWidths 不得进持久化路径(双轨模型铁律, plan 26-09-21-1551)
- test_frontend_col_manual_flag_not_revived: 反向守阵 —— manual 标志位(colManual)不得复活(v5 下 w 非空即固化页)
- test_frontend_cols_legacy_keys_have_migration: LEGACY_COLS_KEYS 键链必须伴随 migrateLegacyToV5 迁移(v3->v4 清零事故的机检)
- test_frontend_cols_empty_hint_names_browser_clear_cause: 空存储提示必须点名浏览器站点级"关闭窗口时清除 Cookie 和站点数据"这条通道 + 给自查路径 + sessionStorage 会话级去重(2026-09-24 取证: cookie 例外 127.0.0.1,* setting=4)
- test_frontend_page_location_persisted: 顶层 page 与设置分区必须持久化(读侧白名单 / 写侧单漏斗) + 启动补一次 cfgLoad + 分区 key 对 schema 校验 —— 否则"设置页刷新掉回种子页"复发(2026-09-25 用户报)
- test_api_group_commands_enqueue: pause/resume/reannounce/delete 命令入队(key 编解码回原值)
- test_api_group_malformed_key_returns_400: 畸形分组 key(base64 非法/非 JSON/结构不符)回 400 而非 500
- test_api_delete_with_files_flag: delete 命令透传 delete_files 标志
- test_api_cmd_result_endpoint: 命令端点返回 cmd_id; /api/cmd/{id} 查询回执(pending -> 结果)
- test_api_enqueue_wakes_main_loop: 投递用户命令唤醒主循环; 反向守卫——自投递命令须登记进 SELF_POSTED_COMMANDS(防自激)
- test_api_traffic_history_endpoint: /api/traffic/history 透出快照 history; 缺省空数组
- test_config_schema_endpoint: 图形化配置元数据端点(分组/插件/热重载级别)
- test_config_tree_roundtrip: 配置树读取/保存写回文件并投递热重载命令
- test_config_tree_invalid_rejected: 非法配置树 -> 400 且不写回
- test_config_tree_restart_field_fallback: R 级字段(data_dir)提交后被回退为磁盘旧值
- test_config_tree_requires_config_root: 缺少 config 根段 -> 400
- test_config_tree_preserves_comments: round-trip 写盘保留已有键的注释
- test_web_token_not_printed_in_logs: 生成的访问密钥不进任何日志(WARNING 会被 notify 推送, 且 /api/log 可读回)
- test_config_tree_masks_secrets: /api/config 掩码敏感字段, 且"读取→原样保存"不会把密码写成占位串
- test_group_key_codec_roundtrip: 分组 key 编解码往返(含中文/多文件)
- test_build_group_view: 分组视图组装(组名/合计/成员站点/单种子大小与总大小/标签/分类/保存路径)
- test_views_published_atomically_when_rebuilt_concurrently: 并发重建(主循环线程 vs Web 线程)时四份视图与版本号必须**同一轮**发布, 不得出现"半新半旧"
- test_build_group_view_member_num_seeds_fields: 组视图成员透出 num_seeds/num_leechs/num_complete/num_incomplete
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
- test_search_torrents_building_triggers: 索引脏时 building=True 并投递构建命令
- test_api_search_endpoint: GET /api/search 转发与鉴权(含空查询)
- test_api_paths_endpoint: GET /api/paths 已知目录聚合(组 save_path + 现有种子 save_path 归一去重排序; 空路径跳过; 无副作用; 鉴权)
- test_api_open_path_endpoint: POST /api/open-path 打开目标文件夹(FX-14 + R10-10) —— 目录/单文件(select=True 定位选中)、回退 save_path、组键首元、未知目标 404、kind 非法 400、客户端传 path 被忽略、无副作用、鉴权
- test_api_fs_dirs_endpoint: GET /api/fs/dirs 目录浏览(R10-11) —— 首屏允许根/只列目录(排除文件与越界符号链接)/上溯到根为止/.. 穿越与白名单外 403/不存在 404/无白名单空返回/鉴权/无副作用
- test_api_fs_dirs_case_sibling_is_outside_whitelist: **仅 Linux** —— 大小写兄弟目录(/x/Media 与 /x/media)必须判为越界, 白名单归一不得做 NTFS 式折叠(折叠 => 越界放行, fail-open)
- test_api_fs_mkdir_endpoint: POST /api/fs/mkdir 新建目录(R10-11) —— 正常创建/重名目录幂等/重名文件 409/名字含分隔符或点为 400/白名单外 403/父目录不存在 404/鉴权/不投命令
- test_drain_web_commands_group_actions: 组级暂停/开始/汇报/删除命令执行并作用于整组 hash
- test_drain_web_commands_torrent_actions: 单种子命令作用于该 hash; 种子不在快照 -> 跳过(删除守阵)
- test_api_torrent_write_endpoints_enqueue: 二轮种子写端点(15个) POST 转发 cmd/参数入队 + 无密钥 401
- test_api_t_bulk_group_keys_enqueue: bulk 组键模式(DLG-02): keys 编码组键入队解码回 tuple, 可与 hashes 混合; 纯 hash 载荷不带 keys 键; 无密钥 401
- test_drain_web_commands_torrent_write_actions: 二轮写命令正常执行(参数透传/cmd_id 回执 ok/限速位置同步快照)
- test_drain_web_commands_torrent_write_unknown_hash_skips: 二轮写命令未知 hash 静默跳过不调 API
- test_drain_web_commands_share_limits_and_queue_mapping: share-limits 缺省维度 -2 补齐; queue 动作映射; 未知动作 error 回执
- test_drain_web_commands_torrent_write_param_errors: 写命令参数错误 -> error 回执且不调 API, 后续命令继续
- test_drain_web_commands_bulk_torrents: 批量多 hash 一次调用 + 聚合回执(部分缺失/未知动作/空列表 -> error)
- test_drain_web_commands_bulk_torrents_group_keys: bulk 组键模式(DLG-02): 组键展开级联全组成员删除; 与 hashes 混合去重; 缺失组计组数; 组不存在不调 API
- test_cmd_trackers_write_invalidates_lazy_cache: tracker 三兄弟写后失效 _trackers_info 惰性缓存(重读拉新值)
- test_drain_web_commands_unknown_and_error_continues: 未知命令与执行异常只记日志, 不中断后续消费
- test_drain_web_commands_empty_queue: 队列为空直接返回(queue.Empty 分支)
- test_reannounce_confirm_success_and_timeout: 汇报确认跟踪 next_announce 重置 -> ok 回执; 超时 -> error 回执
- test_reannounce_confirm_group_aggregate: 组汇报按种子逐个确认, 部分失败聚合 error 带计数
- test_confirm_reannounce_result_matrix: 判定矩阵(updating/next_announce 重置/变 working=成功; not working+msg=失败; 其余 None)
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
- test_frontend_statusbar_speed_reads_server_totals: 静态防回潮 —— 前端 totalDl/totalUl 必须读 status.totals, 不得改回对 this.groups 求和
- test_frontend_ctx_submenu_single_entry_and_hover_close: 右键次级菜单守阵 —— 一级只留「更多操作」一个入口(复制族并入, CTX-06)、移出父项后延迟收起(CTX-05)、hover 图标规则必须限定直接子级且压特异性否则整片子面板变灰(CTX-04)
- test_frontend_ctx_menu_multi_select_targets_selection: 多选右键菜单守阵 —— 四个 open*Menu 必须写 menu.multi、双 UI 必须有批量分支且调 ctxAct/ctxDelete、ctxAct/ctxDelete 必须复用 bulkAct/bulkDelete
- test_api_state_status_carries_server_state: status.server(state)恒回传不受 rid 门控(状态栏与行数据同源同轮)
- test_api_category_tag_endpoints: 分类/标签 CRUD 端点(入队与 400 校验)
- test_category_tag_commands_execute: 分类/标签命令执行(QbApi 封装 + 缓存失效)
- test_api_speed_mode_and_override: /api/speed/mode 曲线/停用两形态 + /api/speed/override 落 transfer 端点
- test_api_speed_mode_curve_config_disabled: 曲线存在但 enabled=False -> curve_enabled=False(快照之上叠加配置判定)
- test_api_add_torrent_endpoint: /api/torrents/add multipart(bytes 内存直传/选项透传/空来源 400)
- test_add_torrent_receipt_and_optional_flags: 添加回执两形态(API>=2.14.0 的 JSON 元数据 / 旧文本 "Ok.")判受理 + 两个 optional 选项(停止位 is_stopped / 自动管理 use_auto_torrent_management)恒显式下发(省略会吃 qB 会话/全局默认) + 成功走 INFO(改前 WARNING 会直推桌面弹窗)
- test_frontend_add_torrent_drag_drop_wiring: DND-01 全局拖拽添加种子接线守阵(静态) —— window 级 drag 四事件 add/remove 对称、drop handler 必 preventDefault(否则浏览器直接打开文件)、接管判据只认 Files/text-uri-list(不误拦页面内拖文本)、双 UI 落点遮罩成对 + app.js addDragOver 状态
- test_api_export_endpoint: /api/torrents/{hash}/export 字节流与 disposition(404/503); 非 ASCII 种子名走 filename*(回归: 头 latin-1 编码崩)
- test_content_disposition_encoding: content_disposition 头值纯 ASCII + filename* 百分号编码 + 清洗/回退
- test_api_log_endpoint: /api/log tail 与 level 过滤(未配置空)
- test_api_log_level_filter_follows_config_format: 等级过滤按 config.logging.format 定位等级名(生产格式无方括号, 按字面量 `[WARNING` 捞会恒空 —— 2026-09-25 真机 bug)
- test_api_log_level_filter_keeps_multiline_record: 多行日志(整段 traceback)折行后跟随其记录的等级, 筛 ERROR 不丢栈
- test_api_log_note_when_level_unfilterable: 筛不了(格式无等级字段 / 已存行与格式不符)回全部行 + note, 不静默给空
- test_api_category_tag_list_endpoints: GET /api/categories 与 /api/tags 列表端点(store 缓存数据源)
- test_seed_flat_view_fields_and_gating: 种子平铺视图(SEED_ITEM)字段契约齐全 + ensure_group_state 同门控回传
- test_flat_view_refreshed_by_main_loop_tick: 种子页速度随主循环刷新(回归: 平铺视图曾被"饿死"停在旧快照)
- test_rebuild_views_single_entry_point: rebuild_views 唯一重建入口(四视图 + 版本号 + 脏标记一次完成)
- test_api_torrent_detail_endpoint: /api/torrents/{hash} 全字段详情(to_dict+site+HR); 未知 hash 404
- test_api_torrent_subresources: /api/torrents/{hash}/trackers|files|peers 透传(未知 404/断连 503)
- test_api_readonly_endpoints_short_cache: P1-4 只读端点短缓存(窗口内合并 / 写命令后失效 / 断连仍 503)
- test_api_torrent_peers_endpoint: /api/torrents/{hash}/peers 走 sync_torrent_peers(torrent_hash=..)整包透传(404/503)
- test_api_stats_endpoint: /api/stats 透出 store.server_state(未同步时 null)
- test_state_kind_maps_states: 状态语义分类映射(暂停态优先于下载/做种)
- test_apply_new_config_levels: 配置热重载按 L0/L1/L2/R 级别应用
- test_apply_new_config_l2_preserves_runtime_state: L2 热重载保留运行期内存 state —— 不得重读磁盘旧版回滚 exec_history/skip_check_day/recheck_fails(issue 26-09-21-1347 守阵)
- test_stop_web_server_releases_port_for_restart: 停止后服务线程真正退出, 同端口可再次监听(10048 回归守阵)
- test_apply_web_config_skips_restart_when_bind_unchanged: 监听身份未变 -> 不重启, 仅刷新密钥
- test_apply_web_config_toggle_enabled: web.enabled 热开关(关->开启动 / 开->关停止并清句柄)
- test_start_web_server_reports_failure_when_port_taken: 端口被占用 -> 句柄未就绪 + ERROR 日志(不再静默)
- test_web_loop_exception_handler_downgrades_connection_reset: 网络波动(WinError 10054 对端强迫关闭)降级为一行 INFO, 不再 ERROR + traceback
- test_web_loop_noise_log_throttled_in_window: 断连日志按窗口节流(窗口内只记首条, 出窗口附抑制条数)
- test_web_loop_exception_handler_delegates_real_bug: 反向守阵 —— 非波动异常交回 asyncio 默认处理器, 不吞
- test_is_network_fluctuation_matrix: 波动判定矩阵(异常类 / winerror / errno 三条路都认; 非 OSError 与"目标拒绝"不算)
- test_uvicorn_config_installs_loop_exception_handler: 处理器必须真的装到 uvicorn 事件循环上(经 get_loop_factory 注入)
- test_cmd_trackers_log_sanitized: tracker 编辑/移除日志只写脱敏主地址 —— 任意命名的凭据全文都不进日志(不按参数名黑名单), 主地址仍在
- test_web_route_manifest_frozen: 路由金清单守阵(W0, plan 26-09-22-1857): 61 条 (method, path) 集合逐一钉死, web.py 拆 web/ 包期间任何路由丢失/改名/方法变更即红
- test_create_app_is_thin_assembly: 组装壳守阵(W6): create_app 源 ≤150 行且无内联路由装饰器(防 926 行单函数回潮)
- test_hr_view_fields_three_state: 详情字段透出站点侧三态与依据(接入站点才有值, 未接入全空)
- test_api_hr_status_disabled_returns_empty_state: 未启用 HR 时 /api/hr/status 回 enabled=false + 说明(前端空态, 不报错)
- test_api_hr_status_reports_site_state: 启用后逐站点摊开现状 —— 新鲜度/覆盖证明/索引与回填进度/配额/熔断/
  「现在为什么不放行」(与 --hr-status 同一 `hr.status` 口径)
- test_api_hr_status_names_the_blocking_step: 覆盖证明不成立时要说清卡在哪一步(用户看到种子没放行时最想知道的一句)
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
from types import SimpleNamespace
from unittest import mock

import pytest

from auto_qb import __version__
from auto_qb.config.models import HrCheckConfig
from auto_qb.infra.utils import decode_group_key, encode_group_key
from auto_qb.webui import create_app

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
    web_cfg = SimpleNamespace(enabled=True, host="127.0.0.1", port=8080, token="", skip_local_verify=False)
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
        _web_token="",
        _group_view=view,
        _flat_view=[],
        web_commands=__import__("queue").Queue(),
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
        _web_last_seen=0.0,
        _group_view_dirty=False,
        _group_view_ver=0,
        # 限速/流量只读快照(真实 manager 由 SpeedCurveMixin 整体替换; 此处为未启用态)
        _traffic_view={
            "state": "disabled",
            "periods": [],
            "history": [],
            "limit": {}
        },
        # 命令执行结果回执(真实 manager 由主循环写; 端点测试直接预置)
        _web_results={},
        _web_write_seq=0,  # P1-4 只读端点短缓存的失效键(写命令执行后自增)
        # 命令唤醒(真实 manager 置位 _wake_event 让主循环立即消费); 此处记录调用供断言
        wake=lambda: wake_calls.append(1),
    )
    # 详情端点的 HR 展示字段由 WebviewMixin 静态方法提供; stub 直接引用同一实现
    from auto_qb.core.qbmanager import QbManager

    # 命令投递经表现层门面(WebUIRuntime.post_command): 替身挂一个, 并与上面那个
    # web_commands 共用同一队列 —— 端点测试直投命令的断言才仍然成立
    from auto_qb.webui import WebUIRuntime

    mgr.web = WebUIRuntime(mgr)
    mgr.web.commands = mgr.web_commands
    mgr._hr_view_fields = QbManager._hr_view_fields
    mgr._wake_calls = wake_calls  # 供端点测试断言"投递命令是否唤醒主循环"
    # 性能修复后 API 调用的替身方法: touch_web_client(心跳) / ensure_group_view(懒视图) /
    # ensure_group_state(带 rid 的增量状态)
    mgr.touch_web_client = lambda: setattr(mgr, "_web_last_seen", __import__("time").time())
    mgr.ensure_group_view = lambda: mgr._group_view

    def _ensure_group_state(rid, view=None):
        # 与真实实现同形: 默认回全部; P1-1 带 view 时只回该视图的数组
        from auto_qb.webui.views import VIEW_ARRAYS

        updated = rid != mgr._group_view_ver
        state = {"rid": mgr._group_view_ver, "updated": updated}
        if updated:
            arrays = {
                "groups": mgr._group_view,
                "singles": [],  # 与真实 ensure_group_state 同形: singles 随 groups 同门控回传
                "shows": {
                    "list": [],
                    "unrecognized": []
                },
                "torrents": mgr._flat_view,  # 种子平铺视图同门控(与真实实现同形)
            }
            for k in (VIEW_ARRAYS.get(view) if view else None) or arrays:
                state[k] = arrays[k]
        return state

    mgr.ensure_group_state = _ensure_group_state
    return mgr


@pytest.fixture()
def web_env(tmp_path):
    """带 TestClient 的 WEB 环境(manager 替身 + 密钥已生成)"""
    from fastapi.testclient import TestClient

    from auto_qb.webui import create_app, ensure_web_token

    mgr = _make_web_manager(
        tmp_path, "config:\n  qbittorrent:\n    host: h\n    port: 1\n    username: u\n    password: p\n"
    )
    mgr._web_token = ensure_web_token(mgr)
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
    assert mgr._web_token not in warns[0].getMessage()
    assert mgr._web_token[:8] not in warns[0].getMessage()
    # 正确密钥放行
    assert client.get("/api/status", headers={"Authorization": f"Bearer {mgr._web_token}"}).status_code == 200


def test_config_public_endpoint_no_auth(web_env):
    """公开只读端点 /api/config/public: 免 token 可读, 只暴露本机免鉴权标志(不含任何机密)"""
    mgr, client = web_env
    # 默认关闭: 公开端点仍可无密钥访问, 且暴露值为 false
    resp = client.get("/api/config/public")
    assert resp.status_code == 200
    assert resp.json() == {"web": {"skip_local_verify": False}}
    # 不泄露访问密钥
    assert str(mgr._web_token) not in resp.text


def test_skip_local_verify_loopback_bypass(web_env, caplog):
    """web.skip_local_verify=true 时: 本机(loopback)连接免密钥放行, 直接进入

    默认 false(保守): 本机连接仍强制鉴权; 开启后仅 loopback 放行 —— 对外/远端连接
    (request.client.host 非 127.0.0.1/::1)即使带对密钥以外的任何请求也须密钥(仍强制)。
    提示日志**每进程只记一次**(R10-01)且为 **INFO**: 免鉴权模式下前端按设计不发 Authorization
    头, 每请求都记会把轮询日志刷满; 首次记一条足以说明该实例不校验密钥。级别用 INFO 而非
    WARNING —— 免鉴权是用户显式开启的配置(非异常), WARNING 会经 notify 推送扰民。
    """
    from fastapi.testclient import TestClient

    from auto_qb.webui import create_app

    mgr = web_env[0]
    # 用独立 loopback 客户端 + 开启开关
    mgr.config.web.skip_local_verify = True
    app = create_app(mgr)
    loopback = TestClient(app, client=("127.0.0.1", 50000))
    remote = TestClient(app, client=("192.168.1.50", 50000))

    caplog.set_level(logging.INFO, logger="auto_qb.web")
    caplog.clear()
    # 本机: 无密钥/错密钥均放行(直接进入)
    assert loopback.get("/api/status").status_code == 200
    infos = [r for r in caplog.records if r.name == "auto_qb.web" and r.levelno == logging.INFO]
    assert infos and "skip_local_verify" in infos[-1].getMessage()
    assert not [r for r in caplog.records if r.name == "auto_qb.web" and r.levelno >= logging.WARNING], \
        "免鉴权是显式配置而非异常: 不得记 WARNING 及以上(否则经 notify 推送扰民)"
    # 只记一次: 其余免密钥请求不再刷日志
    caplog.clear()
    assert loopback.get("/api/status").status_code == 200
    assert loopback.get("/api/status", headers={"Authorization": "Bearer wrong"}).status_code == 200
    assert not [r for r in caplog.records if r.name == "auto_qb.web" and "skip_local_verify" in r.getMessage()]
    # 对外/远端连接: 仍强制鉴权(错密钥 401, 对密钥 200)
    assert remote.get("/api/status").status_code == 401
    assert remote.get("/api/status", headers={"Authorization": f"Bearer {mgr._web_token}"}).status_code == 200


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
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
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
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
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
        "/atlas/", "/atlas/style.css", "/prism/", "/shared/app.js", "/shared/config_editor.js",
        "/shared/vendor/vue.global.prod.js"
    ):
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} 应可访问"
        assert resp.headers.get("cache-control") == "no-cache", f"{path} 应带 no-cache"
    api = client.get("/api/status", headers={"Authorization": f"Bearer {mgr._web_token}"})
    assert api.headers.get("cache-control") != "no-cache", "/api 响应不应被静态策略影响"


def test_ui_root_and_legacy_newui_redirect(web_env):
    """根路径与旧 /newui/* 重定向: / -> 307 /atlas/; /newui/* -> 307 /prism/*

    UI 目录化后 StaticFiles 根下无 index.html, 根路径由显式路由兜底进默认 UI(星图);
    /newui 兼容路由保住升级前书签(子路径原样映射到 /prism/*)。
    """
    _, client = web_env
    root = client.get("/", follow_redirects=False)
    assert root.status_code == 307, "根路径应 307 重定向"
    assert root.headers["location"] == "/atlas/"
    for old, new in (
        ("/newui", "/prism/"), ("/newui/", "/prism/"), ("/newui/css/tokens.css", "/prism/css/tokens.css"),
        ("/newui/js/theme.js", "/prism/js/theme.js")
    ):
        resp = client.get(old, follow_redirects=False)
        assert resp.status_code == 307, f"{old} 应 307 重定向"
        assert resp.headers["location"] == new, f"{old} 应映射到 {new}"


STATIC_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "auto_qb", "webui", "static"
)

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
# ⚠ 必须经 `Module.wrap`: 裸 `new vm.Script(src)` 按**经典脚本**解析, 会把顶层 `return`(CommonJS 下合法)
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

    ❗2026-09-23 由「逐文件起一个 `node --check`」改为**单进程批量**: 20 个文件 = 20 次进程启动,
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
    """app.js 及它按域拆分出的片段文件, 按 prism/index.html 的 <script> **加载顺序**返回 [(path, rel)]

    (2026-09-20 app.js 拆分: 片段以 window.AQB_* 全局 mixin 注入 **同一个** Vue 实例, 逻辑上仍是一份
     代码 —— 故"跨文件的不变量"必须按整包看: 只扫 app.js 会把搬走的那半漏掉。实测拆完当场报
     「找不到 _optimisticSettled 调用点」, 而它只是挪到了 commands.js, 功能没丢。)
     顺序取自 HTML 而非文件名排序 —— 片段必须排在 app.js **之前**(app.js 末尾要读 window.AQB_*)。
    """
    prism = os.path.join(STATIC_ROOT, "prism", "index.html")
    with open(prism, encoding="utf-8") as f:
        html = f.read()
    out = []
    for src in re.findall(r'<script src="(/shared/[^"]+\.js)"></script>', html):
        if "/vendor/" in src:
            continue
        rel = src.lstrip("/")
        out.append((os.path.join(STATIC_ROOT, rel), rel))
    return out


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
    ① 文件写了但漏加 <script> 或漏 app.mixin() —— 那一整块功能凭空消失, 控制台不报错
       (Vue 直接把没注册的 mixin 当不存在);
    ② 两个片段里出现同名成员 —— Vue 的 mixin 合并是**后者覆盖前者**, 不报错, 但被覆盖的那个
       实现从此永不执行(表现为"点了没反应"或行为回到旧逻辑)。
    """
    bundle = _app_bundle_files()
    refs = {rel for _p, rel in bundle}
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
            problems.append(f"{rel} 未被 prism/index.html 的 <script> 引用(拆分片段漏挂 -> 整块功能静默消失)")

    app_text = open(os.path.join(STATIC_ROOT, "shared", "app.js"), encoding="utf-8").read()
    # 三种"已接线"形态:
    #   ① mixin    —— window.AQB_* 注入 Vue 实例
    #   ② component —— 注册为组件(如 hub-field 走 app.component)
    #   ③ **行为基座** —— 被另一个全局用 `Object.assign({}, window.X, …)` 拷走复用(如 config_hub.js
    #      的 HUB_FIELD_COMPONENT 拷 config_editor.js 的 CE_FIELD_BASE)。它本身不是组件、不注册,
    #      但成员确实在跑 ⇒ 不该报"定义了没注入"。
    #      ⚠ 只认 `Object.assign({}, window.X` 这一种形态(本项目唯一的复用写法), 不要放宽成"出现即算"。
    #      (2026-09-25: 经典设置页移除后 ce-field 组件与 tpl-ce-field 模板删除, 基座随之改名去组件化。)
    registered = set(re.findall(r"app\.mixin\(window\.(\w+)\)", app_text))
    registered |= set(re.findall(r"app\.component\(\s*\"[^\"]+\"\s*,\s*window\.(\w+)\)", app_text))
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
    ① 同一批种子在辅种页与追剧页显示成**不同颜色**(用户没法解释, 只会觉得"颜色乱");
    ② 乐观 UI: 前端按自己的表算出"点击后的颜色", 下一轮回执却按后端的表算真值 ⇒ 颜色弹回。
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
      ① `_snapshotTruth(state)` 必须在 `reapplyPending()` **之前** —— 快照要的是服务端原始值;
         挪到之后就变成"行上的补丁值 vs 补丁值", 恒真 ⇒ pending 一瞬间就清(实测 28ms),
         而且冒烟里「落回的是真值」那条**照样 PASS**(补丁值还留在行上, 看着就像真值)。
      ② 判定必须走 `_optimisticSettled`(比真值快照)而不是"拿行上的当前值比" —— 同上。

    ❗2026-09-21 P3 后①②**仍然保留, 且必须保留**: 真值现在主要由 `truth` 事件(SSE)推送,
      但 **SSE 断线期间推的事件会丢**; 这时 `_optimisticSettled` 是唯一的安全网 —— 轮询带回的
      `/api/state` 一旦已经含真值就提前收工, 不用干等到 TRUTH_HOLD_MS(8s)超时回滚。
      没有它, SSE 一断就会出现"命令其实成功了, 8 秒后却回滚"的假失败。
    ❗已删除的旧机制(勿复活): `_settleFromTruth`(回执带真值就地撤下)、
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

    ❗这是本项目踩过的坑(memory-bank/testing.md 列偏好守阵那条): 只查"字符串出现了没有",
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
    body = _computed_body(text, "hrOptions")
    if body is not None and "facetRows" not in body:
        problems.append(f"{rel} computed.hrOptions 没走 facetRows 单点 —— 种子页不回 groups ⇒ H&R 两档恒 0/0")
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
    ①**位置**: 上述六类元素一律不许出现 backdrop-filter(不论哪套 UI、哪份 CSS);
    ②**数量**: 星图与棱镜各自的声明数必须相等 —— 防"只在星图侧加回来"这类单边改动
      (shared/console_hub.css 是共用层, 两边同担, 不计入各自计数)。
    扫描前先剥 `/* ... */`, 否则本文件里解释这段历史的注释会被当成真实声明(实测会误报)。
    """
    counts = {"atlas": 0, "prism": 0}
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
                    if rel.startswith("atlas/"):
                        counts["atlas"] += 1
                    elif rel.startswith("prism/"):
                        counts["prism"] += 1
                    for bad in _PERF_BACKDROP_BANNED:
                        if re.search(r"\.%s\b" % re.escape(bad), sel):
                            problems.append(
                                f"{rel} `{sel or '(未识别选择器)'}` 上出现 backdrop-filter —— "
                                f"{bad} 是全屏遮罩或常驻吸顶/吸底条, 加毛玻璃会与弹层遮罩叠成嵌套模糊"
                                f"(每帧回读 + 重复模糊整个视口; 星图 2026-09-24 卡顿根因, 见 PERF-01)"
                            )
                if "}" in line:
                    sel = ""
    if counts["atlas"] != counts["prism"]:
        problems.append(
            f"两套 UI 的 backdrop-filter 声明数不对齐: 星图 {counts['atlas']} 处 / 棱镜 {counts['prism']} 处 —— "
            f"单边加毛玻璃会让星图重新变卡(棱镜 .modal-mask 从不带 backdrop-filter, 见 PERF-01)"
        )


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


    ⚠ 7/8/9/11 四项按 **app.js 整包**(HTML 加载顺序拼接 app.js + 各片段)扫描, 不按单文件 ——
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
    return problems


def test_frontend_static_bundle_health():
    """前端静态资源守阵: 冲突残留/注释孤儿续行/node 语法校验/CSS 漏闭合/transition 吞弹窗/引用缺失/集成员取 hash/状态优先级表

    三个实测故障(2026-09-17)都是"pytest 全绿但界面废掉"的形态:
    ① app.js 注释续行留在已闭合的 `*/` 之后 -> 整包 SyntaxError -> Vue 不 mount -> 只剩背景色;
    ② prism views.css 一条规则漏 `; }` -> 其后约 200 条规则被浏览器丢弃 -> 棱镜大半样式消失;
    ③ 抽屉外层 `<transition>` 未闭合 -> 统计/限速/添加/确认框被 Transition 丢弃(点了没反应且无报错)。
    装了 node 的机器还会在此跑 `node --check` 对所有前端 JS 做真语法校验(无 node 则静默跳过)。
    """
    problems = _scan_frontend_assets()
    assert not problems, "前端静态资源问题: " + "; ".join(problems)


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

    比 `_section_members` 多两件事: ①**所有** computed 块都要取(组件里的 computed 也在内,
    不只看顶层 mixin); ②终止行按**块的缩进**判定 —— 用 `line.strip() in ("},", "}")`
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
    此前没人发现是因为: ① 模板里 `unitParts.num` 是对的(只错在 JS 方法里);
    ② 只有真的去改"主循环间隔 / 轮转大小"这类带单位的值才会触发。

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


def test_frontend_dist_segments_aggregates_per_view():
    """状态分布 distSegments 必须按当前 viewMode 取数, 不能只数 this.groups

    现象与定性(issue 26-09-21-0247):
    后端按视图回传(P1-1, 见 mixins/web_view.VIEW_ARRAYS): view=torrent 只回 torrents,
    view=group 只回 groups+singles。旧版 distSegments 只数 this.groups[].members[].kind,
    于是两种场景 chips 全空:
    ① localStorage 持久化 `autoqb.ui.view=torrents` 后首进种子页(首轮 groups=[]);
    ② 在种子页停得久(轮询只刷 torrents, groups 永远是空/旧)。
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
    for name in ("shared/columns.js", "shared/app.js"):
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
    # ❗只看**代码行**(同旧守阵教训: 注释里提到不算)
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
    for name in ("shared/columns.js", "shared/app.js"):
        text = open(os.path.join(STATIC_ROOT, name), encoding="utf-8").read()
        assert "colManual" not in text, (
            f"{name} 出现 colManual —— manual 标志位在双轨模型(v5)下已删除, "
            "不得复活(w 非空即固化页); 如确需重引, 先重审 plan 26-09-21-1551"
        )


def test_frontend_cols_legacy_keys_have_migration():
    """LEGACY_COLS_KEYS 键链必须伴随迁移函数 —— 升版必挂迁移(定案口径)

    v3->v4 升版没挂迁移, 用户手调的宽/隐/序一次性清零(四轮修复复盘第①轮, "时不时被重置"
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


def test_frontend_page_location_persisted():
    """顶层 page 与设置分区必须持久化 —— 刷新后停在原页(2026-09-25 用户报"设置页刷新会回到种子页")

    `page` 原本是**纯内存态**、初值恒 "groups" ⇒ 在设置页按 F5 必掉回辅种页, 编辑位置全丢;
    设置页里的分区(`hub.view`)同理, 只持久化顶层页会让「设置 → 站点」刷新后落到设置首页。
    两条都只有真浏览器看得见(pytest 全绿、界面行为退化), 故在此静态钉住四件事:
    ① 读侧**白名单**(只认 "settings", 不信任存储内容) + 写侧唯一漏斗;
    ② **启动必须补一次 cfgLoad** —— 设置页的配置树是按需加载的, 只改初值不改启动路径,
       首屏会停在「配置加载失败 + 重试」(`cfg.schema` 永远为 null);
    ③ 恢复的分区 key 必须**对 schema 校验** —— 分区会随版本改名/删除, 否则停在空白分区;
    ④ 恢复走 `hubGo`(懒加载与默认选中项都在那条路径里, 自己重写必漏一半)。
    """
    app = open(os.path.join(STATIC_ROOT, "shared", "app.js"), encoding="utf-8").read()
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
      ① 四个 open*Menu 必须各自写入 `multi:` —— 漏一处, 那条路径的多选右键就仍是单目标;
      ② 两套 UI 的批量分支必须**成对存在**且逐项一致(双 UI 是两条独立模板, 只改一边 = 另一边
         用户看不到批量菜单), 且只能调 ctxAct/ctxDelete;
      ③ ctxAct/ctxDelete 必须**复用** bulkAct/bulkDelete —— 自己再拆一遍目标集合就会与批量浮条
         的口径漂移(虚拟行/组展开/失效目标跳过这三条语义都在 _bulkTargets 里)。
    """
    # ① 四个菜单入口都必须写 multi
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

    # ② 两套 UI 的批量分支成对且逐项一致
    branches = {}
    for ui in ("atlas", "prism"):
        text = open(os.path.join(STATIC_ROOT, ui, "index.html"), encoding="utf-8").read()
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

    # ③ ctxAct/ctxDelete 复用批量浮条链路, 且先收起菜单(菜单根节点 @click.stop, 全局点空白关不掉)
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


def test_frontend_add_torrent_drag_drop_wiring():
    """DND-01 全局拖拽添加种子接线守阵(静态防回潮)

    拖拽进料口的关键点全在 JS/HTML 静态结构里, pytest 运行时看不见:
      ① window 级 drag 事件四件套(dragenter/dragover/dragleave/drop) add/remove 严格对称
         —— 漏 remove = 卸载后幽灵监听重复 ingest;
      ② drop handler 必须 preventDefault —— 删掉它浏览器会直接打开 .torrent / 跳转链接,
         表现为"拖进去弹出的是文件内容页";
      ③ 接管判据只认 "Files"/"text/uri-list" —— 若放宽到 text/plain, 页面内拖选中文本、
         拖词进输入框的原生行为会被误拦;
      ④ 双 UI 的落点遮罩成对存在(v-if="addDragOver"), app.js 有 addDragOver 状态 ——
         只改一套皮肤 = 另一套用户拖了没反应。
    """
    import re

    add_js = open(os.path.join(STATIC_ROOT, "shared", "add_torrent.js"), encoding="utf-8").read()
    # ① 四件套 add/remove 对称
    added, removed = set(), set()
    for hook, bucket in (("mounted", added), ("unmounted", removed)):
        m = re.search(rf"\n  {hook}\(\) \{{(.*?)\n  \}},", add_js, re.S)
        assert m, f"add_torrent.js 找不到 {hook} 钩子(DND-01 监听挂载点, 改名或挪走了? 同步本守阵)"
        for ev in re.findall(r'window\.(?:add|remove)EventListener\("([a-z]+)"', m.group(1)):
            bucket.add(ev)
    expect = {"dragenter", "dragover", "dragleave", "drop"}
    assert added == expect, f"mounted 缺 drag 事件: {expect - added}(少一个就有一条路径不接管)"
    assert removed == added, f"unmounted 与 mounted 不对称: add={sorted(added)} / remove={sorted(removed)}"

    # ② drop handler 必须拦默认行为 + depth 归零灭遮罩
    m = re.search(r"\n    _addDragDrop\(e\) \{(.*?)\n    \},", add_js, re.S)
    assert m, "add_torrent.js 找不到 _addDragDrop(drop 分流入口, 改名或挪走了? 同步本守阵)"
    assert "preventDefault()" in m.group(1
                                        ), ("_addDragDrop 少了 preventDefault —— 浏览器会直接打开 .torrent/链接而不是交给添加对话框(DND-01)")

    # ③ 接管判据只认文件与链接, 不得放宽到 text/plain
    m = re.search(r"\n    _addDragTakes\(e\) \{(.*?)\n    \},", add_js, re.S)
    assert m, "add_torrent.js 找不到 _addDragTakes(接管判据, 改名或挪走了? 同步本守阵)"
    takes = m.group(1)
    assert 'types.includes("Files")' in takes and 'types.includes("text/uri-list")' in takes, (
        "_addDragTakes 必须显式认 Files 与 text/uri-list(接管面收窄到拖文件/拖链接)"
    )
    assert "text/plain" not in takes, ("_addDragTakes 不得认 text/plain —— 会误拦页面内拖选中文本/拖词进输入框的原生行为(DND-01)")

    # ④ app.js 状态 + 双 UI 遮罩成对
    app_js = open(os.path.join(STATIC_ROOT, "shared", "app.js"), encoding="utf-8").read()
    assert "addDragOver: false" in app_js, "app.js 缺 addDragOver 状态(遮罩显隐没有数据源)"
    for ui in ("atlas", "prism"):
        html = open(os.path.join(STATIC_ROOT, ui, "index.html"), encoding="utf-8").read()
        assert 'class="add-drop-mask"' in html and 'v-if="addDragOver"' in html, (
            f"{ui}/index.html 缺拖拽落点遮罩(.add-drop-mask + v-if=\"addDragOver\")—— "
            f"该皮肤用户拖文件进页面没有落点反馈(双 UI 必须成对改)"
        )


def test_frontend_ctx_submenu_single_entry_and_hover_close():
    """右键菜单的次级菜单: 一级只留「更多操作」一个入口, 且移出后必须收起 (CTX-04 / CTX-05 / CTX-06)

    三条用户报的故障形态, 全部是"pytest 全绿 + node --check 全绿 + 界面废掉"那一类:
      ① **二级菜单图标 hover 变灰**: `.ctx-item:hover .ico` 是后代选择器, 而 `.ctx-sub` 是父项的
         DOM 后代 —— hover 父项会把整个子面板的图标一起刷成 `--fg-muted`, 语义色全被抹平。
         修法两处缺一不可: `>` 限定直接子级 + `:where(:hover)` 把特异性压到 0(让位给语义色规则)。
      ② **移出不消失**: 只有 mouseenter 展开、没有任何 mouseleave, 鼠标移到别的菜单项上子面板
         会一直挂在屏幕上。修法挂**父项**的 mouseleave 延迟收起(子面板上再挂一条会在
         "从面板回到父项"时误收起), 延迟只为跨过父项与面板之间那 4px 缝隙。
      ③ **复制族并成第二个子面板**: 一级出现两个"更多"入口, 用户得先选"该进哪个"。
         CTX-06 把 复制名称/哈希/magnet 并入「更多操作」末尾。
    """
    # ① CSS 的 hover 规则: 直接子级 + 特异性压制(改回后代选择器 = 整片子面板变灰)
    css = {
        "atlas": os.path.join(STATIC_ROOT, "atlas", "style.css"),
        "prism": os.path.join(STATIC_ROOT, "prism", "css", "components.css"),
    }
    for ui, path in css.items():
        text = open(path, encoding="utf-8").read()
        assert ".ctx-item:where(:hover) > .ico" in text, (
            f"{ui} 的右键菜单 hover 规则必须是 `.ctx-item:where(:hover) > .ico` —— "
            f"用后代选择器会把整个子面板的图标一起拉灰, 用不带 :where 的写法会压过语义色规则(CTX-04)"
        )
        assert not re.search(r"\.ctx-item:hover\s+\.ico\b",
                             text), (f"{ui} 仍存在后代写法的 `.ctx-item:hover .ico` —— hover 父项会连子面板图标一起变灰(CTX-04)")

    # ② 两套 UI 的次级菜单: 一级只有一个入口, 复制三项在面板内
    for ui in ("atlas", "prism"):
        text = open(os.path.join(STATIC_ROOT, ui, "index.html"), encoding="utf-8").read()
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

    # ③ 收起的两个方法必须存在且挂在延迟上(同步收起 = 鼠标进不去子面板)
    menu = open(os.path.join(STATIC_ROOT, "shared", "menu.js"), encoding="utf-8").read()
    for name, needle in (("keepSub()", "clearTimeout"), ("scheduleSubClose()", "setTimeout")):
        m = re.search(rf"\n    {re.escape(name)} \{{(.*?)\n    \}},", menu, re.S)
        assert m, f"shared/menu.js 找不到 {name}(改名或挪走了? 同步本守阵)"
        assert needle in m.group(1), f"{name} 必须走 {needle}(延迟收起/撤销挂起), 实现漂移了"
    delay = re.search(r"const SUB_CLOSE_DELAY_MS = (\d+);", menu)
    assert delay and int(delay.group(1)) > 0, "SUB_CLOSE_DELAY_MS 必须为正整数(0 = 同步收起, 进不去子面板)"
    app = open(os.path.join(STATIC_ROOT, "shared", "app.js"), encoding="utf-8").read()
    assert "_subCloseTimer: 0," in app, "app.js data 必须声明 _subCloseTimer(未声明的属性不进响应式, 且易漂移)"
    assert re.search(r'"menu\.visible"\(v\) \{\n(?:.*\n){0,4}?.*this\.keepSub\(\);',
                     app), ("menu.visible 关闭时必须 keepSub() 撤掉挂起的收起 —— 否则一级关掉后定时器还会再触发一次")


def test_api_group_commands_enqueue(web_env):
    """pause/resume/reannounce 命令入队: key 解码回原 tuple, 主循环侧执行"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
    enc = encode_group_key(KEY)
    for action in ("pause", "resume", "reannounce"):
        resp = client.post(f"/api/groups/{enc}/{action}", headers=auth)
        assert resp.status_code == 200, resp.text
    cmds = [mgr.web_commands.get_nowait() for _ in range(3)]
    assert [c for c, _ in cmds] == ["pause_group", "resume_group", "reannounce_group"]
    assert all(p["key"] == KEY for _, p in cmds), "key 应解码回原 tuple"


def test_api_group_malformed_key_returns_400(web_env):
    """畸形分组 key -> 400(客户端错误), 不是 500

    `decode_group_key` 对 base64 非 ASCII / 非法 JSON / 结构不符分别抛 ValueError 系与
    TypeError/IndexError; 不拦截就是 500 + 栈回溯 —— 手输或被篡改的 URL 都能打出服务端错误页。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
    bad_keys = [
        "!!!not-base64!!!",  # 非法 base64 → binascii.Error
        base64.urlsafe_b64encode(b"not json{").decode(),  # 合法 base64, 解出非法 JSON
        base64.urlsafe_b64encode(b"123").decode(),  # 合法 JSON 但结构不符(不可下标)→ TypeError
    ]
    for bad in bad_keys:
        resp = client.post(f"/api/groups/{bad}/pause", headers=auth)
        assert resp.status_code == 400, f"{bad!r} 应回 400, 实际 {resp.status_code}: {resp.text}"
        assert mgr.web_commands.empty(), "畸形 key 不该投递命令"


def test_api_delete_with_files_flag(web_env):
    """delete 命令透传 delete_files 标志(默认 False 保留文件)"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
    enc = encode_group_key(KEY)
    client.post(f"/api/groups/{enc}/delete", headers=auth, json={"delete_files": True})
    cmd, payload = mgr.web_commands.get_nowait()
    assert cmd == "delete_group" and payload["delete_files"] is True


def test_api_cmd_result_endpoint(web_env):
    """命令端点返回 cmd_id; /api/cmd/{id} 查询回执(pending -> 结果)"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
    resp = client.post("/api/torrents/HA/reannounce", headers=auth)
    assert resp.status_code == 200
    cmd_id = resp.json()["cmd_id"]
    assert cmd_id, "投递响应应携带 cmd_id"
    assert client.get(f"/api/cmd/{cmd_id}", headers=auth).json() == {"status": "pending"}
    mgr._web_results[cmd_id] = {"status": "ok", "error": "", "ts": 123.0}
    assert client.get(f"/api/cmd/{cmd_id}", headers=auth).json() == {"status": "ok", "error": "", "ts": 123.0}
    # 其余命令端点同样携带 cmd_id(delete 返回体保留 delete_files 标志)
    enc = encode_group_key(KEY)
    assert client.post(f"/api/groups/{enc}/pause", headers=auth).json()["cmd_id"]
    delete_resp = client.post(f"/api/groups/{enc}/delete", headers=auth, json={"delete_files": True}).json()
    assert delete_resp["cmd_id"] and delete_resp["delete_files"] is True


def test_api_traffic_history_endpoint(web_env):
    """/api/traffic/history: 透出限速曲线任务发布的按日 history; 未启用时返回空数组"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
    assert client.get("/api/traffic/history", headers=auth).json() == {"state": "disabled", "history": []}
    mgr._traffic_view = {
        "state": "ok",
        "history": [{
            "date": "2026-09-14",
            "up": 1024,
            "down": 2048
        }],
    }
    data = client.get("/api/traffic/history", headers=auth).json()
    assert data["state"] == "ok" and data["history"][0]["date"] == "2026-09-14"


def test_config_schema_endpoint(web_env):
    """图形化配置元数据端点: 分组/站点字段/规则字段/插件表/热重载级别齐全"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
    data = client.get("/api/config/schema", headers=auth).json()
    assert [g["key"] for g in data["groups"]] == [
        "basic", "logging", "web", "notify", "maintenance", "hr_check", "speed", "trackers", "rules"
    ]
    assert {p["name"] for p in data["plugins"]["condition"]} >= {"size", "tags", "state", "freespace"}
    assert {p["name"] for p in data["plugins"]["action"]} >= {"add_tags", "checking", "reannounce"}
    # 热重载级别与 impact 同源(R 级字段前端需标"需重启")
    assert data["levels"]["sections"]["data_dir"] == "R"
    assert data["levels"]["sections"]["main_tick"] == "L0"
    assert data["levels"]["tracker_fields"]["domains"] == "L2"


def test_config_tree_roundtrip(web_env):
    """配置树读取与保存: 树为 YAML 同构(标量字符串), 写回文件 + 热重载命令入队"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
    data = client.get("/api/config", headers=auth).json()
    tree = data["tree"]
    assert tree["config"]["qbittorrent"]["host"] == "h", "树应为 YAML 同构的字符串标量"

    tree["config"]["main_tick"] = "5s"
    resp = client.put("/api/config", headers=auth, json={"tree": tree})
    assert resp.status_code == 200, resp.text
    assert resp.json()["applied"] is True
    assert "main_tick" in [c["path"] for c in resp.json()["changes"]]
    with open(mgr.config_path, encoding="utf-8") as f:
        assert "5s" in f.read(), "新配置应写回 config 文件"
    cmd, payload = mgr.web_commands.get_nowait()
    assert cmd == "reload_config" and payload["config"].main_tick == 5.0


def test_config_tree_invalid_rejected(web_env):
    """非法配置树 -> 400, config 文件不被覆盖"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
    tree = client.get("/api/config", headers=auth).json()["tree"]
    tree["config"]["main_tick"] = "abc"
    before = open(mgr.config_path, encoding="utf-8").read()
    resp = client.put("/api/config", headers=auth, json={"tree": tree})
    assert resp.status_code == 400
    assert "main_tick" in resp.json()["detail"]
    assert open(mgr.config_path, encoding="utf-8").read() == before
    assert mgr.web_commands.empty(), "校验失败不应投递热重载"


def test_config_tree_requires_config_root(web_env):
    """缺少 config 根段 -> 400(防止误删整段被当作"全默认"静默接受)"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
    resp = client.put("/api/config", headers=auth, json={"tree": {"qbittorrent": {}}})
    assert resp.status_code == 400
    assert "config" in resp.json()["detail"]


def test_config_tree_restart_field_fallback(web_env):
    """R 级字段提交后回退为磁盘旧值(进程身份不可热切换), 并回报 restart_required"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
    with open(mgr.config_path, "w", encoding="utf-8") as f:
        f.write("config:\n  data_dir: old-dir\n  qbittorrent:\n    host: h\n")

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
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
    with open(mgr.config_path, "w", encoding="utf-8") as f:
        f.write("config:\n  # 保留我\n  main_tick: 2s\n  qbittorrent:\n    host: h\n")

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
    config.min_level(默认 WARNING) ⇒ 密钥被推到系统通知; 落日志文件后已登录者可经
    /api/log 读回。拿到密钥即等于拿到改配置/删种子的能力。改为只提示文件路径。
    """
    from auto_qb.webui import ensure_web_token

    mgr = _make_web_manager(
        tmp_path, "config:\n  qbittorrent:\n    host: h\n    port: 1\n    username: u\n    password: p\n"
    )
    with caplog.at_level(logging.DEBUG, logger="auto_qb.web"):
        token = ensure_web_token(mgr)
    assert token, "前置: 应生成随机密钥"
    assert any(r.name == "auto_qb.web" for r in caplog.records), "前置: 应有生成提示日志"
    for r in caplog.records:
        assert token not in r.getMessage(), f"密钥不得出现在日志: {r.getMessage()}"
        assert token[:8] not in r.getMessage(), f"密钥前缀也不得出现: {r.getMessage()}"


def test_config_tree_masks_secrets(web_env):
    """/api/config 掩码敏感字段, 且"读取后原样保存"不会把密码写成占位串

    掩码只影响展示: PUT 侧用磁盘旧值还原哨兵, 因此前端不改密码地保存一遍仍是真密码 ——
    只掩码不还原的话, 一次保存就会毁掉生产配置。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
    data = client.get("/api/config", headers=auth).json()
    assert data["masked"] is True
    assert data["tree"]["config"]["qbittorrent"]["password"] == data["mask_sentinel"]
    assert data["tree"]["config"]["qbittorrent"]["host"] == "h", "非敏感字段不掩码"

    resp = client.put("/api/config", headers=auth, json={"tree": data["tree"]})
    assert resp.status_code == 200, resp.text
    text = open(mgr.config_path, encoding="utf-8").read()
    assert "password: p" in text, f"原样保存不得把密码写成占位串: {text}"
    assert data["mask_sentinel"] not in text


def test_group_key_codec_roundtrip():
    """分组 key 编解码回原值(base64url(JSON))"""
    key = ("R:/下載/目錄", ("a.mkv", "b.mkv"))
    assert decode_group_key(encode_group_key(key)) == key


def test_build_group_view(tmp_path):
    """分组视图快照组装: 组级聚合求和 + 成员明细 + 编码 key(回归真机 utils.encode_group_key 缺失)"""
    from helpers import FakeClient, FakeTorrent, make_manager

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


def test_build_group_view_member_num_seeds_fields(tmp_path):
    """组视图成员透出 num_seeds/num_leechs/num_complete/num_incomplete(TorrentRecord 快照直取)

    前端成员列/种子页展示连接数与可用性的数据源: _member_view 是组视图 members 与
    singles 未归组种子的共同投影, 字段在成员层透出后两处同形。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

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
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

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

    mgr._group_view_dirty = False
    mgr.refresh_error_reasons()

    assert err.tracker_error_msg == "torrent not registered", "取第一条非空错误 msg(虚拟条目跳过)"
    assert mgr._group_view_dirty is True, "原因变化须显式置脏(非快照字段, store.view_changed 覆盖不到)"
    assert mgr._member_view(err)["error_reason"] == "torrent not registered"
    assert mgr._seed_view(err)["error_reason"] == "torrent not registered"
    assert no_msg.tracker_error_msg == "" and mgr._member_view(no_msg)["error_reason"] == "错误"
    assert mgr._member_view(FakeTorrent(hash="HC", state="stalledUP"))["error_reason"] == "", "非错误状态不带原因"


def test_error_reason_missing_files_without_api(tmp_path):
    """missingFiles 的原因由状态本身给出("文件丢失"), 不需要任何 tracker 请求"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

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
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

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
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = FakeClient()
    t = FakeTorrent(hash="HA", name="A", state="error", tracker_error_msg="unregistered", tracker_error_ts=time.time())
    seed_store(mgr, [t])

    mgr._group_view_dirty = False
    mgr.refresh_error_reasons()
    assert t.tracker_error_msg == "unregistered", "错误态且未过期: 原样保留"
    assert mgr._group_view_dirty is False, "无变化不置脏"

    t.state = "stalledUP"
    mgr.refresh_error_reasons()
    assert t.tracker_error_msg == "" and t.tracker_error_ts == 0.0
    assert mgr._group_view_dirty is True, "清空也是视图变化"


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


def test_hr_view_fields_three_state(tmp_path):
    """详情字段透出站点侧三态与依据(WebUI 可观测性): 接入站点才有值, 未接入四项全空"""
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

    # 未接入 hr_check: 四项全空(前端据此不显示三态行, 与既有四个字段的空值口径一致)
    fields = QbManager._hr_view_fields(rec)
    assert fields["hr_state"] == "" and fields["hr_state_text"] == "" and fields["hr_reason"] == ""
    assert fields["hr_satisfied_src"] == ""

    conf.hr_check = SiteHrCheckConfig(mode="partial", hr_page_url="https://hhanclub.net/myhr.php")
    link = mock.Mock()
    link.judge.return_value = HrJudgement(
        identity=HrIdentity.HR, is_hr=True, reason="清单命中(档位 C)", site_satisfied=None, site="HHan"
    )
    rec.hr_link = link
    fields = QbManager._hr_view_fields(rec)
    assert fields["hr_triggered"] is True, "站点侧清单命中 => 受管束(本地 downloaded=0 不参与)"
    assert fields["hr_state"] == "hr" and fields["hr_state_text"] == "受管束"
    assert fields["hr_reason"] == "清单命中(档位 C)"
    assert fields["hr_satisfied_src"] == "local", "站点没给达标结论 => 标注本地兜底"

    link.judge.return_value = HrJudgement(
        identity=HrIdentity.HR,
        is_hr=True,
        reason="清单命中(档位 B)",
        site_satisfied=True,
        facts=HrSiteFacts(lane="B", remain_seconds=0, ratio=1.5)
    )
    fields = QbManager._hr_view_fields(rec)
    assert fields["hr_satisfied"] is True and fields["hr_satisfied_src"] == "site"
    # 站点侧值(两套值对账): 已给的照传, 没给的空串 —— 未知与 0 必须可分(0 = 已达标)
    assert fields["hr_site_lane"] == "B" and fields["hr_site_remain"] == 0
    assert fields["hr_site_ratio"] == 1.5 and fields["hr_site_need"] == "" and fields["hr_site_dl"] == ""

    link.judge.return_value = HrJudgement(identity=HrIdentity.VERIFIED_NON_HR, is_hr=False, reason="完整刷新未列出")
    fields = QbManager._hr_view_fields(rec)
    assert fields["hr_triggered"] is False and fields["hr_state"] == "verified_non_hr"
    assert fields["hr_state_text"] == "已核实·安全放行" and fields["hr_satisfied_src"] == ""


def _hr_status_env(mgr, tmp_path, *, complete=True):
    """给 web 替身挂上一个**真** HR 服务(跑过一轮), 返回它 —— 站点文件与视图都是真的

    替身 manager 的 config 是 SimpleNamespace(没有 hr_check 段), 所以这里显式补上, 并挂一个
    `hr` 门面替身(真门面需要端点/线程, 与本端点的只读口径无关)。
    """
    from types import SimpleNamespace
    import time

    from auto_qb.hr.runtime import HrRuntimeStatus, HrRefreshService
    from hr_helpers import Clock, FakeFetcher, global_conf, myhr_page, row, site_conf, torrent_blob

    # ❗假时钟要落在**真实当前时间**附近: 端点用真 `time.time()` 取 now, 若测试时钟是
    # hr_helpers 默认的 2023 基准, 数据必然被判「已过有效期」—— 测的就不是想测的东西了
    clock = Clock(start=time.time())
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
    r = client.get("/api/hr/status", headers={"Authorization": f"Bearer {mgr._web_token}"})
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
    r = client.get("/api/hr/status", headers={"Authorization": f"Bearer {mgr._web_token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is True and body["fetch_enabled"] is True and body["worker_running"] is True
    assert [s["site"] for s in body["sites"]] == ["HHan"]

    site = body["sites"][0]
    assert site["mode"] == "partial" and site["complete"] is True
    assert site["index_total"] == 1 and site["index_active"] == 1
    assert site["pending_infohash"] == 0 and site["backfill_ratio"] == 1.0
    assert site["managed"] == 1 and site["keys"] == 2, "一个种子在 by_infohash 里占 v1/v2 两个键"
    assert site["scopes_done"] == ["A", "B", "C"]
    assert site["blocking"] == "", "完整刷新 + 有可查键 => 不挡路"
    assert "上次取数" in site["fresh_text"] and "数据有效期至" in site["fresh_text"]
    assert site["next_refresh_at"] > site["fetched_at"], "下次刷新 = 上次取数 + 周期"
    assert "本小时" in site["quota"]["text"] and site["quota"]["hour_max"] > 0
    assert site["fuse"]["active"] is False and "正常" in site["fuse"]["text"]
    assert site["channel_text"] in ("正常", "未启用") and site["file_path"].endswith("HHan.json")


def test_api_hr_status_names_the_blocking_step(web_env, tmp_path):
    """覆盖证明不成立时, 状态里要直接说出「现在为什么不放行」(用户看到种子没放行时最想知道的一句)"""
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path, complete=False)
    body = client.get("/api/hr/status", headers={"Authorization": f"Bearer {mgr._web_token}"}).json()
    site = body["sites"][0]
    assert site["complete"] is False
    assert "覆盖证明不成立" in site["blocking"], f"要说清卡在哪一步: {site['blocking']!r}"


def test_frontend_hr_status_fields_match_backend():
    """前端 HR 状态块引用的字段必须在后端快照里存在 —— 打错一个字段名就是**整段静默空白**

    两套 UI 各扫一个入口(2026-09-25 起 HR 站点状态并入 Console Hub「HR 在线核实」分区页尾,
    经典设置页与其独立章节/卡片已移除): 这类错误后端全绿、pytest 也全绿, 只有真打开页面才
    看得出来(与 `_scan_page_class_wiring` 的挂件类名同一类故障), 故机检。
    """
    from pathlib import Path

    from auto_qb.hr.status import SiteStatus

    site_keys = set(SiteStatus(site="probe").to_dict().keys())
    hrs_keys = {
        "loaded", "loading", "error", "enabled", "note", "sites", "channel", "fetchEnabled", "workerRunning",
        "pollInterval"
    }
    static = Path(__file__).resolve().parents[1] / "src" / "auto_qb" / "webui" / "static"
    # 锚点必须指向合并块自身: v-if 只在「站点状态」块这一处出现, 重复出现说明块被复制
    anchor = "hub.view === 'hr_check'"
    for name in ("atlas/index.html", "prism/index.html"):
        html = (static / name).read_text(encoding="utf-8")
        idx = html.find(anchor)
        assert idx > 0, f"{name} 缺少锚点 {anchor} —— 合并进「HR 在线核实」的状态块丢失"
        assert html.find(anchor, idx + 1) < 0, f"{name} 锚点出现多次 —— 状态块被复制了?"
        block = html[idx:idx + 4000]
        cut = block.find("</template>")
        assert cut > 0, f"{name}: 状态块没有闭合标签 —— 模板结构被改坏"
        block = block[:cut]
        used_site = set(re.findall(r"\bs\.([a-z_]+)\b(?!\()", block))
        assert used_site, f"{name}: 没扫到任何字段 —— 锚点失效, 这个守阵现在是恒真的"
        missing = sorted(used_site - site_keys)
        assert not missing, f"{name}: 模板引用了后端快照里没有的字段 {missing}(会整段空白)"
        used_hrs = set(re.findall(r"\bhrs\.([A-Za-z_]+)\b(?!\()", block))
        missing_hrs = sorted(used_hrs - hrs_keys)
        assert not missing_hrs, f"{name}: 模板引用了 hrs 状态里没有的字段 {missing_hrs}"


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
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

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
    无锁时后者的"逐条赋值 + 版本号自增"会被前者插到中间 ⇒ ①`_group_view_ver += 1` 是
    读-改-写, 丢失更新; ②Web 线程可能拿到"groups 来自本轮、flat 来自上一轮"的错位组合,
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
            mgr.rebuild_views()  # 主循环 _tick 走的重建路径(持锁)
        except Exception as e:  # 线程内异常不能静默吞掉
            errors.append(e)

    t = _threading.Thread(target=_main_loop_path)
    t.start()
    assert inside.wait(5), "前置: 重建线程应已进入 builder"

    # 关键: 置脏为 False, 让读取路径**不需要重建** —— 于是它是否返回只取决于"有没有锁",
    # 不再受线程调度影响(若改成依赖交错时序, 用例会变 flaky)。
    mgr._group_view_dirty = False

    read_done = _threading.Event()

    def _web_path():
        try:
            mgr.ensure_group_view()  # Web 线程路径
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


def test_build_search_index_files():
    """_build_search_index: 主循环构建索引(hash -> name+files), 单条文件拉取失败跳过该种子"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

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

        mgr._build_search_index()
        assert mgr._search_index_dirty is False
        idx = mgr._search_index
        assert idx["HA"]["name"] == "Alpha"
        assert "movie.mkv" in idx["HA"]["files"]
        assert idx["HB"]["files"] == [], "文件拉取失败的种子 files 应为空"
        assert set(idx.keys()) == {"HA", "HB"}


def test_build_search_index_incremental_and_evict():
    """_build_search_index 增量维护: 已建条目只刷新名称(不重拉文件), 新种子补拉, 已消失种子淘汰"""
    from helpers import FakeClient, FakeTorrent, _fake_file, make_manager, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.files_map["HA"] = [_fake_file("movie.mkv", 0)]
        ha = FakeTorrent(hash="HA", name="Alpha")
        seed_store(mgr, [ha])
        mgr._build_search_index()
        first_calls = client.files_calls
        assert first_calls == 1

        # 种子集未变: 不重复拉文件列表, 仅刷新名称, 且整体替换引用(原子交换契约)
        idx_before = mgr._search_index
        ha.name = "Alpha.Renamed"
        mgr._build_search_index()
        assert client.files_calls == first_calls, "已建条目不重复拉取文件列表"
        assert mgr._search_index["HA"]["name"] == "Alpha.Renamed", "名称应刷新"
        assert mgr._search_index is not idx_before, "索引应整体替换引用(Web 线程并发只读安全), 不就地增删"

        # HA 消失 + HB 新增: 只补拉新种子, 已删种子淘汰
        client.files_map["HB"] = [_fake_file("anime.mkv", 0)]
        seed_store(mgr, [FakeTorrent(hash="HB", name="Beta")])
        mgr._search_index_dirty = True
        mgr._build_search_index()
        assert set(mgr._search_index.keys()) == {"HB"}, "已消失种子应被淘汰"
        assert client.files_calls == first_calls + 1, "只补拉新增种子的文件列表"
        assert mgr._search_index_dirty is False


def test_build_search_index_budget_resumes(monkeypatch):
    """_build_search_index 限流: 单次最多拉预算条, 未拉完保持脏, 下次调用续建至完成"""
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

        mgr._build_search_index()
        assert mgr._search_index_dirty is True, "预算用尽应保持脏(待续建)"
        assert set(mgr._search_index.keys()) == {"HA"}, "单次只拉预算条数的文件列表"

        mgr._build_search_index()
        assert mgr._search_index_dirty is False, "续建后应不再脏"
        assert set(mgr._search_index.keys()) == {"HA", "HB"}


def test_build_search_index_aborts_when_disconnected():
    """_build_search_index: qB 断开(client None)时中止并保持脏——不把空文件列表当成"已建完"""
    from helpers import FakeClient, FakeTorrent, _fake_file, make_manager, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.files_map["HA"] = [_fake_file("movie.mkv", 0)]
        seed_store(mgr, [FakeTorrent(hash="HA", name="Alpha")])

        mgr.client = None  # 模拟 qB 断连(setter 同步解绑 store/api)
        mgr._build_search_index()
        assert mgr._search_index_dirty is True, "断连时应保持脏, 待连接恢复后重建"
        assert mgr._search_index is None, "断连时不得写入空文件索引"

        mgr.client = client  # 连接恢复
        mgr._build_search_index()
        assert mgr._search_index_dirty is False
        assert mgr._search_index["HA"]["files"] == ["movie.mkv"]


def test_search_torrents_name_match():
    """search_torrents: 种子名匹配(即时, 无需文件索引), 大小写不敏感"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

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
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, _fake_file

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
        mgr._build_search_index()

        r = mgr.search_torrents("cat and")
        # HA 名字命中(回归主案例), HB 的下划线文件名归一后也含 "cat and"(file 路径顺带覆盖)
        assert [x["hash"] for x in r["results"]] == ["HA", "HB"], f"空格查询词应命中点号分隔名: {r}"
        assert [x["by"] for x in r["results"]] == ["name", "file"]
        assert [x["hash"] for x in mgr.search_torrents("web dl")["results"]] == ["HA"], "连字符分隔应命中"
        # 对称: 点号查询词同样归一, 仍命中; 词序不同/纯分隔符不命中(子串语义本身未放宽)
        assert [x["hash"] for x in mgr.search_torrents("cat.and")["results"]] == ["HA", "HB"]
        assert mgr.search_torrents("dragon cat")["results"] == []
        assert mgr.search_torrents("...")["results"] == []

        # 文件命中: 下划线分隔的文件名按同一口径(HA 名与文件均不含该子串, 排除 seen 去重干扰)
        r = mgr.search_torrents("and dragon e02")
        assert [x["hash"] for x in r["results"]] == ["HB"], f"下划线文件名应命中: {r}"
        assert r["results"][0]["by"] == "file"


def test_search_torrents_file_match():
    """search_torrents: 文件列表匹配(依赖已构建的索引), 命中文件名"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        from helpers import _fake_file
        client.files_map["HA"] = [_fake_file("movie.mkv", 0)]
        client.files_map["HB"] = [_fake_file("soundtrack.flac", 0)]
        t1 = FakeTorrent(hash="HA", name="Alpha", state="stalledUP")
        t2 = FakeTorrent(hash="HB", name="Beta", state="stalledUP")
        seed_store(mgr, [t1, t2])
        mgr._build_search_index()  # 先构建索引

        # 文件命中: soundtrack 只在 HB 的文件里, 不在任何种子名中
        r = mgr.search_torrents("soundtrack")
        hashes = [x["hash"] for x in r["results"]]
        assert hashes == ["HB"], f"文件匹配应命中 HB: {r}"
        assert r["results"][0]["by"] == "file"
        assert r["building"] is False, "索引已就绪不应 building"


def test_search_torrents_building_triggers():
    """search_torrents: 索引脏(种子集变化后)时返回 building=true 并投递构建命令"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, _fake_file

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.files_map["HA"] = [_fake_file("movie.mkv", 0)]
        t1 = FakeTorrent(hash="HA", name="Alpha", state="stalledUP")
        seed_store(mgr, [t1])

        mgr._search_index_dirty = True  # 模拟种子集变化后未构建
        r = mgr.search_torrents("movie")
        assert r["building"] is True, "索引脏时 building 应为 True"
        # 名称未命中, 文件索引未就绪 -> 无结果, 但投递了构建命令
        assert r["results"] == []
        cmd, payload = mgr.web_commands.get_nowait()
        assert cmd == "build_search_index" and payload == {}

        # 主循环构建后再查 -> building 消除且文件匹配生效
        mgr._cmd_build_search_index()
        r2 = mgr.search_torrents("movie")
        assert r2["building"] is False
        assert [x["hash"] for x in r2["results"]] == ["HA"]


def test_api_search_endpoint(web_env):
    """GET /api/search: 端点返回搜索结果(名称匹配即时), 空查询返回空"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
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
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
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
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
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
        # ① 目录型 content_path -> 取自身(非选中语义)
        r = post({"kind": "torrent", "hash": "HA"})
        assert r.status_code == 200 and r.json() == {"opened": norm(d_content), "select": False}, r.text
        spy.assert_called_once_with(norm(d_content), select=False)
        # ② 文件型 content_path(单文件种子) -> 打开该文件并**定位选中**(R10-10)
        spy.reset_mock()
        assert post({"kind": "torrent", "hash": "HB"}).json() == {"opened": norm(f_file), "select": True}
        spy.assert_called_once_with(norm(f_file), select=True)
        # ③ content_path 缺失 -> 回退 save_path
        spy.reset_mock()
        assert post({"kind": "torrent", "hash": "HC"}).json() == {"opened": norm(d_seed), "select": False}
        spy.assert_called_once_with(norm(d_seed), select=False)
        # ④ 组: 组键首元即规范化 save_path(组内成员天然一致)
        spy.reset_mock()
        group_key = encode_group_key((norm(d_seed), ("a.mkv", )))
        assert post({"kind": "group", "key": group_key}).json() == {"opened": norm(d_seed), "select": False}
        spy.assert_called_once_with(norm(d_seed), select=False)
        # ⑤ 安全: 客户端多传的 path 被忽略 —— 打开的是服务端派生的目录, 不是它
        spy.reset_mock()
        post({"kind": "group", "key": group_key, "path": "C:/Windows/System32"})
        spy.assert_called_once_with(norm(d_seed), select=False)
        # ⑥ 未知组 / 未知 hash / 不存在目录 -> 404; kind 非法 -> 400; 均不调用系统打开
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
    assert mgr.web_commands.empty()
    # 鉴权: 无密钥 401
    assert client.post("/api/open-path", json={"kind": "wat"}).status_code == 401


def test_api_fs_dirs_endpoint(web_env, tmp_path):
    """GET /api/fs/dirs (R10-11): 服务端目录浏览 —— 允许根白名单/只列目录/穿越防护/鉴权

    这是本项目唯一新增的**文件系统读**能力, 安全边界逐条固化: ①首屏(path 空)= 允许根列表;
    ②只返回目录条目(同名文件不出现); ③上溯到允许根为止(根之上 parent 为空);
    ④`..` 穿越与白名单外路径一律 403; ⑤不存在/不是目录 404; ⑥无白名单时空返回(不报错);
    ⑦指向根外的符号链接不出现在列表里(逃逸防护); ⑧无密钥 401; ⑨只读不入命令队列。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
    root = tmp_path / "root"
    (root / "sub" / "deep").mkdir(parents=True)
    (root / "b.txt").write_bytes(b"x")
    outside = tmp_path / "outside"
    outside.mkdir()
    norm = lambda p: str(p).replace("\\", "/")  # noqa: E731  与 utils.path_normalize 同径
    mgr.store.by_hash = {"HA": SimpleNamespace(hash="HA", save_path=str(root), content_path=str(root))}
    get = lambda p=None: client.get("/api/fs/dirs", headers=auth, params={} if p is None else {"path": p})  # noqa: E731

    # ① 首屏 = 允许根列表(前端入口)
    body = get().json()
    assert body["path"] == "" and body["roots"] == [norm(root)]
    assert body["dirs"] == [{"name": norm(root), "path": norm(root)}]
    # ② 列子目录: 只出现目录(同名文件被排除); 已在允许根 -> 不能再上溯
    body = get(norm(root)).json()
    assert [d["name"] for d in body["dirs"]] == ["sub"]
    assert body["path"] == norm(root) and body["parent"] == ""
    # ③ 进入子目录后可上溯回根
    body = get(norm(root / "sub")).json()
    assert [d["name"] for d in body["dirs"]] == ["deep"]
    assert body["parent"] == norm(root)
    # ④ 越界 / .. 穿越 / 不存在 -> 403 / 403 / 404
    assert get(norm(outside)).status_code == 403
    assert get(norm(root / ".." / "outside")).status_code == 403
    assert get(norm(root / "nope")).status_code == 404
    assert get(norm(root / "b.txt")).status_code == 404  # 目标存在但是文件 -> 不是目录
    # ⑤ 符号链接逃逸: 指向根外的子目录不进列表
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
    # ⑥ 无白名单(还没有任何已知保存路径) -> 空返回而非报错
    mgr.store.by_hash = {}
    assert get().json() == {"path": "", "parent": "", "roots": [], "dirs": []}
    # ⑦ 鉴权 + 只读无副作用
    assert client.get("/api/fs/dirs").status_code == 401
    assert mgr.web_commands.empty()


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="只有大小写敏感的 FS(ext4)上两个名字才是两个目录; NTFS 上是同一个, 断言无意义")
def test_api_fs_dirs_case_sibling_is_outside_whitelist(web_env, tmp_path):
    """**大小写兄弟目录必须判为越界** —— `web._fs_real` 不得做 NTFS 式大小写折叠

    生产代码跑在**本机真实磁盘**上: Linux 下 `/x/Media` 与 `/x/media` 是两个**不同**目录。若把归一
    换成 `ntpath.normcase`(折叠大小写 + `/`->`\\`), 后者会被判成"在白名单内" ⇒ **越界放行**
    (fail-open, 安全方向反了)。`os.path.normcase` 在 Linux 是恒等函数, 恰恰是所需语义 —— 钉死它。
    ⚠ 本条只能在 Linux 上真跑(NTFS 上根本建不出"仅大小写不同"的两个目录), 由 CI 验。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
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
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    norm = lambda p: str(p).replace("\\", "/")  # noqa: E731
    mgr.store.by_hash = {"HA": SimpleNamespace(hash="HA", save_path=str(root), content_path=str(root))}
    post = lambda body: client.post("/api/fs/mkdir", json=body, headers=auth)  # noqa: E731

    # ① 正常新建
    r = post({"path": norm(root), "name": "新文件夹"})
    assert r.status_code == 200 and r.json() == {"created": norm(root / "新文件夹"), "existed": False}, r.text
    assert (root / "新文件夹").is_dir()
    # ② 重名目录幂等(不报错)
    assert post({"path": norm(root), "name": "新文件夹"}).json()["existed"] is True
    # ③ 同名文件 -> 409
    (root / "b.txt").write_bytes(b"x")
    assert post({"path": norm(root), "name": "b.txt"}).status_code == 409
    # ④ 名字含路径成分 / . / .. -> 400(只接受单层名字, 不做路径拼接)
    for bad in ("", "  ", "a/b", "a\\b", ".", ".."):
        assert post({"path": norm(root), "name": bad}).status_code == 400, bad
    # ⑤ 白名单外 / 父目录不存在 -> 403 / 404
    assert post({"path": norm(outside), "name": "x"}).status_code == 403
    assert post({"path": "", "name": "x"}).status_code == 403
    assert post({"path": norm(root / "missing"), "name": "x"}).status_code == 404
    # ⑥ 鉴权 + 不入命令队列(不绕过单一写线程: 只建目录)
    assert client.post("/api/fs/mkdir", json={"path": norm(root), "name": "x"}).status_code == 401
    assert mgr.web_commands.empty()


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
    # ❗**同时**灌进 FakeClient: 真值改走 `torrents/info` 直查(不再读同步快照),
    #   直查查的是 qB 客户端里的种子 —— 只 seed store 的话桩里查不到, 与真机不符。
    for t in tors:
        client.torrents[t.hash] = t
    seed_store(mgr, tors)
    mgr._assign_new_torrent("HA")
    mgr._assign_new_torrent("HB")
    return mgr, client, mgr.store.member_to_key["HA"]


def test_drain_web_commands_group_actions():
    """_drain_web_commands: 组级暂停/开始/汇报/删除命令在主循环侧执行, 作用于整组 hash"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        mgr.web_commands.put(("pause_group", {"key": key}))
        mgr.web_commands.put(("resume_group", {"key": key}))
        mgr.web_commands.put(("reannounce_group", {"key": key}))
        mgr._drain_web_commands()
        # reannounce 走 FakeClient 旧约定(记 None; test_actions 多处断言依赖), pause/resume 记 hash 列表
        assert client.calls == [("pause", ["HA", "HB"]), ("resume", ["HA", "HB"]), ("reannounce", None)], client.calls
        # 删除整组: delete_files 透传, 成员从快照移除
        mgr.web_commands.put(("delete_group", {"key": key, "delete_files": True}))
        mgr._drain_web_commands()
        assert client.calls[-1] == ("delete", True), f"delete_group: {client.calls}"
        assert mgr.store.by_hash == {}, "删除整组后成员应已从快照移除"


def test_drain_web_commands_torrent_actions():
    """_drain_web_commands: 单种子命令只作用于该 hash; 种子不在快照 -> 跳过(删除守阵)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        for cmd in ("pause_torrent", "resume_torrent", "reannounce_torrent"):
            mgr.web_commands.put((cmd, {"hash": "HA"}))
        mgr._drain_web_commands()
        assert [c[0] for c in client.calls] == ["pause", "resume", "reannounce"], client.calls
        assert client.calls[0][1] == ["HA"] and client.calls[1][1] == ["HA"], "单种子命令只作用于该 hash"
        # 删除守阵: 种子已不在快照 -> 不调 API
        before = list(client.calls)
        mgr.web_commands.put(("pause_torrent", {"hash": "GONE"}))
        mgr.web_commands.put(("delete_torrent", {"hash": "GONE", "delete_files": True}))
        mgr._drain_web_commands()
        assert client.calls == before, "种子不在快照应跳过(删除守阵)"


def test_api_torrent_write_endpoints_enqueue(web_env):
    """二轮种子写端点(15个) POST 转发: cmd 与参数正确入队; 无密钥 401(鉴权沿用 /api/* 依赖)"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
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
        got_cmd, got_payload = mgr.web_commands.get_nowait()
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
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
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
    cmd, payload = mgr.web_commands.get_nowait()
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
    _, payload2 = mgr.web_commands.get_nowait()
    assert "keys" not in payload2
    # 鉴权: 无密钥 401
    assert client.post("/api/torrents/bulk", json={"keys": [key], "action": "delete"}).status_code == 401


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
            mgr.web_commands.put((cmd, payload))
        mgr._drain_web_commands()
        assert client.calls[0] == ("recheck", None) and client.recheck_hashes_calls[0] == ["HA"]
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
        # ❗D2 之后回执**在 drain 阶段就写**(不再扣住等真值)—— 真机实测 qB 翻状态要 1258ms,
        #   扣着回执等 = 撤下被钉死在 1.25s+(实测撤下 2947ms)。回执只表示"命令已执行"。
        assert mgr._web_results["c1"]["status"] == "ok", "回执必须立即发, 不再等真值落地"
        # 回执**不带 truth**: 带上未落地的真值 = 让前端采纳命令前的旧值 ⇒ 弹回(红线)
        assert "truth" not in mgr._web_results["c1"], "回执不得带真值(真值改由 truth 事件推送)"
        # 真值登记为待推, 由 run() 无条件 flush(幂等; 漏调会让前端一直挂着乐观值)
        assert "c1" in mgr.web.truth_pending, "RESYNC 命令应登记待推真值"
        mgr._flush_truths()
        assert mgr._flush_truths() is None, "重复 flush 必须是安全的空操作"
        # 全部命令回执 ok
        assert all(mgr._web_results[f"c{i}"]["status"] == "ok" for i in range(1, 14)), mgr._web_results
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
            mgr.web_commands.put((cmd, payload))
        mgr._drain_web_commands()
        assert client.calls == [] and client.recheck_hashes_calls == [], client.calls


def test_drain_web_commands_share_limits_and_queue_mapping():
    """share-limits: 缺省维度按 -2(用全局)补齐; queue: 四动作映射到对应 qB 方法, 未知动作 error 回执"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        # queue 四动作 -> qB 队列端点方法(方法名映射正确)
        for action, want in (
            ("top", "queue_top"), ("up", "queue_up"), ("down", "queue_down"), ("bottom", "queue_bottom")
        ):
            mgr.web_commands.put(("queue_torrent", {"hash": "HA", "action": action}))
            mgr._drain_web_commands()
            assert client.calls[-1] == (want, ["HA"]), f"{action}: {client.calls[-1]}"
        # share-limits 缺省维度 -2 补齐(库不过滤 None, 直传会以字面量 "None" 发给 qB)
        mgr.web_commands.put(("set_share_limits", {"hash": "HA", "ratio_limit": 2.0}))
        mgr._drain_web_commands()
        assert client.calls[-1] == ("set_share_limits", (2.0, -2, -2)), client.calls[-1]
        # 未知队列动作 -> error 回执且不调 API
        before = list(client.calls)
        mgr.web_commands.put(("queue_torrent", {"hash": "HA", "action": "middle", "cmd_id": "qerr"}))
        mgr._drain_web_commands()
        assert client.calls == before
        r = mgr._web_results["qerr"]
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
            mgr.web_commands.put((cmd, {**payload, "cmd_id": cmd_id}))
        mgr.web_commands.put(("pause_torrent", {"hash": "HA"}))  # 后续命令不受影响
        mgr._drain_web_commands()
        assert client.calls == [("pause", ["HA"])], client.calls
        for _, _, cmd_id in errs:
            assert mgr._web_results[cmd_id]["status"] == "error", (cmd_id, mgr._web_results[cmd_id])


def test_drain_web_commands_bulk_torrents():
    """批量命令: 多 hash 一次 API 调用 + 聚合回执; 部分缺失/未知动作/空列表 -> error 回执"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        # pause: 一次调用传全部 hashes(单条 call 即单次调用), 全部命中 -> ok
        mgr.web_commands.put(("bulk_torrents", {"hashes": ["HA", "HB"], "action": "pause", "cmd_id": "b1"}))
        mgr._drain_web_commands()
        assert client.calls[-1] == ("pause", ["HA", "HB"]), client.calls[-1]
        assert mgr._web_results["b1"]["status"] == "ok"
        # recheck: hash 级作用范围一次传入
        mgr.web_commands.put(("bulk_torrents", {"hashes": ["HA", "HB"], "action": "recheck", "cmd_id": "b2"}))
        mgr._drain_web_commands()
        assert client.recheck_hashes_calls[-1] == ["HA", "HB"]
        assert mgr._web_results["b2"]["status"] == "ok"
        # delete: delete_files 透传, 成员从快照移除
        mgr.web_commands.put(
            ("bulk_torrents", {
                "hashes": ["HA"],
                "action": "delete",
                "delete_files": True,
                "cmd_id": "b3"
            })
        )
        mgr._drain_web_commands()
        assert client.calls[-1] == ("delete", True)
        assert mgr.store.get("HA") is None
        assert mgr._web_results["b3"]["status"] == "ok"
        # 部分缺失: 已知种子仍执行, 回执 error 带缺失计数
        mgr.web_commands.put(("bulk_torrents", {"hashes": ["HB", "GONE"], "action": "resume", "cmd_id": "b4"}))
        mgr._drain_web_commands()
        assert client.calls[-1] == ("resume", ["HB"])
        r = mgr._web_results["b4"]
        assert r["status"] == "error" and "1/2" in r["error"], r
        # 未知动作 -> error 回执, 不调 API
        before = list(client.calls)
        mgr.web_commands.put(("bulk_torrents", {"hashes": ["HB"], "action": "purge", "cmd_id": "b5"}))
        mgr._drain_web_commands()
        assert client.calls == before
        assert mgr._web_results["b5"]["status"] == "error" and "purge" in mgr._web_results["b5"]["error"]
        # 空 hash 列表 -> error 回执
        mgr.web_commands.put(("bulk_torrents", {"hashes": [], "action": "pause", "cmd_id": "b6"}))
        mgr._drain_web_commands()
        assert mgr._web_results["b6"]["status"] == "error"


def test_drain_web_commands_bulk_torrents_group_keys():
    """bulk 组键模式(DLG-02): 逐组展开成员级联全组, 与 hashes 合并去重, 缺失按组计数

    组键删除 = 组内全部在册成员一次 API 调用(与 delete_group 同级联语义);
    组不存在/成员全部不在快照计一个缺失组(不按种子数), 回执文案与种子缺失分列。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        # 组键删除: 级联全组(一次调用传全部成员), delete_files 透传, 成员从快照移除, 回执 ok
        mgr.web_commands.put(
            ("bulk_torrents", {
                "keys": [key],
                "action": "delete",
                "delete_files": True,
                "cmd_id": "g1"
            })
        )
        mgr._drain_web_commands()
        assert client.calls[-1] == ("delete", True), client.calls
        assert mgr.store.get("HA") is None and mgr.store.get("HB") is None
        assert mgr._web_results["g1"]["status"] == "ok"


def test_drain_web_commands_bulk_torrents_group_keys_mixed_and_missing():
    """bulk 组键模式: 混合选择合并去重(显式 hash 与组员重叠不重复调用); 缺失组分列计数"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        # 混合: 组(含 HA/HB) + 散种子 HA(重叠) + 散种子 GONE(缺失) -> 去重后 [HA, HB] 一次调用; 回执带缺失计数
        mgr.web_commands.put(
            ("bulk_torrents", {
                "hashes": ["HA", "GONE"],
                "keys": [key],
                "action": "pause",
                "cmd_id": "g2"
            })
        )
        mgr._drain_web_commands()
        assert client.calls[-1] == ("pause", ["HA", "HB"]), client.calls[-1]
        r = mgr._web_results["g2"]
        assert r["status"] == "error" and "1/2" in r["error"], r
        # 组键不存在/成员不在快照 -> 计缺失组, 不调 API
        before = list(client.calls)
        gone_key = ("R:/gone", ("x.mkv", ))
        mgr.web_commands.put(("bulk_torrents", {"keys": [gone_key], "action": "pause", "cmd_id": "g3"}))
        mgr._drain_web_commands()
        assert client.calls == before, "缺失组不应调用 qB API"
        r = mgr._web_results["g3"]
        assert r["status"] == "error" and "1/1 个组" in r["error"], r
        # 组部分成员仍在: 只作用于在册成员, 组不算缺失
        mgr.store.by_hash.pop("HA")
        mgr.web_commands.put(("bulk_torrents", {"keys": [key], "action": "resume", "cmd_id": "g4"}))
        mgr._drain_web_commands()
        assert client.calls[-1] == ("resume", ["HB"]), client.calls[-1]
        assert mgr._web_results["g4"]["status"] == "ok"


def test_cmd_trackers_write_invalidates_lazy_cache():
    """tracker 三兄弟写后失效 _trackers_info 惰性缓存: 下轮读取拉新值(同 tick 内后续读不拿旧值)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        rec = mgr.store.get("HA")
        # 预热: 惰性缓存持有旧 tracker 列表
        assert rec.trackers_info(mgr.client)[0]["url"] == "https://tracker.hhanclub.net/announce.php"
        assert rec._trackers_info is not None
        client.trackers_map["HA"] = [{"url": "https://new.example.com/announce"}]
        mgr.web_commands.put(("add_trackers", {"hash": "HA", "urls": ["https://extra.example.com/announce"]}))
        mgr._drain_web_commands()
        assert rec._trackers_info is None, "add_trackers 应失效惰性缓存"
        assert rec.trackers_info(mgr.client) == [{"url": "https://new.example.com/announce"}]
        # edit: 再次失效
        rec.trackers_info(mgr.client)  # 重新预热
        mgr.web_commands.put(
            (
                "edit_tracker", {
                    "hash": "HA",
                    "orig_url": "https://new.example.com/announce",
                    "new_url": "https://edited.example.com/announce"
                }
            )
        )
        mgr._drain_web_commands()
        assert rec._trackers_info is None, "edit_tracker 应失效惰性缓存"
        # remove: 再次失效
        rec.trackers_info(mgr.client)  # 重新预热
        mgr.web_commands.put(("remove_tracker", {"hash": "HA", "url": "https://new.example.com/announce"}))
        mgr._drain_web_commands()
        assert rec._trackers_info is None, "remove_tracker 应失效惰性缓存"


def test_drain_web_commands_unknown_and_error_continues():
    """_drain_web_commands: 未知命令(KeyError)与执行异常只记日志, 不中断后续命令消费"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        mgr.web_commands.put(("no_such_command", {}))  # KeyError 分支
        mgr.web_commands.put(("build_search_index", {"bogus": 1}))  # 参数错误 -> TypeError 分支
        mgr.web_commands.put(("pause_group", {"key": key}))  # 后续命令仍应执行
        mgr._drain_web_commands()
        assert client.calls[-1] == ("pause", ["HA", "HB"]), f"异常命令不应中断消费: {client.calls}"
        assert mgr.web_commands.empty()


def test_drain_web_commands_empty_queue():
    """_drain_web_commands: 队列为空时直接返回(queue.Empty 分支), 无任何 API 调用"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        mgr._drain_web_commands()
        assert client.calls == []


def test_reannounce_confirm_success_and_timeout():
    """强制汇报确认跟踪: next_announce 重置 -> ok 回执; 超时 -> error 回执(删除流程据此不删)"""
    import time as _time

    def _tracker(status, na, msg=""):
        return {"url": "https://tracker.hhanclub.net/announce.php", "status": status, "next_announce": na, "msg": msg}

    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        client.trackers_map = {"HA": [_tracker(1, 10_000)]}
        # 确认前不写回执(登记 pending), tracker 无变化时继续等待
        mgr.web_commands.put(("reannounce_torrent", {"hash": "HA", "cmd_id": "cmd1"}))
        mgr._drain_web_commands()
        assert "cmd1" in mgr._reannounce_pending and "cmd1" not in mgr._web_results
        mgr._check_reannounce_pending()
        assert "cmd1" not in mgr._web_results, "tracker 无变化应继续等待"
        client.trackers_map["HA"][0]["next_announce"] = 9_000  # next_announce 被重置(提前)
        mgr._check_reannounce_pending()
        assert mgr._web_results["cmd1"]["status"] == "ok"
        assert mgr._reannounce_pending == {}, "全部确认后跟踪应移除"
        # 超时: deadline 已过仍未确认 -> error 回执
        mgr.web_commands.put(("reannounce_torrent", {"hash": "HA", "cmd_id": "cmd2"}))
        mgr._drain_web_commands()
        mgr._reannounce_pending["cmd2"]["deadline"] = _time.time() - 1
        mgr._check_reannounce_pending()
        assert mgr._web_results["cmd2"]["status"] == "error"
        assert "超时" in mgr._web_results["cmd2"]["error"]


def test_reannounce_confirm_group_aggregate():
    """组强制汇报: 按种子逐个确认, 部分失败 -> 聚合 error 回执带失败计数"""
    def _tracker(status, na, msg=""):
        return {"url": "https://tracker.hhanclub.net/announce.php", "status": status, "next_announce": na, "msg": msg}

    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        client.trackers_map = {
            "HA": [_tracker(3, 10_000)],  # updating = 正在汇报 -> 成功
            "HB": [_tracker(4, 10_000, "rejected")],  # not working + 错误消息 -> 失败
        }
        mgr.web_commands.put(("reannounce_group", {"key": key, "cmd_id": "cmd3"}))
        mgr._drain_web_commands()
        assert "cmd3" not in mgr._web_results
        mgr._check_reannounce_pending()
        result = mgr._web_results["cmd3"]
        assert result["status"] == "error" and "1/2" in result["error"]


def test_confirm_reannounce_result_matrix():
    """_confirm_reannounce_result 判定矩阵: updating/重置/变 working=成功; not working+msg=失败; 其余 None"""
    from auto_qb.core.qbmanager import QbManager

    base = {"u": (1, 10_000)}

    def _trackers(status, na, msg="", url="u"):
        return [{"url": url, "status": status, "next_announce": na, "msg": msg}]

    f = QbManager._confirm_reannounce_result
    assert f(_trackers(3, 10_000), base) is True, "updating = qB 正在汇报"
    assert f(_trackers(1, 9_000), base) is True, "next_announce 被重置(提前)"
    assert f(_trackers(2, 10_000), base) is True, "从非 working 变 working"
    assert f(_trackers(4, 10_000, "rejected"), base) is False, "not working + 错误消息 = tracker 拒绝"
    assert f(_trackers(1, 10_000), base) is None, "无变化继续等待"
    assert f(_trackers(4, 10_000, ""), base) is None, "not working 但无 msg 不武断判失败"
    # DHT 等虚拟 tracker 不参与判定(仅虚拟 tracker 时无结论)
    assert f([{"url": "** [DHT]", "status": 2, "next_announce": 9_000, "msg": ""}], base) is None


def test_cmd_group_actions_skip_missing_group():
    """组级命令: 组 key 不存在或成员已不在快照 -> 空 hashes, 不调 qB API"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        gone = ("R:/gone", ("x.mkv", ))
        mgr.store.groups[gone] = ["NOT_IN_STORE"]  # 成员不在快照 -> _group_hashes 过滤为空
        assert mgr._group_hashes(gone) == []
        for cmd in ("pause_group", "resume_group", "reannounce_group", "delete_group"):
            mgr.web_commands.put((cmd, {"key": gone}))
        mgr.web_commands.put(("pause_group", {"key": ("R:/nonexistent", ("y.mkv", ))}))  # 组 key 不存在
        mgr._drain_web_commands()
        assert client.calls == [], f"空组不应调用 qB API: {client.calls}"


def test_cmd_reload_config_delegates():
    """_cmd_reload_config: 委托 apply_new_config(热重载分级应用逻辑本身由 config 影响分析测试覆盖)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        applied = []
        mgr.apply_new_config = lambda cfg: applied.append(cfg) or {"applied": True}
        new_cfg = object()
        mgr.web_commands.put(("reload_config", {"config": new_cfg}))
        mgr._drain_web_commands()
        assert applied == [new_cfg], "reload_config 命令应把新配置交给 apply_new_config"


# ---------- Web 视图与配置热重载 ----------


def test_ensure_group_view_rebuilds_when_dirty():
    """ensure_group_view: 脏时立即重建(Web 请求侧兜底), 干净时直接返回当前引用(不重建)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        mgr._group_view = []
        mgr._group_view_dirty = True
        view = mgr.ensure_group_view()
        assert len(view) == 1 and view[0]["count"] == 2, f"脏时应重建分组视图: {view}"
        assert mgr._group_view_dirty is False
        assert mgr.ensure_group_view() is view, "干净时直接返回当前引用(不重建)"


def test_ensure_group_state_versioning():
    """ensure_group_state: 重建分组视图时版本号自增; rid 一致时不回传 groups(体积极小)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        mgr._group_view = []
        mgr._group_view_dirty = True
        start_ver = mgr._group_view_ver
        state = mgr.ensure_group_state(rid=None)  # 首次: 版本不匹配 -> 全量
        assert state["updated"] is True
        assert state["rid"] == start_ver + 1, "重建后版本号应自增"
        assert len(state["groups"]) == 1
        assert state["singles"] == [], "未归组种子为空时 singles 应为空列表(键必须存在, 前端按同门控替换)"
        # 同版本再次请求: 不回传 groups
        again = mgr.ensure_group_state(rid=state["rid"])
        assert again["updated"] is False
        assert again["rid"] == state["rid"]
        assert "groups" not in again and "singles" not in again
        # 视图变化后版本自增, 旧 rid 失效 -> 重新回传
        mgr._group_view_dirty = True
        bumped = mgr.ensure_group_state(rid=state["rid"])
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
        mgr._group_view_dirty = True
        state = mgr.ensure_group_state(rid=None, view="show")
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
        mgr._group_view_dirty = True
        state = mgr.ensure_group_state(rid=None)
        assert [s["hash"] for s in state["singles"]] == ["HZ"], f"singles 应只含未归组种子: {state['singles']}"
        assert state["singles"][0]["save_path"] == r"R:\Elsewhere"
        assert "hr_triggered" in state["singles"][0] and "name" in state["singles"][0]
        grouped_hashes = {m["hash"] for g in state["groups"] for m in g["members"]}
        assert not (grouped_hashes & {s["hash"] for s in state["singles"]}), "已归组种子不得出现在 singles"
        again = mgr.ensure_group_state(rid=state["rid"])
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
        mgr._group_view_dirty = True
        state = mgr.ensure_group_state(rid=None)
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
        mgr._group_view = []
        mgr._group_view_dirty = True
        state = mgr.ensure_group_state(rid=None)
        assert "shows" in state and state["shows"]["list"] == view["list"]
        assert "unrecognized" in state["shows"]
        again = mgr.ensure_group_state(rid=state["rid"])
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
        assert mgr._shows_pending is True, "季包种子索引未覆盖: 应标记待解析"
        assert ("build_search_index", {}) in list(mgr.web_commands.queue), "应投递索引构建命令"
        node = view["list"][0]["seasons"][0]["episodes"][0]
        assert node["key"] == ["pack"], f"索引未建成前整季包无范围: {node['key']}"
        # 消费构建命令(真实链路: 主循环 _drain -> _build_search_index), 文件就位 -> 清 pending + 置脏
        mgr._drain_web_commands()
        assert mgr._shows_pending is False
        assert mgr._group_view_dirty is True, "索引推进是文件兑底唯一信号, 应触发追剧视图重建"
        mgr._group_view_dirty = True
        view = mgr._build_shows_view()
        node = view["list"][0]["seasons"][0]["episodes"][0]
        assert node["key"] == ["range", 1, 3], f"季包从文件列表展开集数范围: {node['key']}"
        # 索引已覆盖全部种子: 不再重复投递
        assert ("build_search_index", {}) not in list(mgr.web_commands.queue)
        assert mgr._shows_pending is False


def test_group_view_ver_seeded_from_start_time():
    """版本号以进程启动时间播种: 重启后不会回落到旧客户端已持有的值(否则前端会一直展示旧列表)"""
    from helpers import make_manager

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        assert mgr._group_view_ver > 1_600_000_000, "应为时间戳量级, 而非 0/1 小整数"


def test_api_state_rid_gate(web_env):
    """/api/state 带 rid: 版本一致时 updated=False 且无 groups; 缺省/不匹配回传全量"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
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
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
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
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
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
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

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

    ❗这是 issue 26-09-20-1646(状态栏速度恒为 0)的防复现守阵。状态栏是**跨视图**的常驻
    显示, 一旦它的数值来自按视图裁剪的数组, 就会在某个视图下恒 0 或停在冻结的旧值。
    故 totals 必须与 traffic / server 同属"恒回传"口径: 不参与 VIEW_ARRAYS 分片、不受 rid 门控。
    """
    from fastapi.testclient import TestClient

    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        mgr._web_token = "t"
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

        # ① 种子页: groups 根本不回传 —— 但若 totals 也跟着没了, 状态栏就恒为 0
        t = tc.get("/api/state?view=torrent", headers=auth).json()
        assert "groups" not in t, "种子页按设计不回 groups(P1-1 体积优化)"
        assert t["status"]["totals"] == want, f"种子页缺少/错误的 totals: {t['status'].get('totals')}"

        # ② 辅种页: totals 与种子页**同源同值**(不能因视图不同而变)
        g = tc.get("/api/state?view=group", headers=auth).json()
        assert g["status"]["totals"] == want

        # ③ rid 命中(updated=False, 任何数组都不回)时 totals 仍必须回传 —— 否则稳态下每轮都拿不到
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
    """_state_kind: 状态语义分类(前端着色) —— 暂停态优先于下载/做种, errored/checking 最前"""
    from auto_qb.core.qbmanager import QbManager
    from helpers import FakeTorrent

    assert QbManager._state_kind(FakeTorrent(hash="H", name="t", state=state)) == kind


def test_apply_new_config_levels(monkeypatch):
    """apply_new_config: 按影响级别应用 —— L0 仅换配置; L1 重挂日志/通知+重连+web 重启;
    L2 重建任务队列/规则并抑制事件一轮; R 仅提示重启不应用"""
    import logging as std_logging

    from auto_qb.core import qbmanager as qbm
    from auto_qb.config.impact import ConfigChange
    from helpers import make_manager

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        new_cfg = mock.MagicMock(name="new_config")
        # 副作用隔离: 日志重挂/通知/重连/规则加载均替身(本测试只验证分级分支)
        mgr._setup_logging = mock.MagicMock()
        mgr._load_rules = mock.MagicMock()
        mgr._create_global_tasks = mock.MagicMock()
        mgr.connect = mock.MagicMock(return_value=True)
        monkeypatch.setattr(qbm, "setup_notify", mock.MagicMock(return_value=std_logging.NullHandler()))

        def _apply(changes):
            # diff 结果受控(变更判定本身由 config/impact 单测覆盖)
            monkeypatch.setattr("auto_qb.config.impact.diff_config_impacts", lambda old, new: changes)
            return mgr.apply_new_config(new_cfg)

        # ① L0: 仅替换配置对象, 任务队列保持不变(运行时动态读取项)
        queue_before = mgr.task_queue
        res = _apply([ConfigChange("main_tick", "L0", 1, 2)])
        assert res == {"applied": True, "levels": ["L0"], "changes": 1, "restart_required": []}, res
        assert mgr.config is new_cfg
        assert mgr.task_queue is queue_before, "L0 不应重建任务队列"

        # ② L1: 重挂日志/通知 + 重连 + web 监听身份变化时重启(次序: 先停旧并等其线程退出 -> 启新)
        mgr._notify_handler = std_logging.NullHandler()
        # 旧配置(复现真实新旧对比): hr_check 也要给上 —— apply_new_config 的 L1 分支要拿旧值
        # 与新的 channel/shared_dir 比对(见 HrRuntime.apply), 缺了会 AttributeError
        mgr.config = SimpleNamespace(web=_web_stub(port=38080), hr_check=HrCheckConfig())
        new_cfg.web = _web_stub(port=38081)  # 仅端口变化 -> 需重启
        old_handle = mock.MagicMock()
        mgr._web_handle = old_handle
        calls = []

        def _fake_stop(handle, timeout=0.0):
            calls.append(("stop", handle))
            return True

        def _fake_start(m):
            calls.append(("start", m))
            return "新句柄"

        monkeypatch.setattr("auto_qb.webui.stop_web_server", _fake_stop)
        monkeypatch.setattr("auto_qb.webui.start_web_server", _fake_start)
        res = _apply([ConfigChange("web.port", "L1", 38080, 38081)])
        assert res["levels"] == ["L1"]
        mgr._setup_logging.assert_called_once()
        mgr.connect.assert_called_once()
        assert calls == [("stop", old_handle), ("start", mgr)], "必须先停旧服务(并等其线程退出)再启新服务"
        assert mgr._web_handle == "新句柄", "web 句柄应换为新服务句柄"

        # ③ L2: 重建任务队列/规则 + 抑制下一轮事件分派
        queue_before = mgr.task_queue
        res = _apply([ConfigChange("interval", "L2", 1, 2)])
        assert res["levels"] == ["L2"]
        assert mgr.task_queue is not queue_before, "L2 应重建任务队列"
        assert mgr._suppress_events is True
        mgr._load_rules.assert_called_once()
        mgr._create_global_tasks.assert_called_once()

        # ④ R: 仅提示重启, 不计入应用级别
        res = _apply([ConfigChange("state_file", "R", "a", "b")])
        assert res["restart_required"] == ["state_file"]
        assert res["levels"] == []


def test_apply_new_config_l2_preserves_runtime_state(monkeypatch):
    """守阵(2026-09-22, issue 26-09-21-1347): L2 热重载不得重读磁盘 state 回滚运行期内存态

    state 平时不落盘(仅优雅退出/跳检重加落盘), 磁盘上的 state.json 永远是「上次退出」
    的旧版 —— L2 分支若 _load_state() 会把本次运行累计的 exec_history/skip_check_day/
    recheck_fails 等整体回滚到旧版, Web UI 改规则保存即确定性触发。断言用「对象同一性
    + 内容保留」双断言, 不 mock _load_state 本身(避免耦合实现符号)。
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
        # 替身: 与分级测试同款(只验证 L2 分支行为, 变更判定由 impact 单测覆盖)
        mgr._setup_logging = mock.MagicMock()
        mgr._load_rules = mock.MagicMock()
        mgr._create_global_tasks = mock.MagicMock()
        mgr.connect = mock.MagicMock(return_value=True)
        monkeypatch.setattr(
            "auto_qb.config.impact.diff_config_impacts", lambda old, new: [ConfigChange("interval", "L2", 1, 2)]
        )

        queue_before = mgr.task_queue
        res = mgr.apply_new_config(mock.MagicMock(name="new_config"))

        assert res["levels"] == ["L2"]
        assert mgr.task_queue is not queue_before, "L2 仍应重建任务队列(本守阵只钉 state 语义)"
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


def test_apply_web_config_skips_restart_when_bind_unchanged(monkeypatch):
    """监听身份(enabled/host/port)未变 -> 不重启服务器, 仅刷新密钥(鉴权每请求实时读取)

    否则改个日志级别之类的 L1 变更也会把 WEB 服务器拆了重建, 白白放大端口竞态窗口。
    """
    from helpers import make_manager

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        # 真实调用点: self.config 已是新配置; 参数是旧 web 段(仅用于对比监听身份)
        mgr.config.web = _web_stub(port=8080, token="新密钥")
        old_handle = mock.MagicMock()
        mgr._web_handle = old_handle
        monkeypatch.setattr("auto_qb.webui.start_web_server", mock.MagicMock())
        monkeypatch.setattr("auto_qb.webui.stop_web_server", mock.MagicMock())

        mgr._apply_web_config(_web_stub(port=8080, token="旧密钥"))

        from auto_qb.webui import start_web_server, stop_web_server

        start_web_server.assert_not_called()
        stop_web_server.assert_not_called()
        assert mgr._web_handle is old_handle, "监听身份未变时不应重启"
        assert mgr._web_token == "新密钥", "密钥变更应即时刷新(无需重启)"


def test_start_web_server_reports_failure_when_port_taken(tmp_path, caplog):
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
        with caplog.at_level(logging.ERROR, logger="auto_qb.web"):
            handle = start_web_server(mgr)
        assert handle.started is False, "端口被占用时不应报告就绪"
        assert any("WEB UI 启动失败" in r.message for r in caplog.records), "失败必须记 ERROR"
        stop_web_server(handle)


def _noise_loop():
    """异常处理器替身: 只关心「是否把异常交还给默认处理器」"""
    return mock.MagicMock()


def _reset_noise_state():
    from auto_qb.webui.server import lifecycle as lc

    lc._noise_state.update(at=0.0, suppressed=0)
    return lc


def test_web_loop_exception_handler_downgrades_connection_reset(caplog):
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
    with caplog.at_level(logging.INFO, logger="auto_qb.web"):
        lc._web_loop_exception_handler(loop, context)

    noise = [r for r in caplog.records if "WEB 连接被对端中断" in r.message]
    assert len(noise) == 1 and noise[0].levelno == logging.INFO, "断连应记为一行 INFO"
    assert not any(r.levelno >= logging.ERROR for r in caplog.records), "不得再出现 ERROR"
    loop.default_exception_handler.assert_not_called(), "波动型异常不应交给默认处理器"


def test_web_loop_noise_log_throttled_in_window(caplog):
    """断连日志按窗口节流: 窗口内只记首条, 出窗口时附被抑制条数(SSE 重连会成串刷屏)"""
    lc = _reset_noise_state()
    loop = _noise_loop()
    context = {"exception": ConnectionResetError(10054, "远程主机强迫关闭了一个现有的连接。")}
    with caplog.at_level(logging.INFO, logger="auto_qb.web"):
        lc._web_loop_exception_handler(loop, context)
        lc._web_loop_exception_handler(loop, context)
        assert len([r for r in caplog.records if "WEB 连接被对端中断" in r.message]) == 1, "窗口内只记一条"

        lc._noise_state["at"] -= lc.NET_NOISE_WINDOW  # 推进到窗口外
        lc._web_loop_exception_handler(loop, context)

    msgs = [r.message for r in caplog.records if "WEB 连接被对端中断" in r.message]
    assert len(msgs) == 2, "出窗口后应再记一条"
    assert "另有 1 条" in msgs[-1], "被抑制的条数要带出来, 不能静默丢"
    loop.default_exception_handler.assert_not_called()


def test_web_loop_exception_handler_delegates_real_bug(caplog):
    """反向守阵: 非网络波动的异常(真 bug)一律不吞, 交回 asyncio 默认处理器"""
    lc = _reset_noise_state()
    loop = _noise_loop()
    context = {"message": "Task exception was never retrieved", "exception": ValueError("真 bug")}
    lc._web_loop_exception_handler(loop, context)

    loop.default_exception_handler.assert_called_once_with(context), "真 bug 必须照旧走默认处理器(ERROR)"
    assert not [r for r in caplog.records if "WEB 连接被对端中断" in r.message], "不得被误判成网络波动"


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
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
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
        mgr._web_token = "t"
        mgr._traffic_view = {"state": "enabled", "limit": {"target": {"up": 100, "down": 50}}}
        tc = TestClient(create_app(mgr))
        auth = {"Authorization": "Bearer t"}
        data = tc.get("/api/speed/mode", headers=auth).json()
        assert data["curve_enabled"] is True
        assert data["curve_target"] == {"upload_kib": 100, "download_kib": 50}
        assert data["current"] == {"upload_limit": 0, "download_limit": 0}
        mgr._traffic_view = {"state": "disabled", "limit": {}}
        data = tc.get("/api/speed/mode", headers=auth).json()
        assert data["curve_enabled"] is False and data["curve_target"] is None
        # 覆盖命令: 入队 + 主循环消费 -> transfer 端点写入(bytes)
        cmd_id = tc.post("/api/speed/override", json={
            "upload_kib": 2048,
            "download_kib": 1024
        }, headers=auth).json()["cmd_id"]
        mgr._drain_web_commands()
        assert mgr._web_results[cmd_id]["status"] == "ok"
        assert ("transfer_set_upload_limit", 2048 * 1024) in client.calls
        assert ("transfer_set_download_limit", 1024 * 1024) in client.calls


def test_api_speed_mode_curve_config_disabled():
    """曲线存在但 enabled=False -> /api/speed/mode 返回 curve_enabled=False(快照滞后也兑底); 对照 enabled=True 不影响"""
    from fastapi.testclient import TestClient

    from auto_qb.config import CurvePoint, GlobalSpeedLimitCurve, PeriodCurve
    from helpers import FakeClient, make_manager

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        mgr._web_token = "t"
        mgr.config.global_speed_limit_curve = GlobalSpeedLimitCurve(
            dat_path="x.dat",
            curves=[PeriodCurve(period="day", upload_points=[CurvePoint(threshold_bytes=1, speed_bytes_per_s=1)])],
            enabled=False,
        )
        mgr._traffic_view = {"state": "ok", "limit": {"target": {"up": 100, "down": 50}}}  # 滞后快照
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
        mgr._web_token = "t"
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
        cmd, payload = mgr.web_commands.queue[0]  # peek 不消费: drain 才是回执写入者
        assert cmd == "add_torrents"
        assert payload["files"] == [b"d8:announce"]
        assert payload["urls"] == ["magnet:?xt=urn:btih:X"]
        assert payload["paused"] is True and payload["auto_tmm"] is True
        assert payload["sequential"] is True and payload["skip_checking"] is False
        assert payload["tags"] == ["4K", "HDR"]
        mgr._drain_web_commands()
        assert mgr._web_results[cmd_id]["status"] == "ok"
        adds = [c for c in client.calls if c[0] == "add"]
        assert len(adds) == 2, "文件与链接各一次 torrents_add"
        assert adds[0][1]["paused"] is True and adds[0][1]["use_auto_torrent_management"] is True
        assert adds[0][1]["tags"] == ["4K", "HDR"]
        # 空来源: 400
        assert tc.post("/api/torrents/add", json={}, headers=auth).status_code == 400


def test_add_torrent_receipt_and_optional_flags():
    """添加种子回执两形态 + 两个 optional 选项恒显式下发 + 成功走 INFO(2026-09-24 真机 bug)

    ① 回执判定只认 `"Ok." in str(result)` ⇒ 在 qB 5.2.3(Web API 2.14.0 起 `/torrents/add` 改成
       JSON 元数据 `{success_count, failure_count, pending_count, added_torrent_ids}`)恒为假 ⇒
       种子明明加进去了, WEB UI 却弹"添加种子失败";
    ② 停止位被"False 就不传"的过滤器吞掉 ⇒ qB 回落到**会话级**默认(SessionImpl::
       initLoadTorrentParams 的 `addStopped.value_or(isAddTorrentStopped())`)⇒ 前端「添加后开始」
       勾了没用。另: 停止位只能用 `is_stopped=` 传 —— 库内 `is_paused or is_stopped` 会把
       `is_paused=False` 折成 None(实测请求体为空);
       同类的「自动种子管理」也是 `std::optional`(缺省回落 `savePath 空 ∧ 全局未禁自动管理`),
       一并按"恒显式"钉住;
    ③ 成功路径原来记 WARNING, 而 NotifyHandler 挂在 auto_qb logger 上 ⇒ 每次添加成功都往桌面推
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
        # ❗不能用 caplog: make_manager 走 setup_logging, 那里有 `logging.getLogger().handlers.clear()`
        #   —— 用例体内建 manager 会把 pytest 挂在 root 上的采集 handler 一并清掉, 之后一条也抓不到
        #   (症状是"日志断言恒空")。挂模块 logger 不受 root 清理影响, 且能验到真实级别。
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        mgr._web_token = "t"
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
                mgr._drain_web_commands()
                return cmd_id

            def add_logs():
                return [(r.levelno, r.getMessage()) for r in cap.records if "添加种子" in r.getMessage()]

            # ① 新形态(API >= 2.14.0): JSON 元数据 -> 受理; 成功必须是 INFO(改前: error + WARNING)
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
            assert mgr._web_results[post_add(False)]["status"] == "ok"
            assert [lvl for lvl, _ in add_logs()] == [logging.INFO], "受理成功不得走 WARNING(通知联动会直推桌面弹窗)"

            # ② 部分失败 -> error 回执(部分成功也报错, 与 bulk 同一口径)且走 WARNING
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
            assert mgr._web_results[cid]["status"] == "error"
            assert "成功 1 / 失败 1" in mgr._web_results[cid]["error"]
            assert [lvl for lvl, _ in add_logs()] == [logging.WARNING]

            # ③ 仅 pending(magnet 元数据未就绪)也是受理, 不是失败
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
            assert mgr._web_results[post_add(False)]["status"] == "ok"

            # ④ 旧形态文本仍认(API < 2.14.0 的 "Ok."/"Fails.")
            add_returns("Ok.")
            assert mgr._web_results[post_add(False)]["status"] == "ok"
            add_returns("Fails.")
            assert mgr._web_results[post_add(False)]["status"] == "error"

            # ⑤ 两个 optional 选项必须**显式**下发(省略 = 吃 qB 会话/全局默认, 勾选框失效):
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
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
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
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
    assert client.get("/api/categories", headers=auth).json() == {"categories": {"mv": {"save_path": "R:/mv"}}}
    assert client.get("/api/tags", headers=auth).json() == {"tags": ["4K", "HDR"]}


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
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
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
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
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
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
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
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
    log_path = os.path.join(mgr.data_dir, "auto-qb.log")
    mgr.config.logging.format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    lines = _log_lines(
        mgr.config.logging.format,
        [("auto_qb.core.x", logging.INFO, "启动完成"), ("auto_qb.core.y", logging.WARNING, "连接重试")]
    )
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    mgr.config.logging.file = log_path
    # ①格式里没有等级字段 -> 等级无从判定
    mgr.config.logging.format = "%(asctime)s %(message)s"
    data = client.get("/api/log?lines=100&level=WARNING", headers=auth).json()
    assert data["lines"] == lines and data["note"] == NOTE_NO_LEVEL_FIELD
    # ②格式有等级字段, 但文件里的行是另一种格式(改了 format, 旧行还在) -> 一行都对不上
    mgr.config.logging.format = "%(levelname)s|%(asctime)s|%(message)s"
    data = client.get("/api/log?lines=100&level=WARNING", headers=auth).json()
    assert data["lines"] == lines and data["note"] == NOTE_FORMAT_MISMATCH
    # 不过滤时无论哪种格式都照常给全部行, 且不带 note
    data = client.get("/api/log?lines=100", headers=auth).json()
    assert data["lines"] == lines and data["note"] == ""


def test_apply_web_config_toggle_enabled(monkeypatch):
    """web.enabled 热开关: 关 -> 开(启动服务器); 开 -> 关(停止并清空句柄)"""
    from helpers import make_manager

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        started = mock.MagicMock(return_value="新句柄")
        stopped = mock.MagicMock()
        monkeypatch.setattr("auto_qb.webui.start_web_server", started)
        monkeypatch.setattr("auto_qb.webui.stop_web_server", stopped)

        # 关 -> 开(旧句柄为 None, 原先该场景完全不生效)
        mgr.config.web = _web_stub(enabled=True, port=8080)
        mgr._web_handle = None
        mgr._apply_web_config(_web_stub(enabled=False, port=8080))
        started.assert_called_once()
        assert mgr._web_handle == "新句柄"

        # 开 -> 关: 停止并清空句柄
        mgr.config.web = _web_stub(enabled=False, port=8080)
        mgr._apply_web_config(_web_stub(enabled=True, port=8080))
        stopped.assert_called_once()
        assert mgr._web_handle is None


# ---------- 种子中心视图(WEB UI 替代 qB 界面: 种子页/详情抽屉/全局统计) ----------


def test_seed_flat_view_fields_and_gating():
    """种子平铺视图(SEED_ITEM): _build_flat_view 全字段契约 + ensure_group_state 同门控回传

    字段集与前端契约一字不差(详见实施 prompt); eta/time_active 按分钟量化(与重建判定
    同一步长); HR 字段与分组成员视图同源; 同版本请求不回传 torrents(与 groups/singles 同门控)。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

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
        state = mgr.ensure_group_state(rid=None)
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
        again = mgr.ensure_group_state(rid=state["rid"])
        assert "torrents" not in again and "groups" not in again and "singles" not in again


def test_flat_view_refreshed_by_main_loop_tick():
    """种子页速度随主循环刷新(2026-09-18 缺陷回归: 平铺视图曾被"饿死")

    症状: 状态栏"速度合计"正常(它取 groups 求和, 由主循环每 tick 重建), 而种子页行内
    速度长时间不变。真因: 主循环只重建 `_group_view` 就把**共享**脏标记清掉 ⇒ Web 线程
    的兜底重建永不触发 ⇒ 平铺视图(flat)永远停在旧快照, 而版本号照常自增 ⇒ 前端判
    `updated=true` 把**陈旧数组整表换上去**。

    本用例钉住端到端事实: 主循环 tick 之后, Web 请求拿到的 torrents 必须是**新**速度。
    """
    from helpers import FakeClient, FakeTorrent, make_manager

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1", state="downloading", dlspeed=100, progress=0.5)
        client.torrents["H2"] = FakeTorrent(hash="H2", name="T2", state="downloading", dlspeed=200, progress=0.5)
        mgr.config.grouping.enabled = True
        mgr.touch_web_client()  # Web 活跃(否则主循环跳过组装)
        mgr._tick(dry_run=False)
        first = mgr.ensure_group_state(rid=None)
        assert sorted(t["dlspeed"] for t in first["torrents"]) == [100, 200], "首轮应建出平铺视图"

        client.torrents["H1"].dlspeed = 999
        client.torrents["H2"].dlspeed = 888
        mgr.touch_web_client()
        mgr._tick(dry_run=False)  # 速度变化 -> 置脏 -> 主循环重建
        second = mgr.ensure_group_state(rid=first["rid"])
        assert second["updated"] is True, "视图版本号应随速度变化自增"
        got = {t["hash"]: t["dlspeed"] for t in second["torrents"]}
        assert got == {"H1": 999, "H2": 888}, f"种子页速度应随主循环刷新(修前恒为旧快照): {got}"
        # 未归组单种子视图(第二个受害者)同样要跟上
        assert {t["hash"]: t["dlspeed"] for t in second["singles"]} == got


def test_rebuild_views_single_entry_point():
    """rebuild_views 是**唯一**重建入口: 四份视图 + 版本号 + 脏标记一次完成

    在调用点各建一部分必然漏建(历史漏了 flat/singles/shows)—— 新增视图只能挂在这里。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        seed_store(mgr, [FakeTorrent(hash="H1", name="T1", dlspeed=1), FakeTorrent(hash="H2", name="T2", dlspeed=2)])
        mgr._group_view_dirty = True
        ver = mgr._group_view_ver
        mgr.rebuild_views()
        assert mgr._group_view_dirty is False, "重建后脏标记复位"
        assert mgr._group_view_ver == ver + 1, "版本号自增"
        assert sorted(t["dlspeed"] for t in mgr._flat_view) == [1, 2], "平铺视图同次重建"
        assert sorted(t["dlspeed"] for t in mgr._singles_view) == [1, 2], "单种子视图同次重建"
        assert mgr._shows_view["unrecognized"] == ["H1", "H2"], "追剧视图同次重建(T1/T2 无集数标记)"
        # 幂等: 标记已清 -> 不重复重建(惰性语义不被破坏)
        mgr.ensure_group_view()
        assert mgr._group_view_ver == ver + 1


def test_api_state_status_carries_server_state(web_env):
    """/api/state 的 status **恒**回传 server_state(不受 rid 门控)

    状态栏常显统计与"限制速度"取它。以前前端要为此单独再打一次 /api/stats —— 两条链路
    刷新频率不同 ⇒ 出现"状态栏速度正常、种子行速度滞后"的错位观测。合并后每轮只剩
    1 条请求, 且两者**同源同轮**。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
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
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
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
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
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
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
    first = client.get("/api/torrents/HA/files", headers=auth).json()
    assert first == fake.files_map["HA"]
    assert fake.files_calls == 1
    # 窗口内重复请求: 命中缓存, 不再打 qB
    assert client.get("/api/torrents/HA/files", headers=auth).json() == first
    assert fake.files_calls == 1, "同一时间窗内的重复请求应合并为一次 qB 调用"
    # 写命令后失效(模拟主循环消费了一条写命令)
    mgr._web_write_seq += 1
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
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
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
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
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
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
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
    ① 本地桩服务没有主循环 ⇒ wait_ms 恒为 0 ⇒ 「投递 → 回执」这一段从来没被测到;
    ② 埋点只随回执回传, 要看就得开 F12 —— 真机上用户常常开不了/不愿开, 等于没有埋点。
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
    # ① 慢 -> WARNING, 且带归因提示(排队/执行各自指向不同的后端原因)
    with caplog.at_level(logging.DEBUG):
        caplog.clear()
        t._log_cmd_timing("pause_torrent", {"wait_ms": 1800.0, "exec_ms": 2.0})
    recs = [r for r in caplog.records if "[cmd]" in r.getMessage()]
    assert recs, "慢命令没有落日志 —— 真机无法排查"
    assert recs[-1].levelno == logging.WARNING, f"慢命令应为 WARNING, 实际 {recs[-1].levelname}"
    assert "1800" in recs[-1].getMessage()

    # ② 快 -> DEBUG(2026-09-21 改: 原本是 INFO, 但每条命令都打会把日志刷满;
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

    # ③ 自投递命令(建索引等)频次高 -> 压到 DEBUG, 不许进常规日志
    with caplog.at_level(logging.DEBUG):
        caplog.clear()
        t._log_cmd_timing("build_search_index", {"wait_ms": 900.0, "exec_ms": 900.0})
    recs = [r for r in caplog.records if "[cmd]" in r.getMessage()]
    assert recs and recs[-1].levelno == logging.DEBUG, "自投递命令会刷屏, 必须压到 DEBUG"

    assert CMD_SLOW_MS > 0


def _mk_mgr_with_one_torrent(state="pausedDL", progress=1.0):
    """一个只含单个种子的 QbManager(供回执时序类断言用)

    ❗临时目录**挂到 mgr 上**, 不用 `tempfile.mkdtemp()`(2026-09-23 实测): 后者没有任何人回收,
    每跑一次就在 TMPDIR 根下留一个 `tmpXXXX` 目录 —— 实测已积到 1268 个。
    也不能写成"函数内建 TemporaryDirectory 但不返回": 局部对象出函数即被回收, 目录当场消失,
    mgr 后续写 state.json 会失败。挂给 mgr 后随 mgr 释放即删, 两头都对。
    """
    import tempfile

    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

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
      ① 回执立刻发 —— 只表示"命令已执行", **不带 truth**(带上未落地的真值 = 让前端采纳
         命令前的旧值 ⇒ 弹回, 那条红线不能破); 前端据此结束压暗 ⇒ 撤下降到 10~20ms。
      ② 真值继续直查, 落地了再推 `truth` 事件; **超时不推**(宁可让前端超时回滚)。
    """
    import time

    from auto_qb.webui.commands import TRUTH_PUSH_CAP_MS

    mgr, tor = _mk_mgr_with_one_torrent(state="pausedDL", progress=1.0)
    rt = mgr.web
    h = tor.hash
    pushed = []
    rt.notify = lambda etype, payload: (pushed.append((etype, payload)), 0)[1]

    # ① 回执立即到账, 且**不带 truth**
    rt.defer_receipt("r1", "resume_torrent", {"hash": h}, {"wait_ms": 0.0, "exec_ms": 1.0})
    assert rt.results["r1"]["status"] == "ok", "回执必须立即发(不再扣住等真值)"
    assert "truth" not in rt.results["r1"], "回执带未落地的真值 ⇒ 前端采纳旧值 ⇒ 弹回"
    assert "r1" in rt.truth_pending, "真值应登记为待推"

    # ② 真值没落地 -> 不推
    rt.flush_truths()
    assert not [p for p in pushed if p[0] == "truth"], "真值未落地不得推送"

    # ③ 真值落地 -> 推 `truth` 事件, 内容是落地后的值
    tor.state = "uploading"
    rt.flush_truths()
    ev = [p for p in pushed if p[0] == "truth"]
    assert len(ev) == 1, ev
    assert ev[0][1]["truth"][h]["kind"] == "seeding", ev[0][1]
    assert "r1" not in rt.truth_pending, "推完应出队"

    # ④ 超时兜底: 真值始终不落地则**放弃推送**(不是推一个可能是旧值的真值)
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
    ❗这条守阵要能挡住"改回读 store.by_hash": 那样 truth 会变成 paused, 断言立刻红。
    """
    with tempfile.TemporaryDirectory() as td:
        from helpers import FakeClient, FakeTorrent, make_manager, seed_store

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

    ❗本条**同时**修掉一个既有缺陷: 原 `test_truth_hold_budget_matches_backend` 在文件里
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
_GOLDEN_ROUTES = {
    ("GET", "/"),
    ("GET", "/api/categories"),
    ("POST", "/api/categories"),
    ("POST", "/api/categories/edit"),
    ("POST", "/api/categories/remove"),
    ("GET", "/api/cmd/{cmd_id}"),
    ("GET", "/api/config"),
    ("PUT", "/api/config"),
    ("POST", "/api/config/preview"),
    ("GET", "/api/config/public"),
    ("GET", "/api/config/schema"),
    ("GET", "/api/events"),
    ("POST", "/api/expr/eval"),
    ("GET", "/api/fs/dirs"),
    ("POST", "/api/fs/mkdir"),
    ("GET", "/api/groups"),
    ("POST", "/api/groups/{key}/delete"),
    ("POST", "/api/groups/{key}/pause"),
    ("POST", "/api/groups/{key}/reannounce"),
    ("POST", "/api/groups/{key}/resume"),
    ("GET", "/api/log"),
    ("POST", "/api/open-path"),
    ("GET", "/api/paths"),
    ("GET", "/api/search"),
    ("GET", "/api/speed/mode"),
    ("POST", "/api/speed/override"),
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
    ("POST", "/api/torrents/{hash}/super-seeding"),
    ("GET", "/api/torrents/{hash}/trackers"),
    ("POST", "/api/torrents/{hash}/trackers/add"),
    ("POST", "/api/torrents/{hash}/trackers/edit"),
    ("POST", "/api/torrents/{hash}/trackers/remove"),
    ("GET", "/api/traffic/history"),
    ("GET", "/newui"),
    ("GET", "/newui/{rest:path}"),
    ("GET", "/api/hr/status"),  # M4: HR 站点级状态快照(只读; 与 --hr-status 同一口径)
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
    """路由金清单守阵: 61 条 (method, path) 集合逐一钉死, 丢失/改名/方法变更即红

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
