# HR 稳态降频实施计划入库 (报告 §13 → plan 工位)

> 摘要: 把取证报告 26-10-03-1505 §13 后记(可行性 + 拍板 idle_refresh_interval 默认 24H 默认启用)转成分步实施计划 [26-10-05-0555](../plans/26-10-05-0555-plan-hr-steady-throttle.html)。核实轮(HEAD ee52e57d)裁定: 报告 §10 缺陷清单 7 项中 <b>5 项已实施完毕</b>(B1/B2/B3/B4/C1 —— 9400296a「显示缺陷修复 + wave_ts 修 C1」等, B1 更早随状态显示改版), 遗留仅 A1 稳态降频(计划核心 S1-S6)与 C3 淘汰预告(候选, 拍板点 D2)。计划含三块核实增量: ①实施锚点行号全量重标(报告两代基线 23796f3b/beb6223d → HEAD, 如 _build_objects 1327-1365 / 间隔闸 479-489); ②报告未载的实施面事实(配置链四点 models/loaders/sections/schema、versioning「补字段不造版本」⇒ HrWaveMeta.idle_mode 免迁移、视图四调用方全走落盘 ⇒ 判据须落盘、site_conf_interval 展示单点); ③§13.3「锚点失败≠稳态」精确化成三态契约(worker._collect_anchors 失败返回 None, run_once .get(site,{}) 区分零锚点, refresh_site:432 去 or {} 吞并)。设计要点: 现算点提级 _refresh_locked 顶部传参进 _do_wave(杜绝双回炉), 稳态旗标翻转才写盘(守自动 poll 零写盘纪律), 展示走 site_conf_interval 单点跟随。报告 §13.6 留的「B2 是否同批」已无需拍板(9400296a 已实施); 剩拍板点 D1(kv 行稳态注记, 推荐做)与 D2(C3 同批与否, 推荐不同批)。
>
> 最后活动: 2026-10-05 08:55

**Refs:** memory-bank/plans/26-10-05-0555-plan-hr-steady-throttle.html,memory-bank/reports/26-10-03-1505-report-hr-fetch-verify-forensics.html

## 正在进行

- (已收口) 拍板点 D1/D2 已随实施轮回写计划 §05「结果」列; 计划 S1-S6 六阶段实施完成, 状态 Done —— 实施记录与遗留见 [实施切片](26-10-05-0855-hr-steady-throttle-impl.md) 与任务档案 [26-10-05-backend-hr-steady-throttle](../tasks/26-10-05-backend-hr-steady-throttle.md), 本切片不再续写。

## 本轮完成

- 计划文档入库: plans/26-10-05-0555-plan-hr-steady-throttle.html (doc-topic hr-steady-throttle, 状态 Open)。
- 认领链: 计划 doc-refs → 报告; 报告 doc-refs 反向声明计划 (doc-updated 抬 26-10-05-0555)。
- 核实轮结论与行号重标表沉淀在计划 §01 (报告正文不动)。
