# 26-11-15-backend-relocate-resume-confirm — relocate 恢复确认账与 fuse 让路: issue 26-11-14-1744 两件修复 + webui 待恢复余量展示

**Status:** Done
**Added:** 2026-11-15
**Updated:** 2026-11-15
**Summary:** fuse to_pause 三支让路(P1 查 relocating_hashes, 后经接缝终审 0441 收窄为 resuming 账窗口) + resume 恢复确认账(四出口开账/每拍对账/30s 退避补发至多 3 次/穷尽挂账照常终态) + webui 待恢复余量展示(投影四字段+文案单点+抽屉/浮窗); issue 26-11-14-1744 两件翻 Done, 邻接面 5 条入池 + 接缝终审收口入池 2 条(已修翻 Done), 合计入池 7 件; 另 flaky 用例入池 1 条(26-11-15-0546, 与本专题无交集)
**Topics:** backend-relocate-resume-confirm
**Refs:** memory-bank/issues/26-11-14-1744-bug-fuse-no-relocating-yield.html, memory-bank/issues/26-11-14-1744-bug-resume-fire-once-no-verify.html, memory-bank/issues/26-11-15-0344-bug-resume-account-overwrite-jobid-reuse.html, memory-bank/issues/26-11-15-0345-bug-resume-pending-deleted-member-unclosed.html, memory-bank/issues/26-11-15-0345-feat-relocate-failure-counters-no-consumer.html, memory-bank/issues/26-11-15-0345-bug-resume-popover-terminal-job-null.html, memory-bank/issues/26-11-15-0345-refactor-webui-borrow-relocate-private-constant.html, memory-bank/issues/26-11-15-0441-bug-fuse-armed-window-yield-stall.html, memory-bank/issues/26-11-15-0441-bug-resume-exhausted-display-premature.html, memory-bank/issues/26-11-15-0546-bug-hr-discovery-start-all-busy-flaky.html, memory-bank/pitfalls/backend/derived-registry-sync-points.md

## 本篇只回答

issue 26-11-14-1744 两件(fuse 不让路 relocating_hashes / resume 单发即弃)修成什么形态、语义拍板了什么、验证链与守阵怎么钉 —— 机制细节单点在代码注释与测试, 本档案只留决策与验证链; 展示口径事实行单点在 conventions/webui.md「迁移状态展示口径」。

## 原始请求

1. 修复 issue 26-11-14-1744 两件(2026-11-14 grilling D5 入池, 用户拍板修复): fuse 保险丝全库扫描不让路 relocating_hashes + relocate 恢复成员单发即弃(无重试无确认无对账)
2. resume 修复拆两批: P2a 机制(恢复确认账)先行, P2b 展示(webui 待恢复余量)随后
3. 收尾: 全量基线切片 / 两 issue 翻 Done / 评审邻接面 5 条入池(用户显式确认「5 条全入池」) / 主题回写 / 本档案立档

## 思考过程与决策

- **P1 fuse 让路(0f4582d2)**: 让路登记补齐第 4 个消费方——to_pause 三支收集点(`_scan_unmanaged` 监控支 / `_advance` armed 支 / `_advance` triggered 分支)各查 relocating_hashes(getattr 单点, ops_skip 同款口径)。语义拍板: **窗口拍不计连击**——被让路成员 confirm_count/_streak 清零, 解除后从零累计(保留计数 = 让路拍虚增连击、变相缩短按住时距)。(让路登记面后经接缝终审 0441 收窄为 resuming 账窗口, 见下方接缝条)
- **接缝终审 2 条修复(f617cad7/4dea136e)**: ①穷尽展示文案 decorate.js「补发穷尽, 需手动恢复」→「不再补发」——下发拍即为真, 不对「是否需手动恢复」作时点承诺(方案 B, 后端投影与机制零改动); ②fuse 让路口径收窄——旧口径让路窗口=relocating_hashes(job 级登记, armed 期恢复运行的真实拉流也被当回声清零连击, 保护停摆至 job 终态), 收窄为「恢复确认账在走」: 新登记 `store.resuming_hashes`(账窗口=resume_pending 非空并集, 非 job 窗口, 扫全部 job 含终态挂账), 重算双挂点(`_note_resume_state` 落账直呼——该点不走 `_set_job` 是关键坑, 只挂漏斗会滞后一拍; `_sync_relocating` 漏斗末尾兜底), fuse 三支谓词 relocating→resuming; relocating 登记与其余三消费方(grouping/ops_skip/qbapi D16)零改动。修向②用户拍板(候选①③有复活 1744 误暂停面风险)。
- **P2a resume 机制(952d3daa)**: 单发即弃收口为「开账 + 每拍对账 + 有界补发」: 四出口(_arm/_finish_direct/relocate_cancel/_fail)一律开账; on_task_line 末尾 `_reconcile_resume_pending` 扫全部 resume_pending 非空 job(含终态), 对照 store 快照核对 pending 成员回非 stopped 态, 未回去的按 `_RESUME_RETRY_SECONDS=30.0` 退避补发(只含仍停着的成员), `_RESUME_RETRY_MAX=3` 穷尽后不再发 qB 写, 余量挂账 + 计数告警每开账回合一笔。设计定案: **穷尽后照常终态 + 余量挂账**(账与相位解耦, 不阻塞收尾); job 新字段 resume_pending/resume_retries 序列化进 job_to_dict/job_from_dict(旧账缺字段=空账); _finish_direct 次序改 **done 落账后再恢复**(否则终态出口先翻 done 丢账)。
- **P2b 展示(90e15489)**: `views_relocate.py::member_relocate` 投影 +4 字段(resume_pending_count/hashes/retries/exhausted; 穷尽上界借 relocate_lifecycle 私有常数不复制数值——升公共面的时机入池记账); 前端文案单点 `relocateResumeText`(decorate.js, 空账零噪音, 穷尽/在途区分位只认后端); 抽屉两条件行(drawer_rows.js) + 浮窗 kv 行(relocate_pop.js); 机制文件零改动。
- **测试**: P1 `tests/test_fuse_mod.py` +3 例; P2a 新 `tests/test_relocate_resume_confirm.py` 14 用例全 FakeClock; P2b `test_webui_relocate_visibility.py` +3 例 + `test_webui_relocate_pop.py` 探针扩段。
- **复验**: 2026-11-15 锚点均仍复现后开修(fuse :90/:148/:185, 收集点 :178/:223/:235; `_resume_members` :148, 调用点 :584/:598/:1796/:176)。
- **评审统计(全轮累计)**: P1 全能档 1 员 1 轮零发现; P2a 分面 2 员 2 轮(轮 1 六条: 2 minor 4 nit, 全修); P2b 分面 2 员 2 轮(轮 1 两条 minor, 全修); 收口接缝终审零 blocker/major, 2 条发现全入池(见进度日志 R1)。
- **评审邻接面 5 条入池**(topic relocate-move-window, 见 Refs): 同 (mover,src,dst) job_id 复用整段覆盖旧账 / 已删成员 resume_pending 永不闭合 / _tag_failures+_resume_failures 无消费面 / 终态账浮窗不弹(done/cancelled 恒 null 边界; failed 在触发表内会弹, issue 正文按代码取证收敛) / webui 跨层借私有常数。

## 实现计划

无分步计划文档(按批实施): P1 让路三支 + 连击语义拍板 → P2a 机制批(账字段/每拍对账/退避补发/穷尽挂账/序列化/出口次序) → P2b 展示批(投影/文案单点/两消费面) → 分批评审循环 → 收尾回写。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| P1 | fuse to_pause 三支让路 + 窗口拍清零连击 + 3 例(0f4582d2) | Done(2026-11-15) |
| P2a | resume 确认账机制批: 四出口开账/每拍对账/退避补发/穷尽挂账/序列化(952d3daa) | Done(2026-11-15) |
| P2b | webui 待恢复余量展示: 投影四字段+文案单点+抽屉/浮窗(90e15489) | Done(2026-11-15) |
| 收尾 | 基线切片 / 两 issue Done / 5 条入池 / 展示口径回写 / 本档案 | Done(2026-11-15) |
| 接缝① | 穷尽展示文案改「不再补发」: decorate.js 单点+注释/docstring+webui.md 口径行+两断言(f617cad7) | Done(2026-11-15) |
| 接缝② | fuse 让路收窄 resuming 账窗口: store 新登记+双挂点+三支谓词+测试改造 3 新增 4(4dea136e) | Done(2026-11-15) |
| 终态收尾 | 终测基线切片 / flaky 入池 / 新口径回写 / 坑档 / kb.wrap | Done(2026-11-15) |

## 进度日志

### R0 · 立档 (2026-11-15)

三批实施 + 评审循环全过(统计见上), 收尾回写落位: 全量基线见 kb.baseline(backend-relocate-resume-confirm 最新切片); 两 issue 翻 Done(复验行 + 修法/验证/与建议修法差异补齐); 评审邻接面 5 条入池; 展示口径事实行进 conventions/webui.md「迁移状态展示口径(路径列)」; 计划 26-11-14-1741 变更记录补 D5 后续一行(该计划 S1-S4 不受影响仍待开工)。

- 2026-11-15 03:52 收尾回写: 全量基线切片+两 issue 翻 Done+邻接面 5 条入池+webui.md 展示口径事实行+计划 1741 变更记录补 D5 后续
- 2026-11-15 04:42 接缝终审收口(5 接缝面): 零 blocker/major, 2 条发现全过引文校验, 用户拍板全入池(第 6/7 件, doc-refs 已双向): fuse armed 窗口让路语义缺口(26-11-15-0441-bug-fuse-armed-window-yield-stall) / 穷尽展示时点超前(26-11-15-0441-bug-resume-exhausted-display-premature)

### R2 · 接缝终审 2 条修复与终态收尾 (2026-11-15)

两件接缝入池件各自修复+评审后翻 Done(f617cad7 批次评审零发现; 4dea136e 评审 2 轮修 3、修复轮零新增), 语义拍板见「思考过程与决策」接缝条; 展示口径行 conventions/webui.md 已随 f617cad7 同步无残留漂移; 全量终态基线新切片见 kb.baseline(backend-relocate-resume-confirm 最新切片); ship.gate 观察到的 test_hr_discovery 计时敏感 flaky 入池 26-11-15-0546(与本两修无交集); fuse 让路新口径(resuming 账窗口/登记重算双挂点)按坑档口径记 `pitfalls/backend/derived-registry-sync-points.md`。

- 2026-11-15 05:54 接缝终审 2 条修复翻 Done: 穷尽展示文案改「不再补发」(f617cad7) + fuse 让路收窄 resuming 账窗口(4dea136e, store 新登记+双挂点); 终态基线切片 0549, flaky 用例入池 0546, 新口径回写档案与坑档
