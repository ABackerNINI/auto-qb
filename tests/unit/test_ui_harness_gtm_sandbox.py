"""ui_harness gtm 发现指针隔离(_isolate_gtm_discovery)的防御性单测(issue 26-11-18-0308)。

归因(取证 2026-11-17): gtm 发现指针是**整机级用户级文件**(agent.pointer_dir 单点,
按平台解析), 而 scripts/ui_harness.py 只钉了 config_path/data_dir 到 mkdtemp —— 宿主
真跑 gtm 时桩进程 probe 真阳性 -> bundle.gtm 非 null -> tests/e2e/settings-backup.spec.mjs
的 bundle.gtm === null 断言整组红, 且导入用例的真 POST 会经 backup._apply_gtm_section
PUT 打到宿主真实 gtm 工具覆写其配置。

修复面是 scripts/ui_harness.py 的 _isolate_gtm_discovery(tmp)(与远端 30fac406 合流后
的机制): 把 agent.pointer_dir 单点 monkeypatch 到 <tmp>/gtm-pointer。本文件锁住
「隔离调用后指针面在桩私有目录里」这一事实 —— 红验: 调用前 agent.pointer_dir() 解析回
宿主真实平台目录, 与桩私有路径必然不同(判据非恒绿)。

平台边界: e2e 轨只在 Windows/Linux 开发机跑(_isolate_gtm_discovery docstring 同口径);
darwin 上平台目录解析走 ~/Library/Application Support 固定分支, 与 Win/Linux 实测面
不同 —— 两例在 darwin 一律 skip, 不做假红。

清理机制: _isolate_gtm_discovery 函数内**直写模块属性**(monkeypatch 追踪不到), 两例
用 try/finally 保存并恢复 agent.pointer_dir 原值, 不向 pytest 会话泄漏污染。

用例纯内存构造(不真动宿主指针), 不连 qB、不真跑 harness。

## 测试计划
- test_isolate_gtm_discovery_redirects_pointer_dir_into_tmp: 调 _isolate_gtm_discovery
  后 agent.pointer_dir() 返回 <tmp>/gtm-pointer(darwin skip, 见上平台边界);
- test_isolate_gtm_discovery_red_pre_call_resolves_platform_dir: 红验 -- 调用前
  agent.pointer_dir() 解析回宿主真实平台目录(不含桩 tmp 段), 调用后才落 <tmp>/gtm-pointer
  (证明隔离判据能区分新旧实现, 不是恒绿); darwin skip(同上)。
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

_DARWIN = sys.platform == "darwin"
_SKIP_REASON = (
    "darwin 平台目录解析走 ~/Library/Application Support 固定分支, 与 Win/Linux "
    "实测面不同 -- e2e 轨限 Win/Linux(见模块 docstring 平台边界)"
)


def _load_script(name: str):
    """scripts/ 不是包, 按路径加载(与 test_legacy_review4_scripts.py 同款做法);
    经 sys.modules 去重, 同一 pytest 进程里先加载过的模块直接复用。"""
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


@pytest.mark.skipif(_DARWIN, reason=_SKIP_REASON)  # owner: abacker
def test_isolate_gtm_discovery_redirects_pointer_dir_into_tmp(tmp_path):
    """_isolate_gtm_discovery 后 agent.pointer_dir() 单点返回 <tmp>/gtm-pointer。"""
    from auto_qb.core.traffic_source import agent as gtm_agent

    original = gtm_agent.pointer_dir
    try:
        mod = _load_script("ui_harness")
        mod._isolate_gtm_discovery(str(tmp_path))

        isolated = gtm_agent.pointer_dir()
        assert isolated == os.path.join(str(tmp_path), "gtm-pointer"), ("隔离后指针面必须落在桩私有 gtm-pointer 子目录")
        assert str(tmp_path) in isolated, "隔离后指针必须落在桩 tmp 里"
    finally:
        gtm_agent.pointer_dir = original


@pytest.mark.skipif(_DARWIN, reason=_SKIP_REASON)  # owner: abacker
def test_isolate_gtm_discovery_red_pre_call_resolves_platform_dir(tmp_path):
    """红验: 调用前 agent.pointer_dir() 解析回宿主真实平台目录, 判据非恒绿。"""
    from auto_qb.core.traffic_source import agent as gtm_agent

    original = gtm_agent.pointer_dir
    try:
        # 未隔离时按平台解析回真实用户级目录(修复前依赖宿主真值, 修复后必须无条件钉桩私有目录)
        bare = gtm_agent.pointer_dir()
        assert str(tmp_path) not in bare, ("未隔离时指针不得落在桩 tmp 里(否则隔离判据恒绿)")

        mod = _load_script("ui_harness")
        mod._isolate_gtm_discovery(str(tmp_path))

        assert gtm_agent.pointer_dir() == os.path.join(str(tmp_path), "gtm-pointer"), ("隔离后指针必须落进桩私有目录")
    finally:
        gtm_agent.pointer_dir = original
