# 红验锚点 · CRLF 与手抄缩进两个失配形态(外迁)

> 摘要: `pitfalls/testing/redverify-anchor-lineendings.md`「两个失配形态（config schema 键面轮）」原文整体外迁(2026-11-05 压缩), 正文原样照搬, 标题降一级以避开坑档条目扫描。
> 触发: CRLF, LF, 行尾, 锚点失配, ANCHOR-MISS, 手抄缩进, 差一空格, read_bytes, write_bytes

## 两个失配形态（config schema 键面轮）

- **触发**: 认领 `config/schema/__init__.py` 键面 issue(27 条 S4 真洞候选), 写临时脚本逐条「文本替换成同构变异 → 跑目标用例 → 原字节还原」做红验, 结果里多行锚点那批报 `ANCHOR-MISS(0)`, 单行锚点那批正常 KILLED —— 若不看那列, 会把「压根没变异」误当成「验过了」。

- **形态一: CRLF 让多行锚点静默失配**。主仓 `src/auto_qb/config/schema/__init__.py` 实测 192 处 CRLF(全文件 CRLF)。红验脚本用 `path.read_bytes().decode("utf-8")` 拿原文, 锚点写成 `'if f.kind == "object":\n                walk(f.fields or (), path)'` —— 文件里实际是 `...:\r\n`, 于是 `str.count(锚点) == 0`, `.replace()` 是空操作, 写回的字节与原文**完全一致**, 被测函数**根本没被变异**。此时跑测试必然绿 ⇒ 脚本报告 `SURVIVED`。**危险点**: 这与「守阵真的挡不住」在输出上无法区分, 只有 `count != 1 → ANCHOR-MISS` 这一句兜底能暴露。
  - **为什么首版会误判成 KILLED**: 单行锚点(如 `"log_levels":`)不受行尾影响、正常匹配, 于是「单行的全 KILLED、多行的全 ANCHOR-MISS」混在一张表里, 若只扫一眼 `KILLED n/m` 就会以为多行那批也验过了。
  - **处置**: `lf = raw.decode("utf-8").replace("\r\n", "\n")` → 在 LF 空间做 `count`/`replace` → 写盘 `mutated.replace("\n", "\r\n").encode("utf-8")`; 还原仍用**原字节** `write_bytes(orig_bytes)`(不要靠反向替换, 多重变异叠加时会漏)。

- **形态二: 手抄缩进差 1 空格**。同一份脚本里锚点 `"            if f.ui_only:\n                continue\n"` 手抄时把 16 空格写成了 17(实测 `len` 52 vs 51), 在 CRLF 修好后仍 `count == 0`。这类错误**肉眼完全看不出来**(对齐看着一模一样), 只能靠 `count != 1` 兜底 + 用 `" " * 16` 拼接规避。
  - **处置**: 多行锚点写成 `'if f.kind == "object":' + "\n" + SP16 + 'walk(f.fields or (), path)'`(`SP16 = " " * 16`), 缩进数量显式可数。
