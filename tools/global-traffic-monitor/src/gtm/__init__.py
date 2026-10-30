"""global-traffic-monitor (gtm) —— 整机流量历史记录小工具 (TrafficMonitor 替代).

独立于 auto-qb 主进程、开机自启: 以 psutil 采样整机全适配器流量 (排除回环与 down
网卡), 以 TrafficMonitor 兼容格式 (history_traffic.dat, 每行 "YYYY/MM/DD 上传KB/下载KB")
原子落盘; 当日累计上下行合计变化超过阈值 (默认 100 MiB) 时, 向所有存活订阅的
auto-qb 实例推送通知 (带单调事件号), 后者按事件号用事件自带权威累计零读盘直达
改写快照「今日流量」并刷新 WebUI 历史流量图。

设计单点: memory-bank/plans/26-10-16-0541-plan-global-traffic-monitor.html
(实施计划 S0-S10; 当前进度: S0 包骨架 / S1 采样器 / S2 落盘 / S3 控制面 /
S4 通知 / S5 自启 / S6 配置面 / S7 接收面 / S8 集成与过渡 / S9 守阵测试 已落地,
S10 真机验收待逐项授权)。
"""

__version__ = "0.1.0"
