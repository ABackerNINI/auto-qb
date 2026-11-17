# 26-11-18-webui-boot-first-data — 重启后 WebUI 首份数据 5-15s: 立项分析(根因链取证 + grilling 拍板 + 提前发布计划)

**Status:** Open
**Added:** 2026-11-18
**Updated:** 2026-11-18
**Summary:** 重启后 WebUI 首份数据 5-15s: 立项分析(根因链取证 + grilling 拍板 D1-D11 + 提前发布计划入库, 零代码改动; S0-S3 待显式开工)
**Topics:** webui-boot-first-data
**Refs:** memory-bank/plans/26-11-18-0259-plan-webui-boot-first-data.html, memory-bank/issues/26-11-18-0259-perf-first-round-grouping-files-serial.html, memory-bank/issues/26-11-18-0259-perf-first-round-pathmap-selfcheck-critical-path.html

## 本篇只回答

「重启后 WebUI 首份数据 5-15s(约 210 种子)」的根因是什么、修法怎么拍板、计划推进到哪 —— 根因结论与拍板细节归档在此; 方案正文单点在计划 26-11-18-0259。

## 原始请求

1. 「auto-qb重启后WEBUI刷新后主界面要5-15秒才出现, 种子约210. 之前修过一次.分析原因」(问答/只读轮)
2. 「立项分析, grilling and then create a plan」(执行授权: 立项 + grilling + 计划/档案产出)

## 思考过程与决策

- 根因(取证 2026-11-18, 详见计划 §02): 排除面桩实测(真 create_app + 210 合成种子): /api/state 冷 52ms / 资产串行链 ≈0.4s / CLI 导入 368ms / 渲染面百毫秒级 —— 都不是瓶颈。真正的链: store 不持久化种子记录 → 重启后首个同步必为全量轮(210 全走 added) → `_refresh_torrents`(qbmanager.py:939)整条管线(apply_sync :956 + path_map_selfcheck :966 + full_round :970 + 归组每种子 files 单发 grouping_mod.py:401 ≈210 次往返 + post 冲突检查)跑完才有首次发布(qbmanager.py:851), 窗口期 group_view_dirty 初始 True(runtime.py:112), 首请求抢先发布空代并把 dirty 压住, 含落库数据的代要等管线跑完 flush_views → 5-15s ≈ 管线时长。
- 与上次修复的关系: 26-11-02-0902(首访行高量齐)是前端渲染段, 不覆盖本次根因; 渲染面健康(210 行走估算开窗)。
- 两轮 grilling 11 问拍板 D1-D11(全记录见计划 §06), 用户改判两处: D5 = ②归组 files 串行 / ③path_map 自检关键路径不入主修、入池两条 issue 独立排期; D10 = S0 取证只用 real-machine 轨道环境, 不取生产数字。
- 关键物理事实: qB WebAPI `/torrents/files` 单 hash 专用(qbittorrentapi 源码取证), files 拉取无法批量合并 → groups 页第二跳时刻由②的 issue 承接, 本计划 North Star 按 D9 分视图口径。

## 实现计划

计划单点: `memory-bank/plans/26-11-18-0259-plan-webui-boot-first-data.html`(Open)。
- S0 真机取证: real-machine 轨道环境1/2 + ≈210 假种子受控重启, 量各视图首份数据出现时刻 + 首轮管线日志时间窗, 坐实根因并喂两条 issue 基线数字。
- S1 提前发布: `_refresh_torrents` 在 apply_sync 后插入启动首轮发布点(store 空 + 首个全量同步判据, 不依赖种子数), 复用既有发布单点, 不新增锁/线程/配置键。
- S2 守阵: 单测(两代发布语义/rid 序列/delta 兼容/首代形状) + e2e(桩冷启动两跳) + test.full 全绿。
- S3 真机验收: 同 S0 口径修复前/后对比, flat/singles/shows ≤2s 硬判据, groups 第二跳记录并回写②。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 立项 | 根因分析 + grilling D1-D11 + 计划入库 + ②③入池 | Done(2026-11-18) |
| S0 | real-machine 环境重启取证(各视图首份数据时刻 + 管线时间窗) | Open |
| S1 | 启动首轮提前发布(apply_sync 后插发布点) | Open |
| S2 | 守阵(单测/e2e/test.full) | Open |
| S3 | 真机验收(修复前后对比, 数字回写 issue②) | Open |

## 进度日志

### R0 · 立档 (2026-11-18)

- 问答轮完成根因分析(排除面桩实测 + 根因链代码取证, 本地桩 210 种子端口 8391 实测后经 dev.port-kill 核身份清理)。
- 分批评审: 三轮(首轮分面×2 + 修复轮×2)累计 11 发现(1 blocker=机制反写: dirty 初始 True 而非 False, 已按真实机制改写 / 1 major=S1 判据竞态失效, 已改「落库后最后一代不含落库数据」判据 / 9 minor=锚点与口径面)全修零 actionable, 引文检 11/11; 评审期间远端锚点前移两次(a5d3175e/9c8824dc 各带 Review:), 批次内容未变。
- grilling 两轮 11 问拍板(D5/D10 用户改判, 余全按推荐); 产出: 计划 26-11-18-0259(Open) + issue ②③(Open) + 本档案; 零代码改动, 基线切片不适用(测试面零改动); 本轮产出件随本专题入库。

- 2026-11-18 03:03 立项轮: 根因链闭环(排除面桩实测: /api/state 冷52ms/资产链0.4s/渲染面百毫秒级均非瓶颈; 真根因=重启首轮全量管线挡首次发布: apply_sync+path_map自检+归组files逐种子单发210次+冲突检查, 窗口期group_view_dirty=False返回空视图) + grilling 两轮11问拍板D1-D11(D5改判②③入池issue两件 / D10改判S0只走real-machine轨道不取生产数字) + 计划26-11-18-0259入库Open(S0-S3待显式开工) + 档案立档; 零代码改动
