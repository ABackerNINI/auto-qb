# 26-10-05-webui-danger-guards — WEBUI 危险动作防护(重检确认框 + 跳检前置条件)

**Status:** Done
**Added:** 2026-10-05
**Updated:** 2026-10-05
**Summary:** 认领 26-10-05-0254 两姊妹件并按计划 26-10-05-0314 实施完成(方向 A: 闸门下沉 ops 单点 + 三分流预检): ops G3-G8 + filelist 执行链 + force 语义 + precheck dry-run(S1), webui 预检端点 + force 透传(S2), 前端重检确认框共用 helper(S3), 跳检预检对话框三分流状态机(S4); 新增守阵 22 条全部红验先红后恢复; 复析翻转 D4(G7/G8)与三分流修订(04:33)均按用户定向落地; test.full 2576 passed + 4 skipped / 99%(基线切片 26-10-05-0737); 相邻缺口「候选自身当日校验失败无闸门」另立 26-10-05-0402(Open 待拍板)。
**Refs:** memory-bank/plans/26-10-05-0314-plan-webui-danger-guards.html, memory-bank/issues/26-10-05-0254-feat-webui-recheck-confirm.html, memory-bank/issues/26-10-05-0254-feat-webui-skip-check-preconditions.html, memory-bank/issues/26-10-05-0402-bug-skip-check-self-fail-gate.html, memory-bank/testing/baselines/26-10-05-0413-webui-danger-guards.md, memory-bank/testing/baselines/26-10-05-0737-webui-danger-guards.md, memory-bank/pitfalls/testing/static-guard-mutation.md
**Topics:** webui-danger-guards

## 原始请求

用户点名两个 WEBUI 危险动作缺口: ①重新校验只有键盘路径有确认框, 鼠标三入口点下即执行; ②跳检(WEB 入口)缺「该不该允许」的判定, 已完成/做种中种子可被删种重加、统计清空、文件缺失被标「完整」。两件以 26-10-05-0254 姊妹 issue 入池后由本任务认领。

## 思考过程与决策

- **方向 A(闸门下沉 ops 单点)而非 WEB 入口自判**: ops_mod 头注自述保护策略单点归本模块; 单发/批量两入口写两遍必漂移; filelist 原语在 ops。判定原语(store/by_hash/active_check_hashes)全部 ops 可达, 无新增跨模块依赖。
- **D4 复析翻转(2026-10-05 第二会话)**: 原「组员校验在途/失败推断不拦」的论据反驳的是 I/O 冲突, 危害实在数据准确性 —— 1.5 实为等判决时序(等待清空后重走决策链: 通过晋升参考/失败 1.6 拦截), 1.6 是当日校验失败+文件映射一致的确定性坏数据证据; G3-G6+确认框对该场景零覆盖(filelist 只查存在与尺寸); 洗白经 chain 0 永久化。均改拦, 新增 G7/G8(谓词逐字镜像规则侧, G8 假失败自愈只读变体)。
- **「候选自身当日校验失败」缺口不并入**: G8 须与 chain 1.6 逐字同谓词(others-only)以保规则侧零变化; 纳入自身即行为变更, 另立 26-10-05-0402 单独拍板。
- **G6 组级判定上移 store 单点**: `group_has_downloading(hash)` 落 TorrentStore, grouping_mod 改委托, 模块间不 import 的契约不破。

## 实现计划

按 [计划 §05](../plans/26-10-05-0314-plan-webui-danger-guards.html) 分步: S0 认领+复验+计划(已完成) → S1 ops 闸门扩展(G3-G8+filelist 并入执行链, store 组级判定上移) → S2 WEB 回执透传核对(预计零改动) → S3 前端重检确认框共用 helper → S4 跳检确认框文案增补 → S5 收尾(红验复核+基线+状态回写)。每步独立提交可 revert; 测试守阵 T1-T17 见计划 §06。

## 子任务状态表

| 子任务 | 状态 | 说明 |
| --- | --- | --- |
| S0 认领+复验+计划 | Done | 计划 26-10-05-0314 落盘 |
| 复析修订(D4 翻转+G7/G8) | Done | 2026-10-05 第二会话; 计划 §01/§03/§04/§05/§06/§07/§08 已更新 |
| 缺口入池 26-10-05-0402 | Done | 自身失败无闸门, bug/standard/Open 待拍板 |
| D1-D10 拍板 | Done | D1/D2/D6 随三分流定向消解, D4 复析翻转; D3/D7/D8/D9/D10 全按推荐落地 |
| S1a store 组级判定上移 | Done | bcc2bce2: group_has_downloading 上移单点, grouping_mod 委托保签名 |
| S1b-1 ops 闸门 G3-G6+force+precheck | Done | 09683720: _skip_gates_detail 单点 + force 语义 + filelist 执行链; R2 前移(差异①) |
| S1b-2 ops 闸门 G7/G8 | Done | 7d9595a7: 镜像 others_checking/1.6 四要件, G7=force / G8=blocked |
| S2 WEB 预检端点+force 透传 | Done | 0ff19787: POST /api/torrents/skip-check/precheck + 逐层 force 透传 |
| S3 重检确认框 | Done | 51e30393: _recheckConfirm 共用 helper 三通道接入; 批量浮条入口已退役(差异④) |
| S4 预检对话框三分流状态机 | Done | bd532d26: 进框禁用→预检→按态渲染, force 钮先见赌注, D10 降级路径 |
| S5 收尾基线+状态回写 | Done | 红验抽查 2 条复证; 基线切片 26-10-05-0737; 两 issue+计划置 Done |
| T15 真机走查 | Open | 留待用户: 三态对话框/混合批次/预检失败降级/三入口确认框 |

## 进度日志

- 2026-10-05 03:14(第一会话) — 认领两姊妹件, 复验均仍复现(基线 5e697ea0); 实施计划落盘(方向 A/矩阵/D1-D7 附推荐/T1-T15 守阵); 双向认领链+kb.index 闭环。
- 2026-10-05 04:02(第二会话) — 用户对 D4 提出复析(组员在途=准确性可能无保障, 校验失败=一定无保障, 用户不观察组员状态)。下沉核对 checking.py/full_checking.py/ops_mod.py 后结论成立, D4 翻转均拦, 新增 G7/G8; 计划七节同步修订; 复析中发现「候选自身当日校验失败无闸门」缺口, 经用户确认入池 26-10-05-0402。
- 2026-10-05 04:13(第二会话) — 收尾 DoD: 任务建档(本件); test.full 基线 2554 passed + 4 skipped / 99% / 29.15s(与上基线五组数字完全相同, 纯文档轮), 切片 26-10-05-0413。
- 2026-10-05(第三会话起, 实施棒 S1-S4) — 六笔提交落地(分支 webui-danger-guards): bcc2bce2(S1a store 组级判定上移, grouping_mod 委托保签名) / 09683720(S1b-1 detail 单点+G3-G6+force+precheck, R2 前移到闸门之前报备) / 7d9595a7(S1b-2 G7/G8 镜像闸门) / 0ff19787(S2 预检端点+force 透传, 回执走 truth 位) / 51e30393(S3 _recheckConfirm 三通道接入; 勘误: 批量浮条入口已退役) / bd532d26(S4 预检对话框三分流状态机)。拍板 D3/D7/D8/D9/D10 全按推荐; 每棒红验探针先红后恢复, T13/T24 首版守阵经红验暴露突变盲区升级为整行活性/逐分支锚定(新坑档 pitfalls/testing/static-guard-mutation.md)。
- 2026-10-05 07:44(S5 收尾棒, 本会话) — 红验抽查 2 条复证守阵活着(摘 G8→T17 红「组员当日失败应拒: ActionResult(success, ...)」; 摘 popovers.html :disabled 绑定→T23 红), 探针恢复后 test.quick 复绿 2576+4; test.full 基线 2576 passed + 4 skipped / 99% / 27.48s+28.13s, 切片 26-10-05-0737(相对 0413: passed +22 = 新增守阵, 语句 +99); 两 issue 置 Done(修复后补充: 实际修法/差异/验证/数字) + 计划置 Done(§08 完成条含差异清单六项); T15 真机走查留待用户。
