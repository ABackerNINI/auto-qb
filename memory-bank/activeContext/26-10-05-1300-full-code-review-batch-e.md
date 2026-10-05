# 全面 Code Review · 批 E 完成 (webui/ 全部 py: views / commands / runtime / server / routes)

> 摘要: 计划 [26-10-05-0951](../plans/26-10-05-0951-plan-full-code-review.html) 批 E 评审轮完成 (只读, 零改码), HEAD `a4d14a8d` 与起点同 commit。先读在途 [reannounce 计划 26-10-05-0923](../plans/26-10-05-0923-plan-reannounce-confirm-rework.html) §03 设计再读码, commands.py / runtime.py 只登记计划未覆盖增量并逐条标注关系。25 文件 / 5,296 行全部逐文件过目, 重点维度 R2 R8 R9 逐文件勾选; 坑档对照 backend concurrency / high-risk-ops / web-package-split + web-ui contract-api。发现 6 条 (**P2 ×1 + P3 ×5**): **E-01 (P2) store 迭代竞态** —— Web 线程无锁迭代 store.by_hash / groups (views.search_torrents:897 / _build_flat_view 等经 ensure_state 的 Web 侧重建路径 / fs.api_paths / hr.mark_local_present, 前三端点无脏门控每请求必迭代) 与主循环原地变更 (store.py:550 remove_torrent pop / :559 restore_torrent / grouping_mod:266 del groups[key]) 并发 → RuntimeError 500; apply_sync 主路径系整体替换安全, 危险面收窄到删除/跳检窗, 瞬时 500 自愈无数据破坏 · E-02 (P3) torrent_detail.api_speed_mode except-pass 静默吞并 + 部分成功组合未声明 (ruff S110/bandit B110 复核采纳) · E-03 (P3, reannounce 计划未覆盖) _cmd_reannounce_group 空组无回执 (deferred 命令 + `if hashes:` 无 else, 前端挂到 waitCmd 超时; 单发/bulk 同口径均有缺失回执) · E-04 (P3) _seed_view 的 magnet_uri 每轮轮询载荷 vs 坑档 contract-api 明文反例 + drawer 按需兜底两组注释口径互斥 · E-05 (P3) traffic_qb.v3cache 惰性建无锁 (B1-01 同族, 良性) · E-06 (P3) consume_commands 的 KeyError 误标「未知命令」(缺参 vs 未知命令未分离, 当前路由载荷齐全不可达, 备查)。复验不登记 10 项: 池 2218/2122/1408 复核现状无结构性缓解 (沿用不重开) · 池 2002 webui 半边定位为前端 config_editor/config_hub (归批 F1) · **池 0402 WEB 半边复核无绕闸旁路** (单发 403 gate + bulk 分派拒单双层, force 只豁 cls=force, 七防护在 ops 层原样) · R2 总结论 WEB 四类危险动作全过闸 · R8 总结论凭据面/输入校验面齐 (trackers 透传含 passkey 与 qB 同口径不登记)。工具源: ruff 1843 条采纳 1 (E-02), F 类 0 条为五批最干净; bandit 1 条 = E-02。test.full 2610+4 / 99% (164/138, 15511/5342) 与基线逐位持平。发现表落盘 [报告草稿批 E 章节](../reports/26-10-05-1036-report-full-code-review.html)。
>
> 最后活动: 2026-10-05 13:00

**Refs:** memory-bank/plans/26-10-05-0951-plan-full-code-review.html · memory-bank/plans/26-10-05-0923-plan-reannounce-confirm-rework.html · memory-bank/reports/26-10-05-1036-report-full-code-review.html · 前序切片 [批 A](26-10-05-1100-full-code-review-batch-a.md) · [批 B1](26-10-05-1130-full-code-review-batch-b1.md) · [批 B2](26-10-05-1135-full-code-review-batch-b2.md) · [批 C](26-10-05-1150-full-code-review-batch-c.md) · [批 D](26-10-05-1210-full-code-review-batch-d.md)

## 本轮完成

- sync 成功记 HEAD `a4d14a8d`; 五步动作序列走完 (读档 计划 §03/§06 + reannounce 计划 §03 全文 + 包 docstring → 坑档 backend 两主题 + web-ui contract-api → LOC 降序 25 件全过目 → ruff+bandit 逐条复核 → 登记去重)。
- 发现表 6 条回填报告草稿批 E 章节 (含逐文件勾选结论 25/25 / R2·R8 维度总结论 / 复验不登记项 10 项 / 工具源小结); E-01 的 store 变更点调用链 (qbapi.py:157 / ops.skip_check) 已实证; E-03/E-01 逐条标注 reannounce 计划「未覆盖」, 其余标注「无交叠」。
- 报告脚注批次进度更新为 E✓ (6 条: P2 ×1 / P3 ×5)。
- test.full: 2610 passed + 4 skipped / 99% (15511/5342, 164/138) 与基线切片逐位持平, 无漂移。

## 遗留 / 待办

- **E-01 (P2) 建议入池**: 修复方向二选一 (store 原地变更点延迟到 apply_sync 统一应用 / Web 侧迭代取快照引用), 可补「删除期间并发 /api/search 不 500」守阵; 与 reannounce 计划无冲突。
- E-03 建议并入 reannounce 计划 S1 实施备注 (空组在 item 级聚合下的回执形状)。
- E-04 随池 2218 载荷瘦身一并处置或更新坑档 contract-api 的 magnet_uri 例外口径。
- 剩余批次: F1 (commands.js 标「落地后复验」) / F2 / G (0402 规则侧主面) / H。
