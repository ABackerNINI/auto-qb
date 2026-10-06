# Git 推送

> 摘要: 提交闸门依赖 `TMPDIR` 约定(默认盘会假红); 判"推没推上"只认 `ls-remote` 对比本地 HEAD —— 该核对已内联进 ship 脚本(结果行「提交成功 <hash>」), 手动 ls-remote 仅在报「无法核实」时; Gitee 间歇性卡住 / `Recv failure` 已由 git 层「单次超时 20s + 有界重试 3 次」兜住(2026-10-06, 不再要手工补推); 镜像只给超时且允许滞后, 成败都不提(26-09-28 定调)。
> 触发: push, 推送, 提交闸门, 推没推上, Gitee, GitHub, 镜像, 卡住, 重试, 超时, 补推, CI action

**Refs:** memory-bank/tasks/26-10-06-commands-git-retry-timeout.md

### 提交闸门(`_pipeline.py` 闸门引擎 / `commit.py` 编排)在工具 shell 的默认 `TMPDIR` 下必红

- **触发**: 跑预检 / 提交 / 推送。
- **判别**: 闸门跑的是 `commands run test.quick`, 而工具 shell 的 `TMPDIR` 默认指向 `H:\Temp` ⇒
  **测试本身全过**, 崩在**会话结束**的临时目录清理(`PermissionError [WinError 5] … pytest-current`),
  退出码非 0 ⇒ 预检判 `rc=1` 给 STOP。
  **判别法**: 闸门报红但失败输出里只有 `pytest-current` 的 PermissionError、没有任何 `FAILED`/`assert` ⇒ 是环境问题不是回归。
- **处置**: 跑预检/提交**前**加 `TMPDIR="R:/Temp/auto-qb/tests"`(与 `testing.md`「运行」那节同一个约定);
  ❌ 不要为此去改 `.commands/my-commit-flow/.my-commit-flow.toml` 的闸门命令(项目事实该外置, 但 TMPDIR 是环境事实, 换台机器路径就变)。

### Gitee 主线会间歇性 `Recv failure` / 卡住 —— 推送核对由 ship 脚本内联

- **触发**: `git push` 报错 / **卡住不返回** / 想确认推送结果。
- **判别**: 同一 URL 上一个通一个不通 = **链路层**, 不是远端名 / 凭据配错(实测连测 5 次只成功 2 次, 失败与成功交替)。
  ⚠ **命令报失败 ≠ 没推上** ⇒ 推没推上的判定依据是 ls-remote 现查远端真值 ——
  **已内联进 ship 脚本**(推完自动核对), 手工裸跑 `git push` 时才需要自己做(它自己也会瞬时失败, 重试 2~3 次再下结论)。
  ❗`git push --dry-run` **不能**用来判断 —— 它只做 ref 协商, 不发包, 永远"成功"。
- **处置**: `ship.commit` / `ship.push` 已内置「**单次超时 20s + 有界重试 3 次**(全部失败才判失败) + `ls-remote` 核对」——
  结果行「提交成功 <hash>」(真改写 HEAD 的步骤行在其上, v3.1 起), 失败一行含原因与下一步(v3 契约, 2026-09-28 起),
  失败行还会缀「已重试 N 次」; **别手动重跑核对**;
  手工裸跑 `git push` 时仍守: 主线**可重试 2~3 次**; GitHub 镜像尝试一次且**成败都不提**
  (允许滞后; 不重试 / 不换代理 / 不改走 SSH / 不回滚主线已完成的推送)。
  判据三档单点在 `_pipeline._retryable`: 网络子命令(push / fetch / pull / ls-remote …)**失败即重试**;
  非幂等的本地写(commit / rebase / merge …)只给超时**不给重试**; 其余只在超时或瞬时签名时重试。
- **复发**: 1 —— 2026-10-06 用户报告「Gitee 偶尔卡住, 经常需要补推」。**为什么没命中**: 旧处置的重试判据挂在
  **两个具体错误签名**上(`Recv failure` / `Connection was reset`), 而卡住是**不报错** —— 签名判据对「不返回」
  天然失效; 且旧口径是「重试一次」+ 单次超时 120s, 单次白等的代价远大于重试的收益(提交被拆成
  「未推送 + 手工补推」)。已改为 git 层统一「单次 20s + 有界重试 3 次」(`_pipeline.run_git`)。

### GitHub Actions: `astral-sh/setup-uv` 没有浮动大版本标签

- **触发**: 给 workflow 里的第三方 action 升大版本。
- **判别**: `@v10` **解析不了** —— 该 action 从 v8 起只发固定标签。
- **处置**: 固定到 commit SHA 并加版本注释; 升大版本前先查 `refs/tags` 里目标 ref **真的存在** ——
  "上一个大版本有浮动标签"不代表下一个也有。
