# 列表行可见带: 「几何在视口内」≠「看得见」(上下各压一层 chrome)

> 摘要: 键盘光标滚动跟随把「目标行几何在视口内」当成「看得见」, 但列表的上下边各压着一层随正文滚动的 chrome —— 顶部是吸在顶栏下缘的吸顶列头 `.group-head`(sticky, top = `--head-h - 1px`), 底部是固定状态栏 `.statusbar`(fixed, 高 `--statusbar-h`), 面板开着时底部还多一个停靠面板。只拿顶栏高 `_headH` 当上界、`window.innerHeight` 当下界算落点, 光标行会停在 chrome 背后: 用 `Home`/`End`(或一路 ↑↓)把光标移到**首个 / 末个种子**时"只显示一半"(2026-10-09 用户报障)。处置 = 上下各收一个单点 `_kbViewTop()` / `_kbViewBottom()`, 所有"这行看得见吗"的判定只走它们。
> 触发: 键盘移到第一个种子只显示一半, 最后一个种子只显示一半, 光标行被列头盖住, 光标行被状态栏盖住, 看不见当前行, 滚动跟随落点, 可见带, 吸顶列头, group-head, statusbar, _headH, innerHeight, 首行不可见, 末行不可见, Home, End, 滚动跟随算错
**Refs:** memory-bank/tasks/26-10-09-webui-kbd-scroll-band.md

## 条目

### 键盘滚动跟随: 上界漏吸顶列头 / 下界漏固定状态栏 (2026-10-09 用户报障, 已修)

- **触发**: 用户报「WEBUI 键盘移动光标到第一个种子时只显示一半, 最后一个种子同理」; 或任何改「元素是否在视口内」判定的改动。本仓库已有**同族前案**: 停靠面板吸底那次(`pitfalls/web-ui/dock-panel.md`)—— 可见下界一度只认 `window.innerHeight`, 忘了面板顶缘。本条是它的两个**未收编的兄弟**: 上界与状态栏。
- **判别**: 症状是**对称的一半**且只在键盘路径出现 —— 鼠标滚到列表顶/底, 首末行都是完整的; 只有键盘把光标移到极值时少半行。真机三步定位(1440x900 桩 300 种子, `--torrents 300`):
  ① 量三层 chrome 的矩形: 顶栏 `.sticky-head`(95px) / 吸顶列头 `.group-head`(32px, 滚动后 top=94 → bottom=126) / 状态栏 `.statusbar`(top=866, 高 34);
  ② 按 `Home` 后量光标行: 修复前 `top=103` < 列头 bottom=126 → **被列头盖 23px / 行高 71**(矮行时过半); 按 `End` 后量: `bottom=892` > 状态栏 top=866 → **被状态栏盖 26px / 行高 50**; 双皮肤同病(atlas 遮 28 / 16px);
  ③ 根因确认 = 落点算式把「在视口内」当可见: 上界 `_headH + 4`(顶栏高, 不含吸在它下缘的列头), 下界 `window.innerHeight`(不含固定状态栏)。**别被"内容区留了底部内边距"骗过** —— `calc(28px + var(--statusbar-h))` 那条内边距只在**滚到文档底**时把末行托到状态栏之上; 滚动跟随的落点是「视口底 - 8px」, 文档余量足够滚到那里, 于是末行安安静静停在状态栏背后。
- **处置**: 上下各一个单点(与仓库既有「可见性下界收单点」纪律同形), 消费点全部改走它们, 单点外零算式:
  ① 上界 `shortcuts.js::_kbViewTop()` = `_headH` + 吸顶列头高(读 `.group-head` 的 `getBoundingClientRect().height`, **不用当前 rect.bottom** —— 吸顶前后 rect 在两态间跳, 只有高度恒定; 列头不在 DOM(成员明细 `.detail-head` 是 `position: relative`)或计算样式非 sticky 时回落纯顶栏高);
  ② 下界 `_kbViewBottom()` 开头补状态栏: `.statusbar` 实测 `position: fixed` 且高 > 0 时取 `min(bot, 状态栏顶缘)`, 再走原有的停靠面板让位(两者取更紧者 —— 面板本就吸在状态栏之上, 面板开着时它更紧);
  ③ 消费点三处: `_kbScrollRowIntoView` 的**渲染行 rect 路径**与**窗口化前缀和路径**、无光标回落 `_kbViewportRow`。渲染行那个 `scrollIntoView` 禁令照旧(见 `hover-keynav-fight`)。
- **守阵**: `tests/test_web_shortcuts.py::test_kb_view_band_single_points`(静态: 两个单点在且被三处消费、上界不得再裸写 `_headH`/下界不得裸用 `innerHeight`)+ `e2e/kbd-scroll-band.spec.mjs`(真浏览器 @fast, 双皮肤: `End` 落末行不被状态栏盖 / `Home` 落首行不被列头盖, 且断言光标确实落在极值行 —— 否则"没被遮"可能只是光标没走到极值, 断言退化成恒真)。红验: 把 `shortcuts.js` 临时退回 HEAD 版, 新 e2e 双皮肤双双转红(已还原)。
- **家族关系**: 本坑与 `dock-panel.md`(下界漏面板)、`hover-keynav-fight.md`(跟随禁用 scrollIntoView)是同一族 —— **凡"这个元素看得见吗"都要问"它上面/下面压着什么"**。新增消费点时先 grep `_kbViewTop|_kbViewBottom`, 别再手写边界算式。
- **复发**: 0
