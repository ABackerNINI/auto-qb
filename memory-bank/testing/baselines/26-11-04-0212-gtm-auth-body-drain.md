# 5032 passed + 10 skipped(根 99%, test.full 157.09s); gtm 551 passed + 2 skipped(99%, test.gtm 70.12s) —— gtm 401 短路 drain 修复全量基线

> 摘要: gtm 401 短路 drain 修复全量基线
> 基线时间: 2026-11-04 02:12
**Refs:**

## 验收数字

- `commands run test.full`(2026-11-04 02:12 实测): TOTAL 23325 / 185 miss / 7956 partial / 158 ignored, 覆盖率 99%; `5032 passed, 10 skipped in 157.09s (0:02:37)`。
- `commands run test.gtm`(2026-11-04 02:07 实测): TOTAL 2613 / 28 miss / 698 partial / 17 ignored, 覆盖率 99%; `551 passed, 2 skipped in 70.12s (0:01:10)`, 门槛判定通过。
- 口径: 两条命令均为全绿, 无失败无 xfail; 改动面在 tools/global-traffic-monitor(根套件不覆盖 gtm 代码, gtm 数字由 test.gtm 单点给出)。

## 本改动面

- `tools/global-traffic-monitor/src/gtm/server.py`: `handle()` 两个 401 短路出口前置 `_drain_body(handler)`(新增, 按 Content-Length 读空请求体, 上限 `_MAX_BODY_BYTES`, 超∶只陪读到上限) —— 修 issue 26-11-03-1144: 不读 body 就断链, socket 残留数据致内核关链时补 RST, Windows 客户端偶发先收 WinError 10053 而非 401。
- `tools/global-traffic-monitor/tests/test_server.py`: 新增确定性回归 `test_auth_401_drains_request_body_before_responding`(声明 Content-Length=100 只先发 11 字节, 断言 401 必须等 body 发满才上 wire; 修前该用例必红); 头部「测试计划」docstring 同步一行。
- `memory-bank/issues/26-11-03-1144-bug-gtm-auth-body-drain.html`: 状态 Open → Done, 复验 + 修复后补充(实际修法/验证方式/测试数字)留痕。
