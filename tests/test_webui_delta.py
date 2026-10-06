"""test_webui_delta 测试计划: WebUI 增量时间线(plan 26-10-07-0414 S2/S3)

被测面: WebUIRuntime 的时间线落代(_fold_delta_pending_locked)/store 增量排空与脏行键推导
(_drain_delta_locked)/full 降级理由集合(R11 五源)/views._build_group_view 的构建期交叉键
回传(S2); ensure_state 的 delta 协商门控与 _reduce_delta 归约判定矩阵 + 增量协议字段(S3)。
show 桶 S8/S9 才接(S3 期 view=show 恒全量)。

## 测试计划(每个测试函数一条)
- test_timeline_appends_per_publish_and_truncates: 时间线落代/截断 —— 每次发布恰追加一条目(ver 与 group_view_ver 对齐, 本仓 ver 单调), 条目形状 = ver/full/upsert/removed 四键分 torrent/group/show 三桶; 45 次发布后 maxlen=40 截断(最旧 5 条被挤掉)
- test_same_tick_upsert_removed_cancel: 交叉抵消(R5) —— 同拍同视图 upsert/removed 同键落代前两清(H3 同拍增删净零), 异键照常保留; show 桶恒空
- test_gate_skipped_round_keys_survive_to_next_gen: 门控跳拍累积(R4) —— 上一版未被取走时 flush 只排空累积不落代, 键集(含组键)并入下一代条目不丢
- test_full_downgrade_sources_matrix: 五个降级源矩阵(R11) —— config_reload(mark_dirty full=True)/hr_revision(flush 判定点)/shows_pending(归位转换拍)/cross_group(构建期键集增删, 走真 _build_group_view 回传)各自触发 full 代(full 条目键集清空 + 累积器与理由一并清空; hr/cross 均有"下一拍不再 full"的对照); 进程重启 = ver 时间播种 + 时间线/累积器为空, 旧客户端 rid 必然窗外或 rid>ver 全量(R10, 无需显式标记)
- test_group_removed_key_unresolvable_full: 组行 removed 键推导(R11) —— removed hash 组键查得到且组仍在 -> 组键进 upsert; 组已解散 -> 组键进 removed; 查不到(与"从未归组"不可区分) -> 本代 full 且键集清空
- test_error_reason_refresh_row_level_upsert: 错误原因预取按行级归约(S2 补丁, 源标签 "tracker_error_refresh") —— 走真 refresh_error_reasons 改写 tracker_error_msg, 仅原因刷新、store 零增量 -> 受影响行进 torrent/group 桶 upsert 且该代不 full; 门控跳拍键集暂存不丢(R4); 无变化轮不登记
- test_ensure_state_no_negotiation_byte_compatible: S3 硬验收 —— 未带 delta=1 协商参数的响应与历史逐字节等价: 键集恰为 rid/updated(+VIEW_ARRAYS 裁剪的数组), 无 full/delta/removed 键; 数组内容 = 当前已发布视图
- test_reduce_delta_full_branch_matrix: 归约判定全分支(S3, R3/R10) —— rid==ver 零回传(带不带 delta 都只回 rid/updated); rid 缺省/0/-1、rid>ver、窗外(maxlen 截断挤掉客户端所在代)、窗内任一代 full -> 全量且协商客户端标 full=true(不含 delta/removed); 启用矩阵: view=show/缺省/未知值恒全量
- test_reduce_delta_upsert_removed_normal: 正常归约(S3) —— torrent 视图 delta.torrents 回平铺整行/removed 回 hash; group 视图 delta.groups 回组行(键 = encode_group_key 字符串)/delta.singles 只收未归组行/removed.groups 回 encode 后字符串; 行内容 = 当前已发布视图的原行(R1, 引用恒等)
- test_reduce_delta_cross_gen_removed_yields_to_upsert: R5 跨代版 —— 先删后加: removed 让位于 upsert, 回 delta 不回 removed; 先加后删: 抵消后 upsert 行已不在当前视图 -> 防御性转 full
- test_reduce_payload_json_native_and_key_exclusivity: JSON 原生守阵(S3 DoD) —— 增量载荷全字段递归断言 JSON 原生类型 + json.dumps 无错(端点 JSONResponse 直出同款); 增量响应不含全量四数组键、全量响应不含 delta/removed 键(逐一断言)
"""
import json
import time
from collections import deque
from types import SimpleNamespace

from auto_qb.core.qbapi import QbApi
from auto_qb.infra.utils import encode_group_key
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


# ---------- ⑦ S3: ensure_state 协商门控 + _reduce_delta 归约 ----------


def _baseline_rid(store_hashes=("H1", )) -> tuple:
    """装库 + 基线代发布, 回 (store, runtime, 客户端所持 rid)"""
    store = _make_store(*store_hashes)
    rt = _delta_runtime(store)
    rt.mark_dirty()
    _publish(rt)  # 基线代(空键集条目): 客户端在此版本上持全量
    return store, rt, rt.group_view_ver


def _advance_gen(store, rt) -> dict:
    """驱动一个带键集的增量代(H1 速度字段变化), 回本代条目"""
    store.delta_fields = {"H1": frozenset({"dlspeed"})}
    rt.mark_dirty()
    return _publish(rt)


def test_ensure_state_no_negotiation_byte_compatible():
    """S3 硬验收: 未带 delta=1 的响应与历史逐字节等价 —— 无 full/delta/removed 键, 数组原样"""
    store, rt, rid = _baseline_rid(("H1", "H2"))
    _advance_gen(store, rt)  # 窗口完美匹配也必须全量: 归约只对协商客户端开放
    # 单视图请求(view=torrent): 键集恰为 rid/updated/torrents
    state = rt.ensure_state(rid, "torrent")
    assert set(state.keys()) == {"rid", "updated", "torrents"}
    assert state["updated"] is True and state["rid"] == rt.group_view_ver
    assert state["torrents"] == rt.flat_view
    for absent in ("full", "delta", "removed"):
        assert absent not in state
    # view=group: groups + singles 连带裁剪
    state = rt.ensure_state(rid, "group")
    assert set(state.keys()) == {"rid", "updated", "groups", "singles"}
    assert state["groups"] == rt.group_view and state["singles"] == rt.singles_view
    # view 缺省: 四数组全回(保守默认)
    state = rt.ensure_state(rid)
    assert set(state.keys()) == {"rid", "updated", "groups", "singles", "shows", "torrents"}
    # rid==ver 零回传形状不变
    assert rt.ensure_state(rt.group_view_ver, "torrent") == {"rid": rt.group_view_ver, "updated": False}


def test_reduce_delta_full_branch_matrix():
    """归约判定全分支(S3, R3/R10): 该 full 的分支一个不少, 零回传语义保留"""
    # a) rid==ver 零回传: 带不带 delta 都只回 rid/updated(plan S3 保留 :828 语义)
    store, rt, rid = _baseline_rid()
    assert rt.ensure_state(rid, "torrent", True) == {"rid": rid, "updated": False}
    assert rt.ensure_state(rid, "torrent") == {"rid": rid, "updated": False}

    # b) rid 缺省/0/-1 -> 全量(协商客户端标 full=true, 不含 delta/removed)
    store, rt, _ = _baseline_rid()
    _advance_gen(store, rt)
    for bad in (None, 0, -1):
        state = rt.ensure_state(bad, "torrent", True)
        assert state["full"] is True and "torrents" in state
        assert "delta" not in state and "removed" not in state

    # c) rid > ver(时钟倒挂) -> 全量
    state = rt.ensure_state(rt.group_view_ver + 1, "torrent", True)
    assert state["full"] is True and "torrents" in state

    # d) rid 窗外: 时间线 maxlen=40 把客户端所在代挤出 -> 全量(R10 窗口滑出)
    store, rt, first = _baseline_rid()
    for _ in range(40):  # 再落 40 代: 首代(客户端所持)被 maxlen 挤出
        rt.mark_dirty()
        _publish(rt)
    assert rt._delta_timeline[0]["ver"] > first  # 前置: 客户端 rid 确已窗外
    state = rt.ensure_state(first, "torrent", True)
    assert state["full"] is True and "torrents" in state

    # e) 窗内任一代 full -> 全量(full 代键集已清空, 键集链断裂, R10/R11)
    store, rt, rid = _baseline_rid()
    rt.mark_dirty(full=True, reason="config_reload")
    _publish(rt)  # 中间代 full
    _advance_gen(store, rt)  # 后续代键集正常也救不回来
    state = rt.ensure_state(rid, "torrent", True)
    assert state["full"] is True and "torrents" in state

    # f) 启用矩阵: view=show / 缺省(四数组)/未知值恒全量(show 桶 S8/S9 才接, S3)
    store, rt, rid = _baseline_rid()
    _advance_gen(store, rt)
    for view in ("show", None, "nope"):
        state = rt.ensure_state(rid, view, True)
        assert state["full"] is True
        assert "delta" not in state and "removed" not in state


def test_reduce_delta_upsert_removed_normal():
    """正常归约(S3): 行内容取自当前已发布视图(R1), 桶按视图裁剪, removed 回标识符列表"""
    # torrent 视图: delta.torrents 回平铺整行(引用恒等), 无删除时 removed 为空列表
    store, rt, rid = _baseline_rid(("H1", "H2"))
    _advance_gen(store, rt)  # H1 速度变化 -> torrent 桶 upsert {H1}
    state = rt.ensure_state(rid, "torrent", True)
    assert state["full"] is False and state["rid"] == rt.group_view_ver
    assert state["delta"] == {"torrents": [rt.flat_view[0]]}  # 行 = 当前视图原行(R1)
    assert state["delta"]["torrents"][0]["hash"] == "H1"
    assert state["removed"] == {"torrents": []}

    # group 视图: 组行 upsert 回整行(键 = encode_group_key), singles 桶只收未归组行
    store = _make_store("H1", "H2")
    store.member_to_key["H1"] = ("R:\\D", )
    store.groups[("R:\\D", )] = ["H1"]  # H1 归组, H2 未归组
    rt = _delta_runtime(store)
    rt.mark_dirty()
    rid = _publish(rt)["ver"]
    store.delta_fields = {"H1": frozenset({"dlspeed"}), "H2": frozenset({"upspeed"})}
    rt.mark_dirty()
    entry = _publish(rt)
    assert entry["full"] is False
    state = rt.ensure_state(rid, "group", True)
    assert state["full"] is False
    gv = {r["key"]: r for r in rt.group_view}
    enc = encode_group_key(("R:\\D", ))
    assert [r["key"] for r in state["delta"]["groups"]] == [enc]
    assert state["delta"]["groups"][0] is gv[enc]  # R1: 行内容 = 当前已发布视图原行
    assert [r["hash"] for r in state["delta"]["singles"]] == ["H2"]  # 归组行不进 singles 桶
    assert state["removed"] == {"groups": [], "singles": []}

    # 组解散代(组内唯一成员被删, 组随之消失): removed.groups 回 encode 后字符串
    # (与视图行键同标识), removed.singles 回 hash
    store = _make_store("H1")
    store.member_to_key["H1"] = ("R:\\D", )
    store.groups[("R:\\D", )] = ["H1"]
    rt = _delta_runtime(store)
    rt.mark_dirty()
    rid = _publish(rt)["ver"]
    store.groups.pop(("R:\\D", ))  # 解散: 组键查得到但 groups 无 -> 组行 removed(S2 同款分流)
    store.by_hash.pop("H1")  # 成员删除是解散的因: 行从 store 与全部视图消失
    store.last_removed = ["H1"]
    rt.mark_dirty()
    entry = _publish(rt)
    assert entry["full"] is False and entry["removed"]["group"] == {("R:\\D", )}
    state = rt.ensure_state(rid, "group", True)
    assert state["full"] is False
    assert state["delta"] == {"groups": [], "singles": []}
    assert state["removed"] == {"groups": [encode_group_key(("R:\\D", ))], "singles": ["H1"]}

    # 空键集代(纯 mark_dirty 的命令驱动重建, 视图内容未变): 归约命中但桶全空 ——
    # delta/removed 恒在、可为空(协议定案)
    store, rt, rid = _baseline_rid(("H1", ))
    rt.mark_dirty()
    _publish(rt)
    state = rt.ensure_state(rid, "torrent", True)
    assert state["full"] is False
    assert state["delta"] == {"torrents": []} and state["removed"] == {"torrents": []}


def test_reduce_delta_cross_gen_removed_yields_to_upsert():
    """R5 跨代版(S3): 后改回的行让位回 upsert; 抵消后 upsert 行已不在当前视图 -> 防御性 full

    删除代必须键可解析(member_to_key 查得到)否则按 R11 本代 full, 走不到归约(S2 用例 ⑤ 专测)。
    """
    # 先删后加: removed 让位于后续 upsert -> 回 delta 行, 不回 removed
    store, rt, rid = _baseline_rid(("H1", "H2"))
    store.member_to_key["H2"] = ("R:\\D", )
    store.groups[("R:\\D", )] = ["H2"]  # H2 归组: 删除代组键可解析, 不触发 R11 full
    store.by_hash.pop("H2")
    store.last_added, store.last_removed = [], ["H2"]  # S1「最近一轮」: 每代显式双写防残值
    rt.mark_dirty()
    e1 = _publish(rt)  # 代+1: removed {H2}
    assert e1["full"] is False
    store.by_hash["H2"] = FakeTorrent(hash="H2", name="Show.H2.S01E01.720p.x264-GRP", state="stalledUP")
    store.last_added, store.last_removed = ["H2"], []
    rt.mark_dirty()
    e2 = _publish(rt)  # 代+2: upsert {H2}
    assert e2["full"] is False
    state = rt.ensure_state(rid, "torrent", True)
    assert state["full"] is False
    assert [r["hash"] for r in state["delta"]["torrents"]] == ["H2"]
    assert state["removed"] == {"torrents": []}

    # 先加后删(反向): 跨代抵消后 upsert 残留, 但行已不在当前视图 -> 防御性转 full
    store, rt, rid = _baseline_rid(("H1", ))
    store.member_to_key["H2"] = ("R:\\D", )
    store.groups[("R:\\D", )] = ["H2"]
    store.by_hash["H2"] = FakeTorrent(hash="H2", name="Show.H2.S01E01.720p.x264-GRP", state="stalledUP")
    store.last_added, store.last_removed = ["H2"], []
    rt.mark_dirty()
    e1 = _publish(rt)  # 代+1: upsert {H2}
    assert e1["full"] is False
    store.by_hash.pop("H2")
    store.last_added, store.last_removed = [], ["H2"]
    rt.mark_dirty()
    e2 = _publish(rt)  # 代+2: removed {H2}(组仍在 -> 键可解析, 非 full)
    assert e2["full"] is False
    state = rt.ensure_state(rid, "torrent", True)  # 窗内两代均非 full: full 只能来自防御检查
    assert state["full"] is True and "torrents" in state
    assert "delta" not in state and "removed" not in state


def _assert_json_native(obj, path="root"):
    """递归断言 JSON 原生类型(str/int/float/bool/None/dict/list) —— 端点 JSONResponse
    直出跳过 jsonable_encoder(state.py fail-fast), 非原生类型会直接 500"""
    if obj is None or isinstance(obj, (str, bool, int, float)):
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            assert isinstance(k, str), f"{path}: 键非 str: {k!r}"
            _assert_json_native(v, f"{path}.{k}")
        return
    if isinstance(obj, list):
        for i, v in enumerate(obj):
            _assert_json_native(v, f"{path}[{i}]")
        return
    raise AssertionError(f"{path}: 非 JSON 原生类型 {type(obj).__name__}")


def test_reduce_payload_json_native_and_key_exclusivity():
    """JSON 原生守阵 + 键互斥(S3 DoD): 增量载荷全字段可 json.dumps; 增量不含四数组键,
    全量不含 delta/removed 键(逐一断言, R10)"""
    store = _make_store("H1", "H2")
    store.member_to_key["H1"] = ("R:\\D", )
    store.groups[("R:\\D", )] = ["H1"]
    rt = _delta_runtime(store)
    rt.mark_dirty()
    rid = _publish(rt)["ver"]
    # 增量代: 组行 + 未归组行 + 新增行, 载荷覆盖 groups/singles/torrents 三桶
    store.by_hash["H3"] = FakeTorrent(hash="H3", name="Show.H3.S01E01.720p.x264-GRP", state="stalledUP")
    store.last_added = ["H3"]
    store.delta_fields = {"H1": frozenset({"dlspeed"}), "H2": frozenset({"upspeed"})}
    rt.mark_dirty()
    entry = _publish(rt)
    assert entry["full"] is False
    for view in ("torrent", "group"):
        state = rt.ensure_state(rid, view, True)
        assert state["full"] is False
        for k in ("groups", "singles", "shows", "torrents"):  # 增量响应不含全量四数组键
            assert k not in state, f"增量响应混入全量数组键 {k}"
        _assert_json_native(state)
        json.dumps(state, ensure_ascii=False)  # 端点 JSONResponse 直出同款序列化, 不得抛
    # 桶内容 sanity: torrent 桶 = H1/H2/H3 全量并集, group 桶 = 组行, singles 桶 = 未归组 H2/H3
    state = rt.ensure_state(rid, "group", True)
    assert {r["hash"] for r in state["delta"]["singles"]} == {"H2", "H3"}
    assert [r["key"] for r in state["delta"]["groups"]] == [encode_group_key(("R:\\D", ))]
    tstate = rt.ensure_state(rid, "torrent", True)
    assert {r["hash"] for r in tstate["delta"]["torrents"]} == {"H1", "H2", "H3"}
    # 全量分支(协商): full=true 且不含 delta/removed(R10)
    for view in ("torrent", "group", "show", None):
        full_state = rt.ensure_state(0, view, True)
        assert full_state["full"] is True
        for k in ("delta", "removed"):
            assert k not in full_state, f"全量响应混入 {k} 键"
        _assert_json_native(full_state)
        json.dumps(full_state, ensure_ascii=False)
    # 未协商全量同样不含 delta/removed(历史形状)
    legacy = rt.ensure_state(0, "torrent")
    for k in ("delta", "removed", "full"):
        assert k not in legacy
