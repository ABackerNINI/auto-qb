# e2e 里 route 改写做"状态翻腿"在增量轮询下恒空转 —— 页内态翻转要么 vm 注入要么整页重载

> 摘要: e2e 想用 `page.route('**/api/state*')` 改写回包做「同一页面 A/B 两腿状态切换」(翻 Node 侧 flag 让下一轮回包不再注入 → app 回落原态)时,**翻腿后 app 永远吃不到新态**: 桩的增量轮询在数据版本未变时**不回传行**(polling.js:345「版本未变时响应体已趋近于零(不回传 groups)」), 响应体里没有 groups/torrents, 改写器根本没机会动那些行 —— app 保留旧渲染态(2026-11-20 实测: 翻腿后 expect.poll 15s 不清零, pair 行纹丝不动, `fetches.plain` 计数涨而 DOM 不变)。可行的两条路: ① **vm 注入**改行对象字段(delta 轮询不重投递未变行, 注入态跨多个轮询周期存活, 实测 >13s; 属 lib/vm.mjs D4 守则允许的「注入/复原桩态」类); ② **两次整页加载**各跑一腿按行 key 差分(无竞态但每腿一次 goto 的时长成本)。
> 触发: e2e 翻腿不生效; route 改写后页面状态不变; expect.poll 超时但页面"看起来对"; A/B 两腿测试第二腿恒空转; exposeFunction 翻 flag 没效果

## 触发 / 判别 / 处置

- **触发**: 一个 spec 要在**同一页面**上先量 A 态再切 B 态(或反向), 选了 route 改写 + Node 侧闭包 flag(`page.exposeFunction` 让页面翻 flag)。
- **判别**: 翻腿后 `expect.poll` 一直拿旧态, 但 route 处理器的腿计数在涨(说明回包在走、flag 也翻了) —— 差点在"回包没带行"这一步: 打桩 `json.groups` 长度, 翻腿后的回包里它是 `undefined`/0。
- **处置**:
  - 首选 **vm 注入**: 直接改 `vm.groups / vm.torrents` 行对象的字段(如 `g.relocate = job` / `= null`), 配「注入数 == 可见行数」覆盖守卫防轮询冲掉部分注入(冲掉的行会让 B 腿假绿)。参照 e2e/relocate-pair-row-height.spec.mjs。
  - 页面级大改(注入不动的态)用**两次加载** A/B, 按 data-key/data-hash 对齐差分, 别在单页里翻。
  - 别假设"桩每 2s 全量重建就一定全量回传" —— 重建≠重发, 发不发由**版本/增量机制**决定; 写依赖轮询回包形态的断言前先打一趟回包形状。
- **同族**: relocate-pair-filter.spec 头注「标注随 rebuild 稳定重现」说的是**初载全量回包后标注稳定存在于 app 态**, 不是"每个轮询回包都重发行" —— 引用它当"全量回传"依据会踩进本坑(2026-11-20 实踩, 白写一版翻腿实现)。
