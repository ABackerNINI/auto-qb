# my-commit-flow 网络容错 — git 命令单次 20s 超时 + 有界重试 3 次

> 摘要: Gitee **间歇性卡住(不报错, 就是不返回)** ⇒ 旧行为单次超时 120s 要等满才失败一次, `ship.commit`
> 报「提交成功(未推送)」+ 手工 `commands run ship.push`, 一次提交被拆成两步(2026-10-06 11:26 日志里
> 就有一次实录)。用户 2026-10-06 定调: **重试 3 次 / 每次 timeout 20s / 全部失败才当作失败, 覆盖
> push·pull·fetch 等所有 git 命令; GitHub 不需要重试, 但可加 timeout**。修法 = 容错下沉到
> `_pipeline.run_git`(`git()`/`git_rc()`/`git_run()` 一律经它), 判据 `_retryable` **按子命令分三档**
> (不是「任何非 0 都重试」); 镜像 `attempts=1`。改动面: 包内 5 脚本 + 1 守阵文件 + 包文档 6 处 + 坑档。
> 最后活动: 2026-10-06 18:18

**Refs:** memory-bank/tasks/26-10-06-commands-git-retry-timeout.md, memory-bank/testing/baselines/26-10-06-1818-commands-git-retry-timeout.md

## 现状

- **机制单点**: `_pipeline.run_git(args, timeout=GIT_TIMEOUT, attempts=GIT_ATTEMPTS, shell, env)` ——
  单次超时 + 有界重试, 全部尝试失败才把最后一次结果交出去; 实际尝试次数挂在返回值的 `attempts_used`,
  由 `retry_note(proc)` 在**失败行**里写成「已重试 N 次」。`GIT_TIMEOUT` 120→**20s**、
  `GIT_ATTEMPTS`=**3**、`GIT_RETRY_BACKOFF`=1s, 三者可用环境变量
  `COMMAND_FLOW_GIT_TIMEOUT` / `COMMAND_FLOW_GIT_ATTEMPTS` / `COMMAND_FLOW_GIT_RETRY_BACKOFF` 覆盖。
- **三档判据**(`_retryable`, 单点): ① 网络子命令 `push`/`fetch`/`pull`/`ls-remote`/`clone`/`remote`
  **失败即重试**(签名靠不住且它们幂等, 重试永远安全, 还能救回「推成功但被判失败」);
  ② 非幂等本地写 `commit`/`rebase`/`merge`/`reset`/`checkout`/`rm`… **只给超时不给重试**;
  ③ 其余(只读查询 + 幂等写)仅在 `rc == -1` 或命中 `TRANSIENT_MARKS` 时重试。
- **单层重试**: `push.py` 原手写「瞬时失败重试一次」循环与 `sync.py::remote_sha_with_retry` 均已退役
  (后者改名 `remote_sha`); 两层各重试 = 最多 6~9 次, 且「重试了几次」会拆成两处口径。
- **镜像**: `git_run(*proxy_disable_args(url), "push", mirror, branch, attempts=1)` —— 只给超时, 不给重试。
- **成功静默**: 重试成功不吐任何行(v3 契约不倒退); 失败行才缀重试次数。
- **顺带补齐**: `sync.py::_git_run_editor`(`rebase --continue`)从裸 `subprocess.run` 改走 `run_git`(带 env + 超时);
  `_ship_config.git()` 原本**完全无 timeout**, 补 `CONFIG_GIT_TIMEOUT` 并把超时/起不来按「取不到」返回空串。
- **守阵 15 条**(`test_pipeline.py`): `GitRetryTest` 13 + `MirrorNoRetryTest` 2。后者是**静态**守 —— 镜像口径
  在输出里零痕迹, 只能靠源码形态钉住 `attempts=1` 那一行。
- **验证**: my-commit-flow 单独 106 条(91→106, +15); `test.pkg` 126 passed / 154.5s;
  `test.full` 2677 + 4 / 99%(16021/163/5472/143, 50.6s) —— 基线
  [26-10-06-1818](../testing/baselines/26-10-06-1818-commands-git-retry-timeout.md)。
- **文档**: `references/pipeline.md` 新增「网络容错」节(三档表)/ `references/config.md` 区分「闸门 timeout」
  与「git 命令超时」/ 包 `README.md` / `commit.py` docstring / `ship/config.toml` note;
  坑档 `pitfalls/git/push.md` Gitee 条改写 + **复发 1**。

## 关键决策

- **为什么不是「任何非 0 都重试」**: `cat-file -e`(判路径在不在 HEAD)与 `merge-tree`(判能否干净合流)
  的**非 0 是正常答案**, 盲重试会把每次查询拖成 3 倍耗时(`_in_head` 在循环里被调用)并搅浑语义。
- **为什么非幂等本地写必须排除重试**: 超时被杀 **≠ 没执行完** —— `commit` 已落盘时重试会拿
  "nothing to commit" 当失败; `commit --amend` 已落盘时重试会**再挪一次 hash**, 而 v3.1 刚承诺
  「步骤行 `旧hash→新hash` 首尾相接」, 多出来的改写会让链子对不上。
- **❗子命令判据必须吃掉 argv 开头的 `git`**: `run_git` 拿到的是**完整 argv**, 不跳它子命令恒为 `"git"`,
  三档判据全部失效、**重试静默失效**(push 落进「本地只读」档, 非 0 不再重试) —— 实写时踩到过一次,
  由 `test_subcommand_skips_git_executable` + push/commit 两条守住。

## 未闭环

- **`ship.commit` 侧的真机实证还欠一次**: 本轮只验证到单元/场景层; 要等下一次真实「Gitee 卡住」才能看到
  失败行里的「已重试 N 次」与重试自愈的实际效果(2026-10-06 11:26 那种「未推送 + 手工补推」应不再出现)。
- **20s 是否够用未取实证**: 大对象首次 fetch/push(新 clone 全量拉取)可能超过 20s 单次上限 ——
  目前靠 `COMMAND_FLOW_GIT_TIMEOUT` 兜; 若真撞到, 处置是调环境变量而非改代码(默认值不该为极端场景让路)。
- **环境**: 本机残留 18 个 `python.exe` 僵进程(多个仅 ~4MB, 疑为先前被 SIGTERM 的 pytest 会话留下),
  测试 spawn 明显变慢(同 `pitfalls/testing/parallel-run.md` 的 CreateProcess 争用)。本轮未清进程。
- `memory-bank/issues/_index.md` cap 债务与 `activeContext/` 切片数债务是**本轮之前就有**的, 未动 ——
  按债务制转告用户另开会话清理。
