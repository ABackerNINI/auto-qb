# 3485 passed + 4 skipped(根) · 167 passed(包内) —— ship.commit 树净拒跑按远端真值分流 + 核 ref 假红不再自相矛盾

> 摘要: 用户转述另一会话现场「`ship.commit` 首跑 提交成功但报『没有可提交的改动』并中止推送」→ 分析原因 → 「按建议修」→「提交」。根因 = 两次调用被读成一跑(首次已落稳于本地「提交成功 <hash>(未推送)」, 二次又跑 `ship.commit` 而非 `ship.push` ⇒ 树净 ⇒ 撞 `resolve_stage_plan` 拒跑出口)。落盘: ①`commit.py` 新增 `clean_tree_route(cfg)`, 树净拒跑行按**远端现查真值**(`ls-remote`, `attempts=1`)三档分流(本地领先 → 直送 `ship.push`; 一致 → 确实无事可做; 取不到 → 如实说「无法核实」+ 两条出路); 只**树净**时接后缀; ②核 ref 假红出口去掉自相矛盾(保留 rc=1 与「提交失败」前缀, 不改写成假装成功), 结果行如实写「提交已落稳, 仅分支 ref 未核对通过」+ 直送补推; ③`sync.py::remote_sha` 加 `attempts` 形参(旁证查询收紧到 1)。数字测在含本轮 3 个源文件改动 + 知识库回写的同一棵树上。
> 基线时间: 2026-10-17 09:09

**Refs:** memory-bank/activeContext/26-10-17-0909-ship-commit-clean-tree-routing.md

- 根 `test.full`(契约: 覆盖率门槛 98% + 包内 TMPDIR): **3485 passed + 4 skipped in 145.10s**; TOTAL **17885 249 6012 181 98%**(语句/未覆盖/分支/partial/覆盖率)。
  - 沙箱内跑会因 `TMPDIR`(R: 盘)收尾清理被拦而退出码非 0, pytest 本身全绿 —— 属已知沙箱现象(见 `pitfalls/testing/tmpdir.md`); 本次**关沙箱**跑, 上述即干净数字。
  - 与上一基线(`26-10-17-0825-global-traffic-source-integration-s14`)语句数/通过数持平: 本轮改动集中在 `.commands/` 包内脚本(不在根 `testpaths`), 根套件无新增用例。
- 定向(本轮变更面): `commands run test.one -- .commands/my-commit-flow/scripts/test_commit.py -k clean_tree -v` → **3 passed**(领先 / 一致 / 离线三态; 老代码上三条皆红 ⇒ 判红力可验)。
- 包内脚本套件: `commands run test.pkg` → **167 passed in 28.32s**。
- `dev.fmt` 通过(`commit.py` / `sync.py` / `test_commit.py`); `commit.py --help` / `sync.py --help` 冒烟正常。

## 本改动面

- `.commands/my-commit-flow/scripts/commit.py` —— 新增纯函数 `clean_tree_route(cfg) -> str`(三档分流; 仅树净拒跑行接后缀); 核 ref 假红出口结果行 + 消费提示去掉自相矛盾并直送补推; import 组展开(`resolve_branch` / `resolve_main_remote`); 模块 docstring 两处口径更新(结果行语义 + 树净分流)。
- `.commands/my-commit-flow/scripts/sync.py` —— import `GIT_ATTEMPTS`; `remote_sha(name, branch, attempts=GIT_ATTEMPTS)` 加形参 + docstring 说明(仅拒跑路径旁证查询收紧)。
- `.commands/my-commit-flow/scripts/test_commit.py` —— 新增 3 条用例(`test_clean_tree_ahead_routes_to_push` / `test_clean_tree_in_sync_reports_nothing_to_do` / `test_clean_tree_offline_keeps_both_exits`); 既有 `test_message_consumed_on_verify_fail_when_head_matches` 加严两条断言; 头部「## 测试计划」清单同步。
- `.commands/my-commit-flow/references/pipeline.md` —— 口径回写(树净拒跑按远端真值分流 + 已落稳时结果行如实标注)。
- `memory-bank/pitfalls/git/push.md` —— 新增条目「树净别重跑 ship.commit: 提交已落稳只差推送 → 补推走 `ship.push`」+ 反向声明本专题档案。
- `memory-bank/tasks/26-10-17-ship-commit-clean-tree-routing.md` · `memory-bank/activeContext/26-10-17-0909-ship-commit-clean-tree-routing.md` —— 本专题滚动面。
