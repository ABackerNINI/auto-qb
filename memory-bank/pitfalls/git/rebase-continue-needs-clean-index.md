# rebase --continue 前索引必须全暂存(git 2.55): 生成物自动化解只 add 冲突集会卡死

> 摘要: 分叉 rebase 撞生成物冲突, 走「取一侧 + 重跑生成器」自动化解时: 重跑会把**其它干净自动合并**的白名单生成物也改出未暂存修改(MM 态), 而旧脚本只 `git add` 冲突集(unmerged 那几个) —— `rebase --continue` 在 git 2.55 上对此报「You must edit all merge conflicts...」并拒绝, 回滚后对外的失败行仍是「需解决冲突…手动合流」, 误导性极强(其实没有任何未解冲突, `ls-files -u` 为空)。手动解: `git add` **全部**改动路径(至少所有 MM 白名单件)再 continue。2026-10-15 提交 4d268762 时实测两连败(ship.commit 内部 sync + 独立 sync 均因此失败行)。**脚本侧根因已于 2026-11-02 修复**(issue 26-11-01-2140: sync.py 现在把「白名单 ∩ 全部改动路径含新增」与冲突集一并暂存), 手动配方保留作旧版脚本与其它调用方的兕底。
> 等级: L0
> 触发: rebase, rebase --continue, 生成物自动化解, MM 状态, 未暂存修改, sync 失败行, 需解决冲突, git 2.55, 索引不干净

### 自动化解的最后一公里: add 的范围小于改动的范围

- **触发**: `my-commit-flow.sync` / `ship.commit` 内部同步在分叉 rebase 上报「同步失败需解决冲突 本地<x> 远端<y> —— rebase 已自动回滚, 手动合流(解冲突)后重跑」, 且重叠文件肉眼可见全是生成物(`_index.md` 一类); 或手动走 generation 化解流程到 `rebase --continue` 被拒。
- **判别**: 失败行说「需解决冲突」但 `git ls-files -u` / `git diff --diff-filter=U` **为空** ⇒ 不是冲突没解, 是 continue 的前置条件没满足。现场签名: `git status --short` 里有 `MM <path>`(已暂存 + 又有未暂存修改)的白名单生成物 —— 它通常是 rebase 时**干净自动合并**(staged M)的那个, 被随后的 `gen_all.py` 重跑改了一两行(MM)。只 add 冲突集会漏掉它。
- **处置**: `git add -- <全部改动路径>`(精确列路径, 禁 `-A`; 至少覆盖所有 MM 白名单件)再 `GIT_EDITOR=true git rebase --continue`。脚本侧根因**已修**(2026-11-02, issue `26-11-01-2140`): `_resolve_rebase` 现在在 `_regen` 后把「白名单 ∩ 全部改动路径(含新增/删除/未跟踪, `_changed_paths()`)」与冲突集一并暂存, 收尾 amend 的 dirty 判定同款扩面 —— 本条手动配方保留给旧版脚本与其它调用方。
  **相邻坑**: [sync-pull.md](sync-pull.md)(生成物冲突的完整谱系与 stash 配方) · [history-integration.md](history-integration.md)(rebase 事故档案; 高风险整合前 `cp -a .git <仓库外备份>` 仍是好习惯 —— 本轮备份 30 秒可弃)。
- **复发**: 1 (2026-11-01, core/ W9b 收尾的远端合流: 37 笔本地提交 rebase 到新基 `6a390e76`, `my-commit-flow.sync` 两连败后由人工逐轮化解 8 次 —— 每次重跑生成器都把其它干净自动合并的白名单件改成 MM。本轮形态变了: **远端新基引入了新的生成物路径**(`plans/attachments/_archive.md` / `tasks/attachments/_archive.md`, 旧 tip `1aed1a33` 树里不存在 ⇒ 同一条 `--list` 在旧树 21 行 / rebase 中 23 行), 重跑的改动面比旧快照更大 ⇒ MM 态更多; 人工 8 轮里最后一轮落在 `plans/_index.md`。**为什么没命中**: 失败行没给冲突清单(`sync.py` 的 `conflict_line` 模板无路径位), 看起来像手写件冲突, 直到人工 `git merge-tree --write-tree --name-only` 探测才认出冲突面全是生成物 —— 识别冲突面这一步卡住, 坑档的处置(全量 add)本身是照做且有效的。自动化解根因疑点另立 issue `26-11-01-2140-bug-sync-generated-whitelist-drift`)。
