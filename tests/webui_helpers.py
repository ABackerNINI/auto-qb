"""webui_helpers 共享件: WEB UI 后端测试拆分后的跨文件辅助与常量(原单文件已拆为 16 个平铺模块, 见 tasks/26-10-08-backend-test-web-split.md)
"""
import json
import logging
import os
import re
import time
from types import SimpleNamespace

from auto_qb.config.models import HrCheckConfig
from auto_qb.infra.utils import encode_group_key
from auto_qb.webui.runtime import WebUIRuntime

KEY = ("R:/seeds", ("a.mkv", "b.mkv"))


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
        skip_check_menu=True
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
    mgr.host = SimpleNamespace(
        modules=lambda: [
            SimpleNamespace(name="webui", sections=lambda: ("web", )),
            SimpleNamespace(name="tracker", sections=lambda: ("trackers", )),
            SimpleNamespace(name="rules", sections=lambda: ("rules_config", "interval")),
        ]
    )
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
    """
    return "\n".join(open(p, encoding="utf-8").read() for p in _ui_css_files(ui))


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


# ==================== P1 覆盖率提升轮: webui 运行时与命令长尾 ====================


class _ListLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


class module_log:
    """挂在指定模块 logger 上的自足采集(pitfalls/testing/log-capture: 禁 caplog)"""
    def __init__(self, name, level=logging.DEBUG):
        self._handler = _ListLogHandler()
        self._logger = logging.getLogger(name)
        self._level = level

    def __enter__(self):
        self._old_level, self._old_propagate = self._logger.level, self._logger.propagate
        self._logger.addHandler(self._handler)
        self._logger.setLevel(self._level)
        self._logger.propagate = False
        return self._handler.messages

    def __exit__(self, *exc):
        self._logger.removeHandler(self._handler)
        self._logger.setLevel(self._old_level)
        self._logger.propagate = self._old_propagate
        return False


# ---------- v3 活尾合流(S6 验收追加, 2026-10-05) ----------


def _attach_live_tail_host(mgr, tails):
    """manager 替身挂模块宿主最小桩: host.get("qb_traffic") -> 带 live_tail 的模块桩
    (真 manager 经 QbManager.host 持 ModuleHost, 端点 getattr 防御取用)"""
    from types import SimpleNamespace

    mgr.host = SimpleNamespace(get=lambda name: SimpleNamespace(live_tail=tails))
