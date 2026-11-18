# 6464 —— S2 守阵补齐全量基线(boot-first 两跳)

> 摘要: 计划 26-11-18-0259 S2 守阵补齐(剩余单测面 + e2e 冷启动两跳形状)收尾基线
> 基线时间: 2026-11-18 07:24
> 档案: memory-bank/tasks/26-11-18-webui-boot-first-data.md

## 验收数字

`commands run test.full` 实测(2026-11-18 07:24 收尾, Windows, 3m17s):

```
TOTAL                                                28870     43  10306     60    99%
6458 passed, 6 skipped in 197.64s (0:03:17)
```

e2e 侧(本计划对象面, 均当轮实测): `commands run dev.e2e`(环境变量 E2E_BOOT_FIRST=on; spec: e2e/boot-first-two-hop.spec.mjs + e2e/delta-sync.spec.mjs) **9 passed**(26.5s; 新 spec 冷启动两跳 1 + delta-sync 双皮肤 8 —— R2「delta 客户端多吃一代」回归面); 默认模式抽查 `commands run dev.e2e`(spec: e2e/delta-sync.spec.mjs + e2e/views.spec.mjs) **46 passed**(2.1m, 桩默认路径行为逐字不变)。

## 本改动面

- `tests/test_webui_boot_first_publish.py`(+2 用例至 6): S1 已钉面不重复, 补 S2 缺面 —— `test_base_generation_lacks_site_derived_fields_completion_fills_them`(基础代 site 派生面全空/补全代 HR 派生字段落位/错误原因任务线一代补齐, ver 逐代 +1)与 `test_delta_client_two_generation_sequence_compatibility`(时间线恰两代 ver 连续/rid==ver 零回传/补全代迁移降级 full 协议回退/未协商形状逐键兼容/真实增量轮回增量); `_boot_env` 扩 hr_tag/errored 参数(默认零行为变化)。
- `scripts/ui_harness.py`: `--boot-first on` 冷启动两跳观测模式(store 不预灌, 启动首轮经真实 `_sync_line` 在主线程跑, 归组 files 单发在 `_BootGate` 闸口挂起, `/__harness__/boot_go|boot_gate` 两跳放行) + `_FileEntry`(dict 子类 + 属性访问: files 端点可序列化与真归组 `f.name` 两面交集, 默认模式 JSON 逐字节不变)。
- `e2e/harness.mjs` + `e2e/lib/mode.mjs`: 模式矩阵加 `E2E_BOOT_FIRST`(on|off, 默认 off)第五维。
- `e2e/boot-first-two-hop.spec.mjs`(新): 冷启动两跳断言(空代 -> 基础代 flat 满/groups 空/singles 超集 -> 补全代 groups 落位/singles 收缩/flat 恒满, rid 严格 +1; UI 落位面单皮肤 prism; 默认模式整组 skip)。
- 本切片 + 任务档案(子任务表 S2 翻 Done + 进度日志 R3 行)。
