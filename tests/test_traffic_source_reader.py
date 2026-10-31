"""test_traffic_source_reader 测试计划: 取数读取与失败判定单点(计划 26-10-18-0813 A2/A4)

> `core.traffic_source.reader.read_source_rows(dat_path)` 是「怎么读、读到什么算失败」的共享
> 单点(来源模块与曲线模块都调它, 模块间不许互 import)。此前零测试文件直接引用(仅被
> test_traffic_snapshot 经 refresh() 间接触达, 断言面粗), W7 轮变异审计前置(计划
> 26-10-31-0128 §02/D2)补定向守阵, 钉住直接契约: 返回三元组的形状、两条失败原因码
> (前端按码分流文案)与失败文案带路径。

## 测试计划(每个测试函数一条)
- test_read_source_rows_ok_parses_rows_and_counts_bad: 正常 dat -> (行, 坏行数, None), 坏行跳过且计数
- test_read_source_rows_missing_file_returns_dat_missing: 读不到文件(OSError) -> 空行 + dat_missing + 文案带路径
- test_read_source_rows_empty_returns_dat_empty: 有文件无有效记录 -> dat_empty + 坏行数透传(不是 0)
- test_read_source_rows_tolerates_non_utf8_bytes: errors="ignore" 容忍非 UTF-8 字节, 不抛异常
"""
from pathlib import Path

from auto_qb.core.traffic_source import reader


def _write(tmp_path: Path, text: str) -> str:
    p = tmp_path / "history_traffic.dat"
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_read_source_rows_ok_parses_rows_and_counts_bad(tmp_path):
    """正常 dat -> (按日行, 坏行数, None); 坏行跳过并计数, 有效行原样透传"""
    dat = _write(tmp_path, 'lines: "3"\n2026/11/01 10/20\nnot-a-date\n2026/11/02 1/2\n')
    rows, bad, fail = reader.read_source_rows(dat)
    assert fail is None
    assert bad == 1
    assert [(d.isoformat(), up, down) for d, up, down in rows] == [
        ("2026-11-01", 10 * 1024, 20 * 1024),
        ("2026-11-02", 1 * 1024, 2 * 1024),
    ]


def test_read_source_rows_missing_file_returns_dat_missing(tmp_path):
    """读不到文件(OSError) -> ([], 0, 失败), 原因码 dat_missing(前端契约), 文案带路径"""
    missing = str(tmp_path / "absent.dat")
    rows, bad, fail = reader.read_source_rows(missing)
    assert rows == [] and bad == 0
    assert fail["code"] == "dat_missing"
    assert fail["text"].startswith("流量数据读取失败")
    assert "No such file or directory" in fail["text"]
    assert missing in fail["log"]
    assert "读取流量数据失败" in fail["log"]


def test_read_source_rows_empty_returns_dat_empty(tmp_path):
    """有文件但无有效记录 -> dat_empty; 坏行数透传(不是 0), 文案带路径"""
    dat = _write(tmp_path, 'lines: "1"\nnot-a-date\n')
    rows, bad, fail = reader.read_source_rows(dat)
    assert rows == [] and bad == 1
    assert fail["code"] == "dat_empty"
    assert "流量数据无有效记录" in fail["text"]
    assert dat in fail["log"]


def test_read_source_rows_tolerates_non_utf8_bytes(tmp_path):
    """errors="ignore": 非 UTF-8 字节不炸读取(剥掉即可), 其余行照常解析"""
    p = tmp_path / "history_traffic.dat"
    p.write_bytes(b"\xff\xfe\xff\nlines: \"1\"\n2026/11/01 3/4\n")
    rows, bad, fail = reader.read_source_rows(str(p))
    assert fail is None and bad == 0
    assert len(rows) == 1
