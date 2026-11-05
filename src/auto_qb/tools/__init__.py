"""auto_qb.tools: 随代码库分发的独立入口(供主进程 detached 拉起, 不单独安装包)

当前成员:
- `recycle_daemon`: fastresume 收尾回收 daemon(计划 26-11-05-0808, D11-D13) —— 独立
  进程, 等 qB 下线窗口(三证)批量改写成员 fastresume 双键并写 journal, 不随 auto-qb
  消亡。旧收尾 guardian `finalize_watch` 已整文件退役(S4), 三证判据随迁进 daemon 模块。
"""
