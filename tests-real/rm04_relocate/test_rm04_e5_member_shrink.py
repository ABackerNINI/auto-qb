"""

同源声明: _write_cfg_fast_tick/_flush 与 test_rm04_e2_alias_add_pass.py /
test_rm04_offline_delete_settle.py 同源(函数体逐字一致, docstring/证据文件名前缀按用例本地化,
单侧改动须同步另两文件, 评审 R23 纪律); _readlink_norm 与 test_rm04_chain_gate_candidates.py
同源; _port_open 与 test_rm04_e2_alias_add_pass.py 同源(函数体逐字一致);
_await_wrapper_patched 复用 test_rm04_e2_alias_add_pass.py 同名单点(import 转发, 不另抄)。
[RM04-30] [E5] 成员收缩收敛: armed 态对成员「仅删除种子」-> 连续 3 拍权威缺席(R4 判据:
在线 + 快照非陈旧 + 增量轮删除上报证据) -> 从 job.hashes 收缩 + WARNING 留痕 + 反馈面 note
(「成员已删除,组账收缩」); 再逐个删光 -> 全删光 -> 空集核验通过 -> 删链门 -> 收尾 done、
别名删除; daemon 对缺失 fastresume 跳过记 settled 不失败。负向对照内建(L3): 组外种子删了
不得影响成员账(误收缩即红)/未删除的存活成员全程不被收缩(qB 同步抖动不得误判)。

计划 plans/26-11-17-0636-plan-real-rm04-relocate-refactor-verify.html §03.4 RM04-30 用例卡
(E5, 新建即 L3; 出处 0448 计划 R4)。断言面按 P4 判定账誊写(run_exp_p4.py 相 13/14/15:
E5-1 收缩收敛 + E5-daemon member_gone settled + E5-2 删光->空集->收尾)。

两腿切分(单测试函数, 各独立产品会话/case 目录, RM04-25 三腿同构):
- A 腿(E5 主链, 纯在线 —— 卡面主序, 副作用行「armed 期删种 1-3 枚」无离线窗): 三成员
  file_links 组 armed -> 组外异名种子删除(负向对照: 不得影响成员账) -> 逐个删成员
  (产品 WEB 仅删种子 = D16「去文件化」出口) -> 每次收缩断言(组账收缩 + WARNING + 反馈面
  note + 存活成员不被收缩) -> 全删光 -> 空集核验 -> 删链门(依赖清零) -> 收尾 done +
  别名删除。全程零离线窗(与 RM04-27 停机期删互补不重叠)。
- B 腿(E5-daemon, 收缩与改写账不一致配套): 双成员组 armed -> 删 mover(幸存非 mover 留
  src, 收尾窗保持)+ 收缩 -> D14 finalize-now -> 下线窗 daemon 改写: 被删成员 fastresume
  缺失(qB 5.2.3 删种即删, E5 前提)-> journal 改写账 status=member_gone(settled 收口,
  不计失败不重试), 存活成员正常 rewritten -> 重启 -> 核验 -> 删链门 -> done。「daemon 对
  缺失 fastresume 跳过不失败」须离线窗才可观测(P4 相 14 同款), A 腿纯在线流 daemon 不开窗,
  故立 B 腿承载; 幸存者若为 mover(已在 dst)收缩与核验同拍完成 job 即 done(首跑实锤),
  finalize-now 将回 blocked —— 「先删 mover」是 B 腿成立的前提。

main_tick 1S 纪律(片C 沉淀, 两腿共用): R4 收缩缺席判定一拍一判且只读当前轮 last_removed
(零变化轮即清空, 证据只存活一个同步轮 1.5S) —— main_tick 2S 会整拍错过删除轮(首跑实锤:
删除后 120s 无收缩行), 1S 拍 < 轮存活期 = 每轮必被判定, 收缩确定性发生。
「账面相位瞬态」取数面(片E 坑点): armed 期 journal 恒无文件(daemon 下线窗才写), 相位断言
走成员详情端点 relocate 相位与 chain 端点 finalize face, 不走 journal_of。
「磁盘账迟滞」取数面(片F 首跑实锤): state.json 按周期落盘(state_save_interval 配置端下限
30S, relocate_mod._persist 只写内存账, 真落盘由 state 服务 maybe_flush 负责) ——
jobs_on_disk 是最长 30S 迟滞的观测面, 只配终态等待(done/finalized 落账稳定后等 flush),
过程断言(收缩发生/存活成员不被收缩/相位)一律走 live 面: 收缩 WARNING 行(日志即时)+
chain 端点 finalize face(members_gone/note/phase 内存快照现取)+ 成员详情端点 relocate 相位;
P4 判定账自身也自注「state.json 的 job 相位随 state_save_interval 落盘, 有迟滞」(run_exp.py:987)。
「产品自选 mover」拓扑纪律(P4 G2 记录 + 片F 首跑实锤): mover 由产品自选(不必等于发起 hash,
RM04-34 三跑实锤同款), armed 后 mover 在 dst、非 mover 留 src —— 幸存成员若是 mover(已在
dst), 收缩与核验同拍完成 job 即 done(R4 G2 拓扑), 收尾窗立即退出; 两腿删除顺序一律
「先删 mover」: 幸存者恒为非 mover(在 src, at_dst=False 稳态), 收缩后 job 停在 armed WAIT,
A 腿逐拍收缩不断链、B 腿 finalize-now 才有窗口面可用。

L3 红验记录(新建即 L3, 计划 §08 片F; 负向对照内建):
- 负向 1(A 腿 S2): 删组外异名种子(带文件, 与成员无文件交集) -> 若收缩判据误把组外删除
  当成员缺席证据(R4 失守), 组账出现收缩/WARNING -> S2 的「组账零收缩 + WARNING 计数 0 +
  hashes 原样」断言红;
- 负向 2(A 腿 S3/S4): 每次收缩断言存活成员恰留在 job.hashes 且 WARNING 计数恰 +1(收缩行
  只点名被删成员) —— 若 qB 同步抖动/断连被误判成存活成员删除(R4「宁慢勿误删」失守),
  hashes 集合断言/计数断言红;
- 修复面无法在真机临时拆掉(产品码零改动红线), 红验以纯函数单测
  tests/test_relocate_units.py absence_shrink 表驱动(静默缺席不计数/证据缺席计数/门拍跳过)
  + 本用例 S2/S3/S4 正负向断言联合钉扎(单测证谓词, 真机证端到端行为), 与 RM04-25 A 腿
  红验方式同口径。

## 测试计划(单测试函数, 两腿 A/B + Z)
- G0 开工闸(共腿): R: 拓扑在 + 双实例在线(connection_status 非 disconnected) + 副实例无
  real-fake 残留; 产品起(旁路 runner, sentinel 优雅退出, fast tick, 阈值 8)。
- A1 造现场: 三成员共享文件组(file_links, 同名同内容异 piece_len x3)落 R: -> 齐完成 ->
  归组断言(恰含三成员) -> 搬迁 armed(WEB confirm 直投 -> started form=file_links +
  job_id -> 已武装收尾 -> symlink 指 dst) -> 产品账 mover 识别(详情端点 relocate.mover)。
- A3 负向对照(组外删除不误收缩): 组外异名种子 X 落旧根 -> 完成 -> qB 直删(带文件) ->
  等过 6+ 判定拍 -> 组账零收缩(WARNING 计数 0 + finalize face members_gone=False +
  相位仍 armed + 三成员全在 qB/组行原样)。
- A4 逐个删光(先删 mover + 三拍收缩 + 负向存活腿): 产品 WEB 删 mover(仅删种子) ->
  live 面断言收缩(WARNING 1 行点名 mover「剩余 2 个」+ finalize face members_gone=True +
  note 同文 + 相位仍 armed)+ 存活成员不被收缩(收缩行只点名被删者) -> 删非 mover 甲 ->
  收缩(WARNING 2 行「剩余 1 个」+ face 同步) -> 删非 mover 乙 -> 收缩(WARNING 3 行
  「剩余 0 个」)。
- A5 空集核验 -> 删链门 -> 收尾: 「收尾完成」行(删链门依赖清零 + 已在线删除别名)+ 磁盘账
  done/finalized(终态等待, 容 30S flush 迟滞)+ symlink 删除 + 纯在线流 daemon 零动作行。
- B1 造现场: 双成员共享文件组(file_links)落 R: -> armed(symlink 现场) + wrapper patch
  在位 + mover 识别。
- B2 删 mover + 收缩: 产品 WEB 删 mover(仅删种子) -> 收缩(WARNING 1 行「剩余 1 个」)+
  finalize face members_gone=True 且相位仍 armed(幸存非 mover 在 src = 收尾窗保持)。
- B3 立即收尾(D14) -> 下线窗: completion_on 基线 -> POST /api/relocate/finalize-now
  {confirm, job_id} -> cls=ok(关闭指令) -> 副实例端口关闭(产品发起优雅退出) -> 主实例
  real.down 补齐 -> journal: rewrites[mover].status=member_gone 且 fails=0(缺失 fastresume
  跳过记 settled 不失败)+ rewrites[幸存者] in {rewritten, already} + journal phase=rewritten
  (journal 由 daemon 直写文件, 不经 state.json 落盘节拍)。
- B4 重启 + 收敛: 双实例回在线 -> 幸存者落 dst(completion_on 等值 = 零 recheck, 健康面) ->
  删链门依赖清零 -> 「收尾完成」行 -> 磁盘账 done/finalized -> symlink 删除。
- Z 收尾(共腿): 产品优雅退出 -> 双实例恢复在线 -> real-fake 删净(连数据) -> BT_backup
  本腿哈希残留清除 + 逐文件比对开工快照 -> case 树与 R: 子树删净 + 别名 lstat 零残留。

前置: 环境1(R: 在, src=R:/qbt-fake/rm04/rm04_30/{a,b}/src 与 dst=D: 异盘) + 双测试实例
      在线(没起先 `commands run real.up -- --port <白名单端口>`); 副实例无 real-fake 残留;
      wrapper 名册窄化旁路在位(沿 RM04-20/21/27/28/34 授权, 零新增旁路面); 独占约 6-8
      分钟(A 腿在线流 + B 腿一次离线窗), conftest serial 锁串行保护。R: 缺席 => skip
      不回退落点(钉死口径)。
副作用: 两次真搬迁(mover 由 qB 原生搬 R:->D:)+ armed 期删种 5 枚(仅删种子不删文件: A 腿
      3 成员 + B 腿 1 成员 = 4 枚产品 WEB 删, 另组外异名 1 枚 qB 直删带文件)+ B 腿一次
      离线窗改写 + 双实例优雅下线/重启各一次(B 腿)+ state 账。
回滚: 产品优雅退出(sentinel 通路); 双实例恢复在线; real-fake 种子删净(连数据); BT_backup
      只清本用例哈希残留 + 逐文件比对开工快照(queue 豁免); case 树与 R:/qbt-fake/rm04/
      rm04_30 子树删净(purge_tree 不递归删穿链接); 别名 lstat 零残留。
失败判据: 收缩未发生或 N 拍判据错点(1S 拍下单次删除 60s 内无收缩行); WARNING/note 缺失或
      收缩行点名错成员; 组外删除误收缩存活成员(负向 1/2 任一红); daemon 对缺失 fastresume
      报失败(B 腿 member_gone 缺席/failed/fails>0); 全删光后收尾卡死(「收尾完成」缺席);
      收尾有残留。

跑法: `commands run real.run -- --case RM04-30 --yes`(不要裸 pytest)。
"""
from __future__ import annotations

import json
import socket
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_rm04_relocate as M  # noqa: E402  (复用 RM04 的造种/清场/断言助手)
import test_rm04_e2_alias_add_pass as E2  # noqa: E402  (复用片E 的旁路接线/收尾 helper; 同源面见其 docstring)

from lib import guard, instances  # noqa: E402
from auto_qb.core.modules import relocate_units as ru  # noqa: E402  (产品码: 相位/原因常量)
from auto_qb.infra import relocate_journal as rj  # noqa: E402  (REWRITE_FAILS_KEY 改写账失败计数键)

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="本片断言含 Windows 特有语义(symlink/优雅退出通路)"),
]

# 拓扑单点(钉死, 见模块 docstring; 两腿子树隔离): src 在 R: 内存盘
R_ROOT = Path("R:/qbt-fake/rm04")
SRC_A = R_ROOT / "rm04_30" / "a" / "src"
SRC_B = R_ROOT / "rm04_30" / "b" / "src"
FILE_SIZE = 1024 * 1024
OUTSIDER_SIZE = 256 * 1024
PIECE_LENS_A = (16384, 32768, 65536)  # 三颗成员: 同文件异 infohash 的区分面
PIECE_LENS_B = (16384, 32768)
OUTPIECE = 16384
SALT = "rm04c30"

# 复用片E 旁路面(单一实现, 不另抄)
_require_r_topology = E2._require_r_topology
start_bypass_app = E2.start_bypass_app
stop_lingering_product = E2.stop_lingering_product
qb_up = E2.qb_up
qb_down = E2.qb_down
bt_backup_snapshot = E2.bt_backup_snapshot
BT_BACKUP = E2.BT_BACKUP
_assert_healthy = E2._assert_healthy
_await_wrapper_patched = E2._await_wrapper_patched

# 片F 证据目录(任务口径: 逐案 evidence 落 tests-real/.work/rm04-sliceF/; 时刻后缀防覆写)
SLICE_EV = HERE.parent / ".work" / "rm04-sliceF"


def _flush(ev: dict, case: Path, tag: str) -> None:
    """证据落盘(gitignored .work/rm04-sliceF): 全量断言现场 + 产品日志副本, 时刻后缀防覆写。"""
    ev["ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
    SLICE_EV.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    (SLICE_EV / f"rm04_30_{tag}_evidence_{stamp}.json"
    ).write_text(json.dumps(ev, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    try:
        log = M.log_text(case)
    except Exception as e:  # noqa: BLE001 —— 取证失败如实带错, 不掩盖主断言
        log = f"<log read failed: {e!r}>"
    (SLICE_EV / f"rm04_30_{tag}_auto-qb_{stamp}.log").write_text(log, encoding="utf-8")


def _write_cfg_fast_tick(case: Path) -> tuple[Path, int]:
    """RM04-30 专用配置: 在 M.write_cfg 基础上把 main_tick 2S -> 1S(片C 沉淀派生)。

    R4 收缩缺席判定一拍一判且只读当前轮 last_removed(证据只存活一个同步轮 1.5S),
    main_tick 2S 会整拍错过删除轮(片C 首跑实锤: 删除后 120s 无收缩行); 1S 拍 < 轮存活期
    = 每轮必被判定, 收缩确定性发生。sync_interval 1.5S 不变。"""
    cfg, web_port = M.write_cfg(case, relocate=True, alias_threshold=8)
    text = cfg.read_text(encoding="utf-8")
    assert "main_tick: 2S" in text
    cfg.write_text(text.replace("main_tick: 2S", "main_tick: 1S"), encoding="utf-8")
    return cfg, web_port


def _shrink_lines(case: Path, job_id: str) -> list[str]:
    """本 job 的「组账收缩」WARNING 行(收缩事件本体留痕; 日志即时落盘 = live 面)。"""
    return [ln for ln in M.log_text(case).splitlines() if job_id in ln and "组账收缩" in ln]


def _wait_shrink_live(
    case: Path, web_port: int, job_id: str, gone: str, survivor: str, remaining: int, warn_n: int, timeout: float
) -> dict:
    """等一次收缩(live 观测面, 片F 首跑实锤: state.json 30S 周期落盘, 磁盘账不配过程断言):

    - WARNING 行计数达 warn_n 且末行点名被删成员、行内「剩余 remaining 个成员继续收尾」
      (WARNING 行本身携带完整收缩注记文本);
    - chain 端点 finalize face(内存快照现取): members_gone=True + note 与 WARNING 同文
      (反馈面透传) + 相位仍在收尾窗(job 未被同拍核验终结 = 幸存者非 mover 在 src 的拓扑证据)。
    负向存活腿内建: 收缩行只点名被删成员 —— 若 qB 同步抖动被误判成存活成员删除(R4 失守),
    点名面断言红。"""
    def probe():
        warns = _shrink_lines(case, job_id)
        if len(warns) < warn_n:
            return None
        last = warns[-1]
        if gone[:8] not in last or f"剩余 {remaining} 个成员继续收尾" not in last:
            return None
        fin = _finalize_face(web_port, survivor)
        if fin.get("members_gone") is not True or fin.get("phase") not in ("armed", "rewritten"):
            return None
        if f"剩余 {remaining} 个成员继续收尾" not in str(fin.get("note") or ""):
            return None
        return {"warn": last.split(": ", 2)[-1], "note": str(fin.get("note")), "phase": fin.get("phase")}

    return M.wait_until(
        probe, timeout, lambda: f"收缩未观测(live 面): gone={gone[:8]} survivor={survivor[:8]} "
        f"WARNING={len(_shrink_lines(case, job_id))}/{warn_n} "
        f"face={json.dumps(_finalize_face(web_port, survivor), ensure_ascii=False)[:200]}"
    )


def _product_delete(web_port: int, ih: str) -> dict:
    """产品 WEB 仅删种子(D16「去文件化」出口, delete_files=False 不拦 —— qbapi docstring 单点)。"""
    r = M.cmd_post_and_wait(web_port, f"/api/torrents/{ih}/delete", {"delete_files": False})
    assert (r or {}).get("status") == "ok", f"产品仅删种子失败({ih[:8]}): {json.dumps(r, ensure_ascii=False)[:400]}"
    return r


def _finalize_face(web_port: int, ih: str) -> dict:
    """收尾反馈面(GET /api/relocate/chain?hash= -> finalize; members_gone/note/phase 内存快照现取)。"""
    return (M.web_req(web_port, "GET", f"/api/relocate/chain?hash={ih}") or {}).get("finalize") or {}


def _mover_of(web_port: int, qb, members: list[str], dst: Path) -> str:
    """产品账 mover 识别(详情端点 relocate.mover 布尔位, 内存快照现取; 退路 = qB save_path==dst)。

    产品自选 mover 不必等于发起 hash(RM04-34 三跑实锤 + 片F 首跑实锤), 删除顺序依赖它:
    先删 mover 让幸存者恒为非 mover(在 src)—— 幸存者若为 mover, 收缩与核验同拍完成 job
    即 done(P4 G2 拓扑), A 腿逐拍收缩断链 / B 腿 finalize-now 回 blocked。"""
    for h in members:
        if ((M.member_detail(web_port, h) or {}).get("relocate") or {}).get("mover") is True:
            return h
    by_path = [h for h in members if M.norm((qb.torrent(h) or {}).get("save_path") or "") == M.norm(dst)]
    assert by_path, f"mover 识别失败(详情端点与 qB 落点双面均无): {members}"
    return by_path[0]


def _arm_group(web_port: int, p, qb, src: Path, dst: Path, names: tuple[str, ...], piece_lens: tuple[int, ...]):
    """造共享文件组 + armed(file_links): 返回 (members, job_id, link)。"""
    members = []
    for i, (name, pl) in enumerate(zip(names, piece_lens)):
        members.append(M.fake_with_data(qb, name, FILE_SIZE, src, SALT, piece_len=pl, write=(i == 0)))
    assert len(set(members)) == len(members), f"成员 infohash 撞车: {members}"
    M.wait_complete(qb, members, 120)
    M.wait_group(web_port, members[0], set(members), 30, "成员未归组")
    M.wait_store_progress(web_port, members, 60)
    result = M.cmd_post_and_wait(
        web_port, f"/api/torrents/{members[0]}/location", {
            "location": str(dst),
            "confirm": True
        }
    )
    item = M.one_started_item(result)
    assert item.get("form") == "file_links", f"形态非 file_links: {json.dumps(item, ensure_ascii=False)[:400]}"
    job_id = item.get("job_id")
    assert job_id, f"started 项缺 job_id: {json.dumps(item, ensure_ascii=False)[:400]}"
    assert p.wait_log("已武装收尾", 60), "未武装(日志锚缺失)"
    link = src / names[0]
    M.wait_until(lambda: M.reparse_kind(link) == "symlink" or None, 60, lambda: f"链接形态异常: {M.reparse_kind(link)}")
    return members, job_id, link


def _leg_cleanup(p, case: Path, subtree: Path, ev: dict, collected: set, snap_before: dict) -> list[str]:
    """单腿收尾(聚合失败不吞, RM04-25 同款): 产品退出 -> 删种子(连数据) -> BT_backup 清本腿哈希 -> 目录删净。"""
    errs: list[str] = []
    if p is not None:
        try:
            ev["stop_rc"] = p.stop(40)
        except Exception as e:  # noqa: BLE001
            errs.append(f"产品停止失败: {e!r}")
    _flush(ev, case, ev.get("leg", "leg"))
    for port in (instances.SECONDARY, instances.PRIMARY):
        try:
            qb_up(port)  # 环境还原: 双实例回在线(B 腿离线窗后; A 腿幂等)
        except Exception as e:  # noqa: BLE001
            errs.append(f"real.up {port} 恢复失败: {e!r}")
    try:
        ev["seeds_removed"] = M.rm_all_fakes(M.qbfake())
    except Exception as e:  # noqa: BLE001
        errs.append(f"real-fake 种子清理失败: {e!r}")
    try:
        removed = []
        for ih in collected:
            for suffix in (".fastresume", ".torrent", ".fastresume.bak", ".torrent.bak"):
                fp = BT_BACKUP / f"{ih}{suffix}"
                if fp.is_file():
                    fp.unlink()
                    removed.append(fp.name)
        now = bt_backup_snapshot()
        residue = [k for k in now if k not in snap_before and not any(k.startswith(ih) for ih in collected)]
        before_files = {k: v for k, v in snap_before.items() if (BT_BACKUP / k).is_file() and k != "queue"}
        changed = [k for k, v in before_files.items() if now.get(k) != v]
        ev["bt_backup"] = {"removed": removed, "residue": residue, "changed": changed}
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


def _port_open(port: int) -> bool:
    """TCP 端口探针(只测本机白名单端口; finalize-now 产品侧下线的关闭完成观测面)。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", int(port))) == 0


# ================================================================ RM04-30


def test_rm04_30_e5_member_shrink():
    """[RM04-30] E5 成员收缩收敛(A=主链在线流 / B=daemon member_gone settled; 断言明细见模块 docstring)

    前置: R: 在 + 双实例在线 + 副实例无 real-fake 残留; wrapper 收编入库版在位。
    副作用/回滚/失败判据: 见模块 docstring(四行契约)。
    """
    _require_r_topology()
    qb = M.qbfake()
    assert not M.rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
    assert BT_BACKUP.is_dir(), f"副实例 BT_backup 不在(env_registry EXE 派生路径失效?): {BT_BACKUP}"
    for port in (instances.PRIMARY, instances.SECONDARY):
        guard.check_port(port)
        status = guard.check_online(instances.make(port))
        assert status != "disconnected", f"{port} connection_status=disconnected(假红陷阱), 拒跑"
    qb_up(instances.SECONDARY)
    qb_up(instances.PRIMARY)

    snap_before = bt_backup_snapshot()
    agg_errs: list[str] = []

    # ============================================================
    # A 腿(E5 主链, 纯在线): 组外删除不误收缩 + 逐个删光 -> 空集核验 -> 删链门 -> done
    # ============================================================
    ev: dict = {"leg": "A_main_online"}
    p = None
    collected: set[str] = set()
    case = M.case_dir("rm04_30a")
    h1 = h2 = h3 = hx = None
    job_id = ""
    link = SRC_A / "rm04c30a.bin"  # finally 的别名零残留检查用(早退时按"建没建"如实判)
    try:
        M.purge_tree(SRC_A.parent)
        stop_lingering_product(case)  # 残留进程守卫(评审 R30; 异常终止后双产品共驱一 qB 污染面)
        cfg, web_port = _write_cfg_fast_tick(case)
        p = start_bypass_app(case, cfg)
        assert p.wait_web(45), f"WEB 没起来:\n{p.log()[-800:]}"
        assert p.wait_log("整组迁移已启用", 20), f"relocate 启动日志缺失:\n{p.log()[-600:]}"
        # ---- A1 造现场: 三成员共享文件组(file_links) armed + 产品账 mover 识别
        dst = case / "dst"
        members, job_id, link = _arm_group(web_port, p, qb, SRC_A, dst, ("rm04c30a.bin", ) * 3, PIECE_LENS_A)
        h1, h2, h3 = members
        collected |= set(members)
        mover = _mover_of(web_port, qb, members, dst)
        others = [h for h in members if h != mover]  # 非 mover 留 src(at_dst=False 稳态)
        m_sp = M.norm((qb.torrent(mover) or {}).get("save_path") or "")
        s_sp = M.norm((qb.torrent(others[0]) or {}).get("save_path") or "")
        assert m_sp == M.norm(dst), f"mover save_path 未落 dst: {m_sp}"
        assert s_sp == M.norm(SRC_A), f"非 mover save_path 异常(应留 src 经别名做种): {s_sp}"
        ev["A1_scene"] = {
            "members": [h[:8] for h in members],
            "mover": mover[:8],
            "mover_at": m_sp,
            "nonmover_at": s_sp
        }
        _flush(ev, case, "A1")

        # ---- A3 负向对照(组外删除不误收缩): 异名落旧根 -> qB 直删带文件 -> 组账零收缩
        hx = M.fake_with_data(qb, "rm04c30ax.bin", OUTSIDER_SIZE, SRC_A, SALT + "x", piece_len=OUTPIECE, write=True)
        collected.add(hx)
        M.wait_complete(qb, [hx], 120)
        qx = qb.torrent(hx) or {}
        assert M.norm(qx.get("save_path") or "") == M.norm(SRC_A), f"组外种子落点异常: {qx.get('save_path')}"
        qb.delete(hx, delete_files=True)  # 组外异名带文件直删(qB 侧; 与产品删面切分见 docstring)
        M.wait_until(lambda: True if qb.torrent(hx) is None else None, 30, "组外种子未从 qB 消失")
        time.sleep(6)  # 过 6+ 判定拍(1S 拍): 若误把组外删除当成员缺席证据, 收缩行必已出现
        warns = _shrink_lines(case, job_id)
        fin0 = _finalize_face(web_port, others[0])
        assert not warns, f"负向对照红(误收缩): 组外删除引发收缩 WARNING: {warns[-1:]}"
        assert fin0.get("members_gone") is not True, \
            f"负向对照红: 组外删除置 members_gone: {json.dumps(fin0, ensure_ascii=False)[:300]}"
        assert fin0.get("phase") == "armed", f"组外删除扰动 job 相位: {fin0.get('phase')}"
        cur = {t["hash"] for t in qb.torrents()}
        assert set(members) <= cur, f"负向对照红: 存活成员被组外删除波及出 qB: {[h[:8] for h in members if h not in cur]}"
        gx = M.group_row(M.groups_view(web_port), others[0])
        assert gx is not None and set(gx["members"]) == set(members), \
            f"负向对照红: 组行被组外删除扰动: {gx}"
        ev["A3_outsider_negative"] = {
            "outsider": hx[:8],
            "warns": 0,
            "members_gone": fin0.get("members_gone"),
            "phase": fin0.get("phase"),
            "group_intact": True
        }
        _flush(ev, case, "A3")

        # ---- A4 逐个删光(先删 mover + 三拍收缩 + 负向存活腿): 产品 WEB 仅删种子
        # 删 mover: 收缩 -> 剩 2 个非 mover(src), WARNING 1 行点名 mover「剩余 2 个」, 反馈面 note
        _product_delete(web_port, mover)
        M.wait_until(lambda: True if qb.torrent(mover) is None else None, 30, "mover 未从 qB 消失")
        live1 = _wait_shrink_live(case, web_port, job_id, mover, others[0], 2, 1, 60)
        w1 = _shrink_lines(case, job_id)
        assert others[0][:8] not in w1[-1] and others[1][:8] not in w1[-1], \
            f"存活成员被误点名(负向存活腿红): {w1[-1]}"
        ev["A4_shrink1"] = {
            "gone": mover[:8],
            "warn": live1["warn"][:120],
            "note": live1["note"][:120],
            "phase": live1["phase"]
        }
        _flush(ev, case, "A4a")

        # 删非 mover 甲: 收缩 -> 剩 1 个(存活成员负向腿), WARNING 2 行
        gone2 = others[0]
        _product_delete(web_port, gone2)
        M.wait_until(lambda: True if qb.torrent(gone2) is None else None, 30, "第二个成员未从 qB 消失")
        live2 = _wait_shrink_live(case, web_port, job_id, gone2, others[1], 1, 2, 60)
        w2 = _shrink_lines(case, job_id)
        assert mover[:8] not in w2[-1] and others[1][:8] not in w2[-1], \
            f"第二次收缩 WARNING 点名面漂移: {w2[-1]}"
        ev["A4_shrink2"] = {"gone": gone2[:8], "warn": live2["warn"][:120], "phase": live2["phase"]}
        _flush(ev, case, "A4b")

        # 删非 mover 乙: 收缩 -> 空集(同拍顺 VERIFY -> 删链门 -> 收尾), WARNING 3 行
        gone3 = others[1]
        _product_delete(web_port, gone3)
        M.wait_until(lambda: True if qb.torrent(gone3) is None else None, 30, "第三个成员未从 qB 消失")

        def shrink3_empty():
            w3 = _shrink_lines(case, job_id)
            if len(w3) >= 3 and gone3[:8] in w3[-1] and "剩余 0 个成员继续收尾" in w3[-1]:
                return w3
            return None

        M.wait_until(shrink3_empty, 60, lambda: f"空集收缩未观测: WARNING={len(_shrink_lines(case, job_id))}")
        ev["A4_shrink3"] = {
            "gone": gone3[:8],
            "warn": _shrink_lines(case, job_id)[-1].split(": ", 2)[-1][:120],
            "warn_total": 3
        }
        _flush(ev, case, "A4c")

        # ---- A5 空集核验 -> 删链门(依赖清零) -> 收尾 done + 别名删除
        M.wait_until(lambda: True if "收尾完成" in M.log_text(case) else None, 120, "收尾完成行未出现(全删光后收尾卡死?)")
        fin_line = [ln for ln in M.log_text(case).splitlines() if "收尾完成" in ln][-1]
        assert "删链门依赖清零" in fin_line and "已在线删除别名" in fin_line, f"收尾行语义不符: {fin_line}"

        def done_on_disk():
            job = M.jobs_on_disk(case).get(job_id) or {}
            return job if job.get("phase") == ru.PHASE_DONE and job.get("reason") == ru.REASON_FINALIZED else None

        M.wait_until(done_on_disk, 100, lambda: f"磁盘账未落 done/finalized: {M.jobs_on_disk(case).get(job_id)}")
        M.wait_until(lambda: True if not M._is_link(str(link)) else None, 60, "收尾后 symlink 未删除")
        # 纯在线流 daemon 不开窗: 语义由「在线删链门依赖清零」收尾行 + done/finalized 账面承证;
        # wrapper log 的 daemon 动作行结构性恒空(recycle_daemon 收口行走 logger 不进 wrapper log,
        # 评审 R31: 修前此面被当断言属恒真, P4 先例引用有误 —— 降级为证据面仅记录)
        daemon_lines = [ln for ln in E2.wrapper_lines() if job_id in ln and ("member_gone" in ln or "fastresume" in ln)]
        ev["A5_finalized"] = {
            "job": job_id,
            "log": fin_line,
            "alias_removed": True,
            "warn_total": len(_shrink_lines(case, job_id)),
            "daemon_lines": len(daemon_lines)
        }
        _flush(ev, case, "A5")
    except Exception as leg_err:  # noqa: BLE001 —— 单腿失败留证后聚合, 继续跑后续腿(FAIL 二分留现场)
        ev["leg_error"] = repr(leg_err)
        agg_errs.append(f"A 腿(主链在线流): {leg_err!r}")
    finally:
        agg_errs.extend(_leg_cleanup(p, case, SRC_A.parent, ev, collected, snap_before))

    # ============================================================
    # B 腿(E5-daemon): 删一枚 + 收缩 -> finalize-now -> 离线窗 member_gone settled -> 重启 -> done
    # ============================================================
    ev: dict = {"leg": "B_daemon_member_gone"}
    p = None
    collected: set[str] = set()
    case = M.case_dir("rm04_30b")
    job_id = ""
    link = SRC_B / "rm04c30b.bin"
    try:
        M.purge_tree(SRC_B.parent)
        stop_lingering_product(case)  # 残留进程守卫(同上)
        cfg, web_port = _write_cfg_fast_tick(case)
        p = start_bypass_app(case, cfg)
        assert p.wait_web(45), f"WEB 没起来:\n{p.log()[-800:]}"
        assert p.wait_log("整组迁移已启用", 20), f"relocate 启动日志缺失:\n{p.log()[-600:]}"
        wl0 = len(E2.wrapper_lines())
        # ---- B1 造现场: 双成员共享文件组(file_links) armed + mover 识别(先删 mover 纪律)
        dst = case / "dst"
        members, job_id, link = _arm_group(web_port, p, qb, SRC_B, dst, ("rm04c30b.bin", ) * 2, PIECE_LENS_B)
        collected |= set(members)
        mover = _mover_of(web_port, qb, members, dst)
        survivor = next(h for h in members if h != mover)  # 非 mover 留 src(at_dst=False 稳态)
        patched = _await_wrapper_patched(wl0, case)
        ev["B1_scene"] = {
            "members": [m[:8] for m in members],
            "mover": mover[:8],
            "survivor": survivor[:8],
            "job": job_id,
            "patched": patched[-1]
        }
        _flush(ev, case, "B1")

        # ---- B2 删 mover + 收缩(live 面): 幸存非 mover 在 src -> job 停在 armed 收尾窗
        _product_delete(web_port, mover)
        M.wait_until(lambda: True if qb.torrent(mover) is None else None, 30, "mover 未从 qB 消失")
        liveb = _wait_shrink_live(case, web_port, job_id, mover, survivor, 1, 1, 60)
        assert survivor[:8] not in liveb["warn"], f"幸存成员被误点名(负向存活腿红): {liveb['warn']}"
        ev["B2_shrink"] = {
            "gone": mover[:8],
            "kept": survivor[:8],
            "warn": liveb["warn"][:120],
            "phase": liveb["phase"]
        }
        _flush(ev, case, "B2")

        # ---- B3 立即收尾(D14) -> 离线窗: 被删成员 fastresume 缺失 -> member_gone settled
        comp_before = (qb.torrent(survivor) or {}).get("completion_on")
        assert comp_before is not None, "completion_on 取不到(基线取不到)"
        result_fn = M.cmd_post_and_wait(web_port, "/api/relocate/finalize-now", {"confirm": True, "job_id": job_id})
        assert (result_fn or {}).get("cls") == "ok", \
            f"finalize-now 回执非 ok(关闭指令未下达): {json.dumps(result_fn, ensure_ascii=False)[:500]}"
        assert "关闭指令" in str((result_fn or {}).get("note") or ""), \
            f"finalize-now note 语义不符: {(result_fn or {}).get('note')}"
        ev["B3_finalize_now"] = {"cls": (result_fn or {}).get("cls"), "note": (result_fn or {}).get("note")}
        _flush(ev, case, "B3a")
        M.wait_until(
            lambda: None
            if _port_open(instances.SECONDARY) else True, 60, "finalize-now 后副实例端口未关闭(产品未真正下发 app/shutdown?)"
        )
        qb_down(instances.PRIMARY)
        ev["B3_down"] = {"secondary_down": "by finalize-now(product)", "primary_down": "test-side real.down"}
        _flush(ev, case, "B3b")

        def window_settled():
            jr = M.journal_of(case, job_id) or {}
            rws = jr.get("rewrites") or {}
            if rws and (rws.get(mover) or {}).get("status") == "member_gone" \
                    and (rws.get(survivor) or {}).get("status") in ("rewritten", "already") \
                    and jr.get("phase") == "rewritten":
                return jr
            return None

        jr = M.wait_until(window_settled, 300, f"daemon 未在下线窗完成 member_gone/rewritten 收口(job={job_id})")
        rws = jr.get("rewrites") or {}
        rec1 = rws.get(mover) or {}
        rec2 = rws.get(survivor) or {}
        assert int(rec1.get(rj.REWRITE_FAILS_KEY) or 0) == 0, \
            f"member_gone 记了失败账(缺失 fastresume 未被跳过): {rec1}"
        assert int(rec2.get(rj.REWRITE_FAILS_KEY) or 0) == 0, f"存活成员改写记了失败账: {rec2}"
        # daemon 收口留痕(证据面, 不作断言门): wrapper 日志 member_gone 收口行(recycle_daemon 单点)
        gone_lines = [ln for ln in E2.wrapper_lines()[wl0:] if job_id in ln and "member_gone" in ln]
        ev["B3_window"] = {
            "m1_status": rec1.get("status"),
            "m1_fails": rec1.get(rj.REWRITE_FAILS_KEY),
            "m2_status": rec2.get("status"),
            "journal_phase": jr.get("phase"),
            "patched": patched[-1],
            "daemon_gone_lines": gone_lines[-2:]
        }
        _flush(ev, case, "B3c")

        # ---- B4 重启 + 收敛: 幸存者落 dst(零 recheck) -> 删链门依赖清零 -> done + 别名删除
        qb_up(instances.SECONDARY)
        qb_up(instances.PRIMARY)
        M.wait_until(
            lambda: M.norm((qb.torrent(survivor) or {}).get("save_path") or "") == M.norm(str(dst)) or None, 120,
            lambda: f"重启后幸存成员未落位 dst: {(qb.torrent(survivor) or {}).get('save_path')}"
        )
        _assert_healthy(qb, survivor, "存活成员")
        comp_after = (qb.torrent(survivor) or {}).get("completion_on")
        assert comp_after == comp_before, f"completion_on 变化 = 全量 recheck(改写链不该引发): {comp_before} -> {comp_after}"
        M.wait_until(lambda: True if "收尾完成" in M.log_text(case) else None, 180, "收尾完成行未出现(B 腿未收敛)")
        fin_line = [ln for ln in M.log_text(case).splitlines() if "收尾完成" in ln][-1]
        assert "删链门依赖清零" in fin_line and "已在线删除别名" in fin_line, f"收尾行语义不符: {fin_line}"

        def done_on_disk_b():
            job = M.jobs_on_disk(case).get(job_id) or {}
            return job if job.get("phase") == ru.PHASE_DONE and job.get("reason") == ru.REASON_FINALIZED else None

        M.wait_until(done_on_disk_b, 100, lambda: f"磁盘账未落 done/finalized: {M.jobs_on_disk(case).get(job_id)}")
        M.wait_until(lambda: True if not M._is_link(str(link)) else None, 60, "收尾后 symlink 未删除")
        ev["B4_finalized"] = {"job": job_id, "log": fin_line, "alias_removed": True}
        _flush(ev, case, "B4")
    except Exception as leg_err:  # noqa: BLE001
        ev["leg_error"] = repr(leg_err)
        agg_errs.append(f"B 腿(daemon member_gone): {leg_err!r}")
    finally:
        agg_errs.extend(_leg_cleanup(p, case, SRC_B.parent, ev, collected, snap_before))

    # ---- Z 总收尾: 别名 lstat 复核零残留 + 聚合两腿失败
    residue_links = [str(pp) for pp in (SRC_A / "rm04c30a.bin", SRC_B / "rm04c30b.bin") if M._is_link(pp)]
    assert not residue_links, f"两腿别名零残留失守: {residue_links}"
    ev["Z"] = {"alias_residue": residue_links, "legs": "A/B"}
    _flush(ev, M.WORK / "rm04_30a", "Z_summary")
    if agg_errs:
        raise AssertionError("RM04-30 两腿存在失败: " + " | ".join(agg_errs))
