# 已实现 · 依赖 / 知识库 / CI

> 摘要: 摘要: 依赖现代化与知识库机制本身的落地记录。
> 触发: 做过没有, 依赖, uv, 知识库, 立档, 索引, 瘦身, skill 瘦身, references, 上限

## 已实现 (✅, 有单测覆盖)

- **memory-bank 四工位导航页 · 三视图可切换 (2026-10-04, 计划 26-10-04-0952 全段落地)**: issues / plans /
  reports / tasks 的状态与关联做成本地导航页, 主视图三套并存(台账 / 控制台 / 卡片墙)顶栏一键切换(选择记忆
  localStorage, file:// 降级)。数据层 `nav_data.collect_nav()` 复用 `gen_doc_map.collect()` 做**薄 enrich**
  (issue 补 issue-type / issue-tier / issue-summary, 全形态补 doc-updated 缺省回落 stamp; 派生 topics[](live
  口径同 is_live)与各形态 x 状态 counts), **不改 collect() 本体**(闸门/守阵消费单点, 键集合由守阵钉死);
  stamp 取数据自带 doc-updated 最大值, 不生成依赖当前时钟的内容。服务层 `nav_server.py` 纯 stdlib
  http.server 绑 127.0.0.1:8765(allow_reuse_address 必须关 —— Windows 上 REUSEADDR 会让同端口双绑静默成功),
  但**浏览器打开的地址用 localhost:8765**(`OPEN_HOST`, 2026-10-04 起; 127.0.0.1 那个 origin 有历史遗留, 换
  localhost 拿干净 origin —— 监听仍只绑回环 IPv4, localhost 解析回落即达):
  `/` 页面壳 + `/api/data` 每请求现算(前端 30s 轮询准实时) + `/memory-bank/<path>` 静态映射(resolve 后必须
  严格落在 memory-bank/ 内, 越界一律 403, ../ %2e%2e ..%2f 反斜杠变体全拒)。壳 `nav_page.html` 入库
  scripts/(http 模式 fetch + 轮询; 静态模式 `--gen-static` 注入单文件, 默认 tmp-analysis/nav/ 已 gitignored);
  `color-scheme: dark` 零外链资源。挂点 `commands run kb.nav`(前台长跑 Ctrl-C 停)。守阵
  `tests/test_kb_nav.py` 9 条: 数据形状 / issue enrich / stamp 防时钟 / collect() 键集合不回归 / 壳三视图
  容器+dark+零外链 / 服务层三路由与防穿越, 全桩目录零网络外呼零子进程。基线 2471 passed + 4 skipped /
  覆盖率 99%(切片 26-10-04-1039)。计划
  [26-10-04-0952](../plans/26-10-04-0952-plan-kb-nav-page.html)。

- **kb.nav 台账置顶 (pin) (2026-10-04, 专题 kb-nav-pin, 计划 26-10-04-1830 全段落地)**: 导航页台账新增人工置顶 ——
  行内图钉 (空心 = 未 pin / 实心 = 已 pin, 点它切换) + 「置顶 · PINNED」**增量专区** (被 pin 件**同时**留在原表格
  = 双向显示, 专区不受筛选/搜索影响) + 右键菜单 (置顶/取消置顶 · 打开原文 · 复制仓库路径)。pin 是**人的视线偏好**、
  非文档属性: 落 localStorage `mb-nav-pins`(与视图选择同款 try/catch 降级), **只在 boot 装载一次、derive() 绝不触碰**
  (同「状态筛选器自动重置」源风险, 坑档案 poll-reseed-filter.md), 不写进任何件 meta、**数据层/服务层零改动**。图钉
  内嵌 title-cell (零列序改动, 不新增 td), 内联 SVG 无外链图标库、无 emoji。守阵 `tests/test_kb_nav.py` +4(专区/菜单
  骨架 · derive 不碰 pins 且装载点唯一 · 双向渲染 · 内联 SVG 无 emoji)。基线 2515 passed + 4 skipped / 99%
  (切片 26-10-04-1849)。计划 [26-10-04-1830](../plans/26-10-04-1830-plan-kb-nav-pin.html)。

- **activeContext 多 clone 冲突治理 = 时间戳切片方案 (2026-09-23, W1–W3)**: 「重写头部滚动栈」改成
  「新增/更新自己的时间戳切片」; 取消 global.md/_index.md/_recent.md 缓存(文件名自带时间与主题,
  `kb.active` 现算); 归档阈值 14 天默认落地(`--stale-days` 可调)。W4(merge-tree 预检 + rerere)可选未做;
  当时的遗留红灯(tasks/_index.md 超 cap)早已随后续收口消解。计划
  [26-09-22-2350](../plans/26-09-22-2350-activecontext-conflict-plan.html); 档案
  [tasks/26-09-22-memory-bank-activecontext-conflict.md](../tasks/26-09-22-memory-bank-activecontext-conflict.md)。

- Memory Bank 任务档案命名重构 · 去序号化与索引生成化 (2026-09-18): `tasks/TASKnnn-<slug>.md` → `tasks/YY-MM-DD-<slug>.md`。**动因**: 全局单调序号在 9 个并行工作区 (当时是 worktree, 2026-09-20 起改多 clone) 下必然撞号 —— 实测 TASK014/TASK015 同一专题两份且 md5 一致、zcode 分支把同一提交 `fae019a` 编成 TASK012 而主线编成 TASK014(**同题异号**)。**方案**: 文件名 = 日期到天(不带时分) + 专题 slug, 由专题派生而非发号; 同日同专题必然撞同一路径, 重复当场暴露为显式 add/add 冲突; 跨天同专题由新增守卫 `test_slug_is_unique_ignoring_date_prefix`(比对时忽略日期前缀)拦下。**索引生成化**: 新增 `.agents/skills/memory-bank/scripts/gen_tasks_index.py`(2026-09-22 从仓库根 `scripts/` 迁入) 扫 `Status` / `Summary` / 标题按四状态分区生成(分区内按 `Updated` 倒序, 活跃度不靠创建日), `_index.md` 降级为**生成物**, 合并冲突只需重跑脚本; 新增守卫 `test_index_is_regenerated` 保证没人手改。**迁移**: 17 个档案 `git mv` 改名 + 补 `**Summary:**`(摘要由旧索引迁入) 与 `**Legacy-ID:**`(旧号回溯) + 标题行同步; 全仓 9 个文件的路径引用同步修正(只改路径, 历史叙述中的旧编号保留, 靠 Legacy-ID 回溯)。**规范同步**: 两份 `SKILL.md`(`.agents` / `.codebuddy`)、`AGENTS.md`、`.github/copilot-instructions.md`、`.github/instructions/memory-bank.instructions.md`、`memory-bank/README.md`。**基线 1021 → 1022 passed / 0 failed**。计划 [memory-bank/plans/26-09-18-1928-memory-bank-task-id-plan.html](../plans/26-09-18-1928-memory-bank-task-id-plan.html); 阶段 3(把三个 `webui-fix-roundN` 合并为一份 `webui-polish`)按计划默认**未做**
- Memory Bank 触发机制修复 (2026-09-17): 补建真正的 skill 载体 `.agents/skills/memory-bank/SKILL.md` (会话开始 3 步 / 收尾 DoD 5 步 / 立档阈值 4 条 / 档案规范 / 反模式; 先建于 `.github/skills/`, 同日按仓库技能根惯例搬入 `.agents/skills/`), always-on 入口 (`AGENTS.md` + `.github/copilot-instructions.md` + `ai-lib.md`) 声明**可判定阈值**并指向 skill, `memory-bank.instructions.md` 顶部标注"本文件不负责触发 (applyTo 限定 memory-bank/**)"; 按**专题粒度**回填 `tasks/TASK001`~`TASK010` (30 条历史会话纪要原文按专题归档) 并重写 `_index.md`; `activeContext.md` 68 行 → 26 行 (恢复易变层定位); 新增守卫 `tests/test_memory_bank.py` (6 项, 红绿验证: 幽灵任务与纪要回流两类违例均被拦截); 基线 989 → **995 passed**
- 依赖管理现代化 (2026-09-15): pyproject.toml(PEP 621 + hatchling, 12 直接依赖 == 锁死含 filelock 3.32.6 / uvicorn 0.53.0 最新, dev 走 PEP 735 依赖组, entry point `auto-qb = auto_qb.cli:main`) + uv.lock 全量锁 41 包 + `commands run env.sync` editable 安装(清除旧壳 venv 与约 20 个无关包); CI 切 astral-sh/setup-uv 固定 commit SHA (v10.1.0; 该 action 已不发布 `v10` 浮动标签, 写 `@v10` 会报 "unable to find version v10") + checkout@v6 + setup-python@v7 + uv sync/uv run; `uv build` sdist/wheel 打包就绪; 前置调研 memory-bank/reports/26-09-15-1150-report-dependency-lock.html; requirements-dev.txt 已被 pyproject 取代(随提交删除); README/AGENTS/testing/techContext 同步, 基线 872 passed (uv 环境)
- **skills 全量安全审查 (2026-09-20, ✅ 已提交并推送 `a370354`, Gitee 主线成功; GitHub 镜像滞后 2 个提交)**: 按 skill-vetter 协议审查 26 个技能 —— 唯一红线是 `autoclaw-design-capability` 内 `design-skeletons/last30days` 的 `lib/chrome_cookies.py`(解密 Chrome cookie 取 X 会话 `auth_token`/`ct0`, 仅 macOS 可触发且该包被 sync 排除 ⇒ 不可达), 已**整体删除该骨架**; 另删 12MB 重复副本 `autoclaw-design-capability_noqa`, 同步清理 `sync_agent_skills.py` 的 `EXCLUDED` / autoclaw `INDEX.md`(骨架计数 83→82) / `NOTICE.md` / `pitfalls.md`。3 条次要发现已入池 `memory-bank/issues/`(hatch-pet 付费 API / 写 `USER.md` 口径冲突 / grill-me 空 stub)。审查报告 [memory-bank/reports/26-09-20-1429-skill-vetter-audit.html](../reports/26-09-20-1429-skill-vetter-audit.html)。**已补**: 实跑 `scripts/sync_agent_skills.py` 后 `my-commit-flow` 已链接进 `.codebuddy/skills`(现 24 个, = 25 个顶层 skill 减去被排除的 autoclaw), 读穿校验 OK、无悬空链接; **重启会话后才会出现在技能列表**。
- **skills 瘦身 · "细节外置 references/ + 去空格 + 上限跟着实测收"三件套 (2026-09-24)**: 先做 `commands`, 再按同一思路做 `memory-bank`。
  **commands**: 收录协议细节 → `.agents/skills/commands/references/howto-add-command.md`(1293 字符, **按需读**), SKILL.md **2986 → 2089 字符**(半角逗号/斜杠/括号后的空格 327 → 171 个), `CONTEXT_CAPS` 上限 **4200 → 2600**。
  **memory-bank**: 知识库结构 / 脚本表 / activeContext 切片四条约定 / 检索纪律 / 扩类扩目录 → `.agents/skills/memory-bank/references/kb-structure.md`(3717 字符, **按需读**), SKILL.md **10114 → 5948 字符(-41%)**(空格 1254 → 580), 上限据此定 **7500**(此前无上限)。
  **两条纪律**: ①**上限跟着实测收** —— 不收的话, 省下的会被慢慢吃回去; ②细节搬进 `references/` 后, 反漂移闸门扫描面从 `.agents/skills/**/SKILL.md` 扩到 `.agents/skills/**/*.md`(扩前实测 0 命中, 不误伤别的 skill), 否则搬出去的内容成了闸门盲区。
  **改 memory-bank SKILL.md 前必读的守卫约束**: `tests/test_memory_bank.py` 要求它含 `会话开始` / `立档阈值` / `收尾 DoD` 三个 token, 且 **cap 表必须留在该文件里**(`test_skill_cap_table_matches_cap_policy` 钉住数值集合与行数 == `_common.CAP_POLICY`)—— 所以 cap 表不能像别节那样外置。
  ⚠ **顺带发现(未改)**: 该 SKILL.md 的「收尾 DoD」标题写"5 步"、实际列了 6 条, 而 `AGENTS.md` 也写"5 步" —— 两边同错, 要订正得一起改(本次只把标题里的数字去掉, 不替它选一个数)。
  实测: `test.full` **1201 passed + 1 skipped**; `doc.caps` commands 2089/2600 · memory-bank 5948/7500 · AGENTS.md 6999/8000; `doc.drift` 0 处。
- **知识库瘦身 (2026-09-20, ✅ 已提交并推送 `9ccace6`, Gitee 与 GitHub 镜像均成功)**: 按"过时 / 重复 / 低价值"三分类清理根 `AGENTS.md` 与 `memory-bank/` —— **路由表与黄金法则单点收在 `AGENTS.md`**(`memory-bank/README.md` 改指针), 已完成条目从本文件迁出到 `progress.md` / 任务档案; `testing.md` 顶部基线数字**未动**(待补测 WSL 一侧再更)。提交时与上游 7 个提交 rebase, `AGENTS.md` 一处冲突按"保留上游新增的 HTML dark 主题规则 + 保留本轮压缩后的计划产出口径"解决。**知识库回写(pitfalls 新增「rebase --continue 被 VS Code 编辑器挂死 + packed-refs 陈旧致核 ref 假红」条目 + 本行状态更新)已入库 `060844e`。**
- **commands 引擎的三条已落地约定 (2026-09-24, 从 commands 切片迁出)**: ①**`doc` 键** —— `[tasks.*]` 可写
  `doc = "<包内文档相对路径>"`, `show` 打印"深读"一行, 把"想看细节读哪份"接到决策点上; 基准目录**子包继承父包**
  (否则子包写 `references/pipeline.md` 会 STOP), 指向的文件不存在即 STOP(指针指空 = 静默失效)。
  ②**反漂移豁免不保护包内 README** —— `.commands/` 豁免的理由是"单点定义在这里", 但定义处是 `config.toml`,
  故 `README.md` 不走豁免并加进 `SCAN_GLOBS`。③**阅读预算是一类新上限** —— `check_context_caps.py` 里
  `CONTEXT_CAPS`(IDE 注入截断)与 `READ_BUDGET_CAPS`(被当入口就得整读)**语义不同, 分两组打印**, 判定与处置共用一套。

- **commands W6 会话噪音治理 · 实测记录 (2026-09-24, 从 commands 切片迁出)**: 引擎摘要改成"末几行结论 + 异常行"后实测 ——
  12 行检查表的 `[WARN]` 行**留在了摘要里**(与结论行同时在); 全量测试通过时**不额外抽行**(`run test.full` 输出 338 字符, 与旧行为一致);
  预检经引擎的输出 551 字符(原先要么看不到 WARN、要么整段 2.4 KB)。闸门摘要收敛: `[PASS] 自动闸门 N 条全过 (共 X s)` 一行,
  取代原先把 9~11 条展开后的命令(含绝对路径)拼成的 ≈1.5 KB 单行, 明细走 `--verbose`。
  同步配方端到端: 用 `git commit-tree` + 临时 remote 造「远端领先 1 + 树脏 5」—— 无重叠出 5 步配方, 让假提交改一个**在途**文件
  则改报"重叠 1 个文件 … 先停下报告"且不给施回配方(用完 `git remote remove`)。包测试入闸门: `test.pkg` 经引擎跑 47 passed。

- **commands 引擎 / `my-commit-flow` 包的实测记录 (2026-09-24, 从 commands 切片迁出)**: 以下都是"改之前先确认过的事实", 免得重做 ——
  ①**可插拔**: 临时加包 → 跑通 → 整包删除, 引擎 `list` / `run` 无异常; 往包里塞引擎不认识的私有配置, 引擎不报错也读不到。
  ②**整包移走** `.commands/my-commit-flow` 后, 引擎仍能 `list` / `run` 其它 task。
  ③**反漂移闸门**: 故意手抄 → 判红, 改成 `commands run <task>` → 转绿(63 → 0); 手抄**脚本类**(带解释器前缀)在 `.exe` 归一后同样判红。
  ④**`pin` 守卫**: 临时树里 3 条 pin 不报、9 条报(一级与子包两层都试过)。
  ⑤**格式化闸门去双写**: `<changed:*.py>` → `run.py run dev.fmt -- <文件…>` → 引擎再展开成 `yapf -i <文件…>`, 两段都实测过, 与旧闸门等价(仍只碰本次改过的 py)。
  ⑥**`list --all` 去重**: 曾把常显命令打两遍(21 条显示成 25 行, 看着像 task id 重复)⇒ `--all` 时不再上浮 pin; 逐视图复验 `--all` 21 行零重复, `list` 3 / `kb` 3 / `test` 3 / `my-commit-flow` 4 / `ship` 2 / `my-commit-flow --all` 5。
  ⑦**反漂移扫描面**扩到 `.agents/skills/**/*.md`(原 `**/SKILL.md`): 细节搬进 `references/` 后只扫 SKILL.md 会留盲区; 扩前实测 0 命中(不误伤别的 skill)。
  ⑧**参数传递**: `run doc.drift -- --list` 转发成功; `run doc.caps -- --strict` **STOP rc=1 且不执行**; 脚本类 `ship.commit -- --message-file … <路径>` 仍接 argv 末尾; 无参数时 `show test.full` 与配置逐字一致。
  ⑨**包内 README 纳管**: 反漂移豁免不保护它(单点定义处是 `config.toml` 而非 README), 已加进 `SCAN_GLOBS` 并给阅读预算 3000 字符。
  ⑩**`<each:>` / `<changed:>` 只盯本次改动清单**, 不是文件系统 glob —— 没匹配上的 WARN 是**按设计跳过**, 不是闸门失效(WARN 文案已点明, 曾误读)。
  ⑪**`doc` 指针基准由子包继承父包**(否则子包写 `references/pipeline.md` 会 STOP), 5 个 task 的 `show` 均打印出父包那份绝对路径。

- **my-commit-flow 同步判据修复 (2026-09-24, 从同名切片迁出)**: 外部走查发现两处潜在缺陷 ——
  ①`classify_merge_probe` 返回二元组致检查表打印 ValueError(expected 3, got 2), 改返回三元组
  (级别/「合流预判」/说明)并钉四分支; ②push/preflight 落后判据回退读 `refs/remotes/gitee/*`
  跟踪 ref, 本 clone 拦截层静默丢弃其写入 → 陈年快照给假「落后 5」拒推 —— 判据一律 `ls-remote`
  现查远端 tip 比对本地 HEAD, 取不到远端真值如实 STOP/ WARN 不凑数; push 后 status -sb 输出删除
  (跟踪 ref 被丢弃时 behind 是假象); 落后提示改 merge --ff-only(当时代码还是 rebase 红线)。
  `test_preflight.py` +5 项回归(含源码扫描守阵禁 `--left-right` 快照判据); 实测 39 项全过 +
  test.full 1201+1 与基线一致。

- **W3 遗留的文档漂移订正 (2026-09-24, 从 commands 切片迁出)**: `AGENTS.md` 那 3 处死链(指向已删除的 skill 与已搬走的 `.commit-flow.toml`)改指 `.commands/my-commit-flow/README.md` 与 `.my-commit-flow.toml`; `pitfalls/ops/_about.md`(连带两份 `_index.md`)/ `pitfalls/ops/prod-files.md` / `pitfalls/git/push.md` / `pitfalls/testing/tmpdir.md` / `conventions/collaboration.md` / `conventions/process.md` 的旧名一并订正。**刻意没动**: `plans/*.html` 与 `tasks/*.md`(冻结快照 / 纪要)、`progress/suggestions.md`(叙述)、`test_preflight.py` 的 glob 夹具字符串、别的专题的切片(按「各 clone 只写自己的切片」约定)。

- **全库文档漂移分段修复 (2026-10-01, 从 activeContext 切片 26-10-01-1809 迁出)**: 内核化重构+别名层处置后四波欠账式漂移(P1×9/P2×63/P3≈45, 25 份文件), 按 [plans/26-10-01-1728](../plans/26-10-01-1728-plan-doc-drift-repair.html) 五段回写**全部完成** —— S1 P1 架构描述重写 5 份(提交 6f474098)/ S2 误导指路与机制反转单点修 9 份(0b422396)/ S3 modules 中度批 6 份(58a88928)/ S4 用户面文档 4 份(7f046ca0)/ S5 P3 计数清扫(projectbrief / roadmap / rules-and-deps 实测刷新)+ 顺手删 mixins/__pycache__ 未跟踪残留; 收尾 test.full **1909 passed + 3 skipped / 91%**(切片 testing/baselines/26-10-01-1930)。代码注释残留 3 处(state.py docstring / qbmanager.py:398 / runtime.py:237)待用户拍板, 未动。滚动档案 [tasks/26-10-01-docs-doc-drift-repair](../tasks/26-10-01-docs-doc-drift-repair.md)。
