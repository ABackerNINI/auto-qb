# 3212 —— webui 路由命令透传样板收敛(issue 26-10-11-0309 认领修)执行基线

> 摘要: 用户「认领并修复 memory-bank/issues/26-10-11-0309-refactor-webui-route-cmd-boilerplate-dup.html」→ webui 重复代码修复轮(26-10-11-webui-dup-code-fixes)按拍板留 Open 的最后一条延后项, 本轮认领修完(webui 10 条 refactor 清零): ① 跳检 403 门控两处逐字同抽 `_require_skip_check(ctx)` 单点; ② 「路由→命令」透传 mechanics 收敛为 8 个形状 helper(torrent_cmds 四: hash/enable/单字符串字段/字符串列表字段; groups 一: 组 key; torrent_detail 三: 分类/标签/限速值), 21 个端点缩为「路径→命令」一行声明, 差异项(命令名/字段名/空组 400 文案)作参数传入(沿用 R1「文案由调用方给」口径); ③ build_router 头样板复评「已趋薄, 无逻辑重复可再安全收敛」(表驱动注册器评估不改道, 理由见任务档案思考段)。全程**行为逐字不变**: 既有表驱动用例逐端点钉 (cmd, payload) 全绿 + 金清单守阵全绿; 新增静态守阵 1 条(AST, 四类突变红验: 写回载荷构造/删 helper/抄双份 helper/新增端点照抄形状)。数字相对上基线 `26-10-15-0454` 无回归信号(差值现列 `commands run kb.baseline -n 2`)。
> 基线时间: 2026-10-15 05:38

**Refs:** memory-bank/tasks/26-10-11-webui-dup-code-fixes.md

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` -> 已同步 5f5689c5; 工作树含本轮改动时实测)
- 命令: `commands run test.full`(Windows)
- **实测 (Windows)**: **3212 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**

| 面 | 语句 | 未覆盖 | 分支 | partial | 覆盖率 |
|---|---|---|---|---|---|
| TOTAL | 16828 | 162 | 5706 | 143 | 99% |

- 耗时: 162.85s(单次采样, 区间口径见 `testing/baseline.md`)
- 新增守阵 1 个测试函数(红验通过): `test_route_cmd_passthrough_single_point`(AST 静态: 8 个形状 helper 各定义恰好一次 + 21 个收敛端点体只剩一行 helper 调用 + 三种逐字透传形状(`{"hash": X}` / `{"hash": X, "enable": X}` / `{"key": _group_key_param(X)}`)零复发; 行为等值由既有表驱动用例保, 不重复动态半)
- 行为逐字不变的证据面(既有用例, 本轮零改动全绿): `test_web_commands.py::test_api_torrent_write_endpoints_enqueue`(15 端点 cmd/payload 逐钉)/ `test_web_longtail.py::test_api_torrent_write_endpoints_extra_enqueue`(pause/resume/delete/skip-check)/ `test_web_admin.py`(分类/标签/限速三对)/ `test_web_skip_check.py` + `test_web_api_core.py`(403 门控两端点)/ `test_web_route_manifest.py::test_web_route_manifest_frozen`(76 条 (method, path) 金清单)
- Linux (WSL 沙箱) 本轮未重测 —— 改动全在 Windows/Linux 同构路径(纯 Python 重构 + 静态守阵), 无平台分支。

## 包内脚本测试

- 本轮未触碰 `.commands/` 与 `.agents/skills/commands/`, 未跑 `test.pkg`; 提交闸门按 match 规则自判。
