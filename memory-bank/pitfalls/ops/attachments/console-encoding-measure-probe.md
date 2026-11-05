## 测量探针变体: 表头被本地化 + 解析器按英文字面匹配 ⇒ 读数静默为 0(2026-10-15 补)

- **触发**: 探针脚本解析 Windows 原生命令输出做**测量**(实测: `netstat -e` 的字节计数行、`netstat -ano` 的连接表),
  Python 侧 `subprocess.run(..., capture_output=True, text=True)`。
- **判别**: 两个方向都中, 且都可**不报错**:
  ① 按 UTF-8 收 GBK 字节 → `UnicodeDecodeError` 抛在 `subprocess._readerthread` 后台线程(本族旧例,
    实测连带表现为 `AttributeError: 'NoneType' object has no attribute 'splitlines'`, 因为 stdout 是 None);
  ② **更阴的一层**: 解码侥幸通过, 但解析器写的是 `p[0] == 'Bytes'` / `'Interface'` 这类**英文字面**,
    中文 Windows 的表头是「字节」「接口统计」⇒ 匹配失败 → 计数器初值保持 0 → **两次采样相减得 0 B/s,
    看上去就是「这个接口没有流量」**。2026-10-15 的 qB 流量取证中, 这条一度支撑出「alltime 在涨而网卡零流量
    ⇒ 纯记账幻觉」的错误中间结论; 改成按「行内两个 6 位以上整数」取值后, 真相是该机 rx 227 KB/s / tx 271 KB/s
    真实存在(= 结论被反转)。
- **处置**: ① 收外部命令输出**显式指定码页**(`encoding="gbk", errors="replace"`), 不靠 locale 也不假定 UTF-8;
  ② 解析**不按表头文字定位** —— 按结构(字段数 / 纯数字列), 或直接换结构化来源(`Get-NetAdapterStatistics`、
  `Get-NetTCPConnection` 返回对象, 与码页无关; 若走 PowerShell 工具而非从 Bash 里 spawn);
  ③ **测量脚本必须做零值/量级自检**: 某计数器连续两次为 0, 或与预期量级差 3 个数量级 ⇒ 先当**解析失败**查,
  不得当结论用; ④ 结论若是否定命题(「没有 X 流量」), 至少两条独立路径交叉(netstat + 进程连接表 + 应用日志)。
- **守阵**: 属探针/环境侧, 常规守阵无可挂; 复验方式 = 同一命令同时跑「结构化来源」与「解析文本」两路, 数字应吻合。



- **崩在打印层**: [../git/message.md](../../git/message.md)「流水线脚本在 GBK 控制台打印 emoji 直接崩」—— 那类是 `UnicodeEncodeError` **抛出来**, 反而容易被发现; 本条是**静默**的那种。
- **写盘方向**: [../git/editing-traps.md](../../git/editing-traps.md)「合并冲突处理不要把 UTF-8 当 GBK 写入」—— 那类会**不可逆**地写坏文件, 检测要按 `U+FFFD` 计数, 别用 Git Bash 管道下结论。
