"""落盘结构化文件的 schema 版本与逐级升级链(计划 26-09-26-0506)

纳入版本链的判据: 程序会**读回**、且结构会**演化**的持久化文件才需要版本号 —— 版本号
的价值是「旧数据能被新代码读懂」。当前三类: state.json / hr/<site>.json / config.yml;
其余落盘点逐项豁免(理由见计划 §2.2)。本模块是版本号与迁移链的**单一事实来源**:

- **CURRENT_VERSIONS[kind]**: 当前程序写出的文件版本。文件结构发生一次破坏性变更就 +1,
  与程序版本(`__version__`)完全解耦 —— 程序发版不迁文件, 反之亦然。
- **MIGRATIONS[kind][from_version]**: 相邻版本迁移表, 每个注册项恰好 +1 级; 跨多级升级
  由 `migrate()` 沿链串行完成(v1→v2→v3), 任何一级都不感知更早的历史。
- **迁移函数纪律**: 纯函数(dict→dict, 无 IO); 原子写 / 备份等 IO 语义一律留在调用方;
  `schema_version` 字段由本框架在每级迁移后统一盖章, 迁移函数不必自己改版本字段。
- **版本检测口径**: 字段缺失 = v1(存量文件口径) —— 三类文件的现行结构即 v1, 第一次
  *破坏性*结构变更才诞生 v2 与第一个迁移函数。刻意不为"补字段"这类非破坏性动作造版本:
  那会让所有存量文件平白走一次迁移写盘, 换来的只是演示价值(链式执行的正确性由单测里的
  临时注册验证, 不落生产)。

依赖纪律: infra 只被依赖 —— 本模块只依赖 .errors, 不 import 任何业务模块。
"""
from typing import Callable, Dict, Tuple

from .errors import SchemaVersionError

#: 版本字段名(三类文件统一; state 在顶层, hr_site / config 在各自文件形状内)
VERSION_KEY = "schema_version"

CURRENT_VERSIONS: Dict[str, int] = {
    "state": 1,  # <data_dir>/state.json 顶层 schema_version
    "hr_site": 1,  # hr/<site>.json 的 schema_version(hr/model.SCHEMA_VERSION 是它的别名)
    "config": 1,  # config.schema_version(YAML 的 config: 块内, 不占根键)
}

# MIGRATIONS[kind][from_version] = fn(data: dict) -> dict
# 纪律见模块 docstring; 首个破坏性结构变更出现时, 在对应表注册 migrate_<kind>_<n>_<n+1>。
MIGRATIONS: Dict[str, Dict[int, Callable[[dict], dict]]] = {
    "state": {},
    "hr_site": {},
    "config": {},
}


def detect_version(kind: str, data: dict) -> int:
    """读数据里的 schema_version; 缺失 = 1(存量文件口径)

    非 int / bool / < 1 / > CURRENT_VERSIONS[kind] / 未注册 kind -> SchemaVersionError。
    「文件比程序新」的报错必须同时说清两个版本号 —— 那是用户排障的唯一线索。
    (bool 是 int 的子类, 显式排除: True 否则会被 isinstance(int) 放行成 1。)
    """
    current = CURRENT_VERSIONS.get(kind)
    if current is None:
        raise SchemaVersionError(f"未注册的文件类型 kind={kind!r}")
    version = data.get(VERSION_KEY, 1)
    if isinstance(version, bool) or not isinstance(version, int):
        raise SchemaVersionError(f"schema_version 必须是整数, 实际为 {version!r}")
    if version < 1:
        raise SchemaVersionError(f"schema_version 必须 >= 1, 实际为 {version}")
    if version > current:
        raise SchemaVersionError(
            f"schema_version={version} 高于本程序支持的 {current}"
            "(文件由更新版本的程序写出, 请先升级程序; 不回退备份 —— 备份里也是同一个新版本)"
        )
    return version


def migrate(kind: str, data: dict) -> Tuple[dict, str]:
    """从检测出的版本沿链逐级迁移到 CURRENT_VERSIONS[kind]

    已是最新则原样返回(不打章 —— 写点统一盖章, 见各集成方); 发生迁移时每完成一级由本
    框架盖一次 schema_version 章。返回 (数据, "v1→v3" 形式的描述; 无迁移发生为 "")。
    迁移表缺项(版本号抬了表没跟上)按 SchemaVersionError fail-fast, 不静默跳级。
    迁移中途崩溃的幂等性由调用方保证: 链的输入是磁盘上的真实版本, 重放同一条链即可。
    """
    version = detect_version(kind, data)
    current = CURRENT_VERSIONS[kind]
    if version == current:
        return data, ""
    table = MIGRATIONS[kind]
    start = version
    while version < current:
        step = table.get(version)
        if step is None:
            raise SchemaVersionError(f"{kind} 缺少 v{version}→v{version + 1} 的迁移函数(版本表与迁移表不同步)")
        data = step(data)
        version += 1
        data[VERSION_KEY] = version
    return data, f"v{start}→v{version}"
