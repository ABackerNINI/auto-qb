# HR 计数: M1 核心对平机制已落地 → M2 等样张与拍板

> 摘要: 专题三轮 —— ①可行性分析 (报告 26-09-29-1803, Done): 计数是清单的校验和非替代品, 补绝对量轴堵 B/C 档翻页标记失效的批量误放行洞。②修改计划 (plans/26-09-29-2036, M1 Done / M2 Open): 三处设计定稿 (adapter 逐页 parse_counters + 首非 None 合并; 收紧落点 = releases_enabled 单点 AND 门, full_depth 字段不动; 截断波差值信息性) + T1 迁移陷阱守阵。③**M1 实施轮 (2026-09-29 21:47)**: 五代码文件 (model +3 字段 / adapter base 默认钩子 / service 波内临时账 + 闸门 + 零行自证 / events 文案 / status 展示; report.py 走 lane_texts 单点零直改) + T1–T6 七守阵 + 红验闭环 (移门 T2/T5① 红, 还原绿); 全量 1756 passed + 3 skipped / 90%。全部 adapter 默认无计数 ⇒ 无计数站点行为与基线逐位一致 (上线即现状)。
> 触发: HR 计数, count_claim, count_match, count_mismatch_streak, full_depth, releases_enabled, depth_broken, parse_counters, 分页区间, 零行自证, T1 迁移陷阱, fail_streak
> 最后活动: 2026-09-29 22:12 (M1 提交 35aa8af + 修复轮: fail_streak 清零 / events 重复常量 / 计划 v1.1, 1758 全绿)

## 状态

**M1 已提交 (35aa8af) + 修复轮待提交** —— M1 触点 7 文件随 35aa8af 入库(基线切片
[26-09-29-2147](../testing/baselines/26-09-29-2147-hr-counter-m1.md)); 其后按用户点单修复
两处计划外缺陷(fail_streak 干净波清零 + events.py 重复常量)并回写计划 v1.1, 全量 1758 全绿。
唯一行为变更点 = 批量「未列出」签发闸门多一个 AND 条件 (service.py `releases_enabled … and not depth_broken`)。

## 未完成

- **拍板结果 (2026-09-29 21:55 当面询问)**: P1 立项 = 已实施 M1 ✓; **P2 校准策略 = 方案 A**(样张实证后
  硬编码启用, 用户拍板, **暂不执行** —— M2 不开工); P3 备选项取舍 = **后续决定**(暂按计划默认缓做);
  P4 样张采集安排 = **后续确定**(用户侧动作, 只阻塞 M2)。
- **M2** (CarPT + BTSchool 启用, 待 P4 样张后启动): 覆写 parse_counters + adapter 用例 + 真机走查。
  实施注意: ①计划签名 `parse_counters(html)` 不带档位参数 —— 区间形站点须从页面自身辨认所属档位
  (tab 形无此问题), 定形时核对样张; ②tab 形计数若把「到期段深处行」计入总数, ②停翻波会持续 mismatch
  冻结批量签发 —— M2 校准须把「②停翻波的 rows vs claim」列为样张必验项。
- **M3**: 提示语收尾 (--hr-confirm-empty 帮助文案) + WebUI 计数徽章; 备选项默认缓做。

## 指针

- [集成修改计划 26-09-29-2036 (M1 Done / M2 Open)](../plans/26-09-29-2036-plan-hr-counter-integration.html) ·
  [基线切片 26-09-29-2147](../testing/baselines/26-09-29-2147-hr-counter-m1.md) ·
  [可行性报告 26-09-29-1803 (Done)](../reports/26-09-29-1803-report-hr-counter-verify.html) ·
  [任务档案](../tasks/26-09-22-backend-partial-hr-verify.md)

**Refs:** memory-bank/plans/26-09-29-2036-plan-hr-counter-integration.html, memory-bank/testing/baselines/26-09-29-2147-hr-counter-m1.md
