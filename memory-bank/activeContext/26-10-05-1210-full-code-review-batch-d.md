# 全面 Code Review · 批 D 完成 (config/ 全部: loaders / models / writer / schema / validation)

> 摘要: 计划 [26-10-05-0951](../plans/26-10-05-0951-plan-full-code-review.html) 批 D 评审轮完成 (只读, 零改码), HEAD `a4d14a8d` 与起点同 commit。19 文件 / 4,966 行全部逐文件过目, 重点维度 R2 R4 逐文件勾选; 读档 config-reference/loading-and-write.md + 坑档 schema-stamp-writeback / hot-reload-held-config / hot-reload-stale-bindings-derived-views。发现 7 条 (**P1 ×1 + P2 ×1 + P3 ×5**): **D-01 (P1, 实测复现) `load_grouping_config` 漏读 `cross_group_conflict_check`** —— 键在 models/schema/校验/键面基线/keys.md 五处齐备、grouping_mod 消费方在, 唯 loader 不取值, YAML 显式 `true` 解析恒 False, 跨组交叉检查经配置永无法启用 (计划 26-10-04-0107 S1「全链贯通」清单缺 loaders; 三道守卫全探不到该缺口: 键面守卫只查键存在 / test_config_schema 只测 validate / test_grouping 直设属性绕 loader) · D-02 (P2, 实测复现) checking 动作 with_reference/without_reference 子段键面无 fail-fast —— `_validate_checking_action_spec` 只查 mode, `enabeld`/`autostart` 拼写错静默走默认 (enabled 拼错 = 分支静默不启用; CheckAction 注释自称校验层保证, 与实际不符; 池 2002 嵌套变体) · D-03 (P3) writer._backup "w" 直写非原子, 与 backup_versioned 的 atomic_write 不一致 · D-04 (P3 备查) _resolve_hr_site_bindings 四处静默 continue = 校验后散落防御唯一实例 · D-05 (P3) v1→v2/v2→v3 迁移无 per-key notes (v3→v4 有先例) + `enabled: ""` 在 load/materialize 两路径语义分歧 · D-06 (P3) 重导出面 F401 ×4 + RUF068 · D-07 (P3) load_tracker_config 冗余构造。复验不登记 7 项 (池 2002 config 半边复核已被未知键全量拒绝 + 键集合互检结构性覆盖 / match_trackers 短伪域 / _validate_fs 父子都拦系设计 / unmask 哨兵保持 / RUF013/UP 系注解债 / 全角标点 / 退化 *_rules 段名)。R2 结论: 配置侧闸门完备 (跳检/免验/采样/HR 全默认关); R4 结论: 热重载校验面与冷启动同路径等价, 唯 D-05 迁移序差。工具源: ruff 193 条采纳 5 (归 D-06); bandit 2 条 B506 均误报 (BaseLoader)。守阵存活: 键面/schema/writer/impact 160 用例局部跑全绿。test.full 2610+4 / 99% (164/138, 15511/5342) 与基线逐位持平。发现表落盘 [报告草稿批 D 章节](../reports/26-10-05-1036-report-full-code-review.html)。
>
> 最后活动: 2026-10-05 12:10

**Refs:** memory-bank/plans/26-10-05-0951-plan-full-code-review.html · memory-bank/reports/26-10-05-1036-report-full-code-review.html · memory-bank/tasks/26-10-04-backend-cross-group-conflict.md · 前序切片 [批 A](26-10-05-1100-full-code-review-batch-a.md) · [批 B1](26-10-05-1130-full-code-review-batch-b1.md) · [批 B2](26-10-05-1135-full-code-review-batch-b2.md) · [批 C](26-10-05-1150-full-code-review-batch-c.md)

## 本轮完成

- sync 成功记 HEAD `a4d14a8d`; 五步动作序列走完 (读档 config-reference + 包 docstring → 坑档 backend 三主题 → LOC 降序 19 件全过目 → ruff+bandit 逐条复核 → 登记去重)。
- 发现表 7 条回填报告草稿批 D 章节 (含逐文件勾选结论 19/19 / R2·R4 维度结论 / 复验不登记项 / 工具源小结); D-01/D-02 以临时配置实测复现后登记 (临时件已清理, 未触仓库文件)。
- test.full: 2610 passed + 4 skipped / 99% (15511/5342, 164/138) 与基线切片逐位持平, 无漂移。

## 遗留 / 待办

- **D-01 (P1) 建议最先入池**: 一行补漏 (load_grouping_config 加第四键 parse_bool) + 回读守阵; 顺带在键面守卫域加「loader 消费核对」防同形态复发。D-02 (P2) 修复时顺带核其它 object 型插件 spec 子段 (add_category/freespace/move_to) 同形态。
- D-05 的 migration notes 补齐与池 2002 合流排期 (issue 清理路线图 26-10-01-1758)。
- 剩余批次: E (webui, 先读 reannounce 计划) / F1 / F2 / G / H。
