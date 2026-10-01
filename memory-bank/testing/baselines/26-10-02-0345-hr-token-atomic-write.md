# 基线 · 2217 passed + 3 skipped / 97.51% —— hr.token 原子写清偿(W1 1/3)

> 摘要: issue 26-10-01-2151 清偿(hr.channel resolve_token 改走 utils.atomic_write, +3 守阵)的收尾基线;
> 相对上一基线(26-10-02-0254: 2143+3 / 96.46% @ 29f1841a)增量 = 测试用例 +74(8b7831cd 覆盖率提升 P2-a
> 与 P1 收尾入库) + 本轮 3 条守阵, 覆盖率 96.46%→97.51%。
> 档案: [tasks/26-10-02-hr-token-atomic-write.md](../../tasks/26-10-02-hr-token-atomic-write.md)。
> 基线时间: 2026-10-02 03:45, develop @ 8b7831cd; 工作树含本轮改动(未提交)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。

TOTAL **2217 passed + 3 skipped / 97.51%**(13,278 语句 / 298 未覆盖 / 4,444 分支 / 88 partial,
test.full 28.5s, rc=0; 阈值 94%)。

## 闸门过程记录(三跑一确认)

- 首跑 1 failed → 判已知 flaky 未动: `test_hr_service.py::test_budget_unit_wait_and_caps` 在 xdist
  全量下偶发, 整文件(77 passed)与单跑均绿 —— 已入池 issue 26-10-02-0306(Open), 与上一基线
  (26-10-02-0254, 零代码变更轮)撞的是同一条, 与本轮 hr/channel.py 改动无涉。
- 二跑同条再挂(偶发窗口内), 三跑全绿: 2217+3 / 97.51%, rc=0。
- 定向: test_hr_channel.py 全文件绿(新增 3 条守阵: 生成可读回 / 已有 token 不漂移 / 写一半中断自愈)。
