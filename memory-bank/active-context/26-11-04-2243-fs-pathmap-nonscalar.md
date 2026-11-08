# fs-pathmap-nonscalar

> 摘要: 同批收掉 fs.path_map from/to 的 str() 判空: 先 isinstance(str) 再判空, 非字符串报必须是字符串(当前为类型), 缺键/空串仍报不能为空; loaders 未动; 新增 2 条回归(类型矩阵+真实 YAML load_config), 红验旧实现 2 failed/恢复后 test_config_misc 67 passed; 全量数字见 kb.baseline; issue 26-11-03-0901 追加同批记录
> 最后活动: 2026-11-04 22:43
**Refs:**

**R0(2026-11-04 22:43):** 同批收掉 fs.path_map from/to 的 str() 判空: 先 isinstance(str) 再判空, 非字符串报必须是字符串(当前为类型), 缺键/空串仍报不能为空; loaders 未动; 新增 2 条回归(类型矩阵+真实 YAML load_config), 红验旧实现 2 failed/恢复后 test_config_misc 67 passed; 全量数字见 kb.baseline; issue 26-11-03-0901 追加同批记录
