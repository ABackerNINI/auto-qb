"""[RM04-24] 批量>20组终态分级保留 真机闭环: 21 组单成员单文件 direct 搬迁(组间异内容异名,
dst 轮换 21 个独立子目录) -> done 终态账自动滚动保留恰 20 条、更老自动删、滚出有序(最老先出);
失败账(停机注入, armed_at>0 配额已用保守保持 failed)与取消账(第 22 组发起后立即 cancel 两投)
不随成功滚出被冲掉(Q11); 被接管旧任务(同组续迁即收官的 superseded 前任)不占 20 计数、随接管
任务整链消亡(D5, 清空历史时经 purge_terminal_chain 连带); 「清空历史」无 confirm 必拒(路由层
同步回 confirm 零动作)带 confirm 后全消(连失败/取消, D3 失败/取消唯一清理入口)。

计划 plans/26-11-17-0636-plan-real-rm04-relocate-refactor-verify.html §03.4 RM04-24 用例卡
(acc3/issue 26-11-10-0326; S3 终态分级保留 1fad4fce: DONE_HISTORY_KEEP=20 非配置键 +
prune_success_history 双触发面[done 落账/_load_jobs 接管] + purge_terminal_chain 整链基元)。

形态选择: 批量 21 组全部单成员单文件(< 阈值 8) => FORM_DIRECT(qB 自搬, 免暂停面 dc337d29),
无别名无 journal 无收尾窗, 单组搬迁秒级(§03.5 批量参数照卡); 被接管面(断言 4)单独用一组
dir_alias 双成员组(阈值 1 压低)走续迁即收官(RM04-22 同款, 不进 daemon 离线窗即可 armed),
前任即时 superseded 后接管任务 cancel 落终态 —— 终态头 + superseded 前任共存至清空历史。

## 测试计划(单测试函数, 分段)
- B1 开工闸: R: 拓扑在 + 双实例在线(connection_status 非 disconnected) + 副实例无 real-fake
  残留 + 副实例 BT_backup 可定位(relocate 部署闸读它)。
- B2 骨架 + 注入失败账: 空库短起停(graceful_after 优雅退出)生成合法 state.json -> 停机注入
  1 条 failed 账(产品 RelocateJob 真实类构造, 照 RM04-23 配方; armed_at>0 = 重入配额已用,
  启动对账保守保持 failed 不翻案) -> 主启(账接管 + 接管面写穿)。
- B3 造种子: 21+1 颗单文件假种子(256KiB/piece 16384, 异名异盐) + dir_alias 组 2 颗(子目录
  布局同内容异 piece_len 异 infohash, write=False 沿用已落数据) 全部校验完成 + 产品快照
  progress 追平(迁移闸门读产品快照) + sup 组归组。
- B4 批量 1-20: 逐组发起(location confirm=true) -> 回执 started(form=direct) -> 经产品 WEB
  详情端点 relocate 标注等 done(reason=direct, 内存快照零落盘等待) -> qB save_path 落 dst_i。
- B5 被接管对: sup 组 A->dst_a 发起 -> armed(日志锚「已武装收尾」+ junction 现场同拍核) ->
  同组 B->dst_b 续迁: 首投回确认面 -> confirm 二投 started job_b -> 前任 job_a 即时 superseded
  (journal 相位 + superseded_by 接管链 + 日志「续迁即收官」) -> 撤销 job_b(两投)落 cancelled。
- B6 批量 21: 第 21 组发起 -> done 落账即滚出(内存即时), 账面 21 done -> 滚出最老 1 条。
- B7 取消样本: 第 22 组发起 -> started 后立即撤销(两投) -> cancelled。
- B8 账面分级断言(磁盘账, state 刷盘周期 30S 内等待): done 恰 20 条 = 第 2..21 组(滚出有序:
  被滚出的恰为 updated_at 最老的 job1 —— 若乱序/LIFO 本断言红); failed 注入账/取消账(g22)/
  cancelled(job_b)/superseded(job_a) 全部在场 —— 失败/取消不被成功滚出冲掉(Q11), superseded
  不占 20 计数(D5 整链口径), 全部账共 24 条。
- B9 清空历史无 confirm 必拒(L3 负向对照 1): POST /api/relocate/history/clear 无 confirm ->
  路由层同步回 {cls: confirm, note}(零 enqueue 零动作) -> 日志无「已清除」行 + 磁盘账逐字未动
  —— 若无 confirm 即生效(清空闸失守)本段红。
- B10 清空历史 confirm 全消: confirm=true -> truth {cls: ok, cleared: 24, remaining: 0} ->
  磁盘账清空(relocate.jobs 空) + 日志「清空历史: 已清除 24 条, 剩余 0 条」—— cleared=24 含
  整链前任(job_b 链上携带 job_a, 断言 4 整链消亡); 失败/取消账在此唯一入口一并清(D3)。
- B11 收尾: 产品退出 -> 双实例恢复在线 -> real-fake 删净(连数据) -> BT_backup 本用例哈希残留
  清除 + 逐文件比对开工快照 -> case 树与 R:/qbt-fake/rm04/rm04_24 子树删净。

L3 红验记录(升档面, 计划 §08 片C 一次升两条):
- 负向对照 1 = B9: 清空历史无 confirm 必拒 —— 路由层同步回执 cls=confirm 且零 enqueue,
  断言「回执 confirm + 日志无清除行 + 磁盘账未动」; 修复前/回归态(无 confirm 即清)该段必红。
- 负向对照 2 = B8: 21 done 滚出发生时 failed/cancelled/superseded 账在场且幸存 —— 若滚出
  误把非 done 账计入(Q11 失守)或滚出后失败/取消账消失, B8 逐条断言红; 若滚出不发生
  (done 恰 21 条未滚), done==20 断言红。滚出真发生由「第 21 组 done 后账面恰 20 条 + job1
  消失」正证(DONE_HISTORY_KEEP=20 是产品常量非配置键, 无法临时改小 —— 以真实滚出代替)。

前置: 环境1(R: 在, src=R:/qbt-fake/rm04/rm04_24/src 与 dst=D: 异盘; direct 搬迁不依赖同卷
      证明闸) + 双测试实例在线(没起先 `commands run real.up -- --port <白名单端口>`);
      副实例无 real-fake 残留; 独占约 6-9 分钟(21 组真搬迁 + 骨架起停 + 两轮 30S 刷盘等待),
      conftest serial 锁串行保护。R: 缺席 => skip 不回退落点(钉死口径, 与 RM04-22 同款)。
副作用: 23 次真搬迁(21 组 direct 秒级 + sup 组 dir_alias 两轮), 另 g22 发起即撤; 2 次撤销(job_b/g22);
      state 账面峰值 24 条(relocate.jobs)后清空; 副实例 24 颗 real-fake 种子; 副实例
      BT_backup 新增本用例哈希的 fastresume/torrent; junction 建立/删除(sup 组)。
回滚: real-fake 连数据删净 + BT_backup 只清本用例哈希残留 + 逐文件比对开工快照(queue 豁免);
      case 树与 R:/qbt-fake/rm04/rm04_24 删净(purge_tree 不递归删穿链接); 产品退出(外部终止,
      非优雅); 双实例恢复在线。
失败判据: done 计数 >20 未滚出或滚出乱序(幸存集 != 第 2..21 组); 失败/取消/superseded 账被
      自动清; 清空无 confirm 即生效(路由层 confirm 闸失守); 清空后残留(remaining>0 或账面
      非空); cleared 计数 != 24(整链前任未随链消亡)。

跑法: `commands run real.run -- --case RM04-24 --yes`(不要裸 pytest)。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_rm04_relocate as M  # noqa: E402  (复用 RM04 的造种/清场/断言助手)
import test_rm04_relocate_window as W  # noqa: E402  (BT_BACKUP 单点/快照比对/qb_up helper 复用)

from lib import app, guard, instances  # noqa: E402
from auto_qb.core.modules import relocate_units as ru  # noqa: E402  (产品码: job 类与序列化/相位常量)

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="本片断言含 Windows 特有语义(junction/外部终止语义)"),
]

# 拓扑单点(钉死, 见模块 docstring; 与 RM04-20/21/22/23 的子树隔离)
R_ROOT = Path("R:/qbt-fake/rm04")
SRC = R_ROOT / "rm04_24" / "src"
FILE_SIZE = 256 * 1024
PIECE = 16384  # §03.5 批量参数: 单文件 256KiB / piece_len 16384
N_BATCH = 21  # 卡面参数: 21 组成功搬迁(DONE_HISTORY_KEEP=20 -> 恰滚出 1 条)
SUP_NAME = "rm04c24sup"
SUP_REL = f"{SUP_NAME}/data/f0.bin"
SUP_PIECE_LENS = (16384, 32768)  # 同文件异 infohash 的区分面(两颗成员)
SALT_SUP = "rm04c24sup"
G22_NAME = "rm04c24g22.bin"
FAILED_JOB_ID = "rm04c24fail0inject"
FAILED_HASH = "0" * 40  # 注入账的成员 hash: qB 无此种子(armed_at>0 保守保持 failed, 不进重入判定)

# 片C 证据目录(任务口径: 逐案 evidence 落 tests-real/.work/rm04-sliceC/; 文件名带时刻后缀
# —— 遍次间不覆写, 可审计; 遍次序号在 run log 文件名与切片记账里)
SLICE_EV = HERE.parent / ".work" / "rm04-sliceC"


def _flush(ev: dict, case: Path) -> None:
    """证据落盘(gitignored .work/rm04-sliceC): 全量断言现场 + 产品日志副本, 时刻后缀防覆写。"""
    ev["ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
    SLICE_EV.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    (SLICE_EV / f"rm04_24_evidence_{stamp}.json"
    ).write_text(json.dumps(ev, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (SLICE_EV / f"rm04_24_auto-qb_{stamp}.log").write_text(M.log_text(case), encoding="utf-8")


def _require_r_topology() -> None:
    """拓扑钉死第一半: R: 必须在(环境1 D盘机)。缺席 = skip 不回退(模块 docstring)。"""
    try:
        SRC.parent.mkdir(parents=True, exist_ok=True)
        probe = SRC.parent / ".probe"
        probe.write_bytes(b"x")
        probe.unlink()
    except OSError as e:
        pytest.skip(f"R: 盘缺席/不可写, 批量搬迁拓扑(src R: vs dst D:)不成立 —— 本用例钉死环境1: {e}")


def _failed_job_dict() -> dict:
    """停机注入的 failed 账(产品 RelocateJob 真实类构造, 照 RM04-23 _plain_job 配方)。

    armed_at>0 = 本生命周期自动链配额已用(启动对账 _startup_reconcile_one 前置闸 A1):
    保守保持 failed, 不翻案不重入 —— 注入账是账面夹具, 不对应 qB 现场任何种子。"""
    return ru.job_to_dict(
        ru.RelocateJob(
            job_id=FAILED_JOB_ID,
            hashes=(FAILED_HASH, ),
            mover=FAILED_HASH,
            src=str(SRC.parent / "fail_src"),
            dst=str(M.WORK / "rm04_24" / "dst_fail"),
            scope=str(SRC.parent / "fail_src"),
            alias_kind="",
            alias_paths=(),
            phase=ru.PHASE_FAILED,
            reason="",
            created_at=time.time(),
            armed_at=time.time(),
            updated_at=time.time(),
            resume_hashes=(),
            attempts=0,
            last_error="注入夹具: 配额已用形态的失败账(批量滚出对照面)",
            plan={
                "form": "direct",
                "link_kind": "",
                "scope": str(SRC.parent / "fail_src"),
                "files": [["rm04c24fail.bin", 2048]]
            },
            move_issued=True,
            tag_on=False,
            origin="web",
        )
    )


def _inject_failed(case: Path) -> None:
    """向骨架 state.json 的 relocate.jobs 注入 failed 账(v8 新格式账: 盖 model_version 章 ——
    空骨架不带该章(迁移器只对旧格式账动手), 注入面按「已迁移新格式账」的盘上形态补齐;
    区别于 RM04-23 的旧格式整盒重写)。"""
    sp = case / "data" / "state.json"
    data = json.loads(sp.read_text(encoding="utf-8"))
    box = data.setdefault("relocate", {})
    box.setdefault("jobs", {})[FAILED_JOB_ID] = _failed_job_dict()
    box["model_version"] = ru.MODEL_VERSION
    sp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _live_relocate(web_port: int, h: str) -> dict | None:
    """成员详情端点的 relocate 标注(内存快照, 零落盘等待)"""
    det = M.member_detail(web_port, h)
    return (det or {}).get("relocate")


def _wait_direct_done(web_port: int, h: str, job_id: str, timeout: float) -> dict:
    """等该成员的迁移标注落 done/reason=direct(产品快照 LIVE, 不等 30S 刷盘)。"""
    def probe():
        rel = _live_relocate(web_port, h) or {}
        if rel.get("job_id") == job_id and rel.get("phase") == ru.PHASE_DONE and rel.get("reason") == "direct":
            return rel
        return None

    return M.wait_until(probe, timeout, lambda: f"{h[:8]} 未落 done/direct: {_live_relocate(web_port, h)}")


def _migrate_one(web_port: int, h: str, dst: Path, expect_form: str) -> str:
    """发起单组搬迁并回 started 项(断言形态), 返回 job_id。"""
    result = M.cmd_post_and_wait(web_port, f"/api/torrents/{h}/location", {"location": str(dst), "confirm": True})
    item = M.one_started_item(result)
    assert item.get("form") == expect_form, f"形态非 {expect_form}: {json.dumps(item, ensure_ascii=False)[:400]}"
    job_id = item.get("job_id")
    assert job_id, f"回执 started 项缺 job_id: {json.dumps(item, ensure_ascii=False)[:400]}"
    return job_id


# ================================================================ RM04-24


def test_rm04_24_batch_retention_terminal_grading():
    """[RM04-24] 批量>20组终态分级保留 真机闭环(B1-B11, 断言明细见模块 docstring)

    前置: R: 在 + 双实例在线 + 副实例无 real-fake 残留; 副实例 BT_backup 可定位。
    副作用/回滚/失败判据: 见模块 docstring(四行契约)。
    """
    _require_r_topology()
    case = M.case_dir("rm04_24")
    qb = M.qbfake()
    assert not M.rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
    assert W.BT_BACKUP.is_dir(), f"副实例 BT_backup 不在(env_registry EXE 派生路径失效?): {W.BT_BACKUP}"

    ev: dict = {"case": str(case), "topology": {"src": str(SRC), "batch_n": N_BATCH}}
    _flush(ev, case)
    p = None
    job_ids: dict[str, str] = {}  # name -> job_id
    sup_members: set[str] = set()
    snap_before = W.bt_backup_snapshot()
    try:
        # ---- B1 双实例在线 + connection_status 非 disconnected(§2.4 假红陷阱闸)
        for port in (instances.PRIMARY, instances.SECONDARY):
            guard.check_port(port)
            status = guard.check_online(instances.make(port))
            assert status != "disconnected", f"{port} connection_status=disconnected(假红陷阱), 拒跑"
        M.purge_tree(SRC.parent)

        # ---- B2 骨架短起停 + 注入 failed 账 + 主启
        cfg, web_port = M.write_cfg(case, relocate=True, alias_threshold=1)
        sk = app.start(cfg, case, graceful_after=6.0)
        rc = sk.wait(90)
        assert rc == 0, f"骨架优雅退出码 {rc}:\n{sk.log()[-600:]}"
        assert (case / "data" / "state.json").is_file(), "骨架退出后 state.json 没落盘"
        _inject_failed(case)
        ev["B2_injected"] = {"job_id": FAILED_JOB_ID, "phase": "failed", "armed_at_gt0": True}
        p = app.start(cfg, case)
        assert p.wait_web(40), f"WEB 没起来:\n{p.log()[-800:]}"
        assert p.wait_log("整组迁移已启用", 20), f"relocate 启动日志缺失(开关没生效?):\n{p.log()[-600:]}"
        assert p.wait_log("启动对账", 30), "启动对账行缺失(failed 注入账未被接管面消费?)"
        _flush(ev, case)

        # ---- B3 造种子: 21+1 颗单文件 + sup 组双成员
        names = [f"rm04c24g{i:02d}.bin" for i in range(1, N_BATCH + 1)] + [G22_NAME]
        hashes: dict[str, str] = {}
        for name in names:
            hashes[name] = M.fake_with_data(qb, name, FILE_SIZE, SRC, name, piece_len=PIECE, write=True)
        assert len(set(hashes.values())) == len(hashes), "infohash 撞车(异盐必须异 infohash)"
        sup1 = M.fake_multi(
            qb, SUP_NAME, [(SUP_REL, FILE_SIZE)], SRC, SALT_SUP, piece_len=SUP_PIECE_LENS[0], write=True
        )
        sup2 = M.fake_multi(
            qb, SUP_NAME, [(SUP_REL, FILE_SIZE)], SRC, SALT_SUP, piece_len=SUP_PIECE_LENS[1], write=False
        )
        assert sup1 != sup2, "sup 组两颗 infohash 撞车"
        sup_members = {sup1, sup2}
        all_hashes = list(hashes.values()) + [sup1, sup2]
        M.wait_complete(qb, all_hashes, 180)
        M.wait_group(web_port, sup1, sup_members, 30, "sup 组未归组(共享文件归组前提不成立)")
        M.wait_store_progress(web_port, all_hashes, 90)  # 迁移闸门读产品快照
        ev["B3_seeds"] = {"n": len(all_hashes), "sup": [sup1[:8], sup2[:8]]}
        _flush(ev, case)

        # ---- B4 批量 1-20: 逐组 direct 搬迁 -> done(LIVE 快照等待)
        dsts = {name: case / "dst" / name.removesuffix(".bin") for name in names}
        for i, name in enumerate(names[:20], start=1):
            h = hashes[name]
            job_id = _migrate_one(web_port, h, dsts[name], "direct")
            job_ids[name] = job_id
            _wait_direct_done(web_port, h, job_id, 60)
            M.wait_until(
                lambda h=h, d=dsts[name]: M.norm((qb.torrent(h) or {}).get("save_path") or "") == M.norm(d) or None,
                30,
                lambda h=h, n=name: f"{n} mover 未落 dst: {(qb.torrent(h) or {}).get('save_path')}"
            )
        assert len(job_ids) == 20, f"批量 1-20 job 数不符: {len(job_ids)}"
        ev["B4_batch20"] = {"jobs": len(job_ids), "last": names[19]}
        _flush(ev, case)

        # ---- B5 被接管对: sup 组 A->dst_a armed -> B->dst_b 续迁(supersede) -> 撤销 job_b
        sup_mover = sup1
        dst_a = case / "dst_sup_a"
        dst_b = case / "dst_sup_b"
        job_a = _migrate_one(web_port, sup_mover, dst_a, "dir_alias")
        job_ids[SUP_NAME + "#a"] = job_a
        assert p.wait_log("已武装收尾", 60), "sup 组 A->dst_a 未武装(日志锚缺失)"
        a_junction = SRC / SUP_NAME
        M.wait_until(
            lambda: M.reparse_kind(a_junction) == "junction" or None, 60,
            lambda: f"A junction 形态异常: {M.reparse_kind(a_junction)}"
        )
        # 续迁即收官: 首投确认面 -> confirm 二投 -> 前任即时 superseded
        first = M.cmd_post_and_wait(web_port, f"/api/torrents/{sup_mover}/location", {"location": str(dst_b)})
        fitems = ((first or {}).get("truth") or {}).get("results") or []
        assert any(it.get("cls") == "confirm" for it in fitems), \
            f"续迁首投未回确认面: {json.dumps(first, ensure_ascii=False)[:500]}"
        result2 = M.cmd_post_and_wait(
            web_port, f"/api/torrents/{sup_mover}/location", {
                "location": str(dst_b),
                "confirm": True
            }, timeout=60
        )
        item2 = M.one_started_item(result2)
        job_b = item2.get("job_id")
        assert job_b and job_b != job_a, f"续迁回执异常: {json.dumps(item2, ensure_ascii=False)[:400]}"
        job_ids[SUP_NAME + "#b"] = job_b
        sup_lines = [ln for ln in M.log_text(case).splitlines() if "续迁即收官" in ln and job_a in ln and job_b in ln]
        assert sup_lines, "日志缺「续迁即收官」行(前任未即时收官)"
        jr_a = M.wait_until(
            lambda: (M.journal_of(case, job_a) or {}).get("phase") == "superseded" and
            (M.journal_of(case, job_a) or {}).get("superseded_by") == job_b and M.journal_of(case, job_a) or None, 45,
            lambda: f"job_a journal 未翻 superseded: {M.journal_of(case, job_a)}"
        )
        ev["B5_supersede"] = {"job_a": job_a, "job_b": job_b, "journal": jr_a}
        # 撤销 job_b(两投: 无 confirm 确认面 / confirm 执行) —— 接管任务落 cancelled 终态头
        rb = M.cmd_post_and_wait(web_port, "/api/relocate/cancel", {"job_id": job_b})
        assert ((rb or {}).get("truth") or {}).get("cls") == "confirm", \
            f"撤销首投未回确认面: {json.dumps(rb, ensure_ascii=False)[:400]}"
        rb2 = M.cmd_post_and_wait(web_port, "/api/relocate/cancel", {"job_id": job_b, "confirm": True})
        it_b = (rb2 or {}).get("truth") or {}
        assert it_b.get("cls") == "ok" and it_b.get("phase") == "cancelled", \
            f"confirm 撤销未落 cancelled: {json.dumps(rb2, ensure_ascii=False)[:400]}"
        _flush(ev, case)

        # ---- B6 批量 21: 第 21 组 done -> 账面 21 done 即滚出最老 1 条(内存即时)
        name21 = names[20]
        h21 = hashes[name21]
        job21 = _migrate_one(web_port, h21, dsts[name21], "direct")
        job_ids[name21] = job21
        _wait_direct_done(web_port, h21, job21, 60)
        ev["B6_batch21"] = {"job": job21}

        # ---- B7 取消样本: 第 22 组发起后立即撤销(两投)
        h22 = hashes[G22_NAME]
        job22 = _migrate_one(web_port, h22, dsts[G22_NAME], "direct")
        job_ids[G22_NAME] = job22
        rc1 = M.cmd_post_and_wait(web_port, "/api/relocate/cancel", {"job_id": job22})
        assert ((rc1 or {}).get("truth") or {}).get("cls") == "confirm", \
            f"g22 撤销首投未回确认面: {json.dumps(rc1, ensure_ascii=False)[:400]}"
        rc2 = M.cmd_post_and_wait(web_port, "/api/relocate/cancel", {"job_id": job22, "confirm": True})
        it_22 = (rc2 or {}).get("truth") or {}
        assert it_22.get("cls") == "ok" and it_22.get("phase") == "cancelled", \
            f"g22 confirm 撤销未落 cancelled: {json.dumps(rc2, ensure_ascii=False)[:400]}"
        ev["B7_cancel22"] = {"job": job22}
        _flush(ev, case)

        # ---- B8 账面分级断言(磁盘账; state 刷盘周期 30S, 等待窗 30s+裕量)
        expect_survivors = {job_ids[n] for n in names[1:20]}  # 第 2..20 组 + 第 21 组
        expect_survivors.add(job21)

        def ledger_ready():
            ledger = M.jobs_on_disk(case)
            dones = {jid for jid, j in ledger.items() if j.get("phase") == ru.PHASE_DONE}
            if len(dones) != 20:
                return None
            if FAILED_JOB_ID not in ledger or ledger[FAILED_JOB_ID].get("phase") != ru.PHASE_FAILED:
                return None
            if job_b not in ledger or ledger[job_b].get("phase") != ru.PHASE_CANCELLED:
                return None
            if job22 not in ledger or ledger[job22].get("phase") != ru.PHASE_CANCELLED:
                return None
            if job_a not in ledger or ledger[job_a].get("phase") != ru.PHASE_SUPERSEDED:
                return None
            if dones != expect_survivors:
                return None
            return ledger

        ledger = M.wait_until(
            ledger_ready, 100, lambda: (
                f"账面未到分级保留终态: done={sum(1 for j in M.jobs_on_disk(case).values() if j.get('phase') == 'done')} "
                f"总账={len(M.jobs_on_disk(case))} job1_in={job_ids[names[0]] in M.jobs_on_disk(case)}"
            )
        )
        ev["B8_ledger"] = {
            "total": len(ledger),
            "phases": {
                jid[:14]: j.get("phase")
                for jid, j in ledger.items()
            },
            "rolled_out": job_ids[names[0]],
            "survivors_are_2_to_21": True,
        }
        _flush(ev, case)

        # ---- B9 清空历史无 confirm 必拒(L3 负向对照 1: 路由层同步 confirm, 零动作)
        log_before = M.log_text(case)
        r0 = M.cmd_post_and_wait(web_port, "/api/relocate/history/clear", {})
        assert r0.get("cls") == "confirm", f"无 confirm 清空未拒: {json.dumps(r0, ensure_ascii=False)[:400]}"
        assert str(r0.get("note") or "").strip(), "confirm 回执缺 note(现场说明缺失)"
        assert "cmd_id" not in r0, "无 confirm 清空被 enqueue(路由层零动作口径失守)"
        time.sleep(3.0)
        assert M.log_text(case).count("已清除") == log_before.count("已清除") == 0, \
            "无 confirm 清空执行了清除(负向对照红)"
        ledger_after_deny = M.jobs_on_disk(case)
        assert len(ledger_after_deny) == len(ledger), "无 confirm 清空动了账面(负向对照红)"
        ev["B9_deny"] = {"cls": r0.get("cls"), "ledger_unchanged": True}

        # ---- B10 清空历史 confirm 全消(D3: 失败/取消唯一清理入口; 整链前任随链消亡)
        r1 = M.cmd_post_and_wait(web_port, "/api/relocate/history/clear", {"confirm": True})
        truth = (r1 or {}).get("truth") or {}
        assert truth.get("cls") == "ok", f"confirm 清空未落 ok: {json.dumps(r1, ensure_ascii=False)[:500]}"
        assert truth.get("cleared") == 24, \
            f"cleared 计数不符(整链前任须随链消亡): cleared={truth.get('cleared')} remaining={truth.get('remaining')}"
        assert truth.get("remaining") == 0, f"清空后仍有残留账: {truth.get('remaining')}"
        assert p.wait_log("清空历史: 已清除 24 条, 剩余 0 条", 30), "日志缺清空汇总行"

        def ledger_empty():
            # 注意: 空 dict 是 falsy, 探针必须回 True/None(wait_until 按真值判), 不能回账面本体
            return True if M.jobs_on_disk(case) == {} else None

        M.wait_until(ledger_empty, 100, lambda: f"磁盘账未清空: {len(M.jobs_on_disk(case))} 条")
        ev["B10_cleared"] = {"cleared": truth.get("cleared"), "remaining": truth.get("remaining"), "disk_empty": True}

    finally:
        # ---- B11 收尾: 产品退出 -> 实例恢复 -> 删种子(连数据) -> BT_backup 核净 -> 目录删净
        ev["B11_cleanup"] = {}
        errs: list[str] = []
        if p is not None:
            try:
                ev["B11_cleanup"]["product_stop_rc"] = p.stop(40)
            except Exception as e:  # noqa: BLE001 —— 收尾失败聚合重抛, 不静默
                errs.append(f"产品停止失败: {e!r}")
        _flush(ev, case)
        for port in (instances.SECONDARY, instances.PRIMARY):
            try:
                W.qb_up(port)  # 环境还原: 双实例回在线(片C 开工前提)
            except Exception as e:  # noqa: BLE001
                errs.append(f"real.up {port} 恢复失败: {e!r}")
        try:
            ev["B11_cleanup"]["seeds_removed"] = M.rm_all_fakes(M.qbfake())
        except Exception as e:  # noqa: BLE001
            errs.append(f"real-fake 种子清理失败: {e!r}")
        try:
            removed = []
            # 本用例全部自造 hash: 批量 21+1 + sup 组 2(局部收集, 早退时有多少清多少)
            collected = set((hashes or {}).values()) | set(sup_members or set())
            for ih in collected:
                for suffix in (".fastresume", ".torrent", ".fastresume.bak", ".torrent.bak"):
                    fp = W.BT_BACKUP / f"{ih}{suffix}"
                    if fp.is_file():
                        fp.unlink()
                        removed.append(fp.name)
            now = W.bt_backup_snapshot()
            residue = [k for k in now if k not in snap_before and not any(k.startswith(ih) for ih in collected)]
            before_files = {k: v for k, v in snap_before.items() if (W.BT_BACKUP / k).is_file() and k != "queue"}
            changed = [k for k, v in before_files.items() if now.get(k) != v]
            ev["B11_cleanup"].update({"bt_backup_removed": len(removed), "residue": residue, "changed": changed})
            if residue:
                errs.append(f"BT_backup 出现非本用例的未知残留: {residue}")
            if changed:
                errs.append(f"开工前已有 BT_backup 逐种子文件被改动: {changed}")
        except Exception as e:  # noqa: BLE001
            errs.append(f"BT_backup 核净失败: {e!r}")
        _flush(ev, case)
        try:
            M.purge_tree(SRC.parent)  # 只删本用例子树(purge_tree 不递归删穿 junction)
            M.purge_tree(case)
        except Exception as e:  # noqa: BLE001
            errs.append(f"目录清理失败: {e!r}")
        if errs:
            raise AssertionError(f"收尾未净(B11): {'; '.join(errs)}")
