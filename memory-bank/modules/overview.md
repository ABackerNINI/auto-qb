# 包入口与「在哪里改」速查

> 📅 **内容基线**: 2026-09-05 @ `51374bd`(全库逐文件核实, 见本库 [README.md](../README.md));
> 文内带日期的条目为**增量更新**, 最新易变状态见 [activeContext.md](../activeContext.md)。
> 行数为 2026-09-05 快照。所有路径相对 `src/auto_qb/`(除注明)。

> 摘要: 包入口在哪、要改某功能该动哪个文件 —— 进本目录前先读这一份。
> 触发: 包入口, 在哪里改, 改哪个文件, 入口, src 布局

## 包入口

| 文件 | 行数 | 职责 |
|------|------|------|
| `../auto-qb.py` | 8 | 兼容入口: `python src/auto-qb.py` → `cli.main` |
| `__init__.py` | 23 | 导出 Config/QbManager/load_config, `__version__="0.2.0"` |
| `__main__.py` | 5 | `python -m auto_qb` 入口 |

## 常用"在哪里改"速查

| 需求 | 位置 |
|------|------|
| 新配置键 | `config/models.py` (dataclass 字段+默认值) + `config/loaders.py` (load 函数) + `config/validation.py` (校验+KNOWN 键); 如属 tracker 级加进 `load_tracker_config` |
| 新规则条件 | `rules/conditions.py` 写类 + `@register_condition` (装饰即注册, import 已在 `rules/__init__.py`), 并在 `config/validation.py` 加 spec 校验 |
| 新规则动作 | `rules/actions/` 对应职责模块写类 + `@register_action`, 并在 `actions/__init__.py` import(否则不注册), 并在 `config/validation.py` 加 spec 校验; 需要新变量替换则扩展 `utils.replace_vars` |
| 新集数命名模式 | `episodes.py` `_EPISODE_PATTERNS` 列表按优先级插入 |
| 新流量数据源 | `curves.py` 加解析 + `mixins/speed_curve.py`/`config/validation.py` 扩展 traffic_source 校验 |
| 新全局周期任务 | `qbmanager.py` `_create_global_tasks` 加 Task |
| 新种子级内置任务 | `qbmanager.py` `_create_torrent_tasks` + handler |
