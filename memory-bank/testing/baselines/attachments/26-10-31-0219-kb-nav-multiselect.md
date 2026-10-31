# 4183 passed + 10 skipped —— kb.nav 多选与批量右键菜单后全量

> 摘要: kb.nav 台账加多选(Ctrl+click 切换 / Shift+click 锚点区间并入, 主表 + 置顶专区双区同亮)+ 批量右键菜单(行∈选区→整集合生效, 文案带灰色 N; 复制每行一个按可见序 / 打开 >5 confirm / pin·hide 幂等批量)+ 辅助件(已选 N chip / Esc 退栈末档 / Ctrl+A); 新守阵 6 条, test.full 全绿
> 基线时间: 2026-10-31 02:19

## 验收数字

`commands run test.full`(pytest `-n 4 --cov=src --cov-branch --cov-fail-under=99`(pytest.ini addopts); 2026-10-31 实测, 全量 73.33s, 建档 02:19):

```
  TOTAL                                                20891     114   7160    105    99%
  4183 passed, 10 skipped in 73.33s (0:01:13)
```

- 汇总行: **4183 passed + 10 skipped(Windows)**; 覆盖率门槛 99% 通过(TOTAL 行 99%)。
- 逐条口径注记: 本轮新增守阵 6 条(test_shell_has_multiselect_state_and_gestures /
  test_multiselect_renders_in_both_zones / test_ctx_menu_batch_upgrade /
  test_batch_actions_idempotent / test_multiselect_chrome_and_escapes /
  test_batch_copy_paths_and_open_links), 均为壳文本结构断言, 无网络 / 子进程副作用;
  语句数与 miss 与上 Windows 基线(26-10-31-0024: 20891/114)逐位相同 —— 改动面全在
  nav_page.html(壳, 无 py 覆盖)与 tests/test_kb_nav.py。
- 真机冒烟(Playwright 无头 chromium, file:// 静态件): **22 项全过** —— Ctrl 切换/取消 /
  Shift 区间并入(同锚点再扩不清先前区间) / 普通单击不清多选且抽屉跟随 / 批量菜单 N 后缀
  与单条无 N / 右键不改选区 / 批量置顶后置顶区同亮 + 动态「取消置顶」反向文案 / Esc 末档
  清多选 / Ctrl+A 全选 863/863 / 复制动作链无异常 / 切视图清空 / 零 pageerror。
  脚本: tmp-analysis/nav/smoke_multiselect.js(gitignored)。

## 本改动面

- `.agents/skills/memory-bank/scripts/nav_page.html`: ①状态 `S.multi`/`S.multiAnchor`(纯会话态,
  derive()/saveFilters() 均不碰) + 多选函数块(isMultiSel/multiSet/toggleMulti/shiftMulti/
  clearMulti/syncMultiChip); ②主表与置顶专区 click 委托加 Ctrl/Shift 分支(先于改 S.sel, 普通单击
  落锚点不清多选); ③`ctxTargets` 目标解析单点(集合>1 且行∈选区→整集合快照) + openCtx 冻结
  links 快照 + 批量文案带 N + 分发改批量链(togglePinBatch/toggleHideBatch/copyPaths/openLinks,
  剪贴板低层抽 copyText); ④顶栏「已选 N」chip #mselChip + tr.msel/sel.msel CSS + setView 切视图
  清空 + escRetreat 多选档 + Ctrl+A selectAllVisible。服务端 nav_server.py / nav_data.py 零改动。
- `tests/test_kb_nav.py`: +6 守阵(文件头测试计划同步 4 行)。
- `memory-bank/plans/26-10-31-0143-plan-kb-nav-multiselect.html`: 本轮计划档(D1-D14 拍板表)。
