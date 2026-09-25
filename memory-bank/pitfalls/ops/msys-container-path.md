# Git Bash 会把 docker 的容器内路径参数也做 POSIX→Windows 转换

> 摘要: 工具 shell 是 Git Bash, `docker exec / docker run / docker compose run` 的**容器内**路径参数(如 `/data/web.token`、`/config/x.yml`)会被 MSYS 按"POSIX 绝对路径"自动改写成 Windows 形态(`D:/Program Files/Git/data/web.token`) —— 命令能跑、退出码正常, 但容器里报「找不到文件/配置文件读取失败」, 看着像容器坏了其实是参数在进容器前就被改了。
> 触发: docker exec, docker run, docker compose run, 容器路径, 找不到文件, 配置文件读取失败, Git Bash, 路径转换, MSYS, web.token, token 文件

## 现象与判别

- **触发**: Git Bash 里执行带容器内绝对路径参数的 docker 命令。2026-09-26 实测两例:
  ①`docker exec auto-qb cat /data/web.token` → 容器内报 `cat: 'D:/Program Files/Git/data/web.token': No such file or directory`;
  ②`docker compose run --rm auto-qb /config/fail-fast.yml` → 程序报 `配置错误: 配置文件读取失败: [Errno 2] No such file or directory: 'D:/Program Files/Git/config/fail-fast.yml'`(这条还伪装成配置校验错误, 退出码 1, 极易误判成"fail-fast 生效了")。
- **判别**: 报错信息里出现 `D:/Program Files/Git/` 前缀(= Git Bash 的安装根)即是本坑 ——
  那是 MSYS 把 `/xxx` 解析为"Git 安装目录下的 xxx"。**宿主机路径**(bind mount 源, 如 `-v D:\x:/config`)不受影响,
  只有**容器内**的目标路径参数中招。
- **同类已有记录**: `pitfalls/git/editing-traps.md` 记过 `cmd //c` 的路径转换坑; 库内此前**没有** docker 参数这条 —— 本条即补位。

## 处置

- **前缀 `MSYS_NO_PATHCONV=1`** 禁用该条命令的路径转换(实测有效):
  ```bash
  MSYS_NO_PATHCONV=1 docker exec auto-qb cat /data/web.token
  MSYS_NO_PATHCONV=1 docker compose run --rm -T auto-qb /config/xxx.yml
  ```
- 或把参数写成**双斜杠** `//data/web.token`(MSYS 转换器跳过双斜杠开头), 但可读性差, 首选前缀法。
- `docker compose run` 的**服务名后**命令参数是重灾区(每个都是容器内路径); `-v` 挂载源在 Windows 下用
  `cygpath -w` 转成 `D:\...` 形态再拼(见 `deployment.md` §8 备份示例的 alpine tar 写法)。
- 关联部署文档: [docs/deployment.md](../../../docs/deployment.md) §13 排障速查最后两行。
