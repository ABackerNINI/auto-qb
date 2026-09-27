# 26-09-28-commands-shipflow-output-contract — my-commit-flow 输出契约 v3 (沉默即成功)

**Status:** Done
**Added:** 2026-09-28
**Updated:** 2026-09-28 02:03
**Summary:** 用户判定 my-commit-flow 输出背离设计初衷(少手写错误/少 token/复杂藏背后)。计划 26-09-28-0157 全章节 Done: v3 已实施并真机验收(4ba6cb7f, ship.commit 输出 2 行); W2 推广落地——W2-1 根治 charset_normalizer 半装(授权普查 7 clone, clone2 待其进程退出), W2-2 引擎摘要结论行必保, W2-3 警告 6→0(pytest.ini 消息前缀过滤)。全量 1818 passed / 0 failed / 0 warnings(基线 26-09-28-0432)。

## 原始请求

用户实贴 `commands run my-commit-flow.sync`(失败态)与 `ship.commit`(成功态)的输出并逐行标注(「多余」「这是什么???」「居然输出了两次」), 判定 my-commit-flow **完全背离设计初衷: 减少手写命令错误、减少 token、将复杂隐藏在背后**。指令: sync 输出只留「同步成功 <hash>」/「同步失败需解决冲突 本地<hash> 远端<hash> <步骤>」; commit 成功只留「提交成功 <hash>」, 失败说清原因; 镜像允许滞后无需提。要求**推翻重构, 先写一个新 my-commit-flow 计划**。

## 思考过程与决策

- **诊断(逐条对到代码)**: 「Exit code 3」=引擎 `FAILED=3`(run.py:31); `[自证] 将要执行+绝对路径`=ship 任务 `risky=true`(ship/config.toml:13)触发 run.py:57-62; WARN 翻倍=commit.py:152 与 push.py:127 **各跑一遍完整预检**; 「从未 fetch?」=sync 被设计成只读不自愈(preflight.py:27); 「略过 61 行」=脚本原始 76 行触发引擎摘要器。根因: v2 计划(26-09-26-2345)的 L1「让命令自己出示证据」把证据当成了默认输出——方向反了。
- **v3 取舍**: 继承 v2 的 L2 零参数化与 L3 编排合一; 推翻 L1 为「沉默即成功」; L4 错误导航收成失败行「原因+下一步」各一句。
- **sync 从只读改自动**(fetch+ls-remote 真值+auto ff-only): 树脏交 git 裁决(无重叠自然成功/重叠 git 拒绝→翻译成失败行), 删 sync_recipe 自算配方 60 行; 分叉走 merge-tree 只读预判(D1 拍板自动 merge 或只报)。
- **行为变化的边界**: 内部检查一个不删(ref 三处/ls-remote 真值/staged 暴增/红线/11 闸门/消费即删/GBK 兜底/PARTIAL 语义), 删的只有检查项里的摆设(上游名/平台关键词提示)与全部常规路径输出。
- **顺带修复**: issue 26-09-28-0128(逐路径 add 撞已暂存删除)在重写 commit.py 时按文件存在性分流 `git rm --cached` 一并落掉。

## 实现计划

计划文档单点: [memory-bank/plans/26-09-28-0157-plan-commands-shipflow-v3.html](../plans/26-09-28-0157-plan-commands-shipflow-v3.html)(输出契约总表/行为规格/保全清单/验证矩阵/token 账)。

- **M1 脚本与配置**: preflight.py→`_pipeline.py`(闸门/展开/changed_files/红线/--init); 新增 sync.py; 重写 commit.py/push.py(一行契约); verify_ref.py 收一行; config.toml 删 preflight 任务+ship 去 risky; 测试重写(含「成功输出 ≤2 行」契约断言 + issue 0128 回归用例)。
- **M2 文档回写**: AGENTS.md(会话协议①/提交节, 跑 doc.caps 查 8000 上限)、memory-bank SKILL.md:15、conventions/collaboration.md、包 README+references/pipeline.md 重写、pitfalls/git/push.md 措辞、kb.index。
- **M3 引擎微调**(D4 拍板后): run.py `FAILED 3→1` + test_engine + docstring。
- **验证**: 临时 clone 场景矩阵(齐平/落后/树脏±重叠/分叉±冲突/离线/红线/闸门红/staged 删除), 只在系统临时目录建 throwaway 副本(跨仓库红线); 真机验收等用户说「提交」。

## 子任务状态表

| 子任务 | 状态 | 备注 |
|---|---|---|
| 摸底现状(包脚本/引擎/引用面/陷阱索引) | ✅ 完成 | 本轮, 全部 file:line 已核 |
| 计划文档 26-09-28-0157 | ✅ 完成 | status Open, 待拍板 |
| D1 拍板: sync 对分叉怎么合流 | ✅ 已拍板 | 26-09-28 用户: rebase 保线性 → 分叉自动 rebase(树净, 冲突即 abort), merge 方案与替代舞蹈淘汰 |
| D2–D5 拍板(镜像静默/preflight 移除/引擎退出码/warn_lines) | ✅ 已拍板 | 26-09-28 用户「其余按推荐」: 镜像全程静默 / preflight 移除 / 退出码统一 0/1 / warn_lines 保留一行 |
| M1 脚本与配置重写 | ✅ 完成 | sync.py 新增; commit/push 重写; _pipeline.py 收编; verify-ref 收一行; 测试重写(57 项) |
| M2 文档回写(AGENTS.md 等 7 处) | ✅ 完成 | AGENTS/SKILL/包 README/pipeline/config/anti-patterns/push.md; doc.caps 与坏链绿 |
| M3 引擎退出码统一 | ✅ 完成 | run.py FAILED 3→1; test_commands_engine 的 preflight id 断言随改 |
| 场景矩阵验证 | ✅ 完成 | test_sync.py 11 场景(真实临时仓库) + 真机 sync 成功/失败双路径冒烟 |
| 真机提交验收 | ✅ 完成 | 26-09-28 03:29 提交 **4ba6cb7f**: ship.commit 全程 58.7s, 输出恰 2 行([ok] + 提交成功 <hash>), 推送 Gitee ✓, 镜像静默到位(github 同步到同 hash); 中途闸门红一次(issues 索引未重建)——失败行一行给出原因与命令, 照做重跑即过, 本身也是失败路径的验收 |
| W2 推广: 其余命令同款噪音 | ✅ 完成 | 计划 §10 四件 04:45 全落地。W2-1: clone1 修复(裸 uv sync 对半装包假绿, 须 --reinstall-package), 警告清零; 授权普查 7 目录仅 clone1/clone2 损伤, **clone2 被 .pyd 占用待进程退出后重跑**(requests 已实测零警告, 余混态美容)。W2-2: 引擎 _digest 结论行(N passed/TOTAL)无条件必保。W2-3: 警告 6→0(自家 docstring \p 转义修 + starlette/anyio 按消息前缀过滤——starlette 类别是 UserWarning 子类按类别落空)。**W2-4(用户追补): silent_success 旗标**——test.full/quick 成功只出结论行不打略过提示(信息类不加旗标), 真机验收 test.full = [ok]+TOTAL+passed 三行 |
| doc-map 容量触顶(收尾时发现, 计划外) | ➡ 已入池 | [issue 26-09-28-0219](../issues/26-09-28-0219-question-kb-doc-map-cap.html), 待用户定调, 本轮不改 |

## 进度日志

- **2026-09-28 02:03** 计划落盘(基线 635693f, 与 gitee/develop 齐平)。诊断表 11 条实贴症状全部对到 file:line; 输出契约 v3 定稿(成功 ≤2 行/失败=原因+下一步/退出码 0/1); 引擎侧只做 E1(config 去 risky, 零引擎改动)+E2(FAILED 3→1); RESULT 协议机制保留不动(范围守恒)。等待用户拍板 D1-D5。
- **2026-09-28 02:20** 收尾回写完成(档案/切片/基线切片 26-09-28-0220/issue 26-09-28-0219)。test.full: 1814 passed / 3 skipped / 1 failed——唯一红 = doc-map cap 触顶(12259/12200), 取证: HEAD 源重生成即 12153(余 47 字符), 合规「计划+档案」对固定占 ~106 字符, 任何立档会话必破; 实测 topic 收口合并反而增大(12259→13181 字节档), 已回退到最小足迹并入池待定调。本轮未改任何源码; 排查中踩「守阵按字符数、wc -c 按字节数」的坑(中文 ×3), 已写进 issue 0219 备注。
- **2026-09-28 02:38** 用户拍板 D1: 「rebase 禁令已移除, 必要时可使用 rebase 保持提交历史线性」→ 计划 D1 定稿为**分叉自动 rebase**(树净才动, 冲突即 --abort 回滚 + 失败行, 只改写未推送提交); 原推荐 A(merge, 非线性)否决, pipeline.md 的 reset --hard + format-patch 替代舞蹈在 M2 一并淘汰。计划文档已同步修订(§3.1/§06/§07/§09/页脚), D2–D5 仍待拍板。
- **2026-09-28 04:07** 用户补报 clone2 的 test.full 实贴(结论行被 RequestsDependencyWarning 两行夹住 + 「略过 169 行」) → 取证: charset_normalizer 半装损坏(无 api 模块)且无 chardet; pytest.ini 无 filterwarnings; 引擎摘要末 3 行取行结论不保。**W2 三件处方补进计划 §10**, 计划回 In Progress。
- **2026-09-28 04:19** 用户**授权跨 clone** 修复 → 普查 D:\Projects 下 7 个 auto-qb 目录: 损伤仅 clone1/clone2, clone3/4/5/long-seeding/auto-qb 正常未动。clone1 经 `uv sync --reinstall-package charset-normalizer` 修复(裸 uv sync 对半装包假绿 "Checked 39 packages" 直接跳过); requests 导入 `-W error` 干净, test.quick warnings 10→6。clone2 首轮失败(cd.cp313-win_amd64.pyd 被占用, 拒绝访问)。
- **2026-09-28 04:45** **W2-4 追补落地**(用户: test.full 成功也要静默, 消掉「略过 149 行」提示): 做成任务级显式旗标 `silent_success`(_config TASK_KEYS/Task 字段/解析; test.full/quick 声明)——引擎成功路径 `_digest(conclusions_only=True)` 只出结论行(无结论形态退回末 N 行不变盲), `_emit` 不打略过提示; **信息类命令不加旗标**(kb.active 的 47 行切片清单靠提示兜底, 一刀切=静默吞内容)。真机验收: test.full = [ok]+TOTAL+passed 三行零提示, test.quick 两行。引擎测试 15 项(+4)。全量 1818 passed / 3 skipped / 0 warnings / 19.8s / 91%, 基线切片 26-09-28-0445。SKILL.md 摘要段同步。
- **2026-09-28 04:32** **W2 三件全部落地**: ①W2-1 见 04:19 条(clone2 重试: uv 仍报 .pyd 占用, 但首次修复已补齐全部 .py 文件——api 可导入、requests 实测零警告; 余下 cd.pyd 混态属美容, 进程退出后彻底重装)。②W2-2: run.py `_digest` 增 `_CONCLUSION` 判据(`N passed/failed` / `TOTAL` / `no tests ran`, 锚定行首), 结论行**无条件必保**、不与异常行竞争 break 名额; +2 引擎用例(含锚定防膨胀反例)。③W2-3: 盘点 6 条警告 → 自家 1 条(test_web.py:44 docstring `\p` 转义 SyntaxWarning 改 `\\p`) + 第三方 2 类按**消息前缀**过滤进 pytest.ini filterwarnings(starlette 的 StarletteDeprecationWarning 是 **UserWarning 子类**, 按 DeprecationWarning 类别匹配落空——实测教训) → **warnings 6→0**。④其余命令盘点: 动作类 env.sync/env.version/doc.links/kb.index/dev.fmt 成功全部 ≤2 行; 信息类 kb.active/kb.baseline/doc.caps 按设计保留明细。⑤验收: test.full 可见 = [ok] + TOTAL + passed + 位置提示; test.quick 干净收尾零警告。全量 1818 passed / 3 skipped / 0 failed / 17.5s / 91%(12512 语句), 基线切片 26-09-28-0432。计划 26-09-28-0157 全章节 Done。
- **2026-09-28 03:30** 真机验收通过, 任务完成: 用户说「提交」→ sync(已同步 9dc7a1b2) → 消息入 `.git/COMMIT_MSG_AI.txt` → `ship.commit` **58.7s 跑通全流程, 输出恰 2 行**(第一次闸门红: issue 0219 改状态后 issues 索引未重建——失败行一行给原因+命令, 重建后重跑即过, 顺带验证了失败路径)。`git ls-remote` 三方一致 4ba6cb7f(gitee/github/本地), 镜像静默生效; 消息文件消费即删, 工作区净。计划 26-09-28-0157 抬 Done。token 账实测: 提交轮可见输出 = sync 2 行 + commit 2 行 + 验收核对, 对比 v2 同轮(sync 6-10 行 + commit 76 行原始/16 行摘要)——按行数 -80% 以上, 且零排障式追问。
- **2026-09-28 03:21** 用户拍板 D2–D5(「其余按推荐」)并下令实施 → **M1–M3 全量落地**: ①M1: preflight.py 删(检查表式预检退役), 共享件收编 `_pipeline.py`(闸门引擎/展开/changed_files/红线/`--init`); 新增 `sync.py`(fetch+快进/rebase, 一行契约); 重写 `commit.py`(编排合一: 内部同步→闸门→逐路径暂存[按存在性分流修 issue 0128]→提交→核 ref→消费即删→内联推送)、`push.py`(同步核对→推主线[瞬时重试一次]→核远端→镜像**全程静默**)、`verify_ref.py`(PASS 一行/失败保留处置细节, 退出码 0/1); 配置×2(task 树 4 入口, ship 去 risky=[自证]消失); 测试重写 test_pipeline(改编)+test_sync(11 场景真实临时仓库)+test_commit(重写)。②M3: run.py FAILED 3→1。③M2: AGENTS.md(会话协议①/硬约束/提交节×3)/memory-bank SKILL.md(连带修掉过时的「rebase/stash 一律禁用」)/包 README+pipeline.md 全重写/config.md 脚本名/anti-patterns 合流与镜像条/pitfalls/git/push.md 摘要与处置。④坑两枚: 新测试用 tmp_path 夹具踩 TMPDIR 假红(修 test.pkg 定义加前缀, 原「不建临时目录」说法过时); sync/push 无 argparse 时 `--help` 被忽略会**真执行同步/推送**(冒烟闸门雷, 补 argparse 前置)。⑤全量 1816 passed / 3 skipped / 0 failed, 覆盖率 91%; 基线切片 26-09-28-0321。⑥远端两次快进合流(7efcc8f/9dc7a1b2, 生成文件恢复→ff→kb.index 无损路径); issue 0219 被上游 gen_doc_map 渲染收口取代(Superseded)。
