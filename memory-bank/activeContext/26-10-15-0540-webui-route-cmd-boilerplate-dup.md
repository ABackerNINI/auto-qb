# webui-route-cmd-boilerplate-dup — 路由命令透传样板收敛(issue 26-10-11-0309 认领修)

> 摘要: 用户「认领并修复 memory-bank/issues/26-10-11-0309-refactor-webui-route-cmd-boilerplate-dup.html」—— dup-code-audit 专题 webui 轮(档案 `26-10-11-webui-dup-code-fixes`)十条延后项的最后一条到手, 修毕 webui 10 条 refactor 清零。开工同步快进 `6adf6282→5f5689c5`; 复验三处重复均在(跳检 403 门控逐字两处 / 12 个单行透传 handler / 三对成对端点)。定案走 issue 建议的「至少对成对抽 helper」支: 表驱动注册器评估不改道(残留重复是 builder 契约本身无逻辑重复; 动态注册丢 handler 名 + 跨 3 文件改注册机制, 收益仅几行别名; 与 R1 commands 层参数化单点先例和「显式端点」文化不合)。落地: `_require_skip_check(ctx)` 门控单点(两处 403 → 1 处); 8 个形状 helper(torrent_cmds 四 + groups 一 + torrent_detail 三)收敛 21 个端点为「路径→命令」一行声明, 差异项(命令名/字段名/空组 400 文案)作参数传入(沿用 R1「文案由调用方给」口径)。全程**行为逐字不变**: 既有表驱动用例逐端点钉 (cmd, payload) 全绿 + 金清单守阵全绿; 新增静态守阵 `test_route_cmd_passthrough_single_point`(AST: helper 各定义一次 + 端点体只剩 helper 调用 + 三种逐字形状零复发), 四类突变红验(写回载荷构造/删 helper/抄双份 helper/新增端点照抄形状)全过。test.full 全绿(数字见基线切片 `26-10-15-0532`, 不手抄)。issue 状态流水 Open → In Progress → Done; 认领链双向闭合(档案 Refs 列本件, 本件 doc-refs 指档案)。
> 最后活动: 2026-10-15 05:40

**Refs:** memory-bank/tasks/26-10-11-webui-dup-code-fixes.md

## 正在进行

- 无(本 issue 已修完入账; webui 10 条 refactor 全部 Done)

## 本专题关键坐标

- 任务档案: `memory-bank/tasks/26-10-11-webui-dup-code-fixes.md`(R4 续轮段 + 子任务表 #10)
- 基线切片: `memory-bank/testing/baselines/26-10-15-0532-webui-route-cmd-boilerplate-dup.md`
- 改动源文件: `src/auto_qb/webui/server/routes/{torrent_cmds,groups,torrent_detail}.py` + 守阵 `tests/test_web_route_manifest.py`
