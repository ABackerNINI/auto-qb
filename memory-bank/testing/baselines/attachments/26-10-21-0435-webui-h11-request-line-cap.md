# 3977 passed + 2 skipped —— 组 key 请求行超 h11 未完成事件上限修复后全量基线

> 摘要: 组 key 请求行超 h11 未完成事件上限修复后全量基线
> 基线时间: 2026-10-21 04:35
**Refs:** memory-bank/pitfalls/backend/webui-h11-request-line-cap.md

## 验收数字

```text
TOTAL                                                20719      73   7012      89    99%
3977 passed, 2 skipped in 143.39s (0:02:23)
```

口径注记:

- 上表是 pytest 全量口径(含覆盖率门槛); 相对上基线的逐位对比不写 —— 看差值 `commands run kb.baseline -n 2`。
- 基线树 = 远端 cecbe4a9 快进后 + 本修复两文件(lifecycle.py / test_web_auth.py)在工作树未入库状态; 测的就是这个组合。
- 裸数字只写基线切片这一处; 档案与报告正文引它而不抄(守卫 `check_wording.py` 判据族 B)。

## 本改动面

- `src/auto_qb/webui/server/lifecycle.py`: 新增常量 `H11_MAX_INCOMPLETE_EVENT_SIZE = 1MiB` 并透传 `uvicorn.Config(h11_max_incomplete_event_size=...)` —— h11 缺省 16KB「未完成事件」上限会间歇性拦下组级路由的请求行(组 key = base64url(组路径+全组文件相对路径), 大组超限), 症状「WEBUI 启动整组报错」(2026-10-19 真机实报)。
- `tests/test_web_auth.py`: +2 守阵 —— ①装配断言 `test_start_web_server_config_raises_h11_incomplete_event_cap`(必须显式放宽且大于 h11 缺省); ②传输层红绿守阵 `test_oversized_request_line_reaches_app_not_transport_400`(真实 uvicorn 下头分两片送、首片 17KB 未完, 响应必须是应用层裁决而非传输层裸 400)。
- 红绿双验: 修复前两守阵均红(缺常量 / 真机同款 "Invalid HTTP request received." + 裸 400), 修复后全绿。
