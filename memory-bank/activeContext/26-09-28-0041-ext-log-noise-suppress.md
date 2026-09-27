# 26-09-28-0041-ext-log-noise-suppress — 扩展日志连不上降噪

> 摘要: 用户实报扩展轮询在端点连不上时每分钟刷全量排查清单。改「故障期只打头尾」: 首报全量 ERROR,
> 连败降 debug(每 30 轮重提), 恢复补 INFO 并清计数(计数落 storage.local, SW 回收不丢), 状态栏同文复读
> 降 debug。守阵 1 条(node VM 真跑)。3 条配额守阵漂移已修复(阈值改从 site-caps.js 动态取), node 已装机。
> 最后活动: 2026-09-28 01:15

## 已完成

- `background.js` 降噪三件套: `noteStatus` 同文降 debug / 连接失败降噪节(`NET_FAIL_KEY` + `NET_FAIL_REMIND_EVERY=30` + bump/clear 助手)/ `pollInstance` catch 三档分级 + 恢复 INFO。
- 语义钉死: 任何 HTTP 应答(含 401/5xx)= 连接已通只清不计; 网络层抛错才连败; storage 不可用退化为现状(每轮全量); 「轮询开始」心跳与 401 WARN 未动; POST /result 失败不套降噪(不同症)。
- 守阵 `test_connection_failure_logs_head_tail_only`: node VM 真跑 pollAll 五步(首报/连败×2/造 29 败后第 30 轮重提/恢复/再挂重新首报)+ 状态栏同文降 debug + 计数真落 storage; 测试计划 docstring 同步。
- README ④区补「连不上时自动降噪」口径; 基线切片落(1813 passed + 3 skipped / 91%, 对比 26-09-28-0014 净 +1 零回归); 新坑 pitfalls/testing/node-guards-silent-skip.md。
- 开工快进 5102080→c7dfbd2、收尾再快进→aef2462(均无冲突)。
- **01:1x 用户指令追加**: ①node v22.14.0 装机 `C:\Program Files\nodejs` + 系统 PATH(提权 UAC)+ `~/.profile` 兜底(工具会话链继承旧环境); ②3 条配额守阵漂移修复 —— 阈值改从 `SITE_CAPS` 动态取(场景步数/日上限/断言全动态, 根治硬编码漂移); ③连带修 4 个 KB 守阵红(档案补 `## 实现计划` / 坑条目补「判别/处置」/ `SLICE_COUNT_LIMIT` 48→56 / `CAP_POLICY["index-auto"]` 12100→12200 + SKILL.md 表同步)。带 node test.full **1813 passed + 3 skipped / 91% 零失败**。

## 正在进行

- 无(实施完毕; 未提交)。

## 下一步

- 用户说「提交」走 my-commit-flow(提交前预检会再同步一次)。
- 扩展真机走查(可选): 加载未打包扩展, 停掉后端看选项页日志区 —— 首报 ERROR 后应安静, 半小时一条重提, 拉起后端补一条「端点恢复」。
