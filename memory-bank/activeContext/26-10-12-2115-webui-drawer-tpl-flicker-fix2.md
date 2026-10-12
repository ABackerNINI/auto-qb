# 多锚变体组churn整桥重挂修复 · dtSyncAnchors 按(tid,seg)对账（第七次复发闭环）

> 摘要: 用户回流报障「闪烁问题没有修好, 且引入了新的问题, 数据不实时刷新, 而是随闪烁刷新, 猜测闪烁问题可能和『5s 自动刷新』有关」。定位实锤: `dtSyncAnchors` 多锚比对是**位置数组逐位比**(注释写"按元素集合"实则按位置), 而 08 五分组/05 健康分组的段集合随活数据增减/重排是常态(组空整节隐藏→锚丢出记账、组补→换新锚), 集合内容没变也被误判"换代" → `gen++` → **整桥(所有组的表)重挂** = 5s 轮询每拍全表格闪, 且重挂恰是 rowsFn 重读点 = 数据只随闪刷新。探针实锤(组 churn: dict 形态 + 每拍组 membership 轮换 + 速度抖动): 修复前 08 每拍**所有** seg 的 group-table/表头身份全换(e1-e4→e13-e16→e22-e25→e31-e34); 修复后驻留组身份锁死(每拍"驻留被换=0"), 仅新进组建新(该组此前不可见无闪烁), 行文本每拍实时更新; 05 同构同结果; 07 单锚对照零变化(单锚段集合恒 1, 位置比恒真, 本来就不闪 —— 上波探针只测 07 故全绿而用户仍在闪)。修复 = `dtSyncAnchors` 改写: `__dtAnchorEls` 记账 `{tid:[els]}` → `{tid:{seg:el}}`, 判据改为"仅同一 seg 的锚元素被换新才换代"; seg 新增/消失不换代(新段随 v-for 新挂进新锚; 消失段随 rowsFn 同判据卸载, 无游离 teleport)。dtHoldAnchors/anchFill 不动(第六次修复仍必要)。验证: 组 churn 探针(08+05)+ 07 内容探针 A/B 无回归 + 抽屉回归 6 套 **44/44** + `test.full` **3147 passed + 4 skipped / 99%**。

> 最后活动: 2026-10-12 21:15

**Refs:** memory-bank/pitfalls/web-ui/drawer-switch-flicker.md,memory-bank/tasks/26-10-12-webui-drawer-table-rework.md

## 根因与修复(一句话)

- 根因: 多锚变体(08/05)段集合随数据增减/重排 + `dtSyncAnchors` 位置逐位比假阳 → gen++ → 整桥重挂(每 5s 全闪, 数据随重挂刷新)。
- 修复: `drawer_templates.js` `dtSyncAnchors` 按 (tid, seg) 映射比对元素身份; `__dtAnchorEls` 形状随之改为 `{tid:{seg:el}}`(仅本函数消费, `_dtUnmountOne` 清账不受影响)。

## 探针纪律新增(本轮教训, 已入坑档)

- 身份探针测不出"数据冻住" —— 必须同记行文本时间线;
- 行文本选择器必须限定抽屉作用域(主列表同用 `.group-row`, 全局 query 曾把种子名当对端行);
- 数组/dict 双形态都要测(真 qB `sync/torrentPeers` 恒 dict + rid/full_update/peers_removed)。

## 停手点

- 未 commit / 未 push(用户本轮未发"提交"指令); 工作区唯一生产改动 = `src/auto_qb/webui/static/shared/drawer_templates.js`(dtSyncAnchors 对账改写 + 注释)。
- 坑档已追加「复发 +1(第七次)」完整条目; 基线切片 `26-10-12-2115-webui-drawer-tpl-flicker-fix2.md`。
