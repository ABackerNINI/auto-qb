"""[RM04-23] 旧账迁移器三形态真机闭环(good/bad/restart): 重构版首次接管存量账时自动迁移
(S1b D8, relocate_mod._migrate_legacy_accounts)——

- good: 空 state 骨架 + 手工注入旧格式账(产品 RelocateJob 真实类构造, 照 RM04-21 配方;
  done 历史 + 在途 + 改道机器前任)后启动 -> 一条不丢(逐条字段对照)、新格式可读(job_from_dict
  全通)、状态行有迁移记录(「旧账迁移完成」WARNING + 备份目录) + model_version 盖章。
  **断言点(评审 R2 补): 旧格式部署须含 v7 顶层 bt_backup 表形态样本(config 旧形状), 断言
  v7->v8 迁移链把顶层表唯一非空条目搬运成 relocate.bt_backup 标量到位**(075dd418 触面)。
- bad: 故意损坏两条旧账(一条整值非 JSON 账形态的串值 / 一条缺 job_id 字段)不崩, 坏账隔离
  留痕(state.json 原样保留该两条)、好账照迁(好账迁移断言全数成立)。
- restart: 在途旧任务(phase=failed/armed_at==0)迁移后由启动对账接管续跑(RM04-21 的 B3-B6
  判据复用): 重入两行(逐笔 + 汇总)-> armed(armed_at>0)-> 外部完成(qB 原生 setLocation 跟进)
  -> 统一收尾 done(reason=finalized) + 删链门删净别名 + 组键归一 dst —— 收官/改指语义与 S1
  一致。**切分(不测三遍)**: daemon 离线窗改写非 mover fastresume 与重启落位(RM04-21 B4/B5)
  是 RM04-20/21 的专属断言面, 本用例不走旁路不做下线窗, 收尾走外部完成支(RM04-05 同款);
  qB 侧自检 skipped(未解析文件级 symlink)跳过面同样归 RM04-21(dir_alias 形态自检 POSITIVE
  不产生 skipped 行)。

计划 plans/26-11-17-0636-plan-real-rm04-relocate-refactor-verify.html §03.4 RM04-23 用例卡
(acc2; ca820f5f 旧账迁移器 + 075dd418 v7->v8 迁移链)。

形态选择: restart 腿用 dir_alias(junction, alias_threshold:1 + 子目录布局)而非 RM04-21 的
file_links —— dir_alias 的 qB 侧自检确定性 POSITIVE, armed 后可直接外部完成收尾, 不需要
daemon 离线窗旁路(RM04-20/21 专属授权面), 本用例零新增旁路。迁移器/对账判定表均形态无关
(物理现状判定: mover 在 dst + dst 内容全量在位)。

config v7 形态的构造纪律: 本用例模板里 schema_version 用占位符动态注入(不写
`schema_version: <数字>` 字面量)—— tests/test_real_schema_version_guard.py 扫 tests-real
全部 YAML/dict 字面量并要求等于现行版本; 本用例写旧版本章是**迁移测试的被测输入**(故意
触发 v7->v8 迁移链), 不是基座漂移, 动态构造让守卫只拦真漂移、不误伤迁移夹具。

## 测试计划(单测试函数, 三腿)
- G1 骨架: v8 配置短起停生成 state.json(接管面盖章空箱) -> 停机注入旧格式账(整盒重写:
  relocate = {jobs: {...}} 无 model_version) + 配置换写 v7 旧形状(顶层 bt_backup 表)。
- G2 迁移启动: 产品带 v7 配置 + 旧账启动 -> 断言 config v7->v8 搬运(日志 WARNING「旧表唯一
  非空条目已收编为单实例标量」+ 盘上 config.yml 已 v8 且 relocate.bt_backup=标量 + 顶层表
  键消失 + 版本号备份 config.yml.v7.bak 落盘)-> 断言旧账迁移(「旧账迁移完成: 1 个改道机器
  前任转 superseded 历史记录(接管关系归集 1 条)」+ model_version==1 + 三条账一条不丢 +
  前任转 superseded/dst 还原原始落点/superseded_from 退役字段摘除/继任 plan.inherited 归集
  条目 + extra_members 并入 + 无关 done 账逐字不动)-> job_from_dict 全通(新格式可读)+
  备份目录(relocate-migration-backup/<ts>/state.json)在位。
- B1 损坏注入: 同骨架 + 好账(前任/继任/done)再添两条坏账(串值 / 缺 job_id) -> 启动不崩
  (WEB 起 + 进程活 + 零 Traceback)-> model_version 盖章 + 好账迁移断言全数成立(前任转
  superseded/继任归集)-> 两条坏账在 state.json 原样保留(隔离留痕, 逐字对照注入值)。
- R1 在途接管: 真机现场(两颗共享文件假种子落 R: -> qB 原生 set_location 自搬 mover 到 dst
  -> src 内容根建 junction 且穿透可读)-> 注入 failed/armed_at==0 旧账(产品 RelocateJob
  真实类 + job_from_dict 回读校验, 整盒重写去 model_version)-> 产品重启 -> 启动对账重入两行
  (「启动对账重入(mover 已在 dst 且 dst 内容全量在位)」逐笔 + 「启动对账 1 笔: 重入 1 /
  保留 0」汇总)-> job 落 armed 且 armed_at>0 -> 外部完成(qB setLocation 跟进非 mover)->
  done(reason=finalized) + 「收尾完成」+ src junction 删净 + 组键归一 dst + 零异常态。
- R2 收尾: 产品优雅退出 -> 双实例恢复在线 -> real-fake 删净(连数据)-> BT_backup 本用例哈希
  残留清除 + 逐文件比对开工快照 -> case 树与 R:/qbt-fake/rm04/rm04_23 删净。

前置: 三腿共用双测试实例在线(没起先 `commands run real.up -- --port <白名单端口>`); 副实例
      无 real-fake 残留; restart 腿需 R: 在(环境1 D盘机, src=R:/qbt-fake/rm04/rm04_23/src
      与 dst=D: 异盘, fastresume 保存键绝对形态与 junction 拓扑同 RM04-20/21 口径), R: 缺席
      => restart 腿拓扑不成立 => 整条 skip 不回退落点(钉死口径, 不做环境自适应); good/bad
      腿零种子零 R: 依赖。独占约 3-5 分钟, conftest serial 锁串行保护。
副作用: 三次产品启停(各腿独立 case 目录); state.json relocate.jobs 迁移改写 + model_version
      盖章 + 迁移备份目录; config.yml v7->v8 改写落盘 + 版本号备份; 副实例加 2 枚 real-fake
      种子(restart 腿)且 mover 被 qB 原生搬 R:->D:; src 出现 junction 再被删链门删除; 副实例
      BT_backup 新增本用例哈希的 fastresume/torrent。
回滚: 产品优雅退出(骨架经 graceful_after 自发 SIGTERM; 三腿主启走 sentinel 优雅通路
      W.start_bypass_app, plain p.stop 是外部强杀(非优雅 rc=1, state 不优雅落盘), 优雅退出与 rc 断言走 sentinel 通路);
      双实例恢复在线; real-fake 种子删净(连数据); case 树与 R: 子树删净; BT_backup 只清
      本用例哈希残留 + 逐文件比对开工快照(queue 豁免); state/config 用例目录随 case 树删净,
      不碰仓库根 auto-qb-data/。
失败判据: 任一形态丢账(注入 N 条迁移后缺条); 坏账致产品启动崩/退出/Traceback; 在途账未被
      对账接管(无重入行或 armed_at 恒 0); 迁移后旧格式字段错位(前任 dst 未还原原始落点/
      继任缺归集条目/无关账字段漂移); config 迁移链未搬运(relocate.bt_backup 缺失或顶层表
      键残留或备份缺失); 重启后组裂/别名残留/出现 recheck 或 error/missing。

跑法: `commands run real.run -- --case RM04-23 --yes`(不要裸 pytest)。
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
import test_rm04_relocate_window as W  # noqa: E402  (BT_BACKUP 单点/qb_up/快照比对 helper 复用)

from lib import app, guard, instances  # noqa: E402
from auto_qb.infra import alias_fs  # noqa: E402  (产品码: 建链单点)
from auto_qb.core.modules import relocate_units as ru  # noqa: E402  (产品码: job 类与序列化)

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="本片断言含 Windows 特有语义(junction/优雅退出通路)"),
]

# 拓扑单点(钉死, 见模块 docstring; 与 RM04-20/21/22 的子树隔离): restart 腿 src 在 R: 内存盘
R_ROOT = Path("R:/qbt-fake/rm04")
SRC = R_ROOT / "rm04_23" / "src"
NAME = "rm04c23pack"
REL = f"{NAME}/data/f0.bin"
FILE_SIZE = 256 * 1024
PIECE_LENS = (16384, 32768)  # 同文件异 infohash 的区分面(两颗成员)
SALT = "rm04c23"

#: v7 旧形状的 schema 版本章(动态注入, 见模块 docstring「config v7 形态的构造纪律」)
V7 = 7

# 片B 证据目录(任务口径: 逐案 evidence 落 tests-real/.work/rm04-sliceB/)
SLICE_EV = HERE.parent / ".work" / "rm04-sliceB"

# v7 旧形状配置模板: 与 M.CONFIG_TEMPLATE 同骨架, 差异两处 —— schema_version 占位(动态注入
# V7) + relocate 段无 bt_backup 标量、顶层 bt_backup 多实例表(075dd418 收编前的形状)。
CFG_V7_TEMPLATE = """config:
    schema_version: {schema_version}
    qbittorrent:
        host: 127.0.0.1
        port: {qb_port}
        username: ""
        password: ""
    data_dir: "{data_dir}"
    main_tick: 2S
    sync_interval: 1.5S
    state_save_interval: 30S
    interval: 60S
    log:
        level: INFO
    grouping:
        enabled: true
    trackers:
        rm04fake:
            domains: ["{fake_host}"]
    relocate:
        enabled: true
        alias_file_threshold: 1
    bt_backup:
        "{qb_key}": "{bt_backup}"
    web:
        enabled: true
        host: 127.0.0.1
        port: {web_port}
        skip_local_verify: true
"""


def _flush(ev: dict, case: Path, tag: str) -> None:
    """证据落盘(gitignored .work/rm04-sliceB): 全量断言现场 + 产品日志副本。"""
    ev["ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
    SLICE_EV.mkdir(parents=True, exist_ok=True)
    (SLICE_EV / f"rm04_23_{tag}_evidence.json"
    ).write_text(json.dumps(ev, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    log = ""
    try:
        log = M.log_text(case)
    except Exception as e:  # noqa: BLE001 —— 取证失败如实带错, 不掩盖主断言
        log = f"<log read failed: {e!r}>"
    (SLICE_EV / f"rm04_23_{tag}_auto-qb.log").write_text(log, encoding="utf-8")


def _require_r_topology() -> None:
    try:
        SRC.parent.mkdir(parents=True, exist_ok=True)
        probe = SRC.parent / ".probe"
        probe.write_bytes(b"x")
        probe.unlink()
    except OSError as e:
        pytest.skip(f"R: 盘缺席/不可写, restart 腿跨盘拓扑(src R: vs dst D:)不成立 —— "
                    f"本用例钉死环境1 D盘机拓扑: {e}")


def _legacy_job(
    job_id: str, mover: str, extra_hash: str, src: str, dst_flip: str, dst_orig: str, alias_path: str
) -> dict:
    """改道机器前任旧账(产品 RelocateJob 真实类构造, 照 RM04-21 配方; 退役字段
    plan.superseded_from 为旧机器唯一落账证据, 经 job_to_dict 后补进 plan —— 该字段写入面
    已随改道机器物理删除, 新账永不携带, 只有旧格式账有)。"""
    job = ru.RelocateJob(
        job_id=job_id,
        hashes=(mover, extra_hash),
        mover=mover,
        src=src,
        dst=dst_flip,
        scope=src,
        alias_kind="file",
        alias_paths=(alias_path, ),
        phase=ru.PHASE_DONE,
        reason="",
        created_at=time.time(),
        armed_at=0.0,
        updated_at=time.time(),
        resume_hashes=(),
        attempts=0,
        last_error="",
        plan={
            "form": "file_links",
            "link_kind": "symlink",
            "scope": src,
            "files": [["a.bin", 1024]]
        },
        move_issued=True,
        tag_on=False,
        origin="web",
    )
    d = ru.job_to_dict(job)
    d["plan"]["superseded_from"] = dst_orig  # 退役字段: 旧格式账的迁移识别面
    return d


def _plain_job(job_id: str, hashes: tuple, mover: str, src: str, dst: str, *, phase: str = "done") -> dict:
    return ru.job_to_dict(
        ru.RelocateJob(
            job_id=job_id,
            hashes=tuple(hashes),
            mover=mover,
            src=src,
            dst=dst,
            scope=src,
            alias_kind="",
            alias_paths=(),
            phase=phase,
            reason="",
            created_at=time.time(),
            armed_at=0.0,
            updated_at=time.time(),
            resume_hashes=(),
            attempts=0,
            last_error="",
            plan={
                "form": "direct",
                "link_kind": "",
                "scope": src,
                "files": [["b.bin", 2048]]
            },
            move_issued=True,
            tag_on=False,
            origin="web",
        )
    )


def _inject_old_ledger(case: Path, jobs: dict) -> None:
    """停机注入旧格式账: relocate 整盒重写(无 model_version = 旧格式标记), 照 RM04-21 配方。

    注意与 RM04-21 的差异: RM04-21 只 clear jobs 盒(骨架短起已把 model_version 盖成 1),
    本用例要重现「旧格式账」就得连 model_version 一起去掉 —— 整盒重写。"""
    sp = case / "data" / "state.json"
    assert sp.is_file(), "state.json 不存在(注入底座不成立)"
    data = json.loads(sp.read_text(encoding="utf-8"))
    data["relocate"] = {"jobs": jobs}  # 无 model_version: 重构前旧账口径
    sp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _skeleton_start(case: Path) -> tuple[Path, int]:
    """空库短起停: 生成合法 state.json(注入底座); 返回 (cfg 路径, web 端口)。

    优雅退出走 graceful_after 自发 SIGTERM(RM04-06 预热先例)—— plain stop 在 Windows 是
    外部强杀(非优雅, 退出码恒 1), 不能当优雅断言; 骨架要的就是干净落盘的 state.json。"""
    cfg, web_port = M.write_cfg(case, relocate=True, alias_threshold=1)
    p = app.start(cfg, case, graceful_after=6.0)
    rc = p.wait(90)
    assert rc == 0, f"骨架优雅退出码 {rc}:\n{p.log()[-600:]}"
    assert (case / "data" / "state.json").is_file(), "骨架退出后 state.json 没落盘"
    return cfg, web_port


def _write_v7_cfg(cfg: Path, web_port: int) -> None:
    """把配置文件换写成 v7 旧形状(顶层 bt_backup 表 + 旧版本章; 动态注入见模块 docstring)。"""
    bt_backup = W.BT_BACKUP
    assert bt_backup.is_dir(), f"副实例 BT_backup 不在(EXE 派生路径失效?): {bt_backup}"
    qb_key = f"127.0.0.1:{instances.SECONDARY}"
    text = CFG_V7_TEMPLATE.format(
        schema_version=V7,
        qb_port=instances.SECONDARY,
        data_dir=(cfg.parent / "data").as_posix(),
        fake_host=M.FAKE_TRACKER_HOST,
        qb_key=qb_key,
        bt_backup=bt_backup.as_posix(),
        web_port=web_port,
    )
    if f"port: {instances.PRIMARY}" in text:
        raise AssertionError(f"配置指向了 {instances.PRIMARY}(真实种子), 拒跑: {cfg}")
    cfg.write_text(text, encoding="utf-8")


# ================================================================ RM04-23


def test_rm04_23_legacy_ledger_migrator_good_bad_restart():
    """[RM04-23] 旧账迁移器三形态真机闭环(good/bad/restart 三腿, 断言明细见模块 docstring)

    前置: 双实例在线 + 副实例无 real-fake 残留; restart 腿需 R: 在(缺席整条 skip, 钉死口径)。
    副作用/回滚/失败判据: 见模块 docstring(四行契约)。
    """
    _require_r_topology()
    # 开工闸: 双实例在线 + connection_status 非 disconnected(§2.4 假红陷阱闸; 起停只经 real.up)
    for port in (instances.PRIMARY, instances.SECONDARY):
        guard.check_port(port)
        status = guard.check_online(instances.make(port))
        assert status != "disconnected", f"{port} connection_status=disconnected(假红陷阱), 拒跑"
    case_g = M.case_dir("rm04_23_good")
    case_b = M.case_dir("rm04_23_bad")
    case_r = M.case_dir("rm04_23_restart")
    qb = M.qbfake()
    assert not M.rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
    assert W.BT_BACKUP.is_dir(), f"副实例 BT_backup 不在(env_registry EXE 派生路径失效?): {W.BT_BACKUP}"

    ev: dict = {"case_good": str(case_g), "case_bad": str(case_b), "case_restart": str(case_r)}
    _flush(ev, case_g, "G0")
    h1 = None  # restart 腿 finally 的收尾按"已知多少清多少"推进
    h2 = None
    p = None
    snap_before = W.bt_backup_snapshot()
    dst = case_r / "dst"
    try:
        # ============================== 腿 1: good ==============================
        cfg_g, web_g = _skeleton_start(case_g)
        mh = "a" * 40
        xh = "b" * 40
        sh2 = "c" * 40
        dh = "d" * 40
        g_src = "R:/qbt-fake/rm04/rm04_23/fake-src-g"
        g_flip = "R:/qbt-fake/rm04/rm04_23/fake-flip-g"
        g_orig = "R:/qbt-fake/rm04/rm04_23/fake-orig-g"
        jobs_g = {
            "jr_g_legacy": _legacy_job("jr_g_legacy", mh, xh, g_src, g_flip, g_orig, f"{g_src}/alias.bin"),
            "jr_g_succ": _plain_job("jr_g_succ", (mh, sh2), mh, f"{g_src}/succ", g_flip),
            "jr_g_done": _plain_job("jr_g_done", (dh, ), dh, f"{g_src}/done", f"{g_src}/done-dst"),
        }
        _inject_old_ledger(case_g, jobs_g)
        _write_v7_cfg(cfg_g, web_g)
        ev["G1_injected"] = {"jobs": list(jobs_g.keys()), "model_version": None, "schema": V7}
        _flush(ev, case_g, "G1")

        # 主启走 sentinel 优雅通路(W.start_bypass_app, RM04-21 同款): plain p.stop 是外部强杀
        # (非优雅 rc=1, state 不优雅落盘), 优雅退出与 rc 断言走 sentinel; 且同 case 日志为追加式,
        # wait_web 会撞骨架进程的旧行假阳性(RM04-06 陷阱条目) —— 等待面一律用「只有本主启会打的
        # 新日志锚」。
        p = W.start_bypass_app(case_g, cfg_g)

        def migration_seen():
            hit = [ln for ln in M.log_text(case_g).splitlines() if "配置 schema 迁移" in ln and "旧表唯一非空条目已收编为单实例标量" in ln]
            if hit:
                return hit
            if not p.alive():
                raise AssertionError(f"good 腿产品进程提前退出(迁移启动失败?):\n{p.log()[-800:]}")
            return None

        hit_lines = M.wait_until(migration_seen, 60, "60s 内未见 v7->v8 bt_backup 收编 WARNING(迁移链未跑?)")
        assert p.alive(), "good 腿产品启动后进程已死"
        # ---- config v7->v8 迁移链(075dd418 触面, 用例卡断言点)
        ev["G2_config_line"] = hit_lines[-1]
        # WARNING 落日志先于 materialize 写盘: 轮询盘上版本章到位再读(竞态窗, 首跑实测踩过)
        M.wait_until(
            lambda: "schema_version: 8" in cfg_g.read_text(encoding="utf-8") or None, 30, "config.yml 版本章未抬到 v8(写盘未完成?)"
        )

        def cfg_v8_text():
            return cfg_g.read_text(encoding="utf-8")

        cfg_text = cfg_v8_text()
        assert "schema_version: 8" in cfg_text, \
            f"迁移后 config 版本章未抬到 v8: {cfg_text[:400]}"
        assert cfg_text.count("bt_backup") == 1 and f"{W.BT_BACKUP.as_posix()}" in cfg_text, \
            "迁移后 config 形态不符(bt_backup 应只剩 relocate 标量一处)"
        bak = case_g / "data" / f"{cfg_g.name}.v{V7}.bak"
        assert bak.is_file(), f"版本号备份缺失: {bak}"
        ev["G2_config"] = {"schema": 8, "backup": str(bak)}
        # ---- 旧账迁移(一条不丢 + 字段对照 + 状态行 + 备份)
        mig_lines = [ln for ln in M.log_text(case_g).splitlines() if "旧账迁移完成" in ln]
        assert mig_lines, "日志缺「旧账迁移完成」状态行(迁移器没跑)"
        assert "1 个改道机器前任" in mig_lines[-1] and "归集 1 条" in mig_lines[-1], \
            f"迁移状态行计数不符: {mig_lines[-1]}"
        sp = case_g / "data" / "state.json"

        def model_version_stamped():
            data = json.loads(sp.read_text(encoding="utf-8"))
            mv = (data.get("relocate") or {}).get("model_version")
            return data if mv == ru.MODEL_VERSION else None

        data = M.wait_until(model_version_stamped, 30, "state.json 未盖章 model_version(接管面写穿未完成?)")  # 迁移行先于接管面落盘
        box = data.get("relocate") or {}
        assert box.get("model_version") == ru.MODEL_VERSION, \
            f"model_version 未盖章: {box.get('model_version')}"
        jbox = box.get("jobs") or {}
        assert set(jbox.keys()) == set(jobs_g.keys()), \
            f"账面条目数不符(一条不丢失守): {sorted(jbox.keys())} vs {sorted(jobs_g.keys())}"
        # 前任: 转 superseded + dst 还原原始落点 + 退役字段摘除 + 其余字段逐字不动
        nd = jbox["jr_g_legacy"]
        base = dict(jobs_g["jr_g_legacy"])
        assert nd.get("phase") == "superseded" and nd.get("reason") == "migrated_superseded", \
            f"前任未转 superseded 历史记录: {nd.get('phase')}/{nd.get('reason')}"
        assert nd.get("dst") == g_orig, f"前任 dst 未还原原始落点: {nd.get('dst')}"
        assert "superseded_from" not in (nd.get("plan") or {}), "退役字段 superseded_from 未摘除"
        expect = dict(base)
        expect["dst"] = g_orig
        expect["phase"] = "superseded"
        expect["reason"] = "migrated_superseded"
        expect["plan"] = {k: v for k, v in base["plan"].items() if k != "superseded_from"}
        assert nd == expect, f"前任账迁移后字段错位: {json.dumps({k: (nd.get(k), expect.get(k)) for k in expect if nd.get(k) != expect.get(k)}, ensure_ascii=False)[:800]}"
        # 继任: plan.inherited 归集条目 + extra_members 并入 + 其余字段逐字不动
        ns = jbox["jr_g_succ"]
        assert (ns.get("plan") or {}).get("inherited"), "继任账缺 plan.inherited 归集条目"
        inh = [e for e in ns["plan"]["inherited"] if isinstance(e, dict) and e.get("job_id") == "jr_g_legacy"]
        assert inh and inh[0].get("dst") == g_orig and inh[0].get("src") == g_src \
            and inh[0].get("alias_kind") == "file" and inh[0].get("link_kind") == "symlink", \
            f"归集条目字段不符: {inh}"
        assert (ns.get("plan") or {}).get("extra_members") == [xh], \
            f"extra_members 未并入前任成员: {ns.get('plan', {}).get('extra_members')}"
        succ_expect = dict(jobs_g["jr_g_succ"])
        succ_expect["plan"] = {
            **jobs_g["jr_g_succ"]["plan"], "inherited": ns["plan"]["inherited"],
            "extra_members": [xh]
        }
        assert ns == succ_expect, "继任账迁移后出现计划外字段漂移"
        # 无关 done 账: 迁移器零触碰, 逐字对照
        assert jbox["jr_g_done"] == jobs_g["jr_g_done"], "无关 done 账被迁移器改动(在途/历史零触碰口径失守)"
        # 新格式可读: 迁移后三条账 job_from_dict 全通
        for jid, jd in jbox.items():
            assert ru.job_from_dict(jd) is not None, f"迁移后账 {jid} job_from_dict 拒收(新格式不可读)"
        # 备份目录
        backups = list((case_g / "data" / "relocate-migration-backup").glob("*/state.json")) \
            if (case_g / "data" / "relocate-migration-backup").is_dir() else []
        assert backups, "迁移备份目录缺 state.json(R1 备份面失守)"
        ev["G2_ledger"] = {
            "model_version": box.get("model_version"),
            "line": mig_lines[-1],
            "backup": str(backups[0].parent),
            "legacy_dst_restored": True
        }
        _flush(ev, case_g, "G2")
        rc = p.stop(40)  # sentinel 优雅退出(真解释器进程内 SIGTERM, rc 可断言)
        assert rc == 0, f"good 腿优雅退出码 {rc}:\n{p.log()[-600:]}"
        p = None

        # ============================== 腿 2: bad ==============================
        cfg_b, web_b = _skeleton_start(case_b)
        b_src = "R:/qbt-fake/rm04/rm04_23/fake-src-b"
        b_flip = "R:/qbt-fake/rm04/rm04_23/fake-flip-b"
        b_orig = "R:/qbt-fake/rm04/rm04_23/fake-orig-b"
        jobs_b = {
            "jr_b_legacy": _legacy_job("jr_b_legacy", "e" * 40, "f" * 40, b_src, b_flip, b_orig, f"{b_src}/alias.bin"),
            "jr_b_succ": _plain_job("jr_b_succ", ("e" * 40, "c" * 40), "e" * 40, f"{b_src}/succ", b_flip),
            "jr_b_done": _plain_job("jr_b_done", ("d" * 40, ), "d" * 40, f"{b_src}/done", f"{b_src}/done-dst"),
            # 坏账两条: 整值非账形态的串值(非法 JSON 形态样本) / 缺 job_id 字段
            "jr_bad_str": "<<<not-a-json-account-garbage>>>",
            "jr_bad_missing": {
                "hashes": ["0123456789abcdef0123456789abcdef01234567"],
                "phase": "done"
            },
        }
        _inject_old_ledger(case_b, jobs_b)
        ev["B1_injected"] = {"jobs": list(jobs_b.keys())}
        _flush(ev, case_b, "B1")

        p = W.start_bypass_app(case_b, cfg_b)

        def migrate_done_seen():
            hit = [ln for ln in M.log_text(case_b).splitlines() if "旧账迁移完成" in ln]
            if hit:
                return hit
            if not p.alive():
                raise AssertionError(f"bad 腿产品进程提前退出(坏账把启动带崩?):\n{p.log()[-800:]}")
            return None

        M.wait_until(migrate_done_seen, 60, "60s 内未见「旧账迁移完成」(迁移器没跑或启动失败)")
        assert p.alive(), "bad 腿产品启动后进程已死(坏账不崩口径失守)"
        assert "Traceback" not in p.log(), "bad 腿启动出现未捕获异常堆栈"
        log_b = M.log_text(case_b)
        assert any("旧账迁移完成" in ln and "1 个改道机器前任" in ln for ln in log_b.splitlines()), \
            "bad 腿好账照迁状态行缺失(或坏账被误计入迁移数)"
        assert not any("旧账迁移失败" in ln for ln in log_b.splitlines()), "bad 腿出现迁移失败行(回滚被触发)"

        def model_version_stamped_b():
            data_b = json.loads((case_b / "data" / "state.json").read_text(encoding="utf-8"))
            return data_b if (data_b.get("relocate") or {}).get("model_version") == ru.MODEL_VERSION else None

        data_b = M.wait_until(model_version_stamped_b, 30, "bad 腿 state.json 未盖章 model_version(接管面写穿未完成?)")
        box_b = data_b.get("relocate") or {}
        assert box_b.get("model_version") == ru.MODEL_VERSION, "bad 腿 model_version 未盖章"
        jbox_b = box_b.get("jobs") or {}
        assert set(jbox_b.keys()) == set(jobs_b.keys()), \
            f"bad 腿账面条目数不符(坏账隔离 ≠ 删除): {sorted(jbox_b.keys())}"
        # 坏账隔离留痕: 注入值逐字保留
        assert jbox_b["jr_bad_str"] == jobs_b["jr_bad_str"], "串值坏账被迁移器改动(隔离留痕失守)"
        assert jbox_b["jr_bad_missing"] == jobs_b["jr_bad_missing"], "缺字段坏账被迁移器改动(隔离留痕失守)"
        # 好账照迁: 前任转 superseded + dst 还原; 继任归集; done 逐字不动
        ndb = jbox_b["jr_b_legacy"]
        assert ndb.get("phase") == "superseded" and ndb.get("dst") == b_orig \
            and "superseded_from" not in (ndb.get("plan") or {}), f"bad 腿好账前任迁移不符: {ndb.get('phase')}/{ndb.get('dst')}"
        nsb = jbox_b["jr_b_succ"]
        assert any(isinstance(e, dict) and e.get("job_id") == "jr_b_legacy" for e in (nsb.get("plan") or {}).get("inherited") or []), \
            "bad 腿继任缺归集条目"
        assert jbox_b["jr_b_done"] == jobs_b["jr_b_done"], "bad 腿无关 done 账被改动"
        ev["B2_bad"] = {"alive": True, "bad_kept": ["jr_bad_str", "jr_bad_missing"], "legacy_converted": True}
        _flush(ev, case_b, "B2")
        rc = p.stop(40)  # sentinel 优雅退出(rc 可断言+state 优雅落盘)
        assert rc == 0, f"bad 腿优雅退出码 {rc}:\n{p.log()[-600:]}"
        p = None

        # ============================== 腿 3: restart ==============================
        _, web_r = _skeleton_start(case_r)  # 空库短起(此刻副实例仍空): state.json 骨架 + 注入底座
        M.purge_tree(SRC.parent)
        h1 = M.fake_multi(qb, NAME, [(REL, FILE_SIZE)], SRC, SALT, piece_len=PIECE_LENS[0], write=True)
        h2 = M.fake_multi(qb, NAME, [(REL, FILE_SIZE)], SRC, SALT, piece_len=PIECE_LENS[1], write=False)
        assert h1 != h2, "两颗 infohash 撞车(必须同文件异 infohash)"
        M.wait_complete(qb, [h1, h2], 120)
        src_str = (qb.torrent(h1) or {}).get("save_path") or ""
        assert src_str, "mover save_path 读取失败(种子不在?)"
        ev["R1_seeded"] = {"h1": h1, "h2": h2, "src_str": src_str}
        _flush(ev, case_r, "R1a")

        # qB 原生 set_location 自搬 mover(绕过 auto-qb: 物理上 qB 自己搬完 —— 事故形态)
        qb.set_location(h1, str(dst))

        def mover_at_dst():
            cur = qb.torrent(h1) or {}
            if M.norm(cur.get("save_path") or "") == M.norm(dst) and (dst / REL).is_file():
                return cur["save_path"]
            return None

        dst_str = M.wait_until(mover_at_dst, 90, "mover 未落 dst 或 dst 文件缺失")
        assert not (SRC / REL).exists(), "src 真身还在(qB 未物理搬走?)"
        # 事故形态: 建链段已完成(指向 dst 的 junction), 断在核验 -> 账留 failed/armed_at==0
        junction = _s_junction_path(src_str, dst_str)
        alias_fs.create_dir_alias(junction, _s_content(dst_str), alias_fs.KIND_JUNCTION)
        assert M.reparse_kind(Path(junction)) == "junction", f"src 链接位形态非 junction: {junction}"
        assert (Path(junction) / "data" / "f0.bin").is_file(), "经 src 原路径穿透读不到数据(链没建好)"
        scope = ru.content_root_of(src_str, [REL])
        job = ru.RelocateJob(
            job_id=ru.job_id_for(h1, dst_str, src_str),
            hashes=(h1, h2),
            mover=h1,
            src=src_str,
            dst=dst_str,
            scope=scope,
            alias_kind="dir",  # _alias_kind_of_form("dir_alias") 同款
            alias_paths=(junction, ),
            phase=ru.PHASE_FAILED,
            reason="verify_mismatch",
            created_at=time.time(),
            armed_at=0.0,  # 对账 A1 闸前提: armed_at==0 才进判定表
            updated_at=time.time(),
            resume_hashes=(h1, h2),
            attempts=0,
            last_error="目标侧文件数/大小不符(注入的收尾断链事故形态)",
            plan={
                "form": "dir_alias",
                "link_kind": "junction",
                "scope": scope,
                "files": [[REL, FILE_SIZE]]
            },
            move_issued=True,
            tag_on=False,
            origin="web",
        )
        d = ru.job_to_dict(job)
        back = ru.job_from_dict(d)
        assert back is not None, "job_from_dict 拒收构造 dict"
        assert back.phase == "failed" and back.armed_at == 0.0, "回读字段不符(对账 A1 闸前提不成立)"
        _inject_old_ledger(case_r, {"jr_r_inflight": d})  # 整盒重写: 在途旧账 + 无 model_version
        ev["R1_injected"] = {"job_id": d["job_id"], "phase": d["phase"], "armed_at": d["armed_at"]}
        _flush(ev, case_r, "R1b")

        # 产品重启 -> 旧账迁移(在途账零触碰) -> 启动对账重入两行 -> armed
        cfg_r = case_r / "config.yml"
        assert cfg_r.is_file(), "restart 腿骨架配置不在"
        p = W.start_bypass_app(case_r, cfg_r)  # sentinel 优雅通路(骨架同 case 日志追加, 不用 wait_web)
        M.wait_until(lambda: "启动对账" in M.log_text(case_r) or None, 90, "90s 内未见「启动对账」日志(对账消费没跑)")

        def armed_seen():
            txt = M.log_text(case_r)
            if "已武装收尾" in txt:
                return True
            if "旧账迁移失败" in txt:
                raise AssertionError(
                    "restart 腿迁移失败(在途账不该进转换面):\n" + "\n".join(ln for ln in txt.splitlines() if "旧账迁移" in ln)[-600:]
                )
            return None

        assert M.wait_until(armed_seen, 180, "armed 未出现(重入链没走完)")
        lines = M.log_text(case_r).splitlines()
        reenter = [ln for ln in lines if "启动对账重入" in ln]
        assert reenter, "日志缺「启动对账重入」逐笔行:\n" + "\n".join(lines[-40:])
        assert "mover 已在 dst" in reenter[-1], f"重入行判据文案不符(走的不是重入支?): {reenter[-1]}"
        summary = [ln for ln in lines if "启动对账 " in ln and "保留" in ln]
        assert summary and "重入 1 / 保留 0" in summary[-1], \
            f"汇总行计数不符(只注入 1 笔): {summary[-1] if summary else '<缺>'}"
        jid = d["job_id"]
        rjob = M.wait_job_phase(case_r, jid, {"armed"}, 120, "job 未落 armed 相位(重入落账没写盘)")
        assert rjob.get("phase") == "armed", f"job 相位非 armed: {rjob.get('phase')}/{rjob.get('reason')}"
        assert float(rjob.get("armed_at") or 0) > 0, "重入落账未置 armed_at(A1 语义丢失)"
        data_r = json.loads((case_r / "data" / "state.json").read_text(encoding="utf-8"))
        assert (data_r.get("relocate") or {}).get("model_version") == ru.MODEL_VERSION, \
            "restart 腿 model_version 未盖章(旧格式账未迁)"
        ev["R1_reentered"] = {"reenter": reenter[-1], "summary": summary[-1], "armed_at": rjob.get("armed_at")}
        _flush(ev, case_r, "R1c")

        # 外部完成支(RM04-05 同款): qB 原生 setLocation 跟进非 mover -> 统一收尾 done(finalized)
        qb.set_location(h2, str(dst))
        M.wait_until(
            lambda: all(M.norm((qb.torrent(h) or {}).get("save_path") or "") == M.norm(dst_str)
                        for h in (h1, h2)) or None, 60, lambda: f"成员 save_path 未全部变 dst: "
            f"{ {h[:8]: (qb.torrent(h) or {}).get('save_path') for h in (h1, h2)} }"
        )
        fjob = M.wait_job_phase(case_r, jid, {"done", "failed"}, 180, "job 未推进到 done(reason=finalized 预期)")
        assert fjob.get("phase") == "done", f"job 终态非 done: phase={fjob.get('phase')} reason={fjob.get('reason')}"
        assert fjob.get("reason") == "finalized", f"job done 但 reason={fjob.get('reason')}(S1 统一收尾语义失守)"
        assert "收尾完成" in M.log_text(case_r), "日志缺「收尾完成」(收尾链没走)"
        assert not os.path.lexists(junction), f"src 链接位残留(删链门没删): {junction}"
        for h in (h1, h2):
            t = qb.torrent(h) or {}
            assert t.get("progress") == 1.0, f"{h[:8]} progress != 1.0: {t.get('progress')}"
            st = str(t.get("state") or "").lower()
            assert "error" not in st and "missing" not in st and "checking" not in st, \
                f"{h[:8]} 异常态: {t.get('state')}"
        g2 = M.wait_group(web_r, h1, {h1, h2}, 60, "组未归一(两颗不同组 = 裂组)")
        k2 = M.decode_key(g2["key"])
        assert M.norm(k2[0]) == M.norm(dst_str), f"终态组键首元不是 dst: {k2[0]}"
        assert tuple(sorted(k2[1])) == (REL, ), f"终态组键文件列表不符: {k2[1]}"
        ev["R1_final"] = {
            "phase": fjob.get("phase"),
            "reason": fjob.get("reason"),
            "link_gone": True,
            "group_key": g2["key"]
        }
        _flush(ev, case_r, "R1d")

    finally:
        # ---- R2 收尾: 产品优雅退出 -> 实例恢复 -> 删种子(连数据) -> BT_backup 核净 -> 目录删净
        ev["R2_cleanup"] = {}
        errs: list[str] = []
        if p is not None:
            try:
                ev["R2_cleanup"]["product_stop_rc"] = p.stop(40)
            except Exception as e:  # noqa: BLE001 —— 收尾失败聚合重抛, 不静默
                errs.append(f"产品停止失败: {e!r}")
        _flush(ev, case_r, "R2a")
        for port in (instances.SECONDARY, instances.PRIMARY):
            try:
                W.qb_up(port)  # 环境还原: 双实例回在线(片C 开工前提)
            except Exception as e:  # noqa: BLE001
                errs.append(f"real.up {port} 恢复失败: {e!r}")
        try:
            ev["R2_cleanup"]["seeds_removed"] = M.rm_all_fakes(M.qbfake())
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
            ev["R2_cleanup"].update(
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
        for tag, c in (("R2b_g", case_g), ("R2b_b", case_b), ("R2b_r", case_r)):
            _flush(ev, c, tag)  # 各腿日志在删目录前最后落一份(独立文件名, 不互覆)
        try:
            M.purge_tree(SRC.parent)  # 只删本用例子树(purge_tree 不递归删穿 junction)
            M.purge_tree(case_g)
            M.purge_tree(case_b)
            M.purge_tree(case_r)
        except Exception as e:  # noqa: BLE001
            errs.append(f"目录清理失败: {e!r}")
        if errs:
            raise AssertionError(f"收尾未净(R2): {'; '.join(errs)}")


def _s_junction_path(src_str: str, dst_str: str) -> str:
    """src 内容根 junction 位(与产品 _build_links dir_alias 支同位: src/<组名>)。"""
    return os.path.join(src_str, NAME)


def _s_content(root: str) -> str:
    """目标内容根(dst/<组名>)。"""
    return os.path.join(root, NAME)
