# 2649 —— WEBUI 错误历史 S8 收尾基线 (S1-S7 六笔提交全量落地后的实测)

> 摘要: 计划 [26-10-05-2026](../../plans/26-10-05-2026-plan-webui-toast-error-history.html)
> S8 收尾: 功能全部实施后 (分支 feat/webui-error-history, develop + 6 笔提交) 的 test.full 基线,
> 记录功能上线实测数字 (前端静态守阵 +6 / 后端行为测试 +7 / test_web.py 路由金清单 +1 条)。
> 基线时间: 2026-10-06 04:13

**Refs:** memory-bank/plans/26-10-05-2026-plan-webui-toast-error-history.html

- 分支: feat/webui-error-history @ ae94311e(= develop @ 5f321099 + 6 笔功能提交, 待并回)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2649 passed + 4 skipped, 28.52s, 覆盖率 TOTAL 98%**
  (15946 语句 / 169 未覆盖 / 5444 分支 / 143 partial; 门槛 98% 达标)
- 相对上一条基线 [26-10-06-0144](26-10-06-0144-full-code-review-remediation-s0-baseline.md)
  (2622 passed + 4 skipped @ fb461fea, 15624/166/5400/139): passed **+27**、语句 +322、
  未覆盖 +3、分支 +44、partial +4。增量两笔来源: ①**本功能 +14 条**(tests/test_webui_error_history.py
  静态守阵 6 + tests/test_webui_backend_errlog.py 行为测试 7 + tests/test_web.py 路由金清单
  77→78 条); ②develop 侧 fb461fea→分支起点 5f321099 之间 code review 修复批次净增 13 条
  (diff 实测 58 增 / 44 删), 与本功能无关 —— 本功能单独对照 = S1 提交时点的 test.quick
  **2636** (= 2622 + 14, 见 9e70b0bd 提交信息), 全量守阵数字以本切片为准。
- 三皮肤真机走查**未做**(本会话为 CLI 会话, 无真机浏览器 + 真实 qB 环境), 入口可见 / 徽标 /
  面板开合 / 点外关 / Esc 关 / 「后端」小标待用户真机验证; 前端行为接线已由静态守阵 6 条钉死。
