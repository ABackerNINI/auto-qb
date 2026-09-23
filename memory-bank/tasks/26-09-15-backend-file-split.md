# 26-09-15-backend-file-split — 后端大文件拆分

**Status:** Completed
**Added:** 2026-09-15
**Updated:** 2026-09-15
**专题:** 架构 / 重构 (零行为变化)
**Legacy-ID:** TASK004
**Summary:** `qbmanager` / `schema` / `torrents` / `validation` 四包拆分, 纯移动零行为变化; 遗留: 既有测试顺序污染待排查 (2026-09-15)

## 原始请求

- 2026-09-15: 拆分后端巨型源文件 (`qbmanager.py` / `config/schema.py` / `torrents.py` / `config/validation.py`), 计划见 `memory-bank/plans/26-09-15-1124-backend-file-split-plan.html`。

## 思考过程与决策

- 原则: **纯移动零行为变化**, 调用方导入面尽量不动 (仅 `test_web` 的 `SEARCH_INDEX_BUILD_BUDGET` patch 目标改 `web_view` 模块)。
- `QbManager` 保持"组合根 + 全部状态留核心", 视图簇 / 命令簇拆为 mixin (最终 8 个 mixin)。
- `config/validation.py` 拆分后由入口做延迟导入 (`validate_config` 内) 以**防循环导入**。
- 拆分前先把工作区遗留的第八轮改动 (后端 singles + 前端 + `test_web`) 验证后独立补交 (`362f292`), 避免混提交。

## 实现计划

- [x] 批次一: `qbmanager.py` 1118 → 647 行 (视图簇 → `mixins/web_view.py`, 命令簇 → `mixins/web_commands.py`, 客户端构造 → `qbclient.py`)
- [x] 批次二: `config/schema.py` 855 行 → 包 (fields / trackers / rules / groups / `__init__`)
- [x] 批次三: `torrents.py` 725 行 → 包 (compat / view / record / store); `config/validation.py` 687 行 → 包 (core 助手 + 入口)
- [x] 真机 `--dry-run` 冒烟 (109 种子同步 / 规则加载 / 任务创建 / 决策链)
- [x] `modules.md` / `systemPatterns.md` 回写 (8 mixin / 包结构 / 依赖方向)
- [ ] 既有测试**顺序污染**排查 (`test_web` + `test_qbmanager` 连跑特定用例必红, HEAD 基线同样复现)

## 子任务状态表

| ID | 描述 | 状态 | 更新 | 备注 |
|----|------|------|------|------|
| 4.1 | 批次一 `qbmanager.py` | Complete | 2026-09-15 | 提交 `0c35474` |
| 4.2 | 批次二 `config/schema.py` | Complete | 2026-09-15 | 提交 `572e154` |
| 4.3 | 批次三 `torrents.py` + `config/validation.py` | Complete | 2026-09-15 | 提交 `8a4374d` / `5e69131` |
| 4.4 | 遗留第八轮改动独立补交 | Complete | 2026-09-15 | `362f292` |
| 4.5 | 测试顺序污染排查 | Not Started | 2026-09-15 | 非本次引入, 全量绿 |

## 进度日志

### 2026-09-15

- 三批次全部完成并提交, 各批 pytest 872 全绿; 导入面零改动 (调用方无感)。
- 发现既有测试顺序污染现象 (与本次拆分无关), 记入待办。

## 历史会话纪要 (原文归档)

> 以下为 `activeContext.md` 会话纪要的**原文归档** (2026-09-17 机械迁移, 未删改; 含一处历史 GBK 编码损坏条目),
> 按时间倒序保留。新增进展请写 `## 进度日志`, 不要再往 `activeContext.md` 堆长纪要。

- 2026-09-15: 后端大文件拆分实施(三批次, 计划见 [memory-bank/plans/26-09-15-1124-backend-file-split-plan.html](../plans/26-09-15-1124-backend-file-split-plan.html)) — 批次一 qbmanager.py 1118→647(视图簇→mixins/web_view.py WebviewMixin, 命令簇→mixins/web_commands.py WebCommandsMixin, 客户端构造→qbclient.py; QbManager 8 mixin, __init__ 组合根+全部状态留核心); 批次二 config/schema.py 855→包 5 文件(fields/trackers/rules/groups/__init__); 批次三 torrents.py 725→包 5 文件(compat/view/record/store) + config/validation.py 687→包 5 文件(core 助手+入口, validate_config 内延迟导入各段防环)。全程纯移动零行为变化, 调用方导入零改动(仅 test_web 的 SEARCH_INDEX_BUILD_BUDGET patch 目标改 web_view 模块); 实施前先把工作区遗留的第八轮改动(后端 singles+前端+test_web)验证后独立补交(362f292); 发现**既有测试顺序污染**: test_web+test_qbmanager 连跑 test_refresh_removed_grouping_disabled 必红(HEAD 基线同样复现, 全量绿), 待排查; dry-run 真机冒烟通过(109 种子同步/规则加载/任务创建/决策链); pytest 872 全绿; 提交 0c35474/572e154/8a4374d/5e69131; modules/systemPatterns 回写(8 mixin/包结构/依赖方向)。
