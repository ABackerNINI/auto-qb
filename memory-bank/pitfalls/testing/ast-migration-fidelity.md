# 逐行迁移的保真坑: ast 求值串改写内容 / 生成模块自我 import

> 摘要: 机械拆分/迁移文件时, **AST 只给结构, 内容必须从源行取** —— `ast.get_docstring` 返回的是**求值后**的字符串(转义已解开), 拿它写回会把 `\\p{L}` 吃成 `\p{L}`(内容被静默改写 + 触发 SyntaxWarning); 另一头, 生成共享模块时若把「跨文件共享名」原样写进该模块自己的 `from X import ...`, 会撞自我 import(模块尚未初始化完)。两处都**测试全绿**、只有逐行对照或收集期才现形。
> 触发: 拆分文件, 迁移脚本, 逐行搬移, ast.get_docstring, 求值串, 转义被吃, `\\p`, SyntaxWarning, 生成模块, 自我 import, 循环 import, 行守恒, 保真校验

### `ast.get_docstring` 是求值串, 不是源文本 (S2 踩到)

- **触发**: 写 test_web.py 拆分工具(`scripts/split_test_web.py`), 用 `ast.get_docstring(tree, clean=False)` 取模块 docstring 再按函数名把「## 测试计划」条目重分布到新文件。
- **判别**: 源里一条计划行含 `\\p{L}\\p{N}`(正则字面量的**双反斜杠**), 经 `get_docstring` 出来变 `\p{L}\p{N}`(单反斜杠) —— 新文件内容被**静默改写**, 且编译期抛 `SyntaxWarning: "\p" is an invalid escape sequence`(源文件本身不报, 因为源是双反斜杠)。
- **处置**: docstring 一律**从源行切片**取(`lines[start-1:end]` 去掉首尾三引号), 不用 AST 求值串。判据: 迁移工具的「行守恒」校验(输出块体逐行 == 源行多重集)必须为真 —— 内容被改写时它会红。
- **同族**: 任何 `ast.literal_eval` / `Constant.value` / `get_docstring` 取到的都是**求值后**的值; 逐行迁移要的是**源文本**, 不是值。

### 生成共享模块时别让它 import 自己 (S2 踩到)

- **触发**: 同上工具 —— 把「被多个目标文件引用的辅助/常量」上收进新模块 `webui_helpers.py`, 该模块的 import 头由「本模块节点用到的跨文件共享名」推导。
- **判别**: 共享辅助之间互相引用(`_ui_aggregate` 用 `_ui_manifest` 等), 于是推导出的名单**包含本模块自己定义的名** ⇒ 生成 `from webui_helpers import _ui_manifest` —— 收集期报 `ImportError: cannot import name 'X' from partially initialized module 'webui_helpers' (most likely due to a circular import)`。
- **处置**: 推导导入名单时扣掉**本文件已定义的名**(`need & shared - local`)。判据: 演练的 `pytest --collect-only` 在导入期即暴露(不靠跑用例)。
