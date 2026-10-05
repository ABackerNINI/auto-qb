# 基线切片 26-10-05-1007 — qB 流量存储 v3 S6 活尾合流(raw 段窗实时)

> 摘要: v3 真机验收发现「流量图不实时更新, 得等后端数据落盘时才更新」—— 根因 = 写侧
> flush_interval(默认 600s)批量落盘 与 读侧纯磁盘取数(V3DayCache)之间无活数据桥。
> S6 修法(方案 A): 采样模块每轮发布不可变 LiveTail 快照(未落盘 buffer 记录 + 开放游程),
> 三端点 raw 段窗(1m-24h)合流(v3_live_tail_slots 复原绝对槽位: head_pending 整块重算 /
> 否则从写侧游标倒推), 槽 ts 镜像保证下按 ts 精确去重 —— 图面尾部随采样节拍实时,
> 快照与 flush 竞态不重不漏。新增守阵 7 条(store 3 / grid 1 / sample 1 / web 2)。
> 基线时间: 2026-10-05 10:07

**Refs:** memory-bank/tasks/26-10-04-backend-qb-traffic-storage-v3.md, memory-bank/activeContext/26-10-05-1005-qb-traffic-v3-s6-live-tail.md

- 分支: develop @ 86441e54 + 工作区改动(未提交, 等提交指令; 树净度量 = stash 往返实测)
- 命令: `commands run test.full`(Windows, 两次采样)
- **实测 (Windows)**: **2596 passed + 4 skipped, 29.09s / 31.05s(两次采样), 覆盖率 TOTAL 99%**
  (15482 语句 / 163 未覆盖 / 5330 分支 / 137 partial; 门槛 98% 达标)
- 相对本 clone 改动前真值 (stash 往返实测 HEAD 86441e54: 2589 passed + 4 skipped / 15398 语句 /
  162 未覆盖 / 5296 分支 / 137 partial / 32.73s): passed **+7** = 本轮新增守阵(store 3 + grid 1 +
  sample 1 + web 2); 语句 +84 / 分支 +34 / 未覆盖 +1(v3_live_tail_slots 防御分支); skip 集合不变。
  耗时 29.1~31.1s 与改动前 32.7s 同噪声带, 非回归。
- ⚠ 上一条基线 [26-10-05-0846](26-10-05-0846-test-ci-timing-upper-bound.md) 的绝对语句数(15576)
  在本 clone 不可复现 —— 该基线在另一 clone 测得, 其 danger-guards 提交哈希与 Gitee develop 上的
  重写哈希不一致(内容等价, 本 clone 无 bcc2bce2 等对象); 本 clone HEAD 字面真值 15398 语句经
  stash 往返实测钉住, 分支数(5296)与 0846 一致。后续基线对比以本条为最新语句面基线。
- 核心守阵(镜像保证 = 去重正确性根基): `test_v3_live_tail_slots_mirror_identity_family` ——
  磁盘部分块槽 + 活尾槽 == 整块重算槽(逐槽恒等; 块全量未落盘 / 中途 flush 显式 dt+z/n 游程混排
  两分割族); web 层 `test_api_traffic_qb_global_live_tail_realtime` 钉住端到端三态逐点一致
  (纯活尾 → 滞后快照重列已落盘记录 → 快照清空纯磁盘)。
- 已知留面(记录非缺陷): agg 段窗(3d/7d/30d/6mo/1y/all)仍纯磁盘 —— 未完结小时/日/月桶缺口
  (当前小时不出 3d 图 / 当日不出 1y 图 / 当月不出 all 图)未合流, 留待后续切片(候选 S7)。
