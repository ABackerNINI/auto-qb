"""内置 HR 站点档案表(计划 26-09-27-1318 REV2 §3.1)

站点 -> (adapter, 页面路径, 种子下载路径, 翻页参数名, 域名) 的**代码写死**档案: 程序已知、
人易配错的内容(页面形态 / 必须是登录后可达的 myhr 页 / 下载路径须含 {id} / 翻页参数站点各不相同)
不再进配置 —— 用户只在「HR 在线核实」分区点选启用 + 微调, 页面事实以 adapter docstring 的
样张核对记录为准(scope 参数 / 表头名 / 列名等仍由 adapter 类自带, 档案只存 adapter 名)。

落在 config 层而不是 hr 包: hr/adapters 依赖 config.models, config 是被依赖的下层,
反向 import 会成环(与 validation/sections.py 故意不复用 EXTENSION_ID_RE 同一先例)。hr 层只读它。

新增站点 = 在 hr/adapters 登记解析能力后, 在 SITE_PRESETS 立一条档案(登记点单点化, 见
hr/adapters/__init__.py docstring「新增站点的四种情形」)。
"""
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Tuple


@dataclass(frozen=True)
class SiteHrPreset:
    """一个已支持站点的页面事实档案(preset id = hr_check.sites 的键名)"""

    preset_id: str
    adapter: str  # hr/adapters.ADAPTERS 里登记的解析器名
    domains: Tuple[str, ...]  # 与 trackers.<站点>.domains 求交集做绑定匹配(小写)
    page_path: str  # HR 名单页路径(myhr 形态); 拼在命中的站点域名后
    download_path: str  # 种子下载路径(须含 {id} 占位)
    page_param: str  # 翻页查询参数名
    # web 域 != tracker 域的站点用它覆盖 URL 主机(档案级硬编码, 不对用户暴露);
    # 空 = 用命中的 tracker 域名(首发两站均同域, BTSchool 有生产实证)
    page_domain: str = ""

    def page_url(self, tracker_domain: str) -> str:
        """HR 页绝对地址 = https://{web 域}{page_path}; web 域缺省取命中的 tracker 域名"""
        host = self.page_domain or tracker_domain.strip().lower()
        return f"https://{host}{self.page_path}"


#: 页面事实来源: btschool = nexusphp adapter docstring(2026-09-22 BTSchool 样张);
#: carpt = carpt adapter docstring(2026-09-27 CarPT 样张, status 参数已核)。
#: nexusphp 形态的翻页参数 `page` 标「待在线实测」(adapter docstring 注记), 错了改档案一行。
SITE_PRESETS: Dict[str, SiteHrPreset] = {
    "btschool":
        SiteHrPreset(
            preset_id="btschool",
            adapter="nexusphp",
            domains=("pt.btschool.club", ),
            page_path="/myhr.php",
            download_path="/download.php?id={id}",
            page_param="page",
        ),
    "carpt":
        SiteHrPreset(
            preset_id="carpt",
            adapter="carpt",
            domains=("carpt.net", ),
            page_path="/myhr.php",
            download_path="/download.php?id={id}",
            page_param="page",
        ),
}


def find_preset(preset_id: str) -> Optional[SiteHrPreset]:
    """按 preset id 查档案; 未登记返回 None(校验层报错并附已支持清单)"""
    return SITE_PRESETS.get(str(preset_id).strip().lower())


def _norm_domains(domains: Iterable[str]) -> List[str]:
    return [str(d).strip().lower() for d in domains if str(d).strip()]


def match_trackers(preset: SiteHrPreset, domains_by_tracker: Mapping[str, Iterable[str]]) -> List[str]:
    """档案域名与各站点 domains 求交集(小写精确匹配), 返回命中的 tracker 名(按名字排序)

    绑定规则(计划 §3.3): 恰好命中一个 = 绑定成功; 零个/多个由 validate_config fail-fast,
    本函数只做查找不报错(校验与 loader 两处共用同一判定, 不留第二份口径)。
    """
    want = set(preset.domains)
    return sorted(name for name, doms in domains_by_tracker.items() if want & set(_norm_domains(doms or ())))


def preset_for_domains(domains: Iterable[str]) -> Optional[SiteHrPreset]:
    """反向查找: 站点 domains 交集命中的档案(旧键 trackers.*.hr_check 等价迁移用)

    多个档案同时命中时返回 None —— 歧义由校验层报错, loader 只在无歧义时迁移。
    """
    have = set(_norm_domains(domains))
    hits = [p for p in SITE_PRESETS.values() if set(p.domains) & have]
    return hits[0] if len(hits) == 1 else None
