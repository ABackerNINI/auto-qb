# 26-10-18-webui-e2e-click-hedge-scale — clickRow 落点对冲: 3000 规模高行(1220px > 视口)把落点推出视口 ⇒ 4 条恒红清偿

**Status:** Done
**Added:** 2026-10-18
**Updated:** 2026-10-18
**Summary:** 已清偿: clickRow 对冲漏了「行高于视口」这一形态 —— 3000 规模下集行 1220px > 900px 视口, 居中滚动把落点推到视口外(elementFromPoint 恒 null)⇒ 双皮肤 4 条恒红; 修法 = 拦截面取全部 sticky 下沿最大值 + 高行改 start 对齐 + 落点钳进可落区, 4 份同构副本同步改齐 ⇒ 3000 档转全绿、300 档全量无回归
**Topics:** webui-e2e-click-hedge-scale
**Refs:** memory-bank/issues/26-10-18-2226-test-click-hedge-shows-scale-3000.html

## 原始请求

1. 用户原话：「认领并修复 memory-bank/issues/26-10-18-2226-test-click-hedge-shows-scale-3000.html」。
   ⇒ 认领(用户显式指派, 符合 create-issue「认领人只能由用户指派」)+ 修复, 收尾置 Done。

## 思考过程与决策

- **先复验再动手**(防过期原则 5): 3000 规模重跑本 spec, 4 条同签名恒红(12 passed / 4 failed), 与入池时逐字一致 ⇒ 现象未过期。
- **不用猜测当根因**: 入池时的假设是「窗口化占位随规模放大 + 2s 重渲染把行盒移走」。仪器化探针(元素几何 / 容器滚动态 / elementFromPoint 多落点)实测后**否掉**该假设 —— 真身是「行高 1220px > 视口 900px」。判据: 失败签名的「最后拦截者 (null)」表示**落点在视口外**(elementFromPoint 只在坐标落在视口内才回元素), 与旧形态「被 sticky-head/html 拦截」(有拦截者元素名)是两回事。
- **修法走 B(治本) 不走 A(门控 skip)**: issue §06 建议先做 A 止血。A 是给两条 test 加 `requireMode({torrents: 300})` 门控, 代价最小但会把「大库下追剧页行交互」这一真实维度的覆盖缺口**固化**; B 的实测代价可控(4 份同构对冲一次改齐 + 一轮全量回归验证)。已在 issue §06 保留建议原文并写明改道原因。
- **同改齐 4 处同构副本, 不是顺手改无关模块**: clickRow 对冲在 `e2e/lib/gestures.mjs`(共享件) 与三个 spec 里各有一份, `gestures.mjs` 头注自己写着「复制两份必漂移」; issue §06 的 B 方案也写明「动的是全 spec 共享点击入口, 须全量轮回归」。只改 failing 那一份会留下三份带同一缺陷的复制, 且误导后来人。
- **不碰产品代码**: 一集 ~142 个版本 chip 把行撑到 1220px 属渲染/信息密度问题, 是产品侧议题 —— 已在 issue §05 记为观察项(未入池、未改), 测试基建的修法不掩盖它也不替它拍板。
- **换端口只是环境**: 8137 当时被透明代理应 200(smoke.md 复发 4 同族) ⇒ 复验与回归都走 `E2E_PORT=8337`; 与本件成因无关, 已在报告里注明。

## 实现计划

1. 认领: 改 issue 两处状态(meta + 封面徽标)为 In Progress + 状态日志 + `kb.index`。
2. 复验: `E2E_PORT=8337 E2E_TORRENTS=3000 commands run dev.e2e -- multiselect-shows.spec.mjs`。
3. 取证: 仪器化探针(tmp-analysis/clickrow-probe*.mjs, 已 gitignore)量行高/容器滚动态/落点命中。
4. 落码: clickRow 对冲三处改齐 —— ①拦截面取所有 `.sticky-head` 下沿最大值 ②高行改 `block:'start'` ③落点钳进「行盒 ∩ (视口 − 拦截面)」; 同改 4 份复制。
5. 回写文档: spec 文件头「第二形态」段 + `pitfalls/testing/smoke.md` 新条目。
6. 验证: 3000 档定点 + 300 档全量 e2e + `test.full`; 数字进基线切片, 正文只引。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 认领并置 In Progress(两处状态 + 索引) | Done (2026-10-18) |
| 2 | 复验锚点(3000 规模重跑, 确认仍复现) | Done (2026-10-18) |
| 3 | 仪器化探针取证(定位真因: 高行居中 ⇒ 落点出视口) | Done (2026-10-18) |
| 4 | clickRow 对冲三处改齐 × 4 份同构副本 | Done (2026-10-18) |
| 5 | 文档回写(spec 文件头 + pitfalls/testing/smoke.md) | Done (2026-10-18) |
| 6 | 验证(3000 定点 / 300 全量 / test.full) + 基线切片 | Done (2026-10-18) |
| 7 | issue 置 Done(实际修法 + 测试数字) | Done (2026-10-18) |

## 进度日志

### R0 · 立档 (2026-10-18)

- 认领 → 复验(仍复现) → 探针定位 → 落码 → 验证 → 置 Done, 一趟走完(单会话)。
- 实测数字见基线切片 `testing/baselines/` 最新一条(正文不抄数字); 结论: 3000 档本 spec 由 12 passed / 4 failed 转 **16 passed / 0 failed**, 300 档全量 e2e 无回归, `test.full` 全绿。
- 新坑已入 `memory-bank/pitfalls/testing/smoke.md`(「行高于视口时 scrollIntoView(center) 把落点推出视口」), 触发词已补进该文件三行头。
- **为什么踩到没命中旧坑**: 既有条目(「行内可交互后代会吞修饰键点击」)覆盖的是**落点被 .stop 后代吞掉**, 本件是**落点在视口外 (null)** —— 同属 clickRow 落点族但判据不同; 旧条目未收 `(null)` 这一签名, 故路由没到。新条目已把两种签名并列写明。

- 2026-10-18 23:58 认领并清偿 issue 26-10-18-2226: 复验仍复现 → 探针定位(集行 1220px > 视口, 居中滚动把落点推到视口外) → clickRow 对冲三处改齐 × 4 份同构副本 → 3000 档 16 passed / 0 failed + 300 档全量 290 passed / 0 failed + test.full 全绿
