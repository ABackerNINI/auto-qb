# 26-11-18-webui-curve-period-sort — 限速曲线自动按天数排序

**Status:** Done
**Added:** 2026-11-18
**Updated:** 2026-11-19
**Summary:** grilling 四轮 13 问拍板 D1-D12; S1-S5 全部落地(排序键 helper/后端两层/前端+e2e)+ S5 收尾(docs 单点回写/真机判定纯桩可验/全量绿见 kb.baseline)
**Topics:** webui-curve-period-sort
**Refs:** memory-bank/plans/26-11-18-0801-plan-webui-curve-period-sort.html

## 本篇只回答

本档案只回答「限速曲线自动按天数排序」专题的**推进状态与决策留痕**; 怎么修见计划件 §03/§04; 键序与行为的用户面单点在 `docs/configuration.md`「全局限速曲线」节「曲线排序」小节(S5 回写)。

## 原始请求

1. 「限速曲线自动按天数排序, grilling」—— 对该想法做拷问式设计评审。
2. 共识清单经确认后:「出计划然后提交」—— 计划入库 + 提交, 零实施。

## 思考过程与决策

- grilling 四轮 13 问(Q1-Q13)逐项拍板, 结论 D1-D12 全表见计划 §06。
- 关键转折一(落点): 事实取证推翻隐含假设 —— UI 渲染磁盘原始树而非解析模型(GET /api/config → read_tree), 无写回路径序列化解析模型, 仅 loader 排序到不了 UI → 定为 GET 路由 + loader + 前端三层(D4)。
- 关键转折二(改值时机): Q10 拍「前端新增定位插入」后, 编辑器事实浮出 —— period 字段逐键写树(traffic-card.html:181 @input) + 曲线列表 v-for 下标 key(traffic-card.html:169), 逐键重排会焦点行数据错写 → Q11 改判重排挂 @change 提交时机(D10)。
- 计划: memory-bank/plans/26-11-18-0801-plan-webui-curve-period-sort.html(已随 S5 收尾翻 Done)。
- 实施期结论(2026-11-18/19 三批): 排序键序的用户面文档单点 = `docs/configuration.md`「全局限速曲线」节「曲线排序: 按 period 自动排序」小节(S5 回写, D12); Python 单点 `core/curves.py period_sort_key` 与 JS 复刻 `config_editor_curve.js _cfgCurvePeriodSortKey` 注释双侧互指。评审实锤教训两条: ① `String()` 强转与 Python `str()` 不等价 —— 树内 period 为数组(如 `['DAY']`)时 `String(['DAY'])==='DAY'` 会误解析出 day 键, JS 侧必须 `typeof` 门拒绝非字符串(与 Python 抛 ValueError → D8 整段放弃对齐); ② e2e 首版注入布局对被测行为无甄别力(实现不接线也能绿), 返工加甄别面(blur 收口 + 非字符串守门子段)。
- 真机自检判定(S5, 依 `testing/real-machine.md` §00): **纯桩可验, 不落真机轨** —— 两类准入均不命中: ① 非「qB 真执行才成立」, 排序纯规范面, 运行时同方向多曲线取最严的合并与列表序无关, 不触任何 qB 执行路径; ② 非「必须碰真文件系统/进程/注册表」, 单测/Fake 树/e2e 桩服务全程覆盖, 桩数据对排序结论无失真(解析语义 BaseLoader 字符串标量可完整复刻)。

## 实现计划

见计划 §04: S1 排序键 helper(core/curves.py, 挂 normalize_period 旁) → S2 loader 排序 → S3 GET 路由展示树排序 → S4 前端两触发点(JS 键复刻/新增定位插入/改值 @change 重排/openCurves 身份跟随) → S5 文档回写 + 测试(pytest + e2e @fast) + 收尾 DoD。每步验收判据随计划表。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | core/curves.py 排序键 helper(ab9c756f) | Done |
| S2 | loader 排序(loaders.py 构造模型前)(ae108430) | Done |
| S3 | GET 路由展示树排序(解析失败整段放弃)(ae108430) | Done |
| S4 | 前端两触发点(JS 键复刻 + 新增定位插入 + 改值 @change 重排)(ae588e66) | Done |
| S5 | pytest + e2e(@fast) + docs 回写 + 收尾 DoD(2026-11-19 本批) | Done |

## 进度日志

### R0 · 立项 (2026-11-18)

grilling 四轮 13 问拍板 D1-D12(共识清单经用户确认)+ 计划 26-11-18-0801 入库 Open(S1-S5 待显式开工)+ 本档案立档; 零代码改动, 计划与档案随本专题入库。

- 2026-11-18 08:05 grilling 四轮 13 问拍板 D1-D12(共识清单经用户确认); 计划 26-11-18-0801 入库 Open(S1-S5 待显式开工); 档案立档; 零代码改动

### R1 · 实施 S1-S4 三批 (2026-11-18/19)

各批结论以提交信息为闸门键, 下列 `Review:` 摘要行照抄自各批提交 trailer(档案行是叙事); 实测数字只认 kb.baseline 基线切片。

- 2026-11-18 08:31 S1(ab9c756f) 排序键 helper: `core/curves.py period_sort_key` 按 D5 键序归一(day=(0,) < {N}D=(1,N) 按 N 数值 < month=(2,) 恒最后), 归一化复用 normalize_period, 非法值透传 ValueError 由调用方捕获放弃(D8 保守默认); 单测 5 条 + 测试计划 docstring 同步。Review: S1 排序键 helper+单测 · 62 行 · blocker 0 · 修 0 · 入池 0 · 检 2/2 · 基 a46175bd
- 2026-11-18 09:00 S2+S3(ae108430) 后端两层接线: loader 构造 GlobalSpeedLimitCurve 前排序(输入已过校验, 无放弃分支); GET /api/config 对磁盘原始树排序, 树形五层形状防御(isinstance 链)+ 任一 period 解析失败整段放弃原样返回(D8); 落盘收敛走被动(D7)不加启动迁移。首轮 3 发现(major 段非字典 500 / minor 断言不足 / nit 恒真测试)当场修完, 复评零新增; 顺带折入 S1 批转来的 2 条 nit(docstring 将来时 / 幂等测试期望序化)。Review: S2+S3 loader+GET 排序接线 · 166 行 · blocker 0 · 修 3 · 入池 0 · 检 3/3 · 轮 2 · 基 6763bf00 · 派发 2 · 分面
- 2026-11-19 01:53 S4(ae588e66) 前端层收口: JS 排序键复刻逐字对齐 Python(注释互指单点改现在时); 新增定位插入(D9, 等键排其后)+ 改值 @change 提交重排(D10, 禁逐键保下标 key v-for 焦点安全)+ 回车提交后 blur 收口(消灭重排后焦点框换条继续键入写错条目的残余面)+ 解析失败整段放弃(D11 与 D8 同策略); 大数 float64 与全角数字两处精度边界接受并注释实证(前端更保守, 保存一次后端归一自愈); e2e 新 spec 4 用例 x prism/atlas 双皮肤(含 blur 收口与非字符串守门甄别子段)。评审三轮: 首轮 3 发现(blur 焦点错写 minor / String 强转分叉 minor / 大数 nit)+ 次轮 2 发现(e2e 甄别力 minor / 全角数字 nit)全修, 末轮复评零新增。Review: S4 前端排序接线+e2e · 303 行 · blocker 0 · 修 5 · 入池 0 · 检 5/5 · 轮 3 · 基 de1a12e6

### R2 · S5 收尾 (2026-11-19)

- 2026-11-19 02:02 docs 回写: `docs/configuration.md`「全局限速曲线」节新增「曲线排序: 按 period 自动排序」小节 —— 排序键序定义(键序用户面单点, D12)+ 三层自动排序行为(GET 展示 / 运行时模型 / UI 新增定位插入与改值提交重排)+ 落盘收敛口径(手写顺序随意, UI 保存后落盘为规范序; 乱序件首次 UI 保存经整体替换语义重排, 曲线段列表项内注释该次丢失一次 —— 计划 §07 风险第一条的 docs 明示义务)+ month 不按当月实际天数(幂等)。README 与 memory-bank 主题文档核查: 无过期排序断言, 无需回写(architecture/webui.md 已超 cap, 不为非必要事实增债)。
- 2026-11-19 02:02 真机自检判定: 纯桩可验, 不落真机轨(依据见「思考过程与决策」); 计划预判成立。
- 2026-11-19 02:02 test.full 全量绿(见 kb.baseline 最新切片 26-11-19-0202-webui-curve-period-sort, 单轮净无 flaky), 基线切片新建。
- 2026-11-19 02:03 kb.wrap 切片(26-11-18-0805-webui-curve-period-sort)+ 本档案进度回写; 计划 26-11-18-0801 与本档案翻 Done。
