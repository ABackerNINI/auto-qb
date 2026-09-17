# TASK012 — UI 组件库 20 式 (设计风格库落地为可挑选的组件库)

**Status:** In Progress
**Started:** 2026-09-17
**Owner:** 主线 (单会话完成产出与自检); **未提交 git** —— 剩用户挑选与按需迭代
**Deliverable:** [`resources/ui-component-libraries/modelscope.dsv4.1flash/`](../../resources/ui-component-libraries/modelscope.dsv4.1flash/README.md) (22 文件: 20 套组件库单页 + 挑选索引 `index.html` + 目录 `README.md`)

## 原始请求

> 根据本项目中的UI设计相关skills, 设计20套不同风格的组件库, 保存在docs/下合适的目录中, 要求每套风格统一, 包含常用组件, 包含风格介绍方便扩展, 需要可直接展示方便挑选

## 思考过程与决策

- **风格来源取"本项目 skill"的字面答案**: 本项目 UI 设计相关 skill 中, [.agents/skills/aesthetic-preset-library/](../../.agents/skills/aesthetic-preset-library/SKILL.md) 正好定义 **5 大流派 × 20 位设计师/工作室** 的风格库 —— "20 套" 与之一一对应, 因此每套 = 一个 preset (01 Pentagram … 20 Neo Shen), 不做自创风格。
- **"可直接展示"= 单文件自包含 HTML**: 沿用项目既有 docs/*.html 交付惯例 + frontend-design/OUTPUT_RULES 的硬约束 —— 单文件、无外链(系统字体栈)、无 emoji 装饰(内联 SVG 图标)、可双击打开、离线可用。
- **"方便挑选"= 索引页做实时缩略预览**: `index.html` 用 20 个 `iframe` 真实渲染缩略(非截图) + 按流派筛选 + 速查表; 预览用固定 340×250 视窗居中裁剪(窄屏不留空带)。
- **"每套风格统一"与"20 套能横向对比"的取舍**: 20 套共用**同一套语义化组件标记**(按钮/表单/数据/表格/导航/反馈/组合), 视觉语汇由每套独立覆写同名类。这样对比的是风格差异而不是结构差异 —— 也便于用户选定后直接拿 CSS 落地。
- **生成方式**: 临时 Python 生成器(共享骨架 CSS + 组件标记 + 每套 :root 变量与覆写 CSS), 产出后**删除生成器**; 交付物以 HTML 为唯一事实源, 扩展方式写进每页"扩展指南"与目录 README(复制文件 → 换 `:root` 变量块)。
- **内容纪律**: 示例数据全部取自本项目领域(站点/Tracker/种子/规则/限速/跳检)并标注"示例"; 不编造统计与评价(遵循 OUTPUT_RULES 的反 slop 与"不捏造数据"规则); 风格预设与 craft 黑名单冲突时按仲裁规则以 preset 明示优先(如 iA 的 system-ui、16 号的单色 FUI)。

## 实现计划

1. 读 UI 设计相关 skills 与项目上下文 → 定风格清单与目录 (`docs/design/ui-component-libraries/`, 后按用户要求迁至 `resources/ui-component-libraries/modelscope.dsv4.1flash/`)。
2. 写共享骨架: 结构层 CSS(token 驱动) + SVG 图形生成器(等高线/粒子/递归细分/手绘线稿/节点图/开本叠压) + 组件标记(20 套共用)。
3. 写 20 套风格定义: 每套含风格介绍(哲学/特征/关键词/灵感来源/标志性做法)、**提示词 DNA**、设计变量(色板/字体/形状刻度/token 清单)、扩展指南(四步法 + 应做/禁止)、专属 CSS(:root 覆盖 + 组件覆写 + 签名细节)。
4. 产出 21+1 文件并做文本层自检(占位符残留/转义泄漏/结构完整性)。
5. 浏览器渲染自检(整页缩略 + 区块细节 + 功能探针 + 390px 断点)并修复发现的问题。
6. 按 memory-bank 规程收尾(立档/索引/焦点/陷阱/测试)。

## 子任务状态表

| # | 项 | 落点 | 状态 |
|---|----|------|------|
| 1 | 20 套风格定义 + 共享骨架生成器 | 临时生成器 (产出后删除) | ✅ |
| 2 | 20 套组件库单页 + 挑选索引 + 目录 README | `resources/ui-component-libraries/modelscope.dsv4.1flash/` | ✅ |
| 3 | 文本层自检(占位符/转义/结构/括号平衡) | 21 文件全绿 | ✅ |
| 4 | 整页缩略图复核(20 套 + 索引) | 4 张拼版逐页过 | ✅ |
| 5 | 区块细节复核(组件区 ×10 套 / 变量区 ×3 套 / 索引 ×4 宽度) | 截图逐张过 | ✅ |
| 6 | 功能探针(tab 切换 / dialog 开合 / 开关) | `--dump-dom` 探针 3 套全绿 | ✅ |
| 7 | 移动端 390px 断点 | iframe@390 复核 | ✅ |
| 8 | 缺陷修复(见下表) | 已全部回写并重新生成 | ✅ |
| 9 | 用户挑选与按需迭代 | 待用户反馈 | 🚧 |
| 10 | 交付物迁址 (用户要求) `docs/design/` → `resources/ui-component-libraries/modelscope.dsv4.1flash/` | 22 文件搬迁 + 6 处引用修正 + `docs/design/` 移除 | ✅ |

### 自检发现并已修的缺陷 (7 项)

| # | 缺陷 | 根因 | 修法 |
|---|------|------|------|
| 1 | 部分风格按钮变体全变成主色(如 01 六个按钮全黑、09 次级不显黄) | 风格里 `.btn{background:...}` 直接属性覆盖 → 变体依赖的 `--btn-bg/--btn-ink` 变量被压掉 | 全库改变量制: `.btn{--btn-bg:…;--btn-ink:…}` + 基础层新增 `--btn-hover-ink` 承载悬停文字色(涉及 01/03/06/07/09/13/14/15/16/18/19/20) |
| 2 | 01 悬停时次级/描边按钮可能白底白字 | 风格 `:hover` 直接写死颜色, 与变体悬停色冲突 | 悬停色改由 `--btn-hover/--btn-hover-ink` 承载 |
| 3 | 18 单选钮渲染成方块(与复选钮无法区分) | 风格统一 `border-radius:0` 时把 `.radio .box` 一起重置 | 单独恢复 `.radio .box{border-radius:50%}` |
| 4 | 18 开关选中/未选中区分度过低 | 选中态只改描边 | 选中态加米白底 |
| 5 | 13 错误态输入框与常态无差别(该风格 --bad 也是黑) | 单色风格里颜色区分失效 | 错误态改用虚线描边(`.field-err .input{border-style:dashed}`), 与"构造线"语汇一致 |
| 6 | 深色/渐变风格禁用按钮浑浊(渐变只降透明度) | 禁用态仅 `opacity:.45` | 基础层禁用态加 `filter:saturate(.35)` |
| 7 | 索引页窄屏预览右侧留空带 | 预览用固定 scale, 卡片宽度随列数变化 | 预览改为固定尺寸容器(340×250)居中 + iframe 1300×958 @scale .2615 |

## 进度日志

- 2026-09-17: 单会话完成 —— 读 skills 与上下文 → 生成器与 20 套风格定义 → 22 文件产出 → 文本层/渲染层/功能/断点四轮自检 → 7 项缺陷修复并重新生成 → `uv run pytest tests -q` 实测 **996 passed, 2 warnings** (20.69s, 分支覆盖率 92%), 与 [testing.md](../testing.md) 基线一致(纯文档新增, 不动代码); 交付物未提交 git, 待用户挑选。
- 20 套风格编号与 aesthetic-preset-library 预设一一对应: 01 Pentagram / 02 Stamen / 03 Information Architects / 04 Fathom / 05 Locomotive / 06 Active Theory / 07 Field.io / 08 Resn / 09 Experimental Jetset / 10 Müller-Brockmann / 11 Build / 12 Sagmeister & Walsh / 13 Zach Lieberman / 14 Raven Kwok / 15 Ash Thorp / 16 Territory Studio / 17 Takram / 18 Kenya Hara / 19 Irma Boom / 20 Neo Shen。
- 2026-09-18: 按用户要求迁址 —— `docs/design/ui-component-libraries/` → `resources/ui-component-libraries/modelscope.dsv4.1flash/` (22 文件 `mv`; `docs/design/` 随之清空移除)。同步修正 6 处引用: 交付物 README 的 skill 相对链接(深度 +1)、`index.html` 页脚目录字样、[../README.md](../README.md) 路由表、[../activeContext.md](../activeContext.md)、[_index.md](_index.md)、本档案。搬后浏览器复核: 索引页 20 张实时预览正常(同目录相对路径不受影响)。
