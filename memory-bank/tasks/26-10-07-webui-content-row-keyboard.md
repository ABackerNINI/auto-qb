# 26-10-07-webui-content-row-keyboard — content 组可点击行/树图块键盘化(roving tabindex)

**Status:** Done
**Added:** 2026-10-07
**Updated:** 2026-10-07 10:03
**Topics:** drawer-tpl, a11y, roving-tabindex, keyboard-nav
**Summary:** content 组 dt10/11 可点击行 [data-node] 与 dt12 树图块 [data-blk]/体积榜行 [data-row] 纯 div+click, 键盘/读屏不可达(修复轮 26-10-07-webui-detail-panel-audit-fixes P3-4 缩围转来的已记未做项)。修法 = issue 建议候选① roving tabindex, 单点收口在核心层 reg.helpers 四件套(roving 锚点 / rowFocusKey 记账 / rowRestore 回焦 / rowMove 移焦), 整行不加 role=button(行内已含原生控件, 嵌套交互语义更糟)。守阵: test_web.py 新增 test_drawer_tpl_content_row_keyboard_roving。

**Refs:** memory-bank/issues/26-10-07-0846-feat-webui-content-row-keyboard.html,memory-bank/activeContext/26-10-07-1003-webui-content-row-keyboard.md,memory-bank/testing/baselines/26-10-07-1003-webui-content-row-keyboard.md

## 原始请求

用户：「认领并修复issue:26-10-07-0846-feat-webui-content-row-keyboard」。

## 思考过程与决策

- **复验**: 三锚点全部仍现(data-node= dt10:254 / dt11:224, data-blk= dt12:276/313, 行号微漂), 复现成立。
- **方案拍板**: issue 建议两候选 —— ① roving tabindex(语义最正, 行容器 tabindex=-1 + 方向键移焦, 行内原生控件自然参与 Tab 序); ② 行展开/选中拆独立行头按钮(结构改动大)。取 ①, 理由: 结构零改动、与 P3-4「模拟控件补键盘达」同方向; 整行**不加** role="button" —— 行内已含原生 button/checkbox, 嵌套交互语义反而更糟(issue 根因段口径), 键盘可达靠 tabindex + 委托, 读屏语义靠行内控件自身。
- **焦点链问题(单点设计的核心动机)**: 变体整帧重建用 replaceChildren 原子换帧, 会打断焦点链 —— 不做回焦, 键盘用户按一次 Enter 激活行就被甩回文档头, 特性等于没做。故四件套里记账(rowFocusKey)/回焦(rowRestore)与锚点(roving)/移焦(rowMove)成对, 变体在 render 尾部三行接入。
- **单点收口**: 四件套放核心层 drawer_templates.js 的 reg.helpers(口径同 26-10-07-0845 骨架收口), 变体零复刻; 三变体各自一处 keydown 委托(onKeyDown), 只有 ev.target 是行容器自身才接管(行内原生控件键盘行为自持, 防 Enter 双重触发)。
- **dt12 特有**: 树图块四向箭头都开移焦(空间布局, DOM 序=squarify 序近似空间序); 焦点互联复用悬停 onOver/onOut(focusin/focusout 冒泡, 与 mouseover/out 同语义) —— 键盘选中块时体积榜联动高亮, 零新代码。
- **dt11 锚点**: 勾选集没有「选中行」语义(不同于 dt10/dt12 的 selPath), 锚点恒首行; 点击行激活逻辑顺带收成 toggleRow 单点供 click/keydown 两路共用。

## 实现计划

单轮小修(无波次): drawer_templates.js(helpers 四件套 + cssAttrEsc) + dt10/11/12(行/块 tabindex=-1 + :focus-visible + render 尾锚点/回焦 + keydown 委托) + 守阵一件(test_web.py)。

## 子任务状态表

| # | 项 | 状态 | 验证门 |
|---|------|------|--------|
| 1 | 复验锚点 | 完成 | 三处仍现(见 issue 状态日志) |
| 2 | 核心 helpers 四件套 | 完成 | 守阵断言单点存在 |
| 3 | dt10/11/12 接入 | 完成 | 同上 + node --check |
| 4 | 守阵 test_drawer_tpl_content_row_keyboard_roving | 完成 | test.quick 8 drawer_tpl 组全绿 |
| 5 | 全量测试 + 基线 + 回写 | 完成 | test.full 2713 passed |

## 进度日志

- 2026-10-07 10:03: 修复完成全绿。test.full 2713 passed + 4 skipped / TOTAL 99% / 56.24s(基线 26-10-07-1003, 相对上基线 passed +1 = 新守阵, 语句/分支/未覆盖全同, 无回归)。issue 置 Done + kb.index 重建。改动随本专题入库。
