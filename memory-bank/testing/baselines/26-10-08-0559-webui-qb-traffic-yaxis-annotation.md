# 2772 —— 流量图纵轴固定模式 + 画布注解层基线

> 摘要: 用户命题「WEBUI 流量图添加纵轴最大值固定模式(可切换; 限速+20% 或手动 MiB/s; 峰值超上限按峰值显示; 覆盖全局/种子/辅种分组三挂点)」+ 一并认领 issue 26-10-07-0149(13 变体限速虚线/缺口斜纹注解层, 用户拍板改为**共享图面**)。纯前端静态层改动(qb_traffic_chart.js / state.js / drawer.html / 三皮肤 views.css)与测试侧守阵, Python 产品代码零改动 ⇒ 相对上基线 26-10-08-0518(2771+4)passed **+1**(本轮新增守阵 `test_frontend_qb_traffic_yaxis_and_annotation`), 覆盖率口径逐位持平。
> 档案: memory-bank/tasks/26-10-08-webui-qb-traffic-yaxis-annotation.md
> 基线时间: 2026-10-08 05:59

**Refs:** memory-bank/tasks/26-10-08-webui-qb-traffic-yaxis-annotation.md,memory-bank/issues/26-10-07-0149-feat-webui-traffic-chart-annotation-layer.html

## test.full 实测

- 分支: `develop`(工作树含本专题回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2772 passed + 4 skipped, 0 failed, 48.44s, 覆盖率 TOTAL 99%**
  (16476 语句 / 165 未覆盖 / 5694 分支 / 149 partial; 门槛 98% 达标)
- 同树复测区间: 48.44s ~ 49.77s(回写前 / 回写后各一次, passed 与覆盖四项**逐位相同**;
  单次数字不单独作基准)。
- 相对上基线 [26-10-08-0518](26-10-08-0518-backend-test-web-split-s7s8.md)
  (2771 passed + 4 skipped @ 50.97s, 同 16476 语句 / 165 未覆盖 / 5694 分支 / 149 partial):
  passed **+1**(新增守阵函数) / 语句 **±0** / 未覆盖 **±0** / 分支 **±0** / partial **±0**。
- 增量明细: `tests/test_webui_static_dom_panel.py` 新增 1 个测试函数(含 2 组 node 真跑电池:
  `_qbYRange` 值域 5 例 + `_qbGapRuns` 缺口游程 5 例); `tests/test_webui_error_history.py` 仅改
  `STORAGE_WRITE_BASELINE` 里 `qb_traffic_chart.js` 1 → 2(setItem 调用点新增一处, 非新增测试)。
  4 skipped 为 Windows 侧 POSIX 专属存量。
- 旁证(非 pytest): `npm run test:e2e:fast` **8 passed**(含「渲染健康: Vue 挂载成功…无运行时错误」),
  真浏览器加载 vendor + 组件跑注解钩子自检 **零 pageerror**, 带钩子画布比不带多 9,870 个已绘制像素。

## 本专题面要点(非 pytest)

- 纵轴三态单点: `QB_YAXIS_MODES`(auto/limit/manual) + `QB_YAXIS_LIMIT_FACTOR=1.2` +
  `QB_YAXIS_MIB`; 上限派生单点 `_qbYCapOf(scope)`(limit = qB 全局限速上下行**较大者** ×1.2,
  manual = MiB 换算, auto = 0); 值域纯函数 `_qbYRange(dmax, cap)` = max(cap, peak*1.05) ——
  **上限只保底, 峰值超出按峰值显示**。
- 持久化粒度 = **三作用域各自独立**(`autoqb.ui.qbYAxis{Global,Torrent,Group}`, 与窗口档位的
  「全局单独 / 组种共用」不同, 用户拍板); 初值 `qbInitialYAxis` 只认合法模式 + 正数手动值。
- 切档/改值走 `_qbChartRescale` = `setData` 重算 scale(不重建图、不重取数); 限速值变化由
  `mounted` 注册的 `$watch` 重排(长窗轮询可夹到 600s, 否则固定上限迟迟不生效)。
- 注解层画在**同一张画布**(共享图面): `drawClear` 钩子画缺口斜纹(系列之下)、`draw` 钩子画限速
  虚线(系列之上); uPlot 1.6.x 的 ctx **无 transform** = 设备像素, 新增 `_qbCanvasScale` 统一按
  `uPlot.pxRatio` 转 CSS 像素坐标; 色值走建图时读到的令牌(限速线随方向, 斜纹取 `grid`)。
- 限速虚线只画**落在可视值域内**的限速(自动模式下峰值未超限速即不画 —— 用户拍板); 0/null 不画。
- 三皮肤 CSS 成对(`.qb-tools` / `.qb-seg` / `.qb-yaxis-input`); 控件在 `shared/tpl/drawer.html`
  流量正文块内, 三挂点 + 经典/所有变体全生效。

## 对照判据(后续沿用)

- 以本切片(2772+4 / 16476 / 165 / 5694 / 149)为对照点: 预期 passed 只升不降、未覆盖 / partial 不升。
