# content 组行级键盘 roving tabindex (Done)

> 摘要: 认领 issue 26-10-07-0846(用户指派)并完成 —— content 组 dt10/11 可点击行 [data-node]
> 与 dt12 树图块 [data-blk]/体积榜行 [data-row] 原纯 div+click 键盘不可达, 按 issue 建议候选①
> roving tabindex 落地: 核心层 drawer_templates.js 增 reg.helpers 四件套(roving 锚点/
> rowFocusKey 记账/rowRestore 回焦/rowMove 移焦), 变体 render 尾三行接入 + 各一处 keydown
> 委托(仅 ev.target 是行容器自身才接管, 行内原生控件自持); 整行不加 role=button(嵌套交互
> 语义, issue 根因段口径, 守阵禁回潮); dt12 焦点互联复用悬停 onOver/onOut(focusin/focusout)。
> 行/块补 :focus-visible。守阵: test_web.py 新增 test_drawer_tpl_content_row_keyboard_roving。
> 验证: test.quick -k drawer_tpl 全绿; **test.full 2713 passed + 4 skipped / 99%**(基线
> 26-10-07-1003)。issue 置 Done + kb.index 重建 + tasks/ 立档(改动 5 源文件命中阈值 2)。
> 最后活动: 2026-10-07 10:03

**Refs:** memory-bank/issues/26-10-07-0846-feat-webui-content-row-keyboard.html,memory-bank/tasks/26-10-07-webui-content-row-keyboard.md,memory-bank/testing/baselines/26-10-07-1003-webui-content-row-keyboard.md

## 现状

- 改动面: drawer_templates.js + drawer_tpl/10/11/12 共 4 份 JS + tests/test_web.py(新增守阵 +
  头部测试计划登记), 零 Python 产品代码改动。改动随本专题入库。
- 设计要点: 记账/回焦是特性成立的必要件(原子换帧打断焦点链, 不回焦一次激活就甩回文档头);
  重建前记账/重建后回焦成对纪律由守阵钉住。
- 无新坑入 pitfalls(方案与配方沿 P3-4/0845 既有口径, 未踩已记坑)。
