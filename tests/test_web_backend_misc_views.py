"""test_web_backend_misc_views 测试计划: WEB 后端杂项: config / token / sites / 分组视图 / 错误原因

## 测试计划(每个测试函数一条)
- test_group_key_codec_roundtrip: 分组 key 编解码往返(含中文/多文件)
- test_build_group_view: 分组视图组装(组名/合计/成员站点/单种子大小与总大小/标签/分类/保存路径)
- test_build_group_view_cross_group_conflict_flag: 组视图跨组文件交叉标记(26-10-04-0107 S4/D4) —— 去重集合展平为组 key 集合后端查好, warned 注入组对两侧 true、组外组 false; warned 空全 false; 未归组单种子视图(singles)为成员级投影不携带组级标记
- test_build_group_view_member_num_seeds_fields: 组视图成员透出 num_seeds/num_leechs/num_complete/num_incomplete
- test_build_group_view_group_aggregates: 组视图组级聚合(辅种扩列 2026-09-28) —— 进度/可用性 max、eta 最小有效值(哨兵不参与)、剩余量 min、最近活动 max(-1 不参与)、已下载求和、做种时长平均、分享率=总上传÷单份大小; 全组无效值回 0/None
- test_member_view_extended_fields: 成员视图透出辅种扩列字段(eta/time_active/last_activity 分钟量化 + downloaded/amount_left/completion_on/seen_complete/availability/限速/tracker/infohash_v2)
- test_member_view_occ_key: occ_key 内容单元标识(计划 26-10-18-2013 D8) —— 归组种子 occ_key == 组行 key(同键空间); 未归组为 null(字段恒在); 种子页平铺行经 _seed_view 继承
- test_error_reason_from_tracker_msg: 错误种子的具体原因取 tracker 报错 msg(虚拟条目跳过)+ 视图透出 error_reason(取不到回退"错误"/非错误态为空)
- test_error_reason_missing_files_without_api: missingFiles 的原因由状态本身给出("文件丢失"), 不发 tracker 请求
- test_refresh_tracker_health_budget_and_ttl: tracker 健康取数限流(单轮预算条数/TTL 内不重取/过期重取)
- test_refresh_tracker_health_clears_when_recovered: 状态恢复后清空原因缓存并置脏(不留旧原因)
- test_refresh_tracker_health_skips_when_disconnected: qB 断开时跳过(不发请求/不清空现值)
- test_tracker_health_debounce_state_machine: 去抖状态机(计划 26-10-19-2007 S1) 首次报错只置疑似不亮 / 满窗复查仍报错才亮 / 已亮重复观测同报错无变化不置脏(T2a2) / 恢复即灭
- test_tracker_health_ignores_fetch_failure: 取数失败(qB 异常)按"取不到"处理 —— 不改现值, 只推进 TTL 时间戳
- test_tracker_health_skips_paused: 暂停态不扫描(不发请求), 健康态保留不灭
- test_tracker_health_error_state_reason_ttl_unchanged: error 态展示原因仍按 ERROR_REASON_TTL 重取(与改造前一致)
- test_tracker_health_lit_schedules_by_lit_ttl: 已亮记录按 LIT_TTL(60s)调度而非 SUSPECT_TTL(30s)(issue 26-11-07-0536, 亮灯清 suspect 疑似/已亮互斥, 已亮复查不回去抖循环)
- test_build_group_view_by_hash_probe_index_race: 组视图构建 by_hash 成员取值改单步 get(issue 26-11-07-0536, 竞态替身钉 pop 窗口 + 缺失成员按 None 跳过行为等价)
- test_site_alert_priority_and_virtual_tracker: site_alert 判定单点 —— no_site_conf 优先于 tracker_error / 纯 DHT 不算缺配置 / 报错文本截断
"""

import logging

import os

import re

import time

from types import SimpleNamespace

import pytest

from auto_qb.infra.utils import decode_group_key, encode_group_key

from webui_helpers import WEB_ENV_CONFIG_TEXT, _make_web_manager, STATIC_ROOT, _UI_ALL, _ui_aggregate


def test_group_key_codec_roundtrip():
    """分组 key 编解码回原值(base64url(JSON))"""
    key = ("R:/下載/目錄", ("a.mkv", "b.mkv"))
    assert decode_group_key(encode_group_key(key)) == key


def test_build_group_view(tmp_path):
    """分组视图快照组装: 组级聚合求和 + 成员明细 + 编码 key(回归真机 utils.encode_group_key 缺失)"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

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


def test_build_group_view_by_hash_probe_index_race(tmp_path):
    """组视图构建的 by_hash 成员取值改单步 get(issue 26-11-07-0536 #4)

    「in 判定 + 下标取值」两步之间主循环可并发 pop 该 hash(remove_torrent / _apply 换代
    回绑 by_hash, 均不持 view_lock), 两步形态 KeyError 使 Web 请求 500 —— 单步取值后判
    None 跳过。确定性竞态替身把 pop 钉在两步之间; 行为等价面: 成员已删(groups 残留)时
    按缺失跳过, 组行以剩余成员构建。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.config.grouping.enabled = True
    mgr.client = FakeClient()
    t1 = FakeTorrent(hash="HA", name="Show", state="stalledUP", save_path=r"R:/s")
    t2 = FakeTorrent(hash="HB", name="Show", state="stalledUP", save_path=r"R:/s")
    seed_store(mgr, [t1, t2])
    key = ("R:/s", ("a.mkv", "b.mkv"))
    mgr.store.groups[key] = ["HA", "HB"]
    mgr.store.member_to_key["HA"] = key
    mgr.store.member_to_key["HB"] = key

    # 竞态注入: __contains__ 判真后立即 pop victim(修复前两步形态在此抛 KeyError)
    mgr.store.by_hash = _PopBetweenProbeAndIndex(mgr.store.by_hash, "HB")
    view = mgr._build_group_view()
    assert len(view) == 1
    assert view[0]["count"] == 2, "单步 .get 不经过 __contains__: 竞态窗口不复存在, 按当刻快照完整构建"

    # 行为等价面: 成员已被主循环删掉(groups 条目残留)时按缺失跳过, 不抛 KeyError
    mgr.store.by_hash = {h: rec for h, rec in mgr.store.by_hash.items() if h != "HB"}
    view = mgr._build_group_view()
    assert view[0]["count"] == 1, "缺失成员按 None 过滤跳过, 组行以剩余成员构建"


def test_build_group_view_cross_group_conflict_flag(tmp_path):
    """组视图透出跨组文件交叉标记(plan 26-10-04-0107 S4/D4) —— 后端查去重集合, 前端只渲染

    warned 注入组对 -> 组对两侧组字段 true、组外组 false; warned 空 -> 全 false;
    未归组种子不进组视图, singles 单种子视图是成员级投影, 不携带组级标记(无污染;
    前端 filters.js 对搜索视图的虚拟单种子组恒补 cross_group_conflict: false, 单种子无组 key)。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.config.grouping.enabled = True
    mgr.client = FakeClient()
    t1 = FakeTorrent(hash="HA", name="ShowA", state="stalledUP", progress=1.0, size=512**2, save_path=r"R:/a")
    t2 = FakeTorrent(hash="HB", name="ShowB", state="downloading", progress=0.5, size=512**2, save_path=r"R:/b")
    t3 = FakeTorrent(hash="HC", name="ShowC", state="stalledUP", progress=1.0, size=512**2, save_path=r"R:/c")
    t4 = FakeTorrent(hash="HD", name="Lone", state="stalledUP", progress=1.0, size=512**2, save_path=r"R:/d")
    seed_store(mgr, [t1, t2, t3, t4])
    key_a = (r"R:/a", ("a.mkv", ))
    key_b = (r"R:/b", ("b.mkv", ))
    key_c = (r"R:/c", ("c.mkv", ))
    mgr.store.groups[key_a] = ["HA"]
    mgr.store.groups[key_b] = ["HB"]
    mgr.store.groups[key_c] = ["HC"]
    for h, k in (("HA", key_a), ("HB", key_b), ("HC", key_c)):
        mgr.store.member_to_key[h] = k

    # warned 空(开关关/无交叉常态) -> 全 false
    view = {g["name"]: g for g in mgr._build_group_view()}
    assert set(view) == {"ShowA", "ShowB", "ShowC"}
    assert not any(g["cross_group_conflict"] for g in view.values()), "warned 空时不得有组被标记"

    # warned 注入组对 (A, B) -> 两侧组 true, 组外 C false
    # (直写 store 去重集合的白盒姿势, 对齐本文件 seed_store + 手填 groups 的既有夹具)
    mgr.store.cross_group_conflict_warned.add((key_a, key_b))
    view = {g["name"]: g for g in mgr._build_group_view()}
    assert view["ShowA"]["cross_group_conflict"] is True
    assert view["ShowB"]["cross_group_conflict"] is True
    assert view["ShowC"]["cross_group_conflict"] is False

    # 未归组种子(Lone)不在组视图里; singles 是成员级投影, 不携带组级标记(无字段污染)
    singles = mgr._build_singles_view()
    assert [m["name"] for m in singles] == ["Lone"]
    assert all("cross_group_conflict" not in m for m in singles)


def test_build_group_view_member_num_seeds_fields(tmp_path):
    """组视图成员透出 num_seeds/num_leechs/num_complete/num_incomplete(TorrentRecord 快照直取)

    前端成员列/种子页展示连接数与可用性的数据源: _member_view 是组视图 members 与
    singles 未归组种子的共同投影, 字段在成员层透出后两处同形。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = FakeClient()
    t1 = FakeTorrent(
        hash="HA",
        name="Show",
        save_path=r"R:/s",
        num_seeds=12,
        num_leechs=3,
        num_complete=45,
        num_incomplete=6,
    )
    t2 = FakeTorrent(
        hash="HB",
        name="Show",
        save_path=r"R:/s",
        num_seeds=34,
        num_leechs=5,
        num_complete=67,
        num_incomplete=8,
    )
    seed_store(mgr, [t1, t2])
    key = ("R:/s", ("a.mkv", "b.mkv"))
    mgr.store.groups[key] = ["HA", "HB"]
    mgr.store.member_to_key["HA"] = key
    mgr.store.member_to_key["HB"] = key

    members = mgr._build_group_view()[0]["members"]
    for m in members:
        for f in ("num_seeds", "num_leechs", "num_complete", "num_incomplete"):
            assert f in m, f"组视图成员缺少字段 {f}: {sorted(m)}"
    by_hash = {m["hash"]: m for m in members}
    assert by_hash["HA"]["num_seeds"] == 12
    assert by_hash["HA"]["num_leechs"] == 3
    assert by_hash["HA"]["num_complete"] == 45
    assert by_hash["HA"]["num_incomplete"] == 6
    assert by_hash["HB"]["num_seeds"] == 34
    assert by_hash["HB"]["num_leechs"] == 5
    assert by_hash["HB"]["num_complete"] == 67
    assert by_hash["HB"]["num_incomplete"] == 8


def test_build_group_view_group_aggregates(tmp_path):
    """组视图组级聚合(辅种扩列 2026-09-28): "单份文件"语义下的口径单点

    组内成员指向同一份文件(组 key 首元即规范化 save_path), 磁盘只占一份 —— 字节量类取
    "单份"视角, 只有逐成员真实发生的网络流量才可求和:
    - progress/availability 取 max(最完整副本 / 最好的 swarm)
    - eta 取最小有效值(下载冲突检查保证同组至多一个在下载; 哨兵 8640000/非正不参与)
    - amount_left 取 min(补齐一份即可 —— 最完整成员还差的字节, 其余成员 recheck 即齐)
    - last_activity 取 max(-1/0 = 从未 哨兵不参与, 全组从未回 0)
    - downloaded 求和(多站切换下载的真实网络流量, 逐成员可加)
    - seeding_time 取平均(成员值已量化到分钟, 平均后再取整)
    - ratio = 总上传 ÷ 单份大小(分母不能是 total_size, N 份会稀释 N 倍)
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.config.grouping.enabled = True
    mgr.client = FakeClient()
    size = 10000
    t1 = FakeTorrent(
        hash="HA",
        name="Show",
        save_path=r"R:/s",
        size=size,
        progress=0.5,
        eta=7261,  # 成员视图量化到分钟 -> 7260
        downloaded=100,
        amount_left=500,
        availability=1.5,
        last_activity=1700000100,
        seeding_time=3641,  # -> 3600(分钟量化)
        uploaded=1024,
        state="stalledUP",
    )
    t2 = FakeTorrent(
        hash="HB",
        name="Show",
        save_path=r"R:/s",
        size=size,
        progress=1.0,
        eta=8640000,  # 哨兵(无 ETA): 不参与 eta 聚合
        downloaded=200,
        amount_left=300,
        availability=-1.0,  # qB 未知: 不参与 availability 聚合
        last_activity=-1,  # 从未: 不参与 last_activity 聚合
        seeding_time=7200,
        uploaded=2048,
        state="pausedUP",
    )
    # 全组无效值: eta 全哨兵/非正 -> 0, last_activity 全从未 -> 0, availability 全未知 -> None
    t3 = FakeTorrent(
        hash="HC", name="Alone", save_path=r"R:/x", eta=8640000, last_activity=-1, availability=-1.0, state="pausedUP"
    )
    t4 = FakeTorrent(
        hash="HD", name="Alone", save_path=r"R:/x", eta=0, last_activity=0, availability=-1.0, state="pausedUP"
    )
    seed_store(mgr, [t1, t2, t3, t4])
    key = ("R:/s", ("a.mkv", "b.mkv"))
    mgr.store.groups[key] = ["HA", "HB"]
    mgr.store.member_to_key["HA"] = key
    mgr.store.member_to_key["HB"] = key
    key2 = ("R:/x", ("c.mkv", ))
    mgr.store.groups[key2] = ["HC", "HD"]
    mgr.store.member_to_key["HC"] = key2
    mgr.store.member_to_key["HD"] = key2

    g = mgr._build_group_view()[0]
    assert g["progress"] == 1.0
    assert g["eta"] == 7260, "组 eta = 最小有效值(哨兵不参与)"
    assert g["downloaded"] == 300
    assert g["amount_left"] == 300
    assert g["availability"] == 1.5
    assert g["last_activity"] == 1700000100
    assert g["seeding_time"] == 5400, "组做种时长 = 成员平均值(3600 与 7200 的均值)"
    assert g["ratio"] == round(3072 / size, 3), "组分享率分母 = 单份大小而非 total_size"

    g2 = {gg["name"]: gg for gg in mgr._build_group_view()}["Alone"]
    assert g2["eta"] == 0 and g2["last_activity"] == 0 and g2["availability"] is None


def test_member_view_extended_fields(tmp_path):
    """成员视图透出辅种扩列字段(2026-09-28): 明细表新列与组级聚合的共同数据源

    _member_view 是组视图 members 与 singles 未归组种子的共同投影 —— 明细表新增的
    剩余时间/已下载/限速/Tracker/Hash v2 等列从这里取数。秒级递增字段(eta/time_active/
    last_activity)必须经 view_field_value 分钟量化(与 store 重建判定同一步长, 否则做种中的
    种子每轮置脏、惰性重建失效); 哨兵原样带过(负数不量化, 见 view_field_value)。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = FakeClient()
    t = FakeTorrent(
        hash="HA",
        name="Show",
        save_path=r"R:/s",
        eta=7261,
        time_active=3661,
        last_activity=1700000123,
        completion_on=1700000500,
        seen_complete=1700000600,
        availability=1.2345,
        dl_limit=1024,
        up_limit=2048,
        tracker="https://tracker.example/announce",
        infohash_v2="v2hash-abcd1234",
        downloaded=123456,
        amount_left=654321,
    )
    seed_store(mgr, [t])
    v = mgr._member_view(mgr.store.by_hash["HA"])
    assert v["eta"] == 7260 and v["time_active"] == 3660 and v["last_activity"] == 1700000100
    assert v["downloaded"] == 123456 and v["amount_left"] == 654321
    assert v["completion_on"] == 1700000500 and v["seen_complete"] == 1700000600
    assert v["availability"] == 1.23
    assert v["dl_limit"] == 1024 and v["up_limit"] == 2048
    assert v["tracker"] == "https://tracker.example/announce"
    assert v["infohash_v2"] == "v2hash-abcd1234"


def test_member_view_occ_key(tmp_path):
    """occ_key 内容单元标识(2026-10-18, 计划 26-10-18-2013 D8): 选中摘要"实际占用"的去重键

    前端选中摘要(selection.js::selSizeSummaryOf)按 occ_key 把"同一份文件的多站点副本"
    并成一个占用单元(单元值取选中成员最大 size, Y≤X 恒成立)。契约三条:
      1. 归组种子 occ_key == 其组行 key(同键空间, 都走 encode_group_key);
      2. 未归组种子(singles)occ_key 为 null(字段恒在, null = 不适用; 前端兜成自单元);
      3. 种子页平铺行经 _seed_view 继承(不重述)。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = FakeClient()
    t1 = FakeTorrent(hash="HA", name="Show", save_path=r"R:/s", size=100)
    t2 = FakeTorrent(hash="HB", name="Show", save_path=r"R:/s", size=200)
    t3 = FakeTorrent(hash="HC", name="Alone", save_path=r"R:/x", size=300)
    seed_store(mgr, [t1, t2, t3])
    key = ("R:/s", ())
    mgr.store.groups[key] = ["HA", "HB"]
    mgr.store.member_to_key["HA"] = key
    mgr.store.member_to_key["HB"] = key

    row = mgr._build_group_view()[0]
    by_hash = {m["hash"]: m for m in row["members"]}
    assert by_hash["HA"]["occ_key"] == row["key"], "归组成员 occ_key == 组行 key(同键空间)"
    assert by_hash["HB"]["occ_key"] == row["key"]
    assert row["key"] == encode_group_key(key)

    single = mgr._build_singles_view()
    assert [s["hash"] for s in single] == ["HC"]
    assert single[0]["occ_key"] is None, "未归组种子 occ_key = null(字段恒在, 前端兜成自单元)"

    seed = {s["hash"]: s for s in mgr._build_flat_view()}
    assert seed["HA"]["occ_key"] == row["key"], "种子页平铺行经 _seed_view 继承 occ_key"
    assert seed["HC"]["occ_key"] is None


class _PopBetweenProbeAndIndex(dict):
    """确定性竞态替身(dict 子类, 批A tests/test_webui_delta_merge.py 同款): __contains__ 判真后
    立即 pop victim —— 把主循环的并发删除钉在「in 判定」与「下标取值」两步之间的窗口内
    (remove_torrent 原地 pop / _apply 换代回绑 by_hash, 均不持 view_lock; Web 线程经
    ensure_view/ensure_state 触发的组视图重建读同一字典)。修复后的单步 .get(h) 不再经过
    __contains__, 窗口不复存在。"""
    def __init__(self, inner, victim):
        super().__init__(inner)
        self._victim = victim

    def __contains__(self, h):
        has = super().__contains__(h)
        if has and h == self._victim:
            dict.pop(self, h, None)  # 竞态窗口: 判真后主循环 pop 落地
        return has


def _tracker_calls(client):
    """给 FakeClient 的 torrents_trackers 挂调用计数器(返回被查询过的 hash 列表)

    "免 API"/"TTL 内不重取"/"单轮预算限流"三类断言都需要该计数, 而公共替身无此计数
    (既有用例不依赖), 故在测试侧按需包装, 不改动 helpers.FakeClient 的既有语义。
    """
    seen = []
    orig = client.torrents_trackers
    client.torrents_trackers = lambda h: (seen.append(h), orig(h))[1]
    return seen


def test_error_reason_from_tracker_msg(tmp_path):
    """错误状态的具体原因: 取 tracker 报错 msg(虚拟条目跳过), 并透出到成员/种子视图

    qB torrents/info **不含**错误文本(Web API 无该字段), 原因只能从 torrents/trackers 的
    msg 取; 预取结果写在记录上, 视图组装只读缓存 —— 视图可能每 tick 重建, 不能在里面发 API。
    取不到报错 msg 的错误种子(磁盘/IO 类)回退状态文本, 不留空串(否则前端显示空白状态)。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    client = FakeClient()
    mgr.client = client
    client.trackers_map["HA"] = [
        {
            "url": "** [DHT] **",
            "status": 4,
            "msg": "virtual-entry-msg"
        },  # 虚拟条目: 不得采信
        {
            "url": "https://tracker.hhanclub.net/announce.php",
            "status": 2,
            "msg": "Working"
        },
        {
            "url": "https://tracker.other.net/announce.php",
            "status": 4,
            "msg": "torrent not registered"
        },
    ]
    client.trackers_map["HB"] = [{"url": "https://tracker.hhanclub.net/announce.php", "status": 2, "msg": "Working"}]
    err = FakeTorrent(hash="HA", name="Show", state="error")
    no_msg = FakeTorrent(hash="HB", name="Show", state="error")
    seed_store(mgr, [err, no_msg])

    mgr.web.group_view_dirty = False
    mgr.refresh_tracker_health()

    assert err.tracker_error_msg == "torrent not registered", "取第一条非空错误 msg(虚拟条目跳过)"
    assert mgr.web.group_view_dirty is True, "原因变化须显式置脏(非快照字段, store.view_changed 覆盖不到)"
    assert mgr._member_view(err)["error_reason"] == "torrent not registered"
    assert mgr._seed_view(err)["error_reason"] == "torrent not registered"
    assert no_msg.tracker_error_msg == "" and mgr._member_view(no_msg)["error_reason"] == "错误"
    assert mgr._member_view(FakeTorrent(hash="HC", state="stalledUP"))["error_reason"] == "", "非错误状态不带原因"


def test_error_reason_missing_files_without_api(tmp_path):
    """missingFiles 的原因由状态本身给出("文件丢失"), 不需要任何 tracker 请求"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    client = FakeClient()
    mgr.client = client
    seen = _tracker_calls(client)
    t = FakeTorrent(hash="HA", name="Show", state="missingFiles")
    seed_store(mgr, [t])

    mgr.refresh_tracker_health()

    assert mgr._member_view(t)["error_reason"] == "文件丢失"
    assert seen == [], "missingFiles 的原因不依赖 API"


def test_refresh_tracker_health_budget_and_ttl(tmp_path, monkeypatch):
    """预取限流: 单轮最多预算条, TTL 内不重取, 过期后重取

    错误种子成片时(整组文件丢失)不能一轮打满 tracker 请求 —— 与搜索索引同一限流哲学。
    """
    from auto_qb.webui import views as web_view
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    monkeypatch.setattr(web_view, "TRACKER_HEALTH_BUDGET", 1)
    mgr = make_manager(str(tmp_path / "state.json"))
    client = FakeClient()
    mgr.client = client
    seen = _tracker_calls(client)
    seed_store(mgr, [FakeTorrent(hash="HA", name="A", state="error"), FakeTorrent(hash="HB", name="B", state="error")])

    mgr.refresh_tracker_health()
    assert seen == ["HA"], "单轮只拉预算条数"
    mgr.refresh_tracker_health()
    assert seen == ["HA", "HB"], "下一轮续取剩余种子"
    mgr.refresh_tracker_health()
    assert seen == ["HA", "HB"], "TTL 内不重取"

    monkeypatch.setattr(web_view, "TRACKER_HEALTH_BUDGET", 5)
    monkeypatch.setattr(web_view, "ERROR_REASON_TTL", 0.0)
    mgr.refresh_tracker_health()
    assert seen == ["HA", "HB", "HA", "HB"], "TTL 过期后重取(tracker msg 随站点状态变化)"


def test_refresh_tracker_health_clears_when_recovered(tmp_path):
    """状态恢复(离开错误态)后清空原因缓存 —— 否则恢复做种仍挂着旧原因"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = FakeClient()
    # tracker_health_ts 与 error_ts 同置为"刚观测过": 统一取数后两者共用同一次观测,
    # 双钟(TTL 600 / 300)任一未到期都不该重取
    t = FakeTorrent(
        hash="HA",
        name="A",
        state="error",
        tracker_error_msg="unregistered",
        tracker_error_ts=time.time(),
        tracker_health_ts=time.time()
    )
    seed_store(mgr, [t])

    mgr.web.group_view_dirty = False
    mgr.refresh_tracker_health()
    assert t.tracker_error_msg == "unregistered", "错误态且未过期: 原样保留"
    assert mgr.web.group_view_dirty is False, "无变化不置脏"

    t.state = "stalledUP"
    mgr.refresh_tracker_health()
    assert t.tracker_error_msg == "" and t.tracker_error_ts == 0.0
    assert mgr.web.group_view_dirty is True, "清空也是视图变化"


def test_refresh_tracker_health_skips_when_disconnected(tmp_path):
    """qB 断开(client None)时跳过: 不发请求、不清空已有原因(连接恢复后自然刷新)"""
    from helpers import FakeTorrent, make_manager, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = None
    t = FakeTorrent(hash="HA", name="A", state="error", tracker_error_msg="unregistered")
    seed_store(mgr, [t])

    mgr.refresh_tracker_health()  # 不抛异常

    assert t.tracker_error_msg == "unregistered" and t.tracker_error_ts == 0.0


def test_tracker_health_debounce_state_machine(tmp_path):
    """去抖状态机(计划 26-10-19-2007 S1): 首次报错只置疑似不亮; 满窗复查仍报错才亮

    反例: 若按"连续 2 次观测"实现, 常规 TTL 600s 下两次观测相隔 20 分钟, 去抖等于没有(R1)。
    """
    from helpers import FakeClient, FakeTorrent, FakeTracker, make_manager, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    client = FakeClient()
    mgr.client = client
    client.trackers_map["HA"] = [{"url": "https://tracker.hhanclub.net/announce.php", "status": 4, "msg": "连接被拒"}]
    # 活跃态: tracker 被拒但种子仍在上传(状态是 seeding 不是 error —— 这正是 P2 痛点)
    t = FakeTorrent(hash="HA", name="A", state="stalledUP", tracker="https://tracker.hhanclub.net/announce.php")
    t.tracker_conf = FakeTracker("HHan")
    seed_store(mgr, [t])

    mgr.refresh_tracker_health()
    assert t.tracker_health_msg == "", "首次观测只置疑似, 不亮"
    assert t.tracker_suspect_since > 0
    assert mgr._member_view(t)["site_alert"] == "", "疑似态不亮图标"

    # 满窗(30s)后复查: 仍报错 -> 亮
    t.tracker_health_ts = time.time() - 31
    t.tracker_suspect_since = time.time() - 31
    mgr.refresh_tracker_health()
    assert t.tracker_health_msg == "连接被拒", "满窗复查仍报错 -> 确认亮"
    view = mgr._member_view(t)
    assert view["site_alert"] == "tracker_error" and view["site_alert_msg"] == "连接被拒"

    # 已亮重复观测同报错(T2a2): 原因未变 -> 不重复登记变化, 不置脏
    mgr.web.group_view_dirty = False
    t.tracker_health_ts = time.time() - 61  # 已亮 -> 60s 复查到期
    mgr.refresh_tracker_health()
    assert t.tracker_health_msg == "连接被拒", "原因未变: 原值保留"
    assert mgr.web.group_view_dirty is False, "无变化不置脏"

    # 恢复即灭: 站点恢复(无报错条目) -> 清空
    client.trackers_map["HA"] = [{"url": "https://tracker.hhanclub.net/announce.php", "status": 2, "msg": "Working"}]
    t.tracker_health_ts = time.time() - 61  # 已亮 -> 60s 复查到期
    mgr.refresh_tracker_health()
    assert t.tracker_health_msg == "" and t.tracker_suspect_since == 0.0, "恢复即灭"
    assert mgr._member_view(t)["site_alert"] == ""


def test_tracker_health_lit_schedules_by_lit_ttl(tmp_path):
    """已亮记录按 LIT_TTL(60s)调度而非 SUSPECT_TTL(30s)(issue 26-11-07-0536 #2)

    修复前不变量 "health_msg 非空 ⟹ suspect_since 非零" 让已亮记录恒走疑似分档:
    buckets[1](elif health_msg)不可达, 已亮记录按 30s 复查(/trackers 请求量翻倍),
    「疑似 -> 已亮 -> error 态」的预算分档失效。修复: 亮灯时清 suspect_since(疑似与
    已亮互斥), 已亮记录落 LIT_TTL 分档; 已亮复查仍报错走"保持已亮"分支, 不回疑似去抖循环。
    """
    from helpers import FakeClient, FakeTorrent, FakeTracker, make_manager, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    client = FakeClient()
    mgr.client = client
    client.trackers_map["HA"] = [{"url": "https://tracker.hhanclub.net/announce.php", "status": 4, "msg": "连接被拒"}]
    t = FakeTorrent(hash="HA", name="A", state="stalledUP", tracker="https://tracker.hhanclub.net/announce.php")
    t.tracker_conf = FakeTracker("HHan")
    seed_store(mgr, [t])
    seen = _tracker_calls(client)

    # 去抖: 首次疑似 -> 满窗亮灯
    mgr.refresh_tracker_health()
    t.tracker_health_ts = time.time() - 31
    t.tracker_suspect_since = time.time() - 31
    mgr.refresh_tracker_health()
    assert t.tracker_health_msg == "连接被拒", "满窗复查仍报错 -> 确认亮"
    assert t.tracker_suspect_since == 0.0, "亮灯时清疑似起点(疑似与已亮互斥), 已亮记录由此落 LIT_TTL 分档"

    # 亮灯后 45s(> SUSPECT_TTL 30s, < LIT_TTL 60s): 不重取 —— 修复前按 30s 疑似分档此处会重取
    mgr.web.group_view_dirty = False
    t.tracker_health_ts = time.time() - 45
    mgr.refresh_tracker_health()
    assert seen == ["HA", "HA"], "已亮未到 LIT_TTL: 不重取(修复前按 SUSPECT_TTL 30s 会重取, 请求量翻倍)"
    assert mgr.web.group_view_dirty is False

    # 61s(> LIT_TTL 60s): 到期重取; 同报错保持已亮, 不回疑似去抖循环
    t.tracker_health_ts = time.time() - 61
    mgr.refresh_tracker_health()
    assert seen == ["HA", "HA", "HA"], "LIT_TTL 到期才重取"
    assert t.tracker_health_msg == "连接被拒", "仍报错: 保持已亮"
    assert t.tracker_suspect_since == 0.0, "已亮复查不得重回疑似去抖循环"


def test_tracker_health_ignores_fetch_failure(tmp_path):
    """取数失败(qB 异常)按"取不到"处理: 不动现值(不能把"没看到"当成"好了")"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HA", name="A", state="stalledUP", tracker_health_msg="连接被拒")
    seed_store(mgr, [t])
    t.tracker_health_ts = 0.0  # 到期

    def boom(h):
        raise RuntimeError("qB 断连")

    client.torrents_trackers = boom
    mgr.refresh_tracker_health()

    assert t.tracker_health_msg == "连接被拒", "取不到不改现值"
    assert t.tracker_health_ts > 0, "TTL 时间戳照常推进(不在断连期间反复重试)"


def test_tracker_health_skips_paused(tmp_path):
    """暂停态不扫描(暂停种子不会汇报, 报错文本无意义); 健康态保留不灭"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    client = FakeClient()
    mgr.client = client
    seen = _tracker_calls(client)
    client.trackers_map["HA"] = [{"url": "https://tracker.hhanclub.net/announce.php", "status": 4, "msg": "拒绝"}]
    t = FakeTorrent(hash="HA", name="A", state="pausedUP", tracker_health_msg="拒绝")
    seed_store(mgr, [t])

    mgr.refresh_tracker_health()

    assert seen == [], "暂停态不发 tracker 请求"
    assert t.tracker_health_msg == "拒绝", "没有观测证据时不拿'没看'当成'好了'"


def test_tracker_health_error_state_reason_ttl_unchanged(tmp_path, monkeypatch):
    """error 态种子: 展示原因仍按 ERROR_REASON_TTL(300s)重取, 与改造前行为一致"""
    from auto_qb.webui import views as web_view
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    client = FakeClient()
    mgr.client = client
    seen = _tracker_calls(client)
    client.trackers_map["HA"] = [
        {
            "url": "https://tracker.hhanclub.net/announce.php",
            "status": 4,
            "msg": "unregistered"
        }
    ]
    t = FakeTorrent(hash="HA", name="A", state="error")
    seed_store(mgr, [t])

    mgr.refresh_tracker_health()
    assert t.tracker_error_msg == "unregistered"
    assert seen == ["HA"]

    # TTL 内(300s 与 30s 疑似复查都没到期): 不重取
    t.tracker_health_ts = time.time() - 20
    t.tracker_error_ts = time.time() - 20
    mgr.refresh_tracker_health()
    assert seen == ["HA"], "TTL 内不重取"

    # 越过 ERROR_REASON_TTL: 重取(健康侧 30s 疑似复查也在此列, 两者共用同一次调用)
    t.tracker_health_ts = time.time() - (web_view.ERROR_REASON_TTL + 1)
    t.tracker_error_ts = time.time() - (web_view.ERROR_REASON_TTL + 1)
    mgr.refresh_tracker_health()
    assert seen == ["HA", "HA"], "过期后重取"


def test_site_alert_priority_and_virtual_tracker(tmp_path):
    """站点告警判定单点: 缺配置优先于 tracker 报错; 纯 DHT/磁力不算缺配置; msg 截断"""
    from auto_qb.webui import views as web_view
    from helpers import FakeTorrent, make_manager, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    # 1. 缺站点配置 + 同时有报错 -> 缺配置优先(配置缺失时连报错文本都不可信)
    no_conf = FakeTorrent(
        hash="HA",
        name="A",
        state="stalledUP",
        tracker="https://tracker.unknown.net/announce.php",
        tracker_health_msg="拒绝"
    )
    # 2. 纯 DHT(无真实 tracker URL): 不报缺配置
    dht_only = FakeTorrent(hash="HB", name="B", state="stalledUP", tracker="** [DHT] **")
    # 3. 报错文本超长 -> 截断到 SITE_ALERT_MSG_MAX
    long_msg = "x" * (web_view.SITE_ALERT_MSG_MAX + 50)
    conf = FakeTorrent(hash="HC", name="C", state="stalledUP", tracker="https://tracker.hhanclub.net/announce.php")
    conf.tracker_conf = object()  # 已匹配站点(只判 None)
    conf.tracker_health_msg = long_msg
    seed_store(mgr, [no_conf, dht_only, conf])

    assert mgr._site_alert(no_conf) == ("no_site_conf", web_view.SITE_ALERT_NO_CONF_TEXT)
    assert mgr._site_alert(dht_only) == ("", ""), "纯 DHT 不算缺配置"
    alert, msg = mgr._site_alert(conf)
    assert alert == "tracker_error" and len(msg) == web_view.SITE_ALERT_MSG_MAX, "报错文本截断到 200"
