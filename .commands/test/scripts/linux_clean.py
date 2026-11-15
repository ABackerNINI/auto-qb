"""test.linux-clean: testbed 三层清扫自动化(issue 26-11-13-0212 认领落地; 计划单点
[memory-bank/plans/26-11-12-0152-plan-linux-testbed-docker.html](../../../memory-bank/plans/26-11-12-0152-plan-linux-testbed-docker.html)
§03 task 族表承诺行 / §10 R9 落地注记; 手工面先例 = 任务档案
memory-bank/tasks/26-11-12-test-linux-testbed.md S5 节)。

**纪律**(继承 S5 手工轮, issue §03): **白名单点名式逐项删**, 绝不许面杀命令(`docker system
prune` / `volume prune` / `image prune` 等在本脚本任何路径都不出现, 守阵钉 absence); PT 工具
容器与镜像硬禁(ban 名单命中即 [STOP] 全停, 不是跳过该项); **任何容器一律不删**(容器面只动
容器内 workdir)。

三层(与 issue 同口径):

- 一层 容器内 workdir(`/root/auto-qb-tests/`): 执行路径**复用 linux_ci.sweep_script**(「内嵌
  pid 已死 + mtime 超龄 12h」双条件单点, 不复制逻辑)。`--name <slug>` 点名 —— 唯一能清
  「已完结无标记」残留的口子: 正常收尾的 workdir 标记被 EXIT trap 摘掉(run_script 自清),
  双条件 sweep 永远碰不到它们, 而它们(整棵 code+venv)正是容器面累积的主源; 点名 pid 仍活
  仍拒(D5)。dry-run 由盘点脚本列出全部 workdir 与处置建议, 同样只盘点不碰。
- 二层 宿主悬空镜像 + 孤儿卷: 悬空镜像只挑 `-f dangling=true`(无 tag), 逐 ID `docker rmi`
  **不带 -f** —— 任何容器引用中的 ID docker 自己拒绝, 在用面(含 PT 容器)自然无损; 候选先按
  「无任何容器(含退出态)引用」筛一遍, 让演练清单与落实行为一致。孤儿卷: 名单白名单
  `^auto-qb-`(本体系命名前缀)且 `docker ps -a` 无任何容器引用才删, 白名单外一律不入选。
- 三层 旧 testbed tag: 只动 auto-qb-testbed 仓内 tag, 其它仓一个字不碰。保留三规则: 当前
  uv.lock hash8(下轮构建锚, linux_env.lock_hash8 单点) + 在跑容器镜像 ID 所指 tag(活面) +
  `latest`(构建输出锚); 其余 untag(rmi, 同 ID 多 tag 时只摘名不动层)。

**默认演练**(无参 = 只读盘点: 三层各列将删项/理由/尺寸, 不动任何东西); `--yes` 才落实删除
—— 保守默认(黄金法则 2): 删 docker 面是高险动作, 盘点先行是本 task 的使用姿势。附带
`--build-cache` 清 docker 构建缓存(`builder prune -f`, S5 手工同款; 默认**不含** —— 这是
唯一批量面, opt-in)。容器不在跑只跳一层(二层三层是宿主面照常), 修复先 test.linux-env。

守阵: `scripts/test_linux_clean.py`(纯函数钉面 + 脚本文本钉面 + 面杀命令/容器删除 absence 钉)。
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import linux_ci  # 同包脚本: sweep_script/sanitize_name/TESTS_ROOT 单点, 不复制字面量
import linux_env  # 同包脚本: 容器状态/lock_hash8/清单核验单点

USAGE = """\
用法: commands run test.linux-clean [-- --yes] [-- --name <slug>] [-- --build-cache]
  (无参)          演练: 只读盘点三层可回收面, 不动任何东西 —— 先演练核对清单, 再 --yes 落实
  --yes           落实删除(仍白名单点名式逐项; 绝无面杀命令)
  --name <slug>   点名容器内 workdir 一并清(唯一能清「已完结无标记」残留的口子; pid 仍活仍拒)
  --build-cache   附带清 docker 构建缓存(builder prune -f, S5 手工同款; 默认不含)
纪律: 白名单点名式逐项删(S5 手工轮); PT 工具容器与镜像硬禁; 任何容器一律不删。
"""

CONTAINER = linux_env.CONTAINER_NAME
IMAGE_REPO = linux_env.IMAGE_REPO
#: 测试态单根(容器内; 与 linux_ci.TESTS_ROOT 同一常量单点)
TESTS_ROOT = linux_ci.TESTS_ROOT
#: 一层 sweep 的 mtime 超龄阈值(linux_ci 单点, 守阵另有对齐 _tmp_bootstrap 的强钉)
SWEEP_AGE_SECONDS = linux_ci.SWEEP_AGE_SECONDS

#: PT 面 ban 名单(S5 纪律「PT 工具容器与镜像硬禁」; 宿主现状点名见本机 docker ps / 任务档案):
#: 词命中即拒 —— 白名单选择逻辑被将来改坏时这里是最后一道闸(命中 [STOP] 全停, 不是跳过该项)。
BAN_SUBSTRINGS = (
    "qbittorrent",
    "transmission",
    "deluge",
    "bitcake",
    "iyuu",
    "downonly",
    "accelerator",
    "resilio",
)
#: 精确禁删项: 生产应用镜像(本仓 Dockerfile 产物, 与 testbed 仓 auto-qb-testbed 相邻易混;
#: 精确匹配不伤 auto-qb-testbed / auto-qb-* 卷名)
BAN_EXACT = ("auto-qb", )
#: 孤儿卷白名单: 只认本体系命名前缀(auto-qb- 带连字符; 生产镜像名 auto-qb 不在此列)
VOLUME_WHITELIST_RE = re.compile(r"^auto-qb-")


def banned_reason(name: str) -> str | None:
    """命中 ban 名单返回命中说明, 未命中返回 None(守阵逐项钉, 含 testbed 不误伤)。"""
    low = name.lower()
    if low in BAN_EXACT:
        return f"精确禁删项(生产应用面): {name}"
    for word in BAN_SUBSTRINGS:
        if word in low:
            return f"含 PT 禁删词 {word!r}: {name}"
    return None


def parse_image_lines(out: str) -> list[tuple[str, str, str]]:
    """`docker images --format 'repo:tag id size'` 输出 -> [(ref, id, size)]。"""
    items: list[tuple[str, str, str]] = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 3:
            items.append((parts[0], parts[1], " ".join(parts[2:])))
    return items


def old_tag_candidates(images: list[tuple[str, str, str]], current_hash8: str, live_image_id: str | None) -> list[str]:
    """三层: 旧 testbed tag 候选(白名单点名式, 只动 IMAGE_REPO 仓内)。

    保留三规则(其余 untag): 当前 uv.lock hash8(下轮构建锚)/ 在跑容器镜像 ID 所指 tag(活面)/
    latest(构建输出锚)。
    """
    cands: list[str] = []
    for ref, img_id, _size in images:
        repo, _sep, tag = ref.rpartition(":")
        if repo != IMAGE_REPO or not tag or tag == "<none>":
            continue
        if tag == "latest" or tag == current_hash8:
            continue
        if live_image_id and img_id == live_image_id:
            continue
        cands.append(ref)
    return cands


def dangling_candidates(out: str, container_image_refs: set[str]) -> list[tuple[str, str, str]]:
    """二层悬空镜像候选: `-f dangling=true` 的无 tag ID, 被任何容器(含退出态)引用的不入选
    (docker rmi 不带 -f 本也会拒, 先筛一遍让演练清单与落实行为一致)。"""
    cands: list[tuple[str, str, str]] = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] not in container_image_refs:
            cands.append((parts[0], parts[1], " ".join(parts[2:])))
    return cands


def orphan_volumes(names: list[str], users: dict[str, list[str]]) -> list[str]:
    """二层孤儿卷候选: 白名单前缀(^auto-qb-)且无任何容器引用; 白名单外一律不入选。"""
    return [n for n in names if VOLUME_WHITELIST_RE.match(n) and not users.get(n)]


def inventory_script(age_seconds: int) -> str:
    """一层 dry-run 盘点(容器内, 只读): 列全部 workdir 与处置建议, 无删除动作。

    与 linux_ci.sweep_script 同纪律: 单根 /root/auto-qb-tests/ 内、只看 .run-pid 标记、
    双条件(pid 死 + 龄超限)才标「可回收」; 无标记 = 已完结会话(标记被 EXIT trap 摘掉),
    只盘点, 处置走 --name 点名。
    """
    return f"""set -u
root="{TESTS_ROOT}"
[ -d "$root" ] || {{ echo "[linux-clean] 容器内 {TESTS_ROOT} 不存在(无测试残留)"; exit 0; }}
now=$(date +%s)
for d in "$root"/*/; do
  d=${{d%/}}
  [ -d "$d" ] || continue  # 单根空时 glob 不展开, d 落成字面 $root/* —— 不给它出假条目
  m="$d/.run-pid"
  if [ ! -f "$m" ]; then
    echo "[linux-clean] 盘点: 已完结/无标记(双条件 sweep 碰不到, 可 --name 点名删): $d"
    continue
  fi
  pid=$(cat "$m" 2>/dev/null || true)
  case "$pid" in ''|*[!0-9]*) echo "[linux-clean] 盘点: 标记坏(不碰): $d"; continue ;; esac
  mtime=$(stat -c %Y "$d" 2>/dev/null || echo "$now")
  age=$(( now - mtime ))
  if kill -0 "$pid" 2>/dev/null; then
    echo "[linux-clean] 盘点: 会话在跑(pid $pid, 不碰): $d"
  elif [ "$age" -ge {age_seconds} ]; then
    echo "[linux-clean] 盘点: 可回收(pid $pid 已死, 龄 ${{age}}s >= {age_seconds}s): $d"
  else
    echo "[linux-clean] 盘点: pid 已死但未超龄(${{age}}s < {age_seconds}s, 本轮 sweep 不碰): $d"
  fi
done
exit 0"""


def targeted_script(slug: str) -> str:
    """--name 点名删(容器内): 路径钉死在单根下(slug 已过 sanitize_name, 纯 [a-z0-9-]);
    pid 仍活拒绝(D5)。无标记目录也允许 —— 正常收尾的 workdir 标记已被 EXIT trap 摘掉,
    点名是清它们的唯一口子(main 里 sanitize 调用是守阵钉面)。"""
    return f"""set -u
d="{TESTS_ROOT}/{slug}"
[ -d "$d" ] || {{ echo "[FAIL] 点名 workdir 不存在: $d"; exit 1; }}
m="$d/.run-pid"
if [ -f "$m" ]; then
  pid=$(cat "$m" 2>/dev/null || true)
  case "$pid" in ''|*[!0-9]*) ;; *)
    if kill -0 "$pid" 2>/dev/null; then
      echo "[FAIL] 会话仍在容器内跑(pid $pid)—— 不删(D5)。NEXT: 等该轮结束后重跑。"
      exit 30
    fi
  ;;
  esac
fi
rm -rf "$d" && echo "[linux-clean] 已删点名 workdir: $d"
"""


def _parse_args(argv: list[str]) -> tuple[bool, str, bool]:
    """argv -> (落实删除, 点名 slug, 含构建缓存); 未知旗标响亮拒绝(默认全 False = 演练)。"""
    yes, name, build_cache = False, "", False
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--yes":
            yes = True
            i += 1
        elif arg == "--name" and i + 1 < len(argv):
            name = argv[i + 1]
            i += 2
        elif arg == "--name":
            raise ValueError("--name 缺 <slug> 值(用法见 --help; 本 task 只认 --yes / --name <slug> / --build-cache)")
        elif arg == "--build-cache":
            build_cache = True
            i += 1
        else:
            raise ValueError(f"未知参数: {arg}(本 task 只认 --yes / --name <slug> / --build-cache)")
    return yes, name, build_cache


def _docker_run(args: list[str]) -> int:
    return subprocess.run(["docker", *args], check=False).returncode


def _docker_out(args: list[str]) -> tuple[int, str]:
    """跑只读 docker 命令, 返回 (rc, stdout) —— **rc 不许丢**: 枚举失败 = 宿主面状态未知,
    调用方必须按「未知」处置(跳过不删 + 计失败), 绝不能把空 stdout 当「无可回收项」出假
    清洁报告(daemon 未起时 which docker 仍命中, 全部枚举 rc!=0 且 stdout 空)。"""
    proc = subprocess.run(
        ["docker", *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, proc.stdout or ""


def container_image_refs(out: str) -> set[str]:
    """`docker ps -a --format {{.Image}}` -> 引用中的镜像(名或 ID); 悬空候选的「在用」判据。"""
    return {line.strip() for line in out.splitlines() if line.strip()}


def main(argv: list[str]) -> int:
    if "--help" in argv or "-h" in argv:
        print(USAGE, end="")
        return 0
    if "--safety" in argv:
        # 闸门安全过滤探针: 无参跑本脚本 = 只读演练(快、零副作用), **不**自认 action-without-args,
        # 留在冒烟面(冒烟给的是 --help, 同样只读; 与 linux_ci/linux_env 的重动作脚本两态相反)。
        return 0
    try:
        yes, name, build_cache = _parse_args(argv)
    except ValueError as exc:
        print(f"[STOP] {exc}")
        return 2
    if shutil.which("docker") is None:
        print("[STOP] 没装 docker: testbed 以 Docker 常驻容器为宿主(D1), 没 docker 跑不了")
        return 1
    root = Path(__file__).resolve().parents[3]  # <root>/.commands/test/scripts/linux_clean.py
    missing = linux_env.missing_manifest(root)
    if missing:
        print(f"[FAIL] 构建清单缺失: {root / missing} —— 三层保留规则要读 uv.lock 算 hash8, "
              "先检查仓库状态(别在残缺工作树上清扫)")
        return 2
    current_hash8 = linux_env.lock_hash8(root)
    mode = "落实删除(--yes)" if yes else "演练(只读盘点, 不动任何东西; 落实: commands run test.linux-clean -- --yes)"
    print(f"[linux-clean] 模式: {mode}")
    print(f"[linux-clean] 当前 uv.lock hash8 = {current_hash8}(三层保留锚)")
    had_failure = False

    state = linux_env.container_state()
    running = bool(state and state[0])
    live_image_id = state[1] if state else None

    # ---- 一层: 容器内 workdir ----
    if running:
        print(f"[linux-clean] 一层(容器内 {TESTS_ROOT}/):")
        if yes:
            proc = subprocess.run(
                ["docker", "exec", CONTAINER, "bash", "-c",
                 linux_ci.sweep_script(SWEEP_AGE_SECONDS)],
                check=False,
            )
            had_failure = had_failure or proc.returncode != 0
        else:
            proc = subprocess.run(
                ["docker", "exec", CONTAINER, "bash", "-c",
                 inventory_script(SWEEP_AGE_SECONDS)],
                check=False,
            )
            # 演练分支也接 rc: 容器 running 但 exec 失败(paused/不健康等)时, 一层段缺失
            # 不许静默成 rc 0 的「假清洁报告」(docker 自身报错已透传 stderr)
            had_failure = had_failure or proc.returncode != 0
        if name:
            try:
                slug = linux_ci.sanitize_name(name)
            except ValueError as exc:
                print(f"[STOP] {exc}")
                return 2
            if yes:
                proc = subprocess.run(
                    ["docker", "exec", CONTAINER, "bash", "-c",
                     targeted_script(slug)],
                    check=False,
                )
                had_failure = had_failure or proc.returncode != 0
            else:
                print(f"[linux-clean] 点名 {slug}: 演练不删; --yes 落实(pid 仍活仍拒)")
    elif name:
        print(f"[FAIL] 容器 {CONTAINER} 不在跑, 一层(含点名 {name})没法 exec。NEXT: "
              "先跑 `commands run test.linux-env` 再重跑本 task。")
        had_failure = True
    else:
        print(
            f"[linux-clean] 一层跳过: 容器 {CONTAINER} 不在跑(容器内 workdir 无法盘点)。NEXT: "
            "修复先 `commands run test.linux-env`(二层三层是宿主面, 照常)。"
        )

    # ---- 二/三层候选选择(宿主面; 白名单即选择逻辑, ban 终闸兜底) ----
    # ! 枚举失败(daemon 未起等) = 宿主面状态未知: 一律 [FAIL] 停手, 该面绝不按「空清单」处理
    #   (空清单会被当成「无可回收项」出具假清洁报告, rc 还恒 0)。
    # ! images×2 / ps 两形态枚举都必须 --no-trunc: {{.ID}}(docker images)与 {{.Image}}
    #   (docker ps, 镜像已无 tag 时)默认都截短 12 位, 而容器 inspect 的 .Image 是 full
    #   sha256:... —— 活面规则(live_image_id 比对)与悬空「无容器引用」判据都按 full 对齐,
    #   缺 --no-trunc 时比较恒失配(活面 tag 被误列候选 / 引用中的悬空 ID 漏筛), 实机演练
    #   抓出, 守阵钉死。
    rc_i, imgs_raw = _docker_out(["images", "--no-trunc", "--format", "{{.Repository}}:{{.Tag}} {{.ID}} {{.Size}}"])
    rc_p, ps_raw = _docker_out(["ps", "-a", "--no-trunc", "--format", "{{.Image}}"])
    rc_v, vols_raw = _docker_out(["volume", "ls", "--format", "{{.Name}}"])
    if rc_i or rc_p or rc_v:
        print(
            f"[FAIL] 宿主面枚举失败(images rc={rc_i} / ps rc={rc_p} / volume ls rc={rc_v}; "
            "daemon 未起或 docker 不可用)—— 宿主面状态未知, 二三层全部跳过不删。NEXT: "
            "核 docker daemon 后重跑本 task。"
        )
        return 1
    images = parse_image_lines(imgs_raw)
    old_tags = old_tag_candidates(images, current_hash8, live_image_id)
    refs = container_image_refs(ps_raw)
    rc_d, dang_raw = _docker_out(
        ["images", "--no-trunc", "-f", "dangling=true", "--format", "{{.ID}} {{.Size}} {{.CreatedSince}}"]
    )
    if rc_d:
        print(f"[FAIL] 悬空镜像枚举失败(rc={rc_d})—— 二层悬空面按未知处置跳过不删(其余面照常)。")
        dang, had_failure = [], True
    else:
        dang = dangling_candidates(dang_raw, refs)
    vol_names = vols_raw.split()
    users: dict[str, list[str]] = {}
    unknown_vols: set[str] = set()  # 引用枚举失败 = 状态未知: 绝不进孤儿候选(保守)
    for vol in vol_names:
        if VOLUME_WHITELIST_RE.match(vol):
            rc_u, u_raw = _docker_out(["ps", "-a", "--filter", f"volume={vol}", "--format", "{{.Names}}"])
            if rc_u:
                print(f"[FAIL] 卷引用枚举失败({vol}, rc={rc_u})—— 状态未知, 该卷跳过不删(保守)。")
                unknown_vols.add(vol)
                had_failure = True
                continue
            users[vol] = u_raw.split()
    orphans = [v for v in orphan_volumes(vol_names, users) if v not in unknown_vols]

    # ban 终闸(防御性): 白名单选择逻辑若被将来改坏命中 PT/生产面, 整个 task [STOP] ——
    # 不是跳过该项(选择逻辑已不可信时, 「跳过」没法证明其余候选安全)。
    for item in old_tags + orphans:
        reason = banned_reason(item)
        if reason:
            print(f"[STOP] ban 名单命中({reason})—— 候选选择逻辑疑似被改坏, 全停不删(容器内一层也不该信)。")
            return 1

    print("[linux-clean] 二层(宿主悬空镜像/孤儿卷):")
    for img_id, size, created in dang:
        if yes:
            rc = _docker_run(["rmi", img_id])
            note = "已删" if rc == 0 else "跳过(docker 拒绝, 在用面自然无损)"
            print(f"[linux-clean] {note}: 悬空镜像 {img_id}({size}, {created})")
            had_failure = had_failure or rc != 0
        else:
            print(f"[linux-clean] 盘点: 将删悬空镜像 {img_id}({size}, {created})")
    for vol in orphans:
        if yes:
            rc = _docker_run(["volume", "rm", vol])
            note = "已删" if rc == 0 else "跳过(docker 拒绝)"
            print(f"[linux-clean] {note}: 孤儿卷 {vol}(白名单 {VOLUME_WHITELIST_RE.pattern} 且无容器引用)")
            had_failure = had_failure or rc != 0
        else:
            print(f"[linux-clean] 盘点: 将删孤儿卷 {vol}(白名单 {VOLUME_WHITELIST_RE.pattern} 且无容器引用)")
    non_wl = sorted(v for v in vol_names if not VOLUME_WHITELIST_RE.match(v))
    if non_wl:
        print(f"[linux-clean] 盘点: 卷白名单外 {len(non_wl)} 个(不碰): {', '.join(non_wl)}")

    print("[linux-clean] 三层(旧 testbed tag):")
    for ref in old_tags:
        if yes:
            rc = _docker_run(["rmi", ref])
            note = "已 untag" if rc == 0 else "跳过(docker 拒绝)"
            print(f"[linux-clean] {note}: {ref}")
            had_failure = had_failure or rc != 0
        else:
            print(f"[linux-clean] 盘点: 将 untag {ref}(保留: current hash8 / live 镜像 ID / latest)")
    if not (dang or orphans or old_tags):
        print("[linux-clean] 宿主面无可回收项")

    if build_cache:
        print("[linux-clean] 附带(构建缓存, --build-cache):")
        if yes:
            rc = _docker_run(["builder", "prune", "-f"])  # 输出透传(docker 自报回收量)
            had_failure = had_failure or rc != 0
        else:
            print("[linux-clean] 盘点: 将 builder prune -f(S5 手工同款; 只清构建缓存, 不碰镜像/卷/容器)")
    else:
        print("[linux-clean] 附带构建缓存未启用(--build-cache 开)")

    return 1 if had_failure else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
