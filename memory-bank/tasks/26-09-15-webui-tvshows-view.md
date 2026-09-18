# 26-09-15-webui-tvshows-view — 追剧视图 (tvshows)

**Status:** Completed
**Added:** 2026-09-15
**Updated:** 2026-09-15
**专题:** WEB UI / 剧集聚合
**Legacy-ID:** TASK008
**Summary:** 剧/季/集解析 + 缺集计算 + atlas 三态视图, 已合入 develop; 遗留: prism 模板欠账 (2026-09-15)

## 原始请求

- 2026-09-15: 增加"追剧视图" — 按 剧 → 季 → 集 聚合展示种子, 露出缺集。

## 思考过程与决策

- **同剧判定 = 无监督聚类**, 方案对比: A 手写解析 (推荐) / B `guessit` (+3 依赖, 备选) / C 文件兑底 / D `save_path` 只提示 / E TMDB (P2) / F 人工纠偏 (P2)。用户拍板"按推荐来"。
- 解析原则: 剧 → 季 → 集 三元组, 手写零依赖; **身份差分保留** — 宁可误拆不可误并。
- 缺集计算含**季包展开** (经搜索索引展开集数范围); `members` 只放 hash, 前端从 `groups ∪ singles` 索引取。
- 8 个决策点均按推荐值落地。

## 实现计划

- [x] M1 `tvshows.py` 解析模块 (解析矩阵 66 测)
- [x] M2 后端接线 `_build_shows_view` / `state.shows` / 文件兑底钩子 (`_trigger_shows_rebuild_if_pending` 置脏闭环), `test_web` +3
- [x] M3 前端 atlas 第三态视图 (剧行 / 季头 / 集行 / 集明细复用明细表 / 未识别折叠区 / 缺集徽章 / 整集右键, `SHOW_COLUMNS` 新 page `show`)
- [x] Edge CDP 冒烟 17/17 (抓出真 bug: 展示名未美化点分隔符 / 平局兜底被排序方向翻转 / 冒烟假服务缺主循环线程致文件兑底链路不可达)
- [x] 合入 develop (`merge 526a7b2`)
- [ ] prism 追剧模板 (棱镜侧欠账, 当前 `viewMode=shows` 兑底渲染种子页)

## 子任务状态表

| ID | 描述 | 状态 | 更新 | 备注 |
|----|------|------|------|------|
| 8.1 | 计划文档 (`docs/plans/26-09-15-1534-webui-shows-view-plan.html`) | Complete | 2026-09-15 | Native 冷峻技术方向 |
| 8.2 | M1 `tvshows.py` + 66 测 | Complete | 2026-09-15 | 手写零依赖 |
| 8.3 | M2 后端聚合与文件兑底 | Complete | 2026-09-15 | `_build_shows_view` |
| 8.4 | M3 atlas 前端三态视图 | Complete | 2026-09-15 | 已随 `526a7b2` 合入 |
| 8.5 | prism 追剧模板 | Not Started | 2026-09-15 | 见 [TASK002](26-09-15-webui-qb-replacement.md) 2.10 |

## 进度日志

### 2026-09-15

- 计划 + M1-M3 + 冒烟 17/17 全绿, pytest 942 全绿, 已合入 develop。
- 踩坑: PowerShell `Get-Content` 无 BOM 按 GBK 误读 UTF-8 → 写回损坏 `style.css` 中文注释 (`git checkout` 恢复, 改用 python patch 文件); `python -c` 内联中文同样被 GBK 搞坏; Edge 须 `Start-Process` 外部启动 + CDP 端口参数; 冒烟缺集预期未算季包覆盖。

## 历史会话纪要 (原文归档)

> 以下为 `activeContext.md` 会话纪要的**原文归档** (2026-09-17 机械迁移, 未删改; 含一处历史 GBK 编码损坏条目),
> 按时间倒序保留。新增进展请写 `## 进度日志`, 不要再往 `activeContext.md` 堆长纪要。

- 2026-09-15: 追剧视图计划 + 实施会话 — 上午调研产出 docs/plans/26-09-15-1534-webui-shows-view-plan.html(Native 冷峻技术方向): 同剧判定=无监督聚类, 方案对比 A 手写解析(推荐)/B guessit(+3依赖, 备选)/C 文件兑底/D save_path 只提示/E TMDB P2/F 人工纠偏 P2; 用户拍板"同步分支 develop + 按推荐来"。同步受阻: develop 被主 worktree D:/Projects/auto-qb 占用(本 worktree 无法检出), 且 develop==frontend/develop 同指 f4c01db, 本地领先远端(代理断连无法 pull, 但 origin/develop 是祖先无新内容), 遂在 frontend/develop 上实施。实施: M1 tvshows.py(解析矩阵 66 测)→M2 web_view 接线(_build_shows_view/state.shows/文件兑底钩子, test_web +3)→M3 atlas 前端(viewMode 三态/SHOW_COLUMNS/整集右键/未识别桶)→Edge CDP 冒烟 17/17(抓出真 bug: 展示名未美化点分隔符、平局兜底被排序方向翻转、冒烟假服务缺主循环线程致文件兑底链路不可达 — 兑底断言改为轮询等待)。踩坑: ① PowerShell Get-Content 无 BOM 按 GBK 误读 UTF-8 → 写回把 style.css 中文注释写坏(git checkout 恢复, 后改用 python patch 文件); ② python -c 内联中文同样被 GBK 搞坏(一律用 UTF-8 patch 文件); ③ Edge 由 node spawn 起不来, Start-Process 外部启动 + CDP 端口参数可行; ④ 冒烟缺集预期没算上季包覆盖(E01-E03 包展开后缺 E04+E06 两集而非一集)。pytest 942 全绿(基线已回写 testing.md), 未提交。
