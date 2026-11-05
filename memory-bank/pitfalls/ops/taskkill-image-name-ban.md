# taskkill /IM 按映像名全杀误伤生产 qb(禁令)

> 摘要: taskkill 任何形态一律禁止 —— 本机生产 qB(26586)与测试实例同名映像 qbittorrent.exe, /IM 按映像名全杀 = 静默误杀生产(2026-11-05 E1.6 实际发生); bash 裸跑还有 MSYS 路径改写假失败层诱人换 python subprocess 绕过
> 触发: taskkill, 杀进程, IM, 映像名, 误杀生产, MSYS 路径改写, Stop-Process, real.down, qbittorrent.exe, 强杀
**Refs:** memory-bank/testing/real-machine.md

### 用 taskkill 杀 qB:三层叠加坑, 最后一层是误杀生产

- **触发**: 会话里想杀 qB 实例(实验/排障/清场), 用了 `taskkill`(bash 裸跑、`//F //IM` 转义、python `subprocess` 任意形态)。本机生产 qB 与测试实例**同名映像** `qbittorrent.exe`, `/IM` 按映像名枚举**全杀**。
- **判别**: 三层叠加 —— ①bash 裸跑 `/F` 被 MSYS 路径改写成 `F:/`, 报「无效参数」rc=1,**假失败诱人换 python subprocess 绕过**; ②python `subprocess.run(['taskkill',...], capture_output=True)` rc=0 真杀, stdout 是 GBK, 用 utf-8 解码会抛 `UnicodeDecodeError`(只是读输出线程崩, kill 已生效)——`capture_output` 吞掉回执后**杀手无凭据**; ③生产实例被静默杀: qB 日志**戛然而止**(无「发起了终止操作」记录)、无 WER 崩溃事件、下次例行动录(如每小时 WebAPI 登录)缺席。2026-11-05 实际事故: relocate 压测 E1.6 硬杀实验按映像名全杀, 生产 26586 连带死亡约 2h 才被发现。
- **处置**: **一律禁 taskkill(AGENTS.md 红线)** —— 杀/起 qB 实例只走 `real.down`/`real.up`(端口白名单+镜像路径前缀核验, 只碰报名 pid); 其它进程按端口查真 PID 走 `dev.port-kill`。已发生误杀: 直接重启实例即可(qB 数据无损, 强杀不碰磁盘), 死亡时刻用「qB 日志例行动录缺席 + auto-qb 断连记录」夹逼。排查同类事故先核对 transcript 印象 vs 实际命令序列(本次曾把前一轮优雅关闭的 pid 记录错安到硬杀头上, 得出「taskkill 是空操作」的错结论)。
- **守阵**: `real.guard` 静态白名单只守 `real.*` 调用链; taskkill 禁令靠本条 + AGENTS.md, 无机检(会话内自查: 杀进程前先 `Get-Process qbittorrent | Select Id,Path` 确认无生产实例)。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
