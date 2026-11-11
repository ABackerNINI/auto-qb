"""test_utils_parse 测试计划: utils 工具函数

## 测试计划(每个测试函数一条)
- test_parse_time: 时间字符串解析
- test_parse_fsize: 文件大小解析
- test_parse_speed: 速度解析
- test_parse_hr_condition: HR 条件解析
- test_parse_bool: 布尔解析
- test_convert_bool_in_dict: 字典内布尔转换
- test_convert_bool_in_dict_list_branch_keeps_decimal_strings: 守阵(26-10-06-0028 H-03)——列表元素与字典分支同口径, 纯数字串保持原样不 True 化
- test_compare: 比较操作符
- test_extract_tracker_hostnames: 提取 tracker hostname
- test_match_tracker_confs: tracker 配置匹配
- test_match_tag_patterns: 标签模式匹配
- test_auto_managed_tag_rules: 程序自动维护标签识别规则(站点/HR 精确集 + 集数模板形状; 事件标记/用户标签不在口径)
- test_match_path_patterns: 路径模式匹配
- test_match_pattern_parse: MatchPattern.parse 统一语法解析(regex: 前缀/:ignore_case 后缀/body/suffix)
- test_match_value_normalize: match_value 核心(normalize 规范化语义, 空模式跳过)
- test_check_filelist_all_ok: 文件列表全部一致(OpsModule.check_filelist)
- test_check_filelist_missing: 文件缺失
- test_check_filelist_size_mismatch: 文件大小不一致
- test_check_filelist_api_error: 文件列表 API 错误
- test_timer: 计时器
- test_parse_time_empty: 空串 -> 0
- test_parse_time_invalid: 非法时间格式 -> ValueError
- test_parse_fsize_invalid_format: 非法大小格式 -> ValueError
- test_parse_fsize_invalid_unit: 非 iB 单位 -> ValueError
- test_parse_speed_empty: 空串 -> 0
- test_parse_speed_invalid: 非法速度格式 -> ValueError
- test_parse_quantity_ladder_valid_and_empty: 三解析器表驱动矩阵·合法值与空串语义(time/speed 空串 -> 0, fsize 无回退)
- test_parse_quantity_ladder_invalid_valueerror: 守阵(issue 26-10-29-1252)——非法输入矩阵断言异常类恰为 ValueError(无前缀 iB/十进制前缀/小数多段/纯非法/空串); KeyError 不是 ValueError 子类, 单位表白名单兜底缺失时必红
- test_parse_quantity_ladder_unit_whitelist_message: 单位白名单兜底报错文案(speed 新增 iB 提示, fsize 旧文案保持不变)
- test_parse_compare_invalid: 无效比较表达式 -> ValueError
- test_check_filelist_oserror: 读取文件异常 -> 无法读取文件(OpsModule.check_filelist)
- test_extract_tracker_hostnames_invalid_url: url 解析异常 -> 跳过
- test_match_tracker_confs_invalid_url: url 解析异常 -> 不匹配
- test_match_tag_patterns_empty_pattern: 空模式跳过
- test_timer_us: us 单位计时
- test_is_manual_speed_limit: 奇数KiB手动限速保护(0/偶数不命中)
- test_replace_vars: ${required_seeding_time} 占位替换(有hr/无hr/tracker_conf=None 留原文)
- test_parse_bool_invalid: 非法布尔值 -> ValueError
- test_fmt_speed_size_ladder_equivalence: fmt_speed/fmt_size 同阶梯单点(整数输入 fmt_speed(v)==fmt_size(v)+"/s" 跨 rung + 逐 rung 钉输出)
- test_fmt_ladder_single_point: 守阵(issue infra-fmt-ladder-dup)——utils.py 里 `if value >= div:` 只出现一次(阶梯判单点)

### P1 覆盖率提升轮: infra 长尾
- test_match_tracker_confs_skips_hostless_urls: 无 hostname 的 URL 跳过
- test_auto_managed_tag_rules_skips_empty_templates: 集数模板空串跳过不产正则
- test_timer_units_us_and_ms: timer 三种单位落日志
- test_sanitize_tracker_url: tracker URL 脱敏只留主地址(query/path/fragment 整段丢, 任意凭据参数名都覆盖; udp 端口/userinfo 处理)
- test_sanitize_tracker_url_unparseable: 空/非字符串/解析不出 host -> 占位串且不抛异常(日志路径不得打断业务)
- test_mask_tracker_url_virtual_passthrough: mask R1 虚拟条目("**"/"[DHT]"/"[PeX]"/"[LSD]" 含裸形态)原样透传
- test_mask_tracker_url_unparseable: mask R2 空/非字符串/解析不出 host -> 占位串且不抛异常
- test_mask_tracker_url_structure: mask R3/R4 scheme 小写保留/userinfo 去除/host 小写/端口保留/缺 scheme 兜底
- test_mask_tracker_url_path_and_query: mask R5/R6 path 末段高熵判定(边界 15/16 位)/端点名保留/fragment 丢/query 全值 hash 含未知参数名/裸名原样/段序不变/值不百分号解码
- test_mask_tracker_url_deterministic_and_unique: mask R7/R8 确定性(两次逐字节一致)与唯一性三例
- test_mask_tracker_entry: mask R9 只改 url 其余字段保全/原条目不被就地改/缺 url 与虚拟条目原样返回
- test_mask_magnet_tracker_urls: magnet tr= 值过 tracker 同款 mask(issue 26-11-08-0043)/多 tr= 逐个掩/非 tr= 参数原样/非 magnet 与空原样/确定性
- test_display_host: 展示地址(可达等价回环 127.0.0.1/::1 含 v4-mapped/全写法折 localhost, 其余回环 127.0.0.2+ 与对外地址原样, 异常入参不炸)
- test_time_in_range_minute_granularity: 时段判定按**分钟**粒度(端点整分钟含在内: 23:59:30 在 "00:00-23:59" 内 / 跨午夜两端 / 起点前 1 分仍在区间外) —— issue 26-10-19-0013 的守阵
- test_is_loopback_host_empty_and_unparsable: 回环判据两条保守出口(空/None、主机名 -> False; localhost 大小写与两族字面量 -> True)
- test_is_loopback_host_ipv4_mapped_version_stable: IPv4-mapped 解包同判(钉平 CPython 3.12/3.13 is_loopback 行为差异)
- test_fmt_size_invalid
- test_parse_hm_invalid_format
"""

import hashlib

import ntpath

import os

import pytest

import sys

import tempfile

import threading

from pathlib import Path

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


def test_convert_bool_in_dict_list_branch_keeps_decimal_strings():
    """守阵(26-10-06-0028 H-03): 列表元素与字典分支同口径 —— 纯数字串保持原样不 True 化

    列表分支原无条件递归, 列表里的 "1"/"on"/"true" 被静默改写为 True/False;
    导出模板(tags/domains 等列表值)回填导入时类型与原值不符。
    """
    d = {"tags": ["1", "on", "true", "notbool", "2026"], "nested": {"list": ["0", "x"]}}
    result = utils.convert_bool_in_dict(d)
    assert result["tags"] == ["1", True, True, "notbool", "2026"], "数字串保持原样, 布尔形串照常转换"
    assert result["nested"]["list"] == ["0", "x"], "嵌套容器内同口径(数字串含 \"0\" 保持原样)"


def test_compare():
    op, val = utils.parse_compare(">=100MiB", utils.parse_fsize)
    assert op == ">=" and val == 100 * 1024**2
    assert utils.compare(">", 5, 3)
    assert not utils.compare("<", 5, 3)
    assert utils.compare(">=", 5, 5)
    assert utils.compare("<=", 3, 5)
    assert utils.compare("==", 5, 5)
    assert utils.compare("!=", 5, 3)


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


@pytest.mark.parametrize(
    "fn,value,expected", [
        (utils.parse_time, "", 0),
        (utils.parse_speed, "", 0),
        (utils.parse_time, "90M", 5400.0),
        (utils.parse_time, "0.5H", 1800.0),
        (utils.parse_fsize, "512B", 512),
        (utils.parse_fsize, "1.5GiB", int(1.5 * 1024**3)),
        (utils.parse_speed, "500B/s", 500),
        (utils.parse_speed, "0.5MiB/s", int(0.5 * 1024**2)),
    ]
)
def test_parse_quantity_ladder_valid_and_empty(fn, value, expected):
    """三解析器合法值与空串语义(time/speed 空串 -> 0; fsize 无空串回退)"""
    assert fn(value) == expected


@pytest.mark.parametrize(
    "fn,value",
    [
        (utils.parse_time, "1iB"),  # 无前缀 iB: time 正则不含 i -> 走不命中分支
        (utils.parse_time, "1.5.5M"),  # 小数多段: 形状命中但 float 拒绝
        (utils.parse_time, "abc"),
        (utils.parse_fsize, ""),  # fsize 空串无回退 -> 不命中分支
        (utils.parse_fsize, "1iB"),  # 无前缀 iB: 正则命中、单位表没有 -> 白名单兜底
        (utils.parse_fsize, "10KB"),  # 十进制前缀同理(旧实现已有兜底, 保持)
        (utils.parse_fsize, "1.5.5MiB"),
        (utils.parse_fsize, "abc"),
        (utils.parse_speed, "1iB/s"),  # 无前缀 iB/s: 修复点 —— 旧实现 KeyError 'IB/S'
        (utils.parse_speed, "10KB/s"),  # 十进制前缀: 同一缺口(旧实现 KeyError 'KB/S')
        (utils.parse_speed, "1.5.5MiB/s"),
        (utils.parse_speed, "abc"),
    ]
)
def test_parse_quantity_ladder_invalid_valueerror(fn, value):
    """非法输入矩阵: 异常类恰为 ValueError(KeyError 不是 ValueError 子类, 白名单兜底缺失时必红)"""
    with pytest.raises(ValueError) as ei:
        fn(value)
    assert type(ei.value) is ValueError


@pytest.mark.parametrize(
    "fn,value,frag", [
        (utils.parse_fsize, "10KB", "无效大小格式(需使用iB单位, 如 10MiB): 10KB"),
        (utils.parse_speed, "1iB/s", "无效速度格式(需使用iB单位, 如 10MiB/s): 1iB/s"),
        (utils.parse_speed, "10KB/s", "无效速度格式(需使用iB单位, 如 10MiB/s): 10KB/s"),
    ]
)
def test_parse_quantity_ladder_unit_whitelist_message(fn, value, frag):
    """单位白名单兜底的报错文案(带 iB 提示); fsize 两条旧文案保持不变"""
    with pytest.raises(ValueError) as ei:
        fn(value)
    assert frag in str(ei.value)


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


def test_fmt_speed_size_ladder_equivalence():
    """fmt_speed/fmt_size 同阶梯单点: 整数输入 fmt_speed(v) == fmt_size(v) + "/s" 跨 rung; 逐 rung 钉输出防两函数同侧漂移"""
    for v in (0, 512, 1023, 1024, 1024**2, 1024**3, 1024**4, 1024**5, 1024**6):
        assert utils.fmt_speed(v) == utils.fmt_size(v) + "/s"
    assert utils.fmt_size(1024**3) == "1.00 GiB"
    assert utils.fmt_speed(1024**3) == "1.00 GiB/s"
    assert utils.fmt_speed(1024**5) == "1.00 PiB/s"
    assert utils.fmt_size(1023) == "1023 B"


def test_fmt_ladder_single_point():
    """守阵(issue infra-fmt-ladder-dup): 阶梯循环单点 _fmt_ladder —— utils_paths.py 里 `if value >= div:` 只出现一次

    (R5 拆分: 该函数随格式化域迁至 utils_paths.py, 仍由 utils 重导出; 判据语义不变。)
    fmt_speed / fmt_size 降为委托; 红验: 任一函数改回自抄阶梯即计数 >1 红。
    """
    from pathlib import Path

    src = (Path(__file__).resolve().parents[1] / "src" / "auto_qb" / "infra" /
           "utils_paths.py").read_text(encoding="utf-8")
    assert src.count("if value >= div:") == 1, "阶梯判单点(出现 >1 次 = 又有人自抄)"


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


def _mask_h16(value: str) -> str:
    """mask R7 的参考实现: sha256 前 16 位 hex —— 测试侧独立重算, 不 import 被测 helper(防同源抄错)"""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def test_mask_tracker_url_virtual_passthrough():
    """mask_tracker_url R1: 虚拟条目("**"/"[DHT]"/"[PeX]"/"[LSD]" 前缀, 含裸形态)原样透传

    必须在函数内挡掉, 不依赖调用方过滤 —— sanitize 会把裸 "[DHT]" 小写化破坏前缀识别,
    mask 若走同一路径就会把虚拟条目误判成"解析不出 host"(计划 26-10-07-0055 R1)。
    """
    from auto_qb.infra.utils import VIRTUAL_TRACKER_PREFIXES, mask_tracker_url

    # 全部前缀 + 裸形态(无 "**" 包裹)都逐字节原样
    for raw in ("** [DHT] **", "[DHT]", "** [PeX] **", "[PeX]", "** [LSD] **", "[LSD]", "**"):
        assert mask_tracker_url(raw) == raw, f"{raw!r} 应原样透传"
    # 前缀集合是单点常量(webui/views.py 引用同一份), 防双源漂移
    assert VIRTUAL_TRACKER_PREFIXES == ("**", "[DHT]", "[PeX]", "[LSD]")


def test_mask_tracker_url_unparseable():
    """mask_tracker_url R2: 非字符串/空/解析不出 host -> 占位串, 绝不抛异常(与 sanitize 同口径)"""
    from auto_qb.infra.utils import SANITIZE_FALLBACK, mask_tracker_url

    for bad in ("", "   ", None, 123, "/announce?passkey=abc", object()):
        assert mask_tracker_url(bad) == SANITIZE_FALLBACK, f"{bad!r} 应降级为占位串"

    # urlparse 自身抛异常也不能冒泡出去
    with mock.patch("auto_qb.infra.utils.urlparse", side_effect=ValueError("boom")):
        assert mask_tracker_url("https://pt.example.com/announce?passkey=abc") == SANITIZE_FALLBACK


def test_mask_tracker_url_structure():
    """mask_tracker_url R3/R4: scheme 保留并小写 / userinfo 去除 / host 小写 / 端口保留 / 缺 scheme 兜底"""
    from auto_qb.infra.utils import mask_tracker_url

    # userinfo 去(@ 之后), host 小写, 端口保留, scheme 小写
    assert mask_tracker_url("HTTP://User:Sec@PT.Example.COM:8443/announce?passkey=abc") == \
        "http://pt.example.com:8443/announce?passkey=" + _mask_h16("abc")
    # 缺 scheme: host 从 path 首段兜底(镜像 sanitize), 且首段不再重复进 path
    assert mask_tracker_url("pt.example.com/announce?passkey=abc") == \
        "pt.example.com/announce?passkey=" + _mask_h16("abc")
    # 无 path 无 query 的裸主地址只做小写归一
    assert mask_tracker_url("udp://Tracker.OpenTrackr.ORG:1337") == "udp://tracker.opentrackr.org:1337"


def test_mask_tracker_url_path_and_query():
    """mask_tracker_url R5/R6: path 末段高熵才换 hash / fragment 丢 / query 全值 hash 不按名挑"""
    from auto_qb.infra.utils import mask_tracker_url

    # 端点名(announce / announce.php)不命中高熵, 保留诊断价值; 无凭据的 udp 条目整条原样
    assert mask_tracker_url(
        "udp://tracker.opentrackr.org:1337/announce"
    ) == "udp://tracker.opentrackr.org:1337/announce"
    assert mask_tracker_url("https://pt.example.com/announce.php?passkey=abc") == \
        "https://pt.example.com/announce.php?passkey=" + _mask_h16("abc")
    # path 末段 24 位高熵整段替换, fragment 丢弃
    assert mask_tracker_url("https://pt.example.com/announce/1a2b3c4d5e6f7a8b9c0d1e2f#frag") == \
        "https://pt.example.com/announce/" + _mask_h16("1a2b3c4d5e6f7a8b9c0d1e2f")
    # 高熵边界: 15 位保留 / 16 位替换(首字符须为字母数字)
    assert mask_tracker_url("https://pt.example.com/abcdefghijklmno") == "https://pt.example.com/abcdefghijklmno"
    assert mask_tracker_url("https://pt.example.com/abcdefghijklmnop") == \
        "https://pt.example.com/" + _mask_h16("abcdefghijklmnop")
    # query: 有 = 的段全 hash(含未知参数名, 铁律不按名挑), 裸名参数原样, 段序不变
    assert mask_tracker_url("https://pt.example.com/announce?passkey=abc&flag&zzz_unknown=sec&uid=7") == (
        "https://pt.example.com/announce?passkey=" + _mask_h16("abc") + "&flag&zzz_unknown=" + _mask_h16("sec") +
        "&uid=" + _mask_h16("7")
    )
    # 值取原文子串, 不做百分号解码(%20 原样作为 hash 输入)
    assert mask_tracker_url("https://pt.example.com/announce?k=a%20b") == \
        "https://pt.example.com/announce?k=" + _mask_h16("a%20b")
    # 空值段(=后无值)同样走 hash 改写, 不抛异常
    assert mask_tracker_url("https://pt.example.com/announce?k=") == \
        "https://pt.example.com/announce?k=" + _mask_h16("")


def test_mask_tracker_url_deterministic_and_unique():
    """mask_tracker_url R7/R8: 确定性(不加盐, 两次调用逐字节一致)与唯一性(hash 保值差异)

    R8 是"mask 可当内容标识用于删除定位"的前提: 三例互异 + 完全相同 url 相同 mask。
    """
    from auto_qb.infra.utils import mask_tracker_url

    # 确定性: 同一输入两次调用逐字节一致
    u1 = "https://pt.example.com/announce?passkey=abc123def456"
    assert mask_tracker_url(u1) == mask_tracker_url(u1)
    # 唯一性一: 同 host 不同 path 互异
    a = mask_tracker_url("https://pt.example.com/aaaaaaaaaaaaaaaa?k=v")
    b = mask_tracker_url("https://pt.example.com/bbbbbbbbbbbbbbbb?k=v")
    assert a != b
    # 唯一性二: 同 path 不同凭据值互异
    c = mask_tracker_url("https://pt.example.com/announce?passkey=one")
    d = mask_tracker_url("https://pt.example.com/announce?passkey=two")
    assert c != d
    # 唯一性三: 完全相同 url -> 相同 mask
    assert c == mask_tracker_url("https://pt.example.com/announce?passkey=one")


def test_mask_tracker_entry():
    """mask_tracker_entry R9: 只改 url 字段, 其余字段保全; 缺 url / 虚拟条目原样返回"""
    from auto_qb.infra.utils import mask_tracker_entry

    entry = {"url": "https://pt.example.com/announce?passkey=abc", "status": 2, "msg": "working", "num_peers": 5}
    masked = mask_tracker_entry(entry)
    assert masked["url"] == "https://pt.example.com/announce?passkey=" + _mask_h16("abc")
    assert masked["status"] == 2
    assert masked["msg"] == "working"
    assert masked["num_peers"] == 5
    # 原条目不被就地修改(返回新 dict)
    assert entry["url"] == "https://pt.example.com/announce?passkey=abc"
    # 缺 url: 原样返回(同一对象, 不做无谓拷贝)
    no_url = {"status": 4, "msg": "err"}
    assert mask_tracker_entry(no_url) is no_url
    # 命中 R1(虚拟条目): 原样返回
    virt = {"url": "** [DHT] **", "status": 0}
    assert mask_tracker_entry(virt) is virt


def test_mask_magnet_tracker_urls():
    """mask_magnet_tracker_urls(issue 26-11-08-0043): magnet tr= 值过 tracker 同款 mask, 其余参数原样

    - tr= percent-encoded announce URL(私站含 passkey): unquote 还原 -> mask -> 重新
      percent-encode 拼回, 掩码值里 passkey 不可见(host/参数名保留)
    - 多 tr= 逐个掩; 非 tr= 参数(xt/dn 等)逐字节原样
    - 非 magnet URI / 无 query / 空串原样返回; 确定性: 同原文两次掩出逐字节一致
    """
    from auto_qb.infra.utils import mask_magnet_tracker_urls
    from urllib.parse import quote, unquote

    tr = quote("https://pt.example.com/announce?passkey=abc", safe="")
    magnet = f"magnet:?xt=urn:btih:H1&dn=T1&tr={tr}"
    masked = mask_magnet_tracker_urls(magnet)
    # tr= 值已掩(passkey 不可见), 掩码值重新 percent-encode 保持 magnet 形态
    assert masked.startswith("magnet:?xt=urn:btih:H1&dn=T1&tr=")
    tr_value = unquote(masked.split("&tr=")[1])
    assert tr_value == "https://pt.example.com/announce?passkey=" + _mask_h16("abc")
    assert "abc" not in masked
    # 多 tr=: 逐个掩, 其余参数原样
    tr2 = quote("udp://tracker.opentrackr.org:1337", safe="")
    masked2 = mask_magnet_tracker_urls(f"magnet:?xt=urn:btih:H1&tr={tr}&tr={tr2}")
    assert masked2.count("&tr=") == 2, "两个 tr= 分隔符原样保留"
    assert unquote(masked2.split("&tr=")[2]) == "udp://tracker.opentrackr.org:1337"
    # 无凭据的裸 tr= 值掩后 host 保留(不降级为整串占位)
    masked3 = mask_magnet_tracker_urls("magnet:?xt=urn:btih:H1&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337")
    assert "tracker.opentrackr.org" in unquote(masked3.split("&tr=")[1])
    # 非 magnet URI / 无 query / 空串原样返回
    assert mask_magnet_tracker_urls("https://pt.example.com/announce?passkey=abc") == \
        "https://pt.example.com/announce?passkey=abc"
    assert mask_magnet_tracker_urls("magnet:?") == "magnet:?"
    assert mask_magnet_tracker_urls("") == ""
    # 确定性: 同原文两次掩出逐字节一致(apply_delta 掩后比较不产生假变化)
    assert mask_magnet_tracker_urls(magnet) == masked


def test_display_host():
    """display_host: 可达等价回环(127.0.0.1/::1 含等价写法)折成 localhost 展示, 其余原样

    折叠口径是「可达等价」而非「全量回环」: 唯一消费点是 lifecycle 的 WEB UI 可连接地址
    提示, 折成 localhost 后要仍连得上才有意义 —— 绑定 127.0.0.2 时 localhost(127.0.0.1/::1)
    拒连, 折叠是误导, 127.0.0.2 必须原样给出。
    """
    from auto_qb.infra.utils import display_host

    # 可达等价回环折成 localhost: 127.0.0.1/::1 本尊、IPv6 全写法(解析归一)、
    # IPv4-mapped(::ffff:127.0.0.1 实测解析后经 ipv4_mapped 解包出 127.0.0.1)、大小写与首尾空白
    for h in ("127.0.0.1", "::1", "::ffff:127.0.0.1", "0:0:0:0:0:0:0:1", " 127.0.0.1 ", "::FFFF:127.0.0.1"):
        assert display_host(h) == "localhost", f"{h!r} 应显示为 localhost"
    # 其余回环与对外地址原样返回(127.0.0.2 是合法回环绑定但 localhost 对它不可达;
    # 0.0.0.0 / 局域网 IP 也不折, 否则掩盖暴露面)
    for h in ("127.0.0.2", "0.0.0.0", "192.168.1.5", "192.168.1.10", "qb.example.com"):
        assert display_host(h) == h
    # 非字符串(配置缺失/取错类型)原样返回: 调用方都在日志路径上, 不该炸
    for bad in ("", None, 123):
        assert display_host(bad) == bad


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


def test_time_in_range_minute_granularity():
    """时段判定按分钟粒度: 端点所在的整分钟都含在内(issue 26-10-19-0013 的守阵)

    守阵价值: 曾经按秒直比, "00:00-23:59"(用户写「全天」)每天漏掉 23:59:01-23:59:59, 且与
    表达式侧 sys.time_of_day(hour*60+minute, 分钟口径)结论相反 —— 等价性用例每天最后一分钟必红。
    """
    from datetime import time as dtime

    # 端点分钟的后 59 秒必须在区间内(全时段配置 = 真的全天)
    assert utils.time_in_range(dtime(23, 59, 30), "00:00-23:59") is True
    assert utils.time_in_range(dtime(0, 0, 0), "00:00-23:59") is True
    # 起点分钟之前一律不收(截断后 22:59 < 23:00), 与表达式侧 sys.time_of_day 同口径
    assert utils.time_in_range(dtime(22, 59, 59), "23:00-08:00") is False
    assert utils.time_in_range(dtime(23, 0, 0), "23:00-08:00") is True
    # 跨午夜: 两端点分钟都算在内, 越过端点整分钟才出界
    assert utils.time_in_range(dtime(23, 59, 59), "23:00-08:00") is True
    assert utils.time_in_range(dtime(8, 0, 30), "23:00-08:00") is True
    assert utils.time_in_range(dtime(8, 1, 0), "23:00-08:00") is False
    # 非跨午夜: 两端点分钟内皆真, 越过即假
    assert utils.time_in_range(dtime(10, 0, 45), "10:00-12:00") is True
    assert utils.time_in_range(dtime(12, 0, 45), "10:00-12:00") is True
    assert utils.time_in_range(dtime(12, 1, 0), "10:00-12:00") is False
    assert utils.time_in_range(dtime(9, 59, 59), "10:00-12:00") is False


def test_is_loopback_host_empty_and_unparsable():
    """回环判据两条保守出口: 空/None -> False, 解析不出的字面量(主机名) -> False

    保守方向是「按非回环处理」: 配置校验(非回环 + pairing=off + 无 token)与配对门
    (pairing=auto 时非回环强制配对)都会因此往「要求配对」走 —— 宁可多要一道, 不放行。
    """
    assert utils.is_loopback_host("") is False
    assert utils.is_loopback_host(None) is False
    assert utils.is_loopback_host("nas.local") is False
    assert utils.is_loopback_host("127.0.0.1") is True
    assert utils.is_loopback_host("::1") is True
    assert utils.is_loopback_host("localhost") is True
    assert utils.is_loopback_host("  LOCALHOST  ") is True
    assert utils.is_loopback_host("192.168.1.5") is False


def test_is_loopback_host_ipv4_mapped_version_stable():
    """IPv4-mapped IPv6 解包同判 —— CPython 3.13 起 IPv6Address.is_loopback 委托 IPv4 侧,
    3.12 只认 ::1; 实现面显式解包钉平, 跨版本行为必须一致(2026-11-12 容器 3.12 全量实证)。
    """
    assert utils.is_loopback_host("::ffff:127.0.0.1") is True
    assert utils.is_loopback_host("::ffff:127.0.0.2") is True
    assert utils.is_loopback_host("::FFFF:127.0.0.1") is True
    assert utils.is_loopback_host("::ffff:192.168.1.5") is False
    assert utils.is_loopback_host("::ffff:8.8.8.8") is False
