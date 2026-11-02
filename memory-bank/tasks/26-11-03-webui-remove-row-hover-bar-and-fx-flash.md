# 26-11-03-webui-remove-row-hover-bar-and-fx-flash — 四皮肤移除鼠标 hover 行左条 + flux 右键强调动效退役

**Status:** Done
**Added:** 2026-11-03
**Updated:** 2026-11-03
**Summary:** 四皮肤移除鼠标 hover 行左条 + flux 右键强调动效退役；保留选中/半选左条、其余 hover 反馈与 `.ctx-src` 静态实心 2px 描边
**Topics:** webui-remove-row-hover-bar-and-fx-flash
**Refs:** memory-bank/testing/baselines/26-11-03-0101-webui-remove-row-hover-bar-and-fx-flash.md

## 原始请求

1. 开工先 `commands run my-commit-flow.sync`，只在 clone1 操作，禁止跨 clone。
2. 先 grep 四皮肤 CSS 的行 hover 左边条规则与 flux 右键强调动效（此前记录为 600ms `fx-row-flash`），列文件与行号，区分哪些皮肤确实有 hover 左边条。
3. 对照 `conventions/webui.md`、`row_lang.css` 行语言约定、`shared/console_hub.css` 确认是否有意设计；冲突时按用户明确要求执行并说明。
4. 最小改动删除 hover 左边条，保留其余 hover 反馈（底色/描边/文字色）；flux 的 `fx-row-flash` 连同 keyframes/规则/无用变量一并移除；**不得动 `.ctx-src` 静态实心 2px 描边**（提交 61d04ca3 成果必须保持）。
5. 起干净端口桩，四皮肤截图对比 hover 态与右键态（给出截图路径）；跑 webui 静态守阵测试，必要时全量；确认 `.ctx-src` 计算值仍是实心 2px、无 animation。
6. 若修改守阵测试，同步 tests 头部「## 测试计划」清单。
7. 不 commit、不 push。

## 思考过程与决策

- 实测现状: **皮肤自有 CSS（prism/atlas/console/flux）无 hover 左边条规则**；唯一的 hover 行左条在共享 `shared/row_lang.css`（flat/wave × 非横滚/横滚 = 4 条 `:hover::before`），默认行语言即 flat，故四皮肤同源生效。`shared/console_hub.css` 无行级左条规则。
- 文档口径冲突: `row_lang.css` 段注此前明确「hover = 中性白条 120ms 渐入」（计划 26-10-30-2359 M2 拍板的有意设计）；用户本轮明确要求移除 ⇒ 按用户要求执行，并同步段注，避免文档继续声称存在 hover 条。
- 删除范围最小化: 只摘 4 条 hover 规则与仅被 hover 条消费的 `--rl-bar` 背景声明/文档 token；选中/半选 `::before` 几何、`--rl-bar-on`、transition 与其余 hover 反馈（行底色/描边/文字色）全部保留。
- flux `fx-row-flash`: 删 `flux/css/fx-mount.css` 的 D4-3 `.ctx-src` 动画规则、`shared/fx/fx.css` 的 `[data-fx~="row-flash"]` + `@keyframes fx-row-flash` + reduced-motion 降级项、`fx.js` REGISTRY 的 `"row-flash"`；`flux/css/components.css` 的 `.ctx-src { outline: 2px solid var(--accent); outline-offset: -2px }` 原值不动，仅删注释里已失效的「fx-row-flash 入场」说法。
- 守阵跟随实现走: `test_frontend_fx_wiring` 注册表名数 27 → 26（基线 9 + S6 提升 17），并在 `## 测试计划` 清单注明 row-flash/D4-3 退役。
- 未改共享 JS/模板/选区与锚点语义；未入池 issue；未 commit/push（用户显式要求）。

## 实现计划

1. 定位四皮肤与共享面的 hover 左条/右键动效规则。
2. `shared/row_lang.css` 移除 4 条 hover 左条，清理 `--rl-bar` 消费与段注。
3. flux 右键强调动效退役：fx-mount.css 规则 + fx.css keyframes/RM + fx.js 注册项。
4. 同步 `test_frontend_fx_wiring` 计数与 tests 头部测试计划。
5. 8160 干净端口桩四皮肤 Playwright 实测（hover/右键截图 + 计算值）。
6. `test.one` 三份 webui 静态守阵 + `test.full` 全量闸门。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 定位四皮肤与共享面规则（结论: 仅共享 row_lang.css 有 hover 左条） | Done(2026-11-03) |
| 2 | row_lang.css hover 左条移除（保留选中/半选条） | Done(2026-11-03) |
| 3 | flux fx-row-flash 动效/keyframes/RM/注册项退役 | Done(2026-11-03) |
| 4 | fx_wiring 守阵计数与测试计划清单同步 | Done(2026-11-03) |
| 5 | 8160 桩四皮肤实测截图与计算值 | Done(2026-11-03) |
| 6 | webui 静态守阵 + 全量测试 | Done(2026-11-03) |

## 进度日志

### R0 · 立档 (2026-11-03)

- 现状: 皮肤自有 CSS 零 hover 左条；`shared/row_lang.css` flat/wave 各 2 条 `:hover::before` 是唯一来源，四皮肤共用。
- 改动: row_lang.css 删 4 条 hover 规则与 `--rl-bar` 消费；flux 删 fx-mount.css D4-3 规则、fx.css `fx-row-flash` 原语/keyframes/RM、fx.js 注册项；`.ctx-src` 静态 outline 规则保持不变。
- 实测(8160/8162 桩，3000 种子/30 组；暗色 `colorScheme=dark` 复验 prism ocean/flat — 其默认浅色 frost 主题本就被 `:not([data-theme="frost"])` 排除): 四皮肤 hover 时行 `::before` opacity=0、行底色仍发生 hover 变化；右键 `.ctx-src` 计算值四皮肤均 `outline: 2px solid …; outline-offset: -2px; animationName: none`；菜单关闭后 `.ctx-src` 计数归零。
- 测试: rebase 前 `tests/test_webui_static_skins.py` 27 passed + 两份 dom 守阵 101 passed; 合流后迁移到 `tests/test_webui_static_skins_{skin,table,widget}.py` 复跑 27 passed; 最终 `test.full` 4906 passed / 10 skipped / 99%(详见最新基线切片)。
- 截图: `%TEMP%\aqb-ui-verify\{prism,atlas,console,flux}-{hover,ctx}.png`（临时验证产物，未入库）。
- 入库: 用户 2026-11-03 明确要求提交(commit+push Gitee develop); 本地提交 `99ad1d92` → rebase 后 `c87ef855`(远端 `a48ead5c`/`b6c01640` 已把 `tests/test_webui_static_skins.py` 拆成 `_skin/_table/_widget`), 27→26 计数与「## 测试计划」清单已迁移到 `tests/test_webui_static_skins_skin.py`(fx_wiring L500/L566)并复跑通过; 索引重建提交 `cd8ba4eb` 已推 Gitee develop, 最终 test.full 4906 passed / 10 skipped / 99%。
