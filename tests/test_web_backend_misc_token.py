"""test_web_backend_misc_token 测试计划: WEB 后端杂项: config / token / sites / 分组视图 / 错误原因

## 测试计划(每个测试函数一条)
- test_web_context_ro_cache_and_require_helpers: WebContext 共享件(P0-T0.5) —— RoCache 命中/写序号失效/128 上限整体清空 + require_torrent 404 / require_client 503 路由前置闸
- test_web_token_not_printed_in_logs: 生成的访问密钥不进任何日志(WARNING 会被 notify 推送, 且 /api/log 可读回)
- test_web_sidecar_dir_single_point: 守阵(issue webui-sidecar-dir-convention-dup) 旁挂文件「state_file 同目录」寻址走 common.state_dir 单点 —— 三处调用点零自写 dirname + 裸文件名回 "."
- test_web_token_generated_atomic_and_readable: 首次生成密钥落盘 web.token 且读回一致, 无临时文件残留(走 atomic_write, issue 26-09-21-1347)
- test_web_token_existing_file_reused_without_rewrite: 已有合法 token 时直接复用文件现值, 不触达写盘路径(不重写不漂移)
- test_web_token_write_interrupt_leaves_no_half_token: 写盘中断不留非空半截 token —— 经真实 atomic_write 跑"写一半抛错", 旧文件不被破坏、临时文件被清理, 下次调用重新生成(自愈)
- test_token_resolve_single_point_in_infra: 守阵(issue hr-token-persist-convention-dup) token 生成/持久化口径单点在 infra.utils.resolve_or_create_token —— token_hex(32) 全仓唯一 + 两侧入口必须委托
"""

import logging

import os

import re

import time

from types import SimpleNamespace

import pytest

from auto_qb.infra.utils import decode_group_key, encode_group_key

from webui_helpers import WEB_ENV_CONFIG_TEXT, _make_web_manager, STATIC_ROOT, _UI_ALL, _ui_aggregate


def test_web_token_not_printed_in_logs(tmp_path, caplog):
    """生成的访问密钥不得出现在任何日志里

    原实现用 `logger.warning(f"WEB UI 访问密钥: {token}")`: notify 处理器的级别取
    config.min_level(早期默认 WARNING, 26-09-27 等级整改后默认 ERROR) ⇒ 密钥被推到系统
    通知; 落日志文件后已登录者可经 /api/log 读回。拿到密钥即等于拿到改配置/删种子的能力。改为只提示文件路径。
    """
    from auto_qb.webui import ensure_web_token

    mgr = _make_web_manager(tmp_path, WEB_ENV_CONFIG_TEXT)
    with caplog.at_level(logging.DEBUG, logger="auto_qb.web"):
        token = ensure_web_token(mgr)
    assert token, "前置: 应生成随机密钥"
    assert any(r.name == "auto_qb.web" for r in caplog.records), "前置: 应有生成提示日志"
    for r in caplog.records:
        assert token not in r.getMessage(), f"密钥不得出现在日志: {r.getMessage()}"
        assert token[:8] not in r.getMessage(), f"密钥前缀也不得出现: {r.getMessage()}"


def test_web_sidecar_dir_single_point(tmp_path):
    """守阵: 旁挂文件「与 state_file 同目录」寻址走 `common.state_dir` 单点(issue webui-sidecar-dir-convention-dup)

    web.token / webui-keys.json / 启动日志提示三处此前各写一遍
    `os.path.join(os.path.dirname(manager.state_file) or ".", <name>)`, 改寻址规则要逐处记得改。
    静态: 三处调用点源码里都不再出现自写的 `os.path.dirname(manager.state_file)`;
    行为: state_dir == state_file 目录, keys 文件落在该目录下; state_file 是裸文件名(无目录段)时回 "."(= cwd, 原口径)。
    红验: 任一侧改回自写 dirname, 静态半判红; 单点漏掉 `or "."` 兜底, 裸文件名分支判红。
    """
    from pathlib import Path

    from auto_qb.webui.server.common import state_dir
    from auto_qb.webui.server.routes.keys import keys_file_path

    root = Path(__file__).resolve().parents[1] / "src" / "auto_qb"
    for rel in ("webui/server/lifecycle.py", "webui/server/routes/keys.py"):
        text = (root / rel).read_text(encoding="utf-8")
        assert "os.path.dirname(manager.state_file)" not in text, f"{rel} 仍在自写旁挂目录寻址(应走 state_dir)"
    # 单点本体只允许在 common.state_dir 里出现一次(多了 = 又有人在别处自写)
    common = (root / "webui/server/common.py").read_text(encoding="utf-8")
    assert common.count("os.path.dirname(manager.state_file)") == 1, "旁挂目录寻址必须在 common.state_dir 单点"

    mgr = _make_web_manager(tmp_path, WEB_ENV_CONFIG_TEXT)
    assert state_dir(mgr) == os.path.dirname(mgr.state_file)
    assert keys_file_path(mgr) == os.path.join(state_dir(mgr), "webui-keys.json")
    assert keys_file_path(SimpleNamespace(state_file="state.json")) == os.path.join(".", "webui-keys.json")
    assert state_dir(SimpleNamespace(state_file="state.json")) == ".", "裸文件名回 cwd(与原口径逐字一致)"


def test_web_token_generated_atomic_and_readable(tmp_path):
    """首次生成: 密钥落盘 web.token 且读回一致, 同目录无临时文件残留(issue 26-09-21-1347)

    ensure_web_token 走 utils.atomic_write(mkstemp 0600 + os.replace): 写盘成功后目标文件
    即完整可读 —— 半截状态只可能存在于临时文件, replace 前对读取侧不可见。
    """
    from auto_qb.webui import ensure_web_token

    mgr = _make_web_manager(tmp_path, WEB_ENV_CONFIG_TEXT)
    token = ensure_web_token(mgr)
    assert re.fullmatch(r"[0-9a-f]{64}", token), "token_hex(32) 应为 64 位小写 hex"
    token_file = tmp_path / "web.token"
    assert token_file.read_text(encoding="ascii") == token, "落盘内容必须与返回值逐字节一致"
    assert not list(tmp_path.glob("web.token.*")), "不得残留临时文件"


def test_web_token_existing_file_reused_without_rewrite(tmp_path, monkeypatch):
    """已有合法 token 时不重写: 直接返回文件现值, 写盘路径一次都不触发(不重写不漂移)"""
    from auto_qb.infra import utils as infra_utils
    from auto_qb.webui import ensure_web_token

    existing = "ab" * 32
    (tmp_path / "web.token").write_text(existing, encoding="ascii")
    mgr = _make_web_manager(tmp_path, WEB_ENV_CONFIG_TEXT)

    def _must_not_write(*_a, **_kw):
        raise AssertionError("已有合法 token 时不得触达写盘路径")

    monkeypatch.setattr(infra_utils, "atomic_write", _must_not_write)
    assert ensure_web_token(mgr) == existing, "应复用文件现值而非重新生成"
    assert (tmp_path / "web.token").read_text(encoding="ascii") == existing


def test_web_token_write_interrupt_leaves_no_half_token(tmp_path, monkeypatch):
    """写盘中断不留非空半截 token(issue 26-09-21-1347): 旧文件不被破坏, 下次调用重新生成(自愈)

    经真实 atomic_write 跑"写一半抛错": 回调写入半截后抛 RuntimeError, 由 atomic_write 负责
    清理临时文件并重抛 —— 目标路径保持旧内容。若实现退回 O_TRUNC 直写, 同一时刻半截内容已落
    目标文件, 本条在 raises 处即红。
    """
    from auto_qb.webui import ensure_web_token

    from helpers import pin_atomic_write_crash

    mgr = _make_web_manager(tmp_path, WEB_ENV_CONFIG_TEXT)
    token_file = tmp_path / "web.token"
    token_file.write_text("", encoding="ascii")  # 空文件: 读取侧判空后走重新生成分支

    pin_atomic_write_crash(monkeypatch)
    with pytest.raises(RuntimeError):
        ensure_web_token(mgr)
    assert token_file.read_text(encoding="ascii") == "", "中断后不得留下非空半截 token"
    assert not list(tmp_path.glob("web.token.*")), "中断的临时文件必须被清理"

    monkeypatch.undo()
    token = ensure_web_token(mgr)  # 自愈: 下次启动重新生成并完整落盘
    assert token_file.read_text(encoding="ascii") == token


def test_token_resolve_single_point_in_infra():
    """守阵(issue hr-token-persist-convention-dup): token 生成/持久化口径单点在 infra.utils.resolve_or_create_token

    此前 hr/channel.resolve_token 与 webui/server/common.ensure_web_token 两处逐字同
    (显式优先 -> 读文件 -> token_hex(32) -> atomic_write -> INFO 只提示路径)。
    静态: `token_hex(32)` 全仓只允许出现在 infra/utils.py(访问密钥生成唯一处;
    webui/runtime 的 token_hex(8) 是 cmd_id 回执, 另一码事), 两侧入口必须引用单点。
    红验: 任一侧改回自写生成(token_hex(32) 回潮)或摘掉委托即红。
    """
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "src" / "auto_qb"
    hits = sorted(
        p.relative_to(root).as_posix() for p in root.rglob("*.py") if "token_hex(32)" in p.read_text(encoding="utf-8")
    )
    assert hits == ["infra/utils.py"], f"token_hex(32) 只允许在 infra/utils.py 单点, 现分布: {hits}"
    for rel in ("hr/channel.py", "webui/server/common.py"):
        assert "resolve_or_create_token" in (root /
                                             rel).read_text(encoding="utf-8"
                                                           ), (f"{rel} 必须委托 infra.utils.resolve_or_create_token")


def test_web_context_ro_cache_and_require_helpers(tmp_path):
    """WebContext 共享件(P0-T0.5): RoCache 带写失效短缓存(命中/写序号失效/上限治理) +
    require_torrent 404 / require_client 503(路由前置闸的纯逻辑)"""
    import threading
    from types import SimpleNamespace

    from fastapi import HTTPException

    from auto_qb.webui.server.context import RoCache, WebContext

    web = SimpleNamespace(write_seq=0)
    mgr = SimpleNamespace(web=web, store=SimpleNamespace(get=lambda h: None), client=None)
    ctx = WebContext(mgr)

    # RoCache: 同一 (key, write_seq) 窗口内命中零重算; write_seq 推进(任何写命令成功)即换键
    calls = {"n": 0}

    def _fn():
        calls["n"] += 1
        return calls["n"]

    assert ctx.cached_read("k", _fn) == 1
    assert ctx.cached_read("k", _fn) == 1 and calls["n"] == 1, "TTL 内命中"
    web.write_seq = 1  # 写命令执行成功 -> 缓存自动失效(防「刚改完还拿旧值」)
    assert ctx.cached_read("k", _fn) == 2 and calls["n"] == 2

    # 上限治理: 塞满 128 条后整体清空(只留新鲜的), 不无界增长
    cache = RoCache(mgr)
    cache._cache = {(f"k{i}", 0): (time.time(), i) for i in range(200)}
    assert cache.get("fresh", _fn) == 3
    assert len(cache._cache) == 1, "超限应整体清空"

    # require_torrent: hash 不在快照 -> 404(路由前置闸单点)
    with pytest.raises(HTTPException) as ei:
        ctx.require_torrent("nope")
    assert ei.value.status_code == 404

    # require_client: qB 断连 -> 503
    with pytest.raises(HTTPException) as ei2:
        ctx.require_client()
    assert ei2.value.status_code == 503
