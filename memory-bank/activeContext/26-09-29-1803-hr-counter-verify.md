# HR 计数: M1+M2 代码侧已落地(两站启用) → 真机走查 + R7 拍板待

> 摘要: 专题四轮 —— ①可行性分析 (报告 26-09-29-1803, Done): 计数是清单的校验和非替代品, 补绝对量轴堵 B/C 档翻页标记失效的批量误放行洞。②修改计划 (plans/26-09-29-2036): 三处设计定稿 + T1 迁移陷阱守阵。③**M1 实施轮 (21:47, 提交 35aa8af)**: model +3 字段 / adapter base 默认钩子 / service 对平记账 + 唯一行为变更点(闸门 AND depth_broken) + 零行自证 / events / status; T1–T6 七守阵 + 红验闭环; 全 adapter 默认无计数 = 上线即现状。④**M2 实施轮 (23:17)**: 用户给 D2 样张并拍板口径 ⇒ 载体定形**页头摘要形**(计划原假设 CarPT 分页区间形被样张证伪 —— 区间终点在早停页==已抓行数, 对翻页标记失效无保护); nexusphp.py 共享 header_hr_numbers(先剥标签再取数) / btschool.py 新薄子类(2 数=考察中/未达标) / carpt.py 覆写(3 数, 上限不采) / ADAPTERS 注册 + 档案改 btschool / docs 补「计数口径校准」节; 8 新用例 + 夹具定形; 全量 1767 passed / 91%。
> 触发: HR 计数, count_claim, count_match, count_mismatch_streak, full_depth, releases_enabled, depth_broken, parse_counters, 页头计数条, header_hr_numbers, 摘要形, 零行自证, T1 迁移陷阱, fail_streak
> 最后活动: 2026-09-29 23:40 (M2 两站启用代码轮, 1767 全绿 @ 42502f29, 未提交)

## 状态

**M1 已提交 (35aa8af); M2 代码侧落地待提交** —— M2 触点 7 文件(nexusphp/btschool/carpt/ADAPTERS/
站点档案/docs/test)按用户样张与口径拍板完成, 基线切片
[26-09-29-2317](../testing/baselines/26-09-29-2317-hr-counter-m2.md); 引擎层零改动(M1 闸门原样)。
校准实证: BTSchool 考察中 页头 1 == A 档实抓 1 行 ✓(位 1 非已达标反证: 已达标样例 50 行而页头 1);
CarPT 考核中 页头 0 == A 实抓 0 行 ✓。未达标位语义来自用户拍板(样张恒 0)。

## 未完成

- **真机走查**(M2 验收, 用户侧): 连续 ≥2 波「站点声明 == 实抓行数」逐档对平(--hr-status 看
  rows/claim) + 人为制造一次缺口验证冻结与自愈。
- **R7 拍板**(②停翻 × 页头计数, 计划 §6 R7): 样张无②停翻波无法离线闭项 —— ②停翻波
  (full_depth=True 但深处到期行未翻)在计数口径含到期段深处行时会持续 mismatch 冻结批量签发
  (方向保守; 当前两站账号 A/C 声明全 0 或对平, 无实际风险)。二选一: 现状观察 vs 另立计划给
  ②来源 full_depth 加可区分标记后豁免该门。
- **M3**(依赖 M2 走查实证): 提示语收尾(--hr-confirm-empty 帮助文案) + WebUI 计数徽章;
  备选项(末页追翻省略 / 徽章总数轴互证 / 登录态佐证)默认缓做, P3 已由用户定为后续决定。
- 两站页头均无「已达标」位 ⇒ §2.5 计数自证空集对这两站不触发, 零行波仍走人工戳(设计内,
  M3 提示语收尾时按此口径写文案)。

## 指针

- [集成修改计划 26-09-29-2036 (M1+M2 Done 代码侧)](../plans/26-09-29-2036-plan-hr-counter-integration.html) ·
  [基线切片 M1 26-09-29-2147](../testing/baselines/26-09-29-2147-hr-counter-m1.md) ·
  [基线切片 M2 26-09-29-2317](../testing/baselines/26-09-29-2317-hr-counter-m2.md) ·
  [可行性报告 26-09-29-1803 (Done)](../reports/26-09-29-1803-report-hr-counter-verify.html) ·
  [任务档案](../tasks/26-09-22-backend-partial-hr-verify.md)

**Refs:** memory-bank/plans/26-09-29-2036-plan-hr-counter-integration.html, memory-bank/testing/baselines/26-09-29-2317-hr-counter-m2.md
