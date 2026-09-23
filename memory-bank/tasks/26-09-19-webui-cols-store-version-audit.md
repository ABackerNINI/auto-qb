# 26-09-19-webui-cols-store-version-audit — WEB UI 列状态存储键 `autoqb_cols_v?` 版本沿革审计与口径回写

**Status:** Done (已入库 `ccedce8` + `8d68300`; GitHub 镜像滞后 1 个提交, 等网络恢复补推)
**Started:** 2026-09-19
**Owner:** 主线 (单会话连续实施)
**Plan doc:** 无 (本次为只读审计 + 知识库回写, 未出计划文档)
**Legacy-ID:** 无
**Summary:** 用 `git log -S` 逐键追溯列状态存储键的 4 次升版本(v1→v4, 集中在 2026-09-13 08:32 ~ 09-14 07:25), 确认 v4 之后 R10-09(`cb57bef`)已把政策反转为"列集变更一律不升版本"; 据此回写 `pitfalls.md`(2 处) / `systemPatterns.md` / `activeContext.md` 三条仍写着"加/减列**必须**升版本"的旧口径, 并补一条"不并发也会偶发的全量失败"判别法; 测试基线 1041 passed 不变。
**Topics:** webui-cols-store-version

## 原始请求

> 分析WEBUI的autoqb_cols_v?版本迭代时间表

随后用户下令「改」(按代码为准回写漂移文档) 与「提交」(commit + 双远端推送)。

## 思考过程与决策

- **不能只读当前文件的注释**: 键名换过两次(`autoqb_colwidths_v1/v2` → `autoqb_cols_v3/v4`), 且 **v2 的"稀疏覆盖"只活在注释与提交信息里** —— 只读 `shared/app.js` 会把它当成"从来没有过"。故用 pickaxe 逐键追溯:
  ```bash
  git log --oneline --all --date=short -S "autoqb_colwidths" -- src resources   # v1 / v2
  git log --oneline --all --date=short -S "autoqb_cols_v3"   -- src resources   # v3 / v4 / 迁移
  ```
  再对候选提交逐个 `git show <c>:<path>` 取当时的 `COLS_STORE_KEY` 与注释, 交叉验证结构形态。
- **四次升版本的性质并不相同** —— 这是本次分析最有用的结论:
  | 版本 | 变更性质 | 是否"列集变更" |
  |---|---|---|
  | v1 → v2 | 存储结构(整表 px 数组 → 稀疏覆盖 `{page:{列索引:px}}`) | 否 |
  | v2 → v3 | 键改名 + 改按**列 key** 存 `{widths,hidden,manual}` | 否(为支持隐藏列) |
  | v3 → v4 | 新增 H&R / 分享率两列 | **是(唯一一次)** |
  即历史上**只有一次**是"因为加列而升版本", 而且这一次后来被判定为错误决策。
- **分水岭是 R10-09(`cb57bef`, 2026-09-17 13:09)**: 宽/隐/序都按列 key 存之后, 新增列在旧缓存里只是"没有记录"(回退 `tpl` 默认宽), 已删列的残留 px 由 `loadColState()` 按当前列 key 求交集洗净 —— 都不会错配; **升版本反而会把用户手调的宽/隐/序清零**, 那才是"列宽时不时被重置"的机制性来源。此后 09-15 新增 show 页 / 09-16 明细表补 8 列 / 09-16 加 `order` / 09-17 保存路径列迁移, **四次都没升版本**。
- **决策 1(文档漂移)**: 按 AGENTS.md 的"代码 > memory-bank"裁决回写, **不动 `memory-bank/plans/` 的历史计划** —— 那份 v3 计划里"重排列集则升 v4→v5"是当时口径的存档, 只在 `activeContext.md` 标注"别照抄"。
- **决策 2(提交顺序)**: 落后主线 6 个提交且工作区脏 ⇒ **先 commit 再 `git pull --rebase`**, 而不是先 pull —— 后者在脏工作区会触发 stash, 撞上本环境"删除拦截层顺着 stash 写入删掉 `.git/objects`"的重大事故坑(见 pitfalls 同名条目)。
- **决策 3(偶发失败不立新坑)**: 首跑全量冒出的 2 条失败复跑即绿, 且**期间没有并发 pytest** ⇒ 属于既有条目「不要并发跑多个 pytest 进程」同一机制(副作用台账越界判定是会话级、拦截层清理它进程遗留 `*.tmp` 也会记进来)的**第二种触发**, 扩展该条目的判别法即可, 不另起一节。

## 实现计划

1. 追溯 `autoqb_cols_v?` 全部分支的引入/改名提交, 产出时间表与每次升版本的触发原因 (只读)
2. 回写 3 处旧口径(`pitfalls.md:115` / `pitfalls.md:227` / `systemPatterns.md:123`) + `activeContext.md` 口径说明
3. commit + rebase + 双远端推送
4. 补"不并发也会偶发全量失败"判别法并提交
5. 立档 + 重建 `tasks/_index.md`

## 子任务状态表

| # | 子任务 | 状态 | 产出 / 提交 |
|---|---|---|---|
| 1 | 版本沿革追溯 (git pickaxe, 只读) | ✅ | 时间表: v1 `88508a0` / v2 `8af6dbc` / v3 `2c45761` / v4 `479f52c` |
| 2 | 旧口径回写 (3 处 + activeContext) | ✅ | `ccedce8`: `memory-bank/{pitfalls,systemPatterns,activeContext}.md` |
| 3 | 提交 + 双远端推送 | ✅ | Gitee `7391b63..ccedce8`; GitHub `b646759..ccedce8` (当时成功) |
| 4 | 补偶发失败判别法 | ✅ | `8d68300`: `memory-bank/pitfalls.md` |
| 5 | 立档 + 索引重建 | ✅ | 本档案 + `scripts/gen_tasks_index.py` |

## 进度日志

- **12:40** 收到"分析版本迭代时间表"; 用 `git log -S` 逐键追溯, 确认 4 次升版本与 R10-09 反转点, 输出时间表(可视化两张: 升迁轴 + v4 后事件轴)。
- **12:46** 用户「改」: 回写 `pitfalls.md:115`(整条反转, 补"只有旧缓存结构无法被 `loadColState()` 解释才升版本"判据 + 4 次未升版本的实证)、`pitfalls.md:227`(去掉 R08 时期"重排列集必须升版本")、`systemPatterns.md:123`(结构补齐 `order` 并删掉错误因果)、`activeContext.md`(口径统一说明)。`tests/test_memory_bank.py` 8 passed。
- **13:10** 用户「提交」: `git fetch` 发现落后 6 个提交(`7391b63` 等, 其中含 `memory-bank/pitfalls.md` 与 `testing.md` 的改动) ⇒ 先 commit(`f3cfe91`)再 `git pull --rebase` 无冲突(rebase 后 `ccedce8`) ⇒ 推 Gitee `7391b63..ccedce8` ✅; 补 `github` 远端后禁用 per-URL 代理直连推 GitHub `b646759..ccedce8` ✅。
- **13:20** 首跑全量的 2 条失败经复跑证伪(1041 全绿), 扩展 `pitfalls.md` 既有条目 ⇒ `8d68300`; Gitee 推送首次 `Recv failure` 重试成功(`ccedce8..8d68300`); **GitHub 本次不可用**(直连超时 21s, 代理 127.0.0.1:10808 亦连不上), 按规矩不重试, 镜像滞后 `8d68300`。
- **13:25** 立档本档案并重建 `tasks/_index.md`。

## 遗留

- GitHub 镜像滞后 1 个提交 `8d68300`(镜像允许滞后, 交付以 Gitee 为准); 网络恢复后补推 `git -c http.https://github.com.proxy= push github develop` 即可。
- `memory-bank/plans/26-09-15-1042-webui-optimization-plan-v3.html` 内"重排列集则升 v4→v5"为当时口径, 存档未改动 —— 后续若有人照抄会误升版本, 已在 `activeContext.md` 标注。
