# WebUI qB 口径流量图 — 实施完成 + 配置边界放宽跟进 (待真机长期观察)

> 摘要: 方案C 实施全部完成 (2026-10-04)。六笔实现提交: P1 采样器核心 1c78218b → P2 dat 存储层 687fe827 → P3 冻结/淘汰 da23e842 (体量 39.1MB ≤ 41MB) → P4 三 GET + 组读侧聚合 61c0ddc4 (金清单 75) → P5a 235507af / P5b 181d90c3 (uPlot 三挂点, 三主题截图自查 30/30)。S6 收尾 (2026-10-04, 续做轮): 前任执行者 sim_qb.py 半成品审计续用 (alltime_dl/alltime_ul 真键名 + 重启回落语义) + 修复语料档 pump AttributeError (回归钉变异验证红→绿) + **P6 十条桩验证 10/10 过** (用户拍板桩验证替代真机; 逐条记录 = 档案「P6 验证记录」节) + 三处裁决口径落定 (catch-up 补封 / 损坏阈值坏行 ≥2 / 分组弹层新建)。计划 [26-10-03-0946](../plans/26-10-03-0946-plan-qb-traffic-charts-c.html) 状态 Done, 档案 [tasks/26-10-03-webui-qb-traffic-charts](../tasks/26-10-03-webui-qb-traffic-charts.md) Done。**跟进轮 (2026-10-04 03:0x): 用户报设置保存被校验拦 (sample_interval 须 >= 15s / raw_window 须 <= 259200s), 按拍板放宽三边界 —— 采样间隔 1.5s~10M / raw 1H~90D(3 个月) / rollup 7D~无上限(等效永久); 连带修 24h 栅格桶宽 ceil(小数间隔下 floor 伪断线) + `_try_time` 整数秒报错显示; 同步 keys.md/keys 表/docstring 口径。**test.full **2418 passed + 3 skipped / 99% / 25.85s** (基线切片 26-10-04-0115; 跟进轮新基线见 [26-10-04-0308](../testing/baselines/26-10-04-0308-webui-qb-traffic-bounds-widen.md))。

> 最后活动: 2026-10-04 03:08

**正在进行**: 无 —— 跟进修复完成, 待用户提交 + 真机长期观察。

**待办**: ① 用户真机走查两项桩外遗留 (fastresume 单种 all-time 持久性 / alltime 回退幅度), 结论回写计划 §10.2 与档案; ② 主 issue 26-09-27-1248 真机观察期后收口。
