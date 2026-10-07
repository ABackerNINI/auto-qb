"""test_web_views_reload 测试计划: Web 视图与配置热重载

## 测试计划(每个测试函数一条)
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
"""
import errno
import json
import logging
import os
import tempfile
from types import SimpleNamespace
from unittest import mock

import pytest

from auto_qb import __version__
from auto_qb.config.models import HrCheckConfig
from auto_qb.webui import create_app

from webui_helpers import _web_stub, _make_web_manager, _make_grouped_manager


def _free_port() -> int:
    """取一个本机空闲端口(先绑 0 再释放; 用于真实起停 WEB 服务器的测试)"""
    import socket

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


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
