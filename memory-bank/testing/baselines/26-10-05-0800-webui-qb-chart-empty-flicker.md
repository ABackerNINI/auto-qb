# 基线切片 26-10-05-0800 — WEBUI qB 流量图空态/错误态闪烁修复

> 摘要: 用户报「qb流量图闪烁『暂无 qB 口径流量数据(程序运行期间无采样)』/『暂无该种子的 qB 口径流量
> 数据(从未有传输记录)』」。根因 = 2026-10-04 静默续拉的 loading 空态门写窄了: 门在「无点」上
> (`!qbCurPoints.length`), 只覆盖「已有图」一态 —— 空数据集(程序刚开/该种子从未传输)没有点, 每个
> 轮询周期 `_qbLoad` 一亮 loading 就把空态文案顶掉一帧再换回; 错误态同理(请求前 `error=""`)。
> 修法 = 判据改「本作用域有无落袋结果」: `qbCurPending = qbCurLoading && !qbCurData && !qbCurError`,
> 且 `_qbLoad` 不再在发请求前清 `error`(改由成功落袋清)。坑档
> [drawer-switch-flicker](../../pitfalls/web-ui/drawer-switch-flicker.md) 复发 +1(第三次)。
> 基线时间: 2026-10-05 08:00

**Refs:** memory-bank/activeContext/26-10-04-0448-webui-qb-chart-poll-flicker.md

- 分支: develop @ 62d71ec0 (+ 本轮未提交改动: shared/qb_traffic_chart.js / shared/tpl/drawer.html /
  tests/test_web.py / 坑档 drawer-switch-flicker.md 及其 `_index.md` / activeContext 切片 / 本切片)
- 命令: `commands run test.full`
- **实测 (Windows)**: **2567 passed + 4 skipped, 49.9s, 覆盖率 TOTAL 99%**
  (15477 语句 / 162 未覆盖 / 5240 分支 / 136 partial; 门槛 98% 达标)
- 相对上一条基线 (26-10-05-0630: 2567 passed + 4 skipped / 99% / 46.0~47.6s): passed / skipped /
  语句 / 未覆盖 / 分支 / partial **六组数字完全相同**(改动只在前端静态资源与测试, 不在 `src/` 的 .py);
  耗时 49.9s 落在近几条切片 43.5~51.1s 的噪声带内, 非回归。
- 靶向 (tests/test_web.py -k qb_traffic): 1 passed —— 守阵**不增用例**, 把既有那条
  `test_frontend_qb_traffic_chart_wiring` 的 loading 空态锚由「模板门 `!qbCurPoints.length`」
  换成「模板门 `qbCurPending`」并**新增两锚**(三合一判据本体 / `_qbLoad` 里 `error` 清除只允许出现在
  `await this.api(` 与 `this[def.data] = data;` 之后), docstring 两处同步。
- 改动面: `src/auto_qb/webui/static/shared/qb_traffic_chart.js`(qbCurPending 新判据 + `_qbLoad` 的
  error 清除点后移 + 文件头「静默续拉」段重写) · `src/auto_qb/webui/static/shared/tpl/drawer.html`
  (loading 空态门 `v-if="qbCurPending"` + 注释) · `tests/test_web.py`(守阵换 1 锚 + 增 2 锚 + docstring)。
  **后端 `traffic_qb.py` / `core/traffic_*` 零改动**(本次纯前端渲染状态问题)。
- 机检 (Playwright + 真 `create_app` 桩 + 空数据目录 / 恒 500 两场景, 逐 20ms 采抽屉正文文本; 驱动脚本
  一次性用完即删, 未入库 —— 复现配方见坑档同条「触发/判别」):
  ①空数据目录: 修前「暂无…」↔「正在加载流量数据…」每 2s 翻一次(14s 内 11 次, 全局图与单种页签两挂点
  都中), 修后 **0 次**(首载那一次 loading 仍在); ②`/api/traffic/qb/**` 恒 500: 修前错误文案↔loading
  每周期翻, 修后恒为错误文案(单次 正在加载 → 错误文案)。
- 未验证面: 真机走查(用户实测空态不再闪 / 有图态与换窗 24h<->30d / 换肤后图色正确)留待用户。
- Linux 侧本轮未重测 —— 改动为纯前端静态资源 + 测试, 无平台分支; 下次 `test.linux` 自然复核。
