"""共享的「可评内容」过滤判定与批次基哈希 —— 提交闸门与 review.pack 单点同源。

从 check_review_trace.py 抽出(计划 26-11-08-1240 §03 3.3): 「哪些路径计入可评内容」的判定
(记账类/生成物排除)原先内联在闸门脚本里, 而基哈希(下述)需要**同一套排除面** —— "末轮评审后
补写记账类/生成物不影响哈希(不误红)"与"记账类/生成物不计行"必须由同一份实现保证, 两处各自
演化就会出现行数实算与哈希口径分叉。

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
