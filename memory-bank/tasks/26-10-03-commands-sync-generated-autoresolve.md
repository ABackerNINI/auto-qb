# 26-10-03-commands-sync-generated-autoresolve — 同步时自动化解生成物索引冲突 (计划 26-10-03-1544 实施)

**Status:** Done
**Added:** 2026-10-03
**Updated:** 2026-10-03 16:16
**Summary:** 实施计划 memory-bank/plans/26-10-03-1544(本期范围 S1 + S2)。把「多 clone 收尾都重跑生成器 → 同一批 `_index.md` 两边各自新版本 → 后同步者必撞」这一最热冲突源, 从人肉解冲突改成脚本三步自动化解: ①新增 `gen_all.py` 作**生成物集合单点**(无参重建 / `--list` 白名单 / `--check` 自证), `kb.index` / `kb.check` 各由四条收成一条; ②配置三键 `auto_resolve_generated` / `generated_list_cmd` / `generated_regen_cmd`(默认开, 加进 `KEY_DEFAULTS` + 类型校验 STOP); ③`run_sync()` 单点上落「白名单 → 任取一侧 + 重跑 → `--check` 自证」—— 快进被拒(落后+脏重叠)与 rebase 冲突(有界循环)两条分支, 生成物冲突零人工, 手写冲突行为逐字不变; 任一前提取不到即退回现状失败行且仓库状态与跑之前一致。S3(分叉+树脏)按计划延后。
**Topics:** commands-sync-generated-autoresolve
**Refs:** memory-bank/plans/26-10-03-1544-plan-sync-generated-index-autoresolve.html

## 原始请求

用户指令: 「先同步远端, 然后实施计划 `26-10-03-1544-plan-sync-generated-index-autoresolve.html`」。计划本体: 多 clone 并行下 `my-commit-flow.sync` 见冲突就停, 执行者被叫去手工合流(陷阱档 `pitfalls/git/sync-pull.md` 的「提交点撞远端前移」条目已复发 7 次, 其中多数重叠文件是生成物索引); 目标是把「生成物冲突零人工、手写冲突零变化、不新增第二处集合定义」落在一个单点上。范围 = S1(落后 + 本地脏与远端改动重叠)+ S2(分叉 + rebase 冲突), S3(分叉 + 树脏)明确不做。

## 思考过程与决策

- **单点选择**: `run_sync()` 是 `sync` / `ship.commit`(内部同步)/ `ship.push`(推送前同步)三条入口共用的唯一函数 —— 改一处三条受益, 不存在「改了 sync 但 commit 还是老行为」的分叉。
- **生成物集合单点 = `gen_all.py`**(不是 sync 里手抄一份清单): 四个生成器(`gen_tasks_index` / `gen_kb_index` / `gen_docs_index` / create-issue 的 `gen_issues_index`)的集合声明收在一处, `--list` 与真正写出的集合**构造上恒等**(同一 `collect()` 实现), 否则白名单多一个其实不是生成物的路径就会在冲突时静默丢手写内容。
- **跨 skill 载入的 `_common` 同名冲突**: memory-bank 与 create-issue 各有一份 `_common.py`, 同进程 import 会串味 —— `gen_all.py` 用 `_load_isolated()`(载入前 pop `sys.modules["_common"]`、载入后还原)解决, 不引入第二处集合定义。
- **三步不变量(白名单 → 重跑 → 自证)**: 不做文本合并、不做行级并集(否决 `-X ours/theirs` 与 `merge=union`, 见计划 §08)。敢默认开的理由 = 生成器是纯函数, 重跑后 `--check` 通过 ⇒ 文件确实等于生成结果 ⇒ 证明没有手写内容被丢弃。
- **只碰「被修改」的路径**: `git diff --diff-filter=M`(工作区 + 暂存两路)取本地被修改文件, 排除新增 / 删除 / 改名 / 未跟踪 —— 那几类属异常状态, 直接退回失败支, 不猜意图。
- **失败后仓库状态与跑之前一致**(沿用「写状态的命令必须比只读的更干净地失败」): S2 天然满足(rebase 前树净, `--abort` / `reset --hard` 即回滚); S1 树脏, 用 `_snapshot_dirty()` 存被跟踪脏文件字节 + `_restore()` 回滚。S1 另加**预检 `--check`**(改动前先确认生成器健康且当前生成物自洽)—— 这就是「自证红」子情形能在**不动任何东西**的前提下被拦下的原因。
- **收尾再自证 + amend**: 多提交重放时中间那次重跑基于「部分重放」的树, 故 rebase 完成后重跑一次; 仍漂移则 `commit --amend --no-edit` 折进 tip(rebase 后的 tip 是未推送的本地提交, amend 安全)。
- **配置类型校验按 STOP**: 三个新键写错(如 `auto_resolve_generated = 1`)会让化解路径行为异常, 与 `timeout` 同级停手(既有的 `config_problems` 白名单机制)。
- **顺手发现并修的两处计划外耦合**: ①`kb.index` 由四条收成一条后, 引擎自证压缩用例(`test_engine.py::test_run_selfcheck_compressed`)借用 `kb.index` 当「多命令 task」失效 → 改用 `kb.check` 并**动态算条数**(不再写死 4); ②`test_memory_bank.py` 的 `gen_cmd` 守卫按「脚本必须在 `kb.index` run 列表里」判定, 收编后需认可 `gen_all.GENERATORS` 这条间接覆盖。

## 实现计划

1. `gen_all.py`(新)+ 单测; `kb.index` / `kb.check` 改调它, 跑 `kb.check` 确认绿。
2. 配置三键 + `KEY_DEFAULTS` + 类型校验; `_pipeline.py --show-config` 确认键生效。
3. S1 重叠自动化解 + `test_sync.py` 场景 1/2。
4. S2 rebase 有界循环 + 收尾自证 + 场景 3/4/5/6。
5. 文档回写(`references/pipeline.md` / 陷阱 / 协作约定 / 包 config.toml note)、`kb.index`、`test.full`、新建基线切片。

## 子任务状态表

| 子任务 | 状态 | 备注 |
|---|---|---|
| gen_all.py(重建 / --list / --check) + kb 两任务收编 | ✅ 完成 | `--list` 20 条路径 == 库内全部 `_index.md`; `--check` 绿; `kb.check` 绿 |
| 配置三键 + `KEY_DEFAULTS` + 类型校验 STOP | ✅ 完成 | `_pipeline.py --show-config` 三键生效; test_pipeline 补 3 用例 |
| S1 落后 + 脏重叠自动化解(预检 + 快照回滚) | ✅ 完成 | test_sync 场景 1/2 + 白名单取不到 / 重跑失败 / 自证红 三子情形 |
| S2 rebase 有界循环 + 收尾自证 + amend | ✅ 完成 | test_sync 场景 3/4/6(线性 / 手写回滚 / 幂等) |
| 引擎自证压缩用例改用 kb.check(计划外耦合) | ✅ 完成 | test_engine 17 passed |
| gen_cmd 守卫认可 gen_all 间接覆盖 | ✅ 完成 | test_memory_bank 31 passed |
| 文档回写(pipeline.md / sync-pull.md / collaboration.md / 包 note) | ✅ 完成 | doc-links / caps / drift 三闸门全绿 |
| `kb.index` + `test.full` + 基线切片 | ✅ 完成 | 数字见下 |

## 进度日志

- **2026-10-03 15:51** 开工同步成功 `7ef83e63`; 读计划 + 现场代码(`sync.py` / `_ship_config.py` / `_pipeline.py` / 四个生成器 / `kb` 包配置 / `test_sync.py` / `test_memory_bank.py`)。确认 `run_sync()` 是三条入口单点、四个生成器均为纯函数、库内 20 个 `_index.md` 全部由四生成器产出。
- **2026-10-03 16:0x** 落 `gen_all.py`(GENERATORS 单点 + `_load_isolated` 解决跨 skill `_common` 同名冲突); `_common.GEN_CMD_BY_SCRIPT` 加 `gen_all.py` 条; `kb.index` / `kb.check` 各收成一条。实测 `--list` 20 条 == `find memory-bank -name _index.md`; `--check` rc=0; `kb.check` 绿。
- **2026-10-03 16:0x** 配置三键 + `GENERATED_KEY_TYPES` 类型校验; `.my-commit-flow.toml` 加三键与注释(「列错 = 静默丢内容」); `--show-config` 确认生效; test_pipeline 补 3 用例。
- **2026-10-03 16:0x** `sync.py` 落自动化解: `_whitelist` / `_regen` / `_self_check` / `_modified_paths` / `_remote_changed` / `_in_head` / `_snapshot_dirty` / `_restore` / `_resolve_behind_overlap` / `_resolve_rebase`; `run_sync()` 两条分支接入。test_sync 12 → 20 用例(新增 8 条)全绿; test.pkg 首次跑出 1 红(引擎自证压缩用例), 改用 `kb.check` + 动态条数后 test.pkg **88 passed**(196s, 3m16s)。
- **2026-10-03 16:1x** 文档回写: `references/pipeline.md`(行为表 + 「生成物冲突自动化解」新段 + 脚本表)、`pitfalls/git/sync-pull.md`(处置段改「先看是否全在生成物上」+ 机制修复成因)、`conventions/collaboration.md`(同步口径补一句)、`.commands/my-commit-flow/config.toml` 的 sync note。`kb.check` / `check_doc_links` / `check_context_caps` / `check_command_drift` 全绿。
- **2026-10-03 16:1x** `test.full` 首跑 1 红 = `test_no_ghost_pkg_dirs`(本 clone 历史残壳 `core/mixins` / `mixins` / `web` / `web/routes`, 与本轮改动无关), 按陷阱档 `pitfalls/testing/ghost-pkg-residue.md` 处方整目录删除即绿, 该条 `复发` +1。
- **2026-10-03 16:2x** 收尾: 立本档案 + activeContext 切片 + 计划 doc-status→Done(+ doc-refs 回指本档案), `kb.index` 重建, `test.full` 复跑 **2411 passed + 3 skipped / 99%**, 新建基线切片。
- **2026-10-03 20:1x** 收到「提交」→ 按口径先合并远端: sync 首跑撞「树脏挡路」(远端已连推 4 笔至 `181d90c3`), 重叠**仅手写件** `pitfalls/git/sync-pull.md` —— 新机制正确地未动作(保守默认首次真机验证), 照行内配方 `cp -a .git <备份>` → `stash push -u` → sync(`同步成功 181d90c3`) → `pop` **零冲突**(两边改动落在不同段)。新基线上 `kb.index` 重建 + `kb.check` 绿 + `test.full` **2413 passed + 3 skipped / 99%**(14,395 语句 / 131 未覆盖 / 4,810 分支 / 104 partial, 40.8s; +3 本任务守阵 +2 合流远端), 基线切片随之改为 `26-10-03-2014`(文件名对齐实测时间); `pitfalls/git/sync-pull.md` 补一条复发登记(含新机制真机验证说明)。
