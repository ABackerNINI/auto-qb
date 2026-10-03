# 认领链守卫报错自解释 — issue 26-10-03-0746 修复置 Done

> 摘要: 认领修复 gen_doc_map refs 视觉分隔符假红 issue, 采用建议①(报错自带格式说明), 解析行为不动。
> 最后活动: 2026-10-03 08:41

## 已完成 (2026-10-03)

- **修复**: `gen_doc_map.check_claim_chain` 报「目标不存在」时, ref 命中视觉分隔符(新增 `VISUAL_SEP_RE`: `· 、 ; ； | ｜`)追加提示「多目标须英文逗号分隔, 整串被当成了单一路径」; `--check` 头行报错补「refs 多目标一律英文逗号分隔」。建议②(放宽解析)未采用 —— 协议单点 doc-forms.md「认领链」本已写明逗号, 报错自解释即可, 约定不放宽。
- **守阵**: `tests/test_docs_forms.py::test_claim_chain_missing_target_hints_separator`(分隔符 case 报错含提示 + 普通断链 case 不误报), 文件头测试计划同步登记。
- **回写**: issue 置 Done(封面徽标 + meta + 状态日志: 复验锚点 3/3 + 实测复现 + 修法/验证/数字), issues/_index.md 重生成。
- 收尾: 基线切片 [baselines/26-10-03-0841](../testing/baselines/26-10-03-0841-kb-docmap-refs-separator-done.md)(2326 passed + 3 skipped / 99% @ 5c983431, dd180a11 实测后合流远端 4 提交复测数字不变); 不满足立档阈值(0 个 src 源文件改动、单轮); 无新坑(坑本身已立 issue, 报错自解释后不复犯)。

## 状态

任务完结, 本轮随 ship.commit 入库(用户已授权提交; 同步 @ 5c983431)。
