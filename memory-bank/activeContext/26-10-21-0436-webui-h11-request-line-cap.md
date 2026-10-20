# webui-h11-request-line-cap

> 摘要: 修 WEBUI 启动整组报错: 组 key 随请求行走, h11 缺省 16KB 未完成事件上限间歇性拦掉大组组级命令(判非法 + MUST_CLOSE 竞态崩溃); lifecycle.py 显式放宽 h11_max_incomplete_event_size=1MiB + test_web_auth 两条守阵(装配断言 + 真实 uvicorn 分片头红绿守阵); 全量 3977 passed + 2 skipped / 99%(基线切片 26-10-21-0435), 坑档 pitfalls/backend/webui-h11-request-line-cap.md
> 最后活动: 2026-10-21 04:36

**R0(2026-10-21 04:36):** 修 WEBUI 启动整组报错: 组 key 随请求行走, h11 缺省 16KB 未完成事件上限间歇性拦掉大组组级命令(判非法 + MUST_CLOSE 竞态崩溃); lifecycle.py 显式放宽 h11_max_incomplete_event_size=1MiB + test_web_auth 两条守阵(装配断言 + 真实 uvicorn 分片头红绿守阵); 全量 3977 passed + 2 skipped / 99%(基线切片 26-10-21-0435), 坑档 pitfalls/backend/webui-h11-request-line-cap.md
