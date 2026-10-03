# HR 在线核实四现象故障取证 — 报告出厂, 修复建议待拍板

> 摘要: 用户报四现象(没有本地 HR 种子仍拉取 / 全 B 已达标仍拉取 / B 达标核实结论「未核实」/ 失踪 0 波最近被见到 09-28 07:14), 四阶段串行子智能体取证闭合, 引擎数据/判定侧零故障。
> 最后活动: 2026-10-03 15:30

## 已完成 (2026-10-03)

- **取证**: 主会话只委派, 四阶段串行子智能体 (P1 机制定位 → P2a 症状1-3 → P2b 症状4 → P3 报告),
  零异常失败; 生产数据在主 clone `auto-qb-data` 只读取证 (本 clone 无运行数据), 代码基线
  develop @ 23796f3b (报告行号口径)。
- **报告出厂**: [reports/26-10-03-1505](../reports/26-10-03-1505-report-hr-fetch-verify-forensics.html)
  (dark 单文件, doc-topic `backend-partial-hr-verify` 串联 HR 报告线)。
- **结论**: 引擎数据/判定侧零故障, 四现象全在展示与产品语义层 —
  ①②「仍拉取」= 设计内行为 (账号级对账取数, 闸门 service.py:448-496 无一读本地种子状态, 波内零种子下载;
  「该站点本地没有 HR 种子」= 明细表空态文案, local_present=本地库存在含暂停, 实测本地与清单零交集);
  ③「未核实」= 设计内 + 文案粒度缺陷 (命中 B 刻意不写放行记录, _record_hit 只删; satisfied 唯一写点
  _freeze_terminal 需行消失 + 位置证明; 明细表认 data.verified 与主列表运行时视图双通路结构性矛盾;
  BTSchool 50 / CarPT 17 活跃 B 行 0 verified 实证, 守阵 test_hr_service.py:744);
  ④「失踪 0 波·09-28 07:14」= 显示语义缺陷 (missing_streak 是 A 档观察期计数器, 退役行结构性恒 0;
  09-28 07:14:04 = v2 末次页面合并笔迹, 142 行单秒批量冻结, 此后 35.5h 页面盲窗 + v3 部署崩溃循环,
  09-29 18:50 v3 首健康波终态退役; 127.1h ≈ 25.4 波槽 / 实际 ≥14 波)。
- **未入池候选** (待指派): wave_ts 跨波冻结 (service.py:517-523+649-651, 缺席证明新鲜度闸用陈旧基准,
  保守方向) / 142 行 10-28 过 INDEX_RETENTION 静默清出 (verified 永续, 80 无 hash 行历史无痕迹)。
- 收尾: 档案 [tasks/26-09-22-backend-partial-hr-verify](../tasks/26-09-22-backend-partial-hr-verify.md)
  追加本轮行与日志 / test.full 闸门数字见 kb.baseline 最新切片 / 同步 @ 61c0ddc4
  (远端流量图 P3/P4 + copytext 轮合流, stash→sync→pop 索引零冲突)。

## 状态

取证面完结, 随本轮 ship.commit 入库; 报告 §8 修复建议 (设计确认 1 / 显示文案 4 / 次要 3)
与两项入池候选**等用户指派**。

- 2026-10-03 21:54 — 用户指派 §8 显示文案 B1 并完成修复: 切换钮「显示老旧种子」→「显示未做种」(+ 空表文案换词), 明细见 [tasks/26-10-02-webui-hr-status-display](../tasks/26-10-02-webui-hr-status-display.md) 进度日志 21:54 条。§8 其余条目(设计确认 1 / 显示文案 B2-B4 / 次要 3)与两项入池候选仍**等用户指派**。
- 2026-10-03 23:35 — B1 文案**二次修订**: 用户驳回「未做种/只看做种中」(实为本地已删除 / 反向态含暂停), 改「显示已删除种子 / 只看本地仍在列」; 见 tasks/26-10-02 进度日志 23:35 条。
- 2026-10-03 23:47 — 用户指派「一并看看」→ 完成 §8 **B2 / B3 / B4 与候选 C1** 四项修复(`test.full` 2417 passed + 3 skipped / 99%):
  - **B4 退役行徽章**: 退役行不再借「失踪 N 波」(service.py 退役即把 missing_streak 清零, 显示恒 0 是语义错位) —— 有放行记录显「已移出」(蓝, hr-pres-out), 无记录显「已退役」(中性, hr-pres-off); 「失踪 N 波」只属活跃行观察期(副行「观察期 N」不变)。改 hr_status.js + 三套 UI CSS 成对。
  - **B2 「下次拉取」措辞**: 三处用户可见文案 + kv 行标签改「下次核对清单」, 点明是对账节奏非取种进度(status.py 两处 + hr_status.js kv 行)。
  - **B3 核实结论中间态**: 后端刻意「命中不写 verified」(防伪, test_hr_service.py 守阵), 但无记录 + 行在列 + 终态档(B/C/D)显「未核实」掩没了「已达标」⇒ 新增中间态「在列·<档位人话>」(蓝) + 副行说明。**前端只消费现状字段(verified_source/lane/lane_text/active), 后端零改动**, 严守「切勿改成命中即写 verified」。新增模块级 `hrsTerminalLane` 判据。
  - **C1 wave_ts 跨波冻结(真 bug)**: service.py:522 `wave_ts=prev.wave_ts if prev.ok else 0.0` + 每波 `if st.wave_ts <= 0` 置一次 ⇒ 连续 ok 档的 wave_ts 永停进程内首成功波, 缺席证明新鲜度闸(`anchor.added_on > st.wave_ts`)用陈旧基准。修法 = 不跨波继承(置 0, 本波重算首页时刻)。方向安全(只让合法放行发生, 不新增误放行 —— 缺席仍须本波位置覆盖)。新增回归 `test_wave_ts_refreshes_every_wave_not_frozen`(变异验证: 还原旧码即红)。
  - **未做**: A1 设计确认项(零对象稳态拉长间隔, 产品取舍)与 C3(30 天静默淘汰预告)仍等指派/未动。
  - 回写: 本切片 + tasks/26-10-02 进度日志; `kb.index` 重跑; 基线切片 `testing/baselines/26-10-03-2348-hr-display-defects-b234-c1.md`。
