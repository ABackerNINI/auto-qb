"""[RM04-25] 删链门候选面三腿真机闭环: 1) 0535 祖先方向(组外种子 save_path 为旧根严格祖先且内容根
恰覆盖旧根, 跨种共享同一物理文件)-> 收尾删链门依赖计数命中(REASON_CHAIN_DEPS, 日志「删链门依赖
未清(1 个)」)+ 别名正确保留 + 依赖种子经别名持续可读 —— 修复前该形态前缀/等值两头都不命中,
依赖误清零导致收尾删别名断粮(0535); 2) 0711 direct 分流: 单成员 direct 形态收尾窗注入依赖(组外
种子落旧根等值面 + 组外种子落旧根前缀面且与成员共享同一物理文件)-> 不被顶进删链门(无别名即无链
可删, 自有面短路 0711b)、迁移正常 done(reason=direct)、添加预检零 confirm; 3) E3 同名依赖账:
file_links 组 armed 态对别名位添加同名同内容跨种种子 -> 添加预检 confirm(场景 2 文案「与成员别名
链接同名/经链接共享同一份物理数据」)-> 确认添加后其文件清单与链接相交 -> 删链门计依赖(别名保留)
-> 删除该种子账面 -> 依赖清零 -> 收尾恢复 done(REASON_FINALIZED + 链接删除)。

计划 plans/26-11-17-0636-plan-real-rm04-relocate-refactor-verify.html §03.4 RM04-25 用例卡
(acc4/issue 26-11-13-0535 + 26-11-13-0711 + E3 并腿; S4 删链门候选面修复 0df84475:
chain_gate_hits 三格候选[scope 前缀 + src 等值 + 0535 祖先格] + direct 自有面短路 + R2 文件级
交集精判; evaluate_add direct 退 confirm 换告知注记[0711 修法 a/b])。

到达删链门的确定性通路(RM04-30/E5 卡口径, 零旁路零授权面): 收尾窗内逐个删光成员种子(仅删种子)
-> R4 连续 3 拍权威缺席收缩(ru.ABSENCE_SHRINK_ROUNDS=3, 增量轮删除上报为证) -> 空集核验顺
VERIFY -> _step_verify 删链门依赖扫描 —— dir_alias/file_links 形态无需 daemon 离线窗即可把
收尾推进到删链门(依赖 >0 悬挂 = 断言窗; 依赖清零 = 在线删别名 + done)。

## 测试计划(单测试函数, 三腿各独立产品会话/case 目录)
- G0 开工闸(共腿): R: 拓扑在 + 双实例在线(connection_status 非 disconnected) + 副实例无
  real-fake 残留。
- A 腿(0535 祖先方向, dir_alias 阈值 1): A1 造组(双成员子目录布局共享文件) -> A2 搬迁
  armed(日志锚「已武装收尾」+ junction 现场) -> A2.5 armed 后加祖先跨种种子 X1(save_path=
  旧根父目录, 种子名=旧根尾段, 内部文件=成员物理文件, 实字节算 pieces; 首跑实证 X1 先加时
  其物理文件在搬迁被移走的文件夹里, 迁移发起拍 qB 侧把它带走 —— 故移到 armed 后加) ->
  A3 删光成员 -> 收缩 3 拍 -> 删链门依赖命中(日志「删链门依赖未清(1 个)」+ 磁盘账
  reason=chain_deps)+ junction 保留 + X1 经 junction 可读(sha1 与 dst 物理文件一致) ->
  A4 删 X1 账面 -> 依赖清零收尾(日志「收尾完成...删链门依赖清零」+ junction 删除 + 磁盘账
  done/finalized)。三腿配置 main_tick 1S(sync_interval 1.5S 不变): R4 收缩的缺席判定一拍
  一判且只读**当前轮** last_removed(零变化轮即清空), 2S 拍会错过 1.5S 存活期的删除轮
  (首跑实锤: 06:15:52.930 删除、120s 无收缩行)—— 1S 拍 < 轮存活期 = 每轮必被判定, 收缩
  确定性发生。
- B 腿(0711 direct 分流): B1 造单成员组 M2 + 组外种子 X2a(恰等旧根等值面) + 组外种子 X2b
  (落旧根前缀面且与成员共享同一物理文件, 跨种异 piece_len) -> B2 direct 搬迁 -> done
  (reason=direct, LIVE 快照等待) -> B3 断言全程零「删链门依赖未清」/零 chain_deps + X2a 健康
  (等值面落点不构成 direct 依赖)+ X2b 账面落点不动(共享文件随搬迁断粮属预期副作用, 如实记账)
  + B2.5 添加预检探针 cls=ok 零 confirm(0711 修法 a 告知面记录)。
- C 腿(E3 同名依赖账, file_links 阈值 8): C1 造组(双成员子目录单文件) -> C2 搬迁 armed
  (文件级 symlink 现场) -> C3 添加预检(POST /api/relocate/precheck-add, 落点=别名链接同名位)
  -> cls=confirm + gate=finalize_window + 场景 2 文案两关键词 + requested_path=落点位(actual_path 系目录级展示键场景 2 恒 None, 不断言) -> C4
  确认后真加同名跨种种子 X3(内容=成员文件, 经链接共享同一份物理数据) -> C5 删光成员 -> 收缩
  -> 删链门计依赖(文件清单 x 链接相交; 日志 + 磁盘账 chain_deps)+ symlink 保留 + X3 经链接
  可读 -> C6 删 X3 账面 -> 依赖清零收尾 done/finalized + 链接删除 + X3 已删零残留。
- Z 收尾(共腿): 产品退出 -> 双实例恢复在线 -> real-fake 删净(连数据) -> BT_backup 本用例哈希
  残留清除 + 逐文件比对开工快照 -> 三腿 case 树与 R:/qbt-fake/rm04/rm04_25 子树删净 + 别名
  lstat 复核零残留。

L3 红验记录(新建即 L3, 计划 §08 片C; 负向对照内建):
- B 腿真机钉扎面(声明收窄, 评审 R19 major): direct 单成员在线通路 stage=link 即 _finish_direct
  收口(relocate_exec.py:287-290), 不进 armed/rewritten、到不了删链门 —— 故 B 腿真机面钉的是
  **direct 通路整体行为**(done/reason=direct 落地 + 组外种子落点不被动 + 预检零 confirm),
  对「direct 被重新拉回 armed 链」的通路级复合回归红; 0711b 短路谓词与修法 a 的 armed 相位
  分流由单测钉扎(tests/test_relocate_exec_verify.py direct 短路/无别名收尾断言 + tests/test_relocate_units.py 分流表 (10) 行), 不在本腿
  真机负向对照力范围内 —— 与 A 腿构成同位对照: 同为「组外种子落在旧根作用域」, 目录级计
  依赖(A)而 direct 不计(B), 形态感知分流的双向证词(通路级)。
- C 腿负向对照 1 = C3: 同名添加必须回 confirm(场景 2 文案)—— 若同名添加零 confirm 直通
  (误放行), C3 断言红; 负向对照 2 = C5: 确认添加后必须计依赖 —— 若交集精判漏计同名跨种
  (R2 失守), 收尾会删链接断粮, C5 的「链接保留 + X3 可读」断言红。
- A 腿红验方式(修复前形态, 历史红): 0535 修复前祖先形态两头都不命中 -> 依赖误清零 -> 收尾
  删别名 -> X1 断粮(A3 的「junction 保留 + X1 经 junction 可读」必红)。修复面无法在真机
  临时拆掉(产品码零改动红线), 该红验以单测 test_chain_gate_deps_ancestor_savepath_grid
  的 红->绿 记录 + 本用例 A3 正向断言联合钉扎(单测证谓词, 真机证端到端行为)。

前置: 环境1(R: 在, 三腿 src=R:/qbt-fake/rm04/rm04_25/{a,b,c}/src 与 dst=D: 异盘) + 双测试
      实例在线(没起先 `commands run real.up -- --port <白名单端口>`); 副实例无 real-fake 残留;
      独占约 8-12 分钟(三腿各一次产品会话 + 两轮收缩等待), conftest serial 锁串行保护。
      R: 缺席 => skip 不回退落点(钉死口径, 与 RM04-22 同款, 不做环境自适应)。
副作用: 三次真搬迁(A/C 腿别名形态 + B 腿 direct)+ 组外种子 4 颗 + 同名依赖种子 1 添加/删除;
      junction/symlink 建立与删除; state 账面(三条 job); 副实例 9 颗 real-fake 种子; 副实例
      BT_backup 新增本用例哈希的 fastresume/torrent。
回滚: real-fake 连数据删净 + BT_backup 只清本用例哈希残留 + 逐文件比对开工快照(queue 豁免);
      case 树与 R:/qbt-fake/rm04/rm04_25 删净(purge_tree 不递归删穿链接)+ 别名 lstat 零残留;
      产品退出(外部终止, 非优雅); 双实例恢复在线。
失败判据: A 腿祖先依赖计数为 0/依赖种子断粮(误清零复发)或收尾卡死不清零; B 腿 direct 被顶进
      删链门(悬挂 chain_deps)或误删/误动 X2a/X2b 或迁移未 done; C 腿同名添加零 confirm 直通
      (误放行)或确认后不计依赖(链接被误删)或删依赖种子后收尾仍卡(依赖账不清零); 任一腿收尾
      有残留。

跑法: `commands run real.run -- --case RM04-25 --yes`(不要裸 pytest)。
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_rm04_relocate as M  # noqa: E402  (复用 RM04 的造种/清场/断言助手)
import test_rm04_relocate_window as W  # noqa: E402  (BT_BACKUP 单点/快照比对/qb_up helper 复用)

from lib import app, guard, instances  # noqa: E402
from lib.bencode import encode  # noqa: E402  (跨种同名种子手工构造: 实字节算 pieces)
from auto_qb.core.modules import relocate_units as ru  # noqa: E402  (产品码: 相位/原因常量)

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="本片断言含 Windows 特有语义(junction/symlink)"),
]

# 拓扑单点(钉死, 见模块 docstring; 三腿子树隔离)
R_ROOT = Path("R:/qbt-fake/rm04")
BASE = R_ROOT / "rm04_25"
SRC_A = BASE / "a" / "src"
SRC_B = BASE / "b" / "src"
SRC_C = BASE / "c" / "src"
FILE_SIZE = 256 * 1024
PIECE_A = (16384, 32768)  # A 腿双成员
PIECE_X1 = 65536  # 祖先跨种种子(第三颗异 infohash)
PACK_A = "rm04c25apack"
REL_A = f"{PACK_A}/data/f0.bin"
PACK_B = "rm04c25bpack"
PACK_C = "rm04c25cpack"
REL_C = f"{PACK_C}/f.bin"
PIECE_C = (16384, 32768)
PIECE_X3 = 65536
NAME_X2A = "x2a.bin"

# 片C 证据目录(任务口径: 逐案 evidence 落 tests-real/.work/rm04-sliceC/; 文件名带时刻后缀
# —— 遍次间不覆写, 可审计)
SLICE_EV = HERE.parent / ".work" / "rm04-sliceC"


def _flush(ev: dict, case: Path, leg: str) -> None:
    """证据落盘(gitignored .work/rm04-sliceC): 全量断言现场 + 产品日志副本, 时刻后缀防覆写。"""
    ev["ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
    SLICE_EV.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    (SLICE_EV / f"rm04_25_{leg}_evidence_{stamp}.json"
    ).write_text(json.dumps(ev, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (SLICE_EV / f"rm04_25_{leg}_auto-qb_{stamp}.log").write_text(M.log_text(case), encoding="utf-8")


def _require_r_topology() -> None:
    """拓扑钉死第一半: R: 必须在(环境1 D盘机)。缺席 = skip 不回退(模块 docstring)。"""
    try:
        BASE.mkdir(parents=True, exist_ok=True)
        probe = BASE / ".probe"
        probe.write_bytes(b"x")
        probe.unlink()
    except OSError as e:
        pytest.skip(f"R: 盘缺席/不可写, 三腿拓扑(src R: vs dst D:)不成立 —— 本用例钉死环境1: {e}")


def _readlink_norm(p: Path) -> str:
    """junction/symlink 目标原始读出(归一成 / 形 + 剥设备前缀; RM04-22 同款)。"""
    s = M.norm(os.readlink(str(p)))
    if s.startswith("//?/UNC/"):
        return "//" + s[len("//?/UNC/"):]
    if s.startswith("//?/"):
        return s[len("//?/"):]
    return s


def _sha1_file(p: Path) -> str:
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _cross_torrent(physical: Path, tname: str, inner_rel: str, piece_len: int) -> tuple[bytes, str]:
    """跨种同名种子手工构造(祖先形态 X1 专用): 种子名 tname(内容根 = save_path + tname),
    内部文件 inner_rel, pieces 从物理文件**实字节**计算(与成员同内容异 piece_len 异 infohash)。

    fake_multi(write=False) 的 blob 由 (salt, rel) 派生 —— X1 的 rel 带旧根尾段前缀, 与成员
    的 (salt, rel) 不可能同时成立, 故必须从盘上实字节反算 pieces(与 lib/torrent.build_from_path
    同语义, 多文件形手工版)。"""
    blob = physical.read_bytes()
    pieces = b"".join(hashlib.sha1(bytes(blob[i:i + piece_len])).digest() for i in range(0, len(blob), piece_len))
    info = {
        "name": tname,
        "piece length": piece_len,
        "pieces": pieces,
        "private": 1,
        "files": [{
            "path": inner_rel.split("/"),
            "length": len(blob)
        }],
    }
    ih = hashlib.sha1(encode(info)).hexdigest()
    raw = encode({"info": info, "comment": "auto-qb real-machine test (fake seed)", "announce": M.ANNOUNCE})
    return raw, ih


def _migrate(web_port: int, h: str, dst: Path, expect_form: str) -> str:
    """发起搬迁(confirm=true 直投)并回 started 项, 返回 job_id。"""
    result = M.cmd_post_and_wait(web_port, f"/api/torrents/{h}/location", {"location": str(dst), "confirm": True})
    item = M.one_started_item(result)
    assert item.get("form") == expect_form, f"形态非 {expect_form}: {json.dumps(item, ensure_ascii=False)[:400]}"
    job_id = item.get("job_id")
    assert job_id, f"回执 started 项缺 job_id: {json.dumps(item, ensure_ascii=False)[:400]}"
    return job_id


def _live_relocate(web_port: int, h: str) -> dict | None:
    det = M.member_detail(web_port, h)
    return (det or {}).get("relocate")


def _wait_direct_done(web_port: int, h: str, job_id: str, timeout: float) -> dict:
    def probe():
        rel = _live_relocate(web_port, h) or {}
        if rel.get("job_id") == job_id and rel.get("phase") == ru.PHASE_DONE and rel.get("reason") == "direct":
            return rel
        return None

    return M.wait_until(probe, timeout, lambda: f"{h[:8]} 未落 done/direct: {_live_relocate(web_port, h)}")


def _write_cfg_fast_tick(case: Path, *, alias_threshold: int) -> tuple[Path, int]:
    """RM04-25 专用配置: 在 M.write_cfg 基础上把 main_tick 2S -> 1S。

    为什么(首跑实测踩中): R4 成员收缩的缺席判定一拍一判(rt["absence_round"] = 判定时的
    store.rounds_applied), 取数面 = **当前轮**的 last_removed 快照 —— 零变化轮会把上一轮
    的删除清单清空(relocate 执行侧 docstring「删于两判定拍之间被覆盖的多轮里, 该成员永不
    进入确认」)。main_tick 2S vs sync_interval 1.5S 时, 删除轮(存活 1.5S)有概率被主循环
    判定拍整个错过 -> 证据永久丢失 -> 静默缺席永不计数 -> 收缩不发生 -> 删链门永远到不了。
    main_tick 1S < sync_interval 1.5S: 每一轮至少被一个判定拍覆盖(轮存活 1.5S > 拍间隔
    1S), 删除证据确定性进判定 —— 首跑 06:15:52.930 删除、120s 无收缩行即此竞态实锤。"""
    cfg, web_port = M.write_cfg(case, relocate=True, alias_threshold=alias_threshold)
    text = cfg.read_text(encoding="utf-8")
    assert "main_tick: 2S" in text
    cfg.write_text(text.replace("main_tick: 2S", "main_tick: 1S"), encoding="utf-8")
    return cfg, web_port


def _leg_cleanup(p, case: Path, subtree: Path, ev: dict, collected: set, snap_before: dict) -> list[str]:
    """单腿收尾(聚合失败不吞): 产品退出 -> 删种子(连数据) -> BT_backup 清本用例哈希 -> 目录删净。"""
    errs: list[str] = []
    if p is not None:
        try:
            ev["stop_rc"] = p.stop(40)
        except Exception as e:  # noqa: BLE001
            errs.append(f"产品停止失败: {e!r}")
    _flush(ev, case, ev.get("leg", "leg"))
    try:
        ev["seeds_removed"] = M.rm_all_fakes(M.qbfake())
    except Exception as e:  # noqa: BLE001
        errs.append(f"real-fake 种子清理失败: {e!r}")
    try:
        removed = []
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
        ev["bt_backup"] = {"removed": len(removed), "residue": residue, "changed": changed}
        if residue:
            errs.append(f"BT_backup 出现非本用例的未知残留: {residue}")
        if changed:
            errs.append(f"开工前已有 BT_backup 逐种子文件被改动: {changed}")
    except Exception as e:  # noqa: BLE001
        errs.append(f"BT_backup 核净失败: {e!r}")
    try:
        M.purge_tree(subtree)
        M.purge_tree(case)
    except Exception as e:  # noqa: BLE001
        errs.append(f"目录清理失败: {e!r}")
    return errs


# ================================================================ RM04-25


def test_rm04_25_chain_gate_candidates_three_legs():
    """[RM04-25] 删链门候选面三腿真机闭环(A=0535 祖先 / B=0711 direct 分流 / C=E3 同名依赖账)

    前置: R: 在 + 双实例在线 + 副实例无 real-fake 残留; 副实例 BT_backup 可定位。
    副作用/回滚/失败判据: 见模块 docstring(四行契约)。
    """
    _require_r_topology()
    qb = M.qbfake()
    assert not M.rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
    assert W.BT_BACKUP.is_dir(), f"副实例 BT_backup 不在(env_registry EXE 派生路径失效?): {W.BT_BACKUP}"
    for port in (instances.PRIMARY, instances.SECONDARY):
        guard.check_port(port)
        status = guard.check_online(instances.make(port))
        assert status != "disconnected", f"{port} connection_status=disconnected(假红陷阱), 拒跑"
    M.purge_tree(BASE)
    snap_before = W.bt_backup_snapshot()
    all_my_hashes: set[str] = set()
    agg_errs: list[str] = []

    # ============================================================
    # A 腿(0535 祖先方向): dir_alias 阈值 1 + 祖先跨种种子 -> 删链门依赖命中 + 别名保留
    # ============================================================
    ev: dict = {"leg": "A_0535_ancestor"}
    p = None
    collected: set[str] = set()
    case = M.case_dir("rm04_25a")
    try:
        cfg, web_port = _write_cfg_fast_tick(case, alias_threshold=1)
        p = app.start(cfg, case)
        assert p.wait_web(40), f"WEB 没起来:\n{p.log()[-800:]}"
        assert p.wait_log("整组迁移已启用", 20), "relocate 启动日志缺失"
        # A1 造组(祖先跨种种子 X1 在 A2.5 armed 后再加 —— 首跑实证: X1 先加时其物理文件
        # 在成员搬迁被 qB 移走的文件夹里, 迁移发起拍 qB 侧「删除种子 1 个」把它带走了)
        h1 = M.fake_multi(qb, PACK_A, [(REL_A, FILE_SIZE)], SRC_A, "rm04c25a", piece_len=PIECE_A[0], write=True)
        h2 = M.fake_multi(qb, PACK_A, [(REL_A, FILE_SIZE)], SRC_A, "rm04c25a", piece_len=PIECE_A[1], write=False)
        assert h1 != h2, "A 腿两颗 infohash 撞车"
        collected |= {h1, h2}
        all_my_hashes |= collected
        M.wait_complete(qb, [h1, h2], 120)
        M.wait_group(web_port, h1, {h1, h2}, 30, "A 腿未归组")
        M.wait_store_progress(web_port, [h1, h2], 60)
        ev["A1"] = {"members": [h1[:8], h2[:8]]}
        _flush(ev, case, "A_0535_ancestor")

        # A2 搬迁 armed(junction 现场)
        dst_a = case / "dst_a"
        job_a = _migrate(web_port, h1, dst_a, "dir_alias")
        assert p.wait_log("已武装收尾", 60), "A 腿未武装(日志锚缺失)"
        a_junction = SRC_A / PACK_A
        M.wait_until(
            lambda: M.reparse_kind(a_junction) == "junction" or None, 60,
            lambda: f"A junction 形态异常: {M.reparse_kind(a_junction)}"
        )
        assert _readlink_norm(a_junction).startswith(M.norm(dst_a)), "A junction 未指 dst_a"
        ev["A2_armed"] = {"job": job_a, "junction": str(a_junction)}
        _flush(ev, case, "A_0535_ancestor")

        # A2.5 armed 后加祖先跨种种子 X1(内容根恰覆盖旧根 = 修复面唯一可判格; 经 junction
        # 读 dst 数据校验)。save_path = 旧根父目录 —— 前缀/等值两格都不命中, 命中即证明
        # 0535 祖先格。添加预检对祖先位零 confirm(不在收尾窗判据面), 属预期。
        raw_x1, ih_x1 = _cross_torrent(dst_a / REL_A, SRC_A.name, REL_A, PIECE_X1)
        M._add_retry(qb, raw_x1, str(SRC_A.parent), ih_x1)
        collected.add(ih_x1)
        all_my_hashes.add(ih_x1)
        M.wait_complete(qb, [ih_x1], 120)  # 实字节 pieces -> 与成员文件逐字一致, 校验必过
        t = qb.torrent(ih_x1) or {}
        assert M.norm(t.get("save_path") or "") == M.norm(SRC_A.parent), \
            f"X1 save_path 不是旧根父目录(祖先形态前提): {t.get('save_path')}"
        ev["A2.5_x1"] = {"x1": ih_x1[:8], "x1_save_path": t.get("save_path"), "state": t.get("state")}
        _flush(ev, case, "A_0535_ancestor")

        # A3 删光成员 -> 收缩 -> 删链门依赖命中(祖先格) + 别名保留 + X1 可读
        anchor0 = M.log_text(case).count("删链门依赖未清")
        qb.delete(h1, delete_files=False)
        qb.delete(h2, delete_files=False)
        M.wait_until(
            lambda: True
            if M.log_text(case).count("删链门依赖未清") > anchor0 else None, 120, "删链门依赖未清行未出现(祖先格未命中 = 0535 误清零复发)"
        )
        dep_line = [ln for ln in M.log_text(case).splitlines() if "删链门依赖未清" in ln][-1]
        assert "(1 个)" in dep_line, f"依赖计数非 1(祖先格命中面漂移): {dep_line}"
        # 别名保留 + 依赖种子经别名持续可读(修复前误清零 -> 别名被删 -> X1 断粮, 本段必红)
        assert M.reparse_kind(a_junction) == "junction", f"删链门悬挂期别名被删(误清零复发): {a_junction}"
        assert _readlink_norm(a_junction).startswith(M.norm(dst_a)), "悬挂期 junction 指向被改"
        sha_dst = _sha1_file(dst_a / REL_A)
        assert _sha1_file(a_junction / "data" / "f0.bin") == sha_dst, "X1 经 junction 读不到 dst 数据(断粮)"

        def chain_deps_on_disk():
            job = M.jobs_on_disk(case).get(job_a) or {}
            return job if job.get("reason") == ru.REASON_CHAIN_DEPS else None

        M.wait_until(
            chain_deps_on_disk, 100,
            lambda: f"磁盘账未落 chain_deps: {(M.jobs_on_disk(case).get(job_a) or {}).get('reason')}"
        )
        ev["A3_gate"] = {"job": job_a, "reason": ru.REASON_CHAIN_DEPS, "log": dep_line, "alias_kept": True}
        _flush(ev, case, "A_0535_ancestor")

        # A4 删 X1 账面 -> 依赖清零收尾 done + 别名删除
        qb.delete(ih_x1, delete_files=False)
        M.wait_until(lambda: True if "收尾完成" in M.log_text(case) else None, 120, "收尾完成行未出现(依赖清零后收尾未恢复)")
        fin_line = [ln for ln in M.log_text(case).splitlines() if "收尾完成" in ln][-1]
        assert "删链门依赖清零" in fin_line and "已在线删除别名" in fin_line, f"收尾行语义不符: {fin_line}"
        M.wait_until(lambda: True if not os.path.lexists(str(a_junction)) else None, 60, "收尾后 junction 未删除")

        def done_on_disk():
            job = M.jobs_on_disk(case).get(job_a) or {}
            return job if job.get("phase") == ru.PHASE_DONE and job.get("reason") == ru.REASON_FINALIZED else None

        M.wait_until(done_on_disk, 100, lambda: f"磁盘账未落 done/finalized: {M.jobs_on_disk(case).get(job_a)}")
        ev["A4_finalized"] = {"job": job_a, "log": fin_line, "alias_removed": True}
        _flush(ev, case, "A_0535_ancestor")
    except Exception as leg_err:  # noqa: BLE001 —— 单腿失败留证后聚合, 继续跑后续腿(FAIL 二分留现场)
        ev["leg_error"] = repr(leg_err)
        agg_errs.append(f"A 腿(0535): {leg_err!r}")
    finally:
        agg_errs.extend(_leg_cleanup(p, case, SRC_A.parent, ev, collected, snap_before))
        all_my_hashes |= collected

    # ============================================================
    # B 腿(0711 direct 分流): 等值面 + 前缀面(共享物理文件)组外种子在场 -> done 零悬挂
    # ============================================================
    ev: dict = {"leg": "B_0711_direct"}
    p = None
    collected: set[str] = set()
    case = M.case_dir("rm04_25b")
    try:
        cfg, web_port = _write_cfg_fast_tick(case, alias_threshold=8)
        p = app.start(cfg, case)
        assert p.wait_web(40), f"WEB 没起来:\n{p.log()[-800:]}"
        assert p.wait_log("整组迁移已启用", 20), "relocate 启动日志缺失"
        # B1 单成员 M2(subfolder 布局; 单成员恒 direct) + 组外种子 X2a(恰等旧根)/X2b(前缀面共享文件)
        hm = M.fake_multi(qb, PACK_B, [(f"{PACK_B}/f0.bin", FILE_SIZE)], SRC_B, "rm04c25b", piece_len=16384, write=True)
        collected.add(hm)
        all_my_hashes.add(hm)
        M.wait_complete(qb, [hm], 120)
        hxa = M.fake_with_data(qb, NAME_X2A, FILE_SIZE, SRC_B, "rm04c25bxa", piece_len=16384, write=True)
        collected.add(hxa)
        all_my_hashes.add(hxa)
        hxb = M.fake_with_data(
            qb, "f0.bin", FILE_SIZE, SRC_B / PACK_B, "rm04c25bxb", piece_len=32768, write=False
        )  # 实字节反算: 与成员共享同一物理文件
        assert hxb != hm, "X2b 与成员 infohash 撞车(异 piece_len 必须异 infohash)"
        collected.add(hxb)
        all_my_hashes.add(hxb)
        M.wait_complete(qb, [hxa, hxb], 120)
        M.wait_store_progress(web_port, [hm], 60)
        assert M.norm((qb.torrent(hxa) or {}).get("save_path") or "") == M.norm(SRC_B), "X2a 不在旧根等值面"
        assert M.norm((qb.torrent(hxb) or {}).get("save_path") or "") == M.norm(SRC_B / PACK_B), \
            "X2b 不在旧根前缀面"
        ev["B1"] = {"m": hm[:8], "x2a": hxa[:8], "x2b": hxb[:8]}
        _flush(ev, case, "B_0711_direct")

        # B2 direct 搬迁 -> done(等值/前缀面组外种子全程在场)
        dst_b = case / "dst_b"
        job_b = _migrate(web_port, hm, dst_b, "direct")
        _wait_direct_done(web_port, hm, job_b, 60)
        M.wait_until(
            lambda: M.norm((qb.torrent(hm) or {}).get("save_path") or "") == M.norm(dst_b) or None, 30,
            lambda: f"M2 未落 dst: {(qb.torrent(hm) or {}).get('save_path')}"
        )
        # B3 断言: 零删链门悬挂 + 组外种子账面落点不动(direct 无别名无重定向, 0711b 短路)
        assert "删链门依赖未清" not in M.log_text(case), "direct 被顶进删链门(0711b 短路失守, 负向对照红)"
        assert M.norm((qb.torrent(hxa) or {}).get("save_path") or "") == M.norm(SRC_B), "X2a 落点被搬迁扰动"
        xa_state = str((qb.torrent(hxa) or {}).get("state") or "")
        assert "error" not in xa_state and "missing" not in xa_state, f"X2a 异常态: {xa_state}"
        xb = qb.torrent(hxb) or {}
        assert M.norm(xb.get("save_path") or "") == M.norm(SRC_B / PACK_B), "X2b 账面落点被搬迁扰动"
        ev["B2_done"] = {
            "job": job_b,
            "x2a_state": xa_state,
            "x2b_state": xb.get("state"),
            "x2b_note": "共享物理文件随 direct 搬迁断粮属预期副作用(无别名保持旧路径), 如实记账"
        }

        def no_chain_deps_on_disk():
            jobs = M.jobs_on_disk(case)
            bad = [jid for jid, j in jobs.items() if j.get("reason") == ru.REASON_CHAIN_DEPS]
            return True if (jobs and not bad) else None

        M.wait_until(no_chain_deps_on_disk, 100, "磁盘账出现 chain_deps(direct 误计, 负向对照红)")
        _flush(ev, case, "B_0711_direct")

        # B2.5 添加预检探针(0711 修法 a 告知面记录): direct 无别名面, 落点在旧根 -> 零 confirm
        pre = M.cmd_post_and_wait(web_port, "/api/relocate/precheck-add", {"save_path": str(SRC_B), "name": NAME_X2A})
        pre_truth = (pre or {}).get("truth") or pre or {}
        assert pre_truth.get("cls") == "ok", \
            f"添加预检非 ok(误拦复发): {json.dumps(pre, ensure_ascii=False)[:400]}"
        assert not [r for r in (pre_truth.get("reasons") or []) if (r or {}).get("gate") == "finalize_window"], \
            "添加预检出现收尾窗 confirm(direct 退 confirm 口径失守)"
        ev["B3_precheck"] = {"cls": pre_truth.get("cls"), "reasons": pre_truth.get("reasons")}
        _flush(ev, case, "B_0711_direct")
    except Exception as leg_err:  # noqa: BLE001
        ev["leg_error"] = repr(leg_err)
        agg_errs.append(f"B 腿(0711): {leg_err!r}")
    finally:
        agg_errs.extend(_leg_cleanup(p, case, SRC_B.parent, ev, collected, snap_before))
        all_my_hashes |= collected

    # ============================================================
    # C 腿(E3 同名依赖账): file_links 阈值 8 + 同名跨种添加 confirm -> 计依赖 -> 删账 -> done
    # ============================================================
    ev: dict = {"leg": "C_E3_same_name"}
    p = None
    collected: set[str] = set()
    case = M.case_dir("rm04_25c")
    try:
        cfg, web_port = _write_cfg_fast_tick(case, alias_threshold=8)
        p = app.start(cfg, case)
        assert p.wait_web(40), f"WEB 没起来:\n{p.log()[-800:]}"
        assert p.wait_log("整组迁移已启用", 20), "relocate 启动日志缺失"
        # C1 造组(双成员子目录单文件, 1 < 阈值 8 => file_links)
        hc1 = M.fake_multi(qb, PACK_C, [(REL_C, FILE_SIZE)], SRC_C, "rm04c25c", piece_len=PIECE_C[0], write=True)
        hc2 = M.fake_multi(qb, PACK_C, [(REL_C, FILE_SIZE)], SRC_C, "rm04c25c", piece_len=PIECE_C[1], write=False)
        assert hc1 != hc2, "C 腿两颗 infohash 撞车"
        collected |= {hc1, hc2}
        all_my_hashes |= collected
        M.wait_complete(qb, [hc1, hc2], 120)
        M.wait_group(web_port, hc1, {hc1, hc2}, 30, "C 腿未归组")
        M.wait_store_progress(web_port, [hc1, hc2], 60)
        # C2 搬迁 armed(文件级 symlink 现场)
        dst_c = case / "dst_c"
        job_c = _migrate(web_port, hc1, dst_c, "file_links")
        assert p.wait_log("已武装收尾", 60), "C 腿未武装(日志锚缺失)"
        c_link = SRC_C / REL_C
        M.wait_until(
            lambda: M.reparse_kind(c_link) == "symlink" or None, 60, lambda: f"C 链接形态异常: {M.reparse_kind(c_link)}"
        )
        assert _readlink_norm(c_link).startswith(M.norm(dst_c)), "C symlink 未指 dst_c"
        ev["C2_armed"] = {"job": job_c, "link": str(c_link)}
        _flush(ev, case, "C_E3_same_name")

        # C3 添加预检: 落点=别名链接同名位 -> confirm(场景 2 文案) —— 负向对照 1(误放行即红)
        pre = M.cmd_post_and_wait(
            web_port, "/api/relocate/precheck-add", {
                "save_path": str(SRC_C / PACK_C),
                "name": "f.bin"
            }
        )
        truth = (pre or {}).get("truth") or pre or {}
        assert truth.get("cls") == "confirm", \
            f"同名添加未回 confirm(误放行, 负向对照红): {json.dumps(pre, ensure_ascii=False)[:500]}"
        reasons = truth.get("reasons") or []
        assert any((r or {}).get("gate") == "finalize_window" for r in reasons), \
            f"confirm 原因缺 finalize_window: {reasons}"
        text = " ".join(str((r or {}).get("text") or "") for r in reasons)
        assert "与成员别名链接同名" in text, f"场景 2 文案缺「与成员别名链接同名」: {text}"
        assert "共享同一份物理数据" in text, f"场景 2 文案缺「共享同一份物理数据」: {text}"
        # 场景 2(文件级同名撞链接)的 confirm 不带 actual_path 重定向展示(base_add 恒 None
        # —— actual_path 是目录级重定向面的展示键; 首跑实测), 断言 requested_path = 落点位
        requested = str(truth.get("requested_path") or "")
        assert M.norm(requested) == M.norm(SRC_C / PACK_C / "f.bin"), \
            f"requested_path 与落点位不符: {requested}"
        ev["C3_confirm"] = {"cls": truth.get("cls"), "text": text[:200], "requested_path": requested}
        _flush(ev, case, "C_E3_same_name")

        # C4 确认后真加同名跨种种子 X3(经链接共享同一份物理数据)
        hx3 = M.fake_with_data(
            qb, "f.bin", FILE_SIZE, SRC_C / PACK_C, "rm04c25cx3", piece_len=PIECE_X3, write=False
        )  # 实字节反算: 内容=成员文件
        assert hx3 not in (hc1, hc2), "X3 infohash 与成员撞车"
        collected.add(hx3)
        all_my_hashes.add(hx3)
        M.wait_complete(qb, [hx3], 120)  # 经 symlink 读 dst 数据校验, 必过
        t3 = qb.torrent(hx3) or {}
        assert M.norm(t3.get("save_path") or "") == M.norm(SRC_C / PACK_C), "X3 落点异常"
        ev["C4_added"] = {"x3": hx3[:8], "state": t3.get("state")}
        _flush(ev, case, "C_E3_same_name")

        # C5 删光成员 -> 收缩 -> 删链门计依赖(文件清单 x 链接相交)+ symlink 保留 + X3 可读
        anchor0 = M.log_text(case).count("删链门依赖未清")
        qb.delete(hc1, delete_files=False)
        qb.delete(hc2, delete_files=False)
        M.wait_until(
            lambda: True
            if M.log_text(case).count("删链门依赖未清") > anchor0 else None, 120, "删链门依赖未清行未出现(同名跨种未计依赖 = R2 交集精判失守, 负向对照红)"
        )
        dep_line = [ln for ln in M.log_text(case).splitlines() if "删链门依赖未清" in ln][-1]
        assert "(1 个)" in dep_line, f"依赖计数非 1: {dep_line}"
        assert M.reparse_kind(c_link) == "symlink", f"删链门悬挂期链接被删(误删): {c_link}"
        sha_dst = _sha1_file(dst_c / REL_C)
        assert _sha1_file(c_link) == sha_dst, "X3 经 symlink 读不到 dst 数据(断粮)"

        def chain_deps_on_disk_c():
            job = M.jobs_on_disk(case).get(job_c) or {}
            return job if job.get("reason") == ru.REASON_CHAIN_DEPS else None

        M.wait_until(
            chain_deps_on_disk_c, 100,
            lambda: f"磁盘账未落 chain_deps: {(M.jobs_on_disk(case).get(job_c) or {}).get('reason')}"
        )
        ev["C5_gate"] = {"job": job_c, "reason": ru.REASON_CHAIN_DEPS, "log": dep_line, "link_kept": True}
        _flush(ev, case, "C_E3_same_name")

        # C6 删 X3 账面 -> 依赖清零收尾 done + 链接删除
        qb.delete(hx3, delete_files=False)
        M.wait_until(lambda: True if "收尾完成" in M.log_text(case) else None, 120, "收尾完成行未出现(删依赖种子后收尾仍卡 = 依赖账不清零)")
        fin_line = [ln for ln in M.log_text(case).splitlines() if "收尾完成" in ln][-1]
        assert "删链门依赖清零" in fin_line and "已在线删除别名" in fin_line, f"收尾行语义不符: {fin_line}"
        M.wait_until(lambda: True if not os.path.lexists(str(c_link)) else None, 60, "收尾后 symlink 未删除")

        def done_on_disk_c():
            job = M.jobs_on_disk(case).get(job_c) or {}
            return job if job.get("phase") == ru.PHASE_DONE and job.get("reason") == ru.REASON_FINALIZED else None

        M.wait_until(done_on_disk_c, 100, lambda: f"磁盘账未落 done/finalized: {M.jobs_on_disk(case).get(job_c)}")
        ev["C6_finalized"] = {"job": job_c, "log": fin_line, "link_removed": True}
        _flush(ev, case, "C_E3_same_name")
    except Exception as leg_err:  # noqa: BLE001
        ev["leg_error"] = repr(leg_err)
        agg_errs.append(f"C 腿(E3): {leg_err!r}")
    finally:
        agg_errs.extend(_leg_cleanup(p, case, SRC_C.parent, ev, collected, snap_before))
        all_my_hashes |= collected

    # ---- Z 总收尾: 别名 lstat 复核零残留 + 双实例恢复在线 + 聚合三腿失败
    residue_links = [
        str(pth) for pth in (SRC_A / PACK_A, SRC_B / PACK_B, SRC_C / PACK_C, SRC_C / REL_C) if M._is_link(pth)
    ]
    assert not residue_links, f"三腿别名零残留失守: {residue_links}"
    for port in (instances.SECONDARY, instances.PRIMARY):
        W.qb_up(port)  # 环境还原: 双实例回在线(片C 开工前提)
    ev["Z"] = {"alias_residue": residue_links, "legs": "A/B/C"}
    _flush(ev, M.WORK / "rm04_25c", "Z_summary")
    if agg_errs:
        raise AssertionError("RM04-25 三腿存在失败: " + " | ".join(agg_errs))
