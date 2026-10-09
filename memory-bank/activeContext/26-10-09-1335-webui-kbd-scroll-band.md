# 键盘滚动跟随的可见带: 首个/末个种子只显示一半 · 已闭环

> 摘要: 用户报「键盘移动光标到第一个种子只显示一半, 最后一个种子同理」。真浏览器取证(桩 300 种子, 1440x900, 双皮肤): 光标**确实**落在极值行上, 是滚动跟随的**上下边界各漏一层 chrome** —— 上界只取顶栏高 `_headH`, 漏了吸在顶栏下缘、盖住列表首行的吸顶列头 `.group-head`(遮 23~28px, 行矮时过半); 下界只取 `window.innerHeight`, 漏了底部**固定**状态栏 `.statusbar`(落点「视口底 - 8px」把末行停进状态栏背后, 遮 16~26px)。修法 = 上下各收一个单点: 新增 `_kbViewTop()`(顶栏 + 吸顶列头; 列头高按自身高度复算, 不用跳变的 rect), `_kbViewBottom()` 补状态栏让位(与停靠面板取更紧者); `_kbScrollRowIntoView`(渲染行 + 窗口化两路)与 `_kbViewportRow` 三处消费全改走单点。**第二轮(同专题)**: 用户指令「修复 _kbMovePage 的问题」→ 一屏改按**可见带**算(旧写法取整窗高, 面板开时可见带只剩 353px/屏内 6 行却仍前进 12 行 = 每屏跳 6 行; 修后 4 行, 不跳行)。**第三轮(同专题)**: 用户指令「修复 _kbViewportRow 的问题」→ 无光标回落的渲染行扫描把**文档坐标** `vTop/vBot`(= `scrollY + 单点`)与**视口坐标** `getBoundingClientRect()` 同框比较, 仅 `scrollY=0` 成立, 追剧页这类非窗口化视图滚过一屏后全判"出视口" ⇒ 退化成**跳极值行**(桩 39 行实测: `↓ @1500` 期望首行 idx 6 实落 row 0 且 scrollY 跳回 8); 修法 = `vTop/vBot` 去 `scrollY` + 新增 `sy` 只在窗口化前缀和那支加回。三轮均已修并有守阵 + 红验。
>
> 最后活动: 2026-10-09 14:37

**Refs:** memory-bank/tasks/26-10-09-webui-kbd-scroll-band.md,memory-bank/pitfalls/web-ui/scroll-visible-band.md,memory-bank/testing/baselines/26-10-09-1418-webui-kbd-scroll-band-page.md,memory-bank/testing/baselines/26-10-09-1435-webui-kbd-scroll-band-viewportrow.md

## 本轮完成

- **取证先行(含一次失败的首轮探针)**: 一路 ↑ 回顶复现不出上界(scrollY=0, 首行自然位就在列头下) —— 必须「先滚下去再回上来」才走前缀和落点; 改用键表现成的 `Home`/`End` 一次按键即复现, 也成了 e2e 的按键路径。修复前实测: prism 首行被列头盖 23px / 末行被状态栏盖 26px; atlas 28 / 16px; 辅种页 / 追剧页同病。
- **`shortcuts.js`**: 新增 `_kbViewTop()`(上界单点: `_headH` + `.group-head` 自身高, 列头不在 DOM / 非 sticky 时回落顶栏高); `_kbViewBottom()` 开头补固定状态栏让位(`position: fixed` 且高 > 0 才参与, `Math.min` 与面板取更紧者); `_kbScrollRowIntoView`(渲染行 rect + 窗口化前缀和两路)与 `_kbViewportRow` 三处消费改走单点, 上界不再裸写 `_headH`; 文件头补一条边界单点口径。
- **守阵**: 新增 `tests/test_web_shortcuts.py::test_kb_view_band_single_points`(静态); 新增 `e2e/kbd-scroll-band.spec.mjs`(真浏览器 @fast, 双皮肤 `Home`/`End` 各一条: 零遮蔽 + 光标确在极值行)。**红验**: 把 `shortcuts.js` 临时退回 HEAD 版 → 双皮肤 e2e 双双转红, 还原后双绿。
- **第二轮(同专题, 2026-10-09 追加, 用户指令「修复 _kbMovePage 的问题」)**: 一屏行数由整窗高改按**可见带**算 —— 实测面板关 739px 可见带/屏内 10~11 行却前进 12 行(每屏跳 1), **面板开 353px/屏内 6 行仍前进 12 行(每屏跳 6)**; 修后 10 / 4, 均不跳行。`per = max(1, floor((_kbViewBottom() - _kbViewTop()) / est))`, `est` 沿用 `_rowH` 实测均值链, 零新增函数。守阵: 静态扩写同一函数(一屏算式必须由可见带得出 + 禁 `_winViewH`/`innerHeight`) + e2e 新增第 2 条(双皮肤 `Home`→`PageDown`, 「前进量 ≤ 屏内可见行数 +1」不变式, 面板关/开两档), **红验**同上。
- 三视图真浏览器复测零遮蔽(首行 top 恰 = 列头 bottom; 末行 bottom 858 < 状态栏 top 866)。实测数字见 `commands run kb.baseline`。
- **第三轮(同专题, 2026-10-09 追加, 用户指令「修复 _kbViewportRow 的问题」)**: 无光标回落的渲染行扫描坐标系错位 —— `vTop/vBot = scrollY + 单点 + 4`(**文档坐标**)与 `rect`(**视口坐标**)同框比, 仅 `scrollY=0` 成立。**破解取证死结**: 桩追剧页只 1 行不可滚 ⇒ 改为 vm 注入展开一剧一集造 39 行(1 剧 + 12 集 + 26 成员, `maxScroll=3387`), `vm.kbCursor = null` 注入"无光标"入口。实测(双皮肤): `↓ @1500` 期望屏内首行 idx 6 实落 **row 0 且 scrollY 跳回 8**; `↑ @1500` 期望 idx 10 实落**最末行(scrollY→2203)**。修法 = `vTop/vBot` 去 `scrollY`(渲染行 rect 直接比, 余量落成 `vTopM/vBotM`)+ 新增 `sy = window.scrollY` **只**在窗口化前缀和那支加回(该支与旧码逐字等价)。守阵: 静态扩写同一函数(单点裸值 / `scrollY` 只经 `sy` / 前缀和 `sy + vTop + 4` / 渲染行比 `vTopM/vBotM`)+ e2e `kbd-scroll-band.spec.mjs` 第 3 条(双皮肤, 追剧页展开一剧一集滚过一屏后 ↑/↓ 各测「光标落按键前可见带内的行」), **红验**: 退回 HEAD 版 → 静态红 + 双皮肤 e2e 双红(报「↓ 落到了按键前看不见的行(idx=0); 按压前屏内可见行 = [31,32,33,34], scrollY 2371->8」)。

## 待办 / 移交

- 无代码遗留。三轮(上下边界 chrome / 翻页一屏行数 / 坐标口径)均已修并有静态 + 真浏览器守阵 + 红验; 坑档 `pitfalls/web-ui/scroll-visible-band.md` 三条并列归档。
