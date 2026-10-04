# WEBUI 危险动作防护(重检确认框 + 跳检前置条件)

> 摘要: 认领 26-10-05-0254 两个姊妹件 issue(重检鼠标路径缺确认框 / 跳检缺前置条件判定), 复验均仍复现, 产出分步实施计划 [26-10-05-0314](../plans/26-10-05-0314-plan-webui-danger-guards.html)(Open 待拍板)。计划核心: 跳检前置走方向 A —— 新闸门(已完成/活跃中/组内活跃下载/同 hash 在途/filelist 前置)全部下沉 `ops._skip_gates` 单点, rule/web 共用, `webui/commands.py` 预计零改动; 重检抽 `_recheckConfirm` 前端三鼠标入口接入。复验两项新核实: ①`check_filelist` 全仓仅规则侧调用(checking.py:121), WEB 跳检从不查文件(未随四阶段迁移); ②HR 锚点 seeding_time 取自 qB 每种统计(record.py:287-296), 跳检重加清零 → HR 超额线(3×, service.py:1358)倒退。拍板点 D1-D7 全部附推荐(D1 已完成禁止/D3 组级一并下沉/D4 组员在途不拦/D5 HR 本期只文案警示/D6 点后报错)。**Refs:** memory-bank/plans/26-10-05-0314-plan-webui-danger-guards.html
>
> 最后活动: 2026-10-05 03:14

## 已完成
- 复验两 issue(取证基线 5e697ea0), 复验行写入各自 §07, 含行号漂移修订(`_skip_gates` :349→:452)与两项待核结论。
- 实施计划落盘(方案/矩阵/S1-S5 分步/T1-T15 测试守阵/风险回滚), 状态 Open。
- 双向认领链(issue doc-refs ↔ plan doc-refs)+ kb.index 重建 + kb.check 闭环验证通过。

## 正在进行
- 等用户对 D1-D7 拍板(计划 §01 表); 拍板后 S1 开工(ops 闸门扩展 + store 组级判定上移)。

## 下一步
- S1 → S5 按 [计划 §05](../plans/26-10-05-0314-plan-webui-danger-guards.html) 分步实施, 每步独立提交; S5 收尾跑 test.full 建基线切片。
