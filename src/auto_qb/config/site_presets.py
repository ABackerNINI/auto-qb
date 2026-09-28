"""内置 HR 站点档案表(计划 26-09-27-1318 REV2 §3.1; 绑定机制被 26-09-27-1930 重写为映射制)

站点 -> (adapter, web 域, announce 域, 页面路径, 种子下载路径, 翻页参数名) 的**代码写死**档案:
程序已知、人易配错的内容(页面形态 / 必须是登录后可达的 myhr 页 / 下载路径须含 {id} / 翻页参数
站点各不相同)不再进配置 —— 用户只在「HR 在线核实」分区点选启用 + 微调。

❗三命名空间纪律(计划 26-09-27-1930 §3.1, 本模块是判定单点):
- **web 域**(web_domain): 用户浏览器访问的站点主机, 仅派生 hr_page_url 与前端展示,
  **永不参与任何匹配**;
- **announce 域**(tracker_domain): 该站公开 tracker 主域(已知映射), 是**唯一允许匹配的空间** ——
  默认绑定 = 这个已知值在用户 trackers.*.domains(同命名空间)里查表;
- **tracker 条目名**: 用户配置的键名, 显式覆盖键 hr_check.sites.<id>.tracker 按字符串相等引用,
  无任何匹配语义。
一切「web 域 vs announce 域」的比对都是设计错误 —— 两域可能毫无从属关系(CarPT: web=carpt.net,
announce=tracker.carpt.net)。

落在 config 层而不是 hr 包: hr/adapters 依赖 config.models, config 是被依赖的下层,
反向 import 会成环(与 validation/sections.py 故意不复用 EXTENSION_ID_RE 同一先例)。hr 层只读它。

新增站点 = 在 hr/adapters 登记解析能力后, 在 SITE_PRESETS 立一条档案(登记点单点化, 见
hr/adapters/__init__.py docstring「新增站点的四种情形」)。
"""
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional


@dataclass(frozen=True)
class SiteHrPreset:
    """一个已支持站点的页面事实档案(preset id = hr_check.sites 的键名)"""

    preset_id: str
    adapter: str  # hr/adapters.ADAPTERS 里登记的解析器名
    web_domain: str  # web 命名空间: 浏览器访问的站点主机; 仅派生 hr_page_url, 永不参与匹配
    tracker_domain: str  # announce 命名空间: 已知映射(该站公开 tracker 主域); 默认绑定的查表键
    page_path: str  # HR 名单页路径(myhr 形态); 拼在 web 域后
    download_path: str  # 种子下载路径(须含 {id} 占位)
    page_param: str  # 翻页查询参数名
    #: 站点形态(v3, 计划 §6.1): list 清单型(有 HR 清单页, 参与取数) | none 全站型(无清单页,
    #: 不取数, 判定恒走行 4 本地兜底) —— partial/all 的 mode 分叉由它取代(站点事实, 非用户意愿)
    listing: str = "list"

    def page_url(self) -> str:
        """HR 页绝对地址 = https://{web 域}{page_path}; 与用户 domains 的写法完全无关"""
        return f"https://{self.web_domain}{self.page_path}"


#: 页面事实来源: btschool = nexusphp adapter docstring(2026-09-22 BTSchool 样张);
#: carpt = carpt adapter docstring(2026-09-27 CarPT 样张, status 参数已核)。
#: nexusphp 形态的翻页参数 `page` 标「待在线实测」(adapter docstring 注记), 错了改档案一行。
SITE_PRESETS: Dict[str, SiteHrPreset] = {
    "btschool":
        SiteHrPreset(
            preset_id="btschool",
            adapter="nexusphp",
            web_domain="pt.btschool.club",
            tracker_domain="pt.btschool.club",  # 两域同值(announce 域恰为 web 域)
            page_path="/myhr.php",
            download_path="/download.php?id={id}",
            page_param="page",
        ),
    "carpt":
        SiteHrPreset(
            preset_id="carpt",
            adapter="carpt",
            web_domain="carpt.net",
            tracker_domain="tracker.carpt.net",  # 两域无关 —— 映射制存在的理由
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
    """默认映射查表(计划 26-09-27-1930 §3.2): 档案已知 announce 域在用户 domains(同一命名空间)里
    查表, 返回命中的 tracker 名(按名字排序)

    命中规则: 用户域名 t 命中档案 tracker_domain d 当且仅当
    `t == d or t.endswith("." + d) or d.endswith("." + t)` —— 同命名空间内的双向子域容错,
    兼容用户配主域或 tracker 子域两种写法。命中 0 个或 >=2 个交校验层, 本函数只查不报
    (校验与 loader 两处共用同一判定, 不留第二份口径)。
    """
    d = preset.tracker_domain.strip().lower()
    return sorted(
        name for name, doms in domains_by_tracker.items()
        if any(t == d or t.endswith("." + d) or d.endswith("." + t) for t in _norm_domains(doms or ()))
    )


def preset_for_web_host(host: str) -> Optional[SiteHrPreset]:
    """按 web 主机精确定位档案(小写归一; 旧键 v1→v2 迁移用)

    旧键 trackers.*.hr_check 自带 hr_page_url, 其 host 与档案 web_domain 同属 web 命名空间,
    同空间精确比对定位档案 —— 不触碰 tracker 域名(计划 26-09-27-1930 §3.4)。
    """
    h = str(host).strip().lower()
    if not h:
        return None
    for preset in SITE_PRESETS.values():
        if preset.web_domain == h:
            return preset
    return None
