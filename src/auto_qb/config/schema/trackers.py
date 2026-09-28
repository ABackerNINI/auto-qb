"""schema 站点段: 站点字段表与站点 hr 子段(HR 输出字段全局/站点共用)

hr_check 字段已移除(计划 26-09-27-1318 REV2): HR 在线核实的站点配置整体上收到
config.hr_check.sites(「HR 在线核实」分区的站点接入卡片), 站点分区只保留 HR 规则段。
旧键兼容层亦已废除(计划 26-09-27-1930): trackers.*.hr_check 由 schema 迁移链 v1→v2
一次性改写, 程序里不再有任何伺候旧键的分支(出现即校验报废除错)。
"""
from typing import Tuple
from .fields import Field

HR_OUTPUT_FIELDS: Tuple[Field, ...] = (
    Field(
        "add_tag",
        "触发后添加标签",
        "str",
        default="",
        help="进入 HR 管理(下载量/比例达条件)但还没达标时给种子打的标签; 支持 ${required_seeding_time} 变量; 留空 = 不打标"
    ),
    Field(
        "add_category",
        "触发后设置分类",
        "str",
        default="",
        help="同上, 但设置的是分类(一个种子只能有一个分类); 留空 = 不设置",
    ),
    Field(
        "overwrite_category",
        "覆盖已有分类",
        "bool",
        default="false",
        group_of="add_category",
        risk="开启后会覆盖人工设置的分类; 关闭时仅覆盖本程序上次自动设置的分类",
    ),
    Field(
        "add_tag_for_satisfied",
        "达标后添加标签",
        "str",
        default="",
        help="HR 达标(做满要求+额外时长, 或分享率达标)后打的标签, 相当于「HR 已完成」标记; 删掉后程序不会再自动添加",
    ),
    Field(
        "add_category_for_satisfied",
        "达标后设置分类",
        "str",
        default="",
        help="达标分支设置的分类; 留空 = 不设置",
    ),
    Field(
        "overwrite_category_for_satisfied",
        "达标后覆盖分类",
        "bool",
        default="false",
        group_of="add_category_for_satisfied",
        risk="开启后会覆盖人工设置的分类",
    ),
    Field(
        "exclude_tags",
        "排除标签(格式)",
        "pattern_list",
        default=[],
        risk="命中任一格式的种子会整个退出 HR 体系: 不打 HR 标签/分类、不参与在线核实判定、规则一律按未触发 —— 若种子实际仍在考核期将漏管",
        help="命中任一格式的种子不纳入 HR 管理; 支持 regex:/ 前缀与 :ignore_case 后缀(可组合), 例: noHR / 'regex:^skip.?hr:ignore_case'。"
        "与「HR 全局默认」里的同名配置取并集(两边都生效); 判定时现算 —— 在 qB 里加/删标签, 下一轮即生效或恢复管束。留空 = 不排除",
    ),
    Field(
        "exclude_categories",
        "排除分类(格式)",
        "pattern_list",
        default=[],
        risk="命中任一格式的分类会把该种子整个排除出 HR 体系(同「排除标签」的漏管风险)",
        help="种子分类命中任一格式即排除出 HR 管理; 支持 regex:/ 前缀与 :ignore_case 后缀。与「HR 全局默认」里的同名配置取并集; 留空 = 不排除",
    ),
)

TRACKER_HR_FIELDS: Tuple[Field, ...] = (
    Field(
        "required_seeding_time",
        "要求做种时长",
        "time",
        default="3D",
        required=True,
        help="站点要求的做种时长(如 3D = 3 天; 也支持 12H / 1.5D); 做满才算 HR 达标"
    ),
    Field("required_share_ratio", "要求分享率", "float", default="0", help="分享率达到该值也算 HR 达标(与做种时长满足其一即可); 0 = 不要求"),
    Field(
        "extra_seeding_time",
        "额外做种时间",
        "time",
        default="0H",
        unit_default="H",
        help="在要求时长之上再多做种这么久才判达标(留出缓冲, 避免刚好卡线被站点判未达标)"
    ),
    Field(
        "condition",
        "HR 触发条件",
        "ratio",
        default="80%",
        help="开始 HR 管理的门槛: 下载比例达(如 80%)或下载量达(如 10MiB)就进入 HR 管理; 辅种(无下载量)不会触发"
    ),
) + HR_OUTPUT_FIELDS

TRACKER_FIELDS: Tuple[Field, ...] = (
    Field(
        "domains",
        "站点域名",
        "str_list",
        default=[],
        required=True,
        help="该站点的 tracker 域名(含子域名自动匹配), 如 hhanclub.net; 每行一个; 必填",
    ),
    Field("tags", "站点标签", "str_list", default=[], help="该站点的种子自动添加这些标签; 第一个标签同时用作日志/界面里的站点名"),
    Field(
        "remove_tags",
        "删除标签格式",
        "pattern_list",
        default=[],
        help="从该站点的种子上删除匹配的标签; 支持 regex:/ 前缀与 :ignore_case 后缀(可组合), 例: regex:^BTS / 'M-Team:ignore_case'",
        risk="匹配到的标签会从该站点的种子中删除",
        tone="danger",
    ),
    Field(
        "groups",
        "站点分组",
        "str_list",
        default=[],
        help="给站点起的分组名(可多个), 供规则里「站点分组」条件筛选; 只是配置概念, 不会写到种子上; 组名随意填, 不用预先定义",
    ),
    Field(
        "upload_speed_limit",
        "单种上传限速",
        "speed",
        default="0KiB/s",
        help="该站点种子添加时即设置的上传限速; 0 = 不限速; 奇数值(如 2001KiB/s)视为你的手动限速, 本程序不覆盖",
    ),
    Field("download_speed_limit", "单种下载限速", "speed", default="0KiB/s", help="同上, 作用于下载方向; 0 = 不限速"),
    Field(
        "hr",
        "HR 规则",
        "object",
        default=None,
        optional=True,
        help="未配置该段 = 该站点不做 HR 管理(不打 HR 标签/分类)。"
        "HR 在线核实的启用已上收至「HR 在线核实」分区的站点接入卡片, 不在本分区",
        fields=TRACKER_HR_FIELDS
    ),
    Field(
        "rules",
        "引用的规则",
        "rules_ref",
        default=[],
        help="该站点要执行的规则: 填 @规则集 或 @规则集.规则名(可从下拉选, 也可直接粘贴); 留空 = 该站点不执行任何规则(不会回退为执行全部启用规则)"
    ),
    Field(
        "remove_similar_tags",
        "删除类似标签",
        "bool",
        default="false",
        help="未配置时回退全局「删除类似标签」的值; 自动清理仅大小写不同的重复标签",
    ),
)
