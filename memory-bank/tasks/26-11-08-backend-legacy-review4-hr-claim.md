# 26-11-08-backend-legacy-review4-hr-claim — 存量评审 R4·hr 21 条认领修复(0527-hr)

**Status:** In Progress
**Added:** 2026-11-08
**Updated:** 2026-11-08
**Summary:** 存量评审 R4·hr 21 条认领修复(0527-hr)
**Topics:** backend-legacy-review4-hr-claim
**Refs:** memory-bank/issues/26-11-07-0527-bug-legacy-review4-hr.html, memory-bank/testing/baselines/26-11-08-0834-backend-legacy-review4-hr-claim.md

## 本篇只回答

存量评审 R4 聚合件 26-11-07-0527-bug-legacy-review4-hr(major 4/minor 17, 14 文件)的 21 条 findings 如何按主题分 7 批认领、实施、评审并全部收口;含各条落点、4 个用户拍板决策、评审发现与修复、全量基线数字。领域性结论(hr 网关鉴权形态/波次节奏闸口径/relocate journal 协议)散见各提交信息与 issue 修复后补充,不在此重复成文。

## 原始请求

<!-- wording:allow --> 1. 用户指派: 修复 `memory-bank/issues/26-11-07-0527-bug-legacy-review4-hr.html`(存量评审 R4 hr 汇总, 21 条); 要求: 先拆解任务, 派子智能体分阶段依次实施; 大任务拆小防 O(n^2) token 消耗与进度丢失, 关联小任务可合并; 不并列执行(防超并发), 一个一个来; 待拍板的先询问; 主会话只委派与总结; 开新本地分支, 每步 `my-commit-flow.commit --no-push` 本地提交; 全程在本地分支; 完成后同步到本地 develop 等提交指令; 子智能体提前停止用 SendMessage 续跑; 非正常失败 3 次停止等人工。
2. 拍板轮(AskUserQuestion 四项): ①#1 鉴权 token 修法=双保险(validate_config 限 ASCII + 比较前 encode); ②#3 guardian failed 相位修法=对账表消费 failed(转 job failed 终态); ③#4 限速视图修法=置 view_changed=True; ④评审派遣=每批单评审员(敏感面点名, 偏离 skill 分面表用户认可)。
3. 收尾拍板: 「入池然后提交」——授权实施期发现的 6 条计划外问题入池 + 授权提交推送。

## 思考过程与决策

- 拆解: 按「同文件聚类+行为风险隔离」分 7 批(S1 hr 网关面 5 条/S2 service_wave 波次核心 4 条/S3 relocate 对账 1 条 major/S4 model/store 数据层 3 条/S5 torrents+transfer 3 条/S6 worker+status 4 条/S7 pitfalls 文档 6 文件), 每批=实施子代理→review.pack→只读评审(code-reviewer)→review.check 引文校验→裁决修复→ship.commit --no-push。
- 提交口径: 用户口中的 my-commit-flow.commit --no-push 实际 task id 为 `commands run ship.commit --no-push`(原生支持, 不同步不推送)。
- 每 commit 自动过提交闸门(全量 test.quick + review.trace 行数实算 ±0 + fmt + 索引守卫), 等于每批一次全量回归。
- S3 背景核实: claim 的 90s 无限重拉在 HEAD 不可发生(guardian 已于 66418c7e 退役), 但消费者缺口真实(旧版残留 failed journal 证据自毁+永不收敛), 按拍板方向修; 两处声明偏差(failed 纳入 STOP_PHASES 单点/journal 即终相位 + 新鲜度锚点三态防误消费)经两轮评审确认正当。
- S4 #8 守卫面扩大(writer/HrWaveMeta 内层)经评审核定有据: 「站点文件读坏时不抛」契约覆盖整个读路径。
- 合流: rebase 到远端新 develop(另一会话同期认领了同批聚合的姊妹件 config-infra 36 条, 范围互补)零冲突; 其 relocate 嵌套闸门工作与 S3 语义相邻, 合树后跑 test.full 全绿确认共存。
- 备份纪律: rebase(高风险历史整合)前 `cp -a .git /d/Projects/zcode/.gitbak-clone3-review4-20261108`。

## 实现计划

每批固定流水(独立可验): ①实施子代理(符号重定位→修→补测试→test.one 定向回归→dev.fmt) ②review.pack 取批次面 ③只读评审子代理(三件套+三钉, 全能档) ④review.check 引文校验 ⑤相关发现派回原实施者修(修复增量>100 行追加一轮评审) ⑥写 COMMIT_MSG_AI.txt(含 Review: trailer 实算行数)→`ship.commit --no-push`。收口: test.full 基线→接缝终审(5 项清单)→rebase 合树→test.full 复验→ff 合回 develop。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | hr 网关面 5 条(#1/#6/#10/#11/#12), 提交 7c896731 | Done(2026-11-08) |
| S2 | service_wave 4 条(#2/#9/#13/#14), 提交 14e2f523 | Done(2026-11-08) |
| S3 | relocate 对账消费 failed(#3, 2 轮评审 4 发现全修), 提交 9b4b34fc | Done(2026-11-08) |
| S4 | model/store 3 条(#7/#8/#17, 闸门补 2 行测试计划), 提交 20054cad | Done(2026-11-08) |
| S5 | torrents/transfer 3 条(#4/#20/#21), 提交 b670d9d6 | Done(2026-11-08) |
| S6 | worker/status 4 条(#15/#16/#18/#19, 评审 2 minor 修), 提交 abbeea83 | Done(2026-11-08) |
| S7 | pitfalls 符号对位 6 文件(#5), 提交 415677de | Done(2026-11-08) |
| 收口 | test.full 5779+2/99% + 接缝终审零发现 + rebase 合树 5779 绿 + ff 合回 develop | Done(2026-11-08) |
| 收尾 | 6 条计划外入池 + issue 0527-hr 置 Done + 切片/基线 + 提交推送 | Done(2026-11-08) |

## 进度日志

### R0 · 立档 (2026-11-08)

21/21 条按 7 批收口: 每批过只读评审(S3 两轮, 全程 10 次评审派遣, 发现 8 条全修/全过检), 合树 test.full 5779 passed + 2 skipped 覆盖率 99%, 接缝终审零发现。develop 本地 HEAD 415677de(7 笔, +1148/-117, 38 文件)。计划外 6 条入池(compare-digest 同构×2/头部读路径 reset/_as_int OverflowError/relocate _arm journal 根治题/docstring 漂移聚合/小件清理聚合)。存量警告: issues 索引超 8k 字符预算(Open 区条数病根, 建件前已 10,107, 现约 12k), 待人工清理在办区。

- 2026-11-08 08:34 R0: 0527-hr 21 条按 7 批收口(7c896731..415677de), 每批评审+提交闸门, 合树 test.full 5779+2/99%, 接缝终审零发现; 计划外 6 条入池, issue 0527-hr 置 Done
