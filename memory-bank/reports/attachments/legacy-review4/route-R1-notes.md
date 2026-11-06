# R1 路线小结(存量代码评审 R4 · 计划 26-11-05-2335)

- owner: clone1-main · freeze: `f088329291e6`(manifest 钉值,git archive 快照评审)
- 执行模式: 主会话委派,每批分面 3 个只读 reviewer 子代理串行派遣(正确性+设计 / 安全+黄金法则 / 测试缺口+文档漂移+R2 复验),发现合并去重后过 `review.check --root <快照>` 逐字校验(0 弃)再落盘。
- 终态: 7/7 批 done,findings **107 条**(major 12 / minor 32 / nit 63),全数过引文校验。

## 批次勾选表

| 批 | 对象 | 行数 | findings | major/minor/nit | 备注 |
|---|---|---|---|---|---|
| R1-1 | 内核执行面(qbmanager/taskqueue/module/qbapi/state 等 13 件) | 3476 | 21 | 1/9/11 | state.load 恢复写回未持锁可写盘(major) |
| R1-2 | 迁移执行(relocate_units/exec/common) | 2096 | 13 | 2/4/7 | 建链崩溃窗口孤儿链接非幂等 + cancel 未核删净即搬回(major×2) |
| R1-3 | 迁移规划与生命期(plan/probe/proof/lifecycle/mod) | 1804 | 18 | 5/4/9 | B′/visibility_only 弱证据跳过 E1 强探测;probe tag 认领无前缀守卫可误删用户数据;run_probe 主循环阻塞 25s+;stop() 清空未载 job 账(major×5) |
| R1-4 | traffic 存取(store/codec/grid/limits/curves) | 3017 | 10 | 0/2/8 | 契约单点 z 行规格漂移 + limits 撕裂尾注释失实(minor×2);测试密度极高零缺口 |
| R1-5 | traffic 采样(sample_*/snapshot/traffic_source) | 2838 | 16 | 1/2/13 | 已关日 hour 重封无合流源致聚合腐蚀(major);day 行回退/endpoint 指针外发面(minor×2) |
| R1-6 | 分组与规则(grouping/rules/tvshows) | 1927 | 15 | 2/6/7 | _DIR_SEASON_SUFFIX_RE 灾难性回溯(主循环可被打挂);UNDETERMINED 闸门零测试(major×2) |
| R1-7 | ops 与维护面(ops_*/fuse/maintenance/speed_curve 等 12 件) | 2775 | 14 | 1/5/8 | 跳检崩溃恢复重加缺 contentLayout/限速参数,恢复种子可能 missingFiles+PT 义务丢失(major) |

## R2 底册复验汇总(6 条复发口径见注)

| R2 条目 | 批 | 结论 | 证据一句话 |
|---|---|---|---|
| A-06(defer 占 due 批次) | R1-1 | 已消失 | taskqueue.py:288 弹出只按可执行批次计预算,守阵 test_run_due_defer_gate_does_not_consume_budget |
| A-03(建链失败 REMOVED→REBUILD 链路) | R1-2/R1-3 | **复发**(风险已收敛) | 链条逐锚点仍在(exec:248 alias_partial→reconcile ACT_REBUILD);注: REBUILD_MAX_ATTEMPTS=3+退避已上界,若 R2 原报主张是"无界循环"可改判已消失 |
| A-04(先 _persist 后 setLocation/恢复一律 issue=False) | R1-2/R1-3 | 已消失 | _load_jobs 相位区分+move_issued 分流补发,四条守阵在位 |
| A-01(相位机无 dry_run 闸) | R1-3 | 已消失 | lifecycle:243/exec:872 双闸+三守阵 |
| A-02(失败路径成员恢复) | R1-3 | 已消失 | _fail 收口单点消费 resume_hashes,守阵两例 |
| A-05(收尾全库先发 files API) | R1-3 | 已消失 | exec:516-518 先过滤再取文件表,守阵 test_finalize_members_prefilters_file_table |
| GH-01(finalize_watch 心跳/journal 头注) | R1-3 | 已消失 | 三处均修: 心跳拒写即退休/max_wait 文档化/头注改两写者 |
| C-01(聚合 cov_s 无下限) | R1-4/R1-5 | 已消失 | codec:427-432 cov<1 raise + agg fail-closed,issue 26-10-30-0622 |
| C-02(curves 隐式 Optional) | R1-4 | 已消失 | curves.py:76 已显式 `date \| None` |
| A-07(ensure_running 方向相反) | R1-5 | 已消失 | agent.py:419 已改 `is False` 同族判据 |
| A-08(ops 死绑定×2) | R1-7 | 已消失 | commit 97af2ca7 删除两处,AST 扫描零残留 |
| T-04(gtm 门面漂移) | R1-1/R1-5/R1-7 | 已消失 | 进度注追平 S0-S9/通知链路改零读盘直达 |

复发净结论: 12 条复验项中 11 条已消失(均有对应修复与守阵),仅 A-03 以「链路仍在(已加上界)」口径记复发。

## 自弃发现记录(评审中识别、按不报清单主动放弃)

- taskqueue Task.torrent/run_count/attempt 有真实消费方,不属死字段(R1-1 面1)。
- episodes 集数 9999 钳制因正则 `\d{1,4}` 不可达,不构成缺口(R1-1 面3)。
- curves.curve_speed 空档位 IndexError 由 config 校验层保证非空,无具体失败场景(R1-4 面1)。
- v4_live_tail_slots 的 head_pending+空 records 状态经发布方(_publish_live_tail)核验不可达(R1-4 面1)。
- traffic_store_codec B 行 start_epoch 负值被下游窗口过滤吞掉,实害无(R1-4 面2)。
- math/Mapping 及 v4_* 在 traffic_sample_mod 顶层属声明的重导出面(R1-5 面1)。
- notify force 重挂覆盖 enabled=false 是注释明说保留的 L1 旧语义(R1-7 面1)。
- dry-run 下写 state 日键带显式 dry_run 标记字段,属有意设计(R1-7 面1)。
- prune_day_keys 两处 lambda(k,v 取值不同)经契约核对均正确(R1-7 面2)。
- 面3(R1-7)曾误在快照根短暂生成 .venv(核验用),当场删除;主会话已核实快照根无残留、标记吻合后才采信该面发现。

## 过程记录

- 工具缺陷修复 1 处: review_pack.py `_resolve_root` 对快照目录死拒(.git 检查),已加 `require_git=False` 放行 check 子命令(pack 保持强校验),commit d2b272a5。
- 每 findings 落盘前经 `review.check --root <快照>` 全量引文校验,7 批累计 107/107 PASS、0 REFUTE。
- 进度与状态单点: route-R1.json(脚本维护);发现单点: route-R1-findings.json。
- 派遣全程串行(每批 3 面),未触发宿主并发上限。
