"""test_release_pipeline 测试计划: release 管线脚本回归网 (计划 26-09-22-2318 v2 §6.2)。

守什么: `.agents/skills/release/scripts/` 的 apply_bump / ff_merge / tag_release /
ci_gate / release_page 五脚本的关键分支 —— 净树守卫、非快进停手、tag 幂等重入与指向
校验、CI 判定矩阵与超时口径、Release 页降级与镜像纪律。全部 git/HTTP/子进程经
monkeypatch 单点注入 —— 零真实网络、零子进程、零仓库外副作用。

## 测试计划

- test_apply_bump_dirty_tree_rejects: 工作树不净拒跑 bump (保守默认)
- test_apply_bump_happy_path: 净树 -> bump-my-version 调用 -> uv sync -> before/after JSON
- test_apply_bump_bm_missing: bump-my-version 不在 PATH -> rc1 单行 stderr
- test_ff_merge_remote_tip_parsing: ls-remote 输出解析 (存在/不存在/空 sha)
- test_ff_merge_non_ff_stops: merge-base 非祖先 -> rc1 非快进停手 (拍板 §09-10)
- test_ff_merge_reentrant: 远端已同点 -> reentrant 不推
- test_ff_merge_happy_path: 祖先成立 -> 显式 ref 推送 -> ls-remote 核验一致
- test_tag_release_pattern_rejects: 非 vX.Y.Z 形态拒收
- test_tag_release_local_conflict_stops: 本地 tag 已存在指向别处 -> 停手要人
- test_tag_release_remote_conflict_stops: 远端 tag 指向不一致 -> 停手要人
- test_tag_release_reentrant: 本地远端均已指向 HEAD -> 重入不重建不重推
- test_tag_release_create_and_verify: 建 annotated tag -> show-ref 核验 -> 双远端推送 -> 核验
- test_ci_gate_judge_matrix: judge 纯函数 (绿/红/未收敛/未知结论按未收敛/零 run pending)
- test_ci_gate_green_and_red_paths: 全绿 rc0 / 红列明细 rc1
- test_ci_gate_timeout_and_zero_runs: 超时 rc2 / 全程零 run rc2 (不静默放行)
- test_ci_gate_api_down: API 不可用 rc3 (停手报告)
- test_release_page_degraded_no_token: gitee token 未配置 -> 降级 WARN rc0 (拍板 §09-14)
- test_release_page_gitee_failure_rc1: token 在手但建页失败 -> rc1 (主线失败要停)
- test_release_page_reentrant_and_created: 已存在重入 / 201 创建
- test_release_page_github_missing_gh: gh 缺席 -> 镜像失败只报告 rc0
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".agents" / "skills" / "release" / "scripts"


def _load(name: str):
    """进程内装载 release skill 脚本 (注册 sys.modules 后 exec, 只装一次)。"""
    key = f"release_{name}"
    if key not in sys.modules:
        path = SCRIPTS / f"{name}.py"
        spec = importlib.util.spec_from_file_location(key, path)
        assert spec and spec.loader, f"缺少 release skill 脚本: {path}"
        mod = importlib.util.module_from_spec(spec)
        sys.modules[key] = mod
        spec.loader.exec_module(mod)
    return sys.modules[key]


def _gitmap(mapping: dict[tuple[str, ...], str], default: str = ""):
    """构造 run_git 替身: 按 args 元组前缀匹配返回预置输出, 未命中抛 RuntimeError。"""
    def run_git(args, repo):
        key = tuple(args)
        for prefix, value in mapping.items():
            if key[:len(prefix)] == prefix:
                if value is None:
                    raise RuntimeError(f"injected failure: {' '.join(args)}")
                return value
        raise RuntimeError(f"unexpected git call: {' '.join(args)}")

    return run_git


# --------------------------------------------------------------- apply_bump


def test_apply_bump_dirty_tree_rejects(tmp_path, monkeypatch, capsys):
    mod = _load("apply_bump")
    monkeypatch.setattr(mod, "run_cmd", lambda args, repo: (0, " M pyproject.toml\n") if args[0] == "git" else (0, ""))
    rc = mod.main(["--repo", str(tmp_path), "--kind", "patch", "--skip-sync"])
    err = capsys.readouterr().err.strip()
    assert rc == 1 and err.startswith("[apply_bump]") and "工作树不净" in err


def test_apply_bump_happy_path(tmp_path, monkeypatch, capsys):
    mod = _load("apply_bump")
    calls = []
    versions = ["0.2.0", "0.3.0"]

    def run_stub(args, repo):
        calls.append(args)
        if args[0] == "git" and args[1] == "status":
            return 0, ""
        return 0, "New version will be '0.3.0'"

    monkeypatch.setattr(mod, "run_cmd", run_stub)
    monkeypatch.setattr(mod, "read_current_version", lambda repo: versions.pop(0))
    rc = mod.main(["--repo", str(tmp_path), "--kind", "minor"])
    cap = capsys.readouterr()
    payload = json.loads(cap.out)
    assert rc == 0 and payload["before"] == "0.2.0" and payload["after"] == "0.3.0" and payload["synced"] is True
    kinds = [args for args in calls if "bump-my-version" in args[0]]
    assert kinds and kinds[0][1:3] == ["bump", "minor"]
    assert any(args[0] == "uv" and args[1] == "sync" for args in calls)  # 元数据刷新 (R1-F4)


def test_apply_bump_bm_missing(tmp_path, monkeypatch, capsys):
    mod = _load("apply_bump")
    monkeypatch.setattr(mod, "run_cmd", lambda args, repo: (0, ""))
    monkeypatch.setattr(mod, "read_current_version", lambda repo: "0.2.0")
    monkeypatch.setattr(mod.shutil, "which", lambda name: None)
    rc = mod.main(["--repo", str(tmp_path), "--kind", "patch", "--skip-sync"])
    err = capsys.readouterr().err.strip()
    assert rc == 1 and "bump-my-version 不在 PATH" in err


# --------------------------------------------------------------- ff_merge


def test_ff_merge_remote_tip_parsing():
    mod = _load("ff_merge")
    git = _gitmap({("ls-remote", "origin", "refs/heads/master"): "abc123\trefs/heads/master\n"})
    assert mod.remote_tip_of(git, "r", "origin", "master") == "abc123"
    git2 = _gitmap({("ls-remote", "origin", "refs/heads/master"): ""})
    assert mod.remote_tip_of(git2, "r", "origin", "master") is None
    git3 = _gitmap({("ls-remote", "origin", "refs/heads/x"): None})
    with pytest.raises(RuntimeError, match="injected failure"):
        mod.remote_tip_of(git3, "r", "origin", "x")


def _ff_base_mapping(remote_tip, head):
    return _gitmap(
        {
            ("status", "--porcelain"): "",
            ("rev-parse", "HEAD"): head,
            ("ls-remote", "gitee", "refs/heads/master"): f"{remote_tip}\trefs/heads/master\n" if remote_tip else "",
            ("fetch", "--quiet", "gitee", "master"): "",
            ("merge-base", "--is-ancestor", remote_tip or "x", head): "" if remote_tip else None,
            ("push", "gitee", f"{head}:refs/heads/master"): "",
        }
    )


def test_ff_merge_non_ff_stops(tmp_path, monkeypatch, capsys):
    mod = _load("ff_merge")
    git = _gitmap(
        {
            ("status", "--porcelain"): "",
            ("rev-parse", "HEAD"): "bbb2222",
            ("ls-remote", "gitee", "refs/heads/master"): "aaa1111\trefs/heads/master\n",
            ("fetch", "--quiet", "gitee", "master"): "",
            ("merge-base", "--is-ancestor", "aaa1111", "bbb2222"): None,  # rc!=0 -> 非祖先
        }
    )
    monkeypatch.setattr(mod, "run_git", git)
    rc = mod.main(["--repo", str(tmp_path), "--remote", "gitee", "--to-branch", "master"])
    err = capsys.readouterr().err.strip()
    assert rc == 1 and "非快进, 停手要人" in err


def test_ff_merge_reentrant(tmp_path, monkeypatch, capsys):
    mod = _load("ff_merge")
    monkeypatch.setattr(mod, "run_git", _ff_base_mapping("same1234", "same1234"))
    rc = mod.main(["--repo", str(tmp_path), "--remote", "gitee", "--to-branch", "master"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0 and payload["status"] == "reentrant"


def test_ff_merge_happy_path(tmp_path, monkeypatch, capsys):
    mod = _load("ff_merge")
    head = "deadbeef1"
    calls = []
    state = {"pushed": False}

    def stateful_git(args, repo):
        key = tuple(args)
        calls.append(key)
        if key[:2] == ("status", "--porcelain"):
            return ""
        if key[:2] == ("rev-parse", "HEAD"):
            return head
        if key[:1] == ("fetch", ):
            return ""
        if key[:1] == ("ls-remote", ):
            tip = head if state["pushed"] else "old11111"
            return f"{tip}\trefs/heads/master\n"
        if key[:1] == ("push", ):
            state["pushed"] = True
            return ""
        if key[:1] == ("merge-base", ):
            return ""  # old11111 是 head 的祖先
        raise AssertionError(f"unexpected git call: {key}")

    monkeypatch.setattr(mod, "run_git", stateful_git)
    rc = mod.main(["--repo", str(tmp_path), "--remote", "gitee", "--to-branch", "master"])
    cap = capsys.readouterr()
    payload = json.loads(cap.out)
    assert rc == 0 and payload["status"] == "fast-forwarded" and payload["tip"] == head
    assert any(k[0] == "push" and k[2] == f"{head}:refs/heads/master" for k in calls)


# --------------------------------------------------------------- tag_release


def test_tag_release_pattern_rejects(tmp_path, capsys):
    mod = _load("tag_release")
    rc = mod.main(["--repo", str(tmp_path), "--tag", "0.3.0", "--remotes", "gitee"])
    err = capsys.readouterr().err.strip()
    assert rc == 1 and "v<major>.<minor>.<patch>" in err


def test_tag_release_local_conflict_stops(tmp_path, monkeypatch, capsys):
    mod = _load("tag_release")

    def git(args, repo):
        key = tuple(args)
        if key[:2] == ("rev-parse", "HEAD"):
            return (0, "head1111\n")
        if key[:3] == ("rev-parse", "--verify", "--quiet"):
            return (0, "other9999\n")  # 本地 tag 指向别处
        raise RuntimeError(f"unexpected: {key}")

    monkeypatch.setattr(mod, "run_git", git)
    rc = mod.main(["--repo", str(tmp_path), "--tag", "v0.3.0", "--remotes", "gitee"])
    err = capsys.readouterr().err.strip()
    assert rc == 1 and "停手要人" in err


def test_tag_release_remote_conflict_stops(tmp_path, monkeypatch, capsys):
    mod = _load("tag_release")
    state = {"tagged": False}

    def git(args, repo):
        key = tuple(args)
        if key[:2] == ("rev-parse", "HEAD"):
            return (0, "head1111\n")
        if key[:3] == ("rev-parse", "--verify", "--quiet"):
            return (0, "head1111\n") if state["tagged"] else (1, "")
        if key[:1] == ("tag", ):
            state["tagged"] = True
            return (0, "")
        if key[:1] == ("ls-remote", ):
            # 远端已有同名校验失败形态: tag 对象与 peeled 均指向别处
            return (0, "other9999\trefs/tags/v0.3.0\nother9999\trefs/tags/v0.3.0^{}\n")
        raise RuntimeError(f"unexpected: {key}")

    monkeypatch.setattr(mod, "run_git", git)
    rc = mod.main(["--repo", str(tmp_path), "--tag", "v0.3.0", "--remotes", "gitee"])
    err = capsys.readouterr().err.strip()
    assert rc == 1 and "停手要人" in err


def test_tag_release_reentrant(tmp_path, monkeypatch, capsys):
    mod = _load("tag_release")
    sha = "head1111"

    def git(args, repo):
        key = tuple(args)
        if key[:2] == ("rev-parse", "HEAD"):
            return (0, sha + "\n")
        if key[:3] == ("rev-parse", "--verify", "--quiet"):
            return (0, sha + "\n")  # 本地已指向 HEAD
        if key[:1] == ("ls-remote", ):
            return (0, f"{sha}\trefs/tags/v0.3.0\n{sha}\trefs/tags/v0.3.0^{{}}\n")
        raise RuntimeError(f"unexpected: {key}")

    monkeypatch.setattr(mod, "run_git", git)
    rc = mod.main(["--repo", str(tmp_path), "--tag", "v0.3.0", "--remotes", "gitee,github"])
    cap = capsys.readouterr()
    payload = json.loads(cap.out)
    assert rc == 0 and payload["remotes"] == {"gitee": "reentrant", "github": "reentrant"}


def test_tag_release_create_and_verify(tmp_path, monkeypatch, capsys):
    mod = _load("tag_release")
    sha = "head2222"
    state = {"tagged": False, "gitee": False, "github": False}

    def git(args, repo):
        key = tuple(args)
        if key[:2] == ("rev-parse", "HEAD"):
            return (0, sha + "\n")
        if key[:1] == ("tag", ):
            state["tagged"] = True
            return (0, "")
        if key[:3] == ("rev-parse", "--verify", "--quiet"):
            return (0, sha + "\n") if state["tagged"] else (1, "")
        if key[:1] == ("ls-remote", ):
            remote = key[1]
            if state[remote]:
                return (0, f"{sha}\trefs/tags/v0.3.0\n{sha}\trefs/tags/v0.3.0^{{}}\n")
            return (0, "")
        if key[:1] == ("push", ):
            state[key[1]] = True
            return (0, "")
        raise RuntimeError(f"unexpected: {key}")

    monkeypatch.setattr(mod, "run_git", git)
    rc = mod.main(["--repo", str(tmp_path), "--tag", "v0.3.0", "--remotes", "gitee,github"])
    cap = capsys.readouterr()
    payload = json.loads(cap.out)
    assert rc == 0 and state["tagged"] and payload["remotes"] == {"gitee": "pushed", "github": "pushed"}
    assert payload["sha"] == sha


# --------------------------------------------------------------- ci_gate


def test_ci_gate_judge_matrix():
    mod = _load("ci_gate")
    ok_run = {"name": "test", "status": "completed", "conclusion": "success"}
    assert mod.judge([]) == ("pending", [])
    assert mod.judge([ok_run]) == ("green", [])
    assert mod.judge([{"name": "test", "status": "in_progress", "conclusion": None}])[0] == "pending"
    bad = [{"name": "e2e", "status": "completed", "conclusion": "failure", "html_url": "u"}]
    state, lines = mod.judge(bad)
    assert state == "red" and "e2e: failure" in lines[0]
    state, _ = mod.judge([{"name": "x", "status": "completed", "conclusion": "weird"}])
    assert state == "pending"  # 未知结论按未收敛, 不当绿放行
    state, _ = mod.judge([ok_run, {"name": "w", "status": "completed", "conclusion": "skipped"}])
    assert state == "green"


def test_ci_gate_green_and_red_paths(tmp_path, monkeypatch, capsys):
    mod = _load("ci_gate")
    monkeypatch.setattr(
        mod, "fetch_check_runs", lambda sha, repo: [{
            "name": "t",
            "status": "completed",
            "conclusion": "success"
        }]
    )
    rc = mod.main(["--gh-repo", "o/r", "--sha", "abc1234", "--interval-sec", "0"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0 and payload["state"] == "green"

    monkeypatch.setattr(
        mod, "fetch_check_runs",
        lambda sha, repo: [{
            "name": "t",
            "status": "completed",
            "conclusion": "failure",
            "html_url": "u"
        }]
    )
    rc = mod.main(["--gh-repo", "o/r", "--sha", "abc1234", "--interval-sec", "0"])
    err = capsys.readouterr().err.strip()
    assert rc == 1 and "CI 红" in err and "t: failure" in err


def test_ci_gate_timeout_and_zero_runs(tmp_path, monkeypatch, capsys):
    mod = _load("ci_gate")
    monkeypatch.setattr(mod, "fetch_check_runs", lambda sha, repo: [])
    rc = mod.main(["--gh-repo", "o/r", "--sha", "abc1234", "--interval-sec", "0", "--timeout-min", "0"])
    err = capsys.readouterr().err.strip()
    assert rc == 2 and "全程零 check run" in err  # 全程零 run 不静默放行

    monkeypatch.setattr(
        mod, "fetch_check_runs", lambda sha, repo: [{
            "name": "t",
            "status": "in_progress",
            "conclusion": None
        }]
    )
    rc = mod.main(["--gh-repo", "o/r", "--sha", "abc1234", "--interval-sec", "0", "--timeout-min", "0"])
    err = capsys.readouterr().err.strip()
    assert rc == 2 and "超时" in err


def test_ci_gate_api_down(tmp_path, monkeypatch, capsys):
    mod = _load("ci_gate")
    monkeypatch.setattr(mod, "fetch_check_runs", lambda sha, repo: None)
    rc = mod.main(["--gh-repo", "o/r", "--sha", "abc1234"])
    assert rc == 3


# --------------------------------------------------------------- release_page


def test_release_page_degraded_no_token(tmp_path, monkeypatch, capsys):
    mod = _load("release_page")
    notes = tmp_path / "notes.md"
    notes.write_text("### Added\n- x", encoding="utf-8")
    monkeypatch.setattr(mod.os, "environ", {})
    rc = mod.main(
        ["--tag", "v0.3.0", "--notes-file",
         str(notes), "--gitee-repo", "o/n", "--gitee-token-env", "NOPE_TOKEN"]
    )
    cap = capsys.readouterr()  # 单次读取(二次调用会清空捕获)
    payload = json.loads(cap.out)
    assert rc == 0 and "degraded" in payload["results"]["gitee"] and "WARN" in cap.err


def test_release_page_gitee_failure_rc1(tmp_path, monkeypatch, capsys):
    mod = _load("release_page")
    notes = tmp_path / "notes.md"
    notes.write_text("x", encoding="utf-8")
    monkeypatch.setattr(mod.os, "environ", {"GITEE_TOKEN": "tok"})
    monkeypatch.setattr(mod, "http_json", lambda url, payload, method="POST": (422, "validation failed"))
    rc = mod.main(["--tag", "v0.3.0", "--notes-file", str(notes), "--gitee-repo", "o/n"])
    err = capsys.readouterr().err.strip()
    assert rc == 1 and "gitee 建页失败" in err


def test_release_page_reentrant_and_created(tmp_path, monkeypatch, capsys):
    mod = _load("release_page")
    notes = tmp_path / "notes.md"
    notes.write_text("x", encoding="utf-8")
    monkeypatch.setattr(mod.os, "environ", {"GITEE_TOKEN": "tok"})
    # GET 探测 200 -> reentrant; POST 201 -> created
    responses = {("GET", "releases/tags/v0.3.0"): (200, "{}"), ("POST", "releases"): (201, "{}")}

    def http(url, payload, method="POST"):
        for (m, frag), (status, body) in responses.items():
            if method == m and frag in url:
                return status, body
        return 500, "boom"

    monkeypatch.setattr(mod, "http_json", http)
    rc = mod.main(["--tag", "v0.3.0", "--notes-file", str(notes), "--gitee-repo", "o/n"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0 and payload["results"]["gitee"] == "reentrant"

    responses2 = {("GET", "releases/tags/v0.3.0"): (404, "not found"), ("POST", "releases"): (201, "{}")}
    monkeypatch.setattr(
        mod,
        "http_json",
        lambda url, payload, method="POST": next(
            (v for (m, frag), v in responses2.items() if method == m and frag in url), (500, "boom")
        )
    )
    rc = mod.main(["--tag", "v0.3.0", "--notes-file", str(notes), "--gitee-repo", "o/n"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0 and payload["results"]["gitee"] == "created"


def test_release_page_github_missing_gh(tmp_path, monkeypatch, capsys):
    mod = _load("release_page")
    notes = tmp_path / "notes.md"
    notes.write_text("x", encoding="utf-8")
    monkeypatch.setattr(mod.shutil, "which", lambda name: None)
    rc = mod.main(["--tag", "v0.3.0", "--notes-file", str(notes), "--github-repo", "o/n"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0 and "gh 不在 PATH" in payload["results"]["github"] and "允许滞后" in payload["results"]["github"]
