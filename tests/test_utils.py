"""test_utils 测试计划: utils 工具函数

## 测试计划(每个测试函数一条)
- test_parse_time: 时间字符串解析
- test_parse_fsize: 文件大小解析
- test_parse_speed: 速度解析
- test_parse_hr_condition: HR 条件解析
- test_parse_bool: 布尔解析
- test_convert_bool_in_dict: 字典内布尔转换
- test_compare: 比较操作符
- test_add_long_path_prefix_for_win: Windows 长路径前缀
- test_extract_tracker_hostnames: 提取 tracker hostname
- test_match_tracker_confs: tracker 配置匹配
- test_match_tag_patterns: 标签模式匹配
- test_match_path_patterns: 路径模式匹配
- test_match_pattern_parse: MatchPattern.parse 统一语法解析(regex: 前缀/:ignore_case 后缀/body/suffix)
- test_match_value_normalize: match_value 核心(normalize 规范化语义, 空模式跳过)
- test_check_filelist_all_ok: 文件列表全部一致(CheckingMixin.check_filelist)
- test_check_filelist_missing: 文件缺失
- test_check_filelist_size_mismatch: 文件大小不一致
- test_check_filelist_api_error: 文件列表 API 错误
- test_timer: 计时器
- test_os_platform_helpers: 平台判定(is_windows/is_linux/is_mac/is_posix)
- test_parse_time_empty: 空串 -> 0
- test_parse_time_invalid: 非法时间格式 -> ValueError
- test_parse_fsize_invalid_format: 非法大小格式 -> ValueError
- test_parse_fsize_invalid_unit: 非 iB 单位 -> ValueError
- test_parse_speed_empty: 空串 -> 0
- test_parse_speed_invalid: 非法速度格式 -> ValueError
- test_add_long_path_prefix_non_windows: 非 Windows 原样返回
- test_add_long_path_prefix_unc: UNC 路径 -> \\?\\UNC 前缀
- test_add_long_path_prefix_already_prefixed: 已加前缀 -> 原样返回
- test_parse_compare_invalid: 无效比较表达式 -> ValueError
- test_check_filelist_oserror: 读取文件异常 -> 无法读取文件(CheckingMixin.check_filelist)
- test_extract_tracker_hostnames_invalid_url: url 解析异常 -> 跳过
- test_match_tracker_confs_invalid_url: url 解析异常 -> 不匹配
- test_match_tag_patterns_empty_pattern: 空模式跳过
- test_path_normalize_empty: 空路径 -> 原样返回
- test_timer_us: us 单位计时
- test_is_manual_speed_limit: 奇数KiB手动限速保护(0/偶数不命中)
- test_replace_vars: ${required_seeding_time} 占位替换(有hr/无hr/tracker_conf=None 留原文)
- test_parse_bool_invalid: 非法布尔值 -> ValueError
"""
import os
import pytest
import sys
import tempfile
from types import SimpleNamespace

from auto_qb import utils
from auto_qb.mixins.checking import CheckingMixin
from helpers import FakeClient, FakeTorrent


def test_parse_time():
    assert utils.parse_time("3D") == 3 * 86400
    assert utils.parse_time("12H") == 12 * 3600
    assert utils.parse_time("30M") == 30 * 60
    assert utils.parse_time("10S") == 10


def test_parse_fsize():
    assert utils.parse_fsize("10MiB") == 10 * 1024**2
    assert utils.parse_fsize("1GiB") == 1024**3
    assert utils.parse_fsize("512KiB") == 512 * 1024
    assert utils.parse_fsize("100B") == 100


def test_parse_speed():
    assert utils.parse_speed("1000KiB/s") == 1000 * 1024
    assert utils.parse_speed("1MiB/s") == 1024**2
    assert utils.parse_speed("2GiB/s") == 2 * 1024**3


def test_parse_hr_condition():
    assert utils.parse_hr_condition("80%") == ("dlratio", 0.8)
    assert utils.parse_hr_condition("70%") == ("dlratio", 0.7)
    assert utils.parse_hr_condition("10MiB") == ("dlsize", 10 * 1024**2)
    assert utils.parse_hr_condition("") == ("dlratio", 0.8)  # 空 = 默认 80%
    assert utils.parse_hr_condition("100%") == ("dlratio", 1.0)


def test_parse_bool():
    for v in (True, "true", "True", "TRUE", "yes", "on", "1", 1):
        assert utils.parse_bool(v) is True, f"应解析为 True: {v!r}"
    for v in (False, "false", "False", "FALSE", "no", "off", "0", 0):
        assert utils.parse_bool(v) is False, f"应解析为 False: {v!r}"
    try:
        utils.parse_bool("invalid")
        assert False, "非法值应抛 ValueError"
    except ValueError:
        pass


def test_convert_bool_in_dict():
    d = {"a": "true", "b": {"c": "false", "d": "yes"}, "e": 1, "f": "notbool"}
    result = utils.convert_bool_in_dict(d)
    assert result["a"] is True
    assert result["b"]["c"] is False
    assert result["b"]["d"] is True
    assert result["e"] == 1  # 纯数字不转换
    assert result["f"] == "notbool"  # 非 bool 字符串保留


def test_compare():
    op, val = utils.parse_compare(">=100MiB", utils.parse_fsize)
    assert op == ">=" and val == 100 * 1024**2
    assert utils.compare(">", 5, 3)
    assert not utils.compare("<", 5, 3)
    assert utils.compare(">=", 5, 5)
    assert utils.compare("<=", 3, 5)
    assert utils.compare("==", 5, 5)
    assert utils.compare("!=", 5, 3)


def test_add_long_path_prefix_for_win(monkeypatch):
    """Windows 平台: 超长/短路径均加 \\\\?\\ 前缀 (monkeypatch 模拟 win32, 与 CI Linux 平台无关)"""
    monkeypatch.setattr(sys, "platform", "win32")
    long_path = r"C:\a" + "\\" + "x" * 300
    prefixed = utils.add_long_path_prefix_for_win(long_path)
    assert prefixed.startswith("\\\\?\\"), f"超长路径应加前缀: {prefixed}"
    short_path = r"C:\short"
    assert utils.add_long_path_prefix_for_win(short_path).startswith("\\\\?\\"), "短路径也加前缀"


def test_extract_tracker_hostnames():
    info = [
        {
            "url": "https://tracker.hhanclub.net/announce.php"
        },
        {
            "url": "http://kufirc.com/announce"
        },
        {
            "url": ""
        },
        {
            "url": "not-a-url"
        },
    ]
    hosts = utils.extract_tracker_hostnames(info)
    assert "tracker.hhanclub.net" in hosts
    assert "kufirc.com" in hosts
    assert len(hosts) == 2


def test_match_tracker_confs():
    confs = {
        "HHan": SimpleNamespace(name="HHan", domains=["tracker.hhanclub.net"]),
        "Kufirc": SimpleNamespace(name="Kufirc", domains=["kufirc.com"]),
    }
    matched = utils.match_tracker_confs(confs, ["https://tracker.hhanclub.net/announce.php"])
    assert [c.name for c in matched] == ["HHan"]
    matched2 = utils.match_tracker_confs(confs, ["https://sub.tracker.hhanclub.net/announce"])
    assert [c.name for c in matched2] == ["HHan"], "子域名应匹配"
    matched3 = utils.match_tracker_confs(confs, ["https://other.com/announce"])
    assert matched3 == []


def test_match_tag_patterns():
    assert utils.match_tag_patterns("HHan", ["HHan"])  # 精确
    assert not utils.match_tag_patterns("hhan", ["HHan"])  # 大小写敏感
    assert utils.match_tag_patterns("hhan", ["HHan:ignore_case"])  # ignore_case
    assert utils.match_tag_patterns("BTSCHOOL-OLD", ["regex:^BTSCHOOL"])  # 正则
    assert utils.match_tag_patterns("btschool-old", ["regex:^BTSCHOOL:ignore_case"])
    assert not utils.match_tag_patterns("HHan", ["regex:^BTSCHOOL"])
    assert not utils.match_tag_patterns("HHan", ["regex:[invalid"])  # 非法正则跳过
    assert not utils.match_tag_patterns("HHan", [])


def test_match_path_patterns():
    assert utils.match_path_patterns(r"R:\Downloads\Movie", [r"R:\Downloads\Movie"])  # 精确(反斜杠)
    assert utils.match_path_patterns("R:/Downloads/Movie", ["R:/Downloads/Movie"])  # 精确(正斜杠)
    assert utils.match_path_patterns(r"R:\Downloads\movie", ["R:/Downloads/Movie:ignore_case"])
    assert utils.match_path_patterns("R:/Downloads/Movie", ["regex:Downloads/Movie"])
    assert utils.match_path_patterns("R:/Downloads/Movie", ["regex:movie:ignore_case"])
    assert not utils.match_path_patterns("R:/Downloads/Movie", ["R:/Windows"])
    assert not utils.match_path_patterns("R:/Windows", ["regex:[invalid"])


def test_match_pattern_parse():
    """MatchPattern.parse: 'regex:' 前缀与 ':ignore_case' 后缀的统一解析(先剥后缀再识别前缀)"""
    p = utils.MatchPattern.parse("regex:foo:ignore_case")
    assert (p.raw, p.is_regex, p.ignore_case, p.core) == ("regex:foo:ignore_case", True, True, "foo")
    assert p.body == "regex:foo" and p.suffix == ":ignore_case"
    assert utils.MatchPattern.parse("tagA").body == "tagA"
    assert not utils.MatchPattern.parse("tagA").is_regex
    assert not utils.MatchPattern.parse("tagA").ignore_case
    p2 = utils.MatchPattern.parse("regex:^tag")
    assert (p2.is_regex, p2.ignore_case, p2.core, p2.suffix) == (True, False, "^tag", "")
    p3 = utils.MatchPattern.parse("tagA:ignore_case")
    assert (p3.is_regex, p3.ignore_case, p3.core, p3.body) == (False, True, "tagA", "tagA")


def test_match_value_normalize():
    """match_value: normalize 参数对候选值与精确模式主体生效, 正则主体不规范化(路径匹配语义)"""
    norm = utils.path_normalize
    assert utils.match_value(r"R:\Downloads\Movie", ["R:/Downloads/Movie"], normalize=norm)
    assert utils.match_value("R:/Downloads/Movie", [r"R:\Downloads\Movie"], normalize=norm)
    assert utils.match_value("R:/Downloads/Movie", ["regex:Downloads"], normalize=norm)
    assert utils.match_value("R:/Downloads/Movie", ["^R:"], normalize=norm) is False  # 非前缀正则不误用
    assert utils.match_value("", [""]) is False  # 空模式跳过(不与空值误等)


def test_check_filelist_all_ok():
    """文件齐全且大小一致 -> None(CheckingMixin.check_filelist)"""
    with tempfile.TemporaryDirectory() as td:
        fpath = os.path.join(td, "movie.mkv")
        with open(fpath, "wb") as f:
            f.write(b"x" * 100)
        client = FakeClient()
        tor = FakeTorrent(hash="H1", name="Movie", save_path=td)
        client.files = [SimpleNamespace(name="movie.mkv", size=100)]
        assert CheckingMixin.check_filelist(client, tor) is None


def test_check_filelist_missing():
    """文件不存在 -> 文件缺失"""
    with tempfile.TemporaryDirectory() as td:
        client = FakeClient()
        tor = FakeTorrent(hash="H1", name="Movie", save_path=td)
        client.files = [SimpleNamespace(name="not_exists.mkv", size=100)]
        result = CheckingMixin.check_filelist(client, tor)
        assert result is not None and "文件缺失" in result


def test_check_filelist_size_mismatch():
    """大小不一致 -> 文件大小不一致"""
    with tempfile.TemporaryDirectory() as td:
        fpath = os.path.join(td, "movie.mkv")
        with open(fpath, "wb") as f:
            f.write(b"x" * 100)
        client = FakeClient()
        tor = FakeTorrent(hash="H1", name="Movie", save_path=td)
        client.files = [SimpleNamespace(name="movie.mkv", size=200)]
        result = CheckingMixin.check_filelist(client, tor)
        assert result is not None and "文件大小不一致" in result


def test_check_filelist_api_error():
    """文件列表获取异常 -> 获取文件列表失败"""
    class Boom:
        def torrents_files(self, h):
            raise RuntimeError("boom")

    tor = FakeTorrent(hash="H1", name="Movie", save_path="")
    result = CheckingMixin.check_filelist(Boom(), tor)
    assert result is not None and "获取文件列表失败" in result


def test_timer():
    logs = []
    unit = "ms"

    @utils.timer(unit=unit, log_func=logs.append)
    def foo():
        return 42

    assert foo() == 42  # 返回原结果
    assert len(logs) == 1
    assert "foo 耗时" in logs[0] and "ms" in logs[0]


def test_os_platform_helpers(monkeypatch):
    """平台判断: is_windows/is_linux/is_mac/is_posix 随 sys.platform 变化"""
    monkeypatch.setattr(sys, "platform", "win32")
    assert utils.is_windows()
    assert not utils.is_linux()
    assert not utils.is_mac()
    assert not utils.is_posix()

    monkeypatch.setattr(sys, "platform", "linux")
    assert utils.is_linux()
    assert not utils.is_windows()
    assert utils.is_posix()

    monkeypatch.setattr(sys, "platform", "darwin")
    assert utils.is_mac()
    assert not utils.is_windows()
    assert utils.is_posix()

    monkeypatch.setattr(sys, "platform", "freebsd")
    assert not utils.is_windows()
    assert utils.is_posix()  # BSD 属 Unix 类


def test_parse_time_empty():
    """parse_time 空串 -> 0"""
    assert utils.parse_time("") == 0


def test_parse_time_invalid():
    """parse_time 非法格式 -> ValueError"""
    try:
        utils.parse_time("abc")
        assert False, "应抛 ValueError"
    except ValueError:
        pass


def test_parse_fsize_invalid_format():
    """parse_fsize 非法格式 -> ValueError"""
    try:
        utils.parse_fsize("abc")
        assert False, "应抛 ValueError"
    except ValueError:
        pass


def test_parse_fsize_invalid_unit():
    """parse_fsize 非 iB 单位(如 KB) -> ValueError"""
    try:
        utils.parse_fsize("10KB")
        assert False, "应抛 ValueError"
    except ValueError:
        pass


def test_parse_speed_empty():
    """parse_speed 空串 -> 0"""
    assert utils.parse_speed("") == 0


def test_parse_speed_invalid():
    """parse_speed 非法格式 -> ValueError"""
    try:
        utils.parse_speed("abc")
        assert False, "应抛 ValueError"
    except ValueError:
        pass


def test_add_long_path_prefix_non_windows(monkeypatch):
    """非 Windows 系统 -> 原样返回路径"""
    monkeypatch.setattr(sys, "platform", "linux")
    p = r"R:\Downloads\Movie"
    assert utils.add_long_path_prefix_for_win(p) == p


def test_add_long_path_prefix_unc(monkeypatch):
    """Windows 平台: UNC 路径 -> \\?\\UNC 前缀 (monkeypatch 模拟 win32)"""
    monkeypatch.setattr(sys, "platform", "win32")
    p = r"\\server\share\file"
    result = utils.add_long_path_prefix_for_win(p)
    assert result == r"\\?\UNC\server\share\file"


def test_add_long_path_prefix_already_prefixed(monkeypatch):
    """Windows 平台: 已加 \\?\\ 前缀 -> 原样返回 (monkeypatch 模拟 win32)"""
    monkeypatch.setattr(sys, "platform", "win32")
    p = r"\\?\C:\x"
    assert utils.add_long_path_prefix_for_win(p) == p


def test_parse_compare_invalid():
    """无效比较表达式 -> ValueError"""
    try:
        utils.parse_compare("   ", utils.parse_fsize)
        assert False, "应抛 ValueError"
    except ValueError:
        pass


def test_check_filelist_oserror(monkeypatch):
    """读取文件大小抛 OSError -> 无法读取文件"""
    with tempfile.TemporaryDirectory() as td:
        fpath = os.path.join(td, "movie.mkv")
        with open(fpath, "wb") as f:
            f.write(b"x" * 100)

        def boom(_p):
            raise OSError("denied")

        monkeypatch.setattr(os.path, "getsize", boom)
        client = FakeClient()
        tor = FakeTorrent(hash="H1", name="Movie", save_path=td)
        client.files = [SimpleNamespace(name="movie.mkv", size=100)]
        result = CheckingMixin.check_filelist(client, tor)
        assert result is not None and "无法读取文件" in result


def test_extract_tracker_hostnames_invalid_url(monkeypatch):
    """url 解析异常 -> 跳过该条目"""
    def boom(url):
        raise ValueError("bad url")

    monkeypatch.setattr("auto_qb.utils.urlparse", boom)
    assert utils.extract_tracker_hostnames([{"url": "https://x.com/a"}]) == set()


def test_match_tracker_confs_invalid_url(monkeypatch):
    """url 解析异常 -> 不匹配任何配置"""
    def boom(url):
        raise ValueError("bad url")

    monkeypatch.setattr("auto_qb.utils.urlparse", boom)
    confs = {"HHan": SimpleNamespace(name="HHan", domains=["tracker.hhanclub.net"])}
    assert utils.match_tracker_confs(confs, ["https://tracker.hhanclub.net/announce.php"]) == []


def test_match_tag_patterns_empty_pattern():
    """模式列表含空串 -> 跳过继续匹配后续模式"""
    assert utils.match_tag_patterns("HHan", ["", "HHan"])


def test_path_normalize_empty():
    """空路径 -> 原样返回"""
    assert utils.path_normalize("") == ""


def test_timer_us():
    """us 单位计时: 日志含 us 且返回原结果"""
    logs = []

    @utils.timer(unit="us", log_func=logs.append)
    def foo():
        return 7

    assert foo() == 7
    assert len(logs) == 1
    assert "us" in logs[0]


def test_is_manual_speed_limit():
    """奇数 KiB/s 视为用户手动设置: 0/偶数不命中; 三处保护共用此实现"""
    from auto_qb.utils import is_manual_speed_limit

    assert is_manual_speed_limit(2001 * 1024) is True
    assert is_manual_speed_limit(2000 * 1024) is False
    assert is_manual_speed_limit(0) is False  # 不限速
    assert is_manual_speed_limit(2048) is False  # 2KiB 偶数


def test_replace_vars():
    """replace_vars: ${required_seeding_time} -> tracker hr 原始值(_raw str); 无 hr 留原文"""
    from auto_qb.utils import replace_vars
    from helpers import _hr_rule

    class _Conf:
        pass

    # 有 hr: 替换为 _raw 字符串(如 "3D"), 不是秒数 int
    conf = _Conf()
    conf.hr = _hr_rule()
    assert replace_vars("seed-${required_seeding_time}", conf) == "seed-3D"
    assert replace_vars("plain", conf) == "plain"
    # hr=None: 占位无法解析, 留原文(不崩)
    conf2 = _Conf()
    conf2.hr = None
    assert replace_vars("seed-${required_seeding_time}", conf2) == "seed-${required_seeding_time}"
    # tracker_conf=None: 同上留原文
    assert replace_vars("seed-${required_seeding_time}", None) == "seed-${required_seeding_time}"


def test_parse_bool_invalid():
    """非法布尔值 -> ValueError(问题提早暴露)"""
    with pytest.raises(ValueError):
        utils.parse_bool("not-a-bool")


def test_parse_hm_invalid_format():
    """非法 HH:MM 格式 -> ValueError(带原文)"""
    with pytest.raises(ValueError, match="非法 HH:MM"):
        utils.parse_hm("abc")


def test_fmt_size_invalid():
    """fmt_size: 非数字输入返回 '-'"""
    assert utils.fmt_size("not-a-number") == "-"
    assert utils.fmt_size(None) == "-"
