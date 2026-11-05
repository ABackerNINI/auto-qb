"""test_core_fastresume 测试计划: fastresume 双键改写编辑器(计划 26-11-05-0808 §3.2 S2 一期)

覆盖面(全部替身 + tmp 目录构造, 不依赖真机 qB; 真机「改写一次重启加载成功」(N2 对齐)
按计划留 S6 留痕 —— 测试 qB 现不在线, 不阻塞本模块交付):
- bencode 编码: 与 hr.bencode 解码往返一致 + 行为口径(键序排序/只收解码闭包类型
  bytes/int/list/dict, str 等域外类型拒 —— 收 str 则「编码后解码 != 原值」, 往返自校验
  不变量被打破);
- 定位: v1 直查优先 -> v2 直查 -> .torrent 对现算 infohash 兜底匹配(混合/v2 不猜命名);
- 双键改写: lt save_path(反斜杠)与 qBt 键(正斜杠)逐键前缀替换保风味(N1 实测字节);
  qBt-downloadPath 独立前缀替换(不抄 save_path 新值); 分量边界(防 R:\\data 吞
  R:\\database); 幂等(已是目标值跳过, 黄金法则 1); N10 相对路径「不匹配即跳过」绝不
  重推导绝对路径; AutoTMM 形态(无 qBt 两键, N8: 55 vs 57 键);
- 安全三件套: 往返自校验不过绝不落盘(N6 拒载形态) / .bak 备份与回滚(D7: 覆盖回原名) /
  tmp+replace+fsync 原子写(无临时残留);
- retarget 单成员一步到位: written / unchanged(零落盘) / not_found / 坏样本上抛。

## 测试计划(每个测试函数一条)
- test_bencode_encode_canonical_and_roundtrip: 嵌套结构钉死字节(键序排序/int/负数/
  utf-8 串) + hr.bencode.bdecode 往返逐键相等
- test_bencode_rejects_unsupported_types: float/None/object 抛 TypeError
- test_load_fastresume_rejects_malformed: 截断/尾部残留/顶层非字典 -> FastresumeError;
  合法样本 -> dict
- test_locate_direct_hits_v1_priority: <v1>.fastresume 命中; 仅 v2 身份命中 <v2> 命名;
  两个名字都在时 v1 优先(钉死命中顺序)
- test_locate_hybrid_falls_back_to_torrent_scan: 文件名不含任何身份 hash 时经配对
  .torrent 现算 infohash 匹配(v1 身份/v2 身份都能命中); 身份不符或 .fastresume 缺席
  -> None
- test_locate_none_cases: 空目录串/目录不存在/双 hash 全空/库内无匹配 -> None
- test_rewrite_dual_keys_flavor_preserved_and_pure: N1 形态(lt 反斜杠 + qBt 正斜杠 +
  downloadPath)逐键各保风味; 无关键字节不动; 入参 dict 不被原地修改(纯函数)
- test_rewrite_downloadpath_independent: 未完成种形态 downloadPath 与 save_path 不同值
  (老根下子目录) -> 各自前缀替换, 互不抄值
- test_rewrite_boundary_and_flavor_variants: 等值/子目录命中改写; R:\\database 不被
  R:\\data 前缀误吞; 混合分隔符值命中后尾巴原样保留; 新根为旧根扩串(R:\\data2)时已
  在新根的值判 already 不误改
- test_rewrite_idempotent_skips_already_at_target: 改写产物重跑全键 already 且 dict
  相等; 嵌套根(old 是 new 前缀)先判 already 防二次改写
- test_rewrite_relative_save_path_skipped: N10 形态 —— lt save_path 为 CWD 相对路径 ->
  unmatched 原样保留(输出无任何重推导的绝对路径), qBt 键照改
- test_rewrite_autotmm_form: N8 形态 —— 无 qBt-savePath/qBt-downloadPath 键, 仅
  save_path 进 rewritten, 其余键原样, 不抛
- test_rewrite_fail_fast_on_bad_roots: 空 old/new 与 old==new -> ValueError; 仅风味
  不同的新旧根(同一路径两种写法)-> 全键 unmatched 零改写
- test_save_roundtrip_and_no_tmp_residue: 写盘后重读逐键相等 + 键数不变(N2「键数不变」
  角度, ~60 键含嵌套) + 无 .aqtmp 残留
- test_save_roundtrip_guard_blocks_corrupt_payload: 注入坏编码产物 -> 往返自校验抛
  FastresumeError, 磁盘零触碰(原文件不动/无 .bak/无 .aqtmp)
- test_save_bak_and_restore_rollback: 落盘建 .bak(内容 = 改写前字节); restore_backup
  覆盖回原名恢复原字节(D7); 无 .bak 时 restore 返回 False
- test_retarget_end_to_end_written_then_unchanged: 真实形态字典整链改写落盘(written +
  双键新值 + .bak 在场); 同参重放 unchanged 且文件字节/mtime 零变化(黄金法则 1)
- test_retarget_not_found_and_malformed_propagation: 身份不符 -> not_found 不抛;
  坏 bencode 样本 -> FastresumeError 上抛且原文件/无 .bak 零触碰
"""
from pathlib import Path

import pytest

from auto_qb.core import fastresume as frmod
from auto_qb.hr.bencode import bdecode as hr_bdecode
from auto_qb.hr.bencode import compute_infohashes

# ---------------------------------------------------------------------------
# 构造器(测试内造, 不放二进制 fixtures —— 与 tests/hr_helpers.py 造种风格一致)
# ---------------------------------------------------------------------------

OLD = r"R:\qbt-fake\n1"
NEW = r"T:\pt"


def _torrent_bytes(name: bytes = b"n1member") -> bytes:
    """最小 .torrent(info dict 结构对定位器无要求, infohash = info 原始切片的哈希)。"""
    info = {b"name": name, b"piece length": 16384, b"pieces": b"\x00" * 20, b"length": 1}
    return frmod.bencode({b"announce": b"http://tracker.example/ann", b"info": info})


def _manual_dict() -> dict:
    """manual 成员形态(N2 实测: lt 键反斜杠, qBt 键正斜杠, 两键风味不一致)。"""
    return {
        b"save_path": rb"R:\qbt-fake\n1\member",
        b"qBt-savePath": b"R:/qbt-fake/n1/member",
        b"qBt-downloadPath": b"R:/qbt-fake/n1",
        b"qBt-name": "成员种".encode("utf-8"),
        b"completed": 1,
        b"trackers": [b"http://tracker.example/ann"],
    }


def _write_torrent_pair(d: Path, torrent: bytes, stem: str) -> str:
    """把 .torrent 与按给定 stem 命名的 .fastresume 成对落库, 返回 v1 hash。"""
    (d / f"{stem}.torrent").write_bytes(torrent)
    v1, _, _ = compute_infohashes(torrent)
    (d / f"{stem}.fastresume").write_bytes(frmod.bencode(_manual_dict()))
    return v1


# ---------------------------------------------------------------------------
# bencode 编码
# ---------------------------------------------------------------------------


def test_bencode_encode_canonical_and_roundtrip():
    val = {
        b"z": "值".encode("utf-8"),  # 多字节 utf-8 值(3B)
        b"a": -5,
        b"m": {
            b"k2": [1, b"x"],
            b"k1": 0
        },
        b"b": b"raw",
    }
    # 键按字节序排序(a < b < m < z; 嵌套字典同理), 整数含负数, 串长为字节数("k1"=2B)
    assert frmod.bencode(val) == (b"d1:ai-5e"
                                  b"1:b3:raw"
                                  b"1:md2:k1i0e2:k2li1e1:xee"
                                  b"1:z3:\xe5\x80\xbc"
                                  b"e")
    enc = frmod.bencode(val)
    back, pos = hr_bdecode(enc)
    assert pos == len(enc)
    assert back == val  # 逐键深度相等(含嵌套)


def test_bencode_rejects_unsupported_types():
    with pytest.raises(TypeError):
        frmod.bencode(1.5)
    with pytest.raises(TypeError):
        frmod.bencode(None)
    with pytest.raises(TypeError):
        frmod.bencode("str")
    with pytest.raises(TypeError):
        frmod.bencode({1: b"x"})  # int 键拒
    with pytest.raises(TypeError):
        frmod.bencode({"k": b"v"})  # str 键拒(解码域只有 bytes 键, 收则往返必不等)


# ---------------------------------------------------------------------------
# 读
# ---------------------------------------------------------------------------


def test_load_fastresume_rejects_malformed(tmp_path):
    p = tmp_path / "h.fastresume"
    good = frmod.bencode(_manual_dict())
    p.write_bytes(good)
    assert frmod.load_fastresume(p) == _manual_dict()

    p.write_bytes(good[:-3])  # 截断
    with pytest.raises(frmod.FastresumeError):
        frmod.load_fastresume(p)
    p.write_bytes(good + b"junk")  # 尾部残留
    with pytest.raises(frmod.FastresumeError):
        frmod.load_fastresume(p)
    p.write_bytes(frmod.bencode([1, 2]))  # 顶层非字典
    with pytest.raises(frmod.FastresumeError):
        frmod.load_fastresume(p)


# ---------------------------------------------------------------------------
# 定位
# ---------------------------------------------------------------------------


def test_locate_direct_hits_v1_priority(tmp_path):
    d = tmp_path / "BT_backup"
    d.mkdir()
    tb = _torrent_bytes()
    v1, v2, _ = compute_infohashes(tb)
    (d / f"{v1}.fastresume").write_bytes(b"v1")
    (d / f"{v2}.fastresume").write_bytes(b"v2")

    assert frmod.locate_fastresume(d, v1, v2) == d / f"{v1}.fastresume"  # v1 优先
    assert frmod.locate_fastresume(d, "", v2) == d / f"{v2}.fastresume"  # 仅 v2 身份
    # v2-only 命名形态(v2-only 种子 fastresume 按 v2 hash 落名)
    assert frmod.locate_fastresume(str(d), "", v2) == d / f"{v2}.fastresume"


def test_locate_hybrid_falls_back_to_torrent_scan(tmp_path):
    d = tmp_path / "BT_backup"
    d.mkdir()
    tb = _torrent_bytes()
    v1, v2, _ = compute_infohashes(tb)
    stem = "cafe0001"  # 文件名不含任何身份 hash(不猜命名的形态)
    assert _write_torrent_pair(d, tb, stem) == v1

    assert frmod.locate_fastresume(d, v1, "") == d / f"{stem}.fastresume"
    assert frmod.locate_fastresume(d, "", v2) == d / f"{stem}.fastresume"
    assert frmod.locate_fastresume(d, v1, v2) == d / f"{stem}.fastresume"
    # .torrent 在场但 .fastresume 缺席 -> None
    (d / f"{stem}.fastresume").unlink()
    assert frmod.locate_fastresume(d, v1, "") is None


def test_locate_none_cases(tmp_path):
    d = tmp_path / "BT_backup"
    d.mkdir()
    v1, v2, _ = compute_infohashes(_torrent_bytes())
    assert frmod.locate_fastresume("", v1, v2) is None  # 空目录串(未配置)
    assert frmod.locate_fastresume(tmp_path / "nope", v1, v2) is None  # 目录不存在
    assert frmod.locate_fastresume(d, "", "") is None  # 双 hash 全空(无身份)
    _write_torrent_pair(d, _torrent_bytes(), "aa00")
    assert frmod.locate_fastresume(d, "f" * 40, "") is None  # 库内无匹配
    assert frmod.locate_fastresume(d, "", "0" * 64) is None


# ---------------------------------------------------------------------------
# 双键改写
# ---------------------------------------------------------------------------


def test_rewrite_dual_keys_flavor_preserved_and_pure():
    val = _manual_dict()
    snapshot = dict(val)
    out, oc = frmod.rewrite_save_paths(val, OLD, NEW)
    assert val == snapshot  # 纯函数: 入参不被原地修改
    assert oc.rewritten == ("save_path", "qBt-savePath", "qBt-downloadPath")
    assert oc.already == () and oc.unmatched == ()
    assert out[b"save_path"] == rb"T:\pt\member"  # lt 键保反斜杠风味(N1 实测)
    assert out[b"qBt-savePath"] == b"T:/pt/member"  # qBt 键保正斜杠风味
    assert out[b"qBt-downloadPath"] == b"T:/pt"
    assert out[b"qBt-name"] == val[b"qBt-name"] and out[b"completed"] == 1  # 无关键不动


def test_rewrite_downloadpath_independent():
    # 未完成种: downloadPath = 老根下独立下载目录, 与 save_path 不同值
    val = {
        b"save_path": rb"R:\qbt-fake\n1",
        b"qBt-savePath": b"R:/qbt-fake/n1",
        b"qBt-downloadPath": b"R:/qbt-fake/n1/incoming",
    }
    out, oc = frmod.rewrite_save_paths(val, OLD, NEW)
    assert oc.rewritten == ("save_path", "qBt-savePath", "qBt-downloadPath")
    assert out[b"save_path"] == rb"T:\pt"
    assert out[b"qBt-downloadPath"] == b"T:/pt/incoming"  # 自身前缀替换, 不抄 save_path 新值
    # 下载目录在老根之外(独立挂载点)-> 不匹配即跳过, 不被搬动
    val2 = {
        b"save_path": rb"R:\qbt-fake\n1",
        b"qBt-savePath": b"R:/qbt-fake/n1",
        b"qBt-downloadPath": b"S:/dl-cache",
    }
    out2, oc2 = frmod.rewrite_save_paths(val2, OLD, NEW)
    assert oc2.unmatched == ("qBt-downloadPath", )
    assert out2[b"qBt-downloadPath"] == b"S:/dl-cache"


def test_rewrite_boundary_and_flavor_variants():
    # 等值命中 -> 整串替换为新根
    out, oc = frmod.rewrite_save_paths({b"save_path": OLD.encode()}, OLD, NEW)
    assert out[b"save_path"] == NEW.encode() and oc.rewritten == ("save_path", )
    # 子目录命中
    out, _ = frmod.rewrite_save_paths({b"save_path": (OLD + "\\sub").encode()}, OLD, NEW)
    assert out[b"save_path"] == (NEW + "\\sub").encode()
    # 分量边界: R:\\database 不被 R:\\data 前缀误吞(前缀替换而非子串替换)
    out, oc = frmod.rewrite_save_paths({b"save_path": rb"R:\qbt-fake\n1db\x"}, OLD, NEW)
    assert oc.unmatched == ("save_path", ) and out[b"save_path"] == rb"R:\qbt-fake\n1db\x"
    # 混合分隔符值: 命中反斜杠变体, 命中点之后尾巴逐字节保留
    mixed = rb"R:\qbt-fake\n1/mixed\sub"
    out, oc = frmod.rewrite_save_paths({b"save_path": mixed}, OLD, NEW)
    assert oc.rewritten == ("save_path", ) and out[b"save_path"] == rb"T:\pt/mixed\sub"
    # 新根是旧根扩串(R:\\data -> R:\\data2): 已在新根的值判 already, 不被旧根二次吞改
    out, oc = frmod.rewrite_save_paths({b"save_path": rb"R:\qbt-fake\n1db\x"}, OLD, OLD + "db")
    assert oc.already == ("save_path", ) and out[b"save_path"] == rb"R:\qbt-fake\n1db\x"


def test_rewrite_idempotent_skips_already_at_target():
    val = _manual_dict()
    once, oc1 = frmod.rewrite_save_paths(val, OLD, NEW)
    assert oc1.rewritten == ("save_path", "qBt-savePath", "qBt-downloadPath")
    twice, oc2 = frmod.rewrite_save_paths(once, OLD, NEW)
    assert oc2.rewritten == () and oc2.already == ("save_path", "qBt-savePath", "qBt-downloadPath")
    assert twice == once  # 幂等(黄金法则 1)
    # 嵌套根(old 是 new 的前缀): 已在 new 下的值先判 already, 防旧根二次吞改
    nested_once, noc1 = frmod.rewrite_save_paths(
        {
            b"save_path": rb"R:\a\b\x",
            b"qBt-savePath": b"R:/a/b/x"
        }, r"R:\a", r"R:\a\b"
    )
    assert noc1.already == ("save_path", "qBt-savePath") and nested_once[b"save_path"] == rb"R:\a\b\x"
    fresh, fnoc = frmod.rewrite_save_paths({b"save_path": rb"R:\a\x", b"qBt-savePath": b"R:/a/x"}, r"R:\a", r"R:\a\b")
    assert fnoc.rewritten == ("save_path", "qBt-savePath")
    assert fresh[b"save_path"] == rb"R:\a\b\x" and fresh[b"qBt-savePath"] == b"R:/a/b/x"


def test_rewrite_relative_save_path_skipped():
    # N10 实测: 跨卷 setLocation 把 lt save_path 写成 CWD 相对路径, qBt 键保持绝对
    val = {b"save_path": b"downloads\\iso", b"qBt-savePath": b"R:/qbt-fake/n1/member"}
    out, oc = frmod.rewrite_save_paths(val, OLD, NEW)
    assert oc.unmatched == ("save_path", )
    assert out[b"save_path"] == b"downloads\\iso"  # 原样保留, 绝不重推导绝对路径
    assert oc.rewritten == ("qBt-savePath", )
    assert out[b"qBt-savePath"] == b"T:/pt/member"


def test_rewrite_autotmm_form():
    # N8 实测: AutoTMM 成员无 qBt-savePath/qBt-downloadPath 键(55 vs 57 键)
    val = {b"save_path": rb"R:\qbt-fake\n1", b"qBt-queueing": b"0", b"completed": 1}
    out, oc = frmod.rewrite_save_paths(val, OLD, NEW)
    assert oc.rewritten == ("save_path", ) and oc.already == () and oc.unmatched == ()
    assert out[b"save_path"] == rb"T:\pt"
    assert b"qBt-savePath" not in out and b"qBt-downloadPath" not in out
    assert out[b"qBt-queueing"] == b"0"


def test_rewrite_fail_fast_on_bad_roots():
    with pytest.raises(ValueError):
        frmod.rewrite_save_paths(_manual_dict(), "", NEW)
    with pytest.raises(ValueError):
        frmod.rewrite_save_paths(_manual_dict(), OLD, "")
    with pytest.raises(ValueError):
        frmod.rewrite_save_paths(_manual_dict(), OLD, OLD)
    # 仅分隔符风味不同 = 同一路径两种写法, 无差异可改 -> 全键 unmatched 零改写
    out, oc = frmod.rewrite_save_paths(_manual_dict(), OLD, OLD.replace("\\", "/"))
    assert oc.rewritten == () and out == _manual_dict()


# ---------------------------------------------------------------------------
# 安全三件套(写)
# ---------------------------------------------------------------------------


def test_save_roundtrip_and_no_tmp_residue(tmp_path):
    # ~60 键含嵌套(N2「键数不变」角度): 重读逐键相等, 无临时残留
    val = _manual_dict()
    for i in range(55):
        val[f"qBt-filler{i}".encode()] = i if i % 3 else [i, {b"k": b"v"}]
    p = tmp_path / "h.fastresume"
    frmod.save_fastresume(p, val)
    assert frmod.load_fastresume(p) == val
    assert list(tmp_path.glob("*.aqtmp")) == []
    assert p.read_bytes()[:1] == b"d"


def test_save_roundtrip_guard_blocks_corrupt_payload(tmp_path, monkeypatch):
    p = tmp_path / "h.fastresume"
    p.write_bytes(frmod.bencode(_manual_dict()))
    before = p.read_bytes()
    monkeypatch.setattr(frmod, "bencode", lambda _v: b"corrupt-payload")  # 注入坏编码产物

    with pytest.raises(frmod.FastresumeError):
        frmod.save_fastresume(p, _manual_dict())

    assert p.read_bytes() == before  # 磁盘零触碰(N6: 坏 bencode 绝不落盘)
    assert list(tmp_path.glob("*.aqtmp")) == [] and list(tmp_path.glob("*.bak")) == []


def test_save_bak_and_restore_rollback(tmp_path):
    p = tmp_path / "deadbeef.fastresume"
    pre_edit = frmod.bencode(_manual_dict())
    p.write_bytes(pre_edit)

    moved, _ = frmod.rewrite_save_paths(_manual_dict(), OLD, NEW)
    frmod.save_fastresume(p, moved)
    bak = frmod.backup_path_of(p)
    assert bak == tmp_path / "deadbeef.fastresume.bak" and bak.read_bytes() == pre_edit  # D7 命名
    assert frmod.load_fastresume(p)[b"save_path"] == rb"T:\pt\member"

    assert frmod.restore_backup(p) is True  # 回滚 = 覆盖回原名(D7)
    assert p.read_bytes() == pre_edit
    assert frmod.restore_backup(tmp_path / "no-bak.fastresume") is False


# ---------------------------------------------------------------------------
# retarget 单成员一步到位
# ---------------------------------------------------------------------------


def test_retarget_end_to_end_written_then_unchanged(tmp_path):
    d = tmp_path / "BT_backup"
    d.mkdir()
    tb = _torrent_bytes()
    v1, v2, _ = compute_infohashes(tb)
    (d / f"{v1}.fastresume").write_bytes(frmod.bencode(_manual_dict()))
    (d / f"{v1}.torrent").write_bytes(tb)

    rep = frmod.retarget(d, v1, v2, OLD, NEW)
    assert rep.status == "written"
    assert Path(rep.path) == d / f"{v1}.fastresume"
    assert set(rep.rewritten) == {"save_path", "qBt-savePath", "qBt-downloadPath"}
    back = frmod.load_fastresume(rep.path)
    assert back[b"save_path"] == rb"T:\pt\member" and back[b"qBt-savePath"] == b"T:/pt/member"
    assert back[b"qBt-downloadPath"] == b"T:/pt"
    assert frmod.backup_path_of(Path(rep.path)).is_file()  # .bak 在场

    fp = Path(rep.path)
    before_bytes, before_mtime = fp.read_bytes(), fp.stat().st_mtime_ns
    rep2 = frmod.retarget(d, v1, v2, OLD, NEW)
    assert rep2.status == "unchanged" and rep2.rewritten == ()  # 幂等重放
    assert rep2.already == ("save_path", "qBt-savePath", "qBt-downloadPath")
    assert fp.read_bytes() == before_bytes and fp.stat().st_mtime_ns == before_mtime  # 零落盘


def test_retarget_not_found_and_malformed_propagation(tmp_path):
    d = tmp_path / "BT_backup"
    d.mkdir()
    tb = _torrent_bytes()
    v1, v2, _ = compute_infohashes(tb)
    p = d / f"{v1}.fastresume"
    p.write_bytes(b"\x00garbage-not-bencode")  # N6 形态: 坏样本
    (d / f"{v1}.torrent").write_bytes(tb)

    assert frmod.retarget(d, "f" * 40, "", OLD, NEW).status == "not_found"  # 身份不符不抛

    before = p.read_bytes()
    with pytest.raises(frmod.FastresumeError):
        frmod.retarget(d, v1, v2, OLD, NEW)  # 坏样本上抛
    assert p.read_bytes() == before  # 原文件零触碰
    assert list(d.glob("*.bak")) == [] and list(d.glob("*.aqtmp")) == []  # 无备份无残留
