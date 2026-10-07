# 详情面板变体骨架去重: reg.helpers 单点收口 (Done)

> 摘要: 认领 issue 26-10-07-0845(P3-8)并完成 —— 核心层 drawer_templates.js 增设 `reg.helpers`
> 骨架单点(工具 dur/size/present/num + skipUnchanged sig 比对 + withScroll 滚动自保 + 
> wireEvents/unwireEvents 挂摘成对), 变体 01-12 共 12 份全部改为消费 helpers, 删除各自复刻的
> `__dtNNWired`/scroller 直读写骨架; 04/05/06 的同名 `num` 是非负谓词语义(另一函数)未并入。
> 13/14/15(traffic)无监听、走引用浅比较, 本就不在重复面。净 -111 行(195+/306-)。
> 守阵同步: scrollleft_restore 改钉核心单点+变体不得回潮; a11y 挂摘断言改走 helper 口径。
> 验证: test.one -k drawer_tpl 8 passed; **test.full 2712 passed + 4 skipped / 99%**(基线
> 26-10-07-0940)。issue 置 Done + kb.index 重建。
> 最后活动: 2026-10-07 09:40

**Refs:** memory-bank/issues/26-10-07-0845-refactor-webui-drawer-tpl-dedup.html · memory-bank/testing/baselines/26-10-07-0940-webui-drawer-tpl-dedup.md

## 现状

- 改动面: drawer_templates.js + drawer_tpl/01-12 共 13 份 JS + tests/test_web.py(两个守阵口径),
  零 Python 产品代码改动。改动随本专题入库。
- 设计要点: 挂摘记账收敛到单一 `host.__dtEvents` 事件表, 成对纪律由 helper 实现保证(变体声明
  事件表即可); withScroll 只包整帧换帧段, loading/error/empty 早退分支行为不变(照旧不还原滚动)。
- 后续候选(未入池): 10/11/12 无滚动自保(原状), 若要补属行为增强非去重; fmtSpeedOf 闭包(07/08/09
  三份)太小不值得抽。
