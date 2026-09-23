# Git 推送

> 摘要: 推送前必须先设 `TMPDIR`(否则闸门必红); 判"推没推上"的唯一依据是 `ls-remote`, 不是 push 的输出。
> 触发: push, 推送, 提交闸门, 推没推上, Gitee, GitHub, 镜像, CI action

### 提交闸门(`preflight.py` / `commit.py`)在工具 shell 的默认 `TMPDIR` 下必红

- **触发**: 跑预检 / 提交 / 推送。
- **判别**: 闸门跑的是 `commands run test.quick`, 而工具 shell 的 `TMPDIR` 默认指向 `H:\Temp` ⇒
  **测试本身全过**, 崩在**会话结束**的临时目录清理(`PermissionError [WinError 5] … pytest-current`),
  退出码非 0 ⇒ 预检判 `rc=1` 给 STOP。
  **判别法**: 闸门报红但失败输出里只有 `pytest-current` 的 PermissionError、没有任何 `FAILED`/`assert` ⇒ 是环境问题不是回归。
- **处置**: 跑预检/提交**前**加 `TMPDIR="R:/Temp/auto-qb/tests"`(与 `testing.md`「运行」那节同一个约定);
  ❌ 不要为此去改 `.commands/my-commit-flow/.my-commit-flow.toml` 的闸门命令(项目事实该外置, 但 TMPDIR 是环境事实, 换台机器路径就变)。

### Gitee 主线会间歇性 `Recv failure` —— 判"推没推上"只看 `ls-remote`

- **触发**: `git push` 报错 / 想确认推送结果。
- **判别**: 同一 URL 上一个通一个不通 = **链路层**, 不是远端名 / 凭据配错(实测连测 5 次只成功 2 次, 失败与成功交替)。
  ⚠ **命令报失败 ≠ 没推上** ⇒ **判定"推没推上"的唯一依据是 `git ls-remote <远端> <分支>`**
  (它自己也会瞬时失败, 重试 2~3 次再下结论)。
  ❗`git push --dry-run` **不能**用来判断 —— 它只做 ref 协商, 不发包, 永远"成功"。
- **处置**: 主线**可重试一次**; GitHub 镜像仍守"尝试一次, 失败只报一次"(不重试 / 不换代理 / 不改走 SSH /
  不回滚主线已完成的推送)。

### GitHub Actions: `astral-sh/setup-uv` 没有浮动大版本标签

- **触发**: 给 workflow 里的第三方 action 升大版本。
- **判别**: `@v10` **解析不了** —— 该 action 从 v8 起只发固定标签。
- **处置**: 固定到 commit SHA 并加版本注释; 升大版本前先查 `refs/tags` 里目标 ref **真的存在** ——
  "上一个大版本有浮动标签"不代表下一个也有。
