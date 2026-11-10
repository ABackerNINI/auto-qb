# 5945 passed + 2 skipped —— bind 守阵构造位绕过收编批收尾全量绿

> 摘要: 5945 passed, 2 skipped (184.12s), 覆盖率 99% (26307 stmts / 50 miss / 9176 br / 62 partial) —— bind 守阵构造位绕过收编批(issue 26-11-11-0114)收尾全量绿
> 基线时间: 2026-11-11 02:36

## 验收数字

```text
TOTAL                                                26307     50   9176     62    99%
5945 passed, 2 skipped in 184.12s (0:03:04)
```

## 本改动面

- `tests/test_flaky_timing_guards.py`: scan_bind_ports 拦截面从「只匹配 .bind(」扩为「.bind( 方法位 + 构造位绑定族」(BIND_CONSTRUCTOR_NAMES 八名 + _is_binding_site_call 裸名/属性两形态); 模块 docstring 扫描器口径与盲区声明(子类化改名/关键字实参位)同步; 活性探针构造位补四份(socketserver 族裸名/属性 + create_server 属性/裸名, 双向禁绑两带各覆盖) + 放行侧补 port=0 属性形态与非绑定构造名 MyConfig。
- `tests/flaky_allowlist.py`: ALLOW_BIND_PORT 段注释口径对齐新拦截面(存量保持空表, 构造位 port=0 三处引用逐行核实)。
- `memory-bank/testing/root-cause-taxonomy.md`: 端口/资源行与守阵段两处口径回写(绑定位固定口 = bind 调用位 + 构造位绑定族)。
- `memory-bank/issues/26-11-11-0114-test-bind-guard-constructor-bypass.html`: 翻 Done(kb.status) + 修复后补充段(修法/盲区边界/探针四份/验证数字)。
- 评审: 分批评审 3 轮(全能档单派, 引文 3/3 过检, minor x3 全当场修, 轮 3 零 actionable)。
