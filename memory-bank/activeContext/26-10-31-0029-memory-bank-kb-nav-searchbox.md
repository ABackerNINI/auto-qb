# memory-bank-kb-nav-searchbox

> 摘要: 搜索框清词按钮(有词显形/syncGclear 单点)+ placeholder 移除(Esc 清空)+ / 快捷键聚焦(输入态/IME 不劫); 新守阵两条, test.full 全绿(见 kb.baseline)
> 最后活动: 2026-10-31 00:35

**R0(2026-10-31 00:29):** 搜索框清词按钮(有词显形/syncGclear 单点)+ placeholder 移除(Esc 清空)+ / 快捷键聚焦(输入态/IME 不劫); 新守阵两条, test.full 全绿(见 kb.baseline)

**R1(2026-10-31 00:35):** 修实测居中漂移: .gsearch svg 后代选择器命中 #gclear 的 × 套了 absolute —— 收窄为 .gsearch > svg 只钉放大镜, × 回流内由 flex 居中(auto-qb .bt.icon 同机制); 守阵加 .gsearch > svg 判据; 真机几何实测 dx=0/dy=0, / 快捷键与清词点击实测过
