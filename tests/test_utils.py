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
- test_atomic_write_creates_file: 原子写生成目标文件且不残留临时文件
- test_atomic_write_rejects_empty_path: 空路径直接 ValueError(否则临时文件落到 CWD 的父目录)
- test_atomic_write_failure_keeps_old_content: 写盘回调抛异常时旧内容不变(直写 open("w") 会先 truncate 成半截文件), 临时文件被清理
- test_atomic_write_keep_backup: keep_backup=True 写盘前复制 .bak; 无旧文件时不凭空造备份
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
- test_open_path_select_file_per_platform: open_path(select=True) 单文件定位选中(PIDL 不可用时 win explorer /select, · mac open -R · linux 退化父目录 · 非文件退化为普通打开)
- test_open_path_windows_long_path_uses_shell_pidl: Windows 长路径目录/定位选中走 Shell PIDL, 绝不触达 os.startfile 与 explorer
- test_open_path_windows_falls_back_to_string_route: PIDL 返回 False 时退回字符串路线(不静默什么都不做)
- test_open_path_non_windows_never_calls_shell_pidl: 非 Windows 平台绝不触达 PIDL 路线(防守阵假阳性)
- test_win_shell_open_non_windows_returns_false: 非 Windows 上 _win_shell_open 前置返回 False, 不碰 ctypes
- test_win_string_open_degrades_long_path_to_ancestor: 字符串路线遇超长路径上溯到最近的可达祖先
- test_exists_dir_file_apply_long_path_prefix: _exists_dir/_exists_file 对判定过长路径前缀 helper
- test_sanitize_tracker_url: tracker URL 脱敏只留主地址(query/path/fragment 整段丢, 任意凭据参数名都覆盖; udp 端口/userinfo 处理)
- test_sanitize_tracker_url_unparseable: 空/非字符串/解析不出 host -> 占位串且不抛异常(日志路径不得打断业务)
- test_display_host: 展示地址(回环 IPv4/IPv6/IPv4-mapped -> localhost, 对外地址与大小写原样, 异常入参不炸)
"""
import os
import pytest
import sys
import tempfile
from types import SimpleNamespace
from unittest import mock

from auto_qb.infra import utils
from auto_qb.core.mixins.checking import CheckingMixin
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
    # 边界在解析单点拦下(校验层经 _try 复用): "0%"/负数/超 100% 立即满足或永不触发, 均与配置意图相反
    with pytest.raises(ValueError):
        utils.parse_hr_condition("0%")
    with pytest.raises(ValueError):
        utils.parse_hr_condition("200%")
    with pytest.raises(ValueError):
        utils.parse_hr_condition("-5%")
    with pytest.raises(ValueError):
        utils.parse_hr_condition("0MiB")  # 下载量 0 同样立即满足


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

    monkeypatch.setattr("auto_qb.infra.utils.urlparse", boom)
    assert utils.extract_tracker_hostnames([{"url": "https://x.com/a"}]) == set()


def test_match_tracker_confs_invalid_url(monkeypatch):
    """url 解析异常 -> 不匹配任何配置"""
    def boom(url):
        raise ValueError("bad url")

    monkeypatch.setattr("auto_qb.infra.utils.urlparse", boom)
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
    from auto_qb.infra.utils import is_manual_speed_limit

    assert is_manual_speed_limit(2001 * 1024) is True
    assert is_manual_speed_limit(2000 * 1024) is False
    assert is_manual_speed_limit(0) is False  # 不限速
    assert is_manual_speed_limit(2048) is False  # 2KiB 偶数


def test_replace_vars():
    """replace_vars: ${required_seeding_time} -> tracker hr 原始值(_raw str); 无 hr 留原文"""
    from auto_qb.infra.utils import replace_vars
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


def _fake_windows(monkeypatch):
    """把宿主伪装成 Windows: 固定 `sys.platform` 并**中和长路径前缀**。

    宿主是 POSIX 时 `add_long_path_prefix_for_win` 会把 `\\\\?\\` 拼到 POSIX 路径上, 于是
    `os.path.isdir` 恒为 False —— 被测的是"平台分支逻辑"而不是"真在 Windows 上跑", 所以前缀
    在这里置成恒等(前缀本身的正确性由 `test_add_long_path_prefix_*` 三条单独覆盖)。
    """
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(utils, "add_long_path_prefix_for_win", lambda p: p)


def test_open_path_select_file_per_platform(tmp_path, monkeypatch):
    """open_path(select=True) 跨平台(R10-10): PIDL 不可用时 win explorer /select, · mac open -R · linux 退化父目录

    平台行为必须 monkeypatch sys.platform(CI 跑 Linux 而本项目以 Windows 为主);
    Windows 分支还要 patch `_win_shell_open`(PIDL 路线, 真调会弹资源管理器)与 `os.startfile`
    —— 后者在非 Windows 解释器上不存在, 故用 create=True。
    非文件目标 / 不存在目标一律退化为普通打开(动作类工具容错优先, 不抛错)。
    """
    f = tmp_path / "a.mkv"
    f.write_bytes(b"x")
    missing = tmp_path / "nope.mkv"

    # Windows: PIDL 路线不可用时退回 explorer /select,(打开父目录并选中该文件, 不是打开文件本身)
    _fake_windows(monkeypatch)
    with mock.patch.object(utils, "_win_shell_open", return_value=False), \
            mock.patch.object(utils.os, "startfile", create=True) as sfile, \
            mock.patch.object(utils.subprocess, "run") as run:
        utils.open_path(str(f), select=True)
        assert sfile.call_count == 0
        run.assert_called_once_with(["explorer", "/select,", os.path.normpath(str(f))], check=False)
        # 目标不是文件(目录) -> 普通打开该目录
        run.reset_mock()
        utils.open_path(str(tmp_path), select=True)
        assert run.call_count == 0
        sfile.assert_called_once_with(os.path.normpath(str(tmp_path)))
        # 目标文件不存在 -> 退化为普通打开(避免"点了没反应"还报错)
        sfile.reset_mock()
        utils.open_path(str(missing), select=True)
        sfile.assert_called_once_with(os.path.normpath(str(missing)))

    # macOS: open -R(Reveal in Finder)
    monkeypatch.setattr(sys, "platform", "darwin")
    with mock.patch.object(utils.subprocess, "run") as run:
        utils.open_path(str(f), select=True)
        run.assert_called_once_with(["open", "-R", str(f)], check=False)
        # 不带 select 时仍是普通打开
        run.reset_mock()
        utils.open_path(str(f))
        run.assert_called_once_with(["open", str(f)], check=False)

    # Linux: 无通用"选中"语义 -> 退化为打开父目录(明确降级优于静默失败)
    monkeypatch.setattr(sys, "platform", "linux")
    with mock.patch.object(utils.subprocess, "run") as run:
        utils.open_path(str(f), select=True)
        run.assert_called_once_with(["xdg-open", os.path.dirname(str(f))], check=False)


def test_open_path_windows_long_path_uses_shell_pidl(tmp_path, monkeypatch):
    """Windows 长路径: 目录 / 定位选中走 Shell PIDL, **绝不触达** os.startfile 与 explorer

    本次修复的核心断言 —— 实测超长路径下 `os.startfile` 抛 `FileNotFoundError`、
    `explorer /select,` **静默打开"桌面"**, 所以这两条路径对长路径必须完全不被触达。
    存在性判定与 PIDL 入口都 mock 掉(真调会弹资源管理器; 长路径在 POSIX 宿主上也不成立)。
    """
    _fake_windows(monkeypatch)
    long_dir = str(tmp_path) + "/" + "d" * 150 + "/" + "e" * 150
    long_file = long_dir + "/a.mkv"
    assert len(long_dir) >= utils.WIN_MAX_PATH, "用例前提: 目标确实是超长路径"

    with mock.patch.object(utils, "_win_shell_open", return_value=True) as pidl, \
            mock.patch.object(utils, "_exists_dir", return_value=True), \
            mock.patch.object(utils.os, "startfile", create=True) as sfile, \
            mock.patch.object(utils.subprocess, "run") as run:
        utils.open_path(long_dir)  # 目录 -> 打开该目录
        pidl.assert_called_once_with(long_dir)
        assert sfile.call_count == 0, "长路径目录不得退回 os.startfile"
        assert run.call_count == 0, "长路径目录不得退回 explorer"

    with mock.patch.object(utils, "_win_shell_open", return_value=True) as pidl, \
            mock.patch.object(utils, "_exists_file", return_value=True), \
            mock.patch.object(utils.os, "startfile", create=True) as sfile, \
            mock.patch.object(utils.subprocess, "run") as run:
        utils.open_path(long_file, select=True)  # 单文件种子 -> 打开父目录并选中
        pidl.assert_called_once_with(long_file)
        assert sfile.call_count == 0
        assert run.call_count == 0


def test_open_path_windows_falls_back_to_string_route(tmp_path, monkeypatch):
    """PIDL 路线返回 False 时, Windows 退回字符串路线 —— 不能静默什么都不做"""
    _fake_windows(monkeypatch)
    d = str(tmp_path)
    with mock.patch.object(utils, "_win_shell_open", return_value=False), \
            mock.patch.object(utils, "_exists_dir", return_value=True), \
            mock.patch.object(utils, "_win_string_open") as fallback:
        utils.open_path(d)
        fallback.assert_called_once_with(d, select=False)
    with mock.patch.object(utils, "_win_shell_open", return_value=False), \
            mock.patch.object(utils, "_exists_file", return_value=True), \
            mock.patch.object(utils, "_win_string_open") as fallback:
        utils.open_path(d + "/a.mkv", select=True)
        fallback.assert_called_once_with(d + "/a.mkv", select=True)


def test_open_path_non_windows_never_calls_shell_pidl(tmp_path, monkeypatch):
    """非 Windows 平台绝不触达 PIDL 路线

    守阵意义: 测试期副作用记账器把 `_win_shell_open` **整体计入 LAUNCH**(放行清单为空) ——
    若 POSIX 分支也去调它(哪怕它自己空转返回 False), 每次 `open_path` 都会记一条假阳性越界。
    """
    f = tmp_path / "a.mkv"
    f.write_bytes(b"x")
    for plat in ("linux", "darwin"):
        monkeypatch.setattr(sys, "platform", plat)
        with mock.patch.object(utils, "_win_shell_open") as pidl, \
                mock.patch.object(utils.subprocess, "run"):
            utils.open_path(str(f))
            utils.open_path(str(tmp_path), select=True)
            assert pidl.call_count == 0, f"{plat} 不得触达 PIDL 路线"


def test_win_shell_open_non_windows_returns_false(monkeypatch):
    """非 Windows 上 `_win_shell_open` 前置返回 False

    必须靠 `is_windows()` 早返回, 而不是靠捕获 `AttributeError` —— `ctypes.windll` 在 POSIX 上
    根本不存在, 让行为依赖"恰好抛了异常"会让 Linux CI 变成偶然通过。
    """
    for plat in ("linux", "darwin"):
        monkeypatch.setattr(sys, "platform", plat)
        assert utils._win_shell_open("/tmp/whatever") is False


def test_win_string_open_degrades_long_path_to_ancestor(monkeypatch):
    """字符串路线遇超长路径上溯到最近的可达祖先

    否则 `os.startfile` 对超长路径必抛 `FileNotFoundError`(即使目录确实存在) —— 上溯后长度
    < `WIN_MAX_PATH`, 故判定用裸路径即可(无需前缀)。
    """
    monkeypatch.setattr(sys, "platform", "win32")
    long_path = "C:/" + "/".join(["d" * 40] * 8)
    assert len(os.path.normpath(long_path)) >= utils.WIN_MAX_PATH, "用例前提: 入参超长"
    with mock.patch.object(utils.os, "startfile", create=True) as sfile:
        utils._win_string_open(long_path, select=False)
        opened = sfile.call_args.args[0]
        assert len(opened) < utils.WIN_MAX_PATH, "必须上溯到长度 < MAX_PATH 的祖先"
        assert os.path.normpath(long_path).startswith(opened), "上溯结果必须是原路径的祖先"


def test_exists_dir_file_apply_long_path_prefix(tmp_path, monkeypatch):
    """`_exists_dir` / `_exists_file` 的判定必须过 `add_long_path_prefix_for_win`

    长路径判定不前缀化会恒为 False(实测 `isdir` 给假) ⇒ 端点误报 404。这里用 spy 钉住
    "确实调了前缀 helper", 而不是断言真实 Windows 行为(CI 跑在 Linux)。
    """
    spy = mock.Mock(side_effect=lambda p: p)
    monkeypatch.setattr(utils, "add_long_path_prefix_for_win", spy)
    assert utils._exists_dir(str(tmp_path)) is True
    assert utils._exists_file(str(tmp_path / "x")) is False
    assert spy.call_args_list == [mock.call(str(tmp_path)), mock.call(str(tmp_path / "x"))]


# ---------------------------------------------------------------- 原子写


def test_atomic_write_creates_file(tmp_path):
    """原子写: 内容落到目标路径, 且同目录不残留临时文件"""
    from auto_qb.infra.utils import atomic_write

    p = tmp_path / "state.json"
    atomic_write(str(p), lambda f: f.write('{"a": 1}'))
    assert p.read_text(encoding="utf-8") == '{"a": 1}'
    assert sorted(c.name for c in tmp_path.iterdir()) == ["state.json"], "临时文件必须已被替换/清理"


def test_atomic_write_failure_keeps_old_content(tmp_path):
    """写盘回调抛异常时旧内容保持不变 —— 这是原子写存在的全部理由

    直接 `open(path, "w")` 会先 truncate: 写盘途中被杀/磁盘满/序列化异常都会留下**半截文件**,
    而 state.json 没有备份 ⇒ 执行历史与去重记录全丢, 重启后规则重放。
    """
    from auto_qb.infra.utils import atomic_write

    def _boom(_f):
        raise RuntimeError("simulated write failure")

    p = tmp_path / "state.json"
    p.write_text("OLD", encoding="utf-8")
    with pytest.raises(RuntimeError):
        atomic_write(str(p), _boom)
    assert p.read_text(encoding="utf-8") == "OLD", "失败时旧内容必须完好"
    assert sorted(c.name for c in tmp_path.iterdir()) == ["state.json"], "失败的临时文件必须清理"


def test_atomic_write_rejects_empty_path():
    """空路径直接 ValueError: 否则临时文件会落到 **CWD 的父目录**(仓库外)

    回归点(2026-09-19): `abspath("")` 是 CWD, 再 `dirname` 就是它的父目录 —— 空路径不会
    "什么都不写", 而是往仓库外面丢 `.xxxxxxxx.tmp`, 然后 `os.replace(tmp, "")` 失败再删掉,
    表现为"偶发、无害"的噪音(长期被误当成 IDE/工具产生的临时文件), 实为调用方漏传路径。
    """
    from auto_qb.infra.utils import atomic_write

    with pytest.raises(ValueError):
        atomic_write("", lambda f: f.write("x"))


def test_atomic_write_keep_backup(tmp_path):
    """keep_backup=True: 写盘前把当前文件复制为 .bak; 无旧文件时不凭空造备份

    备份路径一律按 `path + utils.BACKUP_SUFFIX` 断言(不写字面量): 后缀是写侧与 state 恢复侧
    共用的单点常量, 一旦有人在 atomic_write 里改回字面量, 这条就红 —— 否则两边命名漂移,
    备份写出去没人按同名读回来(issue 26-09-21-1347)。
    """
    from auto_qb.infra.utils import atomic_write

    p = tmp_path / "state.json"
    bak = tmp_path / ("state.json" + utils.BACKUP_SUFFIX)
    atomic_write(str(p), lambda f: f.write("NEW"), keep_backup=True)
    assert not bak.exists(), "无旧文件不应产生备份"

    atomic_write(str(p), lambda f: f.write("NEWER"), keep_backup=True)
    assert bak.read_text(encoding="utf-8") == "NEW"
    assert p.read_text(encoding="utf-8") == "NEWER"


def test_sanitize_tracker_url():
    """sanitize_tracker_url: 只留主地址(scheme://host[:port]), path/query/fragment 整段丢弃

    凭据参数名不统一(passkey 只是其一, 还有 authkey/token/uid 等任意命名), 所以**不按参数名
    过滤**而是整段丢弃 —— 否则每出现一个新站的新参数名就漏一次(issue 26-09-21-1408)。
    """
    from auto_qb.infra.utils import sanitize_tracker_url

    # 常见私站形态: 密钥在 query 里
    assert sanitize_tracker_url("https://pt.example.com/announce?passkey=abc123def456") == "https://pt.example.com"
    # 换任何参数名同样脱敏(不猜名字, 全丢)
    assert sanitize_tracker_url("https://pt.example.com/announce?authkey=zzz&uid=7") == "https://pt.example.com"
    assert sanitize_tracker_url("https://pt.example.com/announce/xyz?token=q") == "https://pt.example.com"
    # 端口保留(定位站点用), path/fragment 丢
    assert sanitize_tracker_url("https://pt.example.com:8443/announce/abc#frag") == "https://pt.example.com:8443"
    # udp tracker: 端口是主地址的一部分, 必须留
    assert sanitize_tracker_url("udp://tracker.opentrackr.org:1337/announce") == "udp://tracker.opentrackr.org:1337"
    # userinfo 凭据(http://user:pass@host)一并丢弃
    assert sanitize_tracker_url("http://user:sec@pt.example.com/announce") == "http://pt.example.com"
    # 无 scheme: urlparse 把 host 落进 path, 取首段兜底(仍不带 path 其余部分)
    assert sanitize_tracker_url("pt.example.com/announce?passkey=abc") == "pt.example.com"
    # 裸主地址原样(小写化)
    assert sanitize_tracker_url("HTTPS://PT.Example.COM") == "https://pt.example.com"


def test_sanitize_tracker_url_unparseable():
    """sanitize_tracker_url: 空/非字符串/解析不出 host -> 占位串, 且不抛异常

    调用方全在日志路径上(qB 写操作之后), 脱敏失败只能降级成占位, 不能把业务动作打断。
    """
    from auto_qb.infra.utils import SANITIZE_FALLBACK, sanitize_tracker_url

    for bad in ("", "   ", None, 123, "/announce?passkey=abc", "?", object()):
        assert sanitize_tracker_url(bad) == SANITIZE_FALLBACK, f"{bad!r} 应降级为占位串"

    # urlparse 自身抛异常(畸形输入)也不能冒泡出去 —— 脱敏在日志路径上, 炸了就打断 qB 写操作
    with mock.patch("auto_qb.infra.utils.urlparse", side_effect=ValueError("boom")):
        assert sanitize_tracker_url("https://pt.example.com/announce?passkey=abc") == SANITIZE_FALLBACK


def test_display_host():
    """display_host: 回环地址统一显示 localhost, 其余原样(只改展示, 不改监听面)

    动机(2026-09-25): 浏览器把 127.0.0.1 与 localhost 当两个 origin, 列偏好/登录态各存一份,
    提示里给 localhost 才能让用户每次都落在同一个 origin 上。
    """
    from auto_qb.infra.utils import display_host

    # 回环的四种写法都折成 localhost(含 IPv6 与 IPv4-mapped)
    for h in ("127.0.0.1", "::1", "::ffff:127.0.0.1", "0:0:0:0:0:0:0:1", " 127.0.0.1 ", "::FFFF:127.0.0.1"):
        assert display_host(h) == "localhost", f"{h!r} 应显示为 localhost"
    # 对外地址原样返回(不能把 0.0.0.0 / 局域网 IP 也折掉, 否则掩盖暴露面)
    for h in ("0.0.0.0", "192.168.1.10", "qb.example.com"):
        assert display_host(h) == h
    # 非字符串(配置缺失/取错类型)原样返回: 调用方都在日志路径上, 不该炸
    for bad in ("", None, 123):
        assert display_host(bad) == bad
