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
