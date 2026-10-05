# 基线切片 26-10-05-1723 — commands.js wait_ms 埋点段缩进归位 (纯空白)

> 摘要: 修复 `src/auto_qb/webui/static/shared/commands.js` 中 `_cmdRecToResult` 的 wait_ms 埋点段既有缩进不齐 ——
> `if (typeof r.wait_ms === "number")` 的块体被写成 14/16/18 空格(文件通篇 2 空格制式, 应为 8/10/12),
> 且 `const c = this.cmdStats;` 一行独写 12 空格, 段内三档缩进互不咬合。25 行纯空白重排,
> `git diff -w` 为空(零语义改动), `node --check` 语法通过。
> 基线时间: 2026-10-05 17:23

**Refs:** memory-bank/activeContext/26-10-05-1723-webui-commands-js-indent.md

- 分支: develop @ a4d14a8d(会话开工同步; 工作树含本轮改动: commands.js 缩进 + 本切片 + activeContext 切片)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2610 passed + 4 skipped, 37.1s, 覆盖率 TOTAL 99%**
  (15702 语句 / 164 未覆盖 / 5342 分支 / 138 partial; 门槛 98% 达标)
- 相对上一条**本 clone** 基线 [26-10-05-1000](26-10-05-1000-pytest-cov-gate-test-one.md)(2603 + 4 @ 8dd38afe):
  passed **+7** / 分支 +34 / 语句 +97 / 未覆盖 +1 —— 全部来自会话开工同步并入的 a4d14a8d
  (qB 流量存储 v3 S6 活尾合流, 新增守阵 7 条 = store 3 + grid 1 + sample 1 + web 2), **与本笔无关**。
  本笔只改 JS 静态资源空白, `src/` 与 `tests/` 零改动, `git diff -w` 为空 ⇒ 对用例数/覆盖率**零增量**。
- ⚠ 26-10-05-1007(2596 + 4)系另一 clone 测得, 绝对数不可与本 clone 直比(该切片已自注跨 clone 哈希差异)。
- 靶向验证: `commands run test.one -- tests/test_web.py` → 296 passed + 1 skipped(webui 守阵全绿 ——
  本轮不新增守阵, 既有"读文件"型守阵对空白改动天然免疫); `node --check commands.js` 语法 OK。
- 改动面: `src/auto_qb/webui/static/shared/commands.js`(25 行缩进归位) · 本切片 + activeContext 切片 · `kb.index` 生成物。
