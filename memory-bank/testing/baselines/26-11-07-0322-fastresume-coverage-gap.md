# 5589 —— S1-S5 覆盖率缺口清偿全量基线(99.91% 达 M8 阈值)

> 摘要: S1-S5 覆盖率缺口清偿全量基线(99.91% 达 M8 阈值)
> 基线时间: 2026-11-07 03:22

## 验收数字

- 汇总行: **5589 passed + 2 skipped** in 177.06s(0:02:57, TMPDIR 由 tests/_tmp_bootstrap.py 自举)。
- 覆盖率 TOTAL 表末行: **TOTAL 25460 stmts / 5 miss / 8772 branch / 27 partial / 99%**,Required 99.5% reached, Total coverage: 99.91%。
- 缺口净额: 本片缺口单位(miss + partial)= 5 + 27 = **32**,上基线(26-11-06-0446)为 57 + 36 = 93 ⇒ 净额 **−61**(全负, 无点名); 分母 32934 → 34232(S1-S5 新代码入库, 语句 24538 → 25460)。
- 残留 5 miss 均为不可达防御支(fastresume 286 尾闸 / relocate_exec 445 终态过滤已由 active_jobs 承担 / relocate_units 483 与 1151 `_norm` 恒非空 / runtime_views 546 映射残值防御), 非遗漏。
- 口径注记: 相对上基线(26-11-06-0446, 5465)净增 124 = 本轮 +45 覆盖率缺口清偿用例 + S1-S5 期间其它用例增量; 全绿, 副作用越界 0。首跑曾 1 flaky(test_hr_discovery 端口 bind, 并行竞争形态)单跑复核通过后重跑全量全绿。
- 差值对比: `commands run kb.baseline -n 2`。

## 本改动面

- 覆盖率缺口清偿(99.31% → 99.91%, 只加测试不改实现), 15 个测试文件 +45 用例, 全部头部 docstring「## 测试计划」同步:
  - `tests/test_core_fastresume.py` +5: 兜底扫描坏 torrent 跳过 / 旧根无分隔符变体去重 / 目录 fsync 双路 / replace 失败清临时文件 / 往返自校验三道闸;
  - `tests/test_relocate_probe.py` +14: `_bencode` 类型闸 / api 不可用 / 可见性与读证轮询期 API 异常 / 无 hash 条目跳过 / setLocation 拒 / 仅复制不搬走 mismatch / `_file_matches` OSError / `_cleanup` 无 hash 矩阵与消失轮询炸与 rmtree 残留 / sweep 列种子炸与删除失败与目录清理失败;
  - `tests/test_alias_fs.py` +11: inspect_path junction / alias_points_to stat 炸与 readlink 不可读 / 占用探测 POSIX 与 isdir 炸与不可分类错误 / 无链接无 kind 推断 / 空真目录占位 / 形态不支持 ValueError / 穿透校验失败三支;
  - `tests/test_relocate_supersede.py` +5: supersede stage 拍重试 / journal 拒记与不在声明源别名 / `_rel_under` 三支 / D19 幂等重放 / 链式孪生建链跳过;
  - `tests/test_relocate_exec_verify.py` +3: 悬挂同参重放 DEBUG / qB 侧自检异常跳过 / 批量删除拦截与无 cmd_id 回执;
  - `tests/test_relocate_exec_reconcile.py` +3: daemon 拉起失败告警与退避 / penetrate 无别名直进武装 / relocate 段缺席标签名空;
  - `tests/test_recycle_daemon.py` +7: journal 终态闸 / `_alive` POSIX 支 / verify_replays 坏形 / reset 终态拒与非 settled 保留 / tasklist 非引号行 / /proc 容错 / 非 Windows 分派;
  - `tests/test_relocate_units.py` +2 / `tests/test_relocate_plan.py`(经 gates 文件)+3: evaluate_add 第二段环终态跳过与目录别名改道 / 源侧三态孪生异常 / 自有别名硬链接悬空容错 / bt_backup 非字典;
  - `tests/test_relocate_proof.py` +2: 客户端缺位 B′ 降级 / 上溯深度耗尽;
  - `tests/test_webui_relocate_chain.py` +3: pick_job_for 无命中 / 远端候选短路 / finalize 端口坏形回落 0;
  - `tests/test_hr_report_once.py` +1(全站型无可走查)/ `tests/test_hr_runtime_feeder.py` +2(取数拒绝两文案)/ `tests/test_hr_server.py` +1(线程句柄已在跑)/ `tests/test_tray.py` +2(IPC close 容错 / run_tray 正常返回)。
