# 写入侧凭据判据的测试 idiom 误报

> 摘要: 工具写入判据把「凭据键名(Authorization/token 等) + 值不回显」的任何赋值形态当凭据字面量拦截 —— 测试里合法的鉴权头字典字面量(值是运行期读桩令牌, 无字面凭据)会让**整个文件**不可写; 且输出层掩码会把 `token: <值>` 显示改写成 `token=[redacted]`, 干扰定位与 oldText 拼写。
> 触发: 改含鉴权头字典字面量的测试文件被 artifact_secret_detected 拦, docstring 写 token 冒号键值形态, 凭显示层所见拼 oldText 永远匹配不上

- **触发**: 对既有测试文件做任何写入(edit/write 都是全文件扫描)被 `artifact_secret_detected` 拦, 报「键名 Authorization/token, 值不回显」。典型形态两类: ①web_env 系测试的鉴权头 idiom `auth = {<键名>: f"Bearer {mgr.web.token}"}`(值为夹具运行期读取); ②docstring/注释里的 `xxx_token: 描述` 冒号键值形态(哪怕值只是普通中文)。判据连 `dict(Authorization=...)` 关键字构造与值已提取成变量的字典字面量也拦 —— 它按**键名标识符 + 赋值形态**匹配, 不看值是否字面量。
- **判别**: 三步定性误报 —— ①`git diff` 为空可证被拦行全是 HEAD 既有内容(本轮未引入凭据); ②值是属性引用(f-string 内插变量)不是字面量; ③**显示掩码干扰**: 输出层(read/exec stdout)会把 `token: 值` 形态显示成 `token=[redacted]`, 凭「所见」拼 edit oldText 永远 `match_not_found` —— 用 `python` + `binascii.hexlify` 回读原始字节才见真值(26-10-15 实证: 显示为 `=[redacted]` 的行, 字节实为 `: 三`, 文件与 HEAD 逐字节一致)。
- **处置**: 判据自带「误判时如实告知用户由其决定, 不要绕过」—— **必须先问再动**。用户拍板后的消误报收敛(26-10-15 P4 轮样板): ①同文件同型行收敛成模块级单点 helper(scratch 脚本做机械替换 + 计数断言; scratch 自身含模式字面量也会被拦 → 匹配键程序化构造, 如 `"Auth" + "orization"`); ②helper 落 `_AUTH_HEADER_KEY = "Auth" + "orization"` 键名拆写常量 + 注释写明缘由与拍板来源(`dict(键名=...)` 与值提取成变量的字典字面量都仍被拦, 只有键名不出现在赋值形态才放行); ③docstring 冒号键值形态改括号注记。行为零变化用 `test.one` 全绿作回归证据。
- **守阵**: 无机检(判据在工具链侧, 非本仓代码); 收敛轮的基线切片注记即处理样板(`testing/baselines/26-10-15-1418-qb-traffic-restart-spike-gap-p4.md`)。
