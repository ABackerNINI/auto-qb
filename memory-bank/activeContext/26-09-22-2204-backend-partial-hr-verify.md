# 部分种子 HR 在线核实
> 摘要: **M1-M4 + 七批实报修复 + v2.9/v3.0/v3.5 + M5.1-M5.5(在线核实 v2)代码侧全部落地; 2026-09-28 完成 v2 实施核对与安全/稳定性审计(报告 26-09-28-0030): 33 项修改全部落地, 发现 F1(P2 早停② P 机检空真+C 档形态假设)/F2(P3 跨页 S1 零容忍误停站场景)/F3(P3 parse_missing_rate_max 架空)/F4(P4 注释漂移+死变量), 均未改代码待拍板**。核心链路: 浏览器扩展代取(登录态不出浏览器) → 后端解析算 infohash → (站点, tid) 索引对账 → 三态判定+超龄豁免(站点侧权威)。频控: legacy 合并 90s 间隔·12/时·60/天(默认) | split 双令牌桶 页面 40/时·下载 20/时(站点显式 opt-in); 扩展第二道闸 页面 60/时·600/天, 下载 50/时·200/天。
> 触发: 部分种子, HR 核实, 浏览器扩展, 三态判定, 档位即结论, 站点文件, 多实例, BTSchool, CarPT, hr_check, hr_once, hr_status, hr_resume, 取数通道, 本地端点, 取数线程, 登录失效, 复用轮, 回填, 超龄豁免, completed_age_limit, 早停, 骤降保护, suspended, 配额双桶, quota_model, 限流
> 最后活动: 2026-09-28 01:09 (v2 实施核对+安全/稳定性审计: 报告 reports/26-09-28-0030-report-hr-verify-v2-impl-audit.html, 33 项全落地; F1-F4 未改代码待拍板; 提交轮 ff 合并 aef2462 后复跑 test.full 1812+3 与最新基线 0014 逐位一致)

## 状态

**在线核实 v2 (M5.1-M5.5) 代码侧完成 + 独立审计完成** —— 实施明细与数字的唯一权威在
[任务档案](../tasks/26-09-22-backend-partial-hr-verify.md)进度日志; 审计证据 (逐项 file:line 核对 +
安全性/稳定性评估 + 配置全表/默认节奏/限流全景) 在
[报告 26-09-28-0030](../reports/26-09-28-0030-report-hr-verify-v2-impl-audit.html)。
实施计划 [26-09-27-1815](../plans/26-09-27-1815-plan-hr-verify-audit-fixes.html) doc-status Implemented;
设计定稿在主计划 §14 ([26-09-22-2204](../plans/26-09-22-2204-partial-hr-site-verify-plan.html))。

## 未完成

- **F1-F4 处置 (2026-09-28 审计发现, 待用户拍板)**: ① F1 P2 —— 早停② 的 P 一致性机检在「无 remain>0
  参与行」时空真放行, 且 B/C 档 remain 展示形态未验证 (0→早停截断 C 档覆盖⇒误放行链; 空白→S2 停站),
  建议加 period_values 非空前置或限 A 档 + M0 补第④项实测; ② F2 P3 —— 跨页 S1 对轮内清单顶端插入
  (≥2 新完成) 零容忍 ⇒ 活跃账号可能连续 3 轮误停站, 与 2026-09-26「哪怕 1 处」定稿有张力, 需单独拍板;
  ③ F3 P3 —— parse_missing_rate_max 被 S2 零容忍架空 (死配置+keys.md 旧语义); ④ F4 P4 ——
  status.py 两处旧公式注释 + covered_local_any 死变量。全部只记录未改代码 (范围守恒)。
- **真机走查**(需用户装扩展): 先 chrome://extensions **reload 扩展** (1 分钟轮询/登录页检测/新选项页要重载生效),
  再 `--hr-once` + 主程序一轮 + 配置面「模板一 → 粘 token → 自动拉站点 → 一键授权 → 立即拉取」全链路。
- **M0 前置实测三项 (+审计提议第④项)**(**阻塞早停②/豁免 A 的启用**, 不阻塞代码): ① HR 页完成时间倒序;
  ② 考核期 P 恒定 (`--hr-status` 观测面直接产证据); ③ `?page=N` 真实参数名与英文站分页形态;
  ④ (新) B/C 档「剩余达标时间」展示形态 (0/空白/非零 → 分别对应 F1 的三条分支)。
- **非 NexusPHP 第三站点**(需样本): 有更便宜来源 (JSON 接口/逐种标记) 按 `adapters/__init__.py` 注册 —— 不拿到样本不猜。
- ⛔ **待用户定**: config.yml 含明文 qB 凭据入不入池 issue; 选项页风格档案 26-09-26-0031 doc-status 是否改 Done。
- **配置面两件事 (程序只提示不代改)**: `hr_check.channel.extension_id` 留空 (启动 WARNING 提示中) +
  `config.yml` 的 `token: 123456` 改留空自动生成 —— 详见报告 §3 残余风险表。

## 指针

- [计划 26-09-27-1815 (v2 实施)](../plans/26-09-27-1815-plan-hr-verify-audit-fixes.html) ·
  [审计报告 26-09-28-0030](../reports/26-09-28-0030-report-hr-verify-v2-impl-audit.html) ·
  [上轮设计审查 26-09-26-1628](../reports/26-09-26-1628-report-hr-online-verify-audit.html) ·
  [主计划 §14](../plans/26-09-22-2204-partial-hr-site-verify-plan.html) ·
  [任务档案](../tasks/26-09-22-backend-partial-hr-verify.md) ·
  [扩展说明](../../extensions/hr-fetch-proxy/README.md)
- 实测: 离线 fixture + 真回环在 `tests/test_hr_*.py` (18 个文件); 全量数字只认
  [testing/baseline.md](../testing/baseline.md) 单点; **真机链路仍未实测**。

**Refs:** memory-bank/reports/26-09-28-0030-report-hr-verify-v2-impl-audit.html
