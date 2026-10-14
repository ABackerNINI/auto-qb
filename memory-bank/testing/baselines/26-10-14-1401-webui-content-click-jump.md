# 3205 —— 内容页树表点击跳动: CSS 入场动画重播(atlas/console 抽屉作用域 animation:none)

**Refs:** memory-bank/tasks/26-10-14-webui-content-click-jump.md

> 摘要: 用户四复查「点击跳动, 持续 0.x 秒后回到原位」—— 前三轮修法(W5 反应式化 / 10-11 补 withScroll)均未命中真机形态: 逐帧采样探针实锤跳动是**瞬态自回位**(参考行 rect +4px, ~0.22s 缓回, scrollTop 不变), 根因 = 抽屉表格体(.group-table/.group-head)是长生命周期元素(桥 Teleport + 锚保活), anchFill 每次整帧换帧把锚**摘下再插回** ⇒ 元素移除再插入 = CSS 动画重启 ⇒ atlas/console 的 page-in 入场动画(translateY(4px) + 淡入, .22s)每次点击重渲(数据回路 POST→补拉→换帧 / 行选中 rerender)都整表跳 4px 再缓回(prism 无该动画规则故探针一直干净). 修法 = 两皮肤 views.css 加 `.drawer .group-head, .drawer .group-table, .drawer .h-cell .arrow { animation: none; }`(主列表表格随视图真重建才播, 不受影响). 验证 = pytest 全量 + e2e @fast 全量(含新增守阵 #9 逐帧采样量具, 双皮肤).
> 基线时间: 2026-10-14 14:01
> 档案: memory-bank/tasks/26-10-14-webui-content-click-jump.md

## 验收数字

- test.full: 3205 passed + 4 skipped / TOTAL 16824 158 5724 140 99%(98.65%, 过 98% 闸门).
- 耗时: 130.45s(单次采样, 口径见 baseline.md).
- e2e @fast 全量(本机 8137 起桩串行): 136 passed —— 较上切片 +2, 即新增守阵 dt-live-update #9「数据回路点击不跳动: 逐帧采样下行/scrollTop 全程零偏移」(prism/atlas 双皮肤各 1 例); 其余 134 例与上切片同口径复跑全绿.
- 包内脚本测试(commands run test.pkg): 本轮未触 .commands/ 与 .agents/skills/commands/, 闸门 match 不命中, 未跑.
- Linux(WSL)侧未重测 —— 改动为纯前端(两皮肤静态 CSS 一条规则 + e2e 新增守阵), 无平台分支; 本条 Windows 侧数字为事实源.
- console 皮肤: 不在 e2e SKINS 冒烟矩阵(既定口径, harness.mjs:76 注释), 本轮由临时探针 zz-verify 直接验过(三皮肤 prism/atlas/console × dt10/11 × 数据回路+选中点击全部 dev=0), 探针已删; 守阵 #9 只覆盖 prism/atlas(矩阵口径).

## 本改动面

- 源(2 文件): static/atlas/css/views.css(第 451 行原 `.group-head, .group-table { animation: page-in }` 之上加抽屉作用域覆盖, 含机制长注释) · static/console/css/views.css(同款规则在第 351 行, 同口径覆盖).
- 测试(1 文件): e2e/dt-live-update.spec.mjs —— 文件头 docstring 补 #9 条目与「瞬态缺陷须逐帧采样」教训; 新增 makeFilesTall(40 文件 6 目录高树, 保证可滚动) fixture; 新增 #9 测试(rAF + 4ms 双路采样器钉两行 rect + scrollTop; POST 走真实端点保 waitCmd 链, GET 在 POST 后翻转 file0 优先级模拟真后端数据变化).
- 红验: 修后全绿(zz-verify 三皮肤); 把旧规则注回 `.drawer .group-table { animation: page-in }` 后探针立刻抓到 rt=4, rm=4 —— 量具有牙, CSS 修复正是生效关键.
- 文档: 本切片 · 任务档案 tasks/26-10-14-webui-content-click-jump.md · activeContext 切片 26-10-14-1202-webui-content-click-jump.md · 坑档 pitfalls/web-ui/frame-swap-scroll-reset.md(新增「动画重播同族」条目, 三复查条目记症状复发) · kb.index 生成物重建.

## 已知偏差 / 移交

- e2e SKINS 矩阵只有 prism/atlas(既定口径未动); console 的 CSS 修复与 atlas 同款同机制, 由本轮临时探针直验, 但**常驻守阵不覆盖 console** —— 若日后 console 进矩阵, #9 自动带上.
- 瞬态缺陷的量具教训已写进 #9 docstring 与坑档: before/after 比对式量具必然错过自回位型跳动; 前三轮量具全绿仍被用户报跳动的盲区 = 只测勾选(纯前端态), 没测数据回路(POST→waitCmd→补拉→换帧).
- 85px 形态(三复查报告 §02)仍未在桩里复现: 桩内 scrollTop 全程无偏移, 85px 属真机形态分账(布局/设备像素比等环境量), 但用户「0.x 秒后回位」的瞬态特征已被 #9 根因完整解释.
