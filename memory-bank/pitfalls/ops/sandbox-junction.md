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
