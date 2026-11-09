"""test_extension_proxy_page_fetch 测试计划: 浏览器扩展(HR 取数代理)的静态与行为守阵

扩展是**要用户装进浏览器**的交付物: pytest 跑不到它的运行期, 但四类故障是**静态/半静态可查**的,
且都属于"pytest 全绿、用户装上就报错"的形态 —— 2026-09-24 实测两条:
1. 裸域名直喂 `chrome.permissions.request` ⇒ `Invalid value for origin pattern pt.btschool.club:
   Missing scheme separator.`(**未捕获的 Promise 拒绝**);
2. 端点没起 / 地址写法不对时用户只看到一句 `TypeError: Failed to fetch`(浏览器对网络层失败只给这句)。
故这里钉死: manifest 的作用域、JS 语法、**与后端的协议常量**、以及"输入先归一化再交给浏览器 API"。

## 测试计划(每个测试函数一条)
- test_background_events_ring_dual_write: 真跑 background.js —— 六类场景双写结构化事件环, tag/host/kind/ms/bytes 契约钉死
- test_page_fetch_is_headless_when_html_looks_fine: 直取能拿到页面时**不得开任何窗口/标签**(用户实报两轮)
- test_page_fetch_renders_offscreen_only_when_needed: 只在内容不像页面时才升级, 且用**离屏 popup 窗口**
- test_page_fetch_renders_when_direct_fetch_hits_login_page: 直取拿到登录页也要升级(SameSite 安全网)
- test_page_fetch_hands_focus_back_when_window_steals_it: 万一窗口抢了焦点, 取完还回原窗口
- test_extension_quota_caps_and_refuses: 真跑 background.js —— 同站访问/下载各自计数, 超限即**拒发**
  (不发请求 + 回传 kind=ext-quota + retry_after); 窗口键变了计数归零
- test_extension_torrent_login_page_detected: 真跑 background.js —— download.php 返回 HTML(登录页)时
  回传 kind=login-page, 让后端按「HR 登录失效」处置而不烧 .torrent 重试额度(2026-09-25 实报)
- test_logger_levels_ring_truncation_and_clear: 真跑 background.js —— 运行日志分级(低于记录级别直接丢)、
  环形上限(丢最旧)、超长字段截断(页面 HTML 整份进日志会撑爆 storage 配额)、清空后落盘为空数组
- test_connection_failure_logs_head_tail_only: 真跑 background.js —— 连不上时只打「头尾」: 首报全量
  排查清单 ERROR; 连败期降 debug(默认记录级别下不落盘), 每 30 轮重提一次全量; 恢复补一句 INFO 并清
  连败计数(计数落 storage, SW 回收也不丢); 状态栏同文复读降 debug(2026-09-28 用户实报每轮复读)
- test_background_bundle_is_process_private: 回归 xdist 共享实例根 —— vm 沙箱聚合脚本落点须掺 pid 且非空
- test_log_ui_wiring_and_escape: 选项页日志面 —— 清空走 clear-logs 协议(两边一致, 直接改 storage
  会被后台内存缓冲盖回)、渲染过 esc 转义(明细含站点 URL/页面片段)、限渲染条数、
  storage.onChanged 自动刷新、日志容器在脚本之前

### 去端口+跨机轮(计划 26-10-14-1241 S4): 判据放开与自动发现
- NORMALIZE_CASES 更新: 私网三段逐段放行 / 公网域名拒绝 / https 保留不折 / 新增 disc 类(发现地址缺端口补 18788)
  —— 旧断言「非回环即抛」「https 折 http」是被本计划翻转的旧语义, 随计划更新而非守阵松动
- test_discovery_helpers_behave: 真跑 discovery.js —— 候选推导与后端 discovery_candidates 同源(65535 截断)/
  合并语义(**手动优先**: 同端点手动整条胜 + 手动置顶且顺序稳定; **发现集整批替换**: 旧发现条目被剪除;
  **空集不替换**(C1); 缺 token 半条不收)/ pairingNeeded 真值表 / 发现响应形态过滤(异形应答 = 非本服务)
- test_background_discovery_flow: 真跑 background.js 发现流程 —— 三候选并行探测(命中次位, V11)/ 配对码随
  X-Hr-Pairing 上来 / 合并落盘 + 清 pairingNeeded / 401 pairing_required 置标记(选项页提示输入配对码)/
  全未命中明确报告(退手动, 不静默)
### 连接自愈轮(计划 26-10-15-2357 S1/S2): 合并语义翻转 + 自愈触发 + 徽标 + 台账
- 合并语义翻转(Q1/Q2/Q8/C1): 旧断言「同端点被发现覆盖 / 只增不减」是被本计划翻转的旧语义, 随计划更新
  而非守阵松动 —— 手动条目 = 高优先级(整条胜 + 置顶 + 永不自动删), 发现集 = 租约(整批替换, 空集除外)。
- test_discovery_period_is_two_minutes: 真跑 background.js —— 周期常量 = 2 分钟(Q3), 60s 节流不变
- test_discovery_triggers_on_any_failure: 真跑 background.js —— **任一实例失败**即触发发现(1 死 1 活也触发)/
  60s 内不重复 / 401 不算失败(端点有应答) / 同钟位正对照 / 实例清单为空也按周期发现(R1)
- test_discovery_snapshot_is_structured: 真跑 background.js —— lastDiscovery 结构化快照(ok/port/merged/reason/
  answered + 逐候选 url/note), 选项页顶部总览与逐候选结果的渲染源
- test_instance_health_ledger_records_per_instance: 真跑 background.js —— 健康台账按端点落, 连续失败累加、
  成功清零、清单外端点剪除(C3 的「疑似失效」阈值靠它, R3 不许每请求写 storage)
- test_badge_reflects_connection_state: 真跑 background.js —— 徽标五态(未配置/正常/重连中/发现失败/
  站点未授权, C4 边界)+ 禁用清空 + 点图标开选项页
- test_badge_text_is_ascii_only: 徽标文案禁非 ASCII 图形符(code-style: 代码禁图形符号)
- 降噪场景(_NODE_RUN_NOISE)显式 discoveryAddress 置空 —— 那条守阵钉「连接失败降噪」, 不混发现流日志
### 连接自愈轮 · S6 守阵补强(计划 26-10-15-2357 S6)
- test_merge_instances_manual_priority: 手动条目同端点**整条胜**(含 token 保留)+ 恒在前且顺序稳定(Q1/Q8/Q9)
- test_merge_instances_discovered_set_replaced: 旧发现条目**整批替换**剪除(死端点不堆积)+ **空集不替换**(C1)
- test_no_opaque_reason_leaks: 选项页无 `未知` 字面量 + 后台每个 reason 都有中文结论映射(§3.4/Q5)
- test_conn_state_judgement_matches_badge: **跨层机械比对** —— 徽标态(background.js::badgeStateOf)与顶部
  总览态(options.js::connStateOf)是同一判据的两个展示面, 切出函数体真跑同一张真值表逐输入一致 +
  五态键集(BADGE vs CONN_STATE_TEXT)同源 + 徽标图例(options.html)与 BADGE label 同源
### 连接区 UI 重排 + 实例状态入表轮(计划 26-10-16-0214 S4-S6)
- test_row_health_of_four_states: 真跑 options.js::rowHealthOf —— 行级四态真值表(绿=正常 / 红=401/403
  token 或来源被拒, 红优先于 ok / 橙=连败(连不上·连败 N 轮) / 灰=还没轮过; 旧台账无 state 字段按 C2
  降级: ok->绿, 否则橙, 无迁移脚本)
- test_probe_all_message_writes_ledger: 真跑 background.js —— probe-all 消息(三实例 ok/down/401 各一)
  逐实例只读探测, 结论经 noteInstanceHealth 落台账(401 记 ok:true + state='401' = 行级红判据源);
  probe-one 已随 R3 取消, 两文件都不得出现
- test_retest_all_goes_through_background: 「重测全部」走 sendMessage probe-all(选项页该路径无直接
  fetch); probeMainInstance 保留但只服务 discoverNow 命中后的即时结论(C1 单一写入口: 台账唯一写者是
  后台); 「自测端点连通」与「载入」旧字面量不得回潮(只扫字符串字面量, 注释里的历史说明不算)
- test_badge_legend_says_browser_toolbar: 徽标图例必须写明「浏览器工具栏」(旧歧义措辞「工具栏图标徽标」
  不得回潮 —— 读者会误解为本页实例表)并配框式色样(R4; 站点未授权与发现失败共用红框)
- test_instance_source_badge_is_manual_or_auto: 来源徽标只有「手动/自动」两值(R2, 「优先」徽标废止;
  上游 26-10-15-2357 口径演进 —— 历史测试中不存在 [优先] 徽标断言, 无需翻转, 以本守阵为准)
  + 「自测端点连通」「载入」按钮字面量不得回潮 + 实例表真表头(状态列)
- test_badge_reflects_connection_state 更新(R4 徽标文字折中): 平时徽标文本清空(状态色外框零遮挡),
  仅「发现失败」与「站点未授权」两态为红 `!` + setBadgeBackgroundColor; 旧 OK/.. 徽标文案不得回潮
- test_badge_icon_frame_mapping: 真跑 background.js::badgeIconOf —— 五态->{16,32} 图标路径映射 +
- test_extension_quota_windows_roll_over
  8 个 PNG(scripts/gen_ext_icons.py 生成物)在盘上 + manifest action.default_icon 指向基础图
  (未配置态与安装初始态共用; Chrome 无还原默认图标 API, 外框方案必须自带基础图)
### 站点可选权限轮(计划 26-10-29-0147 W1/D5): 未授权即拒发 + 逐站展示
- test_origin_grant_matches_across_layers: 真跑两份 `originGranted`(background.js 与 options.js 各写一份,
  两页不共享 SW 作用域)—— 三种模式(`*` / `*.parent` / 精确)+ scheme 必须一致的真值表逐行对照,
  漂移即红; `permissions.contains` 判多 origin 的写法不得回潮(只在**全部**授予时为真)
- test_run_task_refuses_without_site_permission: 真跑 background.js —— 站点未授权时**零请求**
  (stub 的 fetch 一次都不许被调)且回 `kind:'no-permission'`; 授权后同一任务照常发出
- test_run_task_marks_network_failure_when_granted: 已授权却 `Failed to fetch` ⇒ `kind:'network'`
  (与缺权限是两个动作: 查代理 vs 去授权; 都不许落到页面层 `HrFetchError`)
"""

import json

import os

import pathlib

import re

import shutil

import subprocess

import pytest

from auto_qb.hr.channel import API_RESULT, API_SITES, API_TASKS, TOKEN_HEADER, HrChannelError, HrResult

from auto_qb.hr.discovery import API_DISCOVER, DISCOVERY_DEFAULT_PORT

from extension_proxy_support import (
    BACKGROUND_JS,
    background_bundle,
    background_text,
    CHALLENGE_LIKE,
    DISCOVERY_JS,
    EXT_DIR,
    LOGIN_LIKE,
    MANIFEST,
    NORMALIZE_JS,
    OPTIONS_HTML,
    OPTIONS_JS,
    PAGE_WITH_TABLE,
    SITE_CAPS_JS,
    _DISCOVERY_HELPERS_TRACE,
    _NODE_RUN_BADGE_ICON,
    _NODE_RUN_CROSS_LAYER_STATE,
    _NODE_RUN_DISCOVERY_FLOW,
    _NODE_RUN_DISCOVERY_HELPERS,
    _NODE_RUN_EVENTS,
    _NODE_RUN_LOGGER,
    _NODE_RUN_LOGIN_PAGE,
    _NODE_RUN_NOISE,
    _NODE_RUN_PAGE_FETCH,
    _NODE_RUN_PROBE_ALL,
    _NODE_RUN_QUOTA,
    _NODE_RUN_ROW_HEALTH,
    _NODE_RUN_SELFHEAL,
    _NODE_RUN_SITE_PERM,
    _PAGE_FETCH_TRACE,
    _QUOTA_TRACE,
    _SELFHEAL_TRACE,
    _SITE_PERM_TRACE,
    _calls,
    _first,
    _js_func_body,
    _js_object_block,
    _js_object_keys,
    _js_string_literals,
    _node,
    _read,
    _run_node,
    discovery_helpers_trace,
    page_fetch_trace,
    quota_trace,
    selfheal_trace,
    site_perm_trace,
)


def test_no_opaque_reason_leaks():
    """失败码不再外泄(计划 §3.4/Q5): 选项页不得出现 `未知` 字面量; 后台能给出的**每一个** reason 都要有
    中文结论 —— 否则用户又会看到 `发现未命中(no-hit)` / `发现未命中(未知)` 这种要自己猜的原始码
    (后者正是用户 2026-10-15 实报的形态)。映射值必须是真·中文结论, 不能把码抄一遍。
    """
    js = _read(OPTIONS_JS)
    assert "未知" not in js, "`未知` 字面量必须从选项页消失(实报的「发现未命中(未知)」就是它)"
    block = _js_object_block(js, "const DISCOVERY_REASON_TEXT = {")
    mapped = _js_object_keys(block)
    assert mapped, "选项页要有 DISCOVERY_REASON_TEXT(失败码 -> 中文结论)映射表"
    reasons = sorted(set(re.findall(r"reason: '([^']+)'", background_text())))
    assert reasons, "后台应能给出失败码(改用别的键名时这条一起改)"
    for reason in reasons:
        assert reason in mapped, f"后台会报 reason={reason}, 选项页却没有中文映射(会原样外泄给用户)"
    for value in re.findall(r":\s*'([^']*)'", block):
        assert re.search(r"[\u4e00-\u9fff]", value), f"映射值必须是中文结论(不是把码抄一遍): {value!r}"


def test_page_fetch_is_headless_when_html_looks_fine():
    """!默认必须**无界面**: 直取(带站点 cookie 的 fetch)就能拿到页面时, 绝不打开任何窗口/标签

    用户实报过两轮(先「抓数据时打开新标签」, 改完又「打开新窗口」)—— 所以这里钉死的不是
    「窗口该怎么开」, 而是**能不开就不开**: 站点侧页面(NexusPHP 这类)本来就是服务端渲染的表格。
    """
    trace = page_fetch_trace()
    if not trace:
        return  # 没装 node: 与其它前端守阵同口径静默跳过
    direct = trace["direct"]
    assert direct["out"] == {"text": PAGE_WITH_TABLE, "rendered": False}
    assert _calls(direct, "windows.create") == [], f"直取时不得开窗口: {direct['calls']}"
    assert _calls(direct, "tabs.create") == [], f"直取时不得开标签: {direct['calls']}"


def test_page_fetch_renders_offscreen_only_when_needed():
    """直取内容不像页面(挑战页 / 需 JS 渲染)才退到渲染通道: **离屏 popup + 不聚焦**, 用完连窗口删掉"""
    trace = page_fetch_trace()
    if not trace:
        return
    render = trace["render"]
    assert render["out"]["rendered"] is True, "内容里连表格都没有就该升级到渲染通道"
    assert render["out"]["text"] == PAGE_WITH_TABLE, "渲染通道要返回 DOM 快照"

    created = _first(render, "windows.create")
    assert created is not None, f"渲染通道要自己建窗口: {render['calls']}"
    opts = created[1]
    assert opts.get("type") == "popup", "popup 不进任务栏(比普通窗口更难被用户看到)"
    assert opts.get("state") == "minimized", "创建时就最小化(不再依赖后续 update)"
    assert opts.get("focused") is False, "绝不能抢焦点"
    assert opts.get("left") == -32000 and opts.get("top") == -32000, "必须离屏(最小化在部分平台仍会先显示)"
    assert opts.get("url") == "https://pt.example.com/myhr.php?hrtype=A", "建窗口时直接带目标 URL"
    assert _calls(render, "tabs.create") == [], "不得往用户窗口里开标签"
    assert _calls(render, "windows.remove") == ["windows.remove"], "用完要连窗口一起删"


def test_page_fetch_renders_when_direct_fetch_hits_login_page():
    """直取拿到**登录页**(带表格, 所以表格判据放过它)时也要升级渲染 —— SameSite 的安全网

    无 `SameSite` 属性的 cookie 按 Lax 对待, 而扩展发起的 fetch 算跨站子资源请求, 有可能不带 cookie。
    若不把「登录页」当成升级信号, 就会把「扩展取不到登录态」误报成站点改版(表头缺失), 把排查引到
    错的方向。渲染通道是真正的顶层导航, 一定带 cookie。
    """
    trace = page_fetch_trace()
    if not trace:
        return
    login = trace["login"]
    assert login["out"]["rendered"] is True, "登录页要升级渲染, 不能当正常页面"
    assert login["out"]["text"] == PAGE_WITH_TABLE, "升级后拿到的应当是渲染 DOM"
    assert _calls(login, "windows.create") == ["windows.create"], "升级就要开那个离屏窗口"


def test_page_fetch_hands_focus_back_when_window_steals_it():
    """万一建窗口仍把浏览器抬到前台: 取完要把焦点还回原窗口(用户可能正在打字)"""
    trace = page_fetch_trace()
    if not trace:
        return
    stolen = trace["steal"]
    restore = [c for c in stolen["calls"] if c[0] == "windows.update" and c[1] == 1]
    assert restore and restore[0][2].get("focused") is True, \
        f"焦点被抢走后要还回原窗口: {stolen['calls']}"


def test_extension_quota_caps_and_refuses():
    """超限即**拒发**: 不发请求 + 回传 kind=ext-quota + retry_after(后端据此让位, 不计失败)
    !这条闸的意义在「后端出错时」: 后端频控写错 / 配置被改坏 / 有人手工灌任务时, 浏览器仍然
    打不爆站点。所以断言要看两件事: 1.第 cap+1 次被拒 2.**它真的没有发出请求**(只看回传字段不算数)。
    阈值动态取 site-caps.js 现值, 不硬编码(09d4109 阈值上提时硬编码守阵漂移, 见基线 26-09-28-0041)。
    """
    trace = quota_trace()
    if not trace:
        return  # 没装 node: 与其它前端守阵同口径静默跳过
    pages = trace["pages"]
    ok_pages = [p for p in pages if p.get("ok")]
    refused = [p for p in pages if not p.get("ok")]
    cap = trace["pageHourCap"]
    assert len(ok_pages) == cap, f"本小时访问上限 {cap} 次: {[p.get('error') for p in pages]}"
    assert len(refused) == 1, "超限那次必须被拒"
    assert refused[0].get("kind") == "ext-quota", f"要能被后端识别成配额让位: {refused[0]}"
    assert refused[0].get("retry_after", 0) > 0, "要告诉后端下一个窗口还有多久"
    assert "本小时" in refused[0].get("error", ""), refused[0].get("error")
    assert trace["fetchesAfterPages"] == cap, f"被拒的那次**不得发出请求**(发出去就白算安全网): {trace}"
    assert trace["torrent"].get("ok") is True, "下载与访问分开计数: 页面用满不该挡住 .torrent"
    assert trace["fetchesAfterTorrent"] == cap + 1


def test_extension_quota_windows_roll_over():
    """窗口键翻篇就归零(与后端同一套口径), 日上限独立生效 —— 不能出现「一次超限永久停摆」"""
    trace = quota_trace()
    if not trace:
        return
    assert trace["afterRollover"].get("ok") is True, f"小时窗口翻篇后应恢复: {trace['afterRollover']}"
    day = trace["dayRefusal"]
    assert day.get("ok") is False and day.get("kind") == "ext-quota"
    assert "本日" in day.get("error", ""), day.get("error")
    assert day.get("retry_after", 0) > 0 and day.get("retry_after", 0) <= 86400
    assert trace["fetchesAtEnd"] == trace["fetchesAfterTorrent"] + 1, "日上限那次同样不得发出请求"


def test_extension_torrent_login_page_detected():
    """download.php 返回 HTML ⇒ 回传 kind=login-page(后端按「登录失效」处置, 不计取数失败)"""
    node = _node()
    if not node:
        return  # 没装 node: 与其它前端守阵同口径静默跳过
    proc = _run_node([node, "-e", _NODE_RUN_LOGIN_PAGE, background_bundle(), str(DISCOVERY_JS), str(SITE_CAPS_JS)])
    assert proc.returncode == 0, f"node 跑 background.js 的登录页场景失败: {proc.stderr.strip()}"
    payload = json.loads(proc.stdout)["payload"]
    assert payload.get("ok") is False
    assert payload.get("kind") == "login-page", f"必须标成登录页让后端免计失败: {payload}"
    assert "登录" in payload.get("error", ""), payload.get("error")


def test_background_events_ring_dual_write():
    """选项页两张表的数据源: 后台与日志**同源双写**结构化事件环 —— 成功/失败/让位/登录页都进表

    解析日志文案做表太脆, 故钉字段级契约: tag 分类(ok/quota/login/error) + host/kind/ms/bytes。
    """
    node = _node()
    if not node:
        return  # 没装 node: 与其它前端守阵同口径静默跳过
    proc = _run_node([node, "-e", _NODE_RUN_EVENTS, background_bundle(), str(DISCOVERY_JS), str(SITE_CAPS_JS)])
    assert proc.returncode == 0, f"node 跑 background.js 的事件环场景失败: {proc.stderr.strip()}"
    out = json.loads(proc.stdout)
    assert out["quotaPayload"].get("kind") == "ext-quota", "页面访问超限那次要被扩展侧硬上限挡下(场景前提)"
    events = out["events"]
    assert [e.get("tag") for e in events] == ["ok", "ok", "error", "ok", "login", "quota"], \
        f"六类场景各记一条且顺序正确: {events}"
    assert [e.get("kind") for e in events] == ["page", "page", "page", "torrent", "torrent", "page"]
    assert all(e.get("host") == "pt.example.com" for e in events), "host 要从 URL 派生(表一按站点聚合的键)"
    ok1 = events[0]
    assert ok1.get("status") == 200 and ok1.get("bytes", 0) > 0 and ok1.get("ms", 0) >= 0, \
        f"成功事件要带 HTTP/字节/耗时(表二的列): {ok1}"
    assert "403" in events[2].get("note", ""), "失败事件要能把原因带进 note"
    assert "HTML" in events[4].get("note", ""), "登录页事件要能看出来是要人工登录"
    assert "本小时" in events[5].get("note", ""), "让位事件要能看出来是配额原因"


def test_logger_levels_ring_truncation_and_clear():
    """运行日志: 分级(低于记录级别直接丢) / 环形上限(丢最旧) / 超长截断 / 清空 —— 真跑 background.js"""
    node = _node()
    if not node:
        return  # 没装 node: 与其它前端守阵同口径静默跳过
    proc = _run_node([node, "-e", _NODE_RUN_LOGGER, background_bundle(), str(DISCOVERY_JS), str(SITE_CAPS_JS)])
    assert proc.returncode == 0, f"node 跑 background.js 的日志场景失败: {proc.stderr.strip()}"
    got = json.loads(proc.stdout)
    assert got["byLevel"] == ["info", "warn", "error"], f"低于记录级别(debug)要直接丢弃: {got['byLevel']}"
    fields = got["fields"]
    for key in ("t", "lvl", "cat", "msg", "站点", "url", "耗时"):
        assert key in fields, f"日志条目缺字段 {key}: {fields}"
    assert got["longMark"] and got["longLen"] < 450, f"超长字段必须截断(整份 HTML 进日志会撑爆配额): {got}"
    assert got["ringLen"] == 10 and got["ringFirst"] == "行 16" and got["ringLast"] == "行 25", f"环形缓冲要丢最旧的: {got}"
    assert got["debugKept"] and got["infoDropped"], f"记录级别要实时生效: {got}"
    assert got["afterClear"], f"清空后 storage 里应是空数组: {got}"


def test_connection_failure_logs_head_tail_only():
    """连不上时只打「头尾」(2026-09-28 用户实报: 后端不在跑时每轮一条全量排查清单 ERROR +
    状态栏同文复读, 日志环被灌满): 首报全量 ERROR; 连败期降 debug(默认记录级别下不落盘),
    每 30 轮重提一次全量; 恢复补一句 INFO 并清连败计数; 状态栏同文复读降 debug。
    """
    node = _node()
    if not node:
        return  # 没装 node: 与其它前端守阵同口径静默跳过
    proc = _run_node(
        [node, "-e", _NODE_RUN_NOISE,
         background_bundle(),
         str(NORMALIZE_JS),
         str(DISCOVERY_JS),
         str(SITE_CAPS_JS)]
    )
    assert proc.returncode == 0, f"node 跑 background.js 的降噪场景失败: {proc.stderr.strip()}"
    got = json.loads(proc.stdout)

    def has(lines, prefix):
        return any(l.startswith(prefix) for l in lines)

    # 首报: 全量排查清单照旧(error), 状态栏文本变化记 info
    assert len(got["r1"]) == 3, got["r1"]
    assert has(got["r1"], "info|轮询|轮询开始(定时): 1 个实例"), got["r1"]
    assert has(got["r1"], "error|请求|拉任务清单失败: 连不上") and any("逐条确认" in l for l in got["r1"]), got["r1"]
    assert has(got["r1"], "info|状态|"), got["r1"]
    # 连败期: 不再打 error, 降为 debug 短句; 状态栏同文复读也降 debug
    for rnd, n in ((got["r2"], 2), (got["r3"], 3)):
        assert all(not l.startswith("error|") for l in rnd), rnd
        assert has(rnd, f"debug|请求|拉任务清单失败(已连续 {n} 轮, 降噪: 排查清单见首报)"), rnd
        assert has(rnd, "debug|状态|"), rnd
    assert list(got["streak"].values())[0]["n"] == 3, f"连败数要真落 storage(SW 回收也不丢): {got['streak']}"
    # 第 30 轮: 重提全量(防彻底失联无感)
    assert any(l.startswith("error|请求|拉任务清单失败(已连续 30 轮): 连不上") and "逐条确认" in l for l in got["r30"]), got["r30"]
    # 恢复: 一句 INFO + 计数清空 + 状态栏文本变化恢复 info
    assert has(got["rOk"], "info|请求|端点恢复(此前连续失败 30 轮)"), got["rOk"]
    assert got["streakAfterOk"] == {}, f"恢复后连败计数要清掉: {got['streakAfterOk']}"
    assert has(got["rOk"], "info|状态|本机: 无任务"), got["rOk"]
    # 恢复后再挂: 重新首报全量
    assert any(l.startswith("error|请求|拉任务清单失败: 连不上") and "逐条确认" in l for l in got["rAgain"]), got["rAgain"]


def test_discovery_helpers_behave():
    """真跑 discovery.js —— 候选推导与后端同源(65535 截断)/ 合并语义(替换同端点+保留手填+标自动)/ 配对判定 / 形态过滤"""
    got = discovery_helpers_trace()
    if not got:
        return  # 没装 node: 与其它前端守阵同口径静默跳过
    assert got["apiDiscover"] == API_DISCOVER and got["defaultPort"] == DISCOVERY_DEFAULT_PORT
    assert got["cands"] == [f"http://192.168.1.10:{18788 + i}" for i in range(8)], \
        "候选表与后端同源: 18788 起连号 8 个(计划 26-11-10-0515 S2/D6)"
    assert got["candsCap"] == ["http://192.168.1.10:65534", "http://192.168.1.10:65535"], "上限 65535 截断(与后端同源)"
    assert got["candsBad"] == []
    assert got["url"] == f"http://192.168.1.10:18788{API_DISCOVER}", "去尾斜杠拼路径(不出现双斜杠)"
    assert got["pairYes"] is True and got["pairNoStatus"] is False and got["pairNoError"] is False
    merged = got["merged"]
    assert [e["endpoint"] for e in merged] == [
        "http://192.168.1.10:5001",
        "http://127.0.0.1:8788",
        "http://192.168.1.10:5002",
    ], "手动置顶且顺序稳定, 发现只补齐手动没覆盖的端点, 缺 token 的半条不收"
    assert merged[0] == {"name": "m", "endpoint": "http://192.168.1.10:5001", "token": "old"}, \
        "同端点**手动整条胜**(Q8): 手动的 name/token 都不被发现的 d1/new 覆盖"
    assert merged[1] == {"name": "hand", "endpoint": "http://127.0.0.1:8788", "token": "h"}, "手填条目原样保留(无 source 标)"
    assert merged[2]["token"] == "t2" and merged[2]["source"] == "discovered", "补齐的发现条目标「自动」"
    assert [e["endpoint"] for e in got["replaced"]] == [
        "http://127.0.0.1:8788",
        "http://192.168.1.10:5001",
        "http://192.168.1.10:5002",
    ], "发现集整批替换(Q2): 旧 discovered 条目(死端点 5099)必须被剪除, 不再永久堆积"
    assert got["emptyKept"] == [
        {
            "name": "hand",
            "endpoint": "http://127.0.0.1:8788",
            "token": "h"
        },
        {
            "name": "stale",
            "endpoint": "http://192.168.1.10:5099",
            "token": "x",
            "source": "discovered"
        },
    ], "空集例外(C1): 发现返回空集**不得清空**发现集(后端重启瞬间清空 = 自断连接)"
    assert got["manualFlags"] == [True, False, True], "旧数据无 source 字段判为手动(C8: 零迁移获优先语义)"
    assert got["validOk"] is True and got["validNoArray"] is False and got["validHalf"] is False


def test_merge_instances_manual_priority():
    """合并语义 · **手动优先**(Q1/Q8/Q9): 手动条目 = 高优先级的用户显式指定 —— 同端点冲突时**手动整条胜**
    (连 name/token 都不取发现的), 且恒在前、保持原顺序; 发现只负责「补齐手动没覆盖的端点」。

    !旧语义是「同端点被发现覆盖」, 被计划 26-10-15-2357 S1 翻转(用户更正 Q1: 手动是高优先级而非兜底)。
    """
    got = discovery_helpers_trace()
    if not got:
        return  # 没装 node: 与其它前端守阵同口径静默跳过
    merged = got["merged"]
    assert [e["endpoint"] for e in merged[:2]] == [
        "http://192.168.1.10:5001",
        "http://127.0.0.1:8788",
    ], f"手动条目恒在前且保持原顺序(不因周期性重发现抖动): {merged}"
    assert merged[0] == {"name": "m", "endpoint": "http://192.168.1.10:5001", "token": "old"}, \
        "同端点手动整条胜(Q8): 发现给的 d1/new 不得覆盖手动的 name/token"
    assert merged[1] == {"name": "hand", "endpoint": "http://127.0.0.1:8788", "token": "h"}, \
        "手动条目原样保留(不带 source 标 = 判手动)"
    assert merged[2]["endpoint"] == "http://192.168.1.10:5002" and merged[2]["source"] == "discovered", \
        "发现只补齐手动没覆盖的端点(这条 5002 手动没指定)"
    assert got["manualFlags"] == [True, False, True], \
        "isManualEntry: 缺 source 字段的旧数据判为手动(C8 零迁移获优先语义)"


def test_merge_instances_discovered_set_replaced():
    """合并语义 · **发现集租约**(Q2/C1): 每次成功发现**整批替换**旧发现集 —— 死端口的条目自然被剪除,
    不再像旧实现那样「只增不减、永久堆积」; 但**空集不替换**: 后端重启瞬间注册表可能还没心跳(发现返回
    空集), 此时清空发现集 = 自断连接(且实例为空时连「失败即发现」都不触发, 只能干等周期)。
    """
    got = discovery_helpers_trace()
    if not got:
        return  # 没装 node: 与其它前端守阵同口径静默跳过
    assert [e["endpoint"] for e in got["replaced"]] == [
        "http://127.0.0.1:8788",
        "http://192.168.1.10:5001",
        "http://192.168.1.10:5002",
    ], f"发现集整批替换(Q2): 旧 discovered 条目(死端点 5099)必须被剪除, 不再永久堆积: {got['replaced']}"
    assert all(e.get("source") == "discovered" for e in got["replaced"][1:]), "替换进来的发现条目都标「自动」"
    assert got["emptyKept"] == [
        {
            "name": "hand",
            "endpoint": "http://127.0.0.1:8788",
            "token": "h"
        },
        {
            "name": "stale",
            "endpoint": "http://192.168.1.10:5099",
            "token": "x",
            "source": "discovered"
        },
    ], "空集例外(C1): 发现返回空集**不得清空**发现集(后端重启瞬间清空 = 自断连接)"


def test_background_discovery_flow():
    """真跑 background.js 的发现流程 —— 八候选并行探测(命中次位)/ 配对码随头上来 / 合并落盘 +
    清等待标记 / 401 pairing_required 置标记 / 异形应答按「非本服务」忽略 / 全未命中明确报告(退手动)"""
    node = _node()
    if not node:
        return  # 没装 node: 与其它前端守阵同口径静默跳过
    proc = _run_node(
        [
            node, "-e", _NODE_RUN_DISCOVERY_FLOW,
            background_bundle(),
            str(NORMALIZE_JS),
            str(DISCOVERY_JS),
            str(SITE_CAPS_JS)
        ]
    )
    assert proc.returncode == 0, f"node 跑 background.js 的发现流程失败: {proc.stderr.strip()}"
    got = json.loads(proc.stdout)
    assert got["hit"]["ok"] is True and got["hit"]["merged"] == 2, got["hit"]
    discover_calls = [c for c in got["hitCalls"] if c[0].endswith(API_DISCOVER)]
    assert len(discover_calls) == 8, f"八个候选并行探测(计划 26-11-10-0515 S2/D6): {got['hitCalls']}"
    assert all(c[1] == "123456" for c in discover_calls), "配对码随 X-Hr-Pairing 上来"
    assert [e["endpoint"] for e in got["instances"]] == ["http://192.168.1.10:5001", "http://192.168.1.10:5002"]
    assert all(e["source"] == "discovered" for e in got["instances"]), "合并条目标「自动」"
    assert got["pairingCleared"] is False, "命中后清配对等待标记"
    assert got["pair"]["ok"] is False and got["pair"]["reason"] == "pairing_required" and got["pairFlag"] is True
    assert got["weird"]["ok"] is False and got["weird"]["reason"] == "no-hit", "异形应答 = 非本服务, 忽略"
    assert got["down"]["ok"] is False and got["down"]["reason"] == "no-hit", "连接失败不静默(日志 + 状态行)"


def test_discovery_period_is_two_minutes():
    """周期发现 = 2 分钟(Q3): 数据端口重启即变, 10 分钟的空窗期用户会当成「扩展坏了」

    !这条必须与 background.js 的常量同源读取 —— 写死 2 会变成「改了常量但守阵不知道」。
    """
    trace = selfheal_trace()
    if not trace:
        return
    assert trace["period"] == 2, f"周期发现应为 2 分钟(Q3), 实际 {trace['period']}"
    assert trace["minGapMs"] == 60000, f"失败触发的 60s 节流不该被一起改掉: {trace['minGapMs']}"


def test_discovery_triggers_on_any_failure():
    """**任一实例拉取失败即触发一次发现**(Q3) —— 旧口径「全部实例连败」在 1 死 1 活时不触发,
    只能干等周期; 60s 节流不变(发现只打本机 loopback, 但也不该变成第二轮询); 401 不算失败
    (端点有应答 = 连接是通的, 属配置态); 实例清单为空也仍按周期发现(R1, 否则发现集为空时再也回不来)。
    """
    trace = selfheal_trace()
    if not trace:
        return
    a, b, c, d, e = (trace[k] for k in ("aDiscovers", "bDiscovers", "cDiscovers", "dDiscovers", "eDiscovers"))
    assert a == 8, f"1 死 1 活(旧口径不触发)也要跑一轮发现(每轮 = 候选表 8 个并行探测): {a}"
    assert b == a, f"60s 内不重复发现(节流): {a} -> {b}"
    assert c == b, f"全 401 不该触发发现(端点有应答, 距上次 70s: 误判为失败就会开火): {b} -> {c}"
    assert d == c + 8, f"同钟位正对照: 真失败必须开火(否则上一轮的「没开火」说明不了什么): {c} -> {d}"
    assert e == d + 8, f"实例清单为空也要按周期发现(R1): {d} -> {e}"


def test_discovery_snapshot_is_structured():
    """发现结果必须落**结构化快照**(S2): 选项页顶部总览与逐候选结果都从它渲染 —— 此前结果只进
    状态栏最后一句与日志, 「后台发现了但页面看不见」正是用户实报的静默感来源。"""
    trace = selfheal_trace()
    if not trace:
        return
    got = trace["aSnapshot"]
    assert got, "每次发现收尾都要落 lastDiscovery 快照"
    assert got["ok"] is True and got["port"] == "18788" and got["merged"] == 3, got
    assert got["reason"] == "" and got["answered"] is True and got["at"] > 0, got
    cands = got["candidates"]
    assert [c["url"] for c in cands] == [f"http://127.0.0.1:{18788 + i}" for i in range(8)], \
        f"逐候选结果要按候选表顺序落(记 base 而非拼好路径的 URL: 选项页按端口报结论): {cands}"
    assert cands[0]["note"] == "" and all(c["note"] == "HTTP 404" for c in cands[1:]), \
        f"每个候选都要带自己的结论(选项页据此渲染「18789 连接失败 / 18795 异形应答」这类文案): {cands}"


def test_instance_health_ledger_records_per_instance():
    """实例健康台账按端点落(S2) —— 选项页的「疑似失效」标记(C3 阈值 >=3 轮)靠它; 连续失败计数
    必须真累加、成功必须清零, 且实例清单外的端点要被剪掉(防死端点台账堆积, R3)。"""
    trace = selfheal_trace()
    if not trace:
        return
    first = trace["aHealth"]
    assert first["http://127.0.0.1:9001"]["ok"] is True, f"活的实例记 ok: {first}"
    assert first["http://127.0.0.1:9001"]["failStreak"] == 0, first
    assert first["http://127.0.0.1:9002"]["ok"] is False, f"坏的实例记 not-ok: {first}"
    assert first["http://127.0.0.1:9002"]["failStreak"] == 1, f"首轮失败计数应为 1: {first}"
    assert first["http://127.0.0.1:9002"]["note"], "台账要带一句结论(选项页提示里要显示)"
    second = trace["bHealth"]
    assert second["http://127.0.0.1:9002"]["failStreak"] == 2, f"连续失败要累加: {second}"
    assert trace["eHealth"] == {}, f"实例清单为空时台账应剪空(不残留死端点): {trace['eHealth']}"


def test_badge_reflects_connection_state():
    """工具栏图标四态外框 + 徽标文字折中(R4, 计划 26-10-16-0214 S6): 未配置 / 连接正常 / 重连中 /
    发现失败 —— 判据见计划 §3.3, 「重连中 vs 发现失败」的边界是 C4(候选全无应答才叫发现失败)。

    徽标(文字层)由浏览器固定渲染, 会挡住图标且无 API 可调 —— R4 拍板「状态色外框」: setIcon 重画
    图标本体, 平时徽标文本清空(纯外框零遮挡), 仅「发现失败」态追加红色 `!`(故障报警 + 色觉冗余);
    旧 OK/.. 徽标文案随 R4 废止。禁用时必须清空, 点图标要能进选项页(那是报警后的第一动作)。
    """
    trace = selfheal_trace()
    if not trace:
        return
    assert trace["badgeStates"] == ["unconfigured", "ok", "reconnecting", "discoveryFailed"], trace["badgeStates"]
    ok = trace["badgeOk"]
    assert ok["text"] == "", f"R4: 平时徽标文本清空(状态色外框零遮挡), 不再落 OK: {ok}"
    assert trace["iconOk"] == {"16": "icons/icon-ok16.png", "32": "icons/icon-ok32.png"}, \
        f"连接正常 = 绿框图: {trace['iconOk']}"
    assert "连接正常" in (ok["title"] or ""), f"悬停标题要给中文结论: {ok}"
    base_of = {"unconfigured": "icon", "ok": "icon-ok", "reconnecting": "icon-warn", "discoveryFailed": "icon-bad"}
    for st in trace["iconStates"]:
        base = base_of[st["state"]]
        assert st["icon"] == {"16": f"icons/{base}16.png", "32": f"icons/{base}32.png"}, \
            f"{st['state']} 态图标路径: {st['icon']}"
        if st["state"] == "discoveryFailed":
            assert st["text"] == "!" and st["color"] == "#b0453d", f"发现失败态要落红底 !: {st}"
        else:
            assert st["text"] == "", f"{st['state']} 态徽标文本必须清空(零遮挡): {st}"
    assert trace["badgeDisabled"]["text"] == "", f"禁用时清空徽标: {trace['badgeDisabled']}"
    assert trace["iconDisabled"] == {"16": "icons/icon16.png", "32": "icons/icon32.png"}, \
        f"禁用回落基础无框图(未配置态与安装初始态共用): {trace['iconDisabled']}"
    assert trace["hasOnClicked"] is True, "要注册 chrome.action.onClicked(无 default_popup 才收得到)"
    assert trace["opened"] == 1, f"点图标要打开选项页: {trace['opened']}"


def test_badge_text_is_ascii_only():
    """徽标文案只许 ASCII(code-style: 代码/配置禁 emoji 与图形符号)

    徽标字号极小, 对勾/省略号这类图形符在部分平台渲染成方框; 语义交给颜色 + 悬停标题表达。
    """
    bg = background_text()
    block = bg[bg.index("const BADGE = {"):bg.index("function badgeStateOf")]
    texts = re.findall(r"text: '([^']*)'", block)
    # 26-10-29-0147 D5 起五态(新增 noSitePermission): 改结构时这条一起改
    assert len(texts) == 5, f"徽标五态各有文案(改结构时这条一起改): {texts}"
    for text in texts:
        assert text.isascii(), f"徽标文案出现非 ASCII 字符 {text!r}(小字号下渲染成方框)"


def test_row_health_of_four_states():
    """行级四态真值表(计划 §3.2/S5 1): 绿=正常 / 红=401 或 403(token 或来源被拒, 红优先于 ok) /
    橙=连不上·连败 N 轮 / 灰=还没轮过(无台账条目); 旧台账无 state 字段按 C2 降级(ok->绿, 否则橙)。"""
    node = _node()
    if not node:
        return
    proc = _run_node([node, "-e", _NODE_RUN_ROW_HEALTH, str(OPTIONS_JS)])
    assert proc.returncode == 0, f"node 跑 rowHealthOf 失败: {proc.stderr.strip()}"
    got = {e["k"]: e["out"] for e in json.loads(proc.stdout)}
    assert got["null"] == {"level": "none", "text": "还没轮过"}, got["null"]
    assert got["empty"] == {"level": "none", "text": "还没轮过"}, got["empty"]
    assert got["ok"] == {"level": "ok", "text": "正常"}, got["ok"]
    assert got["ok-state-ok"] == {"level": "ok", "text": "正常"}, got["ok-state-ok"]
    for k in ("bad-401-oktrue", "bad-403-oktrue", "bad-401-okfalse", "bad-403-okfalse"):
        assert got[k] == {"level": "bad", "text": "token / 来源被拒"}, f"{k}: {got[k]}"
    assert got["warn-legacy-no-state"] == {"level": "warn", "text": "连不上"}, "C2 旧台账无 state 降级为橙"
    for k in ("warn-down", "warn-http", "warn-bad-endpoint", "warn-streak1"):
        assert got[k] == {"level": "warn", "text": "连不上"}, f"{k}: {got[k]}"
    assert got["warn-streak2"] == {"level": "warn", "text": "连败 2 轮"}, got["warn-streak2"]
    assert got["warn-streak5-down"] == {"level": "warn", "text": "连败 5 轮"}, got["warn-streak5-down"]


def test_probe_all_message_writes_ledger():
    """probe-all(「重测全部」)真跑(计划 S2/S5 2): 消息存在且处理走 noteInstanceHealth —— 三实例
    (ok / down / 401)各探一次, 结构化 state 落台账(401 记 ok:true + state='401': 端点有应答是配置态,
    行级红靠 state 而非 ok); probe-one 已随 R3 取消, 两文件都不得出现。"""
    node = _node()
    if not node:
        return
    proc = _run_node(
        [node, "-e", _NODE_RUN_PROBE_ALL,
         background_bundle(),
         str(NORMALIZE_JS),
         str(DISCOVERY_JS),
         str(SITE_CAPS_JS)]
    )
    assert proc.returncode == 0, f"node 跑 probe-all 失败: {proc.stderr.strip()}"
    got = json.loads(proc.stdout)
    resp = got["resp"]
    assert resp and resp.get("ok") is True and isinstance(resp.get("results"), list) and len(resp["results"]) == 3, resp
    states = [r["state"] for r in resp["results"]]
    assert states == ["ok", "down", "401"], f"逐实例结构化 state(与轮询同口径): {states}"
    health = got["health"]
    assert len(health) == 3, f"台账要按端点落三条: {health}"
    vals = sorted((h["ok"], h["state"]) for h in health.values())
    assert vals == [(False, "down"), (True, "401"), (True, "ok")], f"台账(ok, state): {health}"
    bg = background_text()
    js = _read(OPTIONS_JS)
    # 回潮形态必是带引号的消息字面量(注释里提它不算)
    assert "'probe-one'" not in bg and "'probe-one'" not in js, "probe-one 已随 R3 取消, 不得回潮"


def test_retest_all_goes_through_background():
    """「重测全部」走后台 probe-all(C1 单一写入口): 台账唯一写者是后台, 选项页只读 + 消息触发 ——
    probeMainInstance 保留但只服务 discoverNow 命中后的即时结论(计划 C1 允许的例外); 重测路径不得
    在选项页直接 fetch。「自测端点连通」与「载入」旧字面量不得回潮(字符串字面量口径, 注释不算)。"""
    js = _read(OPTIONS_JS)
    retest = _js_func_body(js, "retestAll")
    assert "probe-all" in retest and "sendMessage" in retest, "重测全部必须经 sendMessage probe-all"
    assert "fetch(" not in retest, "重测路径不得在选项页直接 fetch(单一写入口: 台账唯一写者是后台)"
    assert "probeMainInstance" in js, "probeMainInstance 保留(discoverNow 命中后的即时结论, C1 例外)"
    literals = _js_string_literals(js)
    for old in ("自测端点连通", "载入"):
        leaked = [s for s in literals if old in s]
        assert not leaked, f"旧字面量「{old}」不得回潮(字符串字面量里出现): {leaked}"


def test_badge_legend_says_browser_toolbar():
    """徽标图例措辞守阵(计划 §01 事实澄清/S5 4): 图例必须写明「浏览器工具栏」—— 旧句「工具栏图标徽标
    四态…」未说"浏览器", 读者会误解为本页实例表(用户实问之一); 四态框式色样(R4)齐全。"""
    html = _read(OPTIONS_HTML)
    assert "工具栏图标徽标" not in html, "旧歧义措辞不得回潮(未说「浏览器」, 会被误解为本页元素)"
    i = html.index('id="badgeLegend"')
    legend = html[i:html.index("</p>", i)]
    assert "浏览器工具栏" in legend, "图例必须点明是浏览器工具栏的扩展图标(常驻, 非本页元素)"
    for cls in ("sw-none", "sw-ok", "sw-warn", "sw-bad"):
        assert f'class="sw-frame {cls}"' in legend, f"四态框式色样缺 {cls}(R4)"


def test_instance_source_badge_is_manual_or_auto():
    """来源徽标措辞守阵(R2): 实例徽标只有「手动/自动」两值 —— 旧「优先」徽标废止(用户: 来源列显示
    「优先」本来就是错误的; 行为不变: 手动恒在前, 由 discovery.js::mergeInstances 保证)。上游
    26-10-15-2357 的 [优先] 徽标断言在历史测试中不存在, 无需翻转 —— 口径演进以本守阵为准。"""
    js = _read(OPTIONS_JS)
    badges = re.findall(r'src-tag">([^<]+)<', js)
    assert badges == ["手动", "自动"], f"来源徽标只有两值: {badges}"
    assert '<span class="src-tag">优先</span>' not in js, "「优先」徽标随 R2 废止, 不得回潮"
    assert ">优先<" not in _read(OPTIONS_HTML), "页面里也不得出现「优先」徽标"


def test_badge_icon_frame_mapping():
    """图标外框映射守阵(R4/S6/S5 7): 四态 -> {16,32} 路径纯函数直测 + 8 个 PNG(生成物
    scripts/gen_ext_icons.py)在盘上 + manifest default_icon 指向基础图(Chrome 无还原默认图标 API,
    外框方案必须自带基础图; 未配置态与安装初始态共用); 旧 OK/.. 徽标文案不得回潮。"""
    expected = {
        "unconfigured": {
            "16": "icons/icon16.png",
            "32": "icons/icon32.png"
        },
        "ok": {
            "16": "icons/icon-ok16.png",
            "32": "icons/icon-ok32.png"
        },
        "reconnecting": {
            "16": "icons/icon-warn16.png",
            "32": "icons/icon-warn32.png"
        },
        "discoveryFailed": {
            "16": "icons/icon-bad16.png",
            "32": "icons/icon-bad32.png"
        },
    }
    node = _node()
    if node:
        proc = _run_node([node, "-e", _NODE_RUN_BADGE_ICON, background_bundle()])
        assert proc.returncode == 0, f"node 跑 badgeIconOf 失败: {proc.stderr.strip()}"
        got = dict(json.loads(proc.stdout))
        assert got == expected, f"四态图标路径映射: {got}"
    icons_dir = EXT_DIR / "icons"
    for name in (
        "icon16.png",
        "icon32.png",
        "icon-ok16.png",
        "icon-ok32.png",
        "icon-warn16.png",
        "icon-warn32.png",
        "icon-bad16.png",
        "icon-bad32.png",
    ):
        assert (icons_dir / name).is_file(), f"缺图标文件(scripts/gen_ext_icons.py 生成物入库): {name}"
    manifest = json.loads(_read(MANIFEST))
    assert manifest["action"]["default_icon"] == {"16": "icons/icon16.png", "32": "icons/icon32.png"}, \
        "manifest default_icon 指向基础无框图(未配置态与安装初始态共用)"
    bg = background_text()
    assert "text: 'OK'" not in bg and "text: '..'" not in bg, "旧 OK/.. 徽标文案随 R4 废止, 不得回潮"


def test_conn_state_judgement_matches_badge():
    """**跨层机械比对**: 徽标态(background.js)与顶部总览态(options.js)必须逐输入一致

    两者是同一条判据的两个展示面(计划 §3.3/Q4 2), 此前是两份实现、只靠注释互指 —— 一旦分头演化,
    「徽标报警但页面说正常」这类漂移就没有任何机械拦阻。这里把两个函数体各自从文件里切出来真跑同一张
    真值表(含 C4 边界: 有应答无可用实例 = 重连中 vs 候选全无应答 = 发现失败), 并把四态键集与徽标图例
    文案一起钉住(改判据必须三处一起改)。
    """
    node = _node()
    if not node:
        return  # 没装 node: 与其它前端守阵同口径静默跳过
    proc = _run_node([node, "-e", _NODE_RUN_CROSS_LAYER_STATE, background_bundle(), str(OPTIONS_JS)])
    assert proc.returncode == 0, f"node 跨层比对失败: {proc.stderr.strip()}"
    got = json.loads(proc.stdout)
    assert got["badgeOut"] == got["connOut"], \
        f"徽标态与顶部总览态对同一配置给出了不同结论(同一条判据的两份实现漂移了): {got}"
    assert got["badgeOut"] == [
        "unconfigured", "reconnecting", "ok", "discoveryFailed", "reconnecting", "reconnecting", "ok",
        "noSitePermission", "reconnecting", "ok"
    ], f"五态判据(计划 §3.3 + 26-10-29-0147 D5, C4 边界)取值不符: {got['badgeOut']}"
    assert got["badgeKeys"] == got["connKeys"] == [
        "unconfigured", "ok", "reconnecting", "discoveryFailed", "noSitePermission"
    ], f"五态键集必须同源: BADGE={got['badgeKeys']} CONN_STATE_TEXT={got['connKeys']}"
    html = _read(OPTIONS_HTML)
    legend = html[html.index('id="badgeLegend"'):]
    for label in got["labels"]:
        assert label in legend, f"徽标图例没写全四态(与 background.js 的 BADGE label 同源): 缺 {label}"


def test_origin_grant_matches_across_layers():
    """`originGranted` 在 background.js 与 options.js 是成对的两份 —— 同一张真值表必须逐格一致

    (与 connStateOf/badgeStateOf 同一套纪律: 扩展页与 SW 不共享作用域, 允许成对, 不允许漂移)
    同时钉住匹配语义: scheme 必须一致、`*` 与 `*.父域` 覆盖、通配不覆盖 apex、`<all_urls>` 这种
    裸模式不被认(本扩展**从不**申请它, 出现即说明权限面被改坏)。
    """
    got = site_perm_trace()
    if not got:
        return  # 没装 node: 与其它前端守阵同口径静默跳过
    for idx, (origin, patterns, expected) in enumerate(got["cases"]):
        assert got["bgOut"][idx] == expected, f"background.originGranted({origin}, {patterns}) 应为 {expected}"
        assert got["optOut"][idx] == expected, f"options.originGranted({origin}, {patterns}) 应为 {expected}"
    assert got["bgOut"] == got["optOut"], "两份 originGranted 漂移了(徽标与选项页会给出相反结论)"


def test_run_task_refuses_without_site_permission():
    """取数前预检: 未授权 ⇒ **不发请求** + kind=no-permission + 落 sitePerms 缓存

    这是 2026-10-28 故障的直接对策: 那次三档全失败 12h, 日志一直写「页面取数失败」——
    因为扩展根本没去判「我有没有这个站的权限」, 只能等 fetch 抛一句 `Failed to fetch` 再猜。
    """
    got = site_perm_trace()
    if not got:
        return
    no_perm = got["tasks"][0]
    assert no_perm["payload"]["ok"] is False
    assert no_perm["payload"]["kind"] == "no-permission", no_perm
    assert no_perm["fetches"] == 0, "未授权时不许发出任何站点请求(发也发不出去, 只会多烧一次额度)"
    assert "未授权" in no_perm["payload"]["error"]
    perms = (no_perm.get("sitePerms") or {}).get("https://pt.example.com") or {}
    assert perms.get("granted") is False, f"未授权必须落缓存(徽标读它): {no_perm.get('sitePerms')}"


def test_run_task_marks_network_failure_when_granted():
    """已授权但 fetch 仍报 `Failed to fetch` ⇒ kind=network(通道层); 已授权且成功 ⇒ ok

    !两者必须分开: 缺权限的解是「去授权」, 网络层的解是「查代理/VPN」—— 共用一句 `Failed to fetch`
    正是这次故障被误读成「站点改版」的起点。
    """
    got = site_perm_trace()
    if not got:
        return
    net = got["tasks"][1]
    assert net["payload"]["ok"] is False
    assert net["payload"]["kind"] == "network", net
    assert net["fetches"] == 1, "已授权时请求该照常发出(失败发生在网络层, 不是预检拦的)"
    ok = got["tasks"][2]
    assert ok["payload"]["ok"] is True, ok
    assert ok["payload"].get("kind") is None, "成功回传不得带错误分类"


def test_log_ui_wiring_and_escape():
    """选项页日志面: 清空走后台协议(直接改 storage 会被后台内存缓冲盖回)、渲染必须转义、限渲染条数"""
    js = _read(OPTIONS_JS)
    bg = background_text()
    html = _read(OPTIONS_HTML)
    assert "'clear-logs'" in js and "'clear-logs'" in bg, "清空要经后台清(内存缓冲是唯一写入口)"
    assert "logMax" in js and "logLevel" in js, "条数上限与记录级别要能落盘"
    assert "logFilter" in html and "logView" in html, "分级显示的过滤控件与日志视图要在页面上"
    assert html.index("logView") < html.index("options.js"), "日志容器要在脚本之前(否则 getElementById 拿不到)"
    assert "esc(" in js, "日志渲染必须过 HTML 转义(明细含站点 URL/页面片段, 裸插 innerHTML 是注入面)"
    assert "chrome.storage.onChanged" in js, "后台落盘后选项页要自动刷出来(不用手点刷新)"
    assert "LOG_RENDER_CAP" in js, "全量渲染 10000 行会卡死选项页, 必须限渲染条数"


def test_background_bundle_is_process_private():
    """回归: vm 沙箱聚合脚本落点掺 pid —— xdist worker 共用实例根, 固定名会被并发截断成 0 字节"""
    path = background_bundle()
    assert str(os.getpid()) in os.path.basename(path), \
        "background_bundle 落点缺 pid: 同文件多条用例被 xdist 分到不同 worker, 并发写同名脚本会互相截断"
    assert os.path.getsize(path) > 0, "聚合脚本不得为空"
