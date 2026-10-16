"""落盘: TM 兼容 history_traffic.dat + state.json 原子写 + 单实例锁 (S0 骨架, 实现在 S2).

单写线程 (与采样同一线程, 黄金法则 5) 内写 TM 兼容文件: 首行总行数 N, 每行
"YYYY/MM/DD 上传KB/下载KB" (整数 KB, 与 auto-qb curves.py 解析一致)。
写 = 临时文件 -> os.replace 原子替换, 任意时刻读者见到完整一致的文件。

落盘节流: 日累计变化 >= 1 MiB 或距上次落盘 >= 30s (对齐 TM 落盘节拍)。
state.json (上次快照/当日累计/事件号/租约表) 同法原子写。
filelock 保证工具单实例, 二次启动 fail-fast 报错。
"""

# S0 骨架: 未实现。S2 落地原子写与单实例锁。
