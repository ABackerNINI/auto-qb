# HR 站点绑定改映射制(26-09-27-1930)—— 实施完成 + 写回事故修复 + 物化重构落地

> 摘要: 计划 26-09-27-1930 已落地: 绑定从「域名交集比对」改**映射制**(web 域与 announce 域
> 两命名空间永不互相比对) —— 双域档案(web_domain/tracker_domain) + 默认映射零配置查表 +
> 显式 `hr_check.sites.<id>.tracker` 兜底; 旧键 `trackers.*.hr_check` 走 schema 迁移链
> **config v1→v2**(`config/migrations.py`, 26-09-26-0506 机制首个 config 生产落地)一次性改写,
> 无常驻兼容层。**晚追补一**: 生产 WebUI 保存踩出写回事故 —— writer 校验走迁移临时副本、
> 落盘写未迁移原树 + v2 章, 磁盘 = v2 + 旧键, reload/重启报废。**晚追补二**: 用户复查日志
> 实锤第三缺陷(启动迁移日志被吞: load_config 先于 setup_logging, INFO 无 handler 被丢),
> 裁决整体推翻延迟物化 —— 计划 26-09-27-2252 已实施: 加载即迁移(保留) + 迁移前版本号备份
> (`<data_dir>/<名>.v<m>.bak`) + run() 开头立即落盘(materialize_schema_migration, 幂等常态
> 零 IO; dry-run 只探测) + 延迟语义退场; 写回路径按用户裁决改**拒绝式版本闸门**(提交树版本
> 低于当前含缺失直接 400 指路刷新, 不做迁移修补 —— 第一版迁移补丁被取代移除)。
> 触发: hr 绑定, 映射制, tracker_domain, schema v2, hr_binding, 迁移物化
> 最后活动: 2026-09-27 23:26

## 状态

**Done**(映射制实施 + 写回事故修复 + 物化重构全部落地; 档案 tasks/26-09-27-config-hr-binding-mapping.md
(重构并入其 D9-D13)。test.full 1759 passed + 3 skipped / 91%, 基线 26-09-27-2326。待用户「提交」)。

## 遗留(非阻塞)

1. ⚠ **用户生产 config.yml 已被事故写坏**(D:\Projects\auto-qb: v2 章 + 未迁移旧键, 保存动作
   落盘后才报 500): **重启前**须恢复 `<data_dir>/config.yml.bak`(保存前自动备份, v1 形态,
   新代码加载即自动迁移)或按报错指引在 `hr_check.sites.<档案 id>` 手工重配并删旧键。跨 clone
   红线: AI 不动手, 由用户自行处理。物化重构落地后恢复路径不变(物化不救已损坏文件)。
2. **tracker 下拉选择控件**(计划 §9 明确不做): `tracker` 现以微调字段(文本)形态出,
   下拉(候选 = cfgTrackerNames)留作后续 UX 增强。
3. **一站多 announce 域**: `tracker_domain` 暂为单值, 真出现再扩 Tuple + 显式兜底(计划 §9)。
4. 本轮未踩已记的坑, 无复发记账; 写回事故坑 pitfalls/backend/schema-stamp-writeback.md
   处置段已随闸门口径更新。
