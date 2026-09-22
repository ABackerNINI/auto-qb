"""test_local_qb_service 测试计划: 本地假 qB 服务(真实 qbittorrentapi + requests 栈)集成测试

单元替身(FakeClient)在进程内直接返回 dict, 绕过了真实 HTTP 栈 —— 因此
"requests Session 的 trust_env 是否真的生效""库在首次请求时重建 Session 会不会丢掉我们的设置"
这类问题它永远暴露不出来(2026-09-14 的 trust_env 失效 bug 正是如此)。本文件用 `helpers.FakeQbServer`
(标准库 http.server 后台线程 + 复用 FakeClient 语义)驱动**真实** Client 走完整往返。

## 测试计划(每个测试函数一条)
- test_fake_server_sanity_sync_incremental: 假服务自检: 登录可用, rid 增量语义与真机一致
- test_connect_keeps_env_lookup_disabled_after_real_request: 真实请求(含库重建 Session)后 trust_env 仍为 False
- test_local_request_skips_env_and_netrc_lookup: 本地客户端请求不解析环境代理/~/.netrc
- test_plain_client_still_resolves_env_and_netrc: 对照组: 原生 Client 同流程确实会解析(证明上一测试有区分力)
- test_connect_and_refresh_over_real_http: 端到端: connect + 一次 _refresh_torrents 真实拉取 sync 填充 store
- test_fake_server_files_endpoint_serializes_objects: 假服务 torrents/files 必须回 JSON 可序列化数组(真机语义)
- test_main_loop_throttled_by_main_tick: 节流回归守卫: 非托管模式主循环 tick 频率受 main_tick 约束
"""
import os
import time
from unittest import mock

from qbittorrentapi import Client

from auto_qb.config import QbittorrentConfig
from auto_qb.core.qbclient import LocalQbClient, _new_client
from helpers import FakeQbServer, FakeTorrent, make_manager


def _cfg(srv) -> QbittorrentConfig:
    """指向假服务的 qB 配置"""
    return QbittorrentConfig(host="127.0.0.1", port=srv.port, username="u", password="p")


def _make_manager_for(srv, tmp_path, **kw):
    """构造指向假服务的 manager(state 落在 pytest 临时目录, 不触碰生产数据)"""
    mgr = make_manager(os.path.join(tmp_path, "state.json"), **kw)
    mgr.config.qbittorrent = _cfg(srv)
    return mgr


def test_fake_server_sanity_sync_incremental():
    """假服务自检: 登录可用; rid 增量语义与真机一致(全量 -> 无变化省略 -> 只回变化字段)"""
    with FakeQbServer() as srv:
        srv.client.torrents["a" * 40] = FakeTorrent(hash="a" * 40, state="uploading")
        client = _new_client(_cfg(srv))
        client.auth_log_in()
        first = client.sync_maindata(rid=0)
        assert first["full_update"] is True
        assert set(first["torrents"]) == {"a" * 40}
        # 对齐真机: sync 响应的 hash 是 torrents 字典的键, 值内不含 hash
        assert "hash" not in first["torrents"]["a" * 40]
        second = client.sync_maindata(rid=first["rid"])
        assert second["full_update"] is False
        assert "torrents" not in second and "torrents_removed" not in second  # 无变化即省略
        srv.client.torrents["a" * 40].upspeed = 123
        third = client.sync_maindata(rid=second["rid"])
        assert third["torrents"]["a" * 40] == {"upspeed": 123}


def test_connect_keeps_env_lookup_disabled_after_real_request(tmp_path):
    """真实 HTTP 往返后 trust_env 仍为 False

    connect() 内部就会发请求(login + 协议探测 HEAD), 而库在首次请求的
    `build_base_url()` 中调用 `_trigger_session_initialization()` 重建 Session ——
    旧实现(连上后给 `client._session.trust_env` 赋 False)正是在这里被静默清掉。
    """
    with FakeQbServer() as srv:
        mgr = _make_manager_for(srv, tmp_path)
        assert mgr.connect() is True
        assert type(mgr.client) is LocalQbClient
        assert mgr.client._session.trust_env is False, "connect 内已发过真实请求, 此处仍须为 False"
        mgr.api.torrents_info()  # 再发一次真实请求
        assert mgr.client._session.trust_env is False
        assert srv.hits("auth/login") >= 1


def test_local_request_skips_env_and_netrc_lookup():
    """本地客户端发请求时不解析环境代理与 ~/.netrc(每次请求的固定开销)"""
    with FakeQbServer() as srv:
        client = _new_client(_cfg(srv))
        with mock.patch("requests.sessions.get_environ_proxies", return_value={}) as env, \
                mock.patch("requests.sessions.get_netrc_auth", return_value=None) as netrc:
            client.auth_log_in()
        assert env.call_count == 0, "本地连接不应解析环境代理"
        assert netrc.call_count == 0, "本地连接不应读取 ~/.netrc"


def test_plain_client_still_resolves_env_and_netrc():
    """对照组: 原生 Client(远程语义)走同一流程确实会解析环境代理与 netrc —— 证明上一测试有区分力"""
    with FakeQbServer() as srv:
        client = Client(host=f"http://127.0.0.1:{srv.port}", username="u", password="p")
        with mock.patch("requests.sessions.get_environ_proxies", return_value={}) as env, \
                mock.patch("requests.sessions.get_netrc_auth", return_value=None) as netrc:
            client.auth_log_in()
        assert env.call_count >= 1, "原生 Client 应解析环境代理(对照组失效说明测试无区分力)"
        assert netrc.call_count >= 1, "原生 Client 应读取 ~/.netrc(对照组失效说明测试无区分力)"


def test_connect_and_refresh_over_real_http(tmp_path):
    """端到端: connect + 一次 _refresh_torrents 经真实 HTTP 拉取 sync 并填充 store"""
    with FakeQbServer() as srv:
        srv.client.torrents["a" * 40] = FakeTorrent(hash="a" * 40, state="uploading")
        mgr = _make_manager_for(srv, tmp_path)
        assert mgr.connect() is True
        mgr._refresh_torrents(dry_run=True)
        assert list(mgr.store.by_hash) == ["a" * 40]
        assert mgr.store.get("a" * 40).state == "uploading"
        assert srv.hits("sync/maindata") == 1, "一次 tick 只应拉一次 sync/maindata"


def test_fake_server_files_endpoint_serializes_objects(tmp_path):
    """假服务 torrents/files 必须返回真机语义(JSON 对象数组)

    回归背景(2026-09-14 实测): 替身文件项是 SimpleNamespace, 直接 json.dumps 抛 TypeError ->
    http.server 无响应关闭连接 -> 客户端报 APIConnectionError。分组(_assign_new_torrent)
    以真实 HTTP 拉文件列表, 会被这个替身缺陷整体打断(表现为"辅种分组永远为空"),
    因此这里用真实 Client 走一次完整往返守住它。
    """
    from helpers import _fake_file

    with FakeQbServer() as srv:
        srv.client.files_map["a" * 40] = [_fake_file("Show.S01E01.mkv", 1024)]
        client = _new_client(_cfg(srv))
        client.auth_log_in()
        files = client.torrents_files("a" * 40)
        assert len(files) == 1
        assert files[0]["name"] == "Show.S01E01.mkv" and files[0]["size"] == 1024


def test_main_loop_throttled_by_main_tick(tmp_path):
    """节流回归守卫(非托管模式 + 真实 HTTP): main_tick=0.2s 下 0.9s 内 tick 应约 5 次

    必须用**非托管模式**(CLI 默认, 不传 stop_event)才有区分力: bug 现场是
    `stop_event is not None and stop_event.wait(...)` 被 `and` 短路, 而托管模式里 wait 会
    真实阻塞(看起来"正常")。退出只能靠 KeyboardInterrupt(等价 Ctrl+C), 故在 tick 包装层按
    时间/次数抛出让主线程退出。
    修复前: 非托管模式满速空转, 0.9s 内 tick 达数百次; 修复后应约 0.9/main_tick ≈ 5 次。
    """
    with FakeQbServer() as srv:
        mgr = _make_manager_for(srv, tmp_path)
        # 两条线同拍(分层节拍后若不同拍, 循环按 min(sync_interval, main_tick) 唤醒而
        # _tick 只在两线同时到期时才走到, 本用例的"每轮一次 sync"假设不再成立)
        mgr.config.main_tick = 0.2
        mgr.config.sync_interval = 0.2
        start = time.monotonic()
        real_tick = mgr._tick

        def tick(dry_run, force=False):
            real_tick(dry_run)
            if time.monotonic() - start > 0.9:
                raise KeyboardInterrupt  # 非托管模式唯一退出途径(Ctrl+C); 每轮只发一次真实 HTTP

        mgr._tick = tick
        mgr.run(dry_run=True)
        elapsed = time.monotonic() - start
        hits = srv.hits("sync/maindata")
        assert elapsed >= 0.9, f"主循环应跑满观测窗口, 实际 {elapsed:.2f}s"
        assert hits <= 10, f"main_tick=0.2s 下 {elapsed:.2f}s 内 tick 应约 5 次(节流生效), 实际 {hits} —— 主循环在空转"
        assert hits >= 2, f"节流不应把主循环拖到几乎不执行, 实际 {hits}"
