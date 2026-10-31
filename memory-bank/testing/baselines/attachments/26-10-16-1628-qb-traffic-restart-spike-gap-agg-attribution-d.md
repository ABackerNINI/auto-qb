# 3483 passed + 4 skipped —— agg 行 totals 归属错位修复(形态 D: z 行扩末端快照对)

> 摘要: 用户拍板形态 D(plan 26-10-16-1509 §04, 指令「选择方案D」)→ 实施落地: z 行扩「末端快照对」列(`z,<run_len>,<dlt>,<upt>,<dl_end>,<up_end>[,<dt_ms>]`, 位次在可选尾列 dt_ms 之前; 旧 4/5 列解析为 None → 退化冻结), 在线 `_agg_feed` 与离线 `_agg_credit_day_file` 改按两路共用纯函数 `v4_z_totals_ramp` 把「开启快照 → 末端快照」逐槽摊配(端点精确 / 整数半上取整 / 逐向独立 / n=1 与无末端与末端低于开启恒取开启快照), 游程尾部信用由冻结值改为末端快照(ramp[-1]); 封口末端锚点解析单点 `_resolve_run_end`(显式实测样本 > 游程内最后一条零样本读数(`OpenRun.last_*` 跟踪字段) > 开启快照, 低于开启按开启钳制 —— 游程内计数器重置); raw 面零触碰(冻结列 / `V4Slot.obs` / 差分链逐字不变)。改动 2 源文件 + 2 测试文件(新增 7 条用例: 摊配纯函数专测 / 形状兼容 / 在线摊配 / 两路同源 / 封口路径 ③④ 跟踪值 / 重置退化 / 路径 ① 补钉; 重钉 6 条既有格式与 roundtrip 钉子)。
> 基线时间: 2026-10-16 16:28
> 档案: memory-bank/tasks/26-10-15-webui-qb-traffic-restart-spike-gap.md

- test.full: 3483 passed + 4 skipped / TOTAL 17682 语句 245 未覆盖 6012 分支 180 partial / 98%; `Required test coverage of 98% reached. Total coverage: 98.18%`(闸门过)。耗时 182.5s(测试体 179.96s) / 251.2s(测试体, 回写轮中途同树二次采样 —— 该采样的 5 条红全部是「新增文件后索引未重建」的文档一致性守卫(plans/_index 陈旧 / 认领链目标(本切片)尚缺 / pitfalls 索引未登记新坑档), 非代码面; 索引重建后由本切片落盘后的复测收口)。口径见 baseline.md。
- 本轮新增 7 条用例: `test_v4_z_totals_ramp_endpoints_monotone_and_conservation`(摊配 / 守恒 / 半上取整 / 逐向独立 / 降档) · `test_v4_z_end_pair_shapes_legacy_compat`(新旧形状共存 + raw obs 不变 + agg 逐槽序列) · `test_agg_z_end_anchor_interpolates_via_online`(跨小时界逐小时摊配 / 右端对齐 / 无单桶台阶 / rate lane 不变) · `test_agg_z_end_anchor_two_paths_same_hours`(在线 ≡ 离线, 逐样本逐位) · `test_zrun_end_anchor_tracked_reading_on_stop` / `..._on_interval_change`(封口路径 ③④ 跟踪值) · `test_zrun_end_anchor_counter_reset_degrades_to_open`(重置退化 + 末端列 delta 非负)。
- 红绿双验(5 类突变逐类判红; 突变只作用于真文件、当轮还原, 四文件 SHA256 逐位自证): 关插值 → 5 红(roundtrip agg 断言 / 形状兼容 / 摊配专测 / 在线摊配 / 两路同源); 离线侧不读摊配列 → 1 红(两路同源); 末端列写回冻结值 → 5 红(格式文本钉 / roundtrip / ③ / ④ / 两路同源); 路径 ① 不传末端值 → 1 红(idle 游程末端列钉); 取整口径改截断 → 3 红(roundtrip 中值 / 半上钉 / 在线摊配钉)。
- 只读探针对照(内联 `python -c`, 未入库): 合成几何(3 小时 z 游程跨小时界, S0=(1,000,000/2,000,000)) 修复前三个游程内小时行 totals 全 = 冻结快照 → 修复后逐小时摊配、右端小时 = 末端快照、剩余增长只余末段; `v4_block_agg_totals` 与 `v4_block_slots` 等长同序断言进形状用例。
- 环境注记: 本 clone 工具 shell 无 uv(本轮按 `pitfalls/testing/no-uv-fallback.md` 首选处置把 `C:\Users\<用户>\.local\bin` 前置进 PATH, uv 0.12.18 全线恢复); `TEMP`/`TMP` 指 C 盘临时区(R 盘不存在)。python 3.14.7-final-0(uv 解析)。
- Linux/macOS 侧未跑 —— 改动为纯 Python 逻辑与行格式, 无平台分支; 本条 Windows 侧数字为事实源。

## 本改动面

- `src/auto_qb/core/traffic_store.py`: `V4ZeroRun` 加 `dl_total_end/up_total_end`; `format_v4_z_row` 恒写末端对(缺省写冻结列同值 = 显式退化, 负 delta 免费校验扩到末端两列); `parse_v4_day_text` z 行认 {4,5,6,7} 列(旧形状 → None); 新增 `v4_z_totals_ramp` 与 `v4_block_agg_totals` 两纯函数; v4 行型定约注释补末端对语义与「形态 D 回滚约束」(旧解析器对新行整行判坏 → 回滚须先剥列)。
- `src/auto_qb/core/modules/traffic_sample_mod.py`: `OpenRun` 加 `last_dl_total/last_up_total` 跟踪字段; `_seal_run(key, end_dl, end_up)` + `_resolve_run_end` 单点; `_advance_run` 刷跟踪值并把实测样本传给封口(换型/跨天/保险闸三条), `sample_series` 传封口触发样本; `_agg_feed` 与 `_agg_credit_day_file`(含新 `_slot_agg_obs`) 改按摊配入账; 模块头 / docstring 同步。
- `tests/test_traffic_store.py` / `tests/test_traffic_sample.py`: 见上「本轮新增」; 既有钉子重钉四处文本 + 两处 roundtrip 夹具补显式末端值 + 坏行族补新形状; 两个文件头部「测试计划」清单同步。
- `memory-bank/`: issue `26-10-16-0020-bug-agg-hour-totals-frozen-run` → Done(修复后补充填实) + 计划 `26-10-16-1509-*` → Done(§08 待拍板项就地补注 + §09 实施记录 + 变更记录, doc-updated=1621) + 档案 R15 + 子任务表 + Summary/Refs + activeContext 切片更新 + 新坑档 `pitfalls/backend/traffic-row-format-extension.md` + `pitfalls/testing/credential-shape-write-guard.md` 复发 +1(第二处不可写文件, 等价收敛三行)。

**Refs:** memory-bank/tasks/26-10-15-webui-qb-traffic-restart-spike-gap.md
