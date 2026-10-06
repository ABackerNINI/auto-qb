# O_TRUNC 直写静态守阵并入 — issue 26-10-02-0527 认领完成 (Done)

> 摘要: 认领 issue 26-10-02-0527 (1347 号 issue §06 悬置的 O_TRUNC 直写静态守阵并入, 生效条件「全 src O_TRUNC 代码清零」已由 bc24631b 达成)。复验: 全 src grep 仅余两处修复注释 (hr/channel.py:104 · webui/server/common.py:69), 代码命中为零。新守阵 tests/test_no_o_trunc_write.py::test_src_has_no_o_trunc_write (tokenize 扫 src/ 全部 .py, 非 COMMENT token 含 O_TRUNC 即红; NAME 拦 os.O_TRUNC, STRING 拦 getattr(os, "O_TRUNC") 绕行; 注释豁免; 显式豁免走测试内 _WHITELIST 路径→理由)。红验探针三类命中全抓 (docstring/NAME/STRING) + 注释豁免实证, 删除后回归绿; 守阵登记 testing/guards.md「后端高风险动作 / 状态持久化」表。test.full 2538 passed + 4 skipped / 99% / 31.49s (基线 [26-10-05-0143](../testing/baselines/26-10-05-0143-otrunc-static-guard.md); 增量 +5 = 本轮 1 条 + b4292805 kb.nav 持久化守阵 4 条, 后者上轮未落全量基线)。不满足立档阈值, 无任务档案。
> 最后活动: 2026-10-05 01:48

**Refs:** memory-bank/issues/26-10-02-0527-test-otrunc-static-guard.html(Done)

## 现状

- issue Done, 认领链闭合: 1347 (web.token 非原子写) → 26-10-01-2151 (hr.token 修法 bc24631b) → 清零条件达成 → 守阵落地 (本条)。此后 src 再现 O_TRUNC 直写 = 守阵红, 唯一合法写盘单点 `utils.atomic_write`。
- 收尾补登记 (01:48): 既有守阵 `test_no_ghost_pkg_dirs` 建档时漏登记, 按用户指派补进 guards.md 新节「src 结构卫生」(全 src 静态扫描); O_TRUNC 守阵登记位置不动, issue/切片里的节名引用保持有效。
- 改动面: tests/test_no_o_trunc_write.py / memory-bank/testing/guards.md / issue HTML / 基线切片 / 本切片
