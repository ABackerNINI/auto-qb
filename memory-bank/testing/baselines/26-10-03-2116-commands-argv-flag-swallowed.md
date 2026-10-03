# 基线 · 2415 passed + 3 skipped / 99% —— 修 `argv or []` 吃参数(冒烟闸门不再真跑动作)

> 摘要: 修一个既有隐患 —— `main(argv=None)` 里 `parse_args(argv or [])` 把 CLI 直跑(`argv=None`)
> 与测试裸调(显式 `[]`)混成一个, `or []` 让 argparse 拿到空表 ⇒ `sys.argv[1:]` 里的 `--help` /
> 陌生旗标**全被吞**, 直接落到动作分支。实测 `sync.py --help` 真同步一次、`push.py --help` 真推一次,
> 而它就在提交闸门的脚本冒烟里跑。两处修: ①脚本侧判据改 `sys.argv[1:] if argv is None else argv`;
> ②闸门展开侧加 `|--with-safety`(`<each:GLOB|--flag>`), 拿 `<脚本> --safety` 探针问脚本本人,
> "无参即真动作"即摘掉(摘掉数量打印)。守阵 `test_pipeline.SmokeSafetyTest` + `test_sync` 三条新用例。
> 新坑档 `pitfalls/testing/gate-probe-must-not-run-action.md`(含附带发现: 探针 subprocess 必须钉 stdin=DEVNULL)。
> 基线时间: 2026-10-03 21:16, develop @ fa5cc5ed + 工作区(本轮回写件未提交)。
> 开工 sync 首跑撞「拿不到远端 tip 的对象」瞬时态, 重跑即 `同步成功 fa5cc5ed`(远端已连推两笔)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。

**Refs:** memory-bank/tasks/26-10-03-commands-argv-flag-swallowed.md

TOTAL **2415 passed + 3 skipped / 99%**(14,395 语句 / 131 未覆盖 / 4,810 分支 / 104 partial,
test.full 45.3s, rc=0)。
相对上一切片(26-10-03-2106: 2415 passed + 3 skipped / 99%, 14,395 语句 / 130 未覆盖 / 4,810 分支,
@ 7ca46436) **passed 持平** —— 本单净变化: 新增守卫用例 4 条
(`test_pipeline` SmokeSafetyTest 4 条 + `test_sync` 3 条新用例, 但后者在 `tests/` 之外, 不计入本 TOTAL);
`.commands` 包内测试另跑 `test.pkg` **96 passed**(`-n 4`, ~105s)—— 相对上轮 88 条 **+8**
(SmokeSafetyTest 4 条 + test_sync 3 条 + 1 条随 `--safety` 分支可达性产生的用例变化)。
语句/分支数持平; 未覆盖 130→131 为远端合流(fa5cc5ed / 7ca46436 两笔)与本单净变化之和, 未逐文件归因。

## ⚠ 连带修复: `test.pkg` 闸门 `-n 0` 串行挂死(卡在本单提交路径上)

原以为只是"环境观察", 提交时才发现它是**真阻断**: `.commands/test/config.toml` 的 `test.pkg` 写
`-n 0`(串行), 而 `test_sync.py` 那批真实 git 临时仓库用例串行跑到第 **15** 个后**挂死**(不报错、
不退出), 把 `ship.commit` 整个闸门拖垮 —— 症状是**提交无任何输出即中止**。
取 `git show HEAD:.../test_sync.py` 原版单跑**同样挂** ⇒ 与本次改动无关(存量)。
**处置**: `test.pkg` 改 `-n 4`(实测 96 passed / 108.9s, 在 300s 闸门超时内收口);
坑条反写 `pitfalls/testing/parallel-run.md`(新增「⚠ `-n 0` 对真实仓库用例会挂住」节)。
根因未定位到具体用例(留给 issue), 但"换 -n 4 即过"是可靠解法。
