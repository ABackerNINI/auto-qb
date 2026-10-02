# 26-10-02-config-eol-unify-lf — 行尾统一 LF(仓库设防 + 全局 input)

**Status:** In Progress
**Added:** 2026-10-02
**Updated:** 2026-10-02
**Topics:** config-eol-unify-lf
**Summary:** CRLF 反复引发事故(编辑工具匹配失败 / `\r\r\n` 双重转换 / 行尾幽灵 M 挡同步 / cap 计数虚高), 根因 = 系统级 core.autocrlf=true 且仓库无 .gitattributes。层1(.gitattributes `* text=auto eol=lf` + .editorconfig)与层2(renormalize 归一 LICENSE、memory-bank/pitfalls.md 两个 CRLF blob, --ignore-cr-at-eol 全空=纯行尾)已落地; 全局 core.autocrlf 改 input(用户级压过系统级 true)。层3(存量工作区约 2189 文件一次性转 LF + 各 clone 刷新)用户指示暂缓。

## 原始请求

用户: 目前的 crlf 换行多次引起了问题, 想要统一改为 lf, 分析怎么改。分析轮(只读)交付四层方案后, 用户拍板: 先完成第 1/2/4 层, 其它剩余工作(层3)暂时不转, 同时更改全局 git 配置默认使用 lf。

## 思考过程与决策

- 诊断(`git ls-files --eol` 全量普查, 2316 跟踪文件): 索引侧仅 2 个 CRLF blob(LICENSE、memory-bank/pitfalls.md)+ 1 个 mixed(tasks/26-09-28-commands-shipflow-output-contract.md); 工作区 2189 个 CRLF —— 病灶在检出侧(autocrlf=true 的检出产物), 不在仓库内容。
- D1: 行尾决定权收回仓库 —— `.gitattributes` 单点随仓库走到所有 clone, 不依赖各机器全局配置; blob 侧结构性防复发(提交必归一 LF)。
- D2: `.cmd`/`.bat` 显式 CRLF(cmd 对 LF 拆错行, `test_commands_engine.py::test_wrapper_cmd_written_with_crlf_no_bom` 已固化); png/ico/pdf/mp4 显式 binary 防 text=auto 误判。
- D3: 全局 `core.autocrlf=input` 而非 false —— 提交侧仍归一 CRLF 到 LF, 兜住没有 .gitattributes 的其它仓库; 用户级(`C:/Users/11059/.gitconfig`)压过系统级 true。
- D4: 层3 工作区转换推荐字节级 Python 脚本(符合坑档按字节读写纪律, 不动 git 状态), 备选 `git rm --cached -r . && git reset --hard`(需净树 + `.git` 备份)。
- 测试无依赖: 3 个含 `\r\n` 的测试分别是 .cmd 生成器断言 / HTTP 协议字节 / content-disposition 清洗, 均不依赖仓库文件为 CRLF; test_yamls 6 个 fixture blob 已是 LF。

## 实现计划

- 层1: `.gitattributes` + `.editorconfig`(已落地)
- 层2: `git add --renormalize .` + 经 ship.commit 入库(已暂存, 随本档案一并提交)
- 层4: pitfalls/git/editing-traps.md 与 sync-pull.md 行尾条目标注「已设防 / 层3 完成前仍适用」(已落地)
- 层3(暂缓): 本 clone 存量工作区约 2189 文件字节级转 LF + 其它 clone 各自 sync 后跑同一脚本; config.yml 为红线默认排除, 是否纳入由用户拍板

## 子任务状态表

| 子任务 | 状态 |
|---|---|
| 层1 .gitattributes + .editorconfig | Done |
| 层2 renormalize + 入库 | In Progress(暂存完毕, 随本档案 ship.commit) |
| 层4 pitfalls 回写 | Done |
| 全局 core.autocrlf=input | Done |
| 层3 本 clone 工作区转 LF | Open(用户指示暂缓) |
| 层3 其它 clone 刷新 | Open(跨仓库红线, 各 clone 会话自行执行) |

## 进度日志

- 2026-10-02: 分析轮(只读)产出四层方案; 执行轮落地层 1/2/4 + 全局配置, 层3 暂缓。
