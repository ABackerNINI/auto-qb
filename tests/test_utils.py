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
- test_auto_managed_tag_rules: 程序自动维护标签识别规则(站点/HR 精确集 + 集数模板形状; 事件标记/用户标签不在口径)
- test_match_path_patterns: 路径模式匹配
- test_match_pattern_parse: MatchPattern.parse 统一语法解析(regex: 前缀/:ignore_case 后缀/body/suffix)
- test_match_value_normalize: match_value 核心(normalize 规范化语义, 空模式跳过)
- test_check_filelist_all_ok: 文件列表全部一致(OpsModule.check_filelist)
- test_check_filelist_missing: 文件缺失
- test_check_filelist_qb_transitional_twin_hint: 缺失且 .!qB 孪生存在 -> 文案含疑似过渡态提示(返回语义不变)
- test_check_filelist_size_mismatch: 文件大小不一致
- test_check_filelist_api_error: 文件列表 API 错误
- test_qb_incomplete_twin_path: .!qB 后缀单点常量与孪生路径拼接(纯函数)
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
- test_check_filelist_oserror: 读取文件异常 -> 无法读取文件(OpsModule.check_filelist)
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
- test_open_path_windows_schedules_foreground_bringup: Windows 打开后调度后台置前(参数 = 打开前快照 + 目录名), 非 Windows 不调度
- test_win_foreground_new_explorer_new_window: 快照差集命中新窗口 -> 抬到顶层
- test_win_foreground_new_explorer_reused_window_title_match: 无新窗口(复用已有窗口) -> 按标题匹配抬到顶层; 标题不匹配不置前
- test_win_explorer_hwnds_non_windows_empty: 非 Windows 快照恒空集(不碰 ctypes)
- test_win_wait_explorer_prefers_new_window_over_title_match: 新窗口优先于标题匹配的复用窗口; 两者都无 -> None(超时)
- test_win_force_foreground_zorder_raised_even_when_focus_denied: 取焦被前台锁拒绝时 Z 序提升照做 + SwitchToThisWindow 兜底
- test_win_force_foreground_true_when_focus_taken: 抢到焦点即返回 True, 不再走兜底硬切
- test_win_force_foreground_dead_hwnd_silent: 句柄已失效 -> 零 API 调用, 返回 False
- test_win_topmost_once_toggles_and_clears: TOPMOST 挂一下立刻摘 + SWP_NOACTIVATE(只动顺序不抢焦)
- test_win_force_foreground_retries_until_focus: 单次被拒后有封顶重试(不无限执念)
- test_win_user32_kernel32_non_windows_none: 非 Windows 上句柄取用返回 None(靠早退而非"恰好抛异常")
- test_win_user32_binds_signatures: 每个 user32 API 必须绑死 argtypes —— 不绑时 x64 传参静默失效(本轮真根因的守阵)
- test_win_shell_open_non_windows_returns_false: 非 Windows 上 _win_shell_open 前置返回 False, 不碰 ctypes

### P1 覆盖率提升轮: infra 长尾
- test_atomic_write_backup_failure_continues: 备份失败只 WARNING, 写盘照常
- test_atomic_write_failure_cleans_temp_and_reraises: 写盘中途失败清理临时文件并上抛
- test_long_path_prefix_relative_path: 相对路径先转绝对再加前缀
- test_match_tracker_confs_skips_hostless_urls: 无 hostname 的 URL 跳过
- test_auto_managed_tag_rules_skips_empty_templates: 集数模板空串跳过不产正则
- test_timer_units_us_and_ms: timer 三种单位落日志
- test_win_shell_open_pidl_routes: PIDL 三分支(成功/解析失败/打开失败/COM 异常) + 前缀剥离 + 配对卸载
- test_win_user32_and_kernel32_bind_signatures: user32/kernel32 惰性句柄绑定与缓存
- test_win_explorer_hwnds_and_topmost_and_switch: Explorer 枚举/TOPMOST 开关/SwitchToThisWindow + 失败静默
- test_win_force_foreground_matrix: 三层升级矩阵(还原/显示/焦点/借线程/硬切/异常)
- test_win_reuse_and_wait_explorer: 复用窗口标题匹配/差集新窗口/超时 None/置前重试封顶
  (本组 Shell 测试全部用假替身, 不碰真窗口; _win_shell_open 直调经 sidefx._saved 取回原函数避开记账假阳性;
   平台差异: 涉及 Windows 分支的用例一律 monkeypatch sys.platform, 并用 `_shim_posix_ctypes` 在 POSIX 上
   补 `ctypes.windll`/`WINFUNCTYPE` 门面 —— 否则 Linux CI 上必红; `_win_reuse_title_candidates` 另把
   utils 模块内的 os 固定为 ntpath)
- test_win_string_open_degrades_long_path_to_ancestor: 字符串路线遇超长路径上溯到最近的可达祖先
- test_exists_dir_file_apply_long_path_prefix: _exists_dir/_exists_file 对判定过长路径前缀 helper
- test_sanitize_tracker_url: tracker URL 脱敏只留主地址(query/path/fragment 整段丢, 任意凭据参数名都覆盖; udp 端口/userinfo 处理)
- test_sanitize_tracker_url_unparseable: 空/非字符串/解析不出 host -> 占位串且不抛异常(日志路径不得打断业务)
- test_display_host: 展示地址(回环 IPv4/IPv6/IPv4-mapped -> localhost, 对外地址与大小写原样, 异常入参不炸)
"""
import ntpath
import os
import pytest
import sys
import tempfile
from types import SimpleNamespace
from unittest import mock

from auto_qb.infra import utils
from auto_qb.core.modules.ops_mod import OpsModule
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
    """文件齐全且大小一致 -> None(OpsModule.check_filelist)"""
    with tempfile.TemporaryDirectory() as td:
        fpath = os.path.join(td, "movie.mkv")
        with open(fpath, "wb") as f:
            f.write(b"x" * 100)
        client = FakeClient()
        tor = FakeTorrent(hash="H1", name="Movie", save_path=td)
        client.files = [SimpleNamespace(name="movie.mkv", size=100)]
        assert OpsModule.check_filelist(client, tor) is None


def test_check_filelist_missing():
    """文件不存在 -> 文件缺失"""
    with tempfile.TemporaryDirectory() as td:
        client = FakeClient()
        tor = FakeTorrent(hash="H1", name="Movie", save_path=td)
        client.files = [SimpleNamespace(name="not_exists.mkv", size=100)]
        result = OpsModule.check_filelist(client, tor)
        assert result is not None and "文件缺失" in result


def test_check_filelist_qb_transitional_twin_hint():
    """文件缺失但 <原名>.!qB 孪生存在 -> 文案追加疑似 qB 过渡态提示(返回语义不变, 仍非 None)"""
    with tempfile.TemporaryDirectory() as td:
        client = FakeClient()
        tor = FakeTorrent(hash="H1", name="Movie", save_path=td)
        client.files = [SimpleNamespace(name="movie.mkv", size=100)]
        with open(os.path.join(td, "movie.mkv.!qB"), "wb") as f:
            f.write(b"x" * 100)
        result = OpsModule.check_filelist(client, tor)
        assert result is not None, "孪生存在不改变返回语义(仍报缺失)"
        assert "文件缺失" in result
        assert "疑似 qB .!qB 过渡态" in result, f"应含过渡态提示(取证锚): {result}"

        # 对照: 无孪生 -> 纯缺失文案, 不带提示
        os.remove(os.path.join(td, "movie.mkv.!qB"))
        result2 = OpsModule.check_filelist(client, tor)
        assert result2 is not None and "文件缺失" in result2
        assert "过渡态" not in result2, f"无孪生不应带过渡态提示: {result2}"


def test_qb_incomplete_twin_path():
    """.!qB 后缀单点定义: QB_INCOMPLETE_SUFFIX 常量与 qb_incomplete_twin_path 拼接(纯字符串函数)"""
    assert utils.QB_INCOMPLETE_SUFFIX == ".!qB"
    assert utils.qb_incomplete_twin_path(r"D:/dl/movie.mkv") == r"D:/dl/movie.mkv.!qB"
    assert utils.qb_incomplete_twin_path("plain") == "plain.!qB"


def test_check_filelist_size_mismatch():
    """大小不一致 -> 文件大小不一致"""
    with tempfile.TemporaryDirectory() as td:
        fpath = os.path.join(td, "movie.mkv")
        with open(fpath, "wb") as f:
            f.write(b"x" * 100)
        client = FakeClient()
        tor = FakeTorrent(hash="H1", name="Movie", save_path=td)
        client.files = [SimpleNamespace(name="movie.mkv", size=200)]
        result = OpsModule.check_filelist(client, tor)
        assert result is not None and "文件大小不一致" in result


def test_check_filelist_api_error():
    """文件列表获取异常 -> 获取文件列表失败"""
    class Boom:
        def torrents_files(self, h):
            raise RuntimeError("boom")

    tor = FakeTorrent(hash="H1", name="Movie", save_path="")
    result = OpsModule.check_filelist(Boom(), tor)
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
        result = OpsModule.check_filelist(client, tor)
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


def test_auto_managed_tag_rules():
    """程序自动维护标签识别: 站点/HR 精确集 + 集数模板形状; 事件标记与用户标签不在口径内

    口径(2026-09-28 拍板): MISSING / zSkipChecked 等事件标记程序只打不摘, 留在候选才有
    摘除补救路径; 规则 add_tag 输出属用户自己的自动化 —— 两者都不进排除集。"""
    from auto_qb.config.models import AddEpisodeTagsConfig, Config, HRRule, TrackerConfig

    cfg = Config()
    cfg.trackers = {
        "HHan":
            TrackerConfig(
                name="HHan",
                domains=["d.com"],
                tags=["HHan", "常驻"],
                hr=HRRule(add_tag="HR-${required_seeding_time}", required_seeding_time_raw="3D"),
            ),
        "MTeam":
            TrackerConfig(name="MTeam", domains=["m.com"], tags=[]),
    }
    cfg.add_episode_tags = AddEpisodeTagsConfig(enabled=True)
    exact, patterns = utils.auto_managed_tag_rules(cfg)

    assert exact == {"HHan", "常驻", "HR-3D"}  # 站点 tags 全部 + HR 标签按站点展开(与维护路径同语义)
    assert utils.is_auto_managed_tag("HHan", exact, patterns)
    assert utils.is_auto_managed_tag("HR-3D", exact, patterns)
    assert utils.is_auto_managed_tag("zE1", exact, patterns)  # 单集模板形状
    assert utils.is_auto_managed_tag("zE1-12", exact, patterns)  # 多集模板形状
    assert not utils.is_auto_managed_tag("zE1-2-3", exact, patterns)  # 形状不合
    assert not utils.is_auto_managed_tag("zEa", exact, patterns)
    assert not utils.is_auto_managed_tag("MISSING", exact, patterns)  # 事件标记: 留候选
    assert not utils.is_auto_managed_tag("zSkipChecked", exact, patterns)
    assert not utils.is_auto_managed_tag("4K", exact, patterns)  # 普通用户标签

    # 集数标签关闭: 无模板正则, zE* 不再命中
    cfg.add_episode_tags = AddEpisodeTagsConfig(enabled=False)
    exact2, patterns2 = utils.auto_managed_tag_rules(cfg)
    assert patterns2 == ()
    assert not utils.is_auto_managed_tag("zE1", exact2, patterns2)

    # 全默认配置: 无 trackers 且集数标签关 -> 空规则, 任何标签都不算程序维护
    exact3, patterns3 = utils.auto_managed_tag_rules(Config())
    assert exact3 == set() and patterns3 == ()


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
    # 置前调度一并 stub: 真跑会起后台线程去枚举/推前台真实窗口(测试期不得碰)
    _fake_windows(monkeypatch)
    with mock.patch.object(utils, "_win_shell_open", return_value=False), \
            mock.patch.object(utils, "_win_foreground_explorer_async"), \
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
            mock.patch.object(utils, "_win_foreground_explorer_async"), \
            mock.patch.object(utils.os, "startfile", create=True) as sfile, \
            mock.patch.object(utils.subprocess, "run") as run:
        utils.open_path(long_dir)  # 目录 -> 打开该目录
        pidl.assert_called_once_with(long_dir)
        assert sfile.call_count == 0, "长路径目录不得退回 os.startfile"
        assert run.call_count == 0, "长路径目录不得退回 explorer"

    with mock.patch.object(utils, "_win_shell_open", return_value=True) as pidl, \
            mock.patch.object(utils, "_exists_file", return_value=True), \
            mock.patch.object(utils, "_win_foreground_explorer_async"), \
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
            mock.patch.object(utils, "_win_foreground_explorer_async"), \
            mock.patch.object(utils, "_win_string_open") as fallback:
        utils.open_path(d)
        fallback.assert_called_once_with(d, select=False)
    with mock.patch.object(utils, "_win_shell_open", return_value=False), \
            mock.patch.object(utils, "_exists_file", return_value=True), \
            mock.patch.object(utils, "_win_foreground_explorer_async"), \
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


def test_open_path_windows_schedules_foreground_bringup(tmp_path, monkeypatch):
    """Windows 打开后调度后台置前: 参数 = (打开前窗口快照, 目录名); 非 Windows 不调度

    用户报"打开目标文件夹有概率不弹出至顶层": 根因是后台进程调用 Shell 时新窗口被前台锁压住。
    open_path 负责快照 + 调度, 具体置前逻辑由 _win_foreground_new_explorer 单独覆盖。
    """
    _fake_windows(monkeypatch)
    f = tmp_path / "a.mkv"
    f.write_bytes(b"x")
    with mock.patch.object(utils, "_win_explorer_hwnds", return_value={7, 8}), \
            mock.patch.object(utils, "_win_shell_open", return_value=True), \
            mock.patch.object(utils, "_exists_file", return_value=True), \
            mock.patch.object(utils, "_win_foreground_explorer_async") as fg:
        utils.open_path(str(f), select=True)
        fg.assert_called_once_with({7, 8}, os.path.normpath(str(f)))
    # 目录目标同样调度
    with mock.patch.object(utils, "_win_explorer_hwnds", return_value=set()), \
            mock.patch.object(utils, "_win_shell_open", return_value=True), \
            mock.patch.object(utils, "_exists_dir", return_value=True), \
            mock.patch.object(utils, "_win_foreground_explorer_async") as fg:
        utils.open_path(str(tmp_path))
        fg.assert_called_once_with(set(), os.path.normpath(str(tmp_path)))
    # 非 Windows: 不调度(也不做快照)
    for plat in ("linux", "darwin"):
        monkeypatch.setattr(sys, "platform", plat)
        with mock.patch.object(utils, "_win_explorer_hwnds") as snap, \
                mock.patch.object(utils, "_win_foreground_explorer_async") as fg, \
                mock.patch.object(utils.subprocess, "run"):
            utils.open_path(str(f))
            assert snap.call_count == 0
            assert fg.call_count == 0


def test_win_foreground_new_explorer_new_window(monkeypatch):
    """快照差集命中新窗口 -> 立即抬到顶层(不空等超时)

    轮询超时压到极短: 本用例只验证"命中新窗口"这一条路径, 命中与否与超时长度无关。
    """
    monkeypatch.setattr(utils, "_EXPLORER_FG_TIMEOUT", 0.05)
    monkeypatch.setattr(utils, "_EXPLORER_FG_POLL", 0.01)
    before = {1, 2}
    seq = [before, before | {42}]
    monkeypatch.setattr(utils, "_win_explorer_hwnds", lambda: seq.pop(0) if seq else before | {42})
    monkeypatch.setattr(utils, "_win_window_text", lambda h: "")
    fg = mock.MagicMock(return_value=True)
    monkeypatch.setattr(utils, "_win_force_foreground", fg)
    assert utils._win_foreground_new_explorer(before, "dir") is True
    fg.assert_called_once_with(42)


def test_win_foreground_new_explorer_reused_window_title_match(monkeypatch):
    """无新窗口(Explorer 复用已有窗口导航) -> 按窗口标题匹配抬到顶层; 匹配不上不置前

    实测 SHOpenFolderAndSelectItems 打开的是**父窗口**并选中目标, 所以候选名含父目录名;
    Win11 标题带 " - 文件资源管理器" 后缀, 用 `名字 + " - "` 前缀匹配。
    """
    monkeypatch.setattr(utils, "_EXPLORER_FG_TIMEOUT", 0.05)
    monkeypatch.setattr(utils, "_EXPLORER_FG_POLL", 0.01)
    before = {5, 6}
    monkeypatch.setattr(utils, "_win_explorer_hwnds", lambda: before)
    # 目标 X:/downloads/f1.mkv: 窗口停在父目录 downloads(标题带本地化后缀) -> 命中
    texts = {5: "其它目录", 6: "downloads - 文件资源管理器"}
    monkeypatch.setattr(utils, "_win_window_text", lambda h: texts.get(h, ""))
    fg = mock.MagicMock(return_value=True)
    monkeypatch.setattr(utils, "_win_force_foreground", fg)
    assert utils._win_foreground_new_explorer(before, os.path.join("X:", "downloads", "f1.mkv")) is True
    fg.assert_called_once_with(6)
    # 标题对不上 -> 静默放弃, 绝不误推无关窗口
    fg.reset_mock()
    texts[6] = "别的 - 文件资源管理器"
    monkeypatch.setattr(utils, "_win_window_text", lambda h: texts.get(h, ""))
    assert utils._win_foreground_new_explorer(before, os.path.join("X:", "downloads", "f1.mkv")) is False
    assert fg.call_count == 0


class _FakeUser32:
    """user32 替身: 记录全部调用, 且**前台结果可控** —— 取焦被拒/成功的两条分支都能钉住

    为何要替身: 置前链路的 bug("有概率不弹到顶层")恰恰出在"某个 API 调用被系统静默拒绝"上,
    真调 user32 根本测不出这种分支(且会把开发机的窗口摆弄乱)。
    """
    def __init__(self, hwnd=42, fg=7, focus_after=None, switch_after=None, alive=(42, ), iconic=(), invisible=()):
        self.hwnd = hwnd
        self.fg = fg  # 当前前台窗口
        self.focus_after = focus_after  # SetForegroundWindow 之后的前台(None = 不变)
        self.switch_after = switch_after  # SwitchToThisWindow 之后的前台
        self.alive = set(alive)
        self.iconic = set(iconic)
        self.invisible = set(invisible)
        self.calls = []

    # ---- 查询 ----
    def IsWindow(self, h):
        return h in self.alive

    def IsIconic(self, h):
        return h in self.iconic

    def IsWindowVisible(self, h):
        return h not in self.invisible

    def GetForegroundWindow(self):
        return self.fg

    def GetWindowThreadProcessId(self, h, _lp):
        return 100

    # ---- 动作 ----
    def ShowWindow(self, h, cmd):
        self.calls.append(("ShowWindow", h, cmd))

    def SetWindowPos(self, h, insert, x, y, w, hh, flags):
        self.calls.append(("SetWindowPos", insert, flags))

    def AttachThreadInput(self, a, b, on):
        self.calls.append(("AttachThreadInput", a, b, on))
        return True

    def SetForegroundWindow(self, h):
        self.calls.append(("SetForegroundWindow", h))
        if self.focus_after is not None:
            self.fg = self.focus_after

    def SwitchToThisWindow(self, h, _alt):
        self.calls.append(("SwitchToThisWindow", h))
        if self.switch_after is not None:
            self.fg = self.switch_after

    def BringWindowToTop(self, h):
        self.calls.append(("BringWindowToTop", h))


def _install_fake_win(monkeypatch, **kw):
    """装上假 user32 / kernel32(只替换 `_win_user32` / `_win_kernel32`, 不碰 ctypes)"""
    monkeypatch.setattr(sys, "platform", "win32")
    u32 = _FakeUser32(**kw)
    monkeypatch.setattr(utils, "_win_user32", lambda: u32)

    class _K32:
        def GetCurrentThreadId(self):
            return 999

    monkeypatch.setattr(utils, "_win_kernel32", lambda: _K32())
    return u32


def test_win_wait_explorer_prefers_new_window_over_title_match(monkeypatch):
    """新窗口优先于标题匹配的复用窗口; 两条策略都落空 -> None(超时即放弃, 不无限等)

    旧实现把"复用/复用标题匹配"放在 2s 超时之后才做一次, 慢于 2s 的复用导航整个漏掉 ——
    这是本轮修复的核心回归面: 两条策略必须**每轮都试**。
    """
    monkeypatch.setattr(utils, "_EXPLORER_FG_TIMEOUT", 0.05)
    monkeypatch.setattr(utils, "_EXPLORER_FG_POLL", 0.01)
    before = {5, 6}
    # 既有新窗口 42, 也有标题匹配的旧窗口 6 -> 取新窗口
    monkeypatch.setattr(utils, "_win_explorer_hwnds", lambda: {5, 6, 42})
    monkeypatch.setattr(utils, "_win_window_text", lambda h: "downloads - 文件资源管理器" if h == 6 else "")
    target = os.path.join("X:", "downloads", "f1.mkv")
    assert utils._win_wait_explorer(before, target) == 42
    # 没有新窗口 -> 退到标题匹配的复用窗口
    monkeypatch.setattr(utils, "_win_explorer_hwnds", lambda: {5, 6})
    assert utils._win_wait_explorer(before, target) == 6
    # 两条都落空 -> 超时 None
    monkeypatch.setattr(utils, "_win_explorer_hwnds", lambda: {5, 6})
    monkeypatch.setattr(utils, "_win_window_text", lambda h: "无关窗口")
    assert utils._win_wait_explorer(before, target) is None


def test_win_topmost_once_toggles_and_clears(monkeypatch):
    """TOPMOST 挂一下立刻摘掉 + `SWP_NOACTIVATE`(只动 Z 序, 不抢焦点)

    摘是必须的: 留着 topmost 会让资源管理器长期钉在所有窗口之上, 比原来的 bug 更烦人;
    NOACTIVATE 是它能被后台进程受理的原因 —— 不受前台锁约束。
    """
    u32 = _install_fake_win(monkeypatch)
    utils._win_topmost_once(42)
    pos = [c for c in u32.calls if c[0] == "SetWindowPos"]
    assert pos == [("SetWindowPos", -1, 0x53), ("SetWindowPos", -2, 0x53)], "必须是 TOPMOST -> NOTOPMOST 成对调用"
    assert pos[0][2] & 0x0010, "必须带 SWP_NOACTIVATE: 靠它绕开前台锁"


def test_win_force_foreground_zorder_raised_even_when_focus_denied(monkeypatch):
    """前台锁拒绝取焦时, **Z 序提升照做** + 走 SwitchToThisWindow 兜底

    这是用户报障"有概率不弹出至顶层"的根因面: 后台进程 SetForegroundWindow 被静默拒绝 =>
    资源管理器留在浏览器后面。Window allows后台进程改 Z 序, 所以"看得见"必须与"抢得到焦点"解耦,
    且抬到顶层**不能**依赖任何一层成功。
    """
    u32 = _install_fake_win(monkeypatch, hwnd=42, fg=7, focus_after=7, switch_after=7)
    assert utils._win_force_foreground(42) is False
    kinds = [c[0] for c in u32.calls]
    assert "SetWindowPos" in kinds, "取焦失败也必须把窗口抬到顶层(Z 序)"
    assert "SetForegroundWindow" in kinds
    assert "SwitchToThisWindow" in kinds, "兜底硬切必须走到"
    # 连带效果: AttachThreadInput 必须成对(借了前台权限要还回去)
    attach = [c for c in u32.calls if c[0] == "AttachThreadInput"]
    assert [a[-1] for a in attach] == [True, False]


def test_win_force_foreground_true_when_focus_taken(monkeypatch):
    """抢到焦点即返回 True, 且不再多此一举走兜底硬切"""
    u32 = _install_fake_win(monkeypatch, hwnd=42, fg=7, focus_after=42)
    assert utils._win_force_foreground(42) is True
    kinds = [c[0] for c in u32.calls]
    assert "SwitchToThisWindow" not in kinds
    assert "BringWindowToTop" not in kinds


def test_win_force_foreground_dead_hwnd_silent(monkeypatch):
    """句柄已失效 -> 一个 user32 调用都不发, 返回 False(窗口可能早被关了)"""
    u32 = _install_fake_win(monkeypatch, hwnd=42, alive=())
    assert utils._win_force_foreground(42) is False
    assert u32.calls == []


def test_win_force_foreground_retries_until_focus(monkeypatch):
    """单次被拒后有**封顶**重试(前台锁是概率性的), 全部失败也返回 False 且不抛错"""
    monkeypatch.setattr(utils, "_EXPLORER_FG_RETRY_GAP", 0.0)
    monkeypatch.setattr(utils, "_win_wait_explorer", lambda before, target: 42)
    attempts = iter([False, False, True])
    monkeypatch.setattr(utils, "_win_force_foreground", lambda h: next(attempts))
    assert utils._win_foreground_new_explorer(set(), "dir") is True
    # 全部被拒: 不抛错, 只返回 False(置前是锦上添花)
    monkeypatch.setattr(utils, "_win_force_foreground", lambda h: False)
    assert utils._win_foreground_new_explorer(set(), "dir") is False


def test_win_user32_binds_signatures(monkeypatch):
    """`_win_user32` 必须给每个 API 绑死 argtypes(x64 ABI 陷阱的守阵)

    不绑时 ctypes 把 HWND 按 **32 位 int** 传, 指针宽度参数的高 32 位是寄存器残留:
    `SetWindowPos(hwnd, HWND_TOPMOST=0xFFFFFFFFFFFFFFFF, ...)` 收到畸形值 -> **返回 0 且
    GetLastError 仍为 0**(静默无效果)。2026-09-30 实测: 同一窗口同一时刻, 未绑 ret=0 Z 序不动,
    绑了 ret=1 立刻抬到顶层。这就是"有概率不弹到顶层"的真根因 —— 所以这一条不许退化。
    Windows 上跑真验收: 签名表里的函数必须全部绑上。
    """
    monkeypatch.setattr(sys, "platform", "win32")
    u32 = utils._win_user32()
    if u32 is None:  # POSIX 宿主: 早退本身由另一条覆盖, 这里只跳过真验收
        pytest.skip("非 Windows 宿主, 跳过签名绑定验收")
    for name, argtypes, _ in utils._WIN_USER32_SIGNATURES():
        fn = getattr(u32, name, None)
        assert fn is not None, f"{name} 在 user32 里不存在"
        assert fn.argtypes == list(argtypes), f"{name} 的 argtypes 没绑或绑错了(x64 传参会静默失效)"
    k32 = utils._win_kernel32()
    assert k32.GetCurrentThreadId.argtypes == []


def test_win_user32_kernel32_non_windows_none(monkeypatch):
    """非 Windows 上 user32 / kernel32 句柄取用返回 None(早退, 不靠"恰好抛异常")

    不为别的: `ctypes.windll` 在 POSIX 上不存在 —— 让行为依赖 AttributeError 会让 Linux CI
    变成偶然通过(本坑另有守阵 `test_win_shell_open_non_windows_returns_false`)。
    """
    for plat in ("linux", "darwin"):
        monkeypatch.setattr(sys, "platform", plat)
        assert utils._win_user32() is None
        assert utils._win_kernel32() is None
        assert utils._win_force_foreground(42) is False
        assert utils._win_window_text(42) == ""


def test_win_explorer_hwnds_non_windows_empty(monkeypatch):
    """非 Windows 上窗口快照恒空集, 不碰 ctypes(windll 在 POSIX 不存在)"""
    monkeypatch.setattr(sys, "platform", "linux")
    assert utils._win_explorer_hwnds() == set()


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


def test_atomic_write_backup_failure_continues(tmp_path, monkeypatch):
    """keep_backup 时备份失败(如权限) -> 只 WARNING, 写盘照常进行(不因备份失败丢新数据)"""
    target = tmp_path / "state.json"
    target.write_text("old", encoding="utf-8")

    def boom(src, dst):
        raise OSError(13, "拒绝访问")

    monkeypatch.setattr(utils.shutil, "copy2", boom)
    utils.atomic_write(str(target), lambda f: f.write("new"), keep_backup=True)
    assert target.read_text(encoding="utf-8") == "new"


def test_atomic_write_failure_cleans_temp_and_reraises(tmp_path):
    """写盘中途失败 -> 临时文件清理 + 原异常上抛(不留半截文件)"""
    target = tmp_path / "state.json"

    def bad_write(f):
        raise ValueError("序列化炸了")

    with pytest.raises(ValueError):
        utils.atomic_write(str(target), bad_write)
    assert list(tmp_path.iterdir()) == [], "临时文件已清理"
    assert not target.exists()


def test_long_path_prefix_relative_path(tmp_path, monkeypatch):
    """相对路径 -> 先转绝对再加前缀(与已绝对路径不同径)

    相对分支只在 `is_windows()` 为真时可达 ⇒ 必须 monkeypatch 平台 ——
    否则在 Linux CI 上函数原样返回入参, 前缀断言必红(见 testing/file-conventions.md)。
    """
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.chdir(tmp_path)
    out = utils.add_long_path_prefix_for_win("sub/dir/file.bin")
    assert out.startswith("\\\\?\\") and "sub/dir" in out.replace("\\", "/")


def test_match_tracker_confs_skips_hostless_urls():
    """无 hostname 的 URL(畸形)跳过, 不影响其余匹配"""
    conf = SimpleNamespace(domains=["pt.example.com"])
    got = utils.match_tracker_confs({"a": conf}, ["not a url", "https://pt.example.com/myhr.php"])
    assert got == [conf]
    assert utils.match_tracker_confs({"a": conf}, ["not a url"]) == []


def test_auto_managed_tag_rules_skips_empty_templates():
    """集数模板为空串 -> 跳过不产正则(仅站点 tags 进精确集)"""
    config = SimpleNamespace(
        trackers={"t": SimpleNamespace(tags=["SITE"], hr=None)},
        add_episode_tags=SimpleNamespace(enabled=True, add_tag_single="", add_tag_multi=""),
    )
    exact, patterns = utils.auto_managed_tag_rules(config)
    assert exact == {"SITE"} and patterns == ()


def test_timer_units_us_and_ms():
    """timer 装饰器: 'us'/'ms'/'s' 三种单位都落日志(自定义 log_func)"""
    lines = []
    for unit in ("us", "ms", "s"):
        fn = utils.timer(unit=unit, log_func=lines.append)(lambda: 1)
        assert fn() == 1
    assert len(lines) == 3
    assert lines[0].endswith("us") and lines[1].endswith("ms") and lines[2].endswith(" s")
    assert lines[0].startswith("<lambda> 耗时"), lines


# ---------------- Windows Shell / 窗口置前(全部经替身, 不碰真窗口) ----------------


def test_win_shell_open_not_windows(monkeypatch):
    """非 Windows 恒 False(不进入 ctypes 路线)"""
    monkeypatch.setattr(utils, "is_windows", lambda: False)
    assert utils._win_shell_open("D:/x") is False


def _fake_shell(parse_result=0, open_result=0, parse_sets_pidl=False, coinit_raises=False):
    """假 shell32/ole32 替身(记录调用, 不碰真 Shell)"""
    import ctypes
    calls = {"parse": [], "open": [], "ilfree": 0, "couninit": 0}
    pidl_holder = {"value": None}

    def parse(target, _none, byref_pidl, _flags, _byref_sfgao):
        calls["parse"].append(target)
        if parse_sets_pidl:
            byref_pidl._obj.value = 0x1234
        return parse_result

    def open_items(pidl, _n, _ref, _flags):
        calls["open"].append(pidl)
        return open_result

    def coinit(_reserved, _mode):
        if coinit_raises:
            raise AttributeError("no COM")
        return 1  # S_FALSE

    shell32 = SimpleNamespace(
        SHParseDisplayName=parse,
        SHOpenFolderAndSelectItems=open_items,
        ILFree=lambda pidl: calls.__setitem__("ilfree", calls["ilfree"] + 1),
    )
    ole32 = SimpleNamespace(
        CoInitializeEx=coinit,
        CoUninitialize=lambda: calls.__setitem__("couninit", calls["couninit"] + 1),
    )
    return shell32, ole32, calls


def _unwrapped_shell_open(monkeypatch):
    """取回被 sidefx 记账包装前的原 _win_shell_open(仅本测试内直调)

    本测试把 shell32/ole32 全部换成假替身, 不可能产生真实打开 —— 而 sidefx 对该入口的
    记账包装包在函数外层, 不区分真假, 直调会按 LAUNCH 记成越界假阳性(sidefx.py 自述
    「没有真实副作用就不该记」)。借记账器自己的 _saved 快照把原函数临时装回去, 测后
    monkeypatch 自动恢复包装, 守阵对其余用例的拦截力不变。
    """
    import sidefx

    for container, name, original in list(getattr(sidefx.SESSION, "_saved", ())):
        if container is utils and name == "_win_shell_open":
            monkeypatch.setattr(utils, "_win_shell_open", original)
            return
    raise AssertionError("sidefx 未包装 _win_shell_open: 前置条件变化, 请复核本辅助")


def _shim_posix_ctypes(monkeypatch):
    """POSIX 上补齐 ctypes 的 Windows 专属门面(`windll` / `WINFUNCTYPE`), 让 Windows 分支用例
    在 Linux CI 上也能跑 —— 用例注入的都是假替身, 不碰真窗口。

    Windows 宿主不装: 走真门面, 行为与改动前逐字一致。缺这两样是 POSIX 的既有事实
    (`ctypes.windll` / `ctypes.WINFUNCTYPE` 在 Linux 上不存在), 不是被测代码的缺陷 ——
    生产入口(`_win_user32` / `_win_shell_open` 等)靠 `is_windows()` 早退, 用例则靠本 shim
    把门面补上。`ctypes.wintypes` 两平台都有, 无需补。
    """
    import ctypes

    if not hasattr(ctypes, "windll"):
        monkeypatch.setattr(ctypes, "windll", SimpleNamespace(), raising=False)
    if not hasattr(ctypes, "WINFUNCTYPE"):
        # WINFUNCTYPE(BOOL, HWND, LPARAM) 是回调工厂; 假 user32 下真实调用约定无意义,
        # 直接返回原函数即可(`_win_explorer_hwnds` 只把它当"把 _on_window 包成 proc"用)
        monkeypatch.setattr(ctypes, "WINFUNCTYPE", lambda *a: (lambda f: f), raising=False)


def test_win_shell_open_pidl_routes(monkeypatch):
    """_win_shell_open PIDL 路线三分支: 解析失败 / 打开失败 / 成功; 前缀剥离与 COM 配对

    Windows 分支用例 ⇒ 固定平台 + 补 ctypes 门面(POSIX 无 `windll`), 假 shell32/ole32
    全程替身, 不碰真 Shell。
    """
    import ctypes

    import auto_qb.infra.utils as u

    _shim_posix_ctypes(monkeypatch)
    monkeypatch.setattr(sys, "platform", "win32")
    _unwrapped_shell_open(monkeypatch)
    # 成功: parse 0 + open 0 -> True; pidl 置位 -> ILFree; CoUninitialize 配对
    shell32, ole32, calls = _fake_shell(parse_sets_pidl=True)
    monkeypatch.setattr(ctypes.windll, "shell32", shell32, raising=False)
    monkeypatch.setattr(ctypes.windll, "ole32", ole32, raising=False)
    assert u._win_shell_open("\\\\?\\D:/长路径目录") is True
    assert calls["ilfree"] == 1 and calls["couninit"] == 1
    assert calls["parse"] and not calls["parse"][0].startswith("\\\\?\\"), "前缀与 PIDL 路线互斥, 已剥离"
    # 解析失败 -> False(退回字符串路线)
    shell32, ole32, calls = _fake_shell(parse_result=1)
    monkeypatch.setattr(ctypes.windll, "shell32", shell32, raising=False)
    monkeypatch.setattr(ctypes.windll, "ole32", ole32, raising=False)
    assert u._win_shell_open("D:/nope") is False
    assert calls["ilfree"] == 0, "pidl 未置位不释放"
    # 打开失败 -> False
    shell32, ole32, calls = _fake_shell(parse_result=0, open_result=5)
    monkeypatch.setattr(ctypes.windll, "shell32", shell32, raising=False)
    monkeypatch.setattr(ctypes.windll, "ole32", ole32, raising=False)
    assert u._win_shell_open("D:/nope") is False
    # CoInitializeEx 异常 -> False(防御, 绝不抛)
    shell32, ole32, calls = _fake_shell(coinit_raises=True)
    monkeypatch.setattr(ctypes.windll, "shell32", shell32, raising=False)
    monkeypatch.setattr(ctypes.windll, "ole32", ole32, raising=False)
    assert u._win_shell_open("D:/nope") is False


def test_win_user32_and_kernel32_bind_signatures(monkeypatch):
    """user32/kernel32 惰性句柄: 首次取用绑死 x64 签名(测试重置缓存后真绑定一次, 不调任何 API)

    Windows 分支用例 ⇒ 固定平台 + 假 `ctypes.windll`(句柄对象为空替身, 属性取不到时
    `_win_bind` 自行吞掉), 于是本用例在两平台都跑 —— 不靠"恰好抛 AttributeError"。
    """
    import ctypes

    import auto_qb.infra.utils as u

    _shim_posix_ctypes(monkeypatch)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(
        ctypes, "windll", SimpleNamespace(user32=SimpleNamespace(), kernel32=SimpleNamespace()), raising=False
    )
    monkeypatch.setattr(u, "_bound_user32", None)
    monkeypatch.setattr(u, "_bound_kernel32", None)
    user32 = u._win_user32()
    assert user32 is not None and u._win_user32() is user32, "缓存复用同一句柄"
    kernel32 = u._win_kernel32()
    assert kernel32 is not None and u._win_kernel32() is kernel32


class _P1FakeUser32:
    """可编程 user32 替身: 按脚本回答各 API(不碰真窗口)"""
    def __init__(self, *, is_window=True, iconic=False, visible=True, fg=None, thread_id=7, fg_thread=99):
        self.scripts = []
        self.calls = []
        self._is_window = is_window
        self._iconic = iconic
        self._visible = visible
        self._fg = fg
        self._thread_id = thread_id
        self._fg_thread = fg_thread

    def IsWindow(self, hwnd):
        return self._is_window

    def IsIconic(self, hwnd):
        return self._iconic

    def IsWindowVisible(self, hwnd):
        return self._visible

    def GetForegroundWindow(self):
        self._fg_seq = getattr(self, "_fg_seq", 0) + 1
        return self._fg(self._fg_seq) if callable(self._fg) else self._fg

    def SetForegroundWindow(self, hwnd):
        self.calls.append("SetForegroundWindow")
        return True

    def BringWindowToTop(self, hwnd):
        self.calls.append("BringWindowToTop")
        return True

    def SwitchToThisWindow(self, hwnd, toggle):
        self.calls.append("SwitchToThisWindow")

    def ShowWindow(self, hwnd, cmd):
        self.calls.append(f"ShowWindow:{cmd}")
        return True

    def SetWindowPos(self, hwnd, after, x, y, cx, cy, flags):
        self.calls.append(f"SetWindowPos:{after}")
        return True

    def GetWindowThreadProcessId(self, hwnd, out):
        return self._fg_thread

    def AttachThreadInput(self, a, b, attach):
        self.calls.append("AttachThreadInput" if attach else "DetachThreadInput")
        return True

    def GetClassNameW(self, hwnd, buf, n):
        buf.value = "CabinetWClass"
        return len(buf.value)

    def GetWindowTextW(self, hwnd, buf, n):
        buf.value = "目标 - 文件资源管理器"
        return len(buf.value)

    def EnumWindows(self, proc, lparam):
        proc(101, 0)
        proc(202, 0)
        return True


class _P1FakeKernel32:
    def GetCurrentThreadId(self):
        return 7


def test_win_explorer_hwnds_and_topmost_and_switch(monkeypatch):
    """Explorer 枚举按类名过滤 / TOPMOST 开关式提升 / SwitchToThisWindow 兜底 + 各失败静默

    `_win_explorer_hwnds` 内部要 `ctypes.WINFUNCTYPE`(POSIX 无) ⇒ 补门面; user32 仍是假替身。
    """
    _shim_posix_ctypes(monkeypatch)
    fake = _P1FakeUser32()
    monkeypatch.setattr(utils, "_win_user32", lambda: fake)
    monkeypatch.setattr(utils, "_win_kernel32", lambda: _P1FakeKernel32())
    hwnds = utils._win_explorer_hwnds()
    assert hwnds == {101, 202}, "类名 CabinetWClass 的窗口都进集合"
    utils._win_topmost_once(101)
    assert "SetWindowPos:-1" in fake.calls and "SetWindowPos:-2" in fake.calls, "TOPMOST 挂一下立刻摘"
    assert utils._win_switch_to_this_window(101) is True
    # 失败静默: user32 缺席 / API 缺失
    monkeypatch.setattr(utils, "_win_user32", lambda: None)
    assert utils._win_explorer_hwnds() == set()
    assert utils._win_switch_to_this_window(1) is False

    class _Broken(_P1FakeUser32):
        def SetWindowPos(self, *a):
            raise OSError("无窗口")

    monkeypatch.setattr(utils, "_win_user32", lambda: _Broken())
    utils._win_topmost_once(1)  # 异常吞掉不外抛
    monkeypatch.setattr(utils, "_win_user32", lambda: None)
    utils._win_topmost_once(1)  # user32 缺席早退
    assert utils._win_window_text(1) == "", "user32 缺席标题为空"
    monkeypatch.setattr(utils, "_win_user32", lambda: _P1FakeUser32())
    assert utils._win_window_text(1) == "目标 - 文件资源管理器"


def test_win_force_foreground_matrix(monkeypatch):
    """三层升级矩阵: 不可还原 / 最小化先还原 / 隐藏先显示 / 焦点成功 / 借线程失败硬切 / 异常 False"""
    monkeypatch.setattr(utils, "_win_kernel32", lambda: _P1FakeKernel32())
    # 1) 焦点直接成功
    fake = _P1FakeUser32(fg=lambda seq: 101 if seq >= 2 else 202)
    monkeypatch.setattr(utils, "_win_user32", lambda: fake)
    assert utils._win_force_foreground(101) is True
    assert "AttachThreadInput" in fake.calls and "DetachThreadInput" in fake.calls, "借前台线程权限并归还"
    # 2) 最小化: 先 SW_RESTORE(9)
    fake = _P1FakeUser32(iconic=True, fg=101)
    monkeypatch.setattr(utils, "_win_user32", lambda: fake)
    assert utils._win_force_foreground(101) is True
    assert "ShowWindow:9" in fake.calls
    # 3) 隐藏: 先 SW_SHOW(5)
    fake = _P1FakeUser32(visible=False, fg=101)
    monkeypatch.setattr(utils, "_win_user32", lambda: fake)
    assert utils._win_force_foreground(101) is True
    assert "ShowWindow:5" in fake.calls
    # 4) 焦点拿不到: 硬切 + BringWindowToTop, 仍失败如实 False
    fake = _P1FakeUser32(fg=lambda seq: 202)  # 前台永远是别人
    monkeypatch.setattr(utils, "_win_user32", lambda: fake)
    assert utils._win_force_foreground(101) is False
    assert "SwitchToThisWindow" in fake.calls and "BringWindowToTop" in fake.calls
    # 5) 窗口已不存在 -> False
    monkeypatch.setattr(utils, "_win_user32", lambda: _P1FakeUser32(is_window=False))
    assert utils._win_force_foreground(101) is False
    # 6) user32/kernel32 缺席 -> False
    monkeypatch.setattr(utils, "_win_user32", lambda: None)
    assert utils._win_force_foreground(101) is False


def test_win_reuse_and_wait_explorer(monkeypatch):
    """复用窗口按标题匹配(含本地化后缀); 差集新窗口优先; 超时 None; 置前重试封顶

    `_win_reuse_title_candidates` 用 `os.path` 拆**Windows 形态**的 target(调用点只在 Windows)
    ⇒ 按 pitfalls/testing/patching.md ④ 固定语义: 只把 utils 模块内的 `os` 换成 `ntpath`
    (纯字符串模块, 两平台同语义), 不动全局 os.path。否则 POSIX 上反斜杠不是分隔符, 盘根断言必红。
    """
    monkeypatch.setattr(utils, "os", SimpleNamespace(path=ntpath))
    monkeypatch.setattr(utils, "_win_user32", lambda: _P1FakeUser32())
    monkeypatch.setattr(utils, "_win_kernel32", lambda: _P1FakeKernel32())
    # 标题候选: 目标名 + 父目录名
    names = utils._win_reuse_title_candidates("R:/Media/Show")
    assert names == {"Show", "Media"}
    assert utils._win_reuse_title_candidates("R:\\") == set(), "盘根无候选, 跳过复用兜底"
    # 复用匹配: 只在打开前就存在的窗口里找, 标题带本地化后缀也算
    hit = utils._win_match_reused_explorer({101, 202}, before={202}, names={"目标"})
    assert hit == 202
    assert utils._win_match_reused_explorer({101, 202}, before={202}, names={"无关"}) is None
    # 等待: 差集新窗口立刻返回
    monkeypatch.setattr(utils, "_win_explorer_hwnds", lambda: {999})
    assert utils._win_wait_explorer({202}, "R:/Media/Show") == 999
    # 等待: 无新窗口但旧窗口标题命中 -> 复用
    monkeypatch.setattr(utils, "_win_explorer_hwnds", lambda: {202})
    assert utils._win_wait_explorer({202}, "R:/Media/目标") == 202
    # 等待: 超时(上限拨负) -> None; 名字为空跳过复用匹配
    monkeypatch.setattr(utils, "_EXPLORER_FG_TIMEOUT", -1.0)
    monkeypatch.setattr(utils, "_win_explorer_hwnds", lambda: set())
    assert utils._win_wait_explorer(set(), "R:/Media/Show") is None
    assert utils._win_wait_explorer(set(), "") is None
    # 置前编排: 找不到窗口 -> False(静默); 重试耗尽 -> False(封顶, 不执念)
    assert utils._win_foreground_new_explorer(set(), "R:/x") is False
    monkeypatch.setattr(utils, "_EXPLORER_FG_RETRY", 1)
    monkeypatch.setattr(utils, "_EXPLORER_FG_RETRY_GAP", 0.0)
    monkeypatch.setattr(utils, "_win_wait_explorer", lambda before, target: 101)
    monkeypatch.setattr(utils, "_win_force_foreground", lambda hwnd: False)
    assert utils._win_foreground_new_explorer(set(), "R:/x") is False
    monkeypatch.setattr(utils, "_win_force_foreground", lambda hwnd: True)
    assert utils._win_foreground_new_explorer(set(), "R:/x") is True
