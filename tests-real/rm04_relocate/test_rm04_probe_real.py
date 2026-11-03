"""[RM04-11] 同机强探测 E1 真机正向: 真写目标盘通过 + qB 探针零残留(产品 run_probe 直连 56590)
[RM04-12] E1 指纹缓存: 首探真执行并落缓存 / 同指纹命中零探测 / 改 port 指纹失效重探
[RM04-13] D 级列目录闭证: 56590 默认保存路径(R: 不存在)getDirectoryContent 不可判定 + C: 目录正向对照

计划 26-11-04-0055 §04 P6(真机与收尾)。本文件补两条真机事实:
1) E1 的 qB 侧动作(加种/证读/证写/删种)在 5.2.3 上真的成立, 且清理后 qB 与两侧目录零残留;
2) 指纹缓存/失效语义在真实 qB + 真 state 容器上按产品入口(_ensure_probe)兑现;
3) 报告 26-11-03-2306 §7.4 的待实测项: qB 能否列出默认路径 R:\\Download\\PTing。

口径(2026-11-04 起): agent 自跑真机验收, 不靠人工复验; 只断言外部可观测事实(qB 种子列表 /
文件系统 / state.relocate.probes / 耗时)。取证副本落 tests-real/.work/rm04/probe_real_evidence.json
(gitignored), 供本轮报告引用实测数字。

跑法: `commands run real.run -- --case RM04-11 --yes`(不要裸 pytest)。
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from auto_qb.config import QbittorrentConfig
from auto_qb.core.modules.relocate_mod import RelocateModule
from auto_qb.core.modules.relocate_probe import PROBE_DIR_PREFIX, TAG_PROBE, probe_fingerprint, run_probe
from auto_qb.core.modules.relocate_proof import POSITIVE, UNAVAILABLE, path_evidence
from auto_qb.core.qbapi import QbApi
from auto_qb.core.qbclient import new_client
from auto_qb.torrents.store import TorrentStore
from lib import instances

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="真机轨含 Windows 路径语义"),
]

WORK = Path(__file__).resolve().parents[1] / ".work" / "rm04"
EVIDENCE = WORK / "probe_real_evidence.json"


def _qb_conf(port: int) -> QbittorrentConfig:
    """真机测试实例的 qB 连接配置(本机免鉴权: 用户名/密码留空)。"""
    return QbittorrentConfig(host="127.0.0.1", port=port)


def _ctx(port: int):
    """产品形态 ctx: QbApi(真 Client + TorrentStore) + 真 state 容器 + 真 config 段。"""
    client = new_client(_qb_conf(port))
    client.auth_log_in()
    store = TorrentStore(client)
    api = QbApi(client, store)
    conf = SimpleNamespace(
        qbittorrent=_qb_conf(port),
        relocate=SimpleNamespace(assume_shared=False),
    )
    ctx = SimpleNamespace(api=api, store=store, state=SimpleNamespace(data={}), config=conf, dry_run=False)
    return ctx, client


def _probe_torrents(client) -> list:
    return client.torrents_info(tag=TAG_PROBE) or []


def _no_prefix_dirs(root: Path) -> list[str]:
    return [p.name for p in root.iterdir() if p.name.startswith(PROBE_DIR_PREFIX)]


def _record(case: str, payload: dict) -> None:
    """取证副本(gitignored .work): 断言之外把实测值留给本轮报告, 不参与任何产品逻辑。"""
    WORK.mkdir(parents=True, exist_ok=True)
    data = {}
    if EVIDENCE.is_file():
        try:
            data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        except ValueError:
            data = {}
    data[case] = payload
    EVIDENCE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_rm04_11_probe_real_write_and_cleanup(secondary, workdir):
    """E1 真机正向: passed + read_ok/write_ok + 清理后 qB/目录零残留。"""
    assert secondary.version().startswith("v5.2"), f"56590 版本应为 5.2.x, 实际 {secondary.version()}"
    ctx, client = _ctx(instances.SECONDARY)
    src = workdir / "src"
    dst = workdir / "dst"
    src.mkdir()
    dst.mkdir()

    started = time.monotonic()
    result = run_probe(ctx, str(src), str(dst))
    wall_s = round(time.monotonic() - started, 3)

    assert result.status == "passed", f"E1 真机探测失败: {result.reason} evidence={result.evidence}"
    assert result.reason == "ok" and result.env is False
    ev = result.evidence
    assert ev["read_ok"] is True
    assert ev["write_ok"] is True
    assert ev["cleanup"]["torrent_deleted"] is True
    assert ev["cleanup"]["torrent_gone"] is True
    assert ev["cleanup"]["residue"] == [], f"探针目录残留: {ev['cleanup']['residue']}"
    assert len(ev["cleanup"]["dirs_removed"]) == 2
    assert _probe_torrents(client) == [], "qB 内仍有 aqb-probe 标签种子"
    assert _no_prefix_dirs(src) == [] and _no_prefix_dirs(dst) == []

    _record(
        "RM04-11",
        {
            "status": result.status,
            "reason": result.reason,
            "elapsed_s": ev.get("elapsed_s"),
            "wall_s": wall_s,
            "sha1": ev.get("sha1"),
            "size": ev.get("size"),
            "cleanup": ev.get("cleanup"),
            "residue_torrents": 0,
        },
    )


def test_rm04_12_probe_fingerprint_cache_and_reprobe(secondary, workdir):
    """指纹缓存: 首探真跑并落 state / 同指纹再调零探测 / 改 port 指纹变更后重探。"""
    ctx, client = _ctx(instances.SECONDARY)
    module = RelocateModule(ctx)
    conf_secondary = probe_fingerprint(_qb_conf(instances.SECONDARY))
    conf_primary = probe_fingerprint(_qb_conf(instances.PRIMARY))
    assert conf_secondary != conf_primary, "改 port 后指纹必须变化"

    src = workdir / "src"
    dst = workdir / "dst"
    src.mkdir()
    dst.mkdir()
    facts = SimpleNamespace(same_fs_proved=False, save_path=str(src), target=str(dst))
    records = [SimpleNamespace(hash="a" * 40), SimpleNamespace(hash="b" * 40)]
    verdict = {"reasons": [], "notes": []}

    t0 = time.monotonic()
    assert module._ensure_probe(records, facts, verdict) is None
    first_wall = round(time.monotonic() - t0, 3)
    probes = ctx.state.data["relocate"]["probes"]
    assert conf_secondary in probes and probes[conf_secondary]["status"] == "passed"
    assert probes[conf_secondary]["evidence"]["read_ok"] is True
    assert probes[conf_secondary]["evidence"]["write_ok"] is True
    assert "跳过重复探测" not in " ".join(verdict["notes"])

    t0 = time.monotonic()
    assert module._ensure_probe(records, facts, verdict) is None
    second_wall = round(time.monotonic() - t0, 3)
    assert second_wall < 0.2, f"缓存命中仍耗时 {second_wall}s(应近零)"
    assert any("命中缓存" in n for n in verdict["notes"])
    assert len(probes) == 1

    # 改 port => 连接身份变化 => 指纹未命中 => 重新真探一次(并把客户端一并绑到主实例)
    ctx.config.qbittorrent = _qb_conf(instances.PRIMARY)
    client_primary = new_client(_qb_conf(instances.PRIMARY))
    client_primary.auth_log_in()
    ctx.api.bind(client_primary, TorrentStore(client_primary))
    t0 = time.monotonic()
    assert module._ensure_probe(records, facts, {"reasons": [], "notes": []}) is None
    third_wall = round(time.monotonic() - t0, 3)
    assert conf_primary in ctx.state.data["relocate"]["probes"]
    assert len(ctx.state.data["relocate"]["probes"]) == 2
    entry = ctx.state.data["relocate"]["probes"][conf_primary]
    assert entry["status"] == "passed" and entry["evidence"]["write_ok"] is True
    assert third_wall > 0.2, f"指纹变更后应真重探, 实测只耗时 {third_wall}s"

    for port in (instances.SECONDARY, instances.PRIMARY):
        c = new_client(_qb_conf(port))
        c.auth_log_in()
        assert _probe_torrents(c) == [], f"{port} 内仍有 aqb-probe 标签种子"
    assert _no_prefix_dirs(src) == [] and _no_prefix_dirs(dst) == []

    _record(
        "RM04-12",
        {
            "fingerprint_56590": conf_secondary,
            "fingerprint_56589": conf_primary,
            "first_wall_s": first_wall,
            "cache_hit_wall_s": second_wall,
            "reprobe_wall_s": third_wall,
            "probes": sorted(ctx.state.data["relocate"]["probes"].keys()),
        },
    )


def test_rm04_13_directory_content_default_save_path(secondary, workdir):
    """报告 §7.4 待实测闭合: 56590 默认保存路径(R: 不存在)列目录 → 不可判定; C: 目录降级链对照。

    对照腿只断言「产品最终判 positive」, 不钉证据级(D/B′): 本轮实测发现 D 级对
    qbittorrent-api 返回的 UserList 容器(DirectoryContentList)判定为形态异常而恒降级,
    当前真实链路走 B′ —— 该产品缺陷按 scope-guard 记 issue, 本用例记录两种级别实测值。
    """
    ctx, client = _ctx(instances.SECONDARY)
    prefs = secondary.prefs()
    default_save_path = str(prefs.get("save_path") or "")
    assert default_save_path, "56590 默认 save_path 为空, 无法闭证"

    # 端点原始行为: 不存在/不可见路径应抛 404(与报告 §8.1 C: 正向对照互为印证)
    raw_error = ""
    try:
        client.app_get_directory_content(directory_path=default_save_path, with_metadata="true")
    except Exception as exc:  # noqa: BLE001 - 这里要的就是异常本身
        raw_error = f"{type(exc).__name__}: {exc}"

    ev_default = path_evidence(ctx, default_save_path, default_save_path, visibility_only=True)
    assert ev_default.status == UNAVAILABLE, f"默认路径意外可判: {ev_default}"
    assert "404" in raw_error or "not found" in raw_error.lower() or "不存在" in raw_error, \
        f"默认路径列目录未呈现 404 语义: {raw_error!r}"

    # 正向对照: 本机真实目录。raw 端点取证(容器类型/元数据命中) + 产品降级链最终判 positive
    content = workdir / "content"
    content.mkdir()
    sample = content / "sample.bin"
    sample.write_bytes(os.urandom(4096))
    raw_type, raw_entries, raw_matched = "", 0, False
    try:
        raw = client.app_get_directory_content(directory_path=str(content), with_metadata="true")
        raw_type, raw_entries = type(raw).__name__, len(raw)
        local = os.stat(sample)
        for e in raw:
            if e.get("name") == "sample.bin" and int(e.get("size")) == 4096 and \
                    int(e.get("last_modification_date")) == int(local.st_mtime):
                raw_matched = True
                break
    except Exception as exc:  # noqa: BLE001 - 取证腿失败也要把信息带进记录
        raw_type = f"ERROR {type(exc).__name__}: {exc}"
    assert raw_matched, f"raw 端点元数据与本机 stat 不吻合({raw_type}, entries={raw_entries})"

    d_only = path_evidence(ctx, str(content), str(content))
    ev_control = path_evidence(ctx, str(content), str(content), files=(("sample.bin", 4096), ))
    assert ev_control.status == POSITIVE, f"C: 目录路径级证据最终应 positive, 实际 {ev_control}"

    _record(
        "RM04-13",
        {
            "default_save_path": default_save_path,
            "raw_error": raw_error,
            "default_evidence": {
                "status": ev_default.status,
                "level": ev_default.level,
                "detail": ev_default.detail
            },
            "control_raw": {
                "container_type": raw_type,
                "entries": raw_entries,
                "metadata_matched": raw_matched
            },
            "control_d_only": {
                "status": d_only.status,
                "level": d_only.level,
                "detail": d_only.detail
            },
            "control_final": {
                "status": ev_control.status,
                "level": ev_control.level,
                "detail": ev_control.detail
            },
        },
    )
    shutil.rmtree(content, ignore_errors=True)
