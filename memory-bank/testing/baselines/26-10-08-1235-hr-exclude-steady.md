# 2813 —— HR 排除/稳态降频失效取证 (报告 26-10-08-1235)

> 摘要: 「HR 排除未落到取数侧 ⇒ 稳态降频失效」取证轮收尾基线。本轮**零代码改动** (纯文档/制品轮: 报告 + 档案 + 切片 + 坑档 + 索引重建), 全量套件与守卫全绿。
> 档案: memory-bank/tasks/26-10-08-backend-hr-exclude-steady.md
> 基线时间: 2026-10-08 12:35

**Refs:** memory-bank/tasks/26-10-08-backend-hr-exclude-steady.md

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2813 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**(16476 语句 / 162 未覆盖 / 5694 分支 / 146 partial; 门槛 98% 达标)
- **耗时**: 47.18s(墙时 49.6s)
- **新增守卫覆盖**: 本轮新增的制品均过闸 —— `test_docs_forms.py`(meta 齐 / dark 主题 / 命名合规 / 索引 == 生成结果 / 认领链双向)与 `test_memory_bank.py`(索引↔文件一致 / 命名 / 状态分区 / 裸数字守卫)全绿, 无新增失败。

## 说明

- **相对上基线的参考**: 与 [26-10-08-1016](26-10-08-1016-mutants-config-validator-strings.md) 的差异不逐位抄(口径见 [../baseline.md](../baseline.md)「切片正文只写自己的 TOTAL」); 要看差值跑 `commands run kb.baseline -n 2`。上基线记录的 2 条存量守卫失败在本基线已不见(会话开工先同步到 `fcc3cd69`, 疑由其它 clone 的提交修复)。
- **代码事实变更**: 无 (本轮未改 `src/` 一行)。
