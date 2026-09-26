# 26-09-26-webui-hr-popup — HR 悬停弹窗(做种时长/来源徽标 hover popover, T3 定稿)

**Status:** Done(落码+冒烟+提交轮完成, 随本提交入库)
**Added:** 2026-09-26
**Updated:** 2026-09-26 08:20
**Summary:** 把做种时长单元格的原生 `title`(hrDurTitle 一大段文字)换成**悬停小弹窗**。三版候选模板(共用同一份演示数据与页面骨架, 只有弹窗本体不同): T1 档案卡(逐行对账) / T2 结论卡(结论带+hero) / T3 进度仪表(双轨对照) —— 用户定稿 **T3** 并精修**零冗余**(来源章/考核中章移除、站点轨去数值端点、数值条仅站点侧值、角标只在结论没说时出现)。设计令牌逐字照抄两套 UI 真实 token(atlas :root 与 prism themes/*.css), prism 区可切 ocean/galaxy/frost 验证主题自适配。模板已入库(`plans/26-09-25-2043-*-t3-progress-ledger.html`); **落码 Done**(2026-09-26 07:18): shared/hr.js 弹窗数据组装/调度/定位单点 + 6 处绑定换 mouseenter 触发 + 弹窗单例 teleport 到 body + 两套 CSS(z-index 140) + 守阵改写; 冒烟 8 档位内容矩阵 + 交互 + 五主题全过 0 报错。**提交轮 Done**(08:20): 同步路径合并远端 5 提交(至 1905d6d), baseline.md 冲突按切片化新约迁移, 合并树重测 1666 collected / 1665 passed(TOTAL 92%), 随本提交入库。
**Topics:** webui-hr-popup
**Refs:** memory-bank/plans/26-09-25-1823-plan-webui-hr-safety-display.html, memory-bank/plans/26-09-25-2043-plan-webui-hr-popup-t3-progress-ledger.html

## 原始请求

> 当前的展示方案不够直观, 特别是 tooltip 一大段文字很难一眼看清, 需要优化, 想法是做成一个小弹窗, 鼠标移到做种时长或"在线"/"本地"上时显示, 弹窗继承各UI风格, 小巧精美, 先做3版模板, 选择之后再改代码

后续迭代指令: ①已达标/未达标/已免罪是考核期已过的终态; ②未达标独立醒目红色(不能是绿); ③删「义务未了」、删 A/B/C 档描述、「不能删」对未达标不符合实际; ④「进修t3, 移除冗余信息, 比如"在线"有多个, "考核中"也有多个」→ T3 定稿。

## 思考过程与决策

- **共用 fixture 保证可比**: 三版模板共用同一份 8 行演示数据(R1 考察中/R2 已达标/R3 未达标/R4 本地兜底/R5 策略/R6 超龄豁免/R7 未核实/R8 无HR) 与页面骨架(header + atlas 区 + prism 区含主题切换 + 七张常显样张 + 实现说明页脚), 只允许弹窗本体不同 —— 横向对比才公平。
- **令牌逐字照抄**: 弹窗表面语言对齐两套 UI 既有浮层先例(`.ctx-menu`/`.speed-pop`: bg-card + border-strong + shadow), 色值全部取自真实 `:root`/`themes/*.css`, 模板内零散写色值(prism 区只引用 var(--*)) —— 落码时 CSS 规则可平移。
- **三方向分核心**: T1=信息最全的逐行对账单; T2=1 秒判断(档位大词+hero 单焦点); T3=时间进度可视化(本地 6px 主轨对照站点 3px 细轨)。用户选 T3。
- **零冗余规则(T3 精修定稿)**: 结论短语已含来源(在线·/本地·/策略·)与进行中状态(考察中) → 来源章与「考核中」章不渲染, 生命周期 chip 仅终态标「已结束」; 站点细轨不带数值端点(角标承载); 角标只在结论没说时出现(还需 X / 考核期已过 / 已超出 X); 数值条仅站点侧值(本地值表格行可见), 无站点值整条不渲染; 状态徽记只说「无时长要求」。
- **交互规格**: 触发面 = .m-dur 单元格或 .hr-src 徽标; enter 120ms / leave 160ms 宽限, 移入弹窗不隐藏; position:fixed 锚定触发矩形, 优先上方不足翻下方, 横向夹取视口; ESC/滚动关闭; z-index 140(高于 ctx-menu 100 与 speed-pop 131)。
- **T2 模板踩坑(仅 mockup)**: `.demo-atlas .hp-card`(0,2,0) 压过 `.hp-fly`(0,1,0) 的 position:fixed → 弹窗按 relative 排进文档流"看似不出现"; mockup 无守阵, 靠截图评审才暴露。实装时 Vue 单例弹窗挂在 body 级容器即可避开同类特异性纠缠。

## 实现计划

1. ~~三版候选模板~~ (Done, T1/T2 留档不删) → 2. ~~T3 定稿 + 零冗余精修~~ (Done) → 3. **落码**(pending): `shared/hr.js` 弹窗数据组装/单例定位单点(消费 hr_safety* / hr_site_* / hr_reason, 前端零重算) + 6 处模板绑定(两 UI × 组内成员/种子页/明细)替换 `:title="hrDurTitle(m)"` + 两套 CSS 同值规则(浮层/箭头/双轨/数值条/生命周期章) → 4. 浏览器冒烟(双 UI × 三语境 × 主题切换) + baseline。

## 子任务状态表

| 子任务 | 状态 | 说明 |
|---|---|---|
| 三版候选模板 | Done | T1 档案卡 / T2 结论卡 / T3 进度仪表, 单文件可交互, 共用 fixture; Playwright 实测悬停/翻转/主题跟随 0 console 错误 |
| T3 定稿 + 零冗余精修 | Done | 用户选定 T3; 冗余清理六条见「思考与决策」; 计划文档 §8 修正3 |
| 落码 shared/hr.js | Done | 2026-09-26 07:18 —— hrPopData 数据组装单点(消费 hr_safety* / hr_site_* / hr_reason, 前端零重算; "none" 与无档位行不弹) + hrPopEnter/hrPopLeave/hrPopKeepOpen/hrPopHideNow 调度(enter 120ms / leave 160ms 宽限 / 移入弹窗不隐藏 / ESC·滚动·缩放即关) + _hrPopPlace fixed 定位(优先上方翻下方·横向夹取 8px·箭头指向触发中心·触发矩形为零视作悬停目标已消失); 定时器走模块级变量不进响应式; hrDurTitle 已删 |
| 落码 6 处模板 + 两套 CSS | Done | 2026-09-26 07:18 —— 6 处 `:title` 换 `@mouseenter="hrPopEnter($event, m)" @mouseleave="hrPopLeave"`; 弹窗单例 DOM `<teleport to="body">` 落两套 index.html(#app 尾部, 类名同份); CSS 成对(atlas style.css radius 10 / prism views.css radius-lg 8, z-index 140 高于 ctx-menu 100 与 speed-pop 131, hrpop-in 进场动画 + prefers-reduced-motion 降级); 守阵第②③段改写(触发 ×3 + teleport ×1 + hr-pop 成对 + z-index) |
| 浏览器冒烟 + baseline | Done | 2026-09-26 07:18 —— 冒烟页复用真实 hr.js/format.js/两套 CSS/真实弹窗 markup(fixture 8 档位); 8 档位内容矩阵全对(考察中还需角标+双轨 86%/14% / 已达标站点满格+已结束 / 终态未达标考核期已过+无站点轨 / 本地兜底已超出 / 策略还需 14天08时 / 超龄豁免盾徽记+已结束 / 未核实虚线盾 / 无档位不弹); 交互全过(宽限 100ms 仍开 600ms 关 / 移入弹窗不隐藏 / 滚动·ESC 即关 / 行间移动换内容 / 下翻上翻 / 视口夹取); prism 五主题全跟随(ocean/galaxy/frost/golden/orbit 含两亮色); 真实两页整页编译挂载 0 报错; 数字进 baseline.md |

## 进度日志

- **2026-09-25 20:43 (三版模板产出)** — 3 并行子代理各做一版, 父代理合并评审修 3 处(T2 fixed 被特异性覆盖 / 来源 chip undefined / T2 T3 缺 prism 样张), 截图全过。
- **2026-09-25 22:18–22:54 (语义修正联动 + T3 定稿)** — 终态语义/failed 红档/措辞修正落在 hr-safety-display 档案(联动改动); 用户选定 T3 并下达零冗余精修, 六条冗余全清(来源章/考核中章/轨端数值/已达标角标/本地值数值条/徽标去重), 计划文档记修正3。
- **2026-09-26 02:24 (收尾提交)** — 模板随本轮提交入库; 落码待下一轮开工(本档案续作)。
- **2026-09-26 07:18 (T3 落码 + 冒烟)** — 三项子任务全 Done。落码要点: ①`shared/hr.js` 增 hrPopData
  数据组装(token→内容映射: 身份层放行/未核实/未配时长→盾徽记; site_scope 站点 need 优先回落本地差值;
  site_unsatisfied→「考核期已过」+无站点轨; local 按本地差值出已超出/还需; 终态 chip 已结束 = 5 个终态
  src token), hrDurTitle 删除; ②6 处绑定换 mouseenter/mouseleave, 弹窗单例 teleport 到 body
  (prism 主题令牌挂 html[data-theme] 自动继承, 免拷贝); ③两套 CSS 同值规则 z-index 140; ④守阵第②③段
  改写(旧 :title 断言 → 触发/teleport/hr-pop 成对 CSS/z-index)。冒烟: 冒烟页复用真实产物 + 真实两页
  整页编译, 8 档位内容矩阵 + 交互 + 五主题全过、0 console 错误; test.full 1664 passed + 1 skipped
  (TOTAL 92%, ±0 条)。
  踩坑记录: IAB 自动化的 cua.move 不产 mouseenter、截图动作触发 resize(规格行为"缩放即关")会把弹窗
  关掉 —— 冒烟用合成 MouseEvent 驱动(与真实浏览器事件同级), 截图前注入 `.hr-pop{display:block!important}`
  样式表冻结(样式表 important 压过 v-show 内联样式)。
- **2026-09-26 08:20 (提交轮: 同步路径 + 合并树重测)** — 用户令「提交」。预检落后 5 提交且树脏 9 文件
  (重叠 6), 按「移出改动 → ff 合并远端 5 提交(至 1905d6d) → 施回」走: 7 文件干净施回, 唯一冲突
  baseline.md(远端 340e383 已切片化重写为口径文件) —— 按**远端自己的新规则**迁移: baseline.md 取远端版,
  本轮基线条目落 `baselines/26-09-26-0820-hr-popup-t3.md`(合并树重测 **1666 collected / 1665 passed +
  1 skipped**, TOTAL 92%, 与上一片 0802 持平 ±0 条)。远端 .bt 按钮收敛守阵(零残留/成对)与本改动无冲突
  (弹窗无按钮类)。合并树两页整页编译复验挂载正常。随本提交入库。
