# 基线切片 26-10-04-0115 — qB 流量图 P6 桩验证收尾 (corpus pump 回归钉)

> 摘要: qB 口径流量图方案C S6 收尾轮: 前任 S6 执行者 sim_qb.py 半成品审计续用 + corpus 档 pump AttributeError 修复 + P6 十条桩验证 (替代真机, 用户拍板) + 回归钉 1 条。

- 时间: 2026-10-04 01:15 (GMT+8)
- 分支: develop @ 926d1f66 (基线含远端合入的其它 clone 提交; 本轮回写件全部待用户提交指令, 未 commit)
- 命令: `commands run test.full`
- 实测: **2418 passed + 3 skipped, 25.85s, 覆盖率 99%** (14395 语句 / 131 未覆盖 / 4810 分支 / 104 partial; Required coverage of 98% reached)
  - 本轮起点 (修复后未加测试时) 复跑一次: 2417 passed + 3 skipped / 29.21s / 99% — 新增回归钉 +1 passed。
- 改动面:
  - `scripts/sim_qb.py` (+21/-3): ①假 qB server_state 补真键名 `alltime_dl/alltime_ul` (旧键名 `all_time_*` 与采样器 `_GLOBAL_FIELDS` 不符会让全局系列恒 null; 前任 S6 半成品, 审计规格正确续用); ②alltime 语义: 基值 = 建库时 sum(uploaded/downloaded), 运行期只增不减 (与种子删除解耦), 进程重启回落基值 → 供 §03.4 回落判重置桩验证; ③修复半成品引入的计划内缺陷: 三属性只会在 `_build_torrents`(合成档)初始化, 语料档 pump 首拍 AttributeError 死线程 → 提到 `__init__` 无条件初始化。
  - `tests/test_sim_corpus.py`: 新增 `test_corpus_mode_pump_touches_alltime_accumulators` (变异验证: 还原为仅合成档初始化即红) + 文件头「## 测试计划」清单同步。
- P6 十条桩验证: **10/10 过 (其中 A5 复述 S5b 结论不重跑; A1 持久分支/A7 指纹换键分支为桩外项, 以单测+设计佐证)** —— 逐条方法/实测数字/结论单点在 [tasks/26-10-03-webui-qb-traffic-charts.md](../../tasks/26-10-03-webui-qb-traffic-charts.md) 验证记录节。
- 未做: 真机长期观察 (桩无法替代; 主 issue 保持 Open 待真机)。
- 未验证面: 真机 fastresume 单种 all-time 持久性 / alltime 回退幅度 (qBittorrent-data.ini 落盘周期) —— 待用户真机走查。
