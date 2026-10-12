# 3146 —— 变体模板表格闪烁修复(桥锚驻留 dtHoldAnchors + 三层探针取证)

**Refs:** memory-bank/pitfalls/web-ui/drawer-switch-flicker.md,memory-bank/activeContext/26-10-12-2026-webui-drawer-tpl-flicker-fix.md,memory-bank/testing/baselines/26-10-12-1800-webui-drawer-table-rework-u5.md

> 摘要: 用户报「WEBUI种子详情模板所有表格闪烁, 修复」。修复 = `drawer_templates.js` 新增 `dtHoldAnchors`(早分支清帧后把离文档的记账锚接回宿主 `display:none` 隐藏持有)+ `anchFill` 归位后 display 复位, 全程 +40 行。取证三层(单 rAF 采样循环 + `__stop` 标志): ① 静态数据 20s×3 锚/头/表/首行身份全程不变(peers 段 1853 帧 rowFlips=0); ② API 级数据 churn(route 截拦 `/peers` 速度逐拍变, 静态桩测不到的真实路径)1445 帧 `rowFlips=0` `uniq=1`; ③ 空↔非空 flap 锚身份全程唯一、表头幸存、gen 不升、控制台零报错。**探针伪影反转**: 曾报「2,0,2,0 完美交替、blank 恰好一半」的周期性闪烁读数实为双 rAF 循环共享同一数组的探针 bug。抽屉回归 44/44。
> 基线时间: 2026-10-12 20:31

上一基线：memory-bank/testing/baselines/26-10-12-1800-webui-drawer-table-rework-u5.md

## 验收数字

- `test.full`: **3146 passed + 4 skipped** / 覆盖率 `TOTAL 16708 161 5688 140 99%`(上一基线 3145 passed + 4 skipped; +1 未追因到单条 —— 本波改动仅 `drawer_templates.js` +40 行与知识库回写, 数值以本次实测为准)。
- 抽屉回归(dev.e2e 子集, 本波改动面直接覆盖): drawer-bridge-stub + trackers/peers/content 三套 variant-tables + peers-sticky-flush + drawer-merge 共 **44 passed / 0 failed**(57.3s)。
- 三层探针(临时, 未进仓库): 见摘要 ①②③; 18 个 zz-* 探针全部清除。

## 本波改动面

- **生产代码**(`src/auto_qb/webui/static/shared/drawer_templates.js`, 唯一): `dtHoldAnchors` 模块函数(`_dtRender` 成功后、`dtSyncAnchors` 前调用; 判据 `!el.isConnected`; catch 回落路径不驻留)+ `anchFill` 归位后 `display` 复位(只在真被置过时写)。
- **知识库回写**: 坑档 `drawer-switch-flicker.md` 追加「复发 +1(第六次)」(契约面判别 + 探针自证纪律 + 残留设计内说明); activeContext 新切片 `26-10-12-2026-webui-drawer-tpl-flicker-fix.md`。

## 已知偏差 / 移交

- 残留(设计内非缺陷): 空列表拍桥的 `.group-table` 行容器随 `v-if` 行数卸载、回来重挂 —— 空态期锚整体 `display:none` 不可见, 用户看到的是空态语义本身(P3-5); 表头不重挂。若用户真机复现的正是空↔非空振荡且对重建敏感, 再议 `v-show` 化(动 rowAfter/roving 重挂语义, 有回归面)。
- 存量转告(同 U5): ① `modules/webui-static-contract.md` 超 evergreen cap(33,064 > 20,000, 本波未增长 —— 修复属既有模式, 回写落坑档不入模块文档); ② 切片数债务(kb.check 报 > 70, 本波 +1); ③ 引擎表头 a11y 缺口 issue 26-10-12-0800(Open 未认领)。
- 未跑 dev.e2e 全量(206 用例): 本波改动面经 44/44 抽屉回归覆盖, 全量 e2e 留待下次波次基线或用户指令。
