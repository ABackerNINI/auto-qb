# 26-10-22-test-manager-builder-params-dup — QbManager 构造单点扩参数, 89 处内联装配回收 + 静态守阵

**Status:** Done
**Added:** 2026-10-22
**Updated:** 2026-10-22
**Summary:** 认领 issue 26-10-21-0502(refactor, light): `tests/helpers.make_manager` 是 QbManager 构造单点(45 文件在用), 但不收 config 覆盖参数 —— 需要 grouping / add_episode_tags / delete_tags 等段的用例只能内联 `FakeConfig()` + 逐段赋值 + `QbManager("", config=cfg, no_lock=True)` + `mgr.client = FakeClient()`, 同一段四行样板复制到 12 个文件。修法 = **扩参数而非新建第二构造器**: make_manager 增 `cfg` / `bare` / `client` / `load_rules` / `**段覆盖`(未知段名 fail-fast), 另立 `grouping_cfg()` 分组段单点; 86 处内联构造全部改调单点(净 −91 行), 并新增静态守阵 `tests/test_manager_single_point.py`(AST 扫 tests/ 内 QbManager 构造, 除单点本体外零豁免)防复发。
**Topics:** test-manager-builder-params-dup
**Refs:** memory-bank/issues/26-10-21-0502-refactor-test-manager-builder-params-dup.html, memory-bank/pitfalls/testing/manager-builder-single-point.md, memory-bank/testing/baselines/26-10-22-0408-test-manager-builder-params-dup.md

## 原始请求

1. 「认领并修复 memory-bank/issues/26-10-21-0502-refactor-test-manager-builder-params-dup.html」—— 用户显式指派(认领合法, 非 agent 自行认领)。

## 思考过程与决策

- **复验先于动码**(issue 协议第 5 条): 开工同步 `06db0649` 上按 `grep 'QbManager("'` 逐文件实测 —— **86 处内联构造 / 12 文件**(test_grouping 60 / test_episodes 5 / test_delete_tags 5 / test_hr 4 / test_qbmanager 3 / test_state_matrix 2 / test_checking 2 / test_ui·test_rules_core·test_ops·test_modules_p4·test_locking 各 1), 另有 helpers.py 单点本体 1 处。issue 记「89 处 / 15 文件」: 差在口径 —— 它把 `test_web_seed_center` / `test_qbmanager_alias_freeze` 的 **docstring 提及** 也计进了文件数, 处数则含单点本体。现象属实, 规模按实测记。
- **扩参数, 不新建第二构造器**(issue 建议, 采纳): make_manager 已有 45 文件 403 处调用, 新建 `make_grouping_manager` 之类会让两套入口长期并存, 正是本条 issue 要消的病。所以三种形态都压在同一个函数上。
- **三种装配形态(参数面设计)**:
  - **默认**(`make_manager(state_file)`)—— 与改动前逐字等价: `FakeConfig` + HHan 假 tracker(`_hr_rule()` / `tracker_rules` / `tracker_kw`) + 三条示例规则 + `load_rules()`。
  - **`cfg=`**(现成配置对象)—— 给共享配置(同一 `cfg` 先后构造两个 manager)或**包装器委派**(`test_checking.make_mgr` / `test_ops.make_mgr` 收 cfg 再转手)用; 不装默认 tracker/规则。
  - **`bare=True`**(空配置)—— 等价内联 `FakeConfig()`, 配 `**段覆盖` 表达"只要某几段"; 86 处里绝大多数走这条。
- **`load_rules` 三态(None / True / False)**: 内联用例**本来就不 load_rules**(规则面为空), 若让 `cfg`/`bare` 路径也默认加载, 就是**顺手改了它们的装配语义**(grouping 用例断言 `task_queue._fast` 里没有多余任务, 加载规则会引入种子级任务) —— 所以 `None` = 自动(默认装配路径 True, cfg/bare 路径 False), 自备 `rules_config` 的场景显式 `load_rules=True`(test_checking / test_ops / test_rules_core 三处)。
- **`**段覆盖` 未知段名抛 TypeError**(fail-fast): `**kwargs` 静默 setattr 会在段名写错时造出**幽灵属性** —— 配置没生效而测试照样绿, 这正是「旁路」的变体。有 `hasattr` 守卫后, `grouping=` 写错成 `groupng=` 当场炸。
- **`grouping_cfg()` 单点**: 分组段(`GroupingConfig(enabled=..., missing_tag="MISSING")`)在 test_grouping(60+1) / test_state_matrix(2) / test_modules_p4(1) 各写一份, 收成一个工厂函数, `missing_tag` 口径(测试统一 MISSING)随之单点化。
- **收 `_group_cfg` / `_grp_env` 的本地构造器**: 前者在 test_grouping 与 test_state_matrix 各有一份逐字拷贝(2 份), 后者是 test_grouping 内的白盒环境(返回 mgr/grp/client 三元组) —— 都改成调单点, 本地只留"这个文件特有的那一点"(三元组拆包)。
- **加静态守阵(超出 issue 文字但同根)**: issue 标题就是「单点已存在却被旁路」, 只回收不加守阵必然复发(同族 webui 面已先例: `26-10-22-webui-single-point-bypass-dup`)。守阵 20 行 AST 扫描, 零豁免(需要持锁 `no_lock=False` / 自备配置 `cfg=` / 空配置 `bare=True` 都能覆盖), 并带一支「造违规文件必须被报出」的自检, 防扫描型守阵退化成恒绿(坑档 `pitfalls/testing/guard-dead-branch.md` 的同形风险)。
- **不动 src/**: 纯测试层收敛, 生产零改动。

## 实现计划

1. 复验: 逐文件统计内联构造处数(基线 `06db0649`)。
2. `tests/helpers.py`: `make_manager` 扩参数面(`cfg` / `bare` / `client` / `no_lock` / `load_rules` / `**cfg_overrides` + hasattr 守卫); 三条示例规则抽 `_example_rules_config()`; 新增 `grouping_cfg()`。
3. 12 个测试文件的内联构造改调单点; 删本地 `_group_cfg`(2 份)与 `_grp_env` 的 cfg 装配; 清理失去引用的 `QbManager` / `FakeConfig` / `GroupingConfig` import。
4. 新增守阵 `tests/test_manager_single_point.py` + 红验(临时造一个内联构造文件 → 必须判红并报 文件:行号)。
5. 格式化(`dev.fmt`) + 全量闸门(`test.full`) + 基线切片 + issue 置 Done + 回写。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 复验: 逐文件实测内联构造 86 处 / 12 文件(`06db0649`) | Done(2026-10-22) |
| 2 | make_manager 扩参数面 + `_example_rules_config()` + `grouping_cfg()` | Done(2026-10-22) |
| 3 | test_grouping 60 处改调单点(含 `_grp_env` / 删 `_group_cfg`) | Done(2026-10-22) |
| 4 | 其余 11 文件 26 处改调单点 + 三处包装器委派(`cfg=` / `load_rules=True`) | Done(2026-10-22) |
| 5 | 新增守阵 `test_manager_single_point.py` + 红验(探针判红并报行号) | Done(2026-10-22) |
| 6 | `dev.fmt` + `test.full` 全绿 + 基线切片 + issue 置 Done | Done(2026-10-22) |

## 进度日志

### R0 · 立档 (2026-10-22)

用户指派认领 issue `26-10-21-0502-refactor-test-manager-builder-params-dup`, 单轮完成: 复验 → 扩单点参数面 → 86 处改调 → 静态守阵 + 红验 → 全量闸门。

实测数字见 `commands run kb.baseline`(本轮新切片), 本档案与 issue 正文一律引用不抄。

- 2026-10-22 04:08 认领并修复: make_manager 扩 cfg/bare/client/load_rules/段覆盖五参数, grouping 段收 grouping_cfg 单点, 86 处内联构造改调(测试面 13 文件净 −91 行), 新增 AST 守阵; test.full 全绿, 守阵红验通过

- 2026-10-22 04:11 认领并修复 issue 26-10-21-0502: make_manager 扩 cfg/bare/client/load_rules/段覆盖五参数, grouping 段收 grouping_cfg 单点, 86 处内联装配改调(测试面 13 文件净 -91 行), 新增 AST 守阵 test_manager_single_point 并红验; test.full 全绿
