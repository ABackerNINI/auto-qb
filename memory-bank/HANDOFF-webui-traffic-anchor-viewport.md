# 交接文档: 流量图尾锚显式视口重构(计划 26-11-22-0858)

> ⚠ 本档为 2026-11-22 会话中断时点的快照, 任务已收口(计划 26-11-22-0858 翻 Done): 现状以 memory-bank/tasks/26-11-22-webui-traffic-anchor-viewport.md 为准, 交接分支已 rebase 到本地 develop 顶待合流。下文「不要合入 develop」「ship.commit 未执行」「复评轮 4 未派」等表述均已过时, 仅作历史快照保留。

> **交接时间**: 2026-11-22(会话 token 耗尽中断)
> **分支**: `webui-traffic-anchor-viewport`(已推远端, commit = WIP 中间态; **不要合入 develop**, 重构验收完成后由用户拍板合流方式)
> **基础**: develop @ 8ff76f0b(远端最新, 含 relocate 专题 S4 收尾)
> **一句话现状**: 三不变量几何核心已全量落地, 电池/e2e 换代后全绿(test.quick 6793P + 流量 e2e 69P), 评审已走 3 轮(轮1 三分面 17 发现全过检 → 轮2 复评 9 发现 → 轮3 复评 10 发现全是注释残留级), 轮 3 的注释清理已做完但**复评轮 4 未派、评审包未取、test.full/基线切片未重跑、ship.commit 未执行**。

## 0. 必读(按序)

1. `memory-bank/plans/26-11-22-0858-plan-webui-traffic-anchor-viewport.html` — 重构计划(三不变量/退役清单/分期/风险)
2. `memory-bank/tasks/26-11-22-webui-traffic-anchor-viewport.md` — 任务档案(R0 立档/R1 实施/R2 评审修复轮, 子任务表)
3. `memory-bank/conventions/attachments/webui-traffic-beat.md` 文末「尾锚显式视口换代收口 (2026-11-22)」节 — 现行权威契约
4. `memory-bank/pitfalls/web-ui/traffic-implicit-viewport.md` — 结构根因坑档(判别三信号/处置口径)
5. code-review skill(`.agents/skills/code-review/SKILL.md`) — 评审纪律(本轮已走到修复轮 3)

## 1. 重构内容(已落地, 勿回退)

### 三不变量(替代三轮压缩补丁的结构性方案)

1. **视口恒等式**: `viewport = [anchor − span_s, anchor]`; anchor = 末样本时刻、跨拍单调(`anchorTo = max(st.anchor, 新尾)`); **auto x range 全窗退役** —— 四个 setData 写点(快路判定帧/收敛帧/_qbChartRescale/_qbPreviewEnd)后都**必须**显式 `setScale("x", 锚视口)` 重申, y 成对钉档。
2. **单列恒等**: store 列 == 显示列。退役件: `_qbRollJudge`/`_qbPadTailColumns`/`_qbInheritedViewport`/`_qbBeatVpRem`/`u._qbPad` 记账/悬停索引扣减/收敛帧 slice。列不变量 = `[锚 − (span_s+margin), 锚]`, margin = 2×组距; **修剪线锚 = 视口锚优先、尾点回落**(`_qbTrimStaleHead` 第三参 anchorT; `_qbStreamOnLoad` keepLine 同锚优先)。
3. **取数有效性**: `_qbLoad` 发射时快照 `const w0 = this[def.window]`(先于 await), 成败两路 stale 判据都带 `this[def.window] !== w0`(换窗竞态根除)。

### 新纯函数三件(模块级, node 电池可跑)

- `_qbAnchorJudge(st, tail, stepNom, spanNom)` → `{anchor, delta, step, span, rewin, slide}`; rewin = step/span 变化或锚位移 > 2×组距。
- `_qbAnimAnchorAt(a)` → 在途锚现值(anchorFrom + easeOut × 位移, 末帧 ulp 吸附); 帧循环与打断续滑共用(公式漂移即回跳)。
- `_qbRetainHistory(oldPts, newPts, keepLine)` → GET 落地历史保留合并(旧列余量区真值点并入列头)。

### 判定帧核心语义(`_qbBeatStart(scope, u)` — 三参 inherited 已退役)

- 打断续滑捕获**先于** `_qbBeatCancel`: `anchorHold = animPrev.needsShift && animPrev.preview === undefined ? _qbAnimAnchorAt(animPrev) : null`。
- `anchorPrev = anchorHold ?? anchorTo − delta`; `disp = anchorTo − anchorPrev`(恒 ≥ 0)。
- `slide = !reduce && !rewin && disp > 0 && haveVp && _qbFxShiftGate(cfg, u, nWin)`(nWin = round(span/step)) —— **reduce 分量在 slide 判据内**(否则 reduce 拍视口滞留滑动起点, 电池 S5 钉面)。
- 显式视口**无条件落笔**(haveVp 时): `setScale("x", {min: vAnchor − span, max: vAnchor})` + y 钉档, 含零变化/reduce/instant 拍。
- 滑动 = 锚平移(anchorFrom → anchorTo, min/max 两缘同步); 打断从在途锚续滑; rewin 瞬时落地。

### 退役清单(反向钉在电池静态钉 k, 回潮即红)

`_qbRollJudge` / `_qbPadTailColumns` / `_qbInheritedViewport` / `_qbBeatVpRem` / `_qbPad`(全部记账与调用面)。dx0/dxN 双锚分离记账 → 单锚 disp。

### e2e 换代要点(e2e/traffic-*.spec.mjs)

- **所有采样器/桩 meta 必须带 `span_s`**(旧形状桩缺它 → st.span 回落列宽 → 泵追加列宽增长 → min=anchor−span 回缩 → 刻位回跳, grid-stability 曾因此红)。
- e2e 采样器字段: `dx0/dxN` 已改读 `(anchorTo − anchorFrom)`(拍位移); 过滤器加 `shift`(slide 拍才有 glide 语义; rewin/gate 拒绝拍 disp>0 但瞬时落地)。
- A4 点数断言从「逐拍 +1」改「有界(窗内+余量)」; 首末刻位允许 ≤2s 细化凹口(uPlot 密度切换, 真 pop 掉 30s+ 仍拦)。
- A2 翻动拍签名改行为语义: flipA = `shift===false && dx0===0`(零位移瞬时), flipB = `shift===true && dx0>0 && 双缘≥半格`(位移一格滑动); script 桩 span_s = 常量 `(n0−1)×iv`(不随形变)。

## 2. 测试现状

- `commands run test.quick` → **6793 passed, 2 skipped** 全绿(最后一次实跑在格式化后)。
- `commands run test.full` → 上一版树跑过 6789P(基线切片 26-11-22-1117 已按那次数字誊写); **修复轮 3 之后未重跑**, 交接后需重跑并核对基线切片数字(若变了要改切片或重建)。
- e2e 流量系(grid-stability 5 + fx-frames 17 + stream 3 + fx-anchor 6 + fx-panel + source-switch + gap-zones) → **69 passed** 全绿(修复轮 3 e2e 复跑在列; fx-frames/grid 的最终注释清理后仅 node --check + fx-frames/grid 两 spec 复跑过 22P, 全量 69P 是注释清理前一轮)。
- 红验: 停用收敛帧重申行 → S20b 即红(变异盲区封堵有效)。

## 3. 未完成事项(交接后按序做)

1. **全量复跑**: `commands run test.quick` → `commands run test.full`(带覆盖率), 数字与基线切片 26-11-22-1117 比对, 变了就更新切片(数字只写切片一处)。
2. **e2e 全流量终验**(修复轮 3 最后的注释清理后只跑过 2 spec): `commands run dev.e2e`(全量集;spec 子集 = 同引擎按 spec 路径过滤的形态, e2e/ 子目录跑缺 UI_HARNESS_PORT 注入,baseUrl() 直接抛错、用例全红(必须仓库根跑))。本次子集 = traffic-grid-stability / fx-frames / stream / fx-anchor / fx-panel / source-switch / gap-zones 七 spec, 预期 69 passed。
3. **复评轮 4**:`commands run review.pack`(先 `commands run my-commit-flow.sync` 齐平 + `commands run ship.gate` 预跑), 派只读子代理(分面档 2-3: 正确性/安全/测试缺口, **串行派遣** —— 并发会撞上限)。轮 3 复评的 10 条发现已全部修完(注释面), 轮 4 应零发现或仅剩吹毛求疵; 若新发现按 code-review skill ⑤ 处置循环。
4. **archive/切片/计划状态翻正**: 任务档案子任务表行 4(提交)与 6(收尾)状态; `commands run kb.wrap --topic webui-traffic-anchor-viewport --did "..."` 抬切片。
5. **真机冒烟**(计划 S3 项; qB 真执行类): `commands run dev.run -- config.yml --dry-run` 先干跑, 然后 dev.webui 或浏览器自动化开 1m 窗观察 ≥5 分钟(含 30s 对账撞拍、换窗对比 1m↔5m↔1m、切页往返), 验收 = 视口跨度恒等于名义窗、无压缩无左缺口。qB 离线则按 `testing/real-machine.md` 口径记豁免理由。
6. **提交**: `commands run ship.commit`(消息写 `.git/COMMIT_MSG_AI.txt`, gitmoji + 中文首行; trailer 必须带 `Review: webui 流量图尾锚显式视口 · <N> 行 · blocker 0 · 修 <M> · 入池 1 · 检 P/T · 轮 3 · 基 <review.pack 基哈希> · 派发 3`; 行数与基哈希以提交前最后一次 `commands run review.pack` 实算为准)。**当前分支是 webui-traffic-anchor-viewport, 不是 develop** —— commit 会提到本分支并推远端; 是否合入 develop 由用户拍板(重构验收 + 真机冒烟通过后)。
7. **入池件**: `memory-bank/issues/26-11-22-1401-bug-traffic-anchor-transient-gap.html`(锚领先尾 > 2 组距瞬态左缺口, Open)保持 Open, trailer `入池 1` 即指它。

## 4. 已知风险与边角(勿当新 bug 重查)

- **瞬态左缺口**(入池 issue 26-11-22-1401): 锚领先尾 > 2 组距的连续滑动段, 左缘可瞬态超出数据头(间歇自愈)。主干已修(修剪线锚优先), 残余极端形留 issue。
- **uPlot 密度切换**: 连续滑动下首/末刻位可瞬时吐 1 个更细刻位(≤2s), e2e 已放宽容差; 真 pop(掉 30s+)仍拦。
- **A2 翻动拍签名**: 点数 ±1 被余量列修剪线吸收, 签名改行为语义(flipA 零位移/flipB 位移一格); 旧点数签名退役。
- **fx spawn pxPerT**: 改按名义 span_s(列含余量后列跨度 ≠ 窗长); e2e fx-frames F9 撕裂带已验证。
- **cap 债务**: `doc.caps` 报 17 项(含 real-machine.md 8288>8000), **与本批无关的存量债务**, 提交不拦; 需另开会话清理。

## 5. 关键文件与行号锚点(2026-11-22 版, 行号会漂, 用 grep 词重定位)

- `src/auto_qb/webui/static/shared/qb_traffic_chart.js`(主改 ~4200 行):
  - `_qbAnchorJudge`/`_qbAnimAnchorAt`/`_qbRetainHistory`(模块级纯函数区, grep "锚视口判定单点")
  - `_qbBeatStart(scope, u)`(grep "判定帧开工") — anchorHold 捕获/judge/记账/slide/显式视口落笔
  - `_qbBeatFrame` L0 块(grep "L0 锚平移") / `_qbBeatConverge`(grep "收敛帧") / `_qbChartRescale`(grep "y 轴重排")
  - `_qbStreamFrame` 修剪(grep "保留窗头部修剪") / `_qbStreamOnLoad`(grep "历史保留合并") / `_qbLoad`(grep "w0 = this")
  - `_qbFxSpawn` pxPerT(grep "pxPerT") / setCursor 直通(grep "hoverIdx") / `_qbSummaryOf`(grep "窗内桶数")
- `tests/test_webui_static_dom_panel_traffic.py`(电池 ~7300 行): BEAT_PROBE(J1-J10/L1-L9) + SCHED_PROBE(S0-S20b) + 静态钉 a-k + FXPANEL 双探针(harness 新签名) + STREAM_PROBE(A7/A7b)
- e2e: `traffic-grid-stability.spec.mjs`(3 桩 meta span_s + A4 有界 + 细化凹口) / `traffic-fx-frames.spec.mjs`(采样器 dx0/dxN=锚位移 + shift 过滤 + A2 签名换代 + 桩 span_s)

## 6. 环境备忘

- e2e 必须**仓库根**跑(`commands run dev.e2e` 全量;spec 子集 = 同引擎按 spec 路径过滤的形态;e2e/ 子目录跑缺 UI_HARNESS_PORT 注入,baseUrl() 直接抛错、用例全红(必须仓库根跑)); Docker 无 → test.linux 系改约。
- `dev.fmt` 只吃 .py(.js 是 grep 面); chart 文件禁圈号①②③(ascii_symbol_guard [circled] 冻结 0)。
- 探针调试: `_NODE_STDIN_WRAPPER` 形态(node -e eval(stdin), chart 路径 = argv[1]); 直跑本地文件要把 argv 替换成路径字面量且 polling.js 联评的探针(如 STREAM_PROBE)不能只换一处。
