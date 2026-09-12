"""test_web 测试计划: WEB UI 后端(FastAPI 鉴权/API/命令投递/设置读写)

## 测试计划(每个测试函数一条)
- test_api_requires_token: 无/错密钥访问 /api/* -> 401
- test_api_status_and_groups: 状态与分组快照读取(经注入的 manager)
- test_api_group_commands_enqueue: pause/resume/reannounce/delete 命令入队(key 编解码回原值)
- test_api_delete_with_files_flag: delete 命令透传 delete_files 标志
- test_config_raw_roundtrip: 配置原文读取/保存写回文件并投递热重载命令
- test_config_raw_invalid_rejected: 非法配置文本 -> 400 且不写回
"""
import json
import os
import tempfile
from unittest import mock

import pytest

from auto_qb.utils import decode_group_key, encode_group_key
from auto_qb.web import create_app

KEY = ("R:/seeds", ("a.mkv", "b.mkv"))


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
    )
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


def test_api_requires_token(web_env):
    """无/错密钥访问 /api/* -> 401"""
    mgr, client = web_env
    assert client.get("/api/status").status_code == 401
    assert client.get("/api/status", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.get("/api/status", headers={"Authorization": f"Bearer {mgr._web_token}"}).status_code == 200


def test_api_status_and_groups(web_env):
    """状态与分组快照读取: 徽章数据/组名/站点明细齐全"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
    status = client.get("/api/status", headers=auth).json()
    assert status["connected"] is True and status["torrents"] == 2
    data = client.get("/api/groups", headers=auth).json()
    assert len(data["groups"]) == 1
    g = data["groups"][0]
    assert g["name"] == "Show" and g["count"] == 2 and g["upspeed"] == 2048
    assert [m["site"] for m in g["members"]] == ["HHan", "M-Team"]


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


def test_config_raw_roundtrip(web_env):
    """配置原文读取/合法新文本保存: 写回 config 文件 + 热重载命令入队"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
    original = client.get("/api/config/raw", headers=auth).json()["content"]
    assert "qbittorrent" in original

    new_text = (
        "config:\n"
        "  qbittorrent:\n"
        "    host: h\n"
        "    port: 1\n"
        "    username: u\n"
        "    password: p\n"
        "  main_tick: 5s\n"
        "  trackers:\n"
        "    T1:\n"
        "      domains: [a.com]\n"
    )
    resp = client.put("/api/config/raw", headers=auth, json={"content": new_text})
    assert resp.status_code == 200, resp.text
    assert resp.json()["applied"] is True
    with open(mgr.config_path, encoding="utf-8") as f:
        assert "main_tick: 5s" in f.read(), "新配置应写回 config 文件"
    cmd, payload = mgr.web_commands.get_nowait()
    assert cmd == "reload_config" and payload["config"].main_tick == 5.0


def test_config_raw_invalid_rejected(web_env):
    """非法配置文本 -> 400, config 文件不被覆盖"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr._web_token}"}
    before = open(mgr.config_path, encoding="utf-8").read()
    resp = client.put("/api/config/raw", headers=auth, json={"content": "config:\n  main_tick: abc\n"})
    assert resp.status_code == 400
    assert open(mgr.config_path, encoding="utf-8").read() == before


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
        seeding_time=3600
    )
    t2 = FakeTorrent(
        hash="HB",
        name="Show",
        state="pausedUP",
        upspeed=1024,
        uploaded=2048,
        size=512**2,
        progress=1.0,
        seeding_time=3600
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
    assert g["upspeed"] == 2048 and g["uploaded"] == 4096 and g["size"] == 2 * 512**2
    assert [m["site"] for m in g["members"]] == ["Unknown", "Unknown"]
    assert g["members"][0]["kind"] == "seeding"
