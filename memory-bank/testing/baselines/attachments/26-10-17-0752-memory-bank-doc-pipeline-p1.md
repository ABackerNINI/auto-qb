# 3492 passed + 4 skipped(根) —— memory-bank 文档流水线 P1: 骨架(统一模板×命令化创建/更新)

> 摘要: 计划 26-10-17-0527(memory-bank-doc-pipeline)P1 骨架实施落地: 族登记表 `_common.FAMILIES`(plan/task/slice 三族单点: 命名正则/模板/状态词表/索引动作全复用既有单点 DOC_STATUSES·TASK_STATUSES·timekit, 不造第二套词表) · 三族模板(templates/plan.html·task.md·slice.md, SLOT 注释填空机制) · `kb.new`(plan/task 建档: 时间戳/命名/头部/SLOT 清单/索引全派生, 输出「剩余人工 N 项(判断 · 条件 · 机械 0)」收录断言) · `kb.wrap`(切片零 SLOT 即建即合规 + 抬最后活动/追加 R 行/同专题档案 Updated + 进度日志日期行派生, 只做机械面 D6) · 守卫 `check_doc_templates.py`(冻结线 26-10-17-0736 之后新建文件才查, 存量豁免; 残留 SLOT/状态词表外值/缺头部字段判红) · 守阵测试 7 条(三族冒烟/四条拒绝路径/零 SLOT 切片+档案回写/三突变红绿双验/冻结线豁免/族登记与模板对账/两处接线)。test.full 全绿收口。
> 基线时间: 2026-10-17 07:52

- 根 `test.full`(契约: 覆盖率门槛 98% + 包内 TMPDIR; 跑在含本轮知识库回写的同一棵树上): **3492 passed + 4 skipped in 140.68s**(套件总耗时 143.1s); TOTAL **17885 246 6012 180 98%**(语句/未覆盖/分支/partial/覆盖率)。比 S12 基线(3485+4)净增 7 条 —— 全是本轮 P1 守阵测试(`tests/test_memory_bank.py` 45 → 52), 无产品代码改动 ⇒ 语句数不变(17885), 覆盖率同为 98%。
> 勘误 (26-10-17-0845 补记): 本切片首版「52 → 59」系笔误 —— P1 前为 45、P1 后为 52 (`git show <P1提交>:tests/test_memory_bank.py` 回算核实), 现值 57 是 P2 的 +5; 本条已就地更正, 首版的错误快照留在 P2 基线切片的勘误节里备查。
- `kb.check` 全绿(含新增面检查 1 件在检查面、全部通过); cap 债务 3 项不变(132→133 切片数, 两条超 cap 切片), 均为存量, 不拦提交。

## 本改动面

- `.agents/skills/memory-bank/scripts/_common.py` —— 新增族登记表段: `TASK_DOMAINS`(webui/backend/rule/memory-bank/docs/test/deps/config 八域) · `TASK_STATUSES`(档案 4 词表, 与 gen_tasks_index 共用后删除其本地副本) · `PLAN_FILE_RE`/`TASK_FILE_RE` 命名正则 · `SLOT_RE` · `FamilySpec`(frozen dataclass: name/dir/ext/template/statuses/default_status/index_script/naming_re/domain_first) · `FAMILIES` 字典(plan→DOC_STATUSES+gen_docs_index / task→TASK_STATUSES+gen_tasks_index / slice→无词表无索引, 三族全 import 既有单点)
- `.agents/skills/memory-bank/templates/`(新增三件) —— `plan.html`(暗色样式原样搬现存计划, `@@TITLE@@`/`@@TOPIC@@`/`@@STAMP@@` 占位 + doc-meta 头 + §01–§10 骨架, 全部段首留 `<!-- SLOT: 说明 -->`) · `task.md`(Status/Added/Updated/Summary/Topics 五头部字段, Summary 由 --title 预填即裁定 A1; 无 Refs 行——A3 留人工) · `slice.md`(机械核三行头 + R0 先行, 可选骨架段置后——kb.wrap 截断在 R0 行即零 SLOT)
- `.agents/skills/memory-bank/scripts/new_doc.py`(新增) —— `kb.new`: timekit.now() 取 UTC+8; plan 文件名 `{stamp}-plan-{topic}.html`, task `{date}-{topic}.md` 且领域首段须过 TASK_DOMAINS; 同路径/档案撞名(含跨 clone `../auto-qb-*/`)幂等拒 rc=1; slice 族指路 kb.wrap; `--refs` 接受即拒并说明 D4 反向认领在 P2(防单向认领链判红); 渲染后写(newline=\n); 靶向重建索引(直接调 gen_docs_index.build/gen_tasks_index.build, 不绕 gen_all); 收尾打印 SLOT 清单 + 「剩余人工 N 项(判断 · 条件 · 机械 0)」
- `.agents/skills/memory-bank/scripts/wrap_session.py`(新增) —— `kb.wrap`: 切片不存在→按模板建并截断在 R0 行(零 SLOT, §5.3 判断剩余 0 即裁定 A6); 存在→抬「最后活动」+ 追加 `**RN(time):** did`(RN=现有最大+1); 按 Topics 匹配同专题档案→抬 `**Updated:**` + 追加 `- {stamp} {did}` 进度日志行(A5 日期属派生面); 档案被动则重建 tasks 索引; 同样打印「机械 0」收录断言
- `.agents/skills/memory-bank/scripts/check_doc_templates.py`(新增) —— `FREEZE_LINE="26-10-17-0736"`; 只查冻结线后新建的族文件(plan 按 doc-added 戳/task 与 slice 按文件名日期), 存量豁免(沿 doc-forms 51 份豁免先例); 校验命名正则/头部字段(plan: doc-type/doc-topic/doc-status∈DOC_STATUSES/双戳; task: Status∈TASK_STATUSES+Added/Updated/Summary/Topics; slice: 三行头)/全文与头部区零残留 SLOT; `--check` 模式 rc 反映通过面
- `.agents/skills/memory-bank/scripts/gen_tasks_index.py` —— 4 词状态表删除本地副本, 改 `from _common import TASK_STATUSES as STATUSES`(P1 单点化收编)
- `.commands/kb/config.toml` —— 经 add 协议收录 `kb.new`(when/note/timeout 齐全) 与 `kb.wrap`; kb.check 的 run 清单 += `check_doc_templates.py --check`
- `.commands/my-commit-flow/.my-commit-flow.toml` —— memory-bank/ 门禁 run 清单同步 += 同一检查器(守 `test_commit_gate_covers_kb_check`: kb.check 里每条 --check 必须在门禁出现)
- `tests/test_memory_bank.py` —— 新增 7 条守阵 + 3 个进程内 import helper(`_new_doc`/`_wrap`/`_doc_templates` 插 SKILL_SCRIPTS 进 sys.path, 不起子进程——sidefx POPEN 记账禁越界): ①三族真建+「机械 0」断言+填后复绿 ②四条拒绝路径(slice 族/--refs/坏 topic 非 kebab/坏领域/重复建) ③kb.wrap 零 SLOT 建切片+R1 追加+档案 Updated+进度日志行 ④三突变(删状态行/词表外值/留 SLOT)判红+逐类还原复绿 ⑤冻结线前后各一 task+plan, 存量豁免精确到件 ⑥族登记与模板烘焙默认值对账(statuses is DOC_STATUSES/TASK_STATUSES 身份断言) ⑦两处接线存在性
- 真实冒烟(经命令运行器 show/run 全链路, 落 /tmp 临时目录, 未提交): kb.new plan(10 处 SLOT, 判红→证明守卫拦「没填完」)/ kb.new task(5 处 SLOT, 判红)/ kb.wrap(零 SLOT 切片, 直接过守卫)——三族输出均含「机械 0」断言行; 冒烟目录已删

## 未动(范围守恒)

- P2(证据列/D4 反向认领自动补链)、P3(文档回写)——计划 §07 后续行, 本轮不动; `--refs` 输入面已留位但判拒
- 计划 HTML 与切片 R3 记录的计划内回写按 §08 待拍板项处理, 未触发即不建任务档案(请求边界: 新建文件须用户逐项显式确认)
- cap 债务 3 项(切片 133>70; 26-10-15-0728 19,412; 26-10-16-0541 13,905): 存量, 不拦提交, 转告用户另开会话清理
- MSYS2 heredoc 反斜杠吞转(正则 `\*` 被路径转换成 `/*`, 冒烟脚本静默失配; 已改用无反斜杠行过滤绕开)——候选坑档, 未立(触发词二期)
