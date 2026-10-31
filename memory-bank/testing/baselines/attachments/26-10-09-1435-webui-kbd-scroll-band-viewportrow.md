# 2849 —— 无光标回落修坐标系错位(滚动后不再跳极值行)

> 摘要: 同专题第三轮(用户指令「修复 _kbViewportRow 的问题」)收尾基线。无光标回落(`_kbViewportRow`)的渲染行扫描把**文档坐标** `vTop/vBot`(= `window.scrollY + _kbViewTop() + 4`)与**视口坐标** `getBoundingClientRect()` 同框比较 —— 仅 `scrollY=0` 成立; 非窗口化视图(追剧页)一旦滚过一屏, 所有渲染行都满足 `rect.bottom <= vTop`, 全被判"出视口", `first/last` 恒 -1 ⇒ 退化成兜底「跳极值行」。实测 1440x900 桩 39 行(追剧页展开一剧一集): `↓ @scrollY=1500` 期望落屏内首行 idx 6 实落 **row 0 且 scrollY 跳回 8**; `↑ @1500` 期望 idx 10 实落**最末行(scrollY 冲到 2203)**。修法 = `vTop/vBot` 去 `scrollY`(渲染行 rect 直接比, 余量落成 `vTopM = vTop + 4` / `vBotM = vBot - 4`)+ 新增 `sy = window.scrollY` **只**在窗口化前缀和那支(它的 y 是文档坐标)加回 —— 前缀和分支行为与旧码逐字等价, 只修渲染行分支。守阵: 静态扩写既有 `test_kb_view_band_single_points` + e2e `kbd-scroll-band.spec.mjs` 新增第 3 条(双皮肤, 均红验)。
> 档案: memory-bank/tasks/26-10-09-webui-kbd-scroll-band.md
> 基线时间: 2026-10-09 14:39

**Refs:** memory-bank/tasks/26-10-09-webui-kbd-scroll-band.md

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2849 passed + 4 skipped + 0 failed, 覆盖率 TOTAL 99%**(16567 语句 / 169 未覆盖 / 5716 分支 / 145 partial; 门限 98% 达标, 实算 98.55%)
- **耗时**: 两次采样 29.8s / 19.2s(命令墙时随并行调度波动)
- **新增用例**: **pytest 零新增** —— 本轮只**扩写**既有 `tests/test_web_shortcuts.py::test_kb_view_band_single_points`(加「坐标系口径」四条断言: `vTop`/`vBot` 单点裸值、`window.scrollY` 只经 `sy` 取一次、前缀和须 `sy + vTop + 4`、渲染行须比 `vTopM/vBotM`)。收集数改动前后同为 2853。

## dev.e2e 实测

- 命令: `commands run dev.e2e -- --grep @fast`(桩服务 8137 自动起)
- **实测**: **30 passed**(HEAD 为 28, 本轮 **+2** —— `e2e/kbd-scroll-band.spec.mjs` 新增第 3 条 × 双皮肤), 耗时 36.8s
- 单跑该 spec: 6 passed(双皮肤 × 3 条), 10.5s
- **红验**: 把 `shortcuts.js` 临时退回 HEAD 版 → 静态守阵红 + 双皮肤 e2e 双双红(实测报「↓ 无光标回落落到了按键前**看不见**的行(idx=0); 按压前屏内可见行 = [31, 32, 33, 34], 共 39 行, scrollY 2371->8 —— 滚动后渲染行全判出视口 ⇒ 退化成跳极值行」), 还原后全绿

## 说明

- **代码事实变更**: 有 —— `shared/shortcuts.js::_kbViewportRow` 渲染行扫描改按**视口坐标**比较(单点裸值 + 余量), 前缀和那一支新增 `sy` 加回; 零 CSS / 零后端改动, 零新增函数。
- **真浏览器旁证**(临时桩 `scripts/ui_harness.py --torrents 300 --port 8139`, 探针脚本在系统 TEMP): 追剧页展开一剧一集造 39 行(1 剧 + 12 集 + 26 成员, `maxScroll=3387`), 双皮肤 `↓/↑ @scrollY=1500/1000` 实测 —— 修复后落点均落在按键前可见带内(`↓ @1500` idx 6、`↑ @1000` idx 7), 修复前同路径落 row 0 / 最末行。
- **未验证面**: ①窗口化视图(`group`/`torrent`)走前缀和另一支, 本轮未改其算式, 回归由既有 e2e(Home/End、PageDown)覆盖; ②窄屏 ≤900px(面板转 fixed 全屏)下的无光标回落未单独走查(回落整窗高, 逻辑同上); ③追剧页「集成员行超窗口阈值(200)」时成员行走窗口化, 未构造该场景(本视图成员 26 条 < 阈值, 全渲染)。
