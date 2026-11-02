"""test.pkg.scoped wrapper 的自测 —— 归并纯函数 + main 分支(子进程一律用替身, 不真跑 pytest)。

跑法: uv run pytest .commands -q --no-cov   (test.pkg 的口径)

## 测试计划
- TestPlan   plan(): 单包 / 多包归并排序 / 引擎路径不归并为包 / --full 旗标 / 反斜杠归一 / 去重 / 裸 -- 过滤
- TestMain   main(): 0 包 → rc 0 且不起子进程; 单包 → pytest 目标收窄到该包;
             --full → 转调 run.py run test.pkg; 两包 → D4 保守整跑
             (TMPDIR 自 2026-11-02 起不再由 wrapper 注入, 由子进程 _tmp_bootstrap 自举)
"""

from __future__ import annotations

import subprocess

import pkg_scoped


class TestPlan:
    def test_single_pkg(self) -> None:
        assert pkg_scoped.plan([".commands/kb/scripts/x.py"]) == (False, ["kb"])

    def test_multi_pkgs_sorted_dedup(self) -> None:
        assert pkg_scoped.plan([".commands/doc/b.py", ".commands/kb/a.py", ".commands/kb/c.py"]) == (
            False,
            ["doc", "kb"],
        )

    def test_engine_path_is_not_a_pkg(self) -> None:
        assert pkg_scoped.plan([".agents/skills/commands/scripts/run.py"]) == (False, [])

    def test_full_flag(self) -> None:
        assert pkg_scoped.plan(["--full", ".commands/kb/a.py"]) == (True, ["kb"])

    def test_backslash_normalized_and_dedup(self) -> None:
        assert pkg_scoped.plan([".commands\\kb\\a.py", ".commands/kb/b.py"]) == (False, ["kb"])

    def test_bare_dash_filtered(self) -> None:
        # 引擎 `_extra` 剥不剥前导 `--` 都可能留下它 —— plan() 一律过滤(REMAINDER 行为有版本差)
        assert pkg_scoped.plan(["--", ".commands/kb/a.py"]) == (False, ["kb"])

    def test_root_file_is_not_a_pkg(self) -> None:
        assert pkg_scoped.plan(["README.md", "scripts/x.py"]) == (False, [])


class TestMain:
    @staticmethod
    def _fake_run(monkeypatch, calls):
        def fake_run(argv, **kw):
            calls.append(list(argv))
            return subprocess.CompletedProcess(argv, 0)

        monkeypatch.setattr(pkg_scoped.subprocess, "run", fake_run)

    def test_zero_pkg_is_silent_zero(self, monkeypatch) -> None:
        calls: list[list[str]] = []
        self._fake_run(monkeypatch, calls)
        assert pkg_scoped.main([]) == 0
        assert calls == []

    def test_single_pkg_scopes_pytest(self, monkeypatch) -> None:
        calls: list[list[str]] = []
        self._fake_run(monkeypatch, calls)
        assert pkg_scoped.main(["--", ".commands/kb/scripts/test_x.py"]) == 0
        assert len(calls) == 1
        argv = calls[0]
        assert argv[:3] == ["uv", "run", "pytest"]
        assert ".commands/kb" in argv
        assert "--no-cov" in argv and "-n" in argv

    def test_full_delegates_to_test_pkg(self, monkeypatch) -> None:
        calls: list[list[str]] = []
        self._fake_run(monkeypatch, calls)
        assert pkg_scoped.main(["--full", ".agents/skills/commands/scripts/run.py"]) == 0
        assert calls[0][-2:] == ["run", "test.pkg"]

    def test_two_pkgs_mean_full(self, monkeypatch) -> None:
        calls: list[list[str]] = []
        self._fake_run(monkeypatch, calls)
        pkg_scoped.main([".commands/kb/a.py", ".commands/doc/b.py"])
        assert calls[0][-2:] == ["run", "test.pkg"]
