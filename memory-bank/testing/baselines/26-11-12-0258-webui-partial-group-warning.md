# 6011 —— webui 部分组操作预警: S1-S6 实施完成基线

> 摘要: webui 部分组操作预警: S1-S6 实施完成基线
> 基线时间: 2026-11-12 02:58
**Refs:** memory-bank/tasks/26-11-11-webui-partial-group-warning.md

## 验收数字

```text
TOTAL                                                26747     55   9362     66    99%
6011 passed, 2 skipped in 185.79s (0:03:05)
```

(实测时点: 本批 `commands run test.full` 2026-11-12; 2 skipped 为存量 skip; 缺口净额 0 —— miss 55 + partial 66 = 121 与上片持平; 本切片为本批组合树的测试数字权威, 其余处一律引用不手抄)

## 本改动面

- `src/auto_qb/webui/static/shared/selection.js`: S1 部分组判定谓词 `_partialGroupsOf` 单点 + 聚合 `_partialGroupsSummary` 单点(跨组归并/整组判定同一处, 供三落点复用)。
- `src/auto_qb/webui/static/shared/delete_flow.js`: S2 删除确认框部分组行 —— 带文件删除×部分组时在确认框插入醒目预警行(组内未全选即触发)。
- `src/auto_qb/webui/static/shared/drawer.js`: S3 迁移关提交前确认框(部分组×迁移关移动) + S4 迁移开披露条(级联全组知情提示)。
- `src/auto_qb/webui/static/shared/tpl/move-dialog.html`: S4 披露条区块(迁移开形态的部分组披露条 markup)。
- `src/auto_qb/webui/static/shared/state.js`: S4 `movePartialDisclosure` 状态键(披露条可见性接线)。
- `src/auto_qb/webui/static/{atlas,console,flux,prism}/css/dialogs.css`: 四皮肤统一 warn 档配色(预警行/披露条/确认框同档样式)。
- `tests/test_webui_static_r4_node_batteries.py`: 守阵电池 —— 判定/聚合/三落点文案与接线 node 真跑覆盖, 含接缝终审对称单点锚修复(工作树未提交改动随本批入库)。
- 文档面: `memory-bank/architecture/webui.md` 新节(部分组预警机制), 根 README 辅种管理节 bullet, 计划 26-11-11-0820 / 任务档案 26-11-11 状态翻转(Done)。
