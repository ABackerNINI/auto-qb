# 基线 · 1894 passed + 3 skipped / 91% —— 别名层处置 W3(删兼容层本体 + 回写, 计划收官)

> 摘要: plan plans/26-10-01-0350 **W3 全量实施, W0-W3 收官**: ①qbmanager.py 删 `_WEB_STATE_ALIAS`
> (20 字段)+ `__getattr__`/`__setattr__` 双 dunder + 五节单行委托(模块方法/分组/ops/规则引擎/
> WEB 兼容转发/状态持久化, 分诊 forward 57 名全部退役), 1109 → **838 行**(plan ≤450 口径的差额
> 即内核自有方法与主循环本体, 属计划预告的合理终态); run()/__init__ 的 11 处旧名自调用内联
> (`ctx.state.load/save/maybe_flush(+interval 实参)/bind_field_snapshots(+store 实参)/
> cleanup_orphan_tmp/materialize_migration/next_flush_at`、`host.get("rules")._load_rules()`),
> 失去使用点的 `Task`/`TorrentRecord` import 同步清理; 类体终态 = 分诊「保留」24/24
> (facade 7 + kernel 17), AST 核对零缺零多余。②守阵同波改写(计划 §04 风险表):
> test_qbmanager_alias_freeze 由「冻结比对」转**反复活**(5 例: 别名表/dunder 不复活 / 退役名
> 不复活 / facade 在位 / kernel 在位且不退化 / counts 自洽), 分诊清单转退役名单永久留档
> (meta.disposal 注记); test_periodic_flush_is_wired_in_run / test_state_migration_materialize
> / test_cleanup_orphan_tmp 三个源码字面量守阵改钉新名; test_qbmanager 别名守阵区按计划 §04
> 处置 —— 静态守阵 test_qbmanager_source_has_no_web_state_fields 改读分诊名单保留(防旧字段
> 写回造第二份真相), 代理同对象断言 test_web_state_alias_proxies_to_runtime 整删(9 行豁免区)。
> ③消费方迁移: scripts/ui_harness.py 7 处旧名调用(web.rebuild_views/web.commands/web.results/
> web.pending_ver)+ 注释旧名提法清零(cli.py / config/models.py / core/module.py / views.py
> docstring ×4 / sim_autoqb.py / sim_run.py)。
> 基线时间: 2026-10-01 08:00, develop @ a801c2a9(未提交工作树)。

TOTAL **1894 passed + 3 skipped / 91%**(13179 语句 / 1052 未覆盖 / 4408 分支 / 436 partial,
test.full 35.6s, rc=0)—— 通过数与 W2 基线 26-10-01-0700 持平(删 1 例代理同对象测试 + 守阵
4→5 例相抵); 覆盖率 90% → 91% 回升: W2 注记的未覆盖漂移(1106)随删除面收回(13179 语句 / 1052
未覆盖)。
验收: 全部退役名 × src/tests/scripts 接收者级整仓 grep **零残留**(模块实现单点同名方法除外);
四场景 sim 走查回放(1819 P6 口径, sim_qb 200 种子 steady + sim_autoqb 真实子进程 + web API
GET→改树→PUT 完整用户路径)**21/21 全 PASS**: S1 改 main_tick 动作 [] 无重挂行 + L0 现读 /
S2 改 web.token 不重启同端口继续应答 / S3 热接入首个 HR 站点端点+取数线程从无到有(绑定域不在
sim 种子域, 零真实外呼) / S4 改规则重建恰一次 + rules:rebuilt 回执 + 全局任务重注册; 优雅退出
rc=0 + state 落盘 + 全程零 Traceback。走查驱动临时(不入库), 产物在 %TEMP%/autoqb-w3-walk/。

## 计划外发现(已入池, 本波不修)

- [bug] L2 重建抑制窗内二次重建吞 queue_rebuilt → 全局任务丢失:
  issues/26-10-01-0750-bug-events-suppress-window-queue-rebuilt.html(走查 S3/S4 相隔 0.5s
  实证; P5 引入, 与 W3 无关, 范围守恒入池)。

## 回写清单

- conventions/modules.md「兼容层现状」节改写为退役终态; modules/core-domain.md 注记行数与
  委托退役; qbmanager.py 模块 docstring 同波回写; 分诊清单 meta.disposal 留档。
- 本计划 HTML 标 Done; 任务档案 26-10-01-backend-web-state-alias-disposal W3 行 Done 收官。
