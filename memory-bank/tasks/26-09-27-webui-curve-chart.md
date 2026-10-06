# 26-09-27-webui-curve-chart — WEBUI 限速曲线预览图重构(按流量比例 + 末档∞封顶 + 悬停修正)

**Status:** Done
**Added:** 2026-09-27
**Updated:** 2026-09-28
**Summary:** 用户报预览图三宗罪: 各档等宽不反映真实流量长度、悬停映射错位、图宽度不对。重构 `_buildCurveChart`: X 轴改**按各档实际流量长度比例分段**(取代 SPD-02 等宽), 末档与后端语义一致(`curves.py` X ≥ 末档下限后一直沿用末档速度, 末档阈值不改变速度函数)显示为 **∞ 区且占宽 ≤30%**(仅 1 档时独占全宽), 有限档分摊其余 70%; 末档阈值不再出现在几何里(无刻度/参考线)。悬停换算按 SVG 实际渲染缩放(letterbox 安全), tooltip 用真实像素定位; 根因之一是共享 `console_hub.css` 残留 `height:128px` 以特异性压过主题 aspect-ratio 把图压扁 —— 已删。流程按用户要求「先做模板调整好再应用」: 独立模板 5 用例浏览器实测全部验收点后, 再移植进真实代码并用真实 config_editor.js + vendor Vue 集成冒烟(含故意压扁容器的悬停回归用例)。test.full 1752 passed + 3 skipped / 91%, 与前基线持平零回归。
**Topics:** webui-curve-chart
**Refs:** resources/curve-chart-template.html, resources/curve-chart-smoke.html

## 原始请求

> WEBUI重构限速曲线预览图，当前的预览图每个阶长度一样是不正确的，要按长度显示，但为了避免最后一阶占太长导致其他阶看不清，最后一阶显示为无限（与实际代码处理一致），但占用宽度不得超过30%，目前的图与鼠标交互也不正确，宽度也不对。先做个模板，调整好后再应用

## 思考过程与决策

- **D1 语义对齐后端(读码定案)**: `core/curves.py` 档位语义「阈值是区间上限, X ≥ tn → vn(末档延续)」的**等价实现**是「返回第一个 threshold > X 的档位速度; 不存在则返回末档速度」⇒ **末档阈值 tn 不改变速度函数**(vn 覆盖 [t_{n-1}, ∞)), 速度函数只由 t_1..t_{n-1} + v_1..v_n 决定。所以「最后一阶显示为无限」不是近似, 是精确语义; 末档阈值不再画刻度/参考线, x 轴刻度 = 0 + 有限断点 + ∞。
- **D2 宽度分配**: 末档 ∞ 区固定占图体 30%(n ≥ 2; n=1 时整图即 ∞ 独占全宽 —— 30% 上限的目的是"防其它档被挤没", 只有一档时无此问题), 其余 n−1 个有限区间按流量长度比例分摊 70%: `x(t) = PAD_L + t/t_{n-1} × 0.7×usableW`。X 刻度相邻标签 <46px 时省略(虚线参考线仍画), 防比例化后近断点标签重叠。
- **D3「宽度不对」根因是 CSS 特异性**: 模板类 `class="ce-chart hb-chart"`, 共享 `console_hub.css` 的 `.hb-chart svg { height: 128px }`(0,1,1)压过主题 `.ce-chart-svg { aspect-ratio: 560/210 }`(0,1,0) ⇒ SVG 元素 100%×128px, viewBox 等比居中缩放(letterbox), 绘制区只有容器 ~61% 宽 —— 图"看着窄"且旧悬停换算(假设铺满)整体错位。删该残留规则(svg 尺寸统一由主题 `.ce-chart-svg` 决定)。
- **D4 悬停修正双保险**: ①几何换算按 `scale = min(rect.w/vb.w, rect.h/vb.h)` + 居中偏移, CSS 怎么改都映射正确; ②tooltip 位置用 SVG rect 相对容器的偏移还原成真实像素百分比(旧版用 viewBox 百分比, 受容器 padding/letterbox 影响)。∞ 区悬停显示「累计流量 ∞」+ 末档速度。
- **D5 先模板后应用(用户指定流程)**: 独立单文件模板(dark 主题)承载 5 个用例(均匀三档/末档阈值巨大/单档/六档悬殊/含 0 档)+ 可编辑档位表 + 测量条(每档像素宽与占比)+ 容器宽度滑杆 + 旧版等宽对照开关; 浏览器实测(截图 + 程序化 mousemove + 手工独立期望值核对)全部通过后才移植。
- **D6 移植验证不动真机**: `dev.run` 需真实 qB 且可能与生产实例抢 state.json, 不跑; 改用「真实 config_editor.js + vendor Vue + 真实形状 YAML 树」的集成冒烟页(渲染 + 悬停 + 故意压扁容器的旧 bug 场景回归), 悬停期望值手工独立推导(如 viewBox x=120 → 第2档/37.8GiB/12MiB/s, 旧算法同点会答第4档)。
- **D7 顺手正名**: 旧 note 文案「最严 ${maxS}」语义反了(maxS 是纵轴上限, 限速最小才最严), 改「纵轴上限」。

## 实现计划

1. 读码: 前端几何 `_buildCurveChart`/`cfgChartHover`/三主题 `.ce-chart-*` CSS/共享 `console_hub.css`; 后端语义 `curves.py` docstring。
2. 独立模板 `resources/curve-chart-template.html`(纯函数区与应用同构) → 浏览器实测迭代。
3. 应用: `config_editor.js` 两函数重写 + `settings-detail.html`(∞ 水印 text + 图例文案) + 三主题 CSS(`.ce-chart-inf-mark`) + `console_hub.css`(删压扁规则)。
4. 集成冒烟 `resources/curve-chart-smoke.html` → test.full + 收尾。

## 子任务状态表

| 子任务 | 状态 | 说明 |
|---|---|---|
| 后端语义确认(末档延续/末档阈值不改变速度函数) | Done | curves.py:15-19 |
| 独立模板 + 5 用例浏览器实测 | Done | 比例/∞30%/悬停/标签避让/宽度滑杆全过 |
| 应用到 config_editor.js + 模板 + CSS | Done | 另修 `.hb-chart svg` 压扁残留 |
| 集成冒烟(真实 JS + Vue, 压扁回归用例) | Done | 旧算法会答错的探针点新代码答对 |
| test.full + 基线切片 + kb 回写 | Done | 1752 passed 零回归; 坑入 pitfalls/web-ui/svg-chart-mapping.md |
| 真机设置页肉眼走查 | Open | 冒烟页已覆盖真实 JS 路径; 用户下次开设置页顺眼一扫即可 |
| 曲线标题栏整栏可点折叠 + 图标指示(09-28) | Done | 删「收起/展开」钮; 周期输入框/删除钮 @click.stop; `#i-chevron` 旋转指示; 光标修进 `.hb-curve-hd` |
| 「添加档位」与「下载档位」间距(09-28) | Done | 6px → 18px(`.hb-tier-add` margin-bottom 12px), 浏览器实测 |
| 设置页行内「?」按钮语调色对齐选项(09-28) | Done | xtpl 挂 `hubToneOf` 类 + console_hub.css 两变体; danger 实测边框/发光/底/字全红 |
| 「?」语调色补漏: schema tone 字段单点(09-28 二次) | Done | `Field` 加 `tone` 属性, `hubToneOf` 优先读它回落静态表; 删标两字段补红, CSS 零改动 |

## 进度日志

- 2026-09-27 21:38 全部落地: 模板实测 → 应用(6 文件) → 集成冒烟 → test.quick(1752 passed) → test.full(与上基线持平) → 收尾回写。未提交, 等用户「提交」指令。
- 2026-09-27 22:05 按用户反馈**取消 ∞ 水印**(大号半透明 ∞ 装饰字): 模板/冒烟页/`settings-detail.html` 元素、`_buildCurveChart` 的 infMark 字段、三主题 `.ce-chart-inf-mark` 规则全部撤除(死类连 CSS 一起清); ∞ 语义仍由 X 轴右缘刻度 + 图例「末档 ∞」表达。复验(浏览器 infMarks=0 + 渲染正常)与 test.quick 全绿。
- 2026-09-28 05:49 用户两条新反馈落地(同专题追加): ①曲线**标题栏整栏可点**折叠(删「收起/展开」独立钮), 状态由 `#i-chevron` 旋转指示(收起朝右/展开朝下, 160ms 过渡); 周期输入框与「删除曲线」`@click.stop` 防误触, 支持 Tab+Enter。坑: 可点手型光标既有选择器 `.hb-blk-hd.hb-sub-toggle` 命中不了 `.hb-curve-hd` —— `cursor` 直接写进 `.hb-curve-hd` 并实测。②「添加档位」→「下载档位」间距 6px → 18px(`.hb-tier-add` margin-bottom:12px)。③同轮附带: 设置页行内「?」按钮语调色对齐选项 —— `xtpl.html` 叶子行「?」挂 `hubToneOf(item)` 类, `console_hub.css` 加 `.hb-ask.important/.danger` 变体(静息描边 `--tone-line` 与输入框同配方, hover/打开整组转语义色)。验证: dev.harness 桩 + 真浏览器逐项量测(折叠/图标/键盘/间距像素/?「on」态全红), test.full 见基线 26-09-28。
- 2026-09-28 17:38 用户报「?」语调色**仍有遗漏**(同专题三次追加): 站点「删除标签格式」(`trackers.<站点>.remove_tags`)与自动化「彻底删除标签」(`delete_tags`)仍中性灰。根因: 语调取值只查前端 `HUB_TONE` 静态表, 动态路径(站点级)字段进不去表, 顶层 `delete_tags` 也不在表里。修法: schema `Field` 加 **`tone` 属性**(破坏性字段显式声明, 与 `risk` 文案解耦 —— 带 risk 不全是危险, "需重启"类只写文案不标), `config_hub.js` 的 `hubToneOf` 改为 `field.tone` 优先、静态表回落; 两个删标字段标 `tone="danger"`。CSS 零改动复用 eb57595 的 `.hb-ask.danger` 变体。附带: 两字段行条纹由 warn 黄转红(`hubRowClass` 按 tone 判 danger)。验证: 桩服务 + 真浏览器量测 —— 两行静息描边红 45%/on 态字+底+发光全红/弹层正常, 普通行(域名)中性灰不变, 静态表老键(qbittorrent.password)回落正常; test.full 1820 passed / 3 skipped(基线 26-09-28-1738)。
