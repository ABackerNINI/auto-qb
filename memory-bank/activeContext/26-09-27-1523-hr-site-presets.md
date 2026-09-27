# hr-check-site-presets — HR 在线核实配置收敛: 内置站点档案 + 站点配置上收

> 摘要: plans/26-09-27-1318 REV2 全部落地(M1 后端 + M2 配置面/UI + M3 文档)。站点启用方式
> 变为: `hr_check.sites.<档案 id>`(键 = 内置站点档案, 单点 `config/site_presets.py`)点选启用 +
> 微调, 页面地址/解析器/下载路径/翻页参数由档案填充不再是配置项; loaders 按域名交集自动绑定,
> 派生填充 `TrackerConfig.hr_check`, 运行链路零改动; 旧键 `trackers.*.hr_check` 兼容等价迁移
> (四档案键丢弃, 新旧并存新位置获胜), **生产 config.yml 零修改行为不变**。
> 全量 1700 passed + 1 skipped(TOTAL 91%), 基线 `26-09-27-1420`; 浏览器验证站点卡片通过。
> 最后活动: 2026-09-27 15:23

## 本轮事实

- 新文件 `src/auto_qb/config/site_presets.py`: `SiteHrPreset` + `SITE_PRESETS`(btschool=nexusphp/
  pt.btschool.club, carpt=carpt/carpt.net, 均 /myhr.php + /download.php?id={id} + page)+ `find_preset`
  /`match_trackers`(小写精确交集)/`preset_for_domains`; config 层纯数据(hr 反向依赖会成环)。
- 绑定与迁移在 `loaders._resolve_hr_site_bindings`(校验通过后才跑, 只填值不报错); 绑定类报错
  在 `validation/sections._validate_hr_site_bindings` 独立做一遍(校验器看不到 loader 产物)。
- fail-fast 面: 未登记档案 id(报错+已支持清单)/绑不上/绑多个/绑定站点缺 hr 段/旧键绑不上档案。
- schema: `SITE_HR_CHECK_FIELDS` 删除 → `HR_CHECK_SITES_FIELDS`(mode+五微调); TRACKER_FIELDS 删
  hr_check(hr 字段 help 指向上收); `schema_payload().constants.hr_check_site_presets` = 卡片数据源。
- impact: `HR_CHECK_FIELD_LEVELS.sites = L0`(随 hr_check 动态应用; 派生 trackers.*.hr_check 本就 L0)。
- WEB UI: HR 分区「站点接入」卡片(config_hub.js `hrSite*` 方法族 + settings-detail.html 模板块,
  hubBlocks 跳过 sites 通用渲染); hubReadout 兼容统计 sites+旧键; 站点分区撤出 hr_check(hr 规则保留)。
- 文档回写: docs/configuration.md(HR 章节重写)/config-reference/keys.md(旧键行改兼容语义 +
  新 sites 节)/README/modules/overview.md。
- 开工同步: 远端 8d03995(webui W2b 收口)快进合并, 本地计划登记改动 stash 移出后施回无冲突。

## 验证

- test.full 全绿记基线 `26-09-27-1420`(1700+1, TOTAL 91%, 17.8s)。
- 浏览器(IAB)验证: 卡片渲染 2 张+绑定状态行先行提示 / selectOption 写 `hr_check.sites.btschool.
  mode=partial` / 微调折叠块出现(5 字段, 无 mode)/ 补域名后「已绑定站点: BTSchool」翻转 /
  站点编辑器无 HR 在线核实块、HR 规则保留。

## 待办 / 交接

- 提交轮未做(等用户显式「提交」); 页面 `page_param=page` 的「待在线实测」注记保持 —— 真机
  走查时一次核实, 错了改 site_presets.py 一行。
- 本机无 node(Playwright 冒烟链路不可用), 前端验证走的 IAB 浏览器(见上); ui_smoke.cjs 链路
  恢复后可把 `hrSite*` 断言收编进冒烟合集(非必须)。
