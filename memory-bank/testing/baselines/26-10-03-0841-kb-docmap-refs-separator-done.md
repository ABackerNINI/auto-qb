# 基线 · 2326 passed + 3 skipped / 99% —— 认领链守卫报错自解释修复轮(issue 26-10-03-0746)

> 摘要: 单 issue 修复轮: `gen_doc_map.check_claim_chain` 报「目标不存在」时, ref 命中视觉分隔符
> (`· 、 ; ； | ｜`, 新增 `VISUAL_SEP_RE`)即追加「多目标须英文逗号分隔, 整串被当成了单一路径」提示;
> `--check` 头行补「refs 多目标一律英文逗号分隔」。解析行为不动(仍只认英文逗号), 建议修法②(放宽解析)未采用。
> 新增守阵 `test_claim_chain_missing_target_hints_separator`(test_docs_forms.py, 11 passed)。
> 基线时间: 2026-10-03 08:41, develop @ 5c983431(dd180a11 上实测, 合流远端 4 提交复测, 数字不变; 工作区含本轮回写件 —— 纯文档与 skill 脚本, 不影响数字)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。

TOTAL **2326 passed + 3 skipped / 99%**(13,433 语句 / 88 未覆盖 / 4,542 分支 / 89 partial,
test.full 31.2s, rc=0)。
相对上一切片(26-10-03-0733: 2325 passed + 3 skipped / 99%, 13,433 语句 / 4,542 分支, @ c91be940)
**passed +1** —— 即本轮新增的分隔符提示守阵; 语句 / 分支零增长(纯报错文本与提示分支, 无新逻辑路径)。
区间 dd180a11 → 5c983431 合流的远端 4 提交(站点页阶段 3 + 抽屉调研报告 2 件 + qB 流量图可行性报告)均为文档/前端件, 未带净增用例, 复测数字与 dd180a11 一致。
