# 基线切片 26-10-05-1759 — 流量图窗口选择持久化 + 三条快捷键

> 摘要: qB 口径流量图 UX 补完 —— ①窗口档位(13 档)选择落 localStorage(粒度按用户拍板: 全局单独一份
> `autoqb.ui.qbWinGlobal` / 分组与种子共用一份 `autoqb.ui.qbWinShared`, 换窗即落盘刷新保持), 档位清单收成单点
> `QB_WINDOW_NAMES` 同时喂展示(`v-for="w in qbWindowNames"`, 去模板 13 档硬编码)/前后切换/持久化校验;
> ②三条快捷键: 打开全局图 `Ctrl+Backslash` / 详情面板流量页签 `Alt+5` / 窗口前后切换 `[` `]` —— 后两条新增引擎
> **`when` 条件绑定**(仅 `qbTrafficActive` 时消费键位, 无图时不 preventDefault 留给浏览器)。
> 新增守阵 2 条(红验通过)+ 一次性 node 探针 22/22; 种子流量图并入详情面板一项经核对**当前代码已实现**, 非本轮改动。
> 基线时间: 2026-10-05 17:59

**Refs:** memory-bank/tasks/26-10-05-webui-qb-traffic-window-persist-shortcuts.md

- 分支: develop @ c2ba6054(会话开工同步 `my-commit-flow.sync`; 工作树含本轮改动: 4 源码 + 2 测试 + 本切片 + activeContext 切片)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2619 passed + 4 skipped, 44.24s / 44.15s / 43.89s(三次采样: 回写前 / 回写后 / 终态含档案+索引重建), 覆盖率 TOTAL 99%**
  (15802 语句 / 167 未覆盖 / 5392 分支 / 140 partial; 门槛 98% 达标)
- 增量构成: 相对上一条**本 clone** 基线 [26-10-05-1723](26-10-05-1723-webui-commands-js-indent.md)(2610 + 4 @ a4d14a8d):
  passed **+9** = ① 会话开工同步并入的 **reannounce 确认重构**守阵 **+7**(bf12a487..43af8240, 见切片
  [26-10-05-1202](26-10-05-1202-reannounce-confirm-rework.md)「净增 +7」)**+** ② 本轮净增 **+2**
  (`test_web.py::test_frontend_qb_traffic_window_persist_and_single_source` +
  `test_web_shortcuts.py::test_qb_traffic_shortcuts`)。语句 15702→15802 (+100), 分支 5342→5392 (+50),
  未覆盖 164→167, partial 138→140, 覆盖率 99% 持平。
- 靶向验证: 新增两守阵红验(摘 `when` 分流 → shortcuts 守阵红; 摘 `persistQbWindow` 调用 → web 守阵红; 恢复后绿);
  `commands run test.one -- tests/test_web_shortcuts.py` 27 passed; `tests/test_web.py -k "qb_traffic"` 全绿;
  `node --check` 三改文件语法 OK; 一次性 node 探针(临时, 已删)22/22 覆盖持久化粒度/校验/夹取/`when` 分流/新入口不撞旧键。
- 改动面: `src/auto_qb/webui/static/shared/{qb_traffic_chart.js, shortcuts.js, state.js, tpl/drawer.html}` ·
  `tests/{test_web.py, test_web_shortcuts.py}` · 本切片 + activeContext 切片 · `kb.index` 生成物。
- 未验证面: 真浏览器交互未跑(本 clone node 侧 Playwright 缺失 ⇒ `dev.harness`/`ui_smoke.cjs` 不可用; 且桩 harness
  未开 `qb_traffic`, 图表本不在既有冒烟覆盖内) —— 待用户真机走查窗口保持 / `[` `]` 手感 / 两条入口键。
