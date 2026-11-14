# 子代理配额限流终止: SendMessage 不可续, 只能带全上下文重派

> 摘要: 长子代理(评审/实施)可能被宿主配额限流中途截断(exceed quota limit, 交回部分输出); 此时 `SendMessage` 续跑报「No active local_agent task found」—— 被配额终止的代理实例不可恢复, 唯一恢复路 = **同任务重派全新代理**, 任务提示必须自含全部上下文(前任零记忆)。与 `kb-subagent-concurrency`(并发拒收, 逐个重派即恢复)是两类独立故障。
> 触发: exceed quota limit, No active local_agent task found, 子代理截断, 重派, 部分输出, SendMessage 失败

### 判别与处置

- **触发**: 长子代理(真机实验/大批评审/多轮修复)运行中被宿主配额限流; 或对「已停止」代理误用 SendMessage 续跑。
- **判别**: ①代理交回带「exceed quota limit」框的 PARTIAL 输出(任务未完成); ②对已停止代理 SendMessage 返回「No active local_agent task found」(实例已被清理, 区别于「completed 可续跑」); ③后台任务通知 status=completed 但 result 是截断残留。
- **处置**: 同任务重派全新子代理, 提示词在原任务书基础上加一句「本任务曾有前任被配额限流截断, 你从零评审/实施, 结论独立」+ 把前任已确认的中途事实(如已核过哪些面)作为**待复核线索**而非既定结论带入; 重派计数按用户口径累计(同一任务非正常失败 3 次停手等人工)。
- **预防**: 长任务子代理(真机实验/大批评审)拆小; 每完成一个子步骤先落盘再继续(截断后重派可从落盘处接); 编排者保存每次派遣的完整任务书原文(重派时原样复用)。
- **复发**: 3 (2026-11-14 relocate-form-aware-gates 会话: T2 分面1评审/T2 修复代理/T2 复评轮3评审各一次, 均重派恢复; 前两次截断点部分输出可用于校准重派提示的「从哪里继续核」, 但结论一律重derive)
