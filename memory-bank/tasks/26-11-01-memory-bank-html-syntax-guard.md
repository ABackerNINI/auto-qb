# 26-11-01-memory-bank-html-syntax-guard — HTML 坏标签机检守卫(闭合标签缺右尖括号吞正文类) + vnu 巡检

**Status:** In Progress
**Added:** 2026-11-01
**Updated:** 2026-11-01
**Summary:** HTML 坏标签机检守卫(闭合标签缺右尖括号吞正文类) + vnu 巡检
**Topics:** memory-bank-html-syntax-guard
**Refs:** memory-bank/pitfalls/docs/html-endtag-missing-gt.md, memory-bank/pitfalls/ops/vnu-gate-bootstrap.md, memory-bank/testing/baselines/26-11-01-0938-memory-bank-html-syntax-guard.md

## 原始请求

1. 「修复文档排版错乱:26-11-01-0334-bug-torrent-transfer-duplicate-409.html」—— 修复后全库复扫发现同型笔误还有一处, 用户续示「一并修」。
2. 「此类问题是否可以机检并放进闸门」—— 用户追问「有没有现成的工具可以检查 html 语法」「可以做到闸门只检查修改过的文档吗」, 最终拍板: 增量闸门 + 全量巡检(混合形态)。

## 思考过程与决策

- **工具选型 (实测拍板)**: W3C v.Nu(vnu.jar) 规范级、全库 645 件实测 9s、对事故样本一发命中, 本机 Java 23 可用; stdlib html.parser/lxml 不报语法错(HTML5 容错, 坏标签被当合法 token 吞掉 —— 恰是浏览器静默的原因), 只能做结构断言; npm linter 未选。结论: 现成工具接**巡检**, 轻量自研接**常驻闸门**(D 拍板: 混合)。
- **闸门只查改动文件**: 引擎原生支持 `<changed:GLOB>`/`<each:GLOB>` 占位符 —— v.Nu 接受多文件参数, 用 `<changed:memory-bank/**/*.html>` 单次调用(不逐文件起 JVM, 也避 each_limit); 存量 320 条 error 因此不进闸门(改谁谁达标), 无需冻结清单。
- **常驻判据两层**: L1 行级正则(尾标签名后紧跟非法字符) + L2 stdlib 解析器残缺标签名校验(html.parser 实测复现浏览器吞嵌套行为: 残缺名 `code):` 永不匹配栈上 `code`)。两个首跑实测陷阱: ①单 lookahead 正则会被回溯穿透而全库误报(`</title>` → `</titl`+`e`), 双 lookahead 修; ② `<script>` 内 JS 字面量 `replace(/</g, …)` 触发 L1 误报, 加 script/style 等长遮蔽(保行号), L2 走解析器自身 CDATA 态天然免疫。
- **存量盘点**: L1+L2 全库 645 件零命中(本日两处修完后), 无需存量冻结; v.Nu 全库 320 条 error 属另一层债务(含真伤 26-09-21-1248 b/code 嵌套、26-09-25-0853 未转义 `<`), 留 `kb.html-audit` 低频清, 不挡提交。
- **闸门触发面 (2026-11-01 扩面)**: `match = [".html"]`(子串命中) + `<changed:**/*.html>` 全仓 —— 而不是 `match = [""]` 每次都展开: 命中面贴着「真有 HTML 改动」, 纯 md/py 提交不空跑, 无匹配仍走 `<changed:>` 静默跳过语义; 存量债务仍靠增量语义挡在外面(改谁谁达标, vendored 骨架样例里实测就有存量 error)。L1+L2 常驻面与 `kb.html-audit` 巡检面仍维持 memory-bank 口径未动。

## 实现计划

总体思路: 立档 → 写 `check_html.py`(L1+L2+`--vnu`) → 全库基线实测 → 接线 kb.check 与提交闸门(守阵钉双侧同步) → 补守阵 → 坑档入库 → 收尾。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 新建 `scripts/check_html.py`(L1+L2 常驻判据 + `--vnu` 巡检/jar 自动下载) | Done(2026-11-01) |
| 2 | 全库 645 件存量基线: L1+L2 零命中; 坏样本双网正中 | Done(2026-11-01) |
| 3 | 接线: kb.check 全量行 + 闸门全量行 + 闸门 `<changed:>` 增量 v.Nu 行 + `kb.html-audit` 任务 + `.gitignore` 加 `/.tools/` | Done(2026-11-01) |
| 4 | 守阵四条 `test_html_guard_*` + docstring 测试计划补节 | Done(2026-11-01) |
| 5 | 坑档 pitfalls/docs/html-endtag-missing-gt.md 入库 | Done(2026-11-01) |
| 6 | test.quick 全绿 + kb.check 全绿收口 | Done(2026-11-01) |
| 7 | 闸门扩面: v.Nu 增量面放开到全仓改动 HTML(match 子串 .html + `<changed:**/*.html>`), 守阵断言/docstring/ops 坑档同步 | Done(2026-11-01) |

## 进度日志

### R0 · 立档与落地 (2026-11-01)

事故两起同日修复(issue 26-11-01-0334:113 / reports/26-10-14-1110:320, 均为闭合标签少 `>`)后用户要求机检进闸门。三方案对比(v.Nu 实测 / stdlib 解析器 / npm linter)拍板混合形态: `scripts/check_html.py` L1+L2 常驻(kb.check + 闸门全量行, 全库 <2s 零依赖) + v.Nu 增量闸门(`<changed:>` 只查本次改动, `.tools/` jar 已就位) + `kb.html-audit` 全库巡检(报告不拦); 首跑两个陷阱(正则回溯误报 / script 字面量误报)修掉并落守阵。实测: L1+L2 全库 645 件零命中, 坏样本双网正中, test.quick 全绿(数字口径见 kb.baseline, 本轮 quick 无基线切片), kb.check 全绿; 坑档 pitfalls/docs/html-endtag-missing-gt.md 入库(复发 2)。改动随本专题入库。

- 2026-11-01 04:39 守卫落地: scripts/check_html.py(L1 行级正则 + L2 stdlib 解析器残缺标签名双网, script/style 遮蔽) 挂进 kb.check 与提交闸门; v.Nu 增量闸门行(changed:GLOB 只查本次改动) + kb.html-audit 全库巡检任务; 守阵四条 test_html_guard_* 入阵, test.quick 全绿(数字口径见 kb.baseline); 坑档 pitfalls/docs/html-endtag-missing-gt.md 复发 2; 存量基线 L1+L2 零命中, v.Nu 全库 320 条 error 留巡检清理

### R1 · 闸门扩面: 全仓改动 HTML (2026-11-01)

用户要求 HTML 检测闸门从「只查 memory-bank 的改动」放开到「所有更改的 html」。实测 memory-bank 外还有 268 件存量 HTML(`.agents/skills/` 下设计骨架样例等), 原闸门对它们完全不触发。四处改动: ①闸门 `match` 改子串 `".html"`; ②`<changed:memory-bank/**/*.html>` → `<changed:**/*.html>`(`_glob_match` 的 `**/` 语义实测覆盖根级与任意层级, 已删文件由 check_html 的 is_file 过滤兜底); ③守阵 `test_html_guard_wired_into_kb_check_and_gate` 加钉新触发面; ④check_html docstring 与 ops 坑档 vnu-gate-bootstrap 触发描述同步(认领链双向补齐)。真机验证: 对 skill 骨架样例按新命令形态跑 `--vnu --strict` 一发命中存量 error(空 `<title>`, rc=1) —— 扩面后改谁都真的会达标; test.pkg.scoped 与守阵四条全绿; L1+L2 常驻面与 kb.html-audit 巡检面维持 memory-bank 口径未动(全仓巡检若需要另起一轮)。

- 2026-11-01 09:38 闸门扩面: v.Nu 增量面放开到全仓改动 HTML(match=.html + changed:**/*.html), 守阵/坑档/docstring 同步, 全量绿见基线切片 26-11-01-0938
