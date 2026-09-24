# 包内说明文档被当成入口

> 摘要: 决策点文档(如 `AGENTS.md`)若把某条流程的"唯一去处"写成**包内 README 的链接**, 执行者只能整读它 —— 分层省下的 token 从另一头漏回来; 指针要写 task id, 细节外置到包内 `references/` 按需读。
> 触发: 提交流程要读文档, 包内 README, 整读 README, references, 深读指针, doc 键, 阅读预算, 命令漂移豁免

## 现象

- **触发**: 走提交 / 推送这类流程时, 想知道纪律与停手点, 于是打开包内 README。
- **判别**: `.commands/<包>/README.md` 被当成入口整读(2026-09-24 实测: 8212 字符, 一次约 4–5k token);
  而 `commands` 引擎的分层(包是黑盒 / 包内文件"人不读, 排障才 show")等于被绕过。
- **为什么是坑**: 它没有报错, 只是悄悄地把"读整份文档找命令"的成本搬回来 ——
  而这正是 commands 方案初衷三要消除的东西。

## 处置

- 决策点文档里**只写 task id**, 不写包内文档链接;`show <task>` 会打印 `doc` 深读指针(包内 `references/`, 引擎校验其存在性)。
- 包内 README 维持**索引形态**: 七步表 / 停手点 / 最致命的反模式 / 一张"深读看哪份"指针表; 完整判据、配置机制、反模式全集进 `references/`。
- 本环境专属事实(如 rebase / stash 为何禁用)单点在 `pitfalls/git/_index.md`, **包内不复制一份** —— 包要可移植, 环境事实换仓库要重新确认。

## 机检

- `commands run doc.caps`: `READ_BUDGET_CAPS` 给包内 README 定阅读预算(现 3000 字符), 超限且本次改动命中即 STOP —— 逼着把细节外置。
- `commands run doc.drift`: 扫描面含 `.commands/*/README.md` —— `.commands/` 豁免保护的是"命令的单点定义"
  (即 `config.toml`), **不保护 README 这份包内散文**。
- 闸门自身的两个陷阱(都已修, 别再踩): ①**`.exe` 未归一** —— 脚本类 task 的命令由引擎用 `sys.executable`
  拼出, Windows 上首 token 是 `python.exe` 而文档写 `python`, 于是脚本类手抄**判不出来**(2026-09-24 归一为去
  `.exe` 后缀); ②**`<each:>` / `<changed:>` 只盯本次改动清单**, 不是文件系统 glob —— 没匹配上会打
  "跳过 … 无匹配文件" 的 WARN, 那是**按设计跳过**, 别误读成闸门失效(2026-09-24 已在 WARN 文案里点明)。
