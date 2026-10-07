"""test_webui_delta_mirror 测试计划: WebUI 增量同步镜子测试(plan 26-10-07-0414 S5)

镜子不变量(§02 总纲): 任意操作序列下「从 rid0 逐轮吃 delta 合并(B 通道)」≡「每轮全量快照
(A 通道)」。A 通道 = 每轮 ensure_state(rid=0) 拿全量四数组; B 通道 = S4 前端合并
(polling.js applyStateRows)的 Python 复刻 —— delta 轮行级 upsert(整行替换/追加, R8)+
removed 剔除, full 轮(payload.full 非 False, 含未协商形状)清空重放(R6); 行内容 JSON 深拷贝
落袋(前端持有自有副本的语义)。每轮断言 B ≡ A: 按行键集合 + 行内容逐字段, 不比数组顺序
(S4 顺序安全事实)。

## 测试计划(每个测试函数一条; M1-M5 + 无键 dirty 源本步, M6-M9 + fuzz 归后继步 S5a')
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
"""
import json
from types import SimpleNamespace

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
