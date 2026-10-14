# 3205 — 用户页速度数值下方多余暗色条: 行级微条 track 退役(07/08, 死字段一并)

**Refs:** memory-bank/tasks/26-10-14-webui-peers-speed-track-removal.md

> 摘要: 用户报「种子详情面板用户页四卡仪表/五区分组表中上传/下载速度数值下方有多余的暗色条, 移除」—— 根cause = 行级速度微条 track(.dt07-spd/.dt08-spd .track, 全宽 3px background --bg-sunken)里的填充 `<i>` 无任何 background(模板只置 inline width, 变体 CSS `.track i` 无 background)⇒ 填充恒透明, track 即全宽暗色条不论速度(对照卡 1 flowbar 里的 i 有 background, 行级微条是失填充形态). 修法按用户字「移除」= 整 track 退役: 四速度格删 track span + 两变体删 `.track` CSS 两规则 + 退役死字段 upBar/downBar 与 rowsFn maxUp/maxDown 满刻度求值(grep 无其它消费点) + 卡 1 tip 文案引用摘. 验证 = 真浏览器 DOM 探针两变体速度格零 track + 两截图 + e2e @fast 全绿 + 静态守阵 targeted 绿 + test.full 全绿.
> 基线时间: 2026-10-14 16:15
> 档案: memory-bank/tasks/26-10-14-webui-peers-speed-track-removal.md

## 验收数字

- test.full: 3205 passed + 4 skipped / TOTAL 16824 158 5724 140 99%(98.65%, 过 98% 闸门).
- 耗时: 135.42s(单次采样, 口径见 baseline.md).
- e2e @fast(日常门禁子集, 本机 8137 起桩串行): 136 passed / 251.9s —— 含用户页签速度格守阵(drawer-peers 非空态 + dt-live-update #5 速度实时 + 列对齐三变体)全绿; 端口 8137 残留进程走 `dev.port-kill` 再跑(playwright-teardown 已知本机形态).
- 静态守阵 targeted(test.one: test_webui_static_skins.py + test_webui_static_dom_panel.py): 58 passed / 2.23s —— 钉 cell renderer 与列集(本改动面删 track span 即 cell 内部, 钉不放宽失).
- 包内脚本测试(commands run test.pkg): 本轮未触 .commands/ 与 .agents/skills/commands/, 闸门 match 不命中, 未跑.
- Linux(WSL)侧未重测 —— 改动纯前端静态 HTML/JS 面, 无平台分支; 本条 Windows 侧数字为事实源.

## 本改动面

- 源(3 文件): tpl/xtpl-cells.html(dt07/dt08 upspeed/dlspeed 四格删 `<span class="track">`) · 07-peers-dashboard-tall.js(删 `.track` CSS 两规则 + rowOf 删 upBar/downBar + rowsFn 删 maxUp/maxDown 求值 + card1 tip 文案引用摘) · 08-peers-groups-low.js(同三件).
- 测试: 零改 —— e2e 断走 `.dt07-spd` textContent(track 删不影响), 守阵 not 钉 track/upBar/downBar(grep 定案), 同轮绿即判据不放宽失.
- 红验: 桩 harness 起, 真浏览器双击开抽屉→用户页签两变体 DOM 探针 `.dt07-spd .track`/`.dt08-spd .track` 零个 + 两截图(验收件); 失改形态(track 仍出)即探针必红 —— 探针现绿定改生效.
- 文档: 本切片 · 任务档案 tasks/26-10-14-webui-peers-speed-track-removal.md · activeContext 切片 26-10-14-1615 · kb.index 重建.

## 已知偏差 / 移交

- 速度数值文字保持方向色(与卡 1 去向分段同色联动口径不变); 微条信息(相对速度比重)随用户拍「移除」退役 —— 若日后要真微条, 改填充 background 两变体 CSS 同轮(失填充形态的修复面), 但用户拍移除档, 不自动补.
- e2e 全量矩阵(六行)未重跑 —— 改动纯静态前端删面, @fast 子集覆盖用户页签速度格三 spec; 全量矩阵属收尾/排障轮另跑, 本条记 @fast 口径.
