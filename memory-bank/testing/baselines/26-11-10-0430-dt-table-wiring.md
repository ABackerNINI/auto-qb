# 5879 passed + 2 skipped —— dt_table 真接线 W3 收尾基线

> 摘要: dt_table 真接线 W3 收尾基线
> 基线时间: 2026-11-10 04:30
**Refs:** memory-bank/plans/26-11-10-0027-plan-dt-table-wiring.html

## 验收数字

```text
TOTAL                                                26152     41   9102     53    99%
5879 passed, 2 skipped in 123.66s (0:02:03)
```

(实测时点: HEAD e22d89f2 + 本波工作树改动(仅 e2e 注释与 memory-bank 记账面, 零生产代码), `commands run test.full` 2026-11-10 04:28; 全绿, 较上基线 26-11-10-0051 的 5877 passed +2 —— W1/W2 两波新增守阵用例计入)

## 本改动面

- **W3① e2e 口径改述**(本波唯一代码文件): `e2e/dt-table-layout-parity.spec.mjs` 头注释追加「口径更新」段 —— 几何已是 DT_TABLE.layout 单点(columns_grid._gridTemplate/colAlignCss 内部委托, 旁路拼接已删), 本守阵不再是「两处计算一致」的 parity 比对, 语义改为**钉住单点输出不变**; 断言逻辑零改动, face-bg spec 未动。
- **W3② 记账面**: issue 26-11-08-0147 翻 Done(补复验/修复后补充, 附三笔提交 hash acc496d1/f0e9800f/e22d89f2); 计划 26-11-10-0027 翻 In Progress + §10 R1 行(用户终验四面 06/09/10/11 待真机, D5 点头后才翻 Done 关单); 事实回写 architecture/webui.md(新「表格几何单点」节)+ overview.md 六包边界行同步; 根 README 核对无涉表格几何表述, 零改动。
