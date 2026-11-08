# 5722 —— 5722 passed + 2 skipped(根) — fix/legacy-review4-core 收尾验证基线: R4-core 44 行明细十四批全量绿

> 摘要: 5722 passed + 2 skipped(根) — fix/legacy-review4-core 收尾验证基线: R4-core 44 行明细十四批全量绿
> 基线时间: 2026-11-08 16:25

## 验收数字

`commands run test.full` 实测 (141.9s, 2026-11-08 16:22):

```text
TOTAL                                                25821     22   8934     41    99%
5722 passed, 2 skipped in 139.77s (0:02:19)
```

一次通过零失败零重跑; 覆盖率 99%(25821 stmts / 22 miss / 8934 branch / 41 partial)。2 skipped 为
既有设计性跳过(与本轮无关, 未新增跳过)。上片(26-11-08-0025, 5663 passed)差值 +59, 主要来自十四批
新增测试(tvshows 6 / state+CLI 10 / exporter+CLI 5 / grouping 8 / ops 8 / maintenance 3 /
relocate plan+probe 22 / lifecycle 3 / cancel 3 / traffic 9 / gate 常量守阵 1 等)与
test_memory_bank_structure 2 条既有失败随 kb.index 重建转绿。

## 本改动面

本轮 = issue 26-11-07-0527(存量评审 R4·core 汇总, 44 行)的修复任务全程, 本地分支
fix/legacy-review4-core(1f0343bb..a31ce7c, 15 commits, 基线钉分支顶 a31ce7c), 十四批 + 收口:

- B1 tvshows: 正则原子组消灾难回溯 + 兜底 S1 season_inferred + 跨目录多季守卫(1f0343bb)
- B2 state/cli/episodes: 恢复写回延迟持锁物化 + fuse --all 测试 + docstring 改口(1574e20a)
- B3 exporter/cli/qbmanager: export 双取合并 + 生产配置重写双守卫 + 导出 tracker/magnet 脱敏(ce0323e5)
- B4 grouping: 删除簿记出闸门 + 解散清 skips + skips 入 state_file 持久化 + UNDETERMINED 补测(dbeb5feb)
- B5 ops: 崩溃恢复重加口径单点对齐(10 字段回传) + 死导入 + 退避首拍 + GONE 保备份(6eda8094)
- B6 maintenance: 死变量 handled 删除 + auto_categories 种子消失路径清理(704f6e89)
- B7 relocate plan/units: 同机弱证据不判死(D 级决定性) + 死导入 + 闸门常量统一 + fallback 死字段 + threshold 交叉校验(59c75dc4)
- B8 relocate lifecycle: stop 条件持久化(禁空账清盘) + 热启用补 _load_jobs(a3d67d0e)
- B9 relocate exec cancel: 撤销残留别名验删守卫 + MOVING/WATCHING 相位拒撤(52d03e18)
- B10 relocate probe: 认领/补删/启动扫描三路守卫同口径 + 指纹 HMAC-SHA256 加盐(4b6e2c05)
- B12 traffic 聚合: 已关日/月 hour 重封存根合流重建 + 快照三源钳制(ee1a8ed7)
- B13 traffic 杂项: 撕裂尾写侧查补 + z 行契约单点恢复 + 指针 host/凭据归属双闸(876c3de3)
- B14 文档批: config-reference 退役键 + main-loop/taskqueue 漂移对齐(ab564826)
- 收口: gate 常量化+注释键(d828d443) + issue 回写/三项入池/索引重建(a31ce7c)

明细 43 条中 40 条修复(行 3 R1#22 建链幂等、行 8 R1#39 probe 阻塞拍板不修, 行 3 已拆出独立 issue
26-11-08-1608), 每批均过批评审(分面/全能/派发≥2)+收口接缝终审; R1#39 跳过为用户拍板(B11 未实施)。
