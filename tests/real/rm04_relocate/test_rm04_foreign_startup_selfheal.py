"""[RM04-38] 外部旧路径种子通知账启动自愈: 停机注入陈旧账 -> 启动 -> 逐键清/留 + WebUI 换代(L2)

环境2(C盘机 56589/56590)可跑: 全部落点走 case 目录(.work/rm04/rm04_38), 不依赖 R: 盘,
不起 junction/symlink, 不碰生产 state.json。复用 rm04_relocate 片的造种/清场助手与双实例守卫。

判据代码锚点(读码复核 2026-11-27): relocate_mod.py:932-942(非 dry-run 才清; 清前先记
"账已在"才换代 -> 零账不 materialize), relocate_foreign.py:970-1008(启动清孤儿账:
kind=A/mismatch 且 job 不在 jobs 或已终态 => 删; kind=B 一律留; 活跃 job 的 A 留)。
判据只认外部可观测事实: state.json 的 relocate.foreign.notified 逐键账面 + 产品 WEB
只读详情的 foreign 标注(GET /api/torrents/{hash} 的 relocate 段)。

前置: 环境2 双实例在线(没起先 commands run real.up -- --port <白名单端口>); 副实例无
      real-fake 残留; 串行锁 + 环境 fixture 生效; 5 枚无数据 real-fake 假种子落 case/noise
      (与注入 job 旧根不重合, 避免侦测面全量扫重判污染清/留结论)。
副作用: 预热起停(graceful_after 进程内 SIGTERM)生成合法 state.json; 停机态注入
      relocate.jobs 两条(终态 done + 活跃 moving)与 foreign.notified 五条; 再起一个产品
      进程(WEB 开, relocate.enabled=true); 副实例增 5 枚假种子(连数据删)。
回滚: 产品进程停止(AppProc.stop, 禁 taskkill; 预热腿走优雅 SIGTERM) + real-fake 删净 +
      case 树删净(purge_tree 不递归删穿链接)。
失败判据: 任一应清条目仍在账 / B 或活跃 A 被误清 / WebUI 仍有陈旧 foreign 行 / 产品崩溃;
      前提不成立(双实例离线、state 缺底座、种子未进快照)显式红, 不伪装 PASS。

跑法: commands run real.run -- --case RM04-38 --yes (不要裸 pytest)
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_rm04_relocate as M  # noqa: E402  (复用 RM04 片造种/清场/断言助手)

from lib import app, guard, instances  # noqa: E402

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="真机轨: 环境2(C盘机) Windows 双实例"),
]

SLICE_EV = HERE.parent / ".work" / "rm04" / "foreign"


def _guard_online() -> None:
    """开工闸: 双实例端口白名单 + connection_status 非 disconnected(假红陷阱)。"""
    for port in (instances.PRIMARY, instances.SECONDARY):
        guard.check_port(port)
        status = guard.check_online(instances.make(port))
        assert status != "disconnected", f"{port} connection_status=disconnected(假红陷阱), 拒跑"


def _relocate_box(case: Path) -> dict:
    """state.json 的 relocate 段(只读; 坏/缺按空处理)。"""
    sp = case / "data" / "state.json"
    if not sp.is_file():
        return {}
    try:
        return (json.loads(sp.read_text(encoding="utf-8")) or {}).get("relocate") or {}
    except (json.JSONDecodeError, OSError):
        return {}


def _notified(case: Path) -> dict:
    return _relocate_box(case).get("foreign", {}).get("notified") or {}


def _flush(ev: dict, tag: str) -> None:
    """证据落盘: 断言现场留 .work/gitignored; 取证失败如实带错, 不掩盖主断言。"""
    ev["ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        SLICE_EV.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        (SLICE_EV / f"{tag}_evidence_{stamp}.json"
        ).write_text(json.dumps(ev, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    except Exception as e:  # noqa: BLE001 -- 取证失败不影响主断言
        print(f"[evidence] 写盘失败: {e!r}", file=sys.stderr, flush=True)


def _job(job_id: str, hashes: list, mover: str, src: Path, dst: Path, phase: str) -> dict:
    """停机注入的 job 账条目(job_from_dict 形状; 缺字段按产品缺省, 不改产品代码)。"""
    now = time.time()
    return {
        "job_id": job_id,
        "hashes": hashes,
        "mover": mover,
        "src": src.as_posix(),
        "dst": dst.as_posix(),
        "scope": src.as_posix(),
        "alias_kind": "",
        "alias_paths": [],
        "phase": phase,
        "reason": "finalized" if phase == "done" else "",
        "created_at": now,
        "armed_at": 0.0,
        "updated_at": now,
        "resume_hashes": [],
        "resume_pending": [],
        "resume_retries": 0,
        "attempts": 0,
        "last_error": "",
        "plan": None,
        "move_issued": True,
        "tag_on": False,
        "origin": "web",
        "absent_counts": [],
    }


def test_rm04_38_foreign_startup_selfheal(secondary, workdir):
    """[RM04-38] 外部旧路径种子通知账启动自愈(停机注入 -> 启动 -> 逐键清/留 + WebUI 换代, L2)

    前置: 双实例在线 + 副实例无 real-fake 残留 + 5 枚无数据假种子落 case/noise(旧根不重合)
          + 预热起停生成 state.json 底座 + 停机态注入 2 job/5 账条目。
    副作用: 一个产品进程(WEB 开, relocate.enabled=true); 副实例 5 枚假种子(连数据删);
            state.json 的 jobs/foreign.notified 被测试侧注入并随 case 树在收尾删除。
    回滚: 产品停止(AppProc.stop, 禁 taskkill) + real-fake 删净 + case 树删净(链接不递归删穿)。
    失败判据: 任一 A/mismatch 陈旧条目仍在账 / B 或活跃 A 被误清 / WebUI 陈旧 foreign 行未消失
              / B 行未呈现或字段漂移 / 产品崩溃; 前提不成立显式红。
    """
    case = M.case_dir("rm04_38")
    ev: dict = {"case": str(case)}
    p = None
    try:
        qb = M.qbfake()
        assert not M.rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
        _guard_online()

        cfg, web_port = M.write_cfg(case, relocate=True)
        noise = case / "noise"
        old_done = case / "old_done"
        old_active = case / "old_active"
        moved_done = case / "moved_done"
        moved_active = case / "moved_active"
        noise.mkdir(parents=True, exist_ok=True)

        # 5 枚无数据假种子: hash 即账面键; 全落 noise 根(与两条注入 job 的旧根 old_* 不重合,
        # 启动首轮 foreign 全量扫对已清 hash 重判时 classify 必 None, 不会把清掉的条目补回来)。
        seeds = {
            "orphan_a": ("f38_orphan.bin", "f38orphan"),
            "terminal_a": ("f38_terminal.bin", "f38terminal"),
            "mismatch_gone": ("f38_mismatch.bin", "f38mismatch"),
            "b": ("f38_b.bin", "f38b"),
            "active_a": ("f38_active.bin", "f38active"),
        }
        hs = {k: M.fake_no_data(qb, name, 4096, noise, salt) for k, (name, salt) in seeds.items()}
        assert len(set(hs.values())) == len(hs), "假种子 infohash 撞车(账面键必须互异)"
        M.wait_until(lambda: len(qb.torrents()) >= len(hs), 30, "qB 未收录 5 枚假种子")
        ev["seeds"] = {k: v[:8] for k, v in hs.items()}

        # 预热起停: 走进程内 SIGTERM 优雅落盘, 生成合法 state.json 注入底座(RM04-06 同款)。
        p = app.start(cfg, case, graceful_after=6.0)
        rc = p.wait(90)
        assert rc == 0, f"预热起停退出码 {rc}:\n{p.log()[-600:]}"
        p = None
        sp = case / "data" / "state.json"
        assert sp.is_file(), "预热退出后 state.json 没落盘(注入底座不成立)"

        # 停机注入: 2 条 job + 5 条通知账。活跃 A 用真 job 形状(hashes/mover 取一枚在场种子,
        # move_issued=true 走 _recover 的 stalled-but-issued 分支, 600s 停滞预算内不会翻终态,
        # 避免 _foreign_cleanup_job_terminal 把应留条目误清); 终态 job 无成员, 不参与推进。
        done_id, active_id, ghost_id = "rm04c38done", "rm04c38active", "rm04c38ghost"
        now = time.time()
        data = json.loads(sp.read_text(encoding="utf-8"))
        rel = data.setdefault("relocate", {})
        jobs = rel.setdefault("jobs", {})
        jobs.clear()
        jobs[done_id] = _job(done_id, [], "", old_done, moved_done, "done")
        jobs[active_id] = _job(active_id, [hs["active_a"]], hs["active_a"], old_active, moved_active, "moving")
        notified = rel.setdefault("foreign", {}).setdefault("notified", {})
        notified.clear()
        spec = (
            ("orphan_a", "A", ghost_id, "moving"),  # job 不在 jobs -> 清
            ("terminal_a", "A", done_id, "done"),  # job 已终态 -> 清
            ("mismatch_gone", "mismatch", ghost_id, "moving"),  # 同上 -> 清
            ("b", "B", done_id, "done"),  # B 一律保留
            ("active_a", "A", active_id, "moving"),  # 活跃 job 的 A 保留
        )
        for key, kind, jid, phase in spec:
            notified[hs[key]] = {
                "root": noise.as_posix(),
                "kind": kind,
                "job_id": jid,
                "phase": phase,
                "location": moved_done.as_posix(),
                "first_seen": now,
            }
        sp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        assert set(_notified(case)) == set(hs.values()), "注入账未落盘(键集合不符)"
        ev["injected"] = {"jobs": sorted(jobs), "notified": len(notified)}

        # 再启动: 触发启动自愈(非 dry-run, enabled=true)。日志追加式, 须等新启动行。
        n_start = len(re.findall(r"整组迁移已启用", M.log_text(case)))
        p = app.start(cfg, case)
        assert p.wait_web(40), f"WEB 没起来:\n{p.log()[-800:]}"
        M.wait_until(
            lambda: len(re.findall(r"整组迁移已启用", M.log_text(case))) > n_start,
            20,
            "重启后没有新的 relocate 启动日志行(没走到启动自愈点)",
        )

        # 断言 1: state 账逐键清理/保留。5 枚种子均在快照内 => 通用"种子消失清条目"不可能
        # 代劳; 被清 hash 又不落在任何 job 旧根 => 全量扫也不会重判入账。清块只能由启动自愈产生。
        def _selfhealed():
            nt = _notified(case)
            gone = (hs["orphan_a"], hs["terminal_a"], hs["mismatch_gone"])
            return nt if all(h not in nt for h in gone) else None

        nt = M.wait_until(_selfhealed, 30, lambda: f"启动自愈未清孤儿账: {sorted(k[:8] for k in _notified(case))}")
        for key in ("orphan_a", "terminal_a", "mismatch_gone"):
            assert hs[key] not in nt, f"应清条目仍在账: {key} {hs[key][:8]}"
        for key, kind, jid in (("b", "B", done_id), ("active_a", "A", active_id)):
            entry = nt.get(hs[key])
            assert entry is not None, f"应留条目被误清: {key} {hs[key][:8]}"
            assert entry.get("kind") == kind and entry.get("job_id") == jid, \
                f"应留条目字段漂移: {key} -> {entry}"
        ev["ledger"] = {
            "cleared": 3,
            "kept": [(k, nt[hs[k]]["kind"], nt[hs[k]]["job_id"]) for k in ("b", "active_a")],
        }
        _flush(ev, "rm04_38_ledger")

        # 断言 2: WebUI 只读视图换代。B/mismatch 才投影成 foreign 行(A 由 job 标注面接管),
        # 故陈旧行三枚全为应清项; B 行须仍在且字段与账面一致。
        M.wait_until(lambda: M.member_detail(web_port, hs["b"]) is not None, 30, "产品快照未收录 B 种子")
        for key in ("orphan_a", "terminal_a", "mismatch_gone"):
            det = M.member_detail(web_port, hs[key])
            assert det is not None, f"WebUI 快照缺种子: {key} {hs[key][:8]}"
            assert det.get("relocate") is None, \
                f"WebUI 仍有陈旧 foreign 行: {key} -> {det.get('relocate')}"
        db = M.member_detail(web_port, hs["b"]) or {}
        rel_view = db.get("relocate") or {}
        assert rel_view.get("state") == "foreign", f"WebUI 未呈现 B 通知行: {rel_view}"
        assert rel_view.get("kind") == "B" and rel_view.get("job_id") == done_id, \
            f"WebUI B 行字段漂移: {rel_view}"
        assert rel_view.get("src") == noise.as_posix(), f"WebUI B 行旧根不符: {rel_view}"
        ev["web_view"] = {"stale_rows": 0, "b_row": [rel_view.get(k) for k in ("state", "kind", "job_id")]}
        assert p.alive(), "产品在启动自愈过程中崩溃"
        assert "Traceback" not in p.log(), "启动自愈路径出现未捕获异常堆栈"
        _flush(ev, "rm04_38_final")
    finally:
        errs: list[str] = []
        if p is not None:
            try:
                ev["stop_rc"] = p.stop(40)
            except Exception as e:  # noqa: BLE001 -- 收尾失败聚合重抛, 不静默
                errs.append(f"产品停止失败: {e!r}")
        try:
            ev["seeds_removed"] = M.rm_all_fakes(M.qbfake())
        except Exception as e:  # noqa: BLE001
            errs.append(f"real-fake 清理失败: {e!r}")
        try:
            M.purge_tree(case)
        except Exception as e:  # noqa: BLE001
            errs.append(f"case 清理失败: {e!r}")
        _flush(ev, "rm04_38_cleanup")
        if errs:
            raise AssertionError(f"收尾未净(Z): {'; '.join(errs)}")
