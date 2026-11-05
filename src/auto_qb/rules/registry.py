"""条件/动作/编排块单一注册表: 三元组条目 + 工厂 + 派生访问器(plan 26-11-01-0106 W5)

单一 registry 收口(G9/G10/G11/G13): 统一注册条目 = **三元组**
`类型名 -> 执行函数 + schema 声明 + 文档片段`, 条件/动作/choose 编排块统一入册;
深度校验器分发(config.validation)与触发器 x 动作兼容表、watch_fields 取值域均从本表
条目声明**派生**(派生消费见 accessors 节与 config/validation/rules.py)。

导入方向(R6 定案 a): schema 声明留在 config.schema(声明作者单点不变), 本表条目**按名引用**
(schema_ref), 派生消费走**延迟访问器**(函数内 import)躲 rules->config 导入环
(rules/base.py 顶层有 `from ..config import`)—— 本模块顶层零项目内依赖。
G13 拍板: 未用条目全部保留, registry 化只做派生收口不删条目。

条目形态(PluginEntry):
- cls:            执行函数(插件类: 条件 match(ctx) / 动作 execute(ctx));
- schema_ref:     schema 声明按名引用(config/schema/rules.py 的 Plugin.name, 缺省同名);
- decl:           自带声明(仅新条目尚未进 config.schema 声明表时用, 如测试/演示路径;
                  内置 25 插件一律走按名引用, 声明零复制);
- doc:            文档片段(空 = 取 schema 声明的 help, 同样不复制);
- validator:      深度校验器名(实现单点在 config/validation/rules.py _SPEC_VALIDATOR_IMPLS,
                  分发表按本声明派生; 空 = 无深度校验);
- watchable_field: 条件侧声明「可被 on_torrent_field_changed 监听的种子字段」
                  (G10: watch_fields 取值域从本声明派生; v1 = tags/category, 与条件名同源);
- deleted_ok:     动作侧声明「on_torrent_deleted 触发下允许使用」
                  (G11: 触发器 x 动作兼容声明进条目; 删除后种子无活现场, 仅只读类动作适用)。

幂等与键面: CONDITIONS/ACTIONS 名称字典保持既有形态(工厂与既有消费面零改动),
条目字典按注册顺序与其平行; 重复注册 = 后者覆盖(与旧装饰器行为一致)。
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Tuple

CONDITIONS: dict = {}
ACTIONS: dict = {}

# 三元组条目(与上两个名称字典平行, 同序注册): 名称 -> 条目
CONDITION_ENTRIES: Dict[str, "PluginEntry"] = {}
ACTION_ENTRIES: Dict[str, "PluginEntry"] = {}

# choose 编排块(W3-B)等非插件条目: 名称 -> BlockEntry(执行内联在 Rule.process, 无独立工厂)
BLOCK_ENTRIES: Dict[str, "BlockEntry"] = {}


@dataclass(frozen=True)
class PluginEntry:
    """统一注册条目(三元组): 类型名 -> 执行函数 + schema 声明(按名引用/自带) + 文档片段

    声明与文档的解析都是**延迟访问器**(plugin/doc_text, 函数内 import config.schema),
    本模块不持有 config 侧对象 —— 导入方向 R6(a), 躲 rules->config 顶层导入环。
    """

    name: str
    kind: str  # "condition" | "action"
    cls: type  # 执行函数(插件类)
    schema_ref: str = ""  # schema 声明按名引用(config/schema/rules.py Plugin.name); 空 = 同名
    decl: Any = None  # 自带声明(新条目未进声明表时的兜底路径; 内置插件不使用)
    doc: str = ""  # 文档片段; 空 = 取 schema 声明 help(不复制)
    validator: str = ""  # 深度校验器名(实现单点 config/validation/rules.py); 空 = 无
    watchable_field: str = ""  # 条件: 可监听字段声明(G10 watch_fields 取值域派生源)
    deleted_ok: bool = False  # 动作: on_torrent_deleted 下允许(G11 兼容声明)

    def plugin(self) -> Any:
        """延迟访问器: 解析条目的 schema 声明(按名引用 config.schema; 自带 decl 直返)

        按名未命中 = registry 与 config.schema 声明表脱节 —— 直接 KeyError 显式炸出,
        守卫测试(test_registry_derived)与 cover_registry 族在导入期即对账, 不静默缺省。
        """
        if self.decl is not None:
            return self.decl
        from ..config.schema.rules import ACTION_PLUGINS, CONDITION_PLUGINS

        table = CONDITION_PLUGINS if self.kind == "condition" else ACTION_PLUGINS
        for p in table:
            if p.name == (self.schema_ref or self.name):
                return p
        raise KeyError(
            f"registry 条目 '{self.name}'({self.kind}) 的 schema 声明引用 "
            f"'{self.schema_ref or self.name}' 未在 config.schema 声明表中登记"
        )

    def doc_text(self) -> str:
        """延迟访问器: 文档片段(显式 doc 优先, 否则取 schema 声明 help —— 声明零复制)"""
        if self.doc:
            return self.doc
        return str(self.plugin().help or "")


@dataclass(frozen=True)
class BlockEntry:
    """编排块条目(choose 等): 无插件工厂, 执行内联在 Rule.process

    executor: 运行时形态类(由 rules.base 在模块加载期注册 —— base 顶层 import registry,
    registry 反向引用 base 会成环, 故 choose 条目在 base 侧入册);
    keys_ref: 键面声明按名引用(config.compat 的键面常量名, 延迟访问器 block_keys 解析)。
    """

    name: str
    executor: Any
    doc: str = ""
    keys_ref: str = ""

    def block_keys(self) -> tuple:
        """延迟访问器: 编排块键面(按名引用 config.compat 常量)"""
        from ..config import compat

        return tuple(getattr(compat, self.keys_ref))


def register_condition(cls: type | None = None,
                       *,
                       validator: str = "",
                       watchable_field: str = "",
                       decl: Any = None) -> Callable[[type], type] | type:
    """装饰器: 注册条件插件(类需有 name 属性和 match(ctx) 方法)

    可选声明: validator = 深度校验器名(分发派生源); watchable_field = 可监听字段(G10);
    decl = 自带 schema 声明(缺省按名引用 config.schema)。裸用 @register_condition 兼容。
    """
    def wrap(c: Any) -> type:
        CONDITIONS[c.name] = c
        CONDITION_ENTRIES[c.name] = PluginEntry(
            name=c.name,
            kind="condition",
            cls=c,
            validator=validator,
            watchable_field=watchable_field,
            decl=decl,
        )
        return c

    return wrap(cls) if cls is not None else wrap


def register_action(
    cls: type | None = None,
    *,
    validator: str = "",
    deleted_ok: bool = False,
    doc: str = "",
    decl: Any = None
) -> Callable[[type], type] | type:
    """装饰器: 注册动作插件(类需有 name 属性和 execute(ctx) 方法)

    可选声明: validator = 深度校验器名; deleted_ok = on_torrent_deleted 兼容声明(G11);
    doc/decl = 文档片段与自带声明(缺省按名引用 config.schema)。裸用 @register_action 兼容。
    """
    def wrap(c: Any) -> type:
        ACTIONS[c.name] = c
        ACTION_ENTRIES[c.name] = PluginEntry(
            name=c.name,
            kind="action",
            cls=c,
            validator=validator,
            deleted_ok=deleted_ok,
            doc=doc,
            decl=decl,
        )
        return c

    return wrap(cls) if cls is not None else wrap


def register_block(name: str, executor: Any, doc: str = "", keys_ref: str = "") -> None:
    """注册编排块条目(choose 等, 由 rules.base 模块加载期调用 —— 执行形态类在 base 侧)"""
    BLOCK_ENTRIES[name] = BlockEntry(name=name, executor=executor, doc=doc, keys_ref=keys_ref)


def create_condition(spec: dict) -> Any:
    """根据条件配置(单键dict)创建条件实例, 如 {'size': '>=100MiB'}"""
    name, value = next(iter(spec.items()))
    return CONDITIONS[name](value)


def create_action(name: str, value: Any) -> Any:
    """根据动作名与配置创建动作实例"""
    return ACTIONS[name](value)


# ---------------------------------------------------------------------------
# 派生访问器(W5 收口消费面): 深度校验器分发 / 触发器 x 动作兼容表 / watch_fields 取值域 /
# schema 插件表, 全部从条目声明派生 —— 新增插件只注册本表一处即全链路可用(验收①)。
# ---------------------------------------------------------------------------


def iter_entries() -> List[PluginEntry]:
    """全部插件条目(条件在前, 动作在后, 均按注册序)"""
    return list(CONDITION_ENTRIES.values()) + list(ACTION_ENTRIES.values())


def condition_plugins() -> tuple:
    """条件插件 schema 声明表(按注册序解析; config.schema.plugin_table 的派生源)"""
    return tuple(e.plugin() for e in CONDITION_ENTRIES.values())


def action_plugins() -> tuple:
    """动作插件 schema 声明表(按注册序解析; config.schema.plugin_table 的派生源)"""
    return tuple(e.plugin() for e in ACTION_ENTRIES.values())


def deleted_allowed_actions() -> Tuple[str, ...]:
    """on_torrent_deleted 允许的动作白名单(G11 派生): 条目 deleted_ok 声明的动作名, 按注册序"""
    return tuple(e.name for e in ACTION_ENTRIES.values() if e.deleted_ok)


def watch_fields_allowed() -> Tuple[str, ...]:
    """on_torrent_field_changed 可监听字段取值域(G10 派生): 条件条目 watchable_field 声明, 按注册序"""
    return tuple(e.watchable_field for e in CONDITION_ENTRIES.values() if e.watchable_field)
