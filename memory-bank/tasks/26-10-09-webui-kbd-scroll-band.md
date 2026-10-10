# 26-10-09-webui-kbd-scroll-band — 键盘滚动跟随的可见带: 首个/末个种子不再只显示一半

**Status:** Done
**Added:** 2026-10-09
**Updated:** 2026-10-09
**Summary:** 用户报「WEBUI 键盘移动光标到第一个种子只显示一半, 最后一个种子同理」。真浏览器取证(桩 300 种子, 1440x900, 双皮肤): 光标行确实落在极值行上, 但滚动跟随的**上下边界各漏一层 chrome** —— 上界只取顶栏高 `_headH`, 漏了吸在顶栏下缘、盖住列表首行的吸顶列头 `.group-head`(prism 遮 23px / 行高 71, atlas 28px); 下界只取 `window.innerHeight`, 漏了底部**固定**状态栏 `.statusbar`(落点「视口底 - 8px」把末行停进状态栏背后, prism 遮 21px / 行高 44, atlas 16px)。修法 = 上下各收一个单点: 新增 `shortcuts.js::_kbViewTop()`(顶栏 + 吸顶列头), `_kbViewBottom()` 补状态栏让位(与停靠面板取更紧者); `_kbScrollRowIntoView`(渲染行 + 窗口化两路)与 `_kbViewportRow` 三处消费全改走单点。新增静态守阵 `test_kb_view_band_single_points` + 新 e2e `e2e/kbd-scroll-band.spec.mjs`(Home/End 真按键, 双皮肤), 均红验(退回 HEAD 版 → 双皮肤转红)。**第二轮(同专题, 2026-10-09 追加)**: PageUp/PageDown 的「一屏」也按可见带算 —— 旧写法取整窗高, 面板关可见带 739px(屏内 10~11 行)而一屏前进 12 行(每屏跳 1 行), **面板开可见带只剩 353px(屏内 6 行)而一屏仍前进 12 行 ⇒ 每翻一屏静默跳过 6 行**; 改成 `per = floor((_kbViewBottom - _kbViewTop) / 行高)` 并补 e2e「不跳行不变式」(前进量 ≤ 屏内可见行数 +1, 面板关/开两档, 均红验)。**第三轮(同专题, 2026-10-09 追加)**: 用户指令「修复 _kbViewportRow 的问题」→ 无光标回落的渲染行扫描把**文档坐标** `vTop/vBot`(= `scrollY + 单点`)与**视口坐标** `getBoundingClientRect()` 同框比较, 仅 `scrollY=0` 成立; 追剧页这类非窗口化视图滚过一屏后所有渲染行被判"出视口", 无光标回落退化成**跳极值行**(实测 1440x900 桩 39 行: `↓ @scrollY=1500` 期望落屏内首行 idx 6 实落 row 0 且 scrollY 跳回 8; `↑` 期望 idx 10 实落最末行)。修法 = `vTop/vBot` 去 `scrollY`(渲染行 rect 直接比), 新增 `sy = window.scrollY` 只在窗口化前缀和那支加回; 前缀和分支与旧码逐字等价。补 e2e 第 3 条(双皮肤: 追剧页展开一剧一集 → 滚过一屏 → ↑/↓ 各测「光标落按键前可见带内的行」, 均红验)。实测数字见 `commands run kb.baseline`。
**Topics:** webui-kbd-scroll-band
**Refs:** memory-bank/pitfalls/web-ui/scroll-visible-band.md,memory-bank/testing/baselines/26-10-09-1339-webui-kbd-scroll-band.md,memory-bank/testing/baselines/26-10-09-1418-webui-kbd-scroll-band-page.md,memory-bank/testing/baselines/26-10-09-1435-webui-kbd-scroll-band-viewportrow.md

## 原始请求

用户(2026-10-09 13:02): 「WEBUI使用键盘移动时无法显示完整第一个种子或最后一个种子, 即第一个种子不可见->使用键盘移动光标到第一个种子->第一个种子只显示一半, 最后一个种子同理」。

属执行任务(缺陷报障), 非问答。开工先 `commands run my-commit-flow.sync`(同步成功 `ff768df6`)。

第二轮(2026-10-09 13:47)用户: 「修复_kbMovePage的问题」—— 指上一轮收尾时我标注的「`_kbMovePage` 仍按整流视口高算每屏行数, 比可见带宽约 100px」这处计划外遗留(当时按范围守恒一行未动、在回复里移交)。仍属执行任务。

第三轮(2026-10-09 14:24)用户: 「修复_kbViewportRow的问题」—— 指第二轮取证时撞见的同族第三处计划外缺陷(`_kbViewportRow` 渲染行扫描的文档坐标 / 视口坐标错位, 当时写进档案/坑档/切片留痕、未改)。仍属执行任务。

## 思考过程与决策

- **先取证再动手**: 桩服务(`scripts/ui_harness.py --torrents 300 --port 8139`)+ Playwright 一次性探针(临时脚本在系统 TEMP, 不进仓库)。
  - 首轮探针按「一路 ↑ 60 次回顶」复现不出上界: 初始光标落在视口内, 一路 ↑ 到第 0 行时页面**根本没滚动过**(scrollY=0), 首行自然位就在列头下方 —— **必须"先滚下去再回上来"** 才触发前缀和落点这条路。
  - 二轮探针(↓40 再 ↑60)复现: `scrollY=40`, 列头 bottom=126, 光标行 top=103 → **被列头盖 23px**; 末尾(↓120): 光标行 bottom=892, 状态栏 top=866 → **被状态栏盖 26px / 行高 50**。
  - 用 `Home` / `End`(键表里现成的跳首/末行)一次按键即可复现, 双皮肤都中 —— 这也直接成了 e2e 守阵的按键路径(与用户报障同路径)。
- **根因是"两处边界各漏一层 chrome", 不是算式写错**: 单看 `rect.top < headH + 4` 与 `rect.bottom > innerHeight - 4` 都是对的 —— 病灶在**前提**: 顶栏之下还吸着列头(`.group-head`, sticky top = `--head-h - 1px`), 视口底之下还压着固定状态栏。这与 `pitfalls/web-ui/dock-panel.md`「停靠面板吸底会遮蔽以 `window.innerHeight` 为下界的滚动几何」是**同族**缺陷(那次是面板, 这次是列头与状态栏), 该坑档已写下纪律「凡'元素是否在视口内'一律走单点」, 但当时只收了**下界一个**单点, 上界当时没人问。
- **为什么内边距救不了末行**: 内容区底部有 `calc(28px + var(--statusbar-h))` 的内边距, 但那只在**滚到文档底**时把末行托到状态栏之上; 跟随落点写的是「视口底 - 8px」, 文档余量足够滚到那儿 ⇒ 末行恰好停在状态栏背后。**别按"有内边距所以不会盖住"推断, 量一次就明白**。
- **修法: 上下各一个单点, 单点外零算式**。上界用列头**自身高度**复算而不是当前 `rect.bottom`(吸顶前后 rect 在两态间跳, 高度恒定才可复算); 下界在原有面板让位**之前**补状态栏, 两者由 `Math.min` 取更紧者(面板本就吸在状态栏之上)。消费点三处(`_kbScrollRowIntoView` 渲染行 rect / 窗口化前缀和、`_kbViewportRow`)全部改走单点, 上界不再裸写 `_headH`。
- **不改 `_kbMovePage` 的翻页行数**: 它按 `_winViewH`(整流视口高)算每屏行数, 严格说比可见带大一点(翻页后多走几行), 但跟随会把光标行带回可见带内, 用户无感 —— 属**计划外**, 一行不动(范围守恒); 若要治, 单点在主循环之外的下一轮提。
- **守阵双层**: 静态守阵只能钉"单点在 + 被消费 + 不许裸写", 几何正确性必须真浏览器(本项目既有口径: 静态全绿而真机必红)。故新增 `e2e/kbd-scroll-band.spec.mjs` @fast, 并做了**红验**: 把 `shortcuts.js` 临时退回 HEAD 版 → 双皮肤两条 e2e 双双转红, 还原后双绿。
- **第三轮的"坐标系"病灶与前两条不同层**: 前两条是**边界值**取错(漏 chrome)、第三轮是**坐标系**用错 —— 单点本身是对的(返回视口坐标), 错在消费方把 `scrollY` 混进渲染行的比较里。因此修法不是再收单点, 而是**让两套坐标各归各的**: 单点仍只出视口坐标, 谁需要文档坐标谁自己加 `sy`。这也解释了为何旧码"单看每处都像对的"——`window.scrollY + _kbViewTop() + 4` 在 `scrollY=0` 时确实等于 `_kbViewTop() + 4`, 只有滚动后才露馅。
- **破解取证死结**: 桩数据追剧页只有 1 行(`n:1` 全落未识别)复现不出, 前一轮据此搁置。本轮**不改桩**而是**展开一剧一集**(vm 注入 `expandedShows`/`expandedShowEp`)造出 39 行非窗口化视图 —— 行数够多即 `maxScroll=3387`, 可滚; 且集成员行(`[data-hash]`)与剧/集行(`[data-key]`)两条分支都被扫到。**"无光标"入口**只能经 `vm.kbCursor = null` 注入(点行/按键都会落光标), 这是 `_kbViewportRow` 的唯一触发前置。

## 实现计划

单会话单轮: 真浏览器取证(定"两处边界各漏一层 chrome") → `shortcuts.js` 增 `_kbViewTop()` / `_kbViewBottom()` 补状态栏 / 三处消费改走单点 + 文件头口径补一条 → 静态守阵 + e2e 规格(均红验) → `test.full` + `dev.e2e` → 收尾回写(档案 / 切片 / 基线 / 坑档 / kb.index)。

第二轮(同专题, 同一会话): 真浏览器取证(量面板关/开两档的可见带与一屏前进量) → `_kbMovePage` 改按可见带算一屏 → 静态扩写 + e2e 增一条不跳行不变式(均红验) → `test.full` + `dev.e2e` → 回写档案/切片/坑档。

第三轮(同专题, 同一会话): 真浏览器取证(展开一剧一集造 39 行非窗口化视图, 量 `↑/↓ @scrollY=1500` 的落点) → `_kbViewportRow` 修坐标系(渲染行用视口坐标, 前缀和加回 `sy`) → 静态扩写 + e2e 增一条「落屏内就近行」不变式(均红验) → `test.full` + `dev.e2e` → 回写档案/切片/基线/坑档。

## 子任务状态表

| 子任务 | 内容 | 状态 |
|---|---|---|
| S1 | 真浏览器取证: 复现「首行被列头盖 / 末行被状态栏盖」(双皮肤, 定 23/26/28/16px) | Done |
| S2 | `shortcuts.js`: 新增 `_kbViewTop()`; `_kbViewBottom()` 补固定状态栏让位; 三处消费改走单点 | Done |
| S3 | 静态守阵 `test_kb_view_band_single_points` + e2e `kbd-scroll-band.spec.mjs`(均红验) | Done |
| S4 | `test.full` + `dev.e2e` 复跑; 真浏览器复测(种子页 / 辅种页 / 追剧页三视图零遮蔽) | Done |
| S5 | 收尾回写(档案 / 切片 / 基线 / 坑档 `scroll-visible-band.md` / `kb.index`) | Done |
| S6 | 第二轮(同专题): `_kbMovePage` 的「一屏」改按可见带算 + e2e 不跳行不变式(面板关/开两档, 均红验) | Done |
| S7 | 第三轮(同专题): `_kbViewportRow` 修坐标系错位(渲染行用视口坐标, 前缀和加回 `scrollY`) + e2e 追剧页「落屏内就近行」断言(双皮肤 ↑/↓, 均红验) | Done |

## 进度日志

- **2026-10-09 13:02**: 用户报障。开工先 `my-commit-flow.sync`(同步成功 `ff768df6`, 远端领先 2 笔已快进)。
- **2026-10-09 13:0x–13:1x**(S1): 首轮探针**复现不出**上界(一路 ↑ 回顶时页面没滚过, scrollY=0)—— 改为「↓40 再 ↑60」后复现; 随后发现 `Home`/`End` 一次按键即复现, 定为守阵按键路径。三视图(chromium 1440x900)实测: 种子页 prism 盖 23px(列头)/ 26px(状态栏), atlas 28 / 16; 辅种页、追剧页同病。
- **2026-10-09 13:1x–13:3x**(S2–S3): 落地双单点 + 三处消费; 新增静态守阵(29 项全过)与新 e2e(双皮肤 2 条 @fast, 8s)。红验: `git show HEAD:...shortcuts.js` 覆盖回来跑 e2e → 双皮肤双双红(报「末行: 光标未落到极值行, 或该行仍被 chrome 遮住」), 还原后双绿。
- **2026-10-09 13:3x**(S4): `test.full` 全绿(数字见 `commands run kb.baseline`); `dev.e2e --grep @fast` 全绿; 三视图真浏览器复测零遮蔽(首行 top 恰等于列头 bottom = 完整可见; 末行 bottom 858 < 状态栏 top 866)。
- **2026-10-09 13:4x**(S5, 收尾): 本档案立档 + activeContext 切片 + 基线切片 + 坑档 `pitfalls/web-ui/scroll-visible-band.md` + `kb.index` 重建。全员入库 `a97efc60`。
- **2026-10-09 13:47–14:1x**(S6, 第二轮, 用户指令「修复 _kbMovePage 的问题」): 取证 —— 桩 300 种子实测: 面板关 可见带 739px / `est` 71.4 / 一屏前进 **12 行**而屏内 10~11 行(每屏跳 1 行); **面板开 可见带 353px / 屏内 6 行 / 仍前进 12 行 ⇒ 每屏跳 6 行**。修法 = `per = max(1, floor((_kbViewBottom - _kbViewTop) / est))`(est 仍走 `_rowH` 实测均值 → `ROW_WIN_EST_H` → 44 的既有链), 零新增函数、不动 `_kbViewportRow`。修复后实测: 面板关前进 10(= 屏内 10), 面板开前进 4(≤ 屏内 6) —— **两种情形都不再跳行**(有 1~2 行重叠, 属翻页常态)。守阵: 静态扩写 `test_kb_view_band_single_points`(一屏算式必须由可见带得出 + 禁 `_winViewH` / `innerHeight`); e2e `kbd-scroll-band.spec.mjs` 新增第 2 条(双皮肤 → @fast 共 4 条): 「前进量 ≤ 屏内可见行数 +1」不变式, 面板关/开两档。红验: 把 `per` 退回旧算式 → 静态红 + 双皮肤 e2e 红(报「面板关: 一屏前进 12 行 > 屏内可见 10 行」), 还原后全绿。
- **2026-10-09 13:5x**(S6 取证副产品, 当时**未改**, S7 已收): `_kbViewportRow` 的渲染行扫描把文档坐标 `vTop/vBot`(=`scrollY + 顶栏 + 列头`) 与视口坐标 `getBoundingClientRect()` 直接比较 —— 仅 scrollY=0 时成立, 滚动后所有行被判"看不见" ⇒ 非窗口化视图(追剧页等)上无光标回落退化成「跳极值行」。桩数据的追剧页只有 1 行(`n:1`, 全落「未识别」)复现不出, 当时按**范围守恒**一行未改、移交; 第三轮(下方 S7)按用户指令收口。
- **2026-10-09 14:2x–14:3x**(S7, 第三轮, 用户指令「修复 _kbViewportRow 的问题」): 开工先 `my-commit-flow.sync`(同步成功 `667b3924`)。
  - **复现路径(破解"追剧页只有 1 行"的取证死结)**: 桩数据里所有种子名解析成同一部剧 ⇒ 追剧页仅 1 行不可滚。改用**展开一剧一集**造出 39 行非窗口化视图(1 剧 + 12 集 + 26 集成员), `maxScroll=3387`; 而「无光标」入口靠 `vm.kbCursor = null` 注入(点击/键盘都会落光标, 否则到不了 `_kbViewportRow` 分支)。
  - **实测(1440x900 双皮肤, 探针脚本临时在系统 TEMP)**: `↓ @scrollY=1500` 期望落屏内首行(idx 6)实落 **idx 0 且 scrollY 跳回 8**; `↑ @1500` 期望落屏内末行(idx 10)实落**最末行(scrollY 冲到 2203)**; `@1000` 两向同样越界。根因 = `vTop/vBot = window.scrollY + 单点 + 4`(**文档坐标**)与 `rect`(**视口坐标**)同框比较, 滚过一屏后渲染行全判"出视口"、`first/last` 恒 -1 ⇒ 兜底跳极值行。
  - **修法**: `vTop/vBot` 去 `scrollY`(渲染行 rect 直接比, 余量落成 `vTopM/vBotM`); 新增 `sy = window.scrollY`, **只**在窗口化前缀和那支(文档坐标)比较时加回。前缀和分支与旧码逐字等价, 只修渲染行分支 —— 正是 `_kbViewTop()` 注释早写明的口径(「消费方自行加 window.scrollY」)。
  - **守阵**: 静态扩写 `test_kb_view_band_single_points`(vTop/vBot 必须单点裸值、`window.scrollY` 只经 `sy` 取一次、前缀和须 `sy + vTop + 4`、渲染行须比 `vTopM/vBotM`); e2e `kbd-scroll-band.spec.mjs` 新增第 3 条(双皮肤 → @fast 共 6 条): 追剧页展开一剧一集 → 滚过一屏 → ↑/↓ 各测一遍, 判据 = 光标必须落在**按键前**就在可见带内的行上。**红验**: 退回 HEAD 版 → 静态红 + 双皮肤 e2e 双双红(报「↓ 落到了按键前看不见的行(idx=0); 按压前屏内可见行 = [31,32,33,34], scrollY 2371->8」), 还原后全绿。
