# ci-linux-red-normcase-assert

> 摘要: R0: 修复 GitHub Linux CI 一条红: test_under_alias_root_dual_criteria 把 Windows 侧 normcase 折叠结果写死成期望值(r:/media 小写盘符, Linux normcase 恒等必红) -> 断言改对 ru._norm(root) 平台中立项; 生产码 _norm 跟随平台符合 §3.3 设计口径不动; patching 形态④ 复发 +1
> 最后活动: 2026-11-07 09:27

**R0(2026-11-07 09:27):** R0: 修复 GitHub Linux CI 一条红: test_under_alias_root_dual_criteria 把 Windows 侧 normcase 折叠结果写死成期望值(r:/media 小写盘符, Linux normcase 恒等必红) -> 断言改对 ru._norm(root) 平台中立项; 生产码 _norm 跟随平台符合 §3.3 设计口径不动; patching 形态④ 复发 +1
