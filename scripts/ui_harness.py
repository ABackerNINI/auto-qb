"""WEB UI 浏览器冒烟桩服务(dev-only): 真实 create_app + 合成种子, 不连 qB

为什么需要它
------------
没有可用的浏览器自动化就跑不了这类验证, 而本项目有一整类改动**单测根本测不到**:
(历史背景: 写本脚本时 `agent-browser` 插件还是 1.0.0, 它的 SessionStart hook 在 Windows 上
直接判 `WINDIR` 打印"不支持 Windows"并退出, 连 CLI 都不装 ⇒ 当时只能自己搭。1.3.0 起该插件
已支持 Windows x64; 但本脚本走的是 Playwright, 与它无关, 不因此改变做法。
环境细节见 `memory-bank/techContext.md`「浏览器冒烟环境 (Playwright)」。)
乐观 UI 的半透明与失败回滚、按视图回传后切视图、表头同步是否还在每帧强制布局、
行窗口化后滚动是否跳动 —— 这些都属于"pytest 全绿但界面废掉"的故障形态(见
`test_webui_static_skins.py::test_frontend_static_bundle_health` 的同类守阵思路: 静态能查的静态查,
查不了的只能真跑浏览器)。

本脚本用**真实的** `auto_qb.webui.create_app` 起服务(端点/鉴权/静态挂载全是生产代码),
只把 manager 换成"灌了合成种子的真实 QbManager + FakeClient" —— 因此前端拿到的
响应体与真机同构(字段集/版本号/rid 门控均一致), 只是数据是人造的。

用法
----
    uv run python scripts/ui_harness.py --torrents 3000 --port 8099
    # 浏览器侧断言已迁 e2e 轨: 桩服务由它自动起(8137), 模式走 E2E_* env(见 e2e/harness.mjs),
    # 命令 `commands run dev.e2e`; 手看页面直接开 http://127.0.0.1:8099/prism/

参数
----
    --torrents N   合成种子总数(默认 1500; 用 3000 复现大库)
    --groups G     前 G×2 个种子两两归组(默认 200 组), 其余为未归组单种子
    --port P       监听端口(默认 8099)
    --no-groups    不建分组(纯平铺, 测种子页窗口化最快)
    --cmd-result   ok|error|hang(默认 ok): 兜底命令泵给每条命令的回执 ——
                   error 用于验证 P0-3 乐观 UI 的**失败回滚**, hang 用于验证 3s 回落真值
    --skip-check-menu on|off(默认 on): web.skip_check_menu 桩值两态 ——
                   on 走「跳检…」菜单项/确认链断言(计划 26-10-02-1955 W3/W5),
                   off 验 fail-closed 门控(菜单两处都不渲染; 配套 e2e 轮 E2E_SKIP_CHECK=off)
    --hr-scene on|empty|off(默认 on): HR 在线核实桩场景(计划 26-10-04-0312 S5) ——
                   on 灌五形态拉取历史(表③, HHan/HDSky 跨站时间轴), empty 验空态,
                   off 验未启用态; 配套 e2e 轮 E2E_HR_SCENE(仅 on 跑表③断言组, e2e/hr-history.spec.mjs)

注意
----
* 仅开发期使用, 不参与打包; 数据全在内存 + 临时 state 文件, 关闭即弃。
* 鉴权走 `skip_local_verify`(本机免密钥), 浏览器不需要带 token。
  !正因如此 `--host` **只接受回环地址**(127.0.0.0/8 / ::1 / localhost) —— 绑 0.0.0.0
  等于把一个免鉴权的 WEB UI 交给整个局域网(合成数据也含配置结构), 直接拒绝启动。
"""
import argparse
import ipaddress
import os
import queue
import sys
import tempfile
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from auto_qb.config import WebConfig  # noqa: E402
from auto_qb.webui import create_app  # noqa: E402
from tests.helpers import FakeClient, FakeTorrent, FakeTracker, make_manager, seed_store  # noqa: E402

_STATES = ["stalledUP", "uploading", "downloading", "pausedUP", "pausedDL", "stalledDL", "checkingUP", "errored"]
_SIZES = [2 * 1024**3, 8 * 1024**3, 25 * 1024**3, 60 * 1024**3]


def _make_torrents(count: int, site_conf):
    """合成种子: 名字/大小/状态/进度轮转, 保证每行列宽不整齐(更接近真机)"""
    out = []
    for i in range(count):
        size = _SIZES[i % len(_SIZES)]
        state = _STATES[i % len(_STATES)]
        done = i % 3 != 0  # 1/3 未完成, 让进度条/ETA 列有内容
        out.append(
            FakeTorrent(
                hash=f"{i:040x}",
                name=f"Some.Show.S01E{(i % 24) + 1:02d}.1080p.WEB-DL.x265-GROUP{i}",
                size=size,
                total_size=size,
                state=state,
                progress=1.0 if done else (i % 10) / 10,
                downloaded=size if done else size // 3,
                uploaded=int(size * ((i % 20) / 10)),
                dlspeed=0 if done else 1024 * (i % 900),
                upspeed=1024 * (i % 400),
                seeding_time=(i % 400) * 3600,
                ratio=(i % 30) / 10,
                added_on=1700000000 + i * 37,
                # magnet: 真实 qB 恒有(合成名 + 40 位 hash)。**必须给** —— 前端"复制磁力"
                # 要按需取详情读它(BUG-9), 桩里留空则那条断言退化成"永远提示没有 magnet"。
                magnet_uri=f"magnet:?xt=urn:btih:{i:040x}&dn=Some.Show.S01E{(i % 24) + 1:02d}",
                category=["", "Movies", "TV", "Anime"][i % 4],
                tags=",".join([t for k, t in enumerate(["HHan", "seed-3D", "low-ratio"]) if (i >> k) & 1]),
                tracker=f"https://tracker.hhanclub.net/announce/{i}",
                num_seeds=i % 40,
                num_leechs=i % 7,
                tracker_conf=site_conf,
            )
        )
    return out


# 合成 peer 场景(轮转取用): flags / 速度 / 进度 / 客户端 / 地域多样性 —— 覆盖前端 peers 页签
# (经典表 + 变体 07/08/09)的全部派生分支: 方向五桶(U/D/u/K/握手未完成)、吸血嫌疑启发式
# (迅雷/XL)、内网(192.168/10.)与公网/IPv6、速度与进度的零值与非零值、files 渐进字段。
# 字段集与 qB sync/torrentPeers 的 peer_info 同形(缺省字段渐进省略: country_code/connection/files)。
_PEER_SCENES = [
    # client, flags, ip, port, progress, dlspeed, upspeed, relevance, country_code, connection, files
    ("qBittorrent 5.0.2", "U K E", "203.0.113.7", 51413, 1.0, 0, 512 * 1024, 1.0, "DE", "BT", None),
    ("Transmission 4.0.5", "D E", "198.51.100.23", 6881, 0.62, 256 * 1024, 0, 0.31, "US", "BT", None),
    (
        "libtorrent 2.0.9", "U D", "192.168.1.42", 6881, 0.85, 128 * 1024, 64 * 1024, 0.72, "", "uTP",
        "Some.Show.S01E01.mkv"
    ),
    ("Deluge 2.1.1", "K", "2001:db8::1", 51413, 1.0, 0, 0, 1.0, "FR", "BT", None),
    ("迅雷 11.0.8", "D u", "203.0.113.99", 40000, 0.12, 480 * 1024, 0, 0.09, "CN", "BT", None),
    ("XL0012", "?", "10.0.0.5", 6881, 0.0, 0, 0, 0.0, "", "uTP", None),
    ("qBittorrent 4.6.7", "U K E P", "198.51.100.88", 16881, 1.0, 0, 220 * 1024, 1.0, "NL", "BT", None),
]


def _make_peers_response(i: int) -> dict:
    """单种子的合成 sync/torrentPeers 整包(与 qB 响应同形)

    !peers 用 **dict**(以 "ip:port" 为键)而非数组 —— 真 qB 恒为 dict, 前端 drawerPeerRows 做
    dict/数组双形态归一; 桩若图省事给数组, 归一的 dict 分支就永远测不到(口径同 tests/helpers.py
    FakeClient.sync_torrent_peers)。对端数与组合按种子序号 i 轮转(1~7 个, 首尾相接地错开), 让不同
    种子拿到不同的 flags/速度/进度组合 —— 单种全量轮转只覆盖一种形态, 冒烟就会"自以为测过"
    (见 pitfalls/testing/stubs-sim.md)。
    """
    n = 1 + (i % len(_PEER_SCENES))
    peers = {}
    for k in range(n):
        scene = _PEER_SCENES[(i + k) % len(_PEER_SCENES)]
        client, flags, ip, port, progress, dlspeed, upspeed, relevance, cc, conn, files = scene
        peer = {
            "ip": ip,
            "port": port,
            "client": client,
            "flags": flags,
            "progress": progress,
            "dlspeed": dlspeed,
            "upspeed": upspeed,
            "downloaded": int(progress * 4 * 1024**3),
            "uploaded": (k + 1) * 128 * 1024**2,
            "relevance": relevance,
        }
        if cc:
            peer["country_code"] = cc
        if conn:
            peer["connection"] = conn
        if files:
            peer["files"] = files
        peers[f"{ip}:{port}"] = peer
    return {"rid": 0, "full_update": True, "peers": peers, "peers_removed": {}}


# 合成 tracker 站点(逐种子轮转, 让不同行的 host 可辨)
_TRACKER_SITES = ("tracker.hhanclub.net", "tracker.hdsky.me", "tracker.pt.example")


def _make_trackers_response(i: int) -> list:
    """单种子的合成 /torrents/trackers 列表(与 **qB 5.2+** 同形, 含 per-tracker 汇报时间)

    06 变体逐行汇报倒计时按 P-02 升级为真 per-tracker 口径(行级 next_announce, epoch 秒) ——
    桩若只回单条无 next_announce 的 tracker(FakeClient 默认), 冒烟/截图只走到回退分支, 真口径
    从未被渲染过。这里固定 3 条 real tracker, 前两条 status=2(正常), 第三条按种子序号奇偶给
    4(失败)/3(更新中) —— 保证**每个种子恒有 2 行非「更新中」**(真口径倒计时可渲染且互不相同),
    同时覆盖 06 的 正常/失败/更新中 三档与「仅看异常」分桶。字段与 qB 5.2.3 getTrackers 同名
    (见 reports/26-10-05-0854 §4.1), 不含虚拟条目。next_announce 自 now+30min 起逐行 +30min
    (30/60/90 分钟), 倒计时可辨且余量足够长(同一桩服务连跑 1h 内两行仍互不相同, 不因钳到 0 而撞值)。
    """
    now = int(time.time())
    third = 3 if (i % 2) else 4
    out = []
    for k, status in enumerate((2, 2, third)):
        site = _TRACKER_SITES[(i + k) % len(_TRACKER_SITES)]
        na = now + 1800 + k * 1800
        out.append(
            {
                "url":
                    f"https://{site}/announce.php",
                "status":
                    status,
                "tier":
                    k,
                "num_peers":
                    4 + k,
                "num_seeds":
                    10 + i + k,
                "num_complete":
                    10 + i + k,
                "num_leeches":
                    2 + k,
                "num_incomplete":
                    2 + k,
                "num_downloaded":
                    50 + i * 3 + k,
                "msg":
                    "" if status == 2 else ("Working" if status == 3 else "torrent not registered with this tracker"),
                "next_announce":
                    na,
                "min_announce":
                    na,
            }
        )
    return out


# 桩服务"真改状态"用的目标状态(与后端 _state_kind 的口径一致: pausedDL -> kind=paused,
# uploading -> seeding, downloading -> downloading) —— 前端乐观补丁写的就是这几个 kind。
_PAUSED_STATE = "pausedDL"
_RESUME_DONE = "uploading"
_RESUME_TODO = "downloading"
# !刻意让**回执先到、状态后改**(复刻真机竞态: 服务端 P0-5 补刷新在回执**之后**才跑,
# 见 webui/commands.py)。前端"回执后立刻拉真值"第一次会扑空(rid 还没变),
# 必须靠退避重试才拿得到 —— 这段延迟就是为了让重试逻辑被测到(issue 26-09-19-2024)。
_TRUTH_DELAY = 0.12


def _inject_hr_site(torrents):
    """--hr-site: 按种子轮转注入**真实 HrJudgement**(站点接入形态) —— 冒烟的既知盲区:

    FakeTorrent.hr_judgement 恒 None(替身没接判定桥), 故桩冒烟从头到尾只渲染过
    safety_display 的 judged=None 分支(本地兜底/不适用); 站点在线判定的 hr_safety_src
    token 与详情抽屉 hrStateLine 短语在前端从未被真渲染过。
    这里 monkeypatch 每个种子的 hr_judgement, 按 v3 四行判定表逐行轮转 7 场景:
    行1 考察中 / 行2 终态 B·C·D / 行3 放行记录 / 行4 本地兜底 / judged=None 未接入回落。
    身份与 facts.lane 强耦合(真判定里档位决定身份, resolve_identity 各行的 reason 原文直抄),
    站点侧达标结论按 HrEntry.satisfied_verdict 的档位即结论口径给(A/C=False, B=True, D=None)。
    只构造真 dataclass, 不接取数链 —— _hr_view_fields 消费的就是这些对象, 与真机同构。
    """
    from auto_qb.hr.model import (
        LANE_EXEMPT,
        LANE_SATISFIED,
        LANE_SCOPE,
        LANE_UNSATISFIED,
        SOURCE_EXEMPT,
        SOURCE_NOT_LISTED,
        SOURCE_SATISFIED,
    )
    from auto_qb.hr.resolve import HrIdentity, HrJudgement, HrSiteFacts

    # (identity, lane, reason, released_src, site_satisfied); lane="" ⇒ 命中行缺席, facts=None
    _SCENES = [
        (HrIdentity.HR, LANE_SCOPE, "清单命中·考察中(档位 A)", "", False),
        (HrIdentity.RELEASED, LANE_SATISFIED, "清单命中·已达标(B, 终态放行)", SOURCE_SATISFIED, True),
        (HrIdentity.RELEASED, LANE_UNSATISFIED, "清单命中·未达标(C, 考核结论已定, 终态放行)", "", False),
        (HrIdentity.RELEASED, LANE_EXEMPT, "清单命中·已免罪(D, 终态放行)", SOURCE_EXEMPT, None),
        (HrIdentity.RELEASED, "", "放行记录(覆盖范围内未列出)", SOURCE_NOT_LISTED, None),
        (HrIdentity.NO_EVIDENCE, "", "无有效站点证据(本地判据兜底)", "", None),
    ]

    def _mk(i):
        if i % 7 == 6:
            return None  # 站点未接入: 回落 judged=None(本地兜底口径)
        identity, lane, reason, released_src, site_satisfied = _SCENES[i % 7]
        facts = HrSiteFacts(
            lane=lane,
            need_seed_seconds=3600 * (i % 48),
            remain_seconds=3600 * (i % 12),
            ratio=(i % 30) / 10,
            downloaded_bytes=None,
        ) if lane else None
        return HrJudgement(
            identity=identity,
            reason=reason,
            site_satisfied=site_satisfied,
            site="BTSchool",
            facts=facts,
            released_src=released_src,
        )

    for i, tor in enumerate(torrents):
        tor.hr_judgement = lambda i=i: _mk(i)  # 实例级覆盖: 真记录该方法无参


def _inject_hr_history(mgr, data_dir: str, scene: str):
    """--hr-scene: HR「站点状态」块与拉取历史表③(计划 26-10-04-0312)的桩场景

    三态(冒烟的既知盲区与 --hr-site 同源: 桩 manager 没有 HR 取数线程, /api/hr/* 全族
    端点此前在冒烟里只能走到「未启用」空态, 启用态 / 表③ 时间轴从未被真浏览器渲染过):
      on    启用 + 五形态历史(默认): 完成(ok) / 部分·截断(warn) / 拦下·未到时刻(dim,
            defer) / 通道不可用(err) / 对账(blue) 各一条, 跨两站(HHan + HDSky)合并成
            时间轴; 完成行带 A/B/C 三档 lanes 快照 = 「行展开明细子行」的数据面。
            五形态的 action/kind/trigger 字面量逐一对齐 service 记录器的真实写点
            (refreshed/partial/waiting/no-channel/confirm-empty), 不凭空造形态。
      empty 启用 + 零历史: 空态文案(「最近还没有拉取记录」)。
      off   未启用: 保持 FakeConfig 默认(hr_check.enabled=False), /api/hr/status 回
            enabled=false, 前端站点状态块与表③ 段都显示未启用文案。

    保真口径: 只灌 HrHistoryEvent **输入**, 22 键人话行(徽章色档/耗时文案/档位人话)
    全部经生产 hr.status.history_rows 现算 —— 桩不复制展示层的映射逻辑(替身漂移 =
    自以为在测, 见 pitfalls/testing/stubs-sim.md)。HDSky 除进 service 的 site_confs
    外, 还要在 config.trackers 补一个**绑定壳**(见下方站点绑定段): 表③ 是跨站合并
    时间轴, 站点 chips 需要第二个站才能目检; 种子行的站点匹配不受影响 —— 行 site 取
    rec.tracker_conf(合成种子的 tracker_conf 恒指 HHan 对象), HDSky 壳无任何种子引用。
    """
    from types import SimpleNamespace

    from auto_qb.config.models import HrCheckConfig, SiteHrCheckConfig
    from auto_qb.hr.fetcher import NullFetcher
    from auto_qb.hr.model import HrHistoryEvent
    from auto_qb.hr.runtime import HrRuntimeStatus
    from auto_qb.hr.service import HrRefreshService

    if scene == "off":
        return  # 未启用态: 配置保持默认关, 端点回 enabled=false(前端显示未启用文案)

    mgr.config.hr_check = HrCheckConfig(enabled=True)
    svc = HrRefreshService(
        data_dir=data_dir,
        global_conf=mgr.config.hr_check,
        site_confs={
            "HHan": SiteHrCheckConfig(enabled=True, tracker="HHan"),
            "HDSky": SiteHrCheckConfig(enabled=True, tracker="HDSky"),
        },
        fetcher=NullFetcher("桩服务不执行取数"),
        owner="harness",
        allow_fetch=False,
    )
    if scene == "on":
        now = time.time()
        events = {
            "HHan":
                [
                    # 完成(ok) + lanes 多档可展开行: A/B/C 三档快照(status=ok 本波有效),
                    # 字段抄 _append_history 的 snapshot 口径(lane/status/pages/rows/detail)
                    HrHistoryEvent(
                        ts=now - 300,
                        kind="wave",
                        trigger="auto",
                        action="refreshed",
                        reason="覆盖完成(A 全深度, B/C 命中本地全集)",
                        pages=6,
                        rows=214,
                        torrents_ok=3,
                        torrents_fail=0,
                        verified=1,
                        elapsed_s=42.6,
                        lanes=[
                            {
                                "lane": "A",
                                "status": "ok",
                                "pages": 3,
                                "rows": 96,
                                "detail": "全深度翻完"
                            },
                            {
                                "lane": "B",
                                "status": "ok",
                                "pages": 2,
                                "rows": 78,
                                "detail": "命中本地全集"
                            },
                            {
                                "lane": "C",
                                "status": "ok",
                                "pages": 1,
                                "rows": 40,
                                "detail": "命中本地全集"
                            },
                        ],
                        notes=["B/C 档第 1 页即命中本地全集, 提前收档"],
                        by="harness",
                    ),
                    # 部分·截断(warn): 预算/页数上限截断, 截断点之前的数据仍有效
                    HrHistoryEvent(
                        ts=now - 1900,
                        kind="wave",
                        trigger="auto",
                        action="partial",
                        reason="达到单波页数上限(30), A 档截断",
                        pages=4,
                        rows=118,
                        torrents_ok=1,
                        torrents_fail=0,
                        verified=0,
                        elapsed_s=28.1,
                        lanes=[{
                            "lane": "A",
                            "status": "ok",
                            "pages": 4,
                            "rows": 118,
                            "detail": "达到单波页数上限截断(截断点之前有效)"
                        }],
                        by="harness",
                    ),
                    # 通道不可用(err): HrChannelUnavailable 波终态(还没碰到任何档位, lanes 空)
                    HrHistoryEvent(
                        ts=now - 4900,
                        kind="wave",
                        trigger="auto",
                        action="no-channel",
                        reason="扩展未连接(静默 184s)",
                        elapsed_s=0.4,
                        by="harness",
                    ),
                ],
            "HDSky":
                [
                    # 拦下·未到时刻(dim): defer(立即拉取被频控闸拦下; 记录器口径
                    # kind=defer + trigger=manual + action=waiting, 计数字段全 0)
                    HrHistoryEvent(
                        ts=now - 3400,
                        kind="defer",
                        trigger="manual",
                        action="waiting",
                        reason="未到可取时刻(min_interval, 还差 812s)",
                        by="harness",
                    ),
                    # 对账(blue): confirm_empty 事件(action=confirm-empty 本就不在徽章表内,
                    # kind 特判优先 —— run_hr_confirm_empty 的原话 reason 直抄)
                    HrHistoryEvent(
                        ts=now - 6600,
                        kind="confirm_empty",
                        trigger="confirm",
                        action="confirm-empty",
                        reason="人工对账: 确认账号 HR 清单为空(--hr-confirm-empty), 零行波恢复签发放行, 非零行自动失效",
                        by="harness",
                    ),
                ],
        }
        for site, evs in events.items():
            with svc.store(site).hold() as session:
                session.data.history.extend(evs)
                session.commit(now)

    # 端点侧的站点接入绑定: /api/hr/sites/{site}/entries 与 /api/hr/history?site= 按
    # config.trackers.<站>.hr_check.enabled 判站点接入(生产口径), 不绑则站点明细端点
    # 全 404 —— 前端打开站点状态块会给每个站点拉一次表①(loadHrStatus 首拉), 404 以
    # console.error 落进冒烟末尾的「无 console.error」总检(实测 2 错误/皮肤, 恒红)。
    # 壳只当绑定用: domains/tags 给无害占位值, 不与任何合成种子的 tracker 域相撞。
    for name in svc.enabled_sites():
        tracker = mgr.config.trackers.get(name)
        if tracker is None:
            tracker = FakeTracker(name, hr=None, rules=[])
            tracker.tags = [name]
            tracker.domains = [f"tracker.{name.lower()}.invalid"]
            mgr.config.trackers[name] = tracker
        tracker.hr_check = SiteHrCheckConfig(enabled=True, tracker=name)

    # 站点状态块(/api/hr/status)与表③(/api/hr/history)同源的消费面: 真读 service 的
    # 磁盘文件, 桩只补「线程在跑」的运行时快照与一个永远 409 的立即拉取(桩没有取数线程)。
    # revision 也一并给(webui 视图重建基线读它, 真 HrRuntime 上是 publisher.revision 属性)
    mgr.hr = SimpleNamespace(
        service=svc,
        revision=0,
        status=lambda: HrRuntimeStatus(
            enabled=True,
            sites=svc.enabled_sites(),
            sites_dir=svc.dir,
            writer="harness",
            fetch_enabled=False,
            worker_running=False,
            poll_interval=300.0,
            note="桩服务: 只读展示, 不执行取数",
        ),
        request_refresh=lambda sites=None: {
            "requested": [],
            "note": "桩服务不执行取数"
        },
    )


def _target_hashes(mgr, cmd: str, body: dict):
    """命令影响到的 hash 列表(桩里没有真实 qB, 只能按 payload 展开)"""
    if cmd in ("pause_torrent", "resume_torrent"):
        h = body.get("hash")
        return [h] if h else []
    if cmd in ("pause_group", "resume_group"):
        return list(mgr.store.groups.get(body.get("key") or (), []))
    if cmd == "bulk_torrents":
        out = list(body.get("hashes") or [])
        for k in body.get("keys") or []:
            out.extend(mgr.store.groups.get(k, []))
        return list(dict.fromkeys(out))
    return []


def _restore_state(mgr, hashes):
    """把 _apply_truth 改过的种子还原成**最初**的 state

    !为什么需要: 真机上"暂停"是永久的, 但桩服务是**长驻**的(起一次要跑很多轮冒烟, 红绿双验
    更是同一进程反复跑)。状态一旦永久累积, 跑过一轮"整剧暂停"(合成数据里一剧 = 全部种子)之后,
    下一轮冒烟里**所有行都是 s-paused** ⇒ 所有"挑一个未暂停的行"的断言全部假失败 —— 实测第二轮
    就 4 条断言因此变红, 而它们跟被测代码毫无关系。
    !记的是**最初**值(不是上一次命令后的值): pause→resume 连续两次操作同一批种子时, 若记
    "上一次", 回弹会把它们还原成暂停态。
    """
    orig = getattr(mgr, "_harness_orig_state", None) or {}
    new_states = {}
    for h in hashes:
        if h in orig and mgr.store.by_hash.get(h) is not None:
            new_states[h] = orig[h]
    if new_states:
        _publish_with_delta(mgr, new_states)


def _publish_with_delta(mgr, new_states):
    """发布"状态已变"的新版视图, 并**按增量协议保真**把脏行喂进增量时间线(plan 26-10-07-0414 S4)

    真机上状态变化经主循环 sync 增量推导: store._apply 应用增量 patch, 写 delta_fields
    (变化字段集)/view_changed/dirty_groups 并推进 rounds_applied, flush_views 每拍排空
    (_drain_delta_locked)并入 _delta_pending, _publish_locked 落代时折叠成时间线条目。

    !桩保真(S6/S7 间回归修复, 2026-10-07): 本函数 S4 期曾直改 FakeTorrent.state + 手写
      delta_fields/view_changed 绕过 _apply —— 当时能过; S5b 给 flush_views 加了 keyed
      判定(「本拍确有新 _apply 轮(rounds_applied 前进)」才认行级键, 防 S1 残值误判),
      绕过 ⇒ rounds_applied 不前进 ⇒ keyed=False ⇒ unkeyed_command_source ⇒ 命令真值轮
      **恒 full**(增量被静默降级为全量, 违背"增量成为默认路径"的计划目标; S7 收尾冒烟
      抓到, 净树 stash 对照确认非 S7 引入)。生产主循环每拍都跑 _apply 不受影响 ⇒ 这是
      **桩失真不是生产回归**。
    修法 = 让桩走生产同一条推导: 目标 state 作为增量 patch 喂给**真 store._apply**
    (patch 形状与 qB sync 增量响应同形: 只含变化种子的变化字段), 不再手工预写任何
    store 增量字段。FakeTorrent.apply_delta 与 TorrentRecord.apply_delta 同语义
    (tests/helpers.py :805), patch 里 state 变化会推出 delta_fields/dirty_groups/
    view_changed/rounds_applied++ 全套。若只 rebuild_views, 新代的 delta 桶恒空:
    前端(S4 起默认带 delta=1)每轮都收 "full=false + 空 delta", 真值永远到不了行上
    (2026-10-07 S4 冒烟实测: 暂停后 delta.torrents=[] 而非真值行)。

    !回弹(_restore_state)同样走这里 —— 否则回弹版同样推不出脏行, 前端行会永久停在
    "已暂停"的陈旧增量上(旧全量前端每轮整表替换, 天然掩盖了这一失真)。
    """
    patches = {}
    for h, s in new_states.items():
        if mgr.store.by_hash.get(h) is not None:
            patches[h] = {"state": s}
    if not patches:
        return
    mgr.store._apply(patches, [], full=False)
    mgr.web.flush_views(force=True)


def _revert_after_consume(mgr, hashes, wait_ms: int):
    """等真值这一版**真的被 /api/state 取走**之后, 再等 wait_ms 回弹

    !不能直接 `Timer(revert_ms)` 定时回弹: 回弹可能跑在前端看到真值**之前**(实测一次"整组暂停"
    的撤下因此被拖到 4149ms —— 真值被回弹改回去了, 前端要等到下一次回弹才碰巧对上)。以
    `web.pending_ver` 判"这一版已被消费"(它在 `web.ensure_state` 里被清空), 再等一小段,
    回弹就一定落在前端观测之后。
    """
    deadline = time.time() + 8.0
    while time.time() < deadline and getattr(mgr.web, "pending_ver", None) is not None:
        time.sleep(0.05)
    time.sleep(max(0, wait_ms) / 1000.0)
    _restore_state(mgr, hashes)


def _apply_truth(mgr, cmd: str, body: dict, revert_ms: int = 0):
    """把命令**真的**落到合成数据上 —— 否则真值永远不到, 乐观态只能靠 3s 兜底收尾,
    于是任何「真值对齐」类断言都测不到东西(只会测到"走满 3s")。

    这也是本桩此前最大的失真: 只回 ok 不改状态, 于是 issue 26-09-19-2024 那种
    "真值到了也不清 pending"的缺陷在本地完全无法暴露。

    `revert_ms` > 0 时, 真值被前端取走后再等这么久把它还原(见 _revert_after_consume) ——
    让长驻桩服务可以反复跑而不累积状态。
    """
    act = body.get("action") if cmd == "bulk_torrents" else cmd.split("_", 1)[0]
    if act not in ("pause", "resume"):
        return
    orig = getattr(mgr, "_harness_orig_state", None)
    if orig is None:
        orig = {}
        mgr._harness_orig_state = orig
    hashes = _target_hashes(mgr, cmd, body)
    new_states = {}
    for h in hashes:
        tor = mgr.store.by_hash.get(h)
        if tor is None:
            continue
        orig.setdefault(h, tor.state)  # 只记最初值(见 _restore_state)
        if act == "pause":
            new_states[h] = _PAUSED_STATE
        else:
            new_states[h] = _RESUME_DONE if getattr(tor, "progress", 0) >= 1 else _RESUME_TODO
    # !不再直改 tor.state(那会让真 _apply 的 apply_delta 比不出变化), 目标 state 作为
    #   增量 patch 经 _publish_with_delta 喂给真 _apply, 由 store 完成生产同款推导。
    # 版本号自增 ⇒ 前端下一次 /api/state 拿到新数组(而不是"版本未变"空响应)
    _publish_with_delta(mgr, new_states)
    if revert_ms > 0 and hashes:
        threading.Thread(target=_revert_after_consume, args=(mgr, hashes, revert_ms), daemon=True).start()


def _start_command_pump(mgr, mode: str, revert_ms: int = 0, wait_ms: int = 0):
    """兜底命令泵: 桩服务没有主循环, 命令没人消费 ⇒ 前端 waitCmd 会一直轮询到超时。

    这里不**执行**命令(合成数据没有真实 qB 可打), 只按 mode 直接写回执, 让前端的命令
    闭环可测: ok = 正常完成(乐观值被真值取代), error = 失败(乐观值必须**回滚**),
    hang = 不回执(验证 3s 回落真值, 不留假状态)。
    """
    if mode == "hang":
        return None

    def _loop():
        while True:
            try:
                # !队列元素是 **2 元组** (cmd, body), cmd_id 在 body 里 —— 按 3 元组解包会抛
                # ValueError, 命令被吃掉且永远没有回执(前端一直轮询, 表现为"点了没反应")。
                _cmd, body = mgr.web.commands.get(timeout=0.2)
            except queue.Empty:
                continue
            except Exception:
                time.sleep(0.2)
                continue
            cmd_id = (body or {}).get("cmd_id")
            if not cmd_id:
                continue
            if mode == "error":
                # 失败**不改状态**: 前端必须回滚到原值(回滚干净由冒烟 error 模式断言)
                mgr.web.results[cmd_id] = {"status": "error", "error": "桩服务注入的失败(用于验证乐观 UI 回滚)"}
            else:
                if wait_ms:
                    # !模拟真机「主循环正忙着, 命令排在后面」: 回执与真值是**同一轮主循环**里
                    # 出来的, 所以两者一起延后 —— 不是只延后回执。本地桩没有主循环, wait_ms 恒为 0,
                    # 于是"命令投递到回执"这一段在本地从来测不到, 而真机上它恰恰是最长的那一段。
                    time.sleep(wait_ms / 1000.0)
                mgr.web.results[cmd_id] = {
                    "status": "ok",
                    "wait_ms": round(wait_ms, 1),  # 埋点口径与后端 _timing() 一致: 排队等主循环
                    "exec_ms": 1,
                }
                # 先回执、后改状态(复刻真机补刷新的错位, 见 _TRUTH_DELAY 注释)
                time.sleep(_TRUTH_DELAY)
                try:
                    _apply_truth(mgr, _cmd, body, revert_ms)  # !队列解出来的是 _cmd(与 cmd 区分开)
                except Exception as e:  # 桩的健壮性优先: 同步失败也不能拖死命令泵
                    print(f"[harness] 状态同步失败: {e}", file=sys.stderr)

    t = threading.Thread(target=_loop, name="harness-cmd-pump", daemon=True)
    t.start()
    return t


def _is_loopback(host: str) -> bool:
    """只认回环地址: `localhost` / `::1` / 127.0.0.0/8(含 `0.0.0.0` 之外的任何写法)"""
    if host in ("localhost", "::1"):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description="WEB UI 浏览器冒烟桩服务")
    ap.add_argument("--torrents", type=int, default=1500, help="合成种子总数")
    ap.add_argument("--groups", type=int, default=200, help="归组数量(每组 2 个种子)")
    ap.add_argument("--no-groups", action="store_true", help="不建分组(纯平铺)")
    ap.add_argument(
        "--hr-site",
        action="store_true",
        help="注入站点接入形态的真实 HrJudgement(轮转全分支) —— 冒烟盲区复现用, 见 _inject_hr_site",
    )
    ap.add_argument(
        "--hr-scene",
        choices=["on", "empty", "off"],
        default="on",
        help="HR 在线核实桩场景(默认 on, 见 _inject_hr_history): on = 启用 + 五形态拉取历史"
        "(表③); empty = 启用 + 零历史(空态); off = 未启用(前端显示未启用态)。"
        "配套 e2e 轮 E2E_HR_SCENE —— 仅 on 跑表③断言组(e2e/hr-history.spec.mjs)",
    )
    ap.add_argument("--cmd-result", choices=["ok", "error", "hang"], default="ok", help="命令泵回执(默认 ok)")
    ap.add_argument(
        "--skip-check-menu",
        choices=["on", "off"],
        default="on",
        help="web.skip_check_menu 桩值(默认 on): off 起盘验 fail-closed 门控 —— "
        "「跳检…」在多选与单选菜单都不渲染(配套 e2e 轮 E2E_SKIP_CHECK=off, e2e/menus.spec.mjs)",
    )
    ap.add_argument(
        "--state-revert-ms",
        type=int,
        default=1500,
        help="真值**被 /api/state 取走后**再等多少 ms 还原成初始状态(默认 1500, 让长驻桩服务可反复跑;"
        " 0 = 不还原, 永久生效)。注意不是「真值生效后 N ms」—— 定时回弹会跑到前端观测之前"
        "(见 _revert_after_consume)",
    )
    ap.add_argument(
        "--cmd-wait-ms",
        type=int,
        default=0,
        help="模拟真机「主循环正忙, 命令排在其后」: 回执与真值**一起**延后这么久(两者出自同一轮"
        "主循环)。本地桩没有主循环, wait_ms 恒为 0 ⇒ 「命令投递→回执」这一段从来测不到, "
        "而真机上它往往是最长的那一段。0 = 瞬时(默认)",
    )
    ap.add_argument("--host", default="127.0.0.1", help="监听地址(**只接受回环**)")
    ap.add_argument("--port", type=int, default=8099)
    args = ap.parse_args()

    # !本服务故意免鉴权(skip_local_verify), 绑到非回环等于把 WEB UI 交给整个局域网。
    if not _is_loopback(args.host):
        print(
            f"[harness] 拒绝启动: --host 只接受回环地址(127.0.0.0/8 / ::1 / localhost), 收到 {args.host!r}\n"
            "          该服务免鉴权, 绑非回环会把它暴露给同网段的任何人。",
            file=sys.stderr
        )
        return 2

    tmp = tempfile.mkdtemp(prefix="aqb-harness-")
    state_file = os.path.join(tmp, "state.json")
    mgr = make_manager(state_file)
    mgr.client = FakeClient()
    # skip_check_menu 两态可参数化(W5 汇总): 默认 on —— 既有断言依赖「跳检…」菜单项与确认链
    # (计划 26-10-02-1955 W3); off 复刻生产默认(fail-closed), 供 e2e 轮 E2E_SKIP_CHECK=off
    # 验证门控(菜单两处都不渲染)。走真实 /api/webui/flags 端点渲染菜单, 桩只决定旗标值。
    mgr.config.web = WebConfig(
        enabled=True,
        host=args.host,
        port=args.port,
        token="",
        skip_local_verify=True,
        skip_check_menu=(args.skip_check_menu == "on"),
    )
    mgr._last_conn_ok = True  # 状态栏显示"已连接"(否则前端走断连提示分支)

    site_conf = mgr.config.trackers["HHan"]
    torrents = _make_torrents(args.torrents, site_conf)
    if args.hr_site:
        _inject_hr_site(torrents)
        print(f"[harness] HR 站点判定已注入: {args.torrents} 个种子轮转全分支")
    _inject_hr_history(mgr, tmp, args.hr_scene)
    if args.hr_scene != "off":
        print(f"[harness] HR 场景={args.hr_scene}: 站点状态 + 拉取历史表③已注入(HHan/HDSky)")
    seed_store(mgr, torrents)
    for tor in torrents:  # 抽屉/详情端点按 hash 取, 与 store 保持一致
        mgr.client.torrents[tor.hash] = tor
    # 抽屉 peers 页签的数据面(issue 26-10-07-2309): FakeClient.peers_map 默认恒空 ⇒ peers 页签
    # 在桩服务下永远渲染空态, e2e 与截图目检从未覆盖「有数据」渲染路径。按种子序号灌合成对端
    # (含 flags/速度/进度/客户端多样性, 见 _make_peers_response), 端点 /api/torrents/{h}/peers
    # 走 sync_torrent_peers 整包透传, 前端据此渲染。
    for i, tor in enumerate(torrents):
        mgr.client.peers_map[tor.hash] = _make_peers_response(i)
        # 抽屉 trackers 页签的数据面(P-02 升级, 2026-10-09): 逐行汇报倒计时改真 per-tracker 口径后,
        # 桩按 qB 5.2+ 形态灌多条含 next_announce 的 tracker(见 _make_trackers_response) —— 否则
        # 06 变体在桩下只走回退分支, 真口径渲染路径(e2e / 截图目检)从未被覆盖。
        mgr.client.trackers_map[tor.hash] = _make_trackers_response(i)

    if not args.no_groups:
        groups = {}
        for i in range(min(args.groups, len(torrents) // 2)):
            a, b = torrents[i * 2], torrents[i * 2 + 1]
            b.name = a.name  # 同组同名(真机: 同文件不同站)
            groups[(a.name, ())] = [a.hash, b.hash]
        mgr.store.groups = groups
        # member_to_key 同步重建(增量协议保真, plan 26-10-07-0414 S4 冒烟): 真机上组键索引
        # 由 store 的归组路径维护, 桩直写 groups 绕过了它 —— 索引为空时 _drain_delta_locked
        # 推不出组行键(组桶恒空), 且"归组成员被判未归组"会触发 singles 防御检查整代转 full,
        # 分组视图的增量链路在冒烟里完全测不到。
        mgr.store.member_to_key = {h: k for k, hs in groups.items() for h in hs}
    mgr.web.rebuild_views()
    _start_command_pump(mgr, args.cmd_result, args.state_revert_ms, args.cmd_wait_ms)

    app = create_app(mgr)
    print(
        f"[harness] http://{args.host}:{args.port}/atlas/  /prism/  种子={args.torrents} 组={len(mgr.store.groups)} "
        f"命令回执={args.cmd_result} 跳检菜单={args.skip_check_menu} HR场景={args.hr_scene}",
        flush=True
    )

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
