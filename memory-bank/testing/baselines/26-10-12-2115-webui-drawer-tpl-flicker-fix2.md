# 3147 —— 多锚变体组churn整桥重挂修复(dtSyncAnchors 按(tid,seg)对账)

**Refs:** memory-bank/pitfalls/web-ui/drawer-switch-flicker.md,memory-bank/activeContext/26-10-12-2115-webui-drawer-tpl-flicker-fix2.md,memory-bank/testing/baselines/26-10-12-2031-webui-drawer-tpl-flicker-fix.md

> 摘要: 用户回流「闪烁没有修好 + 数据不实时刷新而是随闪烁刷新 + 疑与 5s 自动刷新有关」。根因 = `dtSyncAnchors` 多锚位置逐位比假阳: 08/05 段集合随活数据增减/重排(组空整节隐藏→锚丢记账、组补→新锚)被误判"换代" → gen++ → 整桥(所有组的表)重挂 = 每 5s 全表格闪, 数据只随重挂刷新。修复 = 对账改按 (tid, seg) 映射的元素身份(仅同一 seg 锚被换新才换代; seg 增/消失不换代)。组 churn 探针实锤: 修复前 08 每拍全部 seg 的 table/表头身份全换; 修复后驻留组锁死(驻留被换=0), 仅新进组建新, 行文本每拍实时更新; 05 同结果; 07 单锚对照零变化。抽屉回归 44/44。
> 基线时间: 2026-10-12 21:15

上一基线：memory-bank/testing/baselines/26-10-12-2031-webui-drawer-tpl-flicker-fix.md

## 验收数字

- `test.full`: **3147 passed + 4 skipped** / 覆盖率 `TOTAL 16708 161 5688 140 99%`(与上一基线 3147 持平 —— 本波仅前端对账逻辑改写, 无测试增删)。
- 抽屉回归(dev.e2e 子集): drawer-bridge-stub + trackers/peers/content 三套 variant-tables + peers-sticky-flush + drawer-merge 共 **44 passed / 0 failed**。
- 组 churn 探针(临时, 未进仓库): 08/05 每拍"驻留组被换=0"、行文本每拍更新; 07 单锚对照 seg→table 身份 17s 内 1 次(仅首挂); 07 内容探针 A(数值 churn 1445 帧级)零重挂零隐藏帧、B(空↔非空 flap)锚身份唯一。

## 本波改动面

- **生产代码**(`src/auto_qb/webui/static/shared/drawer_templates.js`, 唯一): `dtSyncAnchors` 对账改写(位置数组比对 → (tid,seg) 映射的元素身份比对; `__dtAnchorEls` 记账形状 `{tid:[el]}` → `{tid:{seg:el}}`); dtHoldAnchors/anchFill 沿用第六次修复不动。
- **知识库回写**: 坑档「复发 +1(第七次)」(根因/判别/处置/验证/探针纪律三条新增); activeContext 切片 `26-10-12-2115-webui-drawer-tpl-flicker-fix2.md`。

## 已知偏差 / 移交

- anchTouch(筛选 chips / 只看在传)仍按设计整表换代重读 rowsFn —— 用户主动交互路径, 非轮询, e2e 已覆盖(44/44)。
- 存量转告(同前): ① `modules/webui-static-contract.md` 超 evergreen cap(33,064 > 20,000, 本波未增长); ② activeContext 切片数债务(> 70, 本波 +1); ③ 引擎表头 a11y 缺口 issue 26-10-12-0800(Open 未认领)。
- 未 commit / 未 push(用户未发指令); 若用户真机复现面是其它变体或仍有残余闪烁, 按组 churn 探针手法(内容级 + 身份级 + 抽屉作用域)扩展取证。
