# 3966 passed + 10 skipped —— Origin 头端口段非法时跨站闸 fail-closed(issue 26-10-20-2230)

> 摘要: 认领修复 issue 26-10-20-2230 —— `_origin_allowed` 把 `.port` 的 property 访问并入 try, 畸形 Origin 返回 False(403)而非把 ValueError 穿透成 500
> 基线时间: 2026-10-21 03:58
**Refs:** memory-bank/issues/26-10-20-2230-bug-webui-origin-port-parse.html

## 验收数字

`commands run test.full`(本机 Windows, 仓库自带 TMPDIR 前缀), 实测输出:

```text
TOTAL                                                20470     91   7012     93    99%
Required test coverage of 99% reached. Total coverage: 99.30%
3966 passed, 10 skipped in 73.12s (0:01:13)
```

口径注记:

- 0 failed / 0 error; 覆盖率闸(`--cov-fail-under 99`)照过(99%)。
- 本轮跑了三遍全量: 中间那遍红在 `test_memory_bank.py::test_gen_all_check_is_green`, **与本改动无关** —— 远端快进带进来的新 issue 文件未重建索引(以及本轮改了 issue 状态), 跑 `commands run kb.index` 后复绿; 三遍耗时 34.27s ~ 73.12s(单次采样无意义, 记区间)。
- 单点验证: `commands run test.one -- tests/test_web_auth.py` = 14 passed(补断言后仍 14 条: 断言加进既有用例, 未新增函数)。
- 真浏览器侧(`dev.e2e`)本轮未跑 —— 改动仅在 `auth.py` 一个纯函数内且未触及前端, 生产路径行为逐位不变。

## 本改动面

| 文件 | 改动 |
|---|---|
| `src/auto_qb/webui/server/auth.py` | `_origin_allowed`: `urlsplit` 与 `.port` / `.scheme` / `.hostname` 取值一并纳入同一 try, `except ValueError` → `return False`(fail-closed); docstring 补「解析整段 fail-closed」段并注 issue 号 |
| `tests/test_web_auth.py` | `test_auth_host_origin_parsing_helpers` 填实预留注释位: 4 条 Origin 非法端口断言(`127.0.0.1:notaport` 带/不带 host_port、`https://api.localhost:notaport`、`http://localhost:notaport`) |

## 未改(有意)

- 仍按「并入 try」而非「isdigit 预检」: 后者要自己重复 urlsplit 的端口段切分与越界校验, 多一处与标准库漂移的面。
- `_host_header_parts` 未动 —— 它本就把 `.port` 包在 try 内, 是这次对齐的基准侧。
- 未为 Origin 白名单引入配置项: 畸形 Origin 一律拒绝, 与既有「不在白名单即 403」口径一致, 无正当放行场景。
