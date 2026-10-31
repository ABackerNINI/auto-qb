# 26-10-12-webui-traffic-limit-history — qB 流量图限速线按当时值分段

**Status:** Done(26-10-15 状态确认, 计划核到代码)
**Added:** 2026-10-12
**Updated:** 2026-10-15 05:29
**Topics:** webui-traffic-limit-history
**Summary:** 用户命题「流量图限速线显示当前限速值有误导性, 需保存限速更改体现当时的限速, 先写计划, 使用 grilling 技能」。grilling 一轮七问收敛: 记生效值不记曲线目标 / 采样点变化才记 / 前端分段画(各段各区间, 末段到 now, 可见性判据逐段化) / 缺记录不画不回填 / 三挂点与变体维持现状 / 悬停读数增补; D3 用户两轮裁定终值 = **分天保存**(`qb-traffic-v4/limits/<日期>.dat`, 00:00 硬切 + 新天基线 carry, 不淘汰与 day/month 全保留对齐, 无配置键)。追问「不分天吗 / 缺数据区怎么界定 / 保存几年怎么办」推动补强: 读侧 mtime+size 解析缓存、缺数据区界定规则(阶梯函数恒有值, 唯一缺区 = 记录起点前; 停机时刻误差 ≤ 停机时长)、病态翻转常量告警护栏。计划 26-10-12-0535 Open, W1 后端 / W2 前端 / W3 收尾待实施; 纯文档轮零代码, 数字见 `commands run kb.baseline`。**W1-W3 已于 08:15 实施完成, 数字见基线 [26-10-12-0815](../testing/baselines/attachments/26-10-12-0815-webui-traffic-limit-history-w1w3.md); 真机走查(改限速 → 看历史段)待用户; 26-10-15 用户确认完成, 计划与档案状态 Open→Done(实施核到代码)。**
**Refs:** memory-bank/plans/26-10-12-0535-plan-webui-traffic-limit-history.html,memory-bank/testing/baselines/26-10-12-0815-webui-traffic-limit-history-w1w3.md,memory-bank/testing/baselines/26-10-12-1806-traffic-limits-warn-sentinel-ci-fix.md,memory-bank/activeContext/26-10-12-0815-webui-traffic-limit-history.md,memory-bank/pitfalls/testing/monotonic-warn-sentinel.md

## 原始请求

用户原文: 「目前的流量图中显示的限速线是当前的限速值, 有一定误导性, 需要保存限速更改, 体现当时的限速, 先写一份计划, 使用grilling技能」。

## 思考过程与决策

- **现状取证**: 限速线 = `qb_traffic_chart.js` `_qbDrawLimits` 用拉取响应那一刻的 `speedLimitBytes`(单点 `dialogs.js`, 即 `server_state.dl_rate_limit / up_rate_limit`)画满整窗; 限速变化源 = 限速曲线模块每轮查档写 qB(`speed_curve_mod.py`)+ WebUI 手动覆盖 + 备用限速切换; 主循环采样点 `_sample_global` 每轮已拿完整 `server_state`, 记录挂点现成。
- **grilling 七问**(第一轮全前沿一次问齐): D1 记生效值(不记曲线目标——手动保护跳过时目标未写进 qB, 记了是新失真) / D2 采样点变化才记(单线程黄金法则 5、零新增请求、覆盖一切变化源含 qB 原生界面手改) / D3 存储与保留 / D4 前端分段画 / D5 缺区不画不回填 / D6 三挂点 + 变体 13/14/15 维持现状 / D7 悬停读数。用户裁定「其它按推荐」+ D3 修订; 第二轮前沿为空, 收敛。
- **D3 两轮修订**: 初裁「独立文件 + 配置键 90d」→ 用户改「目录与流量数据一致、不加配置键、保留对齐流量图最大保存时间」→ 追问轮(不分天吗 / 缺数据区 / 保存几年)后终裁「**分天保存**」。分天形态: `qb-traffic-v4/limits/<YYYY-MM-DD>.dat`(日期格式单点 `V4_DATE_FORMAT`), 00:00 硬切 + 新天首行基线 carry(单天文件自洽, 读侧拼接不回溯前一天), `limits/` 非系列目录(`v4_rel_dir_to_key` 只认 `global/` 与 `torrents/<hash>`)系列淘汰天然跳过。
- **「保存几年」防御**: 读侧 mtime+size 键控解析缓存(照 `V4DayCache` 形状, 文件没变零解析) + 病态翻转常量告警(照 `_BAD_LINE_WARN_*` 先例, 只告警不删数据——删了违背对齐语义); 正常密度三年千余条 ≈ 百 KB 级, 各层量级核算在计划 §5。
- **缺数据区界定**: 限速是阶梯函数, 记录起点后每个时刻恒有生效值(0 = 不限速也是值), 内部无缺口; 唯一缺区 = 记录起点之前(不画线即「当时值未知」的诚实表达); 停机/写失败窗口内变化的事件时刻误差 ≤ 停机时长(值不丢, 恢复首轮基线补上, 图上不标注)。
- **不推翻 26-10-08 拍板**(任务档案 26-10-08-webui-qb-traffic-yaxis-annotation): 限速取 qB 全局限速、上下载各一条、自动模式峰值超限才画——本计划只改「取值方式」(单值 → 分段历史), 其余判据全部延续。

## 实现计划

见 [计划 26-10-12-0535](../plans/26-10-12-0535-plan-webui-traffic-limit-history.html) §3 方案设计 / §4 波次与验收: W1 后端(`core/traffic_limits.py` 记录器 + 读侧 + `traffic_sample_mod` 接线 + `traffic_qb.py` payload 扩展) → W2 前端(`_qbDrawLimits` 分段化 + 快路暂存 + `_qbHoverOf` 悬停读数 + node 电池红验) → W3 收尾(基线切片 + 文档回写 + 真机走查)。

## 子任务状态表

| 波次 | 内容 | 状态 |
|---|---|---|
| W1 | 后端: 记录器 + 读侧 + payload 扩展 | 完成(2026-10-12) |
| W2 | 前端: 分段线 + 悬停读数 + 守阵 | 完成(2026-10-12) |
| W3 | 收尾: 回写 + 真机走查 | 完成(回写 + 26-10-15 用户确认走查) |

## 进度日志

- 2026-10-12 05:35 计划成文(26-10-12-0535, Open), grilling 七问拍板记录入档(§2)。
- 2026-10-12 06:13 D3 二次裁定分天保存, 计划同文件修订(读侧解析缓存 / 缺数据区界定 / 病态翻转护栏随轮补强, 验收判据扩充)。
- 2026-10-12 06:19 收尾入库: 纯文档轮(计划 + 本档案 + 活跃切片), 零代码零测试改动, 实测数字见 `commands run kb.baseline`; 环境备忘: PowerShell 下 `git grep` 中文输出显示乱码(仅显示层, 文件无损), 查 CJK 内容改用 read 工具直读。
- 2026-10-12 08:15 **W1 后端完成**: 新增 `core/traffic_limits.py`(SpeedLimitRecorder 变化才记 / 00:00 硬切 + carry / 重启去重 / OSError 降级不上抛 / 病态护栏 / LimitsCache mtime+size 键控 / limits_events_for_window 合成首事件 + 同值去重); 接线 `traffic_sample_mod._sample_global`(仅 qB 在线轮, dry_run 同门零写); `traffic_qb.py` 三 payload 统一附 `limits`(空态/全 null 也带, 组空态分支同源; last-good 快照含 limits)。新测试 `tests/test_traffic_limits.py` 12 条(红验两条注入即红/还原即绿); 既有 18 条端点测试扩 `_v4_opens` 排除 `limits/` 归类。
- 2026-10-12 08:15 **W2 前端完成**: `_qbLimitSegs`/`_qbLimitAt` 模块级纯函数(node 电池 12 项真跑); `_qbDrawLimits` 分段化(读 `u._qbLimits`, 逐段可见性, 末段到图右沿); setData 快路/整图重建两路同步暂存 limits; 悬停 tooltip 「当时限速」行(正常/缺口两支, `h-limit`); 统计栏悬浮说明增补 D4 文案; 静态守阵更新(旧单值断言替换为分段锚 + 旧回潮反向断言)。变体 13 不自建 uPlot 图零回归(14/15 共享钩子自动生效)。
- 2026-10-12 08:15 **W3 收尾**: `test.full` 3144 passed + 3 skipped(上基线 3132 + 12 新测试 = 3144, 逐条对账闭合; skip 4→3 同源环境变化在规划轮基线已核); 全量 e2e **166 passed + 10 skipped**(首轮两次 36/14 条失败全是连接拒绝 —— 另一 clone(auto-qb-clone3) 的会话在跑它自己的 e2e, 同抢 8137 单点端口且收尾兜底互杀对方的桩; 第三轮端口空闲后全绿, 零功能性断言失败); 文档回写 `conventions/webui.md`(注解层限速线条目) + `modules/core-runtime.md`(traffic_sample_mod 职责); 基线切片 [26-10-12-0815](../testing/baselines/attachments/26-10-12-0815-webui-traffic-limit-history-w1w3.md)。**环境教训**: PowerShell 管道 `Set-Content -Encoding utf8` 写 CJK 会产生双锟乱码(已把本档案写成乱码一次, git 恢复) —— memory-bank CJK 文件一律走 edit/write 工具, 不走 PowerShell 管道改写。
- 2026-10-12 18:07 **CI 红修复(后续轮)**: GitHub CI 上 `test_traffic_limits.py` 两条 caplog 断言红(`test_recorder_oserror_degrade` / `test_recorder_patological_flip_guard`, 签名 `assert False = any(<generator ...>)`), 而本机全绿。根因 = `SpeedLimitRecorder._oswarn_ts` / `_guard_ts` 拿 `0.0` 当「从未告警」哨兵, 但 `time.monotonic()` 的 0 点是**机器开机时刻** —— 开机不满节流间隔(3600s)的 CI 全新 VM 上 `now - 0.0 >= GAP` 判假, **首次告警被静默吞掉**; dev 机 uptime 数十小时故本机恒绿(非平台差异, 是 uptime 差异)。修法: 两处哨兵 `0.0` → `None` + 判据补 `is None or`(对齐 `core/traffic_store.py::_warn_bad_lines` 的 `prev is not None` 判法, 即本模块 docstring 已承诺的同款), 并新增守阵 `test_recorder_warn_first_fire_on_fresh_boot`(`monkeypatch.setattr(模块.time, "monotonic", lambda: 120.0)` 把时钟钉在开机 2 分钟, 断言首次告警必发)。**红验(本机等价论证, 不依赖 CI)**: 同一时钟下还原旧哨兵 ⇒ 精确复现 CI 那两条红; 修复后同条件 13 passed; 守阵在旧哨兵下本机即红、还原即绿。`test.full` 数字与覆盖率见基线 [26-10-12-1806](../testing/baselines/attachments/26-10-12-1806-traffic-limits-warn-sentinel-ci-fix.md); 坑档 [monotonic-warn-sentinel](../pitfalls/testing/monotonic-warn-sentinel.md)。**为什么没命中**(W1 时没预判): 写节流时按"先例对齐"抄了 `_BAD_LINE_WARN_GAP_S` 的**数值**, 却没抄它的**哨兵判法**(`prev is not None`) —— 数值同源而哨兵异源, 差别恰好在"从未告警"这一支上。
- 2026-10-15 05:29 **状态确认 Open→Done**(用户「计划似乎已完成, 确认后更新状态」): 核到代码——W1 `core/traffic_limits.py` 现档 + `traffic_sample_mod._sample_global` 接线(`SpeedLimitRecorder`)+ `traffic_qb.py` payload 附 `limits` + `tests/test_traffic_limits.py`; W2 `qb_traffic_chart.js` `_qbLimitSegs`/`_qbLimitAt` 分段化 + 快路 setData 暂存 + 悬停「当时限速」; W3 回写现档(`conventions/webui.md` 注解层限速线条目 + `modules/core-runtime.md` 限速历史记录)+ 基线切片 0815/1806 现档。计划 26-10-12-0535 与本档案同步 Open→Done, 计划补变更记录行。纯文档轮零代码零测试改动, 数字见 kb.baseline。
