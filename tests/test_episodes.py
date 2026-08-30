"""test_episodes 测试计划: 集数标签

## 测试计划(每个测试函数一条)
- test_episode_tag_utils: 集数解析/格式化纯函数
- test_episode_tags_added_on_new_torrent: 新增种子添加集数标签
- test_episode_tags_not_on_existing_refresh: 已有种子刷新不加标签
- test_episode_tags_non_continuous_skipped: 非连续集数放弃
- test_episode_tags_ignore_date_screenshot: 日期型截图干扰忽略
- test_episode_tags_disabled: 配置关闭时不加标签
"""
import os
import tempfile
from types import SimpleNamespace

from auto_qb.episodes import extract_episodes_from_files, format_episode_tag, name_has_episode_marker
from auto_qb.qbmanager import QbManager
from helpers import FakeClient, FakeConfig, FakeTorrent


def _fake_file(name, size):
    return SimpleNamespace(name=name, size=size)


def test_episode_tag_utils():
    """集数解析纯函数: 名称标记判断 / 文件集数提取 / 区间合并"""
    # 名称含集数标记判断
    assert name_has_episode_marker("Show.S01E01-E05.1080p")
    assert name_has_episode_marker("Show.EP05")
    assert name_has_episode_marker("Show.第3集")
    assert name_has_episode_marker("Show.第01-05集")
    assert not name_has_episode_marker("Show.BD.BOX.Vol.1")
    assert not name_has_episode_marker("Movie.2024.1080p")

    # 文件列表集数提取: EP/E/第x集/SxxExx + 独立数字, 排除分辨率/年份
    files = [SimpleNamespace(name=n, size=1) for n in ["01.mkv", "02.mkv", "03.mkv", "04.mkv", "05.mkv"]]
    assert extract_episodes_from_files(files) == [1, 2, 3, 4, 5]
    files = [SimpleNamespace(name=n, size=1) for n in ["EP01.mkv", "EP02.mkv", "Show.S01E05.mkv"]]
    assert extract_episodes_from_files(files) == [1, 2, 5]
    files = [SimpleNamespace(name=n, size=1) for n in ["第3集.mkv", "第04-06集.mkv"]]
    assert extract_episodes_from_files(files) == [3, 4, 5, 6]
    # 排除干扰: 分辨率/年份/无数字
    files = [SimpleNamespace(name=n, size=1) for n in ["Movie.2024.1080p.mkv", "sample.mkv"]]
    assert extract_episodes_from_files(files) == []
    # 只考虑视频文件: 截图/字幕/字体等非视频文件即使含集数标记也跳过
    files = [SimpleNamespace(name=n, size=1) for n in ["第1集.jpg", "第2集.png", "01.srt", "02.ass"]]
    assert extract_episodes_from_files(files) == [], "非视频文件不应贡献集数"
    files = [SimpleNamespace(name=n, size=1) for n in ["01.mkv", "02.mkv", "03.ass", "04.jpg"]]
    assert extract_episodes_from_files(files) == [1, 2], "字幕/截图应被跳过"
    files = [SimpleNamespace(name=n, size=1) for n in ["Show.S01E05.ass"]]
    assert extract_episodes_from_files(files) == [], "字幕文件即使含 E 标记也跳过"
    # 只考虑文件名部分: 文件夹路径中的数字/集数标记不参与解析
    files = [SimpleNamespace(name=n, size=1) for n in ["Season 1/01.mkv", "Season 1/02.mkv"]]
    assert extract_episodes_from_files(files) == [1, 2], "文件夹名 Season 1 不应贡献集数"
    files = [SimpleNamespace(name=n, size=1) for n in ["第1季\\01.mkv", "第1季\\02.mkv"]]
    assert extract_episodes_from_files(files) == [1, 2], "文件夹名 第1季 不应贡献集数"
    files = [SimpleNamespace(name=n, size=1) for n in ["Show.S02/第1集.mkv"]]
    assert extract_episodes_from_files(files) == [1], "文件夹 S02 不应参与, 取文件 第1集"
    # 扩展名中的数字不应被当作集数(如 "xx.mp4" 的 4)
    files = [SimpleNamespace(name=n, size=1) for n in ["xx.mp4"]]
    assert extract_episodes_from_files(files) == [], "扩展名数字(如 mp4 的 4)不应被提取"
    files = [SimpleNamespace(name=n, size=1) for n in ["Show.01.mkv", "xx.mp4"]]
    assert extract_episodes_from_files(files) == [1], "xx.mp4 不应贡献数字 4"
    files = [SimpleNamespace(name=n, size=1) for n in ["Show.05.1080p.mkv", "Show.05.mkv"]]
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
    # 单文件多个候选数字(日期时间截图) -> 无法确定唯一集数, 跳过该文件
    files = [SimpleNamespace(name=n, size=1) for n in ["2022.05.11_14.51.23.jpg", "01.mkv", "02.mkv"]]
    assert extract_episodes_from_files(files) == [1, 2], "日期截图不应贡献集数"
    files = [SimpleNamespace(name=n, size=1) for n in ["2022.05.11_14.51.23.jpg"]]
    assert extract_episodes_from_files(files) == []
    # 无标记文件恰好一个候选数字(排除分辨率后) -> 提取
    files = [SimpleNamespace(name=n, size=1) for n in ["Show.Name.05.1080p.mkv"]]
    assert extract_episodes_from_files(files) == [5]
    # 文件名为空 -> 跳过, 不崩溃
    files = [SimpleNamespace(name="", size=1), SimpleNamespace(name="01.mkv", size=1)]
    assert extract_episodes_from_files(files) == [1], "空文件名应跳过"
    assert extract_episodes_from_files([SimpleNamespace(name=None, size=1)]) == []

    # 标签格式化: 必须连续, 非连续/空 -> 放弃(z 前缀使标签排序靠后)
    assert format_episode_tag([1, 2, 3, 4, 5]) == "zE1-5"
    assert format_episode_tag([1, 2, 3, 5]) == ""  # 缺集 -> 放弃
    assert format_episode_tag([3]) == "zE3"
    assert format_episode_tag([]) == ""


def test_episode_tags_added_on_new_torrent():
    """种子添加时自动添加集数标签(从文件列表解析)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
        cfg.state_file = state_file
        cfg.add_episode_tags = True
        mgr = QbManager("", config=cfg)
        client = FakeClient()
        mgr.client = client

        t1 = FakeTorrent(hash="H1", name="Show.S01E01", state="stalledUP")  # 名称含集数标记(仍解析文件)
        t2 = FakeTorrent(hash="H2", name="Show.S02.BluRay", state="stalledUP")  # 名称无集数 -> 解析
        client.torrents["H1"] = t1
        client.torrents["H2"] = t2
        client.files_map["H1"] = [_fake_file("Show.S01E01.mkv", 100)]
        client.files_map["H2"] = [_fake_file(f"{i:02d}.mkv", 100) for i in range(1, 6)]  # 01~05

        mgr._refresh_torrents()

        add_calls = [tags for name, tags in client.calls if name == "add_tags"]
        assert ["zE1-5"] in add_calls, f"H2 应添加 zE1-5 标签: {client.calls}"
        assert ["zE1"] in add_calls, f"H1 应解析文件并添加 zE1: {client.calls}"


def test_episode_tags_not_on_existing_refresh():
    """仅种子添加时触发, 后续刷新不重复拉取文件列表/不重复加标签"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
        cfg.state_file = state_file
        cfg.add_episode_tags = True
        mgr = QbManager("", config=cfg)
        client = FakeClient()
        mgr.client = client

        t1 = FakeTorrent(hash="H1", name="Show.BluRay", state="stalledUP")
        client.torrents["H1"] = t1
        client.files_map["H1"] = [_fake_file("01.mkv", 100)]

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
        cfg = FakeConfig()
        cfg.state_file = state_file
        cfg.add_episode_tags = True
        mgr = QbManager("", config=cfg)
        client = FakeClient()
        mgr.client = client

        t1 = FakeTorrent(hash="H1", name="Show.BluRay", state="stalledUP")
        client.torrents["H1"] = t1
        # 缺第4集: 1,2,3,5 非连续 -> 整体放弃
        client.files_map["H1"] = [_fake_file(f"{i:02d}.mkv", 100) for i in (1, 2, 3, 5)]

        mgr._refresh_torrents()

        assert not any(name == "add_tags" for name, _ in client.calls), f"非连续集数不应加标签: {client.calls}"


def test_episode_tags_ignore_date_screenshot():
    """附带日期时间截图(2022.05.11_14.51.23.jpg)不干扰集数解析"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
        cfg.state_file = state_file
        cfg.add_episode_tags = True
        mgr = QbManager("", config=cfg)
        client = FakeClient()
        mgr.client = client

        t1 = FakeTorrent(hash="H1", name="Show.BluRay", state="stalledUP")
        client.torrents["H1"] = t1
        client.files_map["H1"] = [
            _fake_file("2022.05.11_14.51.23.jpg", 100),
            *[_fake_file(f"{i:02d}.mkv", 100) for i in range(1, 6)],
        ]

        mgr._refresh_torrents()

        add_calls = [tags for name, tags in client.calls if name == "add_tags"]
        assert ["zE1-5"] in add_calls, f"截图应被忽略, 正常添加 zE1-5: {client.calls}"


def test_episode_tags_disabled():
    """add_episode_tags 关闭时不拉取文件列表/不加标签"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
        cfg.state_file = state_file
        cfg.add_episode_tags = False  # 默认关闭
        mgr = QbManager("", config=cfg)
        client = FakeClient()
        mgr.client = client

        t1 = FakeTorrent(hash="H1", name="Show.BluRay", state="stalledUP")
        client.torrents["H1"] = t1
        client.files_map["H1"] = [_fake_file("01.mkv", 100)]

        mgr._refresh_torrents()

        assert client.files_calls == 0, f"关闭时不应拉文件列表: {client.files_calls}"
        assert not any(name == "add_tags" for name, _ in client.calls), f"不应加标签: {client.calls}"
