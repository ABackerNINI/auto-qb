# 26-11-15-backend-relocate-resume-confirm — relocate 恢复确认账与 fuse 让路: issue 26-11-14-1744 两件修复 + webui 待恢复余量展示

**Status:** Done
**Added:** 2026-11-15
**Updated:** 2026-11-15
**Summary:** fuse to_pause 三支让路 relocating_hashes(窗口拍清零连击) + resume 恢复确认账(四出口开账/每拍对账/30s 退避补发至多 3 次/穷尽挂账照常终态) + webui 待恢复余量展示(投影四字段+文案单点+抽屉/浮窗); issue 26-11-14-1744 两件翻 Done, 邻接面 5 条入池 + 接缝终审收口再入池 2 条(合计 7 件)
**Topics:** backend-relocate-resume-confirm
**Refs:** memory-bank/issues/26-11-14-1744-bug-fuse-no-relocating-yield.html, memory-bank/issues/26-11-14-1744-bug-resume-fire-once-no-verify.html, memory-bank/issues/26-11-15-0344-bug-resume-account-overwrite-jobid-reuse.html, memory-bank/issues/26-11-15-0345-bug-resume-pending-deleted-member-unclosed.html, memory-bank/issues/26-11-15-0345-feat-relocate-failure-counters-no-consumer.html, memory-bank/issues/26-11-15-0345-bug-resume-popover-terminal-job-null.html, memory-bank/issues/26-11-15-0345-refactor-webui-borrow-relocate-private-constant.html, memory-bank/issues/26-11-15-0441-bug-fuse-armed-window-yield-stall.html, memory-bank/issues/26-11-15-0441-bug-resume-exhausted-display-premature.html

## 本篇只回答

issue 26-11-14-1744 两件(fuse 不让路 relocating_hashes / resume 单发即弃)修成什么形态、语义拍板了什么、验证链与守阵怎么钉 —— 机制细节单点在代码注释与测试, 本档案只留决策与验证链; 展示口径事实行单点在 conventions/webui.md「迁移状态展示口径」。

## 原始请求

1. 修复 issue 26-11-14-1744 两件(2026-11-14 grilling D5 入池, 用户拍板修复): fuse 保险丝全库扫描不让路 relocating_hashes + relocate 恢复成员单发即弃(无重试无确认无对账)
2. resume 修复拆两批: P2a 机制(恢复确认账)先行, P2b 展示(webui 待恢复余量)随后
3. 收尾: 全量基线切片 / 两 issue 翻 Done / 评审邻接面 5 条入池(用户显式确认「5 条全入池」) / 主题回写 / 本档案立档

## 思考过程与决策

- **P1 fuse 让路(0f4582d2)**: 让路登记补齐第 4 个消费方——to_pause 三支收集点(`_scan_unmanaged` 监控支 / `_advance` armed 支 / `_advance` triggered 分支)各查 relocating_hashes(getattr 单点, ops_skip 同款口径)。语义拍板: **窗口拍不计连击**——被让路成员 confirm_count/_streak 清零, 解除后从零累计(保留计数 = 让路拍虚增连击、变相缩短按住时距)。
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

## 进度日志

### R0 · 立档 (2026-11-15)

三批实施 + 评审循环全过(统计见上), 收尾回写落位: 全量基线见 kb.baseline(backend-relocate-resume-confirm 最新切片); 两 issue 翻 Done(复验行 + 修法/验证/与建议修法差异补齐); 评审邻接面 5 条入池; 展示口径事实行进 conventions/webui.md「迁移状态展示口径(路径列)」; 计划 26-11-14-1741 变更记录补 D5 后续一行(该计划 S1-S4 不受影响仍待开工)。

- 2026-11-15 03:52 收尾回写: 全量基线切片+两 issue 翻 Done+邻接面 5 条入池+webui.md 展示口径事实行+计划 1741 变更记录补 D5 后续
- 2026-11-15 04:42 接缝终审收口(5 接缝面): 零 blocker/major, 2 条发现全过引文校验, 用户拍板全入池(第 6/7 件, doc-refs 已双向): fuse armed 窗口让路语义缺口(26-11-15-0441-bug-fuse-armed-window-yield-stall) / 穷尽展示时点超前(26-11-15-0441-bug-resume-exhausted-display-premature)
