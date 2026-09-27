# 26-09-28-webui-tag-candidates — WEBUI 标签候选剔除程序自动维护标签

**Status:** Done
**Added:** 2026-09-28
**Updated:** 2026-09-28
**Summary:** 添加种子窗口与右键「标签/分类…」弹窗的标签候选改走 GET /api/tags?exclude_auto=1, 服务端剔除程序自动维护的标签: 各站点 tags 全部 + HR 输出标签(按站点 replace_vars 展开)进精确集, 集数标签模板(${episode_*} 占位→\d+)进形状正则; MISSING/zSkipChecked 事件标记(程序只打不摘, 留候选才有补救路径)与规则 add_tag 输出(用户自己的自动化)按拍板保留。改标签弹窗把选中集合共同携带的标签并回候选 —— 胶囊是这类标签唯一摘除入口。全默认配置行为不变; test.full 1820 passed(基线 26-09-28-0724)。
**Topics:** webui-tag-candidates

## 原始请求

「WEBUI添加种子窗口/更改标签中标签下拉框选项移除程序维护会自动添加的标签, 比如站点名, 先确定要移除的范围」—— 先定范围, 拍板后再动手。

## 思考过程与决策

- 排查: 两处候选同源 GET /api/tags(qB 全量标签, store 2s 短缓存)。/api/tags 共 4 个消费点: 添加窗口(addTagOptions)与改标签弹窗(metaTags)在范围内; 标签管理对话框(mgrTags, 管理/删标签定义必须全量)与列表筛选侧栏(tagOptions 来自行数据 facet, 按站点标签筛选是正当用法)不在范围。
- 程序自动打标签 6 个来源全枚举(_handle_maintenance 站点 tags/HR、_add_episode_tags、grouping.missing_tag、skip_checking_tag、规则 add_tag 动作)。本机实况(生产 config 只读解析): 22 个站点名标签 + 集数标签启用(zE${first}[-${last}]) + MISSING/zSkipChecked 默认值 + HR 未配 + 规则 add_tag 0 条。
- 范围拍板(AskUserQuestion 两问): ①集数标签隐藏但保留摘除功能; ②MISSING/zSkipChecked 暂时保留可见。
- 「保留摘除」实现: 改标签弹窗候选 = 过滤后全量 ∪ metaCommonTags(选中集合共同携带) —— 与 _metaCommonTags 既有注释口径一致("编辑场景必须能看到并移除这类标签")。集数标签值无界只能形状匹配: 模板 re.escape 后 ${episode_*} 占位换 \d+ 再 fullmatch。
- 判定函数落 infra/utils(auto_managed_tag_rules/is_auto_managed_tag), config 鸭子类型读字段 —— 真实 Config 与 web_env SimpleNamespace 替身通用, 不必给替身补方法。
- 不动分类候选(同类问题存在, 用户只点名标签); 未新增配置键, 无 validate_config 变更(黄金法则 4)。

## 实现计划

1. infra/utils: `auto_managed_tag_rules(config) -> (精确集, 模板正则元组)` + `is_auto_managed_tag(tag, exact, patterns)`。
2. torrent_detail.py `/api/tags` 加 `exclude_auto: bool = False` 查询参数; 过滤在缓存外做(RoCache 仍存全量, 写序号失效机制不变)。
3. 前端 shared 三处: add_torrent.js 候选拉取带参; dialogs.js loadMetaOptions 带参 + 并回 metaCommonTags; state.js 两条 data 注释同步。
4. 测试: test_utils 单测(真实 Config dataclass) + test_web 端点测试(替身 config 现场改造); 两文件头部测试计划 docstring 同步。

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | 范围确定 + 两项拍板(集数标签/事件标记) | Done |
| 2 | utils 判定函数 + /api/tags exclude_auto 参数 | Done |
| 3 | 前端添加窗口/改标签弹窗接参 + 共同标签并回 | Done |
| 4 | 单测 + 端点测试 + test.full 基线 | Done |

## 进度日志

- 2026-09-28: 范围排查与拍板 → 实现 + 测试落地。test.quick 全绿; test.full 一次通过 **1820 passed / 3 skipped**, TOTAL 91%(基线 26-09-28-0724, 无 throttle 假红)。前端行为仅静态守阵(node --check 语法)覆盖, 未跑浏览器冒烟 —— 候选拉取与数组合并属低风险改动, 真机观感随用户下次打开窗口确认。等待用户说「提交」。
