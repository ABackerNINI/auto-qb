# 5883 passed, 2 skipped —— fastresume 相对键 profile base 解析改写批实测

> 摘要: issue 26-11-07-2336 相对键解析改写批实测: 5883 passed, 2 skipped (116.38s), 覆盖率 99% (26198 stmts / 45 miss)
> 基线时间: 2026-11-10 01:32
**Refs:** memory-bank/issues/26-11-07-2336-bug-relocate-same-drive-finalize.html,memory-bank/tasks/26-11-10-backend-relocate-relpath-finalize.md

## 验收数字

```text
TOTAL                                                26198     45   9134     57    99%
5883 passed, 2 skipped in 116.38s (0:01:56)
```

(实测时点: HEAD 5529b9f8 + 本批工作树改动, `commands run test.full` 2026-11-10 01:32; 较上一基线 26-11-09-2344 的 5876: +7 = 本批新用例 6(fastresume 5 + daemon 1) + 远端并入 scripts 守卫 1)

## 本改动面

- **fastresume 改写器**(src/auto_qb/core/fastresume.py): 新增相对形态解析四件 —— `_split_absolute`(盘符/UNC/POSIX 三根形态)、`_relative_form`、`_resolve_relative`(点段/上弹/越根拒绝, 产物分隔符=base 根分隔符)、`profile_base_of`(BT_backup 上两级); `rewrite_save_paths` 增 `profile_base` 参数(相对键解析进既有前缀管道, 解析失败/不命中原样 unmatched), `retarget` 内部接线(spec.bt_backup → base 推导)。
- **recycle_daemon.py**: `_rewrite_member` unmatched 记账注释同步(相对键已可改写)。
- **测试**(tests/test_core_fastresume.py + tests/test_recycle_daemon.py): 新用例 6 —— E2c 形态解析改写(反斜杠/正斜杠相对键, 等值与根下命中, 产物绝对新根, 幂等重放)、unmatched 面(指旧新根外/越根/无 base 旧链兼容/无点形态)、POSIX 面、profile_base_of 形态表、retarget 端到端、daemon 接线端到端; 既有 N10 钉(无 base 跳过)保留。
- **知识库**: issue 26-11-07-2336 翻 Done(复验/修复后补充/认领链), 任务档案 26-11-10-backend-relocate-relpath-finalize 立档, 坑档 patching.md 复发 +1(e2e 断言硬编码分隔符)。
- 评审 4 轮: 轮1 blocker 2(Linux CI 宿主风味断言)+ nit 2 全修, 轮2/3/4 零 actionable。
