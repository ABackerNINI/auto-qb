"""test_web 测试计划: WEB UI 后端(FastAPI 鉴权/API/命令投递/设置读写)

## 测试计划(每个测试函数一条)
- test_api_requires_token: 无/错密钥访问 /api/* -> 401
- test_config_public_endpoint_no_auth: 公开端点 /api/config/public 免 token 只读本机免鉴权标志(不含机密)
- test_skip_local_verify_loopback_bypass: web.skip_local_verify=true 时本机连接免密钥放行(提示日志 **INFO 级**、**每进程只记一次**), 对外/远端仍强制鉴权
- test_skip_local_verify_default_off: 默认关闭(保守), 本机连接也不免鉴权
- test_api_status_and_groups: 状态与分组快照读取(经注入的 manager; status 含 version)
- test_static_assets_disable_heuristic_cache: 静态资源带 no-cache(/api 不受影响), 防升级后仍加载旧前端(UI 目录化路径: atlas/prism/shared)
- test_ui_root_and_legacy_newui_redirect: / -> 307 /atlas/; 旧 /newui/* 书签 -> 307 /prism/*
- test_frontend_static_bundle_health: 前端静态资源静态守阵(冲突标记/注释孤儿续行/node --check 语法校验/CSS 规则漏闭合/<transition> 吞弹窗/静态引用缺失/追剧视图集成员取 hash 未走 memberHashesOf/STATE_RANK 与后端 _SHOW_STATE_RANK 漂移 —— 均为"pytest 全绿但界面废掉"的故障形态)
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
- test_search_torrents_building_triggers: 索引脏时 building=True 并投递构建命令
- test_api_search_endpoint: GET /api/search 转发与鉴权(含空查询)
- test_api_paths_endpoint: GET /api/paths 已知目录聚合(组 save_path + 现有种子 save_path 归一去重排序; 空路径跳过; 无副作用; 鉴权)
- test_api_open_path_endpoint: POST /api/open-path 打开目标文件夹(FX-14 + R10-10) —— 目录/单文件(select=True 定位选中)、回退 save_path、组键首元、未知目标 404、kind 非法 400、客户端传 path 被忽略、无副作用、鉴权
- test_api_fs_dirs_endpoint: GET /api/fs/dirs 目录浏览(R10-11) —— 首屏允许根/只列目录(排除文件与越界符号链接)/上溯到根为止/.. 穿越与白名单外 403/不存在 404/无白名单空返回/鉴权/无副作用
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
- test_api_state_status_carries_server_state: status.server(state)恒回传不受 rid 门控(状态栏与行数据同源同轮)
- test_api_category_tag_endpoints: 分类/标签 CRUD 端点(入队与 400 校验)
- test_category_tag_commands_execute: 分类/标签命令执行(QbApi 封装 + 缓存失效)
- test_api_speed_mode_and_override: /api/speed/mode 曲线/停用两形态 + /api/speed/override 落 transfer 端点
- test_api_speed_mode_curve_config_disabled: 曲线存在但 enabled=False -> curve_enabled=False(快照之上叠加配置判定)
- test_api_add_torrent_endpoint: /api/torrents/add multipart(bytes 内存直传/选项透传/空来源 400)
- test_api_export_endpoint: /api/torrents/{hash}/export 字节流与 disposition(404/503); 非 ASCII 种子名走 filename*(回归: 头 latin-1 编码崩)
- test_content_disposition_encoding: content_disposition 头值纯 ASCII + filename* 百分号编码 + 清洗/回退
- test_api_log_endpoint: /api/log tail 与 level 过滤(未配置空)
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
- test_stop_web_server_releases_port_for_restart: 停止后服务线程真正退出, 同端口可再次监听(10048 回归守阵)
- test_apply_web_config_skips_restart_when_bind_unchanged: 监听身份未变 -> 不重启, 仅刷新密钥
- test_apply_web_config_toggle_enabled: web.enabled 热开关(关->开启动 / 开->关停止并清句柄)
- test_start_web_server_reports_failure_when_port_taken: 端口被占用 -> 句柄未就绪 + ERROR 日志(不再静默)
"""
import base64
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
from types import SimpleNamespace
from unittest import mock

import pytest

from auto_qb import __version__
from auto_qb.utils import decode_group_key, encode_group_key
from auto_qb.web import create_app

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
    from auto_qb.qbmanager import QbManager

    mgr._hr_view_fields = QbManager._hr_view_fields
    mgr._wake_calls = wake_calls  # 供端点测试断言"投递命令是否唤醒主循环"
    # 性能修复后 API 调用的替身方法: touch_web_client(心跳) / ensure_group_view(懒视图) /
    # ensure_group_state(带 rid 的增量状态)
    mgr.touch_web_client = lambda: setattr(mgr, "_web_last_seen", __import__("time").time())
    mgr.ensure_group_view = lambda: mgr._group_view

    def _ensure_group_state(rid, view=None):
        # 与真实实现同形: 默认回全部; P1-1 带 view 时只回该视图的数组
        from auto_qb.mixins.web_view import VIEW_ARRAYS

        updated = rid != mgr._group_view_ver
        state = {"rid": mgr._group_view_ver, "updated": updated}
        if updated:
            arrays = {
                "groups": mgr._group_view,
                "singles": [],  # 与真实 ensure_group_state 同形: singles 随 groups 同门控回传
                "shows": {"list": [], "unrecognized": []},
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

    from auto_qb.web import create_app, ensure_web_token

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

    from auto_qb.web import create_app

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

    from auto_qb.web import create_app

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
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "auto_qb", "web_ui", "static"
)

# CSS 容器型 at-rule: "开块后下一行是嵌套规则"属正常写法, 不参与"漏闭合"判定
_CSS_CONTAINER_AT = ("@media", "@supports", "@keyframes", "@container", "@layer", "@scope")
# 追剧视图的"集成员"两种写法(e.members / ep.members) —— 取 hash 必须经 memberHashesOf 归一
_EP_MEMBERS_RE = re.compile(r"\b(?:ep|e)\.members\b")


def _scan_css_blocks(path, rel, problems):
    """CSS 规则块守阵: 顶层规则开了块却没闭合, 而下一非空行又开了新规则 -> 漏写 `; }`

    (2026-09-17 实测: prism/css/views.css 有一条 `.ce-subcard .ce-field { … padding: 7px 0` 漏了
    `; }`, 浏览器把其后约 200 条规则整段当作"未结束的声明块"丢弃 —— 棱镜大半样式静默消失而
    pytest 全绿。注意**全文件花括号计数是配平的**(别处有多余 `}`), 只数括号查不出来。)
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


def _scan_js_syntax_with_node(js_files, problems):
    """有 node 时用 `node --check` 对前端 JS 做**真**语法校验(2026-09-17 起本机已装 node)

    这是启发式扫描(注释孤儿续行等)之上的一道硬闸: 任何语法错误都能以 `文件:行` 形式报出。
    无 node(未装的机器/精简 CI)时**静默跳过**本项 —— 不引入 pytest skip(基线是 0 skipped),
    启发式扫描仍在拦最常见的那类损坏。
    """
    node = shutil.which("node")
    if not node:
        return
    for path, rel in js_files:
        proc = subprocess.run([node, "--check", path], capture_output=True, text=True)
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout).strip().splitlines()
            problems.append(f"{rel} node --check 报语法错误: {detail[0] if detail else 'unknown'}")


def _scan_episode_member_hashes(path, rel, problems):
    """追剧视图"集成员 -> hash"守阵 (2026-09-19 实测事故)

    后端 shows 视图的 `members` 是 **hash 数组**, 而前端 `decoratedShows` 会把它换成**成员对象**
    (带 hit 标记, 供行内渲染/筛选)。菜单与命令只认 hash —— 一旦把对象当 hash 传出去, 拼进
    URL/JSON 时字符串化成 `[object Object]` ⇒ 后端查不到该 hash ⇒ 404「种子不存在」:
    整集/整剧的 开始/暂停/强制汇报/打开目标文件夹/删除 全线哑火(单种子菜单传的是 `member.hash`,
    不受影响 —— "种子右键正常、剧/集右键失败"就是这形状)。故凡是"从集成员取 hash"的地方
    一律走 `memberHashesOf`(两形态都收), 这里只做静态拦截。
    """
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    for i, line in enumerate(lines, 1):
        if not _EP_MEMBERS_RE.search(line):
            continue
        wants_hash = "hashes" in line or ".hash" in line or "for (const h of" in line
        if wants_hash and "memberHashesOf(" not in line:
            problems.append(
                f"{rel}:{i} 集成员取 hash 未走 memberHashesOf"
                "(members 在前端已是对象 -> 传出去会变成 [object Object], 后端 404「种子不存在」)"
            )


def _scan_state_rank(path, rel, problems):
    """状态优先级表守阵: 前端 `STATE_RANK` 必须与后端 `_SHOW_STATE_RANK` 逐项一致(2026-09-19)

    两表是**同一概念**("一组/一集种子该显示成什么状态")的两份实现:
    前端那份决定辅种页组行取哪个成员状态着色(`decoratedGroups.status.primary`),
    后端那份决定追剧页集行的 `e.state`。漂移的后果有两层 ——
    ① 同一批种子在辅种页与追剧页显示成**不同颜色**(用户没法解释, 只会觉得"颜色乱");
    ② 乐观 UI: 前端按自己的表算出"点击后的颜色", 下一轮回执却按后端的表算真值 ⇒ 颜色弹回。
    实测曾漂移两处({downloading,checking} 与 {paused,seeding} 两组取值相反), 人眼不可能发现,
    故机械比对(改一边必须改另一边 —— 这正是本守阵要逼出来的动作)。
    """
    from auto_qb.mixins.web_view import _SHOW_STATE_RANK

    with open(path, encoding="utf-8") as f:
        text = f.read()
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


def _scan_pending_settle(path, rel, problems):
    """乐观 UI「撤下」守阵(2026-09-19, 与主线 32f531d / 12657ee 同一族缺陷的第二道锁)

    背景: 「点击 → 行恢复正常」曾实测 3785~5178ms, 根因是 pending 只有 3s 常量兜底一个出口 ——
    systemPatterns 明写的「真值匹配即清」**从未实现过**; 而且这个兜底还只在 refresh() 里被顺带
    求值 ⇒ 撤下 = 3000ms + 等到下一次 /api/state。真机连报三次同一现象, 前三次修复全只动"贴上",
    因为没人量过"撤下"。

    主线修法落地后有三处**极易被改回去/写反**的地方, 本守阵逐条钉住:
      ① `_snapshotTruth(state)` 必须在 `reapplyPending()` **之前** —— 快照要的是服务端原始值;
         挪到之后就变成"行上的补丁值 vs 补丁值", 恒真 ⇒ pending 一瞬间就清(实测 28ms),
         而且冒烟里「落回的是真值」那条**照样 PASS**(补丁值还留在行上, 看着就像真值)。
      ② 判定必须走 `_optimisticSettled`(比真值快照)而不是"拿行上的当前值比" —— 同上;
      ③ 回执后必须调 `_pullTruthAfterCmd`, 否则真值只能等下一轮轮询(1.5/2/3s 分档)。
    """
    with open(path, encoding="utf-8") as f:
        text = f.read()

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
        problems.append(f"{rel} 找不到 _optimisticSettled 的调用点 —— 真值对齐判定被绕过, 撤下退回 3s 兜底")
    if "this._pullTruthAfterCmd(" not in text:
        problems.append(f"{rel} 找不到 _pullTruthAfterCmd 的调用点 —— 回执后不拉真值, 撤下要等下一轮轮询")


def _scan_frontend_assets():
    """扫描 web_ui/static 返回问题清单(空 = 健康)

    检查项(均为"整页白屏 / 整块功能静默失效"级故障, 且 Python 侧测试天然看不见):
    1. 合并冲突标记残留(`<<<<<<<` / `>>>>>>>` / 单独一行 `=======`) —— 语法错误;
    2. JS 里"注释已闭合却仍留续行"(上一非空行以 `*/` 结尾, 本行又以 `*` 起头) ——
       整包 SyntaxError, app.js 不执行, Vue 从不 mount, `v-cloak` 的 #app 恒 display:none;
    3. JS 语法硬校验: 有 node 时跑 `node --check`(见 _scan_js_syntax_with_node);
    4. CSS 规则块漏闭合(浏览器会把其后规则整段当声明丢弃) —— 见 _scan_css_blocks;
    5. 模板 `<transition>` 不配对 / 把弹窗包进 `<transition>`(只渲染首子节点 -> 弹窗全丢);
    6. 模板/样式里以 `/` 开头的 src|href 引用, 在 static 根下必须真实存在(防改名/漏档 404);
    7. 追剧视图"集成员 -> hash"必须走 `memberHashesOf`(见 _scan_episode_member_hashes);
    8. `STATE_RANK` 必须与后端 `_SHOW_STATE_RANK` 逐项一致(见 _scan_state_rank) ——
       两表分别决定"辅种页组行"与"追剧页集行"的颜色, 漂移的后果是同一批种子两页不同色;
    9. 乐观 UI 的**撤下**路径: 真值快照必须早于补丁重贴、判定必须走 `_optimisticSettled`、
       回执后必须调 `_pullTruthAfterCmd`(见 _scan_pending_settle) —— 任一被绕过, 撤下就退回
       3s 常量兜底(真机连报三次的那条), 或判定恒真导致失败路径留假状态(红线)。
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
                    if name == "app.js":
                        _scan_episode_member_hashes(path, rel, problems)
                        _scan_state_rank(path, rel, problems)
                        _scan_pending_settle(path, rel, problems)
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
        "basic", "logging", "web", "notify", "maintenance", "speed", "trackers", "rules"
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
    from auto_qb.web import ensure_web_token

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
    from auto_qb.mixins import web_view
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
    from auto_qb.mixins import web_view
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
    with mock.patch("auto_qb.web.open_path") as spy:
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
    seed_store(
        mgr, [
            FakeTorrent(hash="HA", name="Show", save_path=r"R:\Downloads"),
            FakeTorrent(hash="HB", name="Show", save_path=r"R:\Downloads"),
        ]
    )
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
        # 改种子状态的命令(RESYNC)回执**推迟到补刷新之后** —— 这是 2026-09-20 的修复:
        # 原写法在补刷新**之前**就写 ok ⇒ 前端"拿到回执立刻 refresh"取到的一定是旧快照,
        # 第一次拉取 100% 扑空 ⇒ 大库上就是"点了要 2 秒才恢复正常"(真机撤下实测 1998ms)。
        assert "c1" not in mgr._web_results, "recheck 属 RESYNC 命令, drain 阶段不应就写回执"
        # run() 在补刷新之后无条件落回执(幂等; 漏调会让前端 waitCmd 干等 40s)
        mgr._flush_deferred_receipts()
        assert mgr._flush_deferred_receipts() is None, "重复 flush 必须是安全的空操作"
        # 全部命令回执 ok
        assert all(mgr._web_results[f"c{i}"]["status"] == "ok" for i in range(1, 14)), mgr._web_results
        # 回执附带真值: 前端据此就地撤下乐观态, 不必再拉一次全量 /api/state
        assert mgr._web_results["c1"].get("truth"), "RESYNC 命令的回执应带真值({hash: {kind}})"
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
    from auto_qb.qbmanager import QbManager

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
        "/api/state?view=torrent", "/api/state", "/api/groups",
        # 注: /api/config/schema **故意不在**清单里 —— 它的载荷含 dataclass(Group/Field/Plugin),
        # 必须保留 FastAPI 的 jsonable_encoder 做转换(直返会 500, 见 web.py 该端点的注释)。
        "/api/search?q=Show",
        "/api/torrents/HA", "/api/torrents/HA/trackers",
        "/api/torrents/HA/files", "/api/torrents/HA/peers",
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
    from auto_qb.qbmanager import QbManager
    from helpers import FakeTorrent

    assert QbManager._state_kind(FakeTorrent(hash="H", name="t", state=state)) == kind


def test_apply_new_config_levels(monkeypatch):
    """apply_new_config: 按影响级别应用 —— L0 仅换配置; L1 重挂日志/通知+重连+web 重启;
    L2 重建任务队列/规则并抑制事件一轮; R 仅提示重启不应用"""
    import logging as std_logging

    from auto_qb import qbmanager as qbm
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
        mgr.config = SimpleNamespace(web=_web_stub(port=38080))  # 旧配置(复现真实新旧对比)
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

        monkeypatch.setattr("auto_qb.web.stop_web_server", _fake_stop)
        monkeypatch.setattr("auto_qb.web.start_web_server", _fake_start)
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


def test_stop_web_server_releases_port_for_restart(tmp_path):
    """回归守阵(2026-09-14): 热重载重启 WEB 服务器必须先等旧服务线程退出

    只 stop()(置 should_exit)就立刻启新服务时, 旧服务尚未关闭监听套接字 ——
    新服务 bind 报 `[Errno 10048] 通常每个套接字地址只允许使用一次`, 保存配置后 WEB UI 失联。
    本测试用真实 uvicorn 复现该时序: 停止后同端口必须能再次监听。
    """
    from auto_qb.web import start_web_server, stop_web_server

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
        monkeypatch.setattr("auto_qb.web.start_web_server", mock.MagicMock())
        monkeypatch.setattr("auto_qb.web.stop_web_server", mock.MagicMock())

        mgr._apply_web_config(_web_stub(port=8080, token="旧密钥"))

        from auto_qb.web import start_web_server, stop_web_server

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

    from auto_qb.web import start_web_server, stop_web_server

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
    from auto_qb.web import content_disposition

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


def test_api_log_endpoint(web_env):
    """/api/log: 自身日志 tail + [LEVEL] 过滤; 文件未配置返回空"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
    log_path = os.path.join(mgr.data_dir, "auto-qb.log")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("2026-09-16 01:00:00 [INFO] 启动完成\n")
        f.write("2026-09-16 01:00:05 [WARNING] 连接重试\n")
        f.write("2026-09-16 01:00:10 [ERROR] 校验失败\n")
    mgr.config.logging.file = log_path
    data = client.get("/api/log?lines=10", headers=auth).json()
    assert len(data["lines"]) == 3 and data["file"] == log_path
    data = client.get("/api/log?lines=10&level=warning", headers=auth).json()
    assert len(data["lines"]) == 1 and "WARNING" in data["lines"][0]
    mgr.config.logging.file = ""
    assert client.get("/api/log", headers=auth).json() == {"lines": [], "file": ""}


def test_apply_web_config_toggle_enabled(monkeypatch):
    """web.enabled 热开关: 关 -> 开(启动服务器); 开 -> 关(停止并清空句柄)"""
    from helpers import make_manager

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        started = mock.MagicMock(return_value="新句柄")
        stopped = mock.MagicMock()
        monkeypatch.setattr("auto_qb.web.start_web_server", started)
        monkeypatch.setattr("auto_qb.web.stop_web_server", stopped)

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

    from auto_qb.mixins.web_commands import SELF_POSTED_COMMANDS

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
    mgr._wake_calls.clear()
    assert client.post("/api/torrents/HA/recheck", headers=auth).status_code == 200
    assert len(mgr._wake_calls) == 1, f"用户命令投递后应唤醒主循环, 实际 {len(mgr._wake_calls)} 次"

    # 静态反向守卫: Web 侧所有 self-posted 的 cmd 名都必须登记, 否则下次新增就会自激
    src = open(
        os.path.join(os.path.dirname(__file__), "..", "src", "auto_qb", "mixins", "web_view.py"), encoding="utf-8"
    ).read()
    posted = set(re.findall(r'web_commands\.put\(\(\s*"([^"]+)"', src))
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

    from auto_qb.mixins.web_commands import CMD_SLOW_MS

    class _T:
        """只需要 _log_cmd_timing 用到的两个属性"""
        _web_results = {}
        _web_write_seq = 0

        from auto_qb.mixins.web_commands import WebCommandsMixin as _M

        _log_cmd_timing = _M._log_cmd_timing

    t = _T()
    # ① 慢 -> WARNING, 且带归因提示(排队/执行各自指向不同的后端原因)
    with caplog.at_level(logging.DEBUG):
        caplog.clear()
        t._log_cmd_timing("pause_torrent", {"wait_ms": 1800.0, "exec_ms": 2.0})
    recs = [r for r in caplog.records if "[cmd]" in r.getMessage()]
    assert recs, "慢命令没有落日志 —— 真机无法排查"
    assert recs[-1].levelno == logging.WARNING, f"慢命令应为 WARNING, 实际 {recs[-1].levelname}"
    assert "1800" in recs[-1].getMessage()

    # ② 快 -> INFO(有记录但不过载)
    with caplog.at_level(logging.INFO):
        caplog.clear()
        t._log_cmd_timing("pause_torrent", {"wait_ms": 1.0, "exec_ms": 3.0})
    recs = [r for r in caplog.records if "[cmd]" in r.getMessage()]
    assert recs and recs[-1].levelno == logging.INFO

    # ③ 自投递命令(建索引等)频次高 -> 压到 DEBUG, 不许进常规日志
    with caplog.at_level(logging.DEBUG):
        caplog.clear()
        t._log_cmd_timing("build_search_index", {"wait_ms": 900.0, "exec_ms": 900.0})
    recs = [r for r in caplog.records if "[cmd]" in r.getMessage()]
    assert recs and recs[-1].levelno == logging.DEBUG, "自投递命令会刷屏, 必须压到 DEBUG"

    assert CMD_SLOW_MS > 0
