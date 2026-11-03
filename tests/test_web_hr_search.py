"""test_web_hr_search 测试计划: HR web 端点与搜索 / 文件系统端点

## 测试计划(每个测试函数一条)
- test_build_search_index_files: 搜索索引构建(hash -> name+files), 单条文件拉取失败跳过该种子
- test_build_search_index_incremental_and_evict: 增量维护(不重拉已建条目/补拉新增/淘汰已删)
- test_build_search_index_budget_resumes: 限流分批构建, 未拉完保持脏, 续建至完成
- test_build_search_index_aborts_when_disconnected: qB 断连时中止构建且不写空索引
- test_search_torrents_name_match: 种子名匹配(即时/大小写不敏感)
- test_search_row_view_converged_on_member_view: 守阵(issue b-r16b01-search-row-view-converge) search_torrents._view 不自建行构造 ——
  ast 静态: 返回字典只有 {**_member_view} 展开 + by; 动态: 搜索行键集 = 成员行键集 + {by}, 同名字段值等值,
  seeding_time 走分钟量化, 明细列(eta/num_seeds/downloaded/availability)不再空白
- test_search_torrents_separator_normalized: 分隔符归一匹配 —— 空格查询词命中点/下划线/连字符分隔的名与文件(回归 "cat and" 搜不到 The.Cat.and… 名)
- test_parse_query_tokens: 查询解析词法 —— 正/负词/短语 + 宽容边界(孤立-/未闭合引号/纯标点/--dv/web-dl)
- test_search_torrents_cross_row_and: 正词逐词跨行 AND(拍板 26-09-27 二次定案, 推翻 26-09-26 文件行隔离)—— 每个正词命中任一候选行(全称行/文件行)即可: 「minions mteam」名字×标签、「delta 03」名字×集文件跨行命中; 负词种子级不变
- test_search_torrents_negative_term: 负词种子级(26-09-27 定案)—— 任一候选行含负词 ⇒ 该种子整体排除: 单种子内季包文件统一计算(任一文件带负词整包排除), 多种子集合逐个算
- test_search_torrents_negative_torrent_veto: 负词种子级回归 —— 名字/保存路径/站点行含负词 ⇒ 整种子排除, 优先于一切正词命中(「cat and -11」+「-mteam」两轮报障回归)
- test_search_torrents_facet_rows: 候选行覆盖全部文本面(站点/分类/路径/标签行即时匹配, by 定位行类别) + facet 行负词整种子排除 —— 三页同源(26-09-26 单点化; 负词种子级 26-09-27 定案)
- test_search_torrents_phrase: 短语 "…" 整段归一为连续子串, 词序敏感(terms-AND 命中而短语不命中的区分用例)
- test_search_torrents_regression_envnv10: 回归(26-09-26 报障)——「恶女 10」命中单文件发布物, -ubweb 可排除
- test_search_torrents_negative_only_empty: 仅负词/空查询返回空 + negative_only 标记 + 当前 rev, 不投递索引构建
- test_search_torrents_rev_snapshot_before_read: 守阵(plan 26-11-03-0120 S4)——rev 在读取 store 快照前取值(构行时自增仍回旧值)
- test_api_state_reports_search_rev: 守阵(plan 26-11-03-0120 S3)——/api/status 与 /api/state 的 search_rev 同源且变化可见
- test_search_torrents_file_match: 文件列表匹配(依赖已建索引)
- test_search_torrents_building_triggers: 索引脏时 building=True 并投递构建命令
- test_api_search_endpoint: GET /api/search 转发与鉴权(含空查询)
- testhr_view_fields_three_state: 详情字段透出站点侧三态与依据(接入站点才有值, 未接入全空)
- testhr_view_fields_excluded: HR 排除态视图(hr_excluded=True, 触发/达标 False, 站点侧全空, 桥不被打扰)
"""

import json

import os

import re

import sys

import tempfile

import time

from pathlib import Path

from types import SimpleNamespace

from unittest import mock

import pytest

from auto_qb.infra import file_access

from auto_qb.infra.utils import encode_group_key

from webui_helpers import _UI_ALL, _ui_aggregate, _hr_status_env, ENTRY_ROW_KEYS_API, HISTORY_ROW_KEYS

from web_hr_support import (
    _AUTH_HEADER_KEY,
)


def test_build_search_index_files():
    """build_search_index: 主循环构建索引(hash -> name+files), 单条文件拉取失败跳过该种子"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        from helpers import _fake_file
        client.files_map["HA"] = [_fake_file("movie.mkv", 0), _fake_file("sub.srt", 0)]
        client.files_map["HB"] = [_fake_file("anime.mkv", 0)]
        t1 = FakeTorrent(hash="HA", name="Alpha", tracker_conf=None)
        t2 = FakeTorrent(hash="HB", name="Beta", tracker_conf=None)
        seed_store(mgr, [t1, t2])

        # 让 HB 的文件拉取失败: files() 抛异常 -> 该种子 files 为空但不阻塞
        def boom(h):
            if h == "HB":
                raise RuntimeError("fail")
            return [_fake_file("movie.mkv", 0), _fake_file("sub.srt", 0)]

        client.torrents_files = boom

        mgr.build_search_index()
        assert mgr.web.search_index_dirty is False
        idx = mgr.web.search_index
        assert idx["HA"]["name"] == "Alpha"
        assert "movie.mkv" in idx["HA"]["files"]
        assert idx["HB"]["files"] == [], "文件拉取失败的种子 files 应为空"
        assert set(idx.keys()) == {"HA", "HB"}


def test_build_search_index_incremental_and_evict():
    """build_search_index 增量维护: 已建条目只刷新名称(不重拉文件), 新种子补拉, 已消失种子淘汰"""
    from helpers import FakeClient, FakeTorrent, _fake_file, make_manager, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.files_map["HA"] = [_fake_file("movie.mkv", 0)]
        ha = FakeTorrent(hash="HA", name="Alpha")
        seed_store(mgr, [ha])
        mgr.build_search_index()
        first_calls = client.files_calls
        assert first_calls == 1

        # 种子集未变: 不重复拉文件列表, 仅刷新名称, 且整体替换引用(原子交换契约)
        idx_before = mgr.web.search_index
        ha.name = "Alpha.Renamed"
        mgr.build_search_index()
        assert client.files_calls == first_calls, "已建条目不重复拉取文件列表"
        assert mgr.web.search_index["HA"]["name"] == "Alpha.Renamed", "名称应刷新"
        assert mgr.web.search_index is not idx_before, "索引应整体替换引用(Web 线程并发只读安全), 不就地增删"

        # HA 消失 + HB 新增: 只补拉新种子, 已删种子淘汰
        client.files_map["HB"] = [_fake_file("anime.mkv", 0)]
        seed_store(mgr, [FakeTorrent(hash="HB", name="Beta")])
        mgr.web.search_index_dirty = True
        mgr.build_search_index()
        assert set(mgr.web.search_index.keys()) == {"HB"}, "已消失种子应被淘汰"
        assert client.files_calls == first_calls + 1, "只补拉新增种子的文件列表"
        assert mgr.web.search_index_dirty is False


def test_build_search_index_budget_resumes(monkeypatch):
    """build_search_index 限流: 单次最多拉预算条, 未拉完保持脏, 下次调用续建至完成"""
    from auto_qb.webui import views as web_view
    from helpers import FakeClient, FakeTorrent, _fake_file, make_manager, seed_store

    monkeypatch.setattr(web_view, "SEARCH_INDEX_BUILD_BUDGET", 1)
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.files_map["HA"] = [_fake_file("a.mkv", 0)]
        client.files_map["HB"] = [_fake_file("b.mkv", 0)]
        seed_store(mgr, [FakeTorrent(hash="HA", name="Alpha"), FakeTorrent(hash="HB", name="Beta")])

        mgr.build_search_index()
        assert mgr.web.search_index_dirty is True, "预算用尽应保持脏(待续建)"
        assert set(mgr.web.search_index.keys()) == {"HA"}, "单次只拉预算条数的文件列表"

        mgr.build_search_index()
        assert mgr.web.search_index_dirty is False, "续建后应不再脏"
        assert set(mgr.web.search_index.keys()) == {"HA", "HB"}


def test_build_search_index_aborts_when_disconnected():
    """build_search_index: qB 断开(client None)时中止并保持脏——不把空文件列表当成"已建完"""
    from helpers import FakeClient, FakeTorrent, _fake_file, make_manager, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.files_map["HA"] = [_fake_file("movie.mkv", 0)]
        seed_store(mgr, [FakeTorrent(hash="HA", name="Alpha")])

        mgr.client = None  # 模拟 qB 断连(setter 同步解绑 store/api)
        mgr.build_search_index()
        assert mgr.web.search_index_dirty is True, "断连时应保持脏, 待连接恢复后重建"
        assert mgr.web.search_index is None, "断连时不得写入空文件索引"

        mgr.client = client  # 连接恢复
        mgr.build_search_index()
        assert mgr.web.search_index_dirty is False
        assert mgr.web.search_index["HA"]["files"] == ["movie.mkv"]


def test_search_torrents_name_match():
    """search_torrents: 种子名匹配(即时, 无需文件索引), 大小写不敏感"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        t1 = FakeTorrent(hash="HA", name="My.Movie.2024", state="stalledUP")
        t2 = FakeTorrent(hash="HB", name="Anime.Series.S01", state="downloading")
        seed_store(mgr, [t1, t2])

        r = mgr.search_torrents("my.movie")
        names = [x["hash"] for x in r["results"]]
        assert names == ["HA"], f"名称命中(小写): {r}"
        assert all(x["by"] == "name" for x in r["results"])


def test_search_row_view_converged_on_member_view():
    """守阵: search_torrents._view 不自建行构造(issue b-r16b01-search-row-view-converge)

    静态(ast): `_view`(search_torrents 内嵌函数)的返回字典字面量只有 `**_member_view` 展开
    + 显式键 "by" —— 行构造单点收敛在 _member_view(与 _seed_view 同范式)。此前这里自建一份
    字段子集: seeding_time 原始秒未走 view_field_value(与重建量化契约脱钩), 且缺
    eta/num_*/downloaded 等 19 键 —— 未归组命中种子的搜索虚拟行(searchUncovered)展开明细的
    默认列全空白。红验: 在 _view 里重列任一 _member_view 键即判红。
    动态: 搜索结果行键集 = _member_view 键集 + {"by"}; 同一条记录两侧同名字段值等值;
    seeding_time 走分钟量化(与 _member_view 同口径); 明细列有值。
    """
    import ast

    from auto_qb.torrents.view import view_field_value

    src = Path(__file__).resolve().parents[1] / "src" / "auto_qb" / "webui" / "views_search.py"
    tree = ast.parse(src.read_text(encoding="utf-8"))
    view_fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_view")
    ret = next(n for n in ast.walk(view_fn) if isinstance(n, ast.Return))
    spread = [k for k in ret.value.keys if k is None]  # dict 字面量的 ** 展开在 AST 里是 key=None, 不是 Starred
    declared = {k.value for k in ret.value.keys if isinstance(k, ast.Constant)}
    assert len(spread) == 1, "_view 返回字典必须以 {**_member_view(...)} 起手"
    assert declared == {"by"}, f"_view 只允许显式声明 by(重列 _member_view 键即重述): {sorted(declared)}"

    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        tor = FakeTorrent(
            hash="H1",
            name="SearchRowTest",
            state="stalledUP",
            seeding_time=3630,
            eta=8640030,
            time_active=3641,
            num_seeds=5,
            num_leechs=2,
            availability=1.25,
            dl_limit=1024,
            up_limit=2048,
        )
        seed_store(mgr, [tor])
        rec = mgr.store.get("H1")
        member = mgr._member_view(rec)
        r = mgr.search_torrents("searchrow")
    assert len(r["results"]) == 1, f"应恰好命中一颗种子: {r}"
    row = r["results"][0]
    assert row["by"] == "name"
    assert set(member) <= set(row), f"搜索行缺成员视图字段: {sorted(set(member) - set(row))}"
    assert set(row) - set(member) == {"by"}, f"搜索行只允许多 by: {sorted(set(row) - set(member))}"
    diff = {k: (member[k], row[k]) for k in member if member[k] != row[k]}
    assert not diff, f"同名字段值不等(口径漂移): {diff}"
    assert row["seeding_time"] == view_field_value("seeding_time", rec.seeding_time) == 3600, "seeding_time 必须走分钟量化"
    # 明细列不再空白(issue 的用户可见面): 虚拟行展开的默认可见列有值
    assert row["eta"] == 8640000 and row["num_seeds"] == 5 and row["num_leechs"] == 2
    assert row["downloaded"] == tor.downloaded and row["availability"] == 1.25


def test_search_torrents_separator_normalized():
    """search_torrents: 分隔符归一匹配 —— 空格查询词命中点/下划线/连字符分隔的种子名与文件名

    回归(26-09-25): "The.Cat.and.the.Dragon.S01.1080p.friDay.WEB-DL.AAC2.0.H.264-MWeb"
    搜 "cat and" 不命中 —— 旧实现裸子串匹配, 查询词里的空格对不上名里的点号。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store, _fake_file

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        t1 = FakeTorrent(
            hash="HA", name="The.Cat.and.the.Dragon.S01.1080p.friDay.WEB-DL.AAC2.0.H.264-MWeb", state="stalledUP"
        )
        t2 = FakeTorrent(hash="HB", name="Other.Show.S02", state="stalledUP")
        client.files_map["HA"] = [_fake_file("The.Cat.and.the.Dragon.S01E01.1080p.WEB-DL.mkv", 0)]
        client.files_map["HB"] = [_fake_file("the_cat_and_dragon_e02.mkv", 0)]
        seed_store(mgr, [t1, t2])
        mgr.build_search_index()

        r = mgr.search_torrents("cat and")
        # HA 名字命中(回归主案例), HB 的下划线文件名归一后也含 "cat and"(file 路径顺带覆盖)
        assert [x["hash"] for x in r["results"]] == ["HA", "HB"], f"空格查询词应命中点号分隔名: {r}"
        assert [x["by"] for x in r["results"]] == ["name", "file"]
        assert [x["hash"] for x in mgr.search_torrents("web dl")["results"]] == ["HA"], "连字符分隔应命中"
        # 对称: 点号查询词同样归一, 仍命中; 纯分隔符不命中(解析即丢弃, 等价空查询)
        assert [x["hash"] for x in mgr.search_torrents("cat.and")["results"]] == ["HA", "HB"]
        # 同行同现: 词序无关 —— 旧口径 "dragon cat" 因连续子串序敏感不命中;
        # HA 名行与 HB 的下划线文件行均同含两词, 两路各按行命中
        assert [x["hash"] for x in mgr.search_torrents("dragon cat")["results"]] == ["HA", "HB"]
        assert mgr.search_torrents("...")["results"] == []

        # 文件命中: 下划线分隔的文件名按同一口径(HA 名与文件均不含该子串, 排除 seen 去重干扰)
        r = mgr.search_torrents("and dragon e02")
        assert [x["hash"] for x in r["results"]] == ["HB"], f"下划线文件名应命中: {r}"
        assert r["results"][0]["by"] == "file"


def test_parse_query_tokens():
    """_parse_query: 词法 —— 正/负词、短语、宽容边界(孤立 -/未闭合引号/纯标点/--dv/web-dl/词中引号)"""
    from auto_qb.webui.views import _parse_query

    # 基本分词 + 负词(词首 - 后随非空白); 归一小写
    assert _parse_query("恶女 10 -DV") == (["恶女", "10"], ["dv"])
    # 短语整段归一为连续子串(保留空格); 排除短语
    assert _parse_query('"s01e10" 恶女 -"H264 AAC"') == (["s01e10", "恶女"], ["h264 aac"])
    # 宽容: 孤立 - 忽略 / 未闭合引号收至行尾 / 纯标点 token 丢弃 / --dv 等价 -dv / web-dl 是正词
    assert _parse_query("-") == ([], [])
    assert _parse_query('foo "bar') == (["foo", "bar"], [])
    assert _parse_query("...") == ([], [])
    assert _parse_query("--dv") == ([], ["dv"])
    assert _parse_query("WEB-DL") == (["web dl"], [])
    # 词中引号无特殊含义(随归一折叠); 空查询
    assert _parse_query('foo"bar baz"') == (["foo bar", "baz"], [])
    assert _parse_query("") == ([], [])


def test_search_torrents_cross_row_and():
    """search_torrents 正词逐词跨行 AND(拍板 26-09-27 二次定案): 每个正词命中任一候选行即可, 行可不同

    26-09-26 曾拍板「多词须同行, 文件行不参与跨行」(防季包吸词); 26-09-27 用户实测推翻 ——
    「种子名 Gamma.Delta + 集文件 Gamma.E01-E03」搜「delta 03」须命中(标题在名字行、集号只在
    集文件行), 召回优先, 吸词代价(附加词可被包内任一文件名吸收)知情接受。负词种子级否决不变
    (见 negative_term / negative_torrent_veto); 全称行全覆盖的命中排前, 需文件行补词的以 file
    兜底排后。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store, _fake_file

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        t1 = FakeTorrent(hash="HA", name="Alpha.Beta.S01", state="stalledUP", tags="MTeam")
        t2 = FakeTorrent(hash="HB", name="Gamma", state="stalledUP")
        client.files_map["HB"] = [_fake_file("delta.mkv", 0), _fake_file("Gamma.E03.mkv", 1)]
        # 26-09-27 报障原型: 包名 Gamma.Delta 在名字行, 集号 03 只在集文件行
        t3 = FakeTorrent(hash="HC", name="Gamma.Delta.S01", state="stalledUP")
        client.files_map["HC"] = [
            _fake_file("Gamma.E01.mkv", 0),
            _fake_file("Gamma.E02.mkv", 1),
            _fake_file("Gamma.E03.mkv", 2)
        ]
        seed_store(mgr, [t1, t2, t3])
        mgr.build_search_index()

        # 同行 AND 照常; 全称行跨行(名字×标签)照常(「minions mteam」同型)
        assert [(x["hash"], x["by"]) for x in mgr.search_torrents("alpha s01")["results"]] == [("HA", "name")]
        assert [(x["hash"], x["by"]) for x in mgr.search_torrents("alpha mteam")["results"]] == [("HA", "name")]
        # 报障回归: delta 在名字行、03 只在集文件行 → file 兜底命中(HB 的 delta 则只在文件行)
        assert [(x["hash"], x["by"])
                for x in mgr.search_torrents("delta 03")["results"]] == [("HB", "file"), ("HC", "file")]
        # 26-09-26 的「跨行不命中」断言全部翻转: 词落不同行也命中
        assert [(x["hash"], x["by"])
                for x in mgr.search_torrents("gamma delta")["results"]] == [("HC", "name"), ("HB", "file")]
        assert [(x["hash"], x["by"])
                for x in mgr.search_torrents("gamma e03")["results"]] == [("HB", "file"), ("HC", "file")]
        assert [(x["hash"], x["by"])
                for x in mgr.search_torrents("e03 delta")["results"]] == [("HB", "file"), ("HC", "file")]
        # 单词行为不变; AND 不退化为 OR(alpha 与 delta 无一颗种子同有 → 空)
        assert [(x["hash"], x["by"])
                for x in mgr.search_torrents("delta")["results"]] == [("HC", "name"), ("HB", "file")]
        assert mgr.search_torrents("alpha delta")["results"] == []


def test_search_torrents_negative_term():
    """search_torrents 负词种子级(2026-09-27 定案): 任一候选行含负词 ⇒ 该种子整体排除 —— 单个
    种子内包含的合集(季包文件)统一计算; 多种子集合(辅种组/追剧)里的每个种子单独计算"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store, _fake_file

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        t1 = FakeTorrent(hash="HA", name="Show.S01E10.DV.1080p", state="stalledUP")
        # 单种子内包含的合集(季包): E09 文件带 DV ⇒ 统一计算, 整包排除(E10 行干净也救不回)
        t2 = FakeTorrent(hash="HB", name="Show.S01.Complete", state="stalledUP")
        client.files_map["HB"] = [_fake_file("Show.S01E09.DV.mkv", 0), _fake_file("Show.S01E10.1080p.mkv", 1)]
        # 多种子集合里的另一颗单集种子: 干净 ⇒ 留下
        t3 = FakeTorrent(hash="HC", name="Show.S01E10.1080p.CR.WEB-DL", state="stalledUP")
        seed_store(mgr, [t1, t2, t3])
        mgr.build_search_index()

        # "show 10 -dv": HA 名行含 dv ⇒ 排除; HB 的 E09.DV 文件行含 dv ⇒ 整包排除; HC 干净 ⇒ 名字命中
        r = mgr.search_torrents("show 10 -dv")
        assert [(x["hash"], x["by"]) for x in r["results"]] == [("HC", "name")], f"负词种子级: {r}"
        # 不带负词: 三颗都命中(即时命中 [HA, HC] 先于文件命中 HB; 旧口径 -dv 会把 dv 当正词搜, 顺带验证解析)
        assert [x["hash"] for x in mgr.search_torrents("show 10")["results"]] == ["HA", "HC", "HB"]
        # 排除短语: "web dl" 作为短语只排除 HC(HA/HB 不含该短语)
        assert [x["hash"] for x in mgr.search_torrents("show 10 -\"web dl\"")["results"]] == ["HA", "HB"]


def test_search_torrents_negative_torrent_veto():
    """search_torrents 负词种子级(2026-09-27 定案): 任一候选行(名字/站点/分类/路径/标签/文件行)
    含负词 ⇒ 整种子排除, 优先于一切正词命中

    两轮实机报障的收口: 1.「cat and -11」(26-09-26) —— E11 单文件的种子名行含 "11" 被行级作废,
    却被不含 "11" 的保存路径行整颗捞回; 2.「-mteam」(27-09-27) —— 站点/标签行负词拦不住名字行
    正词命中。负词必须是种子级才有可预测的排除语义; 文件行同入种子级否决(见 negative_term)。
    """
    from helpers import FakeClient, FakeTorrent, FakeTracker, make_manager, seed_store, _fake_file

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        t1 = FakeTorrent(
            hash="HA",
            name="The.Cat.and.the.Dragon.S01E11.1080p.friDay.WEB-DL.AAC2.0.H.264-MWeb.mkv",
            state="stalledUP",
            save_path="D:/TV/The.Cat.and.the.Dragon.S01",
        )
        site = FakeTracker("MTeam")
        site.tags = []  # tracker_name 取 conf.name(默认 tags 会顶掉站点名)
        t2 = FakeTorrent(hash="HB", name="Alpha.S01", state="stalledUP", tracker_conf=site)
        # 名字含负词、文件行干净的种子: 文件轮也须受身份行否决约束
        t3 = FakeTorrent(hash="HC", name="E11.REPACK", state="stalledUP")
        client.files_map["HC"] = [_fake_file("Show.1080p.mkv", 0)]
        seed_store(mgr, [t1, t2, t3])
        mgr.build_search_index()

        # 报障1.回归: HA 名字行含 "11" ⇒ 整种子否决, 保存路径行("cat and" 齐、无 "11")不得捞回
        assert mgr.search_torrents("cat and -11")["results"] == []
        # 无负词时 HA 照常命中(名字行) —— 否决只由负词触发
        assert [(x["hash"], x["by"]) for x in mgr.search_torrents("cat and")["results"]] == [("HA", "name")]
        # 报障2.: HB 名字行通过 "alpha", 但站点行含 "mteam" ⇒ 整种子排除; 去负词后名字行照常命中
        assert mgr.search_torrents("alpha -mteam")["results"] == []
        assert [(x["hash"], x["by"]) for x in mgr.search_torrents("alpha")["results"]] == [("HB", "name")]
        # 文件轮同受身份行否决: HC 名字行含 "repack" ⇒ 排除, 唯一文件行(Show.1080p.mkv)干净也救不回
        assert mgr.search_torrents("show -repack")["results"] == []
        # 对照: 去掉负词后 HC 靠文件行命中("show" 只落在文件行)
        assert [(x["hash"], x["by"]) for x in mgr.search_torrents("show")["results"]] == [("HC", "file")]


def test_search_torrents_facet_rows():
    """search_torrents 候选行覆盖全部文本面(26-09-26 单点化): 站点/分类/保存路径/标签行即时匹配

    正词逐词跨行(拍板 26-09-27 二次定案): 每个正词命中任一候选行(全称行/文件行)即可; 负词
    种子级(26-09-27): facet 行含负词 ⇒ 整种子排除。
    服务端此前的候选行只有 名字/文件, 搜站点/标签只在种子页(旧客户端行)能搜到而分组/追剧页
    搜不到 —— 跨页不一致; 单点化后三页同源, 用 by 定位首个通过的行类别(前端不消费, 测试定位用)。
    """
    from helpers import FakeClient, FakeTorrent, FakeTracker, make_manager, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        site = FakeTracker("MDCx")
        site.tags = []  # tracker_name 取 conf.name(FakeTracker 默认 tags=["HHan"] 会顶掉站点名)
        t1 = FakeTorrent(
            hash="HA",
            name="Alpha.S01E01",
            state="stalledUP",
            save_path="D:/media/anime",
            category="动漫",
            tags="HDCT, 2026",
            tracker_conf=site,
        )
        t2 = FakeTorrent(hash="HB", name="Beta.S01E02", state="stalledUP")
        seed_store(mgr, [t1, t2])
        mgr.build_search_index()

        # 站点/分类/标签/路径行: 各词只落在 HA 的对应行, 不在任何名字/文件里
        assert [(x["hash"], x["by"]) for x in mgr.search_torrents("MDCx")["results"]] == [("HA", "site")]
        assert [(x["hash"], x["by"]) for x in mgr.search_torrents("动漫")["results"]] == [("HA", "category")]
        assert [(x["hash"], x["by"]) for x in mgr.search_torrents("HDCT")["results"]] == [("HA", "tag")]
        assert [(x["hash"], x["by"]) for x in mgr.search_torrents("media anime")["results"]] == [("HA", "path")]
        # facet 行负词 = 整种子排除(2026-09-27 双轨定案): "anime -hdct" 标签行含负词 ⇒ 整种子排除,
        # 路径行干净也救不回(26-09-26 的「负词只作废该行」口径在此类行上被推翻)
        assert mgr.search_torrents("anime -hdct")["results"] == []
        # 同口径: "anime -media" 路径行含负词 ⇒ 整种子排除, 其余行不含 anime → 空结果
        assert mgr.search_torrents("anime -media")["results"] == []


def test_search_torrents_phrase():
    """search_torrents 短语: "…" 整段归一为**连续**子串(可含分隔符), 词序敏感 —— 与词间 AND 的区分用例"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        t1 = FakeTorrent(hash="HA", name="Cat.Dog.And.Bird", state="stalledUP")
        seed_store(mgr, [t1])

        # 词间 AND: cat 与 and 同行即命中(不要求相邻)
        assert [x["hash"] for x in mgr.search_torrents("cat and")["results"]] == ["HA"]
        # 短语: 要求归一后连续出现 —— "cat and" 在 "cat dog and" 里不连续 → 不命中; "dog and" 连续 → 命中
        assert mgr.search_torrents('"cat and"')["results"] == []
        assert [x["hash"] for x in mgr.search_torrents('"dog and"')["results"]] == ["HA"]
        # 短语可跨 scene 分隔符: "cat dog" 命中点号分隔的连续两词
        assert [x["hash"] for x in mgr.search_torrents('"cat dog"')["results"]] == ["HA"]


def test_search_torrents_regression_envnv10():
    """search_torrents 回归(26-09-26 用户报障): 「恶女 10」须命中单文件发布物; -排除词生效

    旧口径整句连续子串匹配: 「恶女 10」要求两词连续, 而文件名里「恶女」后跟「雏宫蝶鼠替换传」、
    「10」在远处的 s01e10 里 —— 必不命中。现行逐词跨行 AND 口径下两词同行照常命中。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        name = (
            "[虽然我不是完美恶女～雏宫蝶鼠替换传～].Futsutsuka.na.Akujo.dewa.Gozaimasu.ga."
            "Suuguu.Chouso.Torikae.Den.2026.S01E10.1080p.CR.WEB-DL.H264.AAC-UBWEB.mkv"
        )
        t1 = FakeTorrent(hash="HA", name=name, state="stalledUP")
        seed_store(mgr, [t1])

        r = mgr.search_torrents("恶女 10")
        assert [x["hash"] for x in r["results"]] == ["HA"], f"报障回归: 恶女 10 应命中: {r}"
        assert r["results"][0]["by"] == "name"
        # 短语与排除词: "s01e10" 连续命中; -ubweb 排除该发布组
        assert [x["hash"] for x in mgr.search_torrents('"s01e10"')["results"]] == ["HA"]
        assert mgr.search_torrents("恶女 10 -ubweb")["results"] == []


def test_search_torrents_negative_only_empty():
    """search_torrents 仅负词/空查询: 无正判据返回空 + negative_only 标记(前端提示依据), 不投递索引构建"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        t1 = FakeTorrent(hash="HA", name="Alpha", state="stalledUP")
        seed_store(mgr, [t1])

        r = mgr.search_torrents("-dv")
        assert r == {
            "results": [],
            "building": False,
            "negative_only": True,
            "rev": mgr.web.search_rev
        }, "仅负词: 空结果 + negative_only + 当前搜索版本号"
        assert mgr.web.commands.empty(), "仅负词无从起搜, 不应投递构建命令"
        # 空查询: 同样空结果, 但 negative_only=False(前端按普通空态处理)
        r2 = mgr.search_torrents("")
        assert r2 == {"results": [], "building": False, "negative_only": False, "rev": mgr.web.search_rev}


def test_search_torrents_rev_snapshot_before_read():
    """守阵(plan 26-11-03-0120 S4): search_rev 在读取 store 快照**之前**取值

    若把取值写在迭代/构行之后, 搜索期间新增的种子可能已读到、却没带进新版本号 ⇒ 该响应
    自报"最新", 前端不再补刷 ⇒ 漏更新。本用例在构行时自增版本号, 钉住响应仍带回旧 rev。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        seed_store(mgr, [FakeTorrent(hash="HA", name="Alpha")])
        base = mgr.web.search_rev
        orig = mgr._member_view

        def bump(rec):
            mgr.web.note_search_data_changed()
            return orig(rec)

        with mock.patch.object(mgr, "_member_view", side_effect=bump):
            r = mgr.search_torrents("alpha")
        assert r["rev"] == base, f"版本号必须在读快照前取值: {r['rev']} != {base}"
        assert mgr.web.search_rev > base, "自增必须生效(供下一轮轮询发现落后)"
        assert [x["hash"] for x in r["results"]] == ["HA"]


def test_api_state_reports_search_rev(web_env):
    """(plan 26-11-03-0120 S3) search_rev 恒回传且 /api/state 与 /api/status 同源"""
    mgr, client = web_env
    auth = {_AUTH_HEADER_KEY: f"Bearer {mgr.web.token}"}
    status = client.get("/api/status", headers=auth).json()
    state = client.get("/api/state", headers=auth).json()["status"]
    assert status["search_rev"] == state["search_rev"] == mgr.web.search_rev
    mgr.web.note_search_data_changed()
    state2 = client.get("/api/state", headers=auth).json()["status"]
    assert state2["search_rev"] == mgr.web.search_rev > status["search_rev"], \
        "数据变化后 /api/state 必须回传新版本(rid 门控不得吞掉它)"


def test_search_torrents_file_match():
    """search_torrents: 文件列表匹配(依赖已构建的索引), 命中文件名"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        from helpers import _fake_file
        client.files_map["HA"] = [_fake_file("movie.mkv", 0)]
        client.files_map["HB"] = [_fake_file("soundtrack.flac", 0)]
        # 季包回归(26-09-26 报障): 包名不含集号 "12", 查询词只在集文件名里 —— 文件行必须命中
        client.files_map["HC"] = [
            _fake_file("The.Cat.and.the.Dragon.S01E12.1080p.friDay.WEB-DL.AAC2.0.H.264-MWeb.mkv", 0),
        ]
        t1 = FakeTorrent(hash="HA", name="Alpha", state="stalledUP")
        t2 = FakeTorrent(hash="HB", name="Beta", state="stalledUP")
        t3 = FakeTorrent(
            hash="HC", name="The.Cat.and.the.Dragon.S01.1080p.friDay.WEB-DL.AAC2.0.H.264-MWeb", state="stalledUP"
        )
        seed_store(mgr, [t1, t2, t3])
        mgr.build_search_index()  # 先构建索引

        # 文件命中: soundtrack 只在 HB 的文件里, 不在任何种子名中
        r = mgr.search_torrents("soundtrack")
        hashes = [x["hash"] for x in r["results"]]
        assert hashes == ["HB"], f"文件匹配应命中 HB: {r}"
        assert r["results"][0]["by"] == "file"
        assert r["building"] is False, "索引已就绪不应 building"

        # 季包: 名行含 cat 不含 12(12 不在任何全称行), 集文件行同含两词 → file 兜底命中
        r = mgr.search_torrents("cat 12")
        assert [(x["hash"], x["by"]) for x in r["results"]] == [("HC", "file")], f"季包集文件应命中: {r}"


def test_search_torrents_building_triggers():
    """search_torrents: 索引脏(种子集变化后)时返回 building=true 并投递构建命令"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store, _fake_file

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.files_map["HA"] = [_fake_file("movie.mkv", 0)]
        t1 = FakeTorrent(hash="HA", name="Alpha", state="stalledUP")
        seed_store(mgr, [t1])

        mgr.web.search_index_dirty = True  # 模拟种子集变化后未构建
        r = mgr.search_torrents("movie")
        assert r["building"] is True, "索引脏时 building 应为 True"
        # 名称未命中, 文件索引未就绪 -> 无结果, 但投递了构建命令
        assert r["results"] == []
        cmd, payload = mgr.web.commands.get_nowait()
        assert cmd == "build_search_index" and payload == {}

        # 主循环构建后再查 -> building 消除且文件匹配生效
        mgr._cmd_build_search_index()
        r2 = mgr.search_torrents("movie")
        assert r2["building"] is False
        assert [x["hash"] for x in r2["results"]] == ["HA"]


def test_api_search_endpoint(web_env):
    """GET /api/search: 端点返回搜索结果(名称匹配即时), 空查询返回空"""
    mgr, client = web_env
    auth = {_AUTH_HEADER_KEY: f"Bearer {mgr.web.token}"}
    # mock 替身: 直接返回固定结果(端点仅做转发, 逻辑由 search_torrents 单测覆盖); 空查询返回空
    mgr.search_torrents = lambda q: (
        {
            "results": [],
            "building": False
        } if not (q or "").strip() else {
            "results": [{
                "hash": "H1",
                "name": q,
                "by": "name"
            }],
            "building": False
        }
    )
    r = client.get("/api/search", params={"q": "movie"}, headers=auth).json()
    assert r["results"][0]["name"] == "movie"
    r2 = client.get("/api/search", params={"q": ""}, headers=auth).json()
    assert r2["results"] == [] and r2["building"] is False
    # 鉴权: 无密钥 401
    assert client.get("/api/search", params={"q": "movie"}).status_code == 401
