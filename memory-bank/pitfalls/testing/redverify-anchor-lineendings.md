# 红验脚本按 LF 拼锚点，在 CRLF 文件上静默匹配不上（且手抄缩进易差 1 空格）

> 摘要: 变异审计的**红验**要靠「把源码某段文本替换成变异体 → 跑目标用例 → 还原」。主仓相当一部分 `.py` 是 **CRLF** 行尾(如 `src/auto_qb/config/schema/__init__.py`), 而红验脚本通常 `read_bytes().decode()` 后直接拿**带 `\n` 的多行字符串**当锚点 —— CRLF 文件里这种锚点 `count == 0`, 替换**根本没发生**, 但脚本若只按「跑完绿不绿」判 KILLED/SURVIVED, 就会把「没变异」的绿当成「变异存活」(假 SURVIVED), 或反过来把空转的探针当通过。第二个同源陷阱: 锚点里的**缩进空格靠手抄**, 极易差 1 个(实测 52 vs 51 字符), 同样静默失配。判别: 红验结果里出现 `ANCHOR-MISS` 就停手; 没有这个兜底时, 表现为「明明写了对的守阵却仍 SURVIVED」。处置: ①锚点先 `replace("\r\n", "\n")` 归一到 LF 空间再匹配、写盘前转回; ②缩进一律用 `" " * N` 拼接, 不手抄; ③锚点 `count != 1` 必须报错停手(数量 >1 说明锚点不唯一, 也不可用)。
> 触发: 红验, 变异测试, mutmut, apply, 同构变异, 锚点, 锚点失配, ANCHOR-MISS, 源码替换, 还原, CRLF, LF, 行尾, newline, 缩进, 空格数, 差一空格, read_bytes, write_bytes, 假绿, 假存活, 守阵空转, 探针空转

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md, memory-bank/testing/baselines/26-10-08-1229-mutants-config-schema-surface.md

### 两个失配形态（2026-10-08, config schema 键面轮）

- **触发**: 认领 `config/schema/__init__.py` 键面 issue(27 条 S4 真洞候选), 写临时脚本逐条「文本替换成同构变异 → 跑目标用例 → 原字节还原」做红验, 结果里多行锚点那批报 `ANCHOR-MISS(0)`, 单行锚点那批正常 KILLED —— 若不看那列, 会把「压根没变异」误当成「验过了」。

- **形态一: CRLF 让多行锚点静默失配**。主仓 `src/auto_qb/config/schema/__init__.py` 实测 192 处 CRLF(全文件 CRLF)。红验脚本用 `path.read_bytes().decode("utf-8")` 拿原文, 锚点写成 `'if f.kind == "object":\n                walk(f.fields or (), path)'` —— 文件里实际是 `...:\r\n`, 于是 `str.count(锚点) == 0`, `.replace()` 是空操作, 写回的字节与原文**完全一致**, 被测函数**根本没被变异**。此时跑测试必然绿 ⇒ 脚本报告 `SURVIVED`。**危险点**: 这与「守阵真的挡不住」在输出上无法区分, 只有 `count != 1 → ANCHOR-MISS` 这一句兜底能暴露。
  - **为什么首版会误判成 KILLED**: 单行锚点(如 `"log_levels":`)不受行尾影响、正常匹配, 于是「单行的全 KILLED、多行的全 ANCHOR-MISS」混在一张表里, 若只扫一眼 `KILLED n/m` 就会以为多行那批也验过了。
  - **处置**: `lf = raw.decode("utf-8").replace("\r\n", "\n")` → 在 LF 空间做 `count`/`replace` → 写盘 `mutated.replace("\n", "\r\n").encode("utf-8")`; 还原仍用**原字节** `write_bytes(orig_bytes)`(不要靠反向替换, 多重变异叠加时会漏)。

- **形态二: 手抄缩进差 1 空格**。同一份脚本里锚点 `"            if f.ui_only:\n                continue\n"` 手抄时把 16 空格写成了 17(实测 `len` 52 vs 51), 在 CRLF 修好后仍 `count == 0`。这类错误**肉眼完全看不出来**(对齐看着一模一样), 只能靠 `count != 1` 兜底 + 用 `" " * 16` 拼接规避。
  - **处置**: 多行锚点写成 `'if f.kind == "object":' + "\n" + SP16 + 'walk(f.fields or (), path)'`(`SP16 = " " * 16`), 缩进数量显式可数。

### 另一个同源陷阱: 探针放在不可达的分支上（空转）

- **触发**: CRLF 与缩进都修好后仍剩 1 条 SURVIVED(`readonly_config_paths__mutmut_2`, `continue` → `break`)。手工推算这两者「应当有差别」(断链会丢后续字段), 于是先怀疑是判据/脚本问题而不是急着判等价变异, 查下去发现是探针本身空转。

- 修完锚点后仍有 1 条 SURVIVED(`readonly_config_paths__mutmut_2`, `continue` → `break`)。原因不在行尾, 而在**探针设计**: 首版合成结构把 `ui_only` 叶放在**顶层**, 而 `readonly_config_paths()` 走的是 `real_config_fields()`, 后者**已先行滤掉 ui_only** —— 那句 `if f.ui_only: continue` 在顶层**永远进不去**, `continue` 与 `break` 自然同结果, 探针空转。
  - **判别**: 一条变异在「手工算过应当有差别」的前提下仍 SURVIVED, 先问「我造的输入真的进得了那一行的分支吗」, 别急着判等价变异。
  - **处置**: 把合成结构改成**嵌套层** `[ui_only 叶][readonly 叶]` 放在一个非 readonly 的 object 段里 —— 嵌套段不做 ui_only 过滤, `continue`/`break` 才真正分化(改完即 KILLED)。
  - **这条与形态一二同源**: 三者都是「脚本/探针看着在验, 其实没验到」。红验的**唯一可信信号**是「锚点命中数 == 1 且跑完变红」, 缺任一半都不能算验过。
