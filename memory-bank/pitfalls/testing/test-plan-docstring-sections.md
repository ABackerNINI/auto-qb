# 测试计划新用例必须登记在主「## 测试计划」段(同级小节不进审计面)

**现象**: `tests/test_test_plan_docstring_guard.py::test_repo_plan_matches_defs` 只审计 docstring 里主「## 测试计划」段——段止于**下一个同级 `## ` 标题**。把新增用例条目写进文件里其它同级小节(如「## R17 变异审计补测(序列化与持久化)」这类人读重复段)时,条目不进审计面;定向测试全绿,首次全量(提交闸门 test.quick)才被点名「N 条用例未列清单」。

**动作**: 新增/改名用例的清单条目一律登记在主「## 测试计划」段内(格式 `- test_用例名: 一句话`);其它小节只可作重复登记(主段为准)。写完拿 `commands run test.one -- tests/test_test_plan_docstring_guard.py` 先自检一把再交闸门。

**实例**(2026-11-08, 0527-hr S4 批): test_hr_store.py 两条新用例写在 R17 小节,主段漏登,提交闸门红一次;补主段两行后绿。
