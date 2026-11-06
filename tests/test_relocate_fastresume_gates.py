"""test_relocate_fastresume_gates 测试计划: fastresume 收尾链 S1 配置面 + 预检部署闸门
(计划 26-11-05-0808 §04 S1: bt_backup 配置键 + 五类闸门中的后端/可达/AutoTMM 三类)

覆盖面(全部替身, 不依赖真机 qB; D/E 形态真机演示按计划留 S6 复跑):
- 配置面: config.bt_backup 各 qB 实例路径表({host:port: 路径})的缺省/校验/loader/查表单点
  (bt_backup_path_of, 鸭子类型 —— 真实 Config 与测试替身同口径)。
- 部署维闸门(relocate_precheck 前置 + relocate_execute 执行体同拦, S6 真机复跑发现执行
  路径漏拦已补 —— 预检不是唯一入口, web 按钮/规则 move_to 都经执行体):
  E 格 = 存储后端非 Legacy(app/preferences 直读 resume_data_storage_type, D2 fail-fast);
  D 格 = BT_backup 未配置/不可达不可写(存在性 + os.access 探测, 运行期零写入)。
- 组级闸门(evaluate_group, 预检与规则执行共用): AutoTMM 成员(fastresume 无 qBt-savePath
  键, N8 实测)有即整组拒迁。

## 测试计划(每个测试函数一条)
- test_bt_backup_defaults_and_lookup: 缺省空表 = 功能未启用; bt_backup_path_of 按
  qbittorrent(host:port)查表命中/缺失/替身缺属性三态
- test_bt_backup_validate_shapes: 段缺省合法; 非字典/坏键(无冒号/坏端口)/非字符串与空值
  逐条进聚合报错(多条错误一次报全, 法则 4)
- test_bt_backup_load_config_round_trip: load_config 真链路(剥空 -> 校验 -> 解析);
  段缺省 = {}; 键值剥空白; 非法形状启动期 ConfigError
- test_is_legacy_resume_storage: 0/"0"/"legacy"/None/空 = Legacy; 1/"1"/"sqlite"/其它 = 非
- test_probe_bt_backup_reject: 空路径/不存在拒; 真实存在且可写过; os.access 判负拒
  (monkeypatch os.access, 验权限位分支文案)
- test_backend_gate_sqlite_rejected: resume_data_storage_type=1 -> 整请求一条 blocked,
  gate=backend, 文案含 Legacy 与 E 格口径
- test_backend_gate_fail_closed: app_preferences 抛错 -> gate=backend(读不到按不可用拒)
- test_backend_gate_missing_key_is_legacy: 偏好无该键(旧 qB) -> 不拦, 落到后续闸门
- test_bt_backup_gate_unconfigured: 表空 -> gate=bt_backup, 文案含配置键与实例身份
- test_bt_backup_gate_unreachable: 指到不存在的目录 -> gate=bt_backup
- test_deployment_gate_order_backend_first: 后端与 BT_backup 同时不满足 -> 先报 backend
  (E 格先于 D 格, 单回执短路面)
- test_deployment_gate_before_group_verdicts: 部署闸拒绝时分组判定不执行(store 无成员也
  拒同文) —— 部署维先于组维
- test_backend_gate_blocks_execute_sqlite: 执行体同拦 E 格(relocate_execute 于 SQLite ->
  blocked gate=backend, 零建账)
- test_bt_backup_gate_blocks_execute_unreachable: 执行体同拦 D 格(坏路径 -> gate=bt_backup)
- test_execute_deployment_gate_after_idempotent_skips: 部署闸不遮幂等(T3)—— 全组已在
  目标位置时即便 SQLite 后端也照旧 skip, 闸只拦新发起
- test_auto_tmm_member_blocks_group: 全链预检(替身环境)组内 HA auto_tmm=true ->
  blocked + gate=auto_tmm; 双成员手动 -> 无 auto_tmm 理由(对照面)
- test_auto_tmm_gate_pure: evaluate_group 纯函数面: auto_tmm_hashes 非空即 block, 文案点名
  成员; 空元组零理由(缺省字段向后兼容既有 GroupFacts 构造)
- test_bt_backup_section_claimed_and_apply: RelocateModule 认领 bt_backup(P6); apply 两段
  全等 none / 仅 bt_backup 变 reloaded(现读, 不换 relocate 缓存)/ relocate 变换缓存
- test_nested_target_boundaries_pure: nested_target_on 成分级边界(E2.3 8/8): 子目录/深层/
  尾斜杠/大小变体(Windows 口径)判嵌套; 兄弟(待删2)/前缀同串(待删除)/父目录/等值 job dst/
  终态 job 不误伤; 活跃 job src/dst 之下命中并区分文案
- test_nested_target_blocks_group: 全链预检 target=成员源内子目录 -> blocked + gate=nested
- test_source_missing_blocks_group: 源盘真实文件删除 -> gate=source_missing, 文案点名文件
- test_source_qb_twin_deep_reuses_qb_temp: 深层 .!qB 孪生(E2.1 漏拦形态) -> 复用既有
  gate=qb_temp(不另造 id), 深层路径被逐文件判定覆盖
- test_source_unknown_blocks_group: fa.exists 全程不可判定 -> gate=source_unknown(保守拒)
- test_unwanted_files_exempt_from_missing: priority=0 的缺文件不构成缺失(误报防线);
  同一文件 wanted(priority 缺省)则照拦(对照面)
"""
import os
import types

import pytest
import yaml

from auto_qb.config import load_config
from auto_qb.config.models import Config, bt_backup_path_of
from auto_qb.config.validation import validate_config
from auto_qb.core.modules import relocate_units as ru
from auto_qb.core.modules.relocate_plan import (
    GroupFacts,
    is_legacy_resume_storage,
    probe_bt_backup_reject,
)
from auto_qb.core.modules.relocate_units import nested_target_on
from helpers import pin_disk_usage, relocate_env
from relocate_exec_support import _stub_cap


def _validate(spec):
    return validate_config({"config": {"bt_backup": spec}})


# ---------- 配置面 ----------


def test_bt_backup_defaults_and_lookup():
    """缺省空表 = 功能未启用; bt_backup_path_of 查表: 命中/缺失/替身缺属性三态"""
    cfg = Config()
    assert cfg.bt_backup == {}
    assert bt_backup_path_of(cfg) == ""
    cfg.qbittorrent.port = 16585  # 真实 Config 默认 8080; 显式对齐 FakeConfig 惯用的实例身份
    cfg.bt_backup = {"127.0.0.1:16585": "D:/qB/BT_backup"}
    assert bt_backup_path_of(cfg) == "D:/qB/BT_backup"
    # 查表键 = qbittorrent 连接身份: 换端口即命中另一实例(多实例口径)
    cfg.qbittorrent.port = 26586
    assert bt_backup_path_of(cfg) == ""
    # 值剥空白口径由 loader 保证, 查表只兜底 strip
    cfg.bt_backup = {"127.0.0.1:26586": "  D:/qB2/BT_backup  "}
    assert bt_backup_path_of(cfg) == "D:/qB2/BT_backup"
    # 鸭子类型: 替身配置(无 bt_backup 属性)与 None 均安全回落 ""
    assert bt_backup_path_of(types.SimpleNamespace(qbittorrent=cfg.qbittorrent)) == ""
    assert bt_backup_path_of(None) == ""


def test_bt_backup_validate_shapes():
    """形状校验: 缺省合法; 非字典/坏键/非字符串值逐条聚合, 多错一次报全(法则 4)"""
    assert _validate(None) == []
    assert _validate({}) == []
    assert _validate({"127.0.0.1:16585": "D:/qB/BT_backup"}) == []
    assert _validate({"localhost:8080": "/var/lib/qbt/BT_backup"}) == []

    errors = _validate("D:/x")
    assert errors == ["config.bt_backup: 必须是字典(键 = qB 连接身份 host:port, 值 = 该实例的 BT_backup 目录路径)"], errors

    # 聚合: 坏键 + 坏值同时报, 互不打断
    errors = _validate({"no-port-key": "D:/a", "127.0.0.1:99999": 123, "127.0.0.1:70000": ""})
    assert any("no-port-key" in e and "host:port" in e for e in errors), errors
    assert any("99999" in e and "1-65535" in e for e in errors), errors
    assert any("70000" in e and "非空路径字符串" in e for e in errors), errors
    assert any("99999" in e and "非空路径字符串" in e for e in errors), errors  # 值类型错独立报

    # 键只有端口段(host 空)同样拒
    errors = _validate({":8080": "D:/a"})
    assert any("host:port" in e for e in errors), errors


def test_bt_backup_load_config_round_trip(tmp_path):
    """load_config 真链路: 剥空 -> 校验 -> 解析; 段缺省 = {}; 键值剥空白; 非法形状启动期报错"""
    from auto_qb.config.errors import ConfigError

    cfg_path = tmp_path / "c.yml"
    cfg_path.write_text(
        yaml.safe_dump(
            {
                "config":
                    {
                        "qbittorrent": {
                            "host": "127.0.0.1",
                            "port": "16585"
                        },
                        "bt_backup": {
                            "  127.0.0.1:16585  ": "  D:/qB/BT_backup  "
                        },
                    }
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    cfg = load_config(str(cfg_path))
    assert cfg.bt_backup == {"127.0.0.1:16585": "D:/qB/BT_backup"}
    assert bt_backup_path_of(cfg) == "D:/qB/BT_backup"

    cfg_path.write_text(yaml.safe_dump({"config": {"main_tick": "3S"}}, allow_unicode=True), encoding="utf-8")
    assert load_config(str(cfg_path)).bt_backup == {}  # 段缺省 = 未启用

    bad = tmp_path / "bad.yml"
    bad.write_text(yaml.safe_dump({"config": {"bt_backup": {"bad-key": "D:/x"}}}, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ConfigError) as ei:
        load_config(str(bad))
    assert "config.bt_backup" in str(ei.value), ei.value


# ---------- 探测/后端纯函数 ----------


def test_is_legacy_resume_storage():
    """resume_data_storage_type 归一: 0/"0"/"legacy"/None(旧 qB 无键)/空 = Legacy; 其余非"""
    assert is_legacy_resume_storage(0) is True
    assert is_legacy_resume_storage("0") is True
    assert is_legacy_resume_storage("legacy") is True
    assert is_legacy_resume_storage("LEGACY") is True
    assert is_legacy_resume_storage(None) is True  # SQLite 选项出现之前的 qB
    assert is_legacy_resume_storage("") is True
    assert is_legacy_resume_storage(1) is False
    assert is_legacy_resume_storage("1") is False
    assert is_legacy_resume_storage("sqlite") is False
    assert is_legacy_resume_storage("SQLite") is False
    assert is_legacy_resume_storage(2) is False


def test_probe_bt_backup_reject(tmp_path, monkeypatch):
    """BT_backup 探测: 空路径/不存在拒(文案含路径与 D 格口径); 真实存在可写过;
    os.access 判负拒(monkeypatch 权限位, 零写入铁律下权限分支的确定性验证)"""
    assert "空值" in probe_bt_backup_reject("")
    assert "空值" in probe_bt_backup_reject("   ")

    missing = os.path.join(str(tmp_path), "nope")
    reject = probe_bt_backup_reject(missing)
    assert "不存在" in reject and "D 格" in reject, reject

    assert probe_bt_backup_reject(str(tmp_path)) == ""  # 真实存在 + 进程可写

    real_access = os.access
    # 探测内部走长路径前缀(\\?\...), 判负面按「路径含 tmp_path」匹配
    monkeypatch.setattr(os, "access", lambda p, m: False if str(tmp_path) in str(p) else real_access(p, m))
    reject = probe_bt_backup_reject(str(tmp_path))
    assert "不可读写" in reject and "D 格" in reject, reject


# ---------- 部署维闸门(relocate_precheck 前置) ----------


def _gate_env(tmp_path, monkeypatch, data_dir=False):
    """闸门用替身环境: relocate 开 + 真实成员组 + 部署闸全放行的默认面(用例按需改坏)

    能力探测一并替身(hermetic: 组级判定面不依赖真机链接探测; 纯部署闸用例它根本跑不到)。
    data_dir=True 时 relocate_env 设 mgr.config.data_dir(执行体建账落盘位置)。
    """
    pin_disk_usage(monkeypatch)
    _stub_cap(monkeypatch, file_kind="hardlink")
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="pausedUP", data_dir=data_dir)
    mgr.config.relocate.enabled = True
    mgr.config.bt_backup["127.0.0.1:16585"] = str(tmp_path)
    return mgr, client, dst, tmp_path


def test_backend_gate_sqlite_rejected(tmp_path, monkeypatch):
    """E 格: resume_data_storage_type=1(SQLite) -> 整请求一条 blocked, gate=backend"""
    mgr, client, dst, _td = _gate_env(tmp_path, monkeypatch)
    client.app_preferences = lambda **kw: {"resume_data_storage_type": 1}
    mod = mgr.host.get("relocate")
    items = mod.relocate_precheck(["HA", "HB"], dst)
    assert len(items) == 1, items
    it = items[0]
    assert set(it) == {"hashes", "cls", "reasons"}, it
    assert it["cls"] == "blocked" and it["hashes"] == ["HA", "HB"], it
    r = it["reasons"][0]
    assert r["gate"] == "backend", r
    assert "Legacy" in r["text"] and "SQLite" in r["text"] and "E 格" in r["text"], r


def test_backend_gate_fail_closed(tmp_path, monkeypatch):
    """app_preferences 抛错 -> 读不到后端按不可用拒(fail-closed, gate=backend)"""
    mgr, client, dst, _td = _gate_env(tmp_path, monkeypatch)

    def _boom(**kw):
        raise RuntimeError("connection reset")

    client.app_preferences = _boom
    mod = mgr.host.get("relocate")
    it = mod.relocate_precheck(["HA"], dst)[0]
    assert it["cls"] == "blocked" and it["reasons"][0]["gate"] == "backend", it
    assert "app/preferences" in it["reasons"][0]["text"], it


def test_backend_gate_missing_key_is_legacy(tmp_path, monkeypatch):
    """偏好无 resume_data_storage_type(旧 qB) -> 按 Legacy 放行, 不落 backend 闸"""
    mgr, client, dst, _td = _gate_env(tmp_path, monkeypatch)
    client.app_preferences = lambda **kw: {"alt_up_limit": 0}
    mod = mgr.host.get("relocate")
    items = mod.relocate_precheck(["HA"], dst)
    assert not any(r.get("gate") == "backend" for it in items for r in it.get("reasons", [])), items


def test_bt_backup_gate_unconfigured(tmp_path, monkeypatch):
    """D 格(未配置): 表空 -> gate=bt_backup, 文案含配置键名与当前实例身份(host:port)"""
    mgr, client, dst, _td = _gate_env(tmp_path, monkeypatch)
    mgr.config.bt_backup = {}
    mod = mgr.host.get("relocate")
    it = mod.relocate_precheck(["HA"], dst)[0]
    assert it["cls"] == "blocked" and it["hashes"] == ["HA"], it
    r = it["reasons"][0]
    assert r["gate"] == "bt_backup", r
    assert "config.bt_backup" in r["text"] and "127.0.0.1:16585" in r["text"], r


def test_bt_backup_gate_unreachable(tmp_path, monkeypatch):
    """D 格(不可达): 指到不存在的目录 -> gate=bt_backup, 文案含路径"""
    mgr, client, dst, _td = _gate_env(tmp_path, monkeypatch)
    mgr.config.bt_backup["127.0.0.1:16585"] = os.path.join(str(tmp_path), "missing-bt")
    mod = mgr.host.get("relocate")
    it = mod.relocate_precheck(["HA"], dst)[0]
    assert it["cls"] == "blocked" and it["reasons"][0]["gate"] == "bt_backup", it
    assert "missing-bt" in it["reasons"][0]["text"], it


def test_deployment_gate_order_backend_first(tmp_path, monkeypatch):
    """后端与 BT_backup 同时不满足 -> 单回执只报 backend(E 格先判, 短路面不叠报)"""
    mgr, client, dst, _td = _gate_env(tmp_path, monkeypatch)
    client.app_preferences = lambda **kw: {"resume_data_storage_type": 1}
    mgr.config.bt_backup = {}
    mod = mgr.host.get("relocate")
    items = mod.relocate_precheck(["HA"], dst)
    assert len(items) == 1 and items[0]["reasons"][0]["gate"] == "backend", items


def test_deployment_gate_before_group_verdicts(tmp_path, monkeypatch):
    """部署闸先于组维: 拒绝时不进分组判定(store 连成员都没有也照样拒同文)"""
    mgr, client, dst, _td = _gate_env(tmp_path, monkeypatch)
    mgr.config.bt_backup = {}
    mgr.store.by_hash.clear()
    mod = mgr.host.get("relocate")
    it = mod.relocate_precheck(["GHOST"], dst)[0]
    assert it["cls"] == "blocked" and it["reasons"][0]["gate"] == "bt_backup", it
    assert it["hashes"] == ["GHOST"], it


# ---------- 部署维闸门 · 执行路径(计划 26-11-05-0808 S1/D2: fail-fast 不限预检) ----------


def test_backend_gate_blocks_execute_sqlite(tmp_path, monkeypatch):
    """执行体同拦 E 格: relocate_execute(web 按钮/规则 move_to 共用入口)于 SQLite 后端 ->
    blocked gate=backend, 且零建账(relocate 目录无 spec/journal, 零副作用)"""
    mgr, client, dst, td = _gate_env(tmp_path, monkeypatch, data_dir=True)
    client.app_preferences = lambda **kw: {"resume_data_storage_type": 1}
    mod = mgr.host.get("relocate")
    it = mod.relocate_execute(["HA"], dst)[0]
    assert it["cls"] == "blocked" and it["reasons"][0]["gate"] == "backend", it
    assert "Legacy" in it["reasons"][0]["text"] and "E 格" in it["reasons"][0]["text"], it
    assert not (td / "data" / "relocate").exists() or not list((td / "data" / "relocate").glob("*")), "零建账被破"


def test_bt_backup_gate_blocks_execute_unreachable(tmp_path, monkeypatch):
    """执行体同拦 D 格: bt_backup 指向不存在目录 -> relocate_execute blocked gate=bt_backup"""
    mgr, client, dst, _td = _gate_env(tmp_path, monkeypatch, data_dir=True)
    mgr.config.bt_backup["127.0.0.1:16585"] = os.path.join(str(tmp_path), "missing-bt")
    mod = mgr.host.get("relocate")
    it = mod.relocate_execute(["HA"], dst)[0]
    assert it["cls"] == "blocked" and it["reasons"][0]["gate"] == "bt_backup", it
    assert "missing-bt" in it["reasons"][0]["text"], it


def test_execute_deployment_gate_after_idempotent_skips(tmp_path, monkeypatch):
    """部署闸不遮幂等(T3 降噪): 全组已在目标位置时即便 SQLite 后端也照旧 skip;
    部署闸只拦「会产生新收尾工作」的发起"""
    mgr, client, dst, _td = _gate_env(tmp_path, monkeypatch, data_dir=True)
    client.app_preferences = lambda **kw: {"resume_data_storage_type": 1}
    mod = mgr.host.get("relocate")
    for rec in ("HA", "HB"):
        mgr.store.by_hash[rec].save_path = dst
    it = mod.relocate_execute(["HA"], dst)[0]
    assert it["cls"] == "skip" and it["reasons"] == [], it
    assert "已在目标位置" in (it["notes"] or [""])[0], it


# ---------- AutoTMM 组级闸门 ----------


def test_auto_tmm_member_blocks_group(tmp_path, monkeypatch):
    """全链预检: 组内 HA auto_tmm=true -> blocked + gate=auto_tmm(点名成员);
    对照面: 双成员手动 -> 无 auto_tmm 理由(其余闸门照旧)"""
    mgr, client, dst, td = _gate_env(tmp_path, monkeypatch)
    mod = mgr.host.get("relocate")
    mgr.store.by_hash["HA"].auto_tmm = True
    it = mod.relocate_precheck(["HA"], dst)[0]
    assert it["cls"] == "blocked", it
    r = next(r for r in it["reasons"] if r["gate"] == "auto_tmm")
    assert "AutoTMM" in r["text"] and "HA" in r["text"], r

    mgr.store.by_hash["HA"].auto_tmm = False
    it = mod.relocate_precheck(["HA"], dst)[0]
    assert not any(r["gate"] == "auto_tmm" for r in it["reasons"]), it


def test_auto_tmm_gate_pure():
    """evaluate_group 纯函数面: auto_tmm_hashes 非空即 block 并点名成员; 缺省空元组零理由
    (GroupFacts 既有构造不传该字段, 行为向后兼容)"""
    facts = GroupFacts(
        hashes=("HA", "HB"),
        mover="HA",
        name="Show",
        save_path="D:/src",
        target="D:/dst",
        files=(("Show/e00.mkv", 64), ),
        auto_tmm_hashes=("HB", ),
    )
    out = ru.evaluate_group(facts)
    assert out["cls"] == ru.CLS_BLOCKED, out
    r = next(r for r in out["reasons"] if r["gate"] == ru.GATE_AUTO_TMM)
    assert "HB" in r["text"] and "qBt-savePath" in r["text"], r

    plain = GroupFacts(
        hashes=("HA", ),
        mover="HA",
        name="Show",
        save_path="D:/src",
        target="D:/dst",
        files=(("Show/e00.mkv", 64), ),
    )
    out = ru.evaluate_group(plain)
    assert not any(r["gate"] == ru.GATE_AUTO_TMM for r in out["reasons"]), out


# ---------- 段认领与热重载面(claim 守阵 P6 / apply 短路契约) ----------


def test_bt_backup_section_claimed_and_apply():
    """RelocateModule 认领 bt_backup(P6 段认领完备); apply 契约: 两段全等 = none;
    仅 bt_backup 变 = reloaded(现读回执, relocate 缓存不换); relocate 变 = reloaded + 换缓存"""
    from auto_qb.config.models import RelocateConfig
    from auto_qb.core.modules.relocate_mod import RelocateModule

    mod = RelocateModule()
    assert "bt_backup" in mod.sections(), mod.sections()
    same = Config()
    assert mod.apply(same, same).action == "none"

    bt_changed = Config()
    bt_changed.bt_backup = {"127.0.0.1:8080": "D:/x/BT_backup"}
    res = mod.apply(same, bt_changed)
    assert res.action == "reloaded" and "bt_backup" in (res.detail or ""), res
    assert mod._conf is None, "仅 bt_backup 变不得换 relocate 生效缓存"

    rel_changed = Config()
    rel_changed.relocate = RelocateConfig(enabled=True)
    res = mod.apply(same, rel_changed)
    assert res.action == "reloaded" and mod._conf is rel_changed.relocate, res


# ---------- 嵌套目标闸门(0546 机制③, 成分级) ----------


def _job(job_id, src, dst, phase=ru.PHASE_ARMED):
    return ru.RelocateJob(job_id=job_id, hashes=("HX", ), mover="HX", src=src, dst=dst, scope=src, phase=phase)


def test_nested_target_boundaries_pure():
    """nested_target_on 成分级边界(E2.3 8/8): 嵌套全拦(子目录/深层/尾斜杠/大小变体@Windows),
    兄弟/前缀同串/父目录/等值 job dst/终态 job 不误伤; 活跃 job src/dst 之下命中并区分文案"""
    # 嵌套: 子目录 / 深层 / 尾斜杠源
    assert "声明源之下" in nested_target_on("D:/src/sub", ("D:/src", ), ())
    assert "声明源之下" in nested_target_on("D:/src/a/b/c", ("D:/src/", ), ())
    # 兄弟目录 / 前缀同串 / 父目录: 不误伤
    assert nested_target_on("D:/待删2", ("D:/待删", ), ()) == ""
    assert nested_target_on("D:/待删2/x", ("D:/待删除", ), ()) == ""
    assert nested_target_on("D:/src", ("D:/src/sub", ), ()) == ""
    # 大小写变体: _norm 平台口径(Windows 折叠判嵌套; POSIX 大小写敏感判不嵌)
    if os.path.normcase("A") == "a":
        assert "声明源之下" in nested_target_on("D:/SRC/x", ("D:/src", ), ())
    else:
        assert nested_target_on("D:/SRC/x", ("D:/src", ), ()) == ""
    # 活跃 job: src 之下(含等于 src)与 dst 之下命中, 文案区分; 等值 dst 不算嵌套
    job = _job("j1", "D:/jobsrc", "D:/jobdst")
    assert "声明源之下" in nested_target_on("D:/jobsrc/inner", ("D:/elsewhere", ), (job, ))
    assert "声明源之下" in nested_target_on("D:/jobsrc", ("D:/elsewhere", ), (job, ))
    assert "声明目标之下" in nested_target_on("D:/jobdst/inner", ("D:/elsewhere", ), (job, ))
    assert nested_target_on("D:/jobdst", ("D:/elsewhere", ), (job, )) == ""
    # 终态 job 不参与
    done = _job("j2", "D:/jobsrc", "D:/jobdst", phase=ru.PHASE_DONE)
    assert nested_target_on("D:/jobsrc/inner", ("D:/elsewhere", ), (done, )) == ""


def test_nested_target_blocks_group(tmp_path, monkeypatch):
    """全链预检: target = 成员源内子目录 -> blocked + gate=nested(点名 ⊆ 关系)"""
    mgr, client, dst, td = _gate_env(tmp_path, monkeypatch)
    mod = mgr.host.get("relocate")
    it = mod.relocate_precheck(["HA"], os.path.join(str(td), "src", "sub"))[0]
    assert it["cls"] == "blocked", it
    r = next(r for r in it["reasons"] if r["gate"] == "nested")
    assert "声明源之下" in r["text"], r


# ---------- 源侧三态(0546 机制①; .!qB 态复用 GATE_QB_TEMP) ----------


def test_source_missing_blocks_group(tmp_path, monkeypatch):
    """源盘真实文件被删(数据藏走, E2.2) -> gate=source_missing, 文案点名文件"""
    mgr, client, dst, td = _gate_env(tmp_path, monkeypatch)
    mod = mgr.host.get("relocate")
    os.remove(os.path.join(str(td), "src", "Show", "e00.mkv"))
    it = mod.relocate_precheck(["HA"], dst)[0]
    assert it["cls"] == "blocked", it
    r = next(r for r in it["reasons"] if r["gate"] == "source_missing")
    assert "e00.mkv" in r["text"] and "零搬移" in r["text"], r


def test_source_qb_twin_deep_reuses_qb_temp(tmp_path, monkeypatch):
    """深层 .!qB 孪生(E2.1 现行顶层扫描漏拦形态) -> 复用既有 gate=qb_temp(不另造 id):
    三态收集把深层孪生并入 qb_temp_entries, 深层路径由逐声明文件判定天然覆盖"""
    pin_disk_usage(monkeypatch)
    _stub_cap(monkeypatch, file_kind="hardlink")
    rel = "Show/data/b/c/f3.bin"
    mgr, client, src, dst, content, files = relocate_env(tmp_path, paths=(rel, ), state="pausedUP", data_dir=False)
    mgr.config.relocate.enabled = True
    mgr.config.bt_backup["127.0.0.1:16585"] = str(tmp_path)
    mod = mgr.host.get("relocate")
    real = os.path.join(str(tmp_path), "src", *rel.split("/"))
    os.rename(real, real + ".!qB")  # 深层孪生化: 原名不在、孪生在(内容根顶层扫描看不到)
    it = mod.relocate_precheck(["HA"], dst)[0]
    assert it["cls"] == "blocked", it
    r = next(r for r in it["reasons"] if r["gate"] == "qb_temp")
    assert "f3.bin.!qB" in r["text"], r


def test_source_unknown_blocks_group(tmp_path, monkeypatch):
    """fa.exists 全程不可判定(容器映射 miss 同效) -> gate=source_unknown(保守拒, D2 口径)"""
    from auto_qb.infra import file_access as fa_mod

    _stub_cap(monkeypatch, file_kind="hardlink")
    mgr, client, dst, td = _gate_env(tmp_path, monkeypatch)
    mod = mgr.host.get("relocate")
    src_root = os.path.join(str(tmp_path), "src")

    class _UnkFA:
        def exists(self, p):
            return fa_mod.UNDETERMINED if str(p).startswith(src_root) else os.path.isdir(p)

        def isdir(self, p):
            return os.path.isdir(p)

        def scandir(self, p):
            return []

        def disk_usage(self, p):
            return types.SimpleNamespace(free=1 << 40, total=1 << 41, used=0)

    monkeypatch.setattr(fa_mod, "get_file_access", lambda: _UnkFA())
    it = mod.relocate_precheck(["HA"], dst)[0]
    assert it["cls"] == "blocked", it
    r = next(r for r in it["reasons"] if r["gate"] == "source_unknown")
    assert "不可判定" in r["text"], r


def test_unwanted_files_exempt_from_missing(tmp_path, monkeypatch):
    """priority=0(未勾选)的缺文件不构成缺失形态(本就不落盘, 误报防线);
    同一文件 wanted(priority 缺省=1)则照拦 —— 过滤面只看优先级, 不看存在性"""
    mgr, client, dst, td = _gate_env(tmp_path, monkeypatch)
    mod = mgr.host.get("relocate")
    rec = mgr.store.by_hash["HA"]
    rec._files = [
        types.SimpleNamespace(name="Show/e00.mkv", size=64),
        types.SimpleNamespace(name="Show/e01.mkv", size=64),
        types.SimpleNamespace(name="Show/unwanted.bin", size=10, priority=0),  # 磁盘上没有
    ]
    it = mod.relocate_precheck(["HA"], dst)[0]
    assert not any(r["gate"] == "source_missing" for r in it["reasons"]), it

    rec._files = [
        types.SimpleNamespace(name="Show/e00.mkv", size=64),
        types.SimpleNamespace(name="Show/e01.mkv", size=64),
        types.SimpleNamespace(name="Show/unwanted.bin", size=10),  # 无 priority 属性 = wanted
    ]
    it = mod.relocate_precheck(["HA"], dst)[0]
    assert any(r["gate"] == "source_missing" for r in it["reasons"]), it
