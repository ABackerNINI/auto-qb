# mutmut 的 survived 判定不可靠: 存活必须 apply + 跑池实测, 且 verify 曾因基线常红恒判 KILLED(已修)

> 摘要: mutmut 报 `survived` 的变异, 把那条 diff **手工 apply 回去、跑一遍定向池**, 池会直接变红 —— 也就是说它其实**早就被杀死了**。rules 首轮实测: 1364 条存活/超时里 **404 条是伪存活(29.6%)**, 名义杀死率 59.9% 比真实 71.8% **低估 12 个点**; 表类(`expr/env.py` 的 `NAME_TABLE`/`FUNC_TABLE`)伪存活率高达 **49.3%**(303/614)。另一条腿当时也断了: `mutants.verify` 走**全量套件**, 而全量套件在本机 Linux 侧有 **3 个既有平台失败**(`test_alias_fs.py` ×2 · `test_relocate_paths.py` ×1), 基线常红 ⇒ 任何变异恒判 **KILLED**(**2026-10-30 已修: 判据改基线差集, 且 3 条平台失败也修绿 —— 两条测试缺 `_WIN_ONLY` 标记 · 一条断言吃到 POSIX `realpath` 的 lstat, 见处置 3**)。两条路都不可信时 ⇒ 存活判定**只能**逐条「apply → 跑定向池 → 还原」实测, 判据是「池能不能抓住」, 不是工具说什么。
> 等级: L0
> 触发: 变异测试, mutmut, 存活不可信, 假存活, survived 误报, verify 恒 KILLED, 基线常红, 全杀等于没杀, 表类变异不生效, import 期函数, process_isolation, 杀死率虚低, apply 跑池还原
**Refs:** memory-bank/testing/baselines/26-10-30-0549-mutants-rules.md, memory-bank/tasks/26-10-08-test-mutation-audit.md

### 工具报 survived, 手工 apply 后池立刻红 (2026-10-30, rules 首轮踩到)

- **触发**: 在 WSL 里跑完一轮 `mutants.run`, 直接拿 `survived` 清单当缺口单去三分类 / 补守阵。目标里含**模块级常量表**(`_build_name_table` / `_build_func_table` 这类 import 期就执行完的函数建出来的 `NAME_TABLE` / `FUNC_TABLE`), 或想用 `mutants.verify` 复核某条存活。
- **判别**:
  - **症状**: 把某条 survived 的 diff 手工 apply 回去, 跑**同一份定向池** → 直接红(池本来就能抓)。rules 首轮: 404/1364 条如此, 表类 **303/614(49.3%)**, 非表类 **101/750(13.5%)** —— 越靠近 import 期构建的数据, 工具越不可信。
  - **反证隔离不是原因**: 把 `process_isolation` 换成 `fork` / `forkserver` 各跑一遍, 伪存活集合**逐条一致** ⇒ 别去调隔离模式, 那不是病根。
  - **`verify` 的失败形态**: 它判 KILLED 的比例异常高(接近 100%), 且**所有**变异都 KILLED —— 一看全量套件在本机 Linux 侧的基线本来就是红的(3 个平台失败), 就明白了: 基线红 ⇒ 每个变异体都「测试失败」⇒ 恒 KILLED。**判别口诀: 全杀 = 没杀。**
- **根因(两类, 都跟工具实现有关, 不是你的测试写错了)**:
  1. **import 期构建的模块级数据里的变异不生效** —— mutmut 改的是源码行, 但 `NAME_TABLE`/`FUNC_TABLE` 是 import 时**求值一次**的字典; 变异体在被 import 的那份模块里生效与否取决于缓存/求值路径, 实测结果是**改了等于没改**, 于是「测试当然抓不到」→ 记 survived。614 条表类变异被**无差别**记为 survived, 与守阵强弱无关。
  2. **隔离模式无关** —— fork/forkserver 结果完全一致(见上判别), 所以「换隔离能修」是伪解法。
  3. **`mutants.verify` 走全量套件** —— 分母里塞进了与本变异无关的平台失败, 基线常红 ⇒ 恒 KILLED。它在**基线全绿**的机器上才有意义; 本机 Linux 侧不是。
     **(2026-10-30 已修)**: `cmd_verify` 改成**基线感知** —— 开跑先量一遍未变异套件的失败集合, 每条候选只判
     「本次失败 - 基线」是否非空; 同时去掉 `-x`(它会停在第一条既有失败上, 变异体根本没被执行, 老口径实测输出
     `1 failed, 1395 passed`)、补 `-B`+清 `__pycache__`、新增失败要**复跑复现**才算 KILLED(否则记 FLAKY)、
     单次套件加 `timeout`(超时记 TIMEOUT)。守阵 `.commands/mutants/scripts/test_mutants.py`。
     **口径仍要留一句**: 基线越红判据越弱(既有失败盖住的行为本来就没被套件盯住)。那 3 条平台失败同日
     已修绿(`test_alias_fs` 两条补 `_WIN_ONLY`; `test_relocate_paths` 那条是本用例的取证断言吃到了
     POSIX `realpath` 内部的 `os.lstat` —— 见 [coverage-floor-platform](coverage-floor-platform.md) 同一轮的平台差异族)。
- **处置**:
  1. **判定一律走实测三连**: 逐条 `apply 变异 → 跑定向池(单进程) → 原字节还原`。判据只有一条: **池变红 = KILLED, 池绿 = SURVIVED**; 工具声称的 survived/killed 只当**提名**, 不当结论。
  2. **分母口径**: 真实杀死率 = `(工具 killed + 实测翻案为 KILLED 的伪存活) / 变异总数`。rules 首轮 = `(2036 + 404) / 3400 = 71.8%`, 而工具名义值 59.9% —— 报数时**两个都给并说明口径**, 只报一个必然被下一轮打脸。
  3. **`mutants.verify` 在本机直接不用**: 要么先把 Linux 侧全量套件修绿(平台失败 3 条), 要么改用「跑定向池」的实测法。中间态(基线红 + 拿 verify 出数)产出的全是假 KILLED。
  4. **apply 别用 `patch -p0`**: `mutmut show <id>` 给的 diff 是 **stub 行号 + 去缩进**的形态(相对 `mutants/` 里的副本), 直接喂 `patch` 会因上下文不匹配失败。正确做法是**按变异 id 定位函数体**: 从 id 解出 `<模块>/<函数>__mutmut_<n>`, 在源码里找到该函数, 用 diff 里的 `-`/`+` 行**重新按函数体缩进**拼回, 替换后 `ast.parse` 自检, 跑池, 最后**按原字节回写**还原(别用 `git checkout` —— 会冲掉未提交的守阵, 见 [mutation-revert-git-checkout](mutation-revert-git-checkout.md))。
  5. **超时单列**: 池在窗口内没变绿 ≠ 等价变异。rules 首轮 18 条超时**不并入**真洞/等价分母(其中 `expr.lexer.x__read_string__mutmut_4` 在 150s 内已刷 F, 实质 KILLED)。
- **守阵**: 无自动机检(这条是**流程口径**, 靠执行时守); 旁证可查 —— 三分类的「假存活」数与实测翻案数**必须逐位吻合**(rules 首轮 404 = 404, 两条独立路径互证)。若两者对不上, 说明有一侧判错了, 停手复核。
- **复发**: 1 —— 2026-10-30 另一会话报告「`mutants.verify` 在本机结构性失效: 跑全量套件 + 基线常红 ⇒ 恒 KILLED」,
  与首次记录(**同一天**, rules 首轮)是同一现象的两条独立路径。为什么没命中: 首次只把它写进坑档**处置**里当
  「流程口径(别用 verify)」, 没有落到**脚本判据**上 —— 坑档写「别用」挡不住下一个人照命令表去用。**判据性缺陷
  要改脚本 + 加守阵, 不能只写「不要用」**; 本次修完即补 `.commands/mutants/scripts/test_mutants.py` 18 例守阵。

## 同族坑(别混)

- [mutation-pool-artifact](mutation-pool-artifact.md) —— 存活数是**池**的函数(池太窄 ⇒ 假存活), 与本条(池够宽但**工具**判错)互补: 那条靠加宽池解, 这条加宽池**无效**。
- [mutation-revert-git-checkout](mutation-revert-git-checkout.md) —— 还原用 `git checkout` 会冲掉未提交守阵。
- [redverify-anchor-lineendings](redverify-anchor-lineendings.md) / [redverify-pycache-stale-verdict](redverify-pycache-stale-verdict.md) —— 实测脚本自身的 apply/缓存坑(伪 KILLED / 伪 SURVIVED), 做「apply + 跑池」前先读。
