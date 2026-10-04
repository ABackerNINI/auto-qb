# HR 已放行记录不覆写守阵 — issue 26-10-02-0526 认领完成 (Done)

> 摘要: 认领 issue 26-10-02-0526 (`_sign_releases` 对已 verified 的 infohash 不查重, `data.verified[h] =` 直接整条覆写既有放行记录, 与「放行永续有效(终态不可逆)」语义冲突)。复验: 覆写赋值点漂移至 src/auto_qb/hr/service.py:1316 (取证基线 b7db4472), 循环守卫仍只有 `h in wave.hits` + 缺席证明两道, 代码层仍复现。**可达性核实为当前代码全路径不可达**: ① `_build_objects`(:1328) 对已 verified 未漂移的 h `continue` 不出对象集、漂移(本机重下)的 h 先 `del data.verified[h]` 回炉再入; ② unmatched ⟹ h ∈ anchors ⟹ h ∈ local_hashes(键集恒等, :286), 本波把该 h 登记进索引必经 `_record_hit` → `wave.hits`(签发跳过)或 tid ∈ `wave.seen`(观察期跳过); ③ 窗口内唯一 verified 写点 `_advance_observation`(:1094, 签发前)只碰「活跃 A 档 + 本波未见」条目, 与 unmatched 无交集; ④ `_freeze_terminal`(:1149)在签发之后且自带 `h not in data.verified` 守卫; ⑤ 其余 verified 写点仅 model.py:642 (from_json 反序列化, 非运行时路径)。按 §06② 补两层守阵: test_build_objects_unit_guards 扩展「已 verified 未漂移不回对象集」半边 + 新增 test_verified_record_not_overwritten_on_rewave(端到端: 跨波记录逐字段原样 + 零二次签发)。红验: 探针摘除排除分支两条件全红(单元红 + releases_signed==1 抓到二次签发), 恢复后绿。test.full 2540 passed + 4 skipped / 99% / 27.60s+27.52s 两次采样 (基线 [26-10-05-0209](../testing/baselines/26-10-05-0209-hr-verified-overwrite-guard.md))。不满足立档阈值, 无任务档案。
> 最后活动: 2026-10-05 02:10

**Refs:** memory-bank/issues/26-10-02-0526-bug-hr-sign-releases-verified-overwrite.html, memory-bank/testing/baselines/26-10-05-0209-hr-verified-overwrite-guard.md

## 现状

- issue Done, 守阵双保险: build 层(排除分支直接钉住) + 波次层(放行记录跨波不被覆写的语义级钉住)。未来任何重构破坏「unmatched 不含已 verified infohash」不变量, 两层任一即红。
- 改动未提交: tests/test_hr_service.py / issue HTML / 基线切片 / 本切片, 等用户显式提交指令。
