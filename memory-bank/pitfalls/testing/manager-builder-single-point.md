# 测试构造单点参数面不足导致内联旁路

> 摘要: 测试构造单点参数面不足导致内联旁路
> 等级: L0
> 触发: 内联构造, make_manager, 单点旁路, 装配样板, FakeConfig, QbManager, 段覆盖, 测试构造器, builder

**Refs:** memory-bank/issues/26-10-21-0502-refactor-test-manager-builder-params-dup.html, memory-bank/tasks/26-10-22-test-manager-builder-params-dup.md

### builder 单点存在但「参数面不够」时, 用例退回内联装配

- **触发**: 测试侧已有构造单点(如 `tests/helpers.make_manager`, 45 文件在用), 但它只覆盖「默认装配」一种形态。需要另一段配置(grouping / add_episode_tags / delete_tags / 自定义 trackers…)的用例绕不开内联: `cfg = FakeConfig(); cfg.x = ...; QbManager("", config=cfg, no_lock=True); mgr.client = FakeClient()` —— 同一段四行样板按文件复制, 同族缺陷在 `tests/` 实测 86 处 / 12 文件(issue 26-10-21-0502)。Web 侧同形(单点存在但不可参数化 → 内联旁路)见 `pitfalls/web-ui/surface-color-family-single-point.md` 一族。
- **判别**: `grep -rn 'QbManager("' tests/`(或同族构造器)命中 **>5 处且跨多文件**; 同一段 `FakeConfig + 赋值 + 构造 + client 挂载` 在两个以上测试文件逐字出现。症状: 改一处装配语义(锁 / 规则加载 / 客户端注入)要改 N 处; 漏改一处 = 各测各的语义, 而全量仍是绿的。
- **处置**: **扩单点参数面, 不新建第二构造器**(新建会让两套入口长期并存, 正是要消的病)。三条判据:
  1. 默认路径必须与改动前**逐字等价**(内部抽函数时别顺手改装配序);
  2. 新参数给「形态」而不是「场景」: `cfg=`(现成配置对象, 共享/包装器委派) / `bare=True`(空配置 + 段覆盖) / `client=`(构造后挂替身) —— 不要为每个测试场景加专用开关(那会退化成第二构造器);
  3. **隐式行为要显式**: 原内联用例不加载规则, 若让新路径默认加载 = 顺手改了它们的语义(grouping 用例断言任务队列无多余任务, 会被规则任务打破) ⇒ 三态参数(`load_rules=None` 按路径自动) + docstring 写清。
  4. `**kwargs` 段覆盖必须 `hasattr` 守卫后 setattr, 未知段名抛 `TypeError` —— 否则段名写错会造出**幽灵属性**, 配置没生效而测试照样绿(「旁路」的变体)。
- **守阵**: 静态扫描零豁免, 但**必须带一支自检**(造一个含内联构造的一次性文件 → 必须被报出并带 `文件:行号`), 否则扫描型守阵会退化成恒绿(`guard-dead-branch.md` 实证: 「没扫到」与「扫了没有违规」输出完全一样)。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
