# rowwin reprobe 去重签名嵌布局读数(表顶) = 抖动假失配

> 摘要: rowwin reprobe 去重签名嵌布局读数(表顶) = 抖动假失配
> 触发: gBCR 超量, reprobe 重探, 皮肤相关探测数, 重开窗

## 本篇只回答

「去重/缓存签名里嵌了布局读数(getBoundingClientRect 类量值)导致假失配、去重失效白付工作」这一类问题的触发、判别与处置; 行高存值陈旧(签名该探而没探)是反方向, 走 rowwin-stale-rowh-pad-jump。

### 表顶(_winTop)嵌进 reprobe 去重签名, 页面收敛期抖动让重开窗一拍全键行白付 gBCR

- **触发**: rowWin off→on 复原重开窗一拍对全部已持键行逐行 gBCR(皮肤相关: atlas off 侧 68 vs prism 34, 与轮数/tTotal 无关, 逐轮复现)。签名 `${sy}|${vh}|${n}|${_winResize}|${_winTop}` 里的表顶是布局读数(.content 顶 + 前置 sticky 列头高), 页面收敛期(列偏好/字体落定)与窗口化/全量两渲染态间有亚像素~4px 抖动; off 轮 `_ensureWinTop`(签名含 lastRid)逐轮重读出新表顶 → 与上次实探落盘的去重缓存假失配(issue 26-11-19-0258, 取证 atlas 182.5→178.5, prism 恒 173.734375 幸免)。
- **判别**: 探针包装去重函数记录「本拍签名 vs 缓存签名」逐因子对比, 失配因子若是不随用户交互变化的布局读数即本坑; 旁证 = 冻结均值/键集/EST_H 两皮肤对称而探测数不对称(排除估算面)。取证现场: `commands run dev.e2e-perf-serial -- e2e/perf.spec.mjs -g "A/B 埋点"` 的 off 侧 gBCR 分段读数。
- **处置**: 把布局读数从签名剔除, 只留陈旧性驱动因子(滚动几何 sy/vh、规模 n、宽度代 _winResize)。剔除前先查历史(`git log -S "<因子>"`)确认它不是针对某回归的 deliberate 守; 该读数原想承担的「外部布局位移」语义改由真正影响面接管(zoom 有函数体内守卫; 字体交换的出窗修正由滚驱动的 sy 变化覆盖)。
- **守阵**: `tests/unit/test_webui_static_dom_page_layout.py::test_frontend_outgoing_rowh_reprobe_guard`(断言签名不含 _winTop/viewMode); 行为面 `e2e/perf.spec.mjs` A/B off 侧 gBCR 两皮对称(修后 prism 34 / atlas 35)。

**Refs:** memory-bank/issues/26-11-19-0258-perf-webui-rowwin-reopen-reprobe-excess.html
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
