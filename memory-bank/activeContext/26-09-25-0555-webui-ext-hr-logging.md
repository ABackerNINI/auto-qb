# 浏览器扩展运行日志(分级 + 环形上限)

> 摘要: 扩展(hr-fetch-proxy)已加运行日志 —— 条数 10–10000 可设(默认 1000, 环形丢最旧)、四级
> debug/info/warn/error(记录阈值默认 info + 选项页分级过滤)、明细含毫秒时间/收到的命令/请求类型与站点/
> HTTP 结果/耗时/字节数/回传后端响应体快照; 唯一事实源 `chrome.storage.local`(防抖整份写回)。选项页④区
> 设置即时生效 + 清空走 clear-logs 协议。守阵真跑抓到 flush 链自引用死锁(已修 + 入坑); 顺带修轮询周期
> 文案漂移(5 分钟→1 分钟)并加防漂守阵。全量 1579 collected: 1576 passed + 1 skipped(2 条 GBK 已知假红)。
> **任务已完成并立档** → [tasks/26-09-25-webui-ext-hr-logging.md](../tasks/26-09-25-webui-ext-hr-logging.md);
> 已提交推送。无未完事项。
> 最后活动: 2026-09-25 05:55
