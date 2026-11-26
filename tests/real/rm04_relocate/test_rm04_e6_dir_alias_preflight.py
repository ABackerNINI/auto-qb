"""

同源声明: _write_cfg_fast_tick/_flush 与 test_rm04_e2_alias_add_pass.py /
test_rm04_e5_member_shrink.py 同源(函数体逐字一致, docstring/证据文件名前缀按用例本地化,
单侧改动须同步对应文件, 评审 R23 纪律); _readlink_norm 与 test_rm04_chain_gate_candidates.py
同源(函数体逐字一致); _assert_healthy 复用 test_rm04_e2_alias_add_pass.py 同名单点
(import 转发, 不另抄); _mover_of/_product_delete/_shrink_lines 复用
test_rm04_e5_member_shrink.py 同名单点(import 转发, 不另抄 —— mover 识别与仅删种子出口
是两用例共用纪律, 单侧改动须同步)。
[RM04-31] [E6] 目录级回归: DIR_ALIAS 形态组(multi-member 子目录布局, 文件数 >= 阈值 8)
armed 后四断言面: 1)对 dst 的 confirm 不松动(目录别名提议的二次确认保留 —— 无 confirm
回执 cls=confirm 零 started 零「迁移发起」零副作用, 带 confirm 才 started); 2)深层路径
(landing 落 scope 内 = junction 所在内容根)添加 -> confirm 新弹窗(D10 告知语义: 请求路径 ->
实际落点 -> 目标卷剩余)且 actual_path 按正 rel 展示(dst 侧镜像根 + 正向尾段, 绝对路径无
「..」负 rel 段); 3)scope 外兄弟/前缀同串目录写入 -> 预检 cls=ok 零弹窗 + 真添加落真实目录
(不经理由 junction 重定向)、删链门不计依赖(预检零依赖文案; 门级全链由收尾腿兑现: 兄弟
种子在场收尾仍 done); 4)D16 目录级全量拦截原样(与成员链接同名的目录级写入, landing 恰等
junction -> confirm 仍拦)。收尾腿: 逐个删光成员(R4 收缩) -> 空集核验 -> 删链门(兄弟种子
在场但 scope 外 = 依赖清零) -> 收尾 done、junction 删除 —— 3)的「删链门不计依赖」门级面
在此兑现。

计划 plans/26-11-17-0636-plan-real-rm04-relocate-refactor-verify.html §03.4 RM04-31 用例卡
(E6, L2; 出处 0448 计划「目录级前缀扩面误伤」行: 仅 landing 落在 scope 内的深层添加本就经
重定向(D10 须告知)—— 弹窗即设计语义; src 下 scope 外兄弟/前缀同串目录写入落真实目录、
删链门不计依赖, 判据不认、不弹窗; E6 回归 actual 展示正确性)。

切分声明(不测三遍):
- 与 RM04-05: RM04-05 测搬迁主链(junction/穿透/journal done), 本条测添加预检
  confirm/深层弹窗/actual_path 展示面(RM04-05 未覆盖);
- 与 RM04-25: 删链门候选面三格(祖先/direct/同名依赖账)由 RM04-25 三腿钉扎, 本条不在
  预检腿重复 —— 收尾腿只兑现「scope 外兄弟不计依赖」这单一格(成员全删光后门自然走到,
  零额外注入);
- 与 RM04-30: R4 收缩判定本体(N 拍判据/负向对照)由 RM04-30 L3 钉扎, 本条收尾腿只把它
  当「到达删链门的确定性通路」使用(RM04-25 A 腿同款), 不复写收缩断言。

坑点传承(片E/片F): 「账面相位瞬态」取数面单点 —— armed 相位断言走成员详情端点 relocate
相位(member_detail), journal 在 armed 恒无文件(daemon 下线窗才写)不走 journal_of; 场景 2
confirm 的 actual_path 为目录级展示键(RM04-25 已实证: 文件级同名 confirm 恒 None, 断言
requested_path) —— 本条是目录级形态, confirm 必带 actual_path, 断言之; 「磁盘账迟滞」
(片F 首跑实锤): state.json 按周期落盘(下限 30S), 收缩过程断言走 WARNING 行 live 面,
磁盘账只配终态等待; 「产品自选 mover」(片F 首跑实锤): 收尾腿删除顺序先删 mover(幸存非
mover 留 src = at_dst=False 稳态), 否则收缩与核验同拍完成 job 提前 done, 空集核验腿失真。

## 测试计划(单测试函数, 五段)
- G0 开工闸: R: 拓扑在 + 双实例在线(connection_status 非 disconnected) + 副实例无
  real-fake 残留; 产品起(旁路 runner, fast tick, 阈值 8 默认)。
- S1 造现场 + 1): 双成员 x 8 文件子目录布局组落 R: -> 齐完成 -> 归组断言 -> 迁移无 confirm
  -> 回执 cls=confirm 零 started + 零「迁移发起」+ dst 不存在(零副作用) -> confirm=true
  重投 -> started form=dir_alias + job_id -> 已武装收尾 -> junction 现场(指 dst)。
- S2 2)深层路径: precheck-add {save_path=内容根/deep, name=深层名} -> cls=confirm +
  gate=finalize_window + 文案「经别名落到」+ actual_path == dst/PACK/deep/<name>(正 rel,
  无「..」)+ notes 带「目标卷剩余」告知面(深形态 save_path 不等 src -> scope_hit 不命中 ->
  卷剩余按「不可判定」告知, 首跑实锤观察项; 真值面归4))。
- S3 3)scope 外兄弟/前缀同串: precheck-add {save_path=src/PACK_extra, name=兄弟名} ->
  cls=ok 零弹窗 + actual_path None(landing=.../pack_extra/<兄弟名> 与内容根前缀同串但
  分隔符为界不命中 —— 旧裸 startswith 扩面在此误拦) -> 真添加兄弟种子(带数据落旧根) ->
  文件落真实目录(junction 未重定向)+ 健康 + job 账零扰动(armed 相位不变 + 零计划外
  「迁移发起」)。
- S4 4)D16 目录级全量拦截: precheck-add {save_path=src, name=PACK(与成员链接同名)} ->
  cls=confirm + gate=finalize_window + 文案「经别名落到」+ actual_path == dst/PACK +
  volume_free 有值 + notes 带卷剩余真值(等值面 scope_hit 命中, D10 三元全貌)。
- S5 收尾腿(3)门级兑现): 产品 WEB 先删 mover 再删幸存成员(仅删种子, 先删 mover 纪律见
  坑点传承) -> R4 收缩 x2(WARNING 行 live 面留痕) -> 空集核验 -> 删链门(兄弟种子在场但
  scope 外 -> 依赖清零) -> 「收尾完成」行 + 磁盘账 done/finalized(终态等待, 容 30S flush
  迟滞)+ junction 删除 + 兄弟种子全程健康落点不动。
- Z 收尾: 产品优雅退出 -> 双实例恢复在线 -> real-fake 删净(连数据) -> BT_backup 本用例
  哈希残留清除 + 逐文件比对开工快照 -> case 树与 R: 子树删净 + junction lstat 零残留。

前置: 环境1(R: 在, src=R:/qbt-fake/rm04/rm04_31/src 与 dst=D: 异盘) + 双测试实例在线
      (没起先 `commands run real.up -- --port <白名单端口>`); 副实例无 real-fake 残留;
      wrapper 名册窄化旁路在位(沿 RM04-20/21/27/28/34 授权, 零新增旁路面; 哨兵优雅退出);
      独占约 4-5 分钟, conftest serial 锁串行保护。R: 缺席 => skip 不回退落点(钉死口径)。
副作用: 一次真搬迁(mover 由 qB 原生搬 R:->D:, 内容根 junction 建立)+ armed 期删种 2 枚
      (仅删种子不删文件)+ 兄弟种子添加 1 枚(带数据落旧根 scope 外)+ state 账。
回滚: 产品优雅退出(sentinel 通路); 双实例恢复在线; real-fake 种子删净(连数据); BT_backup
      只清本用例哈希残留 + 逐文件比对开工快照(queue 豁免); case 树与 R:/qbt-fake/rm04/
      rm04_31 子树删净(purge_tree 不递归删穿链接); junction lstat 零残留。
失败判据: 目录级 confirm 缺失(1)二次确认松动或4)D16 放行); 深层添加零弹窗或 actual_path
      显示错(绝对/负 rel/镜像根错段); scope 外写入被误拦(cls 非 ok)或真添加被重定向或
      收尾计入依赖(删链门悬挂); 收尾未 done 或 junction 残留; 收尾有残留。

跑法: `commands run real.run -- --case RM04-31 --yes`(不要裸 pytest)。
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
import test_rm04_e2_alias_add_pass as E2  # noqa: E402  (复用片E 的旁路接线 helper; 同源面见其 docstring)
import test_rm04_e5_member_shrink as E5  # noqa: E402  (复用 mover 识别/仅删种子/收缩行 helper; 同源面见其 docstring)

from lib import guard, instances  # noqa: E402
from auto_qb.core.modules import relocate_units as ru  # noqa: E402  (产品码: 相位/原因常量)

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="本片断言含 Windows 特有语义(junction/优雅退出通路)"),
]

# 拓扑单点(钉死, 见模块 docstring; 子树隔离): src 在 R: 内存盘
R_ROOT = Path("R:/qbt-fake/rm04")
SRC = R_ROOT / "rm04_31" / "src"
PACK = "rm04c31pack"  # 成员内容根名(= junction 名 = D16 同名拦截对象)
PACK_EXTRA = PACK + "_extra"  # 前缀同串兄弟目录(分隔符为界负向)
SIB_NAME = "rm04c31sib.bin"  # 兄弟目录内真添加种子名
DEEP_NAME = "rm04c31deep.bin"  # 深层路径探针种子名
FILE_SIZE = 64 * 1024
SIB_SIZE = 256 * 1024
PIECE_LENS = (16384, 32768)  # 两颗成员: 同文件列表异 infohash
FILES = [(f"{PACK}/sub/f{i}.bin", FILE_SIZE) for i in range(8)]  # 8 文件 >= 阈值 8 -> dir_alias
SALT = "rm04c31"

# 复用片E 旁路面(单一实现, 不另抄)
_require_r_topology = E2._require_r_topology
start_bypass_app = E2.start_bypass_app
stop_lingering_product = E2.stop_lingering_product
qb_up = E2.qb_up
qb_down = E2.qb_down
bt_backup_snapshot = E2.bt_backup_snapshot
# 副实例 BT_backup 路径单点在 E2, 函数内按需取(收集期不探测 EXE)
_assert_healthy = E2._assert_healthy
_readlink_norm = E2._readlink_norm

# 复用片F E5 单点(单一实现, 不另抄; 见 E5 docstring 的 mover 纪律与 live 取数面)
_mover_of = E5._mover_of
_product_delete = E5._product_delete
_shrink_lines = E5._shrink_lines

# 片F 证据目录(任务口径: 逐案 evidence 落 tests/real/.work/rm04-sliceF/; 时刻后缀防覆写)
SLICE_EV = HERE.parent / ".work" / "rm04-sliceF"


def _flush(ev: dict, case: Path, tag: str) -> None:
    """证据落盘(gitignored .work/rm04-sliceF): 全量断言现场 + 产品日志副本, 时刻后缀防覆写。"""
    ev["ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
    SLICE_EV.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    (SLICE_EV / f"rm04_31_{tag}_evidence_{stamp}.json"
    ).write_text(json.dumps(ev, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    try:
        log = M.log_text(case)
    except Exception as e:  # noqa: BLE001 —— 取证失败如实带错, 不掩盖主断言
        log = f"<log read failed: {e!r}>"
    (SLICE_EV / f"rm04_31_{tag}_auto-qb_{stamp}.log").write_text(log, encoding="utf-8")


def _write_cfg_fast_tick(case: Path) -> tuple[Path, int]:
    """RM04-31 专用配置: 在 M.write_cfg 基础上把 main_tick 2S -> 1S(片C 沉淀派生)。

    收尾腿走 R4 收缩 -> 空集核验 -> 删链门的在线通路, 1S 拍让收缩判定每轮必被覆盖
    (证据轮 last_removed 只存活一个同步轮 1.5S); sync_interval 1.5S 不变。"""
    cfg, web_port = M.write_cfg(case, relocate=True, alias_threshold=8)
    text = cfg.read_text(encoding="utf-8")
    assert "main_tick: 2S" in text
    cfg.write_text(text.replace("main_tick: 2S", "main_tick: 1S"), encoding="utf-8")
    return cfg, web_port


def _precheck(web_port: int, save_path: str, name: str, timeout: float = 30.0) -> dict:
    """添加预检(POST /api/relocate/precheck-add), 返回 truth(dict)。"""
    pre = M.cmd_post_and_wait(
        web_port, "/api/relocate/precheck-add", {
            "save_path": save_path,
            "name": name
        }, timeout=timeout
    )
    return (pre or {}).get("truth") or pre or {}


def _armed_phase(web_port: int, ih: str) -> str:
    """成员详情端点的 relocate 相位(片E 坑点单点: armed 相位断言走详情端点, journal 在 armed 恒无文件)。"""
    return str(((M.member_detail(web_port, ih) or {}).get("relocate") or {}).get("phase") or "")


# ================================================================ RM04-31


def test_rm04_31_e6_dir_alias_preflight():
    """[RM04-31] E6 目录级回归(1)confirm 不松动 / 2)深层弹窗+actual_path / 3)scope 外零弹窗+落真实目录 / 4)D16 原样)

    前置: R: 在 + 双实例在线 + 副实例无 real-fake 残留; wrapper 收编入库版在位。
    副作用/回滚/失败判据: 见模块 docstring(四行契约)。
    """
    _require_r_topology()
    case = M.case_dir("rm04_31")
    stop_lingering_product(case)
    qb = M.qbfake()
    assert not M.rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
    assert E2.BT_BACKUP.is_dir(), f"副实例 BT_backup 不在(env_registry EXE 派生路径失效?): {E2.BT_BACKUP}"
    for port in (instances.PRIMARY, instances.SECONDARY):
        guard.check_port(port)
        status = guard.check_online(instances.make(port))
        assert status != "disconnected", f"{port} connection_status=disconnected(假红陷阱), 拒跑"
    qb_up(instances.SECONDARY)
    qb_up(instances.PRIMARY)

    ev: dict = {"case": str(case), "topology": {"src": str(SRC), "pack": PACK, "dst": "case/dst"}}
    p = None
    h1 = None
    h2 = None
    hsib = None
    job_id = ""
    junction = SRC / PACK  # finally 的别名零残留检查用(早退时按"建没建"如实判)
    dst = case / "dst"
    snap_before = bt_backup_snapshot()
    try:
        M.purge_tree(SRC.parent)
        cfg, web_port = _write_cfg_fast_tick(case)
        p = start_bypass_app(case, cfg)
        assert p.wait_web(45), f"WEB 没起来:\n{p.log()[-800:]}"
        assert p.wait_log("整组迁移已启用", 20), f"relocate 启动日志缺失:\n{p.log()[-600:]}"

        # ---- S1 造现场: 双成员 x 8 文件子目录布局组(DIR_ALIAS) + 1)confirm 握手
        h1 = M.fake_multi(qb, PACK, FILES, SRC, SALT, piece_len=PIECE_LENS[0], write=True)
        h2 = M.fake_multi(qb, PACK, FILES, SRC, SALT, piece_len=PIECE_LENS[1], write=False)
        assert h1 != h2, "两颗 infohash 撞车(必须同文件列表异 piece_len)"
        M.wait_complete(qb, [h1, h2], 120)
        M.wait_group(web_port, h1, {h1, h2}, 30, "双成员组未归组")
        M.wait_store_progress(web_port, [h1, h2], 60)
        ev["S1_scene"] = {"members": [h1[:8], h2[:8]], "files": len(FILES), "src": str(SRC)}
        _flush(ev, case, "S1")

        # 1) 对 dst 的 confirm 不松动: 无 confirm -> 回执 cls=confirm 零 started 零发起零副作用
        result = M.cmd_post_and_wait(web_port, f"/api/torrents/{h1}/location", {"location": str(dst)})
        items = ((result or {}).get("truth") or {}).get("results") or []
        assert items and items[0].get("cls") == "confirm", \
            f"1)目录级二次确认松动(无 confirm 却非 confirm 回执): {json.dumps(result, ensure_ascii=False)[:500]}"
        assert not [it for it in items if it.get("cls") == "started"], f"1)无 confirm 却 started(松动): {items}"
        assert "迁移发起" not in M.log_text(case), "1)无 confirm 却出现「迁移发起」(零副作用失守)"
        assert not dst.exists(), f"1)无 confirm 却创建了 dst(零副作用失守): {dst}"
        ev["S1_confirm_gate"] = {"cls": items[0].get("cls"), "dst_absent": True}
        _flush(ev, case, "S1b")

        # confirm=true 重投 -> started(dir_alias) -> armed 现场
        result = M.cmd_post_and_wait(web_port, f"/api/torrents/{h1}/location", {"location": str(dst), "confirm": True})
        item = M.one_started_item(result)
        assert item.get("form") == "dir_alias", f"形态非 dir_alias: {json.dumps(item, ensure_ascii=False)[:400]}"
        job_id = item.get("job_id")
        assert job_id, f"started 项缺 job_id: {json.dumps(item, ensure_ascii=False)[:400]}"
        assert p.wait_log("已武装收尾", 60), "未武装(日志锚缺失)"
        M.wait_until(
            lambda: M.reparse_kind(junction) == "junction" or None, 60,
            lambda: f"junction 形态异常: {M.reparse_kind(junction)}"
        )
        assert M.norm(_readlink_norm(junction)).startswith(M.norm(dst)), f"junction 未指 dst: {_readlink_norm(junction)}"
        M.wait_until(
            lambda: True if _armed_phase(web_port, h1) == "armed" else None, 30,
            lambda: f"armed 账相位未落(详情端点): {_armed_phase(web_port, h1)}"
        )
        ev["S1_armed"] = {
            "job": job_id,
            "form": "dir_alias",
            "junction": str(junction),
            "target": _readlink_norm(junction)
        }
        _flush(ev, case, "S1c")

        # ---- S2 2)深层路径(landing 落 scope 内 = junction 所在内容根): confirm 弹窗 + actual_path 正 rel
        deep_sp = str(SRC / PACK / "deep")
        truth = _precheck(web_port, deep_sp, DEEP_NAME)
        assert truth.get("cls") == "confirm", \
            f"2)深层添加零弹窗(D10 告知语义失守): {json.dumps(truth, ensure_ascii=False)[:500]}"
        reasons = truth.get("reasons") or []
        assert any((r or {}).get("gate") == "finalize_window" for r in reasons), \
            f"2)confirm 原因缺 finalize_window: {reasons}"
        text2 = " ".join(str((r or {}).get("text") or "") for r in reasons)
        assert "经别名落到" in text2, f"2)文案缺「经别名落到」(重定向面语义): {text2[:200]}"
        expect_actual = f"{M.norm(dst)}/{PACK}/deep/{DEEP_NAME}"
        actual2 = str(truth.get("actual_path") or "")
        assert M.norm(actual2) == expect_actual, f"2)actual_path 展示错: {actual2!r} != {expect_actual!r}"
        assert ".." not in actual2, f"2)actual_path 出现负 rel 段: {actual2!r}"
        assert actual2.startswith(M.norm(dst)), f"2)actual_path 不按 dst 镜像展示: {actual2!r}"
        # D10 第三元(目标卷剩余)在深形态按「不可判定」告知(产品 scope_hit 要求 save_path 恰等
        # src —— 深层 save_path 不命中, 首跑实锤); 告知面本身在场即断言, 真值面归4)等值面探针
        notes2 = [str(n) for n in (truth.get("notes") or [])]
        assert notes2 and any("目标卷剩余" in n for n in notes2), f"2)notes 缺「目标卷剩余」告知面: {notes2}"
        ev["S2_deep_confirm"] = {
            "cls": truth.get("cls"),
            "actual_path": actual2,
            "requested": str(truth.get("requested_path") or ""),
            "notes": notes2,
            "volume_free": truth.get("volume_free"),
            "note": "deep 形态 save_path 不等 src -> scope_hit 不命中 -> volume_free=None, "
                    "notes 走「目标卷剩余不可判定」告知(产品现行为, 观察项)"
        }
        _flush(ev, case, "S2")

        # ---- S3 3)scope 外兄弟/前缀同串: 预检 ok 零弹窗 + 真添加落真实目录 + job 零扰动
        truth3 = _precheck(web_port, str(SRC / PACK_EXTRA), SIB_NAME)
        assert truth3.get("cls") == "ok", \
            f"3)scope 外写入被误拦(前缀扩面复发): {json.dumps(truth3, ensure_ascii=False)[:500]}"
        assert not [r for r in (truth3.get("reasons") or []) if (r or {}).get("gate") == "finalize_window"], \
            f"3)scope 外写入命中 finalize_window(误拦): {truth3.get('reasons')}"
        assert truth3.get("actual_path") is None, \
            f"3)scope 外写入被推成重定向面(actual_path 应 None): {truth3.get('actual_path')}"
        issued0 = M.log_text(case).count("迁移发起")
        hsib = M.fake_with_data(qb, SIB_NAME, SIB_SIZE, SRC / PACK_EXTRA, SALT + "sib", piece_len=16384, write=True)
        M.wait_complete(qb, [hsib], 120)
        tsib = _assert_healthy(qb, hsib, "兄弟种子")
        assert M.norm(tsib.get("save_path") or "") == M.norm(str(SRC / PACK_EXTRA)), \
            f"3)兄弟种子落点被动: {tsib.get('save_path')}"
        assert (SRC / PACK_EXTRA / SIB_NAME).is_file(), "3)实文件未落真实目录(被 junction 重定向?)"
        assert M.log_text(case).count("迁移发起") == issued0, "3)兄弟添加引发计划外「迁移发起」"
        assert _armed_phase(web_port, h1) == "armed", \
            f"3)兄弟添加扰动 job 账相位: {_armed_phase(web_port, h1)}"
        ev["S3_outsider_ok"] = {
            "cls": truth3.get("cls"),
            "sib": hsib[:8],
            "sib_save_path": tsib.get("save_path"),
            "real_file": str(SRC / PACK_EXTRA / SIB_NAME)
        }
        _flush(ev, case, "S3")

        # ---- S4 4)D16 目录级全量拦截原样: landing 恰等 junction(与成员链接同名)仍 confirm
        truth4 = _precheck(web_port, str(SRC), PACK)
        assert truth4.get("cls") == "confirm", \
            f"4)D16 目录级全量拦截松动(同名目录级写入未拦): {json.dumps(truth4, ensure_ascii=False)[:500]}"
        reasons4 = truth4.get("reasons") or []
        assert any((r or {}).get("gate") == "finalize_window" for r in reasons4), \
            f"4)confirm 原因缺 finalize_window: {reasons4}"
        text4 = " ".join(str((r or {}).get("text") or "") for r in reasons4)
        assert "经别名落到" in text4, f"4)文案缺「经别名落到」: {text4[:200]}"
        expect4 = f"{M.norm(dst)}/{PACK}"
        actual4 = str(truth4.get("actual_path") or "")
        assert M.norm(actual4) == expect4, f"4)actual_path(镜像根)展示错: {actual4!r} != {expect4!r}"
        # D10 三元全貌在等值面(save_path 恰等 src -> scope_hit 命中)取真值: 卷剩余有值 + notes 带字节数
        assert truth4.get("volume_free") is not None, \
            f"4)等值面目标卷剩余不可判定(D10 第三元缺失): {truth4.get('volume_free')}"
        notes4 = [str(n) for n in (truth4.get("notes") or [])]
        assert notes4 and any("目标卷剩余" in n and "不可判定" not in n for n in notes4), \
            f"4)等值面 notes 未带卷剩余真值: {notes4}"
        ev["S4_d16_same_name"] = {
            "cls": truth4.get("cls"),
            "actual_path": actual4,
            "volume_free": truth4.get("volume_free"),
            "notes": notes4
        }
        _flush(ev, case, "S4")

        # ---- S5 收尾腿: 先删 mover + 逐个删光成员 -> R4 收缩 x2(live 面) -> 空集核验
        #      -> 删链门(兄弟种子在场但 scope 外 = 依赖清零) -> done
        mover = _mover_of(web_port, qb, [h1, h2], dst)
        gone1 = mover  # 先删 mover: 幸存非 mover 留 src(at_dst=False), 收缩后 job 不会被同拍核验提前终结
        _product_delete(web_port, gone1)
        M.wait_until(lambda: True if qb.torrent(gone1) is None else None, 30, "第一个成员未从 qB 消失")

        def shrink1():
            w = _shrink_lines(case, job_id)
            return w if len(w) >= 1 and gone1[:8] in w[-1] else None

        M.wait_until(shrink1, 60, lambda: f"第一次收缩未观测: WARNING={len(_shrink_lines(case, job_id))}")
        gone2 = h2 if gone1 == h1 else h1
        _product_delete(web_port, gone2)
        M.wait_until(lambda: True if qb.torrent(gone2) is None else None, 30, "第二个成员未从 qB 消失")
        M.wait_until(lambda: True if "收尾完成" in M.log_text(case) else None, 120, "收尾完成行未出现(删链门把兄弟种子计入依赖?)")
        fin_line = [ln for ln in M.log_text(case).splitlines() if "收尾完成" in ln][-1]
        assert "删链门依赖清零" in fin_line and "已在线删除别名" in fin_line, \
            f"3)删链门不计依赖失守/收尾行语义不符: {fin_line}"

        def done_on_disk():
            job = M.jobs_on_disk(case).get(job_id) or {}
            return job if job.get("phase") == ru.PHASE_DONE and job.get("reason") == ru.REASON_FINALIZED else None

        M.wait_until(done_on_disk, 100, lambda: f"磁盘账未落 done/finalized: {M.jobs_on_disk(case).get(job_id)}")
        M.wait_until(lambda: True if not M._is_link(str(junction)) else None, 60, "收尾后 junction 未删除")
        tsib2 = _assert_healthy(qb, hsib, "收尾后兄弟种子")
        assert M.norm(tsib2.get("save_path") or "") == M.norm(str(SRC / PACK_EXTRA)), \
            f"3)收尾后兄弟种子落点被动: {tsib2.get('save_path')}"
        ev["S5_finalized"] = {
            "job": job_id,
            "log": fin_line,
            "alias_removed": True,
            "shrink_lines": [ln.split(": ", 2)[-1][:80] for ln in _shrink_lines(case, job_id)]
        }
        _flush(ev, case, "S5")

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
            my_hashes = [h for h in (h1, h2, hsib) if h]
            for ih in my_hashes:
                for suffix in (".fastresume", ".torrent", ".fastresume.bak", ".torrent.bak"):
                    fp = E2.BT_BACKUP / f"{ih}{suffix}"
                    if fp.is_file():
                        fp.unlink()
                        removed.append(fp.name)
            now = bt_backup_snapshot()
            residue = [k for k in now if k not in snap_before and not any(k.startswith(ih) for ih in my_hashes)]
            before_files = {k: v for k, v in snap_before.items() if (E2.BT_BACKUP / k).is_file() and k != "queue"}
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
        if M._is_link(str(junction)):
            errs.append(f"junction 零残留失守: {junction}")
        if errs:
            raise AssertionError(f"收尾未净(Z): {'; '.join(errs)}")
