# 文档与代码的一致性

> 摘要: 文档与代码冲突时的裁决顺序、`🚧` 标注到底是什么意思、示例配置文件自己也会漂移, 以及哪些历史记录不必再查。
> 触发: 文档与代码不符, 看到 🚧 标注, 回写知识库, 想删"已实现"的标注, 示例配置过时, 抄示例当底子, minimal.yml, 新示例 yml

## 裁决与标注

### 冲突裁决顺序: 代码 > `memory-bank/` > 根 `README.md` > `想法.md`

- **触发**: 发现文档与代码不一致 / 决定以哪份为准。
- **判别**: 三份文档之间对同一事实说法不同。
- **处置**: 一律**以代码为准并回写**; `想法.md` 是设计草稿, 不随实现同步, 不拿它当事实源。

### `🚧` 的语义是"未实现 **或** 已实现但未经实盘验证"

- **触发**: 看到规则系统一节里的 `🚧`, 想"已经实现了, 可以摘掉"。
- **判别**: `🚧` 覆盖 trigger / execute_once / cooldown、size / trackers / state / hr / date_time / seedtime /
  upload_* / freespace 条件、checking / move_to / reannounce 动作、`stop_following_rules_if`。
- **处置**: **必须保留, 勿因"已实现"而移除** —— 这些属"代码有单测但作者认定未经实盘验证"那一档(曾误删, 已按作者要求恢复)。

## 示例文件漂移

### 抄既有示例/文档里的配置当新配置的底子前, 先过一遍 fail-fast 校验 —— 示例文件自己可能已经过时

- **触发**: 写新的示例配置 / 测试 yml, 顺手拿 `minimal.yml` 或 README 里的配置片段当底子。
- **判别**: 示例文件**没有守卫测试盯着**, schema 演进后无人回写 —— 2026-09-25 实测: minimal.yml 的
  `add_episode_tags: true` 已是旧形态(现要求字典 `{enabled: ...}`, 见 `config/validation/sections.py
  _validate_add_episode_tags`), `load_config("minimal.yml")` 直接红 "必须是字典"; 且 enabled 默认 false,
  旧写法被解析器静默忽略 = 功能实际是关的(**已于同日修复为字典形态**)。
- **处置**: 新示例文件落盘后**立即 `load_config()` 验一遍**(它就是校验单点, 别信底子);
  发现既有示例漂移**一行不改** —— 属计划外缺陷, 报告交用户决定(范围守恒)。
- **守阵**: `test_config.py::test_example_minimal_yml_passes_fail_fast` /
  `test_example_docker_config_yml_passes_fail_fast` —— 两份示例过 fail-fast 校验 + 钉各自承诺的
  开箱语义/容器契约字段; minimal 守阵红验过(HEAD 旧形态 → 红)。新示例文件进来时往这里追加一条。

## 不必再查的历史记录

### 已落地的历史项 + 仍敞着的 TODO

- **触发**: 想确认某条历史设计是否已实现 / 找 TODO。
- **判别**: 见下两串。
- **处置**:
  - **不必再查**: 单实例锁与 fail-fast 全量配置校验(2026-09-05)、三个种子事件触发时机(2026-09-12)、
    HR 判定单点化与 tags/category/trackers 的 `:ignore_case`(2026-09-12)、集数标签模板(2026-09-05)。
  - **仍留的 TODO**: `config/loaders.py` 的 `# TODO: optimize`; `CheckAction.execute` 闸门 0 上方
    "未完成且暂停的种子 recheck 后仍未完成会再次校验"(有 3 次/日冷却兜底, 未彻底处理)。
