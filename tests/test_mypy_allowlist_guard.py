"""mypy allowlist 守阵: pyproject [tool.mypy] overrides 豁免清单只减不增(计划 26-11-05-0635 §04 S4, 拍板 D3)

设计不变量(计划 §01): 抵抗面豁免清单冻结进守阵, 新增豁免必须显式改本文件的冻结清单 ——
摩擦是有意的, 摩擦逼着每一条新豁免都留下理由。递减(移除豁免/收紧错误码)不红: 那是
「allowlist 递减」主轴的正向推进。

冻结口径(与任务规格一致):
- ignore_errors = true 的模块模式集合(整模块豁免, 最粗粒度);
- disable_error_code 的 (模块模式, 错误码) 豁免对集合(错误码级豁免)。
真仓 pyproject.toml 静态解析出这两张清单后与冻结清单对照: 出现**新增**条目即红;
**减少**不红。disallow_untyped_defs 收紧面不属于豁免, 不在对账范围(它是递减的推进方式,
新增收紧应当红不起来才对)。

按拍板 D3: 本守阵只做静态扫描, **不在 pytest 内跑 mypy** —— dev.typecheck 是独立任务
(`commands run dev.typecheck`), 豁免面外全绿由它验收。

检出能力由合成 TOML 红验内建: 解析形态(list/单字符串/缺键)、新增豁免变红、递减不红
各有断言, 解析或对账逻辑退化即红。

## 测试计划(每个测试函数一条)

- test_parse_overrides_handles_list_and_string_forms: module / disable_error_code 的列表与单字符串两种形态都能解析; 缺省键(ignore_errors 未设 / 无 disable_error_code)安全跳过
- test_parse_collects_ignore_modules_and_disable_pairs: ignore_errors 模块集合与 (模块模式, 码) 对集合正确产出, 混合多条 overrides 不串
- test_frozen_rejects_new_exemption: 合成 pyproject 出现冻结外的新 ignore 模块或新 (模块, 码) 对 -> finding 指名新增项(红验内建)
- test_frozen_allows_reduction_and_equality: 合成 pyproject 豁免等于或少于冻结清单 -> 零 finding(递减不红)
- test_repo_allowlist_matches_frozen: 真仓 pyproject 解析结果新增面 = 空(新增豁免即红; 递减不红)
"""

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

# ---- 解析 ---------------------------------------------------------------------------------------------


def parse_overrides(data: dict) -> tuple[set[str], set[tuple[str, str]]]:
    """从已解析的 pyproject dict 提取 (ignore_errors 模块模式集合, (模块模式, 错误码) 豁免对集合)。

    module 与 disable_error_code 均接受 list 或单字符串两种 TOML 形态; 缺省键安全跳过。
    """
    ignore_modules: set[str] = set()
    disable_pairs: set[tuple[str, str]] = set()
    overrides = data.get("tool", {}).get("mypy", {}).get("overrides", [])
    for ov in overrides:
        modules = ov.get("module", [])
        if isinstance(modules, str):
            modules = [modules]
        codes = ov.get("disable_error_code", [])
        if isinstance(codes, str):
            codes = [codes]
        if ov.get("ignore_errors"):
            ignore_modules.update(modules)
        for code in codes:
            disable_pairs.update((m, code) for m in modules)
    return ignore_modules, disable_pairs


def parse_pyproject(toml_text: str) -> tuple[set[str], set[tuple[str, str]]]:
    """解析 TOML 文本 -> parse_overrides。"""
    return parse_overrides(tomllib.loads(toml_text))


# ---- 冻结清单(2026-11-06 S4 基线, 与 pyproject 注释逐条对应) -------------------------------------------
# 每条 (模块模式列表, 码列表); 新增豁免必须在此同步登记并写理由, 守阵才放行。

_FROZEN_DISABLE_GROUPS: list[tuple[list[str], list[str]]] = [
    # ③ core/modules + hr service mixin 组合面(attr-defined/has-type)与 Optional 次生噪音
    (
        ["auto_qb.core.modules.*", "auto_qb.hr.service_wave", "auto_qb.hr.service_status"],
        [
            "attr-defined", "has-type", "union-attr", "arg-type", "assignment", "operator", "misc", "return-value",
            "call-arg", "call-overload"
        ],
    ),
    # ④ qbapi 三方 Facade 转发 + qbmanager/state/codec/tvshows/grid Optional 收窄
    (
        [
            "auto_qb.core.qbapi",
            "auto_qb.core.qbmanager",
            "auto_qb.core.state",
            "auto_qb.core.traffic_store_codec",
            "auto_qb.core.tvshows",
            "auto_qb.core.traffic_grid",
        ],
        ["union-attr", "return-value", "arg-type", "assignment", "operator", "call-overload"],
    ),
    # ⑤ qbclient._session 对三方基类签名不兼容
    (["auto_qb.core.qbclient"], ["override"]),
    # ⑥ hr store/model/server Optional 收窄
    (["auto_qb.hr.store", "auto_qb.hr.model", "auto_qb.hr.server"], ["arg-type", "operator", "assignment"]),
    # ⑦ hr/bencode 字节级解析器两段初始化与 bytes 键写入
    (["auto_qb.hr.bencode"], ["no-redef", "call-overload"]),
    # ⑧ rules 插件层 rec/store Optional 收窄
    (["auto_qb.rules.conditions", "auto_qb.rules.actions.*"], ["union-attr"]),
    # ⑨ rules/base union-attr + no-redef + operator
    (["auto_qb.rules.base"], ["union-attr", "operator", "no-redef"]),
    # ⑩ torrents qbittorrent-api JsonValueT 动态返回面
    (
        ["auto_qb.torrents.store", "auto_qb.torrents.record"],
        ["arg-type", "assignment", "union-attr", "index", "operator", "misc"],
    ),
    # ⑪ config 边界面既有数据形状债(收紧面内的递减目标)
    (
        [
            "auto_qb.config.migrations", "auto_qb.config.loaders", "auto_qb.config.schema.fields",
            "auto_qb.config.writer"
        ],
        ["union-attr", "operator", "arg-type", "assignment"],
    ),
    # ⑫ infra port_owner Optional + file_access shutil.disk_usage 结构差
    (["auto_qb.infra.port_owner", "auto_qb.infra.file_access"], ["union-attr", "return-value"]),
    # ⑬ alias_fs Array / agent Popen 三方重载不命中
    (["auto_qb.infra.alias_fs", "auto_qb.core.traffic_source.agent"], ["call-overload"]),
    # ⑭ transfer adapter torrents_add 动态 kwargs 面
    (["auto_qb.transfer.adapters.qb"], ["arg-type", "list-item"]),
    # ⑮ webui 顶层 mixin 面(server 子模块无 mixin, 对其空转)
    (["auto_qb.webui.*"], ["attr-defined", "has-type"]),
    # ⑯ webui server routes 裸 dict payload 面(最后匹配, 整表替换⑮)
    (["auto_qb.webui.server.*"], ["attr-defined", "has-type", "arg-type", "assignment", "union-attr"]),
    # ⑰ webui 零散残余(最后匹配, mixin 两码为整表替换的必要重复)
    (
        [
            "auto_qb.webui.commands_torrents",
            "auto_qb.webui.views_relocate",
            "auto_qb.webui.runtime_views",
            "auto_qb.webui.runtime_stream",
            "auto_qb.webui.tool_client",
        ],
        ["attr-defined", "has-type", "union-attr", "index", "misc", "arg-type"],
    ),
    # ⑱ cli 模块级单例 Optional 收窄
    (["auto_qb.cli"], ["union-attr"]),
]

# ignore_errors 整模块豁免(计划钉死: ① tray GUI 三方回调, ② rules.expr.env 闭包工厂)
FROZEN_IGNORE_MODULES: frozenset[str] = frozenset({"auto_qb.tray.*", "auto_qb.rules.expr.env"})

# disable_error_code 豁免对(模块模式, 错误码)
FROZEN_DISABLE_PAIRS: frozenset[tuple[str, str]] = frozenset(
    (module, code) for modules, codes in _FROZEN_DISABLE_GROUPS for module in modules for code in codes
)


def check_allowlist(
    ignore_modules: set[str],
    disable_pairs: set[tuple[str, str]],
    frozen_ignore: frozenset[str] = FROZEN_IGNORE_MODULES,
    frozen_pairs: frozenset[tuple[str, str]] = FROZEN_DISABLE_PAIRS,
) -> list[str]:
    """对账: 出现冻结清单之外的**新增**豁免即 finding; 减少不红(递减是正向推进)。

    frozen_ignore / frozen_pairs 缺省即本文件的真仓冻结清单; 合成源红验传入合成基线。
    """
    findings: list[str] = []
    new_ignores = sorted(ignore_modules - frozen_ignore)
    if new_ignores:
        findings.append(
            "pyproject [tool.mypy] 新增 ignore_errors 整模块豁免(守阵冻结外): " + ", ".join(new_ignores) +
            " —— 新增豁免须先在本守阵 FROZEN_IGNORE_MODULES 登记并写理由"
        )
    new_pairs = sorted(disable_pairs - frozen_pairs)
    if new_pairs:
        shown = ", ".join(f"{m}[{c}]" for m, c in new_pairs[:20])
        more = f" (+{len(new_pairs) - 20} 条省略)" if len(new_pairs) > 20 else ""
        findings.append(
            "pyproject [tool.mypy] 新增 disable_error_code 豁免对(守阵冻结外): " + shown + more +
            " —— 新增豁免须先在本守阵 _FROZEN_DISABLE_GROUPS 登记并写理由"
        )
    return findings


# ---- 合成源红验样本(不是真仓 pyproject, 只喂解析与对账函数) -------------------------------------------

TOML_BASE = """\
[tool.mypy]
python_version = "3.12"

[[tool.mypy.overrides]]
module = ["pkg.alpha"]
disable_error_code = ["union-attr"]

[[tool.mypy.overrides]]
module = "pkg.beta"
ignore_errors = true
"""

TOML_NEW_IGNORE = TOML_BASE + """
[[tool.mypy.overrides]]
module = ["pkg.gamma"]
ignore_errors = true
"""

TOML_NEW_PAIR = TOML_BASE + """
[[tool.mypy.overrides]]
module = ["pkg.delta"]
disable_error_code = ["arg-type"]
"""

TOML_REDUCED = """\
[tool.mypy]
python_version = "3.12"

[[tool.mypy.overrides]]
module = ["pkg.alpha"]
disable_error_code = ["union-attr"]
"""


def test_parse_overrides_handles_list_and_string_forms():
    ignore, pairs = parse_pyproject(TOML_BASE)
    assert ignore == {"pkg.beta"}, ignore
    assert pairs == {("pkg.alpha", "union-attr")}, pairs


def test_parse_collects_ignore_modules_and_disable_pairs():
    toml = TOML_BASE + """
[[tool.mypy.overrides]]
module = ["pkg.alpha", "pkg.epsilon"]
disable_error_code = ["operator", "index"]
ignore_errors = true
"""
    ignore, pairs = parse_pyproject(toml)
    assert ignore == {"pkg.beta", "pkg.alpha", "pkg.epsilon"}, ignore
    # 同模块既 ignore_errors 又 disable: 两个豁免面都登记(整表豁免是更粗粒度, 不吞掉码级记录)
    assert ("pkg.alpha", "union-attr") in pairs
    assert ("pkg.epsilon", "operator") in pairs and ("pkg.epsilon", "index") in pairs
    assert ("pkg.alpha", "operator") in pairs and ("pkg.alpha", "index") in pairs


def test_frozen_rejects_new_exemption():
    # 合成基线: ignore={pkg.beta}, 对={(pkg.alpha, union-attr)} —— 与 TOML_BASE 对齐
    base_ignore = frozenset({"pkg.beta"})
    base_pairs = frozenset({("pkg.alpha", "union-attr")})

    ignore, pairs = parse_pyproject(TOML_NEW_IGNORE)
    findings = check_allowlist(ignore, pairs, base_ignore, base_pairs)
    assert len(findings) == 1 and "pkg.gamma" in findings[0] and "ignore_errors" in findings[0], findings

    ignore, pairs = parse_pyproject(TOML_NEW_PAIR)
    findings = check_allowlist(ignore, pairs, base_ignore, base_pairs)
    assert len(findings) == 1 and "pkg.delta[arg-type]" in findings[0] and "disable_error_code" in findings[0], findings


def test_frozen_allows_reduction_and_equality():
    base_ignore = frozenset({"pkg.beta"})
    base_pairs = frozenset({("pkg.alpha", "union-attr")})
    # 相等: TOML_BASE 与合成基线完全一致 —— 零 finding
    ignore, pairs = parse_pyproject(TOML_BASE)
    assert check_allowlist(ignore, pairs, base_ignore, base_pairs) == []
    # 递减: pkg.alpha 只剩 union-attr, ignore 面消失 —— 不红
    ignore, pairs = parse_pyproject(TOML_REDUCED)
    assert check_allowlist(ignore, pairs, base_ignore, base_pairs) == []
    # 完全空配置(极端递减)同样不红
    assert check_allowlist(set(), set(), base_ignore, base_pairs) == []


def test_repo_allowlist_matches_frozen():
    toml_text = PYPROJECT_PATH.read_text(encoding="utf-8")
    ignore, pairs = parse_pyproject(toml_text)
    findings = check_allowlist(ignore, pairs)
    assert not findings, (
        "pyproject [tool.mypy] 出现守阵冻结清单之外的新增豁免 —— allowlist 只减不增"
        "(计划 26-11-05-0635 §01/§04 S4): 要么移除新增豁免, 要么先在"
        " tests/test_mypy_allowlist_guard.py 的 FROZEN_IGNORE_MODULES / _FROZEN_DISABLE_GROUPS "
        "登记并写明理由与日期:\n" + "\n".join(findings)
    )
