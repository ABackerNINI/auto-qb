"""test_extension_proxy_options 测试计划: 浏览器扩展(HR 取数代理)的静态与行为守阵

扩展是**要用户装进浏览器**的交付物: pytest 跑不到它的运行期, 但四类故障是**静态/半静态可查**的,
且都属于"pytest 全绿、用户装上就报错"的形态 —— 2026-09-24 实测两条:
1. 裸域名直喂 `chrome.permissions.request` ⇒ `Invalid value for origin pattern pt.btschool.club:
   Missing scheme separator.`(**未捕获的 Promise 拒绝**);
2. 端点没起 / 地址写法不对时用户只看到一句 `TypeError: Failed to fetch`(浏览器对网络层失败只给这句)。
故这里钉死: manifest 的作用域、JS 语法、**与后端的协议常量**、以及"输入先归一化再交给浏览器 API"。

## 测试计划(每个测试函数一条)
- test_options_normalizes_before_browser_api: 站点源与端点先归一化再进权限/存储 API(本次报错的形态)
- test_options_rejections_are_always_handled: 选项页不得留下裸 Promise 拒绝(兜底 unhandledrejection + 逐个 catch)
- test_options_site_fetch_matches_backend: 站点授权清单走 GET /api/hr/sites, 路径/鉴权头与 hr.channel 同源
- test_options_swiss_wiring: 瑞士网格终态(风格选型 A)接线齐全(两表/表单授权/折叠排障区/连接后端一区),
  三档共存机制不回潮; 2026-10-16 S4 合并布局后判据随之更新(删「保存发现地址与配对码」按钮)
- test_options_poll_label_matches_background: 选项页「启用轮询(每 N 分钟…)」文案与 background.js 的
  POLL_MINUTES 同步(漂移史: 文案停在 5 分钟, 实际 v2.6 起已改 1 分钟, 用户照文案理解行为必对不上)

### 去端口+跨机轮(计划 26-10-14-1241 S4): 判据放开与自动发现
- NORMALIZE_CASES 更新: 私网三段逐段放行 / 公网域名拒绝 / https 保留不折 / 新增 disc 类(发现地址缺端口补 18788)
  —— 旧断言「非回环即抛」「https 折 http」是被本计划翻转的旧语义, 随计划更新而非守阵松动
### 连接自愈轮(计划 26-10-15-2357 S1/S2): 合并语义翻转 + 自愈触发 + 徽标 + 台账
- 合并语义翻转(Q1/Q2/Q8/C1): 旧断言「同端点被发现覆盖 / 只增不减」是被本计划翻转的旧语义, 随计划更新
  而非守阵松动 —— 手动条目 = 高优先级(整条胜 + 置顶 + 永不自动删), 发现集 = 租约(整批替换, 空集除外)。
- 降噪场景(_NODE_RUN_NOISE)显式 discoveryAddress 置空 —— 那条守阵钉「连接失败降噪」, 不混发现流日志
### 连接自愈轮 · S6 守阵补强(计划 26-10-15-2357 S6)
- test_options_listens_instances_changes: storage.onChanged 监听 instances/instanceHealth/lastDiscovery(S3 4)
### 连接区 UI 重排 + 实例状态入表轮(计划 26-10-16-0214 S4-S6)
- test_options_swiss_wiring 扩: 元素清单随 S1 更新(helpTroubleshoot/connStateDot/Text/Meta)
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
    EXT_DIR,
    OPTIONS_HTML,
    OPTIONS_JS,
    _balanced_block,
    _read,
)


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
    2026-10-16 计划 26-10-15-2357 S4 把「连接端点 + 手动端点 + 底部工具栏」合并为**一个「1. 连接
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


def test_options_listens_instances_changes():
    """连接面实时刷新(计划 §S3-4): storage.onChanged 必须监听 instances / instanceHealth / lastDiscovery

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


def test_options_poll_label_matches_background():
    """选项页的轮询周期文案必须与 background.js 的 POLL_MINUTES 同步(漂移史: 文案停在 5 分钟,
    实际 v2.6 起已改 1 分钟 —— 用户按选项页显示的数字理解行为, 对不上就把排查引向歧途)"""
    bg = background_text()
    html = _read(OPTIONS_HTML)
    m = re.search(r"const POLL_MINUTES = (\d+);", bg)
    assert m, "POLL_MINUTES 常量要存在(改用别的名字时这条断言一起改)"
    assert f"每 {m.group(1)} 分钟" in html, f"选项页轮询周期文案与 POLL_MINUTES={m.group(1)} 不一致, 两处要同步改"
