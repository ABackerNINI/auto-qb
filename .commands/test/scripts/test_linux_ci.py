"""linux_ci.py 代理透传守阵 —— 容器网络两条坑的机检(坑档单点: pitfalls/testing/patching.md「容器网络坑」)。

只测**纯函数**(`container_env` / `rewrite_proxy`): 真起容器跑全量属 `test.linux` 本体 —— 慢、要网,
不做守阵。(2026-10-11 实测: 缺回环改写时 `uv sync` 直连 PyPI `tls handshake eof`; 注了代理不放行回环时
`tests/test_hr_server.py` 一批回环端点用例 6 failed + 2 errors 假红。)

跑法: python <包>/scripts/test_linux_ci.py  ·  uv run pytest .commands -q --no-cov (test.pkg 口径)

## 测试计划
- test_loopback_proxy_rewritten_to_host_gateway  回环代理 → host.docker.internal + 要 --add-host
- test_non_loopback_proxy_passes_through         真网关代理原样透传, 不白加 --add-host
- test_no_proxy_always_covers_loopback           no_proxy 恒并入回环(缺它 ⇒ 回环用例被代理拦截)
- test_lang_is_pinned_for_utf8_output            LANG 仍钉 C.UTF-8
- test_safety_probe_admits_action_without_args   `--safety` 自认 action-without-args(闸门别白起容器)
"""

from __future__ import annotations

import linux_ci

LOOPBACK = {"127.0.0.1", "localhost", "::1"}


def test_loopback_proxy_rewritten_to_host_gateway() -> None:
    pairs, needs_gateway = linux_ci.container_env(
        {
            "http_proxy": "http://127.0.0.1:4085",
            "HTTPS_PROXY": "http://localhost:8080/",
        }
    )
    env = dict(pairs)
    assert env["http_proxy"] == "http://host.docker.internal:4085"
    assert env["HTTPS_PROXY"] == "http://host.docker.internal:8080/"
    assert needs_gateway is True


def test_non_loopback_proxy_passes_through() -> None:
    pairs, needs_gateway = linux_ci.container_env({"http_proxy": "http://10.1.2.3:3128"})
    assert dict(pairs)["http_proxy"] == "http://10.1.2.3:3128"
    assert needs_gateway is False


def test_no_proxy_always_covers_loopback() -> None:
    for seed in ({}, {"no_proxy": "example.com"}, {"http_proxy": "http://127.0.0.1:4085"}):
        env = dict(linux_ci.container_env(seed)[0])
        bypass = set(env["no_proxy"].split(","))
        assert LOOPBACK <= bypass, seed
        assert env["no_proxy"] == env["NO_PROXY"]
        if "example.com" in (seed.get("no_proxy") or ""):
            assert "example.com" in bypass, "宿主已有的放行项不许被覆盖"


def test_lang_is_pinned_for_utf8_output() -> None:
    assert dict(linux_ci.container_env({})[0])["LANG"] == "C.UTF-8"


def test_safety_probe_admits_action_without_args() -> None:
    assert linux_ci.main(["--safety"]) == 0
