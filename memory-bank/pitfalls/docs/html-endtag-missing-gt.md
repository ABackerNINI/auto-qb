# HTML 闭合标签缺右尖括号静默吞正文

> 摘要: HTML 闭合标签缺右尖括号静默吞正文
> 触发: 手编生成物 HTML(issue/report)时闭合标签漏 >; 或正文出现未转义 <
**Refs:** memory-bank/tasks/26-11-01-memory-bank-html-syntax-guard.md

### 闭合标签少 `>` 被分词器整段吞进非法尾标签, 元素永不闭合

- **触发**: 手编生成物 HTML 时把闭合标签写成 `</code)` / `</code下` (少 `>`); 或正文出现未转义 `<`。HTML5 容错设计下**静默**: 分词器把 `</code): 目标 …。</p` 连同下一个 `>` 整段吃进一个非法尾标签, `<code>` 永不闭合, 其后全部内容嵌进它 (2026-11-01 两起: issues/26-11-01-0334:113 s2-s7/footer 掉进左栏 / reports/26-10-14-1110:320)。
- **判别**: 症状 = 排版错乱但浏览器 DevTools 零报错; 实锤 = 查 DOM 父子关系(块级元素的祖先里出现 `code`/`pre` 这类行内容器)。机检: `commands run kb.check` 里的 check_html(L1 行级正则 + L2 残缺标签名双网); 规范级全量: `commands run kb.html-audit`(W3C v.Nu, 报 `Stray end tag` / `Unclosed element`)。
- **处置**: 补上 `>` 即修; **修后必须浏览器实测 DOM 几何/层级归位**, 不能只看源码像对的就算完(首例的吞段正文中一段在源码里看起来完好)。右尖括号紧邻标签名, 手编时极易连着中文标点一起漏 —— 编辑后必跑 `commands run kb.check`。
- **守阵**: tests/test_memory_bank.py 四条 `test_html_guard_*`(坏标签双网命中 / script 字面量不误报 / 全库 645 件存量零命中 / kb.check+闸门双挂) + 提交闸门 v.Nu 增量行(`<changed:>` 只查本次改动)。
- **复发**: 2 (2026-11-01: 同一天两处, 第二处是全库复扫时发现的存量; 当时无守阵, 路由没到 —— 守阵入闸后此形态归零)
