"""test_traffic_store_incremental 测试计划: V4DayCache 天文件增量解析(F4-1, 计划 26-11-15-1104 S2-1)

## 测试计划(每个测试函数一条)
- test_incremental_append_chunks_bitwise_equivalent: 增量解析正确性主阵 —— 逐块追加 N 次
  (记录续块/新 B 行关块/注释空行/坏行/重复 key 行/无基线块混排), 每步结果与全量重解析
  逐位等价(V4ParsedDay 全字段); 续点链式等价(增量产出的 resume == 全量重解析的 resume,
  下一步续解锚点无漂移); 每步确走增量路径(resume= 非 None)
- test_incremental_size_shrink_and_same_size_full_reparse: R3 守卫 —— size 缩小(裁剪/重写)
  -> 全量重解析(resume=None); size 持平 mtime 变(同尺寸重写)-> 全量重解析; 结果均与
  全量重解析等价
- test_incremental_torn_tail_full_parse_and_repair: 撕裂尾两面 —— (a) 首读即撕裂(末行有效
  无换行 / 末行坏半行两形态): 结果与全量重解析等价(torn_tail 口径同源), 不产续点;
  (b) 撕裂后追加(写侧 repair 前缀 \\n)-> 全量重解析(无续点可续), 结果等价; (c) 增量段内
  再撕裂(追加半行)-> 结果等价 torn_tail=True, 再追加退全量仍等价
- test_incremental_probe_mismatch_falls_back_full: 前缀探针防伪 —— 非追加写(改前缀尾 64B
  内字节且 size 增大)使探针不符 -> 退全量重解析, 结果与全量重解析等价
- test_incremental_bad_header_never_resumes: 头行门闩失守(v3 旧头行整文件坏)不产续点
  (key=None 不可续), 追加后退全量重解析仍整文件坏 —— 续解不丢头行门闩语义
- test_incremental_oserror_last_good_entry_kept: OSError 两路(全量读/增量段读)上抛不落
  缓存不改条目(缓存面 last-good 保留, 端点面 §08 由 traffic_qb 兜底); 恢复后同条目
  续点仍可增量续解且结果等价
- test_incremental_empty_missing_and_first_appearance: 空文件/缺失缓存 None 哨兵(零解析),
  文件出现后全量解析, 再追加走增量 —— 首读/空态边界
- test_incremental_append_parse_ms_level: 实测 —— 4 万行(~1.2MB 文本)天文件追加 200 行
  的增量解析耗时 vs 全量重解析耗时(逐轮真实追加 5 轮取最小, 报告数字); 增量结果与全量
  重解析逐位等价
- test_incremental_v4_block_writer_path_roundtrip: 真实写侧路径(store.append_records 批量
  追加)下的增量等价 —— 跨 flush 同块续记录 + 新块头(计数器重置形态), 每步与全量重解析
  等价且恒走增量路径(只追加不变式的生产形态面)

线程/时钟纪律: 计时用 time.perf_counter(实测数字非断言精确值); 文件一律落在 tmp_path
(test.* 已内置 TMPDIR, 不手工加前缀); 代码/断言零 emoji 零图形符号。
"""
import os
import time

import auto_qb.core.traffic_store as traffic_store_module
import pytest

from auto_qb.core.traffic_store import (
    HEADER_LINE_V4,
    V4DayCache,
    V4DayResume,
    V4Sample,
    parse_v4_day_text,
    v4_day_file_path,
)

_DATE = "2026-11-15"


def _day_text(data_dir, key):
    with open(_day_path(data_dir, key), "rb") as f:
        return f.read().decode("utf-8", errors="replace")


def _write_day(data_dir, key, text):
    path = v4_day_file_path(data_dir, key, _DATE)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(text.encode("utf-8"))
    return path


def _append_day(data_dir, key, text):
    """写侧追加形态仿真(open("a") 追加字节)"""
    path = v4_day_file_path(data_dir, key, _DATE)
    with open(path, "ab") as f:
        f.write(text.encode("utf-8"))


def _day_path(data_dir, key):
    return v4_day_file_path(data_dir, key, _DATE)


def _oracle(data_dir, key, real_parse):
    """全量重解析谕示: 当前文件整读整解(与缓存读面同解码纪律)"""
    with open(_day_path(data_dir, key), "rb") as f:
        return real_parse(f.read().decode("utf-8", errors="replace"))


def _track_parse(monkeypatch):
    """解析调用形状跟踪: calls 每项 = 该次调用的 resume 实参(None = 全量 / V4DayResume = 增量)"""
    calls = []
    real_parse = traffic_store_module.parse_v4_day_text

    def counting_parse(t, **kwargs):
        calls.append(kwargs.get("resume"))
        return real_parse(t, **kwargs)

    monkeypatch.setattr(traffic_store_module, "parse_v4_day_text", counting_parse)
    return calls, real_parse


# 混排行集: 基线块续记录 / 新 B 行关块 / 注释空行 / 重复 key 行(记坏) / 无基线块 n-only /
# 无基线块 r 行(记坏) / 杂行(记坏) / 形态 D z 行 / 带 dt r 行
_LINES = [
    HEADER_LINE_V4,
    "key,global",
    "B,1000,2,10,20",
    "r,100,50,0,0",
    "r,110,51,100,50",
    "r,120,52,200,100,50",
    "z,3,300,150,360,180,200",
    "n,2",
    "",
    "# comment line",
    "B,2000,2,500,600",
    "r,130,53,50,60",
    "r,140,54,150,160,80",
    "key,global",
    "B,3000,2",
    "n,3",
    "n,4,120",
    "r,150,55,300,200",
    "junk,line,here",
    "B,4000,2,1000,2000",
    "r,170,57,10,20",
    "z,2,1030,2030,1090,2090,500",
    "n,5,250",
]


def _chunk_text(lines):
    return "\n".join(lines) + "\n"


def test_incremental_append_chunks_bitwise_equivalent(tmp_path, monkeypatch):
    """逐块追加 4 次(5 块混排), 每步与全量重解析逐位等价 + 续点链式等价 + 恒走增量路径"""
    data_dir = str(tmp_path)
    calls, real_parse = _track_parse(monkeypatch)
    chunks = [_LINES[0:6], _LINES[6:12], _LINES[12:17], _LINES[17:20], _LINES[20:]]
    _write_day(data_dir, "global", _chunk_text(chunks[0]))
    cache = V4DayCache(data_dir)
    p0 = cache.read_day("global", _DATE)
    assert p0 == real_parse(_chunk_text(chunks[0]))
    assert calls == [None]  # 首读全量
    full_text = _chunk_text(chunks[0])
    for i, chunk in enumerate(chunks[1:], start=1):
        _append_day(data_dir, "global", _chunk_text(chunk))
        full_text += _chunk_text(chunk)
        calls.clear()
        got = cache.read_day("global", _DATE)
        expect = real_parse(full_text)
        assert got == expect, f"chunk {i}: 增量结果须与全量重解析逐位等价"
        assert all(c is not None for c in calls) and calls, f"chunk {i}: 恒走增量路径(resume= 非 None)"
        # 续点链式等价: 增量产出的续点 == 全量重解析产出的续点(下一步续解锚点无漂移)
        _, cp_full = real_parse(full_text, with_resume=True)
        assert cache._entries[("global", _DATE)].resume == cp_full
        assert isinstance(cp_full, V4DayResume)


def test_incremental_size_shrink_and_same_size_full_reparse(tmp_path, monkeypatch):
    """R3 守卫: size 缩小(裁剪/重写)-> 全量重解析; size 持平 mtime 变 -> 全量重解析"""
    data_dir = str(tmp_path)
    calls, real_parse = _track_parse(monkeypatch)
    small = _chunk_text(_LINES[:12])
    big = _chunk_text(_LINES)
    _write_day(data_dir, "global", small)
    cache = V4DayCache(data_dir)
    cache.read_day("global", _DATE)
    _write_day(data_dir, "global", big)  # 先变大: 走增量
    got = cache.read_day("global", _DATE)
    assert got == real_parse(big)
    assert calls[-1] is not None  # 增量路径
    # size 缩小(裁剪/重写形态) -> 全量重解析(R3 钉路径)
    calls.clear()
    _write_day(data_dir, "global", small)
    got = cache.read_day("global", _DATE)
    assert got == real_parse(small)
    assert calls == [None], "size 缩小必须整文件全量重解析"
    # size 持平但内容变(同尺寸重写, mtime 变)-> 全量重解析
    same_size = small[:-2] + "9\n"  # 末行改一位数字: 尺寸持平
    assert len(same_size.encode("utf-8")) == len(small.encode("utf-8"))
    calls.clear()
    _write_day(data_dir, "global", same_size)
    got = cache.read_day("global", _DATE)
    assert got == real_parse(same_size)
    assert calls == [None], "size 持平(mtime 变)必须全量重解析"


def test_incremental_torn_tail_full_parse_and_repair(tmp_path, monkeypatch):
    """撕裂尾两面: 首读撕裂(有效无换行/坏半行)等价且不产续点; repair 追加退全量; 增量段内再撕裂"""
    data_dir = str(tmp_path)
    calls, real_parse = _track_parse(monkeypatch)
    body = _chunk_text(_LINES[:-1])
    # 形态 1: 末行有效但无换行(崩溃恰在写完整行后)—— torn_tail=False 但无续点(非整行收尾)
    torn_valid = body + _LINES[-1]
    _write_day(data_dir, "global", torn_valid)
    cache = V4DayCache(data_dir)
    got = cache.read_day("global", _DATE)
    assert got == real_parse(torn_valid) and got.torn_tail is False
    assert cache._entries[("global", _DATE)].resume is None, "非整行收尾不产续点"
    # repair 追加(写侧前缀 \n + 新行)-> 无续点可续: 全量重解析, 结果等价
    calls.clear()
    _append_day(data_dir, "global", "\n" + _chunk_text(["B,5000,2,2000,3000", "r,180,58,20,30"]))
    full_now = torn_valid + "\nB,5000,2,2000,3000\nr,180,58,20,30\n"
    got = cache.read_day("global", _DATE)
    assert got == real_parse(full_now)
    assert calls == [None], "撕裂尾续点缺失 -> 追加退全量重解析"
    # 形态 2: 末行坏半行(torn_tail=True 豁免口径)
    torn_bad = body + "r,9,9,"
    _write_day(data_dir, "global", torn_bad)
    calls.clear()
    got = cache.read_day("global", _DATE)
    assert got == real_parse(torn_bad) and got.torn_tail is True
    assert cache._entries[("global", _DATE)].resume is None
    # 增量段内再撕裂: 干净读(产续点)后追加半行(4 列 r = 真半行, 5 列是完整合法行)
    _write_day(data_dir, "global", _chunk_text(_LINES[:12]))
    calls.clear()
    cache.read_day("global", _DATE)
    assert calls == [None]
    _append_day(data_dir, "global", "r,180,58,2")  # 半行(无换行, 列数不足 = 坏)
    torn_seg = _chunk_text(_LINES[:12]) + "r,180,58,2"
    got = cache.read_day("global", _DATE)
    assert got == real_parse(torn_seg) and got.torn_tail is True
    assert calls[-1] is not None, "有续点时半行追加走增量路径(结果与全量重解析等价)"
    assert cache._entries[("global", _DATE)].resume is None, "段内撕裂不产新续点"
    # 再追加(repair)-> 退全量仍等价
    _append_day(data_dir, "global", "\n" + _chunk_text(["r,190,59,30,40"]))
    full_seg = torn_seg + "\nr,190,59,30,40\n"
    got = cache.read_day("global", _DATE)
    assert got == real_parse(full_seg)


def test_incremental_probe_mismatch_falls_back_full(tmp_path, monkeypatch):
    """前缀探针防伪: 非追加写(前缀尾 64B 内字节被改且 size 增大)-> 探针不符退全量重解析"""
    data_dir = str(tmp_path)
    calls, real_parse = _track_parse(monkeypatch)
    base = _chunk_text(_LINES)
    _write_day(data_dir, "global", base)
    cache = V4DayCache(data_dir)
    cache.read_day("global", _DATE)
    # 非追加写: 改前缀内字节(探针覆盖末 64B)且追加新行(size 增大)
    tampered = base.replace("r,170,57,10,20", "r,170,57,10,29") + _chunk_text(["r,180,58,20,30"])
    assert tampered.encode("utf-8")[:len(base.encode("utf-8")) - 64] == base.encode("utf-8")[:-64]
    _write_day(data_dir, "global", tampered)
    calls.clear()
    got = cache.read_day("global", _DATE)
    assert got == real_parse(tampered)
    assert calls == [None], "探针不符(非追加写)必须退全量重解析"


def test_incremental_bad_header_never_resumes(tmp_path, monkeypatch):
    """头行门闩失守(v3 旧头行整文件坏)不产续点(key=None); 追加退全量仍整文件坏 —— 续解不丢门闩"""
    data_dir = str(tmp_path)
    calls, real_parse = _track_parse(monkeypatch)
    old = _chunk_text(_LINES[:6]).replace(HEADER_LINE_V4, "# auto-qb qb-traffic v3", 1)
    _write_day(data_dir, "global", old)
    cache = V4DayCache(data_dir)
    got = cache.read_day("global", _DATE)
    expect = real_parse(old)
    assert got == expect and got.key is None and got.bad_lines == got.data_lines > 0
    assert cache._entries[("global", _DATE)].resume is None, "头行失守(key=None)不产续点"
    _append_day(data_dir, "global", _chunk_text(["r,1,1,1,1"]))
    calls.clear()
    got = cache.read_day("global", _DATE)
    assert got == real_parse(old + "r,1,1,1,1\n")
    assert got.key is None and got.bad_lines == got.data_lines
    assert calls == [None], "头行失守文件追加必须退全量重解析(门闩语义不续解)"


def test_incremental_oserror_last_good_entry_kept(tmp_path, monkeypatch):
    """OSError 两路上抛不落缓存不改条目(缓存面 last-good 保留); 恢复后同条目续点仍可增量"""
    data_dir = str(tmp_path)
    calls, real_parse = _track_parse(monkeypatch)
    _write_day(data_dir, "global", _chunk_text(_LINES[:12]))
    cache = V4DayCache(data_dir)
    good = cache.read_day("global", _DATE)
    assert good is not None

    # 增量段读路 OSError: 上抛 + 条目不动(先追加强制 stat 失效走增量路)
    def boom_seg(path, prev):
        raise OSError(5, "io error")

    real_seg = traffic_store_module.V4DayCache._read_append_segment
    monkeypatch.setattr(traffic_store_module.V4DayCache, "_read_append_segment", staticmethod(boom_seg))
    _append_day(data_dir, "global", _chunk_text(_LINES[12:17]))
    with pytest.raises(OSError):
        cache.read_day("global", _DATE)
    monkeypatch.setattr(traffic_store_module.V4DayCache, "_read_append_segment", staticmethod(real_seg))
    assert cache._entries[("global", _DATE)].parsed is good, "OSError 后条目原样保留(last-good)"
    got = cache.read_day("global", _DATE)
    assert got == real_parse(_chunk_text(_LINES[:17]))
    assert calls[-1] is not None, "恢复后同条目续点仍走增量"

    # 全量读路 OSError(size 缩小强制走全量): 同样上抛 + 条目不动
    def boom_read(path):
        raise OSError(5, "io error")

    real_read = traffic_store_module._read_day_bytes
    monkeypatch.setattr(traffic_store_module, "_read_day_bytes", boom_read)
    _write_day(data_dir, "global", _chunk_text(_LINES[:6]))  # size 缩小: 全量路
    with pytest.raises(OSError):
        cache.read_day("global", _DATE)
    monkeypatch.setattr(traffic_store_module, "_read_day_bytes", real_read)  # 恢复读路
    assert cache._entries[("global", _DATE)].parsed is got, "全量路 OSError 后条目原样保留"
    got2 = cache.read_day("global", _DATE)
    assert got2 == real_parse(_chunk_text(_LINES[:6]))
    assert calls[-1] is None, "恢复后 size 缩小路走全量重解析"


def test_incremental_empty_missing_and_first_appearance(tmp_path, monkeypatch):
    """缺失/空文件缓存 None 哨兵零解析; 文件出现全量解析; 再追加走增量(首读/空态边界)"""
    data_dir = str(tmp_path)
    calls, real_parse = _track_parse(monkeypatch)
    cache = V4DayCache(data_dir)
    assert cache.read_day("global", _DATE) is None
    _write_day(data_dir, "global", "")
    assert cache.read_day("global", _DATE) is None
    assert calls == [], "缺失/空文件零解析(哨兵缓存)"
    _write_day(data_dir, "global", _chunk_text(_LINES[:6]))
    got = cache.read_day("global", _DATE)
    assert got == real_parse(_chunk_text(_LINES[:6]))
    assert calls == [None]
    _append_day(data_dir, "global", _chunk_text(_LINES[6:12]))
    assert cache.read_day("global", _DATE) == real_parse(_chunk_text(_LINES[:12]))
    assert calls[-1] is not None


def test_incremental_append_parse_ms_level(tmp_path, monkeypatch):
    """实测: 大天文件(~1.2MB 文本, 4 万 r 行)追加 200 行的增量解析耗时 vs 全量重解析耗时
    (逐轮真实追加, 5 轮取最小 —— 每轮文件都增长, 两路都强制走真路径); 增量结果与全量
    重解析逐位等价"""
    data_dir = str(tmp_path)
    calls, real_parse = _track_parse(monkeypatch)
    base_lines = [HEADER_LINE_V4, "key,global", "B,1000,2,0,0"]
    base_lines += [f"r,{i},{2 * i},{i},{2 * i}" for i in range(40000)]
    _write_day(data_dir, "global", _chunk_text(base_lines))
    cache = V4DayCache(data_dir)
    cache.read_day("global", _DATE)  # 基线全量解析(暖机)
    inc_best = full_best = float("inf")
    got_inc = got_full = None
    round_base = 40000
    for rnd in range(5):
        inc_lines = [
            f"r,{round_base + i},{2 * (round_base + i)},{round_base + i},{2 * (round_base + i)}" for i in range(200)
        ]
        _append_day(data_dir, "global", _chunk_text(inc_lines))
        round_base += 200
        t0 = time.perf_counter()
        got_inc = cache.read_day("global", _DATE)
        inc_best = min(inc_best, time.perf_counter() - t0)
        # 强制全量: 新缓存实例冷读同一文件(整读整解)
        t0 = time.perf_counter()
        got_full = V4DayCache(data_dir).read_day("global", _DATE)
        full_best = min(full_best, time.perf_counter() - t0)
        assert got_inc == got_full
    inc_ms = inc_best * 1000.0
    full_ms = full_best * 1000.0
    final_text = _day_text(data_dir, "global")
    print(
        f"\n[incremental timing] 天文件 {len(final_text.encode('utf-8'))} B / "
        f"{final_text.count(chr(10))} 行, 追加 200 行增量解析 {inc_ms:.2f} ms "
        f"vs 全量重解析 {full_ms:.2f} ms (倍率 {full_ms / max(inc_ms, 1e-9):.0f}x)"
    )
    assert calls[0] is None and calls[1] is not None, "计时轮增量路走增量路径(resume= 非 None)"
    assert calls[2] is None, "计时轮全量路走全量重解析(resume=None)"
    assert inc_best < full_best, "增量解析必须快于全量重解析"
    assert real_parse(final_text) == got_inc


def test_incremental_v4_block_writer_path_roundtrip(tmp_path, monkeypatch):
    """真实写侧路径(store.append_records 批量追加)下的增量等价: 跨 flush 同块续记录 + 新块头,
    每步与全量重解析等价 —— 只追加不变式的生产形态面"""
    data_dir = str(tmp_path)
    calls, real_parse = _track_parse(monkeypatch)
    st = traffic_store_module.TrafficV4Store(data_dir)
    cache = V4DayCache(data_dir)
    st.append_records("global", _DATE, (1000, 2.0), (V4Sample(100, 50, 10, 20), ), (10, 20))
    expect = real_parse(_chunk_text([
        HEADER_LINE_V4,
        "key,global",
        "B,1000,2,10,20",
        "r,100,50,0,0",
    ]))
    assert cache.read_day("global", _DATE) == expect
    # 同块续记录(跨 flush, header=None)
    st.append_records("global", _DATE, None, (V4Sample(110, 51, 110, 70), ), (10, 20))
    got = cache.read_day("global", _DATE)
    assert got == real_parse(
        _chunk_text([
            HEADER_LINE_V4,
            "key,global",
            "B,1000,2,10,20",
            "r,100,50,0,0",
            "r,110,51,100,50",
        ])
    )
    assert calls[-1] is not None
    # 新块(计数器重置形态: 新基线)
    st.append_records("global", _DATE, (2000, 2.0), (V4Sample(5, 3, 500, 600), ), (500, 600))
    got = cache.read_day("global", _DATE)
    assert got == real_parse(
        _chunk_text(
            [
                HEADER_LINE_V4,
                "key,global",
                "B,1000,2,10,20",
                "r,100,50,0,0",
                "r,110,51,100,50",
                "B,2000,2,500,600",
                "r,5,3,0,0",
            ]
        )
    )
    assert got.key == "global" and len(got.blocks) == 2
    assert all(c is not None for c in calls[1:]), "写侧追加恒走增量路径"
