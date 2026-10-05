# 强制汇报确认机制重构实施计划 (backend-reannounce-confirm)

> 摘要: 依调研报告 26-10-05-0854 出分步实施计划 plans/26-10-05-0923-plan-reannounce-confirm-rework.html: 现判定把 qB 5.2 的 next_announce(epoch 秒)当倒计时、成功判据方向反了恒不触发 → 30s 恒误报失败; 修复 = 主判据改 epoch 前跳(TOL 3s, 限基线 status≥2 行)+ 停止种子直判 + 「未确认」与「失败」分列 + 推迟路径早回执(已受理·推迟至 HH:MM)+ 后台日志核实 + 旧版(<5.2)回退证据门控。改动收敛在 webui/commands.py(判定纯函数+基线形状+item 级窗口)、webui/runtime.py(check_pending 状态机+reannounce_background)、static/shared/commands.js(reannounce 聚合三桶分流, 前端只认 ok/error 终结态故第三态走 error+前缀约定), 不新增配置键; 规则侧 ReannounceAction 接入为非目标(D5)。实施前置闸 S0 = 报告 §8 只读探针(未联系行 epoch 值/立即跳幅/推迟同值移动)。
> 最后活动: 2026-10-05 09:47

**Refs:** memory-bank/plans/26-10-05-0923-plan-reannounce-confirm-rework.html, memory-bank/tasks/26-10-05-backend-reannounce-confirm.md, memory-bank/reports/26-10-05-0854-report-reannounce-confirm-api.html

## 已完成
- 计划产出: 五分支判定/回执三态文案契约/item 级窗口与推迟早回执时序/S0–S5 分步/测试矩阵/风险回滚, 拍板点 D1–D5 附推荐(D1 早回执+后台核实, D2 TOL 3s+语义(b), D3 字段存在性探测, D4 error+前缀约定, D5 规则侧非目标)。
- 代码事实核验: 现链路四判据锚点(commands.py:24/:209/:228/:311, runtime.py:301)、前端 waitCmd 终结条件只认 ok|error(commands.js:131)、store 停止态判据(record.py:231 state_enum.is_stopped)、规则侧无确认(transfer.py:27 ReannounceAction 仅 600s 限频)、测试未钉住前端 30s 文案。
- 认领链接线: 计划 doc-refs → 调研档案, 档案 Refs 行补反向声明; kb.index 重建 + docmap --check 全绿(405 件/241 专题)。
- 收尾基线: test.full 2589 passed + 4 skipped / 36.73s / 99%(baselines/26-10-05-0947, 零代码改动与上基线全一致)。

## 正在进行
- 等用户对计划拍板点 D1–D5 逐项确认(或「按推荐」一句话拍板) → 拍板后立实施档案 → S0 真机探针 → S1–S5。
