"""RM04 P0–P3 真机取证 —— 迁移可见性(分支 feat/webui-relocate-visibility, HEAD 3dd603f9)。

本条覆盖评审列出的七项未覆盖风险里可自动化固化的部分:
- [RM04-15] 四皮肤行高/徽标几何、浮窗定位与滚动关闭、Esc 逐层退栈、组行入口基准;
  顺带在 armed 状态用真实链路验证「归属章 auto=true」(src 内容根 junction -> dst)。
- [RM04-16] 人工 A->B->C 链(逐跳 type/status/attribution)、6+ 跳长链、UNC 不可达快速返回;
  符号链接段在无 SeCreateSymbolicLinkPrivilege 时降级为 junction 并如实记录(不伪报)。
- [RM04-17] pending_tag 生命周期(armed 真加 -> 手删不重加 -> 重启 reconcile 补写 -> 终态真摘 1 次)。
- [RM04-18] pending_tag 关闭时零写请求(qB 代理计数证明)。
- [RM04-19] 未 armed 直接撤销: 终态不得发 remove(代理计数 0); 对照 armed 终态仍 1 次(RM04-17)。
-RM04-15 另含 P1-2 详情「迁移」段「设置时间」真渲染取证(值须等于 state job.created_at)。

跑法: `commands run real.run -- --case RM04-15 --yes`(同理 RM04-16/17/18/19)。
纪律: 只用 real-fake 假种子与副实例; 临时改 qB 默认 save_path 测毕还原; 产物只落 .work。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_rm04_relocate as M  # noqa: E402  (复用 RM04 的造种/清场/断言助手)

from lib import app, instances, torrent as lib_torrent  # noqa: E402
from lib.proxy import TcpProxy  # noqa: E402

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="本片断言含 Windows 特有语义(junction/symlink/UNC)"),
]
LIB_DIR = HERE.parent / "lib"

PENDING_TAG = "zRelocatePending"
TAG_ADD_PATHS = ("/api/v2/torrents/addTags", )
TAG_REMOVE_PATHS = ("/api/v2/torrents/removeTags", )

# ---------------------------------------------------------------- 公共助手


def make_cfg(case: Path,
             *,
             qb_port: int | None = None,
             pending_tag: str | None = None,
             alias_threshold: int = 1) -> tuple[Path, int]:
    """在 RM04 模板上派生: 可换 qB 端口(经代理计数)/可开 pending_tag/压低别名阈值。"""
    cfg, web_port = M.write_cfg(case, relocate=True, alias_threshold=alias_threshold)
    text = cfg.read_text(encoding="utf-8")
    if qb_port and qb_port != instances.SECONDARY:
        text = text.replace(f"port: {instances.SECONDARY}", f"port: {qb_port}")
    if pending_tag:
        anchor = f"alias_file_threshold: {alias_threshold}"
        assert anchor in text, "模板里找不到 alias_file_threshold 锚点"
        text = text.replace(anchor, f"{anchor}\n        pending_tag: {pending_tag}")
    cfg.write_text(text, encoding="utf-8")
    return cfg, web_port


def files_of(name: str, count: int = 3, size: int = 256 * 1024) -> list[tuple[str, int]]:
    return [(f"{name}/sub/f{i:02d}.bin", size) for i in range(count)]


def seed_pair(qb, name: str, files: list[tuple[str, int]], savepath: Path) -> tuple[str, str]:
    """同内容两成员(不同 piece_len -> 不同 infohash), 第二枚沿用已落数据。"""
    h1 = M.fake_multi(qb, name, files, savepath, name)
    h2 = M.fake_multi(qb, name, files, savepath, name, piece_len=32768, write=False)
    return h1, h2


def start_product(cfg: Path, case: Path, *, qb_port: int | None = None) -> "app.AppProc":
    """起产品进程; qb_port 指向代理时绕开 app.start 的「必须直连副实例」复核(端口仍只许副实例链路)。"""
    if qb_port is None or qb_port == instances.SECONDARY:
        p = app.start(cfg, case)
    else:
        text = cfg.read_text(encoding="utf-8")
        assert f"port: {qb_port}" in text, f"配置未指向预期 qB 端口 {qb_port}"
        assert f"port: {instances.PRIMARY}" not in text, "配置指向主实例, 拒跑"
        popen = subprocess.Popen(
            [str(app.PY), "-m", "auto_qb", str(cfg)],
            cwd=str(app.ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={
                **os.environ, "PYTHONIOENCODING": "utf-8"
            },
        )
        p = app.AppProc(popen, case, cfg)
    assert p.wait_web(40), f"WEB 没起来:\n{p.log()[-800:]}"
    assert p.wait_log("整组迁移已启用", 20), f"relocate 启动日志缺失:\n{p.log()[-600:]}"
    return p


def member_rel(web_port: int, h: str) -> dict | None:
    for g in M.groups_view(web_port):
        for m in g.get("members") or []:
            if m.get("hash") == h:
                return m.get("relocate")
    return None


def wait_live_phase(web_port: int, h: str, phase: str, timeout: float, desc: str) -> dict:
    t0 = time.time()
    last = None
    while time.time() - t0 < timeout:
        last = member_rel(web_port, h)
        if last and last.get("phase") == phase:
            return last
        time.sleep(1.0)
    raise AssertionError(f"{desc} (最后 relocate={json.dumps(last, ensure_ascii=False)})")


def wait_in_store(web_port: int, h: str, timeout: float = 60.0) -> None:
    """等产品 store 快照出现该种子(不要求 progress==1; junction 链种子用这条)。"""
    M.wait_until(
        lambda: any(m.get("hash") == h for g in M.groups_view(web_port) for m in g.get("members") or []),
        timeout,
        f"store 快照未出现种子 {h[:8]}",
    )


def wait_chain_ready(web_port: int, h: str, timeout: float = 60.0) -> None:
    """等链端点可用(404 => store 尚未收录)。

    UNC 保存路径的种子实测不进 `/api/groups`(见 RM04-16 证据的 unc_in_groups=false),
    故不能用 wait_in_store; 直接以链端点 200 作为「store 已有该记录」判据。
    """
    def ready() -> bool:
        try:
            M.web_req(web_port, "GET", f"/api/relocate/chain?hash={h}")
            return True
        except Exception:  # noqa: BLE001 - 404/连接抖动都算未就绪
            return False

    M.wait_until(ready, timeout, f"链端点未就绪(种子 {h[:8]} 未进 store)")


def start_migration(web_port: int, h: str, dst: Path) -> tuple[str, dict]:
    r1 = M.cmd_post_and_wait(web_port, f"/api/torrents/{h}/location", {"location": str(dst)})
    items = [it for it in ((r1.get("truth") or {}).get("results") or []) if it.get("cls") == "confirm"]
    assert items, f"首投缺 confirm 项: {json.dumps(r1, ensure_ascii=False)[:500]}"
    assert items[0].get("form") == "dir_alias", f"首投形态不是目录别名: {items[0].get('form')}"
    r2 = M.cmd_post_and_wait(web_port, f"/api/torrents/{h}/location", {"location": str(dst), "confirm": True})
    assert r2.get("status") == "ok", f"确认后回执 status 非 ok: {r2}"
    item = M.one_started_item(r2)
    job_id = item.get("job_id")
    assert job_id, f"确认后 started 项缺 job_id: {json.dumps(r2, ensure_ascii=False)[:600]}"
    assert item.get("form") == "dir_alias", f"实际形态非目录别名: {item.get('form')}"
    return job_id, item


def wait_armed(case: Path, web_port: int, job_id: str, hashes: list[str]) -> dict:
    M.wait_until(lambda: "已武装收尾" in M.log_text(case), 60, "日志缺「已武装收尾」(arm 段没走)")
    live = wait_live_phase(web_port, hashes[0], "armed", 60, "成员 live 相位未到 armed")
    job = M.wait_job_phase(case, job_id, {"armed"}, 90, "state.json 里 job 未落 armed")
    return {"live": live, "job": job}


def mklink_junction(link: Path, target: Path) -> None:
    if link.exists() or M._is_link(link):
        M.purge_tree(link)
    link.parent.mkdir(parents=True, exist_ok=True)
    target.mkdir(parents=True, exist_ok=True)
    rc = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True, text=True, timeout=20
    )
    assert rc.returncode == 0, f"mklink /J 失败: {rc.stdout} {rc.stderr}"
    assert M.reparse_kind(link) == "junction", f"链接不是 junction: {link} -> {M.reparse_kind(link)}"


def try_symlink(link: Path, target: Path) -> tuple[bool, str]:
    """尽力造目录符号链接; Windows 无 SeCreateSymbolicLinkPrivilege 时如实返回失败原因。"""
    try:
        link.symlink_to(target, target_is_directory=True)
        return True, ""
    except OSError as exc:
        return False, f"winerror={getattr(exc, 'winerror', '')} {exc}"


def run_ui(
    web_port: int,
    case: Path,
    *,
    group_a: str,
    group_b: str,
    mover: str,
    chain_hash: str,
    group_a_save: str = ""
) -> dict:
    out_dir = case / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(
        {
            "RM_UI_BASE": f"http://127.0.0.1:{web_port}",
            "RM_UI_GROUP_A": group_a,
            "RM_UI_GROUP_A_SAVE": group_a_save,
            "RM_UI_GROUP_B": group_b,
            "RM_UI_MOVER": mover,
            "RM_UI_CHAIN_HASH": chain_hash,
            "RM_UI_OUT": str(out_dir),
        }
    )
    cp = subprocess.run(
        ["node", str(LIB_DIR / "relocate_visibility_ui.mjs")],
        cwd=str(LIB_DIR.parent.parent),
        env=env,
        capture_output=True,
        text=True,
        timeout=900
    )
    lines = [ln for ln in cp.stdout.splitlines() if ln.startswith("UI_RESULT ")]
    assert lines, (f"UI 脚本没有输出结果(rc={cp.returncode})\n"
                   f"STDOUT:\n{cp.stdout[-3000:]}\nSTDERR:\n{cp.stderr[-3000:]}")
    ev = json.loads(lines[-1][len("UI_RESULT "):])
    assert cp.returncode == 0 and ev.get("ok"), (
        f"UI 脚本失败 rc={cp.returncode}: {ev.get('error')}\n"
        f"STEPS={json.dumps(ev.get('steps'), ensure_ascii=False)}\n"
        f"STDERR:\n{cp.stderr[-1500:]}"
    )
    return ev


def alpha_of(css: str) -> float:
    """rgb()/rgba() 取 alpha; 其它形态按 1.0。"""
    m = re.match(r"rgba?\(([^)]+)\)", css or "")
    if not m:
        return 1.0
    parts = [p.strip() for p in m.group(1).split(",")]
    return float(parts[3]) if len(parts) >= 4 else 1.0


def chain_get(web_port: int, h: str, *, refresh: bool = True) -> tuple[dict, float]:
    q = f"/api/relocate/chain?hash={h}" + ("&refresh=1" if refresh else "")
    t0 = time.perf_counter()
    data = M.web_req(web_port, "GET", q)
    return data, (time.perf_counter() - t0) * 1000.0


def save_evidence(case: Path, name: str, ev: dict) -> None:
    try:
        M.WORK.mkdir(parents=True, exist_ok=True)
        (M.WORK / f"{name}_evidence.json").write_text(json.dumps(ev, ensure_ascii=False, indent=2), encoding="utf-8")
        (M.WORK / f"{name}_auto-qb.log").write_text(app.read_log(case), encoding="utf-8")
    except Exception:  # noqa: BLE001 - 取证失败不得掩盖主断言
        pass


# ---------------------------------------------------------------- RM04-15


def test_rm04_15_webui_visibility_skins_popover():
    """四皮肤行高/徽标几何 + 浮窗定位/滚动关闭/Esc 退栈 + 组行入口基准(armed 状态)。"""
    case = M.case_dir("rm04_15")
    qb = M.qbfake()
    orig_save_path = qb.prefs().get("save_path")
    p = None
    ev = {"case": "RM04-15", "head": M._head_sha()}
    try:
        assert orig_save_path, "副实例 save_path 读取失败(鉴权/连不通?), 拒跑"
        assert not M.rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
        probe_dir = case / "qbsave"
        probe_dir.mkdir(parents=True, exist_ok=True)
        qb.set_prefs(save_path=str(probe_dir))
        time.sleep(0.5)
        assert qb.prefs().get("save_path") == str(probe_dir), "save_path 临时改写未生效(同卷证明不成立)"

        src = M.RAM / "rm04_15" / "src"
        dst_a = case / "dst_a"
        M.purge_tree(M.RAM / "rm04_15")
        dst_a.mkdir(parents=True, exist_ok=True)
        cfg, web_port = make_cfg(case, alias_threshold=1)
        p = start_product(cfg, case)
        ev["web_port"] = web_port

        files_a = files_of("rm04c15a")
        files_b = files_of("rm04c15b")
        h1a, h2a = seed_pair(qb, "rm04c15a", files_a, src)
        h1b, h2b = seed_pair(qb, "rm04c15b", files_b, src)
        M.wait_complete(qb, [h1a, h2a, h1b, h2b], timeout=120)
        assert M.wait_group(web_port, h1a, {h1a, h2a}, 25, "A 组未成组")
        assert M.wait_group(web_port, h1b, {h1b, h2b}, 25, "B 组未成组")
        M.wait_store_progress(web_port, [h1a, h2a, h1b, h2b], timeout=60)

        # --- 人工多层 junction 长链(供浮窗内部滚动取证): chainroot -> L1..L9 -> store
        chain_parent = case / "chain_parent"
        links = ["chainroot"] + [f"L{i}" for i in range(1, 10)]
        targets = links[1:] + ["store"]
        for name, tgt in zip(links, targets):
            mklink_junction(chain_parent / name, chain_parent / tgt)
        chain_files = [("chainroot/sub/f.bin", 200_000)]
        hc = M.fake_multi(qb, "chainroot", chain_files, chain_parent, "rm04c15chain")
        M.wait_complete(qb, [hc], timeout=60)
        wait_in_store(web_port, hc)
        t = qb.torrent(hc) or {}
        assert M.norm(t.get("root_path")) == M.norm(
            chain_parent / "chainroot"
        ), f"qB root_path 不是链首: {t.get('root_path')}"
        chain, ms_preview = chain_get(web_port, hc)
        assert chain["env"] == "local", f"长链 env={chain['env']}"
        assert len(chain["nodes"]) >= 9, f"长链节点数不足(应 >=9): {len(chain['nodes'])}"
        assert all(n["type"] in ("junction",) for n in chain["nodes"][:8]), \
            f"长链前 8 跳应为 junction: {[n['type'] for n in chain['nodes']]}"
        assert all(n["status"] == "ok" for n in chain["nodes"][:8]), "长链前 8 跳状态非 ok"
        assert all(n["attribution"]["auto"] is False for n in chain["nodes"]), "人工链不应归属 auto-qb"
        ev["chain_long"] = {
            "nodes": len(chain["nodes"]),
            "types": [n["type"] for n in chain["nodes"]],
            "statuses": [n["status"] for n in chain["nodes"]],
            "ms": ms_preview
        }

        # --- A 组发起迁移 -> armed(src 内容根成 junction, 供 auto=true 归属取证)
        job_id, _item = start_migration(web_port, h1a, dst_a)
        moved = M.wait_until(
            lambda: next(
                (h for h in (h1a, h2a) if M.norm((qb.torrent(h) or {}).get("save_path")) == M.norm(dst_a)), None
            ), 90, "qB 侧无成员 save_path 变 dst"
        )
        other = h2a if moved == h1a else h1a
        armed = wait_armed(case, web_port, job_id, [h1a, h2a])
        M.wait_until(lambda: M._is_link(src / "rm04c15a"), 45, "src 内容根未成链接")
        assert M.reparse_kind(src / "rm04c15a") == "junction", "src 内容根链接形态非 junction"
        ev.update({"job_id": job_id, "mover": moved, "armed": armed["job"].get("phase")})

        # armed 真实链路: 非搬移成员起点 = src 内容根 -> dst, 首跳必须归属 auto-qb
        chain_other, ms_other = chain_get(web_port, other)
        nodes = chain_other["nodes"]
        assert nodes[0]["type"] == "junction" and nodes[0]["status"] == "ok", f"非搬移成员首跳异常: {nodes[0]}"
        assert nodes[0]["attribution"]["auto"] is True, f"src 内容根别名未归属 auto-qb: {nodes[0]['attribution']}"
        assert nodes[0]["attribution"]["job_id"] == job_id, "归属 job_id 不符"
        assert nodes[0]["attribution"]["is_mover"] is False, "非搬移成员被标成 mover"
        assert M.norm(nodes[-1]["path"]) == M.norm(dst_a / "rm04c15a"), f"链尾不是 dst 内容根: {nodes[-1]['path']}"
        chain_mover, _ms = chain_get(web_port, moved)
        assert len(chain_mover["nodes"]) == 1 and chain_mover["nodes"][0]["type"] == "dir", \
            f"搬移成员起点应是 dst 普通目录: {chain_mover['nodes']}"
        ev["chain_armed"] = {"other_first": nodes[0], "mover_nodes": len(chain_mover["nodes"]), "ms_other": ms_other}

        # --- 浏览器取证
        ui = run_ui(
            web_port, case, group_a="rm04c15a", group_b="rm04c15b", mover=moved, chain_hash=hc, group_a_save=dst_a.name
        )
        ev["ui"] = {
            "skins":
                {
                    k:
                        {
                            "row_heights": {
                                kk: vv["rowH"]
                                for kk, vv in v["rows"].items()
                            },
                            "badge_counts": {
                                kk: vv["badgeCount"]
                                for kk, vv in v["rows"].items()
                            },
                            "badge_in_row": {
                                kk: vv["inRow"]
                                for kk, vv in v["rows"].items()
                            },
                            "badge_in_cell": {
                                kk: vv["inCell"]
                                for kk, vv in v["rows"].items()
                            },
                            "pop_bg": v["popBg"],
                            "shots": [v["shotGroup"], v["shotTor"]]
                        }
                    for k, v in ui["skins"].items()
                },
            "placement": ui["placement"],
            "groupEntry": ui["groupEntry"],
            "steps": ui["steps"],
        }

        # 1) 四皮肤: 带徽标行与对照行等高; 徽标在行内/单元格内
        for skin, v in ui["skins"].items():
            rr = v["rows"]
            assert rr["groupA"]["badgeCount"] >= 1, f"{skin}: A 组行无徽标"
            assert rr["groupB"]["badgeCount"] == 0, f"{skin}: B 组行不该有徽标"
            assert rr["torrentA"]["badgeCount"] >= 1, f"{skin}: A 种子行无徽标"
            assert rr["torrentB"]["badgeCount"] == 0, f"{skin}: B 种子行不该有徽标"
            assert abs(rr["groupA"]["rowH"] - rr["groupB"]["rowH"]) <= 1, \
                f"{skin}: 组行被徽标撑高 {rr['groupA']['rowH']} vs {rr['groupB']['rowH']}"
            assert abs(rr["torrentA"]["rowH"] - rr["torrentB"]["rowH"]) <= 1, \
                f"{skin}: 种子行被徽标撑高 {rr['torrentA']['rowH']} vs {rr['torrentB']['rowH']}"
            for key in ("groupA", "torrentA"):
                assert rr[key]["inRow"] is True, f"{skin}: {key} 徽标垂直越界"
                assert rr[key]["inCell"] is True, f"{skin}: {key} 徽标横向越出路径格"
                assert rr[key]["badgeH"] <= rr[key]["rowH"], f"{skin}: {key} 徽标高于行"
        assert alpha_of(ui["skins"]["flux"]["popBg"]) == 1.0, \
            f"flux 浮窗透底(alpha={alpha_of(ui['skins']['flux']['popBg'])}): {ui['skins']['flux']['popBg']}"

        # 2) 浮窗定位/滚动/Esc
        pl = ui["placement"]
        assert pl["bottomFlip"]["flipAbove"] and pl["bottomFlip"]["flipInView"], \
            f"贴底未向上翻转: {pl['bottomFlip']}"
        assert pl["clamp_left"]["clampLeft"], f"贴左未夹取: {pl['clamp_left']}"
        assert pl["clamp_right"]["clampRight"], f"贴右未夹取: {pl['clamp_right']}"
        tbl = pl["scrollCloseTable"]
        assert tbl["axis"] in ("x", "y") and tbl["closed"] is True, f"表格容器滚动未关闭浮窗: {tbl}"
        pg = pl["scrollClosePage"]
        assert (not pg["scrollable"]) or pg["closed"] is True, f"页面可滚但滚动未关闭浮窗: {pg}"
        assert pl["longChain"]["scrollable"] is True, "长链浮窗内部不可滚动"
        assert pl["longChain"]["stillOpenAfterInnerScroll"] is True, "浮窗内部滚动误关闭浮窗"
        assert pl["longChain"]["closedByOuterScroll"] is True, "长链浮窗外层滚动未关闭"

        # 3) 组行入口: drawer.hash == 搬移成员; 详情段「路径链」基准一致; Esc 逐层退栈 + 焦点回徽标
        ge = ui["groupEntry"]
        assert ge["badgeClick"]["drawerHash"] == moved, f"组行徽标 drawer.hash 非 mover: {ge['badgeClick']}"
        assert ge["badgeClick"]["chainHash"] == moved, f"组行徽标 chain.hash 非 mover: {ge['badgeClick']}"
        assert all(
            h == moved for h in ge["badgeClick"]["chainReqs"]
        ), f"组行徽标链请求 hash 非 mover: {ge['badgeClick']['chainReqs']}"
        assert ge["afterEsc1"]["chainOpen"] is False and ge["afterEsc1"]["drawerOpen"] is True, \
            f"Esc 首层未只关浮窗: {ge['afterEsc1']}"
        assert ge["afterEsc1"]["focusIsBadge"] is True, f"Esc 后焦点未回触发徽标: {ge['afterEsc1']}"
        assert ge["drawerEntryClick"]["drawerHash"] == moved and ge["drawerEntryClick"]["chainHash"] == moved, \
            f"详情段路径链基准与 drawer.hash 不一致: {ge['drawerEntryClick']}"
        assert all(h == moved for h in ge["drawerEntryClick"]["newReqs"]), \
            f"详情段路径链请求 hash 非 drawer.hash: {ge['drawerEntryClick']['newReqs']}"
        assert ge["afterEsc2"] == {"chainOpen": False, "drawerOpen": False}, f"Esc 二层未关 drawer: {ge['afterEsc2']}"
        # 3c) P1-2 详情「迁移」段真渲染: 「设置时间」必须真实出现, 且与 state 里 job.created_at 同一时刻
        dra = ui.get("drawerRelocate") or {}
        rows = {r["label"]: r["value"] for r in (dra.get("rows") or [])}
        assert "设置时间" in rows, f"详情迁移段缺「设置时间」(plan P1-2): {dra}"
        assert rows["设置时间"] != "—", f"新 job 的设置时间落空: {rows.get('设置时间')!r}"
        created = float((armed["job"] or {}).get("created_at") or 0.0)
        assert created > 0, f"state.json job 缺 created_at(设置时间无源): {armed['job']}"
        expect_time = datetime.fromtimestamp(created).strftime("%m-%d %H:%M")
        assert rows["设置时间"] == expect_time, \
            f"设置时间与 job.created_at 不一致: UI={rows['设置时间']!r} state={expect_time}({created})"
        armed_at = float((armed["job"] or {}).get("armed_at") or 0.0)
        assert created <= armed_at, f"设置时间晚于武装时间, 时间线不通: created={created} armed={armed_at}"
        ev["ui"]["drawerRelocate"] = {
            "rows": dra.get("rows"),
            "shot": dra.get("shot"),
            "expected": expect_time,
            "created_at": created,
            "armed_at": armed_at
        }
        # 3b) 组视图实际行为(plan §3.4 别名作用域重归组): armed 后源/目标**不裂组**,
        #     两个成员仍属同一组, 组行 save_path 取首位成员(此处 mover -> dst_a)
        g15_rows = [g for g in M.groups_view(web_port) if g.get("name") == "rm04c15a"]
        assert len(g15_rows) == 1, f"别名建好后同组种子裂成 {len(g15_rows)} 组(预期并组): {[r['key'] for r in g15_rows]}"
        g15 = g15_rows[0]
        assert {m["hash"] for m in g15["members"]} == {moved, other}, "并组后成员集合不符"
        assert (g15.get("relocate") or {}).get("state") == "pending_finalize", f"组级状态非待收尾: {g15.get('relocate')}"
        ev["ui"]["armedGroup"] = {
            "count": len(g15_rows),
            "memberCount": g15.get("count"),
            "name": g15.get("name"),
            "state": g15["relocate"]["state"]
        }
        ev["result"] = "PASS"
    finally:
        if p is not None:
            p.stop()
        try:
            qb.set_prefs(save_path=orig_save_path)
            time.sleep(0.3)
            ev["save_path_restored"] = qb.prefs().get("save_path") == orig_save_path
        except Exception:  # noqa: BLE001
            ev["save_path_restored"] = False
        try:
            M.rm_all_fakes(M.qbfake())
        finally:
            save_evidence(case, "rm04_15", ev)
            M.purge_tree(case)
            M.purge_tree(M.RAM / "rm04_15")


# ---------------------------------------------------------------- RM04-16


def test_rm04_16_chain_junction_unc():
    """人工 A->B->C 逐跳取证(含 symlink 尝试) + 6+ 跳长链 + UNC 不可达快速返回。"""
    case = M.case_dir("rm04_16")
    qb = M.qbfake()
    p = None
    ev = {"case": "RM04-16", "head": M._head_sha()}
    hunc = None
    try:
        assert not M.rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
        cfg, web_port = make_cfg(case, alias_threshold=1)
        p = start_product(cfg, case)
        ev["web_port"] = web_port

        # --- A -> B -> C: P2/chain2(junction) -> B(尝试 symlink) -> C(真目录)
        p2 = case / "p2"
        b_dir = p2 / "B"
        c_dir = p2 / "C"
        c_dir.mkdir(parents=True, exist_ok=True)
        # 符号链接必须在 B 尚不存在时创建(先建目录再 symlink_to 只会撞 WinError 183)
        sym_ok, sym_err = try_symlink(b_dir, c_dir)
        if not sym_ok:
            mklink_junction(b_dir, c_dir)
        mklink_junction(p2 / "chain2", b_dir)
        ev["symlink"] = {"created": sym_ok, "error": sym_err}
        files2 = [("chain2/sub/f.bin", 200_000)]
        h2 = M.fake_multi(qb, "chain2", files2, p2, "rm04c16two")
        M.wait_complete(qb, [h2], timeout=60)
        wait_in_store(web_port, h2)
        t2 = qb.torrent(h2) or {}
        assert M.norm(t2.get("root_path")) == M.norm(p2 / "chain2"), f"qB root_path 不是链首: {t2.get('root_path')}"
        chain2, ms2 = chain_get(web_port, h2)
        nodes2 = chain2["nodes"]
        assert chain2["env"] == "local", f"env={chain2['env']}"
        assert len(nodes2) == 3, f"A->B->C 节点数应为 3: {[n['path'] for n in nodes2]}"
        expect_types = ["junction", "symlink" if sym_ok else "junction", "dir"]
        assert [n["type"] for n in nodes2] == expect_types, \
            f"逐跳类型不符(期望 {expect_types}): {[n['type'] for n in nodes2]}"
        assert [n["status"] for n in nodes2] == ["ok", "ok", "ok"], f"状态非 ok: {[n['status'] for n in nodes2]}"
        assert nodes2[0]["target"] and nodes2[1]["target"], "链接跳缺 target"
        assert M.norm(nodes2[1]["target"]) == M.norm(c_dir), "第二跳目标不是 C"
        assert all(n["attribution"]["auto"] is False for n in nodes2), "人工链归属章不应为 auto-qb"
        assert ev["symlink"]["created"] or ev["symlink"]["error"], "symlink 结论必须留原因(不得空白)"
        ev["chain_two"] = {
            "types": [n["type"] for n in nodes2],
            "statuses": [n["status"] for n in nodes2],
            "targets": [n["target"] for n in nodes2],
            "ms": ms2
        }

        # --- UNC 不可达: 起点为 UNC 时不做 syscall, 快速返回 remote/未确认
        unc_name = f"unc{int(time.time())}.bin"
        raw, hunc = lib_torrent.build(unc_name, b"z" * 65536, "http://127.0.0.1:1/announce")
        unc_save = r"\\192.0.2.1\share\rm04c16"
        M._add_retry(qb, raw, unc_save, hunc)
        M.wait_until(lambda: qb.torrent(hunc) is not None, 30, f"UNC 假种子未被 qB 接纳: {unc_save}")
        wait_chain_ready(web_port, hunc)
        # 记录实际行为: UNC 保存路径的种子是否进入分组视图(链端点有 200 只说明进了 store)
        unc_in_groups = any(m.get("hash") == hunc for g in M.groups_view(web_port) for m in g.get("members") or [])
        chain_unc, ms_unc = chain_get(web_port, hunc)
        _, ms_local_ref = chain_get(web_port, h2)
        assert chain_unc["env"] == "remote", f"UNC 起点未判 remote: {json.dumps(chain_unc, ensure_ascii=False)[:400]}"
        assert len(chain_unc["nodes"]) == 1, f"remote 只应返回一个未确认节点: {len(chain_unc['nodes'])}"
        nd = chain_unc["nodes"][0]
        assert nd["type"] == "unknown" and nd["status"] == "unknown", f"UNC 节点未表现为未确认: {nd}"
        assert "远程" in (nd["reason"] or ""), f"UNC 未确认缺原因: {nd}"
        assert ms_unc < 2000, f"UNC 链端点耗时过长({ms_unc:.1f}ms, 疑做远端 syscall)"
        # 起点归一化会折叠反斜杠(path_normalize -> /server/share), 这里只钉「主机+共享名保留」
        assert "192.0.2.1" in chain_unc["start"] and "share" in chain_unc["start"], \
            f"UNC 起点丢失: {chain_unc['start']}"
        assert nd["path"] == chain_unc["start"], f"节点路径与起点不一致: {nd['path']} vs {chain_unc['start']}"
        assert ms_unc < max(200.0, ms_local_ref * 20 + 50), \
            f"UNC 与本地链路耗时不相当(unc={ms_unc:.1f}ms local={ms_local_ref:.1f}ms)"
        ev["chain_unc"] = {
            "env": chain_unc["env"],
            "node": nd,
            "ms": ms_unc,
            "local_ms": ms_local_ref,
            "start": chain_unc["start"],
            "unc_in_groups": unc_in_groups,
            "unc_prefix_preserved": chain_unc["start"].startswith("\\\\")
        }

        # --- 6+ 跳长链(与 RM04-15 同型, 这里走 API 断言)
        p3 = case / "p3"
        store = case / "store_long"
        store.mkdir(parents=True, exist_ok=True)
        names = ["chainroot"] + [f"L{i}" for i in range(1, 9)]
        targets = names[1:] + ["store"]
        for name, tgt in zip(names, targets):
            mklink_junction(p3 / name, p3 / tgt)
        hlong = M.fake_multi(qb, "chainroot", [("chainroot/sub/f.bin", 200_000)], p3, "rm04c16long")
        M.wait_complete(qb, [hlong], timeout=60)
        wait_in_store(web_port, hlong)
        chainL, msL = chain_get(web_port, hlong)
        assert chainL["env"] == "local" and len(chainL["nodes"]) >= 9, \
            f"长链不足 9 节点/env 异常: {chainL['env']} {len(chainL['nodes'])}"
        assert chainL["nodes"][-1]["status"] == "limit", f"长链末节点应为 limit: {chainL['nodes'][-1]}"
        assert all(n["status"] == "ok" for n in chainL["nodes"][:-1]), "长链中间跳状态非 ok"
        ev["chain_long"] = {"nodes": len(chainL["nodes"]), "last": chainL["nodes"][-1]["status"], "ms": msL}
        ev["result"] = "PASS"
    finally:
        if p is not None:
            p.stop()
        try:
            if hunc:
                try:  # UNC 删文件会走不可达的 SMB: 只摘记录, 避免收尾在远端超时里
                    qb.delete(hunc, delete_files=False)
                except Exception:  # noqa: BLE001
                    pass
            M.rm_all_fakes(M.qbfake())
        finally:
            save_evidence(case, "rm04_16", ev)
            M.purge_tree(case)


# ---------------------------------------------------------------- RM04-17


def tag_paths(proxy: TcpProxy, prefixes) -> list[tuple[float, str]]:
    return [(ts, path) for ts, path in proxy.requests() if any(pre in path for pre in prefixes)]


def _wait_tag(qb, h: str, tag: str, want: bool, timeout: float, desc: str) -> None:
    def ok() -> bool:
        tags = M._tags_of(qb.torrent(h) or {})
        return (tag in tags) if want else (tag not in tags)

    M.wait_until(ok, timeout, desc)


def test_rm04_17_pending_tag_lifecycle():
    """pending_tag 开启: armed 真加 -> 手删不重加 -> 重启 reconcile 补写 -> 终态真摘。"""
    case = M.case_dir("rm04_17")
    qb = M.qbfake()
    orig_save_path = qb.prefs().get("save_path")
    p = None
    proxy = None
    ev = {"case": "RM04-17", "head": M._head_sha()}
    try:
        assert orig_save_path, "副实例 save_path 读取失败"
        assert not M.rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留"
        probe_dir = case / "qbsave"
        probe_dir.mkdir(parents=True, exist_ok=True)
        qb.set_prefs(save_path=str(probe_dir))
        time.sleep(0.5)
        assert qb.prefs().get("save_path") == str(probe_dir), "save_path 临时改写未生效"

        proxy = TcpProxy(instances.SECONDARY, app.free_port())
        proxy.start()
        cfg, web_port = make_cfg(case, qb_port=proxy.port, pending_tag=PENDING_TAG, alias_threshold=1)
        p = start_product(cfg, case, qb_port=proxy.port)
        ev["web_port"] = web_port

        src = M.RAM / "rm04_17" / "src"
        dst = case / "dst"
        M.purge_tree(M.RAM / "rm04_17")
        dst.mkdir(parents=True, exist_ok=True)
        files = files_of("rm04c17")
        h1, h2 = seed_pair(qb, "rm04c17", files, src)
        M.wait_complete(qb, [h1, h2], timeout=120)
        assert M.wait_group(web_port, h1, {h1, h2}, 25, "组未成组")
        M.wait_store_progress(web_port, [h1, h2], timeout=60)

        job_id, _ = start_migration(web_port, h1, dst)
        moved = M.wait_until(
            lambda: next((h for h in (h1, h2) if M.norm((qb.torrent(h) or {}).get("save_path")) == M.norm(dst)), None),
            90, "qB 侧无成员 save_path 变 dst"
        )
        other = h2 if moved == h1 else h1
        wait_armed(case, web_port, job_id, [h1, h2])

        # 1) armed 期间标签真加上(两枚成员)
        _wait_tag(qb, h1, PENDING_TAG, True, 60, "armed 期间 h1 未加 pending_tag")
        _wait_tag(qb, h2, PENDING_TAG, True, 60, "armed 期间 h2 未加 pending_tag")
        adds = tag_paths(proxy, TAG_ADD_PATHS)
        assert adds, "qB 侧标签已加但代理未记录 addTags 请求(计数面失效)"
        ev["armed_add"] = {
            "requests": len(adds),
            "tags": {
                h[:8]: sorted(M._tags_of(qb.torrent(h) or {}))
                for h in (h1, h2)
            }
        }

        # 2) 用户手删标签: 结论不变, 且不被自动重加
        qb.remove_tags(h1, PENDING_TAG)
        qb.remove_tags(h2, PENDING_TAG)
        _wait_tag(qb, h1, PENDING_TAG, False, 15, "手删 h1 标签未生效")
        time.sleep(4.0)  # > 2 个主循环节拍, 足够触发一次 reconcile 尝试
        adds_before = len(tag_paths(proxy, TAG_ADD_PATHS))
        assert PENDING_TAG not in M._tags_of(qb.torrent(h1) or {}), "手删后标签被自动重加"
        assert PENDING_TAG not in M._tags_of(qb.torrent(h2) or {}), "手删后标签被自动重加"
        assert len(tag_paths(proxy, TAG_ADD_PATHS)) == adds_before, "手删后仍发出 addTags 请求(违反不回填)"
        rel_after_delete = member_rel(web_port, h1)
        assert rel_after_delete and rel_after_delete.get("phase") == "armed", \
            f"手删标签改变了迁移结论: {rel_after_delete}"
        ev["manual_delete"] = {
            "adds_before": adds_before,
            "adds_after": len(tag_paths(proxy, TAG_ADD_PATHS)),
            "relocate_phase": rel_after_delete.get("phase")
        }

        # 3) 重启 reconcile 补写
        p.stop()
        p = start_product(cfg, case, qb_port=proxy.port)
        adds_pre_restart = len(tag_paths(proxy, TAG_ADD_PATHS))
        _wait_tag(qb, h1, PENDING_TAG, True, 60, "重启后 h1 未补写 pending_tag")
        _wait_tag(qb, h2, PENDING_TAG, True, 60, "重启后 h2 未补写 pending_tag")
        assert len(tag_paths(proxy, TAG_ADD_PATHS)) > adds_pre_restart, "重启 reconcile 未再次发出 addTags"
        _wait_tag(qb, h1, PENDING_TAG, True, 30, "重启后标签未真正落到 qB")
        ev["restart_reconcile"] = {"adds_before": adds_pre_restart, "adds_after": len(tag_paths(proxy, TAG_ADD_PATHS))}

        # 4) 终态真摘: 撤销迁移 -> cancelled(两步同模块口径: 首投只回成本, confirm=True 才执行)
        c1 = M.cmd_post_and_wait(web_port, "/api/relocate/cancel", {"job_id": job_id})
        assert (c1.get("truth") or {}).get("cls") == "confirm", \
            f"撤销首投未回成本确认: {json.dumps(c1, ensure_ascii=False)[:500]}"
        c2 = M.cmd_post_and_wait(web_port, "/api/relocate/cancel", {"job_id": job_id, "confirm": True}, timeout=60)
        assert c2.get("status") == "ok" and (c2.get("truth") or {}).get("cls") == "ok", \
            f"撤销回执异常: {json.dumps(c2, ensure_ascii=False)[:500]}"
        M.wait_job_phase(case, job_id, {"cancelled"}, 120, "job 未到 cancelled")
        _wait_tag(qb, h1, PENDING_TAG, False, 60, "终态 h1 标签未摘")
        _wait_tag(qb, h2, PENDING_TAG, False, 60, "终态 h2 标签未摘")
        removes = tag_paths(proxy, TAG_REMOVE_PATHS)
        assert len(removes) == 1, f"armed 终态应恰发 1 次 removeTags(实际 {len(removes)}): {removes}"
        ev["terminal_remove"] = {"requests": len(removes)}
        ev["result"] = "PASS"
    finally:
        if p is not None:
            p.stop()
        if proxy is not None:
            proxy.stop()
        try:
            qb.set_prefs(save_path=orig_save_path)
            time.sleep(0.3)
            ev["save_path_restored"] = qb.prefs().get("save_path") == orig_save_path
        except Exception:  # noqa: BLE001
            ev["save_path_restored"] = False
        try:
            M.rm_all_fakes(M.qbfake())
        finally:
            save_evidence(case, "rm04_17", ev)
            M.purge_tree(case)
            M.purge_tree(M.RAM / "rm04_17")


# ---------------------------------------------------------------- RM04-18


def test_rm04_18_pending_tag_disabled_zero_write():
    """pending_tag 关闭: armed 期间不得发出任何 addTags/removeTags 写请求。"""
    case = M.case_dir("rm04_18")
    qb = M.qbfake()
    orig_save_path = qb.prefs().get("save_path")
    p = None
    proxy = None
    ev = {"case": "RM04-18", "head": M._head_sha()}
    try:
        assert orig_save_path, "副实例 save_path 读取失败"
        assert not M.rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留"
        probe_dir = case / "qbsave"
        probe_dir.mkdir(parents=True, exist_ok=True)
        qb.set_prefs(save_path=str(probe_dir))
        time.sleep(0.5)
        assert qb.prefs().get("save_path") == str(probe_dir), "save_path 临时改写未生效"

        proxy = TcpProxy(instances.SECONDARY, app.free_port())
        proxy.start()
        cfg, web_port = make_cfg(case, qb_port=proxy.port, alias_threshold=1)
        p = start_product(cfg, case, qb_port=proxy.port)
        ev["web_port"] = web_port

        src = M.RAM / "rm04_18" / "src"
        dst = case / "dst"
        M.purge_tree(M.RAM / "rm04_18")
        dst.mkdir(parents=True, exist_ok=True)
        files = files_of("rm04c18")
        h1, h2 = seed_pair(qb, "rm04c18", files, src)
        M.wait_complete(qb, [h1, h2], timeout=120)
        assert M.wait_group(web_port, h1, {h1, h2}, 25, "组未成组")
        M.wait_store_progress(web_port, [h1, h2], timeout=60)

        job_id, _ = start_migration(web_port, h1, dst)
        M.wait_until(
            lambda: any(M.norm((qb.torrent(h) or {}).get("save_path")) == M.norm(dst) for h in (h1, h2)), 90,
            "qB 侧无成员 save_path 变 dst"
        )
        wait_armed(case, web_port, job_id, [h1, h2])
        time.sleep(4.0)  # 覆盖 armed 期间若干主循环节拍
        tags_writes = tag_paths(proxy, TAG_ADD_PATHS + TAG_REMOVE_PATHS)
        assert tags_writes == [], f"pending_tag 关闭仍发出标签写请求: {tags_writes[:10]}"
        assert PENDING_TAG not in M._tags_of(qb.torrent(h1) or {}), "关闭态不应存在 pending 标签"
        ev["zero_write"] = {
            "tag_requests": len(tags_writes),
            "relocate_phase": (member_rel(web_port, h1) or {}).get("phase")
        }
        ev["result"] = "PASS"
    finally:
        if p is not None:
            p.stop()
        if proxy is not None:
            proxy.stop()
        try:
            qb.set_prefs(save_path=orig_save_path)
            time.sleep(0.3)
            ev["save_path_restored"] = qb.prefs().get("save_path") == orig_save_path
        except Exception:  # noqa: BLE001
            ev["save_path_restored"] = False
        try:
            M.rm_all_fakes(M.qbfake())
        finally:
            save_evidence(case, "rm04_18", ev)
            M.purge_tree(case)
            M.purge_tree(M.RAM / "rm04_18")


# ---------------------------------------------------------------- RM04-19


def test_rm04_19_pending_tag_unarmed_terminal_zero_remove():
    """pending_tag 开启但从未 armed 直接撤销: 终态不得发 remove(空闲清理不算「曾加」)。"""
    case = M.case_dir("rm04_19")
    qb = M.qbfake()
    orig_save_path = qb.prefs().get("save_path")
    p = None
    proxy = None
    ev = {"case": "RM04-19", "head": M._head_sha()}
    try:
        assert orig_save_path, "副实例 save_path 读取失败"
        assert not M.rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留"
        probe_dir = case / "qbsave"
        probe_dir.mkdir(parents=True, exist_ok=True)
        qb.set_prefs(save_path=str(probe_dir))
        time.sleep(0.5)
        assert qb.prefs().get("save_path") == str(probe_dir), "save_path 临时改写未生效"

        proxy = TcpProxy(instances.SECONDARY, app.free_port())
        proxy.start()
        cfg, web_port = make_cfg(case, qb_port=proxy.port, pending_tag=PENDING_TAG, alias_threshold=1)
        p = start_product(cfg, case, qb_port=proxy.port)
        ev["web_port"] = web_port

        src = M.RAM / "rm04_19" / "src"
        dst = case / "dst"
        M.purge_tree(M.RAM / "rm04_19")
        dst.mkdir(parents=True, exist_ok=True)
        files = files_of("rm04c19")
        h1, h2 = seed_pair(qb, "rm04c19", files, src)
        M.wait_complete(qb, [h1, h2], timeout=120)
        assert M.wait_group(web_port, h1, {h1, h2}, 25, "组未成组")
        M.wait_store_progress(web_port, [h1, h2], timeout=60)

        job_id, _ = start_migration(web_port, h1, dst)
        # 未武装窗口: armed 才会 add; cancel 必须在 moving/moved 窗口内落地, 否则本条不成立
        live = M.wait_until(lambda: member_rel(web_port, h1), 3, "成员 relocate 投影未出现") or {}
        assert live.get("phase") in ("moving", "watching", "moved"), \
            f"job 已越过未武装窗口(phase={live.get('phase')}), 本条不成立"
        assert not tag_paths(proxy, TAG_ADD_PATHS), "未 armed 前已发出 addTags(前置不成立)"

        c1 = M.cmd_post_and_wait(web_port, "/api/relocate/cancel", {"job_id": job_id})
        assert (c1.get("truth") or {}).get("cls") == "confirm", \
            f"撤销首投未回成本确认: {json.dumps(c1, ensure_ascii=False)[:500]}"
        c2 = M.cmd_post_and_wait(web_port, "/api/relocate/cancel", {"job_id": job_id, "confirm": True}, timeout=60)
        assert c2.get("status") == "ok" and (c2.get("truth") or {}).get("cls") == "ok", \
            f"撤销回执异常: {json.dumps(c2, ensure_ascii=False)[:500]}"
        M.wait_job_phase(case, job_id, {"cancelled"}, 120, "job 未到 cancelled")
        time.sleep(4.0)  # 覆盖终态后若干主循环节拍(旧实现会在这一时期发 remove)

        adds = tag_paths(proxy, TAG_ADD_PATHS)
        removes = tag_paths(proxy, TAG_REMOVE_PATHS)
        assert adds == [], f"未 armed 却发出 addTags: {adds[:5]}"
        assert removes == [], f"未 armed 终态仍发 removeTags(多余 qB 写): {removes[:5]}"
        assert PENDING_TAG not in M._tags_of(qb.torrent(h1) or {}), "未动过的种子不该出现 pending 标签"
        assert PENDING_TAG not in M._tags_of(qb.torrent(h2) or {}), "未动过的种子不该出现 pending 标签"
        ev["unarmed_terminal"] = {
            "live_phase": live.get("phase"),
            "add_requests": len(adds),
            "remove_requests": len(removes),
            "job_phase": (M.jobs_on_disk(case).get(job_id) or {}).get("phase")
        }
        ev["result"] = "PASS"
    finally:
        if p is not None:
            p.stop()
        if proxy is not None:
            proxy.stop()
        try:
            qb.set_prefs(save_path=orig_save_path)
            time.sleep(0.3)
            ev["save_path_restored"] = qb.prefs().get("save_path") == orig_save_path
        except Exception:  # noqa: BLE001
            ev["save_path_restored"] = False
        try:
            M.rm_all_fakes(M.qbfake())
        finally:
            save_evidence(case, "rm04_19", ev)
            M.purge_tree(case)
            M.purge_tree(M.RAM / "rm04_19")
