# 全面 Code Review · 批 B2 完成 (hr/ 其余 20 件: channel / worker / parse / resolve / report / store / runtime / server / adapters 等)

> 摘要: 计划 [26-10-05-0951](../plans/26-10-05-0951-plan-full-code-review.html) 批 B2 评审轮完成 (只读, 零改码), HEAD `a4d14a8d` 与起点同 commit。20 文件 / 4,651 行全部逐文件过目, 重点维度 R6 R7 R8 R9 逐文件勾选。发现 6 条 (P2 ×1 + P3 ×5): B2-01 store 编码类读坏 UnicodeDecodeError 逃出自愈链 (坏文件隔离/.bak 兜底不可达 + build_views 单坏文件拖垮全站视图发布, P2) · B2-02 judge_record 双 hash 平局合并 docstring 承诺未实现 (F841 best_key 旁证) · B2-03 worker._force 注释「空集=全站」与实现相反 · B2-04 parse_size 单元表外静默按 1 字节猜 (违背「认不出返回 None」纪律) · B2-05 死导入 ×5 + 死异常类 HrStoreCorrupted · B2-06 ratelimit 86400 秒推算的 DST 边缘 (备查)。复验不登记 6 项 (末页追翻在 service.py 属池条 0052 / LocalPageFetcher 非安全边界 / submit url 缺省回填 / _anchors 撕裂读单调性论证 / bandit 全误报 / RUF100 noqa)。凭据面复核结论: token 恒时比较 + 内容零入日志 + 协议零 cookie/passkey + URL 白名单 SSRF 边界成立。工具源: ruff 248 条采纳 6; bandit 7 条全误报。test.full 2610+4 / 99% 与基线逐位持平。发现表落盘 [报告草稿批 B2 章节](../reports/26-10-05-1036-report-full-code-review.html)。
>
> 最后活动: 2026-10-05 11:35

**Refs:** memory-bank/plans/26-10-05-0951-plan-full-code-review.html · memory-bank/reports/26-10-05-1036-report-full-code-review.html · 前序切片 [批 A](26-10-05-1100-full-code-review-batch-a.md) · [批 B1](26-10-05-1130-full-code-review-batch-b1.md)

## 本轮完成

- sync 成功记 HEAD `a4d14a8d`; 五步动作序列走完 (读档批 B1 切片 + 稳态降频切片 + 20 件 docstring → 坑档 backend 六主题 → LOC 降序逐文件读码 → ruff+bandit 逐条复核 → 登记去重)。
- 发现表 6 条回填报告草稿批 B2 章节 (含逐文件勾选结论 20/20 / 复验不登记项 / 工具提示源小结 / 基线对照)。
- test.full: 2610 passed + 4 skipped / 99% (15511/5342, 164/138) 与基线切片逐位持平, 无漂移。

## 遗留 / 待办

- B2-01 (P2) 建议尽早入池: 站点文件被编辑器按 GBK 重存即触发, 自愈链 (quarantine/.bak) 对该类坏文件全程不可达, 且一个坏文件拖垮全部站点视图发布 (HR 管束证据全失)。
- HrStoreCorrupted 死异常类的处置二选一 (删除 vs 改为真实抛出) 需语义拍板, 随 B2-05 入池时定。
- 池 perf 26-09-30-0052 (末页追翻) 改动面经复验在 service.py `_run_pages` (B1 范围), 底册「撞车比对批 B2」标注可消 — S6 汇总轮处理。
- 批 C (traffic 三件 2,889 行, R3 R5 R7) 待评审。
