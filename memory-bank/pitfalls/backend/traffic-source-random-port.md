# 随机端口之后, 一切写死的端口都是错的: 唯一出口是发现指针

> 摘要: 控制面端口改成 `http_port: 0`(内核分配)后, 文档示例 / 排障 curl / 订阅注册键里任何写死端口都成了错答案; 端口唯一出口是发现指针(手工看用 `endpoint` 子命令), 且端口一变订阅必须重注册。
> 触发: http_port 0, 随机端口, 8099, endpoint 子命令, 端口占用, 订阅注册, 重注册, 端口变

> 摘要: 控制面端口改成 `http_port: 0`(内核分配)后, 文档示例 / 排障 curl / 订阅注册键里任何写死端口都成了错答案; 端口唯一出口是发现指针(手工看用 `endpoint` 子命令), 且端口一变订阅必须重注册。

### 随机端口后别再猜端口: 指针是唯一出口, 订阅键要含基地址

- **触发**: 把工具控制面端口从固定值改成 `0` 让内核分配(计划 26-10-17-0339 D9), 但周边仍按
  「127.0.0.1:8099」写文档、写排障脚本、拼订阅注册键。
- **判别**: ①照文档敲端口一律 `Connection refused`; ②工具重启后 auto-qb 订阅还在往旧端口推 ——
  注册键里只有 token/客户端名、没有基地址, 端口变了却判成「没变, 继续心跳」; ③两个实例同时起
  不再抢端口(好事), 但「找不到工具」的报错变多 —— 有人还在读配置里的端口。
- **处置**: ①端口**只从指针读**(`host`/`port` 字段), 代码里不许再出现默认端口常量; ②手工排障用
  `global-traffic-monitor endpoint`(打印 host:port / token_path / data_dir); ③订阅注册键**必须含
  工具基地址** —— 端口变即视为新键, 注销旧注册再注册; ④自启项不烧端口(注册命令只带 `--data-dir`);
  ⑤配置校验要放开 `0`(旧校验判非法), 并断言默认值就是 `0`。
- **守阵**: 工具侧 `test_config.py::test_defaults_match_plan_section_05`(默认 0) ·
  `test_server.py::test_random_port_two_starts_differ_and_recorded_in_pointer` +
  `test_endpoint_subcommand_prints_pointer_fields` · auto-qb 侧订阅注册键含基地址
  (`tests/test_traffic_monitor_client.py`)
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
