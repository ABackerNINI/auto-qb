# rebase 解冲突: R 编号撞车要顺延, 冲突替换串别在行尾截断

> 摘要: 与远端分叉后 `git rebase origin/develop`, 冲突几乎全落在「双方各追加一行」的档案进度日志、切片 R 行与生成物索引上 —— 追加行要**两边都留**(不是二选一), 撞号的 R 要**顺延**, 生成物**取一侧 + 重跑生成器**, 而用字符串替换解冲突时切记 `>>>>>>> <hash>` 后面还跟着**提交主题**, 只匹配到 hash 会把主题留在行尾变成脏值。
> 触发: rebase 冲突, 解冲突, R 编号撞车, 同号 R12, 最后活动 格式坏, 冲突标记残留, 追加行冲突, 生成物取一侧, 提交主题残留在行尾, git rebase --continue

**Refs:** memory-bank/pitfalls/git/_index.md

### 追加型冲突被当二选一: 两边的进度日志 / R 行都得留

- **触发**: 同一专题被多个 clone 并行推进(`26-10-20-2233` 这类滚动切片 + 7 个专题档案), 远端先落若干笔, 本地提交再 rebase → `memory-bank/tasks/*.md` 与切片尾部同一位置各追加了一行, git 判 content 冲突。
- **判别**: 冲突块两侧都是**完整独立的一行**(`- <stamp> <did>` 或 `**Rn(<stamp>):** <did>`), 不是同一句的不同改法; `git diff --name-only --diff-filter=U` 里 tasks/ 一连串文件同形态。
- **处置**: 两边都留、按时间先后排列(远端行在前, 本地行在后), 用一次正则批量解: `re.subn(r"<<<<<<< HEAD\n(.*?)\n?=======\n(.*?)>>>>>>> [^\n]*\n", ours.rstrip()+"\n\n"+theirs.strip("\n")+"\n", s, flags=re.S)`。**撞号的 R 必须顺延**: 双方都从「现有最大 + 1」取号, 撞了就把本地那条改成 `R(n+1)`, 否则切片里出现两条同号 R, 后续引用(R12 指哪条?)永远说不清。

### 替换串在 `>>>>>>> <hash>` 处截断, 把提交主题留在行尾

- **触发**: 手工/脚本解冲突时, 替换串写成 `... >>>>>>> 6b256797`(只到 hash), 而文件里那一行实际是 `>>>>>>> 6b256797 (♻️ <提交主题>)`。
- **判别**: 解完后该行尾部多出一段 `(<emoji> <提交主题>)`; 对 `> 最后活动:` 这种**严格格式**字段, 直接表现为 `test_kb_active_context_slices_are_valid` / `test_timekit_check_is_green_on_current_kb` 报「须严格 YYYY-MM-DD HH:MM, 现为 `2026-10-22 12:44 (♻️ …)`」。注意全套闸门在**提交时**是绿的(rebase 发生在提交之后), 不重跑全量就会带着脏值推上去。
- **处置**: 替换串覆盖整行 —— 用 `>>>>>>> [^\n]*\n` 这类正则吃掉行尾; 或替换后 `grep -n ">>>>>>>\|^=======\|<<<<<<<"` 外加对改动行做一次 `sed -n '<n>p'` 目视。rebase 完成后**必须重跑 `commands run test.full`**(合并引入了远端新用例, 数字会变), 再 `commands run my-commit-flow.verify-ref` 核 ref, 最后 `commands run ship.push`。

## 通用顺序: 生成物取一侧 → 重跑生成器 → 再 continue

- **触发**: `memory-bank/issues/_index.md`、`attachments/_archive.md` 这类「本文件是生成物」的件参与冲突(两侧的 Open/Done 计数与条目各不相同)。
- **判别**: 文件头写着「本文件是生成物, 不要手改」; 冲突块两侧都是整段索引内容。
- **处置**: `git checkout --ours <生成物>` 取任一侧 → `commands run kb.index` 重新生成 → `git add -A` → `GIT_EDITOR=true git rebase --continue`。**别在这里手工合并索引条目**(改完下次重跑又回来)。手写件(`tasks/`、`activeContext/`、`pitfalls/`)才需要上面的逐条判断。
- **守阵**: `commands run kb.index` 幂等重跑 + `commands run kb.check`(含新增面/回写/日期三道守卫); rebase 后跑 `test.full` 会连带跑 `test_memory_bank.py` 那一组。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
