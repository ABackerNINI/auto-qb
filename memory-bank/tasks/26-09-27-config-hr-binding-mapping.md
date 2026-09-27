# 26-09-27-config-hr-binding-mapping — HR 在线核实绑定改映射制: 双域档案 + 已知映射零配置 + 旧键迁移 v1→v2

**Status:** Done
**Added:** 2026-09-27
**Updated:** 2026-09-27
**Summary:** 计划 26-09-27-1930 实施: 站点绑定从 1318 的「域名交集比对」整体重写为**映射制** —— web 域与 announce 域是两个命名空间, 永不互相比对(用户裁决, 一切跨命名空间匹配含后缀容错方案全部否决)。档案双域硬编码(`web_domain` 只派生 HR 页地址 / `tracker_domain` 作已知映射查表键, CarPT 两域无关正是映射制价值), 启用零绑定配置(默认映射 = 已知 announce 域在用户 `domains` 同命名空间查表, 双向子域容错 `t == d or t.endswith("." + d) or d.endswith("." + t)`, 单点 `site_presets.match_trackers`), 显式键 `hr_check.sites.<id>.tracker` 按 trackers 条目名直取兜底; 唯一性(一个 tracker 只服务一个档案)与缺 `hr` 段防线保留。旧键 `trackers.*.hr_check` 无常驻兼容层 —— schema 迁移链 **config v1→v2**(26-09-26-0506 机制首个 config 生产落地, 新增 `config/migrations.py`, import 即注册): 按 `hr_page_url` 的 host(web↔web 同命名空间)定位档案一次性改写, off/非字典直接删, 定位不到原地保留交校验报废除错。生产 config.yml 全程零改动: 只读加载实测 BTSchool 旧键自动搬入 `hr_check.sites.btschool` 且派生 URL 与旧值一致, `tracker_carpt_net`(domains=tracker.carpt.net)启用即被默认映射自动绑定 —— 本轮报错的 CarPT 场景就此消失。测试 1752 passed + 3 skipped / 91%(基线切片 26-09-27-2022); test_hr_config.py 交集类用例改写为映射类 + 迁移单测 5 条 + CarPT 回归锚。
**Topics:** config-hr-binding-mapping
**Refs:** memory-bank/plans/26-09-27-1930-plan-hr-binding-tracker-mapping.html

## 原始请求

> 实施计划plans/26-09-27-1930-plan-hr-binding-tracker-mapping.html

## 思考过程与决策

- **D1 命名空间纪律落进代码形状**: `SiteHrPreset` 的 `domains`(语义含混的绑定键)与 `page_domain`(web 覆盖)合并重组为 `web_domain` / `tracker_domain` 两个职责单一字段; `page_url()` 无参化(`https://{web_domain}{page_path}`), 从根上消灭「用命中域名推算 URL」的旧行为(CarPT 报错文案「没有站点的域名包含 carpt.net」的病根)。
- **D2 判定单点不动摇**: `match_trackers` 保留(名字不换)但口径改为同命名空间双向子域容错; loader 与校验器继续共用它, 不留第二份口径。显式 `tracker` 键是**字符串相等直取**, 刻意不做任何匹配语义(计划 §3.1 第三命名空间)。
- **D3 迁移落 config 层不进 infra**: 迁移函数是纯函数但需要 `SITE_PRESETS` 定位档案, 依赖纪律(infra 只依赖 .errors)决定落 `config/migrations.py`, import 即注册进 `MIGRATIONS["config"][1]`(`config/__init__.py` 挂钩, 早于任何 `load_config`); infra 只抬号。定位用 `preset_for_web_host(host)` 精确匹配 —— 旧键 `hr_page_url` 的 host 与档案 `web_domain` 同属 web 命名空间, 不触碰 tracker 域。
- **D4 迁移语义三态**: off/非字典 → 删; 定位到 → 搬 mode+微调项(页面事实四键与未知键丢弃)、删旧键、新旧并存新位置获胜; 定位不到 → 原地保留交校验报废除错(宁可报错不迁错站)。`schema_version` 盖章归框架, 函数体不碰(单测钉死)。
- **D5 hr_page_url 的角色变化要在测试里说清**: 它从「读取后丢弃的档案键」变成「迁移定位键」—— 指到别的站的旧键会定位不到而报废除错, 与其余三个档案键(写错也无视)语义不同, `test_legacy_preset_keys_are_discarded` 相应改写。
- **D6 前端合并函数**: `hrSiteBoundTrackers`/`hrSiteBindText`/`hrSiteBindClass` 合并为 `hrSiteBinding(preset)`(返回 `{text, cls}`), 消费 schema 常量的 `web_domain`/`tracker_domain`; 卡片补站点网址展示; hub 首页 readout 移除旧键计数(键已废除)。
- **D7 连带断言随版本抬号**: config 版本 1→2 使 4 处钉死 "版本号=1/支持的 1" 的断言过期(test_config / test_config_writer / test_exporter), 一并更新 —— 属本计划的直接后果, 非顺手改。

## 实现计划

(照 1930 计划 §10 执行顺序)

1. `site_presets.py` 双域模型 + 新口径 + `preset_for_web_host` + 迁移函数(新建 `migrations.py`) ✅
2. `infra/versioning.py` 抬号 + `models.py` 加 `tracker` 键 + `schema/`(hr.py / __init__.py / trackers.py)三处 ✅
3. `loaders.py` `_resolve_hr_site_bindings` 改「显式直取 > 默认查表」, 删常驻旧键迁移块 ✅
4. `sections.py` 绑定校验按映射口径重写 + 旧键兜底报废除错 ✅
5. `config_hub.js` + `settings-detail.html` 映射口径 ✅
6. 测试改写并全绿 ✅(1752 passed + 3 skipped / 91%)
7. 回写: 1318 计划 §3.3/§3.4 标注废案 + keys.md / overview.md / 本档案 / activeContext ✅

## 子任务状态表

| 子任务 | 状态 | 说明 |
|---|---|---|
| site_presets + migrations(双域/新口径/迁移注册) | Done | 判定单点仍在 site_presets |
| versioning 抬号 + models/schema 加键 | Done | config v1→v2; KNOWN_HR_SITE_KEYS + tracker |
| loaders 绑定解析改映射制 | Done | 派生视图 tracker 回填条目名 |
| sections 校验重写 + 兜底报废除错 | Done | 五类报错文案照计划 §5 |
| WebUI(config_hub.js + 模板) | Done | hrSiteBinding 单函数; 卡片展示 web_domain |
| 测试改写全绿 | Done | +10 用例; CarPT 回归锚; 迁移单测 5 条 |
| 生产 config.yml 走查(零改动) | Done | 只读加载: 迁移触发 + 绑定正确 + URL 一致 |
| 基线切片 | Done | testing/baselines/26-09-27-2022 |
| 文档回写 + 索引重建 | Done | 1318 标注废案; keys.md/overview.md; kb.index |

## 进度日志

- **2026-09-27**(本 clone): 开工同步(gitee develop @ 045ea27 齐平) → 按计划 §10 顺序实施 → test.quick 首轮 5 失败(4 处版本号断言 + 1 处档案键丢弃前提)全数修复 → test.full 1752 passed + 3 skipped / 91% → 生产 config.yml 只读走查: `配置 schema 已迁移 v1→v2` 日志出现, `hr_check.sites.btschool` 生成(mode=partial), 派生 `BTSchool` URL=https://pt.btschool.club/myhr.php 与旧键写的值一致, `tracker_carpt_net` domains=[tracker.carpt.net] 可被默认映射命中 → `--dry-run` 实跑确认配置段全通过(止于本机无 qB 连接, 与配置无关) → 回写与立档。
