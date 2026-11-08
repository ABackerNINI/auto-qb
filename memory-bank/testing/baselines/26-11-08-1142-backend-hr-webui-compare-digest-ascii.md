# 5782 passed, 2 skipped, 99% —— compare_digest 非 ASCII 双保险三面修复后全量基线

> 摘要: compare_digest 非 ASCII 双保险三面修复后全量基线
> 基线时间: 2026-11-08 11:42

## 验收数字

- `commands run test.full`(实测 2026-11-08 11:41, 119.9s): **5782 passed, 2 skipped**(7 warnings)
- 覆盖率 TOTAL 表: 25742 stmts / 15 miss, 8918 branch / 38 partial, **99%**

## 本改动面

- `src/auto_qb/hr/discovery.py` — `_pairing_ok` 展示码/凭证比较前双侧 `encode("utf-8")`(issue 26-11-08-0827; 非 ASCII 配对码头值由 TypeError 异常面改老实 401)
- `src/auto_qb/webui/server/auth.py` — require_token 密钥比较双侧 UTF-8 编码(同上, 与 hr server `_token_ok` 同款双保险)
- `src/auto_qb/config/validation/sections.py` — `web.token` 加 `.isascii()` 档(与 hr_check.channel.token 同形态, 非字符串档不串档)
- `src/auto_qb/config/schema/groups.py` — web.token help 同步「仅限 ASCII 字符」
- `tests/test_hr_discovery.py` — `test_pairing_non_ascii_header_falls_401`; 文件头测试计划清单同步
- `tests/test_web_auth.py` — `test_non_ascii_token_encodes_both_sides`(直调 require_token 钉比较面); 文件头测试计划清单同步
- `tests/test_config_misc.py` — `test_web_token_ascii_only`; 文件头测试计划清单同步
- `memory-bank/issues/26-11-08-0827-bug-hr-webui-compare-digest-ascii.html` — 复验行 + 修复后补充, 状态 Open → Done
