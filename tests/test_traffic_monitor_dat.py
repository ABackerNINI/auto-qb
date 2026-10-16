"""test_traffic_monitor_dat 测试计划: 工具写者 x auto-qb dat_path 读侧的 dat 跨侧契约(计划 26-10-16-0541 S9)

守 S9 清单最后一项「dat_path 指向工具文件时解析兼容」。两侧各自的格式守阵都有盲面:
工具侧 tests/test_storage.py 的 curves oracle 在「工具独立部署」时跳过, auto-qb 侧
tests/test_traffic_monitor_client.py 的样本是手搭的 TM 文本 —— 两侧按同一种错法漂移
(单位口径一起动 / 表头换形状)时两份守阵都保持绿; 只有本文件钉住「工具真写者产出的字节 ->
auto-qb 真读侧(dat_path -> 历史行)」这条链路。

工具写者按源码路径加载(根环境刻意没有 psutil, 是 S0 的隔离判据; 而写者路径 DatStore.render /
DAT_ROW_RE / atomic_write_text 一次都不用 psutil, 只替掉那一个 import); 也不起子进程 ——
根测试的副作用守阵只放行 node 与临时 wrapper(POPEN 白名单), 跨 venv 跑工具是它的越界面。

## 测试计划(每个测试函数一条)
- test_tool_written_dat_round_trips_through_dat_path: 工具真写者原子落盘的 dat 设为 dat_path ->
  只读刷新读回: 历史行按日升序、KB 向下取整后的字节值逐日一致、day/month 周期累计重算正确
  (更早月份的行不进当月累计)
- test_dat_format_single_points_agree: 格式单点两侧同值 —— 单位常量(工具 KB == curves.KB)、
  表头形状(lines: "N" 且 N == 数据行数)、行序(新日在前)、整份产出经 curves.parse_history_dat
  解析 bad == 0(表头若不再被读侧跳过, 只有这里会红: 值断言抓不到这一层)
"""
import importlib
import sys
import types
from datetime import date, timedelta
from pathlib import Path

import pytest

from auto_qb.config import GlobalSpeedLimitCurve, PeriodCurve
from auto_qb.core import curves
from helpers import make_manager

# 工具包源码(单仓内与 auto-qb 同源): 缺失即仓库缺陷, 用具名断言点出而不是 skip 掩盖
TOOL_SRC = Path(__file__).resolve().parents[1] / "tools" / "global-traffic-monitor" / "src"

KB = 1024
MIB = 1024**2
# 表头形状(TM 兼容): 首行 lines: "N", N 为数据行数 —— 读侧只按 "lines:" 前缀整行跳过
DAT_HEADER = 'lines: "{n}"'


@pytest.fixture()
def gtm_writer(monkeypatch):
    """工具包真写者模块 gtm.storage(写者路径不碰 psutil, 只替那一个 import)"""
    assert (TOOL_SRC / "gtm" / "storage.py").is_file(), f"工具包源码缺失(单仓内与 auto-qb 同源): {TOOL_SRC}"
    if "psutil" not in sys.modules:
        # 只替 import 不替行为: 写者若真用到 psutil, 本用例会以 AttributeError 立刻变红(不静默)
        monkeypatch.setitem(sys.modules, "psutil", types.ModuleType("psutil"))
    monkeypatch.syspath_prepend(str(TOOL_SRC))
    return importlib.import_module("gtm.storage")


def _pc(period: str) -> PeriodCurve:
    """一条曲线: 本文件只用 period(只读刷新按它重算累计), 档位表留空"""
    return PeriodCurve(period=period)


def _floor_kb(up_bytes: int, down_bytes: int) -> tuple:
    """工具落盘口径(整数 KB 向下取整) + 读侧还原(KB*1024)的独立期望值 —— 不借工具自己算"""
    return (up_bytes // KB) * KB, (down_bytes // KB) * KB


def _write_tool_dat(gtm_writer, path: Path, rows: dict) -> None:
    """用工具真写者落一份 dat: DatStore.load/upsert -> flush(临时文件 + fsync + os.replace)"""
    store = gtm_writer.DatStore(str(path))
    store.load()
    for day, (up_bytes, down_bytes) in rows.items():
        store.upsert(day, up_bytes, down_bytes)
    store.flush()


def _dat_path_env(tmp_path, dat_path: Path):
    """auto-qb 侧环境: dat_path 指向工具产出文件, 曲线启用(day/month 两条)"""
    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.config.global_speed_limit_curve = GlobalSpeedLimitCurve(
        dat_path=str(dat_path), curves=[_pc("day"), _pc("month")], enabled=True
    )
    mgr.web.traffic_view = {
        "state": "ok",
        "periods": [],
        "history": [],
        "ts": 1.0,
        "date": "1970-01-01",
        "limit": {
            "target": {
                "up": 1,
                "down": 2
            },
            "actual": {
                "up": 1,
                "down": 2
            },
            "reasons": [],
        },
    }
    return mgr


def test_tool_written_dat_round_trips_through_dat_path(gtm_writer, tmp_path):
    """工具产出的 dat 指向 dat_path -> 只读刷新读回真值(KB 取整还原 + 升序历史行 + 周期累计)"""
    today = date.today()
    raw = {
        today: (3 * MIB + 512, 5 * MIB + 1023),  # 余数印证「宁可少报」: 读回必须是取整后的值
        today - timedelta(days=1): (1 * MIB + 3000, 7 * MIB + 1),
        today - timedelta(days=40): (2 * MIB + 99999, 9 * MIB + 12345),  # 恒在更早的月份(>= 32 天前)
    }
    dat_path = tmp_path / "gtm" / "history_traffic.dat"
    _write_tool_dat(gtm_writer, dat_path, raw)

    mgr = _dat_path_env(tmp_path, dat_path)
    assert mgr.host.get("speed_curve").refresh_traffic_view() is True, "dat_path 指向工具文件时刷新必须发布"
    view = mgr.web.traffic_view

    expected = {day: _floor_kb(*vals) for day, vals in raw.items()}
    assert view["history"] == [
        {
            "date": day.isoformat(),
            "up": up,
            "down": down
        } for day, (up, down) in sorted(expected.items())
    ], "历史行必须按日升序原样读回(工具 KB 取整口径)"
    in_month = [v for day, v in expected.items() if (day.year, day.month) == (today.year, today.month)]
    assert [(p["period"], p["up"], p["down"]) for p in view["periods"]] == [
        ("day", *expected[today]),
        ("month", sum(u for u, _d in in_month), sum(d for _u, d in in_month)),
    ], "day/month 周期累计必须按工具产出重算(非当月的旧行只进历史行、不进当月累计)"


def test_dat_format_single_points_agree(gtm_writer, tmp_path):
    """格式单点同值: 单位常量 / 表头形状 / 行序 / 读侧坏行计数 —— 契约漂移的第一道红"""
    assert gtm_writer.KB == curves.KB == KB, "单位常量两侧必须同值(KB = 1024)"

    today = date.today()
    rows = {today: (1 * MIB + 512, 2 * MIB + 1024), today - timedelta(days=1): (3 * MIB, 4 * MIB + 1)}
    dat_path = tmp_path / "gtm" / "history_traffic.dat"
    _write_tool_dat(gtm_writer, dat_path, rows)

    text = dat_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines[0] == DAT_HEADER.format(n=len(rows)), f"首行必须是 TM 兼容表头: {lines[0]!r}"
    assert len(lines) == len(rows) + 1, "表头 + 数据行, 不多不少"
    stamp = [ln.split()[0] for ln in lines[1:]]
    assert stamp == sorted(stamp, reverse=True), "TM 口径: 新日在前(表形状, 与读侧行序不敏感互补)"

    parsed, bad = curves.parse_history_dat(text)
    assert bad == 0, "工具产出的每一行都必须被读侧解析(表头被算作坏行时这里先红)"
    assert parsed == sorted((day, *_floor_kb(*vals)) for day, vals in rows.items())
