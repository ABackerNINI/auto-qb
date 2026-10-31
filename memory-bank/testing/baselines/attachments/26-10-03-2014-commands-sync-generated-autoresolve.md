# 基线 · 2413 passed + 3 skipped / 99% —— 同步时自动化解生成物索引冲突(计划 26-10-03-1544 实施)

> 摘要: 实施计划 26-10-03-1544(本期范围 S1 + S2): 新增 `gen_all.py` 作生成物集合单点(`kb.index` /
> `kb.check` 各由四条收成一条)+ 配置三键(`auto_resolve_generated` / `generated_list_cmd` /
> `generated_regen_cmd`)+ `run_sync()` 落「白名单 → 任取一侧 + 重跑 → `--check` 自证」——
> 快进被拒(落后 + 脏重叠)与 rebase 冲突(有界循环)两条分支自动化解生成物冲突, 手写冲突行为逐字不变;
> S1 另加改动前预检 + 快照回滚, S2 另加收尾自证 + `commit --amend`。src/ 零改动(全在 `.commands/` 与
> `.agents/skills/`)。数字取自**提交时点合并远端之后的新基线**(开工 `7ef83e63` → 实施期间远端连推 4 笔
> 至 `181d90c3`, 按失败行配方 stash→sync→pop 零冲突合流)。test.full 首跑曾红 1 条幽灵包残壳(本 clone
> 历史残留 `core/mixins` / `mixins` / `web` / `web/routes`, 与本轮无关), 按陷阱档处方整目录删除即绿。
> 基线时间: 2026-10-03 20:14, develop @ 181d90c3 + 工作区(本轮回写件未提交)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。

TOTAL **2413 passed + 3 skipped / 99%**(14,395 语句 / 131 未覆盖 / 4,810 分支 / 104 partial,
test.full 40.8s, rc=0)。
相对上一切片(26-10-03-1537: 2408 passed + 3 skipped / 99%, 语句 / 分支数同) **passed +5** ——
本任务 +3(`tests/test_memory_bank.py` 新增 gen_all 守阵三条: 产出集合 == 库内全部 `_index.md` /
`--check` 绿 / `--list` == `collect()`) + 合流远端 2(qB 口径流量图 P5a/P5b 的 `tests/test_web.py` 守阵)。
**包内脚本测试不在本数字内**(testpaths 之外): test_sync 12→20 用例、test_pipeline +3、test_engine 改 1,
走 `commands run test.pkg`(88 passed)。
