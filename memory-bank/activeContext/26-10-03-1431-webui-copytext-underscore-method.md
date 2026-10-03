# 复制钮 _copyText 模板解析失败 — issue 26-10-03-1412 修复置 Done

> 摘要: 认领修复抽屉/弹窗复制钮 issue, 采用建议①(无前缀别名) + 建议③(两类形态静态守阵)。
> 最后活动: 2026-10-03 14:31

## 已完成 (2026-10-03)

- **复验**: 用户真浏览器复验提供 console 原文 `ReferenceError: _copyText is not defined` —— 与坑位
  `pitfalls/web-ui/vue-reactivity.md`「模板里不允许下划线前缀标识符」判别一致, 仍复现, 按根因修复。
- **修复**: `commands.js` 在 `_copyText` 旁新增无前缀别名 `copyText(text, label)`(内部
  `return this._copyText(...)`), `shared/tpl/drawer.html:72` 与 `shared/tpl/popovers.html:126`
  两处 `@click` 改调别名; `drawer.js:442` 的 `this._copyText` 纯 JS 调用点不动(右键菜单复制不受影响)。
- **守阵**: `tests/test_web.py::test_frontend_template_no_reserved_prefix_identifiers` ——
  扫全部 `shared/tpl/*.html` + 三 UI shell 内联段的**插值与指令表达式两类形态**(复发 1 的根子即
  事件绑定形态没被认出来), `_`/`$` 前缀裸标识符即红; `$event` 白名单(Vue 内建),
  `obj._x` 成员访问不拦。已红验证: 修复前两处 `@click="_copyText(...)"` 原文喂同一扫描逻辑均命中。
  文件头测试计划同步登记。
- **回写**: issue 置 Done(封面徽标 + meta + 状态日志: 复验原文 / 实际修法 / 守阵 / 验证数字),
  坑位条目补守阵行, issues/_index.md 重生成。
- 收尾: 基线切片 [baselines/26-10-03-1431](../testing/baselines/26-10-03-1431-webui-copytext-underscore-method-done.md)
  (2390 passed + 3 skipped / 99% @ da23e842; passed +61 主要来自合流远端 qB 流量图 P1/P2/P3 件, 本单 +1 守阵)。
  不满足立档阈值(单轮单 issue, 2 源文件 + 1 测试文件); 坑位已有条目, 只补守阵行未新增。
- 真浏览器点复制钮的最终确认待用户下一轮 UI 冒烟(静态与全量测试已覆盖)。

## 状态

任务完结, 本轮随 ship.commit 入库(用户已授权提交; 同步 @ da23e842)。
