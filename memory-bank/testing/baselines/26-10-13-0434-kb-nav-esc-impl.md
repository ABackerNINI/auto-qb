# 3176 —— kb.nav Esc 退栈实施 (nav_page.html 链 + 守阵 +4)

> 摘要: 拍板四拍点 (P1 as proposed / P2 兜档不清筛选 / P3 keep per-input / P4 IME guard yes) 即实施 —— `nav_page.html` wire() 段新增 `escRetreat()` 单点退栈链 (overlay z-50 → ctxMenu z-40 → drawer z-30 → sel row → 兜档收展开态+清 selTopic, 门 console+非输入态) + IME 守卫; 既有 document-level Esc 监听 (closeCtx only) 并入链; `test_kb_nav.py` 守阵 +4。全绿即基线.
> 基线时间: 2026-10-13 04:34

## 验收数字

- `test.full`: **3176 passed + 4 skipped** / `TOTAL 16750 159 5702 140 99%`.
- 耗时: **49.1s** (本机并行默认).
- 单文件预跑: `test.one tests/test_kb_nav.py` 43 passed (39 既有 + 4 新 Esc 守).
- Linux 侧未重测 (改动为平台无关的 HTML/JS 壳 + static-source 守阵).

## 本波改动面

- 改: `.agents/skills/memory-bank/scripts/nav_page.html` (wire() 段: `escRetreat()` 链 + IME guard + overlay/drawer/sel/兜档; 数据层/服务层零改动) · `tests/test_kb_nav.py` (守阵 +4: single_point / ime_guard / overlay_first / closes_drawer + 测试计划 docstring 登记).
- 回写: `memory-bank/tasks/26-10-13-memory-bank-kb-nav-esc.md` (子任务 2/3/4 推进 + 进度日志) · `memory-bank/plans/26-10-13-0324-plan-kb-nav-esc.html` (拍板落 + 实施记) · 基线切片 (本份) · `kb.index` 生成物重建.

## 已知偏差 / 移交

- 守阵集合 +4 (39→43 单文件); 数字差异看差值 `commands run kb.baseline -n 2` 现列.
- IAB smoke (plan §06 optional) 未跑 —— 链行为 static-source 钉四档齐 + z 序钉; 浏览器冒烟归后续 kb.nav 轮按需.
- 兜档门条件 `S.view === "console"`: 台账视图里展开态 (expanded) 不清 —— 拍板 P2 保守口径 (卡片 expanded 属卡片视图, 未 in scope 兜档).
