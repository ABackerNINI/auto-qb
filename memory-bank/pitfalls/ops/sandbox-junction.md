# skill junction 在代理命令沙箱里新建即断

> 摘要: skill junction 在代理命令沙箱里新建即断
> 触发: skill 链接同步, junction, sync_agent_skills, ship.commit 闸门失败, Path.exists 假 False, codebuddy skills 断链
**Refs:** commit 38f09446 (2026-11-04 提交遇阻)

### `sync_agent_skills.py` 建的 junction 在代理命令沙箱里命令一结束就失效

- **触发**: 在 agent 命令执行环境里跑任何要过提交闸门「skill 链接同步(幂等)」的命令(如
  `commands run ship.commit`), 且 `.codebuddy/skills` 下需新建/重建 skill 链接 —— 闸门内的
  `python scripts/sync_agent_skills.py` 走 `mklink /J` 建目录联接。
- **判别**: ① 失败行 `提交失败: 闸门「skill 链接同步(幂等)…」未过 (rc=1)` + 输出一长串
  `! <skill> -> D:\...\.agents\skills\<skill>`; ② 两步自证: 一条命令建链接
  (`New-Item -ItemType Junction -Path <link> -Target <真实目录>` 返回成功), **下一条命令**查
  `Path.exists()` 为 False 即踩中(宿主原生终端里同一操作持久有效)。`dangerouslyDisableSandbox`
  也绕不过。
- **处置**: 别在 agent 里修 —— 清理断链再建、关沙箱均已验证无效(新建目标被改写为
  `...\modulardata\ai-agent\command-execution\sandbox-storage\unified-cache\<command-id>\drive\D\...`,
  命令结束即消失)。去**宿主原生终端**删掉 `<clone>\.codebuddy\skills` 下的断链(或整个目录后重跑
  `python scripts/sync_agent_skills.py`), 再回 agent 重跑 `commands run ship.commit`;
  `.git/COMMIT_MSG_AI.txt` 未被失败闸门消费, 可直接复用。
- **守阵**: 无专门机检 —— 闸门失败行 + 上述两步存在性判别即自证。
- **复发**: 0 (无既有档: 本次首次落档; 症状在 ship.commit 失败行之后才暴露, 开工路由不会主动到本条)

### 同闸门另一根因: clone 复制遗留的旧路径断链占位(不是沙箱新建失效)

- **触发**: clone 由别的目录整树复制/迁移后, `.codebuddy/skills/` 下留有一批 MSYS 风格
  旧路径的断链(如 `/c/Users/.../auto-qb-clone1/.agents/skills/<skill>`), Windows 解析不到
  => `Path.exists()` 为 False 但目录项仍占位。`ship.commit` 的闸门 `sync_agent_skills.py`
  对这批名字判 `is_junction()=False`(该函数首行 `if not path.exists(): return False`),
  于是走 `create_junction`, `mklink /J` 因同名已存在被拒 —— 输出一长串 `! <skill> -> ...`, rc=1。
- **判别**: 与上方「新建即断」只需两步区分 —— ①闸门输出里有没有 `+ <skill>` 成功项
  (2026-11-06 本次 `release` / `code-review` 为新建且成功); ②**下一条命令**查这些新建链接
  `Path.exists()` 与 `iterdir()`: 为 True 即未踩「新建即断」, 根因是断链占位、可在 agent 内直接修;
  为 False 才是上方沙箱坑, 按上方处置去宿主原生终端。
- **处置**: 只删断链, 不动目标内容、不碰有效链接。按源 `.agents/skills/` 的名字集合, 对
  `.codebuddy/skills/<name>` 中 `exists()=False` 的项用 `os.rmdir()`(junction) /
  `Path.unlink()`(symlink) 摘掉链接本身; 再跑 `python scripts/sync_agent_skills.py` 应 rc=0
  且全部 `+`, 跨命令复查新建链接 `iterdir()` 可读; 然后重跑 `commands run ship.commit`
  (`.git/COMMIT_MSG_AI.txt` 未被失败闸门消费, 可直接复用)。
- **守阵**: 闸门本身即守阵(rc=1 暴露); 判别②的两步自证是区分两种根因的单点。
- **复发**: 0 (2026-11-06 首次落档; 检索命中了本档触发词「ship.commit 闸门失败」, 但
  判别②自证不成立 —— 不是「没读坑档」, 而是同闸门存在第二种根因, 故并列留痕不 +1)。
