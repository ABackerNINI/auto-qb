# 3498 passed + 4 skipped(根) —— memory-bank 文档流水线 P2: 状态与改版(kb.status/kb.bump + D4 反向补链)

> 摘要: 计划 26-10-17-0527(memory-bank-doc-pipeline)P2 实施落地: `kb.status`(flip_status.py —— 载体探测单点 `_common.DOC_KIND_*`, 与建面 FAMILIES 分工「那边管建、这边管改」; 计划/报告 doc-status 5 词表翻转 + 抬 doc-updated, 档案 **Status:** 4 词表翻转 + 抬 Updated; 同状态幂等不抬戳不重建索引; 词表单点 import 表外值 fail-fast; 终态条件提醒(同专题切片迁出 / Summary 收口 A1); 切片/issue/未知载体拒绝并指路; 路径三形态解析) · `kb.bump`(bump_doc.py —— HTML 抬 doc-updated + `## 变更记录` 追加 R 行, 编号 = 段内最大+1, 只追加已有行零触碰, note 自动 HTML 转义; 档案抬 Updated; 切片抬最后活动; 无变更记录段 fail-fast 指路) · D4 反向认领自动补链(new_doc --refs 从「P1 判拒」改实现: 本件写 doc-refs meta / **Refs:** 行, 目标件四类载体(HTML/md)自动反向声明, 幂等合并英文逗号; 坏 refs(不存在/库外/生成物)fail-fast 不落半文件) · 元数据读写单点落 `_common`(html_meta/set_html_meta/md_field/set_md_field/set_last_active/split_refs/html_set_refs/md_set_refs/sync_body_meta —— gen_doc_map 的本地 _split_refs 一并收敛; 索引重建共用 `rebuild_index` 单点) · P1 潜伏缺陷两处修复(领域最长前缀匹配 `match_domain` 补 `memory-bank` 领域可达性 + P1 基线切片「52 → 59」计数笔误就地更正为 45 → 52) · 守阵 6 条全绿(P2 五条 + 领域缺陷守阵一条)。test.full 全绿收口。
> 基线时间: 2026-10-17 08:45

- 根 `test.full`(契约: 覆盖率门槛 98% + 包内 TMPDIR; 跑在含本轮知识库回写的同一棵树上): **3498 passed + 4 skipped in 144.86s**(套件总耗时 147.5s); TOTAL **17885 246 6012 180 98%**(语句/未覆盖/分支/partial/覆盖率)。比 P1 基线(3492+4)净增 6 条 —— P2 守阵 5 条 + P1 缺陷①守阵 1 条(`tests/test_memory_bank.py` 52 → 58), 无产品代码改动 ⇒ 语句数不变(17885), 覆盖率同为 98%。(P2 主体验收首跑 127.10s, 含缺陷修复的终跑 144.86s, 数字一致; 注: P1 基线切片首版「52 → 59」有误 —— 已就地更正为 45 → 52 并留勘误行, 首版错误快照备查)
- `kb.check` 全绿(含新增面检查、认领链双向机检、回写措辞守卫、时间守卫); cap 债务不变(切片数 133, 两条超 cap 切片), 均为存量, 不拦提交。

## 本改动面

- `.agents/skills/memory-bank/scripts/_common.py` —— 改面载体探测段: `DOC_KIND_PLAN/TASK/SLICE/ISSUE` + `DOC_KIND_STATUSES`(词表单点查表) + `DOC_KIND_INDEX_SCRIPT` + `detect_doc_kind(path, mb)`(mb 相对目录前缀+扩展名, 收集口径与 gen_doc_map.collect 同源); `resolve_doc_path(raw, root, mb)`(绝对/仓库根相对/mb 相对三形态); `rebuild_index(root, mb, script)`(kb.new/kb.status/kb.bump 共用, 与 gen_all 同一 build 实现); 元数据读写单点 `html_meta`/`set_html_meta`(存在原行替换, 缺则插 doc-updated 行后)/`md_field`/`set_md_field`(缺行返回 None 交调用方 fail-fast)/`set_last_active`/`split_refs`/`html_set_refs`/`md_set_refs`(md 锚点链: 已有 Refs→并值 / Topics→其后 / 最后一个 `>` 头行 / `# 标题`; 只动元数据行, 幂等)/`sync_body_meta`(计划族正文 .meta 镜像行与 head 同改, 缺即无操作); **缺陷①修复**: `match_domain(topic)`(紧邻 `TASK_DOMAINS` 的最长前缀匹配单点 —— 枚举含短横线项 `memory-bank`, 首段切分 `split("-",1)[0]` 会让它永远不可达; `topic == d` 保留 P1 裸领域照收行为) + `FamilySpec.domain_first` 注释同步
- `.agents/skills/memory-bank/scripts/flip_status.py`(新增) —— `kb.status <path> <to>`: 翻转 + 抬 doc-updated(stamp)或 Updated(日期) + 重建受影响索引; 同状态幂等; 终态条件提醒(plan: 同专题切片 glob 迁出提醒 / task: Summary 收口 A1); 切片→拒绝指路 kb.wrap, issue→拒绝指路 create-issue(跨 skill 不 import 单点纪律), 未知载体/缺状态行/词表外值全 fail-fast; 输出「剩余人工 0 项(判断 0 · 条件 b · 机械 0)」§5.4 契约
- `.agents/skills/memory-bank/scripts/bump_doc.py`(新增) —— `kb.bump <path> --note`: plan 抬 doc-updated + 变更记录追加 `R<max+1> · <stamp>` li(note HTML 转义, 段缺失 fail-fast); task 抬 Updated; slice 抬最后活动; issue/未知载体拒绝; 输出「剩余人工 0 项(判断 0 · 条件 0 · 机械 0)」
- `.agents/skills/memory-bank/scripts/new_doc.py` —— `--refs` 从判拒改 D4 实现: refs 先解析(存在+库内+非生成物, fail-fast 不落半文件)再渲染, 本件正向声明写进渲染结果(html_set_refs/md_set_refs), 目标件反向补链(按后缀分发, 幂等, 打「已双向补链」行); `_rebuild_index` 改为委托 `_common.rebuild_index`; `_print_remaining` 删两条【可选】手补 refs 行(D4 已自动化); **缺陷①修复**: 领域校验改调 `_common.match_domain`(最长前缀), 拒绝文案保留首段回显(`现为 'memory'`)便于就近纠错
- `.agents/skills/memory-bank/scripts/gen_doc_map.py` —— 本地 `_split_refs` 删除, 改 import `_common.split_refs`(认领链分隔单点收敛)
- `.commands/kb/config.toml` —— 经收录协议落 `kb.status`/`kb.bump`(run/when/note/timeout 齐全, 引擎 show 占位符解析实测); kb.new 的 note 更新(--refs 已由 D4 接手)
- `tests/test_memory_bank.py` —— 新增 5 条守阵 + 头部测试计划清单同步 + import-cleanly 列表扩 flip_status/bump_doc: ①flip 全路径(翻转/镜像同改/幂等不抬戳/五类拒绝/终态提醒/契约行只打一次) ②bump 全路径(R 行递推/已有行零触碰/转义/缺段 fail-fast/三载体抬升) ③D4 四类目标反向声明+幂等合并+三类坏 refs+无 refs 与 P1 一致 ④全链演练(kb.new(--refs)→填空→status→bump→认领链双向机检绿+红绿双验(删反向声明判红、还原复绿)+改后仍过新增面守卫) ⑤两命令已收录(.commands/kb 存在性+when/note 必填); **缺陷①守阵** ⑥领域最长前缀(连字符领域 memory-bank 可建 / `memory-` 前缀撞名不误收 / 裸领域沿用 P1 行为 / 真坏领域仍拒 —— 红绿双验: 修前判红「现为 'memory'」, 修后全绿)
- **缺陷②修复**: P1 基线切片(`26-10-17-0752-memory-bank-doc-pipeline-p1.md`)的测试计数笔误「52 → 59」就地更正为 45 → 52(`git show <P1提交>:tests/test_memory_bank.py` 回算核实: P1 前 45 / P1 后 52), 切片内补勘误行注明首版错误与更正依据(基线切片非运行时依赖, 就地更正不破坏历史审计; 标题的 3492+4 与 S12+7 自洽, 不动)
- 计划 HTML(`memory-bank/plans/26-10-17-0527-plan-memory-bank-doc-pipeline.html`) —— §10 追加 R4 行(经 kb.bump 本体落盘=狗粮自验), §07 P2 行标「✅ 已实施验收(R4 · 26-10-17-0844)」, 正文 .meta 镜像 doc-updated 同抬 + 状态括注改 P1/P2
- 会话切片(`memory-bank/activeContext/26-10-17-0527-memory-bank-doc-pipeline.md`) —— 经 kb.wrap 追加 R5 行 + 抬最后活动(切片正文裸测试数字禁写, 数字只誊写进本基线, 裁定 A4)
- `memory-bank/pitfalls/git/unpushed-branch-sync.md`(新增坑档) —— 未推送分支的 ship 死锁: run_push 先跑 run_sync, 而 sync 只认同名远端分支(ls-remote 现查真值), 从未推送的分支永远过不了 sync ⇒ push 死锁; 处置: 用户终端手动 push -u 建立远端对应后再走 ship 脚本

## 未动(范围守恒)

- P3(收尾与二期族: pitfall/report/baseline/progress 模板、doc-forms「创建/更新方式」节、根 AGENTS.md 两行路由、README 细路由、SKILL.md DoD 措辞)——计划 §07 后续行, 本轮不动
- 任务档案 `tasks/2026-10-17-memory-bank-doc-pipeline.md` 仍未建(§08 立档注记: 新建文件待用户显式确认, 确认后随本专题入库)
- 提交按用户显式指令**只提交本地**(`ship.commit --no-push`; 覆盖「提交=commit+push 一次走完」的默认)——当前特性分支无远端对应 = ship 死锁(见坑档 `pitfalls/git/unpushed-branch-sync.md`), 推送待用户终端 `push -u` 建立对应后另行 `ship.push`
- cap 债务不变(切片 134>70; 26-10-15-0728 19,412; 26-10-16-0541 13,905): 存量, 不拦提交, 转告用户另开会话清理
- MSYS2 heredoc 反斜杠吞转(P1 候选坑档, 触发词二期)仍未立档
