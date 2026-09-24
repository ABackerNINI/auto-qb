"""HR **四类事件**的通知文案单点(计划 §11 M4)。

为什么要集中: 这四类事件是「用户需要做点什么」的信号, 文案必须**一眼可辨**(各自带
标签前缀 `[HR 登录失效]` 等), 而原先它们散落在各调用点的 f-string 里 —— 改一处措辞就得
翻三个文件, 更糟的是**同类事件在两端各写一遍**(service 报一次 / worker 又报一次, 措辞不同),
排查时看着像两件事。

四类事件(计划定义):
- `login`    **登录失效**: 页面变成登录页 ⇒ 必须有人去浏览器登录; **不可重试解决**;
- `fuse`     **熔断**: 连续取数失败达阈值 ⇒ 退避冷却(重试可解决, 但要先看站点/通道是否正常);
- `parse`    **页面改版**: 表头找不到 / 分页到底判据变了 ⇒ 覆盖证明不成立, 需人工核对页面;
- `silence`  **通道静默**: 端点长期没被扩展联系 ⇒ 浏览器没开 / 扩展停用 / 端口或 token 配错。

口径: 本模块只出**文案**(日志文本), 不做判断、不分级 —— 级别仍由调用点决定(见 `worker._note`
的三档分级说明)。标签前缀也让用户在日志里 `grep "[HR 熔断]"` 就能捞出这一类事件。
"""
from typing import Iterable, Sequence

import time

EVENT_LOGIN = "login"
EVENT_FUSE = "fuse"
EVENT_PARSE = "parse"
EVENT_SILENCE = "silence"

#: 事件 -> 中文标签(日志前缀用; 也是用户 grep 的锚点)
LABELS = {
    EVENT_LOGIN: "登录失效",
    EVENT_FUSE: "熔断",
    EVENT_PARSE: "页面改版",
    EVENT_SILENCE: "通道静默",
}


def prefix(event: str) -> str:
    """事件标签前缀(如 `[HR 登录失效]`)"""
    return f"[HR {LABELS.get(event, event)}]"


def login_expired(site: str, detail: str) -> str:
    """登录失效告警: 必须给出**动作**(去哪个浏览器登录哪个站点) —— 否则用户只看到「失败了」"""
    return (
        f"{prefix(EVENT_LOGIN)} 站点 {site} | 页面是登录页 ⇒ 本实例的浏览器登录态已失效, "
        f"**请在该浏览器里登录 {site} 后无需其它操作**(在此之前不会产生新放行, 老数据照旧保守回落) | 原始: {detail}"
    )


def login_expired_note(site: str, detail: str) -> str:
    """写进站点文件 `refresh.reason` 的短句(报告与 WebUI 的 notes 都读它 —— 失败路径里唯一持久可见的痕迹)"""
    return f"{prefix(EVENT_LOGIN)} 本轮未发起刷新(页面是登录页, 需人工登录 {site}): {detail}"


def fetch_failed(site: str, failures: int, threshold: int, detail: str) -> str:
    """取数失败(未达熔断阈值): 仍归熔断类 —— 用户关心的后续动作是「等着看会不会熔断」"""
    left = max(0, threshold - failures)
    return f"{prefix(EVENT_FUSE)} 站点 {site} | 取数失败({failures} 次, 距熔断还差 {left} 次): {detail}"


def fuse_opened(site: str, until_ts: float, detail: str) -> str:
    """熔断进入: 退避冷却(重试可解决, 但先看站点能不能访问 / 扩展正不正常)"""
    when = time.strftime("%m-%d %H:%M:%S", time.localtime(until_ts)) if until_ts > 0 else "-"
    return f"{prefix(EVENT_FUSE)} 站点 {site} | 连续失败达阈值, 冷却至 {when}(期间不再请求该站点): {detail}"


def page_changed(site: str, action: str, detail: str) -> str:
    """页面改版疑似: 覆盖证明不成立 ⇒ 不复用旧放行(保守), 需人工核对 HR 页结构"""
    return f"{prefix(EVENT_PARSE)} 站点 {site} | {action}: {detail}(覆盖证明不成立 ⇒ 本轮不产生新放行; 请核对站点 HR 页是否改版)"


def channel_silent(hours: float, where: str, sites: Sequence[str], note: str = "") -> str:
    """通道静默: 端点级事件(扩展没来联系**就没有任何站点能取数**) ⇒ 文案里点出受影响站点"""
    affected = ", ".join(sites) if sites else "(无启用中的站点)"
    tail = f" {note}" if note else ""
    return (
        f"{prefix(EVENT_SILENCE)} 端点已静默 {hours:.1f}h({where}扩展未联系端点), 受影响站点: {affected} | "
        f"浏览器是否在运行 / 扩展是否启用 / 端点端口与 token 是否与扩展配置一致?{tail}"
    )


def summarize_sites(sites: Iterable[str]) -> str:
    """站点清单的稳定顺序(报告与日志都要人读, 顺序抖动会让人以为是两件事)"""
    return ", ".join(sorted(sites))


__all__ = [
    "EVENT_FUSE",
    "EVENT_LOGIN",
    "EVENT_PARSE",
    "EVENT_SILENCE",
    "LABELS",
    "channel_silent",
    "fetch_failed",
    "fuse_opened",
    "login_expired",
    "login_expired_note",
    "page_changed",
    "prefix",
    "summarize_sites",
]
