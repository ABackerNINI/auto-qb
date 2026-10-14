# rebase --continue 前索引必须全暂存(git 2.55): 生成物自动化解只 add 冲突集会卡死

> 摘要: 分叉 rebase 撞生成物冲突, 走「取一侧 + 重跑生成器」自动化解时: 重跑会把**其它干净自动合并**的白名单生成物也改出未暂存修改(MM 态), 而脚本只 `git add` 冲突集(unmerged 那几个) —— `rebase --continue` 在 git 2.55 上对此报「You must edit all merge conflicts...」并拒绝, 回滚后对外的失败行仍是「需解决冲突…手动合流」, 误导性极强(其实没有任何未解冲突, `ls-files -u` 为空)。手动解: `git add` **全部**改动路径(至少所有 MM 白名单件)再 continue。2026-10-15 提交 4d268762 时实测两连败(ship.commit 内部 sync + 独立 sync 均因此失败行)。
> 触发: rebase, rebase --continue, 生成物自动化解, MM 状态, 未暂存修改, sync 失败行, 需解决冲突, git 2.55, 索引不干净

### 自动化解的最后一公里: add 的范围小于改动的范围

- **触发**: `my-commit-flow.sync` / `ship.commit` 内部同步在分叉 rebase 上报「同步失败需解决冲突 本地<x> 远端<y> —— rebase 已自动回滚, 手动合流(解冲突)后重跑」, 且重叠文件肉眼可见全是生成物(`_index.md` 一类); 或手动走 generation 化解流程到 `rebase --continue` 被拒。
- **判别**: 失败行说「需解决冲突」但 `git ls-files -u` / `git diff --diff-filter=U` **为空** ⇒ 不是冲突没解, 是 continue 的前置条件没满足。现场签名: `git status --short` 里有 `MM <path>`(已暂存 + 又有未暂存修改)的白名单生成物 —— 它通常是 rebase 时**干净自动合并**(staged M)的那个, 被随后的 `gen_all.py` 重跑改了一两行(MM)。只 add 冲突集会漏掉它。
- **处置**: `git add -- <全部改动路径>`(精确列路径, 禁 `-A`; 至少覆盖所有 MM 白名单件)再 `GIT_EDITOR=true git rebase --continue`。脚本侧的根因(未修, 属计划外): `_resolve_rebase` 在 `_regen` 后只 `git add` 冲突集, 没把重跑改动的其它白名单件一并暂存 —— 遇到同款失败行时按本条手动补 add 即可, 不必每次重跑脚本碰运气。
  **相邻坑**: [sync-pull.md](sync-pull.md)(生成物冲突的完整谱系与 stash 配方) · [history-integration.md](history-integration.md)(rebase 事故档案; 高风险整合前 `cp -a .git <仓库外备份>` 仍是好习惯 —— 本轮备份 30 秒可弃)。
