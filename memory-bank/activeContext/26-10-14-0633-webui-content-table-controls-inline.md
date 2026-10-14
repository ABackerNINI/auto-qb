# 26-10-14-0633-webui-content-table-controls-inline — 内容页表格交互件收编(按钮/展开钮/勾选框退出独立列)

> 摘要: 修复用户复查(报告 26-10-14-0136 §02)呈现缺陷「操作按钮独立成列」「展开按钮没有层级」+ 二次复查续「复选框仍然独立成列, 还能调整位置」。内容树两变体(10/11)删除 tgl/prio 两条交互轨道: 折叠钮收编进 name 格首部(随缩进 = 层级), 徽章收编进 name 格尾部(margin-left:auto 右对齐); name 列 locked(L4 续效)。二次复查续: ck 勾选框收进 name 格首随缩进, ck 列删除(终态 V11 = name/size/prog/av 四列), 勾选框随 name 格走 ⇒ name 列 locked 续效(隐藏 name = 一并废掉勾选框/折叠钮/徽章三个交互件)。终态 V10 = 3 列 / V11 = 4 列; 用户已存列偏好按 key 求交免迁移。守阵新增回潮判据(tgl/prio/ck 不得回成独立列 + 交互件恰一次且 name 分支内), e2e 三份 spec 同轮改写, @fast 全量(134 例)与静态守阵全绿; test.full 基线与本档案的 Refs 反向闭合。
> 最后活动: 2026-10-14 08:06

**Refs:** memory-bank/tasks/26-10-14-webui-content-table-controls-inline.md,memory-bank/tasks/26-10-14-webui-content-ck-inline.md

## 正在进行

- 无。本专题修复与验证已收口(基线见 tasks 档案 Refs)。

## 下一步

1. 用户复查是否接受「勾选框/徽章收进 name 格内」的呈现(勾选框随缩进, 徽章右对齐不占轨道)—— 若希望徽章紧贴名称右侧而非右对齐, 只需去掉 `.dt10-pbadge`/`.dt11-pbadge` 的 `margin-left:auto`, 单 point 可调。
2. 报告 26-10-14-0136 §02 的其余问题面(点击乱选/点击跳动/无排序/合并态丢内容等)待用户决定开工范围时再立项; §04 开放问题(样板面先行 vs 逐面修、双通路关系)仍无结论。
