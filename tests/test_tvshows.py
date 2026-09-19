"""tvshows 剧集识别单元测试(追剧视图的解析核心)

## 测试计划 (与解析规则一一对应, 新增规则先补这里)

- [x] S01E05 基本解析(季号内嵌回填); S01E05-E06 / S01E05E06 区间; S01x05 形态
- [x] 1x05 旧 scene 风格(季号内嵌); 1920x1080 分辨率不误判
- [x] 第5集 / 第05-08集 / 第5话(話) / 第五集(中文数字)
- [x] EP05 / Episode 5 / E05; webdl5 类粘连不误判 E 模式
- [x] 季标记: S01 / Season 1 / 第一季(中文数字) / 第2期 / 2nd Season
- [x] S01E05 中的 S01 不被季模式重复命中(标题切分点正确)
- [x] 日期型: 2026.09.15 → ISO; 非法日期(2023.13.99)不判为日期
- [x] 动画 bare number: - 05 [1080p] / [Group][Show][05][1080p] / 行尾 - 05
- [x] bare number 排除: 分辨率(720/1080)与年份(1900-2099); 裸尾随数字不识别(Oceans.11)
- [x] bare number 排除 0: [00] / - 00 不得解出 ep_start=0(视图会多一个不存在的 0 集节点、标签生成 zE0)
- [x] 季包: Show.Name.S01.1080p / Show Name Season 1 → season_pack
- [x] 多季合包 S01-S04 / 第1-4季 → unknown
- [x] 身份差分保留: 年份/国家/续作数字参与聚合键(同剧异型不误并)
- [x] 剧名归一化等价: 大小写/分隔符/全角/噪音词(1080p/web-dl/DDP5.1/x265/中字)归一合并
- [x] 字幕组括号前缀: [Group] Title - 05 / [Group][Title][05]; 【剧名】保留
- [x] 未识别: 电影(无标记)/纯噪音 → kind=unknown 或 key 为空
- [x] parse_files: 目录段季号(Season 01/S01/第1季); 集数来自视频文件名
- [x] refine_with_files: 季包展开集数范围; unknown 抢救为 episode; 有明确集数不改
"""
import pytest

from auto_qb import tvshows
from auto_qb.tvshows import (
    KIND_DATE,
    KIND_EPISODE,
    KIND_SEASON_PACK,
    KIND_UNKNOWN,
    ParsedRelease,
    parse_files,
    parse_release,
    refine_with_files,
)


def p(name):
    return parse_release(name)


class TestEpisodePatterns:
    @pytest.mark.parametrize(
        "name, season, start, end",
        [
            ("Show.Name.S01E05.1080p.WEB-DL.x264", 1, 5, None),
            ("Show Name S02E12 1080p", 2, 12, None),
            ("Show.Name.S01E05-E06.720p", 1, 5, 6),
            ("Show.Name.S01E05E06", 1, 5, 6),
            ("Show.Name.S01x05.1080p", 1, 5, None),
            ("Show.Name.1x05.1080p", 1, 5, None),
            ("【剧名】第5集 1080p", 1, 5, None),
            ("剧名 第05-08集", 1, 5, 8),
            ("剧名 第5话", 1, 5, None),
            ("剧名 第五集", 1, 5, None),
            ("Show.Name.EP05.1080p", 1, 5, None),
            ("Show.Name.E05.1080p", 1, 5, None),
            ("Show Name Episode 5", 1, 5, None),
            ("Show.Name.E1080.1080p", 1, 1080, None),  # 大编号动画: 非 bare 模式不受分辨率排除
        ],
    )
    def test_episode_patterns(self, name, season, start, end):
        r = p(name)
        assert r.kind == KIND_EPISODE
        assert r.season == season
        assert r.ep_start == start
        assert r.ep_end == end

    def test_e_lookalike_not_matched(self):
        # "webdl5" 粘连: E 模式带左边界, 不应把 dl5 当集数
        r = p("Show.webdl5.1080p")
        assert r.kind != KIND_EPISODE

    def test_range_end_from_resolution_dropped(self):
        # E05-1080p 粘连: 终点 1080 超上限, 退化为单集
        r = p("Show.Name.S01E05-1080p")
        assert (r.ep_start, r.ep_end) == (5, None)

    def test_episode_before_season(self):
        # 集数标记写在季标记之前: 兜底全局扫描
        r = p("Show E05 S01 1080p")
        assert r.kind == KIND_EPISODE
        assert (r.season, r.ep_start) == (1, 5)

    def test_marker_cut_takes_first_position(self):
        # 标记前段才是剧名: 后续同形标记不参与
        r = p("Show.Name.S01E05.S01E06")
        assert r.key == "show name"
        assert r.ep_start == 5


class TestSeasonPatterns:
    @pytest.mark.parametrize(
        "name, season",
        [
            ("Show.Name.S01.1080p.BluRay", 1),
            ("Show Name Season 2 1080p", 2),
            ("Show.Name.S12.Complete", 12),
            ("剧名 第一季 4K", 1),
            ("剧名 第十二季", 12),
            ("Show 2nd Season - 05 [1080p]", 2),
            ("番名 第2期 1080p", 2),
        ],
    )
    def test_season(self, name, season):
        assert p(name).season == season

    def test_sxe_season_not_double_counted(self):
        # S01E05: 季模式被负向预查排除, 标题切分点 = E05 处, 剧名完整
        r = p("Show.Name.S01E05.1080p")
        assert r.title == "Show Name"
        assert r.key == "show name"

    def test_season_pack(self):
        r = p("Show.Name.S01.Complete.1080p.BluRay")
        assert r.kind == KIND_SEASON_PACK
        assert r.season == 1
        assert r.ep_start is None
        assert r.key == "show name"

    def test_multi_season_unknown(self):
        for name in ("Show.Name.S01-S04.Complete", "剧名 第1-4季 合集", "Show.Name.S01-S02"):
            assert p(name).kind == KIND_UNKNOWN, name


class TestDate:
    def test_date_basic(self):
        r = p("Show.Name.2026.09.15.1080p.WEB.h264")
        assert r.kind == KIND_DATE
        assert r.date == "2026-09-15"
        assert r.season is None
        assert r.key == "show name"

    def test_date_invalid_not_date(self):
        # 月份 13 不合法: 不判日期, 无其它标记 → unknown
        assert p("Show.Name.2023.13.99.1080p").kind == KIND_UNKNOWN

    def test_episode_wins_over_date(self):
        r = p("Show.Name.S01E05.2026.09.15.1080p")
        assert r.kind == KIND_EPISODE


class TestBareNumber:
    def test_dash_form(self):
        r = p("[SubGroup] Show Name - 05 [1080p][HEVC]")
        assert r.kind == KIND_EPISODE
        assert (r.season, r.ep_start) == (1, 5)
        assert r.title == "Show Name"

    def test_bracket_form(self):
        r = p("[SubGroup][Show Name][05][v2][1080p]")
        assert r.kind == KIND_EPISODE
        assert (r.season, r.ep_start) == (1, 5)
        assert r.title == "Show Name"

    def test_bracket_paren_form(self):
        r = p("Show Name (07) [1080p]")
        assert (r.ep_start,) == (7,)

    def test_bare_excludes_resolution_and_year(self):
        assert p("[Group] Show - 1080 [1080p]").kind == KIND_UNKNOWN
        assert p("[Group] Show - 2023 [1080p]").kind == KIND_UNKNOWN
        assert p("[Group] Show [2023] [1080p]").kind == KIND_UNKNOWN

    def test_bare_zero_not_episode(self):
        """bare 形态的 0 不是集数

        `_find_episode` 的 bare 分支只过 `_bare_ok`(不像非 bare 分支那样检查 1..9999),
        漏判会让 "[00]" / "- 00" 解出 ep_start=0 ⇒ 视图多一个不存在的 0 集节点、标签生成 zE0。
        正常编号 01 必须仍然识别(不能把 0 的排除扩散到前导零)。
        """
        for name in ("[00]", "Show - 00", "Show [00]"):
            r = p(name)
            assert r.kind != KIND_EPISODE, f"{name!r} 不应解为 episode: {r}"
            assert r.ep_start != 0, f"{name!r} 不应解出 ep_start=0: {r}"
        assert p("[01]").ep_start == 1
        assert p("Show - 01 [1080p]").ep_start == 1

    def test_bare_trailing_without_context_not_matched(self):
        # 裸尾随数字(Oceans.11): 无破折号/括号语境, 不识别为集数
        r = p("Oceans.11.2001.1080p.BluRay")
        assert r.kind == KIND_UNKNOWN

    def test_anime_season_with_bare_episode(self):
        # 季标记 + 破折号集数: S2 E5
        r = p("Show Name S2 - 05 [1080p]")
        assert r.kind == KIND_EPISODE
        assert (r.season, r.ep_start) == (2, 5)
        assert r.key == "show name"


class TestTitleAndKey:
    def test_group_prefix_stripped(self):
        assert p("[SubGroup] Show Name - 05 [1080p]").title == "Show Name"
        assert p("[Group] Show Name S01E05").key == "show name"

    def test_bracket_only_title_picks_last_candidate(self):
        # [Group][Title] 全括号形态: 取最后一个非组名候选
        r = p("[SubGroup][Show Name][05][1080p]")
        assert r.title == "Show Name"

    def test_fullwidth_brackets_kept_as_title(self):
        assert p("【剧名】第1集").key == "剧名"

    def test_noise_tokens_stripped(self):
        r = p("剧名 4K 中字 第1集")
        assert r.key == "剧名"
        r2 = p("Show.Name.WEB-DL.DDP5.1.HDR.x265.S01E05")
        assert r2.key == "show name"
        r3 = p("Show Name 1080p 中字 E05")
        assert r3.key == "show name"

    def test_identity_diff_preserved(self):
        # 年份/国家/续作数字是身份差分: 保留进聚合键, 互不合并
        keys = {
            p("Show Name 2019 S01E05").key,
            p("Show.Name.(US).S01E05").key,
            p("Show Name 2 S01E05").key,
            p("Show.Name.S01E05").key,
        }
        assert len(keys) == 4

    def test_normalization_equivalence(self):
        # 同剧异写: 大小写/分隔符/全角/噪音 → 同一聚合键
        keys = {
            p("Show.Name.S01E05.1080p.WEB-DL.x264-GROUP").key,
            p("show name s01e05").key,
            p("Show Name S01E05 2160p HDR 内嵌").key,
            p("[GROUP] Show Name - 05 [1080p]").key,
        }
        assert len(keys) == 1

    def test_cjk_equivalence(self):
        keys = {p("【剧名】第5集").key, p("剧名.第5集.1080p").key, p("剧名 第五集").key}
        assert len(keys) == 1


class TestUnknown:
    @pytest.mark.parametrize(
        "name",
        [
            "Some.Movie.2023.1080p.BluRay.x265",   # 电影: 无集数/季标记(年份不是日期, 缺月日)
            "Some.Movie.2019.2160p",               # 同上
            "Oceans.11.2001.1080p.BluRay",         # 裸尾随数字不识别
        ],
    )
    def test_unknown(self, name):
        assert p(name).kind == KIND_UNKNOWN

    def test_empty_or_noise_name_keyless(self):
        # 空名/纯噪音: 连剧名都提不出来, key 为空串
        for name in ("", "   ", "1080p.WEB-DL.x264"):
            assert not p(name).key

    def test_empty_name_defaults(self):
        r = parse_release(None)
        assert r.kind == KIND_UNKNOWN


class TestEpisodeKey:
    def test_key_forms(self):
        assert p("Show S01E05").episode_key == ("ep", 5)
        assert p("Show S01E05-E08").episode_key == ("range", 5, 8)
        assert p("Show.Name.S01.Complete").episode_key == ("pack",)
        assert p("Show.Name.2026.09.15.1080p").episode_key == ("date", "2026-09-15")


class TestFiles:
    def test_parse_files_season_and_episodes(self):
        names = [
            "Season 01/Show.S01E01.mkv",
            "Season 01/Show.S01E02.mkv",
            "Season 01/Show.S01E03.mkv",
            "poster.jpg",
        ]
        season, eps = parse_files(names)
        assert season == 1
        assert eps == [1, 2, 3]

    def test_parse_files_s01_dir_and_zh_marker(self):
        season, eps = parse_files(["S02/第05-06集.mkv"])
        assert season == 2
        assert eps == [5, 6]

    def test_parse_files_no_season(self):
        # episodes.py 不解析裸数字(误判率高), 文件名需带明确标记
        season, eps = parse_files(["Show E05.mkv"])
        assert season is None
        assert eps == [5]

    def test_refine_season_pack(self):
        parsed = p("Show.Name.S01.Complete.1080p")
        files = ["Season 1/Show.S01E01.mkv", "Season 1/Show.S01E02.mkv", "Season 1/Show.S01E03.mkv"]
        r = refine_with_files(parsed, files)
        assert r.kind == KIND_EPISODE
        assert r.episode_key == ("range", 1, 3)
        assert r.season == 1

    def test_refine_unknown_rescued(self):
        parsed = p("Show.Name.Pack.1080p")
        files = ["Show E05.mkv", "Show E06.mkv"]
        r = refine_with_files(parsed, files)
        assert r.kind == KIND_EPISODE
        assert (r.season, r.ep_start, r.ep_end) == (1, 5, 6)

    def test_refine_explicit_episode_untouched(self):
        parsed = p("Show.Name.S01E05.1080p")
        assert refine_with_files(parsed, ["other/xx.mkv"]) == parsed

    def test_refine_no_usable_files_unchanged(self):
        parsed = p("Show.Name.S01.Complete.1080p")
        assert refine_with_files(parsed, ["poster.jpg"]) == parsed

    def test_refine_season_from_files(self):
        parsed = p("Show.Name.Pack.1080p")
        files = ["Season 3/Show.E05.mkv"]
        r = refine_with_files(parsed, files)
        assert r.season == 3


class TestParsedReleaseContract:
    def test_frozen(self):
        r = p("Show S01E05")
        with pytest.raises(Exception):
            r.season = 9

    def test_default_unknown_shared(self):
        # 空/None 名共用同一个不可变实例即可(frozen dataclass)
        assert parse_release("") is parse_release("   ")
