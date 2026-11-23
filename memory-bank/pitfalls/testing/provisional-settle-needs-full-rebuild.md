# 临时态结算必须 full 重建, partial 只翻脏行会滞留每拍重触发

> 摘要: site_provisional=True 的基础代若只靠 partial(增量)结算, 未脏行原样复用致临时态滞留、每拍重复触发结算而永不翻假; 正解=非提前发布拍用行字段判据(`any(r["site_provisional"] for r in flat_view)`)触发 full 四视图整体翻假。全未配库尤其隐蔽: 无 group_key_migrations→无 view_changed→守阵已消费→不置脏, partial 路径整体失效。
> 触发: site_provisional, 临时态, 结算, partial, 增量重建, full, mark_dirty, 脏行, 未脏行复用, view_changed, group_key_migrations, 全未配库, no_site_conf, 滞留, 每拍重触发, provisional_completion

### 形态一: partial 结算只重建脏行, 未脏行原样复用 (2026-11-23)

- **触发**: 基础代以 `site_provisional=True` 提前发布后, 非提前发布拍(补全代/任务线)要把它翻回 False。若结算走 partial(增量)路径 —— 只把本拍脏行键集送进重建 —— 未脏行的 `site_provisional=True` 被原样复用(行字段没变就不进脏集), 于是已发布代仍混着临时态。
- **判别**: 症状是「结算判据每拍为真、每拍都触发重建, 但代里始终有 site_provisional=True 的行」—— 因为触发条件本身就是 `any(r.get("site_provisional") for r in flat_view)`, 行不翻假判据就自灭不了, 形成每拍重触发的死循环。根因链(全未配库最难验的形态): 全未配 → 每行 tracker_conf=None → full_round 无 matched_added → 无 group_key_migrations → guard 分支下 view_changed 已被前序消费 → 不置脏 → partial 的脏行键集为空 → 没有一行被重建翻假。
- **处置**: `runtime_views.flush_views` 里用**行字段**判据(不新增共享状态)在「本拍 `not site_provisional` 且 `any(r.get("site_provisional") for r in self.flat_view)`」时 `mark_dirty(full=True, reason="provisional_completion")` —— full 代清空累积键、四视图整体重建, 每行都过 `_member_view` 拿当前 `_site_provisional_generation=False`, 临时态一次翻假、判据自灭、幂等不每拍多发。判据用行字段而非「是否发过临时代」的共享标志: 翻 False 后判据自然消失, 无需额外清标志。守阵(计划 26-11-23-1339 缺口修复批)钉「全未配库 + 无迁移」下二拍仍翻假并报真 no_site_conf。
- **复发**: 1(2026-11-23, 计划 26-11-23-1339 缺口修复 95bd22f6)。**为什么没命中**: 常规有配库场景二拍伴随 group_key_migrations/view_changed,full 被「顺带」触发, partial 的缺陷被掩盖; 只有**全未配库**(无任何迁移、无视图字段变化)才暴露 partial 路径完全失效。教训: 写「结算/翻假」类守阵时, 必须构造「无其它变更理由」的干净场景, 否则 full 被旁路触发, 守阵验的是顺带行为而非结算本身。**关联**: `fakeclient-default-tracker-masks-unconfigured.md` —— 全未配场景先用它确保桩没把未配悄悄改写成已配, 否则本坑的根因链第一步就不成立。
