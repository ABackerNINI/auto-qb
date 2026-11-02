"""test_extension_proxy_manifest 测试计划: 浏览器扩展(HR 取数代理)的静态与行为守阵

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
- test_site_caps_are_shared_single_source: 硬上限只有一份(site-caps.js), 后台与选项页都载入它

### 去端口+跨机轮(计划 26-10-14-1241 S4): 判据放开与自动发现
- NORMALIZE_CASES 更新: 私网三段逐段放行 / 公网域名拒绝 / https 保留不折 / 新增 disc 类(发现地址缺端口补 18788)
  —— 旧断言「非回环即抛」「https 折 http」是被本计划翻转的旧语义, 随计划更新而非守阵松动
- test_normalizers_are_shared_not_duplicated 扩: discovery.js 六个函数(含 isManualEntry)同样禁止本地副本,
  两个消费方都载入它
- test_protocol_matches_backend 扩: API_DISCOVER 与缺省发现端口三处同源(后端 / discovery.js / normalize.js)
### 连接自愈轮(计划 26-10-15-2357 S1/S2): 合并语义翻转 + 自愈触发 + 徽标 + 台账
- 合并语义翻转(Q1/Q2/Q8/C1): 旧断言「同端点被发现覆盖 / 只增不减」是被本计划翻转的旧语义, 随计划更新
  而非守阵松动 —— 手动条目 = 高优先级(整条胜 + 置顶 + 永不自动删), 发现集 = 租约(整批替换, 空集除外)。
- 降噪场景(_NODE_RUN_NOISE)显式 discoveryAddress 置空 —— 那条守阵钉「连接失败降噪」, 不混发现流日志
### 连接自愈轮 · S6 守阵补强(计划 26-10-15-2357 S6)
### 连接区 UI 重排 + 实例状态入表轮(计划 26-10-16-0214 S4-S6)
  + 「自测端点连通」「载入」按钮字面量不得回潮 + 实例表真表头(状态列)
### 站点可选权限轮(计划 26-10-29-0147 W1/D5): 未授权即拒发 + 逐站展示
"""

import json

import pathlib

import re

import shutil

import subprocess

import pytest

from auto_qb.hr.channel import API_RESULT, API_SITES, API_TASKS, TOKEN_HEADER, HrChannelError, HrResult

from auto_qb.hr.discovery import API_DISCOVER, DISCOVERY_DEFAULT_PORT

from extension_proxy_support import (
    BACKGROUND_JS,
    background_text,
    DISCOVERY_JS,
    EXT_DIR,
    JS_FILES,
    MANIFEST,
    NORMALIZE_CASES,
    NORMALIZE_JS,
    OPTIONS_HTML,
    OPTIONS_JS,
    SITE_CAPS_JS,
    _NODE_RUN_NORMALIZERS,
    _node,
    _read,
    _run_node,
)


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
    for name, text in ((BACKGROUND_JS.name, background_text()), (OPTIONS_JS.name, _read(OPTIONS_JS))):
        assert not re.search(r"(?m)^const SITE_CAPS", text), f"{name} 又定义了一份阈值"
        assert "SITE_CAPS[" in text or "Object.entries(SITE_CAPS)" in text, \
            f"{name} 应当消耗共享阈值而不是写死数字"


def test_protocol_matches_backend():
    """扩展与后端的线上格式钉在一处: 常量取 `hr.channel`/`hr.discovery`, 字段名取实测行为(双向守阵)"""
    background = background_text()
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
