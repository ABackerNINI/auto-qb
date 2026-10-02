# 基线 · 2291 passed + 3 skipped / 99% —— 站点引用规则判重实施完结轮

> 摘要: rules_ref 判重三波次(W1 `dfcda6f9` 后端校验判重 / W2 `e854801e` WebUI 下拉防呆 / W3 `b30b5c07` 文案四处)全部落地后的收尾基线; W2 浏览器冒烟 8 项断言全过(Playwright + 配置副本 + 免 qB 装配, 含粘贴重复 → 保存 toast 报错端到端)。档案: [tasks/26-10-02-backend-rules-ref-duplicate-reject.md](../../tasks/26-10-02-backend-rules-ref-duplicate-reject.md)。
> 基线时间: 2026-10-02 17:34, develop @ 0d286cc5(收尾回写未提交工作树, test.full 实测)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。

TOTAL **2291 passed + 3 skipped / 99%**(13,259 语句 / 86 未覆盖 / 4,442 分支 / 81 partial,
test.full 39.4s, rc=0)。
相对上一切片(26-10-02-1705: 2290 passed + 3 skipped / 99%, @ f83a0db6)passed +1 来自
0d286cc5(ESC 兜底新增 test_esc_chain_clear_filters_fallback), 本 feat 三波次为扩展既有用例
(test_validate_rule_refs 四例 / test_tracker_rules_ref 去重回归锁)净增条目 0; 语句
13,251 → 13,259(+8)与分支 4,436 → 4,442(+6)来自 W1 的 validation/rules.py 判重分支(+16 行),
W2 前端 JS 与 W3 文案不触 Python 覆盖率统计。近期全量耗时采样 29.3-39.4s。
