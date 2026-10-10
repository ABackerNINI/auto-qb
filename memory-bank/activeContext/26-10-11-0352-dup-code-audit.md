# 全仓重复代码审查 · 轮 17–19(rules / infra / torrents+tray+entry)

> 摘要: 用户「做 Phase 1, 17-19部分」→ 按计划 `26-10-10-2333` 执行 **Phase 1 后端余下三包 = 轮 17 rules/ + 轮 18 infra/ + 轮 19 torrents/+tray/+entry**(~6.1k 行 · 36 文件)。**纯审查轮, 零源码改动**: 滚动报告 `26-10-11-0033` 追加 §20–§22 + 累计计数/候选排序 §23 + issue 表 §24; 三包 34 项发现(A11/B5/C9/D9), 全局累计 156(A58/B15/C40/D43); 入池 **11 条 refactor issue**(专题 `dup-code-audit`, 均 Open 未认领)。**Phase 1 后端(config+core+hr+webui+rules+infra+torrents)全部走完**。S2 提名实测: pylint R0801(=6) 仅 `torrents/compat`↔`torrents/view` 字段列表 2 组(= R19-C01), rules/infra 0 命中; jscpd python 0 clone。
> 最后活动: 2026-10-11 03:52

**Refs:** memory-bank/tasks/26-10-10-backend-dup-code-audit.md

## 正在进行

- **轮 17–19(rules / infra / torrents+tray+entry)已完成**(纯审查轮, 零源码改动)。滚动报告 [26-10-11-0033](../reports/26-10-11-0033-report-dup-code-audit.html) 已追加 R17/R18/R19(§20–§22)+ 累计计数/候选排序(§23)+ issue 表(§24)+ 变更记录(§25); 三包计数 A11/B5/C9/D9, 全局累计 156(A58/B15/C40/D43)。
- **11 条 refactor issue 已入池**(均 Open, 未认领): rules 3(`rules-expr-disk-helper-dup` / `rules-expr-numeric-predicate-dup` / `rules-parser-dead-op-constants-dup`); infra 5(`infra-fmt-ladder-dup` / `infra-win-dll-lazy-bind-dup` / `infra-utils-small-helper-dup` / `infra-platform-detect-bypass-dup` / `infra-url-decompose-dup`); torrents+tray 3(`torrents-snapshot-view-field-dup` / `torrents-hr-entry-guard-dup` / `notify-tray-icon-path-dup`)。
- **下一轮候选**: Phase 2 前端轮 20(shared/*.js 非抽屉); 或按用户偏好调整顺序。每轮开工另立会话, 按 S1–S6 走。

## 关键结论(供后续执行参考)

- **三包字面重复同样极低**: pylint R0801(=6) rules/infra 0 命中, torrents 仅 compat↔view 字段列表 2 组; jscpd python 0 clone。**infra 的重复以「小工具样板」与「单点被旁路」为主, torrents 以「同一批字段名双表」为主**。
- **A 类重灾(可提取, 收益中/风险低)**: ① `rules/expr` 盘用量取数四处逐字同(env `_freespace/_disk_total/_disk_used` + `FreespaceCondition.match`) R17-A01; ② `infra/utils` 格式化阶梯 `fmt_speed`↔`fmt_size` R18-A01; ③ `_win_user32`↔`_win_kernel32` 惰性绑定骨架 R18-A02; ④ `notify.ICON_ICO`↔`tray/app.ICON_ICO` 逐字同 R19-A01 —— 最干净的一处(表达式完全相同)。
- **C 类(同一事实多表示, 优先)**: ① **平台判定单点被旁路** `utils.is_windows/is_*` vs 裸 `sys.platform.startswith`(autostart 6 处 + tray/app.py:204) R18-C01/R19-C02(真实漂移点); ② **快照字段表 ↔ 视图字段表** 两处手工枚举同一批 qB 字段(view ⊆ snapshot) R19-C01(热路径脏判定, 漂移即静默不重建); ③ `sanitize_tracker_url`↔`mask_tracker_url` URL 分解口径 R18-C02; ④ `expr/env._STATE_ATTRS` = config `STATE_ATTRS` 第三份(R02-V05 续); ⑤ `versioning._num`↔hr `_as_int`(R12-M02 续)、`NotifyThrottle`↔`base._log_condition_error`↔hr(R14-T03 续)。
- **B 类(只登记, 不急合)**: no-HR 缺省语义两处(R17-B01) / AST 双类型检查(R17-B02) / `parse_*` 三族(R18-B01) / view 量化↔webui(与 R16-B01 同族, R19-B01) / 两处轮末基线刷新(R19-B02)。
- **D 类(明确不动)**: `ActionResult` 构造器族 / 插件注册单点 / `parse_compare` 调用点 / `logging._level_line_re` / `atomic_write` 单点 / `_exists_dir/_exists_file` 惯用式 / 包 `__init__` 重导出 / `_format_uptime` 单点 / cli argparse 互斥校验。
- **既有 issue 复核**: R02-V05(STATE_ATTRS 三份)、R12-M02(强转样板)、R14-T03(告警节流窗口)、R14-T04(URL 分解)、R16-C04(ETA 哨兵)、R16-B01(search 行精度) 在三包各找到对应「另一半」, 已引用不重复入池 —— 说明这些跨包问题确为真。

## 后续候选(未开工)

- Phase 2 前端(轮 20–23)、Phase 3 测试与横切(轮 24–25)、Phase 4 汇总(轮 26)。
- 轮 26 汇总: 重构候选排序表(报告 §23 已有雏形)+ 跨层「同一事实」总账 + 未入池候选(各弱候选 / B 类暂缓 / D 类)按清偿顺序决定。
