# 5855 passed + 2 skipped —— infra 依赖纪律 AST 守阵收尾基线

> 摘要: infra 依赖纪律 AST 守阵收尾基线
> 基线时间: 2026-11-08 18:25

## 验收数字

`commands run test.full`(2026-11-08 18:25 收尾前实测, 分支 develop @ f674ce4a):

```text
TOTAL                                                26055     32   9048     50    99%
5855 passed, 2 skipped, 15 warnings in 160.82s (0:02:40)
```

与上一切片(26-11-08-1713 实测 5783 passed/2 skipped, TOTAL 25749 16 8920 39)相比 +72 条, 覆盖率 99% 持平。**两侧不是同一棵树**: 上一切片取自分支 review-no-exemption-loop @ 7c5104c4, 本轮会话开工 `my-commit-flow.sync` 快进合入 140 笔远端提交到 develop @ f674ce4a, 本轮自身只新增 1 个测试文件 8 例; 其余差额按快进提交面归因, 未逐条定位。

## 本改动面

- `tests/test_infra_import_discipline.py`(新): infra 依赖纪律 AST 守阵 8 例 —— 运行期白名单只许 stdlib / 三方 / `auto_qb.infra*`, TYPE_CHECKING 按 R4#18 只放行 `auto_qb.config*`; 合成源 9 种上行形态 + tmp 目录 + 真仓 16 文件镜像注入违例, 红绿双验
- `memory-bank/testing/guards.md`: 新增「infra 依赖纪律 AST 守阵」登记段(钉住的结论 / 红验 / 判据来源)
- `memory-bank/issues/26-11-08-0703-refactor-infra-import-discipline-guard.html`: 复验留痕 + 状态翻 Done + 实际修法与验证方式
- `memory-bank/pitfalls/testing/tmpdir.md`: 外部 TMPDIR 拒收复发 +1(跑测试前未先清 env)
- 生成物: `memory-bank/issues/_index.md` · `issues/attachments/_archive.md` · `tasks/_index.md` 等由 kb.status / kb.index 重建
- 生产代码零改动(`src/` 无 diff); 分批评审 1 派 0 发现(review.check 0/0)
