"""test_config_writer_write 测试计划: 配置写回(结构化树 -> 校验 -> R 级回退 -> round-trip 写盘)

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
- test_write_tree_ctx_menu_nested_round_trip: web.ctx_menu 嵌套布局(四支 × 两层 × 列表)round-trip 写盘后逐位读回, 且读树-写树二轮稳定(计划 26-10-20-0024 W1)
- test_write_tree_restart_field_fallback: R 级字段回退为磁盘旧值并回报 restart_required
- test_write_tree_restart_field_removed_when_absent_on_disk: 磁盘未配置的 R 级字段提交后被删除(走默认值)
- test_write_tree_readonly_section_fallback: readonly 段(fs, issue 26-09-28-2135)提交改值回退为磁盘旧值(schema 键面写盘防线)
- test_write_tree_readonly_section_removed_when_absent_on_disk: 磁盘未配置的 readonly 段提交后被删除(走默认值)
- test_write_tree_rejects_version_higher_than_program: 提交树版本高于程序 -> 校验层精确报错(readonly 防线不回退 schema_version, 不吞掉该错)
- test_write_tree_updates_derived_state_file: 改 data_dir 时派生的 state_file 一并回退
- test_write_tree_writes_float_and_negative_scalars_plain: 浮点字符串按原生标量写出
- test_write_tree_backup_created: 写盘前生成 `data/config.yml.bak` 备份(父目录按需创建)
- test_write_tree_concurrent_saves_serialize: 并发写盘串行化(批次4 #17) —— 两线程 barrier 后并发 write_tree, 磁盘恰好一个保存完整胜出(两标记不混合), .bak 恒为「胜出保存前」的另一保存完整结果
- test_preview_tree_does_not_touch_disk: 预览不落盘, 且内容与写盘结果一致(除注释形态)
- test_preview_tree_invalid_raises: 预览同样做校验
- test_preview_tree_does_not_create_backup: 预览不产生任何备份文件
- test_write_tree_rejects_stale_version_tree: 版本闸门(计划 26-09-27-2252 用户裁决): 提交树版本低于当前(含缺失)直接拒绝, 磁盘一字不动
- test_write_tree_rejects_v2_tree_with_legacy_key: 已盖 v2 章仍带旧键(手改/事故残留) -> 报废除错且磁盘一字不动(无常驻兼容层)
- test_preview_tree_rejects_stale_version_tree: 预览同口径被闸门拦截
- test_stamp_schema_version_ignores_non_dict_cfg: 树缺 config 段时盖章静默跳过
- test_write_tree_first_save_on_missing_file: 首存无源可备份(跳过) + 从空文档建树
- test_write_tree_rebuilds_doc_from_non_mapping_file: 磁盘文件是非映射 YAML 时以空文档重建
- test_write_tree_roundtrip_list_of_dicts_and_plain_int: 映射列表按 BaseLoader 语义比较; 数字字符串写原生标量
- test_write_tree_backup_relative_path: 备份路径无父目录 -> 跳过 makedirs 分支, 备份照常产生
- test_write_tree_roundtrip_preserves_site_explicit_empty: ruamel round-trip 保留站点 ''(report 待核实项(1)实测)
- test_stamp_schema_version_uses_root_key_and_overwrites: 盖章读 ROOT_KEY 段(非硬编码 None)且无条件覆盖旧版本; 根键非 config 时静默跳过
- test_validate_tree_temp_file_roundtrip: _validate_tree 临时文件 dumps 后可读(delete=False 契约)+ finally 清理; 失败路径同样清理
- test_validate_tree_finally_guard_skips_none_tmp_path: finally 守卫是短路与(and 写成 or 会把原始 OSError 掩盖成 stat(None) 的 TypeError)
- test_preview_tree_stamps_schema_version
- test_write_tree_keeps_lossy_numeric_strings_quoted
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
    _bak,
    _make,
    _text,
)


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


def test_write_tree_preserves_comments_and_plain_scalars(tmp_path):
    """round-trip 写盘: 已有键注释保留, 未修改标量保持原书写风格(数字/布尔不加引号)"""
    path = _make(
        tmp_path, "config:\n"
        "  schema_version: 6\n"
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


def test_write_tree_ctx_menu_nested_round_trip(tmp_path):
    """web.ctx_menu 嵌套布局(计划 26-10-20-0024 W1): 四支 × 两层 × 列表经 round-trip 写盘后
    逐位读回 —— 定制块整对象写进 cfg.tree.web.ctx_menu, 保存路径必须原样落盘不夹瘪"""
    layout = {
        "group":
            {
                "order": ["resume", "sep:d1", "delete"],
                "hidden": ["export"],
                "sub": {
                    "order": ["queue-top"],
                    "hidden": []
                }
            },
        "member": {
            "order": ["resume", "sub-more"],
            "hidden": [],
            "sub": {
                "order": ["super-seeding"],
                "hidden": []
            }
        },
    }
    path = _make(tmp_path, BASE + "  web:\n    enabled: true\n")
    old = load_config(path)
    tree = read_tree(path)
    tree["config"]["web"]["ctx_menu"] = copy.deepcopy(layout)
    write_tree(path, tree, old, _bak(tmp_path))

    text = _text(path)
    assert "ctx_menu" in text and "sep:d1" in text
    loaded = load_config(path)
    assert loaded.web.ctx_menu == layout
    # 再经读树-写树一轮(前端 PUT 语义): 仍逐位稳定
    tree2 = read_tree(path)
    write_tree(path, tree2, loaded, _bak(tmp_path))
    assert load_config(path).web.ctx_menu == layout


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
    assert read_tree(path)["config"]["schema_version"] == "6", "拒绝时磁盘一字不动"


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


def test_write_tree_concurrent_saves_serialize(tmp_path):
    """并发写盘串行化(批次4 #17): 两线程并发 write_tree, 两次保存都完整落盘且 .bak 语义不被交错破坏

    webui 的 PUT /api/config 是同步 def handler(FastAPI 线程池并发): 无锁时两个并发保存会
    交错 —— 后保存方的 .bak 可能读到前者已写入的新内容而非保存前状态(备份恢复资产退化),
    后完成的 _dump_roundtrip 整体覆盖前者(先保存方改动静默丢失)。模块级单锁串行化后可钉死的
    确定性: 恰好一次保存完整胜出(磁盘 = 其完整树), .bak = 另一方保存的完整结果(即「胜出那次
    保存前」的磁盘状态), 两侧都是可 load_config 的完整配置。两保存各改不同键
    (main_tick/sync_interval), 「混合落盘」即可检: 两标记不得同时出现在磁盘上。
    """
    import threading

    path = _make(tmp_path, BASE)
    old = load_config(path)
    tree_a = read_tree(path)
    tree_b = read_tree(path)
    tree_a["config"]["main_tick"] = "5s"
    tree_b["config"]["sync_interval"] = "7s"
    backup = _bak(tmp_path)
    errors: list = []
    barrier = threading.Barrier(2, timeout=30)

    def _save(tree):
        try:
            barrier.wait()
            write_tree(path, tree, old, backup)
        except BaseException as e:  # 线程内异常收进断言, 不静默吞掉
            errors.append(e)

    threads = [threading.Thread(target=_save, args=(t, ), name=f"save-{i}") for i, t in enumerate((tree_a, tree_b))]
    for t in threads:
        t.start()
    for t in threads:
        t.join(60)
    assert not any(t.is_alive() for t in threads), "并发保存不得挂死"
    assert not errors, f"并发保存不得抛错(交错破坏会以异常/混合内容显形): {errors}"

    # 磁盘 = 恰好一个保存方的完整树: 两标记恰中其一, 不得混合
    final = load_config(path)
    a_on_disk = final.main_tick == 5.0
    b_on_disk = final.sync_interval == 7.0
    assert a_on_disk != b_on_disk, f"整树保存必须恰好一个完整胜出, 不得混合: main_tick={final.main_tick} sync_interval={final.sync_interval}"
    # .bak = 胜出方的上一次保存结果(即另一方的完整树), 不是交错半途状态
    bak = load_config(backup)
    assert (bak.sync_interval == 7.0) == a_on_disk and (bak.main_tick == 5.0) == b_on_disk, \
        f".bak 语义被交错破坏: 应为「胜出保存前」的完整状态, 实际 main_tick={bak.main_tick} sync_interval={bak.sync_interval}"


def test_preview_tree_does_not_create_backup(tmp_path):
    """预览不产生任何备份文件(备份只属于真实写盘路径)"""
    path = _make(tmp_path, BASE)
    old = load_config(path)
    tree = read_tree(path)
    tree["config"]["main_tick"] = "8s"
    preview_tree(path, tree, old)
    assert not os.path.exists(_bak(tmp_path))
    assert not (tmp_path / "config.yml.bak").exists()


def test_preview_tree_does_not_touch_disk(tmp_path):
    """预览不落盘; 内容含将写入的新值与已有注释"""
    path = _make(tmp_path, "config:\n  schema_version: 6\n  # 注释\n  main_tick: 2s\n  qbittorrent:\n    host: h\n")
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


def test_write_tree_stamps_schema_version(tmp_path):
    """写回侧打标(计划 26-09-26-0506): WebUI 保存后 config.schema_version 盖成当前版本(int, 无引号)"""
    path = _make(tmp_path, BASE + "  main_tick: 2s\n")
    old = load_config(path)
    tree = read_tree(path)
    tree["config"]["main_tick"] = "3s"
    write_tree(path, tree, old, _bak(tmp_path))

    text = _text(path)
    assert "schema_version: 6" in text, "写回必须带当前版本章"
    assert "'1'" not in text, "版本章必须是 int —— 盖成字符串会被 ruamel 写成带引号的 '1'"


def test_preview_tree_stamps_schema_version(tmp_path):
    """预览与写入同口径: preview_tree 同样带版本章(UI 看到的 = 将写出的)"""
    path = _make(tmp_path, BASE)
    old = load_config(path)
    tree = read_tree(path)
    text = preview_tree(path, tree, old)
    assert "schema_version: 6" in text


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
    corrupt = LEGACY_V1 + "  schema_version: 6\n"
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


def test_stamp_schema_version_ignores_non_dict_cfg():
    """盖章只认 config 段: 树缺 config 段时静默跳过(不炸)"""
    from auto_qb.config.writer import _stamp_schema_version

    tree = {"other": 1}
    _stamp_schema_version(tree)
    assert tree == {"other": 1}


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
    tree["config"]["schema_version"] = "6"
    write_tree(path, tree, old, _bak(tmp_path))
    text = _text(path)
    assert "123" not in text, "旧的非映射内容被整体重建"
    assert "qbittorrent" in text and "schema_version: 6" in text
    loaded = load_config(path)
    assert loaded.qbittorrent.host == "h"


def test_write_tree_roundtrip_list_of_dicts_and_plain_int(tmp_path):
    """列表内映射逐项按 BaseLoader 语义比较(值未变整体跳过); 变更的纯数字字符串按原生标量写出"""
    path = _make(
        tmp_path, "config:\n"
        "  schema_version: 6\n"
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


def test_write_tree_backup_relative_path(tmp_path, monkeypatch):
    """备份路径无父目录(dirname 为空) -> 跳过 makedirs, 备份仍产生在 CWD 且内容 = 写盘前原样"""
    path = _make(tmp_path, BASE)
    monkeypatch.chdir(tmp_path)
    tree = read_tree(path)
    tree["config"]["web"] = {"port": "38080"}
    write_tree(path, tree, load_config(path), "config.yml.bak")
    with open("config.yml.bak", "r", encoding="utf-8") as f:
        assert f.read() == BASE, "备份 = 写盘前的旧内容"


def test_write_tree_roundtrip_preserves_site_explicit_empty(tmp_path):
    """ruamel round-trip 保留站点 ''(report 26-10-03-0504 待核实项(1)实测): 写盘 -> 读回仍为 ''

    write_tree -> ruamel dump 把 '' 写成带引号标量(add_tag: ''), BaseLoader 读回 '' ——
    「覆盖为空」这一稀疏条目在写盘链路无损, WebUI 保存不会把它洗成键缺失。
    """
    path = _make(tmp_path, V4_SITE_EMPTY)
    materialize_schema_migration(path, str(tmp_path / "data"))  # 先升到当前版本(v4->v6), 再走写盘链路
    old = load_config(path)
    tree = read_tree(path)
    tree["config"]["trackers"]["A"]["hr"]["add_category"] = ""  # 新增的站点显式空
    write_tree(path, tree, old, _bak(tmp_path))

    text = _text(path)
    assert "add_tag: ''" in text, f"已有站点 '' 应原样保留: {text}"
    assert "add_category: ''" in text, f"新增站点 '' 应写为带引号空串: {text}"
    loaded = load_config(path)
    assert loaded.trackers["A"].hr.add_tag == "" and loaded.trackers["A"].hr.add_category == ""


def test_stamp_schema_version_uses_root_key_and_overwrites():
    """盖章必须**读 ROOT_KEY 段**(不是硬编码 None)且**无条件覆盖**旧版本值

    _stamp_schema_version 的两条同构变异: (1)`cfg = tree.get(ROOT_KEY)` 改成 `tree.get(None)`
    (2)整句删掉 —— 前者让 cfg 恒为 None 从而静默不盖章, 后者同理。守阵: 用缺 config 段的树
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
