# 26-11-13-test-real-seed-clean-evidence-guard — real.seed.clean 证据保护闸(issue 26-11-12-2345)

**Status:** In Progress
**Added:** 2026-11-13
**Updated:** 2026-11-13
**Summary:** real.seed.clean 证据保护闸(issue 26-11-12-2345)
**Topics:** test-real-seed-clean-evidence-guard
**Refs:** memory-bank/testing/baselines/26-11-13-0232-test-real-seed-clean-evidence-guard.md

## 本篇只回答

「real.seed.clean 整清 tests-real/.work 连带删测量证据」这个缺口是怎么修的: 守卫语义(白名单+拒跑)取什么形、为什么不用 issue §03 的两个原建议、逃生门怎么留, 以及 `_allowed` 白名单的兄弟目录误收是怎么被评审抓出来又怎么修的。

## 原始请求

1. 用户: 「修复 memory-bank/issues/26-11-12-2345-chore-real-seed-clean-evidence-guard.html」—— 即认领该 issue 并修复: real.seed.clean 的旧契约是整目录清空 tests-real/.work 与 R:/qbt-fake, 对 .work 内测量证据(results JSON/复用脚本)无检测即拒跑的保护; 2026-11-12 S5 复评收尾实测证据全树丢失(gitignored, 不可恢复)。issue §03 给了两个可选方向(证据形状检测拒跑 / 收窄清扫范围), 「取其一即可, 方向待接手者定」。

## 思考过程与决策

- **不取形状检测**: issue §03 建议的 `results*/`、`*.json` 形状抓不住脚本证据目录 —— 本 clone `.work` 里现存的 `reconcile-e2e/`、`relocate-rlfn-e2e/`、`tools-daemon-wrapper/`(2026-11-12 事故里丢的 inject/m1/m2/m3 复用脚本同理)都不带证据形状; 形状清单永远追不全。
- **不取纯收窄**: 只清 `.work/seeds` 会让「收尾清场」契约残缺 —— 用例工作目录(rm01~rm10, 含用例落的种子数据)是 clean 的合法清扫面, 收窄后没人清。
- **拍板(合流)**: 白名单 + 拒跑 —— clean 默认整扫与 `--dir` 指 `.work` 本体时, `.work` 顶层凡不是 `seeds/`(seed.py 自造落点)或 `rm\d+`(用例目录)的内容一律 rc=1 拒跑(dry-run 同拒, 删除动作零发生), 逐项列出未知内容并带 issue 指称; `--dir` 显式指名子树是唯一清法(每次一处), **不提供一键全清逃生门**(与 real.guard「没有 --force 逃生门」同哲学)。认得的名字契约不变。
- **R:/qbt-fake 不设闸**: 内存盘重启即清空、只被 seed.py/用例写入, 证据不会存那里。
- **评审轮1修正**(reviewer 发现, 引文过检): `_allowed` 裸字符串前缀匹配会把 `.work-20261112` 这类**兄弟目录**误收为合法落点 —— `--dir` 指过去即整树清且绕过证据闸。修法: 白名单改按路径分量严格包含(`p == r or r in p.parents`), 补守阵钉死。

## 实现计划

1. `tests-real/seed.py`: 抽 `WORK_ROOT` 常量; 加 `CLEAN_KNOWN_WORK` 白名单正则与 `_work_strays`; `cmd_clean` 开头设证据保护闸(默认整扫与 --dir 指 .work 本体同闸, rc=1 拒跑先行于一切删除); 模块 docstring 安全边界与 clean --help 同步口径。
2. `_allowed` 改严格包含(评审轮1)。
3. `tests/test_real_machine_safety.py`: 新增 seed clean 节守阵(隔离加载 seed.py, 落点全改指 tmp —— 真实 .work 本身是被保护对象)。
4. 回写四处口径: `.commands/real/config.toml`(real.seed.clean when/note)、`pitfalls/ops/seed-clean-vs-evidence.md`(处置行: 闸已落地, rmNN 内与 --dir 指名面仍靠人工)、`testing/real-machine.md`(收尾行)、`tests-real/tools/daemon_window_wrapper.py`(「clean 可清」过时措辞, 评审轮1)。
5. issue 翻 In Progress → Done(kb.status 两处翻转), §03 补「修复后补充」(实际修法/改道理由/验证数字)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | seed.py 证据保护闸 + 口径同步 | Done(2026-11-13) |
| 2 | _allowed 严格包含(评审轮1) | Done(2026-11-13) |
| 3 | 守阵 4 条(拒跑/契约不变/逃生门/兄弟目录) | Done(2026-11-13) |
| 4 | 四处口径回写 | Done(2026-11-13) |
| 5 | issue 状态机 In Progress → Done + 修复后补充 | Done(2026-11-13) |
| 6 | 分批评审(全能档, 2 轮) + test.full 基线切片 | Done(2026-11-13) |

## 进度日志

### R0 · 立档 (2026-11-13)

- 同步开工(快进 e1fbd849→68bc89ac, 复评前置再快进 68bc89ac→69093e1a→ce304959)。
- 主实现落地: 守闸 + 守阵 3 条; test.one 守阵文件全绿(13 既有 + 3 新增), test.quick 全量绿(实测数字见基线切片 26-11-13-0232)。
- issue 状态机走齐(In Progress → Done, 修复后补充落 §03)。
- 评审轮1(全能档, 151 行, 引文检 2/2 过): minor `_allowed` 兄弟目录误收(已修 + 补守阵)与 nit wrapper docstring 过时措辞(已修)。
- 评审轮2(182 行, 基哈希 0b872675942a, 锚点 ce304959): 轮1两条处置核验落地未回退; 新发现 1 条 minor —— issue §03 验证数字未随轮2增量更新, 已修(守阵 4 条 / 最终实测数字誊基线切片 26-11-13-0232)。
- test.full 全绿(6084+2, 覆盖率 99%, 见基线切片), 轮3复评 issue HTML 修正段。
- 评审轮3(重派一次: 首派遇远端推进+报备缺列按纪律停手, sync 后按新锚 3642b1a5 重派; 报备补齐排除面三件): 零 actionable —— 轮1/轮2 发现全部核验落地未回退, issue 修正段与提交树逐点一致。三轮累计: 送检 3(检 3/3 过), blocker 0, 修 3, 入池 0。
- review: 182 行 · blocker 0 · 修 3 · 入池 0 · 检 3/3 · 轮 3 · 基 020d4bcc29b2 · 派发 1(闸门实算口径, trailer 以提交信息为准)。

