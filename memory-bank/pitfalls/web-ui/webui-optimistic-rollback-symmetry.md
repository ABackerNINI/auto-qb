# 乐观补丁覆盖面扩到行以外时, 回滚面必须同点对称

> 摘要: 给乐观补丁加第二个覆盖面(如抽屉 detail)时, 失败/超时回滚若只还原行, 新覆盖面就停留假状态 —— 贴与回滚必须经同一单点对称, 且「行采不到 prev」的场景要有独立回滚锚
> 触发: 乐观 UI, 乐观补丁, 回滚, 覆盖面, 对称, 抽屉 detail, drawer.detail, applyOptimisticPatch, applyOptimistic, 贴补丁, 失败回滚, 兜底回滚
**Refs:** memory-bank/issues/26-10-30-0818-bug-webui-rename-rollback-drawer-detail.html

### 贴补丁多写一个面, 回滚出口没跟上 —— 失败后新覆盖面停留假状态

- **触发**: 给 `applyOptimisticPatch`(或 `applyOptimistic`)的补丁加第二个覆盖对象(2026-10-31 实例: editRename 按 D3 把 `drawer.detail.name` 同步改新名)。写贴上时顺手, 写回滚时只想得起 `_forEachRow` 三数组 —— commands.js 的**两条**回滚出口(resolveOptimistic 失败分支 / _expirePending 兜底)只要漏一条, 失败/3s 无回执后新覆盖面就停留新值。
- **判别**: 症状 = 行上回滚正常、第二个面停留假状态直到重开/重拉(issue 26-10-30-0818: 抽屉标题回落分支停留新名)。特别注意消费点可能有**优先级回落**: drawerTitle 优先 memberByHash(行引用, 行回滚自动跟随), 只有 hash 不在视图三数组才读 detail —— 恰好「行不在视图 + 面开着」时第二个面是唯一旧值落点, 此时 `applyOptimisticPatch` 连 `op.prev` 都采不到(空遍历), 盲等回滚会拿到空 prev 无值可退。
- **处置**: ①回滚收敛到**一个单点**(commands.js `_syncDrawerRollback(hash, patch, rolled)`), 两条出口都调它, 回滚值与行**同源**(op.prev, 兜底时 `t || op.prev` —— 兜底要回「最后已知真值」, 见 contract-api.md「"真值到达" ≠ "值覆盖结束"」); ②只写 patch 出现过的键, rolled 缺键跳过不写垃圾; ③行不在视图时由调用方(editRename)把面侧旧值**回填进 op.prev**当回滚锚; ④面没开着/hash 不匹配时跳过(重开自然重拉), 不越权写。
- **守阵**: `tests/test_webui_optimistic_rename_alt.py` rename 四态 node 电池 7 条对称断言(失败/兜底两出口还原 detail; 行不在视图回填锚; 抽屉不在该 hash/已关不碰; 兜底同回最后已知真值)。**新消费者加第二个覆盖面时应扩本电池, 静态守阵看不出来**。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
