# 2791 —— 流量图缺口斜纹配色修复基线

> 摘要: 用户报「WEBUI 流量图断线区域标注未落到正确的区域, 且其颜色几乎不可分辨」。诊断出**两症状同源**: 斜纹色误用装饰性发丝线令牌 `--hairline`(alpha 仅 0.05~0.08)再叠 `globalAlpha=0.5` ⇒ 有效不透明度约 3%, 深/亮底上**都**等于没画; 颜色不可见 ⇒ 无法判读落点, 被感知成"没落到正确区域"。**几何经代数证明 + 数值枚举 6 组 + 真浏览器 A/B 渲染确认与原式逐条线段恒等, 无缺陷**(原诊断"左移 H 像素"被实测证伪)。纯前端静态层改动(`qb_traffic_chart.js` + 5 个 CSS 令牌文件)与守阵补齐, Python 产品代码零改动 ⇒ 相对上基线 26-10-08-1016(2789+4)passed **+2**。
> 档案: (单会话小修, 未立档案 —— 见 activeContext 切片)
> 基线时间: 2026-10-08 11:30

**Refs:** memory-bank/activeContext/26-10-08-1130-webui-qb-traffic-gap-hatch.md,memory-bank/pitfalls/web-ui/canvas-hatch-token.md

## test.full 实测

- 分支: `develop`(工作树含本专题回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **2791 passed + 4 skipped, 0 failed, 35.30s, 覆盖率 TOTAL 99%**
  (16476 语句 / 162 未覆盖 / 5694 分支 / 146 partial; 门槛 98% 达标)
- 同树复测区间: 35.30s ~ 36.41s(回写前 / 回写后各一次, passed 与覆盖四项**逐位相同**)。
- 本专题守阵单跑: `uv run pytest tests/test_webui_static_dom_panel.py --no-cov -q` → **29 passed in 3.23s**。
- 回写件自检: `uv run pytest tests/test_memory_bank.py --no-cov -q` → **42 passed, 1 failed**
  —— 失败者 `test_kb_active_render_respects_byte_budget`(`ModuleNotFoundError: gen_active_recent`)
  经 stash 本件全部改动后**照样红**, 确认为**存量**环境问题(该生成脚本不在 import 路径内), 与本专题无关。
  措辞守卫 / 数字守卫 (`test_wording_guard_*` / `test_number_guard_*`) **全绿**。
- 相对上基线 [26-10-08-1016](26-10-08-1016-mutants-config-validator-strings.md)
  (2789 passed + 4 skipped, 语句/未覆盖/分支/partial 同口径 16476/162/5694/146):
  passed **+2** / 语句 **±0** / 未覆盖 **±0** / 分支 **±0** / partial **±0**。
  - 口径说明: 本专题**未新增测试函数** —— 守阵加在原函数 `test_frontend_qb_traffic_yaxis_and_annotation` 内部(§5b 静态锚 + 一块 node 配色电池)。故 passed +2 来自**其间其它会话并入的守阵**; 本专题的机械贡献是同一函数内断言条数增加(不体现为 passed 计数)。
  - 上基线 26-10-08-1016 自身带 2 failed(存量守卫违规: activeContext 里手抄裸 passed 数字, 经用户裁定「暂时不用管」); **本轮 0 failed** —— 那两条守卫已在其间被清理, 故 2789+2(failed 转 passed 的 2 条) + 0 = **2791**。
  - 4 skipped 为 Windows 侧 POSIX 专属存量。
- 旁证(非 pytest): 真浏览器五主题全皮肤渲染(`tmp-analysis/allskins.html`, 脚手架已清理)确认缺口斜纹在深色三主题(ocean/galaxy/orbit)+ 亮色两主题(frost/golden)下**均清晰可见**且落在缺口区(06:50–07:20 两桶); A/B 双面板(`ab.html`)确认新旧两式斜纹位置**逐条相同**。

## 本专题面要点(非 pytest)

- **症状分离判定**: 「位置错 + 看不清」同时出现时, 先做**几何 / 配色分离验证** —— 几何用代数化简 + 逐条线段比对, 配色用实跑取真值看 alpha; 不互相脑补(本次反面教材: 一度据源码推断"左移 H 像素"并自认被复现"证实", 实为误读测量含义 —— 量的是线段左端并集而非线段集合)。
- **证伪的诊断不得留成守阵锚**: 曾设 `assert "let x = xa - H" not in gb` 类负锚, 该"缺陷"不存在 ⇒ 假锚, 已删除; 整块几何电池替换为配色电池。
- **令牌语义**: `--hairline` = 装饰性 1px 发丝线(alpha 0.05~0.08)。面积底纹 / 高对比标注**必须单列专用令牌** `--qb-gap-hatch`; 用色处 `tk.gap || tk.grid` 回退链绝不落回极低 alpha; 去掉多余 `globalAlpha` 折半。
- **令牌成对纪律**: `--qb-gap-hatch` 在 atlas / console / prism 三皮肤 + prism 五主题(ocean/galaxy/orbit/frost/golden)各自定义, 缺一个 = 那套皮肤下不可见; 亮主题(frost/golden)**必须用深墨色**而非白色(镜面缺陷)。
- **守阵的数值下界**: 除静态字符串锚外, node 配色电池做 **令牌 alpha 量级 >= 0.15** 的数值判定 —— 静态锚可能被后人同步改掉, 数值下界不会。

## 对照判据(后续沿用)

- 以本切片(2791+4 / 16476 / 162 / 5694 / 146)为对照点: 预期 passed 只升不降、未覆盖 / partial 不升。
- 本专题**未新增测试函数**, 故后续若有人误以为"改守阵必须 +1 passed"会算错账 —— 加断言到既有函数里不涨计数。
