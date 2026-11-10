# Git Bash 会把参数里的 POSIX 绝对路径段做改写(docker 容器路径 / 本地命令 / grep 模式)

> 摘要: 工具 shell 是 Git Bash, 发给 native 程序的**参数里凡是含 `/xxx` 绝对路径段**(以 `/` 开头的参数、或参数中段嵌着 `/xxx`, 如 grep 模式 `</code>`)都会被 MSYS 按"POSIX 绝对路径"改写成 Git 安装根形态(`D:/Program Files/Git/xxx`) —— 命令能跑、退出码正常、零报错, 效果是静默污染: 容器里报「找不到文件」, grep **静默 0 命中**(不是没匹配上, 是模式根本变了)。
> 触发: docker exec, docker run, docker compose run, 容器路径, 找不到文件, 配置文件读取失败, Git Bash, 路径转换, MSYS, web.token, token 文件, 命令参数被改写, 标题斜杠开头, kb.new title, Program Files/Git 前缀, grep 模式, 斜杠, 静默零命中, 闭合标签, 正则含路径, ugrep

**Refs:** memory-bank/tasks/26-11-11-backend-relocate-bt-backup-probe.md

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

## 复发

- **复发**: 1(2026-11-08, R4 webui-py 收尾轮, 非 docker 场景)—— **坑面扩到任意本地命令参数**: `commands run kb.new issue --title "/api/torrents/add ..."` 的标题以 `/api/` 开头, Git Bash 对**本地 Windows 程序**的参数同样做 POSIX→Windows 转换, 标题落盘成 `C:/Program Files/Git/api/torrents/add ...`(3 个新 issue 的 title/meta/h1/lede 共 7 处), 命令照常成功零报错 —— 纯静默污染。按判别字样(`Program Files/Git/` 前缀)定位, 原位改回 `/api/` 后重跑 `kb.index` 恢复。**为什么没命中**: 本档标题与触发词全钉在 docker 面, 非 docker 的本地命令参数没进路由。教训: Git Bash 下**任何**本地命令的参数以 `/` 起头都会中招(不只 docker), 长文本参数避免以 `/` 起头, 或对该命令前缀 `MSYS_NO_PATHCONV=1`。
- **复发**: 2(2026-11-11, BT_backup 计划提交收尾轮)—— **坑面扩到参数中段的绝对路径段**(不以 `/` 开头也中招): grep 模式 `</code>` 被改写成 `<D:/Program Files/Git/code>`(`python -c "print(sys.argv)" '</code>'` 直视实形), `grep -o '</code>'` 静默 0 命中, 差点据此误判「全文件闭合标签缺失」—— 真相是文件只有 1 个未闭合标签, 由 HTML 闸门(vNu)抓出。实测机制: 转换只动**绝对路径段**(以 `/` 起的段), 相对段 `a/b` 原样放行(grep `a/b` 正常命中); 本仓 grep 实为 ugrep 7.8.4 shim。**判别**: ①python `sys.argv` 直看参数实形; ②同模式把 `/` 写成 `\/` 对照命中数; ③awk gsub / python str.count 命中而 grep = 0。**处置**: ①模式里斜杠写 `\/`(实测命中正常, ugrep 把 `\/` 当字面 `/`); ②或改用 python/awk; ③`-F` 不救(照样被改写); ④`MSYS_NO_PATHCONV=1` 前缀: 对**仓库文件**参数实测有效(对照命中 187, 多形态复核); 但 `$( )` 子壳 + `/tmp/...` 文件参数组合下 shim 报 `-t TYPES` 假错(可复现: `$(MSYS_NO_PATHCONV=1 grep -c '</code>' /tmp/x.txt 2>&1)`, 机制未钉) —— 临时路径场景弃前缀法, 直接 `\/` 或 python。**为什么没命中**: 复发 1 把坑面钉在「参数以 `/` 开头」, 中段嵌 `/xxx` 的形态(HTML 闭合标签、正则)没进路由。教训: 含 `/` 的文本参数先想 MSYS, 判「不存在」类结论必须有非 grep 旁证。
