"""test_hr_report 测试计划: --hr-once 只读走查(不进主循环、不写盘、不连 qB)

## 测试计划(每个测试函数一条)
- test_build_fetcher_without_dir_is_null: 未给离线目录 -> NullFetcher(不静默直连站点)
- test_local_page_fetcher_reads_scope_files: 离线页面替身按 <档位>.html 提供各档首屏
- test_local_page_fetcher_missing_and_bytes: 缺文件报「无通道」语义; 离线不取 .torrent
- test_run_hr_once_hints_when_disabled: 总开关关闭 -> 明确提示并返回非 0
- test_run_hr_once_hints_when_no_site: 无站点配置 hr_check -> 明确提示并返回非 0
- test_run_hr_once_reports_without_writing: 走查出报告(含站点文件路径与锁自检), 且**不写任何文件**
- test_run_hr_once_null_channel_reports_hint: 无离线目录且通道未启用 -> 如实报「无可用取数通道」并给出提示
"""
import io
import pathlib

from auto_qb.config.models import Config, HrCheckConfig, SiteHrCheckConfig, TrackerConfig
from auto_qb.hr.fetcher import HrChannelUnavailable, NullFetcher
from auto_qb.hr.report import LocalPageFetcher, build_fetcher, run_hr_once

from hr_helpers import EMPTY_TABLE_PAGE, myhr_page, row


def _config(tmp_path, html_dir=None, *, enabled=True, site_mode="partial") -> Config:
    cfg = Config()
    cfg.data_dir = str(tmp_path / "data")
    # 间隔设 0: 走查会真的按 min_torrent_interval 等待, 测试不必真等 90s
    # (「等满而不放弃」的行为由 test_hr_service.test_diagnostic_sleeper_waits_instead_of_giving_up 覆盖)
    cfg.hr_check = HrCheckConfig(enabled=enabled, min_torrent_interval=0.0)
    cfg.trackers["example"] = TrackerConfig(
        name="example",
        domains=["pt.example.com"],
        hr_check=SiteHrCheckConfig(mode=site_mode, hr_page_url="https://pt.example.com/myhr.php"),
    )
    return cfg


def _write_pages(directory: pathlib.Path, pages: dict) -> str:
    directory.mkdir(parents=True, exist_ok=True)
    for scope, html in pages.items():
        (directory / f"{scope}.html").write_text(html, encoding="utf-8")
    return str(directory)


def test_build_fetcher_without_dir_is_null():
    """未给离线目录 -> NullFetcher(绝不静默降级为后端直连)"""
    assert isinstance(build_fetcher(None), NullFetcher)


def test_local_page_fetcher_reads_scope_files(tmp_path):
    """离线页面替身按 <档位>.html 提供各档首屏"""
    html_dir = _write_pages(tmp_path / "pages", {"A": myhr_page([row(101)])})
    fetcher = LocalPageFetcher(html_dir)
    text = fetcher.get_text("https://pt.example.com/myhr.php?hrtype=A")
    assert "101" in text
    assert fetcher.used == ["A.html"]


def test_local_page_fetcher_missing_and_bytes(tmp_path):
    """缺文件报「无通道」语义; 离线不取 .torrent(只能验证解析与索引, 不回填 infohash)"""
    fetcher = LocalPageFetcher(str(tmp_path / "empty"))
    try:
        fetcher.get_text("https://pt.example.com/myhr.php?hrtype=B")
    except HrChannelUnavailable as e:
        assert "B.html" in str(e)
    else:  # pragma: no cover
        raise AssertionError("缺文件时应抛 HrChannelUnavailable")
    try:
        fetcher.get_bytes("https://pt.example.com/download.php?id=1")
    except HrChannelUnavailable as e:
        assert "不取 .torrent" in str(e)
    else:  # pragma: no cover
        raise AssertionError("离线模式不应提供 .torrent")


def test_run_hr_once_hints_when_disabled(tmp_path):
    """总开关关闭 -> 明确提示并返回非 0"""
    buf = io.StringIO()
    code = run_hr_once(_config(tmp_path, enabled=False), out=buf)
    assert code == 1
    assert "hr_check.enabled=false" in buf.getvalue()


def test_run_hr_once_hints_when_no_site(tmp_path):
    """无站点配置 hr_check -> 明确提示并返回非 0"""
    cfg = Config()
    cfg.data_dir = str(tmp_path)
    cfg.hr_check = HrCheckConfig(enabled=True)
    cfg.trackers["s"] = TrackerConfig(name="s", domains=["a.example"])
    buf = io.StringIO()
    assert run_hr_once(cfg, out=buf) == 1
    assert "没有任何站点配置 hr_check" in buf.getvalue()


def test_run_hr_once_reports_without_writing(tmp_path):
    """走查出报告(含站点文件路径与锁自检), 且不写任何文件"""
    html_dir = _write_pages(
        tmp_path / "pages", {
            "A": myhr_page([row(101)]),
            "B": EMPTY_TABLE_PAGE,
            "C": EMPTY_TABLE_PAGE
        }
    )
    cfg = _config(tmp_path)
    buf = io.StringIO()

    code = run_hr_once(cfg, html_dir, out=buf)

    text = buf.getvalue()
    assert code == 0
    assert "只读, 不写盘" in text
    assert "example.json" in text
    assert "锁自检: 可写" in text
    assert "覆盖证明=成立" in text
    assert "本次未写入任何文件" in text
    assert not (tmp_path / "data" / "hr" / "example.json").exists()


def test_run_hr_once_null_channel_reports_hint(tmp_path):
    """无离线目录且通道未启用 -> 如实报「无可用取数通道」, 并提示本轮只能确认配置/路径/锁"""
    cfg = _config(tmp_path)
    buf = io.StringIO()

    code = run_hr_once(cfg, None, out=buf)

    text = buf.getvalue()
    assert code == 0
    assert "no-channel" in text
    assert "未启用取数通道" in text
    assert "只能确认配置/路径/锁状态" in text
