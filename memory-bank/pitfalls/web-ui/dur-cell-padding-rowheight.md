# 做种时间格的 6px 底线占位 padding 会把有文案的行撑高

> 摘要: 做种时间格的 6px 底线占位 padding 会把有文案的行撑高
> 触发: 行高变高, 行高变大, 做种时间, 完成后行高, padding-bottom, dur-pad, 单元格撑高, grid 行高
**Refs:** memory-bank/testing/baselines/26-11-03-0224-webui-dur-pad-rowheight.md, memory-bank/testing/baselines/26-11-03-0252-e2e-skins-all-geometry.md

### `.m-pair.m-dur` 用 `padding-bottom` 给 HR 底线留位, 空单元格不撑行、有文案就撑高整行

- **触发**: 给做种时间格的 HR 下划线预留空间时, 把 `--dur-pad` 写成单元格 `padding-bottom`; 单元格空着时只有 6px 高(不撑行), 一旦有做种时间文案(完成瞬间 qB 就回 `seeding_time=1~2s`, 前端 `cellSeedingTime` 显示"0分钟"), 单元格总高 27.69px 超过其它文字格 22.05px, 整行从 43.05px 抬到 48.69px。观感 = 「下载中列表里, 种子完成一段时间后该行变高」; 用户的"下载速度消失/做种时间显示 1 分钟"只是同一轮刷新造成的相关性错觉(尾速与 60s 文案都不改变高度)。
- **判别**: 同一行 DOM 对比 —— 清空 `.dur-val` 文字后行高回落、填回即升高(差值 ≈5.64px); `getComputedStyle(.m-pair.m-dur).paddingBottom` 非 0 即为根因。别拿真机时间线当判据: 后台标签/无头页受 `polling.js` 的 `document.hidden` 守卫影响, `/api/state` 采样会停, 时间线不可信。
- **处置**: 单元格不加 padding, `--dur-pad` 只当线的下移偏移用: `.m-pair.m-dur { position: relative; --dur-pad: 6px; }` + `.m-dur .dur-body > .hr-line, .m-dur .dur-val > .hr-line { bottom: calc(-1 * var(--dur-pad)); }`。行底 10px 内边距足够容纳 2px 线身(实测线底距行底 5.19px, 成员行 2px), 不会被下一行裁切。四套皮肤(prism/atlas/console/flux)同名规则必须一起改。
- **守阵**: `tests/test_webui_static_skins_widget.py` 静态断言(规则体不得出现 `padding` + 线按 `var(--dur-pad)` 下移) + `e2e/views.spec.mjs` 几何守卫(同一行有文案/无文案行高差 ≤0.5px、`paddingBottom === '0px'`; 遍历 `SKINS_ALL` 四皮肤, 同一份断言体数据驱动)
- **复发**: 0
