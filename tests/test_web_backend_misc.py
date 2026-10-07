"""test_web_backend_misc 测试计划: WEB 后端杂项: config / token / sites / 分组视图 / 错误原因

## 测试计划(每个测试函数一条)
- test_config_schema_endpoint: 图形化配置元数据端点(分组/插件/热重载级别)
- test_config_tree_roundtrip: 配置树读取/保存写回文件并投递热重载命令
- test_config_tree_invalid_rejected: 非法配置树 -> 400 且不写回
- test_config_tree_requires_config_root: 缺少 config 根段 -> 400
- test_config_tree_restart_field_fallback: R 级字段(data_dir)提交后被回退为磁盘旧值
- test_config_tree_preserves_comments: round-trip 写盘保留已有键的注释
- test_web_token_not_printed_in_logs: 生成的访问密钥不进任何日志(WARNING 会被 notify 推送, 且 /api/log 可读回)
- test_web_token_generated_atomic_and_readable: 首次生成密钥落盘 web.token 且读回一致, 无临时文件残留(走 atomic_write, issue 26-09-21-1347)
- test_web_token_existing_file_reused_without_rewrite: 已有合法 token 时直接复用文件现值, 不触达写盘路径(不重写不漂移)
- test_web_token_write_interrupt_leaves_no_half_token: 写盘中断不留非空半截 token —— 经真实 atomic_write 跑"写一半抛错", 旧文件不被破坏、临时文件被清理, 下次调用重新生成(自愈)
- test_config_tree_masks_secrets: /api/config 掩码敏感字段, 且"读取→原样保存"不会把密码写成占位串
- test_sites_missing_scans_and_builds_defaults: GET /api/sites/missing 未配置域名生成默认条目(domains/tags/占位限速/hr 示例值与 --export-yaml 同源); 已配置域名双向包含不重复
- test_sites_missing_name_conflict_suffix: 站点名冲突(既有配置占用/批内同名) -> _N 后缀(与 CLI 导出同一套 gen_tracker_name)
- test_sites_missing_all_covered_returns_empty: 全部域名已被覆盖 -> sites 空数组
- test_sites_missing_requires_connected_client: qB 断连 -> 503(不得拿空扫描冒充"没有缺失站点")
- test_sites_missing_api_failure_maps_502: 扫描中途 qB 调用失败 -> 502 带原因(不裸 500)
- test_frontend_sites_import_wiring: 一键导入按钮接线守阵 —— 两套 UI 站点 pill 行都挂「⤓ 导入缺失站点」+ config_hub.js 的 hubImportSites/防重入标志
- test_frontend_tracker_search_wiring: 站点页搜索接线守阵(计划 26-09-27-1852) —— 模板三件套(输入绑定/清空钮/计数) + 归一化必须 \\p{L}\\p{N}(u 标志, ASCII \\W 折碎中文词) + 收层路径四条一律清词单点(点命中/Esc/点暗幕/点外即收; 方案C 聚焦层 2026-09-29 拍板) + 聚焦层开合/键盘导航/IME 守卫 + 悬停接管位移门限(治上下键选中项闪烁 2026-09-29) + 键盘活动项滚动跟随(26-09-29-2142) + pill 无键数徽标 + 行尾动作区分形 + hb-tr-* 类 CSS 成对定义
- test_frontend_dialog_combo_hover_takeover: 弹窗下拉悬停接管守阵(issue 26-09-29-2142, 站点搜索闪烁同族) —— 分类/标签/编辑分类下拉 @mousemove+3px 位移门限共享小工具(comboHoverIdx) + @mouseenter 直写零残留 + 门限坐标 state 声明 + 开层单点复位 + 三皮肤 data-hi 行 CSS 摘 :hover(高亮只走 .on 单路)
- test_frontend_search_help_wiring: 顶栏搜索语法浮卡接线守阵(计划 26-09-28-0201 方案A) —— 模板(「?」钮/浮卡/示例回填/简化占位符) + state 声明 + view.js 方法(回填即搜) + 点空白/Esc/导航三条收起路径 + 三皮肤 CSS 成对定义与 input 右内边距留位
- test_group_key_codec_roundtrip: 分组 key 编解码往返(含中文/多文件)
- test_build_group_view: 分组视图组装(组名/合计/成员站点/单种子大小与总大小/标签/分类/保存路径)
- test_build_group_view_cross_group_conflict_flag: 组视图跨组文件交叉标记(26-10-04-0107 S4/D4) —— 去重集合展平为组 key 集合后端查好, warned 注入组对两侧 true、组外组 false; warned 空全 false; 未归组单种子视图(singles)为成员级投影不携带组级标记
- test_build_group_view_member_num_seeds_fields: 组视图成员透出 num_seeds/num_leechs/num_complete/num_incomplete
- test_build_group_view_group_aggregates: 组视图组级聚合(辅种扩列 2026-09-28) —— 进度/可用性 max、eta 最小有效值(哨兵不参与)、剩余量 min、最近活动 max(-1 不参与)、已下载求和、做种时长平均、分享率=总上传÷单份大小; 全组无效值回 0/None
- test_member_view_extended_fields: 成员视图透出辅种扩列字段(eta/time_active/last_activity 分钟量化 + downloaded/amount_left/completion_on/seen_complete/availability/限速/tracker/infohash_v2)
- test_error_reason_from_tracker_msg: 错误种子的具体原因取 tracker 报错 msg(虚拟条目跳过)+ 视图透出 error_reason(取不到回退"错误"/非错误态为空)
- test_error_reason_missing_files_without_api: missingFiles 的原因由状态本身给出("文件丢失"), 不发 tracker 请求
- test_refresh_error_reasons_budget_and_ttl: 错误原因预取限流(单轮预算条数/TTL 内不重取/过期重取)
- test_refresh_error_reasons_clears_when_recovered: 状态恢复后清空原因缓存并置脏(不留旧原因)
- test_refresh_error_reasons_skips_when_disconnected: qB 断开时跳过(不发请求/不清空现值)
"""
import logging
import os
import re
import time
from types import SimpleNamespace

import pytest

from auto_qb.infra.utils import decode_group_key, encode_group_key

from webui_helpers import _make_web_manager, STATIC_ROOT, _UI_ALL, _ui_aggregate


def test_config_schema_endpoint(web_env):
    """图形化配置元数据端点: 分组/站点字段/规则字段/插件表/热重载级别齐全"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    data = client.get("/api/config/schema", headers=auth).json()
    # 2026-09-26: 日志/WebUI/通知 三个短段并入 basic(设置页不再单列三张卡)
    # 26-10-03: 流量图分组(plan 26-10-03-0946 §06)插在 speed 与 trackers 之间
    # 26-10-06 用户要求重排: 站点提到第二(紧跟常规), 限速 / HR 在线核实 后置到末尾
    assert [g["key"]
            for g in data["groups"]] == ["basic", "trackers", "maintenance", "traffic", "rules", "speed", "hr_check"]
    assert [f["key"] for f in data["groups"][0]["fields"]][-3:] == ["log", "web", "notify"]
    # 2026-09-28: 三段在「常规」页必须各自成块展示分类名(「常规/日志」而非并入「常规/常规」) ——
    # 成块的前提是不声明 open(open 段被 cfgFlatten 平铺成无标题同级字段, 正是本次回归的根因)
    for f in data["groups"][0]["fields"][-3:]:
        assert f["kind"] == "object" and not f.get("open"), f["key"]
    assert {p["name"] for p in data["plugins"]["condition"]} >= {"size", "tags", "state", "freespace"}
    assert {p["name"] for p in data["plugins"]["action"]} >= {"add_tags", "checking", "reannounce"}
    # 段认领由模块 sections() 派生(W4 级别表退役; 前端不消费, 留给排障对照)
    assert data["levels"]["claimed_sections"]["web"] == ["webui"]
    assert data["levels"]["claimed_sections"]["trackers"] == ["tracker"]
    assert data["levels"]["claimed_sections"]["rules_config"] == ["rules"]


def test_config_tree_roundtrip(web_env):
    """配置树读取与保存: 树为 YAML 同构(标量字符串), 写回文件 + 热重载命令入队"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    data = client.get("/api/config", headers=auth).json()
    tree = data["tree"]
    assert tree["config"]["qbittorrent"]["host"] == "h", "树应为 YAML 同构的字符串标量"

    tree["config"]["main_tick"] = "5s"
    resp = client.put("/api/config", headers=auth, json={"tree": tree})
    assert resp.status_code == 200, resp.text
    assert resp.json()["applied"] is True
    assert "main_tick" in resp.json()["changes"], "PUT 回执应报变更段路径(W4: 路径字符串)"
    with open(mgr.config_path, encoding="utf-8") as f:
        assert "5s" in f.read(), "新配置应写回 config 文件"
    cmd, payload = mgr.web.commands.get_nowait()
    assert cmd == "reload_config" and payload["config"].main_tick == 5.0


def test_config_tree_invalid_rejected(web_env):
    """非法配置树 -> 400, config 文件不被覆盖"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    tree = client.get("/api/config", headers=auth).json()["tree"]
    tree["config"]["main_tick"] = "abc"
    before = open(mgr.config_path, encoding="utf-8").read()
    resp = client.put("/api/config", headers=auth, json={"tree": tree})
    assert resp.status_code == 400
    assert "main_tick" in resp.json()["detail"]
    assert open(mgr.config_path, encoding="utf-8").read() == before
    assert mgr.web.commands.empty(), "校验失败不应投递热重载"


def test_config_tree_requires_config_root(web_env):
    """缺少 config 根段 -> 400(防止误删整段被当作"全默认"静默接受)"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    resp = client.put("/api/config", headers=auth, json={"tree": {"qbittorrent": {}}})
    assert resp.status_code == 400
    assert "config" in resp.json()["detail"]


def test_config_tree_restart_field_fallback(web_env):
    """R 级字段提交后回退为磁盘旧值(进程身份不可热切换), 并回报 restart_required"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    with open(mgr.config_path, "w", encoding="utf-8") as f:
        f.write("config:\n  schema_version: 4\n  data_dir: old-dir\n  qbittorrent:\n    host: h\n")

    tree = client.get("/api/config", headers=auth).json()["tree"]
    tree["config"]["data_dir"] = "new-dir"
    resp = client.put("/api/config", headers=auth, json={"tree": tree})
    assert resp.status_code == 200, resp.text
    # data_dir 变更会连带派生 state_file(<data_dir>/state.json), 两者同为 R 级
    assert "data_dir" in resp.json()["restart_required"]
    text = open(mgr.config_path, encoding="utf-8").read()
    assert "old-dir" in text, "R 级字段应保留旧值"
    assert "new-dir" not in text, "R 级字段的新值不得写入磁盘"


def test_config_tree_preserves_comments(web_env):
    """round-trip 写盘保留已有键注释(列表项注释为已记录的取舍)"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    with open(mgr.config_path, "w", encoding="utf-8") as f:
        f.write("config:\n  schema_version: 4\n  # 保留我\n  main_tick: 2s\n  qbittorrent:\n    host: h\n")

    tree = client.get("/api/config", headers=auth).json()["tree"]
    tree["config"]["main_tick"] = "3s"
    resp = client.put("/api/config", headers=auth, json={"tree": tree})
    assert resp.status_code == 200, resp.text
    text = open(mgr.config_path, encoding="utf-8").read()
    assert "# 保留我" in text, "已有键的注释应在 round-trip 写盘后保留"
    assert "3s" in text


def test_web_token_not_printed_in_logs(tmp_path, caplog):
    """生成的访问密钥不得出现在任何日志里

    原实现用 `logger.warning(f"WEB UI 访问密钥: {token}")`: notify 处理器的级别取
    config.min_level(早期默认 WARNING, 26-09-27 等级整改后默认 ERROR) ⇒ 密钥被推到系统
    通知; 落日志文件后已登录者可经 /api/log 读回。拿到密钥即等于拿到改配置/删种子的能力。改为只提示文件路径。
    """
    from auto_qb.webui import ensure_web_token

    mgr = _make_web_manager(
        tmp_path,
        "config:\n  qbittorrent:\n    host: h\n    port: 1\n    username: u\n    password: p\n  schema_version: 4\n"
    )
    with caplog.at_level(logging.DEBUG, logger="auto_qb.web"):
        token = ensure_web_token(mgr)
    assert token, "前置: 应生成随机密钥"
    assert any(r.name == "auto_qb.web" for r in caplog.records), "前置: 应有生成提示日志"
    for r in caplog.records:
        assert token not in r.getMessage(), f"密钥不得出现在日志: {r.getMessage()}"
        assert token[:8] not in r.getMessage(), f"密钥前缀也不得出现: {r.getMessage()}"


_WEB_MGR_CFG = "config:\n  qbittorrent:\n    host: h\n    port: 1\n    username: u\n    password: p\n  schema_version: 4\n"


def test_web_token_generated_atomic_and_readable(tmp_path):
    """首次生成: 密钥落盘 web.token 且读回一致, 同目录无临时文件残留(issue 26-09-21-1347)

    ensure_web_token 走 utils.atomic_write(mkstemp 0600 + os.replace): 写盘成功后目标文件
    即完整可读 —— 半截状态只可能存在于临时文件, replace 前对读取侧不可见。
    """
    from auto_qb.webui import ensure_web_token

    mgr = _make_web_manager(tmp_path, _WEB_MGR_CFG)
    token = ensure_web_token(mgr)
    assert re.fullmatch(r"[0-9a-f]{64}", token), "token_hex(32) 应为 64 位小写 hex"
    token_file = tmp_path / "web.token"
    assert token_file.read_text(encoding="ascii") == token, "落盘内容必须与返回值逐字节一致"
    assert not list(tmp_path.glob("web.token.*")), "不得残留临时文件"


def test_web_token_existing_file_reused_without_rewrite(tmp_path, monkeypatch):
    """已有合法 token 时不重写: 直接返回文件现值, 写盘路径一次都不触发(不重写不漂移)"""
    from auto_qb.webui import ensure_web_token
    from auto_qb.webui.server import common

    existing = "ab" * 32
    (tmp_path / "web.token").write_text(existing, encoding="ascii")
    mgr = _make_web_manager(tmp_path, _WEB_MGR_CFG)

    def _must_not_write(*_a, **_kw):
        raise AssertionError("已有合法 token 时不得触达写盘路径")

    monkeypatch.setattr(common, "atomic_write", _must_not_write)
    assert ensure_web_token(mgr) == existing, "应复用文件现值而非重新生成"
    assert (tmp_path / "web.token").read_text(encoding="ascii") == existing


def test_web_token_write_interrupt_leaves_no_half_token(tmp_path, monkeypatch):
    """写盘中断不留非空半截 token(issue 26-09-21-1347): 旧文件不被破坏, 下次调用重新生成(自愈)

    经真实 atomic_write 跑"写一半抛错": 回调写入半截后抛 RuntimeError, 由 atomic_write 负责
    清理临时文件并重抛 —— 目标路径保持旧内容。若实现退回 O_TRUNC 直写, 同一时刻半截内容已落
    目标文件, 本条在 raises 处即红。
    """
    from auto_qb.webui import ensure_web_token
    from auto_qb.webui.server import common

    mgr = _make_web_manager(tmp_path, _WEB_MGR_CFG)
    token_file = tmp_path / "web.token"
    token_file.write_text("", encoding="ascii")  # 空文件: 读取侧判空后走重新生成分支

    real_atomic_write = common.atomic_write

    def _crash_mid(path, write_fn, **kw):
        def _half(_f):
            _f.write("deadbeef")  # 半截密钥, 模拟写盘途中被杀
            raise RuntimeError("simulated kill mid-write")

        return real_atomic_write(path, _half, **kw)

    monkeypatch.setattr(common, "atomic_write", _crash_mid)
    with pytest.raises(RuntimeError):
        ensure_web_token(mgr)
    assert token_file.read_text(encoding="ascii") == "", "中断后不得留下非空半截 token"
    assert not list(tmp_path.glob("web.token.*")), "中断的临时文件必须被清理"

    monkeypatch.undo()
    token = ensure_web_token(mgr)  # 自愈: 下次启动重新生成并完整落盘
    assert token_file.read_text(encoding="ascii") == token


def test_config_tree_masks_secrets(web_env):
    """/api/config 掩码敏感字段, 且"读取后原样保存"不会把密码写成占位串

    掩码只影响展示: PUT 侧用磁盘旧值还原哨兵, 因此前端不改密码地保存一遍仍是真密码 ——
    只掩码不还原的话, 一次保存就会毁掉生产配置。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    data = client.get("/api/config", headers=auth).json()
    assert data["masked"] is True
    assert data["tree"]["config"]["qbittorrent"]["password"] == data["mask_sentinel"]
    assert data["tree"]["config"]["qbittorrent"]["host"] == "h", "非敏感字段不掩码"

    resp = client.put("/api/config", headers=auth, json={"tree": data["tree"]})
    assert resp.status_code == 200, resp.text
    text = open(mgr.config_path, encoding="utf-8").read()
    assert "password: p" in text, f"原样保存不得把密码写成占位串: {text}"
    assert data["mask_sentinel"] not in text


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


def test_frontend_sites_import_wiring():
    """一键导入缺失站点的前端接线守阵(2026-09-26)

    两套 UI 的站点 pill 行都必须挂「⤓ 导入缺失站点」按钮并调用 config_hub.js 的
    hubImportSites —— 漏一套那套 UI 就没有入口; 防重入标志 hub.importing 必须存在。
    """
    hub_js = open(os.path.join(STATIC_ROOT, "shared", "config_hub.js"), encoding="utf-8").read()
    assert "async hubImportSites()" in hub_js, "config_hub.js 缺 hubImportSites 方法"
    assert "this.hub.importing" in hub_js, "缺防重入标志 hub.importing"
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
    hub = open(os.path.join(STATIC_ROOT, "shared", "config_hub.js"), encoding="utf-8").read()
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
    ed = open(os.path.join(STATIC_ROOT, "shared", "config_editor.js"), encoding="utf-8").read()
    assert 'trackerQuery: ""' in ed, "cfg.trackerQuery 必须在 config_editor.js state 声明(漏声明 = 响应性缺失)"
    # 6. CSS 成对: 模板用到的 hb-tr-* 类都要有规则
    css = open(os.path.join(STATIC_ROOT, "shared", "console_hub.css"), encoding="utf-8").read()
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
    for token in (
        "@mousemove=\"comboHoverIdx('cat', i, $event)\"",  # 悬停接管走位移门限(治上下键选中项闪烁)
        "@mousemove=\"comboHoverIdx('tag', i, $event)\"",
    ):
        assert token in mgr, f"dialogs-mgr.html 缺少 {token}(分类/标签下拉悬停接线被改坏? 同步本守阵)"
    assert "@mouseenter=\"addCatHi" not in mgr and "@mouseenter=\"addTagHi" not in mgr, \
        "分类/标签下拉行不得挂 @mouseenter(静止光标旧高亮与键盘活动项同源打架 = 上下键选中项闪烁/Enter 选错), 悬停接管走 comboHoverIdx"
    pop = open(os.path.join(STATIC_ROOT, "shared", "tpl", "popovers.html"), encoding="utf-8").read()
    assert "@mousemove=\"comboHoverIdx('meta', i, $event)\"" in pop, "popovers.html 缺少 meta 分类下拉悬停接线(同步本守阵)"
    assert "@mouseenter=\"metaCatHi" not in pop, "编辑弹窗分类下拉行不得挂 @mouseenter(同族打架), 悬停接管走 comboHoverIdx"
    # 1. 门限坐标三字段声明(漏声明 = 响应性缺失) + 共享小工具单点实现(别三处各抄一份)
    st = open(os.path.join(STATIC_ROOT, "shared", "state.js"), encoding="utf-8").read()
    for token in ("addCatMouseAt: null", "addTagMouseAt: null", "metaCatMouseAt: null"):
        assert token in st, f"state.js 缺少 {token}(门限坐标未声明 = 响应性缺失)"
    at = open(os.path.join(STATIC_ROOT, "shared", "add_torrent.js"), encoding="utf-8").read()
    assert "comboHoverIdx(kind, i, ev)" in at, "缺 comboHoverIdx 共享小工具(三处下拉共用, 别各抄一份)"
    fn = re.search(r"comboHoverIdx\(kind, i, ev\) \{(.*?)\n    \},", at, re.S)
    assert fn and "dx * dx + dy * dy < 9" in fn.group(1), \
        "悬停接管必须带 3px 位移门限(合成事件位移恒 0 被挡, 真实移动才接管)"
    # 3. 开层单点复位门限坐标(下次打开首个动作不被旧坐标误挡)
    for fnname, field in (("openAddCatMenu", "addCatMouseAt"), ("openAddTagMenu", "addTagMouseAt")):
        body = re.search(rf"{fnname}\(\) \{{(.*?)\n    \}},", at, re.S)
        assert body and f"{field} = null" in body.group(1), \
            f"{fnname} 必须复位 {field}(开层复位门限坐标)"
    dlg = open(os.path.join(STATIC_ROOT, "shared", "dialogs.js"), encoding="utf-8").read()
    body = re.search(r"openMetaCatMenu\(\) \{(.*?)\n    \},", dlg, re.S)
    assert body and "metaCatMouseAt = null" in body.group(1), \
        "openMetaCatMenu 必须复位 metaCatMouseAt(开层复位门限坐标)"
    # 2. CSS 单路高亮: 三皮肤 data-hi 行摘 :hover(.on 活动项是唯一高亮通道)
    for rel in (
        os.path.join("atlas", "css",
                     "dialogs.css"), os.path.join("console", "css",
                                                  "dialogs.css"), os.path.join("prism", "css", "components.css")
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
    ed = open(os.path.join(STATIC_ROOT, "shared", "config_editor.js"), encoding="utf-8").read()
    openst = re.search(r"async openSettings\(\) \{(.*?)\n    \},", ed, re.S)
    assert openst and "this.searchHelpOpen = false" in openst.group(1), "openSettings 导航必须收起浮卡"
    # 4. CSS 成对: 挂件类在共用层(console_hub.css, 三套 UI 同载), input 右内边距 52px 三皮肤各自留位
    shared_css = open(os.path.join(STATIC_ROOT, "shared", "console_hub.css"), encoding="utf-8").read()
    for cls in (".search-help", ".search-help.no-clear", ".search-help-pop", ".shp-row", ".shp-tip"):
        assert cls in shared_css, f"shared/console_hub.css 缺少 {cls} 定义(挂件类名错配 = 静默裸样式)"
    atlas_css = open(os.path.join(STATIC_ROOT, "atlas", "css", "components.css"), encoding="utf-8").read()
    assert re.search(r"\.search-help \{[^}]*border-radius: 50%", atlas_css), "星图 pill 差异丢失(「?」钮应圆)"
    for rel in ("prism/css/components.css", "atlas/css/components.css", "console/css/components.css"):
        css = open(os.path.join(STATIC_ROOT, rel), encoding="utf-8").read()
        assert "padding: 7px 52px 7px 33px" in css, f"{rel} input 右内边距未给浮卡按钮留位(32px 旧值 = 「?」压住文字)"


def test_group_key_codec_roundtrip():
    """分组 key 编解码回原值(base64url(JSON))"""
    key = ("R:/下載/目錄", ("a.mkv", "b.mkv"))
    assert decode_group_key(encode_group_key(key)) == key


def test_build_group_view(tmp_path):
    """分组视图快照组装: 组级聚合求和 + 成员明细 + 编码 key(回归真机 utils.encode_group_key 缺失)"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.config.grouping.enabled = True
    mgr.client = FakeClient()
    t1 = FakeTorrent(
        hash="HA",
        name="Show",
        state="stalledUP",
        upspeed=1024,
        uploaded=2048,
        size=512**2,
        progress=1.0,
        seeding_time=3641,  # 非整分钟: 视图输出应按分钟向下取整
        save_path=r"R:/s",
        tags="b, a",  # 逗号分隔字符串 -> 视图输出排序后的标签列表
        category="anime",
    )
    t2 = FakeTorrent(
        hash="HB",
        name="Show",
        state="pausedUP",
        upspeed=1024,
        uploaded=2048,
        size=512**2,
        progress=1.0,
        seeding_time=3600,
        save_path=r"R:/s",
        tags="b, a",
        category="anime",
    )
    from helpers import seed_store

    seed_store(mgr, [t1, t2])
    key = ("R:/s", ("a.mkv", "b.mkv"))
    mgr.store.groups[key] = ["HA", "HB"]
    mgr.store.member_to_key["HA"] = key
    mgr.store.member_to_key["HB"] = key

    view = mgr._build_group_view()
    assert len(view) == 1
    g = view[0]
    assert g["key"] == encode_group_key(key)
    assert g["name"] == "Show" and g["count"] == 2
    assert g["upspeed"] == 2048 and g["uploaded"] == 4096
    # size = 单种子大小(代表成员), total_size = 全组求和(两者相等时前端不提示大小不一致)
    assert g["size"] == 512**2 and g["total_size"] == 2 * 512**2
    assert [m["site"] for m in g["members"]] == ["Unknown", "Unknown"]
    assert g["members"][0]["kind"] == "seeding"
    # 成员视图透出 save_path/tags/category 供前端算组级共同值(后端不做集合运算)
    assert [m["save_path"] for m in g["members"]] == [r"R:/s", r"R:/s"]
    assert [m["tags"] for m in g["members"]] == [["a", "b"], ["a", "b"]]
    assert [m["category"] for m in g["members"]] == ["anime", "anime"]
    # seeding_time 展示值按分钟取整(与 store 重建判定同一步长, 防视图内容与脏标记脱钩)
    assert [m["seeding_time"] for m in g["members"]] == [3600, 3600]


def test_build_group_view_cross_group_conflict_flag(tmp_path):
    """组视图透出跨组文件交叉标记(plan 26-10-04-0107 S4/D4) —— 后端查去重集合, 前端只渲染

    warned 注入组对 -> 组对两侧组字段 true、组外组 false; warned 空 -> 全 false;
    未归组种子不进组视图, singles 单种子视图是成员级投影, 不携带组级标记(无污染;
    前端 filters.js 对搜索视图的虚拟单种子组恒补 cross_group_conflict: false, 单种子无组 key)。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.config.grouping.enabled = True
    mgr.client = FakeClient()
    t1 = FakeTorrent(hash="HA", name="ShowA", state="stalledUP", progress=1.0, size=512**2, save_path=r"R:/a")
    t2 = FakeTorrent(hash="HB", name="ShowB", state="downloading", progress=0.5, size=512**2, save_path=r"R:/b")
    t3 = FakeTorrent(hash="HC", name="ShowC", state="stalledUP", progress=1.0, size=512**2, save_path=r"R:/c")
    t4 = FakeTorrent(hash="HD", name="Lone", state="stalledUP", progress=1.0, size=512**2, save_path=r"R:/d")
    seed_store(mgr, [t1, t2, t3, t4])
    key_a = (r"R:/a", ("a.mkv", ))
    key_b = (r"R:/b", ("b.mkv", ))
    key_c = (r"R:/c", ("c.mkv", ))
    mgr.store.groups[key_a] = ["HA"]
    mgr.store.groups[key_b] = ["HB"]
    mgr.store.groups[key_c] = ["HC"]
    for h, k in (("HA", key_a), ("HB", key_b), ("HC", key_c)):
        mgr.store.member_to_key[h] = k

    # warned 空(开关关/无交叉常态) -> 全 false
    view = {g["name"]: g for g in mgr._build_group_view()}
    assert set(view) == {"ShowA", "ShowB", "ShowC"}
    assert not any(g["cross_group_conflict"] for g in view.values()), "warned 空时不得有组被标记"

    # warned 注入组对 (A, B) -> 两侧组 true, 组外 C false
    # (直写 store 去重集合的白盒姿势, 对齐本文件 seed_store + 手填 groups 的既有夹具)
    mgr.store.cross_group_conflict_warned.add((key_a, key_b))
    view = {g["name"]: g for g in mgr._build_group_view()}
    assert view["ShowA"]["cross_group_conflict"] is True
    assert view["ShowB"]["cross_group_conflict"] is True
    assert view["ShowC"]["cross_group_conflict"] is False

    # 未归组种子(Lone)不在组视图里; singles 是成员级投影, 不携带组级标记(无字段污染)
    singles = mgr._build_singles_view()
    assert [m["name"] for m in singles] == ["Lone"]
    assert all("cross_group_conflict" not in m for m in singles)


def test_build_group_view_member_num_seeds_fields(tmp_path):
    """组视图成员透出 num_seeds/num_leechs/num_complete/num_incomplete(TorrentRecord 快照直取)

    前端成员列/种子页展示连接数与可用性的数据源: _member_view 是组视图 members 与
    singles 未归组种子的共同投影, 字段在成员层透出后两处同形。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = FakeClient()
    t1 = FakeTorrent(
        hash="HA",
        name="Show",
        save_path=r"R:/s",
        num_seeds=12,
        num_leechs=3,
        num_complete=45,
        num_incomplete=6,
    )
    t2 = FakeTorrent(
        hash="HB",
        name="Show",
        save_path=r"R:/s",
        num_seeds=34,
        num_leechs=5,
        num_complete=67,
        num_incomplete=8,
    )
    seed_store(mgr, [t1, t2])
    key = ("R:/s", ("a.mkv", "b.mkv"))
    mgr.store.groups[key] = ["HA", "HB"]
    mgr.store.member_to_key["HA"] = key
    mgr.store.member_to_key["HB"] = key

    members = mgr._build_group_view()[0]["members"]
    for m in members:
        for f in ("num_seeds", "num_leechs", "num_complete", "num_incomplete"):
            assert f in m, f"组视图成员缺少字段 {f}: {sorted(m)}"
    by_hash = {m["hash"]: m for m in members}
    assert by_hash["HA"]["num_seeds"] == 12
    assert by_hash["HA"]["num_leechs"] == 3
    assert by_hash["HA"]["num_complete"] == 45
    assert by_hash["HA"]["num_incomplete"] == 6
    assert by_hash["HB"]["num_seeds"] == 34
    assert by_hash["HB"]["num_leechs"] == 5
    assert by_hash["HB"]["num_complete"] == 67
    assert by_hash["HB"]["num_incomplete"] == 8


def test_build_group_view_group_aggregates(tmp_path):
    """组视图组级聚合(辅种扩列 2026-09-28): "单份文件"语义下的口径单点

    组内成员指向同一份文件(组 key 首元即规范化 save_path), 磁盘只占一份 —— 字节量类取
    "单份"视角, 只有逐成员真实发生的网络流量才可求和:
    - progress/availability 取 max(最完整副本 / 最好的 swarm)
    - eta 取最小有效值(下载冲突检查保证同组至多一个在下载; 哨兵 8640000/非正不参与)
    - amount_left 取 min(补齐一份即可 —— 最完整成员还差的字节, 其余成员 recheck 即齐)
    - last_activity 取 max(-1/0 = 从未 哨兵不参与, 全组从未回 0)
    - downloaded 求和(多站切换下载的真实网络流量, 逐成员可加)
    - seeding_time 取平均(成员值已量化到分钟, 平均后再取整)
    - ratio = 总上传 ÷ 单份大小(分母不能是 total_size, N 份会稀释 N 倍)
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.config.grouping.enabled = True
    mgr.client = FakeClient()
    size = 10000
    t1 = FakeTorrent(
        hash="HA",
        name="Show",
        save_path=r"R:/s",
        size=size,
        progress=0.5,
        eta=7261,  # 成员视图量化到分钟 -> 7260
        downloaded=100,
        amount_left=500,
        availability=1.5,
        last_activity=1700000100,
        seeding_time=3641,  # -> 3600(分钟量化)
        uploaded=1024,
        state="stalledUP",
    )
    t2 = FakeTorrent(
        hash="HB",
        name="Show",
        save_path=r"R:/s",
        size=size,
        progress=1.0,
        eta=8640000,  # 哨兵(无 ETA): 不参与 eta 聚合
        downloaded=200,
        amount_left=300,
        availability=-1.0,  # qB 未知: 不参与 availability 聚合
        last_activity=-1,  # 从未: 不参与 last_activity 聚合
        seeding_time=7200,
        uploaded=2048,
        state="pausedUP",
    )
    # 全组无效值: eta 全哨兵/非正 -> 0, last_activity 全从未 -> 0, availability 全未知 -> None
    t3 = FakeTorrent(
        hash="HC", name="Alone", save_path=r"R:/x", eta=8640000, last_activity=-1, availability=-1.0, state="pausedUP"
    )
    t4 = FakeTorrent(
        hash="HD", name="Alone", save_path=r"R:/x", eta=0, last_activity=0, availability=-1.0, state="pausedUP"
    )
    seed_store(mgr, [t1, t2, t3, t4])
    key = ("R:/s", ("a.mkv", "b.mkv"))
    mgr.store.groups[key] = ["HA", "HB"]
    mgr.store.member_to_key["HA"] = key
    mgr.store.member_to_key["HB"] = key
    key2 = ("R:/x", ("c.mkv", ))
    mgr.store.groups[key2] = ["HC", "HD"]
    mgr.store.member_to_key["HC"] = key2
    mgr.store.member_to_key["HD"] = key2

    g = mgr._build_group_view()[0]
    assert g["progress"] == 1.0
    assert g["eta"] == 7260, "组 eta = 最小有效值(哨兵不参与)"
    assert g["downloaded"] == 300
    assert g["amount_left"] == 300
    assert g["availability"] == 1.5
    assert g["last_activity"] == 1700000100
    assert g["seeding_time"] == 5400, "组做种时长 = 成员平均值(3600 与 7200 的均值)"
    assert g["ratio"] == round(3072 / size, 3), "组分享率分母 = 单份大小而非 total_size"

    g2 = {gg["name"]: gg for gg in mgr._build_group_view()}["Alone"]
    assert g2["eta"] == 0 and g2["last_activity"] == 0 and g2["availability"] is None


def test_member_view_extended_fields(tmp_path):
    """成员视图透出辅种扩列字段(2026-09-28): 明细表新列与组级聚合的共同数据源

    _member_view 是组视图 members 与 singles 未归组种子的共同投影 —— 明细表新增的
    剩余时间/已下载/限速/Tracker/Hash v2 等列从这里取数。秒级递增字段(eta/time_active/
    last_activity)必须经 view_field_value 分钟量化(与 store 重建判定同一步长, 否则做种中的
    种子每轮置脏、惰性重建失效); 哨兵原样带过(负数不量化, 见 view_field_value)。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = FakeClient()
    t = FakeTorrent(
        hash="HA",
        name="Show",
        save_path=r"R:/s",
        eta=7261,
        time_active=3661,
        last_activity=1700000123,
        completion_on=1700000500,
        seen_complete=1700000600,
        availability=1.2345,
        dl_limit=1024,
        up_limit=2048,
        tracker="https://tracker.example/announce",
        infohash_v2="v2hash-abcd1234",
        downloaded=123456,
        amount_left=654321,
    )
    seed_store(mgr, [t])
    v = mgr._member_view(mgr.store.by_hash["HA"])
    assert v["eta"] == 7260 and v["time_active"] == 3660 and v["last_activity"] == 1700000100
    assert v["downloaded"] == 123456 and v["amount_left"] == 654321
    assert v["completion_on"] == 1700000500 and v["seen_complete"] == 1700000600
    assert v["availability"] == 1.23
    assert v["dl_limit"] == 1024 and v["up_limit"] == 2048
    assert v["tracker"] == "https://tracker.example/announce"
    assert v["infohash_v2"] == "v2hash-abcd1234"


def _tracker_calls(client):
    """给 FakeClient 的 torrents_trackers 挂调用计数器(返回被查询过的 hash 列表)

    "免 API"/"TTL 内不重取"/"单轮预算限流"三类断言都需要该计数, 而公共替身无此计数
    (既有用例不依赖), 故在测试侧按需包装, 不改动 helpers.FakeClient 的既有语义。
    """
    seen = []
    orig = client.torrents_trackers
    client.torrents_trackers = lambda h: (seen.append(h), orig(h))[1]
    return seen


def test_error_reason_from_tracker_msg(tmp_path):
    """错误状态的具体原因: 取 tracker 报错 msg(虚拟条目跳过), 并透出到成员/种子视图

    qB torrents/info **不含**错误文本(Web API 无该字段), 原因只能从 torrents/trackers 的
    msg 取; 预取结果写在记录上, 视图组装只读缓存 —— 视图可能每 tick 重建, 不能在里面发 API。
    取不到报错 msg 的错误种子(磁盘/IO 类)回退状态文本, 不留空串(否则前端显示空白状态)。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    client = FakeClient()
    mgr.client = client
    client.trackers_map["HA"] = [
        {
            "url": "** [DHT] **",
            "status": 4,
            "msg": "virtual-entry-msg"
        },  # 虚拟条目: 不得采信
        {
            "url": "https://tracker.hhanclub.net/announce.php",
            "status": 2,
            "msg": "Working"
        },
        {
            "url": "https://tracker.other.net/announce.php",
            "status": 4,
            "msg": "torrent not registered"
        },
    ]
    client.trackers_map["HB"] = [{"url": "https://tracker.hhanclub.net/announce.php", "status": 2, "msg": "Working"}]
    err = FakeTorrent(hash="HA", name="Show", state="error")
    no_msg = FakeTorrent(hash="HB", name="Show", state="error")
    seed_store(mgr, [err, no_msg])

    mgr.web.group_view_dirty = False
    mgr.refresh_error_reasons()

    assert err.tracker_error_msg == "torrent not registered", "取第一条非空错误 msg(虚拟条目跳过)"
    assert mgr.web.group_view_dirty is True, "原因变化须显式置脏(非快照字段, store.view_changed 覆盖不到)"
    assert mgr._member_view(err)["error_reason"] == "torrent not registered"
    assert mgr._seed_view(err)["error_reason"] == "torrent not registered"
    assert no_msg.tracker_error_msg == "" and mgr._member_view(no_msg)["error_reason"] == "错误"
    assert mgr._member_view(FakeTorrent(hash="HC", state="stalledUP"))["error_reason"] == "", "非错误状态不带原因"


def test_error_reason_missing_files_without_api(tmp_path):
    """missingFiles 的原因由状态本身给出("文件丢失"), 不需要任何 tracker 请求"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    client = FakeClient()
    mgr.client = client
    seen = _tracker_calls(client)
    t = FakeTorrent(hash="HA", name="Show", state="missingFiles")
    seed_store(mgr, [t])

    mgr.refresh_error_reasons()

    assert mgr._member_view(t)["error_reason"] == "文件丢失"
    assert seen == [], "missingFiles 的原因不依赖 API"


def test_refresh_error_reasons_budget_and_ttl(tmp_path, monkeypatch):
    """预取限流: 单轮最多预算条, TTL 内不重取, 过期后重取

    错误种子成片时(整组文件丢失)不能一轮打满 tracker 请求 —— 与搜索索引同一限流哲学。
    """
    from auto_qb.webui import views as web_view
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    monkeypatch.setattr(web_view, "ERROR_REASON_BUDGET", 1)
    mgr = make_manager(str(tmp_path / "state.json"))
    client = FakeClient()
    mgr.client = client
    seen = _tracker_calls(client)
    seed_store(mgr, [FakeTorrent(hash="HA", name="A", state="error"), FakeTorrent(hash="HB", name="B", state="error")])

    mgr.refresh_error_reasons()
    assert seen == ["HA"], "单轮只拉预算条数"
    mgr.refresh_error_reasons()
    assert seen == ["HA", "HB"], "下一轮续取剩余种子"
    mgr.refresh_error_reasons()
    assert seen == ["HA", "HB"], "TTL 内不重取"

    monkeypatch.setattr(web_view, "ERROR_REASON_BUDGET", 5)
    monkeypatch.setattr(web_view, "ERROR_REASON_TTL", 0.0)
    mgr.refresh_error_reasons()
    assert seen == ["HA", "HB", "HA", "HB"], "TTL 过期后重取(tracker msg 随站点状态变化)"


def test_refresh_error_reasons_clears_when_recovered(tmp_path):
    """状态恢复(离开错误态)后清空原因缓存 —— 否则恢复做种仍挂着旧原因"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = FakeClient()
    t = FakeTorrent(hash="HA", name="A", state="error", tracker_error_msg="unregistered", tracker_error_ts=time.time())
    seed_store(mgr, [t])

    mgr.web.group_view_dirty = False
    mgr.refresh_error_reasons()
    assert t.tracker_error_msg == "unregistered", "错误态且未过期: 原样保留"
    assert mgr.web.group_view_dirty is False, "无变化不置脏"

    t.state = "stalledUP"
    mgr.refresh_error_reasons()
    assert t.tracker_error_msg == "" and t.tracker_error_ts == 0.0
    assert mgr.web.group_view_dirty is True, "清空也是视图变化"


def test_refresh_error_reasons_skips_when_disconnected(tmp_path):
    """qB 断开(client None)时跳过: 不发请求、不清空已有原因(连接恢复后自然刷新)"""
    from helpers import FakeTorrent, make_manager, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = None
    t = FakeTorrent(hash="HA", name="A", state="error", tracker_error_msg="unregistered")
    seed_store(mgr, [t])

    mgr.refresh_error_reasons()  # 不抛异常

    assert t.tracker_error_msg == "unregistered" and t.tracker_error_ts == 0.0
