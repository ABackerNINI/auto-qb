# 基线 · 2325 passed + 3 skipped / 99% —— 站点级三态(删除类标签作用域混淆)修复轮完结

> 摘要: issue 26-10-01-2129 方案 B 完整形态(config 层三态 + WebUI 修齐 + 配置 v3→v4)四阶段收官:
> 阶段1 config 三态基座(`18bde39c`, Field.tri_state 4 站点 str 键 + `_strip_none` 站点段豁免保 '' +
> v3→v4 迁移清存量 '' 逐键 WARNING)/ 阶段2 显示层回退链 7 键生效值回填 + 站点/全局来源徽标(`42d3d90a`)/
> 阶段3 「跟随全局」删键按钮 + str「清空=覆盖为空 / 删键」语义区分 + 9 键 help 三态文案(`9c6bc499`);
> 本轮为阶段4 收尾回写(纯文档, 零代码变更)。UI 冒烟复跑 **118/118**(atlas/prism/console 三皮肤,
> dev.harness 8123 桩 + `node tmp-analysis/phase2_smoke.cjs`, 含 bool 三态走全 / str 覆盖为空 vs 删键 /
> 徽标回退链 / help 三态文案断言)。
> 基线时间: 2026-10-03 09:13, develop @ 9c6bc499(test.full 实测, 工作区含阶段4 未提交回写件 —— 纯文档, 不影响数字)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。

TOTAL **2325 passed + 3 skipped / 99%**(13,433 语句 / 88 未覆盖 / 4,542 分支 / 89 partial,
test.full 30.17s, rc=0)。
相对上一切片(26-10-03-0733: 同为 2325 passed + 3 skipped / 99%, 语句/分支数亦同, @ c91be940)
**数字持平** —— 区间内 `42d3d90a`/`9c6bc499` 落在 WebUI JS 与 help 文案层(无 Python 覆盖面变化,
阶段1 的 config 层用例已计入 0733 基线), 其余为文档提交; 行为变更由冒烟层验证(118 断言全绿)。
