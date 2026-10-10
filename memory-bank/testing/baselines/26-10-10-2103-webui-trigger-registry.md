# 3064 —— WEBUI 触发点登记表 + 作用域静态守阵(S1+S2, 零行为改动)基线

> 摘要: 计划 26-10-10-2001(专题 `webui-selection-trigger-parity`)的 S1+S2 落地。起因: 现状把「动谁」拆在 **7 个目标解析点 + 7 个动作出口 + 1 个平行变体判定**上, 互不引用 —— 于是「选中 A 却动了 B」这类**静默作用对象偏移**(不报错/不白屏/不弹 toast)既无断言覆盖, 也无声明可查。S1 落口径单点 `conventions/webui-scope.md`(三态作用域 sel/anchor/cursor + C1–C5 契约 + 四条偏差机制); S2 落声明式登记表 `shared/triggers.js`(`ui` 36 行 + `calls` 30 行)与静态守阵 `tests/test_webui_trigger_registry.py`(6 条)。**本笔不含任何行为改动** —— 登记与断言只读源码, 触发点与出口的行为逐位不变。**「自动停靠」的机制**: T1 判据取 `method: "POST"` 而非端点字面量(reannounce 的计划投递端点来自变量, 只认字面量会留盲区), 覆盖面因此从 11 处扩到 30 处, 并把 `scope: "none"` 的全局资源类操作也纳入表内(豁免也要写理由, 白名单不复存在) ⇒ 新功能要么走统一出口(网②自检), 要么登记进表(网①强制), 否则当场判红。
> 基线时间: 2026-10-10 21:03

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 快进 `905447df`→`727b72e2`; 工作树含本轮改动 + 回写件时实测)
- 命令: `commands run test.full`(Windows, 两次采样: 回写件落盘前 30.74s / 齐备后 30.75s —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **3064 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16586 语句 / 156 未覆盖 / 5724 分支 / 143 partial; 门槛 98% 达标; 本轮 30.74~30.75s)
- 增量明细(本轮真正新增): `src/auto_qb/webui/static/shared/triggers.js`(登记表常量 `TRIGGER_DEFS` +
  `window.AQB_TRIGGERS.triggerDefs()`; 三份 `index.html` 清单各加一行 + `app.js` 补 `app.mixin`,
  prism shell 已在 210 行硬顶故顺手去掉一处多余空行腾位)/ `tests/test_webui_trigger_registry.py`
  (新文件 6 条: 形状 / T1 投递点双向相等 / T2 出口外不得展开选中集合 / T3 菜单变体对账 /
  T4 四支动作族奇偶 / T5 登记不存在的入口); 回写件 `conventions/webui-scope.md` + 计划 meta 与
  §5.4/§6/§8/§9 更新 + 本基线切片 + 会话切片。
- 静态守阵红验(四条, 均还原即绿):
  - 在 `drawer.js` 加一个未登记的新方法 `__redprobePost`(内含 `method: "POST"`) → T1 报
    `AssertionError: 这些 POST 调用点的所在方法没有登记进 TRIGGER_DEFS.calls: drawer.js::__redprobePost`。
  - 删掉 group 支的「标签/分类…」项(复现 2026-10-09 缺选项) → T4 报
    `AssertionError: group 支缺扩展动作族 ['meta']`。
  - 在 `menu.js::_ctxMulti` 里插一行 `[...this.selMembers]` → T2 报
    `AssertionError: 选中集合的展开出现在出口之外`。
  - 把登记表某行 `entry` 改成 `metaGroupX` → T5 报
    `AssertionError: ui 行 ctx.group.meta 声明的 entry 'metaGroupX' 不是任何片段里的方法`。
  - 另一条**非人为**的红: 首次跑 T1 时登记表自己的文件头注释含 `method: "POST"` 字样, 被扫成表外项
    (`triggers.js::None`) ⇒ 已把登记表自身排除出扫描面(它不投递, 唯一方法只返回常量), 并在代码注释里留了原因。
- 真浏览器(`@fast` 门禁): `npm run test:e2e:fast` **50 passed(1.3m)** —— 三份清单新增脚本后
  浏览器端装载正常(填槽 `/shared/triggers.js`), 无运行时错误。
- 未纳入本轮(刻意不越界): 计划 S3(descriptor 单点 + 出口收敛为三个 `_dispatch*`; 唯一必要的行为改动
  是拆掉 `_kbEditAct`/`_kbTorrentCmd` 借道 `menu.hash` 的写法)、S4(运行时 `scopeAudit`)、
  S5(e2e 参数化矩阵)、S6(菜单项集声明化) —— 按计划 §8 建议留后续轮次。
