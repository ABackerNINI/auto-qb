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
- test_loader_probe_table_covers_named_leaf_surface: loader 消费探针表必须恰好覆盖键面命名叶键
  (扣动态段与豁免) —— 新增键不配探针当场红, 逼着补「YAML 显式值」探针; 键在面上但 loader 漏读
  (issue 26-10-06-0027 D-01 形态: 键面/schema/校验五处齐备唯独 loaders 不取值, 三道旧守卫全探不到)
  由此被结构性堵住
- test_named_leaf_keys_round_trip_through_load_config: 每个命名叶键以显式 YAML 值(≠字段默认)写进
  临时配置, load_config 回读后必须 == 期望解析值 —— YAML 写了但解析拿不到即红(键面守卫域的
  loader 消费核对); 探针期望值 ≠ 字段默认值本身也是断言, 防探针退化成与缺省同值的空转核对
"""
import logging
import re
import tempfile
from pathlib import Path

import pytest
import yaml

from auto_qb.config import Config, load_config, schema
from auto_qb.config.models import QbTraffic
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


# ---------- loader 消费核对(issue 26-10-06-0027 D-01 守阵): 键在键面上 ≠ loader 真的读它 ----------
# D-01 形态: 键在 models/schema/校验/键面基线/keys.md 五处齐备, 唯 load_grouping_config 漏取值,
# YAML 显式写 true 校验零报错、解析恒为默认 False —— 键面/schema/直设属性三道旧守卫全探不到。
# 本守阵给每个命名叶键配「YAML 显式值(≠字段默认) -> 期望解析值」探针, 一份全键探针配置走
# load_config 真链路回读, 显式值拿不到即红。

# 探针豁免键(无法构造「非默认合法探针」/ 专段结构, 逐个注明理由):
# - global_speed_limit_curve: curve 专段编辑器, 内部键本就不入键面(见上方「键面口径」边界),
#   结构与 enabled 开关由 test_validate_gslc* 与 test_config.py 的曲线用例覆盖;
# - notify.channels: v1 渠道值域只有 platform 一档(== 字段默认), 显式探针恒等于缺省, 回读不可判别;
#   loader 显式分支(channels 列表 -> 渠道名)由 test_config.py::test_load_notify_config 覆盖。
_LOADER_PROBE_EXCLUDED = {"global_speed_limit_curve", "notify.channels"}

# Optional 段的缺省实例(Config() 上该属性为 None = 功能未启用, 探针空转核对要用段数据类默认兜底)
_OPTIONAL_SECTION_DEFAULTS = {"qb_traffic": QbTraffic}

# 命名叶键探针表: 键路径 -> (YAML 显式值, 期望解析值)。期望值一律硬编码字面量(不复用 parse 函数),
# 让「YAML 写的 == 解析出的」核对完全独立于被测解析器; 全部取 ≠ 字段默认的合法值(空转核对自断言)。
_LOADER_PROBES = {
    # 顶层标量
    "main_tick": ("3S", 3.0),
    "sync_interval": ("7S", 7.0),
    "interval": ("3M", 180.0),
    "state_save_interval": ("45S", 45.0),
    "max_tasks_per_tick": ("7", 7),
    "data_dir": ("/probe-data", "/probe-data"),
    "state_file": ("/probe-data/state-probe.json", "/probe-data/state-probe.json"),
    "remove_similar_tags": ("true", True),
    "maintenance_tag_mode": ("on_change", "on_change"),
    "skip_checking_tag": ("probe-skip", "probe-skip"),
    "delete_tags": (["probe-a"], ["probe-a"]),
    "delete_tags_if_has_no_torrents": (["probe-b"], ["probe-b"]),
    # log 段(YAML 键 log -> 模型属性 logging)
    "log.level": ("DEBUG", logging.DEBUG),
    "log.file": ("probe-autolog.log", "probe-autolog.log"),
    "log.max_bytes": ("2MiB", 2 * 1024**2),
    "log.format": ("probe-format %(message)s", "probe-format %(message)s"),
    # add_episode_tags 段
    "add_episode_tags.enabled": ("true", True),
    "add_episode_tags.add_tag_single": ("sE${episode_first}", "sE${episode_first}"),
    "add_episode_tags.add_tag_multi": ("mE${episode_first}-${episode_last}", "mE${episode_first}-${episode_last}"),
    # hr 段
    "hr.add_tag": ("probe-hr-tag", "probe-hr-tag"),
    "hr.add_category": ("probe-hr-cat", "probe-hr-cat"),
    "hr.overwrite_category": ("true", True),
    "hr.add_tag_for_satisfied": ("probe-hr-done-tag", "probe-hr-done-tag"),
    "hr.add_category_for_satisfied": ("probe-hr-done-cat", "probe-hr-done-cat"),
    "hr.overwrite_category_for_satisfied": ("true", True),
    "hr.exclude_tags": (["probe-ex-t"], ["probe-ex-t"]),
    "hr.exclude_categories": (["probe-ex-c"], ["probe-ex-c"]),
    # grouping 段(cross_group_conflict_check 即 D-01 缺口键: 默认 False, 显式 true 必须真正解析成 True)
    "grouping.enabled": ("false", False),
    "grouping.check_missing_files": ("false", False),
    "grouping.missing_tag": ("PROBETAG", "PROBETAG"),
    "grouping.cross_group_conflict_check": ("true", True),
    # qbittorrent 段
    "qbittorrent.host": ("192.0.2.1", "192.0.2.1"),
    "qbittorrent.port": ("16585", 16585),
    "qbittorrent.username": ("probe-user", "probe-user"),
    "qbittorrent.password": ("probe-pass", "probe-pass"),
    # web 段
    "web.enabled": ("true", True),
    "web.host": ("192.0.2.1", "192.0.2.1"),
    "web.port": ("18080", 18080),
    "web.token": ("probe-token", "probe-token"),
    "web.skip_local_verify": ("true", True),
    "web.skip_check_menu": ("true", True),
    # notify 段(channels 豁免, 见 _LOADER_PROBE_EXCLUDED)
    "notify.enabled": ("true", True),
    "notify.min_level": ("WARNING", "WARNING"),
    "notify.quiet_hours": ("02:00-05:00", "02:00-05:00"),
    "notify.max_per_hour": ("90", 90),
    "notify.dedup_window": ("90S", 90.0),
    # hr_check 段(sites 动态段不入探针)
    "hr_check.enabled": ("true", True),
    "hr_check.min_interval": ("100S", 100.0),
    "hr_check.max_requests_per_day": ("333", 333),
    "hr_check.max_pages_per_wave": ("33", 33),
    "hr_check.allow_window": ("01:00-06:00", "01:00-06:00"),
    "hr_check.shared_dir": ("/probe-hr-shared", "/probe-hr-shared"),
    "hr_check.reuse_window": ("3H", 10800.0),
    "hr_check.channel.enabled": ("true", True),
    "hr_check.channel.port": ("18788", 18788),
    "hr_check.channel.token": ("probe-ch-token", "probe-ch-token"),
    "hr_check.channel.extension_id": ("a" * 32, "a" * 32),  # 32 位 Chrome 扩展 id(a~p)
    "hr_check.channel.request_timeout": ("240S", 240.0),
    # qb_traffic 段(探针值须过校验: sample >= main_tick(3S) 且 <= 600s; flush 60-3600 整数秒;
    # raw 1h-90d; rollup >= 7d)
    "qb_traffic.enabled": ("true", True),
    "qb_traffic.sample_interval": ("40S", 40.0),
    "qb_traffic.flush_interval": ("150S", 150.0),
    "qb_traffic.raw_window": ("2H", 7200.0),
    "qb_traffic.rollup_window": ("8D", 691200.0),
}


def _named_leaf_keys() -> list:
    """键面里可逐键回读的「命名叶键」: 扣动态段(trackers.* / *_rules.* / fs.path_map.* /
    hr_check.sites.* 通配)与探针豁免键, 只留不被更深路径前缀的末端键"""
    paths = build_config_key_surface()
    return sorted(
        p for p in paths if ".*" not in p and "<任意>" not in p and p not in _LOADER_PROBE_EXCLUDED and
        not any(q != p and q.startswith(p + ".") for q in paths)
    )


def _attr_walk(root, path: str):
    """按键路径取配置模型属性; YAML 键 log 对应模型属性 logging"""
    node = root
    for part in path.split("."):
        node = getattr(node, "logging" if part == "log" else part)
    return node


def test_loader_probe_table_covers_named_leaf_surface():
    """探针表必须恰好覆盖键面命名叶键(扣豁免): 新增键不配探针当场红 —— 键在面上但 loader 漏读
    (D-01 形态)没有结构信号, 靠「加键必须配回读探针」这道闸逼出消费核对"""
    named = set(_named_leaf_keys())
    probed = set(_LOADER_PROBES)
    assert probed == named, (
        "loader 消费探针表与键面命名叶键不一致(键在键面上但回读探针缺失/多余, 新增配置键必须同步配探针):\n"
        f"  缺探针: {sorted(named - probed)}\n"
        f"  多余探针: {sorted(probed - named)}\n"
        f"  豁免口径见 _LOADER_PROBE_EXCLUDED(逐键注明理由)"
    )


def test_named_leaf_keys_round_trip_through_load_config():
    """每个命名叶键以显式 YAML 值写进临时配置, load_config 真链路回读必须 == 期望解析值;
    同时断言期望值 ≠ 字段默认(防探针与缺省同值退化为空转核对)"""
    # 空转防线: 期望值必须偏离字段默认(Optional 段默认 None, 用段数据类默认兜底)
    for path, (_raw, expected) in _LOADER_PROBES.items():
        root_part = path.split(".")[0]
        if root_part in _OPTIONAL_SECTION_DEFAULTS:
            default_value = _attr_walk(_OPTIONAL_SECTION_DEFAULTS[root_part](), path.split(".", 1)[1])
        else:
            default_value = _attr_walk(Config(), path)
        assert expected != default_value, (f"探针 {path} 的期望值 {expected!r} 与字段默认相同, 回读核对空转 —— 换一个非默认的合法探针值")
    # 一份全键探针配置走 load_config 真链路(读文件 -> _strip_none -> 迁移 -> 全量校验 -> 解析)
    probe_cfg: dict = {"config": {}}
    for path, (raw, _expected) in _LOADER_PROBES.items():
        node = probe_cfg["config"]
        parts = path.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = raw
    with tempfile.TemporaryDirectory() as td:
        config_path = Path(td) / "probe_config.yml"
        config_path.write_text(yaml.safe_dump(probe_cfg, allow_unicode=True), encoding="utf-8")
        cfg = load_config(str(config_path))
    mismatched = [
        f"{path}: 期望 {_LOADER_PROBES[path][1]!r}, 实得 {_attr_walk(cfg, path)!r}"
        for path in _LOADER_PROBES if _attr_walk(cfg, path) != _LOADER_PROBES[path][1]
    ]
    assert not mismatched, (
        "键面命名叶键的 YAML 显式值未按期望进入 load_config 解析结果(loader 漏读/错读, D-01 形态):\n  " + "\n  ".join(mismatched)
    )
