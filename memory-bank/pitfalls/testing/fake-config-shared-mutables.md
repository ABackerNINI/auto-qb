# 测试替身的共享可变类属性

> 摘要: helpers 的 `FakeConfig` 段对象是类属性(dataclass/dict/list), 任一测试原地改
> (`mgr.config.grouping.enabled = True`)会泄漏到之后所有 `make_manager` 实例 —— 是否爆雷
> 只取决于 xdist 把哪些测试分进同一 worker。已根修: 实例化时深拷贝可变默认。
> 触发: FakeConfig, 类属性, 测试隔离, xdist 分布, 偶发失败, make_manager, 原地改配置

### 单测全绿、组合跑偶发红: 共享可变类属性 + 原地改

- **触发**: 2026-10-01 P5(pipeline 收口)实施, 新增 test_modules_p5.py 改变了 xdist
  分布, `test_web.py::test_build_group_view` 的 `mgr.config.grouping.enabled = True`
  与 `test_qbmanager.py::test_refresh_removed_grouping_disabled` 的
  `assert mgr.config.grouping.enabled is False` 落进同一 worker, 后者稳定红
  (单跑恒绿 —— 单独跑时该测试拿到的类属性还是默认 False)。
- **判别**: 失败断言的值与**本测试自己设置过的任何东西**都对不上、且单跑绿/组合跑红
  → 先怀疑跨测试状态泄漏, 再查泄漏介质。本项目测试替身的介质是 `tests/helpers.py`
  的**类属性**: `FakeConfig.grouping / add_episode_tags / web / hr_check / logging /
  qbittorrent / hr / delete_tags / rules_config / trackers` 全是类级 dataclass 或
  dict/list 实例, `make_manager` 只赋值 `state_file` 等标量, 其余段全部共享同一对象。
  grep 判据: `grep -rn "config\.<段>\.\w* =" tests/*.py` —— 原地改点有多少, 泄漏面
  就有多大(web.port / hr_check.enabled / grouping.enabled / add_episode_tags.* 都中过)。
- **处置**(2026-10-01 已实施): `FakeConfig.__init__` 对每个**非标量**类属性
  `copy.deepcopy` 成实例属性(与真实 `Config` 每次构造独立实例同形), 标量仍走类属性;
  之后所有 make_manager 的配置段彼此独立, 原地改只影响本测试。**新增测试禁止依赖
  「改类属性影响其它实例」**; 若确需跨实例共享, 显式传同一对象并加注释。
  排查同类问题时按测试文件名字典序 + xdist 分组想: 泄漏方向总是「先跑的写, 后跑的读」。
