# 26-10-21-0358-webui-origin-port-parse — 跨站闸 Origin 端口解析 fail-closed(issue 26-10-20-2230)

> 摘要: 用户指派认领修复 issue 26-10-20-2230 —— `auth.py::_origin_allowed` 里 `.port` 的惰性 property 访问漏在 try 外, 畸形 Origin(`http://127.0.0.1:notaport`)把 ValueError 穿透成 500; 修法 = 构造 + 属性取值一并纳入同一 try, `except ValueError` 返 False(403), 与同文件 `_host_header_parts` 同口径
> 最后活动: 2026-10-21 03:58

**R0(2026-10-21 03:58):** 认领并修复完成。复验先于改动: 报告 §02 的原探针在本 clone 仍逐字复现(锚点行号 `auth.py:92` 未漂移), 同侧 `_host_header_parts` 返回 `('', None)` —— 确认「两侧口径不一致」依旧成立。修法取「并入 try」而非「isdigit 预检」(后者要重复实现 urlsplit 的端口段切分与越界校验, 多一处与标准库漂移的面)。断言落进既有用例 `test_auth_host_origin_parsing_helpers`(填实 §06 预留的注释位, 未新增测试函数)。`test.full` 全绿, 实测数字见 `kb.baseline` 最新切片。

## 判定与取舍

- **为什么是 bug 不是特性**: 闸门挂在 FastAPI 全局依赖单点, 它的契约是「判不了就拒绝」。畸形输入走了 500 = 闸门自己成了故障源; 正确浏览器不发这种头, 但任意客户端的畸形头都应 403 而非 500。
- **为什么不动 `_host_header_parts`**: 它本就把 `.port` 包在 try 内(历史某轮已收口), 是这次对齐的**基准侧**, 不是缺陷侧。
- **为什么不加配置项**: 畸形 Origin 一律拒绝, 与既有「不在白名单即 403」同口径, 没有正当放行场景 —— 引入开关只会给误开放行留出后门。

## 未改(有意)

- 未跑真浏览器 e2e: 改动只在一个纯函数内、未触及前端, 生产路径行为逐位不变; 若后续动到跨站闸的请求面再补。
- 未回写 `config-reference/keys.md`: 本次不涉及配置面(键集/语义/缺省零变化), 事实以 `auth.py` 模块 docstring 与本切片为准 —— 范围守恒, 不顺手扩写。

## 下一步 / 移交

- 本件状态已 Done, 可蒸馏进 `progress/` 后删除本切片(与其它跨站闸条目合并成一张主题切片更合适 —— 已有 `26-10-16-1558-webui-cross-site-localhost-tld.md` 同域)。
- 新坑已记 `pitfalls/backend/lazy-property-parse-error.md`(惰性 property 抛异常, try 只包构造等于没包); 复发计数 0 —— 首次实发在 2026-10-16 那轮, 当时只收了 Host 一侧。
