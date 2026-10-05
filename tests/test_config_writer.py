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
