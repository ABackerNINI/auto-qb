# 2682 —— ship.commit 复跑闸门改用重取的配置(自我改写的配置快照过期)

> 摘要: 修 `ship.commit` 的一条**静默**引擎缺陷 —— 闸门**复跑**在内部同步的 rebase 之后, 用的却是
> **进程启动时**读的那份 `cfg`; 若那次 rebase 把远端新版 `.my-commit-flow.toml` 换进了工作区(本包目录
> 就在仓库里), 复跑就是"用旧规则验合并后的新树"(旧闸门集 / 旧 `each_limit` / 旧红线), 而输出与"全过"
> 一字不差。修法 = 复跑前先 `refresh_package_modules()` 再 `_pipeline.reload_config(cfg)`(磁盘现版本 +
> STOP 复检)。零 `src/` 改动 —— 改动全在 `.commands/my-commit-flow/` 与 `memory-bank/`(两者都不在
> `testpaths`), 故 `test.full` 数字与上一条**逐位相同**。基线时间: 2026-10-06 21:08

**Refs:** memory-bank/tasks/26-10-06-ship-rerun-stale-config.md

- 分支: develop @ **b56520ed**(开工 `commands run my-commit-flow.sync` = `已同步 b56520ed`;
  本轮改动测量时尚未提交)
- 命令: `commands run test.full`(Windows —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **2682 passed + 4 skipped, 覆盖率 TOTAL 99%**。
  语句 **16021** / 未覆盖 **163** / 分支 **5472** / partial **143**。
  耗时: 两次采样 **46.51s** / **46.79s**(后一次为知识库回写 + `kb.index` 后的确认跑) ⇒ 区间约 **46~47s**。
- 相对上一条 [26-10-06-2027](26-10-06-2027-webui-esc-order-history-first.md)
  (2682 + 4 / 16021 / 163 / 5472 / 143): passed / 语句 / 未覆盖 / 分支 / partial **五项逐位相同**
  —— 本轮只动包脚本(`.commands/`)与知识库, 二者都收不进 `testpaths = tests`。
- **包自测**(不在 `testpaths`, 由 `commands run test.pkg` 跑): **137 passed / 165.98s**(上一条 131, **+6**)。
  本包单独: `test_pipeline.py` **57 OK**(+3, `ReloadConfigTest`) · `test_commit.py` **30 passed**(+3, 接线守阵)。
- **红验**: ①把 `commit.py` 的 `reload_config(cfg)` 换回旧行为(`cfg, None`, 即复用启动那份) ⇒
  `test_post_rebase_rerun_uses_reloaded_config` FAIL(第二轮闸门名仍是"旧闸门") +
  `test_post_rebase_broken_new_config_blocks_push` FAIL(`不该走到推送`);
  `test_post_rebase_unchanged_config_stays_silent` 照旧绿(它断言"没有那行", 属预期)。
  ②去掉 `reload_config` 的 STOP 复检(改成无条件交出 fresh) ⇒
  `ReloadConfigTest::test_broken_new_config_reports_problem` FAIL。两处均已还原(`grep RED-VERIFY` 零残留)。
- 守卫: `kb.check` / `doc.links` / `doc.caps` 见提交闸门输出; `kb.index` 重建生成物。
- 改动面:
  - `.commands/my-commit-flow/scripts/_pipeline.py` —— 新增 `reload_config()` + 「自我改写后的配置重取」段;
    模块 docstring 补一行。
  - `.commands/my-commit-flow/scripts/commit.py` —— 第 6 步复跑前 `refresh_package_modules()` →
    `reload_config(cfg)`(坏则停 / 变则留痕 / 按新 `each_limit` 重建 `ctx`); import 与 docstring 补登。
  - `.commands/my-commit-flow/scripts/test_pipeline.py` / `test_commit.py` —— 新守阵 6 条 + 头部「测试计划」补登。
  - `.commands/my-commit-flow/references/pipeline.md` / `config.md` —— v3.1 步骤表 + 两处判据/时机。
  - `memory-bank/` —— 新任务档案 · `pitfalls/git/self-rewrite-config.md` 新条目 · `testing/guards.md`
    新增「提交流水线包」一节 · 本切片 · activeContext 切片。
- 行尾: 本切片与改动面全为 **LF**(仓库 2026-10-02 起 `text=auto eol=lf`)。
