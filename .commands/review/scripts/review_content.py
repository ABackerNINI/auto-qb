"""共享的「可评内容」过滤判定、锚点、逐笔行数实算与批次基哈希 —— 提交闸门与 review.pack 单点同源。

从 check_review_trace.py 抽出(计划 26-11-08-1240 §03 3.3): 「哪些路径计入可评内容」的判定
(记账类/生成物排除)原先内联在闸门脚本里, 而基哈希(下述)需要**同一套排除面** —— "末轮评审后
补写记账类/生成物不影响哈希(不误红)"与"记账类/生成物不计行"必须由同一份实现保证, 两处各自
演化就会出现行数实算与哈希口径分叉。

2026-11-11 再收编锚点与逐笔行数实算(anchor_commit / numstat_batch / untracked_batch,
原在闸门脚本): pack 的评审规模原先走树差 shortstat + 全量 untracked, 与闸门逐笔实算两套
口径 —— 记账类/未跟踪二进制在 pack 侧虚增(实测同一工作树 pack 报 9 行、闸门实算 1 行;
60k 行未跟踪 blob 被 pack 报 60009 行推上分面档), 多笔提交/合并拓扑下树差 ≠ 逐笔和。收编后
pack 的评审规模/分档与 trailer `<N> 行`(闸门实算)恒同源。

## 可评路径判定(_counted)
- 记账类: 结构由 check_doc_templates / check_status_drift / gen_active_recent 三道守卫管,
  它们的内容不进评审面(否则每笔收尾都会被自己的记账逼出一轮评审);
- legacy-review4/ 整目录是 R4 存量评审的 findings/manifest/路线小结 = 被评代码的产物(0441 落点
  3/D3), 与 review.lane.verify 的「树净仅该目录内允许落盘」同源; reports/attachments/ 其余件
  仍是事实性文档, 照旧计行;
- 生成物: `gen_all.py --list` 的权威清单(generated_paths); 取不到时退回 `_index*.md` 兜底,
  不静默失效成"索引重排也算改动"。

## 基哈希(batch_base_hash)
对「anchor -> 工作树」的**过滤后 diff** 构造确定性规范文本再取 sha256 前 12 个 hex 字符:
  已跟踪部分 = `git diff <anchor> -- <可评变更路径>` 的原文输出(--no-renames, 与闸门行数实算
              的删+增口径一致; 可评变更路径来自同参数 name-only 再过 _counted, pathspec 逐个加
              :(literal) 前缀防文件名里的通配字符被 glob 误匹配; 路径多时按字符预算分块多次跑
              再拼接 —— Windows 命令行 32767 字符上限, 块划分由路径序列决定, 拼接序确定);
  未跟踪可评文件 = 按 path 排序, 每文件 `path\n<完整内容>`(原文字节, 不可读按空内容);
  整体拼接 = 已跟踪 hunks(按 git 输出序) + 未跟踪文件(排序后), 对字节串取 sha256。
git 配置面双层钉死, 输出不随机器配置漂移(评审二轮 major 补强): env 层把 system 与 global 配置
整体掐断(_isolated_git_env: GIT_CONFIG_NOSYSTEM=1 / GIT_CONFIG_GLOBAL=<空设备> / GIT_CONFIG_COUNT=0,
后者同时压掉调用方进程继承的 GIT_CONFIG_KEY_N/VALUE_N 注入面); repo 层(.git/config)没有总开关,
由各调用的 -c 逐键压过(_DIFF_PINS: quotepath / noprefix / mnemonicPrefix / algorithm /
indentHeuristic / interHunkContext / suppressBlankEmpty / orderFile / attributesFile /
bigFileThreshold, 未跟踪清单另钉 excludesFile), 输出整形再加 --no-color / --unified=3 /
--src-prefix=a/ / --dst-prefix=b/ / --no-renames / --no-ext-diff / --no-textconv /
--ignore-cr-at-eol(行尾 CR 噪音不算可评改动 —— env 隔离把 core.autocrlf 掐成默认后 CRLF
工作树对 LF blob 会被误报整文件改动, 与 .gitattributes「行尾统一 LF」口径相反)。
固有残留面: .git/info/attributes 与 .git/info/exclude 是 clone 本地文件, git 没有配置开关可掐
—— 同 clone 内恒一致, 跨 clone 一致性由同版本 git + 同内容保证; 树内 .gitattributes/.gitignore
本身是被评内容(树附着), 不属配置漂移面。硬性质: 同一树重复调用同值(repo 配置覆写在场时也一样,
有回归测试钉住); 只改一个可评行/文件必变值; 记账类/生成物变更不影响。
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

# 记账类: 结构由 check_doc_templates / check_status_drift / gen_active_recent 三道守卫管,
# 它们的内容不进评审面(否则每笔收尾都会被自己的记账逼出一轮评审)。
# legacy-review4/ 整目录是 R4 存量评审的 findings/manifest/路线小结 = 被评代码的产物(0441 落点 3/D3),
# 与 review.lane.verify 的「树净仅该目录内允许落盘」同源; reports/attachments/ 其余件仍是事实性文档, 照旧计行。
BOOKKEEPING_PREFIXES = (
    "memory-bank/tasks/",
    "memory-bank/active-context/",
    "memory-bank/testing/baselines/",
    "memory-bank/reports/attachments/legacy-review4/",
)

# pathspec 一律加 :(literal) 前缀(评审二轮 nit): 裸字符串按 git glob 语义解释, 文件名里的
# [ ] * ? 会被当通配符误匹配别的路径 —— 分块下被误匹配路径的 diff 段会跨块重复吐出; literal
# 让匹配逐字精确, 跨 git 版本一致。前缀长度计入分块预算。
PATHSPEC_PREFIX = ":(literal)"

# 分块跑 git diff 的路径字符预算: Windows CreateProcess 整条命令行上限 32767 字符, 留一半余量
# 给 git 前缀参数与 :(literal) 前缀; pathspec 按 argv 逐个传(subprocess 不经 shell), 超预算才
# 分块, 少见路径数单块跑完。
PATHSPEC_CHAR_BUDGET = 16000

# diff 类调用的 repo 配置钉子(评审二轮 major): -c 逐键压过 .git/config(repo 层没有总开关);
# system/global 两层已由 _git_bytes 的 env 掐断。漏钉任何一颗, 同树哈希都会随 repo 配置漂移
# (回归测试: BatchBaseHashTest.test_hash_stable_under_config_overrides)。orderFile / attributesFile
# 钉到空设备而不是空值 —— 空值会被 git 拒收("failed to read orderfile")或回退默认查找路径,
# 空设备可读且无条目 = 保持默认行为; attributesFile 只掐 repo 配置注入的属性文件(树内
# .gitattributes 优先级更高且属被评内容, 不受影响)。bigFileThreshold 钉固定大值 2048m(上游默认
# 512m 的上限加倍): repo 配置调低会把超过阈值的文本文件 diff 压成 "Binary files ... differ" 一行。
# 固有残留面: .git/info/attributes 与 .git/info/exclude 是 clone 本地文件, git 没有配置开关可掐
# —— 口径: 同 clone 内恒一致; 跨 clone 一致性由同版本 git + 同内容(树内 .gitattributes/.gitignore
# 本身是被评内容, 树附着)保证。
_DIFF_PINS = (
    "-c",
    "core.quotepath=off",
    "-c",
    "diff.noprefix=false",
    "-c",
    "diff.mnemonicPrefix=false",
    "-c",
    "diff.algorithm=myers",
    "-c",
    "diff.indentHeuristic=true",
    "-c",
    "diff.interHunkContext=0",
    "-c",
    "diff.suppressBlankEmpty=false",
    "-c",
    "diff.orderFile=" + os.devnull,
    "-c",
    "core.attributesFile=" + os.devnull,
    "-c",
    "core.bigFileThreshold=2048m",
)


def _isolated_git_env() -> dict:
    """git 配置三层(system/global/repo)的前两层在这里整体掐断; repo 层由各调用的 -c 逐键钉
    (见 _DIFF_PINS)。GIT_CONFIG_COUNT=0 同时压掉调用方进程可能继承的 GIT_CONFIG_KEY_N/
    GIT_CONFIG_VALUE_N 注入面。本模块所有 git 子进程调用统一走这里。"""
    env = os.environ.copy()
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = os.devnull  # Windows=nul, POSIX=/dev/null: 可读的空"文件"
    env["GIT_CONFIG_COUNT"] = "0"
    return env


def _git_bytes(root: Path, args: list[str]) -> bytes:
    """跑 git 取原始字节输出(哈希面要字节精确, 不经文本解码), env 按 _isolated_git_env 隔离;
    失败可见报错并按用法/环境错误退出 2。"""
    proc = subprocess.run(["git", *args], cwd=str(root), capture_output=True, env=_isolated_git_env())
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", "replace").strip()
        print(f"[FAIL] review_content: git {' '.join(args)} 失败: {detail}", file=sys.stderr)
        raise SystemExit(2)
    return proc.stdout


def _decode(path: bytes) -> str:
    # 仅用于与 ASCII 前缀/后缀做排除匹配: 记账类前缀与 _index 后缀都是纯 ASCII, UTF-8 解码对
    # ASCII 段恒精确, 非法字节按 replace 只可能落在文件名多字节段, 不会把记账类误判成可评。
    return path.decode("utf-8", "replace")


def generated_paths(root: Path) -> set[str]:
    """生成物权威清单(`gen_all.py --list`); 取不到时退回 `_index` 兜底, 不静默失效成"索引重排也算改动"。"""
    script = root / ".agents/skills/memory-bank/scripts/gen_all.py"
    if script.exists():
        proc = subprocess.run(
            [sys.executable, str(script), "--list"],
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        if proc.returncode == 0:
            return {line.strip().replace("\\", "/") for line in proc.stdout.splitlines() if line.strip()}
    return set()  # 兜底由 _is_generated 的 _index 规则承担


def _is_generated(path: str, gen: set[str]) -> bool:
    if path in gen:
        return True
    name = path.rsplit("/", 1)[-1]
    return name.startswith("_index") and name.endswith(".md")


def _counted(path: str, gen: set[str]) -> bool:
    if _is_generated(path, gen):
        return False
    return not any(path.startswith(p) for p in BOOKKEEPING_PREFIXES)


def _reviewable_tracked_paths(root: Path, anchor: str, gen: set[str]) -> list[bytes]:
    """anchor -> 工作树的全部已跟踪变更路径(name-only --no-renames -z, 与闸门删+增口径一致),
    经 _counted 过滤后以原始字节返回(-z 保证含空格/非 ASCII 的路径逐字节还原)。
    --ignore-cr-at-eol: 行尾 CR 噪音不算改动 —— env 隔离把 core.autocrlf 掐成默认(不归一),
    CRLF 工作树对 LF blob 会被误报成整文件改动(与 .gitattributes「行尾统一 LF」口径相反),
    该旗标在检测侧把它压掉。钉子与整形旗标同 _tracked_diff 一套(name-only 下多数是 harmless
    no-op, 统一套防漏)。"""
    out = _git_bytes(
        root,
        [
            *_DIFF_PINS,
            "diff",
            "--name-only",
            "--no-renames",
            "--no-ext-diff",
            "--no-textconv",
            "--no-color",
            "--ignore-cr-at-eol",
            "-z",
            anchor,
        ],
    )
    return [p for p in out.split(b"\x00") if p and _counted(_decode(p), gen)]


def _pathspec_chunks(paths: list[bytes]) -> list[list[bytes]]:
    """按字符预算把路径序列切成定长的块: 块边界只由路径本身决定, 拼接序因此确定。
    预算按加 :(literal) 前缀后的 argv 实长算。"""
    chunks: list[list[bytes]] = []
    cur: list[bytes] = []
    cur_len = 0
    for p in paths:
        w = len(PATHSPEC_PREFIX) + len(p) + 1
        if cur and cur_len + w > PATHSPEC_CHAR_BUDGET:
            chunks.append(cur)
            cur, cur_len = [], 0
        cur.append(p)
        cur_len += w
    if cur:
        chunks.append(cur)
    return chunks


def _tracked_diff(root: Path, anchor: str, paths: list[bytes]) -> bytes:
    """`git diff <anchor> -- <可评变更路径>` 的原文输出。--no-renames: 与闸门行数口径一致,
    且去掉 rename 相似度阈值这一机器/版本变量; --unified=3 / --src-prefix=a/ / --dst-prefix=b/
    / --no-color 压掉 context/前缀/颜色配置, --no-ext-diff / --no-textconv 防外部驱动改写输出;
    --ignore-cr-at-eol 压行尾 CR 噪音(见 _reviewable_tracked_paths); 其余配置面由 _DIFF_PINS
    与 env 层钉死(见模块头)。pathspec 加 :(literal) 前缀(见 PATHSPEC_PREFIX)。"""
    if not paths:
        return b""
    flags = [
        "diff",
        "--no-renames",
        "--no-ext-diff",
        "--no-textconv",
        "--no-color",
        "--unified=3",
        "--src-prefix=a/",
        "--dst-prefix=b/",
        "--ignore-cr-at-eol",
        anchor,
        "--",
    ]
    parts = []
    for chunk in _pathspec_chunks(paths):
        # argv 传参: 路径字节按 surrogateescape 还原成 str(UTF-8 路径恒无损), 不经 shell 不怕空格
        argv = [*_DIFF_PINS, *flags] + [PATHSPEC_PREFIX + p.decode("utf-8", "surrogateescape") for p in chunk]
        parts.append(_git_bytes(root, argv))
    return b"".join(parts)


def _untracked_reviewable(root: Path, gen: set[str]) -> list[bytes]:
    """未跟踪可评文件, 按 path 排序(UTF-8 字节序, 与码点序一致, 跨机器稳定)。
    excludesFile 钉空值: repo/global 配置的额外忽略清单不得改写未跟踪集合(空值 = 未设, 实测可收)。"""
    out = _git_bytes(
        root,
        ["-c", "core.quotepath=off", "-c", "core.excludesFile=", "ls-files", "--others", "--exclude-standard", "-z"],
    )
    return sorted(p for p in out.split(b"\x00") if p and _counted(_decode(p), gen))


def batch_base_hash(root: Path, anchor: str) -> str:
    """「anchor -> 工作树」过滤后 diff 的基哈希: 规范文本(见模块头)取 sha256 前 12 hex。

    「可评路径」判定用本模块 _counted/generated_paths —— 与提交闸门行数实算同一份实现,
    记账类/生成物变更不影响哈希(计划 26-11-08-1240 D6/R4)。
    """
    gen = generated_paths(root)
    parts: list[bytes] = [_tracked_diff(root, anchor, _reviewable_tracked_paths(root, anchor, gen))]
    for path in _untracked_reviewable(root, gen):
        try:
            content = (root / os.fsdecode(path)).read_bytes()
        except OSError:
            content = b""  # 读不到按空内容: 与闸门"坏文件不卡闸门"同口径
        parts.append(path + b"\n" + content)
    return hashlib.sha256(b"".join(parts)).hexdigest()[:12]


# ---------------------------------------------------------------------------
# 批次实算(逐笔口径)与锚点 —— 自 check_review_trace.py 收编(2026-11-11): pack 的评审规模
# 与 trailer `<N> 行`(闸门实算)原先两套口径(见模块头), 收编后共用本节实现。
#
# 实算面与哈希面的 git 环境刻意不同: 哈希要跨机器确定性(env 隔离 + -c 钉子, 见上), 实算沿用
# 闸门历史行为(环境原样, 仅逐调用 quotepath=off 保路径解析) —— numstat 只计增删行, 对
# algorithm/context 等内容配置不敏感; 不要在这里补隔离改变既有实算口径。
# 唯一例外: 未跟踪清单钉 `core.excludesFile=` —— 与哈希面 _untracked_reviewable 对齐(repo/global
# 额外忽略清单不得改写未跟踪集合, 多算不漏算), 是刻意的口径偏离, 不属 numstat 的「沿用历史」范围。

REVIEW_LINE_RE = re.compile(r"^Review:\s*(.+)$", re.M)
SKIP_LINE_RE = re.compile(r"^Review-Skip:\s*(.+)$", re.M)


def _git_text(root: Path, *args: str, quiet: bool = False) -> str:
    """跑 git 取文本输出(UTF-8 收端, 与闸门原 _git 同款); 失败按用法/环境错误退出 2。

    quiet=True 不打 [FAIL] 行: 供「失败是预期内、调用方自带容忍分支」的路径(remerge 按 0 计)用,
    避免 [FAIL] 前缀 + 最终 rc=0 的组合误导读管线输出的 agent(评审二轮 nit)。
    """
    proc = subprocess.run(
        ["git", *args], cwd=str(root), capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if proc.returncode != 0:
        if not quiet:
            print(f"[FAIL] review_content: git {' '.join(args)} 失败: {proc.stderr.strip()}", file=sys.stderr)
        raise SystemExit(2)
    return proc.stdout


def anchor_commit(root: Path) -> str:
    """主线(first-parent 路径)上最近一条带 `Review:` / `Review-Skip:` 的提交; 一条都没有时退回
    HEAD(冷启动只算工作树)。消费方: 提交闸门定批次范围; review.pack 对 --base 做锚点核对。

    ! HEAD 探测容忍失败: unborn HEAD(新仓库首笔提交前)下 `rev-parse HEAD` 失败按空串处理 ——
    旧闸门 _git 不查 rc 的历史语义, 保住闸门 main() 的「仓库还没有任何提交」跳过分支(收编搬移
    时曾被 _git_text 的 fail-fast 变成 rc=2 崩溃, 评审一轮 major 回归, 2026-11-11)。
    ! 不设扫描窗口: 曾经用 `-200` 提速, 结果"上一条 trailer 在第 201 笔"时静默退回 HEAD ——
    整段累计批被丢弃且无任何提示, 正好与"漏评提交滚进下一批"的连坐机制相反(2026-11-06 评审实测)。
    几千笔提交的 message 全量解析也就几百 KB, 不值得为它换一个静默失效点。
    ! 必须 --first-parent: 侧分支 tip 自带 trailer 时(跨 clone 分支流的常态), 平铺 log 按提交时间
    会取到它 —— 而侧分支常从旧基线切出, 配合树差口径会把主线在分支切出之后的全部已评
    工作整支算进「本批」(2026-11-08 实证: config-infra 分支 tip 80df0b9a 遮蔽主线锚点 70bba719,
    实算虚增 ~9600 行, 提交被死锁; 详见 issue 26-11-08-0903)。侧分支的提交已随它自己的 trailer
    评审过, 不该由主线锚点承担。
    """
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(root), capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    head = proc.stdout.strip() if proc.returncode == 0 else ""
    if not head:
        return ""
    for rec in _git_text(root, "log", "--first-parent", "--format=%H%x1f%B%x1e").split("\x1e"):
        if "\x1f" not in rec:
            continue
        sha, _, body = rec.partition("\x1f")
        if REVIEW_LINE_RE.search(body) or SKIP_LINE_RE.search(body):
            return sha.strip()
    return head


def _count_numstat(root: Path,
                   git_args: list[str],
                   gen: set[str],
                   total: int,
                   files: list[str],
                   quiet: bool = False) -> tuple[int, list[str]]:
    """跑一条 numstat 类 git 命令并把结果累计进 (total, files)。

    quiet 透传 _git_text: remerge 容忍路径按 0 计不打 [FAIL](见 _commit_numstat)。

    `--no-renames`: numstat 默认把改名写成 `a/{b => c}/d` 合成串, 既不是真实路径、也不匹配任何
    前缀 —— 移进记账目录的改名会被当普通改动计入, 生成物的 `{_index.md => _index-1.md}` 也绕开
    排除。改成删+增: 行数偏大(同一内容计两次), 但宁可多算不漏算。
    `core.quotepath=off`: 默认 ON 时非 ASCII 路径被八进制转义加引号, `root / path` 不存在 →
    整批漏计(与 _pipeline.changed_files 同款坑)。
    """
    for line in _git_text(root, "-c", "core.quotepath=off", *git_args, quiet=quiet).splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        add, delete, path = parts[0], parts[1], parts[2].strip()
        if not _counted(path, gen):
            continue
        files.append(path)
        if add == "-" or delete == "-":  # 二进制
            continue
        total += int(add) + int(delete)
    return total, files


def numstat_batch(root: Path, base: str, gen: set[str]) -> tuple[int, list[str]]:
    """`base` 之后的主线提交逐笔 + 侧分支无 trailer 提交 + 工作树 的改动行数(增+删)与路径清单。

    为什么逐笔不整段树差: base..HEAD 之间含合并提交时(跨 clone 分支流合流的常态), 树差
    `git diff base` 量的是「两棵树的差」而不是「新增了哪些提交」—— 被合并分支的已评内容
    会整支算进本批(2026-11-08 实证, 详见 issue 26-11-08-0903)。逐笔口径:
      普通提交 = `git diff <sha>^ <sha>`(自身改动);
      合并提交 = `git show --remerge-diff`(自动合并结果 vs 实际合并结果 = 纯冲突解决面 ——
                 分支侧内容已随分支自己的 trailer 评过, 第一父母树差/combined diff 都会把它们
                 重复计入; 实证 0469bf0c: 第一父母差 53 文件, remerge 只剩 2 个生成物);
                 remerge 失败(旧 git / 特殊提交)按 0 计。
      侧分支提交 = base..HEAD 全集里不在 first-parent 路径上的那部分: 带 Review/Review-Skip
                 trailer 的(已评)排除; **无 trailer 的按自身 diff 计入** —— 连坐承诺(漏评滚进
                 下一批)对侧分支同样成立: 裸 git commit / 漏写 trailer 的提交落在侧分支再被
                 干净合并, 若只算主线+remerge 会整类漏计(评审二轮 major, 假绿通路)。
    工作树部分 = `git diff HEAD`(已暂存未提交 + 未暂存)。
    """
    total, files = 0, []
    mainline = _git_text(root, "rev-list", "--first-parent", f"{base}..HEAD").split()
    seen = set(mainline)
    side = [s for s in _git_text(root, "rev-list", f"{base}..HEAD").split() if s not in seen]
    for sha in mainline:
        total, files = _commit_numstat(root, sha, gen, total, files)
    for sha in side:
        body = _git_text(root, "log", "-1", "--format=%B", sha)
        if REVIEW_LINE_RE.search(body) or SKIP_LINE_RE.search(body):
            continue  # 侧分支自带 trailer = 已评, 不计入
        total, files = _commit_numstat(root, sha, gen, total, files)
    return _count_numstat(root, ["diff", "--numstat", "--no-renames", "HEAD"], gen, total, files)


def _commit_numstat(root: Path, sha: str, gen: set[str], total: int, files: list[str]) -> tuple[int, list[str]]:
    """单笔提交的改动行数: 普通提交 = 与父母的差; 合并提交 = remerge(冲突解决面, 失败按 0 计)。"""
    parents = _git_text(root, "rev-list", "--parents", "-1", sha).split()
    if len(parents) > 2:  # 合并提交(sha + ≥2 父母)
        args = ["show", "--remerge-diff", "--numstat", "--format=", "--no-renames", sha]
    else:
        args = ["diff", "--numstat", "--no-renames", f"{sha}^", sha]
    try:
        return _count_numstat(root, args, gen, total, files, quiet=len(parents) > 2)
    except SystemExit:
        if len(parents) > 2:
            return total, files  # remerge 失败的合并提交按 0 计(见 numstat_batch docstring)
        raise


def untracked_batch(root: Path, gen: set[str]) -> tuple[int, list[str], dict[str, int]]:
    """未跟踪可评文件的行数实算: (总行数, 路径清单, 每文件行数)。

    前两个返回值是提交闸门的历史口径; 第三个供 review.pack 的文件清单展示(每文件
    `[未跟踪 +N 行]`), 同一趟 ls-files 顺带产出, 不让 pack 再走一遍。
    二进制(前 8192 字节含 0x00)按 0 行计: 随机 0x0A 会被数成上千行(pack 旧统计的虚增来源,
    2026-11-11 实测 60k 行 blob 被报 60009 行推上分面档) —— 但路径仍进清单供敏感面判定。
    excludesFile 钉空值: repo/global 配置的额外忽略清单不得改写未跟踪集合。
    """
    proc = _git_text(
        root, "-c", "core.quotepath=off", "-c", "core.excludesFile=", "ls-files", "--others", "--exclude-standard"
    )
    total, files, by_file = 0, [], {}
    for rel in (p.strip() for p in proc.splitlines()):
        if not rel or not _counted(rel, gen):
            continue
        files.append(rel)
        try:
            raw = (root / rel).read_bytes()
        except OSError:
            by_file[rel] = 0
            continue  # 读不到按 0 行计: 不让一个坏文件把整道闸门卡死
        if b"\x00" in raw[:8192]:
            by_file[rel] = 0
            continue  # 二进制: 按 0 计(但仍进 files 供敏感面判定)
        n = len(raw.decode("utf-8", "replace").splitlines())
        by_file[rel] = n
        total += n
    return total, files, by_file
