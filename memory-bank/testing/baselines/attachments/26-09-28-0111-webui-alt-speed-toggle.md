# 基线 · 1814 passed + 3 skipped —— 备用速度切换轮(webui-alt-speed-toggle)

> 摘要: 状态栏备用速度切换(TPL-A 乌龟) + 限速浮层主/备同窗双组(TPL-C)落地(计划 26-09-28-0037):
> 后端 qbapi 备用限速读写(setPreferences alt_*)/模式切换(toggle 端点) + 路由 2 条 + 命令 2 条;
> 前端三主题 sprite + .sb-alt + 弹窗双组; 守阵 +2(路由/命令 + qbapi 换算), 金清单 61→63 条。
> 数字取自实施完成实测(`commands run test.full`; 提交前已合并远端 aef2462d→e8978704)。
> 基线时间: 2026-09-28 01:11
> 档案: memory-bank/tasks/26-09-28-webui-alt-speed-toggle.md

- **测试增量**: +2(`test_api_speed_alt_and_toggle` / `test_qbapi_alt_speed_limits_normalization`);
  `_GOLDEN_ROUTES` +2(POST /api/speed/alt · /api/speed/alt/toggle); `gen_doc_map.py` 头部收口
  (_doc-map 12,144 超 index-auto cap 12,100 → 12,007, 本轮未动 CAP_POLICY)。

TOTAL 1815 passed + 3 skipped / 91%(12390 语句 / 914 未覆盖 / 4204 分支 / 387 partial, test.full 16.7s)
对比前基线(26-09-28-0041): 1813 passed + 3 skipped / 91%(12355 语句 / 914 未覆盖 / 4198 分支 / 387 partial)
—— passed +2(本轮新增测试; 合入远端 e897870 后净 +1), 语句 +35 / 分支 +6(新增代码路径),
未覆盖与覆盖率持平, 零回归。数字取自合并远端之后的新基线实测。
覆盖率口径见 [baseline.md](../../testing/baseline.md)。
