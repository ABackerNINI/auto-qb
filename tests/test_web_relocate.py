"""test_web_relocate 测试计划: 整组迁移 P2 预检的模块面/路由面/drain 面(计划 26-10-18-1604 P2)

验收判据(plan §04 P2): 预检零副作用(不写 state、无 qB 写调用); 路由 fail-closed 门控;
回执经 cmd 通道 truth 字段带出(与跳检预检同形状)。

## 测试计划(每个测试函数一条)
- test_relocate_module_precheck_ok_and_confirm: 真临时目录 + 双成员组: F=2 -> ok(file_links);
  F=9 + 专属子目录 -> confirm(dir_alias, 需确认); qB 写调用零条 + state 深比对不变
- test_relocate_module_precheck_gone_and_param: 未知 hash -> gone/blocked; 空 location -> param/blocked
- test_relocate_module_precheck_target_conflict_gate: 目标已存在同名内容 -> blocked(target_conflict)
- test_relocate_module_precheck_unfinished_job_gate: 非终态 job 碰本组 -> blocked(unfinished, S10)
- test_relocate_module_precheck_readonly_proof: 预检前后 qB 写调用零条 + state 深比对不变(独立断言)
- test_relocate_module_precheck_add: 添加预检 ok / confirm(目录别名作用域, 实际落点+卷剩余) /
  confirm(收尾窗口) / confirm(同名链接覆盖)
- test_web_relocate_precheck_routes: 路由级 403(关, 零入队)/ 400(空 hashes/空 location/缺 name)/
  门开后入队 cmd 与载荷形状
- test_web_relocate_precheck_drain: drain 级回执 truth={results, summary} 结构 + gone verdict +
  混合计数; precheck_add 回执 truth=单 item
"""
import json
import os
import shutil

from auto_qb.core.modules.relocate_units import RelocateJob

from helpers import FakeClient, FakeTorrent, _fake_file, make_manager, seed_store


def _pin_disk_usage(monkeypatch, free=1024**4):
    """把 disk_usage 钉成固定值: 同卷证明/空间闸门不再受并行写盘抖动影响(测试确定性)"""
    from auto_qb.infra import file_access as fa_mod

    monkeypatch.setattr(
        fa_mod.LocalFileAccess,
        "disk_usage",
        lambda self, path: fa_mod.DiskUsage(total=free * 10, used=0, free=free),
    )
    return free


def _make_group_env(td, file_count=2, subdir="Show", free=1024**4):
    """真临时目录 + 双成员组(HA/HB 同内容)的环境; 返回 (mgr, client, src, dst, content)

    同卷证明(§2.4)的 qB 侧读数与 disk_usage 一并钉在 free(测试确定性; 真实判据的
    抖动容差由 same_volume_proof 自身的容差带承担)。
    """
    mgr = make_manager(os.path.join(td, "state.json"))
    client = FakeClient()
    mgr.client = client
    src = os.path.join(td, "src")
    dst = os.path.join(td, "dst")
    content = os.path.join(src, subdir)
    os.makedirs(content)
    os.makedirs(dst)  # 目标卷必须真实存在(exists/scandir 才可判定)
    files = []
    for i in range(file_count):
        name = f"{subdir}/e{i:02d}.mkv"
        with open(os.path.join(content, f"e{i:02d}.mkv"), "wb") as f:
            f.write(b"x" * 64)
        files.append(_fake_file(name, 100))
    client.files_map["HA"] = list(files)
    client.files_map["HB"] = list(files)
    tors = [
        FakeTorrent(hash="HA", name="Show", save_path=src, progress=1.0, state="pausedUP"),
        FakeTorrent(hash="HB", name="Show", save_path=src, progress=1.0, state="pausedUP"),
    ]
    for t in tors:
        client.torrents[t.hash] = t
    seed_store(mgr, tors)
    grouping = mgr.host.get("grouping")
    grouping._assign_new_torrent("HA")
    grouping._assign_new_torrent("HB")
    # 同卷证明(§2.4): qB 上报 free_space_on_disk = 本机源卷剩余(钉值, 见 _pin_disk_usage)
    mgr.store.server_state = {"free_space_on_disk": free}
    mgr.config.relocate.enabled = True
    return mgr, client, src, dst, content


def test_relocate_module_precheck_ok_and_confirm(tmp_path, monkeypatch):
    """双成员组: F=2 -> ok(file_links); F=9+专属子目录 -> confirm(dir_alias); 零 qB 写调用"""
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content = _make_group_env(tmp_path, file_count=2)
    mod = mgr.host.get("relocate")
    items = mod.relocate_precheck(["HA", "HB"], dst)
    assert len(items) == 1, items
    item = items[0]
    assert item["cls"] == "ok", (item["cls"], item["reasons"])
    assert item["form"] == "file_links" and item["hashes"] == ["HA", "HB"] and item["mover"] == "HA"
    assert item["target_free"] is not None and item["same_volume"] is True
    assert client.calls == [], f"预检零 qB 写调用: {client.calls}"
    # F=9 + 专属子目录 -> 目录别名需确认
    mgr2, _c2, src2, dst2, content2 = _make_group_env(tmp_path / "b", file_count=9)
    mod2 = mgr2.host.get("relocate")
    item2 = mod2.relocate_precheck(["HA", "HB"], dst2)[0]
    assert item2["cls"] == "confirm", (item2["cls"], item2["reasons"])
    assert item2["form"] == "dir_alias" and item2["needs_confirm"] is True
    assert item2["alias_kind"], "本机探测至少应给出一种目录别名形态"


def test_relocate_module_precheck_gone_and_param(tmp_path, monkeypatch):
    """未知 hash -> gone/blocked(逐条); 空 location -> param/blocked"""
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content = _make_group_env(tmp_path)
    mod = mgr.host.get("relocate")
    items = mod.relocate_precheck(["HA", "HMISSING"], dst)
    assert len(items) == 2
    gone = [i for i in items if i.get("hash") == "HMISSING"][0]
    assert gone["cls"] == "blocked" and gone["reasons"][0]["gate"] == "gone"
    items2 = mod.relocate_precheck(["HA"], "")
    assert items2[0]["cls"] == "blocked" and items2[0]["reasons"][0]["gate"] == "param"


def test_relocate_module_precheck_target_conflict_gate(tmp_path, monkeypatch):
    """目标已存在同名内容 -> blocked(target_conflict): qB 会走全量校验(进度清零)"""
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content = _make_group_env(tmp_path, file_count=2)
    os.makedirs(os.path.join(dst, "Show"), exist_ok=True)
    with open(os.path.join(dst, "Show", "e00.mkv"), "wb") as f:
        f.write(b"occupied")
    item = mgr.host.get("relocate").relocate_precheck(["HA", "HB"], dst)[0]
    assert item["cls"] == "blocked" and "target_conflict" in [r["gate"] for r in item["reasons"]]


def test_relocate_module_precheck_unfinished_job_gate(tmp_path, monkeypatch):
    """非终态 job 碰本组 -> blocked(unfinished): 链接套链接会让旧迁移收尾失效(S10)"""
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content = _make_group_env(tmp_path)
    mod = mgr.host.get("relocate")
    mod.register_job(
        RelocateJob(
            job_id="j1",
            hashes=("HA", "HB"),
            mover="HA",
            src=src,
            dst=dst,
            scope=content,
            alias_kind="file",
            phase="armed",
        )
    )
    item = mod.relocate_precheck(["HA", "HB"], dst)[0]
    assert item["cls"] == "blocked" and "unfinished" in [r["gate"] for r in item["reasons"]]


def test_relocate_module_precheck_readonly_proof(tmp_path, monkeypatch):
    """预检零副作用独立证明: qB 写调用零条 + state 深比对不变 + store 组结构不变"""
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content = _make_group_env(tmp_path, file_count=9)
    state_before = json.dumps(mgr.state, sort_keys=True, ensure_ascii=False)
    groups_before = {k: list(v) for k, v in mgr.store.groups.items()}
    mod = mgr.host.get("relocate")
    items = mod.relocate_precheck(["HA", "HB"], dst)
    assert items and items[0]["cls"] == "confirm"
    assert client.calls == [], f"预检零 qB 写调用: {client.calls}"
    assert json.dumps(mgr.state, sort_keys=True, ensure_ascii=False) == state_before, "state 被写入"
    assert {k: list(v) for k, v in mgr.store.groups.items()} == groups_before, "分组结构被改"


def _fwd(p):
    """回执路径是词法归一口径(正斜杠), 断言前统一(仅测试侧)"""
    return str(p).replace("\\", "/")


def test_relocate_module_precheck_qb_temp_gate(tmp_path, monkeypatch):
    """内容根存在 qB 未完成孪生(原名 + .!qB 后缀) -> blocked(qb_temp): 数据尚未落定"""
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content = _make_group_env(tmp_path, file_count=2)
    with open(os.path.join(content, "e00.mkv.!qB"), "wb") as f:
        f.write(b"partial")
    item = mgr.host.get("relocate").relocate_precheck(["HA", "HB"], dst)[0]
    assert item["cls"] == "blocked" and "qb_temp" in [r["gate"] for r in item["reasons"]]
    assert any("e00.mkv.!qB" in r["text"] for r in item["reasons"])


def test_relocate_module_precheck_defensive_paths(tmp_path):
    """纵深防御与退化入参: 未启用 / 空 hashes / 上下文缺失 / qB 未连接 各自 blocked 自解释"""
    from types import SimpleNamespace

    from auto_qb.config.models import RelocateConfig

    mgr, client, src, dst, content = _make_group_env(tmp_path)
    mod = mgr.host.get("relocate")
    # 未启用(路由层已 403, 模块侧兜底)
    mgr.config.relocate.enabled = False
    items = mod.relocate_precheck(["HA"], dst)
    assert items[0]["cls"] == "blocked" and items[0]["reasons"][0]["gate"] == "disabled"
    mgr.config.relocate.enabled = True
    # 空 hashes
    items = mod.relocate_precheck([], dst)
    assert items[0]["cls"] == "blocked" and items[0]["reasons"][0]["gate"] == "param"
    # ctx 缺失(现取配置回退到 _conf 缓存)
    mod2 = type(mod)()
    mod2._conf = RelocateConfig(enabled=True)
    items = mod2.relocate_precheck(["HA"], dst)
    assert items[0]["cls"] == "blocked" and items[0]["reasons"][0]["gate"] == "unavailable"
    # qB 客户端未连接
    mod3 = type(mod)()
    mod3._ctx = SimpleNamespace(config=mgr.config, store=mgr.store, api=None)
    items = mod3.relocate_precheck(["HA"], dst)
    assert items[0]["cls"] == "blocked" and items[0]["reasons"][0]["gate"] == "unavailable"


def test_relocate_module_start_and_apply_probe_wiring(tmp_path):
    """启动/热重载接线: enabled 时 start 探测一次、apply 段变重探; 文案随开关变化"""
    from auto_qb.config.models import RelocateConfig

    mgr, client, src, dst, content = _make_group_env(tmp_path)
    mod = mgr.host.get("relocate")
    mod.start(mgr.ctx, dry_run=False)  # enabled=True -> 探测 + INFO
    assert mod._conf is mgr.config.relocate
    old = mgr.config
    new = SimpleCfg(relocate=RelocateConfig(enabled=True, alias_file_threshold=12))
    res = mod.apply(old, new)
    assert res.module == "relocate" and res.action == "reloaded" and "重探" in res.detail
    res2 = mod.apply(new, new)  # 段相等短路
    assert res2.action == "none"
    new2 = SimpleCfg(relocate=RelocateConfig(enabled=False))
    res3 = mod.apply(new, new2)
    assert "未启用不重探" in res3.detail


class SimpleCfg:
    """最小 Config 替身(只带 relocate 段; 模块 apply 按段属性读)"""
    def __init__(self, relocate):
        self.relocate = relocate


def test_relocate_module_fs_fact_branches(tmp_path, monkeypatch):
    """事实收集退化分支: 能力全不可用(提权文案+三出路)/ 目标存在性不可判定 / 空间不可判定"""
    from auto_qb.infra import alias_fs, file_access as fa_mod
    from auto_qb.infra.alias_fs import AliasCapability, LinkProbe

    mgr, client, src, dst, content = _make_group_env(tmp_path, file_count=2)
    mod = mgr.host.get("relocate")
    failed = LinkProbe(False, error="权限不足(需提权/UAC): 以管理员身份运行 auto-qb")
    cap = AliasCapability(
        process_os="windows",
        host_os="windows",
        container=False,
        wsl=False,
        path_style="windows",
        foreign_fs=None,
        link_visible_to_host=True,
        junction=failed,
        dir_symlink=failed,
        file_symlink=failed,
        hardlink=failed,
        uac_available=False,
        probe_root=src,
        probed_at=0.0,
    )
    monkeypatch.setattr(alias_fs, "get_capability", lambda refresh=False: cap)
    # 能力全不可用: 多成员组 blocked(platform), 文件级链接不可建的原因带提权与出路
    item = mod.relocate_precheck(["HA", "HB"], dst)[0]
    assert item["cls"] == "blocked"
    gates = [r["gate"] for r in item["reasons"]]
    assert "platform" in gates and "form" in gates
    assert any("提权" in r["text"] and "出路" in r["text"] for r in item["reasons"])
    # 目标存在性不可判定(容器映射 miss) -> target_unknown
    monkeypatch.setattr(fa_mod.LocalFileAccess, "exists", lambda self, p: fa_mod.UNDETERMINED)
    item2 = mod.relocate_precheck(["HA", "HB"], dst)[0]
    assert "target_unknown" in [r["gate"] for r in item2["reasons"]]
    monkeypatch.undo()
    _pin_disk_usage(monkeypatch)  # 恢复 disk_usage 钉值后重挂「抛错」变体
    monkeypatch.setattr(fa_mod.LocalFileAccess, "disk_usage", lambda self, p: (_ for _ in ()).throw(OSError("no disk")))
    item3 = mod.relocate_precheck(["HA", "HB"], dst)[0]
    gates3 = [r["gate"] for r in item3["reasons"]]
    assert "space" in gates3 and "same_fs" in gates3  # 空间不可判定 + 同卷证明读不到


def test_relocate_module_precheck_scandir_and_lstat_degraded(tmp_path, monkeypatch):
    """内容根 listing 失败 -> 不专属(目录别名不可用); 代表文件不可读 -> 识别降级 note"""
    mgr, client, src, dst, content = _make_group_env(tmp_path, file_count=2)
    # 文件表与磁盘不一致: 记录里的文件不在盘上 -> scandir 失败 + lstat 失败
    ghost = [_fake_file("Show/ghost.mkv", 100)]
    client.files_map["HA"] = list(ghost)
    client.files_map["HB"] = list(ghost)
    for t in (mgr.store.by_hash["HA"], mgr.store.by_hash["HB"]):
        t._files = None  # 失效惰性缓存, 重拉
    item = mgr.host.get("relocate").relocate_precheck(["HA", "HB"], dst)[0]
    assert item["cls"] == "blocked" and item["form"] == "file_links"  # 不专属 -> 逐文件
    notes = " ".join(item["notes"])
    assert "杂项" in notes and "不可读" in notes


def test_relocate_module_precheck_classify_entries(tmp_path, monkeypatch):
    """内容根多出条目分类: 同 save_path 其它种子的文件 -> 组外占用; 散落 .torrent -> 杂项"""
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content = _make_group_env(tmp_path, file_count=2)
    # 组外种子 HC: 同 save_path, 文件落在同一内容根(分集同目录; 盘上要有真实文件, listing 才看得到)
    ext_files = [_fake_file("Show/S01E02.mkv", 100)]
    client.files_map["HC"] = ext_files
    with open(os.path.join(content, "S01E02.mkv"), "wb") as f:
        f.write(b"x" * 64)
    hc = FakeTorrent(hash="HC", name="ShowE02", save_path=src, progress=1.0, state="pausedUP")
    client.torrents["HC"] = hc
    seed_store(mgr, [hc, client.torrents["HA"], client.torrents["HB"]])  # seed_store 整体替换, 三种一起灌
    mgr.host.get("grouping")._assign_new_torrent("HC")
    # 杂项: 内容根里散落的 .torrent 文件
    with open(os.path.join(content, "E01.torrent"), "wb") as f:
        f.write(b"junk")
    item = mgr.host.get("relocate").relocate_precheck(["HA", "HB"], dst)[0]
    notes = " ".join(item["notes"])
    assert "S01E02.mkv" in notes and "E01.torrent" in notes
    assert item["cls"] in ("ok", "confirm")  # 组外/杂项只影响形态, 不硬拒


def test_relocate_module_capability_view(tmp_path):
    """能力面板: alias_fs 六项探测事实 + enabled 状态"""
    mgr, client, src, dst, content = _make_group_env(tmp_path)
    view = mgr.host.get("relocate").capability_view()
    for key in ("junction", "dir_symlink", "file_symlink", "hardlink", "uac_available", "container", "enabled"):
        assert key in view, key
    assert view["enabled"] is True


def test_relocate_module_precheck_add_disk_usage_degraded(tmp_path, monkeypatch):
    """添加预检: 命中作用域但目标卷剩余读不到 -> volume_free=None(展示「不可判定」不猜)"""
    from auto_qb.infra import file_access as fa_mod

    mgr, client, src, dst, content = _make_group_env(tmp_path)
    mod = mgr.host.get("relocate")
    mod.register_job(
        RelocateJob(
            job_id="j1", hashes=("HA", ), mover="HA", src=src, dst=dst, scope=content, alias_kind="dir", phase="armed"
        )
    )
    monkeypatch.setattr(
        fa_mod.LocalFileAccess,
        "disk_usage",
        lambda self, p: (_ for _ in ()).throw(fa_mod.FileAccessError("miss")),
    )
    r = mod.precheck_add(src, "Show")
    assert r["cls"] == "confirm" and r["volume_free"] is None


def test_relocate_module_branch_extras(tmp_path, monkeypatch):
    """覆盖补齐: start 未启用 / 文件表读取失败 / 单文件平铺内容根 / 目标存在性抛错 /
    allow_uac=false 拒绝文案 / UNC 目标 / 真硬链接拒迁 / realpath 抛错降级"""
    from auto_qb.config.models import RelocateConfig
    from auto_qb.infra import alias_fs, file_access as fa_mod

    mgr, client, src, dst, content = _make_group_env(tmp_path, file_count=2)
    mod = mgr.host.get("relocate")
    # start 未启用: 只 debug 不探测(零副作用面)
    mgr.config.relocate.enabled = False
    mod.start(mgr.ctx, dry_run=False)
    mgr.config.relocate.enabled = True
    # 单文件平铺: 内容根 = save_path 本身(file_links; _top_children 平铺分支)
    solo_files = [_fake_file("solo.mkv", 100)]
    client.files_map["HD"] = list(solo_files)
    solo = FakeTorrent(
        hash="HD", name="solo", save_path=os.path.join(td_src := src, "solo"), progress=1.0, state="pausedUP"
    )
    solo_dir = os.path.join(src, "solo")
    os.makedirs(solo_dir, exist_ok=True)
    with open(os.path.join(solo_dir, "solo.mkv"), "wb") as f:
        f.write(b"x" * 64)
    client.torrents["HD"] = solo
    seed_store(mgr, [solo, client.torrents["HA"], client.torrents["HB"]])
    mgr.host.get("grouping")._assign_new_torrent("HD")
    item = mod.relocate_precheck(["HD"], dst)[0]
    assert item["form"] == "direct" and item["file_count"] == 1  # 单成员组: qB 自搬不需要别名

    # 文件表读取失败: files API 抛错 -> 空表 -> plan 拒绝(文件列表为空), 不炸
    def _boom(h):
        raise RuntimeError("api down")

    monkeypatch.setattr(type(client), "torrents_files", _boom)
    for t in (mgr.store.by_hash["HA"], mgr.store.by_hash["HB"]):
        t._files = None
    item2 = mod.relocate_precheck(["HA", "HB"], dst)[0]
    assert item2["cls"] == "blocked" and "form" in [r["gate"] for r in item2["reasons"]]
    monkeypatch.undo()
    _pin_disk_usage(monkeypatch)

    # 目标存在性「抛错」(而非 UNDETERMINED) -> 同样按不可判定拒绝
    def _raise_exists(self, p):
        raise RuntimeError("fs io")

    monkeypatch.setattr(fa_mod.LocalFileAccess, "exists", _raise_exists)
    item3 = mod.relocate_precheck(["HA", "HB"], dst)[0]
    assert "target_unknown" in [r["gate"] for r in item3["reasons"]]
    monkeypatch.undo()
    _pin_disk_usage(monkeypatch)
    # allow_uac=false + 文件级链接需提权 -> 拒绝文案注明「不弹 UAC, 直接拒绝」
    mgr.config.relocate.allow_uac = False
    failed = alias_fs.LinkProbe(False, error="权限不足(需提权/UAC): 以管理员身份运行 auto-qb")
    cap = alias_fs.AliasCapability(
        process_os="windows",
        host_os="windows",
        container=False,
        wsl=False,
        path_style="windows",
        foreign_fs=None,
        link_visible_to_host=True,
        junction=failed,
        dir_symlink=failed,
        file_symlink=failed,
        hardlink=failed,
        uac_available=False,
        probe_root=src,
        probed_at=0.0,
    )
    monkeypatch.setattr(alias_fs, "get_capability", lambda refresh=False: cap)
    monkeypatch.setattr(alias_fs, "is_unc", lambda p: True)  # UNC 目标: junction 不可用 -> 目录 symlink 分支
    item4 = mod.relocate_precheck(["HA", "HB"], dst)[0]
    assert any("allow_uac=false" in r["text"] for r in item4["reasons"])
    monkeypatch.undo()
    _pin_disk_usage(monkeypatch)
    # 真硬链接(组文件 nlink>1) -> blocked(hardlink, D11)
    hl_link = os.path.join(dst, "alias-probe")
    with open(hl_link, "wb") as f:
        f.write(b"x")
    os.remove(hl_link)  # 先移除占位文件, 再建指向组文件的硬链接
    os.link(os.path.join(content, "e00.mkv"), hl_link)
    item5 = mod.relocate_precheck(["HA", "HB"], dst)[0]
    assert "hardlink" in [r["gate"] for r in item5["reasons"]], item5["reasons"]
    os.remove(hl_link)

    # realpath_lexical 抛错 -> 目录级链接检测静默降级(无 note 崩溃)
    def _raise_rt(self, p):
        raise RuntimeError("rt")

    monkeypatch.setattr(fa_mod.LocalFileAccess, "realpath_lexical", _raise_rt)
    item6 = mod.relocate_precheck(["HA", "HB"], dst)[0]
    assert item6["cls"] in ("ok", "confirm", "blocked")


def test_relocate_module_classify_entries_degenerate(tmp_path, monkeypatch):
    """组外分类退化: 其它 save_path 的种子跳过; 记录字段异常的单条跳过不炸"""
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content = _make_group_env(tmp_path, file_count=2)
    elsewhere = FakeTorrent(hash="HX", name="Else", save_path="R:/elsewhere", progress=1.0, state="pausedUP")
    client.files_map["HX"] = [_fake_file("Show/e00.mkv", 100)]  # 即便同名也因 save_path 不同不算组外
    client.torrents["HX"] = elsewhere
    broken = FakeTorrent(hash="HBROKEN", name="Broken", save_path=None, progress=1.0, state="pausedUP")
    client.files_map["HBROKEN"] = [_fake_file("Show/x.mkv", 100)]
    client.torrents["HBROKEN"] = broken
    seed_store(mgr, [elsewhere, broken, client.torrents["HA"], client.torrents["HB"]])
    for h in ("HX", "HBROKEN"):
        mgr.host.get("grouping")._assign_new_torrent(h)
    # 杂项条目触发分类循环
    with open(os.path.join(content, "E01.torrent"), "wb") as f:
        f.write(b"junk")
    item = mgr.host.get("relocate").relocate_precheck(["HA", "HB"], dst)[0]
    notes = " ".join(item["notes"])
    assert "E01.torrent" in notes and "S01E02" not in notes  # 异 save_path 不算组外


def test_relocate_module_precheck_scandir_missing_root(tmp_path, monkeypatch):
    """内容根目录消失(记录与磁盘脱节) -> listing 失败 -> 不专属 -> 逐文件链接(不猜)"""
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content = _make_group_env(tmp_path, file_count=2)
    shutil.rmtree(content)
    item = mgr.host.get("relocate").relocate_precheck(["HA", "HB"], dst)[0]
    assert item["form"] == "file_links" and item["cls"] in ("ok", "confirm", "blocked")


def test_relocate_module_precheck_add(tmp_path):
    """添加预检: ok / confirm(目录别名作用域 -> 实际落点+卷剩余) / confirm(收尾窗口) /
    confirm(同名链接覆盖)"""
    mgr, client, src, dst, content = _make_group_env(tmp_path)
    mod = mgr.host.get("relocate")
    # 无 job: ok
    r = mod.precheck_add(src, "Other.Show")
    assert r["cls"] == "ok" and _fwd(r["requested_path"]) == _fwd(os.path.join(src, "Other.Show"))
    # 目录别名作用域命中: confirm + 实际落点(dst 下) + 卷剩余
    mod.register_job(
        RelocateJob(
            job_id="j1", hashes=("HA", ), mover="HA", src=src, dst=dst, scope=content, alias_kind="dir", phase="armed"
        )
    )
    r = mod.precheck_add(src, "Show")
    assert r["cls"] == "confirm" and r["reasons"][0]["gate"] == "alias_scope"
    assert _fwd(r["actual_path"]) == _fwd(os.path.join(dst, "Show")) and r["volume_free"] is not None
    # 收尾窗口: confirm 警示重复落盘
    mod.register_job(
        RelocateJob(
            job_id="j2",
            hashes=("HA", ),
            mover="HA",
            src=src,
            dst=dst,
            scope=content,
            alias_kind="dir",
            phase="removed"
        )
    )
    r = mod.precheck_add(src, "Late.Show")
    assert r["cls"] == "confirm" and r["reasons"][0]["gate"] == "finalize_window"
    # 同名链接覆盖: 落点是真硬链接 -> confirm alias_file
    mod._jobs.clear()
    mod.register_job(
        RelocateJob(
            job_id="j3", hashes=("HA", ), mover="HA", src=src, dst=dst, scope=content, alias_kind="file", phase="armed"
        )
    )
    landing = os.path.join(content, "S01E01.mkv")
    with open(os.path.join(dst, "S01E01.mkv"), "wb") as f:
        f.write(b"data")
    os.link(os.path.join(dst, "S01E01.mkv"), landing)
    r = mod.precheck_add(src, "Show/S01E01.mkv")
    assert r["cls"] == "confirm" and r["reasons"][0]["gate"] == "alias_file", (r["cls"], r["reasons"])
    assert "覆盖" in r["reasons"][0]["text"]
    # 参数缺失 -> blocked(param)
    r = mod.precheck_add(src, "")
    assert r["cls"] == "blocked" and r["reasons"][0]["gate"] == "param"


def test_web_relocate_precheck_routes(web_env):
    """路由级: 403(关, 零入队, detail 注键名) / 400(空 hashes/空 location/缺 name) /
    门开后入队 cmd 与载荷形状"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    # 关(缺省 enabled=False): 403 零入队
    resp = client.post("/api/torrents/relocate/precheck", headers=auth, json={"hashes": ["HA"], "location": "H:/x"})
    assert resp.status_code == 403, resp.text
    assert "relocate.enabled" in resp.json()["detail"]
    assert mgr.web.commands.empty()
    resp = client.post("/api/relocate/precheck-add", headers=auth, json={"save_path": "H:/x", "name": "n"})
    assert resp.status_code == 403 and mgr.web.commands.empty()
    # 开: 入队形状
    mgr.config.relocate.enabled = True
    resp = client.post(
        "/api/torrents/relocate/precheck", headers=auth, json={
            "hashes": ["HA", "HB"],
            "location": "H:/x"
        }
    )
    assert resp.status_code == 200 and resp.json()["queued"] is True, resp.text
    cmd, payload = mgr.web.commands.get_nowait()
    assert cmd == "relocate_precheck", (cmd, payload)
    payload.pop("cmd_id")
    payload.pop("_queued_ts", None)
    assert payload == {"hashes": ["HA", "HB"], "location": "H:/x"}, payload
    resp = client.post("/api/relocate/precheck-add", headers=auth, json={"save_path": "H:/x", "name": "Show"})
    assert resp.status_code == 200
    cmd, payload = mgr.web.commands.get_nowait()
    assert cmd == "relocate_precheck_add", (cmd, payload)
    payload.pop("cmd_id")
    payload.pop("_queued_ts", None)
    assert payload == {"save_path": "H:/x", "name": "Show"}, payload
    # 400: 参数校验在路由层, 不入队
    for body in ({}, {"hashes": [], "location": "H:/x"}, {"hashes": ["HA"], "location": ""}):
        resp = client.post("/api/torrents/relocate/precheck", headers=auth, json=body)
        assert resp.status_code == 400, (body, resp.text)
    assert mgr.web.commands.empty()
    for body in ({}, {"save_path": "H:/x"}, {"name": "n"}):
        resp = client.post("/api/relocate/precheck-add", headers=auth, json=body)
        assert resp.status_code == 400, (body, resp.text)
    assert mgr.web.commands.empty()


def test_web_relocate_precheck_drain(tmp_path, monkeypatch):
    """drain 级: 回执 truth={results, summary} 结构 + gone verdict + 混合计数;
    precheck_add 回执 truth=单 item"""
    _pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content = _make_group_env(tmp_path, file_count=2)
    mgr.web.commands.put(("relocate_precheck", {"hashes": ["HA", "HMISSING"], "location": dst, "cmd_id": "rp1"}))
    mgr.web.consume_commands()
    rec = mgr.web.results["rp1"]
    assert rec["status"] == "ok", rec
    data = rec["truth"]
    assert set(data) == {"results", "summary"}, data
    results, summary = data["results"], data["summary"]
    assert len(results) == 2, results
    group_item = [r for r in results if "hashes" in r][0]
    assert group_item["cls"] == "ok" and group_item["form"] == "file_links"
    gone = [r for r in results if r.get("hash") == "HMISSING"][0]
    assert gone["cls"] == "blocked" and gone["reasons"][0]["gate"] == "gone"
    assert summary == {"ok": 1, "confirm": 0, "blocked": 1}, summary
    assert client.calls == [], f"drain 预检零 qB 写调用: {client.calls}"
    # precheck_add drain: truth = 单 item
    mgr.web.commands.put(("relocate_precheck_add", {"save_path": src, "name": "Other", "cmd_id": "rpa1"}))
    mgr.web.consume_commands()
    rec = mgr.web.results["rpa1"]
    assert rec["status"] == "ok" and rec["truth"]["cls"] == "ok", rec
    assert _fwd(rec["truth"]["requested_path"]) == _fwd(os.path.join(src, "Other"))


def test_relocate_add_gate_wired_in_add_dialog():
    """P5 前端契约: 添加对话框提交前调落点预检, 取消则不提交; 投递点已登记(triggers 金清单)"""
    from pathlib import Path

    shared = Path(__file__).resolve().parents[1] / "src" / "auto_qb" / "webui" / "static" / "shared"
    add_js = (shared / "add_torrent.js").read_text(encoding="utf-8")
    assert "async _relocateAddGate()" in add_js, "落点预检方法缺失"
    assert "/api/relocate/precheck-add" in add_js
    # 顺序: 预检先于真正的添加投递(取消 = 直接 return, 不发 /api/torrents/add)
    assert add_js.index("if (!(await this._relocateAddGate())) return;") < add_js.index('"/api/torrents/add"')
    assert "if (!(await this._relocateAddGate())) return;" in add_js
    # 预检不可用一律放行(功能未启用 403 / 网络异常不挡添加)
    assert "return true" in add_js.split("async _relocateAddGate()")[1].split("async submitAddTorrent()")[0]
    triggers = (shared / "triggers.js").read_text(encoding="utf-8")
    assert '"fn": "_relocateAddGate"' in triggers, "投递点必须登记进 triggers.js 金清单"
