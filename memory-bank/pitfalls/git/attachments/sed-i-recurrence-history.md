## `sed -i` 行尾坑的复发记录

- **复发 +1 (2026-10-07)**: 触发换成 **Edit 工具** —— 一次普通插入把
  `.commands/my-commit-flow/references/config.md` 整份从 `LF=69 / CRLF=0` 写成 `CRLF=81 / LF=0`,
  而 `git diff --numstat` 仍是干净的 `12 0`(clean filter 归一了), **只有 `git status` 末尾那行
  `warning: … CRLF will be replaced by LF` 露了马脚**。为什么没命中: 本条旧文案把 Edit 写成
  "保留原行尾"的安全选项, 于是改完没做按字节复核 —— 判据必须落在**改完必查**上, 不能落在"用哪个工具"上。
  定式(已并入处置): 改完 md / 交付件后跑一次 `git status`, 见到 CRLF 警告就按字节归一。
- **复发 +1 (2026-10-07, 第二次)**: 这次落在 KB 交付面 —— S4b 用 Edit 工具改
  `memory-bank/conventions/code-style.md`, 整份 `LF=… / CRLF=0` 写成全 CRLF(git diff 依旧只显示
  改动行)。为什么没命中: 委派实施时未把本坑档列入子智能体必读清单, 编辑前没读、改完也没跑
  「git status 看 CRLF 警告」定式。处置照旧: 按字节归一回 LF
  (`write_bytes(read_bytes().replace(b"\r\n", b"\n"))`)。

- **复发 +1 (2026-10-11)**: 触发又换成 **Edit 工具改前端 JS** —— 一次普通方法体替换把
  `shared/sort.js` 整份从 `LF=77 / CRLF=0` 写成 `CRLF=77 / LF=0`(同一批改动的 `app.js` /
  `columns.js` 仍是 LF ⇒ **"哪个文件会被写坏"不可预测**, 不能按文件挑)。暴露方式与上次同款:
  `git status` 末尾的 `warning: … CRLF will be replaced by LF`。为什么没命中: 本轮是前端重构,
  路由只读了 `pitfalls/web-ui/`, 行尾类条目在 `pitfalls/git/` 没被翻到 —— 定式应固化为
  **"改完任何文本文件就跑一次 `git status` 扫 CRLF 警告"**, 与改的是哪个目录无关。处置照旧按字节归一回 LF
  (`write_bytes(read_bytes().replace(b"\r\n", b"\n"))`)。

- **复发 +1 (2026-10-16)**: 触发换成 **Edit 工具改 KB 文档** —— 计划 26-10-15-2357 S3/S4 收尾时用 Edit
  往 `pitfalls/testing/node-guards-silent-skip.md` 追加一节, 整份从 `LF=28 / CRLF=0` 写成
  `CRLF=44 / LF=0`(同轮用 Edit 改的 `options.js` / `options.html` / 两份 activeContext / 档案 / 新基线切片
  都仍是 LF ⇒ 又一次印证"哪个文件会被写坏不可预测")。暴露方式与前几次同款: `git status` / `git diff`
  末尾的 `warning: … CRLF will be replaced by LF`。
  **为什么没命中**: ①路由只走到**顶层** `pitfalls/_index.md` —— 它的「主题」表是空的(`(暂无)`), 没有指向
  `git/editing-traps.md` 的细路由; 而 git 类行的判据被读成「**跑 git 命令前**必读」, 本轮动作是"编辑文档"
  不在该判据内, 于是没进 `pitfalls/git/_index.md`(触发词「行尾」就明写在顶层 git 行里, 没被识别成
  "编辑纯文本也适用"); ②更直接的是**警告行看到了却当成无害噪声** —— 定式要求的是"见到即按字节归一",
  本轮只做到"见到", 直到收尾才发现。处置照旧按字节归一回 LF
  (`write_bytes(read_bytes().replace(b"\r\n", b"\n"))`), 并逐文件核 CRLF/LF 计数。
  **定式强化**: 改完任何文本文件, 收尾必跑一次
  `python -c "…count(b'\r\n')…"` 逐文件复核(不靠肉眼扫 git 警告), 见到警告行**立即**归一, 不推迟到收尾。

