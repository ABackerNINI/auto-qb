# deps-upgrade-pin-bump

> 摘要: deps-upgrade 例行巡检+首条入池件认领: R0 巡检 17 更新/9 包零码 bump 全绿/4 条 major 降档入池(26-10-31-0830 前缀); R1 pyobjc 三件 12.2.2→13.0 认领实施 Done(基线 26-10-31-0928), 顺带发现 test_relocate_exec 一例同树异时 flaky 待拍板, 余三件入池项仍 Open
> 最后活动: 2026-10-31 09:29

**R0(2026-10-31 08:37):** deps-upgrade 例行巡检: 检测 17 个 pin 型更新, 9 包零码 bump(pytest 9.2.0 + 8 传递依赖)逐包 test.full 全绿, 4 条 major/0.x 降档入池(26-10-31-0830 前缀), 基线切片 26-10-31-0837

**R1(2026-10-31 09:29):** 认领 26-10-31-0830 pyobjc issue 并实施: uv.lock 三件(pyobjc-core/-cocoa/-quartz)12.2.2→13.0 原子同升, env.sync Windows 零安装, test.full 全绿(基线切片 26-10-31-0928-pyobjc-13-bump), issue 置 Done; 另发现 test_relocate_exec::test_reconcile_rebuild_when_link_lost_but_qb_alive 同树异时翻转(全量绿后单跑稳定红, venv 未变非本次引入), 未修待拍板
