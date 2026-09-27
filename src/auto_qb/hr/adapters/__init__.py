"""站点 adapter 注册表与工厂。

新增站点的三种情形:
1. **NexusPHP 标准形态**(`myhr.php` 九列表格)—— 只需在 trackers.<site>.hr_check 里配 URL / 路径即可,
   不用写代码; 这是绝大多数 PT 站的形态。
2. **myhr 表格形态但状态参数 / 表头名不同的变体**(如 CarPT)—— 写一个薄 adapter 注入
   scope_param / scope_values / header_key / column_names(见 carpt.py), 并在此登记。
3. **站点有更便宜的来源**(JSON 接口 / 逐种 HR 标记)—— 写一个 adapter 并在此登记, 接口不变,
   且可跳过 §5 的 .torrent 下载成本。
"""
from typing import Callable, Dict, Optional, Tuple

from ...config.models import SiteHrCheckConfig
from .base import HrAdapter, ParsedScope
from .carpt import COLUMN_NAMES as CARPT_COLUMNS
from .carpt import HEADER_KEY as CARPT_HEADER_KEY
from .carpt import SCOPE_STATUS as CARPT_SCOPE_STATUS
from .carpt import CarPtMyhrAdapter
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
    "carpt":
        lambda site, conf: CarPtMyhrAdapter(
            site,
            hr_page_url=conf.hr_page_url,
            download_path=conf.download_path,
            scopes=tuple(conf.hr_page_scopes),
            page_param=conf.page_param,
            scope_param="status",
            scope_values=CARPT_SCOPE_STATUS,
            header_key=CARPT_HEADER_KEY,
            column_names=CARPT_COLUMNS,
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
