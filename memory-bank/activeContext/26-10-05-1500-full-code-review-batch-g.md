# 全面 Code Review · 批 G 完成 (torrents/ 种子数据层 + rules/ 规则引擎本体)

> 摘要: 计划 [26-10-05-0951](../plans/26-10-05-0951-plan-full-code-review.html) 批 G 评审轮完成 (只读, 零改码), HEAD `a4d14a8d` 与起点/F1/F2 同 commit。23 件 / 3,960 行 (torrents 5 件 1,314 + rules 18 件 2,646) 按 LOC 降序全文件过目, 重点维度 R1 R5 R6 逐文件勾选; 坑档 backend 8 主题对照 (high-risk-ops / effect-confirmation / concurrency / qb-api / behavior-core 等); 读档 rule-system 三篇 + core-domain(torrents) + rules-and-deps。**最大发现 G-01 (P1, R5, 实证)**: 表达式内核 LIST 相等比较跨容器类型恒错 —— `tor.tags == ["HR"]` (tor.tags 返回 frozenset, ListLit 求值为 tuple) 编译期放行 (types.py LIST==LIST 只查同标记)、运行期恒 False (标签确实匹配也判不匹配), `!=` 恒 True (全员误匹配), 无任何报错; tracker.groups(list) 同理。另 6 条全 P3: **G-02** sys.time_of_day 双 now() 跨午夜单次错值 · **G-03** FreespaceCondition OSError 静默 False 与同函数 FileAccessError 抛错 / expr 形式判据劈叉 (「绝不降级成假值」原则违例面, 失效与「空间够」同形) · **G-04** add_category 的 except-pass 吞 create 根因 (bandit B110 同点) · **G-05** 决策链 1.6 假失败自愈 pop 不即时落盘 (behavior-core 写点纪律漏网, 后果有界自愈) · **G-06** sys.torrent_count 每次 O(N) 全库浅拷贝 + 唯一未标 expensive 的计数名 · **G-07** custom basic_check 主循环内同步 subprocess 每候选 600s 无总预算 (功能内生, 文档无提示)。**R2 危险闸门规则侧复核 (0402 洗白面归本批)**: checking 决策链 0/1/1.5/1.6/4 全部先于一行委托 ctx.ops.skip_check / ctx.ops.recheck(source="rule") — 与 WEB 同一 ops 层服务端闸门, 规则侧无绕闸旁路; rules 全包确认无 delete 动作; 限速奇数 KiB 保护在 — **0402 issue 现状成立 (决策链确认无对自身 recheck_fails 的检查), 沿用已入池条目不重开**。复验不登记 14 项 (含: _idle inf 系文档化语义且 trace._jsonable 已兜 JSON 面 / hr_* None 面全调用点先守卫系有意设计 / 1.5 等待闸门含 checkingResumeData 正确 — 与生效证据谓词是两个语义面 / UP+DTZ+BLE 工具债沿批 A–D 口径)。工具源: 仓库无 ruff/bandit 配置, uvx 临时版跑批 G 范围 — ruff 184 条 (UP 系 138 归池 1408; DTZ 13 naive 本地挂钟系有意口径; BLE 5 全有日志可观测; 复核采纳 0 新立条), bandit 3 条全 Low (B110 → G-04 采纳; B404/B603 subprocess 配置者即本人不采纳)。test.full **2610 passed + 4 skipped / 99%** (15511/5342, 164/138) 与基线切片 26-10-05-1034 逐位持平, 一次通过无抖动。发现表落盘 [报告草稿批 G 章节](../reports/26-10-05-1036-report-full-code-review.html)。
>
> 最后活动: 2026-10-05 15:00

**Refs:** memory-bank/plans/26-10-05-0951-plan-full-code-review.html · memory-bank/reports/26-10-05-1036-report-full-code-review.html · memory-bank/rule-system/_index.md · memory-bank/pitfalls/backend/_index.md · 前序切片 [批 F2](26-10-05-1420-full-code-review-batch-f2.md) · [批 F1](26-10-05-1305-full-code-review-batch-f1.md) · [批 E](26-10-05-1300-full-code-review-batch-e.md)

## 本轮完成

- sync 成功记 HEAD `a4d14a8d`; 五步动作序列走完 (读档 rule-system 三篇 + modules 两篇 + 包 docstring → 坑档 backend 8 主题 → LOC 降序 23 件全文件过目 → uvx ruff/bandit 逐条人工复核 → 登记去重)。
- 发现表 7 条 (P1 ×1 / P3 ×6) 回填报告草稿批 G 章节 (含逐文件勾选结论 23/23 / 复验不登记项 14 / 工具源小结 / 收尾基线对照); 逐条对照底册附录 A–D: 池 26-10-01-2211 (规则容错键) 不同件不撞, 26-10-05-0402 (跳检自证) 规则侧复核结论写入复验项①。
- G-01 经 uv run 实证复现 (compile 放行 + tags_set={'HR'} 时 == 求值 False / != 求值 True) 后登记, 非推断。
- 报告脚注批次进度更新为 G✓ (7 条: P1 ×1 / P3 ×6)。
- test.full: **2610 passed + 4 skipped / 99%** (15511/5342) 与基线逐位持平。

## 遗留 / 待办

- G-01 是本批唯一 P1: S5 汇总时建议二论证 (表达式 == 列表的误用面与文档惯用法提示), 处置两条路已写入条目 (求值侧归一化容器形态 / 编译期拒绝 LIST 参与 ==/!=)。
- G-03/G-06 建议入池; G-02/G-04/G-05/G-07 仅记录或顺手项, S5 分流定稿。
- 剩余批次: H (infra/tray/scripts/extensions/docker) → S5 汇总分级 → S6 定稿。
