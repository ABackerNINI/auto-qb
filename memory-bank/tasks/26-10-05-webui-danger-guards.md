# 26-10-05-webui-danger-guards — WEBUI 危险动作防护(重检确认框 + 跳检前置条件)

**Status:** In Progress
**Added:** 2026-10-05
**Updated:** 2026-10-05
**Summary:** 认领 26-10-05-0254 两姊妹件(重检鼠标路径缺确认框 / 跳检缺前置条件判定)并出实施计划 26-10-05-0314(方向 A: 闸门下沉 ops 单点); 复析翻转 D4 —— 组员校验在途(1.5)/校验失败推断(1.6)由不拦改拦(新闸门 G7/G8), 相邻缺口「候选自身当日校验失败无闸门」入池 26-10-05-0402; 待 D1-D3/D5-D7 拍板后 S1-S5 分步实施。
**Refs:** memory-bank/plans/26-10-05-0314-plan-webui-danger-guards.html, memory-bank/issues/26-10-05-0254-feat-webui-recheck-confirm.html, memory-bank/issues/26-10-05-0254-feat-webui-skip-check-preconditions.html, memory-bank/issues/26-10-05-0402-bug-skip-check-self-fail-gate.html, memory-bank/testing/baselines/26-10-05-0413-webui-danger-guards.md
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
| S0 认领+复验+计划 | Done | 计划 26-10-05-0314 落盘, Open 待拍板 |
| 复析修订(D4 翻转+G7/G8) | Done | 2026-10-05 第二会话; 计划 §01/§03/§04/§05/§06/§07/§08 已更新 |
| 缺口入池 26-10-05-0402 | Done | 自身失败无闸门, bug/standard/Open |
| D1-D3/D5-D7 拍板 | Open | 等用户拍板(计划 §01 表全部附推荐) |
| S1 ops 闸门扩展 | Open | 依赖拍板; G3-G8+filelist+store 上移 |
| S2 WEB 回执核对 | Open | 预计零改动 |
| S3 重检确认框 | Open | 前端共用 helper, 三入口接入 |
| S4 确认框文案增补 | Open | 依赖 D4(已定)/D5 拍板 |
| S5 收尾基线+状态回写 | Open | test.full+issue/计划置 Done |

## 进度日志

- 2026-10-05 03:14(第一会话) — 认领两姊妹件, 复验均仍复现(基线 5e697ea0); 实施计划落盘(方向 A/矩阵/D1-D7 附推荐/T1-T15 守阵); 双向认领链+kb.index 闭环。
- 2026-10-05 04:02(第二会话) — 用户对 D4 提出复析(组员在途=准确性可能无保障, 校验失败=一定无保障, 用户不观察组员状态)。下沉核对 checking.py/full_checking.py/ops_mod.py 后结论成立, D4 翻转均拦, 新增 G7/G8; 计划七节同步修订; 复析中发现「候选自身当日校验失败无闸门」缺口, 经用户确认入池 26-10-05-0402。
- 2026-10-05 04:13(第二会话) — 收尾 DoD: 任务建档(本件); test.full 基线 2554 passed + 4 skipped / 99% / 29.15s(与上基线五组数字完全相同, 纯文档轮), 切片 26-10-05-0413。
