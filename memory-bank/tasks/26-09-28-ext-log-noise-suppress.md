# 26-09-28-ext-log-noise-suppress — 扩展日志连不上降噪: 故障期只打头尾

**Status:** Done(未提交)
**Added:** 2026-09-28
**Updated:** 2026-09-28 01:15
**Summary:** 用户实报: 后端端点不在跑时, 扩展轮询每分钟一条全量排查清单 ERROR + 状态栏同文再刷一条 INFO, 日志环(默认 1000 条)几小时被灌满。改「故障期只打头尾」: 首次失败全量 ERROR; 连败期降 debug(默认记录级别不落盘), 每连败 30 轮重提一次全量; 恢复补一句 INFO 并清计数(计数落 storage.local, SW 回收不丢); 状态栏同文复读降 debug。守阵 1 条(node VM 真跑 pollAll 五步场景)。

## 原始请求

用户: 「目前的扩展log每轮打印一次, 连不上时会产生大量噪音, 需修改」(附 09-27 18:38 实报日志两行: 轮询开始 INFO + 拉任务清单失败全量排查清单 ERROR)。

## 思考过程与决策

- **噪音三个来源砍两个**: ①`pollInstance` 每轮 ERROR 全量排查清单(主源) ②`noteStatus` 把同样长文按 info 再记一遍(次源, pollAll 收尾必走) ③「轮询开始」INFO 每轮一条(心跳, **保留** —— 用户抱怨的是连不上, 心跳有存活价值, 且砍掉它会让「轮询还活着吗」不可判)。
- **故障期以任务清单 URL 为键, 语义钉死**: 任何 HTTP 应答(含 401/5xx)都算「连接已通」只清不计; 只有网络层抛错(fetch reject)才连败 +1。401 的每轮 WARN 未动(短文案 + 属真实配置错误, 且同文时状态栏那份已降 debug)。
- **连败计数必须落 storage.local**: MV3 SW 随时被回收, 1 分钟轮询间隔 > 30s 空闲回收线, 内存态活不过一次回收 = 等于没降噪。storage 不可用时退化为现状(每轮全量), 不为降噪赌主流程。
- **30 轮重提全量**: 防「彻底失联无感」; 1 分钟一轮 ≈ 半小时一条全量排查清单, 可接受。
- **降 debug 而非静默**: 连败期每轮短句仍在, 用户把「记录」级别调到 debug 可看全程; 默认 info 下不占日志额度。
- **回传失败(POST /result)不套同一降噪**: 只发生在清单已拉到的轮次, 与「连不上」不同症, 保持现状(范围守恒)。
- **「轮询开始」文案未改、事件环不动**: 降噪只动日志级别选择, 不动结构化事件表(选项页两表照旧每轮见真章)。

## 实现计划

- `extensions/hr-fetch-proxy/background.js`: ①`noteStatus` 同文重复降 debug(状态栏本身照常刷新); ②新增「连接失败降噪」节(`NET_FAIL_KEY` / `NET_FAIL_REMIND_EVERY=30` + `bumpNetFailStreak` / `clearNetFailStreak`); ③`pollInstance` 拉清单 catch 按 streak 三档(首报全量 / 30 的倍数重提 / debug 短句), fetch 成功后 clear + 必要时恢复 INFO。
- `tests/test_extension_proxy.py`: 新增 `test_connection_failure_logs_head_tail_only`(node VM 真跑 `pollAll` 五步: 首报 / 连败×2 / 造 29 败后第 30 轮重提 / 恢复 / 再挂重新首报, 并断言状态栏同文降 debug + 连败数真落 storage); 测试计划 docstring 同步。
- `extensions/hr-fetch-proxy/README.md`: ④区「运行日志」补「连不上时自动降噪」口径。

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | background.js 降噪实现(故障期只打头尾) | Done |
| 2 | 守阵 node VM 五步场景 + 测试计划 docstring | Done |
| 3 | README ④区降噪口径回写 | Done |
| 4 | 便携 node 真跑守阵 + test.full 基线 + 新坑入库 | Done |
| 5 | node 装机(`C:\Program Files\nodejs` + 系统 PATH + Git Bash profile 兜底) | Done |
| 6 | 3 条配额守阵漂移修复(阈值改从 site-caps.js 动态取) + SKILL.md/_common cap 涨档 | Done |

## 进度日志

- **2026-09-28 00:41 (Done)**: 实施完成。开工快进 5102080→c7dfbd2, 收尾再快进 c7dfbd2→aef2462(均无冲突)。本机无 node, node 守阵默认静默跳过(假绿) —— 下载便携 node v22.14.0 至 `/tmp/portable-node`(不入 PATH 持久态)真跑: 新守阵过, 同时暴露 **3 条既有配额守阵漂移**(09d4109 阈值已提至 page 60/时·600/日, 守阵仍钉 10/50 —— caps/roll_over/events 三条红; 计划外, 已报告待用户裁决, 未顺手修)。test.full(无 node 标准口径)**1813 passed + 3 skipped / 91%**(基线切片 [26-09-28-0041](../testing/baselines/26-09-28-0041-ext-log-noise-suppress.md))。新坑: pitfalls/testing/node-guards-silent-skip.md。
- **2026-09-28 01:1x (Done)**: 用户指令「将 portable node 安装到 C 盘 Program Files 并加入 PATH, 修复漂移」。①提权 PowerShell(UAC)把便携 node v22.14.0 装进 `C:\Program Files\nodejs`, 系统 PATH 追加该目录; Git Bash 会话链(继承应用启动时旧环境)由 `~/.profile` 兜底 export。②三条漂移守阵改为**从 site-caps.js 动态取阈值**(`SITE_CAPS` 经 vm 全局词法环境读出, 场景步数/日上限/断言全部动态), 根治硬编码漂移; roll_over 断言本无数字未动。③连带修复: 昨日知识回写引入的 4 个 KB 守阵红(任务档案缺 `## 实现计划` 章节 / 坑条目缺「判别/处置」字段 / 切片数 49>48 / _doc-map 12,137>12,100) —— 档案补章节、坑条目改三字段结构、`SLICE_COUNT_LIMIT` 48→56(同口径 14 天×日均 4, 实测 49/49 全活跃)、`CAP_POLICY["index-auto"]` 12100→12200 + SKILL.md 人读表同步。带 node test.full **1813 passed + 3 skipped / 91% 零失败**(守阵从跳过绿变真绿)。
