# 2848 —— 辅种/追剧页成员行 ← 收起所属单元(光标进组后可收起分组)

> 摘要: 修「收起当前行快捷键无法在键盘光标进入分组后收起分组」的收尾基线。`_kbCollapseRow` 原只按 kind 分派 group/show/ep, 成员行(kind=torrent)落空 ⇒ 光标按 ↓ 进展开组/展开集后 ← 静默无反应。修法 = 成员行分支收起**所属单元**并把光标带回其行, 父行解析单点 `_kbParentRow`(复用 `selection.js::_memberRangeList`, 与渲染同源); 新增静态守阵 + `e2e/kbd-members.spec.mjs` 增 2 条 @fast。
> 基线时间: 2026-10-09 13:47

**Refs:** memory-bank/activeContext/26-10-09-1347-webui-kbd-collapse-parent.md

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2848 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**(16567 语句 / 169 未覆盖 / 5716 分支 / 145 partial; 门槛 98% 达标)
- **耗时**: 46.27s(墙时 48.4s)
- **新增测试**: 1 个静态守阵函数(`test_kb_collapse_parent_row`, 挂在 `tests/test_web_shortcuts.py`, 并登记进该文件头部「测试计划」)。
- **e2e**: `e2e/kbd-members.spec.mjs` 增 2 条 @fast(辅种页分组 / 追剧页集), 双皮肤 ⇒ 新增 4 条、该规格全 8 条绿 —— 真浏览器钉住"光标进成员行后 ← 收起所属单元并回父行"。红验: 把 `_kbCollapseRow` 的成员行分支短路(`if (c.kind !== "torrent") return;` → `return;`)时, 静态守阵 1 红 + 新增 4 条 e2e 全红(已还原)。
