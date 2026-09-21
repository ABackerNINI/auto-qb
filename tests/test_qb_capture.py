"""test_qb_capture 测试计划: 真机语料抓取器(scripts/qb_capture.py)

范围: 语料计划 26-09-21-0024 的 W1/W2 —— 脱敏(形态守恒/单射)与等价类守恒(头号验收)。
不连 qB、不碰网络、不写仓库外文件: 全部用合成输入直接打函数。

## 测试计划(每个测试函数一条)
- test_sanitizer_preserves_length_and_shape: 伪名与原文等长; 字符类别(大小写/数字/CJK/标点)逐位守恒
- test_sanitizer_preserves_extension: 扩展名逐字保留(计划 §05: 必须保留扩展名)
- test_sanitizer_is_injective_and_deterministic: 同一盐下同输入同输出; 映射零碰撞; 跨字段一致
- test_sanitizer_short_tag_collision_resolved: 碰撞分支: 用递增 nonce 确定性重派生且仍等长保形(不中止)
- test_sanitizer_short_tags_do_not_collide_on_real_data: 真实 qB 标签集(含 zE7/zE8/U2/R)零碰撞且等长
- test_sanitizer_path_equivalence_boundaries: 尾斜杠有无 / 大小写 / 不同盘符 三条边界 1:1 保留
- test_sanitizer_infohash_length_v1_v2: v1(40 hex) 与 v2(64 hex) 形状分别保持
- test_group_conservation_green: 正常脱敏下 pre/mapped/post 三个分区一致
- test_group_conservation_red_on_casefold: **红验** —— 脱敏把大小写归一后, 守恒判据必须变红(否则是空壳)
- test_group_conservation_red_on_member_path_change: **红验** —— 改掉组内一个成员路径的一个字符, 判据必须变红
- test_stream_accumulator_matches_store_semantics: server_state 是 merge / torrents 后写覆盖 / *_removed 净额
- test_diff_full_tolerates_volatile_but_flags_structural: 采样抖动(last_activity)不判红, 结构字段(state)判红
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "src"))


def _load_capture():
    """scripts/ 不是包, 按路径加载(与 sim_qb 等脚本一致的做法)"""
    spec = importlib.util.spec_from_file_location("qb_capture", _REPO / "scripts" / "qb_capture.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["qb_capture"] = mod
    spec.loader.exec_module(mod)
    return mod


cap = _load_capture()


def _san(salt=b"0123456789abcdef0123456789abcdef"):
    return cap.Sanitizer(salt)


# --------------------------------------------------------------------------- 脱敏
def test_sanitizer_preserves_length_and_shape():
    s = _san()
    for orig in ["Show.S01E01.1080p.WEB-DL-GRPi.mkv", "中文 名 测试.mkv", "ABCdef123-_.x", "FullＷidth１２３.txt", "a.b.c.d.e"]:
        out = s.name(orig)
        assert len(out) == len(orig), f"长度必须 1:1: {orig!r} -> {out!r}"
        for a, b in zip(orig, out):
            if a.isascii() and a.isalpha():
                assert b.isalpha() and (a.islower() == b.islower()), f"拉丁字母类别/大小写必须守恒: {a!r}->{b!r}"
            elif a.isdigit():
                assert b.isdigit(), f"数字必须守恒: {a!r}->{b!r}"
            elif a.isascii():
                assert b == a, f"标点/分隔符必须原样: {a!r}->{b!r}"
        assert out != orig, "应当确实被替换"


def test_sanitizer_preserves_extension():
    s = _san()
    for orig in ["movie.mkv", "dir/sub/name.mp4", "no_ext", "a.tar.gz"]:
        out = s.name(orig)
        assert out.endswith(Path(orig).suffix) or Path(orig).suffix == "", \
            f"扩展名必须逐字保留: {orig!r} -> {out!r}"


def test_sanitizer_is_injective_and_deterministic():
    s1, s2 = _san(), _san()
    names = ["A.mkv", "B.mkv", "A.mkv", "中文.mkv", "中文.mkv", "X" * 40 + ".mkv"]
    outs1 = [s1.name(n) for n in names]
    outs2 = [s2.name(n) for n in names]
    assert outs1 == outs2, "同一盐下必须确定性"
    assert outs1[0] == outs1[2], "同输入必须同输出(跨调用一致)"
    assert len(set(outs1)) == len(set(names)), "映射必须单射"
    # 跨字段一致: 同名目录与同名文件走同一套映射
    assert s1.name("Download") == s1.path("R:\\Download").rsplit("/", 1)[-1], "目录名与文件名须共享映射"


def test_sanitizer_short_tag_collision_resolved(monkeypatch):
    """碰撞必须被**确定性重派生**解决而不是中止(真机短标签同形是常态, 中止会让抓取跑不起来)

    直接打碰撞分支: 把 _shape 固定成同一输出, 逼出碰撞, 再断言两条性质 ——
    ① 仍单射(两个不同原文拿到不同伪名); ② 碰撞被记账(可观测)。
    """
    s = _san()
    monkeypatch.setattr(s, "_shape", lambda text, kind, orig, nonce=0: f"zL{nonce % 10}"[:len(text)])
    a, b = s.text("zE7"), s.text("zE8")
    assert a != b, "碰撞必须被解决(否则真机抓取直接中止)"
    assert len(a) == 3 and len(b) == 3, "重派生后仍须等长"
    assert s.collisions.get("tag", 0) >= 1, "碰撞次数应被记账(可观测)"
    assert s.text("zE7") == a, "重派生结果仍须确定性"


def test_sanitizer_short_tags_do_not_collide_on_real_data():
    """真实 qB 标签集(含 'zE7'/'zE8'/'U2'/'R' 这类同形短串)在正常盐下不得触发中止"""
    s = _san()
    tags = [
        "BTSchool", "CarPT", "CrabPT", "CyanBug", "DigitalCore", "HDFans", "HDHome", "HDTime", "HHan", "Kufirc",
        "MISSING", "MTeam", "MuXueGe", "NovaHD", "PTSBao", "PTTime", "PTZone", "R", "TangPT", "U2", "zE1", "zE1-3",
        "zE1-9", "zE1-20", "zE1-30", "zE1-31", "zE1-40", "zE1-57", "zE1-67", "zE1-71", "zE1-72", "zE1-73", "zE1-78",
        "zE1-80", "zE2", "zE5", "zE7", "zE8", "zE12", "zE23", "zE26", "zSkipChecked", "凤凰PT", "辅种"
    ]
    outs = [s.text(t) for t in tags]
    assert len(set(outs)) == len(tags), "真实标签集必须零碰撞"
    for t, o in zip(tags, outs):
        assert len(t) == len(o), f"等长: {t!r}->{o!r}"


def test_sanitizer_path_equivalence_boundaries():
    s = _san()
    # ① 尾斜杠有无 1:1 保留(不得 rstrip) —— 分隔符可能是 \ 或 /, 只看"是否以分隔符结尾"
    a, b = s.path("R:\\Download\\TV\\"), s.path("R:\\Download\\TV")
    assert a.endswith(("/", "\\")) and not b.endswith(("/", "\\")), \
        f"尾斜杠的有无必须 1:1 保留: {a!r} vs {b!r}"
    # ② 大小写形态 1:1 保留(path_normalize 不做 casefold)
    assert s.path("R:\\Downloads") != s.path("r:\\downloads"), "大小写不同必须是不同 key"
    # ③ 不同盘符不得并组 -> 带盘符短令牌
    assert s.path("R:\\Download") != s.path("S:\\Download"), "不同盘符不得映射到同一路径"
    # 同一逻辑路径的两种分隔符写法必须收敛到同一伪名(path_normalize 语义)
    assert s.path("R:/Download/PTing") == s.path("R:\\Download\\PTing"), "分隔符写法必须收敛"
    # 占位符: 不写死任何真实路径
    assert s.path("R:\\Download").startswith(cap.FSROOT_PLACEHOLDER), "必须用 <FSROOT> 占位符"
    # 分量确实被替换(不能是恒等映射)
    assert "Download" not in s.path("R:\\Download"), "路径分量必须被伪名化"


def test_sanitizer_infohash_length_v1_v2():
    s = _san()
    v1, v2 = "a" * 40, "b" * 64
    o1, o2 = s.infohash(v1), s.infohash(v2)
    assert len(o1) == 40 and len(o2) == 64, "v1=40 hex / v2=64 hex 形状必须分别保持"
    assert all(c in "0123456789abcdef" for c in o1 + o2), "必须仍是 hex"
    assert o1 != v1 and o2 != v2


# --------------------------------------------------------------------------- 守恒
def _toy_corpus():
    """4 个种子:
       H1/H2 同组(同路径集合, 分隔符写法不同); H3 单独(文件集合不同);
       H4 在另一块盘(不同组); H5 与 H1 只差大小写(必须仍是不同组)
    """
    torrents = {
        "H1": {
            "save_path": "R:\\Download\\TV",
            "name": "ShowA",
            "state": "stalledUP"
        },
        "H2": {
            "save_path": "R:/Download/TV",
            "name": "ShowA-copy",
            "state": "stalledUP"
        },
        "H3": {
            "save_path": "R:\\Download\\TV",
            "name": "ShowB",
            "state": "stalledUP"
        },
        "H4": {
            "save_path": "S:\\Download\\TV",
            "name": "ShowA-otherdisk",
            "state": "stalledUP"
        },
        "H5": {
            "save_path": "r:\\download\\tv",
            "name": "ShowA-lower",
            "state": "stalledUP"
        },
    }
    files = {
        "H1": [{
            "name": "ShowA/a.mkv",
            "size": 100
        }, {
            "name": "ShowA/b.mkv",
            "size": 200
        }],
        "H2": [{
            "name": "ShowA/a.mkv",
            "size": 100
        }, {
            "name": "ShowA/b.mkv",
            "size": 200
        }],
        "H3": [{
            "name": "ShowB/c.mkv",
            "size": 300
        }],
        "H4": [{
            "name": "ShowA/a.mkv",
            "size": 100
        }, {
            "name": "ShowA/b.mkv",
            "size": 200
        }],
        "H5": [{
            "name": "ShowA/a.mkv",
            "size": 100
        }, {
            "name": "ShowA/b.mkv",
            "size": 200
        }],
    }
    return torrents, files


def _sanitize(torrents, files, san):
    st = {san.infohash(h): cap.Capture._san_torrent(v, san) for h, v in torrents.items()}
    sf = {
        san.infohash(h): [dict(f, name=san.name(cap.utils.path_normalize(f["name"]))) for f in v]
        for h, v in files.items()
    }
    return st, sf


def test_group_conservation_green():
    t, f = _toy_corpus()
    san = _san()
    st, sf = _sanitize(t, f, san)
    res = cap.Capture._partition_equivalent(t, f, st, sf, san)
    assert res["ok"], f"正常脱敏下守恒判据必须绿: {res['problems']}"
    assert res["groups"] == 4, f"H1H2 / H3 / H4 / H5 => 4 组, 实得 {res['groups']}"


def test_group_conservation_red_on_casefold():
    """**红验**: 脱敏若把大小写归一, H5 会并进 H1/H2 组 —— 判据必须变红(否则它是空壳)"""
    t, f = _toy_corpus()

    class CasefoldSanitizer(cap.Sanitizer):
        """模拟"脱敏把大小写归一"这一等价类破坏: 不同大小写的路径会被并成同一组"""
        def path(self, p):
            return super().path(p.lower())

    san = CasefoldSanitizer(b"0123456789abcdef0123456789abcdef")
    st, sf = _sanitize(t, f, san)
    res = cap.Capture._partition_equivalent(t, f, st, sf, san)
    assert not res["ok"], "大小写被归一后守恒判据必须变红 —— 否则这条判据守不住任何东西"
    assert any("partition_mismatch" in p["kind"] for p in res["problems"])


def test_group_conservation_red_on_member_path_change():
    """**红验**(计划 §09 反向对照①): 改掉**多成员组**里一个成员的路径一个字符 -> 判据必须红"""
    t, f = _toy_corpus()
    san = _san()
    st, sf = _sanitize(t, f, san)
    # H2 原本与 H1 同组; 把它的文件名改一个字符 => 应当掉出该组
    h2 = san.infohash("H2")
    assert len(sf[h2]) == 2
    sf[h2] = [dict(sf[h2][0], name=sf[h2][0]["name"][:-1] + "Z"), sf[h2][1]]
    res = cap.Capture._partition_equivalent(t, f, st, sf, san)
    assert not res["ok"], "多成员组内一个成员路径被改一个字符后判据必须变红"
    assert any("partition_mismatch" in p["kind"] for p in res["problems"])


# --------------------------------------------------------------------------- 流语义
def test_stream_accumulator_matches_store_semantics():
    acc = cap.StreamAccumulator()
    acc.apply(
        {
            "full_update": True,
            "torrents": {
                "A": {
                    "state": "stalledUP",
                    "upspeed": 1
                }
            },
            "server_state": {
                "up_info_speed": 10,
                "free_space_on_disk": 100
            },
            "tags": ["x", "y"],
            "categories": {
                "c1": {}
            }
        }
    )
    assert acc.torrents["A"]["state"] == "stalledUP"
    assert acc.tags == {"x", "y"}
    # 增量: server_state 是 merge 不是 replace(store.py:111-118)
    acc.apply({"torrents": {"A": {"upspeed": 5}}, "server_state": {"up_info_speed": 99}})
    assert acc.torrents["A"]["upspeed"] == 5 and acc.torrents["A"]["state"] == "stalledUP", "增量须后写覆盖"
    assert acc.server_state == {"up_info_speed": 99, "free_space_on_disk": 100}, "server_state 必须 merge"
    # torrents_removed 净额
    acc.apply({"torrents": {}, "torrents_removed": ["A"]})
    assert "A" not in acc.torrents
    # tags 增删
    acc.apply({"torrents": {}, "tags": ["z"], "tags_removed": ["x"]})
    assert acc.tags == {"y", "z"}


def test_diff_full_tolerates_volatile_but_flags_structural():
    """采样抖动(last_activity 是 1 秒分辨率时钟)不得判红; 结构字段(state)漂移必须判红"""
    frame = {
        "torrents": {
            "A": {
                "state": "stalledUP",
                "last_activity": 100,
                "name": "n"
            }
        },
        "server_state": {
            "free_space_on_disk": 1
        }
    }
    acc = cap.StreamAccumulator()
    acc.apply(
        {
            "full_update": True,
            "torrents": {
                "A": {
                    "state": "stalledUP",
                    "last_activity": 99,
                    "name": "n"
                }
            },
            "server_state": {
                "free_space_on_disk": 2
            }
        }
    )
    res = cap.diff_full(acc, frame)
    assert res["ok"], "仅 last_activity / free_space_on_disk 抖动时不得判红"
    assert res["volatile_field_diffs"].get("last_activity") == 1, "抖动仍须上报(可观测)"

    acc2 = cap.StreamAccumulator()
    acc2.apply(
        {
            "full_update": True,
            "torrents": {
                "A": {
                    "state": "stoppedUP",
                    "last_activity": 99,
                    "name": "n"
                }
            },
            "server_state": {
                "free_space_on_disk": 2
            }
        }
    )
    res2 = cap.diff_full(acc2, frame)
    assert not res2["ok"], "state 漂移必须判红"
    assert res2["field_diff_counts"].get("state") == 1


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
