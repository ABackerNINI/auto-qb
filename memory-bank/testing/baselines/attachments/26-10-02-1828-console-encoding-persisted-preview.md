# 基线 · 2291 passed + 3 skipped / 99% —— 控制台编码坑档补写轮

> 摘要: pitfalls/ops/console-encoding.md 补「大输出落盘预览按截断完整性选码」变体节(ZCode Bash 内联上限 30,000 字节 + kme 截断完整性判定 + 探针/字节级证据), 头部摘要/触发词同步; sync-pull.md 固有窗口复发 +1。切片 activeContext/26-10-02-1824。
> 基线时间: 2026-10-02 18:28, develop @ d354745b(收尾回写未提交工作树, test.full 实测)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。

TOTAL **2291 passed + 3 skipped / 99%**(13,357 语句 / 86 未覆盖 / 4,442 分支 / 81 partial,
test.full 34.4s, rc=0)。
相对上一切片(26-10-02-1744: 2291 passed + 3 skipped / 99%, @ 0d286cc5)全持平 —— 本轮与远端
两次推进(cfbfa712 / d354745b roadmap 批次)均纯文档, 零 Python 改动。提交流程首跑撞 sync 固有
窗口一次, 按 cp -a .git 备份 → stash -u → sync → pop 预案化解, 无冲突。
