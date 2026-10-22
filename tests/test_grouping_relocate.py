"""test_grouping_relocate 测试计划: 组判定改造与联动抑制(计划 26-10-18-1604 §04 P4)

验收判据(plan §04 P4): 现有 grouping 测试全绿; 新增六条守阵 ——
① 文件链接在场 ⇒ 两成员同组(别名不裂组); ② 搬迁窗口不误暂停(relocating 让路);
③ 别名期间新加的同内容辅种自动并组; ④ 同名不同内容仍被跨组交叉检测拦下;
⑤ 第三方目录级链接(junction)按解析后路径并组; ⑥ 第三方文件级链接/硬链接被识别且拒迁。

## 测试计划(每个测试函数一条)
- test_file_links_keep_group_together: 活跃 job 作用域内, 指向 src 的成员与已到 dst 的 mover 同组
- test_relocating_skips_missing_scan: relocating 登记内的组不触发缺文件扫描(不暂停/不打标)
- test_new_member_joins_alias_group: 别名期间新增同内容辅种并进同一组
- test_cross_group_conflict_still_blocks: 同名不同内容(文件集不同)仍被交叉检测拦下并暂停下载方
- test_third_party_junction_joins_group: 第三方目录 junction 的种子按解析后物理目录并组
- test_third_party_link_detected_and_relocation_blocked: 硬链接组被打标, 迁移闸门拒迁(hardlink)
- test_resolver_identity_when_disabled: 无 job 且非链接时解析恒等(开关关 = 逐字节现状)
"""
import os

import pytest

from auto_qb.core.modules.relocate_units import RelocateJob
from auto_qb.infra import alias_fs, utils

from helpers import FakeClient, FakeTorrent, _fake_file, make_manager, pin_disk_usage, seed_store

FREE = 1 << 40


def _env(td, files=("Show/e00.mkv", "Show/e01.mkv")):
    """双成员组 + 目标目录; 返回 (mgr, client, src, dst, content)"""
    mgr = make_manager(os.path.join(str(td), "state.json"))
    client = FakeClient()
    mgr.client = client
    src = os.path.join(str(td), "src")
    dst = os.path.join(str(td), "dst")
    content = os.path.join(src, "Show")
    os.makedirs(content)
    os.makedirs(dst)
    fl = []
    for rel in files:
        p = os.path.join(src, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(b"x" * 64)
        fl.append(_fake_file(rel, 64))
    client.files_map["HA"] = list(fl)
    client.files_map["HB"] = list(fl)
    tors = [
        FakeTorrent(hash="HA", name="Show", save_path=src, progress=1.0, state="pausedUP"),
        FakeTorrent(hash="HB", name="Show", save_path=src, progress=1.0, state="pausedUP"),
    ]
    for t in tors:
        client.torrents[t.hash] = t
    seed_store(mgr, tors)
    mgr.store.server_state = {"free_space_on_disk": FREE}
    mgr.config.data_dir = os.path.join(str(td), "data")
    mgr.config.relocate.enabled = True
    return mgr, client, src, dst, content


def _job(src, dst, content, phase="armed", hashes=("HA", "HB")):
    return RelocateJob(
        job_id="j1",
        hashes=hashes,
        mover="HA",
        src=src,
        dst=dst,
        scope=content,
        alias_kind="file",
        phase=phase,
    )


def test_file_links_keep_group_together(tmp_path):
    """① 文件链接在场: 仍指向 src 的 HB 与已到 dst 的 HA 落进同一组(不裂组)"""
    mgr, client, src, dst, content = _env(tmp_path)
    grouping = mgr.host.get("grouping")
    mgr.host.get("relocate").register_job(_job(src, dst, content))
    mgr.store.by_hash["HA"].save_path = dst  # mover 已搬到目标
    grouping._assign_new_torrent("HA")
    grouping._assign_new_torrent("HB")
    key_ha = mgr.store.member_to_key["HA"]
    key_hb = mgr.store.member_to_key["HB"]
    assert key_ha == key_hb, (key_ha, key_hb)
    assert key_ha[0] == dst.replace("\\", "/"), key_ha[0]
    assert set(mgr.store.groups[key_ha]) == {"HA", "HB"}


def test_relocating_skips_missing_scan(tmp_path):
    """② 搬迁窗口: 组内成员在 relocating 登记内 ⇒ 跳过错文件扫描(不暂停、不打 MISSING)"""
    mgr, client, src, dst, content = _env(tmp_path)
    grouping = mgr.host.get("grouping")
    grouping._assign_new_torrent("HA")
    grouping._assign_new_torrent("HB")
    key = mgr.store.member_to_key["HA"]
    for f in os.listdir(content):  # 模拟 qB 正在把文件搬走(此刻盘上确实没有)
        os.remove(os.path.join(content, f))
    client.calls.clear()
    mgr.store.relocating_hashes = {"HA", "HB"}
    grouping._scan_triggered_groups({key}, dry_run=False)
    assert not any(c[0] in ("stop", "pause") for c in client.calls), client.calls
    assert mgr.config.grouping.missing_tag not in mgr.store.by_hash["HA"].tags_set

    # 反证: 不在搬迁窗口时同一现场会被判缺失(整组暂停 + 打标), 证明上面是「让路」不是「坏了」
    mgr.store.relocating_hashes = set()
    grouping._scan_triggered_groups({key}, dry_run=False)
    assert any(c[0] in ("stop", "pause") for c in client.calls), client.calls


def test_new_member_joins_alias_group(tmp_path):
    """③ 别名期间新加的同内容辅种自动并进同一组(作用域不是快照)"""
    mgr, client, src, dst, content = _env(tmp_path)
    grouping = mgr.host.get("grouping")
    mgr.host.get("relocate").register_job(_job(src, dst, content))
    mgr.store.by_hash["HA"].save_path = dst
    grouping._assign_new_torrent("HA")
    grouping._assign_new_torrent("HB")
    new_files = [_fake_file("Show/e00.mkv", 64), _fake_file("Show/e01.mkv", 64)]
    client.files_map["HC"] = new_files
    hc = FakeTorrent(hash="HC", name="Show", save_path=src, progress=1.0, state="pausedUP")
    client.torrents["HC"] = hc
    seed_store(mgr, [client.torrents["HA"], client.torrents["HB"], hc])
    grouping._assign_new_torrent("HC")
    assert mgr.store.member_to_key["HC"] == mgr.store.member_to_key["HA"]


def test_cross_group_conflict_still_blocks(tmp_path):
    """④ 同名不同内容(文件集不同 ⇒ 两组)仍被跨组交叉检测拦下, 只暂停下载方"""
    mgr, client, src, dst, content = _env(tmp_path)
    mgr.config.grouping.cross_group_conflict_check = True  # 该检测默认关(保守默认), 守阵显式开
    # HB 改成 {Show/e01, Show/e02}: 与 HA 的 {e00,e01} 不同组但共享 e01.mkv
    with open(os.path.join(content, "e02.mkv"), "wb") as f:
        f.write(b"x" * 64)
    client.files_map["HB"] = [_fake_file("Show/e01.mkv", 64), _fake_file("Show/e02.mkv", 64)]
    mgr.store.by_hash["HB"].dlspeed = 100
    mgr.store.by_hash["HB"].progress = 0.5
    mgr.store.by_hash["HB"].state = "downloading"
    mgr.store.by_hash["HB"].amount_left = 10
    grouping = mgr.host.get("grouping")
    grouping._assign_new_torrent("HA")
    grouping._assign_new_torrent("HB")
    assert mgr.store.member_to_key["HA"] != mgr.store.member_to_key["HB"]
    client.calls.clear()
    grouping._check_cross_group_file_conflicts(dry_run=False)
    assert any(c[0] in ("stop", "pause") for c in client.calls), client.calls


@pytest.mark.skipif(not utils.is_windows(), reason="junction 仅 Windows")
def test_third_party_junction_joins_group(tmp_path, monkeypatch):
    """⑤ 第三方目录 junction: 按 realpath 解析后的物理目录并组"""
    mgr, client, src, dst, content = _env(tmp_path)
    real = os.path.join(str(tmp_path), "real")
    os.makedirs(os.path.join(real, "Show"))
    with open(os.path.join(real, "Show", "e00.mkv"), "wb") as f:
        f.write(b"x" * 64)
    link = os.path.join(str(tmp_path), "linked")
    try:
        alias_fs.create_dir_alias(link, real, alias_fs.KIND_JUNCTION)
    except Exception as e:  # noqa: BLE001 - 环境无 junction 能力: skip 而非 fail(同 alias_fs 守阵口径)
        pytest.skip(f"本机 cannot 建 junction: {e}")
    client.files_map["HD"] = [_fake_file("Show/e00.mkv", 64)]
    hd = FakeTorrent(hash="HD", name="Show", save_path=link, progress=1.0, state="pausedUP")
    client.torrents["HD"] = hd
    seed_store(mgr, [client.torrents["HA"], client.torrents["HB"], hd])
    grouping = mgr.host.get("grouping")
    grouping._assign_new_torrent("HD")
    key = mgr.store.member_to_key["HD"]
    assert key[0] == os.path.normcase(real).replace("\\", "/"), key[0]


def test_third_party_link_detected_and_relocation_blocked(tmp_path, monkeypatch):
    """⑥ 硬链接组: 组被打标(识别), 迁移闸门拒迁(hardlink) —— 搬走的是链接本身, 数据留原地"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content = _env(tmp_path)
    target = os.path.join(content, "e00.mkv")
    spare = os.path.join(str(tmp_path), "spare.mkv")
    os.remove(target)
    os.link(os.path.join(content, "e01.mkv"), target)  # e00 与 e01 互为硬链接: 代表文件 nlink>1
    assert os.path.exists(spare) is False
    grouping = mgr.host.get("grouping")
    grouping._assign_new_torrent("HA")
    grouping._assign_new_torrent("HB")
    key = mgr.store.member_to_key["HA"]
    assert key in mgr.store.third_party_link_groups, mgr.store.third_party_link_groups
    item = mgr.host.get("relocate").relocate_precheck(["HA"], dst)[0]
    assert item["cls"] == "blocked" and "hardlink" in [r["gate"] for r in item["reasons"]]


def test_resolver_identity_when_disabled(tmp_path):
    """解析恒等: 无 job + 普通目录 ⇒ 组键首元仍是原 save_path(开关关逐字节现状)"""
    mgr, client, src, dst, content = _env(tmp_path)
    mgr.config.relocate.enabled = False
    grouping = mgr.host.get("grouping")
    grouping._assign_new_torrent("HA")
    assert mgr.store.member_to_key["HA"][0] == src.replace("\\", "/")
    assert mgr.host.get("relocate").resolve_physical(src, content) == src


def test_regroup_scope_degenerate(tmp_path, monkeypatch):
    """重归组退化: 文件表读不到 -> 跳过该条; 作用域无人命中 -> 0"""
    mgr, client, src, dst, content = _env(tmp_path)
    grouping = mgr.host.get("grouping")
    monkeypatch.setattr(type(client), "torrents_files", lambda self, h: (_ for _ in ()).throw(RuntimeError("api down")))
    for t in mgr.store.by_hash.values():
        t._files = None
    assert grouping.regroup_scope(content, src) == 0
    monkeypatch.undo()
    assert grouping.regroup_scope(os.path.join(src, "Nope"), src) == 0


def test_cross_group_ghost_member_and_bad_path(tmp_path, monkeypatch):
    """跨组检测退化: 组内幽灵成员(快照无)跳过; 目录 realpath 抛错回退词法不中断"""
    mgr, client, src, dst, content = _env(tmp_path)
    mgr.config.grouping.cross_group_conflict_check = True
    grouping = mgr.host.get("grouping")
    grouping._assign_new_torrent("HA")
    key = mgr.store.member_to_key["HA"]
    mgr.store.groups[key].append("HGHOST")  # 幽灵成员: 组表有, 快照无
    from auto_qb.infra import file_access as fa_mod

    fa = fa_mod.get_file_access()
    monkeypatch.setattr(fa, "realpath_lexical", lambda p: (_ for _ in ()).throw(ValueError("bad path")))
    client.calls.clear()
    grouping._check_cross_group_file_conflicts(dry_run=False)  # 不抛即为通过
