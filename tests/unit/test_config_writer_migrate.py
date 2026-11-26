"""test_config_writer_migrate 测试计划: 配置写回(结构化树 -> 校验 -> R 级回退 -> round-trip 写盘)

## 测试计划(每个测试函数一条)
- test_materialize_migrates_and_backups: 启动物化: 版本号备份(迁移前原样) + 磁盘落当前版本新结构 + 返回 desc 与备份路径
- test_materialize_idempotent_and_noop: 已是当前版本零 IO; 二次调用幂等, 不产生新备份- test_materialize_dry_run_probe: write=False(dry-run 探测)只报 desc, 不校验不备份不落盘
- test_materialize_missing_file_returns_empty: 配置文件不存在 -> 原样返回 ("", "") 且零 IO
- test_reject_stale_version_non_integer_shape_passes_gate: 版本闸门放行非整数形状(交校验层)与当前版本
- test_materialize_bad_version_wraps_config_error: 磁盘 schema_version 非法 -> 包装 ConfigError 且零落盘
- test_migrate_config_1_2_legacy_shapes: v1→v2 旧键非字典删除 / mode=off 删除 / 定位不到档案原地保留
- test_migrate_config_1_2_new_position_wins: v1→v2 新位置已有条目获胜, 旧键只删除
- test_migrate_config_1_2_creates_entry_with_tuning_keys: v1→v2 正例(建条目+调优键随迁+页面事实键丢弃)
- test_migrate_config_2_3_site_entry_shapes: v2→v3 非 dict 条目删除 / mode→enabled / 改名与废弃键清理
- test_materialize_non_mapping_config_section_noop: 树缺 config 映射段 -> 物化按无事可做返回, 零 IO
- test_backup_versioned_relative_backup_dir: 备份目录为空串(相对裸文件名) -> 跳过建目录, 直写 CWD
- test_migrate_config_3_4_removes_explicit_empty: v3→v4 迁移单测 —— 9 键作用域内显式置空移除 + 逐键 notes(非空值/无关站点不误杀)
- test_migrate_config_3_4_idempotent: v3→v4 迁移幂等 —— 移除后重放无变更无 notes(崩溃重放安全)
- test_materialize_v3_removes_explicit_empty_with_warning: v3 文件物化 —— 作用域 '' 移除落盘当前版本(v3→v8) + 每键 WARNING(caplog)
- test_materialize_v4_site_empty_untouched: v4 文件站点 '' = 覆盖为空(v4 起的合法语义), v4→v8 迁移不误杀
- test_materialize_passes_config_path_to_migration: 物化调迁移函数传真实 config_path(不是 None) —— spy 卡实参
- test_backup_versioned_creates_parent_and_relative_forms: backup_versioned 按 dirname 建父目录(exist_ok=True 幂等), 嵌套目录不存在也落盘
- test_reject_stale_version_guards_non_dict_cfg: 版本闸门对非映射 config 段走「版本缺失」拒绝, 不崩在属性访问上
- test_reject_stale_version_message_carries_both_versions: 闸门错误消息须同时带两个版本号并指路刷新(整段换 None 会丢排障线索)
- test_fallback_readonly_skips_version_key_but_covers_others: readonly 回退跳过 schema_version、continue 而非 break、其余键按点路径回退
- test_materialize_unknown_host_old_key_dropped
- test_migrate_config_6_7_exact_roundtrip: v6→v7 精确还原(1.5S/1.5S -> 1 倍), 旧键消失, 单条 note
- test_migrate_config_6_7_seconds_to_multiplier: 30S/2S -> 15 倍; main_tick 缺失兜默认 2.0 同值
- test_migrate_config_6_7_clamped_to_effective_seconds_cap: 600S/7S -> 85 倍(595s <= 600s), note 明示钳制
- test_migrate_config_6_7_rounds_up: 非整除向上取整 7S/2S -> 4 倍(8s)
- test_migrate_config_6_7_no_legacy_key_untouched: 无旧键不动、零 note、零 diff(D9 不补写)
- test_migrate_config_6_7_idempotent: 连跑两次, 第二次零 diff(裸 dict)
- test_migrate_config_6_7_main_tick_over_cap: main_tick 700S -> 倍数 1 且 note 写明上限不可满足
- test_migrate_config_6_7_unparsable_legacy_value_kept: 旧值不可解析 -> 旧键保留 + 一条 note 指路手改
- test_migrate_config_7_8_single_entry_moved: v7→v8 恰一条非空条目搬成 relocate.bt_backup(strip), 单条 note, 版本链注册可串行
- test_migrate_config_7_8_single_entry_new_position_wins: v7→v8 新旧并存新位置获胜, 旧值只丢弃不覆盖
- test_migrate_config_7_8_no_key_untouched: v7→v8 无旧键不动、零 note、零 diff(relocate 段缺失不顺手建)
- test_migrate_config_7_8_multiple_nonempty_dropped: v7→v8 多条非空删键 + note 提示重配, 不猜(D7), relocate 段不被误写
- test_migrate_config_7_8_all_empty_or_junk_dropped: v7→v8 全空/无有效值/非字典删键 + note 提示重配
- test_migrate_config_7_8_idempotent: v7→v8 幂等 —— 搬运后重放零 diff(崩溃重放安全)
- test_materialize_v7_bt_backup_table_migrates_with_warning: 反证 —— v7 文件物化走迁移后校验绿且 note 落 WARNING(caplog)
"""

import copy

import os

import pytest

from auto_qb.config.errors import ConfigError

from auto_qb.config.loaders import load_config

from auto_qb.config.writer import materialize_schema_migration, preview_tree, read_tree, write_tree

from helpers import LEGACY_V1

from config_writer_support import (
    BASE,
    V4_SITE_EMPTY,
    _make,
    _text,
)


def test_materialize_migrates_and_backups(tmp_path):
    """启动物化: v1 磁盘 -> 版本号备份(迁移前原样) + 磁盘落成当前版本新结构 + 返回 desc 与路径"""
    data_dir = tmp_path / "data"
    path = _make(tmp_path, LEGACY_V1)

    desc, backup = materialize_schema_migration(path, str(data_dir))

    assert desc == "v1→v8"
    assert backup == str(data_dir / "config.yml.v1.bak")
    with open(backup, encoding="utf-8") as f:
        assert f.read() == LEGACY_V1, "备份 = 迁移前原样(字节级)"
    text = _text(path)
    assert "schema_version: 8" in text, "磁盘落当前版本章"
    assert "hr_page_url" not in text, "旧键随迁移消失"
    cfg = load_config(path)  # 物化后的磁盘必须能原样通过加载
    assert cfg.trackers["BTSchool"].hr_check is not None
    assert cfg.hr_check.sites["btschool"].enabled is True
    assert cfg.trackers["BTSchool"].hr_check.enabled is True, "v3 派生视图: enabled 取代 mode"


def test_materialize_idempotent_and_noop(tmp_path):
    """已是当前版本: 零 IO 幂等 —— 二次调用与干净 v3 文件都返回空, 不产生新备份"""
    data_dir = tmp_path / "data"
    path = _make(tmp_path, LEGACY_V1)
    desc, _ = materialize_schema_migration(path, str(data_dir))
    assert desc == "v1→v8"
    text_after = _text(path)

    desc2, backup2 = materialize_schema_migration(path, str(data_dir))
    assert (desc2, backup2) == ("", "")
    assert _text(path) == text_after, "二次调用零改动"
    assert len(list(data_dir.iterdir())) == 1, "只有首次迁移的那一个备份"

    path = _make(tmp_path, BASE)  # 天生当前版本的干净文件: 同样零 IO
    assert materialize_schema_migration(path, str(data_dir)) == ("", "")
    assert len(list(data_dir.iterdir())) == 1


def test_materialize_unknown_host_old_key_dropped(tmp_path):
    """v3: 陌生 host 的旧键不再「原地保留报废除错」—— v2→v3 迁移直接删除 trackers.*.hr_check,
    迁移后配置合法落盘(v3 无旧位置兼容, 计划 26-09-28-1932 §7.1)"""
    data_dir = tmp_path / "data"
    bad = LEGACY_V1.replace("https://pt.btschool.club/myhr.php", "https://example.com/myhr.php")
    path = _make(tmp_path, bad)

    desc, backup = materialize_schema_migration(path, str(data_dir))

    assert desc == "v1→v8"
    text = _text(path)
    assert "hr_check" not in text, "陌生 host 的旧键随 v3 迁移删除"
    cfg = load_config(path)
    assert cfg.trackers["BTSchool"].hr_check is None


def test_materialize_dry_run_probe(tmp_path):
    """write=False(dry-run 探测): 只报 desc, 不校验不备份不落盘 —— 与 state 迁移同口径"""
    data_dir = tmp_path / "data"
    path = _make(tmp_path, LEGACY_V1)

    desc, backup = materialize_schema_migration(path, str(data_dir), write=False)

    assert desc == "v1→v8" and backup == ""
    assert _text(path) == LEGACY_V1, "dry-run 不落盘"
    assert not data_dir.exists()


def test_materialize_missing_file_returns_empty(tmp_path):
    """配置文件不存在(测试/非常规构造直接注入配置): 无事可做, 原样返回 ("", "") 且零 IO"""
    data_dir = tmp_path / "data"
    assert materialize_schema_migration(str(tmp_path / "nope.yml"), str(data_dir)) == ("", "")
    assert not data_dir.exists()


def test_reject_stale_version_non_integer_shape_passes_gate():
    """版本闸门只拦「低于当前/缺失」: 非整数形状(交给校验层报精确错)与合法当前版本原样通过"""
    from auto_qb.config.writer import _reject_stale_version

    _reject_stale_version({"config": {"schema_version": "abc"}})  # 不抛
    _reject_stale_version({"config": {"schema_version": []}})  # 不抛
    from auto_qb.infra.versioning import CURRENT_VERSIONS

    _reject_stale_version({"config": {"schema_version": str(CURRENT_VERSIONS["config"])}})  # 当前版本放行


def test_materialize_bad_version_wraps_config_error(tmp_path):
    """磁盘 schema_version 形状非法 -> SchemaVersionError 包装为 ConfigError(报清文件与原因)"""
    data_dir = tmp_path / "data"
    path = _make(tmp_path, BASE.replace("schema_version: 8", "schema_version: abc"))
    with pytest.raises(ConfigError, match="schema 版本问题"):
        materialize_schema_migration(path, str(data_dir))
    assert not data_dir.exists(), "探测阶段失败不应产生备份目录"


def test_migrate_config_1_2_legacy_shapes(tmp_path=None):
    """v1→v2 改写: 旧键非字典直接删除; mode=off 等价键不存在; 定位不到档案原地保留"""
    from auto_qb.config.migrations import _migrate_config_1_2

    # 旧键形状烂: 读不出 mode -> 删除
    cfg = {"trackers": {"T1": {"hr_check": "junk"}}}
    out = _migrate_config_1_2(cfg)
    assert "hr_check" not in out["trackers"]["T1"]

    # mode=off: 新口径下 off = 键不存在
    cfg = {"trackers": {"T1": {"hr_check": {"mode": "off", "hr_page_url": "https://pt.btschool.club/x"}}}}
    out = _migrate_config_1_2(cfg)
    assert "hr_check" not in out["trackers"]["T1"]

    # 非字典 hr_page_url + 陌生 host: 定位不到档案, 原地保留(交校验层报废除错)
    cfg = {"trackers": {"T1": {"hr_check": {"mode": "all", "hr_page_url": 123}}}}
    out = _migrate_config_1_2(cfg)
    assert out["trackers"]["T1"]["hr_check"] == {"mode": "all", "hr_page_url": 123}


def test_migrate_config_1_2_new_position_wins():
    """v1→v2: hr_check/sites 已存在且档案条目已在 -> 新位置获胜, 旧键只删除不覆盖(含调优键丢弃)"""
    from auto_qb.config.migrations import _migrate_config_1_2

    cfg = {
        "trackers":
            {
                "T1":
                    {
                        "hr_check":
                            {
                                "mode": "all",
                                "hr_page_url": "https://pt.btschool.club/myhr.php",
                                "refresh_interval": "9H",
                            }
                    }
            },
        "hr_check": {
            "sites": {
                "btschool": {
                    "enabled": True
                }
            }
        },
    }
    out = _migrate_config_1_2(cfg)
    assert out["hr_check"]["sites"]["btschool"] == {"enabled": True}, "新位置已有条目: 旧值不并入"
    assert "hr_check" not in out["trackers"]["T1"]


def test_migrate_config_1_2_creates_entry_with_tuning_keys():
    """v1→v2 正例: 定位到档案 -> 建 hr_check.sites 条目(mode + 随迁调优键), 页面事实键丢弃"""
    from auto_qb.config.migrations import _migrate_config_1_2

    cfg = {
        "trackers":
            {
                "T1":
                    {
                        "hr_check":
                            {
                                "mode": "partial",
                                "hr_page_url": "https://pt.btschool.club/myhr.php",
                                "refresh_interval": "2H",
                                "adapter": "should-be-dropped",
                            }
                    }
            }
    }
    out = _migrate_config_1_2(cfg)
    entry = out["hr_check"]["sites"]["btschool"]
    assert entry["mode"] == "partial" and entry["refresh_interval"] == "2H"
    assert "adapter" not in entry, "页面事实四键以档案为准, 一律丢弃"
    assert "hr_check" not in out["trackers"]["T1"]


def test_migrate_config_2_3_site_entry_shapes():
    """v2→v3 sites 条目: 非 dict 条目整体删除; mode partial/all -> enabled=true(保留 tracker/refresh_interval)"""
    from auto_qb.config.migrations import _migrate_config_2_3

    cfg = {
        "hr_check":
            {
                "min_torrent_interval": "30S",
                "max_pages_per_day": 500,
                "sites":
                    {
                        "btschool": "junk",  # 形状烂: 整体删除
                        "carpt": {
                            "mode": "partial",
                            "tracker": "T1",
                            "refresh_interval": "2H"
                        },
                    },
            }
    }
    out = _migrate_config_2_3(cfg)
    sites = out["hr_check"]["sites"]
    assert "btschool" not in sites, "非 dict 条目无处可迁: 删除"
    assert sites["carpt"] == {"enabled": True, "tracker": "T1", "refresh_interval": "2H"}
    assert "min_interval" in out["hr_check"] and "min_torrent_interval" not in out["hr_check"]
    assert "max_pages_per_day" not in out["hr_check"], "全局废弃键随 v3 删除"


def test_materialize_non_mapping_config_section_noop(tmp_path, monkeypatch):
    """磁盘树读出来后 config 段不是映射 -> 物化按「无事可做」返回 ("", ""), 零备份零写盘

    read_tree 自身会把非映射 config 归一为空映射, 本用例以替身喂入「绕过归一」的树,
    钉住物化入口对畸形形状的防御分支(不能在物化里炸)。
    """
    from auto_qb.config import writer

    path = _make(tmp_path, BASE)
    monkeypatch.setattr(writer, "read_tree", lambda p: {"other": 1})
    desc, backup = materialize_schema_migration(path, str(tmp_path / "data"))
    assert desc == "" and backup == ""
    assert not (tmp_path / "data").exists(), "无事可做不应产生备份目录"


def test_backup_versioned_relative_backup_dir(tmp_path, monkeypatch):
    """backup_dir 为空串 -> 备份路径是裸文件名(无父目录), 跳过建目录分支, 直写 CWD"""
    from auto_qb.config.writer import backup_versioned

    path = _make(tmp_path, BASE)
    monkeypatch.chdir(tmp_path)
    backup = backup_versioned(path, "", 3)
    assert backup == "config.yml.v3.bak"
    with open(backup, "r", encoding="utf-8") as f:
        assert f.read() == BASE, "版本号备份内容 = 迁移前原样"


# v3 存量形态: 站点/全局都有「写了也白写」的 ''(v3 里被 _strip_none 剥成未配置)
V3_WITH_EMPTIES = (
    "config:\n"
    "  schema_version: 3\n"
    "  remove_similar_tags: ''\n"
    "  hr:\n"
    "    add_tag: ''\n"
    "    add_category: zCat\n"
    "    exclude_tags: ''\n"
    "  trackers:\n"
    "    A:\n"
    "      domains: [a.com]\n"
    "      remove_similar_tags: ''\n"
    "      hr:\n"
    "        required_seeding_time: 3D\n"
    "        add_tag: ''\n"
    "        add_category_for_satisfied: ''\n"
    "        overwrite_category: ''\n"
    "        exclude_categories: ''\n"
    "    B:\n"
    "      domains: [b.com]\n"
    "      hr:\n"
    "        required_seeding_time: 3D\n"
    "        add_tag: zB\n"
)


def test_migrate_config_3_4_removes_explicit_empty():
    """v3→v4 迁移单测: 9 键作用域内显式置空值移除, 返回 (cfg, notes) 逐键明细(非空值/无关站点不误杀)"""
    from auto_qb.config.migrations import _migrate_config_3_4

    cfg = {
        "schema_version": 3,
        "remove_similar_tags": "",
        "hr": {
            "add_tag": "",
            "add_category": "zCat",
            "exclude_tags": ""
        },
        "trackers":
            {
                "A":
                    {
                        "domains": ["a.com"],
                        "remove_similar_tags": "",
                        "hr":
                            {
                                "required_seeding_time": "3D",
                                "add_tag": "",
                                "add_category_for_satisfied": "",
                                "overwrite_category": "",
                                "exclude_categories": "",
                            },
                    },
                "B": {
                    "domains": ["b.com"],
                    "hr": {
                        "required_seeding_time": "3D",
                        "add_tag": "zB"
                    }
                },
                "C": "junk",  # 形状烂的站点: 跳过不炸
            },
    }
    out, notes = _migrate_config_3_4(cfg)

    assert out["schema_version"] == 3, "版本章由框架盖章, 迁移函数不碰版本字段"
    assert "remove_similar_tags" not in out
    assert out["hr"] == {"add_category": "zCat"}, "全局段只移除 '', 非空值保留"
    a = out["trackers"]["A"]
    assert "remove_similar_tags" not in a
    assert a["hr"] == {"required_seeding_time": "3D"}, "站点段 4 类 '' 全部移除, 必填键保留"
    assert out["trackers"]["B"]["hr"]["add_tag"] == "zB", "非空值与无 '' 的站点不误杀"

    paths = {note.split(":", 1)[0] for note in notes}
    assert paths == {
        "config.remove_similar_tags",
        "config.hr.add_tag",
        "config.hr.exclude_tags",
        "config.trackers.A.remove_similar_tags",
        "config.trackers.A.hr.add_tag",
        "config.trackers.A.hr.add_category_for_satisfied",
        "config.trackers.A.hr.overwrite_category",
        "config.trackers.A.hr.exclude_categories",
    }
    assert all("显式置空已移除" in note and "如需覆盖为空请重新显式配置" in note for note in notes)


def test_migrate_config_3_4_idempotent():
    """v3→v4 迁移幂等: 移除后重放无变更、无 notes(返回裸 dict; 崩溃重放安全)"""
    from auto_qb.config.migrations import _migrate_config_3_4

    out1, _ = _migrate_config_3_4({"hr": {"add_tag": ""}, "trackers": {"A": {"hr": {"add_tag": ""}}}})
    result2 = _migrate_config_3_4(out1)
    assert result2 == out1, "第二次应无任何可移除项, 原样返回(裸 dict 形态)"


def test_materialize_v3_removes_explicit_empty_with_warning(tmp_path, caplog):
    """v3 文件物化: 作用域内 '' 移除并落盘当前版本(v3→v4→v5→v6→v7→v8), 每个被移除键一条 WARNING(用户拍板: 日志必须可见)"""
    import logging

    data_dir = tmp_path / "data"
    path = _make(tmp_path, V3_WITH_EMPTIES)

    with caplog.at_level(logging.WARNING, logger="auto_qb.config.loaders"):
        desc, backup = materialize_schema_migration(path, str(data_dir))

    assert desc == "v3→v8"
    assert backup == str(data_dir / "config.yml.v3.bak")
    text = _text(path)
    assert "schema_version: 8" in text
    assert "add_tag: ''" not in text and "remove_similar_tags: ''" not in text \
        and "overwrite_category: ''" not in text, "作用域内的 '' 全部移除"
    assert "add_tag: zB" in text, "非空值不误杀"
    assert "add_category: zCat" in text, "非空值不误杀"
    cfg = load_config(path)
    assert cfg.trackers["A"].hr.add_tag == "" and cfg.hr.add_tag == "", "站点与全局的 '' 都移除 = 双双走默认"
    warnings = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert any("config.trackers.A.hr.add_tag" in m and "显式置空已移除" in m for m in warnings), warnings
    assert any("config.hr.add_tag" in m for m in warnings), warnings


def test_materialize_v4_site_empty_untouched(tmp_path):
    """v4 文件的站点 '' = 覆盖为空(v4 起的合法语义): v4→v8 迁移不得误杀, 站点 '' 原样保留, 加载后生效值 = ''"""
    data_dir = tmp_path / "data"
    path = _make(tmp_path, V4_SITE_EMPTY)

    desc, backup = materialize_schema_migration(path, str(data_dir))
    assert desc == "v4→v8" and backup == str(data_dir / "config.yml.v4.bak")
    text = _text(path)
    assert "schema_version: 8" in text
    assert "add_tag: ''" in text, "v4 的站点 '' 不得被迁移移除"
    cfg = load_config(path)
    assert cfg.trackers["A"].hr.add_tag == "", "覆盖为空生效(不回退全局 zGlobal)"
    assert cfg.hr.add_tag == "zGlobal"


def test_materialize_passes_config_path_to_migration(tmp_path, monkeypatch):
    """物化调迁移函数必须传**真实 config_path**(不是 None)

    变异把 `migrate_config_schema(tree, config_path)` 的第二个实参改成 None —— 迁移里用它做
    日志/定位, 传 None 时行为错但目前无守阵。用 spy 卡住实参。
    """
    from auto_qb.config import writer as writer_mod

    data_dir = tmp_path / "data"
    path = _make(tmp_path, LEGACY_V1)
    seen = []
    real = writer_mod.migrate_config_schema

    def spy(tree, config_path):
        seen.append(config_path)
        return real(tree, config_path)

    monkeypatch.setattr(writer_mod, "migrate_config_schema", spy)
    desc, _ = writer_mod.materialize_schema_migration(path, str(data_dir))
    assert desc == "v1→v8"
    assert seen == [path], "迁移函数必须收到真实 config_path(传 None 会让迁移无法定位文件)"


def test_backup_versioned_creates_parent_and_relative_forms(tmp_path, monkeypatch):
    """backup_versioned: 有父目录时**必须建目录**(parent 被改成 None/缩进丢失/exit_ok 改值都会漏建)

    变异簇: `parent = os.path.dirname(backup_path)` → None · `os.makedirs(parent, exist_ok=True)`
    → `None`/`False`/整句删。守阵: 嵌套备份目录不存在时备份仍必须落盘(顺带覆盖 exist_ok 语义).
    """
    from auto_qb.config.writer import backup_versioned

    path = _make(tmp_path, BASE)
    nested = tmp_path / "deep" / "dir" / "data"
    backup = backup_versioned(path, str(nested), 3)
    assert backup == str(nested / "config.yml.v3.bak")
    with open(backup, encoding="utf-8") as f:
        assert f.read() == BASE, "版本号备份内容 = 迁移前原样"

    # exist_ok=True 语义: 目录已存在时重入不得抛 FileExistsError
    again = backup_versioned(path, str(nested), 3)
    assert again == backup


def test_reject_stale_version_guards_non_dict_cfg():
    """版本闸门: cfg 非 dict 时不得去 `cfg.get`(变异把三元条件改成恒真会 AttributeError)

    守阵: config 段是标量/列表时按「版本缺失」口径拒绝(与缺失同路), 不是崩在属性访问上。
    """
    from auto_qb.config.writer import _reject_stale_version

    for bad_cfg in ("plain", ["x"], 5):
        with pytest.raises(ConfigError) as ei:
            _reject_stale_version({"config": bad_cfg})
        assert "schema_version" in str(ei.value), f"非映射 config 段应按版本缺失拒绝: {bad_cfg!r}"


def test_reject_stale_version_message_carries_both_versions(tmp_path):
    """版本闸门的错误消息必须带上两个版本号(变异把消息整段换成 None 会丢掉唯一排障线索)"""
    from auto_qb.config.writer import _reject_stale_version
    from auto_qb.infra.versioning import CURRENT_VERSIONS

    current = CURRENT_VERSIONS["config"]
    with pytest.raises(ConfigError) as ei:
        _reject_stale_version({"config": {"schema_version": str(current - 1)}})
    msg = str(ei.value)
    assert f"v{current - 1}" in msg and f"v{current}" in msg, f"消息须同时说清两个版本号: {msg}"
    assert "刷新" in msg, "消息须指路刷新页签"


def test_fallback_readonly_skips_version_key_but_covers_others():
    """readonly 回退必须**跳过 schema_version**、**continue 而非 break**、按点路径处理其余键

    三条同构变异: 1. `path == VERSION_KEY` 改 `!=`(全部跳过) 2. `continue` 改 `break`(命中版本键后
    整轮中断, 后面的 readonly 键再也不回退) 3. split(".") 改错. 守阵: 磁盘对 data_dir/fs 有旧值,
    对 schema_version 也构造「程序更新」的值 — 版本键必须**不被回退**(交给校验层报错).
    """
    from auto_qb.config.writer import _fallback_readonly_fields

    old_tree = {"config": {"data_dir": "disk-dir", "fs": {"path_map": [{"from": "a", "to": "b"}]}}}
    tree = {
        "config":
            {
                "data_dir": "ui-dir",
                "fs": {
                    "path_map": [{
                        "from": "x",
                        "to": "y"
                    }]
                },
                "schema_version": 999,  # 比程序新 -> 不得被回退抹平
            }
    }
    _fallback_readonly_fields(tree, old_tree)
    assert tree["config"]["data_dir"] == "disk-dir", "readonly 键须回退为磁盘旧值"
    assert tree["config"]["fs"] == {"path_map": [{"from": "a", "to": "b"}]}, "readonly 段须整体回退"

    # break 变异的反例: 版本键在 fs/data_dir 之前时, 后续键仍须回退
    old_tree2 = {"config": {"data_dir": "disk-dir"}}
    tree2 = {"config": {"schema_version": 999, "data_dir": "ui-dir"}}
    _fallback_readonly_fields(tree2, old_tree2)
    assert tree2["config"]["data_dir"] == "disk-dir", "命中版本键后不得中断后续 readonly 键的回退"
    assert tree2["config"]["schema_version"] == 999, "版本键必须留给盖章/校验层, 不回退"


def test_migrate_config_6_7_exact_roundtrip():
    """v6→v7 精确还原: 旧 1.5S + main_tick 1.5S -> 1 倍(生效 1.5s 与原值一致), 旧键消失, 单条 note"""
    from auto_qb.config.migrations import _migrate_config_6_7

    cfg = {"main_tick": "1.5S", "qb_traffic": {"sample_interval": "1.5S", "enabled": True}}
    out, notes = _migrate_config_6_7(cfg)

    assert out["qb_traffic"] == {"sample_interval_multiplier": 1, "enabled": True}, "同段其余键原样保留"
    assert "sample_interval" not in out["qb_traffic"], "旧键删除(新口径下它是未知键)"
    assert len(notes) == 1, "每个旧键一条 note"
    assert notes[0].startswith("config.qb_traffic.sample_interval -> ")
    assert "1 倍" in notes[0] and "1.5s" in notes[0], notes[0]


def test_migrate_config_6_7_seconds_to_multiplier():
    """v6→v7: 30S + main_tick 2S -> 15 倍; main_tick 缺席兜 2.0(models 同源); 版本链注册可串行"""
    from auto_qb.config.migrations import _migrate_config_6_7

    out, _ = _migrate_config_6_7({"main_tick": "2S", "qb_traffic": {"sample_interval": "30S"}})
    assert out["qb_traffic"] == {"sample_interval_multiplier": 15}

    out2, _ = _migrate_config_6_7({"qb_traffic": {"sample_interval": "30S"}})
    assert out2["qb_traffic"] == {"sample_interval_multiplier": 15}, "main_tick 缺失兜 2.0"

    from auto_qb.infra.versioning import migrate

    chained, desc = migrate(
        "config", {
            "schema_version": 6,
            "main_tick": "2S",
            "qb_traffic": {
                "sample_interval": "30S"
            }
        }
    )
    assert desc == "v6→v8" and chained["qb_traffic"]["sample_interval_multiplier"] == 15, (
        "迁移必须已注册进版本链(现行 v8 起链跨 v6→v7→v8 两级, 换算结果须原样穿过后续级)"
    )


def test_migrate_config_6_7_clamped_to_effective_seconds_cap():
    """v6→v7 钳制: 600S + main_tick 7S -> 85 倍(85x7=595s <= 600s), note 明示被钳制"""
    from auto_qb.config.migrations import _migrate_config_6_7

    out, notes = _migrate_config_6_7({"main_tick": "7S", "qb_traffic": {"sample_interval": "600S"}})
    assert out["qb_traffic"]["sample_interval_multiplier"] == 85
    assert len(notes) == 1 and "钳制" in notes[0] and "595s" in notes[0], notes


def test_migrate_config_6_7_rounds_up():
    """v6→v7 非整除向上取整: 7S + main_tick 2S -> 4 倍(生效 8s, 采样更密不丢数据点)"""
    from auto_qb.config.migrations import _migrate_config_6_7

    out, _ = _migrate_config_6_7({"main_tick": "2S", "qb_traffic": {"sample_interval": "7S"}})
    assert out["qb_traffic"]["sample_interval_multiplier"] == 4


def test_migrate_config_6_7_no_legacy_key_untouched():
    """v6→v7 D9: 未设旧键 -> 不动、零 note、零 diff(不补写新键, 默认变更由升级行为本身承担)"""
    from auto_qb.config.migrations import _migrate_config_6_7

    cfg = {"main_tick": "2S", "qb_traffic": {"sample_interval_multiplier": 5}}
    before = copy.deepcopy(cfg)
    result = _migrate_config_6_7(cfg)
    assert not isinstance(result, tuple), "无旧键时返回裸 dict(框架两种形态都接受)"
    assert cfg == before, "零副作用(不补写、不改值)"


def test_migrate_config_6_7_idempotent():
    """v6→v7 幂等: 连跑两次, 第二次零 diff(崩溃重放安全)"""
    from auto_qb.config.migrations import _migrate_config_6_7

    out1, _ = _migrate_config_6_7({"main_tick": "2S", "qb_traffic": {"sample_interval": "30S"}})
    snapshot = copy.deepcopy(out1)
    result2 = _migrate_config_6_7(out1)
    assert result2 == out1 == snapshot, "第二次应无可迁移项, 原样返回"


def test_migrate_config_6_7_main_tick_over_cap():
    """v6→v7: main_tick 700S(超 600s 上限) -> floor 为 0, 倍数兜 1, note 写明该配置下上限不可满足"""
    from auto_qb.config.migrations import _migrate_config_6_7

    out, notes = _migrate_config_6_7({"main_tick": "700S", "qb_traffic": {"sample_interval": "30S"}})
    assert out["qb_traffic"]["sample_interval_multiplier"] == 1
    assert len(notes) == 1 and "超过 600s" in notes[0] and "不可满足" in notes[0], notes


def test_migrate_config_6_7_unparsable_legacy_value_kept():
    """v6→v7: 旧值不可解析 -> 旧键原地保留(不猜用户意图) + 一条 note 指路手改; 随后由校验层 fail-fast"""
    from auto_qb.config.migrations import _migrate_config_6_7

    cfg = {"main_tick": "2S", "qb_traffic": {"sample_interval": "abc"}}
    out, notes = _migrate_config_6_7(cfg)
    assert out["qb_traffic"] == {"sample_interval": "abc"}, "旧键保留, 不写入新键"
    assert len(notes) == 1 and "无法解析" in notes[0] and "手工" in notes[0], notes


# ---- v7→v8: 顶层 bt_backup 多实例表收编为 relocate.bt_backup 单实例标量(计划 26-11-11-0259 S2/D7) ----


def test_migrate_config_7_8_single_entry_moved():
    """v7→v8 恰一条非空条目: 值搬成 relocate.bt_backup(strip), 旧键删除, 单条 note; 同段其余键原样"""
    from auto_qb.config.migrations import _migrate_config_7_8

    cfg = {"bt_backup": {"192.168.1.5:8080": " /qb/BT_backup "}, "relocate": {"enabled": "true"}}
    out, notes = _migrate_config_7_8(cfg)

    assert "bt_backup" not in out, "旧顶层表删除(新口径下它是未知键)"
    assert out["relocate"] == {"enabled": "true", "bt_backup": "/qb/BT_backup"}, "值收编为标量(strip), 段内其余键原样"
    assert len(notes) == 1, notes
    assert notes[0].startswith("config.bt_backup[") and "-> config.relocate.bt_backup" in notes[0], notes

    from auto_qb.infra.versioning import migrate

    chained, desc = migrate("config", {"schema_version": 7, "bt_backup": {"h:1": "/qb/BT_backup"}})
    assert desc == "v7→v8" and chained["relocate"]["bt_backup"] == "/qb/BT_backup", "迁移必须已注册进版本链"


def test_migrate_config_7_8_single_entry_new_position_wins():
    """v7→v8 新旧并存: relocate.bt_backup 已有显式值时新位置获胜, 旧表只删除不覆盖(v1→v2 同款)"""
    from auto_qb.config.migrations import _migrate_config_7_8

    cfg = {"bt_backup": {"h:1": "/old/BT_backup"}, "relocate": {"bt_backup": "/new/BT_backup"}}
    out, notes = _migrate_config_7_8(cfg)

    assert "bt_backup" not in out
    assert out["relocate"] == {"bt_backup": "/new/BT_backup"}, "新位置值不被旧表覆盖"
    assert len(notes) == 1 and "/old/BT_backup" in notes[0], notes


def test_migrate_config_7_8_no_key_untouched():
    """v7→v8 无旧键: 不动、零 note、零 diff(relocate 段缺失也不顺手建 —— 仅抬版本号)"""
    import copy as _copy

    from auto_qb.config.migrations import _migrate_config_7_8

    for cfg in ({"main_tick": "2S"}, {"relocate": {"enabled": "true"}}):
        before = _copy.deepcopy(cfg)
        result = _migrate_config_7_8(cfg)
        assert not isinstance(result, tuple), "无旧键时返回裸 dict(框架两种形态都接受)"
        assert cfg == before, "零副作用(relocate 段不被无谓创建)"


def test_migrate_config_7_8_multiple_nonempty_dropped():
    """v7→v8 多于一条非空: 删键 + note 提示重配, 不猜哪条对应当前 qB(D7); relocate 段不被误写"""
    from auto_qb.config.migrations import _migrate_config_7_8

    cfg = {"bt_backup": {"h:1": "/a/BT_backup", "h:2": "/b/BT_backup", "h:3": "   "}, "relocate": {"enabled": "true"}}
    out, notes = _migrate_config_7_8(cfg)

    assert "bt_backup" not in out, "旧表整体删除"
    assert out["relocate"] == {"enabled": "true"}, "不猜测: 不把任何条目写进 relocate 段"
    assert len(notes) == 1 and "2 条非空条目" in notes[0] and "手工" in notes[0], notes


def test_migrate_config_7_8_all_empty_or_junk_dropped():
    """v7→v8 全空/无有效值(空表/纯空白值/整段非字典): 删键 + note 提示重配, relocate 段不被误建"""
    from auto_qb.config.migrations import _migrate_config_7_8

    for legacy in ({}, {"h:1": ""}, {"h:1": "   "}, "junk"):
        cfg = {"bt_backup": legacy}
        out, notes = _migrate_config_7_8(cfg)
        assert "bt_backup" not in out, legacy
        assert "relocate" not in out, "无可搬条目不得顺手建 relocate 段"
        assert len(notes) == 1 and "无有效条目" in notes[0] and "config.relocate.bt_backup" in notes[0], (legacy, notes)


def test_migrate_config_7_8_idempotent():
    """v7→v8 幂等: 搬运后重放走「旧键缺席」分支, 零 diff 零 note(崩溃重放安全)"""
    import copy

    from auto_qb.config.migrations import _migrate_config_7_8

    out1, _ = _migrate_config_7_8({"bt_backup": {"h:1": "/qb/BT_backup"}})
    snapshot = copy.deepcopy(out1)
    result2 = _migrate_config_7_8(out1)
    assert result2 == out1 == snapshot, "第二次应无可迁移项, 原样返回(裸 dict)"


V7_WITH_BT_BACKUP = (
    "config:\n"
    "  schema_version: 7\n"
    "  qbittorrent:\n"
    "    host: h\n"
    "    port: 1\n"
    "    username: u\n"
    "    password: p\n"
    "  bt_backup:\n"
    "    'h:1': /qb/BT_backup\n"
    "  relocate:\n"
    "    enabled: true\n"
)


def test_materialize_v7_bt_backup_table_migrates_with_warning(tmp_path, caplog):
    """反证(计划 §04 S2): v7 树装载走迁移后校验绿且 note 落 WARNING —— 旧表恰一条非空条目收编为
    relocate.bt_backup 标量落盘 v8 章, load_config 真链路回读生效"""
    import logging

    data_dir = tmp_path / "data"
    path = _make(tmp_path, V7_WITH_BT_BACKUP)

    with caplog.at_level(logging.WARNING, logger="auto_qb.config.loaders"):
        desc, backup = materialize_schema_migration(path, str(data_dir))

    assert desc == "v7→v8"
    assert backup == str(data_dir / "config.yml.v7.bak")
    text = _text(path)
    assert "schema_version: 8" in text, "磁盘落当前版本章"
    tree = read_tree(path)
    assert "bt_backup" not in tree["config"], "旧顶层表随迁移消失"
    assert tree["config"]["relocate"]["bt_backup"] == "/qb/BT_backup", "值收编为新标量"
    cfg = load_config(path)  # 迁移后的磁盘必须能原样通过加载(校验绿)
    assert cfg.relocate.bt_backup == "/qb/BT_backup"
    warnings = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert any("config.bt_backup" in m and "config.relocate.bt_backup" in m for m in warnings), warnings
