# Active Context — 当前焦点

> Memory Bank 核心文件之一: 回答「现在正在做什么 / 上次做到哪 / 下一步从哪继续」。**每次会话开始先读本文件。**
> 稳定事实在 [projectbrief.md](projectbrief.md) / [productContext.md](productContext.md) / [systemPatterns/_index.md](systemPatterns/_index.md) / [techContext.md](techContext.md) 与各主题文档;
> 已完成状态在 [progress/_index.md](progress/_index.md), 陷阱与判据在 [pitfalls/_index.md](pitfalls/_index.md)。
> 本文件**只放易变的会话级状态**, 且**硬顶 12 KB**(守卫 `test_kb_active_context_within_cap`) —— 超了就是内容该外迁的信号。
> 维护纪律(完整规程见 [memory-bank skill](../.agents/skills/memory-bank/SKILL.md)):
> ①每次会话收尾更新本文件; **已完成条目沉淀到 [progress/](progress/_index.md) 或主题文档后从本文件删除**;
> ②命中立档阈值的任务在 [tasks/](tasks/_index.md) 立档并同步索引;
> ③**禁止**在本文件追加长流水账纪要 —— 那是 2026-09-17 那次膨胀 10 倍的直接原因, 现已由 cap 守卫兜住。
> ⚠ 下面的「最后更新」是**滚动状态**(每轮会话替换上一轮), **不是档案** —— 要回查「某次改动何时入库 / 带哪个 sha」,
> 请看 [tasks/_index.md](tasks/_index.md) 各档案的「进度日志」段或 [progress/_index.md](progress/_index.md)。

**最后更新**: 2026-09-23 00:15 (**部分种子 HR 在线核实: 计划 v1.1 + BTSchool 实验脚本 scripts/ + --auto-cookie 全自动通道** ——
  计划 v1.1: HR 页八字段确认入模 (HR 编号/名称/上传量/下载量/分享率/还需做种/完成/剩余达标),
  (站点, tid) 主键跨站隔离 + infohash 回填 + hr_downloaded 防重下永久层
  → [计划](../docs/plans/26-09-22-2204-partial-hr-site-verify-plan.html) ·
  [档案](tasks/26-09-22-backend-partial-hr-verify.md);
  本 clone fetch + merge --ff-only 同步两次 (49eacb8 → 2c5eaa5, 途经行尾幽灵 M 用 add+reset 刷新);
  实验脚本 --auto-cookie 全自动 CDP 通道实测通过 (无头拉起→CDP 抓取→干净报错→清理零残留), 仅剩首次人工登录;
  selftest 11/11 + 离线样张解析 1 行全字段正确 + 全量 1189 passed + 1 skipped (TOTAL 91%)。
  其前一条状态: 2026-09-22 23:59 (**产出 activeContext 多 clone 冲突治理计划并立档, 待拍板实施** ——
  根因: 多 clone 并行下 activeContext.md 为全体收尾必写热点; 推荐按 clone 拆文件 + 生成式聚合索引 + merge-tree 预检,
  W1–W4 波次 → [计划](../docs/plans/26-09-22-2350-activecontext-conflict-plan.html) +
  [档案](tasks/26-09-22-memory-bank-activecontext-conflict.md)(Pending)。仅文档, 未改代码。)
  其前一条状态: 2026-09-22 23:47 (**软件版本管理方案已出, 待拍板** —— 0.x 语义化 + __init__ 单源 + 手工三步发版 +
  Keep a Changelog + v0.2.0 基线 tag, 3 决策点 → [档案](tasks/26-09-22-deps-version-management.md)。)
  其前一条状态: 2026-09-22 23:44 (**README 按用户视角重写** —— 亮点前置 + 删实现细节, 27KB→13.5KB, 机检过。)
  其前一条状态: 2026-09-22 23:1x (**方案 C 目录分层归拢 W1-W4b 入库** —— webui/{server,static,runtime} / tray/ /
  infra/ / core/ 四波零行为变更, 全量 1189 passed; 坑实录 [pitfalls/git/package-move-imports.md](pitfalls/git/package-move-imports.md)。)
  其前一条状态: 2026-09-22 22:38 (**入池 feat issue: 跨组文件交叉紧急处置** —— 分组键不拦跨组交叉,
  已入池 26-09-22-2221 (Open); 仅 issues 池文档。)
  其前一条状态: 2026-09-22 22:19 / 21:58 (**README+configuration.md 文档同步 / 开工同步规则修正** ——
  详单见入库提交 a61d0f4 / e50755d。)

## 正在进行

- **🆕 部分种子 HR 在线核实 (2026-09-22)**: 计划 v1.1 待拍板 (开放问题 4 条: 首批站点 / 频度默认 /
  unknown_policy / cookie 分期; 字段与防重下已确认入模); BTSchool 实验脚本已产出 (--auto-cookie
  全自动 CDP 通道实测通过, 在线待首次登录验证);
  [计划](../docs/plans/26-09-22-2204-partial-hr-site-verify-plan.html) · [档案](tasks/26-09-22-backend-partial-hr-verify.md)
- **🆕 activeContext 多 clone 冲突治理 (2026-09-22, 计划已产出待拍板)**: 根因 = 并行会话状态塞进单文件串行媒介
  (全体收尾必写 + 「最后更新」滚动栈同段重写); 推荐按 clone 拆文件 + 生成式聚合索引 + merge-tree 预检,
  W1–W4 波次待实施, W1–W3 须连续入库
  → [计划](../docs/plans/26-09-22-2350-activecontext-conflict-plan.html) ·
  [档案](tasks/26-09-22-memory-bank-activecontext-conflict.md)(Pending)
- **🆕 软件版本管理方案 (2026-09-22, 待拍板)**: 「版本管理」立项 —— git 健在, 空白在软件版本/发布层
  (0 tag / 无 CHANGELOG / 双源漂移 0.1.0 vs 0.2.0); [方案](../docs/plans/26-09-22-2318-version-management-plan.html)
  推荐 0.x 语义化 + __init__ 单源 + 手工三步发版 + Keep a Changelog + 打 v0.2.0 基线 tag;
  3 个决策点待拍板, 阶段 0 不涉码 → [档案](tasks/26-09-22-deps-version-management.md)
- **🆕 跨组文件交叉检测 (2026-09-22, 已入池待认领)**: 分组键不拦跨组文件交叉(部分重叠文件列表 /
  大小写不同文件名 / junction·symlink 别名路径), 现有三条防线(组内大小一致性 / 同组下载冲突 /
  缺文件扫描)全以同组为边界; 建议方向: 全局物理路径映射检测 + 警告暂停, 细节开工拍板
  → [issue 报告](issues/26-09-22-2221-feat-cross-group-file-conflict.html)(Open)。
- **README 用户视角重写 (2026-09-22, 九轮完成)**: 砍实现细节 / 亮点前置 / 删 Web UI 详情章 / 开发测试去贡献者规范(见「最后更新」)。
  范围外残留待拍板: memory-bank keys.md 运行时文件表仍有 `web.py` 字样; AGENTS.md「testing.md 顶部」旧指针(存根可跳转, 危害低)
- **🆕 qB 移动 .!qB 误判缺文件 (issue 26-09-21-0219) 已认领, 计划待过目 (2026-09-22)**: 过渡态容忍 + 连续 3 次上限;
  [计划](../docs/plans/26-09-22-2038-qb-move-dot-qb-suffix-fix-plan.html); 用户确认后实施, issue 已置 In Progress
- **config 取值范围收紧 (2026-09-22, 随合并入库)**: issue [26-09-22-1937-bug-config-value-range-validation](issues/26-09-22-1937-bug-config-value-range-validation.html) 已置 Fixed。
  收紧清单: `interval` 1s-1D / `main_tick` 0.5s-1H / `sync_interval` 1s-10M / `max_tasks_per_tick` 1-500 /
  `log.max_bytes` 1MiB-1GiB(0=RotatingFileHandler 从不轮转) / 站点 hr `required_share_ratio` [0,100] 拦 nan/inf /
  `hr.condition` 百分比 (0,100] 与下载量 >0(`utils.parse_hr_condition` 解析单点拦) / `notify.max_per_hour` ≤100 /
  `dedup_window` ≤24H(0=不去重仍合法) / 规则 `interval` 显式 0 拦 —— **缺省 0S=每 tick 级别是既有行为未动**,
  是否收紧属行为变更待拍板。机制文档已回写 [config-reference/loading-and-write.md](config-reference/loading-and-write.md)
  「校验范围 · 取值范围」条。
- **web.py→web/ 包拆分 —— 已入库(本条随提交走)**: 零行为变更纯结构重构; 守阵 2 条红验
  (金清单 60 条 / 组装壳 ≤150); 全量 1188 passed + 1 skipped; 冒烟 70×2 全绿。三条安全
  发现(S1-01/02/05)可在 auth.py/events.py/system.py 局部落刀(上游已修 S1-05 脱敏, 见
  44c1a0f)。剩: push 后真机无需走查(行为零变更, 冒烟已覆盖)。
- **后端状态周期落盘 —— 已实施并入库 (2026-09-22)**: issue 26-09-21-1347 修复完成 —— 新键
  `state_save_interval`(默认 120s/下限 30s/0=关) + 主循环周期落盘 + skip_check_day/recheck_fails 即时落盘;
  红验通过(修复打回 → 3 条守阵全红); issue 已标 Fixed
  → [计划](../docs/plans/26-09-22-1912-backend-state-periodic-flush-plan.html)
- **设置页 Console Hub 卡片标题暗色下发黑已修 + 卡片静息发光 (2026-09-22, 已入库 `c31ee0d`, Gitee + GitHub 镜像均已推)**:
  ① `.hb-card` / `.hb-row-hit` 是 `<button>` 且未显式设 `color`, 文字色回退 UA 默认 `buttontext`
  (系统浅色 = 纯黑), 已在 `shared/console_hub.css` 补 `color: var(--fg)`;
  ② 应用户要求卡片静息即发软光(`--glow-soft` 提到静息态), hover / 聚焦升全光(`--glow`), 数值沿用配方不自造。
  全量 1176 passed + 1 skipped。坑已记 [pitfalls/web-ui/layout-css.md](pitfalls/web-ui/layout-css.md)。
- **🆕 设置页伪警示已定性并入池, 暂不施行 (2026-09-22)**: 首页警示条由『已配置且 schema 带 risk 文案』驱动,
  恒亮、静态、与配置健康无关; 且 load_config 对 schema 外键静默忽略(升级失效键无提示)。
  方向已与用户讨论: 撤伪警示 + 后端 unknown-key 收集 → warnings 分级 → 警示条渲染 warnings。
  详见 [issues/26-09-22-2002-bug-webui-config-health-warning.html](issues/26-09-22-2002-bug-webui-config-health-warning.html)(Open)。
- **memory-bank 目录化重构 W0–W8 已全部入库**(2026-09-22) —— 方案、逐波实测与检索演练见
  [档案](tasks/26-09-22-memory-bank-dir-refactor.md) ·
  [计划](../docs/plans/26-09-22-1248-memory-bank-dir-refactor-plan.html)

- **① 上轮计划复核的收尾(只剩第 7 项) (2026-09-19)**: 复核报表

## 待用户真机走查

> 整段(约 15 KB / 100 行)**已迁至 [checklists/manual-walkthrough.md](checklists/manual-walkthrough.md)** ——
> 它是**清单**(逐项勾选), 读的时机是「做真机走查时」, 不是「每次会话开始」。
> ⚠ 其中绝大多数是**前端观感项**, 语料回放测不到 —— 已在那边按「数据面 / 观感」分过档。

## 定案口径 (别改回去)

> 逐条已归位, 本文件只留指针(**改之前先读目标文件, 不要只看这一行**):

- **列偏好"升版本" / 双轨模型 / localStorage 两种重置 / 已知限制** →
  [pitfalls/web-ui/columns-persist.md](pitfalls/web-ui/columns-persist.md)。
- **行宽口径 / 表头吸顶 / 列对齐**(第十一轮定案) → [pitfalls/web-ui/layout-css.md](pitfalls/web-ui/layout-css.md)。
- **开工先同步(fetch+ls-remote+ff-only) + 提交即推送 / 跨仓库操作** → 单点在根 [AGENTS.md](../AGENTS.md)
  (「会话协议 · 开始」与「提交 / PR」与「🔴 跨仓库操作」); 细则在 [conventions/collaboration.md](conventions/collaboration.md)「协作约定」。
- **工作区模式: 多 clone 并行 (2026-09-20 用户拍板, **git worktree 已弃用**)**: 每个 AI 实例一份**完整克隆**(各自独立 `.git`), 跨工作区同步一律走 Gitee `develop`; 单点在 `AGENTS.md`「环境硬约束」与 `conventions.md`「协作约定」。原 8 个 worktree 目录已打包存档到 `D:/Projects/_archive/auto-qb-worktrees-2026-09-20/`(含 `MANIFEST.md` 与 `sha256.txt`), 目录已移除(5 个进回收站, `auto-qb-other` 因回收站报"不支持该功能"改移到存档区 `_removed-dirs/`), 8 个本地分支已删除 —— 删除前已核验全部 `ahead=0`, 无独有提交。新布局为 `D:/Projects/auto-qb`(主) + `auto-qb-clone1` / `auto-qb-clone2` / `auto-qb-long-seeding`。
- **`想法.md`**: 工作区**干净**(最后一次入库 `3bface9`)。它属于红线文件(与 `config.yml` / `auto-qb-data/` 同级),
  提交前照例用 `git status --short` 确认一遍是否又有改动, 不进暂存区。

## 下一步候选 (来源: `想法.md` 待办 + progress/roadmap.md)

- **上轮复核的收尾**(见「正在进行」第 ① 条) —— 只剩报表 §08 第 7 项(节拍对齐, **需先拍板方向**)
  与同类端点的同样改法(低优先); 第 1、2 批与 §11 已实施未提交
- WEB UI: WebSocket 推送; 多用户; **设置页全面重构**(`想法.md` 现存最大一条未做项)
- WEB UI: 窗口日志等级可选; 星图侧补齐第九轮的纯版式项(棱镜已做: FX-05/06/09/17~25)
- 规则系统: 条件取反 (`!`/非 logic); 重新梳理 ignore_next_action_error / stop_following_rules_if
- tracker 分组前端增强 (阶段 2/3, 2026-09-15 拍板后续): 设置页 groups 下拉快捷追加 (rules_ref 风格); 辅种管理页按组筛选 (web_view 透出 conf.groups + app.js filterDefs)
- 其它: 切分大文件; 种子未变动时不触发内置维护任务; 命中限速曲线强调显示; 插件系统
- 🚧 实机验证: README 标注 🚧 的功能 (alpha 阶段), 生产使用前先 `--dry-run` 观察

## 历史归档 (已迁出本文件)

2026-09-14 ~ 2026-09-19 的全部会话纪要已按专题迁移到 [tasks/](tasks/_index.md) 各档案的「历史会话纪要 (原文归档)」段(原文未删改), 或已沉淀进 [progress/_index.md](progress/_index.md) 的「已实现」段。
需要回查历史请走 `tasks/_index.md` 定位专题档案; 本文件只保留**当前焦点**。
