# 3790 passed + 2 skipped(根, 覆盖率 97.65%) + 工具侧 303 passed —— gtm 正主注册 P1-P4 全量基线

> 摘要: gtm 正主注册与让位代拉(计划 26-10-20-1316)实施完成(P1 身份模块+启动矩阵 / P2 claim 人工易主通道 / P3 auto-qb 侧编排+设置页 / P4 文档)后的全量基线
> 基线时间: 2026-10-20 15:55

## 验收数字

根(`.venv/Scripts/python.exe -m pytest -q`, 2026-10-20 15:5x, 本地):

```
TOTAL      20685    378   6998    259    98%
3790 passed, 2 skipped in 141.45s
```

工具侧(`cd tools/global-traffic-monitor && uv run pytest -q`, 同轮):

```
303 passed in 35.99s
```

口径注记:

- 根 3790 = 上基线(26-10-20-0049) 3758 + 32: 新增 test_identity.py 39 例(工具侧, 不占根套件)之外的根套件增量全部来自本轮 —— test_traffic_source_agent.py +9(claim 目标解析/有界前台/注记只读/状态载荷/镜像守阵扩项)、test_web_traffic_monitor.py +6(claim 路由 3 例 + 注记透传 + 前端接线守阵 + auth 扩点)、test_web_route_manifest.py 金清单 84 -> 86、test_webui_trigger_registry.py 补 tmClaim 登记(两条守阵由红转绿即此)。
- 覆盖率 97.65%(pytest 显示 98%) —— **存量缺口非本轮引入**: 上基线(0049) 97.53%、更早 0004 轮为 97.54% 且 FAIL 行已在基线里留痕; 本轮 97.65% 略高于上基线。`--cov-fail-under=98` 的 FAIL 属既有状态, 全量用例 0 failed。
- 首轮全量曾 2 failed(test_web_route_manifest_frozen / test_trigger_registry_call_sites_exact): 均为「新增路由/调用点必须登记」的冻结守阵, 按纪律补金清单与 triggers.js 登记后转绿 —— 守阵工作正常, 非代码缺陷。
- 副作用台账越界 0 条(含 `_run_foreground` 真跑 node --version 一例, node 在 sidefx POPEN 白名单内)。

## 端到端复算(手动, 真进程)

`tools/global-traffic-monitor/tests/manual_e2e_relay.py`(不入套件: sidefx POPEN 白名单不放行 python 子进程), 仓库 venv python 实跑通过:

- A 起(认领正主, 数据落 A/data) -> A 强杀崩溃(留残留指针) -> B 先起(读记录 id 异 -> **代拉 A 的启动器后立即退出, rc=0, B 零写入**) -> A 被代拉起(注记已清, 数据仍落 A/data, B/data 不存在) -> A 在跑时 B claim 被拒(「请先停止」) -> 停 A 后 B claim 成功(primary.json 三项换成 B, B/data 认领 data-id)。

## 本改动面

| 文件 | 改动 |
|---|---|
| `tools/global-traffic-monitor/src/gtm/identity.py` | 新建(P1): 三处 ID 读写 + O_EXCL 原子认领 + 判定矩阵 ①②③④ + 记录自洽校验 + 注记写/清 + 代拉起单点; P2 补 claim 启动器常量 |
| `tools/global-traffic-monitor/src/gtm/__main__.py` | cmd_run 启动序列插桩(身份门在取锁/绑端口/解析数据目录之前; refuse 注记+exit 1; relay 代拉+注记+exit 0; 数据归属校验+data_dir 补写; server.start 成功后清注记); 新增 cmd_claim(P2) |
| `tools/global-traffic-monitor/claim.cmd` / `claim.sh` | 新建(P2): 安装内第二启动器, 零参数(D19 同族), 源码态 venv / 编译态同目录 exe 两形态注释 |
| `tools/global-traffic-monitor/tests/test_identity.py` | 新建: 39 例 hermetic(monkeypatch 路径单点与 _spawn)+ cmd_run/cmd_claim 集成 |
| `tools/global-traffic-monitor/tests/manual_e2e_relay.py` | 新建: 手动 e2e 复算脚本(双安装真进程, 环境全重定向临时目录) |
| `src/auto_qb/core/traffic_source/agent.py` | P3: 正主注册镜像常量块 + ClaimTarget/ClaimResult + resolve_claim_target + _run_foreground(可注入单点) + run_claim(有界前台) + deferred_note_path/read_deferred_note(D7 只读) + status() 增 claim_note + CLAIM_TIMEOUT_S |
| `src/auto_qb/webui/server/routes/traffic_monitor.py` | P3: 新增 `POST /api/traffic/monitor/claim`(不经工具控制面; 502 缺入口 / 409 拒绝原样转述 / 200 成功); status 载荷增 claim_note |
| `src/auto_qb/webui/static/shared/triggers.js` | P3: calls 登记 tmClaim(scope/why) |
| `src/auto_qb/webui/static/shared/state.js` / `config_hub.js` / `tpl/traffic-card.html` | P3: claim 四态(claiming/claimMsg/claimErr/claimNote) + tmClaim(二次确认+调用) + tmLoad 回填 + 按钮恒显示(D6) + 「正主注册」注记行(D7) |
| `tests/test_traffic_source_agent.py` / `tests/test_web_traffic_monitor.py` / `tests/test_web_route_manifest.py` | P3 测试与冻结守阵扩项 |
| `tools/global-traffic-monitor/README.md` / `docs/configuration.md` | P4: 「正主注册与让位」完整章节(三处 ID/矩阵/claim 流程/注记/纪律/e2e 跑法) + 配置文档多安装小节 |
| `.gitignore` | tools/global-traffic-monitor/tool-id(安装 ID, 仓库内安装根首启即生成) |

提交: P1 `96635018` · P2 `d0ba1693` · P3+P4 本轮(develop, 推送后远端一致)。
