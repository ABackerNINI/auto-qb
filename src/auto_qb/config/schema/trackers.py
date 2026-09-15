"""schema 站点段: 站点字段表与站点 hr 子段(HR 输出字段全局/站点共用)"""
from typing import Tuple
from .fields import Field

HR_OUTPUT_FIELDS: Tuple[Field, ...] = (
    Field(
        "add_tag",
        "触发后添加标签",
        "str",
        default="",
        help="已触发 HR(下载量/比例达条件)但尚未满足做种时长/分享率时自动添加的标签; 支持 ${required_seeding_time} 变量; 留空 = 不添加"
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
        help="做种时长已达要求 + 额外时间(或分享率达标)后添加的标签; 用于标记“HR 已完成”; 可自行删除, 本程序不会再添加",
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
)

TRACKER_HR_FIELDS: Tuple[Field, ...] = (
    Field(
        "required_seeding_time",
        "要求做种时长",
        "time",
        default="3D",
        required=True,
        help="站点要求的做种时长(如 3D = 3 天 / 12H / 1.5D); 达到该时长才算满足 HR"
    ),
    Field("required_share_ratio", "要求分享率", "float", default="0", help="上传量/下载量 达到该值也算满足 HR(与做种时长二选一); 0 = 不要求"),
    Field(
        "extra_seeding_time",
        "额外做种时间",
        "time",
        default="0H",
        unit_default="H",
        help="缓冲量: 要求时长 + 额外时长 才判定达标(避免刚好卡在边界时被站点判定未达标)"
    ),
    Field(
        "condition", "HR 触发条件", "ratio", default="80%", help="下载比例(如 80%)或下载量(如 10MiB)达到该值即视为需要 HR 管理; 注意辅种(无下载量)不触发"
    ),
) + HR_OUTPUT_FIELDS

TRACKER_FIELDS: Tuple[Field, ...] = (
    Field(
        "domains",
        "站点域名",
        "str_list",
        default=[],
        required=True,
        help="按 hostname 精确匹配(含子域名), 例: hhanclub.net; 必填; 每行一个",
    ),
    Field("tags", "站点标签", "str_list", default=[], help="该站点的种子自动添加这些标签; 第一个标签同时用作日志/界面里的站点名"),
    Field(
        "remove_tags",
        "删除标签格式",
        "pattern_list",
        default=[],
        help="支持 regex: 前缀与 :ignore_case 后缀(可组合), 例: regex:^BTS / 'M-Team:ignore_case'",
        risk="匹配到的标签会从该站点的种子中删除",
    ),
    Field(
        "groups",
        "站点分组",
        "str_list",
        default=[],
        help="站点的分组归属(可多个, 供规则 tracker_group 条件筛选); 配置层概念, 不写种子、不加标签 —— 与 grouping 段的辅种种子分组无关; 组名自由填写, 无需预定义",
    ),
    Field(
        "upload_speed_limit",
        "单种上传限速",
        "speed",
        default="0KiB/s",
        help="种子添加时写入 qB 的单种限速; 0 = 不限速; 奇数值(如 2001KiB/s)视为手动设置, 本程序不覆盖",
    ),
    Field("download_speed_limit", "单种下载限速", "speed", default="0KiB/s", help="同上, 作用于下载; 0 = 不限速"),
    Field(
        "hr",
        "HR 规则",
        "object",
        default=None,
        optional=True,
        help="未配置该段 = 该站点不做 HR 管理(不打 HR 标签/分类)",
        fields=TRACKER_HR_FIELDS
    ),
    Field(
        "rules",
        "引用的规则",
        "rules_ref",
        default=[],
        help="填写 @规则集 或 @规则集.规则名(可从右侧下拉选, 也可直接粘贴); 留空 = 该站点不执行任何规则——不会回退为\"执行全部启用规则\""
    ),
    Field(
        "remove_similar_tags",
        "删除类似标签",
        "bool",
        default="false",
        help="未配置时回退全局 自动化.删除类似标签 的值; 删除仅大小写不同的同名标签",
    ),
)
