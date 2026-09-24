"""站点 adapter 注册表与工厂。

新增站点的两种情形:
1. **NexusPHP 形态**(`myhr.php` 九列表格)—— 只需在 trackers.<site>.hr_check 里配 URL / 路径即可,
   不用写代码; 这是绝大多数 PT 站的形态。
2. **站点有更便宜的来源**(JSON 接口 / 逐种 HR 标记)—— 写一个 adapter 并在此登记, 接口不变,
   且可跳过 §5 的 .torrent 下载成本。
"""
from typing import Callable, Dict, Optional, Tuple

from ...config.models import SiteHrCheckConfig
from .base import HrAdapter, ParsedScope
from .nexusphp import NexusPhpMyhrAdapter

AdapterFactory = Callable[[str, SiteHrCheckConfig], HrAdapter]

#: adapter 名 -> 工厂。名字来自站点配置的 `adapter` 键(缺省 `nexusphp`)
ADAPTERS: Dict[str, AdapterFactory] = {
    "nexusphp":
        lambda site, conf: NexusPhpMyhrAdapter(
            site,
            hr_page_url=conf.hr_page_url,
            download_path=conf.download_path,
            scopes=tuple(conf.hr_page_scopes),
            page_param=conf.page_param,
        ),
}

DEFAULT_ADAPTER = "nexusphp"


def available_adapters() -> Tuple[str, ...]:
    """已登记的 adapter 名(供配置报错时提示可用值)"""
    return tuple(sorted(ADAPTERS))


def build_adapter(site: str, conf: SiteHrCheckConfig) -> Optional[HrAdapter]:
    """按配置构造 adapter; adapter 名未登记返回 None(由调用方报错并跳过该站)"""
    factory = ADAPTERS.get(conf.adapter or DEFAULT_ADAPTER)
    if factory is None:
        return None
    return factory(site, conf)


__all__ = [
    "ADAPTERS",
    "DEFAULT_ADAPTER",
    "HrAdapter",
    "ParsedScope",
    "available_adapters",
    "build_adapter",
]
