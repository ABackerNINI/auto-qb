# 2689 —— my-commit-flow 快照自举实施 (develop @ f4430f32)

> 摘要: 认领任务 26-10-07-ship-self-snapshot —— 把「本包脚本 / 配置住在被它自己操作的仓库里 ⇒ 同一次调用里
> "提交前 / 提交后"跑的不是同一版代码 / 规则」这类**自指**缺陷**治本**: 新增 `scripts/_snapshot.py`
> (入口把整包复制到**仓库之外**再从副本重入 ⇒ 一次调用 = 一个版本), 四个入口加 `__main__` 守卫,
> `_ship_config.find_root()` 认 `COMMAND_FLOW_REPO_ROOT`, 退役 `refresh_package_modules` / `reload_config` /
> `sync._reload_cfg` 三条治标机制及接线, 新增 `pack_touched` 步骤行; 守阵迁到 `test_snapshot.py`(15 条)。
> 真机 `my-commit-flow.sync` 与 `verify-ref` 均经快照重入成功、无残留临时目录。
> 基线时间: 2026-10-07 02:43

**Refs:** memory-bank/tasks/26-10-07-ship-self-snapshot.md, memory-bank/activeContext/26-10-07-0208-ship-self-snapshot.md

- 分支: develop @ **f4430f32**(开工 `commands run my-commit-flow.sync` = 快进 0b614153→f4430f32, 远端领先 2 笔;
  本轮尚无本地提交)
- 命令: `commands run test.full`(Windows)
- **实测 (Windows)**: **2689 passed + 4 skipped, 覆盖率 TOTAL 99%**; pytest 自报 **50.76s**(task 52.3s)。
  语句 **16021** / 未覆盖 **163** / 分支 **5472** / partial **143**。
- 相对上一条 [26-10-07-0204](26-10-07-0204-webui-delta-sync-feasibility.md)
  (2686 + 4 / 15823 / 163 / 5472 / 143): passed **+3**、语句 **+198**, 其余三项逐位相同 ——
  **归因于开工同步快进进来的远端两笔**(`a5577646` WEBUI 错误历史 tooltip 修复改了 `src/`),
  与本轮改动无关(本轮只动 `.commands/my-commit-flow/`, 不进 `--cov=src` 统计面)。
- **包内脚本测试**: `commands run test.pkg` **142 passed**(改前 141)—— 删 15 条旧守阵
  (`PackageRefreshTest` 3 + `ReloadConfigTest` 3 + `test_commit.py` 5 + `test_sync.py` 4)、
  增 16 条(`test_snapshot.py` 15 + `test_commit.py::test_post_rebase_pack_changed_leaves_hint`), 净 +1。
  首跑 4 条 push 用例在 `-n 4` 并行下假红(`git-receive-pack: Permission denied`), 串行复跑全绿 ——
  与本轮改动无关(同族见 `memory-bank/pitfalls/testing/parallel-run.md`)。
- 过程注记: `commands run doc.caps` 无债务; `kb.index` 重建 20 个生成物; `tests/test_memory_bank.py` 37 passed。
