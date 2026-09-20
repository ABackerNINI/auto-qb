"""my-commit-flow 的配置单点 —— 换机器 / 换项目只改这里。

**通用性声明**: 本 skill 依赖本仓库的具体环境(Windows 工具 shell 的删除拦截层、Gitee 主线 +
GitHub 镜像双远端、9 个 worktree 并行), 不是通用 git 工作流。拿到别的项目用之前, 先把本文件的
远端名 / 分支 / 红线清单改对, 并确认那个环境没有「脏工作区 + 非快进合并 → 删 .git/objects」的拦截层。
"""

from __future__ import annotations

# 协作主线(判交付看它)与镜像(允许滞后)
REMOTE_MAIN = "origin"  # Gitee; 该 clone 若把 Gitee 挂成 `gitee`, 改这里
REMOTE_MIRROR = "github"  # GitHub 镜像; 不存在也不算 STOP, 只提示补 remote
MAIN_HOST_MARK = "gitee.com"  # 判断 REMOTE_MAIN 是否真是主线
BRANCH = "develop"

# 红线: 出现即 STOP(不得进暂存清单)
RED_LINES = (
    "config.yml",  # 用户真实生产配置, 非示例
    "auto-qb-data/",  # 运行时数据(state.json / 锁 / 日志 / 跳检备份)
)
# 高危: 出现需人工确认(可能是用户自己的在途改动)
WARN_LINES = (
    "想法.md",
    ".workbuddy-ai/",  # 项目数据目录, 一般不入库(.gitignore 已忽略, 出现即为异常)
)

# 闸门: 改动命中哪些文件 → 提交前必须跑什么(脚本只提示, 由执行者跑)
GATES: tuple[tuple[tuple[str, ...], tuple[str, ...], str], ...] = (
    (("src/", "tests/"), ("yapf -i <改过的 py 文件>", "uv run pytest tests -q"),
     "Python 改动: 先格式化再跑全量测试"),
    (("memory-bank/issues/",), ("python .agents/skills/create-issue/scripts/gen_issues_index.py --check",),
     "issue 池改动: 索引是生成物, 必须 --check 通过"),
    (("memory-bank/tasks/",), ("python scripts/gen_tasks_index.py --check",), "任务档案改动: 索引需自洽"),
    ((".agents/skills/",), ("python <改动脚本> --help",), "skill 改动: 冒烟跑一遍被改的脚本"),
)

# 平台差异: 命中这些关键词的改动, Windows 全绿不算数, 要去 Linux 复现
LINUX_CHECK_HINTS = ("winreg", "shutil.rmtree", "dir_fd", "socket", "subprocess", "os.open")

# GitHub 镜像直连: 用 -c 覆盖为空即禁用全局 per-URL 代理
MIRROR_PROXY_DISABLE_ARGS = ("-c", "http.https://github.com.proxy=")
MIRROR_URL = "https://github.com/ABackerNINI/auto-qb.git"

# 提交后若 staged 数量超过这个阈值 → 高度怀疑「分支 ref 被别的会话回退」(见 pitfalls)
STAGED_PANIC = 200
