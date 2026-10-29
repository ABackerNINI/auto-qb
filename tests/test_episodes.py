"""test_episodes 测试计划: 集数标签

## 测试计划(每个测试函数一条)
- test_episode_tag_utils: 集数解析/格式化纯函数
- test_episode_tags_added_on_new_torrent: 新增种子添加集数标签
- test_episode_tags_not_on_existing_refresh: 已有种子刷新不加标签
- test_episode_tags_non_continuous_skipped: 非连续集数放弃
- test_episode_tags_ignore_date_screenshot: 日期型截图干扰忽略
- test_episode_tags_disabled: 配置关闭时不加标签
- test_tvshows_side_forms_not_matched: 负测守阵(与 tvshows 族双向非对称, issue 26-10-29-1328)
"""
import os
import tempfile
from types import SimpleNamespace

import pytest

from auto_qb.config.models import AddEpisodeTagsConfig
from auto_qb.core.episodes import extract_episodes_from_files, extract_episodes_from_names, format_episode_tag, name_has_episode_marker
from helpers import FakeClient, FakeTorrent, _fake_file, make_manager


def test_episode_tag_utils():
    """集数解析纯函数: 名称标记判断 / 文件集数提取 / 区间合并"""
    # 名称含集数标记判断
    assert name_has_episode_marker("Show.S01E01-E05.1080p")
    assert name_has_episode_marker("Show.EP05")
    assert name_has_episode_marker("Show.第3集")
    assert name_has_episode_marker("Show.第01-05集")
    assert not name_has_episode_marker("Show.BD.BOX.Vol.1")
    assert not name_has_episode_marker("Movie.2024.1080p")

    # 文件列表集数提取: EP/E/第x集/SxxExx(bare number 暂禁用, 仅明确标记生效)
    files = [SimpleNamespace(name=n, size=1) for n in ["EP01.mkv", "EP02.mkv", "EP03.mkv", "EP04.mkv", "EP05.mkv"]]
    assert extract_episodes_from_files(files) == [1, 2, 3, 4, 5]
    files = [SimpleNamespace(name=n, size=1) for n in ["EP01.mkv", "EP02.mkv", "Show.S01E05.mkv"]]
    assert extract_episodes_from_files(files) == [1, 2, 5]
    files = [SimpleNamespace(name=n, size=1) for n in ["第3集.mkv", "第04-06集.mkv"]]
    assert extract_episodes_from_files(files) == [3, 4, 5, 6]
    # 排除干扰: 分辨率/年份/无数字
    files = [SimpleNamespace(name=n, size=1) for n in ["Movie.2024.1080p.mkv", "sample.mkv"]]
    assert extract_episodes_from_files(files) == []
    # 只考虑视频文件: 截图/字幕/字体等非视频文件即使含集数标记也跳过
    files = [SimpleNamespace(name=n, size=1) for n in ["第1集.jpg", "第2集.png", "EP01.srt", "EP02.ass"]]
    assert extract_episodes_from_files(files) == [], "非视频文件不应贡献集数"
    files = [SimpleNamespace(name=n, size=1) for n in ["EP01.mkv", "EP02.mkv", "EP03.ass", "EP04.jpg"]]
    assert extract_episodes_from_files(files) == [1, 2], "字幕/截图应被跳过"
    files = [SimpleNamespace(name=n, size=1) for n in ["Show.S01E05.ass"]]
    assert extract_episodes_from_files(files) == [], "字幕文件即使含 E 标记也跳过"
    # 只考虑文件名部分: 文件夹路径中的数字/集数标记不参与解析
    files = [SimpleNamespace(name=n, size=1) for n in ["Season 1/EP01.mkv", "Season 1/EP02.mkv"]]
    assert extract_episodes_from_files(files) == [1, 2], "文件夹名 Season 1 不应贡献集数"
    files = [SimpleNamespace(name=n, size=1) for n in ["第1季\\EP01.mkv", "第1季\\EP02.mkv"]]
    assert extract_episodes_from_files(files) == [1, 2], "文件夹名 第1季 不应贡献集数"
    files = [SimpleNamespace(name=n, size=1) for n in ["Show.S02/第1集.mkv"]]
    assert extract_episodes_from_files(files) == [1], "文件夹 S02 不应参与, 取文件 第1集"
    # 无集数标记的视频文件 -> 不提取(bare number 禁用)
    files = [SimpleNamespace(name=n, size=1) for n in ["xx.mp4"]]
    assert extract_episodes_from_files(files) == [], "无标记文件不应提取"
    files = [SimpleNamespace(name=n, size=1) for n in ["Show.01.mkv", "xx.mp4"]]
    assert extract_episodes_from_files(files) == [], "无标记文件不应提取(bare number 禁用)"
    files = [SimpleNamespace(name=n, size=1) for n in ["Show.E05.1080p.mkv", "Show.E05.mkv"]]
    assert extract_episodes_from_files(files) == [5]
    # 模式优先级: 第x集/S01E05 > EP05 > E05(单文件多模式时取优先级最高者)
    files = [SimpleNamespace(name=n, size=1) for n in ["Show.S01E05.EP03.E04.mkv"]]
    assert extract_episodes_from_files(files) == [5], "S01E05 应优先于 EP03/E04"
    files = [SimpleNamespace(name=n, size=1) for n in ["Show.EP03.E04.mkv"]]
    assert extract_episodes_from_files(files) == [3], "EP03 应优先于 E04"
    files = [SimpleNamespace(name=n, size=1) for n in ["Show.第3集.E05.mkv"]]
    assert extract_episodes_from_files(files) == [3], "第x集 应优先于 E05"
    files = [SimpleNamespace(name=n, size=1) for n in ["Show.第3-5集.S01E02.mkv"]]
    assert extract_episodes_from_files(files) == [3, 4, 5], "第x-y集 区间应优先展开"
    files = [SimpleNamespace(name=n, size=1) for n in ["Show.E05.mkv"]]
    assert extract_episodes_from_files(files) == [5]
    # 非视频文件含日期数字 -> 不贡献集数
    files = [SimpleNamespace(name=n, size=1) for n in ["2022.05.11_14.51.23.jpg", "EP01.mkv", "EP02.mkv"]]
    assert extract_episodes_from_files(files) == [1, 2], "日期截图不应贡献集数"
    files = [SimpleNamespace(name=n, size=1) for n in ["2022.05.11_14.51.23.jpg"]]
    assert extract_episodes_from_files(files) == []
    # 无标记文件不提取(bare number 禁用)
    files = [SimpleNamespace(name=n, size=1) for n in ["Show.Name.05.1080p.mkv"]]
    assert extract_episodes_from_files(files) == [], "无标记文件不提取(bare number 禁用)"
    # 文件名为空 -> 跳过, 不崩溃
    files = [SimpleNamespace(name="", size=1), SimpleNamespace(name="EP01.mkv", size=1)]
    assert extract_episodes_from_files(files) == [1], "空文件名应跳过"
    assert extract_episodes_from_files([SimpleNamespace(name=None, size=1)]) == []

    # 标签格式化: 必须连续, 非连续/空 -> 放弃(z 前缀使标签排序靠后)
    DEFAULT_SINGLE = "zE${episode_first}"
    DEFAULT_MULTI = "zE${episode_first}-${episode_last}"
    assert format_episode_tag([1, 2, 3, 4, 5], DEFAULT_SINGLE, DEFAULT_MULTI) == "zE1-5"
    assert format_episode_tag([1, 2, 3, 5], DEFAULT_SINGLE, DEFAULT_MULTI) == ""  # 缺集 -> 放弃
    assert format_episode_tag([3], DEFAULT_SINGLE, DEFAULT_MULTI) == "zE3"
    assert format_episode_tag([], DEFAULT_SINGLE, DEFAULT_MULTI) == ""
    # 自定义模板
    assert format_episode_tag([3], "E${episode_first}", "E${episode_first}-${episode_last}") == "E3"
    assert format_episode_tag([1, 2, 3, 4, 5], "E${episode_first}", "E${episode_first}-${episode_last}") == "E1-5"
    # [1, 5] 间隔 4 集 -> 不连续 -> 返回空
    assert format_episode_tag([1, 5], "single", "multi") == ""


@pytest.mark.parametrize(
    "name, expected",
    [
        ("Show.1x05.mkv", []),  # scene 风格: 仅 tvshows 侧识别
        ("Show.第五集.mkv", []),  # 中文数字: 仅 tvshows 侧识别
        ("Show.第5话.mkv", []),  # 话: 仅 tvshows 侧识别
        ("Show.第5話.mkv", []),  # 繁体 話: 仅 tvshows 侧识别
        ("Show.S01E05-E06.mkv", [5]),  # 区间续接不做: 按 S01E05 只取首集
    ],
)
def test_tvshows_side_forms_not_matched(name, expected):
    """负测守阵(issue 26-10-29-1328): episodes 族不认 tvshows 侧独有的形态

    episodes(文件列表路径)与 tvshows(种子标题路径)两族覆盖域不同、互有对方不认的形态,
    不是子集/超集 —— 本组用例钉住 episodes 侧不认的项: 谁要合并两族, 这里必红, 须显式
    改期望并说明行为 delta。对照面(tvshows 侧不认 ShowE05)见 test_tvshows.py 的
    test_showe05_glued_title_side_unknown。
    """
    assert extract_episodes_from_names([name]) == expected, f"{name!r} 解析结果不符现状"


def test_episode_tags_added_on_new_torrent():
    """种子添加时自动添加集数标签(从文件列表解析)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, add_episode_tags=AddEpisodeTagsConfig(enabled=True), client=client)

        t1 = FakeTorrent(hash="H1", name="Show.S01E01", state="stalledUP")  # 名称含集数标记(仍解析文件)
        t2 = FakeTorrent(hash="H2", name="Show.S02.BluRay", state="stalledUP")  # 名称无集数 -> 解析
        client.torrents["H1"] = t1
        client.torrents["H2"] = t2
        client.files_map["H1"] = [_fake_file("Show.S01E01.mkv", 100)]
        client.files_map["H2"] = [_fake_file(f"EP{i:02d}.mkv", 100) for i in range(1, 6)]  # EP01~05

        mgr._refresh_torrents()

        add_calls = [tags for name, tags in client.calls if name == "add_tags"]
        assert ["zE1-5"] in add_calls, f"H2 应添加 zE1-5 标签: {client.calls}"
        assert ["zE1"] in add_calls, f"H1 应解析文件并添加 zE1: {client.calls}"


def test_episode_tags_not_on_existing_refresh():
    """仅种子添加时触发, 后续刷新不重复拉取文件列表/不重复加标签"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, add_episode_tags=AddEpisodeTagsConfig(enabled=True), client=client)

        t1 = FakeTorrent(hash="H1", name="Show.BluRay", state="stalledUP")
        client.torrents["H1"] = t1
        client.files_map["H1"] = [_fake_file("EP01.mkv", 100)]

        mgr._refresh_torrents()  # 添加: 拉一次文件列表
        assert client.files_calls == 1, f"添加时应拉一次文件列表: {client.files_calls}"
        add_calls = [tags for name, tags in client.calls if name == "add_tags"]
        assert ["zE1"] in add_calls, f"应添加 zE1: {client.calls}"

        mgr._refresh_torrents()  # 后续刷新: 无新增, 不应再拉文件列表
        assert client.files_calls == 1, f"后续刷新不应再拉文件列表: {client.files_calls}"


def test_episode_tags_non_continuous_skipped():
    """集数非连续(存在缺集/误提取)时放弃添加标签"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, add_episode_tags=AddEpisodeTagsConfig(enabled=True), client=client)

        t1 = FakeTorrent(hash="H1", name="Show.BluRay", state="stalledUP")
        client.torrents["H1"] = t1
        # 缺第4集: 1,2,3,5 非连续 -> 整体放弃
        client.files_map["H1"] = [_fake_file(f"EP{i:02d}.mkv", 100) for i in (1, 2, 3, 5)]

        mgr._refresh_torrents()

        episode_calls = [
            tags for name, tags in client.calls if name == "add_tags" and any(t.startswith("zE") for t in tags)
        ]
        assert not episode_calls, f"非连续集数不应加标签: {client.calls}"


def test_episode_tags_ignore_date_screenshot():
    """附带日期时间截图(2022.05.11_14.51.23.jpg)不干扰集数解析"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, add_episode_tags=AddEpisodeTagsConfig(enabled=True), client=client)

        t1 = FakeTorrent(hash="H1", name="Show.BluRay", state="stalledUP")
        client.torrents["H1"] = t1
        client.files_map["H1"] = [
            _fake_file("2022.05.11_14.51.23.jpg", 100),
            *[_fake_file(f"EP{i:02d}.mkv", 100) for i in range(1, 6)],
        ]

        mgr._refresh_torrents()

        add_calls = [tags for name, tags in client.calls if name == "add_tags"]
        assert ["zE1-5"] in add_calls, f"截图应被忽略, 正常添加 zE1-5: {client.calls}"


def test_episode_tags_disabled():
    """add_episode_tags 关闭时不拉取文件列表/不加标签"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, add_episode_tags=AddEpisodeTagsConfig(), client=client)  # 默认 disabled

        t1 = FakeTorrent(hash="H1", name="Show.BluRay", state="stalledUP")
        client.torrents["H1"] = t1
        client.files_map["H1"] = [_fake_file("EP01.mkv", 100)]

        mgr._refresh_torrents()

        assert client.files_calls == 0, f"关闭时不应拉文件列表: {client.files_calls}"
        episode_calls = [
            tags for name, tags in client.calls if name == "add_tags" and any(t.startswith("zE") for t in tags)
        ]
        assert not episode_calls, f"不应加集数标签: {client.calls}"
