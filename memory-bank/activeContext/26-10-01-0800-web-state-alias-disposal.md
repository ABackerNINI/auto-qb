# 别名层处置(web-state-alias-disposal: W0-W3 全部完成, 计划收官)

> 摘要: plan 26-10-01-0350 **W3 删兼容层本体完成, W0-W3 收官**: ①qbmanager.py 删 `_WEB_STATE_ALIAS`
> (20 字段)+ 双 dunder + 五节单行委托(forward 57 名全退), 1109 → **838 行**, 类体终态 = 分诊保留
> 24/24(facade 7 + kernel 17)AST 核对零缺零多; run()/__init__ 11 处旧名自调用内联(`ctx.state.*` /
> `host.get("rules")._load_rules()`), 失用 import(Task/TorrentRecord)同清。②守阵同波改写(计划 §04):
> alias_freeze 转反复活 5 例(退役名/别名表/dunder 复活即红 + facade 在位 + kernel 不退化 + counts),
> 分诊清单转退役名单永久留档(meta.disposal); 源码字面量守阵 3 例(test_periodic_flush /
> test_state_migration / test_cleanup_orphan_tmp)改钉新名; test_qbmanager 静态守阵改读分诊名单
> 保留、代理同对象断言整删(9 行豁免区)。③消费方: scripts/ui_harness.py 7 处旧名调用(分诊未扫的
> scripts 侧真实调用方)改 web.* 新名; 注释旧名提法清零 8 文件。④验收: 退役名 × src/tests/scripts
> 接收者级 grep 零残留; test.full **1894+3 / 91%**(覆盖率回升, W2 的未覆盖漂移随删除面收回),
> 基线 26-10-01-0800; 四场景 sim 走查回放 **21/21 全 PASS**(P6 口径, 优雅退出 rc=0 零 Traceback)。
> 计划外发现: suppress 窗内二次重建吞 queue_rebuilt → 全局任务丢失(P5 引入)入池
> issues/26-10-01-0750, 本波范围守恒不修。计划 HTML 标 Done; 档案收官。
> 最后活动: 2026-10-01 08:00

## 正在进行

- (无 —— 计划收官; 待用户说「提交」走 commit + push)

## 已完成

- W0(2026-10-01 04:43): 分诊清单 JSON + 守阵 4 例 + 档案立档 + 计划标 In Progress +
  conventions/modules.md 补清单/守阵指针 + 基线切片 26-10-01-0443。
- W1(2026-10-01 05:45): 路由与 src 侧改新名(见 0545 切片), 基线切片 26-10-01-0545。
- W2(2026-10-01 07:00): 测试面四批 + 补漏迁移(见 0700 切片), 基线切片 26-10-01-0700。
- W3(2026-10-01 08:00): 删兼容层本体 + 守阵转反复活 + ui_harness 迁移 + 注释清零 + 回写
  (modules.md 兼容层节改退役终态 / core-domain.md 838 行注记 / qbmanager docstring / 计划 HTML
  Done / 分诊清单留档 / 档案收官)+ 四场景走查 21/21 PASS, 基线切片 26-10-01-0800。

## 前序波次切片已蒸馏(2026-10-03 切片计数清理)

- **前序波次切片已蒸馏**: `26-10-01-0443-web-state-alias-disposal`(拍板); `26-10-01-0545-web-state-alias-disposal`(W1 路由与 src 侧); `26-10-01-0700-web-state-alias-disposal`(W2 测试面迁移) —— 内容全在其档案 [tasks/26-10-01-backend-web-state-alias-disposal](../tasks/26-10-01-backend-web-state-alias-disposal.md), 按 [cap-counting 坑档](../pitfalls/kb/cap-counting.md)「切片计数触顶的合法出口」删除(清理前切片数 104 > SLICE_COUNT_LIMIT 70)。
