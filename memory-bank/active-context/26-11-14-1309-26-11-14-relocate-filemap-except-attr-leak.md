# 26-11-14-relocate-filemap-except-attr-leak

> 摘要: 修复 issue 26-11-14-0401: relocate_plan._file_map except 支改防御取值(getattr log_repr 退化 repr(rec)), 补替身缺属性用例钉兜底; 整文件 48 passed / test.quick 6136 passed; 评审零 actionable; issue 翻 Done
> 最后活动: 2026-11-14 13:09

**R0(2026-11-14 13:09):** 修复 issue 26-11-14-0401: relocate_plan._file_map except 支改防御取值(getattr log_repr 退化 repr(rec)), 补替身缺属性用例钉兜底; 整文件 48 passed / test.quick 6136 passed; 评审零 actionable; issue 翻 Done <!-- wording:allow --> (存量历史流水引述, 他 clone 入库后越过本地冻结常数 394, 2026-11-15 补豁免解闸)
