"""test_web_longtail_frontend 测试计划: P1 覆盖率提升轮 + v3 活尾 (运行时 / 命令 / 路由长尾)

## 测试计划(每个测试函数一条)
### P1 覆盖率提升轮: webui 运行时与命令长尾
- test_common_open_path_wraps_file_access: common.open_path 包装层直驱 —— 经 get_file_access() 打开并透传 select(稳定 patch 地址不漂移回 infra.utils 直调)
- test_frontend_toast_duration_floor_by_kind: 错误/超时类 toast 停留下限守阵(2026-10-05 用户报「右下角错误信息停留太短」) ——
  ui_feedback.js 头部 `TOAST_MS_FLOOR` 给 error/timeout 设 ≥8s 下限, `toast()` 与 `_finishToast()`
  两条排期路径都经 `toastMs(kind, ms)` 解析且 ms 缺省为 null(绕过即回到裸 ms, 下限形同虚设)
- test_aq_tip_anchor_watch_and_reacquire_wired: aq-tip 锚定保活守阵(2026-10-07 用户报「详情面板 tooltip 位置不正确」, 变体 5s 轮询整帧重建三条错位路径) —— ui_feedback.js 定位抽 place() 单点(show 初显与显示期重定位共用, 夹取/err-panel 避让同口径) + reacquire() 语义重解析(data-aq-tip 同文案节点按视口中心距旧矩形最近者, 语义扫描先于指针坐标 elementFromPoint 回退, 回退有 Number.isFinite(curX) 门护键盘 NaN 路径) + watch/tick rAF 帧环(浮层可见期才运转, 每帧只 1 次 getBoundingClientRect 零 DOM 查询: 断链走语义重解析 / 四轴 rect 漂移超 1px 重定位) + enter 记 curRect 基准 / hide 作废成对, 任一环被重构摘除即红
"""

import base64

import errno

import os

import re

import tempfile

import time

from pathlib import Path

from types import SimpleNamespace

from auto_qb.infra import file_access

from auto_qb.infra.utils import encode_group_key

from auto_qb.webui.runtime import (
    CMD_SLOW_MS,
    EVENT_QUEUE_MAX,
    REANNOUNCE_CONFIRM_TIMEOUT,
    WEB_RESULT_MAX,
    WEB_RESULT_TTL,
    WebUIRuntime,
)

from helpers import capture_logs

from webui_helpers import (
    KEY,
    STATIC_ROOT,
    _enable_qb_traffic,
    _qb_v4,
    _make_grouped_manager,
    _attach_live_tail_host,
)


def test_frontend_toast_duration_floor_by_kind() -> None:
    """错误 / 超时类 toast 停留时长下限守阵(2026-10-05 用户报「右下角错误信息停留太短」)

    停留时长单点在 `shared/ui_feedback.js` 头部的 `TOAST_MS_FLOOR`; `toast()` 与 `_finishToast()`
    两条排期路径都必须经 `toastMs(kind, ms)` 解析 —— 绕过即回到裸 ms, 按 kind 的下限形同虚设。
    钉住三件事(全是"pytest 全绿、界面行为退化"的形态):
    1. error / timeout 的下限不得低于 8s(用户报障的正是"4s 一闪而过, 带原因段的报错读不完");
    2. 排期点恰好 2 处且都走 `toastMs(kind, ms)`(新增排期点须一并走解析, 否则新链路漏掉下限);
    3. 两处 `ms` 缺省为 `null`(写死数字会让 kind 下限在缺省路径不生效 —— 而报障的恰恰是缺省路径)。
    """
    fb = open(os.path.join(STATIC_ROOT, "shared", "ui_feedback.js"), encoding="utf-8").read()
    m = re.search(r"TOAST_MS_FLOOR = \{([^}]*)\}", fb)
    assert m, "ui_feedback.js 缺 TOAST_MS_FLOOR(停留时长单点; 改名或挪走了? 同步本守阵)"
    floors = {k: int(v) for k, v in re.findall(r"(\w+)\s*:\s*(\d+)", m.group(1))}
    assert floors.get("error", 0) >= 8000, \
        f"error 类 toast 停留下限过低({floors.get('error')}ms) —— 「错误信息一闪而过」会复发"
    assert floors.get("timeout", 0) >= 8000, \
        f"timeout 类 toast 停留下限过低({floors.get('timeout')}ms) —— 部分失败汇总同样要读得完"
    assert fb.count("toastMs(kind, ms)") == 2, \
        "排期点应为 2 处(toast / _finishToast)且都必须走 toastMs(kind, ms)(绕过 = 下限失效)"
    assert re.search(r"toast\(text, kind = \"info\", ms = null, opts = \{\}\)", fb), \
        "toast() 的 ms 缺省必须是 null(写死 4000 会让 kind 下限在缺省路径不生效)"
    assert re.search(r"_finishToast\(id, kind, text, ms = null\)", fb), \
        "_finishToast() 的 ms 缺省必须是 null(同上)"


def test_aq_tip_anchor_watch_and_reacquire_wired():
    """aq-tip 锚定保活守阵(2026-10-07 用户报「详情面板 tooltip 位置不正确」)

    详情面板 15 变体由轮询数据驱动整帧重建(replaceChildren), tooltip 三条错位路径:
    ①350ms 窗口内锚点被换掉后按旧指针坐标重解析可能中到别的元素(布局移位), 键盘 focusin
    路径无坐标; ②浮层已显示后锚点被 5s 轮询换成新节点(mouseover 不再触发), 浮层停旧坐标;
    ③重建引发布局移位, 浮层不跟随。修法单点在 shared/ui_feedback.js: 定位抽 place() 单点 +
    reacquire() 语义重解析(先于指针坐标回退) + watch/tick rAF 帧环廉价体检。本守阵读 JS
    源码钉住结构与次序(剥行注释后锚定, 注释改写不红、代码突变必红), 任一环被重构摘除即红:
    1. enter 记录锚点矩形基准 curRect, hide 作废(键盘路径无坐标, 全靠矩形基准重解析);
    2. reacquire 语义优先: 全文档 [data-aq-tip] 同文案节点按矩形中心距取最近, 之后才是指针
       坐标 elementFromPoint 回退(次序倒了 = 布局移位路径复发), 回退有 Number.isFinite 门;
    3. show 断链走 reacquire, 定位统一走 place 并挂 watch(两路径夹取/避让同口径);
    4. tick 帧环: 只在浮层可见期运转, 每帧仅 1 次 getBoundingClientRect 零 DOM 查询,
       断链分支与四轴漂移分支齐备(非断链路径出现 querySelectorAll = 性能红线)。
    """
    ui = open(os.path.join(STATIC_ROOT, "shared", "ui_feedback.js"), encoding="utf-8").read()

    # ① 矩形基准的记/废成对
    assert re.search(r"^  let curRect = null;", ui, re.M), \
        "ui_feedback.js 缺 curRect 矩形基准状态(语义重解析/漂移检测失锚, 同步本守阵)"
    assert re.search(r"curRect = target\.getBoundingClientRect\(\);", ui), \
        "enter 未记录锚点矩形基准 —— 键盘路径(focusin 无坐标)的锚点重解析退化为直接收起"
    m = re.search(r"function hide\(\)\s*\{(.*?)\n  \}", ui, re.S)
    assert m and "curRect = null" in m.group(1), \
        "hide 未作废 curRect 基准(悬空基准会污染下一次悬浮的重解析)"

    # ② reacquire: 语义扫描先于指针回退, 回退有 NaN 门
    m = re.search(r"function reacquire\(\)\s*\{(.*?)\n  \}", ui, re.S)
    assert m, "ui_feedback.js 找不到 reacquire(锚点被重建换掉后的语义重解析单点被摘? 同步本守阵)"
    acq = re.sub(r"//[^\n]*", "", m.group(1))
    assert 'querySelectorAll("[data-aq-tip]")' in acq, \
        "reacquire 缺语义候选扫描(同 data-aq-tip 文案的新节点) —— 断链后无处重解析"
    i_sem = acq.index('querySelectorAll("[data-aq-tip]")')
    i_ptr = acq.find("elementFromPoint")
    assert i_ptr != -1, \
        "reacquire 缺指针坐标回退(2026-10-04 收口口径: 语义解析不到才按指针重解析)"
    assert i_sem < i_ptr, \
        "reacquire 指针回退先于语义解析 —— 布局移位时旧坐标下的元素已不是原锚点(路径③复发)"
    assert re.search(r"Number\.isFinite\(curX\)", acq), \
        "指针回退缺 Number.isFinite(curX) 门 —— 键盘路径 NaN 坐标会传给 elementFromPoint"

    # ③ show 断链走 reacquire; 定位单点 place + 显示期监测 watch 成对
    m = re.search(r"function show\(anchor\)\s*\{(.*?)\n  \}", ui, re.S)
    assert m, "ui_feedback.js 找不到 show(改名或挪走了? 同步本守阵)"
    sh = re.sub(r"//[^\n]*", "", m.group(1))
    assert "reacquire()" in sh, \
        "show 的断链分支未走 reacquire(键盘路径无指针坐标, 只能靠语义重解析兜住)"
    assert re.search(r"function place\(anchor\)", ui), \
        "定位未抽 place() 单点 —— show 初显与显示期重定位两套夹取/避让口径必然漂移"
    assert re.search(r"place\(anchor\);", sh) and "watch();" in sh, \
        "show 未统一走 place + watch(定位单点/显示期监测被绕开)"
    assert re.search(r"curRect = \{ left: r\.left, top: r\.top", ui), \
        "place 未在定位时刷新 curRect 基准(漂移检测失准)"

    # ④ tick 帧环: 可见期才运转, 断链/漂移两分支齐备, 每帧路径零全文档查询
    m = re.search(r"function tick\(\)\s*\{(.*?)\n  \}", ui, re.S)
    assert m, "ui_feedback.js 找不到 tick(rAF 帧环主体被摘? 同步本守阵)"
    tick = re.sub(r"//[^\n]*", "", m.group(1))
    assert 'classList.contains("on")' in tick and "cur" in tick, \
        "tick 缺可见性守卫(cur + .on) —— 浮层收起后帧环空转烧帧"
    assert "isConnected" in tick, \
        "tick 缺锚点存活检查 —— 浮层显示后锚点被重建换掉不再跟随(路径②复发)"
    assert "reacquire()" in tick, "tick 断链分支未走语义重解析"
    for axis in ("left", "top", "width", "height"):
        assert f"curRect.{axis}" in tick, f"tick 漂移检测缺 {axis} 轴比对(重建移位/内容变宽不重定位)"
    assert "querySelectorAll" not in tick, \
        "tick 每帧路径出现全文档查询 —— 体检必须只做 1 次 rect 比对(5s 轮询场景的性能红线)"
    assert re.search(r"requestAnimationFrame\(tick\)", ui), \
        "帧环未用 requestAnimationFrame(定时器轮询会与绘制解耦空转)"


def test_common_open_path_wraps_file_access(monkeypatch):
    """common.open_path 包装层直驱: 经 get_file_access() 打开并透传 select(稳定 patch 地址)

    open-path 端点与既有守阵都以 `common.open_path` 为 patch 地址(拆分时定下的稳定点) ——
    直调包装层钉住「再导出改回 infra.utils 直调」这类漂移: 容器(Mapped)实现抛
    NotSupported 的语义化 501 全靠这层转发, 绕过即丢。
    """
    import auto_qb.webui.server.common as fs_common

    seen = []

    class _FA:
        def open_path(self, path, select=False):
            seen.append((path, select))

    monkeypatch.setattr(fs_common, "get_file_access", lambda: _FA())
    fs_common.open_path("/tmp/probe")
    fs_common.open_path("/tmp/probe2", select=True)
    assert seen == [("/tmp/probe", False), ("/tmp/probe2", True)]
