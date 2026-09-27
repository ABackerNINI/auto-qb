# 26-09-28-webui-dialog-gap-warn-expand — WEBUI 弹窗按钮排间隙 + 跳检警告塌缩展开

**Status:** Done
**Added:** 2026-09-28
**Updated:** 2026-09-28
**Summary:** 标签/分类弹层「完成」与添加种子「取消/添加」与上文间隙过小 —— 三套皮肤 `.modal-actions` 统一 `margin-top: 16px`(相邻兄弟 margin 折叠取最大, 不叠加)。跳检警告行原为 FX-21「常驻占位」(visibility 切换, 空白恒占), 改为整行塌缩/展开: 未勾选 `max-height/margin-top/opacity` 全归零零占位, 勾选后 0.22s 过渡展开、下方内容平滑下移。三套 UI 成对改; 真浏览器专项量测通过; test.full 1817 passed(基线 26-09-28-0702)。
**Topics:** webui-dialog-gap-warn-expand

## 原始请求

用户报: ①「WEBUI添加标签页的"完成"按钮与上方的间隙太小, 添加种子中的"取消"/"添加"也有同样的问题」; ②「添加种子页中的跳检警告的留空很突兀, 改为不留空, 点击"跳过校验时"在下方插入警告, 同时下方的元素都往下移, 但需要添加过渡动画, 不能突兀」。

## 思考过程与决策

- 间隙根因: `.modal-actions` 无 top margin, 间隙全靠上文元素自身 margin-bottom —— `.modal-body` 有 18px 所以确认框正常, 而 `.mgr-hint`(标签弹层)与 `.add-dialog-body`(添加种子)没给足, 视觉贴死。修 `.modal-actions` 一处全局受益; 相邻兄弟 margin 折叠取最大值, 对已有 18px 的确认框零影响(守恒不叠加)。
- 警告行: 保留 FX-21「节点常驻」的实现载体但反转占位语义 —— 原「常驻占位」用 `visibility:hidden` 保高度不变(勾选前后窗口不跳), 代价是空白恒占; 用户明确要"不留空 + 过渡动画"。塌缩态 `max-height:0 + opacity:0 + margin-top:0 + overflow:hidden`, 展开态 `max-height:4.5em`(11.5px 字号单行实测 17-18px, 4.5em 容三行折行余量) + `margin-top:7px`, transition 三属性齐动(0.22s/0.18s/0.22s)。高度过渡量真实文本, 不人工估高。
- 选择器用双类 `.add-dialog-hint.add-dialog-hint-warn`(2/3 类): prism 的 views.css:601 另有一条单类 `.add-dialog-hint { margin: 0 }`, 单类对单类级联看 link 序不可靠, 双类稳赢。
- 三套 UI 成对改(atlas/prism/console); 节点仍常驻所以模板结构零改动, 只更新 dialogs-mgr.html 的 FX-21 注释口径。

## 实现计划

1. 三套皮肤 components.css `.modal-actions` +`margin-top: 16px`。
2. 三套皮肤(atlas/dialogs.css、prism/components.css、console/dialogs.css)重写 `.add-dialog-hint-warn` 两态规则 + 注释; dialogs-mgr.html FX-21 注释同步。
3. 验证: test.quick → 全量浏览器冒烟(ui_smoke.cjs 96 项) → 专项 Playwright 量测(三套 UI × 塌缩/展开/收回/下方位移/间隙) → test.full。

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | 三套皮肤 modal-actions margin-top 16px | Done |
| 2 | 跳检警告塌缩/展开动画(三套 CSS + tpl 注释) | Done |
| 3 | 全量冒烟 + 专项量测 + test.full | Done |
| 4 | 收尾回写(档案/切片/基线/坑条/索引) | Done |

## 进度日志

- 2026-09-28 06:2x 定位并实施(三套 CSS ×2 处 + tpl 注释); test.quick 1818 passed。
- 2026-09-28 06:4x dev.harness 默认端口 8099 被残留 python 进程占用(多 clone 环境, 疑似其它会话的 harness, 未动它)改 `--port 8098`; 全量冒烟 96 项 2 失败(「列设置·隐藏列宽度保留」双 UI)—— stash 本改动在干净 HEAD 复跑**同样失败**, 判定既有问题与本次无关。
- 2026-09-28 06:55 专项 Playwright 量测三套 UI 全绿: 警告行塌缩 0px / 展开 17.3-18.4px(透明度 1) / 收回 0px, 下方内容布局坐标下移 27.8-29.4px(=行高+7px margin+行距取整); 三处按钮排 margin-top 16px、视觉间隙 16.0px。量测曾两度假红: ①Playwright `waitForSelector` 默认等 visible 被塌缩元素(height 0)卡超时; ②视口 rect 位移只有增量一半 —— 居中弹窗增高时上下对半扩, 视口坐标被上扩抵消, 须用「相对 body 顶 + scrollTop」布局坐标。已沉淀 pitfalls/web-ui/dialog-measure.md。
- 2026-09-28 07:0x test.full 首轮 1 失败 = 已记录的 Windows throttle 假红(sleep 46ms < 0.05s 下限, 见 testing/baseline.md 常驻警告); deselect 重跑稳态 1817 passed / 3 skipped, TOTAL 91%, 20.77s; 基线切片 26-09-28-0702。
