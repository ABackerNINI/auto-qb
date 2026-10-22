"""test_extension_proxy 测试计划: 浏览器扩展(HR 取数代理)的静态与行为守阵

扩展是**要用户装进浏览器**的交付物: pytest 跑不到它的运行期, 但四类故障是**静态/半静态可查**的,
且都属于"pytest 全绿、用户装上就报错"的形态 —— 2026-09-24 实测两条:
1. 裸域名直喂 `chrome.permissions.request` ⇒ `Invalid value for origin pattern pt.btschool.club:
   Missing scheme separator.`(**未捕获的 Promise 拒绝**);
2. 端点没起 / 地址写法不对时用户只看到一句 `TypeError: Failed to fetch`(浏览器对网络层失败只给这句)。
故这里钉死: manifest 的作用域、JS 语法、**与后端的协议常量**、以及"输入先归一化再交给浏览器 API"。

## 测试计划(每个测试函数一条)
- test_manifest_is_mv3_and_scoped: MV3 + service worker + 只申请回环与可选站点权限, **绝不出现 <all_urls>**
- test_manifest_covers_loopback_aliases: localhost / [::1] 也在 host_permissions 里(归一化会用到, 否则 fetch 被拦)
- test_js_syntax_passes_node_check: 三个 JS 过 node 语法校验(无 node 时静默跳过, 与前端守阵同口径)
- test_normalizers_behave: **真跑** normalize.js(裸域名补 scheme / localhost 折 127.0.0.1 / https 折 http / 非法报错)
- test_normalizers_are_shared_not_duplicated: 归一化只有一份(normalize.js), 两个消费方都载入它
- test_protocol_matches_backend: 端点路径 / 鉴权头 / 回传字段名与 `hr.channel` + `HrResult` 一致(改一边漏改另一边必红)
- test_options_normalizes_before_browser_api: 站点源与端点先归一化再进权限/存储 API(本次报错的形态)
- test_options_rejections_are_always_handled: 选项页不得留下裸 Promise 拒绝(兜底 unhandledrejection + 逐个 catch)
- test_options_site_fetch_matches_backend: 站点授权清单走 GET /api/hr/sites, 路径/鉴权头与 hr.channel 同源
- test_options_swiss_wiring: 瑞士网格终态(风格选型 A)接线齐全(两表/表单授权/折叠排障区/连接后端一区),
  三档共存机制不回潮; 2026-10-16 S4 合并布局后判据随之更新(删「保存发现地址与配对码」按钮)
- test_background_events_ring_dual_write: 真跑 background.js —— 六类场景双写结构化事件环, tag/host/kind/ms/bytes 契约钉死
- test_page_fetch_is_headless_when_html_looks_fine: 直取能拿到页面时**不得开任何窗口/标签**(用户实报两轮)
- test_page_fetch_renders_offscreen_only_when_needed: 只在内容不像页面时才升级, 且用**离屏 popup 窗口**
- test_page_fetch_renders_when_direct_fetch_hits_login_page: 直取拿到登录页也要升级(SameSite 安全网)
- test_page_fetch_hands_focus_back_when_window_steals_it: 万一窗口抢了焦点, 取完还回原窗口
- test_site_caps_are_shared_single_source: 硬上限只有一份(site-caps.js), 后台与选项页都载入它
- test_extension_quota_caps_and_refuses: 真跑 background.js —— 同站访问/下载各自计数, 超限即**拒发**
  (不发请求 + 回传 kind=ext-quota + retry_after); 窗口键变了计数归零
- test_extension_torrent_login_page_detected: 真跑 background.js —— download.php 返回 HTML(登录页)时
  回传 kind=login-page, 让后端按「HR 登录失效」处置而不烧 .torrent 重试额度(2026-09-25 实报)
- test_logger_levels_ring_truncation_and_clear: 真跑 background.js —— 运行日志分级(低于记录级别直接丢)、
  环形上限(丢最旧)、超长字段截断(页面 HTML 整份进日志会撑爆 storage 配额)、清空后落盘为空数组
- test_connection_failure_logs_head_tail_only: 真跑 background.js —— 连不上时只打「头尾」: 首报全量
  排查清单 ERROR; 连败期降 debug(默认记录级别下不落盘), 每 30 轮重提一次全量; 恢复补一句 INFO 并清
  连败计数(计数落 storage, SW 回收也不丢); 状态栏同文复读降 debug(2026-09-28 用户实报每轮复读)
- test_log_ui_wiring_and_escape: 选项页日志面 —— 清空走 clear-logs 协议(两边一致, 直接改 storage
  会被后台内存缓冲盖回)、渲染过 esc 转义(明细含站点 URL/页面片段)、限渲染条数、
  storage.onChanged 自动刷新、日志容器在脚本之前
- test_options_poll_label_matches_background: 选项页「启用轮询(每 N 分钟…)」文案与 background.js 的
  POLL_MINUTES 同步(漂移史: 文案停在 5 分钟, 实际 v2.6 起已改 1 分钟, 用户照文案理解行为必对不上)

### 去端口+跨机轮(计划 26-10-14-1241 S4): 判据放开与自动发现
- NORMALIZE_CASES 更新: 私网三段逐段放行 / 公网域名拒绝 / https 保留不折 / 新增 disc 类(发现地址缺端口补 18788)
  —— 旧断言「非回环即抛」「https 折 http」是被本计划翻转的旧语义, 随计划更新而非守阵松动
- test_discovery_helpers_behave: 真跑 discovery.js —— 候选推导与后端 discovery_candidates 同源(65535 截断)/
  合并语义(**手动优先**: 同端点手动整条胜 + 手动置顶且顺序稳定; **发现集整批替换**: 旧发现条目被剪除;
  **空集不替换**(C1); 缺 token 半条不收)/ pairingNeeded 真值表 / 发现响应形态过滤(异形应答 = 非本服务)
- test_background_discovery_flow: 真跑 background.js 发现流程 —— 三候选并行探测(命中次位, V11)/ 配对码随
  X-Hr-Pairing 上来 / 合并落盘 + 清 pairingNeeded / 401 pairing_required 置标记(选项页提示输入配对码)/
  全未命中明确报告(退手动, 不静默)
- test_normalizers_are_shared_not_duplicated 扩: discovery.js 六个函数(含 isManualEntry)同样禁止本地副本,
  两个消费方都载入它
- test_protocol_matches_backend 扩: API_DISCOVER 与缺省发现端口三处同源(后端 / discovery.js / normalize.js)
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
- test_badge_reflects_connection_state: 真跑 background.js —— 徽标四态(未配置/正常/重连中/发现失败,
  C4 边界)+ 禁用清空 + 点图标开选项页
- test_badge_text_is_ascii_only: 徽标文案禁非 ASCII 图形符(code-style: 代码禁图形符号)
- 降噪场景(_NODE_RUN_NOISE)显式 discoveryAddress 置空 —— 那条守阵钉「连接失败降噪」, 不混发现流日志
### 连接自愈轮 · S6 守阵补强(计划 26-10-15-2357 S6)
- test_merge_instances_manual_priority: 手动条目同端点**整条胜**(含 token 保留)+ 恒在前且顺序稳定(Q1/Q8/Q9)
- test_merge_instances_discovered_set_replaced: 旧发现条目**整批替换**剪除(死端点不堆积)+ **空集不替换**(C1)
- test_no_opaque_reason_leaks: 选项页无 `未知` 字面量 + 后台每个 reason 都有中文结论映射(§3.4/Q5)
- test_options_listens_instances_changes: storage.onChanged 监听 instances/instanceHealth/lastDiscovery(S3④)
- test_conn_state_judgement_matches_badge: **跨层机械比对** —— 徽标态(background.js::badgeStateOf)与顶部
  总览态(options.js::connStateOf)是同一判据的两个展示面, 切出函数体真跑同一张真值表逐输入一致 +
  四态键集(BADGE vs CONN_STATE_TEXT)同源 + 徽标图例(options.html)与 BADGE label 同源
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
  不得回潮 —— 读者会误解为本页实例表)并配四态框式色样(R4)
- test_instance_source_badge_is_manual_or_auto: 来源徽标只有「手动/自动」两值(R2, 「优先」徽标废止;
  上游 26-10-15-2357 口径演进 —— 历史测试中不存在 [优先] 徽标断言, 无需翻转, 以本守阵为准)
- test_options_swiss_wiring 扩: 元素清单随 S1 更新(helpTroubleshoot/connStateDot/Text/Meta)
  + 「自测端点连通」「载入」按钮字面量不得回潮 + 实例表真表头(状态列)
- test_badge_reflects_connection_state 更新(R4 徽标文字折中): 平时徽标文本清空(状态色外框零遮挡),
  仅「发现失败」态为红 `!` + setBadgeBackgroundColor; 旧 OK/.. 徽标文案不得回潮
- test_badge_icon_frame_mapping: 真跑 background.js::badgeIconOf —— 四态->{16,32} 图标路径映射 +
- test_extension_quota_windows_roll_over
  8 个 PNG(scripts/gen_ext_icons.py 生成物)在盘上 + manifest action.default_icon 指向基础图
  (未配置态与安装初始态共用; Chrome 无还原默认图标 API, 外框方案必须自带基础图)
"""
import json
import pathlib
import re
import shutil
import subprocess

import pytest

from auto_qb.hr.channel import API_RESULT, API_SITES, API_TASKS, TOKEN_HEADER, HrChannelError, HrResult
from auto_qb.hr.discovery import API_DISCOVER, DISCOVERY_DEFAULT_PORT

EXT_DIR = pathlib.Path(__file__).resolve().parents[1] / "extensions" / "hr-fetch-proxy"
MANIFEST = EXT_DIR / "manifest.json"
NORMALIZE_JS = EXT_DIR / "normalize.js"
DISCOVERY_JS = EXT_DIR / "discovery.js"
SITE_CAPS_JS = EXT_DIR / "site-caps.js"
BACKGROUND_JS = EXT_DIR / "background.js"
OPTIONS_JS = EXT_DIR / "options.js"
OPTIONS_HTML = EXT_DIR / "options.html"
JS_FILES = (NORMALIZE_JS, DISCOVERY_JS, SITE_CAPS_JS, BACKGROUND_JS, OPTIONS_JS)

#: 归一化的行为钉死表 —— **含用户 2026-09-24 实际踩到的两种写法**。
#: (kind, 输入, 期望输出或 None=应当报错)
#: 去端口+跨机(计划 26-10-14-1241 S4/V5)翻转的两条旧语义: 私网放行(原「非回环即抛」)、
#: https 保留(原「一律折 http」); 新增 disc 类 = normalizeDiscovery(缺端口补 18788)。
NORMALIZE_CASES = [
    ("ep", "127.0.0.1:8788", "http://127.0.0.1:8788"),
    ("ep", "  http://127.0.0.1:8788/  ", "http://127.0.0.1:8788"),
    ("ep", "http://localhost:8788/", "http://127.0.0.1:8788"),
    ("ep", "https://127.0.0.1:8788", "https://127.0.0.1:8788"),
    ("ep", "127.0.0.1", None),
    ("ep", "192.168.1.9:8788", "http://192.168.1.9:8788"),
    ("ep", "10.0.0.5:8788", "http://10.0.0.5:8788"),
    ("ep", "172.16.31.5:8788", "http://172.16.31.5:8788"),
    ("ep", "pt.example.com:8788", None),
    ("ep", "http://pt.example.com:8788", None),
    ("ep", "", None),
    ("disc", "192.168.1.10", "http://192.168.1.10:18788"),
    ("disc", "http://192.168.1.10:18788/", "http://192.168.1.10:18788"),
    ("disc", "nas.local", None),
    ("og", "pt.btschool.club", "https://pt.btschool.club/*"),
    ("og", "https://pt.btschool.club/", "https://pt.btschool.club/*"),
    ("og", "pt.btschool.club/myhr.php", "https://pt.btschool.club/*"),
    ("og", "http://pt.example.com/a/b", "http://pt.example.com/*"),
    ("og", "notadomain", None),
    ("og", "", None),
]

#: 在 node 里 eval normalize.js 并跑上表(纯函数, 不引用 document/chrome ⇒ 可直接载入)
_NODE_RUN_NORMALIZERS = """
const fs = require('fs');
const src = fs.readFileSync(process.argv[1], 'utf8');
const mod = new Function(src + '\\nreturn {normalizeEndpoint, normalizeOrigin, normalizeDiscovery};')();
const out = [];
for (const [kind, input] of JSON.parse(process.argv[2])) {
  try {
    const fn = kind === 'ep' ? mod.normalizeEndpoint : kind === 'disc' ? mod.normalizeDiscovery : mod.normalizeOrigin;
    out.push({ kind, input, got: fn(input) });
  } catch (e) {
    out.push({ kind, input, err: String(e.message) });
  }
}
process.stdout.write(JSON.stringify(out));
"""


def _node() -> str:
    return shutil.which("node") or ""


def _run_node(args):
    """跑 node 并**显式按 UTF-8 解码** —— node 的输出是 UTF-8, 而 `text=True` 会按本机 locale
    (本机是 GBK)去解 ⇒ 归一化的中文报错会让读取线程直接抛 UnicodeDecodeError(实测)。
    """
    return subprocess.run(args, capture_output=True, encoding="utf-8", errors="replace")


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------- manifest ----------


def test_manifest_is_mv3_and_scoped():
    manifest = json.loads(_read(MANIFEST))
    assert manifest["manifest_version"] == 3
    assert manifest["background"]["service_worker"].endswith(".js")
    host_permissions = manifest["host_permissions"]
    assert "http://127.0.0.1/*" in host_permissions, "端点只监听回环: 没有这条 host_permission, fetch 直接被拦"
    # 站点权限走**可选**(按站点授予), 而不是一次性写进必给的 host_permissions
    optional = manifest["optional_host_permissions"]
    assert optional, "站点源应走 optional_host_permissions"
    for pattern in host_permissions + optional:
        assert pattern != "<all_urls>", "不给全站权限是设计约束"
        assert pattern.startswith(("http://", "https://")), f"匹配模式必须带 scheme: {pattern}"


def test_manifest_covers_loopback_aliases():
    """localhost / [::1] 也要在 host_permissions 里: 用户这么写时归一化会兜住, 但排查/手改时也不能被拦"""
    manifest = json.loads(_read(MANIFEST))
    host_permissions = manifest["host_permissions"]
    assert "http://localhost/*" in host_permissions
    assert "http://[::1]/*" in host_permissions


# ---------- 语法与行为 ----------


def test_js_syntax_passes_node_check():
    node = _node()
    if not node:
        return  # 与前端守阵同口径: 没装 node 就静默跳过(不引入 skip 计数)
    for path in JS_FILES:
        proc = _run_node([node, "--check", str(path)])
        assert proc.returncode == 0, f"{path.name} 语法错误: {proc.stderr.strip()}"


def test_normalizers_behave():
    """真跑 normalize.js —— 这是本次两条报错的直接守阵

    !node --check 只看语法, 看不见"LOOPBACK_HOSTS 未定义"这类运行期错(本次重构时就真出现过一次),
    所以这里必须**执行**它。
    """
    node = _node()
    if not node:
        return
    cases = [[kind, text] for kind, text, _want in NORMALIZE_CASES]
    proc = _run_node([node, "-e", _NODE_RUN_NORMALIZERS, str(NORMALIZE_JS), json.dumps(cases)])
    assert proc.returncode == 0, f"node 执行 normalize.js 失败: {proc.stderr.strip()}"
    got = json.loads(proc.stdout)
    assert len(got) == len(NORMALIZE_CASES)
    for case, result in zip(NORMALIZE_CASES, got):
        kind, text, want = case
        label = f"{kind}({text!r})"
        if want is None:
            assert "err" in result, f"{label} 应当报错(给不出可操作提示就是错的), 实际得到 {result.get('got')}"
            assert result["err"], f"{label} 的错误消息不能为空(要能直接给用户看)"
        else:
            assert result.get("got") == want, f"{label} 应归一化为 {want}, 实际 {result}"


def test_normalizers_are_shared_not_duplicated():
    """归一化与发现协议函数只能有一份 —— 两份分头演化的症状是「配了不生效」; 选项页与后台都载入同一份"""
    for path in (BACKGROUND_JS, OPTIONS_JS):
        text = _read(path)
        for fn in (
            "normalizeEndpoint", "normalizeOrigin", "normalizeDiscovery", "mergeInstances", "isManualEntry",
            "discoveryCandidates"
        ):
            assert not re.search(rf"(?m)^function {fn}", text), f"{path.name} 又定义了 {fn} 本地副本"
    assert "importScripts('normalize.js')" in _read(BACKGROUND_JS)
    assert "importScripts('discovery.js')" in _read(BACKGROUND_JS), "后台要载入发现协议单点(discovery.js)"
    html = _read(OPTIONS_HTML)
    assert html.index("normalize.js") < html.index("discovery.js") < html.index("options.js"), "载入顺序: 归一化/发现在选项页脚本之前"


def test_site_caps_are_shared_single_source():
    """硬上限只有一份(site-caps.js): 后台用 importScripts、选项页用 <script> —— 都不许写死阈值

    两份分头演化的后果很具体: 选项页显示的数字与实际生效的阈值不符, 用户据此理解行为, 结果对不上。
    """
    caps = _read(SITE_CAPS_JS)
    assert "SITE_CAPS" in caps and "perHour" in caps and "perDay" in caps
    assert "importScripts('site-caps.js')" in _read(BACKGROUND_JS)
    html = _read(OPTIONS_HTML)
    assert "site-caps.js" in html and html.index("site-caps.js") < html.index("options.js"), "载入顺序: 常量在前"
    for path in (BACKGROUND_JS, OPTIONS_JS):
        assert not re.search(r"(?m)^const SITE_CAPS", _read(path)), f"{path.name} 又定义了一份阈值"
        assert "SITE_CAPS[" in _read(path) or "Object.entries(SITE_CAPS)" in _read(path), \
            f"{path.name} 应当消耗共享阈值而不是写死数字"


# ---------- 与后端的协议 ----------


def test_protocol_matches_backend():
    """扩展与后端的线上格式钉在一处: 常量取 `hr.channel`/`hr.discovery`, 字段名取实测行为(双向守阵)"""
    background = _read(BACKGROUND_JS)
    assert API_TASKS in background and API_RESULT in background, "端点路径必须与 hr.channel 一致"
    assert "buildDiscoveryUrl(" in background and "runDiscovery(" in background, \
        "发现流程必须经 discovery.js 的单点拼 URL(路径常量只在 discovery.js 一处)"
    discovery_js = _read(DISCOVERY_JS)
    normalize_js = _read(NORMALIZE_JS)
    assert f"const API_DISCOVER = '{API_DISCOVER}'" in discovery_js, "discovery.js 的发现路径常量要与后端同源"
    assert str(DISCOVERY_DEFAULT_PORT) in discovery_js and str(DISCOVERY_DEFAULT_PORT) in normalize_js, \
        "缺省发现端口(18788)三处同源: 后端 / discovery.js / normalize.js 补端口"
    assert TOKEN_HEADER in background and TOKEN_HEADER in _read(OPTIONS_JS), "鉴权头名必须两边一致"
    # 扩展实际发出去的两条结果形态(见 background.js::runTask)必须能被后端解析
    for payload in (
        {
            "id": "t1",
            "ok": True,
            "status": 200,
            "url": "https://pt.example.com/a",
            "text": "<html/>"
        },
        {
            "id": "t2",
            "ok": True,
            "status": 200,
            "url": "https://pt.example.com/b",
            "body_b64": "AAEC"
        },
        {
            "id": "t3",
            "ok": False,
            "url": "https://pt.example.com/c",
            "error": "HTTP 403"
        },
    ):
        parsed = HrResult.from_json(payload)
        assert parsed.task_id == payload["id"] and parsed.ok == payload["ok"]
    # 清单与批量信封的键名, 以及"任务 id 由后端给、扩展只回显"这条不变量
    assert "data.tasks" in background and "results" in background
    assert "id: task.id" in background, "回传的 id 必须回显后端下发的 task.id(扩展不得自己编号)"
    with pytest.raises(HrChannelError):
        HrResult.from_json({"ok": True, "text": "缺 id"})


# ---------- 选项页的输入处理 ----------


def test_options_normalizes_before_browser_api():
    """本次报错的形态: 原始输入直接进浏览器 API —— 钉住"先归一化、再落盘/授权"

    判据不是"文件里出现过 normalizeXxx", 而是**调用顺序**: 归一化必须在权限/存储 API 之前。
    """
    text = _read(OPTIONS_JS)
    assert "chrome.permissions.request" in text, "用例本身要跟着实现走: 授权入口改名就一起改"
    start = text.index("async function grant()")
    nxt = text.find("\nasync function ", start + 1)
    grant_body = text[start:nxt if nxt > 0 else len(text)]
    assert grant_body.index("parseOrigins()") < grant_body.index("chrome.permissions.request"), \
        "站点源必须先归一化再交给 chrome.permissions.request(裸域名会被它拒且是未捕获拒绝)"
    assert "$('origins').value" not in grant_body, "绝不把原始文本直接喂给权限 API"
    # 非法输入不拖垮整批: 好的照收、坏的逐条报(否则用户改好一条还得再猜其它条)
    assert "bad.push(" in text and "被跳过" in text


def test_options_rejections_are_always_handled():
    """选项页不得留下裸 Promise 拒绝(用户只会看到一行英文红字, 完全无从下手)"""
    text = _read(OPTIONS_JS)
    assert "unhandledrejection" in text, "要有兜底: 漏网的拒绝也得落到状态栏"
    assert text.count(".catch(") >= 5, "四个按钮 + 初始 load 都要 catch"
    assert "try {" in text, "授权/自测这类浏览器 API 调用必须包 try(它们会同步抛)"


def test_options_site_fetch_matches_backend():
    """站点授权清单走 GET /api/hr/sites: 路径与鉴权头必须与 hr.channel 同源(改一边漏改另一边必红)"""
    js = _read(OPTIONS_JS)
    assert f'const API_SITES = "{API_SITES}"' in js, "选项页的站点清单路径常量要与后端 hr.channel.API_SITES 一致"
    assert "X-Hr-Token" in js, "拉站点清单要带与拉任务同款的鉴权头"


def test_options_swiss_wiring():
    """瑞士网格终态(风格选型 A)的接线: 两表 + 表单授权 + 折叠排障区齐全, 容器在脚本之前

    2026-09-26 用户澄清「三模板」是三套独立风格选一套实施(非共存)—— 选定 A 后本条守阵随之改钉
    单一风格终态, 并钉住「共存实现不回潮」(三档切换机制不得再出现)。
    2026-10-16 计划 26-10-15-2357 S4 把「连接端点 + 手动端点 + 底部工具栏」合并为**一个「① 连接
    后端」区**并删掉「保存发现地址与配对码」按钮(隐式保存)—— 被删的 id/落点随口径更新, 属口径
    演进非守阵松动; 新布局的判据(总览行/折叠手动区/徽标图例)在此一并钉住。
    2026-10-16 计划 26-10-16-0214 S1 再重排: 状态卡(connStateDot/Text/Meta)+ 实例表真表头 +
    「说明与排障」折叠(helpTroubleshoot 收编三段长文); 「自测端点连通」更名「重测全部」(id test
    保留), 「载入」与行内「测」随 R3 删除 —— 元素清单随之更新, 旧字面量反向断言钉死。
    """
    html = _read(OPTIONS_HTML)
    js = _read(OPTIONS_JS)
    for el in (
        "siteTable",
        "eventTable",
        "siteChecks",
        "fetchSites",
        "selectAllSites",
        "grantChecked",
        "instList",
        "addInstance",
        "newInstance",
        "manualOrigins",
        "origins",
        "instances",
        "advLogs",
        "logView",
        "logMax",
        "logLevel",
        "logFilter",
        "caps",
        "status",
        "enabled",
        "discEndpoint",
        "discPairing",
        "discNow",
        "discStatus",
        "connState",
        "manualEndpoints",
        "badgeLegend",
        "test",
        "poll",
        "hint",
        "save",
        "instEndpoint",
        "instToken",
        # S1 新落点: 状态卡三段 + 说明与排障折叠
        "connStateDot",
        "connStateText",
        "connStateMeta",
        "helpTroubleshoot",
    ):
        assert el in html, f"选项页缺 {el}"
    assert "discSave" not in html, "S4 已删「保存发现地址与配对码」按钮(发现隐式保存), 别让它回潮"
    # R3 删除的操作入口 + 更名前的按钮字面量, 均不得回潮(用户可见串)
    assert "自测端点连通" not in html, "按钮已更名「重测全部」, 旧字面量不得回潮"
    assert ">载入<" not in html and 'id="load"' not in html, "「载入」按钮已随 R3 删除(改 token = 删除重加)"
    for el in ("siteTable", "eventTable", "advLogs", "logView", "origins", "instances"):
        assert html.index(el) < html.index("options.js"), f"{el} 容器要在脚本之前"
    # 实例表是真表头(来源/端点/token/状态/最近联系/操作): 状态列是「实例状态入表」的落点
    inst_thead = html[html.index('<th>来源</th>'):html.index('</thead>')]
    for col in ("来源", "端点", "token", "状态", "最近联系", "操作"):
        assert col in inst_thead, f"实例表头缺「{col}」列"
    assert "重测全部" in html and 'id="test"' in html, "动作行按钮 id test 保留, 文案为「重测全部」"
    for el in (
        "refreshTables",
        "renderSiteStatus",
        "renderEvents",
        "scheduleTablesRender",
        "fetchSites",
        "grantChecked",
        "API_SITES",
        "SITE_CAPS",
        "discoverNow",
        "DEFAULT_DISCOVERY_ADDRESS",
        # S3 落点: 顶部总览 + 隐式保存的授权序 + 自动接自测 + 失败码中文映射 + 实时刷新
        "renderConnOverview",
        "connStateOf",
        "DISCOVERY_REASON_TEXT",
        "candidateSummary",
        "probeMainInstance",
        "scheduleConnRender",
        "isManualEntry"
    ):
        assert el in js, f"options.js 缺 {el} 的落点(按钮点了没反应)"
    # 单一风格定案: 三档共存的机制(uiTemplate/模板切换)不得回潮
    assert "uiTemplate" not in js and "tplSimple" not in html and "tplStandard" not in html, \
        "风格已选定 A(瑞士网格), 三档共存机制不该再回来"
    # 两表数据源是后台双写的结构化事件环, 不是解析日志文案
    assert "events" in js and "siteLedger" in js


def _balanced_block(text: str, start: int) -> str:
    """从 start(须指向 '{')起取到配平的 '}' —— 切出 JS 回调/函数体(本文件的块内无含花括号的字符串)"""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise AssertionError("花括号不配平")


def _js_object_block(text: str, decl: str) -> str:
    """切出 `const X = { ... };` 的块体(首个 `};` 收尾)"""
    start = text.index(decl)
    return text[start:text.index("};", start)]


def _js_object_keys(block: str) -> list:
    """取对象字面量的顶层键名(保序; 键可带引号, 如 'no-hit')"""
    return re.findall(r"(?m)^\s*'?([A-Za-z_][\w-]*)'?\s*:", block)


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
    reasons = sorted(set(re.findall(r"reason: '([^']+)'", _read(BACKGROUND_JS))))
    assert reasons, "后台应能给出失败码(改用别的键名时这条一起改)"
    for reason in reasons:
        assert reason in mapped, f"后台会报 reason={reason}, 选项页却没有中文映射(会原样外泄给用户)"
    for value in re.findall(r":\s*'([^']*)'", block):
        assert re.search(r"[\u4e00-\u9fff]", value), f"映射值必须是中文结论(不是把码抄一遍): {value!r}"


def test_options_listens_instances_changes():
    """连接面实时刷新(计划 §S3-④): storage.onChanged 必须监听 instances / instanceHealth / lastDiscovery

    此前只监听 logs/events/siteLedger, 后台发现并入的实例要**重开页面**才看得见 —— 这正是用户实报
    「操作逻辑混乱」的一半: 点了发现, 页面上的实例列表纹丝不动。监听面必须覆盖连接面并触发重渲染。
    """
    js = _read(OPTIONS_JS)
    i = js.index("chrome.storage.onChanged.addListener(")
    body = _balanced_block(js, js.index("{", i))
    for key in ("instances", "instanceHealth", "lastDiscovery"):
        # !词边界: `changes.instancesX` 里也含 `changes.instances` 子串, 不加边界会漏判(红验实测)
        assert re.search(rf"\bchanges\.{key}\b", body), \
            f"storage.onChanged 回调没监听 {key}(后台改了页面不知道, 要重开页面才刷新)"
    assert "scheduleConnRender" in body, "连接面变更要触发重渲染(防抖), 不能只改内存不刷新"


# ---------- 页面取数: 不打扰用户(实报两轮: 先「开新标签」后「开新窗口」) ----------

#: 两个页面样本(单点定义: 注入给 node 脚本, Python 侧断言也用同一份)
#: 1. 服务端渲染的真页面(自带表格) 2. 挑战页形态(短小、无表格 ⇒ 应当升级到渲染通道)
PAGE_WITH_TABLE = '<html><body><table class="main"><tr><td>HR编号</td></tr></table></body></html>'
CHALLENGE_LIKE = '<html><head><title>Just a moment...</title></head><body>Checking your browser</body></html>'
#: 带表格的**登录页** —— 直取可能因为 SameSite 不带 cookie 而拿到它, 必须当成"要升级渲染"的信号
LOGIN_LIKE = (
    '<html><body><table><tr><td>登录</td></tr></table>'
    '<form action="takelogin.php"><input type="password" name="password"></form></body></html>'
)

#: 用**假 chrome API** 真跑 background.js, 记录每一次窗口/标签调用 —— 纯字符串断言看不见调用形态。
#: 三个场景一次跑完(省 node 启动开销): direct=直取(页面自带表格) / render=直取内容不像页面 ⇒ 离屏渲染 /
#: steal=渲染时新窗口把浏览器抬到前台(看是否把焦点还回去)。
_NODE_RUN_PAGE_FETCH = """
const fs = require('fs');
const vm = require('vm');
const noop = { addListener() {} };
const PAGE_URL = 'https://pt.example.com/myhr.php?hrtype=A';
const PAGE_WITH_TABLE = __PAGE_WITH_TABLE__;
const CHALLENGE_LIKE = __CHALLENGE_LIKE__;
const LOGIN_LIKE = __LOGIN_LIKE__;
const store = {};
let calls = [];
let stealFocus = false;
function record(name, ret) {
  return function () {
    const args = Array.prototype.slice.call(arguments);
    calls.push([name].concat(args));
    return Promise.resolve(typeof ret === 'function' ? ret.apply(null, args) : ret);
  };
}
let focusedCalls = 0;
const chrome = {
  alarms: { create: record('alarms.create'), onAlarm: noop },
  runtime: { onInstalled: noop, onStartup: noop, onMessage: noop, onSuspend: noop },
  permissions: { onAdded: noop },
  storage: {
    onChanged: noop,   // background.js 顶层注册了「设置联动 / 外部清空采纳」监听
    local: {
      get: (defaults) => {
        const out = {};
        for (const key of Object.keys(defaults || {})) out[key] = (key in store) ? store[key] : defaults[key];
        return Promise.resolve(out);
      },
      set: (obj) => { Object.assign(store, obj); return Promise.resolve(); },
    },
  },   // 真存真读: noteStatus 与硬上限台账都要跨调用可见
  windows: {
    create: record('windows.create', () => ({ id: 777, tabs: [{ id: 42 }] })),
    get: async (id) => ({ id }),
    // 焦点守卫: 取数前返回用户窗口 1; 取数后若被抢走则返回我们建的窗口 777
    getLastFocused: async () => ({ id: (stealFocus && ++focusedCalls > 1) ? 777 : 1 }),
    update: record('windows.update', () => ({})),
    remove: record('windows.remove', () => {}),
  },
  tabs: {
    create: record('tabs.create', () => ({ id: 42, windowId: 777 })),
    get: async () => ({ id: 42, status: 'complete' }),
    remove: record('tabs.remove', () => {}),
  },
  scripting: { executeScript: async () => [{ result: PAGE_WITH_TABLE }] },
};
let nextPage = PAGE_WITH_TABLE;
const sandbox = {
  chrome, importScripts: () => {}, console, setTimeout, clearTimeout, Date, Promise, JSON, URL,
  fetch: async () => ({ ok: true, status: 200, text: async () => nextPage, json: async () => ({}) }),
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[3], 'utf8'), sandbox);   // discovery.js(默认发现端口常量; 模拟 importScripts)
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), sandbox);   // site-caps.js(模拟 importScripts)
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox);   // background.js
async function scenario(name, page, steal) {
  calls = []; focusedCalls = 0; stealFocus = Boolean(steal); nextPage = page;
  const out = await sandbox.pageText(PAGE_URL);
  return [name, { out, calls }];
}
(async () => {
  const rows = [];
  rows.push(await scenario('direct', PAGE_WITH_TABLE, false));      // 直取: 页面自带表格
  rows.push(await scenario('render', CHALLENGE_LIKE, false));       // 直取内容不像页面 ⇒ 离屏渲染
  rows.push(await scenario('login', LOGIN_LIKE, false));            // 直取拿到登录页 ⇒ 也得升级渲染
  rows.push(await scenario('steal', CHALLENGE_LIKE, true));         // 同上, 且新窗口抢了焦点
  process.stdout.write(JSON.stringify(Object.fromEntries(rows)));
})();
"""

_PAGE_FETCH_TRACE: dict = {}


def page_fetch_trace() -> dict:
    """跑一次 node 拿三个场景的调用轨迹(缓存: 三个用例共用同一次 node 运行)"""
    if _PAGE_FETCH_TRACE:
        return _PAGE_FETCH_TRACE
    node = _node()
    if not node:
        return {}
    proc = _run_node(
        [
            node,
            "-e",
            _NODE_RUN_PAGE_FETCH.replace("__PAGE_WITH_TABLE__", json.dumps(PAGE_WITH_TABLE)).replace(
                "__CHALLENGE_LIKE__", json.dumps(CHALLENGE_LIKE)
            ).replace("__LOGIN_LIKE__", json.dumps(LOGIN_LIKE)),
            str(BACKGROUND_JS),
            str(DISCOVERY_JS),
            str(SITE_CAPS_JS),
        ]
    )
    assert proc.returncode == 0, f"node 跑 background.js 失败: {proc.stderr.strip()}"
    _PAGE_FETCH_TRACE.update(json.loads(proc.stdout))
    return _PAGE_FETCH_TRACE


def _calls(trace: dict, name: str) -> list:
    return [c[0] for c in trace["calls"] if c[0] == name]


def _first(trace: dict, name: str):
    for call in trace["calls"]:
        if call[0] == name:
            return call
    return None


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


# ---------- 扩展侧硬上限(第二道闸: 后端出错时的兜底, 2026-09-25 用户指定) ----------

#: 用**真** storage(内存)真跑 background.js: 台账必须真存真读, 否则「计数」是自欺欺人。
#: 四个场景一次跑完: 1.页面上限(第 cap+1 次被拒且**不发请求**) 2.下载有独立额度(页面用满照样能下)
#: 3.窗口键过期 ⇒ 计数归零 4.日上限 ⇒ 拒发且 retry_after 指向次日。
#: !阈值一律从 site-caps.js 现值动态取(SITE_CAPS), 场景与断言**不许硬编码魔法数字** ——
#: 09d4109(配额双桶)把 10/50 提到 60/600·50/200 时, 硬编码守阵红了一天没人看见(本机无 node 静默跳过)。
_NODE_RUN_QUOTA = """
const fs = require('fs');
const vm = require('vm');
const noop = { addListener() {} };
const PAGE_URL = 'https://pt.example.com/myhr.php?hrtype=A';
const DL_URL = 'https://pt.example.com/download.php?id=313852';
const PAGE = __PAGE_WITH_TABLE__;
const store = {};
let fetches = 0;
function getWithDefaults(defaults) {
  const out = {};
  for (const key of Object.keys(defaults || {})) out[key] = (key in store) ? store[key] : defaults[key];
  return Promise.resolve(out);
}
const chrome = {
  alarms: { create() {}, onAlarm: noop },
  runtime: { onInstalled: noop, onStartup: noop, onMessage: noop },
  permissions: { onAdded: noop },
  storage: { onChanged: noop, local: {   // onChanged: background.js 顶层注册了「设置联动 / 外部清空采纳」监听
    get: (defaults) => getWithDefaults(defaults),
    set: (obj) => { Object.assign(store, obj); return Promise.resolve(); },
  } },
  windows: {
    create: async () => ({ id: 1, tabs: [{ id: 1 }] }),
    getLastFocused: async () => ({ id: 1 }),
    update: async () => ({}),
    remove: async () => {},
  },
  tabs: { create: async () => ({ id: 1 }), get: async () => ({ status: 'complete' }), remove: async () => {} },
  scripting: { executeScript: async () => [{ result: PAGE }] },
};
const sandbox = {
  chrome, importScripts: () => {}, console, setTimeout, clearTimeout, Date, Promise, JSON, URL, btoa,
  TextDecoder, TextEncoder,   // fetchBinary 解析响应头/首字节要用(真实 SW 里有, 桩必须同形)
  fetch: async () => {
    fetches += 1;
    return { ok: true, status: 200,
             headers: { get: () => 'application/octet-stream' },   // 与真实 Response 同形(fetchBinary 读 content-type)
             text: async () => PAGE, arrayBuffer: async () => new ArrayBuffer(8),
             json: async () => ({}) };
  },
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[3], 'utf8'), sandbox);   // discovery.js(默认发现端口常量; 模拟 importScripts)
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), sandbox);   // site-caps.js(模拟 importScripts)
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox);   // background.js
const LEDGER = vm.runInContext('SITE_LEDGER_KEY', sandbox);
const CAPS = JSON.parse(vm.runInContext('JSON.stringify(SITE_CAPS)', sandbox));   // 阈值动态取: 不硬编码(漂移教训)
const HOST = 'pt.example.com';
const page = (id) => sandbox.runTask({ id: id, kind: 'page', url: PAGE_URL }).then((r) => r.payload);
const torrent = (id) => sandbox.runTask({ id: id, kind: 'torrent', url: DL_URL }).then((r) => r.payload);
(async () => {
  const out = { pages: [], torrent: null, afterRollover: null, dayRefusal: null, ledgerKey: LEDGER };
  for (let i = 1; i <= CAPS.page.perHour + 1; i += 1) out.pages.push(await page('p' + i));
  out.pageHourCap = CAPS.page.perHour;
  out.fetchesAfterPages = fetches;
  out.torrent = await torrent('t1');            // 下载与访问分开计数: 页面用满不影响它
  out.fetchesAfterTorrent = fetches;
  const led = store[LEDGER] || {};
  led[HOST].page.hk = '1970-01-01T00';          // 造「小时窗口已经翻篇」
  store[LEDGER] = led;
  out.afterRollover = await page('p12');        // 计数归零 ⇒ 又能取
  const led2 = store[LEDGER] || {};
  led2[HOST].page = {
    hk: vm.runInContext('hourKey(Date.now())', sandbox),
    dk: vm.runInContext('dayKey(Date.now())', sandbox),
    hour: 1,
    day: CAPS.page.perDay,                      // 日上限已到
  };
  out.pageDayCap = CAPS.page.perDay;
  store[LEDGER] = led2;
  out.dayRefusal = await page('p13');
  out.fetchesAtEnd = fetches;
  out.ledger = store[LEDGER];
  process.stdout.write(JSON.stringify(out));
})();
"""

_QUOTA_TRACE: dict = {}


def quota_trace() -> dict:
    """跑一次 node 拿四个场景的结果(缓存: 两个用例共用同一次 node 运行)"""
    if _QUOTA_TRACE:
        return _QUOTA_TRACE
    node = _node()
    if not node:
        return {}
    proc = _run_node(
        [
            node, "-e",
            _NODE_RUN_QUOTA.replace("__PAGE_WITH_TABLE__", json.dumps(PAGE_WITH_TABLE)),
            str(BACKGROUND_JS),
            str(DISCOVERY_JS),
            str(SITE_CAPS_JS)
        ]
    )
    assert proc.returncode == 0, f"node 跑 background.js 的配额场景失败: {proc.stderr.strip()}"
    _QUOTA_TRACE.update(json.loads(proc.stdout))
    return _QUOTA_TRACE


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


#: download.php 返回 HTML(登录页)的场景: fetchBinary 必须识别并标 kind=login-page,
#: 让后端按「HR 登录失效」处置(不计取数失败), 而不是回传 HTML 让 infohash 解析烧重试额度。
_NODE_RUN_LOGIN_PAGE = """
const fs = require('fs');
const vm = require('vm');
const noop = { addListener() {} };
const DL_URL = 'https://pt.example.com/download.php?id=313852';
const LOGIN_HTML = '<!doctype html><html><body><form action="takelogin.php">' +
  '<input type="password" name="password"></form></body></html>';
const store = {};
function getWithDefaults(defaults) {
  const out = {};
  for (const key of Object.keys(defaults || {})) out[key] = (key in store) ? store[key] : defaults[key];
  return Promise.resolve(out);
}
const chrome = {
  alarms: { create() {}, onAlarm: noop },
  runtime: { onInstalled: noop, onStartup: noop, onMessage: noop },
  permissions: { onAdded: noop },
  storage: { onChanged: noop, local: {   // onChanged: background.js 顶层注册了「设置联动 / 外部清空采纳」监听
    get: (defaults) => getWithDefaults(defaults),
    set: (obj) => { Object.assign(store, obj); return Promise.resolve(); },
  } },
};
const sandbox = {
  chrome, importScripts: () => {}, console, setTimeout, clearTimeout, Date, Promise, JSON, URL, btoa,
  TextDecoder, TextEncoder,
  fetch: async () => {
    const bytes = new TextEncoder().encode(LOGIN_HTML);
    return { ok: true, status: 200, headers: { get: () => 'text/html; charset=utf-8' },
             text: async () => LOGIN_HTML, arrayBuffer: async () => bytes.buffer, json: async () => ({}) };
  },
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[3], 'utf8'), sandbox);   // discovery.js(默认发现端口常量; 模拟 importScripts)
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), sandbox);   // site-caps.js(模拟 importScripts)
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox);   // background.js
(async () => {
  const r = await sandbox.runTask({ id: 't1', kind: 'torrent', url: DL_URL });
  process.stdout.write(JSON.stringify({ payload: r.payload }));
})();
"""


def test_extension_torrent_login_page_detected():
    """download.php 返回 HTML ⇒ 回传 kind=login-page(后端按「登录失效」处置, 不计取数失败)"""
    node = _node()
    if not node:
        return  # 没装 node: 与其它前端守阵同口径静默跳过
    proc = _run_node([node, "-e", _NODE_RUN_LOGIN_PAGE, str(BACKGROUND_JS), str(DISCOVERY_JS), str(SITE_CAPS_JS)])
    assert proc.returncode == 0, f"node 跑 background.js 的登录页场景失败: {proc.stderr.strip()}"
    payload = json.loads(proc.stdout)["payload"]
    assert payload.get("ok") is False
    assert payload.get("kind") == "login-page", f"必须标成登录页让后端免计失败: {payload}"
    assert "登录" in payload.get("error", ""), payload.get("error")


#: 事件环(选项页两表的数据源)守阵: 真跑 background.js 走六类场景 —— 页面成功×2 / HTTP 失败 /
#: .torrent 成功 / .torrent 登录页 / 配额让位 —— 断言每类都双写出结构化事件且字段齐全。
_NODE_RUN_EVENTS = """
const fs = require('fs');
const vm = require('vm');
const noop = { addListener() {} };
const PAGE_URL = 'https://pt.example.com/myhr.php?hrtype=A';
const DL_URL = 'https://pt.example.com/download.php?id=313852';
const PAGE_WITH_TABLE = '<html><body><table class="main"><tr><td>HR</td></tr></table></body></html>';
const LOGIN_HTML = '<!doctype html><html><body><form><input type="password"></form></body></html>';
const BIN = new Uint8Array(2048).fill(65);
let mode = 'page-ok';
const store = {};
const chrome = {
  alarms: { create() {}, onAlarm: noop },
  runtime: { onInstalled: noop, onStartup: noop, onMessage: noop },
  permissions: { onAdded: noop },
  storage: { onChanged: noop, local: {   // onChanged: background.js 顶层注册了「设置联动 / 外部清空采纳」监听
    get: (defaults) => {
      const out = {};
      for (const key of Object.keys(defaults || {})) out[key] = (key in store) ? store[key] : defaults[key];
      return Promise.resolve(out);
    },
    set: (obj) => { Object.assign(store, obj); return Promise.resolve(); },
  } },
};
const sandbox = {
  chrome, importScripts: () => {}, console, setTimeout, clearTimeout, Date, Promise, JSON, URL, btoa,
  TextDecoder, TextEncoder,
  fetch: async () => {
    if (mode === 'http-403') return { ok: false, status: 403 };
    if (mode === 'torrent-ok') {
      return { ok: true, status: 200, headers: { get: () => 'application/x-bittorrent' }, arrayBuffer: async () => BIN.buffer };
    }
    if (mode === 'torrent-login') {
      const bytes = new TextEncoder().encode(LOGIN_HTML);
      return { ok: true, status: 200, headers: { get: () => 'text/html' }, arrayBuffer: async () => bytes.buffer };
    }
    return { ok: true, status: 200, text: async () => PAGE_WITH_TABLE, json: async () => ({}) };
  },
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[3], 'utf8'), sandbox);   // discovery.js(默认发现端口常量; 模拟 importScripts)
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), sandbox);   // site-caps.js(模拟 importScripts)
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox);   // background.js
(async () => {
  await sandbox.runTask({ id: 'p1', kind: 'page', url: PAGE_URL });    // ok(计 1 次访问)
  await sandbox.runTask({ id: 'p2', kind: 'page', url: PAGE_URL });    // ok(计 2)
  mode = 'http-403';
  await sandbox.runTask({ id: 'p3', kind: 'page', url: PAGE_URL });    // error(计 3)
  mode = 'torrent-ok';
  await sandbox.runTask({ id: 't1', kind: 'torrent', url: DL_URL });   // ok(下种计数独立)
  mode = 'torrent-login';
  await sandbox.runTask({ id: 't2', kind: 'torrent', url: DL_URL });   // login
  mode = 'page-ok';
  const CAPS = JSON.parse(vm.runInContext('JSON.stringify(SITE_CAPS)', sandbox));  // 阈值动态取: 不硬编码(漂移教训)
  for (let i = 0; i < CAPS.page.perHour - 3; i += 1) await sandbox.requireAllowance('page', PAGE_URL);  // 计满本时访问额度(3+fill=cap)
  const quota = await sandbox.runTask({ id: 'p4', kind: 'page', url: PAGE_URL }); // 超限那次 → quota
  await sandbox.flushEvents();
  process.stdout.write(JSON.stringify({ quotaPayload: quota.payload, events: store.events || [] }));
})();
"""


def test_background_events_ring_dual_write():
    """选项页两张表的数据源: 后台与日志**同源双写**结构化事件环 —— 成功/失败/让位/登录页都进表

    解析日志文案做表太脆, 故钉字段级契约: tag 分类(ok/quota/login/error) + host/kind/ms/bytes。
    """
    node = _node()
    if not node:
        return  # 没装 node: 与其它前端守阵同口径静默跳过
    proc = _run_node([node, "-e", _NODE_RUN_EVENTS, str(BACKGROUND_JS), str(DISCOVERY_JS), str(SITE_CAPS_JS)])
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


# ---------- 运行日志(分级 + 环形上限 + 落 storage) ----------

#: 真跑 background.js 的日志场景: 1.默认记录级别 info ⇒ debug 直接丢, 且条目字段齐全、超长字段截断
#: 2.环形上限 10 ⇒ 灌 25 条只留最新 10 条 3.记录级别实时生效(debug 收得进 / error 起滤掉 info)
#: 4.clearLogs 清空后 storage 里是空数组。
_NODE_RUN_LOGGER = """
const fs = require('fs');
const vm = require('vm');
const noop = { addListener() {} };
const store = {};
const chrome = {
  alarms: { create() {}, onAlarm: noop },
  runtime: { onInstalled: noop, onStartup: noop, onMessage: noop },
  permissions: { onAdded: noop },
  storage: { onChanged: noop, local: {   // onChanged: background.js 顶层注册了「设置联动 / 外部清空采纳」监听
    get: (defaults) => {
      const out = {};
      for (const key of Object.keys(defaults || {})) out[key] = (key in store) ? store[key] : defaults[key];
      return Promise.resolve(out);
    },
    set: (obj) => { Object.assign(store, obj); return Promise.resolve(); },
  } },
};
const sandbox = { chrome, importScripts: () => {}, console, setTimeout, clearTimeout, Date, Promise, JSON };
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[3], 'utf8'), sandbox);   // discovery.js(默认发现端口常量; 模拟 importScripts)
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), sandbox);   // site-caps.js(模拟 importScripts)
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox);   // background.js
(async () => {
  const out = {};
  await sandbox.log('debug', '任务', 'debug 行(应被丢)');
  await sandbox.log('info', '命令', '收到命令', { 站点: 'pt.example.com', url: 'https://pt.example.com/x', 耗时: '12ms' });
  await sandbox.log('warn', '配额', 'warn 行');
  await sandbox.log('error', '任务', 'error 行', { url: 'ab'.repeat(1000) });
  await sandbox.flushLogs();
  out.byLevel = (store.logs || []).map((e) => e.lvl);
  out.fields = (store.logs || [])[0];
  const longEntry = (store.logs || []).find((e) => e.lvl === 'error');
  out.longLen = (longEntry.url || '').length;
  out.longMark = (longEntry.url || '').includes('…(共');
  sandbox.applyLogSettings(10, undefined);
  for (let i = 1; i <= 25; i += 1) await sandbox.log('info', '任务', '行 ' + i);
  await sandbox.flushLogs();
  out.ringLen = store.logs.length;
  out.ringFirst = store.logs[0].msg;
  out.ringLast = store.logs[store.logs.length - 1].msg;
  sandbox.applyLogSettings(undefined, 'debug');
  await sandbox.log('debug', '任务', 'debug 行(应收)');
  sandbox.applyLogSettings(undefined, 'error');
  await sandbox.log('info', '任务', 'info 行(应被丢)');
  await sandbox.flushLogs();
  out.debugKept = store.logs.some((e) => e.msg === 'debug 行(应收)');
  out.infoDropped = !store.logs.some((e) => e.msg === 'info 行(应被丢)');
  await sandbox.clearLogs();
  out.afterClear = Array.isArray(store.logs) && store.logs.length === 0;
  process.stdout.write(JSON.stringify(out));
})();
"""


def test_logger_levels_ring_truncation_and_clear():
    """运行日志: 分级(低于记录级别直接丢) / 环形上限(丢最旧) / 超长截断 / 清空 —— 真跑 background.js"""
    node = _node()
    if not node:
        return  # 没装 node: 与其它前端守阵同口径静默跳过
    proc = _run_node([node, "-e", _NODE_RUN_LOGGER, str(BACKGROUND_JS), str(DISCOVERY_JS), str(SITE_CAPS_JS)])
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


#: 连不上时的降噪场景(2026-09-28 用户实报: 后端不在跑时每轮一条全量排查清单 ERROR + 状态栏同文,
#: 日志环被复读机灌满)。真跑 background.js 的 pollAll 五步: 1.首报全量 2.连败降 debug 3.第 30 轮重提
#: 4.恢复补 INFO 并清计数 5.恢复后再挂重新首报。记录级别预置 debug —— 连败期的 debug 短句要看得见;
#: normalize.js 也要真载入(safeEndpoint 要用 normalizeEndpoint)。
_NODE_RUN_NOISE = """
const fs = require('fs');
const vm = require('vm');
const noop = { addListener() {} };
const EP = 'http://127.0.0.1:18788';
const TASKS_URL = EP + '/api/hr/tasks';
// discoveryAddress 置空 = 显式关闭发现: 本用例钉的是「连接失败降噪」, 不让发现流的日志混进计数
const store = { enabled: true, logLevel: 'debug', discoveryAddress: '', instances: [{ name: '本机', endpoint: EP, token: 't' }] };
let down = true;
const chrome = {
  alarms: { create() {}, onAlarm: noop },
  runtime: { onInstalled: noop, onStartup: noop, onMessage: noop },
  permissions: { onAdded: noop },
  storage: { onChanged: noop, local: {   // onChanged: background.js 顶层注册了「设置联动 / 外部清空采纳」监听
    get: (defaults) => {
      const out = {};
      for (const key of Object.keys(defaults || {})) out[key] = (key in store) ? store[key] : defaults[key];
      return Promise.resolve(out);
    },
    set: (obj) => { Object.assign(store, obj); return Promise.resolve(); },
  } },
};
const sandbox = { chrome, importScripts: () => {}, console, setTimeout, clearTimeout, Date, Promise, JSON, URL,
  fetch: async () => {
    if (down) throw new TypeError('Failed to fetch');
    return { ok: true, status: 200, text: async () => '', json: async () => ({ tasks: [] }) };
  } };
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), sandbox);   // normalize.js(safeEndpoint 要用)
vm.runInContext(fs.readFileSync(process.argv[3], 'utf8'), sandbox);   // discovery.js(与 importScripts 同序)
vm.runInContext(fs.readFileSync(process.argv[4], 'utf8'), sandbox);   // site-caps.js(模拟 importScripts)
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox);   // background.js
const delta = async (fn) => {   // 只取本轮新增的日志行(级别|类别|文案)
  const before = (store.logs || []).length;
  await fn();
  return (store.logs || []).slice(before).map((e) => e.lvl + '|' + e.cat + '|' + e.msg);
};
(async () => {
  const out = {};
  out.r1 = await delta(() => sandbox.pollAll('定时'));            // 第 1 轮: 首报全量
  out.r2 = await delta(() => sandbox.pollAll('定时'));            // 第 2 轮: 连败降噪
  out.r3 = await delta(() => sandbox.pollAll('定时'));            // 第 3 轮: 同上
  out.streak = JSON.parse(JSON.stringify(store.netFailStreak || {}));   // 深拷贝快照: 活引用会被后续轮次原地变异
  store.netFailStreak = { [TASKS_URL]: { n: 29 } };                     // 造「已连败 29 轮」
  out.r30 = await delta(() => sandbox.pollAll('定时'));                  // 第 30 轮: 重提全量
  down = false;
  out.rOk = await delta(() => sandbox.pollAll('定时'));                  // 恢复: 补一句 INFO + 清计数
  out.streakAfterOk = JSON.parse(JSON.stringify(store.netFailStreak || {}));
  down = true;
  out.rAgain = await delta(() => sandbox.pollAll('定时'));        // 恢复后再挂: 重新首报
  process.stdout.write(JSON.stringify(out));
})();
"""


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
         str(BACKGROUND_JS),
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


# ---------- 去端口+跨机(计划 26-10-14-1241 S4): discovery.js 纯函数 + 后台发现流程 ----------

#: 真跑 discovery.js —— 候选推导 / 合并语义 / 配对判定 / 形态过滤(纯函数, node 直接 eval)。
_NODE_RUN_DISCOVERY_HELPERS = """
const fs = require('fs');
const src = fs.readFileSync(process.argv[1], 'utf8');
const mod = new Function(src + '\\nreturn {API_DISCOVER, DISCOVERY_DEFAULT_PORT, discoveryCandidates, buildDiscoveryUrl, pairingNeeded, mergeInstances, isManualEntry, validDiscoveryPayload};')();
const out = {};
out.apiDiscover = mod.API_DISCOVER;
out.defaultPort = mod.DISCOVERY_DEFAULT_PORT;
out.cands = mod.discoveryCandidates('http://192.168.1.10:18788');
out.candsCap = mod.discoveryCandidates('http://192.168.1.10:65534');
out.candsBad = mod.discoveryCandidates('not-a-url');
out.url = mod.buildDiscoveryUrl('http://192.168.1.10:18788/');
out.pairYes = mod.pairingNeeded({ status: 401, error: 'pairing_required' });
out.pairNoStatus = mod.pairingNeeded({ status: 403, error: 'pairing_required' });
out.pairNoError = mod.pairingNeeded({ status: 401, error: 'unauthorized' });
out.merged = mod.mergeInstances(
  [
    { name: 'm', endpoint: 'http://192.168.1.10:5001', token: 'old' },
    { name: 'hand', endpoint: 'http://127.0.0.1:8788', token: 'h' },
  ],
  [
    { name: 'd1', endpoint: 'http://192.168.1.10:5001', token: 'new' },
    { name: 'd2', endpoint: 'http://192.168.1.10:5002', token: 't2' },
    { name: 'half', endpoint: 'http://192.168.1.10:5003' },
  ]
);
// 整批替换: 旧的 discovered 条目(死端点)必须被剪除, 手动条目照旧
out.replaced = mod.mergeInstances(
  [
    { name: 'hand', endpoint: 'http://127.0.0.1:8788', token: 'h' },
    { name: 'dead', endpoint: 'http://192.168.1.10:5099', token: 'x', source: 'discovered' },
  ],
  [
    { name: 'd1', endpoint: 'http://192.168.1.10:5001', token: 'new' },
    { name: 'd2', endpoint: 'http://192.168.1.10:5002', token: 't2' },
  ]
);
// 空集例外(C1): 发现返回空 ⇒ 保留旧发现集, 绝不清空
out.emptyKept = mod.mergeInstances(
  [
    { name: 'hand', endpoint: 'http://127.0.0.1:8788', token: 'h' },
    { name: 'stale', endpoint: 'http://192.168.1.10:5099', token: 'x', source: 'discovered' },
  ],
  []
);
out.manualFlags = [
  mod.isManualEntry({ endpoint: 'http://a:1' }),
  mod.isManualEntry({ endpoint: 'http://a:1', source: 'discovered' }),
  mod.isManualEntry(null),
];
out.validOk = mod.validDiscoveryPayload({ instances: [{ endpoint: 'http://x:1', token: 't' }] });
out.validNoArray = mod.validDiscoveryPayload({});
out.validHalf = mod.validDiscoveryPayload({ instances: [{ endpoint: 'http://x:1' }] });
process.stdout.write(JSON.stringify(out));
"""

_DISCOVERY_HELPERS_TRACE: dict = {}


def discovery_helpers_trace() -> dict:
    """跑一次 node 拿 discovery.js 纯函数的全部断言点(缓存: 合并语义的多条用例共用同一次 node 运行)"""
    if _DISCOVERY_HELPERS_TRACE:
        return _DISCOVERY_HELPERS_TRACE
    node = _node()
    if not node:
        return {}
    proc = _run_node([node, "-e", _NODE_RUN_DISCOVERY_HELPERS, str(DISCOVERY_JS)])
    assert proc.returncode == 0, f"node 执行 discovery.js 失败: {proc.stderr.strip()}"
    _DISCOVERY_HELPERS_TRACE.update(json.loads(proc.stdout))
    return _DISCOVERY_HELPERS_TRACE


def test_discovery_helpers_behave():
    """真跑 discovery.js —— 候选推导与后端同源(65535 截断)/ 合并语义(替换同端点+保留手填+标自动)/ 配对判定 / 形态过滤"""
    got = discovery_helpers_trace()
    if not got:
        return  # 没装 node: 与其它前端守阵同口径静默跳过
    assert got["apiDiscover"] == API_DISCOVER and got["defaultPort"] == DISCOVERY_DEFAULT_PORT
    assert got["cands"] == ["http://192.168.1.10:18788", "http://192.168.1.10:18789", "http://192.168.1.10:18790"]
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


#: 真跑 background.js 的发现流程: 三候选并行探测(命中次位)/ 配对码随头上来 / 合并落盘 /
#: 401 pairing_required 置标记 / 异形应答按「非本服务」忽略 / 全未命中明确报告(退手动, 不静默)。
_NODE_RUN_DISCOVERY_FLOW = """
const fs = require('fs');
const vm = require('vm');
const noop = { addListener() {} };
const store = { enabled: true, logLevel: 'debug', discoveryAddress: 'http://192.168.1.10:18788', pairingCode: '123456' };
let mode = 'ok-second';   // 首候选被普通应用占用(404), 次候选命中
let calls = [];
const DISCOVER_BODY = { instances: [
  { id: 'a1', name: 'nas', endpoint: 'http://192.168.1.10:5001', token: 'k1' },
  { id: 'a2', name: 'nas2', endpoint: 'http://192.168.1.10:5002', token: 'k2' },
] };
const chrome = {
  alarms: { create() {}, onAlarm: noop },
  runtime: { onInstalled: noop, onStartup: noop, onMessage: noop },
  permissions: { onAdded: noop },
  storage: { onChanged: noop, local: {
    get: (defaults) => { const out = {}; for (const k of Object.keys(defaults || {})) out[k] = (k in store) ? store[k] : defaults[k]; return Promise.resolve(out); },
    set: (obj) => { Object.assign(store, obj); return Promise.resolve(); },
  } },
};
const sandbox = { chrome, importScripts: () => {}, console, setTimeout, clearTimeout, Date, Promise, JSON, URL,
  fetch: async (url, opts) => {
    calls.push([String(url), opts && opts.headers ? opts.headers['X-Hr-Pairing'] : undefined]);
    if (mode === 'down') throw new TypeError('Failed to fetch');
    if (mode === 'pairing') return { status: 401, json: async () => ({ error: 'pairing_required' }) };
    if (mode === 'weird') return { status: 200, json: async () => ({ html: '<html>not-us</html>' }) };
    if (mode === 'ok-second' && Number(new URL(url).port) === 18788) return { status: 404, json: async () => ({}) };
    return { status: 200, json: async () => DISCOVER_BODY };
  } };
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), sandbox);   // normalize.js
vm.runInContext(fs.readFileSync(process.argv[3], 'utf8'), sandbox);   // discovery.js
vm.runInContext(fs.readFileSync(process.argv[4], 'utf8'), sandbox);   // site-caps.js
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox);   // background.js
(async () => {
  const out = {};
  out.hit = await sandbox.runDiscovery('测试');
  out.hitCalls = calls.slice();
  out.instances = JSON.parse(JSON.stringify(store.instances || []));
  out.pairingCleared = store.pairingNeeded;
  calls = []; mode = 'pairing';
  store.pairingNeeded = false;
  out.pair = await sandbox.runDiscovery('测试');
  out.pairFlag = store.pairingNeeded;
  mode = 'weird';
  out.weird = await sandbox.runDiscovery('测试');
  mode = 'down';
  out.down = await sandbox.runDiscovery('测试');
  process.stdout.write(JSON.stringify(out));
})();
"""


def test_background_discovery_flow():
    """真跑 background.js 的发现流程 —— 三候选并行探测(命中次位)/ 配对码随头上来 / 合并落盘 +
    清等待标记 / 401 pairing_required 置标记 / 异形应答按「非本服务」忽略 / 全未命中明确报告(退手动)"""
    node = _node()
    if not node:
        return  # 没装 node: 与其它前端守阵同口径静默跳过
    proc = _run_node(
        [
            node, "-e", _NODE_RUN_DISCOVERY_FLOW,
            str(BACKGROUND_JS),
            str(NORMALIZE_JS),
            str(DISCOVERY_JS),
            str(SITE_CAPS_JS)
        ]
    )
    assert proc.returncode == 0, f"node 跑 background.js 的发现流程失败: {proc.stderr.strip()}"
    got = json.loads(proc.stdout)
    assert got["hit"]["ok"] is True and got["hit"]["merged"] == 2, got["hit"]
    discover_calls = [c for c in got["hitCalls"] if c[0].endswith(API_DISCOVER)]
    assert len(discover_calls) == 3, f"三个候选并行探测: {got['hitCalls']}"
    assert all(c[1] == "123456" for c in discover_calls), "配对码随 X-Hr-Pairing 上来"
    assert [e["endpoint"] for e in got["instances"]] == ["http://192.168.1.10:5001", "http://192.168.1.10:5002"]
    assert all(e["source"] == "discovered" for e in got["instances"]), "合并条目标「自动」"
    assert got["pairingCleared"] is False, "命中后清配对等待标记"
    assert got["pair"]["ok"] is False and got["pair"]["reason"] == "pairing_required" and got["pairFlag"] is True
    assert got["weird"]["ok"] is False and got["weird"]["reason"] == "no-hit", "异形应答 = 非本服务, 忽略"
    assert got["down"]["ok"] is False and got["down"]["reason"] == "no-hit", "连接失败不静默(日志 + 状态行)"


# ---------- 连接自愈轮(计划 26-10-15-2357 S2): 失败即发现 + 徽标四态 + 结构化快照 + 健康台账 ----------

#: 真跑 background.js 的**自愈**场景(六轮 pollAll + 徽标四态), 一轮一断言点:
#: 1. 1 死 1 活(旧口径「全部实例连败」不触发) ⇒ 任一失败即发现 + 落结构化快照 + 台账/徽标
#: 2. 紧接着再跑一轮 ⇒ 60s 节流: 不重复发现
#: 3. 全 401(端点有应答=连接是通的, 距上次 70s) ⇒ **不**触发发现
#: 4. 同钟位正对照: 真失败 ⇒ 发现开火(证明第 3 轮的"没开火"不是被节流挡的)
#: 5. 实例清单为空 + 距上次 130s ⇒ 仍按周期发现(R1: 否则发现集为空时连接再也回不来)
#: 6. 徽标四态纯函数取值 + 禁用清空 + 图标点击开选项页
_NODE_RUN_SELFHEAL = """
const fs = require('fs');
const vm = require('vm');
const noop = { addListener() {} };
const A = 'http://127.0.0.1:9001';   // 恒活
const B = 'http://127.0.0.1:9002';   // 可坏
const store = {
  enabled: true, logLevel: 'debug', discoveryAddress: 'http://127.0.0.1:18788',
  instances: [{ name: 'a', endpoint: A, token: 't1' }, { name: 'b', endpoint: B, token: 't2' }],
};
let bDown = true;
let b401 = false;
let fetches = [];
let badge = { text: null, color: null, title: null };
let icon = null;
let opened = 0;
let onClicked = null;
const chrome = {
  alarms: { create() {}, onAlarm: noop },
  runtime: {
    onInstalled: noop, onStartup: noop, onMessage: noop,
    openOptionsPage: () => { opened += 1; return Promise.resolve(); },
  },
  permissions: { onAdded: noop },
  action: {
    onClicked: { addListener: (fn) => { onClicked = fn; } },
    setBadgeText: (o) => { badge.text = o.text; return Promise.resolve(); },
    setBadgeBackgroundColor: (o) => { badge.color = o.color; return Promise.resolve(); },
    setTitle: (o) => { badge.title = o.title; return Promise.resolve(); },
    setIcon: (o) => { icon = o.path; return Promise.resolve(); },
  },
  storage: { onChanged: noop, local: {
    get: (defaults) => { const out = {}; for (const k of Object.keys(defaults || {})) out[k] = (k in store) ? store[k] : defaults[k]; return Promise.resolve(out); },
    set: (obj) => { Object.assign(store, obj); return Promise.resolve(); },
  } },
};
const sandbox = { chrome, importScripts: () => {}, console, setTimeout, clearTimeout, Date, Promise, JSON, URL,
  fetch: async (url) => {
    const u = String(url);
    fetches.push(u);
    if (u.endsWith('/api/hr/discover')) {
      // 首候选被普通应用占用(404), 次候选(18788)命中 —— 逐候选结果因此有内容可渲染
      if (!u.includes(':18788')) return { status: 404, json: async () => ({}) };
      return { status: 200, json: async () => ({ instances: [{ id: 'd', name: 'd', endpoint: 'http://127.0.0.1:9003', token: 'k3' }] }) };
    }
    if (u.startsWith(B) && bDown) throw new TypeError('Failed to fetch');
    if (u.startsWith(B) && b401) return { status: 401, ok: false, json: async () => ({}) };
    return { ok: true, status: 200, json: async () => ({ tasks: [] }) };
  } };
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), sandbox);   // normalize.js
vm.runInContext(fs.readFileSync(process.argv[3], 'utf8'), sandbox);   // discovery.js
vm.runInContext(fs.readFileSync(process.argv[4], 'utf8'), sandbox);   // site-caps.js
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox);   // background.js
const discovers = () => fetches.filter((u) => u.endsWith('/api/hr/discover')).length;
const snap = (v) => JSON.parse(JSON.stringify(v));
(async () => {
  const out = {};
  out.period = vm.runInContext('DISCOVERY_EVERY_MINUTES', sandbox);
  out.minGapMs = vm.runInContext('DISCOVERY_MIN_GAP_MS', sandbox);

  await sandbox.pollAll('定时');                       // 1. 1 死 1 活
  out.aDiscovers = discovers();
  out.aSnapshot = snap(store.lastDiscovery || null);
  out.aHealth = snap(store.instanceHealth || {});
  out.aBadge = snap(badge);

  await sandbox.pollAll('定时');                       // 2. 60s 节流
  out.bDiscovers = discovers();
  out.bHealth = snap(store.instanceHealth || {});

  store.lastDiscoveryAt = Date.now() - 70000;          // 3. 全 401: 有应答 ⇒ 不算失败
  bDown = false; b401 = true;
  await sandbox.pollAll('定时');
  out.cDiscovers = discovers();

  b401 = false; bDown = true;                          // 4. 同钟位正对照: 真失败 ⇒ 开火
  store.lastDiscoveryAt = Date.now() - 70000;
  await sandbox.pollAll('定时');
  out.dDiscovers = discovers();

  store.instances = [];                                // 5. 实例为空也跑周期发现(R1)
  store.lastDiscoveryAt = Date.now() - 130000;
  await sandbox.pollAll('定时');
  out.eDiscovers = discovers();
  out.eHealth = snap(store.instanceHealth || {});

  out.badgeStates = [                                  // 6. 徽标四态 + 禁用清空 + 点击
    sandbox.badgeStateOf({ instances: [], discoveryAddress: '' }),
    sandbox.badgeStateOf({
      instances: [{ endpoint: A }], discoveryAddress: 'http://127.0.0.1:18788', instanceHealth: { [A]: { ok: true } }
    }),
    sandbox.badgeStateOf({
      instances: [], discoveryAddress: 'http://127.0.0.1:18788', instanceHealth: {},
      lastDiscovery: { ok: false, answered: true }
    }),
    sandbox.badgeStateOf({
      instances: [{ endpoint: A }], discoveryAddress: 'http://127.0.0.1:18788', instanceHealth: {},
      lastDiscovery: { ok: false, answered: false }
    }),
  ];
  store.instances = [{ name: 'a', endpoint: A, token: 't1' }];
  store.instanceHealth = { [A]: { ok: true, at: Date.now(), note: 'a: 无任务', failStreak: 0 } };
  store.lastDiscovery = { ok: true, answered: true };
  await sandbox.refreshBadge();
  out.badgeOk = snap(badge);
  out.iconOk = snap(icon);
  store.enabled = false;
  await sandbox.refreshBadge();
  out.badgeDisabled = snap(badge);
  out.iconDisabled = snap(icon);
  // R4(计划 26-10-16-0214 S6): 四态图标外框 + 徽标文本仅「发现失败」态非空(平时零遮挡)
  const iconCfgs = [
    ['unconfigured', { instances: [], discoveryAddress: '' }],
    ['ok', { instances: [{ endpoint: A }], discoveryAddress: 'http://127.0.0.1:18788', instanceHealth: { [A]: { ok: true } } }],
    ['reconnecting', { instances: [{ endpoint: A }], discoveryAddress: 'http://127.0.0.1:18788', instanceHealth: {}, lastDiscovery: { ok: false, answered: true } }],
    ['discoveryFailed', { instances: [{ endpoint: A }], discoveryAddress: 'http://127.0.0.1:18788', instanceHealth: {}, lastDiscovery: { ok: false, answered: false } }],
  ];
  out.iconStates = [];
  for (const [st, cfg] of iconCfgs) {
    Object.assign(store, { enabled: true }, cfg);
    await sandbox.refreshBadge();
    out.iconStates.push({ state: st, text: badge.text, color: badge.color, icon: snap(icon), title: badge.title });
  }
  out.hasOnClicked = typeof onClicked === 'function';
  if (onClicked) await onClicked();
  out.opened = opened;
  process.stdout.write(JSON.stringify(out));
})();
"""

_SELFHEAL_TRACE: dict = {}


def selfheal_trace() -> dict:
    """跑一次 node 拿自愈场景的全部断言点(缓存: 多条用例共用同一次 node 运行)"""
    if _SELFHEAL_TRACE:
        return _SELFHEAL_TRACE
    node = _node()
    if not node:
        return {}
    proc = _run_node(
        [node, "-e", _NODE_RUN_SELFHEAL,
         str(BACKGROUND_JS),
         str(NORMALIZE_JS),
         str(DISCOVERY_JS),
         str(SITE_CAPS_JS)]
    )
    assert proc.returncode == 0, f"node 跑 background.js 的自愈场景失败: {proc.stderr.strip()}"
    _SELFHEAL_TRACE.update(json.loads(proc.stdout))
    return _SELFHEAL_TRACE


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
    assert a == 3, f"1 死 1 活(旧口径不触发)也要跑一轮发现: {a}"
    assert b == a, f"60s 内不重复发现(节流): {a} -> {b}"
    assert c == b, f"全 401 不该触发发现(端点有应答, 距上次 70s: 误判为失败就会开火): {b} -> {c}"
    assert d == c + 3, f"同钟位正对照: 真失败必须开火(否则上一轮的「没开火」说明不了什么): {c} -> {d}"
    assert e == d + 3, f"实例清单为空也要按周期发现(R1): {d} -> {e}"


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
    assert [c["url"] for c in cands] == [
        "http://127.0.0.1:18788",
        "http://127.0.0.1:18789",
        "http://127.0.0.1:18790",
    ], f"逐候选结果要按候选表顺序落(记 base 而非拼好路径的 URL: 选项页按端口报结论): {cands}"
    assert cands[0]["note"] == "" and cands[1]["note"] == "HTTP 404" and cands[2]["note"] == "HTTP 404", \
        f"每个候选都要带自己的结论(选项页据此渲染「18789 连接失败 / 18790 异形应答」这类文案): {cands}"


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
    bg = _read(BACKGROUND_JS)
    block = bg[bg.index("const BADGE = {"):bg.index("function badgeStateOf")]
    texts = re.findall(r"text: '([^']*)'", block)
    assert len(texts) == 4, f"徽标四态各有文案(改结构时这条一起改): {texts}"
    for text in texts:
        assert text.isascii(), f"徽标文案出现非 ASCII 字符 {text!r}(小字号下渲染成方框)"


# ---------- 连接区 UI 重排 + 实例状态入表(计划 26-10-16-0214 S4-S6): 行级四态 / 重测全部 / 徽标外框 ----------

#: 真跑 options.js::rowHealthOf(切出函数体, 不载入整页): 行级四态真值表 —— 数据源是后台落的
#: instanceHealth 台账条目(键=端点); 红(401/403)优先于 ok(401 在轮询口径里记 ok:true, 但表格必须
#: 标红); 旧台账无 state 字段按 C2 降级(ok->绿, 否则橙), 无迁移脚本。
_NODE_RUN_ROW_HEALTH = """
const fs = require('fs');
function grab(src, name) {
  const i = src.indexOf('function ' + name + '(');
  if (i < 0) throw new Error('未找到函数 ' + name);
  let depth = 0, seen = false;
  for (let k = i; k < src.length; k += 1) {
    const ch = src[k];
    if (ch === '{') { depth += 1; seen = true; }
    else if (ch === '}') { depth -= 1; if (seen && depth === 0) return src.slice(i, k + 1); }
  }
  throw new Error('函数体花括号不配平: ' + name);
}
const fn = new Function(grab(fs.readFileSync(process.argv[1], 'utf8'), 'rowHealthOf') + '\\nreturn rowHealthOf;')();
const cases = [
  ['null', null],
  ['empty', {}],
  ['ok', { ok: true }],
  ['ok-state-ok', { ok: true, state: 'ok' }],
  ['bad-401-oktrue', { ok: true, state: '401' }],
  ['bad-403-oktrue', { ok: true, state: '403' }],
  ['bad-401-okfalse', { ok: false, state: '401' }],
  ['bad-403-okfalse', { ok: false, state: '403' }],
  ['warn-legacy-no-state', { ok: false }],
  ['warn-down', { ok: false, state: 'down' }],
  ['warn-http', { ok: false, state: 'http' }],
  ['warn-bad-endpoint', { ok: false, state: 'bad-endpoint' }],
  ['warn-streak1', { ok: false, failStreak: 1 }],
  ['warn-streak2', { ok: false, failStreak: 2 }],
  ['warn-streak5-down', { ok: false, failStreak: 5, state: 'down' }],
];
process.stdout.write(JSON.stringify(cases.map(([k, h]) => ({ k, out: fn(h) }))));
"""


def test_row_health_of_four_states():
    """行级四态真值表(计划 §3.2/S5①): 绿=正常 / 红=401 或 403(token 或来源被拒, 红优先于 ok) /
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


#: 真跑 background.js 的 probe-all 消息: 三实例各一(200 / 连不上 / 401), 逐实例只读探测,
#: 结论经 noteInstanceHealth 落台账 —— 实例表状态列的单一数据源(C1 单一写入口)。
_NODE_RUN_PROBE_ALL = """
const fs = require('fs');
const vm = require('vm');
const noop = { addListener() {} };
const A = 'http://127.0.0.1:9001';   // 200 无任务 => ok
const B = 'http://127.0.0.1:9002';   // 连不上 => down
const C = 'http://127.0.0.1:9003';   // 401 => ok:true + state:'401'(端点有应答, 行级红判据源)
const store = {
  enabled: true, logLevel: 'info', discoveryAddress: '',
  instances: [
    { name: 'a', endpoint: A, token: 't1' },
    { name: 'b', endpoint: B, token: 't2' },
    { name: 'c', endpoint: C, token: 't3' },
  ],
};
let onMessageFn = null;
const chrome = {
  alarms: { create() {}, onAlarm: noop },
  runtime: {
    onInstalled: noop, onStartup: noop,
    onMessage: { addListener: (fn) => { onMessageFn = fn; } },
    openOptionsPage: () => Promise.resolve(),
  },
  permissions: { onAdded: noop },
  action: {
    onClicked: { addListener() {} },
    setBadgeText: () => Promise.resolve(),
    setBadgeBackgroundColor: () => Promise.resolve(),
    setTitle: () => Promise.resolve(),
    setIcon: () => Promise.resolve(),
  },
  storage: { onChanged: noop, local: {
    get: (defaults) => { const out = {}; for (const k of Object.keys(defaults || {})) out[k] = (k in store) ? store[k] : defaults[k]; return Promise.resolve(out); },
    set: (obj) => { Object.assign(store, obj); return Promise.resolve(); },
  } },
};
const sandbox = { chrome, importScripts: () => {}, console, setTimeout, clearTimeout, Date, Promise, JSON, URL,
  fetch: async (url) => {
    const u = String(url);
    if (u.startsWith(A)) return { ok: true, status: 200, json: async () => ({ tasks: [], next_poll_s: 60 }) };
    if (u.startsWith(B)) throw new TypeError('Failed to fetch');
    if (u.startsWith(C)) return { ok: false, status: 401, json: async () => ({}) };
    throw new Error('unexpected fetch: ' + u);
  } };
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), sandbox);   // normalize.js
vm.runInContext(fs.readFileSync(process.argv[3], 'utf8'), sandbox);   // discovery.js
vm.runInContext(fs.readFileSync(process.argv[4], 'utf8'), sandbox);   // site-caps.js
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox);   // background.js
(async () => {
  let resp = null;
  const sendResponse = (r) => { resp = r; };
  if (!onMessageFn) throw new Error('background.js 没注册 onMessage');
  onMessageFn({ type: 'probe-all' }, {}, sendResponse);
  for (let i = 0; i < 400 && resp === null; i += 1) await new Promise((r) => setTimeout(r, 5));
  process.stdout.write(JSON.stringify({ resp, health: store.instanceHealth || {} }));
})();
"""


def test_probe_all_message_writes_ledger():
    """probe-all(「重测全部」)真跑(计划 S2/S5②): 消息存在且处理走 noteInstanceHealth —— 三实例
    (ok / down / 401)各探一次, 结构化 state 落台账(401 记 ok:true + state='401': 端点有应答是配置态,
    行级红靠 state 而非 ok); probe-one 已随 R3 取消, 两文件都不得出现。"""
    node = _node()
    if not node:
        return
    proc = _run_node(
        [node, "-e", _NODE_RUN_PROBE_ALL,
         str(BACKGROUND_JS),
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
    bg = _read(BACKGROUND_JS)
    js = _read(OPTIONS_JS)
    # 回潮形态必是带引号的消息字面量(注释里提它不算)
    assert "'probe-one'" not in bg and "'probe-one'" not in js, "probe-one 已随 R3 取消, 不得回潮"


def _js_func_body(js: str, name: str) -> str:
    """切出 `function name(...) { ... }` 的函数体(花括号配平; 模板串里的 ${} 自带配平)"""
    i = js.index(f"function {name}(")
    start = js.index("{", i)
    depth = 0
    for k in range(start, len(js)):
        if js[k] == "{":
            depth += 1
        elif js[k] == "}":
            depth -= 1
            if depth == 0:
                return js[start:k + 1]
    raise AssertionError(f"函数 {name} 花括号不配平")


def _js_string_literals(js: str) -> list:
    """JS 字符串字面量(单引号/双引号/反引号), 先剥注释 —— 反向断言只钉用户可见串, 不误伤历史注释"""
    body = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    body = re.sub(r"(?<![:\\])//[^\n]*", "", body)  # (?<!:) 放过 http:// 这类 URL
    return re.findall(r"'[^'\n]*'|\"[^\"\n]*\"|`[^`\n]*`", body)


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
    """徽标图例措辞守阵(计划 §01 事实澄清/S5④): 图例必须写明「浏览器工具栏」—— 旧句「工具栏图标徽标
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


#: 真跑 background.js::badgeIconOf(切出函数体): 四态 -> {16,32} 图标路径映射(R4 路径 A)。
_NODE_RUN_BADGE_ICON = """
const fs = require('fs');
function grab(src, name) {
  const i = src.indexOf('function ' + name + '(');
  if (i < 0) throw new Error('未找到函数 ' + name);
  let depth = 0, seen = false;
  for (let k = i; k < src.length; k += 1) {
    const ch = src[k];
    if (ch === '{') { depth += 1; seen = true; }
    else if (ch === '}') { depth -= 1; if (seen && depth === 0) return src.slice(i, k + 1); }
  }
  throw new Error('函数体花括号不配平: ' + name);
}
const src = fs.readFileSync(process.argv[1], 'utf8');
const iconDecl = src.indexOf('const BADGE_ICON = {');
const iconBlock = src.slice(iconDecl, src.indexOf('};', iconDecl) + 2);
const fn = new Function(iconBlock + '\\n' + grab(src, 'badgeIconOf') + '\\nreturn badgeIconOf;')();
process.stdout.write(JSON.stringify(['unconfigured', 'ok', 'reconnecting', 'discoveryFailed'].map((s) => [s, fn(s)])));
"""


def test_badge_icon_frame_mapping():
    """图标外框映射守阵(R4/S6/S5⑦): 四态 -> {16,32} 路径纯函数直测 + 8 个 PNG(生成物
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
        proc = _run_node([node, "-e", _NODE_RUN_BADGE_ICON, str(BACKGROUND_JS)])
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
    bg = _read(BACKGROUND_JS)
    assert "text: 'OK'" not in bg and "text: '..'" not in bg, "旧 OK/.. 徽标文案随 R4 废止, 不得回潮"


#: 跨层机械比对(计划 26-10-15-2357 S6 + 档案「机械比对缺口」): 徽标态(background.js::badgeStateOf)与
#: 顶部总览态(options.js::connStateOf)是**同一条判据的两个展示面** —— 两份实现分头演化就会出现
#: 「徽标报警但页面说正常」这类最危险的静默漂移(用户最怕的正是这个)。这里把两个函数体各自从文件里
#: **切出来真跑**同一张真值表逐输入比对; 另钉四态键集(BADGE vs CONN_STATE_TEXT)与徽标图例文案同源。
_NODE_RUN_CROSS_LAYER_STATE = """
const fs = require('fs');
function grab(src, name) {
  const i = src.indexOf('function ' + name + '(');
  if (i < 0) throw new Error('未找到函数 ' + name);
  let depth = 0;
  let seen = false;
  for (let k = i; k < src.length; k += 1) {
    const ch = src[k];
    if (ch === '{') { depth += 1; seen = true; }
    else if (ch === '}') { depth -= 1; if (seen && depth === 0) return src.slice(i, k + 1); }
  }
  throw new Error('函数体花括号不配平: ' + name);
}
function objKeys(src, name) {
  const i = src.indexOf('const ' + name + ' = {');
  if (i < 0) throw new Error('未找到常量 ' + name);
  const body = src.slice(i, src.indexOf('};', i));
  return (body.match(/^\\s*([A-Za-z_][\\w]*):/gm) || []).map((s) => s.trim().replace(':', ''));
}
const bg = fs.readFileSync(process.argv[1], 'utf8');
const opt = fs.readFileSync(process.argv[2], 'utf8');
const badgeFn = new Function(grab(bg, 'badgeStateOf') + '\\nreturn badgeStateOf;')();
const connFn = new Function(grab(opt, 'connStateOf') + '\\nreturn connStateOf;')();
const A = 'http://127.0.0.1:9001';
const cases = [
  { instances: [], discoveryAddress: '' },
  { instances: [], discoveryAddress: 'http://127.0.0.1:18788' },
  { instances: [{ endpoint: A }], discoveryAddress: '', instanceHealth: { [A]: { ok: true } } },
  {
    instances: [{ endpoint: A }], discoveryAddress: 'http://127.0.0.1:18788',
    instanceHealth: { [A]: { ok: false } }, lastDiscovery: { ok: false, answered: false }
  },
  {
    instances: [{ endpoint: A }], discoveryAddress: 'http://127.0.0.1:18788',
    instanceHealth: {}, lastDiscovery: { ok: false, answered: true }
  },
  { instances: [{ endpoint: A }], discoveryAddress: '', instanceHealth: {}, lastDiscovery: null },
  {
    instances: [{ endpoint: A }], discoveryAddress: 'http://127.0.0.1:18788',
    instanceHealth: { [A]: { ok: true } }, lastDiscovery: { ok: false, answered: false }
  },
];
const badgeBlock = bg.slice(bg.indexOf('const BADGE = {'), bg.indexOf('function badgeStateOf'));
const labels = (badgeBlock.match(/label: '([^']*)'/g) || []).map((s) => s.replace("label: '", '').replace("'", ''));
process.stdout.write(JSON.stringify({
  badgeOut: cases.map((c) => badgeFn(c)),
  connOut: cases.map((c) => connFn(c)),
  badgeKeys: objKeys(bg, 'BADGE'),
  connKeys: objKeys(opt, 'CONN_STATE_TEXT'),
  labels: labels,
}));
"""


def test_conn_state_judgement_matches_badge():
    """**跨层机械比对**: 徽标态(background.js)与顶部总览态(options.js)必须逐输入一致

    两者是同一条判据的两个展示面(计划 §3.3/Q4②), 此前是两份实现、只靠注释互指 —— 一旦分头演化,
    「徽标报警但页面说正常」这类漂移就没有任何机械拦阻。这里把两个函数体各自从文件里切出来真跑同一张
    真值表(含 C4 边界: 有应答无可用实例 = 重连中 vs 候选全无应答 = 发现失败), 并把四态键集与徽标图例
    文案一起钉住(改判据必须三处一起改)。
    """
    node = _node()
    if not node:
        return  # 没装 node: 与其它前端守阵同口径静默跳过
    proc = _run_node([node, "-e", _NODE_RUN_CROSS_LAYER_STATE, str(BACKGROUND_JS), str(OPTIONS_JS)])
    assert proc.returncode == 0, f"node 跨层比对失败: {proc.stderr.strip()}"
    got = json.loads(proc.stdout)
    assert got["badgeOut"] == got["connOut"], \
        f"徽标态与顶部总览态对同一配置给出了不同结论(同一条判据的两份实现漂移了): {got}"
    assert got["badgeOut"] == [
        "unconfigured", "reconnecting", "ok", "discoveryFailed", "reconnecting", "reconnecting", "ok"
    ], f"四态判据(计划 §3.3, C4 边界)取值不符: {got['badgeOut']}"
    assert got["badgeKeys"] == got["connKeys"] == ["unconfigured", "ok", "reconnecting", "discoveryFailed"], \
        f"四态键集必须同源: BADGE={got['badgeKeys']} CONN_STATE_TEXT={got['connKeys']}"
    html = _read(OPTIONS_HTML)
    legend = html[html.index('id="badgeLegend"'):]
    for label in got["labels"]:
        assert label in legend, f"徽标图例没写全四态(与 background.js 的 BADGE label 同源): 缺 {label}"


def test_log_ui_wiring_and_escape():
    """选项页日志面: 清空走后台协议(直接改 storage 会被后台内存缓冲盖回)、渲染必须转义、限渲染条数"""
    js = _read(OPTIONS_JS)
    bg = _read(BACKGROUND_JS)
    html = _read(OPTIONS_HTML)
    assert "'clear-logs'" in js and "'clear-logs'" in bg, "清空要经后台清(内存缓冲是唯一写入口)"
    assert "logMax" in js and "logLevel" in js, "条数上限与记录级别要能落盘"
    assert "logFilter" in html and "logView" in html, "分级显示的过滤控件与日志视图要在页面上"
    assert html.index("logView") < html.index("options.js"), "日志容器要在脚本之前(否则 getElementById 拿不到)"
    assert "esc(" in js, "日志渲染必须过 HTML 转义(明细含站点 URL/页面片段, 裸插 innerHTML 是注入面)"
    assert "chrome.storage.onChanged" in js, "后台落盘后选项页要自动刷出来(不用手点刷新)"
    assert "LOG_RENDER_CAP" in js, "全量渲染 10000 行会卡死选项页, 必须限渲染条数"


def test_options_poll_label_matches_background():
    """选项页的轮询周期文案必须与 background.js 的 POLL_MINUTES 同步(漂移史: 文案停在 5 分钟,
    实际 v2.6 起已改 1 分钟 —— 用户按选项页显示的数字理解行为, 对不上就把排查引向歧途)"""
    bg = _read(BACKGROUND_JS)
    html = _read(OPTIONS_HTML)
    m = re.search(r"const POLL_MINUTES = (\d+);", bg)
    assert m, "POLL_MINUTES 常量要存在(改用别的名字时这条断言一起改)"
    assert f"每 {m.group(1)} 分钟" in html, f"选项页轮询周期文案与 POLL_MINUTES={m.group(1)} 不一致, 两处要同步改"
