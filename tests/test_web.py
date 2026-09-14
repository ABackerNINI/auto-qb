"""test_web 测试计划: WEB UI 后端(FastAPI 鉴权/API/命令投递/设置读写)

## 测试计划(每个测试函数一条)
- test_api_requires_token: 无/错密钥访问 /api/* -> 401
- test_api_status_and_groups: 状态与分组快照读取(经注入的 manager; status 含 version)
- test_static_assets_disable_heuristic_cache: 静态资源带 no-cache(/api 不受影响), 防升级后仍加载旧前端
- test_api_group_commands_enqueue: pause/resume/reannounce/delete 命令入队(key 编解码回原值)
- test_api_delete_with_files_flag: delete 命令透传 delete_files 标志
- test_api_cmd_result_endpoint: 命令端点返回 cmd_id; /api/cmd/{id} 查询回执(pending -> 结果)
- test_api_traffic_history_endpoint: /api/traffic/history 透出快照 history; 缺省空数组
- test_config_schema_endpoint: 图形化配置元数据端点(分组/插件/热重载级别)
- test_config_tree_roundtrip: 配置树读取/保存写回文件并投递热重载命令
- test_config_tree_invalid_rejected: 非法配置树 -> 400 且不写回
- test_config_tree_restart_field_fallback: R 级字段(data_dir)提交后被回退为磁盘旧值
- test_config_tree_requires_config_root: 缺少 config 根段 -> 400
- test_config_tree_preserves_comments: round-trip 写盘保留已有键的注释
- test_group_key_codec_roundtrip: 分组 key 编解码往返(含中文/多文件)
- test_build_group_view: 分组视图组装(组名/合计/成员站点/单种子大小与总大小/标签/分类/保存路径)
- test_build_search_index_files: 搜索索引构建(hash -> name+files), 单条文件拉取失败跳过该种子
- test_build_search_index_incremental_and_evict: 增量维护(不重拉已建条目/补拉新增/淘汰已删)
- test_build_search_index_budget_resumes: 限流分批构建, 未拉完保持脏, 续建至完成
- test_build_search_index_aborts_when_disconnected: qB 断连时中止构建且不写空索引
- test_search_torrents_name_match: 种子名匹配(即时/大小写不敏感)
- test_search_torrents_file_match: 文件列表匹配(依赖已建索引)
- test_search_torrents_building_triggers: 索引脏时 building=True 并投递构建命令
- test_api_search_endpoint: GET /api/search 转发与鉴权(含空查询)
- test_drain_web_commands_group_actions: 组级暂停/开始/汇报/删除命令执行并作用于整组 hash
- test_drain_web_commands_torrent_actions: 单种子命令作用于该 hash; 种子不在快照 -> 跳过(删除守阵)
- test_drain_web_commands_unknown_and_error_continues: 未知命令与执行异常只记日志, 不中断后续消费
- test_drain_web_commands_empty_queue: 队列为空直接返回(queue.Empty 分支)
- test_reannounce_confirm_success_and_timeout: 汇报确认跟踪 next_announce 重置 -> ok 回执; 超时 -> error 回执
- test_reannounce_confirm_group_aggregate: 组汇报按种子逐个确认, 部分失败聚合 error 带计数
- test_confirm_reannounce_result_matrix: 判定矩阵(updating/next_announce 重置/变 working=成功; not working+msg=失败; 其余 None)
- test_cmd_group_actions_skip_missing_group: 组 key 不存在/成员不在快照 -> 空 hashes 不调 API
- test_cmd_reload_config_delegates: reload_config 命令委托 apply_new_config
- test_ensure_group_view_rebuilds_when_dirty: 分组视图脏时重建(Web 请求侧兜底)/干净时复用引用
- test_ensure_group_state_versioning: 分组视图版本号: 首次重建自增, rid 一致时不回传 groups
- test_group_view_ver_seeded_from_start_time: 版本号以启动时间播种(进程重启不回落到旧值)
- test_api_state_rid_gate: /api/state 带 rid: 版本一致时 updated=False 且无 groups; 缺省/不匹配回传全量
- test_state_kind_maps_states: 状态语义分类映射(暂停态优先于下载/做种)
- test_apply_new_config_levels: 配置热重载按 L0/L1/L2/R 级别应用
- test_stop_web_server_releases_port_for_restart: 停止后服务线程真正退出, 同端口可再次监听(10048 回归守阵)
- test_apply_web_config_skips_restart_when_bind_unchanged: 监听身份未变 -> 不重启, 仅刷新密钥
- test_apply_web_config_toggle_enabled: web.enabled 热开关(关->开启动 / 开->关停止并清句柄)
- test_start_web_server_reports_failure_when_port_taken: 端口被占用 -> 句柄未就绪 + ERROR 日志(不再静默)
"""
import json
import logging
import os
import tempfile
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

    state_file = os.path.join(tmp_path, "state.json")
    config_file = os.path.join(tmp_path, "config.yml")
    with open(config_file, "w", encoding="utf-8") as f:
        f.write(config_text)
    web_cfg = SimpleNamespace(enabled=True, host="127.0.0.1", port=8080, token="")
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
        store=SimpleNamespace(groups=groups),
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
    )
    # 性能修复后 API 调用的替身方法: touch_web_client(心跳) / ensure_group_view(懒视图) /
    # ensure_group_state(带 rid 的增量状态)
    mgr.touch_web_client = lambda: setattr(mgr, "_web_last_seen", __import__("time").time())
    mgr.ensure_group_view = lambda: mgr._group_view

    def _ensure_group_state(rid):
        updated = rid != mgr._group_view_ver
        state = {"rid": mgr._group_view_ver, "updated": updated}
        if updated:
            state["groups"] = mgr._group_view
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

    症状: 升级程序后仍加载旧 app.js/style.css("改了但没变"), 本次开发中实际撞到。
    no-cache 仍允许存储, 但每次必须带 ETag 重新校验(未变走 304); /api 响应不受影响。
    """
    mgr, client = web_env
    for path in ("/", "/app.js", "/style.css", "/config_editor.js"):
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} 应可访问"
        assert resp.headers.get("cache-control") == "no-cache", f"{path} 应带 no-cache"
    api = client.get("/api/status", headers={"Authorization": f"Bearer {mgr._web_token}"})
    assert api.headers.get("cache-control") != "no-cache", "/api 响应不应被静态策略影响"


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
        "history": [{"date": "2026-09-14", "up": 1024, "down": 2048}],
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
    from auto_qb import qbmanager
    from helpers import FakeClient, FakeTorrent, _fake_file, make_manager, seed_store

    monkeypatch.setattr(qbmanager, "SEARCH_INDEX_BUILD_BUDGET", 1)
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
        # 同版本再次请求: 不回传 groups
        again = mgr.ensure_group_state(rid=state["rid"])
        assert again["updated"] is False
        assert again["rid"] == state["rid"]
        assert "groups" not in again
        # 视图变化后版本自增, 旧 rid 失效 -> 重新回传
        mgr._group_view_dirty = True
        bumped = mgr.ensure_group_state(rid=state["rid"])
        assert bumped["updated"] is True
        assert bumped["rid"] == state["rid"] + 1
        assert "groups" in bumped


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
