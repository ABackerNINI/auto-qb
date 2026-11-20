# 6557 passed + 6 skipped —— relocate 重构第二批 S6(探测异步化)收尾全量基线

> 摘要: relocate 重构第二批 S6(探测异步化)收尾全量基线
> 基线时间: 2026-11-20 23:48

## 验收数字

`commands run test.full` 实测(2026-11-20, Windows 开发机, relocate-probe-async @ 824f6b94):

```text
TOTAL                                                29284     54  10444     66    99%
6557 passed, 6 skipped, 8 warnings in 184.19s (0:03:04)
```

- 汇总: 6557 passed / 6 skipped / 0 failed; **覆盖率闸门达标** —— 99.70% ≥ Windows 阈 99.5(tests/conftest.py `COVERAGE_FLOOR_WIN`; 本轮 silent_success 只回显 TOTAL/passed 两行, 精确值由同轮 cov 数据文件 `coverage report --precision 2` 现算, 数据文件时间戳与本轮完成时刻一致), 一次跑绿无中断轮记账; 耗时单次采样 184.19s(并行 -n 8)。
- 缺口净额(M8): 本片 120 单位(miss 54 + partial 66) 减上片 26-11-20-0244 的 106 单位(miss 44 + partial 62) = **+14**; 分母由语句 28901 / 分支 10308 变为 29284 / 10444(S6 批净增 +383 语句 / +136 分支); 净额 ≤ +15 无点名 —— 本批触碰面 relocate 家族无新进榜缺口。
- 差值口径: 上一基线 [26-11-20-0244](26-11-20-0244-relocate-refactor-s5.md) 6495P/6S → 本片 6557P/6S, +62 passed; 增量 = S6 五笔提交新增用例 59 条(T1 17 + T2 8 + T3 13 + T4 15 + T5 6, 逐笔 hash 与落点见「本改动面」)+ rebase 带入的远端推进面 3 条(a14e1e20 ALT 解锁 → test_utils_windows +2, e0411a38 行高恒等 → test_webui_relocate_visibility +1); 上片实测在 rebase 前(80d8ea09), 本片在 rebase 后(824f6b94), S5 两笔 hash 已改写 a652290f→bde75be0 / 80d8ea09→28e3b4dd(树差 27 文件远端推进面, tests 仅上述 +3 用例, 与 R2 先例同型); quick/full 两跑法 skip 面不同(2 vs 6), 逐位对比读两片现算。

## 本改动面

- 五笔提交(relocate S6 第二批, 计划 26-11-15-2340 刀4 探测异步化, 并轨 26-11-10-2350 D1-D10):
  - d899e91a(S6-T1 探测 runner 基建): relocate_probe 增 ProbeSingleFlight 单飞槽 + PROBE_VERDICT_QUEUE 结果队列 + probe_thread_ctx 线程侧独立 qB 连接(new_client 重建不共享主循环 Session) + ProbeRunner 双形态(try_start daemon 线程 / run_inline 注入 seam), run_probe 本体零改动; relocate_mod 增 relocate.probe_pending 容器读写单点(条目 {fingerprint, hashes, src, dst, origin, ts}, setdefault 补键不走版本链); 新增 tests/test_relocate_probe_async.py 17 用例。
  - 9caf2675(S6-T2 _ensure_probe 异步化): 决策表「未命中」分支改意图入队 + 单飞 kick + 探测中回执(cls=blocked + item[probing] 机器键); 合并键收窄为意图三元组(指纹 + 归一 src + 归一 dst, 并轨适配点: probe_fingerprint 实为 qB 连接身份不编码 src/dst); 新增 tests/test_relocate_probe_gate_async.py 8 用例, 既有 gate 10 + probe 36 + T1 17 语义零漂移。
  - 8f129b47(S6-T3 verdict 消费接线): on_task_line 先消费后步进、每 tick ≤1 条, 消费四步(probe_put D7 三态 / 队首指纹一致才重放 relocate_execute 幂等面 / probe_pending_pop 清条目 / 释放槽 kick 下一条); 防自环 = 重放回执带 probing 键终止自动链(消费定形判别改 verdict 真值(failed+env)); 重启恢复 = 队首重 kick(start/apply 对称); 超龄清扫(>PROBE_PENDING_MAX_AGE_S=120s)挂 start+apply; 新增 tests/test_relocate_probe_consume.py 13 用例。
  - 7d99ce32(S6-T4 web 两段回执): 受理段 warn(探测中)+ verdict 终态补发; 补发通道 = cmd_id 绑 pending 条目 receipt_ids + relocate 内存出站面 + webui drain 取走; 新增 15 用例(test_relocate_probe_async 3 + test_relocate_probe_consume 6 + test_web_relocate 6), test_web_commands_bulk 替身签名 1 行适配语义零变化。
  - 824f6b94(S6-T5 sweep 四断点残留核验 + 两洞补扫): 四断点(add 完成/证读中途/证写中途/清理中途)残留清扫面核验; H1 目录残留根集扫描(_probe_pending_roots 取 pending 根集 + _sweep_residue_dirs 直接子目录扫描)+ H3 _map_local namespaced 映射; 目录认领收紧自产 token 形状(评审 major: 裸前缀认领的用户目录误删面, 全修 + lookalike 对照用例); test_relocate_probe 36→42(+6)。
- 收尾回写随本批入库, 纯文档零代码: 计划 26-11-10-2350(R3 并轨执行完成注记, doc-status 保持 Superseded)/计划 26-11-15-2340(R5 + §04-S6 达成口径 + §03.6 0638 行更新)/任务档案 26-11-15-backend-relocate-refactor S6 段/issue 26-11-10-0638 正文注记(状态保持 Open, 待真机复验)/pitfalls/testing/ascii-circled-digits-py-comments.md 复发+1/本切片/kb.wrap 切片行。
- 真机两项拍板延期待真机复验轮: dry-run 冒烟受理段 + FS 不可达 tick 停摆断言(单步预算)。
