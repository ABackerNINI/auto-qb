# config 包重复代码修复(dup-code-audit 7 issue)

> 摘要: 用户「修复config部分问题:26-10-11-0033-report-dup-code-audit.html, 相关issue一并认领」→ 认领 7 条 refactor issue(0031 枚举双份 + 0032 六项)并全部修完置 Done。核心改动: 枚举族收敛 schema/fields 单点(validation/rules・sections・rules/expr/env 引用派生, 死件 MAINTENANCE_TAG_MODES 删除); loaders 两处统一 _get; models.SiteHrCheckConfig 派生五键默认改空(真值单点 SITE_PRESETS); validation 抽 _try_port/_try_time_window; writer 抽 _atomic_copy; docs 漂移修正(log.format / hr_check 键数 / 档案 adapter 列)+ schema_version 默认派生 CURRENT_VERSIONS; 新守阵 4 条。档案: [26-10-11-config-dup-code-fixes](../tasks/26-10-11-config-dup-code-fixes.md)。
> 最后活动: 2026-10-11 16:11

**Refs:** memory-bank/tasks/26-10-11-config-dup-code-fixes.md

## 正在进行

- **7 条 issue 全部 Done**: 枚举单源 / loaders _get 统一 / 页面事实单点 / 小校验收敛 / writer 备份单点 / docs 漂移清零, 全量测试全绿(数字见 `commands run kb.baseline`)。工作树改动随本专题入库。
- **0032 default-multi-source 改道项**: 「schema.Field.default 全键由 models 派生」未做(逐键 YAML↔解析空间换算成本高; 已有 unit_default/可解析守卫 + 新 docs 守卫兜主要漂移面), 留待后续真需要时再立项。

## 关键结论

- **config 包 C 类(同一事实多表示)是主战场**: 枚举族 9 份双声明 + STATE_ATTRS 三份 + 默认值四源 + 键面四抄 —— 修复方向一律「择一单点 + 他方派生 + is 断言守阵」, 不引入新抽象层。
- **守阵样式**: 派生关系用 `is` 断言钉住(比 == 强, 防同值第二份回潮); docs 侧用「键数 token + format 字面」守卫, 是 docs↔代码方向的第一个守阵。
- **报告 26-10-11-0033 的其余部分**(core/hr/webui/rules/infra/torrents 共 40+ 条 issue)未动, 等各自认领轮。
