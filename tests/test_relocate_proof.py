"""test_relocate_proof 测试计划: 同机判据的路径级证据(D 目录元数据比对 + B′ 降级)
(计划 26-11-04-0055 §03.1/§04 P3 前半 —— relocate_proof.py 的 path_evidence/最近存在祖先)

替身形态: qB 侧用 SimpleNamespace(api=SimpleNamespace(client=替身)), 替身只实现
app_get_directory_content(响应形状按报告 26-11-03-2306 §8.1 实测: withMetadata=true
回对象数组 name/size/last_modification_date, 未开启回纯路径字符串数组); 本机侧用
真临时目录(os.scandir/os.stat 走真实 FS)。404/400 用 qbittorrentapi 真异常类
(NotFound404Error/InvalidRequest400Error)—— 生产代码只按「异常 => unavailable」
兜, 异常类型本身不进判定。

## 测试计划(每个测试函数一条)
- test_d_metadata_equal_positive: D 级元数据相等 -> positive(级 D); withMetadata 钉死字符串 "true";
  directory_path 原样透传 qB 视角路径
- test_d_all_mismatch_negative: 抽中代表文件 size/mtime 全不等 -> negative(级 D), detail 带文件名
- test_d_qb_only_name_negative: qB 独有文件名(本机没有)算不等 -> negative
- test_d_plain_list_unavailable: 纯字符串列表(withMetadata 未生效) -> unavailable -> B′ 降级
- test_d_404_degrades_to_bprime: NotFound404Error -> D unavailable; B′ 元数据 size 相等 -> positive(级 B′)
- test_d_400_unavailable_final: InvalidRequest400Error 且无文件清单 -> unavailable(B′ 同样不可判定)
- test_with_metadata_kwarg_pinned: 捕获 kwargs 断言 with_metadata == "true"(字符串; True/"1" 实测不算开启)
- test_d_sample_k_stride: 条目多于 k 时均匀步长抽 k=3(首/中/尾): 抽中全等 -> positive,
  未抽中的不等不影响; 反向(抽中全不等、未抽中相等)-> negative —— 钉住抽样语义
- test_d_directory_entries_skipped: qB type 为目录/本机侧是目录的条目剔除; 剔完无可比文件 -> unavailable
- test_d_local_unreadable_unavailable: 本机目录不可读 -> unavailable -> B′ 降级
- test_bprime_positive_negative_unavailable: B′ 三态: 任一 size 相等 positive / stat 成功但全等不上
  negative / 文件全读不到 unavailable; 文件数受 BPRIME_MAX_FILES 截断
- test_bprime_runs_without_client: 客户端缺失时仍走 B′(files 是已取回的元数据)
- test_dst_visibility_only: dst 口径: 列目录成功即 positive(空目录/纯字符串列表都算); 客户端缺失 unavailable
- test_nearest_existing_ancestor: 叶子不存在上溯最近存在祖先 / 首层可用原样返回 / 全链不可用 None
- test_evidence_constants: 三态与级别常量取值钉住(稳定字符串, 调用方按值分支)
- test_sample_helper_deterministic: _sample 短表原样 / k<=1 取首 / 长表均匀步长且确定性
- test_d_mtime_size_pairwise: size/mtime 任一分量不等即不等(完全相等才 positive)
- test_d_malformed_mtime_no_raise: last_modification_date 为 None/数字字符串/浮点/畸形串时
  数值化守卫兜住(可数值化按 int(float(x)) 参与比对, 畸形按该条不等跳过) —— 单条坏条目不抛不炸预检
### P4 F 运行时兜底(计划 26-11-04-0055 §04 P4): link_follow_evidence
- test_link_follow_positive_negative_unavailable: 一致 positive / 全不等 negative / 404 unavailable
  (不降级 B′ —— B′ 与「链接是否被跟随」无关)
- test_link_follow_name_filter: names 过滤到本组文件(无关条目不进比对) / 过滤后无条目 unavailable
  / 空 names 不过滤(既有 D 级语义)
- test_link_follow_no_client_unavailable: 客户端缺失 / 客户端无该方法(qB<5.0 替身) -> unavailable
"""

import os
import types

import pytest
from qbittorrentapi.exceptions import InvalidRequest400Error, NotFound404Error

from auto_qb.core.modules import relocate_proof as rp

MT = 1700000000  # 固定 mtime(报告实测口径: qB last_modification_date 与本机 st_mtime 同为 UTC 秒)


def _make_file(root, name, size, mtime=MT):
    p = os.path.join(str(root), *name.split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(b"x" * size)
    os.utime(p, (mtime, mtime))
    return p


def _entry(name, size, mtime=MT, typ="File"):
    return {"name": name, "size": size, "last_modification_date": mtime, "type": typ}


class _DirClient:
    """app_get_directory_content 替身: 回预制条目 / 抛指定异常, 并记录调用参数"""
    def __init__(self, entries=None, error=None):
        self.calls = []
        self._entries = entries
        self._error = error

    def app_get_directory_content(self, directory_path=None, with_metadata=None, **kw):
        self.calls.append({"directory_path": directory_path, "with_metadata": with_metadata})
        if self._error is not None:
            raise self._error
        return list(self._entries or [])


def _ctx(client):
    return types.SimpleNamespace(api=types.SimpleNamespace(client=client))


def _plain_client():
    """无 app_get_directory_content 的客户端(旧版 qB / 未实现该方法的替身)"""
    class _Bare:
        pass

    return _Bare()


# ---------- D 级 ----------


def test_d_metadata_equal_positive(tmp_path):
    """D 级元数据相等 -> positive(级 D); withMetadata 钉死字符串 "true"; dirPath 透传"""
    _make_file(tmp_path, "a.txt", 100)
    client = _DirClient([_entry("a.txt", 100, MT)])
    ev = rp.path_evidence(_ctx(client), str(tmp_path), str(tmp_path))
    assert ev.status == rp.POSITIVE and ev.level == rp.LEVEL_D
    assert "a.txt" in ev.detail
    assert client.calls[0]["directory_path"] == str(tmp_path)
    assert client.calls[0]["with_metadata"] == "true"  # 实测坑: 必须字符串 "true"(报告 §8.1)


def test_d_all_mismatch_negative(tmp_path):
    """抽中代表文件 size/mtime 全不等 -> negative(级 D), detail 带文件名"""
    _make_file(tmp_path, "a.txt", 100)
    client = _DirClient([_entry("a.txt", 999, MT), _entry("a.txt", 100, MT + 5)])
    ev = rp.path_evidence(_ctx(client), str(tmp_path), str(tmp_path))
    assert ev.status == rp.NEGATIVE and ev.level == rp.LEVEL_D
    assert "a.txt" in ev.detail


def test_d_qb_only_name_negative(tmp_path):
    """qB 独有文件名(本机没有)算不等 -> negative(同一命名空间不该有单侧独有条目)"""
    _make_file(tmp_path, "a.txt", 100)
    client = _DirClient([_entry("ghost.bin", 7, MT)])
    ev = rp.path_evidence(_ctx(client), str(tmp_path), str(tmp_path))
    assert ev.status == rp.NEGATIVE and ev.level == rp.LEVEL_D


def test_d_plain_list_unavailable(tmp_path):
    """纯字符串列表(withMetadata 未生效) -> unavailable -> B′ 降级(文件 size 相等 -> positive B′)"""
    _make_file(tmp_path, "a.txt", 100)
    client = _DirClient(["a.txt"])
    ev = rp.path_evidence(_ctx(client), str(tmp_path), str(tmp_path), files=[("a.txt", 100)])
    assert ev.status == rp.POSITIVE and ev.level == rp.LEVEL_BPRIME
    # 无文件清单时保留 D 级不可判定原因
    ev2 = rp.path_evidence(_ctx(client), str(tmp_path), str(tmp_path))
    assert ev2.status == rp.UNAVAILABLE and "纯路径列表" in ev2.detail


def test_d_404_degrades_to_bprime(tmp_path):
    """NotFound404Error -> D unavailable; B′ 元数据 size 相等 -> positive(级 B′)"""
    _make_file(tmp_path, "a.txt", 100)
    client = _DirClient(error=NotFound404Error("目录不存在"))
    ev = rp.path_evidence(_ctx(client), str(tmp_path), str(tmp_path), files=[("a.txt", 100)])
    assert ev.status == rp.POSITIVE and ev.level == rp.LEVEL_BPRIME
    assert "弱证据" in ev.detail  # B′ 文案自带弱证据说明


def test_d_400_unavailable_final(tmp_path):
    """InvalidRequest400Error 且无文件清单 -> unavailable(注明 B′ 降级同样不可判定)"""
    client = _DirClient(error=InvalidRequest400Error("bad request"))
    ev = rp.path_evidence(_ctx(client), str(tmp_path), str(tmp_path))
    assert ev.status == rp.UNAVAILABLE and ev.level == ""
    assert "B′ 降级同样不可判定" in ev.detail


def test_with_metadata_kwarg_pinned(tmp_path):
    """with_metadata kwarg 恒为字符串 "true"(True/"1"/false 实测都被 qB 当未开启)"""
    _make_file(tmp_path, "a.txt", 100)
    client = _DirClient([_entry("a.txt", 100, MT)])
    rp.path_evidence(_ctx(client), str(tmp_path), str(tmp_path), visibility_only=True)
    assert client.calls[0]["with_metadata"] == "true"
    assert isinstance(client.calls[0]["with_metadata"], str)


def test_d_sample_k_stride(tmp_path):
    """抽样 k 语义: 条目多于 k 时均匀步长抽 k=3(首/中/尾); 抽中全等 positive,
    未抽中的不等不影响; 反向抽中全不等 negative —— 钉住「抽代表」不是「全量」"""
    names = [f"f{i}.bin" for i in range(5)]
    for n in names:
        _make_file(tmp_path, n, 10)
    # f0/f2/f4 相等, f1/f3 不等 -> 步长抽样(0,2,4)全中 -> positive(全量比对会判负)
    client = _DirClient(
        [
            _entry(names[0], 10),
            _entry(names[1], 999),
            _entry(names[2], 10),
            _entry(names[3], 999),
            _entry(names[4], 10)
        ]
    )
    ev = rp.path_evidence(_ctx(client), str(tmp_path), str(tmp_path))
    assert ev.status == rp.POSITIVE, ev
    # 反向: f0/f2/f4 全不等, f1/f3 相等 -> 抽样判负(钉住确实只抽 k 个)
    client2 = _DirClient(
        [
            _entry(names[0], 999),
            _entry(names[1], 10),
            _entry(names[2], 999),
            _entry(names[3], 10),
            _entry(names[4], 999)
        ]
    )
    ev2 = rp.path_evidence(_ctx(client2), str(tmp_path), str(tmp_path))
    assert ev2.status == rp.NEGATIVE, ev2
    # 条目不多于 k 时全量比对: 2 条 1 等 1 不等 -> positive
    client3 = _DirClient([_entry("f0.bin", 10), _entry("f1.bin", 999)])
    ev3 = rp.path_evidence(_ctx(client3), str(tmp_path), str(tmp_path))
    assert ev3.status == rp.POSITIVE, ev3


def test_d_directory_entries_skipped(tmp_path):
    """目录条目剔除(qB 对目录 size 语义未实测): 混合目录条目不影响判定;
    剔完无可比文件 -> unavailable 走 B′"""
    _make_file(tmp_path, "a.txt", 100)
    os.makedirs(os.path.join(str(tmp_path), "sub"))
    client = _DirClient([_entry("sub", 0, MT, typ="Folder"), _entry("a.txt", 100, MT)])
    ev = rp.path_evidence(_ctx(client), str(tmp_path), str(tmp_path))
    assert ev.status == rp.POSITIVE, ev
    # 只剩目录条目: 无可比 -> 降级 B′(文件清单相等则 positive)
    client2 = _DirClient([_entry("sub", 0, MT, typ="Folder")])
    ev2 = rp.path_evidence(_ctx(client2), str(tmp_path), str(tmp_path), files=[("a.txt", 100)])
    assert ev2.status == rp.POSITIVE and ev2.level == rp.LEVEL_BPRIME


def test_d_local_unreadable_unavailable(tmp_path):
    """本机目录不可读(os.scandir 失败) -> D unavailable; 无文件清单时 B′ 同样不可判定"""
    ghost_dir = str(tmp_path / "no-such-dir")
    client = _DirClient([_entry("a.txt", 100, MT)])
    ev = rp.path_evidence(_ctx(client), ghost_dir, ghost_dir)
    assert ev.status == rp.UNAVAILABLE
    assert "本机目录不可读" in ev.detail and "B′ 降级同样不可判定" in ev.detail


# ---------- B′ 级 ----------


def test_bprime_positive_negative_unavailable(tmp_path):
    """B′ 三态 + 截断: 任一 size 相等 positive / stat 成功但全不等 negative /
    全读不到 unavailable; 文件清单受 BPRIME_MAX_FILES 截断"""
    _make_file(tmp_path, "hit.bin", 100)
    _make_file(tmp_path, "miss.bin", 200)
    ev = rp._bprime_evidence(str(tmp_path), [("hit.bin", 999), ("miss.bin", 200)])
    assert ev.status == rp.POSITIVE  # 任一相等即 positive(首个 miss 不影响)
    ev1 = rp._bprime_evidence(str(tmp_path), [("hit.bin", 100)])
    assert ev1.status == rp.POSITIVE and ev1.level == rp.LEVEL_BPRIME
    ev2 = rp._bprime_evidence(str(tmp_path), [("hit.bin", 999), ("miss.bin", 999)])
    assert ev2.status == rp.NEGATIVE and "2 个文件" in ev2.detail
    ev3 = rp._bprime_evidence(str(tmp_path), [("ghost.bin", 1)])
    assert ev3.status == rp.UNAVAILABLE
    ev4 = rp._bprime_evidence(str(tmp_path), [])
    assert ev4.status == rp.UNAVAILABLE and "无文件清单" in ev4.detail
    # 截断: 超上限的条目不参与(全部真实存在但 size 声明不符; 截断把命中档排除 => 判负)
    for i in range(rp.BPRIME_MAX_FILES):
        _make_file(tmp_path, f"g{i}.bin", 10)
    many = [(f"g{i}.bin", 999) for i in range(rp.BPRIME_MAX_FILES)] + [("hit.bin", 100)]
    ev5 = rp._bprime_evidence(str(tmp_path), many)
    assert ev5.status == rp.NEGATIVE


def test_bprime_runs_without_client(tmp_path):
    """客户端缺失时仍走 B′(files 是调用方已取回的种子元数据, 不依赖此刻客户端)"""
    _make_file(tmp_path, "a.txt", 100)
    ev = rp.path_evidence(_ctx(_plain_client()), str(tmp_path), str(tmp_path), files=[("a.txt", 100)])
    assert ev.status == rp.POSITIVE and ev.level == rp.LEVEL_BPRIME


# ---------- dst 侧可见性 ----------


def test_dst_visibility_only(tmp_path):
    """dst 口径(visibility_only): 列目录成功即 positive —— 空目录/纯字符串列表都算;
    客户端缺失 -> unavailable(B′ 对 dst 无意义)"""
    client = _DirClient([])
    ev = rp.path_evidence(_ctx(client), str(tmp_path), str(tmp_path), visibility_only=True)
    assert ev.status == rp.POSITIVE and ev.level == rp.LEVEL_D
    client2 = _DirClient(["a.txt", "b/"])
    ev2 = rp.path_evidence(_ctx(client2), str(tmp_path), str(tmp_path), visibility_only=True)
    assert ev2.status == rp.POSITIVE
    ev3 = rp.path_evidence(_ctx(_plain_client()), str(tmp_path), str(tmp_path), visibility_only=True)
    assert ev3.status == rp.UNAVAILABLE


# ---------- 最近存在祖先 ----------


def test_nearest_existing_ancestor(tmp_path, monkeypatch):
    """上溯: 叶子不存在 -> 最近存在祖先; 首层可用 -> 原样; 全链不可用 -> None
    (与 _volume_free_resolved 同一 disk_usage 判据, 故用桩替身按层抛错)"""
    from auto_qb.infra import file_access as fa_mod

    fa = fa_mod.LocalFileAccess()  # 直跑实现单测(不经全局单例 —— 映射测试可能换过它)
    assert rp.nearest_existing_ancestor(fa, str(tmp_path)) == str(tmp_path)
    leaf = os.path.join(str(tmp_path), "not-yet-created")
    assert rp.nearest_existing_ancestor(fa, leaf) == str(tmp_path)

    class _Layered:
        """b 层抛错、a 层可用的替身(verify 上溯停在最深可用层)"""
        def disk_usage(self, p):
            if str(p).replace("\\", "/").rstrip("/").endswith("/b"):
                raise OSError("no such dir")
            return None

    assert rp.nearest_existing_ancestor(_Layered(), "X:/a/b") == os.path.normpath("X:/a")

    class _NoDisk:
        def disk_usage(self, p):
            raise OSError("no disk")

    assert rp.nearest_existing_ancestor(_NoDisk(), "X:/a/b") is None


def test_evidence_constants():
    """三态与级别常量钉值(稳定字符串: 调用方按值分支, 改名即破坏兼容)"""
    assert (rp.POSITIVE, rp.NEGATIVE, rp.UNAVAILABLE) == ("positive", "negative", "unavailable")
    assert rp.LEVEL_D == "D" and rp.LEVEL_BPRIME == "B'"
    assert rp.PROOF_SAMPLE_K == 3
    assert rp.WITH_METADATA == "true"


def test_sample_helper_deterministic():
    """_sample: 短表原样 / k<=1 取首 / 长表均匀步长且确定性(两次一致)"""
    seq = list(range(10))
    assert rp._sample(seq, 3) == [0, 4, 9]  # 步长 4.5: round 银行家舍入取 4(确定性即可, 钉住现值)
    assert rp._sample([7], 3) == [7]
    assert rp._sample(seq, 1) == [0]
    assert rp._sample(seq, 3) == rp._sample(seq, 3)


@pytest.mark.parametrize(
    "size,mtime,expect", [
        (100, MT, rp.POSITIVE),
        (100, MT + 1, rp.NEGATIVE),
        (101, MT, rp.NEGATIVE),
    ]
)
def test_d_mtime_size_pairwise(tmp_path, size, mtime, expect):
    """size/mtime 任一分量不等即不等(完全相等才 positive; 报告实测 mtime 无时区偏差)"""
    _make_file(tmp_path, "a.txt", 100, MT)
    client = _DirClient([_entry("a.txt", size, mtime)])
    ev = rp.path_evidence(_ctx(client), str(tmp_path), str(tmp_path))
    assert ev.status == expect, ev


@pytest.mark.parametrize(
    "mtime,expect",
    [
        (None, rp.NEGATIVE),  # None: 按该条不等跳过, 不抛
        ("garbage", rp.NEGATIVE),  # 畸形串: 同上
        (str(MT), rp.POSITIVE),  # 数字字符串: int(float(x)) 数值化后相等
        (str(MT) + ".7", rp.POSITIVE),  # 字符串小数: 同上(亚秒截断)
        (MT + 0.4, rp.POSITIVE),  # 浮点形态: int(float(x)) 截断后相等
    ]
)
def test_d_malformed_mtime_no_raise(tmp_path, mtime, expect):
    """last_modification_date 形态不稳(None/数字字符串/浮点/畸形): 数值化守卫兜住,
    一条坏条目只按「该条不等」跳过, 绝不 TypeError/ValueError 打穿 relocate_precheck"""
    _make_file(tmp_path, "a.txt", 100, MT)
    client = _DirClient([_entry("a.txt", 100, mtime)])
    ev = rp.path_evidence(_ctx(client), str(tmp_path), str(tmp_path))
    assert ev.status == expect, ev


# ---------- 链接跟随自检(P4 F 运行时兜底, 计划 26-11-04-0055 §04 P4) ----------


def test_link_follow_positive_negative_unavailable(tmp_path):
    """链接跟随三态: 一致 positive / 全不等 negative / 404 unavailable(不降级 B′)"""
    _make_file(tmp_path, "a.txt", 100)
    ev = rp.link_follow_evidence(_ctx(_DirClient([_entry("a.txt", 100)])), "qbsrc", str(tmp_path), names=["a.txt"])
    assert ev.status == rp.POSITIVE and ev.level == rp.LEVEL_D, ev
    ev = rp.link_follow_evidence(_ctx(_DirClient([_entry("a.txt", 999)])), "qbsrc", str(tmp_path), names=["a.txt"])
    assert ev.status == rp.NEGATIVE, ev
    # 端点不可用保持 unavailable —— 该函数没有 B′ 降级(B′ 证不了链接被跟随)
    ev = rp.link_follow_evidence(_ctx(_DirClient(error=NotFound404Error)), "qbsrc", str(tmp_path), names=["a.txt"])
    assert ev.status == rp.UNAVAILABLE and ev.level == "", ev


def test_link_follow_name_filter(tmp_path):
    """names 过滤: 无关条目不进比对 / 过滤后无条目 unavailable / 空 names 不过滤(既有 D 级语义)"""
    _make_file(tmp_path, "a.txt", 100)
    client = _DirClient([_entry("ghost.bin", 7), _entry("a.txt", 100)])
    ev = rp.link_follow_evidence(_ctx(client), "qbsrc", str(tmp_path), names=["a.txt"])
    assert ev.status == rp.POSITIVE, ev  # ghost.bin 被滤掉, 不拉低抽样
    ev = rp.link_follow_evidence(_ctx(_DirClient([_entry("ghost.bin", 7)])), "qbsrc", str(tmp_path), names=["a.txt"])
    assert ev.status == rp.UNAVAILABLE and "未见本组文件" in ev.detail, ev
    # 空 names: 不过滤 —— 独有名字算不等(与 path_evidence 的 D 级语义一致)
    ev = rp.link_follow_evidence(_ctx(_DirClient([_entry("ghost.bin", 7)])), "qbsrc", str(tmp_path))
    assert ev.status == rp.NEGATIVE, ev


def test_link_follow_no_client_unavailable():
    """客户端缺失 / 客户端无该方法(qB<5.0 替身) -> unavailable(调用方按跳过处理)"""
    ev = rp.link_follow_evidence(types.SimpleNamespace(api=types.SimpleNamespace(client=None)), "qbsrc", "nowhere")
    assert ev.status == rp.UNAVAILABLE and "客户端不可用" in ev.detail, ev
    ev = rp.link_follow_evidence(_ctx(_plain_client()), "qbsrc", "nowhere")
    assert ev.status == rp.UNAVAILABLE and ev.level == "", ev
