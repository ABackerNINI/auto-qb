# 5947 passed + 2 skipped —— 规则页条件树 ce 透传修复批收尾全量绿

> 摘要: 5947 passed, 2 skipped (138.54s), 覆盖率 99% (26307 stmts / 50 miss / 9176 br / 62 partial) —— WEBUI 规则页条件树 aq-cond-node/aq-choose-block 补 ce 透传修复批收尾全量绿; e2e fast 三 shard 336 passed(含新增回归 spec 2 例, 远端并行批新增守阵使总数较 310 增长)
> 基线时间: 2026-11-11 03:59

## 验收数字

```text
TOTAL                                                26307     50   9176     62    99%
5947 passed, 2 skipped in 138.54s (0:02:18)
```

## 本改动面

- `src/auto_qb/webui/static/shared/config_rules.js`: `AQ_COND_NODE_COMPONENT` / `AQ_CHOOSE_BLOCK_COMPONENT` 补 `inject:["ce"]` + `provide(){ce:this.ce}` 透传(traffic_card.js:13-20 同款范式) —— 全局 mixin(CONFIG_EDITOR)给每个组件挂 provide(){ce:this}, 宿主组件不透传时内嵌 hub-field 注入到中间实例(mixin data 新建 cfg 副本 tree=null), 条件叶子「＋ 添加」抛 TypeError 被吞、「?」浮窗开不出、叶子编辑写坏副本全丢(用户报障, Playwright 桩服复现实锤)。
- `e2e/rules-cond-editor.spec.mjs`: 新增回归 spec(SKINS 两皮肤): 建规则集/规则(真实手势, 只动客户端草稿树不落盘) -> 条件叶子列表「＋ 添加」写路径往返(vm 草稿树探针, 非缺省态) -> 「?」浮窗开/关 -> choose 第二现场(when 加叶子 + then 加动作规范形写树); 摘掉透传 2 例全红(TypeError 被 console 守卫 + 写路径断言双抓), 恢复全绿。
- `memory-bank/pitfalls/web-ui/mixin-ce-inject-break.md`: 复发 +1(W3-A/W3-B 新增组件没把透传当必填项; 判据应读作「任何 hub-field/ce 消费者的非根直系祖先组件都必须透传」, 触发关键词补第二现场词面)。
- 评审: 分批评审 3 轮(全能档单派): 轮 1 修复面 0 发现; 轮 2 发现 2 条(major: spec choose 段缺 ce 介面写路径交互, 守阵对该组件单摘零鉴别力; minor: 坑档复发行守阵口径夸大)当场修; 轮 3 复核零 actionable。
- 与上片差值: passed/skipped 与覆盖率全部持平(前端 + e2e 改动, 不进 py 覆盖率); e2e fast 总数 336(含上述回归 spec 两皮肤 2 例; 与早先中间值 310 的差 = 远端并行批新增的守阵例)。
