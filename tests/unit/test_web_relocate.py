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
- test_web_relocate_cancel_route: 撤销路由 403(关)/ 400(空 job_id)/ 门开后入队 cmd 与载荷形状
- test_web_relocate_cancel_drain: drain 级两步走(D6 停手语义): 未确认只回三段式确认面(D7 guide,
  数据零变动), 确认后删自己的链接 + phase=cancelled + journal 落盘(零 setLocation 不搬回;
  R1#24 的 MOVING 期硬拒撤随搬回能力退役, 半途撤销照常停手)
- test_web_relocate_precheck_drain: drain 级回执 truth={results, summary} 结构 + gone verdict +
- test_relocate_add_gate_wired_in_add_dialog
- test_relocate_confirm_loop_wired_in_move_dialog: 前端静态守阵(issue 26-11-04-0734): _editPost /
  _bulkEditPost 在 r.ok 且 truth.summary.confirm > 0 时返回 "confirm" 且不弹成功; submitMoveDialog
  先收设定位置框 -> _relocateConfirmGate 展示形态/来源/目标/未来种子/原因 -> 带 confirm=true 重发;
  confirm = 0 仍走原成功路径; 整组语义披露(计划 26-11-07-1300 R6): R6a move-dialog 常驻提示
  (relocate_enabled 旗标门控, flags 通路 fail-closed) + R6b 来源行接 member_count(>1 披露整组 N 个成员)
- test_web_relocate_confirm_passthrough_routes: 路由 confirm 透传契约 —— 缺省/False 载荷无 confirm
  键(历史形状不变), confirm=true 才附加(单种子 set_torrent_location + 批量 bulk_torrents)
- test_relocate_module_branch_extras
- test_relocate_module_capability_view
- test_relocate_module_classify_entries_degenerate
- test_relocate_module_fs_fact_branches
- test_relocate_module_precheck_add_disk_usage_degraded
- test_relocate_module_precheck_classify_entries
- test_relocate_module_precheck_defensive_paths
- test_relocate_module_precheck_qb_temp_gate
- test_relocate_module_precheck_qb_temp_foreign_demoted
- test_relocate_module_precheck_qb_temp_unowned_demoted
- test_relocate_volume_free_ancestor_fallback
- test_relocate_module_space_gate_ancestor_and_missing
- test_relocate_module_target_conflict_beyond_50
- test_relocate_module_target_is_file_blocked
- test_relocate_volume_free_resolved_degenerate
- test_relocate_module_classify_entries_per_record_error
- test_relocate_module_precheck_scandir_and_lstat_degraded
- test_relocate_module_precheck_scandir_missing_root
- test_relocate_module_same_fs_p3_semantics: P3 同机判据替换预检层 —— D 级 wiring(withMetadata="true"/
  列内容根)/ D 级判负硬拦(两条出路, reasons 元素 gate/cls/text 同形, gate id "same_fs";
  R1#35 后 B′ 级判负是弱证据不硬拦, 硬拦守阵由 D 级判负承载)/
  不可判定转 note 不拦 / E1 缓存凭据放行 / assume_shared 直通(note 注明由用户承担)
- test_relocate_module_start_and_apply_probe_wiring
- test_relocate_precheck_no_false_dir_link_note
  混合计数; precheck_add 回执 truth=单 item
- test_relocate_receipt_probing_acceptance_not_error: T4 受理段(D8) —— 仅探测中回 warn
  「已受理」非 blocked 错误(probing 桶独立计数, blocked 桶排除探测中); 探测中+真实拒绝
  仍 warn 带「另有 N 项被闸门拒绝」; 探测中+已发起混合走 ok; 缺失计数文案带探测中段
- test_web_relocate_probe_receipt_cmd_id_wired: 受理段绑定接线 —— 单种/批量两个调用点把
  cmd_id 传给 relocate_execute(receipt_cmd_id), 探测中 items 经命令全链出 warn 受理回执
- test_web_relocate_probe_two_phase_full_chain: 两段回执全链 —— web 命令受理(warn + cmd_id
  绑进 pending 条目 receipt_ids) -> verdict 消费重放建账 -> 出站面 -> WebUIModule
  on_command_line 排空补发(同 cmd_id 二次写覆盖 warn 为 ok + notify 推两次 cmd 事件)
- test_web_relocate_probe_terminal_drain_error_and_defense: 补发段 error 形态与防御面 ——
  重放异常/防自环终止的 error 回执(items 空不冒充终态); 无 cmd_id 条目跳过; relocate
  缺位/无 probe_receipts_take 时零动作
- test_web_relocate_probe_split_group_terminal_maps_ok: 拆组形态(R5 评审修复) —— passed
  verdict 但重放按新 save_path 拆组出混合 items(本组 started + 拆出组 probing gate):
  终态照常投 items 非 error(判别真值来源 = verdict 本体), drain 映射 ok(started+probing);
  重放透传条目 receipt_ids 首个(评审终审接缝修复, 指纹漂移重入队时绑定延续)
- test_web_relocate_probe_terminal_last_write_wins: 同一 cmd_id 绑多条 pending 条目(批量
  双组受理)-> 逐条各投终态 -> 一次 drain 二次写同 id 收敛 last-write-wins(后投条目明细),
  cmd 事件计数 = 受理 1 + 终态 2
"""
import json
import os
import queue
import shutil

from auto_qb.core.modules.relocate_units import PHASE_MOVING, RelocateJob

from clock import wait_until

from helpers import FakeClient, FakeTorrent, _fake_file, make_manager, pin_disk_usage, relocate_env, seed_store

from relocate_exec_support import _spy_spawn

from test_relocate_exec_probe_gate import _passed

from test_relocate_probe_consume import _recording_probe, _wire_async


def test_relocate_module_precheck_ok_and_confirm(tmp_path, monkeypatch):
    """双成员组: F=2 -> ok(file_links); F=9+专属子目录 -> confirm(dir_alias); 零 qB 写调用"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, _ = relocate_env(tmp_path, file_count=2, data_dir=False)
    mod = mgr.host.get("relocate")
    items = mod.relocate_precheck(["HA", "HB"], dst)
    assert len(items) == 1, items
    item = items[0]
    assert item["cls"] == "ok", (item["cls"], item["reasons"])
    assert item["form"] == "file_links" and item["hashes"] == ["HA", "HB"] and item["mover"] == "HA"
    assert item["target_free"] is not None and item["same_volume"] is True
    assert client.calls == [], f"预检零 qB 写调用: {client.calls}"
    # F=9 + 专属子目录 -> 目录别名需确认
    mgr2, _c2, src2, dst2, content2, _ = relocate_env(tmp_path / "b", file_count=9, data_dir=False)
    mod2 = mgr2.host.get("relocate")
    item2 = mod2.relocate_precheck(["HA", "HB"], dst2)[0]
    assert item2["cls"] == "confirm", (item2["cls"], item2["reasons"])
    assert item2["form"] == "dir_alias" and item2["needs_confirm"] is True
    assert item2["alias_kind"], "本机探测至少应给出一种目录别名形态"


def test_relocate_precheck_no_false_dir_link_note(tmp_path, monkeypatch):
    """P7 真机回归: 全大写内容根不误报「目录级链接」

    realpath_lexical 出口带 normcase(Windows = lowercase); 拿它与原始路径做大小写
    **敏感**比较恒不等 —— 任何含大写字母的正常目录都会被误报成目录级链接。两侧同过
    normcase 再比后, 只有**真实**链接(解析结果确实不同)才出该 note。
    """
    pin_disk_usage(monkeypatch)
    # 全大写内容根(比 tmp_path 默认混合大小写更严: 两侧 normcase 后必须相等)
    src = os.path.join(str(tmp_path), "SRC-UPPER")
    os.makedirs(src)
    content = os.path.join(src, "SHOW-UPPER")
    os.makedirs(content)
    for i in range(2):
        with open(os.path.join(content, f"E{i:02d}.mkv"), "wb") as f:
            f.write(b"x" * 64)
    dst = os.path.join(str(tmp_path), "DST-UPPER")
    os.makedirs(dst)
    mgr = make_manager(os.path.join(str(tmp_path), "state.json"))
    client = FakeClient()
    mgr.client = client
    client.files_map["HA"] = [_fake_file("SHOW-UPPER/e00.mkv", 100)]
    client.files_map["HB"] = [_fake_file("SHOW-UPPER/e01.mkv", 100)]
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
    mgr.store.server_state = {"free_space_on_disk": 1024**4}
    mgr.config.relocate.enabled = True
    item = mgr.host.get("relocate").relocate_precheck(["HA", "HB"], dst)[0]
    assert "目录级链接" not in " ".join(item.get("notes") or []), item.get("notes")
    assert not any("目录级链接" in (r.get("text") or "") for r in item.get("reasons") or [])


def test_relocate_module_precheck_gone_and_param(tmp_path, monkeypatch):
    """未知 hash -> gone/blocked(逐条); 空 location -> param/blocked"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, _ = relocate_env(tmp_path, data_dir=False)
    mod = mgr.host.get("relocate")
    items = mod.relocate_precheck(["HA", "HMISSING"], dst)
    assert len(items) == 2
    gone = [i for i in items if i.get("hash") == "HMISSING"][0]
    assert gone["cls"] == "blocked" and gone["reasons"][0]["gate"] == "gone"
    items2 = mod.relocate_precheck(["HA"], "")
    assert items2[0]["cls"] == "blocked" and items2[0]["reasons"][0]["gate"] == "param"


def test_relocate_module_precheck_target_conflict_gate(tmp_path, monkeypatch):
    """目标已存在同名内容 -> blocked(target_conflict): qB 会走全量校验(进度清零)"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, _ = relocate_env(tmp_path, file_count=2, data_dir=False)
    os.makedirs(os.path.join(dst, "Show"), exist_ok=True)
    with open(os.path.join(dst, "Show", "e00.mkv"), "wb") as f:
        f.write(b"occupied")
    item = mgr.host.get("relocate").relocate_precheck(["HA", "HB"], dst)[0]
    assert item["cls"] == "blocked" and "target_conflict" in [r["gate"] for r in item["reasons"]]


def test_relocate_module_precheck_unfinished_job_gate(tmp_path, monkeypatch):
    """搬迁在途 job 碰本组 -> blocked(unfinished): 叠加 setLocation 互相覆盖(S10; D15 收窄后
    前段相位仍拦, 收尾窗 armed/rewritten 放行 —— 放行面单测在 test_relocate_units)"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, _ = relocate_env(tmp_path, data_dir=False)
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
            phase="moving",
        )
    )
    item = mod.relocate_precheck(["HA", "HB"], dst)[0]
    assert item["cls"] == "blocked" and "unfinished" in [r["gate"] for r in item["reasons"]]


def test_relocate_module_precheck_readonly_proof(tmp_path, monkeypatch):
    """预检零副作用独立证明: qB 写调用零条 + state 深比对不变 + store 组结构不变"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, _ = relocate_env(tmp_path, file_count=9, data_dir=False)
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


def _stub_bprime_unavailable(monkeypatch):
    """把同机证明的 B′ 降级判定桩成「不可判定」—— 桩打在**判定层**, 不碰 os.stat

    !别用「桩 os.stat」造这个状态(2026-11-07 Linux CI 红的根): POSIX 的 `os.path.exists` 就是
    `posixpath.exists`(每次调用走 os.stat), 元数据桩会连带把 0808 S1 的源侧三态判成「声明文件
    缺失」并以 source_missing 抢拦, B′ 分支根本走不到; Windows 的 `os.path.exists` 是 C 内建、
    绕过 Python 层补丁, 于是同一份桩本地全绿、CI 全红。而真实 POSIX 上也**不存在**「stat 读不到
    但文件在盘」这个状态(stat 失败即不存在), 该刺激只能在判定层造。
    """
    from auto_qb.core.modules import relocate_proof as rp_mod

    monkeypatch.setattr(rp_mod, "_bprime_evidence", lambda *a, **kw: rp_mod._unavailable("B′ 桩: 成员元数据比对不可判定"))


def test_relocate_module_precheck_qb_temp_gate(tmp_path, monkeypatch):
    """本组文件的 .!qB 孪生(剥后缀对回本组 own) -> blocked(qb_temp): 本组数据尚未落定

    qb_temp 收窄(plan 26-11-02-0134)后硬拦面只剩本组; 外组/无主 .!qB 降 notes,
    见 test_relocate_module_precheck_qb_temp_foreign_demoted / _unowned_demoted。
    """
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, _ = relocate_env(tmp_path, file_count=2, data_dir=False)
    with open(os.path.join(content, "e00.mkv.!qB"), "wb") as f:
        f.write(b"partial")
    item = mgr.host.get("relocate").relocate_precheck(["HA", "HB"], dst)[0]
    assert item["cls"] == "blocked" and "qb_temp" in [r["gate"] for r in item["reasons"]]
    assert any("e00.mkv.!qB" in r["text"] for r in item["reasons"])


def test_relocate_module_precheck_qb_temp_foreign_demoted(tmp_path, monkeypatch):
    """外组种子的 .!qB 未完成文件 -> 不硬拦(qb_temp 收窄): 降级为组外 note

    qB 的搬运(libtorrent 1.2/2.0 aux::move_storage)只遍历种子自己的文件表逐文件搬,
    外组 .!qB 与本次迁移无因果作用 —— 与外来普通文件同口径(plan 26-11-02-0134)。
    """
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, _ = relocate_env(tmp_path, file_count=2, data_dir=False)
    # 组外种子 HC: 同 save_path, 单集下载中, 其 .!qB 孪生落在本组内容根(共享剧集目录场景)
    hc = FakeTorrent(hash="HC", name="413INSTC-305", save_path=src, progress=0.5, state="downloading")
    client.torrents["HC"] = hc
    client.files_map["HC"] = [_fake_file("Show/413INSTC-305.mp4", 100)]
    seed_store(mgr, [hc, client.torrents["HA"], client.torrents["HB"]])
    mgr.host.get("grouping")._assign_new_torrent("HC")
    with open(os.path.join(content, "413INSTC-305.mp4.!qB"), "wb") as f:
        f.write(b"partial")
    item = mgr.host.get("relocate").relocate_precheck(["HA", "HB"], dst)[0]
    assert item["cls"] == "ok", (item["cls"], item["reasons"])
    assert "qb_temp" not in [r["gate"] for r in item["reasons"]], item["reasons"]
    assert any("413INSTC-305.mp4.!qB" in n for n in item.get("notes") or []), item.get("notes")


def test_relocate_module_precheck_qb_temp_unowned_demoted(tmp_path, monkeypatch):
    """无主 .!qB(剥后缀对不回任何种子) -> 不硬拦(D1): 降级为杂项 note

    孤儿残留不被逐文件搬运触碰, 不该永久锁死该目录的迁移(plan 26-11-02-0134 D1)。
    """
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, _ = relocate_env(tmp_path, file_count=2, data_dir=False)
    with open(os.path.join(content, "LEFTOVER-ORPHAN.mkv.!qB"), "wb") as f:
        f.write(b"partial")
    item = mgr.host.get("relocate").relocate_precheck(["HA", "HB"], dst)[0]
    assert item["cls"] == "ok", (item["cls"], item["reasons"])
    assert "qb_temp" not in [r["gate"] for r in item["reasons"]], item["reasons"]
    assert any("LEFTOVER-ORPHAN.mkv.!qB" in n for n in item.get("notes") or []), item.get("notes")


def test_relocate_volume_free_ancestor_fallback(tmp_path, monkeypatch):
    """_volume_free_resolved: 叶子未建 -> 上溯最近存在祖先(plan R1 方案A); 裸名无分隔符 -> None

    真盘实证: shutil.disk_usage 对不存在的目录抛 FileNotFoundError(WinError 3),
    而目标目录尚未创建是迁移的正常输入(qB 落地时 libtorrent create_directories)。
    桩 disk_usage(存在回固定 free / 不存在抛错): 两次独立采样间任何后台写盘都会让
    全等断言偶发红(issue 26-11-02-0413), 钉死后语义不变、采样确定。
    """
    from auto_qb.core.modules.relocate_common import _volume_free_resolved
    from auto_qb.infra import file_access as fa_mod
    from auto_qb.infra.file_access import LocalFileAccess

    def pinned(self, p):
        clean = str(p).replace("\\\\?\\", "")
        if not os.path.exists(clean):
            raise FileNotFoundError(2, "系统找不到指定的路径", clean)
        return fa_mod.DiskUsage(total=10**12, used=0, free=500_000_000)

    monkeypatch.setattr(fa_mod.LocalFileAccess, "disk_usage", pinned)
    fa = LocalFileAccess()
    base = os.path.join(str(tmp_path), "existing-lib")
    os.makedirs(base)
    free_base = fa.disk_usage(base).free
    # 1. 已存在叶子: 原语义不变(自身卷)
    assert _volume_free_resolved(fa, base) == free_base
    # 2. 叶子未建: 祖先卷(新建目录将落的卷, junction/挂载点语义下同为该卷)
    assert _volume_free_resolved(fa, os.path.join(base, "NEW", "Show")) == free_base
    # 3. 裸名无分隔符: 无卷可判 -> None
    assert _volume_free_resolved(fa, "bare-name") is None
    # 4. 空串/None 入参: -> None
    assert _volume_free_resolved(fa, "") is None


def test_relocate_module_space_gate_ancestor_and_missing(tmp_path, monkeypatch):
    """空间闸门(方案A): 目标叶子未建 -> 祖先卷解析不再误拦; 整卷不可达 -> 仍硬拦

    桩 disk_usage: 存在的路径回固定值(同卷证明可控), 不存在/不可达抛错 —— 真实
    复刻 shutil.disk_usage 的失败形态(不存在即抛)。
    """
    from auto_qb.infra import file_access as fa_mod

    mgr, client, src, dst, content, _ = relocate_env(tmp_path, file_count=2, data_dir=False)

    def flaky(self, p):
        clean = str(p).replace("\\\\?\\", "")
        if "VOL-MISSING" in clean:
            raise fa_mod.FileAccessError("卷不可达")
        if not os.path.exists(clean):
            raise FileNotFoundError(2, "系统找不到指定的路径", clean)
        return fa_mod.DiskUsage(total=10**12, used=0, free=500_000_000)

    monkeypatch.setattr(fa_mod.LocalFileAccess, "disk_usage", flaky)
    mgr.store.server_state = {"free_space_on_disk": 500_000_000}
    # 1. 叶子未建(dst 存在): 祖先卷解析 => 无 space 闸门, 可迁移
    item = mgr.host.get("relocate").relocate_precheck(["HA", "HB"], os.path.join(dst, "NEWLIB", "Show"))[0]
    assert "space" not in [r["gate"] for r in item["reasons"]], item["reasons"]
    assert item["cls"] == "ok", (item["cls"], item["reasons"])
    # 2. 整卷不可达: 上溯全失败 => space 闸门照旧硬拦(真不可判定, 保守默认不破)
    item2 = mgr.host.get("relocate").relocate_precheck(["HA", "HB"], "VOL-MISSING:/newlib/Show")[0]
    assert "space" in [r["gate"] for r in item2["reasons"]], item2["reasons"]
    assert item2["cls"] == "blocked"


def test_relocate_module_target_conflict_beyond_50(tmp_path, monkeypatch):
    """R2 #2: 目标冲突检测覆盖全量文件(旧实现只查前 50, 第 51+ 的冲突会漏拦致进度清零)"""
    pin_disk_usage(monkeypatch)
    paths = tuple(f"Show/e{i:02d}.mkv" for i in range(60))
    mgr, client, src, dst, content, _ = relocate_env(tmp_path, file_count=60, data_dir=False, paths=paths)
    os.makedirs(os.path.join(dst, "Show"))
    with open(os.path.join(dst, "Show", "e59.mkv"), "wb") as f:
        f.write(b"conflict")
    item = mgr.host.get("relocate").relocate_precheck(["HA", "HB"], dst)[0]
    assert "target_conflict" in [r["gate"] for r in item["reasons"]], item["reasons"]
    assert item["cls"] == "blocked"


def test_relocate_module_target_is_file_blocked(tmp_path, monkeypatch):
    """R2 #3: 目标已存在但是文件 -> blocked(target_type): qB 无法在其下创建内容"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, _ = relocate_env(tmp_path, file_count=2, data_dir=False)
    with open(os.path.join(dst, "occupied.txt"), "wb") as f:
        f.write(b"x")
    item = mgr.host.get("relocate").relocate_precheck(["HA", "HB"], os.path.join(dst, "occupied.txt"))[0]
    assert "target_type" in [r["gate"] for r in item["reasons"]], item["reasons"]
    assert item["cls"] == "blocked"


def test_relocate_volume_free_resolved_degenerate(tmp_path, monkeypatch):
    """上溯退化面: 深层全缺失走尽层数上限 / 空目标 / 卷根不动点 => None(覆盖补齐)"""
    import auto_qb.infra.alias_fs as alias_fs

    from auto_qb.core.modules.relocate_common import _same_volume_resolved, _volume_free_resolved
    from auto_qb.infra.file_access import LocalFileAccess

    fa = LocalFileAccess()
    deep = os.path.join(str(tmp_path), *tuple(f"d{i}" for i in range(70)))
    assert _volume_free_resolved(fa, deep) is None  # 64 层上溯走尽仍不存在
    assert _volume_free_resolved(fa, "") is None
    # 同卷: 桩 same_volume 恒 None -> 卷根不动点/走尽层数/空目标 都 None(纯词法, 不触盘)
    monkeypatch.setattr(alias_fs, "same_volume", lambda a, b: None)
    assert _same_volume_resolved(alias_fs, "D:/src", "D:/") is None  # 卷根不动点(Windows; POSIX 走空串分支)
    assert _same_volume_resolved(alias_fs, "D:/src", deep) is None  # 走尽层数
    assert _same_volume_resolved(alias_fs, "D:/src", "") is None


def test_relocate_module_classify_entries_per_record_error(tmp_path, monkeypatch):
    """_classify_entries: 单条记录归一化抛错 -> except-continue 跳过, 其余分类不炸(覆盖补齐)"""
    from auto_qb.infra import utils as infra_utils

    mgr, client, src, dst, content, _ = relocate_env(tmp_path, file_count=2, data_dir=False)
    hc = FakeTorrent(hash="HC", name="HC", save_path=src, progress=1.0, state="pausedUP")
    client.torrents["HC"] = hc
    client.files_map["HC"] = [_fake_file("Show/HC.mkv", 100)]
    seed_store(mgr, [hc, client.torrents["HA"], client.torrents["HB"]])
    calls = {"n": 0}
    orig = infra_utils.path_normalize

    def flaky(p):
        calls["n"] += 1
        # 第 1 次 = save_path 归一, 第 2/3 次 = _rel_under 内 content_root/save_path 归一
        # (刀2 收编 ru 单点后的调用拓扑), 第 4 次落在 HC 记录上(own 已提前跳过) ——
        # 断言语义不变: 单条记录归一化抛错 -> except-continue 跳过, 其余分类不炸
        if calls["n"] == 4:
            raise RuntimeError("boom")
        return orig(p)

    monkeypatch.setattr(infra_utils, "path_normalize", flaky)
    misc, external = mgr.host.get("relocate")._classify_entries(["HC.mkv"], src, src, ("HA", "HB"), mgr.store, client)
    assert external == [] and "HC.mkv" in misc


def test_relocate_module_precheck_defensive_paths(tmp_path):
    """纵深防御与退化入参: 未启用 / 空 hashes / 上下文缺失 / qB 未连接 各自 blocked 自解释"""
    from types import SimpleNamespace

    from auto_qb.config.models import RelocateConfig

    mgr, client, src, dst, content, _ = relocate_env(tmp_path, data_dir=False)
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

    mgr, client, src, dst, content, _ = relocate_env(tmp_path, data_dir=False)
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

    mgr, client, src, dst, content, _ = relocate_env(tmp_path, file_count=2, data_dir=False)
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
    pin_disk_usage(monkeypatch)  # 恢复 disk_usage 钉值后重挂「抛错」变体
    monkeypatch.setattr(fa_mod.LocalFileAccess, "disk_usage", lambda self, p: (_ for _ in ()).throw(OSError("no disk")))
    monkeypatch.setattr(alias_fs, "same_volume", lambda a, b: False)  # R2 #1 后同卷豁免会让 space 不拦, 桩成跨卷才能测到空间闸门
    item3 = mod.relocate_precheck(["HA", "HB"], dst)[0]
    gates3 = [r["gate"] for r in item3["reasons"]]
    # P3 判据替换: 空间不可判定照拦; 同机证据走 B′(文件 size 相等)正证放行 ——
    # free-space 代理不再参与 proved, 同机不再因「qB 默认路径读不到」被硬拦
    assert "space" in gates3 and "same_fs" not in gates3
    assert any("同机判定" in n for n in item3["notes"]), item3["notes"]


def test_relocate_module_same_fs_p3_semantics(tmp_path, monkeypatch):
    """P3 同机判据替换(计划 26-11-04-0055 §03.1, 预检层): D 级正证 wiring(qB dirPath=内容根)/
    B′ 判负硬拦 / 不可判定转 note 不拦 / assume_shared 直通 / E1 缓存凭据放行"""
    from auto_qb.core.modules.relocate_probe import probe_fingerprint
    from auto_qb.core.modules import relocate_proof as rp_mod

    # 1. D 级 wiring: 桩 app_get_directory_content 回真实 stat 的元数据 -> positive(D 级)放行
    mgr, client, src, dst, content, files = relocate_env(tmp_path, file_count=2, data_dir=False)
    mtimes = {}
    for f in files:
        st = os.stat(os.path.join(src, *f.name.split("/")))
        mtimes[f.name] = (st.st_size, int(st.st_mtime))
    captured = []

    def _dir_content(directory_path=None, with_metadata=None, **kw):
        captured.append((directory_path, with_metadata))
        return [
            {
                # qB 列目录回**条目名**(列的是内容根, 不含目录段; 全相对路径名会让 src 侧
                # D 比对判负, 弱证据优先序修正后不再被 dst visibility positive 掩盖)
                "name": name.rsplit("/", 1)[-1],
                "size": sz,
                "last_modification_date": mt,
                "type": "File"
            } for name, (sz, mt) in mtimes.items()
        ]

    client.app_get_directory_content = _dir_content
    item = mgr.host.get("relocate").relocate_precheck(["HA", "HB"], dst)[0]
    assert item["cls"] == "ok", (item["cls"], item["reasons"])
    assert captured and captured[0][1] == "true"  # withMetadata 钉死字符串 "true"
    assert captured[0][0].replace("\\", "/").endswith("Show")  # 列的是内容根, 不是下载根上层
    assert any("D 级" in n for n in item["notes"]), item["notes"]

    # 2. D 级判负: qB 列目录元数据(size)与本机文件全不等 -> blocked(same_fs, 两条出路)
    # !R1#35 弱证据收窄: B′ 级判负(种子元数据 size)不再作确定性结论(降 note 交执行链
    # 强探测定夺, 见 test_group_facts_weak_positive_degrades_to_note); 硬拦守阵换 **D 级**
    # 判负承载(桩列目录端点回错配 size)。dst 侧 visibility positive(stub 对 dst 同样
    # 回条目)不得掩盖 src D 级判负 —— 判定序 D 级在先的守阵就在本段。
    mgr2, client2, src2, dst2, content2, files2 = relocate_env(tmp_path / "b", file_count=2, data_dir=False)
    mtimes2 = {f.name: (999, 1234567890) for f in files2}  # size 错配(本机真实 64)

    def _dir_content_mismatch(directory_path=None, with_metadata=None, **kw):
        return [
            {
                "name": name.rsplit("/", 1)[-1],
                "size": sz,
                "last_modification_date": mt,
                "type": "File"
            } for name, (sz, mt) in mtimes2.items()
        ]

    client2.app_get_directory_content = _dir_content_mismatch
    item2 = mgr2.host.get("relocate").relocate_precheck(["HA", "HB"], dst2)[0]
    assert item2["cls"] == "blocked" and "same_fs" in [r["gate"] for r in item2["reasons"]]
    # 回执 truth 结构(gate/cls/text 同形): gate id 断言用 "same_fs" 不用全文
    r2 = next(r for r in item2["reasons"] if r["gate"] == "same_fs")
    assert r2["cls"] == "blocked" and set(r2) >= {"gate", "cls", "text"}, item2["reasons"]
    text2 = r2["text"]
    assert "fs.path_map" in text2 and "assume_shared" in text2
    assert "判负详情" in " ".join(item2["notes"]), item2["notes"]  # note 带出 D 级判负详情

    # 3. 不可判定(D 端点不可用 + B′ 读不到)-> 多成员不再硬拦, note 转执行链强探测
    # !0808 S1 源侧三态起(E2.2): 「声明文件不在盘」会以 source_missing 抢拦 —— 本场景的
    # ghost 落盘成真文件(size 与声明一致, 三态判「在」), B′ 不可判定面由判定层桩承载
    # (见 _stub_bprime_unavailable: 不用 os.stat 桩, 它会把三态一起打死)。
    mgr3, client3, src3, dst3, content3, _ = relocate_env(tmp_path / "c", file_count=2, data_dir=False)
    ghost = [_fake_file("Show/ghost.mkv", 100)]
    client3.files_map["HA"] = list(ghost)
    client3.files_map["HB"] = list(ghost)
    for t in (mgr3.store.by_hash["HA"], mgr3.store.by_hash["HB"]):
        t._files = None
    with open(os.path.join(src3, "Show", "ghost.mkv"), "wb") as f:
        f.write(b"x" * 100)
    _stub_bprime_unavailable(monkeypatch)
    item3 = mgr3.host.get("relocate").relocate_precheck(["HA", "HB"], dst3)[0]
    assert item3["cls"] == "ok" and "same_fs" not in [r["gate"] for r in item3["reasons"]]
    assert any("一次性强探测" in n for n in item3["notes"]), item3["notes"]

    # 4. E1 缓存 passed: 两侧证据不可判定时凭机器级强证明放行(note 注明)
    # 预播种带盐: ensure 先生成并持久化盐, plan 只读面读同盐 => 覆盖「带盐预检读」形态
    mod3 = mgr3.host.get("relocate")
    mod3.probe_put(probe_fingerprint(mgr3.config.qbittorrent, mod3.probe_salt_ensure()), "passed", {"method": "e1"})
    item4 = mod3.relocate_precheck(["HA", "HB"], dst3)[0]
    assert item4["cls"] == "ok" and any("机器级强证明" in n for n in item4["notes"]), item4["notes"]

    # 5. assume_shared 直通: 全部证据不可得也放行, note 注明用户承担
    mgr3.config.relocate.assume_shared = True
    item5 = mod3.relocate_precheck(["HA", "HB"], dst3)[0]
    assert item5["cls"] == "ok" and any("未经 auto-qb 验证" in n and "由用户承担" in n for n in item5["notes"]), item5["notes"]


def test_relocate_module_precheck_scandir_and_lstat_degraded(tmp_path, monkeypatch):
    """内容根 listing 失败 -> 不专属(目录别名不可用); 代表文件不可读 -> 识别降级 note"""
    mgr, client, src, dst, content, _ = relocate_env(tmp_path, file_count=2, data_dir=False)
    # 文件表与磁盘不一致: 记录里的文件(ghost)不在盘上 -> scandir 只见别组/杂项 + lstat 失败
    # !0808 S1 源侧三态起(E2.2): 「声明文件不在盘」会以 source_missing 抢拦 —— ghost 落盘
    # 成真文件(size 与声明一致, 三态判「在」), 代表文件不可读面由 lstat 桩承载(仅源路径炸),
    # B′ 不可判定面由判定层桩承载(见 _stub_bprime_unavailable: 不用 os.stat 桩, 它会连带把
    # 三态判成「缺失」抢拦)。
    ghost = [_fake_file("Show/ghost.mkv", 100)]
    client.files_map["HA"] = list(ghost)
    client.files_map["HB"] = list(ghost)
    for t in (mgr.store.by_hash["HA"], mgr.store.by_hash["HB"]):
        t._files = None  # 失效惰性缓存, 重拉
    with open(os.path.join(content, "ghost.mkv"), "wb") as f:
        f.write(b"x" * 100)
    _real_lstat = os.lstat
    # 路径可能带 Windows 长路径前缀(\?\)(_prefixed), 桩用包含而非前缀匹配
    monkeypatch.setattr(
        os, "lstat", lambda p, *a, **kw: (_ for _ in ()).throw(OSError("lstat 桩"))
        if str(src) in str(p) else _real_lstat(p, *a, **kw)
    )
    _stub_bprime_unavailable(monkeypatch)
    item = mgr.host.get("relocate").relocate_precheck(["HA", "HB"], dst)[0]
    # P3 同机闸门重排: 未证明(此处 B′ 也不可判定)不再硬拦多成员组
    assert item["cls"] == "ok" and item["form"] == "file_links"  # 不专属 -> 逐文件
    assert "same_fs" not in [r["gate"] for r in item["reasons"]]
    assert any("一次性强探测" in n for n in item["notes"])
    notes = " ".join(item["notes"])
    assert "杂项" in notes and "不可读" in notes


def test_relocate_module_precheck_classify_entries(tmp_path, monkeypatch):
    """内容根多出条目分类: 同 save_path 其它种子的文件 -> 组外占用; 散落 .torrent -> 杂项"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, _ = relocate_env(tmp_path, file_count=2, data_dir=False)
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
    mgr, client, src, dst, content, _ = relocate_env(tmp_path, data_dir=False)
    view = mgr.host.get("relocate").capability_view()
    for key in ("junction", "dir_symlink", "file_symlink", "hardlink", "uac_available", "container", "enabled"):
        assert key in view, key
    assert view["enabled"] is True


def test_relocate_module_precheck_add_disk_usage_degraded(tmp_path, monkeypatch):
    """添加预检: 命中作用域但目标卷剩余读不到 -> volume_free=None(展示「不可判定」不猜)"""
    from auto_qb.infra import file_access as fa_mod

    mgr, client, src, dst, content, _ = relocate_env(tmp_path, data_dir=False)
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

    mgr, client, src, dst, content, _ = relocate_env(tmp_path, file_count=2, data_dir=False)
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
    pin_disk_usage(monkeypatch)

    # 目标存在性「抛错」(而非 UNDETERMINED) -> 同样按不可判定拒绝
    def _raise_exists(self, p):
        raise RuntimeError("fs io")

    monkeypatch.setattr(fa_mod.LocalFileAccess, "exists", _raise_exists)
    item3 = mod.relocate_precheck(["HA", "HB"], dst)[0]
    assert "target_unknown" in [r["gate"] for r in item3["reasons"]]
    monkeypatch.undo()
    pin_disk_usage(monkeypatch)
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
    pin_disk_usage(monkeypatch)
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
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, _ = relocate_env(tmp_path, file_count=2, data_dir=False)
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
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, _ = relocate_env(tmp_path, file_count=2, data_dir=False)
    shutil.rmtree(content)
    item = mgr.host.get("relocate").relocate_precheck(["HA", "HB"], dst)[0]
    assert item["form"] == "file_links" and item["cls"] in ("ok", "confirm", "blocked")


def test_relocate_module_precheck_add(tmp_path):
    """添加预检: ok / confirm(目录别名作用域 -> 实际落点+卷剩余) / confirm(收尾窗口) /
    confirm(同名链接覆盖)"""
    mgr, client, src, dst, content, _ = relocate_env(tmp_path, data_dir=False)
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
    assert r["cls"] == "confirm" and r["reasons"][0]["gate"] == "finalize_window", r
    assert _fwd(r["actual_path"]) == _fwd(os.path.join(dst, "Show")) and r["volume_free"] is not None
    # 收尾窗口(rewritten): confirm 警示删链门永久依赖(D16)
    mod.register_job(
        RelocateJob(
            job_id="j2",
            hashes=("HA", ),
            mover="HA",
            src=src,
            dst=dst,
            scope=content,
            alias_kind="dir",
            phase="rewritten"
        )
    )
    r = mod.precheck_add(src, "Late.Show")
    assert r["cls"] == "confirm" and r["reasons"][0]["gate"] == "finalize_window"
    # 同名链接覆盖(前段相位 moved): 落点是真硬链接 -> confirm alias_file
    # (前段相位不进分支 1 finalize_window; 收尾窗判据已形态感知(计划 26-11-13-0448 R1-R3):
    #  添加预检目录级双面真值/文件级落点名判定, 删种拦截 R3 文件级按「文件清单 x alias_paths
    #  交集」精判、目录级全量拦保留)
    mod._jobs.clear()
    mod.register_job(
        RelocateJob(
            job_id="j3", hashes=("HA", ), mover="HA", src=src, dst=dst, scope=content, alias_kind="file", phase="moved"
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


def test_web_relocate_cancel_route(web_env):
    """撤销路由: 403(关, 零入队, detail 注键名) / 400(空 job_id) / 门开后入队 cmd 与载荷形状"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    # 关(缺省 enabled=False): 403 零入队
    resp = client.post("/api/relocate/cancel", headers=auth, json={"job_id": "j1"})
    assert resp.status_code == 403, resp.text
    assert "relocate.enabled" in resp.json()["detail"]
    assert mgr.web.commands.empty()
    # 开: 入队形状(confirm 提供才透传)
    mgr.config.relocate.enabled = True
    resp = client.post("/api/relocate/cancel", headers=auth, json={"job_id": "j1"})
    assert resp.status_code == 200 and resp.json()["queued"] is True, resp.text
    cmd, payload = mgr.web.commands.get_nowait()
    assert cmd == "relocate_cancel", (cmd, payload)
    payload.pop("cmd_id")
    payload.pop("_queued_ts", None)
    assert payload == {"job_id": "j1", "confirm": False}, payload
    resp = client.post("/api/relocate/cancel", headers=auth, json={"job_id": "j1", "confirm": True})
    assert resp.status_code == 200
    cmd, payload = mgr.web.commands.get_nowait()
    payload.pop("cmd_id")
    payload.pop("_queued_ts", None)
    assert payload == {"job_id": "j1", "confirm": True}, payload
    # 400: job_id 空在路由层拒收, 不入队
    for body in ({}, {"job_id": ""}, {"confirm": True}):
        resp = client.post("/api/relocate/cancel", headers=auth, json=body)
        assert resp.status_code == 400, (body, resp.text)
    assert mgr.web.commands.empty()


def test_web_relocate_cancel_drain(tmp_path, monkeypatch):
    """drain 级撤销两步走(D6 停手语义): 未确认(cls=confirm + 三段式 guide, 数据零变动);
    确认(cls=ok, 删自己的链接 + phase=cancelled + journal 落盘, 零 setLocation 不搬回)

    旧 R1#24 的 MOVING 期硬拒撤随搬回能力退役: 半途撤销(cmd 通道直发)照常停手 ——
    先在 moving 期撤一条(零 setLocation), 再起一条走到 armed 走两步确认。
    """
    from relocate_exec_support import _run_ticks, _simulate_moved, _spy_spawn, _stub_probe_pass

    pin_disk_usage(monkeypatch)
    _stub_probe_pass(monkeypatch)  # R1#35 后多成员组执行链必走 run_probe(本用例只关心撤销链)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, file_count=2, data_dir=False)
    mgr.config.data_dir = str(tmp_path / "data")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    # 半途撤销: moving 期(cmd 通道直发)照常停手 —— 零 setLocation(不叠加任何搬迁指令)
    job_moving = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    assert mod.get_job(job_moving).phase == "moving" and client.calls  # 已下发搬迁(执行链正常下发)
    client.calls.clear()
    mgr.web.commands.put(("relocate_cancel", {"job_id": job_moving, "confirm": True, "cmd_id": "rc0"}))
    mgr.web.consume_commands()
    truth0 = mgr.web.results["rc0"]["truth"]
    assert truth0["cls"] == "ok" and mod.get_job(job_moving).phase == "cancelled", truth0
    assert not any(c[0] == "set_location" for c in client.calls), f"半途撤销零 setLocation: {client.calls}"
    # armed 现场走两步确认
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    _simulate_moved(mgr, dst, files, content)
    _run_ticks(mod, 6)
    assert mod.get_job(job_id).phase == "armed", mod.get_job(job_id).phase
    # 第一步: 不确认 => 只回三段式确认面(D7 guide), 零 qB 写(撤销前清空并断言无新调用)
    client.calls.clear()
    mgr.web.commands.put(("relocate_cancel", {"job_id": job_id, "cmd_id": "rc1"}))
    mgr.web.consume_commands()
    rec = mgr.web.results["rc1"]
    assert rec["status"] == "ok", rec
    truth = rec["truth"]
    assert truth["cls"] == "confirm" and "guide" in truth, truth
    guide = truth["guide"]
    assert "不会搬回" in guide["consequence"], guide  # 其一 后果
    assert "缺件" in guide["halfway"] and "补下" in guide["halfway"], guide  # 其二 半途警示
    assert "当前位置" in guide["halfway"] and "源位置" in guide["halfway"], \
        f"补下位置不锚定新位置(按成员当前位置自行补下): {guide['halfway']}"
    assert len(guide["manual"]) == 4, guide  # 其三 手动处置推荐
    assert "重新校验" in guide["manual"][1], guide  # 缺件处理条(强制重新校验出口)
    assert "当前位置" in guide["manual"][0] and "重新发起" in guide["manual"][3], guide
    assert client.calls == [], f"未确认时不得有任何 qB 写调用: {client.calls}"
    # 第二步: 确认 => 删自己的链接 + cancelled + journal 落盘(零 setLocation)
    mgr.web.commands.put(("relocate_cancel", {"job_id": job_id, "confirm": True, "cmd_id": "rc2"}))
    mgr.web.consume_commands()
    rec = mgr.web.results["rc2"]
    assert rec["status"] == "ok" and rec["truth"]["cls"] == "ok", rec
    assert mod.get_job(job_id).phase == "cancelled"
    assert not any(c[0] == "set_location" for c in client.calls), f"撤销零 setLocation(D6): {client.calls}"
    journal = os.path.join(str(tmp_path / "data"), "relocate", f"{job_id}.json")
    assert os.path.exists(journal), "撤销后 journal 必须落 cancelled 相位(guardian 退休信号)"


def test_web_relocate_precheck_drain(tmp_path, monkeypatch):
    """drain 级: 回执 truth={results, summary} 结构 + gone verdict + 混合计数;
    precheck_add 回执 truth=单 item"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, _ = relocate_env(tmp_path, file_count=2, data_dir=False)
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

    shared = Path(__file__).resolve().parents[2] / "src" / "auto_qb" / "webui" / "static" / "shared"
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


def _drawer_body(src: str, start: str, end: str) -> str:
    """取 drawer.js 中某方法体(从 start 到其后的 end 标记); 标记缺失即本守阵失败"""
    i = src.index(start)
    return src[i:src.index(end, i)]


def test_relocate_confirm_loop_wired_in_move_dialog():
    """confirm 回路前端静态守阵(issue 26-11-04-0734)

    后端 confirm 仍回 status=ok(只在 truth.summary.confirm 计数), 前端必须在 r.ok 之上消费 summary:
    命中时不得先弹「已执行」, 由设定位置提交点收框 -> 二次确认框 -> 带 confirm=true 重发。
    confirm=0 仍走原成功路径(成功 toast + 关框)。
    整组语义披露两披露点(计划 26-11-07-1300 R6, 拍板 D5/D8): R6a = move-dialog.html 常驻提示
    (relocate_enabled 旗标门控, shared 单点 + flags 通路 fail-closed); R6b = 确认框「来源」行
    接 member_count(>1 才后缀披露, 旧回执/单成员形状不变, 不新增行不改触发条件)。
    """
    from pathlib import Path

    shared = Path(__file__).resolve().parents[2] / "src" / "auto_qb" / "webui" / "static" / "shared"
    drawer = (shared / "drawer.js").read_text(encoding="utf-8")
    # 两条投递路径(单种子 / 批量)都要识别 confirm, 且确认分支先于成功 toast
    edit = _drawer_body(drawer, "async _editPost(", "/* 速度限制")
    assert 'action === "location"' in edit and "this._relocateConfirmCount(r) > 0" in edit
    assert 'return "confirm"' in edit, "confirm 命中必须交回调用方, 不能当成功"
    assert edit.index('return "confirm"') < edit.index("this._relocateDoneText(r, okText)"), \
        "confirm 命中不得先弹「已执行」"
    bulk = _drawer_body(drawer, "async _bulkEditPost(", "/* 重命名")
    assert 'action === "location"' in bulk and "this._relocateConfirmCount(r) > 0" in bulk
    assert 'return "confirm"' in bulk
    assert bulk.index('return "confirm"') < bulk.index("this._relocateDoneText(r,")
    # 回执读取单点: truth.summary.confirm
    count = _drawer_body(drawer, "_relocateConfirmCount(r) {", "/* 确认框行表")
    assert "truth.summary.confirm" in count
    # 确认框信息面: 形态/来源/目标/未来种子(目录别名语义)/原因
    rows = _drawer_body(drawer, "_relocateConfirmRows(r) {", "/* 二次确认框")
    for token in ("未来种子", "目录别名", "save_path", "target", "reasons"):
        assert token in rows, f"确认框缺 {token} 信息面"
    # 整组语义披露(计划 26-11-07-1300 R6b, D8): 来源行 value 接 member_count(>1 才后缀披露);
    # 只扩 value 不改名, 不新增行, 触发条件在 _relocateConfirmGate(不在本行表)
    assert "member_count" in rows and "(整组 ${members} 个成员)" in rows, \
        "确认框来源行缺整组成员数披露(R6b)"
    assert "members > 1" in rows, "披露阈值 >1 必须钉死(单成员/缺字段不得披露)"
    assert 'label: p + "来源"' in rows, "来源行标签不得改名(R6b 只扩 value)"
    gate = _drawer_body(drawer, "async _relocateConfirmGate(r) {", "/* 成功 toast")
    assert "this._openModal({" in gate and "verdict:" in gate and "确认迁移" in gate
    assert "目录别名" in gate, "确认框正文必须讲清目录别名会影响未来落点"
    # 提交点: 先收设定位置框(两层遮罩同 z-index) -> 确认框 -> 带 confirm=true 重发
    sub = _drawer_body(drawer, "async submitMoveDialog() {", "/* ---------------- 批量编辑")
    assert "await this._relocateConfirmGate(receipt)" in sub
    assert "this.moveOpen = false" in sub
    assert sub.index("this.moveOpen = false") < sub.index("await this._relocateConfirmGate(receipt)")
    assert "confirm: true" in sub and "await post(true)" in sub
    assert sub.index("await post(true)") > sub.index("await this._relocateConfirmGate(receipt)")
    # 取消/失败回到设定位置框; confirm=0 仍走原成功关框路径
    assert "reopen()" in sub
    assert "if (ok) this.moveOpen = false;" in sub
    done = _drawer_body(drawer, "_relocateDoneText(r, okText) {", "/* 编辑类命令统一投递")
    assert "if (!s) return `已执行: ${okText}`;" in done, "无 summary 的动作文案与历史一致"
    # R6a(计划 26-11-07-1300, D5): 设定位置对话框常驻提示在 shared 单点模板(五主题共用, 不碰
    # 各主题 index.html), relocate_enabled 旗标门控 —— 开 = 提交前披露整组语义(零额外点击),
    # 关 = 不渲染(普通移动语义不变)
    tpl = (shared / "tpl" / "move-dialog.html").read_text(encoding="utf-8")
    assert 'v-if="flags.relocate_enabled"' in tpl, "move-dialog 缺整组提示旗标门(R6a)"
    assert "整组迁移已启用: 移动将以内容组为单位, 同组其它成员一并迁移" in tpl, "R6a 常驻提示文案缺失"
    # flags 通路(relocate.enabled -> flags.relocate_enabled): 显式建 fail-closed 默认 + loadWebFlags 写回
    state_js = (shared / "state.js").read_text(encoding="utf-8")
    lifecycle_js = (shared / "lifecycle.js").read_text(encoding="utf-8")
    assert "relocate_enabled: false" in state_js and "relocate_enabled: false" in lifecycle_js, \
        "flags 默认/失败分支缺 relocate_enabled: false(fail-closed 初值必须显式建)"
    assert "relocate_enabled: !!(f && f.relocate_enabled)" in lifecycle_js, \
        "loadWebFlags 必须写回 relocate_enabled(缺了旗标恒 false = 提示永不出现)"


def test_web_relocate_confirm_passthrough_routes(web_env):
    """confirm 透传契约: 缺省/False 不入载荷(历史形状不变), confirm=true 才附加

    单种子 /api/torrents/{hash}/location 与批量 /api/torrents/bulk(action=location) 两个出口;
    前端 confirm 回路靠这条通道把用户的显式确认带回后端。"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}

    def _queued():
        cmd, payload = mgr.web.commands.get_nowait()
        payload.pop("cmd_id", None)
        payload.pop("_queued_ts", None)
        return cmd, payload

    for confirm in (None, False, True):
        body = {"location": "R:/X"}
        if confirm is not None:
            body["confirm"] = confirm
        resp = client.post("/api/torrents/HA/location", headers=auth, json=body)
        assert resp.status_code == 200, resp.text
        cmd, payload = _queued()
        assert cmd == "set_torrent_location"
        want = {"hash": "HA", "location": "R:/X"}
        if confirm:
            want["confirm"] = True
        assert payload == want, (body, payload)

    for confirm in (None, False, True):
        body = {"hashes": ["HA"], "action": "location", "location": "R:/X"}
        if confirm is not None:
            body["confirm"] = confirm
        resp = client.post("/api/torrents/bulk", headers=auth, json=body)
        assert resp.status_code == 200, resp.text
        cmd, payload = _queued()
        assert cmd == "bulk_torrents"
        want = {"hashes": ["HA"], "action": "location", "delete_files": False, "location": "R:/X"}
        if confirm:
            want["confirm"] = True
        assert payload == want, (payload)


def _probing_item(hashes=("HA", )):
    """「探测中」gate 回执(S2 异步化形态, T4 受理段的输入面): cls=blocked + 机器判别键"""
    return {
        "hashes": list(hashes),
        "mover": hashes[0],
        "name": "Show",
        "save_path": "R:/src",
        "target": "R:/dst",
        "cls": "blocked",
        "probing": True,
        "reasons": [{
            "gate": "same_fs",
            "cls": "blocked",
            "text": "同机探测已入队(探测进行中或等位)"
        }],
        "notes": ["同机探测已入队: 同机强探测进行中, 迁移将在探测结论到达后自动续跑"],
    }


def test_relocate_receipt_probing_acceptance_not_error(tmp_path, monkeypatch):
    """T4 受理段(D8): 仅探测中回 warn「已受理」非 blocked 错误; probing 桶独立计数; 混合/缺失形态

    用宿主命令 mixin 的 _relocate_receipt(与生产 handler 同一份实现)直驱: 探测中 item(cls
    仍是 blocked)按机器判别键单独成桶, 不再进 blocked 桶 —— 仅探测中(可混真实拒绝)出 warn
    受理形态; 探测中+已发起混合走既有 ok; 缺失计数文案追加探测中段(26-11-07-0536 契约不变)。
    """
    pin_disk_usage(monkeypatch)
    mgr, _client, _src, _dst, _content, _files = relocate_env(tmp_path, file_count=2, data_dir=False)
    started = {"cls": "started", "job_id": "j1", "hashes": ["HA"], "form": "file_links", "reasons": []}
    blocked = {
        "cls": "blocked",
        "hashes": ["HB"],
        "reasons": [{
            "gate": "target_conflict",
            "cls": "blocked",
            "text": "目标已存在"
        }]
    }
    # 仅探测中: warn 受理, 不再当 blocked 错误呈现
    mgr._relocate_receipt("c-accept", [_probing_item()], "测试受理")
    rec = mgr.web.results["c-accept"]
    assert rec["status"] == "warn", rec
    assert "已受理" in rec["error"] and "同机探测进行中 1 项" in rec["error"], rec["error"]
    assert rec["truth"]["summary"] == {"started": 0, "skip": 0, "confirm": 0, "blocked": 0, "probing": 1}, rec["truth"]
    # 探测中 + 真实闸门拒绝: 仍 warn 受理(受理是主事实), 文案带拒绝计数, 明细在 truth
    mgr._relocate_receipt("c-accept-mixed", [_probing_item(), blocked], "测试受理混合")
    rec2 = mgr.web.results["c-accept-mixed"]
    assert rec2["status"] == "warn" and "另有 1 项被闸门拒绝" in rec2["error"], rec2
    assert rec2["truth"]["summary"]["blocked"] == 1 and rec2["truth"]["summary"]["probing"] == 1
    # 探测中 + 已发起混合: 走既有 ok(部分成功不报错), probing 桶照常计数
    mgr._relocate_receipt("c-accept-started", [_probing_item(), started], "测试受理已发起")
    rec3 = mgr.web.results["c-accept-started"]
    assert rec3["status"] == "ok" and rec3["truth"]["summary"]["started"] == 1 and rec3["truth"]["summary"]["probing"
                                                                                                           ] == 1
    # 纯真实拒绝(无探测中): blocked error 形态不变(D8 只改探测中呈现)
    mgr._relocate_receipt("c-blocked", [blocked], "测试拒绝")
    assert mgr.web.results["c-blocked"]["status"] == "error"
    assert mgr.web.results["c-blocked"]["error"] == "目标已存在"
    # 缺失计数契约(批量): error 文案追加「同机探测进行中」段
    mgr._relocate_receipt("c-missing", [_probing_item()], "测试缺失", missing_msgs=["1 个 hash 不在快照"])
    rec5 = mgr.web.results["c-missing"]
    assert rec5["status"] == "error" and "另有 1 项同机探测进行中" in rec5["error"], rec5["error"]


class _StubRelocateExecute:
    """relocate 模块替身(仅 relocate_execute 面): 记录 kwargs 并回给定 items"""
    def __init__(self, items):
        self.items = items
        self.calls = []

    def relocate_execute(self, hashes, location="", confirm=False, origin="unknown", receipt_cmd_id=""):
        self.calls.append(
            {
                "hashes": list(hashes),
                "location": location,
                "confirm": confirm,
                "origin": origin,
                "receipt_cmd_id": receipt_cmd_id
            }
        )
        return [dict(it) for it in self.items]


def test_web_relocate_probe_receipt_cmd_id_wired(tmp_path, monkeypatch):
    """受理段绑定接线(T4): 单种/批量两个调用点把 cmd_id 传给 relocate_execute(receipt_cmd_id)

    探测中 items 经命令全链(consume_commands -> handler -> _relocate_receipt)出 warn 受理
    回执; 绑定语义本身(receipt_cmd_id -> pending 条目 receipt_ids -> 出站面)由
    test_relocate_probe_async / test_relocate_probe_consume 的容器与消费面用例钉死。
    """
    pin_disk_usage(monkeypatch)
    mgr, _client, _src, _dst, _content, _files = relocate_env(tmp_path, file_count=2, data_dir=False)
    stub = _StubRelocateExecute([_probing_item()])
    mgr.ctx.relocate = stub
    mgr.web.commands.put(("set_torrent_location", {"hash": "HA", "location": "R:/dst", "cmd_id": "c-s1"}))
    mgr.web.commands.put(
        ("bulk_torrents", {
            "hashes": ["HB"],
            "action": "location",
            "location": "R:/dst",
            "cmd_id": "c-b1"
        })
    )
    mgr.web.consume_commands()
    assert [c["receipt_cmd_id"] for c in stub.calls] == ["c-s1", "c-b1"], \
        f"两个调用点都把 cmd_id 传给 relocate_execute: {stub.calls}"
    assert all(c["origin"] == "web" for c in stub.calls)
    for cid in ("c-s1", "c-b1"):
        rec = mgr.web.results[cid]
        assert rec["status"] == "warn" and "已受理" in rec["error"], rec


def test_web_relocate_probe_two_phase_full_chain(tmp_path, monkeypatch):
    """两段回执全链(D8): 受理(warn + cmd_id 绑 pending) -> verdict 消费重放建账 -> 出站面 ->
    WebUIModule.on_command_line 排空补发(同 cmd_id 二次写覆盖 warn 为 ok + notify 两次 cmd 事件)"""
    pin_disk_usage(monkeypatch)
    _stub_bprime_unavailable(monkeypatch)
    mgr, _client, _src, dst, _content, _files = relocate_env(tmp_path, file_count=2)
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    q, _slot = _wire_async(mod, _recording_probe([]))
    sub = queue.Queue()
    mgr.web._subscribers.append(sub)  # 捕获 notify 事件(真实通路)
    # 受理段: web 命令 -> relocate_execute 探测闸未命中(异步) -> 探测中回执 -> warn 受理
    mgr.web.commands.put(("set_torrent_location", {"hash": "HA", "location": dst, "cmd_id": "c-full"}))
    mgr.web.consume_commands()
    rec = mgr.web.results["c-full"]
    assert rec["status"] == "warn" and "已受理" in rec["error"], rec
    entries = mod.probe_pending_list()
    assert len(entries) == 1 and entries[0]["receipt_ids"] == ["c-full"], "cmd_id 已绑进 pending 条目"
    # 终态: verdict 到达 -> on_task_line 消费(probe_put + 重放建账 + 出站面投递)
    assert wait_until(lambda: q.qsize() == 1), "探测替身 verdict 到达"
    mod.on_task_line()
    jobs = mod.active_jobs()
    assert len(jobs) == 1 and jobs[0].phase == PHASE_MOVING, "重放命中 passed 缓存续跑建账"
    assert mgr.web.results["c-full"]["status"] == "warn", "补发前回执仍是受理态"
    # 补发段: 生产挂点 = WebUIModule.on_command_line(排空出站面 -> 同 cmd_id 二次写)
    mgr.host.get("webui").on_command_line()
    rec2 = mgr.web.results["c-full"]
    assert rec2["status"] == "ok" and rec2["truth"]["summary"]["started"] == 1, f"终态覆盖受理态: {rec2}"
    evs = []
    while not sub.empty():
        evs.append(sub.get_nowait())
    cmd_evs = [e for e in evs if e["type"] == "cmd" and e["payload"].get("cmd_id") == "c-full"]
    assert len(cmd_evs) >= 2, f"受理段与终态各推一次 cmd 事件(set_result notify): {len(cmd_evs)}"
    assert mod.probe_receipts_take() == [], "出站面已排空(不重复补发)"


def test_web_relocate_probe_terminal_drain_error_and_defense(tmp_path, monkeypatch):
    """补发段 error 形态与防御面: error 回执(items 空不冒充终态) / 无 cmd_id 跳过 / relocate 缺位零动作"""
    pin_disk_usage(monkeypatch)
    mgr, _client, _src, _dst, _content, _files = relocate_env(tmp_path, file_count=2, data_dir=False)
    mod = mgr.host.get("relocate")
    # relocate 缺位替身(ctx.relocate 无 probe_receipts_take): 零动作不炸
    mgr.ctx.relocate = _StubRelocateExecute([])
    mgr.web.drain_probe_receipts()
    mgr.ctx.relocate = None
    mgr.web.drain_probe_receipts()
    assert mgr.web.results == {}, "缺位/无取走面: 零动作"
    mgr.ctx.relocate = mod
    # error 终态(防自环终止/重放异常形态): items 空, error 文案直达
    mod._probe_receipt_publish(["c-err"], [], "同机探测失败(add_rejected): 自动续跑已终止(环境性失败未缓存)")
    mgr.web.drain_probe_receipts()
    rec = mgr.web.results["c-err"]
    assert rec["status"] == "error" and "add_rejected" in rec["error"], rec
    assert "truth" not in rec, "error 形态无 items 不带 truth(不冒充明细)"
    # 无 cmd_id 条目跳过(不可达形态, 防御面); 正常条目照常
    mod._probe_receipt_publish([""], [], "ghost")  # 空 id 零投递(relocate 侧已拦, 双保险)
    mod._probe_receipt_outbox.append({"cmd_id": "", "items": [], "error": "orphan"})  # 直塞坏条目
    mod._probe_receipt_publish(["c-ok2"], [{"cls": "skip", "hashes": ["HA"], "reasons": [], "notes": []}], "")
    mgr.web.drain_probe_receipts()
    assert "orphan" not in str(mgr.web.results.get("", "")), "无 cmd_id 条目跳过"
    rec2 = mgr.web.results["c-ok2"]
    assert rec2["status"] == "ok" and rec2["truth"]["summary"]["skip"] == 1, "正常条目照常出回执"
    assert mod.probe_receipts_take() == [], "排空式语义(防重复补发)"


def test_web_relocate_probe_split_group_terminal_maps_ok(tmp_path, monkeypatch):
    """拆组形态(R5 评审修复 #1): passed verdict 但重放拆组出混合 items -> 终态投 items 非 error

    重放经 relocate_execute 按当前 save_path 重新分组: 探测窗口内组员 save_path 变了就拆组,
    重放 items 可能是「本组缓存命中 started + 拆出组闸未命中 probing gate」混合 —— 消费面
    防自环 error 判别的真值来源 = verdict 本体(failed env=True), 不是 any-probing, 否则
    passed verdict 会被折成「同机探测失败」。混合 items 交宿主 _relocate_receipt 重计:
    started+probing 出 ok; 拆出条目无 receipt_ids 后续不再补发(该 probing 组的进展由
    job 视图承载)。防自环语义不变: env=True 失败时重放必回 probing 回执(test_consume_
    env_failure_publishes_error_terminal 钉住)。重放透传条目 receipt_ids 首个(评审终审
    接缝修复: 指纹漂移重入队时绑定延续; 本用例重放未重入队, 透传对拆组映射无副作用,
    test_consume_fingerprint_drift_reenq_binds_receipt_cmd_id 钉住重入队形态)。
    """
    pin_disk_usage(monkeypatch)
    mgr, _client, src, dst, _content, _files = relocate_env(tmp_path, file_count=2)
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    from auto_qb.core.modules.relocate_probe import probe_fingerprint

    q, slot = _wire_async(mod, _recording_probe([]))
    fp = probe_fingerprint(mgr.config.qbittorrent, mod.probe_salt_ensure())
    mod.probe_pending_append(fp, ["HA", "HB"], src, dst, "web", receipt_id="c-split")
    slot.try_acquire(fp)
    q.put((fp, _passed()))

    started = {"cls": "started", "job_id": "j-own", "hashes": ["HA"], "reasons": []}
    split_probing = _probing_item(("HB", ))
    replay_calls = []

    def _split_replay(hashes, location="", confirm=False, origin="unknown", receipt_cmd_id=""):
        # 重放面桩: 探测窗口内组员 save_path 变了 -> 按新 save_path 拆组
        replay_calls.append({"hashes": list(hashes), "receipt_cmd_id": receipt_cmd_id})
        return [dict(started), dict(split_probing)]

    monkeypatch.setattr(mod, "relocate_execute", _split_replay)
    mod.on_task_line()  # 消费: probe_put(passed) + 重放(拆组桩) + 出站面投递
    assert replay_calls == [{"hashes": ["HA", "HB"], "receipt_cmd_id": "c-split"}], \
        "重放透传条目 receipt_ids 首个(评审终审接缝修复: 指纹漂移重入队时绑定延续)"
    out = list(mod._probe_receipt_outbox)  # 非排空窥视(排空归 webui 命令线)
    assert len(out) == 1 and out[0]["cmd_id"] == "c-split", "拆组形态照常投终态(不折成 error)"
    assert out[0]["error"] == "" and [it["cls"] for it in out[0]["items"]] == ["started", "blocked"], \
        "items 原样带出(started + probing gate), 交宿主按明细重计"
    assert mod.probe_pending_list() == () and slot.in_flight() is None, "条目清 + 槽释放照常"
    # drain 映射: started+probing -> ok 受理(不是 error「同机探测失败」)
    mgr.host.get("webui").on_command_line()
    rec = mgr.web.results["c-split"]
    assert rec["status"] == "ok", rec
    assert rec["truth"]["summary"] == {"started": 1, "skip": 0, "confirm": 0, "blocked": 0, "probing": 1}, rec["truth"]
    assert "同机探测失败" not in rec["error"], "passed verdict 不得被折成探测失败文案"


def test_web_relocate_probe_terminal_last_write_wins(tmp_path, monkeypatch):
    """同一 cmd_id 绑多条 pending 条目 -> 逐条各投终态 -> 一次 drain 二次写同 id 收敛

    批量跨两组受理(cmd_id 绑两条意图)时, 每条意图的 verdict 各投一条终态(同 cmd_id),
    webui 一次 drain 顺序二次写 —— set_result 覆盖语义收口为 last-write-wins(后投条目
    明细), cmd 事件计数 = 受理 1 + 终态 2。
    """
    pin_disk_usage(monkeypatch)
    mgr, _client, src, _dst, _content, _files = relocate_env(tmp_path, file_count=2)
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    from auto_qb.core.modules.relocate_probe import probe_fingerprint

    q, slot = _wire_async(mod, _recording_probe([]))
    fp = probe_fingerprint(mgr.config.qbittorrent, mod.probe_salt_ensure())
    # 一条 web 命令(批量)跨两组受理: 同 cmd_id 绑两条意图(同指纹异目标, 追加等位)
    mod.probe_pending_append(fp, ["HA"], src, "R:/dst-a", "web", receipt_id="c-multi")
    mod.probe_pending_append(fp, ["HB"], src, "R:/dst-b", "web", receipt_id="c-multi")
    # 受理段: 仅探测中 -> warn「已受理」+ truth, notify 推第 1 次 cmd 事件
    sub = queue.Queue()
    mgr.web._subscribers.append(sub)
    mgr._relocate_receipt("c-multi", [_probing_item(("HA", )), _probing_item(("HB", ))], "批量双组受理")
    assert mgr.web.results["c-multi"]["status"] == "warn"
    # 终态: 逐条 verdict -> 逐条重放(桩, 按 hash 出可区分明细)-> 逐条投递
    replayed = []

    def _replay(hashes, location="", confirm=False, origin="unknown", receipt_cmd_id=""):
        tag = "A" if "HA" in list(hashes) else "B"
        replayed.append(f"j-{tag}")
        return [{"cls": "started", "job_id": f"j-{tag}", "hashes": list(hashes), "reasons": []}]

    monkeypatch.setattr(mod, "relocate_execute", _replay)
    slot.try_acquire(fp)
    q.put((fp, _passed()))
    mod._consume_probe_verdict()  # 条目 A: 重放 -> 投 {c-multi, j-A} -> 清 -> kick B
    assert wait_until(lambda: q.qsize() == 1), "kick 下一条(B)的 verdict 到达"
    mod._consume_probe_verdict()  # 条目 B: 重放 -> 投 {c-multi, j-B} -> 清
    assert replayed == ["j-A", "j-B"], "FIFO 逐条消费"
    out = list(mod._probe_receipt_outbox)  # 非排空窥视(排空归 webui 命令线)
    assert [r["cmd_id"] for r in out] == ["c-multi", "c-multi"], "同 cmd_id 各投一条"
    assert [r["items"][0]["job_id"] for r in out] == ["j-A", "j-B"], "两条终态明细可区分"
    # 一次 drain: 二次写同 cmd_id, last-write-wins 收敛为后投条目明细
    mgr.host.get("webui").on_command_line()
    rec = mgr.web.results["c-multi"]
    assert rec["status"] == "ok" and rec["truth"]["results"][0]["job_id"] == "j-B", f"last-write-wins: {rec}"
    evs = []
    while not sub.empty():
        evs.append(sub.get_nowait())
    cmd_evs = [e for e in evs if e["type"] == "cmd" and e["payload"].get("cmd_id") == "c-multi"]
    assert len(cmd_evs) == 3, f"cmd 事件计数 = 受理 1 + 终态 2: {len(cmd_evs)}"
