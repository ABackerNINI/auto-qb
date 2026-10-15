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
- test_run_hr_status_shows_defense_lines: 防伪观测行: A 档流转守恒 / 骤降观测 / 各档波次
- test_run_hr_status_shows_order_violation_note: 排序违反波的报告: 各档行标出该档状态 + 备注行给出首处位置
- test_run_hr_status_zero_row_counter_attested_tail: M3 展示口径 —— 计数自证空集的零行波
  尾注标「计数自证空集, 无需人工确认」, 全文不再出现 --hr-confirm-empty 话术(计划 26-09-29-2036 §2.5)

### P1 覆盖率提升轮: 报告层长尾
- test_scope_of_url_variants: URL 档位提取(hrtype=/status=/都没有)
- test_confirm_empty_disabled_reports_hint: 确认戳在总开关关闭时明确提示非 0
- test_confirm_empty_readonly_and_lock_busy: 只读退化与锁占用各自的提示 + 非 0
- test_confirm_empty_records_history_event: 对账动作入拉取历史(计划 26-10-04-0312 §3.3)——
  恰一条 confirm_empty 事件(trigger=confirm / action=confirm-empty)随既有 commit 落盘
- test_status_row_cells_marks_observation: 观察期行的档位文案后缀
- test_ellipsis_respects_cjk_double_width: CJK 双宽截断(保最后 1 格给 …)
- test_print_channel_lists_shared_dir_when_configured: 配了共享目录时明示
- test_print_site_includes_view_line: 走查报告视图行(view 非空输出)

### R20 展示导出变异守阵(issue 26-10-10-1108-test-hr-mutation-display, 排序口径/宽字符对齐/人话回落)
- test_status_rows_sort_missing_download_tiebreak: 明细排序与 entry_details 同公式(缺失按 0; None 与 1 的次序)
- test_status_rows_limit_boundary_no_leftover_line: 行数恰等 limit 不出「还有 N 行未显示」(> 口径)
- test_status_rows_header_and_alignment_exact: 表头逐字 + 八列对齐方向(tid/数值右, 档位/名称/infohash 左)
- test_status_row_cells_hash_lane_and_ratio: infohash 取 12 位(v1 优先/空回落 -) + 未知档位回落 + 量值缺省 0 + ratio None
- test_dwidth_classifies_wide: 全角/宽字符算 2 格(F/W 两类都认)
- test_pad_direction_and_default: 默认左对齐 + right 分支逐字(补位格宽)
- test_ellipsis_boundaries_exact: 截断边界(恰宽不截/ASCII 与 CJK 各形态/None 回落空串)
- test_print_channel_lines_exact: 通道自检段逐行(端点/密钥来源/扩展 origin/共享目录两分支)
- test_print_site_lines_exact: 走查站点段逐行(action/锁自检/各档/视图行 + 未知通道回落)
- test_run_hr_once_force_bypasses_interval_gate: force=True 绕过拉取间隔闸(走查本义)
- test_run_hr_once_view_line_and_separators: 走查输出面(视图行/分隔线/站点表 join/提示/耗时量纲)
- test_run_hr_status_lines_exact: 现状输出面(头两行/分隔线/两条提示/默认 limit 10)
- test_run_hr_confirm_empty_note_and_stamp: 对账 notes 累加不丢旧备注 + 事件 site + 打印戳与落盘一致
- test_build_fetcher_null_message: 无通道提示逐字(含配置键名, 不静默降级)
- test_local_page_fetcher_replaces_bad_bytes: 离线页面按 utf-8/replace 读(坏字节不抛)
"""
import io
import pathlib
import re
import time
import unicodedata

import pytest

from auto_qb.config.models import Config, HrCheckConfig, HrChannelConfig, SiteHrCheckConfig, TrackerConfig
from auto_qb.hr.channel import token_path
from auto_qb.hr.fetcher import HrChannelUnavailable, NullFetcher
from auto_qb.hr.model import FETCH_LANES, HrEntry, HrSiteData
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
            download_path="/download.php?id={id}",
            page_param="page",
            listing="list",
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


def test_confirm_empty_records_history_event(tmp_path):
    """对账动作入拉取历史(计划 26-10-04-0312 §3.3): 恰一条 confirm_empty 事件随既有 commit 落盘"""
    store = HrSiteStore(SITE, str(tmp_path / "hr"))
    cfg = _config(tmp_path, data_dir=tmp_path)
    buf = io.StringIO()

    assert run_hr_confirm_empty(cfg, [SITE], out=buf) == 0

    data, err = store.read_unlocked()
    assert err is None and data.empty_confirmed_at > 0, "对账戳照常落盘"
    (ev, ) = data.history
    assert (ev.kind, ev.trigger, ev.action) == ("confirm_empty", "confirm", "confirm-empty")
    assert "人工对账" in ev.reason
    assert ev.ts > 0 and len(ev.by) == 6, "by = 写者实例短标识(store.owner 前 6 位)"
    assert ev.rows == 0 and ev.lanes == [], "对账事件不携带波次计数字段"


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


# ==================== R20 展示导出变异守阵(issue 26-10-10-1108-test-hr-mutation-display) ====================
# 排序口径与 CLI 一致 · 宽字符对齐口径 · 人话映射未知回落原文


def _rows_seed(tmp_path, entries, blobs=None):
    """落一份含指定条目的站点数据(明细表读它)"""
    _seed(
        tmp_path,
        FakeFetcher(
            pages={
                "A": myhr_page(entries),
                "B": EMPTY_TABLE_PAGE,
                "C": EMPTY_TABLE_PAGE
            },
            blobs=blobs or {},
        ),
    )


def test_status_rows_sort_missing_download_tiebreak():
    """明细排序与 entry_details 同公式(key = 档位, -下载量; 缺失按 0) —— None 与 1 的次序"""
    # 直接构造: _print_status_rows 只认 data.index, 不起引擎
    from auto_qb.hr.report import _print_status_rows

    data = HrSiteData()
    data.index = {
        201: HrEntry(tid=201, name="n201", lane="A", downloaded_bytes=None),
        202: HrEntry(tid=202, name="n202", lane="A", downloaded_bytes=1),
        203: HrEntry(tid=203, name="n203", lane="A", downloaded_bytes=1000),
    }
    out = io.StringIO()
    _print_status_rows(data, 10, out)
    body = [ln for ln in out.getvalue().splitlines() if "n20" in ln]
    assert [ln.split()[0] for ln in body] == ["203", "202", "201"], "下载量降序; 缺失(按 0)落 1 之后"
    # 降序方向: 把 sort 的负号掰正会变升序(201/202/203), 被上一句钉死;
    # 列位固定所以各行 name 的字符下标相同, 不比位置比行序


def test_status_rows_limit_boundary_no_leftover_line():
    """行数恰等 limit 不出「还有 N 行未显示」(> 口径; >= 会多印一行)"""
    from auto_qb.hr.model import HrSiteData
    from auto_qb.hr.report import _print_status_rows

    data = HrSiteData()
    data.index = {i: HrEntry(tid=i, name=f"n{i}", lane="A") for i in (1, 2, 3)}
    out = io.StringIO()
    _print_status_rows(data, 3, out)
    assert "还有" not in out.getvalue(), "恰等 limit 不提示未显示行"
    out2 = io.StringIO()
    _print_status_rows(data, 2, out2)
    assert "还有 1 行未显示" in out2.getvalue()


def test_status_rows_header_and_alignment_exact():
    """表头逐字 + 八列对齐方向(tid/上传/下载/分享率/还需做种右, 档位/名称/infohash 左)

    期望行**硬编码**: 若用被测模块的 _pad/_dwidth 重建, 它们被变异时期望跟着变, 自证死循环。
    """
    from auto_qb.hr.model import HrSiteData
    from auto_qb.hr.report import _print_status_rows

    data = HrSiteData()
    data.index = {11: HrEntry(tid=11, name="短", lane="A", uploaded_bytes=1, downloaded_bytes=2, ratio=0.5)}
    out = io.StringIO()
    _print_status_rows(data, 10, out)
    lines = out.getvalue().splitlines()
    header = next(ln for ln in lines if "tid" in ln and "infohash" in ln)
    row_line = next(ln for ln in lines if ln.lstrip().startswith("11"))
    assert header == "        tid  档位    上传量  下载量  分享率  还需做种  名称  infohash", "表头逐字(文案/列宽/对齐)"
    assert row_line == "         11  考察中     1 B     2 B   0.500         -  短    -       ", "数据行逐字同口径铺列"
    # tid 右对齐: 8 空格前缀 + 1 格补位(方向被杀成左对齐会前移 1 格)
    assert row_line.index("11") == 9, "tid 列右对齐(左侧补位)"
    assert row_line.rstrip().endswith("-"), "infohash 列在行尾(左对齐, 尾部有补位空格)"


def test_status_row_cells_hash_lane_and_ratio():
    """infohash 取 12 位(v1 优先/双空回落 -) + 未知档位回落原文 + 量值缺省 0 + ratio None"""
    from auto_qb.hr.model import HrEntry
    from auto_qb.hr.report import _status_row_cells

    v1 = "a" * 40
    cells = _status_row_cells(HrEntry(tid=1, name="x", lane="A", infohash_v1=v1, infohash_v2="b" * 40))
    assert cells[7] == v1[:12], "v1 优先且只取 12 位(不是 13)"
    assert _status_row_cells(HrEntry(tid=2, name="x", lane="A", infohash_v2="b" * 40))[7] == "b" * 12, "仅 v2 也可用"
    assert _status_row_cells(HrEntry(tid=3, name="x", lane="A"))[7] == "-", "双空回落 -"
    assert _status_row_cells(HrEntry(tid=4, name="x", lane="Z"))[1] == "Z", "未知档位回落原文, 不是 None"
    none_up = _status_row_cells(HrEntry(tid=5, name="x", lane="A", uploaded_bytes=None, downloaded_bytes=None))
    assert none_up[2] == "0 B" and none_up[3] == "0 B", "量值缺省按 0 展示(or 0 口径)"
    assert _status_row_cells(HrEntry(tid=6, name="x", lane="A", ratio=None))[4] == "-", "ratio 缺失展示 -"
    assert _status_row_cells(HrEntry(tid=7, name="x", lane="A", ratio=1.5))[4] == "1.500", "ratio 三位小数"
    wide41 = "名" * 20 + "x"  # 41 格
    cut = _status_row_cells(HrEntry(tid=8, name=wide41, lane="A"))[6]
    assert cut.endswith("…"), "超 40 格的名称截断(宽度 41 会被 mutant 放行)"


def test_dwidth_classifies_wide():
    """显示格宽: 全角(F)与宽字符(W)都算 2, ASCII 算 1"""
    from auto_qb.hr.report import _dwidth

    assert _dwidth("") == 0 and _dwidth("abc") == 3
    assert _dwidth("中文") == 4, "CJK(表意文字, W)算双宽"
    assert _dwidth("Ａ") == 2, "全角形式(F)同样算双宽"
    assert _dwidth("a中b") == 4


def test_pad_direction_and_default():
    """补位: 默认左对齐(文本在左); right=True 右对齐; 补位格宽按显示宽"""
    from auto_qb.hr.report import _dwidth, _pad

    assert _pad("x", 5) == "x    ", "默认左对齐(文本左侧, 右侧补位)"
    assert _pad("x", 5, right=True) == "    x", "right=True 右对齐"
    assert _pad("x", 5, right=False) == "x    ", "right=False 显式左对齐"
    assert _pad("中", 5) == "中   ", "双宽字符只补 3 格(按显示宽, 不是字符数)"
    assert _pad("abc", 2) == "abc", "已超宽不补"


def test_ellipsis_boundaries_exact():
    """截断边界: None 回落空串 / 恰宽不截 / 超宽保最后 1 格给 … / ASCII 与 CJK 分别按 1/2 格计"""
    from auto_qb.hr.report import _dwidth, _ellipsis

    assert _ellipsis(None, 10) == "" and _ellipsis("", 10) == ""
    assert _ellipsis("abcde", 5) == "abcde", "恰等宽不截"
    assert _ellipsis("abcdef", 5) == "abcd…", "ASCII 超宽截到 4 格 + …"
    assert _ellipsis("中中中", 5) == "中中…", "CJK 按双宽: 5 格容 2 字 + …"
    cut = _ellipsis("虽然我不是完美恶女", 9)
    assert _dwidth(cut) <= 9 and cut.endswith("…"), "截断后不超目标宽"
    assert _dwidth(cut[:-1]) <= 8, "正文部分给 … 留 1 格"


def test_print_channel_lines_exact(tmp_path):
    """通道自检段逐行: 端点/轮询/等回传/密钥来源/扩展 origin/共享目录两分支"""
    from auto_qb.config.models import HrChannelConfig
    from auto_qb.hr.report import _print_channel

    cfg = _config(tmp_path)
    cfg.hr_check.channel = HrChannelConfig(
        enabled=True, port=18765, request_timeout=45.0, extension_id="ext123", token="tok"
    )
    cfg.hr_check.shared_dir = ""
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
    lines = out.getvalue().splitlines()
    assert lines[0] == "取数通道: 启用"
    assert lines[
        1
    ] == "    端点: http://127.0.0.1:18765/api/hr/tasks   轮询节奏: 60s(常量)   等回传上限: 45s   发现端口: 18788(0 = 关闭发现)", "去端口+跨机(计划 26-10-14-1241): 自述行带发现端口"
    assert lines[2] == f"    密钥来源: config({token_path(cfg.data_dir)})   只放行扩展 ext123"
    assert lines[3] == (f"    共享目录: 未配置 ⇒ 站点文件落 {service.dir}; 多实例共享同一账号时需指向同一目录(云同步盘不可用)"), "共享目录未配置分支逐字(含云同步盘告警)"
    # 未启用 + 未配扩展 + 配了共享目录的分支
    cfg2 = _config(tmp_path)
    cfg2.hr_check.channel = HrChannelConfig(enabled=False)
    cfg2.hr_check.shared_dir = "R:/Shared/hr"
    out2 = io.StringIO()
    _print_channel(cfg2, service, out2)
    lines2 = out2.getvalue().splitlines()
    assert lines2[0] == "取数通道: 未启用(本实例无取数能力, 只会读共享数据)"
    assert lines2[2] == f"    密钥来源: none({token_path(cfg2.data_dir)})   放行任意扩展 origin(靠 token 鉴权)", \
        "未配扩展时的 origin 文案逐字"
    assert lines2[3] == "    共享目录: R:/Shared/hr(多实例共用同一份站点数据)"


def test_print_site_lines_exact():
    """走查站点段逐行: action/reason/锁自检/各档计数/视图行 + 未知通道态回落原文"""
    from auto_qb.hr.report import _print_site
    from auto_qb.hr.service import HrRefreshResult
    from auto_qb.hr.resolve import HrEntry, HrSiteView

    result = HrRefreshResult(
        site=SITE,
        action="partial",
        reason="",
        pages_fetched=3,
        entries=2,
        lane_texts="A:[x]1页2行",
        torrents_fetched=1,
        torrents_failed=2,
        verified_count=3,
        releases_signed=4,
        lock_ok=True,
    )
    view = HrSiteView(
        site=SITE,
        listing="list",
        channel_state="zzz",
        generated_at=1.0,
        healthy_ts=1_699_999_000.0,
        lane_a={"H": HrEntry(tid=1, name="x")},
        verified={},
    )
    out = io.StringIO()
    _print_site(result, view, out)
    lines = out.getvalue().splitlines()
    assert lines[0] == f"[{SITE}] partial — 正常", "reason 空回落「正常」"
    assert lines[1] == f"    文件: {result.path}    锁自检: 可写"
    assert lines[2] == "    各档: A:[x]1页2行  页数: 3  条目: 2  取种子: 1 失败: 2  放行记录: 3  本波签发: 4"
    assert "通道=zzz" in lines[3], "未知通道态回落原文(不是 None)"
    assert "考察中命中=1" in lines[3]
    assert "最近健康波=从未" not in lines[3], "健康波时刻来自 view.healthy_ts(None 会回落「从未」)"
    assert "最近健康波=" in lines[3] and lines[3].rstrip().endswith("通道=zzz")
    bad_lock = HrRefreshResult(site=SITE, action="error", reason=" Boom ", pages_fetched=0, lock_ok=False)
    out2 = io.StringIO()
    _print_site(bad_lock, None, out2)
    assert "锁自检: 只读退化(锁疑似不生效)" in out2.getvalue()
    assert f"[{SITE}] error —  Boom " in out2.getvalue(), "reason 非空时原样(不回落正常)"
    assert "    各档: -  页数: 0" in out2.getvalue(), "lane_texts 空回落 '-'"


def test_run_hr_once_force_bypasses_interval_gate(tmp_path, monkeypatch):
    """走查本义 = 人工立即跑一波: force=True 越过复用窗/拉取间隔两道调度闸(掰成 False 会被闸成「复用/未到时刻」)"""
    import auto_qb.hr.report as report_mod

    # 刚落一盘(healthy_ts/fetched_at=now, expires_at=now+2h) ⇒ 不 force 必撞复用窗
    _rows_seed(tmp_path, [row(101)], blobs={101: torrent_blob("a.bin")})
    monkeypatch.setattr(
        report_mod,
        "build_fetcher",
        lambda _dir: FakeFetcher(
            pages={
                "A": myhr_page([row(101)]),
                "B": EMPTY_TABLE_PAGE,
                "C": EMPTY_TABLE_PAGE
            },
            blobs={101: torrent_blob("a.bin")},
        ),
    )
    cfg = _config(tmp_path, data_dir=tmp_path)  # min_interval=0: 账号安全线不拦, 只测 force 越过的调度闸
    buf = io.StringIO()
    assert run_hr_once(cfg, None, out=buf) == 0
    text = buf.getvalue()
    assert "refreshed" in text, "force 走查不被复用窗/拉取间隔闸挡下"
    assert "数据仍在复用窗" not in text and "未到拉取时刻" not in text


def test_run_hr_once_view_line_and_separators(tmp_path, monkeypatch):
    """走查输出面: 视图行/分隔线(92 连字符)/站点表 join/无通道提示/耗时量纲"""
    import auto_qb.hr.report as report_mod

    html_dir = _write_pages(
        tmp_path / "pages", {
            "A": myhr_page([row(101)]),
            "B": EMPTY_TABLE_PAGE,
            "C": EMPTY_TABLE_PAGE
        }
    )
    # LocalPageFetcher 不提供 .torrent(整波被拦成 no-channel, 无快照) ⇒ 注入口罩通道把波跑完
    monkeypatch.setattr(
        report_mod,
        "build_fetcher",
        lambda _dir: FakeFetcher(
            pages={
                "A": myhr_page([row(101)]),
                "B": EMPTY_TABLE_PAGE,
                "C": EMPTY_TABLE_PAGE
            },
            blobs={101: torrent_blob("a.bin")},
        ),
    )
    cfg = _config(tmp_path)
    buf = io.StringIO()
    assert run_hr_once(cfg, html_dir, out=buf) == 0
    lines = buf.getvalue().splitlines()
    assert lines[0] == "HR 在线核实走查(只读, 不写盘) 共 1 个站点: example", "站点表用 ', ' 连接"
    assert lines[1].startswith("站点文件目录: ") and "单次等待上限" in lines[1]
    assert "取数通道: " in buf.getvalue()
    assert "-" * 92 in lines, "分隔线 = 92 连字符(数量与字符都不能变)"
    assert lines.count("-" * 92) >= 2
    assert any("视图:" in ln for ln in lines), "内存快照预览的视图行(不走 view=None 分支)"
    assert "考察中命中=2" in buf.getvalue(), "同一 v1 torrent 回填 v1/v2 双 hash, 视图按 hash 索引(单 hash 索引会被杀)"
    m = re.search(r"用时 (\d+(?:\.\d+)?)s", buf.getvalue())
    assert m and float(m.group(1)) < 60, "耗时是正的小量(now+started 会爆成巨大值)"
    assert "本次未写入任何文件" in buf.getvalue()
    assert "只能确认配置/路径/锁状态" not in buf.getvalue(), "有通道时不印无通道提示(isinstance 分支)"
    # 无离线目录且无通道: 两条提示都要在(撤销口罩通道还原 NullFetcher 场景)
    monkeypatch.undo()
    buf2 = io.StringIO()
    assert run_hr_once(_config(tmp_path), None, out=buf2) == 0
    assert buf2.getvalue().splitlines(
    )[-1] == ("提示: 未提供离线页面(--hr-html-dir), 且取数通道未启用 ⇒ 本轮只能确认配置/路径/锁状态。"), "无通道提示逐字(子串会被 XX 包首尾/小写改写放过)"


def test_run_hr_once_passes_html_dir_to_fetcher(tmp_path, monkeypatch):
    """--hr-html-dir 透传给取数通道构造(吞成 None 会静默退化成「无通道」走查)"""
    import auto_qb.hr.report as report_mod

    seen = []

    def spy(d):
        seen.append(d)
        return NullFetcher("spy")

    monkeypatch.setattr(report_mod, "build_fetcher", spy)
    cfg = _config(tmp_path)
    html_dir = str(tmp_path / "pages")
    assert run_hr_once(cfg, html_dir, out=io.StringIO()) == 0
    assert seen == [html_dir], "走查把离线目录原样传给 build_fetcher"


def test_run_hr_status_lines_exact(tmp_path):
    """现状输出面: 头两行/通道段落 buf/分隔线/收尾两条提示逐字/默认 limit 10"""
    _rows_seed(
        tmp_path,
        [row(101),
         row(102),
         row(103),
         row(104),
         row(105),
         row(106),
         row(107),
         row(108),
         row(109),
         row(110),
         row(111)]
    )
    cfg = _config(tmp_path, data_dir=tmp_path)
    buf = io.StringIO()
    assert run_hr_status(cfg, out=buf) == 0
    lines = buf.getvalue().splitlines()
    assert lines[0] == "HR 在线核实现状(只读: 不取数 / 不加锁 / 不写盘) 共 1 个站点: example"
    assert lines[1] == (f"站点文件目录: {tmp_path / 'hr'}(每站点一个 JSON; 多实例共享同一账号时需共用同一目录)")
    assert "取数通道: " in buf.getvalue(), "通道自检段落进报告(打去 stdout 会丢段)"
    assert lines.count("-" * 92) >= 2
    assert "最多显示 10 行" in buf.getvalue(), "默认 limit = 10(不是 11)"
    assert "还有 1 行未显示" in buf.getvalue()
    assert lines[-2] == "提示: 以上全部读自**已落盘数据**(原子替换, 读到的是完整的一份), 未触发任何取数。", \
        "收尾提示逐字(不是子串——XX 包首尾也会被 in 放过)"
    assert lines[-1] == "      要看「现在能不能取到数」跑 --hr-once; 要在线核实请让浏览器扩展保持开启。"
    assert not any("WARN:" in ln for ln in lines), "好文件不出 WARN 行(read_error 空占位会在这暴露)"


def _add_site(cfg, name: str) -> None:
    """给配置加第二个启用站点(多站点输出面用)"""
    cfg.trackers[name] = TrackerConfig(
        name=name,
        domains=[f"pt-{name}.example.com"],
        hr_check=SiteHrCheckConfig(
            enabled=True,
            tracker=name,
            hr_page_url=f"https://pt-{name}.example.com/myhr.php",
            download_path="/download.php?id={id}",
            page_param="page",
            listing="list",
            required_seeding_time=86400.0,
        ),
    )


def test_run_hr_status_multisite_join(tmp_path):
    """多站点: 站点表用 ', ' 连接(', ' 被换成别的分隔会被钉)"""
    _rows_seed(tmp_path, [row(101)])
    cfg = _config(tmp_path, data_dir=tmp_path)
    _add_site(cfg, "second")
    buf = io.StringIO()
    assert run_hr_status(cfg, out=buf) == 0
    assert buf.getvalue().splitlines()[0] == ("HR 在线核实现状(只读: 不取数 / 不加锁 / 不写盘) 共 2 个站点: example, second")


def test_run_hr_status_read_error_warn(tmp_path):
    """坏站点文件: read_error 原文进 WARN 行(空值回落 "" 不是占位文本)"""
    _rows_seed(tmp_path, [row(101)])
    cfg = _config(tmp_path, data_dir=tmp_path)
    (tmp_path / "hr" / f"{SITE}.json").write_text("{bad json", encoding="utf-8")
    buf = io.StringIO()
    assert run_hr_status(cfg, out=buf) == 0
    warn = [ln for ln in buf.getvalue().splitlines() if "WARN:" in ln]
    assert warn and warn[0].startswith("    文件: "), "读坏文件时出 WARN 行"
    assert "XXXX" not in buf.getvalue(), "read_error 空回落空串(占位文本会被 here 捕获)"


def test_run_hr_once_multisite_join(tmp_path):
    """走查多站点: 站点表同样 ', ' 连接"""
    cfg = _config(tmp_path)
    _add_site(cfg, "second")
    buf = io.StringIO()
    assert run_hr_once(cfg, None, out=buf) == 0
    assert buf.getvalue().splitlines()[0] == ("HR 在线核实走查(只读, 不写盘) 共 2 个站点: example, second")


def test_run_hr_confirm_empty_note_and_stamp(tmp_path):
    """对账: notes 累加不丢旧备注 + 事件 site 归属 + 打印戳与落盘值一致"""
    from auto_qb.hr.store import HrSiteStore
    from auto_qb.hr.status import stamp_text

    store = HrSiteStore(SITE, str(tmp_path / "hr"))
    with store.hold() as session:
        session.data.wave.notes = "旧备注"
        session.commit(time.time())
    cfg = _config(tmp_path, data_dir=tmp_path)
    buf = io.StringIO()
    assert run_hr_confirm_empty(cfg, [SITE], out=buf) == 0
    data, err = store.read_unlocked()
    assert data.wave.notes.startswith("旧备注"), "旧备注留在头部(新备注追加在后, 不是覆盖/前插)"
    assert "人工对账" in data.wave.notes and "确认账号 HR 清单为空" in data.wave.notes, "对账备注逐字追加"
    assert data.writer_heartbeat > 0, "写盘心跳是本次时刻(commit(None) 会落 null)"
    (ev, ) = data.history
    assert ev.kind == "confirm_empty" and ev.trigger == "confirm" and ev.action == "confirm-empty", "事件类型/触发/动作钉死(历史按站点文件归属, 无 site 字段)"
    assert ev.reason == "; 人工对账: 确认账号 HR 清单为空(--hr-confirm-empty), 零行波恢复签发放行, 非零行自动失效".strip("; ")
    text = buf.getvalue()
    assert f"[{SITE}] 已写入人工对账戳({stamp_text(data.empty_confirmed_at)})。" in text, "打印戳与落盘值同源"
    assert text.splitlines()[-1] == ("      之后结构完好的零行波可正常签发放行; 清单再现任何非零行时确认戳自动失效。"), "第二行提示逐字(子串会被 XX 包首尾放过)"


def test_run_hr_confirm_empty_disabled_hint(tmp_path):
    """总开关关闭: 明确提示「无需对账」并返回非 0(提示逐字)"""
    cfg = _config(tmp_path, enabled=False)
    buf = io.StringIO()
    assert run_hr_confirm_empty(cfg, [SITE], out=buf) == 1
    assert buf.getvalue().splitlines() == ["hr_check.enabled=false: HR 在线核实未启用, 无需对账。"]


def test_build_fetcher_null_message():
    """无通道提示逐字: 含配置键名(不静默降级为后端直连)"""
    fetcher = build_fetcher(None)
    assert isinstance(fetcher, NullFetcher)
    assert fetcher._reason == "本实例未启用取数通道 (hr_check.channel.enabled=false 或取数通道未落地)"


def test_local_page_fetcher_replaces_bad_bytes(tmp_path):
    """离线页面按 utf-8 + replace 读: 坏字节不抛(错误处理策略被掰掉会炸)"""
    page = tmp_path / "A.html"
    page.write_bytes(b"<html>\xff\xfe</html>")
    fetcher = LocalPageFetcher(str(tmp_path))
    text = fetcher.get_text("https://pt.example.com/myhr.php?hrtype=A")
    assert "<html>" in text and "</html>" in text, "坏字节被替换而不是抛错"
    assert fetcher.used == ["A.html"]
    try:
        fetcher.get_bytes("https://pt.example.com/download.php?id=1")
    except HrChannelUnavailable as e:
        assert str(e) == "离线走查不取 .torrent(无法回填 infohash); 在线核实请走浏览器扩展通道", "离线不取 .torrent 的提示逐字"
    else:  # pragma: no cover
        raise AssertionError("离线模式不应提供 .torrent")


def test_run_hr_confirm_empty_blank_notes(tmp_path):
    """notes 原本为空: 对账备注就是全部(空值回落占位文本会被 startswith 抓到)"""
    from auto_qb.hr.store import HrSiteStore

    store = HrSiteStore(SITE, str(tmp_path / "hr"))
    with store.hold() as session:
        session.commit(time.time())  # 不设 notes ⇒ 保持默认空
    cfg = _config(tmp_path, data_dir=tmp_path)
    assert run_hr_confirm_empty(cfg, [SITE], out=io.StringIO()) == 0
    data, _ = store.read_unlocked()
    assert data.wave.notes.startswith("人工对账: 确认账号 HR 清单为空"), "空 notes 时新备注即全部(无占位前缀)"


def test_print_status_site_lane_counts_missing_keys_fall_to_zero():
    """档位计数缺键回落 0: 某档位无条目时不能显示 None/空/1(按档诊断会误导)"""
    from auto_qb.hr.report import _print_status_site

    out = io.StringIO()
    _print_status_site(_st(lane_counts={"A": 1}), HrSiteData(), 10, out)
    assert "档位 A=1 B=0 C=0 D=0(免罪)" in out.getvalue(), "B/C/D 缺键回落 0(不是占位)"
    out2 = io.StringIO()
    _print_status_site(_st(lane_counts={}), HrSiteData(), 10, out2)
    assert "档位 A=0 B=0 C=0 D=0(免罪)" in out2.getvalue(), "A 也缺键时同样回落 0"


def test_status_rows_header_aligns_when_cell_wider():
    """数据比表头宽时表头仍按列方向铺(tid 7 位 > 「tid」3 格 ⇒ 表头右对齐前补位)"""
    from auto_qb.hr.report import _print_status_rows

    data = HrSiteData()
    data.index = {1234567: HrEntry(tid=1234567, name="x", lane="A")}
    out = io.StringIO()
    _print_status_rows(data, 10, out)
    header = next(ln for ln in out.getvalue().splitlines() if "infohash" in ln)
    assert header.startswith("        " + "    tid"), "tid 列宽撑到 7 ⇒ 表头右对齐补 4 空格(左对齐会变 8 前缀直连)"


# ---------- R20 续: _print_status_site 现状段(此前零守阵, 红验最大真洞群) ----------


def _st(**kw):
    """SiteStatus 全字段非默认构造(展示守阵源值)"""
    from auto_qb.hr.status import LaneStatus, QuotaStatus, SiteStatus

    base = dict(
        site=SITE,
        enabled=True,
        listing="list",
        now=1_700_000_000.0,
        channel_state="ok",
        channel_text="正常",
        revision=9,
        file_path="/d/hr/s.json",
        read_error="",
        fetched_at=1_699_999_940.0,
        healthy_ts=1_699_999_000.0,
        expires_at=1_700_000_100.0,
        next_wave_at=1_700_000_000.0,
        refresh_interval=3600.0,
        idle_mode=False,
        stale=False,
        fresh_text="取波文本",
        lanes=[
            LaneStatus(
                lane="A",
                status="ok",
                status_text="有效",
                lane_text="考察中",
                wave_ts=0.0,
                pages=3,
                rows=4,
                cutoff_done=0.0,
                full_depth=True,
                fail_streak=0,
                count_claim=None,
                count_match=None,
                detail="",
                text="A 有效: 3 页 / 4 行(全深度)",
            )
        ],
        lanes_text="A:[x]3页4行",
        releases_enabled=True,
        zero_rows=False,
        empty_confirmed=False,
        count_attested_empty=False,
        retention_text="守恒文本",
        notes="备注文本",
        writer_instance="w1",
        writer_heartbeat=0.0,
        index_total=4,
        index_active=3,
        lane_counts={
            "A": 2,
            "B": 1,
            "D": 1
        },
        pending_infohash=1,
        backfill_ratio=2 / 3,
        managed=1,
        keys=2,
        downloaded=1,
        fails=1,
        verified=1,
        observing=2,
        quota=QuotaStatus(
            day=7, day_max=100, left=93, last_fetch_ts=0.0, min_interval=2.0, next_reset=0.0, text="配额文本"
        ),
        allow_window="09:00-18:00",
        blocking="",
    )
    base.update(kw)
    return SiteStatus(**base)


def test_print_status_site_lines_exact():
    """现状段逐行: 头部四要素/文件/取波/各档+逐档明细/备注/守恒/数据两行/频控(无明细数据段的提示行)"""
    from auto_qb.hr.report import _print_status_site

    out = io.StringIO()
    _print_status_site(_st(), HrSiteData(), 10, out)
    lines = out.getvalue().splitlines()
    assert lines[0] == f"[{SITE}] 形态=list  通道=正常  数据版本=9  放行签发=开"
    assert lines[1] == "    文件: /d/hr/s.json"
    assert lines[2] == "    取波: 取波文本"
    assert lines[3] == "    各档: A:[x]3页4行"
    assert lines[4] == "      · A 有效: 3 页 / 4 行(全深度)"
    assert lines[5] == "    最近一波备注: 备注文本"
    assert lines[6] == "    守恒: 守恒文本"
    assert lines[7] == "    数据: 索引条目 4(活跃 3)  档位 A=2 B=1 C=0 D=1(免罪)  考察中命中 1 个(键 2 个)  观察期中 2 个"
    assert lines[8] == "    已取种子 1 条  取种子失败 1 条  待回填 infohash 1 条(进度 67%)  放行记录 1 条"
    assert lines[9] == "    频控: 配额文本  时间窗: 09:00-18:00"
    assert lines[10] == "    明细: (还没有数据 —— 先跑 --hr-once 或让扩展抓一波)"


def test_print_status_site_branches_and_placeholders():
    """分支与占位: 冻结/read_error WARN/blocking 行/零行三态/各档空/时间窗不限/备注空"""
    from auto_qb.hr.report import _print_status_site

    # 冻结 + WARN + blocking 行(顺序: 文件/取波/各档/明细行/备注/blocking/守恒/零行/数据/频控)
    st = _st(releases_enabled=False, read_error="坏 JSON", blocking="未到拉取时刻", zero_rows=True, empty_confirmed=True)
    out = io.StringIO()
    _print_status_site(st, HrSiteData(), 10, out)
    lines = out.getvalue().splitlines()
    assert lines[0] == f"[{SITE}] 形态=list  通道=正常  数据版本=9  放行签发=冻结"
    assert lines[1] == "    文件: /d/hr/s.json  WARN: 坏 JSON", "read_error 非空才追 WARN(不是恒显/占位)"
    assert "    现在为什么不签发放行: 未到拉取时刻" in lines
    assert "    零行: 本波清单为 0(已人工确认)" in lines
    # 零行另两态
    out2 = io.StringIO()
    _print_status_site(_st(zero_rows=True, count_attested_empty=True), HrSiteData(), 10, out2)
    assert "    零行: 本波清单为 0(计数自证空集, 无需人工确认)" in out2.getvalue().splitlines()
    out3 = io.StringIO()
    _print_status_site(_st(zero_rows=True), HrSiteData(), 10, out3)
    assert "    零行: 本波清单为 0(未确认 —— 零行波不签发放行)" in out3.getvalue().splitlines()
    # 各档空回落 "-" / 时间窗空回落 "不限" / 备注空不印
    out4 = io.StringIO()
    _print_status_site(_st(lanes_text="", lanes=[], allow_window="", notes=""), HrSiteData(), 10, out4)
    text4 = out4.getvalue()
    assert "    各档: -\n" in text4, "lanes_text 空回落 '-'(不是占位)"
    assert "    频控: 配额文本  时间窗: 不限" in text4.splitlines(), "时间窗空回落 '不限'(or 口径)"
    assert "最近一波备注" not in text4, "备注空不印该行"


def test_print_status_rows_empty_hint_exact():
    """明细空数据的提示行逐字(print 文案/None 文件/占位都被钉)"""
    from auto_qb.hr.report import _print_status_rows

    out = io.StringIO()
    _print_status_rows(HrSiteData(), 10, out)
    assert out.getvalue().splitlines() == ["    明细: (还没有数据 —— 先跑 --hr-once 或让扩展抓一波)"]
