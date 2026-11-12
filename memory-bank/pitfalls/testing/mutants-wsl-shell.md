# WSL 登录壳 zsh 的 `$PWD` / `$(...)` 失真 —— 容器形态(docker exec bash)不适用

> 摘要: (2026-11-12 起容器口径) `mutants.*` 后端已迁 `docker exec auto-qb-testbed bash -c`(计划 26-11-12-0152 S4), 容器 bash **不存在本坑** —— 脚本经 argv 直传容器 bash, 无登录壳、无 zsh, `cd` 与 `$()`/`$PWD` 是同进程常规语义; `mutants.status` 脚本已回归常规 `$(...)` 形态。本坑只剩 **WSL 形态的历史价值**(见下「历史留痕」), 仅当再写 WSL 侧脚本(兜底/迁移/一次性探针)时才需提防。
> 触发: WSL, wsl.exe, bash -lc, zsh, 命令替换, $(), $PWD, cd 不生效, 相对路径读错, mutants.status, mutmut=no, 镜像目录, 路径漂移, docker exec, bash, 不适用, 容器

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

### 容器形态(2026-11-12 起): 不适用

- `mutants.py` 的 `_exec` 走 `docker exec <容器> bash -c <script>`, 脚本经 **argv** 传入(不经宿主壳引号层), 容器内是普通 bash: `cd X && echo "$(pwd)"` 两者一致, 不存在「$() 报启动目录」。
- `mutants.status` 因此从 WSL 时代的 `cd X && <直接命令>` 特化形态回归常规 `$(...)` 形态(`_status_script` / `_status_all_script`, 见脚本头注)。
- 再见到 `mutmut=no` 时, 先查的是**版本不匹配**(`_ensure_tool` 按版本核对, 镜像里躺旧版 mutmut 3.8.0 + pytest 9.2 会在 stats 收集崩), 不再是壳层 cwd 失真。

### 历史留痕(WSL 形态, 2026-10-08, config 变异审计首轮踩到; 2026-11-12 随 S4 容器迁移退役)

- **触发**: 在 WSL 里跑「先 `cd` 到镜像/工作目录, 再用 `$(...)` 取相对路径」的脚本(如 `mutants.status` 的 `echo mutmut=$(test -x .venv/bin/mutmut && echo yes || echo no)`)。触发条件: 本机 WSL 登录壳实为 zsh(`$0` = `/usr/bin/zsh`)。

- **判别**: `wsl.exe -d <distro> -- bash -lc '<script>'` 下逐条实测(2026-10-08 07:57):

  | 脚本 | 输出 | 说明 |
  |---|---|---|
  | `cd "$HOME/auto-qb-mut"; pwd` | `/home/abacker/auto-qb-mut` | 真实 cwd **正确** |
  | `cd "$HOME/auto-qb-mut"; echo "$(pwd)"` | `/mnt/d/Projects/auto-qb-clone4` | `$()` 报**启动目录** |
  | `cd "$HOME/auto-qb-mut"; echo "$PWD"` | `/mnt/d/Projects/auto-qb-clone4` | `$PWD` 变量**没被 cd 更新** |
  | `cd X && echo "$(pwd)" && pwd` | 前者错 / 后者对 | 同一条脚本里两者不一致 |

  只要脚本里出现**相对路径 + 命令替换**, 结果就按「启动目录」算 —— `mutants.status` 因此恒输出 `mutmut=no`, 而 `cd "$HOME/auto-qb-mut" && ls -d .venv/bin/mutmut` 是找得到的。**不受影响**的写法: `cd X && <命令>`(不带 `$()`)全程正确, 所以 `mutants.run` 的六步编排能正常跑。

- **处置**(WSL 形态): ①在 WSL 里写脚本**不要**用 `$(...)` 去解析相对路径 —— 用 `cd X && cmd` 直连, 或改用绝对路径(`$HOME/...`)参与 `$()`; ②见到 `mutants.status` 报 `mutmut=no` **不要**据此重装工具, 先按上表核实真实 cwd; ③排障时以 `cd X && <cmd>` 的**直接输出**为准, 别信 `$()` 包一层的结果。

**复发**: 1 —— 2026-10-08 config 变异审计首轮(排障耗时约 30min: 一度怀疑镜像/工具装错)。**工具侧已修(2026-10-08 09:52)**: `mutants.py` 的 `cmd_status` 四条回显改 `cd {mq} && <直接命令>` 形态(issue `26-10-08-0758-bug-mutants-status-wsl`, 已 `Done`); 2026-11-12 S4 迁容器后失真源消失, status 脚本回归 `$(...)` 常规形态。
