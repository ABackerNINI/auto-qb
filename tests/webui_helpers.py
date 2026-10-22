"""webui_helpers 共享件: WEB UI 后端测试拆分后的跨文件辅助与常量(原单文件已拆为 16 个平铺模块, 见 tasks/26-10-08-backend-test-web-split.md)
"""
import json
import os
import re
import time
from types import SimpleNamespace

from auto_qb.config.models import HrCheckConfig
from auto_qb.config.models import RelocateConfig  # noqa: E402  (整组迁移, 计划 26-10-18-1604 P2)
from auto_qb.core.qbapi import QbApi
from auto_qb.infra.utils import encode_group_key
from auto_qb.torrents import TorrentStore
from auto_qb.webui.runtime import WebUIRuntime

KEY = ("R:/seeds", ("a.mkv", "b.mkv"))

# WEB 测试环境配置文本单点(issue 26-10-21-0502-refactor-test-web-env-param-dup):
# conftest.web_env 与 _make_web_manager 的各内联拷贝收敛于此 —— 6 份拷贝(conftest 1 +
# test_web_backend_misc 2 + test_web_views_reload 3)并为 web_env 的 config_text 参数缺省值。
WEB_ENV_CONFIG_TEXT = "config:\n  qbittorrent:\n    host: h\n    port: 1\n    username: u\n    password: p\n  schema_version: 5\n"


def _web_stub(enabled=True, host="127.0.0.1", port=8080, token="t"):
    """WEB 段替身(仅 _apply_web_config 关心的字段)"""
    return SimpleNamespace(enabled=enabled, host=host, port=port, token=token)


def _make_web_manager(tmp_path, config_text):
    """构造 WEB API 所需的 manager 替身(轻量 namespace, 不连 qB)"""
    from types import SimpleNamespace

    wake_calls = []  # 记录 manager.wake() 调用: 投递用户命令应唤醒, 自投递命令不应唤醒
    state_file = os.path.join(tmp_path, "state.json")
    config_file = os.path.join(tmp_path, "config.yml")
    with open(config_file, "w", encoding="utf-8") as f:
        f.write(config_text)
    web_cfg = SimpleNamespace(
        enabled=True,
        host="127.0.0.1",
        port=8080,
        token="",
        skip_local_verify=False,
        # R2(计划 26-10-02-1955 W1): 测试侧默认开 —— gate 用例按需实例级置 False
        skip_check_menu=True,
        # ctx_menu(计划 26-10-20-0024 W1): None = 默认布局; flags 端点原样下发, 用例按需置布局
        ctx_menu=None
    )
    config = SimpleNamespace(
        web=web_cfg,
        trackers={
            "HHan":
                SimpleNamespace(
                    tags=["HHan"],
                    remove_tags=[],
                    remove_similar_tags=False,
                    upload_speed_limit=0,
                    download_speed_limit=0,
                    hr=None,
                    domains=["d.com"],
                    rules=[]
                )
        },
        state_file=state_file,
        data_dir=str(tmp_path),
        grouping=SimpleNamespace(enabled=True, check_missing_files=True, missing_tag="MISSING"),
        add_episode_tags=SimpleNamespace(enabled=False, add_tag_single="", add_tag_multi=""),
        delete_tags=[],
        delete_tags_if_has_no_torrents=[],
        global_speed_limit_curve=None,
        # 整组迁移(计划 26-10-18-1604 P2): 路由 403 门控读 relocate.enabled —— 用真模型,
        # 缺省 enabled=False(保守默认); 端点用例按需实例级置 True
        relocate=RelocateConfig(),
        # 全局流量来源(计划 26-10-17-0339 S15/S17): 来源单点 —— provider + 两来源面;
        # 缺省 provider=traffic_monitor / 工具面 enabled=false(与真 Config 默认一致)
        traffic_source=SimpleNamespace(
            provider="traffic_monitor",
            traffic_monitor=SimpleNamespace(dat_path=""),
            global_traffic_monitor=SimpleNamespace(
                enabled=False, tool_dir="", tool_exe="", data_dir="", notify_cooldown_s=600.0
            ),
        ),
        qb_traffic=None,  # qB 口径流量(plan 26-10-03-0946 §06): None = 未启用; 用例按需置 QbTraffic(enabled=True)
        notify=SimpleNamespace(enabled=False),
        qbittorrent=SimpleNamespace(host="127.0.0.1", port=1, username="u", password="p"),
        logging=SimpleNamespace(level="WARNING", file="", max_bytes=1048576, format="%(message)s"),
        main_tick=2.0,
        sync_interval=1.5,
        max_tasks_per_tick=20,
        interval=60.0,
        remove_similar_tags=False,
        skip_checking_tag="zSkipChecked",
        rules_config={},
    )
    groups = {KEY: ["HA", "HB"]}
    view = [
        {
            "key":
                encode_group_key(KEY),
            "name":
                "Show",
            "count":
                2,
            "dlspeed":
                0,
            "upspeed":
                2048,
            "uploaded":
                4096,
            "size":
                1024**3,
            "members":
                [
                    {
                        "hash": "HA",
                        "site": "HHan",
                        "state": "stalledUP",
                        "kind": "seeding",
                        "dlspeed": 0,
                        "upspeed": 1024,
                        "uploaded": 2048,
                        "size": 512**2,
                        "progress": 1.0,
                        "seeding_time": 3600,
                        "ratio": 1.2
                    },
                    {
                        "hash": "HB",
                        "site": "M-Team",
                        "state": "pausedUP",
                        "kind": "paused",
                        "dlspeed": 0,
                        "upspeed": 1024,
                        "uploaded": 2048,
                        "size": 512**2,
                        "progress": 1.0,
                        "seeding_time": 3600,
                        "ratio": 1.2
                    },
                ],
        }
    ]
    mgr = SimpleNamespace(
        status_snapshot=lambda: {
            "connected": True,
            "paused": False,
            "torrents": 2
        },
        state_file=state_file,
        data_dir=str(tmp_path),
        config=config,
        config_path=config_file,
        store=SimpleNamespace(groups=groups, by_hash={}, get=lambda h: None, server_state=None),
        client=None,
        # 命令唤醒(真实 manager 置位 _wake_event 让主循环立即消费); 此处记录调用供断言
        wake=lambda: wake_calls.append(1),
    )
    # 模块宿主替身(schema 端点的段认领由模块 sections() 派生, W4 级别表退役)
    # S17: 来源卡路由经 host.get("webui") 取「工具发现/拉起单点」(= 生产中 WebUIModule 的
    # 订阅客户端)。替身里照给真实 WebUIModule —— 惰性构造, 因为它依赖 mgr.web, 而 web
    # 门面在本函数下方才挂上; 其它名字沿用轻量假模块(sections 派生用)
    _stub_modules = [
        SimpleNamespace(name="webui", sections=lambda: ("web", )),
        SimpleNamespace(name="tracker", sections=lambda: ("trackers", )),
        SimpleNamespace(name="rules", sections=lambda: ("rules_config", "interval")),
    ]
    _lazy_modules = {}

    def _host_get(name):
        if name == "webui":
            if name not in _lazy_modules:
                from auto_qb.webui.module import WebUIModule
                _lazy_modules[name] = WebUIModule(mgr)
            return _lazy_modules[name]
        for m in _stub_modules:
            if m.name == name:
                return m
        return None

    mgr.host = SimpleNamespace(modules=lambda: _stub_modules, get=_host_get)
    # 详情端点的 HR 展示字段由 WebviewMixin 静态方法提供; stub 直接引用同一实现
    from auto_qb.core.qbmanager import QbManager

    # 命令投递经表现层门面(WebUIRuntime.post_command): post_command 与 consume_commands
    # 共用 runtime 自带的 commands 队列 —— 端点测试直投 mgr.web.commands, 断言仍然成立
    from auto_qb.webui import WebUIRuntime

    mgr.web = WebUIRuntime(mgr)
    # routes 走 web.* 新名口(plan 别名层处置 W1/W2): 替身数据挂门面命名空间,
    # 门面方法覆盖为读替身数据
    mgr.web.group_view = view
    mgr.web.flat_view = []
    mgr.web.traffic_view = {"state": "disabled", "periods": [], "history": [], "limit": {}}
    mgr.hr_view_fields = QbManager.hr_view_fields
    mgr._wake_calls = wake_calls  # 供端点测试断言"投递命令是否唤醒主循环"
    # 视图替身方法: routes 现调 web.ensure_view / web.ensure_state, 这里把门面方法指到替身数据上
    mgr.web.ensure_view = lambda: mgr.web.group_view

    def _ensure_group_state(rid, view=None, delta=False):
        # 与真实实现同形(plan 26-10-07-0414 S3 起 ensure_state 增 delta 协商参; 替身不模拟
        # 归约, 现有端点用例均不带 delta=1, 行为与历史全量形状一致)
        from auto_qb.webui.views import VIEW_ARRAYS

        updated = rid != mgr.web.group_view_ver
        state = {"rid": mgr.web.group_view_ver, "updated": updated}
        if updated:
            arrays = {
                "groups": mgr.web.group_view,
                "singles": [],  # 与真实 ensure_group_state 同形: singles 随 groups 同门控回传
                "shows": {
                    "list": [],
                    "unrecognized": []
                },
                "torrents": mgr.web.flat_view,  # 种子平铺视图同门控(与真实实现同形)
            }
            for k in (VIEW_ARRAYS.get(view) if view else None) or arrays:
                state[k] = arrays[k]
        return state

    mgr.web.ensure_state = _ensure_group_state
    return mgr


STATIC_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "auto_qb", "webui", "static"
)

# 全部 UI(皮肤)清单: 目录即 UI(static/<名>/index.html, 后端零注册表)。
# 新增皮肤 = 加一档, 全文件"成对改"守阵随本常量自动扩档; 单独点名的守阵(令牌对账/CSS 链接序)另行核对。
_UI_ALL = ("atlas", "prism", "console")


def _ui_manifest(ui):
    """解析 ui/index.html shell 里 <script type="application/json" id="tpl-manifest"> 清单

    清单是 boot.js 与守阵共用的单一来源(plans/26-09-26-2233 §5): parts = 模板分片(into: app|body,
    其余值为 #app 内自定义选择器落点, 方案A 停靠面板 26-10-03-0917 W1 起支持),
    scripts = 逻辑脚本加载顺序。缺清单/坏 JSON 直接断言红 —— shell 半残比假绿好。
    """
    shell = open(os.path.join(STATIC_ROOT, ui, "index.html"), encoding="utf-8").read()
    m = re.search(r'<script type="application/json" id="tpl-manifest">(.*?)</script>', shell, re.S)
    assert m, f"{ui}/index.html 缺 tpl-manifest 清单(拆分半途? 同步本守阵)"
    return json.loads(m.group(1))


def _ui_shell_inline(ui):
    """shell index.html 里 #app 的内联残余(登录遮罩区): `<div id="app" v-cloak>` 到 2 空格 `  </div>`"""
    lines = open(os.path.join(STATIC_ROOT, ui, "index.html"), encoding="utf-8").read().split("\n")
    try:
        open_i = lines.index('  <div id="app" v-cloak>')
    except ValueError:
        raise AssertionError(f"{ui}/index.html 缺 #app 容器(拆分半途? 同步本守阵)")
    closes = [i for i, ln in enumerate(lines) if ln == "  </div>"]
    assert len(closes) == 1, f"{ui}/index.html 的 #app 收口锚点(2 空格 `  </div>`)应恰有一处, 实测 {len(closes)}"
    return "\n".join(lines[open_i + 1:closes[0]])


def _ui_aggregate(ui):
    """拆分后模板聚合 = shell 内联段 + 分片按清单序拼接 —— 拆分后守阵只认聚合, 不认单分片

    26-09-26 模板分片(plans/26-09-26-2233 W1)后, 原 2555/2613 行 index.html 变成 ≤200 行 shell
    + tpl/*.html; 旧守阵继续读 index.html 会整体假绿(内容都搬去了分片)。顺序 = boot 注入序
    (app 桶在 shell 内联段之后按清单序进 #app, body 桶进 body), 与运行时 Vue 编译输入一致。
    单看任何一个分片都会漏跨分片的结构(如批量菜单的 template 链), 所以一律走这里。
    """
    chunks = [_ui_shell_inline(ui)]
    for part in _ui_manifest(ui)["parts"]:
        text = open(_tpl_path(part["src"], ui), encoding="utf-8").read()
        chunks.append(text.rstrip("\n"))
    return "\n".join(chunks)


def _ui_css_files(ui):
    """ui shell <head> 里声明的本 UI CSS 链接顺序(link 顺序即级联序) —— CSS 拆分后的加载序单一来源"""
    shell = open(os.path.join(STATIC_ROOT, ui, "index.html"), encoding="utf-8").read()
    hrefs = re.findall(r'<link rel="stylesheet" href="(/%s/[^"]+\.css)"' % ui, shell)
    assert hrefs, f"{ui} shell head 缺本 UI 的 CSS 链接"
    return [os.path.join(STATIC_ROOT, *h.lstrip("/").split("/")) for h in hrefs]


def _ui_css_aggregate(ui):
    """UI CSS 聚合(按 shell link 序拼接) —— CSS 分层拆分后守阵只认聚合, 级联序 = link 序

    26-09-27 atlas/style.css 分层拆分(W2)后, 旧守阵继续单读 style.css 会假绿(规则搬进了 css/)。
    切分是连续字节切片(级联序不变), 聚合与拆分前逐字节等价。

    注意: 本函数**只含本皮肤自己的 CSS**。三皮肤共用层的规则(shared/console_hub.css 等)
    不在里面 —— 需要「这套 UI 最终生效的样式面」时用 _ui_css_effective。
    """
    return "\n".join(open(p, encoding="utf-8").read() for p in _ui_css_files(ui))


def _ui_css_effective(ui):
    """UI 最终生效的样式面 = 本皮肤聚合 + 三皮肤共用层(shared/*.css), 仍按 link 序

    issue 26-10-20-2231 把逐字节相同的规则族(qb-tabs / drawer-tabs / 弹窗语义配色 /
    HR 表① 件)收敛进 shared/console_hub.css 后, 这些规则**只在共用层存在一份**。
    此时继续用 _ui_css_aggregate 断言「三皮肤各有一份」会恒红, 而放宽成「共用层有就算过」
    又会把「某皮肤真漏了」也放过 —— 所以判据要落在**该皮肤实际吃到的级联面**上:
    共用层在三皮肤 shell 里都挂且排在各皮肤 CSS 之后(级联序即收敛点), 故聚合后接共用层
    与浏览器真实生效面一致。
    """
    shell = open(os.path.join(STATIC_ROOT, ui, "index.html"), encoding="utf-8").read()
    shared = [
        os.path.join(STATIC_ROOT,
                     *h.lstrip("/").split("/"))
        for h in re.findall(r'<link rel="stylesheet" href="(/shared/[^"]+\.css)"', shell)
    ]
    return "\n".join(open(p, encoding="utf-8").read() for p in _ui_css_files(ui) + shared)


def _app_bundle_files():
    """app.js 及它按域拆分出的片段文件, 按 prism shell 的 tpl-manifest **加载顺序**返回 [(path, rel)]

    (2026-09-20 app.js 拆分: 片段以 window.AQB_* 全局 mixin 注入 **同一个** Vue 实例, 逻辑上仍是一份
     代码 —— 故"跨文件的不变量"必须按整包看: 只扫 app.js 会把搬走的那半漏掉。实测拆完当场报
     「找不到 _optimisticSettled 调用点」, 而它只是挪到了 commands.js, 功能没丢。)
     顺序取自清单而非文件名排序 —— 片段必须排在 app.js **之前**(app.js 末尾要读 window.AQB_*);
     26-09-26 模板分片后 <script> 标签从 HTML 搬进了 tpl-manifest 的 scripts 数组, 由 boot.js 依序放行。
    """
    out = []
    for src in _ui_manifest("prism")["scripts"]:
        if "/vendor/" in src:
            continue
        rel = src.lstrip("/")
        out.append((os.path.join(STATIC_ROOT, rel), rel))
    return out


def _app_bundle_text():
    """app.js + 内核片段(清单序)聚合文本 —— W2b 拆分后成员按域存放, 守阵找成员一律读聚合"""
    return "\n".join(open(p, encoding="utf-8").read() for p, _rel in _app_bundle_files())


def _tpl_path(src, ui):
    """清单分片 src -> 盘上路径: /shared/... = 单一语义源(收敛后唯一形态); 相对路径按 <ui>/ 解析(兼容)"""
    if src.startswith("/"):
        return os.path.join(STATIC_ROOT, *src.lstrip("/").split("/"))
    return os.path.join(STATIC_ROOT, ui, *src.split("/"))


# ---- qB 口径流量图三 GET 端点(plan 26-10-03-0946 §08 P4; 装配单点 server/traffic_qb.py, 纯函数口径 core/traffic_grid.py) ----


def _enable_qb_traffic(mgr, **kw):
    """用例侧启用 qb_traffic(真实 QbTraffic 段, 缺省键取设计缺省; kw 可覆盖任意键)"""
    from auto_qb.config import QbTraffic

    mgr.config.qb_traffic = QbTraffic(**{"enabled": True, **kw})
    return mgr.config.qb_traffic


def _qb_v4(mgr):
    """指向替身 data_dir(tmp_path)的 v4 存储层: 用例经真实写路径造 qb-traffic-v4/ 天文件与 agg.dat"""
    from auto_qb.core.traffic_store import TrafficV4Store

    return TrafficV4Store(mgr.config.data_dir)


# ---- HR 两张表的行键面单点(闭集断言: test_hr_status 与 test_web_hr 同引此处; 后端加字段只改这一处) ----
# 字面量刻意写在**测试侧**、不从 dataclass 派生: 派生会让「后端加字段」与「期望键面」同步漂移, 守阵形同虚设。
# 正确姿势 = 改 prod 的 dataclass/装配 -> 两条用例同时红 -> 在此改一次 -> 两处同时绿(单点声明, 语义不变)。
HISTORY_ROW_KEYS = frozenset(
    {
        "ts",
        "ts_text",
        "site",
        "kind",
        "kind_text",
        "trigger",
        "trigger_text",
        "action",
        "result_text",
        "result_tone",
        "reason",
        "reason_kind",
        "pages",
        "rows",
        "torrents_ok",
        "torrents_fail",
        "verified",
        "elapsed_s",
        "elapsed_text",
        "lanes",
        "notes",
        "by",
    }
)
# EntryDetail.to_dict 面(entry_details 导出; 计划 26-10-01-2216 §3 P0+P1 全集)
ENTRY_ROW_KEYS = frozenset(
    {
        "tid",
        "dl_id",
        "name",
        "lane",
        "lane_text",
        "uploaded_bytes",
        "downloaded_bytes",
        "ratio",
        "need_seed_seconds",
        "need_seed_text",
        "infohash_v1",
        "infohash_v2",
        "verified_ts",
        "verified_source",
        "verified_source_text",
        "done_iso",
        "active",
        "missing_streak",
        "first_seen",
        "last_seen",
    }
)
# 响应层多一个只读标记: mark_local_present 的 join 追加(server/routes/hr.py, 计划 26-10-02-1936 §3.3 决策点③a)
ENTRY_ROW_KEYS_API = ENTRY_ROW_KEYS | {"local_present"}
# history 行内嵌的 lane 子键面(HistoryLane.to_dict; 拉取历史展开小表的一行)
HISTORY_LANE_KEYS = frozenset({"lane", "lane_text", "status", "status_text", "pages", "rows", "detail"})
# 站点级快照面(SiteStatus.to_dict; WebUI 表② 的 kv 行与摘要层)
SITE_STATUS_KEYS = frozenset(
    {
        "site",
        "enabled",
        "listing",
        "now",
        "channel_state",
        "channel_text",
        "revision",
        "file_path",
        "read_error",
        "fetched_at",
        "healthy_ts",
        "expires_at",
        "next_wave_at",
        "refresh_interval",
        "idle_mode",
        "stale",
        "fresh_text",
        "lanes",
        "lanes_text",
        "releases_enabled",
        "zero_rows",
        "empty_confirmed",
        "count_attested_empty",
        "retention_text",
        "notes",
        "writer_instance",
        "writer_heartbeat",
        "index_total",
        "index_active",
        "lane_counts",
        "pending_infohash",
        "backfill_ratio",
        "managed",
        "keys",
        "downloaded",
        "fails",
        "verified",
        "observing",
        "quota",
        "allow_window",
        "blocking",
    }
)


def _hr_status_env(mgr, tmp_path, *, complete=True, pages=None):
    """给 web 替身挂上一个**真** HR 服务(跑过一轮), 返回它 —— 站点文件与视图都是真的

    替身 manager 的 config 是 SimpleNamespace(没有 hr_check 段), 所以这里显式补上, 并挂一个
    `hr` 门面替身(真门面需要端点/线程, 与本端点的只读口径无关)。
    pages 可整组替换三档页面(种子明细端点的空站点用例用全零行页)。
    """
    from types import SimpleNamespace
    import time

    from auto_qb.hr.runtime import HrRuntimeStatus, HrRefreshService
    from auto_qb.config.models import SiteHrCheckConfig
    from hr_helpers import Clock, FakeFetcher, global_conf, myhr_page, row, site_conf, torrent_blob

    # !假时钟要落在**真实当前时间**附近: 端点用真 `time.time()` 取 now, 若测试时钟是
    # hr_helpers 默认的 2023 基准, 数据必然被判「已过有效期」—— 测的就不是想测的东西了
    clock = Clock(start=time.time())
    if pages is None:
        pages = {"A": myhr_page([row(101)]), "B": myhr_page([row(101)]), "C": myhr_page([row(101)])}
        if not complete:
            pages["C"] = "<html><body>没有表格</body></html>"
    svc = HrRefreshService(
        data_dir=str(tmp_path),
        global_conf=global_conf(),
        site_confs={"HHan": site_conf()},
        fetcher=FakeFetcher(pages, {101: torrent_blob("t101.bin")}),
        owner="tester",
        now_fn=clock,
    )
    svc.refresh_site("HHan")
    mgr.config.hr_check = HrCheckConfig(enabled=True)
    # 写类路由(confirm-empty / refresh)按 trackers.*.hr_check 判「站点已接入」——替身条目补真模型
    mgr.config.trackers["HHan"].hr_check = SiteHrCheckConfig(enabled=True, tracker="HHan")
    mgr.hr = SimpleNamespace(
        service=svc,
        status=lambda: HrRuntimeStatus(
            enabled=True,
            sites=("HHan", ),
            fetch_enabled=True,
            worker_running=True,
            poll_interval=300.0,
            sites_dir=str(tmp_path / "hr"),
            writer="tester",
            channel=None,
            note="",
        ),
    )
    return svc


# ---------- Web 命令执行(主循环侧 _drain_web_commands) ----------


def _make_grouped_manager(td):
    """构造两个同文件列表的种子并归组(供 Web 命令执行测试); 返回 (mgr, client, key)"""
    from helpers import FakeClient, FakeTorrent, _fake_file, make_manager, seed_store

    mgr = make_manager(os.path.join(td, "state.json"))
    client = FakeClient()
    mgr.client = client
    files = [_fake_file("movie.mkv", 100)]
    client.files_map["HA"] = files
    client.files_map["HB"] = files
    tors = [
        FakeTorrent(hash="HA", name="Show", save_path=r"R:\Downloads"),
        FakeTorrent(hash="HB", name="Show", save_path=r"R:\Downloads"),
    ]
    # !**同时**灌进 FakeClient: 真值改走 `torrents/info` 直查(不再读同步快照),
    #   直查查的是 qB 客户端里的种子 —— 只 seed store 的话桩里查不到, 与真机不符。
    for t in tors:
        client.torrents[t.hash] = t
    seed_store(mgr, tors)
    mgr.host.get("grouping")._assign_new_torrent("HA")
    mgr.host.get("grouping")._assign_new_torrent("HB")
    return mgr, client, mgr.store.member_to_key["HA"]


def _iter_api_routes(routes):
    """展平 include_router 的注册结果: 本环境 FastAPI 把路由包在 _IncludedRouter 里,
    不再展开为平铺 APIRoute —— 按域 Router 拆分后必须递归下钻才能清点到全部路由。"""
    from fastapi.routing import APIRoute

    for r in routes:
        if isinstance(r, APIRoute):
            yield r
            continue
        for attr in ("original_router", "router"):
            sub = getattr(r, attr, None)
            if sub is not None and hasattr(sub, "routes"):
                yield from _iter_api_routes(sub.routes)
                break


# ---------- v3 活尾合流(S6 验收追加, 2026-10-05) ----------


def _attach_live_tail_host(mgr, tails):
    """manager 替身挂模块宿主最小桩: host.get("qb_traffic") -> 带 live_tail 的模块桩
    (真 manager 经 QbManager.host 持 ModuleHost, 端点 getattr 防御取用)"""
    from types import SimpleNamespace

    mgr.host = SimpleNamespace(get=lambda name: SimpleNamespace(live_tail=tails))


# ---------- 增量时间线装库(issue 26-10-21-0502: 原 test_webui_delta / _mirror 各一份) ----------


def make_store(*hashes, state: str = "stalledUP") -> TorrentStore:
    """真实 TorrentStore 装库(FakeClient/FakeTorrent 范式同 test_sync), 随后清掉装库轮的
    S1 快照与 view_changed —— 基线不进被测时间线窗口, 各用例从干净基线驱动

    剧集形命名: parse_release 解析为 episode(带 key) —— 不触发 _build_shows_view 的文件兑底
    pending 标记(名称解析不出剧键时构建器会 mark_shows_pending(True), 与 c 场景的转换拍
    断言互相干扰)。
    """
    from helpers import FakeClient, FakeTorrent

    client = FakeClient()
    for h in hashes:
        client.torrents[h] = FakeTorrent(hash=h, name=f"Show.{h}.S01E01.720p.x264-GRP", state=state)
    store = TorrentStore(client)
    store.apply_sync(QbApi(client, store))
    store.last_added = []
    store.last_removed = []
    store.delta_fields = {}
    store.consume_view_changed()
    return store
