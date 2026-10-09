# 26-10-08-backend-test-web-split — tests/test_web.py 拆分(15 域 → 15 平铺模块)

**Status:** Done  
**Added:** 2026-10-08  
**Updated:** 2026-10-08  
**Summary:** 实施计划 [26-10-07-2336](../plans/26-10-07-2336-plan-test-web-split.html) 的执行档案(S0–S8 全部 ✅)。把 tests/test_web.py(14,556 行 / 329 个被收集测试函数)按注释分节机械拆成 **16** 个平铺模块 + 共享件上收(21 件 → `tests/webui_helpers.py` + `conftest.py`), 零逻辑改动、集合恒等; `tests/test_web.py` 已删除。S1 勘察映射表 329 fn 全覆盖; P-01/P-02 用户拍板(节 3 拆两份 / 节 2 panel·page / 节 1 14-7 / 共享件 fixture→conftest + 辅助→helpers); 落地分支由 `feat/test-web-split` 改道 `develop`。逐批实施记录与完整进度日志原文见 [attachments/26-10-08-backend-test-web-split-history.md](attachments/26-10-08-backend-test-web-split-history.md)。
**Topics:** test-web-split  
**Refs:** memory-bank/testing/baselines/26-10-08-0258-backend-test-web-split-s0s1.md, memory-bank/testing/baselines/26-10-08-0518-backend-test-web-split-s7s8.md

> 背景关联(不进机器认领链): 计划 26-10-07-2336 按 §2.3 声明「不声明 doc-refs, 豁免认领链」, 故本档不以 `**Refs:**` 挂计划, 只用散文引用; 计划见 [26-10-07-2336](../plans/26-10-07-2336-plan-test-web-split.html)(建档切片 26-10-07-2344-test-web-split-plan 已随本档收口迁出)。

## 原始请求

用户指令: 「实施计划S0-S1: 26-10-07-2336-plan-test-web-split.html」。即按计划 §04 的步进执行 **S0 开工前置** 与 **S1 勘察与映射表** 两步; S1 的门是 **P-01 拍板点**(请用户过目文件边界与命名后开工 S2)。

## 思考过程与决策

- **计划口径冻结, 但实测数字须重算**: 计划 §2.1 的行号/函数数是规划时点(基线 `0ae3212e`, 14,367 行)的实测; 当前 HEAD `34356f49` 已前进 5 笔, test_web.py 在流量图速率口径 S2/S3 中 +216/−27 行 → **14,556 行**。故 S1 的 AST 扫描一律以**当前文件**为真值, 不沿用计划数字。
- **S0 基线复测(计划要求「HEAD 显著前进则重跑 test.full」)**: 在 `feat/test-web-split`(从 `34356f49`)上 `commands run test.full` = **2771 passed + 4 skipped / 0 failed / TOTAL 16476/165/5694/149 / 99%**, 与最新切片 [26-10-08-0223](../testing/baselines/26-10-08-0223-test-webui-peers-harness.md)(测于含未提交改动的树)**逐位持平**。收尾 DoD 按「提交时落基线切片」新建 [26-10-08-0258](../testing/baselines/26-10-08-0258-backend-test-web-split-s0s1.md)(committed HEAD 复测, 同值), 作为本专题开工基线。
- **分支(落地改道)**: 按计划 S0 开了 `feat/test-web-split`, 但提交时发现**新分支流水线推不动** —— `run_sync` 假定远端分支已存在(先 `fetch <远端> <分支>` 再比 left-right), 取不到远端 ref 就报「拿不到远端」; `ship.push` 同样先走同步, 会卡在同一处。实测 Gitee 只有 `develop`/`master`/`feature_rules`, **无任何 `feat/*`**, 且 `gitee/develop` 已被另一 clone 推进(1a5f0262) —— 与 AGENTS.md「日常在 develop」「跨工作区同步一律走 Gitee develop」一致。经用户拍板**改落 `develop`**: develop 快进到远端 tip 后 cherry-pick 本次提交, 临时分支删除; S2–S7 亦在 develop 上做。
- **档案落名**: 计划 S0 写 `tasks/26-10-07-backend-test-web-split.md`, 但按 memory-bank skill 硬口径「档案日期取**创建日**(`commands run kb.time date`)」, 实际建档日为 **2026-10-08** ⇒ 落 `26-10-08-backend-test-web-split.md`(slug `backend-test-web-split` 不变, 已查本 clone 与跨工作区无同名)。
- **S1 关键纠偏(见 §S1 表)**: ①被收集测试函数 **329**(327 `test_*` + 2 `testhr_*`), 非计划说的 323; ②docstring 计划条目 **312**(0 幽灵 / 17 函数无条目), 非 306; ③计划「节 3 → test_web_traffic_qb.py」名不副实 —— 节 3(标记 5892→7884)实为 **18 个流量 fn + 37 个杂项 fn**(config/token/sites/group-view/error-reason/hr-status), 须 P-01 定夺拆分或改名; ④上收 conftest 的共享件远多于计划 §3.2 的 3 个(实测 **16 个辅助函数 + 3 个常量**, 含 164 行的 `_make_web_manager`)。
- **S2 校验器口径据此更新**: 校验①(集合恒等)面 = **329 个被收集函数**; 校验③(反幽灵+守恒)= 每文件条目指向本文件存在函数 + 15 文件条目总数 == **312**。
- **范围守恒**: S0–S1 只读勘察 + 建档 + 分支; 未动 tests/ 与 src/ 任何一行; 分析脚本落 gitignore 的 `tmp-analysis/`。

## 实现计划

计划 §04 的 S0–S8 步进(每批一 commit, 批间独立可停, 任何一批后中止仓库全绿)。本档跟踪各步状态。

## 子任务状态表

| #  | 子任务                                               | 状态 | 产出/说明                                                                                                                                                               |
| -- | ------------------------------------------------- | -- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S0 | 开工前置                                              | ✅  | 同步 `34356f49`; 分支 `feat/test-web-split`(提交时改落 `develop`, 见决策节); 基线复测 2771+4(见切片 26-10-08-0258); 本档; 忆坑四篇(bulk-rename/parallel-run/single-file-coverage-gate/tmpdir) |
| S1 | 勘察与映射表(只读轮)                                       | ✅  | AST 扫描 + 映射表 329 fn 全覆盖(§S1); 节 1/节 2 聚类定界与命名; 常量/辅助归属矩阵                                                                                                            |
| —  | **门: P-01/P-02 拍板**                               | ✅  | 2026-10-08 用户裁决(§P-01): 节 3 拆两份 / 节 2 panel·page / 节 1 14-7 / 共享件 fixture→conftest + 辅助→`tests/webui_helpers.py`                                                    |
| S2 | 拆分工具与红验                                           | ✅  | `scripts/split_test_web.py`(AST 切块 + 映射表 + 归属闭包 + import 裁剪 + docstring 逐条重分布); 校验 4 条内建(+内容/行守恒); 演练 collect-only **337 项 / 329 名 == 源**; 红验 3 条 6/6(§S2)          |
| S3 | 批 1 试切(节 1 → auth + api_core)                     | ✅  | 14 + 7 fn; 校验全绿; test.one 14+7 / test.quick 2771+4 / test.full 2771+4·99%; 2 处活注释已改; 批模式修工具 4 缺陷(§S3)                                                               |
| S4 | 批 2 webui 静态守阵(节 2 → 3 份)                         | ✅  | skins(8) + panel(28) + page(27); 校验 1–4 + 守恒全绿; test.one 63 / test.quick 2771+4 / test.full 2771+4·99%; 修工具第 5 缺陷(§S4)                                                    |
| S5 | 批 3 端点域(节 3 + 4 → traffic_qb + backend_misc + hr) | ✅  | 18 + 37 + 51 = 106 fn; 校验 1–4 + 守恒全绿; 演练 105+1s; test.one 105+1s / test.quick 2771+4 / test.full 2771+4·99%; 余量源 5,271 行(余 139 fn); 工具零新缺陷(§S5)             |
| S6 | 批 4 命令与视图域(节 5–9)                                 | ✅  | 31 + 25 + 17 + 21 = 94 fn; 校验 1–4 + 守恒全绿; 演练 102 passed; test.one 102 / test.quick 2771+4 / test.full 2771+4·99%; 余量源 1,517 行(余 45 fn); 工具零新缺陷(§S6)             |
| S7 | 批 5 结构守阵与长尾(节 10–15)                              | ✅  | 2 + 10 + 5 + 28 = 45 fn; 校验 1–4 + 守恒全绿; 演练 45 passed; test.one 45 / test.quick 2771+4 / test.full 2771+4·99%; **`tests/test_web.py` 已删除**(收官); 修工具第 6 缺陷(末批删除模式的 collect 面, §S7); 脚本保留入 `memory-bank/archive/`(§S7) |
| S8 | 收口验收                                              | ✅  | 全仓活引用 grep 处置 + 守阵全绿(no_duplicate / docs_forms / doc_map / kb.check) + 新基线切片 26-10-08-0525 + kb 回写(切片迁出 / 计划 Done / kb.index)(§S8)             |

## 实施记录 (原文归档)

> S1 勘察结论(329 fn 映射表)· S2–S8 逐批实施记录 原文已外迁 →
> [attachments/26-10-08-backend-test-web-split-history.md](attachments/26-10-08-backend-test-web-split-history.md)
> (与完整进度日志同文件; 档案 62,661 → 约 6.2K 字符, cap 清理轮)。

## 进度日志

> 完整进度日志(10,746 字符)**已外迁** →
> [attachments/26-10-08-backend-test-web-split-history.md](attachments/26-10-08-backend-test-web-split-history.md)
