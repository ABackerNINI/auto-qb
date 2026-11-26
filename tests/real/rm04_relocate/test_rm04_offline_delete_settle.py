"""

同源声明: _write_cfg_fast_tick/_await_wrapper_patched/_flush 三件 helper 与 test_rm04_e9_selfheal_nomisfire.py 同源(函数体逐字一致, docstring/证据文件名前缀按用例本地化), 单侧改动须同步另一文件(评审 R23)。[RM04-27] 0401 停机期删除闭账复验: 搬迁 armed/收尾窗中双实例优雅下线 → 停机期删成员
(qB 侧删种, fastresume 随 qB 删除路径走) → 重启 → 断言闭账行为符合定稿语义(728d6ac8
三态判据: 收缩/闭账/摘要行) + 停机计数摘要一行 —— 结论喂 issue 26-11-14-0401 终态裁决。

计划 plans/26-11-17-0636-plan-real-rm04-relocate-refactor-verify.html §03.4 RM04-27 用例卡
(issue 0401 + 728d6ac8 已删成员闭账三态判据: 不在 store 的 resume_pending 成员连续
_DELETED_CONFIRM_TICKS=3 拍判真删除后闭账 —— relocate_lifecycle._reconcile_resume_pending
单点, 双面同删 resume_hashes/resume_pending + INFO 一行 + 收尾链重算)。

到达路径与确定性(构造论证): armed 相位 _resume_members 在武装拍即开恢复确认账, 成员回
运行态后 1-2 拍内闭合 —— 收尾窗(下线窗)开启时账已闭合, 停机期删除自然落不进闭账判据。
本用例的恢复账重开走**产品自有失败出口**: 收尾窗 journal failed 证据(relocate_units
_journals_failed_action ACT_FAIL_TERMINAL 判据: reason 非空 + ts 不早于 armed_at 锚点)
被 _consume_failed_journal 消费 → _fail 单点 → _resume_members 对下线中的 qB 开账
(「成功/失败都开」, relocate_lifecycle docstring 明载)→ resume_pending=(h1,h2) 持久在账
—— 终态与否都扫(四个终态出口的确认语义不漏口), 闭账判据与 job 相位无关。时序全程
确定性: 删除发生在下线窗内(fastresume 摘除 = qB 删除路径同终态, 重启后 qB 不再加载该
成员), 闭账发生在重启后 3 拍内(main_tick 1S)。

0401 披露面(宁悬挂勿误删, 用户拍板维持现状)顺带钉扎: 重启后全量轮差集被弃(issue 0401
证据锚定语义)→ job 停 ACT_WAIT、job.hashes 不收缩 —— 用例在重启后先观察该面(相位不动
+ hashes 含被删成员 + 别名在), 再走失败出口开账断言闭账面。

切分(不测三遍): daemon 离线窗改写链的深断言(改写账逐键/fastresume 字节/completion_on
零 recheck 锚/开窗观测面细节)归 RM04-21 B4/B5 已入库断言, 本用例只做**流程驱动等价**
(改写 settled + 双押开窗面各一断)以推进到删除窗, 不复写 B 链。

## 测试计划(单测试函数, 六段)
- G0 开工闸: R: 拓扑在 + 双实例在线 + 副实例无 real-fake 残留; 骨架短起停(state.json 底座)。
- S1 造现场(RM04-21 B1 配方): 两颗共享文件假种子落 R: → qB 原生 set_location 自搬 mover
  到 dst → src 建 file symlink 且穿透可读 → 注入 failed/armed_at==0 账(产品 RelocateJob
  真实类构造 + job_from_dict 回读校验)。
- S2 重入武装(产品重启): 启动对账重入两行 → armed(armed_at>0)→ 武装恢复账自然开合
  (成员回运行态, 闭合行进日志)。
- S3 收尾窗开窗: 双实例优雅下线(real.down 语义, 绝不 taskkill)→ daemon 改写非 mover
  fastresume(journal rewritten + 非 mover status=rewritten 各一断)→ 开窗观测面双押
  (window_regime_face 单断)。
- S4 停机期删成员: 摘除非 mover 的 fastresume+torrent(qB 删除路径同终态)→ 双证(文件
  消失 + 孪生 .bak 同净)。
- S5 重启 + 0401 披露面: 双实例回在线 → h1 落 dst / h2 不再加载(不在 qB)→ 观察 ~8s:
  job 相位不动(armed/rewritten)、job.hashes 仍含 h2(全量轮差集弃用, 收缩不计数)、
  reason 非 members_gone、别名在(宁悬挂勿误删)。
- S6 闭账断言(728d6ac8 三态): journal failed 注入(产品自有消费路径)→ 失败出口开恢复账
  (「已下发恢复 2 个成员(待快照回流确认)」日志锚 —— 开账暂态只存活 ~3 拍, state.json
  30S 落盘周期追不上, 首跑实锤)→ 3 拍闭账: 日志「成员已删除, 恢复账闭账」且含 h2 +
  state resume_hashes 收缩为 (h1,)(收缩面)+ h1 未被误闭(仍含 h1, 负向面)+ h1 回运行态
  确认闭合行 + h1 健康(progress 1.0 / dst / 零异常态)→ 产品优雅退出(sentinel)→ 停机
  计数摘要一行(「relocate | 停机: tag_failures=」, 全 0 也打)。
- Z 收尾: real-fake 删净(连数据)→ BT_backup 本用例哈希残留清除 + 逐文件比对开工快照 →
  case 树与 R: 子树删净 + symlink 零残留。

前置: 环境1(R: 在, src=R:/qbt-fake/rm04/rm04_27/src 与 dst=D: 异盘, fastresume 保存键
      绝对形态) + 双测试实例在线(没起先 `commands run real.up -- --port <白名单端口>`);
      副实例无 real-fake 残留; wrapper 名册窄化旁路在位(沿 RM04-20/21 授权, 零新增旁路
      面); 独占约 3-4 分钟, conftest serial 锁串行保护。R: 缺席 => skip 不回退落点。
副作用: 一次真搬迁(mover 被 qB 原生搬 R:->D:)+ 一次下线窗改写(非 mover fastresume 被
      daemon 改写)+ 停机删一枚成员的 fastresume/torrent + state 账(failed job + 闭账)+
      resume_failures 计数; symlink 建立后保留(失败出口保现场)再随清理删除。
回滚: 产品优雅退出(sentinel 通路, 停机摘要断言在其后); 双实例恢复在线; real-fake 种子
      删净(连数据); BT_backup 只清本用例哈希残留 + 逐文件比对开工快照(queue 豁免);
      case 树与 R:/qbt-fake/rm04/rm04_27 子树删净(purge_tree 不递归删穿链接)。
失败判据: 停机期删除不被闭账(闭账行缺失或 resume_hashes 仍含 h2 = 证据不计数病灶在
      闭账面复发)或误闭账吞掉存活成员(h1 被移出 resume_hashes); 摘要行缺失; 重入武装
      失败(无重入行或 armed_at==0); 改写未发生(非 mover 未 rewritten); h1 重启后异常态
      (recheck/error/missing)或未落 dst。

跑法: `commands run real.run -- --case RM04-27 --yes`(不要裸 pytest)。
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
import test_rm04_relocate_window as W  # noqa: E402  (RM04-20/21 同款旁路接线/收尾 helper, 授权见其 docstring)

from lib import app, guard, instances  # noqa: E402
from auto_qb.infra import alias_fs  # noqa: E402  (产品码: 建链单点)
from auto_qb.infra import relocate_journal as rj  # noqa: E402  (产品码: journal 写入面, 失败出口证据)
from auto_qb.core.modules import relocate_units as ru  # noqa: E402  (产品码: job 类与序列化)
from auto_qb.core.modules.relocate_common import _native  # noqa: E402  (产品码: 路径拼装单点)

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="本片断言含 Windows 特有语义(symlink/优雅退出通路)"),
]

# 拓扑单点(钉死, 见模块 docstring; 与 RM04-20/21/22/23/25/26 的子树隔离): src 在 R: 内存盘
R_ROOT = Path("R:/qbt-fake/rm04")
SRC = R_ROOT / "rm04_27" / "src"
FILE_NAME = "rm04c27.bin"
FILE_SIZE = 1024 * 1024
PIECE_LENS = (16384, 32768)  # 同文件异 infohash 的区分面(两颗成员)
SALT = "rm04c27"

# 复用 RM04-21 的旁路面(单一实现, 不另抄一份)
_require_r_topology = W._require_r_topology
start_bypass_app = W.start_bypass_app
stop_lingering_product = W.stop_lingering_product
qb_up = W.qb_up
qb_down = W.qb_down
bt_backup_snapshot = W.bt_backup_snapshot
wrapper_lines = W.wrapper_lines
live_daemon_pid = W.live_daemon_pid
window_regime_face = W.window_regime_face
# 副实例 BT_backup 路径单点在 W, 函数内按需取(收集期不探测 EXE)

# 片D 证据目录(任务口径: 逐案 evidence 落 tests/real/.work/rm04-sliceD/; 时刻后缀防覆写)
SLICE_EV = HERE.parent / ".work" / "rm04-sliceD"

#: 0401 披露面观察窗(重启后; 收缩若会发生会在 3 判定拍内发生, 8s 足以证「不发生」)
ABSENCE_OBSERVE_SECONDS = 8.0

#: 闭账确认拍数(产品常量 _DELETED_CONFIRM_TICKS=3)对齐的等待上限(main_tick 1S 拍闭账
#: ~3-4s; state.json 落盘 30S 周期, 收缩面读盘按一整个落盘周期+裕量给)
CLOSE_WAIT_SECONDS = 90


def _flush(ev: dict, case: Path, tag: str) -> None:
    """证据落盘(gitignored .work/rm04-sliceD): 全量断言现场 + 产品日志副本, 时刻后缀防覆写。"""
    ev["ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
    SLICE_EV.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    (SLICE_EV / f"rm04_27_{tag}_evidence_{stamp}.json"
    ).write_text(json.dumps(ev, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    try:
        log = M.log_text(case)
    except Exception as e:  # noqa: BLE001 —— 取证失败如实带错, 不掩盖主断言
        log = f"<log read failed: {e!r}>"
    (SLICE_EV / f"rm04_27_{tag}_auto-qb_{stamp}.log").write_text(log, encoding="utf-8")


def _write_cfg_fast_tick(case: Path) -> tuple[Path, int]:
    """RM04-27 专用配置: 在 M.write_cfg 基础上把 main_tick 2S -> 1S(片C 沉淀派生)。

    闭账判据按主循环拍计(连续 3 拍不在 store), 1S 拍让 3 拍确认在 ~3-4s 内确定发生;
    sync_interval 1.5S 不变(重启后首轮全量 + 其后增量轮的节奏照旧)。"""
    cfg, web_port = M.write_cfg(case, relocate=True, alias_threshold=8)
    text = cfg.read_text(encoding="utf-8")
    assert "main_tick: 2S" in text
    cfg.write_text(text.replace("main_tick: 2S", "main_tick: 1S"), encoding="utf-8")
    return cfg, web_port


def _fr_files(ih: str) -> list[Path]:
    """本用例哈希在 BT_backup 的全部账文件(fastresume/torrent 及 .bak 孪生)。"""
    out = []
    for suffix in (".fastresume", ".torrent", ".fastresume.bak", ".torrent.bak"):
        fp = W.BT_BACKUP / f"{ih}{suffix}"
        if fp.is_file():
            out.append(fp)
    return out


def _await_wrapper_patched(wl0: int, case: Path, timeout: float = 15.0) -> list[str]:
    """等 wrapper patch 行或在位健康 daemon(daemon 刚拉起时 patch 行/心跳落盘有 ~1s 竞态窗)。"""
    def probe():
        patched = [ln for ln in wrapper_lines()[wl0:] if "patched rd._proc_absent" in ln]
        if patched:
            return patched
        pid = live_daemon_pid(case)
        if pid:
            return [f"reused live patched daemon pid={pid}(前轮宽限窗内在位, 产品按健康 watcher 复用)"]
        return None

    return M.wait_until(probe, timeout, "wrapper patch 行与在位健康 daemon 均未出现(旁路没装上?)")


# ================================================================ RM04-27


def test_rm04_27_offline_delete_settle():
    """[RM04-27] 停机期删除闭账复验(六段 S1-S6+Z, 断言明细见模块 docstring)

    前置: R: 在 + 双实例在线 + 副实例无 real-fake 残留; wrapper 收编入库版在位。
    副作用/回滚/失败判据: 见模块 docstring(四行契约)。
    """
    _require_r_topology()
    case = M.case_dir("rm04_27")
    stop_lingering_product(case)
    qb = M.qbfake()
    assert not M.rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
    assert W.BT_BACKUP.is_dir(), f"副实例 BT_backup 不在(env_registry EXE 派生路径失效?): {W.BT_BACKUP}"
    for port in (instances.PRIMARY, instances.SECONDARY):
        guard.check_port(port)
        status = guard.check_online(instances.make(port))
        assert status != "disconnected", f"{port} connection_status=disconnected(假红陷阱), 拒跑"
    qb_up(instances.SECONDARY)  # 已在线则 [skip](runner 同一实现面, 无副作用)
    qb_up(instances.PRIMARY)

    ev: dict = {"case": str(case), "bt_backup": str(W.BT_BACKUP), "topology": {"src": str(SRC), "dst": "case/dst"}}
    p = None
    h1 = None  # finally 的收尾按"已知多少清多少"推进
    h2 = None
    dst = case / "dst"
    snap_before = bt_backup_snapshot()
    wl0 = len(wrapper_lines())
    try:
        # ---- S1 造现场(RM04-21 B1/B2 配方): 骨架短起 -> 双成员种子 -> qB 自搬 mover -> 建 symlink -> 注入账
        # 端口单点 = _write_cfg_fast_tick 返回值(app.free_port 记会话已用集, 双调必错位 ——
        # RM04-34 首跑实锤: 额外 free_port 占 39001, cfg 实绑 39002, 探针打 39001 恒拒连)
        M.purge_tree(SRC.parent)
        cfg, _web_port = _write_cfg_fast_tick(case)
        p = start_bypass_app(case, cfg)
        assert p.wait_web(45), f"WEB 没起来:\n{p.log()[-800:]}"
        assert p.wait_log("整组迁移已启用", 20), f"relocate 启动日志缺失:\n{p.log()[-600:]}"
        time.sleep(3)  # 让首轮 tick 落完
        rc = p.stop(40)
        p = None
        assert rc == 0, f"骨架优雅退出码 {rc}:\n{p.log()[-600:] if p else ''}"
        M.wait_until(lambda: (case / "data" / "state.json").is_file() or None, 10, "state.json 未生成(注入底座不成立)")

        h1 = M.fake_with_data(qb, FILE_NAME, FILE_SIZE, SRC, SALT, piece_len=PIECE_LENS[0], write=True)
        h2 = M.fake_with_data(qb, FILE_NAME, FILE_SIZE, SRC, SALT, piece_len=PIECE_LENS[1], write=False)
        assert h1 != h2, "两颗 infohash 撞车(必须同文件异 infohash)"
        M.wait_complete(qb, [h1, h2], 120)
        src_str = (qb.torrent(h1) or {}).get("save_path") or ""
        assert src_str, "mover save_path 读取失败(种子不在?)"
        qb.set_location(h1, str(dst))

        def mover_at_dst():
            cur = qb.torrent(h1) or {}
            if M.norm(cur.get("save_path") or "") == M.norm(dst) and (dst / FILE_NAME).is_file():
                return cur["save_path"]
            return None

        dst_str = M.wait_until(mover_at_dst, 90, "mover 未落 dst 或 dst 文件缺失")
        assert not (SRC / FILE_NAME).exists(), "src 真身还在(qB 未物理搬走?)"
        link = _native(src_str, FILE_NAME)
        target = _native(dst_str, FILE_NAME)
        alias_fs.create_file_alias(link, target, "symlink")
        assert M.reparse_kind(Path(link)) == "symlink", f"src 链接位形态非 symlink: {link}"
        assert len(Path(link).read_bytes()) == FILE_SIZE, "经 src 原路径穿透读不到同 size(链没建好)"
        ev["S1_scene"] = {"h1": h1, "h2": h2, "dst_str": dst_str, "link": link}
        _flush(ev, case, "S1")

        scope = ru.content_root_of(src_str, [FILE_NAME])
        job = ru.RelocateJob(
            job_id=ru.job_id_for(h1, dst_str, src_str),
            hashes=(h1, h2),
            mover=h1,
            src=src_str,
            dst=dst_str,
            scope=scope,
            alias_kind="file",
            alias_paths=(link, ),
            phase=ru.PHASE_FAILED,
            reason="qb_side_check_failed",
            created_at=time.time(),
            armed_at=0.0,  # 对账 A1 闸前提: armed_at==0 才进判定表
            updated_at=time.time(),
            resume_hashes=(h1, h2),
            attempts=0,
            last_error="qB 经原路径读到的文件元数据与本机 dst 不一致: 链接可能未被 qB 跟随",
            plan={
                "form": "file_links",
                "link_kind": "symlink",
                "scope": scope,
                "files": [[FILE_NAME, FILE_SIZE]],
            },
            move_issued=True,
            tag_on=False,
            origin="web",
        )
        d = ru.job_to_dict(job)
        back = ru.job_from_dict(d)
        assert back is not None and back.phase == "failed" and back.armed_at == 0.0, "注入账回读校验失败"
        job_id = d["job_id"]
        sp = case / "data" / "state.json"
        data = json.loads(sp.read_text(encoding="utf-8"))
        box = data.setdefault("relocate", {}).setdefault("jobs", {})
        box.clear()
        box[job_id] = d
        sp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        ev["S1_injected"] = {"job_id": job_id, "resume_hashes": [h1[:8], h2[:8]]}
        _flush(ev, case, "S1b")

        # ---- S2 重入武装: 启动对账重入 -> armed(armed_at>0; 武装恢复账自然开合)
        stop_lingering_product(case)
        p = start_bypass_app(case, cfg)
        assert p.wait_web(45), f"WEB 没起来:\n{p.log()[-800:]}"
        M.wait_until(lambda: "启动对账" in M.log_text(case) or None, 90, "90s 内未见「启动对账」(对账消费没跑)")
        assert M.wait_until(lambda: "已武装收尾" in M.log_text(case) or None, 180, "armed 未出现(重入链没走完)")
        lines = M.log_text(case).splitlines()
        reenter = [ln for ln in lines if "启动对账重入" in ln]
        assert reenter and "mover 已在 dst" in reenter[-1], f"重入行缺失或判据文案不符: {reenter[-1:]}"
        rjob = M.wait_job_phase(case, job_id, {"armed"}, 120, "job 未落 armed 相位")
        assert rjob.get("phase") == "armed" and float(rjob.get("armed_at") or 0) > 0, \
            f"armed/armed_at 不符: {rjob.get('phase')}/{rjob.get('armed_at')}"
        ev["S2_armed"] = {"reenter": reenter[-1], "armed_at": rjob.get("armed_at")}
        _flush(ev, case, "S2")

        # ---- S3 收尾窗开窗: 双实例优雅下线 -> daemon 改写非 mover -> 开窗观测面双押(单断)
        wl1 = len(wrapper_lines())
        patched = _await_wrapper_patched(wl0, case)
        comp_before = {h: (qb.torrent(h) or {}).get("completion_on") for h in (h1, h2)}
        qb_down(instances.SECONDARY)
        qb_down(instances.PRIMARY)
        ev["S3_down"] = {"wl1": wl1, "patched": patched[-1]}
        _flush(ev, case, "S3a")

        def rewrite_settled():
            jr = M.journal_of(case, job_id) or {}
            rws = jr.get("rewrites") or {}
            if rws and all(
                ((rws.get(h) or {}).get("status")) in ("rewritten", "already", "unmatched") for h in (h1, h2)
            ) and jr.get("phase") == "rewritten":
                return jr
            return None

        jr = M.wait_until(rewrite_settled, 300, f"daemon 未在下线窗完成改写(job={job_id}; 30s 稳定窗+改写预算内)")
        rws = jr.get("rewrites") or {}
        assert (rws.get(h2) or {}).get("status") == "rewritten", \
            f"非 mover {h2[:8]} 改写账 status={(rws.get(h2) or {}).get('status')} != rewritten"
        assert (rws.get(h1) or {}).get("status") in ("already", "rewritten"), \
            f"mover {h1[:8]} 改写账异常: {rws.get(h1)}"
        wnew = wrapper_lines()[wl1:]
        l1_face, obs_owner = window_regime_face(case, wnew)  # 双押单断(细节归 RM04-21 B4, 切分见 docstring)
        ev["S3_rewrite"] = {
            "h2_status": (rws.get(h2) or {}).get("status"),
            "h1_status": (rws.get(h1) or {}).get("status"),
            "window_regime": {
                "l1_face": l1_face,
                "obs_owner_pid_alive": (obs_owner or {}).get("pid_alive")
            }
        }
        _flush(ev, case, "S3b")

        # ---- S4 停机期删成员: 摘除非 mover 的 fastresume+torrent(qB 删除路径同终态)
        fr2 = _fr_files(h2)
        assert fr2, f"非 mover {h2[:8]} 在 BT_backup 无账文件(改写产物缺失?)"
        removed = [fp.name for fp in fr2]
        for fp in fr2:
            fp.unlink()
        assert not _fr_files(h2), "停机删除后 BT_backup 仍有 h2 账文件"
        ev["S4_offline_delete"] = {"removed": removed, "hash": h2}
        _flush(ev, case, "S4")

        # ---- S5 重启 + 0401 披露面: h1 落 dst / h2 不再加载; 相位不动 + hashes 不收缩
        qb_up(instances.SECONDARY)
        qb_up(instances.PRIMARY)
        M.wait_until(lambda: (qb.torrent(h1) or {}).get("save_path") or None, 60, "重启后 h1 未回场")
        assert qb.torrent(h2) is None, "停机删除未生效: h2 重启后仍在 qB(h2 不该被加载)"
        t1 = qb.torrent(h1) or {}
        assert M.norm(t1.get("save_path") or "") == M.norm(dst_str), f"h1 未落 dst: {t1.get('save_path')}"
        assert t1.get("progress") == 1.0, f"h1 progress != 1.0: {t1.get('progress')}"
        st1 = str(t1.get("state") or "").lower()
        assert "error" not in st1 and "missing" not in st1, f"h1 异常态: {t1.get('state')}"
        comp_after = (qb.torrent(h1) or {}).get("completion_on")
        assert comp_before.get(h1) is not None and comp_after is not None, \
            f"completion_on 取数失败(守卫, 与 RM04-34 同款): before={comp_before.get(h1)} after={comp_after}"
        assert comp_after == comp_before.get(h1), \
            f"completion_on 变化 = 全量 recheck(改写链不该引发): before={comp_before.get(h1)} after={comp_after}"
        # 0401 披露面观察: 全量轮差集弃用 -> 收缩不计数, job 停 ACT_WAIT 系、hashes 仍含 h2
        time.sleep(ABSENCE_OBSERVE_SECONDS)
        hang_job = M.jobs_on_disk(case).get(job_id) or {}
        assert hang_job.get("phase") in ("armed", "rewritten"), \
            f"0401 披露面失守: job 相位被推进 {hang_job.get('phase')}(宁悬挂勿误删语义破)"
        assert h2 in tuple(hang_job.get("hashes") or ()), \
            "0401 披露面失守: job.hashes 收缩摘掉了停机期删除的成员(证据不计数语义破, 误收缩)"
        assert hang_job.get("reason") != ru.REASON_MEMBERS_GONE, "出现 members_gone 收缩(停机删除被误计数)"
        assert os.path.lexists(str(link)), "悬挂期别名被删(宁悬挂勿误删语义破)"
        ev["S5_offline_hang_face"] = {
            "phase": hang_job.get("phase"),
            "hashes_keep_deleted": True,
            "reason": hang_job.get("reason"),
            "h1_state": t1.get("state")
        }
        _flush(ev, case, "S5")

        # ---- S6 闭账断言(728d6ac8 三态: 收缩/闭账/摘要行): 失败出口开账 -> 3 拍闭账
        # 日志基线(评审 R23: S2 武装期已打同形「已下发恢复」行, 追加式日志下 next() 首匹配
        # 会命中陈旧行 —— 开账/闭合两锚只在基线之后的行里找)
        s6_base = len(M.log_text(case).splitlines())
        rj.write_journal(
            str(case / "data"), job_id, {
                "phase": ru.PHASE_FAILED,
                "reason": "verify_mismatch",
                "ts": time.time(),
            }
        )
        M.wait_until(lambda: "转 failed 终态" in M.log_text(case) or None, 60, "journal failed 证据未被消费(失败出口没走, 恢复账开不了)")
        fjob = M.wait_job_phase(case, job_id, {"failed"}, 60, "job 未落 failed 终态(证据消费未落账)")
        # 恢复账开账证据(日志锚; state.json 落盘 30S 周期追不上 ~3 拍即闭合的暂态窗口,
        # 首跑实锤: pending=(h1,h2) 只存活 ~2s, 轮盘永远读不到 —— 开账断言走日志行):
        open_line = M.wait_until(
            lambda: next(
                (ln for ln in M.log_text(case).splitlines()[s6_base:] if "已下发恢复 2 个成员" in ln and "待快照回流确认" in ln), None
            ), 60, "失败出口未开恢复账(基线后无「已下发恢复 2 个成员」行)"
        )
        # 闭账: 连续 3 拍不在 store -> 判真删除 -> 双面同删
        closed_line = M.wait_until(
            lambda: next((ln for ln in M.log_text(case).splitlines() if "成员已删除, 恢复账闭账" in ln), None),
            CLOSE_WAIT_SECONDS, "闭账行未出现(停机期删除不被闭账 = 0401 病灶在闭账面复发)"
        )
        assert h2 in closed_line, f"闭账行未点名被删成员: {closed_line}"

        def hashes_shrunk():
            cur = (M.jobs_on_disk(case).get(job_id) or {})
            rh = tuple(cur.get("resume_hashes") or ())
            return cur if (h2 not in rh and h1 in rh) else None

        cur = M.wait_until(hashes_shrunk, CLOSE_WAIT_SECONDS, "resume_hashes 未收缩(双面同删失守)")
        assert h1 in tuple(cur.get("resume_hashes") or ()), "存活成员被误闭账吞掉(负向面红)"
        ev["S6_close"] = {
            "line": closed_line,
            "open_line": open_line,
            "resume_hashes": [h[:8] for h in cur.get("resume_hashes") or ()]
        }
        _flush(ev, case, "S6a")

        # 存活成员回运行态 + 确认闭合
        M.wait_until(
            lambda: str((qb.torrent(h1) or {}).get("state") or "").lower().find("stop") < 0 and "error" not in str(
                (qb.torrent(h1) or {}).get("state") or ""
            ).lower() or None, 90, lambda: f"h1 未回运行态: {(qb.torrent(h1) or {}).get('state')}"
        )

        def confirm_closed():
            hit = [ln for ln in M.log_text(case).splitlines()[s6_base:] if "恢复确认闭合" in ln]
            return hit[-1] if hit else None

        cc_line = M.wait_until(confirm_closed, 90, "恢复确认闭合行未出现(存活成员确认语义失守)")
        # 点名 h1 按产品行真格式落地(r23 首跑实锤: assert h1 in cc_line 恒假 —— 产品行
        # 「恢复确认闭合(N 个成员已回到运行态)」只带计数不带 hash, relocate_lifecycle 单点):
        # S6a 已证收缩后账恰为 (h1,)(双成员组 h2 出/h1 留), 行内计数==存活账大小 即点名
        # h1 的构造性等价, 计数不匹配照红(存活成员被换/多闭都逃不掉)。
        n_survive = len(tuple(cur.get("resume_hashes") or ()))
        assert f"恢复确认闭合({n_survive} 个成员已回到运行态)" in cc_line, \
            f"确认闭合行计数与存活账不符: {cc_line} / 账 {n_survive} 个"
        t1b = qb.torrent(h1) or {}
        assert t1b.get("progress") == 1.0 and "error" not in str(t1b.get("state") or "").lower(), \
            f"h1 健康面失守: {t1b.get('state')}/{t1b.get('progress')}"
        assert os.path.lexists(str(link)), "失败出口应保现场(别名不删), 却被删了"
        ev["S6_survivor"] = {"state": t1b.get("state"), "alias_kept": True}
        _flush(ev, case, "S6b")

        # 摘要行(停机计数, D12 全 0 也打): 哨兵优雅退出后断言
        rc = p.stop(40)
        p = None
        assert rc == 0, f"产品优雅退出码 {rc}"
        summary = [ln for ln in M.log_text(case).splitlines() if "relocate | 停机: tag_failures=" in ln]
        assert summary, "停机计数摘要一行缺失(D12 语义失守)"
        ev["S6_summary"] = {"line": summary[-1], "stop_rc": rc}
        _flush(ev, case, "S6c")

    finally:
        # ---- Z 收尾: 产品退出 -> 实例恢复 -> 删种子(连数据) -> BT_backup 核净 -> 目录删净
        ev["Z_cleanup"] = {}
        errs: list[str] = []
        if p is not None:
            try:
                ev["Z_cleanup"]["product_stop_rc"] = p.stop(40)
            except Exception as e:  # noqa: BLE001
                errs.append(f"产品停止失败: {e!r}")
        _flush(ev, case, "Z1")
        for port in (instances.SECONDARY, instances.PRIMARY):
            try:
                qb_up(port)  # 环境还原: 双实例回在线
            except Exception as e:  # noqa: BLE001
                errs.append(f"real.up {port} 恢复失败: {e!r}")
        try:
            ev["Z_cleanup"]["seeds_removed"] = M.rm_all_fakes(M.qbfake())
        except Exception as e:  # noqa: BLE001
            errs.append(f"real-fake 种子清理失败: {e!r}")
        try:
            removed = []
            my_hashes = [h for h in (h1, h2) if h]
            for ih in my_hashes:
                for fp in _fr_files(ih):
                    fp.unlink()
                    removed.append(fp.name)
            now = bt_backup_snapshot()
            residue = [k for k in now if k not in snap_before and not any(k.startswith(ih) for ih in my_hashes)]
            before_files = {k: v for k, v in snap_before.items() if (W.BT_BACKUP / k).is_file() and k != "queue"}
            changed = [k for k, v in before_files.items() if now.get(k) != v]
            ev["Z_cleanup"].update({"bt_backup_removed": removed, "residue": residue, "changed": changed})
            if residue:
                errs.append(f"BT_backup 出现非本用例的未知残留: {residue}")
            if changed:
                errs.append(f"开工前已有 BT_backup 逐种子文件被改动: {changed}")
        except Exception as e:  # noqa: BLE001
            errs.append(f"BT_backup 核净失败: {e!r}")
        _flush(ev, case, "Z2")
        try:
            M.purge_tree(SRC.parent)
            M.purge_tree(case)
        except Exception as e:  # noqa: BLE001
            errs.append(f"目录清理失败: {e!r}")
        if errs:
            raise AssertionError(f"收尾未净(Z): {'; '.join(errs)}")
