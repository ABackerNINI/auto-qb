# 26-10-21-webui-css-rule-family-shared — 三皮肤 CSS 四规则族收敛进共用层(issue 26-10-20-2231 认领修复)

**Status:** In Progress
**Added:** 2026-10-21
**Updated:** 2026-10-21
**Summary:** 认领并修复 issue 26-10-20-2231(三皮肤 CSS 规则族互克隆): 逐字节相同的四族规则(qb-tabs / drawer-tabs / 弹窗语义配色分级 / HR 表① 件)从三份皮肤 CSS 收敛进 `shared/console_hub.css` 单点(四族共 43 条规则, 搬 35 条, 余 4 条是差异底形的色义修饰与差异绑成族)/ 三皮肤合计净减 162 行(共用层 +96); 三皮肤**真差异**(drawer-tabs 激活态令牌 / HR 徽章底形与副行字体)按 issue 口径留皮肤内并在原位注明。守阵判据从「皮肤聚合」改为「生效面(聚合 + shared)」(`_ui_css_effective`), 并新增「底形族不许并进共用层」的反向断言。等价性: 收敛前后生效规则表 59 条逐条同;全量与 e2e 双绿(数字见 kb.baseline)
**Topics:** webui-css-rule-family-shared
**Refs:** memory-bank/issues/26-10-20-2231-refactor-fe-css-rule-family-dup.html

## 原始请求

1. 「认领并修复: `memory-bank/issues/26-10-20-2231-refactor-fe-css-rule-family-dup.html`」——
   用户显式指派认领(create-issue skill 要求的「用户指派」口径), 同时授权修这一件。
2. 开工同步 `my-commit-flow.sync`: 已同步 `64f20d86`。
3. 收尾口径按 AGENTS.md: 全量测试 + 真浏览器冒烟 + 基线切片 + 坑档 + 主题文档回写。
   用户**未**说「提交」, 故本轮不 commit / 不 push。

## 思考过程与决策

**取证(改前)**: 按 issue 给的判据用脚本逐条比对三皮肤聚合的规则体(剥注释后按顶层规则块解析),
结论比 issue 的描述更精确 —— 四族里**绝大多数逐字节同, 少数是真空差异**:

| 族 | 规则数 | 逐条同 | 真差异 |
|---|---|---|---|
| qb-tabs | 4(+2 挂点胶水) | 4 | — |
| drawer-tabs | 3 | 2 | `.active` 令牌: atlas/console `--accent` vs prism `--accent-hi/--accent-line` |
| 弹窗语义配色分级 | 11 | 11 | — |
| HR 表① 件 | 22 | 19 | `.hr-vsrc` / `.hr-pres` 描边(prism `--border-soft`) / `.hr-sub` 字体(prism `--font-mono`) |

**决策 1 · 落点**: 不新建 shared 文件, 追加到 `shared/console_hub.css` 尾段。理由: ①三份 `index.html`
里 console/prism 的 shell 已卡满 212 行 cap, 新增 `<link>` 要动 cap 与守阵, 收益不抵成本;
②该文件事实上已是共用层(`.kb-cursor` / `.ctx-custom-*` / `.aq-tip` 都住这里), 只是文件头还写着
「设置页样式系统」—— 追加一个自述边界的尾段比另起一份更小。③三皮肤都挂它且排在各自 CSS **之后**,
级联序天然就是收敛点, 不需要 `!important`。

**决策 2 · 搬什么**: 只搬**逐字节相同**的; 有差异的按 issue「三皮肤确实有视觉差异的规则留在皮肤内」
留在原地并写清差异事实。刻意**成组**搬(弹窗语义分级 ①②③④ 连注释整组搬; HR 徽章底形族 base +
色义修饰整族留) —— 拆散后各自的特异性论证(如 `:where()` 压到 0-2-0 靠源序胜出)就读不懂了。

**决策 3 · 守阵怎么办**: 原守阵断言「三皮肤各自的 CSS 聚合里都有 X」, 收敛后恒红; 直接改成
「共用层有就算过」又会放过「某皮肤真漏了」。正解是加 `_ui_css_effective(ui)` = 皮肤聚合 + shell 挂的
shared CSS(link 序) —— 判据落在**该皮肤实际吃到的级联面**上, 语义仍是「三皮肤成对」。
另补反向断言: 徽章底形族必须留在各皮肤自己的 CSS 里(真差异不许被共用层顺手抹平)。

**决策 4 · 等价性怎么证**: 不信人眼。脚本对收敛前后各现算一次「生效规则表」, 逐条比 selector→body,
并查生效表内有无重复声明 —— 全等才继续。再叠 `test.full` + `dev.e2e` 双绿。

## 实现计划

1. 取证: 脚本解析三皮肤聚合, 逐族逐条比对规则体, 分出「同 / 异」两列。
2. 落共用层: `shared/console_hub.css` 追加尾段(A qb-tabs / B drawer-tabs / C 弹窗语义分级 / D HR 表① 件)。
3. 清皮肤: 三皮肤逐条删同族规则, 原位留指针注释(留什么 / 为什么留)。
4. 守阵改造: `_ui_css_effective` + 三处断言改量生效面 + prism 两文件拆分的钉法改为「共用层持有」
   + 新增底形族反向断言。
5. 等价性: 收敛前后生效规则表逐条比对 + 生效表重复声明检查。
6. 红验: ①删 atlas 底形规则 → 新断言必须红(实测红了); ②删共用层过滤栏规则 → 共用层断言必须红(实测红了)。
7. 验证: `test.full` 全绿 + `dev.e2e` 全绿。
8. 收尾: 基线切片 / 坑档(断言子串命中 + 守阵量程) / `conventions/webui.md` 回写 / issue 置 Done。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|

| S1 | 取证: 三皮肤四族逐条比对(同/异) | Done(2026-10-21) |
| S2 | 共用层尾段落盘(35 条规则) | Done(2026-10-21) |
| S3 | 三皮肤删同族规则 + 指针注释 | Done(2026-10-21) |
| S4 | 守阵改量生效面 + 底形族反向断言 | Done(2026-10-21) |
| S5 | 等价性自证(生效规则表逐条同 / 无重复声明) | Done(2026-10-21) |
| S6 | 红验两支 | Done(2026-10-21) |
| S7 | `test.full` + `dev.e2e` | Done(2026-10-21) |
| S8 | 收尾回写(基线 / 坑档 / 主题文档 / issue Done) | Done(2026-10-21) |

## 进度日志

### R0 · 立档 (2026-10-21)

- 认领 issue 26-10-20-2231 并一轮修完(用户指派「认领并修复」)。
- 四族 43 条规则里 35 条收敛进 `shared/console_hub.css`(余 4 条色义修饰与差异底形绑成族留皮肤内); 三皮肤净减 162 行(共用层 +96, 全仓净 −66 行)。
- 三皮肤真差异留原地并注明: `.drawer-tabs button.active` 令牌、`.hr-vsrc`/`.hr-pres` 描边、`.hr-sub` 字体。
- 守阵新增 `_ui_css_effective`, 三处断言改量生效面; 新增「底形族不许并进共用层」反向断言, 两支红验实测。
- 等价性: 生效规则表 59 条逐条一致, 无重复声明; `test.full` 与 `dev.e2e` 双绿(数字见 kb.baseline)。
- 踩坑两条已回写 `pitfalls/testing/assertions.md`: ①`assert ".a .b" in css` 会被 `.a .b.mod` 子串命中(红验假绿);
  ②CSS 收敛后「皮肤聚合」不再是「生效面」。

- 2026-10-21 03:41 认领并修复 issue 26-10-20-2231: 三皮肤逐字节相同的四族 CSS 规则(35 条)收敛进 shared/console_hub.css 单点(三皮肤合计 −324 行), 三皮肤真差异(drawer-tabs 激活态令牌/HR 徽章底形/副行字体)按口径留皮肤内并原位注明; 守阵新增 _ui_css_effective 改量生效面 + 底形族反向断言(两支红验); 等价性=生效规则表 59 条逐条同; test.full 与 dev.e2e 双绿
