"""routes 子包: 按域拆分的 APIRouter(每模块 build_router(ctx) -> APIRouter).

factory 按 ROUTE_BUILDERS 顺序 include; 各模块内部路由相对顺序保持拆分前源码顺序;
跨模块无同形路径冲突 —— 金清单守阵 test_web_route_manifest_frozen 钉死。
"""
from . import state as _state, events as _events, groups as _groups, torrent_cmds as _torrent_cmds, torrent_detail as _torrent_detail, fs as _fs, config as _config, system as _system

ROUTE_BUILDERS = (
    _state.build_router,
    _events.build_router,
    _groups.build_router,
    _torrent_cmds.build_router,
    _torrent_detail.build_router,
    _fs.build_router,
    _config.build_router,
    _system.build_router,
)
