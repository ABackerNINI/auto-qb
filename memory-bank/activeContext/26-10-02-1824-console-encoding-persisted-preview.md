# 大输出落盘预览乱码 — 机制定案并入坑档

> 摘要: 用户问「压到多少 KB 正常」→ 定案: ZCode Bash 工具内联上限 30,000 字节(outputLimit.maxInlineBytes 硬编码 3e4, 显示口径 29.3KB, 判定只认字节); 超限落盘 + 2KB 预览, 解码函数 kme 按「干净且完整 UTF-8 则 UTF-8, 否则整段 legacy(GBK)」选码 —— 截断点切进多字节字符(kb.active 的「的」e7 9a ae 横跨截断区)即整段乱且稳定复现, 纯 ASCII 不乱; 落盘日志逐字节完好(iconv 整文件校验), Read 即真值。已补 [pitfalls/ops/console-encoding.md](../pitfalls/ops/console-encoding.md) 2026-10-02 节; 前一轮「预览按 GBK 解」的表述据此精确化。
> 最后活动: 2026-10-02 18:24
