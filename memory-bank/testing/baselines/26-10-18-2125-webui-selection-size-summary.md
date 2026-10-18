# 3590 passed + 4 skipped(根, 覆盖率 98%) —— 选中摘要(个数+合计/实际占用)落地后全量基线

> 摘要: 选中摘要(个数+合计/实际占用)落地后全量基线
> 基线时间: 2026-10-18 21:25
**Refs:** memory-bank/plans/26-10-18-2013-plan-webui-selection-size-summary.html, memory-bank/tasks/26-10-18-webui-selection-size-summary.md

## 验收数字

`commands run test.full`(2026-10-18 21:24 实测):

```
TOTAL                                                18147    266   6146    193    98%
3590 passed, 4 skipped in 35.13s
```

口径: 根套件(pytest.ini 的 8 worker); `TOTAL` 列序 = 语句数 / 未覆盖 / 分支数 / 部分分支 / 覆盖率。
相对上一条基线(26-10-18 10:58 traffic-limit-card-p2b, 3587 passed): +3 用例 —— 本轮新增
`test_member_view_occ_key`(后端契约)与 `test_frontend_selection_size_summary_wiring`
(前端接线)2 条, 另 +1 为两日间其他合入(覆盖率持平 98%)。

e2e 侧按 smoke.md 六轮矩阵纪律逐轮跑完(每轮独立起桩, 端口 8137):

| 轮 | 模式 | 结果 |
|---|---|---|
| 日常门禁 | `npm run test:e2e:fast`(@fast) | 170 passed(6.2m) |
| ① 默认轮 | ok / on / on / 300 | 286 passed / 10 skipped / 0 failed(9.4m) —— 含本计划新增 4 项(2 test × 双皮肤) |
| ② error | error / on / on / 300 | 266 passed / 26 skipped / 4 failed |
| ③ hang | hang / on / on / 300 | 252 passed / 40 skipped / 4 failed |
| ④ skip-check-off | ok / off / on / 300 | 274 passed / 22 skipped / 0 failed(9.1m) |
| ⑤ hr-scene-empty | ok / on / empty / 300 | 282 passed / 14 skipped / 0 failed(9.6m) |
| ⑥ 3000 种子 | ok / on / on / 3000 | 284 passed / 8 skipped / 4 failed(21.4m) —— 修复后复跑; 余 4 红 = 存量落点对冲规模失效(issue 26-10-18-2226) |

②③ 两轮的 4 条红**全部同一处**: `e2e/delta-sync.spec.mjs` 两条真值对齐用例(双皮肤)无
`CMD_RESULT` 模式分流 —— error 下命令失败、hang 下无回执, 桩都不改真值 ⇒ 8s 轮询必超时。
**HEAD 同参实证**: `git stash` 暂存本轮全部改动后隔离复跑, 4 failed 逐字同签名(issue
26-10-18-2122 已入池, 属存量测试设计债, 不在本轮范围修)。

### 中途两红归因(均已消, 非遗留)

- **②③ 的 4 条 delta-sync 红**：存量测试设计债(真值对齐断言无模式分流, HEAD 同签名实证)，非本轮引入，已入池 issue 26-10-18-2122(未修)。
- **⑥ 初跑本计划 2 条新 test 双皮肤 4 红**：**测试期望失真，非产品缺陷** —— 桩 `--groups` 默认 200(前 G×2 个归组)，3000 种子下 added_on 降序的前两行是**未归组**种子(occ_key=null)，产品正确地不显示 Y(X=Y)，而测试按 hash 编号 2k/2k+1 推错了期望。修为「期望值从产品 occ_key 载荷现推，归组/未归组两分支都断言」后复跑转绿(⑥ 复跑 284 passed)；教训(编号同对 ≠ 真同组，与「恒真断言」同族)记入 spec 文件头追记。
- **⑥ 复跑后余 4 红**(追剧页 2 test × 双皮肤)：存量落点对冲(clickRow)在 3000 规模确定性失效，与本改动无关，已入池 issue 26-10-18-2226(未修)。

①④⑤ 轮与 @fast 门禁本改动相关断言(选中摘要 2 test × 双皮肤 + 删除框同口径行)全绿。

### 回写后复验(2026-10-18 23:0x)

本基线切片 + 任务档案 + 2 条 issue + 计划 R2 + 坑档条目全部写完后重跑 `commands run test.full`
得 **3590 passed, 4 skipped**(33.13s)，`TOTAL 18147 / 266 / 6146 / 193` 与上表逐位一致
(覆盖率同 98%)。中途两红归因：首跑回写后 `test_memory_bank.py` 两条文档守卫红(措辞/数字同根因)
—— 切片与档案的收尾摘要手抄了裸测试数字(族 B 债务冻结 394 处 +3)，按纪律改引「见 kb.baseline」
后转绿(**未抬冻结常数**，那等于把违规洗成债务)；教训与既有条目「手写样本与配置脱节」同族，
已补 pitfalls/testing/assertions.md 新条目。

## 本改动面

- 后端: `src/auto_qb/webui/views.py` —— `_member_view` 加 `occ_key`(归组带
  `encode_group_key`、未归组 null; 组 key 查表前置, 保 `return {字典字面量}` 形状)。
- 前端: `static/shared/selection.js` —— `selSizeSummaryOf(members)` 算法单点(occ_key 单元
  去重取 max)+ `selectedSize` computed(无选中早退, 经 memberByHash 解析 selHashSet);
  `static/shared/tpl/topbar.html` —— `.sel-summary` 指示器(v-if=selectedCount, 整行复用
  `.strip-note`, 零新 CSS); `static/shared/delete_flow.js` —— `_deleteDetails` 总大小行走
  单点 + Y<X 时追加「实际占用」条件行(挂 d.hint); `static/shared/tpl/popovers.html` ——
  详情行 `:title` 吃 `d.hint || String(d.value)`(既有行零变化)。
- 测试: `tests/test_web_backend_misc.py::test_member_view_occ_key`(契约三条: 归组==组行
  key / 未归组 null / 种子页继承); `tests/test_webui_static_dom_page.py::
  test_frontend_selection_size_summary_wiring`(模板/JS/删除行三层接线 + 不复活 .bulk-*);
  `e2e/multiselect-shows.spec.mjs` 新增 2 test × 双皮肤(期望值从产品 occ_key 载荷现推 ——
  归组对断 Y 现、未归组断 Y 不现, 300/3000 规模均成立; 3000 轮教训见「中途两红归因」)。
- 文档: `memory-bank/conventions/webui.md` 新增「WEB UI 选中摘要口径 (2026-10-18)」节;
  测试文件头「## 测试计划」清单同步; 计划文档 26-10-18-2013(R0/R1/R2)。
- 载荷实测(计划 §07 风险表承诺项): 300 种子全归组合成库, 单行 occ_key 均长 55B,
  `/api/state` 增量 16.5KB = **+1.7%**, 无异常, 不入池。
