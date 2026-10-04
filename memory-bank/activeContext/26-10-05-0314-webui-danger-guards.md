# WEBUI 危险动作防护(重检确认框 + 跳检前置条件)

> 摘要: 认领 26-10-05-0254 两姊妹件, 实施计划 [26-10-05-0314](../plans/26-10-05-0314-plan-webui-danger-guards.html)(Open, 待拍板 D1-D3/D5-D7)。2026-10-05 复析翻转 D4: 组员 full-checking 在途(1.5)与校验失败推断(1.6)由不拦改拦 —— 1.5 实为等判决时序而非省 I/O, 1.6 是确定性坏数据证据, 洗白经 chain 0 永久化且 G3-G6+确认框零覆盖; 新增 G7/G8(谓词逐字镜像规则侧, G8 假失败自愈只读变体), 前置条件 5 条→7 条, 守阵增 T16/T17。复析另发现「候选自身当日校验失败无闸门」缺口(规则侧 without_reference 段与 WEB 路径共有; 不并入本计划以防破坏规则侧零变化), 入池 [26-10-05-0402](../issues/26-10-05-0402-bug-skip-check-self-fail-gate.html)。已完成条目(复验/计划落盘/复析修订/入池/建档/基线 0413)沉淀进任务档案, 本切片只留易变层。
>
> 最后活动: 2026-10-05 04:13

## 正在进行

- 等用户对 D1-D3/D5-D7 拍板(计划 §01 表, 全部附推荐); D4 已拍板(均拦, G7/G8)。

## 下一步

- 拍板后 S1 开工(ops 闸门扩展 G3-G8 + filelist 并入执行链 + store 组级判定上移) → S5 按 [计划 §05](../plans/26-10-05-0314-plan-webui-danger-guards.html) 分步实施, 每步独立提交; S5 收尾跑 test.full 建基线切片并把 issue/计划置 Done。

**Refs:** memory-bank/tasks/26-10-05-webui-danger-guards.md, memory-bank/plans/26-10-05-0314-plan-webui-danger-guards.html
