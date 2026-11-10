"""dev.run 注入测试带守阵(计划 26-11-10-0515 S5)

装置三的工具链注入面回归闸门: dev.run(scripts/dev_run.py 包装)默认把 HR 发现口钉到
测试带 28788, 显式 --hr-prod-discovery 豁免回配置文件原值(生产带)。注入机制 = 产品 CLI
的 --hr-discovery-port CLI 覆盖(零 config 侵入: 只改本进程内存生效值, 配置文件/schema/
校验口径零触碰; 落点 QbManager 构造期 _apply_hr_discovery_override, 装载仍归 QbManager)。
本守阵钉四件事: 包装注入逻辑自身、CLI 覆盖的落点、main -> QbManager 的旗标接线、
dev.run -> 包装的接线不被回退。

## 测试计划
- test_inject_port_default_band: 未豁免 -> 注入 --hr-discovery-port 28788 且插在用户参数之前
- test_inject_port_user_explicit_kept: 用户显式 --hr-discovery-port 原样保留(排在注入值后, argparse 后者胜)
- test_inject_port_exempt_flag: --hr-prod-discovery 豁免 -> 不注入且旗标被剥掉(任意位置)
- test_override_applies_to_channel: 覆盖落到 channel.discovery_port(内存生效值)
- test_override_zero_and_absent: 覆盖 0 = 关闭发现; 缺省 None = 零行为变化(模型默认 18788 一字不动)
- test_main_wires_flag_to_manager: main 把旗标接线到 QbManager(hr_discovery_port_override 透传; 含 parse 级显式胜出回归)
- test_hot_reload_keeps_override: WebUI 保存热重载(新配置对象读自磁盘)后注入值仍在内存生效值上
- test_hot_reload_no_phantom_changes: 仅注入在身热重载 changes=0(覆盖重盖先于变更 diff)
- test_stub_default_is_test_band: hr_ext_stub.py 默认口 = 28788(生产带字面不作桩默认)
- test_dev_run_wiring: .commands/dev/config.toml 的 dev.run 走 scripts/dev_run.py 且豁免旗标在案
"""
from __future__ import annotations

import copy
import importlib.util
import os
import tempfile
import tomllib
from pathlib import Path
from unittest import mock

from auto_qb.config import Config
from auto_qb.config.models import HrCheckConfig
from auto_qb.core.qbmanager import _apply_hr_discovery_override
from helpers import make_manager

ROOT = Path(__file__).resolve().parent.parent


def _load_dev_run():
    spec = importlib.util.spec_from_file_location("dev_run", ROOT / "scripts" / "dev_run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------- 包装注入逻辑(scripts/dev_run.py::inject_port, 纯函数) ----------


def test_inject_port_default_band():
    dr = _load_dev_run()
    assert dr.TEST_BAND_DISCOVERY_PORT == 28788
    assert dr.inject_port(["config.yml", "--dry-run"]) == ["--hr-discovery-port", "28788", "config.yml", "--dry-run"]


def test_inject_port_user_explicit_kept():
    dr = _load_dev_run()
    out = dr.inject_port(["--hr-discovery-port", "12345", "config.yml"])
    # 注入值在最前、用户显式值在后: argparse 同名参数后者胜, 显式面永远赢过注入默认面
    assert out == ["--hr-discovery-port", "28788", "--hr-discovery-port", "12345", "config.yml"], out


def test_inject_port_exempt_flag():
    dr = _load_dev_run()
    assert dr.EXEMPT_FLAG == "--hr-prod-discovery"
    # 豁免: 不注入, 旗标自身剥掉(不留进产品 CLI 的 argv); 任意位置都剥
    assert dr.inject_port(["--hr-prod-discovery", "config.yml", "--dry-run"]) == ["config.yml", "--dry-run"]
    assert dr.inject_port(["config.yml", "--hr-prod-discovery"]) == ["config.yml"]


# ---------- CLI 覆盖落点(src/auto_qb/core/qbmanager.py::_apply_hr_discovery_override) ----------


def test_override_applies_to_channel():
    cfg = Config()  # 全默认实例: channel.discovery_port = 模型默认
    assert cfg.hr_check.channel.discovery_port == 18788
    _apply_hr_discovery_override(cfg, 28788)
    assert cfg.hr_check.channel.discovery_port == 28788


def test_override_zero_and_absent():
    cfg = Config()
    _apply_hr_discovery_override(cfg, 0)  # 显式 0 = 关闭发现(与配置键同口径)
    assert cfg.hr_check.channel.discovery_port == 0
    cfg2 = Config()
    _apply_hr_discovery_override(cfg2, None)  # 缺省 None = 零行为变化
    assert cfg2.hr_check.channel.discovery_port == 18788  # 生产带公开默认一字不动


# ---------- main -> QbManager 旗标接线(镜像 test_cli 的分发面桩) ----------


def test_main_wires_flag_to_manager():
    manager = mock.MagicMock()
    cfg = Config()
    argv_variants = [
        (["auto-qb", "config.yml", "--dry-run", "--hr-discovery-port", "28788"], 28788),
        (["auto-qb", "config.yml", "--dry-run"], None),  # 未传旗标: override=None(零行为变化)
        # parse 级优先级回归(评审 nit 2026-11-11): 注入值在前、显式值在后, 经真 argparse 实析
        # 后者胜 —— 只钉 argv 形状守不住「改插入位/解析前剥重」这类行为回退
        (["auto-qb", "--hr-discovery-port", "28788", "--hr-discovery-port", "12345", "config.yml", "--dry-run"], 12345),
    ]
    for argv, expected in argv_variants:
        with mock.patch("sys.argv", list(argv)), \
                mock.patch("auto_qb.cli.QbManager", return_value=manager) as m_qb, \
                mock.patch("auto_qb.cli.load_config", return_value=cfg):
            from auto_qb.cli import main

            main()
        assert m_qb.call_args.kwargs["hr_discovery_port_override"] == expected, argv


# ---------- 覆盖跨热重载保持(QbManager.apply_new_config 重盖面) ----------


def test_hot_reload_keeps_override():
    """WebUI 保存热重载: 新配置对象读自磁盘(discovery_port 回配置原值), 不重盖则
    监听身份判定会把 28788 -> 18788 当「身份变化」拆重挂端点, 注入被一次保存静默冲掉"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), cfg=Config(), hr_discovery_port_override=28788)
        assert mgr.config.hr_check.channel.discovery_port == 28788
        new_cfg = copy.copy(mgr.config)
        new_cfg.hr_check = HrCheckConfig()  # 重读盘形态: discovery_port 回模型默认 18788
        assert new_cfg.hr_check.channel.discovery_port == 18788
        mgr.apply_new_config(new_cfg)
        assert mgr.config.hr_check.channel.discovery_port == 28788  # 重盖后保持注入值


def test_hot_reload_no_phantom_changes():
    """仅注入在身、用户未改任何段 -> 热重载 changes 计数为 0(评审 major 2026-11-11):
    覆盖重盖必须先于变更 diff, 否则注入态下每次 WebUI 保存都多出一条幻影 hr_check 变更"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), cfg=Config(), hr_discovery_port_override=28788)
        new_cfg = copy.copy(mgr.config)
        new_cfg.hr_check = HrCheckConfig()  # 重读盘形态: 磁盘原值(无注入)
        result = mgr.apply_new_config(new_cfg)
        assert result["changes"] == 0, result  # 注入不产生幻影变更
        assert result["restart_required"] == []


# ---------- 桩默认与接线(文本级钉面; 桩在 scripts/ 不受限, 守阵只断言默认值) ----------


def test_stub_default_is_test_band():
    stub_src = (ROOT / "scripts" / "hr_ext_stub.py").read_text(encoding="utf-8")
    assert "default=28788" in stub_src
    assert "default=18788" not in stub_src  # 生产带字面不得作桩默认(显式 --discovery-port 才回生产带)


def test_dev_run_wiring():
    with open(ROOT / ".commands" / "dev" / "config.toml", "rb") as f:
        dev_pack = tomllib.load(f)
    task = dev_pack["tasks"]["dev.run"]
    assert "scripts/dev_run.py" in task["run"][0], task  # 接线不被回退成直跑 src/auto-qb.py
    assert "--hr-prod-discovery" in task["note"], task  # 豁免口在案(风险表对策面)
