"""[RM04-26] 0420 磁盘名错位复验: 「账面完成但磁盘名错位(.!qB)」冻结态样本 → 迁移闸门拦截
(gate=qb_temp, 不 started / 零「迁移发起」/ 零副作用), 对照正常样本放行 —— 复验结论直接喂
issue 26-11-05-0420 终态裁决。

计划 plans/26-11-17-0636-plan-real-rm04-relocate-refactor-verify.html §03.4 RM04-26 用例卡
(issue 0420; 0546 机制1 源侧三态 _source_three_states 逐声明文件 stat + .!qB 孪生收集面,
深层路径天然覆盖 —— E2.1 顶层扫描漏拦面已修)。

冻结态构造(真机路径, D2 预案未触发 —— 构造可行性证据见本 docstring 开头段(D2 声明)):
issue 0420 的病灶态 = 组成员账面(下载器 files API)声明裸名、prog=1.00 做种中, 磁盘文件
物理挂 .!qB 后缀(深层路径原样, 465 文件全带后缀的生产冻结形态)。本用例按「终态等价」
直接构造该冻结态: 真种子带数据落 R: → qB 校验完成做种(账面声明裸名) → 测试侧把声明文件
逐个改名为 声明名.!qB(磁盘侧单操作, 与事故形态同一终态)。等价性论证: 闸门消费面 =
「store 声明名 x 磁盘 stat」(relocate_plan._source_three_states), 生产冻结态与本构造在该
比较面上逐点同形(声明名缺席 + 孪生名在场 + 完成态 + 做种中); 事故侧 qB 自演变通路
(rejected re-add forceAppendExt + 归位零搬移触发 recheck 改名, 见 issue 0420 §05 根因链)
依赖 qB 内部竞态时序(0.4-1.2s 窗), 用例内复演不稳定 —— 端态等价构造确定性成立, 闸门
语义断言不受构造通路影响。断言「正常样本放行」用对照组(同拓扑不改动名)同批完成。

## 测试计划(单测试函数, 两样本)
- G0 开工闸: R: 拓扑在 + 双实例在线(connection_status 非 disconnected) + 副实例无
  real-fake 残留; 产品起(relocate 开, 阈值 8)。
- A 错位样本(双成员共享单文件, file_links 形态面): A1 造组(两颗同内容异 piece_len 真种子
  落 R: 内容根, 数据齐) → A2 冻结态构造(声明文件改名为 声明名.!qB —— 深层孪生, 账面
  prog==1.0 不动、state 无 error/missing = qB 侧未察觉) → A3 迁移被闸门拦截(confirm 直投
  → 回执 status=error, results 零 started、blocked 项 gate=qb_temp 且文案含 .!qB 孪生
  相对路径 = 深层补漏面在岗, summary blocked 计数齐) → A4 零副作用(「迁移发起」计数不变
  + dst 树未创建 + qB save_path 未动 + 无 job 账落盘 + 磁盘孪生名原样)。
- B 对照样本(单成员 direct 形态, 同拓扑不改动名): B1 迁移放行(confirm 直投 → started 项
  form=direct + job_id) → B2 真搬迁落地(qB save_path 翻转 dst + 文件在 dst + done/direct
  = 闸门不误拦健康组)。
- Z 收尾: 产品优雅退出(sentinel 通路) → real-fake 删净(连数据) → case 树与 R: 子树删净。

前置: 环境1(R: 在 —— 错位组 src=R:/qbt-fake/rm04/rm04_26/src 与 dst=D: 异盘) + 双测试
      实例在线(没起先 `commands run real.up -- --port <白名单端口>`); 副实例无 real-fake
      残留; 独占约 2-3 分钟, conftest serial 锁串行保护。R: 缺席 => skip 不回退落点
      (钉死口径, 与 RM04-22/23/25 同款, 不做环境自适应)。
副作用: 副实例加 3 颗 real-fake 种子(错位组 2 颗 + 对照组 1 颗); 对照组一次 qB 真搬迁
      (R:→D:, direct 形态); 一条闸门拒回执(错位组); state 落账(对照组 job)。
回滚: real-fake 种子删净(连数据); 产品优雅退出(sentinel); case 树与 R:/qbt-fake/rm04/
      rm04_26 子树删净(purge_tree 不递归删穿链接); 双实例恢复在线。
失败判据: 错位样本 started(假成功复发 = 0420 病灶回归); 闸门拦截但 gate 非 qb_temp 或
      文案不含孪生相对路径(三态收集面漂移); 正常对照被误拦(闸门误伤); 拦截却发生
      「迁移发起」或 dst 被写入(零副作用失守); 冻结态构造不成立(账面 prog != 1.0 或
      qB 报 error/missing)。

跑法: `commands run real.run -- --case RM04-26 --yes`(不要裸 pytest)。
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_rm04_relocate as M  # noqa: E402  (复用 RM04 的造种/清场/断言助手)
import test_rm04_relocate_window as W  # noqa: E402  (qb_up 复用 real.up 同一实现面)

from lib import app, guard, instances  # noqa: E402
from auto_qb.core.modules import relocate_units as ru  # noqa: E402  (产品码: 相位/原因常量)

# 拓扑单点(钉死, 见模块 docstring; 与 RM04-20/21/22/23/25 的子树隔离)
R_ROOT = Path("R:/qbt-fake/rm04")
BASE = R_ROOT / "rm04_26"
SRC_MISMATCH = BASE / "src"  # 错位组旧根(R: 内存盘)
SRC_NORMAL = BASE / "src_normal"  # 对照组旧根
PACK_MISMATCH = "rm04c26pack"
REL_MISMATCH = f"{PACK_MISMATCH}/data/f0.bin"
PACK_NORMAL = "rm04c26npk"
FILE_SIZE = 256 * 1024
PIECE_MISMATCH = (16384, 32768)  # 错位组双成员(同内容异 infohash)
PIECE_NORMAL = 16384

# 片D 证据目录(任务口径: 逐案 evidence 落 tests-real/.work/rm04-sliceD/; 文件名带时刻后缀
# —— 遍次间不覆写, 可审计)
SLICE_EV = HERE.parent / ".work" / "rm04-sliceD"


def _flush(ev: dict, case: Path, tag: str) -> None:
    """证据落盘(gitignored .work/rm04-sliceD): 全量断言现场 + 产品日志副本, 时刻后缀防覆写。"""
    ev["ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
    SLICE_EV.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    (SLICE_EV / f"rm04_26_{tag}_evidence_{stamp}.json"
    ).write_text(json.dumps(ev, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    try:
        log = M.log_text(case)
    except Exception as e:  # noqa: BLE001 —— 取证失败如实带错, 不掩盖主断言
        log = f"<log read failed: {e!r}>"
    (SLICE_EV / f"rm04_26_{tag}_auto-qb_{stamp}.log").write_text(log, encoding="utf-8")


def _require_r_topology() -> None:
    """拓扑钉死: R: 必须在(环境1 D盘机)。缺席 = skip 不回退(模块 docstring)。"""
    try:
        BASE.mkdir(parents=True, exist_ok=True)
        probe = BASE / ".probe"
        probe.write_bytes(b"x")
        probe.unlink()
    except OSError as e:
        pytest.skip(f"R: 盘缺席/不可写, 跨盘拓扑(src R: vs dst D:)不成立 —— 本用例钉死环境1: {e}")


def _freeze_declared_files(declared_rel: str, save_path: str) -> list[str]:
    """冻结态构造: 声明文件逐个改名 声明名.!qB(磁盘侧; 深层相对路径原样)。返回改名清单。"""
    renamed = []
    src = Path(save_path) / declared_rel
    twin = Path(save_path) / (declared_rel + ".!qB")
    assert src.is_file(), f"冻结态构造前提不成立(声明文件不在盘上): {src}"
    assert not twin.exists(), f"孪生名已存在(上轮残留?): {twin}"
    os.rename(src, twin)
    renamed.append(declared_rel + ".!qB")
    return renamed


# ================================================================ RM04-26


def test_rm04_26_zero_move_disk_name_mismatch_gate():
    """[RM04-26] 磁盘名错位冻结态 → 迁移闸门拦截 + 正常对照放行(断言明细见模块 docstring)

    前置: R: 在 + 双实例在线 + 副实例无 real-fake 残留。
    副作用/回滚/失败判据: 见模块 docstring(四行契约)。
    """
    _require_r_topology()
    qb = M.qbfake()
    assert not M.rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
    for port in (instances.PRIMARY, instances.SECONDARY):
        guard.check_port(port)
        status = guard.check_online(instances.make(port))
        assert status != "disconnected", f"{port} connection_status=disconnected(假红陷阱), 拒跑"
    M.purge_tree(BASE)
    case = M.case_dir("rm04_26")
    ev: dict = {"case": str(case), "base": str(BASE)}
    p = None
    collected: set[str] = set()
    try:
        cfg, web_port = M.write_cfg(case, relocate=True, alias_threshold=8)
        p = app.start(cfg, case)
        assert p.wait_web(40), f"WEB 没起来:\n{p.log()[-800:]}"
        assert p.wait_log("整组迁移已启用", 20), "relocate 启动日志缺失"
        # ---- A1 造错位组(双成员共享单文件) + 对照组(单成员)
        hm1 = M.fake_multi(
            qb,
            PACK_MISMATCH, [(REL_MISMATCH, FILE_SIZE)],
            SRC_MISMATCH,
            "rm04c26m",
            piece_len=PIECE_MISMATCH[0],
            write=True
        )
        hm2 = M.fake_multi(
            qb,
            PACK_MISMATCH, [(REL_MISMATCH, FILE_SIZE)],
            SRC_MISMATCH,
            "rm04c26m",
            piece_len=PIECE_MISMATCH[1],
            write=False
        )
        assert hm1 != hm2, "错位组两颗 infohash 撞车(必须同文件异 infohash)"
        collected |= {hm1, hm2}
        hn = M.fake_multi(
            qb,
            PACK_NORMAL, [(f"{PACK_NORMAL}/f0.bin", FILE_SIZE)],
            SRC_NORMAL,
            "rm04c26n",
            piece_len=PIECE_NORMAL,
            write=True
        )
        collected.add(hn)
        M.wait_complete(qb, [hm1, hm2, hn], 120)
        M.wait_group(web_port, hm1, {hm1, hm2}, 30, "错位组未归组")
        M.wait_store_progress(web_port, [hm1, hm2, hn], 60)
        sp_mismatch = (qb.torrent(hm1) or {}).get("save_path") or ""
        assert M.norm(sp_mismatch) == M.norm(SRC_MISMATCH), f"错位组 save_path 异常: {sp_mismatch}"
        ev["A1_seeded"] = {"members": [hm1[:8], hm2[:8]], "normal": hn[:8], "save_path": sp_mismatch}
        _flush(ev, case, "A1")

        # ---- A2 冻结态构造: 声明文件改名 声明名.!qB(深层孪生; 账面不动)
        renamed = _freeze_declared_files(REL_MISMATCH, sp_mismatch)
        twin_path = SRC_MISMATCH / renamed[0]
        assert twin_path.is_file(), f"孪生名落盘失败: {twin_path}"
        assert not (SRC_MISMATCH / REL_MISMATCH).exists(), "声明名仍在盘上(改名未生效)"
        for h in (hm1, hm2):
            t = qb.torrent(h) or {}
            assert t.get("progress") == 1.0, f"冻结态构造后 {h[:8]} 账面 prog != 1.0: {t.get('progress')}"
            st = str(t.get("state") or "").lower()
            assert "error" not in st and "missing" not in st, f"冻结态构造被 qB 察觉({h[:8]}): {t.get('state')}"
        ev["A2_frozen"] = {"twins": renamed, "declared": REL_MISMATCH}
        _flush(ev, case, "A2")

        # ---- A3 迁移被闸门拦截(gate=qb_temp; 深层孪生相对路径进文案 = E2.1 补漏面在岗)
        dst_mismatch = case / "dst_mismatch"
        assert not dst_mismatch.exists(), "dst 叶子预存在(对照基线不成立)"
        before_issued = M.log_text(case).count("迁移发起")
        result = M.cmd_post_and_wait(
            web_port, f"/api/torrents/{hm1}/location", {
                "location": str(dst_mismatch),
                "confirm": True
            }
        )
        truth = (result or {}).get("truth") or {}
        items = truth.get("results") or []
        started = [it for it in items if it.get("cls") == "started"]
        assert not started, f"错位样本 started(假成功复发 = 0420 病灶回归): {json.dumps(items, ensure_ascii=False)[:600]}"
        blocked = [it for it in items if it.get("cls") == "blocked"]
        assert blocked, f"回执无 blocked 项(拦截面缺失): {json.dumps(result, ensure_ascii=False)[:600]}"
        gates = [r for it in blocked for r in (it.get("reasons") or []) if (r or {}).get("gate") == "qb_temp"]
        assert gates, f"拦截原因缺 gate=qb_temp(三态收集面漂移): {json.dumps(blocked, ensure_ascii=False)[:600]}"
        text = " ".join(str((r or {}).get("text") or "") for r in gates)
        assert ".!qB" in text, f"qb_temp 文案缺 .!qB 标识: {text}"
        assert renamed[0] in text, f"qb_temp 文案缺深层孪生相对路径(E2.1 补漏面失守): {text}"
        summary = truth.get("summary") or {}
        assert summary.get("blocked", 0) >= 1 and summary.get("started", 0) == 0, \
            f"summary 计数不符: {summary}"
        ev["A3_gate"] = {"status": (result or {}).get("status"), "blocked_text": text[:200], "summary": summary}
        _flush(ev, case, "A3")

        # ---- A4 零副作用: 零迁移发起 + dst 未创建 + save_path 未动 + 无 job 账 + 孪生名原样
        assert M.log_text(case).count("迁移发起") == before_issued, \
            "闸门拦截却新增「迁移发起」(零副作用失守)"
        assert not dst_mismatch.exists(), f"拦截却创建了目标叶子(目标卷被写入): {dst_mismatch}"
        assert M.norm((qb.torrent(hm1) or {}).get("save_path") or "") == M.norm(SRC_MISMATCH), \
            "拦截后 qB save_path 被改动"
        assert not M.jobs_on_disk(case), f"拦截却落了 job 账: {list(M.jobs_on_disk(case))[:3]}"
        assert twin_path.is_file() and not (SRC_MISMATCH / REL_MISMATCH).exists(), \
            "冻结态现场被迁移链扰动(孪生名原样失守)"
        ev["A4_zero_side_effect"] = {"issued_delta": 0, "dst_absent": True, "job_ledger": "empty"}
        _flush(ev, case, "A4")

        # ---- B 对照样本放行(单成员 direct; 同拓扑不改动名)
        dst_normal = case / "dst_normal"
        result_n = M.cmd_post_and_wait(
            web_port, f"/api/torrents/{hn}/location", {
                "location": str(dst_normal),
                "confirm": True
            }
        )
        item_n = M.one_started_item(result_n)
        assert item_n.get("form") == "direct", \
            f"对照样本形态非 direct: {json.dumps(item_n, ensure_ascii=False)[:400]}"
        job_n = item_n.get("job_id")
        assert job_n, f"对照样本 started 项缺 job_id: {json.dumps(item_n, ensure_ascii=False)[:400]}"
        assert M.log_text(case).count("迁移发起") == before_issued + 1, "对照组放行但「迁移发起」计数未进(锚面漂移)"

        def normal_at_dst():
            cur = qb.torrent(hn) or {}
            if M.norm(cur.get("save_path") or ""
                     ) == M.norm(dst_normal) and (dst_normal / PACK_NORMAL / "f0.bin").is_file():
                return cur["save_path"]
            return None

        M.wait_until(normal_at_dst, 90, lambda: f"对照组未真搬迁: {(qb.torrent(hn) or {}).get('save_path')}")

        def direct_done():
            rel_n = ((M.member_detail(web_port, hn) or {}).get("relocate") or {})
            if rel_n.get("job_id") == job_n and rel_n.get("phase") == ru.PHASE_DONE and rel_n.get("reason") == "direct":
                return rel_n
            return None

        rel_done = M.wait_until(
            direct_done, 90, lambda: f"对照组 job 未落 done/direct: "
            f"{((M.member_detail(web_port, hn) or {}).get('relocate') or {})}"
        )
        ev["B_normal_pass"] = {"job": job_n, "form": "direct", "dst": str(dst_normal), "final": rel_done}
        _flush(ev, case, "B")

    finally:
        # ---- Z 收尾: 产品退出 -> 删种子(连数据) -> 目录删净 -> 双实例在线
        errs: list[str] = []
        if p is not None:
            try:
                ev["stop_rc"] = p.stop(40)
            except Exception as e:  # noqa: BLE001 —— 收尾失败聚合重抛, 不静默
                errs.append(f"产品停止失败: {e!r}")
        _flush(ev, case, "Z1")
        try:
            ev["seeds_removed"] = M.rm_all_fakes(M.qbfake())
        except Exception as e:  # noqa: BLE001
            errs.append(f"real-fake 种子清理失败: {e!r}")
        try:
            M.purge_tree(BASE)  # 含孪生名文件与对照组真身
            M.purge_tree(case)
        except Exception as e:  # noqa: BLE001
            errs.append(f"目录清理失败: {e!r}")
        for port in (instances.SECONDARY, instances.PRIMARY):
            try:
                W.qb_up(port)
            except Exception as e:  # noqa: BLE001
                errs.append(f"real.up {port} 恢复失败: {e!r}")
        if errs:
            raise AssertionError(f"收尾未净(Z): {'; '.join(errs)}")
