# 基线切片 26-10-05-0143 — O_TRUNC 直写静态守阵并入 (issue 26-10-02-0527 认领)

> 摘要: 认领 issue 26-10-02-0527, 1347 号 issue §06 悬置的「O_TRUNC 直写静态守阵」并入 ——
> 生效条件「全 src O_TRUNC 代码清零」(bc24631b) 复验仍成立, 新守阵 test_src_has_no_o_trunc_write
> (tokenize 静态扫描, 非注释 token 含 O_TRUNC 即红, STRING 拦 getattr 绕行, 注释豁免)。
> 基线时间: 2026-10-05 01:43

**Refs:** memory-bank/issues/26-10-02-0527-test-otrunc-static-guard.html, memory-bank/activeContext/otrunc-static-guard.md

- 分支: develop @ 87fef709 (+ 本轮未提交改动: tests/test_no_o_trunc_write.py / issue HTML / 本切片)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2538 passed + 4 skipped, 31.49s, 覆盖率 TOTAL 99%**
  (14871 语句 / 153 未覆盖 / 4982 分支 / 113 partial; 门槛 98% 达标)
- 靶向 (tests/test_no_o_trunc_write.py): **1 passed**。红验: 探针文件三类命中全抓
  (docstring / NAME `os.O_TRUNC` / STRING `getattr(os, "O_TRUNC")`, 探针 1/4/5 行),
  注释行豁免; 删除探针回归绿。
- 相对上基线 (26-10-05-0127: 2533 passed + 4 skipped / 99% / 28.6s): passed **+5** =
  本轮新守阵 1 条 + b4292805 (kb.nav 筛选器 localStorage) 守阵 4 条 —— 该轮只靶向未落全量基线;
  skip 集合不变 (Windows 侧 4 条 POSIX 专属)。
- 改动面: tests/test_no_o_trunc_write.py(新守阵 1 条, 纯静态扫描, src/ 零改动)。
