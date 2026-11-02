"""test_hr_report_once 测试计划: --hr-once 只读走查 / --hr-status 现状报告(均不进主循环、不写盘、不连 qB)

## 测试计划(每个测试函数一条)
- test_build_fetcher_without_dir_is_null: 未给离线目录 -> NullFetcher(不静默直连站点)
- test_local_page_fetcher_reads_scope_files: 离线页面替身按 <档位>.html 提供各档首屏
- test_local_page_fetcher_missing_and_bytes: 缺文件报「无通道」语义; 离线不取 .torrent
- test_run_hr_once_hints_when_disabled: 总开关关闭 -> 明确提示并返回非 0
- test_run_hr_once_hints_when_no_site: 无站点配置 hr_check -> 明确提示并返回非 0
- test_run_hr_once_reports_without_writing: 走查出报告(含站点文件路径与锁自检), 且**不写任何文件**
- test_run_hr_once_null_channel_reports_hint: 无离线目录且通道未启用 -> 如实报「无可用取数通道」并给出提示

### P1 覆盖率提升轮: 报告层长尾
- test_confirm_empty_disabled_reports_hint: 确认戳在总开关关闭时明确提示非 0
- test_confirm_empty_readonly_and_lock_busy: 只读退化与锁占用各自的提示 + 非 0
- test_confirm_empty_records_history_event: 对账动作入拉取历史(计划 26-10-04-0312 §3.3)——
  恰一条 confirm_empty 事件(trigger=confirm / action=confirm-empty)随既有 commit 落盘
- test_print_channel_lists_shared_dir_when_configured: 配了共享目录时明示

### R20 展示导出变异守阵(issue 26-10-10-1108-test-hr-mutation-display, 排序口径/宽字符对齐/人话回落)
- test_run_hr_once_force_bypasses_interval_gate: force=True 绕过拉取间隔闸(走查本义)
- test_run_hr_once_view_line_and_separators: 走查输出面(视图行/分隔线/站点表 join/提示/耗时量纲)
- test_run_hr_confirm_empty_note_and_stamp: 对账 notes 累加不丢旧备注 + 事件 site + 打印戳与落盘一致
- test_build_fetcher_null_message: 无通道提示逐字(含配置键名, 不静默降级)
- test_local_page_fetcher_replaces_bad_bytes: 离线页面按 utf-8/replace 读(坏字节不抛)
- test_run_hr_confirm_empty_blank_notes
- test_run_hr_confirm_empty_disabled_hint
- test_run_hr_confirm_empty_stamps_site
- test_run_hr_once_multisite_join
- test_run_hr_once_passes_html_dir_to_fetcher
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

from auto_qb.hr.store import HrSiteStore

from hr_helpers import EMPTY_TABLE_PAGE, FakeFetcher, global_conf, make_service, myhr_page, row, site_conf, torrent_blob

from hr_report_support import (
    SITE,
    _add_site,
    _config,
    _rows_seed,
    _seed,
)


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


def test_print_channel_lists_shared_dir_when_configured(tmp_path):
    """配了 shared_dir: 通道自检段明示共享目录(多实例共用同一份数据)"""
    from auto_qb.hr.report import _print_channel

    cfg = _config(tmp_path)
    cfg.hr_check.shared_dir = "R:/Shared/hr"
    service = make_service(
        tmp_path, NullFetcher("x"), now_fn=time.time, site_confs={SITE: site_conf()}, gconf=cfg.hr_check, persist=False
    )
    out = io.StringIO()
    _print_channel(cfg, service, out)
    assert "R:/Shared/hr" in out.getvalue() and "多实例共用" in out.getvalue()


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
