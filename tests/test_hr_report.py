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
- test_run_hr_status_rows_aligned_and_truncated: 明细列纵向对齐(CJK 按双宽计)/ 长名称截断 / 档位显示
  实际意思 / 还需做种镜像站点形态(HH:MM:SS)/ 剩余达标时间不再显示 —— 它是「考核窗口」不是
  「还需做种的量」, 摆出来会被读成后者(2026-09-25 实报: 9d21h 被当成还要做种 9 天)
- test_run_hr_status_survives_broken_file: 站点文件坏掉时如实标 WARN:, 报告仍出得来
- test_run_hr_status_shows_observation_lines: 观测面四行(排序/P 分布/骤降/档位对比)
- test_run_hr_status_shows_order_violation: 排序违反轮的 x + 首处位置
- test_run_hr_status_zero_row_counter_attested_tail: M3 展示口径 —— 计数自证空集的零行波
  尾注标「计数自证空集, 无需人工确认」, 全文不再出现 --hr-confirm-empty 话术(计划 26-09-29-2036 §2.5)
- test_period_stats_consistency_and_gap: P 反算一致率与离散(前置实测2.的证据口径)
- test_run_hr_resume_clears_suspension: --hr-resume 清停用 + 记恢复痕迹; 未停用如实说明

### P1 覆盖率提升轮: 报告层长尾
- test_scope_of_url_variants: URL 档位提取(hrtype=/status=/都没有)
- test_confirm_empty_disabled_reports_hint: 确认戳在总开关关闭时明确提示非 0
- test_confirm_empty_readonly_and_lock_busy: 只读退化与锁占用各自的提示 + 非 0
- test_status_row_cells_marks_observation: 观察期行的档位文案后缀
- test_ellipsis_respects_cjk_double_width: CJK 双宽截断(保最后 1 格给 …)
- test_stamp_text_ts_zero_is_dash: 无时刻显示 "-"
- test_print_channel_lists_shared_dir_when_configured: 配了共享目录时明示
- test_print_site_includes_view_line: 走查报告视图行(view 非空输出)
"""
import io
import pathlib
import re
import time
import unicodedata

import pytest

from auto_qb.config.models import Config, HrCheckConfig, SiteHrCheckConfig, TrackerConfig
from auto_qb.hr.fetcher import HrChannelUnavailable, NullFetcher
from auto_qb.hr.model import FETCH_LANES, HrEntry
from auto_qb.hr.adapters.nexusphp import NexusPhpMyhrAdapter
from auto_qb.hr.ratelimit import day_key
from auto_qb.hr.report import LocalPageFetcher, build_fetcher, run_hr_confirm_empty, run_hr_once, run_hr_status
import auto_qb.hr.service as hr_service
from auto_qb.hr.service import HrRefreshService
from auto_qb.hr.store import HrSiteStore

from hr_helpers import EMPTY_TABLE_PAGE, FakeFetcher, global_conf, myhr_page, row, site_conf, torrent_blob

SITE = "example"


def _config(tmp_path, html_dir=None, *, enabled=True, site_enabled=True, data_dir=None) -> Config:
    cfg = Config()
    cfg.data_dir = str(data_dir or tmp_path / "data")
    # 间隔设 0: 走查会真的按 min_interval 等待, 测试不必真等 90s
    cfg.hr_check = HrCheckConfig(enabled=enabled, min_interval=0.0)
    cfg.trackers[SITE] = TrackerConfig(
        name=SITE,
        domains=["pt.example.com"],
        hr_check=SiteHrCheckConfig(
            enabled=site_enabled,
            tracker=SITE,
            hr_page_url="https://pt.example.com/myhr.php",
            required_seeding_time=86400.0,
        ),
    )
    return cfg


def _seed(tmp_path, fetcher, *, site=None, gconf=None) -> None:
    """用真服务把一份数据落到 <tmp_path>/hr/<site>.json —— 现状报告读的就是它

    刻意不打钟(用真时钟): 报告里的「x 前 / 复用窗至」才有意义。
    """
    HrRefreshService(
        data_dir=str(tmp_path),
        global_conf=gconf or global_conf(),
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
    assert "没有任何站点启用 hr_check" in buf.getvalue()


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
    assert "各档:" in text, "波次视图要摊出各档状态"
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
    assert "没有任何站点启用 hr_check" in buf.getvalue()


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
    assert "放行签发=开" in text
    assert "数据: 索引条目 2" in text and "考察中命中 1 个" in text
    assert "档位 A=1 B=1" in text
    assert "频控: 今天" in text
    assert "已达标" in text, "站点点明已达标的那行(B 档)要看得见"
    assert "上传量" in text and "还需做种" in text, "明细要摊出站点侧上传量与还需做种时间"
    assert "剩余达标" not in text, "剩余达标时间是「考核窗口」不是「还需做种的量」, 不再显示"
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
        gconf=global_conf(max_pages_per_wave=3),  # 3 页被三档均分 => A 截断(没翻到第 2 页)
    )
    buf = io.StringIO()

    code = run_hr_status(_config(tmp_path, data_dir=tmp_path), out=buf)

    text = buf.getvalue()
    assert code == 0
    assert "达到单波页数上限" in text, "截断原因要在各档明细里可见"
    assert "待回填 infohash 1 条" in text or True
    assert "待回填 infohash 1 条" in text
    assert "取种子失败 1 条" in text, "没有 .torrent 的站点应如实记失败次数"
    assert "101" in text


def test_run_hr_status_quota_text_rolls_stale_windows(tmp_path):
    """日额展示按窗口键折算: 昨天的窗口键翻篇后旧计数按 0 计, 与「还能取 N 次」同源一致"""
    now = time.time()
    store = HrSiteStore(SITE, str(tmp_path / "hr"), owner="tester")
    with store.hold() as session:
        session.data.rate.day_window = "2000-01-01"  # 昨天的窗口键(计数还挂着 50)
        session.data.rate.day_count = 50
        session.commit(now)
    cfg = _config(tmp_path, data_dir=tmp_path)
    cfg.hr_check = HrCheckConfig(enabled=True, min_interval=0.0, max_requests_per_day=240)
    buf = io.StringIO()

    code = run_hr_status(cfg, out=buf)

    text = buf.getvalue()
    assert code == 0
    assert "今天 0/240" in text, "昨天的计数不得标成「今天」"
    assert "还能取 240 次" in text


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
    # !断言用「默认种子名」特征串而非裸 tid: text 含临时目录路径, 裸 "103" 会撞上
    # pytest-of-<user>/pytest-<counter> 的计数编号(2026-10-01 实报 pytest-1033 假红)
    assert "EXAMPLE 103" not in text, "超出行数的条目不该出现在明细里(但站点文件里仍有)"


def test_run_hr_status_rows_aligned_and_truncated(tmp_path):
    """明细列纵向对齐(CJK 按双宽计)、长名称截断; 档位显示实际意思, 还需做种镜像站点形态"""
    _seed(
        tmp_path,
        FakeFetcher(
            pages={
                "A":
                    myhr_page(
                        [
                            row(101, "An Example Name That Is Definitely Longer Than Forty Display Cells 2026 1080p"),
                            row(102, "短名"),
                        ]
                    ),
                "B":
                    EMPTY_TABLE_PAGE,
                "C":
                    EMPTY_TABLE_PAGE,
            },
            blobs={
                101: torrent_blob("a.bin"),
                102: torrent_blob("b.bin")
            },
        ),
    )
    buf = io.StringIO()

    assert run_hr_status(_config(tmp_path, data_dir=tmp_path), out=buf) == 0

    text = buf.getvalue()
    assert "剩余达标" not in text
    assert "考察中" in text, "档位要显示实际意思(A=考察中), 不是光秃秃的字母"
    assert "01:00:00" in text, "还需做种镜像站点书写形态(HH:MM:SS)"
    assert "0.500" in text, "分享率按站点侧 3 位小数显示"

    def cells_width(s: str) -> int:
        return sum(2 if unicodedata.east_asian_width(ch) in ("F", "W") else 1 for ch in s)

    detail = [ln for ln in text.splitlines() if re.match(r"^ {8}10[12]  考察中", ln)]
    assert len(detail) == 2
    starts = []
    for ln in detail:
        m = re.search(r"[0-9a-f]{12}$", ln.rstrip())
        assert m, f"明细行应以 12 位 infohash 结尾: {ln!r}"
        starts.append(cells_width(ln[:m.start()]))
    assert len(set(starts)) == 1, "infohash 列要纵向对齐: CJK 短名行与截断长名行必须同一列位"
    assert "…" in detail[0], "超宽名称要截断"
    assert "短名" in detail[1]


def test_run_hr_status_survives_broken_file(tmp_path):
    """站点文件坏掉时如实标 WARN:, 报告仍出得来(不能因一个站点的坏文件就整份看不到)"""
    hr_dir = tmp_path / "hr"
    hr_dir.mkdir(parents=True, exist_ok=True)
    (hr_dir / f"{SITE}.json").write_text("{ 这不是 JSON", encoding="utf-8")
    buf = io.StringIO()

    assert run_hr_status(_config(tmp_path, data_dir=tmp_path), out=buf) == 0

    text = buf.getvalue()
    assert f"{SITE}.json" in text
    assert "WARN:" in text
    assert "索引条目 0" in text


# ---------- 防伪观测面(v3, 计划 26-09-28-1932 §5.3) ----------


def test_run_hr_status_shows_defense_lines(tmp_path):
    """防伪观测行: A 档流转守恒 / 骤降观测 / 各档波次 —— 「证据是否成立」的现场证据"""
    _seed(
        tmp_path,
        FakeFetcher(
            pages={
                "A": myhr_page([row(101), row(102)]),
                "B": EMPTY_TABLE_PAGE,
                "C": EMPTY_TABLE_PAGE,
            },
            blobs={
                101: torrent_blob("a.bin"),
                102: torrent_blob("b.bin")
            },
        ),
    )
    buf = io.StringIO()

    code = run_hr_status(_config(tmp_path, data_dir=tmp_path), out=buf)

    text = buf.getvalue()
    assert code == 0
    assert "守恒: 不适用(上波无 A 档行)" in text
    assert "骤降" not in text  # 骤降保护已按 26-09-29 裁决移除
    assert "各档: A:" in text and "B:" in text and "C:" in text


def test_run_hr_status_shows_order_violation_note(tmp_path):
    """排序违反波的报告: 各档行标出该档状态 + 备注行给出首处位置(告警与报告同源)"""
    _seed(
        tmp_path,
        FakeFetcher(
            pages={
                "A":
                    myhr_page(
                        [
                            row(101, done="2026-09-25 10:00:00"),
                            row(102, done="2026-09-24 10:00:00"),
                            row(103, done="2026-09-26 10:00:00"),  # 乱序行
                        ]
                    ),
                "B":
                    EMPTY_TABLE_PAGE,
                "C":
                    EMPTY_TABLE_PAGE,
            },
            blobs={
                101: torrent_blob("a.bin"),
                102: torrent_blob("b.bin"),
                103: torrent_blob("c.bin")
            },
        ),
    )
    buf = io.StringIO()

    code = run_hr_status(_config(tmp_path, data_dir=tmp_path), out=buf)

    text = buf.getvalue()
    assert code == 0
    assert "排序违反(页内逆序 1 处)" in text and "强制早停" in text


def test_run_hr_confirm_empty_stamps_site(tmp_path):
    """--hr-confirm-empty: 写一次性人工对账戳 + 记确认痕迹(计划 26-09-28-1932 §5.3)"""
    from auto_qb.hr.store import HrSiteStore

    store = HrSiteStore(SITE, str(tmp_path / "hr"))
    cfg = _config(tmp_path, data_dir=tmp_path)

    buf = io.StringIO()
    code = run_hr_confirm_empty(cfg, [SITE], out=buf)

    text = buf.getvalue()
    assert code == 0
    assert "已写入人工对账戳" in text
    assert "确认戳自动失效" in text
    data, err = store.read_unlocked()
    assert err is None and data.empty_confirmed_at > 0, "确认戳落盘"
    assert "人工对账" in data.wave.notes, "站点文件里留下可查的确认痕迹"

    # 清单再现非零行时由波次引擎自动清戳(service 侧测试覆盖), 这里验幂等重复写入不炸
    buf2 = io.StringIO()
    assert run_hr_confirm_empty(cfg, [SITE], out=buf2) == 0
    assert "已写入人工对账戳" in buf2.getvalue()


def test_run_hr_status_zero_row_counter_attested_tail(tmp_path, monkeypatch):
    """M3 展示口径(计划 26-09-29-2036 §2.5): 计数自证空集(各档声明全 0)的零行波,
    零行尾注标「计数自证空集, 无需人工确认」且全文不再出现 --hr-confirm-empty 话术;
    对照: 未证到计数的零行波维持「未确认」旧口径(行为面守阵见 test_zero_rows_no_release)。"""
    class _CounterNexus(NexusPhpMyhrAdapter):
        def parse_counters(self, html):
            return {lane: 0 for lane in FETCH_LANES}

    monkeypatch.setattr(
        hr_service,
        "build_adapter",
        lambda site, conf: _CounterNexus(
            site,
            hr_page_url=conf.hr_page_url,
            download_path=conf.download_path,
            scopes=FETCH_LANES,
            page_param=conf.page_param,
        ),
    )
    _seed(tmp_path, FakeFetcher(pages={l: EMPTY_TABLE_PAGE for l in "ABC"}))

    buf = io.StringIO()
    assert run_hr_status(_config(tmp_path, data_dir=tmp_path), out=buf) == 0

    text = buf.getvalue()
    assert "计数自证空集, 无需人工确认" in text
    assert "未确认 —— 零行波不签发放行" not in text
    assert "--hr-confirm-empty" not in text, "计数自证的站点不再被引导去人工对账"


# ==================== P1 覆盖率提升轮: 报告层长尾 ====================


def test_scope_of_url_variants():
    """URL 档位提取: hrtype= / status=(CarPT 变体) / 都没有 -> ?"""
    from auto_qb.hr.report import _scope_of

    assert _scope_of("https://pt.example.com/myhr.php?hrtype=A&page=2") == "A"
    assert _scope_of("https://carpt.net/myhr.php?status=1") == "1"
    assert _scope_of("https://pt.example.com/index.php") == "?"


def test_confirm_empty_disabled_reports_hint(tmp_path):
    """--hr-confirm-empty 在总开关关闭时明确提示并返回非 0(不静默成功)"""
    out = io.StringIO()
    code = run_hr_confirm_empty(_config(tmp_path, enabled=False), [SITE], out=out)
    assert code == 1 and "hr_check.enabled=false" in out.getvalue()


def test_confirm_empty_readonly_and_lock_busy(tmp_path, monkeypatch):
    """写戳遇只读退化(锁自检失败)/锁被占用 -> 各自明确提示并返回非 0"""
    cfg = _config(tmp_path)
    # 只读退化(锁自检判不生效): run_hr_confirm_empty 每次新建服务/存储, 锁自检基线从 0 起算,
    # 无法经文件制造回退 —— 在自检决策点注入退化条件, 验证报告层的提示与退出码
    monkeypatch.setattr(HrSiteStore, "_check_lock_effective", lambda self, data: False)
    out = io.StringIO()
    assert run_hr_confirm_empty(cfg, [SITE], out=out) == 1
    assert "锁自检失败" in out.getvalue()
    monkeypatch.undo()
    # 锁被占用(真实互斥: 其它实例持锁)
    out2 = io.StringIO()
    outsider = HrSiteStore(SITE, str(pathlib.Path(cfg.data_dir) / "hr"), lock_timeout=0.0, owner="other")
    with outsider.hold():
        code = run_hr_confirm_empty(cfg, [SITE], out=out2)
    assert code == 1 and "锁被占用" in out2.getvalue()


def test_status_row_cells_marks_observation():
    """观察期中的行: 档位文案带「观察期N」后缀(明细表一眼可辨)"""
    from auto_qb.hr.report import _status_row_cells

    entry = HrEntry(tid=11, name="Example.Show.S01", lane="A", downloaded_bytes=1024**3, missing_streak=1)
    cells = _status_row_cells(entry)
    assert cells[1] == "考察中(观察期1)"
    plain = HrEntry(tid=12, name="Example.Show.S02", lane="B")
    assert _status_row_cells(plain)[1] == "已达标"


def test_ellipsis_respects_cjk_double_width():
    """按显示格宽截断: CJK 算 2 格, 超宽保最后 1 格给 …"""
    from auto_qb.hr.report import _dwidth, _ellipsis

    short = "Example.S01"
    assert _ellipsis(short, 40) == short, "未超宽原样返回"
    wide = "虽然我不是完美恶女～雏宫蝶鼠替换传～" * 3
    cut = _ellipsis(wide, 20)
    assert _dwidth(cut) <= 20 and cut.endswith("…")
    assert _dwidth(cut[:-1]) <= 19, "正文部分不超可用格宽"


def test_stamp_text_ts_zero_is_dash():
    """无时刻(0/None 语义)显示 '-'(不渲染 1970)"""
    from auto_qb.hr.report import stamp_text_ts

    assert stamp_text_ts(0.0) == "-"
    assert stamp_text_ts(1700000000.0).startswith("20")


def test_print_channel_lists_shared_dir_when_configured(tmp_path):
    """配了 shared_dir: 通道自检段明示共享目录(多实例共用同一份数据)"""
    from auto_qb.hr.report import _print_channel

    cfg = _config(tmp_path)
    cfg.hr_check.shared_dir = "R:/Shared/hr"
    service = HrRefreshService(
        data_dir=str(tmp_path),
        global_conf=cfg.hr_check,
        site_confs={SITE: site_conf()},
        fetcher=NullFetcher("x"),
        owner="t",
        persist=False,
    )
    out = io.StringIO()
    _print_channel(cfg, service, out)
    assert "R:/Shared/hr" in out.getvalue() and "多实例共用" in out.getvalue()


def test_print_site_includes_view_line(tmp_path):
    """走查报告的视图行: 命中/放行/通道人话(view 非空时输出)"""
    from auto_qb.hr.model import CHANNEL_OK
    from auto_qb.hr.report import _print_site
    from auto_qb.hr.service import HrRefreshResult
    from auto_qb.hr.resolve import HrEntry, HrSiteView

    result = HrRefreshResult(site=SITE, action="refreshed", reason="", pages_fetched=3)
    view = HrSiteView(
        site=SITE,
        listing="list",
        channel_state=CHANNEL_OK,
        generated_at=1.0,
        lane_a={"H": HrEntry(tid=1, name="x")},
        verified={"H2": None} or {},
    )
    out = io.StringIO()
    _print_site(result, view, out)
    assert "考察中命中=1" in out.getvalue() and "通道=" in out.getvalue()
