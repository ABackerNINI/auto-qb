# 6115 —— 6115 passed + 2 skipped(根宿主 Windows) —— relocate 形态感知判据 P4 真机验收批次(E1-E9 38 判定全 PASS: E 矩阵 25 + 相位判定 13)

> 摘要: 6115 passed + 2 skipped(根宿主 Windows) —— relocate 形态感知判据 P4 真机验收批次(E1-E9 38 判定全 PASS: E 矩阵判定 25 条 + 相位/清场判定 13 条)
> 基线时间: 2026-11-14 06:37
**Refs:** memory-bank/testing/real-baselines/26-11-14-0635-real-relocate-form-gates-p4.md

## 验收数字

```text
TOTAL                                                27279     68   9580     73    99%
6115 passed, 2 skipped in 190.34s (0:03:10)
```

(实测时点: R1-R5 五笔落地(ba098a33..7f93de58) + P4 真机全链路验收 E1-E9 复跑 38 判定全 PASS 后收尾
`commands run test.full` 2026-11-14, 根宿主 Windows; 上一切片 26-11-13-0411 在 env3 Linux 6075+19,
本切片 6115+2: 差值 =  intervening 批次(webui 键位收尾等)增量 + 本批 relocate 判据改写伴随的表驱动用例
翻新, 平台差按 26-11-13-0411 的既有说明口径, 零回归; 覆盖率 TOTAL 27279 语句 / 68 miss / 9580 分支 /
73 partial = 99%, 缺口净额 141 与上片口径同源)

## 本改动面

- **验收批次**: relocate 形态感知判据计划 26-11-13-0448 的 P4 段 —— 真机全链路验收 E1-E9 在修后代码
  (基线 7f93de58)路径上全量复跑, 38 判定全 PASS / 0 FAIL(E1-E9 矩阵判定 25 条 + 相位/清场判定 13 条),
  回炉条款未触发; 切片见
  `testing/real-baselines/26-11-14-0635-real-relocate-form-gates-p4.md`(环境指纹/逐条断言/修前 vs 修后
  对照/证据指针)。
- **实验面**(gitignored .work): `tests-real/.work/relocate-form-gates/run_exp_p4.py`(22 相位(21 + reinject
  重做相位)harness,
  断言翻转到修后期望; E8 进程内门级注入)+ exp_state_p4.json + evidence-p4/(86 件)。T1 产物未触碰。
- **测试面**: 本批零产品代码改动(P4 为验收段); test.full 全绿含 relocate 判据改写的既有表驱动用例
  翻新(P2/P3 批次随 7f93de58 入库)。
