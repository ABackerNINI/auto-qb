"""`--hr-once` 真机只读走查: 跑一遍刷新管道, 只出报告, **不写文件、不联动 qB**(计划 §11 M2 / §12)。

用途与边界:
- 它**不加锁也就不可能写盘**(`persist=False`), 因此可以在正常实例运行期间安全地跑
  (锁会被正常实例持有 → 报告里如实显示"锁被持有/跳过", 这本身就是有用的信息);
- 它把「配置是否成立 / 站点文件落在哪 / 锁在该目录是否生效 / 解析是否还能读 / 覆盖证明是否成立」
  一次性摊开, 供用户确认多实例共享目录与站点改版;
- ❗它**不绕过零 cookie 边界**: 取数仍然只能经 `HrFetcher`(浏览器扩展通道)。
  `--hr-html-dir` 只是给走查用的**离线页面替身**(把保存下来的页面按 `<档位>.html` 放进目录),
  不会让后端自己发请求。
"""
import logging
import time
from pathlib import Path
from typing import List, Optional

from ..config.models import Config
from .channel import API_TASKS, describe_token_source, token_path
from .fetcher import HrChannelUnavailable, HrFetcher, NullFetcher
from .model import CHANNEL_OK, CHANNEL_SILENT
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
