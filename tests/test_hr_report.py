"""test_hr_report 测试计划: --hr-once 只读走查 / --hr-status 现状报告(均不进主循环、不写盘、不连 qB)

## 测试计划(每个测试函数一条)
- test_build_fetcher_without_dir_is_null: 未给离线目录 -> NullFetcher(不静默直连站点)
- test_local_page_fetcher_reads_scope_files: 离线页面替身按 <档位>.html 提供各档首屏
- test_local_page_fetcher_missing_and_bytes: 缺文件报「无通道」语义; 离线不取 .torrent
- test_run_hr_once_hints_when_disabled: 总开关关闭 -> 明确提示并返回非 0
- test_run_hr_once_hints_when_no_site: 无站点配置 hr_check -> 明确提示并返回非 0
- test_run_hr_once_reports_without_writing: 走查出报告(含站点文件路径与锁自检), 且**不写任何文件**
- test_run_hr_once_null_channel_reports_hint: 无离线目录且通道未启用 -> 如实报「无可用取数通道」并给出提示
- test_run_hr_status_hints_when_disabled: 状态报告在总开关关闭时也明确提示并返回非 0
- test_run_hr_status_hints_when_no_site: 状态报告无可用站点时提示并返回非 0
- test_run_hr_status_reports_data_without_fetching: 报告摊开档位/条目/放行/配额/明细, 且**站点文件一字未改**
- test_run_hr_status_shows_incomplete_reason_and_pending: 不完备的原因与原样计数(待回填 infohash)都显示出来
- test_run_hr_status_quota_text_rolls_stale_windows: 配额展示按窗口键折算 —— 上一小时/昨天的计数
  不得标成「本小时/本天」(否则「本小时 7/12 · 还能取 12 次」自相矛盾, 2026-09-25 实报)
- test_run_hr_status_rows_limit: 明细行数受 --hr-status-rows 限制并如实提示未显示行数
- test_run_hr_status_survives_broken_file: 站点文件坏掉时如实标 ⚠, 报告仍出得来
"""
import io
import pathlib
import time

from auto_qb.config.models import Config, HrCheckConfig, SiteHrCheckConfig, TrackerConfig
from auto_qb.hr.fetcher import HrChannelUnavailable, NullFetcher
from auto_qb.hr.ratelimit import day_key
from auto_qb.hr.report import LocalPageFetcher, build_fetcher, run_hr_once, run_hr_status
from auto_qb.hr.service import HrRefreshService
from auto_qb.hr.store import HrSiteStore

from hr_helpers import EMPTY_TABLE_PAGE, FakeFetcher, global_conf, myhr_page, row, site_conf, torrent_blob

SITE = "example"


def _config(tmp_path, html_dir=None, *, enabled=True, site_mode="partial", data_dir=None) -> Config:
    cfg = Config()
    cfg.data_dir = str(data_dir or tmp_path / "data")
    # 间隔设 0: 走查会真的按 min_torrent_interval 等待, 测试不必真等 90s
    # (「等满而不放弃」的行为由 test_hr_service.test_diagnostic_sleeper_waits_instead_of_giving_up 覆盖)
    cfg.hr_check = HrCheckConfig(enabled=enabled, min_torrent_interval=0.0)
    cfg.trackers[SITE] = TrackerConfig(
        name=SITE,
        domains=["pt.example.com"],
        hr_check=SiteHrCheckConfig(mode=site_mode, hr_page_url="https://pt.example.com/myhr.php"),
    )
    return cfg


def _seed(tmp_path, fetcher, *, site=None) -> None:
    """用真服务把一份数据落到 <tmp_path>/hr/<site>.json —— 现状报告读的就是它

    刻意不打钟(用真时钟): 报告里的「x 前 / 有效期至」才有意义。
    """
    HrRefreshService(
        data_dir=str(tmp_path),
        global_conf=global_conf(),
        site_confs={
            SITE: site or site_conf()
        },
        fetcher=fetcher,
        owner="tester",
        persist=True,
    ).refresh_site(SITE)


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


# ---------- --hr-status: 现状报告 ----------


def test_run_hr_status_hints_when_disabled(tmp_path):
    """状态报告在总开关关闭时也明确提示并返回非 0"""
    buf = io.StringIO()
    assert run_hr_status(_config(tmp_path, enabled=False), out=buf) == 1
    assert "hr_check.enabled=false" in buf.getvalue()


def test_run_hr_status_hints_when_no_site(tmp_path):
    """状态报告无可用站点时提示并返回非 0"""
    cfg = Config()
    cfg.data_dir = str(tmp_path)
    cfg.hr_check = HrCheckConfig(enabled=True)
    cfg.trackers["s"] = TrackerConfig(name="s", domains=["a.example"])
    buf = io.StringIO()
    assert run_hr_status(cfg, out=buf) == 1
    assert "没有任何站点配置 hr_check" in buf.getvalue()


def test_run_hr_status_reports_data_without_fetching(tmp_path):
    """报告摊开档位/条目/放行/配额/明细, 且**站点文件一字未改**(读现状不动数据)"""
    _seed(
        tmp_path,
        FakeFetcher(
            pages={
                "A": myhr_page([row(101)]),
                "B": myhr_page([row(201)]),  # B 档 = 站点侧已达标
                "C": EMPTY_TABLE_PAGE,
            },
            blobs={
                101: torrent_blob("a.bin"),
                201: torrent_blob("b.bin")
            },
        )
    )
    site_file = tmp_path / "hr" / f"{SITE}.json"
    before = site_file.read_bytes()
    cfg = _config(tmp_path, data_dir=tmp_path)
    buf = io.StringIO()

    code = run_hr_status(cfg, out=buf)

    text = buf.getvalue()
    assert code == 0
    assert "只读: 不取数 / 不加锁 / 不写盘" in text
    assert "覆盖证明=成立" in text
    assert "数据: 索引条目 2" in text and "受管束种子 2 个" in text
    assert "档位 A=1 B=1" in text
    assert "配额: 本小时" in text and "熔断: 正常" in text
    assert "已达标" in text, "站点点明已达标的那行(B 档)要看得见"
    assert "未触发任何取数" in text
    assert site_file.read_bytes() == before, "现状报告不得改写站点文件"


def test_run_hr_status_shows_incomplete_reason_and_pending(tmp_path):
    """不完备的原因、待回填 infohash、取种子失败计数都要能看见(这正是「数据对不对」的入口)"""
    _seed(
        tmp_path,
        FakeFetcher(pages={
            "A": myhr_page([row(101)], has_next=True),
            "B": EMPTY_TABLE_PAGE,
            "C": EMPTY_TABLE_PAGE
        }),
        site=site_conf(max_pages_per_refresh=1),  # 翻页上限挡住 => partial
    )
    buf = io.StringIO()

    code = run_hr_status(_config(tmp_path, data_dir=tmp_path), out=buf)

    text = buf.getvalue()
    assert code == 0
    assert "覆盖证明=不成立" in text
    assert "最近一次刷新不完备的原因: 档位 A 达到单次翻页上限(1)仍未到底" in text
    assert "待回填 infohash 1 条" in text
    assert "取种子失败 1 条" in text, "没有 .torrent 的站点应如实记失败次数"
    assert "101" in text


def test_run_hr_status_quota_text_rolls_stale_windows(tmp_path):
    """配额展示按窗口键折算: 窗口键翻篇后旧计数按 0 计, 与「还能取 N 次」同源一致"""
    now = time.time()
    store = HrSiteStore(SITE, str(tmp_path / "hr"), owner="tester")
    with store.hold() as session:
        session.data.quota.hour_window = "2000-01-01T00"  # 上一小时的窗口键(计数还挂着 7)
        session.data.quota.hour_count = 7
        session.data.quota.day_window = day_key(now)  # 天窗口仍是今天(计数有效)
        session.data.quota.day_count = 18
        session.commit(now)
    cfg = _config(tmp_path, data_dir=tmp_path)
    cfg.hr_check = HrCheckConfig(
        enabled=True, min_torrent_interval=0.0, max_torrents_per_hour=12, max_torrents_per_day=60
    )
    buf = io.StringIO()

    code = run_hr_status(cfg, out=buf)

    text = buf.getvalue()
    assert code == 0
    assert "本小时 0/12" in text, "上一小时的计数不得标成「本小时」"
    assert "本天 18/60" in text
    assert "还能取 12 次" in text, "与展示的已用数同源: min(12-0, 60-18)=12"


def test_run_hr_status_rows_limit(tmp_path):
    """明细行数受 --hr-status-rows 限制, 并如实提示还有多少行未显示"""
    _seed(
        tmp_path,
        FakeFetcher(
            pages={
                "A": myhr_page([row(101), row(102), row(103)]),
                "B": EMPTY_TABLE_PAGE,
                "C": EMPTY_TABLE_PAGE
            },
            blobs={
                101: torrent_blob("a.bin"),
                102: torrent_blob("b.bin"),
                103: torrent_blob("c.bin")
            },
        )
    )
    buf = io.StringIO()

    assert run_hr_status(_config(tmp_path, data_dir=tmp_path), limit=1, out=buf) == 0

    text = buf.getvalue()
    assert "最多显示 1 行" in text
    assert "还有 2 行未显示" in text
    assert "103" not in text, "超出行数的条目不该出现在明细里(但站点文件里仍有)"


def test_run_hr_status_survives_broken_file(tmp_path):
    """站点文件坏掉时如实标 ⚠, 报告仍出得来(不能因一个站点的坏文件就整份看不到)"""
    hr_dir = tmp_path / "hr"
    hr_dir.mkdir(parents=True, exist_ok=True)
    (hr_dir / f"{SITE}.json").write_text("{ 这不是 JSON", encoding="utf-8")
    buf = io.StringIO()

    assert run_hr_status(_config(tmp_path, data_dir=tmp_path), out=buf) == 0

    text = buf.getvalue()
    assert f"{SITE}.json" in text
    assert "⚠" in text
    assert "索引条目 0" in text
