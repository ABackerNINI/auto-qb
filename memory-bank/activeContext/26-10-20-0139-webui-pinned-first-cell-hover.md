# webui-pinned-first-cell-hover

> 摘要: 必显列悬停闪竖带修复: 行板 160ms 过渡而吸左首格无过渡 ⇒ 滑过首帧错拍; 三皮肤补同源 `background-color` 过渡, 静态 + e2e 逐帧双守阵(详情见 R0 与基线切片)
> 最后活动: 2026-10-20 02:52

**R0(2026-10-20 01:39):** 修三主表必显列悬停闪竖带: 行板 .group-row 有 transition: background var(--dur)(160ms) 而吸左首格无过渡 ⇒ 滑过首帧首格 snap、其余列渐入, 160ms 内一条硬边竖带(用户报「短暂后恢复一致」); 三皮肤 views.css 补 transition: background-color var(--dur) var(--ease), 静态守阵 test_frontend_pinned_first_cell_hover_transition_parity + e2e main-table-pinned-hover.spec.mjs 逐帧采(滑入/移出各 ≤2, 修复前实测 14/18), 红绿双验已过

**R1(2026-10-20 02:01):** 按用户追问「其它位置的表格有没有此问题」做全仓审计: 首格镜像规则只有三皮肤 .group-row > :first-child 一条, 经典抽屉表与 04-11 变体面全部继承它; 真浏览器逐帧复测 06/07/09/10/11 + 经典抽屉面滑入/移出差全 0(10 有 0.5 取整), 04/05 是单内容根无兄弟列; 非 .group-row 的真表(HR 明细/波次/拉取历史、统计面板、hub 行)悬停是整行所有格同时换色且全链无 transition, 结构性不可能错拍。拾取一条非本例的静态残差: 08 bad 行静息态首格 vs 相邻列差 5.3(prism)/3.4(atlas), 远低于可辨阈, 未修、已记档。静态守阵补第 ④ 款(首格过渡只在皮肤单点, dt_table.css 与变体注入不得自带 transition)+ 红验

**R2(2026-10-20 02:52):** 按用户『非本例差异一并修』修 08 用户分组 bad 行首格: 逐层量出承光链 —— 行级 error-soft 叠在 section.dt08-grp(计算底 = --bg-row #f7fafd)上, 而首格合成取的抽屉卡底 --bg-card(#fdfeff), 两令牌差经 12% tint 后 5/4/2; dt_table.css 该条基色改 var(--bg-row) 即与行板逐通道一致; e2e dt-table-face-bg 补 STATE_CASES['08'] —— 一直漏测的位; 静态守阵 08 条改口径(必含 --bg-row / 禁 --bg-card), 两侧红绿双验; 全量 pytest 与全量 e2e 均绿
