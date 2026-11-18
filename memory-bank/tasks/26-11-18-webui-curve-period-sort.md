# 26-11-18-webui-curve-period-sort — 限速曲线自动按天数排序

**Status:** Open
**Added:** 2026-11-18
**Updated:** 2026-11-18
**Summary:** grilling 四轮 13 问拍板 D1-D12; 计划 26-11-18-0801 入库 Open(S1-S5 待显式开工); 立项轮零代码改动
**Topics:** webui-curve-period-sort
**Refs:** memory-bank/plans/26-11-18-0801-plan-webui-curve-period-sort.html

## 本篇只回答

本档案只回答「限速曲线自动按天数排序」专题的**推进状态与决策留痕**; 怎么修见计划件 §03/§04, 领域结论待实施后回写主题文档。

## 原始请求

1. 「限速曲线自动按天数排序, grilling」—— 对该想法做拷问式设计评审。
2. 共识清单经确认后:「出计划然后提交」—— 计划入库 + 提交, 零实施。

## 思考过程与决策

- grilling 四轮 13 问(Q1-Q13)逐项拍板, 结论 D1-D12 全表见计划 §06。
- 关键转折一(落点): 事实取证推翻隐含假设 —— UI 渲染磁盘原始树而非解析模型(GET /api/config → read_tree), 无写回路径序列化解析模型, 仅 loader 排序到不了 UI → 定为 GET 路由 + loader + 前端三层(D4)。
- 关键转折二(改值时机): Q10 拍「前端新增定位插入」后, 编辑器事实浮出 —— period 字段逐键写树(traffic-card.html:181 @input) + 曲线列表 v-for 下标 key(traffic-card.html:169), 逐键重排会焦点行数据错写 → Q11 改判重排挂 @change 提交时机(D10)。
- 计划: memory-bank/plans/26-11-18-0801-plan-webui-curve-period-sort.html(Open)。

## 实现计划

见计划 §04: S1 排序键 helper(core/curves.py, 挂 normalize_period 旁) → S2 loader 排序 → S3 GET 路由展示树排序 → S4 前端两触发点(JS 键复刻/新增定位插入/改值 @change 重排/openCurves 身份跟随) → S5 文档回写 + 测试(pytest + e2e @fast) + 收尾 DoD。每步验收判据随计划表。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | core/curves.py 排序键 helper | Open |
| S2 | loader 排序(loaders.py 构造模型前) | Open |
| S3 | GET 路由展示树排序(解析失败整段放弃) | Open |
| S4 | 前端两触发点(JS 键复刻 + 新增定位插入 + 改值 @change 重排) | Open |
| S5 | pytest + e2e(@fast) + docs 回写 + 收尾 DoD | Open |

## 进度日志

### R0 · 立项 (2026-11-18)

grilling 四轮 13 问拍板 D1-D12(共识清单经用户确认)+ 计划 26-11-18-0801 入库 Open(S1-S5 待显式开工)+ 本档案立档; 零代码改动, 计划与档案随本专题入库。

- 2026-11-18 08:05 grilling 四轮 13 问拍板 D1-D12(共识清单经用户确认); 计划 26-11-18-0801 入库 Open(S1-S5 待显式开工); 档案立档; 零代码改动
