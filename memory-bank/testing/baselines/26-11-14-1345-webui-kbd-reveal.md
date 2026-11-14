# 6102 passed + 2 skipped(根) —— WebUI 键位提示全面改造 实施收尾(显影/常驻/全量落点)

> 摘要: WebUI 键位提示全面改造 实施收尾(显影/常驻/全量落点)
> 基线时间: 2026-11-14 13:45
**Refs:** memory-bank/tasks/26-11-14-webui-kbd-reveal.md

## 验收数字

`commands run test.full` 实测输出(未提交树, HEAD bf3acfb4 + 本轮文档/注释改动; pytest 收集面与 bf3acfb4 同):

    TOTAL                                                27113     65   9480     69    99%
    6102 passed, 2 skipped in 206.84s (0:03:26)

## 本改动面

- `memory-bank/architecture/webui.md`: 「键位现场提示」节按实施结果回写(显影链 / 两态开关 / 键帽形态 / 角标与恒渲染槽 / 表外 kbd / 测试面), 摘要与触发词同步。
- `memory-bank/conventions/webui.md`: 「悬浮提示」节补 D11 边界(控件自身功能说明仍写 title)。
- `e2e/menus.spec.mjs`: 仅改置灰行键帽用例注释(S2 后基形为 --fg-dim 且默认隐藏), 断言零改动。
- 本基线切片自身。
- 纯文档 / 注释改动, 零 `src/` 产品代码与零测试断言改动 —— pytest 数字与 T6a 在 98a3f2f8 的实测(6102 passed / 2 skipped, 27113 stmt / 9480 branch)一致, 可交叉校验。

