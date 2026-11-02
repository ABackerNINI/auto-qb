"""test_webui_static_dom_page_store 测试计划: webui 前端静态守阵: 页面 / 列模型 / 视图

## 测试计划(每个测试函数一条)
- test_frontend_cols_store_single_setitem_site: COLS_STORE_KEY 的 setItem 全仓恰好一处(persistPage 内) —— 散写回潮即红
- test_frontend_cols_legacy_keys_have_migration: LEGACY_COLS_KEYS 键链必须伴随 migrateLegacyToV5 迁移(v3->v4 清零事故的机检)
- test_frontend_cols_empty_hint_names_browser_clear_cause: 空存储提示必须点名浏览器站点级"关闭窗口时清除 Cookie 和站点数据"这条通道 + 给自查路径 + sessionStorage 会话级去重(2026-09-24 取证: cookie 例外 127.0.0.1,* setting=4)
- test_frontend_dir_browse_and_search_stale_guard: 目录浏览与搜索的请求代际守卫(F2-03, issue 26-10-06-0028) —— add_torrent.js loadDir 发请求即记 _dirReqPath 戳, 落袋/报错/finally 三处比对(过期响应丢弃且不动 loading 态) + view.js doSearch 落袋与报错前比对 searchQuery 当前词(慢响应不覆盖新词状态), 任一处守卫被摘除即红
- test_web_store_iteration_snapshot_race_guard: Web 读侧快照竞态守阵(E-01, issue 26-10-06-0028) —— 写线程高频原地增删 store.by_hash/groups/cross_group_conflict_warned 期间, 连续跑 search_torrents/_build_* 系/mark_local_present 不抛 "dictionary changed size during iteration"(修复前大库下必抛)
- test_frontend_cols_empty_hint_is_not_a_floating_banner

## 皮肤档位口径
- 皮肤清单单点在 webui_helpers._UI_ALL(atlas/prism/console/flux); flux(第四套, plan 26-10-31-2316 S5)
  fork 自 console, 按 _UI_ALL 枚举的接线守阵随常量自动收编; 单独点名的三套成对面(HR 表②/全屏弹窗/
  表③)已显式加 flux 档。
"""

import base64

import json

import os

import re

import shutil

import subprocess

import time

from auto_qb.infra.utils import encode_group_key

from webui_helpers import read_shared
from webui_helpers import (
    KEY,
    STATIC_ROOT,
    _UI_ALL,
    _ui_shell_inline,
    _ui_aggregate,
    _ui_css_aggregate,
    _app_bundle_files,
    _app_bundle_text,
)

from webui_dom_page_support import _bundle_iter


def test_frontend_cols_store_single_setitem_site():
    """全仓前端对 COLS_STORE_KEY 的 setItem 必须恰好一处(persistPage 内) —— 唯一持久化漏斗

    plan 26-09-21-1551: 旧模型 6 个落盘点各自决定写入时机, "先存后算/先算后存"选错 3 处,
    内存/存储长期漂移(失败分析实测: 内存 12 键 / 存储 0 键)。新模型只有一个漏斗,
    散写回潮 = 本守阵红。
    """
    hits = []
    for name, text in _bundle_iter():
        text = open(os.path.join(STATIC_ROOT, name), encoding="utf-8").read()
        for i, ln in enumerate(text.splitlines(), 1):
            code = ln.split("//")[0]
            if "localStorage.setItem(COLS_STORE_KEY" in code:
                hits.append(f"{name}:{i}")
    assert len(hits) == 1 and hits[0].startswith("shared/columns"), (
        f"COLS_STORE_KEY 的 setItem 必须只存在于 columns.js 的 persistPage 内, 实测: {hits}"
    )
    cols = read_shared("columns.js")
    m = re.search(r"persistPage\s*\(\s*page\s*\)\s*\{(.*?)\n    \},", cols, re.S)
    assert m, "columns.js 找不到 persistPage(page)(改名或挪走了? 同步本守阵)"
    assert "localStorage.setItem(COLS_STORE_KEY" in m.group(1), "setItem 不在 persistPage 内? 同步本守阵"


def test_frontend_cols_legacy_keys_have_migration():
    """LEGACY_COLS_KEYS 键链必须伴随迁移函数 —— 升版必挂迁移(定案口径)

    v3->v4 升版没挂迁移, 用户手调的宽/隐/序一次性清零(四轮修复复盘第1.轮, "时不时被重置"
    的机制性来源)。v5 挂 migrateLegacyToV5; 本守阵钉住键链与迁移的耦合。
    """
    rel = "shared/app.js"
    text = open(os.path.join(STATIC_ROOT, rel), encoding="utf-8").read()
    m = re.search(r"const LEGACY_COLS_KEYS = \[(.*?)\];", text, re.S)
    assert m, f"{rel} 找不到 LEGACY_COLS_KEYS"
    keys = re.findall(r'"([^"]+)"', m.group(1))
    assert keys == [
        "autoqb_cols_v4", "autoqb_cols_v3"
    ], (f"LEGACY_COLS_KEYS 变更了({keys}) —— 升版/换键必须同步 migrateLegacyToV5 与迁移测试"
        "(plan 26-09-21-1551; v3->v4 清零事故的机检)")
    assert "function migrateLegacyToV5" in text, "LEGACY_COLS_KEYS 非空但找不到 migrateLegacyToV5(迁移函数)"
    assert "migrateLegacyToV5(raw)" in text, "readColStateRaw 未使用 migrateLegacyToV5(旧键不会被迁移)"


def test_frontend_cols_empty_hint_names_browser_clear_cause():
    """空存储提示必须点出"浏览器站点级关闭时清除站点数据"这条通道 + 自查路径 + 会话级去重

    2026-09-24 取证(真因, 非应用 bug): 用户 Edge/Chrome 的 `content_settings.exceptions.cookies`
    里都有 `127.0.0.1,*` setting=4(Chromium `CONTENT_SETTING_SESSION_ONLY`, 界面文案 = "关闭窗口时
    清除 Cookie 和站点数据") ⇒ 关浏览器时该 host 的 Cookie 与 localStorage **一起**被清, 于是
    "浏览器重启后偏好全回默认"。旧提示只写了 origin 隔离(换地址/端口), 把排查方向带偏了好几轮。
    另一层: 清站点数据的环境下 localStorage 里的"已提示"标记也一起没了 ⇒ 没有 sessionStorage
    兜底就会每次关浏览器重开都弹。
    """
    text = read_shared("columns.js")
    m = re.search(r"_showColsOriginHint\(\)\s*\{(.*?)\n    \},", text, re.S)
    assert m, "columns.js 找不到 _showColsOriginHint(改名或挪走了? 同步本守阵)"
    body = m.group(1)
    assert "关闭窗口时清除" in body, (
        "空存储提示没提浏览器站点级『关闭窗口时清除 Cookie 和站点数据』—— 用户会把整站数据被清"
        "误判成应用 bug(2026-09-24 取证: Edge/Chrome 的 cookie 例外 127.0.0.1,* setting=4)"
    )
    assert "edge://settings/content/all" in body, "提示必须给出可自查的浏览器设置路径(否则用户无从下手)"
    assert "sessionStorage" in body, "缺少 sessionStorage 兜底 ⇒ 清站点数据的环境下每次开浏览器都弹"
    assert "localStorage.setItem(COLS_ORIGIN_HINT_KEY" in body, "普通场景的跨会话去重标记(只记一次)被删了"


def test_frontend_cols_empty_hint_is_not_a_floating_banner():
    """空存储提示的出口 = 通知面板, **不得是页面浮层**(2026-10-09 用户实报: 遮挡自动化测试截图)

    旧实现运行时往 body 插一条 fixed 横幅(可点关 / 15s 自灭): 它压在页面内容上, 且**每次跑自动化
    测试都触发** —— 测试用全新浏览器上下文, 没有"已提示"去重标记, 于是每张截图底部都被盖一截。
    改道后只进通知面板(ui_feedback.js::_recordNotice): 面板默认收起、不占版面、不进截图, 入口留
    一个未读徽标。本守阵钉死"不再建浮层"这个不变量(文案 / 去重标记的守阵在上一条)。
    """
    text = read_shared("columns.js")
    m = re.search(r"_showColsOriginHint\(\)\s*\{(.*?)\n    \},", text, re.S)
    assert m, "columns.js 找不到 _showColsOriginHint(改名或挪走了? 同步本守阵)"
    body = m.group(1)
    assert "this._recordNotice(" in body, ("空存储提示没走 _recordNotice —— 出口必须是通知面板(陈述型告知一律进面板, 不占版面/不进截图)")
    for banned in ("document.createElement", "appendChild", "position:fixed", "z-index:9999"):
        assert banned not in body, (
            f"空存储提示里出现 {banned} —— 页面级浮层会压住页面内容并遮挡自动化测试截图"
            "(2026-10-09 用户实报; 陈述型提示一律走 _recordNotice)"
        )


def test_frontend_dir_browse_and_search_stale_guard():
    """目录浏览与搜索的请求代际守卫(F2-03, issue 26-10-06-0028) —— 慢响应不得覆盖新状态

    add_torrent.loadDir 快速连点 A→B 时 A 的响应后到会把 dirBrowse 覆写回 A; view.doSearch
    连续输入 a→b 时 a 的响应后到会把命中集覆写成 a(搜索框显示 b、高亮集却是 a, 无轮询
    自动纠正)。修法 = 与 drawer.js _drawerStale 同式收口: loadDir 以 path 戳(_dirReqPath)、
    doSearch 以 query 戳(落袋前比对当前 searchQuery), 守卫覆盖落袋与报错两路, 且过期请求
    不动 loading 态(新在途请求持有它, 免闪一帧"加载完"假象)。
    """
    at = open(os.path.join(STATIC_ROOT, "shared", "add_torrent.js"), encoding="utf-8").read()
    vw = open(os.path.join(STATIC_ROOT, "shared", "view.js"), encoding="utf-8").read()

    # ① loadDir: 发请求即记 path 戳
    m = re.search(r"async loadDir\(path\)\s*\{(.*?)\n    \},", at, re.S)
    assert m, "add_torrent.js 找不到 loadDir(改名或挪走了? 同步本守阵)"
    body = re.sub(r"//[^\n]*", "", m.group(1))
    assert re.search(r"const reqPath = path \|\| \"\";\s*this\._dirReqPath = reqPath;", body), \
        "loadDir 未在发请求前记录 path 戳(_dirReqPath) —— A→B 连点旧响应会覆盖新状态"
    # 落袋与报错两路都比对(截获 return 而非 continue 写状态)
    assert body.count("if (this._dirReqPath !== reqPath) return;") == 2, \
        "loadDir 落袋/报错两路都须有过期响应丢弃守卫(恰两处)"
    assert "if (this._dirReqPath === reqPath) this.dirBrowse.loading = false;" in body, \
        "loadDir finally 未按戳守卫 —— 过期请求会闪一帧\"加载完\"假象(新在途请求持有 loading)"

    # ② doSearch: 落袋前比对当前搜索词
    # quiet 参数(plan 26-11-03-0120 F2): 静默刷新复用同一落袋路径, 签名容忍可选参
    m = re.search(r"async doSearch\([^)]*\)\s*\{(.*?)\n    \},", vw, re.S)
    assert m, "view.js 找不到 doSearch(改名或挪走了? 同步本守阵)"
    body = re.sub(r"//[^\n]*", "", m.group(1))
    assert body.count('if ((this.searchQuery || "").trim() !== q) return;') == 2, \
        "doSearch 落袋/报错两路都须比对当前搜索词(query 戳) —— 慢响应会把命中集覆写成旧词的"


def test_web_store_iteration_snapshot_race_guard(tmp_path):
    """Web 读侧快照竞态守阵(E-01, issue 26-10-06-0028) —— 迭代 store 期间原地增删不 500

    remove_torrent/restore_torrent(原地 pop/赋值)/reset_runtime(groups.clear)/
    grouping_mod._leave_group(del) 都在主循环线程; /api/search、/api/paths、/api/hr/*/entries
    与 Web 请求触发的视图重建(_build_* 系)在 Web 线程无锁迭代同一批 dict —— 修复前大库
    重叠窗口内必抛 "dictionary changed size during iteration"。守阵 = 写线程高频原地增删
    by_hash/groups/cross_group_conflict_warned 期间连续跑全部读侧迭代面, 断言零异常
    (读侧快照后 mutation 不再打进迭代中的 dict 视图; 写线程只碰非组员 hash, 免得踩
    组员快照的 by_hash[h] 查找 —— 那是成员一致性语义, 不属本条)。
    """
    import threading

    from auto_qb.webui.server.routes.hr import mark_local_present
    from helpers import FakeTorrent, make_manager

    mgr = make_manager(str(tmp_path / "state.json"))
    n = 20000
    for i in range(n):
        mgr.store.by_hash[f"h{i}"] = FakeTorrent(hash=f"h{i}", name=f"t{i} 2026")
    # 分组索引给一点真形: 组 key = (save_path, files); 组员固定不动(见 docstring 口径)
    gkey = ("R:/seeds", ("a.mkv", ))
    mgr.store.groups[gkey] = ["h0", "h1", "h2"]
    mgr.store.cross_group_conflict_warned.add(("R:/seeds", "R:/other"))

    stop = threading.Event()

    def writer():
        i = 0
        while not stop.is_set():
            h = f"new{i}"
            mgr.store.by_hash[h] = FakeTorrent(hash=h, name="x")  # restore_torrent 形
            mgr.store.by_hash.pop(h, None)  # remove_torrent 形
            if i % 100 == 0:
                mgr.store.groups[(f"R:/tmp{i}", ())] = []  # _leave_group / reset_runtime 形
                mgr.store.groups.pop((f"R:/tmp{i}", ()), None)
                mgr.store.cross_group_conflict_warned.add((f"R:/tmp{i}", "R:/x"))
                mgr.store.cross_group_conflict_warned.discard((f"R:/tmp{i}", "R:/x"))
            i += 1

    t = threading.Thread(target=writer, daemon=True)
    t.start()
    errors = []
    try:
        deadline = time.time() + 2.0
        while time.time() < deadline and not errors:
            try:
                mgr.search_torrents("t1")
                mgr._build_group_view()
                mgr._build_singles_view()
                mgr._build_flat_view()
                mgr._build_speed_totals()
                mgr._build_shows_view()
                mark_local_present([{"infohash_v1": "h1", "infohash_v2": ""}], mgr.store.by_hash)
            except RuntimeError as e:  # 修复前必抛: dictionary changed size during iteration
                errors.append(e)
    finally:
        stop.set()
        t.join()
    assert not errors, f"Web 读侧迭代与主循环原地增删并发仍崩溃: {errors[0]!r}"
