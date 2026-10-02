# 基线 · 2314 passed + 3 skipped / 99% —— docs issue 清理轮(收尾)

> 摘要: 4 条 docs issue (26-10-02-0728 AUMID 漂移 / 26-10-01-2212 schema docstring 退役级别表 / 26-09-21-1408 README 用例数与 modules 行数快照 / 26-09-20-1427 skill USER.md 口径冲突) 全部修复置 Done; 本轮只动文档与 docstring, 零行为改动。
> 基线时间: 2026-10-03 06:50, develop @ fe70fccd(合并远端认领链闸门缺口修复后, test.full 实测)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。

TOTAL **2314 passed + 3 skipped / 99%**(13,469 语句 / 88 未覆盖 / 4,502 分支 / 89 partial,
test.full 31.7s, pytest 30.96s, rc=0)。
相对上一切片(26-10-03-0440: 2309 passed + 3 skipped / 99%, 13,354 语句 / 4,502 分支, @ 8cb2da59)
**passed +5** —— 全部来自本轮合并进来的远端提交 fe70fccd(认领链机检下沉 gen_doc_map --check,
配套 +5 用例); 本轮 docs 修复自身零测试增删、零行为改动, 各阶段 test.quick 均 2309 passed / 3 skipped
(修复期 @ 54fa227f)。合并前 @ 54fa227f 曾实测 2309+3 / 99%(13,452 语句, 该快照语句数与前后两条
均不一致, 疑似统计口径漂移, 不影响结论)。
