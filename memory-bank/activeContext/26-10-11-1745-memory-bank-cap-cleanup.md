# 26-10-11-1745-memory-bank-cap-cleanup — cap 债务清零轮(索引三件 + 手写两件)

> 摘要: 用户令「清理 cap 债务」; 开工 `doc.caps -- --strict` 报 **5 项**(`issues/_index` 31,196 / `tasks/_index` 25,974 / `pitfalls/web-ui/_index` 25,940 / `implemented-webui.md` 23,251 / 档案 `26-10-08-test-mutation-audit.md` 56,960), 条数债务(切片 64 / 70)本就不超。按「**先量无摘要口径**」判据分三路治: ①**条目数撑爆**的 issues 索引走**视图归档**(不动文件): 生成器加 `CLOSED_KEEP=60`, 已关闭状态只渲染最近 60 条 + 全量清单另落 `issues/attachments/_archive.md`(48,932, 在 `EXCLUDED_DIRS` 不计 cap)⇒ 31,196 → 16,960; ②**摘要顶爆**的两份索引压渲染口径(`gen_tasks_index.SUMMARY_MAX` 60→30; `gen_kb_index` 新增 `SUMMARY_MAX=140` / `TRIGGER_MAX=120`)⇒ 20,190 / 15,986; ③两件手写文档按「切最老一半到 `attachments/`」外迁(档案 → 23,480; progress 件 → 10,362, 另把 41 条同质指针行压成一行省 5,642)。**为什么没搬 issue 文件**: 零外部引用的只有 28/243 条, 搬光也清偿不完; 且被搬件牵动 27 个 md 链接 + 21 个件的 `doc-refs`/`**Refs:**` 认领链(18 个为 plans/reports 冻结件), 双向认领链漏改一处即红 —— 新坑单独开档 `pitfalls/kb/index-archive-view.md`(cap-counting.md 主题文件余量不足, 按它自己记的「贴顶时新主题单独开文件」判据处置), cap-counting 侧只留一行指针。收口 `doc.caps -- --strict` **0 债务** / `doc.links` 绿 / `kb.check` 全绿 / `test.full` **3124 passed + 4 skipped**(守阵 `test_gen_all_declares_exactly_all_indexes` 因新增非 `_index.md` 生成物先红, 已在 `EXTRA_GENERATED` 显式登记, 未放宽为恒真)。基线切片见 `testing/baselines/26-10-11-1745-memory-bank-cap-cleanup.md`。
> 触发: cap 债务, 清理会话, doc.caps, 索引撞 cap, 条目数撑爆, 视图归档, CLOSED_KEEP, attachments, 外迁, EXTRA_GENERATED

## 状态

- **已清偿(5 → 0)**: 三项索引 + 两件手写文档; 机检 `doc.caps -- --strict` 报「无阻塞项 · 无 cap 债务」。
- 工作树含本轮全部改动(生成器 3 处 + 守阵登记 1 处 + 外迁 4 件 + 回写切片/坑档/基线), **等用户显式说「提交」**再 `ship.commit`。
- 未动: `SLICE_COUNT_LIMIT`(条数上限, 治理政策, 未拍板不调)、`CAP_POLICY`(未抬任何 cap)。

## 本轮副产物(下次清理会话直接用)

- **新常态**: issues 索引已关闭区只列最近 60 条 —— 找老 issue 去 `issues/attachments/_archive.md`(全量、摘要不截断)或按文件名 grep `issues/`, 别以为主索引漏了。
- **先行指标**: tasks 侧无摘要口径占 cap 由 48% → **57%**(193 档案); issues 侧已越过 100%(故走视图归档)。tasks 侧再涨 ~40 个档案就要同款处置。
- **口径观察(未动)**: 仓库行尾已是 `text=auto eol=lf` + `core.autocrlf=input`, 而 `cap-counting.md` 里仍有「归一 CRLF」的旧口径表述 —— 属文档漂移, 本轮未改(范围守恒), 记此备查。
