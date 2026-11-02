"""test_qbmanager_query 测试计划: qbmanager 全局任务/种子查询/连接/主循环

## 测试计划(每个测试函数一条)
- test_tick_refresh_error_continues: 主循环内 _refresh_torrents 抛异常被捕获, 下一 tick 继续
- test_refresh_added_no_tracker_match_skips: 新增种子未匹配 tracker 配置 -> 警告并跳过
- test_refresh_removed_grouping_disabled: 删除种子且分组关闭 -> 只移除任务不扫描
- test_refresh_suppress_window_exception_closes_window_in_finally: 守阵(26-10-06-0028 A-01)——suppress 窗内异常上抛后 live 旗标不残留, 下一成功轮 full_round 相位照常广播不被吞
- test_refresh_schema_validation_missing_raises: 首次拉到非空种子信息时校验字段, 缺失抛 QbCompatError
- test_refresh_schema_validation_passes_once: 全字段通过置 flag 不再重复校验
- test_export_torrents_info: export_torrents_info 写种子信息到文件(编码恒 utf-8, GBK 外字符不崩)
- test_view_rebuild_waits_for_client_consume: 节拍对齐门控 —— 上一版没被 /api/state 取走就不生产下一版(>3000 种子时约一半 rebuild 无人消费), 且**脏标记必须保留**; 命令驱动的那一轮 force=True **必须绕过**(P0-5 要求真值几十毫秒内进快照, 不能等客户端轮询)
- test_tick_rebuilds_all_views_when_changed: 视图变化且 Web 活跃 -> 四份视图同一入口**同次**重建
- test_tick_rebuilds_views_when_grouping_disabled: 分组未启用时脏标记不被吞, 视图照样重建
- test_qbmanager_source_has_no_web_state_fields: 静态守阵(2026-09-20 解耦, W3 起名单读分诊清单)——主循环源码不得直接读写表现层旧字段(别名层已删, 写回即静默造第二份真相, 只能靠扫描抓回潮)
- test_hr_anchors_from_store: HR 判定桥在构造时挂上 + 锚点按站点分组给出(QB 侧给取数线程的交接面)
- test_p2a_run_materializes_schema_migration_dry_run_then_write: run() 启动物化 dry-run 不落盘 / 非 dry-run 迁移+备份 (P2-a)
- test_p2a_refresh_added_pipeline_skips_ghost_and_unmatched: added 管线幽灵 hash / 未匹配 tracker 跳过 (P2-a)
- test_w6_refresh_transitions_phase_payload: 守阵(W6)——transitions 相位与载荷契约
- test_w6_refresh_events_removed_and_scan_phase: 守阵(W6)——events_removed/removed_scan 相位载荷契约(含删除前快照)
- test_w6_refresh_suppression_window_opens: 守阵(W6)——抑制请求位必须真正开窗(两事件相位不派发)
- test_w6_refresh_events_added_phase_payload: 守阵(W6)——events_added 相位载荷契约
- test_w6_refresh_torrents_added_phase_payload: 守阵(W6)——torrents_added 逐种子相位载荷契约
- test_w6_refresh_post_phase_payload: 守阵(W6)——post 相位载荷契约
- test_w6_refresh_matching_loop_continues_past_skips: 守阵(W6)——匹配循环跳过(幽灵/未匹配)不截断后续种子
- test_w6_refresh_fs_selfcheck_once: 守阵(W6)——映射自检一次性闸门: 恰好首轮全量跑一次且实参为 save_path 清单
- test_w6_refresh_search_index_dirty_on_add_only: 守阵(W6)——单边新增/删除都必须标搜索索引脏
- test_w6_refresh_added_logging_domains: 守阵(W6)——新增 INFO/未匹配 WARNING 审计面 + 诊断域名来自真实拉取
- test_w6_export_torrents_info_pins_utf8_encoding: 守阵(W6, 平台相关)——导出 open 探针钉 encoding="utf-8"
"""

import json

import logging

import os

import tempfile

import threading

import time

from unittest import mock

from auto_qb.core.taskqueue import FINISHED, PENDING, REQUEUE, Task, TaskQueue

import pytest

from qbittorrentapi import APIConnectionError, Client

from auto_qb.config import QbittorrentConfig

from auto_qb.config import PathMapEntry

from auto_qb.config.models import FsConfig

from auto_qb.infra.errors import AutoQbError

from auto_qb.infra import file_access

from auto_qb.infra.file_access import MappedFileAccess

from auto_qb.core.module import ApplyResult

from auto_qb.core import qbmanager as _qbm

from auto_qb.core.qbclient import REQUESTS_TIMEOUT, LocalQbClient, new_client

from auto_qb.core.qbmanager import RECONNECT_MAX_INTERVAL, QbConnectError, QbManager, _throttle, _wait_next

from auto_qb.torrents import QbCompatError

from helpers import LEGACY_V1, FakeClient, FakeConfig, FakeTorrent, capture_logs, make_manager, seed_store


def test_tick_refresh_error_continues():
    """run 主循环: _refresh_torrents 抛异常被捕获, 循环继续到下一 tick"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        mgr.connect = mock.Mock(return_value=True)
        # !节拍调小(26-10-02-0728): 异常路径现在会推进 next_*_at 退避, 第一次异常后主循环
        # 真等一个 main_tick 才进下一拍 —— 默认 1.0s 会让本用例多挂 1s。
        mgr.config.main_tick = 0.05
        mgr.config.sync_interval = 0.05
        # 第一次抛普通异常(被内层 except Exception 捕获), 第二次抛 KeyboardInterrupt(退出循环)
        mgr._refresh_torrents = mock.Mock(side_effect=[RuntimeError("refresh boom"), KeyboardInterrupt()])
        with mock.patch("auto_qb.core.qbmanager.time.sleep"):
            mgr.run(dry_run=False)
        assert mgr._refresh_torrents.call_count == 2, "第一次异常应被捕获, 第二次 tick 继续执行"


def test_refresh_added_no_tracker_match_skips():
    """新增种子未匹配任何 tracker 配置: 警告并跳过, 不写限速/不建任务"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["U1"] = FakeTorrent(hash="U1", name="T1")
        mgr.config.trackers = {}  # 无任何 tracker 配置
        mgr._refresh_torrents()
        assert client.calls == []
        assert mgr.task_queue.run_due(time.time(), max_tasks=10) == 0


def test_refresh_schema_validation_missing_raises():
    """首次拉到非空种子信息时校验必需字段: 缺失抛 QbCompatError(qB 版本漂移早暴露)"""
    from types import SimpleNamespace

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        # 模拟 qB 版本不兼容: torrent info 缺少 ratio/seeding_time 等字段
        client.torrents["H1"] = SimpleNamespace(hash="H1", name="T1", state="stalledUP")
        with pytest.raises(QbCompatError) as excinfo:
            mgr._refresh_torrents()
        assert "缺少字段" in str(excinfo.value)


def test_refresh_schema_validation_passes_once():
    """全字段样本通过校验并置 flag; 后续 refresh 不再重复校验(qB 版本运行期不变)"""
    from types import SimpleNamespace

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        mgr._refresh_torrents()  # 首次: 校验通过
        assert mgr._schema_validated is True
        # 第二轮: flag 已置, 即使出现缺字段对象也不再校验(防御性断言 flag 语义)
        client.torrents["H1"] = SimpleNamespace(hash="H1", name="T1", state="stalledUP")
        mgr._refresh_torrents()  # 不抛


def test_refresh_removed_grouping_disabled():
    """检测到删除种子且分组功能关闭: 移除任务但不触发组内缺文件扫描"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        seed_store(mgr)  # 首轮快照已同步
        del client.torrents["H1"]  # 种子被删除
        mgr._refresh_torrents()
        assert mgr.store.get("H1") is None
        assert mgr.config.grouping.enabled is False  # 分组关闭: 跳过组内扫描


def test_refresh_suppress_window_exception_closes_window_in_finally():
    """守阵(26-10-06-0028 A-01): suppress 窗内异常上抛后 live 旗标不残留, 下一成功轮相位不被吞

    事件分派两相位窗口(events_removed 前 arm -> events_added 后 close)内异常原样上抛
    (issue 取证源: ctx.trackers.match 网络异常; emit 无逐订阅者隔离), 关窗点必须在
    finally 兜底: 残留 live 旗标会把下一成功刷新轮的 full_round / events_* 全吞
    (emit 返回 0), 边沿驱动事件不可重放。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        seen: list = []
        mgr.events.on("full_round", lambda event: seen.append("full_round"))
        # match 异常只注入 added 循环调用点(窗内), full_round 订阅者(_on_full_round)同方法
        # 需照常成功 —— 按调用序给效果: R1 全量轮(成功) / R1 added 循环(炸) / R2 全量轮(成功) / R2 added 循环(炸)
        mgr.ctx.trackers.match = mock.Mock(
            side_effect=[None, RuntimeError("match boom"), None,
                         RuntimeError("match boom")]
        )
        mgr.events.request_suppression()  # 热重载首轮: 挂请求位, take 即 arm
        with pytest.raises(RuntimeError, match="match boom"):
            mgr._refresh_torrents()
        assert not mgr.events.suppressed, "异常路径关窗: live 旗标不得残留(try/finally 兜底)"
        # 下一成功刷新轮(强制全量同步触发 full_round): 相位照常广播, 不被残留旗标吞掉
        # (本轮无新增种子, added 循环不跑, 刷新完整走完)
        seen.clear()
        mgr.store.rid = 0
        mgr._refresh_torrents()
        assert seen == ["full_round"], "下一成功轮 full_round 相位照常广播(修复前被吞)"


def test_export_torrents_info():
    """export_torrents_info: 全量种子逐条写入文件(debug 用); 编码恒 utf-8 —— 含 GBK 外
    字符的种子名不崩(Windows 默认 cp936 会 UnicodeEncodeError 中途崩; issue
    26-10-06-0028 chore-export-torrents-info-encoding)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        client.torrents["H2"] = FakeTorrent(hash="H2", name="T2")
        # U+20000 不在 GBK 内: 无显式 encoding 时 cp936 环境写到该种子即崩
        # (FakeTorrent 无 __str__, 落盘是对象 repr; 这里用带名字 __str__ 的桩验证编码)
        client.torrents["H3"] = type("NamedStub", (), {"name": "种子𠀀X", "__str__": lambda self: self.name})()
        out = os.path.join(td, "torrents.txt")
        mgr.export_torrents_info(out)
        text = open(out, encoding="utf-8").read()
        lines = [ln for ln in text.splitlines() if ln.strip()]
        assert len(lines) == 3, f"每个种子一行, 共 3 条: {lines}"
        assert text.count("\n\n") == 3  # 每条种子后空行分隔
        assert "种子𠀀X" in text, "GBK 外字符按 utf-8 如实落盘"
        # 静态钉: 本机默认编码恰为 utf-8 时行为面红验不可达(与 O_TRUNC 守阵同判), 源码级
        # 断言 export_torrents_info 必须显式 encoding="utf-8" —— 还原 open(path, "w") 即红
        import inspect

        src = inspect.getsource(type(mgr).export_torrents_info)
        assert 'encoding="utf-8"' in src, "export_torrents_info 必须显式 encoding=utf-8(禁 open(path, 'w'))"


def test_tick_rebuilds_all_views_when_changed():
    """视图惰性重建: 仅视图变化且 Web 活跃时重建 —— **四份视图同一入口同次重建**

    历史缺陷(2026-09-18, 症状"种子页速度冻结、状态栏正常"): 主循环曾**只**重建
    `_group_view` 就把共享的 `_group_view_dirty` 清掉 ⇒ Web 线程的兜底重建永不触发,
    singles/shows/flat 三份视图长期停留在旧快照, 而版本号照常自增 ⇒ 前端判
    `updated=true` 把**陈旧数组整表换上去**; 状态栏"速度合计"因取 groups 求和反而一直新鲜。

    故本用例断言的是"四份视图**同次**重建", 而不是"某一份被重建" —— 只断言其中一份
    会漏掉这个缺陷(原用例正是只 spy 了 `_build_group_view`, 把缺陷固化成了预期行为)。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        mgr.config.grouping.enabled = True
        mgr.web.touch()  # Web 活跃
        with mock.patch.object(mgr, "_refresh_torrents"), \
             mock.patch.object(mgr, "_build_group_view", return_value=[]) as g, \
             mock.patch.object(mgr, "_build_singles_view", return_value=[]) as s, \
             mock.patch.object(mgr, "_build_shows_view", return_value={"list": [], "unrecognized": []}) as sh, \
             mock.patch.object(mgr, "_build_flat_view", return_value=[]) as f:
            counts = lambda: (g.call_count, s.call_count, sh.call_count, f.call_count)  # noqa: E731
            mgr.store.view_changed = True
            mgr._tick(dry_run=False)
            assert counts() == (1, 1, 1, 1)  # 视图变化 -> 四份同次重建
            mgr._tick(dry_run=False)
            assert counts() == (1, 1, 1, 1)  # 标记已消费且无新变化 -> 不重建
            # WARN: 新增前提: 上面那一版**还没被任何 /api/state 请求取走**(pending 未清) ⇒
            # 即便又脏了也不生产新版本(节拍对齐门控)。这里模拟客户端取走一次再继续。
            mgr.store.view_changed = True
            mgr._tick(dry_run=False)
            assert counts() == (1, 1, 1, 1)  # 上一版没人取 -> 不重建(脏标记保留)
            mgr.web.ensure_state(mgr.web.group_view_ver)  # 客户端取走当前版本
            mgr._tick(dry_run=False)
            assert counts() == (2, 2, 2, 2)  # 已取走 + 仍脏 -> 重建, 且四份同次
            mgr.store.view_changed = True
            mgr.web.last_seen = 0.0  # Web 不活跃(超过 TTL)
            mgr._tick(dry_run=False)
            assert counts() == (2, 2, 2, 2)  # 不重建
            assert mgr.web.group_view_dirty is True  # 脏标记保留, 待 Web 恢复后重建


def test_view_rebuild_waits_for_client_consume():
    """节拍对齐: 上一版没被 /api/state 取走就不生产下一版; 命令驱动的那轮必须绕过

    服务端 `sync_interval` 固定 1.5s, 而前端 `basePollMs()` 按种子量取 1.5/2/3s ⇒
    >3000 种子时服务端每 3s 产 2 版、客户端只取最后一版, 中间那版的重建 CPU 无人消费
    (issues/26-09-19-1900-webui-poll-cadence-mismatch, 方案 B)。
    这里让"生产"等"消费": `_web_pending_ver` 未清(没人取)就不重建, 但**脏标记必须保留**
    (否则这次变化会被丢掉) —— 客户端一取走立刻补上。

    WARN: `force=True`(本轮有命令改了种子状态)**必须绕过** —— P0-5 要求用户操作后真值几十毫秒内
    进快照; 若被门控挡住, 真值要等客户端下一次轮询才可见, 与 P0-5 相悖。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        mgr.web.touch()  # Web 活跃
        with mock.patch.object(mgr, "_refresh_torrents"), mock.patch.object(
            mgr, "_build_group_view", return_value=[]
        ) as g, mock.patch.object(mgr, "_build_singles_view", return_value=[]), mock.patch.object(
            mgr, "_build_shows_view", return_value={
                "list": [],
                "unrecognized": []
            }
        ), mock.patch.object(mgr, "_build_flat_view", return_value=[]):
            # 1. 首版: 无 pending -> 重建, 并登记"这一版还没人取走"
            mgr.store.view_changed = True
            mgr.web.flush_views()
            assert g.call_count == 1
            assert mgr.web.pending_ver == mgr.web.group_view_ver

            # 2. 又脏了但上一版还没人取 -> **不生产**(这就是省掉的那一次)
            mgr.store.view_changed = True
            mgr.web.flush_views()
            assert g.call_count == 1, "上一版没人取就再产一版 = 白烧 CPU(节拍错配的症状)"
            assert mgr.web.group_view_dirty is True, "脏标记必须保留, 否则这次变化会被丢掉"

            # 3. 命令驱动: force=True 必须绕过门控(P0-5: 真值不能等客户端轮询)
            mgr.web.flush_views(force=True)
            assert g.call_count == 2, "命令改了状态就必须立刻重建, 不能等客户端轮询"
            assert mgr.web.group_view_dirty is False

            # 4. 客户端取走当前版本(此时不脏, 不会顺带重建) -> pending 清空
            mgr.web.ensure_state(mgr.web.group_view_ver)
            assert mgr.web.pending_ver is None
            assert g.call_count == 2

            # 5. 已被取走 -> 门控重新打开, 再脏就能重建
            mgr.store.view_changed = True
            mgr.web.flush_views()
            assert g.call_count == 3


def test_tick_rebuilds_views_when_grouping_disabled():
    """分组未启用: 视图**仍须**重建(种子页平铺视图与"辅种分组是否启用"无关)

    历史缺陷: 整个重建块曾被 `if grouping.enabled` 包住 —— 而 `consume_view_changed()`
    在块**外**已把脏标记读走复位 ⇒ 分组关闭时标记无处落地、永久丢失 ⇒ 版本号不再变化
    ⇒ 前端 `updated=false` 并退避轮询, 四份视图全部冻住。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        mgr.config.grouping.enabled = False
        mgr.web.touch()
        with mock.patch.object(mgr, "_refresh_torrents"), \
             mock.patch.object(mgr, "_build_group_view", return_value=[]) as g, \
             mock.patch.object(mgr, "_build_singles_view", return_value=[]) as s, \
             mock.patch.object(mgr, "_build_shows_view", return_value={"list": [], "unrecognized": []}) as sh, \
             mock.patch.object(mgr, "_build_flat_view", return_value=[]) as f:
            mgr.store.view_changed = True
            mgr._tick(dry_run=False)
            assert (g.call_count, s.call_count, sh.call_count, f.call_count) == (1, 1, 1, 1)
            assert mgr.web.group_view_dirty is False  # 标记被真正消费(不是被吞掉)


def test_qbmanager_source_has_no_web_state_fields():
    """静态守阵: 主循环源码不得直接读写表现层旧字段(防回潮)

    2026-09-20 解耦后 19 个表现层字段归 WebUIRuntime, QbManager 只经 `self.web` 的门面方法
    交互; 兼容代理曾把旧字段名**静默转发** —— 代码照样能跑, 状态归属却散回核心域。别名层处置
    W3 已把代理删除, 现在写 `self._group_view = ...` 会在实例上直接造出第二份真相(与 runtime
    那份互不可见且不报错), 比转发期更隐蔽, 仍只能靠扫描源码抓住。旧字段名单以分诊清单为准
    (退役名单永久留档, 守阵 tests/test_qbmanager_alias_freeze.py 同源); 别名表已不存在, 无需豁免。
    """
    import json
    import re

    src = open(
        os.path.join(os.path.dirname(__file__), "..", "src", "auto_qb", "core", "qbmanager.py"), encoding="utf-8"
    ).read()
    triage = json.loads(
        open(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "memory-bank",
                "plans",
                "26-10-01-0350-plan-web-state-alias-disposal.triage.json",
            ),
            encoding="utf-8",
        ).read()
    )
    hits = [old for old in triage["alias_layer"]["fields"] if re.search(rf"self\.{re.escape(old)}\b", src)]
    assert not hits, (
        f"主循环源码又直接引用了表现层旧字段 {hits} —— 应改用 self.web 的门面方法"
        "(consume_commands / flush_views / flush_receipts / mark_dirty …)"
    )


def test_hr_anchors_from_store():
    """HR 判定桥在构造时挂上 + 锚点提供者(主循环给取数线程的交接面, 计划 §9)

    锚点形状/站点键必须与取数侧一致(`refresh_site(site, anchors)` 取 infohash -> HrAnchor),
    否则「本实例二次下载 ⇒ 放行立即作废」永远发现不了 —— 而且不会报错。
    """
    from auto_qb.config.models import SiteHrCheckConfig
    from auto_qb.hr.resolve import HrAnchor

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        assert mgr.store.hr_link is mgr.hr, "判定桥必须构造时就挂上(记录读取时现算, 不靠遍历刷新)"
        assert mgr.hr._anchors() == {}, "站点未接入 hr_check -> 不上交任何锚点"

        site = mgr.config.trackers["HHan"]
        site.hr_check = SiteHrCheckConfig(
            enabled=True, tracker="hhan", hr_page_url="https://hhan/myhr.php", required_seeding_time=86400.0
        )
        # 用真记录(store.refresh), 不用 seed_store 的对象身份注入: 锚点由 record.hr_anchor() 派生
        mgr.store.refresh([FakeTorrent(hash="H1"), FakeTorrent(hash="H2")])
        got = mgr.store.get("H1")
        got.tracker_conf = site
        got.infohash_v1 = "aa" * 20
        got.added_on = 11
        got.downloaded = 123
        anchors = mgr.hr._anchors()  # H2 未匹配 tracker_conf -> 不进锚点
        assert set(anchors) == {"HHan"} and set(anchors["HHan"]) == {"aa" * 20}
        assert anchors["HHan"]["aa" * 20
                              ] == HrAnchor(added_on=11, downloaded=123, completion_on=-1, progress=0.0, name="Test")

        site.hr_check = SiteHrCheckConfig(enabled=False)  # 站点关掉 -> 同样不上交
        assert mgr.hr._anchors() == {}


def test_p2a_run_materializes_schema_migration_dry_run_then_write():
    """run() 启动物化: dry-run 只探测不落盘(425); 非 dry-run 迁移+备份落盘(427)"""
    from auto_qb.config import load_config

    legacy = LEGACY_V1
    with tempfile.TemporaryDirectory() as td:
        cfg = FakeConfig()
        cfg.state_file = os.path.join(td, "state.json")
        cfg.data_dir = os.path.join(td, "data")
        config_path = os.path.join(td, "config.yml")
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(legacy)
        mgr = make_manager(cfg.state_file)
        mgr.config.data_dir = cfg.data_dir
        mgr.config_path = config_path
        mgr.connect = mock.Mock(return_value=True)
        mgr._tick = mock.Mock(side_effect=[None, KeyboardInterrupt()])
        # dry-run: 迁移只报内存生效, 磁盘一字不动
        mgr.run(dry_run=True)
        with open(config_path, encoding="utf-8") as f:
            assert "schema_version" not in f.read(), "dry-run 不得写盘"
        # 非 dry-run: 迁移落盘 + 版本号备份(重武装 _tick: 上一次的 side_effect 已耗尽,
        # StopIteration 会被主循环 except Exception 吞掉导致空转死循环)
        mgr._tick = mock.Mock(side_effect=[None, KeyboardInterrupt()])
        mgr.run(dry_run=False)
        with open(config_path, encoding="utf-8") as f:
            assert "schema_version: 5" in f.read(), "磁盘应落当前版本章"
        backup = os.path.join(cfg.data_dir, "config.yml.v1.bak")
        assert os.path.exists(backup), "迁移前备份应存在"
        load_config(config_path)  # 迁移后磁盘可原样通过加载


def test_p2a_refresh_added_pipeline_skips_ghost_and_unmatched():
    """added 管线守卫: 新增 hash 快照缺失(防御分支)与匹配不到 tracker 且域名拉取抖动 -> 跳过不崩溃"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        client.torrents_trackers = lambda h: [{"url": "http://unknown.example.com/announce"}]  # 匹配不到
        mgr.client = client
        t = FakeTorrent(hash="HB", name="T", state="stalledUP")
        client.torrents["HB"] = t
        client.torrents["HGONE"] = FakeTorrent(hash="HGONE", name="G", state="stalledUP")

        orig_get = mgr.store.get

        def ghost_get(h):
            if h == "HGONE":
                return None  # 模拟 added 里有但快照已取走(防御分支语义)
            return orig_get(h)

        from auto_qb.torrents import TorrentRecord

        with mock.patch.object(mgr.store, "get", side_effect=ghost_get), mock.patch.object(
            mgr.ctx.trackers, "match", return_value=None
        ), mock.patch.object(TorrentRecord, "trackers_info", side_effect=RuntimeError("api down")):
            mgr._refresh_torrents(False)  # 不崩溃: GHOST 跳过 / HB 匹配失败且域名拉取抖动 -> 空域名告警跳过
        assert orig_get("HB") is not None, "未匹配种子记录保留(告警由管线负责)"
        assert not any(c[0].startswith("set_") for c in client.calls), "未匹配种子不限速不建任务"


def test_w6_refresh_transitions_phase_payload():
    """守阵(W6, 中/低): transitions 相位与载荷逐字契约(相位失联/载荷键变异即红)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        mgr.config.trackers = {}
        seen = []
        mgr.events.on("transitions", lambda event: seen.append((event.phase, event.payload)))
        mgr._refresh_torrents(False)
        assert seen == [("transitions", {"dry_run": False})], f"transitions 相位与载荷契约: {seen}"


def test_w6_refresh_events_removed_and_scan_phase():
    """守阵(W6, 中/低): events_removed/removed_scan 相位载荷契约(含删除前快照留档)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1", save_path="R:/Downloads/T1")
        mgr._refresh_torrents(False)  # 首轮: 种子入库
        tor = mgr.store.get("H1")
        removed_seen, scan_seen = [], []
        mgr.events.on("events_removed", lambda e: removed_seen.append((e.phase, e.payload)))
        mgr.events.on("removed_scan", lambda e: scan_seen.append((e.phase, e.payload)))
        del client.torrents["H1"]
        with capture_logs("auto_qb.core.qbmanager") as cap:
            mgr._refresh_torrents(False)
        assert len(removed_seen) == 1, f"events_removed 必须派发: {removed_seen}"
        phase, payload = removed_seen[0]
        assert phase == "events_removed"
        assert payload["removed"] == ["H1"], "删除清单键/值契约"
        assert payload["snapshots"]["H1"] is tor, "删除前快照必须带原记录对象(留档面)"
        assert set(payload) == {"removed", "snapshots", "dry_run"}, f"events_removed 载荷键面: {set(payload)}"
        assert scan_seen == [("removed_scan", {"hashes": ["H1"], "dry_run": False})], f"removed_scan 载荷契约: {scan_seen}"
        assert "检测到删除种子 1 个" in cap.text, "删除 INFO 不得丢"


def test_w6_refresh_suppression_window_opens():
    """守阵(W6, 中): 抑制请求位必须真正开窗 —— 窗口内两事件相位不派发(不开窗=热重载首轮全库重放)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        mgr.config.trackers = {}
        events_seen = []
        mgr.events.on("events_removed", lambda e: events_seen.append(e.phase))
        mgr.events.on("events_added", lambda e: events_seen.append(e.phase))
        trans_seen = []
        mgr.events.on("transitions", lambda e: trans_seen.append(e.phase))
        mgr.events.request_suppression()
        mgr._refresh_torrents(False)
        assert events_seen == [], "抑制窗口内 events_removed/events_added 不得派发"
        assert trans_seen, "transitions 不受抑制窗口影响(仅两事件相位)"
        assert not mgr.events.suppressed, "窗口必须在 finally 关闭(不残留)"


def test_w6_refresh_events_added_phase_payload():
    """守阵(W6, 中/低): events_added 相位与载荷契约(相位失联=事件规则不触发)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["U1"] = FakeTorrent(hash="U1", name="T1")
        seen = []
        mgr.events.on("events_added", lambda e: seen.append((e.phase, e.payload)))
        mgr._refresh_torrents(False)
        assert seen == [("events_added", {"added": ["U1"], "dry_run": False})], f"events_added 载荷契约: {seen}"


def test_w6_refresh_torrents_added_phase_payload():
    """守阵(W6, 低): torrents_added 逐种子相位载荷契约"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["U1"] = FakeTorrent(hash="U1", name="T1")
        seen = []
        mgr.events.on("torrents_added", lambda e: seen.append((e.phase, e.payload)))
        mgr._refresh_torrents(False)
        assert seen == [("torrents_added", {"hash": "U1", "dry_run": False})], f"torrents_added 载荷契约: {seen}"


def test_w6_refresh_post_phase_payload():
    """守阵(W6, 中/低): post 相位载荷契约(收尾重归组/冲突检查的判据面)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        seen = []
        mgr.events.on("post", lambda e: seen.append((e.phase, e.payload)))
        mgr._refresh_torrents(False)
        assert seen == [("post", {"dry_run": False})], f"post 载荷契约: {seen}"


def test_w6_refresh_matching_loop_continues_past_skips():
    """守阵(W6, 中): 匹配循环跳过(幽灵/未匹配)不得截断后续种子(continue→break 家族)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        client.trackers_map["H1"] = [{"url": "http://unknown.example.com/announce"}]  # H1 匹配不到
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        mgr._refresh_torrents(False)  # H1 入库但未匹配
        # 第二轮新增: 幽灵(hash 缺快照) + 未匹配(H9) + 可匹配(H2, 默认 hhanclub URL) —— 排序覆盖两类 break
        client.trackers_map["H9"] = [{"url": "http://unknown2.example.com/announce"}]
        client.torrents["HGHOST"] = FakeTorrent(hash="HGHOST", name="G")
        client.torrents["H9"] = FakeTorrent(hash="H9", name="T9")
        client.torrents["H2"] = FakeTorrent(hash="H2", name="T2")
        orig_get = mgr.store.get

        def ghost_get(h):
            return None if h == "HGHOST" else orig_get(h)

        added_seen = []
        mgr.events.on("events_added", lambda e: added_seen.append(e.payload.get("added")))
        with mock.patch.object(mgr.store, "get", side_effect=ghost_get):
            mgr._refresh_torrents(False)
        assert added_seen and added_seen[-1] == ["H2"], \
            f"匹配循环跳过后必须继续处理后续种子(幽灵/未匹配不得截断): {added_seen}"


def test_w6_refresh_fs_selfcheck_once():
    """守阵(W6, 中/低): 映射自检一次性闸门 —— 恰好首轮全量跑一次, 实参 = 现存 save_path 清单"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1", save_path="R:/Downloads/T1")
        with mock.patch("auto_qb.infra.file_access.path_map_selfcheck") as sc:
            mgr._refresh_torrents(False)
            mgr.store.rid = 0  # 强制下一轮全量(need_validate 重新置位)
            mgr._refresh_torrents(False)
        assert sc.call_count == 1, f"映射自检必须恰好跑一次(闸门失效=每全量轮重跑): {sc.call_count}"
        assert sc.call_args == mock.call(["R:/Downloads/T1"]), f"自检实参 = save_path 清单(不得为 None): {sc.call_args}"


def test_w6_refresh_search_index_dirty_on_add_only():
    """守阵(W6, 中): 单边新增或单边删除都必须标搜索索引脏(and 收紧=索引陈旧)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        mgr.web.mark_search_index_dirty = mock.Mock()
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        mgr._refresh_torrents(False)  # 仅新增
        assert mgr.web.mark_search_index_dirty.call_count == 1, "单边新增必须标索引脏"
        mgr.web.mark_search_index_dirty.reset_mock()
        del client.torrents["H1"]
        mgr._refresh_torrents(False)  # 仅删除
        assert mgr.web.mark_search_index_dirty.call_count == 1, "单边删除必须标索引脏"


def test_w6_refresh_added_logging_domains():
    """守阵(W6, 低): 新增 INFO/未匹配 WARNING 审计面 + 诊断域名来自**本次** tracker 拉取

    trackers_info 实参变异(trackers_info(None)/=None/extract(None))必须让域名清单丢失;
    match 桩掉避免它先拉一次 tracker 把记录级缓存焐热(热缓存会掩盖实参变异)。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.config.trackers = {}  # 全部匹配不到
        mgr.ctx.trackers.match = mock.Mock(return_value=None)  # 不预热记录级 trackers 缓存
        client = FakeClient()
        client.torrents_trackers = lambda h: [{"url": "https://tracker.hhanclub.net/announce.php"}]
        mgr.client = client
        client.torrents["U1"] = FakeTorrent(hash="U1", name="T1")
        with capture_logs("auto_qb.core.qbmanager") as cap:
            mgr._refresh_torrents(False)
        assert any("检测到新增种子 1 个" in m for m in cap.messages), "新增 INFO 不得丢"
        warn = [m for m in cap.messages if "未匹配 tracker 配置" in m]
        assert warn, "未匹配 WARNING 不得丢"
        assert any("tracker.hhanclub.net" in m for m in warn), "诊断域名清单必须来自真实 tracker 拉取"


def test_w6_export_torrents_info_pins_utf8_encoding(monkeypatch):
    """守阵(W6, 中, 平台相关): 导出 open 探针钉 encoding="utf-8"(Windows cp936 平台面, 全平台可观测)"""
    import builtins

    real_open = builtins.open
    seen = {}

    def spy(file, mode="r", *args, **kwargs):
        seen[os.fspath(file)] = (mode, kwargs.get("encoding"))
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", spy)
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        out = os.path.join(td, "torrents.txt")
        mgr.export_torrents_info(out)
        assert seen[out] == ("w", "utf-8"), f"导出必须显式 encoding=utf-8(Windows cp936 mojibake 面): {seen}"
