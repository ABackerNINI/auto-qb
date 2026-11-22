# 7025P/6S 覆盖率 99% —— port_kill nt 支 ANSI 解码修复后基线

> 摘要: issue 26-11-23-0012 修复批后基线 —— nt 实杀失败原因行改按系统 ANSI 码页解码, 新增守阵 1 条; 真机未触发 taskkill(高风险外部动作), 中文 Windows 真 GBK 字节解码链本机实测
> 基线时间: 2026-11-23 01:31

## 验收数字

`commands run test.full` 实测:

```
TOTAL                                                31412    108  11190     93    99%
7025 passed, 6 skipped, 8 warnings in 145.61s (0:02:25)
```

## 本改动面

- `scripts/port_kill.py`: nt 支 `_kill_pid` 收字节(去掉 text=True/encoding/errors), 新增 `CONSOLE_CODEC = "mbcs"` + `_decode_console_text` 单点按系统 ANSI 码页解码(str 桩透传 / 非 Windows mbcs 缺失 utf-8 兜底); POSIX 支零改动。
- `tests/test_legacy_review4_scripts.py`: 新增 `test_port_kill_nt_kill_failed_decodes_ansi_codepage`(真 GBK 字节 + 无 U+FFFD + 禁 text=True + 旧解码红验 + str/兜底两面), 同步头部「测试计划」清单。
- `memory-bank/issues/26-11-23-0012-bug-port-kill-gbk-mojibake.html`: 复验与修复后补充落 §07, 状态 In Progress → Done。
- 相对 26-11-23-0017(7024P): +1 用例 = 本批新增守阵; 其余计数与覆盖率不变。
- 真机准入: 中文 Windows 本机对 taskkill 同串 GBK 字节做 utf-8/mbcs 对照实测(01:07, mojibake 复现 + mbcs 还原原文); 未对真实进程触发 taskkill(杀进程属高风险外部动作, 守阵桩已覆盖完整失败分支), 故不做进程面真机冒烟。
