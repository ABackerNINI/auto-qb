# 基线切片 26-10-05-0737 — webui 危险动作防护实施完成(S1-S4 六笔提交 + S5 收尾)

> 摘要: 计划 26-10-05-0314 全部实施落地 —— ops 跳检闸门 G3-G8 + filelist 执行链 +
> _skip_gates_detail 三分流单点 + force 语义 + skip_check_precheck dry-run(S1a/S1b-1/S1b-2),
> webui 预检端点 + force 透传(S2), 前端重检确认框共用 helper(S3), 跳检预检对话框三分流
> 状态机(S4); store 组级判定上移 + grouping 委托。新增守阵 22 条, 全部经红验探针先红后恢复;
> S5 收尾红验抽查(摘 G8→T17 红 / 摘 :disabled 绑定→T23 红)复证守阵活着。
> 基线时间: 2026-10-05 07:37

**Refs:** memory-bank/tasks/26-10-05-webui-danger-guards.md, memory-bank/issues/26-10-05-0254-feat-webui-recheck-confirm.html, memory-bank/issues/26-10-05-0254-feat-webui-skip-check-preconditions.html

- 分支: webui-danger-guards @ bd532d26(六笔实施提交 bcc2bce2/09683720/7d9595a7/0ff19787/51e30393/bd532d26; 树净, 红验探针已全部恢复)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2576 passed + 4 skipped, 27.48s / 28.13s(两次采样), 覆盖率 TOTAL 99%**
  (14970 语句 / 152 未覆盖 / 5038 分支 / 114 partial; 门槛 98% 达标)
- 相对上基线 (26-10-05-0413: 2554 passed + 4 skipped / 99% / 29.15s): passed **+22** = 本计划新增守阵
  (S1a store 直测+grouping 委托等价 2 · S1b-1 ops 闸门 T1-T7/T18-T20 11 · S1b-2 T16/T17 2 ·
  S2 T10/T11/T21/T22 4 · S3 T13 1 · S4 T23/T24 2); 语句 **+99**(ops_mod/store/路由/前端测试桩),
  分支 +56, partial +1; 未覆盖 152 持平。skip 集合不变(Windows 侧 4 条 POSIX 专属)。
  耗时 27.5~28.1s 落在近几条切片噪声带低端, 非回归。
- S5 红验抽查(本轮, 树净后复绿 2576+4/24.09s): ①摘 G8(ops_mod.py `if key is not None` → `if False and …`)
  → T17 红 `AssertionError: 组员当日失败应拒: ActionResult(success, skip-checking 跳检完成)`;
  ②摘 popovers.html modalOk `:disabled="modal.okDisabled"` 绑定 → T23 红
  `modalOk 确认钮缺 :disabled="modal.okDisabled" 绑定 —— 进框禁用/按态解锁失效`。
  附带复证已知坑: 单文件跑 test.one 覆盖率 FAIL 假红(TOTAL 21.37% < 98%)照旧出现。
