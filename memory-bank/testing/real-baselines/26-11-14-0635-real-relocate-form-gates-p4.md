# relocate 形态感知判据 P4 真机全链路验收: E1-E9 修后代码路径全量复跑 —— 38 判定全 PASS(E 矩阵 25 + 相位判定 13), 回炉条款未触发

> 摘要: 计划 `plans/26-11-13-0448-plan-relocate-form-aware-gates.html` §04 P4(环境1 D盘机, 主实例 36595)。
> 修后代码(基线 7f93de58, R1-R5 全落地)路径上 E1-E9 全量复跑: 误拦两单真机翻转(异名添加预检 confirm -> **ok 零弹窗** /
> 组外异名带文件删除 D16 拒 -> **当场成功**), 同名仍拦(新文案「与成员别名链接同名/经链接共享同一份物理数据」),
> 删链门交集豁免(组外异名 B 在场而依赖计数=1, 同名真依赖清除后 done+别名删), 成员收缩 N=3 拍收敛(members_gone +
> WARNING + 持久反馈面 note + daemon member_gone settled), 目录级回归四断言(==src confirm/深层新弹窗/scope 外兄弟 ok/
> D16 原样), E8 注入取数失败两门保守(删链门计依赖/D16 照旧拦), E9 自愈全链零人工收敛 done。38 判定全 **PASS** / 0 FAIL
> (构成: E1-E9 矩阵判定 25 条 + 相位/清场判定 13 条, 见 exp_state_p4.json results 账),
> 回炉条款未触发。test.full 全绿 6115 passed + 2 skipped(覆盖 99%)。生产 16585/26586 全程零触碰(只读识别留痕)。
> 基线时间: 2026-11-14 05:59-06:30(实验墙钟 1877s)
> 基线 commit: 7f93de58
**Refs:** memory-bank/plans/26-11-13-0448-plan-relocate-form-aware-gates.html · memory-bank/reports/26-11-13-0617-report-relocate-form-aware-gates.html(T1 改码前基线, 本片逐项翻转对照) · memory-bank/testing/real-baselines/26-11-10-0435-real-relocate-rlfn-e2e.md(构造方法先例), memory-bank/testing/baselines/26-11-14-0637-relocate-form-gates-p4.md

## 01 验收数字

实验 harness `tests-real/.work/relocate-form-gates/run_exp_p4.py`(gitignored, .work 面; 判定账 exp_state_p4.json,
证据树 evidence-p4/ 共 86 件)。五组拓扑独立(G1/G2/G4/G5 FILE_LINKS + G3 DIR_ALIAS + nsf 独立根), 三次离线窗
(G1+G4 同窗 / G2 / G5)。全链墙钟 1877s(t0=05:58:58, exp_state_p4.json)。命令面:

```text
commands run real.env / real.guard / real.up -- --port 36595(x3 次: 开工 + 窗1/窗2/窗3 后重启)
commands run real.down -- --port 36595(x3 次: 窗1/窗2/窗3 开窗前优雅退出, 各约 1.6-1.7s)
commands run real.seed.list -- --port 36595   # 收尾: 共 0 个种子, 自造 0 个
python run_exp_p4.py <phase>                  # 22 相位(21 + reinject 重做相位): setup/g1seeds/g1out/e1/
                                              #         e3a/e4/e2add/g4seeds/reinject/e7/window/chain/
                                              #         g2seeds/g2shrink/window2/g2chain/g3/g5seeds/
                                              #         g5e9/window3/g5chain/cleanup
commands run test.full                        # 6115 passed, 2 skipped in 190.34s; TOTAL 27279/68/9580/73 99%
```

E 逐项判定(E -> 判定行): E1=E1-1+E1-2 / E2=E2-add+E2-gate+E2-chain / E3=E3a+E3b-1+E3b-2 / E4=E4 / E5=E5-1+E5-daemon
+E5-note+E5-2 / E6=E6-1+E6-2+E6-2b+E6-3 / E7=E7a+E7b / E8=E8-d16+E8-chain+E8-recover / E9=E9a+E9b+E9c —— 全 PASS, 0 FAIL。

## 02 环境指纹

| 项 | 值 |
|---|---|
| 环境/实例 | 环境1(D盘机); 主 36595 = D:\Programs\qBittorrent-testing(pid 37116 -> 三次重启轮换), 副 36596 全程下线(开窗判据) |
| qB 版本/连接态 | v5.2.3(与生产同版本) · firewalled |
| 真实种子 | 开工 0 个 / 收尾 0 个(real.seed.list 复核, 实例整库 0 种子) |
| 生产实例 | 16585(pid 17680)/26586(pid 6560) 常驻在跑, 全程零请求零触碰(netstat 只读识别留痕) |
| 拓扑 | 五组: G1 rfg-p4g1/G2 rfg-p4g2/G4 rfg-p4g4/G5 rfg-p4g5(R: -> .work 各 dst, 异盘 file_links) + G3 rfg-p4dir(2 成员 x 8 文件 >= 阈值 8 -> dir_alias junction) + rfg-p4nsf(NoSubfolder 独立根) |
| job 账 | G1 jr-f9b88f0d79e9 / G4 jr-4e7c1be6893d / G2 jr-de9df5d33db3 / G3 jr-c573bf1fdcbd / G5 jr-f36bd76ba437 —— 全部收敛 done(finalized), 别名删除 |
| 产品进程 | tests-real 派生配置(WEB :39000, relocate.enabled, bt_backup 查表); daemon 旁路 = 产品 docstring 自留测试接缝(_spawn_daemon)+ wrapper 实例级名册(授权先例 2026-11-10) |
| E8 注入 | 进程内 TorrentRecord.files 对注入 hash 4662304a 前缀 raise(修后定稿形态: raise 落在两个门级消费方 _file_map/_relocate_file_names 各自 try/except 之内, 产品「清单不可得->保守」分支原码消费) |

## 03 逐条断言与实测结果(修前 vs 修后对照)

job 口径: 成员=组账 2 颗(异 piece_len 异 infohash), 组外异名=落旧根真实文件种子, 同名跨种=同文件异 piece_len。

| E | 断言(修后期望) | 三态 | 实测(证据 evidence-p4/) |
|---|---|---|---|
| E1(1) | 旧根异名添加预检: T1 confirm(文件级文案) -> **ok 零弹窗零 reasons** | **PASS** | cls=ok, actual_path=None(p4_e1_precheck_add.json) —— 误拦(1)消失(R1 分支(3)) |
| E1(2) | 组外异名带文件删除: T1 D16 拒 -> **status=ok 当场成功** | **PASS** | status=ok, 种子与真实文件清干净(p4_e1_delete_ok.json) —— 误拦(2)消失(R3 交集不相交放行) |
| E2 | 异名添加全链: 预检 ok -> qB 直加做种 -> 重启改写核验 -> 删链门(交集豁免) -> done; 新种子照常做种账面 1.00 零 recheck 零拒载 | **PASS** | 三段全过: E2-add(9ea9b559 做种态落旧根, 组隔离) -> E2-gate(删链门依赖计数=1 而 B 在场) -> E2-chain(stalledUP progress=1.00, p4_e2_final.json) |
| E3 | 同名仍拦(R1 分支(1) 新文案)+ 真依赖实证: confirm 后删链门计依赖(别名保留), 删账面 -> 依赖清零 -> 收尾恢复 | **PASS** | confirm 文案含「与成员别名链接同名/经链接共享同一份物理数据」; 清单 x alias_paths _norm 全等 1/1; chain_deps=1(0ba56656)别名保留 -> 删账面 -> done(finalized)+别名删除(p4_e3a_samename.json/p4_e3b_*.json) |
| E4 | armed 态组外异名带文件删除放行: 当场成功/文件清干净/别名与成员无损 | **PASS** | status=ok, islink=True 别名在位, 成员 x2 做种无损, job 仍 armed(p4_e4_delete_ok.json) |
| E5 | 成员收缩收敛: 仅删 M1 账面 -> N=3 拍收缩(members_gone+WARNING+反馈面 note); 删光 -> 空集核验 -> 删链门 -> done; daemon 对缺失 fastresume 跳过不失败 | **PASS** | M1(22967f63) 删除后约 5.2s 收缩(=3 个 2S 判定拍); WARNING「组账收缩 1 个」; 持久 note(mover 收缩后余成员在 src, reason=members_gone 稳定 + finalize_face note 透传, p4_e5_members_gone_note.json); journal M1=member_gone(settled 不计失败)/M2=already(p4_e5_member_gone.json, 改写账快照); 下线窗后 journal 相位翻 rewritten 见 exp_state_p4.json results 账 E5-daemon detail 与 timeline window2 条目(现值含 rewritten); 空集 -> done(finalized)+别名删除(p4_e5_finalized.json) |
| E6 | 目录级回归: ==src confirm 不松动(等值面文案+actual 镜像根)/scope 内深层新弹窗(覆盖洞闭合)/scope 外兄弟静默 ok/D16 全量拦原样 | **PASS** | 四断言全过: E6-1(actual=dst/dexp 镜像根) / E6-2(cls=confirm, actual=dst/dexp/deeper/deepseed 真实落点, 文案「经别名落到」; T1 此位 cls=ok) / E6-2b(cls=ok) / E6-3(status=error 前缀面拦)(p4_e6_*.json) |
| E7 | 取数核验(修后复跑): files API/_file_map 对 FILE_LINKS 与 NoSubfolder 与磁盘一致, 交集判定正确 | **PASS** | 成员 1MB x2 三方全等; 交集: 成员 True/组外异名 B False/同名跨种 True; NoSubfolder 名单无根前缀与磁盘平铺一致(p4_e7a_file_map.json/p4_e7b_nosubfolder.json) |
| E8 | 不可判定保守回归: 注入清单取数失败 -> 删链门计依赖 + D16 照旧拦 | **PASS** | D16: status=error(R5 分型组外文案, 非注入异常透传), 种子/数据原样(p4_e8_d16_blocked.json); 删链门: chain_deps=1(4662304a 计入, 文件级措辞), 删账面 -> 依赖清零 -> done+别名删除(p4_e8_chain_deps.json/p4_e8_recovered.json) |
| E9 | 自愈全链(R6 三断言, 生产等价态): armed+组外异名已落旧根+qB 不重启 -> (1)带文件删除当场成功 (2)新添加异名静默 ok (3)重启 -> 改写 -> 核验 -> 删链门豁免 -> 别名删除 -> done 零人工清理 | **PASS** | E9a(e0aee4b5 status=ok, 别名成员无损) / E9b(f1695db7 预检 cls=ok, 做种落旧根) / E9c(零 recheck, F 交集豁免零依赖, done(finalized), 全程对组外零产品动作, p4_e9c_zero_touch_done.json) |

## 04 过程记录与取证

- **产品 src/ 零 diff**: 本轮只读运行产品(R1-R5 本体 = ba098a33..7f93de58 五笔, 本轮真机验证其行为); 实验面
  `tests-real/.work/relocate-form-gates/`(gitignored): run_exp_p4.py + exp_state_p4.json + evidence-p4/(86 件,
  含 p4_* 证据 53 件(E 判定件、同名/注入/nsf/深层种子 .bytes 原件、journal/日志摘录) + p4g* 组级产物 32 件
  (p4g1 x10 + p4g2 x6 + p4g4 x7 + p4g5 x9: 各组 armed/job_account/receipt/outgroup 件 + 成员 .bytes/.torrent
  原件) + timeline.json = 86 件)。T1 产物(run_exp.py/evidence/ 42 件)未触碰。
- **harness 侧三处修正(非产品缺陷, 过程留痕)**: ①wait_until 两处 gone 条件谓词写反(相位重跑幂等修复);
  ②E8 注入首版 raise 打在门方法边界(产品 try/except 之外) -> D16 回执 error 为异常透传非保守拦 —— 注入点移进
  TorrentRecord.files(两门级消费方各自 catch 之内)后重做(p4_e8_d16_blocked.json attempt 2 + p4_reinject 相位);
  ③E5 首删的证据轮(last_removed)只存活一个同步轮(1.5s), 判定 tick(2S)消费时可能已被零变化轮覆盖 -> 计数不启动
  —— 与计划 §07「收缩误判」行披露的残余时机一致, 按该行明文出口(重新添加该种子恢复账面后再删)实现重试回路
  attempt_shrink(未成次留痕 p4_e5_m1_delete.json attempts; 收缩判定本体全程产品原码)。
- **G2 拓扑注记**: 余下成员为 mover 已在 dst 时, 收缩与核验同拍完成, reason=members_gone 为单拍瞬态 ——
  members_gone 持久反馈面 note 观察面由 G3 目录级 job 承载(mover 先收缩, 余成员在 src, at_dst=False 稳态,
  p4_e5_members_gone_note.json)。
- **范围外观察(只记录不顺手修)**: ①产品重启后首轮全量基线的 torrents_added 分批处理中, 单条种子 files 抛异常会
  中断该批后续归组(E8 注入副作用; 产品代码对归组批内单条有 try/except 的路径安全, _assign_new_torrent 路径无包裹
  —— 真实生产无此注入源, 仅注记); ②restart 后 mover 识别/pid 轮换为 qB 常态。
- **收尾核净**: 产品优雅退出(sentinel SIGTERM); qB 自造种子删净(tag real-fake 全扫, 连数据, qB 直连不经产品
  D16, p4_cleanup.json hashes_touched); 五组数据根与 case 目录清空; BT_backup before=1 after=1 零残留(queue 记账
  文件除外); real.seed.list 复核 0 种子; 双测试实例优雅退出(与开工态一致); 生产零触碰; 本轮未 commit/push(本地
  分支, 主会话统一提交)。
