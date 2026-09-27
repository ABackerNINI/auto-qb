# 1700 passed + 1 skipped —— HR 在线核实配置收敛: 内置站点档案 + 站点配置上收 hr_check.sites

> 摘要: plans/26-09-27-1318 REV2 三里程碑落地。①新增 `config/site_presets.py` 内置站点档案表
> (btschool/carpt 两档, 页面事实代码写死); ②站点级配置整体上收 `hr_check.sites.<档案 id>`
> (mode + 五微调项), loaders 按域名交集自动绑定并派生填充 `TrackerConfig.hr_check`(绑定结果
> 视图, 下游 service/channel/parse/锚点零改动); ③旧键 `trackers.<站点>.hr_check` 兼容接受并
> 等价迁移(adapter/hr_page_url/download_path/page_param 四键丢弃, 值一律以档案为准, 新旧并存
> 新位置获胜) —— **生产 config.yml 零修改行为不变**(回归锚 test_legacy_equivalent_migration)。
> 未登记档案/绑不上/绑多个/缺 hr 段全部 validate_config 聚合报错。WEB UI: HR 分区新增「站点
> 接入」卡片(键来自 schema.constants.hr_check_site_presets, 点选启用 + 微调 + 绑定状态行),
> 站点分区撤出 hr_check 块(hr 规则保留)。真浏览器(IAB)验证: 卡片渲染/点选写入/绑定翻转/
> 站点编辑器无 hr_check。
> 基线时间: 2026-09-27 15:20
> 档案: plans/26-09-27-1318(计划即档案)

- **测试增量**: 1688+1 → **1700+1**(+12): test_hr_config.py 站点级用例整体迁移到
  hr_check.sites 新位置(+档案四键来自档案/URL 推算/未登记清单/绑不上/绑多个/缺 hr 段/旧键
  等价迁移/四键丢弃/新旧并存/旧键未知子键接受等), test_config_schema.py 守阵换
  HR_CHECK_SITES_FIELDS + KNOWN_HR_SITE_KEYS + hr_check_site_presets constants + TRACKER_FIELDS
  去掉 hr_check(兼容例外), test_web.py 状态块扫描窗 4000→8000(合并块扩大)。
- **代码触点**(10): site_presets.py(新) / models.py(HrCheckConfig.sites) / loaders.py
  (_resolve_hr_site_bindings) / validation/sections.py(_validate_hr_site_entry +
  _validate_hr_site_bindings + 旧键兼容模式) / schema/hr.py(HR_CHECK_SITES_FIELDS) /
  schema/trackers.py(删 hr_check 字段) / schema/__init__.py(constants) / impact.py(sites=L0) /
  hr/adapters/__init__.py(docstring 四情形) / webui(config_hub.js + settings-detail.html)。

TOTAL 91%(11293 语句 / 818 未覆盖 / 3770 分支 / 333 partial; test.full 17.8s, 1 采样;
覆盖率口径见 [../baseline.md](../baseline.md))。
