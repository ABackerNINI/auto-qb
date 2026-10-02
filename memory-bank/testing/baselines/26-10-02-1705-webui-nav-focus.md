# 基线 · 2290 passed + 3 skipped / 99% —— WEBUI 导航焦点不变式修复轮

> 摘要: 键盘切页旧页签残留焦点框修复(tpl/topbar.html data-view + view.js::syncNavFocus) + ui_smoke「导航焦点」双断言 + 档案/坑单/切片回写。档案: [tasks/26-10-02-webui-nav-focus.md](../../tasks/26-10-02-webui-nav-focus.md)。
> 基线时间: 2026-10-02 17:05, develop @ f83a0db6(收尾回写未提交工作树, test.full 实测)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。

TOTAL **2290 passed + 3 skipped / 99%**(13,251 语句 / 86 未覆盖 / 4,436 分支 / 81 partial,
test.full 29.3s, rc=0)。
相对上一切片(26-10-02-1653: 2290 passed + 3 skipped / 99%, @ 6ea89ff4)passed/skipped/覆盖率
全持平; 语句 13,349 → 13,251(-98)来自**基点移动**(本轮 sync 合入远端至 f83a0db6), 本轮 src/
改动仅前端模板与 JS、不触 Python 语句数。另: ui_smoke.cjs 双 UI **104 项 0 失败**(含新增
「导航焦点」4 断言, playwright-core@1.63 + chromium-1243)。
