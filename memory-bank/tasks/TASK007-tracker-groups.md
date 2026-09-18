# TASK007 - tracker 分组 (站点 groups 字段 + tracker_group 条件)

**Status:** Completed
**Added:** 2026-09-15
**Updated:** 2026-09-15
**专题:** 规则系统 / 配置模型

## 原始请求

- 2026-09-15: 支持按 tracker 分组 (站点段声明组名, 规则可按组筛选); 要求先出计划并列出决策点。

## 思考过程与决策

- **D1 = 方案 B**: 站点段新增可选 `groups` (字符串列表) — 组名即声明, 零引用错误面 (`TRACKER_FIELDS` 加 `str_list` 后设置页自动渲染, 前端零改动); 否决方案 A (顶层 `tracker_groups` 段, 唯一硬优势是引用校验但 B 无此错误面)。
- **D2 = 新条件插件 `tracker_group`**: 镜像 `TrackersCondition`, 走 `utils.match_value`, 或关系, 支持 `regex:` 与 `:ignore_case`, 无 `tracker_conf` 恒 `False`。
- **热重载级别 S0 核实**: `groups = L2` — `record.tracker_conf` 仅在 added 流程绑定一次, L2 经 `reset_runtime` 置空重匹配才见新值 (与 `domains` / `rules` 同级); L0 会读到旧 conf 对象。
- 空串项被 `_strip_none` 统一剔除属项目既有约定 (用例改测纯空白项)。
- **阶段 2/3 (前端) 后续**: 设置页 groups 下拉快捷追加 (`rules_ref` 风格) + 辅种管理页按组筛选。

## 实现计划

- [x] `models.py` `TrackerConfig.groups`
- [x] `validation/sections.py` `KNOWN_TRACKER_KEYS` + `_check_str_list` 校验
- [x] `loaders.py` `_get` 解析
- [x] `impact.py` `TRACKER_FIELD_LEVELS` `groups=L2`
- [x] `conditions.py` `TrackerGroupCondition` (+ `validation/rules.py` spec validator)
- [x] `schema/rules.py` Plugin + `schema/trackers.py` Field (双登记, 守卫自动 15→16)
- [x] 测试 +4 (`helpers.FakeTracker` 加 `groups`), 基线 884 passed
- [x] 真机 `--dry-run` 冒烟 (119 种子 / 规则加载 / 决策链)
- [x] 文档回写 (README 5 处 15→16 / `docs/configuration.md` / `rule-system.md` / `config-reference.md` / `testing.md` / `想法.md` 勾选 / 计划文档状态)
- [ ] 阶段 2/3 前端 (设置页快捷追加 + 按组筛选)

## 子任务状态表

| ID | 描述 | 状态 | 更新 | 备注 |
|----|------|------|------|------|
| 7.1 | 计划文档 + 决策点 | Complete | 2026-09-15 | `docs/plans/26-09-15-1504-tracker-group-plan.html` |
| 7.2 | 后端实施 (models/validation/loaders/impact) | Complete | 2026-09-15 | 已随提交入库 (`backend/develop`) |
| 7.3 | 新条件插件 `tracker_group` | Complete | 2026-09-15 | 条件 15→16 |
| 7.4 | 测试 + 真机冒烟 | Complete | 2026-09-15 | 884 passed |
| 7.5 | 阶段 2/3 前端增强 | Not Started | 2026-09-15 | 设置页 groups 快捷追加 / 辅种页按组筛选 |

## 进度日志

### 2026-09-15

- 全部后端工作落地并入库, 基线 884 passed, 真机 dry-run 通过。
- 后续合并: worktree 同步时 `README` / `testing.md` / `activeContext` 三处冲突按"两侧全保留"解决 (基线 942+4=946)。

## 历史会话纪要 (原文归档)

> 以下为 `activeContext.md` 会话纪要的**原文归档** (2026-09-17 机械迁移, 未删改; 含一处历史 GBK 编码损坏条目),
> 按时间倒序保留。新增进展请写 `## 进度日志`, 不要再往 `activeContext.md` 堆长纪要。

- 2026-09-15: tracker 分组计划会话 — 读 AGENTS/memory-bank(rule-system/config-reference)后摸底 TrackerConfig(models.py)/KNOWN_TRACKER_KEYS(sections.py)/TrackersCondition(conditions.py)/_PLUGIN_SPEC_VALIDATORS/GROUPS+TRACKER_FIELDS(schema)/TRACKER_FIELD_LEVELS(impact.py)/守卫测试, 产出 docs/plans/26-09-15-1504-tracker-group-plan.html (delivery-artifact Native 冷峻技术方向, 与既有计划同族), 未改任何代码。关键结论: 推荐 D1=方案 B(站点段新字段 groups, 组名即声明零引用错误面, TRACKER_FIELDS 加 str_list 后设置页自动渲染前端零改动)而非 A(顶层 tracker_groups 段, 唯一硬优势是引用校验但 B 无此错误面); D2=新条件插件 tracker_group(镜像 TrackersCondition, 走 utils.match_value); 守卫双面覆盖(站点键集合+条件插件表 15→16); 首要核实点 S0=TRACKER_FIELD_LEVELS 里 groups 列 L0 还是 L2(取决于 TorrentRecord.tracker_conf 热重载重绑定机制, 拿不准列 L2 保守)。待用户拍板 D1/D2/阶段 3(管理页按组筛选)后实施。
