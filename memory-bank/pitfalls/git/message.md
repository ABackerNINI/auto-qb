# 提交信息

> 摘要: 提交信息里的反引号会被 bash 当命令替换; `commit -F -` 的 heredoc 会让 push 静默不执行; 规模数字要当场实测。
> 等级: L0
> 触发: 写提交信息, git commit -m, git commit -F, 提交消息, 规模数字

### 提交信息里的反引号会被 bash 当命令替换

- **触发**: 用 `git commit -m "… `xxx` …"` 写提交信息。
- **判别**: **双引号内也替换** ⇒ 那一段变成空, 同时报 `command not found`。
- **处置**: 用**单引号**包整条 `-m`, 或干脆不用反引号; 提交后 `git log -1 --format=%B` **复核**。
  ⚠ 已推送的提交**不要 amend + 强推**。

### `git commit -F - <<'MSG' … MSG && git push` 会让 push 静默不执行

- **触发**: 手拼裸 git 命令想"提交完顺手推"(提交与推送已由 `commands run ship.commit` 一条走完,
  正常流程不会写出这种命令; 见于排障 / 绕行场景)。
- **判别**: 结束符没被识别, 命令体读到 EOF, **push 被当成 heredoc 内容** ⇒ 提交成功但根本没推。
- **处置**: 提交与推送**不手拼命令** —— 一律 `commands run ship.commit`; 推没推上只认它的结果行
  (「提交成功 <hash>」; 带「(未推送)」才补 `ship.push`) —— **不要**提交后用 `git status -sb` 快照
  或手工 ls-remote 自查(快照本环境不可信, ls-remote 核对已内联进脚本; 见 [push.md](push.md) / [refs.md](refs.md))。

### 提交消息里的规模数字要在提交那一刻实测

- **触发**: 写提交信息里的"改了 N 行 / N 个文件"。
- **判别**: 上游合入会让基线行数变掉 ⇒ 沿用会话中途量的数字必然不准。
- **处置**: 当场实测(`git show HEAD^:<file> | wc -l` 这类), 不沿用旧值。

### 流水线脚本在 GBK 控制台打印 emoji 直接崩 (2026-09-22 已修)

- **触发**: gitmoji 提交信息 / 闸门与远端输出含 emoji, 走 my-commit-flow 脚本 print。
- **判别**: `UnicodeEncodeError: 'gbk' codec can't encode character '\U0001f41b'` —— 崩在打印层,
  但 git 操作(如 commit)可能**已成功**; 别被退出码骗, 也**不要**手工核 ref / 远端 —— 核对已内联进
  ship 脚本, 树净与否由重跑 `ship.commit` 的分流判定(见 [push.md](push.md))。
- **处置**: 四个 CLI 入口脚本(commit/preflight/push/verify_ref)入口已统一
  `sys.stdout/stderr.reconfigure(encoding="utf-8", errors="replace")`; 新增打印外部输出的
  CLI 脚本照抄这三行(库模块不动全局 stdout)。顺带补了 verify_ref 的 `--help` 契约:
  闸门 `verify_ref.py --help` 期望 rc=0, 手工解析参数时必须显式拦下 —— 否则 --help 被当
  期望 sha → 退出码 2 → 闸门假红(实测 2026-09-22)。
