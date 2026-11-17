# rowwin-zoom-est-rescale

> 摘要: 修复 issue 26-11-16-0716: 行窗口化占位基准冻结后运行时 root zoom 变化不重校(未量行按旧缩放估高偏大 ~11%) —— _rootZoomOf 单点(body 比值实测, null 不回落 1) + _measureRowH 开头按 zNew/zOld 原地比例重标 _rowHs/_rowH(不删键不翻量齐态) + 出窗重探过渡拍让路(防双重缩放) + created() 初始化 _rowHZoom; 三层守阵(静态剥注释守阵 + node 电池 11 项 + e2e 运行时缩放用例×3皮肤, 判据 scrollHeight≈0.9×before 判稳后取值) + 两轮红验(首轮 3/3 红, 评审改判据后 prism 复红 1907px); 评审 2 轮(轮1 1 minor 判别力不足已修, 轮2 零 actionable); issue 翻 Done + 两坑档回写(css-zoom 已知权衡段改写 + rowwin-stale 缩放重标段) + 基线切片; test.full 6253P/19S 覆盖99%
> 最后活动: 2026-11-17 00:09

**R0(2026-11-17 00:09):** 修复 issue 26-11-16-0716: 行窗口化占位基准冻结后运行时 root zoom 变化不重校(未量行按旧缩放估高偏大 ~11%) —— _rootZoomOf 单点(body 比值实测, null 不回落 1) + _measureRowH 开头按 zNew/zOld 原地比例重标 _rowHs/_rowH(不删键不翻量齐态) + 出窗重探过渡拍让路(防双重缩放) + created() 初始化 _rowHZoom; 三层守阵(静态剥注释守阵 + node 电池 11 项 + e2e 运行时缩放用例×3皮肤, 判据 scrollHeight≈0.9×before 判稳后取值) + 两轮红验(首轮 3/3 红, 评审改判据后 prism 复红 1907px); 评审 2 轮(轮1 1 minor 判别力不足已修, 轮2 零 actionable); issue 翻 Done + 两坑档回写(css-zoom 已知权衡段改写 + rowwin-stale 缩放重标段) + 基线切片; test.full 6253P/19S 覆盖99%
