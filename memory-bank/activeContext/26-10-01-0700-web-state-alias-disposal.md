# 别名层处置(web-state-alias-disposal: W0-W2 完成, W3 待做)

> 摘要: plan 26-10-01-0350 **W2 测试面迁移完成**(只改名零行为变更, D2 按模块域 4 批 + 验收补漏
> 共 5 提交): 分诊 W2 名的测试消费方(别名 18 字段 + 转发 49 名, 约 750 处接收者级引用)全部改新名口
> —— 批次1 web 域(3e4231d1, 376 处: 别名 → `mgr.web.*`、WEB 转发 8 名 → `web.*`, test_web 假替身
> 收尾 W1 双轨: 旧名属性删除/数据挂 mgr.web.*/token 双写改单写); 批次2 maintenance+trackers 域
> (fe0cc172, 85 处: `ctx.trackers`/`ctx.maintenance`/`host.get("maintenance"|"speed_curve")`);
> 批次3 grouping 域(e88d4e4b, 52 处: `host.get("grouping")._*`); 批次4 rules+state+ops 域
> (e4c57568, 150 处: `host.get("rules")` 属性对与六方法、`ctx.state.*`(maybe_flush 补 interval /
> bind_field_snapshots 补 store 实参 / next_flush_at)、`ctx.ops.*`、helpers.make_manager 装载行);
> 补漏(5a3c8a75, 9 处: 整仓验收 grep 抓出跨批漏迁 —— 名字归批×文件归批错位, 漏迁不红因转发还在)。
> 豁免残留: test_qbmanager 别名守阵同对象断言 9 行(计划 §04, W3 同删)。过渡期钉子: test_modules_p4
> 两测试的「旧名委托等价」断言改写为纯 ctx.ops 语义。两坑落 pitfalls/testing/bulk-rename.md
> (替换串丢接收者 / 跨批漏迁)。验收: test.full **1894+3 / 90%**(覆盖率 91→90 系转发方法失去唯一
> 调用方的预期漂移, 随 W3 删除)。基线 26-10-01-0700。档案 26-10-01-backend-web-state-alias-disposal。
> 最后活动: 2026-10-01 07:00

## 正在进行

- W3(删兼容层本体 + 回写 + 四场景走查回放): 删 `_WEB_STATE_ALIAS` + 双 dunder + W2 清空的各
  委托节(预计 qbmanager.py 1092 → ≈950 行); run() 接线内联(_load_state/_load_rules/
  _next_state_flush_at 字面量)**连同 test_periodic_flush_is_wired_in_run 守阵同波改写**;
  删别名守阵区(test_qbmanager 847-890)与清单同步(冻结守阵双向比对); memory-bank 回写
  (conventions/modules.md 兼容层现状节、core-domain 注记、qbmanager docstring、views.py
  docstring 自身字段名提法核对); 借 1819 P6 的 sim 走查驱动四场景回放。

## 已完成

- W0(2026-10-01 04:43): 分诊清单 JSON + 守阵 4 例 + 档案立档 + 计划标 In Progress +
  conventions/modules.md 补清单/守阵指针 + 基线切片 26-10-01-0443。
- W1(2026-10-01 05:45): 路由与 src 侧改新名(见 0545 切片), 基线切片 26-10-01-0545。
- W2(2026-10-01 07:00): 测试面四批 + 补漏迁移(见摘要), 基线切片 26-10-01-0700。
