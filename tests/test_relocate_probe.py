"""test_relocate_probe 测试计划: 同机强探测 E1(假种一次性探测)
(计划 26-11-04-0055 §04 P2 —— relocate_probe.py 的指纹/造种/探测主函数/启动残留扫描)

替身形态: FakeClient 子类仿 tests/helpers.py 的 relocate_env/FakeTorrent 先例 ——
同机语义替身(_SameFsClient)把 recheck 译成 progress=1.0、setLocation 译成真搬目录;
超时类用例 monkeypatch relocate_probe 的超时常量到小值(常量是单点, 直接改模块属性)。
探测统一走 ctx.api(QbApi Facade, make_manager 装配), 不裸散 client。

## 测试计划(每个测试函数一条)
- test_probe_fingerprint_stable_and_sensitive: 指纹稳定可复现; host/port/username/password/api_key 任一变化即变; password 空时回落 api_key; 双空也稳定; 16 位十六进制
- test_build_probe_torrent_structure: 造种 4KiB/piece 16KiB/单 piece/无 tracker/无私有标志/体积约 102B, hr.bencode.bdecode 回读逐键核对
- test_probe_full_lifecycle_pass: 全生命通过(读证+写证+清理无残留): status=passed, evidence 齐全, qB 无种子, 两侧临时目录消失, cleanup 记录干净
- test_probe_add_params_isolated: add 参数钉死: is_stopped=True / autoTMM=False / save_path=src 临时子目录 / tags=aqb-probe / category 空
- test_probe_read_proof_timeout_failed_no_env: recheck 不进 1.0 => failed + env=False(缓存方向), 探针种子已清
- test_probe_write_proof_timeout_failed_no_env: dst 不出现(setLocation 无效果) => failed + env=False, 探针种子已清
- test_probe_write_mismatch_failed_no_env: dst 出现但内容不符 => write_mismatch + env=False, evidence 记 dst_seen
- test_probe_add_rejected_env: add 被拒 => failed + env=True(不缓存方向), 本机临时目录已清
- test_probe_api_error_env: recheck/recheck 轮询期 API 异常 => failed + env=True
- test_probe_torrent_invisible_env: add 受理但种子始终不可见 => failed + env=True
- test_probe_tag_fallback_delete_on_invisible: add 受理但探测窗口拿不到 hash => finally 按 tag
  补删探测种子(此刻可见则删成; 恒不可见则只告警留证)
- test_probe_passes_with_namespaced_view: 容器部署命名空间错位(fs.path_map: qB 视角 /qb/... 与
  本机视图不同, FS 实际共享)下 run_probe 仍 passed —— 本机读写侧经 map_to_container 换算
- test_probe_cleanup_runs_on_every_failure_path: 各阶段中断仍清理(本机写失败/add 拒/读证失败/delete 失败留证+warning 但不改结论)
- test_probe_timeout_budget_constants: 超时常量单点取值钉住(读 10s/写 10s/清理 5s/轮询 0.25s)
- test_sweep_probe_residue: 启动扫描清残留(种子+目录), 幂等二次为 0, 非本前缀目录不动
- test_sweep_residue_tag_only_no_delete_files: tag 命中但种子名/保存路径均不带 aqb-probe 前缀
  => 只删种子记录, delete_files=False(绝不误删用户数据); 目录侧保留现状
- test_start_hook_sweeps_residue: relocate 启动钩子: enabled 时清残留并在日志提及; disabled/dry_run 不动手
- test_lifecycle_mixin_wires_sweep: LifecycleMixin.start 源码里确实调用 sweep_probe_residue(钩子挂接不回退)

覆盖率缺口清偿(26-11-07, test.full 99.31% -> 99.5% 闸):
- test_probe_bencode_type_gates: _bencode 类型闸(bool 拒 / list 编码 / float 拒)
- test_probe_api_unavailable_env: ctx 无 api => 环境性失败 api_unavailable
- test_probe_tag_list_api_error_during_await: 可见性轮询期 API 异常 => api_error + env=True
- test_probe_recheck_poll_api_error_env: 读证轮询期 API 异常 => api_error + env=True
- test_probe_awaits_past_hashless_tag_entries: 轮询撞无 hash 条目跳过继续等
- test_probe_set_location_rejected_env: setLocation 被拒 => env=True
- test_probe_write_proof_copy_without_move_mismatch: dst 一致而 src 未消失 => 等到超时定 mismatch
- test_file_matches_oserror_is_false: 本机文件比对 OSError => 不一致不抛
- test_cleanup_tag_delete_matrix: 无 hash 清理四支(跳过/补删/补删炸/定位炸)
- test_cleanup_gone_poll_error_records_and_continues: 消失轮询炸留证继续目录清理
- test_cleanup_rmtree_failure_and_leftover: 目录清理失败 residue 留证
- test_sweep_probe_residue_list_error_returns_zero: 扫描列种子炸返回 0 不挡启动
- test_sweep_probe_residue_delete_failure_and_hashless: 残留删除失败继续/无 hash 条目不发删除
- test_sweep_probe_residue_dir_cleanup_failure_warns: 残留目录清理失败只告警
"""

import hashlib
import logging
import os
import shutil
import types
from types import SimpleNamespace
from unittest import mock

import pytest

from auto_qb.config.models import PathMapEntry, QbittorrentConfig
from auto_qb.core.modules import relocate_probe as rp
from auto_qb.core.modules.relocate_lifecycle import LifecycleMixin
from auto_qb.hr.bencode import bdecode
from auto_qb.infra import file_access
from helpers import FakeClient, FakeTorrent, capture_logs, make_manager

# ---------- 替身与环境 ----------


class _SameFsClient(FakeClient):
    """同机语义替身: recheck 即刻校验通过(progress=1.0), setLocation 真把 save_path 搬到 location

    仿 relocate_env/FakeTorrent 先例的"替身保真"口径: 探测轮询消费的 progress/本机文件
    都要跟着 qB 写操作走, 否则全生命用例没有真值可断言。set_location_mode 控制故障注入:
    "move"(默认, 同机 rename)/ "none"(dst 永不出现)/ "corrupt"(搬过去但内容截断)。
    """
    def __init__(self, set_location_mode="move"):
        super().__init__()
        self.set_location_mode = set_location_mode

    def torrents_recheck(self, torrent_hashes=None):
        super().torrents_recheck(torrent_hashes=torrent_hashes)
        for tor in self.torrents.values():  # 本替身里只有探测种子: recheck = 校验通过
            tor.progress = 1.0

    def torrents_set_location(self, torrent_hashes=None, location=None):
        super().torrents_set_location(torrent_hashes=torrent_hashes, location=location)
        if self.set_location_mode == "none":
            return
        for h in (torrent_hashes if isinstance(torrent_hashes, (list, tuple)) else [torrent_hashes]):
            tor = self.torrents.get(h)
            if tor is None or not os.path.isdir(tor.save_path):
                continue
            shutil.move(tor.save_path, location)
            if self.set_location_mode == "corrupt":  # 模拟跨卷复制截断: 文件在场但内容不符
                with open(os.path.join(location, os.listdir(location)[0]), "wb") as f:
                    f.write(b"corrupted")
            tor.save_path = location


class _BrokenRecheckClient(_SameFsClient):
    """recheck 被 qB 拒(环境性故障注入)"""
    def torrents_recheck(self, torrent_hashes=None):
        raise RuntimeError("422")


class _MuteListClient(FakeClient):
    """torrents_info 恒空: add 受理但种子永远不可见"""
    def torrents_info(self, torrent_hashes=None, **kw):
        return []


class _NamespacedClient(_SameFsClient):
    """命名空间错位替身(容器部署形态): qB 记账用逻辑路径(/qb/...), 物理搬目录经
    file_access.map_to_container 换算本机真实路径 —— 模拟「FS 实际共享、仅视角不同」;
    修复前 run_probe 直用 qB 视角路径做本机读写, 该替身下必然证写超时(env=False)"""
    def _mp(self, p):
        fa = file_access.get_file_access()
        return fa.map_to_container(p) or p

    def torrents_set_location(self, torrent_hashes=None, location=None):
        FakeClient.torrents_set_location(self, torrent_hashes=torrent_hashes, location=location)  # 记台账
        for h in (torrent_hashes if isinstance(torrent_hashes, (list, tuple)) else [torrent_hashes]):
            tor = self.torrents.get(h)
            if tor is None or not os.path.isdir(self._mp(tor.save_path)):
                continue
            shutil.move(self._mp(tor.save_path), self._mp(location))  # qB 物理侧在容器挂载点
            tor.save_path = location


def _env(tmp_path, client=None):
    """探测用最小环境: bare manager + FakeClient + 真实 src/dst 目录; 返回 (ctx, client, src, dst)

    client 缺省 = 原生 FakeClient(recheck 不改 progress / setLocation 不搬文件)—— 失败类用例
    靠它天然造出"FS 不可达"; 全生命通过类用例显式传 _SameFsClient。
    """
    mgr = make_manager(os.path.join(str(tmp_path), "state.json"), bare=True, client=client or FakeClient())
    src = os.path.join(str(tmp_path), "src")
    dst = os.path.join(str(tmp_path), "dst")
    os.makedirs(src, exist_ok=True)  # 同一用例可多次 _env(start 钩子三分支), 目录共存
    os.makedirs(dst, exist_ok=True)
    return mgr.ctx, mgr.client, src, dst


@pytest.fixture()
def fast_timeouts(monkeypatch):
    """超时常量压到小值: 轮询立刻到期, 测试不真等(超时/轮询语义仍走同一条代码路径)"""
    monkeypatch.setattr(rp, "PROBE_READ_TIMEOUT_S", 0.3)
    monkeypatch.setattr(rp, "PROBE_WRITE_TIMEOUT_S", 0.3)
    monkeypatch.setattr(rp, "PROBE_CLEANUP_TIMEOUT_S", 0.3)
    monkeypatch.setattr(rp, "PROBE_POLL_INTERVAL_S", 0.01)


def _probe_torrents(client):
    """替身客户端里打 tag 的种子(qB 侧真值)"""
    return [t for t in client.torrents.values() if "aqb-probe" in (t.tags or "").split(",")]


# ---------- 指纹 ----------


def test_probe_fingerprint_stable_and_sensitive():
    """指纹稳定可复现; 任一凭据字段变化即变; password 空回落 api_key; 双空稳定; 16 位十六进制"""
    base = QbittorrentConfig(host="127.0.0.1", port=8080, username="u", password="p")
    assert rp.probe_fingerprint(base) == rp.probe_fingerprint(
        QbittorrentConfig(host="127.0.0.1", port=8080, username="u", password="p")
    )
    fp = rp.probe_fingerprint(base)
    assert len(fp) == 16 and all(c in "0123456789abcdef" for c in fp)
    variants = [
        QbittorrentConfig(host="10.0.0.2", port=8080, username="u", password="p"),
        QbittorrentConfig(host="127.0.0.1", port=8081, username="u", password="p"),
        QbittorrentConfig(host="127.0.0.1", port=8080, username="u2", password="p"),
        QbittorrentConfig(host="127.0.0.1", port=8080, username="u", password="p2"),
    ]
    changed = {rp.probe_fingerprint(v) for v in variants}
    assert len(changed) == len(variants) and fp not in changed
    # password 空时回落 api_key(有谁用谁); 两者都空 = 空串, 依旧稳定
    assert rp.probe_fingerprint(QbittorrentConfig(host="h", port=1, username="u", api_key="k")) == \
        rp.probe_fingerprint(QbittorrentConfig(host="h", port=1, username="u", password="", api_key="k"))
    both_empty = QbittorrentConfig(host="h", port=1, username="u")
    assert rp.probe_fingerprint(both_empty) == rp.probe_fingerprint(QbittorrentConfig(host="h", port=1, username="u"))


# ---------- 造种 ----------


def test_build_probe_torrent_structure():
    """造种: 4KiB 内容/piece 16KiB 单 piece/无 tracker/无私有标志/约 102B; bdecode 回读逐键核对"""
    content = b"\xa5" * rp.PROBE_FILE_SIZE
    name = "aqb-probe-abc123.bin"
    torrent = rp.build_probe_torrent(content, name)
    assert len(content) == rp.PROBE_FILE_SIZE
    assert 80 <= len(torrent) <= 140  # 报告实测 102B(随随机名长度浮动), 远小于 1KiB
    top, _ = bdecode(torrent)
    assert set(top) == {b"info"}  # 无 announce/announce-list => 无 tracker
    info = top[b"info"]
    assert info[b"length"] == rp.PROBE_FILE_SIZE
    assert info[b"piece length"] == rp.PROBE_PIECE_LENGTH == 16384
    assert info[b"name"].decode() == name
    assert info[b"pieces"] == hashlib.sha1(content).digest()
    assert b"private" not in info  # 非私有标志
    # bencode 编码器往返: 重编码同结构应得到同字节(键序规范)
    assert rp._bencode(top) == torrent


# ---------- 探测主函数 ----------


def test_probe_full_lifecycle_pass(tmp_path, fast_timeouts):
    """全生命通过: 读证+写证+清理无残留; evidence 齐全; qB 无种子; 两侧临时目录消失"""
    ctx, client, src, dst = _env(tmp_path, client=_SameFsClient())
    result = rp.run_probe(ctx, src, dst)
    assert result.status == "passed" and result.reason == "ok" and result.env is False
    ev = result.evidence
    assert ev["read_ok"] is True and ev["write_ok"] is True
    assert ev["size"] == rp.PROBE_FILE_SIZE and len(ev["sha1"]) == 40
    assert ev["method"] == "e1" and ev["hash"] == "HASH123"
    # 证写确实经 qB 的 setLocation(Facade 透传), 且搬进 dst 侧固定前缀目录
    assert any(call[0] == "set_location" and call[1] == ev["dst_dir"] for call in client.calls)
    # 清理无残留: 种子没了, 两侧前缀目录没了
    assert _probe_torrents(client) == []
    assert not os.path.exists(ev["src_dir"]) and not os.path.exists(ev["dst_dir"])
    assert ev["cleanup"]["torrent_deleted"] is True and ev["cleanup"]["torrent_gone"] is True
    assert ev["cleanup"]["residue"] == []


def test_probe_add_params_isolated(tmp_path, fast_timeouts):
    """add 参数钉死(R1 隔离面): is_stopped=True / autoTMM=False / tags=aqb-probe / category 空 /
    save_path=src 下固定前缀临时子目录; recheck/setLocation/deleteFiles 依次下发"""
    ctx, client, src, dst = _env(tmp_path, client=_SameFsClient())
    result = rp.run_probe(ctx, src, dst)
    assert result.status == "passed"
    adds = [call for call in client.calls if call[0] == "add"]
    assert len(adds) == 1
    params = adds[0][1]
    assert params["paused"] is True and params["is_stopped_raw"] is True  # 停止位显式 is_stopped= 传
    assert params["use_auto_torrent_management"] is False
    assert params["category"] is None and params["tags"] == rp.TAG_PROBE == "aqb-probe"
    assert params["save_path"] == result.evidence["src_dir"]
    assert os.path.basename(params["save_path"]).startswith(rp.PROBE_DIR_PREFIX)
    assert client.recheck_hashes_calls == [["HASH123"]]  # 显式 recheck(证读)
    deletes = [call for call in client.calls if call[0] == "delete"]
    assert deletes and deletes[-1][1] is True  # deleteFiles=True 收尾


def test_probe_read_proof_timeout_failed_no_env(tmp_path, fast_timeouts):
    """recheck 不进 1.0 => failed + env=False(FS 不可达, 缓存方向); 探针种子已被清理"""
    ctx, client, src, dst = _env(tmp_path)  # 原生 FakeClient: recheck 不改 progress(恒 0)
    result = rp.run_probe(ctx, src, dst)
    assert result.status == "failed" and result.reason == "read_proof_timeout" and result.env is False
    assert "read_ok" not in result.evidence
    assert _probe_torrents(client) == []  # 失败路径同样清干净
    assert not os.path.exists(result.evidence["src_dir"])


def test_probe_write_proof_timeout_failed_no_env(tmp_path, fast_timeouts):
    """dst 不出现(setLocation 无效果) => failed + env=False; src 文件仍在(现场保留待清理)"""
    ctx, client, src, dst = _env(tmp_path, client=_SameFsClient(set_location_mode="none"))
    result = rp.run_probe(ctx, src, dst)
    assert result.status == "failed" and result.reason == "write_proof_timeout" and result.env is False
    assert "write_ok" not in result.evidence and result.evidence["read_ok"] is True
    assert _probe_torrents(client) == []


def test_probe_write_mismatch_failed_no_env(tmp_path, fast_timeouts):
    """dst 出现但内容不符(跨卷复制截断形态) => write_mismatch + env=False, evidence 记 dst_seen"""
    ctx, client, src, dst = _env(tmp_path, client=_SameFsClient(set_location_mode="corrupt"))
    result = rp.run_probe(ctx, src, dst)
    assert result.status == "failed" and result.reason == "write_mismatch" and result.env is False
    assert result.evidence["dst_seen"] is True


def test_probe_add_rejected_env(tmp_path, fast_timeouts):
    """add 被拒(队列满/磁盘满) => failed + env=True(不缓存方向); 本机临时目录已清"""
    ctx, client, src, dst = _env(tmp_path)
    client.add_error = RuntimeError("queue full")
    result = rp.run_probe(ctx, src, dst)
    assert result.status == "failed" and result.reason == "add_rejected" and result.env is True
    assert "hash" not in result.evidence  # 种子没建成
    assert result.evidence["cleanup"]["torrent_deleted"] is False  # 无种子可删
    assert not os.path.exists(result.evidence["src_dir"])  # 但本机落源目录已清


def test_probe_api_error_env(tmp_path, fast_timeouts):
    """recheck 被 qB 拒 => failed + env=True(环境性); 清理仍执行"""
    ctx, client, src, dst = _env(tmp_path, client=_BrokenRecheckClient())
    result = rp.run_probe(ctx, src, dst)
    assert result.status == "failed" and result.reason == "recheck_rejected" and result.env is True
    assert _probe_torrents(client) == []


def test_probe_torrent_invisible_env(tmp_path, fast_timeouts):
    """add 受理但种子始终不可见(_MuteListClient: info 恒空) => failed + env=True(qB 状态异常)"""
    ctx, client, src, dst = _env(tmp_path, client=_MuteListClient())
    result = rp.run_probe(ctx, src, dst)
    assert result.status == "failed" and result.reason == "torrent_invisible" and result.env is True
    assert not os.path.exists(result.evidence["src_dir"])
    # finally 按 tag 补删对 _MuteListClient(info 恒空)列不到种子: 尽力删除零动作,
    # 种子留残属预期 —— 补删生效的形态由 test_probe_tag_fallback_delete_on_invisible 钉


def test_probe_tag_fallback_delete_on_invisible(tmp_path, fast_timeouts, monkeypatch):
    """add 受理但探测窗口按 tag 不可见(hash 拿不到) => finally 按 tag 补删探测种子(尽力)"""
    ctx, client, src, dst = _env(tmp_path, client=FakeClient())
    # 可见轮询窗口压成 0: add 受理(种子已在 client 里)但 _await_probe_torrent 一次都列不到
    monkeypatch.setattr(rp, "PROBE_READ_TIMEOUT_S", 0.0)
    result = rp.run_probe(ctx, src, dst)
    assert result.status == "failed" and result.reason == "torrent_invisible" and result.env is True
    assert "hash" not in result.evidence  # probe_hash=None, 常规按 hash 删不到
    assert _probe_torrents(client) == []  # 按 tag 补删成功: 探针种子不留残
    assert client.calls[-1] == ("delete", True) and result.evidence["cleanup"]["torrent_deleted"] is True


def test_probe_passes_with_namespaced_view(tmp_path, fast_timeouts, monkeypatch):
    """容器部署命名空间错位: fs.path_map 把 qB 视角(/qb/src|/qb/dst)映到本机临时目录,
    FS 实际共享仅视角不同 => 本机读写经 map_to_container 换算后 run_probe 照常通过
    (修复前: 本机直 stat qB 视角路径 => 证写超时 env=False 被永久缓存, 组被永久硬拦)"""
    local_src = os.path.join(str(tmp_path), "local-src")
    local_dst = os.path.join(str(tmp_path), "local-dst")
    os.makedirs(local_src)  # qB 视角下的挂载点, 本机视图的真实目录
    os.makedirs(local_dst)
    ctx, client, _src, _dst = _env(tmp_path, client=_NamespacedClient())
    # make_manager 构造会经 init_file_access 重建单例, 映射替换必须在其后
    monkeypatch.setattr(
        file_access, "_instance",
        file_access.MappedFileAccess(
            (
                PathMapEntry(src="/qb/src", dst=local_src),
                PathMapEntry(src="/qb/dst", dst=local_dst),
            )
        )
    )
    result = rp.run_probe(ctx, "/qb/src", "/qb/dst")
    assert result.status == "passed" and result.reason == "ok" and result.env is False, result.evidence
    # qB API 侧保持逻辑路径不动(save_path/setLocation 均是 /qb/... 视角)
    assert result.evidence["src_dir"].replace("\\", "/").startswith("/qb/src/")
    assert any(call[0] == "set_location" and call[1] == result.evidence["dst_dir"] for call in client.calls)
    # 本机侧(映射挂载点)无残留: 探针目录在真实 FS 落过且被清掉
    assert os.listdir(local_src) == [] and os.listdir(local_dst) == []


def test_probe_cleanup_runs_on_every_failure_path(tmp_path, fast_timeouts, monkeypatch):
    """各阶段中断仍清理: 本机写失败 / 读证失败后 delete 抛异常 => 结论不变、清理留证并 warning"""
    # 1) 本机写失败(src 不可建): 目录不存在、env=True, 且 finally 里的 rmtree 不炸
    ctx, client, src, dst = _env(tmp_path)
    blocked = os.path.join(src, "not-a-dir")  # makedirs(src_dir) 的父路径是文件 => OSError
    with open(blocked, "w") as f:
        f.write("x")
    result = rp.run_probe(ctx, os.path.join(src, "not-a-dir", "deeper"), dst)
    assert result.status == "failed" and result.reason == "local_write_failed" and result.env is True
    # 2) 读证超时 + deleteFiles 抛异常: 探测结论仍 read_proof_timeout/env=False; 本机目录照常清,
    #    qB 侧种子删不掉 => cleanup 留证(delete_error/torrent_gone=False) + warning
    ctx2, client2, src2, dst2 = _env(tmp_path)

    def _boom(torrent_hashes=None, delete_files=False):
        raise RuntimeError("delete refused")

    monkeypatch.setattr(client2, "torrents_delete", _boom)
    with capture_logs("auto_qb.core.modules.relocate_mod", level=logging.WARNING) as rec:
        result2 = rp.run_probe(ctx2, src2, dst2)
    assert result2.status == "failed" and result2.reason == "read_proof_timeout" and result2.env is False
    info = result2.evidence["cleanup"]
    assert info["torrent_deleted"] is False and info["delete_error"] != ""
    assert info["torrent_gone"] is False and info["residue"] == []
    assert set(info["dirs_removed"]) == {result2.evidence["src_dir"], result2.evidence["dst_dir"]}
    assert any("删除探测种子失败" in r.getMessage() for r in rec.records)
    assert _probe_torrents(client2) != []  # 种子确实没删掉(留证不撒谎)


def test_probe_timeout_budget_constants():
    """超时常量单点取值钉住: 读证 10s / 写证 10s / 清理 5s / 轮询 0.25s(总预算收敛, 计划 R4)"""
    assert rp.PROBE_READ_TIMEOUT_S == 10.0
    assert rp.PROBE_WRITE_TIMEOUT_S == 10.0
    assert rp.PROBE_CLEANUP_TIMEOUT_S == 5.0
    assert rp.PROBE_POLL_INTERVAL_S == 0.25
    assert rp.TAG_PROBE == "aqb-probe" and rp.PROBE_DIR_PREFIX == "aqb-probe-"


# ---------- 启动残留扫描 ----------


def _inject_residue(ctx, client, root):
    """造一个崩溃残留: 探测 tag 种子 + save_path 前缀目录(含文件)"""
    save_path = os.path.join(root, rp.PROBE_DIR_PREFIX + "deadbeef")
    os.makedirs(save_path, exist_ok=True)
    with open(os.path.join(save_path, "aqb-probe-deadbeef.bin"), "wb") as f:
        f.write(b"leftover")
    client.torrents["RES1"] = FakeTorrent(
        hash="RES1", name="aqb-probe-deadbeef.bin", save_path=save_path, tags=rp.TAG_PROBE
    )
    return save_path


def test_sweep_probe_residue(tmp_path):
    """启动扫描清残留(种子+前缀目录); 幂等二次为 0; 非本前缀目录保守不动"""
    ctx, client, src, dst = _env(tmp_path)
    save_path = _inject_residue(ctx, client, src)
    assert rp.sweep_probe_residue(ctx) == 1
    assert _probe_torrents(client) == [] and not os.path.exists(save_path)
    assert rp.sweep_probe_residue(ctx) == 0  # 幂等
    # tag 是探测 tag 但 save_path 不带固定前缀(用户自己打了同名 tag 的种子): 只删种子不动目录
    other_dir = os.path.join(src, "user-dir")
    os.makedirs(other_dir)
    with open(os.path.join(other_dir, "keep.txt"), "w") as f:
        f.write("keep")
    client.torrents["RES2"] = FakeTorrent(hash="RES2", name="user.bin", save_path=other_dir, tags=rp.TAG_PROBE)
    assert rp.sweep_probe_residue(ctx) == 1
    assert os.path.exists(os.path.join(other_dir, "keep.txt"))  # 目录保守未动
    assert client.calls[-1] == ("delete", False)  # 名不匹配: 只删种子记录, 不 deleteFiles


def test_sweep_residue_tag_only_no_delete_files(tmp_path):
    """tag 命中但种子名/保存路径均不带 aqb-probe 前缀 => 只删种子记录不删文件
    (delete_files=False, 保守默认: 用户自己打了同名 tag 的种子数据绝不能被误删)"""
    ctx, client, src, dst = _env(tmp_path)
    user_dir = os.path.join(src, "user-data")
    os.makedirs(user_dir)
    keep_file = os.path.join(user_dir, "e01.mkv")
    with open(keep_file, "w") as f:
        f.write("keep")
    client.torrents["RES9"] = FakeTorrent(hash="RES9", name="My Show S01", save_path=user_dir, tags=rp.TAG_PROBE)
    assert rp.sweep_probe_residue(ctx) == 1
    assert _probe_torrents(client) == []  # 种子记录已摘(探测 tag 认领)
    assert os.path.exists(keep_file)  # 数据文件保留(不 deleteFiles)
    assert client.calls[-1] == ("delete", False)


def test_start_hook_sweeps_residue(tmp_path, fast_timeouts):
    """relocate 启动钩子: enabled 时清残留并在启动日志提及; disabled / dry_run 不动手"""
    residue_root = os.path.join(str(tmp_path), "src")
    # enabled: 清 + 日志提及
    ctx, client, src, dst = _env(tmp_path)
    save_path = _inject_residue(ctx, client, residue_root)
    mod = ctx.relocate
    ctx.config.relocate.enabled = True
    with capture_logs("auto_qb.core.modules.relocate_mod", level=logging.INFO) as rec:
        mod.start(ctx, dry_run=False)
    assert _probe_torrents(client) == [] and not os.path.exists(save_path)
    assert any("探测残留" in r.getMessage() for r in rec.records)
    # disabled: 零动作
    ctx2, client2, src2, dst2 = _env(tmp_path)
    save_path2 = _inject_residue(ctx2, client2, residue_root)
    mod2 = ctx2.relocate
    ctx2.config.relocate.enabled = False
    mod2.start(ctx2, dry_run=False)
    assert _probe_torrents(client2) != [] and os.path.exists(save_path2)
    # dry_run: enabled 也不动手(启动扫描是真写)
    ctx3, client3, src3, dst3 = _env(tmp_path)
    save_path3 = _inject_residue(ctx3, client3, residue_root)
    mod3 = ctx3.relocate
    ctx3.config.relocate.enabled = True
    mod3.start(ctx3, dry_run=True)
    assert _probe_torrents(client3) != [] and os.path.exists(save_path3)


# 确认 LifecycleMixin 已挂 sweep(relocate_mod 类定义消费该 Mixin; 防止有人把钩子拆掉)
def test_lifecycle_mixin_wires_sweep():
    """LifecycleMixin.start 源码里确实调用 sweep_probe_residue(钩子挂接不回退)"""
    import inspect
    src_text = inspect.getsource(LifecycleMixin.start)
    assert "sweep_probe_residue" in src_text


# ---------------------------------------------------------------------------
# 覆盖率缺口清偿(26-11-07): 错误分支与轮询边角
# ---------------------------------------------------------------------------


class _TagListErrorClient(FakeClient):
    """按 tag 列种子恒炸: add 受理后可见性轮询期 API 异常(环境性)"""
    def torrents_info(self, torrent_hashes=None, **kw):
        if kw.get("tag") == rp.TAG_PROBE:
            raise RuntimeError("tag list broke")
        return super().torrents_info(torrent_hashes=torrent_hashes, **kw)


class _RecheckPollErrorClient(_SameFsClient):
    """recheck 后按 hash 轮询进度恒炸: 读证轮询期 API 异常(环境性)"""
    def torrents_info(self, torrent_hashes=None, **kw):
        if torrent_hashes:
            raise RuntimeError("progress poll broke")
        return super().torrents_info(torrent_hashes=torrent_hashes, **kw)


class _HashlessFirstClient(_SameFsClient):
    """首次 tag 列表回一个无 hash 条目: 可见性轮询的「无 hash 跳过」支"""
    def __init__(self):
        super().__init__()
        self._tag_calls = 0

    def torrents_info(self, torrent_hashes=None, **kw):
        res = super().torrents_info(torrent_hashes=torrent_hashes, **kw)
        if kw.get("tag") == rp.TAG_PROBE:
            self._tag_calls += 1
            if self._tag_calls == 1:
                return [FakeTorrent(hash="", name="ghost", tags=rp.TAG_PROBE)]
        return res


class _RejectSetLocationClient(_SameFsClient):
    """setLocation 被 qB 拒(环境性)"""
    def torrents_set_location(self, torrent_hashes=None, location=None):
        raise RuntimeError("location rejected")


class _CopyNoMoveClient(_SameFsClient):
    """setLocation 只复制不搬走: dst 出现一致内容而 src 恒在场(证写超时的「仅复制」形态)"""
    def torrents_set_location(self, torrent_hashes=None, location=None):
        FakeClient.torrents_set_location(self, torrent_hashes=torrent_hashes, location=location)  # 只记台账
        for h in (torrent_hashes if isinstance(torrent_hashes, (list, tuple)) else [torrent_hashes]):
            tor = self.torrents.get(h)
            if tor is None or not os.path.isdir(tor.save_path):
                continue
            src_dir = tor.save_path
            os.makedirs(location, exist_ok=True)
            for fn in os.listdir(src_dir):
                with open(os.path.join(src_dir, fn), "rb") as f:
                    data = f.read()
                with open(os.path.join(location, fn), "wb") as f:
                    f.write(data)  # 内容一致但源不消失
            tor.save_path = location  # qB 账面照常翻到新位置(物理侧只是复制)


def test_probe_bencode_type_gates():
    """_bencode 类型闸: bool 拒 / list 编码 / 域外类型(float)拒"""
    with pytest.raises(TypeError, match="bool"):
        rp._bencode(True)
    assert rp._bencode([1, b"2"]) == b"li1e1:2e"
    with pytest.raises(TypeError, match="不支持的类型"):
        rp._bencode(3.5)


def test_probe_api_unavailable_env(tmp_path):
    """ctx 无 api / api 无客户端 => 环境性失败 api_unavailable(不进任何探测动作)"""
    result = rp.run_probe(types.SimpleNamespace(), str(tmp_path / "src"), str(tmp_path / "dst"))
    assert result.status == "failed" and result.reason == "api_unavailable" and result.env is True


def test_probe_tag_list_api_error_during_await(tmp_path, fast_timeouts):
    """可见性轮询期按 tag 列种子炸 => api_error + env=True(与种子不可见同出口, 带错误证据)"""
    ctx, client, src, dst = _env(tmp_path, client=_TagListErrorClient())
    result = rp.run_probe(ctx, src, dst)
    assert result.status == "failed" and result.reason == "api_error" and result.env is True
    assert "tag list broke" in result.evidence["error"]


def test_probe_recheck_poll_api_error_env(tmp_path, fast_timeouts):
    """读证轮询期按 hash 列进度炸 => api_error + env=True(recheck 本身已受理)"""
    ctx, client, src, dst = _env(tmp_path, client=_RecheckPollErrorClient())
    result = rp.run_probe(ctx, src, dst)
    assert result.status == "failed" and result.reason == "api_error" and result.env is True
    assert "progress poll broke" in result.evidence["error"]


def test_probe_awaits_past_hashless_tag_entries(tmp_path, fast_timeouts):
    """可见性轮询撞无 hash 条目: 跳过继续等, 下拍命中真种子全生命通过"""
    ctx, client, src, dst = _env(tmp_path, client=_HashlessFirstClient())
    result = rp.run_probe(ctx, src, dst)
    assert result.status == "passed" and result.reason == "ok"
    assert client._tag_calls >= 2  # 无 hash 条目没让轮询提前退


def test_probe_set_location_rejected_env(tmp_path, fast_timeouts):
    """setLocation 被拒 => set_location_rejected + env=True(不缓存方向)"""
    ctx, client, src, dst = _env(tmp_path, client=_RejectSetLocationClient())
    result = rp.run_probe(ctx, src, dst)
    assert result.status == "failed" and result.reason == "set_location_rejected" and result.env is True
    assert "location rejected" in result.evidence["error"]


def test_probe_write_proof_copy_without_move_mismatch(tmp_path, fast_timeouts):
    """dst 已出现一致内容而 src 未消失: 继续等到超时定性 mismatch(不只看 dst 在场)"""
    ctx, client, src, dst = _env(tmp_path, client=_CopyNoMoveClient())
    result = rp.run_probe(ctx, src, dst)
    assert result.status == "failed" and result.reason == "write_mismatch" and result.env is False
    assert result.evidence.get("dst_seen") is True and result.evidence.get("src_present") is True


def test_file_matches_oserror_is_false(tmp_path):
    """本机文件比对读不了(size/开文件 OSError) => 不一致(不抛)"""
    missing = str(tmp_path / "gone.bin")
    assert rp._file_matches(missing, "0" * 40, 4) is False


class _CleanupApi:
    """_cleanup 直测替身: tag 列表/删除/消失轮询三面可注入故障"""
    def __init__(self, tag_rows=(), tag_error=None, delete_error=None, gone_poll_error=None):
        self.tag_rows = list(tag_rows)
        self.tag_error = tag_error
        self.delete_error = delete_error
        self.gone_poll_error = gone_poll_error
        self.deleted = []

    def torrents_info(self, torrent_hashes=None, **kw):
        if self.tag_error is not None and kw.get("tag"):
            raise self.tag_error
        if self.gone_poll_error is not None and torrent_hashes:
            raise self.gone_poll_error
        if kw.get("tag"):
            return list(self.tag_rows)
        return []  # 消失轮询: 默认已消失

    def torrents_delete(self, torrent_hashes=None, delete_files=False):
        if self.delete_error is not None:
            raise self.delete_error
        self.deleted.append((tuple(torrent_hashes or ()), delete_files))


def test_cleanup_tag_delete_matrix(tmp_path):
    """无 hash 的清理: 无 hash 条目跳过 / 正常补删 / 补删炸留证 / 定位炸留证, 均不抛"""
    ev: dict = {}
    api = _CleanupApi(tag_rows=[SimpleNamespace(hash=""), SimpleNamespace(hash="T1")])
    rp._cleanup(api, "", (str(tmp_path / "a"), str(tmp_path / "b")), ev)
    assert ev["cleanup"]["torrent_deleted"] is True and api.deleted == [(("T1", ), True)]

    ev2: dict = {}
    api2 = _CleanupApi(tag_rows=[SimpleNamespace(hash="T1")], delete_error=RuntimeError("delete refused"))
    rp._cleanup(api2, "", (), ev2)
    assert "tag_delete_error" in ev2["cleanup"] and ev2["cleanup"]["torrent_deleted"] is False

    ev3: dict = {}
    api3 = _CleanupApi(tag_error=RuntimeError("locate broke"))
    rp._cleanup(api3, "", (), ev3)
    assert "tag_locate_error" in ev3["cleanup"]


def test_cleanup_gone_poll_error_records_and_continues(tmp_path):
    """删除后的消失轮询炸: gone_error 留证并直接进目录清理(不抛不改结论)"""
    ev: dict = {}
    d = tmp_path / "a"
    d.mkdir()
    api = _CleanupApi(gone_poll_error=RuntimeError("poll broke"))
    rp._cleanup(api, "HASH1", (str(d), ), ev)
    info = ev["cleanup"]
    assert info["torrent_deleted"] is True and "gone_error" in info and info["torrent_gone"] is False
    assert info["dirs_removed"] == [str(d)]


def test_cleanup_rmtree_failure_and_leftover(tmp_path, monkeypatch):
    """目录清理失败: residue 留证 + 清理后仍存在则并入 leftover(启动扫描兜底文案)"""
    d1, d2 = tmp_path / "a", tmp_path / "b"
    d1.mkdir()
    d2.mkdir()

    def _boom(path, *a, **kw):
        raise PermissionError(13, "locked")

    monkeypatch.setattr(shutil, "rmtree", _boom)
    ev: dict = {}
    rp._cleanup(_CleanupApi(), "H", (str(d1), str(d2)), ev)
    info = ev["cleanup"]
    assert info["residue"] == [str(d1), str(d2)] and info["dirs_removed"] == []
    assert os.path.exists(d1) and os.path.exists(d2)  # leftover 面成立


def test_sweep_probe_residue_list_error_returns_zero(tmp_path):
    """启动扫描列种子炸: 吞掉记 warning 返回 0(绝不挡启动); 无 api 同样 0"""
    ctx, client, src, dst = _env(tmp_path)

    def _boom(**kw):
        raise RuntimeError("list broke")

    client.torrents_info = _boom  # 直接替换: sweep 只走这一个入口
    assert rp.sweep_probe_residue(ctx) == 0
    assert rp.sweep_probe_residue(types.SimpleNamespace()) == 0  # ctx 无 api/client: 零动作


def test_sweep_probe_residue_delete_failure_and_hashless(tmp_path):
    """残留删除失败: 单条告警继续其余条目; 无 hash 条目跳过删除仍计数"""
    ctx, client, src, dst = _env(tmp_path)
    client.torrents["R1"] = FakeTorrent(hash="", name="aqb-probe-x.bin", save_path=src, tags=rp.TAG_PROBE)

    calls = {"n": 0}

    def _boom(*a, **kw):
        calls["n"] += 1
        raise RuntimeError("delete broke")

    client.torrents["R2"] = FakeTorrent(hash="R2", name="aqb-probe-y.bin", save_path=src, tags=rp.TAG_PROBE)
    with mock.patch.object(client, "torrents_delete", side_effect=_boom):
        assert rp.sweep_probe_residue(ctx) == 1  # 无 hash 条目计 cleaned; 删除失败条目不计
    assert calls["n"] == 1  # 无 hash 条目没发起删除


def test_sweep_probe_residue_dir_cleanup_failure_warns(tmp_path, monkeypatch):
    """残留目录清理失败: 只告警不抛(人工/启动扫描兜底)"""
    ctx, client, src, dst = _env(tmp_path)
    save_path = _inject_residue(ctx, client, src)

    def _boom(path, *a, **kw):
        raise PermissionError(13, "locked")

    monkeypatch.setattr(shutil, "rmtree", _boom)
    assert rp.sweep_probe_residue(ctx) == 1
    assert os.path.exists(save_path)  # 目录清理失败: 保守保留现场
