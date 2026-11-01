# 26-11-01-backend-gtm-sampler — gtm 网卡采样改原生 GetIfTable2 整表读取 (issue 26-10-20-2345)

**Status:** Done
**Added:** 2026-11-01
**Updated:** 2026-11-01
**Summary:** gtm 采样默认 provider 改原生 GetIfTable2 整表单读 (17 ops/轮, psutil 149), 口经 psutil 名单缓存严格一致, 校验失败自动回退; issue 26-10-20-2345 Done, test.gtm/test.full 双绿
**Topics:** backend-gtm-sampler
**Refs:** memory-bank/issues/26-10-20-2345-perf-gtm-sampler-other-io.html

## 原始请求

1. 「认领26-10-20-2345-perf-gtm-sampler-other-io.html, 分析方案优劣, grilling」
2. 「3个方案都不是很满意, Q1 其实是a为主, b为辅, 不能指望用户去认真读用户手册. 分析还有没有其它更好的方案」
3. 「按推荐」(Round 2 Q6-Q10 全采: E 方案定案)

## 思考过程与决策

- grilling 两轮拍板。入池 A/B/C 三案均否: A 改产品语义参数且不解决误读; B 只省一半且
  down->up 有漏计语义; C 的收益估计建立在未归因的 2 倍差异上, 且 Sampler 全重做被高估。
- 用户重定性: (a) 任务管理器「I/O 其它」累计值误导排查为主, (b) 省无谓内核调用为辅。
- 重新实测打开方案空间: 裸 GetIfTable2 整表 17 ops/次 (psutil 同口径 88.4), GetIfEntry2
  单行 2 ops。方案 E 定案: Windows 原生整表 + psutil 回退 + 启动交叉校验。
- **关键发现与取舍**: psutil 的接口全集来自 GetAdaptersAddresses (4 个), ≠ if-table 全集
  (28 行, 含 WFP/QoS 过滤层同名镜像行) —— 整表全集直接用会改变 AdapterFilter 候选口径
  (双计物理流量)。取舍: 名单取 psutil.net_if_stats() 键集缓存, 每轮整表读后按别名映射,
  LUID 集变化即刷新 —— 口径与 psutil 严格一致, 每轮仍只一次整表读。
- 覆盖率闸: 双 OS 同门槛下 win32 专属行 Linux 跑不到, 按根仓先例改平台分档
  (conftest 单点, Windows 98.5 / 其余 98.0)。

## 实现计划

总体思路: Sampler 注入点契约零改动, 只换生产默认 provider 的解析路径 (懒决议,
构造不触系统 API); 校验不过/运行失败一律回退 psutil, 最坏回到现状。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 认领 + 复验 (锚点未漂移, 机制仍复现 149/轮) + 状态 In Progress | Done(2026-11-01) |
| S2 | grilling 两轮定案方案 E, 用户按推荐确认 | Done(2026-11-01) |
| S3 | gtm/nic.py 实现 (布局/映射/校验/回退/懒决议) + sampler.py 接线 | Done(2026-11-01) |
| S4 | test_nic.py 30 用例 + test.gtm 全绿 (459 passed, 覆盖 99%) | Done(2026-11-01) |
| S5 | 验收实测: 17.0 ops/轮 (vs 149.0); 2 倍差异取证 (record 39/轮) | Done(2026-11-01) |
| S6 | test.full 全绿 4461 passed + 基线切片 26-11-01-2052 | Done(2026-11-01) |
| S7 | issue 置 Done + 坑档 + 回写 | Done(2026-11-01) |

## 进度日志

### R0 · 立档 (2026-11-01)

认领 + grilling 两轮定案 + 实现与验收一次完成: nic.py 新模块 + sampler 接线 + 30 用例,
test.gtm/test.full 双绿 (数字见基线切片 26-11-01-2052); 验收实测 17.0 ops/轮 (psutil 149.0,
8.8 倍), record 原子写另贡献 39 ops/轮 (设计内路径, 归因入坑档与 issue 修后补充);
issue 已置 Done。工作区未提交 (用户未授权提交)。

- 2026-11-01 20:54 认领 issue 26-10-20-2345(perf) grilling 两轮定案方案 E: gtm 网卡采样默认 provider 改 Windows 原生 GetIfTable2 整表单读(17 ops/轮, psutil 149)+psutil 名单缓存映射保口径一致+启动交叉校验失败回退+运行期异常当轮回退; 新模块 gtm/nic.py + sampler 接线, 注入点契约零改动; test_nic 30 用例, test.gtm 459 过/test.full 4461 过(基线切片 26-11-01-2052); 验收实测全轮 56 ops/轮≈11.2 次/秒, 2 倍差异取证 record 原子写 39/轮; issue 置 Done; 坑档 psutil-nic-universe 入库; 工作区未提交(用户未授权)

- 2026-11-01 23:31 补测 Linux 侧: WSL Ubuntu-26.04 装全局 uv 0.13.6, UV_PROJECT_ENVIRONMENT=~/.venvs/gtm-linux (不动工作区 Windows venv); 首跑布局守卫当场拦下 c_ulong LP64 错位 (sizeof 1408 vs 1352), 全字段改显式定宽类型修复; Linux 459 passed / 覆盖 98.54% (98.0 闸过, nic.py 15 未覆盖行全为 win32 专属), Windows 复跑 459 passed / 99.03%; conftest 分档依据改实测数字, 坑档补 c_ulong LP64 条目; 全部前台执行未用后台
