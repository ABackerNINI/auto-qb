"""test_webui_delta_mirror 测试计划: WebUI 增量同步镜子测试(plan 26-10-07-0414 S5)

镜子不变量(§02 总纲): 任意操作序列下「从 rid0 逐轮吃 delta 合并(B 通道)」≡「每轮全量快照
(A 通道)」。A 通道 = 每轮 ensure_state(rid=0) 拿全量四数组; B 通道 = S4 前端合并
(polling.js applyStateRows)的 Python 复刻 —— delta 轮行级 upsert(整行替换/追加, R8)+
removed 剔除, full 轮(payload.full 非 False, 含未协商形状)清空重放(R6); 行内容 JSON 深拷贝
落袋(前端持有自有副本的语义)。每轮断言 B ≡ A: 按行键集合 + 行内容逐字段, 不比数组顺序
(S4 顺序安全事实)。

## 测试计划(每个测试函数一条; S5a = M1-M5 + 无键 dirty 源, S5b = M6-M9 + fuzz)
- test_m1_same_torrent_two_beats_unconfirmed_middle: M1(避坑#1, #24845 形态键级回归) —— 同一种子
  连续两拍变化、中间响应未被确认(门控跳拍): 两代键集都进窗口, B 合并后行内容 = 两拍叠加的
  最新真值 ≡ A(R1 值回放不取陈旧代)
- test_m2_two_clients_reduce_own_window: M2(避坑#2) —— rid1 与 rid5 两个客户端各自归约各自的
  窗口, 各自合并结果都 ≡ A(时间线全局一份, 多客户端不互踩退化全量)
- test_m3_quantum_boundary_beat_invisible: M3(避坑#4) —— last_activity 在 _VIEW_QUANTUM(60s)
  桶内跳动: apply_delta 量化判定不记变化 -> 不置脏不落代(对照: 跨桶跳动正常产生增量代, 行
  内容为量化值); 活跃速度字段(dlspeed)不量化属预期真脏, 不在本用例范围
- test_m4_same_tick_add_remove_and_pending_removed_overlap: M4(避坑#7) —— 同一 hash 同拍一增
  一删经 R5 交叉抵消, 响应不含该 hash 的 upsert/removed; 待报删除(_pending_removed)与增量
  removed 重叠去重, 响应恰一次
- test_m5_hr_revision_wave_yields_full: M5(02 笔记 2.5.3) —— HR revision 波次 -> 本代 full,
  响应不含 delta/removed 键(R10); 下一拍 revision 未再变 -> 恢复行级增量
- test_unkeyed_command_source_yields_full: 无键 dirty 源(R11 缺口, S3 观察) —— 命令自写字段
  (update_torrent_fields)/reset_runtime 只置 view_changed 无行键, 落代必须 full(修复前为
  「空键集且 full=False」, delta 客户端漏变更); 对照: store 驱动常规轮不受影响照常行级增量
- test_m6_restart_ver_seeding_old_rid_full: M6 —— 进程重启 ver 时间播种(runtime.py:137-138,
  不回落): 时间线/累积器归零, 旧客户端 rid 窗外 -> 全量(R10); 对照: 重启后新一轮增量照常
- test_m7_window_slide_out_and_rid_ahead_full: M7 —— 窗口滑出(41 代未消费, maxlen=40 把客户端
  所在代挤出)与 rid>ver(时钟倒挂)都退化全量(R3/R10), 全量重放补齐后 ≡ A
- test_m8_show_view_always_full: M8 —— view=show / 缺省(四数组)/ 未知值恒全量且响应无
  delta/removed 键(S9 前的启用矩阵; 增量镜像客户端只覆盖 torrent/group 两个已启用视图)
- test_m9_gate_skipped_rounds_end_to_end: M9 —— 门控跳拍累积(R4)端到端镜子版: 三拍中后两拍
  未被消费, 键集并入下一代不丢; 恢复消费后一轮增量拿齐全部三拍变化, B ≡ A
- test_fuzz_random_operation_sequence: fuzz —— 固定种子(random.Random(20261007))随机操作序列
  N=220 轮, 操作池覆盖 增/删/改(量化边界+真脏字段)/同拍增删/门控跳拍/命令无键源/HR 波次,
  每轮断言 B ≡ A
"""
import itertools
import json
import random
import time
from types import SimpleNamespace
from unittest import mock

from auto_qb.core.qbapi import QbApi
from auto_qb.torrents import REQUIRED_TORRENT_FIELDS, TorrentStore
from auto_qb.webui import WebUIRuntime
from auto_qb.webui.views import WebviewMixin

from helpers import FakeClient, FakeTorrent

# ---------- 替身与驱动(范式同 test_webui_delta/test_sync) ----------


class _ViewHost(WebviewMixin):
    """views 构建器真跑的最小宿主(纯读 store/web, 见 test_webui_delta 同款)"""
    def __init__(self, store):
        self.store = store
        self.web = None  # _delta_runtime 里回填
        self.client = None

    def wake(self):  # _build_shows_view 的 post_command 路径兜底(本文件用例不会触发)
        pass


def _make_store(*hashes, state: str = "stalledUP") -> TorrentStore:
    """真实 TorrentStore 装库(FakeClient/FakeTorrent 范式同 test_sync), 随后清掉装库轮的
    S1 快照与 view_changed —— 基线不进被测时间线窗口, 各用例从干净基线驱动"""
    client = FakeClient()
    for h in hashes:
        # 剧集形命名: parse_release 解析为 episode(带 key), 不触发 _build_shows_view 的
        # 文件兑底 pending 标记(与 test_webui_delta 同款防干扰)
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


def _beat(store, hash_: str, **fields):
    """真机节拍的一拍: 改 qB 侧种子字段 -> 增量 sync 一轮(store._apply 真跑推导 delta_fields)"""
    tor = store.client.torrents[hash_]
    for k, v in fields.items():
        setattr(tor, k, v)
    return store.apply_sync(QbApi(store.client, store))


# ---------- 双通道断言器 ----------

_ROW_KEYS = {"torrents": "hash", "singles": "hash", "groups": "key"}


def _json_copy(row):
    return json.loads(json.dumps(row, ensure_ascii=False))


class DeltaClient:
    """B 通道消费端: S4 前端合并(polling.js applyStateRows)的 Python 复刻

    - full 轮(payload.full 非 False, 含未协商旧形状): 清空重放(R6), 只吃载荷里存在的
      数组键(前端「键不存在必须保留原引用」纪律 -> 镜子侧不动对应桶);
    - delta 轮(full===False): 行级 upsert(整行替换/追加, R8)+ removed 剔除;
    - 行内容 JSON 深拷贝(前端持有自有副本, 不与服务端行对象别名), rid 随响应推进。
    """
    def __init__(self, view: str):
        self.view = view  # "torrent" | "group"(S3 期增量启用矩阵仅此两视图)
        self.rid = 0
        self.rows = {"torrents": {}, "singles": {}, "groups": {}}

    def apply(self, payload: dict) -> dict:
        if payload.get("full") is not False:
            for bucket, keyf in _ROW_KEYS.items():
                if bucket in payload:
                    self.rows[bucket] = {r[keyf]: _json_copy(r) for r in payload[bucket]}
            self.rid = payload["rid"]
            return payload
        d = payload.get("delta") or {}
        r = payload.get("removed") or {}
        for bucket, keyf in _ROW_KEYS.items():
            ups = d.get(bucket) or []
            rms = r.get(bucket) or []
            if not ups and not rms:
                continue
            for row in ups:
                self.rows[bucket][row[keyf]] = _json_copy(row)
            for k in rms:
                self.rows[bucket].pop(k, None)
        self.rid = payload["rid"]
        return payload


def _assert_rows(merged: dict, expect_rows: list, keyf: str, ctx: str) -> None:
    """镜子断言: 行键集合相等 + 行内容逐字段相等(不比数组顺序)"""
    expect = {r[keyf]: r for r in expect_rows}
    assert set(merged) == set(expect), (f"{ctx}: 行键集合不等\n  B(增量合并) = {sorted(merged)}\n  A(全量快照) = {sorted(expect)}")
    for k, row in expect.items():
        assert merged[k] == row, f"{ctx}: 行 {k} 内容不等\n  B = {merged[k]}\n  A = {row}"


class Mirror:
    """双通道断言器: 同一操作序列喂两条消费路径, 每轮断言 B ≡ A

    publish() = 生产侧一拍(不模拟消费 —— 消费由 sync 的 ensure_state 完成并放行下一版;
    「中间响应未被确认」形态由用例显式构造: 连续 publish 而中间无 sync 即门控跳拍)。
    """
    def __init__(self, store: TorrentStore, rt: WebUIRuntime):
        self.store = store
        self.rt = rt

    def publish(self, force: bool = False) -> dict:
        self.rt.flush_views(force=force)
        return self.rt._delta_timeline[-1]

    def snapshot(self) -> dict:
        """A 通道: 全量快照(rid=0 恒全量; 顺带完成消费侧节拍)"""
        return self.rt.ensure_state(0)

    def sync(self, *clients: DeltaClient) -> dict:
        """一轮完整断言: A 快照 + B 逐客户端按自身 rid 拿增量合并 + B ≡ A

        clients 为空时只做 A 快照(维持生产节拍、不步进任何 B 客户端)。
        """
        a = self.snapshot()
        resps = []
        for c in clients:
            resps.append(c.apply(self.rt.ensure_state(c.rid, c.view, True)))
            if c.view == "torrent":
                _assert_rows(c.rows["torrents"], a["torrents"], "hash", "torrent视图")
            else:
                _assert_rows(c.rows["groups"], a["groups"], "key", "group视图/groups")
                _assert_rows(c.rows["singles"], a["singles"], "hash", "group视图/singles")
        return {"full": a, "resps": resps}


def _mirror(hashes=("H1", "H2")):
    """装库 + 基线代发布 + 双 B 客户端基线全量, 回 (store, rt, mirror, torrent客户端, group客户端)"""
    store = _make_store(*hashes)
    rt = _delta_runtime(store)
    m = Mirror(store, rt)
    ct, cg = DeltaClient("torrent"), DeltaClient("group")
    rt.mark_dirty()
    m.publish()
    m.sync(ct, cg)
    return store, rt, m, ct, cg


# ---------- M1: 同一种子连续两拍变化、中间响应未被确认(避坑#1) ----------


def test_m1_same_torrent_two_beats_unconfirmed_middle():
    store, rt, m, ct, cg = _mirror(("H1", "H2"))
    # 拍1: H1 速度变化, 发布成 gen2 —— 未被任何客户端取走
    _beat(store, "H1", dlspeed=1024)
    e2 = m.publish()
    assert e2["full"] is False and e2["upsert"]["torrent"] == {"H1"}
    # 拍2: 同一种子 state 变化 —— 上一版未确认, 门控跳拍不落代, 键集并入下一代(R4)
    _beat(store, "H1", state="pausedUP")
    m.publish()
    assert len(rt._delta_timeline) == 2  # 基线 + gen2: 跳拍未产生新代
    assert rt.group_view_dirty is True
    # 客户端此刻才来: ensure_state 触发落代 gen3, 窗口 (rid1, gen3] 含两代键集
    out = m.sync(ct, cg)
    assert len(rt._delta_timeline) == 3
    resp = out["resps"][0]
    assert resp["full"] is False
    assert [r["hash"] for r in resp["delta"]["torrents"]] == ["H1"]
    # 行内容 = 两拍叠加后的最新真值(R1 现取当前视图, 不取陈旧代值 —— #24845 键级回归点)
    assert resp["delta"]["torrents"][0]["dlspeed"] == 1024
    assert resp["delta"]["torrents"][0]["state"] == "pausedUP"


# ---------- M2: 两个不同 rid 的客户端各自拿增量(避坑#2) ----------


def test_m2_two_clients_reduce_own_window():
    store, rt, m, ct, cg = _mirror(("H1", "H2", "H3"))
    c5 = DeltaClient("torrent")  # gen5 才入场的第二客户端
    # gen2..gen5: 每拍不同种子变化; 期间只有 A 通道消费(维持生产节拍), ct/c5 缺席不步进
    for i, h in enumerate(("H1", "H2", "H3", "H1"), start=2):
        _beat(store, h, dlspeed=100 * i)
        m.publish()
        if i == 5:
            m.sync(c5)  # rid5 客户端入场: rid0 -> 全量重放, 此后持 gen5
        else:
            m.sync()  # 仅 A 快照
    assert ct.rid != c5.rid  # 前置: 两客户端各持不同 rid
    # gen6: H2 再变 -> 两客户端各自归约各自窗口, 合并结果都 ≡ A(时间线全局一份不互踩)
    _beat(store, "H2", dlspeed=999)
    m.publish()
    out = m.sync(ct, cg, c5)
    r1, r5 = out["resps"][0], out["resps"][2]
    assert r1["full"] is False and r5["full"] is False  # 各自归约命中, 都没退化全量
    assert {r["hash"] for r in r1["delta"]["torrents"]} == {"H1", "H2", "H3"}  # ct 窗口 = gen2..gen6 全程
    assert [r["hash"] for r in r5["delta"]["torrents"]] == ["H2"]  # c5 窗口 = gen6 一代
    assert r1["delta"]["torrents"][0]["dlspeed"] == 500  # ct 合并出 H1 的最新值(gen5 拍)
    h2_r1 = next(r for r in r1["delta"]["torrents"] if r["hash"] == "H2")
    assert h2_r1["dlspeed"] == r5["delta"]["torrents"][0]["dlspeed"] == 999


# ---------- M3: 量化边界值不产生增量(避坑#4) ----------


def test_m3_quantum_boundary_beat_invisible():
    store, rt, m, ct, cg = _mirror(("H1", ))
    # 真机 qB 每轮都报 last_activity(秒级递增); FakeClient 替身的 sync 载荷只含
    # REQUIRED_TORRENT_FIELDS(扩展字段不上线), 故按 qB 增量 patch 形态直喂 _apply ——
    # apply_delta 的量化判定(R9, view_field_value 单点)与真机同径
    # 基线拍: last_activity -1(从未) -> 960(量化桶 960)
    store._apply({"H1": {"last_activity": 960}}, [], full=False)
    m.publish()
    out = m.sync(ct, cg)
    assert out["resps"][0]["delta"]["torrents"][0]["last_activity"] == 960
    # 本体: 桶内跳动(+30, 仍落在 960 桶) -> apply_delta 量化判定不记变化 -> 不置脏不落代
    ver_before = rt.group_view_ver
    n_before = len(rt._delta_timeline)
    store._apply({"H1": {"last_activity": 990}}, [], full=False)
    m.publish()
    assert rt.group_view_ver == ver_before  # 不产生新代
    assert len(rt._delta_timeline) == n_before
    assert store.delta_fields == {}  # 变化集为空(量化吸收)
    m.sync(ct, cg)  # 零回传; B ≡ A 依旧
    # 对照: 跨桶跳动(960 -> 1021, 量化 1020) -> 正常产生增量代, 行内容为量化值
    store._apply({"H1": {"last_activity": 1021}}, [], full=False)
    m.publish()
    out = m.sync(ct, cg)
    resp = out["resps"][0]
    assert resp["full"] is False
    assert resp["delta"]["torrents"][0]["last_activity"] == 1020


# ---------- M4: 同拍一增一删 + 待报删除与增量 removed 重叠(避坑#7) ----------


def test_m4_same_tick_add_remove_and_pending_removed_overlap():
    # H2/H4 归组须在基线发布**前**登记(基线后手工改归组本身就是无键重建, B 通道无从观测)
    store = _make_store("H1", "H2", "H4")
    store.member_to_key["H2"] = ("R:\\D", )
    store.member_to_key["H4"] = ("R:\\D", )
    store.groups[("R:\\D", )] = ["H2", "H4"]
    rt = _delta_runtime(store)
    m = Mirror(store, rt)
    ct, cg = DeltaClient("torrent"), DeltaClient("group")
    rt.mark_dirty()
    m.publish()
    m.sync(ct, cg)
    # a) 待报删除与增量 removed 重叠: 本程序自删登记 _pending_removed, 下一轮 qB 增量响应
    #    也列出 torrents_removed —— 两路清单并集去重, 响应恰一次
    store.remove_torrent("H2")
    store.client.torrents.pop("H2")
    store.apply_sync(QbApi(store.client, store))
    entry = m.publish()
    assert entry["full"] is False
    assert entry["removed"]["torrent"] == {"H2"} and entry["upsert"]["group"] == {("R:\\D", )}
    out = m.sync(ct, cg)
    resp = out["resps"][0]
    assert resp["removed"]["torrents"] == ["H2"]  # 重叠不双报
    assert resp["delta"]["torrents"] == []
    # b) 同一 hash 同拍一增一删(H3 自删登记在前, 同拍 qB 又报一增一删)+ 组键预置可解析
    #    -> R5 交叉抵消, 响应不含该 hash 的 upsert/removed
    store.member_to_key["H3"] = ("R:\\D", )  # 组键可解析(组仍在), 不触发 R11 full
    h3 = FakeTorrent(hash="H3", name="Show.H3.S01E01.720p.x264-GRP")
    patch = {f: getattr(h3, f) for f in REQUIRED_TORRENT_FIELDS if hasattr(h3, f)}
    store._pending_removed.add("H3")
    added, removed = store._apply({"H3": patch}, ["H3"], full=False)
    assert added == ["H3"] and removed == ["H3"]  # 待报删除与增量 removed 重叠去重
    assert store._pending_removed == set()  # 对齐时序: 报过即清
    entry = m.publish()
    assert "H3" not in entry["upsert"]["torrent"] and "H3" not in entry["removed"]["torrent"]
    out = m.sync(ct, cg)
    resp = out["resps"][0]
    assert resp["full"] is False
    assert resp["delta"]["torrents"] == [] and resp["removed"]["torrents"] == []


# ---------- M5: HR revision 波次 -> full(02 笔记 2.5.3) ----------


def test_m5_hr_revision_wave_yields_full():
    store, rt, m, ct, cg = _mirror(("H1", ))
    rt._host.hr = SimpleNamespace(revision=7)  # 重建基线仍为 None -> 下一拍判不等
    rt.mark_dirty()
    m.publish()
    assert rt._delta_timeline[-1]["full"] is True  # HR revision 波次 -> 本代 full(R11)
    out = m.sync(ct, cg)
    for c, resp in zip((ct, cg), out["resps"]):  # R10: full 响应不含 delta/removed 键
        assert resp["full"] is True
        assert {"torrent": "torrents", "group": "groups"}[c.view] in resp
        assert "delta" not in resp and "removed" not in resp
    # 波次回落: revision 未再变(基线已随重建前移)-> 下一拍恢复行级增量
    _beat(store, "H1", dlspeed=500)
    m.publish()
    out = m.sync(ct, cg)
    resp = out["resps"][0]
    assert resp["full"] is False
    assert [r["hash"] for r in resp["delta"]["torrents"]] == ["H1"]
    assert resp["delta"]["torrents"][0]["dlspeed"] == 500


# ---------- 无键 dirty 源(R11 缺口, S3 观察) ----------


def test_unkeyed_command_source_yields_full():
    # a) 命令自写字段: QbApi Facade -> store.update_torrent_fields 原地写 state, 只置
    #    view_changed, 无 last_added/last_removed/delta_fields —— 修复前落代为「空键集且
    #    full=False」, delta 客户端漏变更(命令轮真值要等下轮 qB 增量才可见)
    store, rt, m, ct, cg = _mirror(("H1", "H2"))
    store.update_torrent_fields("H1", state="pausedUP")
    assert not store.last_added and not store.last_removed and not store.delta_fields  # 前置: 无键
    m.publish(force=True)  # 命令驱动轮: force 绕过门控(P0-5)
    assert rt._delta_timeline[-1]["full"] is True  # 纯命令源 -> 本代 full(R11)
    out = m.sync(ct, cg)
    resp = out["resps"][0]
    assert resp["full"] is True
    row = next(r for r in resp["torrents"] if r["hash"] == "H1")
    assert row["state"] == "pausedUP"  # full 重放即见真值
    # 对照(别误伤): store 驱动的常规轮照常行级增量, 不被误降 full
    _beat(store, "H2", dlspeed=700)
    m.publish()
    out = m.sync(ct, cg)
    assert rt._delta_timeline[-1]["full"] is False
    assert [r["hash"] for r in out["resps"][0]["delta"]["torrents"]] == ["H2"]

    # b) reset_runtime: 清分组索引 + 置 view_changed, 同样无键 —— 组行消失/成员回 singles,
    #    行键不可推导 -> 必须 full, 否则 B 组行残留 + H1 单行缺失(镜子必红)
    store2 = _make_store("H1", "H2")
    store2.member_to_key["H1"] = ("R:\\D", )
    store2.groups[("R:\\D", )] = ["H1"]
    rt2 = _delta_runtime(store2)
    m2 = Mirror(store2, rt2)
    ct2, cg2 = DeltaClient("torrent"), DeltaClient("group")
    rt2.mark_dirty()
    m2.publish()
    m2.sync(ct2, cg2)  # 基线含组行
    store2.reset_runtime()
    assert not store2.groups and not store2.member_to_key  # 前置: 分组索引已清空
    m2.publish(force=True)
    assert rt2._delta_timeline[-1]["full"] is True
    m2.sync(ct2, cg2)  # 修复前此处红: B 合并结果 != A 全量快照


# ---------- M6: 重启 ver 播种 -> 旧 rid 窗外 full ----------


def test_m6_restart_ver_seeding_old_rid_full():
    store = _make_store("H1", "H2")
    rt = _delta_runtime(store)
    m = Mirror(store, rt)
    ct, cg = DeltaClient("torrent"), DeltaClient("group")
    rt.mark_dirty()
    m.publish()
    m.sync(ct, cg)
    _beat(store, "H1", dlspeed=100)
    m.publish()
    m.sync(ct, cg)  # 旧进程两代, 旧客户端持 gen2
    old_rid = ct.rid
    # 重启: 全新运行时, ver 以进程启动时间播种(测试用 mock 前移播种钟点, 保证旧 rid 必然窗外);
    # 真实重启 store 同样全新 —— 此处清掉 S1「最近一轮」残值模拟「首轮全量 sync 前无快照」
    future = int(time.time()) + 100
    host = rt._host
    with mock.patch("auto_qb.webui.runtime.time") as ft:
        ft.time.return_value = future
        rt2 = WebUIRuntime(host)
    host.web = rt2  # 构建器 note_cross_keys 接线切到新运行时
    rt2.touch()
    store.last_added = []
    store.last_removed = []
    store.delta_fields = {}
    assert len(rt2._delta_timeline) == 0  # 时间线归零(进程重启)
    assert rt2._delta_pending["upsert"]["torrent"] == set()  # 累积器归零
    m2 = Mirror(store, rt2)
    rt2.mark_dirty()
    e1 = m2.publish()
    assert e1["ver"] == future + 1 and e1["ver"] > old_rid  # 时间播种不回落, 旧 rid 必然窗外
    # 旧客户端按旧 rid 拿增量 -> 窗外退化全量(R10), 全量重放后 ≡ A
    out = m2.sync(ct, cg)
    for resp in out["resps"]:
        assert resp["full"] is True and "delta" not in resp and "removed" not in resp
    assert set(ct.rows["torrents"]) == {r["hash"] for r in out["full"]["torrents"]}
    assert set(cg.rows["groups"]) == {r["key"] for r in out["full"]["groups"]}
    # 对照: 重启后新一轮变化, 旧客户端照常行级增量(rid 已追平新 ver)
    _beat(store, "H2", dlspeed=200)
    m2.publish()
    out = m2.sync(ct, cg)
    assert out["resps"][0]["full"] is False
    assert [r["hash"] for r in out["resps"][0]["delta"]["torrents"]] == ["H2"]


# ---------- M7: 窗口滑出 / rid>ver -> full ----------


def test_m7_window_slide_out_and_rid_ahead_full():
    store, rt, m, ct, cg = _mirror(("H1", "H2"))
    # 41 代未被 ct/cg 消费: maxlen=40 把客户端所在代挤出时间线
    for i in range(41):
        _beat(store, "H1", dlspeed=100 + i)
        m.publish()
        m.sync()  # 仅 A 快照消费(维持生产节拍), ct/cg 缺席
    assert len(rt._delta_timeline) == 40
    assert rt._delta_timeline[0]["ver"] > ct.rid  # 前置: 客户端 rid 已窗外
    out = m.sync(ct, cg)  # 窗口滑出 -> 全量(R10), 重放补齐后 ≡ A
    for resp in out["resps"]:
        assert resp["full"] is True and "delta" not in resp and "removed" not in resp
    assert set(ct.rows["torrents"]) == {"H1", "H2"}
    # rid > ver(时钟倒挂): 直接持未来 rid 请求 -> 全量(R3 数值区间比较)
    ahead = rt.ensure_state(rt.group_view_ver + 5, "torrent", True)
    assert ahead["full"] is True and "torrents" in ahead
    assert "delta" not in ahead and "removed" not in ahead


# ---------- M8: show 视图请求恒 full(S9 前的启用矩阵) ----------


def test_m8_show_view_always_full():
    store, rt, m, ct, cg = _mirror(("H1", "H2"))
    _beat(store, "H1", dlspeed=100)
    m.publish()  # 窗口内有带键集的代: 若启用矩阵放行本可归约
    rid = rt.group_view_ver - 1
    for view, arrays in (
        ("show", {"shows", "groups", "singles"}),
        (None, {"groups", "singles", "shows", "torrents"}),
        ("nope", {"groups", "singles", "shows", "torrents"}),
    ):
        state = rt.ensure_state(rid, view, True)
        assert state["full"] is True
        assert {k for k in state if k in ("shows", "groups", "singles", "torrents")} == arrays
        assert "delta" not in state and "removed" not in state
        assert state["rid"] == rt.group_view_ver
        assert state["updated"] is True


# ---------- M9: 门控跳拍累积(端到端镜子版, R4) ----------


def test_m9_gate_skipped_rounds_end_to_end():
    store, rt, m, ct, cg = _mirror(("H1", "H2"))
    # 三拍连续变化: 只有第一拍落代(gen2), 后两拍因「上一版未被取走」被门控跳过
    _beat(store, "H1", dlspeed=100)
    e2 = m.publish()
    assert e2["upsert"]["torrent"] == {"H1"}
    _beat(store, "H2", state="pausedUP")
    m.publish()
    _beat(store, "H1", upspeed=50)
    m.publish()
    assert len(rt._delta_timeline) == 2  # 跳拍未产生新代
    assert rt._delta_pending["upsert"]["torrent"] == {"H1", "H2"}  # 键集暂存累积器
    # 恢复消费: ensure_state 触发落代, 累积键集并入下一代不丢(R4)
    out = m.sync(ct, cg)
    assert len(rt._delta_timeline) == 3
    resp = out["resps"][0]
    assert resp["full"] is False
    assert {r["hash"] for r in resp["delta"]["torrents"]} == {"H1", "H2"}
    row = next(r for r in resp["delta"]["torrents"] if r["hash"] == "H1")
    assert row["dlspeed"] == 100 and row["upspeed"] == 50  # 三拍变化一轮拿齐
    row2 = next(r for r in resp["delta"]["torrents"] if r["hash"] == "H2")
    assert row2["state"] == "pausedUP"


# ---------- fuzz: 固定种子随机操作序列 ----------


def test_fuzz_random_operation_sequence():
    """固定种子(random.Random(20261007))随机操作序列 N=220 轮, 每轮断言 B ≡ A

    操作池覆盖 M1-M9 全部形态: 真脏字段/量化字段(含桶内不可见跳动)、增/删(含待报删除
    重叠)/同拍一增一删、命令无键源(R11 full)、HR 波次、门控跳拍(随机 1-3 拍不消费)。
    跑一次全绿为准, 不追求极限压测。
    """
    rng = random.Random(20261007)
    store = _make_store("H1", "H2", "H3")
    rt = _delta_runtime(store)
    m = Mirror(store, rt)
    ct, cg = DeltaClient("torrent"), DeltaClient("group")
    rt.mark_dirty()
    m.publish()
    m.sync(ct, cg)
    add_counter = itertools.count(100)
    states = ["stalledUP", "pausedUP", "downloading", "uploading", "stoppedUP"]

    def rand_hash():
        return rng.choice(sorted(store.client.torrents))

    def op_field():  # 真脏字段(qB 增量路径)
        h = rand_hash()
        f = rng.choice(["dlspeed", "upspeed", "seeding_time", "tags", "state"])
        v = {
            "dlspeed": rng.randint(0, 10**7),
            "upspeed": rng.randint(0, 10**7),
            "seeding_time": rng.randint(0, 10**6),
            "tags": ",".join(rng.sample(["a", "b", "c"], rng.randint(0, 2))),
            "state": rng.choice(states),
        }[f]
        _beat(store, h, **{f: v})

    def op_jitter():  # 量化字段(扩展字段不上线, 按 qB patch 形态直喂 _apply; 桶内跳动常不可见)
        h = rand_hash()
        f = rng.choice(["last_activity", "eta", "seeding_time", "time_active"])
        cur = max(0, getattr(store.by_hash[h], f))
        new = cur + rng.choice([rng.randint(0, 59), 60 + rng.randint(0, 59)])
        store._apply({h: {f: new}}, [], full=False)

    def op_add():
        h = f"H{next(add_counter)}"
        store.client.torrents[h] = FakeTorrent(hash=h, name=f"Show.{h}.S01E01.720p.x264-GRP", state=rng.choice(states))
        if rng.random() < 0.5:  # 入库即归组: added 的组键在排空点可推导
            key = (f"R:\\G{rng.randint(1, 3)}", )
            store.member_to_key[h] = key
            store.groups.setdefault(key, []).append(h)
        store.apply_sync(QbApi(store.client, store))

    def op_remove():
        hs = sorted(store.client.torrents)
        if len(hs) <= 1:
            return
        h = rng.choice(hs)
        store.client.torrents.pop(h)
        if rng.random() < 0.5:  # 自删登记在前: 待报删除与增量 removed 重叠
            store.remove_torrent(h)
        store.apply_sync(QbApi(store.client, store))

    def op_same_tick():  # 同拍一增一删(M4b 形态; 组键解析与否随机 -> 归约/防御 full 两路都过)
        h = f"H{next(add_counter)}"
        if rng.random() < 0.5:
            store.member_to_key[h] = (f"R:\\G{rng.randint(1, 3)}", )
        tor = FakeTorrent(hash=h, name=f"Show.{h}.S01E01.720p.x264-GRP")
        patch = {f: getattr(tor, f) for f in REQUIRED_TORRENT_FIELDS if hasattr(tor, f)}
        if rng.random() < 0.5:
            store._pending_removed.add(h)
        store._apply({h: patch}, [h], full=False)

    def op_unkeyed():  # 命令无键源 -> 本代 full(R11)
        h = rand_hash()
        pick = rng.random()
        if pick < 0.4:
            store.update_torrent_fields(h, state=rng.choice(states))
        elif pick < 0.7:
            store.update_torrent_fields(h, tags_add=rng.sample(["x", "y", "z"], rng.randint(1, 2)))
        else:
            store.update_torrent_fields(h, category=f"cat{rng.randint(0, 2)}")

    def op_hr():  # HR revision 波次 -> 本代 full(R11)
        hr = getattr(rt._host, "hr", None)
        if hr is None:
            rt._host.hr = SimpleNamespace(revision=1)
        else:
            hr.revision += 1

    ops = [op_field] * 3 + [op_jitter] * 2 + [op_add] * 2 + [op_remove, op_same_tick, op_unkeyed, op_hr]
    for _ in range(220):
        rng.choice(ops)()
        for _ in range(rng.randint(0, 2)):  # 门控跳拍: 未消费的发布(无变化轮则不落代)
            m.publish()
        m.publish()
        m.sync(ct, cg)  # 每轮断言 B ≡ A
    assert len(rt._delta_timeline) <= 40  # 时间线上限守卫
    assert store.client.torrents  # 增删随机游走后库非空(操作池自检)
