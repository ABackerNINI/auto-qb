# 6265 passed, 2 skipped —— resume 已删成员 kept 过滤守阵补全量基线

> 摘要: resume 已删成员 kept 过滤守阵补全量基线
> 基线时间: 2026-11-15 15:46

## 验收数字

`commands run test.full` 实测(2026-11-15 15:46, Windows 开发机):

```text
TOTAL                                                27855     73   9822     79    99%
6265 passed, 2 skipped in 181.29s (0:03:01)
```

- 汇总: 6265 passed / 2 skipped, 覆盖率 99%(实测表尾 99% 由 pytest-cov 出)。
- 配套面: `commands run test.one -- tests/test_relocate_resume_confirm.py` 28 passed; `commands run test.one -- tests/test_test_plan_docstring_guard.py` 6 passed; `commands run ship.gate` 闸门全绿(命中 8 条 / 执行 15 条命令)。
- 缺口净额(M8): 本片 152 单位(miss 73 + partial 79) 减上片 26-11-15-1318 的 151 单位(miss 73 + partial 78) = +1; 分母由语句 27477 / 分支 9664 变为 27855 / 9822(开工快进远端 146 笔带来分母增加), 净额未超 +15, 无需点名新进榜模块。

## 本改动面

修复 issue 26-11-15-1433(resume_hashes 已删成员 kept 过滤保证无用例直接钉):

- `tests/test_relocate_resume_confirm.py`: 新增 `test_resume_deleted_closure_keeps_non_pending_member` 一条 —— 账上 `resume_hashes=("HC", "HA")` / `resume_pending=("HA", )`(HC 已闭合出 pending 但仍在账上, 快照空窗不在 store), HA 连续 3 拍不在 store 判真删除闭账后, 断言 HC 仍在 resume_hashes、HA 从 pending 撤出、闭账日志只点名 HA; 同步登记进文件头主「## 测试计划」段。
- 红绿双验: 两种回归口径各注入一次源码变异 —— 扫描面改成全账扫 `job.resume_hashes` / `kept` 改成只留 remaining pending —— 新用例均在 `assert job.resume_hashes == ("HC", )` 处红(实测 `() == ('HC',)`); 还原后 `git diff -- src/auto_qb/core/modules/relocate_lifecycle.py` 为空, 零产品代码改动。
- 记录面: issue 26-11-15-1433 补 §05 修复后补充并翻 Done; 同专题 active-context 切片与任务档案回写; 本切片即本轮基线。
- 评审: code-review 一轮全能档(37 行), 只读子代理零 actionable; 基哈希 c0c1552f335d, 闸门预跑全绿。
