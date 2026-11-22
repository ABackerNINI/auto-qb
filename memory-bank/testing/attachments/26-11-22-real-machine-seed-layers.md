# 种子层: L0/L1/L2
> 摘要: 真机实测的三级假种子构造法 —— 从只读数据面到真上传下载, 附 announce 局域网 IP 与伪 tracker 排除请求者两条铁律。
> 触发: 种子层, L0, L1, L2, 假种子, 伪 tracker, announce, 局域网 IP, WSAEADDRNOTAVAIL, 做种, 数据面

## 03 种子层: L0/L1/L2

| 层 | 怎么造 | 种子状态 | 能测什么 |
|---|---|---|---|
| L0 | `real.seed` 假种子, 无 announce | paused/stalledUP | 只读数据面 |
| L1 | 构造种子+伪 tracker announce(零 peer) | 零外网流量 | 标签/限速/规则/HR 数据面 |
| L2 | 主做种+副下载, 伪 tracker 回对端 | 真上传下载 | 速率/进度/完成事件 |

L1/L2 已验证解锁(环境1 RM00; 环境2 2026-11-01 实证), 各片直接引用; 大库量级归**语料回放轨**。写 L1/L2 两条铁律: ① announce 用局域网 IP(`lib/net.py: local_host()`), 写 `127.0.0.1` → `WSAEADDRNOTAVAIL`(qB 出站 socket 绑物理网卡); ② 伪 tracker 回包必须排除请求者自己(同 IP 单连接限制会挤掉真 leech; `lib/tracker.py` 已按 port 排除)。

