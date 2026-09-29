# HR 计数: M1+M2+M3 代码侧全落地(拍板全闭) → 真机走查待

> 摘要: 专题五轮 —— ①可行性分析 (报告 26-09-29-1803, Done): 计数是清单的校验和非替代品, 补绝对量轴堵 B/C 档翻页标记失效的批量误放行洞。②修改计划 (plans/26-09-29-2036): 三处设计定稿 + T1 迁移陷阱守阵。③**M1 实施轮 (21:47, 提交 35aa8af)**: model +3 字段 / adapter base 默认钩子 / service 对平记账 + 唯一行为变更点(闸门 AND depth_broken) + 零行自证 / events / status; T1–T6 七守阵 + 红验闭环。④**M2 实施轮 (23:17)**: 用户给 D2 样张并拍板口径 ⇒ 载体定形**页头摘要形**(计划原假设 CarPT 分页区间形被样张证伪); nexusphp.py 共享 header_hr_numbers / btschool.py 新薄子类(2 数=考察中/未达标) / carpt.py 覆写(3 数, 上限不采) / ADAPTERS 注册 + 档案改 btschool / docs 补「计数口径校准」节; 8 新用例。⑤**M3 实施轮 (26-09-30 00:24)**: 拍板两项 —— R7=**现状观察**(冻结保守+告警引导+streak 升级, 信号充分, 真出现再立豁免计划), P3 备选项=**全部缓做**; 落地三件 —— 提示语收尾(cli help + WebUI 确认弹窗「计数自证空集的站点无需人工确认」) / 展示口径对齐(实施期发现: 行为面已认计数自证而展示面只认人工戳 ⇒ 误标「零行未确认」; status.py 新 count_attested_empty 字段+helper 与 service 同式, blocking_reason 补豁免, report 零行尾注三分支) / WebUI「各档波次」徽章化(rows/声明 + 对不平 warn + 失效 error)与自证站点摘人工戳入口; 全量 1768 passed / 91%。
> 触发: HR 计数, count_claim, count_match, count_mismatch_streak, full_depth, releases_enabled, depth_broken, parse_counters, 页头计数条, header_hr_numbers, 摘要形, 零行自证, count_attested_empty, T1 迁移陷阱, fail_streak
> 最后活动: 2026-09-30 00:24 (M3 退役与打磨代码轮, 1768 全绿 @ f39413b0, 未提交)

## 状态

**M1 已提交 (35aa8af); M2 已提交 (f39413b); M3 代码侧落地待提交** —— M3 展示层 5 文件
(status.py / report.py / cli.py / hr_status.js / settings-detail.html) + 测试 3 处(新增 report
尾注守阵 + T4/zero_rows 加强), 基线切片 [26-09-30-0024](../testing/baselines/26-09-30-0024-hr-counter-m3.md);
引擎层零改动。拍板全闭: P2 方案 A / R7 现状观察 / P3 全缓做。

## 未完成

- **真机走查**(M2/M3 验收, 用户侧): 连续 ≥2 波「站点声明 == 实抓行数」逐档对平(--hr-status 与
  WebUI 徽章 rows/声明 一致) + 人为制造一次缺口验证冻结与自愈。
- 两站页头均无「已达标」位 ⇒ §2.5 计数自证空集对这两站不触发, 零行波仍走人工戳(设计内);
  自证空集路径目前只对「各档声明齐全且全 0」的站点生效(展示面已对齐)。
- P3 备选项(已拍板缓做, 非遗忘): 末页追翻省略 / HR 上限徽章总数轴互证(依赖 D4 口径实证) /
  looks_like_login 登录态佐证。

## 指针

- [集成修改计划 26-09-29-2036 (v1.3, M1+M2+M3 Done 代码侧)](../plans/26-09-29-2036-plan-hr-counter-integration.html) ·
  [基线切片 M1 26-09-29-2147](../testing/baselines/26-09-29-2147-hr-counter-m1.md) ·
  [基线切片 M2 26-09-29-2317](../testing/baselines/26-09-29-2317-hr-counter-m2.md) ·
  [基线切片 M3 26-09-30-0024](../testing/baselines/26-09-30-0024-hr-counter-m3.md) ·
  [可行性报告 26-09-29-1803 (Done)](../reports/26-09-29-1803-report-hr-counter-verify.html) ·
  [任务档案](../tasks/26-09-22-backend-partial-hr-verify.md)

**Refs:** memory-bank/plans/26-09-29-2036-plan-hr-counter-integration.html, memory-bank/testing/baselines/26-09-30-0024-hr-counter-m3.md
