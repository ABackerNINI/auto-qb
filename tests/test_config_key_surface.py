"""test_config_key_surface 测试计划: 配置版本升级守卫 —— 键面基线冻结快照 (计划 26-09-28-1834)

## 为什么需要这道守卫
现有防线(版本链框架 / 写回版本闸门 / 启动物化 / schema↔validation 互检)全部以「流程被正确走」
为前提: schema 与 validation 一起改名/删键时互检恒绿, 没有任何一环在开发期拦住「改键不抬版本、
不写迁移」, 后果是存量 config.yml 出现孤儿键(静默丢弃或废除报废)。本模块维护**第三份冻结副本**
(tests/fixtures/config_key_surface.txt, 独立于 schema 与 validation 两边), 键面一变即红。

## 版本升级流程口径(报错文案的路由单点)
- **破坏性变更**(删键 / 改名 / 结构形状变): 抬 CURRENT_VERSIONS["config"](infra/versioning.py)
  → 在 config/migrations.py 注册迁移(import 即注册, 纯函数 dict→dict) → 补迁移回归测试
  (参照 test_hr_config.py 的兼容锚写法) → 重生成基线。口径: versioning.py 模块 docstring /
  计划 26-09-26-0506 / pitfalls/backend/schema-stamp-writeback.md。
- **非破坏变更**(纯新增键): 刻意不造版本, 直接重生成基线(commands run test.keys-update)并回写
  memory-bank/config-reference/keys.md。
- 守卫不自动裁决破坏/非破坏(机器判不了语义), 用键面差异 + 报错文案分流路由。

## 键面口径(生成器 build_config_key_surface 是单点, 再生脚本只是调用方)
- 顶层键: validation.KNOWN_CONFIG_KEYS 剔除 schema_version(版本章本身, 归版本链框架管, 不入面)。
- 具名子树: schema.config_fields() 按 Field.fields 递归(web/log/notify/grouping/hr/fs/qbittorrent/
  hr_check.channel/add_episode_tags …)。
- 动态段归一通配: trackers.*(TRACKER_FIELDS), hr_check.sites.*(HR_CHECK_SITES_FIELDS),
  <任意>_rules.*(RULE_FIELDS + 全部条件/动作插件 spec), fs.path_map.* 条目键(KNOWN_PATH_MAP_ENTRY_KEYS)。
- **边界**: 限速曲线段内部键(traffic_source/curves/阶梯点)是 validation/curves.py 内联字面量,
  无常量可派生, v1 不入面(要纳入先提常量); 默认值/文案/UI 元数据(如 tone)不是结构, 永不入面;
  键不变、语义改义没有结构信号, 拦不住, 靠评审与档案。

## 测试计划(每个测试函数一条)
- test_config_key_surface_matches_baseline: 当前键面+config 版本 == 基线; 不一致列出增删清单并按
  「消失键(破坏)/纯新增(非破坏)/版本已抬」三种现场分流报错, 文案指路升级流程
- test_config_migration_chain_complete: MIGRATIONS["config"] 恰好覆盖 1..CURRENT-1 —— 版本表与
  迁移表同步的静态断言(原来只在运行时 migrate() 里 fail-fast, 抬号忘迁移提前到测试期暴露)
- test_keys_md_covers_key_surface: 键面每个叶键(路径末段, 词边界匹配)在参考文档反引号 span 内有
  出处 —— 改键忘回写文档当场报。语料 = keys.md + 其规则集段委托的插件参考
  (rule-system/conditions-and-actions.md), 跟随委托关系不重复维护。**豁免**: 插件 spec 内部键
  (<任意>_rules.*.conditions/actions.<插件名> 之下的层级) —— 插件 spec 键面尚未逐键进参考文档,
  权威单点是 schema 插件表; 插件名本身仍要求有出处。展开插件 spec 键面属独立回写任务, 未做前豁免保持
"""
import re
from pathlib import Path

import pytest

from auto_qb.config import schema
from auto_qb.config.schema import HR_CHECK_SITES_FIELDS, RULE_FIELDS, TRACKER_FIELDS
from auto_qb.config.validation import KNOWN_CONFIG_KEYS
from auto_qb.config.validation.sections import KNOWN_PATH_MAP_ENTRY_KEYS
from auto_qb.infra.versioning import CURRENT_VERSIONS, MIGRATIONS

REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = Path(__file__).parent / "fixtures" / "config_key_surface.txt"
# 出处语料 = keys.md + 它在「规则集段」委托的插件参考(keys.md 只留指针, 插件清单单点在那边,
# 跟随委托关系合并检查, 避免同一批插件键两处重复维护)
_DOC_PATHS = (
    REPO_ROOT / "memory-bank" / "config-reference" / "keys.md",
    REPO_ROOT / "memory-bank" / "rule-system" / "conditions-and-actions.md",
)

# keys.md 出处检查的豁免段: 插件 spec 内部键(插件名之下的层级) —— 参考文档尚未逐键展开,
# 权威单点是 schema 插件表(keys.md 规则集段已声明指向); 插件名本身不豁免
_DOC_EXEMPT = re.compile(r"^<任意>_rules\.[^.]+\.(conditions|actions)\.[^.]+\.")

# 版本章自身不入键面(它归版本链框架管); trackers 顶层键单独按动态段展开
_EXCLUDED_TOP_KEYS = {"schema_version", "trackers"}

# 具名子树里的动态映射段: (父路径, 子键) -> 通配前缀; 命中后子键按 <通配>.<孙键> 展开
_DYNAMIC_SEGMENTS = {("hr_check", "sites"): "hr_check.sites.*"}


def _walk(field: schema.Field, prefix: str, out: set) -> None:
    """把 Field 子树展开进键面: prefix 已含本字段键, object 子字段继续下钻"""
    out.add(prefix)
    for child in field.fields:
        wildcard = _DYNAMIC_SEGMENTS.get((prefix, child.key))
        if wildcard is not None:
            out.add(f"{prefix}.{child.key}")
            for grandchild in child.fields:
                _walk(grandchild, f"{wildcard}.{grandchild.key}", out)
        else:
            _walk(child, f"{prefix}.{child.key}", out)


def build_config_key_surface() -> set:
    """config.yml 结构性键路径全集(动态段归一通配); 测试与再生脚本的单一事实来源"""
    surface: set = set()
    top_fields = {f.key: f for f in schema.config_fields()}
    for key in sorted(KNOWN_CONFIG_KEYS - _EXCLUDED_TOP_KEYS):
        field = top_fields.get(key)
        assert field is not None, f"KNOWN_CONFIG_KEYS 的 {key!r} 在 schema 无顶层字段(schema↔validation 互检应已拦, 先查 test_config_schema)"
        _walk(field, key, surface)
    # trackers 站点段(键名用户自定 -> 通配; hr 子段经 Field.fields 自然下钻)
    surface.add("trackers")
    for field in TRACKER_FIELDS:
        _walk(field, f"trackers.*.{field.key}", surface)
    # fs.path_map 条目键(YAML 列表条目, 形状常量在 validation/sections.py)
    for entry_key in KNOWN_PATH_MAP_ENTRY_KEYS:
        surface.add(f"fs.path_map.*.{entry_key}")
    # 规则集动态段: 规则级字段 + 条件/动作插件 spec(容器键 conditions/actions 见 RULE_KNOWN_KEYS)
    surface.add("<任意>_rules")
    for field in RULE_FIELDS:
        _walk(field, f"<任意>_rules.*.{field.key}", surface)
    for kind, container in (("condition", "conditions"), ("action", "actions")):
        for plugin in schema.plugin_table()[kind]:
            base = f"<任意>_rules.*.{container}.{plugin.name}"
            surface.add(base)
            for field in plugin.fields:
                _walk(field, f"{base}.{field.key}", surface)
    return surface


def render_baseline(version: int, keys: set) -> str:
    """基线文件全文: 头部口径注释 + version 行 + 排序键路径(生成物, 禁止手改)"""
    lines = [
        "# 配置键面基线 — tests/test_config_key_surface.py 的冻结快照(生成物, 勿手改)",
        "# 再生成: commands run test.keys-update",
        "# 口径: 消失/改名 = 破坏性变更 -> 抬 CURRENT_VERSIONS['config'] + config/migrations.py 注册迁移;",
        "#       纯新增 = 非破坏, 直接重生成. schema_version 是版本章本身不入面; 动态段归一为通配.",
        f"version: {version}",
        "",
    ]
    lines.extend(sorted(keys))
    return "\n".join(lines) + "\n"


def _parse_baseline(text: str):
    """解析基线: 返回 (version, 键集合); version 行缺失 = 损坏的基线, 让比对测试报红而非静默当 v1"""
    version = None
    keys: set = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("version:"):
            version = int(stripped.split(":", 1)[1].strip())
            continue
        keys.add(stripped)
    assert version is not None, f"基线缺 version 行(损坏?), 请 commands run test.keys-update 重生成: {BASELINE_PATH}"
    return version, keys


def test_config_key_surface_matches_baseline():
    """当前键面+config 版本必须与基线一致; 不一致按现场状态分流并指路升级流程"""
    current = build_config_key_surface()
    current_version = CURRENT_VERSIONS["config"]
    baseline_version, baseline_keys = _parse_baseline(BASELINE_PATH.read_text(encoding="utf-8"))
    if baseline_keys == current and baseline_version == current_version:
        return
    added = sorted(current - baseline_keys)
    removed = sorted(baseline_keys - current)
    detail = []
    if removed:
        detail.append(f"消失的键({len(removed)}): " + " ".join(removed))
    if added:
        detail.append(f"新增的键({len(added)}): " + " ".join(added))
    if baseline_version != current_version:
        routing = (
            f"config 版本已从 v{baseline_version} 抬到 v{current_version}, 基线待重生成 —— "
            "先确认迁移链完整(test_config_migration_chain_complete), 再 commands run test.keys-update"
        )
    elif removed:
        routing = (
            "出现消失键 = 删键/改名属破坏性结构变更, 必须走版本升级流程:\n"
            "  1) 抬 CURRENT_VERSIONS['config'](src/auto_qb/infra/versioning.py)\n"
            "  2) 在 src/auto_qb/config/migrations.py 注册迁移(import 即注册, 纯函数 dict->dict)\n"
            "  3) 补迁移回归测试(参照 tests/test_hr_config.py 的兼容锚写法)\n"
            "  4) commands run test.keys-update 重生成基线, 并回写 memory-bank/config-reference/keys.md\n"
            "口径: versioning.py 模块 docstring / 计划 26-09-26-0506 / pitfalls/backend/schema-stamp-writeback.md"
        )
    else:
        routing = (
            "纯新增键 = 非破坏性变更(刻意不造版本, versioning.py 口径):\n"
            "  commands run test.keys-update 重生成基线, 并回写 memory-bank/config-reference/keys.md"
        )
    pytest.fail(
        f"配置键面与基线不一致(基线 v{baseline_version} / 当前 v{current_version})\n" + "\n".join(detail) + f"\n处置: {routing}"
    )


def test_config_migration_chain_complete():
    """迁移表必须恰好覆盖 1..CURRENT-1: 抬了版本号忘写迁移, 测试期就红(不等运行时 migrate fail-fast)"""
    current = CURRENT_VERSIONS["config"]
    registered = set(MIGRATIONS["config"])
    expected = set(range(1, current))
    assert registered == expected, (
        f"config 迁移链与版本表不同步: 版本表 v{current}, 迁移表注册了 {sorted(registered)}, 期望 {sorted(expected)} —— "
        "抬 CURRENT_VERSIONS['config'] 必须同时在 config/migrations.py 注册 v(n-1)->vn 迁移(import 即注册)"
    )


def test_keys_md_covers_key_surface():
    """键面叶键必须在参考文档反引号 span 内有出处(词边界匹配): 改键忘回写参考文档当场报"""
    spans: list = []
    for doc in _DOC_PATHS:
        spans.extend(re.findall(r"`([^`\n]+)`", doc.read_text(encoding="utf-8")))
    missing = []
    for path in sorted(build_config_key_surface()):
        if _DOC_EXEMPT.match(path):
            continue
        leaf = path.rsplit(".", 1)[-1]
        pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(leaf)}(?![A-Za-z0-9_])")
        if not any(pattern.search(span) for span in spans):
            missing.append(path)
    assert not missing, (
        "键面叶键在参考文档(keys.md + rule-system/conditions-and-actions.md)无出处(改键必须同步回写):\n  " + "\n  ".join(missing)
    )
