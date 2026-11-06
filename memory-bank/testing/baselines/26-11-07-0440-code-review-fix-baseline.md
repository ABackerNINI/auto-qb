# 5597 —— 收口评审修复轮 8 发现全量基线(99.90% 达闸)

> 摘要: 收口评审修复轮 8 发现全量基线(99.90% 达闸)
> 基线时间: 2026-11-07 04:40

## 验收数字

- 汇总行: **5597 passed + 2 skipped** in 139.12s(0:02:19, TMPDIR 由 tests/_tmp_bootstrap.py 自举)。
- 覆盖率 TOTAL 表末行: **TOTAL 25497 stmts / 5 miss / 8794 branch / 27 partial / 99%**,Required 99.5% reached, Total coverage: 99.90%。
- 缺口净额: 本片缺口单位(miss + partial)= 5 + 27 = **32**,上基线(26-11-07-0322)为 5 + 27 = 32 ⇒ 净额 **0**; 分母 34232 → 34291(修复新增语句 +37 / 分支 +22), 残留缺口集合与上基线完全相同(fastresume 尾闸 298 + 296->295 / relocate_exec 445 + 427->424 + 736->739), 修复轮新增代码零残留(test.full term-missing 逐文件核对)。
- 口径注记: 8 条评审发现(blocker 1 / major 2 / minor 3 / nit 2)逐条修复 + 配套测试, 6 个测试文件净增 8 用例(5589 → 5597); 中途 1 flaky(test_hr_discovery 端口 bind, 并行竞争形态, 与本轮改动面无关)单跑复核通过; test.quick 复跑全绿。数字为本轮实测誊写, 差值对比 `commands run kb.baseline -n 2`。

## 本改动面

- `src/auto_qb/core/fastresume.py`(评审 #1, blocker): `rewrite_save_paths` already 判定改为「先算旧根命中与改写产物」—— 嵌套 new⊂old(目标=源祖先)时旧根命中优先, 产物 != 原值必改写(旧实现新根前缀命中先判 already, 旧根键值永不改写, journal 永久悬挂违 D10); 嵌套 old⊂new(值已在新根内)仍 already, 幂等不破。
- `src/auto_qb/infra/alias_fs.py`(评审 #2, major): `retarget_alias` 建链段 hardlink 形态 + 新链接位置与新目标跨卷(st_dev 判定, 探新链接父目录)时回落 KIND_SYMLINK(宁降级不进 os.link EXDEV 死循环; 卷位判不了保守回落; 回落失败抛错走 D20); docstring 同步。
- `src/auto_qb/core/modules/relocate_exec.py`(评审 #2/#3): `_start_job` GATE_ALIAS_BUSY 段新增「前任别名形态 x 新目标卷位」预检(hardlink 形态 + 非同卷 + 文件 symlink 能力不可用 ⇒ 搬前整体拒绝零副作用); `relocate_cancel` 成本确认前新增 settled 改写检查(journal.rewrites 有 REWRITE_SETTLED 记录 ⇒ 拒绝撤销 gate=cancel_rewritten, 防 0420 同款冻结态)。
- `src/auto_qb/tools/recycle_daemon.py`(评审 #4/#6): `_process_window` 逐成员现读 spec(read_spec 失败本 job 本拍放弃, 不拿窗口 scan 快照改写 —— supersede 账面段窗口内改道即时生效); `_proc_absent` 进程证与端口证改双判合取(名册见 qB + 端口拒连不判缺席 —— WebUI 不可达 != 进程不在, N1 铁律; 名册不可用退端口单证 + WARNING 降级说明; 无端口退名册单证)。注意: 旧「端点拒连即实例级缺席」短路判据随本修退役, 多实例同机时收尾窗需等全部 qB 进程退场(任务拍板口径)。
- `src/auto_qb/core/qbapi.py`(评审 #5): `_relocate_delete_blocked` 对 tag 含 TAG_PROBE 的探测种子放行(自造探针非组成员数据, 拦截会让探测清理 deleteFiles 恒失败)。
- `tests/test_core_fastresume.py` +1: 嵌套反向(new 是 old 真前缀)旧根键值必改写 / 新根下旧根外 already / 产物重跑幂等。
- `tests/test_alias_fs.py` +1(评审 #8 同文件): hardlink 跨卷回落 symlink(False/None 两注入 + 同卷对照)/ 恒真断言删除(`not islink or kind` 行)。
- `tests/test_relocate_supersede.py` +2: 形态 x 卷位预检拦截与 symlink 放行两支(4 假链接触发截断文案 + junction 形态前任 continue 支)/ settled 改写拒绝撤销(cost_confirmed 双态 + 非 dict 残账守卫 + reset 后放行)。
- `tests/test_recycle_daemon.py` +3(评审 #7 同文件): 窗口中段 spec 改道剩余成员写新 dst / spec 现读失败放弃本 job / `_proc_absent` 双判合取与名册降级告警矩阵; 恒真断言(`X or True`)换真断言; `_stub_qb` 与两处名册桩改 state 联动(合取语义下单实例机器模型)。
- `tests/test_relocate_paths.py`(零净增用例): `test_daemon_three_proofs_helpers` 按合取新契约改断言(名册见 qB + 端口拒连 ⇒ 不进窗)。
- `tests/test_relocate_exec_verify.py` +1: 探测种子放行 / 普通种子同根仍拦 / 混批拦截只点名普通种子。
