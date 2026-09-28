"""HR 事件通知文案单点(v3)。

为什么要集中: 这些事件是「用户需要做点什么」的信号, 文案必须**一眼可辨**(各自带
标签前缀 `[HR 登录失效]` 等), 而原先它们散落在各调用点的 f-string 里 —— 改一处措辞就得
翻三个文件, 更糟的是**同类事件在两端各写一遍**(service 报一次 / worker 又报一次, 措辞不同),
排查时看着像两件事。

事件(v3, 计划 26-09-28-1932 §5.2「告警升级, 行为不变」):
- `login`    **登录失效**: 页面变成登录页 ⇒ 必须有人去浏览器登录; **不可重试解决**;
- `parse`    **页面改版**: 表头找不到 / 字段缺失 / 排序崩塌 / 防伪不过 ⇒ 该档截断, 需人工核对页面;
- `silence`  **通道静默**: 端点长期没被扩展联系 ⇒ 浏览器没开 / 扩展停用 / 端口或 token 配错。

被删除的旧事件: `fuse`(熔断)与 `suspended`(停用)随模型删除 —— v3 的失败处置是
「档位截断 + 周期自然重试」, 无独立熔断/停用机制; 失败档连续多波失效升级为
`lane_persistent_failure`(ERROR, 只提示人, 不改变取数与判定行为)。

口径: 本模块只出**文案**(日志文本), 不做判断、不分级 —— 级别仍由调用点决定。标签前缀也让
用户在日志里 `grep "[HR 页面改版]"` 就能捞出这一类事件。
"""
import time
from typing import Iterable, Sequence

EVENT_LOGIN = "login"
EVENT_PARSE = "parse"
EVENT_SILENCE = "silence"

#: 事件 -> 中文标签(日志前缀用; 也是用户 grep 的锚点)
LABELS = {
    EVENT_LOGIN: "登录失效",
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
        f"**请在该浏览器里登录 {site} 后无需其它操作**(在此之前不会产生新放行, 无证据种子按本地判据兜底) | 原始: {detail}"
    )


def login_expired_note(site: str, detail: str) -> str:
    """写进站点文件 `wave.notes` 的短句(报告与 WebUI 的 notes 都读它 —— 失败路径里唯一持久可见的痕迹)"""
    return f"{prefix(EVENT_LOGIN)} 本波未继续(页面是登录页, 需人工登录 {site}): {detail}"


def fetch_failed(site: str, failures: int, threshold: int, detail: str) -> str:
    """页面取数失败: 该档证据在此截断, 下周期自然重试(§5.2)"""
    return f"{prefix(EVENT_PARSE)} 站点 {site} | 页面取数失败(本波第 {failures} 次): {detail}(该档截断, 下周期自然重试)"


def page_changed(site: str, action: str, detail: str) -> str:
    """页面改版疑似: 表头缺失/字段缺失等结构性失效 ⇒ 需人工核对 HR 页结构"""
    return f"{prefix(EVENT_PARSE)} 站点 {site} | {action}: {detail}(请核对站点 HR 页是否改版)"


def order_broken(site: str, detail: str) -> str:
    """排序假设不成立(§3.4 强制早停): 页面行序与单调假设矛盾 ⇒ 该档立即停翻, 深处不可信"""
    return (f"{prefix(EVENT_PARSE)} 站点 {site} | 排序假设不成立({detail}): 该档强制早停"
            "(失效点之前数据有效) —— 请核对 HR 页是否改版")


def lane_persistent_failure(site: str, lane: str, streak: int, detail: str) -> str:
    """连续多波同档失效(§5.2 告警升级): 疑似改版, 建议走查"""
    return (
        f"{prefix(EVENT_PARSE)} 站点 {site} | 档位 {lane} 已连续 {streak} 波失效: {detail} | "
        f"疑似改版 —— 建议跑 --hr-once 走查核对页面结构(期间该档维持原状态, 命中照常)"
    )


#: 流转守恒下限(与 service.LANE_RETENTION_MIN 同值; 文案模块不反依赖 service, 就地声明)
LANE_RETENTION_MIN = 0.7


def retention_violation(site: str, ratio: float) -> str:
    """A 档流转守恒不达标(§5.3 首要防伪): 上波考察中行在本波留存率过低"""
    return (
        f"{prefix(EVENT_PARSE)} 站点 {site} | A 档流转守恒不达标(上波考察中行本波留存率 {ratio:.0%} < "
        f"{int(LANE_RETENTION_MIN * 100)}%): 批量「未列出」签发已冻结(防 A 段定向吞行); "
        "失踪个体维持管束走观察期"
    )


def zero_listing(site: str) -> str:
    """结构完好的零行波(§5.3): 不签发放行; 人工对账一次(确认戳)后零行波才可正常签发"""
    return (
        f"{prefix(EVENT_PARSE)} 站点 {site} | 清单为 0(结构完好): 不签发放行 —— 全部毕业/被清除? 还是改版空表? | "
        f"若确认账号的 HR 清单确实为空, 跑 --hr-confirm-empty {site}(或用 WebUI 站点卡片按钮)写一次性确认戳; "
        "清单再现非零行时确认戳自动失效"
    )


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


#: 流转守恒下限(与 service.LANE_RETENTION_MIN 同值; 文案模块不反依赖 service, 就地声明)
LANE_RETENTION_MIN = 0.7

__all__ = [
    "EVENT_LOGIN",
    "EVENT_PARSE",
    "EVENT_SILENCE",
    "LABELS",
    "channel_silent",
    "fetch_failed",
    "lane_persistent_failure",
    "login_expired",
    "login_expired_note",
    "order_broken",
    "page_changed",
    "prefix",
    "retention_violation",
    "summarize_sites",
    "zero_listing",
]
