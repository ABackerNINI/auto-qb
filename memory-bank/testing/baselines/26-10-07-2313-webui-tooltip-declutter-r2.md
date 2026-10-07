# 2757 —— WebUI tooltip 二轮去冗 + 锚定下放收尾基线 (webui-tooltip-fix2)

> 摘要: 专题 webui-tooltip-declutter 二轮(26-10-07)收尾 —— 详情面板移除 45 处复述/开发者
> 口径 title + 容器级 title 锚定下放 6 组(修 tracker 状态卡片栅格错位), 两提交
> `94013201`/`99fa6eef`, 真浏览器悬浮实测 12/12 PASS。对比上基线 26-10-07-1336(2745+4)。
> 基线时间: 2026-10-07 23:13

**Refs:** memory-bank/tasks/26-10-04-webui-tooltip-declutter.md

## test.full 实测

- 分支: webui-tooltip-fix2(已快进并入本地 develop @ `99fa6eef`; 工作树含本轮收尾回写的未提交改动时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2757 passed + 4 skipped, 0 failed, 32.41s, 覆盖率 TOTAL 99%**
  (16259 语句 / 166 未覆盖 / 5686 分支 / 150 partial; 门槛 98% 达标)
- 相对上基线 [26-10-07-1336](26-10-07-1336-webui-delta-sync-s10-baseline.md)
  (2745 passed + 4 skipped @ 35.4s, 16259 语句 / 166 未覆盖 / 5686 分支 / 150 partial):
  passed **+12** —— 本轮测试改动 = 既有守阵 `test_removed_redundant_tooltips_stay_removed`
  扩 I 组 37 needle(测试函数数不变, 源码面 16 文件纯删/移挂 title), 零 Python 产品代码改动,
  语句 / 分支 / 未覆盖 / partial 四项与上基线**逐项持平**; passed 增量来自 1336 基线树之后
  并入 develop 的其它分支提交携带的测试(audit-fixes / followups 等守阵)与本轮 issue HTML /
  activeContext 切片入库后的 docs-forms / memory-bank 收集增量。
- 4 skipped 为 Windows 侧 POSIX 专属存量。

## 补充实测(本轮专题面)

- `npm run test:e2e:fast`: **6 passed**(chromium, 桩 ui_harness@8137 自动起停)。
- 真浏览器悬浮实测(ui_harness@8199 + Playwright chromium 1280x800): **12/12 PASS** ——
  04 色族胶囊×3 / 01 横幅 chips / 06·09 收起摘要条 span / 05 删净无弹 / peers 07 IP 单元格
  与 04 卡头保留项 / console 零错误; 浮层与悬浮元素中心水平距 0.1~29.4px(阈值 40~70px),
  证据截图 9 张存 `.zcode-tmp/`(临时, 勿入库)。

## 对照判据(后续沿用)

- 以本切片(2757+4 / 16259 / 166 / 5686 / 150)为二轮后对照点: 预期 passed 只升不降、
  未覆盖 / partial 不升; 回退先查 webui-tooltip-fix2 两提交段的改动。
- e2e 对照点: `test:e2e:fast` 6 passed; 全量 `dev.e2e` 的 6 条存量失败(根因 A/B, 见
  1336 切片「e2e 复测结论」段)与本轮无关, 修复后应回 92 passed。
