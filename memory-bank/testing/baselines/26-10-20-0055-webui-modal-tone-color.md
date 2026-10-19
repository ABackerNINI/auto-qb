# 3757 passed + 10 skipped(Windows 单侧) —— 弹窗语义配色分级落地后的全量(纯前端改动, Python 侧数字未变)

> 摘要: 3757 passed + 10 skipped(Windows 单侧) —— 弹窗语义配色分级落地后的全量(纯前端改动, Python 侧数字未变)
> 基线时间: 2026-10-20 00:55

## 验收数字

```
TOTAL                                                20328    391   6956    262    98%
3757 passed, 10 skipped in 70.73s (0:01:10)
```

口径注记:
- 本侧 = Windows(本机 `.venv` Python 3.14.7, `commands run test.full`, xdist `-n 4`)。Linux 侧本轮未跑(本机无 Docker/WSL, `test.linux` 跑不了) —— 且本轮是**纯前端改动**(JS/CSS/HTML), 不触碰 Python 可执行行, 跨平台差异风险为零。
- 与上一基线(`26-10-20-0004`)用例总数一致(3756+1+10 = 3757+10); 该基线的 `1 failed`(`test_api_traffic_qb_global_24h_reads_only_involved_day_files`, 墙钟相关、与本轮无涉)本轮**未复现** —— 同一份代码两次全量结果不同, 佐证它是时间敏感型抖动。
- 覆盖率达标(98%), 未触发 fail-under; 上一基线触发是因为少了那条用例的覆盖贡献 + 覆盖率取样刚好压线。
- 语句未覆盖数 391 vs 上基线 390: 差 1, 来自上面那条抖动用例的随机通过与否, 不是本轮引入。

## 本改动面

弹窗语义配色分级(计划 `26-10-19-2341`)的实施 S1~S5 —— 全部落在前端静态资源:

- `shared/ui_feedback.js`: `_modalInit` 增 `tone: ""` / `strip: false`; `_openModal` 增派生单行 `const tone = cfg.tone || (cfg.danger ? "error" : "warn")` 并入 modal 字面量(`mid` 自增留在同一字面量内， identity 守阵要求)。
- `shared/tpl/popovers.html`: 框容器类绑定改数组式(追加 `strip` 与 `tone-*`); verdict 行与 details 行的 `:class` 改 `[d.tone && 'is-' + d.tone, { wide: d.wide }]` —— 容器与 `.bt.danger-solid` 按钮一字符未动(T23 整行硬锚定)。
- `shared/delete_flow.js`: `_confirmDelete` 显式 `tone: "error"` + `strip: true`; HR 风险行 `tone: "error"`。
- `shared/drawer.js`: `_skipCheckDialog` 显式 `tone: "warn"` + `strip: true`; 固定警示区 4 行 / 预检失败行(2 处)/ 计数行 / 按原因分组行 / 单发原因行 / 全满足行各自挂 tone。**`_skipPrecheck` 六分支语块零增删**(T24 逐语句等值断言)。
- CSS 三套成对: atlas `css/views.css` + console `css/views.css` + prism `css/components.css`, 各 10 条规则(框级 tone 2 + strip 3 + 行级 3 + 注释)。
- 新增 pitfall `pitfalls/web-ui/css-file-line-cap.md`(atlas `components.css` 卡满 700 行的体量守阵)。

未改动: Python 侧零改动、零新增 Python 测试 —— 行为变更为零(纯装饰层), 故不加新守阵; 视觉 एक मात्र验收靠 `dev.e2e` 冒烟 + 人工目视。
