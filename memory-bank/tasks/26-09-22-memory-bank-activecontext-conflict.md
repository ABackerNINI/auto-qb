# 26-09-22-memory-bank-activecontext-conflict — activeContext 多 clone 冲突治理

**Status:** In Progress
**Added:** 2026-09-22
**Updated:** 2026-09-23
**Summary:** activeContext.md 全体收尾必写 + 「最后更新」滚动栈同段重写 → develop 汇合高频冲突; 已按 **A′ 时间戳切片 + D** 实施 W1–W3(取消 global.md / _index.md / 取最近 N 条与缓存文件), W4(merge-tree 预检) 可选未做。
**Topics:** memory-bank-activecontext-conflict

## 原始请求

用户 2026-09-22 23:20 提问:「分析如何解决多agent合作activeContext易冲突的问题」; 23:43 指令「产出计划然后提交」—— 产出计划文档(单文件 HTML, memory-bank/plans/)并按「提交」口径 commit + push。

## 思考过程与决策

- **根因定性**: 不是 agent 手滑, 是结构必然 —— 一个所有 clone 的收尾 DoD 都必写的单文件, 最热写点(「最后更新」滚动栈)还集中在文件头同一段; 本质是「并行会话状态」被塞进「串行媒介(单文件 + 线性 git 历史)」。本环境(禁 rebase/stash、非快进+脏=必炸、合并后未触及文件可消失)把冲突处置成本放大到危险级, 详见 pitfalls/git/history-integration.md。
- **放大因素**: 写点重叠(滚动栈 = 每会话重写头部同几十行) × 高频(每执行轮收尾必写; 09-22 一天头部叠加 5 个时段状态) × 反馈滞后(push 被拒才暴露)。
- **现有防线评估**: 12 KB cap / 流水账禁令 / 先同步后开工 缩小的都是爆炸半径, 没有动写点重叠根因; collaboration.md「合并冲突交用户主导」是承认冲突必然并转嫁成本。
- **解法空间**: 三条正交路线 —— 写点并行化(拆文件) / 读点聚合化(生成物) / 写串行化(单写者); 五案对比 A 拆文件 / B 生成式聚合 / C 同文件分段 / D git 兜底(merge-tree 预检 + rerere; union driver 对滚动替换结构不适用) / E 单写者。
- **决策**: 推荐 **A + B + D**。A 消灭冲突源(clone-id 沿用工作区目录名 auto-qb/clone1/clone2/long-seeding, 不发明新机制); B 兜住「别人在干嘛」读点(生成物冲突解法 = 重跑, 与 tasks/_index、pitfalls/_index 同模式); D 做最后保险。C 治标; E 牺牲并行且 global 段本就低频, 不值得。
- **职责澄清**: activeContext 混了两种性质相反的状态 —— 全局项目焦点(低频共享)与会话滚动状态(高频 per-clone); 只有后者需要拆。
- **不碰的东西**: tasks/ 档案「不带时分、同天同专题必撞同路径」是故意设计的 add/add 查重信号(SKILL.md 明文), 保持不动; issues 认领状态继续走 Gitee 单一事实源, 不进 activeContext。

## 实现计划

计划文档(含目标结构、协议变化对照、波次、验收标准):
[memory-bank/plans/26-09-22-2350-activecontext-conflict-plan.html](../plans/26-09-22-2350-activecontext-conflict-plan.html)

要点(v1.1 修订后): W1 结构拆分(`activeContext/` 目录 + 按专题的时间戳切片 + ≤1 KB 存根 +
`_common` 的 `SLICE_FILE_RE` / `CAP_POLICY["slice"]` / `STUB_CANDIDATES` / `EXCLUDED_DIRS`) →
W2 阅读脚本(`gen_active_recent.py`, **打印而非生成**) + 守卫 →
W3 协议接线(SKILL.md / AGENTS.md / collaboration.md / README 细路由 + 三个常驻规则载体) →
W4 可选加固(preflight merge-tree 预判 + rerere)。
**W1–W3 必须连续入库**(同批提交分笔连续推送), 避免双 clone 协议错位窗口跨同步周期。

v1.1 与初稿的三处差异(2026-09-23 与用户确议, 理由见计划 §04):
取消 `global.md`(长青四段各有归属, 实测占旧文件 3,516 字节 / 27%)、取消 `_index.md`(文件名即索引)、
取消「取最近 N 条」与 `_recent.md` 缓存(条数不是稳定时间尺度, 且截断会漏掉活跃切片)。

## 子任务状态表

| 子任务 | 状态 | 说明 |
|---|---|---|
| W1 结构拆分 | Completed | `activeContext/` 目录 + 9 张切片 + `_about.md` + ≤1 KB 存根; `STUB_CANDIDATES` / `EXCLUDED_DIRS` 接线 |
| W2 阅读脚本与守卫 | Completed | `gen_active_recent.py`(skill 的 scripts/, 只打印不写文件) + `_common` 常量 + 3 条守卫 + 闸门 |
| W3 协议接线 | Completed | SKILL.md / AGENTS.md / README 细路由 / collaboration.md + **三个常驻规则载体**(copilot-instructions · ai-lib · memory-bank.instructions) |
| W4 预检加固(可选) | Completed | `preflight.py` 合流预判(`classify_merge_probe` + `git_rc`, push 阶段撞即 STOP) + 本 clone `rerere.enabled=true` |
| 冲突演练(AC-3) | Completed | 临时仓库实测: 各写自己的切片 → rc **0**; 旧结构同段 → rc **1**; 同分钟同名 add/add → rc **1** |
| 遗留: 归档阈值 | 待拍板 | 切片 >14 天未动即归档 —— 已作为脚本默认值(`--stale-days`)与 `_about.md` 约定落地, 可调 |
| 遗留: 既有红灯 | 待拍板 | `test_kb_files_respect_caps`: `tasks/_index.md` 12,261 > 12,000 —— **非本轮引入**, 按范围守恒未修 |

## 进度日志

- **2026-09-23 00:34–15:30 (方案迭代 → W1–W3 实施)**: 三轮确议把方案从 A+B+D 收敛到 **A′ 时间戳切片 + D**,
  并先行落地脚本与 skill(W2/W3 部分), 随后按「开始实施」完成 W1 与 W3 剩余。
  开工 ff-only 同步核过: 本地 HEAD == Gitee tip `fda13cd`, 不落后。
  - **W1**: 建 `memory-bank/activeContext/`(`_about.md` + 9 张切片, 按专题、文件名 `YY-MM-DD-HHMM-<slug>.md`);
    `activeContext.md` 降级为 690 字符存根(`is_stub` 判据全过)。
    **守恒核对**(旧「正在进行」12 条 → 新结构): 9 条进切片(HR 核实 / activeContext 冲突治理 / 版本管理 /
    跨组交叉 / README 重写 / .!qB 误判 / config 取值范围 / web 包拆分 / 上轮复核收尾);
    4 条按 DoD 迁出**且各有已存在的事实源** —— 后端状态周期落盘(issue 26-09-21-1347 Fixed + 计划 HTML)、
    Console Hub 卡片(入库 c31ee0d + 坑 pitfalls/web-ui/layout-css.md)、设置页伪警示(issues/26-09-22-2002 Open)、
    memory-bank 目录化 W0–W8(tasks/26-09-22-memory-bank-dir-refactor.md)。**missing = 0**。
    长青四段(定案口径 / 下一步候选 / 待走查 / 历史归档)按去处删除副本, 入口收进存根与 README 细路由。
  - **W2**: `gen_active_recent.py` 落地 memory-bank skill 的 `scripts/`; `_common.py` 加 `SLICE_FILE_RE` /
    `LAST_ACTIVE_RE` / `SLICE_DIR` / `CAP_POLICY["slice"]=6000` / `role_of` 分支 / `STUB_CANDIDATES` /
    `EXCLUDED_DIRS`(后者防 `gen_kb_index` 自造 `_index.md`); `.commit-flow.toml` 加切片闸门。
    实测三态: 正常目录 → 9 行全量倒序; 探针目录含坏命名 → `--check` 退出码 1; 无目录 → 提示 + 退出码 0。
  - **W3**: SKILL.md(开始 / DoD / cap 表 / 脚本表 / 切片小节 / 反模式 5 条)、AGENTS.md(6684/8000 字符)、
    README 细路由拆两行、collaboration.md 补切片口径; 另修**三个常驻规则载体**
    (`copilot-instructions.md` / `instructions/ai-lib.md` / `instructions/memory-bank.instructions.md`)——
    它们原本都教「读 activeContext.md 并往里写状态」, 不改就是决策点与生效点错位(库里记过的反模式)。
  - **实测**: 全量 `1189 passed + 1 skipped + 1 failed` / 91% / 143.77s; 那条 failed 是**既有红**
    (`tasks/_index.md` 12,261 > 12,000, 本轮未碰该文件), 已按范围守恒保留并记进
    [testing/baseline.md](../testing/baseline.md) 与 [baseline-history.md(已切片化为 baselines/)](../testing/baseline.md)。
    闸门全绿: `gen_kb_index --check` / `gen_tasks_index --check` / `check_doc_links.py` /
    `check_context_caps.py` / `check_kb_structure.py`(仅上述既有红那 1 项)。
  - **新坑**: 改单文件 HTML 计划文档时字符串替换吞掉 `</p>`(浏览器静默容错) →
    [pitfalls/docs/html-edit.md](../pitfalls/docs/html-edit.md)。
- **2026-09-23 15:46–16:00 (收尾连带两件)**:
  ①**规则载体瘦身**: `.github/instructions/memory-bank.instructions.md` 4,213 → **2,486 字符**(106 → 55 行) ——
  删掉四节与别处重复的内容(cap 分级表 / 三行头模板 / pitfalls 字段 / 任务档案格式), 换成指向 skill 与
  `_common.py` 的指针; 保留 `applyTo` 机制 + 三条铁律(检索纪律 / 生成物不许手改 / 改完跑机检) + 收尾命令。
  同步换掉守卫 `test_memory_bank_instructions_match_current_structure` 的针列表(去掉 `## 原始请求` /
  `## 进度日志`, 换成 `CAP_POLICY` / `gen_active_recent.py`)。**没有做成纯指针** —— 该文件是自动注入、
  skill 是按需触发, 纯指针会把规则从"可见"降级成"可触达"。
  ②**新增守卫 `test_skill_cap_table_matches_cap_policy`**: 钉住 SKILL.md 的 cap 表与 `_common.CAP_POLICY`
  的数值集合 + 行数一致(2026-09-23 加 `slice=6000` 时两张表都是手工同步的, 守卫只钉 token 不钉数值)。
  ③**轮转**: `testing/baseline-history.md` 加一条流水后撞 `log` cap(24,466 > 24,000, 此前仅余 170 字符),
  按 cap 的设计意图把最老一条原样外迁 `testing/attachments/baseline-history-old.md` → 15,664 字符。
  新坑 [pitfalls/kb/cap-counting.md](../pitfalls/kb/cap-counting.md)(char_count 按 CRLF 计 + 流水轮转)。
- **2026-09-23 15:52 (轮转策略修订, 用户指出首版不妥)**: 「只搬最老一条」确实错 —— 条目大小不受控,
  可能只有几百字符, 下次追加立刻再触顶(该文件触顶时只剩 170 字符余量, 等于**每次新增都要迁移一次**)。
  改为**触顶即切约 1/3**: 策略落成机器单点 `_common.LOG_ROTATE_KEEP = 2/3`(切完落回 ~2/3 容量);
  `check_kb_structure.check_caps` 报 `log` 超 cap 时**直接把目标字符数打出来**(夹具实测输出
  "切到 ≤ 16,000 字符 (保留 ~67%)"), 把修法摆到决策点。SKILL.md / README 生成物节 / pitfall / 外迁存档说明四处同步口径。
  连带: README 因新增说明一度顶破 `index` 档(3,195 > 3,000) —— 压缩表述 + 收掉「核心设计」「黄金法则」两处赘述后回到 2,931。
  **`tasks/_index.md` 超 cap 按用户指示暂不改造**(它会让提交闸门 STOP, 待后续处理)。
- **2026-09-23 15:57 (tasks 改造, 用户指令「将 tasks 也照此改造」—— 但**照搬轮转不成立**, 改用同目的的另一手法)**:
  先量数据, 结论是**轮转在 tasks 上不可行**: 索引 12,299 = header 626 + 33 条 ×**平均 350 字符/行**;
  可轮转对象只有 16 个 `Completed`(另 16 个 `In Progress` 是活的), 其中**仅 1 个无外部引用**;
  落到 2/3 目标需砍 4,299 字符 —— 即①搬走有引用的档案会让 `check_doc_links.py` 变红(除非连带改写引用)
  ②即使把 16 个全搬也只够一次, 下次触顶立刻再来 —— **病根没动**(用户上一轮抱怨的正是这个)。
  真病因: 索引把 `**Summary:**` **全文**打进一行, 于是索引大小由「摘要写得多长」决定, 而不是由「有几个档案」决定。
  ⇒ 改**渲染口径**: `gen_tasks_index.SUMMARY_MAX = 80`(摘要截断成一行, 全文留在档案),
  索引 **12,299 → 5,710**(余量 6,290, 同 cap 可容纳 ~90 个档案), **零链接破坏、零信息丢失**, 红灯消失。
  外迁条目降级为**后备**(真到几百个档案、条目数本身撑爆 cap 时才用, 且要挑无外部引用的老档案)。
  连带修 `gen_tasks_index.py` 两处**漂移**(由上一轮 activeContext 去掉长青职能引起):
  `EMPTY_HINT["Pending"]` 仍指向已不存在的「下一步候选」段、header 仍说「日常短周期只记 activeContext.md」。
  坑已并入 [pitfalls/kb/cap-counting.md](../pitfalls/kb/cap-counting.md) 第三节「生成式索引撞 cap: 先查渲染口径」。
- **2026-09-23 16:06 (AC-3 + W4, 用户指令「做AC-3以及W4」)**:
  - **AC-3 冲突演练**(在 `R:/Temp` 临时仓库做, **不碰本仓 git 状态**; 探针用后清理):
    ① 两 clone 各写自己的切片 → `git merge-tree --write-tree` 退出码 **0**(无冲突)✓
    ② 对照组: 同改旧单文件头部同一段 → 退出码 **1**(`CONFLICT (add/add)`)✓
    ③ 残余风险: 同分钟同名 add/add → 退出码 **1** ✓(已知低概率, 如实暴露而非回避)
    ⚠ 探针踩到环境坑: 这套 PortableGit(1.2.0) `git init -b main` **不生效**(默认 `master`),
    且切分支后新目录不会恢复 —— 探针脚本每步 `mkdir -p` 绕开(仅影响临时仓库, 与本仓无关)。
  - **W4 预检加固**(用户显式授权改 `my-commit-flow` skill): `preflight.py` 新增
    `git_rc()`(只取退出码 —— 既有 `git()` 在 `check=False` 时丢退出码, 而退出码正是这里的信号)
    与纯函数 `classify_merge_probe(rc, phase)`; 落后/分叉时跑 `merge-tree --write-tree HEAD <远端 tip>`
    报「撞 / 不撞」, **push 阶段撞 = STOP**(本环境非快进 + 脏 = 必炸, 先留备份),
    拿不到远端对象时如实说"无法预判"; `--check-started` 只在**本地已有远端 tip 对象**时附这一行,
    不为凑一行去 fetch(保住"只读"承诺)。SKILL.md 的 S1 与脚本表同步。
    实测: `merge-tree HEAD HEAD~1` → rc 0; `--check-started` 退出码 0 且**跑前跑后 HEAD 与工作区指纹均未变**;
    纯函数四分支 rc∈{None,0,1}×phase∈{commit,push} → WARN/PASS/WARN/STOP。
    本 clone 已开 `git config rerere.enabled true`(**其余 clone 需各自开** —— 跨 clone 属红线, 本会话不代办)。
  - 计划 §05 W4 与 §07 AC-1…AC-7 已逐条标为实测通过; 未新增测试文件(建新文件需单独确认)。

- **2026-09-22 23:20–23:50 (问答 → 计划产出)**: 先按问答轮完成根因分析(读 activeContext.md / collaboration.md / SKILL.md / pitfalls/git/history-integration.md + git grep 检索); 用户指令「产出计划然后提交」后转入执行: 开工 ff-only 同步 9 提交至 `d4dea8b`(含 W5 src 布局重构), 工作区干净; 立档查重(本 clone + 跨工作区 ls)无同名 slug; 闸门①等价动作 —— 干净代码态跑全量 `uv run pytest tests -q` = **1189 passed + 1 skipped**(32.9s, 覆盖率 91%, TMPDIR 已设 R:/Temp/auto-qb/tests), 与重构前基线一致; 计划 HTML 落盘 memory-bank/plans/26-09-22-2350-activecontext-conflict-plan.html(25.6 KB, dark 主题)。仅文档, 未改代码。
