# HR 在线核实 v3 波次模型重建
> 摘要: **计划 26-09-28-1932 M1–M5 已全部落地**(2026-09-29): 判定 = 四行判定表(命中考察中管束·本地达标与否都管 / 终态档 B·C·D 与移出未列出放行·永续 / 无证据本地兜底·达标放行未达标管束·硬编码), 12 格矩阵单测钉死「管束只三格」; 取数 = 单波型波次引擎(每波第 1 页起全量对账 + A/B/C 轮流 + 三停翻条件①完成时间覆盖②remain==0×5 到期段③本地全集 infohash; 档位级截断式有效性; 失踪观察期; 流转守恒 0.7/骤降 30%/零行戳三道防伪; A 档行无条件下载 + 终态行粗配≥K 触发·infohash 精配定论; 超额 3× 出对象集); 频控 = 单模型三键(min_interval 90S + 日额 240 + max_pages_per_wave 30, 熔断/停用/退避删除); 配置 40→14 键(config v2→v3 + hr_site v1→v2 迁移, 档案 listing 字段); `--hr-resume` 删 / `--hr-confirm-empty` 增(含 WebUI 按钮与 /api/hr/confirm-empty)。全量 1735 passed + 3 skipped(90%), 基线切片 26-09-29-0301。
> 触发: HR 在线核实, 波次引擎, 四行判定表, 单波型, 停翻条件, 失踪观察期, 流转守恒, hr-confirm-empty, 覆盖对象集, 超额线, 档位截断, hr_check, hr_status, hr_once, 取数通道, BTSchool, CarPT
> 最后活动: 2026-09-29 06:13
> (跟进修复两轮: ①WEBUI「站点接入」卡片仍写旧三态 `mode` 键致保存报
> 「未知键 ['mode']」; ②`check_hr_condition`↔`check_hr_satisfied` 行 4 互相递归致 RecursionError
> (BTSchool 实报) —— 均已修, 详见进度日志 2026-09-29 跟进条)

## 状态

**v3 已实施, v2 模型代码已全部替换** —— 判定/波次/频控/配置/呈现五层与计划一致;
真机走查(装扩展 reload + `--hr-once` + 主程序一轮 + WebUI 站点卡片)仍开放, 是唯一的验收缺口。
2026-09-29 跟进: v3 重构漏改了 WEBUI 设置页「站点接入」卡片 —— 前端仍按旧三态写 `mode` 键,
保存被 validate_config 拒(未知键 ['mode']); 已改写为 `enabled` 布尔口径(config_hub.js +
settings-detail.html), 存量 `mode` 由 `_migrate_config_2_3` 加载期自动转换。
2026-09-29 跟进②: `check_hr_satisfied` 行 4 回落调 `check_hr_condition`, 与后者的行 4 →
`check_hr_satisfied` 形成无限递归(站点接入 + 判定落行 4 即触发, BTSchool 实报 RecursionError;
record 级测试的行 4 只测过桥返回 None 路径故未兜住)。已改行 4 回落直调纯本地判据
`_local_hr_triggered()`(语义等价: 走到该行时站点侧分支均已返回), 补行 4 回归测试。
test.quick 1736 passed + 3 skipped。
明细权威在 [任务档案](../tasks/26-09-22-backend-partial-hr-verify.md) 2026-09-29 条;
计划 [plans/26-09-28-1932](../plans/26-09-28-1932-plan-hr-verify-rebuild.html) doc-status Done。

## 未完成

- **真机走查**: chrome://extensions reload 扩展 → `--hr-once` → 主程序跑一轮 → `--hr-status`
  核对各档波次状态与 WebUI「站点状态」块一致性; 确认粗配阈值 K=12 在真实样张上的表现。
- **M0 前置实测剩余项**: `?page=N` 真实参数名(nexusphp 形态标「待在线实测」); 英文站分页形态。
- ⛔ **待用户定**: config.yml 含明文 qB 凭据入不入池 issue; 选项页风格档案 26-09-26-0031 doc-status 是否改 Done。
- **配置面一件事(程序只提示不代改)**: `hr_check.channel.extension_id` 留空(启动 WARNING 提示中) +
  `config.yml` 的 `token: 123456` 改留空自动生成。

## 指针

- [计划 26-09-28-1932 (v3, Done)](../plans/26-09-28-1932-plan-hr-verify-rebuild.html) ·
  [审计报告 26-09-28-0030](../reports/26-09-28-0030-report-hr-verify-v2-impl-audit.html) ·
  [任务档案](../tasks/26-09-22-backend-partial-hr-verify.md) ·
  [基线切片 26-09-29-0301](../testing/baselines/26-09-29-0301-hr-v3-wave-model-rebuild.md) ·
  [扩展说明](../../extensions/hr-fetch-proxy/README.md)

**Refs:** memory-bank/plans/26-09-28-1932-plan-hr-verify-rebuild.html, memory-bank/reports/26-09-29-0404-report-hr-verify-v3-audit.html
