# psutil 的 Windows 网卡全集来自 GetAdaptersAddresses, 不等于 if-table 全集

> 摘要: psutil 的 Windows 网卡全集来自 GetAdaptersAddresses, 不等于 if-table 全集
> 触发: psutil,net_io_counters,net_if_stats,GetIfTable2,GetAdaptersAddresses,网卡全集,过滤层,WFP,虚拟网卡,双计,接口口径,gtm 采样
**Refs:** memory-bank/issues/26-10-20-2345-perf-gtm-sampler-other-io.html

### 换掉 psutil 采样路径时, 直接用 GetIfTable2 整表做候选全集会改变流量口径 (虚拟/过滤层行混入, 物理流量双计)

- **触发**: 用原生 IP Helper API (GetIfTable2/GetIfEntry2) 替换 psutil 的 net_io_counters /
  net_if_stats 时, 拿 if-table 全部行当候选全集。psutil 在 Windows 上的全集来自
  **GetAdaptersAddresses** (IP 适配器, 本机 4 个), 不是 if-table (本机 28 行); 表里还混着
  **WFP/QoS 过滤层行** (别名带 "-WFP"/"-QoS" 后缀), 它们是同一物理网卡的镜像计数行。
  gtm 的 AdapterFilter 默认只排 loopback 与 down —— 整表全集下这些行会混入合计,
  物理流量被物理行 + 过滤层行**双计**。
- **判别**: 替换后同一时刻原生读数的键集比 psutil 多出大量虚拟/过滤层行; 物理网卡流量
  翻倍; gtm 当日累计突增。实取证 (2026-11-01): psutil 4 键 vs if-table 28 行,
  以太网存在 "以太网-WFP Native MAC Layer LightWeight Filter" 等 3 条镜像行。
- **处置**: 名单口径与 psutil 严格一致: 名单取 psutil.net_if_stats() 键集 (缓存),
  每轮一次 GetIfTable2 整表读后**按别名精确匹配**名单 (过滤层行别名必带后缀, 命中
  不唯一即判拓扑漂移); 表行 InterfaceLuid 集合变化即刷新名单 (新网卡下一轮感知);
  启动时与 psutil 读数交叉校验 (键集/isup/计数单调有界), 不过即回退 psutil。
  单点实现: `tools/global-traffic-monitor/src/gtm/nic.py`。另注意: MIB_IF_ROW2 的
  InterfaceAndOperStatusFlags 是 8 个 BOOLEAN:1 位域 = **1 字节** (MSDN 文档页展开成
  8 个成员, 按 8 字节声明则 OperStatus 等后续字段错位); 双平台同布局的 ctypes 结构体
  字段必须用**显式定宽类型** (c_uint32/c_uint64) —— c_ulong 在 LP64 Linux 是 8 字节而
  Windows 是 4 (2026-11-01 WSL 实测 sizeof 1408 vs 1352, import 期布局断言当场拦住);
  c_wchar 在 Linux 是 4 字节, 字符串字段要用等宽字节数组手工 utf-16 解码。
- **守阵**: `tools/global-traffic-monitor/tests/test_nic.py` 布局断言 (sizeof/偏移,
  import 期 fail-fast + 用例双平台守) 与「名单口径映射」用例 (多余表行不收编);
  启动交叉校验不过自动回退 psutil, 最坏回到现状。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
