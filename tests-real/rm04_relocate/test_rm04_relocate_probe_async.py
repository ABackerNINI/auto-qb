"""[RM04-35] S6 探测异步化真机复验 (1): 探测闸 dry-run 分支冒烟(模块直连 56590) + 同拓扑非 dry-run 受理对照(L3)
[RM04-36] S6 探测异步化真机复验 (2): 受理段 warn 全链(产品进程 WEB): warn 受理 -> verdict 消费 -> 自动续跑 -> done(finalized)
[RM04-37] S6 探测异步化真机复验 (3): FS 不可达行为面代理(句柄锁造法): 受理不阻塞/窗内主循环活性/verdict 窗期特征/终态补发/缓存污染面清理

计划 plans/26-11-21-0223-plan-real-rm11-s6-probe-verify.html §04(S6 探测异步化真机复验轮 RM11;
锚 issue 26-11-10-0638 三项真机待办; 上轮验收=单测/仿真全绿, 基线 26-11-20-2348)。
编号并入 rm04_relocate 片续号(定案 D4: RM05-01/02/03 已被 rm05_tracker_tags 片占用,
runner._cases 按 id 建 dict 会静默覆盖 —— real.run --case RM05-01 会静默跑错文件)。

三项判据的代码锚点与两项核实结论(dry-run 形态拆两腿 / 幽灵盘造法不可达改句柄锁)见计划
§01-§02, 这里不复述, 只落可执行断言。

## 测试计划
- RM04-35(判据 (1)a, L3): 模块直连真机形态(不起产品进程, RM04-11/12 同款 _ctx):
  2 枚带数据假种子(多文件子目录布局, 同内容异 piece_len 共享物理文件)落 .work 成组。
  A 腿 _dry=True: relocate_execute 返回恰 1 条 cls=ok + notes 含「dry-run: 跳过强探测」与
  「dry-run: 未下发搬迁」+ 无 probing 判别键 + qB save_path 零变动 + 零 aqb-probe 痕 +
  state 无 probes/probe_pending(dry-run 下 job 账仍登记是产品现行行为, relocate_exec.py:2328-2337
  先登记 :2339 才早退 —— 不对 job 账做空断言)。
  B 对照腿(L3 红验, _dry=False, 异 dst 免幂等 skip): 闸未命中 -> 异步受理(item cls=blocked +
  PROBE_GATE_PROBING_KEY=True) + probe_pending 恰 1 条 + daemon 线程真探测(56590 出现
  TAG_PROBE 种子 -> 证读证写 -> 自清理) + verdict 队列取到 passed/ok/env=False;
  收尾(清 pending/slot release/队列排空/槽空闲断言)在 finally 按受理状态容错执行(批B #5,
  模块直连无消费线)。
- RM04-36(判据 (1)b+(2), L2): 产品进程(WEB 开, relocate.enabled, bt_backup 56590 派生,
  schema_version 8)。前提自证: /api/torrents/relocate/precheck 的 item notes 含「一次性强探测」
  (子目录布局 -> D 级不可判 -> B' 弱证据 -> 未证明)。主链:
  A1 POST location -> 回执 status=warn + 文案「已受理: 同机探测进行中 1 项, 探测结论到达后自动续跑」
  + truth.summary {probing:1, started:0};
  A2 消费日志出现前「迁移发起」计数不增(probing != started);
  A3 日志出现「probe verdict 消费: 指纹 <fp8> 结论 passed/ok(缓存已写(passed))」;
  A4 之后「迁移发起」出现 + 同 cmd_id 回执被终态补发覆盖为 ok(started 带 job_id, probing==0);
  A5 mover save_path->dst + dst 文件对齐 + member2 测试侧助推后 job done(finalized)
  (相位取数单点 = GET /api/torrents/{hash} 的 relocate.phase, journal/state.json 30s 迟滞不作断言源);
  A6 state.json relocate.probes 含 passed 条目(30s 周期落盘, 轮询等待);
  收尾残留断言: _probe_residue 对 src/dst 双空(探针种子与目录, 批B #4)。
- RM04-37(判据 (3), L2): 同拓扑组 + 第三枚种子(W2 观测靶)。造法 = 句柄锁: POST 受理后测试进程
  轮询组 save_path 下 aqb-probe-* 目录, 探针文件落盘即 open('rb') 持句柄(Windows 无
  FILE_SHARE_DELETE -> qB 搬迁 rename 失败/copy 后 delete 失败) -> 证写 10s 超时 -> failed
  env=False -> 写指纹缓存。观测面(阈值写死, 见计划 §4.3):
  W1 POST->warn 回执 <=5s 且缓存条目 at(挂钟 epoch 秒)与受理 POST 时刻差 >=8s;
  W2 窗内对第三种子发 pause WEB 命令: 回执 <=8s 且 qB 态 stopped;
  W3 POST 后 <=25s 日志出现「probe verdict 消费: ... failed/<write_proof_timeout|write_mismatch>
  (缓存已写(failed, FS 不可达方向))」;
  W4 同 cmd_id 回执被覆盖为 error 且文案含「上次同机探测失败」与「已缓存」(D7-1 重放 blocked 面);
  W5 优雅态等 30s 周期落盘后 state.json relocate.probes 含 failed 条目(evidence.reason/at 留证)
  -> 停机态测试侧删 relocate.probes 键并复核为空;
  W6 全 case 零「迁移发起」/ 零 job 账 / 成员 save_path 不变 / dst 无组内容;
  W7 句柄关闭后测试侧显式删净两侧 aqb-probe-* 目录并断言删净(产品 _cleanup 持句柄期必失败
  不重试)+ TAG_PROBE 种子零残留。
  开工预检(批B #2, 计划 §4.3 R1): 用例体开头直调 run_probe(线程化, 独立 ctx 不经产品进程)
  + 句柄锁独立临时目录, 断言 failed/reason∈FAIL_REASONS/env=False, 不成立即 pytest.fail
  (BLOCKED: 句柄锁造法在该 qB 版本不成立 —— 不硬闯不降级)。

前置: 环境2(C盘机)双实例在线(没起先 `commands run real.up -- --port <白名单端口>`);
      副实例无 real-fake 残留; 串行锁保护(real.suite/real.run 逐条跑, 本轮不整片 suite ——
      范围仅 S6 三项, 整片会连跑旧用例超范围)。
副作用: 副实例加 2-3 枚 real-fake 假种子(连数据删); RM04-36/37 各起一个产品进程(case 目录内
      data_dir); RM04-36 一次 qB 真搬迁(用例目录内); RM04-37 两次失败探测(预检造法验证 + 主探测, 均自建自清);
      RM04-37 state.relocate.probes 写入后测试侧清理。
回滚: 删光 real-fake 种子(连数据); 产品进程优雅/常规停止(AppProc.stop, 禁 taskkill); case 树
      删净(purge_tree 不递归删穿链接); TAG_PROBE/aqb-probe-* 零残留核验。
失败判据: 见各用例 docstring 与计划 §04 三张卡; 任何「前提不成立」显式红不伪装 PASS。

跑法: `commands run real.run -- --case RM04-35 --yes`(不要裸 pytest; RM04-36/37 同款换 id)。
"""
from __future__ import annotations

import json
import queue
import shutil
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_rm04_relocate as M  # noqa: E402  (复用 RM04 的造种/清场/断言助手)

from lib import app, guard, instances  # noqa: E402
from auto_qb.config.models import RelocateConfig  # noqa: E402
from auto_qb.config import QbittorrentConfig  # noqa: E402
from auto_qb.core.modules import relocate_units as ru  # noqa: E402  (PROBE_GATE_PROBING_KEY 判别键)
from auto_qb.core.modules.relocate_mod import RelocateModule  # noqa: E402
from auto_qb.core.modules.relocate_probe import PROBE_DIR_PREFIX, TAG_PROBE, run_probe  # noqa: E402
from auto_qb.core.qbapi import QbApi  # noqa: E402
from auto_qb.core.qbclient import new_client  # noqa: E402
from auto_qb.torrents.store import TorrentStore  # noqa: E402

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="真机轨含 Windows 句柄语义(文件锁造法)"),
]

# 证据落点(计划 §3.2; gitignored .work, 时刻后缀防覆写 —— RM04-26 _flush 同款)
SLICE_EV = HERE.parent / ".work" / "rm04" / "async"

WARN_TEXT = "已受理: 同机探测进行中 1 项, 探测结论到达后自动续跑"
CONSUME_MARK = "probe verdict 消费"
ISSUE_MARK = "迁移发起"
# FS 不可达方向的两个失败 reason 都 env=False(可缓存): 证写轮询超时(dst 未出现)与
# dst 已出现但源未消失(= qB 只复制未搬走, relocate_probe._write_proof_poll 两出口)
FAIL_REASONS = ("write_proof_timeout", "write_mismatch")


def _flush(ev: dict, tag: str) -> None:
    """证据落盘: 断言现场 + 产品日志副本, 时刻后缀防覆写。取证失败如实带错不掩盖主断言。"""
    ev["ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        SLICE_EV.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        (SLICE_EV / f"{tag}_evidence_{stamp}.json"
        ).write_text(json.dumps(ev, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    except Exception as e:  # noqa: BLE001 —— 取证失败不影响主断言
        print(f"[evidence] 写盘失败: {e!r}", file=sys.stderr, flush=True)


def _flush_log(p, tag: str) -> None:
    try:
        log = p.log() if p is not None else ""
        SLICE_EV.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        (SLICE_EV / f"{tag}_auto-qb_{stamp}.log").write_text(log, encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        print(f"[evidence] 日志副本失败: {e!r}", file=sys.stderr, flush=True)


def _guard_online() -> None:
    """开工闸: 双实例端口白名单 + connection_status 非 disconnected(假红陷阱, 计划 §3.2)。"""
    for port in (instances.PRIMARY, instances.SECONDARY):
        guard.check_port(port)
        status = guard.check_online(instances.make(port))
        assert status != "disconnected", f"{port} connection_status=disconnected(假红陷阱), 拒跑"


def _subdir_group(qb, src: Path, salt: str, pack: str):
    """多文件子目录布局组(2 成员, 共享物理文件): 内容根下只有目录子项 -> D 级不可判 ->
    B' 弱证据 -> 探测闸真实命中(计划 §4.2 拓扑前提)。返回 (h1, h2, files)。"""
    files = [(f"{pack}/sub/a.bin", 256 * 1024), (f"{pack}/sub/b.bin", 128 * 1024)]
    h1 = M.fake_multi(qb, pack, files, src, salt, write=True)  # 数据只写这一份
    h2 = M.fake_multi(qb, pack, files, src, salt, piece_len=32768, write=False)
    assert h1 != h2, "两成员 infohash 撞车(必须同文件异 infohash)"
    return h1, h2, files


def _wait_probe_gone(qb) -> None:
    """等探测种子自清理(TAG_PROBE 零残留; 探测 finally 自带 deleteFiles, 这里只核验)。"""
    M.wait_until(lambda: not [t for t in qb.torrents() if TAG_PROBE in M._tags_of(t)], 30, "探测种子未自清理(TAG_PROBE 残留)")


def _purge_probe_torrents(qb) -> list:
    """TAG_PROBE 兜底清扫: 遍历实例内探针种子逐个 delete(delete_files=True), 返回删掉的 hash 前 8 位。

    预检/主探测失败路径探测线程未跑完自清即被红时防种子残留(否则会把后续用例的残留断言
    打成假红); 调用方负责容错聚合(批B复评 #1, 与 RM04-35 B 腿 finally 收尾同构)。
    """
    gone = []
    for t in qb.torrents():
        if TAG_PROBE in M._tags_of(t):
            qb.delete(t["hash"], delete_files=True)
            gone.append(t.get("hash", "")[:8])
    return gone


def _sweep_probe_torrents(ev: dict, errs: list) -> None:
    """TAG_PROBE 兜底清扫 + 核净 + 留证(RM04-35/36/37 三处外层 finally 共用; 批B第3轮复评 #1)。

    预检/受理/主探测失败路径探测线程未跑完自清即被红时防种子残留(daemon 线程随测试会话
    退出被杀/产品强停进程内线程随死), 否则会把后续用例(RM04-36/37)的残留断言打成假红;
    qB 不可达时不掩盖原始失败, 异常聚合进 errs 留证。
    """
    try:
        swept = _purge_probe_torrents(M.qbfake())
        if swept:
            M.wait_until(
                lambda: not [t for t in M.qbfake().torrents() if TAG_PROBE in M._tags_of(t)], 15, "TAG_PROBE 兜底清扫后仍有残留"
            )
        ev["probe_torrent_sweep"] = swept
    except Exception as e:  # noqa: BLE001 —— 兜底失败聚合留证, 不掩盖原始失败
        ev["probe_torrent_sweep_error"] = repr(e)
        errs.append(f"TAG_PROBE 兜底清扫失败: {e!r}")


def _probe_ctx(port: int):
    """模块直连 ctx(RM04-11/12 同款形态): 真 Client + 真 TorrentStore + 真 state 容器 +
    产品 RelocateConfig(enabled + bt_backup 实路径)。state 用独立 SimpleNamespace(data={}),
    与产品 state 服务零共享(模块直连无周期落盘, 断言只读内存面)。"""
    conf = QbittorrentConfig(host="127.0.0.1", port=port)
    client = new_client(conf)
    client.auth_log_in()
    store = TorrentStore(client)
    api = QbApi(client, store)
    bt_backup = Path(guard.EXE[port]).parent / "profile" / "qBittorrent" / "data" / "BT_backup"
    assert bt_backup.is_dir(), f"BT_backup 派生路径失效(EXE={guard.EXE[port]}): {bt_backup}"
    rel_conf = RelocateConfig(enabled=True, bt_backup=bt_backup.as_posix())
    ctx = SimpleNamespace(
        api=api,
        store=store,
        state=SimpleNamespace(data={}),
        config=SimpleNamespace(qbittorrent=conf, relocate=rel_conf),
        dry_run=False,
    )
    return ctx, client


def _find_probe_file(root: Path):
    """root 直下找 aqb-probe-*/aqb-probe-*.bin(命中返回探针文件路径, 否则 None)。"""
    if not root.is_dir():
        return None
    for d in root.iterdir():
        if d.is_dir() and d.name.startswith(PROBE_DIR_PREFIX):
            bins = list(d.glob("aqb-probe-*.bin"))
            if bins:
                return bins[0]
    return None


def _probe_residue(qb, roots: list) -> dict:
    """探针残留面盘点(qB TAG_PROBE 种子 + 各根下 aqb-probe-* 目录)。"""
    dirs = []
    for r in roots:
        rp = Path(r)
        if rp.is_dir():
            dirs += [p.name for p in rp.iterdir() if p.name.startswith(PROBE_DIR_PREFIX)]
    return {
        "tag_probe_torrents": [t.get("hash", "")[:8] for t in qb.torrents() if TAG_PROBE in M._tags_of(t)],
        "probe_dirs": dirs
    }


# ================================================================ RM04-35


def test_rm04_35_probe_gate_dry_run_smoke(secondary, workdir):
    """[RM04-35] 探测闸 dry-run 分支冒烟 + 非 dry-run 受理对照(断言明细见模块 docstring 测试计划)

    前置: 双实例在线 + 副实例无 real-fake 残留 + 2 枚子目录布局假种子成组校验完成。
    副作用: 副实例 2 枚假种子(连数据删); B 腿一次真探测(自建探针种子, 自清理)。
    回滚: real-fake 删净(连数据) + case 树删净 + TAG_PROBE/aqb-probe 零残留核验。
    失败判据: A 腿任一 note 缺失/cls 非 ok/出现 probing 键/save_path 被动/探针残留;
              B 腿未出现「探测中」受理或 verdict 未达(30s); 收尾槽/pending/队列未清。
    """
    case = M.case_dir("rm04_35")
    ev: dict = {"case": str(case)}
    b_module = None  # 批B #5: B 腿受理面收尾(移入 finally)的状态哨兵
    b_runner = None
    qb = M.qbfake()
    src = case / "src"
    dst_a = case / "dst_a"
    dst_b = case / "dst_b"
    try:
        assert not M.rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
        _guard_online()
        h1, h2, files = _subdir_group(qb, src, "rm04c35", "rm04c35pack")
        M.wait_complete(qb, [h1, h2], 120)
        ev["seeds"] = {"h1": h1[:8], "h2": h2[:8], "files": [list(f) for f in files]}

        ctx, client = _probe_ctx(instances.SECONDARY)
        client_tors = list(client.torrents_info())
        ctx.store.refresh(client_tors)  # 真记录入 store(relocate_execute 的组拆分数据源)
        module = RelocateModule(ctx)
        ev["ctx"] = {"store_records": len(client_tors), "bt_backup": ctx.config.relocate.bt_backup}

        # ---- A 腿: dry-run(产品 dry-run 真实进入点 = start 期透传, 单测 :274 同款入口升真机)
        module._dry = True
        items = module.relocate_execute([h1, h2], str(dst_a), confirm=True)
        assert len(items) == 1, f"A 腿回执条数不符: {json.dumps(items, ensure_ascii=False)[:600]}"
        it = items[0]
        assert it.get("cls") == "ok", f"A 腿 cls 非 ok(闸/预检分支漂移): {json.dumps(items, ensure_ascii=False)[:600]}"
        notes = [str(n) for n in (it.get("notes") or [])]
        assert any("dry-run: 跳过强探测" in n for n in notes), f"notes 缺「dry-run: 跳过强探测」: {notes}"
        assert any("dry-run: 未下发搬迁" in n for n in notes), f"notes 缺「dry-run: 未下发搬迁」: {notes}"
        assert it.get(ru.PROBE_GATE_PROBING_KEY) is not True, "dry-run 却出现 probing 判别键(结构性不应出现)"
        ev["A_dry_run"] = {"cls": it.get("cls"), "notes": notes, "job_id": it.get("job_id")}
        # dry-run 下 job 账仍登记(产品现行行为, relocate_exec.py:2328-2337 先登记 :2339 才早退)——
        # 记录不断言; 零副作用断言落在 qB 面(setLocation 未下发)
        ev["A_job_ledger_registered"] = sorted((ctx.state.data.get("relocate") or {}).get("jobs") or {})

        # ---- A 腿零副作用: qB save_path 不动 + 零探针痕 + 缓存/pending 空
        for h in (h1, h2):
            cur = qb.torrent(h) or {}
            assert M.norm(cur.get("save_path")) == M.norm(src), \
                f"dry-run 却动了 save_path: {h[:8]} -> {cur.get('save_path')}"
        res = _probe_residue(qb, [src, dst_a])
        assert res["tag_probe_torrents"] == [] and res["probe_dirs"] == [], f"A 腿探针残留: {res}"
        box = (ctx.state.data.get("relocate") or {})
        assert not (box.get("probes") or {}), f"dry-run 却写了探测缓存: {box.get('probes')}"
        assert not (box.get("probe_pending") or []), f"dry-run 却入了探测意图: {box.get('probe_pending')}"
        ev["A_zero_side_effect"] = {"residue": res, "probes": 0, "probe_pending": 0}
        _flush(ev, "rm04_35_A")

        # ---- B 对照腿(L3 红验): 同拓扑关掉 dry-run -> 必须真实受理(证明 A 腿分支承重)
        # 独立 ctx/module: A 腿 dry-run 在旧 ctx 里登记了 moving 相位的 job 账(产品行为),
        # 会对同组再迁移触发 GATE_UNFINISHED(relocate_units.py:983-1002)—— B 腿用全新
        # state/job 账, 只隔离 job 面, 探测 runner(PROBE_SLOT/PROBE_VERDICT_QUEUE)仍是
        # 模块级单例, 与产品同款。
        ctx_b, client_b = _probe_ctx(instances.SECONDARY)
        client_b_tors = list(client_b.torrents_info())
        ctx_b.store.refresh(client_b_tors)
        module_b = RelocateModule(ctx_b)
        b_module, b_runner = module_b, module_b._active_probe_runner()  # 批B #5: finally 收尾引用
        items_b = module_b.relocate_execute([h1, h2], str(dst_b), confirm=True)
        assert len(items_b) == 1, f"B 腿回执条数不符: {json.dumps(items_b, ensure_ascii=False)[:600]}"
        itb = items_b[0]
        assert itb.get("cls") == "blocked", \
            f"B 腿未走探测闸(cls={itb.get('cls')}): 拓扑前提失效或缓存误命中: {json.dumps(items_b, ensure_ascii=False)[:600]}"
        assert itb.get(ru.PROBE_GATE_PROBING_KEY) is True, \
            f"B 腿 blocked 但非「探测中」受理: {json.dumps(items_b, ensure_ascii=False)[:600]}"
        pending = (ctx_b.state.data.get("relocate") or {}).get("probe_pending") or []
        assert len(pending) == 1, f"probe_pending 条数不符: {pending}"
        fp_in_flight = b_runner.slot().in_flight()
        assert fp_in_flight, "单飞槽未被占(探测线程没起)"
        assert pending[0].get("fingerprint") == fp_in_flight, "pending 指纹与在飞槽不一致"
        ev["B_accept"] = {"cls": itb.get("cls"), "probing_key": True, "fingerprint": fp_in_flight[:8], "pending": 1}

        # ---- B 腿 verdict: daemon 线程真探测(模块直连无消费线, 测试侧从结果队列取)
        fp, verdict = b_runner.verdict_queue().get(timeout=30)
        assert verdict.status == "passed", f"B 腿探测未通过: {verdict.status}/{verdict.reason} {verdict.evidence}"
        assert verdict.reason == "ok" and verdict.env is False, \
            f"B 腿 verdict 形态不符: {verdict.status}/{verdict.reason} env={verdict.env}"
        assert verdict.evidence.get("write_ok") is True, f"B 腿证写未过: {verdict.evidence}"
        assert fp == fp_in_flight, "verdict 指纹与受理指纹不一致"
        ev["B_verdict"] = {
            "status": verdict.status,
            "reason": verdict.reason,
            "elapsed_s": verdict.evidence.get("elapsed_s")
        }
        _wait_probe_gone(qb)  # 探测 finally 自清理核验
        res = _probe_residue(qb, [src, dst_b])
        assert res == {"tag_probe_torrents": [], "probe_dirs": []}, f"B 腿探针残留: {res}"
        for h in (h1, h2):
            cur = qb.torrent(h) or {}
            assert M.norm(cur.get("save_path")) == M.norm(src), \
                f"受理窗内 save_path 被动(probing != started 失守): {h[:8]}"
        ev["B_cleanup_ok"] = res
        _flush(ev, "rm04_35_B")
        # (批B #5: 主路径不做受理面收尾 —— pending/slot/队列清理移入 finally)
    finally:
        errs: list[str] = []
        if b_module is not None:
            # ---- 批B #5: B 腿受理面测试侧收尾(按受理状态容错: 未受理/verdict 未到时各步自然
            #      空转; slot release 在测试进程单例槽上幂等, 探测线程仍在飞时其 verdict 由下方
            #      排空兜走, 不留跨用例残留)
            try:
                popped = b_module.probe_pending_pop()
                b_runner.slot().release()
                drained = 0
                try:
                    while True:
                        b_runner.verdict_queue().get_nowait()
                        drained += 1
                except queue.Empty:
                    pass
                assert b_runner.slot().in_flight() is None, "收尾后单飞槽未空闲"
                ev["Z_test_side_cleanup"] = {
                    "pending_popped": popped is not None,
                    "queue_drained": drained,
                    "slot_free": True
                }
                _flush(ev, "rm04_35_Z")
            except Exception as e:  # noqa: BLE001 —— 收尾失败聚合重抛, 不静默
                errs.append(f"B 腿测试侧收尾失败: {e!r}")
        try:
            gone = M.rm_all_fakes(M.qbfake())
            ev["seeds_removed"] = gone
        except Exception as e:  # noqa: BLE001 —— 收尾失败聚合重抛, 不静默
            errs.append(f"real-fake 清理失败: {e!r}")
        _sweep_probe_torrents(ev, errs)  # 批B第3轮复评 #1: B 腿 verdict 超时红时 daemon 线程未自清
        try:
            M.purge_tree(case)
        except Exception as e:  # noqa: BLE001
            errs.append(f"case 清理失败: {e!r}")
        _flush(ev, "rm04_35_final")
        if errs:
            raise AssertionError(f"收尾未净(Z): {'; '.join(errs)}")


# ================================================================ RM04-36


def test_rm04_36_probe_accept_warn_full_chain(secondary, workdir):
    """[RM04-36] 受理段 warn 全链(产品进程, WEB 全链; 断言明细见模块 docstring 测试计划)

    前置: 双实例在线 + 副实例无 real-fake 残留 + 产品进程(relocate.enabled, WEB 开)。
    副作用: 2 枚假种子(连数据删); qB 真搬迁(用例目录内 src -> dst); state 落 job/缓存账。
    回滚: 产品进程停止(AppProc.stop) + real-fake 删净 + case 树删净(链接不递归删穿)。
    失败判据: 回执直接 started(闸被绕过/缓存误命中)或 blocked; warn 文案/summary 桶形不符;
              无消费日志; 续跑不发生; 终态补发未覆盖同 cmd_id; job 不终态(90s); 探针残留。
    """
    case = M.case_dir("rm04_36")
    ev: dict = {"case": str(case)}
    p = None
    try:
        qb = M.qbfake()
        assert not M.rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
        _guard_online()
        cfg, web_port = M.write_cfg(case, relocate=True)  # alias_threshold 默认 8: 2 文件 -> 逐文件链接, 免确认
        p = app.start(cfg, case)
        assert p.wait_web(40), f"WEB 没起来:\n{p.log()[-800:]}"
        assert p.wait_log("整组迁移已启用", 20), f"relocate 启动日志缺失:\n{p.log()[-600:]}"

        src = case / "src"
        dst = case / "dst"
        h1, h2, files = _subdir_group(qb, src, "rm04c36", "rm04c36pack")
        M.wait_complete(qb, [h1, h2], 120)
        assert M.wait_group(web_port, h1, {h1, h2}, 30, "两成员未成组(前提不成立)")
        M.wait_store_progress(web_port, [h1, h2])  # 闸门读产品快照, 等 1-2 个同步拍追平
        ev["seeds"] = {"h1": h1[:8], "h2": h2[:8]}

        # ---- 前提自证: 只读预检必须判「未证明 -> 执行时一次性强探测」(拓扑前提不成立显式红)
        pre = M.cmd_post_and_wait(
            web_port, "/api/torrents/relocate/precheck", {
                "hashes": [h1],
                "location": str(dst)
            }, timeout=30
        )
        pre_items = ((pre or {}).get("truth") or {}).get("results") or []
        pre_notes = [str(n) for it in pre_items for n in (it.get("notes") or [])]
        assert any("一次性强探测" in n for n in pre_notes), \
            f"前提自证失败(预检未判一次性强探测, 探测闸不会命中): {json.dumps(pre_items, ensure_ascii=False)[:600]}"
        ev["premise_precheck"] = {"notes": pre_notes}

        # ---- A1 受理段: warn 回执(探测闸未命中 -> 意图入队 + 单飞 kick, 门禁不搬数据)
        issued_before = M.count_anchor(case, ISSUE_MARK)
        t_post = time.monotonic()
        cmd_id, result = post_cmd(
            web_port, f"/api/torrents/{h1}/location", {
                "location": str(dst),
                "confirm": True
            }, timeout=30
        )  # 批B #1: cmd_id 取自 POST 入队响应(两段式); 终态补发覆盖面 = 同 cmd_id 二次写(set_result 覆盖语义)
        t_warn = time.monotonic()
        assert result.get("status") == "warn", \
            f"A1 回执非 warn(status={result.get('status')}): {json.dumps(result, ensure_ascii=False)[:600]}"
        assert WARN_TEXT in str(result.get("error") or ""), \
            f"A1 warn 文案不符: {result.get('error')!r}"
        summary = ((result or {}).get("truth") or {}).get("summary") or {}
        assert summary.get("probing") == 1 and summary.get("started") == 0, f"A1 summary 桶形不符: {summary}"
        ev["A1_warn"] = {
            "status": result.get("status"),
            "text": str(result.get("error") or "")[:160],
            "summary": summary,
            "cmd_id": cmd_id[:8],
            "latency_s": round(t_warn - t_post, 2)
        }
        _flush(ev, "rm04_36_A1")

        # ---- A2 受理窗内零执行(probing != started): 消费日志出现前「迁移发起」不增
        # 无竞态取法: 消费日志行先于重放的「迁移发起」落盘(产品序: relocate_exec.py:169 先于
        # :191 重放), 把单次读到的日志在消费行处切前缀, 前缀内计数即受理窗真值(不受
        # 「读日志与重放落盘竞速」影响)。
        def _consume_line():
            log = M.log_text(case)
            idx = log.find(CONSUME_MARK)
            return log[idx:] if idx >= 0 else None

        consumed = M.wait_until(_consume_line, 40, "verdict 消费日志未出现(A3)")
        log_now = M.log_text(case)
        idx = log_now.find(CONSUME_MARK)
        assert idx >= 0, "消费日志行消失(日志被轮转?)"
        assert log_now[:idx].count(ISSUE_MARK) == issued_before, \
            "受理窗内出现「迁移发起」(probing != started 失守)"
        ev["A2_no_issue_in_window"] = {"issued_before": issued_before}
        _flush(ev, "rm04_36_A2")

        # ---- A3 verdict 消费日志形态(passed 写缓存)
        assert "结论 passed/ok(缓存已写(passed))" in consumed, \
            f"A3 消费日志形态不符: {consumed[:300]}"
        ev["A3_consume_log"] = consumed[:220]

        # ---- A4 自动续跑: 消费后「迁移发起」出现 + 同 cmd_id 回执被终态补发覆盖为 ok(started)
        M.wait_until(lambda: M.count_anchor(case, ISSUE_MARK) > issued_before, 30, "verdict 消费后自动续跑未发生(无新「迁移发起」)")

        def _final_ok():
            r = M.web_req(web_port, "GET", f"/api/cmd/{cmd_id}")
            return r if r.get("status") == "ok" else None

        final = M.wait_until(_final_ok, 90, "终态补发未覆盖原 cmd_id 回执(90s)")
        assert final.get("status") == "ok", \
            f"A4 终态回执非 ok(status={final.get('status')}): {json.dumps(final, ensure_ascii=False)[:600]}"
        fsummary = (final.get("truth") or {}).get("summary") or {}
        assert fsummary.get("probing") == 0 and fsummary.get("started") == 1, f"A4 summary 桶形不符: {fsummary}"
        fitems = (final.get("truth") or {}).get("results") or []
        started = [it for it in fitems if it.get("cls") == "started"]
        assert started and started[
            0].get("job_id"), f"A4 started 明细缺 job_id: {json.dumps(fitems, ensure_ascii=False)[:600]}"
        job_id = started[0].get("job_id")
        ev["A4_final_receipt"] = {"status": final.get("status"), "summary": fsummary, "job_id": job_id}
        _flush(ev, "rm04_36_A4")

        # ---- A5 迁移终态: mover 落 dst + 数据对齐 + member2 助推后 done(finalized)
        for rel, size in files:
            f = dst / rel
            M.wait_until(
                lambda f=f, size=size: f.is_file() and f.stat().st_size == size, 60, lambda f=f: f"dst 侧文件未对齐: {f}"
            )
        M.wait_until(
            lambda: M.norm((qb.torrent(h1) or {}).get("save_path")) == M.norm(dst), 60,
            lambda: f"mover save_path 未到 dst: {(qb.torrent(h1) or {}).get('save_path')}"
        )
        qb.set_location(h2, str(dst))  # member2 助推(RM04-05 同款: 收尾链等全员 save_path==dst)
        M.wait_until(
            lambda: M.norm((qb.torrent(h2) or {}).get("save_path")) == M.norm(dst), 30,
            lambda: f"member2 setLocation 未生效: {(qb.torrent(h2) or {}).get('save_path')}"
        )

        def _job_done():
            rel = (M.member_detail(web_port, h1) or {}).get("relocate") or {}
            return rel if rel.get("job_id") == job_id and rel.get("phase") == "done" else None

        job = M.wait_until(
            _job_done, 90, lambda: f"job {job_id} 未推进到 done: {(M.member_detail(web_port, h1) or {}).get('relocate')}"
        )
        assert job.get("reason") == "finalized", \
            f"job done 但 reason={job.get('reason')}(预期统一收尾 finalized): {job}"
        ev["A5_terminal"] = {
            "job_id": job_id,
            "phase": job.get("phase"),
            "reason": job.get("reason"),
            "save_path_h1": str(dst),
            "save_path_h2": str(dst)
        }
        _flush(ev, "rm04_36_A5")

        # ---- A6 指纹缓存(30s 周期落盘, 轮询等待; 相位/journal 不作断言源, 见 R7)
        def _cached_passed():
            box = _state_box(case)
            probes = box.get("probes") or {}
            return probes if any((v or {}).get("status") == "passed" for v in probes.values()) else None

        probes = M.wait_until(_cached_passed, 60, "state.json 未落 passed 探测缓存(30s 周期窗内)")
        ev["A6_cache"] = {"entries": len(probes), "status": "passed"}
        _flush(ev, "rm04_36_A6")

        # ---- 残留断言(批B #4): 探针种子与目录双空
        res36 = _probe_residue(M.qbfake(), [src, dst])
        assert res36 == {"tag_probe_torrents": [], "probe_dirs": []}, f"RM04-36 探针残留: {res36}"
        ev["residue_clean"] = res36
        _flush_log(p, "rm04_36")
    finally:
        errs: list[str] = []
        if p is not None:
            try:
                ev["stop_rc"] = p.stop(40)
            except Exception as e:  # noqa: BLE001
                errs.append(f"产品停止失败: {e!r}")
        _flush_log(p, "rm04_36_Z")
        try:
            ev["seeds_removed"] = M.rm_all_fakes(M.qbfake())
        except Exception as e:  # noqa: BLE001
            errs.append(f"real-fake 清理失败: {e!r}")
        _sweep_probe_torrents(ev, errs)  # 批B第3轮复评 #1: A1-A2 窗内红时产品强停, 进程内探测线程随死
        try:
            M.purge_tree(case)
        except Exception as e:  # noqa: BLE001
            errs.append(f"case 清理失败: {e!r}")
        _flush(ev, "rm04_36_final")
        if errs:
            raise AssertionError(f"收尾未净(Z): {'; '.join(errs)}")


def post_cmd(web_port: int, path: str, body: dict | None, timeout: float = 30.0):
    """两段式 WEB 命令(批B #1, rm09_webui_write 先例同款): POST 端点 200 只代表「入队」,
    入队响应 {queued, cmd_id} 是 cmd_id 的唯一来源 —— 结果回执 set_result 只存
    status/error/ts/timing/truth, 无 cmd_id 键。自投 POST 拿 cmd_id -> 轮询
    GET /api/cmd/{id} 到首个非 pending 回执, 返回 (cmd_id, 首个非 pending 回执)。

    轮询语义与 M.cmd_post_and_wait 同源, 差别只在返回 cmd_id(不改 M 既有函数)。
    """
    receipt = M.web_req(web_port, "POST", path, body)
    cmd_id = str(receipt.get("cmd_id") or "")
    assert receipt.get("queued") is True and cmd_id, \
        f"入队回执形状不对(缺 queued/cmd_id): {path} -> {json.dumps(receipt, ensure_ascii=False)[:300]}"

    def probe():
        r = M.web_req(web_port, "GET", f"/api/cmd/{cmd_id}")
        return r if r.get("status") != "pending" else None

    first = M.wait_until(probe, timeout, f"命令回执未落: {path}")
    return cmd_id, first


def _state_box(case: Path) -> dict:
    """state.json 的 relocate 段(只读; 坏/缺按空处理)。"""
    sp = case / "data" / "state.json"
    if not sp.is_file():
        return {}
    try:
        return ((json.loads(sp.read_text(encoding="utf-8")) or {}).get("relocate") or {})
    except (json.JSONDecodeError, OSError):
        return {}


# ================================================================ RM04-37


def test_rm04_37_fs_unreachable_behavioral_proxy(secondary, workdir):
    """[RM04-37] FS 不可达行为面代理(句柄锁造法; 断言明细见模块 docstring 测试计划)

    前置: 双实例在线 + 副实例无 real-fake 残留 + 产品进程 + 同拓扑组 + 第三枚种子(W2 靶)。
    副作用: 3 枚假种子(连数据删); 两次失败探测(预检造法验证 + 主探测, 均自建自清;
            探针目录残留测试侧显式删净(W7)+ 随 case 树清理(预检段)); state.relocate.probes 写入后测试侧停机态清理。
    回滚: 产品进程停止 + real-fake 删净 + case 树删净 + probes 键清理核验。
    失败判据: W1-W7 任一不满足(见模块 docstring); 造法预检不成立; 探针种子/目录残留。
    """
    case = M.case_dir("rm04_37")
    ev: dict = {"case": str(case)}
    p = None
    lock_fh = None
    try:
        qb = M.qbfake()
        assert not M.rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
        _guard_online()

        # ---- 开工预检(计划 §4.3 R1, 批B #2): 句柄锁造法先独立验证 —— 直调 run_probe
        #      (与 runner.run_inline 同款执行面: 独立 ctx 不经产品进程; 线程化以便测试侧并发上锁)
        #      对 56590 + 独立临时目录 + 句柄锁; 断言 failed/reason∈FAIL_REASONS/env=False,
        #      不成立即 pytest.fail BLOCKED(计划定案: 不硬闯不降级, 报告主会话)。
        pf_src = case / "preflight" / "src"
        pf_dst = case / "preflight" / "dst"
        pf_src.mkdir(parents=True)
        pf_dst.mkdir(parents=True)
        pf_ctx, _pf_client = _probe_ctx(instances.SECONDARY)
        pf_result: list = []
        pf_thread = threading.Thread(
            target=lambda: pf_result.append(run_probe(pf_ctx, str(pf_src), str(pf_dst))), daemon=True
        )
        pf_thread.start()
        pf_fh = None
        try:
            pf_file = M.wait_until(lambda: _find_probe_file(pf_src), 15, "预检: 15s 内未见探针文件落盘(探测没跑?)", interval=0.05)
            pf_fh = open(pf_file, "rb")  # noqa: SIM115 —— 预检造法本体, 本段 finally 关闭
            pf_thread.join(timeout=40)
            assert pf_result, "预检探测线程 40s 未返回(证写/清理预算超期, 环境异常)"
            pf_v = pf_result[0]
            if not (pf_v.status == "failed" and pf_v.reason in FAIL_REASONS and pf_v.env is False):
                pytest.fail(
                    "BLOCKED: 句柄锁造法在该 qB 版本不成立"
                    f"(verdict={pf_v.status}/{pf_v.reason} env={pf_v.env} "
                    f"evidence={json.dumps(pf_v.evidence, ensure_ascii=False)[:400]}) —— 计划 §4.3 R1: 不硬闯不降级"
                )
            ev["preflight"] = {"status": pf_v.status, "reason": pf_v.reason, "env": pf_v.env}
        finally:
            if pf_fh is not None:
                pf_fh.close()
        pf_res = _probe_residue(qb, [pf_src, pf_dst])
        assert pf_res["tag_probe_torrents"] == [], f"预检探针种子残留: {pf_res}"
        ev["preflight_residue"] = pf_res  # 目录残留(锁文件所在)随 case 树 finally 清理, 此处只核种子面
        _flush(ev, "rm04_37_preflight")

        cfg, web_port = M.write_cfg(case, relocate=True)
        p = app.start(cfg, case)
        assert p.wait_web(40), f"WEB 没起来:\n{p.log()[-800:]}"
        assert p.wait_log("整组迁移已启用", 20), f"relocate 启动日志缺失:\n{p.log()[-600:]}"

        src = case / "src"
        dst = case / "dst"
        solo = case / "solo"
        h1, h2, files = _subdir_group(qb, src, "rm04c37", "rm04c37pack")
        h3 = M.fake_with_data(qb, "rm04c37solo.bin", 256 * 1024, solo, "rm04c37s")  # W2 观测靶
        M.wait_complete(qb, [h1, h2, h3], 120)
        assert M.wait_group(web_port, h1, {h1, h2}, 30, "两成员未成组(前提不成立)")
        M.wait_store_progress(web_port, [h1, h2, h3])
        ev["seeds"] = {"h1": h1[:8], "h2": h2[:8], "h3": h3[:8]}

        # ---- 前提自证(同 RM04-36)
        pre = M.cmd_post_and_wait(
            web_port, "/api/torrents/relocate/precheck", {
                "hashes": [h1],
                "location": str(dst)
            }, timeout=30
        )
        pre_items = ((pre or {}).get("truth") or {}).get("results") or []
        pre_notes = [str(n) for it in pre_items for n in (it.get("notes") or [])]
        assert any("一次性强探测" in n for n in pre_notes), \
            f"前提自证失败: {json.dumps(pre_items, ensure_ascii=False)[:600]}"

        # ---- 受理: POST -> warn(造法窗口起点)
        issued_before = M.count_anchor(case, ISSUE_MARK)
        t_post = time.monotonic()
        t_post_epoch = time.time()  # W1 第二子句基准: 缓存条目 at = int(SystemClock.now()) = int(time.time())
        cmd_id, result = post_cmd(
            web_port, f"/api/torrents/{h1}/location", {
                "location": str(dst),
                "confirm": True
            }, timeout=10
        )  # 批B #1: cmd_id 取自 POST 入队响应(两段式); 结果回执无 cmd_id 键
        t_warn = time.monotonic()
        assert result.get("status") == "warn", \
            f"受理回执非 warn(status={result.get('status')}): {json.dumps(result, ensure_ascii=False)[:600]}"
        # W1 前半: POST -> warn <= 5s(旧同步形态 = 整窗 25-35s)
        warn_latency = t_warn - t_post
        assert warn_latency <= 5.0, f"W1 受理延迟 {warn_latency:.2f}s > 5s(旧版阻塞形态?)"
        ev["W1_warn"] = {"latency_s": round(warn_latency, 2), "cmd_id": cmd_id[:8]}
        _flush(ev, "rm04_37_W1")

        # ---- 句柄锁: 探针文件落盘即独占读句柄(Windows: 无 FILE_SHARE_DELETE)
        probe_file = M.wait_until(lambda: _find_probe_file(src), 10, "10s 内未见探针文件落盘(探测没跑?)", interval=0.05)
        lock_fh = open(probe_file, "rb")  # noqa: SIM115 —— 句柄即造法本体, finally 关闭
        t_lock = time.monotonic()
        ev["lock"] = {"probe_file": str(probe_file), "lock_after_post_s": round(t_lock - t_post, 2)}
        _flush(ev, "rm04_37_lock")

        # ---- W2 窗内主循环活性: 第三种子 pause 命令回执 <=8s 且 qB 态可见
        t_pause = time.monotonic()
        r_pause = M.cmd_post_and_wait(web_port, f"/api/torrents/{h3}/pause", None, timeout=8)
        pause_latency = time.monotonic() - t_pause
        assert r_pause.get("status") == "ok", \
            f"W2 pause 回执非 ok: {json.dumps(r_pause, ensure_ascii=False)[:400]}"
        M.wait_until(
            lambda: str((qb.torrent(h3) or {}).get("state") or "").startswith("stopped"), 8,
            lambda: f"W2 pause 未落到 qB: {(qb.torrent(h3) or {}).get('state')}"
        )
        assert pause_latency <= 8.0, f"W2 窗内命令延迟 {pause_latency:.2f}s > 8s(主循环停摆形态)"
        ev["W2_loop_alive"] = {"pause_latency_s": round(pause_latency, 2)}
        _flush(ev, "rm04_37_W2")

        # ---- W3 verdict 按窗期特征到达: POST 后 <=25s 消费日志(failed + 缓存已写(failed)
        def _consume_failed():
            log = M.log_text(case)
            for line in log.splitlines():
                if CONSUME_MARK in line and "failed/" in line and "缓存已写(failed" in line:
                    return line
            return None

        remain = max(1.0, 25.0 - (time.monotonic() - t_post))
        consume_line = M.wait_until(_consume_failed, remain, lambda: f"W3 消费日志未在窗内出现(剩余 {remain:.1f}s)")
        assert any(r in consume_line for r in FAIL_REASONS), \
            f"W3 失败 reason 不在 FS 不可达方向两态内: {consume_line[:300]}"
        ev["W3_consume"] = {"line": consume_line[:220], "post_to_consume_s": round(time.monotonic() - t_post, 2)}
        _flush(ev, "rm04_37_W3")

        # ---- W4 终态补发(D7-1): 同 cmd_id 被覆盖为 error, 文案含缓存 blocked 语义
        t_consume = time.monotonic()

        def _final_error():
            r = M.web_req(web_port, "GET", f"/api/cmd/{cmd_id}")
            return r if r.get("status") == "error" else None

        final = M.wait_until(_final_error, 15, "W4 终态补发未覆盖原回执(15s)")
        drain_latency = time.monotonic() - t_consume
        assert drain_latency <= 10.0, f"W4 补发延迟 {drain_latency:.2f}s > 10s"
        err_text = str(final.get("error") or "")
        assert "上次同机探测失败" in err_text and "已缓存" in err_text, \
            f"W4 文案缺 D7-1 语义: {err_text[:400]}"
        ev["W4_final"] = {
            "status": final.get("status"),
            "text": err_text[:200],
            "drain_latency_s": round(drain_latency, 2)
        }
        _flush(ev, "rm04_37_W4")

        # ---- W6 零迁移副作用(D5: passed 前零建账零 setLocation)
        assert M.count_anchor(case, ISSUE_MARK) == issued_before, "FS 不可达却出现「迁移发起」"
        assert not M.jobs_on_disk(case), f"W6 却落了 job 账: {list(M.jobs_on_disk(case))[:3]}"
        for h in (h1, h2):
            cur = qb.torrent(h) or {}
            assert M.norm(cur.get("save_path")) == M.norm(src), \
                f"W6 save_path 被动: {h[:8]} -> {cur.get('save_path')}"
        assert not list(dst.rglob("*.bin")), "W6 dst 出现组内容(搬迁发生)"
        ev["W6_zero_side_effect"] = {"issued_delta": 0, "jobs": 0, "dst_absent": True}
        _flush(ev, "rm04_37_W6")

        # ---- W5 缓存污染面: 30s 周期落盘后读 failed 条目留证 -> 停机态测试侧清理 probes 键
        def _cached_failed():
            probes = _state_box(case).get("probes") or {}
            hits = {k: v for k, v in probes.items() if (v or {}).get("status") == "failed"}
            return hits or None

        failed = M.wait_until(_cached_failed, 60, "W5 state.json 未落 failed 探测缓存(30s 周期窗内)")
        entry = next(iter(failed.values()))
        evd = entry.get("evidence") or {}
        assert str(evd.get("reason") or "") in FAIL_REASONS, f"W5 缓存 reason 形态不符: {evd}"
        # ---- W1 第二子句(计划 26-11-21-0223 §4.3 修正口径): 缓存条目 at(挂钟 epoch 秒, clock 单点)
        #      与受理 POST 时刻差 >=8s = 证写 10s 预算特征。failed 路径缓存无 elapsed_s
        #      (relocate_probe.py:451 仅 passed 路径写); at = probe_put 写缓存时刻
        #      (int(SystemClock.now()) = int(time.time()))。采样在本段: 缓存条目经 30s 周期落盘后才
        #      可读, 差值由探测窗时长决定, 与读取时刻无关。
        at_delta = float(entry.get("at") or 0) - t_post_epoch
        assert at_delta >= 8.0, \
            f"W1 缓存条目 at 与受理 POST 时刻差 {at_delta:.1f}s < 8s(证写预算特征不成立, 未真跑证写预算): entry={entry}"
        ev["W1_at_window"] = {"at_delta_s": round(at_delta, 1)}
        ev["W5_cache"] = {"reason": evd.get("reason"), "at": entry.get("at")}  # W5 留证 = evidence.reason + 条目 at
        p.stop(40)  # 停机态(常规停止; 数据已随 30s 周期落盘, 非优雅只省最后一笔 flush)
        p = None
        sp = case / "data" / "state.json"
        data = json.loads(sp.read_text(encoding="utf-8"))
        assert (data.get("relocate") or {}).get("probes"), "停机态 state 里 probes 箱缺失"
        data["relocate"]["probes"] = {}  # 主会话任务指定的清理手段: 测试侧停机态清指纹缓存
        sp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        assert not _state_box(case).get("probes"), "probes 键清理未生效"
        ev["W5_cleanup"] = {"probes_cleared": True}
        _flush(ev, "rm04_37_W5")

        # ---- W7 探针核净(批B #3): 关句柄 -> 测试侧显式删净两侧 aqb-probe-* 目录并断言删净
        #      (产品 _cleanup 持句柄期必失败不重试, 目录泄漏回归在此测出)-> TAG_PROBE 种子零残留
        lock_fh.close()
        lock_fh = None
        removed: list = []
        for root in (src, dst):
            if root.is_dir():
                for d in root.iterdir():
                    if d.is_dir() and d.name.startswith(PROBE_DIR_PREFIX):
                        shutil.rmtree(d)
                        removed.append(str(d))
        _wait_probe_gone(qb)
        res = _probe_residue(qb, [src, dst])
        assert res["tag_probe_torrents"] == [] and res["probe_dirs"] == [], \
            f"W7 探针残留(qB 种子或目录): {res}"
        ev["W7_probe_gone"] = {"residue": res, "test_side_removed": removed}
        _flush_log(p, "rm04_37")
    finally:
        if lock_fh is not None:
            try:
                lock_fh.close()
            except OSError:
                pass
        errs: list[str] = []
        if p is not None:
            try:
                ev["stop_rc"] = p.stop(40)
            except Exception as e:  # noqa: BLE001
                errs.append(f"产品停止失败: {e!r}")
        _flush_log(p, "rm04_37_Z")
        try:
            ev["seeds_removed"] = M.rm_all_fakes(M.qbfake())
        except Exception as e:  # noqa: BLE001
            errs.append(f"real-fake 清理失败: {e!r}")
        _sweep_probe_torrents(ev, errs)  # 批B复评 #1: 预检/主探测失败路径探测线程未自清的兜底(三处共用)
        try:
            M.purge_tree(case)
        except Exception as e:  # noqa: BLE001
            errs.append(f"case 清理失败: {e!r}")
        _flush(ev, "rm04_37_final")
        if errs:
            raise AssertionError(f"收尾未净(Z): {'; '.join(errs)}")
