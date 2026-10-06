"""test_webui_delta 测试计划: WebUI 增量时间线(plan 26-10-07-0414 S2, 服务端内部状态)

被测面: WebUIRuntime 的时间线落代(_fold_delta_pending_locked)/store 增量排空与脏行键推导
(_drain_delta_locked)/full 降级理由集合(R11 五源)与 views._build_group_view 的构建期交叉键
回传。不接端点(S3)、不动前端(S4); show 桶本步恒空。

## 测试计划(每个测试函数一条)
- test_timeline_appends_per_publish_and_truncates: 时间线落代/截断 —— 每次发布恰追加一条目(ver 与 group_view_ver 对齐, 本仓 ver 单调), 条目形状 = ver/full/upsert/removed 四键分 torrent/group/show 三桶; 45 次发布后 maxlen=40 截断(最旧 5 条被挤掉)
- test_same_tick_upsert_removed_cancel: 交叉抵消(R5) —— 同拍同视图 upsert/removed 同键落代前两清(H3 同拍增删净零), 异键照常保留; show 桶恒空
- test_gate_skipped_round_keys_survive_to_next_gen: 门控跳拍累积(R4) —— 上一版未被取走时 flush 只排空累积不落代, 键集(含组键)并入下一代条目不丢
- test_full_downgrade_sources_matrix: 五个降级源矩阵(R11) —— config_reload(mark_dirty full=True)/hr_revision(flush 判定点)/shows_pending(归位转换拍)/cross_group(构建期键集增删, 走真 _build_group_view 回传)各自触发 full 代(full 条目键集清空 + 累积器与理由一并清空; hr/cross 均有"下一拍不再 full"的对照); 进程重启 = ver 时间播种 + 时间线/累积器为空, 旧客户端 rid 必然窗外或 rid>ver 全量(R10, 无需显式标记)
- test_group_removed_key_unresolvable_full: 组行 removed 键推导(R11) —— removed hash 组键查得到且组仍在 -> 组键进 upsert; 组已解散 -> 组键进 removed; 查不到(与"从未归组"不可区分) -> 本代 full 且键集清空
- test_error_reason_refresh_row_level_upsert: 错误原因预取按行级归约(S2 补丁, 源标签 "tracker_error_refresh") —— 走真 refresh_error_reasons 改写 tracker_error_msg, 仅原因刷新、store 零增量 -> 受影响行进 torrent/group 桶 upsert 且该代不 full; 门控跳拍键集暂存不丢(R4); 无变化轮不登记
"""
import time
from types import SimpleNamespace

from auto_qb.core.qbapi import QbApi
from auto_qb.torrents import TorrentStore
from auto_qb.webui import WebUIRuntime
from auto_qb.webui.views import WebviewMixin

from helpers import FakeClient, FakeTorrent

# ---------- 替身与驱动 ----------


class _ViewHost(WebviewMixin):
    """views 构建器**真跑**的最小宿主: 纯读 store/web(构建器是纯读, 见 WebviewMixin 模块头),
    让 cross 键集的构建期回传(note_cross_keys)走真实 _build_group_view 接线"""
    def __init__(self, store):
        self.store = store
        self.web = None  # _delta_runtime 里回填
        self.client = None

    def wake(self):  # _build_shows_view 的 post_command 路径兜底(本文件用例不会触发)
        pass


def _make_store(*hashes, state: str = "stalledUP") -> TorrentStore:
    """真实 TorrentStore 装库(首轮全量, FakeClient/FakeTorrent 范式同 test_sync);
    随后清掉装库轮的 S1 快照与 view_changed —— 基线不进被测时间线窗口, 各用例从干净基线驱动"""
    client = FakeClient()
    for h in hashes:
        # 剧集形命名: parse_release 解析为 episode(带 key)—— 不触发 _build_shows_view 的
        # 文件兑底 pending 标记(名称解析不出剧键时构建器会 mark_shows_pending(True),
        # 与 c) 场景的转换拍断言互相干扰)
        client.torrents[h] = FakeTorrent(hash=h, name=f"Show.{h}.S01E01.720p.x264-GRP", state=state)
    store = TorrentStore(client)
    store.apply_sync(QbApi(client, store))
    store.last_added = []
    store.last_removed = []
    store.delta_fields = {}
    store.consume_view_changed()
    return store


def _delta_runtime(store) -> WebUIRuntime:
    host = _ViewHost(store)
    rt = WebUIRuntime(host)
    host.web = rt
    rt.touch()  # Web 活跃: 门控放行(is_active 依赖 last_seen 心跳)
    return rt


def _publish(rt) -> dict:
    """驱动一轮 flush 并落代(清 pending_ver 模拟客户端取走上一版), 回本代条目"""
    rt.pending_ver = None
    rt.flush_views()
    return rt._delta_timeline[-1]


# ---------- ① 时间线落代/截断 ----------


def test_timeline_appends_per_publish_and_truncates():
    """每次发布恰追加一条目 + maxlen=40 截断(plan S2 验收 DoD 第 1 条)"""
    store = _make_store("H1")
    rt = _delta_runtime(store)
    base = rt.group_view_ver
    assert len(rt._delta_timeline) == 0  # 尚未发布: 时间线为空
    for i in range(1, 46):  # 45 次发布(无 store 增量 -> 空键集条目)
        rt.mark_dirty()
        entry = _publish(rt)
        assert len(rt._delta_timeline) == min(i, 40)
        assert entry["ver"] == rt.group_view_ver == base + i  # 本仓 ver 单调(qB 为循环, 不回绕)
        assert entry["full"] is False
    # 条目形状(plan S2 数据结构)
    entry = rt._delta_timeline[-1]
    assert set(entry.keys()) == {"ver", "full", "upsert", "removed"}
    for bucket in ("upsert", "removed"):
        assert set(entry[bucket].keys()) == {"torrent", "group", "show"}
        assert all(v == set() for v in entry[bucket].values())
    # 环满截断: 最旧 5 条(base+1..base+5)已被挤掉
    vers = [e["ver"] for e in rt._delta_timeline]
    assert vers[0] == base + 6 and vers[-1] == base + 45


# ---------- ② 交叉抵消 ----------


def test_same_tick_upsert_removed_cancel():
    """同拍同视图 upsert/removed 交叉抵消(R5): 落代前分视图两清, 不给客户端又删又发同一行

    removed hash 须带组键(否则按 R11 直接本代 full, 走不到抵消段) —— 用例 ⑤ 专测该分支。
    """
    store = _make_store("H1")
    store.member_to_key["H3"] = ("R:\\D", )
    store.groups[("R:\\D", )] = ["H3"]
    store.member_to_key["H4"] = ("R:\\E", )
    store.groups[("R:\\E", )] = ["H4"]
    rt = _delta_runtime(store)
    store.last_added = ["H2", "H3"]
    store.last_removed = ["H3", "H4"]  # H3 同拍增删 -> 净零; H4 组仍 -> 组行 upsert
    rt.mark_dirty()
    entry = _publish(rt)
    assert entry["full"] is False
    assert entry["upsert"]["torrent"] == {"H2"}
    assert entry["removed"]["torrent"] == {"H4"}
    assert entry["upsert"]["group"] == {("R:\\D", ), ("R:\\E", )}
    assert entry["removed"]["group"] == set()
    # show 桶本步恒空(S8/S9 再接)
    assert entry["upsert"]["show"] == set() and entry["removed"]["show"] == set()


# ---------- ③ 门控跳拍累积 ----------


def test_gate_skipped_round_keys_survive_to_next_gen():
    """门控跳拍键集累积进下一代不丢(R4): 「上一版没被取走不重建」语义原样保留"""
    store = _make_store("H1")
    store.member_to_key["H2"] = ("R:\\D", )
    store.groups[("R:\\D", )] = ["H2"]
    rt = _delta_runtime(store)
    rt.pending_ver = 999  # 模拟上一版未被任何 /api/state 取走
    store.last_added = ["H2"]
    store.delta_fields = {"H1": frozenset({"dlspeed", "upspeed"})}
    rt.mark_dirty()
    rt.flush_views()  # 门控拦截: 不落代
    assert len(rt._delta_timeline) == 0
    assert rt.group_view_dirty is True
    # 排空照常: 键集已并入累积器(hash 直用 torrent 桶, member_to_key 映射 group 桶)
    assert rt._delta_pending["upsert"]["torrent"] == {"H1", "H2"}
    assert rt._delta_pending["upsert"]["group"] == {("R:\\D", )}
    # 下一拍客户端取走 -> 落代, 累积键集并入本代条目不丢
    entry = _publish(rt)
    assert len(rt._delta_timeline) == 1
    assert entry["ver"] == rt.group_view_ver
    assert entry["upsert"]["torrent"] == {"H1", "H2"}
    assert entry["upsert"]["group"] == {("R:\\D", )}


# ---------- ④ 五个降级源矩阵 ----------


def test_full_downgrade_sources_matrix():
    """五个降级源各自触发 full 代(R11): full 条目键集清空, 累积器与理由一并清空"""
    # a) 配置热重载(module.py apply -> mark_dirty(full=True, reason="config_reload"))
    rt = _delta_runtime(_make_store("H1"))
    rt._delta_pending["upsert"]["torrent"].add("HX")  # 预置累积键: full 代一并清空
    rt.mark_dirty(full=True, reason="config_reload")
    entry = _publish(rt)
    assert entry["full"] is True and entry["ver"] == rt.group_view_ver
    assert all(v == set() for bucket in entry.values() if isinstance(bucket, dict) for v in bucket.values())
    assert rt._delta_pending["upsert"]["torrent"] == set()  # 累积器清空(full 响应覆盖到当前 ver)
    assert rt._pending_full_reasons == set()  # 理由一并清空

    # b) HR revision(flush_views 判定点): 基线不等即 full, 重建后基线前移下一拍不再 full
    store = _make_store("H1")
    rt = _delta_runtime(store)
    rt._host.hr = SimpleNamespace(revision=7)
    rt.mark_dirty()
    assert _publish(rt)["full"] is True
    rt.mark_dirty()
    assert _publish(rt)["full"] is False

    # c) shows_pending 归位(True->False 转换拍; 非转换拍不登记)
    rt = _delta_runtime(_make_store("H1"))
    rt.shows_pending = True
    rt.mark_shows_pending(False)  # 模拟 views._trigger_shows_rebuild_if_pending 归位
    rt.mark_dirty()
    assert _publish(rt)["full"] is True
    rt.mark_shows_pending(False)  # 已归位: False->False 无转换
    rt.mark_dirty()
    assert _publish(rt)["full"] is False

    # d) 跨组交叉标记增删(走真 _build_group_view 的构建期回传): 首代立基线, 增删即 full
    store = _make_store("H1")
    rt = _delta_runtime(store)
    store.cross_group_conflict_warned = {(("R:\\A", ), ("R:\\B", ))}
    rt.mark_dirty()
    assert _publish(rt)["full"] is False  # 首代只立基线(时间线此前为空, 客户端本就窗外)
    store.cross_group_conflict_warned = {(("R:\\A", ), ("R:\\B", )), (("R:\\C", ), ("R:\\D", ))}
    rt.mark_dirty()
    entry = _publish(rt)
    assert entry["full"] is True  # 键集增 -> 本代 full(不归约旧组键)
    assert entry["upsert"]["torrent"] == set() and entry["removed"]["torrent"] == set()

    # e) 进程重启: ver 以进程启动时间播种(runtime 构造), 时间线/累积器归零 —— 旧客户端
    #    的 rid 小于新 ver 即窗外、大于新 ver 即 rid>ver, 两者都退化全量(R10), 无需显式标记
    store = _make_store("H1")
    rt = _delta_runtime(store)
    for _ in range(3):
        rt.mark_dirty()
        _publish(rt)
    floor = int(time.time())
    rt2 = WebUIRuntime(rt._host)  # 全新运行时 = 进程重启的进程内观察面
    assert len(rt2._delta_timeline) == 0
    assert rt2._delta_pending["upsert"]["torrent"] == set()
    assert rt2.group_view_ver >= floor  # 时间播种不回落到旧客户端已持有的值之前


# ---------- ⑤ 组行 removed 键不可推导转 full ----------


def test_group_removed_key_unresolvable_full():
    """组行 removed 键推导(R11): 查得到按组仍在/解散分流; 查不到 -> 本代 full(保守)"""
    store = _make_store("H1")
    store.member_to_key["HG"] = ("R:\\D", )
    store.groups[("R:\\D", )] = ["HG"]
    rt = _delta_runtime(store)
    # 对照: removed hash 组键查得到且组仍在 -> 组行内容变了(upsert)
    store.last_removed = ["HG"]
    rt.mark_dirty()
    entry = _publish(rt)
    assert entry["full"] is False
    assert entry["removed"]["torrent"] == {"HG"}
    assert entry["upsert"]["group"] == {("R:\\D", )}
    # 组键查得到但组已解散 -> 组行消失(removed)
    store.member_to_key["HX"] = ("R:\\E", )  # groups 无 ("R:\\E",) = 已解散
    store.last_removed = ["HX"]
    rt.mark_dirty()
    entry = _publish(rt)
    assert entry["full"] is False
    assert entry["removed"]["group"] == {("R:\\E", )}
    # 本体: removed hash 查不到组键(组键已随 _leave_group/解散清除, 与"从未归组"不可区分)
    # -> 该组行键不可归约 -> 本代 full 且键集清空(R11 保守正确优先)
    rt._delta_pending["upsert"]["torrent"].add("HY")  # 预置累积键: full 代一并清空
    store.last_removed = ["H404"]
    rt.mark_dirty()
    entry = _publish(rt)
    assert entry["full"] is True
    assert entry["removed"]["torrent"] == set() and entry["upsert"]["torrent"] == set()
    assert rt._pending_full_reasons == set()  # 理由随落代清空
    assert rt._delta_pending["upsert"]["torrent"] == set()


# ---------- ⑥ 错误原因预取的行级归约(S2 补丁) ----------


def test_error_reason_refresh_row_level_upsert():
    """错误原因预取按行级归约(S2 补丁, 源标签 "tracker_error_refresh"): 改写的行(hash)在
    改写点可得 -> 不走 full 降级, delta 客户端本代即拿到 error_reason 新值

    走真 refresh_error_reasons(错误态种子 + FakeClient.trackers_map 报错条目);
    任务线真实时序 = 预取 -> flush_views(排空) -> 发布(落代)。
    """
    store = _make_store("H1", state="error")
    store.member_to_key["H1"] = ("R:\\D", )
    store.groups[("R:\\D", )] = ["H1"]
    rt = _delta_runtime(store)
    host = rt._host
    host.client = store.client
    host.client.trackers_map["H1"] = [
        {
            "url": "https://tracker.example.net/announce.php",
            "status": 4,
            "msg": "torrent not registered"
        },
    ]
    rt.mark_dirty()
    _publish(rt)  # 基线代: 先发布一版, 之后仅错误原因变化
    # 仅错误原因刷新的一拍: store 零增量(无 added/removed/delta_fields)
    host.refresh_error_reasons()
    assert store.by_hash["H1"].tracker_error_msg == "torrent not registered"
    assert not store.last_added and not store.last_removed and not store.delta_fields
    assert rt._pending_error_hashes == {"H1"}  # 行键已在改写点登记, 等落代消费
    # 门控跳拍: 暂存键集不丢(R4, fold 是唯一消费点)
    rt.pending_ver = 999
    rt.flush_views()
    assert rt._pending_error_hashes == {"H1"}
    # 门控放行 -> 落代: 受影响行进 torrent 桶, 组行 members 的 error_reason 随成员变化 -> 组键一并 upsert
    entry = _publish(rt)
    assert entry["full"] is False
    assert entry["upsert"]["torrent"] == {"H1"}
    assert entry["upsert"]["group"] == {("R:\\D", )}
    assert rt._pending_error_hashes == set()  # 暂存随落代清空
    # 无变化轮不登记(TTL 内不重取): 下一条目键集为空
    rt.mark_dirty()
    entry = _publish(rt)
    assert entry["full"] is False
    assert entry["upsert"]["torrent"] == set() and entry["upsert"]["group"] == set()
