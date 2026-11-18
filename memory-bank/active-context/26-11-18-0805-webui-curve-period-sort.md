# webui-curve-period-sort

> 摘要: S1-S5 全部落地: 三层 period 自动排序接线(排序键 helper / loader+GET / 前端+e2e)+ S5 收尾(docs 单点回写 / 真机判定纯桩可验 / 全量绿见 kb.baseline); 档案与计划 26-11-18-0801 翻 Done
> 最后活动: 2026-11-19 02:03

**R0(2026-11-18 08:05):** grilling 四轮 13 问拍板 D1-D12(共识清单经用户确认); 计划 26-11-18-0801 入库 Open(S1-S5 待显式开工); 档案立档; 零代码改动

**R1(2026-11-19 02:03):** S5 收尾: docs/configuration.md 曲线排序小节回写 + 真机自检判定纯桩可验 + test.full 全量绿 + 基线切片新建

## 蒸馏 (2026-11-19, S1-S5 三批)

- **三层落点单点键**: Python 单点 `core/curves.py period_sort_key`(day=(0,) < {N}D=(1,N) 按 N 数值 < month=(2,) 恒最后; 归一化复用 normalize_period)+ JS 复刻 `config_editor_curve.js _cfgCurvePeriodSortKey`, 注释双侧互指; 键序用户面文档单点 = `docs/configuration.md`「全局限速曲线」节「曲线排序」小节(S5 回写)。
- **D8/D11 失败放弃策略**: 后端 GET 面 isinstance 链五层形状防御 + 任一 period 抛 ValueError 即整段放弃(不部分重排); JS 同策略, 新增退回尾部追加 —— 前端只少排不错排, 保存一次后端归一自愈。
- **D10 焦点安全设计**: `@input` 逐键写树不动 / `@change`(失焦/回车)提交时整段重排 / 提交后 blur 收口 —— v-for 下标 key 下逐键重排会让焦点行数据错写, 重排只挂提交时机。
- **评审实锤教训两条**: ① `String()` 强转与 Python `str()` 不等价 —— 树内 period 为数组(如 `['DAY']`)时 `String(['DAY'])==='DAY'` 会误解析出 day 键, JS 必须 `typeof` 门拒非字符串; ② e2e 注入布局无甄别力(实现不接线也能绿), 首版返工加甄别面(blur 收口 + 非字符串守门子段)。

**Refs:** memory-bank/tasks/26-11-18-webui-curve-period-sort.md
