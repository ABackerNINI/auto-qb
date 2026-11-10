"""RM04-21 启动对账自愈真机闭环: 停机注入 failed/armed_at==0 账(生产事故形态: mover 已在 dst +
dst 内容全量在位 + src file symlink 已建, 收尾断在 qB 侧自检) -> 产品重启 -> 启动对账重入两行
(逐笔行 + 汇总行) -> qB 侧自检 skipped 不挡(文件级 symlink = 链接对象元数据, 真伪不可判) ->
armed -> 双测试实例优雅下线窗(daemon 改写非 mover fastresume) -> 重启全员落位 dst -> 收尾
done + 删链门删净别名 + 组键归一 dst。

计划 plans/26-11-10-0721-plan-relocate-startup-reconcile.html §03 的 T4a 手工实验
(tests-real/.work/reconcile-e2e/drive.py, gitignored, 含 facts.json 证据)全链闭环成功后沉淀为
耐久用例; 断言面 = T4a 实测证据(重入两行 / skipped 自检不挡 / armed / 改写账 / 收尾 done /
save_path 全员 dst / 别名删净 / 组归一), 构造面照 drive.py 配方(产品 RelocateJob 真实类生成
job 记录 + job_from_dict 回读校验, 不手拼字符串)。

## 测试计划(每个测试函数一条)
- test_rm04_21_reconcile_reenter_selfheal_e2e: B1 造现场(空库短起生成 state.json 骨架 -> 两颗共享
  文件假种子落 R: -> qB 原生 set_location 自搬 mover 到 dst -> src 建 file symlink 且穿透可读)
  -> B2 注入账面(产品 RelocateJob 真实类构造 failed/armed_at==0 -> job_from_dict 回读校验 ->
  写进 state.json relocate.jobs) -> B3 产品重启(旁路 runner)-> 启动对账重入两行(「启动对账重入
  (mover 已在 dst 且 dst 内容全量在位)」逐笔行 + 「启动对账 1 笔: 重入 1 / 保留 0」汇总行)->
  qB 侧自检 skipped(未解析文件级 symlink)不挡链且零 qb_side_check_failed -> job 落 armed 且
  armed_at>0 -> B4 双实例优雅下线(wrapper 名册窄化开窗, 新 patch 行或在位健康 daemon 二者其一)
  -> daemon 改写非 mover fastresume(journal 账 + fastresume 字节双证, mover=already)-> B5 重启
  全员落位 dst(零 recheck 零异常态)-> B6 job done + 「收尾完成」+ src 链接删净 + 组键归一 dst
  -> B7 收尾零残留 + 环境还原。

【daemon 离线窗旁路 —— 人工闸, 已授权 2026-11-10】
本机生产 16585/26586 常驻在跑, 全机 qbittorrent.exe 名册判据下离线窗永不开
(memory-bank/pitfalls/testing/relocate-window-machine-roster.md)。授权面 = 人工闸, 不随用例
自动扩大; 本用例**零新增旁路面** —— 旁路接线(start_bypass_app 进程内替换
relocate_exec.ExecMixin._spawn_daemon 经 tests-real/tools/daemon_window_wrapper.py 拉起)逐字
沿用 RM04-20(test_rm04_relocate_window.py, 授权记录/判据/边界见其模块 docstring), 本文件只复用。

拓扑钉死(drive.py 同款): src = R:/qbt-fake/rm04/reconcile/src(R: 内存盘, 与 qB CWD D: 异盘 =>
fastresume 保存键绝对形态, daemon 改写可达); dst = 用例 case/dst(D:, 与 src 异盘 + 单文件
1 < 阈值 8 => file_links+symlink 形态)。R: 缺席(环境2 C盘机)=> 拓扑不成立 => skip, 不回退
落点(钉死口径, 不做环境自适应)。

前置: 双测试实例在线(没起先 `commands run real.up -- --port <白名单端口>`); 副实例无 real-fake
残留; 本用例独占约 4-6 分钟(qB 两次起停 + 30s 稳定窗), conftest serial 锁串行保护; 实例起停经
RM04-20 同款 runner.py cmd_up/cmd_down(real.up/real.down task id 同一实现面)。
副作用: 副实例 加 2 假种子(real-fake)且 mover 被 qB 原生搬 R:->D:; src 出现 file symlink 再被
删链门删除; 两测试实例各优雅下线/重启一次; 副实例 BT_backup 新增本用例哈希的 fastresume/torrent
且非 mover 的被 daemon 改写; 产品 case 目录落账; wrapper 决策日志追加。
回滚: 产品优雅退出(sentinel 进程内 SIGTERM); 双实例恢复在线; real-fake 种子删净(连数据);
src/case 目录删净; BT_backup 只清本用例哈希残留 + 逐文件比对开工快照(queue 记账豁免);
daemon 靠自扫断粮 + 宽限退位自杀(绝不外杀, AGENTS.md 进程安全红线)。
失败判据: B3 无「启动对账重入」逐笔行或汇总行计数不符(对账消费面失效); 出现 qb_side_check_failed
(自检把 skipped 形态误判 NEGATIVE); job 未落 armed 或 armed_at==0(A1 落账语义丢); B4 非 mover
未 rewritten 或改写后仍指 src; B5 出现 recheck/error/missing 或未全员落位 dst; B6 job 非 done 或
src 链接残留或组键未归一 dst; B7 有残留或环境未还原。

升档(规程 §08): L2(脚本自动断言, B1-B7 全链)。与 RM04-20 的差异面: RM04-20 从迁移发起正向走
全链, 本用例从「failed 账 + 物理现状已就位」停机注入起步, 专验启动对账消费面(重入判定表 +
重入落账置 armed_at + 既有收尾链接管), 二者互补覆盖同一收尾链的两个入口。

跑法: `commands run real.run -- --case RM04-21 --yes`(不要裸 pytest)。
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import test_rm04_relocate as M  # noqa: E402  (复用 RM04 的造种/清场/断言助手)
import test_rm04_relocate_window as W  # noqa: E402  (RM04-20 同款旁路接线/派生配置/收尾 helper, 授权见其 docstring)

from lib import app, instances  # noqa: E402
from auto_qb.infra import alias_fs  # noqa: E402  (产品码: 建链单点)
from auto_qb.core.modules import relocate_units as ru  # noqa: E402  (产品码: job 类与序列化)
from auto_qb.core.modules.relocate_common import _native  # noqa: E402  (产品码: 路径拼装单点)

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="本片断言含 Windows 特有语义(symlink/优雅退出通路)"),
]

# 拓扑单点(钉死, 见模块 docstring; 与 RM04-20 的 rm04_20 子树隔离): src 在 R: 内存盘, dst 在 case(D:)
R_ROOT = Path("R:/qbt-fake/rm04")
SRC = R_ROOT / "reconcile" / "src"
FILE_NAME = "rm04c21.bin"
FILE_SIZE = 1024 * 1024
PIECE_LENS = (16384, 32768)  # 同文件异 infohash 的区分面(两颗成员)
SALT = "rm04c21"

# 复用 RM04-20 的旁路面(单一实现, 不另抄一份): qB 起停 / 派生配置 / 旁路产品 / 收尾核净
_require_r_topology = W._require_r_topology
_write_cfg = W._write_cfg
start_bypass_app = W.start_bypass_app
stop_lingering_product = W.stop_lingering_product
qb_up = W.qb_up
qb_down = W.qb_down
fr_path_keys = W.fr_path_keys
bt_backup_snapshot = W.bt_backup_snapshot
wrapper_lines = W.wrapper_lines
live_daemon_pid = W.live_daemon_pid
BT_BACKUP = W.BT_BACKUP


def _flush(ev: dict, case: Path) -> None:
    """证据落盘(gitignored .work, 与 RM04-20 片同落点): 全量断言现场 + 产品日志副本。"""
    ev["ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
    (M.WORK /
     "rm04_21_evidence.json").write_text(json.dumps(ev, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (M.WORK / "rm04_21_auto-qb.log").write_text(app.read_log(case), encoding="utf-8")


# ================================================================ RM04-21


def test_rm04_21_reconcile_reenter_selfheal_e2e():
    """[RM04-21] 启动对账自愈真机闭环(7 段 B1-B7, 断言明细见模块 docstring)

    前置: R: 在 + 双实例在线 + 副实例无 real-fake 残留; wrapper 收编入库版在位; 副实例 BT_backup
          可定位(env_registry EXE 派生)。
    副作用/回滚/失败判据: 见模块 docstring(四行契约)。
    """
    _require_r_topology()
    case = M.case_dir("rm04_21")
    stop_lingering_product(case)
    qb = M.qbfake()
    assert not M.rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
    assert BT_BACKUP.is_dir(), f"副实例 BT_backup 不在(env_registry EXE 派生路径失效?): {BT_BACKUP}"

    qb_up(instances.SECONDARY)  # 已在线则 [skip](runner 同一实现面, 无副作用)
    qb_up(instances.PRIMARY)

    ev: dict = {"case": str(case), "bt_backup": str(BT_BACKUP), "topology": {"src": str(SRC), "dst": "case/dst"}}
    _flush(ev, case)
    p = None
    h1 = None  # finally 的收尾按"已知多少清多少"推进, 早退时未造的成员不参与清理
    h2 = None
    dst = case / "dst"
    snap_before = bt_backup_snapshot()
    wl0 = len(wrapper_lines())  # wrapper 决策日志起点(本用例新增行 = [wl0:])
    try:
        # ---- B1 造现场: 空库短起(state.json 骨架) -> 两颗共享文件假种子 -> qB 自搬 mover 到 dst -> 建 src symlink
        M.purge_tree(SRC.parent)
        web_port = app.free_port()
        cfg = _write_cfg(case, web_port)
        # 短起(此刻副实例为空库, 产品零副作用): 生成合法 state.json, 停机注入才有干净底座
        p = start_bypass_app(case, cfg)
        assert p.wait_web(45), f"WEB 没起来:\n{p.log()[-800:]}"
        assert p.wait_log("整组迁移已启用", 20), f"relocate 启动日志缺失(开关没生效?):\n{p.log()[-600:]}"
        time.sleep(3)  # 让首轮 tick 落完
        rc = p.stop(40)
        p = None
        ev["B1_brief_start_rc"] = rc
        M.wait_until(lambda: (case / "data" / "state.json").is_file() or None, 10, "state.json 未生成(注入底座不成立)")

        h1 = M.fake_with_data(qb, FILE_NAME, FILE_SIZE, SRC, SALT, piece_len=PIECE_LENS[0], write=True)
        h2 = M.fake_with_data(qb, FILE_NAME, FILE_SIZE, SRC, SALT, piece_len=PIECE_LENS[1], write=False)
        assert h1 != h2, "两颗 infohash 撞车(必须同文件异 infohash)"
        M.wait_complete(qb, [h1, h2], 120)
        src_str = (qb.torrent(h1) or {}).get("save_path") or ""
        assert src_str, "mover save_path 读取失败(种子不在?)"
        ev["B1_seeded"] = {"h1": h1, "h2": h2, "src_str": src_str}
        _flush(ev, case)

        # qB 原生 set_location 自搬 mover(绕过 auto-qb: 物理上 qB 自己搬完 —— 事故「搬迁完成但收尾断链」形态)
        qb.set_location(h1, str(dst))

        def mover_at_dst():
            cur = qb.torrent(h1) or {}
            if M.norm(cur.get("save_path") or "") == M.norm(dst) and (dst / FILE_NAME).is_file():
                return cur["save_path"]
            return None

        dst_str = M.wait_until(mover_at_dst, 90, "mover 未落 dst 或 dst 文件缺失")
        assert not (SRC / FILE_NAME).exists(), "src 真身还在(qB 未物理搬走?)"

        # 事故形态: 建链段已完成(指向 dst 的 file symlink), 断在 qB 侧自检 -> 账留 failed
        link = _native(src_str, FILE_NAME)
        target = _native(dst_str, FILE_NAME)
        alias_fs.create_file_alias(link, target, "symlink")
        assert M.reparse_kind(Path(link)) == "symlink", f"src 链接位形态非 symlink: {link}"
        assert len(Path(link).read_bytes()) == FILE_SIZE, "经 src 原路径穿透读不到同 size(链没建好)"
        ev["B1_scene"] = {"dst_str": dst_str, "link": link, "target": target}
        _flush(ev, case)

        # ---- B2 注入账面: 产品 RelocateJob 真实类构造 failed/armed_at==0 -> 回读校验 -> 写进 state.json
        scope = ru.content_root_of(src_str, [FILE_NAME])
        job = ru.RelocateJob(
            job_id=ru.job_id_for(h1, dst_str, src_str),
            hashes=(h1, h2),
            mover=h1,
            src=src_str,
            dst=dst_str,
            scope=scope,
            alias_kind="file",  # _alias_kind_of_form("file_links") 同款
            alias_paths=(link, ),  # 事故形态: 建链已做(指向 dst 的 symlink), 断在 qB 侧自检
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
        assert back is not None, "job_from_dict 拒收构造 dict"
        assert back.job_id == d["job_id"] and back.phase == "failed", "回读字段不符"
        assert back.armed_at == 0.0, f"armed_at 回读 {back.armed_at} != 0(对账 A1 闸前提不成立)"
        assert back.mover == d["mover"] and tuple(back.hashes) == tuple(d["hashes"]), "成员回读不符"
        assert (back.plan or {}).get("form") == "file_links", "plan 回读不符"
        assert tuple(back.alias_paths) == tuple(d["alias_paths"]), "alias_paths 回读不符"
        job_id = d["job_id"]
        sp = case / "data" / "state.json"
        data = json.loads(sp.read_text(encoding="utf-8"))
        box = data.setdefault("relocate", {}).setdefault("jobs", {})
        box.clear()
        box[job_id] = d
        sp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        ev["B2_injected"] = {"job_id": job_id, "phase": d["phase"], "armed_at": d["armed_at"]}
        _flush(ev, case)

        # ---- B3 产品重启 -> 启动对账重入两行 -> skipped 自检不挡 -> armed(armed_at>0)
        stop_lingering_product(case)  # 幂等保险: 上一轮残留进程不占位
        p = start_bypass_app(case, cfg)
        assert p.wait_web(45), f"WEB 没起来:\n{p.log()[-800:]}"
        M.wait_until(lambda: "启动对账" in M.log_text(case) or None, 90, "90s 内未见「启动对账」日志(对账消费没跑)")

        def armed_seen():
            txt = M.log_text(case)
            if "已武装收尾" in txt:
                return True
            if "qb_side_check_failed" in txt:
                # 负向证据直达: wait_until 对假值不短路(会白烧到超时且报错被顶成泛化文案),
                # 检测到假阴性复发直接 raise 带该行日志
                raise AssertionError(
                    "自检把本形态误判 NEGATIVE(假阴性复发, 无需再等 armed):\n" +
                    "\n".join(ln for ln in txt.splitlines() if "qb_side_check_failed" in ln)[-600:]
                )
            return None

        assert M.wait_until(armed_seen, 180, "armed 未出现(重入链没走完)")
        lines = M.log_text(case).splitlines()
        reenter = [ln for ln in lines if "启动对账重入" in ln]
        assert reenter, "日志缺「启动对账重入」逐笔行:\n" + "\n".join(lines[-40:])
        assert "mover 已在 dst" in reenter[-1], f"重入行判据文案不符(走的不是重入支?): {reenter[-1]}"
        summary = [ln for ln in lines if "启动对账 " in ln and "保留" in ln]
        assert summary, "日志缺「启动对账 N 笔: 重入 N / 保留 N」汇总行"
        assert "重入 1 / 保留 0" in summary[-1], f"汇总行计数不符(只注入 1 笔): {summary[-1]}"
        skipped = [ln for ln in lines if "qB 侧自检跳过" in ln]
        assert skipped, "日志未见「qB 侧自检跳过」(skipped 不挡链的证据缺失)\n" + "\n".join(lines[-40:])
        assert any("未解析文件级 symlink" in ln for ln in skipped), \
            f"跳过原因不是链接对象元数据形态: {skipped[:2]}"
        assert not any("qb_side_check_failed" in ln for ln in lines), \
            "日志出现 qb_side_check_failed(自检把本形态误判 NEGATIVE, 假阴性复发)"
        job = M.wait_job_phase(case, job_id, {"armed"}, 120, "job 未落 armed 相位(重入落账没写盘)")
        assert job.get("phase") == "armed", f"job 相位非 armed: {job.get('phase')}/{job.get('reason')}"
        assert float(job.get("armed_at") or 0) > 0, "重入落账未置 armed_at(A1 语义丢失)"
        assert any("已武装收尾" in ln for ln in lines), "日志缺「已武装收尾」(arm 段没走)"
        ev["B3_reentered"] = {
            "reenter": reenter[-1],
            "summary": summary[-1],
            "skipped": skipped[-1],
            "phase": job.get("phase"),
            "armed_at": job.get("armed_at")
        }
        _flush(ev, case)

        # ---- B4 双测试实例优雅下线 -> wrapper 名册窄化开窗 -> daemon 改写非 mover fastresume
        wl1 = len(wrapper_lines())
        patched = [ln for ln in wrapper_lines()[wl0:] if "patched rd._proc_absent" in ln]
        if not patched:
            reused = live_daemon_pid(case)
            assert reused, ("wrapper 决策日志无新 patch 行且无在位健康 daemon(旁路没装上?)\n" + "\n".join(wrapper_lines()[wl0:][-10:]))
            patched = [f"reused live patched daemon pid={reused}(前轮宽限窗内在位, 产品按健康 watcher 复用)"]
        comp_before = {h: (qb.torrent(h) or {}).get("completion_on") for h in (h1, h2)}
        assert all(v is not None for v in comp_before.values()), \
            f"completion_on 取不到(recheck 锚失效): {comp_before}"
        qb_down(instances.SECONDARY)
        qb_down(instances.PRIMARY)
        ev["B4_down"] = {"wl1": wl1, "patched": patched[-1], "completion_on": comp_before}
        _flush(ev, case)

        def rewrite_settled():
            jr = M.journal_of(case, job_id) or {}
            rws = jr.get("rewrites") or {}
            if rws and all(
                ((rws.get(h) or {}).get("status")) in ("rewritten", "already", "unmatched") for h in (h1, h2)
            ):
                return jr
            return None

        jr = M.wait_until(rewrite_settled, 300, f"daemon 未在下线窗完成改写(job={job_id}; 30s 稳定窗+改写预算内)")
        rws = jr.get("rewrites") or {}
        rec = rws.get(h2) or {}
        assert rec.get("status") == "rewritten", f"非 mover {h2[:8]} 改写账 status={rec.get('status')} != rewritten"
        assert rec.get("keys"), f"非 mover {h2[:8]} 逐键明细缺失: {rec}"
        assert (rws.get(h1) or {}).get("status") in ("already", "rewritten"), \
            f"mover {h1[:8]} 改写账异常: {rws.get(h1)}"
        keys_after = fr_path_keys(h2)
        assert keys_after, f"改写后 {h2[:8]} fastresume 无非空路径键"
        assert all(M.norm(v).startswith(M.norm(dst_str)) for v in keys_after.values()), \
            f"{h2[:8]} 改写后未指 dst: {keys_after}"
        M.wait_until(
            lambda: (M.journal_of(case, job_id) or {}).get("phase") == "rewritten" or None, 120,
            "journal 相位未翻 rewritten"
        )
        wnew = wrapper_lines()[wl1:]
        assert any("test_qb=0" in ln and "refused=True" in ln and "absent=True" in ln for ln in wnew), \
            "wrapper 决策日志未见「测试 qB 全下线 => absent=True」开窗判定(名册窄化未生效?)"
        ev["B4_rewrite"] = {
            "rewrites": {
                h[:8]: rws.get(h)
                for h in (h1, h2)
            },
            "fr_keys_after": keys_after,
            "wrapper_new_lines": wnew[-20:]
        }
        _flush(ev, case)

        # ---- B5 重启双实例 -> 全员落位 dst(completion_on 锚定零 recheck、零 error/missing)
        qb_up(instances.SECONDARY)
        qb_up(instances.PRIMARY)

        def all_at_dst():
            cur = {t["hash"]: t for t in qb.torrents()}
            if all(M.norm((cur.get(h) or {}).get("save_path") or "") == M.norm(dst_str) for h in (h1, h2)):
                return {h: cur[h]["save_path"] for h in (h1, h2)}
            return None

        sps = M.wait_until(
            all_at_dst, 120, lambda: f"重启后未全员落位 dst: "
            f"{ {h: (qb.torrent(h) or {}).get('save_path') for h in (h1, h2)} }"
        )
        # recheck 判定改状态锚(评审轮 1: 轮询采样窗错过 qB 载入期, checking 采样结构性失效):
        # fastresume completion_date 载入保持原值, 全量 recheck 完成才刷新 —— 下线前后相等即零 recheck
        comp_after = {h: (qb.torrent(h) or {}).get("completion_on") for h in (h1, h2)}
        assert comp_after == comp_before, (
            "completion_on 变化 = qB 载入后对成员做过全量 recheck(改写链不该引发): "
            f"before={comp_before} after={comp_after}"
        )
        for h in (h1, h2):
            t = qb.torrent(h) or {}
            assert t.get("progress") == 1.0, f"{h[:8]} progress != 1.0: {t.get('progress')}"
            assert "error" not in str(t.get("state")).lower() and "missing" not in str(t.get("state")).lower(), \
                f"{h[:8]} 异常态: {t.get('state')}"
        ev["B5_restart"] = {"save_paths": sps, "completion_on_before": comp_before, "completion_on_after": comp_after}
        _flush(ev, case)

        # ---- B6 收尾 done + 别名删净 + 组归一(终态解析登记表退出后, 组键整体归一 dst)
        job = M.wait_job_phase(case, job_id, {"done", "failed"}, 300, "job 未收敛")
        assert job.get("phase") == "done", f"job 终态非 done: phase={job.get('phase')} reason={job.get('reason')}"
        assert not os.path.lexists(str(link)), f"src 链接位残留(删链门没删): {link}"
        assert "收尾完成" in M.log_text(case), "日志缺「收尾完成」(收尾链没走)"
        assert not any("qb_side_check_failed" in ln for ln in M.log_text(case).splitlines()), \
            "全程出现 qb_side_check_failed(假阴性复发)"
        g2 = M.wait_group(web_port, h1, {h1, h2}, 60, "组未归一(两颗不同组 = 裂组)")
        k2 = M.decode_key(g2["key"])
        assert M.norm(k2[0]) == M.norm(dst_str), f"终态组键首元不是 dst: {k2[0]}"
        assert tuple(sorted(k2[1])) == (FILE_NAME, ), f"终态组键文件列表不符: {k2[1]}"
        ev["B6_final"] = {
            "phase": job.get("phase"),
            "reason": job.get("reason"),
            "link_gone": True,
            "group_key": g2["key"]
        }
        _flush(ev, case)

    finally:
        # ---- B7 收尾: 产品优雅退出 -> 实例恢复 -> 删种子(连数据) -> BT_backup 核净 -> 目录删净
        # 每步独立收集失败(不吞: 结尾聚合重抛, 原始失败信息一并保留); 证据先落盘再删目录。
        ev["B7_cleanup"] = {}
        errs: list[str] = []
        if p is not None:
            try:
                ev["B7_cleanup"]["product_stop_rc"] = p.stop(40)
            except Exception as e:  # noqa: BLE001 —— 收尾失败聚合重抛, 不静默
                errs.append(f"产品停止失败: {e!r}")
        _flush(ev, case)
        for port in (instances.SECONDARY, instances.PRIMARY):
            try:
                qb_up(port)  # 环境还原: 双实例回在线(conftest 模块闸与后续片的开工前提)
            except Exception as e:  # noqa: BLE001
                errs.append(f"real.up {port} 恢复失败: {e!r}")
        try:
            ev["B7_cleanup"]["seeds_removed"] = M.rm_all_fakes(M.qbfake())
        except Exception as e:  # noqa: BLE001
            errs.append(f"real-fake 种子清理失败: {e!r}")
        try:
            removed = []
            my_hashes = [h for h in (h1, h2) if h]
            for ih in my_hashes:
                for suffix in (".fastresume", ".torrent", ".fastresume.bak", ".torrent.bak"):
                    fp = BT_BACKUP / f"{ih}{suffix}"
                    if fp.is_file():
                        fp.unlink()
                        removed.append(fp.name)
            now = bt_backup_snapshot()
            residue = [k for k in now if k not in snap_before and not any(k.startswith(ih) for ih in my_hashes)]
            # 比对面只认开工前已有的逐种子文件; queue = qB 自身记账文件(会话期合法变化, 豁免)
            before_files = {k: v for k, v in snap_before.items() if (BT_BACKUP / k).is_file() and k != "queue"}
            changed = [k for k, v in before_files.items() if now.get(k) != v]
            ev["B7_cleanup"].update(
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
            M.purge_tree(SRC.parent)  # 只删本用例子树; 产品不删空内容根目录(设计内, 实验切片口径)
            M.purge_tree(case)
        except Exception as e:  # noqa: BLE001
            errs.append(f"目录清理失败: {e!r}")
        if errs:
            raise AssertionError(f"收尾未净(B7): {'; '.join(errs)}")
