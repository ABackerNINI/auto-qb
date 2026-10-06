# 26-10-06-webui-ctx-menu-viewport — 浮层菜单视口钳位: 常量估算改开层实测

**Status:** Done
**Added:** 2026-10-06
**Updated:** 2026-10-06
**Topics:** webui-row-menu-click
**Summary:** 认领 issue 26-10-06-1717(用户指派)并修复 —— `_menuPos` 以常量 h=222 估算菜单高度做视口钳位, 而菜单真实高度随分支差一倍以上(批量菜单实测 393px) ⇒ 锚点落在视口下部时菜单底越出下缘最多 171px, 底部项(标签分类/导出/批量删除)真实点击不可达(旧冒烟 W4 组选中导出段的存量 30s 超时即此, 曾被误当 flaky)。修法 = `ui_feedback.js` 新增 `_menuFit`/`_menuFitRefit`(按 offsetWidth/Height 实测重钳位, 极矮视口退化分支限高可滚), `state.js` 在 `menu`/`headMenu`/`filePrio` 三个**开层 watcher**(判据 = 对象替换, 覆盖"菜单开着又右键另一行")里 `$nextTick` 调出口, `tpl/ctx-menus.html` 三处补 ref。验证: 新 e2e 回归「挑视口下部行 → 菜单盒整体在视口内 + 真实点击底部项」修复前双皮肤红 / 修复后绿; 新静态守阵钉接线(摘 ref 红验过); 全量 e2e 82 passed + 10 skipped / 0 failed; `test.full` 见下方基线切片。
**Refs:** memory-bank/issues/26-10-06-1717-bug-webui-batch-menu-viewport-overflow.html, memory-bank/pitfalls/web-ui/overlays.md, memory-bank/testing/baselines/26-10-06-1830-webui-ctx-menu-viewport.md, memory-bank/activeContext/26-10-06-1817-webui-ctx-menu-viewport.md

## 原始请求

> 认领issue并修复: memory-bank/issues/26-10-06-1717-bug-webui-batch-menu-viewport-overflow.html

（本 clone 开工时该 issue 尚未同步到本地 —— 先跑会话协议第 1 步 `commands run my-commit-flow.sync`
快进 `4236975c→779cf088`(远端领先 13 笔, 其中一笔正是"入池三项"), 文件才到位。）

## 思考过程与决策

### 1. 为什么"把常量改大"不是修法

`_menuPos(event, w=214, h=222)` 的 `h` 只用于一件事: `y = min(clientY, innerHeight - h - 8)` ——
即"光标往下放不下就往上收"。菜单真实高度**随分支变**: 单种子菜单 14 项 / 批量菜单 10 项 /
整集整剧 6 项 / 表头菜单 5 项 / 文件优先级 4 项, 还受 `flags.skip_check_menu`(跳检项)影响。
抓到的实测值: 批量菜单 **393px**(双皮肤一致, skip-check on) —— 估算低估 171px。
只要还用常量, 换个分支或加个菜单项就会再犯; 故走**实测**。

### 2. 判据选"对象替换"而不是 `visible` 翻转

三个菜单的**开层入口有六处**(`menu.js` 的 `openMenu`/`openMemberMenu`/`openHeadMenu`、
`shows.js` 的 `openShowMenu`/`openShowEpMenu`、`drawer.js` 的 `openFilePrio`), 逐个挂调用必漏
(与 `_fitAddPop` 同族: 那里是"开层入口四处, 直挂方法会漏"的既有判据)。收成 watcher 单点后,
剩下一个岔路: 挂 `X.visible` 还是挂 `X` 本身?

- 挂 `X.visible`: **"菜单还开着又右键另一行"漏钳位** —— 右键不会触发 window 的 `click` 收层
  (浏览器对非主键只发 `contextmenu`/`auxclick`), 此时 `visible` 恒 true、只是换了锚点,
  位置变了而 watcher 不响。
- 挂 `X` 本身(**采用**): 三处开层一律写 `this.X = {…}`, 而关层与执行动作只写字段
  (`this.menu.visible = false`) ⇒ 浅 watcher 恰好**每次开层响一次**; 钳位回写的是 `x`/`y`
  字段而非整个对象, 不会自触发。

量测放在 `$nextTick`: Vue 的 DOM 补丁在微任务里跑完、浏览器尚未绘制, 所以回写 x/y 触发的那次
重渲染落在**同一帧**内 —— 用户看不到"先弹在错位置再跳一下"。这也是 `hubAsk`(config_hub.js)与
`_fitAddPop`(add_torrent.js)的既有范式, 本任务只是把它补到菜单族。

### 3. 建议修法的第二方案(无脑加 `max-height + overflow-y`)为什么只当退化兜底

`.ctx-menu` 内嵌 `position:absolute` 的 flyout 次级面板(`.ctx-sub`, 「更多操作」)。给菜单盒加
`overflow` 非 `visible` 会**裁掉**这个绝对定位后代 ⇒ 常态下就把「更多操作」废掉。故只在
**菜单比视口还高**(`h > innerHeight - 16`, 极矮视口)这一退化分支才挂限高 + 可滚 ——
那时菜单已占满视口, 子面板本来也无处可展; 且每次开层先复位(`el.style.maxHeight = ""`),
否则本次量到的是上次压过的高度(照抄 `_fitAddPop` 的第 4 条纪律)。

### 4. 未动 e2e 里那条"挑上部行"的 arrange

`menus.spec.mjs` 的 W4-组选中导出用例为了躲这个 bug, arrange 里限定 `r.bottom <= 500`。
修复后它不再必要, 但保留不影响结论(挑上部行同样是合法 arrange), 故只**改注释**记录 bug 已修 +
指向新的 CTX-fit 回归, 不改筛选条件 —— 少动一处就有少一处的对账面。

## 实现计划

| # | 文件 | 改动 |
|---|---|---|
| 1 | `shared/ui_feedback.js` | 新增 `_menuFit(el, x, y)`(实测钳位 + 退化限高)与 `_menuFitRefit(stateKey, refName)`(watcher 出口, 现读现取 + 守 visible); `_menuPos` 注释降级为"初值" |
| 2 | `shared/state.js` | `watch` 新增 `menu` / `headMenu` / `filePrio` 三个开层 watcher → `$nextTick` → `_menuFitRefit` |
| 3 | `shared/tpl/ctx-menus.html` | 三个 `.ctx-menu` 加 `ref="ctxMenu"` / `ref="headMenuEl"` / `ref="filePrioEl"` |
| 4 | `tests/test_web.py` | 新增静态守阵 `test_frontend_ctx_menu_refit_by_measured_size`(接线三向对齐 + `offset*` 实测算) + 头部「测试计划」补登 |
| 5 | `e2e/menus.spec.mjs` | 新增 CTX-fit 回归用例(挑视口下半带行 → 菜单盒在视口内 + 真实点底部项); 头注「计划外发现」段与 W4 arrange 注释同步为"已修" |
| 6 | `memory-bank/` | issue 置 Done(含复验 / 实际修法 / 测试数字) · 本档案 · `pitfalls/web-ui/overlays.md` 新条目 · `testing/guards.md` 登记 · 基线切片 · activeContext 切片 |

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| S1 | 会话开工同步 + issue 到位 | Done |
| S2 | 复验(先用 e2e 写成红: 菜单底 1063 vs 限值 892) | Done |
| S3 | `_menuFit` / `_menuFitRefit` + 三 ref + 三 watcher | Done |
| S4 | e2e 回归断言(红→绿, 双皮肤) | Done |
| S5 | 静态守阵 + 摘 ref 红验 | Done |
| S6 | 全量 e2e / test.full | Done |
| S7 | 知识库回写 + 索引重建 | Done |

## 进度日志

- 2026-10-06 18:0x 开工。会话协议第 1 步同步成功 `779cf088`(远端领先 13 笔; 本地未提交改动原样保留)。
  issue 文件在同步后才出现 —— 开工前 `ls memory-bank/issues/` 无此件(本 clone 落后)。
- 18:0x **复验**: 先把 e2e 回归断言写成红再动手。首版 arrange「视口最下 220px 带」在棱镜皮肤只凑到
  1 行(行高不齐), 改成「从末行倒着取两个完整可见行」后双皮肤都复现: **菜单盒 `y+height = 1063`**、
  限值 `892`(视口 1440x900, 边距 8)⇒ 溢出 **171px**, 即 issue 记的 361→393 估算差在真实几何上的落点。
- 18:1x 实现 S3。`node --check` 过; CTX-fit 重跑 **2 passed**(修复前同命令 2 failed)。
- 18:1x 加静态守阵 `test_frontend_ctx_menu_refit_by_measured_size`; `test.one` 1 passed;
  **红验**: 把 `ref="ctxMenu"` 改名 ⇒ 该守阵 FAIL(`ctx-menus.html 缺 ref="ctxMenu"`), 还原后绿。
- 18:1x 全量 e2e `commands run dev.e2e` = **82 passed + 10 skipped / 0 failed**(2.9m, 含新增 2 条)。
- 18:2x `test.full` 首跑 2 failed(预期内): `test_claim_chain_is_bidirectional`(issue 的 `doc-refs`
  已指向本档案, 本档案尚未落盘) + `test_gen_all_check_is_green`(生成物索引未重建, 新档案没登记)。
  按「先建件 → 再 `kb.index` → 再跑」的顺序收尾。
