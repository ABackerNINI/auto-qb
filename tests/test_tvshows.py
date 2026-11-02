"""tvshows 剧集识别单元测试(追剧视图的解析核心)

## 测试计划 (与解析规则一一对应, 新增规则先补这里)

- [x] S01E05 基本解析(季号内嵌回填); S01E05-E06 / S01E05E06 区间; S01x05 形态
- [x] 1x05 旧 scene 风格(季号内嵌); 1920x1080 分辨率不误判
- [x] 第5集 / 第05-08集 / 第5话(話) / 第五集(中文数字)
- [x] EP05 / Episode 5 / E05; webdl5 类粘连不误判 E 模式
- [x] ShowE05 粘连不识别(E 模式左边界) —— 与 episodes 文件列表侧互为对照, 两族双向非对称 (issue 26-10-29-1328)
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
- [x] parse_files: 「季标记 + 发布后缀」目录(Season 2 (1080p)/S02 Complete/第2季(1080p) 等);
      多季合包与白名单外尾词仍判未知 (issue 26-10-29-1329-bug-b-r08e03-dir-season-anchor)
- [x] refine_with_files: 季包展开集数范围; unknown 抢救为 episode; 有明确集数不改;
      名称无季标记时 season_inferred 留痕
- [x] 中文数字百位进位与非法字符兜底(_cjk_int) (P2-a)
- [x] 季标记越界季号跳过 + 多模式最早位置保留 (P2-a)
- [x] 非 bare 集数起点 0 跳过(E0) (P2-a)
- [x] 剧名归一化 bigram 噪音成对剔除 (P2-a)
- [x] parse_files 目录段无季标记继续向后 (P2-a)
- [x] 零位标记名空段 title/key 皆空串 (title_and_key_4/5); 全 groupish 括号候选取尾候选不崩 (strip_group_22) (W3-S5)
- [x] parse_files 首文件无季继续扫后续文件 (parse_files_20); 标点剥除进聚合键 (normalize_key_15/16) (W3-S5)
- [x] 两轮扫描: 零位 bare 不劫持「季在中间、集在季后」的切分 (find_episode_2/11); 区间终点 999 合法 (find_episode_31) (W3-S5)
- [x] 名称标记优先: 带集数/日期且带 key 的结果不被文件集数改写 (refine_1) (W3-S5)
- [x] 年份窗口 1900-2099 两端闭区间 + 2100 反向对照 (bare_ok_9/10/11/12) (W3 余量)
- [x] 集数上下界: E9999 起点合法 / 区间终点 1000 超限 (find_episode_24/32) (W3 余量)
- [x] 目录季 1..99 闭区间: S99 收 / 第百季 拒 (dir_season_13/14) (W3 余量)
- [x] 非法日期跳过继续找后续合法日期 (find_date_18) (W3 余量)
- [x] CJK「百」裸写=100 且「第百季」不进季号 (cjk_int_27 / find_season_14) (W3 余量)
- [x] 归一化尾位 bigram(dual audio/dd plus/hdr10 plus) 成对剔除 (normalize_key_25) (W3 余量)
- [x] 噪音词挖空后连续空格在展示名中折叠 (title_and_key_37) (W3 余量)
- [x] 归一化循环不依赖手工步长递增, 多 bigram 标题正常返回 (timeout 34/38 代码侧防御) (W3 余量)
- [x] 标题尾 trim 字符集: 全角【】收尾剥除 (title_and_key_30) (W3 余量)
- test_anime_season_with_bare_episode
- test_bare_excludes_resolution_and_year
- test_bare_trailing_without_context_not_matched
- test_bracket_only_all_groupish_candidates
- test_bare_zero_not_episode
- test_bracket_form
- test_bracket_only_title_picks_last_candidate
- test_bracket_paren_form
- test_cjk_equivalence
- test_cjk_int_bare_hundred
- test_cjk_int_hundred_and_invalid_char
- test_dash_form
- test_date_basic
- test_date_invalid_not_date
- test_default_unknown_shared
- test_dir_season_99_boundary
- test_e05_glued_title_side_unknown
- test_e_lookalike_not_matched
- test_empty_name_defaults
- test_empty_or_noise_name_keyless
- test_episode_before_season
- test_episode_patterns
- test_episode_range_end_999_kept
- test_episode_scan_after_season_beats_zero_position_bare
- test_episode_upper_bounds
- test_episode_wins_over_date
- test_find_episode_non_bare_zero_skipped
- test_find_season_out_of_range_and_earliest_kept
- test_find_season_rejects_hundred_plus
- test_frozen
- test_fullwidth_brackets_kept_as_title
- test_group_prefix_stripped
- test_identity_diff_preserved
- test_invalid_date_continues_to_later_valid
- test_key_forms
- test_marker_cut_takes_first_position
- test_multi_season_unknown
- test_noise_gap_whitespace_collapsed_in_title
- test_noise_tokens_stripped
- test_normalization_equivalence
- test_normalize_key_bigram_noise
- test_normalize_key_multi_bigram_terminates
- test_normalize_key_strips_punctuation
- test_normalize_key_tail_bigram_noise
- test_parse_files_multi_season_dir_unknown
- test_parse_files_no_season
- test_parse_files_s01_dir_and_zh_marker
- test_parse_files_season_and_episodes
- test_parse_files_season_dir_non_suffix_tail_unknown
- test_parse_files_season_dir_with_suffix
- test_parse_files_season_in_later_file
- test_parse_files_season_scan_skips_non_matching_parts
- test_range_end_from_resolution_dropped
- test_refine_explicit_episode_untouched
- test_refine_name_season_not_inferred
- test_refine_name_episode_and_date_untouched
- test_refine_no_usable_files_unchanged
- test_refine_season_from_files
- test_refine_season_from_suffixed_dir
- test_refine_season_pack
- test_refine_unknown_rescued
- test_season
- test_season_pack
- test_sxe_season_not_double_counted
- test_title_tail_trim_charset
- test_unknown
- test_year_window_bare_edges
- test_zero_position_marker_name_keyless
"""
import pytest

from auto_qb.core import tvshows
from auto_qb.core.tvshows import (
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

    def test_e05_glued_title_side_unknown(self):
        # ShowE05 粘连: E 模式要求左边界, 标题侧不识别 —— 与 episodes 文件列表侧对照
        # (episodes 认 ShowE05 -> [5], 两族双向非对称, issue 26-10-29-1328)
        r = p("ShowE05.mkv")
        assert r.kind == KIND_UNKNOWN

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
        assert (r.ep_start, ) == (7, )

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
            "Some.Movie.2023.1080p.BluRay.x265",  # 电影: 无集数/季标记(年份不是日期, 缺月日)
            "Some.Movie.2019.2160p",  # 同上
            "Oceans.11.2001.1080p.BluRay",  # 裸尾随数字不识别
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
        assert p("Show.Name.S01.Complete").episode_key == ("pack", )
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

    @pytest.mark.parametrize(
        "dir_name",
        [
            "Season 2 (1080p)",  # 季 + 画质后缀: 旧整段 $ 锚定拒绝(issue 26-10-29-1329)
            "S02 Complete",
            "第2季(1080p)",
            "Season 02 [1080p]",
            "2nd Season 1080p",
            "Show S02 Complete",  # 剧名 + 季标记 + 后缀: 放宽后的有意行为(issue §06 ②显式写明)
            "Show.S02.Complete",  # 点分隔同上
        ],
    )
    def test_parse_files_season_dir_with_suffix(self, dir_name):
        assert parse_files([f"Show/{dir_name}/E05.mkv"]) == (2, [5])

    def test_parse_files_multi_season_dir_unknown(self):
        # 多季合包无法归单季: 宁可未知也不错归 S1(放宽锚定后不得退化)
        assert parse_files(["Show/S01-S04/E05.mkv"]) == (None, [5])
        assert parse_files(["Show/第1-4季/E05.mkv"]) == (None, [5])

    def test_parse_files_season_dir_non_suffix_tail_unknown(self):
        # 白名单外的尾随词不算发布后缀: 不放宽成标题侧的模糊搜(防剧名尾词误判)
        assert parse_files(["Show/Season 2 of Show/E05.mkv"]) == (None, [5])

    def test_refine_season_from_suffixed_dir(self):
        # issue 26-10-29-1329: 名称无季标记 + 带后缀季目录 → season 2(曾静默落 S1);
        # 其余字段逐字不变, 且 season_inferred 留痕
        parsed = p("Show.1080p.Complete")
        r = refine_with_files(parsed, ["Show/Season 2 (1080p)/E05.mkv"])
        assert r.kind == KIND_EPISODE and r.season == 2
        assert (r.key, r.title, r.ep_start, r.ep_end) == (parsed.key, parsed.title, 5, None)
        assert r.season_inferred is True

    def test_refine_name_season_not_inferred(self):
        # 名称侧已有季标记: 季号沿用, season_inferred 不置位
        r = refine_with_files(p("Show.Name.S01.Complete.1080p"), ["Season 1/Show.S01E01.mkv"])
        assert r.season == 1 and r.season_inferred is False

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
        assert r.season_inferred is True  # 季 1 是「带集数无季标记」既有口径的兑底, 留痕

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


# ---------------- P2-a 长尾清偿 (计划 26-10-01-2157 §3 P2, 2026-10-02) ----------------


def test_cjk_int_hundred_and_invalid_char():
    """中文数字: 百位进位(含零/两)与非法字符兜底"""
    assert tvshows._cjk_int("一百零五") == 105
    assert tvshows._cjk_int("一百") == 100
    assert tvshows._cjk_int("两百三十四") == 234
    assert tvshows._cjk_int("十") == 10
    assert tvshows._cjk_int("甲") is None  # 非 CJK 数字字符: 解析失败
    assert tvshows._cjk_int("") is None


def test_find_season_out_of_range_and_earliest_kept():
    """季标记筛选: 越界季号(S00)跳过; 多模式命中时只保留最早位置(后见不取代先见)"""
    assert tvshows._find_season("S00") is None  # 季号 0 越界: 跳过
    assert tvshows._find_season("S00 Season 5 2nd Season") == (4, 12, 5)  # 后见的 2nd Season 不取代先见
    assert tvshows._find_season("S99") == (0, 3, 99)


def test_find_episode_non_bare_zero_skipped():
    """集数标记: 非 bare 模式起点 0(E0)跳过, 正常编号不受影响"""
    assert tvshows._find_episode("Show.Name.E0.1080p", None) is None
    assert tvshows._find_episode("Show.Name.E5.1080p", None) is not None


def test_normalize_key_bigram_noise():
    """剧名归一化: 相邻噪音 token 组成 bigram(dual audio/dd plus/hdr10 plus)成对剔除"""
    assert tvshows._normalize_key("Show Dual Audio 1080p") == "show 1080p"
    assert tvshows._normalize_key("Show DD Plus 1080p") == "show 1080p"
    assert tvshows._normalize_key("Show HDR10 Plus 1080p") == "show 1080p"


def test_parse_files_season_scan_skips_non_matching_parts():
    """parse_files: 目录段逐段扫季标记, 无季标记的目录段继续向后(不误报/不中断)"""
    season, eps = parse_files([r"SomeShow/Extra/file.mkv"])
    assert season is None
    season2, _ = parse_files([r"SomeShow/Season 02/file.mkv", r"Other/ep01.mkv"])
    assert season2 == 2


# ---------------- W3 变异审计定向补测 (S5, 2026-10-31) ----------------
# 真洞清单与守阵断言形态: tmp-analysis/mut-core-w3-classify.md「S4 verify 对账」(中危 9 条)


def test_zero_position_marker_name_keyless():
    """零位标记名("[01] ..."): 标记前段为空, title/key 皆空串(进未识别桶)

    title_and_key_4/5: 空段返回值被换成 "XXXX" -> 全部零位标记名误并进同一个假聚合桶
    (误并几乎不可发现, 本模块取向的头号恶); 展示面(title)与聚合面(key)两面都锁。
    """
    for name in ("[01]", "[01] Show Name"):
        r = p(name)
        assert r.key == "", f"{name!r} key 应为空串: {r}"
        assert r.title == "", f"{name!r} title 应为空串: {r}"


def test_bracket_only_all_groupish_candidates():
    """全括号候选均为组名特征: 取最后一个候选作标题(不崩、不取纯数字)

    strip_group_22(or->and): 全 groupish 候选时 (空 and cands)[-1] IndexError,
    parse_release 对 "[Subs][RAW][05]" 类命名整类崩溃。
    """
    r = p("[Subs][RAW][05]")
    assert r.title == "RAW"
    assert r.kind == KIND_EPISODE
    assert (r.season, r.ep_start) == (1, 5)


def test_parse_files_season_in_later_file():
    """首个文件无季不放弃: 继续扫后续文件, 季目录不在首位也能找到

    parse_files_20(break 条件反转): 首个文件无季即放弃 -> 丢季 -> refine 兜底误归 S1。
    """
    assert parse_files(["Show/file.mkv", "Season 02/E05.mkv"])[0] == 2
    # 反向对照: 首个文件已带季, 结果不变
    assert parse_files(["Season 02/E05.mkv", "Show/file.mkv"])[0] == 2


def test_normalize_key_strips_punctuation():
    """标点剥除进聚合键: "Show: Name" / "Re:Zero" 类标题标点不残留(同剧异写不误拆)

    normalize_key_15/16: 剥除正则加 XX 边界 / 替换串变 "XX XX" -> 标点残留或污染聚合键。
    """
    assert tvshows._normalize_key("Show: Name") == "show name"
    assert tvshows._normalize_key("Re:Zero") == "re zero"  # 无空格粘连的标点同样剥除


def test_episode_scan_after_season_beats_zero_position_bare():
    """两轮扫描: 有季标记时先在季标记之后找集数, 零位 bare 标记不得劫持切分

    find_episode_2/11(第一轮扫描被废 / search 丢 pos): "[05]" 在 0 位被选中 ->
    标题丢、key 空进未识别桶。断言形态取「零位 bare + 季 + 季后集数」组合;
    注: 无季的 "[05] Show.S01E05" 两形态同结果, 杀不动(classify 守阵形态已修正)。
    """
    r = p("[05] Show S2 - 05 [1080p]")
    assert r.title == "Show" and r.key == "show"
    assert (r.season, r.ep_start) == (2, 5)


def test_episode_range_end_999_kept():
    """区间终点 999 合法(end > 999 才判异常): S01E05-999 是 5-999 的区间包

    find_episode_31(>999 -> >=999): end==999 的合法区间被砍成单集。
    """
    r = p("Show.Name.S01E05-999")
    assert (r.ep_start, r.ep_end) == (5, 999)


def test_refine_name_episode_and_date_untouched():
    """名称标记优先于文件推断: 带集数/日期且带 key 的结果不被文件集数改写

    refine_1(or->and): 早退门被废 -> S01E05 被 EP01 改写、DATE 被改 EPISODE;
    两个 kind 各断言一份。反向对照(季包确实被文件展开)见 test_refine_season_pack。
    """
    parsed = p("Show.Name.S01E05.1080p")
    assert refine_with_files(parsed, ["Season 1/Show.S01E01.mkv"]) == parsed
    dated = p("Show.Name.2026.09.15.1080p")
    assert refine_with_files(dated, ["Season 1/Show.S01E01.mkv"]) == dated


# ---------------- W3 余量定向补测 (2026-11-02) ----------------
# 覆盖 W3 池遗留: 年份/bare 边界、CJK「百」、键归一、标题尾 trim
# (issue 26-10-31-1211 / 26-10-31-1212 四件, 同属标题/年月/键名归一化方向)


def test_year_window_bare_edges():
    """bare 年份窗口 1900-2099 是闭区间: 两端点都不当集数, 2100 是合法大编号

    bare_ok_9/10(1900<=n -> 1901<=n / 1900<n): 1900 漏排解成 ep 1900;
    bare_ok_11/12(n<=2099 -> n<2099 / n<=2100): 2099 漏排、2100 被误当年份。
    """
    assert p("[Group] Show - 1900 [1080p]").kind == KIND_UNKNOWN
    assert p("[Group] Show - 2099 [1080p]").kind == KIND_UNKNOWN
    assert p("Show - 2100 [1080p]").ep_start == 2100  # 反向对照: 窗口外仍认


def test_episode_upper_bounds():
    """集数上界: E9999 起点合法(<=9999); 区间终点 1000 超限应丢弃

    find_episode_24(start<=9999 -> <9999): E9999 起点被丢;
    find_episode_32(end>999 -> >1000): end==1000 应判异常终点却保留。
    """
    assert p("Show.Name.E9999").ep_start == 9999
    assert p("Show.Name.S01E05-1000").ep_end is None


def test_dir_season_99_boundary():
    """目录季 1..99 闭区间: S99 收进季号, 第百季(100)拒绝

    dir_season_13(s<=99 -> s<99): S99 目录被丢;
    dir_season_14(s<=99 -> s<=100): 「第百季」被收为季 100。
    """
    assert parse_files(["S99/E05.mkv"])[0] == 99
    assert parse_files(["第百季/E05.mkv"])[0] is None


def test_invalid_date_continues_to_later_valid():
    """非法日期跳过继续找: 同一名字里后面还有合法日期时仍判 DATE

    find_date_18(continue -> break): 首个坏日期(2023.13.99)即放弃 ->
    "Show.2023.13.99.2026.09.15" 原判 DATE 变 unknown。
    """
    r = p("Show.2023.13.99.2026.09.15")
    assert r.kind == KIND_DATE
    assert r.date == "2026-09-15"


def test_cjk_int_bare_hundred():
    """中文数字「百」裸写 = 100(缺省数字按 1 计, 不带进位语义)

    cjk_int_27((num or 1) -> (num or 2)): 「百」解成 200。
    """
    assert tvshows._cjk_int("百") == 100


def test_find_season_rejects_hundred_plus():
    """标题季标记 1..99: 「第百季」(100) 不进季号

    find_season_14(s<=99 -> s<=100): 「第百季」被收为季 100, 违反 1..99 口径。
    """
    assert tvshows._find_season("第百季") is None


def test_normalize_key_tail_bigram_noise():
    """归一化: 位于 tokens 末尾的相邻噪音 bigram 也要成对剔除

    normalize_key_25(i+1<len -> i+2<len): 尾位 bigram 边界失效,
    "Show Dual Audio" / "Show DD Plus" / "Show HDR10 Plus" 的噪音词残留进聚合键。
    注: issue 原建议的 "Show Web Dl" 不可达 —— "dl" 已在 _EXTRA_NOISE_TOKENS
    单 token 剔除, bigram 分支看不到它; 换用可达的三种 bigram。
    """
    assert tvshows._normalize_key("Show Dual Audio") == "show"
    assert tvshows._normalize_key("Show DD Plus") == "show"
    assert tvshows._normalize_key("Show HDR10 Plus") == "show"


def test_noise_gap_whitespace_collapsed_in_title():
    """噪音词被挖空留下的连续空格必须折叠, 否则展示名残留多空格

    title_and_key_37(\\s+ 折叠失效): "Show 1080p Name" 的 title 变 "Show   Name"。
    注: issue 原建议断言两形态 key 相等 —— 实测杀不动: _normalize_key 的
    str.split() 本身会折叠空白, key 恒为 "show name"; 真正可观测面是 title。
    """
    assert p("Show 1080p Name S01E05").title == p("Show Name S01E05").title == "Show Name"


def test_normalize_key_multi_bigram_terminates():
    """多 token / 多 bigram 标题正常返回(归一化循环不依赖手工步长递增)

    normalize_key_34(i+=2 -> i-=2) / normalize_key_38(i+=1 -> i=1) 是死循环形态,
    补测只能断言输入形态正常返回; 步长防御在 _normalize_key 的 for 循环侧。
    """
    assert tvshows._normalize_key("Show Dual Audio HDR10 Plus 1080p") == "show 1080p"


def test_title_tail_trim_charset():
    """标题尾 trim 字符集生效: 全角【】收尾必须剥除(展示面不残留)

    title_and_key_30(尾 strip 字符集 -> strip(None)): 末行只剥空白,
    "【剧名】第1集" 的 title 残留 "【剧名】"。
    注: issue 建议的 "Show - S01E05" 不可达 —— 切段后 " - " 已被
    首行 _TRIM_CHARS strip 提前剥净, 打不到末行 strip; 换用实测可达的【】形态。
    ("Show.Name.(US)" 的右括号同属该字符集, 当前展示名会剥成 "Show Name (US")
    """
    assert p("【剧名】第1集").title == "剧名"
