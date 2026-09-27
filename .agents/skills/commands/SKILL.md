---
name: commands
description: '项目命令的统一入口:想跑测试(pytest)/格式化(yapf)/提交推送(git commit/push)/依赖同步(uv)/建索引这类项目命令,先来这里找 task id —— 裸跑等价物会丢包内环境陷阱。命令单点定义在 <仓库根>/.commands/ 的包里,只认 task id。USE FOR: 想跑任何项目命令时(多半已收录,先 list);已知 id 直接 run;想加新命令先 list 查重再走 add 收录协议;用户说"跑一下测试"/"提交"时。DO NOT USE FOR: 一次性调试命令(直接在对话里跑)、"该不该做这件事" —— 只管"怎么跑",不管"该不该跑"。'
user-invocable: true
---

# commands

项目命令的**统一调用面**:要跑命令时不去文档里抄,先按层级定位再调。

❗**缺省规则 —— 先 task id, 后裸命令**: pytest / yapf / git commit / 依赖同步 / 包内脚本, 第一步找 task id; 裸跑会丢包里单点的环境陷阱(TMPDIR / cmd.exe 写法 / 红线拦截); 一次性调试直接跑。

> `<skill-dir>` = 本 skill 目录(先 Glob 定位 `**/commands/scripts/run.py`); 项目解释器跑: `uv run python <路径> run <task>`。

引擎只认识**包**:项目事实全在 `<包>/config.toml` —— **加命令只有"放进某个包"这一条路**,包外文件引擎扫不到(静默失效)。

## 入口:先试跑, 失败才装

`commands run <task>` **直接试跑**; command not found 才装一次(幂等):
`python <skill-dir:commands>/scripts/install_wrapper.py`(仓库根 + PATH, 跨项目共享)。
坑见 [references/wrapper.md](references/wrapper.md)。

## 记法

- **文档记法** `commands run <task>` —— 文档与回复一律用它; 子包两种写法都认(`ship.commit` / `包/子包.<task>`)。
- **真实入口** 装 wrapper 即它本身; 没装时展开 `python <skill-dir:commands>/scripts/run.py <子命令> [参数]`。

两者都不是让你抄命令本体 —— 抄一份就是反漂移闸门判红的形态。

## 四个子命令

| 子命令 | 作用 |
|---|---|
| `run <task>` | 校验前置后执行,超时按失败计。**常规路径只用它** |
| `list [包路径]` | 列出**当前层级**:包 + 常显命令 |
| `show <task>` | 打印展开命令与 `doc` 深读指针,不执行(排障/自证) |
| `add` | 收录一条命令进包(默认 dry-run) |

`run` 默认只回摘要;`requires`/`risky` 任务先自证**首条**命令(共 N 条, 全量 `show`)再跑。
摘要 = **末几行结论 + 异常行**(`[WARN]`/`[FAIL]`/`Traceback`,封顶 8 行)—— ❗检查表的 WARN 内容在中段, 只取末几行等于逼调用方重跑。协议行 `RESULT/WHY/NEXT/EVIDENCE:` 与异常行**同权必保**, 失败时紧跟 `[FAIL]` 转述; **文本无裸 rc**。
结论行(`N passed`/`TOTAL`)**无条件必保**(警告明细可能打在其后)。`silent_success = true`(test.full/quick): 成功只出结论行、无略过提示; 信息类不加, 有损摘要靠提示兜底。

## 引导:按当前任务逐级下钻

- **定位** → 不知道调哪个 `list`,未定位再 `list <包>[/<子包>]`; 已知 id `run`; 细节 `show` 的 `doc` 指针; 排障 `list --all`。

包内 README 与 `references/` 是**包私有**(引擎不读):按 `doc` 指针按需读,**不要整读**。

`★` = 常显,浮到父级;一级只出"包 + 常显" —— **靠分层,不靠写得短**。

## 收录协议

三条判据**任一命中**就自己收:①**重复**(本会话第二次) ②**难拼**(≥2 个环境前缀/参数) ③**易错**(有"看着正常但不生效"的写法)。都不中 → **不收**。

细节(判据 / 放哪个包 / `add` 必填项 / 防滥用)见 **[references/howto-add-command.md](references/howto-add-command.md)**,收录时才读。

## 停手点

- **STOP(rc=1)**:配置写错 / 占位符展不开 / 参数给了不接参的 task / `requires` 前置非 0 / task id 重复 / 包名≠目录名 / `doc` 指针落空 —— **不静默降级**, 静默失效比报错坏得多。
- **命令非 0(rc=1)**:失败输出自带「原因 + 下一步」—— 语义在那, 不在 rc 数字; 不要盲目照着重跑。

## 反模式

- ❌ 去文档里抄命令(可能正是"看起来最正常但不生效"的那版);用 `list`/`show` 取。
- ❌ 裸跑已收录命令的等价物 —— 见顶部缺省规则; 一次性调试(未收录)才直接跑。
- ❌ 见命令就收 —— 三条判据同时是上限,否则配置变垃圾桶。
