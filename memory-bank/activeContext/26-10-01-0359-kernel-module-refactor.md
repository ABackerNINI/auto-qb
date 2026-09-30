# QbManager 内核化重构(P0-P6 全部完成, 计划收官)

> 摘要: plan 26-09-30-1819 滚动实施收官 —— P6 收尾段完成: ①**段认领完备守阵上线**(hot-reload
> §3.3 规则 3): impact.py 新增 KERNEL_SECTIONS 内核自认领面(main_tick/sync_interval/
> max_tasks_per_tick/state_save_interval/qbittorrent), ModuleHost.claimed_sections() 并集口,
> apply_new_config 对未认领段变更落 WARN + rebuild_runtime 相位全量重建兜底(rules 订阅执行,
> 与 L2 同一单点, 回执含 kernel:rebuild_fallback), maintenance 补认领 hr/remove_similar_tags
> —— 配置 24 段全部有主。②文档回写: 根 README 新增「架构」段 / core-domain 内核化注记 /
> **新增 conventions/modules.md 模块契约单点**(段认领红线/相位表/协作纪律/守阵地图)。
> ③四场景真机走查全 PASS(sim_qb 代真机: 本机 qB 未运行, 200 种子仿真端 + sim_autoqb 真实
> 子进程 + PUT /api/config 全用户路径; S1 main_tick 零动作 / S2 web.token 不重启 /
> S3 HR 从无到有 / S4 重建恰一次)。④别名层处置立计划 26-10-01-0350(D4, Open 待拍板:
> 20 字段别名表 + 81 委托成员 + 27 文件 727 测试引用点, 分诊 W0/路由 W1/测试 W2/删除 W3)。
> 坑档新增 pitfalls/testing/hot-reload-section-choice-side-effects.md(热重载测试选段判据)。
> test.full 1890+3 / 91%。**本专题计划完结; 遗留 = 别名层处置计划待拍板。**
> 最后活动: 2026-10-01 03:59

## 已完成

- P6(2026-10-01): config/impact.py(KERNEL_SECTIONS)/ core/module.py(claimed_sections)/
  core/qbmanager.py(未认领段兜底三件套)/ rules_mod(rebuild_runtime 相位)/ maintenance_mod
  (sections 4→6 段); 新建 tests/test_modules_p6.py 6 例; README 架构段 + core-domain 注记 +
  conventions/modules.md + overview.md 速查修正; 基线切片 26-10-01-0359-p6-closeout.md(四场景
  实录); 1819 计划 In Progress→Done(doc-refs 反向声明 0350 计划)。P0-P5 各段见任务档案
  与基线切片 26-09-30-1912 / 2000 / 2048 / 2142 / 2250 / 26-10-01-0245。

## 下一步

- 别名层处置计划(memory-bank/plans/26-10-01-0350-plan-web-state-alias-disposal.html)**待拍板**
  —— 决策点 D1(属性对永久保留?)/ D2(测试分批粒度)/ D3(执行时机); W0 分诊清单可先行。
