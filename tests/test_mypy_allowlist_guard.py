"""mypy allowlist 守阵: pyproject [tool.mypy] 三张清单对账(计划 26-11-05-0635 §04 S4, 拍板 D3; 收口评审扩展 2026-11-06)

设计不变量(计划 §01): 豁免清单冻结进守阵, 新增豁免必须显式改本文件的冻结清单 ——
摩擦是有意的, 摩擦逼着每一条新豁免都留下理由。递减(移除豁免/收紧错误码)不红: 那是
「allowlist 递减」主轴的正向推进。

三张对账面(收口评审后):
- ignore_errors = true 的模块模式集合(整模块豁免, 最粗粒度): 新增红 / 递减不红;
- disable_error_code 的 (模块模式, 错误码) 豁免对集合(错误码级豁免): 新增红 / 递减不红;
- 收紧面集合(disallow_untyped_defs = true 的模块模式集合, 递减的推进方式): **回撤(集合变小)红**,
  新增收紧(集合变大)不红 —— 收紧不是豁免, 只拦回撤。
另: [tool.mypy] **顶层**出现 disable_error_code 或 ignore_errors 键(全局豁免)一律红 ——
per-module 之外的全局豁免直接击穿整个 allowlist; 顶层合法键(python_version / files /
ignore_missing_imports 等)不在报警面, 只对这两个键报警。

按拍板 D3: 本守阵只做静态扫描, **不在 pytest 内跑 mypy** —— dev.typecheck 是独立任务
(`commands run dev.typecheck`), 豁免面外全绿由它验收。

检出能力由合成 TOML 红验内建: 解析形态(list/单字符串/缺键)、新增豁免变红、递减不红、
顶层全局豁免变红、收紧面回撤变红/新增不红各有断言, 解析或对账逻辑退化即红。

## 测试计划(每个测试函数一条)

- test_parse_overrides_handles_list_and_string_forms: module / disable_error_code 的列表与单字符串两种形态都能解析; 缺省键(ignore_errors 未设 / 无 disable_error_code)安全跳过
- test_parse_collects_ignore_modules_and_disable_pairs: ignore_errors 模块集合与 (模块模式, 码) 对集合正确产出, 混合多条 overrides 不串
- test_parse_disable_code_bare_string_yields_pair: disable_error_code 裸字符串形态 -> 正确产出 (模块, 码) 对
- test_parse_top_level_offenders_and_tightened_modules: 顶层豁免键探测(overrides 内同键不误报)与收紧面模块集合解析正确
- test_frozen_rejects_new_exemption: 合成 pyproject 出现冻结外的新 ignore 模块或新 (模块, 码) 对 -> finding 指名新增项(红验内建)
- test_frozen_allows_reduction_and_equality: 合成 pyproject 豁免等于或少于冻结清单 -> 零 finding(递减不红)
- test_top_level_global_exemption_red: [tool.mypy] 顶层出现 disable_error_code / ignore_errors -> finding 指名键名(红验内建)
- test_top_level_legal_keys_not_red: 顶层只出现 python_version / files / ignore_missing_imports 等合法键 -> 零 finding(不误红)
- test_tightening_shrink_red_growth_ok: 收紧面模块回撤(变小) -> finding 指名被回撤模式; 相等/新增收紧 -> 零 finding(红验内建)
- test_repo_allowlist_matches_frozen: 真仓 pyproject 三张清单 + 顶层键对照: 新增豁免面 = 空、顶层全局豁免键 = 空、收紧面无回撤(违规即红)
"""

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

# ---- 解析 ---------------------------------------------------------------------------------------------

# [tool.mypy] 顶层禁止出现的键(全局豁免, 直接击穿 per-module allowlist)
_TOP_LEVEL_FORBIDDEN_KEYS: tuple[str, ...] = ("disable_error_code", "ignore_errors")


def _as_list(value: object) -> list[str]:
    """TOML 的 module / disable_error_code 接受 list 或单字符串两种形态, 归一成 list。"""
    if isinstance(value, str):
        return [value]
    return list(value)


def parse_overrides(data: dict) -> tuple[set[str], set[tuple[str, str]]]:
    """从已解析的 pyproject dict 提取 (ignore_errors 模块模式集合, (模块模式, 错误码) 豁免对集合)。

    module 与 disable_error_code 均接受 list 或单字符串两种 TOML 形态; 缺省键安全跳过。
    """
    ignore_modules: set[str] = set()
    disable_pairs: set[tuple[str, str]] = set()
    overrides = data.get("tool", {}).get("mypy", {}).get("overrides", [])
    for ov in overrides:
        modules = _as_list(ov.get("module", []))
        codes = _as_list(ov.get("disable_error_code", []))
        if ov.get("ignore_errors"):
            ignore_modules.update(modules)
        for code in codes:
            disable_pairs.update((m, code) for m in modules)
    return ignore_modules, disable_pairs


def parse_top_level_offenders(data: dict) -> set[str]:
    """提取 [tool.mypy] 顶层出现的全局豁免键(disable_error_code / ignore_errors)。

    只看 mypy 表的直接子键 —— [[tool.mypy.overrides]] 条目里的同名键是 per-module 豁免,
    不在报警面。
    """
    top = data.get("tool", {}).get("mypy", {})
    return {key for key in _TOP_LEVEL_FORBIDDEN_KEYS if key in top}


def parse_tightened_modules(data: dict) -> set[str]:
    """提取收紧面集合: disallow_untyped_defs = true 的 overrides 条目的模块模式集合。"""
    tightened: set[str] = set()
    overrides = data.get("tool", {}).get("mypy", {}).get("overrides", [])
    for ov in overrides:
        if ov.get("disallow_untyped_defs"):
            tightened.update(_as_list(ov.get("module", [])))
    return tightened


def parse_pyproject(toml_text: str) -> tuple[set[str], set[tuple[str, str]]]:
    """解析 TOML 文本 -> parse_overrides。"""
    return parse_overrides(tomllib.loads(toml_text))


# ---- 冻结清单(2026-11-06 S4 基线, 与 pyproject 注释逐条对应) -------------------------------------------
# 每条 (模块模式列表, 码列表); 新增豁免必须在此同步登记并写理由, 守阵才放行。

_FROZEN_DISABLE_GROUPS: list[tuple[list[str], list[str]]] = [
    # ③ core/modules + hr service mixin 组合面(attr-defined/has-type)与 Optional 次生噪音
    #    call-arg 已随 issue 26-11-06-0247 修正注解而摘除(allowlist 递减), 从冻结面一并撤下 ——
    #    再往这一面加回 call-arg 会当场红。
    (
        ["auto_qb.core.modules.*", "auto_qb.hr.service_wave", "auto_qb.hr.service_status"],
        [
            "attr-defined", "has-type", "union-attr", "arg-type", "assignment", "operator", "misc", "return-value",
            "call-overload"
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

# 收紧面(disallow_untyped_defs = true): 递减的推进方式, 只拦回撤(集合变小), 新增收紧不红。
# 基线 2026-11-06 S4(与 pyproject「S4 收紧面」两条 overrides 对应): 回撤任一模式即红。
FROZEN_TIGHTENED_MODULES: frozenset[str] = frozenset(
    {
        "auto_qb.config.*",
        "auto_qb.torrents.*",
        "auto_qb.core.*",
        "auto_qb.rules.base",
        "auto_qb.rules.conditions",
        "auto_qb.rules.registry",
        "auto_qb.rules.checking_meta",
        "auto_qb.rules.actions.*",
    }
)


def check_allowlist(
    ignore_modules: set[str],
    disable_pairs: set[tuple[str, str]],
    frozen_ignore: frozenset[str] = FROZEN_IGNORE_MODULES,
    frozen_pairs: frozenset[tuple[str, str]] = FROZEN_DISABLE_PAIRS,
    *,
    top_level_offenders: set[str] | None = None,
    tightened_modules: set[str] | None = None,
    frozen_tightened: frozenset[str] = FROZEN_TIGHTENED_MODULES,
) -> list[str]:
    """对账: 顶层全局豁免 / 新增豁免 / 收紧面回撤即 finding; 豁免递减与新增收紧不红。

    frozen_ignore / frozen_pairs 缺省即本文件的真仓冻结清单; 合成源红验传入合成基线。
    top_level_offenders / tightened_modules 传 None(缺省)时跳过对应对账面 —— 供既有
    豁免对账的合成红验样本继续单面验证; 真仓校验必须三面全传。
    """
    findings: list[str] = []
    if top_level_offenders:
        findings.append(
            "pyproject [tool.mypy] 顶层出现全局豁免键(全局豁免直接击穿 per-module allowlist, 一律禁止): " +
            ", ".join(sorted(top_level_offenders)) + " —— 移除顶层键, 需要豁免就写 [[tool.mypy.overrides]] 并在守阵登记"
        )
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
    if tightened_modules is not None:
        shrunk = sorted(frozen_tightened - tightened_modules)
        if shrunk:
            findings.append(
                "pyproject [tool.mypy] 收紧面(disallow_untyped_defs)回撤: 以下模块模式不再开启强制注解: " + ", ".join(shrunk) +
                " —— 收紧面只减不允许回撤, 恢复对应 overrides 或先在守阵记录回撤理由"
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

# 裸字符串形态: disable_error_code 不用数组直接给单字符串(解析形态面)
TOML_BARE_CODE = """\
[[tool.mypy.overrides]]
module = "pkg.zeta"
disable_error_code = "union-attr"
"""

# 顶层全局豁免(红验): 顶层 disable_error_code + ignore_errors 同时出现
TOML_TOP_OFFENDER = """\
[tool.mypy]
python_version = "3.12"
ignore_errors = true
disable_error_code = ["attr-defined"]

[[tool.mypy.overrides]]
module = ["pkg.alpha"]
disable_error_code = ["union-attr"]
"""

# 顶层只有合法键(不误红): python_version / files / ignore_missing_imports 均不在报警面
TOML_TOP_LEGAL = """\
[tool.mypy]
python_version = "3.12"
files = ["src/pkg"]
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = ["pkg.alpha"]
disable_error_code = ["union-attr"]
"""

# 收紧面合成基线(与 TOML_TIGHT_SHRINK / TOML_TIGHT_GROWN 对照)
TOML_TIGHT_BASE = """\
[tool.mypy]
python_version = "3.12"

[[tool.mypy.overrides]]
module = ["pkg.alpha", "pkg.beta"]
disallow_untyped_defs = true
"""

# 收紧面回撤(红验): pkg.beta 不再强制注解
TOML_TIGHT_SHRINK = """\
[tool.mypy]
python_version = "3.12"

[[tool.mypy.overrides]]
module = ["pkg.alpha"]
disallow_untyped_defs = true
"""

# 收紧面新增(不红): pkg.gamma 新开强制注解 = 递减主轴正向推进
TOML_TIGHT_GROWN = """\
[tool.mypy]
python_version = "3.12"

[[tool.mypy.overrides]]
module = ["pkg.alpha", "pkg.beta", "pkg.gamma"]
disallow_untyped_defs = true
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


def test_parse_disable_code_bare_string_yields_pair():
    # 裸字符串形态: disable_error_code = "union-attr"(非数组)也要产出 (模块, 码) 对
    data = tomllib.loads(TOML_BARE_CODE)
    _, pairs = parse_overrides(data)
    assert pairs == {("pkg.zeta", "union-attr")}, pairs


def test_parse_top_level_offenders_and_tightened_modules():
    # 顶层键探测: TOML_TOP_OFFENDER 顶层两键都命中; overrides 条目内的同名键不算顶层
    data = tomllib.loads(TOML_TOP_OFFENDER)
    assert parse_top_level_offenders(data) == {"disable_error_code", "ignore_errors"}, data["tool"]["mypy"].keys()
    # 合法键 + per-module 豁免: 顶层零命中
    assert parse_top_level_offenders(tomllib.loads(TOML_TOP_LEGAL)) == set()
    # 收紧面解析: 多模块一条 overrides 全收
    assert parse_tightened_modules(tomllib.loads(TOML_TIGHT_BASE)) == {"pkg.alpha", "pkg.beta"}
    # 缺省键安全跳过: 无 overrides / 无 disallow_untyped_defs 均空集
    assert parse_top_level_offenders(tomllib.loads(" ")) == set()
    assert parse_tightened_modules(tomllib.loads(" ")) == set()


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


def test_top_level_global_exemption_red():
    # 红验: 顶层 disable_error_code / ignore_errors -> finding 指名键名
    data = tomllib.loads(TOML_TOP_OFFENDER)
    findings = check_allowlist(
        *parse_overrides(data),
        frozenset(),
        frozenset({("pkg.alpha", "union-attr")}),
        top_level_offenders=parse_top_level_offenders(data),
    )
    assert len(findings) == 1, findings
    assert "顶层出现全局豁免键" in findings[0] and "disable_error_code" in findings[0] and "ignore_errors" in findings[0
                                                                                                             ], findings


def test_top_level_legal_keys_not_red():
    # python_version / files / ignore_missing_imports 是合法顶层键, 不误红
    data = tomllib.loads(TOML_TOP_LEGAL)
    findings = check_allowlist(
        *parse_overrides(data),
        frozenset(),
        frozenset({("pkg.alpha", "union-attr")}),
        top_level_offenders=parse_top_level_offenders(data),
    )
    assert findings == [], findings


def test_tightening_shrink_red_growth_ok():
    frozen = frozenset({"pkg.alpha", "pkg.beta"})
    # 相等: 零 finding
    tightened = parse_tightened_modules(tomllib.loads(TOML_TIGHT_BASE))
    assert check_allowlist(set(), set(), tightened_modules=tightened, frozen_tightened=frozen) == []
    # 回撤(集合变小): 红, finding 指名被回撤的模式
    tightened = parse_tightened_modules(tomllib.loads(TOML_TIGHT_SHRINK))
    findings = check_allowlist(set(), set(), tightened_modules=tightened, frozen_tightened=frozen)
    assert len(findings) == 1 and "pkg.beta" in findings[0] and "disallow_untyped_defs" in findings[0], findings
    # 新增收紧(集合变大): 不红
    tightened = parse_tightened_modules(tomllib.loads(TOML_TIGHT_GROWN))
    assert check_allowlist(set(), set(), tightened_modules=tightened, frozen_tightened=frozen) == []
    # 极端回撤(收紧面清空): 红
    findings = check_allowlist(set(), set(), tightened_modules=set(), frozen_tightened=frozen)
    assert len(findings) == 1 and "pkg.alpha" in findings[0] and "pkg.beta" in findings[0], findings


def test_repo_allowlist_matches_frozen():
    data = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
    ignore, pairs = parse_overrides(data)
    findings = check_allowlist(
        ignore,
        pairs,
        top_level_offenders=parse_top_level_offenders(data),
        tightened_modules=parse_tightened_modules(data),
    )
    assert not findings, (
        "pyproject [tool.mypy] 守阵对账红: "
        "(1) 顶层全局豁免键(一律禁止) / (2) 冻结清单外新增豁免(allowlist 只减不增, 计划 26-11-05-0635 §01/§04 S4) / "
        "(3) 收紧面(disallow_untyped_defs)回撤(只减不允许回撤)。\n"
        "处置: 豁免要么移除, 要么先在 tests/test_mypy_allowlist_guard.py 的 FROZEN_IGNORE_MODULES / "
        "_FROZEN_DISABLE_GROUPS / FROZEN_TIGHTENED_MODULES 登记并写明理由与日期; 收紧面回撤要恢复 overrides。\n" + "\n".join(findings)
    )
