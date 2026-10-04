# WEBUI 危险动作防护(重检确认框 + 跳检前置条件 + 三分流预检)

> 摘要: 认领 26-10-05-0254 两姊妹件, 实施计划 [26-10-05-0314](../plans/26-10-05-0314-plan-webui-danger-guards.html)(Open, 待拍板 D3/D7/D8-D10)。2026-10-05 04:02 复析翻转 D4: 新增 G7/G8(均拦), 前置条件 5 条→7 条; 「候选自身校验失败无闸门」缺口入池 [26-10-05-0402](../issues/26-10-05-0402-bug-skip-check-self-fail-gate.html)。04:33 用户定向三分流修订(可行性已复核: 可行且强化原架构): WEB 跳检改「点跳检 → 确认框先开确认钮禁用 → 预检请求(ops 同谓词 dry-run) → 三态返回(禁止/需显式强制/可跳检) → 按态渲染」; case 1 = 确定性危害或零收益(G3/G4/部分下载/G6/G8/filelist/同日去重, 无逃生), case 2 = 真不确定(G5/G7, force 逃生), case 3 = 放行; 执行路径闸门原样全跑(预检-执行无信任传递), force 服务端裁决缺省 False(规则侧零变化保持); webui 路由/commands 改为小改(预检端点 + force 透传)。
>
> 最后活动: 2026-10-05 04:33

## 正在进行

- 等用户对 D3/D7/D8-D10 拍板(计划 §01 表, 全部附推荐); D1/D2/D6 已随三分流定向消解, D4 已拍板并细分(G8=case 1 / G7=case 2)。

## 下一步

- 拍板后 S1 开工(ops 闸门扩展 G3-G8 + _skip_gates_detail 三态单点 + skip_check_precheck dry-run + force 参数 + filelist 并入执行链 + store 组级判定上移) → S2 路由/命令层(预检端点 + force 透传) → S3 重检确认框 → S4 预检对话框(modal 扩展 + 三分流渲染 + 降级路径), 每步独立提交; S5 收尾跑 test.full 建基线切片并把 issue/计划置 Done。

**Refs:** memory-bank/tasks/26-10-05-webui-danger-guards.md, memory-bank/plans/26-10-05-0314-plan-webui-danger-guards.html
