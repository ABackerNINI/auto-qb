# 5783 —— 评审流程改造落地后基线

> 摘要: 评审流程改造落地后基线
> 基线时间: 2026-11-08 17:13

## 验收数字

`commands run test.full`(2026-11-08 17:11, 分支 review-no-exemption-loop @ 7c5104c4):

```text
TOTAL                                                25749     16   8920     39    99%
5783 passed, 2 skipped, 7 warnings in 119.46s (0:01:59)
```

与上一切片(26-11-08-1142 实测 5782 passed/2 skipped, TOTAL 25742 15 8918 38)相比: **+1 条**(5782+2 → 5783+2); tests/ src/ e2e/ 主套件源文件零增删(e6e3e73b..7c5104c4 对三目录 diff 为空), +1 来自目录/数据驱动收集随本批非测试文件新增(疑为文档守卫类按文件收集, 未逐条定位); 覆盖率 99% 持平, TOTAL 25742→25749(+7, 来源未逐项定位)。

## 本改动面

- `.commands/review/scripts/review_content.py`(新): 可评路径过滤 + `batch_base_hash`(双层配置隔离 13 钉 + literal pathspec + --ignore-cr-at-eol); check_review_trace.py / review_pack.py 改 import, 单点同源
- `.commands/review/scripts/check_review_trace.py`: 50 行下限退役(可评 >0 必评)、新提交 Review-Skip 判红、`· 基` 必填+现算比对、`· 轮` 缺省 1、累计口径注释; 敏感面语义随下限退役改为「强制评非必红」
- `.commands/review/scripts/review_pack.py`: pack 输出基哈希行
- `.commands/review/scripts/test_review_pkg.py`: 86 → 112(判定矩阵 4 条语义翻转 + 新增 16 条: 抗配置漂移 15+2 键/rename 展开/literal/金值/POST_MARKER×基/敏感面端到端/轮派发同现等)
- `.commands/review/config.toml` + `.commands/my-commit-flow/.my-commit-flow.toml`: 三条 note 同步新口径(旧口径第三/四副本清除)
- `.agents/skills/code-review/SKILL.md` 全文新口径 + `.agents/skills/memory-bank/SKILL.md` 第 0 步判据同步
- 记账面: 计划档 R1/R2、任务档案 W1-W3 Done + 进度日志、新 issue 26-11-08-1701、坑档 pitfalls/kb/reviewer-subagent-hang-on-long-commands
