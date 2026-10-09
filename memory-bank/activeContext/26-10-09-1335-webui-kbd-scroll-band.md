# 键盘滚动跟随的可见带: 首个/末个种子只显示一半 · 已闭环

> 摘要: 用户报「键盘移动光标到第一个种子只显示一半, 最后一个种子同理」。真浏览器取证(桩 300 种子, 1440x900, 双皮肤): 光标**确实**落在极值行上, 是滚动跟随的**上下边界各漏一层 chrome** —— 上界只取顶栏高 `_headH`, 漏了吸在顶栏下缘、盖住列表首行的吸顶列头 `.group-head`(遮 23~28px, 行矮时过半); 下界只取 `window.innerHeight`, 漏了底部**固定**状态栏 `.statusbar`(落点「视口底 - 8px」把末行停进状态栏背后, 遮 16~26px)。修法 = 上下各收一个单点: 新增 `_kbViewTop()`(顶栏 + 吸顶列头; 列头高按自身高度复算, 不用跳变的 rect), `_kbViewBottom()` 补状态栏让位(与停靠面板取更紧者); `_kbScrollRowIntoView`(渲染行 + 窗口化两路)与 `_kbViewportRow` 三处消费全改走单点。**刻意不动 `_kbMovePage` 的翻页行数**(计划外, 范围守恒)。
>
> 最后活动: 2026-10-09 13:38

**Refs:** memory-bank/tasks/26-10-09-webui-kbd-scroll-band.md,memory-bank/pitfalls/web-ui/scroll-visible-band.md,memory-bank/testing/baselines/26-10-09-1339-webui-kbd-scroll-band.md

## 本轮完成

- **取证先行(含一次失败的首轮探针)**: 一路 ↑ 回顶复现不出上界(scrollY=0, 首行自然位就在列头下) —— 必须「先滚下去再回上来」才走前缀和落点; 改用键表现成的 `Home`/`End` 一次按键即复现, 也成了 e2e 的按键路径。修复前实测: prism 首行被列头盖 23px / 末行被状态栏盖 26px; atlas 28 / 16px; 辅种页 / 追剧页同病。
- **`shortcuts.js`**: 新增 `_kbViewTop()`(上界单点: `_headH` + `.group-head` 自身高, 列头不在 DOM / 非 sticky 时回落顶栏高); `_kbViewBottom()` 开头补固定状态栏让位(`position: fixed` 且高 > 0 才参与, `Math.min` 与面板取更紧者); `_kbScrollRowIntoView`(渲染行 rect + 窗口化前缀和两路)与 `_kbViewportRow` 三处消费改走单点, 上界不再裸写 `_headH`; 文件头补一条边界单点口径。
- **守阵**: 新增 `tests/test_web_shortcuts.py::test_kb_view_band_single_points`(静态); 新增 `e2e/kbd-scroll-band.spec.mjs`(真浏览器 @fast, 双皮肤 `Home`/`End` 各一条: 零遮蔽 + 光标确在极值行)。**红验**: 把 `shortcuts.js` 临时退回 HEAD 版 → 双皮肤 e2e 双双转红, 还原后双绿。
- 三视图真浏览器复测零遮蔽(首行 top 恰 = 列头 bottom; 末行 bottom 858 < 状态栏 top 866)。实测数字见 `commands run kb.baseline`。

## 待办 / 移交

- 无代码遗留。
- **可选的下一轮(未做, 计划外)**: `_kbMovePage` 按 `_winViewH`(整流视口高)算每屏行数, 比可见带宽约 100px(约 2 行) —— 跟随会把光标带回可见带, 用户无感, 本轮一行未动。
