"""存量评审 R4 的路线机械面: review.lane —— 认领/快照/复核/勾选/终态 + manifest 生成。

计划 26-11-05-2335 (legacy-code-review-4) 的配套脚本 (拍板 D13/D15):
- manifest: 生成 manifest.json —— 批次到文件精确矩阵 + 每批撞车底册切片(R2 终表 + Open issues
            按文件 basename 映射) + 覆盖守卫(全部分层范围内文件恰被一批认领, 重叠/漏配即失败)。
- claim:    认领路线。freeze 机械解析 = 计划文件首个 commit(diff-filter=A), 校验为其祖先且
            本地 HEAD == 远端 tip(ls-remote 现查, 防在落后/分叉基线上认领); 写 route JSON。
- start:    git archive <freeze> 导出评审快照到 repo 外目录(不切分支不动 HEAD, 不扰动
            develop), 写 .snapshot-hash 标记, 打印存量适配三件套与首批文件。
- verify:   每批派遣前/交回后复核 —— 快照存在且标记吻合 / 工作树净(仅 legacy-review4/ 内
            允许脏) / 状态一致; 打印下一批派遣材料。
- batch:    勾选批次完成(--findings 记发现数)。
- done:     全批完成后校验 findings/小结在盘, 翻终态并提示 ship.commit。
- smoke:    全环真冒烟(真实 claim/start/verify/batch/done 含负例断言), 结束清理全部痕迹。

退出码: 0=通过; 1=校验失败(状态/守卫不满足); 2=用法/环境错误。--dry-run 只演算不落盘
(start 的 dry-run 在临时目录真实解包一份快照后删除, 验证 archive 链路)。

快照与发现约定(计划 §04): reviewer 只读快照目录; findings 七字段 schema 与 review.check
一致, 校验用 `commands run review.check --findings <json> --root <快照目录>`。
"""

from __future__ import annotations

import argparse
import fnmatch
import io
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

PLAN_REL = "memory-bank/plans/26-11-05-2335-plan-legacy-code-review-4.html"
LANE_DIR = "memory-bank/reports/attachments/legacy-review4"
R2_REPORT = "memory-bank/reports/26-10-30-0237-report-full-code-review-2.html"
ISSUES_DIR = "memory-bank/issues"
SNAP_ROOT_NAME = "auto-qb-review4-snap"
ROUTES = ("R1", "R2", "R3", "R4", "R5")
BRANCH_REQUIRED = "develop"

# 分层范围: 评审对象 = src 代码文件 + 根 scripts; tests/.commands/assets 明确排除(计划 §03)
CODE_EXTS = (".py", ".js", ".css", ".html")


def _is_scoped(rel: str) -> bool:
    if rel.startswith("scripts/") and rel.endswith(".py"):
        return True
    if not rel.startswith("src/"):
        return False
    if "__pycache__" in rel:
        return False
    if rel.startswith("src/auto_qb/webui/static/shared/vendor/"):
        return False  # 第三方发行物(vue/uPlot min), 不属评审对象
    return rel.endswith(CODE_EXTS)


# --------------------------------------------------------------------------- 批次定义
# exact = 精确路径(posix); globs = fnmatch(posix, 大小写敏感)。定义必须互斥且覆盖全范围,
# manifest 生成时守卫断言(重叠/漏配 -> rc=1 列出清单)。depth: full=逐文件精评 /
# contract=py↔js 契约与机制 / mechanism=机制红线抽查(不逐行) / scan=快扫。


def _B(bid: str, route: str, title: str, depth: str, exact: tuple[str, ...] = (), globs: tuple[str, ...] = ()) -> dict:
    return {"id": bid, "route": route, "title": title, "depth": depth, "exact": list(exact), "globs": list(globs)}


P = "src/auto_qb/"
BATCH_DEFS: list[dict] = [
    # ---- R1 core ----
    _B("R1-1", "R1", "内核执行面: qbmanager/taskqueue/module/qbapi/state + core 根杂件", "full",
       exact=("src/auto-qb.py", P + "__init__.py", P + "__main__.py", P + "cli.py", P + "core/__init__.py",
              P + "core/qbmanager.py", P + "core/taskqueue.py", P + "core/module.py",
              P + "core/qbapi.py", P + "core/state.py", P + "core/qbclient.py",
              P + "core/episodes.py", P + "core/exporter.py")),
    _B("R1-2", "R1", "迁移执行: relocate_units/relocate_exec/relocate_common", "full",
       exact=(P + "core/modules/relocate_units.py", P + "core/modules/relocate_exec.py",
              P + "core/modules/relocate_common.py")),
    _B("R1-3", "R1", "迁移规划与生命期: relocate_mod/plan/probe/proof/lifecycle", "full",
       exact=(P + "core/modules/relocate_mod.py", P + "core/modules/relocate_plan.py",
              P + "core/modules/relocate_probe.py", P + "core/modules/relocate_proof.py",
              P + "core/modules/relocate_lifecycle.py")),
    _B("R1-4", "R1", "traffic 存取: store/agg/codec/common/paths/grid/limits/curves", "full",
       exact=(P + "core/traffic_store.py", P + "core/traffic_store_agg.py", P + "core/traffic_store_codec.py",
              P + "core/traffic_store_common.py", P + "core/traffic_store_paths.py",
              P + "core/traffic_grid.py", P + "core/traffic_limits.py", P + "core/curves.py")),
    _B("R1-5", "R1", "traffic 采样: sample_mod/agg/blocks/common/snapshot + traffic_source", "full",
       exact=(P + "core/modules/traffic_sample_mod.py", P + "core/modules/traffic_sample_agg.py",
              P + "core/modules/traffic_sample_blocks.py", P + "core/modules/traffic_sample_common.py",
              P + "core/modules/traffic_snapshot_mod.py"),
       globs=(P + "core/traffic_source/*.py",)),
    _B("R1-6", "R1", "分组与规则模块: grouping_mod/rules_mod/tvshows", "full",
       exact=(P + "core/modules/grouping_mod.py", P + "core/modules/rules_mod.py", P + "core/tvshows.py")),
    _B("R1-7", "R1", "ops 与维护面: ops_*/maintenance/fuse/speed_curve/logging/notify/tracker", "full",
       exact=tuple(P + "core/modules/" + n for n in (
           "__init__.py", "fuse_mod.py", "logging_mod.py", "maintenance_mod.py", "notify_mod.py",
           "ops_common.py", "ops_jobs.py", "ops_mod.py", "ops_skip.py", "ops_verdict.py",
           "speed_curve_mod.py", "tracker_mod.py"))),
    # ---- R2 config · rules · infra ----
    _B("R2-1", "R2", "校验面: config/validation 全部", "full",
       globs=(P + "config/validation/*.py",)),
    _B("R2-2", "R2", "schema 与装载: schema 全部 + loaders + models", "full",
       globs=(P + "config/schema/*.py",),
       exact=(P + "config/loaders.py", P + "config/models.py")),
    _B("R2-3", "R2", "写入与迁移: writer/migrations/compat/errors/impact/site_presets", "full",
       exact=(P + "config/__init__.py", P + "config/compat.py", P + "config/errors.py",
              P + "config/impact.py", P + "config/migrations.py", P + "config/site_presets.py",
              P + "config/writer.py")),
    _B("R2-4", "R2", "rules 全域: base/conditions/registry/checking_meta + expr + actions", "full",
       globs=(P + "rules/*.py", P + "rules/expr/*.py", P + "rules/actions/*.py")),
    _B("R2-5", "R2", "infra 存储: alias_fs/file_access", "full",
       exact=(P + "infra/alias_fs.py", P + "infra/file_access.py")),
    _B("R2-6", "R2", "infra 工具: utils*/notify/locking/logging/journal/recovery 等", "full",
       exact=tuple(P + "infra/" + n for n in (
           "__init__.py", "autostart.py", "errors.py", "locking.py", "logging.py", "notify.py",
           "port_owner.py", "relocate_journal.py", "store_recovery.py", "utils.py",
           "utils_parse.py", "utils_paths.py", "versioning.py"))),
    # ---- R3 hr · 新代码 ----
    _B("R3-1", "R3", "transfer 全域(新模块) + torrents/store", "full",
       globs=(P + "transfer/*.py", P + "transfer/adapters/*.py"),
       exact=(P + "torrents/store.py",)),
    _B("R3-2", "R3", "torrents 杂件 + tray + cli + tools", "full",
       exact=(P + "torrents/__init__.py", P + "torrents/compat.py", P + "torrents/record.py",
              P + "torrents/view.py", P + "tray/__init__.py", P + "tray/app.py",
              P + "tools/__init__.py", P + "tools/finalize_watch.py"),
       globs=(P + "tray/*.py", P + "tools/*.py")),
    _B("R3-3", "R3", "hr service 族: service_wave/service/service_common/service_status/module", "full",
       exact=(P + "hr/service_wave.py", P + "hr/service.py", P + "hr/service_common.py",
              P + "hr/service_status.py", P + "hr/module.py")),
    _B("R3-4", "R3", "hr 模型状态: model/status/resolve", "full",
       exact=(P + "hr/model.py", P + "hr/status.py", P + "hr/resolve.py")),
    _B("R3-5", "R3", "hr 运行时: runtime/server/channel/worker/threadlifecycle/queue/events", "full",
       exact=(P + "hr/runtime.py", P + "hr/server.py", P + "hr/channel.py", P + "hr/worker.py",
              P + "hr/threadlifecycle.py", P + "hr/queue.py", P + "hr/events.py")),
    _B("R3-6", "R3", "hr 取数解析: discovery/report/parse/fetcher/store/bencode/log/ratelimit + adapters", "full",
       exact=(P + "hr/__init__.py", P + "hr/bencode.py", P + "hr/discovery.py", P + "hr/fetcher.py",
              P + "hr/log.py", P + "hr/parse.py", P + "hr/ratelimit.py", P + "hr/report.py",
              P + "hr/store.py"),
       globs=(P + "hr/adapters/*.py",)),
    # ---- R4 webui-py · CSS 机制 ----
    _B("R4-1", "R4", "webui commands 面: commands*/runtime_commands", "full",
       exact=tuple(P + "webui/" + n for n in (
           "commands.py", "commands_common.py", "commands_config.py", "commands_limit.py",
           "commands_logs.py", "commands_torrents.py", "runtime_commands.py"))),
    _B("R4-2", "R4", "webui 视图与运行时: runtime*/views*/tool_client/module/relocate_chain", "full",
       exact=tuple(P + "webui/" + n for n in (
           "__init__.py", "module.py", "relocate_chain.py", "runtime.py", "runtime_common.py",
           "runtime_stream.py", "runtime_views.py", "tool_client.py", "views.py", "views_common.py",
           "views_episodes.py", "views_group.py", "views_relocate.py", "views_row.py", "views_search.py"))),
    _B("R4-3", "R4", "webui server 全域: factory/auth/context/routes/traffic_qb", "full",
       globs=(P + "webui/server/*.py", P + "webui/server/routes/*.py")),
    _B("R4-4", "R4", "CSS 机制面 + 模板 HTML(减配: 加载序/特异性冲突/守阵对齐/双皮肤一致)", "mechanism",
       globs=(P + "webui/static/*.css", P + "webui/static/**/*.css", P + "webui/static/shared/tpl/*.html",
              P + "webui/static/*/index.html", P + "webui/static/fx/showcase.html")),
    # ---- R5 static 契约 · scripts ----
    _B("R5-1", "R5", "shared 启动与状态: app/state/boot/lifecycle/auth/polling/fetch_low/ui_feedback", "contract",
       exact=tuple(P + "webui/static/shared/" + n for n in (
           "app.js", "state.js", "boot.js", "lifecycle.js", "auth.js", "polling.js",
           "fetch_low.js", "ui_feedback.js"))),
    _B("R5-2", "R5", "shared 菜单·触发·命令链: menu/triggers/commands*/ctx_menu*/view/overlay_fit/ctl_bits/scope_audit/shortcuts(+panel)", "contract",
       exact=tuple(P + "webui/static/shared/" + n for n in (
           "menu.js", "triggers.js", "scope_audit.js", "commands.js", "commands_send.js",
           "commands_optimistic.js", "view.js", "ctx_menu.js", "ctx_menu_custom.js",
           "overlay_fit.js", "ctl_bits.js", "shortcuts.js", "shortcuts_panel.js"))),
    _B("R5-3", "R5", "shared 表格与列: table/dt_table/columns*/sort/filters/selection/format/rowlang/decorate", "contract",
       exact=tuple(P + "webui/static/shared/" + n for n in (
           "table.js", "dt_table.js", "columns.js", "columns_computed.js", "columns_drag.js",
           "columns_menu.js", "columns_persist.js", "columns_grid.js", "sort.js", "filters.js",
           "selection.js", "format.js", "rowlang.js", "decorate.js"))),
    _B("R5-4", "R5", "shared drawer 族: drawer/drawer_templates/drawer_store/drawer_{general,rows,files,head}", "contract",
       exact=tuple(P + "webui/static/shared/" + n for n in (
           "drawer.js", "drawer_templates.js", "drawer_store.js", "drawer_general.js",
           "drawer_rows.js", "drawer_files.js", "drawer_head.js"))),
    _B("R5-5", "R5", "shared drawer 模板·general 与 trackers(01-09 号)", "contract",
       globs=(P + "webui/static/shared/drawer_tpl/0[1-9]-*.js",)),
    _B("R5-11", "R5", "shared drawer 模板·content 与 peers(10-12/90 号)", "contract",
       globs=(P + "webui/static/shared/drawer_tpl/1[0-9]-*.js", P + "webui/static/shared/drawer_tpl/9[0-9]-*.js")),
    _B("R5-6", "R5", "shared 对话框与流转: dialogs/add_torrent/dialogs_{meta,history}/delete_flow/transfer_{flow,targets}/relocate_chain", "contract",
       exact=tuple(P + "webui/static/shared/" + n for n in (
           "dialogs.js", "add_torrent.js", "dialogs_meta.js", "dialogs_history.js",
           "delete_flow.js", "transfer_flow.js", "transfer_targets.js", "relocate_chain.js"))),
    _B("R5-7", "R5", "shared config 族: config_rules/config_editor{,_curve,_form,_tree}/config_hub{,_tm,_tracker,_hr}", "contract",
       exact=tuple(P + "webui/static/shared/" + n for n in (
           "config_rules.js", "config_editor.js", "config_editor_curve.js", "config_editor_form.js",
           "config_editor_tree.js", "config_hub.js", "config_hub_tm.js", "config_hub_tracker.js",
           "config_hub_hr.js"))),
    _B("R5-8", "R5", "图表·hr 面板·快捷键引擎·fx: qb_traffic_chart/hr_status/hr/shows/traffic_card/shortcuts_engine + fx/皮肤 js", "contract",
       exact=(P + "webui/static/shared/qb_traffic_chart.js", P + "webui/static/shared/hr_status.js",
              P + "webui/static/shared/hr.js", P + "webui/static/shared/shows.js",
              P + "webui/static/shared/traffic_card.js", P + "webui/static/shared/shortcuts_engine.js"),
       globs=(P + "webui/static/shared/fx/*.js", P + "webui/static/flux/*.js",
              P + "webui/static/atlas/*.js", P + "webui/static/console/*.js",
              P + "webui/static/prism/*.js")),
    _B("R5-9", "R5", "scripts 快扫: sim_* 全族", "scan",
       globs=("scripts/sim_*.py",)),
    _B("R5-10", "R5", "scripts 快扫: qb_capture*/ui_harness/检查与实验散件", "scan",
       exact=tuple("scripts/" + n for n in (
           "bench_expr.py", "check_command_drift.py", "check_context_caps.py", "dev_webui.py",
           "e2e_selfcheck.py", "gen_ext_icons.py", "hr_ext_stub.py", "hr_fetch_experiment.py",
           "port_kill.py", "qb_capture.py", "qb_capture_cli.py", "qb_capture_core.py",
           "sync_agent_skills.py", "ui_content_map.py", "ui_harness.py", "update_config_key_surface.py"))),
]


# --------------------------------------------------------------------------- 基础设施


def _die(msg: str) -> None:
    print(f"[FAIL] {msg}", file=sys.stderr)
    raise SystemExit(2)


def _fail(msg: str) -> None:
    print(f"[FAIL] {msg}", file=sys.stderr)
    raise SystemExit(1)


def _flat(value) -> str:
    return "".join(ch if ch.isprintable() else " " for ch in str(value))


def _now() -> str:
    return datetime.now().strftime("%y-%m-%d-%H%M")


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    cmd = ["git", "-c", "core.quotepath=off", *args]
    try:
        proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace")
    except OSError as exc:
        _die(f"git 启动失败: {exc}")
    if check and proc.returncode != 0:
        _die(f"git {' '.join(args)} 失败: {proc.stderr.strip()}")
    return proc


def _git_bytes(root: Path, *args: str) -> bytes:
    cmd = ["git", "-c", "core.quotepath=off", *args]
    try:
        proc = subprocess.run(cmd, cwd=root, capture_output=True)
    except OSError as exc:
        _die(f"git 启动失败: {exc}")
    if proc.returncode != 0:
        _die(f"git {' '.join(args)} 失败: {proc.stderr.decode('utf-8', 'replace').strip()}")
    return proc.stdout


def _resolve_root(explicit: str | None) -> Path:
    if explicit:
        root = Path(explicit).resolve()
        if not (root / ".git").exists():
            _die(f"--root {root} 不是 git 仓库(缺 .git)")
        return root
    proc = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        _die("当前目录不在 git 仓库内(也没有 --root)")
    return Path(proc.stdout.strip()).resolve()


def _porcelain(root: Path) -> list[str]:
    out = _git(root, "status", "--porcelain").stdout
    rows = []
    for line in out.splitlines():
        if len(line) > 3:
            rows.append((line[:2], line[3:]))
    return rows


def _require_clean(root: Path, allow_lane: bool = False) -> None:
    """树净守卫。allow_lane=True 时仅放行 legacy-review4/ 下的路径(路线期间 findings/状态单点的正常落盘)。"""
    rows = _porcelain(root)
    if not rows:
        return
    if allow_lane:
        bad = [p for st, p in rows if not p.startswith(LANE_DIR + "/")]
        if not bad:
            return
        _fail("工作树在 legacy-review4/ 之外有未提交改动, 先处理再继续:\n  " + "\n  ".join(f"{st} {p}" for st, p in rows))
    _fail("工作树不净(先 commit/stash 处理):\n  " + "\n  ".join(f"{st} {p}" for st, p in rows))


def _require_branch(root: Path) -> str:
    branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if branch != BRANCH_REQUIRED:
        _fail(f"当前分支 {branch} != {BRANCH_REQUIRED}, 路线认领与执行一律在 {BRANCH_REQUIRED} 上")
    return branch


def _resolve_freeze(root: Path) -> str:
    plan = root / PLAN_REL
    if not plan.is_file():
        _die(f"计划文件不在盘: {PLAN_REL}")
    out = _git(root, "log", "--diff-filter=A", "--format=%H", "--", PLAN_REL).stdout.split()
    if not out:
        _die(f"解析不到计划文件的首个 commit({PLAN_REL} 未被任何 commit 添加?)")
    return out[-1]  # 最早一次添加(防未来异常重加)


def _require_ancestor(root: Path, freeze: str) -> None:
    proc = _git(root, "merge-base", "--is-ancestor", freeze, "HEAD", check=False)
    if proc.returncode != 0:
        _fail(f"freeze {freeze} 不是 HEAD 的祖先(历史被改写?), 停手人工介入")


def _require_tip(root: Path, remote: str) -> None:
    branch = _require_branch(root)
    head = _git(root, "rev-parse", "HEAD").stdout.strip()
    proc = _git(root, "ls-remote", remote, f"refs/heads/{branch}", check=False)
    if proc.returncode != 0:
        _fail(f"ls-remote {remote} 失败(离线? 先 commands run my-commit-flow.sync): {proc.stderr.strip()}")
    tip = ""
    for line in proc.stdout.splitlines():
        h, _, ref = line.partition("\t")
        if ref.strip() == f"refs/heads/{branch}":
            tip = h.strip().lower()
    if not tip:
        _fail(f"ls-remote 输出里没有 refs/heads/{branch}")
    if head.lower() != tip:
        _fail(f"本地 HEAD {head[:12]} != 远端 {remote}/{branch} tip {tip[:12]} —— 先 commands run my-commit-flow.sync 再认领")


def _load_manifest(root: Path) -> dict:
    path = root / LANE_DIR / "manifest.json"
    if not path.is_file():
        _die(f"manifest 不存在: {LANE_DIR}/manifest.json —— 先跑 review.lane.manifest 生成")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        _die(f"manifest 解析失败: {exc}")
    if not data.get("coverage", {}).get("ok"):
        _fail("manifest 覆盖守卫未通过(coverage.ok != true), 禁止认领 —— 重跑 review.lane.manifest")
    return data


def _load_route(root: Path, route: str) -> dict:
    path = root / LANE_DIR / f"route-{route}.json"
    if not path.is_file():
        _fail(f"路线未认领: {LANE_DIR}/route-{route}.json 不存在 —— 先 review.lane.claim")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        _die(f"route JSON 解析失败: {exc}")


def _save_route(root: Path, route: str, data: dict) -> None:
    path = root / LANE_DIR / f"route-{route}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _snapshot_dir(root: Path, explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    return (root.parent / SNAP_ROOT_NAME / root.name).resolve()


def _batches_of(manifest: dict, route: str) -> list[dict]:
    return [b for b in manifest["batches"] if b["route"] == route]


# --------------------------------------------------------------------------- manifest


def _count_lines(path: Path) -> int:
    try:
        data = path.read_bytes()
    except OSError:
        return -1
    if not data:
        return 0
    return data.count(b"\n") + (0 if data.endswith(b"\n") else 1)


def _strip_tags(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def _parse_r2(root: Path, all_files: list[dict]) -> list[dict]:
    """R2 终表切片: ID -> 命中的 basename 集合 + 一句话。找不到终表节则返回空(不静默, 打警告)。"""
    path = root / R2_REPORT
    if not path.is_file():
        print(f"[warn] R2 报告不在盘: {R2_REPORT}, 底册切片将没有 R2 条目")
        return []
    text = path.read_text(encoding="utf-8")
    start = text.find("8.1 合并终表")
    if start < 0:
        print("[warn] R2 报告里找不到「8.1 合并终表」节, 底册切片将没有 R2 条目")
        return []
    end = text.find("8.2 ", start)
    section = text[start:end if end > start else len(text)]
    rows = re.findall(r"<td>([A-Z]{1,2}-\d{2})</td>(.*?)</tr>", section, re.S)
    base_of = {f["path"]: f["path"].rsplit("/", 1)[-1] for f in all_files}
    entries = []
    for fid, rest in rows:
        rowtext = _strip_tags(rest)
        hits = sorted({p for p, b in base_of.items() if b in rowtext})
        entries.append({"id": fid, "files": hits, "gist": rowtext[:160]})
    return entries


def _parse_issues(root: Path, all_files: list[dict]) -> list[dict]:
    """Open/In Progress issue 底册: 按正文/标题 basename 命中映射(辅助指针, S6 终验兜底)。"""
    issues_dir = root / ISSUES_DIR
    if not issues_dir.is_dir():
        print(f"[warn] issues 目录不在盘: {ISSUES_DIR}, 底册切片将没有 issue 条目")
        return []
    base_of = {f["path"]: f["path"].rsplit("/", 1)[-1] for f in all_files}
    entries = []
    for path in sorted(issues_dir.glob("*.html")):
        try:
            raw = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        m_title = re.search(r'<meta name="issue-title" content="([^"]*)"', raw)
        m_status = re.search(r'<meta name="issue-status" content="([^"]*)"', raw)
        m_type = re.search(r'<meta name="issue-type" content="([^"]*)"', raw)
        status = m_status.group(1) if m_status else "?"
        if status not in ("Open", "In Progress"):
            continue
        text = _strip_tags(raw)
        hits = sorted({b for b in set(base_of.values()) if b in text})
        if not hits:
            continue
        entries.append({
            "issue": f"{ISSUES_DIR}/{path.name}",
            "id": path.name.split("-", 3)[-1].rsplit(".", 1)[0] if "-" in path.name else path.name,
            "type": m_type.group(1) if m_type else "?",
            "title": _flat(m_title.group(1))[:80] if m_title else "?",
            "status": status,
            "files": hits,
        })
    return entries


def cmd_manifest(args: argparse.Namespace) -> int:
    root = _resolve_root(args.root)
    if not (root / PLAN_REL).is_file():
        _die(f"计划文件不在盘: {PLAN_REL}")
    # 1) 分层范围盘点
    scoped: list[str] = []
    for dirpath, dirnames, filenames in __import__("os").walk(root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for name in filenames:
            rel = Path(dirpath, name).resolve().relative_to(root).as_posix()
            if _is_scoped(rel):
                scoped.append(rel)
    scoped.sort()
    # 2) 按批次定义分配(互斥 + 全覆盖)
    files_of: dict[str, list[dict]] = {b["id"]: [] for b in BATCH_DEFS}
    overlap: list[str] = []
    unassigned: list[str] = []
    for rel in scoped:
        hits = [b["id"] for b in BATCH_DEFS if rel in b["exact"] or any(fnmatch.fnmatchcase(rel, g) for g in b["globs"])]
        if len(hits) > 1:
            overlap.append(f"{rel} -> {','.join(hits)}")
        elif not hits:
            unassigned.append(rel)
        else:
            lines = _count_lines(root / rel)
            files_of[hits[0]].append({"path": rel, "lines": lines})
    if overlap or unassigned:
        if overlap:
            print(f"[FAIL] 批次定义重叠 {len(overlap)} 处:")
            for row in overlap:
                print(f"  {row}")
        if unassigned:
            print(f"[FAIL] 范围内未分配文件 {len(unassigned)} 个(补进对应批次定义):")
            for rel in unassigned:
                print(f"  {rel}")
        raise SystemExit(1)
    all_files = [f for b in BATCH_DEFS for f in files_of[b["id"]]]
    # 3) 撞车底册切片
    r2 = _parse_r2(root, all_files)
    issues = _parse_issues(root, all_files)
    base_by_file: dict[str, list[str]] = {}
    for e in r2:
        for p in e["files"]:
            base_by_file.setdefault(p, []).append(e["id"])
    issue_by_file: dict[str, list[dict]] = {}
    for e in issues:
        for p in e["files"]:
            issue_by_file.setdefault(p, []).append(e)
    batches = []
    for b in BATCH_DEFS:
        files = files_of[b["id"]]
        reg_r2 = sorted({fid for f in files for fid in base_by_file.get(f["path"], [])})
        reg_issues = sorted({e["issue"] for f in files for e in issue_by_file.get(f["path"], [])})
        batches.append({
            "id": b["id"], "route": b["route"], "title": b["title"], "depth": b["depth"],
            "total_lines": sum(f["lines"] for f in files if f["lines"] >= 0),
            "files": files,
            "registry": {"r2_ids": reg_r2, "r2_index": {e["id"]: e["gist"] for e in r2 if e["id"] in reg_r2},
                         "issues": [e for e in issues if e["issue"] in reg_issues]},
        })
    manifest = {
        "campaign": "legacy-code-review-4",
        "plan_file": PLAN_REL,
        "generated_at": _now(),
        "note": "机器事实源(计划 §04/D14); freeze 由 review.lane.claim 时机械解析, 不存于此",
        "routes": {r: [b["id"] for b in batches if b["route"] == r] for r in ROUTES},
        "batches": batches,
        "coverage": {
            "ok": True,
            "scoped_files": len(scoped),
            "assigned_files": len(all_files),
            "total_lines": sum(b["total_lines"] for b in batches),
            "registry": {"r2_findings": len(r2), "open_issues_matched": len(issues)},
        },
    }
    out = root / LANE_DIR / "manifest.json"
    if args.dry_run:
        print(f"[dry-run] manifest 将写入 {out}")
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"覆盖守卫: 通过 —— 范围内 {len(scoped)} 文件恰被 {len(BATCH_DEFS)} 批认领, 共 {manifest['coverage']['total_lines']} 行")
    print(f"底册切片: R2 终表 {len(r2)} 条 / Open·In-Progress issues 命中 {len(issues)} 条")
    for route in ROUTES:
        rows = [b for b in batches if b["route"] == route]
        print(f"  {route}: {len(rows)} 批 / {sum(b['total_lines'] for b in rows)} 行  " +
              "  ".join(f"{b['id']}={b['total_lines']}行" for b in rows))
    return 0


# --------------------------------------------------------------------------- lane


def cmd_claim(args: argparse.Namespace) -> int:
    root = _resolve_root(args.root)
    manifest = _load_manifest(root)
    route = args.route
    if route not in manifest["routes"]:
        _fail(f"未知路线 {route} (合法: {'/'.join(manifest['routes'])})")
    rpath = root / LANE_DIR / f"route-{route}.json"
    if rpath.is_file():
        old = json.loads(rpath.read_text(encoding="utf-8"))
        _fail(f"{route} 已被认领(owner={old.get('owner')}, {old.get('claimed_at')}) —— 认领记录是协调单点, 争议走用户")
    _require_branch(root)
    _require_tip(root, args.remote)
    _require_clean(root)
    freeze = _resolve_freeze(root)
    _require_ancestor(root, freeze)
    batches = [{"id": b["id"], "title": b["title"], "status": "pending", "done_at": None, "findings": 0}
               for b in _batches_of(manifest, route)]
    data = {
        "route": route, "owner": _flat(args.owner), "claimed_at": _now(),
        "freeze": freeze, "freeze_note": "计划文件首个 commit (diff-filter=A 机械解析)",
        "snapshot": None, "status": "claimed", "batches": batches,
    }
    if args.dry_run:
        print(f"[dry-run] 将写 {rpath.relative_to(root)}: owner={data['owner']} freeze={freeze[:12]} 批次 {len(batches)} 个")
        return 0
    _save_route(root, route, data)
    print(f"认领成功: {route} owner={data['owner']} freeze={freeze[:12]} (共 {len(batches)} 批)")
    print("下一步: commands run ship.commit  # 认领入库(其他 clone 可见, 防重复认领)")
    print(f"然后:   commands run review.lane.start --route {route}  # 导出快照并开始")
    return 0


def _extract_snapshot(root: Path, freeze: str, snap: Path) -> int:
    raw = _git_bytes(root, "archive", "--format=tar", freeze)
    if snap.exists():
        _die(f"快照目录已存在且标记不匹配: {snap} —— 确认后 --fresh 重建")
    snap.mkdir(parents=True)
    count = 0
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as tf:
        try:
            tf.extractall(snap, filter="data")  # 3.12+: 拒绝绝对路径/.. 穿越/特殊成员
        except TypeError:
            tf.extractall(snap)  # 旧版回退(git archive 成员本就仓库相对, 无穿越面)
        count = len(tf.getnames())
    (snap / ".snapshot-hash").write_text(freeze + "\n", encoding="utf-8")
    (snap / ".snapshot-info.json").write_text(
        json.dumps({"freeze": freeze, "generated_at": _now(), "source": str(root)}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    return count


def _check_snapshot(root: Path, data: dict) -> Path:
    snap = Path(data["snapshot"])
    marker = snap / ".snapshot-hash"
    if not snap.is_dir() or not marker.is_file():
        _fail(f"快照目录/标记缺失: {snap} —— 重跑 review.lane.start --route {data['route']} 重建")
    got = marker.read_text(encoding="utf-8").strip()
    if got != data["freeze"]:
        _fail(f"快照标记 {got[:12]} != 路线钉值 {data['freeze'][:12]} —— 重跑 review.lane.start --route {data['route']} --fresh")
    return snap


def _print_triplet(root: Path, data: dict, manifest: dict, batch: dict | None) -> None:
    snap = Path(data["snapshot"])
    print("== 三件套(存量适配, 照抄派遣) ==")
    print("1. 只读契约: 禁止一切写操作 —— git 状态变更(sync/rebase/merge/stash/checkout/commit/push)、"
          "写任何文件、跑 kb 等写类 task id 一律禁止, 只允许读命令; AGENTS.md 的开工同步对本任务豁免。")
    print(f"2. 评审目标钉死: 快照目录 {snap}")
    print(f"   (冻结 {data['freeze'][:12]} 的 git archive 导出, 非 git 仓库, 纯只读树; 发现的 file/line/quote 一律以快照内容为准)")
    print("3. 开工自检: 快照存在且 .snapshot-hash == 钉值; 收尾复核: review.lane.verify 通过才采信发现。")
    if batch:
        print(f"当前批: {batch['id']} {batch['title']} [{batch['depth']}] — {len(batch['files'])} 文件 / {batch['total_lines']} 行")
        for f in batch["files"]:
            print(f"  {f['path']} ({f['lines']})")
        reg = batch["registry"]
        if reg["r2_ids"]:
            print(f"R2 底册命中 {len(reg['r2_ids'])} 条(不重报, 复验是否仍在): " + ", ".join(reg["r2_ids"]))
            for fid in reg["r2_ids"]:
                print(f"  {fid}: {reg['r2_index'].get(fid, '')}")
        if reg["issues"]:
            print(f"Open issues 命中 {len(reg['issues'])} 条(不重报): " + ", ".join(e["id"] for e in reg["issues"]))
        print(f"findings: route-{data['route']}-findings.json (七字段 schema, review.check --root {snap} 校验)")


def cmd_start(args: argparse.Namespace) -> int:
    root = _resolve_root(args.root)
    manifest = _load_manifest(root)
    data = _load_route(root, args.route)
    if data["status"] != "claimed":
        _fail(f"{args.route} 状态为 {data['status']}, 仅 claimed 可 start")
    _require_branch(root)
    _require_ancestor(root, data["freeze"])
    _require_clean(root)
    snap = _snapshot_dir(root, args.snapshot)
    if args.dry_run:
        tmp = Path(tempfile.mkdtemp(prefix="lane-smoke-snap-"))
        try:
            raw = _git_bytes(root, "archive", "--format=tar", data["freeze"])
            with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as tf:
                tf.extractall(tmp, filter="data")
                n = len(tf.getnames())
            print(f"[dry-run] archive+解包链路 OK: {n} 个文件, 真实快照将落 {snap}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        return 0
    if args.fresh and snap.exists():
        shutil.rmtree(snap)
    if snap.exists() and (snap / ".snapshot-hash").is_file():
        got = (snap / ".snapshot-hash").read_text(encoding="utf-8").strip()
        if got == data["freeze"]:
            print(f"快照已存在且标记吻合, 复用: {snap}")
        else:
            _fail(f"快照目录标记 {got[:12]} != 钉值 {data['freeze'][:12]}: {snap} —— --fresh 重建")
    else:
        n = _extract_snapshot(root, data["freeze"], snap)
        print(f"快照导出完成: {snap} ({n} 个文件, freeze={data['freeze'][:12]})")
    data["snapshot"] = str(snap)
    data["status"] = "in-progress"
    data["started_at"] = _now()
    _save_route(root, args.route, data)
    first = next((b for b in data["batches"] if b["status"] == "pending"), None)
    mb = next((b for b in manifest["batches"] if b["id"] == first["id"]), None) if first else None
    _print_triplet(root, data, manifest, mb)
    print(f"路线进度: {sum(1 for b in data['batches'] if b['status'] == 'done')}/{len(data['batches'])} 批完成")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    root = _resolve_root(args.root)
    manifest = _load_manifest(root)
    data = _load_route(root, args.route)
    if data["status"] != "in-progress":
        _fail(f"{args.route} 状态为 {data['status']}, 仅 in-progress 可 verify")
    _require_branch(root)
    _require_ancestor(root, data["freeze"])
    snap = _check_snapshot(root, data)
    _require_clean(root, allow_lane=True)
    done = sum(1 for b in data["batches"] if b["status"] == "done")
    print(f"复核通过: 快照 {snap} 标记吻合, 树净(legacy-review4/ 内 {sum(1 for st, p in _porcelain(root) if p.startswith(LANE_DIR))} 处在盘), 进度 {done}/{len(data['batches'])}")
    if args.batch:
        mb = next((b for b in manifest["batches"] if b["id"] == args.batch), None)
        if not mb or mb["route"] != args.route:
            _fail(f"批次 {args.batch} 不属于路线 {args.route}")
    pending = [b for b in data["batches"] if b["status"] == "pending"]
    if not pending:
        print("全部批次已勾选 —— 跑 review.lane.done 收尾")
        return 0
    nxt = next((mb for mb in manifest["batches"] if mb["id"] == pending[0]["id"]), None)
    _print_triplet(root, data, manifest, nxt)
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    root = _resolve_root(args.root)
    data = _load_route(root, args.route)
    if data["status"] != "in-progress":
        _fail(f"{args.route} 状态为 {data['status']}, 仅 in-progress 可勾选批次")
    rows = [b for b in data["batches"] if b["id"] == args.id]
    if not rows:
        _fail(f"批次 {args.id} 不属于路线 {args.route} (合法: {', '.join(b['id'] for b in data['batches'])})")
    row = rows[0]
    if row["status"] == "done":
        _fail(f"批次 {args.id} 已勾选({row['done_at']}); 重开请手工改 route JSON 并说明")
    row["status"] = "done"
    row["done_at"] = _now()
    row["findings"] = max(0, args.findings)
    _save_route(root, args.route, data)
    done = sum(1 for b in data["batches"] if b["status"] == "done")
    print(f"批次勾选: {args.id} (findings={row['findings']}) —— 进度 {done}/{len(data['batches'])}")
    if done < len(data["batches"]):
        print(f"下一批: {next(b['id'] for b in data['batches'] if b['status'] == 'pending')}")
    else:
        print("全部批次完成 —— 跑 review.lane.done 收尾")
    return 0


def cmd_done(args: argparse.Namespace) -> int:
    root = _resolve_root(args.root)
    data = _load_route(root, args.route)
    if data["status"] != "in-progress":
        _fail(f"{args.route} 状态为 {data['status']}, 仅 in-progress 可收尾")
    pending = [b["id"] for b in data["batches"] if b["status"] != "done"]
    if pending:
        _fail(f"还有未勾选批次: {', '.join(pending)} —— 完成判据=批次全覆盖无断号")
    lane = root / LANE_DIR
    findings = lane / f"route-{args.route}-findings.json"
    notes = lane / f"route-{args.route}-notes.md"
    missing = [str(p.relative_to(root)) for p in (findings, notes) if not p.is_file()]
    if missing:
        _fail(f"产出物缺失: {', '.join(missing)} —— findings 过 review.check 后与小结一起落盘再 done")
    try:
        json.loads(findings.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        _fail(f"findings JSON 非法: {exc}")
    data["status"] = "done"
    data["done_at"] = _now()
    _save_route(root, args.route, data)
    total = sum(b["findings"] for b in data["batches"])
    print(f"路线终态: {args.route} done —— findings {total} 条 / 批次 {len(data['batches'])}/{len(data['batches'])}")
    print("下一步: commands run ship.commit  # findings + 小结 + 状态单点入库; 之后由聚合会话 S6 合并")
    return 0


# --------------------------------------------------------------------------- smoke


def cmd_smoke(args: argparse.Namespace) -> int:
    """全环真冒烟: 真实 claim/start/verify/batch/done(含两个负例断言), 结束清理全部痕迹。"""
    root = _resolve_root(args.root)
    ns = argparse.Namespace
    route = args.route
    snap = _snapshot_dir(root, None)

    def cleanup(tag: str) -> None:
        lane = root / LANE_DIR
        for p in (lane / f"route-{route}.json", lane / f"route-{route}-findings.json",
                  lane / f"route-{route}-notes.md"):
            if p.is_file():
                p.unlink()
        if snap.is_dir():
            shutil.rmtree(snap, ignore_errors=True)
        print(f"[smoke] 清理完成({tag}): route JSON / findings / 小结 / 快照目录已删")

    print(f"[smoke 1/7] claim {route} (真实写入)")
    cmd_claim(ns(route=route, owner="smoke", remote=args.remote, root=str(root), dry_run=False))
    print("[smoke 2/7] claim 重复认领负例(必须失败)")
    try:
        cmd_claim(ns(route=route, owner="smoke", remote=args.remote, root=str(root), dry_run=False))
        cleanup("负例失败, 未通过")
        _fail("重复认领未被拒绝 —— claim 守卫失效")
    except SystemExit as exc:
        if exc.code != 1:
            cleanup(f"负例异常 rc={exc.code}")
            raise
        print("[smoke] 重复认领按预期拒绝 (rc=1)")
    print("[smoke 3/7] start (真实导出快照)")
    cmd_start(ns(route=route, snapshot=None, fresh=False, root=str(root), dry_run=False))
    print("[smoke 4/7] verify (必须通过)")
    cmd_verify(ns(route=route, batch=None, root=str(root)))
    print("[smoke 5/7] done 负例(批次未齐, 必须失败)")
    try:
        cmd_done(ns(route=route, root=str(root)))
        cleanup("负例失败, 未通过")
        _fail("批次未齐时 done 未被拒绝 —— 完成判据守卫失效")
    except SystemExit as exc:
        if exc.code != 1:
            cleanup(f"负例异常 rc={exc.code}")
            raise
        print("[smoke] 批次未齐按预期拒绝 (rc=1)")
    print("[smoke 6/7] 逐批勾选后 done (真实终态)")
    manifest = _load_manifest(root)
    data = _load_route(root, route)
    findings = root / LANE_DIR / f"route-{route}-findings.json"
    notes = root / LANE_DIR / f"route-{route}-notes.md"
    findings.write_text("[]\n", encoding="utf-8")
    notes.write_text(f"# smoke\n\n{route} 冒烟小结(测试痕迹, 可删)。\n", encoding="utf-8")
    for b in data["batches"]:
        cmd_batch(ns(route=route, id=b["id"], findings=0, root=str(root)))
    cmd_done(ns(route=route, root=str(root)))
    print("[smoke 7/7] 清理全部痕迹")
    cleanup("全环通过")
    print("[smoke] 全环通过: claim/重复认领负例/start/verify/done 负例/逐批勾选/done/清理 全部符合预期")
    return 0


# --------------------------------------------------------------------------- main


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    parser = argparse.ArgumentParser(description="存量评审 R4 路线机械面: manifest/claim/start/verify/batch/done/smoke")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("manifest", help="生成 manifest.json(批次矩阵+底册切片+覆盖守卫)")
    p.add_argument("--root")
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("claim", help="认领路线: freeze 机械解析 + 远端 tip 校验 + 写 route JSON")
    p.add_argument("--route", required=True)
    p.add_argument("--owner", required=True, help="认领者标识(clone 名/会话名)")
    p.add_argument("--remote", default="origin")
    p.add_argument("--root")
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("start", help="导出冻结快照(repo 外)并打印三件套")
    p.add_argument("--route", required=True)
    p.add_argument("--snapshot", help="快照目录(默认 <repo>/../auto-qb-review4-snap/<repo名>)")
    p.add_argument("--fresh", action="store_true", help="删除既有快照重建")
    p.add_argument("--root")
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("verify", help="每批派遣前/交回后复核 + 打印下一批材料")
    p.add_argument("--route", required=True)
    p.add_argument("--batch", help="只看指定批次")
    p.add_argument("--root")

    p = sub.add_parser("batch", help="勾选批次完成")
    p.add_argument("--route", required=True)
    p.add_argument("--id", required=True, help="批次 id (如 R1-1)")
    p.add_argument("--findings", type=int, default=0, help="该批通过 review.check 的发现数")
    p.add_argument("--root")

    p = sub.add_parser("done", help="全批完成后翻终态")
    p.add_argument("--route", required=True)
    p.add_argument("--root")

    p = sub.add_parser("smoke", help="全环真冒烟(含负例断言, 结束清理)")
    p.add_argument("--route", required=True, help="冒烟用的路线 id(结束后清理其全部痕迹)")
    p.add_argument("--remote", default="origin")
    p.add_argument("--root")

    args = parser.parse_args()
    return {
        "manifest": cmd_manifest, "claim": cmd_claim, "start": cmd_start, "verify": cmd_verify,
        "batch": cmd_batch, "done": cmd_done, "smoke": cmd_smoke,
    }[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
