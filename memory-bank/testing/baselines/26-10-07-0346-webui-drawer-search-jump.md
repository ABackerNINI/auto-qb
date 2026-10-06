# 2690 —— WEBUI 详情面板/流量图搜索筛选跳动修复收尾 (develop, 源码小修轮)

> 摘要: 修复「种子详情面板/流量图在搜索/筛选时跳动」—— 搜索首词待响应窗空命中集把列表塌成
> 0 行(文档高塌掉 → 滚动钳回 0 → 面板失去 sticky 锚点弹跳)+ 短列表下 sticky 吸底脱锚。
> 修法 = searchPending 门(view/state/filters) + 三皮肤 .layout min-height 撑满首屏(--head-h 单点)。
> 改动: view.js + state.js + filters.js + 三皮肤 CSS + test_web.py(新守阵) + e2e 新 spec。
> 基线时间: 2026-10-07 03:46

**Refs:** memory-bank/tasks/26-10-07-webui-drawer-search-jump.md

- 分支: develop @ **2e2d6789**(开工 sync 快进 47ce4452→2e2d6789, 本轮尚无本地提交)
- 命令: `commands run test.full`(Windows)
- **实测 (Windows)**: **2690 passed + 4 skipped, 覆盖率 TOTAL 99%(16021 语句 / 163 未覆盖 /
  5472 分支 / 143 partial)**; pytest 自报 **36.88s**(commands 包脚本计时 41.7s 含开销)。
- e2e: `npm run test:e2e` 默认矩阵 **84 passed + 10 skipped**(含新增
  drawer-dock-stability.spec.mjs 2 条); `test:e2e:fast` 6 passed(原 4 + 新 2)。
- 相对上一条 [26-10-07-0251](26-10-07-0251-webui-drawer-tab-traffic-form-guard.md)
  (2689 + 4 / 16021 / 163 / 5472 / 143): passed +1(新增静态守阵 1 条), 覆盖四指标逐位相同
  —— 前端 JS 不进 `--cov=src` 统计, 新增 e2e spec 不进 pytest 收集面。
