# 2686 —— sync.py 生成物自动化解改用合并后的配置(自我改写的配置快照过期 · 第二轮)

> 摘要: 收掉同族第三处 —— `sync.py` 的**生成物自动化解**先把树推到上游 tip, 再按白名单丢本地那份并重跑
> 生成器, 而白名单来源 / 重跑命令 / `auto_resolve_generated` 都取自**进程启动时**那份 `cfg`。上游那笔若
> 改了 `.my-commit-flow.toml`(本包目录就在仓库里), 就是"拿旧政策处置合并后的树": 旧白名单**放宽** =
> 静默丢内容, 收窄 = 该保的没保, 重跑命令换了 = 重跑的是旧生成器(`--check` 自证也自证的是旧规则)。
> 修法 = `sync._reload_cfg(cfg)`(`_pipeline.reload_config` + "新配置仍允许自动化解"), 快进后 / rebase
> 每轮开头与收尾各取一次; 任一档不成立即**放弃自动化解、回滚**, 退回现状失败行。零 `src/` 改动 ——
> 改动全在 `.commands/my-commit-flow/` 与 `memory-bank/`(都不在 `testpaths`), 故覆盖四项与上一条
> **逐位相同**。基线时间: 2026-10-07 01:44

**Refs:** memory-bank/tasks/26-10-06-ship-rerun-stale-config.md

- 分支: develop @ **20bd2157**(开工 `commands run my-commit-flow.sync` =
  `同步: 远端领先 1 笔 → 快进 b56520ed→20bd2157 · 本地未提交改动原样保留`; 本轮改动测量时尚未提交)
- 命令: `commands run test.full`(Windows —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **2686 passed + 4 skipped, 覆盖率 TOTAL 99%**。
  语句 **16021** / 未覆盖 **163** / 分支 **5472** / partial **143**。
  耗时: 两次采样 **54.88s**(索引重建前) / **50.52s**(索引重建 + 本切片落盘后的确认采样) ⇒ 区间约 **50~55s**。
  - 注: 首次采样那次的 **4 failed** 全是索引未重建的老签名 —— `test_index_is_regenerated` /
    `test_kb_index_is_regenerated` / `test_gen_all_check_is_green` 三条等的是本轮 `commands run kb.index`,
    `test_claim_chain_is_bidirectional` 等的是**本切片**落盘(它就在本档案 `**Refs:**` 里)。
    索引重建 + 本切片落盘后该四条转绿 ⇒ 2686。
- 相对上一条 [26-10-06-2108](26-10-06-2108-ship-rerun-stale-config.md)
  (2682 + 4 / 16021 / 163 / 5472 / 143): 语句 / 未覆盖 / 分支 / partial **四项逐位相同**(本轮零 `src/` 改动);
  **passed +4 全部来自开工同步进来的那笔 `20bd2157`**(kb.nav 隐藏条目: `tests/test_kb_nav.py` 35→39 条),
  与本轮改动无关 —— 本轮只动包脚本(`.commands/`)与知识库, 二者都收不进 `testpaths = tests`。
- **包自测**(不在 `testpaths`, 由 `commands run test.pkg` 跑): **141 passed / 186.3s**(上一条 137, **+4**)。
  本包单独: `test_sync.py` **34 passed / 367.98s**(+4, 配置重取族)。
- **红验三处**(均已还原, `grep RED-VERIFY` 零残留):
  - ①**快进路径不重取**(`fresh = cfg`) ⇒ `test_behind_overlap_new_config_disables_autoresolve` FAIL +
    `test_behind_overlap_new_regen_cmd_is_used` FAIL(内容停在旧生成器的 `generated:gen/a.md`),
    而分叉那条**照旧绿** ⇒ 两个取用点各自独立受守。
  - ②**分叉路径两处都不重取** ⇒ `test_diverged_conflict_new_config_narrowing_rolls_back` FAIL
    (`assert not ok` 拿到 `True`: 拿旧白名单把它"化解"掉了), 快进两条照旧绿。
  - ③**去掉 `_reload_cfg` 的"新配置关掉自动化解"档** ⇒ `test_reload_cfg_honours_disk_and_policy` FAIL。
- **顺带修的自身事故**: `git status` 末尾报 `.commands/my-commit-flow/references/config.md`
  `CRLF will be replaced by LF` —— 上一轮那次 Edit 把整份从 `LF=69` 写成 `CRLF=81`(git diff 干净, 只有
  警告露马脚)。按字节归一回 LF; `pitfalls/git/editing-traps.md` 的 `sed -i` 条目**复发 +1**, 并把判据
  从"用哪个工具"改到"**改完必查**"(旧文案把 Edit 说成安全选项, 正是这次没查的原因)。
- 守卫: `kb.check` / `doc.links` / `doc.drift` / `doc.caps` 见提交闸门输出; `kb.index` 重建生成物。
- 改动面:
  - `.commands/my-commit-flow/scripts/sync.py` —— 新增 `_reload_cfg()`; `_resolve_behind_overlap` 快进后
    重取 + 按新白名单复核已丢弃路径; `_resolve_rebase` 每轮循环开头与收尾各重取; 两处 docstring 补判据。
  - `.commands/my-commit-flow/scripts/test_sync.py` —— 夹具扩 `tag` / `auto`; 新增 `_push_remote_files` /
    `_seed_repo_config_conflict`(配置放进仓库里) + 守阵 4 条 + 头部「测试计划」补登。
  - `.commands/my-commit-flow/scripts/_pipeline.py` —— `reload_config` docstring 补第二个调用点与两侧"停"的差别。
  - `.commands/my-commit-flow/references/{pipeline,config}.md` —— 生成物自动化解节 / 读配置时机表补 sync。
  - `memory-bank/` —— 本档案续记(第二轮) · `pitfalls/git/self-rewrite-config.md` 补第二条目 + 摘要/触发扩写 ·
    `pitfalls/git/editing-traps.md` 复发 +1 · `testing/guards.md` 补 4 行 · 本切片 · activeContext 切片更新。
- 行尾: 本切片与改动面全为 **LF**(仓库 2026-10-02 起 `text=auto eol=lf`)。
