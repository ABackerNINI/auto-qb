# 3449 passed + 4 skipped —— P4 接缝提示判据左端口径修订(issue 26-10-16-0954 认领与修复; 数字为合流提交树, 合入前 3418+4)

> 摘要: 用户「认领并修复 memory-bank/issues/26-10-16-0954-bug-traffic-seam-hint-missed-after-first-sample.html」。`webui/static/shared/qb_traffic_chart.js` `_qbSeamHint` 判据左端从「链末桶覆盖端 `t+interval`」放宽到「链末桶前一桶起点 `t-interval`」(两端含): 原口径隐含前提「链末桶晚于重启时刻 ⟹ 链已接续、无误读面」在「重启后首采已入账、随后立即进入开放零游程」形态下不成立 —— 首采(恒落在重启后 <= 一个 main_tick)总归进链末桶, 但尾区仍在(实测帧: 重启 04:45:01 -> 首采桶 04:45:02 -> 04:45:04 起整片斜纹到右沿却零提示)。放宽一桶宽 = 「链在重启处断」与「重启后首个观测桶即链末」在桶粒度上不可分; 反方向链末桶起点晚于重启 + 1 个桶宽以上 = 链确已接续, 不提示。同步面: node 电池 `_qbSeamHint` 用例 11 -> 17 条(含实测帧重建回归) + 静态守阵第 6 节补左端整行活性锚 + drawer.html 注释与测试头 docstring 口径同步; 断线语义零改动(spanGaps ×2 原样)。
> 基线时间: 2026-10-16 12:04
> 档案: memory-bank/tasks/26-10-15-webui-qb-traffic-restart-spike-gap.md

**Refs:** memory-bank/tasks/26-10-15-webui-qb-traffic-restart-spike-gap.md,memory-bank/issues/26-10-16-0954-bug-traffic-seam-hint-missed-after-first-sample.html

## 验收数字

- test.full(提交树 = rebase 合流 cc4b6bec + 64b26dac 后的 HEAD): 3449 passed + 4 skipped / TOTAL 17362 214 5912 166 98%; 耗时 154.9s(单次采样, 口径见 baseline.md)。
- **本切片两次测量口径(2026-10-16 12:34 补记)**: 上面的 TOTAL 行取**提交时 rebase 合流另两笔提交(cc4b6bec 接缝三形态修复轮 + 64b26dac S6 工具/配置面)之后**在提交树的实测; 合入前本地树(仅本轮改动)的实测为 **3418 passed + 4 skipped / TOTAL 17178 184 5854 158 98%**(五次采样 149.1~237.7s 逐位一致)。passed/TOTAL 的增量(+31 / +184 语句 / +58 分支)全部来自另两笔提交的守阵与新增源码, **不是本轮改动**; 红绿双验 / 复验 / 定向回归三行的数字与结论均在本轮改动面上实测, 不受合流影响。
- 口径注记(供对账): **合入前**(仅本轮改动的工作树)实测语句 17178, 与本 clone 前两条基线记录(26-10-16-1051 / 26-10-16-1109)的 17377 相差 -199(未覆盖 -1; **分支 5854 / partial 158 逐位一致**)。已核: ①git 内容一致(`git diff 999d9f0b..3473aa9a -- src` 为空, 本轮零 Python 源码改动); ②工具链一致(各 clone `.venv` 均 Python 3.14.7 / coverage 7.16.1, 机器仅装 3.14); ③本环境五次采样(pytest-cov 报表 ×4 + uv 直跑 ×1)语句/未覆盖/分支/partial 逐位一致。差异面不在本轮改动面(亦不在可观测源码面), passed/skipped 与分支/partial 判据均无变化; 未定位具体成因, 留档供后续对账。
- 复验(修复前, 只读探针 `.openclaw/tmp/probe1.js`, 未入库): 实测帧重建(1m 窗 interval=2s: 04:45:00 记 100 / 重启 04:45:01 记 101 / 全窗唯一非 null = 首采桶 04:45:02 记 102 / 右沿 140)代入旧判据 ⇒ `started=101` -> **null(零提示, 现象复现)**; `started=104`(= 链末桶覆盖端) -> 提示。修复后同探针: `started=101` -> `{startedAt:101}`(提示显示), `started=100`(恰在链末前一桶起点) -> 提示, `started=99`(早一桶宽) -> null。
- 红绿双验(node 电池全 50 检查; `.openclaw/tmp/redverify_seam_hint.py`, 突变只写 `.openclaw/tmp` 副本, 真源码字节恒等自证): ①左端退回旧口径(`t+interval`) ⇒ **4 条判红**(重启落在链末桶覆盖窗 / 恰在链末前一桶起点 / 实测帧首采即链末桶 / 实测帧边界); ②去掉左端(`-Infinity`) ⇒ **3 条判红**(早于链末前一桶 / 重启远早于链末 / 实测帧早一桶宽); 还原后真源码 50/50 全绿。
- 定向回归: `commands run test.one -- tests/test_webui_static_dom_panel.py` 43 passed(含新电池与新静态锚), 副作用台账越界 0。

## 本改动面

- `src/auto_qb/webui/static/shared/qb_traffic_chart.js`: `_qbSeamHint` 左端定义行改 `chainPrevStart = points[last].t - interval`(原 `chainCoverEnd = points[last].t + interval`)与判据比较行同步; 函数 docstring 与 `qbCurSeamHint` 注释口径重写(左端修订理由与「不可分带」论证入注释)。
- `src/auto_qb/webui/static/shared/tpl/drawer.html`: 提示行模板注释口径同步(「期间服务重启」->「重启贴近链末」+ 左端修订指针; 提示行本体/文案/类名零改动)。
- `tests/test_webui_static_dom_panel.py`: node 电池 `_qbSeamHint` 用例 11 -> 17 条(原「重启在链内->null」反例按修订语义翻为「重启落在链末桶覆盖窗->提示」; 新增左端两点边界、远早于链末 null、实测帧三条回归); 第 6 节静态守阵补左端整行活性锚(`if (started < chainPrevStart || started > rightEdge) return null;` 整行匹配, 退回旧口径即红); 两处 docstring 测试清单同步。
- 滚动面(文档): issue `26-10-16-0954`(Open -> In Progress -> Done + doc-refs 认领链 + 复验/修复后补充/§06 落点说明)、计划 `26-10-15-0829` §03 P4 判据修订注记 + 变更记录、档案 `26-10-15-webui-qb-traffic-restart-spike-gap` R11、activeContext 切片、坑档 `pitfalls/web-ui/bucket-granularity-boundary.md`(新) + `pitfalls/testing/sandbox-tool-cache.md` 变体补记(工具 shell 环境下 uv 托管命令的缓存落点陷阱)。

## 范围与残留

- 断线语义零改动(G2): 尾区仍如实渲染 null/斜纹, 提示只改「怎么读」不改「画什么」; `spanGaps: false` ×2 与斜纹钩子原样(守阵照旧)。
- 「开放游程为何读侧不可见」未动 —— issue §03/§07 已认定为独立未解问题, 若后续定位到读侧, 另开一条。
- 同帧另一症状(缝首桶孤点, issue `26-10-16-0954-bug-traffic-seam-zero-bucket-isolated-marker`)与「<=60s 短缝尖峰」(issue `26-10-16-0954-bug-traffic-seam-short-gap-spike`)均未在本轮范围, 仍 Open。
