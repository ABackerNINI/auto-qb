# 异步操作的成败宣称凭一份快照观测直接下结论 —— 成功必须有正证据门控, 决定性时刻直查真值

> 摘要: 「从陈旧观测直接下确定性结论」—— 异步操作(recheck 这类 qB 异步应用 + 快照按节拍滞后)的成败宣称若只凭一份快照观测, 而该快照在「生效前」与「生效后」**不可分辨**(已完成种子 progress=1.0 且非 checking, 既是校验前的完成态也是校验通过后的状态), 必然产出假结论。三个面: ①假成功 —— 首跳误判(issue 26-10-03-1140: WEB 批量 recheck 已完成种子, 提交后约 1.1s 四条「校验成功」挤在同一毫秒, 实际 40GB 原盘刚开始校验; 规则源同路径会把未经真实校验的种子假晋升 verified_references); ②同族假失败 —— 小种子校验在约 2s 采样间隔内完成时永远见不到 checking, 走满宽限误判「校验启动超时」(rule 源还会计冷却); ③伪证据别名 —— qB 启动期 checkingResumeData 是简历校验(恢复上次中断的进度), 与本轮 recheck 是否生效无关, 拿它当生效证据会打开新的假成功路径。修法(plan 26-10-04-1824, 2026-10-04 落地): 判定提为纯函数 + 生效证据谓词收窄 + 决定性时刻直查真值 + 歧义保守落侧。
> 触发: 异步操作, 成败判定, 轮询, recheck, 校验成功, 校验启动超时, seen_checking, poll_verdict, is_piece_checking, checkingResumeData, 伪证据, 快照滞后, 首跳, 假成功, 假失败, 证据门控, 效果确认, 等待期零API

### 快照在「生效前」与「生效后」不可分辨时, 单份观测推不出确定性结论

- **触发**: 给任何「提交后异步生效」的操作写结果轮询 / 成败判定, 或排查「日志宣称成功/超时, 实际 qB 里
  行为相反」—— 只要判定输入是**一份快照观测**, 而存在某个状态对 (生效前, 生效后) 在该观测上取值相同,
  判定就必然有一侧是假的。
- **判别**: 三问。①成功分支的正证据是什么? 只有 progress / 状态位这类**结果态**而没有**过程态**
  (观测到操作真实生效的过程) ⇒ 假成功面(首跳落在「尚未生效 / 快照未反映」窗口即命中)。②严格要过程态
  后, 小于采样间隔的过程会不会被整段跳过? 会 ⇒ 假失败面(等满宽限误判超时)。③过程态的状态值集合里
  有没有同名伪证据(qB 启动期 checkingResumeData 也叫 checking)? 有 ⇒ 伪证据面(别名把别的管线的过程
  当成自己的生效证据)。
- **处置** (判据/修法四条, 本次修复点 `ops_mod.py` recheck):
  1. **成功结论必须有正证据门控**: 观测到真正的过程态才算「生效已确认」, 且证据谓词收窄排除同名伪证据
     (`checking_meta.is_piece_checking` 只认 {checkingDL, checkingUP}, 排除 checkingResumeData)。
     判定提为**纯函数**(`checking_meta.poll_verdict(seen_checking, progress, baseline_progress, elapsed,
     giveup)`), 成功签名要求 seen_checking=True —— 「无证据成功」在签名层面不可表达, 配全叉积穷举测试
     钉死(test_checking.py 160 组合)。
  2. **决定性时刻直查真值, 不回落快照**: 影响结论落定的时刻(提交点 R1 复核 / 宽限耗尽仲裁)对 qB 单
     hash 直查核实, 事件驱动一次性(生命周期至多 1 次), 不构成周期轮询; 直查异常 fail-closed 判败,
     直查不可得不为「成功」背书。
  3. **歧义保守落侧**: 未见证据且 progress 回落按「校验未通过」提前判败(回落是数据缺损的辅助签名);
     宽限耗尽仍无证据判「启动超时」—— 宁可标签诚实的超时, 不要标签体面的假成功。
  4. **周期观测与决定性直查分工**: 等待期的周期观测保持零 API 纯快照读(等价性红线, E 组用例钉住),
     API 只花在决定性时刻 —— 不把「直查真值」退化成高频轮询。
- **守阵**: `tests/test_checking.py` A 组(谓词 / 逐行表测 / 160 组合穷举) + `tests/test_ops.py`
  B 组(门控状态机) / C 组(仲裁直查) / D 组(R1 实时复核) / E 组(等待期零 API 红线)。
- **库内既有范本** (同一纪律的四处先例):
  [src/auto_qb/webui/runtime.py](../../../src/auto_qb/webui/runtime.py) `defer_receipt` / `flush_truths`
  (改种子状态的命令回执推迟到补刷新之后再写 —— 宣称落后于真值落地); 同文件 `check_pending` +
  [commands.py](../../../src/auto_qb/webui/commands.py) `_confirm_reannounce_result`(reannounce 只发指令
  并登记确认跟踪, 回执由确认机制对照 baseline 核实后给出 —— 发出 ≠ 成功);
  [src/auto_qb/core/modules/ops_mod.py](../../../src/auto_qb/core/modules/ops_mod.py) skip_check R2 实时
  复核 + `_poll_until`(动手前对 qB 短间隔直查确认); 同 webui/runtime.py WEB 命令真值直查红线(取不到就
  返回 None 不回落快照 —— 回落会把「读不到」伪装成「读到了旧值」)。本次修复点: 同文件 `OpsModule.recheck`
  —— poll_verdict 门控(S1/P0) + poll 闭包证据门控状态机(S2a/P0) + 宽限耗尽仲裁直查(S2b/P0) + 提交点
  R1 实时复核与 live 基线(S3/P1)。
- **已知边界** (不在修复范围, 计划 §6.4 原话): seen_checking 已立起但校验进程被 qB 重启吞掉不续跑 ——
  该情形仍走向超时/失败侧的既有语义, 属既有边界, 本次未处理。
