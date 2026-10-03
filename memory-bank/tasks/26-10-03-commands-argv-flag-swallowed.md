# 26-10-03-commands-argv-flag-swallowed — 修 `argv or []` 吃参数(闸门冒烟真跑动作)

**Status:** Done
**Added:** 2026-10-03
**Updated:** 2026-10-03 21:16
**Summary:** 清偿上一会话遗留观察:「`sync.py --help` 实际会真跑一次同步(`main()` 的 `parse_args(argv or [])` 让 CLI 的 `--help` 落空, `push.py` 同款更危险), 且它就在提交闸门的脚本冒烟里跑」。实测定性根因: `main(argv=None)` 把 CLI 直跑(`argv=None`)与测试裸调(显式 `[]`)混成 `argv or []`, CLI 时 `or []` 让 argparse 拿到空表 ⇒ `sys.argv[1:]` 里的 `--help` / 陌生旗标**全被吞**, 直落动作分支(`sync.py --help` 真同步、`push.py --help` 真推)。两处修: ①脚本侧判据改 `sys.argv[1:] if argv is None else argv`; ②闸门展开侧加 `|--with-safety`(`<each:GLOB|--flag>`), 拿 `<脚本> --safety` 探针问脚本本人, "无参即真动作"即摘掉(摘掉数量打印)。守阵 `test_pipeline.SmokeSafetyTest` + `test_sync` 三条新用例。新坑档 `pitfalls/testing/gate-probe-must-not-run-action.md`。
**Topics:** commands-shipflow-argv-entry
**Refs:** memory-bank/pitfalls/testing/gate-probe-must-not-run-action.md, memory-bank/testing/baselines/26-10-03-2116-commands-argv-flag-swallowed.md

> 背景关联(不进机器认领链): 遗留观察出自 tasks/26-10-03-commands-sync-generated-autoresolve.md 的「遗留观察」条; 本任务是用户的直接修复指令(非 issue 清偿路线图)。

## 原始请求

用户引述另一会话报告:「一个既有隐患(未改, 仅报告): `sync.py --help` 实际会真跑一次同步 —— `main()` 里 `parse_args(argv or [])` 让 CLI 的 `--help` 落空(push.py 同款, 那个更危险)。它就在提交闸门的脚本冒烟里跑。」指令: **修复**。

## 思考过程与决策

- **根因定性(2026-10-03 21:0x, 实测定性)**: 报告里"`--help` 落空"是**表象**, 真形态更宽 —— **任何陌生参数都会被吞**。`main(argv=None)` 里 `parse_args(argv or [])` 把两种调用方混成一个:
  - CLI 直跑 → `argv=None` → `or []` 给 argparse 空表 ⇒ `sys.argv[1:]` 整个被丢, `--help`/`--safety`/`--bogus` 一律当"无参"落动作分支;
  - 测试裸调 `main()` → 同样走 `argv or []` ⇒ 也正是这个原因让测试看不到 CLI 行为差异。
  - 实测铁证: `sync.py --help` → `已同步 70bfc383`; `push.py --help` → `推送成功 70bfc383`(**真的推了一次**)。
- **对照归因(为什么只有这两个漏)**: `commit.py` / `run.py` / `gen_all.py` 一直写 `parse_args(argv)`(直接吃 `None` 语义)⇒ 陌生旗标正常 `error: unrecognized arguments` + Exit 2。同包同形状脚本行为不一致 = 这一处漏改, 而不是全仓库性问题。
- **修法一(脚本侧)**: 判据写成 `sys.argv[1:] if argv is None else argv` —— `None` 才回退 `sys.argv`(CLI), 显式 `[]` 仍是测试的动作入口, 两个入口各留语义。
  - ⚠ **连带必改**: 改完裸调 `main()` 会去读 **pytest 自己的 `sys.argv`**(用例名 / `-q` / `-k` 都被 argparse 拒)⇒ 既有"测动作"的用例(`test_main_prints_one_line_contract`)必须显式传 `[]`。首次实跑即撞 `pytest: error: unrecognized arguments: .commands/...test_sync.py -q -n 0`。
- **修法二(闸门侧, 报告没提但不可或缺)**: 光修脚本不够 —— 下一个写"无参即真动作"的人还会再踩, 且静默。展开侧新增 `|--with-safety`: 探针 `<脚本> --safety`, 答 `action-without-args` 即摘掉。
  - **判据按探针内容而非文件名规则**: 文件名规则会在下次改名时静默失效(与仓库既有"集合单点"原则一致)。
  - 声明处放**脚本自己**(`gen_all.py` 的 `PARAMETERLESS_ACTION_GENERATORS`), 不在 `_pipeline` 抄一张危险文件名清单 —— 只有脚本知道自己无参干什么。
- **附带发现**: `gen_all.py` 无参 = 重建全部生成物(写文件), 本就不该靠 `--help` 探活 ⇒ 一并声明 `action-without-args`。
- **探针实现坑**: `subprocess` 必须钉 `stdin=DEVNULL` —— 父进程是 pytest 时 stdin 是被捕获管道, 子进程继承后挂到 10s 超时(实测整轮卡死)。

## 实现计划

- 脚本侧: `sync.py` / `push.py` 改判据 + 加 `--safety` 探针分支。
- 闸门侧: `_pipeline.py` 的 `EACH_RE` 认 `<each:GLOB|--flag>`、新增 `_safe_files()` 探针分拣、全摘时返回 skip(不静默降级成空展开); 两处 docstring 说明。
- 配置: `.my-commit-flow.toml` 两条 `--help` run 加 `|--with-safety` + 占位符说明块; `references/config.md` 补语义节。
- 声明: `gen_all.py` 加 `PARAMETERLESS_ACTION_GENERATORS` 常量 + `--safety` 分支(在任何动作之前, 只答常量)。
- 守阵: `test_pipeline.SmokeSafetyTest`(配置守卫 / EACH_RE / 探针分拣 / 全摘 skip / 超时按不安全) + `test_sync` 三条新用例。
- 验证: 逐一验 `--help` 不动 HEAD、陌生旗标 Exit 2、探针答案; 跑 test.pkg。
- 收尾: 坑档 + `kb.index` + 基线切片 + 本档案。

## 子任务状态表

| 子任务 | 状态 | 备注 |
|---|---|---|
| 根因定性(实测复现) | ✅ 完成 | `sync.py --help` / `push.py --help` 真跑动作复现; 对照三脚本行为不一致定位漏改点 |
| 脚本侧修判据 + 探针 | ✅ 完成 | `sync.py` / `push.py`: `sys.argv[1:] if argv is None else argv` + `--safety` 分支 |
| 闸门侧 `\|--with-safety` 过滤 | ✅ 完成 | `_pipeline.EACH_RE` + `_safe_files()`(探针钉 stdin=DEVNULL) |
| 声明 action-without-args | ✅ 完成 | sync.py / push.py / gen_all.py(`PARAMETERLESS_ACTION_GENERATORS`) |
| 配置 + references 回写 | ✅ 完成 | `.my-commit-flow.toml` 两条 run + 占位符说明; `references/config.md` 语义节 |
| 守阵用例 | ✅ 完成 | `test_pipeline.SmokeSafetyTest` 4 条 + `test_sync` 3 条 |
| 验证 | ✅ 完成 | `--help` 不动 HEAD / `--bogus` Exit 2 / 探针三答; test.pkg 96 passed(`-n 4`) |
| 坑档 + kb.index | ✅ 完成 | `pitfalls/testing/gate-probe-must-not-run-action.md` + `_index` 重生; `parallel-run.md` 反写 `-n 0` 挂死节 |
| 连带修 `test.pkg` 闸门 `-n 0` 挂死 | ✅ 完成 | 卡在提交路径上(提交无输出即中止); 改 `-n 4`, 闸门 108.9s 通过 |
| 基线切片 | ✅ 完成 | test.full 2415 passed + 3 skipped / 99%(@ fa5cc5ed, 45.3s) |
| 提交(ship.commit) | ✅ 完成 | 见进度日志末条 |

## 进度日志

- **2026-10-03 21:16** 收口。开工 `my-commit-flow.sync` 首跑撞「拿不到远端 tip 的对象」(瞬时态, 脚本自带"重跑") → 重跑 `同步成功 fa5cc5ed`(远端连推 `7ca46436` / `fa5cc5ed` 两笔, 快进落地, 改动全数存活)。新基线上: `gen_all.py` 重建 20 生成物、`--check` 绿、`check_doc_links` / `check_context_caps` / `check_command_drift` 全绿; `test.full` **2415 passed + 3 skipped / 99%**(14,395 语句 / 131 未覆盖 / 4,810 分支, 45.3s, rc=0); `test.pkg` **96 passed**(`-n 4`)。改动 9 文件 + 新坑档 1 + 新基线切片 1 + 本档案。基线切片 `testing/baselines/26-10-03-2116-argv-flag-swallowed.md`。
- **2026-10-03 21:2x** 连带修复(**提交路径阻断, 原被判为"仅观察"**): `ship.commit` 首跑**无输出即中止** —— 定位到 `test.pkg` 闸门(`.commands/test/config.toml`)写 `-n 0`(串行), 而 `test_sync.py` 的真实 git 临时仓库用例串行到第 15 个后**挂死**, 拖垮整个闸门(闸门 `timeout=300` 兜不住"不退出")。取 `git show HEAD:.../test_sync.py` 原版单跑**同样挂** ⇒ 与本次改动无关(存量)。处置: `test.pkg` 改 `-n 4`, 实测闸门 108.9s 通过(96 passed); 坑条 `pitfalls/testing/parallel-run.md` 新增「⚠ `-n 0` 对真实仓库用例会挂住」节(含"提交无输出即中止"这个最易误读的症状)。根因未定位到具体用例, 留给 issue。
- **2026-10-03 21:0x** 修复 + 验证。定性见「思考过程」; 端到端实测: `sync.py --help` → usage rc=0 且 **HEAD 不动**; `push.py --bogus` → Exit 2(不再推); 探针 `sync.py` / `push.py` / `gen_all.py` 三答 `action-without-args`; 闸门展开实测摘掉 sync/push/gen_all、只冒烟 `_pipeline` / `commit` / `test_*` / `verify_ref`。
- **2026-10-03 21:0x** 环境观察(当时**未改**): `test.pkg` / `test_sync` 包内配置写 `-n 0`(串行), 本会话实测串行在 15 个用例后**挂住**; 取 HEAD 原版 `test_sync.py` 对照**同样挂** ⇒ 存量问题。当时记「待另立 issue」, 后证实它**卡在提交路径上**, 遂于 21:2x 直接修复(见上条)。
