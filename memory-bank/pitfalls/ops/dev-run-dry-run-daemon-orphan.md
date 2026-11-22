# dev.run --dry-run 是守护循环: 停后台任务只杀 wrapper, python 孤儿继续持锁落盘

> 摘要: `commands run dev.run -- config.yml --dry-run` 不是「跑完即退」-- cli.py 把 --dry-run 原样传给守护循环主入口(`manager.run(dry_run=True)`, dry 只压动作, 循环永续); 后台任务被停/会话收尾只杀 bash/uv 包装链, venv python 子进程孤儿化继续持 state 锁、按 state_save_interval 周期落盘。清孤儿走 `commands run dev.clone-kill -- --match dev_run --yes`(clone 域归属定点); taskkill 一律禁(AGENTS 红线), port-kill 管不到非监听残留。
> 触发: dev.run, dry-run, 干跑探针, 探针残留, 孤儿进程, 杀包装不死子, state 锁, 周期落盘, clone-kill, 停后台任务, TaskStop, 会话收尾, 探针为什么还活着

## 形态(2026-11-22, dev.run 干跑探针双残留)

- 后台跑 `commands run dev.run -- config.yml --dry-run` 做探针, 之后停掉后台任务/会话收尾 -- 只杀掉 bash/uv 包装链, venv python 子进程孤儿化(父控制台消亡)继续跑守护循环: 持 config 所指 state 的锁、周期落盘、对 qB 零变更但对 state 持续写入。另一会话取证 pid 15624/36312 即此形态(cmdline 逐字核实为本 clone .venv 的 dev_run.py config.yml --dry-run)。
- 取证结论: **残留不是挂死, 是 by-design** -- `src/auto_qb/cli.py` 的 --dry-run 语义就是守护循环; 「探针为什么不退」的正确答案是「它本来就不该退」。这正是 port_kill docstring 记录的「杀包装不死子」形态(pitfalls/testing/harness-save-flow.md)在 dev.run 上的再现。

## 判别

- 「探针为什么还活着」第一解读是「它在跑守护循环」, 不是「卡死了」; cmdline(`--dry-run` 在) + state 落盘节奏即可定性。
- 本 clone 活进程清单(只读取证): `Get-CimInstance Win32_Process -Filter "CommandLine LIKE '%<clone 根>%'"`; 归属判据单点 = port_kill.in_clone_domain(cmdline, REPO_ROOT)。
- 探针多数不监听端口(webui/HR 口被占时静默不绑), **port-kill 管不到**, 别往端口方向找。

## 处置

- 清孤儿: `commands run dev.clone-kill -- --match dev_run --yes` -- 默认只列; 杀必须 --match + --yes 双闸; 目标后代连坐但逐个过闸; 自身与祖先链硬排除。工具面 scripts/clone_kill.py, 判据 import 复用 port_kill 单点(in_clone_domain/_kill_pid, 判据与实杀都不两处演化)。
- 任务管理器手动杀仍是合法兜底(用户亲手操作不受 AI 红线约束), 但 AI 代理自己一律不碰 taskkill。
- 预防面(2026-11-22 grilling 拍板 D9): 只记档不改产品 -- 父亡自毁 / --dry-run 语义改造都是产品行为变更, 想做另立项。

## 守阵

- tests/test_clone_kill_script.py(测试计划见其 docstring): 判据 import 单点 / 候选矩阵 / 排除集 / 后代闸 / 双闸接线 / 双平台扫描; taskkill/SIGKILL 全程不真执行。
- port_kill 侧既有守阵不变(test_legacy_review4_scripts.py)。

**Refs:** memory-bank/pitfalls/testing/harness-save-flow.md, memory-bank/tasks/26-11-23-dev-clone-kill-tool.md

- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
