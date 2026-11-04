"""test_web_backend_misc_sites 测试计划: WEB 后端杂项: config / token / sites / 分组视图 / 错误原因

## 测试计划(每个测试函数一条)
- test_sites_missing_scans_and_builds_defaults: GET /api/sites/missing 未配置域名生成默认条目(domains/tags/占位限速/hr 示例值与 --export-yaml 同源); 已配置域名双向包含不重复
- test_sites_missing_name_conflict_suffix: 站点名冲突(既有配置占用/批内同名) -> _N 后缀(与 CLI 导出同一套 gen_tracker_name)
- test_sites_missing_all_covered_returns_empty: 全部域名已被覆盖 -> sites 空数组
- test_sites_missing_requires_connected_client: qB 断连 -> 503(不得拿空扫描冒充"没有缺失站点")
- test_sites_missing_api_failure_maps_502: 扫描中途 qB 调用失败 -> 502 带原因(不裸 500)
- test_sites_missing_batch_tracker_failure_maps_502: 逐种 tracker 查询过半失败 -> 502 拒出结果
  (不拿空集冒充「无缺失站点」误导前端分支1, issue 26-11-04-2347)
- test_sites_missing_single_tracker_failure_tolerated: 单种失败(未过半)仍容忍, 正常出结果
- test_sites_missing_groups_merge_cooccurring_domains: 同一颗种子共现的两缺失域名 -> groups 一条(domains 两元素 sorted、name=代表名=组内最短域名、entry 为后端单点产出的合并条目, 与 CLI 合并导出同规则)
- test_sites_missing_groups_single_domains_match_sites: 无共现全单元素组 -> groups 与 sites 一一对应且 domains 单元素、entry 键存在; sites 保持 name/domain/entry 三键原形
- test_sites_missing_no_missing_groups_empty: 无缺失域名 -> groups 空数组(与 sites 空数组同现)
- test_frontend_sites_import_wiring: 一键导入按钮接线守阵 —— 两套 UI 站点 pill 行都挂「⤓ 导入缺失站点」+ config_hub.js 的 hubImportSites/防重入标志 + M4 三分支自适应引导(sites 空 toast 不变 / 无 >=2 域名组走现状逐域名单点 / 有多域名组弹 confirmThreeDialog 三钮, ok=合并导入(Enter 默认)·extra=拆分导入(ghost 样式, 复用逐域名单点)·cancel 不做) + 合并模式键=groups[i].name 值=groups[i].entry + 合并明细列前 10 组超限折叠 + ui_feedback extraStyle 契约(缺省 "" 兜底 danger-solid 零变化, ghost 落地单点 _applyExtraBtnGhost)
- test_frontend_tracker_search_wiring: 站点页搜索接线守阵(计划 26-09-27-1852) —— 模板三件套(输入绑定/清空钮/计数) + 归一化必须 \\p{L}\\p{N}(u 标志, ASCII \\W 折碎中文词) + 收层路径四条一律清词单点(点命中/Esc/点暗幕/点外即收; 方案C 聚焦层 2026-09-29 拍板) + 聚焦层开合/键盘导航/IME 守卫 + 悬停接管位移门限(治上下键选中项闪烁 2026-09-29) + 键盘活动项滚动跟随(26-09-29-2142) + pill 无键数徽标 + 行尾动作区分形 + hb-tr-* 类 CSS 成对定义
- test_frontend_dialog_combo_hover_takeover: 弹窗下拉悬停接管守阵(issue 26-09-29-2142, 站点搜索闪烁同族) —— 分类/标签/编辑分类下拉 @mousemove+3px 位移门限共享小工具(comboHoverIdx) + @mouseenter 直写零残留 + 门限坐标 state 声明 + 开层单点复位 + 三皮肤 data-hi 行 CSS 摘 :hover(高亮只走 .on 单路)
- test_frontend_search_help_wiring: 顶栏搜索语法浮卡接线守阵(计划 26-09-28-0201 方案A) —— 模板(「?」钮/浮卡/示例回填/简化占位符) + state 声明 + view.js 方法(回填即搜) + 点空白/Esc/导航三条收起路径 + 三皮肤 CSS 成对定义与 input 右内边距留位
"""

import logging

import os

import re

import time

from types import SimpleNamespace

import pytest

from auto_qb.infra.utils import decode_group_key, encode_group_key

from webui_helpers import read_shared
from webui_helpers import WEB_ENV_CONFIG_TEXT, _make_web_manager, STATIC_ROOT, _UI_ALL, _ui_aggregate


def _site_scan_env(web_env, trackers_by_hash):
    """给 web_env 的 manager 挂上站点扫描所需的最小 api/client 替身"""
    from types import SimpleNamespace

    mgr, client = web_env
    mgr.client = object()  # require_client 只判 None
    # collect_all_tracker_hostnames 按 tor.hash 属性取 hash(QbApi 同形), 不能给 dict
    torrents = [SimpleNamespace(hash=h) for h in trackers_by_hash]
    mgr.api = SimpleNamespace(
        torrents_info=lambda **kw: list(torrents),
        torrents_trackers=lambda h: list(trackers_by_hash.get(h, [])),
    )
    return mgr, client


def test_sites_missing_scans_and_builds_defaults(web_env):
    """GET /api/sites/missing: 未配置域名生成默认条目; 已配置域名(双向包含)不重复出现"""
    mgr, client = _site_scan_env(
        web_env,
        {
            "T1": [{
                "url": "https://tracker.d.com/announce"
            }, {
                "url": "http://tracker.newsite.org/announce"
            }],
            "T2": [{
                "url": "https://tracker.d.com/announce"
            }],
        },
    )
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    data = client.get("/api/sites/missing", headers=auth).json()
    assert data["torrents"] == 2 and data["domains"] == 2
    assert [s["name"] for s in data["sites"]] == ["tracker_newsite_org"]
    entry = data["sites"][0]["entry"]
    assert entry["domains"] == ["tracker.newsite.org"]
    assert entry["tags"] == ["Newsite"], "默认标签 = 倒数第二级域名首字母大写"
    assert entry["upload_speed_limit"] == "0KiB/s", "占位限速与 --export-yaml 同源"
    assert entry["hr"]["required_seeding_time"] == "3D", "hr 示例值与 --export-yaml 同源"


def test_sites_missing_name_conflict_suffix(web_env):
    """站点名冲突: 既有配置占用目标名 / 批内清洗同名 -> _N 后缀(与 CLI 导出同一套 gen_tracker_name)"""
    from types import SimpleNamespace

    mgr, client = _site_scan_env(
        web_env,
        {"T1": [{
            "url": "http://a.b.com/announce"
        }, {
            "url": "http://a-b.com/announce"
        }]},
    )
    mgr.config.trackers["a_b_com"] = SimpleNamespace(domains=["zzz.com"])  # 占用目标名但域名不覆盖缺失域
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    data = client.get("/api/sites/missing", headers=auth).json()
    assert [s["name"] for s in data["sites"]] == ["a_b_com_1", "a_b_com_2"]


def test_sites_missing_all_covered_returns_empty(web_env):
    """全部域名已被配置覆盖 -> sites 空数组(前端据此提示"没有发现未配置的站点")"""
    mgr, client = _site_scan_env(web_env, {"T1": [{"url": "https://tracker.d.com/announce"}]})
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    data = client.get("/api/sites/missing", headers=auth).json()
    assert data["sites"] == []


def test_sites_missing_requires_connected_client(web_env):
    """qB 断连 -> 503(不得拿空扫描结果冒充"没有缺失站点")"""
    mgr, client = web_env  # stub 默认 client=None
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    assert client.get("/api/sites/missing", headers=auth).status_code == 503


def test_sites_missing_api_failure_maps_502(web_env):
    """扫描中途 qB 调用失败 -> 502 带原因(不裸 500)"""
    from types import SimpleNamespace

    def _boom(**kw):
        raise RuntimeError("boom")

    mgr, client = web_env
    mgr.client = object()
    mgr.api = SimpleNamespace(torrents_info=_boom)
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    resp = client.get("/api/sites/missing", headers=auth)
    assert resp.status_code == 502 and "boom" in resp.json()["detail"]


def test_sites_missing_batch_tracker_failure_maps_502(web_env):
    """逐种 tracker 查询过半失败 -> 502 拒出结果(issue 26-11-04-2347)

    torrents_info() 成功而逐种 tracker 请求全失败(qB 重启/断连)曾被吞成空 sites/groups,
    前端按分支1提示「无需导入」—— 现在过半失败必须 502 且 detail 带失败比例。
    """
    from types import SimpleNamespace

    def _boom(h):
        raise RuntimeError("tracker query lost")

    mgr, client = web_env
    mgr.client = object()
    torrents = [SimpleNamespace(hash=f"H{i}") for i in range(3)]
    mgr.api = SimpleNamespace(torrents_info=lambda **kw: list(torrents), torrents_trackers=_boom)
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    resp = client.get("/api/sites/missing", headers=auth)
    assert resp.status_code == 502
    detail = resp.json()["detail"]
    assert "批量失败" in detail and "3/3" in detail, "detail 必须带失败比例(排障可读)"


def test_sites_missing_single_tracker_failure_tolerated(web_env):
    """单种失败(未过半)仍容忍: 该种空集不触发 502, 其余种子正常出结果(回归守阵)"""
    from types import SimpleNamespace

    def trackers(h):
        if h == "H1":
            raise RuntimeError("boom")
        return [{"url": "https://tracker.d.com/announce"}]

    mgr, client = web_env
    mgr.client = object()
    torrents = [SimpleNamespace(hash="H1"), SimpleNamespace(hash="H2")]
    mgr.api = SimpleNamespace(torrents_info=lambda **kw: list(torrents), torrents_trackers=trackers)
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    resp = client.get("/api/sites/missing", headers=auth)
    assert resp.status_code == 200
    assert resp.json()["torrents"] == 2


def test_sites_missing_groups_merge_cooccurring_domains(web_env):
    """groups(计划 26-11-03-2337 M3): 同一颗种子共现的两缺失域名 -> 合并成一条组

    分组/代表名与 CLI 合并导出同一套构件(group_missing_domains / build_merged_entry):
    代表域名 = 组内最短(tie 取字典序), domains 组内 sorted。
    """
    mgr, client = _site_scan_env(
        web_env,
        {"T1": [{
            "url": "https://www.longptsite.com/announce"
        }, {
            "url": "http://abc.pt/announce"
        }]},
    )
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    data = client.get("/api/sites/missing", headers=auth).json()
    assert len(data["groups"]) == 1, "同一颗种子共现 -> 只并成一条组"
    g = data["groups"][0]
    assert g["domains"] == ["abc.pt", "www.longptsite.com"], "组内域名 sorted"
    # 代表名 = 最短域名 abc.pt 的清洗名; 组名按 CLI 同规则单独查重(不叠加 sites 的 _1 后缀)
    assert g["name"] == "abc_pt"
    assert "entry" in g and g["entry"]["domains"] == ["abc.pt", "www.longptsite.com"], \
        "合并 entry 由后端单点产出(build_merged_entry), domains 键为组内全域名"


def test_sites_missing_groups_single_domains_match_sites(web_env):
    """groups 退化形态: 无共现全单元素组 -> 与 sites 一一对应且 domains 单元素; sites 原形不变"""
    mgr, client = _site_scan_env(
        web_env,
        {
            "T1": [{
                "url": "http://alpha.io/announce"
            }],
            "T2": [{
                "url": "http://beta.net/announce"
            }],
        },
    )
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    data = client.get("/api/sites/missing", headers=auth).json()
    assert [g["domains"] for g in data["groups"]] == [["alpha.io"], ["beta.net"]]
    assert [g["domains"][0] for g in data["groups"]] == [s["domain"] for s in data["sites"]], \
        "全单元素组时 groups 与 sites 按序一一对应"
    assert [g["name"] for g in data["groups"]] == ["alpha_io", "beta_net"], \
        "组名按 CLI 同规则单独查重(与 sites 逐域名名互不占用)"
    for g in data["groups"]:
        assert "entry" in g, "groups 每条带合并 entry(前端合并模式直接用)"
    for s in data["sites"]:
        assert set(s.keys()) == {"name", "domain", "entry"}, "sites 保持逐域名三键原形(加字段零破坏)"


def test_sites_missing_no_missing_groups_empty(web_env):
    """无缺失域名 -> groups 空数组(与 sites 空数组同现, 前端维持现状路径)"""
    mgr, client = _site_scan_env(web_env, {"T1": [{"url": "https://tracker.d.com/announce"}]})
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    data = client.get("/api/sites/missing", headers=auth).json()
    assert data["sites"] == [] and data["groups"] == []


def test_frontend_sites_import_wiring():
    """一键导入缺失站点的前端接线守阵(2026-09-26; M4 三分支引导 计划 26-11-03-2337)

    两套 UI 的站点 pill 行都必须挂「⤓ 导入缺失站点」按钮并调用 config_hub.js 的
    hubImportSites —— 漏一套那套 UI 就没有入口; 防重入标志 hub.importing 必须存在。
    M4(2026-11-04): 后端 /api/sites/missing 已带 groups(共现合并组, 组数可为 0), 前端
    三分支自适应 —— ①sites 空 -> 现状 toast; ②不存在 >=2 域名的组(groups 缺省/为空/全单
    元素) -> 现状 confirmDialog 逐域名导入(路径零变化, 抽成 _hubImportPerDomain 单点,
    分支②与「拆分导入」共用一份不留拷贝); ③存在 >=2 域名的组 -> confirmThreeDialog
    三钮(ok=合并导入[Enter 默认·推荐] / extra=拆分导入[extraStyle:"ghost" —— 拆分不是
    破坏性动作] / cancel=取消)。合并模式键 = groups[i].name、值 = groups[i].entry
    (entry.domains 已含组内全域名), 同名键跳过语义与逐域名路径一致。
    """
    hub_js = read_shared("config_hub.js")  # 聚合含 config_hub_tracker.js(hubImportSites 落点)
    assert "async hubImportSites()" in hub_js, "config_hub.js 缺 hubImportSites 方法"
    assert "this.hub.importing" in hub_js, "缺防重入标志 hub.importing"
    # 分支①: sites 空 -> 现状 toast(不变)
    assert "没有发现未配置的站点" in hub_js, "缺「无需导入」空态提示(分支①被改坏?)"
    # 分支②/拆分共用逐域名单点(不留两份拷贝); 逐域名键 = sites[i].name
    assert "async _hubImportPerDomain(sites)" in hub_js, \
        "缺逐域名导入单点(分支②与拆分导入必须共用一份, 各抄一份 = 行为漂移温床)"
    assert "trackers[s.name] = s.entry" in hub_js, "逐域名模式键必须是 sites[i].name"
    assert "Object.prototype.hasOwnProperty.call(trackers, s.name)" in hub_js, \
        "逐域名判重必须只认自有键(防 constructor/__proto__ 继承属性误判已存在)"
    assert hub_js.count("_hubImportPerDomain(sites)") >= 3, \
        "分支②与 extra 分支都要调逐域名单点(方法定义 + 两处调用)"
    # 分支③闸门: 只有存在 >=2 域名的组才引导(D4: 会真实合并才弹框, 否则空转)
    assert "some((g) => (g.domains || []).length >= 2)" in hub_js, \
        "缺多域名组闸门(缺了 = 全单域名场景也弹三钮, 现状路径被无谓改写)"
    assert 'confirmThreeDialog(' in hub_js, "缺三钮弹窗入口(分支③)"
    assert 'okText: "合并导入"' in hub_js and 'extraText: "拆分导入"' in hub_js, \
        "三钮文案错(合并=ok 且 Enter 默认推荐, 拆分=extra)"
    assert 'extraStyle: "ghost"' in hub_js, \
        "拆分钮必须传 extraStyle:\"ghost\"(非破坏性动作不该渲染成 danger-solid 红钮)"
    # 合并模式: 键 = groups[i].name, 值 = groups[i].entry(后端单点产出的合并条目)
    assert "trackers[g.name] = g.entry" in hub_js, "合并模式必须用 groups[i].name/entry 作键值"
    assert "Object.prototype.hasOwnProperty.call(trackers, g.name)" in hub_js, \
        "合并判重必须只认自有键(防 constructor/__proto__ 继承属性误判已存在)"
    assert "合并明细" in hub_js and "另有" in hub_js, \
        "三钮 body 必须带合并明细(列前 10 组 Name(d1、d2), 超出折叠「…另有 N 组」)"
    assert "const DETAIL_MAX = 10;" in hub_js and "groups.slice(0, DETAIL_MAX)" in hub_js \
        and "groups.length - DETAIL_MAX" in hub_js, \
        "合并明细截断三件套(DETAIL_MAX / slice 上限 / 折叠计数)缺一即回归"
    # ui_feedback 侧 extraStyle 契约: 缺省 "" = danger-solid 现状(既有调用点零变化),
    # ghost 只认白名单值, 落地单点 = _applyExtraBtnGhost(模板第三钮类静态, 只能开框后换类)
    fb = read_shared("ui_feedback.js")
    assert 'extraStyle: "",' in fb, "ui_feedback _modalInit 缺 extraStyle 缺省声明(漏声明 = 既有框读到 undefined)"
    assert 'extraStyle: opts.extraStyle === "ghost" ? "ghost" : ""' in fb, \
        "extraStyle 必须白名单归一(任意字符串不得经 opts 流进 DOM 类名)"
    assert "_applyExtraBtnGhost()" in fb and "extraStyle === \"ghost\"" in fb, \
        "缺 ghost 落地单点(缺省路径必须完全不走 DOM 改动 = 既有三钮框渲染逐字节不变)"
    for ui in _UI_ALL:
        html = _ui_aggregate(ui)
        assert "hubImportSites()" in html, f"{ui} 站点分区缺导入按钮"
        assert "导入缺失站点" in html, f"{ui} 缺导入按钮文案"


def test_frontend_tracker_search_wiring():
    """站点页搜索接线守阵(静态防回潮, 计划 26-09-27-1852; 方案C 聚焦搜索层 2026-09-29 拍板)

    trackers 二级页搜索是纯前端实现, pytest 运行时看不见, 断链都是静默的:
      1. 模板三件套(输入框绑定 / 清空钮 / 计数)与命中行结构缺一 = 搜索入口废;
      2. 归一化必须用 [^\\p{L}\\p{N}](u 标志) —— JS 的 ASCII \\W 是 Unicode 语义的反面,
         会把整个中文词折成空格, 中文搜索静默失效(Python \\W 的同语义直译陷阱);
      3. 收层路径四条(点命中 / Esc / 点暗幕 / 点外即收)一律走 hubTrackerStageClose 清词单点 ——
         漏一条 = 层赖着盖详情(「不主动消失」报障的根因);
      4. 聚焦层开合(聚焦或有词即开) + 键盘导航(↑↓ 移动 / Enter 打开) + IME 组词守卫(方案C)
         + 悬停接管(mousemove + 3px 位移门限, 静止光标/合成事件不夺活动项 —— 治上下键选中项闪烁 2026-09-29)
         + 键盘活动项滚动跟随(↑↓ 后 .act 行滚进 300px 列表视野, 手动 scrollTop 差值, 禁 scrollIntoView —— 26-09-29-2142);
      5. 站点 pill 不带配置键数徽标(26-09-27 拍板); 新增/导入收进行尾动作区与站点 pill 分形(P4);
      6. 模板用到的 hb-tr-* 类必须在 console_hub.css 有定义(挂件类名错配变体)。
    """
    tpl = open(os.path.join(STATIC_ROOT, "shared", "tpl", "settings.html"), encoding="utf-8").read()
    for token in (
        'v-model="cfg.trackerQuery"',
        "hubTrackerClear()",
        "hubTrackerCountText",
        "hubTrackerHits.hits",
        'class="hb-tr-drop"',  # 命中面板(v-if hubTrackerStageOpen)仍挂搜索行下
        'class="hb-tr-detail"',
        "hb-tr-hit",
        "hb-tr-chip",
        # 方案C 聚焦层结构: 舞台 + 暗幕 + 开合 + 键盘 + 面板头尾 + 行尾动作区
        "hb-tr-stage",
        "hubTrackerStageOpen",
        "hb-tr-veil",
        "hubTrackerStageClose(true)",
        'ref="trackerSearchInput"',
        "hub.trackerSearchFocus = true",
        "hubTrackerKeydown($event)",
        '@mousemove="hubTrackerHoverIdx(i, $event)"',  # 悬停接管走位移门限(治上下键选中项闪烁)
        "hb-tr-drop-hd",
        "hb-tr-drop-ft",
        "hb-pill-tail",
        "hubAddTracker(cfg.trackerQuery.trim())",  # 面板尾快捷新增把搜索词带进命名框
    ):
        assert token in tpl, f"shared/tpl/settings.html 缺少 {token}(站点搜索模板被改坏? 同步本守阵)"
    pills = re.search(r'class="hb-pills"(.*?)</div>', tpl, re.S)
    assert pills, "trackers pill 行找不到(结构改名? 同步本守阵)"
    assert "hubCount" not in pills.group(1), "站点 pill 不应显示配置键数徽标(hubCount), 26-09-27 拍板"
    assert "hb-pill-tail" in pills.group(1) and "hubImportSites()" in pills.group(1), \
        "行尾动作区(新增/导入)必须留在 pill 行内(P4: 与站点 pill 分形分位)"
    # 2. 逻辑层单点: CJK 安全归一化 + 解析 / 行索引 / 命中 / 清空 / 收层 / 键盘
    hub = read_shared("config_hub.js")
    assert re.search(r"replace\(/\[\^\\p\{L\}\\p\{N\}\]\+/gu",
                     hub), ("站点归一化必须用 [^\\p{L}\\p{N}](u 标志): ASCII \\W 会把整个中文词折成空格")
    for token in (
        "trackerParseQuery(q)",
        "trackerRows(name, entry)",
        "hubTrackerHits()",
        "hubTrackerClear()",
        "hubTrackerPick(name)",
        "hubTrackerStageClose(blurInput)",
        "hubTrackerKeydown(e)",
        "hubTrackerHoverIdx(i, ev)",
        "trackerMouseAt: null",
        "trackerSearchFocus: false",
        "trackerHitIdx: -1",
    ):
        assert token in hub, f"shared/config_hub.js 缺少 {token}"
    keydown = re.search(r"hubTrackerKeydown\(e\) \{(.*?)\n    \},", hub, re.S)
    assert keydown and "isComposing" in keydown.group(1) and "ArrowDown" in keydown.group(1) \
        and "Enter" in keydown.group(1), "键盘导航必须含 ↑↓/Enter 且 IME 组词中不劫持(isComposing 守卫)"
    # 2.b 滚动跟随(26-09-29-2142): 命中列表 max-height 300px 可滚, ↑↓ 只改 idx 不推滚动条,
    #    长列表上高亮走出可视区 = 键盘选择不可用。手动差值调 scrollTop, 禁 scrollIntoView(连带滚整页)。
    assert keydown and "hubTrackerScrollActIntoView" in keydown.group(1), \
        "↑↓ 改 idx 后必须调 hubTrackerScrollActIntoView 滚动跟随(长列表高亮走出视野)"
    scrollfn = re.search(r"hubTrackerScrollActIntoView\(\) \{(.*?)\n    \},", hub, re.S)
    assert scrollfn, "缺 hubTrackerScrollActIntoView() 实现(改名/挪走? 同步本守阵)"
    scbody = scrollfn.group(1)
    assert "getBoundingClientRect" in scbody and "scrollTop" in scbody, \
        "滚动跟随必须手动差值调 scrollTop(只滚命中列表自身, block:nearest 语义)"
    assert "scrollIntoView" not in scbody, \
        "不得用 scrollIntoView(逐层滚动所有可滚祖先, 连带滚动暗幕后面的整页产生二次干扰)"
    # 3. 收层单点四条路径: 点命中 / Esc(hubOnKey) / 点暗幕(veil) / 点外即收(hubOnDocClick) —— 全部清词
    pick = re.search(r'@click="(hubTrackerPick\(h\.name\))"', tpl)
    assert pick, "命中行 @click 必须接 hubTrackerPick —— 只选中不清词会把切站效果留在暗幕底下(死锁)"
    assert '@mouseenter="hub.trackerHitIdx' not in tpl, \
        "命中行不得挂 @mouseenter(静止光标的旧高亮与键盘活动项同源打架 = 上下键选中项闪烁), 悬停接管走 hubTrackerHoverIdx"
    veil = re.search(r'class="hb-tr-veil" @click="(hubTrackerStageClose\(true\))"', tpl)
    assert veil, "暗幕 @click 必须接 hubTrackerStageClose(true) —— 点暗幕 = 清词收层退聚焦层"
    docclick = re.search(r"hubOnDocClick\(e\) \{(.*?)\n    \},", hub, re.S)
    assert docclick and 'closest(".hb-tr-stage")' in docclick.group(1) \
        and "hubTrackerStageClose(true)" in docclick.group(1), \
        "hubOnDocClick 必须含点外即收(closest .hb-tr-stage 豁免 stage 内点击)"
    onkey = re.search(r"hubOnKey\(e\) \{(.*?)\n    \},", hub, re.S)
    assert onkey and "isComposing" in onkey.group(1), "hubOnKey 必须 IME 组词守卫(组词中 Esc 归输入法)"
    assert onkey and "hubTrackerStageClose(true)" in onkey.group(1), "Esc 必须清词收层退聚焦层"
    for fn in ("hubGo(key)", "hubBack()"):
        body = re.search(rf"{re.escape(fn)} \{{(.*?)\n    \}},", hub, re.S)
        assert body and "hubTrackerStageClose(false)" in body.group(1), \
            f"{fn} 必须走收层单点(离开分区不带搜索残留, 聚焦态一并复位)"
    closefn = re.search(r"hubTrackerStageClose\(blurInput\) \{(.*?)\n    \},", hub, re.S)
    assert closefn and 'this.cfg.trackerQuery = ""' in closefn.group(1) \
        and "trackerSearchFocus = false" in closefn.group(1) \
        and "trackerMouseAt = null" in closefn.group(1), \
        "收层单点必须清词 + 复位聚焦态 + 复位悬停门限坐标(跳转器拍板: 收层一律清词)"
    ed = read_shared("config_editor.js")
    assert 'trackerQuery: ""' in ed, "cfg.trackerQuery 必须在 config_editor.js state 声明(漏声明 = 响应性缺失)"
    # 6. CSS 成对: 模板用到的 hb-tr-* 类都要有规则
    css = read_shared("console_hub.css")
    for cls in (
        "hb-tr-stage",
        "hb-tr-veil",
        "hb-tr-search",
        "hb-tr-x",
        "hb-tr-drop",  # 命中面板(方案C: 头/列表/尾三段式)
        "hb-tr-drop-hd",
        "hb-tr-drop-list",
        "hb-tr-drop-ft",
        "hb-tr-detail",
        "hb-tr-hit",
        "hb-tr-hit-name",
        "hb-tr-cur",
        "hb-tr-chips",
        "hb-tr-chip",
        "hb-tr-hint",
        "hb-pill-tail",
        "hb-btn.dashed",
    ):
        assert "." + cls in css, f"console_hub.css 缺少 .{cls} 定义(挂件类名错配 = 静默裸样式)"
    assert ".hb-tr-hit.act" in css and "hb-tr-hit:hover" not in css, \
        "命中行高亮只走 .act —— CSS :hover 会跟键盘活动项双高亮打架(闪烁根因之一), 悬停接管在 hubTrackerHoverIdx"


def test_frontend_dialog_combo_hover_takeover():
    """弹窗下拉悬停接管守阵(issue 26-09-29-2142, 站点搜索闪烁同族, 2026-09-29 修)

    添加种子分类/标签下拉与编辑弹窗分类下拉原是 @mouseenter 直写键盘活动项 —— 光标静止停在
    列表上用 ↑↓ 选择时, 行滚动/DOM 变更后浏览器给静止光标补发合成 hover 事件, 活动项被拽回
    光标行(改前真机实测: ↓×16 轨迹两次被拽回, Enter 选中 cat-06 而非键盘到达的 cat-16 ——
    不止闪烁, 实选错)。处置(hover-keynav-fight 同款): 1. 悬停接管走 @mousemove + 3px 位移
    门限(comboHoverIdx 共享小工具, 三处不各抄一份); 2. CSS 摘 data-hi 行的 :hover, 高亮只走
    .on 一条路; 3. 开层单点复位门限坐标(下次打开首个动作不被旧坐标误挡)。
    """
    mgr = open(os.path.join(STATIC_ROOT, "shared", "tpl", "dialogs-mgr.html"), encoding="utf-8").read()
    pop = open(os.path.join(STATIC_ROOT, "shared", "tpl", "popovers.html"), encoding="utf-8").read()
    # 收敛 issue 26-10-20-2230: 分类/标签/meta 三处下拉的候选行进共享组件 #tpl-combo-input
    # (xtpl.html), 悬停接线 = 模板 @mousemove=comboOnHover -> 组件方法按 comboKey 转发
    # $root.comboHoverIdx; 调用点只传 combo-key(cat/tag/meta) —— 门限判据/分存坐标仍是下方单点
    xt = open(os.path.join(STATIC_ROOT, "shared", "tpl", "combo-input.html"), encoding="utf-8").read()
    tpl_seg = re.search(r'id="tpl-combo-input">([\s\S]*?)</script>', xt, re.S)
    assert tpl_seg, "combo-input.html 找不到 #tpl-combo-input(combobox 共享模板, 悬停接线被改坏? 同步本守阵)"
    assert '@mousemove="comboOnHover(i, $event)"' in tpl_seg.group(1), \
        "组件模板候选行缺 @mousemove=comboOnHover(悬停接管走位移门限, 治上下键选中项闪烁)"
    assert "@mouseenter" not in tpl_seg.group(1), \
        "组件模板候选行不得挂 @mouseenter(静止光标旧高亮与键盘活动项同源打架 = 上下键选中项闪烁/Enter 选错), 悬停接管走 comboHoverIdx"
    at = open(os.path.join(STATIC_ROOT, "shared", "add_torrent.js"), encoding="utf-8").read()
    fwd = re.search(r"comboOnHover\(i, ev\) \{(.*?)\n    \},", at, re.S)
    assert fwd and "if (this.comboKey)" in fwd.group(1), \
        "comboOnHover 必须守 comboKey 空值(保存路径面板无悬停/键盘互斥面, 空 = 不接管)"
    assert fwd and "this.$root.comboHoverIdx(this.comboKey, i, ev)" in fwd.group(1), \
        "comboOnHover 必须按 comboKey 转发 $root.comboHoverIdx(转发断链 = 悬停接管失效)"
    for kind in ("cat", "tag"):
        assert f'combo-key="{kind}"' in mgr, \
            f"dialogs-mgr.html 缺少 combo-key=\"{kind}\"(分类/标签下拉悬停接线被改坏? 同步本守阵)"
    assert "@mouseenter=\"addCatHi" not in mgr and "@mouseenter=\"addTagHi" not in mgr, \
        "分类/标签下拉行不得挂 @mouseenter(静止光标旧高亮与键盘活动项同源打架 = 上下键选中项闪烁/Enter 选错), 悬停接管走 comboHoverIdx"
    assert 'combo-key="meta"' in pop, "popovers.html 缺少 combo-key=\"meta\"(meta 分类下拉悬停接线, 同步本守阵)"
    assert "@mouseenter=\"metaCatHi" not in pop, "编辑弹窗分类下拉行不得挂 @mouseenter(同族打架), 悬停接管走 comboHoverIdx"
    # 1. 门限坐标三字段声明(漏声明 = 响应性缺失) + 共享小工具单点实现(别三处各抄一份)
    st = open(os.path.join(STATIC_ROOT, "shared", "state.js"), encoding="utf-8").read()
    for token in ("addCatMouseAt: null", "addTagMouseAt: null", "metaCatMouseAt: null"):
        assert token in st, f"state.js 缺少 {token}(门限坐标未声明 = 响应性缺失)"
    assert "comboHoverIdx(kind, i, ev)" in at, "缺 comboHoverIdx 共享小工具(三处下拉共用, 别各抄一份)"
    fn = re.search(r"comboHoverIdx\(kind, i, ev\) \{(.*?)\n    \},", at, re.S)
    assert fn and "dx * dx + dy * dy < 9" in fn.group(1), \
        "悬停接管必须带 3px 位移门限(合成事件位移恒 0 被挡, 真实移动才接管)"
    # 3. 开层单点复位门限坐标(下次打开首个动作不被旧坐标误挡)
    for fnname, field in (("openAddCatMenu", "addCatMouseAt"), ("openAddTagMenu", "addTagMouseAt")):
        body = re.search(rf"{fnname}\(\) \{{(.*?)\n    \}},", at, re.S)
        assert body and f"{field} = null" in body.group(1), \
            f"{fnname} 必须复位 {field}(开层复位门限坐标)"
    dlg = read_shared("dialogs.js")
    body = re.search(r"openMetaCatMenu\(\) \{(.*?)\n    \},", dlg, re.S)
    assert body and "metaCatMouseAt = null" in body.group(1), \
        "openMetaCatMenu 必须复位 metaCatMouseAt(开层复位门限坐标)"
    # 2. CSS 单路高亮: 三皮肤 data-hi 行摘 :hover(.on 活动项是唯一高亮通道)
    for rel in (
        os.path.join("atlas", "css",
                     "dialogs.css"), os.path.join("console", "css",
                                                  "dialogs.css"), os.path.join("prism", "css", "dialogs.css")
    ):
        css = open(os.path.join(STATIC_ROOT, rel), encoding="utf-8").read()
        assert ".pop-item[data-hi]:not(.on):hover" in css, \
            f"{rel} 缺 data-hi 行 hover 中和规则(CSS :hover 与键盘活动项双高亮 = 闪烁根因之一)"


def test_frontend_search_help_wiring():
    """顶栏搜索语法浮卡接线守阵(计划 26-09-28-0201 方案A) —— 模板(帮助钮/浮卡/示例回填/简化占位符)
    + state 声明(漏声明 = 响应性缺失) + view.js 方法(回填即搜/焦点还给输入框)
    + 三条收起路径(点空白/Esc/导航) + 三皮肤 CSS 成对定义(挂件类名错配 = 静默裸样式)"""
    tpl = open(os.path.join(STATIC_ROOT, "shared", "tpl", "topbar.html"), encoding="utf-8").read()
    for token in (
        'placeholder="搜索种子或文件名..."',  # 占位符简化(语法细节移交浮卡), 26-09-28 用户拍板
        'class="search-help"',
        "'no-clear': !searchQuery",  # 空框无清空钮时「?」右移补位(6px), 有词退回 27px —— 26-09-28 用户
        "toggleSearchHelp",
        'class="search-help-pop"',
        "searchHelpFill('4k hdr')",
        "searchHelpFill('&quot;web dl&quot;')",
        "shp-row",
        "shp-tip",
        'ref="searchInput"',
    ):
        assert token in tpl, f"shared/tpl/topbar.html 缺少 {token}(搜索语法浮卡被改坏? 同步本守阵)"
    # 2. state 声明 + 方法单点(回填必须走 doSearch 即搜 + 焦点还输入框)
    state = open(os.path.join(STATIC_ROOT, "shared", "state.js"), encoding="utf-8").read()
    assert "searchHelpOpen: false" in state, "searchHelpOpen 必须在 state.js data 声明(漏声明 = 响应性缺失)"
    view = open(os.path.join(STATIC_ROOT, "shared", "view.js"), encoding="utf-8").read()
    for token in ("toggleSearchHelp()", "searchHelpFill(q)", "this.doSearch()", "this.$refs.searchInput"):
        assert token in view, f"shared/view.js 缺少 {token}"
    fill = re.search(r"searchHelpFill\(q\) \{(.*?)\n    \},", view, re.S)
    assert fill and "this.searchHelpOpen = false" in fill.group(1), "searchHelpFill 必须先收起浮卡"
    # 3. 收起路径: 点空白 + Esc(lifecycle 两条链), 以及 goView/openSettings 导航收起(不带残留跨页)
    lc = open(os.path.join(STATIC_ROOT, "shared", "lifecycle.js"), encoding="utf-8").read()
    assert lc.count("this.searchHelpOpen = false") >= 2, "浮卡必须挂 lifecycle 的点空白与 Esc 两条收起链"
    assert "searchHelpOpen) this.searchHelpOpen = false" in lc, "Esc 退栈必须含浮卡(pop 层)"
    goview = re.search(r"goView\(mode\) \{(.*?)\n    \},", view, re.S)
    assert goview and "this.searchHelpOpen = false" in goview.group(1), "goView 导航必须收起浮卡"
    ed = read_shared("config_editor.js")
    openst = re.search(r"async openSettings\(\) \{(.*?)\n    \},", ed, re.S)
    assert openst and "this.searchHelpOpen = false" in openst.group(1), "openSettings 导航必须收起浮卡"
    # 4. CSS 成对: 挂件类在共用层(console_hub.css, 三套 UI 同载), input 右内边距 52px 三皮肤各自留位
    shared_css = read_shared("console_hub.css")
    for cls in (".search-help", ".search-help.no-clear", ".search-help-pop", ".shp-row", ".shp-tip"):
        assert cls in shared_css, f"shared/console_hub.css 缺少 {cls} 定义(挂件类名错配 = 静默裸样式)"
    atlas_css = open(os.path.join(STATIC_ROOT, "atlas", "css", "components.css"), encoding="utf-8").read()
    assert re.search(r"\.search-help \{[^}]*border-radius: 50%", atlas_css), "星图 pill 差异丢失(「?」钮应圆)"
    for rel in ("prism/css/components.css", "atlas/css/components.css", "console/css/components.css"):
        css = open(os.path.join(STATIC_ROOT, rel), encoding="utf-8").read()
        assert "padding: 7px 52px 7px 33px" in css, f"{rel} input 右内边距未给浮卡按钮留位(32px 旧值 = 「?」压住文字)"
