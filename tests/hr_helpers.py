"""HR 在线核实测试用的共享夹具(非测试文件, 不被 pytest 收集)。

四件事: 1. 读脱敏页面 fixture; 2. 按行构造 myhr 页面(行为测试用, 恰好裁剪出需要的行);
3. 构造合法 .torrent 字节(测试 infohash 用, 不依赖外部样本); 4. 假取数通道 ——
按 URL/scope 返回 HTML、按 tid 返回 .torrent, 并记录调用序列(用于验证防重取与限速)。
"""
import pathlib
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from auto_qb.config.models import HrCheckConfig, SiteHrCheckConfig
from auto_qb.hr.fetcher import HrChannelQuota, HrFetchError, HrLoginExpired

FIXTURE_DIR = pathlib.Path(__file__).parent / "fixtures" / "hr"

LOGIN_PAGE = (
    '<html><body><form action="takelogin.php" method="post">'
    '<input name="username"><input type="password" name="password"></form></body></html>'
)

CHALLENGE_PAGE = (
    '<html><head><title>Just a moment...</title></head>'
    '<body><div id="cf-chl-widget">Checking your browser before accessing</div></body></html>'
)

REVISED_PAGE = "<html><body><h1>H&amp;R记录</h1><p>站点改版了, 没有 HR 表格</p></body></html>"

#: 只有表头、没有数据行 —— 「账号确实没有 HR 种子」的合法空结果(区别于改版)
EMPTY_TABLE_PAGE = """
<div><table class="main"><tbody><tr><td class="embedded"><table width="100%"><tbody><tr>
<td class="colhead">HR编号</td><td class="colhead">种子名称</td><td class="colhead">上传量</td>
<td class="colhead">下载量</td><td class="colhead">分享率</td><td class="colhead">还需做种时间</td>
<td class="colhead">完成时间</td><td class="colhead">剩余达标时间</td><td class="colhead">20000魔力值免罪</td>
</tr></tbody></table><p align="center"><font class="gray"><b>0&nbsp;-&nbsp;0</b></font></p>
</td></tr></tbody></table></div>
"""


def load_fixture(name: str) -> str:
    """读脱敏页面 fixture(见 tests/fixtures/hr/)"""
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def bencode_bytes(text: str) -> bytes:
    return f"{len(text.encode())}:".encode() + text.encode()


def torrent_blob(
    name: str = "example.bin",
    length: int = 1024,
    private: bool = True,
    extra_info_keys: Iterable[Tuple[str, bytes]] = ()
) -> bytes:
    """构造一份最小合法 .torrent。

    刻意**不排序**顶层键 —— 被测代码不依赖键序(它只用原始字节切片算 hash)。
    private=True 会**在 info 之后**再加一个顶层键, 专门覆盖「切片不能粗切到结尾」的坑。
    """
    info = b"d6:lengthi" + str(length).encode() + b"e4:name" + bencode_bytes(name)
    for key, raw in extra_info_keys:
        info += bencode_bytes(key) + raw
    info += b"12:piece lengthi16384e6:pieces20:" + b"\x00" * 20 + b"e"
    tail = b"7:privatei1e" if private else b""
    return b"d8:announce25:http://t.example/announce4:info" + info + tail + b"e"


def carpt_counter_bar(surveying: int, unsatisfied: int, limit: int) -> str:
    """CarPT 页头计数条(2026-09-29 样张原文形态, 计划 26-09-29-2036 §2.1 摘要形)。

    标签在 <a> 外、数字段被 [] 包裹, 未达标位红字, 3 个数 = 考察中 / 未达标 / 上限。
    M2 carpt 覆写 parse_counters 的解析对象; 引擎行为测试仍经 adapter 覆写上交合成值。
    """
    return (
        '<font class="color_bonus">H&amp;R: </font> '
        f'[<a href="https://carpt.net/myhr.php">{surveying}/'
        f'<font color="red">{unsatisfied}</font>/{limit}</a>]'
    )


def btschool_counter_bar(surveying: int, unsatisfied: int) -> str:
    """BTSchool 页头计数条(2026-09-29 样张原文形态): 标签在 <a> 内, 未达标位红色加粗 span。

    2 个数 = 考察中 / 未达标。span 的 style 属性里带数字(rgb(255, 0, 0)) ——
    解析必须先剥标签再取数, 本夹具专门钉住这个坑。
    """
    return (
        '<a href="https://pt.btschool.club/myhr.php">'
        '<font class="color_bonus">&nbsp;&nbsp;H&amp;R:</font>'
        f'{surveying}/<span style="color: rgb(255, 0, 0); font-weight: bold;">{unsatisfied}</span></a>'
    )


def myhr_page(
    rows: Sequence[Tuple[int, str, str, str, str, str, str, str]],
    has_next: bool = False,
    *,
    counter_bar_html: str = ""
) -> str:
    """构造与真实 myhr.php 同构的 HR 页(含 <td class="embedded"> 包裹表)。

    rows 每项: (tid, 名称, 上传量, 下载量, 分享率, 还需做种, 完成时间, 剩余达标)
    counter_bar_html: 可选计数条片段(见 counter_bar), 插在表格前 —— 计数站点任意页都带。
    解析测试用真实样张 fixture; 行为测试用本构造器裁剪出恰好需要的行。
    """
    body = ""
    for tid, name, up, down, ratio, need, done, remain in rows:
        body += (
            "<tr>"
            f'<td class="rowfollow nowrap" align="center">{tid}</td>'
            f'<td class="rowfollow" align="left"><a href="https://pt.example.com/details.php?id={tid}">{name}</a></td>'
            f'<td class="rowfollow nowrap" align="center">{up}</td>'
            f'<td class="rowfollow nowrap" align="center">{down}</td>'
            f'<td class="rowfollow nowrap" align="center">{ratio}</td>'
            f'<td class="rowfollow nowrap" align="center">{need}</td>'
            f'<td class="rowfollow nowrap" align="center">{done}</td>'
            f'<td class="rowfollow nowrap" align="center">{remain}</td>'
            '<td class="rowfollow nowrap" align="center">'
            f'<a href="https://pt.example.com/myhr.php?hrtype=C&amp;USEBOUNS={tid}"><b>购买免罪</b></a></td>'
            "</tr>"
        )
    next_link = (
        '<a href="https://pt.example.com/myhr.php?hrtype=A&amp;page=1"><b>下一页&nbsp;&gt;&gt;</b></a>'
        if has_next else '<font class="gray"><b title="Alt+Pagedown">下一页&nbsp;&gt;&gt;</b></font>'
    )
    return (
        '<h1>H&amp;R记录</h1>' + counter_bar_html +
        '<table class="main"><tbody><tr><td class="embedded"><table width="100%"><tbody><tr>'
        '<td class="colhead">HR编号</td><td class="colhead">种子名称</td><td class="colhead">上传量</td>'
        '<td class="colhead">下载量</td><td class="colhead">分享率</td><td class="colhead">还需做种时间</td>'
        '<td class="colhead">完成时间</td><td class="colhead">剩余达标时间</td>'
        '<td class="colhead">20000魔力值免罪</td>' + "</tr>" + body + "</tbody></table><p>" + next_link +
        "</p></td></tr></tbody></table>"
    )


def row(
    tid: int,
    name: str = "",
    *,
    down: str = "10.00 GB",
    up: str = "0.00 KB",
    ratio: str = "0.500",
    need: str = "1:00:00",
    done: str = "2026-09-20 10:00:00",
    remain: str = "2天00:00:00"
):
    """一行 HR 记录的快捷构造(默认值覆盖常见形态)"""
    return (tid, name or f"EXAMPLE {tid}", up, down, ratio, need, done, remain)


class FakeFetcher:
    """假取数通道: 按 URL(优先)或 scope 给 HTML, 按 tid 给 .torrent。"""
    def __init__(
        self,
        pages: Optional[Dict[str, str]] = None,
        blobs: Optional[Dict[int, bytes]] = None,
        *,
        fail_text_at: Optional[Dict[str, str]] = None,
        fail_bytes_at: Optional[Dict[int, str]] = None,
        #: scope -> 秒: 取页抛带 retry_after 的 HrFetchError(站点明确指令等待, H1 回归用)
        retry_after_at: Optional[Dict[str, float]] = None,
        #: tid -> 秒: 取 .torrent 抛带 retry_after 的 HrFetchError(下载路径上抛波级, H1 回归用)
        retry_bytes_at: Optional[Dict[int, float]] = None,
        #: scope 集合: 取页抛 HrLoginExpired(扩展回传登录页语义, M1 回归用)
        login_at: Iterable[str] = (),
        quota: bool = False,
    ) -> None:
        self.pages = dict(pages or {})
        self.blobs = dict(blobs or {})
        self.fail_text_at = dict(fail_text_at or {})
        self.fail_bytes_at = dict(fail_bytes_at or {})
        self.retry_after_at = dict(retry_after_at or {})
        self.retry_bytes_at = dict(retry_bytes_at or {})
        self.login_at = set(login_at)
        #: True = 每次都抛 HrChannelQuota(模拟扩展侧硬上限拒发, 与「取数失败」区分开)
        self.quota = quota
        self.text_calls: List[str] = []
        self.byte_calls: List[str] = []

    @staticmethod
    def scope_of(url: str) -> str:
        for part in url.split("?", 1)[-1].split("&"):
            if part.startswith("hrtype="):
                return part.split("=", 1)[1]
        return ""

    @staticmethod
    def tid_of(url: str) -> int:
        for part in url.split("?", 1)[-1].split("&"):
            if part.startswith("id="):
                try:
                    return int(part.split("=", 1)[1])
                except ValueError:
                    return -1
        return -1

    def get_text(self, url: str) -> str:
        self.text_calls.append(url)
        if self.quota:
            raise HrChannelQuota("扩展侧硬上限挡下(HR 页访问 本小时达硬上限 10 次)")
        scope = self.scope_of(url)
        if scope in self.login_at:
            raise HrLoginExpired(f"扩展取到登录页而非内容(scope={scope})")
        if scope in self.retry_after_at:
            raise HrFetchError(f"站点限速(scope={scope})", retry_after=self.retry_after_at[scope])
        if scope in self.fail_text_at:
            raise HrFetchError(self.fail_text_at[scope])
        if url in self.pages:
            return self.pages[url]
        if scope in self.pages:
            return self.pages[scope]
        raise HrFetchError(f"假通道没有配置 scope={scope} 的页面: {url}")

    def get_bytes(self, url: str) -> bytes:
        self.byte_calls.append(url)
        if self.quota:
            raise HrChannelQuota("扩展侧硬上限挡下(.torrent 下载 本小时达硬上限 50 次)")
        tid = self.tid_of(url)
        if tid in self.retry_bytes_at:
            raise HrFetchError(f"站点限速(tid={tid})", retry_after=self.retry_bytes_at[tid])
        if tid in self.fail_bytes_at:
            raise HrFetchError(self.fail_bytes_at[tid])
        if tid not in self.blobs:
            raise HrFetchError(f"假通道没有配置 tid={tid} 的 .torrent")
        return self.blobs[tid]


class Clock:
    """可推进的假时钟(测试有效期与频控, 不真等)"""
    def __init__(self, start: float = 1_700_000_000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def site_conf(**overrides) -> SiteHrCheckConfig:
    """站点级 hr_check 配置(测试默认: enabled / 清单型 / 12H 周期; 页面事实为派生字段)"""
    base = dict(
        enabled=True,
        tracker="example",
        hr_page_url="https://pt.example.com/myhr.php",
        download_path="/download.php?id={id}",
        page_param="page",
        listing="list",
        required_seeding_time=2 * 86400.0,
        refresh_interval=12 * 3600.0,
    )
    base.update(overrides)
    return SiteHrCheckConfig(**base)


def global_conf(**overrides) -> HrCheckConfig:
    """全局 hr_check 配置(测试默认: 零间隔 / 宽日额 / 大页上限, 便于在假时钟下推进)"""
    base = dict(
        enabled=True,
        min_interval=0.0,
        max_requests_per_day=100000,
        max_pages_per_wave=100,
    )
    base.update(overrides)
    return HrCheckConfig(**base)


def anchor(
    *,
    added_on: float = 0.0,
    downloaded: int = 1 << 30,
    completion_on: float = -1,
    progress: float = 1.0,
    seeding_time: int = 0,
    name: str = "",
) -> "HrAnchor":
    """本地种子锚点快捷构造(默认: 本机下载完成形态 —— completion_on 未设时按需覆盖)"""
    from auto_qb.hr.resolve import HrAnchor

    return HrAnchor(
        added_on=int(added_on),
        downloaded=downloaded,
        completion_on=int(completion_on),
        progress=progress,
        seeding_time=seeding_time,
        name=name,
    )
