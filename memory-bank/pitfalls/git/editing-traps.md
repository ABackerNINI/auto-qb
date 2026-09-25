# 编辑与工具陷阱 (git / 文本)

> 摘要: 工具 shell 里改文件的多类静默事故 —— 编辑器挂死、行尾被归一、编码写坏、多行替换错位、同文件多次 Edit、edit 工具 CRLF 匹配、PowerShell 引号剥除 (旧"stash 毁库"条已随拦截层修复解除)。
> 触发: git stash, GIT_EDITOR, 改文件, 行尾, CRLF, LF, 编码, 乱码, 多行替换, Edit, junction, oldText, python -c, 引号

### 工具 shell 里 `git rebase --continue` / `commit --amend` / `merge` 一律带 `GIT_EDITOR=true`

- **触发**: 跑上面这几条命令。
- **判别**: 本机 `core.editor` 是 `code --wait`, 无可交互窗口 ⇒ **永久等待**(实测挂 6 分钟)。
- **处置**: 命令前加 `GIT_EDITOR=true`(必要时再加 `GIT_SEQUENCE_EDITOR=:`); 这是编辑器挂死问题,
  与已解除的 rebase/merge/stash 毁库禁令无关 —— 禁令解除后这些命令可跑, 但本条仍适用。

### 对照旧代码: `git archive` + `PYTHONPATH` 方案 (stash 已恢复可用, 本方案免改工作区)

- **触发**: 想"改动前 vs 改动后"对照, 又不想改工作区。
- **判别**: 旧版写"不要用 `git stash`", 理由是拦截层会顺着 stash 写入删 `.git/objects` —— 该问题
  2026-09-25 已修复, stash 禁令解除; 但"对照旧代码不动工作区"这个需求本身, 下面的方案更直接。
- **处置**: 用 `git archive` + `PYTHONPATH` 取旧代码:
  ```bash
  git archive HEAD src | tar -x -C .workbuddy-ai/tmp/aqb_old
  PYTHONPATH=".../aqb_old/src" uv run python -c "import auto_qb.qbmanager as m; print(m.__file__)"   # 先确认加载的是旧代码
  ```
  ❗**必须先验证 `PYTHONPATH` 真的覆盖了 editable install**, 否则是拿新代码比新代码。

### 用 Python 文本模式改文件会把整份 CRLF 悄悄改成 LF

- **触发**: 用 Python 读写 html / css / md。
- **判别**: 本仓库行尾**不统一**(index.html 等是 CRLF, style.css / views.css 是 LF);
  `io.open(p).read()` 走通用换行把 `\r\n` 读成 `\n`, 再 `write(newline="")` 落盘就只剩 LF ——
  `git diff` **仍只显示你改的那几行**(索引存 LF, 归一化后看不出来), 但字节层面整份文件的行尾都被改了。
- **处置**: 改 html/css/md 一律**按字节读写**(`open(p,"rb")` + `bytes.replace`), 或写回时补
  `.replace(b"\n", b"\r\n")`; 复核用 `b.count(b"\r\n")` ——
  git bash 里 `grep -c $'\r' file` 会给**假结果**(实测计数等于总行数), 别信。

### `core.autocrlf=true` 下编辑会归一整文件行尾

- **触发**: 在 `core.autocrlf=true` 的仓库里编辑文件。
- **判别**: 单文件 diff 从 23 行变 1431 行 —— **不是损坏**, 是行尾归一。
- **处置**: 提交信息里写明"行尾归一"; 想避免就用上面的按字节读写。

### 合并冲突处理不要把 UTF-8 当 GBK 写入

- **触发**: 手工合并冲突 / 用脚本重写文件。
- **判别**: 文档乱码且**不可逆**(曾藏 3 天); 特征是**私用区字符与 U+FFFD**。
  检测: 统计 GBK 误解码高频字密度。
- **处置**: **恢复从 git 取原文**(逐父 `git show <parent>:<file>` 比对取唯一来源那一侧), **不要反解**;
  写回保持 CRLF 否则整文件 diff 炸开; 顺手做一次全文件链接存在性扫描。
  **验证编码一律用 Python 显式 UTF-8 读**(`open(p,"rb").read().decode("utf-8")` 不抛错且 `"\ufffd" not in text`)——
  Git Bash 的 `sed/cut` 管道对**完好的** UTF-8 也会打印乱码, 不能据此下结论。

### 多行文本替换在"多处同型块"上会错位吞行

- **触发**: 用 oldString/newString 做多行替换, 而目标在多处出现。
- **判别**: 工具**仍返回成功**, 产出 `</p>note warn">` 这类**语法垃圾**。
- **处置**: oldString 扩到含前后**不重复**的上下文; 改完做**标签配对计数**;
  已损坏就 `git checkout -- <file>` 回滚重做, **不要就地缝补**。

### 同一文件在一条消息里多次 Edit 会互相覆盖

### Markdown 表格会被"自动格式化器"改坏

- **触发**: 改文档后 `git diff` 比预期**大一个量级**(2026-09-21 实测 `docs/sim-client-test-howto.md`)。
- **判别**: 有个格式化器在提交后又跑了, 把表格做了列对齐 + 加硬换行(尾随双空格), 顺带**改坏两处**:
  ①单元格里的 `<br>` 被换成真换行 ⇒ **表格行被劈成两行**(markdown 表格不允许单元格内换行);
  ②`` `recorded`\|`p50` `` 这类**转义竖线被还原成 `|`** ⇒ 平白多出几列。
  (这次 32860 vs 25027 字节, 但 `git diff -w` 只剩 19/9。)
- **处置**: **用 `git diff -w` 分辨"有没有真的动到文字"**, 再决定是留还是还原。
  **表格里要换行只能用 `<br>`, 要写竖线必须 `\|`。**

### Bash heredoc 往 Python 里写"反斜杠转义"会被路径归一化层改成正斜杠

- **触发**: 用 heredoc 给 Python 写多行内容。
- **判别**: 写 `\n` 进文件, 落盘可能变成 `/n` 或 `//n`, 生成物里就出现**字面量** `\n`(本工具环境实测)。
- **处置**: **规避: 多行内容用三引号 + 真实换行**(`f"""..."""`), 完全不用转义序列;
  或用编辑工具逐行改, **别走 heredoc**。

- **触发**: 一条消息里对同一文件发多个 Edit。
- **判别**: 工具逐个报成功, 实际**只有一部分落盘**。
- **处置**: 改同一文件时**逐条改、改完 grep 复核**。
  ⚠ 删 junction 用 Python `os.rmdir()` —— 别用 `cmd /c rmdir`: 本会话 Git Bash 里 `cmd //c` 会被路径转换坑掉
  且**可能静默不执行**。

### edit 工具的 oldText 在 CRLF 文件上匹配失败, 且报错与落盘可能不一致

- **触发**: 对 git checkout 出来的 CRLF 文件(memory-bank 大部分 md/html)用 edit 工具, oldText 含换行(默认 LF)。
- **判别**: 返回 `Could not find the exact text ... (must match exactly)`; 更阴的是**报错后落盘内容与 newText 不完全一致**
  (2026-09-22 实测 baseline-history.md: 多段追加后连报两次匹配失败, 最终文件内容与两次提供文本都对不上)。
- **处置**: 对 CRLF 文件**优先用单行锚**(避开跨行匹配); 改完**必须 grep 复核实际落盘内容**, 别信返回消息;
  多段插入可走 PowerShell `Add-Content`/按字节读写(见上文条目)。

### PowerShell 里 `python -c "..."` 的内层双引号会被剥掉

- **触发**: 在工具 shell(PowerShell)里写 `python -c "print(f"{x}")"` 这类内层双引号代码。
- **判别**: Python 报 SyntaxError 且源码片段里引号消失(如 `rsrc/auto_qb/...` —— `r"..."` 的引号没了), 或**静默无输出退出 0**。
- **处置**: 单行短代码改用**读文件/写临时文件**绕开(或单引号包外层 + 内层全用双引号且不再嵌套);
  更稳的做法是把探查脚本写到 `.openclaw/tmp/` 下再 `python <file>`; 多行逻辑禁止硬塞 `python -c`。
