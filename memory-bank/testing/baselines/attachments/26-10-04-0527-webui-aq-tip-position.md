# 基线切片 26-10-04-0527 — 状态栏上传速度 tooltip 定位修复 (aq-tip: 锚点脱离重解析 + 竖向不越锚点)

> 摘要: 用户报「WEBUI状态栏的上传速度tooltip位置错误, 出现时会挡住元素本身」。常规窗口尺寸
> (1280/1440/1024/900/800/640 × atlas/prism/console) 用 Playwright 实测**复现不出**(浮层正常在
> 按钮上方 6px、仅横向被右缘夹取); 深挖后在 `shared/ui_feedback.js` 的 `show()` 定位到两处真缺陷:
> ①锚点在 350ms 延时窗口内被 Vue 轮询整个换掉时已脱离文档, `getBoundingClientRect()` 全 0 ⇒ 浮层
> 落到视口左上角 `(8,6)`; ②竖向末尾**无条件**把浮层夹回视口内, 底缘锚点(状态栏)走「转下方」分支
> 时被拉回状态栏上 —— 正好盖住它自己描述的元素。修法: 锚点 `!isConnected` 时按 `mouseover` 记下的
> 指针坐标 `elementFromPoint()` 重解析(解析不到就收起); 竖向改「上方优先 → 转下方 → 两侧都放不下
> 才允许溢出视口」, 任何分支都不越过锚点。改动单文件 `shared/ui_feedback.js`(27+/8-)。

- 时间: 2026-10-04 05:27 (GMT+8); 会话起点 sync 至 7da54233(树脏挡路 → `git stash push -u` → sync → `git stash pop`)
- 分支: develop @ 7da54233(+ 本轮未提交改动: ui_feedback.js + memory-bank 回写件)
- 命令: `commands run test.full`
- 实测: **2442 passed + 4 skipped, 47.76s, 覆盖率 TOTAL 99%**(14495 语句 / 135 未覆盖 / 4864 分支 / 106 partial; 门槛 98% 达标 98.73%)
- 相对上基线(26-10-04-0414: 2423 passed + 3 skipped)用例数 **+19 / +1**: 来自同期合入的远端提交
  7da54233(qB 流量图时间窗扩十档, `tests/test_traffic_grid.py` / `tests/test_web.py` 扩写), 非本轮新增;
  本轮为纯前端行为层修复, **零新增/删改用例**
- 收尾回写件未落齐时 test.full 曾有 4 条 memory-bank 守卫为红(索引未重生成 / 新坑档链接未落),
  补齐回写件 + `kb.index` 后同批转绿, 用例数与覆盖率不变
- 另做 Playwright 几何验证: ①常规尺寸 sweep 与修复前**逐像素一致**(防回归); ②节点替换用例 box 由
  `[8,6,291,41]` 回到 `[989,731,1272,766]`; ③`vh` 76→50 逐档 `overlap === false`(旧版 vh=70 实测 overlap=true)
- 未验证面: 真机三皮肤状态栏 hover 走查(用户环境若仍复现需截图/窗口尺寸); Linux (WSL) 侧未重测
  (与上条基线同口径)
