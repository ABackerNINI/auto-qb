# HR 站点绑定改映射制(26-09-27-1930)—— 实施完成

> 摘要: 计划 26-09-27-1930 已落地: 绑定从「域名交集比对」改**映射制**(web 域与 announce 域
> 两命名空间永不互相比对) —— 双域档案(web_domain/tracker_domain) + 默认映射零配置查表 +
> 显式 `hr_check.sites.<id>.tracker` 兜底; 旧键 `trackers.*.hr_check` 走 schema 迁移链
> **config v1→v2**(`config/migrations.py`, 26-09-26-0506 机制首个 config 生产落地)一次性改写,
> 无常驻兼容层。生产 config.yml 全程零改动且只读走查通过(BTSchool 旧键自动搬家, 派生 URL
> 与旧值一致; CarPT 启用即被默认映射自动绑定)。test.full 1752 passed + 3 skipped / 91%。
> 触发: hr 绑定, 映射制, tracker_domain, schema v2, hr_binding
> 最后活动: 2026-09-27 20:22

## 状态

**Done**(实施 + 测试全绿 + 生产走查 + 回写立档完成, 档案见 tasks/26-09-27-config-hr-binding-mapping.md)。

## 遗留(非阻塞)

1. **tracker 下拉选择控件**(计划 §9 明确不做): `tracker` 现以微调字段(文本)形态出,
   下拉(候选 = cfgTrackerNames)留作后续 UX 增强。
2. **一站多 announce 域**: `tracker_domain` 暂为单值, 真出现再扩 Tuple + 显式兜底(计划 §9)。
3. 本轮未踩已记的坑, 无复发记账。
