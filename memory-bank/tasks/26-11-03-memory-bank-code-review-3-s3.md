# 26-11-03-memory-bank-code-review-3-s3 — 全量代码评审第三轮 S3（B5 前端实质评审 + B6 拆分等价核验）

**Status:** Done
**Added:** 2026-11-03
**Updated:** 2026-11-03
**Summary:** 全量代码评审第三轮 S3：B5 前端逐文件过目（含 flux CSS 全量扫描）+ B6 四组 R12 等价核验 + config_rules 契约对照；B5 覆盖已闭合，发现全部入池
**Topics:** memory-bank-code-review-3-s3
**Refs:** memory-bank/plans/26-11-03-0557-plan-full-code-review-3.html, memory-bank/tasks/26-11-03-memory-bank-code-review-3-s1.md, memory-bank/tasks/26-11-03-memory-bank-code-review-3-s2.md, memory-bank/tasks/26-11-03-memory-bank-code-review-3-s4.md

## 原始请求

1. 执行第三次全量 code review 计划的 **S3 步骤**（B5 前端实质评审 + B6 拆分等价核验），范围 `bf9920d3..812ad785`；评审阶段**零代码改动**。
2. 开工跑 `commands run my-commit-flow.sync`，把「已同步 <hash>」贴进回复；只动 clone1。
3. B5 按 plan 五步评审法**逐文件过目（不得抽样）**，凭 R1–R11 + R13 前端性能与渲染证据；四皮肤验加载序、挂载名、层叠序、CSS 特异性；性能结论要有实测或可复现判据。
4. B6 按 S1 附录 C 配对表逐对做 R12 等价核验（R1 10→48、R2 25→110、R3 4→11、R4 8→23），含区间改动的目标扩大核验（S2 点名 `tests/test_transfer_targets_editor.py`）。
5. 前端验证用 `dev.e2e-check`、`dev.e2e`（必要时 `dev.ui-map`）；禁止占用 8155 端口。
6. 真实问题当场 create-issue 入池；同类连续 >5 条合并。
7. 过程与发现写进本步 task 文档；计划文档不写流水，只推进 S3 状态。
8. 收尾按 DoD（`kb.wrap`/`kb.index`/`kb.check`），然后单独提交推送本步文档（`.git/COMMIT_MSG_AI.txt` + `ship.commit` + `ship.push`）。
9. **发现 P0/P1 立即停下单独报告，不要等整步跑完。**
10. 第二轮指令：S3 就地收尾，不继续评审、不改代码——把两条已确认发现入池、把已有成果落盘本档（含未完成项与续接点）、kb 收尾后单独提交推送。明确不做：修 P1、改 `src`、动计划正文流水。

## 思考过程与决策

- **零代码改动**：本轮只写 task 档与 issue 报告、跑只读探针；`src/`、`tests/` 一行未动。
- **B5 方法**：先按 S1 附录 B 清单逐文件读区间 diff（新增文件读全文，存量读上下文）；子代理两次只回「代码片段」不落结论，故放弃委派，全部自读 + 运行时探针取证，符合「不得抽样」。
- **B6 方法**：Python 侧用 `ast.dump` 对 def/class/assign 建多重集比对（忽略注释/docstring 位置差异）；JS/CSS 侧去注释后做行级多重集 + LCS，并单独校验切片加载序单调性。脚本临时放 `%TEMP%\cr3_s3`，不入库。
- **P1 处置**：`S3-P1-01` 属行为缺陷（窗口化坐标系错判），按第 9 条立即停下报告；用户决定「就地收尾、不修」→ 入池并留为续接点，未改 `src`。
- **HEAD e2e 断裂**：`dev.e2e` 全量在 import 阶段失败，根因是窗口外 `47a61c7c` 改 `harness.mjs`（`BASE_URL` → `baseUrl()`）而未同步区间内新 spec；区间终点 `812ad785` 处正常，判为**窗口外回归**，入池不修。
- **e2e 回收口径**：全量入口不可用，改用显式 spec 列表跑定向用例，结果作为本步前端验证证据。
- **未入池候选**（未确认到 P 级、证据不足，仅备查）：`drawer_tpl` 的 `filesSig` 用 `(h*31 + f.progress) | 0` 截断小数，progress/availability 小数变化不进签名，框架脚统计可能滞留；`flux/fx-mount.js` 的 `rows()` 每次全量 diff 且 `rowNode` 逐 key `querySelector`，大规模切换站点近似 O(N×DOM)。

## 实现计划

1. 同步 + 读计划/S0/S1/S2 底册与坑档入口。
2. B5：四皮肤 19 文件 → shared JS/CSS → drawer_tpl/tpl → 8 个根文件，逐件过目；四皮肤加载序/挂载名/层叠序/特异性核对。
3. B6：R1/R2/R3/R4 四组配对，源对目标多重集比对 + 覆盖率补齐（残留根文件计入目标）。
4. R13：性能与渲染证据（行窗口化 DOM 规模、rowsFn 耗时、折叠/滚动 longtask）。
5. 前端验证：`dev.e2e-check` + 定向 e2e 列表回收。
6. 发现入池（create-issue，standard 档），并做 Open 去重。
7. 就地收尾：本档落盘 + `kb.wrap`/`kb.index`/`kb.check` + 单独提交推送。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S3-0 | 同步 + 底册/坑档入口 | Done(2026-11-03) |
| S3-1 | B5 四皮肤 + shared + 结构件逐件过目（含 flux CSS 全量、`config_rules.js` 深读） | Done(2026-11-03)，覆盖闭合 |
| S3-2 | B6 四组 R12 等价核验 | Done(2026-11-03) |
| S3-3 | R13 性能与渲染证据 | Done(2026-11-03) |
| S3-4 | 前端验证（e2e-check + 定向 e2e） | Done(2026-11-03)（全量入口断裂已入池） |
| S3-5 | 发现入池 + Open 去重 | Done(2026-11-03)，本步共 5 条（2+3） |
| S3-6 | 收尾（本档 + kb + 提交推送） | Done(2026-11-03) |
| S3-7 | 续接评审（flux CSS 全量 / `config_rules.js` 深读） | Done(2026-11-03) |
| S3-8 | `S3-P1-01` 认领与修复 | Open（需用户指派） |

## 进度日志

### R0 · 立档与 S3 就地收尾 (2026-11-03)

- 开工同步 `commands run my-commit-flow.sync` → 已同步 `d1c8f261`（远端领先 9 笔，重叠 2 处均为生成物，已自动重跑）。
- B5 逐文件过目完成主体：四皮肤 19 文件（atlas 4 / console 4 / flux 7 / prism 4）、flux 预读、shared JS 19、CSS 3（`row_lang.css`/`dt_table.css`/`hscroll.css`）、`drawer_tpl` 5、`tpl` 8、8 个根文件；四皮肤加载序与挂载名一致，层叠序与 CSS 特异性无新增冲突。清单见附录 B。
- B6 四组等价核验完成，全部 `missing=0 / drift=0`；明细见附录 A。
- R13 实测：dt10 prism 常驻 24 行 / 302 节点、rowsFn max 1.1ms mean 0.95ms；dt11 25 行 / 367 节点、rowsFn max 5.6ms mean 4.19ms；K2 折叠 longtask 0ms、mut 29、padH 33213→0→33213、滚动 maxGap 50ms、>100ms 帧 0/40。
- e2e：`dev.e2e-check` 通过；全量 `dev.e2e` 在 import 阶段失败（`BASE_URL` 未导出，4.9s），已按窗口外回归入池；改用显式 spec 列表回收，**148 passed / 16 skipped / 0 failed**（6.6m，端口 64611）。
- 发现入池 2 条（均 standard，状态 Open）：
  - `memory-bank/issues/26-11-03-1035-bug-webui-group-window-source-mismatch.html` — `S3-P1-01`，group 视图窗口化坐标系错判；
  - `memory-bank/issues/26-11-03-1035-test-e2e-harness-baseurl-import.html` — HEAD 上全量 e2e 断裂。
- **停止原因**：命中 `S3-P1-01`（P1），按原始请求第 9 条立即停下报告；用户拍板「就地收尾、不修 P1、不继续评审」。因此 flux 皮肤 CSS 全量与 `config_rules.js` 深读未做，属**有意保留**的未完成项（附录 C）。
- 收尾 DoD：`kb.wrap` / `kb.index` / `kb.check` + 本档单独提交推送（S3-6）。

### R1 · 补完 flux CSS 全量与 config_rules 契约对照 (2026-11-03)

- **flux CSS 全量扫描闭合**：按 `flux/index.html` 实际加载序过 14 个 CSS 文件（flux 自有 5 个 / 177 KB + shared 9 个 / 173 KB，约 350 KB、5277 条声明）。逐条做「选择器 → 特异性 → 声明位置 → 胜出者」计算；4 处 `!important` 全部有明确兜底用途；344 个变量定义/引用全部可解析（`--head-h` 由 JS 注入并均带 fallback）；`@keyframes` 无跨文件重名。
  - 跨文件同名同属性冲突 33 处，逐条判定：媒体查询内的响应式覆盖（`.topbar`/`.status-strip`/`.hb-row` 等）与 `html[data-fx-preset] :is(...)` 的提权覆盖均**有意为之且胜出**；`to/from/0%` 与 `:is()` 逗号拆分属扫描器伪差异。
  - 唯一真问题：`.ce-page` 移动端内边距被后加载的 `dialogs.css` 同特异性规则恒覆盖（P3）→ 已入池。
  - 复用/覆盖关系：flux 不重定义 shared 的结构性选择器，只通过 `html[data-fx-preset]` 提权层做主题化；shared → flux 的 token 借用完整，无未定义且无 fallback 的变量。
- **`config_rules.js` 契约对照**：与 `config/compat.py` 的 `normalize_legacy_rule` / `normalize_action_entry` / `normalize_choose_block` 逐分支比对——扁平动作→规范形、单键提升、`choose` 保留未知键、`when` 列表包 `all`、`on_error` 缺省注入、退役伪动作跳过注入，**语义等价**；`String(value)` 写数值与全 UI 的字符串标量约定一致，后端 `int()/float()` 校验与引擎 cast 均可接受。
  - `on_error`：默认值 `{policy: stop, retries: 3, backoff: 60}`、prune-if-default 与后端 normalize 注入等价；无契约偏差。
  - 退役键：**发现真问题**——`retired_control_keys_in` / `disable_retired_rule_spec` 与前端 `cfgRuleRetiredKeys` 均只扫顶层 `actions`；`choose.then/default` 内的 `ignore_next_action_error` 校验放行但未被剔除，`Rule` 构造抛 `ConfigError`（已用探针复现）→ 已入池（P2）。
  - 契约一致性另记一条：JS 规范化是 Python 的手抄镜像，无跨语言对拍守卫（R10）→ 已入池（test/light）。
- 本步新增 3 条 issue（累计 5 条），B5 全量覆盖闭合，无 P0；P1 仍待指派。

## 附录 A · B6 拆分等价核验（R12）

方法：Python `ast.dump` 逐 def/class/assign 建多重集；JS/CSS 去注释行级多重集 + LCS；切片加载序单独校验。源侧为拆分前文件，目标侧为拆分后切片集合（含残留根文件）。

| 组 | 源文件数 | 目标切片数 | 核验节点/行数 | 缺失 | 漂移 | 备注 |
|---|---|---|---|---|---|---|
| R1 | 10 | 48 | AST 1170 | 0 | 0 | 重复名 1 个（ROOT），目标侧数量保持 |
| R2 | 25 | 110 | AST 1696 | 0 | 0 | 重复名 9 个，目标侧数量保持 |
| R3 | 4 | 11 | AST 0 / 0 | 0 | 0 | JS 0 丢失，仅新增 2 行 `importScripts`；target-only `_SCRIPTS_DIR` 良性 |
| R4 | 8 | 23 | 行级 | 0 | 0 | CSS 0 丢失 / 0 新增；加载序单调（layout 309 < controls 619 < panels 1133） |

- 覆盖率修订：初版仅比对切片，残留根文件（`columns.js`/`background.js`/`qb_capture.py` 等）漏计造成误报；把拆分的 M 文件新版本加入 targets 后，四组均 `missing=0`。
- 区间改动目标扩大核验：`tests/test_transfer_targets_editor.py`（S2 点名）纳入 R2 目标集，AST 比对 `missing=0 / drift=0`。
- 脚本缺陷自纠：初版把 `(lineno, dump)` 元组整体入多重集，比较时取错位导致 1170 条伪漂移；改为只存 dump 后归零。

## 附录 B · B5 已过目清单

| 类别 | 数量 | 内容 |
|---|---|---|
| 四皮肤入口 | 19 | atlas 4 / console 4 / flux 7 / prism 4（`index.html` + 皮肤 JS/CSS 挂载） |
| flux 预读 | 1 组 | `flux/fx-mount.js`、`fx.js`、皮肤 CSS 装载链 |
| shared JS | 19 | 含 `columns.js`/`columns_grid.js`/`transfer_*.js`/`console_hub_*`/`hscroll` 相关 |
| CSS（初轮） | 3 | `row_lang.css`、`dt_table.css`、`hscroll.css` |
| CSS（全量补扫） | 14 | flux 自有 5 个（`style.css` 9.8 KB、`components.css` 56 KB、`views.css` 38.6 KB、`dialogs.css` 46.5 KB、`fx-mount.css` 26.4 KB，合计 177 KB）+ shared 9 个（`console_hub*` 四层、`row_lang`、`hscroll`、`dt_table`、`fx.css`、`fx-presets.css`，合计 173 KB） |
| `drawer_tpl` | 5 | `10-content-tree-detail-tall.js`、`11-content-treegrid-batch-low.js` 等 |
| `tpl` | 8 | 含 `rule-tree.html`（条件树/编排）与 `ctx-menus.html`（通用 submenu） |
| 根文件 | 8 | 区间内新增行合计 221 行 |

核验要点（均通过）：

- 四皮肤均加载 `transfer_targets.js`、`transfer_flow.js`、`console_hub_*` 三片、`hscroll.css` 与新模板，顺序与源文件区段一致。
- 挂载名统一走 `Object.assign(window.AQB_X.methods, {...})`，无重复键覆盖。
- `tpl/rule-tree.html` 仅 `{{ }}` 文本插值与 `:value`，无 `v-html`（R8 通过）。
- 层叠序：layout < controls < panels 单调；新增选择器未越级覆盖既有皮肤规则。
- `drawer_tpl` 的 `rowMem`/`filesSig` 记忆化在同帧内可复用；`filesSig` 位运算截断小数属**候选未确认**（见「思考过程与决策」）。

**flux CSS 全量扫描结论（覆盖闭合）：**

- 规模：按 `flux/index.html` 真实加载序过 14 个文件、约 350 KB、5277 条声明；选择器级做了「特异性 → 声明位置 → 胜出者」全量计算，非抽样。
- 特异性与层叠：无 `#id` 选择器；4 处 `!important` 均为移动端/降级兜底；`html[data-fx-preset] :is(...)` 统一用 `(0,2,1)` 提权做 flux 主题化，故意压过 shared 的 `(0,1,0)` 同名规则，胜出方向正确。
- 跨文件同名同属性冲突 33 处：媒体查询内的响应式覆盖（`.topbar`/`.status-strip`/`.hb-row`/`.site-chip` 等）与主题提权覆盖均有意为之；`to/from/0%` 与 `:is()` 内逗号属扫描器伪差异，人工复核排除。
- 变量与复用：344 个变量定义/引用全部可解析；`--head-h` 由 JS 注入且引用处均带 fallback；flux 不重定义 shared 的结构性选择器，token 借用完整。
- 动画：`@keyframes` 无跨文件重名，无后加载覆盖导致的前段动画失效。
- 唯一真问题：`.ce-page` 移动端 padding 被 `dialogs.css` 后置同特异性规则恒覆盖（P3）→ 已入池。

## 附录 C · 未完成项与续接点（已闭合）

**原两项未完成已补完并闭合：**

1. ✅ **flux 皮肤 CSS 全量**：选择器/特异性/层叠序/复用与覆盖关系已扫完（见附录 B），结论「无 P0/P1，1 条 P3 已入池」。
2. ✅ **`shared/config_rules.js` 深读**：`on_error` 语义、退役键、前后端契约已对照 `config/compat.py`；语义等价，1 条 P2（嵌套退役伪动作）+ 1 条 test 缺口已入池。
3. ✅ 定向 e2e 已回收（148 passed / 16 skipped / 0 failed，64611）；全量门禁恢复仍作为 issue 待认领。

**本档闭合后仍开放的事项（不在 S3 范围内修）：**

1. `S3-P1-01`（group 窗口化坐标系，P1）待用户指派后认领。
2. `webui-config-normalize-parity-gap`（test/light）待认领。
3. `rules-choose-nested-retired-control`（bug/standard，P2）待认领。
4. `webui-flux-ce-page-media-cascade`（bug/standard，P3）待认领。
5. HEAD 全量 `dev.e2e` 门禁恢复（`BASE_URL` → `baseUrl()` + import-smoke 守卫）待认领。

## 附录 D · 本步新增 issue

1. `memory-bank/issues/26-11-03-1035-bug-webui-group-window-source-mismatch.html` — bug/standard（P1）：`WIN_SOURCES.group` 为 `Object.assign` 克隆，`_winSrc(kind) === WIN_SRC_DOC` 恒假 → 抽屉关时 group 窗口化不启用、抽屉开时按抽屉滚切片。三锚 `columns_grid.js:461-465` / `columns.js:49-79` / `tests/webui_dom_page_support.py:483-484`（取证 2026-11-03 10:20）；引入 `e6b02991`，拆分 `20a74274` 原样保留。
2. `memory-bank/issues/26-11-03-1035-test-e2e-harness-baseurl-import.html` — test/standard：`e2e/search-uncovered-no-duplicate.spec.mjs` 静态导入 `BASE_URL`，`e2e/harness.mjs` 已由窗口外 `47a61c7c` 改为 `baseUrl()`；区间终点 `812ad785` 正常，属窗口外回归。建议 spec 改 `baseUrl()` + 加 import-smoke 守卫。
3. `memory-bank/issues/26-11-03-1120-bug-rules-choose-nested-retired-control.html` — bug/standard（P2）：`choose.then/default` 内 `ignore_next_action_error` 未被退役检测/剔除，校验放行后 `Rule` 构造抛 `ConfigError`。三锚 `rules_mod.py:53-93` / `validation/rules.py` 的 `_validate_action_entry` / `rules/base.py` 的 `_build_action_steps`；探针输出 `retired_keys=()` + `Rule raised: ConfigError`（取证 2026-11-03 11:18）。建议递归检测/剔除或校验前置拒绝，并补 then/default 用例。
4. `memory-bank/issues/26-11-03-1120-bug-webui-flux-ce-page-media-cascade.html` — bug/standard（P3）：`views.css:133` 的 `@media(max-width:900px) .ce-page` 被 `dialogs.css:482` 同特异性后置规则恒覆盖。三锚 `views.css:133` / `dialogs.css:482` / `flux/index.html:15,20`（取证 2026-11-03 11:22）。建议基础 padding 提前层或移动端覆盖并入 dialogs 媒体块，四皮肤一并评估。
5. `memory-bank/issues/26-11-03-1120-test-webui-config-normalize-parity-gap.html` — test/light：`config_rules.js` 与 `compat.py` 两套归一实现无同输入对拍守卫。锚 `config_rules.js` 的 `cfgNormalize*` / `compat.py` 的 `normalize_*`（取证 2026-11-03 11:20）。建议共享 fixtures 跨语言对拍，或退役前端镜像。

去重：5 条分别覆盖 `webui-windowing`、`e2e-harness-port`、`rules-choose-retired`、`webui-css-cascade`、`webui-config-contract` 五个专题，与既有 Open/Done issue 无同锚点重复（`26-10-01-2211-refactor-rules-keys-semantics-review` 只覆盖顶层退役键，未覆盖 choose 嵌套，已在新报中引用为相关背景）。

## 附录 E · 交给 S4 的输入清单

1. **B7/B8 清单口径**：沿用 S1 附录 B 的 B7（工具链/scripts）与 B8（变更函数）范围；`claims_gate.py` 现由 `validation/rules.py` 的 `_validate_action_entry` 与 `rules/base.py` 的 `_build_action_steps` 双向守护，S4 读码时按 R11 核对 choose 分支。
2. **待验证的前置结论**：`compat.py` 归一与前端 `config_rules.js` 语义等价（不含嵌套退役键）；`.ce-page` 是唯一 CSS 级联真问题，其余 32 处冲突已判定为有意覆盖。
3. **可复用的只读资产**：`%TEMP%\cr3_s3\css_audit2.py`（级联扫描）、`kf_audit.py`（keyframes 重名）、`probe_nested_retired.py`（嵌套退役键复现）；均为临时脚本，不随提交入库，需要时可按附录锚点重写。
4. **开放 issue 交接**：`S3-P1-01`、`rules-choose-nested-retired-control`、`webui-flux-ce-page-media-cascade`、`webui-config-normalize-parity-gap`、`e2e-harness-baseurl-import` 均保持 Open，S4 不认领、只按需引用。
5. **测试基线引用**：本轮定向 e2e 数字与性能数字仅作本档记录，不抄进基线；S4 的全量测试数字以 `commands run kb.baseline` 为准。

- 2026-11-03 10:41 S3 就地收尾：B5 主体过目 + B6 四组 R12 等价(0/0) + 定向 e2e 148p/16s + 入池 P1 与 e2e 断裂两条, 留 flux CSS/config_rules 续接

- 2026-11-03 11:24 补完 flux CSS 全量扫描(14 文件/350KB/33 冲突逐条判定)与 config_rules 契约对照, B5 覆盖闭合, 新增 3 条 issue, 状态转 Done
