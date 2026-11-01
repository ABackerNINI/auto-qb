# mutmut 3.8 跨轮增量 + 预置 src 的 mtime 竞态: 跳过 trampoline 生成致 forced-fail 假轮与 dump 全部无法重放(两形态)

> 摘要: mutmut 3.8 跨轮增量 + 预置 src 的 mtime 竞态: 跳过 trampoline 生成致 forced-fail 假轮与 dump 全部无法重放(两形态)
> 触发: mutmut run 换目标, cp src 进镜像, 镜像 mutants 旧副本, Unable to force test failures, 全 no tests 假判定, dump 重放失败, source_mtime, 无 trampoline 原件, mutate_file_contents, 跨轮增量复用 mutants

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

### mutmut 按 mtime 误判「变异已存/未变」: 跳过 trampoline 生成 → forced-fail 假轮 + 全 no-tests 假判定污染 stats, 或镜像 mutants/ 内目标文件被回写成无 trampoline 原件 → dump 重放全部失败

- **触发**: mutmut 3.8 跨轮增量复用 `mutants/`(不走 `mutants.run` wrapper 的清缓存路径)时, 两个入口都会踩: ①往镜像 cp 过新 src(或上轮生成阶段已把目标文件复制进 `mutants/src/`)后**换 only_mutate 目标**再跑 —— 镜像副本 mtime 新于真实 src, mutmut 误判「已处理」跳过 trampoline 生成; ②镜像 `mutants/` 内的目标文件副本被任何中间操作回写成**无 trampoline 的原始文件**(手工恢复/编辑器误触等中间操作)后再导出 dump。
- **判别**: 形态①—— 跑步几秒内就 `FAILED: Unable to force test failures`(forced-fail 注入的变异根本没进 trampoline, 测试自然全绿); 或跑完 stats 里目标函数**全部 no tests**(测试没映射到变异函数)。形态②—— `mutants.report` 导出时**每一条**都「无法重放/diff 重放失败」, 且 `mutants/src/**/<目标>.py` grep 不到 `__mutmut` trampoline; 对照 `.meta` 判定与 `.spans` 索引仍完好(判定数据没坏, 只是 trampoline 文本丢了)。根因都是 `source_mtime < mutant_mtime` 一类 mtime 比较让 mutmut 相信「内容没变」。
- **处置**: 形态①—— 删 `mutants/` 内该目标的**文件副本 + `<file>.meta` + `<file>.spans` + `mutmut-stats.json`**(整体 `rm -rf mutants` 亦可, 但会连没坏的目标一起重跑), 再 `mutmut run` 重跑; stats 必须删, 否则假判定继续被当缓存复用。形态②—— meta/spans 完好时不必重跑: 用 mutmut 自带 API 在镜像里原位重建(`mutate_file_contents`, 按 `.spans` 逐函数重建 trampoline 文本; 函数 hash 未变则判定全保留), 再重导出 dump。**根治口径**: 跨轮换目标/换池一律走 `commands run mutants.run`(自带 `rm -rf mutants mutmut-cache.db`); 绕过 wrapper 直跑 mutmut 时, 开跑前先删目标副本+meta+spans+stats。
- **守阵**: 无机检; 复跑轮的「新增存活=0 逐 id 对差」是兜底探测面 —— 假轮产出的存活集会大面积偏离首轮, 对差立刻爆。
- **复发**: 3 —— (1) 2026-11-01 W9a(R33) T17a 首轮(换目标跑出全 no-tests 假判定污染 stats, 删副本+meta+spans+stats 重跑后恢复); (2) 同日 T17b(镜像 grouping_mod.py 副本被 14:50 中间操作回写成无 trampoline 原件, 1455 dump 全部无法重放, mutate_file_contents 原位重建后重导出 1505 dump 236 条 0 失败); (3) 同日本收尾轮 S6 复跑 run B 再现形态①(run A 生成阶段已把 ops_mod 复制进 mutants/, 换目标后 forced-fail 假轮, 删 ops_mod 副本+stats 重跑恢复)。
