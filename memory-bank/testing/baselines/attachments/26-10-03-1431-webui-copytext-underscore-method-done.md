# 基线 · 2390 passed + 3 skipped / 99% —— 复制钮 _copyText 模板解析修复轮(issue 26-10-03-1412)

> 摘要: 单 issue 修复轮: 抽屉常规页 / 弹窗详情行复制钮 `@click="_copyText(...)"` 在 Vue 3.5 模板里解析不到
> (`_` 前缀为内部保留域, 真浏览器抛 `ReferenceError: _copyText is not defined`), 按 issue 建议修法①
> 在 `commands.js` 补无前缀别名 `copyText`(内部转 `this._copyText`), 两处模板改调别名;
> 并落地防复发守阵 `test_frontend_template_no_reserved_prefix_identifiers`(test_web.py,
> 插值+指令表达式两类形态, `$event` 白名单), 已红验证命中修复前原文。
> 基线时间: 2026-10-03 14:31, develop @ da23e842(先在 e7165781 实测 2375 passed, 提交前同步合流远端
> qB 流量图 P3 一笔后在 da23e842 复测, 工作区含本轮修复与回写件)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。

TOTAL **2390 passed + 3 skipped / 99%**(13,996 语句 / 127 未覆盖 / 4,728 分支 / 99 partial,
test.full 35.1s, rc=0)。
相对上一切片(26-10-03-1335: 2329 passed + 3 skipped / 99%, 13,433 语句 / 88 未覆盖 / 4,542 分支, @ f89c9e06)
**passed +61** —— 合流远端提交(qB 口径流量图 P1/P2/P3 等)带入的用例 60 条 + 本单新增守阵 1 条;
语句 / 分支增长(13,433→13,996 / 4,542→4,728)同源, 均为合流件而非本单(本单纯前端别名与守阵)。
