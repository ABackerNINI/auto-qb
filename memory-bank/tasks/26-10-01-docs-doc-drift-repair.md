# 26-10-01-docs-doc-drift-repair — 知识库文档漂移分段修复

**Status:** Done
**Added:** 2026-10-01
**Updated:** 2026-10-01
**Summary:** 内核化重构+别名层处置后的全库文档漂移, 按 plans/26-10-01-1728 分五段(S1-S5)回写; **S1-S5 全部完成并过验收**(S5 = P3 计数清扫 + 豁免核实 + 顺手项 + 机检三连 + 收尾基线 1909 passed / 91% 切片 26-10-01-1930; 代码注释残留 3 处待用户拍板未动)。

**Topics:** docs-doc-drift-repair

## 原始请求

用户 26-10-01 判定「底层经过重构, 文档可能出现很多漂移」, 先审计后出分段修复计划(plans/26-10-01-1728-plan-doc-drift-repair.html, 立档前已获用户确认); 本轮用户指令「实施S1: 26-10-01-1728-plan-doc-drift-repair.html」。

## 思考过程与决策

- 方案与取舍冻结在计划文档, 本档案只记执行与验证数字(计划 §8)。
- **S1 顺带收口一处计划未列项**: web-runtime.md 前端列缓存键 `autoqb_cols_v4` → `v5`(坐标 `webui/static/shared/app.js:207`, v4/v3 已入 LEGACY_COLS_KEYS `:208`)—— 该段属重写级回写, 带着已知错值进新稿违背重写本意; 计划 S3 对 core-domain.md 有同键修复, 口径一致。
- 行数/计数快照: core-runtime.md 有「快照披露」头注, 除计划点名的实测项(带 26-10-01 实测标注)外, 其余行数按计划 S5 豁免口径不动。

## 实现计划

五段路线与各段文件清单/验收口径见 [plans/26-10-01-1728](../plans/26-10-01-1728-plan-doc-drift-repair.html) §4; 本档案不复制。

## 子任务状态表

| 段 | 内容 | 状态 |
|----|------|------|
| S1 | P1 架构描述重写(5 份: systemPatterns/overview · main-loop · web-runtime · client-and-state + modules/core-runtime) | 完成(26-10-01) |
| S2 | 误导指路与机制反转单点修(9 份, 2 处 P1) | 完成(26-10-01) |
| S3 | modules/ 中度批(6 份) | 完成(26-10-01) |
| S4 | 用户面文档(4 份: README + docs/) | 完成(26-10-01) |
| S5 | P3 清扫 + 待决件 + 收尾基线(test.full 基线切片) | 完成(26-10-01) |

## 进度日志

- **2026-10-01 S1 完成并过验收**(基线 38604d07, 未提交待用户指令):
  - 5 份全部重写, 每条新断言带代码坐标(全部实测核对: qbmanager.py:142-145/158-234/339-351/441-449/485/530-535/577-578/663/679/692-701/726-832/818; webui/module.py:57-80/82-106; webui/runtime.py:52/105/192/328/556/576/581/603/613-642/116-164; webui/views.py:27/77-78/235-341; webui/server/auth.py:59/67; routes/__init__.py:6-20(11 域); core/state.py:117/149/183; core/modules/speed_curve_mod.py:280/301; core/modules/rules_mod.py:397; infra/versioning.py:28; tracker_mod.py:40/60/77; maintenance_mod.py:81/189; taskqueue.py:33; app.js:207-208)。
  - 退役名 grep 零残留 8/8: `_WEB_STATE_ALIAS` / `remove_torrent` / `flush_receipts` / `_hr_view_fields` / `SpeedCurveMixin._publish_traffic` / `ops_recheck` / `_web_token` / `web_runtime.py`。
  - 机检: `kb.index` 重建(4 份三行头有动) → `kb.check` 绿(主键纪律 OK: 251 文档 / 154 专题) → `doc.links` 绿 → `pytest tests/test_memory_bank.py` 27 passed。test.full 基线按计划留给 S5 收尾(本轮纯文档零代码变更)。
- **2026-10-01 合流 a03c3a8d 后坐标复核**(随「提交」同步合入远端 M1+M2/M3 三提交): `take_suppressed` 消费点自轮首迁 events_removed 臂(qbmanager.py:776, take 即 arm), 747-774 区段 -4 → 修正 3 处相位坐标(full_round :758→:754 / transitions :771→:767 / 删除前快照副本 :764→:760), 其余相位坐标(:778/:808/:815/:822/:826/:818)与总行数(839)经实测均未漂移; main-loop.md 内核保留职责句补 M1 消费点语义。
- **2026-10-01 S2 完成并过验收**(基线 6f474098, 已提交 0b422396): 9 份全部按计划修毕, 每条新断言先实测核对代码坐标 —— 条件 13(`@register_condition`)/动作 12(`actions/*.py` 7+1+4, `__init__.py` 那处匹配是 docstring)/测试 73 个 test_*.py/pyproject 依赖 10 个/`validation`·`schema` 均包/hr `server.py:219-227` 四端点(补 refresh)/`maintenance_mod.py:268` `add_hr_tag_or_category`/`qbmanager.py:535` maybe_flush + `ops_mod.py:438/483/508` 即时 save/`polling.js:76-95` 恒定分档+失败退避/`state.py:183-199`/`static_ui.py:49-58`/`runtime.py:576`/`versioning.py` config=3/`writer.py:121` 盖章/`routes/config.py:111-118` + `common.py:52` `config_backup_path`/`loaders.py:448`/`single_instance_lock` 全 config 零接受(删句依据)。顺带把 techContext L10 的旧路径 `web_ui/static` 一并更正为 `webui/static`(同句指路, 属该条目修复面); productContext 版本按计划对齐 pyproject(v0.1.0)。退役名 grep 零残留(`core/mixins/tags.py` / `config/validation.py` / `config/schema.py` / `WebviewMixin` / `single_instance_lock` / `qbmanager._new_client` / 机制句 `web.py`·`web_ui/static`; 余留 2 处均合法: `tests/test_web.py` 现存文件名 + overview 迁移映射表历史件)。三行头未动 → 免 kb.index; `kb.check` 绿(253 文档 / 156 专题; 切片数 81>70 为既有债务不拦提交)。test.full 基线按计划留给 S5。
- **2026-10-01 S3 完成并过验收**(6 份全部按计划修毕, 每条断言先实测):
  - `core-config.md`: 头注快照口径改「2026-10-01 实测」; models.py 176→362(类清单补 HrChannelConfig/HrCheckConfig/SiteHrCheckConfig/WebConfig/NotifyConfig, 顺带补实测存在的 FsConfig/PathMapEntry); loaders.py 309→550(函数面补 load_web/notify/hr_check/site_hr_check/fs_config + normalize_schema_version/migrate_config_schema + materialize 落盘口径; `load_add_episode_tags` 更名 `_get_episode_tags`); validation/ 817→1341(同表顺带刷新); schema/ 932/5→1396/6 补 hr.py; 新增 site_presets.py(111, 三命名空间判定单点)与 migrations.py(146, v1→v2 一次性迁移)两行; writer.py ~215→427(补 materialize_schema_migration); impact.py ~55→69 补 `KERNEL_SECTIONS` 五段及 P6 并集口径。
  - `core-domain.md`: L6 838→839 行; web_ui/static 行 双界面→三界面(补 console/, V1 深海单主题)+「双 shell」→「三 shell」(守阵 `_UI_ALL` 实扫三套, tests/test_web.py:613); app.js 411→488; 片段口径 15→23 个 `AQB_*` mixin(app.js:464-486 实数); `autoqb_cols_v4`→`v5`(shared/app.js:207-208, v4/v3 入 LEGACY_COLS_KEYS)。
  - `rules-and-deps.md`: conditions.py 294→261 行、16→13 条件; actions 906→934/6、12 动作确认并补分文件行数; tests 段整体改写 33→73 个 test_*.py, 按六域分组并补守阵清单(alias_freeze/module_host/modules_p3-p6/config_key_surface/memory_bank/docs_forms/commands_engine 等); 依赖图 qbmanager 行补 webui/hr/core.module+state/infra 边(逐条对 qbmanager.py:36-76 import 实测, 内核零 rules import 口径保留), `modules/*`→`core/modules/*`; schema 图补 hr.py(fields 零依赖; hr/trackers/rules→fields; groups→{fields,hr,trackers})。
  - `webui-static-contract.md`: L9 拆分段整体改写为 09-27 三层拆分现状(app.js 488 行 / shared/ 27 个 JS / state+lifecycle 根选项展开 / 23 个 AQB_* mixin), 硬约束改「shell 清单序」; L11 两套 UI→三套共用 shared/。
  - `mixins.md`: 摘要转「历史快照」定位; tags 并非独立模块 → 并入 MaintenanceModule(`ctx.maintenance`, qbmanager.py:223); 补两 mixin 类声明坐标 qbmanager.py:142-145。
  - `conventions/modules.md`: 三层结构表十模块目录归属注记(8 本体 core/modules/*_mod.py + 2 门面 webui/hr module.py); 838→839 行; 「内核自有方法 17 / 属性对 7」AST 逐项核实 —— 类体 def 名 24 = 内核自有 17(15 方法 + `__init__` + `state_file` 只读 getter) + 属性 7 名(6 组读写对 + client 绑定对); 原文把 `state_file` 列进「属性对」而漏 `client`, 已按「外观属性面 7 个(config/store/api/state/state_file/task_queue/web, state_file 只读不成对)+ client 非外观绑定对」定口径; baselines 基线路径补全 `memory-bank/testing/` 前缀。
  - 机检: mixins.md 摘要有动 → `kb.index` 重建 → `kb.check` 绿 → `pytest tests/test_memory_bank.py` 27 passed。与计划的偏差均为「以代码为准」: 计划未列的 writer.py/validation/ 行数与 core-domain「双 shell」措辞随同表实测刷新。test.full 基线按计划留给 S5。
- **2026-10-01 S4 完成并过验收**(4 份全部按计划修毕, 每条断言先实测核对代码坐标; 随本段单独提交入库):
  - `README.md`: L84 「?? 种条件」→ 13、触发时机补全 5 种(加「字段变化」; TRIGGER_VALUES 实测 5 项, config/validation/rules.py:29-36); 架构节「16 种筛选条件」→ 13; 十模块归属更正为「8 本体 core/modules/*_mod.py + 2 门面 webui/hr module.py」(目录实扫: core/modules/ 恰 8 个 *_mod.py)。
  - `docs/configuration.md`: L410 条件 16→13; 筛选条件表头 12→13 并补 `expr` 行(ExprCondition, rules/conditions.py:216-234; `@register_condition` 实数 13); 触发表补 `on_torrent_field_changed` 行 + watch_fields 注记(FIELD_WATCH_ALLOWED = tags/category, rules.py:38; 校验在 rules.py:158-171), YAML 示例补 watch_fields 注释行; hr_check 全局段 7 键→8 键(HrCheckConfig 除 sites 外恰 8 字段, models.py:108-119, 与原列举 8 项对齐); 旧键迁移句 v2→v3 → v1→v2 并拆开表述(_migrate_config_1_2 改写到 sites, migrations.py:40; v2→v3 只把 mode 转 enabled)。
  - `docs/deployment.md`: §11.3 指路 `core/mixins/grouping.py` → `core/modules/grouping_mod.py:273`(`_check_missing_files`), 旧 `os.path.exists` 片段 → `fa.exists` + `UNDETERMINED` 现状(:296-307 实读); §14 state schema v2→v3(infra/versioning.py:28); §8 卷名示例 `auto-qb-clone4_` → `<项目名>_` 占位(节尾本有「以 docker volume ls 实际输出为准」注)。
  - `docs/hr-online-verify-docs.md`: 删两行坏链索引(26-09-22-2204-backend-partial-hr-verify 与 26-09-25-0555-webui-ext-hr-logging 两个 activeContext 切片, ls 实证不存在); 「想了解功能全貌」先读入口改指任务档案(现存) + 26-09-29-0404-hr-verify-v3-audit 切片(现存)。
  - 与计划的偏差(以代码为准): 计划称 configuration L495 为「16」实测该处写「12 种」(同一文档 L410 与表头自身就互斥), 一并统一为 13; 其余坐标全部命中。
  - 机检: `doc.links` 绿 + `kb.check` 绿(切片 81>70 为既有债务, 不拦提交); 档案/slice 摘要有动 → `kb.index` 重建。test.full 基线按计划留给 S5。
- **2026-10-01 S5 完成并过验收(全段收尾; 随本段单独提交入库)**:
  - **P3 计数清扫**(逐条 `wc -l`/grep 实测, 只修无「快照披露」头注的, 修处统一标实测口径): `projectbrief.md` 15→13 种筛选条件(`@register_condition` 计 13); `progress/roadmap.md` 图形化配置编辑行 16→13 条件; `modules/rules-and-deps.md` base.py 274→314 / expr/ ~700·6 文件→1245·7 文件(含 `__init__.py` 46) / actions/ 934→673、full_checking 178→152 —— 后两处为 S3 沿用旧文未复测的残留, 实测校正。
  - **豁免未动**(有披露头注, 按计划 §4-S5 既例): productContext.md(「内容基线 2026-09-05」头注; 其 `src/auto_qb/ ~6300 行` 实测 123 文件 28266 行, 属披露快照, 列汇报)、modules/overview.md 与 core-domain.md(「行数为 2026-09-05 快照」头注; core-domain torrents/ 行 816 实测 1262, 同属披露面)、core-runtime.md(「快照口径以行内标注为准」)、mixins.md(历史快照定位)、webui-static-contract.md 与 core-config.md(已标 26-10-01 实测)、conventions/code-style.md(实测无残留计数断言)。
  - **顺手项**: `src/auto_qb/mixins/`(仅 __pycache__, 26-10-01-1835 基线删过一次后被测试进程再生)再次确认 git 零跟踪后删除。
  - **代码注释残留**: 按计划 §6 用户未拍板, **未动任何 .py**; 实存 3 处(core/state.py docstring / qbmanager.py:398 / webui/runtime.py:237; 第 4 处 core/mixins/__init__.py 已随审计 L2 删除), 仍待拍板。
  - **机检三连全绿**: `kb.index` 再生 16 个索引(plans/_index.md 随 doc-status=Done 重建); `kb.check` 256 文档 / 159 专题无缺主键(既有债务: 切片 81>70 + cap 债务 1, 未新增); `doc.links` 绿。
  - **收尾基线**: test.full **1909 passed + 3 skipped / 91%**(13278 语句 / 1051 未覆盖 / 4408 分支 / 435 partial, test.full 31.2s, rc=0), 切片 [testing/baselines/26-10-01-1930-doc-drift-repair-s5.md](../testing/baselines/26-10-01-1930-doc-drift-repair-s5.md)(基线 develop @ 7f046ca0, S4 已提交、工作树含 S5 文档改动); 通过数与 26-10-01-1835 基线持平(纯文档零代码变更)。已完成条目迁出 progress/implemented-tooling.md; 计划 doc-status Open→Done(26-10-01-1930) + 变更记录行。
