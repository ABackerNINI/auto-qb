# 26-10-06-commands-git-retry-timeout — my-commit-flow: git 命令单次 20s 超时 + 有界重试 3 次

**Status:** Done
**Added:** 2026-10-06
**Updated:** 2026-10-06 18:18
**Summary:** 用户动议「Gitee 偶尔卡住, 经常需要补推」⇒ 给 my-commit-flow 的 git 命令加统一容错: 单次超时 120s→**20s**, 失败后**有界重试 3 次, 全部失败才判失败**, 覆盖 push/pull/fetch 等所有 git 命令; GitHub 镜像**只给超时不给重试**。机制下沉到 `_pipeline.run_git`(`git()`/`git_rc()`/`git_run()` 一律经它), 判据 `_retryable` **分三档**而非「任何非 0 都重试」: 网络子命令失败即重试 / 非幂等本地写(commit·rebase·merge…)只给超时不给重试 / 其余仅在超时或瞬时签名时重试。`push.py` 手写重试循环与 `sync.py` 的 `remote_sha_with_retry` 退役(避免双层重试), `_ship_config.git()` 补上原本**完全缺失**的超时。新增 15 条守阵。test.pkg 126 passed(my-commit-flow 单独 106 条); test.full 2677 passed + 4 skipped / 99%(基线 [26-10-06-1818](../testing/baselines/26-10-06-1818-commands-git-retry-timeout.md))。
**Topics:** commands-git-retry-timeout
**Refs:** memory-bank/testing/baselines/26-10-06-1818-commands-git-retry-timeout.md, memory-bank/activeContext/26-10-06-1818-commands-git-retry-timeout.md, memory-bank/pitfalls/git/push.md

## 原始请求

用户: 「my-commit-flow, gitee 偶尔会出现卡住的情况, 经常需要补推。需要添加重试机制 + timeout 机制, 重试 3 次, 每次 timeout 20s, 全部失败才当作失败, 包括 push/pull/fetch 等所有 git 命令, github 不需要重试, 但可加 timeout」。
随后「继续」推进实施、「收尾 DOD, 提交」授权收尾与入库。

## 思考过程与决策

- **卡住 ≠ 报错, 这是本轮的根因**: 旧行为单次超时 120s, Gitee 卡住时要**等满 120s 才失败一次** ⇒
  `ship.commit` 报「提交成功(未推送)」+ 手工 `commands run ship.push`, 一次提交被拆成两步(同日 11:26
  的日志里正是一次实录)。旧的重试判据挂在两个**具体错误签名**上(`Recv failure` / `Connection was reset`),
  而卡住是**不返回** —— 签名判据对它天然失效。修法必须同时动两处: ①超时收紧; ②重试不依赖签名。
- **为什么不是「任何非 0 都重试」**: 有些调用的**非 0 是正常答案** —— `cat-file -e` 判路径在不在 HEAD、
  `merge-tree` 判能否干净合流。盲重试会把每次查询拖成 3 倍耗时并搅浑语义(`_in_head` 在循环里被调用)。
  反过来, 网络子命令的失败签名五花八门(网关 502 / 代理重置 / TLS 抖动), 靠白名单必然漏。于是**按子命令分三档**:
  ① 网络子命令(`push`/`fetch`/`pull`/`ls-remote`/`clone`/`remote`)**失败即重试** —— 它们幂等
  (fetch/ls-remote 只读; push 同 ref 重推是 no-op 或 "up-to-date"), 重试永远安全, 还能顺手救回
  「推成功但被判失败」; ② 非幂等本地写(`commit`/`rebase`/`merge`/`reset`/`checkout`/`rm`…)**只给超时不给重试**;
  ③ 其余(只读查询 + 幂等写)仅在 `rc == -1`(看门狗杀树)或命中 `TRANSIENT_MARKS` 时重试。
- **②为什么必须排除重试**: 超时被杀 **≠ 没执行完**。`commit` 若已落盘, 重试会拿到 "nothing to commit"
  被当成失败; `commit --amend` 若已落盘, 重试会**再挪一次 hash** —— 而 v3.1 刚建立「步骤行 `旧hash→新hash`
  首尾相接」的承诺, 多出来的那次改写会让链子对不上。`rebase --continue` 同理("no rebase in progress")。
- **重试层只做一层**: `push.py` 原有的「瞬时失败重试一次」手写循环与 `sync.py` 的 `remote_sha_with_retry`
  都退役 —— 两层各重试 = 最多 6~9 次尝试, 且「重试了几次」会拆成两处口径, 失败行说不清。`attempts` 是唯一旋钮。
- **镜像的例外是用户明示的**: GitHub 允许滞后且成败都不提(26-09-28 定调), 重试它没有收益 ⇒ `attempts=1`。
  这条口径**没有行为出口**(输出里零痕迹), 所以用**静态守阵**钉住 `push.py` 那一行。
- **成功静默, 失败留痕**: 重试成功不吐任何行(v3「沉默即成功」不倒退); 失败行在原因后缀「已重试 N 次」——
  否则读的人只看到一次失败原因, 会以为命令没试过就报错而去手工补跑。
- **`_ship_config.git()` 的超时是顺带但必要的**: 它是配置加载器的 git 调用(`remote -v` / `rev-parse` /
  `config --get-regexp`), 原本**裸 `subprocess.run` 无 timeout** —— 用户口径是「所有 git 命令」, 而这条路
  同样能挂死。它**不重试**(本地查询, 重试无意义), 只补超时 + 超时/起不来按「取不到」返回空串。
  常量写在 `_ship_config` 而非 import `_pipeline`: 后者 import 前者, 反向依赖成环。

## 实现计划

1. `_pipeline.py`: `GIT_TIMEOUT` 120→20; 新增 `GIT_ATTEMPTS`/`GIT_RETRY_BACKOFF`/`NETWORK_SUBCOMMANDS`/
   `NON_IDEMPOTENT_SUBCOMMANDS`/`TRANSIENT_MARKS`; 新增 `run_git`/`_retryable`/`_subcommand`/`retry_note`;
   `git()`/`git_rc()`/`git_run()` 改经 `run_git`; `run_capture` 加 `env` 参数(供 `rebase --continue`)。
2. `push.py`: 删手写重试循环; 主线走默认 3 次; 镜像 `attempts=1`; 失败行缀 `retry_note`。
3. `sync.py`: `remote_sha_with_retry` → `remote_sha`; `_git_run_editor` 改走 `run_git`; `_git_reason` 缀重试备注。
4. `_ship_config.py`: `CONFIG_GIT_TIMEOUT` + 超时/起不来返回空串。
5. 守阵: `test_pipeline.py` 新增 `GitRetryTest`(13 条) + `MirrorNoRetryTest`(2 条); 同步「## 测试计划」。
6. 回写: `references/pipeline.md`(新增「网络容错」节 + 三档表)/ `references/config.md`(两种 timeout 消歧)/
   包 `README.md` / `commit.py` docstring / `ship/config.toml`; 坑档 `pitfalls/git/push.md`(改写 + 复发 +1)。
7. 收尾: 立本档案 + activeContext 切片 + 基线切片 + `kb.index` + `test.full`。

## 子任务状态表

| 子任务 | 状态 | 备注 |
|---|---|---|
| `_pipeline.py` git 层(run_git / _retryable / 三档判据) | ✅ 完成 | `GIT_TIMEOUT` 20s · `GIT_ATTEMPTS` 3 · 退避 1s, 均可环境变量覆盖 |
| `push.py` 收编重试 + 镜像 attempts=1 | ✅ 完成 | 删手写循环, 避免双层; 失败行带「已重试 N 次」 |
| `sync.py` 去双层重试 + editor 调用走看门狗 | ✅ 完成 | `remote_sha_with_retry`→`remote_sha`; `rebase --continue` 带 env + 超时 |
| `_ship_config.py` 补超时 | ✅ 完成 | 原本完全无 timeout |
| 守阵 15 条 | ✅ 完成 | `GitRetryTest` 13 + `MirrorNoRetryTest` 2(静态钉镜像那一行) |
| 文档回写 6 处 | ✅ 完成 | pipeline.md / config.md / 包 README / commit.py / ship config.toml / pitfalls/git/push.md |
| 收尾(档案 / 切片 / 索引 / test.full 基线) | ✅ 完成 | 数字见进度日志 |

## 进度日志

- **2026-10-06 17:3x** 开工 `commands run my-commit-flow.sync` → 快进 `ec53fda0→779cf088`(远端领先 12 笔), `同步成功 779cf088`。
- **2026-10-06 17:4x** 读码定位: 全部 git 调用收口在 `_pipeline.run_capture`(默认 `GIT_TIMEOUT` 120s),
  `git()`/`git_rc()`/`git_run()` 三入口; 另有 `push.py` 手写重试、`sync.py` 的 `remote_sha_with_retry`、
  `sync.py::_git_run_editor` 与 `_ship_config.git()` 两处**裸 `subprocess.run`**(后者无 timeout)。
- **2026-10-06 17:5x** 实施 1-4。**自测时抓到一个致命自错**: `_subcommand` 未跳过 argv 开头的 `git`
  (`run_git` 传的是完整 argv) ⇒ 子命令恒为 `"git"`, 三档判据全部失效、**重试静默失效**
  (push 落进「本地只读」档, 非 0 不再重试) —— 恰好把本功能修没。修法: 跳过开头可执行名, 并加
  `test_subcommand_skips_git_executable` + push/commit 两条回归。**这个自错是本轮最值得留档的一点。**
- **2026-10-06 18:0x** 守阵 15 条 + 文档回写 6 处; `dev.fmt`; 坑档 `pitfalls/git/push.md` Gitee 条改写
  (摘要 / 处置 / 复发 1, 写明「为什么没命中」= 签名判据对「不返回」失效)。
- **2026-10-06 18:0x** 验证: `test_pipeline.py` **51 passed**(13.1s, 含新 15 条);
  `test_sync.py + test_commit.py` **55 passed**(155.8s); `test.pkg` **126 passed**(154.5s);
  `test.full` **2677 passed + 4 skipped / 99%**(16021/163/5472/143; 耗时 50.59s / 63.80s 两次采样)。
  `kb.index` 重建 20 生成物; 6 个索引 `--check` 全绿(主键纪律 463 文档 / 认领链 OK);
  `doc.caps` / `doc.links` / `check_command_drift` 全绿(无新增债务)。
- **2026-10-06 18:1x** 收尾: 立本档案 + activeContext 切片 + 基线切片 + `testing/baseline.md` 常驻警告
  的一处陈旧值订正(该行仍写 `test_preflight.py`(已改名 `test_pipeline.py`)与旧计数 103)。
- **环境观察(非本轮引入)**: 本机残留 18 个 `python.exe`(多个仅 ~4MB, 疑为先前被 SIGTERM 的 pytest
  会话留下的僵进程), 测试 spawn 明显变慢(与 `pitfalls/testing/parallel-run.md` 的 CreateProcess 争用同源)。
  本轮测试用 `-n 4` 跑完, 未清进程。
