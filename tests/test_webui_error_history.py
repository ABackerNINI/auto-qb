"""WEBUI 错误历史前端静态守阵 (计划 S7 · 前端守阵; 数据层 S1 / boot 合并 S3 / 面板 T2 / 断线源 S6)。

守什么: 前端无 JS 测试框架, 错误历史的收集/展示链路断任何一环都是**静默**的 (toast 照弹但不进历史、
徽标不亮、面板空白、后端条目进不来), 只能靠静态接线断言钉住。断言一律按「接线存在性」(grep/结构),
不锁视觉值 (z-index/偏移走真机走查, 计划 §07 明确守阵不管这类值)。后端环的行为守阵在
tests/test_webui_backend_errlog.py (S2), 本文件只管前端。

## 测试计划

- test_frontend_error_history_hooks_present: ui_feedback.js 的 toast() 与 _finishToast() 两处都接
  _recordErrorToast (emit 即收 + settle upsert 双钩子; 漏一处 = sticky 链或直接链丢历史), 且 toast()
  里的收集调用在 sticky 早退 return 之前 (挪到后面 sticky 条 emit 时就漏收)
- test_frontend_error_history_cap_ring: ERR_HISTORY_CAP 存在且 _recordErrorToast / _mergeBackendErrlog
  两处裁剪都是「超限 pop」环形语义 (改成 shift/filter 或无界增长即红)
- test_frontend_error_history_no_persistence: shared/ 层 localStorage/sessionStorage 写入 (setItem)
  逐文件计数钉死不增 —— 历史语义钉死在会话内存 (刷新即失); 读 (getItem) 不算写不拦
- test_frontend_error_history_entry_wired: statusbar.html 有 .sb-err 入口钮 (toggle errPanelOpen) 与
  未读徽标 (errUnread) 绑定; overlays.html 有 .err-panel 面板 (v-if=errPanelOpen) 与清空钮
  (clearErrorHistory 别名中转); state.js 有 errHistory/errUnread 两个无前缀模板别名 (模板代理不认
  _ 前缀, 没别名 = 徽标与面板直接渲染失败)
- test_frontend_error_history_copy_wired: 面板行内复制钮 @click 走 copyText 而非 _copyText (Vue 模板
  下划线方法坑, issue 26-10-03-1412; 模板保留域守阵在 test_web, 本条聚焦面板复制钮的接线指向), 且
  commands.js 的 copyText 包装存在并委托 _copyText (别名不是空壳)
- test_frontend_error_history_boot_merge_wired: lifecycle 含 errlog boot 拉取 (本机免鉴权 + auth.js
  密钥路径两处各调一次 _pullErrlogBoot, boot 全量不计未读) + 60s 补拉定时器 (setInterval 60000) +
  unmounted 撤定时器 (clearInterval _errPollTimer) 三处接线 (漏一处 = 后端条目进不了面板或热重载堆叠)
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src" / "auto_qb" / "webui" / "static"
SHARED = STATIC / "shared"
TPL = SHARED / "tpl"


def _read(rel: str) -> str:
    return (SHARED / rel).read_text(encoding="utf-8")


def _fn_body(text: str, signature: str, indent: int = 4) -> str:
    """按方法签名取函数体(到同缩进 `},` 收口); 找不到即断言失败 —— 方法被改名/搬走时守阵要响。
    indent: 收口缩进 —— mixin 方法体在 4 空格, 根组件选项(mounted/unmounted)在 2 空格"""
    m = re.search(r"(?:^|\n)[ \t]*" + re.escape(signature) + r" \{(.*?)\n" + " " * indent + r"\},", text, re.S)
    assert m, f"找不到方法 {signature}(被改名/搬走? 同步本守阵)"
    return m.group(1)


def test_frontend_error_history_hooks_present() -> None:
    """S1 双钩子: toast() emit 即收 + _finishToast 终态 upsert, 两处都接 _recordErrorToast"""
    fb = _read("ui_feedback.js")
    record = _fn_body(fb, "_recordErrorToast(id, kind, text)")
    assert "this._errHistory" in record, "_recordErrorToast 必须写 _errHistory(收集单点被搬走?)"
    # 收集单点定义存在之后, 两条链各自接线:
    toast = _fn_body(fb, 'toast(text, kind = "info", ms = null, opts = {})')
    at = toast.find("this._recordErrorToast(")
    assert at >= 0, "toast() 缺错误历史收集钩子(直接链 emit 即收断了: error/timeout toast 照弹但不进历史)"
    sticky_at = toast.find("if (opts.sticky) return id;")
    assert 0 <= at < sticky_at, (
        "toast() 的收集钩子必须在 sticky 早退 return 之前(挪到后面 = sticky「等待中」条 emit 时不收, "
        "只能靠 _finishToast 结算, 双钩子退化成单钩子)"
    )
    finish = _fn_body(fb, "_finishToast(id, kind, text, ms = null)")
    assert "this._recordErrorToast(" in finish, (
        "_finishToast 缺终态 upsert 钩子(sticky 链丢了历史: busy 不入 ERR_HISTORY_KINDS, "
        "只在结算成 timeout/error 时首次入历史)"
    )


def test_frontend_error_history_cap_ring() -> None:
    """cap 存在 + 两处写入都走「超限 pop」环形语义(防改成无界增长或裁错方向)"""
    fb = _read("ui_feedback.js")
    m = re.search(r"const ERR_HISTORY_CAP = (\d+);", fb)
    assert m and int(m.group(1)) >= 1, "ERR_HISTORY_CAP 常量缺失(环形上限单点被改名/删除)"
    clip = "this._errHistory.length > ERR_HISTORY_CAP) this._errHistory.pop();"
    record = _fn_body(fb, "_recordErrorToast(id, kind, text)")
    assert clip in record, "_recordErrorToast 缺超限 pop 裁剪(cap 失守 = 无界增长)"
    assert "this._errHistory.unshift(" in record, "_recordErrorToast 新条目必须 unshift(新在上; 裁剪方向依赖它)"
    life = _read("lifecycle.js")
    merge = _fn_body(life, "_mergeBackendErrlog(items, last, opts = {})")
    assert clip in merge, "_mergeBackendErrlog 缺超限 pop 裁剪(后端合并路径绕开环形上限)"
    # 两处裁剪必须引用同一个常量(口径单点; 各写一个字面量 = 改 cap 只改得到一处)
    assert "ERR_HISTORY_CAP" in record and "ERR_HISTORY_CAP" in merge


# shared/ 层 Web Storage 写入逐文件基线(只数 setItem; getItem 读不算写)。
# 错误历史语义钉死在会话内存 —— 本功能零写入; 任何 shared/ 片段新增一条 setItem(含给错误历史
# 加持久化)都会使计数超基线即红。既有功能加写入属合法演化: 改这里的基线并在行内注明来源。
STORAGE_WRITE_BASELINE = {
    "auth.js": 1,  # autoqb_token
    "config_hub.js": 1,  # hub 视图选择
    "columns.js": 3,  # 列宽/顺序/隐藏
    "drawer.js": 3,  # drawerHeight / drawerOpen / drawerTab
    "menu.js": 1,  # 菜单收合态
    "qb_traffic_chart.js": 1,  # qbWinGlobal / qbWinShared
    "view.js": 2,  # 视图选择
}


def test_frontend_error_history_no_persistence() -> None:
    """历史不出会话: shared/ 层 setItem 逐文件计数 == 基线(不增)"""
    counts: dict[str, int] = {}
    for p in sorted(SHARED.glob("*.js")):
        n = len(re.findall(r"(?:localStorage|sessionStorage)\.setItem\(", p.read_text(encoding="utf-8")))
        if n:
            counts[p.name] = n
    assert counts == STORAGE_WRITE_BASELINE, (
        "shared/ 层 Web Storage 写入计数漂移(错误历史零持久化的语义被破坏, 或既有功能加了新写入"
        " —— 后者属合法演化, 更新 STORAGE_WRITE_BASELINE 并行内注明):\n"
        f"  实测: {counts}\n  基线: {STORAGE_WRITE_BASELINE}"
    )


def test_frontend_error_history_entry_wired() -> None:
    """T2 模板接线存在性: 状态栏入口 + 未读徽标 / 面板 + 清空钮 / state.js 无前缀别名"""
    sb = (TPL / "statusbar.html").read_text(encoding="utf-8")
    assert re.search(r'<button class="sb-err"[^>]*@click\.stop="errPanelOpen = !errPanelOpen"',
                     sb), ("statusbar.html 缺错误历史入口钮(.sb-err, toggle errPanelOpen) —— 面板无打开路径")
    assert re.search(r'<span v-if="errUnread > 0" class="sb-err-badge">\{\{ errUnread \}\}</span>',
                     sb), ("statusbar.html 缺未读徽标绑定(errUnread > 0 才显示, 无未读静默 = 保守默认)")
    ov = (TPL / "overlays.html").read_text(encoding="utf-8")
    assert 'v-if="errPanelOpen" class="err-panel"' in ov, "overlays.html 缺错误历史面板(v-if=errPanelOpen)"
    assert '@click="clearErrorHistory()"' in ov, "overlays.html 缺清空钮(必须走 clearErrorHistory 别名中转)"
    state = _read("state.js")
    for alias in ("errHistory() {", "errUnread() {"):
        assert alias in state, f"state.js 缺无前缀模板别名 {alias[:-3]}(模板代理不认 _ 前缀, 没别名 = 面板渲染失败)"
    assert "errPanelOpen(v) {" in state and "this._errUnread = 0;" in state, (
        "state.js 缺 errPanelOpen watcher(开面板清未读) —— 徽标不灭"
    )


def test_frontend_error_history_copy_wired() -> None:
    """面板行内复制钮走 copyText(模板安全别名), 不直调 _copyText; 包装非空壳"""
    ov = (TPL / "overlays.html").read_text(encoding="utf-8")
    assert re.search(r'<button class="err-copy" @click="copyText\(e\.text, [^"]+\)">',
                     ov), ("err-copy 复制钮未走 copyText(下划线方法模板调不到, issue 26-10-03-1412 —— 改了即整行复制失效)")
    ov_code = re.sub(r"<!--.*?-->", "", ov, flags=re.S)  # 剥掉 HTML 注释(注释里点名 _copyText 是禁令本身)
    assert "_copyText" not in ov_code, "overlays.html 出现 _copyText 直调(Vue 模板保留域, 渲染即 ReferenceError)"
    cmd = _read("commands.js")
    wrapper = _fn_body(cmd, "copyText(text, label)")
    assert "this._copyText(text, label)" in wrapper, "commands.js 的 copyText 必须委托 _copyText(别名空壳 = 复制静默无效)"


def test_frontend_error_history_boot_merge_wired() -> None:
    """S3 三处接线: boot 拉取(两条启动路径) + 60s 补拉定时器 + unmounted 撤定时器"""
    life = _read("lifecycle.js")
    mounted = _fn_body(life, "async mounted()", indent=2)  # 根组件选项 2 空格
    assert "this._pullErrlogBoot();" in mounted, "lifecycle mounted 缺 boot 全量拉取(本机免鉴权路径后端条目进不了面板)"
    auth = _read("auth.js")
    assert "this._pullErrlogBoot();" in auth, "auth.js bootstrap 成功路径缺 boot 全量拉取(密钥路径后端条目进不了面板)"
    boot = _fn_body(life, "async _pullErrlogBoot()")
    assert "this._pullErrlog(false)" in boot, "boot 全量必须不计未读(false; 开页即见, 计未读 = 开页就挂红色徽标)"
    assert "const ERR_POLL_INTERVAL_MS = 60000;" in life, "60s 补拉节拍常量缺失(被改名/改值后守阵同步)"
    poll = _fn_body(life, "_startErrPoll()")
    assert "setInterval(() => this._pullErrlog(true), ERR_POLL_INTERVAL_MS);" in poll, (
        "缺 60s 补拉定时器(boot 之后的后端增量条目进不了面板)"
    )
    assert "if (this._errPollTimer) return;" in poll, "补拉定时器必须幂等(双启动路径/重入不叠定时器)"
    unmounted = _fn_body(life, "unmounted()", indent=2)
    assert "clearInterval(this._errPollTimer);" in unmounted, "unmounted 缺撤补拉定时器(热重载句柄堆叠, 补拉越跑越密)"


if __name__ == "__main__":
    raise SystemExit(__import__("pytest").main([__file__, "-q"]))
