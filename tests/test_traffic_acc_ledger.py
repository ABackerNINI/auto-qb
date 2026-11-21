"""test_traffic_acc_ledger 测试计划: acc 快照账本核心(plan 26-11-21-1546 S2 第一步 —— 账本读写组件 + 单测, 零接线)

## 测试计划(每个测试函数一条)
- test_acc_ledger_append_bootstrap_and_batch: 追加面 —— 文件不存在建头行(版本头行门闩首行)/
  批量多系列行一次 open 落盘 / 二批追加续尾 / 空批零操作不建件; 行文本 = format_acc_row 逐列定约
- test_acc_ledger_append_repairs_torn_tail: 尾字节查补(镜像 _ensure_file_prefix 先例)—— 崩溃残留
  半行(无换行)后追加不与残行合并(查补换行), 残行成独立坏行被读侧丢弃, 该系列回落上一有效行
- test_acc_ledger_last_wins: last-wins(§03.4 与 agg.dat「同 epoch 取末行」同款)—— 同 key 重复行
  读侧取最后一行, 他系列不受牵连
- test_acc_ledger_read_missing_and_empty: 回退矩阵之一 —— 账本缺失/空文件 = 整本无效
  (header_ok=False + 空 snapshots, 调用方全体 fallback; 升级首启常态)
- test_acc_ledger_header_latch_family: 回退矩阵之二 —— 版本头行门闩族(v2 未来头行 / 旧 v4 天文件
  头行 / 无头行 / 纯空白)全部整本无效(全部行计坏含头行, snapshots 空); 合法头行下空行注释行跳过不计坏
- test_acc_ledger_corrupt_and_torn_tail_matrix: 回退矩阵之三 —— 单行损坏按系列隔离(中段坏行他系列
  不放大 / 仅坏行系列无快照走 fallback / 尾行解析失败用次末行 = last-wins 自然回落)/ 撕裂尾两形态
  (物理截断无换行 = torn_tail 标记 + 末行丢弃; 完整但不可解析 = 同单行损坏)/ 恰好完整但缺尾换行的
  末行照常消费(torn 标记不误标)/ 尾部多余列严格记坏
- test_acc_ledger_compaction_trigger_idempotent_equivalent: 压实(D8)—— 超(注桩的)阈值单次重写:
  整本 last-wins 折叠成每系列单行(key 升序)+ 内容等价(重写前后 snapshots 逐系列相等)/ 幂等
  (同内容再压实字节级不变)/ 恢复默认阈值后未到阈值零写(黄金法则 1)/ 重写自洁坏行
- test_acc_ledger_compaction_refuses_latch_failure_and_missing: 压实守门 —— 文件缺失/空 = False;
  头行门闩失守不重写(陌生格式原样留存, 字节级不变)
- test_acc_ledger_fingerprint_probe_family: 指纹探针(D9 两级)—— 纯函数 (size, mtime_ns) 全等判据
  (任一列不同即失配)/ stat 采样真实 agg.dat / 匹配 / 追加+mtime 变化失配 / 缺失 = 失配(OSError
  按缺失语义)/ 写侧采样缺失 = (0, 0) 哨兵
- test_acc_ledger_roundtrip_random_corpus: 无损 roundtrip(单测钉)—— 随机语料(固定种子: 12 系列 x
  随机 pending 桶数与浮点 fold / open_credit / day/month 开放层 / 已关层存根 / earliest / 游标含
  亚秒 / 全空状态), 纯函数级(拼文本->解析)与文件级(append->read)双向, AccSnapshot 逐字段深度相等;
  二批演化追加后 last-wins 视图正确
- test_acc_ledger_cursor_fingerprint_semantics: 游标与指纹字段语义钉(R3)—— 游标 = 累计器已入账到的
  最后槽位(浮点秒, 亚秒精度无损往返)/ None(尚无入账)往返 / 指纹二元组原样随行往返(探针输入面)
- test_acc_ledger_writer_fail_fast: 写侧 fail-fast —— 段位 kind 不符(day_hours 塞 day 行)/ epoch 空列带行(day/month)/ 非法系列键
  (含逗号形态/未知前缀)/ 解析侧 pending hour epoch 重复记坏
- test_acc_ledger_state_field_parity_static: 静态守阵 —— AccSeriesState 与 SeriesAgg 字段名字+顺序
  全对齐(增删字段即红, 强制同步镜像与行格式)/ AccHourFoldState 与 HourFold 字段+默认值对齐 /
  落点钉: acc.dat 根级(v4_root_dir 直下, 旧版系列键扫描不见, 回滚降级零影响)
- test_acc_ledger_read_logging_honest: 读侧留痕如实(DEBUG/INFO 分级)—— 缺失 INFO / 门闩失守 INFO /
  非撕裂坏行 INFO / 纯撕裂尾只 DEBUG(不产坏行 INFO 噪音)
"""
import logging
import os
import random

import pytest

from auto_qb.core import traffic_store_acc_ledger as acc_ledger_mod
from auto_qb.core.modules.traffic_sample_common import HourFold, SeriesAgg
from auto_qb.core.traffic_store import HEADER_LINE_V4
from auto_qb.core.traffic_store_acc_ledger import (
    ACC_LEDGER_HEADER_V1,
    AccHourFoldState,
    AccSeriesState,
    AccSnapshot,
    agg_fingerprint_matches,
    append_acc_snapshots,
    compact_acc_ledger,
    format_acc_row,
    parse_acc_ledger_text,
    probe_agg_fingerprint,
    read_acc_ledger,
    stat_agg_fingerprint,
)
from auto_qb.core.traffic_store_codec import AggRow
from auto_qb.core.traffic_store_paths import v4_acc_ledger_path, v4_agg_file_path, v4_series_dir

_LEDGER_LOGGER = "auto_qb.core.traffic_store_acc_ledger"

# ---------- 语料构造助手 ----------


def _row(kind: str, epoch: int, cov_s: int = 3600) -> AggRow:
    """确定性 AggRow(kind 段位合法)"""
    return AggRow(
        kind=kind,
        epoch=epoch,
        dl_avg=100 + epoch % 7,
        dl_max=200 + epoch % 5,
        up_avg=50 + epoch % 3,
        up_max=80 + epoch % 11,
        dl_total=100000 + epoch,
        up_total=50000 + epoch,
        cov_s=cov_s,
    )


def _fold(dl_wsum: float, up_wsum: float, cov: float, credits: int = 10) -> AccHourFoldState:
    return AccHourFoldState(
        dl_wsum=dl_wsum,
        up_wsum=up_wsum,
        cov=cov,
        dl_max=1200,
        up_max=340,
        dl_total=777000,
        up_total=222000,
        credits=credits,
    )


def _rnd_row(rnd: random.Random, kind: str, epoch: int) -> AggRow:
    cov_hi = 3600 if kind == "hour" else 86400
    return AggRow(
        kind=kind,
        epoch=epoch,
        dl_avg=rnd.randrange(0, 10**9),
        dl_max=rnd.randrange(0, 10**9),
        up_avg=rnd.randrange(0, 10**9),
        up_max=rnd.randrange(0, 10**9),
        dl_total=rnd.randrange(0, 10**12),
        up_total=rnd.randrange(0, 10**12),
        cov_s=rnd.randrange(1, cov_hi),
    )


def _rnd_state(rnd: random.Random, base: int) -> AccSeriesState:
    """随机 SeriesAgg 形态折叠态(覆盖全部持久化字段的有/无组合)"""
    st = AccSeriesState()
    for i in range(rnd.randrange(0, 4)):
        st.pending[base + 3600 * i] = AccHourFoldState(
            dl_wsum=rnd.uniform(0, 10**9),
            up_wsum=rnd.uniform(0, 10**9),
            cov=rnd.uniform(0.001, 3600),
            dl_max=rnd.randrange(0, 10**7),
            up_max=rnd.randrange(0, 10**7),
            dl_total=rnd.randrange(0, 10**12),
            up_total=rnd.randrange(0, 10**12),
            credits=rnd.randrange(1, 5000),
        )
    if rnd.random() < 0.5:
        st.open_credit = (
            base + rnd.random(),
            rnd.randrange(0, 10**7),
            rnd.randrange(0, 10**7),
            rnd.randrange(0, 10**12),
            rnd.randrange(0, 10**12),
        )
    if rnd.random() < 0.7:
        st.day_epoch = base - 3600
        st.day_hours = [_rnd_row(rnd, "hour", base - 7200 + 3600 * i) for i in range(rnd.randrange(1, 5))]
    if rnd.random() < 0.5:
        st.month_epoch = base - 86400 * 20
        st.month_days = [_rnd_row(rnd, "day", base - 86400 * (i + 1)) for i in range(rnd.randrange(1, 4))]
    if rnd.random() < 0.4:
        st.closed_day = (
            base - 86400,
            [_rnd_row(rnd, "hour", base - 86400 + 3600 * i) for i in range(rnd.randrange(1, 3))],
        )
    if rnd.random() < 0.3:
        st.closed_month = (
            base - 86400 * 50,
            [_rnd_row(rnd, "day", base - 86400 * (i + 1)) for i in range(rnd.randrange(1, 3))],
        )
    if rnd.random() < 0.8:
        st.earliest_hour = base - rnd.randrange(0, 100) * 3600
    return st


def _rnd_corpus(rnd: random.Random) -> list:
    """随机系列语料: global + 11 个 infohash 形态单种系列(其中一个恒全空状态)"""
    keys = ["global"] + [f"torrent:{i:040x}" for i in range(1, 12)]
    snaps = []
    for idx, key in enumerate(keys):
        base = 1732262400 + idx * 86400
        if idx == 11:
            state = AccSeriesState()  # 全空状态(新装系列 flush 前的终态行形态)
            cursor = None
        else:
            state = _rnd_state(rnd, base)
            cursor = base + rnd.random() if rnd.random() < 0.8 else None
        snaps.append(
            AccSnapshot(
                key=key, cursor=cursor, agg_fingerprint=(rnd.randrange(0, 2**40), rnd.randrange(0, 2**40)), state=state
            )
        )
    return snaps


def _write_raw(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _read_raw(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _snap(key: str, cursor, fp=(1, 2), state=None) -> AccSnapshot:
    return AccSnapshot(
        key=key, cursor=cursor, agg_fingerprint=fp, state=state if state is not None else AccSeriesState()
    )


# ---------- 追加面 ----------


def test_acc_ledger_append_bootstrap_and_batch(tmp_path):
    data_dir = str(tmp_path)
    append_acc_snapshots(data_dir, [])  # 空批零操作
    assert not os.path.exists(v4_acc_ledger_path(data_dir))  # 不建件(惰性)
    s1 = _snap("global", 100.0, (11, 22), AccSeriesState(earliest_hour=90, pending={3600: _fold(1.5, 2.5, 3.5)}))
    s2 = _snap("torrent:ab12", 200.0, (33, 44), AccSeriesState(day_epoch=0, day_hours=[_row("hour", 0)]))
    append_acc_snapshots(data_dir, [s1, s2])
    path = v4_acc_ledger_path(data_dir)
    lines = _read_raw(path).splitlines()
    assert lines[0] == ACC_LEDGER_HEADER_V1  # 版本头行门闩首行
    assert len(lines) == 3
    assert lines[1] == format_acc_row(s1)
    assert lines[2] == format_acc_row(s2)
    append_acc_snapshots(data_dir, [_snap("global", 300.0)])  # 二批续尾
    lines = _read_raw(path).splitlines()
    assert len(lines) == 4
    res = read_acc_ledger(data_dir)
    assert res.header_ok and set(res.snapshots) == {"global", "torrent:ab12"}


def test_acc_ledger_append_repairs_torn_tail(tmp_path):
    data_dir = str(tmp_path)
    append_acc_snapshots(data_dir, [_snap("global", 100.0)])
    path = v4_acc_ledger_path(data_dir)
    with open(path, "ab") as f:
        f.write(b"A,global,17")  # 崩溃残留半行(无换行)
    append_acc_snapshots(data_dir, [_snap("torrent:ab12", 200.0)])  # 查补换行后续写
    lines = _read_raw(path).splitlines()
    assert "A,global,17" in lines  # 残行自成独立行(不与新行合并)
    res = parse_acc_ledger_text(_read_raw(path))
    assert res.header_ok and res.bad_lines == 1 and not res.torn_tail  # 查补后残行 = 完整坏行
    assert res.snapshots["global"].cursor == 100.0  # 该系列回落上一有效行
    assert res.snapshots["torrent:ab12"].cursor == 200.0


def test_acc_ledger_last_wins(tmp_path):
    data_dir = str(tmp_path)
    st_v1 = AccSeriesState(earliest_hour=10, pending={3600: _fold(1.0, 1.0, 1.0)})
    st_v2 = AccSeriesState(earliest_hour=20, pending={7200: _fold(2.0, 3.0, 4.0)}, open_credit=(99.5, 1, 2, 3, 4))
    append_acc_snapshots(data_dir, [_snap("global", 100.0, state=st_v1)])
    append_acc_snapshots(data_dir, [_snap("global", 200.0, (7, 8), st_v2), _snap("torrent:cd34", 300.0)])
    res = read_acc_ledger(data_dir)
    assert res.snapshots["global"] == _snap("global", 200.0, (7, 8), st_v2)  # 末行胜
    assert res.snapshots["global"].state.open_credit == (99.5, 1, 2, 3, 4)
    assert res.snapshots["torrent:cd34"].cursor == 300.0  # 他系列不受牵连


# ---------- 回退矩阵 ----------


def test_acc_ledger_read_missing_and_empty(tmp_path, caplog):
    data_dir = str(tmp_path)
    with caplog.at_level(logging.INFO, logger=_LEDGER_LOGGER):
        res = read_acc_ledger(data_dir)
    assert res.header_ok is False and res.snapshots == {} and res.bad_lines == 0
    assert any("账本缺失" in r.message for r in caplog.records)  # 升级首启常态留痕
    _write_raw(v4_acc_ledger_path(data_dir), "")  # 空文件同判
    res = read_acc_ledger(data_dir)
    assert res.header_ok is False and res.snapshots == {}


def test_acc_ledger_header_latch_family(tmp_path):
    path = str(v4_acc_ledger_path(str(tmp_path)))
    body = format_acc_row(_snap("global", 100.0))
    # 门闩族: 未来版本头行 / 旧 v4 天文件头行 / 无头行 / 纯空白 —— 全部整本无效
    for head in ("# auto-qb qb-traffic-acc v2", HEADER_LINE_V4, "garbage", ""):
        _write_raw(path, (head + "\n" + body + "\n") if head else body + "\n")
        res = parse_acc_ledger_text(_read_raw(path))
        assert res.header_ok is False and res.snapshots == {}
        assert res.bad_lines == res.data_lines  # 全部行计坏(含头行, 同 _parse_v4_text 口径)
    _write_raw(path, "\n\n")  # 纯空白文件
    res = parse_acc_ledger_text(_read_raw(path))
    assert res.header_ok is False and res.snapshots == {}
    # 合法头行下空行/注释行跳过不计坏(data_lines 只数头行后的受检行 = 4)
    _write_raw(path, ACC_LEDGER_HEADER_V1 + "\n\n# 注释\n" + body + "\n\n")
    res = parse_acc_ledger_text(_read_raw(path))
    assert res.header_ok and res.bad_lines == 0 and res.data_lines == 4
    assert res.snapshots["global"].cursor == 100.0


def test_acc_ledger_corrupt_and_torn_tail_matrix(tmp_path):
    path = str(v4_acc_ledger_path(str(tmp_path)))
    good_a1 = format_acc_row(_snap("global", 100.0, state=AccSeriesState(earliest_hour=10)))
    good_a2 = format_acc_row(_snap("global", 200.0, state=AccSeriesState(earliest_hour=20)))
    good_b = format_acc_row(_snap("torrent:ab12", 300.0))
    # 中段坏行: 该系列用次末有效行, 他系列不放大
    _write_raw(
        path, ACC_LEDGER_HEADER_V1 + "\n" + good_a1 + "\nA,global,notafloat,1,2\n" + good_a2 + "\n" + good_b + "\n"
    )
    res = parse_acc_ledger_text(_read_raw(path))
    assert res.header_ok and res.bad_lines == 1 and not res.torn_tail
    assert res.snapshots["global"].cursor == 200.0
    assert res.snapshots["torrent:ab12"].cursor == 300.0
    # 仅一行且坏: 该系列无快照(调用方按系列 fallback), 不崩不放大
    _write_raw(path, ACC_LEDGER_HEADER_V1 + "\nA,global,notafloat,1,2\n")
    res = parse_acc_ledger_text(_read_raw(path))
    assert res.header_ok and res.bad_lines == 1 and res.snapshots == {}
    # 撕裂尾形态一(物理截断, 无换行): 末行丢弃, 有上一有效行则回落, torn_tail 如实标记
    _write_raw(path, ACC_LEDGER_HEADER_V1 + "\n" + good_a1 + "\n" + good_b + "\nA,global,17")
    res = parse_acc_ledger_text(_read_raw(path))
    assert res.torn_tail is True and res.bad_lines == 1
    assert res.snapshots["global"].cursor == 100.0 and res.snapshots["torrent:ab12"].cursor == 300.0
    _write_raw(path, ACC_LEDGER_HEADER_V1 + "\n" + good_a1 + "\nA,torrent:zz,1")  # 无上一有效行
    res = parse_acc_ledger_text(_read_raw(path))
    assert res.torn_tail is True and "torrent:zz" not in res.snapshots and res.snapshots["global"].cursor == 100.0
    # 撕裂尾形态二(完整但不可解析, 有换行): 同单行损坏, 用次末行, 不误标 torn
    _write_raw(path, ACC_LEDGER_HEADER_V1 + "\n" + good_a1 + "\n" + good_a2 + "\nA,global,xyz\n")
    res = parse_acc_ledger_text(_read_raw(path))
    assert res.torn_tail is False and res.bad_lines == 1 and res.snapshots["global"].cursor == 200.0
    # 恰好完整但缺尾换行的末行照常消费(torn 物理态不误标 —— 末行解析成功)
    _write_raw(path, ACC_LEDGER_HEADER_V1 + "\n" + good_a2)
    res = parse_acc_ledger_text(_read_raw(path))
    assert res.torn_tail is False and res.snapshots["global"].cursor == 200.0
    # 尾部多余列严格记坏(免费校验)
    _write_raw(path, ACC_LEDGER_HEADER_V1 + "\n" + good_a2 + ",junk\n")
    res = parse_acc_ledger_text(_read_raw(path))
    assert res.bad_lines == 1 and res.snapshots == {}


# ---------- 压实(D8) ----------


def test_acc_ledger_compaction_trigger_idempotent_equivalent(tmp_path, monkeypatch):
    data_dir = str(tmp_path)
    monkeypatch.setattr(acc_ledger_mod, "ACC_LEDGER_COMPACT_BYTES", 10)  # 注桩小阈值必触发
    st_v1 = AccSeriesState(earliest_hour=10, pending={3600: _fold(1.0, 1.0, 1.0)})
    st_v2 = AccSeriesState(earliest_hour=20, day_epoch=0, day_hours=[_row("hour", 0)])
    append_acc_snapshots(data_dir, [_snap("torrent:ab12", 100.0, state=st_v1)])
    append_acc_snapshots(data_dir, [_snap("torrent:ab12", 200.0, state=st_v2), _snap("global", 300.0)])
    before = read_acc_ledger(data_dir)
    path = v4_acc_ledger_path(data_dir)
    assert compact_acc_ledger(data_dir) is True
    after = read_acc_ledger(data_dir)
    assert after.snapshots == before.snapshots  # 内容等价(last-wins 折叠无损)
    lines = _read_raw(path).splitlines()
    assert len(lines) == 3  # 头行 + 每系列单行
    assert lines[1].split(",")[1] == "global" and lines[2].split(",")[1] == "torrent:ab12"  # key 升序
    data1 = open(path, "rb").read()
    assert compact_acc_ledger(data_dir) is True  # 仍超小阈值 -> 再重写
    assert open(path, "rb").read() == data1  # 幂等: 已折叠内容字节级不变
    monkeypatch.setattr(acc_ledger_mod, "ACC_LEDGER_COMPACT_BYTES", 16 * 1024 * 1024)
    assert compact_acc_ledger(data_dir) is False  # 未到阈值零写(黄金法则 1)
    assert open(path, "rb").read() == data1


def test_acc_ledger_compaction_refuses_latch_failure_and_missing(tmp_path, monkeypatch):
    data_dir = str(tmp_path)
    monkeypatch.setattr(acc_ledger_mod, "ACC_LEDGER_COMPACT_BYTES", 10)  # 注桩小阈值越过尺寸闸
    assert compact_acc_ledger(data_dir) is False  # 缺失零写
    assert compact_acc_ledger(str(tmp_path / "nope")) is False
    path = v4_acc_ledger_path(data_dir)
    body = format_acc_row(_snap("global", 100.0))
    _write_raw(path, "# auto-qb qb-traffic-acc v2\n" + body + "\n")
    raw = open(path, "rb").read()
    assert compact_acc_ledger(data_dir) is False  # 门闩失守不代清场
    assert open(path, "rb").read() == raw  # 陌生格式原样留存


# ---------- 指纹探针(D9) ----------


def test_acc_ledger_fingerprint_probe_family(tmp_path):
    # 纯函数级: (size, mtime_ns) 全等判据, 任一列不同即失配
    assert agg_fingerprint_matches((5, 100), 5, 100) is True
    assert agg_fingerprint_matches((0, 0), 0, 0) is True  # 缺失哨兵自等
    assert agg_fingerprint_matches((5, 100), 6, 100) is False
    assert agg_fingerprint_matches((5, 100), 5, 101) is False
    # 探针级: 真实 agg.dat stat 采样 -> 匹配 / 追加+mtime 变化 -> 失配 / 缺失 -> 失配
    data_dir = str(tmp_path)
    os.makedirs(v4_series_dir(data_dir, "global"))
    agg = v4_agg_file_path(data_dir, "global")
    with open(agg, "w", encoding="utf-8", newline="\n") as f:
        f.write(HEADER_LINE_V4 + "\nkey,global\nhour,100,1,2,3,4,5,6,3600\n")
    os.utime(agg, ns=(1000, 1234567800))  # NTFS mtime 粒度 100ns, 取倍数保证 stat 回读等值
    fp = stat_agg_fingerprint(data_dir, "global")
    assert fp == (os.path.getsize(agg), 1234567800)
    assert probe_agg_fingerprint(data_dir, "global", fp) is True
    with open(agg, "a", encoding="utf-8", newline="\n") as f:
        f.write("hour,200,1,2,3,4,5,6,3600\n")
    os.utime(agg, ns=(1000, 9876543200))
    assert probe_agg_fingerprint(data_dir, "global", fp) is False  # 追加必失配
    os.remove(agg)
    assert probe_agg_fingerprint(data_dir, "global", fp) is False  # 缺失 = 失配语义
    assert stat_agg_fingerprint(data_dir, "global") == (0, 0)  # 写侧缺失哨兵


# ---------- 无损 roundtrip 与字段语义 ----------


def test_acc_ledger_roundtrip_random_corpus(tmp_path):
    rnd = random.Random(1546)
    snaps = _rnd_corpus(rnd)
    # 纯函数级: 头行 + 逐行文本 -> 解析, AccSnapshot 逐字段深度相等(浮点 repr 无损)
    text = ACC_LEDGER_HEADER_V1 + "\n" + "\n".join(format_acc_row(s) for s in snaps) + "\n"
    res = parse_acc_ledger_text(text)
    assert res.header_ok and res.bad_lines == 0 and not res.torn_tail
    assert res.snapshots == {s.key: s for s in snaps}
    # 文件级: append -> read 同等
    data_dir = str(tmp_path)
    append_acc_snapshots(data_dir, snaps)
    res = read_acc_ledger(data_dir)
    assert res.snapshots == {s.key: s for s in snaps}
    # 二批演化: 一半系列出终态新行, last-wins 视图 = 新状态, 其余不变
    evolved = {}
    for s in snaps[:6]:
        new_state = _rnd_state(rnd, 1740000000)
        evolved[s.key] = AccSnapshot(key=s.key, cursor=1740000000.5, agg_fingerprint=(7, 9), state=new_state)
    append_acc_snapshots(data_dir, [evolved[k] for k in evolved])
    res = read_acc_ledger(data_dir)
    expect = {s.key: s for s in snaps}
    expect.update(evolved)
    assert res.snapshots == expect


def test_acc_ledger_cursor_fingerprint_semantics(tmp_path):
    # 游标 = 累计器已入账到的最后槽位(浮点秒): 亚秒精度无损往返(R3 两向语义的比对基准)
    cursor = 1732262400 + 0.123456789
    snap = _snap("global", cursor, (123, 456), AccSeriesState(earliest_hour=1732258800))
    res = parse_acc_ledger_text(ACC_LEDGER_HEADER_V1 + "\n" + format_acc_row(snap) + "\n")
    got = res.snapshots["global"]
    assert got.cursor == cursor and isinstance(got.cursor, float)
    assert got.agg_fingerprint == (123, 456)  # 指纹二元组原样随行往返(探针输入面)
    assert got.state.earliest_hour == 1732258800
    # None(尚无入账)往返
    res = parse_acc_ledger_text(ACC_LEDGER_HEADER_V1 + "\n" + format_acc_row(_snap("global", None)) + "\n")
    assert res.snapshots["global"].cursor is None


def test_acc_ledger_writer_fail_fast():
    # 段位 kind 不符 fail-fast(防错段序列化静默改行型)
    bad_state = AccSeriesState(day_epoch=0, day_hours=[_row("day", 0)])
    with pytest.raises(ValueError):
        format_acc_row(_snap("global", None, state=bad_state))
    bad_month = AccSeriesState(month_epoch=0, month_days=[_row("hour", 0)])
    with pytest.raises(ValueError):
        format_acc_row(_snap("global", None, state=bad_month))
    # epoch 空列的段不得携带行(与读侧免费校验同判据对称 —— 防转换层拷贝 bug 静默写出坏行型)
    with pytest.raises(ValueError):
        format_acc_row(_snap("global", None, state=AccSeriesState(day_epoch=None, day_hours=[_row("hour", 0)])))
    with pytest.raises(ValueError):
        format_acc_row(_snap("global", None, state=AccSeriesState(month_epoch=None, month_days=[_row("day", 0)])))
    # 非法系列键 fail-fast(键字符集保证无逗号, 行格式不被注入)
    for key in ("global/x", "torrent:", "torrent:bad hash!", "unknown", "torrent:哈希"):
        with pytest.raises(ValueError):
            format_acc_row(_snap(key, None))
    # 解析侧 pending hour epoch 重复记坏(确定性破坏检测: 同 epoch 桶第二段插在 credit 段前 + 计数 +1)
    row = format_acc_row(_snap("global", 1.0, state=AccSeriesState(pending={3600: _fold(1.0, 1.0, 1.0)})))
    parts = row.split(",")
    i = parts.index("3600")  # 首个 3600 = pending 桶 epoch(前置列不含该值)
    n_idx = i - 1  # n_pending 列
    injected = parts[:n_idx] + [str(int(parts[n_idx]) + 1)] + parts[n_idx + 1:i + 9] + parts[i:i + 9] + parts[i + 9:]
    res = parse_acc_ledger_text(ACC_LEDGER_HEADER_V1 + "\n" + ",".join(injected) + "\n")
    assert res.bad_lines == 1 and res.snapshots == {}


# ---------- 静态守阵与留痕分级 ----------


def test_acc_ledger_state_field_parity_static():
    from dataclasses import fields

    # AccSeriesState 与 SeriesAgg 字段名字+顺序全对齐(SeriesAgg 增删字段即红 -> 强制同步镜像与行格式)
    assert [f.name for f in fields(SeriesAgg)] == [f.name for f in fields(AccSeriesState)]
    # AccHourFoldState 与 HourFold 字段+默认值对齐(浮点/整数默认值口径 = repr/nn 列判据的依据)
    hf, ahf = fields(HourFold), fields(AccHourFoldState)
    assert [f.name for f in hf] == [f.name for f in ahf]
    assert [f.default for f in hf] == [f.default for f in ahf]
    # 落点钉: acc.dat 在 v4 根级直下(旧版系列键扫描只看 global//torrents/ 两级, 回滚降级零影响)
    assert os.path.basename(v4_acc_ledger_path("d")) == "acc.dat"
    from auto_qb.core.traffic_store_paths import v4_root_dir

    assert os.path.dirname(v4_acc_ledger_path("d")) == v4_root_dir("d")


def test_acc_ledger_read_logging_honest(tmp_path, caplog):
    data_dir = str(tmp_path)
    path = v4_acc_ledger_path(data_dir)
    with caplog.at_level(logging.DEBUG, logger=_LEDGER_LOGGER):
        caplog.clear()
        read_acc_ledger(data_dir)  # 缺失 -> INFO
        assert any(r.levelno == logging.INFO and "账本缺失" in r.message for r in caplog.records)
        caplog.clear()
        _write_raw(path, "# auto-qb qb-traffic-acc v2\nA,global,1\n")
        read_acc_ledger(data_dir)  # 门闩失守 -> INFO
        assert any(r.levelno == logging.INFO and "门闩失守" in r.message for r in caplog.records)
        caplog.clear()
        good = format_acc_row(_snap("global", 100.0))
        _write_raw(path, ACC_LEDGER_HEADER_V1 + "\nA,global,badfloat\n" + good + "\n")
        read_acc_ledger(data_dir)  # 非撕裂坏行 -> INFO
        assert any(r.levelno == logging.INFO and "损坏行" in r.message for r in caplog.records)
        caplog.clear()
        _write_raw(path, ACC_LEDGER_HEADER_V1 + "\n" + good + "\nA,global,17")  # 纯撕裂尾
        read_acc_ledger(data_dir)  # 撕裂尾只 DEBUG(不产坏行 INFO 噪音)
        assert any(r.levelno == logging.DEBUG and "撕裂尾" in r.message for r in caplog.records)
        assert not any(r.levelno == logging.INFO and "损坏行" in r.message for r in caplog.records)
