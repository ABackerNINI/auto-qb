# 26-11-17-memory-bank-skill-portability — 自制 skill 轨道可移植性改造

**Status:** In Progress
**Added:** 2026-11-17
**Updated:** 2026-11-18
**Summary:** 自制 skill 轨道可移植性改造
**Topics:** memory-bank-skill-portability
**Refs:** memory-bank/plans/26-11-17-0010-plan-skill-portability.html, memory-bank/reports/26-11-17-0010-report-skill-portability.html, memory-bank/testing/baselines/26-11-18-0041-memory-bank-skill-portability.md

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
| S1 | memory-bank 配置化(config/project.toml + 宽容回落) | Done(2026-11-17, cd1bfcc5) |
| S2 | 锚守卫摘链+kb.check 空库恒绿全链审计 | Done(2026-11-17) |
| S3 | 全包 rmtree/unlink 复核 | Done(2026-11-17) |
| S4 | red_lines/warn_lines glob 化+存量迁移审计 | Done(2026-11-17) |
| S5 | PORTING 升级轨道 runbook(双场景, 重点存量) | Done(2026-11-17, 4323d5f9) |
| S6 | 出厂配置模板四件+数据件骨架三件 | Done(2026-11-17, ad82b1ef+fc1d2193) |
| S7 | review_lane 数据外置 lane.toml(存量评审开箱) | Done(2026-11-17) |
| S8 | 每 skill references/PORTING.md | Done(2026-11-17, 6ef64c16) |
| S9 | sync 配置化(.config/sync.toml) | Done(2026-11-17, 53ce6fb9) |
| S10 | 出厂配置环境中立(uv→python3) | Done(2026-11-17, 随 S6a 出厂设计吸收, 模板面 run 行零 uv) |
| S11 | 沙箱重放+grep 白名单审计收口 | Done(2026-11-17, 收口轮 ①③④ 过; ② 经批9b 四处外置配置后 grep 复验操作性零命中, 用户拍板) |

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

### S1/S5/S6/S8/S9/S10 · 记账补齐 (2026-11-17)

- 各批次本体改动与提交见 git log(S1 cd1bfcc5 配置化+宽容回落 / S5 4323d5f9 轨道 runbook / S6a ad82b1ef+S6b fc1d2193 模板四件+数据件骨架 / S8 6ef64c16 九份 PORTING / S9 53ce6fb9 sync 配置化); 各批守阵随批入库(tests/test_memory_bank_cli.py / test_sync_agent_skills_config.py 等), 明细以提交与计划 §04 为准。此前批次未回写本档案(提交未带记账), 本轮收口按 git log 补账。
- S10 判定说明: 出厂/模板面(config.minimal.toml 四件 + 数据件骨架三件)自 S6a 建件起即以 python3 出厂(run 行零 uv, 头注明示「uv 等项目偏好不入出厂配置」), S10 判据「模板面 grep 零 uv」由 S6a 设计吸收达成。

### S11 · 收口轮 (2026-11-17)

- **① 沙箱重放(D5)过**: 绿地场景(/tmp/port-replay/demo-farm, git init 模拟目标项目), 照 runbook 移植单位清单表拷 6 单位(memory-bank skill + commands 引擎 + kb/my-commit-flow/review/test 四包 + scripts/sync_agent_skills.py + KB 数据件骨架), 配置填空 4 件(project.toml 目标项目值 / kb·test config.toml 与 .my-commit-flow.toml 由 minimal 模板改名填空 / .config/sync.toml), KB 骨架+三件数据件+README+_about.md。验收全绿: kb.time 三行正常; kb.index 首生成; kb.check 8 成员绿; doc.links 绿; kb.new task 建档成功后即删(领域枚举 farm- 前缀与 siblings 空列表真实生效); my-commit-flow `_pipeline.py --show-config` 读到填空配置(红线/警告/3 起步闸门); 起步闸门手工跑绿(pytest 1 passed / node --check 绿); sync 脚本落 .farm-skills 2 条链接。**0 行代码 diff 取证**: diff -rq 全轨道对照源仓, 零 .py 内容差异(唯一 .py 级差异行 = 本仓 .commands/conftest.py 与 test_conftest_guard.py 未拷 —— 仓内 pytest 收集面, 不属移植单位清单); 差异面全部落在配置/数据件(project.toml、四包根配置、sync.toml、KB 数据件)。
- **③ 空库首跑绿终验 + 删配置态过**: 独立裸沙箱(/tmp/port-replay/bare-kb, 零 config/project.toml): kb.check 默认链 8 成员全绿(首跑 kb.index 生成 0 物, 空库恒绿); 删配置态 kb.new task rc=0 且必打两行 `[KB-CONFIG]` 提示(领域枚举缺失跳过校验 / 跨 clone 查重缺失跳过) —— D13 宽容回落非静默, 不红。
- **② grep 白名单审计(R-4)不过 —— 停手待拍板**: 分词 grep(auto-qb / auto_qb / qBittorrent / qbittorrent / gitee, -i)对 .agents/skills + .commands + scripts 全量命中(约 700 处, 集中: review/lane.toml 222=本仓矩阵实例, 根 scripts/ 约 160=项目运行时代码非移植单位, 包根 config.toml 各文件=本仓 task id 运行面, test_*.py=守阵合成夹具/本仓基建钉值, md/html 文档=历史文档与 provenance 注释, mutants.py 与 test 包 linux_*.py=深度项目绑定件 PORTING/双场景指导明示不移植)。**轨道单位内 2 处未申报操作性命中**: ①`.agents/skills/memory-bank/scripts/nav_data.py:48` `REPO_DENY` 硬编码 `auto-qb-data`(取证 2026-11-17); ②`.agents/skills/memory-bank/scripts/nav_server.py:75` `MAIN_REMOTE_CANDIDATES = ("gitee","origin","github")` gitee-first 双远端假设(与报告 §04 横切原则「单远端而非 gitee/github 双远端假设」相抵) —— 两处均在 kb.nav(可选机检, 不在默认链)但随 skill 整目录被拷, 无 PORTING/config 申报, 未外置。**验收判据「操作性代码零命中」不成立, S11 ② 不过**; 按收口指令停手报告, 不放宽判据、不入池、不自行修(nav 不属 S1-S10 改造面, 范围守恒只记录)。另 2 处非轨道单位的申报出入同轮记录: `.agents/skills/release/scripts/tag_release.py:78` 默认 tag 附注硬编码 `auto-qb`(其 references/PORTING.md:8 声明「skill 脚本零项目事实」—— 单点漂移, release 本体不在 D2 改造面); `.agents/skills/deps-upgrade/scripts/check_updates.py:37` USER_AGENT 硬编码 `auto-qb-deps-upgrade/1.0`(project/ 数据目录未收编此项)。
- **④ D15 实测(Linux 半条过)**: `commands run test.pkg` 全绿(含 my-commit-flow 自带测试 test_pipeline/test_gate/test_commit/test_snapshot/test_sync 与 commands 引擎; 实测数字与用时单点见基线切片 26-11-17-0622); `commands run test.full` 全绿, 基线切片 26-11-17-0622。「全包无未校验 rmtree 调用点」已由 S3 收口(全包逐调用点复核零命中)。
- **Windows 半条场地声明留痕(D15 ⑤)**: 本 clone(Linux)不可执行 Windows 半条 —— 按 D15 场地声明执行: 有 Windows 侧实例则补测, 无则以 33e3a3d6 锚定防呆守阵(语义绑数据不绑宿主 OS)+Linux 绿为**过渡态**, 不静默收窄; 后续有 Windows 侧实例时补跑 my-commit-flow 包内测试并回写本档案。
- **runbook 微调两处(重放暴露缺口, 计划面允许)**: PORTING.md「最小移植 3 步」第 2 步补「空库阶段 _about.md 不预挂类级 _index 链接」(空类目录不生成类索引, 挂了 doc.links 必红 —— 重放首轮实测); 移植单位清单表 #3 补 test 包例外交叉引用(只取 config.minimal.toml 起步, 原包脚本不移植)。
- **R-6 入池(用户已显式批准)**: `memory-bank/issues/26-11-17-0620-docs-memory-bank-history-sink.html`(docs/light, D14 拍板缓行的 P2 文案类「SKILL.md 演进史批量下沉」, 与计划 26-11-17-0010 已双向补链)。
- **收口结论(收口轮)**: 验收五条(报告 §5)逐条 = ①过 ②**不过** ③过 ④过 ⑤Linux 过渡态过(Windows 留痕) —— 当轮 S11 保持 In Progress, ② 的 4 处操作性命中报用户拍板。

### 批9b · 四处操作性命中外置配置 (2026-11-17, 用户拍板「全部外置配置, 照 S1 同款模式」)

- **外置1 nav_data**: `REPO_DENY` 常量 → `DEFAULT_REPO_DENY = (".git", ".env")`(通用默认, 零项目词)+ `effective_repo_deny()` 现读 `<skill>/config/project.toml` `[nav] repo_deny`(server 30s 轮询下改配置即生效); 缺失/形态不对 → 回落默认 + stderr 必打 `[KB-CONFIG]` 提示一次(免轮询刷屏); 显式空列表 = 合法配置(全放行不提示, 口径同 siblings); 坏 TOML 异常上抛 fail-fast。本仓 `[nav] repo_deny = ["config.yml","auto-qb-data",".git",".env"]` = 旧 REPO_DENY 原样搬家, **行为零变化**。读者单点 `_common.config_nav_repo_deny`(S1 读者同款形态判据)。
- **外置2 nav_server**: `MAIN_REMOTE_CANDIDATES` → `DEFAULT_REMOTE_CANDIDATES = ("origin",)`(单远端通用, 对齐报告 §04 横切原则)+ `_remote_candidates()` 读 `[nav] remotes`, 回落语义同上(names[0] 兜底口径不变; 显式空列表 = 直接取 git remote 第一个)。本仓 `remotes = ["gitee","origin","github"]` 原样搬家, 行为零变化。读者单点 `_common.config_nav_remotes`。
- **外置3 tag_release**: 默认附注 `f"auto-qb {tag}"` → 纯函数 `tag_message(message, prefix, tag)` 三分支(--message 显式恒胜 / `<prefix> <tag>` / 空前缀回落通用 `release <tag>` 并置 fallback 旗 → main 打 WARN, 非静默); 项目词经新增 CLI 参 `--tag-note-prefix` 从 `.commands/release/config.toml` 的 release.tag **run 行**传入 —— 沿用该包「项目事实全在 config.toml run 行」的既有参数化模式(PORTING.md 配置键行声明), 不新增脚本读引擎配置的机制; FlagConsistencyTest(旗标 ⊆ argparse)守阵自动覆盖新旗标, 项目事实钉值扩进 test_project_facts_pinned。脚本零项目词(usage/docstring 同步通用化)。
- **外置4 check_updates**: `USER_AGENT` 常量 → `user_agent()` 函数读**新建** `.agents/skills/deps-upgrade/config/project.toml` `[user_agent] value`(D19 统一落点, 该 skill 首份 config); 缺失/形态不对(value 非串/空白/节非表)→ 回落通用 `DEFAULT_USER_AGENT = "deps-upgrade/1.0 (skill script; read-only)"` + stderr `[DEPS-CONFIG]` 提示一次; 坏 TOML fail-fast。选型留痕: User-Agent 是 API 礼仪标识非校验面, 回落提示取「提示着降级」与 D13 同口径(不静默)。
- **PORTING 依赖面同步三处**(不造第二口径): memory-bank runbook「配置落点」skill 面补 `[nav]` 两键; release PORTING 配置键行补 `--tag-note-prefix` 与回落语义; deps-upgrade PORTING 配置键行补 `[user_agent]`(并修正原「零硬编码项目词」声明与事实不符的漂移)。
- **守阵(红绿双验, 各文件头部测试计划同步)**: test_kb_nav_data 4 例(配置生效/整体替换语义/回落零项目词+提示一次/混型回落/显式空合法)、test_kb_nav_server 5 例(remotes 读配置生效/回落 origin+提示一次/候选序无命中退 names[0]/混型回落/显式空直取第一个; 既有 offline 测试改经配置给 gitee 候选序)、test_memory_bank_cli 2 例(本仓成态 [nav] 两节在场钉 + 读者形态判据)、release 包 TagMessageTest 3 例 + run 行项目事实钉值、tests/test_deps_upgrade_user_agent.py 新文件 4 例(配置生效/回落+提示/形态不对/坏 TOML fail-fast)。test.quick 全绿(实测数字与增量单点见新基线切片); dev.fmt 全部改过的 .py。
- **grep 复验(操作性代码零命中达成)**: 分词 grep(-i, auto-qb/auto_qb/qBittorrent/qbittorrent/gitee)对 .agents/skills + .commands + scripts 全量 695 处逐文件分类: C1 配置/数据面(task id 运行面/项目配置/项目数据件)283, C2 历史文档/PORTING/references 38, C3 provenance 注释/docstring 21, C4 守阵合成夹具/钉值 105, C5 项目专属不移植件/平台 API 词汇(PORTING/双场景指导明示声明同源)76, C6 根 scripts/ 项目运行时(非移植单位)172 —— **操作性代码命中 0**(批9b 前 4 处: nav×2/tag_release/check_updates 全部外置归零; 四个文件的余量命中均为注释/docstring, 计划字面词形大小写敏感下 nav_server 的 Gitee 注释等不构成「qBittorrent」形态命中)。**边界留痕**: `check_updates.py:365` 联合分析输出文案含小写 `qbittorrent` 三依赖名 —— 按计划 S11 字面词形(大小写敏感)不命中; -i 口径下归类「依赖面声明/特性词汇」白名单(与 SKILL.md「三特殊依赖联合分析」特性描述同源, 权威数据在 project/deps.toml 数据件), 外置需改输出装配逻辑(超出批9b 四处范围), 留痕供复核。
- **S11 终态**: 验收五条(报告 §5)全过 —— ①拷目录+填配置+0 行代码 diff 过; ②grep 白名单审计操作性代码零命中过(批9b 后); ③kb.check 空库首跑绿+删配置态宽容回落过; ④runbook 照做可复现过(①联验); ⑤my-commit-flow 自带测试 Linux 绿过(Windows 半条场地声明留痕, 见上轮)。S11 翻 **Done**。
- **批9b 评审修正(1 major 必修, 收集面分层)**: 基线切片首版(0653)的增量分解有误 —— 把 release 包 TagMessageTest 3 例计入了 test.full 增量, 静态按用例函数推 +17 与 test.full 实测增量 +14 矛盾。根因 = **收集面分层**: tests/ 收集面(test.full 消费)与 .commands 包收集面(test.pkg 消费)各自独立计数, test_release_pkg 在 test.full 收集面恒为 0 项。实证: 节点级收集清单 diff(stash 态 HEAD 6291 项 → 当前 6305 项, 净 +14, 零删除项; TagMessageTest 不在 test.full 清单)+ 逐文件收集计数(13/24/35/4/13)。处置: ①test.full 与 test.pkg 双面重跑实测(test.full 数字与上轮一致; test.pkg 较收口轮 +3 = TagMessageTest 3 例在其收集面在场); ②0653 切片未提交即废, 按「写完不改」口径删除重切为 26-11-17-0719(增量分解按面分摊 tests/ 面 14 + 包面 3, 与两轮实测严格对账; test_memory_bank_cli 净 +1 —— 既有「本仓 project.toml 成态」用例系加断言改造不计增量, 修正评审「净 +1」判定与首版「+2」的双重偏差); ③全部新守阵收集面自检通过: 14 项在 tests/ 面 node diff 逐条在列, TagMessageTest 3 例经 test.pkg 实测在场 —— 无「测量后扩写」(deps 4 例首版测量前已写, 评审的疑似不成立)。数字与分解单点 = 基线切片 26-11-17-0719。

- 2026-11-18 00:39 S1-S11 全波次实施+分批评审闭环入库: 配置化/摘链恒绿/glob 化/轨道 runbook/lane 外置/PORTING 全配/sync 配置化/收口五条验收; 合流适配修绿上游 Windows 盲区 3 红; 收尾观察 5 件建档; 全链线性推送 Gitee
