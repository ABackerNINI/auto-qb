"""test_torrents_model 测试计划: 种子信息数据层(TorrentRecord/TorrentStore)自测(不连接真实 qB)

## 测试计划(每个测试函数一条)
- test_record_from_torrent: TorrentRecord.from_torrent 逐字段复制(TorrentDictionary 兼容)
- test_record_update_from: apply_delta 更新快照字段(hash 不变)
- test_record_update_keeps_lazy_cache: apply_delta 保留惰性缓存(文件列表不重复拉取)
- test_record_state_enum: state_enum 解析与 UNKNOWN 降级
- test_record_state_enum_flags: state_enum 语义判定(暂停/上传/下载)
- test_record_tags_set: tags 字符串 -> 预计算集合(逗号分隔去空白)
- test_record_check_hr_on_real_record: 真实 TorrentRecord.check_hr_* 直测(防鸭子影子掩盖)
- test_record_trackers_info_unbound: 记录级 trackers_info 未绑定 client 报错
- test_record_hr_boundaries: HR 判定边界(total_size=0 兜底/小种子完全下载即触发/无 hr 恒 False)
- test_record_update_from_returns_changed: update_from 返回视图字段变化标记
- test_record_seeding_time_quantized_update_from: update_from 双通道(Mapping/对象)的分钟量化
- test_record_hr_managed_follows_site_judgement: 接入站点后 hr_managed 听站点侧(转移种子 downloaded=0 也受管束); check_hr_condition 只答本地触发
- test_record_hr_released_by_site_view: 已核实放行 -> hr_managed False(本地 downloaded 再大也不管束)
- test_record_hr_falls_back_without_link: 未注入判定桥 / 站点未接入 / 桥返回 None -> 行为与既有本地逻辑完全一致(零静默变更)
- test_record_hr_no_evidence_row4_semantics: 行 4(站点无有效证据)语义反转 —— 纯辅种做种满即达标 / 未达标即管束; 结构断言两方法互不调用(回归 2026-09-29 RecursionError)
- test_record_hr_methods_decoupled_structurally: 结构断言 check_hr_condition / check_hr_satisfied 互不调用, hr_managed 为需管束单点(计划 26-09-30-0559)
- test_record_hr_excluded_blocks_all_entries: HR 排除命中标签 -> 三入口全短路且判定桥不被打扰
- test_record_hr_excluded_category_and_regex: HR 排除的分类命中与 regex:/ :ignore_case 格式
- test_record_hr_excluded_beats_site_judgement: 排除优先级最高, 站点接入(enabled)也压不过用户显式排除
- test_record_hr_excluded_table_empty_is_noop: 排除表未命中 -> 行为与无排除一致(零静默变更)
- test_record_hr_anchor_carries_excluded_flag: 锚点快照带排除位(方案 B 的判据载体); 未命中恒 False, 标签/分类命中即带位
- test_snapshot_fields_match_record_slots: 守卫: _SNAPSHOT_FIELDS ↔ record 声明字段一一对应, REQUIRED ⊆ SNAPSHOT
- test_record_from_real_example_payload: 真机 TorrentDictionary 字段样例全量入库(不再丢弃字段)
- test_record_getattr_raw_fallback_and_missing: __getattr__ 前向兼容(_raw 命中 / 无键与 _raw 不可读均 AttributeError)
- test_record_invalidate_trackers_forces_refetch: invalidate_trackers 失效 tracker 惰性缓存, 下次读取重拉
- test_record_hr_entries_short_circuit_without_hr: 无 hr 配置时三判定入口(hr_excluded/hr_managed/check_hr_condition)恒 False
- test_record_hr_condition_dlratio_branches: dlratio 判据(total_size=0 兜底 False / 达线 True)与未知条件类型走完成兜底
- test_record_tracker_name_and_hr_fallback
- test_record_tracker_name_unknown_without_conf
"""

from dataclasses import MISSING, fields as dc_fields

import pytest

from auto_qb.torrents import REQUIRED_TORRENT_FIELDS, TorrentRecord, TorrentStore, view_dirty, view_field_value

from auto_qb.torrents.compat import _SNAPSHOT_FIELDS

from auto_qb.torrents.view import _VIEW_EXCLUDED_FIELDS

from helpers import FakeClient, FakeTorrent

from torrents_support import (
    _EXAMPLE_TORRENT_INFO,
    _StubLink,
    _client,
    _count_trackers,
)


def test_record_from_torrent():
    tor = FakeTorrent(hash="H1", name="Movie", state="stalledUP", tags="a, b", ratio=1.5)
    rec = TorrentRecord.from_torrent(tor)
    assert rec.hash == "H1"
    assert rec.name == "Movie"
    assert rec.state == "stalledUP"
    assert rec.tags == "a, b"
    assert rec.ratio == 1.5
    assert rec.save_path == tor.save_path
    assert rec.total_size == tor.total_size


def test_record_update_from():
    rec = TorrentRecord.from_torrent(FakeTorrent(hash="H1", name="Old", state="stalledUP"))
    changed = rec.apply_delta(FakeTorrent(hash="H1", name="New", state="pausedUP", category="HR-DONE"))
    assert rec.name == "New"
    assert rec.state == "pausedUP"
    assert rec.category == "HR-DONE"
    assert rec.hash == "H1"  # hash 是主键, 不更新
    assert {"name", "state", "category"} <= changed


def test_record_update_keeps_lazy_cache():
    client = _client()
    rec = TorrentRecord.from_torrent(FakeTorrent(hash="H1"))
    _ = rec.files(client)
    calls = client.files_calls
    rec.apply_delta(FakeTorrent(hash="H1", name="Updated"))
    assert rec.files(client) == client.files
    assert client.files_calls == calls  # 缓存保留, 不重复拉取


def test_record_state_enum():
    rec = TorrentRecord.from_torrent(FakeTorrent(hash="H1", state="stalledUP"))
    assert rec.state_enum is not None
    assert rec.state_enum.value == "stalledUP"
    bad = TorrentRecord.from_torrent(FakeTorrent(hash="H1", state="not-a-real-state"))
    assert bad.state_enum is not None
    assert bad.state_enum.name == "UNKNOWN"


def test_record_state_enum_flags():
    """state_enum 提供语义判定(上传/下载/暂停), TorrentRecord 桥接到枚举"""
    paused = TorrentRecord.from_torrent(FakeTorrent(hash="H1", state="pausedUP"))
    assert paused.state_enum.is_stopped
    assert not paused.state_enum.is_uploading
    uploading = TorrentRecord.from_torrent(FakeTorrent(hash="H1", state="stalledUP"))
    assert uploading.state_enum.is_uploading
    downloading = TorrentRecord.from_torrent(FakeTorrent(hash="H1", state="downloading"))
    assert downloading.state_enum.is_downloading
    assert not downloading.state_enum.is_stopped


def test_record_tags_set():
    rec = TorrentRecord.from_torrent(FakeTorrent(hash="H1", tags=" a ,b,,c "))
    assert rec.tags_set == frozenset({"a", "b", "c"})
    empty = TorrentRecord.from_torrent(FakeTorrent(hash="H1", tags=""))
    assert empty.tags_set == frozenset()


def test_record_check_hr_on_real_record():
    """真实 TorrentRecord.check_hr_* 直测: 回归 2026-09-06 BUG(迁入时误用 self.torrent,
    被FakeTorrent鸭子影子掩盖, 真实记录上 AttributeError)"""
    from auto_qb.config import HRRule, TrackerConfig

    rec = TorrentRecord.from_torrent(FakeTorrent(hash="H1", state="stoppedDL"))
    rec.tracker_conf = TrackerConfig(
        name="X",
        domains=["d.com"],
        tags=[],
        remove_tags=[],
        upload_speed_limit=0,
        download_speed_limit=0,
        hr=HRRule(required_seeding_time=3 * 86400, condition=("dlratio", 0.7)),
    )
    rec.downloaded = 70 * 1024**2
    rec.total_size = 100 * 1024**2
    # dlratio 0.7 >= 0.7: 触发; 做种 0 < 3D: 未满足
    assert rec.check_hr_condition() is True
    assert rec.check_hr_satisfied() is False
    # 做种时长达标 -> satisfied
    rec.seeding_time = 3 * 86400 + 12 * 3600
    assert rec.check_hr_satisfied() is True
    # dlsize 条件: downloaded 提至 100MiB >= 100MiB 触发
    rec.downloaded = 100 * 1024**2
    rec.tracker_conf.hr.condition = ("dlsize", 100 * 1024**2)
    assert rec.check_hr_condition() is True
    # 无 hr: False
    rec.tracker_conf.hr = None
    assert rec.check_hr_condition() is False


def _hr_record(*, downloaded=0, total_size=100 * 1024**2, mode="partial"):
    """真实 TorrentRecord + 已接入 hr_check 的站点配置(判定桥的挂载点)"""
    from auto_qb.config import HRRule, TrackerConfig
    from auto_qb.config.models import SiteHrCheckConfig

    rec = TorrentRecord.from_torrent(FakeTorrent(hash="H1", state="stoppedDL"))
    rec.infohash_v1 = "aa" * 20
    rec.added_on = 1000
    rec.total_size = total_size
    rec.downloaded = downloaded
    conf = TrackerConfig(
        name="X", domains=["d.com"], hr=HRRule(required_seeding_time=3 * 86400, condition=("dlratio", 0.7))
    )
    if mode is not None:
        conf.hr_check = SiteHrCheckConfig(
            enabled=(mode != "off"), tracker="x", hr_page_url="https://x.com/myhr.php", required_seeding_time=86400.0
        )
    rec.tracker_conf = conf
    return rec


def test_record_hr_managed_follows_site_judgement():
    """接入站点后 hr_managed 听站点侧三态: 转移种子(A 客户端下载 → B 保种)downloaded=0 也受管束;
    check_hr_condition 只答本地下载触发(展示辅助), 不再受站点侧身份影响(计划 26-09-30-0559)"""
    from auto_qb.hr.resolve import HrIdentity, HrJudgement

    rec = _hr_record(downloaded=0)  # 本地看是纯辅种, 站点侧却是清单命中
    link = _StubLink(HrJudgement(identity=HrIdentity.HR, reason="清单命中(档位 A)"))
    rec.hr_link = link
    assert rec.check_hr_condition() is False, "纯辅种本地未触发 —— 触发判据只看本机下载"
    assert rec.hr_managed() is True, "名单命中即需管束, 与本地 downloaded=0 无关"
    site, hashes, anchor = link.calls[0]
    assert site == "X" and hashes == (rec.infohash_v1, rec.infohash_v2)
    assert anchor == rec.hr_anchor() and anchor.added_on == 1000

    link.judged = HrJudgement(identity=HrIdentity.RELEASED, site_satisfied=True)
    assert rec.check_hr_satisfied() is True, "站点侧 B 档(终态放行) => 直接达标"
    assert rec.hr_managed() is False, "放行 => 不许管束(即便本地未做够)"
    link.judged = HrJudgement(identity=HrIdentity.RELEASED, site_satisfied=False)
    assert rec.check_hr_satisfied() is False, "站点侧 C 档 => 直接未达标"
    assert rec.hr_managed() is False, "终态放行: 本地未做够也不许管束(not satisfied 的补集不成立)"
    link.judged = HrJudgement(identity=HrIdentity.RELEASED, site_satisfied=None)
    assert rec.check_hr_satisfied() is False, "站点没给达标字段 => 回落本地(做种不足)"
    rec.seeding_time = 3 * 86400 + 12 * 3600
    assert rec.check_hr_satisfied() is True, "回落本地时做种时长达标仍算达标(不能因缺字段误报)"
    assert rec.hr_managed() is False, "放行记录: 达标与否都不管束"
    link.judged = HrJudgement(identity=HrIdentity.HR)
    assert rec.check_hr_satisfied() is False, "命中考察中 => 义务仍在, 恒未达标"
    assert rec.hr_managed() is True, "考察中恒管束(含本地已达标者)"


def test_record_hr_released_by_site_view():
    """已核实放行(安全放行): hr_managed False —— 本地 downloaded 再大也不管束;
    check_hr_condition 只看本地触发, 站点放行不再改写它(旧断言「触发也 False」作废)"""
    from auto_qb.hr.resolve import HrIdentity, HrJudgement

    rec = _hr_record(downloaded=100 * 1024**2)
    assert rec.check_hr_condition() is True, "前置: 本地口径下它确实触发(对照用)"
    rec.hr_link = _StubLink(HrJudgement(identity=HrIdentity.RELEASED, reason="覆盖范围内未列出"))
    assert rec.check_hr_condition() is True, "触发判据 = 纯本地, 站点结论不再改写"
    assert rec.hr_managed() is False, "放行记录在案: 不打 HR 标签、不管束"
    assert rec.check_hr_satisfied() is False, "站点没给达标结论 + 做种 0: 未达标(但已放行)"


def test_record_hr_no_evidence_row4_semantics():
    """行 4(站点无有效证据)语义反转(计划 26-09-30-0559): 管束/达标全走本地判据, 无触发门 ——
    纯辅种(downloaded=0)做种满也算达标(旧断言「恒未达标」作废), 未达标即管束(全量纳入)。
    旧实现 check_hr_condition 行 4 调 check_hr_satisfied, 后者回落本地时又调回前者 ——
    无限递归 RecursionError(2026-09-29 BTSchool 实报); 递归源已随重构消失(另见结构断言)"""
    from auto_qb.hr.resolve import HrIdentity, HrJudgement

    rec = _hr_record(downloaded=70 * 1024**2)  # 本地 dlratio 0.7 >= 0.7: 触发
    rec.hr_link = _StubLink(HrJudgement(identity=HrIdentity.NO_EVIDENCE, reason="站点无有效证据"))
    assert rec.check_hr_condition() is True, "行 4 本地触发判据: 本机下载达线"
    assert rec.hr_managed() is True, "行 4 未达标即管束"
    assert rec.check_hr_satisfied() is False, "做种 0 < 3D: 未达标"
    rec.seeding_time = 3 * 86400 + 12 * 3600
    assert rec.check_hr_satisfied() is True, "做种时长达标 -> 达标"
    assert rec.hr_managed() is False, "做种满即义务已了, 不再管束"
    # 纯辅种(downloaded=0 本地不触发): 语义反转 —— 做种满也达标; 未满时管束(疑似辅种全量纳入)
    rec2 = _hr_record(downloaded=0)
    rec2.hr_link = _StubLink(HrJudgement(identity=HrIdentity.NO_EVIDENCE))
    assert rec2.check_hr_condition() is False, "纯辅种本地未触发"
    assert rec2.check_hr_satisfied() is False, "做种 0: 未达标"
    assert rec2.hr_managed() is True, "未触发不代表无义务 —— 疑似辅种未满也管束"
    rec2.seeding_time = 3 * 86400 + 12 * 3600
    assert rec2.check_hr_satisfied() is True, "纯辅种做种满 -> 达标(触发门已删)"
    assert rec2.hr_managed() is False


def test_record_hr_methods_decoupled_structurally():
    """结构断言(计划 26-09-30-0559 §8): check_hr_condition(纯本地触发, 展示辅助)与
    check_hr_satisfied(义务已了)互不调用 —— 递归风险源消失; hr_managed 为需管束单点,
    显式放行短路 + satisfied 兜底(不能写成 not check_hr_satisfied)"""
    import inspect

    cond_src = inspect.getsource(TorrentRecord.check_hr_condition)
    sat_src = inspect.getsource(TorrentRecord.check_hr_satisfied)
    managed_src = inspect.getsource(TorrentRecord.hr_managed)
    assert "check_hr_satisfied" not in cond_src, "check_hr_condition 不得调 check_hr_satisfied(纯本地判据)"
    assert "check_hr_condition" not in sat_src, "check_hr_satisfied 不得调 check_hr_condition(触发门已删)"
    assert "check_hr_satisfied" in managed_src, "hr_managed 兜底必须经 check_hr_satisfied(达标判据单点)"
    assert "RELEASED" in managed_src, "hr_managed 必须显式放行短路(放行记录+未做够也不许管束)"
    assert "hr_judgement" in managed_src, "hr_managed 必须经站点侧判定"


def test_record_hr_falls_back_without_link():
    """零静默变更: 未注入判定桥 / 站点未接入(mode=off) / 桥返回 None -> 全是既有本地判断"""
    from auto_qb.config.models import SiteHrCheckConfig

    rec = _hr_record(downloaded=70 * 1024**2)
    assert rec.hr_link is None
    assert rec.hr_judgement() is None and rec.check_hr_condition() is True
    assert rec.hr_managed() is True, "未接入 + 未达标: 本地判据兜底管束(全量纳入)"
    link = _StubLink(None)
    rec.hr_link = link
    assert rec.hr_judgement() is None and rec.check_hr_condition() is True, "桥返回 None(总开关关) => 本地逻辑"
    assert rec.hr_managed() is True
    rec.tracker_conf.hr_check = None  # 该站未接入(桥在也不该问它)
    asked = len(link.calls)
    assert rec.hr_judgement() is None and rec.check_hr_condition() is True
    assert len(link.calls) == asked, "站点未接入时不该读判定桥"
    rec.tracker_conf.hr_check = SiteHrCheckConfig(enabled=False)
    assert rec.hr_judgement() is None and len(link.calls) == asked, "mode=off 不该打扰判定桥"


def test_record_hr_excluded_blocks_all_entries():
    """HR 排除(计划 26-09-28-1805): 命中排除表 -> 判定入口全短路, 判定桥不被打扰

    打标/规则/表达式/WebUI 四个消费点全经由这些入口 —— 单点短路即全体系退出。
    """
    from auto_qb.hr.resolve import HrIdentity, HrJudgement

    rec = _hr_record(downloaded=70 * 1024**2)
    rec.tags = "HHan,noHR"  # _tags_set 尚未缓存, 直接赋值即生效(须先于任何 tags_set 读取)
    assert rec.check_hr_condition() is True and rec.hr_excluded() is False, "对照: 未配排除时照常触发"
    rec.tracker_conf.hr.exclude_tags = ["noHR"]
    assert rec.hr_excluded() is True
    assert rec.hr_excluded_by() == "tag", "命中来源 token 与命中列表一致(弹窗依据行消费)"
    link = _StubLink(HrJudgement(identity=HrIdentity.HR, reason="清单命中(档位 A)"))
    rec.hr_link = link
    asked = len(link.calls)
    assert rec.hr_judgement() is None, "排除种子连站点侧判定都不发起"
    assert rec.check_hr_condition() is False
    assert rec.check_hr_satisfied() is False, "排除后达标语义无意义, 恒 False(显式短路)"
    assert rec.hr_managed() is False, "排除后管束语义无意义, 恒 False(显式短路)"
    assert len(link.calls) == asked, "排除种子不该打扰判定桥"


def test_record_hr_excluded_category_and_regex():
    """HR 排除: 分类命中(默认大小写敏感)与 regex:/ :ignore_case 组合格式"""
    rec = _hr_record(downloaded=70 * 1024**2)
    rec.tracker_conf.hr.exclude_categories = ["free"]
    rec.category = "FREE"
    assert rec.hr_excluded() is False, "默认大小写敏感(FREE 不匹配 free)"
    rec.category = "free"
    assert rec.hr_excluded() is True
    assert rec.hr_excluded_by() == "category"
    rec.category = ""
    rec.tracker_conf.hr.exclude_tags = ["regex:^skip.?hr:ignore_case"]
    rec.tags = "HHan,SKIP_HR"
    assert rec.hr_excluded() is True
    assert rec.hr_excluded_by() == "tag"
    rec.category = "free"  # 标签与分类同时命中: 来源 token 合并(弹窗依据行据此说明)
    assert rec.hr_excluded_by() == "tag+category"


def test_record_hr_excluded_beats_site_judgement():
    """排除优先级最高: 站点接入(enabled)也压不过用户显式排除"""
    rec = _hr_record(downloaded=70 * 1024**2, mode="enabled")
    assert rec.tracker_conf.hr_check.enabled is True
    rec.tags = "noHR"
    rec.tracker_conf.hr.exclude_tags = ["noHR"]
    assert rec.check_hr_condition() is False and rec.check_hr_satisfied() is False


def test_record_hr_excluded_table_empty_is_noop():
    """零静默变更: 排除表配置了但未命中 -> 行为与无排除完全一致"""
    rec = _hr_record(downloaded=70 * 1024**2)
    rec.tracker_conf.hr.exclude_tags = ["noHR"]
    rec.tags = "HHan"
    assert rec.hr_excluded() is False and rec.check_hr_condition() is True
    assert rec.hr_excluded_by() == "", "未命中来源 token 为空串(前端据此不出依据短语)"


def test_record_hr_anchor_carries_excluded_flag():
    """方案 B(计划 26-10-08-1249 S1): 锚点快照携带排除位 —— 排除态在 record 之外无载体,
    取数/对账侧的对象集现算(service._build_objects)靠它判「第四档排除」。
    未命中排除表时恒 False(零静默变更); 标签 / 分类任一命中即带位(与 hr_excluded 同源单点)。"""
    from auto_qb.hr.resolve import HrAnchor

    assert HrAnchor().excluded is False, "结构默认 False"
    rec = _hr_record(downloaded=70 * 1024**2)
    assert rec.hr_anchor().excluded is False, "无排除配置 ⇒ 默认 False"
    rec.category = "IYUU自动辅种"
    rec.tracker_conf.hr.exclude_categories = ["IYUU自动辅种"]
    assert rec.hr_excluded() is True and rec.hr_anchor().excluded is True, "分类命中 ⇒ 锚点带位"
    rec.category = ""
    rec.tags = "HHan,noHR"  # _tags_set 尚未缓存, 直接赋值即生效(同 hr_excluded 系列用例)
    rec.tracker_conf.hr.exclude_tags = ["noHR"]
    assert rec.hr_excluded() is True and rec.hr_anchor().excluded is True, "标签命中 ⇒ 锚点带位"


def test_record_trackers_info_unbound():
    """记录级 trackers_info 未绑定 client 报错(store 传入 client=None 时)"""
    rec = TorrentRecord.from_torrent(FakeTorrent(hash="H1"))
    try:
        rec.trackers_info(None)
    except RuntimeError:
        pass
    else:
        raise AssertionError("记录级 trackers_info 未绑定 client 时应报错")


def test_record_tracker_name_unknown_without_conf():
    """tracker_name: tracker_conf=None -> 'Unknown'(旧实现回退 tor.client, 真实
    TorrentDictionary 无 client 属性导致生产 log_repr AttributeError)"""
    from types import SimpleNamespace

    rec = TorrentRecord.from_torrent(SimpleNamespace(hash="ABC123", name="T"))
    assert rec.tracker_conf is None
    assert rec.tracker_name == "Unknown"  # 不触碰 tor.client
    assert rec.log_repr == "'T' [Unknown] (ABC123)"


def test_record_hr_boundaries():
    """HR 判定边界: 兜底触发 = 下载量达到种子完整大小; downloaded=0 纯辅种/下载 1B/total_size=0/无 hr 均不触发"""
    from auto_qb.config import HRRule, TrackerConfig

    conf = TrackerConfig(
        name="X",
        domains=["d.com"],
        tags=[],
        remove_tags=[],
        upload_speed_limit=0,
        download_speed_limit=0,
        hr=HRRule(required_seeding_time=3 * 86400, condition=("dlsize", 100 * 1024**2)),
    )
    # total_size=0 空种子: 辅种排除兜底, 不触发
    rec = TorrentRecord.from_torrent(FakeTorrent(hash="E1", state="stalledUP", total_size=0, downloaded=0))
    rec.tracker_conf = conf
    assert rec.check_hr_condition() is False
    # 小种子(10MiB, 触发量 100MiB 永不可达)完整下载完: downloaded == total_size -> 触发
    rec2 = TorrentRecord.from_torrent(
        FakeTorrent(hash="E2", state="stalledUP", total_size=10 * 1024**2, downloaded=10 * 1024**2)
    )
    rec2.tracker_conf = conf
    assert rec2.check_hr_condition() is True
    # downloaded=0 的纯辅种种子(添加时数据已完整, progress=1.0): 不欠 HR 债, 不触发
    rec_seed = TorrentRecord.from_torrent(
        FakeTorrent(hash="E2b", state="stalledUP", total_size=100 * 1024**2, downloaded=0, progress=1.0)
    )
    rec_seed.tracker_conf = conf
    assert rec_seed.check_hr_condition() is False, "纯辅种种子不应触发 HR"
    # 仅下载 1B: 远未"完整下载完", 不触发
    rec_1b = TorrentRecord.from_torrent(
        FakeTorrent(hash="E2c", state="stalledUP", total_size=10 * 1024**2, downloaded=1, progress=1.0)
    )
    rec_1b.tracker_conf = conf
    assert rec_1b.check_hr_condition() is False, "下载 1B 不应触发 HR"
    # 无 hr 配置 -> 恒 False
    conf_nohr = TrackerConfig(
        name="Y", domains=["d.com"], tags=[], remove_tags=[], upload_speed_limit=0, download_speed_limit=0
    )
    rec3 = TorrentRecord.from_torrent(FakeTorrent(hash="E3", state="stalledUP"))
    rec3.tracker_conf = conf_nohr
    assert rec3.check_hr_condition() is False


def test_record_tracker_name_and_hr_fallback():
    """tracker_name 取配置名; check_hr_satisfied 无 hr/条件未达 -> False"""
    from auto_qb.config import HRRule, TrackerConfig

    conf = TrackerConfig(
        name="配置名X",
        domains=["d.com"],
        tags=[],
        remove_tags=[],
        upload_speed_limit=0,
        download_speed_limit=0,
        hr=HRRule(required_seeding_time=3 * 86400, condition=("dlratio", 0.7)),
    )
    rec = TorrentRecord.from_torrent(
        FakeTorrent(hash="T1", state="stalledUP", total_size=100 * 1024**2, downloaded=10 * 1024**2)
    )
    rec.tracker_conf = conf
    assert rec.tracker_name == "配置名X"
    # 比例 0.1 < 0.7: 条件未达 -> satisfied False(L235 分支)
    assert rec.check_hr_satisfied() is False
    # 无 hr 配置: condition/satisfied 均 False(L232 分支)
    conf_nohr = TrackerConfig(
        name="Y", domains=["d.com"], tags=[], remove_tags=[], upload_speed_limit=0, download_speed_limit=0
    )
    rec.tracker_conf = conf_nohr
    assert rec.check_hr_condition() is False
    assert rec.check_hr_satisfied() is False


def test_record_update_from_returns_changed():
    """TorrentRecord.apply_delta 返回变化字段名集合(空集 = 无变化)"""
    rec = TorrentRecord.from_torrent(FakeTorrent(hash="H1", state="stalledUP", upspeed=0))
    assert rec.apply_delta(FakeTorrent(hash="H1", state="stalledUP", upspeed=0)) == frozenset()
    assert rec.apply_delta(FakeTorrent(hash="H1", state="stalledUP", upspeed=7)) == {"upspeed"}
    # 非视图字段变化: 同样计入变化集(downloaded 不在 _VIEW_FIELDS, 但仍是真变化)
    # 注: FakeTorrent 的 amount_left 由 total_size-downloaded 推导, 改 downloaded 会同时带动它
    assert rec.apply_delta(FakeTorrent(hash="H1", state="stalledUP", upspeed=7,
                                       downloaded=999)) == {"downloaded", "amount_left"}


def test_record_seeding_time_quantized_update_from():
    """apply_delta 的分钟量化在两种通道(Mapping dict / 普通对象)下一致"""
    # 对象通道(测试替身)
    rec = TorrentRecord.from_torrent(FakeTorrent(hash="H1", state="stalledUP", seeding_time=600))
    assert rec.apply_delta(FakeTorrent(hash="H1", state="stalledUP", seeding_time=659)) == frozenset()
    assert rec.apply_delta(FakeTorrent(hash="H1", state="stalledUP", seeding_time=660)) == {"seeding_time"}
    # Mapping 通道(真机 TorrentDictionary / sync 响应走这条快路径)
    rec2 = TorrentRecord(hash="H2")
    assert rec2.apply_delta({"hash": "H2", "state": "stalledUP", "seeding_time": 600}) == {"state", "seeding_time"}
    assert rec2.apply_delta({"hash": "H2", "state": "stalledUP", "seeding_time": 640}) == frozenset()
    assert rec2.apply_delta({"hash": "H2", "state": "stalledUP", "seeding_time": 660}) == {"seeding_time"}


def test_snapshot_fields_match_record_slots():
    """守卫: _SNAPSHOT_FIELDS ↔ TorrentRecord 声明字段一一对应(防漏声明/拼写错位);
    REQUIRED ⊆ SNAPSHOT; 除主键 hash 外全部字段带默认值"""
    lazy_slots = {"_tags_set", "_state_enum", "_trackers_info", "_files", "_raw", "tracker_conf", "hr_link"}
    # 错误原因(WebUI 状态列) + tracker 健康(站点 chip 底色): 记录级派生展示字段,
    # 非 qB 快照字段(不进字段表/不参与 apply_delta), 由 WebviewMixin.refresh_tracker_health
    # 在主循环预取后写入
    lazy_slots |= {
        "tracker_error_msg", "tracker_error_ts", "tracker_health_msg", "tracker_health_ts", "tracker_suspect_since"
    }
    declared = {f.name for f in dc_fields(TorrentRecord)}
    snapshot = set(_SNAPSHOT_FIELDS)

    assert snapshot <= declared - lazy_slots, "字段表有未声明的 slot(或拼错)"
    assert declared - lazy_slots - snapshot == set(), "有声明了但不在字段表的 slot(字段表漏登记)"
    assert set(REQUIRED_TORRENT_FIELDS) <= snapshot
    no_default = [f.name for f in dc_fields(TorrentRecord) if f.default is MISSING and f.default_factory is MISSING]
    assert no_default == ["hash"]


def test_record_from_real_example_payload():
    """真机字段样例全量入库: 每个响应字段都进快照(声明字段), 不再丢弃; 哨兵值原样透传"""
    rec = TorrentRecord.from_torrent(_EXAMPLE_TORRENT_INFO, hash=_EXAMPLE_TORRENT_INFO["hash"])

    assert rec.hash == "047b3fad9834f0f2c00f9d4a9189068431e4a191"
    assert rec.eta == 8640000 and rec.completion_on == -1 and rec.seen_complete == -1  # 哨兵原样
    assert rec.private is True and rec.priority == 3 and rec.has_metadata is True
    assert rec.magnet_uri.startswith("magnet:?")
    assert rec.trackers_count == 1 and rec.connections_limit == 30 and rec.time_active == 23098
    assert rec.popularity == 0 and rec.reannounce_in == 0 and rec.total_wasted == 0
    assert rec.comment == "https://kufirc.com/torrents.php?id=240006"
    assert rec.ratio_limit == -2 and rec.seeding_time_limit == -2  # 升格字段来自样例而非默认
    assert rec._raw is None  # 样例字段全部已声明, 无未知字段落 _raw

    d = rec.to_dict()
    assert set(_EXAMPLE_TORRENT_INFO) <= set(d)  # 样例字段全量导出无丢失(记录现声明字段更多)


def test_record_getattr_raw_fallback_and_missing():
    """__getattr__ 前向兼容: 未声明字段走 _raw; _raw 无键与 _raw 不可读时仍 AttributeError(与 TorrentDictionary 语义一致)"""
    rec = TorrentRecord.from_torrent({"hash": "H1", "future_field": "v"})
    assert rec.future_field == "v"  # _raw 命中(qB 新版本字段数据不丢)
    with pytest.raises(AttributeError):
        _ = rec.never_seen_field  # _raw 无键: KeyError 吞掉后 AttributeError
    del rec._raw  # 槽删除: object.__getattribute__ 抛 AttributeError -> raw=None 兜底分支
    with pytest.raises(AttributeError):
        _ = rec.never_seen_field


def test_record_invalidate_trackers_forces_refetch():
    """invalidate_trackers: tracker 写操作后失效惰性缓存, 下次读取重新拉取"""
    client = _client()
    counter = _count_trackers(client)
    rec = TorrentRecord.from_torrent(FakeTorrent(hash="H1"))
    _ = rec.trackers_info(client)
    assert counter["n"] == 1
    rec.invalidate_trackers()
    _ = rec.trackers_info(client)
    assert counter["n"] == 2  # 缓存已失效: 真的重新拉取


def test_record_hr_entries_short_circuit_without_hr():
    """无 hr 配置: hr_excluded / hr_managed / check_hr_condition 三入口恒 False(入口短路行直测)"""
    from auto_qb.config import TrackerConfig

    conf = TrackerConfig(
        name="X",
        domains=["d.com"],
        tags=[],
        remove_tags=[],
        upload_speed_limit=0,
        download_speed_limit=0,
        hr=None,
    )
    rec = TorrentRecord.from_torrent(FakeTorrent(hash="H1", state="stalledUP"))
    rec.tracker_conf = conf
    assert rec.hr_excluded() is False
    assert rec.hr_managed() is False
    assert rec.check_hr_condition() is False


def test_record_hr_condition_dlratio_branches():
    """dlratio 判据分支: total_size=0 辅种兜底 False / 下载达线 True; 未知条件类型走「下载完」兜底"""
    from auto_qb.config import HRRule, TrackerConfig

    def mk(total_size, downloaded, cond):
        conf = TrackerConfig(
            name="X",
            domains=["d.com"],
            tags=[],
            remove_tags=[],
            upload_speed_limit=0,
            download_speed_limit=0,
            hr=HRRule(condition=cond),
        )
        rec = TorrentRecord.from_torrent(
            FakeTorrent(hash="H1", state="stalledUP", total_size=total_size, downloaded=downloaded)
        )
        rec.tracker_conf = conf
        return rec

    assert mk(0, 0, ("dlratio", 1.0)).check_hr_condition() is False  # total_size=0: 辅种排除兜底
    assert mk(100, 100, ("dlratio", 1.0)).check_hr_condition() is True  # downloaded/total_size >= 阈值
    assert mk(100, 100, ("seedsize", 5)).check_hr_condition() is True  # 未知类型: 完整下载兜底
    assert mk(100, 50, ("seedsize", 5)).check_hr_condition() is False  # 未下载完: 兜底也不触发
