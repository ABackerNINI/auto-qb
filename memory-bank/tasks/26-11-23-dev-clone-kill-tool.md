# 26-11-23-dev-clone-kill-tool — clone 域残留进程定点清理工具(clone_kill)与 dev.run dry-run 孤儿取证

**Status:** Done
**Added:** 2026-11-23
**Updated:** 2026-11-23
**Summary:** dev.run --dry-run 孤儿残留根因定案(守护循环 by-design)+ clone_kill 新工具(grilling 九问拍板 D1-D9, 判据/实杀 import 复用 port_kill 单点)+ 全治理链落地 + 真机冒烟过 + 两轮分面评审零 actionable 出口 + test.full 全绿(见 kb.baseline 26-11-23-0017)
**Topics:** dev-clone-kill-tool

## 本篇只回答

为什么 dev.run 干跑探针会残留、拍板了什么(D1-D9)、clone_kill 怎么实现与验证。工具的日常用法看 `.commands/dev/config.toml` 的 dev.clone-kill 条目与 `pitfalls/ops/dev-run-dry-run-daemon-orphan.md`(判别/处置单点), 本篇不重复。

## 原始请求

1. 另一会话报告: 两个干跑探针(pid 15624/36312, 本 clone .venv 的 dev_run.py config.yml --dry-run)确认存活, taskkill 红线且 port-kill 不适用非监听进程, 请任务管理器手动结束。
2. 「参考 port-kill 添加一个专门用于 kill 当前克隆(非特指 clone2)发起的进程, 或在 temp 位置的进程」, 附 grilling 触发词。

## 思考过程与决策

grilling 一轮九问(❓Q1-Q9)+ 两次「按推荐」拍板, 全部结论:

- **D1 范围**: kill 工具 + dry-run 只读取证, 产品代码零改动。取证定案: `src/auto_qb/cli.py:305` `manager.run(args.dry_run)` —— **--dry-run 就是守护循环主入口, 残留不是挂死是 by-design**; 残留机制 = 守护循环 + wrapper 被停(TaskStop/会话收尾只杀 bash/uv 链)→ venv python 子进程孤儿化继续持 state 锁、周期落盘。预防面(D9)只记档不改产品(父亡自毁/--dry-run 语义改造均属独立立项)。
- **D2**: 「temp 位置的进程」判据删除 —— 现场反证: 本机非 clone 根位置的 python 长期进程全是合法活体(uv shim 在 Roaming\uv、VSCode LSP 在 extensions、gtm 在别的 clone), 按位置杀没有身份锚, 与 fail-closed 纪律冲突; 案例真复现再立第二判据。
- **D3**: 判据 import 复用 port_kill 的 `in_clone_domain` + `_kill_pid`(不复制, 判据/实杀不两处演化; e2e_selfcheck 有同款先例); 已接受盲区 = 相对 cmdline 的 uv 包装杀不到(子死后自退)。
- **D4**: 默认只列; 杀必须 `--match`(cmdline 小写子串, 非正则)+ `--yes` 双闸缺一不可。依据: bash 瞬态命令文本含 clone 根(取证实测), clone 域分不出「本会话残留」与「并发会话活体」; 「杀全部 clone 域」这个表达从工具里物理删掉。
- **D5**: 自身 pid + 祖先链(PPID 上溯)硬排除, 非配置项(工具自身经 commands 引擎跑在 clone .venv 下, 自身 cmdline 还含 match 词)。
- **D6**: 目标后代闭包(PPID 递归)连坐但逐个过同一闸, 后代先杀(深度降序); 后代里的 clone 域外进程(如产品拉起的 explorer)被闸保住, REFUSED 行记账 rc=1。
- **D7**: nt/posix 双支(守阵在 Docker testbed 跑), 与 port_kill 同构。
- **D8**: 全治理链 = scripts/clone_kill.py + commands 收录 dev.clone-kill + AGENTS.md 红线豁免第三处 + pitfalls 新档 + 守阵新文件 + memory-bank 回写。
- **评审修复轮增补**(round-1 三分面 10 发现全修): `--match` 空白值拒收 rc=2(空子串恒真 = 变相「杀全部」)、后代实杀行补归属审计行、AGENTS.md 余量回 5、守阵补自杀排除生产路径守卫(main 流程 os.getpid 钉表外常量 + 自身形态入表断言零出现)等。

现场关键事实(开工取证): 两个探针已死亡(三次定点/全扫复核), 悬案作废; 38080/38081/18788 当时由**其它 clone 的生产实例**持有(pid 40156/28260)—— clone 域闸此刻就在实际挡刀, 也证明「temp/位置」判据方向不可取。

## 实现计划

1. scripts/clone_kill.py: 全量进程枚举(nt: Win32_Process 一把查全含 ParentProcessId; posix: /proc comm/cmdline/stat)→ 候选筛选(in_clone_domain + 排除集 + match)→ 杀面编排(后代闭包逐个过闸, 深度降序)→ main(双闸/空表 fail-safe/rc 0/1/2)。实杀经 port_kill._kill_pid。
2. commands 收录 dev.clone-kill(add dry-run 自证后 --write; doc 指针指向新 pitfall)。
3. pitfalls/ops/dev-run-dry-run-daemon-orphan.md(判别/处置/守阵)+ AGENTS.md 进程安全节豁免追加 + kb.index。
4. 守阵 tests/test_clone_kill_script.py(docstring 测试计划随用例同步; 判据单点/候选矩阵/排除集/后代闸/双闸接线/双平台扫描/角落加固)。
5. 真机端到端冒烟: 本会话自有 dummy 探针 spawn → list → match 收窄 → --yes 实杀 → 零残留复核(杀的是自己会话起过的进程, 符合「本次会话起过又确认残留」纪律)。
6. 分批评审: 三分面(安全/正确性/测试缺口)→ 10 发现全修 → 修复轮复评零 actionable 出口。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | scripts/clone_kill.py(枚举/筛选/杀面/main, 判据与实杀复用 port_kill 单点) | Done(2026-11-23) |
| S2 | dev.clone-kill 收录(commands add 自证 + --write, doc→pitfall) | Done(2026-11-23) |
| S3 | pitfall 新档 + AGENTS.md 豁免第三处 + kb.index + doc.caps | Done(2026-11-23) |
| S4 | 守阵新文件(docstring 测试计划同步) | Done(2026-11-23) |
| S5 | 真机端到端冒烟(dummy 全链 + 零残留) | Done(2026-11-23) |
| S6 | 两轮分面评审(检全过检, 全修, 零 actionable 出口)+ GBK mojibake 既有缺陷入池 | Done(2026-11-23) |
| S7 | test.full + 基线切片 | Done(2026-11-23) |

## 进度日志

### R0 · 立档 (2026-11-23)

- grilling 一轮九问拍板 D1-D9; dry-run 守护循环取证定案(cli.py:305); 现场证伪「temp 判据」。
- 实现全链落地(S1-S6), 真机冒烟通过(dummy 探针全链清理, 残留复核零; 38080/38081 生产实例全程零出现在候选行 —— clone 域闸真机背书)。
- 评审两轮: 三分面 10 发现(2 major: --match 空白值绕闸 / 自杀排除生产路径零守卫)当场全修, 修复轮复评零 actionable 出口; 评审账见提交 trailer(Review: 行)。
- 范围外发现(范围守恒未修, 入池): port_kill._kill_pid nt 支 taskkill 输出按 utf-8 解 GBK 变 mojibake, issue 26-11-23-0012。
- 全绿数字见 kb.baseline 最新切片(裸数字不抄此处)。

**Refs:** memory-bank/pitfalls/ops/dev-run-dry-run-daemon-orphan.md, memory-bank/issues/26-11-23-0012-bug-port-kill-gbk-mojibake.html, memory-bank/testing/baselines/26-11-23-0017-dev-clone-kill-tool.md

- 2026-11-23 00:17 实施收口: clone_kill 工具+守阵+收录/豁免/坑档治理链全落地, 真机端到端冒烟过(自有 dummy 全链清理, 生产实例零出现在候选), 两轮分面评审零 actionable 出口, test.full 全绿见 kb.baseline 26-11-23-0017; 范围外 GBK mojibake 入池 26-11-23-0012
