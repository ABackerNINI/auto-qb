# 6270 passed + 2 skipped(Windows) —— HR 三表迁 aq-table grid 链路第二轮 W1-W3 全量基线(计划 26-11-17-0059)

> 摘要: HR 三表迁 aq-table grid 链路第二轮 W1-W3 全量基线(计划 26-11-17-0059)
> 基线时间: 2026-11-18 01:00
> 档案: memory-bank/tasks/26-11-17-webui-hr-table-grid.md

## 验收数字

`commands run test.full` 实测(2026-11-18 01:03, Windows, 2m52s):

```
TOTAL                                                27855     73   9822     78    99%
6270 passed, 2 skipped in 172.19s (0:02:52)
```

覆盖率闸 99.5% 达成(test.full silent_success 只留结论行, 同树上一轮实测覆盖率 99.59% —— 两轮 TOTAL 表逐位一致, 差异仅 1 条 ASCII 闸红已修)。

e2e 侧(本计划对象面): `e2e/dt-table-layout-parity.spec.mjs` **22 passed**(55.2s, 双皮肤; 含 W3(1) 新增 HR 三面 hrDetail 10 / hrWave 8 / hrKv 2 列, route 拦截喂合成载荷) + `e2e/hr-history.spec.mjs` **4 passed**(11.6s, W3(2) 回归)。

## 本改动面

- `e2e/dt-table-layout-parity.spec.mjs`(+194): W3(1) parity 守阵增 HR 三面 —— HR_CASES(hrDetail/hrWave/hrKv, openDiag 区分「排障视图」details 内外表) + hrStatusPayload/hrEntriesPayload 合成载荷(对齐 SiteStatus/EntryDetail.to_dict + 路由层 local_present) + openHrModal 导航(设置 hub → HR 卡片 → 站点状态弹层, 手势链 hr-history 同族) + 三 test 双皮肤, 探针与抽屉面同规格(轨道数/列头格数/行子格数/左缘±1px/text-align)。
- `src/auto_qb/webui/static/shared/hr_status.js`(头注微调): 表身份段补一行 W3(1) parity 守阵事实。
- 文档回写: `memory-bank/architecture/webui.md`(D4 例外清单收缩为「仅 04 卡片」+ HR 三表终态事实 + 守阵条补 HR 三面 + 触发词), 根 `README.md`(HR 节补列交互面), 计划 26-11-17-0059(§10 R2 变更记录 + doc-updated 抬戳, doc-status 保持 Open 待用户终验), 任务档案续作(子任务状态表 W1/W2 翻 Done)。
- 本切片。
