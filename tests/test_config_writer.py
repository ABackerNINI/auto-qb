"""test_config_writer 测试计划: 配置写回(结构化树 -> 校验 -> R 级回退 -> round-trip 写盘)

## 测试计划(每个测试函数一条)
- test_read_tree_scalars_are_strings: 读出的树与 BaseLoader 语义一致(标量全为字符串)
- test_read_tree_missing_or_empty_file: 文件不存在/空/非映射 -> 空 config 段
- test_write_tree_requires_config_root: 缺少 config 根段 -> ValueError
- test_write_tree_invalid_rejected_without_touching_disk: 非法值 -> ConfigError 且磁盘不变
- test_write_tree_preserves_comments_and_plain_scalars: 写回保留注释, 未修改标量保持原书写风格
- test_write_tree_updates_existing_scalar: 修改已有键 -> 按项目风格写出(数字/布尔无引号)
- test_write_tree_adds_and_removes_keys: 新增键写入/缺失键移除
- test_write_tree_removes_empty_list: 列表被清空后键移除
- test_write_tree_restart_field_fallback: R 级字段回退为磁盘旧值并回报 restart_required
- test_write_tree_restart_field_removed_when_absent_on_disk: 磁盘未配置的 R 级字段提交后被删除(走默认值)
- test_write_tree_updates_derived_state_file: 改 data_dir 时派生的 state_file 一并回退
- test_write_tree_writes_float_and_negative_scalars_plain: 浮点字符串按原生标量写出
- test_write_tree_backup_created: 写盘前生成 `data/config.yml.bak` 备份(父目录按需创建)
- test_preview_tree_does_not_touch_disk: 预览不落盘, 且内容与写盘结果一致(除注释形态)
- test_preview_tree_invalid_raises: 预览同样做校验
- test_preview_tree_does_not_create_backup: 预览不产生任何备份文件
- test_mask_tree_hides_sensitive_scalars: 敏感键(键名含 password/passkey/token)的非空标量被掩码; 空值与普通键不受影响; 原树不被就地修改
- test_unmask_tree_restores_from_disk: 提交树里的掩码哨兵按磁盘旧值还原 —— 前端"未改密码"原样保存不会把密码写成占位串
"""
import os

import pytest

from auto_qb.config.errors import ConfigError
from auto_qb.config.loaders import load_config
from auto_qb.config.writer import preview_tree, read_tree, write_tree

BASE = "config:\n  qbittorrent:\n    host: h\n    port: 1\n    username: u\n    password: p\n"


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
    path = _make(tmp_path, "config:\n  # 注释\n  main_tick: 2s\n  qbittorrent:\n    host: h\n")
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
