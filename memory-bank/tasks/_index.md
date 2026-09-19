# Tasks Index

> **本文件是生成物, 不要手改** —— 由 `scripts/gen_tasks_index.py` 扫描 `tasks/*.md` 的 `Status` / `Summary` / 标题生成; 新增或改状态后跑 `python scripts/gen_tasks_index.py` 重建即可, 合并冲突也只需重跑。
> 档案命名 `YY-MM-DD-<slug>.md`(见 [memory-bank skill](../../.agents/skills/memory-bank/SKILL.md)); 旧编号保留在各档案的 `**Legacy-ID:**` 字段, 供历史文档回溯。
> 粒度为**专题**(一个功能线一个档案, 不逐会话建文件); 历史流水账原文归档在各档案的 `## 历史会话纪要 (原文归档)` 段。
> 日常短周期工作只记 [../activeContext.md](../activeContext.md); 完成项沉淀进 [../progress.md](../progress.md)。
> 机械守卫: `tests/test_memory_bank.py`(索引 == 生成结果 / slug 唯一 / 命名规范 / 状态分区 / 必备章节)。

## In Progress

- [26-09-18-test-sidefx-guard] 测试期真实系统副作用收口 (通知框 + 环境依赖假失败) - 真凶 `test_cli.py::test_main_qb_compat_error_clean_exit` 用 MagicMock 当配置 ⇒ 绕过 `notify_fatal` 守卫真发 Windows toast; 修 mock + 新增 `tests/conftest.py` 会话级通知器命令拦截; 另修 2 个环境依赖假失败(`APPDATA` 未设 / 沙箱把 `os.symlink` 落成真实目录) + `.gitignore` 补 `.coverage.*`; **1007 passed / 0 failed**; **已入库 `7ae21a1`** (剩用户再跑一次测试确认不再弹框)
- [26-09-18-webui-error-reason] WEB UI 错误种子显示具体原因 (状态列 `error_reason`) - 状态列由笼统「错误」改为具体原因(`missingFiles`→"文件丢失" / `error`→tracker `msg` 原文); 后端 `refresh_error_reasons` 主循环 TTL(300s)+预算(5/轮)预取 + 显式置脏, 视图透出 `error_reason`, 前端 `stateText` 双 UI 生效; 1006 passed, 假 qB 服务浏览器冒烟实测; **已入库 `9723a76`** (剩用户真机走查)
- [26-09-18-webui-view-rebuild-scope] WEB UI 视图重建范围收口 (种子速度刷新滞后) - 真因: 主循环 `_tick` 只重建 `_group_view` 却清掉共享脏标记 ⇒ singles/shows/flat 被饿死(版本号照常自增 ⇒ 前端换上陈旧数组), 状态栏因取 groups 求和反而正常; 同源: 置脏在 grouping 门控内 ⇒ 分组关闭时标记被吞。修法: 唯一入口 `rebuild_views()` + 置脏移出门控 + 前端取消 idle 退避并把 `server_state` 并入 `/api/state`; **1021 passed / 0 failed** (基线 1018, 红绿验证); **未提交** (剩用户真机走查)
- [26-09-15-webui-qb-replacement] WEB UI 替代 qB 界面 (波次一 ~ 波次三 + 复查) - 32 工作项双 UI 同构 + 两大根因修复完成; 剩实机 CDP 双 UI 走查 + 真机 dry-run + prism 追剧模板, **未提交 git**
- [26-09-17-memory-bank-trigger-fix] Memory Bank 触发机制修复 (skill 缺失 + 立档纪律失败) - skill 载体 + always-on 阈值 + TASK001~TASK009 回填 + activeContext 瘦身 + 守卫测试完成; 待提交
- [26-09-17-webui-component-libraries] UI 组件库 20 式 (设计风格库落地为可挑选的组件库) - 按设计哲学风格库 5 流派 × 20 preset 各出一套自包含组件库单页 + 挑选索引 + 目录 README (`resources/ui-component-libraries/modelscope.dsv4.1flash/`); 四轮自检 + 7 项缺陷修复; 996 passed; 已提交 `fae019a` (剩用户挑选与按需迭代)
- [26-09-17-webui-fix-round10] WEB UI 第十轮修复 (16 项 · R10-01~R10-16) - 状态栏三项硬 bug(限速取数单点/星图双窗/免鉴权放行) + 列对齐进列模型 + 列偏好不重置 + 服务端目录浏览与 open-path 定位选中 + 弹窗尺寸令牌族; 999 passed, 双 UI 浏览器冒烟逐项实测通过; **已入库 `cb57bef`** (含真机走查 r1 反馈两处)
- [26-09-17-webui-fix-round11] WEB UI 第十一轮修复 (7 项 · 图标着色/明细排序/滚动条) - 图标着色(导航/状态栏) + 历史去文字 + 明细表点击排序 + 辅种表加保存路径/明细表删列 + 两个横向滚动条根因(表头撑页 / `.detail` 自成滚动 / 单元格 min-width) + 标签分类芯片改状态色; 999 passed, 双 UI 冒烟逐项实测; **已入库 `4a027ef`**
- [26-09-17-webui-fix-round9] WEB UI 第九轮修复 (25 项 · FX-01~FX-25) - 口径单点化 + 浮层锁定契约 + 选择模型互斥/派生 + 删除链统一 + 菜单分层 + 新端点 `/api/open-path`; 996 passed, 浏览器冒烟 25 项全过; 已提交 `49d3151` (剩用户真机 dry-run)

## Pending

- [26-09-19-webui-responsiveness] WEB UI 操作跟手性优化 - 用户报「WEBUI 操作不跟手」。链路剖面定位四类根因: ①命令要等主循环 main_tick(默认 2s)才被 drain ②waitCmd 首查前固定睡 500ms 且全程无即时反馈 ③每 2s 全量回传四视图 + 单个巨型 Vue 实例整树重渲染(种子页无虚拟化) ④bulkAct 逐目标 POST ⇒ 后端 N 次 qB 串行调用阻塞主循环。计划含 P0×5 / P1×5 / P2×4 共 14 项、三波次、验收口径与红线

## Completed

- [26-09-19-webui-cols-store-version-audit] WEB UI 列状态存储键 `autoqb_cols_v?` 版本沿革审计与口径回写 - 用 `git log -S` 逐键追溯列状态存储键的 4 次升版本(v1→v4, 集中在 2026-09-13 08:32 ~ 09-14 07:25), 确认 v4 之后 R10-09(`cb57bef`)已把政策反转为"列集变更一律不升版本"; 据此回写 `pitfalls.md`(2 处) / `systemPatterns.md` / `activeContext.md` 三条仍写着"加/减列**必须**升版本"的旧口径, 并补一条"不并发也会偶发的全量失败"判别法; 测试基线 1041 passed 不变。
- [26-09-14-memory-bank-migration] 知识库 (Memory Bank) 建设与仓库治理 - `ai/` → `memory-bank/` 六核心文件迁移 + 跨 agent 入口统一 + 测试基线单点化 + worktree 同步 (2026-09-14 ~ 09-15)
- [26-09-15-backend-file-split] 后端大文件拆分 - `qbmanager` / `schema` / `torrents` / `validation` 四包拆分, 纯移动零行为变化; 遗留: 既有测试顺序污染待排查 (2026-09-15)
- [26-09-15-backend-torrentrecord-fields] TorrentRecord 全字段缓存 (快照 21 → 70 字段) - 快照 21 → 70 字段 (`_raw` 降为兜底) + `to_dict()`; 基线 879 (2026-09-15)
- [26-09-15-deps-env-modernization] 依赖管理与运行环境现代化 (uv / pyproject / venv 重建) - `pyproject` + `uv.lock` + CI 切 uv + 7 个 worktree venv 重建; 遗留: 无 (2026-09-15)
- [26-09-15-docs-restructure] README 重构与配置文档分离 - README 29KB→10KB + 抽出 `docs/configuration.md` (2026-09-15)
- [26-09-15-rule-tracker-groups] tracker 分组 (站点 groups 字段 + tracker_group 条件) - 后端与条件插件完成入库, 条件 15→16; 遗留: 阶段 2/3 前端增强待排期 (2026-09-15)
- [26-09-15-webui-polish-and-redesign] WEB UI 打磨轮次与棱镜重设计 (第六 ~ 八轮 + 双界面命名) - `atlas`/`prism`/`shared` 目录化 + 五主题令牌 + 各轮冒烟全绿 (2026-09-15)
- [26-09-15-webui-tvshows-view] 追剧视图 (tvshows) - 剧/季/集解析 + 缺集计算 + atlas 三态视图, 已合入 develop; 遗留: prism 模板欠账 (2026-09-15)

## Abandoned

(暂无)
