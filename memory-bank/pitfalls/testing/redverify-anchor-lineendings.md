# 红验脚本按 LF 拼锚点，在 CRLF 文件上静默匹配不上（且手抄缩进易差 1 空格）

> 摘要: 变异审计的**红验**要靠「把源码某段文本替换成变异体 → 跑目标用例 → 还原」。主仓相当一部分 `.py` 是 **CRLF** 行尾(如 `src/auto_qb/config/schema/__init__.py`), 而红验脚本通常 `read_bytes().decode()` 后直接拿**带 `\n` 的多行字符串**当锚点 —— CRLF 文件里这种锚点 `count == 0`, 替换**根本没发生**, 但脚本若只按「跑完绿不绿」判 KILLED/SURVIVED, 就会把「没变异」的绿当成「变异存活」(假 SURVIVED), 或反过来把空转的探针当通过。第二个同源陷阱: 锚点里的**缩进空格靠手抄**, 极易差 1 个(实测 52 vs 51 字符), 同样静默失配。判别: 红验结果里出现 `ANCHOR-MISS` 就停手; 没有这个兜底时, 表现为「明明写了对的守阵却仍 SURVIVED」。处置: ①锚点先 `replace("\r\n", "\n")` 归一到 LF 空间再匹配、写盘前转回; ②缩进一律用 `" " * N` 拼接, 不手抄; ③锚点 `count != 1` 必须报错停手(数量 >1 说明锚点不唯一, 也不可用)。
> 触发: 红验, 变异测试, mutmut, apply, 同构变异, 锚点, 锚点失配, ANCHOR-MISS, 源码替换, 还原, CRLF, LF, 行尾, newline, 缩进, 空格数, 差一空格, read_bytes, write_bytes, 假绿, 假存活, 守阵空转, 探针空转, dump 行块, 函数相对行号, hunk 头, qualname, 分隔符字形, docstring 续行, 子进程超时

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md, memory-bank/testing/baselines/26-10-08-1229-mutants-config-schema-surface.md, memory-bank/testing/baselines/26-10-10-0925-mutants-config-loader-defaults.md, memory-bank/testing/baselines/26-10-10-1408-mutants-hr-service.md, memory-bank/testing/baselines/26-10-10-1458-mutants-hr-serialization.md, memory-bank/testing/baselines/26-10-10-2044-mutants-hr-judgment-core.md

**复发**: 5 —— ①2026-10-10(config loader-defaults 轮): 本轮的形态是「**删整行**」而不是「替换多行文本」, 首版脚本在**字节层**做(`splitlines(keepends=True)` 后逐行 `strip()` 比对), 却拿 **str 锚点**去比 bytes 行 ⇒ 恒不相等、`hits=0`; 以及单行锚点在两个函数里各出现一次(`count=2`)。两个都由坑里那句「`count != 1` 必须报错停手」的兜底抓住(报 `ANCHOR-MISS` 而非假绿), 属于**守阵按预期工作**, 但坑里没写「字节层操作的类型失配」这一形态, 首版照写仍会踩。新增形态三见下。②2026-10-10(hr service-engine 轮): 锚点来源从「手写文本」换成**从 mutmut dump 取行块**, 于是踩到「dump 行块相对源码整体**去缩进**、且**续行缩进不被归一**」⇒ 精确块匹配恒失配(9 条 ANCHOR-MISS)。新增形态四见下。③2026-10-10(hr serialization 轮): 同源第二面 —— dump 的 hunk 行号是**函数相对**(不是文件相对)、`ǁ` 分隔符**字形不可靠**、去缩进对 **docstring 续行不生效** ⇒ 首版 271 条全失配。新增形态五见下。④2026-10-10(hr runtime-worker 轮): dump 的 hunk **带上下文行**且 docstring 续行不去缩进 ⇒ 拿「首行缩进差」当统一位移, 首版整块替换把上下文行也吃掉(6 条 APPLY-ERROR)。新增形态六见下。⑤2026-10-10(hr judgment-core 轮): 改用「整段 hunk(上下文 + 删除行)」定位后, 取**首行**缩进作 `add` 行基准 —— hunk 首行是 `def`/docstring(缩进 0)而被改行在函数体内(缩进 4)时, `add` 行**丢缩进** ⇒ `IndentationError` ⇒ pytest 收集失败被**伪判 KILLED**(首版红验 242/292 与 S6 严重不符, 实测 ~52 条虚高)。新增形态七见下。

### 两个失配形态（2026-10-08, config schema 键面轮）

- **触发**: 认领 `config/schema/__init__.py` 键面 issue(27 条 S4 真洞候选), 写临时脚本逐条「文本替换成同构变异 → 跑目标用例 → 原字节还原」做红验, 结果里多行锚点那批报 `ANCHOR-MISS(0)`, 单行锚点那批正常 KILLED —— 若不看那列, 会把「压根没变异」误当成「验过了」。

- **形态一: CRLF 让多行锚点静默失配**。主仓 `src/auto_qb/config/schema/__init__.py` 实测 192 处 CRLF(全文件 CRLF)。红验脚本用 `path.read_bytes().decode("utf-8")` 拿原文, 锚点写成 `'if f.kind == "object":\n                walk(f.fields or (), path)'` —— 文件里实际是 `...:\r\n`, 于是 `str.count(锚点) == 0`, `.replace()` 是空操作, 写回的字节与原文**完全一致**, 被测函数**根本没被变异**。此时跑测试必然绿 ⇒ 脚本报告 `SURVIVED`。**危险点**: 这与「守阵真的挡不住」在输出上无法区分, 只有 `count != 1 → ANCHOR-MISS` 这一句兜底能暴露。
  - **为什么首版会误判成 KILLED**: 单行锚点(如 `"log_levels":`)不受行尾影响、正常匹配, 于是「单行的全 KILLED、多行的全 ANCHOR-MISS」混在一张表里, 若只扫一眼 `KILLED n/m` 就会以为多行那批也验过了。
  - **处置**: `lf = raw.decode("utf-8").replace("\r\n", "\n")` → 在 LF 空间做 `count`/`replace` → 写盘 `mutated.replace("\n", "\r\n").encode("utf-8")`; 还原仍用**原字节** `write_bytes(orig_bytes)`(不要靠反向替换, 多重变异叠加时会漏)。

- **形态二: 手抄缩进差 1 空格**。同一份脚本里锚点 `"            if f.ui_only:\n                continue\n"` 手抄时把 16 空格写成了 17(实测 `len` 52 vs 51), 在 CRLF 修好后仍 `count == 0`。这类错误**肉眼完全看不出来**(对齐看着一模一样), 只能靠 `count != 1` 兜底 + 用 `" " * 16` 拼接规避。
  - **处置**: 多行锚点写成 `'if f.kind == "object":' + "\n" + SP16 + 'walk(f.fields or (), path)'`(`SP16 = " " * 16`), 缩进数量显式可数。

### 形态三: 字节层比对的类型失配（2026-10-10, config loader-defaults 轮）

- **触发**: 本轮要变异的其中一类是「**删掉整个关键字实参**」(如删掉 `download_path=preset.download_path,`), 用整行删除而不是文本替换。脚本为保 CRLF 全程在 bytes 层操作(`data.splitlines(keepends=True)`), 比对时写成 `ln.strip() == anchor.strip()` —— 左边是 **bytes**、右边是 **str**, Python 静默判不等 ⇒ `hits=0` ⇒ 6 条 `_resolve_hr_site_bindings` 变异全报 `ANCHOR-MISS`。
- **同源第二例**: `host=_get(spec, "host", d.host),` 这类单行锚点在 `load_qbittorrent_config` 与 `load_web_config` 里**各出现一次** ⇒ `count=2`, 同样被兜底拦下(改带上下文的两行锚点后可用)。
- **判别**: 与形态一二完全同表 —— 输出里出现 `ANCHOR-MISS` 就停手, 别把它当「已验」; 一行锚点在**同文件里出现在两个函数**时也必须靠 `count != 1` 兜底(形态一二讲的是文件级行尾/缩进, 这条讲的是**函数级重复**)。
- **处置**: ①字节层比对时锚点一律 `.encode()`(或整段 `decode` 后在 str 空间做、写盘前转回 —— 与形态一同一条纪律, 关键是**两侧同类型**); ②单行锚点不够唯一就**带上相邻行**(把上一行一起拼进锚点)。

### 形态四: 锚点取自 mutmut dump 时的「整体去缩进 + 续行不归一」（2026-10-10, hr service-engine 轮）

- **触发**: 本轮不再手写锚点, 而是**从 R14 的带 diff dump 直接取每条候选的行块**做同构变异(省掉手抄)。首版脚本按「整块精确匹配」找锚点, 结果 9 条 `_run_downloads` 变异全报 `ANCHOR-MISS`。
- **根因(两层)**:
  1. **dump 行块相对源码整体去缩进** —— mutmut 抽取函数体再打 diff, 方法体行在 dump 里比源码**少 4 空格**(类体缩进)。所以拿 dump 行块去 `==` 源码行**恒不等**。
  2. **续行(反斜杠续行)的缩进 mutmut 不归一** —— 同一个 hunk 内, 普通行是「源码 − 4」, 而**续行**(如 `if ... and \` 的下一行)却是「源码 − 0」。实测同一块里既有 −4 也有 −0 ⇒ 想用「整体加一个常量偏移」的写法也**恒失配**(这也是为什么「逐 offset 试精确匹配」这一版只救回一部分, 9 条仍失配)。
- **判别**: 与形态一二三同表 —— 输出出现 `ANCHOR-MISS` 就停手; 但这次**不是** `count=0`, 而是「所有 offset 都 0 命中」。
- **处置**: ①**放弃精确匹配**, 改用「**strip 后内容**序列唯一命中」定位(要求整块 strip 后逐行相等且唯一); ②改写时按「源码行缩进 − 锚点行缩进」算**位移**, 只重写 strip 后**有变化**的行(difflib opcodes), **未变的上下文行原样保留**(否则会把续行重新缩进成错值)。③另一处本轮踩到的同源: 首版脚本用 `Path.write_text()` 在 Windows 把 **LF 写成 CRLF**(还原时污染工作树) ⇒ 一律 **`read_bytes` / `write_bytes`**, 不碰文本模式。
- **一句话**: 锚点来源换成「别人产出的 diff」时, 先假设它的**空白/缩进不可信** —— 只信 strip 后的内容, 靠唯一性 + 位移复原。

### 形态五: dump 的 hunk 行号是**函数相对** + `ǁ` 分隔符字形不可靠 + docstring 续行不去缩进（2026-10-10, hr serialization 轮）

- **触发**: 同形态四(从 R14 dump 取行块做同构变异), 但换了实现 —— 首版想用「hunk 头 `@@ -L,C +L2,C2 @@` 的 `L` 当**文件行号**」直接定位, 结果 **271 条全报 `ANCHOR-MISS`**。
- **根因(三层)**:
  1. **hunk 行号是函数相对的** —— mutmut 逐函数抽体打 diff, `@@ -1,3 @@` 的 `1` 指的是**函数体第 1 行**(= `def` 行或它的装饰器行), 不是文件第 1 行。按文件行号套 ⇒ 全部错位。
  2. **mutmut id 的分隔符字形不可靠** —— id 形如 `xǁHrEntryǁto_json`(类方法) / `x_hr_dir` / `x__opt_int`(模块函数)。那个类分隔符是 **U+01C1 `ǁ`**, 脚本里按字面 `"ǁ"` split **可能不匹配**(字形相近的不同码位 / 文件编码往返) ⇒ 解析不出 qualname。判据要写成「**非标识符字符**」(`re.split(r"[^A-Za-z0-9_]+", ...)`), 不认字形。
  3. **去缩进对 docstring 续行不生效** —— 与形态四同源但触发源不同: 形态四是**反斜杠续行**, 本轮是 **docstring 的多行正文**。实测 `cancel_all` 的 hunk 里 `"""` 那行保留 8 空格, 而紧随的 `with self._cond:` 被去成 4 空格 ⇒ 同一块内既有 −0 也有 −4, 「整体加常量偏移」恒失配。
- **判别**: 与形态一~四同表 —— 输出出现 `ANCHOR-MISS` 就停手; 本轮表现是「**全部**失配」而不是个别, 一眼可辨是定位法本身错了。
- **处置**(本轮的可用配方, 比形态四更省事): ①先用变异 id 的 qualname 定位**函数体行范围**(类方法走 `class X` → `def y`); ②在范围内按 **strip 后内容**匹配被删(`-`)行序列, 要求**恰好命中一次**(函数范围天然消掉了跨函数重名); ③以「**源码该行缩进 − dump 该行缩进**」为位移, 把新增(`+`)行还原到源码缩进后替换; ④自检 —— 逐条 apply 后 `ast.parse` 必须通过、revert 后字节恒等(本轮 271 条全过)。
- **同源边界**: 变异体若让守阵**挂起**(如 `_cond.wait(None)`), 红验脚本对子进程**必须设超时**, 否则整轮永不返回(本轮实测: 无超时版跑了 6m49s 才被手工 `TaskStop`); 挂起按「未绿 = 被杀」处理(与 mutmut 的 `timeout` 同口径)。

### 形态六: dump 的 hunk **带上下文行** + docstring 续行不去缩进（2026-10-10, hr runtime-worker 轮）

- **触发**: 从 R14 dump 取 hunk 做同构变异时, 首版拿「整块(含上下文行)替换」—— 结果 6 条 `APPLY-ERROR`(把**上下文行**也一起吃掉了)。
- **根因**: dump 的 hunk **不只有 `-`/`+` 行**, 还带**上下文行**(未变行, 前缀空格); 且同形态四五 —— **去缩进对 docstring 续行不生效**(同 hunk 内代码行 −4 / docstring 行 −0)⇒ 不能拿「首行缩进差」当**统一位移**。
- **处置**: ①**只用 `-` 行**定位与取缩进; ②歧义(命中不唯一)时用**整段 hunk(上下文 + `-`)定位**, 但**只替换 `-` 区间**(上下文行原样保留); ③`+` 行的缩进基准取**首个 `-` 行**对应源行的缩进。

### 形态七: 整段 hunk 定位后取**首行**缩进作 `add` 行基准 ⇒ 丢缩进 ⇒ `IndentationError` 伪判 KILLED（2026-10-10, hr judgment-core 轮）

- **触发**: 按形态六改用「整段 hunk(上下文行 + 删除行)strip 唯一命中」定位后, 红验报 **242/292 KILLED** —— 但 S6 只支持 ~170。**逐文件对差严重不符**(bencode 红验 68 杀 vs S6 16 杀)。
- **根因**: 重排 `add`(`+`)行时, 缩进基准取的是**匹配到的首行**(`base_indent = 首行缩进`)—— 当 hunk **首行是 `def`/docstring**(缩进 0)而被改行在**函数体内**(缩进 4)时, `rel = add缩进 − del缩进 = 0` ⇒ `add` 行被重排成**缩进 0**, 插进函数体里 ⇒ **`IndentationError`**。pytest 收集即失败 ⇒ 脚本按「跑完非零 = KILLED」**伪判被杀**。实测 ~52 条虚高(bencode `bdecode m3` 等)。
  - **危险点**: 与「守阵真的杀死了这条」在 `KILLED` 列上**完全无法区分** —— 唯一暴露方式是**与 S6(权威工具)对差**, 或 apply 后做语法自检。
- **处置**: ①缩进基准改取**首个删除行**对应的源行(`d0 = 第一个 del 的下标; base_indent = src_lines[i+d0] 的缩进`), `rel = add缩进 − 首个del缩进`; ②**apply 后 `ast.parse` 自检**, 不通过记 `APPLY-ERROR`(而非跑测试) —— 把「文件被改坏」与「守阵杀掉变异」彻底分开; ③**红验数字必须与 S6 对差**(逐文件新杀数), 对不上先怀疑脚本而非结论。

- **一句话(六/七同源)**: 用**整段 hunk**定位时, 「缩进基准」必须绑定到**被替换的 `-` 行**, 不能绑定到「匹配到的第一行」; 且 apply 后一律 `ast.parse` 自检。

### 另一个同源陷阱: 探针放在不可达的分支上（空转）
- **触发**: CRLF 与缩进都修好后仍剩 1 条 SURVIVED(`readonly_config_paths__mutmut_2`, `continue` → `break`)。手工推算这两者「应当有差别」(断链会丢后续字段), 于是先怀疑是判据/脚本问题而不是急着判等价变异, 查下去发现是探针本身空转。

- 修完锚点后仍有 1 条 SURVIVED(`readonly_config_paths__mutmut_2`, `continue` → `break`)。原因不在行尾, 而在**探针设计**: 首版合成结构把 `ui_only` 叶放在**顶层**, 而 `readonly_config_paths()` 走的是 `real_config_fields()`, 后者**已先行滤掉 ui_only** —— 那句 `if f.ui_only: continue` 在顶层**永远进不去**, `continue` 与 `break` 自然同结果, 探针空转。
  - **判别**: 一条变异在「手工算过应当有差别」的前提下仍 SURVIVED, 先问「我造的输入真的进得了那一行的分支吗」, 别急着判等价变异。
  - **处置**: 把合成结构改成**嵌套层** `[ui_only 叶][readonly 叶]` 放在一个非 readonly 的 object 段里 —— 嵌套段不做 ui_only 过滤, `continue`/`break` 才真正分化(改完即 KILLED)。
  - **这条与形态一二同源**: 三者都是「脚本/探针看着在验, 其实没验到」。红验的**唯一可信信号**是「锚点命中数 == 1 且跑完变红」, 缺任一半都不能算验过。
