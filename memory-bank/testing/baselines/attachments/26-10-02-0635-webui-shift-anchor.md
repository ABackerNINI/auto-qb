# 基线 · 2290 passed + 3 skipped / 99% —— WEBUI Shift 连选起点与键鼠联动统一(方案 B)

> 摘要: 计划 plans/26-10-02-0608 实施收官基线 —— 区间**起点(anchor)**纳入键鼠统一模型: ①起点解析/写入单点 `_selAnchor` / `_selSetAnchor`(兜底链 显式锚点 -> 当前光标 -> [group: 展开的组] -> 列表首行), 四处消费者不再各写一遍 `list[0]`; ②五个点击入口普通/Ctrl 路径落起点(**排除 Shift** —— 法则 2 起点在扩展期间不动); ③键盘 Shift 手势原点 `_selSeedAnchorFromCursor` 在 `_kbMove` **之前**落起点; ④追剧页起点缺失不再退化为单单元切换。纯前端改动(JS/注释/守阵), 无 Python src / 配置键 / 后端改动。
> 档案: [tasks/26-09-28-webui-keyboard-shortcuts.md](../../tasks/26-09-28-webui-keyboard-shortcuts.md)。
> 计划: [plans/26-10-02-0608-plan-webui-shift-anchor.html](../../plans/26-10-02-0608-plan-webui-shift-anchor.html)(W1-W5 全落地)。
> 基线时间: 2026-10-02 07:05, develop @ eae2aede + 本笔工作树(阈值 98 下 test.full 实测; 收尾回写未提交)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。

TOTAL **2290 passed + 3 skipped / 99%**(13,349 语句 / 86 未覆盖 / 4,436 分支 / 81 partial,
test.full 43.1s, rc=0)。

相对上一条基线(26-10-02-0603: 2289 passed / 13,357 语句 / 91 未覆盖 / 4,448 分支 / 86 partial / 99%)
**+1 passed**(新增守阵 `test_shift_anchor_unified` 一条)。语句 13,357 → 13,349(−8)、分支 4,448 → 4,436
(−12)、未覆盖 91 → 86、partial 86 → 81 —— 后四项**非本笔改动所致**: 本轮纯前端 JS/注释, `--cov=src`
不收 tests 与 static; 差异来自提交前并入的远端提交(`eae2aede` 一族, 含删除 tray 恒假读回校验分支
与主循环 StopIteration 显式重抛等)。综合口径仍 **99%**(远高于阈值 98)。

改动面: `src/auto_qb/webui/static/shared/selection.js`(起点单点 5 方法 + 四处消费者改调用 +
五入口落起点 + `_extendUnit` 区间化 + 头注)/ `shared/shortcuts.js`(`_selSeedAnchorFromCursor` +
`_kbExtend` 顺序 + 头注)/ `shared/state.js`(三锚点字段注释)/ `tests/test_web_shortcuts.py`
(+1 守阵 + 测试计划清单一行)。无模板/CSS 改动。

守阵: `tests/test_web_shortcuts.py` 18 → 19 条。`node --check` 三 JS 全绿。

浏览器冒烟(dev.harness 桩服务 + `scripts/ui_smoke.cjs`, 3000 种子): **80 PASS + 2 FAIL**, 失败项为
`[prism]/[atlas] 冒烟整体执行 — elementHandle.click 超时(sticky-head 遮挡落点)` —— **stash 前后
对照确认先在**(同 80 PASS、同 2 项、同行号), 且提交前并入 `eae2aede`(改 console_hub.css / xtpl.html)
后**重测仍同 80 PASS + 同 2 项同行号** —— 属坑档 [testing/smoke.md](../../pitfalls/testing/smoke.md)
记录的间歇性吸顶遮挡, 与本笔无关, 未修(范围守恒)。故本轮**无新增**冒烟失败, 无 pageerror /
console.error。

未做: 真机(用户实际 qB 实例)实弹走查 —— 计划 §07.1 行为验收 M1-M8 的实弹确认留给用户; 静态守阵
只钉"调用点存在且顺序正确", 不验证区间语义。
