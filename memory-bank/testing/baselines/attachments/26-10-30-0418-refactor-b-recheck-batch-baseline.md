# 4086 passed + 2 skipped(根) —— B 类复核批次 14 单 refactor 收口后全量基线

> 摘要: B 类重复代码复核批次 14 条 open refactor issue 全部收口(issue 置 Done)后的全量基线
> 基线时间: 2026-10-30 04:18
**Refs:** memory-bank/issues/26-10-29-1310-refactor-b-r10x03-exempt-baseline-single-source.html,memory-bank/issues/26-10-29-1321-refactor-b-r16b02-delta-cancel-helper.html,memory-bank/issues/26-10-29-1327-refactor-b-r13s01-lane-summary-twin.html,memory-bank/issues/26-10-29-1328-refactor-b-r08e02-episode-pattern-family.html,memory-bank/issues/26-10-29-1334-refactor-b-r20c07-spec-list-empty-write.html,memory-bank/issues/26-10-29-1340-refactor-b-r21a06-file-prio-text-table.html,memory-bank/issues/26-10-29-1343-refactor-b-r21c06-content-file-tree-two-copies.html,memory-bank/issues/26-10-29-1343-refactor-b-r21c07-tracker-bucket-table-shapes.html,memory-bank/issues/26-10-29-1354-refactor-b-r23b13-drawer-host-vfor.html,memory-bank/issues/26-10-29-1355-refactor-b-r23b15-settings-inline-svg.html,memory-bank/issues/26-10-29-1403-refactor-b-r24a02-wait-until-helpers.html,memory-bank/issues/26-10-29-1404-refactor-b-r24a03-hr-service-builder.html,memory-bank/issues/26-10-29-1405-refactor-b-r24b03-relocate-env-builder.html,memory-bank/issues/26-10-29-1406-refactor-b-r24b08-endpoint-pointer-writer.html

## 验收数字

`commands run test.full`(pytest `-n 8 --cov-branch --cov-fail-under=99`(pytest.ini addopts, TMPDIR 由 task 内置); 2026-10-30 实测, 全量 132.33s, 建档 04:18):

```
  TOTAL                                                21061    102   7126    103    99%
  4086 passed, 2 skipped in 132.33s (0:02:12)
```

- 汇总行: **4086 passed + 2 skipped(根)**; 覆盖率门槛 99% 通过(TOTAL 行 99%)。
- 逐条口径注记:
  - 本基线树 = 14 条 B 类复核 refactor issue 修复提交(8fd15867/409f36fc/6441a707/bfd19fda/0075d3ce/79dc6b52/6dc63e5b/3c9de728/b3949cf0/541ede4b/a1ccda70/58f3d798/cf7357cb/2bd0e234)逐单合入后的 HEAD `2bd0e234`; 每单的定向数字与 test.quick 逐单数字在各提交信息与本单 issue 的状态变更日志里, 不在此复抄。
  - 「2 skipped(根)」为既有环境条件 skip, 与本批次无关(`26-10-30-0139-expr-hr-guard-delegate` 等近期切片同为 2)。
  - 批次内唯一行为变更: issue 1310 豁免线基准 3×req → 3×(req+extra)(用户拍板 req+extra; 默认站型 9D → 10.5D, extra=0 部署零变化), 其余 13 单为等价收敛/纯测试面/死代码删除。

## 本改动面

| 面 | 内容 |
| --- | --- |
| tests/ 单点收口 5 单 | 1403 wait_until · 1406 write_endpoint_pointer · 1405 relocate_env · 1404 make_service(HR 装配, 落 hr_helpers) · 1321 _cancel_delta_buckets(webui 源码内测试面单点, 属 src) —— 均删逐字副本收共享层单点, 断言零改动 |
| 死代码删除 1 单 | 1334 config_rules.js 八个无调用者 spec 编辑死助手(用户拍板方案 A, 零行为影响) |
| webui 前端收敛 5 单 | 1354 抽屉宿主/桥 dtTabItems v-for · 1355 设置页图标 sprite 化 · 1340 PRIO_TEXT/prioText 单点 · 1343-C07 tracker 五桶文案表 reg.trackers 单源 · 1343-C06 content 目录树 buildFileTree 单点(统一节点模型) |
| 规则/HR 语义 3 单 | 1328 集数正则族不合并只补守阵负测 · 1327 波次摘要三部件单点落 hr/model(拍板全深度+透传 status) · 1310 豁免线派生属性单点(拍板 req+extra, 行为变更见上) |
| 配套 | 每单新增/扩展守阵与红验各见其提交; 各 issue 状态变更日志已留痕(修法一句/提交 hash/定向验证) |
