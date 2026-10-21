# 3988 passed + 10 skipped —— Esc 收起展开态后键盘光标归位(辅种/追剧页)全量基线

> 摘要: Esc 收起展开态后键盘光标归位(辅种/追剧页)全量基线
> 基线时间: 2026-10-22 02:27

**Refs:** memory-bank/tasks/26-10-22-webui-kbd-esc-collapse-cursor.md

## 验收数字

`commands run test.full` 实测(裸数字只写本切片这一处):

- 汇总行: **3988 passed, 10 skipped in 35.64s**
- 覆盖率: TOTAL **99%**(20728 stmts / 7088 branch)

逐条口径注记:

- 本轮改动面在 test.full 内全绿, 新增守阵 `test_esc_collapse_returns_cursor_to_parent` 红验通过(把三档归位任一处改回"只复位展开态"即红)
- 浏览器侧另跑 `commands run dev.e2e` 全量 **340 passed / 10 skipped / 0 failed in 11.8m** —— e2e 不在 test.full 内, 单列在此
- 基线测在「已含本次代码改动、尚未提交」的工作树上

## 本改动面

- `src/auto_qb/webui/static/shared/lifecycle.js` —— Esc 退栈链三档收起分支由「只复位展开态」改为「复位 + 把 `kbCursor` 退回被收起的父行」: `expandedKey`→`{kind:"group"}` / `expandedShowEp`→`{kind:"ep"}` / `expandedShows`→`{kind:"show"}`(多支展开优先光标所在那一支, 走 `_kbParseEpId`); 就地赋值不调 `_kbCollapseRow`
- `e2e/kbd-members.spec.mjs` —— 新增两条 @fast 用例(辅种页 Esc 退回组行 / 追剧页两次 Esc 逐层退回集行·剧行), 头注覆盖清单 5/6 同步
- `tests/test_web_shortcuts.py` —— 新增守阵 `test_esc_collapse_returns_cursor_to_parent`, 文件头「## 测试计划」清单同步
- `memory-bank/pitfalls/web-ui/kbd-cursor-collapse-dangling.md` —— 新坑档(收起展开态 → 光标悬空链外; 复发 1, 记为什么没命中)
