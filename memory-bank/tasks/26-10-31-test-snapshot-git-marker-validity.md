# 26-10-31-test-snapshot-git-marker-validity — 快照 _find_repo_root 判据加 .git/HEAD 有效性校验: 空壳标记不算仓库根

**Status:** Done
**Added:** 2026-10-31
**Updated:** 2026-10-31
**Summary:** 快照 _find_repo_root 判据加 .git/HEAD 有效性校验: 空壳标记不算仓库根
**Topics:** test-snapshot-git-marker-validity

## 原始请求

1. (追问) `_find_repo_root` 为什么会找到用户目录去? —— 已答: TMPDIR 指向未挂载的 `R:` 回落用户 `%TEMP%` + 家目录空 `.git` 空壳叠加, walk-up 只查存在性被空壳骗中。
2. 给判据加 `.git/HEAD` 有效性校验。

## 思考过程与决策

- 判据分形态: `.git` **目录**必须含 `HEAD`(真仓库 `git init` 即建; 空壳/半初始化目录不算 —— 26-10-31 事故: 家目录被塞空 `.git` + TMPDIR 回落用户资料区, walk-up 在此误判仓库根把 `REPO_ROOT` 注进无关运行); `.git` **文件** = worktree 指针, 文件本身即真标记, 直接命中(误造 `.git` 文件的概率远低于误造目录, 不再深验内容)。
- 生产调用面安全: `_run` 里 `_find_repo_root(src_pack)` 起点在仓库内, 第一个祖先即本项目真 `.git`, 行为不变; 只有测试类「仓库外路径」场景走完整 walk-up。
- 守阵策略: 原 walk-up 用例用空 `.git` 目录当标记 —— 与新判据语义相悖, 改为真标记(`.git/HEAD`); 新增空壳豁免(事故回归阵)与 worktree 文件两例; 文件头「## 测试计划」同步。

## 实现计划

两步: ①`_snapshot.py::_find_repo_root` 目录形态加 `HEAD` 存在性检查、文件形态(worktree)保持命中, docstring 记事故与判据; ②`test_snapshot.py` 三例改/增(真标记 walk-up / 空壳不算仓库 / worktree 文件命中) + 头部测试计划措辞。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | `_find_repo_root` 判据改造 + docstring | Done(26-10-31) |
| 2 | 守阵三例改/增 + 测试计划同步, test.pkg 188 全绿 | Done(26-10-31) |
| 3 | test.full 4304+10(基线切片 26-10-31-2214) + 立档收尾 | Done(26-10-31) |

## 进度日志

### R0 · 立档 (2026-10-31)

上一轮 ship.commit 闸门事故(test_find_repo_root_returns_none_outside_repo 被家目录空 `.git` + R: 盘未挂载叠加打红)的根治项; 判据加 HEAD 有效性校验后空壳标记恒不算仓库, 同类环境复发不再影响提交闸门。

- 2026-10-31 22:01 根治 26-10-31 闸门事故: _find_repo_root 判据加 .git/HEAD 有效性校验(目录形态空壳不算仓库, worktree 文件保持命中); 守阵三例改/增, test.pkg 188 全绿; test.full 4304+10 见基线 26-10-31-2201
