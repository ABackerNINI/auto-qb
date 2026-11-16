# 26-11-17-memory-bank-skill-portability — 自制 skill 轨道可移植性改造

**Status:** In Progress
**Added:** 2026-11-17
**Updated:** 2026-11-17
**Summary:** 自制 skill 轨道可移植性改造
**Topics:** memory-bank-skill-portability
**Refs:** memory-bank/plans/26-11-17-0010-plan-skill-portability.html, memory-bank/reports/26-11-17-0010-report-skill-portability.html

## 本篇只回答

自制 skill 轨道(skill 目录 + commands 引擎 + `.commands/` 包 + sync 脚本 + KB 数据件骨架 + PORTING)的可移植性改造: 改造方案与执行进度到哪了。方案与拍板单点在计划, 摩擦证据单点在收编报告 —— 本篇只记「怎么修、修到哪」。

## 原始请求

1. 自制 skills 的可移植性改造: skills 需要尽量通用, 理论上移植后不需要修改 skills 本身(表述/代码等), 只需要修改配置。
2. `PTSKIT-farm-helper` 中包含一次真实移植示例, 其 `docs/skill-portability-report.md` 可做参考。
3. grilling 然后出一个可移植性改造计划。
4. (grilling R1) 报告收编: 用户授权 copy 进本仓。
5. (grilling R3/R4) 每个 skill 需要有一个移植帮助文档; 帮助文档中需要对新项目/正在开发中的项目做移植指导, 特别是后者; 配置/帮助文档放相应子目录, 不放 skill 根目录。

## 思考过程与决策

- 四轮 grilling(D1-D20)全部拍板, 结论表与依据单点: `memory-bank/plans/26-11-17-0010-plan-skill-portability.html` §06。
- 关键口径: 改造单位=轨道级(报告 §2.6-1 实证一半工作量在 skill 外); 配置分散自管+宽容回落; fail-closed 守卫摘默认链改显式挂载; red_lines 升级 glob; review_lane 留包内做纯数据外置(支持存量评审); 每 skill 一份 `references/PORTING.md`(双场景, 重点存量项目); 验收五条全收, 场地=仓内沙箱(跨仓红线零消耗)。
- 本轮(立档轮)零代码改动: 报告收编(D6)+计划入库+本档案; S1-S11 未开工。

## 实现计划

计划 `26-11-17-0010-plan-skill-portability.html` §04 三波次 S1-S11(每步验收判据见计划, 此处不重抄):

- 波次 1 (P0 防复发): S1 memory-bank 配置化 / S2 锚守卫摘链+空库恒绿审计 / S3 全包 rmtree 复核。
- 波次 2 (P1 降手工): S4 红线 glob 化 / S5 PORTING 轨道 runbook / S6 配置模板四件+数据件骨架三件 / S7 review_lane 数据外置 / S8 每 skill PORTING.md / S9 sync 配置化。
- 波次 3 (P2 机械面+收口): S10 出厂配置环境中立 / S11 沙箱重放+grep 白名单审计收口。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| R0 | 报告收编+grilling 拍板+计划入库 | Done(2026-11-17) |
| S1 | memory-bank 配置化(config/project.toml + 宽容回落) | Open |
| S2 | 锚守卫摘链+kb.check 空库恒绿全链审计 | Done(2026-11-17) |
| S3 | 全包 rmtree/unlink 复核 | Done(2026-11-17) |
| S4 | red_lines/warn_lines glob 化+存量迁移审计 | Done(2026-11-17) |
| S5 | PORTING 升级轨道 runbook(双场景, 重点存量) | Open |
| S6 | 出厂配置模板四件+数据件骨架三件 | Open |
| S7 | review_lane 数据外置 lane.toml(存量评审开箱) | Done(2026-11-17) |
| S8 | 每 skill references/PORTING.md | Open |
| S9 | sync 配置化(.config/sync.toml) | Open |
| S10 | 出厂配置环境中立(uv→python3) | Open |
| S11 | 沙箱重放+grep 白名单审计收口 | Open |

## 进度日志

### R0 · 立档 (2026-11-17)

- 开工同步: 远端领先 77 笔, 快进 dbfed3b4→2e2ffe1f。
- 盘点: 收编报告 §2 改造清单在本仓基本零落地(逐项核实见计划 §02); T4 rmtree 主案已修(33e3a3d6)。
- 报告收编: 经用户授权拷入 `memory-bank/reports/26-11-17-0010-report-skill-portability.md`(直拷 .md+来源注记, D8)。
- 四轮 grilling D1-D20 拍板全记录; 计划 `26-11-17-0010` 入库(Open); 本档案立档。
- 零代码改动, 未入池 issue(演进史下沉缓行待实施开工轮入池, R-6), 本轮产物随本专题入库。
- review 三轮(全能档 1 子代理连续派遣, 322 行): 11 发现(1 major/7 minor/3 nit)检 11/11 过零弃, 修 10 零入池, 1 nit 不阻塞留痕(R 符号一行三义, 版次/评审轮/grilling 轮各处有先行词可消解) —— R1 修 6(半自制口径对齐/kb uv run 例证/轮次计数/S6 补 kb 包模板/D15 Windows 场地声明/引证 §2.6-1); R2 修 4(D2 拆面表述/§03 S6 子项数/33e3a3d6 定语改锚定防呆守阵/修正轮次 R2+R4); R3 验证 4 修未回退+R1 行自洽。计划改版留痕经 kb.bump R1 行(doc-updated 0042)。

- 2026-11-17 00:14 grilling 四轮 D1-D20 拍板 + 计划 26-11-17-0010 入库(Open, 三波次 S1-S11 待显式开工) + PTSKIT 移植摩擦报告授权收编 + 档案立档; 零代码改动

### S2+S3 · 波次1 S2+S3 落地 (2026-11-17)

- S2 摘挂同批(计划 26-11-17-0010 §04 S2 / D4 / R-2): `check_mutation_anchor.py --check` 与 `gen_doc_map.py --check` 两处 fail-closed 守卫摘出 kb.check 默认链(10 条 → 8 条), kb 包新增 `kb.anchor` / `kb.docmap` task 显式挂载, 提交闸门(memory-bank/)两行改指 `python <skill-dir:commands>/scripts/run.py run kb.anchor` / `... run kb.docmap`(引擎单点形态, 同 dev.fmt/test.quick); mutation-testing SKILL.md 的「挂 kb.check」引述与 kb.status note / doc-forms.md / set_doc_refs.py NEXT 行的 gen_doc_map 挂载点引述同步改指。**行为零变化断言**: 闸门调用形态与 `commands run kb.anchor` / `kb.docmap` 同一 task(引擎 rc 透传已由锚守卫注入实验证明: 注入「轮次台账」违规 rc=1、还原后 rc=0; gen_doc_map 对单向认领链 rc=1 同机制), 该拦的仍拦; `test_commit_gate_covers_kb_check` 两侧集合对齐照旧绿。守阵: test_mutation_anchor_guard_mounted_explicitly_out_of_default_chain + test_doc_map_guard_mounted_explicitly_out_of_default_chain(各钉「不在默认链 + task 在场 + 闸门改指」三缺一即红)。
- **空库恒绿审计(S2.4, S2 验收原文「kb.check 对空库首跑绿」实测达标)**: /tmp 沙箱新空库骨架(各族目录全建、零文档件)逐成员实测 kb.check 默认链 —— 首轮实测发现两处 fail-closed: ①锚守卫(锚文件缺失即红, 计划 D4 已拍板摘链); ②`gen_doc_map.py --check` 空库判红「没有任何件声明引用——认领链守阵失去校验对象」(rc=1, gen_doc_map.py `if not checked` 分支)。gen_doc_map 处置经用户拍板(2026-11-16): **与锚守卫同款摘链+显式挂载**(首轮子代理「只记录不改」系临场判断, 已被用户改判)。摘链后复测: 默认链 8 成员(gen_all / gen_active_recent / gen_baseline_recent / check_wording / check_doc_templates / timekit / check_status_drift / check_html)对空库骨架**全绿**; 两守卫空库判红保留为摘链判据, 进 PORTING「项目可选守卫勿默认移植」清单(两条)与守阵 test_kb_check_default_chain_empty_kb_audit(8 绿 + 两个 fail-closed 空库红, 分界线钉死)。
- S3 全包 rmtree/unlink 复核(§04 S3): grep `rmtree|unlink` 全包(.commands/ 与 .agents/skills/ 下脚本)逐调用点审计, **零「解析值未校验直接当路径」调用点**。已校验形态: tempfile 自建路径(mutants/test 系夹具)、常量拼接(linux_ci.py TESTS_ROOT 容器内清扫: 标记+死 pid+超龄双条件; commit.py post_marker; check_review_trace.py marker)、删前认标记(_snapshot.py 双防呆 + install_wrapper.py uninstall MARK)、删前容器守卫(review_lane.py cmd_start `_guard_snap_path`)、只删约定路径并核等值(commit.py consume_message_file)、生成器自产残留页(gen_all/_common stale_volume_pages: mb 内 rglob + 卷页正则)。有界形态: sync.py `_restore` 的 git porcelain 解析路径(git 保证仓库相对、快照同源)。方法论与清单进 PORTING「测试与脚本卫生」节。相邻观察(记录不改, 范围守恒): review_lane.py cmd_smoke 的 `--route` 为 CLI 参数非解析值, `_smoke-<route>` 清理路径未过 `_guard_snap_path`(操作者自担面, 与 --snapshot 的守卫面不同级), 不属 S3 害类。
- 本批改面: .commands/kb/config.toml / .commands/my-commit-flow/.my-commit-flow.toml(仅两守卫两行+note 改指) / .agents/skills/mutation-testing/SKILL.md(一行改指) / memory-bank/conventions/doc-forms.md(两处挂载点引述改指) / .agents/skills/memory-bank/scripts/set_doc_refs.py(NEXT 行改指) / .agents/skills/memory-bank/references/PORTING.md(可选守卫清单两条+测试卫生节) / tests/test_memory_bank_docs.py(守阵改钉 1 + 新增 3, 头部测试计划同步)。对照组 skill 零改动。工作树留全部改动, 提交动作不在本批范围(按批次指示)。

### S4 · 波次2 红线 glob 化 (2026-11-17)

- 匹配语义(计划 26-11-17-0010 §04 S4 / D9): `red_lines` / `warn_lines` / `gates[].match` 条目一律 **fnmatch glob**(`fnmatchcase`, 对仓库相对整路径, 大小写敏感不随宿主归一, `*` 跨 `/`)。**裸串 = 精确相等** —— 旧「前缀 startswith 或子串 in」双口径退役; 迁移显式化: 前缀意图写 `foo*`、子串意图写 `*foo*`、精确写 `foo`。`""` 空串不是 glob, 是 `gates_for` 的「每次提交都命中」哨兵, 在 glob 匹配前短路(纯删除提交上哨兵闸门仍跑, 2026-11-06 评审实测洞)。glob 元字符 `?`/`[`/`]` 有特殊含义, 字面量转义如 `data[[]1[]].txt`。语义单点: `_pipeline.hit()`; 同源消费面: gate.py 红线/预警预跑、commit.py `resolve_stage_plan` 拦截面、review 包 `check_review_trace.sensitive_hit` / `review_pack._match_rule`。语义文档单点: `.commands/my-commit-flow/references/config.md`「匹配语义」节(正反例表)+ 配置文件头注; `SENSITIVE_PATH_MARKERS` 保持路径标记词子串语义(非条目匹配, 已注记)。出厂模板面归 S6, 本批只同步 `_ship_config` 既有探测闸门与头注措辞。
- **迁移对照表(R-1, 逐条保意图; 21 个条目, 零意图漂移)** —— 「旧条目 → 新写法 → 旧语义命中例 → 新语义命中例 → 意图判定」:
  1. red_lines `config.yml` → `*config.yml*` | 旧: `config.yml`(前缀) / `xconfig.yml`(前缀) / `a/config.yml.bak`(子串) | 新: 全部仍命中 | 意图=生产配置以任何路径/后缀形态入库都拦, 子串显式化, 覆盖面与旧一致。
  2. red_lines `auto-qb-data/` → `*auto-qb-data/*` | 旧: `auto-qb-data/state.json`(前缀) / `sub/auto-qb-data/x.json`(子串) | 新: 全部仍命中 | 意图=运行时数据目录任何位置, 零缩水。
  3. warn_lines `想法.md` → `*想法.md*` | 旧: `想法.md` / `docs/想法.md` / `想法.md.bak` | 新: 全部仍命中 | 零缩水。
  4. warn_lines `.workbuddy-ai/` → `*.workbuddy-ai/*` | 旧: `.workbuddy-ai/x`(前缀) / `a/.workbuddy-ai/y`(子串) | 新: 全部仍命中 | 零缩水。
  5-6. fmt/test 两闸门 `src/`,`tests/` → `src/*`,`tests/*` | 旧前缀命中 `src/a.py`、`src/auto_qb/b.py`; 旧子串半多命中 `lib/src/a.py`(假阳性) | 新: 前缀面全保, 假阳性消失 | 意图=源码/测试目录前缀, 真值零缩水。
  7. test.pkg.scoped 闸门 `.commands/`,`.agents/skills/commands/` → 前缀 glob | 同 5-6 形态(子串半 `x.commands/y` 假阳性消失) | 真值零缩水。
  8. kb 闸门 `memory-bank/` → `memory-bank/*` | 同前缀形态 | 零缩水。
  9. v.Nu 闸门 `.html` → `*.html` | 旧子串命中 `x.html`(真值)与 `a.html.bak`/`notes.htmlmd`(假阳性, 且 `<changed:**/*.html>` 展开本就只喂真 .html, 多命中=空跑) | 新: 真值面全保, 假阳性收紧 | 意图原文「真有 HTML 改动才命中」, 收紧的是假阳性非意图面。
  10. active-context 闸门 `memory-bank/active-context/` → 前缀 glob | 零缩水。
  11. doc-links 闸门 `memory-bank/`→`memory-bank/*`, `docs/`→`docs/*`, `AGENTS.md`→`AGENTS.md`(精确) | 旧 AGENTS.md: startswith 命中 `AGENTS.md.bak`、子串命中 `docs/AGENTS.md.old`(假阳性; run 行本就只喂 `--files AGENTS.md` 精确面) | 新: 精确=意图(AGENTS.md 本体硬约束对象) | 真值零缩水。
  12. 脚本冒烟闸门 `.agents/skills/`,`.commands/` → 前缀 glob | 同 5-6 形态 | 零缩水。
  13-14. review.trace / sync 两闸门 `""` | 哨兵不变 | 纯删除提交仍命中(实跑验证)。
  15. caps 闸门 `AGENTS.md`(精确, 同 11), `.agents/skills/`→`.agents/skills/*`, `memory-bank/`→`memory-bank/*` | 零缩水。
  16-17. 出厂探测面 `_ship_config._detect_project` python/node 两闸门 `src/`,`tests/` → `src/*`,`tests/*` | 初稿生成面与主配置同口径。
  总判定: 4 条红线/警告为子串意图显式化(`*x*`), 覆盖面与旧一致; 12 个闸门路径条目为前缀意图显式化(`x*`), 真值命中面零缩水, 旧子串半的多命中均为假阳性空跑(消失属收紧噪音非「该红不红」); 2 处意图收紧(v.Nu `*.html` / AGENTS.md 精确)均为假阳性面, 收敛到原文意图; **零意图漂移**。
- **守阵(红绿双验)**: `test_pipeline.HitTest` 8 条(裸串精确化正反例 / 前缀 glob 含跨 `/` 与假阳性不命中 / 子串 glob / `*.cookies*` 可命中(T4 面 A 回归) / glob 元字符与转义正反例 / `fnmatchcase` 大小写敏感(Windows 归一即红) / 空串哨兵匹配零 / gates_for 纯删除提交哨兵仍命中); `test_gate.test_red_line_glob_hits_nested_and_suffixed_paths`(预跑 WARN 面不缩); `test_commit.test_stage_plan_red_line_glob_hits_nested_and_suffixed_paths` + `test_stage_plan_bare_string_red_is_exact_only`(拦截面不缩 + 裸串精确化); test_review_pkg 断言随口径更新(命中细节显示条目原文)。
- **实跑回归(真配置+真函数, /tmp 不碰真实树)**: `load_config()` 读真实 `.my-commit-flow.toml` → `resolve_stage_plan([], red_lines, ["backup/config.yml.old"], ["sub/auto-qb-data/state.json"])` 拒并点名两件(该红仍红); `src/a.py` 放行(该绿仍绿); `*.cookies*` 命中 `src/x.cookies` 与 `a/b.cookies.txt`(T4 面 A 可命中); warn 真实条目命中 `docs/想法.md` 与 `x.workbuddy-ai/tmp`; `gates_for` 真实 gates 清单端到端: `memory-bank/tasks/x.md` 命中 KB 闸门、`src/a.py` 命中 fmt/test、`templates/x.html` 命中 v.Nu、空清单上 3 条哨兵闸门仍命中。
- 本批改面: `.commands/my-commit-flow/scripts/`(_pipeline.hit glob 化+commit.py 红线拦截面同源+_ship_config 探测闸门/头注+三测试文件) / `.commands/review/scripts/`(check_review_trace.sensitive_hit + review_pack._match_rule 改 fnmatch + 测试断言随口径) / `.commands/my-commit-flow/.my-commit-flow.toml`(头注语义节+red/warn/gates 条目显式化) / `.commands/my-commit-flow/references/config.md`(匹配语义节)。对照组 skill 零改动。工作树留全部改动, 提交动作不在本批范围(按批次指示)。

### S7 · 波次2 review_lane 数据外置 (2026-11-17)

- 数据外置(计划 26-11-17-0010 §04 S7 / D13/D18/D20, R-3): review_lane.py 的全部项目数据收编进包根 `.commands/review/lane.toml`(与 `.my-commit-flow.toml` 同构, 脚本只读不写) —— `[lane]`(campaign/freeze_branch/snapshot_root/lane_dir/plan_file/r2_report/issues_dir 七指针字段) + `[lane.scope]`(include/exclude fnmatch glob, vendor 第三方发行物与 `__pycache__` 排除在 exclude) + `[[route]]/[[route.batch]]` 34 批矩阵(exact 精确清单 + globs fnmatch, depth 词表 full/contract/mechanism/scan 以接线实现为准)。机械流程零改(claim/start/verify/batch/done/smoke 状态机与守卫一字未动, 只换数据源); `_load_lane_config` 单点加载(D13: 文件/矩阵/必填字段缺失或 TODO 占位未填 = 引导性报错 rc=2 指路 lane.toml 与具体字段; r2_report/issues_dir 不在盘属校验类辅助数据, 沿用既有警告+切片空不拦)。**无远端稳态(D18)**: `_require_tip` 先探 `git remote get-url`, 未配置远端 → freeze 取本地 HEAD 免 ls-remote(实测 /tmp 沙箱无远端仓库 manifest/claim/smoke 全绿); 有远端语义不变(离线仍拒)。lane.toml 真实矩阵由脚本从改前 BATCH_DEFS 程序化生成(零手抄), S6a 骨架的「当前无代码消费」头注同步换成本仓真实实例说明。
- **R-3 对账(最高风险: 外置丢条目, 结论: 零漏批/漏文件)**: 三方对拍 —— ①改前 BATCH_DEFS(git HEAD 版脚本) vs ②lane.toml 加载矩阵 vs ③在库 manifest.json(freeze f0883292 冻结树 `git archive` 重放): 分层范围清单三方恒等(366 文件); 重叠/漏配 双方 0/0; 34 批逐批文件清单(path+行数)三方全等; 指纹 `b576f4f8ead1d7d6` == 在库 manifest fingerprint(搬运零漂移)。逐批文件数: R1 七批 13/3/5/8/9/3/12=53, R2 六批 5/8/7/18/2/14=54, R3 六批 7/8/5/3/7/14=44, R4 四批 7/15/23/64=109, R5 十一批 8/13/14/7/9/4/8/9/9/9/16=106, 合计 366 == manifest coverage.assigned_files。守阵: LaneConfigTest.test_fingerprint_matches_committed_manifest 把指纹+批次数钉死(改矩阵须显式重生成 manifest 并同步本钉)。
- **smoke 真冒烟(/tmp 沙箱真仓, 本仓脚本+lane.toml 机制, D5 场地)**: 无远端沙箱仓库(manifest → claim R1 → smoke --route R2)全环绿 —— claim/重复认领负例(rc=1)/start(真实快照导出)/verify/done 负例(rc=1)/逐批勾选/done/痕迹清理 全部符合预期, D18 note 行实测; 真认领路线 R1 全生命周期(start/verify/batch×2/done)亦绿。**引导性报错实测**: 缺文件 rc=2「lane 配置缺失…照模板复制或按头注逐字段填写」; 缺矩阵 rc=2「批次矩阵缺失…先按头注说明划分路线与批次([[route]] id + 逐批 [[route.batch]]…)」; TODO 占位 rc=2 点名批次「R1-1 缺 desc 或仍是模板 TODO 占位」; 坏 depth rc=2「depth 非法: 'deep' (词表: full/contract/mechanism/scan)」; 假矩阵(globs 指空)走既有覆盖守卫 rc=1 列漏配文件清单+指路 lane.toml。
- 守阵: test_review_pkg 新增 LaneConfigTest 6 条(真实配置矩阵形状钉值 R1:7/R2:6/R3:6/R4:4/R5:11 共 34 / 指纹同源钉 / 分层范围伪树行为 vendor·tests·根散件排除 / 缺文件·缺矩阵·TODO·坏 depth 四类引导报错 rc=2 含文案片段); LaneStateTest 随 cfg 签名更新; 文件头「## 测试计划」同步。本仓包内实测 `test.one` `129 passed`(改前 `123`, 差 6 = LaneConfigTest)。
- 本批改面: `.commands/review/lane.toml`(骨架→真实配置) / `.commands/review/scripts/review_lane.py`(数据外置加载+D18+引导报错, 流程零改) / `.commands/review/scripts/test_review_pkg.py`(LaneConfigTest+签名随改) / `.commands/review/config.toml`(manifest/claim/verify/smoke 四条 note 随 D18/S7 语义同步) / `.agents/skills/memory-bank/references/PORTING.md`(存量 lane 用法接线状态两行改「已接线 S7」, 口径不复制)。对照组 skill(commands/create-issue/scope-guard)零改动; config.yml/auto-qb-data/ 未动; 在库 manifest.json 与 route-*.json 未动。工作树留全部改动, 提交动作不在本批范围(按批次指示)。
- S7 批次评审修复轮(5 条全过检, 当场修): ①[major] LaneTipTest 新增 4 条钉 `_require_tip` 三分支(无远端 note+本地 HEAD D18 / remote 可解析但 ls-remote 失败 rc=1 / 远端无该分支 ref rc=1 / HEAD!=tip rc=1, 附加同步态放行无 note; 本地 bare 仓当远端零网络); ②LaneConfigTest 引导报错守阵表扩到 13 个 _die 分支(坏 TOML/缺 [lane] 节/缺必填字段/缺 scope 节/include 类型错或空/路线缺 id、id 重复、无批/批次前缀错、id 重复/exact-globs 全空、类型错, subTest 表驱动); ③加载面路径形态校验(lane_dir 须仓库相对, snapshot_root 须单段目录名, 违者 D13 引导报错 —— _guard_snap_path 删除授权依赖 snapshot_root 点名) + 4 条路径形态守阵 + lane.toml 头注字段口径同步; ④LaneManifestGuardTest 钉「认领后拒 manifest 重生成」(rc=1, 不写 manifest); ⑤钉「漏配即拒列清单」(rc=1, 列出漏配文件, 不写 manifest)。机械流程仍零改(③属加载面校验); 测试计划清单同步; 包内 `test.one` `138 passed` + `17 subtests`(修前 `129`), `test.quick` 全量 `6261 passed` / `19 skipped`。
- S7 复评轮 3(nit, 一行成本修): `_is_repo_relative` 补禁 `'\'` 字段 —— git porcelain 恒正斜杠, Windows 宿主 TOML 填 `'memory-bank\reports'` 一类反斜杠原串会过旧校验而 lane 前缀比对对不齐(同类误导性误报); lane_dir/snapshot_root 报错文案与 lane.toml 头注同步「路径字段一律填 posix 形态」; 守阵补 TOML 字面串反斜杠反例(basic string 装裸反斜杠会先死在 TOML 转义, 用 literal string 构造) + 直驱单元反例。包内 `test.one` `139 passed` + `21 subtests`。
