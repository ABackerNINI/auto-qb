"""tests-real 基座 schema_version 字面量守卫(issue 26-11-08-0044 修复轮防复发).

## 测试计划
2026-11-10 issue 26-11-08-0044 修复(tests-real 各片基座 5→6)+ 评审 minor 防复发:
- test_tests_real_base_schema_version_is_current: 扫 tests-real/**/*.py(排除 .work/),
  所有 `schema_version: <int>`(YAML 模板形)与 `"schema_version": <int>`(dict 形)字面量
  必须等于 infra.versioning.CURRENT_VERSIONS["config"]; rm09 keys 域(WebUI 快捷键模板包
  版本, 非配置 schema)按 (文件, 值) 白名单豁免。产品 bump v7 时本守卫直接红, 基座不再
  静默走启动物化迁移改写+留 <名>.v<m>.bak 搅浑用例临时目录。
- test_guard_scan_still_sees_the_bases: 守卫自身活性自检 —— 至少扫到一处基座字面量,
  且白名单文件里的 keys 域豁免仍真实存在(白名单陈旧 = 扫描逻辑漂移, 必红)。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

from auto_qb.infra.versioning import CURRENT_VERSIONS

ROOT = Path(__file__).resolve().parents[1]
TESTS_REAL = ROOT / "tests-real"

# 两种字面量形: YAML 模板形(基座 CONFIG_TEMPLATE 等模板常量)与 dict 形(yaml.safe_dump
# 落盘前的 cfg 构造)。docstring 里的**散文**提法(schema_version: N 嵌在行文中)不匹配
# 两形、不在扫描面 —— 由坑档动作条款「docstring 措辞一并改」人工同步。
_YAML_FORM = re.compile(r"^\s+schema_version:\s*(\d+)\s*$", re.M)
_DICT_FORM = re.compile(r'"schema_version":\s*(\d+)')

# 非 config.yml schema 的同名字段豁免表: (相对路径, {合法值})。
# rm09 的 WebUI keys 存储(webui-keys.json, 快捷键模板包版本 1)与 422 负向(值 2)
# 与配置 schema 无关; 若 keys 域版本演进, 更新本表并同步 keys 用例。
_OTHER_DOMAIN = {
    "rm09_webui_write/test_rm09_webui_write.py": {1, 2},
}


def _scan() -> list[tuple[str, int, str]]:
    """扫 tests-real 全部 .py(排除 .work/ 草稿), 回 [(相对路径, 值, 字面量形)]。"""
    found: list[tuple[str, int, str]] = []
    for f in sorted(TESTS_REAL.rglob("*.py")):
        if ".work" in f.parts:
            continue
        rel = f.relative_to(TESTS_REAL).as_posix()
        text = f.read_text(encoding="utf-8")
        for m in _YAML_FORM.finditer(text):
            found.append((rel, int(m.group(1)), "yaml"))
        for m in _DICT_FORM.finditer(text):
            found.append((rel, int(m.group(1)), "dict"))
    return found


def test_tests_real_base_schema_version_is_current():
    current = CURRENT_VERSIONS["config"]
    stale = [
        (rel, val, form) for rel, val, form in _scan() if val != current and val not in _OTHER_DOMAIN.get(rel, set())
    ]
    assert not stale, (
        f"tests-real 基座 schema_version 字面量与产品现行版本 v{current} 不一致"
        "(会走启动物化迁移改写+留版本号备份, issue 26-11-08-0044 同款): " + "; ".join(f"{rel}={val}({form})" for rel, val, form in stale)
    )


def test_guard_scan_still_sees_the_bases():
    """守卫活性自检: 扫描面归零(基座全被删/改名)或白名单失效时, 守卫不得静默变空转。"""
    found = _scan()
    bases = [x for x in found if x[2] == "yaml" or x[2] == "dict"]
    assert bases, "守卫一处基座字面量都没扫到 —— 扫描逻辑或基座结构漂移, 守卫已空转"
    current = CURRENT_VERSIONS["config"]
    assert any(val == current for _rel, val, _form in bases), (f"扫描到的基座字面量无一等于现行 v{current} —— 扫描形与基座写法脱钩, 守卫已空转")
    for rel, values in _OTHER_DOMAIN.items():
        present = {val for _r, val, _f in found if _r == rel}
        assert values & present, f"豁免表条目 {rel} 值 {sorted(values)} 已不存在 —— 豁免表陈旧, 请核对 keys 域实况后更新"


if __name__ == "__main__":  # pragma: no cover
    sys.exit(pytest.main([__file__, "-q"]))
