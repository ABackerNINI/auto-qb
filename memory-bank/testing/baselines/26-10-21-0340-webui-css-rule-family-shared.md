# 3974 passed + 2 skipped —— 三皮肤 CSS 四规则族收敛进共用层(issue 26-10-20-2231)

> 摘要: 三皮肤 CSS 四规则族收敛进共用层(issue 26-10-20-2231)
> 基线时间: 2026-10-21 03:40
**Refs:** memory-bank/issues/26-10-20-2231-refactor-fe-css-rule-family-dup.html

## 验收数字

`commands run test.full`(本机 Windows, 仓库自带 TMPDIR 前缀), 实测输出:

```text
TOTAL                                                20715     75   7012     88    99%
3974 passed, 2 skipped in 147.39s (0:02:27)
```

口径注记:

- 0 failed / 0 error; 覆盖率闸(`--cov-fail-under 99`)照过(99%)。
- 本轮跑了两遍全量(改完代码一遍、文档回写后再一遍): 数字逐位相同, 耗时 130.94s ~ 147.39s(单次采样无意义, 记区间)。
- 本轮**纯 CSS 收敛 + 守阵判据调整, 零 Python 生产代码改动** —— 用例数不变, 数字与上一条基线持平。
- 真浏览器侧另跑 `commands run dev.e2e`:**336 passed / 10 skipped / 0 failed**(11.1m)。三皮肤主表、
  抽屉、设置页 HR 表①、弹窗全在断言面内, 视觉零变化。
- 等价性自证不靠人眼: 收敛前后按「皮肤聚合 + shared 共用层」现算**最终生效规则表**(59 条族内规则),
  逐条 selector→body **完全一致**, 且生效表内无重复声明(证明「搬走的那份」与「留下的那份」不冲突,
  级联序换了位置但没人被盖掉)。

## 本改动面

| 文件 | 改动 |
|---|---|
| `src/auto_qb/webui/static/shared/console_hub.css` | 新增尾段「三皮肤共用规则族单点」: A qb-tabs 4 条 / B drawer-tabs 2 条 / C 弹窗语义配色分级 11 条 / D HR 表① 件 18 条(+96 行) |
| `atlas|console|prism` 各皮肤 CSS | 同族规则逐条删除, 原位留一行指针注释(说明哪些留、为什么留); 弹窗语义分级的 ①②③④ 层次注释连规则整组搬走 |
| 皮肤文件净行数 | `atlas/views` −35 · `console/views` −35 · `prism/views` −23 · `atlas/dialogs` −20 · `console/dialogs` −20 · `prism/components` −29 ⇒ **三皮肤合计 −162 行**(共用层 +96, 全仓净 −66) |
| `tests/webui_helpers.py` | 新增 `_ui_css_effective(ui)` = 皮肤聚合 + shell 里挂的 shared CSS(link 序); `_ui_css_aggregate` 补注「只含本皮肤」 |
| `tests/test_webui_static_skins.py` | HR 表① 两处成对守阵 + 箭头几何守阵改量「生效面」; prism 两文件拆分的钉法改为「共用层持有」; 新增「徽章底形族必须留在各皮肤自己的 CSS」断言(带 `{` 边界) |
| `tests/test_webui_static_dom_panel.py` | 流量图控件 `.qb-tabs button.active` 断言改量生效面 |

三皮肤各自的真差异(留皮肤内, 未抹平): `.drawer-tabs button.active` 令牌(atlas/console `--accent` vs prism `--accent-hi/--accent-line`);
`.hr-vsrc` / `.hr-pres` 描边(prism `--border-soft` vs 另两皮肤 `--border`); `.hr-sub` 字体(prism `--font-mono` vs 字面等宽栈)。
