"""HR 只读报告: `--hr-once` 真机走查 / `--hr-status` 数据现状(计划 §11 M2 / §12)。

`--hr-once`(跑一遍刷新管道, 只出报告, **不写文件、不联动 qB**):
- 它**不加锁也就不可能写盘**(`persist=False`), 因此可以在正常实例运行期间安全地跑
  (锁会被正常实例持有 → 报告里如实显示"锁被持有/跳过", 这本身就是有用的信息);
- 它把「配置是否成立 / 站点文件落在哪 / 锁在该目录是否生效 / 解析是否还能读 / 覆盖证明是否成立」
  一次性摊开, 供用户确认多实例共享目录与站点改版;
- ❗它**不绕过零 cookie 边界**: 取数仍然只能经 `HrFetcher`(浏览器扩展通道)。
  `--hr-html-dir` 只是给走查用的**离线页面替身**(把保存下来的页面按 `<档位>.html` 放进目录),
  不会让后端自己发请求。

`--hr-status`(把**已落盘的数据**摊开, 连取数都不试):
- 回答「拉到的数据对不对 / 齐不齐 / 为什么没放行」—— 走查只能告诉你流程能通, 现状才能让你核对内容;
- 同样不加锁、不写盘, 读的是原子替换后的完整快照(`read_unlocked`)。
"""
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

from ..config.models import Config
from ..infra.utils import fmt_size
from .channel import API_TASKS, describe_token_source, token_path
from .fetcher import HrChannelUnavailable, HrFetcher, NullFetcher
from .model import (
    CHANNEL_OK,
    CHANNEL_SILENT,
    LANE_EXEMPT,
    LANE_SATISFIED,
    LANE_SCOPE,
    LANE_UNSATISFIED,
    HrSiteData,
)
from .ratelimit import fuse_active, quota_left
from .service import DIAGNOSTIC_MAX_WAIT, HrRefreshResult, HrRefreshService
from .store import instance_id

logger = logging.getLogger(__name__)


class LocalPageFetcher:
    """离线页面替身(仅走查用): 目录里 `<档位>.html` 当作该档首屏; 不提供 .torrent。"""
    def __init__(self, directory: str) -> None:
        self.dir = Path(directory)
        self.used: List[str] = []

    def get_text(self, url: str) -> str:
        scope = _scope_of(url)
        path = self.dir / f"{scope}.html"
        if not path.exists():
            raise HrChannelUnavailable(f"离线目录里没有 {path.name}({self.dir})")
        self.used.append(path.name)
        return path.read_text(encoding="utf-8", errors="replace")

    def get_bytes(self, url: str) -> bytes:
        raise HrChannelUnavailable("离线走查不取 .torrent(无法回填 infohash); 在线核实请走浏览器扩展通道")


def _scope_of(url: str) -> str:
    for part in url.split("?", 1)[-1].split("&"):
        if part.startswith("hrtype="):
            return part.split("=", 1)[1]
    return "?"


def build_fetcher(html_dir: Optional[str]) -> HrFetcher:
    """有离线目录则用页面替身, 否则用真通道(未落地时是 NullFetcher, 如实报「无通道」)"""
    if html_dir:
        return LocalPageFetcher(html_dir)
    return NullFetcher("本实例未启用取数通道 (hr_check.channel.enabled=false 或取数通道未落地)")


def run_hr_once(config: Config, html_dir: Optional[str] = None, out=None) -> int:
    """跑一遍各站点的刷新走查并打印报告; 返回进程退出码(0 = 出报告成功)"""
    import sys

    out = out or sys.stdout
    if not config.hr_check.enabled:
        print("hr_check.enabled=false: HR 在线核实未启用, 无可走查内容。", file=out)
        return 1
    site_confs = {name: tc.hr_check for name, tc in config.trackers.items() if tc.hr_check is not None}
    enabled = [name for name, conf in site_confs.items() if conf.enabled]
    if not enabled:
        print("没有任何站点配置 hr_check(mode != off), 无可走查内容。", file=out)
        return 1

    service = HrRefreshService(
        data_dir=config.data_dir,
        global_conf=config.hr_check,
        site_confs=site_confs,
        fetcher=build_fetcher(html_dir),
        owner=instance_id(),
        persist=False,  # 只读走查: 不写站点文件
        allow_fetch=True,
        # 走查是「把一轮跑完给人看」: 遇到间隔/配额门槛等满而不是放弃(上限 DIAGNOSTIC_MAX_WAIT)。
        # 单次最多等几分钟, 与「抓数据等几分钟可接受」一致; 配额到顶仍然会停
        sleeper=time.sleep,
    )

    print(f"HR 在线核实走查(只读, 不写盘) 共 {len(enabled)} 个站点: {', '.join(enabled)}", file=out)
    print(f"站点文件目录: {service.dir}(单次等待上限 {DIAGNOSTIC_MAX_WAIT:.0f}s)", file=out)
    _print_channel(config, service, out)
    print("-" * 92, file=out)
    started = time.time()
    results = service.refresh_all()
    for result in results:
        # 走查不写盘 ⇒ 已落盘视图必然是旧的; 用本轮内存快照预览, 否则报告会误显示「覆盖证明不成立」
        view = service.build_view_for(result.site, result.snapshot) if result.snapshot is not None else None
        _print_site(result, view, out)
    elapsed = time.time() - started
    print("-" * 92, file=out)
    print(f"合计 {len(results)} 个站点, 用时 {elapsed:.1f}s; 本次未写入任何文件。", file=out)
    if isinstance(service.fetcher, NullFetcher):
        print("提示: 未提供离线页面(--hr-html-dir), 且取数通道未启用 ⇒ 本轮只能确认配置/路径/锁状态。", file=out)
    return 0


def run_hr_status(config: Config, limit: int = 10, out=None) -> int:
    """`--hr-status` 只读现状报告: **不取数、不加锁、不写盘、不联动 qB**; 返回退出码(0 = 出报告成功)

    与 `--hr-once` 的分工: 走查证的是「流程能通」(它真去抓一轮), 现状证的是「**内容对不对**」——
    把已落盘的站点文件摊开给人核对(档位分布 / 下载量 / 剩余达标 / 放行 / 配额 / 熔断),
    以及回答「为什么没放行」(覆盖证明成不成立、最近一次刷新的 reason)。
    """
    import sys

    out = out or sys.stdout
    if not config.hr_check.enabled:
        print("hr_check.enabled=false: HR 在线核实未启用, 无可查看内容。", file=out)
        return 1
    site_confs = {name: tc.hr_check for name, tc in config.trackers.items() if tc.hr_check is not None}
    enabled = [name for name, conf in site_confs.items() if conf.enabled]
    if not enabled:
        print("没有任何站点配置 hr_check(mode != off), 无可查看内容。", file=out)
        return 1

    service = HrRefreshService(
        data_dir=config.data_dir,
        global_conf=config.hr_check,
        site_confs=site_confs,
        fetcher=NullFetcher("状态报告不取数"),
        owner=instance_id(),
        persist=False,
        allow_fetch=False,  # 本报告连「试着取一次」都不做: 要抓数据请看 --hr-once
    )
    now = time.time()
    print(f"HR 在线核实现状(只读: 不取数 / 不加锁 / 不写盘) 共 {len(enabled)} 个站点: {', '.join(enabled)}", file=out)
    print(f"站点文件目录: {service.dir}(每站点一个 JSON; 多实例共享同一账号时需共用同一目录)", file=out)
    _print_channel(config, service, out)
    print("-" * 92, file=out)
    for site in enabled:
        data, err = service.store(site).read_unlocked()
        view = service.build_view_for(site, data)
        _print_status_site(site, data, view, service, err, now, limit, out)
    print("-" * 92, file=out)
    print("提示: 以上全部读自**已落盘数据**(原子替换, 读到的是完整的一份), 未触发任何取数。", file=out)
    print("      要看「现在能不能取到数」跑 --hr-once; 要在线核实请让浏览器扩展保持开启。", file=out)
    return 0


def _print_status_site(
    site: str, data: HrSiteData, view, service: HrRefreshService, err, now: float, limit: int, out
) -> None:
    """单站点现状段: 刷新 / 数据 / 配额 / 熔断 / 明细"""
    conf = service.site_confs[site]
    limits = service.limits_for(site)
    channel = {CHANNEL_OK: "正常", CHANNEL_SILENT: "静默(长期没有成功刷新)"}.get(view.channel_state, "未启用")
    print(
        f"[{site}] 模式={conf.mode}  覆盖证明={'成立' if view.complete else '不成立'}  通道={channel}  "
        f"数据版本={data.revision}",
        file=out
    )
    print(f"    文件: {service.site_path(site)}" + (f"  ⚠ {err}" if err else ""), file=out)
    print(
        f"    刷新: 上次取数 {_ago(data.fetched_at, now)}  最近完整刷新 {_ago(data.refresh.last_success_ts, now)}  "
        f"本次数据有效期至 {_stamp(data.expires_at) if data.expires_at > 0 else '-'}",
        file=out
    )
    page = (
        f"档位 {','.join(data.refresh.scopes_done) or '-'}  页数 {data.refresh.pages_fetched}  "
        f"抓到 {data.refresh.entry_count} 行  缺字段 {data.refresh.missing_field_rate:.0%}"
    )
    print(f"    {page}  上次写入者 {data.writer_instance or '-'}(心跳 {_ago(data.writer_heartbeat, now)})", file=out)
    if data.refresh.reason:
        print(f"    最近一次刷新不完备的原因: {data.refresh.reason}", file=out)

    lanes = _lane_counts(data)
    pending = sum(1 for e in data.index.values() if e.active and not e.infohash_v1 and not e.infohash_v2)
    managed = len({e.tid for e in view.by_infohash.values()})
    print(
        f"    数据: 索引条目 {len(data.index)}(活跃 {sum(1 for e in data.index.values() if e.active)})  "
        f"档位 {LANE_SCOPE}={lanes.get(LANE_SCOPE, 0)} {LANE_SATISFIED}={lanes.get(LANE_SATISFIED, 0)} "
        f"{LANE_UNSATISFIED}={lanes.get(LANE_UNSATISFIED, 0)} {LANE_EXEMPT}={lanes.get(LANE_EXEMPT, 0)}(免罪)  "
        f"受管束种子 {managed} 个(infohash 键 {len(view.by_infohash)} 个: v1/v2 各一)",
        file=out
    )
    print(
        f"    已取种子 {len(data.downloaded)} 条  取种子失败 {len(data.fails)} 条  "
        f"待回填 infohash {pending} 条  放行记录 {len(data.verified)} 条",
        file=out
    )
    fuse = "熔断中至 " + _stamp(data.fuse.until_ts) + f"({data.fuse.reason})" if fuse_active(data.fuse, now) else "正常"
    print(
        f"    配额: 本小时 {data.quota.hour_count}/{limits.max_per_hour}  本天 {data.quota.day_count}/{limits.max_per_day}  "
        f"还能取 {quota_left(data.quota, limits, now)} 次  最近请求 {_ago(data.quota.last_fetch_ts, now)}  "
        f"最小间隔 {limits.min_interval:g}s",
        file=out
    )
    print(f"    熔断: {fuse}(连续失败 {data.fuse.failures})  时间窗: {limits.allow_window or '不限'}", file=out)
    _print_status_rows(data, limit, out)


def _print_status_rows(data: HrSiteData, limit: int, out) -> None:
    """明细表(按档位·剩余达标时间排序): 给人拿站点页面核对「拉到的对不对」"""
    rows = [e for e in data.index.values() if e.active]
    if not rows:
        print("    明细: (还没有数据 —— 先跑 --hr-once 或让扩展抓一轮)", file=out)
        return
    rows.sort(key=lambda e: (e.lane, -(e.downloaded_bytes or 0)))
    print(f"    明细(活跃 {len(rows)} 行, 按档位·下载量排序, 最多显示 {limit} 行):", file=out)
    print(f"        {'tid':>9}  {'档':<2} {'下载量':>9}  {'剩余达标':<10} {'名称':<40} infohash", file=out)
    for entry in rows[:limit]:
        if entry.satisfied_by_site:
            remain = "已达标"
        elif entry.remain_seconds is None:
            remain = "-"
        else:
            remain = _duration(entry.remain_seconds)
        name = _ellipsis(entry.name, 40)
        ihash = entry.infohash_v1 or entry.infohash_v2
        print(
            f"        {entry.tid:>9}  {entry.lane:<2} {fmt_size(entry.downloaded_bytes or 0):>9}  {remain:<10} "
            f"{name:<40} {ihash[:12] or '-'}",
            file=out
        )
    if len(rows) > limit:
        print(f"        ...(还有 {len(rows) - limit} 行未显示; 站点文件里是完整数据)", file=out)


def _lane_counts(data: HrSiteData) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for entry in data.index.values():
        counts[entry.lane] = counts.get(entry.lane, 0) + 1
    return counts


def _duration(seconds: float) -> str:
    seconds = int(max(0, seconds))
    if seconds >= 86400:
        return f"{seconds // 86400}d{seconds % 86400 // 3600}h"
    if seconds >= 3600:
        return f"{seconds // 3600}h{seconds % 3600 // 60}m"
    if seconds >= 60:
        return f"{seconds // 60}m{seconds % 60}s"
    return f"{seconds}s"


def _ago(ts: float, now: float) -> str:
    """相对时间(报告给人看: 绝对时间戳要心算)"""
    if not ts or ts <= 0:
        return "从未"
    return _duration(now - ts) + "前"


def _stamp(ts: float) -> str:
    return time.strftime("%m-%d %H:%M:%S", time.localtime(ts)) if ts and ts > 0 else "-"


def _ellipsis(text: str, width: int) -> str:
    text = text or ""
    return text if len(text) <= width else text[:width - 1] + "…"


def _print_channel(config: Config, service: HrRefreshService, out) -> None:
    """通道自检段(计划 §7): 端点 / 密钥来源 / 共享目录 —— 都不含密钥内容"""
    conf = config.hr_check
    channel = conf.channel
    state = "启用" if channel.enabled else "未启用(本实例无取数能力, 只会读共享数据)"
    print(f"取数通道: {state}", file=out)
    print(
        f"    端点: http://127.0.0.1:{channel.port}{API_TASKS}   轮询节奏: {conf.poll_interval:g}s   "
        f"等回传上限: {channel.request_timeout:g}s",
        file=out
    )
    origin = f"只放行扩展 {channel.extension_id}" if channel.extension_id else "放行任意扩展 origin(靠 token 鉴权)"
    print(
        f"    密钥来源: {describe_token_source(channel.token, config.data_dir)}"
        f"({token_path(config.data_dir)})   {origin}",
        file=out
    )
    if conf.shared_dir:
        print(f"    共享目录: {conf.shared_dir}(多实例共用同一份站点数据)", file=out)
    else:
        print(f"    共享目录: 未配置 ⇒ 站点文件落 {service.dir}; 多实例共享同一账号时需指向同一目录"
              "(云同步盘不可用)", file=out)


def _print_site(result: HrRefreshResult, view, out) -> None:
    print(f"[{result.site}] {result.action} — {result.reason or '正常'}", file=out)
    print(f"    文件: {result.path}    锁自检: {'可写' if result.lock_ok else '只读退化(锁疑似不生效)'}", file=out)
    print(
        f"    档位: {','.join(result.scopes_done) or '-'}  页数: {result.pages_fetched}  "
        f"条目: {result.entries}(新增 {result.entries_new})  取种子: {result.torrents_fetched} 失败: {result.torrents_failed}"
        f"  放行记录: {result.verified_count}",
        file=out
    )
    if view is not None:
        channel = {CHANNEL_OK: "正常", CHANNEL_SILENT: "静默"}.get(view.channel_state, view.channel_state)
        print(
            f"    视图: 模式={view.mode} 覆盖证明={'成立' if view.complete else '不成立'} "
            f"最近成功刷新={view.last_success_ts:.0f} 受管束={len(view.by_infohash)} 放行={len(view.verified)} "
            f"通道={channel}",
            file=out
        )
