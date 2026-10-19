# 26-10-17-ship-commit-clean-tree-routing — ship.commit 树净拒跑按远端真值分流 + 核 ref 假红不再自相矛盾

**Status:** Done
**Added:** 2026-10-17
**Updated:** 2026-10-17
**Summary:** 用户转述另一会话现场: 「`ship.commit` 首跑 提交成功但报了『没有可提交的改动』并中止推送(疑似内部幂等步误判, 提交对象已正确落稳)」→ 要求分析原因; 结论确认后用户「按建议修」。根因 = **两次调用被读成一跑**: 首次 `ship.commit` 因同步/推送失败停在「提交成功 <hash>(未推送)」, 随后**又跑 `ship.commit`(而非 `ship.push`)** ⇒ 树已净 ⇒ 撞 `resolve_stage_plan` 的拒跑出口(该出口在 commit/sync/push 之前 `return 1`)。旧拒跑文案「工作区干净(改动在别的 clone 或未保存?)」把「提交已在本地、只差推送」误导成「改动没落笔」(报告里被读成"提交丢了"); 核 ref 假红出口在**已判定落稳**时仍写「提交可能没落稳」, 进一步诱导重跑 `ship.commit`。落盘(缺省路径, 未新建配置项): ①`commit.py` 新增纯函数 `clean_tree_route(cfg)` —— 树净拒跑行按**远端现查真值**(`ls-remote`, `attempts=1`)三档分流(本地领先 → 直送 `ship.push`; 一致 → 确实无事可做; 取不到 → 如实说「无法核实」并摆两条出路); 拒跑路径补后缀只在**树净**时接(有改动时照旧)。②核 ref 假红出口去掉自相矛盾: 保留 rc=1 与「提交失败」前缀(不加假装成功的改法 —— ref 不一致仍可能是分支指针真被回退), 但结果行如实写「提交已落稳, 仅分支 ref 未核对通过」并直送补推。③`sync.py` `remote_sha` 加 `attempts` 形参(旁证查询收紧到 1, 不让拒跑路径白等三个退避周期)。变更集 3 个源文件 + 包内口径件 ⇒ 命中立档阈值, 建本档(无 issue: 本轮由外部报告驱动, 非 `issues/` 池内件)。测试数字唯一权威在基线切片(见 **Refs:**)。
**Topics:** ship-commit-clean-tree-routing

**Refs:** memory-bank/pitfalls/git/push.md
## 原始请求

> 用户(2026-10-17): 「另一会话报告: 一点说明：`ship.commit` 首跑 提交成功但报了「没有可提交的改动」并中止推送 （疑似内部幂等步误判，提交对象已正确落稳）\n分析原因」
> 用户(2026-10-17): 「按建议修」
> 用户(2026-10-17): 「提交」

## 思考过程与决策

- **请求边界**: 首条 = 问答/只读(分析原因, 只在回复里作答); 第二条「按建议修」= 执行任务(经边界提示后用户显式点头才动代码); 末条「提交」= commit + push 单点授权(触发词口径), 并触发收尾 DoD 回写。
- **根因定位(纯代码事实)**: `resolve_stage_plan` 的拒跑 `return 1` 是**唯一**树净出口, 且在闸门 / `git commit` / `from sync import run_sync` / `run_push` 全之前 —— 故「提交成功」与「没有可提交的改动」逻辑上不可能同出一跑 ⇒ 必是**两次调用**(首次已落稳于本地 + 二次撞树净拒跑)。报告里「疑似内部幂等步误判」的假设被排除: 不存在内部幂等步骤。
- **误读链**: ①旧拒跑文案「改动在别的 clone 或未保存?」在为真时(提交只差推送)错误归因; ②核 ref 假红出口(packed-refs 滞后类误报, 2026-10-07 已实证)在 HEAD 消息已与本次一致 = 已落稳时, 仍照旧文案写「提交可能没落稳」 —— 两处合起来把人推向「重跑 `ship.commit`」, 而正确动作是 `ship.push`。
- **修法取舍**: 拒跑行不能只在配置里写死「去推」—— 树净有两种真相(本地领先 / 已一致), 必须**现查远端真值**分流。判据只认 `ls-remote`(本环境 `refs/remotes/*` 写入被静默丢弃、`status -sb` 是快照, 都不可信; 单点 `pitfalls/git/refs.md`)。取不到真值时**不猜**, 如实说「无法核实」并把两条出路都摆出来。
- **一处有意偏离用户建议**: 原建议②是把落稳的结果行改成「提交成功 <hash>(未推送)」语义; 实施时**否掉假装成功** —— ref 三处不一致仍可能是分支指针**真被回退**(`classify_form` 分流为一档), 若放行 rc=0, 调用方(脚本 / 人)会顺手去推一个可能已被回退的指针。改为**保留 rc=1 与「提交失败」前缀**, 只去掉自相矛盾那句并直送 `ship.push`(见「实现计划」S2)。
- **旁证查询不白等**: 拒跑路径上的「本地是否领先远端」是**旁证**而非同步判据 —— `remote_sha` 收紧到 `attempts=1`(默认仍 3), 否则离线时一句「确实无事可做」要白等三个退避周期。
- **立档判定**: 变更集源文件 3 个(`commit.py` / `sync.py` / `test_commit.py`)命中阈值 #2 ⇒ 建本档; 认领链双向(本档 ↔ 切片 · 本档 ↔ 坑档)。

## 实现计划

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 开工同步 + 路由(pitfalls/git refs·push + `_pipeline` 步骤登记 + 包内 pipeline.md) | Done |
| S2 | 只读定位根因(拒跑出口唯一性 + 两次调用定性 + 文案误读链) | Done |
| S3 | 修①: `commit.py::clean_tree_route(cfg)` 三档分流 + 拒跑行后缀(仅树净接) | Done |
| S4 | 修②: 核 ref 假红出口结果行去掉自相矛盾 + 直送补推(保留 rc=1) | Done |
| S5 | 修③: `sync.py::remote_sha` 加 `attempts` 形参(旁证查询 attempts=1) | Done |
| S6 | 守阵: `test_commit.py` 新增 3 条用例 + 头部「## 测试计划」清单 + 既有断言加严 | Done |
| S7 | 包内口径回写 `references/pipeline.md`(拒跑分流 + 已落稳结果行口径) | Done |
| S8 | `dev.fmt` + `test.pkg` / `test.quick` / 定向 `-k clean_tree` 验证 | Done |
| S9 | 坑档 `git/push.md` 增「树净别重跑 ship.commit」条目 + `kb.index`/`kb.check` | Done |
| S10 | `test.full` + 基线切片 + 本档随该笔入库(`ship.commit`) | Done |

## 子任务状态表

| 子任务 | 状态 | 说明 |
|---|---|---|
| 树净拒跑按远端真值分流 | Done | `clean_tree_route`: 本地领先 → `ship.push`; 一致 → 无事可做; 取不到 → 两条出路 |
| 核 ref 假红结果行去自相矛盾 | Done | 已落稳如实写「提交已落稳, 仅分支 ref 未核对通过」+ 直送补推; rc 仍 1 |
| `remote_sha` 旁证查询收紧 | Done | 新增 `attempts` 形参, 拒跑路径传 1 |
| 守阵(3 条 + 断言加严) | Done | 领先 / 一致 / 离线三态; 既有「已落稳」用例加严两条断言 |
| 包内口径回写 | Done | `references/pipeline.md`(非 memory-bank, 包内单点) |
| 坑档 | Done | `pitfalls/git/push.md` 新条目(触发/判别/处置)+ 反向声明本档 |
| 基线切片 | Done | `testing/baselines/26-10-17-0909-ship-commit-clean-tree-routing.md`(数字唯一权威) |
| 提交入库 | Done | `ship.commit`(结果行见会话回复) |

## 进度日志

- **2026-10-17 08:5x 分析轮(只读)**: 用户转述外部报告要求分析原因 ⇒ 定位到「两次调用 + 拒跑文案误归因 + 核 ref 假红自相矛盾」三点, 回复给出根因与两处修法建议(未动代码)。
- **2026-10-17 09:0x 修复轮**: 用户「按建议修」⇒ 落盘 S3–S7; `dev.fmt` 通过; 定向 `test.pkg` 全绿、`-k clean_tree` 三例全绿(老代码上三者皆红 ⇒ 判红力可验); `test.quick` 全绿。一处有意偏离用户建议②已在「思考过程与决策」写明。
- **2026-10-17 09:0x 收尾**: 坑档新增条目 + `push.md` 反向声明本档; 本档与切片新建; `kb.index` / `kb.check` 全绿; `test.full` 全绿(数字见基线切片)。
- **2026-10-17 09:09 提交**: 收尾回写件随本笔入库(`commands run ship.commit`)。

## 未做 / 残留(转告)

- **未做**: 拒跑行的分流**未配置化**(硬编码在 `clean_tree_route`; `ls-remote` 主机名取自 `resolve_main_remote`, 已是单点) —— 若将来要按远端名定制文案再议, 现无需求。
- **残留(本机环境, 与本次改动无关)**: `test.full` 在沙箱内会因 `TMPDIR`(R: 盘)收尾清理被拦而退出码非 0, pytest 本身全绿; 关沙箱复跑即 rc=0(见 `pitfalls/testing/tmpdir.md`)。
- **cap 债务转告(本会话不修)**: `activeContext/26-10-15-0728-qb-traffic-restart-spike-gap.md`(超切片 cap)、`activeContext/26-10-16-0541-global-traffic-monitor.md`(超切片 cap)、切片数超阈值 —— 另开新会话清理(`commands run doc.caps` 现算)。
