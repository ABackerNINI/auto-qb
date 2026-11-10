# bind-guard-ctor-bypass-fix

> 摘要: 认领并修复 issue 26-11-11-0114: bind 守阵 scan_bind_ports 拦截面从「只拦 .bind( 调用位」扩为「.bind( 位 + 构造位绑定族」(socketserver 服务族八名 + socket.create_server, 裸名/属性两形态), 盲区声明补子类化改名/关键字实参位; 活性探针构造位补四份双向覆盖 + 放行侧负例; 分批评审 3 轮(引文 3/3, minor x3 全修, 零 actionable); issue 翻 Done 补修复后补充, taxonomy 两处口径回写, 白名单注释对齐; test.quick/test.full 全绿(见 kb.baseline, 基线切片 26-11-11-0236)
> 最后活动: 2026-11-11 02:37

**R0(2026-11-11 02:37):** 认领并修复 issue 26-11-11-0114: bind 守阵 scan_bind_ports 拦截面从「只拦 .bind( 调用位」扩为「.bind( 位 + 构造位绑定族」(socketserver 服务族八名 + socket.create_server, 裸名/属性两形态), 盲区声明补子类化改名/关键字实参位; 活性探针构造位补四份双向覆盖 + 放行侧负例; 分批评审 3 轮(引文 3/3, minor x3 全修, 零 actionable); issue 翻 Done 补修复后补充, taxonomy 两处口径回写, 白名单注释对齐; test.quick/test.full 全绿(见 kb.baseline, 基线切片 26-11-11-0236)
