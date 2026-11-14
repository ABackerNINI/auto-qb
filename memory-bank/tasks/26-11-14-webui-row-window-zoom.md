# 26-11-14-webui-row-window-zoom — zoom!=1 行窗口化 pad 坐标空间错配修复

**Status:** In Progress
**Added:** 2026-11-14
**Updated:** 2026-11-14
**Summary:** 修 issue 26-11-14-0844: zoom!=1 分数布局下贴文档底后行窗口化渲染窗整体错位(~1900px), 根因 = gBR/scrollY 视觉空间 vs style.height 布局空间错配, pad 是唯一不闭环出口; _rowWindow 两 pad 出口按 _winZoomOf 实测有效缩放 1/z 换算
**Topics:** webui-row-window-zoom

## 本篇只回答

zoom!=1 时行窗口化渲染窗为什么整体错位、怎么修的、怎么验证的。领域结论(坐标空间模型/取整陷阱)单点在坑档 `memory-bank/pitfalls/web-ui/css-zoom-coordinate-space.md`, 本篇不重复。

## 原始请求

1. 用户:「修复memory-bank/issues/26-11-14-0844-bug-webui-zoom-window-misalign.html」—— 修复 issue 本体(zoom!=1 分数布局贴文档底后渲染行整体落在视口上方约 1900px, flux 全部行不可见)。

## 思考过程与决策

- **定位**: issue §05 候选方向是「_rowWindow 取整/取界偏差」, 实测定案后**改道**: Chrome 探针(html zoom 0.9)实测 scrollY/scrollHeight/gBR 全按视觉空间报数(43.7 布局 → 39.325 视觉), 窗口选行与前缀和在视觉空间内自洽, 千九百像素级错位是系统性坐标空间错配而非取整噪声 —— pad(style.height = 布局空间)是唯一不闭环出口。
- **有效缩放测量口径三轮收敛**: ①computed zoom 不可读(Chrome 不把 zoom 报成继承, 实测 body 恒 "1"); ②gBR.width/offsetWidth 比值有 offsetHeight 取整相对误差(~1450px 容器上 0.034%, 放大到 ~19000px padTop 上 ~6px, 实测撞红 flux 像素带判据 T7/S-A); ③终选 gBR.height / getComputedStyle().height(used 值, 布局空间分数精度, zoom=1 时比值数值等价 1 至多 1ulp)。
- **窗口选择自洽性**: pre 前缀和与 rel 在同一(视觉)空间, gap(computed rowGap = 布局空间)混入前缀和会在选行与 pad 渲染两端同枚抵消 —— 除 pads 外全链零改动。
- **测试基线数字只写一处**: issue 收口句改为引用基线切片, 不手抄(评审轮 2 发现 3)。

## 实现计划

1. Chrome 探针实测定坐标空间模型(gBR/scrollY 视觉 vs style/computed 布局)。
2. columns_grid.js: 新增 `_winZoomOf` + `_rowWindow` 两 pad 出口按 1/z 换算 + `_winSigExtra` 加根缩放令牌。
3. node 语义电池 +3 条 zoom 换算 checks(webui_dom_page_support.py, 23/23 + 活性注入必红); r4 两电池 ctx 补 `_winContainer` 桩; 阈值 18→20。
4. 新 e2e `row-window-zoom.spec.mjs` 三皮肤(先 zoom 后贴底 = 用户真实流次序, 修复前 flux 必红); T8 flux 解跳。
5. 收尾 DoD: code-review 三轮(6 发现全修, 检 6/6)→ issue Done → 坑档 → test.full 基线切片 26-11-14-1250。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 探针实测坐标空间模型 | Done(2026-11-14) |
| 2 | _winZoomOf + pad 1/z 换算 + _winSigExtra 根缩放令牌 | Done(2026-11-14) |
| 3 | 电池 +2 checks / 桩 / 阈值 | Done(2026-11-14) |
| 4 | e2e row-window-zoom + T8 flux 解跳 | Done(2026-11-14) |
| 5 | 收尾 DoD(评审/issue Done/坑档/基线切片) | Done(2026-11-14) |

## 进度日志

### R0 · 立档 (2026-11-14)

修 issue 26-11-14-0844 全链完成: 修法见坑档修法契约; 验证 = node 电池 23/23(活性注入必红)+ e2e row-window-zoom 三皮肤绿(修复前 flux 红验红)+ T8 六条全绿 + test.full 全绿(数字见基线切片 26-11-14-1250)。评审六轮 9 发现全修(blocker 0); 另判得 drawer-dock-stability 两条 flux 用例整 spec 顺序既有 flake, 经用户拍板入池 26-11-14-1323。真机自检: 本缺陷为纯前端浏览器几何面, e2e 真浏览器(chromium)已实测复现与修复, 桩可验 —— 未另跑真机轨。

**Refs:** memory-bank/issues/26-11-14-0844-bug-webui-zoom-window-misalign.html, memory-bank/pitfalls/web-ui/css-zoom-coordinate-space.md, memory-bank/testing/baselines/26-11-14-1250-webui-zoom-window-misalign.md, memory-bank/issues/26-11-14-1323-bug-drawer-dock-flux-fullspec-flake.html

review: 轮 1 全能档 1 派遣 5 发现(minor 3/nit 2)全当场修; 轮 2 核验 4 修复 + 新增 1 nit(自相矛盾注释)当场修; 轮 3 零发现出口; 轮 4(入池 flake 档后批 409 行, 派发 2 串行)2 发现(docstring 旧分母措辞 + _winSigExtra 根缩放令牌零覆盖)当场修(电池补第 3 条钉子); 轮 5 核验 2 修复 + 新增 1 nit(in-test docstring 枚举与头部不一致)当场修; 轮 6 零发现出口。

- 2026-11-14 13:00 修 issue 26-11-14-0844: zoom!=1 pad 坐标空间错配, _winZoomOf 实测缩放 + pad 1/z 换算 + e2e/电池收口
