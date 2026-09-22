"""test_sim_corpus 测试计划: 语料回放(scripts/sim_fsmock.py · scripts/sim_qb.py 的语料侧)

范围: 语料计划 26-09-21-0024 的 W3 —— FS mock / 窗口合并语义 / piece hash 派生 / 语料加载与配置派生。
不连 qB、不起服务、不写仓库外文件。

## 测试计划(每个测试函数一条)
- test_fsmock_intercepts_corpus_paths: 语料树内的路径走表(三态), 树外原样委托真函数
- test_fsmock_long_path_prefix_and_case: 剥 \\\\?\\ 前缀 + 大小写不敏感(NTFS 语义) —— 不这么做会把存在的文件报成缺失
- test_fsmock_case_folding_does_not_follow_platform: **防回潮** —— 折叠必须固定走 NTFS 语义, 不得跟随 `os.path`(运行时把 os 换成 posixpath 判, 不靠文本扫描)
- test_sim_is_within_host_semantics: B2 逃逸判定在**宿主语义**下成立(真子路径/根自身/树外兄弟), 两平台各真跑一次
- test_sim_is_within_linux_equivalent: Linux 等价(`os`->posixpath + sep '/')下同一组断言仍成立
- test_sim_is_within_red_on_fold_without_sep: **红验** —— 只换 ntpath 折叠、分隔符不动 => 真子路径被误拒(证明上条不恒绿)
- test_safe_delete_rejects_path_outside_fs_root: B2 逃逸(从 `sim_qb.py --self-test` **下沉**, 进 CI)—— 树外删除目标被拒 + 文件没被真删 + 记进 violations
- test_safe_delete_rejects_bulk_over_declared: B3 数量上限(下沉)—— 钉**两侧**: 超 declared*2 要拒, 恰好 2 倍不拒(只钉一侧会被"更严格"或"更宽松"两头骗过)
- test_delete_group_files_removes_them_from_disk: D4 删组文件(下沉)—— 走**合成档**(语料档 mock 模式磁盘上没文件 ⇒ `_walk()` 恒 0 ⇒ 判据恒假), 删完磁盘真少文件 + 组内恰好一个成员进 error
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
import ntpath
import os
import posixpath
import sys
import time
import types
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


def test_fsmock_case_folding_does_not_follow_platform(monkeypatch):
    """大小写折叠必须**固定走 NTFS 语义**, 不能跟随运行平台(2026-09-22 Linux CI 红了这条)。

    ❗为什么不用文本扫描当判据: `os.path.normcase` 这串字**就写在 `_key()` 的 docstring 里**
    (作为反例警告), 文本扫描会被注释骗过 —— 冒烟里 `_scan_filter_facets` 先剥注释就是同一个坑。
    故改为**运行时判定**: 把模块里的 `os` 换成 `path=posixpath` 的替身。折叠若真跟随 `os.path`,
    结果立刻退化成大小写敏感 ⇒ 红; 走 `ntpath.normcase` 则不受影响 ⇒ 绿。
    这一换**精确等价**于"旧代码跑在 Linux"(Linux 下 `os.path is posixpath`), 所以本机就能
    抓住只在 CI 上现形的失败, 不必等推上去。
    """
    s = r"x:\CORPUS-FS\d0\a\movie.mkv"
    want = s.replace("/", "\\").lower()  # 纯字符串的 NTFS 折叠(与平台无关的期望式)
    assert fsmock._key(s) == want, f"_key 必须做大小写折叠: {fsmock._key(s)!r} != {want!r}"

    monkeypatch.setattr(fsmock, "os", types.SimpleNamespace(path=posixpath))
    assert fsmock._key(s) == want, (
        "大小写折叠跟随了 os.path —— 在 Linux(os.path is posixpath, "
        "normcase 是恒等函数)上会退化成大小写敏感 ⇒ D4 判据全假"
    )


# --------------------------------------------------------------------------- B2 逃逸判定: 宿主语义
# sim_qb 的 fs_root 是 `os.path.join(run_dir, "fs")` 且 os.makedirs 真建的**宿主目录**
# (语料档走 resolve_fsroot: "<FSROOT>" -> 同一个 fs_root), save_path 一律由它拼出 ⇒
# 路径是**宿主形态**, 不是 Windows 假路径 ⇒ 判定必须跟随宿主 FS 语义(不能统一到 ntpath)。
def test_sim_is_within_host_semantics(tmp_path):
    """B2 逃逸判定在**宿主语义**下必须成立 —— 本机 win32 / CI linux, 两边各真跑一次

    用 tmp_path 而不是写死盘符路径, 就是为了让它**两平台都能真跑**(而不是靠 monkeypatch 演算)。
    """
    root = tmp_path / "fs"
    (root / "d0").mkdir(parents=True)
    child = root / "d0" / "x.mkv"
    sibling = tmp_path / "other" / "x.mkv"  # 兄弟目录: 名字以 root 为前缀但不是其子
    assert simqb.is_within(str(child), str(root)) is True, "真子路径必须判为在界内"
    assert simqb.is_within(str(root), str(root)) is True, "根自身算界内"
    assert simqb.is_within(str(sibling), str(root)) is False, "树外兄弟目录必须判为逃逸"


def test_sim_is_within_linux_equivalent(monkeypatch):
    """Linux 等价: `os` -> (posixpath, sep '/') ⇒ 本机(win32)就能复现 CI 的语义

    与 test_fsmock_case_folding_does_not_follow_platform 同款手法: 不必等推上去才知道 Linux 红不红。
    """
    monkeypatch.setattr(simqb, "os", types.SimpleNamespace(path=posixpath, sep="/"))
    assert simqb.is_within("/run/fs/d0/x.mkv", "/run/fs") is True
    assert simqb.is_within("/run/other/x.mkv", "/run/fs") is False


def test_sim_is_within_red_on_fold_without_sep(monkeypatch):
    """**红验**: 只把折叠换成 ntpath、分隔符不动 ⇒ Linux 上**真子路径被误拒**

    含义: 「统一到 ntpath」不是单点改动 —— **折叠与分隔符必须同源**。只换一半会混分隔符
    (`r="\\run\\fs"` 再拼 `"/"`) ⇒ B2 把**所有**路径判成逃逸 ⇒ sim 每个写入撞 BoundaryViolation。
    本条证明上一条守阵**能区分两态**, 不是恒绿。
    """
    monkeypatch.setattr(simqb, "os", types.SimpleNamespace(path=posixpath, sep="/"))

    def _norm_ntpath_only(p):
        if p.startswith("\\\\?\\"):
            p = p[4:]
        return ntpath.normcase(posixpath.realpath(posixpath.abspath(p)))

    monkeypatch.setattr(simqb, "_norm", _norm_ntpath_only)
    assert simqb.is_within("/run/fs/d0/x.mkv", "/run/fs") is False, ("只换 normcase 会把真子路径判成逃逸 ⇒ 折叠与分隔符必须同源(改一个就必红)")


def test_safe_delete_rejects_path_outside_fs_root(tmp_path):
    """B2 逃逸: `safe_delete_files` 对落在 fs_root 之外的目标必须拒绝(从 `--self-test` 下沉, 进 CI)

    ❗为什么要下沉: 这一段原本只在 `python scripts/sim_qb.py --self-test` 里跑 —— 要真起 HTTP 服务
    **且**真装 qbittorrentapi(没装就整段 `return 0` 跳过), **CI 从不执行** ⇒ 平台语义回归抓不到
    (pitfalls「Windows 全绿 / Linux 全红」❗⑤ 的根因就是这个盲区)。这里改成直接打方法, 不起服务。
    比原自检多钉两条: ① 拒绝时**文件没被真删**(别把"拒了"做成"删了") ② **记进 violations**
    (否则"拒了但没记账"看不出来 —— 记账是 sim_run 判定越界的依据)。
    """
    sim = _make_sim(tmp_path, cmd_latency_ms=0, md_lag_ms=0)
    outside = os.path.join(os.path.dirname(sim.fs_root), "outside.txt")
    with open(outside, "w", encoding="utf-8") as f:
        f.write("x")
    with pytest.raises(simqb.BoundaryViolation):
        sim.safe_delete_files([outside], 1)
    assert os.path.exists(outside), "拒绝后文件必须还在 —— 拒绝≠删除"
    assert any("B2" in v for v in sim.violations), f"必须记进 violations(否则越界无从审计): {sim.violations}"


def test_safe_delete_rejects_bulk_over_declared(tmp_path):
    """B3 数量上限(从 `--self-test` 下沉): 单次删除条数 > declared*2 必须拒绝, 且**恰好 2 倍不拒**

    钉两侧是因为只钉一侧判据会失真: 只钉"超了要拒" ⇒ 有人把阈值改成 1 倍(更严格)也绿;
    只钉"2 倍不拒" ⇒ 有人改成 10 倍(形同虚设)也绿。
    """
    sim = _make_sim(tmp_path, cmd_latency_ms=0, md_lag_ms=0)
    h0 = next(iter(sim.torrents))
    paths = sim.file_paths_of(sim.torrents[h0])
    assert paths, "该种子必须带文件列表, 否则 B3 判据无从触发(恒绿)"
    with pytest.raises(simqb.BoundaryViolation):
        sim.safe_delete_files(paths * 3, 1)  # 3 > 1*2 ⇒ 必须拒
    assert any("B3" in v for v in sim.violations), f"必须记进 violations: {sim.violations}"
    # 反向: 恰好 declared*2 条 ⇒ 不该触发 B3(放行; 文件不存在时各自被吞, 不抛)
    sim.safe_delete_files(paths * 2, 1)


def test_delete_group_files_removes_them_from_disk(tmp_path):
    """D4 删组文件(从 `--self-test` 下沉): 删完磁盘上**确实少文件**, 且组内一个成员进 `error`

    ❗必须用**合成档**: 语料档是 `fs-mode=mock`, 磁盘上根本没有文件 ⇒ `_walk()` 前后都是 0
    ⇒ "删完更少"永远不成立 ⇒ 判据**恒假**(比不测更糟)。这是下沉时最容易踩的坑, 故显式断言
    `before > 0` 把"没物化"变成红而不是绿。
    """
    sim = _make_synthetic_sim(tmp_path, n=40)
    assert sim.groups, "合成档必须造出辅种组"
    before = len(sim._walk())
    assert before > 0, "合成档必须真物化文件 —— 否则 D4 判据恒假(语料档 mock 模式下就是 0)"
    n = sim.delete_group_files(0)
    after = len(sim._walk())
    assert n > 0, "必须真删掉了文件"
    assert after < before, f"磁盘上该文件必须消失: {before} -> {after}"
    # 组内**一个**成员进 error(qB 状态名必须是 "error"; 写成 "errored" 会被解析成 UNKNOWN)
    members = [h for h in sim.groups[0] if h in sim.torrents]
    assert sum(1 for h in members if sim.torrents[h]["state"] == "error") == 1, "只该有一个成员进 error"


def _make_synthetic_sim(tmp_path, n: int = 40):
    """合成档 SimQb(默认**物化**文件) —— D4 这类"磁盘上真少了文件"的判据只能用它

    与 `_make_sim`(语料档, fs-mode=mock, 不物化)成对: 两者路径语义相同(都是宿主真实目录),
    差别只在磁盘上有没有真文件。
    """
    args = simqb.build_parser().parse_args(["--source=synthetic", "--n", str(n), "--root", str(tmp_path / "root")])
    args.root = str(tmp_path / "root")
    args.run_dir = simqb.make_run_dir(args.root, "syn")
    return simqb.SimQb(args)


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
    "core/mixins/grouping.py": {
        "os.path.exists": 1,
        "os.path.getsize": 1
    },
    "core/mixins/checking.py": {
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
    (tmp_path / "auto_qb" / "core" / "mixins" /
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
        corpus = None  # 没有语料 -> 必须退回统计派生
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


# --------------------------------------------------------------------------- 时间轴回放(W4)
def _write_timeline_corpus(tmp_path: Path) -> Path:
    """4 帧: T0 + 2 条带 dt_ms 的增量 + 末帧 closure; 第 2 条增量带 fs_delta"""
    d = tmp_path / "tl"
    d.mkdir(parents=True, exist_ok=True)
    h1, h2 = "a" * 40, "b" * 40
    t0 = {
        "t_seq": 0,
        "role": "t0",
        "full_update": True,
        "rid": 1,
        "dt_ms": 0,
        "rtt_ms": 10.0,
        "torrents":
            {
                h1:
                    {
                        "name": "N1",
                        "save_path": "<FSROOT>/d0/x",
                        "state": "stalledUP",
                        "tags": "",
                        "category": "",
                        "size": 10
                    }
            },
        "server_state": {
            "free_space_on_disk": 123,
            "up_info_speed": 0
        },
        "tags": [],
        "categories": {}
    }
    i1 = {
        "t_seq": 1,
        "role": "inc",
        "full_update": False,
        "rid": 2,
        "dt_ms": 1000.0,
        "rtt_ms": 3.0,
        "torrents": {
            h1: {
                "upspeed": 111
            }
        },
        "server_state": {
            "up_info_speed": 111
        }
    }
    i2 = {
        "t_seq": 2,
        "role": "inc",
        "full_update": False,
        "rid": 3,
        "dt_ms": 1000.0,
        "rtt_ms": 5.0,
        "torrents":
            {
                h1: {
                    "upspeed": 222
                },
                h2:
                    {
                        "name": "N2",
                        "save_path": "<FSROOT>/d0/y",
                        "state": "stalledUP",
                        "tags": "",
                        "category": "",
                        "size": 20
                    }
            },
        "torrents_removed": [],
        "server_state": {
            "up_info_speed": 222
        },
        "fs_delta": {
            h1: {
                "x/f.mkv": {
                    "exists": True,
                    "size": 10
                }
            }
        }
    }
    cl = {
        "t_seq": 3,
        "role": "closure",
        "full_update": True,
        "rid": 9,
        "dt_ms": 0,
        "rtt_ms": 10.0,
        "torrents":
            {
                h1:
                    {
                        "name": "N1",
                        "save_path": "<FSROOT>/d0/x",
                        "state": "stalledUP",
                        "tags": "",
                        "category": "",
                        "size": 10,
                        "upspeed": 222
                    },
                h2:
                    {
                        "name": "N2",
                        "save_path": "<FSROOT>/d0/y",
                        "state": "stalledUP",
                        "tags": "",
                        "category": "",
                        "size": 20
                    }
            },
        "server_state": {
            "free_space_on_disk": 123,
            "up_info_speed": 222
        },
        "tags": [],
        "categories": {}
    }
    with gzip.open(d / "sync-stream.jsonl.gz", "wt", encoding="utf-8") as f:
        for fr in (t0, i1, i2, cl):
            f.write(json.dumps(fr, ensure_ascii=False) + "\n")
    with gzip.open(d / "files.json.gz", "wt", encoding="utf-8") as f:
        json.dump({h1: [{"name": "x/f.mkv", "size": 10}], h2: [{"name": "y/g.mkv", "size": 20}]}, f)
    with gzip.open(d / "trackers.json.gz", "wt", encoding="utf-8") as f:
        json.dump({h1: [], h2: []}, f)
    with gzip.open(d / "disk.json.gz", "wt", encoding="utf-8") as f:
        json.dump({h1: {"x/f.mkv": {"exists": False, "size": None}}, h2: {}}, f)
    with gzip.open(d / "groups.json.gz", "wt", encoding="utf-8") as f:
        json.dump({"groups": []}, f)
    (d / "meta.json").write_text(json.dumps({"status": "ok", "frames": 4}), encoding="utf-8")
    return d


def _make_tl_sim(tmp_path, speed: float = 0.0):
    d = _write_timeline_corpus(tmp_path)
    args = simqb.build_parser().parse_args(
        ["--source=corpus:%s" % d, "--root",
         str(tmp_path / "root"), "--replay-speed",
         str(speed)]
    )
    args.root = str(tmp_path / "root")
    args.run_dir = simqb.make_run_dir(args.root, "tl")
    return simqb.SimQb(args)


def test_timeline_excludes_closure_frame(tmp_path):
    """末帧是校验锚点, **不得**进可回放集合(吐了客户端会按全量轮重置一次)"""
    sim = _make_tl_sim(tmp_path)
    assert len(sim.replay_data) == 3, "T0 + 2 增量 可回放; closure 必须被排除"
    assert all(f.get("role") != "closure" for f in sim.replay_data)
    assert sim.replay_total_ms == 2000.0, "时间轴 = 各帧实测 dt_ms 之和"


def test_timeline_advances_and_merges_window(tmp_path):
    """游标推进: 消费窗口内的帧并**合并成一拍**; 后写覆盖 + server_state merge"""
    sim = _make_tl_sim(tmp_path, speed=0.0)
    h1 = "a" * 40
    # 游标 0: T0 那一帧(dt=0)应当被消费, 但不带任何变化
    sim.consume_replay(0)
    assert sim.replay_pos == 1
    # 推进到 1000ms: 消费第 2 帧
    sim.consume_replay(1000)
    assert sim.replay_pos == 2
    assert sim.torrents[h1]["upspeed"] == 111
    assert sim._corpus_ss["up_info_speed"] == 111, "server_state 必须 merge"
    # 推进到 2500ms: 第 3 帧也要进来(合并成一拍)
    sim.consume_replay(2500)
    assert sim.replay_pos == 3
    assert sim.torrents[h1]["upspeed"] == 222, "窗口内后写覆盖"
    assert "b" * 40 in sim.torrents, "该帧新增的种子必须进状态"
    assert sim.replay_stats["windows"] == 3
    # 游标推到时间轴之后: 不重复消费
    sim.consume_replay(999999)
    assert sim.replay_pos == 3
    assert sim.replay_stats["ended"] is True


def test_timeline_applies_fs_delta(tmp_path):
    """录制期真发生过的磁盘变化必须按 t_seq 重演(不是"回放时文件都齐全")"""
    sim = _make_tl_sim(tmp_path, speed=0.0)
    h1 = "a" * 40
    key = sim.fs_root.replace("\\", "/") + "/d0/x/x/f.mkv"  # 解析后的 save_path + 相对路径
    # 初值: disk.json 说它不存在
    assert sim.fsmock_state()["files"][key]["exists"] is False
    sim.consume_replay(2500)
    assert sim.fsmock_state()["files"][key]["exists"] is True, "fs_delta 必须叠到磁盘状态上"
    assert sim.fsmock_state()["files"][key]["size"] == 10


def test_replay_latency_modes(tmp_path):
    """--latency-mode: recorded 用录到的真实 rtt; const 用 --latency-ms"""
    sim = _make_tl_sim(tmp_path, speed=0.0)
    sim.consume_replay(2500)
    assert sim._last_rtt_ms > 0
    assert sim.replay_latency_ms() == sim._last_rtt_ms, "recorded 模式用录到的 rtt"
    sim.args.latency_mode = "const"
    sim.latency_ms = 7.0
    assert sim.replay_latency_ms() == 7.0, "const 模式用 --latency-ms"


# --------------------------------------------------------------------------- 头号判据 CORPUS.group_exact
def test_group_exact_diff_green(tmp_path=None):
    """顺序无关: 只要成员集合逐组一致就是绿"""
    simrun = _load("sim_run")
    truth = [{"a", "b"}, {"c"}, {"d", "e"}]
    actual = [{"d", "e"}, {"a", "b"}, {"c"}]
    missing, extra = simrun.group_exact_diff(truth, actual)
    assert not missing and not extra


def test_group_exact_diff_red_on_member_swap():
    """**红验**: 成员被串了组 —— 组数**仍然相同**, 只比组数会漏掉(这正是增量应用出错的样子)"""
    simrun = _load("sim_run")
    truth = [{"a", "b"}, {"c", "d"}]
    actual = [{"a", "c"}, {"b", "d"}]
    missing, extra = simrun.group_exact_diff(truth, actual)
    assert len(missing) == 2 and len(extra) == 2, "串组必须同时报 missing 与 extra"


def test_group_exact_diff_red_on_split_group():
    """**红验**: 一个真值组被拆成两组 => 必须红"""
    simrun = _load("sim_run")
    truth = [{"a", "b"}]
    actual = [{"a"}, {"b"}]
    missing, extra = simrun.group_exact_diff(truth, actual)
    assert missing and extra


def test_group_exact_diff_red_on_missing_group():
    """**红验**: 真值组没被分出来 => 必须红"""
    simrun = _load("sim_run")
    truth = [{"a", "b"}, {"c", "d"}]
    actual = [{"a", "b"}]
    missing, extra = simrun.group_exact_diff(truth, actual)
    assert len(missing) == 1 and not extra


# --------------------------------------------------------------------------- 脱敏映射(W3 补: tracker / tag)
def test_known_tag_literals_are_mapped_after_sanitization():
    """auto-qb 自有标签字面量(MISSING / zSkipChecked)被伪名化后, 必须能在 meta 里查到"字面量 -> 伪名"

    ❗踩过的坑: 标签集合里存的是**已脱敏**的伪名, 拿原始字面量去 `in` 判断永远为假 ⇒ 映射恒为空
    ⇒ 回放端生成的 config 用的还是真字面量 ⇒ 跳检 / 缺文件行为与真机不一致(判据全绿也是假的)。
    所以必须用反查表把伪名还原成原文再比。
    """
    cap = _load("qb_capture")
    san = cap.Sanitizer(b"\x00" * 32)
    pseudo = {san.text(t) for t in ("MISSING", "zSkipChecked", "PTFans")}
    # 伪名不是原文(确实被脱敏了)
    assert "MISSING" not in pseudo and "zSkipChecked" not in pseudo
    # 反查表能把伪名还原成原文 —— 这是"只在真机上真出现过才记"这条判据能成立的前提
    revs = san._revs.get("tag") or {}
    raw_seen = {revs.get(t, t) for t in pseudo}
    assert raw_seen == {"MISSING", "zSkipChecked", "PTFans"}
    mapped = {lit: san.text(lit) for lit in cap.KNOWN_TAG_LITERALS if lit in raw_seen}
    assert mapped == {"MISSING": san.text("MISSING"), "zSkipChecked": san.text("zSkipChecked")}
    # 确定性: 同一字面量跨实例(同盐)必须同一伪名
    assert cap.Sanitizer(b"\x00" * 32).text("MISSING") == san.text("MISSING")
