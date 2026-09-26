# 26-09-27-rule-iyuu-stop-guard — 规则系统可行性实验: 禁止 IYUU辅种 分类种子开始下载

**Status:** Done
**Added:** 2026-09-27
**Updated:** 2026-09-27
**Summary:** 想法.md L298 的可行性实验(问答轮起, 用户令「报告落盘后提交」): 现行规则系统能否表达「禁止带 IYUU辅种 分类的种子开始下载」。实验分两步 —— 配置期 `validate_config` 校验候选 spec(三种写法全通过; 实测显式 `interval: 0S` 被拒、`state` 只收 `is_*`), 行为级用内存 Fake 跑真 `Rule.process`(状态矩阵 8×3 + 去重对照)。**结论: 条件侧完全支持, 动作侧只有 `stop`** ⇒ 能表达「永远不处于下载方向状态」的**持续压制**, 不是「禁止开始下载」的预防保证(种子由 IYUU 直接加入 qB, 本程序只能在同步节拍 1.5s 后事后发现, 窗口内已在下)。推荐形态 = `on_torrent_added` 立即压制 + 缺省 interval 每 tick 兜底, 条件必须带 `state:["is_downloading"]`(只按分类会误伤做种), 且**不能**配 `execute_once: once/daily`。边界: 真正闭环需新动作(整种子文件优先级置 0, qB 层已有该手段且 WEB UI 有手动入口)或加入端暂停。发现一处计划外样例漂移(`test_yamls/` 五个样例写 `log_level`, 现行 spec 已拒该键), 按范围守恒未修。产出报告 `reports/26-09-27-0047-report-rule-iyuu-stop-guard.html`。
**Topics:** rule-iyuu-stop-guard
**Refs:** memory-bank/reports/26-09-27-0047-report-rule-iyuu-stop-guard.html

## 原始请求

> 实验现行规则系统是否支持语义: 禁止带"IYUU辅种"分类的种子开始下载

（来源: `想法.md` L298 的待办条目。首轮为**只读咨询轮**, 在回复里给出结论与实测; 用户随后指令「报告落盘后提交」= 授权新建文件 + commit + push。）

## 思考过程与决策

- **D1 判据拆成两半**: 「条件能不能选中这个集合」与「有没有动作能阻止下载」是两个独立问题。前者查 `conditions.py`(有 `category` 条件与 `expr` 的 `tor.category`), 后者查动作全集(12 个: add/remove tags·category、start、stop、checking、move_to、reannounce、upload/download_speed_limit、print_torrent_details)—— **没有任何「禁止下载」类动作**, qB WebAPI 同样没有该开关(能影响下载方向的只有 pause/stop、限速、文件优先级、强制开始、分享率)。
- **D2 语义只能落在「持续压制」**: 既然没有阻断开关、且种子的加入发生在 qB 侧(IYUU 直接添加), 唯一可达的语义是「发现它处于下载方向状态就暂停」。这决定了答案不是「支持/不支持」二元, 而是「近似支持 + 三条前提」。
- **D3 条件必须带状态限定**: 只按分类写会在 uploading/stalledUP 上误伤做种(实测)。加 `state: ["is_downloading"]` 后行为正确, 但该类别集含 `checkingDL`/`metaDL` ⇒ 会连带挡住校验与拉元数据(副作用, 需用户取舍)。**这是实验发现的、写规则时最容易踩的一点。**
- **D4 去重必须留 `never`**: 「不变量」要求每次被重新开始都能再按下去。实测 `execute_once: once` 第二轮起就被 `exec_history` 去重掉 ⇒ 明确写入结论「不能配 once/daily」。
- **D5 两条触发路径叠加**: `on_torrent_added` 在同步线内**同步即时**分派(qbmanager.py:779), 比周期任务早一个任务线节拍; 缺省 interval 规则「加入队列即立即到期下一 tick 执行」+ 每 tick 重入队 ⇒ 兜底。推荐两条一起配(单一事件触发挡不住之后的 resume; 单一 interval 首次压制晚一拍)。
- **D6 不做实机验证**: 结论只依赖「动作映射到什么 API + 何时被调度」, 内存 Fake 已能完全覆盖(FakeClient 的 stop 会改写状态为 pausedDL, 与 qB 语义一致); 真机差异只剩下载窗口大小这类环境量, 不足以改变结论。
- **D7 计划外发现按范围守恒处理**: `test_yamls/test_actions/*.yml` 五份样例写 `log_level`, 而现行规则 spec 已知键已无该项(实测被 `validate_config` 拒)。**未修、未入池**(入池需显式授权), 只在报告 §8 留证。

## 实现计划

1. 读码取判据: `rules/conditions.py`(category) / `rules/actions/*`(动作全集) / `rules/base.py`(process 语义与去重) / `core/mixins/rule_engine.py` + `core/qbmanager.py`(绑定与触发时机) / `config/validation/rules.py`(spec 取值约束)。
2. 配置期实验: 三种候选 spec 过 `validate_config`, 并实测两条约束(显式 `interval: 0S` / `state` 裸枚举名)。
3. 行为级实验: 内存 Fake 装配 manager, 状态矩阵 8 状态 × 3 形态 + 去重对照(never vs once, 每轮重置状态模拟 resume)。
4. 落报告(本件 26-09-27-0047, dark 单文件 HTML, `doc-refs` 指向本档案)。
5. 收尾 DoD: 本档案 + activeContext 切片(受 40 上限约束需蒸馏一张最老切片)+ 坑复发记账 + `kb.index` + `test.full` 与基线切片 + 提交入库。

## 子任务状态表

| 子任务 | 状态 | 说明 |
|---|---|---|
| 读码取判据(条件/动作/绑定/触发/spec 约束) | Done | 关键位置见报告 §9 证据索引 |
| 配置期校验实验 | Done | 三种写法全通过; `interval: 0S` 与 `state: ["downloading"]` 实测被拒 |
| 行为级状态矩阵实验 | Done | 8 状态 × 3 形态, 见报告 §3 |
| 去重语义对照实验 | Done | never 每轮压制 / once 第二轮起漏过, 见报告 §4 |
| 报告落盘 | Done | `reports/26-09-27-0047-report-rule-iyuu-stop-guard.html` |
| 提交入库 | In Progress | 随本提交入库(报告 + 档案 + 切片 + 索引 + 基线) |
| (未做) 新增「阻断下载」动作插件 | Open | 需用户拍板; 属改代码, 本轮只给边界判定 |

## 进度日志

- **2026-09-27 (问答轮)** — 只读轮: 按 AGENTS.md 路由读规则系统文档 + 源码, 给出结论(条件支持 / 动作只有 stop / 竞态窗口 / 绑定前提 / checkingDL 副作用 / 跳检 auto_start 对抗), 并附实测矩阵。**未改任何文件、未入池、未立档**(遵守请求边界: 纯问答轮只在回复作答)。
- **2026-09-27 (落盘轮)** — 用户令「报告落盘后提交」⇒ 按 doc-forms 协议落 report(26-09-27-0047, 单文件 dark)、建本档案与 activeContext 切片。收尾细节: ①切片数在写前恰为 40(= `SLICE_COUNT_LIMIT`), 新增即 41 ⇒ 蒸馏最老的可蒸馏切片 `26-09-22-2221-backend-cross-group-file-conflict`(其活线索已在 Open issue `issues/26-09-22-2221-feat-cross-group-file-conflict.html` 内, 切片只余指针)并把指针并入 `progress/roadmap.md`, 删切片守上限。②踩到已记坑 `pitfalls/testing/tmpdir.md`: 想「单文件小跑」而裸跑 `uv run pytest tests/test_memory_bank.py tests/test_docs_forms.py` ⇒ `PermissionError … pytest-current`(默认 `H:\Temp`)—— 正是该坑「复发 4→8」记的同一根因(把单文件小跑当轻量例外绕开引擎), 已在该条 `复发` +1 并记「为什么没命中」。③闸门与基线见下方收尾条目。
- **2026-09-27 (收尾闸门 + 合流)** — ①守卫面 34 绿(doc-forms / memory-bank 两个文件); ②全量在**合流前**的 base
  (`38918da8`)上 1683 passed + 1 skipped / TOTAL 91%; ③提交预检发现远端已被另一 clone 推进到 `f1879040`
  (两笔 WEBUI 搜索提交), 按「同步路径」走: 内容改动存仓外 patch → `git restore` 清空 → `git merge --ff-only` 快进
  → `git apply --3way` 施回。唯一冲突 `pitfalls/testing/tmpdir.md`(双方都在追复发流水)手工解 —— 我的条目按合并后
  编号由 9 **订正为 12**(合并进来的会话已用到 11); ④该文件在合并后顶到 pitfall cap(合并版本 5,999 字符, 余量 1),
  按 skill「超了拆文件或外迁」把最早的复发流水(1 / 2+3 / 4→9 共九踩)**原样外迁**到
  `pitfalls/testing/attachments/tmpdir-recurrence-history.md`, 原位留指针(主文件回落到 5,137); ⑤索引在新基线上重建,
  kb.check 6/6 绿; ⑥新坑入库: `pitfalls/git/editing-traps.md` 增「文本模式写回已含 CRLF 的内容 ⇒ `\r\r\n` 双重转换」
  (本轮实写踩到; 虚高的行数字符还会把文件假顶到 cap); ⑦最终闸门数字见基线切片(在合流后的 base 上重测)。