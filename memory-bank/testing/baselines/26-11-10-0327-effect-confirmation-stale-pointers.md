# 5886 passed + 2 skipped —— issue 26-11-08-0043 坑档陈旧指针修复批全量绿

> 摘要: issue 26-11-08-0043 坑档陈旧指针修复批全量绿
> 基线时间: 2026-11-10 03:27

## 验收数字

```text
TOTAL                                                26198     45   9134     57    99%
5886 passed, 2 skipped in 142.82s (0:02:22)
```

(实测时点: HEAD eee97f5b + 本批工作树改动, `commands run test.full` 2026-11-10 04:37。本专题先后三次开工/评审前同步: 706e360c→5529b9f8(11 笔)得 5877 passed, 5529b9f8→391f133a(7 笔)得 5885 passed, 391f133a→eee97f5b(2 笔, 远端 `tests/test_qbmanager_loop.py` 新增守卫用例); 提交前在最终齐平组合树重跑一次, 以本组 5886 passed 为唯一基线, 前两组均不作基线)

## 本改动面

- **修 issue 26-11-08-0043(docs/便签)**: 只改 `memory-bank/pitfalls/backend/effect-confirmation.md` 范本区两处陈旧指针 —— ① `_verdict_reannounce` 链接 `[commands.py]` → `[commands_torrents.py]`, 补 `:30` 与取证时间、move-only 出处(计划 26-11-02-2342 §07 R5); ② 「真值直查红线」行文 `webui/runtime.py` → `[runtime_commands.py]` `:370` `_affected_truth`, 补红线原文 `:380-381` 与取证时间。其余描述(defer_receipt / flush_truths / check_pending / ops_mod 段)逐字未动; 产品代码、测试、配置零改动。
- **改道**: issue §03 建议的 `src/auto_qb/webui/server/routes/runtime_commands.py` 在当前树不存在; 复验 grep 实测红线在 `src/auto_qb/webui/runtime_commands.py:370`(`_affected_truth` docstring「直查 qB, 不读同步快照」), 故按当前代码树改指该路径。
- **issue 回写**: Open → In Progress → Done(徽标 + meta 两处), 补 §01 复验行与 §03「修复后补充」(实际修法 / 改道原因 / 验证方式 / 测试数字)。
- **机检**: `commands run kb.check` 全绿(主键 / 词表 / 认领链 / 回写守卫 / 日期守卫 / check_html 907 件, 2026-11-10 04:34 复测); issue HTML 标签平衡机检 BALANCED; 全库 `git grep` 验收目标坑档旧指针零残留(历史冻结件保留当时记载, 按 `pitfalls/docs/drift.md` 口径不改)。
- **真机**: 纯文档指针修正, 不涉 qB 真执行 / 真文件系统 / 进程 / 注册表 —— 真机不适用(纯静态可验)。
- **分批评审**: 首轮全能档 1 只读子代理 / 47 行 / 零发现(`[]`); 用户授权扩范围后整批 52 行(评审包基哈希 `4aac6ab2bce7`)重走复评轮与收口接缝终审, `commands run review.check` 的派发/发现计数见提交信息 `Review:` trailer; 记账类补写不改基哈希。
- **用户授权扩范围(2026-11-10 04:34)**: `memory-bank/pitfalls/backend/announce-epoch-semantics.md:12` 原写 `webui/commands.py::_verdict_reannounce`, 属同类陈旧指针; 用户显式说「一起修」(scope-guard 例外 3: 用户当场扩范围), 随本批改指 `[commands_torrents.py]` `:30` 并标取证时间与 move-only 出处(计划 26-11-02-2342 §07 R5)。既已修完不另建 Open issue; issue 报告 §03 范围守恒段与会话切片 R2 同步留痕。
