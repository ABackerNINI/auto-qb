# 给 AI 的实现建议

> 摘要: 基于现有架构的延伸方向 —— 动手改架构 / 工程化前先看这里有没有既定建议。
> 触发: 实现建议, 延伸方向, 工程化, 知识库改进, 架构建议

## 给 AI 的实现建议 (基于现有架构的延伸方向)

- **新触发时机** (`on_torrent_added`): `_refresh_torrents` 的 added 循环已经是事件点; 按 09 事件触发规划, `_dispatch_events` 同步分派 added 事件规则 (不建周期任务), 复用 `_apply_event_rule` + rule-event origin 机制。
- **状态变化触发** (`on_torrent_state_enum_changed`): `store.state_snapshot` 已保存上一轮枚举状态, `_handle_state_transitions` 是现成的"状态转移检测"参考实现 (grouping 内部用); 事件分派用它对比上轮/本轮状态枚举筛选触发。
- **删除触发** (`on_torrent_deleted`): 用 `store.refresh` 返回的 removed 及其删除前快照副本触发; 白名单只允许 `print_torrent_details` 只读留档。
- **新流量源**: `curves.py` 保持无项目内依赖; 数据源解析独立成函数返回 `List[HistoryRow]` 即可复用 aggregate/curve_speed 全链路。

### 工程化 / 知识库（2026-09-20）

- **create-issue skill 类型化改造（已实施）**: 计划 [26-09-20-0941](../plans/26-09-20-0941-issue-typing-plan.html)。
  ① 8 类类型进文件名第二段 `<时间>-<type>-<slug>.html`（bug / perf / docs / test / refactor / feat / chore / question，
  枚举单点在 `scripts/_common.py` 的 `TYPES`）；② 表单分两档 —— `light` 便签（现象一句话 + 位置，≤2 分钟）与
  `standard` 标准（现象 / 证据 / 影响面 / 定位锚点，≤10 分钟），根因与建议修法一律降为可选、默认"待查"；
  ③ 防过期五条（只记事实不记结论 / 行号标"当时"+ 符号 + grep 词 / 不为填单做分析 / 证据标取证时间 / 开工先复验）；
  ④ 通用化 —— meta 去 `aqb-` 前缀改 `issue-*`，目录 `--dir`（不传按 memory-bank/issues → issues → docs/issues 探测）、
  仓库根改 `.git` 向上探测（不再 `parents[4]`）、品牌 `--project` 可选注入、索引 HEADER 链接动态计算；
  ⑤ 存量 8 份报告已迁移（bug 4 / perf 3 / docs 1），17 处外链同步，索引顶部有 Open 按类型计数表。
  文件名与状态取值由生成器守卫（`--check` 可挂 CI）。单测 **1057 passed** 不变。
- **提交推送流水线 skill（已实施，2026-09-20）**: 提案 [26-09-20-1128](../plans/26-09-20-1128-git-ship-skill-proposal.html)，
  落地 `.agents/skills/my-commit-flow/`（七步：预检 → 闸门 → 逐路径暂存 → 提交并核 ref 三处 → 推 Gitee 主线
  → 尝试一次 GitHub 直连 → 查幽灵 diff）。脚本 `preflight.py`（只读预检）/ `commit.py`（逐路径 add + commit，
  **拒 `-A` / `.` / `*` 与红线文件**）/ `verify_ref.py`（ref 三处一致）/ `push.py`（先 fetch → 推主线 → 核对远端
  → 镜像直连只尝试一次），配置单点 `scripts/_ship_config.py`。
  停手点：rebase / 混入他人在途改动 / staged > 200 / ref 不一致 / 镜像失败 / 闸门未过 —— 脚本只报不碰。
  已回写指针：AGENTS.md 提交节 + 环境硬约束 + 路由表、memory-bank/README.md 路由表、memory-bank skill 会话开始第 1 步。
  **通用性有限**（依赖本仓环境：工具 shell 拦截层 / Gitee+GitHub 双远端 / 多个工作区并行 (2026-09-20 起为多 clone)），换项目先改 `_ship_config.py`。
  提交 `0c0bf1e`，用它自己的流水线提交（dogfooding），Gitee 与 GitHub 均推成功。

- **HTML 文档统一 dark 主题（已实施，2026-09-20 13:00）**: 用户指定"产出的 HTML 一律 dark"，已写进
  `AGENTS.md`「计划产出」节（深色底 + 浅色字 + `color-scheme: dark`，禁止浅底黑字）。存量同步：
  `memory-bank/plans/` 25 份中 9 份浅色计划文档（`26-09-15-1150 / 1241 / 1504 / 1534`、`26-09-16-1128`、
  `26-09-17-0346`、`26-09-19-1745 / 2245`、`26-09-20-0906`）重写 `:root` 配色盘转深色（保色相、
  只翻明度），另给 14 份原本就深色但缺声明的补了 `color-scheme: dark`；`memory-bank/issues/` 9 份
  本就是深色、未动。`resources/`（设计观摩稿 + 设置页候选稿）按用户裁定**不在本次范围** —— 那批的
  白底极简（kenya-hara / pentagram / muller-brockmann）是设计本体，转深会毁掉参考价值。
  单测 **1059 passed**。

- **提交信息改 gitmoji + 中文口径（已实施，2026-09-22）**: 来源 `github/awesome-copilot` 的 `skills/gitmoji/`
  （MIT），落地 `.agents/skills/gitmoji/`（`SKILL.md` + `references/gitmoji-reference.md`，官方 75 个 emoji 全表，
  与上游逐字一致，仅多 `user-invocable: true` 一行对齐本仓库写法）。口径单点定义在 `AGENTS.md`「提交 / PR」：
  首行 `<gitmoji> <中文一句话概述>`，空一行后写动机 / 取舍 / 影响面 / 实测数字，**一个提交只用一个 emoji**
  （具体优先于笼统：小修 🩹 而非 🐛）；路由表新增「写提交信息 / 选 emoji」行；`conventions.md` 两处同步为指针。
  **未动 `.agents/skills/my-commit-flow/`** —— 通用资产不写项目事实，其 S4 与 gitmoji 前缀兼容。
  闸门实测 `check_context_caps.py` → AGENTS.md 7112/8000（余量 888）。提交 `f093d22`，Gitee 与 GitHub 均推成功。
  ② **知识库回写随主提交（同一天定口径）**：原先一次改动要两笔（`f093d22` 主提交 + `1b735e6` 回写），
  根因不是「拆分」口径 —— `conventions.md` 只是**认可**拆分；而是 `my-commit-flow` 的 **S7 把「回写知识库」
  排在推送之后**，已推送又不能 amend 强推，只能补第二笔。改为**先回写再提交**：S3 加「暂存前先把收尾做完」、
  S7 只留查幽灵 diff、新增《提交前先收尾》小节、反模式加「推完才回写」；项目侧 `AGENTS.md` 加
  「提交前先收尾」、`conventions.md` 第 18 行加例外。顺序固定为
  **改完 → 闸门 → 回写 → 暂存 → 提交 → 推送 → 查幽灵 diff**。
