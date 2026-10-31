# 2791 —— 流量图缺口斜纹**几何**修复基线(第一次修复未成功后的二次修复)

> 摘要: 用户复报「WEBUI 流量图断线区域标注**未落到正确的区域**, 且其**倾斜超出了范围**(第一次修复未成功)」。真根因 = `_qbDrawGaps` 用 45 度线段铺缺口时**只把外层 clip 收到整个绘图区**, 涂出的并集是"宽 = 图高 H 的**斜向平行四边形**"(左右边界皆斜边), 缺口右段下半留白、左段上半越界到缺口左侧。第一轮修复只改了配色令牌, 当时把几何缺陷误判为"颜色不可见导致无法判读落点", 并写下"几何经代数证明恒等、无缺陷"的**错误结论**(代数只证了"两式等价", 未回答"画出来该是矩形还是斜带", 两式同错)。修法 = **逐 run 追加一次 clip 到缺口矩形** `ctx.rect(xa, T, xb-xa, H)` + `xa<xb` 退化守卫。纯前端静态层(1 个 js) + 守阵(既有函数内加断言 / 扩 node 电池), Python 产品代码零改动。
> 档案: (单会话小修, 未立档案 —— 见 activeContext 切片)
> 基线时间: 2026-10-08 11:44

**Refs:** memory-bank/activeContext/26-10-08-1130-webui-qb-traffic-gap-hatch.md,memory-bank/pitfalls/web-ui/canvas-hatch-token.md,memory-bank/testing/baselines/26-10-08-1130-webui-qb-traffic-gap-hatch.md

## test.full 实测

- 分支: `develop`(工作树含本专题回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **2791 passed + 4 skipped, 0 failed, 32.8s, 覆盖率 TOTAL 99%**
  (16476 语句 / 162 未覆盖 / 5694 分支 / 146 partial; 门槛 98% 达标)
- 本专题守阵单跑: `uv run pytest tests/test_webui_static_dom_panel.py -k yaxis --no-cov -q` → **1 passed in 3.19s**;
  文件全量单跑 → 29 passed(口径同上基线)。
- 红验(本专题新增几何锚): 删掉 `_qbDrawGaps` 里的 per-run 缺口矩形 clip 三步后重跑,
  node 电池 20 项中 **1 项按预期变红**(`存在逐 run 缺口矩形 clip(ctx.rect(xa, T, xb-xa, H))`),
  还原后复绿 —— 证明新几何锚非假锚、真的钉住了本次缺陷。
- 相对上基线 [26-10-08-1130](26-10-08-1130-webui-qb-traffic-gap-hatch.md)
  (2791 passed + 4 skipped, 语句/未覆盖/分支/partial 同口径 16476/162/5694/146):
  passed **±0** / 语句 **±0** / 未覆盖 **±0** / 分支 **±0** / partial **±0**。
  - 口径说明: 本专题**未新增测试函数** —— §5b 静态锚加在原函数 `test_frontend_qb_traffic_yaxis_and_annotation`
    内(新增 2 条 assert), node 电池在原 `_NODE_QB_YAXIS_PROBE` 内**扩写**(新增 6 项几何判定)。
    故 passed 计数不变; 机械贡献 = 既有函数内断言/电池项条数增加。
- 4 skipped 为 Windows 侧 POSIX 专属存量。

## 本专题面要点(非 pytest)

- **真根因(几何)**: 45 度线段水平跨度恒为 `H`; 只按底端 x 扫 `[xa, xb+H]` + 外层仅裁**绘图区**
  ⇒ 并集 = 宽 `H` 的斜带(平行四边形)。**必须逐 run 再裁一次到目标矩形** `[xa, xb] × [T, T+H]`。
- **第一轮的错**: 把"位置错 + 看不清"两症状判成**同源**(皆配色), 用代数恒等"证明"几何无缺陷 ——
  但恒等只证两式互等、未证形状正确。**坑档已回改**(原"几何无缺陷"结论已删除并纠正)。
- **守阵判据的坑**: `ctx.clip()` 是画布操作, **不改写**记账式假 ctx 记到的 `moveTo/lineTo` 端点
  ⇒ 不能断言"原始端点落在 `[xa,xb]` 内"(它们本就该越界, 靠 clip 收)。正确判据 =
  "per-run 缺口矩形 clip 存在且 == 目标矩形" + "扫线覆盖目标矩形两个竖直边界" + "线段跨度恒 = H"。
- **真值判据**: 栅格化模拟(逐像素判定覆盖范围)+ 真浏览器 canvas 渲染截图, 直接看**画出来的形状**
  是否等于目标矩形 —— 而非看两段代码是否等价。

## 对照判据(后续沿用)

- 以本切片(2791+4 / 16476 / 162 / 5694 / 146)为对照点: 预期 passed 只升不降、未覆盖 / partial 不升。
- 本专题**未新增测试函数**, 后续若有人误以为"改守阵必须 +1 passed"会算错账 —— 加断言到既有函数里不涨计数。
