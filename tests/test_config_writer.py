"""test_config_writer 测试计划: 配置写回(结构化树 -> 校验 -> R 级回退 -> round-trip 写盘)

## 测试计划(每个测试函数一条)
- test_read_tree_scalars_are_strings: 读出的树与 BaseLoader 语义一致(标量全为字符串)
- test_read_tree_missing_or_empty_file: 文件不存在/空/非映射 -> 空 config 段
- test_write_tree_stamps_schema_version: 写回侧打标: 保存后 config.schema_version 盖当前版本(int 无引号)
- test_write_tree_requires_config_root: 缺少 config 根段 -> ValueError
- test_write_tree_invalid_rejected_without_touching_disk: 非法值 -> ConfigError 且磁盘不变
- test_write_tree_preserves_comments_and_plain_scalars: 写回保留注释, 未修改标量保持原书写风格
- test_write_tree_updates_existing_scalar: 修改已有键 -> 按项目风格写出(数字/布尔无引号)
- test_write_tree_adds_and_removes_keys: 新增键写入/缺失键移除
- test_write_tree_removes_empty_list: 列表被清空后键移除
- test_write_tree_restart_field_fallback: R 级字段回退为磁盘旧值并回报 restart_required
- test_write_tree_restart_field_removed_when_absent_on_disk: 磁盘未配置的 R 级字段提交后被删除(走默认值)
- test_write_tree_readonly_section_fallback: readonly 段(fs, issue 26-09-28-2135)提交改值回退为磁盘旧值(schema 键面写盘防线)
- test_write_tree_readonly_section_removed_when_absent_on_disk: 磁盘未配置的 readonly 段提交后被删除(走默认值)
- test_write_tree_rejects_version_higher_than_program: 提交树版本高于程序 -> 校验层精确报错(readonly 防线不回退 schema_version, 不吞掉该错)
- test_write_tree_updates_derived_state_file: 改 data_dir 时派生的 state_file 一并回退
- test_write_tree_writes_float_and_negative_scalars_plain: 浮点字符串按原生标量写出
- test_write_tree_backup_created: 写盘前生成 `data/config.yml.bak` 备份(父目录按需创建)
- test_backup_atomic_write_no_partial_bak: 保存前备份走 atomic_write(与 backup_versioned 统一), 写盘中断不留半截 .bak
- test_preview_tree_does_not_touch_disk: 预览不落盘, 且内容与写盘结果一致(除注释形态)
- test_preview_tree_invalid_raises: 预览同样做校验
- test_preview_tree_does_not_create_backup: 预览不产生任何备份文件
- test_mask_tree_hides_sensitive_scalars: 敏感键(键名含 password/passkey/token)的非空标量被掩码; 空值与普通键不受影响; 原树不被就地修改
- test_unmask_tree_restores_from_disk: 提交树里的掩码哨兵按磁盘旧值还原 —— 前端"未改密码"原样保存不会把密码写成占位串
- test_write_tree_rejects_stale_version_tree: 版本闸门(计划 26-09-27-2252 用户裁决): 提交树版本低于当前(含缺失)直接拒绝, 磁盘一字不动
- test_write_tree_rejects_v2_tree_with_legacy_key: 已盖 v2 章仍带旧键(手改/事故残留) -> 报废除错且磁盘一字不动(无常驻兼容层)
- test_preview_tree_rejects_stale_version_tree: 预览同口径被闸门拦截
- test_materialize_migrates_and_backups: 启动物化: 版本号备份(迁移前原样) + 磁盘落当前版本新结构 + 返回 desc 与备份路径
- test_materialize_idempotent_and_noop: 已是当前版本零 IO; 二次调用幂等, 不产生新备份- test_materialize_dry_run_probe: write=False(dry-run 探测)只报 desc, 不校验不备份不落盘
- test_materialize_missing_file_returns_empty: 配置文件不存在 -> 原样返回 ("", "") 且零 IO
- test_collect_explicit_empty_paths_all_trackers: v3→v4 显式置空收集不被非 dict 条目中断(continue 而非 break)
- test_unmask_tree_restores_nested_and_toplevel: 哨兵还原遍历整棵树, 嵌套分支命中后顶层后续键仍还原
- test_mask_tree_non_dict_passthrough: 掩码只处理映射, 列表整体不动
- test_unmask_tree_guards_and_sentinel_old_value: 非映射树原样返回; 旧值缺失/本身是哨兵时保持哨兵
- test_stamp_schema_version_ignores_non_dict_cfg: 树缺 config 段时盖章静默跳过
- test_reject_stale_version_non_integer_shape_passes_gate: 版本闸门放行非整数形状(交校验层)与当前版本
- test_write_tree_first_save_on_missing_file: 首存无源可备份(跳过) + 从空文档建树
- test_write_tree_rebuilds_doc_from_non_mapping_file: 磁盘文件是非映射 YAML 时以空文档重建
- test_write_tree_roundtrip_list_of_dicts_and_plain_int: 映射列表按 BaseLoader 语义比较; 数字字符串写原生标量
- test_materialize_bad_version_wraps_config_error: 磁盘 schema_version 非法 -> 包装 ConfigError 且零落盘
- test_url_host_shapes: host 提取(非串/畸形 IPv6 -> 空串; 正常小写化)
- test_migrate_config_1_2_legacy_shapes: v1→v2 旧键非字典删除 / mode=off 删除 / 定位不到档案原地保留
- test_migrate_config_1_2_new_position_wins: v1→v2 新位置已有条目获胜, 旧键只删除
- test_migrate_config_1_2_creates_entry_with_tuning_keys: v1→v2 正例(建条目+调优键随迁+页面事实键丢弃)
- test_migrate_config_2_3_site_entry_shapes: v2→v3 非 dict 条目删除 / mode→enabled / 改名与废弃键清理
- test_materialize_non_mapping_config_section_noop: 树缺 config 映射段 -> 物化按无事可做返回, 零 IO
- test_backup_versioned_relative_backup_dir: 备份目录为空串(相对裸文件名) -> 跳过建目录, 直写 CWD
- test_write_tree_backup_relative_path: 备份路径无父目录 -> 跳过 makedirs 分支, 备份照常产生
- test_path_helpers_mid_node_shapes: _set_path 中途节点非 dict 重建 / _delete_path 中途非 dict 与裸标量树安全返回
- test_migrate_config_3_4_removes_explicit_empty: v3→v4 迁移单测 —— 9 键作用域内显式置空移除 + 逐键 notes(非空值/无关站点不误杀)
- test_migrate_config_3_4_idempotent: v3→v4 迁移幂等 —— 移除后重放无变更无 notes(崩溃重放安全)
- test_materialize_v3_removes_explicit_empty_with_warning: v3 文件物化 —— 作用域 '' 移除落盘 v4 + 每键 WARNING(caplog)
- test_materialize_v4_site_empty_untouched: v4 文件站点 '' = 覆盖为空(合法保留), 物化零 IO 不误杀
- test_write_tree_roundtrip_preserves_site_explicit_empty: ruamel round-trip 保留站点 ''(report 待核实项①实测)
- test_stamp_schema_version_uses_root_key_and_overwrites: 盖章读 ROOT_KEY 段(非硬编码 None)且无条件覆盖旧版本; 根键非 config 时静默跳过
- test_materialize_passes_config_path_to_migration: 物化调迁移函数传真实 config_path(不是 None) —— spy 卡实参
- test_backup_versioned_creates_parent_and_relative_forms: backup_versioned 按 dirname 建父目录(exist_ok=True 幂等), 嵌套目录不存在也落盘
- test_prepare_passes_old_tree_to_restart_fallback: _prepare 调 R 级回退时 old_tree 来自 read_tree(不是 None)
- test_reject_stale_version_guards_non_dict_cfg: 版本闸门对非映射 config 段走「版本缺失」拒绝, 不崩在属性访问上
- test_reject_stale_version_message_carries_both_versions: 闸门错误消息须同时带两个版本号并指路刷新(整段换 None 会丢排障线索)
- test_validate_tree_temp_file_roundtrip: _validate_tree 临时文件 dumps 后可读(delete=False 契约)+ finally 清理; 失败路径同样清理
- test_validate_tree_finally_guard_skips_none_tmp_path: finally 守卫是短路与(and 写成 or 会把原始 OSError 掩盖成 stat(None) 的 TypeError)
- test_build_yaml_preserves_quotes_and_indent_profile: _build_yaml 保留引号 + 4/4/2 缩进档案(preserve_quotes/indent 三参)
- test_build_doc_reads_existing_and_falls_back_to_empty: _build_doc 读已有 CommentedMap/非映射与缺失文件都回退空文档重建
- test_fallback_helpers_split_dot_paths_and_rebuild_missing_nodes: R 级回退按 `.` 切点路径取旧值、嵌套覆盖、磁盘无旧值则删键(不写 None)
- test_fallback_readonly_skips_version_key_but_covers_others: readonly 回退跳过 schema_version、continue 而非 break、其余键按点路径回退
- test_delete_path_removes_last_segment_only: _delete_path 精确删最后一段(不倒索引/不误删兄弟键), 末段缺失静默
- test_sync_mapping_skips_unchanged_scalar_and_list_nodes: _sync_mapping「值未变不动原节点」对标量与列表都成立(保注释/引号形态)
- test_sync_mapping_scalar_vs_container_not_skipped: _sync_mapping 标量与容器互转不得被「未变化」逻辑吞掉(and 链不得写坏)
- test_same_value_none_and_as_builtin_semantics: _same_value(None,..)=False; _as_builtin 布尔小写/None→空串/数字→str/容器递归
- test_plain_scalar_bool_and_lossless_rules: _plain_scalar 布尔识别大小写无关, 有损数字串(007/1.10)保持字符串
- test_unmask_tree_init_and_guards: unmask_tree 非映射入口原样返回; 旧值缺失/旧值即哨兵时保持哨兵
- test_unmask_tree_only_touches_sentinel_values: unmask_tree 只还原恰为哨兵的键, 用户真改的值不得被旧值覆盖
- test_mask_tree_recurses_into_nested_dicts: mask_tree 递归进嵌套映射掩码深层敏感键; 空值不掩码; 原树不改
- test_set_path_rebuilds_non_mapping_mid_nodes: _set_path 复用已有 dict 中途节点(不丢兄弟键)/标量重建/缺失现场建
- test_backup_skips_when_source_missing_and_keeps_encoding: _backup 源缺失零副作用; 按 dirname 建目录; utf-8 读写无损
"""
import copy
import os

import pytest

from auto_qb.config.errors import ConfigError
from auto_qb.config.loaders import load_config
from auto_qb.config.writer import materialize_schema_migration, preview_tree, read_tree, write_tree

# 「天生当前版本的干净文件」锚(当前 = v4): BASE 供各写盘用例当无 hr 的最小合法配置
BASE = "config:\n  qbittorrent:\n    host: h\n    port: 1\n    username: u\n    password: p\n  schema_version: 4\n"


def _make(tmp_path, text: str) -> str:
    path = tmp_path / "config.yml"
    path.write_text(text, encoding="utf-8")
    return str(path)


def _text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _bak(tmp_path) -> str:
    """测试用备份路径: 与生产同形落在独立 data 目录下(`<data_dir>/<配置名>.bak`)"""
    return str(tmp_path / "data" / "config.yml.bak")


# ---------------------------------------------------------------- 读取


def test_read_tree_scalars_are_strings(tmp_path):
    """读出的树与 BaseLoader 语义一致: 数字/布尔均以字符串形态出现"""
    path = _make(tmp_path, BASE + "  main_tick: 2s\n  web:\n    enabled: true\n    port: 38080\n")
    tree = read_tree(path)
    assert tree["config"]["main_tick"] == "2s"
    assert tree["config"]["web"]["enabled"] == "true"
    assert tree["config"]["web"]["port"] == "38080"


def test_read_tree_missing_or_empty_file(tmp_path):
    """文件不存在/为空/根非映射 -> 返回空 config 段"""
    missing = str(tmp_path / "nope.yml")
    assert read_tree(missing) == {"config": {}}

    empty = _make(tmp_path, "")
    assert read_tree(empty) == {"config": {}}

    # config 段存在但不是映射(如误写成列表/标量) -> 归一为空映射
    wrong_type = _make(tmp_path, "config: []\n")
    assert read_tree(wrong_type) == {"config": {}}


# ---------------------------------------------------------------- 校验


def test_write_tree_requires_config_root(tmp_path):
    """缺少 config 根段(如误删整段)直接拒绝, 不当成"全默认"静默接受"""
    path = _make(tmp_path, BASE)
    with pytest.raises(ValueError):
        write_tree(path, {"qbittorrent": {}}, load_config(path), _bak(tmp_path))


def test_write_tree_invalid_rejected_without_touching_disk(tmp_path):
    """非法值 -> ConfigError 且磁盘内容与备份均不产生"""
    path = _make(tmp_path, BASE)
    before = _text(path)
    tree = read_tree(path)
    tree["config"]["main_tick"] = "abc"
    with pytest.raises(ConfigError):
        write_tree(path, tree, load_config(path), _bak(tmp_path))
    assert _text(path) == before
    assert not (tmp_path / "data").exists(), "校验失败时连备份目录都不应创建"


# ---------------------------------------------------------------- 写盘


def test_write_tree_preserves_comments_and_plain_scalars(tmp_path):
    """round-trip 写盘: 已有键注释保留, 未修改标量保持原书写风格(数字/布尔不加引号)"""
    path = _make(
        tmp_path, "config:\n"
        "  schema_version: 4\n"
        "  # 连接设置\n"
        "  qbittorrent:\n"
        "    host: h\n"
        "    port: 16585\n"
        "    username: u\n"
        "    password: p\n"
        "  web:\n"
        "    enabled: true\n"
    )
    old = load_config(path)
    tree = read_tree(path)
    tree["config"]["main_tick"] = "3s"
    write_tree(path, tree, old, _bak(tmp_path))

    text = _text(path)
    assert "# 连接设置" in text, "已有键注释必须保留"
    assert "port: 16585" in text, "未修改的标量应保持原有书写风格"
    assert "enabled: true" in text, "未修改的布尔应保持原有书写风格"
    assert "3s" in text


def test_write_tree_updates_existing_scalar(tmp_path):
    """修改已有键: 新值按项目风格写出(数字/布尔无引号, 不再是 ruamel 的类型守恒引号)"""
    path = _make(tmp_path, BASE + "  main_tick: 2s\n  web:\n    enabled: false\n")
    old = load_config(path)
    tree = read_tree(path)
    tree["config"]["main_tick"] = "5S"
    tree["config"]["web"]["enabled"] = "true"
    write_tree(path, tree, old, _bak(tmp_path))

    text = _text(path)
    assert "5S" in text
    assert "enabled: true" in text
    assert "'true'" not in text
    assert load_config(path).main_tick == 5.0


def test_write_tree_adds_and_removes_keys(tmp_path):
    """新增键写入树中的值; 树中缺失的键从磁盘移除"""
    path = _make(tmp_path, BASE + "  main_tick: 2s\n  max_tasks_per_tick: 20\n")
    old = load_config(path)
    tree = read_tree(path)
    tree["config"]["interval"] = "90S"
    del tree["config"]["max_tasks_per_tick"]
    write_tree(path, tree, old, _bak(tmp_path))

    text = _text(path)
    assert "90S" in text and "interval" in text
    assert "max_tasks_per_tick" not in text
    loaded = load_config(path)
    assert loaded.interval == 90.0
    assert loaded.max_tasks_per_tick == 20  # 移除后走默认值


def test_write_tree_removes_empty_list(tmp_path):
    """列表清空后写入空列表(结构保留, 原条目全部移除), 解析语义为空"""
    path = _make(tmp_path, BASE + "  delete_tags:\n    - \"A\"\n")
    old = load_config(path)
    tree = read_tree(path)
    tree["config"]["delete_tags"] = []
    write_tree(path, tree, old, _bak(tmp_path))
    text = _text(path)
    assert '"A"' not in text and "- A" not in text
    assert load_config(path).delete_tags == []


# ---------------------------------------------------------------- R 级字段


def test_write_tree_restart_field_fallback(tmp_path):
    """R 级字段(进程身份)提交后回退为磁盘旧值, 并回报 restart_required"""
    path = _make(tmp_path, BASE + "  data_dir: disk-dir\n")
    old = load_config(path)
    tree = read_tree(path)
    tree["config"]["data_dir"] = "ui-dir"
    result = write_tree(path, tree, old, _bak(tmp_path))

    assert "data_dir" in result.restart_required
    text = _text(path)
    assert "disk-dir" in text and "ui-dir" not in text
    assert result.changes, "变更列表应包含本次差异"


def test_write_tree_updates_derived_state_file(tmp_path):
    """data_dir 变更会派生 state_file(两者同为 R 级), 均回退为磁盘旧值"""
    path = _make(tmp_path, BASE + "  data_dir: disk-dir\n")
    old = load_config(path)
    tree = read_tree(path)
    tree["config"]["data_dir"] = "ui-dir"
    result = write_tree(path, tree, old, _bak(tmp_path))
    assert set(result.restart_required) <= {"data_dir", "state_file"}
    # 磁盘上既没有 data_dir 新值, 也没有派生出的 state_file 新值
    assert "ui-dir" not in _text(path)


def test_write_tree_restart_field_removed_when_absent_on_disk(tmp_path):
    """磁盘原本未配置 R 级字段: 提交后被回退为"未配置"(键被删除, 走默认值)"""
    path = _make(tmp_path, BASE)
    old = load_config(path)
    tree = read_tree(path)
    tree["config"]["data_dir"] = "ui-dir"
    result = write_tree(path, tree, old, _bak(tmp_path))

    assert "data_dir" in result.restart_required
    assert "data_dir" not in _text(path), "磁盘未配置的 R 级字段不得被写入"
    assert load_config(path).data_dir == "auto-qb-data"


def test_write_tree_readonly_section_fallback(tmp_path):
    """readonly 段(fs, issue 26-09-28-2135)提交改值回退为磁盘旧值 —— schema 键面写盘防线

    R 级回退只认"本次变更命中 R 闸的段"; 本防线按 schema 的 readonly 标全量兜底, 与 R 级回退
    覆盖面有交集无冲突(都回退到同一磁盘旧值)。fs 段同时是两者, 任一失效另一道仍兜住。
    """
    path = _make(tmp_path, BASE + "  fs:\n    path_map:\n      - from: D:/Downloads/Old\n        to: /mnt/old\n")
    old = load_config(path)
    tree = read_tree(path)
    tree["config"]["fs"]["path_map"] = [{"from": "D:/Downloads/New", "to": "/mnt/new"}]
    result = write_tree(path, tree, old, _bak(tmp_path))

    assert result.changes, "变更列表应包含本次差异(回退不掩盖提交树的 diff)"
    new_tree = read_tree(path)
    assert new_tree["config"]["fs"]["path_map"] == [{"from": "D:/Downloads/Old", "to": "/mnt/old"}], "readonly 段应保留磁盘旧值"
    assert "D:/Downloads/New" not in _text(path), "readonly 段的新值不得写入磁盘"


def test_write_tree_readonly_section_removed_when_absent_on_disk(tmp_path):
    """磁盘未配置的 readonly 段: 提交后被删除(走默认值), 不得被写入 —— 与 R 级回退同语义"""
    path = _make(tmp_path, BASE)
    old = load_config(path)
    tree = read_tree(path)
    tree["config"]["fs"] = {"path_map": [{"from": "D:/Downloads/New", "to": "/mnt/new"}]}
    write_tree(path, tree, old, _bak(tmp_path))

    assert "fs" not in read_tree(path)["config"], "磁盘未配置的 readonly 段不得被写入"
    assert load_config(path).fs.path_map == (), "fs 走默认(空映射)"


def test_write_tree_rejects_version_higher_than_program(tmp_path):
    """提交树版本高于程序: 放行给校验层报精确错(readonly 防线不回退 schema_version, 不吞掉该错)

    issue 26-09-28-2135 的红线: schema_version 的只读由 _stamp_schema_version 盖章承担;
    若 readonly 回退也碰它, 「文件比程序新」的树会被抹平成磁盘旧值静默保存, 吞掉用户排障的
    唯一线索(报错须同时说清两个版本号)。
    """
    from auto_qb.infra.versioning import CURRENT_VERSIONS

    path = _make(tmp_path, BASE)
    old = load_config(path)
    tree = read_tree(path)
    tree["config"]["schema_version"] = str(CURRENT_VERSIONS["config"] + 1)
    with pytest.raises(ConfigError) as ei:
        write_tree(path, tree, old, _bak(tmp_path))
    assert "高于本程序支持" in str(ei.value)
    assert read_tree(path)["config"]["schema_version"] == "4", "拒绝时磁盘一字不动"


def test_write_tree_writes_float_and_negative_scalars_plain(tmp_path):
    """浮点/布尔样式字符串按原生标量写出(与项目 YAML 风格一致), 不产生多余引号"""
    path = _make(tmp_path, BASE)
    old = load_config(path)
    tree = read_tree(path)
    tree["config"]["trackers"] = {
        "T1": {
            "domains": ["a.com"],
            "hr": {
                "required_seeding_time": "3D",
                "required_share_ratio": "1.5"
            }
        }
    }
    write_tree(path, tree, old, _bak(tmp_path))

    text = _text(path)
    assert "required_share_ratio: 1.5" in text
    assert "'1.5'" not in text and '"1.5"' not in text
    assert load_config(path).trackers["T1"].hr.required_share_ratio == 1.5


def test_write_tree_keeps_lossy_numeric_strings_quoted(tmp_path):
    """会因类型转换丢失信息的数字串(1.10/007)必须保持字符串形态, 不得被规范化"""
    path = _make(tmp_path, BASE)
    old = load_config(path)
    tree = read_tree(path)
    tree["config"]["trackers"] = {
        "T1": {
            "domains": ["a.com"],
            "hr": {
                "required_seeding_time": "3D",
                "required_share_ratio": "1.10"
            }
        }
    }
    write_tree(path, tree, old, _bak(tmp_path))

    text = _text(path)
    assert "1.10" in text, "1.10 不得被写成 1.1"
    assert str(load_config(path).trackers["T1"].hr.required_share_ratio) == "1.1"  # 解析器自身语义
    assert "required_share_ratio: '1.10'" in text or 'required_share_ratio: "1.10"' in text


def test_write_tree_backup_created(tmp_path):
    """写盘前生成 `<data_dir>/<配置名>.bak` 备份(内容为写盘前文本; 父目录不存在时按需创建)

    备份落 data 目录是用户要求: 不再在项目根目录散落 config.yml.bak。
    """
    path = _make(tmp_path, BASE)
    before = _text(path)
    old = load_config(path)
    tree = read_tree(path)
    tree["config"]["main_tick"] = "7s"
    backup = _bak(tmp_path)
    assert not os.path.isdir(os.path.dirname(backup)), "前置: 备份目录本不存在"

    write_tree(path, tree, old, backup)

    assert os.path.isdir(os.path.dirname(backup)), "应自动创建备份目录"
    with open(backup, "r", encoding="utf-8") as f:
        assert f.read() == before
    assert not (tmp_path / "config.yml.bak").exists(), "项目目录不得再产生 .bak"


def test_backup_atomic_write_no_partial_bak(tmp_path, monkeypatch):
    """保存前备份走 utils.atomic_write(与 backup_versioned 统一): 写盘中断不留半截 .bak

    备份恰是坏配置的恢复资产, 半截比没有更危险(issue 26-10-06-0028 chore-config-writer-backup-atomic;
    原 "w" 直写从 O_TRUNC 守阵面外漏过)。
    """
    from auto_qb.config import writer as writer_mod
    from auto_qb.infra import utils as infra_utils

    path = _make(tmp_path, BASE)
    backup = _bak(tmp_path)

    routed = []
    real_atomic = infra_utils.atomic_write

    def spy_atomic(p, fn, keep_backup=False):
        routed.append(p)
        real_atomic(p, fn, keep_backup)

    monkeypatch.setattr(infra_utils, "atomic_write", spy_atomic)
    writer_mod._backup(path, backup)
    assert routed == [backup], "保存前备份必须经 utils.atomic_write(与 backup_versioned 统一)"
    assert _text(backup) == _text(path), ".bak 内容 = 写盘前原样"

    # 写盘中断(内容写到一半抛): 干净路径上不得出现半截文件(atomic_write 失败即无目标文件)
    backup2 = str(tmp_path / "data" / "config2.yml.bak")

    def interrupted(p, fn, keep_backup=False):
        def boom(f):
            f.write("半截")
            raise RuntimeError("模拟写盘中断")

        real_atomic(p, boom, keep_backup)

    monkeypatch.setattr(infra_utils, "atomic_write", interrupted)
    with pytest.raises(RuntimeError):
        writer_mod._backup(path, backup2)
    assert not os.path.exists(backup2), "写盘中断不得留半截 .bak(atomic_write 失败即无目标文件)"
    assert _text(backup) == _text(path), "已存在的旧备份在中断场景保持原样(不被截断)"


def test_preview_tree_does_not_create_backup(tmp_path):
    """预览不产生任何备份文件(备份只属于真实写盘路径)"""
    path = _make(tmp_path, BASE)
    old = load_config(path)
    tree = read_tree(path)
    tree["config"]["main_tick"] = "8s"
    preview_tree(path, tree, old)
    assert not os.path.exists(_bak(tmp_path))
    assert not (tmp_path / "config.yml.bak").exists()


# ---------------------------------------------------------------- 预览


def test_preview_tree_does_not_touch_disk(tmp_path):
    """预览不落盘; 内容含将写入的新值与已有注释"""
    path = _make(tmp_path, "config:\n  schema_version: 4\n  # 注释\n  main_tick: 2s\n  qbittorrent:\n    host: h\n")
    before = _text(path)
    old = load_config(path)
    tree = read_tree(path)
    tree["config"]["main_tick"] = "9s"
    text = preview_tree(path, tree, old)

    assert _text(path) == before, "预览不得改动磁盘"
    assert "9s" in text
    assert "# 注释" in text


def test_preview_tree_invalid_raises(tmp_path):
    """预览与保存共用校验: 非法配置同样抛 ConfigError"""
    path = _make(tmp_path, BASE)
    tree = read_tree(path)
    tree["config"]["main_tick"] = "oops"
    with pytest.raises(ConfigError):
        preview_tree(path, tree, load_config(path))


# ---------------------------------------------------------------- 敏感字段掩码


def test_mask_tree_hides_sensitive_scalars():
    """掩码只作用于 dict 内非空标量: 密码/passkey/token 类键被替换, 空值与普通键原样返回

    空值不掩码是刻意的 —— 空密码掩码后前端会以为"已设置密码", 反而误导。
    """
    from auto_qb.config.writer import MASK_SENTINEL, mask_tree

    tree = {
        "config":
            {
                "qbittorrent": {
                    "host": "h",
                    "username": "u",
                    "password": "p"
                },
                "web": {
                    "token": "",
                    "enabled": "true"
                },
            }
    }
    masked = mask_tree(tree)
    assert masked["config"]["qbittorrent"]["password"] == MASK_SENTINEL
    assert masked["config"]["qbittorrent"]["host"] == "h", "非敏感键不得被动到"
    assert masked["config"]["web"]["token"] == "", "空值不掩码(否则前端以为已设置)"
    assert tree["config"]["qbittorrent"]["password"] == "p", "掩码不得就地修改原树"


def test_unmask_tree_restores_from_disk(tmp_path):
    """提交树里的哨兵按磁盘旧值还原: 前端"没改密码"地原样保存不会把密码写成占位串

    这是掩码能否成立的关键 —— 只掩码不还原的话, 一次保存就会毁掉生产配置里的 qB 密码。
    """
    from auto_qb.config.writer import MASK_SENTINEL, mask_tree, unmask_tree

    path = _make(tmp_path, BASE)
    old = read_tree(path)
    submitted = mask_tree(old)
    assert submitted["config"]["qbittorrent"]["password"] == MASK_SENTINEL, "前置: GET 侧确实掩码了"

    submitted["config"]["main_tick"] = "5s"  # 模拟用户只改了一个无关字段
    unmask_tree(submitted, old)
    assert submitted["config"]["qbittorrent"]["password"] == "p", "哨兵应还原为磁盘旧值"

    write_tree(path, submitted, load_config(path), _bak(tmp_path))
    text = _text(path)
    assert "password: p" in text, f"未改密码不应被写成占位串: {text}"
    assert "5s" in text, "真正改动的字段仍应写回"


def test_write_tree_stamps_schema_version(tmp_path):
    """写回侧打标(计划 26-09-26-0506): WebUI 保存后 config.schema_version 盖成当前版本(int, 无引号)"""
    path = _make(tmp_path, BASE + "  main_tick: 2s\n")
    old = load_config(path)
    tree = read_tree(path)
    tree["config"]["main_tick"] = "3s"
    write_tree(path, tree, old, _bak(tmp_path))

    text = _text(path)
    assert "schema_version: 4" in text, "写回必须带当前版本章"
    assert "'1'" not in text, "版本章必须是 int —— 盖成字符串会被 ruamel 写成带引号的 '1'"


def test_preview_tree_stamps_schema_version(tmp_path):
    """预览与写入同口径: preview_tree 同样带版本章(UI 看到的 = 将写出的)"""
    path = _make(tmp_path, BASE)
    old = load_config(path)
    tree = read_tree(path)
    text = preview_tree(path, tree, old)
    assert "schema_version: 4" in text


# ------------------------------------------------- 写回版本闸门 + 启动物化(计划 26-09-27-2252)

# schema v1 存量形态(BTSchool 旧键未迁移, 无版本章), 与 test_hr_config.test_legacy_equivalent_migration
# 的生产锚点同构 —— 程序升级前打开的页签 GET 到的就是这棵树
LEGACY_V1 = (
    "config:\n"
    "  qbittorrent:\n"
    "    host: h\n"
    "    port: 1\n"
    "    username: u\n"
    "    password: p\n"
    "  trackers:\n"
    "    BTSchool:\n"
    "      domains: [pt.btschool.club]\n"
    "      hr:\n"
    "        required_seeding_time: 3D\n"
    "      hr_check:\n"
    "        mode: partial\n"
    "        adapter: nexusphp\n"
    "        hr_page_url: https://pt.btschool.club/myhr.php\n"
    "        refresh_interval: 6H\n"
)


def test_write_tree_rejects_stale_version_tree(tmp_path):
    """版本闸门(用户裁决): 提交树版本低于当前(含缺失)直接拒绝 —— 不迁移不修补, 磁盘一字不动。

    静默把用户没见过的结构写进磁盘等于替用户做主; 拒绝并指路刷新, 未保存改动由用户取舍。
    程序升级前打开的页签 GET 到的树没有版本章(物化前磁盘无此键), 显式 v1 章同样算落后。
    """
    path = _make(tmp_path, LEGACY_V1)
    stale = read_tree(path)  # 页签在升级前 GET: 树无版本章
    stale["config"]["main_tick"] = "5s"  # 即便用户真改了字段也照拒(改动随刷新丢弃, 报错文案已提示)
    with pytest.raises(ConfigError) as ei:
        write_tree(path, stale, load_config(path), _bak(tmp_path))
    assert "刷新" in str(ei.value)
    assert _text(path) == LEGACY_V1, "拒绝写盘, 磁盘一字不动"
    assert not os.path.exists(_bak(tmp_path)), "备份也不产生(写盘动作根本没发生)"

    stamped_text = LEGACY_V1 + "  schema_version: 1\n"  # 显式 v1 章同样算落后
    stamped = _make(tmp_path, stamped_text)
    with pytest.raises(ConfigError):
        write_tree(stamped, read_tree(stamped), load_config(stamped), _bak(tmp_path))
    assert _text(stamped) == stamped_text


def test_write_tree_rejects_v2_tree_with_legacy_key(tmp_path):
    """已盖当前版本章仍带旧键(手改版本号/事故残留): 写盘前校验报废除错, 磁盘一字不动 —— 不设常驻
    兼容层, 迁移链只在版本推进时运行"""
    old = load_config(_make(tmp_path, BASE))
    corrupt = LEGACY_V1 + "  schema_version: 4\n"
    path = _make(tmp_path, corrupt)  # 同名路径覆写为「当前版本章 + 旧键」的事故残留形态
    tree = read_tree(path)

    with pytest.raises(ConfigError) as ei:
        write_tree(path, tree, old, _bak(tmp_path))
    assert "废除" in str(ei.value)
    assert _text(path) == corrupt, "拒绝写盘, 磁盘一字不动"
    assert not os.path.exists(_bak(tmp_path)), "备份也不产生(写盘动作根本没发生)"


def test_preview_tree_rejects_stale_version_tree(tmp_path):
    """预览与保存同口径: 旧版树在预览阶段就被闸门拦截(UI 看不到迁移后的预览)"""
    path = _make(tmp_path, LEGACY_V1)
    with pytest.raises(ConfigError):
        preview_tree(path, read_tree(path), load_config(path))
    assert _text(path) == LEGACY_V1


def test_materialize_migrates_and_backups(tmp_path):
    """启动物化: v1 磁盘 -> 版本号备份(迁移前原样) + 磁盘落成当前版本新结构 + 返回 desc 与路径"""
    data_dir = tmp_path / "data"
    path = _make(tmp_path, LEGACY_V1)

    desc, backup = materialize_schema_migration(path, str(data_dir))

    assert desc == "v1→v4"
    assert backup == str(data_dir / "config.yml.v1.bak")
    with open(backup, encoding="utf-8") as f:
        assert f.read() == LEGACY_V1, "备份 = 迁移前原样(字节级)"
    text = _text(path)
    assert "schema_version: 4" in text, "磁盘落当前版本章"
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
    assert desc == "v1→v4"
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

    assert desc == "v1→v4"
    text = _text(path)
    assert "hr_check" not in text, "陌生 host 的旧键随 v3 迁移删除"
    cfg = load_config(path)
    assert cfg.trackers["BTSchool"].hr_check is None


def test_materialize_dry_run_probe(tmp_path):
    """write=False(dry-run 探测): 只报 desc, 不校验不备份不落盘 —— 与 state 迁移同口径"""
    data_dir = tmp_path / "data"
    path = _make(tmp_path, LEGACY_V1)

    desc, backup = materialize_schema_migration(path, str(data_dir), write=False)

    assert desc == "v1→v4" and backup == ""
    assert _text(path) == LEGACY_V1, "dry-run 不落盘"
    assert not data_dir.exists()


def test_materialize_missing_file_returns_empty(tmp_path):
    """配置文件不存在(测试/非常规构造直接注入配置): 无事可做, 原样返回 ("", "") 且零 IO"""
    data_dir = tmp_path / "data"
    assert materialize_schema_migration(str(tmp_path / "nope.yml"), str(data_dir)) == ("", "")
    assert not data_dir.exists()


def test_collect_explicit_empty_paths_all_trackers():
    """v3→v4 显式置空收集: 非 dict 的 tracker 条目不得中断后续收集(continue 而非 break)"""
    from auto_qb.config.migrations import _collect_explicit_empty_paths

    cfg = {
        "remove_similar_tags": "",
        "trackers":
            {
                "Bad": "oops",  # 非 dict: 跳过它, 但不得中断后续 tracker 的收集
                "T1": {
                    "remove_similar_tags": "",
                    "hr": {
                        "add_tag": ""
                    }
                },
            },
    }
    paths = _collect_explicit_empty_paths(cfg)
    assert "config.remove_similar_tags" in paths, paths
    assert "config.trackers.T1.remove_similar_tags" in paths, paths
    assert "config.trackers.T1.hr.add_tag" in paths, paths


def test_unmask_tree_restores_nested_and_toplevel():
    """哨兵还原须遍历整棵树: 嵌套分支命中后不得中断顶层遍历(continue 而非 break)"""
    from auto_qb.config.writer import MASK_SENTINEL, unmask_tree

    tree = {"qbittorrent": {"password": MASK_SENTINEL}, "token": MASK_SENTINEL}
    old = {"qbittorrent": {"password": "p"}, "token": "t"}
    unmask_tree(tree, old)
    assert tree["qbittorrent"]["password"] == "p", "嵌套分支应还原"
    assert tree["token"] == "t", "嵌套分支命中后, 顶层后续键仍须还原"


# ---------- T0.7 扩展: 掩码/闸门/首存 round-trip 长尾 + schema 迁移函数缺口 ----------


def test_mask_tree_non_dict_passthrough():
    """掩码只处理映射: 顶层/嵌套列表整体不动(列表项无法与磁盘旧值稳定对应)"""
    from auto_qb.config.writer import mask_tree

    assert mask_tree(["a", "b"]) == ["a", "b"]
    assert mask_tree({"config": {
        "delete_tags": ["X", "Y"],
        "web": {
            "token": "secret"
        }
    }})["config"]["delete_tags"] == ["X", "Y"]
    assert mask_tree({"config": {"web": {"token": "secret"}}})["config"]["web"]["token"] == "********"


def test_unmask_tree_guards_and_sentinel_old_value():
    """还原守卫: 非映射树原样返回; 旧值缺失/旧值本身是哨兵时保持哨兵(宁可占位不可静默清密)"""
    from auto_qb.config.writer import MASK_SENTINEL, unmask_tree

    assert unmask_tree("plain", {}) == "plain"
    tree = {"config": {"password": MASK_SENTINEL}}
    # 旧值就是哨兵: 保持不动
    out = unmask_tree(copy.deepcopy(tree), {"config": {"password": MASK_SENTINEL}})
    assert out["config"]["password"] == MASK_SENTINEL
    # 旧值缺失: 同样保持哨兵, 不静默写成空
    out = unmask_tree(copy.deepcopy(tree), {"config": {}})
    assert out["config"]["password"] == MASK_SENTINEL
    # 旧值真实存在: 回填
    out = unmask_tree(copy.deepcopy(tree), {"config": {"password": "real"}})
    assert out["config"]["password"] == "real"


def test_stamp_schema_version_ignores_non_dict_cfg():
    """盖章只认 config 段: 树缺 config 段时静默跳过(不炸)"""
    from auto_qb.config.writer import _stamp_schema_version

    tree = {"other": 1}
    _stamp_schema_version(tree)
    assert tree == {"other": 1}


def test_reject_stale_version_non_integer_shape_passes_gate():
    """版本闸门只拦「低于当前/缺失」: 非整数形状(交给校验层报精确错)与合法当前版本原样通过"""
    from auto_qb.config.writer import _reject_stale_version

    _reject_stale_version({"config": {"schema_version": "abc"}})  # 不抛
    _reject_stale_version({"config": {"schema_version": []}})  # 不抛
    from auto_qb.infra.versioning import CURRENT_VERSIONS

    _reject_stale_version({"config": {"schema_version": str(CURRENT_VERSIONS["config"])}})  # 当前版本放行


def test_write_tree_first_save_on_missing_file(tmp_path):
    """首存: 目标配置文件尚不存在 -> 无源可备份(跳过) + round-trip 从空文档建树, 写盘成功"""
    seed_dir = tmp_path / "seed"
    seed_dir.mkdir()
    old = load_config(_make(seed_dir, BASE))
    target = str(tmp_path / "new" / "config.yml")
    tree = read_tree(str(seed_dir / "config.yml"))
    write_tree(target, tree, old, _bak(tmp_path))
    assert os.path.exists(target)
    assert "qbittorrent" in _text(target)
    assert not os.path.exists(_bak(tmp_path)), "无源文件不应产生备份"


def test_write_tree_rebuilds_doc_from_non_mapping_file(tmp_path):
    """磁盘文件是非映射 YAML(手改坏掉的纯标量) -> round-trip 以空文档重建, 配置树完整落盘"""
    seed_dir = tmp_path / "seed"
    seed_dir.mkdir()
    old = load_config(_make(seed_dir, BASE))
    path = _make(tmp_path, "123\n")
    tree = read_tree(path)  # 非映射 -> 空 config 段
    tree["config"]["qbittorrent"] = {"host": "h", "port": "1", "username": "u", "password": "p"}
    tree["config"]["schema_version"] = "4"
    write_tree(path, tree, old, _bak(tmp_path))
    text = _text(path)
    assert "123" not in text, "旧的非映射内容被整体重建"
    assert "qbittorrent" in text and "schema_version: 4" in text
    loaded = load_config(path)
    assert loaded.qbittorrent.host == "h"


def test_write_tree_roundtrip_list_of_dicts_and_plain_int(tmp_path):
    """列表内映射逐项按 BaseLoader 语义比较(值未变整体跳过); 变更的纯数字字符串按原生标量写出"""
    path = _make(
        tmp_path, "config:\n"
        "  schema_version: 4\n"
        "  qbittorrent:\n"
        "    host: h\n"
        "    port: 1\n"
        "    username: u\n"
        "    password: p\n"
        "  notify:\n"
        "    channels:\n"
        "      - platform: {}\n"
        "  web:\n"
        "    port: 8080\n"
    )
    old = load_config(path)
    tree = read_tree(path)
    tree["config"]["web"]["port"] = "9999"  # 纯数字字符串 -> 原生 int(421)
    write_tree(path, tree, old, _bak(tmp_path))
    text = _text(path)
    assert "port: 9999" in text, "纯数字字符串应写成原生标量(无引号)"
    assert "platform" in text, "未变化的映射列表应整体保留"
    assert load_config(path).web.port == 9999


def test_materialize_bad_version_wraps_config_error(tmp_path):
    """磁盘 schema_version 形状非法 -> SchemaVersionError 包装为 ConfigError(报清文件与原因)"""
    data_dir = tmp_path / "data"
    path = _make(tmp_path, BASE.replace("schema_version: 4", "schema_version: abc"))
    with pytest.raises(ConfigError, match="schema 版本问题"):
        materialize_schema_migration(path, str(data_dir))
    assert not data_dir.exists(), "探测阶段失败不应产生备份目录"


# ---------- schema 迁移函数缺口(_url_host / v1→v2 改写 / v2→v3 sites 清理) ----------


def test_url_host_shapes():
    """host 提取: 非串/解析失败 -> 空串(定位不到档案, 旧键原地保留); 正常 URL 小写化"""
    from auto_qb.config.migrations import _url_host

    assert _url_host(None) == ""
    assert _url_host(123) == ""
    assert _url_host("http://[::1/x") == "", "畸形 IPv6 -> ValueError -> 空串"
    assert _url_host("https://PT.BTSchool.club/myhr.php") == "pt.btschool.club"


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


def test_write_tree_backup_relative_path(tmp_path, monkeypatch):
    """备份路径无父目录(dirname 为空) -> 跳过 makedirs, 备份仍产生在 CWD 且内容 = 写盘前原样"""
    path = _make(tmp_path, BASE)
    monkeypatch.chdir(tmp_path)
    tree = read_tree(path)
    tree["config"]["web"] = {"port": "38080"}
    write_tree(path, tree, load_config(path), "config.yml.bak")
    with open("config.yml.bak", "r", encoding="utf-8") as f:
        assert f.read() == BASE, "备份 = 写盘前的旧内容"


def test_path_helpers_mid_node_shapes():
    """_set_path / _delete_path 的形状防御(纯函数直测): 中途节点非 dict 时 set 重建、delete 静默返回;
    单段路径打在非映射树上 delete 也是安全空转 —— R 级回退对烂形状的容错底座"""
    from auto_qb.config.writer import _delete_path, _set_path

    # set: 中途节点是标量 -> 整体替换为新 dict 再落值
    tree = {"config": {"web": "junk"}}
    _set_path(tree, ["config", "web", "port"], "123")
    assert tree["config"]["web"] == {"port": "123"}

    # set: 中途节点缺失 -> 现场建 dict
    tree = {"config": {}}
    _set_path(tree, ["config", "fs", "path_map"], [{"from": "a", "to": "b"}])
    assert tree["config"]["fs"]["path_map"] == [{"from": "a", "to": "b"}]

    # delete: 中途节点是标量 -> 无处可删, 原样返回不炸
    tree = {"config": {"web": "junk"}}
    _delete_path(tree, ["config", "web", "port"])
    assert tree["config"]["web"] == "junk"

    # delete: 中途节点缺失 -> 同样静默返回
    tree = {"config": {}}
    _delete_path(tree, ["config", "fs", "path_map"])
    assert tree == {"config": {}}

    # delete: 路径本身只有一段且树非映射 -> 循环零圈, 树不是 dict 则跳过 pop
    _delete_path("plain", ["config"])
    tree = {"config": {"a": 1}}
    _delete_path(tree, ["config", "a"])
    assert tree == {"config": {}}, "正常单段删除: 键被移除"


# ---------- v3→v4: 9 键作用域显式置空移除(report 26-10-03-0504 方案 B 阶段 1) ----------

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

# v4 形态: 站点 '' = 覆盖为空(合法稀疏条目, 迁移不得误杀)
V4_SITE_EMPTY = (
    "config:\n"
    "  schema_version: 4\n"
    "  hr:\n"
    "    add_tag: zGlobal\n"
    "  trackers:\n"
    "    A:\n"
    "      domains: [a.com]\n"
    "      hr:\n"
    "        required_seeding_time: 3D\n"
    "        add_tag: ''\n"
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
    """v3 文件物化: 作用域内 '' 移除并落盘 v4, 每个被移除键一条 WARNING(用户拍板: 日志必须可见)"""
    import logging

    data_dir = tmp_path / "data"
    path = _make(tmp_path, V3_WITH_EMPTIES)

    with caplog.at_level(logging.WARNING, logger="auto_qb.config.loaders"):
        desc, backup = materialize_schema_migration(path, str(data_dir))

    assert desc == "v3→v4"
    assert backup == str(data_dir / "config.yml.v3.bak")
    text = _text(path)
    assert "schema_version: 4" in text
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
    """v4 文件的站点 '' = 覆盖为空(合法保留): 物化零 IO 不误杀, 加载后生效值 = ''"""
    data_dir = tmp_path / "data"
    path = _make(tmp_path, V4_SITE_EMPTY)

    assert materialize_schema_migration(path, str(data_dir)) == ("", ""), "已是当前版本: 零 IO"
    assert _text(path) == V4_SITE_EMPTY, "v4 的站点 '' 不得被迁移移除"
    cfg = load_config(path)
    assert cfg.trackers["A"].hr.add_tag == "", "覆盖为空生效(不回退全局 zGlobal)"
    assert cfg.hr.add_tag == "zGlobal"


def test_write_tree_roundtrip_preserves_site_explicit_empty(tmp_path):
    """ruamel round-trip 保留站点 ''(report 26-10-03-0504 待核实项①实测): 写盘 -> 读回仍为 ''

    write_tree -> ruamel dump 把 '' 写成带引号标量(add_tag: ''), BaseLoader 读回 '' ——
    「覆盖为空」这一稀疏条目在写盘链路无损, WebUI 保存不会把它洗成键缺失。
    """
    path = _make(tmp_path, V4_SITE_EMPTY)
    old = load_config(path)
    tree = read_tree(path)
    tree["config"]["trackers"]["A"]["hr"]["add_category"] = ""  # 新增的站点显式空
    write_tree(path, tree, old, _bak(tmp_path))

    text = _text(path)
    assert "add_tag: ''" in text, f"已有站点 '' 应原样保留: {text}"
    assert "add_category: ''" in text, f"新增站点 '' 应写为带引号空串: {text}"
    loaded = load_config(path)
    assert loaded.trackers["A"].hr.add_tag == "" and loaded.trackers["A"].hr.add_category == ""


# ---------- 长尾守阵: 回退/掩码/round-trip/格式判定(issue 26-10-08-0903-test-config-mutation-writer-tail) ----------
# 背景: 变异审计确认 writer.py 有 74 条「全套件杀不掉」的真洞候选, 集中在回退(_fallback_*)、
# 掩码还原(unmask_tree)、round-trip 比较(_same_value/_as_builtin/_sync_mapping)、格式判定
# (_plain_scalar)与内部写盘细节(_validate_tree/_build_yaml/_build_doc)上。以下用例按函数簇补齐.


def test_stamp_schema_version_uses_root_key_and_overwrites():
    """盖章必须**读 ROOT_KEY 段**(不是硬编码 None)且**无条件覆盖**旧版本值

    _stamp_schema_version 的两条同构变异: ①`cfg = tree.get(ROOT_KEY)` 改成 `tree.get(None)`
    ②整句删掉 —— 前者让 cfg 恒为 None 从而静默不盖章, 后者同理。守阵: 用缺 config 段的树
    (跳过)与带旧版本的 config 段(必须被改成当前版本)两侧夹住。
    """
    from auto_qb.config.writer import _stamp_schema_version
    from auto_qb.infra.versioning import CURRENT_VERSIONS

    current = CURRENT_VERSIONS["config"]

    # 正侧: config 段存在且版本落后 -> 必须被盖成当前版本(int)
    tree = {"config": {"schema_version": 1, "x": "1"}}
    _stamp_schema_version(tree)
    assert tree["config"]["schema_version"] == current, "必须按 ROOT_KEY 取到 config 段并覆盖旧版本"
    assert isinstance(tree["config"]["schema_version"], int), "盖章必须是 int, 不能是字符串"

    # 反侧: 根键不是 ROOT_KEY(如 "cfg") -> 不得误盖到 `tree[None]`, 也不得凭空造 config 段
    other = {"cfg": {"schema_version": 1}}
    _stamp_schema_version(other)
    assert other == {"cfg": {"schema_version": 1}}, "根键不是 config 时静默跳过, 不得改别的段"


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
    assert desc == "v1→v4"
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


def test_prepare_passes_old_tree_to_restart_fallback(tmp_path, monkeypatch):
    """_prepare 调 R 级回退时 old_tree 必须来自 read_tree(**不是 None**)

    变异把 `_fallback_restart_fields(tree, old_tree, ...)` 的第二实参改成 None —— 回退就再也读不到
    磁盘旧值。守阵: 用 spy 验证收到的 old_tree 含磁盘真实段值(而不是被换成的 None).
    """
    from auto_qb.config import writer as writer_mod

    path = _make(tmp_path, BASE + "  data_dir: disk-dir\n")
    old_config = load_config(path)
    tree = read_tree(path)
    tree["config"]["data_dir"] = "ui-dir"
    seen = []
    real = writer_mod._fallback_restart_fields

    def spy(t, old_tree, changes):
        seen.append(old_tree)
        return real(t, old_tree, changes)

    monkeypatch.setattr(writer_mod, "_fallback_restart_fields", spy)
    writer_mod._prepare(path, tree, old_config)
    assert seen, "命中 R 闸时必须调用 R 级回退"
    assert seen[0]["config"]["data_dir"] == "disk-dir", "R 级回退必须拿到磁盘旧树(传 None 会回退失败)"


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


def test_validate_tree_temp_file_roundtrip(tmp_path, monkeypatch):
    """_validate_tree: 落临时文件 + load_config 校验 + **finally 清理**

    变异簇集中在 tempfile 参数(encoding/suffix/delete)与 yaml.dump 关键参数 — 这条用「校验
    正例返回 Config」+「临时文件被清理」两段夹住最核心的 delete=False 契约: delete=True 时
    文件在 with 退出即被删, 后续 load_config 无从读; 而 finally 里的 `and os.path.exists` 若被
    改成 `or`, 空 tmp_path 分支会误删。
    """
    from auto_qb.config import writer as writer_mod

    tmp_path_dir = tmp_path / "tmpdir"
    tmp_path_dir.mkdir()
    monkeypatch.setenv("TMPDIR", str(tmp_path_dir))
    monkeypatch.setenv("TEMP", str(tmp_path_dir))
    monkeypatch.setenv("TMP", str(tmp_path_dir))

    tree = read_tree(_make(tmp_path, BASE + "  main_tick: 2s\n"))
    cfg = writer_mod._validate_tree(tree)
    assert cfg.main_tick == 2.0, "校验必须走到 load_config 拿到解析结果(临时文件须在 dumps 后可读)"
    assert list(tmp_path_dir.iterdir()) == [], "校验后临时文件必须被 finally 清理"

    # 校验失败路径: 同样必须清理临时文件(不留垃圾)
    bad = {"config": {"main_tick": "abc"}}
    with pytest.raises(ConfigError):
        writer_mod._validate_tree(bad)
    assert list(tmp_path_dir.iterdir()) == [], "校验失败后临时文件也必须清理"


def test_validate_tree_finally_guard_skips_none_tmp_path(tmp_path, monkeypatch):
    """_validate_tree 的 finally 守卫必须是 `tmp_path and os.path.exists(...)` 的**短路与**

    变异把 `and` 写成 `or`: 临时文件创建失败(NamedTemporaryFile 抛)时 tmp_path 仍是 None,
    `None or os.path.exists(None)` 会去 stat(None) 抛 TypeError, 把原始 OSError 掩盖成
    TypeError —— 调用方看到的是"类型错误"而非真实原因(磁盘不可写/临时目录缺失).
    守阵: 让临时文件创建失败, 断言原始 OSError 原样冒出(不变成 TypeError), 且守卫不误删.
    """
    from unittest import mock

    from auto_qb.config import writer as writer_mod

    with mock.patch("tempfile.NamedTemporaryFile", side_effect=OSError("tempdir 不可写")):
        with pytest.raises(OSError) as ei:
            writer_mod._validate_tree({"config": {}})
    assert "tempdir 不可写" in str(ei.value), "原始 OSError 必须原样冒出(and 写坏成 or 会变 TypeError)"

    # 正常路径: 文件被创建 -> 守卫仍须清理(and 的两侧都要生效)
    from auto_qb.config import writer as w2

    tmp_dir = tmp_path / "t2"
    tmp_dir.mkdir()
    monkeypatch.setenv("TMPDIR", str(tmp_dir))
    monkeypatch.setenv("TEMP", str(tmp_dir))
    monkeypatch.setenv("TMP", str(tmp_dir))
    w2._validate_tree(read_tree(_make(tmp_path, BASE + "  main_tick: 2s\n")))
    assert list(tmp_dir.iterdir()) == [], "临时文件必须被清理(守卫右侧须生效)"


def test_build_yaml_preserves_quotes_and_indent_profile():
    """_build_yaml 的三项配置必须是项目 YAML 风格(引号保留 + 4/4/2 缩进)

    变异簇把 preserve_quotes 改成 None/False、indent 的 mapping/sequence/offset 改值或删参 —
    这些只改格式不改语义, 但正是「写回后文件可读性」的守阵面。直接断言 ruamel 实例属性。
    """
    from auto_qb.config.writer import _build_yaml

    ry = _build_yaml()
    assert ry.preserve_quotes is True, "必须保留磁盘原有引号形态"
    assert ry.map_indent == 4, "映射缩进 4(与原 config.yml 风格一致)"
    assert ry.sequence_indent == 4, "序列缩进 4"
    assert ry.sequence_dash_offset == 2, "序列破折号偏移 2"


def test_build_doc_reads_existing_and_falls_back_to_empty(tmp_path):
    """_build_doc: 已存在文件读为 CommentedMap; 非映射/不存在 -> 以空文档重建

    变异把 `doc = None` 改成 `doc = ""`(初始值形状)或把 open 的 `"r"` 删掉 —— 前者在
    「文件不存在」时 `isinstance(doc, dict)` 仍为 False 从而走 {} 分支(看似无害, 实则丢了
    None 哨兵语义); 这条直接覆盖两条路径的行为契约.
    """
    from auto_qb.config.writer import _build_doc

    path = _make(tmp_path, "config:\n    web:\n        # 注释\n        port: 1\n")
    doc = _build_doc(path, {"config": {"web": {"port": "2"}}})
    assert isinstance(doc, dict)
    assert doc["config"]["web"]["port"] == 2, "树的值须同步进文档"

    # 文件不存在 -> 从空文档建起, 树内容仍完整同步
    missing = str(tmp_path / "nope.yml")
    doc2 = _build_doc(missing, {"config": {"web": {"port": "3"}}})
    assert isinstance(doc2, dict) and doc2["config"]["web"]["port"] == 3

    # 磁盘是非映射 YAML -> 以空文档重建
    np = _make(tmp_path, "- a\n- b\n")
    doc3 = _build_doc(np, {"config": {"web": {"port": "4"}}})
    assert isinstance(doc3, dict) and doc3["config"]["web"]["port"] == 4


def test_fallback_helpers_split_dot_paths_and_rebuild_missing_nodes(tmp_path):
    """R 级/readonly 回退必须按 `.` 正确切分点路径并重建中途节点

    变异簇: `.split(".")` 改 `.split(None)`/`"XX.XX"`(切分错 → 找不到旧值); `_set_path` 的
    `node.get(p)` 改 None/get(None)(中途节点被无视 → 结构写错位). 这条用「磁盘有旧值须覆盖」
    +「磁盘无旧值须删除」两侧夹住.
    """
    from auto_qb.config.impact import ConfigChange
    from auto_qb.config.writer import _fallback_restart_fields

    # 磁盘旧值存在(嵌套路径 state_file 在 config 段下) -> 提交树的新值被覆盖为旧值
    old_tree = {"config": {"state_file": "old-state.json", "nested": {"x": "old"}}}
    tree = {"config": {"state_file": "new-state.json", "nested": {"x": "new"}}}
    changes = [
        ConfigChange(path="state_file", old="old-state.json", new="new-state.json"),
        ConfigChange(path="nested.x", old="old", new="new"),
    ]
    _fallback_restart_fields(tree, old_tree, changes)
    assert tree["config"]["state_file"] == "old-state.json", "点路径切分正确才能取到旧值"
    assert tree["config"]["nested"]["x"] == "old", "嵌套点路径须正确切分并覆盖"

    # 磁盘无旧值 -> 键须被删除(走默认值), 不得把 None 写进去
    tree2 = {"config": {"data_dir": "ui-dir"}}
    _fallback_restart_fields(tree2, {"config": {}}, [ConfigChange(path="data_dir", old=None, new="ui-dir")])
    assert "data_dir" not in tree2["config"], "磁盘未配置的 R 级键须删除, 不是写成 None"


def test_fallback_readonly_skips_version_key_but_covers_others():
    """readonly 回退必须**跳过 schema_version**、**continue 而非 break**、按点路径处理其余键

    三条同构变异: ①`path == VERSION_KEY` 改 `!=`(全部跳过) ②`continue` 改 `break`(命中版本键后
    整轮中断, 后面的 readonly 键再也不回退) ③split(".") 改错. 守阵: 磁盘对 data_dir/fs 有旧值,
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


def test_delete_path_removes_last_segment_only():
    """_delete_path 必须删**最后一段**(变异把 parts[-1] 改成 parts[+1] → IndexError/删错键)"""
    from auto_qb.config.writer import _delete_path

    tree = {"config": {"a": "1", "b": "2"}}
    _delete_path(tree, ["config", "a"])
    assert tree == {"config": {"b": "2"}}, "须精确删除目标键, 不动兄弟键"

    # 单段路径: parts[-1] == parts[0], 同样必须命中
    tree2 = {"only": "1"}
    _delete_path(tree2, ["only"])
    assert tree2 == {}

    # 末段不存在: 静默无操作(不抛)
    _delete_path({"config": {}}, ["config", "ghost"])


def test_sync_mapping_skips_unchanged_scalar_and_list_nodes():
    """_sync_mapping「值未变则不动原节点」必须对**标量与列表**都成立

    变异簇把 _same_value 的两侧实参换成 None、或把 `not isinstance(...)` 的 and 链写坏 —— 后果是
    「未修改的节点被重写」, 表现为磁盘上的引号/注释形态漂移。守阵: 用带引号标量与列表两类节点
    夹住「未变保持原对象」这个契约(注释保留是它的可观测副作用).
    """
    from ruamel.yaml.comments import CommentedMap

    from auto_qb.config.writer import _sync_mapping

    doc = CommentedMap()
    doc["port"] = "16585"  # 磁盘原标量(ruamel 读作 str, 因为引号形态)
    doc.yaml_set_comment_before_after_key("port", before="keep-me", after="tail")
    doc["tags"] = ["A", "B"]
    port_node = doc["port"]
    tags_node = doc["tags"]

    # 树里的值与磁盘同构(标量字符串一致 / 列表项一致) -> 必须跳过赋值, 原节点不动
    _sync_mapping(doc, {"port": "16585", "tags": ["A", "B"]})
    assert doc["port"] is port_node, "未变化的标量不得被替换(否则注释/引号形态被重写)"
    assert doc["tags"] is tags_node, "未变化的列表不得被替换"
    assert doc.get("port") == "16585"

    # 值真变了 -> 替换
    _sync_mapping(doc, {"port": "999", "tags": ["C"]})
    assert doc["port"] == 999 or doc["port"] == "999"
    assert list(doc["tags"]) == ["C"]

    # 树里缺失的键 -> 从磁盘删除
    _sync_mapping(doc, {})
    assert "port" not in doc and "tags" not in doc


def test_sync_mapping_scalar_vs_container_not_skipped():
    """_sync_mapping 的类型分派: `not isinstance(value, (dict, list)) and not isinstance(existing, ...)`
    的 and 链不得被写坏(变异把两侧 not 去掉/换 or → 标量与容器互转时误跳过或误比较)

    守阵: ①标量值覆盖容器节点 ②容器值覆盖标量节点 —— 两种都不得被"未变化"逻辑吞掉.
    """
    from ruamel.yaml.comments import CommentedMap

    from auto_qb.config.writer import _sync_mapping

    # 标量 -> 覆盖磁盘上的 dict 节点
    doc = CommentedMap()
    doc["x"] = CommentedMap()
    doc["x"]["old"] = "1"
    _sync_mapping(doc, {"x": "scalar"})
    assert doc["x"] == "scalar", "标量须能覆盖原容器节点(类型不同不得误判为未变)"

    # dict -> 覆盖磁盘上的标量节点
    doc2 = CommentedMap()
    doc2["y"] = "plain"
    _sync_mapping(doc2, {"y": {"k": "v"}})
    assert isinstance(doc2["y"], dict) and doc2["y"]["k"] == "v", "容器须能覆盖原标量节点"


def test_same_value_none_and_as_builtin_semantics():
    """_same_value/_as_builtin 的 BaseLoader 语义(变异把两侧实参换 None / 布尔小写化写坏)

    - `existing is None` -> False(空节点不算「未变化」)
    - 布尔统一小写字符串; None -> ""; 数字 -> str; 容器递归
    """
    from auto_qb.config.writer import _as_builtin, _same_value

    assert _same_value(None, "x") is False, "existing 为 None 必须判为「有变化」"
    assert _same_value("true", True) is True, "字符串 true 与 bool True 在 BaseLoader 语义下同值"
    assert _same_value("16585", 16585) is True
    assert _same_value("1", "2") is False

    assert _as_builtin(True) == "true" and _as_builtin(False) == "false", "布尔须小写字符串化"
    assert _as_builtin(None) == "", "None -> 空串"
    assert _as_builtin(7) == "7", "数字 -> 字符串"
    assert _as_builtin({"a": True}) == {"a": "true"}, "映射递归且键字符串化"
    assert _as_builtin([1, False]) == ["1", "false"], "列表递归"


def test_plain_scalar_bool_and_lossless_rules():
    """_plain_scalar: 布尔识别大小写无关且**信息无损**才转换

    变异把 `low` 改成 `hi`/`FALSE` —— 「FALSE」将不再被识别为布尔, 写回时形态漂移。守阵覆盖
    大小写两侧 + 有损数字串(007/1.10)必须保持字符串.
    """
    from auto_qb.config.writer import _plain_scalar

    assert _plain_scalar("true") is True
    assert _plain_scalar("TRUE") is True, "布尔识别须大小写无关"
    assert _plain_scalar("False") is False
    assert _plain_scalar("FALSE") is False, "布尔识别须大小写无关(小写化后再判定)"
    assert _plain_scalar("16585") == 16585
    assert _plain_scalar("007") == "007", "有损(前导零)不得转换"
    assert _plain_scalar("1.10") == "1.10", "有损(尾零)不得转换"
    assert _plain_scalar({"a": ["TRUE", "1"]}) == {"a": [True, 1]}, "递归处理新子树"


def test_unmask_tree_init_and_guards():
    """unmask_tree 的入口守卫与哨兵判定(变异把 isinstance 判断/环回写坏)

    - 非映射 tree 或 old_tree -> 原样返回(不做任何写)
    - 哨兵命中但旧值缺失/旧值本身也是哨兵 -> 保持哨兵(不静默清空密码)
    """
    from auto_qb.config.writer import MASK_SENTINEL, unmask_tree

    assert unmask_tree("plain", {"config": {}}) == "plain", "非映射 tree 原样返回"
    assert unmask_tree({"config": {}}, "plain") == {"config": {}}, "非映射 old_tree 原样返回"

    # 哨兵 + 旧值也是哨兵 -> 保持(宁可占位)
    t = {"config": {"password": MASK_SENTINEL}}
    out = unmask_tree(copy.deepcopy(t), {"config": {"password": MASK_SENTINEL}})
    assert out["config"]["password"] == MASK_SENTINEL
    # 哨兵 + 旧值缺失 -> 保持
    out2 = unmask_tree(copy.deepcopy(t), {"config": {}})
    assert out2["config"]["password"] == MASK_SENTINEL
    # 哨兵 + 有真实旧值 -> 回填
    out3 = unmask_tree(copy.deepcopy(t), {"config": {"password": "real"}})
    assert out3["config"]["password"] == "real"


def test_unmask_tree_only_touches_sentinel_values():
    """unmask_tree 只还原**值恰为哨兵**的键; 旧树里有值但提交值不是哨兵时不得改动

    变异把 `value == MASK_SENTINEL` 写成 `!=` 或对非哨兵值也回填 —— 后果是「用户真改了值却被
    磁盘旧值覆盖」, 这是掩码链路最危险的静默数据丢失。守阵两侧夹住。
    """
    from auto_qb.config.writer import MASK_SENTINEL, unmask_tree

    # 提交值不是哨兵(用户真改了) -> 必须保留用户新值, 不得回填旧值
    tree = {"config": {"password": "user-changed", "token": "another"}}
    old = {"config": {"password": "disk-old", "token": "disk-token"}}
    unmask_tree(tree, old)
    assert tree["config"]["password"] == "user-changed", "非哨兵值不得被磁盘旧值覆盖"
    assert tree["config"]["token"] == "another"

    # 混合: 哨兵回填, 非哨兵保持
    tree2 = {"config": {"password": MASK_SENTINEL, "token": "new-token"}}
    unmask_tree(tree2, old)
    assert tree2["config"]["password"] == "disk-old", "哨兵须回填"
    assert tree2["config"]["token"] == "new-token", "非哨兵须保持"


def test_mask_tree_recurses_into_nested_dicts():
    """mask_tree 必须递归进嵌套映射(变异把递归分支写坏 -> 深层密码明文泄露)

    守阵: 深两层的敏感键必须被掩码, 且空值不掩码(空值掩码会误导前端以为已设置).
    """
    from auto_qb.config.writer import MASK_SENTINEL, mask_tree

    tree = {
        "config":
            {
                "qbittorrent": {
                    "password": "secret",
                    "user": "u"
                },
                "web": {
                    "authkey": "k",
                    "apikey": "plain"
                },
                "trackers": {
                    "T": {
                        "passkey": "pk",
                        "cookie": "ck"
                    }
                },
                "empty_password": "",
                "nothing": None,
            }
    }
    out = mask_tree(tree)
    cfg = out["config"]
    assert cfg["qbittorrent"]["password"] == MASK_SENTINEL
    assert cfg["qbittorrent"]["user"] == "u", "非敏感键不得被掩码"
    assert cfg["web"]["authkey"] == MASK_SENTINEL, "键名含 authkey -> 掩码"
    assert cfg["web"]["apikey"] == "plain", "不含敏感词的键不得被掩码"
    assert cfg["trackers"]["T"]["passkey"] == MASK_SENTINEL, "深层敏感键须递归掩码"
    assert cfg["trackers"]["T"]["cookie"] == MASK_SENTINEL
    assert cfg["empty_password"] == "" and cfg["nothing"] is None, "空值不掩码(避免误导已设置)"
    assert tree["config"]["qbittorrent"]["password"] == "secret", "原树不得被就地修改"


def test_set_path_rebuilds_non_mapping_mid_nodes():
    """_set_path 中途节点非映射时必须**重建为 dict**(变异把 `node.get(p)` 改 None/get(None))

    前者让已存在的 dict 节点被无视而覆盖重建(丢兄弟键); 后者拿不到任何节点。守阵用 spy 语义:
    已有 dict 的中途节点须**原地复用**(兄弟键保留), 非 dict 的须重建.
    """
    from auto_qb.config.writer import _set_path

    # 中途节点已是 dict -> 原地复用, 兄弟键保留
    tree = {"config": {"web": {"port": "1", "host": "h"}}}
    _set_path(tree, ["config", "web", "port"], "2")
    assert tree["config"]["web"] == {"port": "2", "host": "h"}, "须复用已有 dict 节点(不丢兄弟键)"

    # 中途节点是标量 -> 重建为 dict
    tree2 = {"config": {"web": "junk"}}
    _set_path(tree2, ["config", "web", "port"], "3")
    assert tree2["config"]["web"] == {"port": "3"}

    # 中途节点缺失 -> 现场建 dict
    tree3 = {"config": {}}
    _set_path(tree3, ["config", "fs", "path_map"], ["x"])
    assert tree3["config"]["fs"]["path_map"] == ["x"]


def test_backup_skips_when_source_missing_and_keeps_encoding(tmp_path):
    """_backup: 源文件不存在时**直接返回**(不建任何东西); 存在时按 utf-8 读并原子写

    变异簇: `os.path.dirname` → None(父目录漏建) + open 的 `"r"` 被删 —— 前者让嵌套备份目录
    不建, 后者改变读模式语义。守阵两侧夹住。
    """
    from auto_qb.config import writer as writer_mod

    missing = str(tmp_path / "nope.yml")
    nested_backup = tmp_path / "deep" / "x.bak"
    writer_mod._backup(missing, str(nested_backup))
    assert not nested_backup.exists() and not (tmp_path / "deep").exists(), "源缺失时零副作用"

    path = _make(tmp_path, BASE)
    writer_mod._backup(path, str(nested_backup))
    assert nested_backup.exists(), "须按 dirname 建父目录并落备份"
    with open(nested_backup, encoding="utf-8") as f:
        assert f.read() == BASE

    # 非 ASCII 内容往返(验证 utf-8 读写契约)
    path2 = _make(tmp_path, BASE + "  web:\n    title: 中文标题\n")
    b2 = str(tmp_path / "deep2" / "y.bak")
    writer_mod._backup(path2, b2)
    with open(b2, encoding="utf-8") as f:
        assert "中文标题" in f.read(), "utf-8 读取须无损"
