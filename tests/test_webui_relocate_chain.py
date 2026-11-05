"""路径链探测与浮窗(P2, 计划 26-11-04-1042)。

## 测试计划
- test_chain_endpoint_gate_and_hash_validation: 403 门控 / 只收 hash / 路径注入 422 / 未知 hash 404;
- test_chain_endpoint_ignores_path_param: 客户端传 path 不改变服务端派生起点;
- test_chain_walk_types_targets_and_attribution: A->B->C 逐跳类型/目标/归属章(命中/非命中/陈旧);
- test_chain_cycle_and_hop_limit: 环检测与 8 跳上限;
- test_chain_cache_ttl_refresh_and_capacity: TTL / refresh=1 / LRU 容量;
- test_chain_mapped_and_remote_are_unknown_not_guessed: 映射/远程不做 syscall, 返回未确认;
- test_probe_chain_edge_states: 空起点/空根/缺失起点/目标越界/目标不可映射的兜底分支;
- test_inspect_path_error_classification: 不存在/权限不足/未知类型各自可表达;
- test_inspect_path_link_variants: UNC 前缀/空目标/父目录不可读/重解析标签与 S_ISLNK/readlink 失败;
- test_chain_start_derivation_and_env: 空记录/映射/远程 UNC/候选越界回退四种起点派生与环境判定;
- test_alias_helpers: `\\??\\` 前缀、相对链接、硬链接、挂载点识别;
- test_chain_alias_index_prefers_active_job: 同路径多 job 优先活跃 job;
- test_chain_frontend_static_and_node: 浮窗可达性/零渲染期探测/皮肤脚本与文案映射。

### S3 收尾反馈面与「立即收尾」按钮(计划 26-11-05-0808 §3.2 失败反馈面行 / §06 D14)
- test_finalize_now_route_contract: 403 门控 / 未确认只回现场说明 / 后端窗口复核 blocked /
  确认 -> app_shutdown -> ok / shutdown 被拒 -> degraded 降级(不重试) / 断连 503
- test_chain_finalize_face_in_response: 链响应 finalize 段(pending 现读/daemon_stale/
  window 相位单点; 旧链 spec 与终态 journal 恒 pending=0)
- test_finalize_button_and_hint_static: 前端静态守阵(按钮/提示挂浮窗, 确认框与降级文案,
  渲染面零调用)
"""
import json
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from auto_qb.core.modules.relocate_units import job_rank
from auto_qb.infra import alias_fs
from auto_qb.infra import file_access as fa_mod
from auto_qb.infra.utils_paths import path_normalize
from auto_qb.webui import relocate_chain
from clock import FakeClock  # noqa: E402  统一假钟单点(时间语义用例: tests/clock.py)

ROOT = Path(__file__).resolve().parents[1]
HASH = "a" * 40


def _auth(mgr) -> dict:
    return {"Authorization": f"Bearer {mgr.web.token}"}


def _static(rel: str) -> str:
    return (ROOT / "src/auto_qb/webui/static" / rel).read_text(encoding="utf-8")


def _install(web_env, root_path: str, snapshot=None):
    """把 web_env 替身接到真实临时目录: 一条种子记录 + 可选迁移快照"""
    mgr, client = web_env
    mgr.config.relocate = SimpleNamespace(enabled=True)
    # save_path 用链接所在目录作为允许根(测试都在同一个 src 下造链)
    rec = SimpleNamespace(
        save_path=str(Path(root_path).parent),
        root_path=root_path,
        content_path="",
    )
    mgr.store.by_hash = {HASH: rec}
    mgr.store.get = lambda h: rec if h == HASH else None
    if snapshot is not None:
        mgr.ctx = SimpleNamespace(relocate=SimpleNamespace(jobs_snapshot=lambda: snapshot))
    return mgr, client, rec


def _link(link: Path, target: Path) -> str:
    """造一条目录链接; Windows 优先符号链接(需权限时退回免管理员 junction)"""
    link.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        try:
            os.symlink(str(target), str(link), target_is_directory=True)
            return alias_fs.KIND_SYMLINK
        except OSError:
            alias_fs.create_dir_alias(str(link), str(target), alias_fs.KIND_JUNCTION)
            return alias_fs.KIND_JUNCTION
    os.symlink(str(target), str(link), target_is_directory=True)
    return alias_fs.KIND_SYMLINK


def test_chain_endpoint_gate_and_hash_validation(web_env, tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    mgr, client, _rec = _install(web_env, str(src))

    mgr.config.relocate.enabled = False
    assert client.get(f"/api/relocate/chain?hash={HASH}", headers=_auth(mgr)).status_code == 403
    mgr.config.relocate.enabled = True

    for bad in ("", "../etc/passwd", HASH + "/../../", "xyz"):
        resp = client.get("/api/relocate/chain", params={"hash": bad}, headers=_auth(mgr))
        assert resp.status_code == 422, bad

    # 合法 hash 但无记录 -> 404(不泄露路径)
    mgr.store.get = lambda h: None
    assert client.get(f"/api/relocate/chain?hash={HASH}", headers=_auth(mgr)).status_code == 404


def test_chain_endpoint_ignores_path_param(web_env, tmp_path):
    src = tmp_path / "src"
    target = src / "target"
    target.mkdir(parents=True)
    link = src / "link"
    _link(link, target)
    mgr, client, _rec = _install(web_env, str(link))

    resp = client.get(f"/api/relocate/chain?hash={HASH}&path={target}", headers=_auth(mgr))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["start"] == path_normalize(str(link)), "起点必须由服务端派生, 客户端 path 参数无效"
    assert [n["path"] for n in data["nodes"]] == [path_normalize(str(link)), path_normalize(str(target))]


def test_chain_walk_types_targets_and_attribution(web_env, tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    c_dir = src / "c"
    c_dir.mkdir()
    b_link = src / "b"
    _link(b_link, c_dir)
    a_link = src / "a"
    kind_a = _link(a_link, b_link)

    job = {
        "hashes": [HASH],
        "alias_paths": [str(a_link), str(b_link)],
        "job_id": "job-1",
        "phase": "armed",
        "origin": "web",
        "armed_at": 100.0,
        "updated_at": 200.0,
        "mover": HASH,
        "attempts": 0,
        "last_error": "",
        "alias_kind": kind_a,
    }
    snap = SimpleNamespace(jobs=(job, ), generation=7)
    mgr, client, _rec = _install(web_env, str(a_link), snap)

    resp = client.get(f"/api/relocate/chain?hash={HASH}", headers=_auth(mgr))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    nodes = data["nodes"]
    assert data["env"] == "local" and len(nodes) == 3
    assert nodes[0]["path"] == path_normalize(str(a_link))
    assert nodes[0]["type"] in (alias_fs.KIND_SYMLINK, alias_fs.KIND_JUNCTION)
    assert nodes[0]["target"] == path_normalize(str(b_link))
    assert nodes[1]["target"] == path_normalize(str(c_dir))
    assert nodes[2]["type"] == alias_fs.KIND_DIR and nodes[2]["status"] == "ok"
    assert nodes[0]["attribution"]["auto"] is True
    assert nodes[0]["attribution"]["job_id"] == "job-1"
    assert nodes[0]["attribution"]["origin"] == "web"
    assert nodes[0]["attribution"]["phase"] == "armed"
    assert nodes[0]["attribution"]["armed_at"] == 100.0
    assert nodes[0]["attribution"]["is_mover"] is True
    assert nodes[1]["attribution"]["auto"] is True
    assert nodes[2]["attribution"] == {"auto": False}, "未登记的落点必须标非 auto-qb 设置"


def test_chain_cycle_and_hop_limit(web_env, tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    a = src / "a"
    b = src / "b"
    _link(a, b)
    _link(b, a)
    mgr, client, _rec = _install(web_env, str(a))
    resp = client.get(f"/api/relocate/chain?hash={HASH}", headers=_auth(mgr))
    nodes = resp.json()["nodes"]
    assert nodes[-1]["status"] == "cycle" and "环" in nodes[-1]["reason"]
    assert nodes[-1]["path"] == path_normalize(str(a))

    # 9 条链接 -> 只允许跟随 8 跳, 第 9 跳标「链路过长」
    chain_src = tmp_path / "limits"
    chain_src.mkdir()
    (chain_src / "d9").mkdir()
    for i in range(8, -1, -1):
        _link(chain_src / f"d{i}", chain_src / f"d{i + 1}")
    mgr2, client2, _rec2 = _install(web_env, str(chain_src / "d0"))
    nodes = client2.get(f"/api/relocate/chain?hash={HASH}", headers=_auth(mgr2)).json()["nodes"]
    assert nodes[-1]["status"] == "limit" and "8" in nodes[-1]["reason"]


def test_chain_cache_ttl_refresh_and_capacity(web_env, tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    mgr, client, _rec = _install(web_env, str(src))
    first = client.get(f"/api/relocate/chain?hash={HASH}", headers=_auth(mgr)).json()
    second = client.get(f"/api/relocate/chain?hash={HASH}", headers=_auth(mgr)).json()
    assert second["cached"] is True and second["probed_at"] == first["probed_at"]
    refreshed = client.get(f"/api/relocate/chain?hash={HASH}&refresh=1", headers=_auth(mgr)).json()
    assert refreshed["cached"] is False and refreshed["probed_at"] >= first["probed_at"]

    calls = {"n": 0}

    def _load():
        calls["n"] += 1
        return {"n": calls["n"]}

    cache = relocate_chain.ChainCache(ttl=10.0, capacity=2, clock=FakeClock())
    value, hit = cache.get("k", _load)
    assert value == {"n": 1} and hit is False
    value, hit = cache.get("k", _load)
    assert value == {"n": 1} and hit is True
    cache._clock.advance(11.0)  # TTL 过期语义走注入假钟(判据②), 不真睡等过期
    value, hit = cache.get("k", _load)
    assert value == {"n": 2} and hit is False, "TTL 过期后必须重探"
    cache.get("x", _load)
    cache.get("y", _load)
    assert len(cache._data) == 2, "容量上限必须淘汰最久未用条目"


def test_chain_mapped_and_remote_are_unknown_not_guessed():
    roots = ["C:/root"]
    mapped = relocate_chain.probe_chain("C:/root/a", roots, {}, HASH, env=relocate_chain.ENV_MAPPED)
    assert mapped["nodes"][0]["status"] == "unknown"
    assert "映射" in mapped["nodes"][0]["reason"]
    remote = relocate_chain.probe_chain("//server/share/a", roots, {}, HASH, env=relocate_chain.ENV_REMOTE)
    assert remote["nodes"][0]["status"] == "unknown"
    assert "远程" in remote["nodes"][0]["reason"]
    outside = relocate_chain.probe_chain("/etc/passwd", ["C:/root"], {}, HASH)
    assert outside["nodes"][0]["status"] == "outside_scope"
    empty = relocate_chain.probe_chain("", roots, {}, HASH)
    assert empty["nodes"][0]["status"] == "unknown"


def test_probe_chain_edge_states(tmp_path, monkeypatch):
    assert relocate_chain.path_within_roots("", ["C:/root"]) is False
    assert relocate_chain.path_within_roots("C:/root/a", ["", "C:/root"]) is True
    assert relocate_chain.build_alias_index(SimpleNamespace(jobs=({"hashes": [HASH], "alias_paths": []}, )), HASH) == {}

    missing = relocate_chain.probe_chain(str(tmp_path / "gone"), [str(tmp_path)], {}, HASH)
    assert missing["nodes"][0]["status"] == "missing"

    outside_root = tmp_path / "root"
    outside_root.mkdir()
    outside_target = tmp_path / "outside"
    outside_target.mkdir()
    link = outside_root / "link"
    _link(link, outside_target)
    escaped = relocate_chain.probe_chain(str(link), [str(outside_root)], {}, HASH)
    assert escaped["nodes"][-1]["status"] == "outside_scope"

    fake = alias_fs.PathInspection(status="ok", kind=alias_fs.KIND_SYMLINK, target="\\??\\Volume{1}\\x")
    monkeypatch.setattr(relocate_chain.alias_fs, "inspect_path", lambda p: fake)
    unmappable = relocate_chain.probe_chain(str(link), [str(outside_root)], {}, HASH)
    assert unmappable["nodes"][-1]["status"] == "unknown"
    assert "无法映射" in unmappable["nodes"][-1]["reason"]


def test_chain_start_derivation_and_env(web_env, tmp_path, monkeypatch):
    src = tmp_path / "src"
    src.mkdir()
    mgr, client, rec = _install(web_env, str(src))

    # 1) 记录三项皆空 -> 起点空, 如实给「未确认」而不是随手换一个路径
    rec.root_path = rec.content_path = rec.save_path = ""
    empty = client.get(f"/api/relocate/chain?hash={HASH}", headers=_auth(mgr)).json()
    assert empty["start"] == "" and empty["nodes"][0]["status"] == "unknown"

    # 2) 映射态: 起点派生不做 syscall, 环境标 mapped
    rec.root_path, rec.save_path = "D:/Downloads/seed", "D:/Downloads"
    with monkeypatch.context() as m:
        m.setattr(fa_mod, "get_file_access", lambda: fa_mod.MappedFileAccess(()))
        mapped = client.get(f"/api/relocate/chain?hash={HASH}", headers=_auth(mgr)).json()
    assert mapped["env"] == "mapped"
    assert mapped["start"] == path_normalize("D:/Downloads/seed")
    assert "映射" in mapped["nodes"][0]["reason"]

    # 3) 远程 UNC: 不做本机 syscall, 环境标 remote
    #    ! 不能把 inspect_path 换成 stub 完事 —— 那样只是"用假实现避免真实网络 syscall",
    #    无法证明路由真的没调它; 这里计数并断言 0 次(起点派生/链探测都不得碰 UNC)
    rec.root_path, rec.save_path = "//server/share/seed", "//server/share"
    probes = []
    with monkeypatch.context() as m:
        m.setattr(alias_fs, "inspect_path", lambda p: probes.append(p))
        remote = client.get(f"/api/relocate/chain?hash={HASH}", headers=_auth(mgr)).json()
    assert remote["env"] == "remote" and "远程" in remote["nodes"][0]["reason"]
    assert probes == [], f"远端 UNC 不得做本机 syscall, 实际探测了: {probes}"

    # 4) 候选全越界/不可用 -> 回退首选候选并如实标范围外(不换成可用路径假装成功)
    rec.root_path, rec.content_path = str(tmp_path / "elsewhere"), str(tmp_path / "elsewhere2")
    rec.save_path = str(src / "gone")
    fallback = client.get(f"/api/relocate/chain?hash={HASH}", headers=_auth(mgr)).json()
    assert fallback["start"] == path_normalize(str(tmp_path / "elsewhere"))
    assert fallback["nodes"][0]["status"] == "outside_scope"


def test_inspect_path_link_variants(tmp_path, monkeypatch):
    # UNC 扩展前缀与空目标: 归一失败时返回空串(让调用方标未确认)
    assert alias_fs.strip_device_prefix("\\\\?\\UNC\\server\\share") == "\\\\server\\share"
    assert alias_fs.resolve_link_target("", "/a/link") == ""

    # 父目录不可读 -> 不判挂载点(返回 False, 不猜)
    def _deny(path):
        raise PermissionError(13, "denied")

    monkeypatch.setattr(alias_fs.os, "lstat", _deny)
    assert alias_fs._is_mount_point(str(tmp_path / "d"), SimpleNamespace(st_dev=1)) is False

    # 重解析点标签 SYMLINK(不依赖 islink): 分类为符号链接并能读目标
    st_tag = SimpleNamespace(
        st_mode=stat.S_IFDIR,
        st_nlink=1,
        st_dev=1,
        st_reparse_tag=alias_fs.IO_REPARSE_TAG_SYMLINK,
    )
    monkeypatch.setattr(alias_fs.os, "lstat", lambda p: st_tag)
    monkeypatch.setattr(alias_fs.os, "readlink", lambda p: str(tmp_path / "target"))
    tagged = alias_fs.inspect_path(str(tmp_path / "link"))
    assert tagged.status == "ok" and tagged.kind == alias_fs.KIND_SYMLINK
    assert tagged.target == str(tmp_path / "target")

    # POSIX S_ISLNK 分支(无重解析标签)
    st_link = SimpleNamespace(st_mode=stat.S_IFLNK, st_nlink=1, st_dev=1)
    monkeypatch.setattr(alias_fs.os, "lstat", lambda p: st_link)
    assert alias_fs.inspect_path(str(tmp_path / "l2")).kind == alias_fs.KIND_SYMLINK

    # readlink 失败 -> 未确认(不猜目标), 只给原因
    monkeypatch.setattr(alias_fs.os, "readlink", _deny)
    bad = alias_fs.inspect_path(str(tmp_path / "l3"))
    assert bad.status == "unknown" and bad.kind == alias_fs.KIND_SYMLINK
    assert "权限不足" in bad.error


def test_inspect_path_error_classification(tmp_path, monkeypatch):
    missing = alias_fs.inspect_path(str(tmp_path / "nope"))
    assert missing.status == "missing" and "不存在" in missing.error

    def _boom(path):
        raise PermissionError(13, "denied")

    monkeypatch.setattr(alias_fs.os, "lstat", _boom)
    denied = alias_fs.inspect_path(str(tmp_path / "x"))
    assert denied.status == "permission" and "权限不足" in denied.error

    def _weird(path):
        raise OSError(95, "not supported")

    monkeypatch.setattr(alias_fs.os, "lstat", _weird)
    unknown = alias_fs.inspect_path(str(tmp_path / "y"))
    assert unknown.status == "unknown"

    monkeypatch.setattr(
        alias_fs.os,
        "lstat",
        lambda p: SimpleNamespace(st_mode=stat.S_IFSOCK, st_nlink=1, st_dev=1),
    )
    assert alias_fs.inspect_path(str(tmp_path / "z")).kind == alias_fs.KIND_OTHER


def test_alias_helpers(tmp_path):
    assert alias_fs.strip_device_prefix("\\??\\C:\\a\\b") == "C:\\a\\b"
    assert alias_fs.strip_device_prefix("\\\\?\\C:\\a\\b") == "C:\\a\\b"
    assert path_normalize(alias_fs.resolve_link_target("../b", "/a/c/link")) == "/a/b"
    assert alias_fs.resolve_link_target("\\??\\Volume{1}\\x", "C:/a") == ""

    hard_target = tmp_path / "f"
    hard_target.write_text("x", encoding="utf-8")
    hard_link = tmp_path / "f2"
    try:
        os.link(str(hard_target), str(hard_link))
    except OSError as exc:  # pragma: no cover - 文件系统不支持硬链接
        pytest.skip(f"文件系统不支持硬链接, 跳过硬链接识别: {exc}")
    info = alias_fs.inspect_path(str(hard_link))
    assert info.kind == alias_fs.KIND_HARDLINK and info.nlink >= 2

    mount = alias_fs.inspect_path("/")
    assert mount.status == "ok" and mount.is_mount is False, "根目录不得被认成挂载点"


def test_chain_alias_index_prefers_active_job():
    old = {"hashes": [HASH], "alias_paths": ["C:/x"], "job_id": "old", "phase": "failed", "updated_at": 10.0}
    active = {"hashes": [HASH], "alias_paths": ["C:/x"], "job_id": "active", "phase": "armed", "updated_at": 20.0}
    snap = SimpleNamespace(jobs=(old, active))
    index = relocate_chain.build_alias_index(snap, HASH)
    assert list(index.values()) == [active]
    assert job_rank(active) > job_rank(old)

    other = {"hashes": ["b" * 40], "alias_paths": ["C:/x"], "job_id": "other", "phase": "armed", "updated_at": 30.0}
    snap = SimpleNamespace(jobs=(old, active, other))
    assert list(relocate_chain.build_alias_index(snap, HASH).values()) == [active], \
        "别的 hash 的 job 不得串到本种子的归属章"


def test_chain_frontend_static_and_node():
    js = _static("shared/relocate_chain.js")
    assert "/api/relocate/chain?hash=" in js and "refresh=1" in js
    assert "relChainOpen" in js and "relChainClose" in js and "relChainRefresh" in js
    # 列表渲染期零探测: 只有浮窗模块碰端点, 徽标渲染文件绝不能出现
    assert "/api/relocate/chain" not in _static("shared/decorate.js")
    cells = _static("shared/tpl/xtpl-cells.html")
    assert "relChainOpen" not in cells, "徽标模板只负责触发 relocateOpen, 浮窗取数在 JS 方法里"
    assert "AQB_RELOCATE_CHAIN" in _static("shared/app.js")
    for skin in ("console", "atlas", "prism", "flux"):
        assert "/shared/relocate_chain.js" in (ROOT / f"src/auto_qb/webui/static/{skin}/index.html").read_text(
            encoding="utf-8"
        )

    pop = _static("shared/tpl/popovers.html")
    for needle in (
        'role="dialog"', 'aria-label="迁移路径链"', 'tabindex="-1"', '@keydown.esc', "relc-backdrop", "relChainRefresh()",
        "relChainCopyAll()"
    ):
        assert needle in pop, needle
    assert ">关闭路径链<" in pop or 'aria-label="关闭路径链"' in pop
    # 浮窗底(P1-4): shared 基线仍不透明 --bg-pop(另三皮肤无毛玻璃); flux 侧 2026-11-04 全浮层
    # 玻璃化 —— html[data-fx-preset] 前缀覆盖为半透明 --bg-card + blur(详见 _scan_flux_modal_frost)
    css = _static("shared/row_lang.css")
    pop_css = css.split(".relc-pop {", 1)[1].split("}", 1)[0]
    assert "background: var(--bg-pop)" in pop_css, "路径链浮窗 shared 基线必须用不透明 --bg-pop"
    flux_pop = _static("flux/css/dialogs.css")
    assert re.search(r"html\[data-fx-preset\] :is\([^)]*\.relc-pop[^)]*\)\s*\{[^}]*var\(--bg-card\)", flux_pop), \
        "flux 侧路径链浮窗必须玻璃化覆盖(半透明 --bg-card + blur), 与全浮层玻璃化档位一致"
    # 长链可滚(P2-4): 浮窗自身 overflow:auto, 内部滚动不得触发「滚动即关」
    assert "overflow: auto" in pop_css
    assert "pop.contains(t)" in js, "滚动关闭必须放过浮窗内部滚动, 否则长链滚不动"
    rows = _static("shared/drawer_rows.js")
    assert 'act: "chain"' in rows and 'A → B → C' in rows
    for tpl in (
        "shared/drawer_tpl/01-general-hero-tall.js", "shared/drawer_tpl/02-general-cards-low.js",
        "shared/drawer_tpl/03-general-dossier-collapsed.js"
    ):
        assert 'data-act="chain"' in _static(tpl) and "ctx.relChainOpen" in _static(tpl)
    assert "relChain.open" in _static("shared/lifecycle.js"), "Esc 必须进退栈链"
    assert "this.relChain.open" in _static("shared/dialogs_meta.js")
    assert "this.relChain.open" in _static("shared/shortcuts_engine.js")

    node = shutil.which("node")
    if not node:
        return
    probe = r"""
const fs=require('fs'),vm=require('vm');
const sandbox={window:{},console};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),sandbox);
const M=Object.assign({},sandbox.window.AQB_RELOCATE_CHAIN.methods);
const call=(n,a)=>M[n].call(Object.assign({},M),a);
process.stdout.write(JSON.stringify({
  dataKeys:Object.keys(sandbox.window.AQB_RELOCATE_CHAIN.data()),
  junction:call('relChainTypeText','junction'),
  hardlink:call('relChainTypeText','hardlink'),
  dir:call('relChainTypeText','dir'),
  mount:call('relChainTypeText','mount'),
  unknownType:call('relChainTypeText','nope'),
  okStatus:call('relChainStatusText',{status:'ok'}),
  missingStatus:call('relChainStatusText',{status:'missing'}),
  limitStatus:call('relChainStatusText',{status:'limit'}),
  unknownStatus:call('relChainStatusText',{status:'unknown',reason:'boom'}),
  phase:call('relChainPhaseText','armed'),
  phaseWatching:call('relChainPhaseText','watching'),
  phaseMoved:call('relChainPhaseText','moved'),
  phaseRewritten:call('relChainPhaseText','rewritten'),
  probed:Object.assign(M,{fmtTs:()=>'T'})['relChainProbedText'].call(
    Object.assign({},M,{fmtTs:()=>'T',relChain:{data:{probed_at:1,cached:false}}}))
}));
"""
    proc = subprocess.run(
        [node, "-e", probe, str(ROOT / "src/auto_qb/webui/static/shared/relocate_chain.js")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["dataKeys"] == ["relChain"]
    assert out["junction"] == "junction" and out["hardlink"] == "硬链接"
    assert out["dir"] == "普通目录" and out["mount"] == "挂载点" and out["unknownType"] == "未知类型"
    assert out["okStatus"] == "已确认" and out["missingStatus"] == "路径不存在"
    assert out["limitStatus"] == "链路过长"
    assert out["unknownStatus"] == "未确认: boom"
    assert out["phase"] == "待收尾"
    # 十个相位都必须落在用户状态词表(P1): 落空会显示「未知状态」
    assert out["phaseWatching"] == "迁移中"
    assert out["phaseMoved"] == "待收尾"
    assert out["phaseRewritten"] == "待收尾"
    assert out["probed"].startswith("探测于 T")


# ---------------------------------------------------------------- S3 收尾反馈面与「立即收尾」按钮(计划 26-11-05-0808)


def test_finalize_now_route_contract(web_env, tmp_path):
    """D14 端点契约: 403 门控 / 未确认只回现场说明(零动作) / 后端窗口复核(快照无
    FINALIZE_WINDOW 相位 job -> blocked, 前端可见性不是授权) / 确认 -> app_shutdown ->
    ok / shutdown 被拒 -> degraded 降级提示手动重启(不重试) / 断连 503(前端同降级)"""
    from auto_qb.core.modules.relocate_units import FINALIZE_WINDOW_PHASES

    mgr, client = web_env
    # 403 门控(relocate 默认关, fail-closed)
    assert client.post("/api/relocate/finalize-now", json={"confirm": True}, headers=_auth(mgr)).status_code == 403
    mgr.config.relocate = SimpleNamespace(enabled=True)

    # 未确认: 只回现场说明(cls=confirm, 数据零动作 —— 成本先行, 与 relocate_cancel 同口径)
    r = client.post("/api/relocate/finalize-now", json={}, headers=_auth(mgr))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["cls"] == "confirm" and "重启 qB" in body["note"], body

    # 确认但快照无收尾窗口 job: blocked(保守默认, 误触防护的后端半)
    r = client.post("/api/relocate/finalize-now", json={"confirm": True}, headers=_auth(mgr))
    assert r.json()["cls"] == "blocked", r.json()

    shutdown_calls = []
    mgr.client = SimpleNamespace(app_shutdown=lambda: shutdown_calls.append("go"))
    job = {"job_id": "j1", "phase": sorted(FINALIZE_WINDOW_PHASES)[0], "hashes": [HASH]}
    mgr.ctx = SimpleNamespace(
        relocate=SimpleNamespace(jobs_snapshot=lambda: SimpleNamespace(jobs=(job, ), generation=1))
    )

    # 确认 -> app_shutdown 下发 -> ok + 手动重启提示
    r = client.post("/api/relocate/finalize-now", json={"confirm": True, "job_id": "j1"}, headers=_auth(mgr))
    body = r.json()
    assert body["cls"] == "ok" and shutdown_calls == ["go"], body
    assert "手动重启" in body["note"], body

    # job_id 不在窗口(已推进/不存在): 拒, 零下发
    r = client.post("/api/relocate/finalize-now", json={"confirm": True, "job_id": "other"}, headers=_auth(mgr))
    assert r.json()["cls"] == "blocked", r.json()
    assert shutdown_calls == ["go"]

    # app_shutdown 被拒: 降级 degraded + 手动重启提示(不重试、不自动重启)
    def _boom():
        raise RuntimeError("rejected")

    mgr.client.app_shutdown = _boom
    r = client.post("/api/relocate/finalize-now", json={"confirm": True, "job_id": "j1"}, headers=_auth(mgr))
    body = r.json()
    assert body["cls"] == "degraded" and "手动重启" in body["note"], body
    assert shutdown_calls == ["go"], "降级路径不得重试"

    # qB 断连: 503(require_client 既有语义; 前端 catch 到后同样降级提示)
    mgr.client = None
    r = client.post("/api/relocate/finalize-now", json={"confirm": True, "job_id": "j1"}, headers=_auth(mgr))
    assert r.status_code == 503, r.text


def test_chain_finalize_face_in_response(web_env, tmp_path):
    """链响应附带 finalize 反馈面(不进缓存): pending 现读(rewrites 已收口出账) /
    daemon_stale(无账=True, 健康在位=False) / window 相位单点(armed=True, rewritten=True,
    S4 新相位集; 前段 moved=False); 旧链 spec(无 bt_backup)与 journal 终态恒 pending=0
    (「重启 qB 即完成」只对新链成立)"""
    from auto_qb.infra import relocate_journal as rj

    src = tmp_path / "src"
    target = src / "t"
    target.mkdir(parents=True)
    link = src / "l"
    _link(link, target)
    job = {"job_id": "j1", "phase": "armed", "hashes": [HASH], "alias_paths": [str(link)], "mover": HASH}
    mgr, client, _rec = _install(web_env, str(link), SimpleNamespace(jobs=(job, ), generation=1))
    backup = tmp_path / "BT_backup"
    backup.mkdir()
    rj.write_spec(
        str(tmp_path), "j1", {
            "job_id": "j1",
            "src": "R:/src",
            "dst": "R:/dst",
            "hashes": ["h1", "h2"],
            "host": "127.0.0.1",
            "port": 1,
            "bt_backup": str(backup),
            "members": [{
                "hash_v1": "h1",
                "hash_v2": ""
            }, {
                "hash_v1": "h2",
                "hash_v2": ""
            }],
        }
    )
    rj.record_rewrites(str(tmp_path), "j1", {"h1": {"status": "rewritten"}}, ts=1.0)

    data = client.get(f"/api/relocate/chain?hash={HASH}", headers=_auth(mgr)).json()
    face = data["finalize"]
    assert face["job_id"] == "j1" and face["phase"] == "armed", face
    assert face["window"] is True and face["pending"] == 1 and face["daemon_stale"] is True, face

    # 相位单点: rewritten 也在收尾窗口集 -> window True; 前段 moved -> False
    mgr.ctx.relocate.jobs_snapshot = lambda: SimpleNamespace(jobs=(dict(job, phase="rewritten"), ), generation=2)
    data = client.get(f"/api/relocate/chain?hash={HASH}", headers=_auth(mgr)).json()
    assert data["finalize"]["window"] is True, data["finalize"]
    mgr.ctx.relocate.jobs_snapshot = lambda: SimpleNamespace(jobs=(dict(job, phase="moved"), ), generation=3)
    data = client.get(f"/api/relocate/chain?hash={HASH}", headers=_auth(mgr)).json()
    assert data["finalize"]["window"] is False, data["finalize"]

    # daemon 健康在位(pid 活 + 心跳新鲜) -> daemon_stale False
    rj.write_daemon_state(str(tmp_path), rj.instance_key("127.0.0.1", 1), os.getpid())
    data = client.get(f"/api/relocate/chain?hash={HASH}", headers=_auth(mgr)).json()
    assert data["finalize"]["daemon_stale"] is False, data["finalize"]
    rj.release_daemon_state(str(tmp_path), rj.instance_key("127.0.0.1", 1), os.getpid())

    # 旧链 spec(无 bt_backup): pending 恒 0(daemon 不认领, 提示不成立)
    rj.write_spec(
        str(tmp_path), "j1", {
            "job_id": "j1",
            "src": "R:/src",
            "dst": "R:/dst",
            "hashes": ["h1", "h2"],
            "host": "127.0.0.1",
            "port": 1,
        }
    )
    data = client.get(f"/api/relocate/chain?hash={HASH}", headers=_auth(mgr)).json()
    assert data["finalize"]["pending"] == 0, data["finalize"]

    # journal 终态(已取消): pending 恒 0(反馈面不再悬)
    rj.write_spec(
        str(tmp_path), "j1", {
            "job_id": "j1",
            "src": "R:/src",
            "dst": "R:/dst",
            "hashes": ["h1", "h2"],
            "host": "127.0.0.1",
            "port": 1,
            "bt_backup": str(backup),
        }
    )
    rj.write_journal(str(tmp_path), "j1", {"phase": "cancelled"})
    data = client.get(f"/api/relocate/chain?hash={HASH}", headers=_auth(mgr)).json()
    assert data["finalize"]["pending"] == 0, data["finalize"]


def test_finalize_button_and_hint_static():
    """前端静态守阵(D14 按钮 + S3 提示): 浮窗模板挂按钮/提示, JS 有确认框与降级文案,
    端点路径只出现在链模块(渲染面零调用)"""
    pop = _static("shared/tpl/popovers.html")
    for needle in (
        "立即收尾", "relChainFinalizeNow()", "relChainFinalizeWindow()", "relChainFinalizePending()", "待收尾: 重启 qB 即完成"
    ):
        assert needle in pop, needle
    js = _static("shared/relocate_chain.js")
    for needle in ("/api/relocate/finalize-now", "confirmDialog(", "手动重启 qB", "finalizing", "danger: true"):
        assert needle in js, needle
    # 渲染面零调用: 徽标/行文件不得出现按钮或端点
    for rel in ("shared/decorate.js", "shared/drawer_rows.js"):
        assert "/api/relocate/finalize-now" not in _static(rel), rel
        assert "relChainFinalizeNow" not in _static(rel), rel
