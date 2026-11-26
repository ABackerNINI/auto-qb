"""[RM04-22] 链式续迁收官 + 撤销不搬回 真机闭环: A->B 搬迁 armed 后同组发起 B->C -> 旧任务立即
收官为只读历史(superseded)且未完成链接工作移交新任务 -> handover 统一改指后旧路径 A/B 经 chain
端点与文件系统双证解析到 C 终位置(别名直指物理数据, 无链式锚点中间跳) -> 撤销活任务(两投:
无 confirm 回三段式确认面 / confirm=true 执行)后数据与下载器路径逐字未动(不搬回)、半搬数据留
新位置、任务自己已建的链接删除而继承别名(前任的)不删不撤 -> 旧任务随新任务账面共存且不可单独
删除(终态守卫拒绝 + 无独立删除路由)。

计划 plans/26-11-17-0636-plan-real-rm04-relocate-refactor-verify.html §03.4 RM04-22 用例卡
(acc1/issue 26-11-07-0528; S1a 单活任务模型 33d7f850 + S2 撤销语义重做 1f3f88a7)。
guide 三段只做 API 结构化断言(consequence/halfway/manual 三键齐备), UI 消费面(撤销入口+
弹窗渲染)不入真机轨 —— 已入池 26-11-17-0156 另案(计划 §03.3)。

形态选择: dir_alias(junction)。alias_threshold: 1 + 子目录布局(内容根 = save_path/<组名> 目录
专属) => FORM_DIR_ALIAS(RM04-05 同款); junction 对 qB 可判定(穿透读 = 真实元数据), qB 侧自检
POSITIVE 不跳过, A->B 两段都能在不进 daemon 离线窗的前提下确定性走到 armed(RM04-05 先例)——
链式用例的断言窗在 armed(改指收敛后), 不需要 RM04-20/21 的旁路面, 零新增授权。

## 测试计划(单测试函数, 分段)
- C1 开工闸: R: 拓扑在 + 双实例在线(connection_status 非 disconnected) + 副实例无 real-fake
  残留 + BT_backup 可定位。
- C2 造组: 两颗共享文件假种子(子目录布局, 同内容异 piece_len 异 infohash)落 R: 成组 +
  产品快照 progress 追平。
- C3 A->B 发起 + armed: 回执 started(形态 dir_alias) -> mover 落 B -> A 内容根成 junction
  -> 经原路径穿透可读 -> 日志「迁移发起」「已武装收尾」-> job1 落 armed。
- C4 B->C 发起(续迁即收官): 首投(无 confirm)回确认面且零 GATE_UNFINISHED(收尾窗放行新口径)
  -> confirm=true 二投 started job2 -> job1 立即 superseded(journal 相位+superseded_by 即时面
  + state 账面 + 日志「续迁即收官 -> 只读历史」三证)-> job2.plan.inherited 含前任移交条目
  (dst=B / alias_paths=[A junction] / alias_kind=dir / link_kind=junction)。
- C5 job2 armed + 改指收敛: mover 落 C -> B 内容根 junction -> C -> handover 日志「别名统一
  改指」-> plan.handover_done -> A junction 已改指 C(不再是 A->B)。
- C6 旧路径双证解析到 C(chain 端点 + 文件系统, 用例卡断言 2): chain 端点从旧根成员出发
  nodes[0]=A junction target 直指 C、链中无 B 中间跳、终节点 ok -> 文件系统 readlink 双链接
  (A/B)均直指 C -> 经 A/B 原路径穿透读 sha1 与 C 物理文件一致。
- C7 撤销两投(用例卡断言 3/4): 无 confirm -> cls=confirm + guide 三段齐备(后果/半途警示/
  手动处置推荐)且本投零副作用(相位/链接现场未动) -> confirm=true -> cls=ok phase=cancelled。
- C8 撤销不搬回断言面: 两成员 qB save_path/root_path/content_path 逐字未动 -> C 数据 sha1
  未动(半搬数据留新位置)-> 任务自建链接(B junction)已删、B 侧无数据回填(不搬回)-> 继承
  别名(A junction)不删不撤且仍解析 C -> 非 mover fastresume 三路径键逐字未动(撤销链不碰
  fastresume)-> 成员零 error/missing。
- C9 账面共存 + 无单独删除入口(用例卡断言 1/5): state 账 job1(superseded)+job2(cancelled)
  共存 -> 撤销旧任务被终态守卫拒(gate=cancel_terminal, 连确认面都不给)-> 探测无独立删除路由
  (POST /api/relocate/jobs/<id>/delete -> 404)。
- C10 收尾: 产品退出(外部终止, 非优雅 —— Windows 无进程外 SIGTERM, 与 RM04-23 sentinel 通路口径相抵处按机制如实表述) -> 双实例恢复在线 -> real-fake 删净(连数据)-> BT_backup 本用例哈希
  残留清除 + 逐文件比对开工快照 -> case 树与 R:/qbt-fake/rm04/rm04_22 删净。

前置: 环境1(R: 在, src=R:/qbt-fake/rm04/rm04_22/src 与 dst=D: 异盘) + 双测试实例在线(没起先
      `commands run real.up -- --port <白名单端口>`); 副实例无 real-fake 残留; 独占约 3-5 分钟,
      conftest serial 锁串行保护。R: 缺席 => 拓扑不成立 => skip 不回退落点(钉死口径, 与
      RM04-20/21 同款, 不做环境自适应)。
副作用: 两轮真搬迁(A->B、B->C, qB 真移数据)+ 一次撤销; A/B 内容根 junction 建立与改指/删除;
      state/relocate 账落盘(两条 job); 副实例 BT_backup 新增本用例哈希的 fastresume/torrent;
      副实例 2 枚 real-fake 种子。
回滚: real-fake 连数据删净 + BT_backup 只清本用例哈希残留 + 逐文件比对开工快照(queue 豁免);
      case 树与 R:/qbt-fake/rm04/rm04_22 删净(purge_tree 不递归删穿链接); 产品退出(外部终止, 非优雅);
      双实例恢复在线。
失败判据: 续迁发起后旧任务未立即 superseded 或账面缺移交条目; 旧路径不解析到 C(chain 端点或
      文件系统任一证不成立)或链中出现 B 中间跳; 回执缺 guide 任一段; 撤销后任一成员 qB 路径
      变化(搬回复发)或 C 数据被搬回 B; 自建链接(B junction)残留或继承别名被误删; 旧任务可
      单独删除(终态守卫失守或存在删除路由); 非 mover fastresume 被改写; 收尾有残留。
拓扑钉死: src = R:/qbt-fake/rm04/rm04_22/src(R: 内存盘, 与 dst 所在 D: 异盘); B/C = 用例
      case 子目录。alias_threshold: 1 压低阈值(用例卡口径)。

跑法: `commands run real.run -- --case RM04-22 --yes`(不要裸 pytest)。
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.error
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_rm04_relocate as M  # noqa: E402  (复用 RM04 的造种/清场/断言助手)
import test_rm04_relocate_window as W  # noqa: E402  (BT_BACKUP 单点/fr 三路径键/快照比对 helper 复用)

from lib import app, guard, instances  # noqa: E402

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="本片断言含 Windows 特有语义(junction/外部终止语义)"),
]

# 拓扑单点(钉死, 见模块 docstring; 与 RM04-20/21 的子树隔离)
R_ROOT = Path("R:/qbt-fake/rm04")
SRC = R_ROOT / "rm04_22" / "src"
NAME = "rm04c22pack"
REL = f"{NAME}/data/f0.bin"
REL_UNDER = "data/f0.bin"  # 内容根下的相对路径(REL 去掉组名前缀; junction 穿透读用)
FILE_SIZE = 256 * 1024
PIECE_LENS = (16384, 32768)  # 同文件异 infohash 的区分面(两颗成员)
SALT = "rm04c22"

# 片B 证据目录(任务口径: 逐案 evidence 落 tests/real/.work/rm04-sliceB/)
SLICE_EV = HERE.parent / ".work" / "rm04-sliceB"


def _flush(ev: dict, case: Path) -> None:
    """证据落盘(gitignored .work/rm04-sliceB): 全量断言现场 + 产品日志副本。"""
    ev["ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
    SLICE_EV.mkdir(parents=True, exist_ok=True)
    (SLICE_EV /
     "rm04_22_evidence.json").write_text(json.dumps(ev, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (SLICE_EV / "rm04_22_auto-qb.log").write_text(M.log_text(case), encoding="utf-8")


def _sha1_file(p: Path) -> str:
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _readlink_norm(p: Path) -> str:
    """junction/symlink 目标原始读出(归一成 / 形 + 剥设备前缀; 断言直指谁用)。

    产品建链带 Windows 长路径前缀(alias_fs add_long_path_prefix_for_win 单点), os.readlink
    把带前缀形态原样回吐 —— M.norm 只翻斜杠不剥前缀, 比对前必须剥掉(首跑实测踩中:
    `//?/D:/...`.startswith(`D:/...`) 恒 False 的假红)。"""
    s = M.norm(os.readlink(str(p)))
    if s.startswith("//?/UNC/"):
        return "//" + s[len("//?/UNC/"):]
    if s.startswith("//?/"):
        return s[len("//?/"):]
    return s


def _require_r_topology() -> None:
    """拓扑钉死第一半: R: 必须在(环境1 D盘机)。缺席 = skip 不回退(模块 docstring)。"""
    try:
        SRC.parent.mkdir(parents=True, exist_ok=True)
        probe = SRC.parent / ".probe"
        probe.write_bytes(b"x")
        probe.unlink()
    except OSError as e:
        pytest.skip(f"R: 盘缺席/不可写, 跨盘拓扑(src R: vs dst D:)不成立 —— 本用例钉死环境1 D盘机拓扑: {e}")


def _chain_of(web_port: int, h: str) -> dict:
    return M.web_req(web_port, "GET", f"/api/relocate/chain?hash={h}&refresh=1")


def _http_post_status(web_port: int, path: str, body: dict) -> int:
    """探测路由存在性: 404 = 无该路由; 其余 HTTP 错误如实上抛(不吞)。"""
    try:
        M.web_req(web_port, "POST", path, body)
    except urllib.error.HTTPError as e:
        return e.code
    return 200


# ================================================================ RM04-22


def test_rm04_22_chain_supersede_cancel_no_moveback():
    """[RM04-22] 链式续迁收官 + 撤销不搬回 真机闭环(C1-C10, 断言明细见模块 docstring)

    前置: R: 在 + 双实例在线 + 副实例无 real-fake 残留; 副实例 BT_backup 可定位。
    副作用/回滚/失败判据: 见模块 docstring(四行契约)。
    """
    _require_r_topology()
    case = M.case_dir("rm04_22")
    qb = M.qbfake()
    assert not M.rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
    assert W.BT_BACKUP.is_dir(), f"副实例 BT_backup 不在(env_registry EXE 派生路径失效?): {W.BT_BACKUP}"

    ev: dict = {"case": str(case), "topology": {"src": str(SRC), "b": "case/b", "c": "case/c"}}
    _flush(ev, case)
    p = None
    h1 = None  # finally 的收尾按"已知多少清多少"推进, 早退时未造的成员不参与清理
    h2 = None
    b_root = case / "b"
    c_root = case / "c"
    snap_before = W.bt_backup_snapshot()
    try:
        # ---- C1 双实例在线 + connection_status 非 disconnected(§2.4 假红陷阱闸)
        for port in (instances.PRIMARY, instances.SECONDARY):
            guard.check_port(port)
            status = guard.check_online(instances.make(port))
            assert status != "disconnected", f"{port} connection_status=disconnected(假红陷阱), 拒跑"
        M.purge_tree(SRC.parent)
        b_root.mkdir(parents=True, exist_ok=True)
        c_root.mkdir(parents=True, exist_ok=True)

        # ---- C2 产品实例 + 两颗共享文件假种子归同组
        cfg, web_port = M.write_cfg(case, relocate=True, alias_threshold=1)
        p = app.start(cfg, case)
        assert p.wait_web(40), f"WEB 没起来:\n{p.log()[-800:]}"
        assert p.wait_log("整组迁移已启用", 20), f"relocate 启动日志缺失(开关没生效?):\n{p.log()[-600:]}"
        h1 = M.fake_multi(qb, NAME, [(REL, FILE_SIZE)], SRC, SALT, piece_len=PIECE_LENS[0], write=True)
        h2 = M.fake_multi(qb, NAME, [(REL, FILE_SIZE)], SRC, SALT, piece_len=PIECE_LENS[1], write=False)
        assert h1 != h2, "两颗 infohash 撞车(必须同文件异 infohash)"
        M.wait_complete(qb, [h1, h2], 120)
        M.wait_group(web_port, h1, {h1, h2}, 30, "两颗未归入同一辅种组(共享文件归组前提不成立)")
        M.wait_store_progress(web_port, [h1, h2])  # 迁移闸门读产品快照, 等 1-2 个同步拍追平
        g = M.group_row(M.groups_view(web_port), h1)
        kpath, kfiles = M.decode_key(g["key"])
        assert M.norm(kpath) == M.norm(SRC), f"组键首元不是 src 内容根: {kpath}"
        ev["C2_group_before"] = {"key": g["key"], "members": [h1, h2]}
        _flush(ev, case)

        # ---- C3 A->B 发起 + armed(dir_alias: threshold=1, 内容根目录专属)
        result = M.cmd_post_and_wait(
            web_port, f"/api/torrents/{h1}/location", {
                "location": str(b_root),
                "confirm": True
            }
        )
        item = M.one_started_item(result)
        job1 = item.get("job_id")
        assert job1, f"回执 started 项缺 job_id: {json.dumps(item, ensure_ascii=False)[:400]}"
        assert item.get("form") == "dir_alias", f"A->B 形态非 dir_alias: {item.get('form')}"
        assert p.wait_log("迁移发起", 10), "日志缺「迁移发起」(A->B 搬迁没有真正下发)"
        job = M.wait_job_phase(case, job1, {"armed", "failed"}, 240, "job1 未到 armed(或提前 failed)")
        assert job.get("phase") == "armed", f"job1 未武装: phase={job.get('phase')} reason={job.get('reason')}"
        src_str = str(job.get("src") or "")
        b_str = str(job.get("dst") or "")
        mover1 = str(job.get("mover") or "")
        assert M.norm(src_str) == M.norm(SRC), f"job1 src 不是 A: {src_str}"
        assert M.norm(b_str) == M.norm(b_root), f"job1 dst 不是 B: {b_str}"
        assert mover1 in (h1, h2), f"job1 mover 不在组内: {mover1}"
        assert "已武装收尾" in M.log_text(case), "日志缺「已武装收尾」(A->B arm 段没走)"
        # A->B armed 现场: mover 在 B; A 内容根 = junction -> B; 穿透可读
        wait_mover_at = M.wait_until(
            lambda: M.norm((qb.torrent(mover1) or {}).get("save_path") or "") == M.norm(b_str) or None, 60,
            lambda: f"A->B mover 未落 B: {(qb.torrent(mover1) or {}).get('save_path')}"
        )
        ev["C3_job1_armed"] = {"job_id": job1, "mover": mover1, "mover_save_path": wait_mover_at}
        a_junction = SRC / NAME
        assert M.reparse_kind(a_junction) == "junction", f"A 内容根链接形态非 junction: {M.reparse_kind(a_junction)}"
        assert _readlink_norm(a_junction).startswith(M.norm(b_str)), \
            f"A junction 未指 B: {_readlink_norm(a_junction)}"
        c3_sha = _sha1_file(SRC / REL)
        assert c3_sha == _sha1_file(Path(b_str) / REL), "经 A 原路径穿透读到的内容与 B 物理文件不一致(链没建好)"
        _flush(ev, case)

        # ---- C4 B->C 发起(续迁即收官, 用例卡断言 1/5 的发起半边)
        anchor0 = M.count_anchor(case, "迁移发起")
        first = M.cmd_post_and_wait(web_port, f"/api/torrents/{h1}/location", {"location": str(c_root)})
        fitems = ((first or {}).get("truth") or {}).get("results") or []
        fconfirms = [it for it in fitems if it.get("cls") == "confirm"]
        assert fconfirms, f"B->C 首投未回确认面: {json.dumps(first, ensure_ascii=False)[:600]}"
        gates4 = [r.get("gate") for it in fitems for r in (it.get("reasons") or [])]
        assert "unfinished" not in [str(g or "").lower() for g in gates4], \
            f"收尾窗再迁移被 GATE_UNFINISHED 拦(单活模型放行新口径失守): {gates4}"
        assert M.count_anchor(case, "迁移发起") == anchor0, "首投(未确认)出现「迁移发起」(确认面前置失守)"
        result2 = M.cmd_post_and_wait(
            web_port, f"/api/torrents/{h1}/location", {
                "location": str(c_root),
                "confirm": True
            }, timeout=60
        )
        item2 = M.one_started_item(result2)
        job2 = item2.get("job_id")
        assert job2 and job2 != job1, f"B->C 回执 started 项异常: {json.dumps(item2, ensure_ascii=False)[:400]}"
        assert item2.get("form") == "dir_alias", f"B->C 形态非 dir_alias: {item2.get('form')}"
        assert p.wait_log("迁移发起", 10), "日志缺 B->C「迁移发起」"
        # 收官三证之一: 日志锚(即时)
        sup_lines = [ln for ln in M.log_text(case).splitlines() if "续迁即收官" in ln and job1 in ln and job2 in ln]
        assert sup_lines, (
            "日志缺「续迁即收官 -> 只读历史(superseded)」行:\n" +
            "\n".join(ln for ln in M.log_text(case).splitlines() if "单活模型" in ln)[-10:]
        )
        # 收官三证之二: journal 即时面(superseded + superseded_by)
        jr1 = M.wait_until(
            lambda: (M.journal_of(case, job1) or {}).get("phase") == "superseded" and
            (M.journal_of(case, job1) or {}).get("superseded_by") == job2 and M.journal_of(case, job1) or None, 30,
            f"job1 journal 未即时翻 superseded(superseded_by={job2})"
        )
        ev["C4_supersede"] = {"job1": job1, "job2": job2, "journal": jr1, "log": sup_lines[-1]}
        # 收官三证之三: state 账面(周期刷盘, 宽限窗)
        j1d = M.wait_job_phase(case, job1, {"superseded"}, 90, "job1 未落 superseded 只读历史(state 账面)")
        assert j1d.get("reason") == "superseded", f"job1 收官 reason 不符: {j1d.get('reason')}"
        assert M.norm(j1d.get("dst") or "") == M.norm(b_str), "前任账面 dst 被改写(收官冻结语义失守)"

        # 移交条目: job2.plan.inherited 含前任(链接工作移交, 未完成链接工作的承接面)
        def inherited_ready():
            j2 = M.jobs_on_disk(case).get(job2) or {}
            inh = ((j2.get("plan") or {}).get("inherited") or [])
            hit = [e for e in inh if isinstance(e, dict) and e.get("job_id") == job1]
            if hit:
                return (j2, hit[0])
            return None

        j2d, entry = M.wait_until(inherited_ready, 90, "job2 账面缺前任移交条目(plan.inherited 未落)")
        assert M.norm(entry.get("dst") or "") == M.norm(b_str), f"移交条目 dst 不是 B: {entry}"
        assert [M.norm(x) for x in (entry.get("alias_paths") or ())] == [M.norm(str(a_junction))], \
            f"移交条目别名清单不符: {entry}"
        assert entry.get("link_kind") == "junction", f"移交条目 link_kind 不符: {entry}"
        ev["C4_inherited"] = entry
        _flush(ev, case)

        # ---- C5 job2 armed + handover 统一改指(别名直指物理数据, 无链式锚点中间跳)
        job = M.wait_job_phase(case, job2, {"armed", "failed"}, 240, "job2 未到 armed(或提前 failed)")
        assert job.get("phase") == "armed", f"job2 未武装: phase={job.get('phase')} reason={job.get('reason')}"
        assert float(job.get("armed_at") or 0) > 0, "job2 armed_at 未置位"
        c_str = str(job.get("dst") or "")
        mover2 = str(job.get("mover") or "")
        assert M.norm(c_str) == M.norm(c_root), f"job2 dst 不是 C: {c_str}"
        assert M.norm(str(job.get("src") or "")) == M.norm(b_str), \
            f"job2 src 应按物理根解析为 B(前任 dst): {job.get('src')}"
        assert mover2 in (h1, h2), f"job2 mover 不在组内: {mover2}"
        M.wait_until(
            lambda: M.norm((qb.torrent(mover2) or {}).get("save_path") or "") == M.norm(c_str) or None, 60,
            lambda: f"B->C mover 未落 C: {(qb.torrent(mover2) or {}).get('save_path')}"
        )
        b_junction = Path(b_str) / NAME
        assert M.reparse_kind(b_junction) == "junction", f"B 内容根链接形态非 junction: {M.reparse_kind(b_junction)}"
        assert _readlink_norm(b_junction).startswith(M.norm(c_str)), f"B junction 未指 C: {_readlink_norm(b_junction)}"
        assert _readlink_norm(a_junction).startswith(M.norm(c_str)), \
            f"A junction 未改指 C(仍是 {_readlink_norm(a_junction)}): handover 统一改指失守"
        assert any(
            "别名统一改指" in ln and job1 in ln and M.norm(c_str) in M.norm(ln) for ln in M.log_text(case).splitlines()
        ), "日志缺 handover「别名统一改指」行"
        j2_now = M.jobs_on_disk(case).get(job2) or {}
        assert (j2_now.get("plan") or {}).get("handover_done") is True, \
            f"plan.handover_done 未落(改指收敛标记缺失): {j2_now.get('plan')}"
        ev["C5_job2_armed"] = {"dst": c_str, "mover": mover2, "handover_done": True}
        _flush(ev, case)

        # ---- C6 旧路径双证解析到 C(chain 端点 + 文件系统, 用例卡断言 2)
        nonmover = h2 if mover2 == h1 else h1
        chain = _chain_of(web_port, nonmover)
        nodes = chain.get("nodes") or []
        assert nodes, f"chain 端点空链: {json.dumps(chain, ensure_ascii=False)[:600]}"
        n0 = nodes[0]
        assert M.norm(n0.get("path") or "").startswith(M.norm(str(a_junction))), \
            f"chain 起点不是旧根 junction 位: {n0}"
        assert n0.get("type") == "junction", f"chain 首节点形态非 junction: {n0}"
        assert M.norm(n0.get("target") or "").startswith(M.norm(c_str)), \
            f"chain 首跳 target 未直指 C(无中间跳口径): {n0.get('target')}"
        assert not any(M.norm(nd.get("path") or "").startswith(M.norm(b_str)) for nd in nodes), \
            f"链中出现 B 中间跳(A->B->C 链式锚点复发): {json.dumps(nodes, ensure_ascii=False)[:600]}"
        last = nodes[-1]
        assert last.get("status") == "ok", f"chain 终节点未 ok: {last}"
        assert M.norm(last.get("path") or "").startswith(M.norm(c_str)), f"chain 终点不是 C: {last}"
        c6_sha = _sha1_file(Path(c_str) / REL)
        for via in (a_junction, b_junction):
            assert _sha1_file(via / REL_UNDER) == c6_sha, f"经 {via} 穿透读到的内容与 C 物理文件不一致"
        ev["C6_chain"] = {"hash": nonmover, "nodes": nodes, "fs_sha_ok": True}
        _flush(ev, case)

        # ---- C7 撤销两投(无 confirm 确认面 / confirm 执行; 用例卡断言 3/4)
        paths_before = {}
        for h in (h1, h2):
            t = qb.torrent(h) or {}
            paths_before[h] = {
                "save_path": t.get("save_path"),
                "root_path": t.get("root_path"),
                "content_path": t.get("content_path")
            }
        fr_before = {h: W.fr_path_keys(h) for h in (h1, h2)}
        r1 = M.cmd_post_and_wait(web_port, "/api/relocate/cancel", {"job_id": job2})
        it1 = (r1 or {}).get("truth") or {}
        assert it1.get("cls") == "confirm", f"无 confirm 撤销未回确认面: {json.dumps(r1, ensure_ascii=False)[:600]}"
        assert it1.get("job_id") == job2, f"确认面 job_id 不符: {it1.get('job_id')}"
        assert any((rr or {}).get("gate") == "cost" for rr in (it1.get("reasons") or [])), \
            f"确认面缺 gate=cost: {it1.get('reasons')}"
        guide = it1.get("guide") or {}
        assert set(guide.keys()) >= {"consequence", "halfway", "manual"}, \
            f"guide 三段不齐备(后果/半途警示/手动处置推荐): {list(guide.keys())}"
        assert str(guide.get("consequence") or "").strip(), "guide.consequence(后果)为空"
        assert "半途撤销警示" in str(guide.get("halfway") or ""), \
            f"guide.halfway 缺半途撤销警示语义: {guide.get('halfway')}"
        manual = guide.get("manual")
        assert isinstance(manual, list) and manual and all(str(x).strip() for x in manual), \
            f"guide.manual(手动处置推荐)为空或非串列表: {manual}"
        # 首投零副作用: 相位未动 + 自建链接现场未动
        assert (M.jobs_on_disk(case).get(job2) or {}).get("phase") == "armed", "确认面投递改变了相位(零副作用失守)"
        assert M.reparse_kind(b_junction) == "junction", "确认面投递删除了自建链接(零副作用失守)"
        r2 = M.cmd_post_and_wait(web_port, "/api/relocate/cancel", {"job_id": job2, "confirm": True})
        it2 = (r2 or {}).get("truth") or {}
        assert it2.get("cls") == "ok" and it2.get("phase") == "cancelled", \
            f"confirm 撤销未落 ok/cancelled: {json.dumps(r2, ensure_ascii=False)[:600]}"
        ev["C7_cancel"] = {"guide_keys": list(guide.keys()), "manual_n": len(manual), "final": it2}
        _flush(ev, case)

        # ---- C8 撤销不搬回断言面(S2 停手语义)
        j2f = M.wait_job_phase(case, job2, {"cancelled"}, 90, "job2 未落 cancelled(state 账面)")
        assert j2f.get("reason") == "cancelled", f"job2 reason 不符: {j2f.get('reason')}"
        assert list(j2f.get("alias_paths") or ()) == [], "cancelled 账面 alias_paths 未清空(自建链接账面口径)"
        for h in (h1, h2):
            t = qb.torrent(h) or {}
            now = {
                "save_path": t.get("save_path"),
                "root_path": t.get("root_path"),
                "content_path": t.get("content_path")
            }
            assert now == paths_before[h], f"{h[:8]} qB 路径被撤销改动(搬回复发): {paths_before[h]} -> {now}"
            assert W.fr_path_keys(h) == fr_before[h], f"{h[:8]} fastresume 被撤销改写(撤销链不碰成员路径口径失守)"
            st = str(t.get("state") or "").lower()
            assert "error" not in st and "missing" not in st, f"{h[:8]} 撤销后异常态: {t.get('state')}"
        assert _sha1_file(Path(c_str) / REL) == c6_sha, "C 数据被撤销改动(半搬数据留新位置失守)"
        assert not os.path.lexists(str(b_junction)), f"任务自建链接(B junction)撤销后残留: {b_junction}"
        assert not (Path(b_str) / REL).exists(), "数据被搬回 B(撤销不搬回失守)"
        assert M.reparse_kind(a_junction) == "junction", "继承别名(A junction)被撤销误删(D6 继承面不删不撤失守)"
        assert _readlink_norm(a_junction).startswith(M.norm(c_str)), \
            f"继承别名指向被撤销改动: {_readlink_norm(a_junction)}"
        assert _sha1_file(a_junction / REL_UNDER) == c6_sha, "经继承别名穿透读不到 C 数据(服务连续性失守)"
        ev["C8_no_moveback"] = {"paths": paths_before, "fr_untouched": True, "own_link_gone": True}
        _flush(ev, case)

        # ---- C9 账面共存 + 无单独删除入口(用例卡断言 5 + 1 的删除半边)
        ledger = M.jobs_on_disk(case)
        assert job1 in ledger and job2 in ledger, \
            f"账面缺共存记录: job1={job1 in ledger} job2={job2 in ledger} keys={list(ledger)[:6]}"
        assert ledger[job1].get("phase") == "superseded" and ledger[job2].get("phase") == "cancelled", \
            "共存记录相位不符"
        rb = M.cmd_post_and_wait(web_port, "/api/relocate/cancel", {"job_id": job1})
        itb = (rb or {}).get("truth") or {}
        assert itb.get("cls") == "blocked", f"旧任务撤销未被终态守卫拒: {json.dumps(rb, ensure_ascii=False)[:600]}"
        assert any((rr or {}).get("gate") == "cancel_terminal" for rr in (itb.get("reasons") or [])), \
            f"拒绝闸门非 cancel_terminal: {itb.get('reasons')}"
        # 无独立删除路由的面: 首跑实测 POST 未知 /api 路径回 405(factory 的静态挂载 "/" 是
        # 兜底路由, POST 不在其方法集 —— 405 与 404 都是「无该 API handler」的面; 2xx/4xx
        # 业务态(400/403/409 等)才算存在删除入口)
        del_status = _http_post_status(web_port, f"/api/relocate/jobs/{job1}/delete", {})
        assert del_status in (404, 405), \
            f"存在旧任务独立删除路由(API 无旧任务删除路由口径失守): POST 回 {del_status}"
        ev["C9_ledger"] = {
            "phases": {
                job1[:14]: ledger[job1].get("phase"),
                job2[:14]: ledger[job2].get("phase")
            },
            "cancel_terminal": True,
            "no_delete_route": True
        }

    finally:
        # ---- C10 收尾: 产品退出(外部终止, 非优雅) -> 实例恢复 -> 删种子(连数据) -> BT_backup 核净 -> 目录删净
        # 每步独立收集失败(不吞: 结尾聚合重抛); 证据先落盘再删目录。
        ev["C10_cleanup"] = {}
        errs: list[str] = []
        if p is not None:
            try:
                ev["C10_cleanup"]["product_stop_rc"] = p.stop(40)
            except Exception as e:  # noqa: BLE001 —— 收尾失败聚合重抛, 不静默
                errs.append(f"产品停止失败: {e!r}")
        _flush(ev, case)
        for port in (instances.SECONDARY, instances.PRIMARY):
            try:
                W.qb_up(port)  # 环境还原: 双实例回在线(片C 开工前提)
            except Exception as e:  # noqa: BLE001
                errs.append(f"real.up {port} 恢复失败: {e!r}")
        try:
            ev["C10_cleanup"]["seeds_removed"] = M.rm_all_fakes(M.qbfake())
        except Exception as e:  # noqa: BLE001
            errs.append(f"real-fake 种子清理失败: {e!r}")
        try:
            removed = []
            my_hashes = [h for h in (h1, h2) if h]
            for ih in my_hashes:
                for suffix in (".fastresume", ".torrent", ".fastresume.bak", ".torrent.bak"):
                    fp = W.BT_BACKUP / f"{ih}{suffix}"
                    if fp.is_file():
                        fp.unlink()
                        removed.append(fp.name)
            now = W.bt_backup_snapshot()
            residue = [k for k in now if k not in snap_before and not any(k.startswith(ih) for ih in my_hashes)]
            before_files = {k: v for k, v in snap_before.items() if (W.BT_BACKUP / k).is_file() and k != "queue"}
            changed = [k for k, v in before_files.items() if now.get(k) != v]
            ev["C10_cleanup"].update(
                {
                    "bt_backup_removed": removed,
                    "residue": residue,
                    "changed": changed,
                    "before_count": len(snap_before),
                    "after_count": len(now)
                }
            )
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
            raise AssertionError(f"收尾未净(C10): {'; '.join(errs)}")
