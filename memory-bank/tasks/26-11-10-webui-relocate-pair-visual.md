# 26-11-10-webui-relocate-pair-visual — WEBUI 整组迁移双排路径伪影错觉修正: 上排删除线替代透明度分层

**Status:** In Progress
**Added:** 2026-11-10
**Updated:** 2026-11-10
**Summary:** WEBUI 整组迁移双排路径伪影错觉修正: 上排删除线替代透明度分层
**Topics:** webui-relocate-pair-visual
**Refs:** memory-bank/pitfalls/web-ui/opacity-tier-ghosting.md, memory-bank/testing/baselines/26-11-10-0844-webui-relocate-pair-visual.md

## 本篇只回答

主列表 `save_path` 列迁移中双排 A→B 展示时, 上排「当前位置」用什么视觉手段表达层级, 才不会被读成下排的淡影/伪影。

## 原始请求

1. 用户原话: 「WEBUI整组移动保存路径双排显示伪影错觉: 双排显示下上方的路径颜色浅, 远看像下方路径的伪影, 像近视错觉, 需要修改, grilling」。
2. 要求走 grilling 逐轮拍板, 不接受直接改代码。
3. 第三轮追加: Q6 先做视觉示例再选, 并另加「上排斜体」候选。
4. 边界: 按 Q10 授权执行, 不 commit/push。

## 思考过程与决策

- 事实核查: 浅色唯一来源 `row_lang.css` 的 `.rl-scope .rel-pa { opacity: .55 }`; 两排同为 11px 等宽与 `currentColor` 状态色, 上排 A = `relocate.src`(与原 save_path 同值)、下排 B = `relocate.dst`, 文本高度相似。计划 `26-11-07-2344` D6 拍板「上暗下亮」, mockup 与 `conventions/webui.md` 三处一致 —— 是刻意设计而非 bug。
- grilling 三轮拍板(Q1-Q13): Q1 保留 D6 语义只换实现手段; Q2 不改内容、纯表现层解决; Q3 授权面 = CSS 单点 + 口径回写 + 1 条守阵, 不动 DOM/JS/四皮肤令牌; Q4 范围只锁 `.rl-scope` 行内双排, 浮窗 `--path-src` 与四皮肤不碰; Q5 验收 = 机械断言防回归 + 用户真机截图目检; Q7 `rel-pulse` 不动; Q8 历史计划原 D6 行保留、追加修订行; Q9 正反双断言 + 红验先行; Q10 授权 DoD 立档/基线/坑档与评审, 不提交。
- Q6 示例五组(现状 / A 删除线 / B 上排斜体 / C 删除线+斜体 / D 等亮无装饰) + 「远看模拟」开关。判定: 等宽字体 italic 多为合成 oblique, 11px 发虚且骨架不变, 仍像歪掉的影子; 删除线是形状差异, 不可能被读成残影。用户「按推荐」= 选 A。相关计划路径: `memory-bank/plans/26-11-07-2344-plan-relocate-status-display.html` 新增 D18(D6 部分修订)。
- Q11 口径修订不算语义翻案(上=当前/下=目标、状态色唯一载体全保留); Q12 措辞逐字按默认; Q13 共识达成开工。

## 实现计划

1. 红验先行: `tests/test_webui_relocate_visibility.py` 新增正反双断言用例 + docstring 清单, 对旧 CSS 跑红。
2. 双验: 只去掉 `opacity` 再跑一次(白名单断言红), 证明两条守阵都不是死断言。
3. 改 `row_lang.css` `.rel-pa` 为 100% 不透明 + `text-decoration: line-through`, 同步注释块口径, 跑整份测试转绿。
4. 回写 `conventions/webui.md`、计划 D18 修订行 + `kb.bump`、mockup 视觉规格单点四条规则与头部修订标记。
5. 分批评审(code-review skill) + `test.full` 全量闸门。
6. DoD: 新坑档 + `kb.index`、本档案、基线切片、`kb.wrap`、`kb.check`。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 正反双断言 + 旧 CSS 红验 | Done (2026-11-10) |
| 2 | 只去 opacity 的白名单红验 | Done (2026-11-10) |
| 3 | CSS 单点改删除线 + 注释, 整份测试转绿 | Done (2026-11-10) |
| 4 | 口径三处回写 + kb.bump | Done (2026-11-10) |
| 5 | 分批评审 + test.full | Done (2026-11-10) |
| 6 | DoD 收尾(坑档/基线/切片/自查) | Done (2026-11-10) |

## 进度日志

### R0 · 立档 (2026-11-10)

grilling 三轮拍板 Q1-Q13(用户逐轮「按推荐」), Q6 附五组可切换远看模拟的视觉示例; 已完成步骤 1-4: 红验双验留痕(旧 CSS 反断言红 / 只去 opacity 时正断言红 / 最终态单文件用例转绿), CSS 单点改删除线, 口径三处回写, 新坑档 `pitfalls/web-ui/opacity-tier-ghosting.md` 经 `kb.new task --refs` 双向补链。评审与全量闸门、DoD 剩余项随本专题入库。真机观感按 Q5 由用户截图目检(纯静态 CSS + 桩可验, 不属真机轨强制准入)。

- 2026-11-10 08:45 grilling 三轮拍板 Q1-Q13: 上排删除线替代 opacity 分层; 红验双验留痕 + 只读评审零发现 + 全量绿(见 kb.baseline); 计划 D18/新坑档/基线切片入库, 真机观感按 Q5 由用户截图目检

### R1 · 提交闸门清障 (2026-11-10)

用户说「提交」后, `ship.commit` 的 HTML 规范级增量检查(v.Nu)报 70 条 error, 全部来自 `plans/attachments/relocate-status-display-v2-mockup.html`(同批计划 HTML 零错误); 对 HEAD 原始版跑同一校验同样 70 条、类型逐条一致 → 100% 预存债务, 与本批改动无关。该件 11-08 由 `8a55701e` 以新建文件身份入库(无 doctype/head, `<style>` 在 `<div id="rsd">` 内), 增量闸门取已跟踪 diff 故当时漏检, 今天首次作为已跟踪文件被修改而翻出。

经 AskUserQuestion 显式扩范围, 用户选 B「修 mockup 本体」(未选「改校验脚本加片段豁免」): 补 doctype/html/head/title、`<style>` 归 head、`<div id="rsd">` 移入 body、皮肤切换栏补 `role="group"`、末尾闭合 body/html; CSS 规则(除本批既定的 4 条删除线回写)与整段 JS 一字未动。实测: v.Nu 增量 2 文件零 error、L1+L2 零命中、真实浏览器 6 行渲染 + 上排 `line-through`/`opacity:1` + 皮肤切换生效 + 零 pageerror; 增量只读评审零发现, 全量闸门与 `kb.check` 重跑全绿(数字见基线切片)。
