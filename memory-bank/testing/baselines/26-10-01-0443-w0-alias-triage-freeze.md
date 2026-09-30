# 基线 · 1894 passed + 3 skipped / 91% —— 别名层处置 W0(分诊清单 + 守阵立桩)

> 摘要: plan plans/26-10-01-0350 **W0 全量实施(纯文档与测试, 零产品代码), 计划标 In Progress**
> (拍板按推荐: D1 属性面永久保留 / D2 按模块域分批 / D3 W0 先行)。本波内容:
> ①**逐名分诊清单落 JSON 附件**(plans/26-10-01-0350-...triage.json, 命名随 .baseline.json
> 脚本直读先例): 20 别名字段 + 2 dunder + 57 单行转发 + 7 外观属性(D1 保留: config/store/
> api/state/state_file/task_queue/web) + 17 内核自有(形似旧名实非委托, 显式标保留防误删)
> = 106 个类面成员; 波次 W1(src 消费方先行)×15 / W2(仅测试)×57 / W3(无消费方直删)×5 /
> 保留×24; 每名带目标新名口 + src 行级消费方 + 测试接收者级计数。
> ②**冻结守阵上线**: tests/test_qbmanager_alias_freeze.py 4 例 —— AST 扫 QbManager 单行转发
> 形状(去 docstring 单语句 + self.<svc> 起链)与清单双向比对: 清单外新增旧名委托即红
> (conventions/modules.md 禁令机检化)/ 清单成员消失须同步清单(逼 W3 删除同波改清单)/
> kernel 成员不得退化 / counts 自洽。清单与代码双向一致由机检钉住。
> ③分诊三处实测修正(计划数字是 54c83ac3 勘察值, 本基线 82330d45): 委托成员 86(计划 81);
> 「4 个纯内部属性对」实为 1 对(_next_state_flush_at); 真实 src 消费方比 W1 原口径多
> rules 动作三域 7 处 + getattr 字符串暗消费方 1 处(context.py:32)。
> 基线时间: 2026-10-01 04:43, develop @ 82330d45 + 本轮 W0 改动。

TOTAL **1894 passed + 3 skipped / 91%**(13314 语句 / 1057 未覆盖 / 4412 分支 / 437 partial,
test.full 36.2s, rc=0)—— 较上基线 26-10-01-0359-P6 收尾(1890 passed + 3 skipped / 91%)净增 4:
test_qbmanager_alias_freeze 新增 4 例(守阵), 产品代码零改动故覆盖率分母不变。

## 本波改动面

- 新建: memory-bank/plans/26-10-01-0350-plan-web-state-alias-disposal.triage.json(分诊清单,
  守阵与其双向比对)/ tests/test_qbmanager_alias_freeze.py(4 例守阵)。
- 修改: memory-bank/plans/26-10-01-0350-plan-web-state-alias-disposal.html(Open → In Progress,
  拍板注记)/ memory-bank/conventions/modules.md(兼容层现状节补清单与守阵指针)。
- 文档: 任务档案 26-10-01-backend-web-state-alias-disposal(立档, W0 收档)。
- src/ 零改动 —— W0 按计划定义不碰产品代码; W1 才开始迁移调用方。
