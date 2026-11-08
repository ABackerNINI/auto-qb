# 26-11-08-backend-hr-webui-compare-digest-ascii — issue 26-11-08-0827 compare_digest 非 ASCII 隐患同构两处修复

**Status:** Done
**Added:** 2026-11-08
**Updated:** 2026-11-08
**Summary:** compare_digest str 形态遇非 ASCII 抛 TypeError 的同构两处(hr discovery 配对码 / webui auth token)按 0527-hr #1 拍板形态修复: 运行期双侧 UTF-8 编码比较 + validate_config 给 web.token 限 ASCII + schema help 同步, 三面各补一条用例
**Topics:** backend-hr-webui-compare-digest-ascii
**Refs:** memory-bank/issues/26-11-08-0827-bug-hr-webui-compare-digest-ascii.html

## 本篇只回答

issue 26-11-08-0827(discovery 配对码 / webui auth token 的 str 形态 compare_digest 非 ASCII 隐患)怎么修的、修在哪三面、如何验证。

## 原始请求

1. 用户: 「修复memory-bank/issues/26-11-08-0827-bug-hr-webui-compare-digest-ascii.html」—— 显式认领 + 修复指令。

## 思考过程与决策

- 该 issue 由 0527-hr #1 的全仓同构排查发现(scope-guard 只报告不修), 修法 issue §06 已给: 复刻 #1 拍板形态(双保险)。本档案只做执行, 无改道。
- 双保险分层: 配置期限 ASCII(第一道闸, fail-fast)+ 运行期编码比较(不能靠配置校验兜运行期)。运行期修法与 hr/server.py `_token_ok`(已修样板)逐款对齐。
- 真机自检判定: **纯桩可验** —— 修复面是鉴权比较逻辑(401 vs TypeError), 单元测试直接构造非 ASCII 头值即可钉死, 不涉 qB 真执行/真文件系统进程注册表, 不入真机轨。

## 实现计划

1. 复验锚点(discovery.py `_pairing_ok` / auth.py require_token 的 str 形态 compare_digest; web.token 校验只验类型不限字符集)→ 均仍复现。
2. discovery.py `_pairing_ok`: given 与展示码/凭证双侧 `encode("utf-8")` 后比较(展示码/凭证由 HMAC 现导恒为 ASCII, 非 ASCII 头值必然不匹配 → 老实 401)。
3. webui/server/auth.py: token 与 manager.web.token 双侧编码后比较。
4. validate_config: web.token 加 `.isascii()` 档(报错文案与 hr_check.channel.token 同形态), 非字符串档不串档; schema groups.py web.token help 同步「仅限 ASCII 字符」。
5. 测试三面各补一条: test_hr_discovery(非 ASCII 配对码头 401)/ test_web_auth(非 ASCII 密钥直调 require_token: 匹配放行/不匹配 401)/ test_config_misc(web.token ASCII 校验四档)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 复验锚点(两处 compare_digest + web.token 校验面) | Done(2026-11-08) |
| 2 | discovery `_pairing_ok` 双侧 UTF-8 编码 | Done(2026-11-08) |
| 3 | webui auth require_token 双侧 UTF-8 编码 | Done(2026-11-08) |
| 4 | validate_config web.token 限 ASCII + schema help 同步 | Done(2026-11-08) |
| 5 | 三面测试补齐 + 相关测试文件全绿 | Done(2026-11-08) |
| 6 | 收尾: 评审 + issue 翻 Done + 基线切片 | Done(2026-11-08) |

## 进度日志

### R0 · 立档与修复 (2026-11-08)

- 同步开工(4e4cd116→00d3402d), 复验锚点均仍复现, 按 §06 建议修法执行(无改道)。
- 批次评审(209 行, 分面档 2 派发): 正确性+安全面零发现; 测试缺口+一致性面 2 条 —— ①issue 未摘账(major, 本轮收尾动作本身) ②新测试 `_req` 与既有 `_auth_request` 重复(nit, 当场修复)。两条均过 review.check(检 2/2)。
- test.full 全绿(见 kb.baseline); issue 翻 Done; 基线切片单点记数。

- 2026-11-08 11:43 issue 26-11-08-0827 修复: discovery 配对码/webui auth token 双侧 UTF-8 编码比较 + web.token 配置期限 ASCII(与 hr_check.channel.token 同形态) + 三面各补一条用例
