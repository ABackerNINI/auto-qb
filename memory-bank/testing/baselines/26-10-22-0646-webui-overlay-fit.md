# 3999 passed + 2 skipped(根) —— 浮层定位几何收敛 overlay_fit 单点(12 处手写 → 四入口)

> 摘要: 浮层定位几何收敛 overlay_fit 单点(12 处手写 → 四入口)
> 基线时间: 2026-10-22 06:46
**Refs:** memory-bank/issues/26-10-20-2231-refactor-fe-overlay-geometry-dup.html, memory-bank/tasks/26-10-22-webui-overlay-fit.md

## 验收数字

`commands run test.full`(本机 Windows, 仓库自带 TMPDIR 前缀), 改动落盘后实测输出:

```text
TOTAL                                                20981     98   7088    101    99%
3999 passed, 2 skipped in 134.08s (0:02:14)
```

口径注记:

- 0 failed / 0 error; 覆盖率闸(`--cov-fail-under 99`)照过(99%)。较上一轮基线(04:09, 3996)+3: +1 = 本轮新增守阵 `test_overlay_fit_single_point`; 其余 +2 来自 04:31 开工同步(`ad17518a`)合入的并行会话提交(单点绕过收敛 / test-manager 守阵等, 非本轮改动, 未逐笔核对)。
- 真浏览器侧: e2e 全量集(task 定义 `dev.e2e`, line reporter) **340 passed / 10 skipped(11.1m)**, 0 failed —— 与上轮基线(336 passed / 10 skipped)差 +4 为套件自然增长(非本轮新增 spec); 本轮几何改动(浮层夹取单点化)的行为面即由该集 CTX-fit 左右缘诸例盯, 全绿。
- 定向: `tests/test_webui_static_dom_panel.py` + `test_webui_static_skins.py` + `test_webui_ctx_menu_registry.py` 29 passed; 新增守阵单跑 1 passed。
- 红验五类全部命中即红, 还原后复绿: ①atlas 清单摘除 overlay_fit.js →「清单漏挂」红; ②drawer.js openFilePrio 回退手写夹取 →「接线数 1 != 2」红; ③clampAxis 代数破坏(max→min) → node 电池 9 项红; ④hubAsk 12px 匿名成字面 →「必须显式命名」红; ⑤两文件同写顶层 const FIT →「顶层同名」红。
- 中途事故记录(修复后复验): 收敛首版把别名写成七个文件各自的**顶层** `const FIT` —— 经典脚本顶层 let/const 进全局词法环境, 首个声明(config_hub.js)之后六个文件全部 SyntaxError, mixin 静默不注册、整页崩; 静态守阵全绿(只读源码字符串), **只有 e2e 真浏览器现形**(pageerror: Identifier 'FIT' has already been declared)。修法 = 别名改方法内局部取; 守阵补「顶层 const/let 跨文件撞名零容忍」扫描(第 6 项)。教训已回写契约与坑档。
- 耗时区间: test.full 一遍 134.1s; e2e 一遍 667s(11.1m)。

## 本改动面

| 文件 | 改动 |
|---|---|
| `src/auto_qb/webui/static/shared/overlay_fit.js` | **新增**: 浮层「贴边留白 + 视口夹取」几何单点 `window.AQB_OVERLAY_FIT`(IIFE, 四入口: `EDGE`=8 / `clampAxis` / `probeRight` / `probeLeft` / `fitInViewport`) |
| `src/auto_qb/webui/static/{atlas,console,prism}/index.html` | tpl-manifest 同点插入 `"/shared/overlay_fit.js"`(与 fetch_low.js 同行, 不增 shell 行数 —— prism 已顶 214 行上限), 装载序在首个消费方 config_hub.js 之前 |
| `src/auto_qb/webui/static/shared/ui_feedback.js` | `_menuOverflowsRight` 改 `probeRight`; `_menuPos` 改 `fitInViewport`(估算尺寸); `_menuFit` 两轴改 `clampAxis`(maxHeight 兜底留原位); aq-tip `place()` 水平夹取改 `clampAxis`、`EDGE` 取单点 |
| `src/auto_qb/webui/static/shared/menu.js` | `_subOverflowsRight` 改 `probeRight(·, 202, 4)`; `_subFitViewport` 的 room 双探针改 `!probeRight/!probeLeft`、垂直夹取改 `clampAxis`(翻位/箭头策略留原位) |
| `src/auto_qb/webui/static/shared/config_hub.js` | `hubAsk` 全几何改单点; 12px 显式命名 `const EDGE = 12` + 注释(无佐证必须不同, 行为零变化保留) |
| `src/auto_qb/webui/static/shared/hr.js` | `_hrPopPlace` 居中夹取与贴底兜底改 `clampAxis`, `margin` 取 `FIT.EDGE` |
| `src/auto_qb/webui/static/shared/drawer.js` | `openFilePrio` 两轴改 `clampAxis` |
| `src/auto_qb/webui/static/shared/columns.js` | `openColMenuAt` 横轴夹取改 `clampAxis`, PAD 取 `FIT.EDGE`(复验增量处, 入池未记账) |
| `src/auto_qb/webui/static/shared/dialogs.js` | `speedPopStyle` 夹取改 `clampAxis(·, SPEED_PAD)`; `openSpeedAt` 回落锚字面 12 提为命名 `SPEED_PAD` + 注释(复验增量处) |
| `tests/test_webui_static_dom_panel.py` | 新增 `test_overlay_fit_single_point`(单点在册/三清单登记+装载序/七文件接线数对账/手写式零残留/12px 显式命名/顶层 const 撞名扫描/node 电池七型+旧书写代数等价), 文件头测试计划同步 |
| `memory-bank/modules/webui-static-contract.md` | 新增「浮层定位几何单点」契约条(四入口口径/12px 显式传参/不入单点的两类/守阵编号) |

行为零变化依据: 旧四种夹取书写(标准 / openFilePrio 横轴 / hubAsk 纵轴 if 链 / 居中)与两个 `Math.max` 兜底在 7×5×5×10×2 网格上逐点代数等价(node 电池同款判据); `openFilePrio` 纵轴原未钳下缘的不可达角(锚点底在视口顶 4px 内), 经 state.js filePrio watcher 的 `_menuFitRefit` 实测重钳后终值一致(初值即终值)。
