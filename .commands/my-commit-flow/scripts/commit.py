"""零参数全量提交 + 闸门 + 同步 + 推送 —— 编排合一, 承接 v3(计划 26-09-28-0157)「沉默即成功」并升级到 v3.1。

  结果行      → 提交成功 <hash>
  步骤行(上面) → 本次"真发生了"的 HEAD 改写, 相邻两步首尾相接 **旧hash→新hash**:
                同步: 远端领先 1 笔 · 本地领先 1 笔(分叉) → rebase 重放本地 1 笔 aa11bb22→bb22cc33
                闸门复跑: 合流后闸门改了 2 个文件 → amend bb22cc33→cc33dd44
                (非改写类: 合流后上游改动了本包时留一行「本次仍按启动版本运行, 重跑以采用新版本」)
  推送未完成  → 提交成功 <hash>(未推送) ＋ 推送未完成: <原因> —— 补推: commands run ship.push
                 (提交这个主目标已达成, 别重新提交; 退出码仍 0)
  失败        → 提交失败: <原因> —— <下一步>(闸门红附失败闸门名 + 输出末 20 行)
                树净的「没有可提交的改动」按**远端现查真值**分流(2026-10-17): 本地 ≠ 远端(有未推送的
                提交) → 直送 commands run ship.push, 别重跑 ship.commit; 一致 → 确实无事可做; 取不到 → 两条出路都摆

一次 ship.commit 里 HEAD 最多被改写三次 —— 提交自身、内部同步的 rebase、闸门复跑后的 amend
(补推前 run_push 内部还可能再同步一次)。结果行只给终值, 前两段若不登记就成了黑箱 —— 这正是 v3.1
要补的漏洞(2026-10-06 用户指出「输出过于精简, rebase 后 hash 变了会让人去查原因」)。
登记纪律见 `_pipeline.py`「步骤登记」段; 结果行的唯一出口是 `emit()`。

流程(2026-10-04 起**提交先行** —— 提交后树必然干净, 分叉 rebase 恒可自动, stash 解锁舞蹈自提交路径退役;
全部静默, 检查项一个不删 —— 保全清单见计划 §04):
  0. 提交信息机检(msg_check.py: 硬拦/自动修/警告三态, 计划 26-11-06-0124) —— 在闸门前拦: 消息修复是
     秒级动作; 自动修仅骨架位(BOM/承接空格/空行)且逐行留痕, 正文零代改; 逃生走 msg_check_allow
  1. 闸门(auto = true 真跑, 全过即静默; 失败给闸门名 + 末 20 行) —— 按本地改动清单
  2. 暂存计划: 缺省 = changed_files() 全量; 红线拦; 拒 -A / . / *(逐路径纪律)
  3. 逐路径 add —— 工作区已不存在的路径: 在索引里走 `rm --cached`, 都不在(已暂存的删除)则无事可做
     (修 issue 26-09-28-0128: 逐路径 add 撞「已暂存删除」的 pathspec 落空); 子集提交另打一行提示:
     未参与 add 的改动按索引状态分组(已暂存的仍随整索引进本笔 / 未暂存的不进本笔) —— git commit
     提交的是整个索引, 旧文案「未纳入」与事实相反(修 issue 26-10-16-1523)
  4. git commit -F <消息文件>; 消息缺省读 <root>/.git/COMMIT_MSG_AI.txt
  5. ref 三处核对(提交命令成功 ≠ ref 落稳 —— 本环境 ref 写入会被静默丢弃, 必须赶在同步前拦下:
     同步拿 HEAD 当真值, ref 丢了会把旧 tip 当成本地提交) → 落稳即消费消息文件
  6. 内部同步(run_sync): 齐平即 no-op; 分叉自动 rebase 保线性 —— 冲突 / 断网自动回滚后按
     「推送未完成」停下要人
  7. rebase 真合入了远端提交(HEAD 改写) → 复跑一轮(合并后的树才算数): 闸门命中与暂存仍按本批
     改动(present)算, 但 `<changed:>` 的展开面**扩到本批 + 远端合入的 memory-bank/** 文件
     (远端文件不产生本地 diff, 纯增量会漏扫它们; 计划 26-11-09-0559 §04 S4-1); fmt 类闸门若又
     改了文件 → 逐路径 add + commit --amend 折进未推送的 tip(与 sync.py 生成物收尾同款)。规则仍是
     **启动版本那份** —— 快照语义下不重取配置(那正是撕裂的来源); 合流若改动了本包, 登记一行提示重跑;
     复跑过后再登记一行「评审边界」—— 组合树只过了测试闸门, 评审未覆盖远端合入(计划 26-11-07-0201)
  8. 内联推送(run_push): 自带同步核对(竞态窗口兜底) / 推主线 20s×3 次(见 `_pipeline.run_git`) / 镜像 attempts=1 全程静默
消息文件不删的时机: commit 失败, 或 ref 核对失败**且** HEAD 消息与文件不一致(提交真没落到
ref, 修好重跑还能用同一份)。核对失败但 HEAD 消息与文件一致 = 提交已落稳(packed-refs 滞后类
误报, 2026-10-07 实证), 照常消费; 入口另有一道残留扫描(文件内容 == HEAD 消息即删并拒跑),
任何路径漏删的残骸在下一次 ship.commit 自愈。已判落稳时, 结果行如实写「提交已落稳, 仅分支 ref 未
核对通过」并直送补推 —— 不许再写「提交可能没落稳」(2026-10-17: 自相矛盾那句被读成"要重跑 ship.commit")。

用法: python <包>/scripts/commit.py [路径...] [--message-file <文件>] [--no-push]
退出码: 0 成功(含推送未完成) · 1 失败(输出自带原因, 不存在需要查的码表)
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Windows GBK 控制台兑底(与包内其它脚本同根): gitmoji 首行含 emoji, GBK 编不出来会让 print 崩掉。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _pipeline import (  # noqa: E402
    changed_files,
    config_stops,
    emit_steps,
    gates_for,
    git,
    git_run,
    hit,
    pack_touched,
    run_capture,
    run_gates,
    staged_overflow,
    step,
)
from _ship_config import (  # noqa: E402
    ConfigMissing,
    find_root as _find_root,
    load_config,
    resolve_branch,
    resolve_main_remote,
)
from verify_ref import check_refs  # noqa: E402
from msg_check import check_message_file  # noqa: E402  (提交消息机检, 计划 26-11-06-0124)

BULK = {"-A", "--all", ".", "*", "-u", "--update"}
DEFAULT_MESSAGE_REL = Path(".git") / "COMMIT_MSG_AI.txt"
# 记账类前缀 —— 同源抄自 .commands/review/scripts/check_review_trace.py(跨包不 import, 双处抄用 +
# 注释互指是既有先例: check_review_trace 的 SENSITIVE_PATH_MARKERS 也与 review_pack.py 同源双抄;
# 统一 import 单点超出本轮范围, 计划 26-11-07-0201 R2)。漂移后果: 评审边界提示行多打或少打一行, 不判红。
BOOKKEEPING_PREFIXES = (
    "memory-bank/tasks/",
    "memory-bank/active-context/",
    "memory-bank/testing/baselines/",
    "memory-bank/reports/attachments/legacy-review4/",
)


def emit(steps: list[str], line: str) -> None:
    """打结果行 —— 步骤行永远排在它上面。**所有**结果行都从这里出(别处 print 结果行会让步骤行掉队)。

    为什么必须集中: 一次提交里 HEAD 最多被改写三次(自身 → 内部 rebase → 闸门改后 amend);
    只要有一个出口绕开这里, 那个 hash 变化就成了无人解释的黑箱 —— 正是 v3.1 要补的洞。
    """
    emit_steps(steps)
    print(line)


def find_root() -> Path:  # noqa: F811  — 包一层, 测试替身钉这里
    return _find_root()


def default_message_path(root: Path) -> Path:
    """消息文件的约定单点 —— <root>/.git/COMMIT_MSG_AI.txt(永不入库, 多 clone 隔离)。"""
    return root / DEFAULT_MESSAGE_REL


def consume_message_file(msg_file: Path, root: Path) -> None:
    """消费即删 —— 提交落稳后删除约定路径的消息文件, 防旧消息残留被回看者当现状。

    只删约定路径: 显式 --message-file 指向别处的文件归调用方管。删除失败只提示
    不影响退出码 —— 提交已成功, 别让收尾环节的失败骗执行者重跑。
    Windows 上文件可能被刚写完它的编辑器 / 杀软短暂占着(共享冲突是瞬时的): 小步重试
    几次再放弃, 别把瞬时锁当成永久删除失败。
    """
    if msg_file != default_message_path(root):
        return
    last: OSError | None = None
    for attempt in range(3):
        try:
            msg_file.unlink()
            return
        except OSError as exc:
            last = exc
            time.sleep(0.2 * (attempt + 1))
    print(f"WARN: 消息文件删除失败({last}); 请手动删除 {msg_file}, 避免下次提交误读旧消息")


def head_message() -> str:
    """HEAD 提交消息原文(%B); 仓库无提交 / git 异常返回空串(调用方按不匹配处理)。"""
    proc = git_run("log", "-1", "--format=%B")
    return proc.stdout.strip() if proc.returncode == 0 else ""


def message_matches_head(msg_file: Path) -> bool:
    """消息文件内容 == HEAD 提交消息 → 这条消息已经随一次提交落库(残留判定单点)。

    两个消费点: 1) ref 核对失败出口 —— HEAD 消息与本文件一致说明分支 ref 已指向本次提交,
    核对红是其它两处滞后(packed-refs 落后, 2026-10-07 实证)的误报, 提交已落稳就该消费,
    不留「已入库消息」的残骸(修复 26-10-07: 残留会一直躺到下次提交覆盖, 期间可被当现状误读);
    2) 入口残留扫描 —— 上次落库后消息文件因任何路径漏删时, 下次 ship.commit 自愈, 并拦住
    「旧消息被当新提交的消息复用」。判不匹配时宁可保留不误删(修好重跑还能用同一份消息)。
    """
    head = head_message()
    if not head:
        return False
    try:
        content = msg_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return content.strip() == head


def resolve_stage_plan(paths: list[str], red_lines: list[str], staged: list[str],
                       unstaged: list[str]) -> tuple[list[str], list[str], str | None]:
    """算暂存计划, 返回 (to_stage, omitted, refuse); refuse 非 None 即拒绝执行。

    paths 为空 → 全量改动(权威单点 changed_files); 传路径 → 子集, omitted = 未传给脚本的其余改动
    (去重 —— MM 文件同时在 staged / unstaged 两份清单里, 不去重计数与示例会翻倍)。
    omitted 与「是否进了本笔」的关系由 omitted_note 按索引状态分组说明 —— 子集只限制 add 清单,
    git commit 提交的是整个索引(issue 26-10-16-1523)。红线按既有的子串口径匹配。
    """
    bulk = [p for p in paths if p in BULK]
    if bulk:
        return [], [], f"拒绝批量暂存 {' '.join(bulk)} —— 项目纪律是逐路径 add; 零参数 = 全量提交"
    all_changed = staged + unstaged
    if paths:
        to_stage = list(paths)
        omitted = [p for p in dict.fromkeys(all_changed) if p not in set(paths)]
    else:
        to_stage = all_changed
        omitted = []
    if not to_stage:
        return [], [], "没有可提交的改动 —— 工作区与索引都干净"
    red = [p for p in to_stage if any(r in p for r in red_lines)]
    if red:
        return [], [], f"红线文件不得提交: {' '.join(red)} —— 移出提交范围后重跑(见 AGENTS.md「红线」节)"
    return to_stage, omitted, None


def clean_tree_route(cfg: dict) -> str:
    """树净「没有可提交的改动」拒跑行的后缀 —— 按远端真值分流, 别把"已提交待推"读成"改动没落笔"。

    为什么(2026-10-17 实证): 首跑 ship.commit 因同步/推送失败停在「提交成功 <hash>(未推送)」后, 若再跑
    ship.commit(而不是 ship.push), 树已净 —— 旧口径只报「工作区干净(改动在别的 clone 或未保存?)」,
    把"提交已在本地、只差推送"误导成"改动没落地"(报告里被读成"提交丢了")。分流三档:
    - 远端 tip ≠ HEAD → 本地有未推送的提交 → 直送 `commands run ship.push`;
    - 远端 tip == HEAD → 已同步, 确实无事可做;
    - 取不到远端真值(离线 / 未配主线) → 如实说「无法核实」, 两条出路都摆出来。
    判据只认远端现查真值: 本环境 refs/remotes 的写入会被静默丢弃, `status -sb` 的 ahead/behind 是快照,
    都不可信(单点 memory-bank/pitfalls/git/refs.md)。attempts=1 —— 这是拒跑路径上的旁证查询, 离线时
    不该像推送那样白等三个退避周期(见 sync.remote_sha 的 attempts)。
    """
    from sync import remote_sha  # noqa: E402  (延后 import: 与 run_sync 同款, 测试替身可覆盖)

    main, _url = resolve_main_remote(cfg)
    tip = remote_sha(main, resolve_branch(cfg), attempts=1) if main else ""
    if not tip:
        return (
            "。取不到远端真值(未配主线 / 离线) —— 若上一步报过「提交成功 <hash>(未推送)」就补推 "
            "commands run ship.push; 否则核对改动是否在别的 clone / 未保存"
        )
    head = git_run("rev-parse", "HEAD").stdout.strip()
    if tip == head:
        return f"。与远端 {tip[:8]} 一致, 确实无事可做"
    return (
        f"。本地 {head[:8]} ≠ 远端 {tip[:8]}: 有未推送的提交 —— 补推走 commands run ship.push"
        f"(不要重跑 ship.commit; 见 references/pipeline.md「推送未完成」)"
    )


def _sample(files: list[str], limit: int = 3) -> str:
    """示例清单: 前 limit 个路径 + 省略号(与旧提示同口径 —— 3 个后省略)。"""
    return "、".join(files[:limit]) + ("…" if len(files) > limit else "")


def omitted_note(omitted: list[str], staged: list[str]) -> str:
    """子集提交的「另有 N 个改动未参与 add」提示行 —— 按索引状态分组, 让提示与提交面一致。

    为什么分组(issue 26-10-16-1523): 子集模式只限制 git add 清单, 而 git commit 提交的是
    **整个索引** —— 已暂存的其他改动照样随它落进同一笔。旧文案「未纳入」把这些也读成"没进",
    与事实相反(实测: 撤跟踪的 `D ` 删除项被列成「未纳入」, 却全在同一笔提交里)。
    - 已暂存(在 staged 清单里): 仍会随整索引进本笔 —— 没传给脚本也一样;
    - 未暂存(只在 unstaged 清单里): 不会进本笔 —— 想带上就得重跑并把路径补进参数。
    同一路径同时有已暂存与未暂存改动(MM)时归「已暂存」组: 其暂存快照确实落笔(未暂存部分不动)。
    """
    staged_set = set(staged)
    in_commit = [p for p in omitted if p in staged_set]
    out_commit = [p for p in omitted if p not in staged_set]
    parts = []
    if in_commit:
        parts.append(f"已暂存 {len(in_commit)} 个(仍会随整索引进本笔: {_sample(in_commit)})")
    if out_commit:
        parts.append(f"未暂存 {len(out_commit)} 个(不会进本笔: {_sample(out_commit)})")
    return f"…(子集提交: 另有 {len(omitted)} 个改动未参与 add —— {'; '.join(parts)} —— 确认这是有意的)"


def _generated_paths(root: Path) -> set[str] | None:
    """生成物权威清单(`gen_all.py --list` 子进程; 写法照 .commands/review/scripts/check_review_trace.generated_paths)。

    与那边的差别: 取不到时返回 **None** 而不是空集 —— 调用方把生成物豁免收窄为 `_index*` 兜底并
    照常判, 不静默视为全记账(计划 26-11-07-0201 落点 2: 宁可多打一行, 不可静默漏打)。子进程走
    run_capture(看门狗超时)而非裸 subprocess.run —— Windows 挂死陷阱的根因与处置见其注释。
    """
    script = root / ".agents/skills/memory-bank/scripts/gen_all.py"
    if not script.exists():
        return None
    proc = run_capture([sys.executable, str(script), "--list"], cwd=str(root))
    if proc.returncode != 0:
        return None
    paths = {line.strip().replace("\\", "/") for line in (proc.stdout or "").splitlines() if line.strip()}
    return paths or None


def _exempt_as_generated(path: str, gen: set[str] | None) -> bool:
    """生成物豁免(判据与 check_review_trace._is_generated 同源): 清单命中, 或 `_index*.md` 兜底。

    `gen is None`(清单取不到)时豁免收窄为 `_index*` 兜底 —— 权威清单缺席不得扩大成全豁免
    (计划 26-11-07-0201 落点 2)。
    """
    if gen is not None and path in gen:
        return True
    name = path.rsplit("/", 1)[-1]
    return name.startswith("_index") and name.endswith(".md")


def _count_and_paths(base: str, tip: str) -> tuple[int, list[str]] | None:
    """`base..tip` 的远端笔数与改动路径(计划 26-11-07-0201 落点 2 的判据公式: merge-base(旧HEAD,
    rsha)..rsha 只取远端侧); 空 / 非 0 笔都按推导失败返回 None。diff 带 core.quotepath=off ——
    非 ASCII 路径被八进制转义后会对不上本批清单(与 changed_files / check_review_trace._numstat 同款坑)。
    """
    n_raw = git("rev-list", "--count", f"{base}..{tip}", check=False)
    if not n_raw.isdigit() or int(n_raw) <= 0:
        return None
    paths = [
        line.strip()
        for line in git("-c", "core.quotepath=off", "diff", "--name-only", base, tip, check=False).splitlines()
        if line.strip()
    ]
    return int(n_raw), paths


def _remote_side(old_head: str, new_head: str) -> tuple[int, list[str]] | None:
    """本地推导 rebase 合入的远端侧(笔数, 路径), 零网络; 推导不可靠返回 None(调用方走旁证)。

    rsha 为什么这样取(计划 26-11-07-0201 落点 2 授权自定, 不按「先 ls-remote」走): rebase 刚把本地
    提交重放到远端 tip(rsha)上 —— new_head 历史 = 本地重放 M 笔 + rsha 及其祖先, 其中
    M = merge-base(old_head, new_head)..old_head 的笔数, 于是 rev-list 第 M+1 笔就是 rsha。好处:
    1) 零网络 —— ship.commit 的网络时刻刚在 sync 过完, 提交热路径不再添一次 ls-remote 等待;
    2) 免疫竞态 —— sync 与查询之间别的 clone 又推了一笔时, ls-remote 拿到的新 tip 对象还没 fetch,
    merge-base 直接失败; 本地推导只用已落对象库的历史。
    可靠性钉一道校验: 重放提交的 subject 序列必须与重放前逐条一致 —— rebase 会丢弃与远端 patch
    全同 / 合并后变空的本地提交, 那时第 M+1 笔会数偏, 校验不过就退回 ls-remote 旁证。
    """
    base = git("merge-base", old_head, new_head, check=False)
    if not base:
        return None
    m_raw = git("rev-list", "--count", f"{base}..{old_head}", check=False)
    if not m_raw.isdigit():
        return None
    m = int(m_raw)
    rsha = git("rev-list", f"--skip={m}", "--max-count=1", new_head, check=False)
    if not rsha:
        return None
    if git_run("merge-base", "--is-ancestor", rsha, new_head).returncode != 0:
        return None
    if git_run("merge-base", "--is-ancestor", rsha, old_head).returncode == 0:
        return None  # 候选是旧 HEAD 的祖先 —— 数偏了, 不猜
    if m > 0:
        mine = git("log", "--format=%s", f"{base}..{old_head}", check=False).splitlines()
        replayed = git("log", "-n", str(m), "--format=%s", new_head, check=False).splitlines()
        if mine != replayed:
            return None
    return _count_and_paths(base, rsha)


def _remote_side_via_remote_tip(cfg: dict, old_head: str) -> tuple[int, list[str]] | None:
    """ls-remote 旁证(attempts=1 —— 先例 sync.remote_sha 的注释: 旁证路径不值得等满退避, 与
    clean_tree_route 同款)。旁证失效(离线 / 竞态 tip 对象未 fetch)返回 None, 交降级文案。"""
    from sync import remote_sha  # noqa: E402  (延后 import: 与 run_sync 同款, 测试替身可覆盖)

    main, _url = resolve_main_remote(cfg)
    tip = remote_sha(main, resolve_branch(cfg), attempts=1) if main else ""
    if not tip or tip == old_head:
        return None
    base = git("merge-base", old_head, tip, check=False)
    if not base:
        return None  # 竞态: 同步之后远端又推进, 新 tip 的对象还没 fetch —— 旁证失效
    return _count_and_paths(base, tip)


def _rebase_merged_paths(root: Path, old_head: str, new_head: str) -> list[str] | None:
    """rebase 前后两棵树的差异里, `memory-bank/**` **与全仓 HTML** 且工作区仍存在的路径 ——
    **只喂 `<changed:>` 展开**。

    为什么(计划 26-11-09-0559 §02 洞 1): 远端 rebase 合入的文件**不产生本地 diff**(HEAD 已经跟着
    往前走了), 纯增量闸门(`--files <changed:memory-bank/**>`)对这批文件形同虚设 —— 而「合流后
    第二轮闸门」恰恰是唯一还能扫到它们的那一轮。

    为什么带 `*.html`(2026-11-09 终审 minor): HTML 闸门(S2)已从 `memory-bank/**` 放开到全仓
    `<changed:**/*.html>`, 远端合入的 `src/**` · `resources/**` 等非 KB HTML 同样不产生本地 diff;
    只取 KB 会让它们在复跑第二轮继续漏扫。git pathspec 的 `*.html` 自带跨目录语义(任意层级,
    含根目录), 与 `<changed:**/*.html>` 的匹配面一致; 仍由 `<changed:>` 的 glob 自行收窄
    (喂进来的 HTML 不会让 `memory-bank/**` 闸门多扫)。

    判据用「rebase 前后的 tree diff」而不是远端侧推导(同文件的 `_remote_side`): 零网络、对象都在
    本地对象库、**两棵树的净差异**天然把远端带进来的文件全收进来; 本地提交在 rebase 后是重放,
    内容不变 ⇒ 不会把本地改动重复计入(与 present 相交时由 `changed_for_expand` 去重)。删除件按
    `exists()` 滤掉(与 `present` 同口径 —— 闸门脚本只消费仍存在的文件)。
    None = diff 取不到: 调用方按「改动面拿不准宁可全量跑」兜底(计划 §01 底线 5)。
    """
    proc = git_run(
        "-c", "core.quotepath=off", "diff", "--name-only", old_head, new_head, "--", "memory-bank/", "*.html"
    )
    if proc.returncode != 0:
        return None
    return [p for p in (line.strip() for line in (proc.stdout or "").splitlines()) if p and (root / p).exists()]


def _tracked_scan_paths(root: Path) -> list[str]:
    """HEAD 里 `memory-bank/**` 与全仓 HTML 的全部跟踪路径 —— 扩面判定拿不准时的**全量兜底**清单。

    宁可多扫不可漏扫(计划 §01 底线 5): 全量跑只是慢(与收窄前的行为等价), 漏扫则是「合流后的树
    没人验」。取不到(ls-tree 非 0)返回空表 —— 那时闸门退回只扫本批改动, 与未扩面时一致。
    """
    proc = git_run("-c", "core.quotepath=off", "ls-tree", "-r", "--name-only", "HEAD", "--", "memory-bank/", "*.html")
    if proc.returncode != 0:
        return []
    return [p for p in (line.strip() for line in (proc.stdout or "").splitlines()) if p and (root / p).exists()]


def review_boundary_line(
    cfg: dict,
    root: Path,
    old_head: str,
    new_head: str,
    batch: list[str],
    head_clause: str = "组合树仅过测试闸门"
) -> str | None:
    """评审边界提示行(计划 26-11-07-0201 落点 2, 拍板 D2/D3) —— rebase 真合入远端提交时登记一行:
    评审未覆盖远端侧。远端改动**全部**落在记账类/生成物才不打(D3: 含手写文件就打)。返回行文案,
    None = 不打。`batch` = 本批改动清单(commit.py 步骤 1 的 staged+unstaged, 含删除的全集 ——
    删除相交在 rebase 会撞冲突到不了成功路径, 集合仍取全集保守计)。
    `head_clause` 按登记时点取真值: 复跑成功后的出口用默认「组合树仅过测试闸门」; 复跑判红的出口
    传「组合树测试闸门未过」—— 边界行在 rebase 合入后的**每个**出口都留痕(2026-11-07 收口评审:
    复跑红一次、修好再补推的组合树, 若只在成功尾部登记就漏了痕迹), 而「仅过」只在复跑真过后为真。
    """
    derived = _remote_side(old_head, new_head)
    if derived is None:
        derived = _remote_side_via_remote_tip(cfg, old_head)
    if derived is None:
        # 两条推导都取不到 → 「全记账类/生成物」的豁免无法核实, 不静默(宁可多打一行不可漏打): 降级成无数值的可见行
        return (f"评审边界: {head_clause}, 评审未覆盖远端合入的提交"
                "(笔数与路径无法核实 —— 本地推导与 ls-remote 旁证都取不到)")
    n, remote_paths = derived
    if not remote_paths:
        return None
    gen = _generated_paths(root)
    handwritten = [
        p for p in remote_paths if not any(p.startswith(prefix)
                                           for prefix in BOOKKEEPING_PREFIXES) and not _exempt_as_generated(p, gen)
    ]
    if not handwritten:
        return None  # D3: 全在记账类/生成物 → 不打
    m = len(set(remote_paths) & set(batch))
    shown = handwritten[:5]
    paths_txt = "、".join(shown) + (f" 等 {len(handwritten)} 条" if len(handwritten) > 5 else "")
    return f"评审边界: {head_clause}, 评审未覆盖远端 {n} 笔 · 路径 {paths_txt} · 与本批相交 {m} 处"


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="要暂存的路径(缺省 = 全部改动); 传了即子集提交")
    parser.add_argument("--message-file", default=None, help=f"提交消息文件(缺省 <root>/{DEFAULT_MESSAGE_REL}; 约定路径落稳后自动删除)")
    parser.add_argument("--no-push", action="store_true", help="只提交不推送(不同步, 离线可用; 补推: commands run ship.push)")
    args = parser.parse_args(argv)
    steps: list[str] = []  # 步骤登记簿由入口持有(见 _pipeline.py「步骤登记」段的三条纪律)

    try:  # 外置配置缺失 → 停手引导, 不猜默认值
        cfg, _src = load_config()
    except ConfigMissing as exc:
        emit(steps, str(exc))
        return 1
    stops = config_stops(cfg, _src)
    if stops:  # 未知键 / timeout 非法 → 闸门可能静默失效, 必须停(不降级)
        emit(steps, f"提交失败: 配置错误 —— {stops[0]}")
        return 1
    root = find_root()

    # 入口残留扫描: 约定消息文件的内容与 HEAD 消息一致 = 上次已落库提交漏删的残骸 ——
    # 删掉并拒跑(拦住旧消息被当本次提交消息复用)。必须在暂存计划之前: 落库后恢复路径
    # (手工修 ref + sync/push)结束时树是净的, 放在「没有可提交的改动」之后这扫永远够不着
    # (2026-10-07 实证的残留形态)。显式 --message-file 时约定文件归调用方管, 不扫。
    if args.message_file is None:
        default_msg = default_message_path(root)
        if default_msg.exists() and message_matches_head(default_msg):
            consume_message_file(default_msg, root)
            emit(steps, "提交失败: 消息文件是已落库提交的残留(内容与 HEAD 消息一致, 已删除) —— "
                 "有新改动就重写消息再跑, 没有则无需提交")
            return 1

    staged, unstaged = changed_files()
    overflow = staged_overflow(staged, cfg["staged_panic"])
    if overflow:
        emit(steps, f"提交失败: {overflow}")
        return 1
    to_stage, omitted, refuse = resolve_stage_plan(args.paths, cfg["red_lines"], staged, unstaged)
    if refuse:
        # 树净时别把"已提交、只差推送"读成"改动没落笔" —— 按远端真值补一句分流(2026-10-17, 见 clean_tree_route)
        line = refuse if (staged or unstaged) else f"{refuse}{clean_tree_route(cfg)}"
        emit(steps, f"提交失败: {line}")
        return 1
    warn_files = hit(staged + unstaged, cfg["warn_lines"])

    msg_file = Path(args.message_file).expanduser() if args.message_file else default_message_path(root)
    if not msg_file.exists():
        emit(steps, f"提交失败: 提交消息文件不存在 {msg_file} —— 把消息(中文首行 + 空行 + 动机/取舍/影响面/实测数字)"
             f"写入后重跑; 约定文件消费即删, 每次提交前都要重写")
        return 1

    # 0 提交信息机检(计划 26-11-06-0124): 在闸门前拦 —— 消息修复是秒级动作, 别让它排在一轮贵闸门后面;
    #   闸门复跑阶段的 amend --no-edit 复用已审消息, 不复检。自动修(仅骨架位)写回后逐行留痕 ——
    #   脚本改了 agent 写的文件, 沉默即成功只属于零修正的绿。违规不产生提交, 消息文件保留。
    report = check_message_file(msg_file, allow=frozenset(cfg.get("msg_check_allow", [])))
    if report.fixed:
        # 写回与 consume_message_file 同款小步重试 —— Windows 瞬时占锁(编辑器/杀软, 在库实证)
        # 不能变成裸 traceback(违反「失败=一行带原因与下一步」输出契约)。
        written = False
        last_exc: OSError | None = None
        for attempt in range(3):
            try:
                msg_file.write_text(report.text, encoding="utf-8", newline="\n")
                written = True
                break
            except OSError as exc:
                last_exc = exc
                time.sleep(0.2 * (attempt + 1))
        if not written:
            emit(steps, f"提交失败: 自动修正写回失败({last_exc}) —— 瞬时占锁时稍后重跑, "
                 f"或按下方修正说明手动改 {msg_file}")
            for line in report.fixed:
                print(f"已自动修正(未写回): {line}")
            return 1
        for line in report.fixed:
            print(f"已自动修正: {line}")
    for line in report.warnings:
        print(f"WARN: 提交信息: {line}")
    if report.violations:
        for vid, detail in report.violations:
            print(f"  - [{vid}] {detail}")  # ASCII 前缀: 代码打印面禁图形符号(code-style 约束)
        emit(
            steps, f"提交失败: 提交信息机检 {len(report.violations)} 项未过 —— 重写消息文件后重跑"
            f"(明细见上; 确认是误报时逃生: .my-commit-flow.toml 的 msg_check_allow 加对应条目 id)"
        )
        return 1  # 消息文件保留(自动修的部分一并保留): 修好后重跑用的是修后文本

    # 1 闸门(在暂存前: fmt 类闸门会改文件)。按本地改动清单跑; 合流后的树在步骤 6 复跑。
    #   评审留痕闸门(review.trace)要读提交信息: 闸门是 shell 子进程, 拿不到 args.message_file,
    #   所以把生效路径经环境变量递下去(约定路径与 --message-file 都覆盖)。不设它, 闸门只会去读
    #   .git/COMMIT_MSG_AI.txt —— --message-file 指向别处时就会读到旧文件, 判成"没写 trailer"(假红)。
    os.environ["COMMIT_FLOW_MSG_FILE"] = str(msg_file)
    changed = staged + unstaged
    present = [p for p in changed if (root / p).exists()]
    ctx = {"root": root, "changed": present, "each_limit": cfg.get("each_limit", 99)}
    failures, manual, _ran = run_gates(gates_for(present, cfg["gates"]), ctx)
    if failures:
        note, cmd, rc, secs, tail = failures[0]
        emit(steps, f"提交失败: 闸门「{note}」未过 (rc={rc}, {secs:.1f}s) —— 处理后重跑 commands run ship.commit")
        print(f"  $ {cmd}")
        for line in tail.splitlines():
            print(f"    {line}")
        return 1
    if manual:
        print("人工闸门(未自动执行, 需自行跑): " + " ; ".join(manual))

    # 2 逐路径暂存 —— 工作区已不存在的路径: 索引里还有 → rm --cached; 都不在(已暂存的删除)→ 无事可做
    for path in to_stage:
        exists = (root / path).exists()
        if not exists:
            in_index = git_run("ls-files", "--", path).stdout.strip()
            if in_index:
                proc = git_run("rm", "--cached", "--", path)
            else:
                continue  # 已暂存的删除: 索引与工作区都没有, add 本就无处匹配(issue 26-09-28-0128)
        else:
            proc = git_run("add", "--", path)
        if proc.returncode != 0:
            err = (proc.stderr or "").strip().splitlines()
            emit(
                steps, f"提交失败: git {'add' if exists else 'rm --cached'} 失败 {path} —— "
                f"{err[-1] if err else 'git 非 0'}"
            )
            return 1
    if omitted:
        print(omitted_note(omitted, staged))

    # 3 提交
    proc = git_run("commit", "-F", str(msg_file))
    if proc.returncode != 0:
        detail = [l.strip() for l in ((proc.stdout or "") + (proc.stderr or "")).splitlines() if l.strip()]
        emit(steps, f"提交失败: git commit 未通过 —— {detail[-1] if detail else 'git 非 0(明细: git status)'}")
        return 1  # 消息文件保留: 修好重跑还能用同一份
    sha_full = git_run("rev-parse", "HEAD").stdout.strip()
    sha = sha_full[:8]  # 8 位, 与 sync.py 的 <hash> 口径一致

    # 4 ref 三处核对 —— 提交命令成功 ≠ ref 落稳(本环境 ref 写入会被静默丢弃); 必须赶在同步前拦下:
    #   同步拿 HEAD 当真值, ref 丢了会把旧 tip 当成本地提交推出去
    ok, detail = check_refs()
    for line in detail:
        print(line)  # 自愈失败说明行仅在 COMMAND_FLOW_DEBUG=1 时返回; 正常路径/成功自愈时为空
    if not ok:
        if message_matches_head(msg_file):
            # HEAD 消息与文件一致 → 分支 ref 已指向本次提交, 核对红只是 packed-refs 滞后一类
            # 的误报(2026-10-07 实证: 当时提交已落稳, 消息文件按「保留现场」滞留成了残骸)。
            # 提交已落稳 → 照常消费; ref 处置后没有「重跑同一份消息」的需求了。
            consume_message_file(msg_file, root)
            print("消息文件已消费: HEAD 消息与之一致, 本次提交已落稳 —— 处置 ref 后直接补同步/推送即可")
            # 结果行不许与上面那句自相矛盾: 已判定落稳就别再说「提交可能没落稳」(2026-10-17),
            # 并直送补推 —— 否则「落稳却报失败」被读成"要重跑 ship.commit"(那次报告的直接诱因)。
            emit(
                steps, "提交失败: ref 三处不一致(HEAD 消息与本次一致 = 提交已落稳, 仅分支 ref 未核对通过)"
                " —— 处置下方 ref 后直接补推: commands run ship.push(不要重跑 ship.commit)"
            )
        else:
            emit(steps, "提交失败: ref 三处不一致 —— 提交可能没落稳; 确认无他人操作 .git 后按下方步骤处置")
        return 1  # 消息文件保留(仅当判不匹配 = 提交真没落到 ref): 现场未定, 别急着消费

    consume_message_file(msg_file, root)

    if args.no_push:  # 纯本地提交: 不同步不推送(离线可用), 合流留给补推时的 ship.push
        emit(steps, f"提交成功 {sha}(未推送 —— 补推: commands run ship.push)")
        if warn_files:
            print(f"WARN: 已包含: {'、'.join(warn_files)} —— 确认是有意的")
        return 0

    # 5 内部同步(提交先行, 2026-10-04): 树已净 —— 齐平 no-op / 分叉自动 rebase 恒可自动;
    #   冲突 / 断网自动回滚后停下要人 —— 提交已落稳, 按「推送未完成」处理, 别重新提交
    from sync import run_sync  # noqa: E402  (延后 import: 测试替身要能覆盖)

    ok, sync_line = run_sync(steps)
    if not ok:
        sep = "" if sync_line.startswith("需解决") else ": "
        emit(steps, f"提交成功 {sha}(未推送)")
        print(f"推送未完成: 同步失败{sep}{sync_line} —— 补推: commands run ship.push")
        if warn_files:
            print(f"WARN: 已包含: {'、'.join(warn_files)} —— 确认是有意的")
        return 0

    # 6 rebase 真合入了远端提交(HEAD 改写) → 闸门按同一份清单复跑一轮 —— 合并后的树才算数(检查项一个不删);
    #   fmt 类闸门若又改了文件, 逐路径 add 后折进未推送的 tip(rebase 后 tip 未推送, amend 安全)
    head_now = git_run("rev-parse", "HEAD").stdout.strip()
    if head_now != sha_full:

        def _boundary(clause: str = "组合树仅过测试闸门") -> None:
            # 评审边界行(6c)在合入后的每个出口统一登记(2026-11-07 收口评审补): 复跑红/机械失败/
            # 成功尾部各自留痕, 措辞按出口取真值 —— 「仅过测试闸门」只有在复跑真过后才为真。
            line = review_boundary_line(cfg, root, sha_full, head_now, changed, head_clause=clause)
            if line:
                step(steps, line)

        # 6a 快照语义(一次调用 = 一个版本): 本进程从启动起就跑在**仓库之外的副本**上(`_snapshot`),
        #    内部同步的 rebase 把远端新版**本包**写进工作区, 对本进程不可见 —— 新版本从下一次调用生效。
        #    这里只把"上游改过本包"如实登记一行: 静默会让人以为已经用上新版本(这正是撕裂要换来的东西)。
        if pack_touched(sha_full, head_now):
            step(steps, "快照: 上游改动了本包 → 本次仍按启动版本运行, 重跑以采用新版本")
        # 6b 复跑闸门: 规则仍是**启动版本那份** cfg —— 快照语义下不重取配置(那正是撕裂的来源);
        #    复跑要验的是"合并后的树" = 本批改动 + 远端合入的文件。
        #    扩面(计划 26-11-09-0559 §04 S4-1): 远端 rebase 合入的 KB / 全仓 HTML 不产生本地 diff,
        #    纯增量闸门(`--files <changed:...>`)扫不到它们 —— 合流后的第二轮是唯一还能扫到的那一轮。
        #    扩面只进 ctx 的独立键 `changed_extra`, 只影响 `<changed:>` 展开: present /
        #    gates_for 命中 / 暂存清单逐字不动(§07 R2)。拿不准(diff 取不到)→ memory-bank + 全仓
        #    HTML 全量, 宁可多扫不可漏扫(§01 底线 5), 并如实登记一行。
        merged_paths = _rebase_merged_paths(root, sha_full, head_now)
        if merged_paths is None:
            merged_paths = _tracked_scan_paths(root)
            step(
                steps, "复跑闸门: 远端合入面取不到(rebase 前后 diff 失败) → "
                f"memory-bank 全量 + 全仓 HTML 参与 <changed:> 展开({len(merged_paths)} 个文件)"
            )
        ctx_rerun = dict(ctx, changed_extra=merged_paths)
        #    ! 阶段标记: 评审留痕闸门(review.trace)按"锚点→工作树"算行数, 复跑时 rebase 进来的远端
        #    提交会被算进本批 → 假红。**用文件标记, 不用环境变量**: 闸门里会跑 pytest, 子进程继承
        #    env —— 实测 `COMMIT_FLOW_GATE_PHASE` 传下去后, 包里"跑闸门脚本并断言它判红"的自测全部
        #    拿到 0(齐红)。标记在 finally 删; 进程被杀导致残留时, 闸门脚本读到即消费(最多漏检一次)。
        post_marker = root / ".git" / "review_trace_post"
        post_marker.write_text(sha_full, encoding="utf-8")
        try:
            failures_r, _manual_r, _ran_r = run_gates(gates_for(present, cfg["gates"]), ctx_rerun)
        finally:
            post_marker.unlink(missing_ok=True)
        if failures_r:
            note, cmd, rc, secs, tail = failures_r[0]
            _boundary("组合树测试闸门未过")
            emit(steps, f"提交成功 {head_now[:8]}(未推送)")
            print(
                f"推送未完成: 闸门「{note}」未过(合并远端后复跑, rc={rc}, {secs:.1f}s) —— "
                f"修复后重跑 commands run ship.commit(修复将作为新提交入库)"
            )
            print(f"  $ {cmd}")
            for line in tail.splitlines():
                print(f"    {line}")
            if warn_files:
                print(f"WARN: 已包含: {'、'.join(warn_files)} —— 确认是有意的")
            return 0
        st_r, un_r = changed_files()
        dirty_r = [p for p in st_r + un_r if (root / p).exists()]
        for path in dirty_r:
            proc = git_run("add", "--", path)
            if proc.returncode != 0:
                err = (proc.stderr or "").strip().splitlines()
                _boundary()
                emit(steps, f"提交成功 {head_now[:8]}(未推送)")
                print(f"推送未完成: git add 失败 {path} —— {err[-1] if err else 'git 非 0'} —— 补推: commands run ship.push")
                if warn_files:
                    print(f"WARN: 已包含: {'、'.join(warn_files)} —— 确认是有意的")
                return 0
        if dirty_r:
            before = head_now
            amend = git_run("commit", "--amend", "--no-edit")
            if amend.returncode != 0:
                detail = [l.strip() for l in ((amend.stdout or "") + (amend.stderr or "")).splitlines() if l.strip()]
                _boundary()
                emit(steps, f"提交成功 {head_now[:8]}(未推送)")
                print(f"推送未完成: 闸门改动 amend 失败 —— {detail[-1] if detail else 'git 非 0'} —— 补推: commands run ship.push")
                if warn_files:
                    print(f"WARN: 已包含: {'、'.join(warn_files)} —— 确认是有意的")
                return 0
            head_now = git_run("rev-parse", "HEAD").stdout.strip()
            # 闸门复跑改了文件 → amend 又挪了一次 tip: 不登记的话, 成功行的 hash 第三次失真
            step(steps, f"闸门复跑: 合流后闸门改了 {len(dirty_r)} 个文件 → amend {before[:8]}→{head_now[:8]}")
            ok, detail = check_refs()  # amend 又是一次 ref 写入 —— 复核
            for line in detail:
                print(line)  # 自愈失败说明行仅在 COMMAND_FLOW_DEBUG=1 时返回; 正常路径/成功自愈时为空
            if not ok:
                _boundary()
                emit(steps, "提交失败: ref 三处不一致(amend 后) —— 提交可能没落稳; 确认无他人操作 .git 后按下方步骤处置")
                return 1
        # 6c 评审边界成功尾部(计划 26-11-07-0201 落点 2): 复跑真过 → 「仅过测试闸门」此刻才为真;
        #    其余出口的登记见上方 _boundary(2026-11-07 收口评审补齐, 措辞随出口)。
        _boundary()
    sha = head_now[:8]

    # 7 内联推送(run_push 内含同步核对 / 推主线 20s×3 重试 / attempts=1 静默镜像); 推送未完成 ≠ 提交失败
    from push import run_push  # noqa: E402

    pushed, push_line = run_push(steps)
    if not pushed:
        emit(steps, f"提交成功 {sha}(未推送)")
        print(f"推送未完成: {push_line} —— 补推: commands run ship.push")
    else:
        # run_push 内部同步可能又 rebase(竞态) → 以终值为准; 中间那次改写由它自己登记在步骤行里
        sha = git_run("rev-parse", "HEAD").stdout.strip()[:8]
        emit(steps, f"提交成功 {sha}")
    if warn_files:
        print(f"WARN: 已包含: {'、'.join(warn_files)} —— 确认是有意的")
    return 0


if __name__ == "__main__":
    from _snapshot import maybe_respawn  # noqa: E402  (快照自举: 一次调用 = 一个版本)

    _rc = maybe_respawn(__file__)  # 未在快照里 → 复制整包到仓库之外并重入
    if _rc is not None:
        raise SystemExit(_rc)  # 已由子进程(副本)接管
    raise SystemExit(main())
