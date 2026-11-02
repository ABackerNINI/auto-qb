# memory-bank-kb-nav-searchbox

> 摘要: 搜索框清词(Esc)/快捷键聚焦 + 全局搜索支持文件名与相对路径 (navSearchText 单点, 台账/控制台频道/卡片墙共用); 守阵三条, 数字见 kb.baseline
> 最后活动: 2026-11-03 01:10
**Refs:** memory-bank/tasks/26-11-03-memory-bank-kb-nav-searchbox.md

**R0(2026-10-31 00:29):** 搜索框清词按钮(有词显形/syncGclear 单点)+ placeholder 移除(Esc 清空)+ / 快捷键聚焦(输入态/IME 不劫); 新守阵两条, test.full 全绿(见 kb.baseline)

**R1(2026-10-31 00:35):** 修实测居中漂移: .gsearch svg 后代选择器命中 #gclear 的 × 套了 absolute —— 收窄为 .gsearch > svg 只钉放大镜, × 回流内由 flex 居中(auto-qb .bt.icon 同机制); 守阵加 .gsearch > svg 判据; 真机几何实测 dx=0/dy=0, / 快捷键与清词点击实测过

**R2(2026-11-03 00:46):** 修 #gq 搜索按文件名/相对路径无命中: 新增 navSearchText 单点补 link 与 repository-root 相对形态, 台账/控制台频道/卡片墙三处统一消费, 正文不入索引且大小写/反斜杠归一; 原字段匹配与排序展示不变, 守阵 +1, 数字见 kb.baseline

**R3(2026-11-03 01:10):** 合流后 test.quick 红: 远端新真机守阵的受控桩依赖系统卷/祖先属性; 桩化 SystemDrive 与非 hid 属性后定向 57 passed, 最终 test.full 全绿, 处置见新基线切片首跑红节
