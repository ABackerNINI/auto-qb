# 危险操作独立操作层 · 已实施 (P1+P2' 落地, 未提交)

> 摘要: 用户指令「实施计划」—— §06 四决策点按建议拍板(D1 采纳 / D2 不做 / D3 接受现状 / D4 仅抽 recheck+skip_check), P1+P2' 一轮落地。ops 层 = `core/mixins/ops.py`(474 行 OpsMixin: ops_recheck/ops_skip_check, R1 提交点检查 + R2 实时复核 + 保护按 source 区分); full_checking.py 留 1.5/1.6 闸门与常量 helper(178 行), skip_checking.py 剩一行委托(28 行); WEB recheck 单发+bulk 第二入口经 ops 提交(handler 自写回执, 入 DEFERRED_RECEIPT), 右键跳检(POST /api/torrents/{hash}/skip-check + 前端确认框)落地; webui 不 import rules 静态守阵 test_webui_no_rules_import。**导入防环决策**: 常量/冷却 helper 单点留 full_checking.py, ops 反向 import 它(反向即成环)。提交时合并远端 87d154c7(键盘快捷键+HR 触发语义, stash→sync→pop 交集 4 文件); 合并后基线 **1829 passed + 3 skipped / 91%**(test.full 24.82s)。计划 doc 已置 Done; 档案 [tasks/26-09-30-rule-dangerous-op-layer.md](../tasks/26-09-30-rule-dangerous-op-layer.md); 基线 [testing/baselines/26-09-30-1210-dangerous-ops-layer.md](../testing/baselines/26-09-30-1210-dangerous-ops-layer.md)。
> 最后活动: 2026-09-30 12:40

## 正在进行

- 无 —— 已按「提交」指令走 ship.commit(合并远端 → 闸门 → 提交 → 推 Gitee)。

## 下一步（候选, 未拍板）

- 用户验收后提交(建议提交信息: ✨ 危险操作独立操作层: ops 抽取 + R1/R2 + 右键跳检)。
- 未来第三来源(HR 联动 / 外部 API)接入时按 §3.8 红线扩 ops(新增 source 调 ops, 不开旁路); C3/C4 实证冲击后分别立专项(材料在计划 §06 D3)。
