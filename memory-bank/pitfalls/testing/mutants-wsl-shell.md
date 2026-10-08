# WSL 里 `cd` 改了真实 cwd, 但 `$PWD` / `$(...)` 仍报启动目录

> 摘要: 本机 WSL(`Ubuntu-26.04`, 登录壳实为 zsh 5.9)里 `cd X && cmd` 会真的在 X 下执行, 但 **`$PWD` 与 `$(...)` 命令替换仍报 WSL 的启动目录**(即调用方的 Windows cwd 映射成的 `/mnt/d/...`)。凡「先 cd 再用 `$(...)` 取相对路径 / cwd」的脚本都会**静默读到错目录**, 不报错、看着像正常。`mutants.status` 因此在本机恒报 `mutmut=no`(实际装了), `mutants.run` 不受影响(它全程用 `cd X && cmd` 直连)。
> 触发: WSL, wsl.exe, bash -lc, zsh, 命令替换, $(), $PWD, cd 不生效, 相对路径读错, mutants.status, mutmut=no, 镜像目录, 路径漂移

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

### 现象与判别 (2026-10-08, config 变异审计首轮踩到)

- **触发**: 在 WSL 里跑「先 `cd` 到镜像/工作目录, 再用 `$(...)` 取相对路径」的脚本(如 `mutants.status` 的 `echo mutmut=$(test -x .venv/bin/mutmut && echo yes || echo no)`)。触发条件: 本机 WSL 登录壳实为 zsh(`$0` = `/usr/bin/zsh`)。

- **判别**: `wsl.exe -d <distro> -- bash -lc '<script>'` 下逐条实测(2026-10-08 07:57):

  | 脚本 | 输出 | 说明 |
  |---|---|---|
  | `cd "$HOME/auto-qb-mut"; pwd` | `/home/abacker/auto-qb-mut` | 真实 cwd **正确** |
  | `cd "$HOME/auto-qb-mut"; echo "$(pwd)"` | `/mnt/d/Projects/auto-qb-clone4` | `$()` 报**启动目录** |
  | `cd "$HOME/auto-qb-mut"; echo "$PWD"` | `/mnt/d/Projects/auto-qb-clone4` | `$PWD` 变量**没被 cd 更新** |
  | `cd X && echo "$(pwd)" && pwd` | 前者错 / 后者对 | 同一条脚本里两者不一致 |

  只要脚本里出现**相对路径 + 命令替换**, 结果就按「启动目录」算 —— `mutants.status` 因此恒输出 `mutmut=no`, 而 `cd "$HOME/auto-qb-mut" && ls -d .venv/bin/mutmut` 是找得到的。**不受影响**的写法: `cd X && <命令>`(不带 `$()`)全程正确, 所以 `mutants.run` 的六步编排能正常跑。

- **处置**: ①在 WSL 里写脚本**不要**用 `$(...)` 去解析相对路径 —— 用 `cd X && cmd` 直连, 或改用绝对路径(`$HOME/...`)参与 `$()`; ②见到 `mutants.status` 报 `mutmut=no` **不要**据此重装工具, 先按上表核实真实 cwd; ③排障时以 `cd X && <cmd>` 的**直接输出**为准, 别信 `$()` 包一层的结果。

**复发**: 1 —— 2026-10-08 config 变异审计首轮(排障耗时约 30min: 一度怀疑镜像/工具装错)。工具侧未修(属计划外, 已入池 `26-10-08-0758-bug-mutants-status-wsl`)。
