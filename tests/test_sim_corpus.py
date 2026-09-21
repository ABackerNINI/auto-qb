"""test_sim_corpus 测试计划: 语料回放(scripts/sim_fsmock.py · scripts/sim_qb.py 的语料侧)

范围: 语料计划 26-09-21-0024 的 W3 —— FS mock / 窗口合并语义 / piece hash 派生 / 语料加载与配置派生。
不连 qB、不起服务、不写仓库外文件。

## 测试计划(每个测试函数一条)
- test_fsmock_intercepts_corpus_paths: 语料树内的路径走表(三态), 树外原样委托真函数
- test_fsmock_long_path_prefix_and_case: 剥 \\\\?\\ 前缀 + 大小写不敏感(NTFS 语义) —— 不这么做会把存在的文件报成缺失
- test_fsmock_unknown_path_in_scope_is_missing: 命中语料树但表里没有 -> 报"不存在"并计数(暴露探测不完整, 不伪装成真缺失)
- test_fsmock_disk_usage_uses_recorded_free_space: shutil.disk_usage 回录制到的可用空间(不是回放机的)
- test_fs_mock_coverage_static_guard: **静态守阵** —— 语料相关的 FS 探测点必须仍是被 mock 覆盖的那三个函数
- test_fs_mock_coverage_red_on_pathlib: **红验** —— 把探测换成 pathlib/os.stat, 守阵必须变红(否则是空壳)
- test_merge_window_net_effects: 窗口内先增后删 => 不吐该 hash; 先删后加 => 净额是"加"(计划 §08)
- test_merge_window_server_state_is_merge: server_state 是 merge 不是 replace(与 store.py:111-118 同款)
- test_piece_hashes_shared_by_content_set: 同(相对路径+大小)集合 => 同列表(严格模式判据不恒假); 不同集合 => 不同
- test_resolve_fsroot_placeholder: <FSROOT> 占位符解析, 且不写死任何真实路径
- test_corpus_source_loads_and_rejects_aborted: 语料加载; status=aborted 的语料必须拒绝回放
- test_corpus_tracker_section_picks_specific_tag: 站点标签取"对该 host 最专有"的, 不被通用标签抢走
"""
from __future__ import annotations

import gzip
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "scripts"))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, _REPO / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


fsmock = _load("sim_fsmock")
simqb = _load("sim_qb")


# --------------------------------------------------------------------------- FS mock
def test_fsmock_intercepts_corpus_paths():
    root = r"X:\corpus-fs"
    table = {
        r"X:\corpus-fs\d0\a\movie.mkv": {
            "exists": True,
            "size": 1234
        },
        r"X:\corpus-fs\d0\a\gone.mkv": {
            "exists": False,
            "size": None
        },
    }
    m = fsmock.FsMock(root, table)
    assert m.exists(r"X:\corpus-fs\d0\a\movie.mkv") is True
    assert m.getsize(r"X:\corpus-fs\d0\a\movie.mkv") == 1234
    assert m.exists(r"X:\corpus-fs\d0\a\gone.mkv") is False
    with pytest.raises(FileNotFoundError):
        m.getsize(r"X:\corpus-fs\d0\a\gone.mkv")
    # 树外: 原样委托真函数(绝不能 mock 到 config.yml / state.json / WEB 密钥)
    assert m.in_scope(r"C:\Users\x\config.yml") is False
    assert m.delegated >= 0


def test_fsmock_long_path_prefix_and_case():
    """传进来的是 add_long_path_prefix_for_win 的产物(\\\\?\\D:\\…), 且 NTFS 不区分大小写。

    若按原样精确匹配, 会把**存在**的文件报成缺失 => D4 判据全假(最坏的一种失败)。
    """
    root = r"X:\corpus-fs"
    table = {r"X:\corpus-fs\d0\A\Movie.MKV": {"exists": True, "size": 7}}
    m = fsmock.FsMock(root, table)
    assert m.exists(r"\\?\X:\corpus-fs\d0\A\Movie.MKV") is True, "必须剥 \\\\?\\ 前缀"
    assert m.exists(r"x:\CORPUS-FS\d0\a\movie.mkv") is True, "必须大小写不敏感"
    assert m.exists(r"X:/corpus-fs/d0/a/movie.mkv") is True, "分隔符必须归一"


def test_fsmock_unknown_path_in_scope_is_missing():
    """语料树内但表里没有 -> 报"不存在", 同时**计数**暴露出来(不把探测不完整伪装成真缺失)"""
    m = fsmock.FsMock(r"X:\corpus-fs", {})
    assert m.exists(r"X:\corpus-fs\d0\never-probed.mkv") is False
    assert m.misses == 1
    assert m.stats()["misses"] == 1


def test_fsmock_disk_usage_uses_recorded_free_space():
    """free_space_on_disk 必须回**录制到的真机值**, 不是回放机的剩余空间"""
    m = fsmock.FsMock(r"X:\corpus-fs", {}, free_space=18_474_057_728, total_space=70 * 1024**3)
    du = m.disk_usage(r"X:\corpus-fs\d0")
    assert du.free == 18_474_057_728
    assert du.total == 70 * 1024**3
    assert du.used == du.total - du.free


# ---- 静态守阵: 计划 §09 CORPUS.fs_mock_coverage(必须做红绿双验) ----
# 语料相关的 FS 探测点必须是**被 mock 覆盖的那三个函数**; 换成 pathlib / os.stat 会让 mock 静默失效
# => 判据变假绿(最坏的一种失败)。故这里把"期望的探测点"钉死。
_EXPECTED_PROBES = {
    "mixins/grouping.py": {
        "os.path.exists": 1,
        "os.path.getsize": 1
    },
    "mixins/checking.py": {
        "os.path.exists": 1,
        "os.path.getsize": 1
    },
    "rules/expr/env.py": {
        "os.path.exists": 1,
        "shutil.disk_usage": 3
    },
}
# 不被 mock 覆盖的探测写法: 出现在上述文件里即视为守阵失败
_UNMOCKED_PATTERNS = ("os.stat(", "Path(", "pathlib", ".is_file(", ".is_dir(")


def scan_fs_probes(src_root: Path) -> dict:
    """扫语料相关的 FS 探测点 -> {相对文件: {函数: 次数}}; 同时返回违规写法"""
    found: dict = {}
    violations: list[str] = []
    for rel in _EXPECTED_PROBES:
        p = src_root / "auto_qb" / rel
        if not p.is_file():
            violations.append(f"{rel}: 文件不存在")
            continue
        text = p.read_text(encoding="utf-8")
        counts = {}
        for fn in ("os.path.exists", "os.path.getsize", "shutil.disk_usage"):
            n = text.count(fn + "(")
            if n:
                counts[fn] = n
        found[rel] = counts
        for pat in _UNMOCKED_PATTERNS:
            if pat in text:
                violations.append(f"{rel}: 出现未被 mock 覆盖的探测写法 {pat!r}")
    return {"found": found, "violations": violations}


def test_fs_mock_coverage_static_guard():
    """**静态守阵**: 语料相关 FS 探测点 ⊆ mock 覆盖集(计划 §09 CORPUS.fs_mock_coverage)"""
    res = scan_fs_probes(_REPO / "src")
    assert not res["violations"], f"出现 mock 不覆盖的 FS 探测写法: {res['violations']}"
    assert res["found"] == _EXPECTED_PROBES, (
        f"FS 探测点与 mock 覆盖集不一致(增删探测点必须同步更新 sim_fsmock 的覆盖说明):\n"
        f"  实际 {res['found']}\n  期望 {_EXPECTED_PROBES}"
    )


def test_fs_mock_coverage_red_on_pathlib(tmp_path):
    """**红验**: 把探测换成 pathlib / os.stat, 守阵必须变红 —— 否则它守不住任何东西"""
    for rel in _EXPECTED_PROBES:
        p = tmp_path / "auto_qb" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        # 先给一份"正确"的, 确认扫描器本身是绿的
        p.write_text(
            "import os, shutil\n"
            "os.path.exists('x')\nos.path.getsize('x')\nshutil.disk_usage('x')\n",
            encoding="utf-8"
        )
    # 正确形态: 只有 shutil.disk_usage 次数不匹配会红, 这里先只看 violations
    assert not scan_fs_probes(tmp_path)["violations"]
    # 换成 pathlib: 必须被 violations 抓住
    (tmp_path / "auto_qb" / "mixins" /
     "grouping.py").write_text("from pathlib import Path\nPath('x').exists()\n", encoding="utf-8")
    res = scan_fs_probes(tmp_path)
    assert res["violations"], "换成 pathlib 后守阵必须变红(否则 mock 静默失效 => 假绿)"


# --------------------------------------------------------------------------- 窗口合并
def test_merge_window_net_effects():
    """窗口内先增后删 => 不吐该 hash; 先删后加 => 净额是"加"(计划 §08, 与 store 语义对齐)"""
    frames = [
        {
            "torrents": {
                "A": {
                    "state": "stalledUP"
                },
                "B": {
                    "state": "stalledUP"
                }
            },
            "torrents_removed": []
        },
        {
            "torrents": {
                "A": {
                    "upspeed": 5
                }
            },
            "torrents_removed": ["B"]
        },  # B 被删
        {
            "torrents": {
                "B": {
                    "state": "stalledUP"
                }
            },
            "torrents_removed": []
        },  # B 又被加回来
        {
            "torrents": {},
            "torrents_removed": ["A"]
        },  # A 被删
    ]
    out = simqb.merge_window(frames)
    assert "A" not in out["torrents"], "窗口内先增后删 => 不该吐该 hash"
    assert "B" in out["torrents"], "先删后加 => 净额是'加'"
    assert "A" in out["torrents_removed"], "A 被删且末态不在 => 必须报进 removed(客户端靠它得知种子没了)"
    assert "B" not in out["torrents_removed"], "B 的删除被后续新增抵消(净额)"
    assert out["torrents"]["A"]["upspeed"] if "A" in out["torrents"] else True


def test_merge_window_server_state_is_merge():
    """server_state 是 merge 不是 replace(与 store.py:111-118 同款)"""
    frames = [
        {
            "torrents": {},
            "server_state": {
                "up_info_speed": 1,
                "free_space_on_disk": 100
            }
        },
        {
            "torrents": {},
            "server_state": {
                "up_info_speed": 9
            }
        },
    ]
    out = simqb.merge_window(frames)
    assert out["server_state"] == {"up_info_speed": 9, "free_space_on_disk": 100}


def test_merge_window_tags_net():
    frames = [
        {
            "torrents": {},
            "tags": ["x", "y"],
            "tags_removed": []
        },
        {
            "torrents": {},
            "tags": ["z"],
            "tags_removed": ["x"]
        },
    ]
    out = simqb.merge_window(frames)
    assert set(out["tags"]) == {"y", "z"}
    assert out["tags_removed"] == ["x"]


# --------------------------------------------------------------------------- piece hash
def test_piece_hashes_shared_by_content_set():
    """同(相对路径+大小)集合 => 同列表 —— 否则严格模式判据恒假(比不测更糟)"""
    a = [("Show/a.mkv", 100), ("Show/b.mkv", 200)]
    b = [("Show/b.mkv", 200), ("Show/a.mkv", 100)]  # 顺序不同, 集合相同
    c = [("Show/a.mkv", 100), ("Show/b.mkv", 201)]  # 大小不同
    assert simqb.piece_hashes_of(a) == simqb.piece_hashes_of(b), "同内容集合必须共享同一列表(成员间一致)"
    assert simqb.piece_hashes_of(a) != simqb.piece_hashes_of(c)
    assert all(len(h) == 40 for h in simqb.piece_hashes_of(a))


def test_minimal_bencode_is_parseable_shape():
    blob = simqb.minimal_bencode("movie.mkv", 1234)
    assert blob.startswith(b"d") and blob.endswith(b"e")
    assert b"movie.mkv" in blob and b"i1234e" in blob


# --------------------------------------------------------------------------- 语料加载
def test_resolve_fsroot_placeholder():
    assert simqb.resolve_fsroot("<FSROOT>/d0/a", r"X:\run\fs") == "X:/run/fs/d0/a"
    assert simqb.resolve_fsroot("no-placeholder", r"X:\run") == "no-placeholder"
    # 不写死任何真实路径: 占位符必须真的被替换掉
    assert simqb.FSROOT_PLACEHOLDER not in simqb.resolve_fsroot("<FSROOT>/d0", "Y:/fs")


def _write_corpus(tmp_path: Path, status: str = "ok") -> Path:
    d = tmp_path / "corpus"
    d.mkdir(parents=True, exist_ok=True)
    t0 = {
        "t_seq": 0,
        "role": "t0",
        "full_update": True,
        "rid": 1,
        "torrents":
            {
                "a" * 40:
                    {
                        "name": "N",
                        "save_path": "<FSROOT>/d0/x",
                        "state": "stalledUP",
                        "tags": "T",
                        "category": "",
                        "size": 10
                    }
            },
        "server_state": {
            "free_space_on_disk": 123,
            "up_info_speed": 0
        },
        "tags": ["T"],
        "categories": {},
    }
    last = dict(t0, t_seq=1, role="closure", full_update=True)
    with gzip.open(d / "sync-stream.jsonl.gz", "wt", encoding="utf-8") as f:
        f.write(json.dumps(t0, ensure_ascii=False) + "\n")
        f.write(json.dumps(last, ensure_ascii=False) + "\n")
    with gzip.open(d / "files.json.gz", "wt", encoding="utf-8") as f:
        json.dump({"a" * 40: [{"name": "x/f.mkv", "size": 10}]}, f)
    with gzip.open(d / "trackers.json.gz", "wt", encoding="utf-8") as f:
        json.dump({"a" * 40: [{"url": "https://site-1.example/ann"}]}, f)
    with gzip.open(d / "disk.json.gz", "wt", encoding="utf-8") as f:
        json.dump({"a" * 40: {"x/f.mkv": {"exists": False, "size": None, "suffix": None}}}, f)
    with gzip.open(d / "groups.json.gz", "wt", encoding="utf-8") as f:
        json.dump({"groups": [{"group_id": "g00000", "size": 1, "members": ["a" * 40]}]}, f)
    (d / "meta.json").write_text(json.dumps({"status": status, "frames": 2}), encoding="utf-8")
    return d


def test_corpus_source_loads_and_rejects_aborted(tmp_path):
    d = _write_corpus(tmp_path)
    src = simqb.CorpusSource(str(d), r"X:\run\fs")
    assert len(src.frames) == 2
    assert src.t0["torrents"]["a" * 40]["save_path"] == "X:/run/fs/d0/x", "<FSROOT> 必须被解析"
    assert src.files_of("a" * 40)[0]["name"] == "x/f.mkv"
    assert src.closure is not None
    # 磁盘表: disk.json 里 exists=False => mock 必须回"不存在"
    tbl = src.disk_table()
    assert tbl["X:/run/fs/d0/x/x/f.mkv"]["exists"] is False

    bad = _write_corpus(tmp_path / "bad", status="aborted")
    with pytest.raises(SystemExit):
        simqb.CorpusSource(str(bad), r"X:\run\fs")


def test_corpus_tracker_section_picks_specific_tag():
    """站点标签取"对该 host 最专有"的 —— 通用标签(散布全库)不能被选中"""
    class FakeSim:
        corpus_mode = True
        torrents = {
            "h1": {
                "tags": "SiteA, Common",
                "_trackers_raw": [{
                    "url": "https://site-1.example/ann"
                }]
            },
            "h2": {
                "tags": "SiteA, Common",
                "_trackers_raw": [{
                    "url": "https://site-1.example/ann"
                }]
            },
            "h3": {
                "tags": "SiteB, Common",
                "_trackers_raw": [{
                    "url": "https://site-2.example/ann"
                }]
            },
            "h4": {
                "tags": "Common",
                "_trackers_raw": [{
                    "url": "https://site-2.example/ann"
                }]
            },
        }

    text = simqb.corpus_tracker_section(FakeSim())
    assert "site-1.example" in text and "site-2.example" in text
    assert "SiteA" in text and "SiteB" in text
    # Common 出现在两个站 => 专有度低, 不该被选中
    assert "- Common" not in text, f"通用标签不该被当作站点标签: {text}"
    # 生成物必须是**多行 YAML**, 不能是字面量 \n
    assert "\\n" not in text, "必须是真实换行, 不能是字面量反斜杠 n"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))


# --------------------------------------------------------------------------- 两层状态模型
def _make_sim(tmp_path, cmd_latency_ms: float, md_lag_ms: float, status: str = "ok"):
    """用极小语料构造一个 SimQb(不起 HTTP, 直接打方法)"""
    d = _write_corpus(tmp_path, status=status)
    args = simqb.build_parser().parse_args(
        [
            "--source=corpus:%s" % d, "--root",
            str(tmp_path / "root"), "--command-latency-ms",
            str(cmd_latency_ms), "--maindata-lag-ms",
            str(md_lag_ms)
        ]
    )
    args.root = str(tmp_path / "root")
    args.run_dir = simqb.make_run_dir(args.root, "t")
    return simqb.SimQb(args)


def test_two_layer_state_info_newer_than_maindata(tmp_path):
    """计划 §07 两层状态: 命令效果对 info 先可见, 对 sync/maindata 后可见(md 额外滞后)

    这是 issue 26-09-20-2145 的复现载体: 没有它, "真值尚未落地"这一类缺陷在本地永远测不出来。
    """
    sim = _make_sim(tmp_path, cmd_latency_ms=0, md_lag_ms=200)
    h = next(iter(sim.torrents))
    assert sim.torrents[h]["state"] == "stalledUP"

    sim.apply_write("torrents/stop", {"hashes": h})
    # 流状态(base)必须**不动** —— 命令效果一律走 overlay, base 只由录制流推进
    assert sim.torrents[h]["state"] == "stalledUP", "命令不得直接改流状态"

    now = time.time()
    assert sim._live(h, now)["state"] == "pausedUP", "info 侧应立刻可见(torrents/stop -> pausedUP)"
    assert sim._snapshot_view(h, now)["state"] == "stalledUP", "maindata 侧此刻还不该可见"

    later = now + 0.5
    assert sim._snapshot_view(h, later)["state"] == "pausedUP", "过了 md 滞后线后 maindata 才可见"


def test_two_layer_state_red_without_lag(tmp_path):
    """**红验**: 把两个滞后都设 0 => 两端同刻可见。若这一条不成立, 上一条也没在测滞后(只是恒绿)"""
    sim = _make_sim(tmp_path, cmd_latency_ms=0, md_lag_ms=0)
    h = next(iter(sim.torrents))
    sim.apply_write("torrents/stop", {"hashes": h})
    now = time.time()
    assert sim._live(h, now)["state"] == "pausedUP"
    assert sim._snapshot_view(h, now)["state"] == "pausedUP", "无滞后时两端必须同刻可见(红验: 判据能区分)"


def test_corpus_sync_full_then_increment(tmp_path):
    """语料档 sync: rid 失配走全量(87 种子全给), rid 一致走增量(只给脏集合)"""
    sim = _make_sim(tmp_path, cmd_latency_ms=0, md_lag_ms=0)
    full = sim.sync_maindata(0)
    assert full["full_update"] is True
    assert len(full["torrents"]) == len(sim.torrents)
    assert full["server_state"]["free_space_on_disk"] == 123, "server_state 必须来自流的首帧"
    inc = sim.sync_maindata(full["rid"])
    assert inc["full_update"] is False
    assert inc["torrents"] == {}, "无变化时增量轮不带种子"


# --------------------------------------------------------------------------- 两层状态模型
def _make_sim(tmp_path, cmd_latency_ms: float, md_lag_ms: float, status: str = "ok"):
    """用极小语料构造一个 SimQb(不起 HTTP, 直接打方法)"""
    d = _write_corpus(tmp_path, status=status)
    args = simqb.build_parser().parse_args(
        [
            "--source=corpus:%s" % d, "--root",
            str(tmp_path / "root"), "--command-latency-ms",
            str(cmd_latency_ms), "--maindata-lag-ms",
            str(md_lag_ms)
        ]
    )
    args.root = str(tmp_path / "root")
    args.run_dir = simqb.make_run_dir(args.root, "t")
    return simqb.SimQb(args)


def test_two_layer_state_info_newer_than_maindata(tmp_path):
    """计划 §07 两层状态: 命令效果对 info 先可见, 对 sync/maindata 后可见(md 额外滞后)

    这是 issue 26-09-20-2145 的复现载体: 没有它, "真值尚未落地"这一类缺陷在本地永远测不出来。
    """
    sim = _make_sim(tmp_path, cmd_latency_ms=0, md_lag_ms=200)
    h = next(iter(sim.torrents))
    assert sim.torrents[h]["state"] == "stalledUP"

    sim.apply_write("torrents/stop", {"hashes": h})
    # 流状态(base)必须**不动** —— 命令效果一律走 overlay, base 只由录制流推进
    assert sim.torrents[h]["state"] == "stalledUP", "命令不得直接改流状态"

    now = time.time()
    assert sim._live(h, now)["state"] == "pausedUP", "info 侧应立刻可见(torrents/stop -> pausedUP)"
    assert sim._snapshot_view(h, now)["state"] == "stalledUP", "maindata 侧此刻还不该可见"

    later = now + 0.5
    assert sim._snapshot_view(h, later)["state"] == "pausedUP", "过了 md 滞后线后 maindata 才可见"


def test_two_layer_state_red_without_lag(tmp_path):
    """**红验**: 把两个滞后都设 0 => 两端同刻可见。若这一条不成立, 上一条也没在测滞后(只是恒绿)"""
    sim = _make_sim(tmp_path, cmd_latency_ms=0, md_lag_ms=0)
    h = next(iter(sim.torrents))
    sim.apply_write("torrents/stop", {"hashes": h})
    now = time.time()
    assert sim._live(h, now)["state"] == "pausedUP"
    assert sim._snapshot_view(h, now)["state"] == "pausedUP", "无滞后时两端必须同刻可见(红验: 判据能区分)"


def test_corpus_sync_full_then_increment(tmp_path):
    """语料档 sync: rid 失配走全量(87 种子全给), rid 一致走增量(只给脏集合)"""
    sim = _make_sim(tmp_path, cmd_latency_ms=0, md_lag_ms=0)
    full = sim.sync_maindata(0)
    assert full["full_update"] is True
    assert len(full["torrents"]) == len(sim.torrents)
    assert full["server_state"]["free_space_on_disk"] == 123, "server_state 必须来自流的首帧"
    inc = sim.sync_maindata(full["rid"])
    assert inc["full_update"] is False
    assert inc["torrents"] == {}, "无变化时增量轮不带种子"
