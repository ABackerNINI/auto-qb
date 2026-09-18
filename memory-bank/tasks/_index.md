# Tasks Index

> Memory Bank 任务档案索引。**命中立档阈值** (见 [memory-bank skill](../../.agents/skills/memory-bank/SKILL.md)) 的任务创建 `TASKnnn-<slug>.md` 并登记到下表; 状态变更时同步更新任务文件与本索引。
> 完整规程与反模式: [SKILL.md](../../.agents/skills/memory-bank/SKILL.md); 机械守卫: `tests/test_memory_bank.py` (索引↔文件双向一致 / 命名规范 / 状态分区 / 必备章节)。
> 粒度为**专题**(一个功能线一个档案, 不逐会话建文件); 历史流水账原文归档在各档案的 `## 历史会话纪要 (原文归档)` 段。
> 日常短周期工作只记 [../activeContext.md](../activeContext.md); 完成项沉淀进 [../progress.md](../progress.md)。

## In Progress

- [TASK015] WEB UI 错误种子显示具体原因 - 状态列由笼统「错误」改为具体原因(`missingFiles`→"文件丢失" / `error`→tracker `msg` 原文); 后端 `refresh_error_reasons` 主循环 TTL(300s)+预算(5/轮)预取 + 显式置脏, 视图透出 `error_reason`, 前端 `stateText` 双 UI 生效; 1006 passed, 假 qB 服务浏览器冒烟实测; **未提交** (剩用户真机走查)
- [TASK014] UI 组件库 20 式 - 按设计哲学风格库 5 流派 × 20 preset 各出一套自包含组件库单页 + 挑选索引 + 目录 README (`resources/ui-component-libraries/modelscope.dsv4.1flash/`); 四轮自检 + 7 项缺陷修复; 996 passed; 已提交 `fae019a` (剩用户挑选与按需迭代)
- [TASK013] WEB UI 第十一轮修复 (7 项) - 图标着色(导航/状态栏) + 历史去文字 + 明细表点击排序 + 辅种表加保存路径/明细表删列 + 两个横向滚动条根因(表头撑页 / `.detail` 自成滚动 / 单元格 min-width) + 标签分类芯片改状态色; 999 passed, 双 UI 冒烟逐项实测; **已入库 `4a027ef`**
- [TASK012] WEB UI 第十轮修复 (16 项 R10-01~R10-16) - 状态栏三项硬 bug(限速取数单点/星图双窗/免鉴权放行) + 列对齐进列模型 + 列偏好不重置 + 服务端目录浏览与 open-path 定位选中 + 弹窗尺寸令牌族; 999 passed, 双 UI 浏览器冒烟逐项实测通过; **已入库 `cb57bef`** (含真机走查 r1 反馈两处)
- [TASK011] WEB UI 第九轮修复 (25 项 FX-01~FX-25) - 口径单点化 + 浮层锁定契约 + 选择模型互斥/派生 + 删除链统一 + 菜单分层 + 新端点 `/api/open-path`; 996 passed, 浏览器冒烟 25 项全过; 已提交 `49d3151` (剩用户真机 dry-run)
- [TASK002] WEB UI 替代 qB 界面 (波次一~三 + 复查) - 32 工作项双 UI 同构 + 两大根因修复完成; 剩实机 CDP 双 UI 走查 + 真机 dry-run + prism 追剧模板, **未提交 git**
- [TASK010] Memory Bank 触发机制修复 - skill 载体 + always-on 阈值 + TASK001~TASK009 回填 + activeContext 瘦身 + 守卫测试完成; 待提交

## Pending

(暂无 — 下一步候选见 [../activeContext.md](../activeContext.md) 的"下一步候选"段)

## Completed

- [TASK001] 知识库 (Memory Bank) 建设与仓库治理 - `ai/` → `memory-bank/` 六核心文件迁移 + 跨 agent 入口统一 + 测试基线单点化 + worktree 同步 (2026-09-14 ~ 09-15)
- [TASK003] WEB UI 打磨轮次与棱镜重设计 (第六~八轮 + 双界面命名) - `atlas`/`prism`/`shared` 目录化 + 五主题令牌 + 各轮冒烟全绿 (2026-09-15)
- [TASK004] 后端大文件拆分 - `qbmanager` / `schema` / `torrents` / `validation` 四包拆分, 纯移动零行为变化; 遗留: 既有测试顺序污染待排查 (2026-09-15)
- [TASK005] 依赖管理与运行环境现代化 - `pyproject` + `uv.lock` + CI 切 uv + 7 个 worktree venv 重建; 遗留: 无 (2026-09-15)
- [TASK006] TorrentRecord 全字段缓存 - 快照 21 → 70 字段 (`_raw` 降为兜底) + `to_dict()`; 基线 879 (2026-09-15)
- [TASK007] tracker 分组 (站点 `groups` + `tracker_group` 条件) - 后端与条件插件完成入库, 条件 15→16; 遗留: 阶段 2/3 前端增强待排期 (2026-09-15)
- [TASK008] 追剧视图 (tvshows) - 剧/季/集解析 + 缺集计算 + atlas 三态视图, 已合入 develop; 遗留: prism 模板欠账 (2026-09-15)
- [TASK009] README 重构与配置文档分离 - README 29KB→10KB + 抽出 `docs/configuration.md` (2026-09-15)

## Abandoned

(暂无)

