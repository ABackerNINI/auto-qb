# 5488 passed + 2 skipped —— W1-W5 实施完成全量基线(create-issue 融合 memory-bank)

> 摘要: W1-W5 实施完成全量基线(create-issue 融合 memory-bank)
> 基线时间: 2026-11-07 07:18

## 验收数字

`commands run test.full` 实测 (2026-11-07, 命令整体 135.4s):

```text
TOTAL                                                24538     57   8396     36    99%
5488 passed, 2 skipped, 1 warning in 133.29s (0:02:13)
```

- 缺口净额 (M8 口径, miss + partial): 本片 57 + 36 = **93 单位**; 上上片 [26-11-07-0339](26-11-07-0339-memory-bank-nav-relation-graph.md) (74 + 41 = 115) 比净额 **−22** (紧邻片 26-11-07-0345 未记 miss/partial 明细, 净额隔片对比在此注明)。pytest-cov 的精确覆盖率行不在 test.full 的 silent_success 结论行内, 按裁定 A4 不转抄不推算。

## 本改动面

create-issue 并入 memory-bank 计划 (26-11-07-0549) 五波全落地后的全量基线:

- **W1 代码融合**: `.agents/skills/create-issue/scripts/`(new_issue.py / gen_issues_index.py / _common.py)与 `assets/issue-*.html` 并入 memory-bank skill(`scripts/` + `templates/`), 常量单点并轨 `_common.py`; `gen_all.py` 收编 issues 索引生成器; 3 条跨 skill 钉住测试删除。词表并轨顺带统一索引状态分区序(issues 索引由 Open 在前改为 In Progress 在前, 同 DOC_STATUSES 序; 词表合一的必然派生, 声明留痕)。
- **W2 模板翻新**: issue 两模板单栏版式对齐四形态 + `@@` 占位符(不引入 SLOT, 不扩 check_doc_templates 扫描面, D6)。
- **W3 建件收编**: `kb.new issue` 族(new_doc.py FamilySpec 扩展, slug 位置参数 + --type/--title/--summary 必填), new_issue.py 退役(D4, 翻案 26-10-17-0527 D2)。
- **W4 翻状态收编**: `kb.status` issue 分支(flip_status.py: 徽标+meta 两处一次改 + 状态日志行 + 索引重建, 幂等, 终态提醒, D5)。
- **W5 回写收口(本波)**: create-issue SKILL.md 正文改写(frontmatter 不动, 机械面指 `commands run kb.*`, 可移植性节改「随整套 memory bank 搬走」); scope-guard / doc-forms / README / code-style 指针更新; kb 包 config.toml kb.new/kb.status when+note 更新; gen_issues_index 索引头部文案与链接一致化(头部变长 + 新增计划/档案条目令索引预算各收紧: plans 轮出 179→180、tasks 270→271 各 1 条进归档, issues 完结区维持 0 可见、报告与归档原地不动); PORTING.md 两处 W1 遗留修正(生成器归属 / 时间戳单点)。
- AGENTS.md 零改动(计划红线); 红线 config.yml / auto-qb-data/ 未触碰。
