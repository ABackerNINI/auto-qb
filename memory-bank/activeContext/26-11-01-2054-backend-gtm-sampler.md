# backend-gtm-sampler

> 摘要: 认领 issue 26-10-20-2345(perf) grilling 两轮定案方案 E: gtm 网卡采样默认 provider 改 Windows 原生 GetIfTable2 整表单读(17 ops/轮, psutil 149)+psutil 名单缓存映射保口径一致+启动交叉校验失败回退+运行期异常当轮回退; 新模块 gtm/nic.py + sampler 接线, 注入点契约零改动; test_nic 30 用例, test.gtm 459 过/test.full 4461 过(基线切片 26-11-01-2052); 验收实测全轮 56 ops/轮≈11.2 次/秒, 2 倍差异取证 record 原子写 39/轮; issue 置 Done; 坑档 psutil-nic-universe 入库; 工作区未提交(用户未授权)
> 最后活动: 2026-11-01 23:31
**Refs:**

**R0(2026-11-01 20:54):** 认领 issue 26-10-20-2345(perf) grilling 两轮定案方案 E: gtm 网卡采样默认 provider 改 Windows 原生 GetIfTable2 整表单读(17 ops/轮, psutil 149)+psutil 名单缓存映射保口径一致+启动交叉校验失败回退+运行期异常当轮回退; 新模块 gtm/nic.py + sampler 接线, 注入点契约零改动; test_nic 30 用例, test.gtm 459 过/test.full 4461 过(基线切片 26-11-01-2052); 验收实测全轮 56 ops/轮≈11.2 次/秒, 2 倍差异取证 record 原子写 39/轮; issue 置 Done; 坑档 psutil-nic-universe 入库; 工作区未提交(用户未授权)

**R1(2026-11-01 23:31):** 补测 Linux 侧: WSL Ubuntu-26.04 装全局 uv 0.13.6, UV_PROJECT_ENVIRONMENT=~/.venvs/gtm-linux (不动工作区 Windows venv); 首跑布局守卫当场拦下 c_ulong LP64 错位 (sizeof 1408 vs 1352), 全字段改显式定宽类型修复; Linux 459 过 / 覆盖 98.54% (98.0 闸过, nic.py 15 未覆盖行全为 win32 专属), Windows 复跑 459 过 / 99.03%; conftest 分档依据改实测数字, 坑档补 c_ulong LP64 条目; 全部前台执行未用后台
