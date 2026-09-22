# 配置加载 · 写回 · fail-fast 校验

> 📅 **内容基线**: 2026-09-05 @ `51374bd`(全库逐文件核实, 见本库 [README.md](../README.md));
> 文内带日期的条目为**增量更新**, 最新易变状态见 [activeContext.md](../activeContext.md)。

> 摘要: `load_config` 加载机制、图形化编辑器的写回、`validate_config` 全量聚合校验。
> 触发: 配置加载, load_config, 写回, 图形化编辑器, fail-fast, validate_config, 新配置键

## 配置加载机制 (config.py `load_config`)

- YAML 用 **`yaml.BaseLoader`** 加载 → **所有标量都是字符串** (包括数字/布尔), 随后经 `utils.parse_*` 转换 (`parse_time`/`parse_fsize`/`parse_speed`/`parse_bool`/`int()`)。因此:
  - `parse_bool` 接受 true/1/yes/on (大小写不敏感), 非法值抛 ValueError (fail-fast)。
  - exporter 导出时用 `convert_bool_in_dict` 把字符串布尔转回真布尔以保留可读性。
- **fail-fast**: 非法格式/未知键在加载时抛 ValueError, 程序不启动。给新配置键写解析时必须校验并给出可读错误 (参考 `load_global_speed_limit_curve` 的逐键 unknown-key 检查风格)。
- 站点配置覆盖全局: `load_tracker_hr(spec, global_hr)` 站点字段优先全局兜底; `remove_similar_tags` 同理。合并发生在加载时, 运行期只用合并后的值。

## 配置写回(图形化编辑器, 2026-09-14, config/writer.py)

WEB UI 设置页的保存路径(取代旧的"直接编辑 YAML 全文"):

1. 前端提交与磁盘**同构的 YAML 树**(标量全为字符串, 与 `BaseLoader` 语义一致), 就地增删改;
2. `write_tree` 把树落临时文件跑 `load_config` —— **与程序启动完全同一校验路径**, 失败 400 且不碰磁盘;
3. `diff_config_impacts` 判定变更(热重载级别唯一来源仍是 `impact.py`);
4. **R 级字段(state_file/data_dir)回退为磁盘旧值**(进程身份不可热切换, 与旧行为一致), 并在响应中回报 `restart_required`;
5. 备份为 `<data_dir>/<配置文件名>.bak`(备份路径由 `web.py` 传入 `write_tree`, **不再**在项目根目录生成 `config.yml.bak`; 目录不存在时自动创建) → **ruamel round-trip 写盘** → 投递 `reload_config` 命令(仍由主循环线程应用)。

**注释与格式取舍**: 已存在键的注释保留; **值未变化的键跳过赋值**以保留原标量形态(否则 ruamel 会把无引号的 `16585`/`true` 重写为 `'16585'`/`'true'`); 新增/修改的标量走 `_plain_scalar`(数字/布尔写成原生标量, BaseLoader 下语义等价); **列表整体替换, 项级注释不保留**。

**UI 元数据(新增配置键时必看)**: `config/schema.py` 是图形化表单的唯一描述来源, 新增配置键必须同步登记 `GROUPS`(或对应段), 新增条件/动作插件必须同步登记 `CONDITION_PLUGINS`/`ACTION_PLUGINS` —— 否则 `tests/test_config_schema.py` 的守卫测试直接失败(键集合 vs `KNOWN_*_KEYS`, 插件表 vs `registry`)。

**单位控件的元数据约定 (2026-09-14)**: `Field.kind` 属 `schema.UNIT_KINDS`(`time`/`size`/`speed`)时, 前端把值渲染为**数值框 + 单位下拉**(选项表 `schema.TIME_UNITS`/`SIZE_UNITS`/`SPEED_UNITS`, 由前端 `UNIT_OPTIONS` 镜像 —— 只按 kind 决定单位, 故插件 spec(`spec_kind="speed"`)与配置字段共用同一控件)。`Field.unit_default` 仅在“未配置/无法解析”时作为下拉框初值(如 `extra_seeding_time` 习惯从 `H` 开始), 留空则回退该 kind 的首个单位。**写回仍是单个字符串**(与磁盘同构的 YAML 树不变), 合法性仍由 `validate_config` 把关; 新增 UNIT_KINDS 字段时 `default` 须写成完整的“数值+单位”形式(守测 `test_unit_kind_defaults_are_parseable`)。

**规则引用控件 (2026-09-14)**: 站点 `rules` 字段的 `kind` 为 `rules_ref` —— 前端渲染“可自由输入 + 下拉快捷追加”(下拉选项从配置树的 `*_rules` 动态生成), 因站点若手写错规则集名, 校验只在保存时报错, 不如直接给选择器。
**帮助文本是纯文本, 不要写 Markdown 标记 (2026-09-14)**: `Field.help`/`Field.risk`/`Plugin.help` 由前端当作**纯文本**插入 DOM(不经 Markdown 渲染), 因此 `**粗体**` 会原样显示成星号 —— 需要强调时用措辞与标点, 不要用 Markdown 语法。

## fail-fast 全量校验 (2026-09-05 新增, config.validate_config)

`load_config` 在解析前做全量校验, **聚合全部错误一次性抛 `ConfigError`**(ValueError 子类, 统一承载文件读取失败/YAML 解析失败/校验失败/启动期规则 spec 错误), 每条带配置路径, 形如:

```
配置校验失败(config.yml), 共 2 处:
  [1] config.qbittorrent: 未知键 ['hos'], 可用键: ['host', 'password', 'port', 'username']
  [2] config.trackers.T1: 缺少必填键 domains(站点域名列表)
```

校验范围:
- **未知键**: 根节点(仅允许 config)/config 顶层/各段(log/qbittorrent/grouping/hr)/tracker 段/站点 hr 段/规则 spec 一律拒绝; `single_instance_lock` 为规划中预留键(接受但不生效)
- **必填项**: tracker 的 `domains`(非空字符串列表)、站点 hr 的 `required_seeding_time`; 其余键有默认值
- **值格式**: 复用 utils.parse_*(时间/大小/速度/布尔)与 parse_hr_condition; `main_tick` 须 >0; `port` 1-65535; 日志等级须合法; `regex:` 模式须可编译(delete_tags/tracker.remove_tags/tags/category/trackers 条件/remove_tags 动作, 经 `_PLUGIN_SPEC_VALIDATORS` 分发)
- **取值范围 (2026-09-22 收紧, issue 26-09-22-1937)**: 拦"格式合法但危险"的值 —— `interval` 1s-1D(0 会经 TaskQueue._norm_interval 归一化成 1s → 全部种子级任务每秒跑)/`main_tick` 0.5s-1H/`sync_interval` 1s-10M/`max_tasks_per_tick` 1-500(上界防单 tick 上千任务)/`log.max_bytes` 1MiB-1GiB(0 在 RotatingFileHandler 语义 = 从不轮转 → 磁盘写满)/站点 hr `required_share_ratio` [0,100] 且拦 nan/inf(nan 比较恒 False 永不满足)/`hr.condition` 百分比 (0,100] 与下载量 >0(在 `utils.parse_hr_condition` 解析单点拦, 校验层经 `_try` 复用)/`notify.max_per_hour` ≤100/`notify.dedup_window` ≤24H(0=不去重仍合法)/规则 `interval` 显式配置须 >0(缺省 0S=每 tick 级别是既有行为, 未动)。助手层: 新增 `_try_number`(int/float + `math.isfinite` 拦 nan/inf + 闭区间), `_try_time` 增 `min_s/max_s` 形参, `_try` 成功时返回解析值供调用方续做范围检查(log.max_bytes 用)
- **规则集 spec**: 已知键/`execute_once`(never/once/daily/hourly)/`stop_following_rules_if` 六值/`trigger` 四值(interval/on_torrent_added/on_torrent_deleted/on_torrent_state_enum_changed, 取值非法即抛)/conditions-actions 须单键字典且名称已注册(经 registry 延迟导入, 避免循环依赖); **触发时机×动作兼容白名单** (`_validate_trigger_action_compat`): `on_torrent_deleted` 仅允许 `print_torrent_details`(删除后种子无活现场, 需活种子的动作直接拒绝, 见 04), 其余 trigger 不设限; 条件/动作 spec 值的深度校验在 Rule 构造时进行(报错带规则名上下文)
- **tracker.rules 引用**: 必须 `@` 开头且引用的规则集/规则存在(否则运行时会静默不执行)

**留空语义**: `yaml.BaseLoader` 把 `key:` 留空解析为空串 `''`(不是 None); `_strip_none` 将 None/空串统一视为"未配置", 走默认值(默认值本为空串的键如 hr.add_tag 行为不变)。因此"有默认值的配置允许为空, 没有的必须有"。

**默认值单一来源 (2026-09-05)**: 全部默认值只定义在 `models.py` 的 dataclass 字段上 (解析后空间, 与字段类型注解一致, `Config()` 即全默认实例)。`loaders.py` 统一用 `_get(spec, key, d.field, parse)` 取值: 键存在 → parse(原始串); 键缺失 → 字段默认(不再 parse)。models 顶部仅存 2 个**非字段默认**常量: `DEFAULT_CONFIG_FILE`(cli argparse 缺省) 与 `UNLIMITED_SPEED`(exporter 生成模板的原始串占位)。

**先验证再解析**: 全部正确性检查集中在 `validate_config`(含 `_validate_global_speed_limit_curve` 与 `_PLUGIN_SPEC_VALIDATORS` 插件 spec 深度校验); 通过后各 `load_*` 函数仅做转换、不含任何检查。**config 之后的全部代码同样假定配置正确**: registry 工厂直接按名索引(未知名 = KeyError, 由校验兜底)、`config.global_speed_limit_curve`/`rules_config`/`tracker.rules` 等属性直接访问(无 getattr 兜底)、exporter 重读原始文件时复用 `_strip_none`。注意区分: 功能开关(`grouping.enabled`/`check_missing_files`/`hr` 等)是语义判断不是正确性检查, 正常保留。

**单实例锁 (2026-09-05)**: 仅正常 `run()` 模式持锁, 锁文件 `<state_file 去扩展名>.lock` 与伴生 `.meta.json` (PID/启动时间/配置路径); 锁失败抛 `SingleInstanceLockError(AutoQbError)`, 走 CLI 退出码 1 + stderr 无堆栈; `--export-yaml` / `--export-torrents_info` 通过 `QbManager(no_lock=True)` 跳过锁 (可与正常实例并发); 基于第三方 `filelock` (跨平台 fcntl/msvcrt); 陈旧锁不接管, OS 句柄随进程退出自动释放, 必要时手动删除锁文件。

**CLI 错误输出**: `cli.main` 单点捕获 **`AutoQbError` 体系** —— `ConfigError` 加 `配置错误: ` 前缀输出; `SingleInstanceLockError`(锁竞争)/`QbCompatError`(qB 字段不兼容)等消息自身已含完整上下文, 直接输出。均无堆栈/exec_info, 退出码 1。非 AutoQbError 异常(ValueError/OSError 等)属程序 bug, 照常抛出保留堆栈。入口(auto-qb.py / __main__.py)用 `sys.exit(main())` 使退出码生效。
