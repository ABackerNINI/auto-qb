"""test_web_route_manifest 测试计划: W0 结构守阵 + 路由金清单

## 测试计划(每个测试函数一条)
- test_web_route_manifest_frozen: 路由金清单守阵(W0, plan 26-09-22-1857; ALT-01 增 2 条 speed/alt, P2' 增 1 条 skip-check, 26-10-01-2216 阶段1 增 1 条 hr sites entries, 26-10-02-1955 W1 增 1 条 webui/flags, 26-10-03-0946 P4 增 3 条 traffic/qb, 26-10-04-0312 S3 增 1 条 hr history, 26-10-05-0314 S2 增 1 条 skip-check/precheck, WEBUI 错误历史 S2 增 1 条 errlog, 26-10-16-0541 S6 增 3 条 traffic/monitor, 26-10-16-0541 S7 增 1 条 traffic/monitor/notify, 26-10-17-0339 S17 增 1 条 traffic/monitor/relaunch): 82 条 (method, path) 集合逐一钉死, web.py 拆 web/ 包期间任何路由丢失/改名/方法变更即红
- test_create_app_is_thin_assembly: 组装壳守阵(W6): create_app 源 ≤150 行且无内联路由装饰器(防 926 行单函数回潮)
- test_route_cmd_passthrough_single_point: 守阵(issue webui-route-cmd-boilerplate-dup) 「路由→命令」透传 mechanics 只存于形状单点 —— 8 个 helper 各定义恰好一次 + 21 个收敛端点体只剩一行 helper 调用 + 三种逐字透传形状零复发(AST 静态; 行为等值由既有表驱动用例逐端点钉 cmd/payload)
"""
from auto_qb.webui import create_app

from webui_helpers import _iter_api_routes

# ---- W0 结构守阵(plan 26-09-22-1857: web.py create_app 拆分 web/ 包, 先行落阵再动刀) ----

# 从拆分前的 web.py 用 AST 提取的全部路由(取证 2026-09-22, develop @ 975e146):
# 57 个 /api 端点 + 3 个 UI 重定向(/, /newui, /newui/{rest:path})。拆分全程必须逐条保持。
# (2026-09-28 ALT-01 增 POST /api/speed/alt 与 /api/speed/alt/toggle 两条, 计划 26-09-28-0037)
# (2026-10-02 增 POST /api/events/ticket —— SSE 一次性票据换票, issue 26-09-21-1408 B-01)
# (2026-10-03 增 3 条 GET /api/traffic/qb/* —— qB 口径流量图, plan 26-10-03-0946 §08 P4)
# (2026-10-04 增 1 条 GET /api/hr/history —— 拉取历史时间轴, plan 26-10-04-0312 §3.4)
_GOLDEN_ROUTES = {
    ("GET", "/"),
    ("GET", "/api/categories"),
    ("POST", "/api/categories"),
    ("POST", "/api/categories/edit"),
    ("POST", "/api/categories/remove"),
    ("GET", "/api/cmd/{cmd_id}"),
    ("POST", "/api/hr/confirm-empty"),
    ("POST", "/api/hr/refresh"),  # 26-09-30-0240: 立即拉取(置一次性 force 旗标 + 唤醒取数线程)
    ("GET", "/api/config"),
    ("PUT", "/api/config"),
    ("POST", "/api/config/preview"),
    ("GET", "/api/config/public"),
    ("GET", "/api/config/schema"),
    ("GET", "/api/events"),
    ("POST", "/api/events/ticket"),  # SSE 换票(26-10-02 加固: ?ticket= 取代长期密钥查询串)
    ("POST", "/api/expr/eval"),
    ("GET", "/api/fs/dirs"),
    ("POST", "/api/fs/mkdir"),
    ("GET", "/api/groups"),
    ("POST", "/api/groups/{key}/delete"),
    ("POST", "/api/groups/{key}/pause"),
    ("POST", "/api/groups/{key}/reannounce"),
    ("POST", "/api/groups/{key}/resume"),
    ("GET", "/api/keys"),  # 键盘快捷键 W6(计划 26-09-28-0354): webui-keys.json 读(兜底链)
    ("PUT", "/api/keys"),  # 同上: 整份替换写(结构校验 422)
    ("GET", "/api/log"),
    ("GET", "/api/errlog"),  # 错误历史内存环增量(WEBUI 错误历史 S2; 与 /api/log 同属系统诊断)
    ("POST", "/api/open-path"),
    ("GET", "/api/paths"),
    ("GET", "/api/search"),
    ("GET", "/api/speed/mode"),
    ("POST", "/api/speed/override"),
    ("POST", "/api/speed/alt"),
    ("POST", "/api/speed/alt/toggle"),
    ("GET", "/api/state"),
    ("GET", "/api/stats"),
    ("GET", "/api/status"),
    ("GET", "/api/tags"),
    ("POST", "/api/tags"),
    ("POST", "/api/tags/remove"),
    ("POST", "/api/torrents/add"),
    ("POST", "/api/torrents/bulk"),
    ("GET", "/api/torrents/{hash}"),
    ("POST", "/api/torrents/{hash}/auto-tmm"),
    ("POST", "/api/torrents/{hash}/delete"),
    ("GET", "/api/torrents/{hash}/export"),
    ("GET", "/api/torrents/{hash}/files"),
    ("POST", "/api/torrents/{hash}/files/priority"),
    ("POST", "/api/torrents/{hash}/force-start"),
    ("POST", "/api/torrents/{hash}/limits"),
    ("POST", "/api/torrents/{hash}/location"),
    ("POST", "/api/torrents/{hash}/pause"),
    ("GET", "/api/torrents/{hash}/peers"),
    ("POST", "/api/torrents/{hash}/queue"),
    ("POST", "/api/torrents/{hash}/reannounce"),
    ("POST", "/api/torrents/{hash}/recheck"),
    ("POST", "/api/torrents/{hash}/rename"),
    ("POST", "/api/torrents/{hash}/rename-fs"),
    ("POST", "/api/torrents/{hash}/resume"),
    ("POST", "/api/torrents/{hash}/share-limits"),
    ("POST", "/api/torrents/{hash}/skip-check"),  # P2' 右键跳检(plan 26-09-30-0109)
    ("POST", "/api/torrents/skip-check/precheck"),  # 跳检预检只读端点(plan 26-10-05-0314 S2; 403 门控同单发)
    ("POST", "/api/torrents/relocate/precheck"),  # 整组迁移预检只读端点(plan 26-10-18-1604 P2; 403 门控 relocate.enabled)
    ("POST", "/api/relocate/precheck-add"),  # 添加种子落点预检只读端点(计划 26-10-18-1604 §3.6.1; 同一 403 门控)
    ("POST", "/api/relocate/cancel"),  # 撤销迁移端点(§3.5.1 成本两步; 同一 403 门控; P7 补齐界面入口)
    ("POST", "/api/torrents/{hash}/super-seeding"),
    ("GET", "/api/torrents/{hash}/trackers"),
    ("POST", "/api/torrents/{hash}/trackers/add"),
    ("POST", "/api/torrents/{hash}/trackers/remove"),
    ("GET", "/api/traffic/history"),
    ("GET", "/api/traffic/qb/global"),  # qB 口径流量图三端点(plan 26-10-03-0946 §08 P4; 同域对照 history)
    ("GET", "/api/traffic/qb/group/{key}"),  # 同上: 组读侧现算(§04.1), key 同 /api/groups/{key} 通道
    ("GET", "/api/traffic/qb/torrent/{hash}"),  # 同上: 单种(数据挂 infohash, 删种冻结后历史仍可查)
    ("GET", "/newui"),
    ("GET", "/newui/{rest:path}"),
    ("GET", "/api/hr/status"),  # M4: HR 站点级状态快照(只读; 与 --hr-status 同一口径)
    ("GET", "/api/hr/sites/{site}/entries"),  # 种子明细(计划 26-10-01-2216 §7 阶段1; 决策点②b 按站点按需拉)
    ("GET", "/api/hr/history"),  # 拉取历史时间轴(计划 26-10-04-0312 §3.4; 表③ 数据源, 跨站合并)
    ("GET", "/api/sites/missing"),  # 站点导入: 未配置站点扫描(只读; 与 --export-yaml --only-missing 同口径)
    ("GET", "/api/webui/flags"),  # R2 跳检菜单开关(计划 26-10-02-1955 W1): 前端功能旗标(登录后, 读实时配置)
    ("GET", "/api/traffic/monitor/status"),  # 全局流量监视器工具联动(计划 26-10-16-0541 S6): 工具 /status 代理(只读, 恒 200 空态)
    ("PUT", "/api/traffic/monitor/config"),  # 同上: 工具 /config 代理(全量覆盖 -> 前端读后写)
    ("POST", "/api/traffic/monitor/autostart"),  # 同上: 工具 /autostart 代理(幂等注册/卸载自启)
    ("POST", "/api/traffic/monitor/relaunch"),  # S17: 「立即拉起/重试」促订阅线程重跑一轮(经 webui 模块 request_relaunch)
    ("POST", "/api/traffic/monitor/shutdown"),  # 26-10-17-1737 S3: 停止工具(代理工具 POST /shutdown)
    ("POST", "/api/traffic/monitor/notify"),  # S7 接收面: 工具推送的累计流量阈值事件(鉴权同全局; 路径与 webui/tool_client.NOTIFY_PATH 同源)
}


def test_web_route_manifest_frozen(web_env):
    """路由金清单守阵: 84 条 (method, path) 集合逐一钉死, 丢失/改名/方法变更即红

    (2026-10-07 编辑 tracker 下线, plan 26-10-07-0055 S2: 减 POST /api/torrents/{hash}/trackers/edit, 77->76;
     2026-10-16-0541 S6: 增 3 条 /api/traffic/monitor/* —— 全局流量监视器工具联动代理;
     2026-10-16-0541 S7: 增 1 条 /api/traffic/monitor/notify —— 工具通知接收面;
     2026-10-17-0339 S17: 增 1 条 /api/traffic/monitor/relaunch —— 来源卡「立即拉起/重试」;
     2026-10-17-1737 S3: 增 1 条 /api/traffic/monitor/shutdown —— 来源卡「停止工具」代理;
     2026-10-18-1604 P2: 增 2 条整组迁移预检(迁移/添加种子, 只读, 403 门控 relocate.enabled), 82->84)
     2026-10-18-1604 P7: 增 1 条撤销迁移(§3.5.1 界面入口补齐, 同一 403 门控), 84->85)

    集合比对**不比顺序**: 拆分后按域 include_router, 跨 router 注册顺序与旧源码不再逐条
    一致 —— 已核实无同形路径冲突(每条 (method, path) 恰好一条路由, /api/torrents/bulk、
    /add 与 /{hash} 靠方法区分); 各 router 内部相对顺序保持源码顺序。
    HEAD 是 Starlette 对 GET 路由的自动补集, 比对时剔除。
    """
    from starlette.routing import Mount

    mgr, client = web_env
    app = client.app
    found = {(next(iter(r.methods - {"HEAD"})), r.path) for r in _iter_api_routes(app.routes)}
    assert found == _GOLDEN_ROUTES, (
        f"路由清单漂移: 多出 {sorted(found - _GOLDEN_ROUTES)}, 丢失 {sorted(_GOLDEN_ROUTES - found)}"
    )
    assert any(isinstance(r, Mount) for r in app.routes), "静态挂载(StaticFiles)不得丢失"


def test_create_app_is_thin_assembly():
    """组装壳守阵(W6, plan 26-09-22-1857): create_app 源 ≤150 行且不含内联路由装饰器

    本 issue 的病根是工厂函数无约束生长(926 行); 行数上限 + 装饰器检查双闸防回潮。
    红验: 同一断言跑拆分前的 create_app(926 行, 含 @app.*)必红(见计划 §06 W6)。
    """
    import inspect

    from auto_qb.webui import create_app

    src = inspect.getsource(create_app)
    n = len(src.splitlines())
    assert n <= 150, f"create_app 长回 {n} 行(上限 150) —— 端点请进 routes/ 对应域模块, 别再塞回工厂"
    assert "@app." not in src, "组装壳里不得出现内联路由装饰器 —— 端点一律放 routes/ 模块"


def test_route_cmd_passthrough_single_point():
    """守阵(issue webui-route-cmd-boilerplate-dup): 「路由→命令」透传的 mechanics 只存于形状单点

    routes/* 的单行透传端点此前成对逐字同(仅命令名 / 字段名不同): 载荷构造(取参 / 清洗 /
    投递)收敛到形状 helper 后, 端点本身应只剩「路径 -> 命令」一行声明。
    静态(AST, 三文件 routes/{torrent_cmds,groups,torrent_detail}.py):
      ① 八个形状 helper 各定义恰好一次(torrent_cmds 四 + groups 一 + torrent_detail 三);
      ② 21 个收敛端点的函数体(可带 docstring)必须恰是一行形状 helper 调用;
      ③ 任何端点体不得再出现 issue 点名的三种逐字形状 —— `_enqueue(<str>, <行内 dict>)`
         且 dict 为 {"hash": X} / {"hash": X, "enable": X} / {"key": _group_key_param(X)}。
    行为等值不由本守阵保 —— 既有表驱动用例逐端点钉 (cmd, payload):
    test_web_commands.py::test_api_torrent_write_endpoints_enqueue(15 端点)、
    test_web_longtail.py::test_api_torrent_write_endpoints_extra_enqueue(pause/resume/delete/skip-check)、
    test_web_admin.py(分类/标签/限速三对)、金清单本件 test_web_route_manifest_frozen。
    红验: 任一端点写回逐字载荷构造 / 删一个 helper 定义 / 抄双份 helper, 三类突变均判红。
    """
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "src" / "auto_qb" / "webui" / "server" / "routes"
    # 文件 -> (形状 helper 名集, 必须收敛为「一行 helper 调用」的端点名集)
    plan = {
        "torrent_cmds.py":
            (
                {"_cmd_hash", "_cmd_enable", "_cmd_field", "_cmd_str_list"},
                {
                    "api_t_pause",
                    "api_t_resume",
                    "api_t_reannounce",
                    "api_t_recheck",
                    "api_t_super_seeding",
                    "api_t_force_start",
                    "api_t_auto_tmm",
                    "api_t_location",
                    "api_t_rename",
                    "api_t_queue",
                    "api_t_trackers_add",
                    "api_t_trackers_remove",
                },
            ),
        "groups.py": ({"_cmd_key"}, {"api_pause", "api_resume", "api_reannounce"}),
        "torrent_detail.py":
            (
                {"_cmd_category", "_cmd_tags", "_cmd_speed_limits"},
                {
                    "api_category_create",
                    "api_category_edit",
                    "api_tags_create",
                    "api_tags_remove",
                    "api_speed_override",
                    "api_speed_alt",
                },
            ),
    }
    for fname, (helpers, endpoints) in plan.items():
        tree = ast.parse((root / fname).read_text(encoding="utf-8"))
        build = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "build_router")
        nested = [n for n in build.body if isinstance(n, ast.FunctionDef)]
        names = [n.name for n in nested]
        by_name = {n.name: n for n in nested}
        for h in sorted(helpers):
            assert names.count(h) == 1, f"{fname}: 形状单点 {h} 应定义恰好一次(现 {names.count(h)} 次)"
        for ep in sorted(endpoints):
            assert ep in by_name, f"{fname}: 端点 {ep} 缺失(改名/删除须走金清单与调用方)"
            body = by_name[ep].body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                body = body[1:]  # docstring
            assert len(body) == 1 and isinstance(body[0], ast.Return), f"{fname}:{ep} 函数体应只剩一行 return(单点调用)"
            call = body[0].value
            assert isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id in helpers, (
                f"{fname}:{ep} 应调用形状单点 {sorted(helpers)}(现 {ast.dump(call)[:80]})—— mechanics 不得在端点体重抄"
            )
        # ③ 逐字形状 Ban: 端点(非 helper)return _enqueue(<str>, <行内 dict>) 且命中点名形状
        for fn in nested:
            if fn.name in helpers:
                continue
            for node in ast.walk(fn):
                if not (isinstance(node, ast.Return) and isinstance(node.value, ast.Call)):
                    continue
                c = node.value
                if not (isinstance(c.func, ast.Name) and c.func.id == "_enqueue" and len(c.args) == 2):
                    continue
                d = c.args[1]
                if not isinstance(d, ast.Dict):
                    continue
                keys = [k.value for k in d.keys if isinstance(k, ast.Constant)]
                if keys == ["hash"] and len(d.keys) == 1:
                    shape = '{"hash": X}'
                elif keys == ["hash", "enable"] and len(d.keys) == 2:
                    shape = '{"hash": X, "enable": X}'
                elif (
                    keys == ["key"] and len(d.keys) == 1 and isinstance(d.values[0], ast.Call) and
                    isinstance(d.values[0].func, ast.Name) and d.values[0].func.id == "_group_key_param"
                ):
                    shape = '{"key": _group_key_param(X)}'
                else:
                    continue
                raise AssertionError(f"{fname}:{fn.name} 又出现逐字透传形状 {shape} —— mechanics 应收敛到形状单点")
