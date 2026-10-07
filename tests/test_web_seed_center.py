"""test_web_seed_center 测试计划: 种子中心视图 (种子页 / 详情抽屉 / 全局统计)

## 测试计划(每个测试函数一条)
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
"""
import logging
import os
import re
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from auto_qb.infra.utils import mask_tracker_url
from auto_qb.webui.runtime import CMD_SLOW_MS, WebUIRuntime

from webui_helpers import STATIC_ROOT, _iter_api_routes

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
