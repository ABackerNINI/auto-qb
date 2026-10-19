"""auto_qb.tools: 随代码库分发的独立入口(供主进程 detached 拉起, 不单独安装包)

当前成员:
- `finalize_watch`: 整组迁移的收尾 guardian(计划 26-10-18-1604 P6) —— 独立进程,
  等 qB 退出后删别名并写 journal, 不随 auto-qb 消亡。
"""
