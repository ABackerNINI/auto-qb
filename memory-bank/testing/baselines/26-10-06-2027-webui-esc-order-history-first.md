# 2682 —— Esc 退栈顺序修正: 历史弹层先于抽屉 (@ 已入库 91964997)

> 摘要: 用户报「qB 流量图与历史流量图同开时 Esc 应先关历史流量图」。根因 = `lifecycle.js` Esc
> 退栈链把抽屉分支(`drawerVisible`)排在历史弹层(`historyOpen`)之前, 与视觉层叠(遮罩 z-index 130
> > 抽屉 80)相反。改动全在前端 JS 与测试/文档(`lifecycle.js` 链序 + `test_web.py` 顺序断言 +
> `pitfalls/web-ui/overlays.md`), **不进 `--cov=src` 的 Python 统计** ⇒ 覆盖四项与上一条逐位相同。
> 基线时间: 2026-10-06 20:27

**Refs:** memory-bank/activeContext/26-10-06-2027-webui-esc-order-history-first.md

- 分支: develop @ **250c5951**(开工 `commands run my-commit-flow.sync` = `已同步 250c5951`;
  本轮改动已入库 **91964997** —— 提交内部同步把本地提交 rebase 重放 14c19184→91964997,
  Gitee develop 核验一致)
- 命令: `commands run test.full`(Windows; 本机 R 盘临时目录被污染, 本次把临时根指到 C 盘绕过
  sessionfinish 的 `PermissionError … pytest-current` 假红 —— 非回归, 见 pitfalls/testing/tmpdir)
- **实测 (Windows)**: **2682 passed + 4 skipped, 覆盖率 TOTAL 99%**; pytest 自报 **46.00s**。
  语句 **16021** / 未覆盖 **163** / 分支 **5472** / partial **143**。
- 相对上一条 [26-10-06-1955](26-10-06-1955-memory-bank-timekit.md)
  (2682 + 4 / 16021 / 163 / 5472 / 143): passed / 语句 / 未覆盖 / 分支 / partial **五项逐位相同**
  —— 本轮未碰 `src/` 的 Python 代码(`lifecycle.js` 与 `test_web.py` 都不在覆盖率口径内)。
- 本轮真正验收: `test.one -- tests/test_web.py -k "qb_traffic_chart_wiring or ..."` **2 passed**
  (新增 `hist_at < drawer_at` 顺序断言随原守阵跑绿); 定向 `tests/test_web.py tests/test_web_shortcuts.py`
  **339 passed + 1 skipped**。
