# 本工具 shell 的环境变量陷阱(拼 PATH / 裸 `python`)

> 摘要: 本工具的终端是**长驻会话**(环境变量跨命令保留) —— 为拿到机器级 PATH 里的工具而反复执行 `$env:PATH = $env:PATH + ';' + 机器PATH` 会把它撑到 240+ 项, **子进程的环境块被截断** ⇒ `cmd.exe` 里连 `python` 都报「不是内部或外部命令」, 而 `where.exe python` 仍找得到; 症状看着像「命令引擎坏了」。判据: ①裸名解析不到时先数 PATH 项数 ②拼之前先按项去重 ③本项目自己的命令一律走 `commands run <task>`。
> 触发: PATH, 环境变量, python 不是内部或外部命令, not recognized, node 找不到, 命令引擎, kb.check 失败, 子进程环境块, 长驻终端, 沙箱, commands 装了没用, wrapper 不识别, ~/bin, install_wrapper, Git Bash 与 PowerShell 判据相反

## 现象与判别(2026-09-25 实测)

- **触发**: 本机 node 在**机器级** PATH 里, 而长驻会话拿的是旧 PATH ⇒ 为了跑 `node --check` 在会话里
  `$env:PATH = $env:PATH + ';' + [Environment]::GetEnvironmentVariable('Path','Machine')`; 后面又执行了同一条。
- **判别**: `commands run kb.check` 报 `[FAIL] rc!=0` + `'python' is not recognized as an internal or external command`;
  同时 `Get-Command python` / `where.exe python` **都能找到** —— 这不是"没装 Python", 而是**子进程拿到的 PATH 被截断**
  (Windows 环境块有上限, 项一多就丢尾巴)。取证一句话: `($env:PATH -split ';').Count` —— 实测被撑到 **246**,
  归一化后是 **33**。
- **处置**: 会话内按项去重重置一次即可(不必重启 IDE):

  ```powershell
  $env:PATH = ((([Environment]::GetEnvironmentVariable('Path','Machine') + ';' +
                 [Environment]::GetEnvironmentVariable('Path','User')) -split ';' |
                 Where-Object { $_ } | Select-Object -Unique) -join ';')
  ```

  之后 `cmd /c "python -V"` 与 `commands run kb.check` 立刻恢复。

## 口径

- **别在同一会话里反复拼 PATH**: 需要某个工具先 `Get-Command <tool>` 确认; 真不行**一次**拼, 且拼之前去重。
- **裸名(`python` / `node`)能不能解析, 要用 `cmd /c` 复核**: PowerShell 的解析与 `cmd.exe`(**命令引擎跑任务用的那个**)
  不是一回事, 只看 PowerShell 会误判"环境是好的"。
- 本项目自己的命令一律 `commands run <task>`(引擎内部走 `uv run python`), **不要手敲 `python xxx.py`** ——
  手敲时用的可能不是 `.venv` 里的解释器(本机实测裸 `python` 指向 msys 的 3.14)。

## 同类第二坑: wrapper 装进了 `~/bin`, 而 `~/bin` 不在 Windows PATH(2026-09-28 实测)

- **触发**: 用户报「我明明装了 `commands`, 敲 `commands` 还是 not recognized」。
- **判别**: `Get-Command commands -All` **解析不到**, 而 `C:\Users\11059\bin\commands.cmd` **确实存在** ——
  即「装了」为真、「能用」为假。根因在安装脚本的落点判据: PATH 那份只在 `~/bin` / `~/.local/bin`
  **已在 PATH 上**时才写, 否则打印「都不在 PATH 上 —— 跳过」。而 **Git Bash / MSYS 默认把 `~/bin` 放进 PATH**,
  Windows 用户级 PATH 里却从来没有 —— 同一个生成器在两种 shell 下结论相反: Git Bash 下「在 PATH 上, 写进去」,
  PowerShell 下「不在 PATH 上, 跳过」; 而先前已写进去的那份, 因目录不在 PATH 里永远找不到。
  另一条并列原因: 仓库根那份 wrapper **PowerShell 不搜 cwd**, 必须 `./commands`(只有 cmd.exe 搜 cwd) —— 装成
  「只装仓库根」也照样 not recognized。
- **处置**: 把 `~/bin` 加进**用户级** PATH(先判重, 勿重复追加)后重跑安装脚本:

  ```powershell
  $bin = "$env:USERPROFILE\bin"
  New-Item -ItemType Directory -Force -Path $bin | Out-Null
  $items = @([Environment]::GetEnvironmentVariable('Path','User') -split ';' | Where-Object { $_ })
  if ($items -notcontains $bin) {
    [Environment]::SetEnvironmentVariable('Path', (($items + $bin) -join ';'), 'User')
  }
  ```

  ❗安装脚本读的是**当前进程的 `PATH`** ⇒ 已开着的会话要先手拼一次 `$env:PATH="$env:PATH;$bin"` 再跑, 否则仍判「跳过」。
  ❗改完环境变量**必须新开终端 / 重启 VS Code** 才生效 —— 旧终端拿的是旧环境块, 不会回灌。
- **口径**: 报「命令 not recognized」按此序判: ①`Get-Command <名> -All` 看解析 ②按绝对路径看文件在不在
  (在 ⇒ 目录没进 PATH; 不在 ⇒ 真没装) ③再数 PATH 项数, 排除上面那条环境块截断的坑。
