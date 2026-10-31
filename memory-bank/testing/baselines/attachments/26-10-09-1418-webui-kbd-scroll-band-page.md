# 2848 —— PageUp/PageDown 一屏改按可见带算(面板开着不再每屏跳一半行)

> 摘要: 同专题第二轮(用户指令「修复 _kbMovePage 的问题」)收尾基线。旧写法一屏按整窗高算(`floor(window.innerHeight / 行高)`), 而可见带被顶栏/吸顶列头/固定状态栏/停靠面板吃掉一截: 实测 1440x900 桩 300 种子, 面板关 可见带 739px(屏内 10~11 行)而一屏前进 12 行(每屏跳 1 行); **面板开 可见带只剩 353px(屏内 6 行)而一屏仍前进 12 行 ⇒ 每翻一屏静默跳过 6 行**。修法 = `per = max(1, floor((_kbViewBottom() - _kbViewTop()) / est))`(est 沿用 `_rowH` 实测均值 → `ROW_WIN_EST_H` → 44 既有链), 零新增函数、不动 `_kbViewportRow`; 修后前进 10 / 4, 两种情形都不跳行。守阵: 静态扩写既有 `test_kb_view_band_single_points` + e2e `kbd-scroll-band.spec.mjs` 新增第 2 条(双皮肤, 面板关/开两档), 均红验。
> 档案: memory-bank/tasks/26-10-09-webui-kbd-scroll-band.md
> 基线时间: 2026-10-09 14:18

**Refs:** memory-bank/tasks/26-10-09-webui-kbd-scroll-band.md

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2848 passed + 4 skipped + 0 failed, 覆盖率 TOTAL 99%**(16567 语句 / 169 未覆盖 / 5716 分支 / 145 partial; 门槛 98% 达标)
- **耗时**: 两次采样 36.55s / 41.96s(命令墙时 38.7~44.3s)
- **新增用例**: **pytest 零新增** —— 本轮只**扩写**既有 `tests/test_web_shortcuts.py::test_kb_view_band_single_points`(加「一屏算式必须由可见带得出」+ 禁 `_winViewH` / `innerHeight` 四条断言)

## dev.e2e 实测

- 命令: `commands run dev.e2e -- --grep @fast`(桩服务 8137 自动起)
- **实测**: **24 passed**(上轮 20 + 新 2) —— 新增 `e2e/kbd-scroll-band.spec.mjs` 第 2 条(双皮肤: `Home` → `PageDown` → 「前进量 ≤ 屏内可见行数 +1」不变式, **面板关 / 面板开两档**), 耗时 37.2s
- 单跑该 spec: 4 passed(双皮肤 × 2 条), 12s
- **红验**: 把 `per` 退回旧算式(`(this._winViewH || window.innerHeight) / est`) → 静态守阵红 + 双皮肤 e2e 双双红(实测报「面板关: 一屏前进 12 行 > 屏内可见 10 行(+1 余量) ⇒ 这一屏跳过了看不见的行(可见带 739px)」), 还原后全绿

## 说明

- **代码事实变更**: 有 —— `shared/shortcuts.js::_kbMovePage` 一屏行数由整窗高改按可见带(复用上一轮落地的 `_kbViewTop()` / `_kbViewBottom()` 两个单点); 零 CSS / 零后端改动。
- **真浏览器旁证**(临时桩 `scripts/ui_harness.py --torrents 300 --port 8139`, 探针脚本在系统 TEMP 未入库): 种子页 prism 真实按键实测 —— 面板关 前进 10 行(屏内 10~11)/ 面板开 前进 4 行(屏内 6), 均无跳行; 修复前同路径 12 / 12。
- **未验证面**: ①**未决(本轮按范围守恒未改)**: `_kbViewportRow` 的渲染行扫描把文档坐标 `vTop/vBot` 与视口坐标 `getBoundingClientRect()` 直接比较, 仅 scrollY=0 成立 ⇒ 非窗口化视图(追剧页)上无光标回落退化成「跳极值行」; 桩数据追剧页只有 1 行复现不出, 需先给桩造多行剧集。②窄屏 ≤900px(面板转 fixed 全屏)下的一屏行数未走查。③`est` 走 `_rowH` 实测均值, 行高差异大(展开组 218px 与普通行 44px 混排)时一屏会偏保守(前进量少于屏内可见行数 = 有重叠, 不跳行 —— 属可接受偏差)。
