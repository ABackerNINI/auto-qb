# 编辑与工具陷阱 (git / 文本)

> 摘要: 工具 shell 里改文件的多类静默事故 —— 编辑器挂死、行尾被归一(`sed -i` 把 LF 写成 CRLF, git 侧看不见、cap 侧多算)、文本模式写回双重换行(`\r\r\n`)、编码写坏、多行替换错位、同文件多次 Edit、edit 工具 CRLF 匹配、PowerShell 引号剥除 (旧"stash 毁库"条已随拦截层修复解除)。2026-10-02 起仓库 .gitattributes 统一 LF, 行尾类条目适用范围收窄(见首节)。
> 触发: git stash, GIT_EDITOR, 改文件, 行尾, CRLF, LF, 双重换行, write_text, 编码, 乱码, 多行替换, Edit, junction, oldText, python -c, 引号, 控制字符, 转义被吃, Windows 路径, 反斜杠, 幽灵 M, stat 缓存, sed -i, 机械替换, 凭空多出的债务

### 2026-10-02 起仓库统一 LF: 行尾类条目适用范围收窄

- **变更**: 仓库根新增 `.gitattributes`(`* text=auto eol=lf`)+ 全局 `core.autocrlf` 改 `input` —— blob 侧提交必归一 LF, 新检出文件为 LF; 此后「编辑导致整文件行尾归一、diff 爆炸」不再可能(git 侧看不到行尾差异)。
- **仍适用(层3未完成)**: 存量工作区文件磁盘上仍是 CRLF(一次性转 LF 暂缓), 各 clone 跑完工作区转换前, 下文「edit 工具 oldText CRLF 匹配」「Python 文本模式 `\r\r\n`」「heredoc 终止符」等条目照旧适用。
- **长期适用**: `.cmd` 生成物必须 CRLF(cmd 对 LF 拆错行)与 Python 写模式陷阱, 与仓库行尾统一无关。

### 统一 LF 后 `kb.index` 在 Windows 把生成物写成 CRLF: 一批无内容差异的 modified

- **触发**: 跑 `commands run kb.index`(或任何用 Python 文本模式写 `.md` 的生成器)后看 `git status`。
- **判别**: 一批 `_index.md` 被标记 modified, 但 `git diff` **返回 0**(clean filter 把两侧都归一成 LF ⇒ 无内容差异);
  `git ls-files --eol` 显 `i/lf w/crlf`, 而工作区其余文件是 `w/lf`(2026-10-02 起 `.gitattributes` `eol=lf`)。
  实测 2026-10-03: `kb.index` 后 9 个 `_index.md` 变 `w/crlf`。**这不是索引内容漂移** —— 别据此判断生成物变了。
  2026-10-04 根治后 `kb.index` 不再复现(处置①); 本条保留给存量**手写**文件与其它未登记的文本模式写盘点。
- **处置**: ①**根治已落地 (2026-10-04)**: 5 处生成器写盘点(`gen_all.py` / `gen_kb_index.py` / `gen_tasks_index.py` /
  `gen_docs_index.py` / create-issue 的 `gen_issues_index.py`)一律显式 `write_text(..., newline="\n")` —— 原先吃
  `newline=None` 的默认值, 落盘时按 `os.linesep` 翻换行, Windows 上就是 CRLF。守阵
  `tests/test_memory_bank.py::test_generated_indexes_are_lf_only`(逐字节断言生成物无 CR; `--check` 用 `read_text`
  会把 CRLF 折成 LF, 对行尾不敏感, 所以这条缺陷此前能一路绿灯)。
  ②存量工作区(层3 未做)里**手写**文件仍可能是 CRLF, 归一只需 `git checkout -- <那批文件>`(内容零差异, 安全);
  提交侧 clean filter 本就会归一, 不归也**不进 commit**(blob 不变)。
  ③⚠ 生成物由 CRLF 改写成 LF 后, 若索引 stat 缓存还记着旧(CRLF)尺寸, `git status` 会报一批**幽灵 M** ——
  `git diff` / `git diff-files` 内容比对均为 0, `git update-index --refresh` 也刷不掉; 跑一次
  `git add -- <那批文件>` 刷新 stat 即净(内容与索引恒等 ⇒ 不产生任何暂存条目)。
- **复发 +1 (2026-10-05)**: 处置①修的是生成器, **其它 clone 盘上的旧 CRLF 生成物不会被自动清理** —— 本 clone
  首次跑 test.quick 即被守阵 `test_generated_indexes_are_lf_only` 抓到 11 个 `_index.md` 残留(`eol=lf` 归一化下
  git status 不可见); `kb.index` 重建即绿。没翻到本条的原因: 本轮任务是纯文档编辑, 未走 git 前置路由;
  守阵报错自带处置配方, 拦截闭环成立。
- **复发 +2 (2026-10-07)**: 同一根因换了个入口 —— **一次性清洗脚本**用 `Path.write_text(text, encoding="utf-8")`
  写回 64 个**手写** `memory-bank/*.md`, 默认 `newline=None` 在 Windows 上按 `os.linesep` 把 LF 翻成 CRLF,
  整批文件变 `w/crlf`; `.gitattributes` 归一化下 `git diff` **只显示改动行**(内容差异 84 行), 肉眼完全看不出来。
  **暴露它的是 git 的警告行**「CRLF will be replaced by LF the next time Git touches it」—— 不是任何守阵
  (守阵 `test_generated_indexes_are_lf_only` 只覆盖**生成物**, 手写文件没有对应守卫)。处置: 就地
  `p.write_text(p.read_text(), encoding="utf-8", newline="\n")` 重写, 复核 `b"\r" in p.read_bytes()` 归零。
  **为什么没命中**: 本条处置①的措辞是「**生成器**写盘点一律显式 `newline="\n"`」, 读起来像"只约束生成器";
  而这次是**一次性脚本写手写文档**, 不在那句话的射程内 —— 判据其实是「**任何** `write_text` 都要显式
  `newline="\n"`」, 与是不是生成器无关。**建议**: 写 md 类文件时 `newline="\n"` 当默认肌肉记忆, 别等守阵
  (手写文件那条路没有守阵兜底)。

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

### 用 Python 文本模式**写回已含 CRLF 的内容**会写出 `\r\r\n`(双重转换)

- **触发**: 用 `Path.write_text(...)` / `open(p, "w")` 写回**刚从 CRLF 文件读出的内容**(Windows)。
- **判别**: 文本模式默认 `newline=None` ⇒ 每个 `\n` 再翻一次成 `\r\n`, 内容里本就有的 `\r\n`
  于是变 `\r\r\n` —— **每行多一个裸 `\r`**。编辑器多半吞掉, 肉眼正常, 只有逐字节比对才现形
  (实测一份 90 行的坑文档写出后 `裸CR = CRLF = 90`)。
  连带效应很阴: 各 cap 按**原始字符数**算, 虚高的 90 字符会把文件"顶到 cap" —— 实测该文件因此报
  6,084(真值 5,980), 差 104 = 行数, 看着像内容真超限。
- **处置**: 写回一律 `Path(p).write_bytes(text.encode("utf-8"))`; 复核
  `b.count(b"\r\n")` 与 `b.count(b"\r") - b.count(b"\r\n")`(后者必须 0); 已写坏的用
  `text.replace("\r\r\n", "\r\n")` 修回。

### Git Bash 里 `sed -i` 会把整份文件的行尾改成 CRLF

- **触发**: 在工具 shell(Git Bash / MSYS)里用 `sed -i` 做机械替换。本仓库 2026-10-02 起统一 **LF**
  (`.gitattributes` `* text=auto eol=lf`), 而 HEAD 里是 LF 的文件经 `sed -i` 会被整份写成 **CRLF**。
- **判别**: `git diff` / `git status` **完全看不出**(clean filter 把两侧都归一成 LF ⇒ 行尾变化不进 diff),
  只有按字节量才现形 —— 实测 2026-10-06 一遍 `sed -i` 把 `check_kb_structure.py` 从
  `LF=392 / CRLF=0` 变成 `LF=414 / CRLF=414`, 而 `git diff --stat` 只显示改的那几行。
  危害不在 git(blob 被归一, 提交不受影响), 而在**任何按原始字符数算的东西**: `_common.char_count()`
  在 CRLF 上**每行多算 1** ⇒ 角色 `pitfall` / `slice` 等的 cap 检查可能凭空多出一笔"债务",
  `b.count(b"\n") == b.count(b"\r\n")` 那类自查断言也会响。**与本轮新记的「拿 KB 比字符数」是同一族**:
  口径不一致 ⇒ 报出根本不存在的债。
- **处置**: ①机械替换优先用 Edit 工具(**但这不是保证** —— 见下方复发条: Edit 同样能把整份写成 CRLF);
  ②非用 sed 不可时, 改完**立刻按字节归一**
  (`p.write_bytes(p.read_bytes().replace(b"\r\n", b"\n"))`), 并核对 `git diff --stat` 的变更行数
  确实等于你真正改的行数; ③复核别用 `grep -c $'\r'`(会给假结果), 用 `b.count(b"\r\n")`。
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
- **同族(2026-09-25 实测, 更隐蔽)**: 把 **Windows 路径**写进 Python 字符串字面量 ⇒ `\a` / `\t` / `\n`
  被当转义**吃掉**, 落盘成**控制字符**。现场: `tmpdir.md` 里的
  `R:\Temp\auto-qb\tests` 变成 `R:` + BEL(0x07) + `uto-qb` + TAB(0x09) + `ests` ——
  **肉眼看着像对的**(控制字符在编辑器里几乎不可见), `grep` 也命中, 只有 `repr()` 才露馅;
  且 cap 计数会**少算**这几行。⇒ 写路径一律用**正斜杠**; 怀疑某行被吃字符时先 `repr(行)` 看一眼。
- **复发(2026-09-29)**: `cat >> 文件 << 'EOF'` 追加多行测试代码 ⇒ 结束符未被识别(体内容经 shell 进来带
  CRLF), **追加内容被截断**且落成混合行尾, 追加完没核对尾部就继续往下走 —— 到复跑测试才暴露。
  处置照旧: **别走 heredoc**, 多行内容一律用编辑工具 / Python 脚本落盘, 落完必查行数与文件尾部。

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
