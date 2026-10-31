# 26-10-31-memory-bank-doc-guard-filename-scope-fix — 新增面守卫圈面改文件名 stamp 前缀: 堵缺 doc-added 手写新件逃逸洞 (RM02-RM10 事故)

**Status:** Done
**Added:** 2026-10-31
**Updated:** 2026-10-31
**Summary:** 新增面守卫圈面改文件名 stamp 前缀: 堵缺 doc-added 手写新件逃逸洞 (RM02-RM10 事故)
**Topics:** doc-guard-filename-scope-fix

## 原始请求

1. 最近的一些计划件出现「(无状态)」, 需要修复; 模板生成时就应包含状态 —— 是没有使用模板吗? 为什么没有被提交闸门拦住? 调查一下流程是否出了问题。
2. 按调查给出的四条加固建议实施 (守卫圈面 / kb.new 预检 / 回归守阵 / 坑档两条)。
3. 立档收尾然后提交。

## 思考过程与决策

- 根因三件套: ①创建侧 RM02-RM10 手写抄冻结线前旧件头部 (`plan-slug`/`plan-stamp` 旧 meta + 大写 topic 违 `PLAN_FILE_RE`), 未走 `kb.new`; ②守卫侧 `check_doc_templates` plan/report 圈面按**文件自身 doc-added** 决定扫不扫, 缺头部新件整件逃逸 (豁免自噬: 越缺字段越查不到); ③守阵侧只测存量豁免方向, 无「新建缺 doc-added 必红」用例。闸门本身接线无误、每笔都跑了 —— 恒绿是守卫判据洞, 不是漏跑。
- 修正一处上轮误判: `new_doc.py:259` 的 `SLUG_RE` 早拒大写 topic, 「kb.new 传大写造出违规件」假设不成立 —— 小写化不重造, 只补派生文件名 vs 族命名正则的不变量守卫 (防建件端/守卫端正则失配漂移)。
- 圈面判据与 baseline/slice 对齐: 文件名 stamp 前缀, 不读文件内部任何 meta; 存量豁免语义不变 (非日期前缀命名/坑档/进展件仍由既有守卫兜底)。
- RM 九件状态回填取 Done: RM00-RM10 全部有实测基线 (排期计划已消费完毕), 对照 RM01 先例; `doc-updated` 取各片实测基线 stamp。
- 实施中踩 Windows 仅大小写改名坑 (`write_bytes` 按不敏感匹配开旧件 + `unlink` 把同一文件删掉, 九件一度消失) —— 从 HEAD 恢复后改「临时名中转 → unlink → os.rename」序列重做, git 侧 `rm --cached`+`add` 落改名; 入坑档 `pitfalls/git/windows-case-only-rename.md`。

## 实现计划

总体四步 (每步独立可验): ①守卫圈面 plan/report 改文件名 stamp 前缀 + 模块 docstring ②`kb.new` 派生文件名不变量守卫 ③回归阵 + 冻结线测试措辞 ④坑档两条 + toml note 注记; RM 九件头部修复与引用同步在加固前完成并绿验/红验收口。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | RM02-RM10 九件回填 doc-* 头部 + 改名小写 + 引用 9 处同步 (锚 issue 等 5 个 issue 件 / manual-walkthrough / 3 个 real-baselines) | Done(26-10-31) |
| 2 | `check_doc_templates` plan/report 圈面改文件名 stamp 前缀 + docstring | Done(26-10-31) |
| 3 | `new_doc` 派生文件名族命名正则不变量守卫 | Done(26-10-31) |
| 4 | 回归阵 `test_checker_catches_new_plan_missing_doc_added` + 冻结线测试措辞更新 | Done(26-10-31) |
| 5 | 坑档两条 (kb/handmade-doc-header-escape · git/windows-case-only-rename) + toml note 注记 | Done(26-10-31) |
| 6 | test.full 全绿 (基线切片 26-10-31-2128) + kb.check 全绿 + 立档 | Done(26-10-31) |

## 进度日志

### R0 · 立档 (2026-10-31)

调查定性 (三问三答: 未用模板 / 闸门跑了但守卫圈面有逃逸洞 / 守阵缺口) + 加固四项实施 + RM 九件修复收口; test.full 实测数字见 kb.baseline 切片 26-10-31-2128。

- 2026-10-31 21:33 立档收口: 档案 Status Done + 六步全落; test.full 全绿见基线 26-10-31-2128; 提交走 ship.commit
