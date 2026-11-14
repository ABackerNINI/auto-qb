# 6127 —— 基线: hrExclTip methods 层修复批 (6127 passed / 2 skipped)

> 摘要: 基线: hrExclTip methods 层修复批 (6127 passed / 2 skipped)
> 基线时间: 2026-11-14 10:38

## 验收数字

`commands run test.full` 实测(2026-11-14 10:38 前后, 干净树):

```
6127 passed, 2 skipped in 209.94s (0:03:29)
TOTAL                                                27285     68   9582     73    99%
Required test coverage of 99.5% reached. Total coverage: 99.61%
```

## 本改动面

- `src/auto_qb/webui/static/shared/hr.js`: hrExclTip 判定门调用补 `.methods` 层(cd14ffe6 根路径直呼修复)+ 注释层级纪律。
- `tests/test_webui_static_skins_widget.py`: `test_frontend_hr_safety_wiring` 新增第 5 组层级钉扎断言(AQB_DECORATE 顶层片段锚定 / methods 存在性 / 定义缩进敏感锚 / 调用路径 + 根路径直呼归零), 头部测试计划与函数 docstring 同步。
- 新增坑档 `memory-bank/pitfalls/web-ui/mixin-method-call-misses-methods-layer.md`(_index 生成物随 kb.index 再生)。
