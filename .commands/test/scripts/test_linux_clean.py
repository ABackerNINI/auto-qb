"""linux_clean.py 守阵 —— testbed 三层清扫自动化(issue 26-11-13-0212; 计划 26-11-12-0152
§03 承诺行落地)的行为钉面。

只测**纯函数、生成的脚本文本与 CLI 两态**: 真删 docker 面属 `--yes` 本体, 守阵绝不触发
(默认演练只读, 但守阵连演练都不跑 —— 不依赖本机 docker 状态)。核心钉面: 白名单选择逻辑
(卷前缀 / 旧 tag 三保留规则 / 悬空「无容器引用」判据)、ban 名单(PT 词 + 生产镜像精确项 +
testbed 不误伤)、**面杀命令与容器删除 absence**(S5 纪律: system/volume/image prune 与
docker rm 在源码里出现即红)、一层执行复用 linux_ci.sweep_script(双条件单点不复制)、
演练默认(--yes 缺省 False)与 --safety 探针两态(无参 = 只读演练, 留在冒烟面)。

跑法: python <包>/scripts/test_linux_clean.py  ·  uv run pytest .commands -q --no-cov (test.pkg 口径)

## 测试计划
- test_safety_probe_kept_for_smoke          --safety rc 0 且不自认 action-without-args(无参 = 只读演练)
- test_help_prints_usage_rc0                --help 出用法 rc 0
- test_parse_args_defaults_dry_run          默认演练; --yes/--name/--build-cache 解析齐
- test_parse_args_rejects_unknown           未知旗标响亮拒绝(rc 2)
- test_unknown_flag_stops_via_main          main 对未知旗标落 [STOP] rc 2(不碰 docker)
- test_ban_list_blocks_pt_and_prod_image    ban 名单: PT 词命中 + 生产镜像精确命中; testbed/卷名不误伤
- test_volume_whitelist_prefix_only         卷白名单 ^auto-qb-: 白名单外不入选; 引用中不入选
- test_old_tag_keep_rules                   旧 tag 三保留规则(current hash8 / live 镜像 ID / latest)逐条钉
- test_dangling_requires_no_container_ref   悬空候选: 被任何容器引用的 ID 不入选
- test_execution_reuses_ci_sweep            一层执行复用 linux_ci.sweep_script(双条件单点, 不复制逻辑)
- test_main_sanitizes_name_before_targeted  --name 先过 linux_ci.sanitize_name, 且喂 targeted_script 的是 slug 非 name(数据流钉)
- test_ban_final_gate_pinned_in_main        ban 终闸循环钉在 main(删掉守阵必红)
- test_inventory_script_readonly_bounded    盘点脚本: 单根边界 / 无标记只盘点 / 双条件建议口径 / 无 rm
- test_targeted_script_refuses_live_pid     点名脚本: 路径钉死单根下 / pid 活拒(exit 30) / 只删点名一个
- test_no_face_kill_commands                面杀命令 absence: system/volume/image/container prune 与 prune -a 即红
- test_no_container_removal_no_force_rmi    docker rm(容器面)absence + rmi 永不带 -f(在用自然拒绝)
- test_images_calls_use_no_trunc            images 调用恒带 --no-trunc({{.ID}} 截短 vs full sha 失配回环, 实机抓出)
- test_engine_config_pinned                 config.toml test.linux-clean: script/timeout/doc 指针钉面
"""

from __future__ import annotations

import contextlib
import io
import re
import tomllib
from pathlib import Path

import pytest

import linux_clean

SOURCE = Path(linux_clean.__file__).read_text(encoding="utf-8")


def _capture_main(argv: list[str]) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = linux_clean.main(argv)
    return rc, buf.getvalue()


# ---- CLI 两态 ----


def test_safety_probe_kept_for_smoke() -> None:
    rc, out = _capture_main(["--safety"])
    assert rc == 0
    assert "action-without-args" not in out, "无参 = 只读演练(快、零副作用), 不自认危险, 留在冒烟面"


def test_help_prints_usage_rc0() -> None:
    rc, out = _capture_main(["--help"])
    assert rc == 0
    assert "用法" in out and "--yes" in out, "用法面带 --yes 与演练默认说明"


def test_parse_args_defaults_dry_run() -> None:
    assert linux_clean._parse_args([]) == (False, "", False), "无参 = 演练(保守默认, 黄金法则 2)"
    assert linux_clean._parse_args(["--yes"]) == (True, "", False)
    assert linux_clean._parse_args(["--yes", "--name", "aqb-1-2", "--build-cache"]) == (
        True,
        "aqb-1-2",
        True,
    )


def test_parse_args_rejects_unknown() -> None:
    with pytest.raises(ValueError):
        linux_clean._parse_args(["--force"])
    with pytest.raises(ValueError):
        linux_clean._parse_args(["--name"]),  # --name 缺值


def test_unknown_flag_stops_via_main() -> None:
    rc, out = _capture_main(["--force"])
    assert rc == 2 and "[STOP]" in out


# ---- 白名单选择逻辑(纯函数) ----


def test_ban_list_blocks_pt_and_prod_image() -> None:
    # 宿主现状点名(S5 手工轮实证的 PT 面): 词命中一律拒
    for name in (
        "lscr.io/linuxserver/qbittorrent:latest",
        "lscr.io/linuxserver/qbittorrent:5.1.4-r3-ls453",
        "iyuucn/iyuuplus-dev:latest",
        "ghcr.io/wenfer/bitcake:latest",
        "eternalcurse/pt-accelerator:latest",
        "ghcr.io/echoping07/downonly:latest",
    ):
        assert linux_clean.banned_reason(name), f"PT 面必须命中 ban 名单: {name}"
    assert linux_clean.banned_reason("auto-qb"), "生产应用镜像精确禁删"
    assert linux_clean.banned_reason("AUTO-QB") is not None, "ban 匹配大小写不敏感"
    # BAN_SUBSTRINGS 全词钉(名单可静默缩水的缺口): 每个词一个合成名
    for word in ("qbittorrent", "transmission", "deluge", "bitcake", "iyuu", "downonly", "accelerator", "resilio"):
        assert linux_clean.banned_reason(f"example/{word}-tool:1") is not None, f"ban 词 {word} 必须生效"
    assert linux_clean.banned_reason("auto-qb-testbed:073a459e") is None, "testbed 仓不误伤"
    assert linux_clean.banned_reason("auto-qb-uv-cache") is None, "本体系卷名不误伤"


def test_volume_whitelist_prefix_only() -> None:
    assert linux_clean.orphan_volumes(["auto-qb-uv-cache"], {}) == ["auto-qb-uv-cache"]
    assert linux_clean.orphan_volumes(["auto-qb-uv-cache"], {"auto-qb-uv-cache": ["c1"]}) == [], \
        "容器引用中不入选"
    assert linux_clean.orphan_volumes(["auto-qb", "pt-data", "qb-cache", "auto_qb_x"], {}) == [], \
        "白名单外一律不入选(^auto-qb- 带连字符前缀)"
    assert linux_clean.orphan_volumes(["auto-qb-uv-cache", "auto-qb-tmp"], {}) == \
        ["auto-qb-uv-cache", "auto-qb-tmp"]


def test_old_tag_keep_rules() -> None:
    images = [
        ("auto-qb-testbed:48e6fda6", "sha256:new", "2.95GB"),  # current hash8 -> keep
        ("auto-qb-testbed:latest", "sha256:new", "2.95GB"),  # latest -> keep
        ("auto-qb-testbed:073a459e", "sha256:old", "2.95GB"),  # 旧 hash 且非活面 -> 候选
        ("auto-qb-testbed:deadbeef", "sha256:new", "2.95GB"),  # 同 ID 活面 -> keep
        ("auto-qb-testbed:<none>", "sha256:x", "1GB"),  # 畸形 tag 不入选
        ("ghcr.io/astral-sh/uv:python3.13-bookworm-slim", "sha256:y", "256MB"),  # 其它仓不碰
        ("lscr.io/linuxserver/qbittorrent:latest", "sha256:z", "291MB"),  # PT 仓不碰
    ]
    cands = linux_clean.old_tag_candidates(images, "48e6fda6", "sha256:new")
    assert cands == ["auto-qb-testbed:073a459e"], "三保留规则之外的旧 tag 才是候选"
    # 容器不在跑(live_image_id=None): 只剩 hash8/latest 两保留, 活面规则不误放
    cands2 = linux_clean.old_tag_candidates(images, "48e6fda6", None)
    assert "auto-qb-testbed:deadbeef" in cands2 and "auto-qb-testbed:48e6fda6" not in cands2


def test_dangling_requires_no_container_ref() -> None:
    out = "sha256:a 402.1MB 2 months ago\nsha256:b 10MB 3 days ago\n"
    cands = linux_clean.dangling_candidates(out, {"sha256:a"})
    assert [c[0] for c in cands] == ["sha256:b"], "被任何容器(含退出态)引用的悬空 ID 不入选"
    assert cands[0][1] == "10MB" and cands[0][2] == "3 days ago", "尺寸/时间列进演练清单"


# ---- 一层复用与注入闸 ----


def test_execution_reuses_ci_sweep() -> None:
    assert "linux_ci.sweep_script(SWEEP_AGE_SECONDS)" in SOURCE, \
        "一层执行复用 linux_ci 双条件单点(pid 死 + mtime 12h), 不复制逻辑"


def test_main_sanitizes_name_before_targeted() -> None:
    assert re.search(r"slug = linux_ci\.sanitize_name\(name\)", SOURCE), \
        "--name 必须先过 sanitize_name(slug 安全集)再进 targeted_script —— 路径注入闸"
    assert "targeted_script(slug)" in SOURCE and "targeted_script(name)" not in SOURCE, \
        "数据流钉死: 喂给 targeted_script 的必须是 sanitize 后的 slug, 不是原始 name" \
        "(只钉 sanitize 调用存在不钉结果去向的弱钉已修: 改回 targeted_script(name) 必红)"


def test_ban_final_gate_pinned_in_main() -> None:
    assert "for item in old_tags + orphans:" in SOURCE and "banned_reason(item)" in SOURCE, \
        "ban 终闸循环钉死在 main 里 —— 删掉终闸守阵必须红(白名单选择逻辑改坏时唯一兜底, " \
        "不能是无守阵钉的「最后一道闸」)"


# ---- 容器内脚本文本钉面 ----


def test_inventory_script_readonly_bounded() -> None:
    script = linux_clean.inventory_script(linux_clean.SWEEP_AGE_SECONDS)
    root = linux_clean.TESTS_ROOT
    assert f'root="{root}"' in script and "$root" in script, "盘点只看 /root/auto-qb-tests/ 单根"
    assert '[ ! -f "$m" ]' in script, "无标记目录只盘点不碰(处置走 --name 点名)"
    assert "kill -0" in script and "-ge" in script, "可回收建议 = 双条件口径(pid 死 + 龄超限)"
    assert "rm -rf" not in script, "盘点脚本只读, 无删除动作"
    assert f"-ge {linux_clean.SWEEP_AGE_SECONDS}" in script, "阈值单点透传(linux_ci.SWEEP_AGE_SECONDS)"


def test_targeted_script_refuses_live_pid() -> None:
    script = linux_clean.targeted_script("aqb-1")
    root = linux_clean.TESTS_ROOT
    assert f'd="{root}/aqb-1"' in script, "点名路径钉死在单根下(sanitize 过的 slug)"
    assert "kill -0" in script and "exit 30" in script, "会话仍在跑拒绝(D5)"
    assert script.count("rm -rf") == 1, "只删点名这一个目录, 不钻子树不越根"


# ---- S5 纪律 absence 钉(源码级) ----


def test_no_face_kill_commands() -> None:
    # 检查代码体(摘掉模块 docstring —— 纪律文字面本身要提到禁词, ban 的是执行路径)
    assert SOURCE.lstrip().startswith('"""'), "body 锚点依赖模块 docstring 是文件首个三引号对(锚在位守卫)"
    body = SOURCE.split('"""', 2)[2]
    for banned in ("system prune", "volume prune", "image prune", "container prune", "prune -a"):
        assert banned not in body, f"面杀命令禁止出现在执行路径: {banned}(S5 纪律, 白名单点名式)"
    # ! argv 列表形态才是本仓 docker 调用的真实写法 —— 只钉散文形态(带空格子串)对
    #   '"system", "prune"' 形态的回归失明, 两种形态都钉
    assert not re.search(r'"(system|volume|image|container)",\s*"prune"', body), \
        "面杀命令(argv 列表形态)禁止出现 —— S5 纪律最危险的回归路径"
    assert not re.search(r'"prune",\s*"-(?!f")', body), \
        "prune 带旗标(-a 等)禁止出现; 唯一放行 = builder prune -f"
    # 唯一放行的 prune = builder prune -f(opt-in 构建缓存, S5 手工同款)
    assert '"builder", "prune", "-f"' in body


def test_no_container_removal_no_force_rmi() -> None:
    body = SOURCE.split('"""', 2)[2]
    assert not re.search(r'"docker",\s*"rm"', body), "任何容器一律不删(docker rm 不出现)"
    assert not re.search(r'"rmi",\s*"-f"', body), "rmi 不带 -f: 在用镜像由 docker 自然拒绝, 不强删"


def test_images_calls_use_no_trunc() -> None:
    body = SOURCE.split('"""', 2)[2]
    assert body.count('"--no-trunc"') == 3, \
        "docker images 的 {{.ID}} 与 docker ps 的 {{.Image}}(镜像无 tag 时)默认截短 12 位, " \
        "活面规则/悬空判据按 full sha 比对必须 --no-trunc(images 枚举/悬空枚举/ps 引用面共 3 处; " \
        "缺了比较恒失配: 活面 tag 误列候选或引用中的悬空 ID 漏筛 —— 实机演练抓出)"


# ---- 引擎面 ----


def test_engine_config_pinned() -> None:
    cfg_path = Path(linux_clean.__file__).resolve().parents[1] / "config.toml"
    with cfg_path.open("rb") as fh:
        cfg = tomllib.load(fh)
    task = cfg["tasks"]["test.linux-clean"]
    assert task["script"] == "linux_clean.py"
    assert task["timeout"] == 300
    assert task["doc"].endswith("26-11-12-0152-plan-linux-testbed-docker.html"), \
        "doc 指针钉计划单点"
    assert "--yes" in task["note"], "note 里带落实用法(演练默认的使用姿势)"
