"""存量评审 R4 的路线机械面: review.lane —— 认领/快照/复核/勾选/终态 + manifest 生成。

计划 26-11-05-2335 (legacy-code-review-4) 的配套脚本 (拍板 D13/D15); 数据外置见移植计划
26-11-17-0010 S7/D18: 全部项目数据(批次矩阵/分层范围含 vendor 排除/快照与 lane 目录/计划
与 R2 报告指针/分支策略)单点在包根 `lane.toml`, 机械流程零改只换数据源; 矩阵缺失=引导性
报错(D13 运行必需数据不适用宽容回落); 未配置远端时 freeze 取本地 HEAD(无远端稳态, 免
ls-remote)。各子命令:
- manifest: 生成 manifest.json —— 冻结基线钉定(生成时点基线分支 tip: 有远端时 ls-remote 核验,
            无远端稳态取本地 HEAD, D18; 有路线认领后拒绝重生成) + 批次到文件精确矩阵 +
            每批撞车底册切片(R2 终表 + Open issues 按文件词边界映射) + 覆盖守卫(全部分层
            范围内文件恰被一批认领, 重叠/漏配即失败)。
- claim:    认领路线。freeze 取 manifest 钉值(D17), 校验为其祖先且
            本地 HEAD == 远端 tip(ls-remote 现查, 防在落后/分叉基线上认领; 无远端稳态免核验); 写 route JSON。
- start:    git archive <freeze> 导出评审快照到 repo 外目录(不切分支不动 HEAD, 不扰动
            基线分支), 写 .snapshot-hash 标记, 打印存量适配三件套与首批文件。
- verify:   每批派遣前/交回后复核 —— 快照存在且标记吻合 / 工作树净(仅 lane 目录内
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
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from datetime import datetime
from pathlib import Path

# 数据外置单点(S7, 计划 26-11-17-0010): 项目数据在包根 lane.toml(与本包 scripts 同目录的
# 上一级), 本脚本只读不写; 加载与校验见 _load_lane_config。
LANE_CONFIG = Path(__file__).resolve().parent.parent / "lane.toml"
DEPTH_ENUM = ("full", "contract", "mechanism", "scan")


def _is_repo_relative(p: str) -> bool:
    """仓库相对路径形态, 对**原串**逐段判: 非绝对路径, 不含反斜杠, 且不含 ''/'.'/ '..' 段。

    不能用 Path 归一化后判: '.'/空段会被 Path 吸掉, 而 cfg 保留原串 —— _require_clean 的
    porcelain 前缀比对用原串, 'mb/./lane' 一类形态会永不匹配, 纯 lane 内改动被误报
    「lane 目录之外有未提交改动」(fail-closed 但报错误导), 必须在加载面拒。
    反斜杠同理: git porcelain 路径恒正斜杠, Windows 宿主填 'a\\b' 一类原串比对必然对不齐,
    路径字段一律填 posix 形态。
    """
    if Path(p).is_absolute() or "\\" in p:  # 含 Windows 盘符绝对形态; porcelain 恒正斜杠, 禁 '\' 字段
        return False
    return all(seg not in ("", ".", "..") for seg in p.split("/"))


# --------------------------------------------------------------------------- lane 配置加载
# D13 口径: lane.toml 是运行必需数据 —— 文件/矩阵/必填字段缺失或模板 TODO 占位未填 = 引导性
# 报错(文案指路 lane.toml 与具体字段), 不静默降级; 校验类辅助数据(r2_report/issues_dir 指向
# 的文件不在盘)缺失才允许跳过 + 必打提示(见 _parse_r2/_parse_issues)。


def _load_lane_config(path: Path | None = None, need_matrix: bool = False) -> dict:
    path = path or LANE_CONFIG
    if not path.is_file():
        _die(
            f"lane 配置缺失: {path} —— 存量评审的项目数据单点(批次矩阵/分层范围/快照与 lane 目录/"
            f"指针/分支策略), 照 `.commands/review/lane.toml` 模板复制或按其头注逐字段填写后重试"
        )
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError, OSError) as exc:
        _die(f"lane 配置解析失败: {path} ({exc}) —— TOML 语法自检命令见文件头注")
    lane = raw.get("lane")
    if not isinstance(lane, dict):
        _die(f"lane 配置缺 [lane] 节: {path} —— 各字段说明在文件头注")
    cfg: dict = {}
    for key in ("campaign", "freeze_branch", "snapshot_root", "lane_dir", "plan_file", "r2_report", "issues_dir"):
        val = lane.get(key)
        if not isinstance(val, str) or not val.strip():
            _die(f"lane 配置缺必填字段 [lane].{key}: {path} —— 各字段说明在文件头注")
        cfg[key] = val
    # 路径形态校验: lane_dir/snapshot_root 写出仓库外 = 配置错误, 按 D13 引导报错
    # (snapshot_root 还参与 _guard_snap_path 的删除授权, 误填通用名/多层路径会放大误删面)
    if not _is_repo_relative(cfg["lane_dir"]):
        _die(
            f"lane 配置 [lane].lane_dir 必须是仓库相对路径(不得为绝对路径, 不得含 '\\\\' 或 ''/'.'/ '..' 段"
            f" —— 路径字段一律填 posix 形态, git porcelain 恒正斜杠): "
            f"{cfg['lane_dir']!r} ({path}) —— 状态单点不允许写出仓库外, 也不允许 lane 前缀比对对不齐的非常规段"
        )
    if not _is_repo_relative(cfg["snapshot_root"]) or "/" in cfg["snapshot_root"]:
        _die(
            f"lane 配置 [lane].snapshot_root 必须是仓库相对的单段目录名(不得含 '/'、'\\\\' 或 '..'): "
            f"{cfg['snapshot_root']!r} ({path}) —— 仓库外快照容器目录的授权/清理按它点名, 勿填通用名"
        )
    scope = lane.get("scope")
    if not isinstance(scope, dict):
        _die(f"lane 配置缺 [lane.scope] 节(分层范围 include/exclude): {path} —— 口径在文件头注")
    for name in ("include", "exclude"):
        vals = scope.get(name, [])
        if not isinstance(vals, list) or any(not isinstance(v, str) or not v.strip() for v in vals):
            _die(f"lane 配置 [lane.scope].{name} 必须是非空字符串列表(fnmatch glob, 口径在文件头注): {path}")
    if need_matrix and not scope.get("include"):
        _die(f"lane 配置 [lane.scope].include 为空(分层范围不可为空, 否则无文件可评): {path} —— 口径在文件头注")
    cfg["scope_include"] = list(scope.get("include", []))
    cfg["scope_exclude"] = list(scope.get("exclude", []))
    cfg["routes"] = []
    cfg["batch_defs"] = []
    if not need_matrix:
        return cfg  # 矩阵只有 manifest 生成与 claim 指纹校验消费, 其余子命令不拦
    defs = raw.get("route")
    if not isinstance(defs, list) or not defs:
        _die(
            f"lane 配置批次矩阵缺失: {path} 里没有任何 [[route]] 路线 —— 开存量评审先按头注说明"
            f"按现状目录划分路线与批次([[route]] id + 逐批 [[route.batch]] id/desc/depth/exact/globs)"
        )
    seen_route: set[str] = set()
    seen_batch: set[str] = set()
    for r in defs:
        rid = r.get("id") if isinstance(r, dict) else None
        if not isinstance(rid, str) or not rid.strip():
            _die(f"lane 配置 [[route]] 缺非空 id: {path}")
        if rid in seen_route:
            _die(f"lane 配置路线 id 重复: {rid} ({path})")
        seen_route.add(rid)
        batches = r.get("batch")
        if not isinstance(batches, list) or not batches:
            _die(f"lane 配置路线 {rid} 没有任何 [[route.batch]] 批次: {path} —— 每条路线至少一批")
        rows = []
        for b in batches:
            bid = b.get("id") if isinstance(b, dict) else None
            if not isinstance(bid, str) or not bid.strip():
                _die(f"lane 配置路线 {rid} 下有批次缺非空 id: {path}")
            if not bid.startswith(rid + "-"):
                _die(f"lane 配置批次 id {bid} 不以路线前缀 {rid}- 开头: {path} (口径: 批次 id = <路线>-<序号>)")
            if bid in seen_batch:
                _die(f"lane 配置批次 id 重复: {bid} ({path})")
            seen_batch.add(bid)
            desc = b.get("desc")
            if not isinstance(desc, str) or not desc.strip() or "TODO" in desc:
                _die(f"lane 配置批次 {bid} 缺 desc 或仍是模板 TODO 占位: {path} —— 填本批评审范围一句话")
            depth = b.get("depth")
            if depth not in DEPTH_ENUM:
                _die(f"lane 配置批次 {bid} depth 非法: {depth!r} (词表: {'/'.join(DEPTH_ENUM)}, 说明在文件头注)")
            exact = b.get("exact", [])
            globs = b.get("globs", [])
            for name, vals in (("exact", exact), ("globs", globs)):
                if not isinstance(vals, list) or any(not isinstance(v, str) or not v.strip() for v in vals):
                    _die(f"lane 配置批次 {bid} 的 {name} 必须是非空字符串列表: {path} (口径在文件头注)")
            if not exact and not globs:
                _die(
                    f"lane 配置批次 {bid} 的 exact/globs 全空(本批该看什么不可判定): {path} —— "
                    f"exact 填精确路径清单, globs 填 fnmatch glob"
                )
            if any("TODO" in v for v in (*exact, *globs)):
                _die(f"lane 配置批次 {bid} 的 exact/globs 仍是模板 TODO 占位: {path} —— 逐批填实际覆盖范围")
            rows.append(
                {
                    "id": bid,
                    "route": rid,
                    "title": desc,
                    "depth": depth,
                    "exact": list(exact),
                    "globs": list(globs)
                }
            )
        cfg["routes"].append({"id": rid, "batches": rows})
        cfg["batch_defs"].extend(rows)
    return cfg


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


ROUTE_ID_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9_-]*[A-Za-z0-9])?")


def _require_route_id(route: str) -> None:
    """route 白名单格式校验(issue 26-11-17-2339 拍板: 格式校验, 不走 _guard_snap_path)。

    route 原样拼进 route-{route}.json / -findings / -notes(cleanup unlink)与快照子目录
    _smoke-{route}(cleanup rmtree)等删除路径, 含 `..`/路径分隔符/其它非常规字符的值会把
    删除面带出 lane 目录 —— 从严白名单拒收: 字母或数字开头结尾, 中间仅字母/数字/-/_
    (与 lane.toml [[route]] id 实际取值形态同域)。挂全部消费 --route 的子命令入口
    (claim/start/verify/batch/done/smoke), 各自做任何 IO 之前先校验。
    """
    if not ROUTE_ID_RE.fullmatch(route):
        _die(
            f"--route 非法: {route!r} —— 只允许字母/数字开头结尾、中间仅字母/数字/-/_ 的路线 id"
            "(与 lane.toml [[route]] id 同域); 该值要拼 route JSON/findings/notes 与快照子目录等清理路径"
        )


def _porcelain(root: Path) -> list[str]:
    out = _git(root, "status", "--porcelain").stdout
    rows = []
    for line in out.splitlines():
        if len(line) > 3:
            rows.append((line[:2], line[3:]))
    return rows


def _require_clean(root: Path, cfg: dict, allow_lane: bool = False) -> None:
    """树净守卫。allow_lane=True 时仅放行 lane 目录(cfg.lane_dir)下的路径(路线期间 findings/状态单点的正常落盘)。

    rename/copy 条目的 porcelain 路径形态是「old -> new」: 必须拆开两侧分别校验,
    否则旧路径在 lane 内的「lane 内 -> lane 外」重命名会整段命中前缀被放行。
    """
    lane_dir = cfg["lane_dir"]
    rows = _porcelain(root)
    if not rows:
        return
    if allow_lane:

        def in_lane(p: str) -> bool:
            return p.strip('"').startswith(lane_dir + "/")

        bad = [p for st, p in rows if not all(in_lane(q) for q in ((p, ) if " -> " not in p else p.split(" -> ")))]
        if not bad:
            return
        _fail("工作树在 lane 目录(" + lane_dir + "/)之外有未提交改动, 先处理再继续:\n  " + "\n  ".join(f"{st} {p}" for st, p in rows))
    _fail("工作树不净(先 commit/stash 处理):\n  " + "\n  ".join(f"{st} {p}" for st, p in rows))


def _require_branch(root: Path, cfg: dict) -> str:
    branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    required = cfg["freeze_branch"]
    if branch != required:
        _fail(f"当前分支 {branch} != {required}, 路线认领与执行一律在 {required} 上")
    return branch


def _require_ancestor(root: Path, freeze: str) -> None:
    proc = _git(root, "merge-base", "--is-ancestor", freeze, "HEAD", check=False)
    if proc.returncode != 0:
        _fail(f"freeze {freeze} 不是 HEAD 的祖先(历史被改写?), 停手人工介入")


def _require_tip(root: Path, cfg: dict, remote: str) -> str:
    """基线分支 tip 核验。有远端: 本地 HEAD == 远端 tip 才放行(防在落后/分叉基线上钉 freeze);
    未配置远端: 无远端稳态(D18), freeze 取本地 HEAD 免 ls-remote(本地分支/离线项目也能用)。
    """
    branch = _require_branch(root, cfg)
    head = _git(root, "rev-parse", "HEAD").stdout.strip()
    probe = _git(root, "remote", "get-url", remote, check=False)
    if probe.returncode != 0:
        print(f"[note] 未配置远端 {remote}: freeze 取本地 HEAD {head[:12]}(无远端稳态, 免 ls-remote 核验)")
        return branch
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
    return branch


def _load_manifest(root: Path, cfg: dict) -> dict:
    path = root / cfg["lane_dir"] / "manifest.json"
    if not path.is_file():
        _die(f"manifest 不存在: {cfg['lane_dir']}/manifest.json —— 先跑 review.lane.manifest 生成")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        _die(f"manifest 解析失败: {exc}")
    if not data.get("coverage", {}).get("ok"):
        _fail("manifest 覆盖守卫未通过(coverage.ok != true), 禁止认领 —— 重跑 review.lane.manifest")
    freeze = data.get("freeze")
    if not isinstance(freeze, str) or len(freeze) != 40:
        _fail("manifest 缺合法 freeze 钉值(40 位 hash) —— 重跑 review.lane.manifest")
    return data


def _load_route(root: Path, cfg: dict, route: str) -> dict:
    path = root / cfg["lane_dir"] / f"route-{route}.json"
    if not path.is_file():
        _fail(f"路线未认领: {cfg['lane_dir']}/route-{route}.json 不存在 —— 先 review.lane.claim")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        _die(f"route JSON 解析失败: {exc}")
    # 最小 schema 校验: 状态单点被手工改坏时给清晰失败(而非 TypeError/StopIteration 裸 traceback)
    rel = path.relative_to(root).as_posix()
    if not isinstance(data, dict):
        _fail(f"route JSON 顶层必须是对象, 实为 {_flat(type(data).__name__)} ({rel}) —— 手工修复或删除后重新认领")
    for key in ("route", "owner", "claimed_at", "freeze", "status", "batches"):
        if key not in data:
            _fail(f"route JSON 缺字段 {key}: {rel} —— 手工修复或删除后重新认领")
    if data["status"] not in ("claimed", "in-progress", "done"):
        _fail(f"route JSON status 非法: {data['status']!r} ({rel}) —— 手工修复或删除后重新认领")
    if data["status"] == "in-progress" and (not isinstance(data.get("snapshot"), str) or not data["snapshot"]):
        _fail(f"route JSON in-progress 但 snapshot 非非空 str ({rel}) —— 手工把 status 回退 claimed 后重跑 start")
    if not isinstance(data["batches"], list) or not data["batches"]:
        _fail(f"route JSON batches 非非空列表 ({rel}) —— 手工修复或删除后重新认领")
    for b in data["batches"]:
        if (
            not isinstance(b, dict) or "id" not in b or b.get("status") not in ("pending", "done") or
            "findings" not in b or "done_at" not in b
        ):
            _fail(f"route JSON 批次条目非法({rel}): {_flat(b)} —— 手工修复或删除后重新认领")
    return data


def _save_route(root: Path, cfg: dict, route: str, data: dict) -> None:
    path = root / cfg["lane_dir"] / f"route-{route}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    # 原子写: 状态单点不允许留半截 JSON(崩溃窗口内旧版或完整新版二选一)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _snapshot_dir(root: Path, explicit: str | None, cfg: dict) -> Path:
    if explicit:
        return Path(explicit).resolve()
    return (root.parent / cfg["snapshot_root"] / root.name).resolve()


def _guard_snap_path(root: Path, snap: Path, cfg: dict) -> None:
    """快照目录容器守卫: 与仓库根重合/互含一律拒绝; 删除类操作另要求标记或专用目录名。"""
    snap_root = cfg["snapshot_root"]
    root_r = root.resolve()
    snap_r = Path(snap).resolve()
    if snap_r == root_r or snap_r.is_relative_to(root_r) or root_r.is_relative_to(snap_r):
        _die(f"快照目录与仓库根重合或互含, 拒绝: {snap_r}")
    has_marker = (snap_r / ".snapshot-hash").is_file()
    in_snap_root = snap_root in snap_r.parts
    if not has_marker and not in_snap_root:
        _die(f"快照目录既无 .snapshot-hash 标记也不在 {snap_root}/ 专用目录下, 拒绝操作: {snap_r}")


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


def _mentions(text: str, base: str) -> bool:
    """basename 词边界命中: 裸子串会把 store.py 误配进 traffic_store.py 一类(评审实证)。

    前顾只拦 \\w 与 -: 路径形态提及(core/modules/x.py)的 basename 前导是 "/", 必须放行,
    否则底册条目大面积漏配(增量评审实证 19->11); "_" 属 \\w, 原误配仍被挡。
    """
    return re.search(r"(?<![\w-])" + re.escape(base) + r"(?![\w.-])", text) is not None


def _parse_r2(root: Path, all_files: list[dict], cfg: dict) -> list[dict]:
    """R2 终表切片: ID -> 命中的 basename 集合 + 一句话。找不到终表节则返回空(不静默, 打警告)。"""
    path = root / cfg["r2_report"]
    if not path.is_file():
        print(f"[warn] R2 报告不在盘: {cfg['r2_report']}, 底册切片将没有 R2 条目")
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
        hits = sorted({p for p, b in base_of.items() if _mentions(rowtext, b)})
        entries.append({"id": fid, "files": hits, "gist": rowtext[:160]})
    return entries


def _parse_issues(root: Path, all_files: list[dict], cfg: dict) -> list[dict]:
    """Open/In Progress issue 底册: 按正文/标题 basename 命中映射(辅助指针, S6 终验兜底)。"""
    issues_dir = root / cfg["issues_dir"]
    if not issues_dir.is_dir():
        print(f"[warn] issues 目录不在盘: {cfg['issues_dir']}, 底册切片将没有 issue 条目")
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
        # files 存全路径(与 _parse_r2 同构): issue_by_file 按全路径键查, basename 键永远 miss
        hits = sorted({p for p, b in base_of.items() if _mentions(text, b)})
        if not hits:
            continue
        entries.append(
            {
                "issue": f"{cfg['issues_dir']}/{path.name}",
                "id": path.name.split("-", 3)[-1].rsplit(".", 1)[0] if "-" in path.name else path.name,
                "type": m_type.group(1) if m_type else "?",
                "title": _flat(m_title.group(1))[:80] if m_title else "?",
                "status": status,
                "files": hits,
            }
        )
    return entries


def _scoped_files(root: Path, cfg: dict) -> list[str]:
    """分层范围盘点(lane.toml [lane.scope]): include/exclude 均为 fnmatch 整路径 glob,
    exclude 先判(命中即排除, vendor 第三方发行物/ __pycache__ 不属评审对象)。
    """
    out: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for name in filenames:
            rel = Path(dirpath, name).resolve().relative_to(root).as_posix()
            if any(fnmatch.fnmatchcase(rel, g) for g in cfg["scope_exclude"]):
                continue
            if any(fnmatch.fnmatchcase(rel, g) for g in cfg["scope_include"]):
                out.append(rel)
    out.sort()
    return out


def _defs_fingerprint(defs: list[dict]) -> str:
    """批次定义(lane.toml 矩阵)的指纹: manifest 是否由当前矩阵版本生成, 与树无关 ——
    manifest 描述的是冻结树, 树在 campaign 期间照常演进, 拿树当指纹会让后认领的路线永远对不上。"""
    defs_json = json.dumps(
        [[b["id"], b["route"], b["depth"], b["exact"], b["globs"]] for b in defs],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(defs_json.encode("utf-8")).hexdigest()[:16]


def cmd_manifest(args: argparse.Namespace) -> int:
    root = _resolve_root(args.root)
    cfg = _load_lane_config(need_matrix=True)
    defs = cfg["batch_defs"]
    route_ids = [r["id"] for r in cfg["routes"]]
    if not (root / cfg["plan_file"]).is_file():
        _die(f"计划文件不在盘: {cfg['plan_file']}")
    # 0) 冻结基线钉定(D17): manifest 生成时点的基线分支 tip —— 有远端时 ls-remote 现查核验
    #    (未 sync 即拒), 未配置远端时取本地 HEAD(无远端稳态, D18)。
    #    任何路线认领后禁止重生成 —— 冻结基线一经 route JSON 引用即不可移动。
    branch = _require_tip(root, cfg, args.remote)
    freeze = _git(root, "rev-parse", "HEAD").stdout.strip()
    claimed = [r for r in route_ids if (root / cfg["lane_dir"] / f"route-{r}.json").is_file()]
    if claimed:
        _fail(f"已有路线认领状态({','.join(claimed)}) —— 冻结基线一经引用不可移动, 重钉须先清理全部路线状态")
    # 1) 分层范围盘点 —— 在冻结树的临时解包上做: manifest 描述评审目标(冻结树),
    #    与基线分支后续演进(其它 clone 合流的新文件)无关, 覆盖守卫不随树漂移误报
    raw = _git_bytes(root, "archive", "--format=tar", freeze)
    with tempfile.TemporaryDirectory(prefix="lane-manifest-tree-") as td:
        tree = Path(td).resolve()  # 与子路径 resolve 同基准: TEMP 含符号链接/8.3 短名时纯词法 relative_to 不炸
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as tf:
            tf.extractall(tree, filter="data")
        scoped = _scoped_files(tree, cfg)
        # 2) 按批次定义分配(互斥 + 全覆盖)
        files_of: dict[str, list[dict]] = {b["id"]: [] for b in defs}
        overlap: list[str] = []
        unassigned: list[str] = []
        for rel in scoped:
            hits = [b["id"] for b in defs if rel in b["exact"] or any(fnmatch.fnmatchcase(rel, g) for g in b["globs"])]
            if len(hits) > 1:
                overlap.append(f"{rel} -> {','.join(hits)}")
            elif not hits:
                unassigned.append(rel)
            else:
                files_of[hits[0]].append({"path": rel, "lines": _count_lines(tree / rel)})
    if overlap or unassigned:
        if overlap:
            print(f"[FAIL] 批次定义重叠 {len(overlap)} 处:")
            for row in overlap:
                print(f"  {row}")
        if unassigned:
            print(f"[FAIL] 范围内未分配文件 {len(unassigned)} 个(补进对应批次定义):")
            for rel in unassigned:
                print(f"  {rel}")
        print("[note] 批次矩阵在 .commands/review/lane.toml 的 [[route.batch]] —— 按上面清单补 exact/globs")
        raise SystemExit(1)
    all_files = [f for b in defs for f in files_of[b["id"]]]
    # 3) 撞车底册切片
    r2 = _parse_r2(root, all_files, cfg)
    issues = _parse_issues(root, all_files, cfg)
    base_by_file: dict[str, list[str]] = {}
    for e in r2:
        for p in e["files"]:
            base_by_file.setdefault(p, []).append(e["id"])
    issue_by_file: dict[str, list[dict]] = {}
    for e in issues:
        for p in e["files"]:
            issue_by_file.setdefault(p, []).append(e)
    batches = []
    for b in defs:
        files = files_of[b["id"]]
        reg_r2 = sorted({fid for f in files for fid in base_by_file.get(f["path"], [])})
        reg_issues = sorted({e["issue"] for f in files for e in issue_by_file.get(f["path"], [])})
        batches.append(
            {
                "id": b["id"],
                "route": b["route"],
                "title": b["title"],
                "depth": b["depth"],
                "total_lines": sum(f["lines"] for f in files if f["lines"] >= 0),
                "files": files,
                "registry":
                    {
                        "r2_ids": reg_r2,
                        "r2_index": {
                            e["id"]: e["gist"]
                            for e in r2 if e["id"] in reg_r2
                        },
                        "issues": [e for e in issues if e["issue"] in reg_issues]
                    },
            }
        )
    manifest = {
        "campaign":
            cfg["campaign"],
        "plan_file":
            cfg["plan_file"],
        "generated_at":
            _now(),
        "freeze":
            freeze,
        "note":
            "机器事实源(计划 §04/D17): freeze = 生成时点核验的 " + branch + " tip"
            "(有远端 ls-remote 核验, 无远端稳态取本地 HEAD, D18); "
            "有路线认领后本命令拒绝重生成(冻结基线一经引用不可移动)",
        "routes": {
            r: [b["id"] for b in batches if b["route"] == r]
            for r in route_ids
        },
        "batches":
            batches,
        "fingerprint":
            {
                "defs": _defs_fingerprint(defs),
                "batches": len(defs),
                "files": len(all_files),
                "total_lines": sum(b["total_lines"] for b in batches)
            },
        "coverage":
            {
                "ok": True,
                "scoped_files": len(scoped),
                "assigned_files": len(all_files),
                "total_lines": sum(b["total_lines"] for b in batches),
                "registry": {
                    "r2_findings": len(r2),
                    "open_issues_matched": len(issues)
                },
            },
    }
    out = root / cfg["lane_dir"] / "manifest.json"
    if args.dry_run:
        print(f"[dry-run] manifest 将写入 {out}")
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"冻结基线: {freeze[:12]} (生成时点 {branch} tip 已核验; 有认领后重生成即拒)")
    print(f"覆盖守卫: 通过 —— 范围内 {len(scoped)} 文件恰被 {len(defs)} 批认领, 共 {manifest['coverage']['total_lines']} 行")
    print(f"底册切片: R2 终表 {len(r2)} 条 / Open·In-Progress issues 命中 {len(issues)} 条")
    for route in route_ids:
        rows = [b for b in batches if b["route"] == route]
        print(
            f"  {route}: {len(rows)} 批 / {sum(b['total_lines'] for b in rows)} 行  " +
            "  ".join(f"{b['id']}={b['total_lines']}行" for b in rows)
        )
    return 0


# --------------------------------------------------------------------------- lane


def cmd_claim(args: argparse.Namespace) -> int:
    _require_route_id(args.route)
    root = _resolve_root(args.root)
    cfg = _load_lane_config(need_matrix=True)
    manifest = _load_manifest(root, cfg)
    owner = _flat(args.owner).strip()
    if not owner:
        _die("--owner 不能为空(认领记录是跨 clone 判责的协调身份)")
    fp = manifest.get("fingerprint")
    if not fp or fp.get("defs") != _defs_fingerprint(cfg["batch_defs"]) or fp.get("batches") != len(cfg["batch_defs"]):
        _fail(
            f"manifest 与当前 lane.toml 批次矩阵不符(defs={fp.get('defs') if fp else '缺失'} vs "
            f"{_defs_fingerprint(cfg['batch_defs'])}) —— 重跑 review.lane.manifest 并入库后再认领"
        )
    route = args.route
    if route not in manifest["routes"]:
        _fail(f"未知路线 {route} (合法: {'/'.join(manifest['routes'])})")
    rpath = root / cfg["lane_dir"] / f"route-{route}.json"
    if rpath.is_file():
        old = json.loads(rpath.read_text(encoding="utf-8"))
        _fail(f"{route} 已被认领(owner={old.get('owner')}, {old.get('claimed_at')}) —— 认领记录是协调单点, 争议走用户")
    _require_branch(root, cfg)
    _require_tip(root, cfg, args.remote)
    _require_clean(root, cfg)
    freeze = manifest["freeze"]  # 钉值来自 manifest(生成时点核验的 tip, D17), 非 claim 时点解析
    _require_ancestor(root, freeze)
    batches = [
        {
            "id": b["id"],
            "title": b["title"],
            "status": "pending",
            "done_at": None,
            "findings": 0
        } for b in _batches_of(manifest, route)
    ]
    data = {
        "route": route,
        "owner": owner,
        "claimed_at": _now(),
        "freeze": freeze,
        "freeze_note": f"manifest 钉值 (生成时点 {cfg['freeze_branch']} tip, D17)",
        "snapshot": None,
        "status": "claimed",
        "batches": batches,
    }
    if args.dry_run:
        print(f"[dry-run] 将写 {rpath.relative_to(root)}: owner={owner} freeze={freeze[:12]} 批次 {len(batches)} 个")
        return 0
    _save_route(root, cfg, route, data)
    print(f"认领成功: {route} owner={data['owner']} freeze={freeze[:12]} (共 {len(batches)} 批)")
    print("下一步: commands run ship.commit  # 认领入库(其他 clone 可见, 防重复认领)")
    print(f"然后:   commands run review.lane.start --route {route}  # 导出快照并开始")
    return 0


def _extract_snapshot(root: Path, freeze: str, snap: Path, cfg: dict) -> int:
    _guard_snap_path(root, snap, cfg)
    raw = _git_bytes(root, "archive", "--format=tar", freeze)
    if snap.exists():
        if snap.is_dir() and not any(snap.iterdir()) and not (snap / ".snapshot-hash").is_file():
            try:
                snap.rmdir()  # 上次中断留下的空壳目录(无标记无内容): 直接重建
            except OSError as exc:
                _die(f"空壳快照目录重建失败: {snap} ({exc}) —— 手工删除后重试")
        else:
            _die(f"快照目录已存在且标记不匹配: {snap} —— 确认后 --fresh 重建")
    snap.mkdir(parents=True)
    count = 0
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as tf:
        # requires-python>=3.12: filter="data" 恒可用, 拒绝绝对路径/.. 穿越/链接逃逸;
        # git 树可存 symlink blob, 不能无 filter 解包
        tf.extractall(snap, filter="data")
        count = len(tf.getnames())
    (snap / ".snapshot-hash").write_text(freeze + "\n", encoding="utf-8")
    (snap / ".snapshot-info.json").write_text(
        json.dumps({
            "freeze": freeze,
            "generated_at": _now(),
            "source": str(root)
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )
    return count


def _check_snapshot(root: Path, data: dict) -> Path:
    snap = Path(data["snapshot"])
    marker = snap / ".snapshot-hash"
    if not snap.is_dir() or not marker.is_file():
        _fail(
            f"快照目录/标记缺失: {snap} —— start 仅放行 claimed: 手工把 route JSON 的 status 回退 claimed 后"
            f"重跑 review.lane.start --route {data['route']} 重建"
        )
    got = marker.read_text(encoding="utf-8").strip()
    if got != data["freeze"]:
        _fail(
            f"快照标记 {got[:12]} != 路线钉值 {data['freeze'][:12]} —— 手工把 route JSON 的 status 回退 claimed 后"
            f"重跑 review.lane.start --route {data['route']} --fresh"
        )
    return snap


def _print_triplet(root: Path, data: dict, manifest: dict, batch: dict | None) -> None:
    snap = Path(data["snapshot"])
    print("== 三件套(存量适配, 照抄派遣) ==")
    print(
        "1. 只读契约: 禁止一切写操作 —— git 状态变更(sync/rebase/merge/stash/checkout/commit/push)、"
        "写任何文件、跑 kb 等写类 task id 一律禁止, 只允许读命令; AGENTS.md 的开工同步对本任务豁免。"
    )
    print(f"2. 评审目标钉死: 快照目录 {snap}")
    print(f"   (冻结 {data['freeze'][:12]} 的 git archive 导出, 非 git 仓库, 纯只读树; 发现的 file/line/quote 一律以快照内容为准)")
    print("3. 开工自检: 快照存在且 .snapshot-hash == 钉值; 收尾复核: review.lane.verify 通过才采信发现。")
    if batch:
        print(
            f"当前批: {batch['id']} {batch['title']} [{batch['depth']}] — {len(batch['files'])} 文件 / {batch['total_lines']} 行"
        )
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
    _require_route_id(args.route)
    root = _resolve_root(args.root)
    cfg = _load_lane_config()
    manifest = _load_manifest(root, cfg)
    data = _load_route(root, cfg, args.route)
    if data["status"] != "claimed":
        _fail(f"{args.route} 状态为 {data['status']}, 仅 claimed 可 start")
    _require_branch(root, cfg)
    _require_ancestor(root, data["freeze"])
    # 放行 lane 目录内落盘(认领 JSON 可能尚未入库): 树净保的是「无混入的无关改动」,
    # 跨 clone 重复认领防护靠认领 JSON 入库基线分支, 与此检查无关(claim 输出已指引)。
    _require_clean(root, cfg, allow_lane=True)
    snap = _snapshot_dir(root, args.snapshot, cfg)
    _guard_snap_path(root, snap, cfg)  # --snapshot 任意路径 + --fresh 整删的组合必须先过容器守卫
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
        n = _extract_snapshot(root, data["freeze"], snap, cfg)
        print(f"快照导出完成: {snap} ({n} 个文件, freeze={data['freeze'][:12]})")
    data["snapshot"] = str(snap)
    data["status"] = "in-progress"
    data["started_at"] = _now()
    _save_route(root, cfg, args.route, data)
    first = next((b for b in data["batches"] if b["status"] == "pending"), None)
    mb = next((b for b in manifest["batches"] if b["id"] == first["id"]), None) if first else None
    _print_triplet(root, data, manifest, mb)
    print(f"路线进度: {sum(1 for b in data['batches'] if b['status'] == 'done')}/{len(data['batches'])} 批完成")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    _require_route_id(args.route)
    root = _resolve_root(args.root)
    cfg = _load_lane_config()
    manifest = _load_manifest(root, cfg)
    data = _load_route(root, cfg, args.route)
    if data["status"] != "in-progress":
        _fail(f"{args.route} 状态为 {data['status']}, 仅 in-progress 可 verify")
    _require_branch(root, cfg)
    _require_ancestor(root, data["freeze"])
    snap = _check_snapshot(root, data)
    _require_clean(root, cfg, allow_lane=True)
    done = sum(1 for b in data["batches"] if b["status"] == "done")
    print(
        f"Review passed: snapshot {snap} marker matches, tree clean (in {cfg['lane_dir']}/ "
        f"{sum(1 for st, p in _porcelain(root) if p.startswith(cfg['lane_dir']))} entries on disk), "
        f"progress {done}/{len(data['batches'])}"
    )
    mb_sel = None
    if args.batch:
        row = next((b for b in data["batches"] if b["id"] == args.batch), None)
        if not row:
            _fail(f"Batch {args.batch} does not belong to route {args.route}")
        if row["status"] != "pending":
            print(f"Batch {args.batch} status {row['status']}, not pending, no dispatch materials output")
            return 0
        mb_sel = next((mb for mb in manifest["batches"] if mb["id"] == args.batch), None)
        if mb_sel is None:
            _fail(f"Batch {args.batch} is not in the manifest (fail-closed)")
    else:
        pending = [b for b in data["batches"] if b["status"] == "pending"]
        if not pending:
            print("全部批次已勾选 —— 跑 review.lane.done 收尾")
            return 0
        mb_sel = next((mb for mb in manifest["batches"] if mb["id"] == pending[0]["id"]), None)
        if mb_sel is None:
            _fail(f"批次 {pending[0]['id']} 不在 manifest(fail-closed, 与 --batch 分支同口径)")
    _print_triplet(root, data, manifest, mb_sel)
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    _require_route_id(args.route)
    root = _resolve_root(args.root)
    cfg = _load_lane_config()
    data = _load_route(root, cfg, args.route)
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
    _save_route(root, cfg, args.route, data)
    done = sum(1 for b in data["batches"] if b["status"] == "done")
    print(f"批次勾选: {args.id} (findings={row['findings']}) —— 进度 {done}/{len(data['batches'])}")
    if done < len(data["batches"]):
        print(f"下一批: {next(b['id'] for b in data['batches'] if b['status'] == 'pending')}")
    else:
        print("全部批次完成 —— 跑 review.lane.done 收尾")
    return 0


def cmd_done(args: argparse.Namespace) -> int:
    _require_route_id(args.route)
    root = _resolve_root(args.root)
    cfg = _load_lane_config()
    data = _load_route(root, cfg, args.route)
    if data["status"] != "in-progress":
        _fail(f"{args.route} 状态为 {data['status']}, 仅 in-progress 可收尾")
    pending = [b["id"] for b in data["batches"] if b["status"] != "done"]
    if pending:
        _fail(f"还有未勾选批次: {', '.join(pending)} —— 完成判据=批次全覆盖无断号")
    lane = root / cfg["lane_dir"]
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
    _save_route(root, cfg, args.route, data)
    total = sum(b["findings"] for b in data["batches"])
    print(f"路线终态: {args.route} done —— findings {total} 条 / 批次 {len(data['batches'])}/{len(data['batches'])}")
    print("下一步: commands run ship.commit  # findings + 小结 + 状态单点入库; 之后由聚合会话 S6 合并")
    return 0


# --------------------------------------------------------------------------- smoke


def cmd_smoke(args: argparse.Namespace) -> int:
    """全环真冒烟: 真实 claim/start/verify/batch/done(含两个负例断言), 结束清理全部痕迹。

    与真路线的隔离: 快照用专用子目录 _smoke-<route>, cleanup 只删它, 不碰进行中路线的
    共享快照; 预清理只动 owner=smoke 的残留认领, 真实认领一律拒绝运行。
    负例断言: rejected 标志在 except 内置位, cleanup+_fail 全部落在 try 之外 ——
    守卫真失效时 _fail 不会再被自己的 except 吞掉(评审实证的自吞缺陷)。
    route 白名单格式校验(issue 26-11-17-2339)在一切 IO 之前: 该值要拼进下面的清理路径。
    """
    route = args.route
    _require_route_id(route)
    root = _resolve_root(args.root)
    cfg = _load_lane_config()
    ns = argparse.Namespace
    snap = _snapshot_dir(root, None, cfg) / f"_smoke-{route}"
    lane = root / cfg["lane_dir"]
    rpath = lane / f"route-{route}.json"

    def step(msg: str) -> None:
        # 负例步骤走 stderr(无缓冲), stdout 是块缓冲 —— 每步即时 flush 才不产生乱序伪影
        print(msg, flush=True)
        sys.stdout.flush()

    def cleanup(tag: str) -> None:
        for p in (rpath, lane / f"route-{route}-findings.json", lane / f"route-{route}-notes.md"):
            if p.is_file():
                p.unlink()
        if snap.exists():
            shutil.rmtree(snap, ignore_errors=True)
            if snap.exists():
                print(f"[warn] smoke 快照子目录删除失败(可能被占用), 手工删: {snap}", flush=True)
                return
            try:
                snap.parent.rmdir()  # 本 smoke 创建的父空壳随手带走; 父内有他路线快照时 rmdir 必败, 忽略
                snap.parent.parent.rmdir()  # 顶层快照容器(snapshot_root)/ 同理(仅空时可移除)
            except OSError:
                pass
        print(f"[smoke] 清理完成({tag}): route JSON / findings / 小结 / smoke 快照子目录已删", flush=True)

    # 预清理: 上次冒烟中途失败的残留(try/finally 的兜底只保本次, 修不掉上次)。真认领绝不触碰。
    if rpath.is_file():
        try:
            old = json.loads(rpath.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            old = {}
        if old.get("owner") == "smoke":
            cleanup("预清理上次冒烟残留")
        else:
            _fail(f"{route} 已被真实认领(owner={old.get('owner')}) —— smoke 拒绝在真实认领上运行, 换 --route")

    ok = False
    try:
        step(f"[smoke 1/7] claim {route} (真实写入)")
        cmd_claim(ns(route=route, owner="smoke", remote=args.remote, root=str(root), dry_run=False))
        step("[smoke 2/7] claim 重复认领负例(必须失败)")
        rejected = False
        try:
            cmd_claim(ns(route=route, owner="smoke", remote=args.remote, root=str(root), dry_run=False))
        except SystemExit as exc:
            if exc.code != 1:
                raise
            rejected = True
        if not rejected:
            _fail("重复认领未被拒绝 —— claim 守卫失效")
        print("[smoke] 重复认领按预期拒绝 (rc=1)", flush=True)
        step("[smoke 3/7] start (真实导出快照, smoke 专用子目录)")
        cmd_start(ns(route=route, snapshot=str(snap), fresh=False, root=str(root), dry_run=False))
        step("[smoke 4/7] verify (必须通过)")
        cmd_verify(ns(route=route, batch=None, root=str(root)))
        step("[smoke 5/7] done 负例(批次未齐, 必须失败)")
        rejected = False
        try:
            cmd_done(ns(route=route, root=str(root)))
        except SystemExit as exc:
            if exc.code != 1:
                raise
            rejected = True
        if not rejected:
            _fail("批次未齐时 done 未被拒绝 —— 完成判据守卫失效")
        print("[smoke] 批次未齐按预期拒绝 (rc=1)", flush=True)
        step("[smoke 6/7] 逐批勾选后 done (真实终态)")
        manifest = _load_manifest(root, cfg)
        data = _load_route(root, cfg, route)
        findings = lane / f"route-{route}-findings.json"
        notes = lane / f"route-{route}-notes.md"
        findings.write_text("[]\n", encoding="utf-8")
        notes.write_text(f"# smoke\n\n{route} 冒烟小结(测试痕迹, 可删)。\n", encoding="utf-8")
        for b in data["batches"]:
            cmd_batch(ns(route=route, id=b["id"], findings=0, root=str(root)))
        cmd_done(ns(route=route, root=str(root)))
        step("[smoke 7/7] 清理全部痕迹")
        ok = True
    finally:
        if not ok:
            cleanup("中途失败, 兜底清理")
    cleanup("全环通过")
    print("[smoke] 全环通过: claim/重复认领负例/start/verify/done 负例/逐批勾选/done/清理 全部符合预期", flush=True)
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

    p = sub.add_parser("manifest", help="生成 manifest.json(freeze 钉定+批次矩阵+底册切片+覆盖守卫)")
    p.add_argument("--remote", default="origin", help="钉定 freeze 时的远端核验目标(默认 origin)")
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
    p.add_argument("--snapshot", help="快照目录(默认 <repo>/../<lane.toml snapshot_root>/<repo名>)")
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
    p.add_argument("--route", required=True, help="冒烟用的路线 id(仅字母/数字开头结尾、中间字母/数字/-/_; 结束后清理其全部痕迹)")
    p.add_argument("--remote", default="origin")
    p.add_argument("--root")

    args = parser.parse_args()
    return {
        "manifest": cmd_manifest,
        "claim": cmd_claim,
        "start": cmd_start,
        "verify": cmd_verify,
        "batch": cmd_batch,
        "done": cmd_done,
        "smoke": cmd_smoke,
    }[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
