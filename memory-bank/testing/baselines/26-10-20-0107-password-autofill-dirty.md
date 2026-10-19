# 3758 passed + 10 skipped —— 密码框自动填充造脏修复

> 摘要: 密码框自动填充造脏修复
> 基线时间: 2026-10-20 01:07

## 验收数字

`commands run test.full`(本机 Windows, 仓库自带 TMPDIR 前缀), 实测输出:

```text
TOTAL                                                20328    390   6956    262    98%
3758 passed, 10 skipped in 202.43s (0:03:22)
```

口径注记:

- 相对上一条基线 +1 passed —— 即本轮新增的静态守阵 `test_frontend_password_field_ignores_autofill`; 差值逐位对比见 `commands run kb.baseline -n 2`, 本文件不重复。
- 0 failed / 0 error; 覆盖门(--cov-fail-under 98)照过(98%)。
- 浏览器侧另有 e2e 两条用例(常规页 / HR 在线核实页), 双皮肤共 **4 passed / 12.8s**, 用 `dev.e2e` 按名字 grep 单跑; 回退两个源文件后同一个 grep **4 failed**(两条都红, HR 那条红在行为断言上), 恢复后复绿 —— 红绿双向都验过。HR 那条用 `page.route` 现注入带 `hr_check.channel` 的配置树(桩配置没有这一段, 整块默认关闭则不渲染密码行)。全量 e2e 未跑(本轮只动设置页一个 `kind=password` 分支, 其余断言面零接触)。

## 本改动面

| 文件 | 改动 |
|---|---|
| `src/auto_qb/webui/static/shared/tpl/xtpl.html` | 密码分支: 密码 input 加 `autocomplete="new-password"`; 写回由 `@input="set($event.target.value)"` 改为 `@input="setSecret($event)"`; 分支头注补「自动填充不得写进配置树」的理由与事故日期 |
| `src/auto_qb/webui/static/shared/config_editor.js` | `CE_FIELD_BASE.methods` 新增 `setSecret(ev)`: 事件到达时 `document.activeElement !== el`(**未聚焦 = 自动填充**)一律不写树, 并把显示拉回树值; 聚焦才 `cfgSetPath` |
| `tests/test_webui_static_dom_page.py` | 新增静态守阵 `test_frontend_password_field_ignores_autofill`(三皮肤聚合模板断言 `autocomplete` / `setSecret` 接线 / 未直连 `set()`, 并钉 `setSecret` 的焦点判据与回填分支) + 文件头测试计划一行 |
| `e2e/views.spec.mjs` | 新增两条 e2e: ①「设置-常规: 密码框被自动填充不得造脏」—— 真实手势进设置→常规, 断言 `autocomplete` 属性、未聚焦填充后 actbar 仍「已与磁盘同步」+ 保存按钮禁用 + 显示回填, 再对照聚焦键入照旧翻「有改动还没保存」; ②「设置-HR 在线核实: 端点密钥同样不被自动填充写脏」—— 用户追加报障的那一页(`hr_check.channel.token` 与常规共用同一密码分支), 桩无该段故用 `page.route` 注入配置树 |

未触碰: 配置读取/写盘/后端校验、其它字段类型、登录页(`autocomplete=current-password` 是它该有的语义)。
