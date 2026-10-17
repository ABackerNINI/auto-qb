# 3502 passed + 4 skipped(根) —— memory-bank 文档流水线 P3: 收尾与二期族(四族模板×注册表×守卫扩面×文档回写)

> 摘要: 计划 26-10-17-0527(memory-bank-doc-pipeline)P3 实施落地: 族注册表 `_common.FAMILIES` 扩四族(pitfall 带 `--class` 7 类枚举子目录 + `--triggers` 三行头 / report 出厂即 Done / baseline `--total` 誊写且无索引 / progress 三行头) · 四族模板落 skill `templates/`(SLOT 只在正文区, 头部机器字段全派生; A7 裁定走 `--triggers` 参数分支) · `kb.new` 接入四族分派(参数 fail-fast + 剩余人工契约 + D4 双向补链对坑档形态实测) · 守卫 `check_doc_templates` 扩面(validate_file 增四族 + 扫描面增 reports 与 testing/baselines; 坑档/进展件命名无时间戳按既有口径跳过) · 文档回写(doc-forms「创建/更新方式」节 / 根 AGENTS.md 会话协议两行 / README 细路由 / SKILL.md DoD 并入 kb.wrap) · 守阵 4 条全绿(四族冒烟红绿双验 / 参数 fail-fast / 坑档 D4 补链 / 报告三类突变) + 注册表同源守阵扩展(含头部区零 SLOT 契约)。test.full 全绿收口; `kb.status`/`kb.bump`/`kb.new baseline` 均在真件上狗粮自验通过。
> 基线时间: 2026-10-17 09:44

## 验收数字

- 根 `test.full`(契约: 覆盖率门槛 98% + 包内 TMPDIR; 跑在含本轮知识库回写的同一棵树上): **3502 passed + 4 skipped in 121.44s**(套件总耗时 123.8s); TOTAL **17885 246 6012 180 98%**(语句/未覆盖/分支/partial/覆盖率)。比 P2 基线(3498+4)净增 4 条 —— 全是本轮 P3 守阵测试(`tests/test_memory_bank.py` 58 → 62), 无产品代码改动 ⇒ 语句数不变(17885), 覆盖率同为 98%。
- `kb.check` 全绿(新增面检查含 report/baseline 两个新扫描面, 冒烟件在 tmp 夹具不入库); `doc.drift` 无手抄(0 处); `doc.caps` 绿(AGENTS.md 7,282/8,000, 余量 718); cap 债务 2 项不变(`pitfalls/testing/redverify-anchor-lineendings.md` 14,596>12,000 · `progress/implemented-core.md` 21,038>20,000), 均为存量, 不拦提交, 转告用户另开会话清理。
- 狗粮自验(真件非夹具): `kb.status` 翻转计划 HTML(In Progress → Done, 终态带切片迁出提醒) · `kb.bump` 追加 R5 行(doc-updated 抬至 26-10-17-0944) · `kb.new baseline` 建本切片(戳/命名/头部/基线时间全派生, 2 处 SLOT 待填)。

## 本改动面

- `.agents/skills/memory-bank/scripts/_common.py` —— 族注册表扩四族: `REPORT_FILE_RE` 命名正则(与 PLAN_FILE_RE 同款 stamp+type 形态) · `FamilySpec` 增 `subdir_flag`/`subdir_values`(坑档子目录选择器, 默认空) · `FAMILIES` 增 pitfall(`dir=pitfalls` + `--class` 第二段, 命名 TOPIC_FILE_RE, 索引 gen_kb_index, subdir_values=PITFALL_CLASSES 单点) / report(`dir=reports`, 出厂 Done, 索引 gen_docs_index) / baseline(`dir=testing/baselines`, 复用 SLICE_FILE_RE 带时分命名, **无索引**——时间戳文件名即索引) / progress(`dir=progress`, 三行头, 索引 gen_kb_index) · `rebuild_index` 扩 `gen_kb_index` 分支(build_all 全量重建, 与 kb.index 同一实现)
- `.agents/skills/memory-bank/templates/`(新增四件) —— `pitfall.md`(`# 标题`/`> 摘要:`[--title 预填]/`> 触发:`[--triggers] 三行头 + `###` 条目骨架: 触发/判别/处置三必填 SLOT + 守阵 SLOT + 复发 0 选填; D4 的 `--refs` 经 md_set_refs 锚点链的三行头分支插入) · `report.html`(dark CSS 同 plan 族, doc-type=report + **出厂 doc-status=Done**, 骨架 结论/证据快照/方法与局限, 无变更记录段——kb.bump 对无段件 fail-fast 指路) · `baseline.md`(`# @@TOTAL@@ —— @@TITLE@@` + `> 基线时间:` 排序键 + `## 验收数字`/`## 本改动面` 骨架; `--total` 由 agent 誊写, 裁定 A4) · `progress.md`(三行头 + `## 叙述段` 骨架; `##` 标题使头部区边界可判定)
- `.agents/skills/memory-bank/scripts/new_doc.py` —— 四族分派: `--class`(dest=doc_class, 校验 PITFALL_CLASSES 单点, 扩类先改常量三处同步) / `--triggers`(pitfall/progress 必填, A7 参数分支——头部区零 SLOT 契约) / `--total`(baseline 必填, A4) 三参数全 fail-fast; 目标路径坑档带第二段子目录; `_print_remaining` 扩四族契约输出(判断 1 · 条件 0 · 机械 0 + 族别可选提示); docstring 同步
- `.agents/skills/memory-bank/scripts/check_doc_templates.py` —— `validate_file` 扩四族(plan/report 共用 doc-* 校验, doc-type 区分; pitfall/progress 三行头; baseline 头部三字段 + 基线时间严格格式) · `check_new_faces` 扫描面增 reports(doc-added ≥ 冻结线) 与 testing/baselines(stamp 前缀 ≥ 冻结线) · 坑档/进展件命名无时间戳不可判新旧, 按既有「分不清新旧跳过」口径不在扫描面(docstring 声明, 由 check_kb_structure 兜底) · `MD_HEADER_SPLIT_RE` 改 `##`+(坑档 `###` 条目正确结束头部区, SLOT 落点不再误报头部区)
- `tests/test_memory_bank.py` —— 新增 4 条守阵 + 头部测试计划清单同步 + 两条既有守阵扩展: ①四族真建冒烟(命名/头部/出厂状态齐 + 「机械 0」断言 + 建后残留 SLOT 判红填完判绿 + 扫描面恰 2 件) ②四族参数 fail-fast(缺/坏 --class、缺 --triggers、缺 --total) ③坑档 D4 双向补链(锚点链三行头分支) ④报告三类突变红绿双验(删 doc-status/词表外值/留 SLOT); 扩展: 族注册表同源(报告出厂 Done + doc-type、三行头触发词占位、基线 TOTAL/基线时间占位、坑档 subdir 单点身份断言、**全族模板头部区零 SLOT** 契约) · 冻结线测试扩 report/baseline 两个扫描面(线前豁免精确到件)
- `memory-bank/conventions/doc-forms.md` —— 新增「创建/更新方式(命令化, 2026-10-17)」节: 九条动作×task id 表(只放 task id, 不抄命令本体) + SLOT 填空机制/头部零 SLOT/`--refs` D4/切片不走 kb.new/issues 走 create-issue 四条口径; 三行头触发词补 `创建方式, kb.new, 命令化创建`
- 根 `AGENTS.md` —— 会话协议两行: 新增「建件与改版」入口行(kb.new/kb.status/kb.bump/kb.wrap 四条命令族清单) + 收尾行改版(机械面一条 kb.wrap + 立档/基线/新坑走 kb.new 族命令); 7,282/8,000 字符(余量 718)
- `memory-bank/README.md` —— 细路由新增一行「建制品/翻状态/改版/收尾」(命令化入口, 指向 doc-forms「创建/更新方式」)
- `.agents/skills/memory-bank/SKILL.md` —— 收尾 DoD 步骤 1-2 并入 kb.wrap(D6: 只做机械面, 蒸馏与判断仍是 agent 的活; 进度日志日期行由 kb.wrap 追加, 裁定 A5); 会话开始步骤 5 补「走 kb.new/kb.wrap 的件时间戳由命令派生」注记
- 计划 HTML(`memory-bank/plans/26-10-17-0527-plan-memory-bank-doc-pipeline.html`) —— §07 P3 行标「✅ 已实施验收(R5 · 26-10-17-0941)」 · A7 行记录 P3 裁定(走 `--triggers` 参数分支) · 正文 .meta 镜像 doc-status 与 doc-updated 同抬(经 kb.status 本体) · §10 追加 R5 行(经 kb.bump 本体落盘=狗粮自验)
- 基线切片(`memory-bank/testing/baselines/26-10-17-0944-memory-bank-doc-pipeline-p3.md`, 本件) —— 经 kb.new baseline 本体创建=狗粮自验

## 未动(范围守恒)

- 任务档案 `tasks/2026-10-17-memory-bank-doc-pipeline.md` 仍未建(§08 立档注记: 新建文件待用户显式确认, 确认后随本专题入库)
- 提交按用户显式指令另行触发(当前特性分支无远端对应 = ship 死锁, 见坑档 `pitfalls/git/unpushed-branch-sync.md`, 推送待用户终端 `push -u` 建立对应后 `ship.push`)
- cap 债务 2 项不变(`redverify-anchor-lineendings.md` · `implemented-core.md`): 存量, 不拦提交, 转告用户另开会话清理
- 冒烟夹具在 `tmp-analysis/p3-smoke/`(gitignored), 验毕即删, 不入库
