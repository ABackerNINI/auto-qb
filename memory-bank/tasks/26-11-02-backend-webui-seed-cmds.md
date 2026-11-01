# 26-11-02-backend-webui-seed-cmds — WebUI set_share_limits 补必填参 shareLimitAction (issue 26-11-01-2102)

**Status:** Done
**Added:** 2026-11-02
**Updated:** 2026-11-02
**Summary:** 认领修复 issue 26-11-01-2102: facade 补必填参 share_limit_action="Default"(qB 5.0+/WebAPI 2.10.4 起必填, 缺失恒 400), commands 透传; 守阵 FakeClient 5 元组 + wire facade 出口新守阵; test.full 4804 过(基线切片 26-11-02-0044); issue 置 Done; RM04-09 真机验收留真机轨
**Topics:** backend-webui-seed-cmds
**Refs:** memory-bank/issues/26-11-01-2102-bug-webui-set-share-limits-missing-sharelimitaction.html, memory-bank/testing/baselines/26-11-02-0044-sharelimit-action-fix.md

## 原始请求

1. 「认领并修复 memory-bank/issues/26-11-01-2102-bug-webui-set-share-limits-missing-sharelimitaction.html」—— 用户显式指派认领并修复(2026-11-02, clone4 会话)。无既有计划;修法即 issue §06 建议修法。

## 思考过程与决策

- **复验(2026-11-02)三锚点全在**:①facade `qbapi.py::torrents_set_share_limits` 只补 `share_limits_mode="Default"`,不传 `share_limit_action`;②`commands.py::_cmd_set_share_limits` 调用点同;③库 qbittorrent-api 2026.10.1 `torrents.py:1585` wire 字典 `"shareLimitAction": share_limit_action` 且具名参缺省 None → requests 丢弃不发。qB 5.0+(Web API 2.10.4)该端点必填 `shareLimitAction` → 恒 400。现象在代码层复现。
- **修法 = issue §06 建议修法**(与 `share_limits_mode` 同一手法,见坑档 backend/qb-api.md「库透传参数的键名与 None 语义」):facade 补具名参 `share_limit_action: str = "Default"` 显式发参,commands 调用点透传 `"Default"` = 到限执行 qB 全局默认动作;5.2 无该参数、忽略未知参数无副作用,5.0+/5.3 同义。
- **守阵走 facade 出口而非裸库**:既有 wire 用例直调裸库并显式传 `share_limits_mode`,钉不住「facade 漏参」这一缺陷形态 —— 新守阵经 `QbApi` 出口发请求,断言请求体同时含 `shareLimitAction=Default` 与 `shareLimitsMode=Default`。
- **RM04-09 真机验收**(issue 验收判据)本轮无真机凭据(QBT_TEST_* 环境变量未给),留待真机轨复测;单测面全绿即代码层完成。

## 实现计划

1. facade `qbapi.py::torrents_set_share_limits` 补 `share_limit_action: str = "Default"` + docstring 补语义;
2. `commands.py::_cmd_set_share_limits` 调用点透传 `share_limit_action="Default"` + docstring 同步;
3. `tests/helpers.py` FakeClient 扩 `share_limit_action` 参并记 5 元组;`test_web_commands.py`(2 处)与 `test_web_longtail.py`(1 处)断言同步;
4. `tests/test_qbapi_wire.py` 新增 facade 出口 wire 守阵(请求体含 shareLimitAction),同步头部「## 测试计划」;
5. `dev.fmt` 改动文件 → `test.quick` → `test.full` + 新基线切片;
6. issue 置 Done 写修法/数字 → `kb.index` → `kb.wrap` → `kb.check`。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | facade 补参 `share_limit_action` + docstring | Done(2026-11-02) |
| 2 | commands.py 调用点透传 | Done(2026-11-02) |
| 3 | FakeClient 5 元组 + 既有断言更新 | Done(2026-11-02) |
| 4 | test_qbapi_wire 新增 facade 出口守阵 | Done(2026-11-02) |
| 5 | fmt/quick/full + 基线切片 | Done(2026-11-02, 切片 26-11-02-0044) |
| 6 | issue 置 Done + 收尾 | Done(2026-11-02) |

## 进度日志

### R0 · 立档 (2026-11-02)

- 同步成功 10a32bfe(91a6c66d→10a32bfe 快进, 远端领先 56 笔)。认领立档, issue 置 In Progress + doc-refs 双向登记; 复验三锚点成立(详见「思考过程与决策」)。

- 2026-11-02 00:45 认领修复 issue 26-11-01-2102: facade 补必填参 share_limit_action=Default(qB 5.0+/WebAPI 2.10.4), commands 透传; FakeClient 5 元组 + wire facade 出口新守阵; test.full 4804 过(基线 26-11-02-0044); issue 置 Done; 未提交(用户未授权)
