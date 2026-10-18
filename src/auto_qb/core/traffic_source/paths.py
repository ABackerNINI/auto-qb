"""取数路径解析单点(计划 26-10-17-0339 R2/D20).

**为什么需要这一层**: `traffic_source` 段里只有「用户能配什么」; 工具来源的 dat 路径不是配置
事实 —— 它是**工具运行期报出来的**(发现指针 `endpoint.json` 的 `data_dir`)。旧设计让配置里再存
一份 `global_traffic_monitor.data_dir`, 于是同一件事有两个来源: 配置空 -> 取数恒失败, 配置旧
-> 指向一个不再存在的目录。实测事故(26-10-17 14:00)就是前者: 迁移没搬出 data_dir, 状态区却
一直显示指针里的真实目录, 看着"已就绪"而曲线读的是空路径。

**本模块是唯一入口**: 谁要 dat 路径, 一律 `dat_path(config)`, 不许自己拼 `data_dir + 文件名`
也不许读配置里的旧字段(该字段已删)。

口径
----
- `provider == "traffic_monitor"` -> `traffic_monitor.dat_path`(去空白; 纯配置事实)
- `provider == "global_traffic_monitor"` -> 读发现指针 -> `<data_dir>/history_traffic.dat`

总开关(计划 26-10-17-1737 S1/D1): `traffic_source.enabled=false` = 停一切取数 ——
`dat_path` 返回空串, `unavailable_reason` 报「流量来源已关闭」(判定优先于 provider 分支:
关源时工具指针在不在都不再取数, 文案指到总开关而不是数据源)。

指针只读、**不探活**: 探活是 HTTP, 属于订阅线程的事; 取数路径解析发生在主循环的曲线轮与
规则求值里, 那里只允许一次小文件读。工具优雅退出会删指针 -> 这里返回空串 -> 调用方按
「数据源不可得」显式报错/落 stale; 工具崩溃留下的残留指针仍能读出路径, 恰好让图表停在上次
数据而不是突然清空 —— 两种情况都不猜。

文件名 `history_traffic.dat` 是**跨包契约**(工具侧 `gtm.storage` 同源), 只在这里出现一次。
"""
from __future__ import annotations

import os
from typing import Optional

from . import agent

#: 工具历史流量文件名(跨包契约): 与 tools/global-traffic-monitor/src/gtm/storage.py 同源
DAT_FILE_NAME = "history_traffic.dat"


def _traffic_source(config) -> Optional[object]:
    """取 traffic_source 段; 缺段(桩配置/老调用方) -> None(按"未配置"处理, 不抛)"""
    return getattr(config, "traffic_source", None)


def source_enabled(config) -> bool:
    """数据来源总开关(计划 26-10-17-1737 S1/D1): 只有显式 false 算关闭

    恒等判据 `is not False`: 桩配置(MagicMock 属性等)不触发关闭 —— 同族问题见
    pitfalls hot-reload-mock-sections(属性值不能当成启用/关闭的事实)。
    """
    ts = _traffic_source(config)
    return getattr(ts, "enabled", True) is not False


def _provider(config) -> str:
    """当前生效来源; 段缺失/留空 -> traffic_monitor(与 loader/校验同口径)"""
    ts = _traffic_source(config)
    return str(getattr(ts, "provider", "") or "traffic_monitor").strip()


def tool_dat_path() -> str:
    """工具来源的 dat 路径: 发现指针里的 data_dir + 契约文件名; 指针缺失/字段空 -> ""

    !不做存在性检查: 路径解析与"文件在不在"是两件事, 后者由读取方按 OSError 区分
    (dat_missing 文案带路径, 比在这里返回空串更好排障)。
    """
    ep = agent.discover()
    data_dir = str(getattr(ep, "data_dir", "") or "").strip() if ep else ""
    return os.path.join(data_dir, DAT_FILE_NAME) if data_dir else ""


def dat_path(config) -> str:
    """当前生效来源的 dat 文件路径(空 = 取不到; 调用方决定报错口径) —— 取数唯一入口

    总开关关闭(S1/D1)优先于 provider 分支: 关源即停取数, 指针在不在都不读。
    """
    if not source_enabled(config):
        return ""
    if _provider(config) == "global_traffic_monitor":
        return tool_dat_path()
    ts = _traffic_source(config)
    tm = getattr(ts, "traffic_monitor", None)
    return str(getattr(tm, "dat_path", "") or "").strip()


def source_signature(config) -> tuple:
    """来源身份指纹 `(enabled, provider, traffic_monitor.dat_path)` —— 「切源即刷新」判定单点

    用途(计划 26-10-17-1737 S8): 热重载**前后各算一次**, 不等即说明「用户在换来源」, 立刻投递
    一次历史流量刷新, 不必等下一个曲线 interval。

    !只取**配置事实**, 不把 `dat_path(config)` 的解析结果算进来: 工具来源的路径是运行期事实
    (发现指针的内容随时可被工具改写), 两次读之间可能变 —— 算进来会让「保存任何无关配置」偶发
    触发刷新, 判定也不再可复现。文件 <-> 工具互切已由 provider 这一位覆盖。
    """
    ts = _traffic_source(config)
    tm = getattr(ts, "traffic_monitor", None)
    return (source_enabled(config), _provider(config), str(getattr(tm, "dat_path", "") or "").strip())


def unavailable_reason(config) -> str:
    """取不到路径时的人读原因(按 provider 分支) —— 让运行期报错直接指到该改哪里

    与 `dat_path` 同源判定: 文案里的分支必须和取数分支一致, 否则用户按文案改完还是不生效
    (pitfalls/backend/verdict-scope-parity.md 的同族问题)。关源分支优先: 此时 provider 指向
    谁都不取数, 文案必须指到总开关(S1/D1)。
    """
    if not source_enabled(config):
        return ("流量来源已关闭: config.traffic_source.enabled=false —— 曲线/规则表达式/工具订阅"
                "已停止取数; 到设置页「全局流量来源」重新启用总开关即可恢复")
    if _provider(config) == "global_traffic_monitor":
        return (
            "数据源不可得: 全局流量监视器未在运行(发现指针 endpoint.json 缺失或未报出数据目录), "
            "取不到 history_traffic.dat 路径 —— 到设置页「全局流量来源」看工具状态, 或点「立即拉起」"
        )
    return "数据源未配置: 需要 config.traffic_source.traffic_monitor.dat_path"
