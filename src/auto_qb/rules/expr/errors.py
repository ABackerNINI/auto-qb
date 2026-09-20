"""表达式错误类型

两类错误的处理路径完全不同, 不要混用:
- ExprSyntaxError: 编译期错误(词法/语法/静态检查)。配置加载阶段 fail-fast, 由 config
  校验聚合成 ConfigError 一并报出, 运行期不会再遇到。
- ExprError: 求值期错误(除零 / 类型不符 / 数据源不可用)。由 Rule.process 的条件分支
  兜住 -> 不匹配 + 中断后续规则(见计划第 05 节「出错即停规则」)。
"""


class ExprError(Exception):
    """表达式错误基类"""


class ExprSyntaxError(ExprError):
    """编译期错误: 词法 / 语法 / 静态检查失败

    pos 为 1 起的字符列号(仅用于让报错能定位, 消息本体由调用方拼好)。
    """
    def __init__(self, message: str, pos: int | None = None):
        self.pos = pos
        super().__init__(f"{message}（第 {pos} 列）" if pos is not None else message)
