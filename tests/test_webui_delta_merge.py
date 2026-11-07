"""test_webui_delta_merge 测试计划: WebUI 增量时间线(plan 26-10-07-0414 S2/S3)

被测面: WebUIRuntime 的时间线落代(_fold_delta_pending_locked)/store 增量排空与脏行键推导
(_drain_delta_locked)/full 降级理由集合(R11 五源 + S9b show_unrecognized)/views._build_group_view
的构建期交叉键回传(S2); ensure_state 的 delta 协商门控与 _reduce_delta 归约判定矩阵 + 增量协议
字段(S3); 剧键等价映射与迁移候选暂存(S8, S9b 起暂存在落代段并入 show 桶); S9a 单剧可调用等价
(views._build_show_row 纯重构守阵); S9b show 视图解锁(时间线 show 桶推导/局部重聚合/show 归约)。

## 测试计划(每个测试函数一条)
- test_s6_partial_rebuild_reference_stability: S6 引用稳定不变量 —— 局部重聚合后未脏行对象引用原样保留(is 恒等), 脏行必然新对象; 组行整行新对象且内嵌 members 随行重建(P-02 一期口径), 组外平铺行引用不动; removed 键(组员删除/组解散)直接从视图剔除
- test_s6_partial_rows_equal_full_rebuild: S6 逐字段一致性 —— 混合序列(未归组变化/组员变化/新增归组/组员删除)逐代局部重聚合后, 发布视图与全量重跑逐行逐字段相等(含脏组行 == 全量重跑该行); 每代走局部路径的判据(条目 full=False 且键集非空)随行断言
- test_s6_solo_member_group_removal_no_stale_row: S6 补 —— 独成员组且组条目未清理的桩态下删除成员(组键仍可解析路由 g_up): 组行重建为空(_build_group_row 回 None)-> 组键转 removed 剔除旧行, 局部产物 == 全量重建(修复前旧行残留); 子场景: 重建候选旧行本不在视图 -> 键原样保留 upsert(S2 排空契约, 缺行防御 full 兜底); 对照: 多成员组删单员照常重建(test_s6_partial_rebuild_reference_stability c 钉住)
- test_s8_added_hash_registered_without_candidates: S8 新增登记 —— added hash(真增量轮) -> 映射登记; 无旧键 -> 不产生迁移候选
- test_s8_restart_backfill_without_candidates: S8 重启回填 —— 新 runtime 映射为空, 首拍全量(空键集代走全量路径)全库回填且不产生迁移候选; 映射非空的后继全量代不重置既有映射(回填幂等)
- test_s9a_show_row_callable_matches_full_view: S9a 单剧可调用等价(纯重构守阵) —— 库态覆盖四边界落位(季级 gaps/covered 含索引兑底 range 与整包 has_pack、剧名频次众数、集行状态 _SHOW_STATE_RANK 归并、unrecognized 折叠)+ 日期型 None 季桶/pending 接线; _build_show_row(剧键, 独立重放分类的成员集) == 全量 _build_shows_view 同剧行递归逐字段; 空成员 -> None(_build_group_row 空组口径)
- test_s9b_show_partial_rebuild_equal_and_reference_stable: S9b 局部重聚合(正确性边界 1-4 落位) —— 脏剧键整行重建与全量重跑逐行逐字段相等(频次众数/季级 gaps/状态归并/members), 未脏剧行引用原样、脏剧行必然新对象; 成员增/删(组键可解析)/迁移旧键清空转 removed/新剧追加尾部; 静止未识别种子(电影)速度抖动不触发折叠面 full
- test_s9b_show_unrecognized_downgrade_full: S9b 折叠面降级(R11) —— 未识别种子新增/改名进未识别区/删除 -> 本代 full 且下一拍恢复行级增量; 对照: 未识别种子字段抖动(分类不变)不触发 full
- test_merge_rows_single_point_semantics: _merge_rows 合并骨架单点(issue 26-10-11-0309 认领修) —— removed 键剔除/脏行换新对象/未脏行同一 dict 原样复用/新增行追加尾部; key_field 参数化(hash 键空间); pop 清空无二次消费
- test_publish_partial_merge_skeleton_single_point: 静态守阵 —— _publish_partial_locked 四段合并只走 _merge_rows 单点(4 调用点), 内联骨架(.pop(k) if k in 形态)零残留, 单点内恰一份
### T2a 覆盖率第三轮: HR 基线竞态弧与兑底登记不重投
- test_publish_hr_baseline_holds_when_revision_moves_mid_build: 局部重建期间 HR revision 被并发发布抬高(确定性收束替身) -> 基线保留旧值不前移, 下一拍 flush 波次判定补一次 full, 前移后不循环置脏
- test_show_partial_pending_without_index_coverage_does_not_repost_command: 局部剧重建兑底登记(季包索引未覆盖 -> shows_pending); 索引已建成且无脏 -> 不重复投递 build_search_index
### T2a2 覆盖率第三轮: 剧视图余下小件
- test_agg_show_node_hr_counts_and_show_row_empty_title: _agg_show_node 的 HR 计数分支(触发计数/未达标 pending 两弧)与 _build_show_row 空标题成员分支(titles 不累加, 展示名回落剧键)直驱
- test_build_shows_view_row_none_guard_and_pending_no_repost: _build_shows_view 行剔除防御弧(单剧可调用回 None -> 行不进视图, 确定性替身直驱)与全量路径 pending 兑底接线(索引已建成且无脏 -> 只登记 shows_pending 不重投 build_search_index)
### issue 26-11-07-0536 批A
- test_ensure_state_publish_hr_wave_lands_full_timeline_entry: ensure_state 触发的发布检出 hr_wave(flush 判定点后 HR worker 才推进 revision, 门控又推迟了重建)-> 发布路径登记 hr_revision 理由, fold 落 full=True 条目(修复前 full=False 且键集仅 store 增量键, HR 派生字段变更不进时间线); 理由随落代清空、基线前移不循环
- test_publish_partial_group_members_by_hash_probe_index_race: 局部重聚合组段成员取值改单步 by_hash.get —— 确定性替身(dict 子类)把主循环 pop 钉在「in 判定」与「下标取值」之间(修复前 KeyError 使请求 500), 局部路径照常完成且组行按当刻快照完整重建
"""

import inspect

import json

import time

from collections import deque

from types import SimpleNamespace

from auto_qb.core import tvshows

from auto_qb.core.qbapi import QbApi

from auto_qb.infra.utils import encode_group_key

from auto_qb.webui import WebUIRuntime

from auto_qb.webui.views import WebviewMixin

from helpers import FakeTorrent, FakeTracker

from webui_helpers import make_store

from webui_delta_support import (
    _S8_NAME,
    _ViewHost,
    _beat,
    _delta_runtime,
    _publish,
    _s8_baseline,
)


def _rows_by(view, keyf):
    return {r[keyf]: r for r in view}


def test_s6_partial_rebuild_reference_stability():
    """S6 引用稳定不变量: 局部重聚合后未脏行对象引用原样保留(is 恒等), 脏行必然新对象

    前端 S7 按行对象身份的 WeakMap 记忆化依赖: 引用稳定**只对未脏行**承诺, 脏行新对象
    自然 miss 重算。组行内嵌 members 数组随组行整行走(P-02 一期口径, R8)。
    """
    store = make_store("H1", "H2", "H3", "H4")
    # H3/H4 归组, H1/H2 未归组(归组登记须在基线发布前, 同镜子 M4 前置口径)
    store.member_to_key["H3"] = ("R:\\D", )
    store.member_to_key["H4"] = ("R:\\D", )
    store.groups[("R:\\D", )] = ["H3", "H4"]
    rt = _delta_runtime(store)
    rt.mark_dirty()
    entry = _publish(rt)  # 基线代: 空键集 -> 全量路径
    assert entry["full"] is False and entry["upsert"]["torrent"] == set()
    flat0 = _rows_by(rt.flat_view, "hash")
    singles0 = _rows_by(rt.singles_view, "hash")
    groups0 = _rows_by(rt.group_view, "key")
    gkey = encode_group_key(("R:\\D", ))
    assert set(singles0) == {"H1", "H2"} and set(groups0) == {gkey}

    # a) 未归组脏行: H1 变速 -> singles/flat 的 H1 行新对象且内容更新, H2 行引用原样;
    #    组行未脏 -> 引用原样
    _beat(store, "H1", dlspeed=1024)
    entry = _publish(rt)
    assert entry["full"] is False and entry["upsert"]["torrent"] == {"H1"}  # 走了局部路径
    flat1, singles1 = _rows_by(rt.flat_view, "hash"), _rows_by(rt.singles_view, "hash")
    assert flat1["H1"] is not flat0["H1"] and flat1["H1"]["dlspeed"] == 1024  # 脏行必然新对象
    assert singles1["H1"] is not singles0["H1"] and singles1["H1"]["dlspeed"] == 1024
    assert flat1["H2"] is flat0["H2"] and singles1["H2"] is singles0["H2"]  # 未脏行引用原样
    assert flat1["H3"] is flat0["H3"] and flat1["H4"] is flat0["H4"]
    assert _rows_by(rt.group_view, "key")[gkey] is groups0[gkey]

    # b) 组内成员脏 -> 组行整行新对象(members 随行整体重建), 组外平铺行引用不动:
    #    H4 平铺行未脏仍旧对象, 组行内 H4 成员视图是新 dict(只活在组行内, P-02 口径)
    _beat(store, "H3", dlspeed=2048)
    entry = _publish(rt)
    assert entry["full"] is False and entry["upsert"]["torrent"] == {"H3"}
    flat2, groups2 = _rows_by(rt.flat_view, "hash"), _rows_by(rt.group_view, "key")
    assert groups2[gkey] is not groups0[gkey]  # 脏组行必然新对象
    assert [m["dlspeed"] for m in groups2[gkey]["members"]] == [2048, 0]
    assert flat2["H3"] is not flat1["H3"] and flat2["H3"]["dlspeed"] == 2048
    assert flat2["H4"] is flat1["H4"] and flat2["H1"] is flat1["H1"] and flat2["H2"] is flat1["H2"]
    assert _rows_by(rt.singles_view, "hash")["H1"] is singles1["H1"]

    # c) removed 键剔除: 组员 H4 删除(组仍在)-> 平铺行消失, 组行重建, 其余行引用原样
    store.client.torrents.pop("H4")
    store.apply_sync(QbApi(store.client, store))
    entry = _publish(rt)
    assert entry["full"] is False  # 组键可解析: 非降级源, 走局部路径
    assert entry["removed"]["torrent"] == {"H4"} and entry["upsert"]["group"] == {("R:\\D", )}
    flat3, groups3 = _rows_by(rt.flat_view, "hash"), _rows_by(rt.group_view, "key")
    assert "H4" not in flat3
    assert flat3["H1"] is flat2["H1"] and flat3["H2"] is flat2["H2"] and flat3["H3"] is flat2["H3"]
    assert groups3[gkey] is not groups2[gkey]
    assert groups3[gkey]["count"] == 1 and [m["hash"] for m in groups3[gkey]["members"]] == ["H3"]

    # d) 组解散: 末位成员删除 -> 组键进 removed, 组行从视图剔除(全量构建不产空组行, 产物对齐)
    store.groups.pop(("R:\\D", ))  # 模拟 grouping_mod._leave_group 的解散清除(成员键保留可解析)
    store.client.torrents.pop("H3")
    store.apply_sync(QbApi(store.client, store))
    entry = _publish(rt)
    assert entry["full"] is False
    assert entry["removed"]["torrent"] == {"H3"} and entry["removed"]["group"] == {("R:\\D", )}
    assert _rows_by(rt.group_view, "key") == {}
    flat4 = _rows_by(rt.flat_view, "hash")
    assert set(flat4) == {"H1", "H2"} and flat4["H1"] is flat3["H1"] and flat4["H2"] is flat3["H2"]


def test_s6_partial_rows_equal_full_rebuild():
    """S6 逐字段一致性: 局部重聚合的构建产物与全量重跑逐行逐字段相等(plan S6 核心不变量)

    混合序列逐代局部重聚合后, 发布视图(未脏行复用旧对象)与全量重跑对照 —— 行键集合 +
    行内容逐字段(不比数组顺序); 另断言脏组行 == 单组可调用全量重跑该行。
    """
    store = make_store("H1", "H2", "H3")
    store.member_to_key["H1"] = ("R:\\D", )
    store.member_to_key["H2"] = ("R:\\D", )
    store.groups[("R:\\D", )] = ["H1", "H2"]
    rt = _delta_runtime(store)
    host = rt._host
    rt.mark_dirty()
    _publish(rt)  # 基线代(全量路径)
    gkey_d, gkey_e = encode_group_key(("R:\\D", )), encode_group_key(("R:\\E", ))
    for gen in range(4):
        if gen == 0:
            _beat(store, "H3", dlspeed=11)  # 未归组行
        elif gen == 1:
            _beat(store, "H2", dlspeed=22, state="pausedUP")  # 组员(组行 + 平铺行双脏)
        elif gen == 2:  # 新增种子入库即归新组(新组行 + 新平铺行)
            store.client.torrents["H4"] = FakeTorrent(hash="H4", name="Show.H4.S01E01.720p.x264-GRP")
            store.member_to_key["H4"] = ("R:\\E", )
            store.groups[("R:\\E", )] = ["H4"]
            store.apply_sync(QbApi(store.client, store))
        else:  # 组员删除(组仍在 -> 组行重建, 平铺行剔除)
            store.client.torrents.pop("H1")
            store.apply_sync(QbApi(store.client, store))
        entry = _publish(rt)
        assert entry["full"] is False  # 每代都走局部路径(无降级源且键集非空)
        assert entry["upsert"]["torrent"] or entry["removed"]["torrent"]
        # 局部重聚合产物 vs 全量重跑: 三视图逐行逐字段相等(不比数组顺序)
        assert _rows_by(rt.flat_view, "hash") == _rows_by(host._build_flat_view(), "hash")
        assert _rows_by(rt.singles_view, "hash") == _rows_by(host._build_singles_view(), "hash")
        assert _rows_by(rt.group_view, "key") == _rows_by(host._build_group_view(), "key")
    # 脏组行 == 单组可调用全量重跑该行(「同一组键局部重算结果 == 全量重算结果」直测)
    row = _rows_by(rt.group_view, "key")[gkey_d]
    assert row == host._build_group_row(("R:\\D", ), [store.by_hash["H2"]], set())
    assert _rows_by(rt.group_view, "key")[gkey_e] == host._build_group_row(("R:\\E", ), [store.by_hash["H4"]], set())
    assert row["cross_group_conflict"] is False and row["count"] == 1


def test_s6_solo_member_group_removal_no_stale_row():
    """S6 补: 独成员组且组条目未清理的桩态下删除成员 —— 组键仍可解析路由 g_up, 组行重建
    为空(_build_group_row 回 None)-> 组键转 removed 剔除旧行, 局部产物 == 全量重建

    修复前: None 行被静默跳过, 时间线记 upsert(行内容取自残留在视图的旧行), 局部 != 全量
    (全量构建不产空组行), 增量客户端永远持有幽灵组行。子场景: 重建候选旧行本不在任何已
    发布代 -> 键**原样保留**在 upsert(S2 排空契约: 组键推导结果逐字进时间线; 行不存在由
    归约缺行防御性 full 兜住)。对照: 多成员组删单员照常重建非 removed —— 由
    test_s6_partial_rebuild_reference_stability c) 钉住(row 非 None 分支不挪键)。
    """
    store = make_store("H1", "H2")
    store.member_to_key["H1"] = ("R:\\D", )
    store.groups[("R:\\D", )] = ["H1"]
    rt = _delta_runtime(store)
    rt.mark_dirty()
    _publish(rt)  # 基线: 组行在视图
    gkey = encode_group_key(("R:\\D", ))
    assert [r["key"] for r in rt.group_view] == [gkey]

    # a) 本体: 独成员删除(组条目仍列 H1 的桩态, 未经 _leave_group 清理)-> 组行消失转 removed
    store.client.torrents.pop("H1")
    store.apply_sync(QbApi(store.client, store))
    entry = _publish(rt)
    assert entry["full"] is False  # 组键可解析: 非 R11 降级, 走局部路径
    assert entry["removed"]["torrent"] == {"H1"}
    assert entry["upsert"]["group"] == set()  # 重建为空: 候选撤下
    assert entry["removed"]["group"] == {("R:\\D", )}  # 旧行剔除进时间线(修复前残留在视图)
    assert rt.group_view == []  # 局部产物无残留
    assert rt.group_view == rt._host._build_group_view()  # == 全量重建(逐行逐字段)

    # b) 重建候选旧行本不在视图(组条目只列已灭 hash, 从未入任何已发布代)-> 键原样保留
    # 在 upsert(S2 排空契约), 行不存在由归约缺行防御性 full 兜住(无残留面: 行退出视图
    # 必有 removed 记录, 客户端不可能持有)
    store.member_to_key["HX"] = ("R:\\Z", )
    store.groups[("R:\\Z", )] = ["HX"]  # HX 不在 by_hash
    store.last_removed = ["HX"]
    rt.mark_dirty()
    entry = _publish(rt)
    assert entry["full"] is False
    assert entry["upsert"]["group"] == {("R:\\Z", )} and entry["removed"]["group"] == set()
    assert rt.group_view == rt._host._build_group_view()


def test_merge_rows_single_point_semantics():
    """_merge_rows 合并骨架单点契约: removed 键剔除 / 脏行换新对象 / 未脏行同一 dict 原样
    复用 / 新增行追加在尾部 —— 四段(groups/singles/flat/shows)共用的引用稳定契约直测

    前端 S7 按行对象身份的 WeakMap 记忆化依赖「未脏行 is 恒等」: 该契约此前靠 S6 端到端
    用例间接守, 抽单点后在此钉住合并语义本身(与四段各自内联时逐字一致)。
    """
    old_a, old_b, old_c = {"key": "a"}, {"key": "b"}, {"key": "c"}
    new_b, new_d = {"key": "b", "v": 2}, {"key": "d"}
    rebuilt = {"b": new_b, "d": new_d}
    merged = WebUIRuntime._merge_rows([old_a, old_b, old_c], "key", rebuilt, {"c"})
    assert merged == [old_a, new_b, new_d]  # 顺序: 旧视图序(跳过 c) + 新增行尾部
    assert merged[0] is old_a  # 未脏行原样复用(引用稳定)
    assert merged[1] is new_b  # 脏行换新对象
    assert rebuilt == {"d": new_d}  # 替换过的键已 pop 清出; 残余(新增行)已 extend 追加尾部, 调用方随后即弃
    # key_field 参数化: singles/flat 段按 hash 键空间合并(组段按 encode 后的 key)
    h1, h2 = {"hash": "h1"}, {"hash": "h2"}
    m = WebUIRuntime._merge_rows([h1, h2], "hash", {"h2": {"hash": "h2", "v": 1}}, {"h1"})
    assert m == [{"hash": "h2", "v": 1}]  # h1 removed 剔除; h2 脏行替换


def test_publish_partial_merge_skeleton_single_point():
    """静态守阵: _publish_partial_locked 四段合并只走 _merge_rows 单点 —— 又抄一份内联
    骨架(`.pop(k) if k in` 形态)即判红(issue 26-10-11-0309 的漂移点复发面)"""
    caller = inspect.getsource(WebUIRuntime._publish_partial_locked)
    assert caller.count("self._merge_rows(") == 4  # groups/singles/flat/shows 四段各一个调用点
    assert ".pop(k) if k in" not in caller  # 调用方内联合并骨架零残留
    helper = inspect.getsource(WebUIRuntime._merge_rows)
    assert helper.count(".pop(k) if k in") == 1  # 骨架在单点里恰一份


class _PopBetweenProbeAndIndex(dict):
    """确定性竞态替身(dict 子类): __contains__ 判真后立即 pop victim —— 把主循环的并发
    删除钉在「in 判定」与「下标取值」两步之间的窗口内(remove_torrent 原地 pop / _apply
    增量轮换代回绑 by_hash, 均不持 view_lock; ensure_state 触发的发布在 Web 线程读)。
    修复后的单步 .get(h) 不再经过 __contains__, 窗口不复存在。"""
    def __init__(self, inner, victim):
        super().__init__(inner)
        self._victim = victim

    def __contains__(self, h):
        has = super().__contains__(h)
        if has and h == self._victim:
            dict.pop(self, h, None)  # 竞态窗口: 判真后主循环 pop 落地
        return has


def test_publish_partial_group_members_by_hash_probe_index_race():
    """issue 26-11-07-0536 #3: 局部重聚合组段成员取值改单步 get —— 「in 判定 + 下标取值」
    两步之间主循环 pop 该 hash 时 KeyError 使请求 500。确定性替身把 pop 钉在两步之间;
    行为等价面: 与 singles/flat 段同款按当刻快照取值, 本代局部路径照常完成不降级"""
    store = make_store("H1", "H2")
    store.member_to_key["H1"] = ("R:\\D", )
    store.member_to_key["H2"] = ("R:\\D", )
    store.groups[("R:\\D", )] = ["H1", "H2"]
    rt = _delta_runtime(store)
    rt.mark_dirty()
    _publish(rt)  # 基线代: 组行在视图
    _beat(store, "H1", dlspeed=321)
    store.by_hash = _PopBetweenProbeAndIndex(store.by_hash, "H1")
    entry = _publish(rt)  # 修复前: in 判真后下标取值踩空 -> KeyError
    assert entry["full"] is False  # 竞态不炸也不降级: 本代仍走局部路径
    gkey = encode_group_key(("R:\\D", ))
    row = _rows_by(rt.group_view, "key")[gkey]
    assert [m["hash"] for m in row["members"]] == ["H1", "H2"]  # 单步 get 按当刻快照完整重建
    assert [m["dlspeed"] for m in row["members"]] == [321, 0]


def test_s8_added_hash_registered_without_candidates():
    """S8 新增登记: added hash(真增量轮) -> 映射登记; 无旧键 -> 不产生迁移候选"""
    store, rt, keys = _s8_baseline("H1")
    store.client.torrents["H2"] = FakeTorrent(hash="H2", name=_S8_NAME.format("H2"))
    store.apply_sync(QbApi(store.client, store))
    rt.mark_dirty()
    _publish(rt)
    assert rt._show_member_keys == {"H1": keys["H1"], "H2": tvshows.parse_release(_S8_NAME.format("H2")).key}
    assert rt._pending_show_migrations == {"upsert": set(), "removed": set()}


def test_s8_restart_backfill_without_candidates():
    """S8 重启回填: 新 runtime 映射空, 首拍全量(空键集代走全量路径)全库回填且不产生迁移候选"""
    store, rt, keys = _s8_baseline("H1", "H2")
    rt2 = WebUIRuntime(rt._host)  # 进程内重启观察面(同 test_full_downgrade_sources_matrix e 口径)
    rt2.touch()
    assert rt2._show_member_keys == {}  # 重启后映射空
    rt._host.web = rt2  # 发布路径 _build_shows_view/note_cross_keys 经 host.web 接线
    rt2.mark_dirty()
    entry = _publish(rt2)  # 首拍: 无键集 -> 全量路径 -> 回填
    assert entry["upsert"]["show"] == set() and entry["removed"]["show"] == set()  # show 桶恒空(M8)
    assert rt2._show_member_keys == {"H1": keys["H1"], "H2": keys["H2"]}
    assert rt2._pending_show_migrations == {"upsert": set(), "removed": set()}  # 回填纯登记无候选
    # 回填幂等: 映射非空的后继全量代(config_reload 降级)不重置既有映射
    rt2.mark_dirty(full=True, reason="config_reload")
    _publish(rt2)
    assert rt2._show_member_keys == {"H1": keys["H1"], "H2": keys["H2"]}


def test_s9a_show_row_callable_matches_full_view():
    """S9a 单剧可调用等价: _build_show_row(剧键, 成员集) == 全量 _build_shows_view 同剧行逐字段

    全量路径已改为「分类分桶 -> 逐剧调用」(plan 26-10-07-0414 S9a), 本用例两头钉:
    ①边界语义不因搬动走样 —— 季级 gaps/covered(索引兑底 range + 整包 has_pack)、
    剧名频次众数、集行状态 _SHOW_STATE_RANK 归并、unrecognized 折叠、日期型 None 季桶、
    pending 接线; ②单剧可调用只凭 (剧键, 成员集) 即复现全量该行(无隐式上下文依赖,
    S9b 局部重算的衔接面)。成员集按 tvshows 直算独立重放分类(不走 _parse_show_member),
    防同源互证。
    """
    store = make_store()  # 空库起步, 逐颗装异形命名种子(覆盖各解析分支)
    client = store.client
    spec = {
        # 同剧异写("Show.Name"/"SHOW NAME" 同键异题): 频次 2:1 -> 展示名取众数
        "HA": dict(name="Show.Name.S01E05.1080p.WEB-DL", state="downloading", added_on=1700000123),
        "HB": dict(name="SHOW NAME S01E05.720p.HDTV", state="pausedUP"),  # 与 HA 同集行: 状态归并
        "HC": dict(name="Show.Name.S01E07.1080p", state="stalledUP"),
        "HP": dict(name="Show.Name.S01.Complete.1080p", state="stalledUP"),  # 索引兑底 -> range 1-4
        "HQ": dict(name="Show.Name.S02.Complete.1080p", state="stalledUP"),  # 索引未覆盖 -> pack(pending)
        "HD": dict(name="Show.Name.2026.09.15.1080p.WEB.h264", state="stalledUP"),  # 日期型 -> None 季桶
        "HE": dict(name="Another.Show.S01E01.1080p", state="stalledUP"),  # 另一部剧: 分桶不串
        "HF": dict(name="Some.Movie.2023.1080p.BluRay.x265", state="stalledUP"),  # 未识别折叠
    }
    for h, kw in spec.items():
        client.torrents[h] = FakeTorrent(hash=h, **kw)
    store.apply_sync(QbApi(client, store))
    store.last_added = []
    store.last_removed = []
    store.delta_fields = {}
    store.consume_view_changed()

    rt = _delta_runtime(store)
    rt.search_index = {  # HP 有文件(兑底展开集数), HQ 刻意不覆盖(pending 接线)
        "HP": {"name": spec["HP"]["name"], "files": [f"Show.S01E0{i}.mkv" for i in range(1, 5)], "files_q": []},
    }

    host = rt._host
    view = host._build_shows_view()
    rows = {row["key"]: row for row in view["list"]}
    show = rows["show name"]
    # ---- 边界语义钉(全量产物本身) ----
    assert view["unrecognized"] == ["HF"], "无剧键种子进未识别折叠, 不进任何剧行"
    assert show["name"] == "Show Name" and rows["another show"]["name"] == "Another Show"
    seasons = {s["season"]: s for s in show["seasons"]}
    assert set(seasons) == {1, 2, None}, "日期型归 None 季桶, 编号季独立"
    assert seasons[1]["gaps"] == [6], "covered={1..4,5,7} -> 缺 E6(季级整季重算)"
    assert seasons[2]["gaps"] == [], "整包覆盖全季: 不提示缺集"
    eps1 = {tuple(e["key"]): e for e in seasons[1]["episodes"]}
    assert set(eps1) == {("ep", 5), ("ep", 7), ("range", 1, 4)}, "季包经文件兑底展开为 range"
    assert eps1[("ep", 5)]["count"] == 2 and eps1[("ep", 5)]["members"] == ["HA", "HB"], "members 数组整体(R8)"
    assert eps1[("ep", 5)]["state"] == "downloading", "集行状态按 _SHOW_STATE_RANK 取 min(downloading<paused)"
    assert seasons[None]["episodes"][0]["key"] == ["date", "2026-09-15"]
    assert show["member_count"] == 6 and show["episode_count"] == 5
    assert show["latest"] == 1700000123, "剧级 latest = 成员最新 added_on"
    assert rt.shows_pending is True, "HQ 索引未覆盖: 分类层 pending 接线保持"
    # ---- 等价主断言: dict 相等 = 递归逐字段一致 ----
    by_show: dict = {}
    for h, kw in spec.items():
        rec = store.by_hash[h]
        parsed = tvshows.parse_release(rec.name)
        files = (rt.search_index.get(h) or {}).get("files")
        if parsed.kind in (tvshows.KIND_SEASON_PACK, tvshows.KIND_UNKNOWN) and parsed.key and files:
            parsed = tvshows.refine_with_files(parsed, files)
        if parsed.kind == tvshows.KIND_UNKNOWN or not parsed.key:
            continue
        by_show.setdefault(parsed.key, []).append((rec, parsed))
    for key, members in by_show.items():
        assert host._build_show_row(key, members) == rows[key], f"单剧可调用应复现全量该行: {key}"
    # 空成员 -> None(与 _build_group_row 空组口径对齐, S9b 旧行剔除依据)
    assert host._build_show_row("no-such-key", []) is None


def _s9b_baseline() -> tuple:
    """S9b 等价断言基线: 同剧多成员(S01/S02)+ 独立剧 + 未识别种子, 其中两成员预归组
    (删除拍组键可解析), 回 (store, runtime, host, 剧行键表)"""
    store = make_store()  # 空库起步, 逐颗装异形命名种子
    client = store.client
    for h, kw in {
        "HA": dict(name="Show.Alpha.S01E01.1080p-GRP", state="downloading"),
        "HB": dict(name="Show.Alpha.S01E02.1080p-GRP", state="stalledUP"),
        "HC": dict(name="Show.Alpha.S02E01.1080p-GRP", state="stalledUP"),
        "HD": dict(name="Show.Beta.S01E01.1080p-GRP", state="stalledUP"),
        "HE": dict(name="Some.Movie.2023.1080p", state="stalledUP"),  # kind UNKNOWN -> 折叠区
    }.items():
        client.torrents[h] = FakeTorrent(hash=h, **kw)
    store.apply_sync(QbApi(client, store))
    # HB/HD 预归组: HB 删除拍组仍有 HD 余员 -> 组键可解析(行级 removed, 不降 full)
    store.member_to_key["HB"] = ("R:\\D", )
    store.member_to_key["HD"] = ("R:\\D", )
    store.groups[("R:\\D", )] = ["HB", "HD"]
    store.last_added = []
    store.last_removed = []
    store.delta_fields = {}
    store.consume_view_changed()
    rt = _delta_runtime(store)
    host = rt._host
    rt.mark_dirty()
    _publish(rt)  # 基线代(空键集 -> 全量路径, 映射回填)
    keys = {h: tvshows.parse_release(r.name).key for h, r in store.by_hash.items()}
    assert rt._show_member_keys == keys  # 前置: 映射含未识别种子(S8 过宽口径, key 非空)
    assert rt.shows_view["unrecognized"] == ["HE"]
    assert {r["key"] for r in rt.shows_view["list"]} == {"show alpha", "show beta"}
    return store, rt, host, keys


def test_s9b_show_partial_rebuild_equal_and_reference_stable():
    """S9b 局部重聚合: 脏剧键整行重建与全量重跑逐行逐字段相等(任务 D 等价断言), 未脏
    剧行引用原样、脏剧行必然新对象(S6 同款不变量); 覆盖正确性边界 1-4 落位 —— 成员
    增/删/迁移(边界1)、季级 gaps 整季重算(边界2)、剧名频次(边界3, 随整行)、集行状态
    归并(边界4, 随整行); 静止未识别种子的字段抖动不触发折叠面 full、不产幻影剧行"""
    store, rt, host, keys = _s9b_baseline()
    shows0 = {r["key"]: r for r in rt.shows_view["list"]}

    # a) 剧内成员字段变化(HA 速度) -> alpha 整行新对象且与全量重跑相等, beta 行引用原样
    _beat(store, "HA", dlspeed=500)
    entry = _publish(rt)
    assert entry["full"] is False and entry["upsert"]["show"] == {"show alpha"}
    assert entry["removed"]["show"] == set()
    shows1 = {r["key"]: r for r in rt.shows_view["list"]}
    assert shows1["show alpha"] is not shows0["show alpha"]  # 脏行必然新对象
    assert shows1["show beta"] is shows0["show beta"]  # 未脏行引用原样
    assert shows1["show alpha"]["seasons"][0]["episodes"][0]["dlspeed"] == 500  # 整行携带
    assert rt.shows_view["list"] == host._build_shows_view()["list"]  # 逐行逐字段相等
    assert rt.shows_view["unrecognized"] == ["HE"]

    # b) 新成员入库(HF 同剧 S01E03) -> alpha 行重建(边界2: covered/gaps 整季重算)
    store.client.torrents["HF"] = FakeTorrent(hash="HF", name="Show.Alpha.S01E03.1080p-GRP", state="stalledUP")
    store.apply_sync(QbApi(store.client, store))
    entry = _publish(rt)
    assert entry["full"] is False and entry["upsert"]["show"] == {"show alpha"}
    shows2 = {r["key"]: r for r in rt.shows_view["list"]}
    assert shows2["show alpha"]["member_count"] == 4
    s1 = next(s for s in shows2["show alpha"]["seasons"] if s["season"] == 1)
    assert s1["gaps"] == [] and {tuple(e["key"]) for e in s1["episodes"]} == {("ep", 1), ("ep", 2), ("ep", 3)}
    assert rt.shows_view["list"] == host._build_shows_view()["list"]
    assert shows2["show beta"] is shows1["show beta"]

    # c) 成员删除(HB, 组键可解析 -> 行级 removed) -> alpha 行重建减员, 边界1 删除侧
    store.client.torrents.pop("HB")
    store.apply_sync(QbApi(store.client, store))
    entry = _publish(rt)
    assert entry["full"] is False
    assert entry["removed"]["torrent"] == {"HB"} and entry["upsert"]["show"] == {"show alpha"}
    shows3 = {r["key"]: r for r in rt.shows_view["list"]}
    assert shows3["show alpha"]["member_count"] == 3
    assert all("HB" not in e["members"] for s in shows3["show alpha"]["seasons"] for e in s["episodes"])
    assert rt.shows_view["list"] == host._build_shows_view()["list"]

    # d) 单成员剧迁移(HD 改名 beta -> gamma): 旧键重算无成员 -> 行消失转 removed,
    # 新键 upsert(S8 暂存两侧并入重建候选, 「按当前库态定行止」)
    _beat(store, "HD", name="Show.Gamma.S01E01.1080p-GRP")
    entry = _publish(rt)
    assert entry["full"] is False
    assert entry["upsert"]["show"] == {"show gamma"} and entry["removed"]["show"] == {"show beta"}
    shows4 = {r["key"]: r for r in rt.shows_view["list"]}
    assert set(shows4) == {"show alpha", "show gamma"}
    assert rt.shows_view["list"] == host._build_shows_view()["list"]

    # e) 静止未识别种子(HE 电影)字段抖动: 分类不变 -> 不触发折叠面 full, 且不产幻影
    #    剧行(S8 映射过宽登记的 "some movie 2023" 键重算无成员、原不在视图 -> 仅撤候选)
    _beat(store, "HE", dlspeed=777)
    entry = _publish(rt)
    assert entry["full"] is False  # 折叠面检测精确: 分类未变不降级
    assert entry["upsert"]["show"] == set() and entry["removed"]["show"] == set()
    shows5 = {r["key"]: r for r in rt.shows_view["list"]}
    assert set(shows5) == {"show alpha", "show gamma"}  # 无幻影行
    assert shows5["show alpha"] is shows4["show alpha"] and shows5["show gamma"] is shows4["show gamma"]
    assert rt.shows_view["unrecognized"] == ["HE"]
    assert rt.shows_view == host._build_shows_view()


def test_s9b_show_unrecognized_downgrade_full():
    """S9b 折叠面降级(R11): 未识别成员增/删/分类变化不可归约为行级脏(协议无未识别桶)
    -> 本代 full; 分类不变的未识别种子抖动不触发(精确不放大); full 后下一拍恢复行级增量"""
    # a) 新增未识别种子 -> full; 下一拍常规变化恢复行级增量(对照)
    store = make_store("H1")
    store.client.torrents["HM"] = FakeTorrent(hash="HM", name="Some.Movie.2023.1080p", state="stalledUP")
    store.apply_sync(QbApi(store.client, store))
    rt = _delta_runtime(store)
    rt.mark_dirty()
    rid = _publish(rt)["ver"]  # 基线: unrec [HM]
    assert rt.shows_view["unrecognized"] == ["HM"]
    store.client.torrents["H2"] = FakeTorrent(hash="H2", name="Another.Movie.2020.720p", state="stalledUP")
    store.apply_sync(QbApi(store.client, store))
    entry = _publish(rt)
    assert entry["full"] is True and rt._delta_pending["upsert"]["show"] == set()  # full 代键集清空
    assert rt.shows_view["unrecognized"] == ["H2", "HM"]
    _beat(store, "H1", dlspeed=100)
    entry = _publish(rt)
    assert entry["full"] is False  # 下一拍恢复行级增量
    # b) 未识别种子字段抖动(分类不变) -> 不触发(静止电影下载不退化全量)
    _beat(store, "HM", dlspeed=888)
    entry = _publish(rt)
    assert entry["full"] is False
    assert entry["upsert"]["show"] == set()  # 幻影键已撤(重算无成员、原不在视图)
    # c) 未识别种子改名进剧(分类离开折叠区) -> full, 折叠面随全量重建收敛
    _beat(store, "HM", name="Show.Movie.S01E01.1080p-GRP")
    entry = _publish(rt)
    assert entry["full"] is True
    assert rt.shows_view["unrecognized"] == ["H2"]
    assert {r["key"] for r in rt.shows_view["list"]} == {"show h1", "show movie"}
    # d) 未识别种子删除(组键预置可解析, 隔离 row_key_unresolvable) -> full(折叠面收缩)
    store.member_to_key["H2"] = ("R:\\E", )
    store.member_to_key["H1"] = ("R:\\E", )
    store.groups[("R:\\E", )] = ["H2", "H1"]
    store.client.torrents.pop("H2")
    store.apply_sync(QbApi(store.client, store))
    entry = _publish(rt)
    assert entry["full"] is True and rt.shows_view["unrecognized"] == []
    _beat(store, "H1", dlspeed=200)
    assert _publish(rt)["full"] is False  # 恢复行级增量


class _MidBuildWaveHr:
    """确定性收束的跨线程竞态替身: HR 线程在 flush 波次判定(第 1 次读)之后、基线前移点
    (第 3 次读)之前发布新判定 —— revision 前 2 次读回旧值 1, 之后恒回新值 2(不起真线程)"""
    def __init__(self):
        self._reads = 0

    @property
    def revision(self):
        self._reads += 1
        return 1 if self._reads <= 2 else 2


def test_publish_hr_baseline_holds_when_revision_moves_mid_build():
    """局部重建期间 HR 波次又动了(跨线程登记竞态): 基线保留旧值不前移, 下一拍 flush 的
    波次判定补一次 full —— 未脏行的 HR 字段不被静默吞掉, 且基线前移后不循环置脏"""
    store = make_store("H1")
    rt = _delta_runtime(store)
    rt._host.hr = SimpleNamespace(revision=1)
    rt.mark_dirty()
    _publish(rt)  # 基线代(全量): 基线记当刻 revision
    assert rt._hr_rev_at_build == 1
    # 局部代: 门控与 hr_wave 判定都读到旧值(竞态尚未现), 构建期间 HR 线程发布新判定
    _beat(store, "H1", dlspeed=512)
    rt._host.hr = _MidBuildWaveHr()
    rt.mark_dirty()
    entry = _publish(rt)
    assert entry["full"] is False, "前置: 门控读到的还是旧基线, 该代走局部路径"
    assert rt._hr_rev_at_build == 1, "构建期间 revision 已动: 基线不前移(保留给下一拍补 full)"
    # 下一拍: 波次判定读到新值 -> 本代 full; 基线前移后不再循环置脏
    rt.pending_ver = None
    rt.flush_views()
    assert rt._delta_timeline[-1]["full"] is True, "被竞态吞掉的波次必须由下一拍 full 补上"
    assert rt._hr_rev_at_build == 2
    rt.pending_ver = None
    rt.flush_views()
    assert rt.group_view_dirty is False, "基线已前移, 不得循环置脏"


def test_ensure_state_publish_hr_wave_lands_full_timeline_entry():
    """issue 26-11-07-0536 #1: ensure_state 触发的发布检出 hr_wave -> 登记理由落 full=True 条目

    重建侧分叉早就兜住(flush_views 同款判定), 缺的是时间线侧: HR worker 在 flush 的判定
    点**之后**推进 revision 时, flush 的 mark_dirty(full, "hr_revision") 登记没赶上, 发布
    路径只重建不登记 -> fold 见理由为空落 full=False 条目且键集仅含 store 增量键, HR 派生
    字段变更不进时间线, delta 客户端停旧值直到下一个 full 代才自愈。修复 = 发布路径与
    flush 登记点同源登记, 落代即 full(整表重取语义)且理由清空、基线前移不循环。
    """
    store = make_store("H1")
    rt = _delta_runtime(store)
    rt._host.hr = SimpleNamespace(revision=1)
    rt.mark_dirty()
    _publish(rt)  # 基线代: 基线记当刻 revision
    assert rt._hr_rev_at_build == 1
    # 主循环一拍: keyed 路径 mark_dirty, 但上一版未被取走 -> 门控推迟重建; flush 的 HR
    # 判定读到的还是 revision=1(波次未现), 不登记理由
    _beat(store, "H1", dlspeed=512)
    rt.pending_ver = 99  # 模拟上一版未被取走: 门控拦下本轮重建
    rt.flush_views()
    assert rt.group_view_dirty is True  # 前置: 脏已置上, 重建被门控推迟
    assert rt._pending_full_reasons == set()  # 前置: flush 判定点未见波次, 理由为空
    # HR worker 推进 revision(flush 判定点之后), Web 线程经 ensure_state 触发发布
    rt._host.hr = SimpleNamespace(revision=2)
    rt.ensure_state(None)
    entry = rt._delta_timeline[-1]
    assert entry["full"] is True  # 修复前: full=False 且键集仅 store 增量键, HR 变更不进时间线
    assert rt._pending_full_reasons == set()  # 理由随落代清空
    assert rt._hr_rev_at_build == 2  # 基线前移: 下一拍不再波次
    # 对照: revision 未再变的后继拍恢复行级增量, 不循环 full
    _beat(store, "H1", dlspeed=700)
    assert _publish(rt)["full"] is False


def test_show_partial_pending_without_index_coverage_does_not_repost_command():
    """局部剧重建的兑底登记: 可兑底成员(季包)索引未覆盖 -> 登记 shows_pending; 索引已建成
    (非 None)且索引无脏 -> 不重复投递 build_search_index(防建索引自激)"""
    import queue as _queue

    store = make_store("H1")
    store.client.torrents["HP"] = FakeTorrent(hash="HP", name="Show.Pack.S01.720p.x264-GRP", state="stalledUP")
    store.apply_sync(QbApi(store.client, store))
    store.last_added = []
    store.delta_fields = {}
    store.consume_view_changed()
    rt = _delta_runtime(store)
    rt.mark_dirty()
    _publish(rt)  # 基线代: 全量(季包成员可兑底而索引缺 -> shows_pending 置位)
    assert rt.shows_pending is True
    while True:  # 清掉基线代投递的建索引命令, 只考察本代是否重复投递
        try:
            rt.commands.get_nowait()
        except _queue.Empty:
            break
    rt.search_index = {}  # 索引已建成(非 None)但不覆盖 HP; 建索引命令已消费过(脏位已清)
    rt.search_index_dirty = False
    _beat(store, "HP", dlspeed=333)
    rt.mark_dirty()
    entry = _publish(rt)
    key_hp = tvshows.parse_release("Show.Pack.S01.720p.x264-GRP").key
    assert entry["full"] is False and entry["upsert"]["show"] == {key_hp}
    assert rt.shows_pending is True, "可兑底而索引未覆盖: 登记待归位(归位拍由索引推进兜住)"
    assert rt.commands.qsize() == 0, "索引非空且无脏: 不重复投递 build_search_index"


def test_agg_show_node_hr_counts_and_show_row_empty_title():
    """T2a2 清偿: _agg_show_node 的 HR 计数分支与 _build_show_row 空标题成员分支(直驱)

    - HR 计数: 触发成员逐个计入 hr_triggered, 其中未达标成员才计入 hr_pending(达标不重复计);
    - 空标题成员: parsed.title 为空串是单剧可调用的合法输入(名称无剧名形态, 分类由调用方
      完成传入) —— titles 不累加, 展示名回落剧键, 集行照常聚合不炸。
    """
    from helpers import _hr_rule

    store = make_store()
    conf = FakeTracker("HHan", hr=_hr_rule(required_share_ratio=2.0))

    def tor(h, **kw):
        base = dict(
            hash=h,
            name=f"Show.{h}.S01E05.1080p",
            state="stalledUP",
            tracker_conf=conf,
            size=512**2,
            total_size=512**2,
            downloaded=512**2,  # dlratio 条件(默认 0.7): 下载量 >= 种子大小 -> 触发
            progress=1.0,
        )
        base.update(kw)
        return FakeTorrent(**base)

    host = _ViewHost(store)
    rec_pending = tor("HP1", seeding_time=100, ratio=0.5)  # 触发未达标
    rec_done = tor("HD1", seeding_time=4 * 86400)  # 触发且时长达标
    node = {
        "members": [],
        "kinds": [],
        "sites": [],
        "dlspeed": 0,
        "upspeed": 0,
        "uploaded": 0,
        "size": 0,
        "size_progress": -1.0,
        "progress": 1.0,
        "hr_triggered": 0,
        "hr_pending": 0,
        "added_on": 0,
    }
    host._agg_show_node(node, rec_pending)
    host._agg_show_node(node, rec_done)
    assert node["hr_triggered"] == 2, "两个成员都触发 HR: 计数求和"
    assert node["hr_pending"] == 1, "只有未达标成员计入 pending(达标不重复计)"
    assert node["members"] == ["HP1", "HD1"] and node["progress"] == 1.0, "集进度 = 最差版本(全完成为 1.0)"

    # 空标题成员: titles 不累加 -> 展示名回落剧键(键面契约: name 恒非空)
    parsed = tvshows.parse_release("S01E05.mkv")  # kind=episode, title="", 集键照常解析
    assert parsed.title == "" and parsed.episode_key == ("ep", 5)
    row = host._build_show_row("orphan-key", [(rec_pending, parsed)])
    assert row is not None and row["key"] == "orphan-key"
    assert row["name"] == "orphan-key", "无剧名成员: 展示名回落剧键"
    assert row["member_count"] == 1 and row["episode_count"] == 1
    assert row["seasons"][0]["episodes"][0]["hr_triggered"] == 1, "HR 计数进集行"


def test_build_shows_view_row_none_guard_and_pending_no_repost():
    """T2a2 清偿: _build_shows_view 的行剔除防御弧与全量路径 pending 兑底接线

    ① 单剧可调用回 None(空成员集口径, S9b 旧行剔除依据) -> 该剧行不进视图不炸 ——
       全量路径分桶成员恒非空, 防御弧用确定性替身(实例属性覆盖)直驱;
    ② 全量路径 pending 接线: 季包索引未覆盖 -> 登记 shows_pending; 索引已建成(非 None)
       且无脏 -> 不重复投递 build_search_index(与 S9b 局部路径同一防自激口径, 见 T2a 局部版)。
    """
    import queue as _queue

    store = make_store("H1")
    store.client.torrents["HP"] = FakeTorrent(hash="HP", name="Show.Pack.S02.720p.x264-GRP", state="stalledUP")
    store.apply_sync(QbApi(store.client, store))
    store.last_added = []
    store.delta_fields = {}
    store.consume_view_changed()
    rt = _delta_runtime(store)
    host = rt._host

    # ① 防御弧: 行可调用回 None -> 行被跳过
    host._build_show_row = lambda key, members: None  # 确定性替身: 只考察视图层的剔除口径
    view = host._build_shows_view()
    assert view["list"] == [] and view["unrecognized"] == [], "None 行不入视图"
    assert rt.shows_pending is True, "季包索引未覆盖: pending 登记与行剔除互不影响"
    del host._build_show_row  # 还原类方法查找

    # ② pending 接线: 索引已建成且无脏 -> 只登记不投递(清掉①基线代投递的建索引命令再考察)
    while True:
        try:
            rt.commands.get_nowait()
        except _queue.Empty:
            break
    rt.search_index = {}  # 索引已建成(非 None)但不覆盖 HP
    rt.search_index_dirty = False
    view = host._build_shows_view()
    key_hp = tvshows.parse_release("Show.Pack.S02.720p.x264-GRP").key
    assert {row["key"] for row in view["list"]} == {"show h1", key_hp}, "还原后单剧可调用正常产行"
    assert rt.shows_pending is True, "可兑底而索引未覆盖: 登记待归位"
    assert rt.commands.qsize() == 0, "索引非空且无脏: 不重复投递 build_search_index"
